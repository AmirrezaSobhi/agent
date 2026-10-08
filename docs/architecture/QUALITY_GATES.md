# WPF v0.1.4 Quality Targets and Release Gates

**Status:** Proposed measurable acceptance targets. Targets are not achieved
until evidence from the same release artifact is reviewed. Thresholds are
starting release criteria and may be tightened by the Product Owner; they must
not be weakened silently.

Test reference device for performance: Windows 10/11 x64 VM or physical host,
4 vCPU, 8 GiB RAM, SSD, 100% scale; repeat each timing 30 times after 3 warm-up
runs and report median/P95. UI tests use synthetic data and fake Agent service;
no live trading.

| # | Dimension | Metric / proposed threshold | Test method and evidence | Blocking |
|---:|---|---|---|---|
| 1 | Visual Design | 100% production views use approved token dictionaries; zero status conveyed by color alone; no clipped content at supported scaling | Screenshot review at light/dark, 100/150/200%, min/max window; token audit | Yes |
| 2 | UX | Service-offline state, cause and next safe action visible within 2 interactions; every unavailable module labeled | Five scripted customer scenarios; record steps, screen capture and user review | Yes |
| 3 | Responsiveness | Main window visible ≤2.5 s P95; click-to-feedback ≤100 ms P95; UI thread blocked >100 ms zero times in scripted flows | 30 cold/warm launches; WPF ETW/UI Automation timestamp trace | Yes |
| 4 | Runtime Performance | Dashboard refresh completion ≤2 s P95 on prepared Agent; no request interval faster than 5 s by default | Instrumented fake/real safe-read service; timestamps and trace | Yes |
| 5 | Memory Efficiency | ≤200 MiB private bytes after 10 min idle; growth ≤10% across 100 navigation cycles | Process counters + navigation soak, same host and build | Yes |
| 6 | CPU Efficiency | ≤2% average CPU over 5 min idle after warm-up; no polling busy loop | Process counters/PerfMon with Service disconnected and connected | Yes |
| 7 | Stability | 8 h soak with zero unhandled exceptions; 100 Service disconnect/reconnect cycles without UI crash or duplicate subscription | Interactive Windows soak logs, dump scan, lifecycle counters | Yes |
| 8 | Security | 100% unauthorized pipe operations denied; no `Everyone` DACL; zero synthetic secret canaries in logs/support output; no direct Worker-pipe UI connection | SID/ACL inspection, negative tests, canary scan, code review | Yes (P0) |
| 9 | Maintainability | No project reference cycles; no new UI framework dependency; zero high-severity analyzer findings; ViewModel/IPC critical-path branch coverage ≥80% | Build/analyzer report, graph check, coverage report | Yes for cycles/security findings; otherwise release gate |
| 10 | Scalability | 10,000 synthetic log rows remain virtualized; first page ≤1 s P95; retained UI memory increase ≤50 MiB | UI Automation data load, ETW and memory counters | Yes |
| 11 | Testability | All seven status dimensions, each error code and all permission-denial operations have deterministic automated tests; Windows integration contract suite passes | Test inventory mapped to contracts; JUnit/TRX reports | Yes |
| 12 | Windows Compatibility | Package launches on Windows 10 x64, 11 x64, Server 2022 x64 Desktop Experience, Server 2025 x64 Desktop Experience; no support claim for other Windows versions | Clean prepared VMs; capture OS build, .NET release key, launch/status/package evidence | Yes |
| 13 | Installation Experience | On a pre-provisioned supported host, documented user-scope package placement and first launch ≤5 min; Service state not changed by package install | Fresh prepared VM, timed operator walkthrough, before/after SCM snapshot | Yes |
| 14 | Update Reliability | No auto-update in v0.1.4; package manifest identifies version/commit and SHA-256; deployed file hash equals tested artifact | Extract package, verify manifest/hash and same-artifact pipeline provenance | Yes |
| 15 | Accessibility | 100% interactive controls keyboard reachable with visible focus and UI Automation name/role; text contrast ≥4.5:1 and non-text controls ≥3:1 | UIA tree audit, keyboard-only run, contrast measurements and screen-reader smoke | Yes |
| 16 | Observability | 100% displayed status carries source, observed UTC time, age and reason; every failed request has correlation ID and stable code | Contract/UI assertions and sanitized log inspection | Yes |
| 17 | Fault Recovery | Service stop, pipe break, Worker loss and MT5 disconnect do not freeze UI; stale rule triggers within 15 s; restart guidance distinguishes Service/Worker/UI | Fault injection of each condition, timestamped screenshots and request logs | Yes |
| 18 | Commercial Readiness | All P0 gates pass on the approved matrix; no claim of installer, central enrollment, live trading, billing or auto-update; Windows 10 risk disclosed | Signed release checklist and scope review | Yes |
| 19 | Localization | No user-facing literal outside resources except protocol/code; English resource coverage 100%; layout supports direction change without left/right hard-coding | Resource scan, pseudo-localization, long-string and RTL readiness layout test | Yes for English; RTL feature deferred |
| 20 | Privacy | Support export preview lists every file/field; cancel produces no transmission; export/log canary scan has zero secret matches | Synthetic canary fixtures, preview/cancel/upload-network assertion | Yes |

## Target OS and lifecycle evidence

`.NET Framework 4.8` is available on all four approved OS families; newer
Windows builds may have 4.8.1 as an in-place update, which is compatible with
applications targeting 4.8. Require .NET Framework 4.8 or later and verify
runtime release key in test evidence. Windows Server requires **Desktop
Experience**; Server Core has no standard desktop shell and is unsupported for
the WPF client.

Windows 10 remains Product Owner-approved in the matrix, but Microsoft ended
general support for Windows 10 22H2 on 2025-10-14. ESU is time-limited and
edition/program-specific; it does not turn the product matrix into an OS
support guarantee. Product support policy must state supported Windows 10
editions/builds and require current applicable security servicing/ESU. Review
the lifecycle at each release. Windows Server 2022 moves from mainstream to
extended support after 2026-10-14 and receives extended security support
through 2031-10-15. Windows Server 2025 is in mainstream support through
2029-11-14 and extended support through 2034-11-15. These lifecycle dates are separate
from WPF/.NET technical compatibility and must be rechecked at release time.

Sources checked 2026-10-08: [Microsoft .NET Framework system requirements](https://learn.microsoft.com/en-us/dotnet/framework/get-started/system-requirements), [Server Core vs Desktop Experience](https://learn.microsoft.com/en-us/windows-server/get-started/install-options-server-core-desktop-experience), [Windows 10 release information](https://learn.microsoft.com/en-us/windows/release-health/release-information), [Windows Server 2022 lifecycle](https://learn.microsoft.com/en-us/lifecycle/products/windows-server-2022), and [Windows Server 2025 lifecycle](https://learn.microsoft.com/en-us/lifecycle/products/windows-server-2025).

## Evidence ownership

Each gate records commit, artifact SHA-256, OS edition/build/architecture,
.NET release value, test identity/session (no secrets), run timestamps, test
tool version, raw report paths, failures/retries, and reviewer. A missing runner
or measurement is an unmet gate, not a pass. Release approval must review the
Windows 10 lifecycle risk separately from technical launch compatibility.

## Phase 1 measurements

The Windows no-MT5 Runner compiled the WPF solution and ran its custom test
executable: 19 passed, 0 failed. Its inbox MSBuild/compiler and installed
framework assemblies were used because the .NET Framework 4.8 Developer Pack
is absent; this is not clean-targeting-pack evidence. The Dispatcher test
confirmed a DispatcherTimer tick while the synthetic 350 ms operation remained
pending, but no P95 launch/click measurement was collected. No visual, DPI,
accessibility, memory, CPU, soak, package or Server/Windows 11 test has passed.
Python regression on Linux was 255 passed and 34 skipped. This is a historical
Phase 1 snapshot; see the Phase 2 evidence below. All remaining quality gates
remain unverified unless separately evidenced.

## Phase 2 verification — 2026-10-08

- Official .NET Framework 4.8 Developer Pack installed on the Windows 10 Pro
  22H2 x64 runner. MSBuild `4.8.9037.0` completed a clean Release x64
  `/t:Rebuild` using the official reference assemblies and no
  `FrameworkPathOverride`.
- C# WPF/ViewModel/Management IPC console tests: **27 passed, 0 failed**.
- Windows Python Management IPC contract tests: **15 passed, 0 failed**.
- Linux Python regression: **268 passed, 36 skipped**. The selected Windows
  integration test set ran separately on Windows. No skipped tests count as
  passed.
- Isolated Windows security spike proved Session 0/Session 1 Named Pipe
  identity and DACL allow/deny. A cross-language smoke used synthetic status;
  it did not connect to a provisioned Agent Service, MT5 terminal or broker.
- The new GitLab `test:wpf-management` job has not yet run in a GitLab pipeline.
  Only Windows 10 was available for this mission. No Windows 11/Server matrix,
  interactive screenshot/UI Automation, full Python regression on Windows,
  P95 launch measurement, memory/CPU measurement, package test or soak test was
  collected. These gates remain open.

## Phase 3 validation — Pipeline 43 succeeded

The Phase 3 branch extends `test:wpf-management` with a cross-process Windows
Named Pipe smoke. It starts the actual Python `Agent`, `ApplicationHost`, and
`CompositeHostingPort` lifecycle with a deterministic test Runtime adapter,
then queries it from the compiled .NET Framework WPF client. The existing
`smoke:mt5-runtime` job also receives that WPF client and queries a candidate
Agent connected to the configured live Worker/MT5 Runtime. Both are required
before the package gate. Pipeline 43 on commit
`7b64af90c460fdf17a66594c0f63110858eba0a4` passed all 9 jobs: validation 341,
Linux tests 342, Windows tests 343, WPF Management 344, build 345, invalid
configuration 346, control-plane 347, live MT5 runtime 348, and package 349.
The WPF job reported 29/29 C# tests and 16/16 Windows Management IPC tests;
Linux regression reported 270 passed / 36 skipped. The live MT5 job reported
Agent `AGENT_RUNNING`, Worker `WORKER_READY`, MT5 `CONNECTED`, and fresh
Management status via the compiled .NET client in Session 0. IPC round trip
was 90 ms for one sample only; this is not an average or P95.

These results do not prove the installed Service lifecycle or interactive UI.
No idle CPU, memory, visual, DPI, accessibility, P95, or long-duration reconnect
measurement is claimed until collected on an interactive Windows host. No
Windows 11 or Server 2022/2025 run was included.

## Phase 4 Windows validation — 2026-10-08

- On the Windows 10 Pro 22H2 x64 host, MSBuild `4.8.9037.0` completed
  `MSBuild.exe MT5Agent.Desktop.sln /t:Rebuild /p:Configuration=Release
  /p:Platform=x64 /m:1 /nologo /verbosity:minimal` using the official .NET
  Framework 4.8 targeting assemblies, without `FrameworkPathOverride`.
- The Phase 4 C# test executable passed **40/40** tests (recorded after the
  final rebuild). Windows Python suite passed **317**, skipped **2** dedicated
  Runtime Worker ACL experiment gates, and failed **0**. Windows Management
  IPC/security tests passed **23/23**, no skips.
- In active Windows console Session 1, UI Automation navigated Dashboard,
  Runtime, Settings, Logs, Diagnostics and About; switched themes; minimized
  and restored from the notification area; exercised close-to-tray; and used
  the tray context-menu Exit. The process remained alive after minimize and
  close-to-tray, then exited through Exit. Screenshots are stored under
  `docs/evidence/v0.1.4/phase4/` and linked from the implementation baseline.
- GitLab pipeline [#45](http://gitlab.local/root/agent/-/pipelines/45) passed
  all 9 jobs against commit `438c80f7`; all phase jobs remained unchanged.
  CPU/RAM, responsiveness percentiles, high-DPI scaling, accessibility, soak,
  multi-session/RDP, installed Service lifecycle, other supported OS versions
  and production packaging remain unmeasured/unverified.
- No trading command or order operation was called.

## Phase 5 measurement and evidence status — 2026-10-08

The thresholds above remain the release targets. Phase 5 did not collect new
interactive application measurements. Startup time, idle CPU, private bytes,
refresh/IPC latency distributions, log-view performance, reconnection time,
navigation soak, high-DPI layout, UI Automation/accessibility, or stability
soak are **not measured**. The Phase 4 one-sample IPC time must not be reported
as a Phase 5 percentile.

The current authorized host inventory contains Windows 10 Pro build 19045 x64
runners only. No Windows 11, Windows Server 2022 Desktop Experience, or Windows
Server 2025 Desktop Experience compatibility result exists. No installed
MT5Agent Windows Service was found; accordingly Service lifecycle gates remain
blocked on a prepared host. The Phase 4 Session 1 screenshots are historical,
not Phase 5 verification. See the [Windows compatibility matrix](WINDOWS_COMPATIBILITY.md)
and the [Phase 5 baseline snapshot](IMPLEMENTATION_BASELINE.md#phase-5-verification-snapshot-2026-10-08).

No new test suite executed from the Linux authoring host because its system
Python has no `pytest` module. Do not install dependencies into the host to
mask this limitation; run regression through the repository's Windows/Linux
GitLab jobs and retain exact commit/job reports. Existing `test:windows` ACL
cases remain skipped unless the dedicated environment gate and principal are
provided; skipped cases are unresolved, not passed.
