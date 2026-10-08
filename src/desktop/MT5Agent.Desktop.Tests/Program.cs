using System;
using System.ComponentModel;
using System.IO;
using System.IO.Pipes;
using System.Collections.Generic;
using System.Text;
using System.Web.Script.Serialization;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Media;
using MT5Agent.Desktop.Services;
using MT5Agent.Desktop.Resources;
using MT5Agent.Desktop.ViewModels;
using MT5Agent.Desktop.ViewModels.Commands;
using MT5Agent.Desktop.Views;

namespace MT5Agent.Desktop.Tests
{
    internal static class Program
    {
        private static int _passed;
        private static int _failed;

        [STAThread]
        private static int Main(string[] args)
        {
            if ((args.Length == 2 || args.Length == 3) && args[0] == "--management-ipc-smoke")
                return ManagementPipeSmoke(args[1], args.Length == 3 && args[2] == "live-runtime"
                    ? "live-mt5-runner" : "deterministic-runtime-adapter");
            Run("ViewModel property notification", PropertyNotification);
            Run("English UI resource is available", EnglishResource);
            Run("Navigation changes route and disposes previous view model", NavigationLifecycle);
            Run("Unknown route is rejected", UnknownRoute);
            Run("Theme preference persists per user path", ThemePreferencePersistence);
            Run("Theme dictionaries switch without restart", ThemeDictionarySwitch);
            Run("Shell XAML lays out all registered routes", ShellXamlLayoutsAllRoutes);
            Run("Invalid preference falls back to dark", InvalidPreferenceFallback);
            Run("RelayCommand executes action", RelayCommandExecutes);
            Run("AsyncCommand executes and resets running state", AsyncCommandExecutes);
            Run("AsyncCommand prevents duplicate concurrent execution", AsyncCommandPreventsDuplicates);
            Run("AsyncCommand cancellation is observed", AsyncCommandCancellation);
            Run("AsyncCommand disposal cancels active work", AsyncCommandDisposal);
            Run("AsyncCommand reports sanitized error state", AsyncCommandErrorState);
            Run("Settings command persists and applies theme", SettingsCommandPersistsTheme);
            Run("Dashboard keeps unobserved runtime data unavailable", DashboardOfflineState);
            Run("Dashboard exposes a failed status request", DashboardErrorState);
            Run("Dashboard distinguishes stale status from a live response", DashboardStaleStatus);
            Run("Dashboard background request leaves Dispatcher responsive", DispatcherResponsiveness);
            Run("Application service disposal releases the active page", ApplicationServiceDisposal);
            Run("Management IPC serializes and deserializes the v1 status contract", ManagementClientReadsTypedStatus);
            Run("Management IPC fails closed on protocol mismatch", ManagementClientRejectsVersionMismatch);
            Run("Management IPC rejects oversized response frames", ManagementClientRejectsOversizedFrame);
            Run("Management IPC cancellation interrupts a pending response", ManagementClientCancellation);
            Run("Management IPC reports service unavailable without blocking UI", ManagementClientUnavailable);
            Run("Management IPC reconnects after service becomes available", ManagementClientReconnects);
            Run("Management IPC handles concurrent status requests", ManagementClientConcurrentRequests);
            Run("Management IPC marks delayed and clock-skewed observations stale", ManagementClientMarksStaleData);
            Run("Dashboard presents fresh, typed management status", DashboardObservedStatus);

            Console.WriteLine("RESULT: {0} passed; {1} failed.", _passed, _failed);
            return _failed == 0 ? 0 : 1;
        }

        private static void Run(string name, Action test)
        {
            try { test(); _passed++; Console.WriteLine("PASS " + name); }
            catch (Exception ex) { _failed++; Console.Error.WriteLine("FAIL " + name + ": " + ex); }
        }

        private static void PropertyNotification()
        {
            var vm = new ProbeViewModel();
            string changed = null;
            vm.PropertyChanged += (sender, args) => changed = args.PropertyName;
            vm.Value = 42;
            Assert(vm.Value == 42 && changed == "Value", "PropertyChanged should include the changed property.");
            changed = null;
            vm.Value = 42;
            Assert(changed == null, "An unchanged value should not raise a notification.");
        }

        private static void EnglishResource()
        {
            Assert(Strings.NavDashboard == "Dashboard", "English resource did not load from the assembly.");
        }

        private static void NavigationLifecycle()
        {
            var nav = new NavigationService();
            nav.Register("first", () => new ProbeViewModel());
            nav.Register("second", () => new ProbeViewModel());
            nav.Navigate("first");
            var first = nav.CurrentViewModel;
            nav.Navigate("second");
            Assert(nav.CurrentRoute == "second", "Current route was not updated.");
            Assert(first.IsDisposed, "Previous view model was not disposed.");
            nav.Dispose();
        }

        private static void UnknownRoute()
        {
            var nav = new NavigationService();
            AssertThrows<ArgumentOutOfRangeException>(() => nav.Navigate("missing"));
            nav.Dispose();
        }

        private static void ThemePreferencePersistence()
        {
            WithTempDirectory(directory =>
            {
                var store = new UserPreferencesStore(Path.Combine(directory, "prefs.v1"));
                store.SaveThemeAsync(ThemePreference.Light, CancellationToken.None).GetAwaiter().GetResult();
                Assert(store.LoadTheme() == ThemePreference.Light, "Theme did not persist.");
            });
        }

        private static void ThemeDictionarySwitch()
        {
            var application = EnsureApplication();
            var theme = new ThemeService(application);
            theme.Apply(ThemePreference.Dark);
            var dark = (SolidColorBrush)application.TryFindResource("CanvasBrush");
            theme.Apply(ThemePreference.Light);
            var light = (SolidColorBrush)application.TryFindResource("CanvasBrush");
            Assert(theme.CurrentTheme == ThemePreference.Light, "Theme service did not update the active theme.");
            Assert(dark.Color != light.Color, "Light and dark resources did not change.");
        }

        private static void InvalidPreferenceFallback()
        {
            WithTempDirectory(directory =>
            {
                var path = Path.Combine(directory, "prefs.v1");
                File.WriteAllText(path, "not-a-theme");
                Assert(new UserPreferencesStore(path).LoadTheme() == ThemePreference.Dark, "Invalid preference did not use safe default.");
            });
        }

        private static void RelayCommandExecutes()
        {
            var value = 0;
            var command = new RelayCommand(parameter => value = (int)parameter);
            Assert(command.CanExecute(7), "Command should be executable.");
            command.Execute(7);
            Assert(value == 7, "Command action was not called.");
        }

        private static void AsyncCommandExecutes()
        {
            var errors = new ErrorService();
            var count = 0;
            var command = new AsyncCommand(token => { count++; return Task.FromResult(0); }, errors);
            command.ExecuteAsync(CancellationToken.None).GetAwaiter().GetResult();
            Assert(count == 1 && !command.IsRunning && command.CanExecute(null), "Async command did not complete cleanly.");
            command.Dispose(); errors.Dispose();
        }

        private static void AsyncCommandCancellation()
        {
            var errors = new ErrorService();
            var started = new TaskCompletionSource<bool>();
            var command = new AsyncCommand(async token =>
            {
                started.SetResult(true);
                await Task.Delay(Timeout.Infinite, token);
            }, errors);
            using (var cancellation = new CancellationTokenSource())
            {
                var work = command.ExecuteAsync(cancellation.Token);
                started.Task.GetAwaiter().GetResult();
                cancellation.Cancel();
                work.GetAwaiter().GetResult();
            }
            Assert(!command.IsRunning && !errors.HasError, "Cancellation should finish without an error.");
            command.Dispose(); errors.Dispose();
        }

        private static void AsyncCommandPreventsDuplicates()
        {
            var errors = new ErrorService();
            var started = new TaskCompletionSource<bool>();
            var release = new TaskCompletionSource<bool>();
            var count = 0;
            var command = new AsyncCommand(async token =>
            {
                Interlocked.Increment(ref count);
                started.SetResult(true);
                await release.Task;
            }, errors);
            var first = command.ExecuteAsync(CancellationToken.None);
            started.Task.GetAwaiter().GetResult();
            Assert(!command.CanExecute(null), "Command remained available during work.");
            command.ExecuteAsync(CancellationToken.None).GetAwaiter().GetResult();
            Assert(count == 1, "A duplicate command started while the first was active.");
            release.SetResult(true);
            first.GetAwaiter().GetResult();
            command.Dispose(); errors.Dispose();
        }

        private static void AsyncCommandDisposal()
        {
            var errors = new ErrorService();
            var started = new TaskCompletionSource<bool>();
            var command = new AsyncCommand(async token =>
            {
                started.SetResult(true);
                await Task.Delay(Timeout.Infinite, token);
            }, errors);
            var work = command.ExecuteAsync(CancellationToken.None);
            started.Task.GetAwaiter().GetResult();
            command.Dispose();
            work.GetAwaiter().GetResult();
            Assert(!command.IsRunning && !errors.HasError, "Dispose did not cancel pending work cleanly.");
            errors.Dispose();
        }

        private static void AsyncCommandErrorState()
        {
            var errors = new ErrorService();
            var command = new AsyncCommand(token => { throw new IOException("synthetic-private-detail"); }, errors);
            command.ExecuteAsync(CancellationToken.None).GetAwaiter().GetResult();
            Assert(errors.HasError, "Error handler was not invoked.");
            Assert(!errors.Message.Contains("synthetic-private-detail"), "Raw exception detail was exposed.");
            command.Dispose(); errors.Dispose();
        }

        private static void SettingsCommandPersistsTheme()
        {
            WithTempDirectory(directory =>
            {
                var store = new UserPreferencesStore(Path.Combine(directory, "prefs.v1"));
                var theme = new FakeThemeService();
                var errors = new ErrorService();
                var vm = new SettingsViewModel(store, theme, errors, ThemePreference.Dark);
                vm.ToggleThemeCommand.ExecuteAsync(CancellationToken.None).GetAwaiter().GetResult();
                Assert(vm.Theme == ThemePreference.Light && store.LoadTheme() == ThemePreference.Light, "Settings did not persist Light theme.");
                Assert(theme.CurrentTheme == ThemePreference.Light && theme.ApplyCount == 1, "Theme service was not updated.");
                vm.Dispose(); errors.Dispose();
            });
        }

        private static void DashboardOfflineState()
        {
            var client = new FakeManagementClient();
            var errors = new ErrorService();
            var vm = new DashboardViewModel(client, errors);
            vm.RefreshAsync(CancellationToken.None).GetAwaiter().GetResult();
            Assert(vm.Message == "No secure connection is configured.", "Dashboard did not explain missing data.");
            Assert(vm.Cards[0].Value == "Unknown" && vm.Cards[4].Value == "Disconnected" &&
                vm.Cards[5].Value == "Not configured", "Dashboard fabricated an observed state.");
            Assert(!errors.HasError && !vm.IsLoading, "Offline state should not be a thrown error.");
            vm.Dispose(); errors.Dispose();
        }

        private static void DashboardErrorState()
        {
            var client = new FakeManagementClient { Handler = token => Task.FromException<ManagementStatus>(new IOException("synthetic-detail")) };
            var errors = new ErrorService();
            var vm = new DashboardViewModel(client, errors);
            vm.RefreshAsync(CancellationToken.None).GetAwaiter().GetResult();
            Assert(vm.InlineError != null && errors.HasError && !vm.IsLoading, "Dashboard error state was not surfaced.");
            Assert(!errors.Message.Contains("synthetic-detail"), "Raw exception was exposed.");
            vm.Dispose(); errors.Dispose();
        }

        private static void DispatcherResponsiveness()
        {
            EnsureApplication();
            var errors = new ErrorService();
            var vm = new DashboardViewModel(new UnavailableManagementClient(), errors);
            var refresh = vm.RefreshAsync(CancellationToken.None);
            Assert(!refresh.IsCompleted, "Simulated status request should remain asynchronous.");

            var frame = new System.Windows.Threading.DispatcherFrame();
            var timer = new System.Windows.Threading.DispatcherTimer { Interval = TimeSpan.FromMilliseconds(30) };
            var dispatcherProcessed = false;
            timer.Tick += (sender, args) =>
            {
                dispatcherProcessed = true;
                timer.Stop();
                frame.Continue = false;
            };
            timer.Start();
            System.Windows.Threading.Dispatcher.PushFrame(frame);
            Assert(dispatcherProcessed && !refresh.IsCompleted, "Dispatcher did not process input while the request was pending.");
            refresh.GetAwaiter().GetResult();
            vm.Dispose(); errors.Dispose();
        }

        private static void ShellXamlLayoutsAllRoutes()
        {
            var app = EnsureApplication();
            Assert(app.TryFindResource("BodyText") != null, "Application style dictionary did not expose BodyText.");
            var theme = new ThemeService(app);
            theme.Apply(ThemePreference.Dark);
            var navigation = new NavigationService();
            var errors = new ErrorService();
            var services = new ApplicationServices(new UserPreferencesStore(Path.Combine(Path.GetTempPath(), "mt5agent-shell-prefs")),
                theme, errors, new UnavailableManagementClient(), navigation);
            services.RegisterRoutes();
            var shell = new ShellViewModel(navigation, errors);
            var window = new MainWindow { DataContext = shell };
            window.Measure(new Size(1180, 760));
            window.Arrange(new Rect(0, 0, 1180, 760));
            window.UpdateLayout();
            foreach (var item in shell.NavigationItems)
            {
                shell.Navigate(item.Route);
                window.UpdateLayout();
                Assert(shell.CurrentRoute == item.Route, "A registered navigation route failed to load.");
            }
            window.DataContext = null;
            shell.Dispose();
            services.Dispose();
            window.Close();
        }

        private static Application EnsureApplication()
        {
            if (Application.Current != null) return Application.Current;
            var app = new MT5Agent.Desktop.App();
            app.InitializeComponent();
            return app;
        }

        private static void ApplicationServiceDisposal()
        {
            var navigation = new NavigationService();
            var errors = new ErrorService();
            var services = new ApplicationServices(new UserPreferencesStore(Path.Combine(Path.GetTempPath(), "mt5agent-disposal-prefs")),
                new FakeThemeService(), errors, new UnavailableManagementClient(), navigation);
            services.RegisterRoutes();
            var shell = new ShellViewModel(navigation, errors);
            var activePage = navigation.CurrentViewModel;
            shell.Dispose();
            services.Dispose();
            Assert(activePage.IsDisposed && navigation.CurrentViewModel == null, "Shutdown did not dispose the active page.");
        }

        private static void ManagementClientReadsTypedStatus()
        {
            ManagementStatus result = null;
            var server = StartMockPipe(1, request =>
            {
                Assert(Convert.ToInt32(request["protocol_version"]) == 1, "Request protocol version was not serialized.");
                Assert((string)request["operation"] == "status.get", "Unexpected operation was sent.");
                var id = (string)request["request_id"];
                return StatusResponse(id, (string)request["correlation_id"], 1, "AGENT_RUNNING");
            }, 0);
            result = new NamedPipeManagementClient().GetStatusAsync(CancellationToken.None).GetAwaiter().GetResult();
            Assert(server.Join(3000), "Mock server did not finish.");
            Assert(result.IsObserved && result.AgentState == "AGENT_RUNNING" && result.Mt5Connected,
                "Typed status projection was not populated from the response.");
            Assert(result.ServiceState == "UNKNOWN" && result.ManagementState == "CONNECTED" &&
                result.SourceIdentity == "MT5Agent.AgentCore", "Status provenance or unknown service state was lost.");
            Assert(result.CentralState == "NOT_CONFIGURED" && result.TradingCapability == "UNSUPPORTED",
                "Local Setup or trading capability was falsely enabled.");
        }

        private static void ManagementClientRejectsVersionMismatch()
        {
            var server = StartMockPipe(1, request => StatusResponse((string)request["request_id"],
                (string)request["correlation_id"], 77, "AGENT_RUNNING"), 0);
            try
            {
                new NamedPipeManagementClient().GetStatusAsync(CancellationToken.None).GetAwaiter().GetResult();
                throw new InvalidOperationException("Protocol mismatch was accepted.");
            }
            catch (ManagementIpcException ex) { Assert(ex.Code == "PROTOCOL_MISMATCH", "Wrong version error code."); }
            Assert(server.Join(3000), "Mock server did not finish.");
        }

        private static void ManagementClientRejectsOversizedFrame()
        {
            var server = StartMockPipe(1, request =>
            {
                var oversized = StatusResponse((string)request["request_id"], (string)request["correlation_id"], 1, "AGENT_RUNNING");
                ((Dictionary<string, object>)oversized["data"])["padding"] = new string('x', 66000);
                return oversized;
            }, 0);
            try
            {
                new NamedPipeManagementClient().GetStatusAsync(CancellationToken.None).GetAwaiter().GetResult();
                throw new InvalidOperationException("Oversized response was accepted.");
            }
            catch (ManagementIpcException ex) { Assert(ex.Code == "MESSAGE_TOO_LARGE", "Wrong oversize error code."); }
            server.Join(3000);
        }

        private static void ManagementClientCancellation()
        {
            var server = StartMockPipe(1, request => StatusResponse(
                (string)request["request_id"], (string)request["correlation_id"], 1, "AGENT_RUNNING"), 1200);
            using (var cancellation = new CancellationTokenSource(100))
            {
                try
                {
                    new NamedPipeManagementClient().GetStatusAsync(cancellation.Token).GetAwaiter().GetResult();
                    throw new InvalidOperationException("Cancellation was not observed.");
                }
                catch (OperationCanceledException) { }
            }
            server.Join(3000);
        }

        private static void ManagementClientUnavailable()
        {
            try
            {
                new NamedPipeManagementClient().GetStatusAsync(CancellationToken.None).GetAwaiter().GetResult();
                throw new InvalidOperationException("Missing Agent service unexpectedly returned status.");
            }
            catch (ManagementIpcException ex)
            {
                Assert(ex.Code == "PIPE_NOT_FOUND" || ex.Code == "TIMEOUT", "Wrong service-offline error.");
            }
        }

        private static void ManagementClientReconnects()
        {
            ManagementClientUnavailable();
            var server = StartMockPipe(1, request => StatusResponse((string)request["request_id"],
                (string)request["correlation_id"], 1, "AGENT_RUNNING"), 0);
            var result = new NamedPipeManagementClient().GetStatusAsync(CancellationToken.None).GetAwaiter().GetResult();
            Assert(result.IsObserved, "Client did not reconnect after the service became available.");
            Assert(server.Join(3000), "Reconnect mock server did not finish.");
        }

        private static void ManagementClientConcurrentRequests()
        {
            var server = StartMockPipe(3, request => StatusResponse((string)request["request_id"],
                (string)request["correlation_id"], 1, "AGENT_RUNNING"), 0);
            var client = new NamedPipeManagementClient();
            var tasks = new[] { client.GetStatusAsync(CancellationToken.None), client.GetStatusAsync(CancellationToken.None),
                client.GetStatusAsync(CancellationToken.None) };
            Task.WhenAll(tasks).GetAwaiter().GetResult();
            Assert(server.Join(3000), "Mock server did not finish all concurrent requests.");
            foreach (var task in tasks) Assert(task.Result.IsObserved, "A concurrent request failed.");
        }

        private static void ManagementClientMarksStaleData()
        {
            var oldServer = StartMockPipe(1, request => StatusResponse((string)request["request_id"],
                (string)request["correlation_id"], 1, "AGENT_RUNNING", DateTime.UtcNow.AddSeconds(-20)), 0);
            var oldStatus = new NamedPipeManagementClient().GetStatusAsync(CancellationToken.None).GetAwaiter().GetResult();
            Assert(oldStatus.IsStale && oldStatus.Freshness == "STALE", "Old observation timestamp was shown as fresh.");
            Assert(oldServer.Join(3000), "Delayed observation server did not finish.");

            var futureServer = StartMockPipe(1, request => StatusResponse((string)request["request_id"],
                (string)request["correlation_id"], 1, "AGENT_RUNNING", DateTime.UtcNow.AddMinutes(5)), 0);
            var futureStatus = new NamedPipeManagementClient().GetStatusAsync(CancellationToken.None).GetAwaiter().GetResult();
            Assert(futureStatus.IsStale && futureStatus.Freshness == "STALE", "Clock-skewed future timestamp was shown as fresh.");
            Assert(futureServer.Join(3000), "Clock-skewed observation server did not finish.");
        }

        private static int ManagementPipeSmoke(string evidencePath, string runtimeEvidence)
        {
            ManagementStatus status = null;
            try
            {
                var timer = System.Diagnostics.Stopwatch.StartNew();
                status = new NamedPipeManagementClient().GetStatusAsync(CancellationToken.None).GetAwaiter().GetResult();
                timer.Stop();
                if (!status.IsObserved || status.AgentState != "AGENT_RUNNING")
                    throw new InvalidOperationException("AGENT_STATUS_NOT_RUNNING");
                if (status.WorkerState != "WORKER_READY" || !status.Mt5Connected)
                    throw new InvalidOperationException("WORKER_OR_MT5_STATUS_NOT_READY");
                var evidence = "IPC_SMOKE_PASS session=" + System.Diagnostics.Process.GetCurrentProcess().SessionId +
                    " protocol=1 agent=" + status.AgentState + " worker=" + status.WorkerState +
                    " mt5=" + status.Mt5State + " freshness=" + status.Freshness +
                    " source=" + status.SourceIdentity + " ipc_round_trip_ms=" + timer.ElapsedMilliseconds +
                    " runtime_evidence=" + runtimeEvidence;
                File.WriteAllText(evidencePath, evidence);
                Console.WriteLine(evidence);
                return 0;
            }
            catch (Exception ex)
            {
                var evidence = "IPC_SMOKE_FAIL type=" + ex.GetType().Name +
                    (ex is ManagementIpcException ? " code=" + ((ManagementIpcException)ex).Code :
                        (ex is InvalidOperationException ? " check=" + ex.Message : "")) +
                    (status == null ? "" : " agent=" + status.AgentState + " worker=" + status.WorkerState +
                        " mt5=" + status.Mt5State + " freshness=" + status.Freshness + " source=" + status.SourceIdentity);
                File.WriteAllText(evidencePath, evidence);
                Console.Error.WriteLine(evidence);
                return 1;
            }
        }

        private static void DashboardObservedStatus()
        {
            var client = new FakeManagementClient
            {
                Handler = token => Task.FromResult(new ManagementStatus
                {
                    IsObserved = true, AgentState = "AGENT_RUNNING", WorkerState = "WORKER_READY",
                    RuntimeState = "MT5_CONNECTED", Mt5State = "CONNECTED", Mt5Connected = true,
                    ServiceState = "UNKNOWN", ManagementState = "CONNECTED", SourceIdentity = "MT5Agent.AgentCore",
                    CentralState = "NOT_CONFIGURED", TradingCapability = "UNSUPPORTED",
                    TradingAuthorized = "UNKNOWN", TradingReadiness = "UNAVAILABLE",
                    ObservedAtUtc = DateTime.UtcNow, IsStale = false
                })
            };
            var errors = new ErrorService();
            var vm = new DashboardViewModel(client, errors);
            vm.RefreshAsync(CancellationToken.None).GetAwaiter().GetResult();
            Assert(vm.Cards[0].Value == Strings.Unknown && vm.Cards[1].Value == Strings.Responsive &&
                vm.Cards[2].Value == Strings.Ready && vm.Cards[3].Value == Strings.Connected,
                "Dashboard did not display actual typed status fields without inferring Service state.");
            Assert(vm.Cards[4].Value == Strings.Connected && vm.Cards[5].Value == Strings.NotConfigured &&
                vm.Cards[6].Value == "UNSUPPORTED",
                "Dashboard enabled central/trading capabilities without evidence.");
            Assert(vm.FreshnessText.StartsWith("Observed ", StringComparison.Ordinal), "Freshness was not displayed.");
            vm.Dispose(); errors.Dispose();
        }

        private static void DashboardStaleStatus()
        {
            var client = new FakeManagementClient
            {
                Handler = token => Task.FromResult(new ManagementStatus
                {
                    IsObserved = true, IsStale = true, ServiceState = "UNKNOWN", AgentState = "RESPONSIVE",
                    WorkerState = "WORKER_READY", Mt5State = "CONNECTED", ManagementState = "CONNECTED",
                    CentralState = "NOT_CONFIGURED", TradingCapability = "UNSUPPORTED",
                    TradingAuthorized = "UNKNOWN", TradingReadiness = "UNAVAILABLE",
                    SourceIdentity = "MT5Agent.AgentCore", ObservedAtUtc = DateTime.UtcNow.AddMinutes(-1)
                })
            };
            var errors = new ErrorService();
            var vm = new DashboardViewModel(client, errors);
            vm.RefreshAsync(CancellationToken.None).GetAwaiter().GetResult();
            Assert(vm.Message == Strings.StatusStale && vm.Cards[1].Value == Strings.Stale,
                "Stale source data was displayed as current.");
            Assert(vm.Cards[4].Value == Strings.Connected, "Fresh IPC delivery should remain distinct from stale source data.");
            vm.Dispose(); errors.Dispose();
        }

        private static Thread StartMockPipe(int count, Func<Dictionary<string, object>, Dictionary<string, object>> responseFactory,
            int delayBeforeResponse)
        {
            var thread = new Thread(new ThreadStart(delegate
            {
                var serializer = new JavaScriptSerializer();
                for (var index = 0; index < count; index++)
                {
                    try
                    {
                        using (var server = new NamedPipeServerStream(NamedPipeManagementClient.PipeName,
                            PipeDirection.InOut, 1, PipeTransmissionMode.Message, PipeOptions.Asynchronous))
                        {
                            server.WaitForConnection();
                            server.ReadMode = PipeTransmissionMode.Message;
                            var requestBytes = ReadPipeMessage(server);
                            var request = serializer.Deserialize<Dictionary<string, object>>(Encoding.UTF8.GetString(requestBytes));
                            if (delayBeforeResponse > 0) Thread.Sleep(delayBeforeResponse);
                            var bytes = Encoding.UTF8.GetBytes(serializer.Serialize(responseFactory(request)));
                            server.Write(bytes, 0, bytes.Length);
                            server.Flush();
                            if (bytes.Length <= NamedPipeManagementClient.MaxMessageBytes)
                            {
                                var acknowledgement = serializer.Deserialize<Dictionary<string, object>>(
                                    Encoding.UTF8.GetString(ReadPipeMessage(server)));
                                Assert((string)acknowledgement["ack"] == (string)request["request_id"],
                                    "Client acknowledgement did not match the response request id.");
                            }
                        }
                    }
                    catch (IOException) { if (delayBeforeResponse == 0) throw; }
                }
            }));
            thread.IsBackground = true;
            thread.Start();
            return thread;
        }

        private static byte[] ReadPipeMessage(PipeStream pipe)
        {
            using (var output = new MemoryStream())
            {
                var buffer = new byte[4096];
                do
                {
                    var count = pipe.Read(buffer, 0, buffer.Length);
                    if (count == 0) throw new EndOfStreamException();
                    output.Write(buffer, 0, count);
                } while (!pipe.IsMessageComplete);
                return output.ToArray();
            }
        }

        private static Dictionary<string, object> StatusResponse(string requestId, string correlationId,
            int version, string agentState, DateTime? observedAtUtc = null)
        {
            var observed = observedAtUtc ?? DateTime.UtcNow;
            return new Dictionary<string, object>
            {
                { "protocol_version", version }, { "request_id", requestId }, { "correlation_id", correlationId },
                { "result", "ok" }, { "code", "OK" }, { "message", "Status observed." },
                { "observed_at_utc", observed.ToString("o") },
                { "data", new Dictionary<string, object>
                    {
                        { "observed_at_utc", observed.ToString("o") }, { "service_state", "UNKNOWN" },
                        { "source_identity", "MT5Agent.AgentCore" }, { "freshness", "FRESH" },
                        { "agent_state", agentState }, { "worker_available", true }, { "worker_state", "WORKER_READY" },
                        { "agent_lifecycle_state", "RUNNING" }, { "runtime_state", "MT5_CONNECTED" },
                        { "mt5_state", "CONNECTED" }, { "mt5_connected", true },
                        { "central_state", "NOT_CONFIGURED" }, { "trading_capability", "UNSUPPORTED" },
                        { "trading_authorized", "UNKNOWN" }, { "trading_readiness", "UNAVAILABLE" }
                    }
                }
            };
        }

        private static void WithTempDirectory(Action<string> action)
        {
            var directory = Path.Combine(Path.GetTempPath(), "mt5agent-desktop-tests-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(directory);
            try { action(directory); }
            finally { if (Directory.Exists(directory)) Directory.Delete(directory, true); }
        }

        private static void Assert(bool condition, string message)
        {
            if (!condition) throw new InvalidOperationException(message);
        }

        private static void AssertThrows<T>(Action action) where T : Exception
        {
            try { action(); }
            catch (T) { return; }
            throw new InvalidOperationException("Expected " + typeof(T).Name + ".");
        }

        private sealed class ProbeViewModel : ViewModelBase
        {
            private int _value;
            public int Value { get { return _value; } set { SetProperty(ref _value, value); } }
        }
    }
}
