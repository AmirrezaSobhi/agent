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
| 12 | Windows Compatibility | Phase 5 validates Windows 10 x64 only. Windows 11/Server 2022/Server 2025 remain approved product targets but are `DEFERRED — PRODUCT OWNER VALIDATION`; they are not Phase 5 blockers and are not marked passed. Full release matrix remains a release gate. | Phase 5 Windows 10 evidence bundle; later PO evidence for each deferred row | Yes for commercial release; deferred OS rows excluded from Phase 5 completion |
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

**Phase 5 scope decision:** Windows 10 x64 is the sole Phase 5 OS execution
requirement. Windows 11 x64, Server 2022 Desktop Experience and Server 2025
Desktop Experience are `DEFERRED — PRODUCT OWNER VALIDATION`; this explicit
deferral does not block Phase 5. It does not establish commercial compatibility.

### Windows 10 measurements and gate results

| Gate | Metric / target | Test and evidence | Result | Remaining blocker |
|---|---|---|---|---|
| Visual design | Both themes; no clipped status text at tested layout; 100/150/200% target scales | UIA screenshots at 1280×800, WPF window 1180×760; [Dashboard, Settings, pages](../evidence/v0.1.4/phase5/windows10-19045/) | **PARTIAL.** Light/Dark rendered; a long Dashboard card value was made wrapping and regression-tested. | Only 96 DPI/100% tested; other scales pending; contrast not instrument-measured. |
| UX/offline | Clear cause and available next action in ≤2 interactions | Service absent/pipe timeout pages and UIA navigation | **PASS for offline display.** Agent/Worker data is explicitly unavailable; no state was fabricated. | Real Service recovery guidance remains unverified. |
| Startup | Main window visible ≤2.5s P95; target N=30 | Five interactive Windows 10 launches; measurement record | **PASS at measured sample.** N=5 median 152.7ms, P95(max) 198.0ms. | Below target sample count; this is not a 30-run release result. |
| Refresh / IPC | Healthy Agent response ≤2s P95; timeout bounded; UI responsive | Offline UIA run plus 30 status and 10 `logs.query` round trips against the temporary SCM Agent harness; raw JSON in `management-performance-probe.json` | **PASS for bounded test-harness IPC.** Status N=30 median 0.32ms/P95 32.89ms/max 33.15ms; `logs.query` N=10 (up to 10 events) median 0.30ms/P95 31.57ms. Offline timeout N=10 median 2018.1ms/P95(max) 2099.4ms; concurrent navigation median 27.9ms/P95(max) 51.1ms. | No packaged/product Service UI refresh percentile or production load. |
| Memory | ≤200 MiB after 10 min idle; ≤10% growth over 100 navigations | Private bytes sampled once/sec for 20 samples after 5s warmup | **PARTIAL.** Median 55.7 MiB, max 58.4 MiB. | 10-minute/100-navigation soak not run. |
| CPU | ≤2% average over 5 min idle | 20s interactive process CPU sample | **PARTIAL.** 0.155% of total reported processor capacity during sample. | 5-minute sample not run; temporary Agent harness does not change this short sample. |
| Stability | 8h soak and 100 Service reconnect cycles | UIA navigation/refresh; temporary SCM start/stop/restart; 30 status and 10 log IPC requests; Windows 10 tray close-to-tray lifecycle | **PARTIAL.** No crash in bounded UI/IPC runs; 30/30 status and 10/10 logs succeeded; one Service restart restored Pipe/status; closing the WPF window left the UI process alive in the tray. | No 8h soak/100 cycles, product Worker, or repeated dashboard recovery percentile. |
| Security | OS DACL default-deny; caller TokenUser SID; per-operation allowlist; no secret/path disclosure | Runtime SDDL query; allowlisted Admin open/status/log requests; Users-only unallowlisted account impersonation; forged-claim unit test; Worker ACL tests | **PASS for the isolated Management Pipe test harness.** Admin opened the Pipe and completed status/log calls. The actual test-account SID `S-1-5-21-950479549-2068523145-3370569714-1011`, confirmed member of Users and not Administrators, received Win32 `ERROR_ACCESS_DENIED (5)` from `CreateFile`; the denial occurred before protocol/application authorization. Runtime SDDL was `D:(A;;FA;;;SY)(A;;0x12019b;;;LA)`. The account/profile/service were removed. | Product Service SID/ACL provisioning, cross-session negative cases, and full secret-canary review remain separate release gates. The prior NetworkService task's `0x80070005` remains classified as a harness failure only. |
| Maintainability | Clean x64 rebuild, no project cycles, analyzer zero high findings | Official .NET Framework targeting pack, MSBuild rebuild, 41 C# tests | **PARTIAL.** Build and tests pass. | Static analyzer/coverage reports not collected. |
| Scalability | 10,000 log rows virtualized; first page ≤1s | Existing bounded filtering tests | **PENDING.** | No 10k-row UI run and no real log records. |
| Testability | Deterministic tests, no hidden skips counted as pass | Windows/Linux test logs and JUnit | **PASS for executed suite.** Closure Pipeline [#48](http://gitlab.local/root/agent/-/pipelines/48) passed all 9 jobs on `bb7013f30c43ddf940212f9332341c0fb51ba55d`; GitLab reports 632 tests. Earlier local evidence: C# 41/41; Python Windows 318/2 gated skips, with Worker ACL cases separately 2/2; Python Linux 276/36 platform skips. The low-privilege DACL probe was independently compiled and executed on Windows 10, outside CI. | Tray `Exit` UIA invocation, some lifecycle/DPI/accessibility cases remain isolated or pending; they are not counted as passed. |
| Compatibility | Windows 10 test; other product rows deferred | Build, UIA, 96 DPI and test evidence | **PARTIAL for Windows 10; other three DEFERRED — PRODUCT OWNER VALIDATION.** | RDP/multi-session, additional DPI and actual product Service deployment remain unverified. No other OS test is required in Phase 5. |
| Installation/update | Option A, already-provisioned Agent; package/build integrity | WPF executable hash recorded; no commercial package created | **PENDING.** | Minimal deployable package and same-artifact CI provenance remain for later release gate. |
| Accessibility | Keyboard reachable, visible focus, Automation names/roles | UIA keyboard Tab/focus and named navigation/buttons | **PARTIAL.** | Screen-reader and contrast-tool checks absent. |
| Observability/fault | Status source/age/reason; bounded error state; offline UI stable | Offline and live Service UIA screenshots; status/log IPC probes; SCM stop/restart and pipe disconnect/reconnect | **PASS for the tested test-harness flow.** Dashboard showed responsive Agent, disconnected Worker/MT5 and explicit runtime error; offline screen showed no stale status as current. | No real Worker/MT5; no reboot, RDP recovery, or product-Service recovery policy. |
| Tray close/Exit | Close-to-tray leaves UI alive with main window hidden; `Exit` menu closes UI | Windows 10 Session 1 UIA task; process/session observation; taskbar UIA tree; `TrayLifecyclePolicyBehavior` C# test | **PARTIAL.** Close-to-tray was exercised interactively: `CloseToTray=true`, WM_CLOSE left the process alive and main window hidden. The UIA provider did not expose the `MT5Agent Desktop` icon or its context menu; only an aggregate `User Promoted Notification Area` toolbar was discoverable. The source route from menu `Exit` to `ExitRequested` to `RequestExit` and the explicit-exit close policy is present and unit-tested. | Actual menu invocation and tray restore from this follow-up remain unverified due to the Windows 10 UIA surface; no application defect was observed. Use a manual pointer/keyboard run on an accessible desktop before commercial release. |
| Commercial readiness | All P0 gates, product deployment path and approved release evidence | This Phase 5 evidence set | **BLOCKED.** | Product Service installation/recovery, package/signing, same-artifact release promotion, RDP/multi-session, DPI/accessibility and Product Owner validation of deferred OS rows remain release gates. The isolated temporary-harness DACL negative is now PASS. |

Performance evidence is specific to `window10-test`, Windows 10 Pro build
19045.6466, interactive Session 1, 96 DPI, and the Phase 5 WPF binary. The
successful IPC sample used a temporary, demand-start .NET SCM harness hosting
the real Python Agent Core in Session 0 with Worker access disabled; it is not
a product Service. Sample sizes and limits are in the evidence files. No
successful WPF refresh percentile, full log-volume stress, multi-cycle
reconnect, RDP recovery, or long soak was measured.

The Windows 10 suite ran from the Phase 5 source bundle (SHA-256
`ee4417298240cfa8cb555b7f66cf774e76f66e9be3c040ac1d71e82f3d80778f`), based
on commit `9286e4f5640c979ccaf345b7fdf64a962d7e77bc` plus the documented Phase 5
working-tree changes. The clean x64 command used the official framework
reference assemblies and no `FrameworkPathOverride`. Raw tests, hashes, UIA
screenshots, and measurements are linked from the [evidence bundle](../evidence/v0.1.4/phase5/windows10-19045/).

The repository still has no productized Agent Service installer/adapter. The
approved temporary SCM integration harness has been removed after its tests;
its limited evidence is not commercial deployment evidence. RDP/logoff/reboot
were not run on the shared console host. No Windows 11 or Server test was
attempted. No real trade was executed. Pipeline [#46](http://gitlab.local/root/agent/-/pipelines/46)
passed all 9 jobs on commit `f841c55021af0535f39632b02d9efcd7e0ca37a0`; the
follow-up documentation commit receives a separate pipeline check.

## Phase 6 package-specific gates

The package gates below apply in addition to the quality targets above. Their
final values must cite the same CI artifact tested on Windows 10. A successful
build alone is not a clean-package pass.

| Gate | Metric / threshold | Test and evidence | Result |
|---|---|---|---|
| One-build artifact provenance | Exactly one WPF Release x64 rebuild per pipeline; C# tests and package verifier consume that output; packaged EXE SHA-256 equals build-output SHA-256 | GitLab `desktop:build-package`, `test:wpf-management`, and `desktop:package-verify`; CI report with commit/pipeline/build job IDs | PENDING final pipeline |
| Package integrity | Every declared payload file and manifest has a SHA-256; no duplicate, traversal, absolute or undeclared files; archive hash unchanged before/after validation | `Test-DesktopPackage.ps1` report; extracted manifest and checksum file | PENDING final pipeline |
| Clean Windows 10 deployment | Exact CI ZIP launches from a user-writable path without repository, Visual Studio, unpublished DLL or custom environment dependency; startup and shutdown controlled | Interactive Windows 10 run, screenshots, process/session evidence | PENDING exact CI ZIP |
| Settings/data safety | Preferences outside application folder survive replacement/rollback; no plaintext secrets; package removal leaves preferences and Agent state intact | Before/after file hashes/state inventory; settings tests; package content scan | PENDING Windows run |
| Upgrade recovery | New version extracted side-by-side; previous known-good folder remains available; interrupted replacement does not mutate the previous folder | Bounded file-operation simulation plus operator runbook review | PENDING Windows run |
| Runtime dependency | .NET Framework 4.8 or later installed; no developer targeting pack required on end-user host | Manifest/prerequisite review and Windows 10 launch | PENDING Windows run |
| Code signing | Authorized production Authenticode signature verifies for the distributed executable | Signer identity and `Get-AuthenticodeSignature` verification without exposing key material | BLOCKED: no authorized signer identified |
| OS coverage | Windows 10 x64 package evidence; other approved OS rows explicitly deferred | [Compatibility Matrix](WINDOWS_COMPATIBILITY.md) | Windows 10 PENDING; Windows 11/Server `DEFERRED — PRODUCT OWNER VALIDATION` |

Thresholds for startup, idle CPU/RAM and IPC remain those documented in the
Phase 5 measurement protocol; compare only equivalent WPF artifacts and test
conditions. Do not use a CI Session 0 startup smoke as interactive UI evidence.
