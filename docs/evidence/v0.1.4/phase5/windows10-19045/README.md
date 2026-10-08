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

## GitLab and release boundary

No Phase 5 GitLab pipeline or deployable package is represented by this local
evidence bundle. Phase 4 pipeline #45 is historical only. No trade was executed;
no Windows 11 or Windows Server environment was created or tested.
