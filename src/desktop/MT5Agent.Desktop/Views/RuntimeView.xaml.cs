using System.Windows.Controls;
using MT5Agent.Desktop.ViewModels;
namespace MT5Agent.Desktop.Views
{
    public partial class RuntimeView : UserControl
    {
        public RuntimeView()
        {
            InitializeComponent();
            Loaded += (sender, args) => { var vm = DataContext as RuntimeViewModel; if (vm != null && vm.RefreshCommand.CanExecute(null)) vm.RefreshCommand.Execute(null); };
            Unloaded += (sender, args) => { var vm = DataContext as RuntimeViewModel; if (vm != null) vm.CancelRefresh(); };
        }
    }
}
