# MT5Agent Desktop — Phase 1 Foundation

**State:** Phase 1 implementation is present. Windows build and automated
ViewModel tests have run; release-quality toolchain, interactive visual review,
and supported-OS matrix verification remain incomplete.

## Implemented

- `MT5Agent.Desktop.sln` contains a .NET Framework 4.8 x64 WPF application and
  a dependency-free .NET Framework 4.8 test executable.
- MVVM base, bindable navigation, relay/async commands, explicit disposal,
  application composition, cancellation and sanitized error presentation.
- Dashboard, Runtime, Settings, Logs, Diagnostics and About pages. Accounts,
  Security, Updates and Support are visibly marked as previews/unavailable.
- Dark/light `ResourceDictionary` themes, shared styles/design tokens, English
  `.resx` strings, DPI manifest, keyboard focus and accessible control names.
- Theme preference stored per Windows user at
  `%LOCALAPPDATA%\MT5Agent\Desktop\preferences.v1`.
- `Services\Management\IManagementClient` is a testable boundary. Its Phase 1 implementation is a
  delayed unavailable stub. It does not read Windows Service state, call
  `/command`, open either Named Pipe, inspect MT5 or invent account/trading
  status. The UI starts without the Python Agent.

## Build and run on Windows x64

Prerequisites:

- Windows 10 x64, Windows 11 x64, or Windows Server 2022/2025 x64 with Desktop
  Experience. Server Core is unsupported.
- Visual Studio 2022 or Build Tools with the .NET desktop build components and
  .NET Framework 4.8 Developer/Targeting Pack installed.
- .NET Framework 4.8 or later runtime. The Python Agent/MT5 Worker is not a
  build or startup prerequisite.

From a Developer Command Prompt with MSBuild available:

```powershell
cd src\desktop
msbuild .\MT5Agent.Desktop.sln /t:Rebuild /m /p:Configuration=Release /p:Platform=x64
```

Launch `MT5Agent.Desktop\bin\Release\MT5Agent.Desktop.exe`.

Run the automated test executable after the solution build:

```powershell
.\MT5Agent.Desktop.Tests\bin\Release\MT5Agent.Desktop.Tests.exe
```

The test executable prints individual PASS/FAIL lines and exits nonzero when a
test fails. It uses only framework and project references; no test package
restore is required.

## Implementation status

| Feature | State | Notes |
|---|---|---|
| WPF startup/composition, MVVM and navigation | Implemented | Windows build, ViewModel tests and off-screen XAML layout of all routes pass; interactive appearance remains unreviewed. |
| Dark/light theme and per-user preference | Implemented | Runtime dictionary swap and file persistence tests pass. |
| English resource localization | Implemented | `.resx` lookup test passes; Persian/RTL is future work. |
| Dashboard availability/error presentation | Partially Implemented | Only honest unavailable/unobserved state; no Agent state is queried. |
| Clean net48 targeting-pack build | Partially Implemented | Compile passed via installed framework assemblies; official Developer Pack is absent. |
| Interactive visual/DPI/UI Automation review | Blocked | No interactive UI runner was available to this session. |
| Secure Management IPC and real Agent status | Planned | No network, `/command`, or Worker pipe access is present. |
| Tray, logs, diagnostics collection, support, service/runtime controls | Planned | Current pages are informational; no collection or privileged operation runs. |

## Current verification evidence

- Windows 10 Pro 22H2 x64, `windows-self-hosted-no-mt5` host: MSBuild
  `4.8.9037.0` rebuilt the x64 solution and the test executable reported **19
  passed, 0 failed**. The build used the installed .NET Framework runtime
  reference path (`FrameworkPathOverride`) because this runner lacks the .NET
  Framework 4.8 Developer/Targeting Pack. This is a successful compile against
  the runner's installed framework assemblies, but is not a substitute for a
  clean build against the official 4.8 reference assemblies.
- The host's inbox C# compiler supports through C# 5; the projects pin C# 5 so
  the foundation can build on the available compiler. A future CI toolchain
  should pin a supported Visual Studio Build Tools release and Developer Pack.
- The async responsiveness test ran a WPF Dispatcher timer while a synthetic
  350 ms status operation was pending; the Dispatcher tick occurred before the
  operation completed. This verifies the tested path did not synchronously
  block the Dispatcher; it is not a 100 ms P95 performance measurement.
- The test harness initialized the actual WPF `App.xaml`, constructed and laid
  out the MainWindow off-screen, and navigated/layout-checked all registered
  routes. This verifies resource resolution and basic visual-tree construction;
  it is not screenshot, interactive, DPI, or accessibility validation.
- Hashes of the tested outputs in the runner's temporary workspace: Desktop
  `e82faccd5545c2a5b2474c0f35d29587b30f73e35ed7e0acdde43bc300ceb5f3`; test
  executable `980d6da7f713b1bc44303fe61f6b5f88e666ef4f1b91854f323911675cee878c`.
- Python regression suite on Linux Python 3.14: **255 passed, 34 skipped**;
  `tests/test_windows_worker_launcher.py` was excluded, matching the existing
  Linux CI topology. No Python source or runtime configuration changed.
- No interactive visual, DPI, accessibility, tray, Windows UI Automation, or
  launch-in-a-real-user-desktop verification has been performed. The Windows
  SSH build session was Session 0; a dedicated interactive UI runner is still
  required for that evidence.

## Planned or blocked

| Capability | State | Boundary |
|---|---|---|
| Secure management IPC | Planned | No pipe/HTTP endpoint is connected. Never use existing `/command` or the Worker pipe. |
| Real Agent/Worker/MT5 status | Planned | Dashboard remains unavailable until Phase 2 contract and authenticated client exist. |
| Settings beyond theme | Planned | No machine configuration or credentials are read/written. |
| Logs/diagnostics/support export | Planned | Pages explain that no data was collected/read. |
| Tray, notifications, runtime/service controls | Planned | No privileged operation or lifecycle control exists. |
| Clean net48 Developer Pack build | Blocked by Runner prerequisite | Current Windows runner has inbox MSBuild but no .NET Framework 4.8 reference pack or Visual Studio Build Tools; do not install system-wide on this shared runner. |
| Visual verification and UI Automation | Blocked by infrastructure | Existing runner job is Session 0; use a dedicated interactive Windows desktop runner. |
| Server 2022/2025 and Windows 11 compatibility | Not verified | Build/test evidence currently covers only the Windows 10 runner. |

## Security boundary

The UI runs as the signed-in Windows user and requests no elevation. Theme
preferences are per-user only. There is no Service ACL change, Runtime
credential handling, Autologon setup, trading command, broker connection or
network API call in this project. `IManagementClient` is the sole intended
future data boundary; it currently returns explicitly unobserved/unavailable
state.
