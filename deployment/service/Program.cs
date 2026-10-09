using Microsoft.Win32;
using System;
using System.Diagnostics;
using System.IO;
using System.ServiceProcess;
using System.Threading;

namespace MT5Agent.Service
{
    internal static class Program
    {
        private static void Main() { ServiceBase.Run(new AgentService()); }
    }

    internal sealed class AgentService : ServiceBase
    {
        private Process agent;
        private readonly object gate = new object();
        private readonly object logGate = new object();
        private string root;
        private string logRoot;

        public AgentService()
        {
            ServiceName = "MT5Agent";
            CanStop = true;
            CanShutdown = true;
            AutoLog = true;
        }

        protected override void OnStart(string[] args)
        {
            root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory);
            logRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "MT5Agent", "Logs");
            Directory.CreateDirectory(logRoot);
            string executable = Path.GetFullPath(Path.Combine(root, "Agent", "MT5Agent-v0.1.3.exe"));
            if (!executable.StartsWith(root, StringComparison.OrdinalIgnoreCase) || !File.Exists(executable))
                throw new InvalidOperationException("AGENT_EXECUTABLE_MISSING_OR_OUTSIDE_INSTALL_ROOT");

            ProcessStartInfo start = new ProcessStartInfo(executable) {
                WorkingDirectory = Path.GetDirectoryName(executable), UseShellExecute = false,
                CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true
            };
            start.EnvironmentVariables["MT5_AGENT_HTTP_HOST"] = "127.0.0.1";
            start.EnvironmentVariables["MT5_AGENT_LOG_LEVEL"] = "INFO";
            string[] allowedSids = ReadManagementSids();
            start.EnvironmentVariables["MT5_AGENT_MANAGEMENT_ALLOWED_SIDS"] = String.Join(",", allowedSids);
            lock (gate)
            {
                agent = new Process { StartInfo = start, EnableRaisingEvents = true };
                agent.OutputDataReceived += (s, e) => Append("agent.stdout.log", e.Data);
                agent.ErrorDataReceived += (s, e) => Append("agent.stderr.log", e.Data);
                if (!agent.Start()) throw new InvalidOperationException("AGENT_PROCESS_START_FAILED");
                agent.BeginOutputReadLine(); agent.BeginErrorReadLine();
            }
        }

        protected override void OnStop() { StopAgent(); }
        protected override void OnShutdown() { StopAgent(); base.OnShutdown(); }

        private string[] ReadManagementSids()
        {
            using (RegistryKey key = Registry.LocalMachine.OpenSubKey(@"SOFTWARE\MT5Agent\Management", false))
            {
                object value = key == null ? null : key.GetValue("AllowedUserSids", null, RegistryValueOptions.DoNotExpandEnvironmentNames);
                string[] sids = value as string[];
                if (sids == null || sids.Length == 0) throw new InvalidOperationException("MANAGEMENT_CONTROL_PRINCIPAL_NOT_CONFIGURED");
                foreach (string sid in sids)
                    if (String.IsNullOrWhiteSpace(sid) || !sid.StartsWith("S-1-", StringComparison.Ordinal))
                        throw new InvalidOperationException("MANAGEMENT_CONTROL_SID_INVALID");
                return sids;
            }
        }

        private void StopAgent()
        {
            lock (gate)
            {
                if (agent == null) return;
                try
                {
                    if (!agent.HasExited)
                    {
                        // The child executable path is fixed under the protected install directory.
                        // No caller-controlled command line or process name is used.
                        agent.CloseMainWindow();
                        if (!agent.WaitForExit(8000)) agent.Kill();
                        agent.WaitForExit(5000);
                    }
                }
                finally { agent.Dispose(); agent = null; }
            }
        }

        private void Append(string name, string line)
        {
            if (line == null) return;
            try
            {
                lock (logGate)
                {
                    string path = Path.Combine(logRoot, name);
                    FileInfo current = new FileInfo(path);
                    if (current.Exists && current.Length >= 10 * 1024 * 1024)
                    {
                        string previous = path + ".1";
                        if (File.Exists(previous)) File.Delete(previous);
                        File.Move(path, previous);
                    }
                    File.AppendAllText(path, DateTime.UtcNow.ToString("o") + " " + line + Environment.NewLine);
                }
            }
            catch { /* Service availability does not depend on diagnostic disk writes. */ }
        }
    }
}
