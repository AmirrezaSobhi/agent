using MT5Agent.Desktop.Resources;

namespace MT5Agent.Desktop.ViewModels
{
    public sealed class RuntimeViewModel : ViewModelBase
    {
        public string Title { get { return Strings.NavRuntime; } }
        public string State { get { return Strings.Unavailable; } }
        public string SectionLabel { get { return Strings.SectionRuntime; } }
        public string EmptyMessage { get { return Strings.NoRuntimeData; } }
        public string Description { get { return Strings.PageRuntimeDescription; } }
    }
}
