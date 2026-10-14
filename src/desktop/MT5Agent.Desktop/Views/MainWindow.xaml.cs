using System.Windows;
using System.ComponentModel;
using MT5Agent.Desktop.Services;

namespace MT5Agent.Desktop.Views
{
    public partial class MainWindow : Window
    {
        private readonly IUserPreferencesStore _preferences;
        private readonly TrayService _tray;
        private bool _explicitExit;

        public MainWindow() : this(new UserPreferencesStore(), null) { }
        public MainWindow(IUserPreferencesStore preferences, TrayService tray)
        {
            InitializeComponent();
            _preferences = preferences;
            _tray = tray;
            Closing += OnClosing;
            StateChanged += OnStateChanged;
        }

        public void RequestExit() { _explicitExit = true; Close(); }

        private void OnClosing(object sender, CancelEventArgs e)
        {
            if (TrayLifecyclePolicy.ShouldHideOnClose(_explicitExit, _preferences.Load().CloseToTray))
            {
                e.Cancel = true;
                Hide();
            }
        }

        private void OnStateChanged(object sender, System.EventArgs e)
        {
            if (WindowState == WindowState.Minimized && _tray != null) _tray.HideWindow();
        }
    }
}
