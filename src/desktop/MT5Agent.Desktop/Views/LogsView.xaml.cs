using System.Windows.Controls;
using MT5Agent.Desktop.ViewModels;
namespace MT5Agent.Desktop.Views
{
    public partial class LogsView : UserControl
    {
        public LogsView()
        {
            InitializeComponent();
            Loaded += (sender, args) => { var vm = DataContext as LogsViewModel; if (vm != null && vm.LoadCommand.CanExecute(null)) vm.LoadCommand.Execute(null); };
            Unloaded += (sender, args) => { var vm = DataContext as LogsViewModel; if (vm != null) vm.CancelLoad(); };
        }
    }
}
