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
Python regression on Linux was 255 passed and 34 skipped; see the implementation
evidence for runtime version and scope. All remaining quality gates remain
unverified unless separately evidenced.
