using MT5Agent.Desktop.Resources;

namespace MT5Agent.Desktop.ViewModels
{
    public sealed class DiagnosticsViewModel : ViewModelBase
    {
        public string Title { get { return Strings.DiagnosticsTitle; } }
        public string SectionLabel { get { return Strings.SectionHealth; } }
        public string EmptyTitle { get { return Strings.NoDiagnosticsCollected; } }
        public string Description { get { return Strings.DiagnosticsNoCollection; } }
    }
}
