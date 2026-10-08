using System;
using System.ComponentModel;
using System.IO;
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
        private static int Main()
        {
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
            Run("Dashboard background request leaves Dispatcher responsive", DispatcherResponsiveness);
            Run("Application service disposal releases the active page", ApplicationServiceDisposal);

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
            Assert(vm.Cards[0].Value == "Unavailable" && vm.Cards[3].Value == "Not configured", "Dashboard fabricated an observed state.");
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
