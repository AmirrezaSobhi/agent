using MT5Agent.Service;
using System;
using System.Diagnostics;
using System.IO;
using System.Threading;

namespace MT5Agent.Service.Tests
{
    internal static class Program
    {
        private const string AgentName = "MT5Agent-v0.1.3.exe";
        private static int passed;

        private static int Main()
        {
            string root = Path.Combine(Path.GetTempPath(), "mt5agent-service-tests-" + Guid.NewGuid().ToString("N"));
            string service = Path.Combine(root, "Service");
            string agentDir = Path.Combine(root, "Agent");
            string logs = Path.Combine(root, "Logs");
            Directory.CreateDirectory(service);
            Directory.CreateDirectory(agentDir);
            string cmd = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "cmd.exe");
            string fixture = Path.Combine(agentDir, AgentName);
            File.Copy(cmd, fixture);
            try
            {
                Run("installed layout resolves sibling Agent folder", delegate {
                    Equal(Path.GetFullPath(fixture), AgentService.ResolveAgentExecutable(service, AgentName));
                });
                Run("missing Agent executable fails with useful detail", delegate {
                    Throws<FileNotFoundException>(delegate { AgentService.ResolveAgentExecutable(service, "missing.exe"); }, "AGENT_EXECUTABLE_MISSING");
                });
                Run("invalid service directory layout is rejected", delegate {
                    Throws<InvalidOperationException>(delegate { AgentService.ResolveAgentExecutable(root, AgentName); }, "SERVICE_DIRECTORY_LAYOUT_INVALID");
                });
                Run("invalid SID configuration fails closed", delegate {
                    Throws<InvalidOperationException>(delegate { AgentService.ValidateManagementSids(new[] { "S-1-not-a-sid" }); }, "MANAGEMENT_CONTROL_SID_INVALID");
                });
                Run("missing SID configuration fails closed", delegate {
                    Throws<InvalidOperationException>(delegate { AgentService.ValidateManagementSids(new string[0]); }, "MANAGEMENT_CONTROL_PRINCIPAL_NOT_CONFIGURED");
                });
                Run("service starts one child, rejects duplicate start, and cleans up", delegate {
                    AgentService host = Create(service, logs, "/c ping 127.0.0.1 -n 4 >nul");
                    host.StartForTest();
                    int firstPid = host.AgentPidForTest;
                    if (firstPid <= 0) throw new Exception("Agent PID was not captured after start.");
                    host.StartForTest();
                    if (host.AgentPidForTest != firstPid) throw new Exception("Duplicate start launched a second Agent process.");
                    Contains(File.ReadAllText(Path.Combine(logs, "service-host.log")), "duplicate start request ignored");
                    host.StopForTest();
                    if (IsProcessRunning(firstPid)) throw new Exception("Service stop left its Agent child running.");
                    host.StartForTest();
                    host.StopForTest();
                });
                Run("immediate child exit fails startup and logs exit code", delegate {
                    AgentService host = Create(service, logs, "/c exit 7");
                    Throws<InvalidOperationException>(host.StartForTest, "AGENT_PROCESS_EXITED_DURING_STARTUP");
                    string log = File.ReadAllText(Path.Combine(logs, "service-host.log"));
                    Contains(log, "AGENT_PROCESS_EXITED_DURING_STARTUP");
                    Contains(log, "exit_code=7");
                    Contains(log, "System.InvalidOperationException");
                });
                Run("invalid configuration is logged and never reports healthy", delegate {
                    AgentService host = new AgentService(service, AgentName, delegate { return new[] { "invalid" }; }, "/c exit 0", logs);
                    Throws<InvalidOperationException>(host.StartForTest, "MANAGEMENT_CONTROL_SID_INVALID");
                    Contains(File.ReadAllText(Path.Combine(logs, "service-host.log")), "MANAGEMENT_CONTROL_SID_INVALID");
                });
                Run("invalid working directory is logged as a startup failure", delegate {
                    AgentService host = new AgentService(service, AgentName, delegate { return new[] { "S-1-5-18" }; },
                        "/c exit 0", logs, Path.Combine(root, "missing-working-directory"));
                    Throws<InvalidOperationException>(host.StartForTest, "failed to start");
                    string log = File.ReadAllText(Path.Combine(logs, "service-host.log"));
                    Contains(log, "working_directory=");
                    Contains(log, "Win32Exception");
                });
                Run("unexpected child exit is recorded as service failure", delegate {
                    AgentService host = Create(service, logs, "/c ping 127.0.0.1 -n 3 >nul & exit 7");
                    host.StartForTest();
                    DateTime deadline = DateTime.UtcNow.AddSeconds(10);
                    string logPath = Path.Combine(logs, "service-host.log");
                    while (DateTime.UtcNow < deadline && (!File.Exists(logPath) || !File.ReadAllText(logPath).Contains("Agent child exited unexpectedly")))
                        Thread.Sleep(100);
                    Contains(File.ReadAllText(logPath), "Agent child exited unexpectedly");
                    if (host.ExitCode == 0) throw new Exception("Unexpected child exit left service ExitCode healthy.");
                });
                Console.WriteLine("SERVICE_TEST_SUMMARY passed=" + passed + " failed=0");
                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("SERVICE_TEST_FAILURE " + ex);
                return 1;
            }
            finally
            {
                try { Directory.Delete(root, true); } catch { }
            }
        }

        private static AgentService Create(string service, string logs, string arguments)
        {
            return new AgentService(service, AgentName, delegate { return new[] { "S-1-5-18" }; }, arguments, logs);
        }

        private static void Run(string name, Action test)
        {
            test();
            passed++;
            Console.WriteLine("PASS " + name);
        }

        private static void Equal(string expected, string actual)
        {
            if (!String.Equals(expected, actual, StringComparison.OrdinalIgnoreCase))
                throw new Exception("Expected '" + expected + "' but got '" + actual + "'.");
        }

        private static void Contains(string value, string expected)
        {
            if (value.IndexOf(expected, StringComparison.OrdinalIgnoreCase) < 0)
                throw new Exception("Expected text not found: " + expected);
        }

        private static bool IsProcessRunning(int pid)
        {
            try { using (Process process = Process.GetProcessById(pid)) return !process.HasExited; }
            catch (ArgumentException) { return false; }
        }

        private static void Throws<T>(Action action, string expectedMessage) where T : Exception
        {
            try { action(); }
            catch (T ex) { Contains(ex.ToString(), expectedMessage); return; }
            throw new Exception("Expected " + typeof(T).Name + " containing " + expectedMessage + ".");
        }
    }
}
