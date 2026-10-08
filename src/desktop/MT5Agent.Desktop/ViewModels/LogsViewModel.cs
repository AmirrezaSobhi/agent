using MT5Agent.Desktop.Resources;

namespace MT5Agent.Desktop.ViewModels
{
    public sealed class LogsViewModel : ViewModelBase
    {
        public string Title { get { return Strings.LogsTitle; } }
        public string SectionLabel { get { return Strings.SectionOperations; } }
        public string Description { get { return Strings.PageLogsDescription; } }
        public string EmptyMessage { get { return Strings.NoLogs; } }
        public string EmptyDetail { get { return Strings.NoLogFilesRead; } }
    }
}
