using System;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;

namespace MT5Agent.Desktop.Services
{
    public enum ThemePreference { Dark, Light }

    public sealed class DesktopUserPreferences
    {
        public ThemePreference Theme { get; set; }
        public int RefreshIntervalSeconds { get; set; }
        public bool NotificationsEnabled { get; set; }
        public bool CloseToTray { get; set; }
        public string Language { get; set; }

        public static DesktopUserPreferences Defaults()
        {
            return new DesktopUserPreferences { Theme = ThemePreference.Dark, RefreshIntervalSeconds = 10,
                NotificationsEnabled = true, CloseToTray = false, Language = "en" };
        }

        public DesktopUserPreferences Copy()
        {
            return new DesktopUserPreferences { Theme = Theme, RefreshIntervalSeconds = RefreshIntervalSeconds,
                NotificationsEnabled = NotificationsEnabled, CloseToTray = CloseToTray, Language = Language };
        }
    }

    public interface IUserPreferencesStore
    {
        DesktopUserPreferences Load();
        Task SaveAsync(DesktopUserPreferences preferences, CancellationToken cancellationToken);
        ThemePreference LoadTheme();
        Task SaveThemeAsync(ThemePreference theme, CancellationToken cancellationToken);
    }

    public sealed class UserPreferencesStore : IUserPreferencesStore
    {
        private readonly string _path;
        private readonly JavaScriptSerializer _serializer = new JavaScriptSerializer { MaxJsonLength = 4096 };

        public UserPreferencesStore() : this(Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "MT5Agent", "Desktop", "preferences.v1")) { }

        public UserPreferencesStore(string path)
        {
            if (string.IsNullOrWhiteSpace(path)) throw new ArgumentException("A preference path is required.", "path");
            _path = path;
        }

        public DesktopUserPreferences Load()
        {
            try
            {
                if (!File.Exists(_path)) return DesktopUserPreferences.Defaults();
                var raw = File.ReadAllText(_path, Encoding.UTF8).Trim();
                ThemePreference legacyTheme;
                if (Enum.TryParse(raw, true, out legacyTheme) && Enum.IsDefined(typeof(ThemePreference), legacyTheme))
                {
                    var migrated = DesktopUserPreferences.Defaults();
                    migrated.Theme = legacyTheme;
                    return migrated;
                }
                var values = _serializer.Deserialize<DesktopUserPreferences>(raw);
                return Validate(values) ? values : DesktopUserPreferences.Defaults();
            }
            catch (IOException) { return DesktopUserPreferences.Defaults(); }
            catch (UnauthorizedAccessException) { return DesktopUserPreferences.Defaults(); }
            catch (InvalidOperationException) { return DesktopUserPreferences.Defaults(); }
            catch (ArgumentException) { return DesktopUserPreferences.Defaults(); }
        }

        public ThemePreference LoadTheme() { return Load().Theme; }

        public Task SaveThemeAsync(ThemePreference theme, CancellationToken cancellationToken)
        {
            var preferences = Load();
            preferences.Theme = theme;
            return SaveAsync(preferences, cancellationToken);
        }

        public async Task SaveAsync(DesktopUserPreferences preferences, CancellationToken cancellationToken)
        {
            if (!Validate(preferences)) throw new ArgumentException("User preferences are outside the supported bounds.", "preferences");
            var directory = Path.GetDirectoryName(_path);
            if (string.IsNullOrEmpty(directory)) throw new IOException("Preference path has no directory.");
            Directory.CreateDirectory(directory);
            var temporaryPath = _path + "." + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                using (var stream = new FileStream(temporaryPath, FileMode.CreateNew, FileAccess.Write, FileShare.None, 4096, true))
                using (var writer = new StreamWriter(stream, new UTF8Encoding(false)))
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    await writer.WriteAsync(_serializer.Serialize(preferences)).ConfigureAwait(false);
                    await writer.FlushAsync().ConfigureAwait(false);
                    cancellationToken.ThrowIfCancellationRequested();
                    stream.Flush(true);
                }
                if (File.Exists(_path)) File.Replace(temporaryPath, _path, null);
                else File.Move(temporaryPath, _path);
            }
            finally { if (File.Exists(temporaryPath)) File.Delete(temporaryPath); }
        }

        private static bool Validate(DesktopUserPreferences value)
        {
            return value != null && Enum.IsDefined(typeof(ThemePreference), value.Theme) &&
                value.RefreshIntervalSeconds >= 5 && value.RefreshIntervalSeconds <= 60 &&
                (value.RefreshIntervalSeconds % 5) == 0 &&
                String.Equals(value.Language, "en", StringComparison.OrdinalIgnoreCase);
        }
    }
}
