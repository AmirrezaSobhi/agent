using System.Threading;
using System.Threading.Tasks;

namespace MT5Agent.Desktop.Services
{
    /// <summary>Test-only client for deterministic unavailable/latency states.</summary>
    public sealed class UnavailableManagementClient : IManagementClient
    {
        public async Task<ManagementStatus> GetStatusAsync(CancellationToken cancellationToken)
        {
            await Task.Delay(350, cancellationToken).ConfigureAwait(false);
            return new ManagementStatus
            {
                AgentState = "Unavailable", WorkerState = "Unavailable", RuntimeState = "Unavailable",
                CentralState = "NOT_CONFIGURED", TradingCapability = "UNSUPPORTED",
                TradingAuthorized = "NOT_AUTHORIZED",
                IsObserved = false,
                ErrorCode = "PIPE_NOT_FOUND",
                Reason = Resources.Strings.NoRuntimeStatusQueried
            };
        }

        public async Task<System.Collections.Generic.IList<ManagementLogEntry>> GetLogsAsync(int limit, string severity,
            CancellationToken cancellationToken)
        {
            await Task.Delay(350, cancellationToken).ConfigureAwait(false);
            return new System.Collections.Generic.List<ManagementLogEntry>();
        }
    }
}
