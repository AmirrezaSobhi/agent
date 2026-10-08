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
        public string RuntimeState { get; set; }
        public string Mt5State { get; set; }
        public bool IsObserved { get; set; }
        public string Reason { get; set; }
    }
}
