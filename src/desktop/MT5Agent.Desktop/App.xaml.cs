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

        public void OnApplicationStartup(object sender, StartupEventArgs e)
        {
            try
            {
                var preferences = new UserPreferencesStore();
                var themeService = new ThemeService(this);
                var initialTheme = preferences.LoadTheme();
                themeService.Apply(initialTheme);

                var errors = new ErrorService();
                var managementClient = new UnavailableManagementClient();
                var navigation = new NavigationService();
                _services = new ApplicationServices(preferences, themeService, errors, managementClient, navigation);
                _services.RegisterRoutes();

                var shell = new ShellViewModel(navigation, errors);
                var window = new MainWindow { DataContext = shell };
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
        }
    }
}
