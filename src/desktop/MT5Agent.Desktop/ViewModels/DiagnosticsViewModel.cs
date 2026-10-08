using System;
using System.Collections.ObjectModel;
using System.IO;
using System.Reflection;
using Microsoft.Win32;
using System.Threading;
using System.Threading.Tasks;
using MT5Agent.Desktop.Resources;
using MT5Agent.Desktop.Services;
using MT5Agent.Desktop.ViewModels.Commands;

namespace MT5Agent.Desktop.ViewModels
{
    public sealed class DiagnosticItem
    {
        public DiagnosticItem(string name, string value) { Name = name; Value = value; }
        public string Name { get; private set; }
        public string Value { get; private set; }
    }

    public sealed class DiagnosticsViewModel : ViewModelBase
    {
        private readonly IManagementClient _management;
        private readonly IErrorHandler _errors;
        private bool _isLoading;
        private string _lastResponse = Strings.NoObservationYet;
        private string _connectionError = Strings.NoConnectionError;

        public DiagnosticsViewModel(IManagementClient management, IErrorHandler errors)
        {
            _management = management; _errors = errors;
            Items = new ObservableCollection<DiagnosticItem>();
            RefreshCommand = new AsyncCommand(RefreshAsync, errors);
            Add("UI version", Assembly.GetExecutingAssembly().GetName().Version.ToString());
            Add(".NET Framework target", "4.8 · CLR " + Environment.Version);
            Add("Operating system", GetOperatingSystemDisplayName());
            Add("Management protocol", "v1 · " + NamedPipeManagementClient.PipeName);
            Add("Central connection", "Local Setup · Not configured");
            Add("Trading capability", "Unsupported in this release");
        }

        public ObservableCollection<DiagnosticItem> Items { get; private set; }
        public AsyncCommand RefreshCommand { get; private set; }
        public string Title { get { return Strings.DiagnosticsTitle; } }
        public string SectionLabel { get { return Strings.SectionHealth; } }
        public string Description { get { return Strings.DiagnosticsLocalDescription; } }
        public string LastResponse { get { return _lastResponse; } private set { SetProperty(ref _lastResponse, value); } }
        public string ConnectionError { get { return _connectionError; } private set { SetProperty(ref _connectionError, value); } }
        public bool IsLoading { get { return _isLoading; } private set { SetProperty(ref _isLoading, value); } }

        public async Task RefreshAsync(CancellationToken cancellationToken)
        {
            IsLoading = true; ConnectionError = Strings.CheckingConnection;
            try
            {
                var status = await _management.GetStatusAsync(cancellationToken);
                if (status == null || !status.IsObserved) { ConnectionError = Strings.DiagnosticsAgentUnavailable; return; }
                LastResponse = status.ObservedAtUtc.HasValue ? status.ObservedAtUtc.Value.ToLocalTime().ToString("G") : Strings.Unknown;
                ConnectionError = String.IsNullOrWhiteSpace(status.ErrorCode) || status.ErrorCode == "OK"
                    ? Strings.NoConnectionError : String.Format(Strings.RuntimeErrorCode, status.ErrorCode);
                SetItem("Agent", status.AgentState);
                SetItem("Worker", status.WorkerState);
                SetItem("MT5", status.Mt5State);
                SetItem("Management source", status.SourceIdentity);
                SetItem("Status freshness", status.IsStale ? "Stale" : "Fresh");
            }
            catch (OperationCanceledException) { throw; }
            catch (ManagementIpcException ex)
            {
                ConnectionError = String.Format(Strings.RuntimeErrorCode, ex.Code);
                if (!IsExpectedUnavailable(ex.Code)) _errors.Handle(ex, "Diagnostics.Refresh");
            }
            catch (Exception ex) { ConnectionError = Strings.DiagnosticsAgentUnavailable; _errors.Handle(ex, "Diagnostics.Refresh"); }
            finally { IsLoading = false; }
        }

        private void Add(string name, string value) { Items.Add(new DiagnosticItem(name, value)); }

        private static string GetOperatingSystemDisplayName()
        {
            // Environment.OSVersion can report a compatibility-shimmed version when
            // the executable has no supportedOS manifest. Read public OS labels from
            // the Windows CurrentVersion key instead of presenting a misleading NT version.
            try
            {
                using (var key = Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\Windows NT\CurrentVersion", false))
                {
                    if (key != null)
                    {
                        var product = key.GetValue("ProductName") as string;
                        var displayVersion = key.GetValue("DisplayVersion") as string;
                        var build = key.GetValue("CurrentBuildNumber") as string;
                        var ubr = key.GetValue("UBR");
                        var version = !String.IsNullOrWhiteSpace(build)
                            ? build + (ubr == null ? String.Empty : "." + Convert.ToString(ubr))
                            : String.Empty;
                        var parts = new[] { product, displayVersion, version };
                        var result = String.Join(" ", Array.FindAll(parts, value => !String.IsNullOrWhiteSpace(value)));
                        if (!String.IsNullOrWhiteSpace(result)) return result;
                    }
                }
            }
            catch (System.Security.SecurityException) { }
            catch (UnauthorizedAccessException) { }
            catch (IOException) { }
            return "Unknown";
        }

        private static bool IsExpectedUnavailable(string code)
        {
            return code == "PIPE_NOT_FOUND" || code == "PIPE_BROKEN" || code == "PIPE_BUSY" ||
                code == "ACCESS_DENIED" || code == "TIMEOUT" || code == "SERVICE_UNAVAILABLE";
        }

        private void SetItem(string name, string value)
        {
            for (var i = 0; i < Items.Count; i++) if (Items[i].Name == name) { Items[i] = new DiagnosticItem(name, String.IsNullOrWhiteSpace(value) ? Strings.Unknown : value); return; }
            Add(name, value);
        }
    }
}
