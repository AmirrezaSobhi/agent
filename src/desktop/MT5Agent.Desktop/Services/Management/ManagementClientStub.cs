using System.Threading;
using System.Threading.Tasks;

namespace MT5Agent.Desktop.Services
{
    /// <summary>Phase 1 placeholder. It does not inspect a Service, pipe, terminal or account.</summary>
    public sealed class UnavailableManagementClient : IManagementClient
    {
        public async Task<ManagementStatus> GetStatusAsync(CancellationToken cancellationToken)
        {
            await Task.Delay(350, cancellationToken).ConfigureAwait(false);
            return new ManagementStatus
            {
                AgentState = "Unavailable",
                RuntimeState = "Unavailable",
                Mt5State = "Unavailable",
                IsObserved = false,
                Reason = Resources.Strings.NoRuntimeStatusQueried
            };
        }
    }
}
