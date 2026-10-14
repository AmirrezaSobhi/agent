// Temporary test-only SCM host. This is not the product installer/service.
// It starts only the Python Agent Core read-only Management Pipe with runtime
// access explicitly disabled. Reversible setup/removal is documented in the
// Phase 5 evidence bundle.
using System;
using System.Diagnostics;
using System.IO;
using System.ServiceProcess;
using System.Threading;

internal sealed class Phase5ServiceHarness : ServiceBase
{
    private const string Python = @"C:\Users\Administrator\AppData\Local\Temp\mt5agent-phase5-python-9286e4f\Scripts\python.exe";
    private const string SourceRoot = @"C:\Users\Administrator\AppData\Local\Temp\mt5agent-phase5-correct";
    private const string AgentEntry = @"C:\Users\Administrator\AppData\Local\Temp\mt5agent-phase5-correct\tests\windows\phase5_service_agent.py";
    private const string StopEventName = @"Global\MT5AgentPhase5TestStop";
    private const string OutputLog = @"C:\Users\Administrator\AppData\Local\Temp\mt5agent-phase5-service-child.log";

    private Process child;
    private EventWaitHandle stopSignal;

    private Phase5ServiceHarness()
    {
        ServiceName = "MT5AgentPhase5Test";
        CanStop = true;
        CanShutdown = true;
        AutoLog = true;
    }

    protected override void OnStart(string[] args)
    {
        stopSignal = new EventWaitHandle(false, EventResetMode.ManualReset, StopEventName);
        var info = new ProcessStartInfo
        {
            FileName = Python,
            Arguments = "-u \"" + AgentEntry + "\"",
            WorkingDirectory = SourceRoot,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        info.EnvironmentVariables["PYTHONPATH"] = SourceRoot;
        info.EnvironmentVariables["MT5_AGENT_PHASE5_CONTEXT"] =
            @"C:\Users\Administrator\AppData\Local\Temp\mt5agent-phase5-service-context.json";
        child = new Process { StartInfo = info, EnableRaisingEvents = true };
        child.OutputDataReceived += WriteChildOutput;
        child.ErrorDataReceived += WriteChildOutput;
        child.Exited += ChildExited;
        if (!child.Start()) throw new InvalidOperationException("Python Agent process did not start.");
        child.BeginOutputReadLine();
        child.BeginErrorReadLine();
    }

    private static void WriteChildOutput(object sender, DataReceivedEventArgs args)
    {
        if (String.IsNullOrEmpty(args.Data)) return;
        try
        {
            File.AppendAllText(OutputLog, DateTime.UtcNow.ToString("o") + " " + args.Data + Environment.NewLine);
        }
        catch (IOException) { }
        catch (UnauthorizedAccessException) { }
    }

    private void ChildExited(object sender, EventArgs args)
    {
        // A premature Agent exit should be visible to SCM as a service failure.
        if (child != null && !stopSignal.WaitOne(0)) Stop();
    }

    protected override void OnStop()
    {
        if (stopSignal != null) stopSignal.Set();
        if (child != null)
        {
            if (!child.WaitForExit(10000)) child.Kill();
            child.WaitForExit(2000);
            child.Dispose();
            child = null;
        }
        if (stopSignal != null)
        {
            stopSignal.Dispose();
            stopSignal = null;
        }
        base.OnStop();
    }

    protected override void OnShutdown() { OnStop(); base.OnShutdown(); }

    private static void Main() { ServiceBase.Run(new Phase5ServiceHarness()); }
}
