using System.Windows.Controls;
using MT5Agent.Desktop.ViewModels;
namespace MT5Agent.Desktop.Views
{
    public partial class DiagnosticsView : UserControl
    {
        public DiagnosticsView()
        {
            InitializeComponent();
            Loaded += (sender, args) => { var vm = DataContext as DiagnosticsViewModel; if (vm != null && vm.RefreshCommand.CanExecute(null)) vm.RefreshCommand.Execute(null); };
        }
    }
}
