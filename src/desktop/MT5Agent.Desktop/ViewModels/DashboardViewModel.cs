using System;
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
        private string _freshnessText = Strings.NoObservationYet;
        private bool _hasObservedStatus;

        public DashboardViewModel(IManagementClient management, IErrorHandler errors)
        {
            _management = management;
            _errors = errors;
            Cards = new ObservableCollection<StatusCardViewModel>
            {
                new StatusCardViewModel(Strings.ServiceStatus, Strings.Unavailable, Strings.ServiceUnavailableDetail),
                new StatusCardViewModel(Strings.AgentStatus, Strings.Unavailable, Strings.AgentUnavailableDetail),
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
        public string FreshnessText { get { return _freshnessText; } private set { SetProperty(ref _freshnessText, value); } }

        public async Task RefreshAsync(CancellationToken cancellationToken)
        {
            IsLoading = true;
            InlineError = null;
            try
            {
                var result = await _management.GetStatusAsync(cancellationToken);
                if (result == null || !result.IsObserved)
                {
                    if (_hasObservedStatus) MarkStale();
                    else Message = result == null || String.IsNullOrWhiteSpace(result.Reason) ? Strings.NoSecureChannel : result.Reason;
                    return;
                }
                _hasObservedStatus = true;
                Cards[0].Set(Strings.ServiceRunning, Strings.ServiceRunningDetail);
                Cards[1].Set(result.AgentState, Strings.AgentResponsiveDetail);
                Cards[2].Set(result.WorkerState, result.RuntimeState);
                Cards[3].Set(result.Mt5Connected ? Strings.Connected : Strings.Disconnected,
                    result.Mt5Connected ? Strings.Mt5ConnectedDetail : Strings.Mt5DisconnectedDetail);
                Cards[4].Set(result.CentralState, Strings.CentralLocalDetail);
                Cards[5].Set(result.TradingCapability, result.TradingAuthorized);
                var observed = result.ObservedAtUtc.HasValue ? result.ObservedAtUtc.Value.ToLocalTime().ToString("g") : Strings.Unknown;
                FreshnessText = String.Format(Strings.ObservedAt, observed);
                Message = result.IsStale ? Strings.StatusStale : Strings.StatusCurrent;
                if (result.IsStale) MarkStale();
            }
            catch (System.OperationCanceledException) { throw; }
            catch (System.Exception ex)
            {
                InlineError = ex is ManagementIpcException
                    ? String.Format(Strings.StatusErrorCode, ((ManagementIpcException)ex).Code)
                    : Strings.RefreshError;
                if (_hasObservedStatus) MarkStale();
                _errors.Handle(ex, "Dashboard.Refresh");
            }
            finally { IsLoading = false; }
        }

        private void MarkStale()
        {
            for (var index = 0; index < 4; index++) Cards[index].Set(Strings.Stale, Cards[index].Detail);
            Message = Strings.StatusStale;
            FreshnessText = Strings.LastObservationStale;
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing && RefreshCommand != null) RefreshCommand.Dispose();
            base.Dispose(disposing);
        }
    }

    public sealed class StatusCardViewModel : ViewModelBase
    {
        private string _value;
        private string _detail;
        public StatusCardViewModel(string title, string value, string detail)
        { Title = title; _value = value; _detail = detail; }
        public string Title { get; private set; }
        public string Value { get { return _value; } private set { SetProperty(ref _value, value); } }
        public string Detail { get { return _detail; } private set { SetProperty(ref _detail, value); } }
        public void Set(string value, string detail) { Value = value; Detail = detail; }
    }
}
