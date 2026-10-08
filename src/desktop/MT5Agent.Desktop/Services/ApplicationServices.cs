using System;
using MT5Agent.Desktop.ViewModels;

namespace MT5Agent.Desktop.Services
{
    /// <summary>Small composition root; future IPC remains behind IManagementClient.</summary>
    public sealed class ApplicationServices : IDisposable
    {
        public ApplicationServices(IUserPreferencesStore preferences, IThemeService theme, ErrorService errors,
            IManagementClient managementClient, NavigationService navigation)
        {
            Preferences = preferences;
            Theme = theme;
            Errors = errors;
            ManagementClient = managementClient;
            Navigation = navigation;
        }

        public IUserPreferencesStore Preferences { get; private set; }
        public IThemeService Theme { get; private set; }
        public ErrorService Errors { get; private set; }
        public IManagementClient ManagementClient { get; private set; }
        public NavigationService Navigation { get; private set; }

        public void RegisterRoutes()
        {
            Navigation.Register("Dashboard", () => new DashboardViewModel(ManagementClient, Errors));
            Navigation.Register("Runtime", () => new RuntimeViewModel());
            Navigation.Register("Settings", () => new SettingsViewModel(Preferences, Theme, Errors, Theme.CurrentTheme));
            Navigation.Register("Logs", () => new LogsViewModel());
            Navigation.Register("Diagnostics", () => new DiagnosticsViewModel());
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
