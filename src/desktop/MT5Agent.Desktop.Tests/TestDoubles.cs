using System;
using System.Threading;
using System.Threading.Tasks;
using MT5Agent.Desktop.Services;

namespace MT5Agent.Desktop.Tests
{
    internal sealed class FakeThemeService : IThemeService
    {
        public ThemePreference CurrentTheme { get; private set; }
        public int ApplyCount { get; private set; }
        public void Apply(ThemePreference theme) { CurrentTheme = theme; ApplyCount++; }
    }

    internal sealed class RecordingNotifier : IDesktopNotifier
    {
        public readonly System.Collections.Generic.List<bool> Transitions = new System.Collections.Generic.List<bool>();
        public void ConnectionChanged(bool connected) { Transitions.Add(connected); }
    }

    internal sealed class FakeManagementClient : IManagementClient
    {
        public Func<CancellationToken, Task<ManagementStatus>> Handler { get; set; }
        public Func<int, string, CancellationToken, Task<System.Collections.Generic.IList<ManagementLogEntry>>> LogsHandler { get; set; }
        public Task<ManagementStatus> GetStatusAsync(CancellationToken cancellationToken)
        {
            if (Handler == null) return Task.FromResult(new ManagementStatus
                { IsObserved = false, Reason = "No secure connection is configured." });
            return Handler(cancellationToken);
        }
        public Task<System.Collections.Generic.IList<ManagementLogEntry>> GetLogsAsync(int limit, string severity, CancellationToken cancellationToken)
        {
            return LogsHandler == null
                ? Task.FromResult<System.Collections.Generic.IList<ManagementLogEntry>>(new System.Collections.Generic.List<ManagementLogEntry>())
                : LogsHandler(limit, severity, cancellationToken);
        }
    }

    internal sealed class FakeServiceControlClient : IServiceControlClient
    {
        public Func<int, CancellationToken, Task<ServiceObservation>> QueryHandler { get; set; }
        public Func<ServiceAction, CancellationToken, Task<ServiceActionResult>> ExecuteHandler { get; set; }
        public int QueryCount { get; private set; }
        public ServiceAction? LastAction { get; private set; }
        public Task<ServiceObservation> QueryAsync(CancellationToken cancellationToken)
        { return QueryHandler(++QueryCount, cancellationToken); }
        public Task<ServiceActionResult> ExecuteAsync(ServiceAction action, CancellationToken cancellationToken)
        { LastAction = action; return ExecuteHandler(action, cancellationToken); }
    }
}
