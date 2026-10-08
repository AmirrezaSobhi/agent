using System;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace MT5Agent.Desktop.Services
{
    public enum ThemePreference { Dark, Light }

    public interface IUserPreferencesStore
    {
        ThemePreference LoadTheme();
        Task SaveThemeAsync(ThemePreference theme, CancellationToken cancellationToken);
    }

    public sealed class UserPreferencesStore : IUserPreferencesStore
    {
        private readonly string _path;

        public UserPreferencesStore() : this(Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "MT5Agent", "Desktop", "preferences.v1")) { }

        public UserPreferencesStore(string path)
        {
            if (string.IsNullOrWhiteSpace(path)) throw new ArgumentException("A preference path is required.", "path");
            _path = path;
        }

        public ThemePreference LoadTheme()
        {
            try
            {
                if (!File.Exists(_path)) return ThemePreference.Dark;
                ThemePreference theme;
                return Enum.TryParse(File.ReadAllText(_path, Encoding.UTF8).Trim(), true, out theme)
                    ? theme : ThemePreference.Dark;
            }
            catch (IOException) { return ThemePreference.Dark; }
            catch (UnauthorizedAccessException) { return ThemePreference.Dark; }
        }

        public async Task SaveThemeAsync(ThemePreference theme, CancellationToken cancellationToken)
        {
            var directory = Path.GetDirectoryName(_path);
            if (string.IsNullOrEmpty(directory)) throw new IOException("Preference path has no directory.");
            Directory.CreateDirectory(directory);
            var temporaryPath = _path + "." + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                using (var stream = new FileStream(temporaryPath, FileMode.Create, FileAccess.Write, FileShare.None, 4096, true))
                using (var writer = new StreamWriter(stream, new UTF8Encoding(false)))
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    await writer.WriteAsync(theme.ToString()).ConfigureAwait(false);
                    await writer.FlushAsync().ConfigureAwait(false);
                    cancellationToken.ThrowIfCancellationRequested();
                    stream.Flush(true);
                }
                if (File.Exists(_path)) File.Replace(temporaryPath, _path, null);
                else File.Move(temporaryPath, _path);
            }
            finally
            {
                if (File.Exists(temporaryPath)) File.Delete(temporaryPath);
            }
        }
    }
}
