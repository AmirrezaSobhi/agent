# Phase 5 Windows 10 Evidence

Test environment: `WINDOW10-TEST` / `win10-runner`, Windows 10 Pro x64 22H2
build `19045.6466`, .NET Framework `4.8.09037` (release key `533325`),
official .NET Framework 4.8 targeting assemblies installed, MSBuild
`4.8.9037.0`. Interactive tests ran as local `Administrator` in console
Session 1, display `1280×800`, WPF window DPI `96` (100% scale). Session 0
LocalSystem was used for the Worker ACL experiment and a later isolated SCM
integration harness. No MT5 terminal/runtime or production Agent Service was
installed on this host. The temporary test Service was removed after testing.

Tested source package SHA-256:
`ee4417298240cfa8cb555b7f66cf774e76f66e9be3c040ac1d71e82f3d80778f`.
The source package was based on Phase 5 baseline commit
`9286e4f5640c979ccaf345b7fdf64a962d7e77bc` plus the uncommitted Phase 5 code
and test changes. It is a validation source archive, not a release package.

## Build and regression

Clean command:

```text
MSBuild.exe MT5Agent.Desktop.sln /t:Rebuild /p:Configuration=Release /p:Platform=x64 /m:1 /nologo /verbosity:minimal
```

The build used the official framework reference assemblies and no
`FrameworkPathOverride`. Results: WPF x64 Release build succeeded; C#
`41 passed, 0 failed`; Windows Python `318 passed, 2 skipped`; Linux portable
Python `276 passed, 36 skipped`. The two Windows skips were the gated Worker
ACL experiments. Those exact experiments were run separately in Session 0 and
passed `2/2` (`6 deselected`). No failures were hidden or skipped to obtain a
green result.

WPF application SHA-256 after the tested clean rebuild:
`3471c491722cc1b947f05e0caaff732764851e830c5f9de721c840a32a00a714`.
C# test executable SHA-256:
`aec6ac6b5db2aed8608b037e61d863e30a4dc468e67bf253e699afac78b6c050`.

## Interactive UI

The WPF application launched in interactive Session 1 while no product Agent
Service was installed. UI Automation navigated Dashboard, Runtime, Settings, Logs,
Diagnostics and About; switched Light/Dark themes; checked keyboard focus;
resized the window; minimized/restored it; enabled Close-to-tray; verified the
UI process remained alive when the window closed; and restored it by activating
the tray icon. The tray context menu's `Exit` item was not exposed to UI
Automation in this Phase 5 run and is recorded as unverified. The test process
was cleaned up, and the pre-test per-user preferences file bytes were restored.
Temporary scheduled tasks were removed.

The first Dashboard and Runtime run showed unavailable state because the Agent
Service was absent. Logs and Diagnostics showed the bounded Management pipe
timeout; no file paths or secrets were displayed. Screenshots are from the
actual interactive desktop, not Session 0/offscreen rendering.

## Worker ACL experiment

The ACL tests ran from a one-shot LocalSystem Session 0 scheduled task on the
isolated Windows 10 host. Actual caller SID: `S-1-5-18` (`NT AUTHORITY\\SYSTEM`).
Selected target principal: `WINDOW10-TEST\\Administrator`, SID
`S-1-5-21-950479549-2068523145-3370569714-500`, Session 1. The controlled
Worker fixture launched in a nonzero session; a duplicate launch was rejected;
cleanup succeeded; and Window Station/Desktop DACL rollback verification
passed. The original and temporarily changed descriptor hashes are recorded in
`worker-acl-dacl-rollback.json`. The temporary test task was removed. This is
not an installed Agent Service or MT5 Runtime test.

## Performance sample

See `performance-measurements.txt`. It records five startup samples, twenty
one-second idle process samples after warmup, ten offline Dashboard refresh
completion samples and ten navigation actions concurrent with those refreshes.
The Agent was offline, so this refresh metric is bounded unavailable/timeout
completion. Supplemental successful IPC measurements against a temporary SCM
test harness are recorded below; they do not represent a product Service.

## Supplemental SCM integration and security evidence

After explicit Product Owner authorization for a temporary Service and
rollback, a demand-start SCM entry `MT5AgentPhase5Test` was created on
`window10-test`. A temporary .NET Framework `ServiceBase` host ran the real
Python Agent Core in Session 0 with its Runtime adapter hard-disabled, HTTP
listener absent, and only the actual read-only Management Pipe exposed. This
was a test harness, not the product Service installer. It returned actual
Agent-Core status and bounded in-memory logs to the allowlisted Administrator
SID. The Service was stopped, restarted, and removed; evidence includes
[service lifecycle](service-lifecycle.txt), [Session 0 process context](service-process-context.json),
[sanitized Agent log](service-child-log.txt), [authorized status/latency probe](management-performance-probe.json),
[LocalSystem authorization denial](management-probe-system.json), and the
[NetworkService task failure](management-probe-networkservice.txt).

The live UI screenshot shows Management connected and Agent responsive while
the explicitly disabled Worker/MT5 adapter is disconnected; the [Dashboard](dashboard-live-service.png)
and [bounded Logs view](logs-live-service.png) were captured on the interactive
console. The WPF test process exited while the test SCM Service remained
running. SCM stop removed the Agent child and pipe; the authorized pipe probe
returned Win32 error 2 while stopped, and the restarted Service again returned
status and logs.

The allowed Administrator SID was
`S-1-5-21-950479549-2068523145-3370569714-500`. The Agent child token was
`S-1-5-18` in Session 0. A LocalSystem client could connect using the
Service-process DACL ACE, but `status.get` and `logs.query` returned
`UNAUTHORIZED`. The NetworkService negative task ended with `0x80070005` before
emitting a caller identity or probe result; it is not counted as a successful
runtime DACL-denial test. The Worker ACL experiments separately passed 2/2
with verified DACL rollback.

The test-harness IPC sample was 30 status requests (median 0.32 ms, P95 32.89
ms, max 33.15 ms) and 10 bounded log queries (median 0.30 ms, P95 31.57 ms,
up to 10 fixed events per response). It does not measure UI refresh latency,
production load, Worker/MT5, long soak, or repeated recovery.

## Final security closure — 2026-10-08

The previous NetworkService Scheduled Task failure (`0x80070005`) was not
reused as DACL evidence. A fresh `MT5AgentPhase5Test` SCM harness was created
and removed under the previously approved temporary-Service scope. It ran the
real Python Agent Core in Session 0 as LocalSystem (`S-1-5-18`) with the
Runtime adapter disabled and the explicit allowlist limited to the local
Administrator SID `S-1-5-21-950479549-2068523145-3370569714-500`.

An ordinary local account `MT5AgentDaclProbe` was created only for the test,
confirmed in `Users` and absent from `Administrators`, and removed afterward.
Its test SID was `S-1-5-21-950479549-2068523145-3370569714-1011`. The probe
obtained a Windows token using `LogonUser`, checked `TokenUser`, impersonated
that identity, performed `CreateFile` on
`\\.\pipe\MT5Agent.Management.v1`, and reverted impersonation in `finally`.
The calling process was the test Administrator in Session 0; the effective
calling thread token was the standard account in Session 0. The process never
used a caller-supplied SID as authentication evidence and sent no protocol
payload on the unauthorized path.

Observed runtime pipe SDDL: `D:(A;;FA;;;SY)(A;;0x12019b;;;LA)`. The `LA`
alias resolved to the explicitly allowlisted local Administrator SID. The
authorized Admin opened the same Pipe; 30/30 `status.get` and 10/10 bounded
`logs.query` requests returned `ok`. The standard-account impersonated
`CreateFile` returned native Win32 `5` (`ERROR_ACCESS_DENIED`) at the Windows
Pipe DACL boundary, before application authorization. The full sanitized
result, including account group membership, SIDs, process/session and cleanup
state, is [`negative-dacl-test-raw.json`](negative-dacl-test-raw.json). The
reusable test-only caller probe is
[`Phase5ManagementPipeDaclProbe.cs`](../../../../../tests/windows/Phase5ManagementPipeDaclProbe.cs).

The forged-caller-claim/default-deny check is
`test_default_deny_and_caller_claim_is_ignored` in
`tests/test_management_ipc_contract.py`; it asserts forged `claimed_sid` and
`caller_sid` values do not authorize a non-allowlisted actual SID and that
dispatch is not called. The new branch pipeline must execute this regression.

### Tray close and automation boundary

On the actual Windows 10 console desktop, the rebuilt WPF application ran in
Session 1. After saving `CloseToTray=true`, a window close left the UI process
alive while its main window became hidden. The preference was restored to
`false` after the run. `tray-close-to-tray-result.json` and
`tray-uia-tree.json` record the process state and Windows UIA tree. The UIA
provider exposed only the aggregate `User Promoted Notification Area`
`ToolbarWindow32`; it did not expose the app's NotifyIcon or context menu, so
the `Exit` menu item could not be invoked by this automation lane. This is an
automation-surface limitation, not evidence of an application failure or a
verified Tray Exit. The source path and `TrayLifecyclePolicyBehavior` unit
test remain evidence for explicit-exit logic; manual Exit verification remains
a release check.

The repeated tray automation attempt is [`tray-exit-uia-result.txt`](tray-exit-uia-result.txt).
It returned `PARTIAL`: close-to-tray passed, but tray-menu restore and Exit were
not exposed. No app process, temporary service, account, scheduled task, or
test profile remained afterward.

## GitLab and release boundary

Phase 5 Pipeline [#47](http://gitlab.local/root/agent/-/pipelines/47) passed all
9 jobs on baseline commit `b780a2c703891a2e407be153d547102fab44e58a`; it is
historical evidence and does not validate the final closure commit. The final
closure pipeline and exact commit will be recorded here after execution. The
pipeline job graph includes Windows validation, Windows/Linux regression, WPF
Management tests, Windows build, three smoke jobs, and packaging. No trade was
executed; no Windows 11 or Windows Server environment was created or tested.
