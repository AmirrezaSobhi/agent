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

    internal sealed class FakeManagementClient : IManagementClient
    {
        public Func<CancellationToken, Task<ManagementStatus>> Handler { get; set; }
        public Task<ManagementStatus> GetStatusAsync(CancellationToken cancellationToken)
        {
            if (Handler == null) return Task.FromResult(new ManagementStatus
                { IsObserved = false, Reason = "No secure connection is configured." });
            return Handler(cancellationToken);
        }
    }
}
