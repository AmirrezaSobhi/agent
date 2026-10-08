using System.Threading;
using System.Threading.Tasks;

namespace MT5Agent.Desktop.Services
{
    public interface IManagementClient
    {
        Task<ManagementStatus> GetStatusAsync(CancellationToken cancellationToken);
    }

    public sealed class ManagementStatus
    {
        public string AgentState { get; set; }
        public string WorkerState { get; set; }
        public string RuntimeState { get; set; }
        public bool Mt5Connected { get; set; }
        public string CentralState { get; set; }
        public string TradingCapability { get; set; }
        public string TradingAuthorized { get; set; }
        public bool IsObserved { get; set; }
        public bool IsStale { get; set; }
        public System.DateTime? ObservedAtUtc { get; set; }
        public string ErrorCode { get; set; }
        public string Reason { get; set; }
    }
}
