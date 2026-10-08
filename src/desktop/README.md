# MT5Agent Desktop — WPF Foundation and Management IPC

**State:** Phase 1 WPF foundation plus Phase 2 read-only Management IPC are
implemented. The official .NET Framework 4.8 targeting-pack build and tests
passed on one Windows 10 runner. Interactive visual verification and the
remaining supported OS matrix are still unverified.

## Implemented

- `MT5Agent.Desktop.sln`: x64 WPF application and dependency-free .NET
  Framework 4.8 test executable; MVVM base, navigation, commands, composition,
  cancellation, disposal, centralized errors, English `.resx` resources and
  light/dark per-user preferences.
- Dashboard, Runtime, Settings, Logs, Diagnostics and About views. Accounts,
  Security, Updates and Support are explicitly informational/unavailable.
- `NamedPipeManagementClient` communicates asynchronously only with
  `MT5Agent.Management.v1`. It applies a 64 KiB limit, two-second timeout,
  cancellation, correlation/version validation and bounded reconnect attempts.
- Python Management IPC accepts only `protocol.negotiate` and read-only
  `status.get`, uses an explicit user SID allowlist plus caller-token identity,
  and returns an observed Agent/Worker/MT5 projection. Central reports
  `NOT_CONFIGURED`; trading reports `UNSUPPORTED` and `NOT_AUTHORIZED`.
- With the Service stopped or allowlist missing, the UI remains available and
  presents offline/unavailable state. The UI does not call `/command` or open
  the internal Worker pipe. No trade or Service control exists.

## Build and run on Windows x64

Prerequisites:

- Windows 10 x64, Windows 11 x64, or Windows Server 2022/2025 x64 with Desktop
  Experience. Server Core and other Windows versions are unsupported.
- Official .NET Framework 4.8 Developer/Targeting Pack and .NET Framework 4.8
  or later runtime. Visual Studio is not required if MSBuild and the targeting
  pack are installed.
- The Python Agent/MT5 Worker is not required to build or launch the UI.

```powershell
cd src\desktop
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\MSBuild.exe .\MT5Agent.Desktop.sln /t:Rebuild /p:Configuration=Release /p:Platform=x64 /m:1 /nologo /verbosity:minimal
.\MT5Agent.Desktop.Tests\bin\Release\MT5Agent.Desktop.Tests.exe
.\MT5Agent.Desktop\bin\Release\MT5Agent.Desktop.exe
```

The test executable prints individual PASS/FAIL lines and exits nonzero on
failure; it needs no test package restore.

## Enable the Python status pipe

On the already provisioned Agent host, a machine administrator configures
`MT5_AGENT_MANAGEMENT_ALLOWED_SIDS` in the Agent Service process environment
with the exact comma-separated Windows user SID(s) allowed to read local
status, then restarts the Agent. An empty/missing allowlist disables the
management pipe. Do not use `Everyone` or send caller identity in request JSON.
The Service identity is also included in the pipe DACL for server operations.

## Verification evidence — 2026-10-08

- Windows 10 Pro 22H2 x64: official Microsoft-signed .NET Framework 4.8
  Developer Pack installed; reference assemblies confirmed present. Clean
  Release x64 MSBuild `4.8.9037.0` rebuild succeeded without
  `FrameworkPathOverride`.
- WPF/ViewModel/Management IPC tests: **27 passed, 0 failed**.
- Windows Python Management IPC tests: **15 passed, 0 failed**.
- Linux Python regression suite: **268 passed, 36 skipped**. Skips are not
  counted as passes.
- Isolated security spike proved actual Named Pipe caller SID extraction,
  DACL allow/deny, impersonation restoration/fail-closed behavior, forged SID
  claim rejection and LocalSystem Session 0 to interactive Session 1.
- Cross-language Python Session 0 → C# Session 1 smoke passed with a synthetic
  status fixture. It did not query production Agent/Worker/MT5 or broker state.
- `.gitlab-ci.yml` includes `test:wpf-management`, but no GitLab pipeline job
  was run for this branch.

## Remaining limitations

| Area | State | Evidence gap or boundary |
|---|---|---|
| Interactive visual/DPI/UI Automation review | Not verified | CI runner is Session 0; no screenshot or interactive UIA run. |
| Supported OS matrix | Partially verified | Only Windows 10 Pro 22H2 build/test evidence; Windows 11 and Server 2022/2025 not run. |
| Production Agent Service identity/provisioning | Open | Spike used disposable LocalSystem service. SID list is configured manually; no reader group provisioning. |
| Multi-user/multi-session behavior | Partial | Session 0/1 communication tested; full multiple-user isolation matrix not run. |
| Service start/stop and Runtime restart | Not implemented | No privileged operation or custom helper. SCM/UAC guidance only. |
| Logs, diagnostics collection, support export, tray, notifications | Planned | Pages are informational; no data collection or external transmission. |
| Packaging and release | Not implemented | Reproducible UI build is verified; user-scope deployment package and same-artifact release flow remain future gates. |
| Performance, memory, CPU, soak | Not measured | Dispatcher responsiveness covered by unit harness, not commercial thresholds. |

No real trades were executed. The earlier Phase 1 build evidence used the
runner's installed runtime assemblies before the official Developer Pack was
installed; the Phase 2 build above supersedes it for clean targeting-pack
verification. See [Implementation Baseline](../../docs/architecture/IMPLEMENTATION_BASELINE.md)
and [IPC Contract](../../docs/architecture/IPC_CONTRACT.md).
