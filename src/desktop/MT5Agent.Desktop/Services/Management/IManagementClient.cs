using System.Threading;
using System.Threading.Tasks;

namespace MT5Agent.Desktop.Services
{
    public interface IManagementClient
    {
        Task<ManagementStatus> GetStatusAsync(CancellationToken cancellationToken);
        Task<System.Collections.Generic.IList<ManagementLogEntry>> GetLogsAsync(int limit, string severity, CancellationToken cancellationToken);
    }

    public sealed class ManagementLogEntry
    {
        public System.DateTime TimestampUtc { get; set; }
        public string Severity { get; set; }
        public string Source { get; set; }
        public string Code { get; set; }
        public string Message { get; set; }
    }

    public sealed class ManagementStatus
    {
        public string ServiceState { get; set; }
        public string AgentState { get; set; }
        public string AgentLifecycleState { get; set; }
        public string ManagementState { get; set; }
        public string WorkerState { get; set; }
        public string RuntimeState { get; set; }
        public string Mt5State { get; set; }
        public bool Mt5Connected { get; set; }
        public string CentralState { get; set; }
        public string TradingCapability { get; set; }
        public string TradingAuthorized { get; set; }
        public string TradingReadiness { get; set; }
        public string SourceIdentity { get; set; }
        public string CorrelationId { get; set; }
        public string Freshness { get; set; }
        public bool IsObserved { get; set; }
        public bool IsStale { get; set; }
        public System.DateTime? ObservedAtUtc { get; set; }
        public string ErrorCode { get; set; }
        public string Reason { get; set; }
    }
}
