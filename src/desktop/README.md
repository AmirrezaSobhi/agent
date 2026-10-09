# MT5Agent Desktop — WPF Foundation and Management IPC

**State:** v0.1.5 extends the accepted v0.1.4 x64 WPF application with local
SCM management, safer runtime diagnostics, optional log refresh and a versioned
Desktop-only package. Windows 10 x64 build and automated regression evidence
is recorded in the [v0.1.5 internal status](../../docs/releases/v0.1.5-internal-status.md).
Live Service lifecycle/denial integration remains unverified.

## Implemented

- `MT5Agent.Desktop.sln`: x64 WPF application and dependency-free .NET
  Framework 4.8 test executable; MVVM base, navigation, commands, composition,
  cancellation, disposal, centralized errors, English `.resx` resources and
  light/dark per-user preferences.
- Dashboard, Runtime, Settings, Logs, Diagnostics and About views. Accounts,
  Security, Updates, and Support remain explicitly unavailable.
- `NamedPipeManagementClient` communicates asynchronously only with
  `MT5Agent.Management.v1`. It applies a 64 KiB limit, two-second timeout,
  cancellation, correlation/version validation and bounded reconnect attempts.
- Python Management IPC accepts read-only `protocol.negotiate`, `status.get`,
  and `logs.query`, uses an explicit user SID allowlist plus caller-token
  identity, and returns observed Agent/Worker/MT5 projection plus fixed-message
  events from a 200-entry volatile buffer (100 records maximum per query).
  Logs accept no path and never read files. Central reports
  `NOT_CONFIGURED`; trading reports `UNSUPPORTED` and `NOT_AUTHORIZED`.
- Windows Service status and lifecycle requests use SCM for only the fixed
  `MT5Agent` name. SCM authorizes the current caller per requested access
  right. The app does not elevate or alter ACLs. Stop and Restart require
  confirmation. Operation results and post-operation state are shown in
  Dashboard; an unknown outcome requires state refresh before retry.
- With the Service stopped or allowlist missing, the UI remains available and
  presents offline/unavailable state. The UI does not call `/command` or open
  the internal Worker pipe. The tray can restore or explicitly exit the UI;
  closing/minimizing the window never controls the Agent or Worker. No trade or
  Service mutation through the Python Management pipe exists.
- User preferences (theme, bounded refresh interval, notifications and
  close-to-tray) are validated and atomically saved in LocalAppData. Startup
  registration is shown as unavailable; it is not changed by the client.
- Runtime shows the Worker session ID, protocol version and last successful
  MT5 operation only when present in authenticated status. Terminal paths,
  process IDs, and account details are excluded.
- Logs support optional 30-second auto-refresh with overlap prevention. The
  remote query remains capped at 100 events. Diagnostics copy an explicit
  allowlist of non-secret fields.
- Local Diagnostics show the UI/framework/OS and last verified Agent response.
  Support export and remote upload are not implemented.

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
- Phase 4 WPF/ViewModel/Management IPC tests: **40 passed, 0 failed** on the
  final Windows rebuild, including OS-label and expected-offline diagnostics
  regressions.
- Windows Python regression suite: **317 passed, 2 skipped**. The skips are
  dedicated Runtime Worker ACL experiment gates and are not counted as passes.
- Windows Management IPC contract/security suite: **23 passed, 0 skipped**.
- UI Automation drove Dashboard, Runtime, Settings, Logs, Diagnostics, About,
  and theme switching in the active Windows console session. WPF `PrintWindow`
  screenshots captured the rendered window. Minimize-to-tray retained the UI
  process; tray restore, close-to-tray retention, and context-menu Exit were
  exercised successfully in the active session. The capture image set is in
  [`docs/evidence/v0.1.4/phase4/`](../../docs/evidence/v0.1.4/phase4/).
- Isolated security spike proved actual Named Pipe caller SID extraction,
  DACL allow/deny, impersonation restoration/fail-closed behavior, forged SID
  claim rejection and LocalSystem Session 0 to interactive Session 1.
- Cross-language Python Session 0 → C# Session 1 smoke passed with a synthetic
  status fixture. It did not query production Agent/Worker/MT5 or broker state.
- GitLab [pipeline #45](http://gitlab.local/root/agent/-/pipelines/45) passed
  all 9 jobs on Phase 4 commit `438c80f7`: validation, Linux/Windows/Python and
  WPF Management tests, Windows build, three smoke jobs, and Windows package.
  This was the project CI pipeline; it does not close the other-OS, installed
  Service, performance, or release-signing gates.

## Remaining limitations

| Area | State | Evidence gap or boundary |
|---|---|---|
| Interactive visual/DPI/UI Automation review | Partial | Windows 10 x64 console Session 1 UIA verified navigation, theme change, minimize/restore, close-to-tray, and explicit Exit; screenshots exist. DPI/scaling variants and other supported OS remain open. |
| Supported OS matrix | Partially verified | Only Windows 10 Pro 22H2 build/test evidence; Windows 11 and Server 2022/2025 not run. |
| Production Agent Service identity/provisioning | Open | Spike used disposable LocalSystem service. SID list is configured manually; no reader group provisioning. |
| Multi-user/multi-session behavior | Partial | Session 0/1 communication tested; full multiple-user isolation matrix not run. |
| SCM start/stop/restart | Implemented; Windows verification pending | Fixed `MT5Agent` service name; caller-token SCM ACL checks, bounded result/read-back, confirmation for disruptive actions and per-user audit. No lifecycle test was run against a real Service in this cycle. |
| Runtime Worker restart | Not implemented | No Desktop-to-Worker mutation exists. |
| Logs, diagnostics, tray, notifications | Implemented, bounded | Logs expose only fixed-message Management events; no raw file access or support upload. Interactive tray lifecycle verified on the Windows 10 console host. |
| v0.1.5 package | Windows CI pending | Build job publishes `MT5Agent-Desktop-v0.1.5-windows-x64.zip`; verifier consumes the same artifact. |
| Performance, memory, CPU, soak | Not measured | Dispatcher responsiveness covered by unit harness, not commercial thresholds. |

No real trades were executed. The earlier Phase 1 build evidence used the
runner's installed runtime assemblies before the official Developer Pack was
installed; the Phase 2 build above supersedes it for clean targeting-pack
verification. See [Implementation Baseline](../../docs/architecture/IMPLEMENTATION_BASELINE.md)
and [IPC Contract](../../docs/architecture/IPC_CONTRACT.md).
