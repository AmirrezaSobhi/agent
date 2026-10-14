namespace MT5Agent.Desktop.ViewModels
{
    public sealed class UnavailableViewModel : ViewModelBase
    {
        public UnavailableViewModel(string title, string description)
        { Title = title; Description = description; }
        public string Title { get; private set; }
        public string Description { get; private set; }
    }
}
