# v0.1.4 Acceptance Checklist

**Status:** Measurable release checklist. Phase 4 implementation and one
Windows 10 desktop validation are evidenced, but no v0.1.4 release gate is
declared complete. Product
Owner-approved boundary is Option A: WPF Desktop Client and testable user-scope
package for an already installed/provisioned Agent/Runtime. No real trades are
permitted.

## Phase 1 evidence snapshot

Implemented: shell startup/composition, navigation, dark/light theme switching,
per-user theme persistence, English resources, cancellation/disposal patterns,
unavailable-only Dashboard, and 19 automated tests. A Windows 10 x64 MSBuild
compile completed using installed framework runtime assemblies; the runner
lacks the .NET Framework 4.8 Developer/Targeting Pack. The 19 tests passed on
that runner. Python regression was 255 passed / 34 skipped on Linux. See
[`src/desktop/README.md`](../../src/desktop/README.md) for command, runner and
toolchain details.

Phase 2 evidence: official net48 reference-pack build succeeded on the Windows
10 runner; 27 WPF/ViewModel/IPC tests and 15 Windows Python Management IPC
tests passed. An isolated Session 0/Session 1 SID/DACL security spike passed,
and a synthetic cross-language status smoke passed. This does not prove
interactive UI rendering or production Service provisioning. Windows 11/Server
2022/2025, UI Automation/DPI, packaging, tray, and a deployed Agent integration
remain unverified.

## Phase 3 implementation snapshot

The Phase 3 branch fixes Worker-availability reporting after successful
authenticated Worker health probes, keeps SCM state explicitly Unknown, adds
separate local Management Pipe connectivity and freshness-aware Dashboard
cards, and extends `test:wpf-management` with a Windows cross-process
Agent/ApplicationHost-to-WPF smoke using a deterministic Runtime adapter. The
actual `smoke:mt5-runtime` job also runs the compiled .NET client against the
candidate Agent and the configured live Worker/MT5 path; it receives only a
process-scoped allowlist for the CI caller. Both jobs are required before
package publication. Pipeline 43 on commit
`7b64af90c460fdf17a66594c0f63110858eba0a4` passed all jobs; the live client
observed `AGENT_RUNNING`, `WORKER_READY`, `MT5 CONNECTED`, and fresh status.
The single measured Management IPC round trip was 90 ms. The run used the
candidate Agent in Session 0, not the installed Service, and did not launch the
interactive WPF window. Screenshots, P95 performance, other supported Windows
versions, and installed Service lifecycle remain open.

## Phase 4 implementation and Windows desktop evidence — 2026-10-08

The Phase 4 branch clean-built the WPF application with the official .NET
Framework 4.8 targeting pack on Windows 10 Pro 22H2 x64 and ran 40/40 C# tests,
317 Python tests (2 Runtime Worker ACL experiment skips), and 23/23 Management
IPC/security tests. In active console Session 1, UIA navigated all implemented
screens, switched themes, minimized/restored through the tray, verified
close-to-tray retained the process, and exited through the tray menu. Window
screenshots are in [`../evidence/v0.1.4/phase4/`](../evidence/v0.1.4/phase4/).
Dashboard/Runtime/Logs/Diagnostics showed unavailable state when the Agent
Management Pipe was unavailable. These results verify one Windows 10 host;
they do not verify Windows 11/Server compatibility, scaling/accessibility,
installed Service lifecycle, cross-user/RDP behavior, performance gates, or
production package installation. GitLab [pipeline #45](http://gitlab.local/root/agent/-/pipelines/45)
passed all 9 jobs on commit `438c80f7`. Details are recorded in the
[Phase 4 implementation baseline](IMPLEMENTATION_BASELINE.md#phase-4-desktop-operations--2026-10-08).

## Scope and release gates

Mandatory foundation: C#/WPF/XAML/.NET Framework 4.8/MVVM shell, truthful local
status for one existing Runtime, Local Setup, per-user preferences, secure
dedicated management IPC, English/resource localization, independent UI
lifecycle, offline guidance, tray/close behavior, safe diagnostic/log view,
minimal local support export, and reproducible x64 user-scope package. The
client does not install/provision the Agent Service or Runtime. Full commercial
installer, account creation, Autologon, custom elevated helper, central backend,
production updater, full auto-update/rollback, multi-runtime and multi-Agent
failover are out of scope.

## Traceable checklist

“Not executed” means no evidence was collected for v0.1.4. Existing v0.1.3 CI
does not pass these criteria by implication.

| ID | Acceptance criterion | Verification evidence required | Initial status / gap (see Phase 4 snapshot above for newer evidence) |
|---|---|---|---|
| A01 | UI runs independently from Agent Service | Windows test starts UI with Service running/stopped; UI process and service state evidence | Partial: UI was launched without Agent/Management Pipe in interactive Windows Session 1; installed-Service running/stopped matrix remains unverified |
| A02 | UI crash does not terminate Agent or Worker | Fault-inject UI exit; assert Service/Worker PID and health remain | Not executed; UI harness absent |
| A03 | Agent remains operational when UI closes | Close/exit UI; poll Agent and Worker health independently | Not executed |
| A04 | Service-offline UI opens successfully | Stop Service; launch UI; inspect recovery guidance without crash/hang | Partial: offline Management Pipe UI opened and displayed unavailable state interactively; installed Service stop test remains pending |
| A05 | Cached state is clearly labeled stale | Disconnect probe source; assert observation age/source and stale label | Partial: stale on >15-second source age or >2-minute future clock skew; offline last values are labeled stale. Windows CI and visual verification pending |
| A06 | Dashboard displays actual runtime information | Compare UI projection with live diagnostic/Worker evidence, including unavailable case | Partial: Windows CI queried the candidate Agent through the WPF client and observed live Worker/MT5 state; installed Service and interactive UI verification remain |
| A07 | Unauthorized privileged requests are rejected | Negative tests by user/session/principal/action; audit denial and no side effect | Partial: real Windows DACL denied another SID; token SID extraction and allowlist verified. No privileged mutations exist; full multi-user matrix remains |
| A08 | Machine and user settings remain isolated | Cross-user access/write test, ACL inspection, service/UI identity test | Partial: theme preference is per-user LocalAppData; no machine writes; cross-user ACL test pending |
| A09 | Existing MT5 Runtime continues in its provisioned interactive session | Assert existing principal, nonzero session, Worker/terminal identity and safe-read health; no provisioning changes | Current v0.1.3 lab evidence exists; rerun compatibility check on prepared host |
| A10 | Existing prepared host cold-boot behavior is checked | Boot prepared host without RDP/console login; capture existing Service/Worker/MT5 timeline | Prior lab evidence exists; do not create accounts or change Autologon in v0.1.4 |
| A11 | RDP disconnect behavior is tested | Disconnect/reconnect RDP without logoff; assert profile-specific runtime state | Not executed; compatibility gap |
| A12 | Management work is bounded and MT5 work remains serialized | Assert one active Management pipe request, bounded frame/timeouts, and no overlapping MT5 operations | Partial: single pipe instance, 64 KiB frames, 2-second client/server limits and concurrent client tests; no app queue. Existing Python runtime serialization regression remains passing on Linux; Windows soak unverified |
| A13 | Unknown execution outcome is never blindly replayed | Use fake service/fake broker contract fixture to drop response after synthetic dispatch; assert `OUTCOME_UNKNOWN` and no retry without reconciliation | No live or test-account order operations; zero-trade simulation required |
| A14 | Diagnostics do not expose secrets | Seed synthetic canary secrets; inspect UI, logs, exports and error paths | Not executed; bundle absent |
| A15 | Support export is previewable and never sent without explicit consent | Preview exact files/manifest; cancel; assert zero network transmission; if remote upload is later added, separate explicit consent/audit test | Local export only in Option A; remote support deferred |
| A16 | WPF deployment package works on already prepared supported hosts | Extract/install user-scope package and launch on each approved OS; assert preexisting Service/config unchanged; verify package manifest/hash | No full install/upgrade/repair/uninstall acceptance; no Service provisioning |
| A17 | Windows and desktop CI tests pass | Build/analysis/unit/contract tests on Windows build runner; UI Automation on interactive desktop runner; Python regressions unchanged | Phase 4 Windows build and local C# 40/40, Windows Python 317 passed/2 skipped, IPC 23/23, and interactive UIA passed on Windows 10. Phase 4 GitLab pipeline unavailable; other OS jobs remain gaps |
| A18 | No real trades are executed | Confirm demo/test account and inspect command logs/test harness; no order operations | Mission constraint; no trades run |
| A19 | v0.1.3 behavior does not regress | Same-artifact regression suite plus Session 0/Worker/pipe and safe-read smoke | Linux Python suite 268 passed/36 skipped; Windows IPC tests passed. Existing production MT5 Runtime/Worker smoke was not rerun |
| A20 | Build Once → Test Same Artifact → Release Same Artifact is preserved | Build manifest and SHA-256 match the exact package consumed by tests and release | Existing Python pipeline remains unchanged; WPF build job emits test artifacts, but same-artifact deployment packaging/release is not implemented |

## Cross-cutting release evidence

Record exact commit and artifact SHA-256; OS build/architecture; user/session
identity without secrets; test timestamps and clock health; pipeline/job IDs;
test account/demo status; logs; failures/retries; and reviewer. Do not mark
acceptance passed from code inspection alone. If CI lacks UI, accessibility,
package or session tests, identify the infrastructure gap and name an approved
manual gate before release. Windows Server targets mean Desktop Experience;
Server Core is unsupported.

## Explicitly deferred

Full multi-runtime execution, central Web Console, production billing,
enterprise custom roles, Remote Support implementation, central offline
license issuance, complete auto-update/rollback and production multi-Agent
failover. No criterion in this list authorizes those features for v0.1.4.

## Phase 5 hardening status — 2026-10-08

Phase 5 has not passed its release gates. The two authorized Windows hosts are
Windows 10 Pro build 19045 x64; no Windows 11 or supported Windows Server test
host was found. No installed MT5Agent Agent Service was found on either host,
so Service startup/restart, pipe recovery, Worker independence and RDP/session
lifecycle scenarios were not executed. No Phase 5 interactive UI capture, DPI
or accessibility measurement, performance sample, or soak result exists.

The two Runtime Worker ACL experiment tests remain pending and must not be
counted among the previously reported two skips. Their fail-closed test requires
an explicit dedicated flag and local worker principal. No real trades were run.
The Linux authoring host could not run pytest (`No module named pytest`). See
[Phase 5 implementation baseline](IMPLEMENTATION_BASELINE.md#phase-5-verification-snapshot--2026-10-08),
[Quality Gates](QUALITY_GATES.md), and the [Windows compatibility matrix](WINDOWS_COMPATIBILITY.md)
for evidence and remaining blockers. Phase 4 pipeline #45 is historical and
was not run against Phase 5 documentation.
