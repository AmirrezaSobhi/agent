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
        private string _lastObservationText = Strings.NoObservationYet;
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
                new StatusCardViewModel(Strings.ManagementStatus, Strings.Disconnected, Strings.ManagementUnavailableDetail),
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
                    Cards[4].Set(Strings.Disconnected, Strings.ManagementUnavailableDetail);
                    if (_hasObservedStatus) MarkOffline();
                    else Message = result == null || String.IsNullOrWhiteSpace(result.Reason) ? Strings.NoSecureChannel : result.Reason;
                    return;
                }
                _hasObservedStatus = true;
                Cards[0].Set(DisplayServiceState(result.ServiceState), Strings.ServiceUnavailableDetail);
                Cards[1].Set(DisplayAgentState(result.AgentState), Strings.AgentResponsiveDetail);
                Cards[2].Set(DisplayState(result.WorkerState), SafeDetail(result.ErrorCode, result.RuntimeState));
                Cards[3].Set(DisplayMt5State(result.Mt5State),
                    String.IsNullOrWhiteSpace(result.ErrorCode) || String.Equals(result.ErrorCode, "OK", StringComparison.Ordinal)
                        ? Strings.Mt5StatusDetail : String.Format(Strings.StatusErrorCode, DisplayState(result.ErrorCode)));
                Cards[4].Set(Strings.Connected, String.Format(Strings.ManagementConnectedDetail,
                    String.IsNullOrWhiteSpace(result.SourceIdentity) ? Strings.Unknown : result.SourceIdentity));
                Cards[5].Set(DisplayCentralState(result.CentralState), Strings.CentralLocalDetail);
                Cards[6].Set(DisplayState(result.TradingCapability),
                    String.Format(Strings.TradingAuthorizationDetail, DisplayState(result.TradingAuthorized), DisplayState(result.TradingReadiness)));
                var observed = result.ObservedAtUtc.HasValue ? result.ObservedAtUtc.Value.ToLocalTime().ToString("g") : Strings.Unknown;
                _lastObservationText = String.Format(Strings.ObservedAtWithSource, observed,
                    String.IsNullOrWhiteSpace(result.SourceIdentity) ? Strings.Unknown : result.SourceIdentity);
                FreshnessText = _lastObservationText;
                Message = result.IsStale ? Strings.StatusStale : Strings.StatusCurrent;
                if (result.IsStale) MarkStale();
            }
            catch (System.OperationCanceledException) { throw; }
            catch (System.Exception ex)
            {
                InlineError = ex is ManagementIpcException
                    ? String.Format(Strings.StatusErrorCode, ((ManagementIpcException)ex).Code)
                    : Strings.RefreshError;
                Cards[4].Set(Strings.Disconnected, Strings.ManagementUnavailableDetail);
                if (_hasObservedStatus) MarkOffline();
                _errors.Handle(ex, "Dashboard.Refresh");
            }
            finally { IsLoading = false; }
        }

        public void CancelRefresh()
        {
            if (RefreshCommand != null) RefreshCommand.Cancel();
        }

        private void MarkStale()
        {
            for (var index = 1; index < 4; index++) Cards[index].Set(Strings.Stale, Cards[index].Detail);
            Message = Strings.StatusStale;
            FreshnessText = String.Format(Strings.ObservedStale, _lastObservationText);
        }

        private void MarkOffline()
        {
            for (var index = 1; index < 4; index++) Cards[index].Set(Strings.Stale, Cards[index].Detail);
            Cards[4].Set(Strings.Disconnected, Strings.ManagementUnavailableDetail);
            Message = Strings.StatusOffline;
            FreshnessText = String.Format(Strings.ObservedOffline, _lastObservationText);
        }

        private static string DisplayServiceState(string value)
        {
            if (String.Equals(value, "RUNNING", StringComparison.Ordinal)) return Strings.ServiceRunning;
            if (String.Equals(value, "STOPPED", StringComparison.Ordinal)) return Strings.ServiceStopped;
            if (String.Equals(value, "STARTING", StringComparison.Ordinal)) return Strings.Starting;
            if (String.Equals(value, "STOPPING", StringComparison.Ordinal)) return Strings.Stopping;
            if (String.Equals(value, "ACCESS_DENIED", StringComparison.Ordinal)) return Strings.AccessDenied;
            return Strings.Unknown;
        }

        private static string DisplayAgentState(string value)
        {
            if (String.Equals(value, "RESPONSIVE", StringComparison.Ordinal) ||
                String.Equals(value, "AGENT_RUNNING", StringComparison.Ordinal)) return Strings.Responsive;
            return DisplayState(value);
        }

        private static string DisplayMt5State(string value)
        {
            if (String.Equals(value, "CONNECTED", StringComparison.Ordinal)) return Strings.Connected;
            if (String.Equals(value, "DISCONNECTED", StringComparison.Ordinal)) return Strings.Disconnected;
            if (String.Equals(value, "INITIALIZING", StringComparison.Ordinal)) return Strings.Starting;
            if (String.Equals(value, "ERROR", StringComparison.Ordinal)) return Strings.Error;
            return Strings.Unknown;
        }

        private static string DisplayCentralState(string value)
        {
            if (String.Equals(value, "CONNECTED", StringComparison.Ordinal)) return Strings.Connected;
            if (String.Equals(value, "DISCONNECTED", StringComparison.Ordinal)) return Strings.Disconnected;
            if (String.Equals(value, "UNSUPPORTED", StringComparison.Ordinal)) return Strings.NotImplemented;
            return Strings.NotConfigured;
        }

        private static string DisplayState(string value)
        {
            return String.IsNullOrWhiteSpace(value) || String.Equals(value, "UNKNOWN", StringComparison.Ordinal)
                ? Strings.Unknown : value.Replace('_', ' ');
        }

        private static string SafeDetail(string errorCode, string state)
        {
            if (!String.IsNullOrWhiteSpace(errorCode) && !String.Equals(errorCode, "OK", StringComparison.Ordinal))
                return String.Format(Strings.StatusErrorCode, DisplayState(errorCode));
            return DisplayState(state);
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
