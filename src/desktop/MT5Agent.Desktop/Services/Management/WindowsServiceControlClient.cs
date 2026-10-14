using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;

namespace MT5Agent.Desktop.Services
{
    public enum ServiceAction { Start, Stop, Restart }

    public sealed class ServiceObservation
    {
        public string State { get; set; }
        public bool Installed { get; set; }
        public bool CanStart { get; set; }
        public bool CanStop { get; set; }
        public string ErrorCode { get; set; }
        public DateTime ObservedAtUtc { get; set; }
    }

    public sealed class ServiceActionResult
    {
        public bool Succeeded { get; set; }
        public string Code { get; set; }
        public string State { get; set; }
    }

    public interface IServiceControlClient
    {
        Task<ServiceObservation> QueryAsync(CancellationToken cancellationToken);
        Task<ServiceActionResult> ExecuteAsync(ServiceAction action, CancellationToken cancellationToken);
    }

    /// <summary>
    /// Uses only SCM APIs against the fixed product service name. Windows checks
    /// the logged-on token against per-operation service ACL rights; this client
    /// never elevates, changes ACLs, or starts arbitrary processes.
    /// </summary>
    public sealed class WindowsServiceControlClient : IServiceControlClient
    {
        public const string ServiceName = "MT5Agent";
        private const uint ScManagerConnect = 0x0001;
        private const uint ServiceQueryStatus = 0x0004;
        private const uint ServiceStart = 0x0010;
        private const uint ServiceStop = 0x0020;
        private const uint ServiceControlStop = 0x00000001;
        private const uint ScStatusProcessInfo = 0;
        private const int ErrorAccessDenied = 5;
        private const int ErrorServiceDoesNotExist = 1060;
        private const int ErrorServiceAlreadyRunning = 1056;
        private const int ErrorServiceNotActive = 1062;
        private const int ErrorServiceCannotAcceptControl = 1061;
        private readonly SemaphoreSlim _operation = new SemaphoreSlim(1, 1);

        public Task<ServiceObservation> QueryAsync(CancellationToken cancellationToken)
        {
            return Task.Run(() => { cancellationToken.ThrowIfCancellationRequested(); return Query(); }, cancellationToken);
        }

        public async Task<ServiceActionResult> ExecuteAsync(ServiceAction action, CancellationToken cancellationToken)
        {
            if (!await _operation.WaitAsync(0, cancellationToken).ConfigureAwait(false))
                return new ServiceActionResult { Code = "OPERATION_IN_PROGRESS", State = "UNKNOWN" };
            try
            {
                cancellationToken.ThrowIfCancellationRequested();
                var desired = action == ServiceAction.Start ? ServiceStart : ServiceStop;
                if (action == ServiceAction.Restart) desired |= ServiceStart;
                using (var service = OpenService(ServiceQueryStatus | desired))
                {
                    if (service == null) return FromLastError();
                    var state = QueryState(service);
                    if (action == ServiceAction.Start)
                    {
                        if (state == "RUNNING") return Result(true, "ALREADY_RUNNING", state);
                        if (state != "STOPPED") return Result(false, "SERVICE_BUSY", state);
                        if (!StartServiceNative(service, 0, IntPtr.Zero))
                        {
                            var error = Marshal.GetLastWin32Error();
                            if (error == ErrorServiceAlreadyRunning) return Result(true, "ALREADY_RUNNING", "RUNNING");
                            return FromError(error);
                        }
                        return await WaitForStateAsync("RUNNING", cancellationToken).ConfigureAwait(false);
                    }
                    if (action == ServiceAction.Stop || action == ServiceAction.Restart)
                    {
                        if (state == "STOPPED")
                        {
                            if (action == ServiceAction.Stop) return Result(true, "ALREADY_STOPPED", state);
                        }
                        else if (state != "STOP_PENDING")
                        {
                            var status = new ServiceStatus { CurrentState = 0 };
                            if (!ControlServiceNative(service, ServiceControlStop, ref status))
                            {
                                var error = Marshal.GetLastWin32Error();
                                if (error != ErrorServiceNotActive && error != ErrorServiceCannotAcceptControl)
                                    return FromError(error);
                            }
                        }
                        var stopped = await WaitForStateAsync("STOPPED", cancellationToken).ConfigureAwait(false);
                        if (!stopped.Succeeded || action == ServiceAction.Stop) return stopped;
                        cancellationToken.ThrowIfCancellationRequested();
                        if (!StartServiceNative(service, 0, IntPtr.Zero))
                        {
                            var error = Marshal.GetLastWin32Error();
                            if (error != ErrorServiceAlreadyRunning) return FromError(error);
                        }
                        return await WaitForStateAsync("RUNNING", cancellationToken).ConfigureAwait(false);
                    }
                }
                return Result(false, "UNSUPPORTED_OPERATION", "UNKNOWN");
            }
            catch (OperationCanceledException) { return Result(false, "CANCELLED_OUTCOME_UNKNOWN", "UNKNOWN"); }
            catch (Win32Exception ex) { return FromError(ex.NativeErrorCode); }
            finally { _operation.Release(); }
        }

        private async Task<ServiceActionResult> WaitForStateAsync(string expected, CancellationToken cancellationToken)
        {
            var deadline = DateTime.UtcNow.AddSeconds(20);
            while (DateTime.UtcNow < deadline)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var observation = Query();
                if (observation.State == expected) return Result(true, "COMPLETED", expected);
                if (observation.ErrorCode != null) return Result(false, observation.ErrorCode, observation.State);
                await Task.Delay(250, cancellationToken).ConfigureAwait(false);
            }
            return Result(false, "TIMEOUT_OUTCOME_UNKNOWN", Query().State);
        }

        private static ServiceObservation Query()
        {
            using (var service = OpenService(ServiceQueryStatus))
            {
                if (service == null) return ObservationFromError(Marshal.GetLastWin32Error());
                var state = QueryState(service);
                var start = HasAccess(ServiceStart);
                var stop = HasAccess(ServiceStop);
                return new ServiceObservation { Installed = true, State = state,
                    CanStart = start, CanStop = stop, ErrorCode = state == "UNKNOWN" ? "QUERY_FAILED" : null,
                    ObservedAtUtc = DateTime.UtcNow };
            }
        }

        private static bool HasAccess(uint access)
        {
            using (var service = OpenService(access)) return service != null;
        }

        private static string QueryState(SafeScHandle service)
        {
            var buffer = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(ServiceStatusProcess)));
            try
            {
                int needed;
                if (!QueryServiceStatusEx(service, ScStatusProcessInfo, buffer,
                    Marshal.SizeOf(typeof(ServiceStatusProcess)), out needed)) return "UNKNOWN";
                var status = (ServiceStatusProcess)Marshal.PtrToStructure(buffer, typeof(ServiceStatusProcess));
                switch (status.CurrentState)
                {
                    case 1: return "STOPPED"; case 2: return "START_PENDING"; case 3: return "STOP_PENDING";
                    case 4: return "RUNNING"; case 5: return "CONTINUE_PENDING"; case 6: return "PAUSE_PENDING";
                    case 7: return "PAUSED"; default: return "UNKNOWN";
                }
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        private static SafeScHandle OpenService(uint access)
        {
            var manager = OpenSCManager(null, null, ScManagerConnect);
            if (manager == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error());
            try
            {
                var service = OpenServiceNative(manager, ServiceName, access);
                return service == IntPtr.Zero ? null : new SafeScHandle(service, true);
            }
            finally { CloseServiceHandle(manager); }
        }

        private static ServiceActionResult FromLastError() { return FromError(Marshal.GetLastWin32Error()); }
        private static ServiceActionResult FromError(int error)
        {
            var code = error == ErrorAccessDenied ? "ACCESS_DENIED" :
                error == ErrorServiceDoesNotExist ? "NOT_INSTALLED" : "SERVICE_OPERATION_FAILED";
            return Result(false, code, "UNKNOWN");
        }
        private static ServiceObservation ObservationFromError(int error)
        {
            var code = error == ErrorAccessDenied ? "ACCESS_DENIED" :
                error == ErrorServiceDoesNotExist ? "NOT_INSTALLED" : "QUERY_FAILED";
            return new ServiceObservation { Installed = error != ErrorServiceDoesNotExist,
                State = code == "NOT_INSTALLED" ? "NOT_INSTALLED" : code, ErrorCode = code, ObservedAtUtc = DateTime.UtcNow };
        }
        private static ServiceActionResult Result(bool success, string code, string state)
        { return new ServiceActionResult { Succeeded = success, Code = code, State = state }; }

        private sealed class SafeScHandle : SafeHandle
        {
            public SafeScHandle(IntPtr handle, bool owns) : base(IntPtr.Zero, owns) { SetHandle(handle); }
            public override bool IsInvalid { get { return handle == IntPtr.Zero; } }
            protected override bool ReleaseHandle() { return CloseServiceHandle(handle); }
        }
        [StructLayout(LayoutKind.Sequential)] private struct ServiceStatusProcess
        { public uint ServiceType, CurrentState, ControlsAccepted, Win32ExitCode, ServiceSpecificExitCode, CheckPoint, WaitHint, ProcessId, ServiceFlags; }
        [StructLayout(LayoutKind.Sequential)] private struct ServiceStatus
        { public uint ServiceType, CurrentState, ControlsAccepted, Win32ExitCode, ServiceSpecificExitCode, CheckPoint, WaitHint; }
        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern IntPtr OpenSCManager(string machine, string database, uint access);
        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true, EntryPoint = "OpenServiceW")] private static extern IntPtr OpenServiceNative(IntPtr manager, string name, uint access);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool CloseServiceHandle(IntPtr handle);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool QueryServiceStatusEx(SafeScHandle service, uint level, IntPtr buffer, int size, out int needed);
        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true, EntryPoint = "StartServiceW")] private static extern bool StartServiceNative(SafeScHandle service, int argumentCount, IntPtr arguments);
        [DllImport("advapi32.dll", SetLastError = true, EntryPoint = "ControlService")] private static extern bool ControlServiceNative(SafeScHandle service, uint control, ref ServiceStatus status);
    }
}
