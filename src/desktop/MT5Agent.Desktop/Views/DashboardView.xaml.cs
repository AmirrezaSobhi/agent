using System.Windows.Controls;
using System.Windows.Threading;
using MT5Agent.Desktop.ViewModels;

namespace MT5Agent.Desktop.Views
{
    public partial class DashboardView : UserControl
    {
        private readonly DispatcherTimer _refreshTimer;

        public DashboardView()
        {
            InitializeComponent();
            _refreshTimer = new DispatcherTimer { Interval = System.TimeSpan.FromSeconds(5) };
            _refreshTimer.Tick += OnRefreshTick;
            Loaded += OnLoaded;
            Unloaded += OnUnloaded;
        }

        private void OnLoaded(object sender, System.Windows.RoutedEventArgs e)
        {
            _refreshTimer.Start();
            var viewModel = DataContext as DashboardViewModel;
            if (viewModel != null && viewModel.RefreshCommand.CanExecute(null)) viewModel.RefreshCommand.Execute(null);
        }

        private void OnUnloaded(object sender, System.Windows.RoutedEventArgs e)
        {
            _refreshTimer.Stop();
            var viewModel = DataContext as DashboardViewModel;
            if (viewModel != null) viewModel.CancelRefresh();
        }

        private void OnRefreshTick(object sender, System.EventArgs e)
        {
            var viewModel = DataContext as DashboardViewModel;
            if (viewModel != null && viewModel.RefreshCommand.CanExecute(null)) viewModel.RefreshCommand.Execute(null);
        }
    }
}
