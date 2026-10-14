using System;
using MT5Agent.Desktop.ViewModels;

namespace MT5Agent.Desktop.Services
{
    /// <summary>Small composition root; future IPC remains behind IManagementClient.</summary>
    public sealed class ApplicationServices : IDisposable
    {
        private readonly IServiceControlClient _serviceControl;
        private readonly Func<ServiceAction, bool> _confirmServiceAction;
        public ApplicationServices(IUserPreferencesStore preferences, IThemeService theme, ErrorService errors,
            IManagementClient managementClient, NavigationService navigation)
            : this(preferences, theme, errors, managementClient, navigation, null) { }

        public ApplicationServices(IUserPreferencesStore preferences, IThemeService theme, ErrorService errors,
            IManagementClient managementClient, NavigationService navigation, IDesktopNotifier notifier)
            : this(preferences, theme, errors, managementClient, navigation, notifier, null, null) { }

        public ApplicationServices(IUserPreferencesStore preferences, IThemeService theme, ErrorService errors,
            IManagementClient managementClient, NavigationService navigation, IDesktopNotifier notifier,
            IServiceControlClient serviceControl, Func<ServiceAction, bool> confirmServiceAction)
        {
            Preferences = preferences;
            Theme = theme;
            Errors = errors;
            ManagementClient = managementClient;
            Navigation = navigation;
            Notifier = notifier;
            _serviceControl = serviceControl;
            _confirmServiceAction = confirmServiceAction;
        }

        public IUserPreferencesStore Preferences { get; private set; }
        public IThemeService Theme { get; private set; }
        public ErrorService Errors { get; private set; }
        public IManagementClient ManagementClient { get; private set; }
        public NavigationService Navigation { get; private set; }
        public IDesktopNotifier Notifier { get; private set; }

        public void RegisterRoutes()
        {
            Navigation.Register("Dashboard", () => new DashboardViewModel(ManagementClient, Errors, Preferences, Notifier,
                _serviceControl, _confirmServiceAction));
            Navigation.Register("Runtime", () => new RuntimeViewModel(ManagementClient, Errors));
            Navigation.Register("Settings", () => new SettingsViewModel(Preferences, Theme, Errors, Preferences.Load()));
            Navigation.Register("Logs", () => new LogsViewModel(ManagementClient, Errors));
            Navigation.Register("Diagnostics", () => new DiagnosticsViewModel(ManagementClient, Errors));
            Navigation.Register("About", () => new AboutViewModel());
            Navigation.Register("Accounts", () => new UnavailableViewModel("Accounts", Resources.Strings.PageAccountsDescription));
            Navigation.Register("Security", () => new UnavailableViewModel("Security", Resources.Strings.PageSecurityDescription));
            Navigation.Register("Updates", () => new UnavailableViewModel("Updates", Resources.Strings.PageUpdatesDescription));
            Navigation.Register("Support", () => new UnavailableViewModel("Support", Resources.Strings.PageSupportDescription));
        }

        public void Dispose()
        {
            if (Navigation != null) Navigation.Dispose();
            if (Errors != null) Errors.Dispose();
        }
    }
}
