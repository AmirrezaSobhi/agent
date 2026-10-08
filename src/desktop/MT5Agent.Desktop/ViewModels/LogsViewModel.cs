using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using MT5Agent.Desktop.Resources;
using MT5Agent.Desktop.Services;
using MT5Agent.Desktop.ViewModels.Commands;

namespace MT5Agent.Desktop.ViewModels
{
    public sealed class LogsViewModel : ViewModelBase
    {
        private readonly IManagementClient _management;
        private readonly IErrorHandler _errors;
        private CancellationTokenSource _loadCancellation;
        private string _severity = "ALL";
        private string _searchText;
        private bool _isLoading;
        private string _message = Strings.NoLogs;

        public LogsViewModel(IManagementClient management, IErrorHandler errors)
        {
            _management = management; _errors = errors;
            Entries = new ObservableCollection<ManagementLogEntry>();
            FilteredEntries = new ObservableCollection<ManagementLogEntry>();
            LoadCommand = new AsyncCommand(LoadAsync, errors);
        }

        public ObservableCollection<ManagementLogEntry> Entries { get; private set; }
        public ObservableCollection<ManagementLogEntry> FilteredEntries { get; private set; }
        public AsyncCommand LoadCommand { get; private set; }
        public string Title { get { return Strings.LogsTitle; } }
        public string SectionLabel { get { return Strings.SectionOperations; } }
        public string Description { get { return Strings.LogsOperationalDescription; } }
        public string Message { get { return _message; } private set { SetProperty(ref _message, value); } }
        public bool IsLoading { get { return _isLoading; } private set { SetProperty(ref _isLoading, value); } }
        public string Severity { get { return _severity; } set { if (SetProperty(ref _severity, value)) ApplyFilter(); } }
        public string SearchText { get { return _searchText; } set { if (SetProperty(ref _searchText, value)) ApplyFilter(); } }
        public bool HasEntries { get { return FilteredEntries.Count != 0; } }

        public async Task LoadAsync(CancellationToken cancellationToken)
        {
            IsLoading = true; Message = Strings.LoadingLogs;
            _loadCancellation = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            try
            {
                var result = await _management.GetLogsAsync(100, "ALL", _loadCancellation.Token);
                Entries.Clear();
                foreach (var item in result.Take(100)) Entries.Add(item);
                ApplyFilter();
                Message = Entries.Count == 0 ? Strings.NoManagementEvents : Strings.LogsSourceNotice;
            }
            catch (OperationCanceledException) { throw; }
            catch (ManagementIpcException ex)
            {
                Entries.Clear(); FilteredEntries.Clear(); NotifyHasEntries();
                Message = String.Format(Strings.LogsUnavailableCode, ex.Code);
                if (!IsExpectedUnavailable(ex.Code)) _errors.Handle(ex, "Logs.Load");
            }
            catch (Exception ex)
            {
                Entries.Clear(); FilteredEntries.Clear(); NotifyHasEntries();
                Message = Strings.LogsUnavailable; _errors.Handle(ex, "Logs.Load");
            }
            finally { IsLoading = false; if (_loadCancellation != null) { _loadCancellation.Dispose(); _loadCancellation = null; } }
        }

        public void CancelLoad() { if (_loadCancellation != null) _loadCancellation.Cancel(); if (LoadCommand != null) LoadCommand.Cancel(); }

        private void ApplyFilter()
        {
            FilteredEntries.Clear();
            var search = (SearchText ?? String.Empty).Trim();
            foreach (var entry in Entries)
            {
                if (Severity != "ALL" && !String.Equals(entry.Severity, Severity, StringComparison.OrdinalIgnoreCase)) continue;
                if (search.Length > 0 && !((entry.Message ?? String.Empty).IndexOf(search, StringComparison.OrdinalIgnoreCase) >= 0 ||
                    (entry.Code ?? String.Empty).IndexOf(search, StringComparison.OrdinalIgnoreCase) >= 0 ||
                    (entry.Source ?? String.Empty).IndexOf(search, StringComparison.OrdinalIgnoreCase) >= 0)) continue;
                FilteredEntries.Add(entry);
            }
            NotifyHasEntries();
        }

        private void NotifyHasEntries() { OnPropertyChanged("HasEntries"); }

        private static bool IsExpectedUnavailable(string code)
        {
            return code == "PIPE_NOT_FOUND" || code == "PIPE_BROKEN" || code == "PIPE_BUSY" ||
                code == "ACCESS_DENIED" || code == "TIMEOUT" || code == "SERVICE_UNAVAILABLE";
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing) { CancelLoad(); if (LoadCommand != null) LoadCommand.Dispose(); }
            base.Dispose(disposing);
        }
    }
}
