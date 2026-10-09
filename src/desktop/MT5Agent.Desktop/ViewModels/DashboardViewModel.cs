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
        private readonly IUserPreferencesStore _preferences;
        private readonly IDesktopNotifier _notifier;
        private readonly IServiceControlClient _serviceControl;
        private readonly Func<ServiceAction, bool> _confirmServiceAction;
        private readonly Func<ServiceAction, string, string, bool> _auditServiceAction;
        private string _serviceState = "UNKNOWN";
        private string _servicePermission = "Checking Windows service permissions…";
        private string _serviceOperationText;
        private bool _isServiceBusy;
        private bool _serviceCanStart;
        private bool _serviceCanStop;
        private bool _isLoading;
        private string _message = Strings.NoSecureChannel;
        private string _inlineError;
        private string _freshnessText = Strings.NoObservationYet;
        private string _lastObservationText = Strings.NoObservationYet;
        private bool _hasObservedStatus;
        private bool? _lastConnectionState;

        public DashboardViewModel(IManagementClient management, IErrorHandler errors,
            IUserPreferencesStore preferences = null, IDesktopNotifier notifier = null,
            IServiceControlClient serviceControl = null, Func<ServiceAction, bool> confirmServiceAction = null,
            Func<ServiceAction, string, string, bool> auditServiceAction = null)
        {
            _management = management;
            _errors = errors;
            _preferences = preferences;
            _notifier = notifier;
            _serviceControl = serviceControl;
            _confirmServiceAction = confirmServiceAction;
            _auditServiceAction = auditServiceAction ?? ServiceOperationAudit.TryRecord;
            Cards = new ObservableCollection<StatusCardViewModel>
            {
                new StatusCardViewModel(Strings.ServiceStatus, Strings.Unknown, Strings.ServiceUnavailableDetail),
                new StatusCardViewModel(Strings.AgentStatus, Strings.Unavailable, Strings.AgentUnavailableDetail),
                new StatusCardViewModel(Strings.WorkerStatus, Strings.Unavailable, Strings.RuntimeUnavailableDetail),
                new StatusCardViewModel(Strings.Mt5Status, Strings.Unavailable, Strings.Mt5UnavailableDetail),
                new StatusCardViewModel(Strings.ManagementStatus, Strings.Disconnected, Strings.ManagementUnavailableDetail),
                new StatusCardViewModel(Strings.CentralStatus, Strings.NotConfigured, Strings.CentralLocalDetail),
                new StatusCardViewModel(Strings.TradingStatus, Strings.NotImplemented, Strings.TradingUnsupportedDetail)
            };
            RefreshCommand = new AsyncCommand(RefreshAsync, _errors);
            StartServiceCommand = new AsyncCommand(token => ExecuteServiceActionAsync(ServiceAction.Start, token), _errors);
            StopServiceCommand = new AsyncCommand(token => ExecuteServiceActionAsync(ServiceAction.Stop, token), _errors);
            RestartServiceCommand = new AsyncCommand(token => ExecuteServiceActionAsync(ServiceAction.Restart, token), _errors);
        }

        public ObservableCollection<StatusCardViewModel> Cards { get; private set; }
        public AsyncCommand RefreshCommand { get; private set; }
        public AsyncCommand StartServiceCommand { get; private set; }
        public AsyncCommand StopServiceCommand { get; private set; }
        public AsyncCommand RestartServiceCommand { get; private set; }
        public string ServiceState { get { return _serviceState; } private set { SetProperty(ref _serviceState, value); } }
        public string ServicePermission { get { return _servicePermission; } private set { SetProperty(ref _servicePermission, value); } }
        public string ServiceOperationText { get { return _serviceOperationText; } private set { SetProperty(ref _serviceOperationText, value); } }
        public bool IsServiceBusy { get { return _isServiceBusy; } private set { SetProperty(ref _isServiceBusy, value); } }
        public bool CanStartService { get { return _serviceControl != null && _serviceCanStart && ServiceState == "STOPPED" && !IsServiceBusy; } }
        public bool CanStopService { get { return _serviceControl != null && _serviceCanStop && (ServiceState == "RUNNING" || ServiceState == "PAUSED") && !IsServiceBusy; } }
        public bool CanRestartService { get { return _serviceControl != null && _serviceCanStart && _serviceCanStop && (ServiceState == "RUNNING" || ServiceState == "STOPPED" || ServiceState == "PAUSED") && !IsServiceBusy; } }
        public bool IsLoading { get { return _isLoading; } private set { SetProperty(ref _isLoading, value); } }
        public int RefreshIntervalSeconds { get { return _preferences == null ? 10 : _preferences.Load().RefreshIntervalSeconds; } }
        public string Message { get { return _message; } private set { SetProperty(ref _message, value); } }
        public string InlineError { get { return _inlineError; } private set { SetProperty(ref _inlineError, value); } }
        public string FreshnessText { get { return _freshnessText; } private set { SetProperty(ref _freshnessText, value); } }

        public async Task RefreshAsync(CancellationToken cancellationToken)
        {
            IsLoading = true;
            InlineError = null;
            try
            {
                await RefreshServiceAsync(cancellationToken);
                var result = await _management.GetStatusAsync(cancellationToken);
                if (result == null || !result.IsObserved)
                {
                    RecordConnectionState(false);
                    Cards[4].Set(Strings.Disconnected, Strings.ManagementUnavailableDetail);
                    if (_hasObservedStatus) MarkOffline();
                    else Message = result == null || String.IsNullOrWhiteSpace(result.Reason) ? Strings.NoSecureChannel : result.Reason;
                    return;
                }
                _hasObservedStatus = true;
                _errors.Clear();
                RecordConnectionState(true);
                Cards[1].Set(DisplayAgentState(result.AgentState), Strings.AgentResponsiveDetail);
                Cards[2].Set(DisplayWorkerState(result.WorkerState), SafeDetail(result.ErrorCode, result.RuntimeState));
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
                RecordConnectionState(false);
                InlineError = ex is ManagementIpcException
                    ? String.Format(Strings.StatusErrorCode, ((ManagementIpcException)ex).Code)
                    : Strings.RefreshError;
                Cards[4].Set(Strings.Disconnected, Strings.ManagementUnavailableDetail);
                if (_hasObservedStatus) MarkOffline();
                var pipeUnavailable = ex is ManagementIpcException &&
                    (String.Equals(((ManagementIpcException)ex).Code, "PIPE_NOT_FOUND", StringComparison.Ordinal) ||
                     String.Equals(((ManagementIpcException)ex).Code, "PIPE_BROKEN", StringComparison.Ordinal) ||
                     String.Equals(((ManagementIpcException)ex).Code, "PIPE_BUSY", StringComparison.Ordinal) ||
                     String.Equals(((ManagementIpcException)ex).Code, "ACCESS_DENIED", StringComparison.Ordinal) ||
                     String.Equals(((ManagementIpcException)ex).Code, "TIMEOUT", StringComparison.Ordinal) ||
                     String.Equals(((ManagementIpcException)ex).Code, "SERVICE_UNAVAILABLE", StringComparison.Ordinal));
                if (!pipeUnavailable) _errors.Handle(ex, "Dashboard.Refresh");
            }
            finally { IsLoading = false; }
        }

        private async Task RefreshServiceAsync(CancellationToken cancellationToken)
        {
            if (_serviceControl == null) { ServiceState = "UNKNOWN"; ServicePermission = "Service management is unavailable."; NotifyServiceActions(); return; }
            try
            {
                var observation = await _serviceControl.QueryAsync(cancellationToken).ConfigureAwait(true);
                ServiceState = observation == null ? "UNKNOWN" : observation.State;
                _serviceCanStart = observation != null && observation.CanStart;
                _serviceCanStop = observation != null && observation.CanStop;
                ServicePermission = observation == null ? "Service status could not be queried." :
                    observation.ErrorCode == "NOT_INSTALLED" ? "MT5Agent Windows Service is not installed." :
                    observation.ErrorCode == "ACCESS_DENIED" ? "Windows denied Service status access." :
                    observation.ErrorCode != null ? "Service status query failed (" + observation.ErrorCode + ")." :
                    (observation.CanStart ? "Start allowed" : "Start requires Windows Service permission") + " · " +
                    (observation.CanStop ? "Stop allowed" : "Stop requires Windows Service permission");
                Cards[0].Set(DisplayServiceState(ServiceState), ServicePermission);
            }
            catch (OperationCanceledException) { throw; }
            catch (Exception)
            {
                ServiceState = "QUERY_FAILED"; ServicePermission = "Windows Service status could not be queried.";
                Cards[0].Set(DisplayServiceState(ServiceState), ServicePermission);
            }
            NotifyServiceActions();
        }

        private async Task ExecuteServiceActionAsync(ServiceAction action, CancellationToken cancellationToken)
        {
            if (_serviceControl == null) { ServiceOperationText = "Service control is unavailable."; return; }
            if ((action == ServiceAction.Start && !CanStartService) ||
                (action == ServiceAction.Stop && !CanStopService) ||
                (action == ServiceAction.Restart && !CanRestartService))
            { ServiceOperationText = "The current Service state or Windows permissions do not allow this operation."; return; }
            if ((action == ServiceAction.Stop || action == ServiceAction.Restart) &&
                (_confirmServiceAction == null || !_confirmServiceAction(action))) return;
            IsServiceBusy = true; NotifyServiceActions(); ServiceOperationText = action + " requested…";
            try
            {
                var result = await _serviceControl.ExecuteAsync(action, cancellationToken).ConfigureAwait(true);
                ServiceOperationText = result == null ? "Service operation returned no result." :
                    (result.Succeeded ? "Completed: " : "Not completed: ") + result.Code + " · " + result.State;
                if (result != null && !_auditServiceAction(action, result.Code, result.State))
                    ServiceOperationText += " Audit log could not be written.";
            }
            catch (OperationCanceledException) { ServiceOperationText = "Operation cancelled; check current Service state before retrying."; }
            catch (Exception) { ServiceOperationText = "Service operation failed; check current Service state before retrying."; }
            finally { await RefreshServiceAsync(CancellationToken.None); IsServiceBusy = false; NotifyServiceActions(); }
        }

        private void NotifyServiceActions()
        {
            OnPropertyChanged("CanStartService"); OnPropertyChanged("CanStopService"); OnPropertyChanged("CanRestartService");
        }

        public void CancelRefresh()
        {
            if (RefreshCommand != null) RefreshCommand.Cancel();
        }

        private void RecordConnectionState(bool connected)
        {
            if (_lastConnectionState.HasValue && _lastConnectionState.Value != connected && _notifier != null)
                _notifier.ConnectionChanged(connected);
            _lastConnectionState = connected;
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
            if (String.Equals(value, "START_PENDING", StringComparison.Ordinal) || String.Equals(value, "CONTINUE_PENDING", StringComparison.Ordinal)) return Strings.Starting;
            if (String.Equals(value, "STOP_PENDING", StringComparison.Ordinal) || String.Equals(value, "PAUSE_PENDING", StringComparison.Ordinal)) return Strings.Stopping;
            if (String.Equals(value, "ACCESS_DENIED", StringComparison.Ordinal)) return Strings.AccessDenied;
            if (String.Equals(value, "NOT_INSTALLED", StringComparison.Ordinal)) return "Not installed";
            if (String.Equals(value, "QUERY_FAILED", StringComparison.Ordinal)) return "Query failed";
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

        private static string DisplayWorkerState(string value)
        {
            if (String.Equals(value, "WORKER_READY", StringComparison.Ordinal) ||
                String.Equals(value, "READY", StringComparison.Ordinal)) return Strings.Ready;
            if (String.Equals(value, "WORKER_STARTING", StringComparison.Ordinal)) return Strings.Starting;
            if (String.Equals(value, "WORKER_STOPPING", StringComparison.Ordinal)) return Strings.Stopping;
            if (String.Equals(value, "WORKER_STOPPED", StringComparison.Ordinal) ||
                String.Equals(value, "WORKER_MISSING", StringComparison.Ordinal) ||
                String.Equals(value, "DISCONNECTED", StringComparison.Ordinal)) return Strings.Disconnected;
            if (String.Equals(value, "WORKER_FAILED", StringComparison.Ordinal) ||
                String.Equals(value, "MT5_RUNTIME_UNHEALTHY", StringComparison.Ordinal)) return Strings.Error;
            return DisplayState(value);
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
            if (disposing) { StartServiceCommand.Dispose(); StopServiceCommand.Dispose(); RestartServiceCommand.Dispose(); }
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
