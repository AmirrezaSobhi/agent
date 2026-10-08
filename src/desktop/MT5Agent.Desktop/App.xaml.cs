using System;
using System.Windows;
using MT5Agent.Desktop.Services;
using MT5Agent.Desktop.Resources;
using MT5Agent.Desktop.ViewModels;
using MT5Agent.Desktop.Views;

namespace MT5Agent.Desktop
{
    public partial class App : Application
    {
        private ApplicationServices _services;
        private TrayService _tray;

        public void OnApplicationStartup(object sender, StartupEventArgs e)
        {
            try
            {
                var preferences = new UserPreferencesStore();
                var themeService = new ThemeService(this);
                var initialTheme = preferences.LoadTheme();
                themeService.Apply(initialTheme);

                var errors = new ErrorService();
                var managementClient = new NamedPipeManagementClient();
                var navigation = new NavigationService();
                _tray = new TrayService(preferences, Dispatcher);
                _services = new ApplicationServices(preferences, themeService, errors, managementClient, navigation, _tray);
                _services.RegisterRoutes();

                var shell = new ShellViewModel(navigation, errors);
                var window = new MainWindow(preferences, _tray) { DataContext = shell };
                _tray.Attach(window);
                _tray.ExitRequested += (exitSender, exitArgs) => window.RequestExit();
                MainWindow = window;
                window.Show();
            }
            catch (Exception)
            {
                MessageBox.Show(Strings.StartupFailure,
                    "MT5Agent Desktop", MessageBoxButton.OK, MessageBoxImage.Error);
                Shutdown(-1);
            }
        }

        public void OnApplicationExit(object sender, ExitEventArgs e)
        {
            var shell = MainWindow == null ? null : MainWindow.DataContext as IDisposable;
            if (shell != null) shell.Dispose();
            if (_services != null)
            {
                _services.Dispose();
                _services = null;
            }
            if (_tray != null) { _tray.Dispose(); _tray = null; }
        }
    }
}
