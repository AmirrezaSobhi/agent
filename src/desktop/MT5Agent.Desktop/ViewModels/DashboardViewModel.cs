using System.Collections.ObjectModel;
using System.Threading;
using System.Threading.Tasks;
using MT5Agent.Desktop.Resources;
using MT5Agent.Desktop.Services;
using MT5Agent.Desktop.ViewModels.Commands;

namespace MT5Agent.Desktop.ViewModels
{
    public sealed class DashboardViewModel : ViewModelBase
    {
        private readonly IManagementClient _management;
        private readonly IErrorHandler _errors;
        private bool _isLoading;
        private string _message = Strings.NoSecureChannel;
        private string _inlineError;

        public DashboardViewModel(IManagementClient management, IErrorHandler errors)
        {
            _management = management;
            _errors = errors;
            Cards = new ObservableCollection<StatusCardViewModel>
            {
                new StatusCardViewModel(Strings.ServiceStatus, Strings.Unavailable, Strings.ServiceUnavailableDetail),
                new StatusCardViewModel(Strings.WorkerStatus, Strings.Unavailable, Strings.RuntimeUnavailableDetail),
                new StatusCardViewModel(Strings.Mt5Status, Strings.Unavailable, Strings.Mt5UnavailableDetail),
                new StatusCardViewModel(Strings.CentralStatus, Strings.NotConfigured, Strings.CentralLocalDetail),
                new StatusCardViewModel(Strings.TradingStatus, Strings.NotImplemented, Strings.TradingUnsupportedDetail)
            };
            RefreshCommand = new AsyncCommand(RefreshAsync, _errors);
        }

        public ObservableCollection<StatusCardViewModel> Cards { get; private set; }
        public AsyncCommand RefreshCommand { get; private set; }
        public bool IsLoading { get { return _isLoading; } private set { SetProperty(ref _isLoading, value); } }
        public string Message { get { return _message; } private set { SetProperty(ref _message, value); } }
        public string InlineError { get { return _inlineError; } private set { SetProperty(ref _inlineError, value); } }

        public async Task RefreshAsync(CancellationToken cancellationToken)
        {
            IsLoading = true;
            InlineError = null;
            try
            {
                var result = await _management.GetStatusAsync(cancellationToken);
                if (result == null || !result.IsObserved)
                {
                    Message = result == null || string.IsNullOrWhiteSpace(result.Reason) ? Strings.NoSecureChannel : result.Reason;
                    return;
                }
                // Reserved for a future authorized client. Phase 1 never reports simulated values as observed state.
                Message = Strings.NoSecureChannel;
            }
            catch (System.OperationCanceledException) { throw; }
            catch (System.Exception ex)
            {
                InlineError = Strings.RefreshError;
                _errors.Handle(ex, "Dashboard.Refresh");
            }
            finally { IsLoading = false; }
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing && RefreshCommand != null) RefreshCommand.Dispose();
            base.Dispose(disposing);
        }
    }

    public sealed class StatusCardViewModel
    {
        public StatusCardViewModel(string title, string value, string detail)
        { Title = title; Value = value; Detail = detail; }
        public string Title { get; private set; }
        public string Value { get; private set; }
        public string Detail { get; private set; }
    }
}
