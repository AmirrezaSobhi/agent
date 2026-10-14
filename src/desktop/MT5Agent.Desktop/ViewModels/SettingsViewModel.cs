using System.Collections.ObjectModel;
using System.Threading;
using System.Threading.Tasks;
using MT5Agent.Desktop.Resources;
using MT5Agent.Desktop.Services;
using MT5Agent.Desktop.ViewModels.Commands;

namespace MT5Agent.Desktop.ViewModels
{
    public sealed class SettingsViewModel : ViewModelBase
    {
        private readonly IUserPreferencesStore _preferences;
        private readonly IThemeService _themeService;
        private readonly IErrorHandler _errors;
        private readonly DesktopUserPreferences _settings;
        private string _saveState = Strings.Saved;

        public SettingsViewModel(IUserPreferencesStore preferences, IThemeService themeService,
            IErrorHandler errors, ThemePreference initialTheme)
            : this(preferences, themeService, errors, preferences.Load())
        { _settings.Theme = initialTheme; }

        public SettingsViewModel(IUserPreferencesStore preferences, IThemeService themeService,
            IErrorHandler errors, DesktopUserPreferences initial)
        {
            _preferences = preferences;
            _themeService = themeService;
            _errors = errors;
            _settings = initial.Copy();
            RefreshIntervals = new ObservableCollection<int> { 5, 10, 15, 30, 60 };
            ToggleThemeCommand = new AsyncCommand(ToggleThemeAsync, errors);
            SaveSettingsCommand = new AsyncCommand(SaveSettingsAsync, errors);
        }

        public ObservableCollection<int> RefreshIntervals { get; private set; }
        public ThemePreference Theme { get { return _settings.Theme; } private set { _settings.Theme = value; OnPropertyChanged("Theme"); OnPropertyChanged("IsDarkTheme"); OnPropertyChanged("ThemeLabel"); } }
        public bool IsDarkTheme { get { return Theme == ThemePreference.Dark; } }
        public string ThemeLabel { get { return IsDarkTheme ? Strings.ThemeDark : Strings.ThemeLight; } }
        public int RefreshIntervalSeconds { get { return _settings.RefreshIntervalSeconds; } set { if (RefreshIntervals.Contains(value) && _settings.RefreshIntervalSeconds != value) { _settings.RefreshIntervalSeconds = value; OnPropertyChanged("RefreshIntervalSeconds"); MarkDirty(); } } }
        public bool NotificationsEnabled { get { return _settings.NotificationsEnabled; } set { if (_settings.NotificationsEnabled != value) { _settings.NotificationsEnabled = value; OnPropertyChanged("NotificationsEnabled"); MarkDirty(); } } }
        public bool CloseToTray { get { return _settings.CloseToTray; } set { if (_settings.CloseToTray != value) { _settings.CloseToTray = value; OnPropertyChanged("CloseToTray"); MarkDirty(); } } }
        public string Language { get { return Strings.LanguageEnglish; } }
        public string ConnectionInformation { get { return NamedPipeManagementClient.PipeName + " · Protocol v1 · Read-only"; } }
        public string StartupBehavior { get { return Strings.StartupUnsupported; } }
        public string SaveState { get { return _saveState; } private set { SetProperty(ref _saveState, value); } }
        public string Description { get { return Strings.SettingsOperationsDescription; } }
        public string SectionLabel { get { return Strings.SectionSettings; } }
        public string ScopeDescription { get { return Strings.PreferencesScope; } }
        public AsyncCommand ToggleThemeCommand { get; private set; }
        public AsyncCommand SaveSettingsCommand { get; private set; }

        public async Task ToggleThemeAsync(CancellationToken cancellationToken)
        {
            Theme = Theme == ThemePreference.Dark ? ThemePreference.Light : ThemePreference.Dark;
            await PersistAsync(cancellationToken, true);
        }

        public Task SaveSettingsAsync(CancellationToken cancellationToken) { return PersistAsync(cancellationToken, true); }

        private void MarkDirty() { SaveState = Strings.UnsavedChanges; }

        private async Task PersistAsync(CancellationToken cancellationToken, bool applyTheme)
        {
            SaveState = Strings.Saving;
            try
            {
                await _preferences.SaveAsync(_settings.Copy(), cancellationToken);
                cancellationToken.ThrowIfCancellationRequested();
                if (applyTheme) _themeService.Apply(_settings.Theme);
                SaveState = Strings.Saved;
            }
            catch (System.OperationCanceledException) { throw; }
            catch
            {
                SaveState = Strings.PreferencesSaveError;
                throw;
            }
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                if (ToggleThemeCommand != null) ToggleThemeCommand.Dispose();
                if (SaveSettingsCommand != null) SaveSettingsCommand.Dispose();
            }
            base.Dispose(disposing);
        }
    }
}
