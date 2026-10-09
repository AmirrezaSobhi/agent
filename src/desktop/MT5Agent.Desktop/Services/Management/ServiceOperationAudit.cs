using System;
using System.IO;
using System.Text;

namespace MT5Agent.Desktop.Services
{
    /// <summary>Local, bounded-format audit for SCM requests; contains no user or account identifiers.</summary>
    public static class ServiceOperationAudit
    {
        private const long MaxBytes = 1024 * 1024;

        public static bool TryRecord(ServiceAction action, string resultCode, string resultingState)
        {
            try
            {
                var directory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "MT5Agent", "Desktop");
                Directory.CreateDirectory(directory);
                var path = Path.Combine(directory, "service-operations.log");
                var info = new FileInfo(path);
                if (info.Exists && info.Length >= MaxBytes)
                {
                    var previous = path + ".previous";
                    if (File.Exists(previous)) File.Delete(previous);
                    File.Move(path, previous);
                }
                var line = DateTime.UtcNow.ToString("o", System.Globalization.CultureInfo.InvariantCulture) + "\t" +
                    action + "\t" + Safe(resultCode) + "\t" + Safe(resultingState) + Environment.NewLine;
                using (var stream = new FileStream(path, FileMode.Append, FileAccess.Write, FileShare.Read))
                using (var writer = new StreamWriter(stream, new UTF8Encoding(false)))
                { writer.Write(line); writer.Flush(); stream.Flush(true); }
                return true;
            }
            catch (IOException) { return false; }
            catch (UnauthorizedAccessException) { return false; }
            catch (System.Security.SecurityException) { return false; }
            catch (ArgumentException) { return false; }
        }

        private static string Safe(string value)
        {
            if (String.IsNullOrEmpty(value) || value.Length > 64) return "UNKNOWN";
            foreach (var character in value) if (!Char.IsLetterOrDigit(character) && character != '_' && character != '-') return "UNKNOWN";
            return value;
        }
    }
}
