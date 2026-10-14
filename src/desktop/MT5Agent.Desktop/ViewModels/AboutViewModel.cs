using System.Reflection;
using MT5Agent.Desktop.Resources;

namespace MT5Agent.Desktop.ViewModels
{
    public sealed class AboutViewModel : ViewModelBase
    {
        public string Title { get { return Strings.AboutTitle; } }
        public string Description { get { return Strings.AboutDescription; } }
        public string SectionLabel { get { return Strings.SectionProduct; } }
        public string TechnologyLabel { get { return Strings.TechnologyLabel; } }
        public string Version { get { return Assembly.GetExecutingAssembly().GetName().Version.ToString(); } }
    }
}
