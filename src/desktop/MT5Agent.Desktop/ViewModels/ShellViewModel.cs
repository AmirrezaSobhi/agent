using System.Collections.ObjectModel;
using MT5Agent.Desktop.Resources;
using MT5Agent.Desktop.Services;
using MT5Agent.Desktop.ViewModels.Commands;

namespace MT5Agent.Desktop.ViewModels
{
    public sealed class ShellViewModel : ViewModelBase
    {
        private readonly NavigationService _navigation;
        private readonly ErrorService _errors;

        public ShellViewModel(NavigationService navigation, ErrorService errors)
        {
            _navigation = navigation;
            _errors = errors;
            NavigationItems = new ObservableCollection<NavigationItem>
            {
                new NavigationItem("Dashboard", Strings.NavDashboard, "\uE80F"),
                new NavigationItem("Runtime", Strings.NavRuntime, "\uE7F4"),
                new NavigationItem("Accounts", Strings.NavAccounts, "\uE77B", false),
                new NavigationItem("Security", Strings.NavSecurity, "\uE72E", false),
                new NavigationItem("Settings", Strings.NavSettings, "\uE713"),
                new NavigationItem("Logs", Strings.NavLogs, "\uE81C"),
                new NavigationItem("Diagnostics", Strings.NavDiagnostics, "\uE9D9"),
                new NavigationItem("Updates", Strings.NavUpdates, "\uE777", false),
                new NavigationItem("Support", Strings.NavSupport, "\uE8D7", false),
                new NavigationItem("About", Strings.NavAbout, "\uE946")
            };
            NavigateCommand = new RelayCommand(parameter => Navigate(parameter as string));
            _navigation.PropertyChanged += OnNavigationChanged;
            _errors.PropertyChanged += OnErrorChanged;
            _navigation.Navigate("Dashboard");
        }

        public ObservableCollection<NavigationItem> NavigationItems { get; private set; }
        public RelayCommand NavigateCommand { get; private set; }
        public ViewModelBase CurrentPage { get { return _navigation.CurrentViewModel; } }
        public string CurrentPageTitle
        {
            get
            {
                var item = FindItem(_navigation.CurrentRoute);
                return item == null ? Strings.AppName : item.Title;
            }
        }
        public bool HasError { get { return _errors.HasError; } }
        public string ErrorMessage { get { return _errors.Message; } }
        public string CurrentRoute { get { return _navigation.CurrentRoute; } }

        public void Navigate(string route)
        {
            if (string.IsNullOrWhiteSpace(route)) return;
            try { _navigation.Navigate(route); }
            catch (System.Exception ex) { _errors.Handle(ex, "Shell.Navigate"); }
        }

        private NavigationItem FindItem(string route)
        {
            foreach (var item in NavigationItems) if (item.Route == route) return item;
            return null;
        }

        private void OnNavigationChanged(object sender, System.ComponentModel.PropertyChangedEventArgs e)
        {
            if (e.PropertyName == "CurrentViewModel") OnPropertyChanged("CurrentPage");
            if (e.PropertyName == "CurrentRoute")
            {
                OnPropertyChanged("CurrentPageTitle");
                OnPropertyChanged("CurrentRoute");
                foreach (var item in NavigationItems) item.IsActive = item.Route == _navigation.CurrentRoute;
            }
        }

        private void OnErrorChanged(object sender, System.ComponentModel.PropertyChangedEventArgs e)
        {
            if (e.PropertyName == "HasError") OnPropertyChanged("HasError");
            if (e.PropertyName == "Message") OnPropertyChanged("ErrorMessage");
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                _navigation.PropertyChanged -= OnNavigationChanged;
                _errors.PropertyChanged -= OnErrorChanged;
                NavigateCommand = null;
            }
            base.Dispose(disposing);
        }
    }
}
