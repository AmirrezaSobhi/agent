# v0.1.5 Service Startup Crash Analysis

## Observed failure

The Pipeline #73 controlled installation report states that the Installer
registered `MT5Agent`, then Windows Event 1026 recorded an
`InvalidOperationException` during `AgentService.OnStart`. SCM subsequently
reported Event 7023. The Installer correctly returned failure and its service
installation script removed the service it had just created. The original VM
log files are not present in this development worktree, so the Event 1026
message and stack were not independently re-read during this code change.

## Root cause in source

The installed layout places the service host in
`<install-root>\Service\MT5Agent.Service.exe` and the Python Agent in
`<install-root>\Agent\MT5Agent-v0.1.3.exe` (`deployment/installer/MT5Agent.iss`,
`[Files]`). The old `AgentService.OnStart` treated
`AppDomain.CurrentDomain.BaseDirectory` (the `Service` folder) as the install
root, then appended `Agent\MT5Agent-v0.1.3.exe`. It therefore checked the
nonexistent path `<install-root>\Service\Agent\MT5Agent-v0.1.3.exe` and threw
`AGENT_EXECUTABLE_MISSING_OR_OUTSIDE_INSTALL_ROOT` before launching the Agent.
This is a deterministic mismatch between the checked-in service code and the
Installer's checked-in payload layout; no Inno Setup API failure is needed to
explain the failure. The actual Event 1026 stack was unavailable here, so the
correlation to that exact guard is strong and code-supported, but not a direct
replay of the original exception text.

## Correction and safeguards

`AgentService` now validates that its executable directory is named `Service`
and resolves `Agent` from that directory's parent. It validates configured
SIDs using Windows `SecurityIdentifier`, logs startup stage, resolved path,
exception type/message/stack, and Win32 error context under
`%ProgramData%\MT5Agent\Logs\service-host.log`, with credential-like key/value
text redacted. Startup exceptions clean up the owned process/job and are
re-thrown with the original exception as the inner cause so SCM still observes
failure. A child that exits in the startup observation window fails startup;
an unexpected later exit is logged and requests a nonzero service stop. Stop
uses a bounded wait and closes only the Service-owned kill-on-close job.

## Validation boundary

The Windows CI test harness builds the .NET Framework 4.8 Service host and runs
disposable child-process lifecycle cases: correct sibling layout, missing
Agent, invalid layout/SID/configuration/working directory, immediate and later
child exit, duplicate start rejection, and stop/restart cleanup. These are
process-host tests, not a real SCM registration test, and do not reproduce
Session 0 on the dedicated VM. The VM was not changed or used to run this
candidate. A successful CI build/package does not establish live Service,
Agent IPC, Worker, WPF, or MT5 operation; a controlled VM retest remains
required.
