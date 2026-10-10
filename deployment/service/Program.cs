using Microsoft.Win32;
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.ServiceProcess;
using System.Threading;
using System.Runtime.CompilerServices;
using System.Text.RegularExpressions;

[assembly: InternalsVisibleTo("MT5Agent.Service.Tests")]

namespace MT5Agent.Service
{
    internal static class Program
    {
        private static void Main() { ServiceBase.Run(new AgentService()); }
    }

    internal sealed class AgentService : ServiceBase
    {
        private const string AgentExecutableName = "MT5Agent-v0.1.3.exe";
        private const int StopGracePeriodMilliseconds = 8000;
        private const int StartupObservationMilliseconds = 1200;
        private const int ServiceSpecificError = 1066;

        private readonly object gate = new object();
        private readonly object logGate = new object();
        private readonly Func<string[]> managementSidProvider;
        private readonly string serviceDirectory;
        private readonly string configuredExecutableName;
        private readonly string logRoot;
        private readonly string testArguments;
        private readonly string testWorkingDirectory;
        private Process agent;
        private IntPtr agentJob = IntPtr.Zero;
        private bool stopping;
        private string agentExecutable;

        public AgentService()
            : this(AppDomain.CurrentDomain.BaseDirectory, AgentExecutableName,
                ReadManagementSids, null,
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "MT5Agent", "Logs"), null, null)
        {
        }

        // The injectable constructor and lifecycle methods keep Windows process
        // ownership testable without registering a real service or touching HKLM.
        internal AgentService(string serviceDirectory, string executableName, Func<string[]> sidProvider,
            string arguments, string diagnosticDirectory)
            : this(serviceDirectory, executableName, sidProvider, arguments, diagnosticDirectory, null, null)
        {
        }

        internal AgentService(string serviceDirectory, string executableName, Func<string[]> sidProvider,
            string arguments, string diagnosticDirectory, string workingDirectory)
            : this(serviceDirectory, executableName, sidProvider, arguments, diagnosticDirectory, workingDirectory, null)
        {
        }

        private AgentService(string serviceDirectory, string executableName, Func<string[]> sidProvider,
            string arguments, string diagnosticDirectory, string workingDirectory, object unused)
        {
            ServiceName = "MT5Agent";
            CanStop = true;
            CanShutdown = true;
            AutoLog = true;
            this.serviceDirectory = Path.GetFullPath(serviceDirectory);
            configuredExecutableName = executableName;
            managementSidProvider = sidProvider;
            testArguments = arguments;
            testWorkingDirectory = workingDirectory;
            logRoot = diagnosticDirectory;
        }

        protected override void OnStart(string[] args)
        {
            string workingDirectory = null;
            try
            {
                Directory.CreateDirectory(logRoot);
                agentExecutable = ResolveAgentExecutable(serviceDirectory, configuredExecutableName);
                workingDirectory = testWorkingDirectory ?? Path.GetDirectoryName(agentExecutable);
                string[] allowedSids = managementSidProvider();
                ValidateManagementSids(allowedSids);

                ProcessStartInfo start = new ProcessStartInfo(agentExecutable)
                {
                    WorkingDirectory = workingDirectory,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true
                };
                if (testArguments != null) start.Arguments = testArguments;
                start.EnvironmentVariables["MT5_AGENT_HTTP_HOST"] = "127.0.0.1";
                start.EnvironmentVariables["MT5_AGENT_LOG_LEVEL"] = "INFO";
                start.EnvironmentVariables["MT5_AGENT_MANAGEMENT_ALLOWED_SIDS"] = String.Join(",", allowedSids);

                lock (gate)
                {
                    if (agent != null && !HasExited(agent))
                    {
                        Append("service-host.log", "WARN duplicate start request ignored; agent_pid=" + agent.Id);
                        return;
                    }
                    if (agent != null) StopAgentLocked();
                    stopping = false;
                    agent = new Process { StartInfo = start, EnableRaisingEvents = true };
                    agent.OutputDataReceived += (s, e) => Append("agent.stdout.log", e.Data);
                    agent.ErrorDataReceived += (s, e) => Append("agent.stderr.log", e.Data);
                    agent.Exited += AgentExited;

                    if (!agent.Start()) throw new InvalidOperationException("AGENT_PROCESS_START_RETURNED_FALSE");
                    // Drain redirected streams before the job assignment so a
                    // verbose child cannot block while startup is being checked.
                    agent.BeginOutputReadLine();
                    agent.BeginErrorReadLine();
                    AttachAgentToOwnedJob(agent);
                    if (agent.WaitForExit(StartupObservationMilliseconds))
                        throw new InvalidOperationException("AGENT_PROCESS_EXITED_DURING_STARTUP; exit_code=" + agent.ExitCode);

                    Append("service-host.log", "INFO startup completed; agent_pid=" + agent.Id + "; executable=" + agentExecutable);
                }
            }
            catch (Exception ex)
            {
                ExitCode = ServiceSpecificError;
                lock (gate)
                {
                    stopping = true;
                    Append("service-host.log", "ERROR startup failed; executable=" + (agentExecutable ?? "<unresolved>") +
                        "; working_directory=" + (workingDirectory ?? "<unresolved>") + Environment.NewLine + ex);
                    StopAgentLocked();
                }
                // Keep the original exception and stack visible to SCM/Event Log.
                throw new InvalidOperationException("MT5Agent failed to start. See the Service Host log for diagnostic context.", ex);
            }
        }

        protected override void OnStop()
        {
            lock (gate)
            {
                stopping = true;
                Append("service-host.log", "INFO service stop requested.");
                StopAgentLocked();
            }
        }

        protected override void OnShutdown() { OnStop(); base.OnShutdown(); }

        internal void StartForTest() { OnStart(new string[0]); }
        internal void StopForTest() { OnStop(); }
        internal int AgentPidForTest { get { lock (gate) return agent == null ? 0 : agent.Id; } }

        internal static string ResolveAgentExecutable(string serviceDirectory, string executableName)
        {
            if (String.IsNullOrWhiteSpace(serviceDirectory)) throw new ArgumentException("Service directory is required.", "serviceDirectory");
            if (String.IsNullOrWhiteSpace(executableName) || Path.GetFileName(executableName) != executableName)
                throw new ArgumentException("Agent executable must be a filename beneath the install root.", "executableName");

            string servicePath = Path.GetFullPath(serviceDirectory).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            DirectoryInfo serviceFolder = new DirectoryInfo(servicePath);
            if (!String.Equals(serviceFolder.Name, "Service", StringComparison.OrdinalIgnoreCase) || serviceFolder.Parent == null)
                throw new InvalidOperationException("SERVICE_DIRECTORY_LAYOUT_INVALID: expected <install-root>\\Service.");

            string installRoot = serviceFolder.Parent.FullName;
            string agentDirectory = Path.Combine(installRoot, "Agent");
            string executable = Path.GetFullPath(Path.Combine(agentDirectory, executableName));
            string prefix = Path.GetFullPath(agentDirectory).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (!executable.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("AGENT_EXECUTABLE_OUTSIDE_INSTALL_ROOT");
            if (!File.Exists(executable)) throw new FileNotFoundException("AGENT_EXECUTABLE_MISSING: expected Agent beside Service under the install root.", executable);
            return executable;
        }

        internal static void ValidateManagementSids(string[] sids)
        {
            if (sids == null || sids.Length == 0) throw new InvalidOperationException("MANAGEMENT_CONTROL_PRINCIPAL_NOT_CONFIGURED");
            foreach (string sid in sids)
            {
                try { new SecurityIdentifier(sid); }
                catch (Exception ex) { throw new InvalidOperationException("MANAGEMENT_CONTROL_SID_INVALID", ex); }
            }
        }

        private static string[] ReadManagementSids()
        {
            using (RegistryKey key = Registry.LocalMachine.OpenSubKey(@"SOFTWARE\MT5Agent\Management", false))
            {
                object value = key == null ? null : key.GetValue("AllowedUserSids", null, RegistryValueOptions.DoNotExpandEnvironmentNames);
                string[] sids = value as string[];
                ValidateManagementSids(sids);
                return sids;
            }
        }

        private void AgentExited(object sender, EventArgs args)
        {
            Process exited = sender as Process;
            if (exited == null) return;
            ThreadPool.QueueUserWorkItem(delegate
            {
                lock (gate)
                {
                    if (stopping || !Object.ReferenceEquals(agent, exited)) return;
                    int childExitCode = 1;
                    try { childExitCode = exited.ExitCode; } catch { }
                    ExitCode = childExitCode == 0 ? 1 : childExitCode;
                    Append("service-host.log", "ERROR Agent child exited unexpectedly; exit_code=" + childExitCode + "; service is transitioning to stopped.");
                    try { Stop(); }
                    catch (Exception ex) { Append("service-host.log", "ERROR SCM stop notification failed." + Environment.NewLine + ex); }
                }
            });
        }

        private void StopAgentLocked()
        {
            Process current = agent;
            if (current == null) { CloseAgentJob(); return; }
            agent = null;
            try
            {
                if (!HasExited(current))
                {
                    current.CloseMainWindow();
                    if (!current.WaitForExit(StopGracePeriodMilliseconds))
                    {
                        Append("service-host.log", "WARN graceful Agent shutdown timed out; closing owned process job.");
                        CloseAgentJob();
                        if (!HasExited(current)) current.Kill();
                        current.WaitForExit(5000);
                    }
                }
            }
            catch (Exception ex) { Append("service-host.log", "ERROR Agent shutdown failed." + Environment.NewLine + ex); }
            finally
            {
                CloseAgentJob();
                current.Dispose();
            }
        }

        private static bool HasExited(Process process)
        {
            try { return process.HasExited; }
            catch (InvalidOperationException) { return true; }
        }

        private void CloseAgentJob()
        {
            if (agentJob == IntPtr.Zero) return;
            NativeMethods.CloseHandle(agentJob);
            agentJob = IntPtr.Zero;
        }

        private void Append(string name, string line)
        {
            if (line == null || String.IsNullOrEmpty(logRoot)) return;
            line = Regex.Replace(line,
                @"(?i)\b(password|passwd|token|secret|authorization|api[_-]?key)\b(\s*[:=]\s*)(""[^""]*""|'[^']*'|[^\s,;]+)",
                "$1$2[REDACTED]");
            try
            {
                lock (logGate)
                {
                    Directory.CreateDirectory(logRoot);
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
            catch { /* Diagnostics must never hide the original startup failure. */ }
        }

        private void AttachAgentToOwnedJob(Process process)
        {
            agentJob = NativeMethods.CreateJobObject(IntPtr.Zero, null);
            if (agentJob == IntPtr.Zero) throw new Win32ExceptionWrapper("AGENT_JOB_CREATE_FAILED");
            JobObjectExtendedLimitInformation limits = new JobObjectExtendedLimitInformation();
            limits.BasicLimitInformation.LimitFlags = 0x00002000; // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if (!NativeMethods.SetInformationJobObject(agentJob, 9, ref limits,
                    (uint)Marshal.SizeOf(typeof(JobObjectExtendedLimitInformation))) ||
                !NativeMethods.AssignProcessToJobObject(agentJob, process.Handle))
                throw new Win32ExceptionWrapper("AGENT_JOB_ASSIGN_FAILED");
        }

        private sealed class Win32ExceptionWrapper : InvalidOperationException
        {
            internal Win32ExceptionWrapper(string operation)
                : base(operation + ": win32_error=" + Marshal.GetLastWin32Error()) { }
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct BasicLimitInformation
        {
            public long PerProcessUserTimeLimit; public long PerJobUserTimeLimit; public uint LimitFlags;
            public UIntPtr MinimumWorkingSetSize; public UIntPtr MaximumWorkingSetSize; public uint ActiveProcessLimit;
            public UIntPtr Affinity; public uint PriorityClass; public uint SchedulingClass;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct IoCounters { public ulong ReadOperationCount; public ulong WriteOperationCount; public ulong OtherOperationCount; public ulong ReadTransferCount; public ulong WriteTransferCount; public ulong OtherTransferCount; }
        [StructLayout(LayoutKind.Sequential)]
        private struct JobObjectExtendedLimitInformation
        {
            public BasicLimitInformation BasicLimitInformation; public IoCounters IoInfo; public UIntPtr ProcessMemoryLimit;
            public UIntPtr JobMemoryLimit; public UIntPtr PeakProcessMemoryUsed; public UIntPtr PeakJobMemoryUsed;
        }
        private static class NativeMethods
        {
            [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] internal static extern IntPtr CreateJobObject(IntPtr attributes, string name);
            [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)] internal static extern bool SetInformationJobObject(IntPtr job, int informationClass, ref JobObjectExtendedLimitInformation information, uint informationLength);
            [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)] internal static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
            [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)] internal static extern bool CloseHandle(IntPtr handle);
        }
    }
}
