using System;
using System.IO;
using System.IO.Pipes;
using System.Security.AccessControl;
using System.Security.Principal;
using System.ServiceProcess;
using System.Text;
using System.Threading;

namespace MT5Agent.WindowsSecuritySpike
{
    internal static class Program
    {
        private const string PipeName = "MT5Agent.Management.SecuritySpike";
        private const string LocalSystemSid = "S-1-5-18";

        private static string SidForEvidence(string sid)
        {
            if (String.IsNullOrEmpty(sid)) return String.Empty;
            var parts = sid.Split('-');
            if (parts.Length > 7 && parts[0] == "S" && parts[1] == "1" &&
                parts[2] == "5" && parts[3] == "21")
                return "S-1-5-21-REDACTED-" + parts[parts.Length - 1];
            return sid;
        }

        private static int Main(string[] args)
        {
            if (args.Length > 0 && args[0] == "--client") return RunClient(args);
            if (args.Length > 1 && args[0] == "--client-service")
            {
                ServiceBase.Run(new PipeClientTestService(args[1]));
                return 0;
            }
            if (args.Length > 1 && args[0] == "--service")
            {
                ServiceBase.Run(new PipeSpikeService(args[1]));
                return 0;
            }
            Console.Error.WriteLine("Use --service <allowed-sid> under SCM or --client <output-file> [expect-denied].");
            return 2;
        }

        private static int RunClient(string[] args)
        {
            if (args.Length < 2) return 2;
            var expectedDenied = args.Length > 2 && args[2] == "expect-denied";
            var output = args[1];
            var ownSid = WindowsIdentity.GetCurrent().User.Value;
            var session = System.Diagnostics.Process.GetCurrentProcess().SessionId;
            try
            {
                using (var client = new NamedPipeClientStream(".", PipeName, PipeDirection.InOut,
                    PipeOptions.None, TokenImpersonationLevel.Impersonation))
                {
                    client.Connect(4000);
                    using (var writer = new StreamWriter(client, new UTF8Encoding(false), 1024, true))
                    using (var reader = new StreamReader(client, Encoding.UTF8, false, 1024, true))
                    {
                        writer.WriteLine("{\"operation\":\"status.get\",\"claimed_sid\":\"S-1-5-21-FORGED\"}");
                        writer.Flush();
                        var response = reader.ReadLine();
                        File.WriteAllText(output, "{\"client_sid\":\"" + SidForEvidence(ownSid) + "\",\"client_session\":" + session +
                            ",\"expected_denied\":false,\"response\":" + response + "}", Encoding.UTF8);
                    }
                }
                return expectedDenied ? 3 : 0;
            }
            catch (Exception ex)
            {
                var denied = ex is UnauthorizedAccessException || (ex is IOException &&
                    (ex.HResult & 0xffff) == 5);
                File.WriteAllText(output, "{\"client_sid\":\"" + SidForEvidence(ownSid) + "\",\"client_session\":" + session +
                    ",\"expected_denied\":" + denied.ToString().ToLowerInvariant() +
                    ",\"error_type\":\"" + ex.GetType().Name + "\",\"hresult\":" + ex.HResult + "}", Encoding.UTF8);
                return expectedDenied && denied ? 0 : 4;
            }
        }

        private sealed class PipeSpikeService : ServiceBase
        {
            private readonly string _allowedSid;
            private readonly ManualResetEvent _stopping = new ManualResetEvent(false);
            private Thread _worker;

            public PipeSpikeService(string allowedSid)
            {
                _allowedSid = allowedSid;
                ServiceName = "MT5AgentManagementSecuritySpike";
                CanStop = true;
                AutoLog = true;
            }

            protected override void OnStart(string[] args)
            {
                _worker = new Thread(Serve) { IsBackground = true, Name = "Management pipe security spike" };
                _worker.Start();
            }

            protected override void OnStop()
            {
                _stopping.Set();
                try
                {
                    using (var wake = new NamedPipeClientStream(".", PipeName, PipeDirection.InOut))
                    {
                        wake.Connect(1000);
                        using (var writer = new StreamWriter(wake, new UTF8Encoding(false), 1024, true))
                        using (var reader = new StreamReader(wake, Encoding.UTF8, false, 1024, true))
                        {
                            writer.WriteLine("");
                            writer.Flush();
                            reader.ReadLine();
                        }
                    }
                }
                catch { }
                if (_worker != null) _worker.Join(5000);
            }

            private void Serve()
            {
                var selfSid = WindowsIdentity.GetCurrent().User.Value;
                var security = new PipeSecurity();
                security.SetAccessRuleProtection(true, false);
                security.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(LocalSystemSid),
                    PipeAccessRights.FullControl, AccessControlType.Allow));
                security.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(_allowedSid),
                    PipeAccessRights.ReadWrite, AccessControlType.Allow));
                while (!_stopping.WaitOne(0))
                {
                    try
                    {
                        using (var server = new NamedPipeServerStream(PipeName, PipeDirection.InOut, 1,
                            PipeTransmissionMode.Byte, PipeOptions.None, 4096, 4096, security))
                        {
                            server.WaitForConnection();
                            using (var reader = new StreamReader(server, Encoding.UTF8, false, 1024, true))
                            using (var writer = new StreamWriter(server, new UTF8Encoding(false), 1024, true))
                            {
                                var request = reader.ReadLine();
                                string actualSid = null;
                                var dispatchedAfterFailure = false;
                                var impersonationFailureDenied = !TryCaptureSid(
                                    callback => { throw new InvalidOperationException("SPIKE_IMPERSONATION_FAILURE"); },
                                    delegate { dispatchedAfterFailure = true; }, out actualSid) && !dispatchedAfterFailure;
                                actualSid = null;
                                var captured = TryCaptureSid(callback => server.RunAsClient(callback), delegate { }, out actualSid);
                                if (!captured) actualSid = null;
                                var restorationAfterCallbackException = false;
                                try
                                {
                                    server.RunAsClient(delegate { throw new InvalidOperationException("SPIKE_CALLBACK_FAILURE"); });
                                }
                                catch (InvalidOperationException) { }
                                restorationAfterCallbackException = WindowsIdentity.GetCurrent().User.Value == selfSid;
                                var afterSid = WindowsIdentity.GetCurrent().User.Value;
                                var authorized = actualSid != null && String.Equals(actualSid, _allowedSid, StringComparison.Ordinal);
                                writer.WriteLine("{\"protocol\":1,\"operation\":\"status.get\",\"actual_client_sid\":\"" +
                                    SidForEvidence(actualSid) + "\",\"service_sid_after_impersonation\":\"" + SidForEvidence(afterSid) +
                                    "\",\"service_session\":" + System.Diagnostics.Process.GetCurrentProcess().SessionId +
                                    ",\"authorized\":" + authorized.ToString().ToLowerInvariant() +
                                    ",\"claimed_sid_ignored\":" + (request != null && request.Contains("S-1-5-21-FORGED")).ToString().ToLowerInvariant() +
                                    ",\"impersonation_failure_denied\":" + impersonationFailureDenied.ToString().ToLowerInvariant() +
                                    ",\"restoration_after_callback_exception\":" + restorationAfterCallbackException.ToString().ToLowerInvariant() + "}");
                                writer.Flush();
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        if (!_stopping.WaitOne(0)) System.Diagnostics.Trace.WriteLine(
                            "Security spike pipe failed closed: " + ex.GetType().Name);
                    }
                }
            }

            private delegate void ImpersonationInvoker(PipeStreamImpersonationWorker callback);

            private static bool TryCaptureSid(ImpersonationInvoker impersonate, Action onIdentity, out string sid)
            {
                sid = null;
                try
                {
                    var capturedSid = (string)null;
                    impersonate(delegate
                    {
                        capturedSid = WindowsIdentity.GetCurrent(TokenAccessLevels.Query).User.Value;
                        onIdentity();
                    });
                    sid = capturedSid;
                    return !String.IsNullOrWhiteSpace(sid);
                }
                catch
                {
                    sid = null;
                    return false;
                }
            }
        }

        private sealed class PipeClientTestService : ServiceBase
        {
            private readonly string _output;
            private Thread _worker;

            public PipeClientTestService(string output)
            {
                _output = output;
                ServiceName = "MT5AgentManagementSecuritySpikeDeniedClient";
                CanStop = true;
                AutoLog = true;
            }

            protected override void OnStart(string[] args)
            {
                _worker = new Thread(new ThreadStart(delegate { RunClient(new[] { "--client", _output, "expect-denied" }); }))
                { IsBackground = true, Name = "Unauthorized pipe client spike" };
                _worker.Start();
            }

            protected override void OnStop()
            {
                if (_worker != null) _worker.Join(5000);
            }
        }
    }
}
