using System.ComponentModel;
using MT5Agent.Desktop.Resources;

namespace MT5Agent.Desktop.ViewModels
{
    public sealed class NavigationItem : INotifyPropertyChanged
    {
        private bool _isActive;
        public NavigationItem(string route, string title, string glyph, bool isAvailable = true)
        {
            Route = route;
            Title = title;
            Glyph = glyph;
            IsAvailable = isAvailable;
        }
        public string Route { get; private set; }
        public string Title { get; private set; }
        public string Glyph { get; private set; }
        public bool IsAvailable { get; private set; }
        public string AvailabilityText { get { return IsAvailable ? string.Empty : Strings.NavPreview; } }
        public bool IsActive
        {
            get { return _isActive; }
            set
            {
                if (_isActive == value) return;
                _isActive = value;
                var handler = PropertyChanged;
                if (handler != null) handler(this, new PropertyChangedEventArgs("IsActive"));
            }
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }
}
