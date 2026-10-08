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
        private ThemePreference _theme;
        private string _saveState = Strings.Saved;

        public SettingsViewModel(IUserPreferencesStore preferences, IThemeService themeService,
            IErrorHandler errors, ThemePreference initialTheme)
        {
            _preferences = preferences;
            _themeService = themeService;
            _theme = initialTheme;
            ToggleThemeCommand = new AsyncCommand(ToggleThemeAsync, errors);
        }

        public ThemePreference Theme { get { return _theme; } private set { SetProperty(ref _theme, value); OnPropertyChanged("IsDarkTheme"); OnPropertyChanged("ThemeLabel"); } }
        public bool IsDarkTheme { get { return Theme == ThemePreference.Dark; } }
        public string ThemeLabel { get { return IsDarkTheme ? Strings.ThemeDark : Strings.ThemeLight; } }
        public string SaveState { get { return _saveState; } private set { SetProperty(ref _saveState, value); } }
        public string Description { get { return Strings.ThemeDescription; } }
        public string SectionLabel { get { return Strings.SectionSettings; } }
        public string SettingLabel { get { return Strings.ThemeSetting; } }
        public string ScopeDescription { get { return Strings.PreferencesScope; } }
        public AsyncCommand ToggleThemeCommand { get; private set; }

        public async Task ToggleThemeAsync(CancellationToken cancellationToken)
        {
            var next = Theme == ThemePreference.Dark ? ThemePreference.Light : ThemePreference.Dark;
            SaveState = Strings.Loading;
            try
            {
                await _preferences.SaveThemeAsync(next, cancellationToken);
                cancellationToken.ThrowIfCancellationRequested();
                _themeService.Apply(next);
                Theme = next;
                SaveState = Strings.Saved;
            }
            catch (System.OperationCanceledException) { throw; }
            catch
            {
                SaveState = Strings.ThemeSaveError;
                throw;
            }
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing && ToggleThemeCommand != null) ToggleThemeCommand.Dispose();
            base.Dispose(disposing);
        }
    }
}
