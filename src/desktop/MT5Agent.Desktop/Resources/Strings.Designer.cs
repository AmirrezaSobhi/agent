using System.Globalization;
using System.Resources;

namespace MT5Agent.Desktop.Resources
{
    public static class Strings
    {
        private static readonly ResourceManager Manager =
            new ResourceManager("MT5Agent.Desktop.Resources.Strings", typeof(Strings).Assembly);

        public static CultureInfo Culture { get; set; }

        private static string Get(string name)
        {
            return Manager.GetString(name, Culture) ?? name;
        }

        public static string AppName { get { return Get("AppName"); } }
        public static string AppSubtitle { get { return Get("AppSubtitle"); } }
        public static string NavDashboard { get { return Get("NavDashboard"); } }
        public static string NavRuntime { get { return Get("NavRuntime"); } }
        public static string NavAccounts { get { return Get("NavAccounts"); } }
        public static string NavSecurity { get { return Get("NavSecurity"); } }
        public static string NavSettings { get { return Get("NavSettings"); } }
        public static string NavLogs { get { return Get("NavLogs"); } }
        public static string NavDiagnostics { get { return Get("NavDiagnostics"); } }
        public static string NavUpdates { get { return Get("NavUpdates"); } }
        public static string NavSupport { get { return Get("NavSupport"); } }
        public static string NavAbout { get { return Get("NavAbout"); } }
        public static string EyebrowLocalClient { get { return Get("EyebrowLocalClient"); } }
        public static string DashboardTitle { get { return Get("DashboardTitle"); } }
        public static string DashboardDescription { get { return Get("DashboardDescription"); } }
        public static string LocalSetup { get { return Get("LocalSetup"); } }
        public static string NotConnected { get { return Get("NotConnected"); } }
        public static string Unavailable { get { return Get("Unavailable"); } }
        public static string NotConfigured { get { return Get("NotConfigured"); } }
        public static string NotImplemented { get { return Get("NotImplemented"); } }
        public static string RefreshStatus { get { return Get("RefreshStatus"); } }
        public static string NoSecureChannel { get { return Get("NoSecureChannel"); } }
        public static string ServiceStatus { get { return Get("ServiceStatus"); } }
        public static string WorkerStatus { get { return Get("WorkerStatus"); } }
        public static string Mt5Status { get { return Get("Mt5Status"); } }
        public static string CentralStatus { get { return Get("CentralStatus"); } }
        public static string TradingStatus { get { return Get("TradingStatus"); } }
        public static string PageRuntimeDescription { get { return Get("PageRuntimeDescription"); } }
        public static string PageLogsDescription { get { return Get("PageLogsDescription"); } }
        public static string PageDiagnosticsDescription { get { return Get("PageDiagnosticsDescription"); } }
        public static string PageAccountsDescription { get { return Get("PageAccountsDescription"); } }
        public static string PageSecurityDescription { get { return Get("PageSecurityDescription"); } }
        public static string PageUpdatesDescription { get { return Get("PageUpdatesDescription"); } }
        public static string PageSupportDescription { get { return Get("PageSupportDescription"); } }
        public static string SettingsTitle { get { return Get("SettingsTitle"); } }
        public static string ThemeDescription { get { return Get("ThemeDescription"); } }
        public static string ThemeDark { get { return Get("ThemeDark"); } }
        public static string ThemeLight { get { return Get("ThemeLight"); } }
        public static string ThemeToggle { get { return Get("ThemeToggle"); } }
        public static string Saved { get { return Get("Saved"); } }
        public static string Loading { get { return Get("Loading"); } }
        public static string ErrorTitle { get { return Get("ErrorTitle"); } }
        public static string Retry { get { return Get("Retry"); } }
        public static string AboutDescription { get { return Get("AboutDescription"); } }
        public static string BuildLabel { get { return Get("BuildLabel"); } }
        public static string ThemeSaveError { get { return Get("ThemeSaveError"); } }
        public static string RefreshError { get { return Get("RefreshError"); } }
        public static string NoLogs { get { return Get("NoLogs"); } }
        public static string LogsTitle { get { return Get("LogsTitle"); } }
        public static string DiagnosticsTitle { get { return Get("DiagnosticsTitle"); } }
        public static string AboutTitle { get { return Get("AboutTitle"); } }
        public static string NotConnectedDetail { get { return Get("NotConnectedDetail"); } }
        public static string CurrentStatus { get { return Get("CurrentStatus"); } }
        public static string SectionRuntime { get { return Get("SectionRuntime"); } }
        public static string SectionSettings { get { return Get("SectionSettings"); } }
        public static string SectionOperations { get { return Get("SectionOperations"); } }
        public static string SectionHealth { get { return Get("SectionHealth"); } }
        public static string SectionProduct { get { return Get("SectionProduct"); } }
        public static string ThemeSetting { get { return Get("ThemeSetting"); } }
        public static string NoRuntimeData { get { return Get("NoRuntimeData"); } }
        public static string NoLogFilesRead { get { return Get("NoLogFilesRead"); } }
        public static string DiagnosticsNoCollection { get { return Get("DiagnosticsNoCollection"); } }
        public static string PreferencesScope { get { return Get("PreferencesScope"); } }
        public static string ServiceUnavailableDetail { get { return Get("ServiceUnavailableDetail"); } }
        public static string RuntimeUnavailableDetail { get { return Get("RuntimeUnavailableDetail"); } }
        public static string Mt5UnavailableDetail { get { return Get("Mt5UnavailableDetail"); } }
        public static string CentralLocalDetail { get { return Get("CentralLocalDetail"); } }
        public static string TradingUnsupportedDetail { get { return Get("TradingUnsupportedDetail"); } }
        public static string StartupFailure { get { return Get("StartupFailure"); } }
        public static string OperationError { get { return Get("OperationError"); } }
        public static string NoRuntimeStatusQueried { get { return Get("NoRuntimeStatusQueried"); } }
        public static string TechnologyLabel { get { return Get("TechnologyLabel"); } }
        public static string NoDiagnosticsCollected { get { return Get("NoDiagnosticsCollected"); } }
        public static string NavPreview { get { return Get("NavPreview"); } }
        public static string ThemeAutomationName { get { return Get("ThemeAutomationName"); } }
        public static string AgentStatus { get { return Get("AgentStatus"); } }
        public static string AgentUnavailableDetail { get { return Get("AgentUnavailableDetail"); } }
        public static string ServiceRunning { get { return Get("ServiceRunning"); } }
        public static string ServiceRunningDetail { get { return Get("ServiceRunningDetail"); } }
        public static string AgentResponsiveDetail { get { return Get("AgentResponsiveDetail"); } }
        public static string Connected { get { return Get("Connected"); } }
        public static string Disconnected { get { return Get("Disconnected"); } }
        public static string Mt5ConnectedDetail { get { return Get("Mt5ConnectedDetail"); } }
        public static string Mt5DisconnectedDetail { get { return Get("Mt5DisconnectedDetail"); } }
        public static string StatusCurrent { get { return Get("StatusCurrent"); } }
        public static string StatusStale { get { return Get("StatusStale"); } }
        public static string ObservedAt { get { return Get("ObservedAt"); } }
        public static string LastObservationStale { get { return Get("LastObservationStale"); } }
        public static string NoObservationYet { get { return Get("NoObservationYet"); } }
        public static string StatusErrorCode { get { return Get("StatusErrorCode"); } }
        public static string Stale { get { return Get("Stale"); } }
        public static string Unknown { get { return Get("Unknown"); } }
    }
}
