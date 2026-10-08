using System;
using System.Threading;
using System.Threading.Tasks;
using MT5Agent.Desktop.Resources;
using MT5Agent.Desktop.Services;
using MT5Agent.Desktop.ViewModels.Commands;

namespace MT5Agent.Desktop.ViewModels
{
    public sealed class RuntimeViewModel : ViewModelBase
    {
        private readonly IManagementClient _management;
        private readonly IErrorHandler _errors;
        private CancellationTokenSource _refreshCancellation;
        private ManagementStatus _status;
        private bool _isLoading;
        private string _error;
        private string _lastObserved;

        public RuntimeViewModel(IManagementClient management, IErrorHandler errors)
        {
            _management = management; _errors = errors;
            _lastObserved = Strings.NoObservationYet;
            RefreshCommand = new AsyncCommand(RefreshAsync, errors);
        }

        public string Title { get { return Strings.NavRuntime; } }
        public string SectionLabel { get { return Strings.SectionRuntime; } }
        public string Description { get { return Strings.RuntimeOperationsDescription; } }
        public bool IsLoading { get { return _isLoading; } private set { SetProperty(ref _isLoading, value); } }
        public bool HasStatus { get { return _status != null && _status.IsObserved; } }
        public bool IsStale { get { return Error != null || (_status != null && (_status.IsStale || !_status.IsObserved)); } }
        public string AgentState { get { return HasStatus ? Display(_status.AgentState) : Strings.Unavailable; } }
        public string WorkerState { get { return HasStatus ? Display(_status.WorkerState) : Strings.Unavailable; } }
        public string RuntimeState { get { return HasStatus ? Display(_status.RuntimeState) : Strings.Unavailable; } }
        public string Mt5State { get { return HasStatus ? Display(_status.Mt5State) : Strings.Unavailable; } }
        public string SourceIdentity { get { return HasStatus ? _status.SourceIdentity : Strings.NotObserved; } }
        public string LastObservation { get { return _lastObserved; } private set { SetProperty(ref _lastObserved, value); } }
        public string Error { get { return _error; } private set { SetProperty(ref _error, value); } }
        public string RuntimeIdentity { get { return Strings.RuntimeIdentityNotExposed; } }
        public string ProcessSession { get { return Strings.ProcessSessionNotExposed; } }
        public string RecoveryGuidance { get { return Error == null ? Strings.RuntimeRecoveryDefault : Error; } }
        public AsyncCommand RefreshCommand { get; private set; }

        public async Task RefreshAsync(CancellationToken cancellationToken)
        {
            IsLoading = true; Error = null;
            _refreshCancellation = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            try
            {
                var value = await _management.GetStatusAsync(_refreshCancellation.Token);
                if (value != null && value.IsObserved)
                {
                    _status = value;
                    LastObservation = value.ObservedAtUtc.HasValue
                        ? String.Format(Strings.ObservedAt, value.ObservedAtUtc.Value.ToLocalTime().ToString("g"))
                        : Strings.NoObservationYet;
                }
                else Error = value == null ? Strings.RuntimeStatusUnavailable : SafeCode(value.ErrorCode);
                NotifyStatus();
            }
            catch (OperationCanceledException) { throw; }
            catch (ManagementIpcException ex) { Error = SafeCode(ex.Code); _errors.Handle(ex, "Runtime.Refresh"); NotifyStatus(); }
            catch (Exception ex) { Error = Strings.RuntimeStatusUnavailable; _errors.Handle(ex, "Runtime.Refresh"); NotifyStatus(); }
            finally { IsLoading = false; if (_refreshCancellation != null) { _refreshCancellation.Dispose(); _refreshCancellation = null; } }
        }

        public void CancelRefresh() { if (_refreshCancellation != null) _refreshCancellation.Cancel(); if (RefreshCommand != null) RefreshCommand.Cancel(); }
        private void NotifyStatus()
        {
            OnPropertyChanged("HasStatus"); OnPropertyChanged("IsStale"); OnPropertyChanged("AgentState");
            OnPropertyChanged("WorkerState"); OnPropertyChanged("RuntimeState"); OnPropertyChanged("Mt5State");
            OnPropertyChanged("SourceIdentity"); OnPropertyChanged("RecoveryGuidance");
        }
        private static string Display(string value) { return String.IsNullOrWhiteSpace(value) ? Strings.Unknown : value.Replace('_', ' '); }
        private static string SafeCode(string code) { return String.Format(Strings.RuntimeErrorCode, String.IsNullOrWhiteSpace(code) ? "UNKNOWN" : code); }

        protected override void Dispose(bool disposing)
        {
            if (disposing) { CancelRefresh(); if (RefreshCommand != null) RefreshCommand.Dispose(); }
            base.Dispose(disposing);
        }
    }
}
