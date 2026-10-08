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
[Phase 4 implementation baseline](IMPLEMENTATION_BASELINE.md).

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
| A01 | UI runs independently from Agent Service | Windows test starts UI with Service running/stopped; UI process and service state evidence | Partial: interactive UI opened offline; live test-SCM Service responded to UI; after UI exit SCM Service remained RUNNING. UI was not kept open through the later stop action. No Worker existed. |
| A02 | UI crash does not terminate Agent or Worker | Fault-inject UI exit; assert Service/Worker PID and health remain | Partial: UI test process exited while temporary SCM Service remained RUNNING and Python Agent child remained. No Worker was provisioned, so Worker independence is not live-verified. |
| A03 | Agent remains operational when UI closes | Close/exit UI; poll Agent and Worker health independently | Partial: management Service stayed RUNNING after UI exit; a later Admin status probe returned AGENT_RUNNING. Worker/MT5 unavailable by test design. |
| A04 | Service-offline UI opens successfully | Stop Service; launch UI; inspect recovery guidance without crash/hang | Partial: WPF launched with no Service and showed explicit offline/unavailable state; stopping temporary service removed the pipe and authorized probe returned Win32 2. UI was not opened while that temporary Service stop was in progress. |
| A05 | Cached state is clearly labeled stale | Disconnect probe source; assert observation age/source and stale label | Partial: stale on >15-second source age or >2-minute future clock skew; offline last values are labeled stale. Windows CI and visual verification pending |
| A06 | Dashboard displays actual runtime information | Compare UI projection with live diagnostic/Worker evidence, including unavailable case | Partial: Windows CI queried the candidate Agent through the WPF client and observed live Worker/MT5 state; installed Service and interactive UI verification remain |
| A07 | Unauthorized privileged requests are rejected | Negative tests by user/session/principal/action; audit denial and no side effect | The temporary Session 0 harness DACL boundary is verified: the allowlisted Administrator completed read-only status/log calls; a verified Users-only SID outside the allowlist received Win32 `ERROR_ACCESS_DENIED (5)` from `CreateFile` before protocol dispatch. The NetworkService task launch error `0x80070005` remains a separate harness failure. Product Service identity provisioning and cross-session authorization remain open release gates. See Phase 5 closure evidence below. |
| A08 | Machine and user settings remain isolated | Cross-user access/write test, ACL inspection, service/UI identity test | Partial: theme preference is per-user LocalAppData; no machine writes; cross-user ACL test pending |
| A09 | Existing MT5 Runtime continues in its provisioned interactive session | Assert existing principal, nonzero session, Worker/terminal identity and safe-read health; no provisioning changes | Current v0.1.3 lab evidence exists; rerun compatibility check on prepared host |
| A10 | Existing prepared host cold-boot behavior is checked | Boot prepared host without RDP/console login; capture existing Service/Worker/MT5 timeline | Prior lab evidence exists; do not create accounts or change Autologon in v0.1.4 |
| A11 | RDP disconnect behavior is tested | Disconnect/reconnect RDP without logoff; assert profile-specific runtime state | Not executed; compatibility gap |
| A12 | Management work is bounded and MT5 work remains serialized | Assert one active Management pipe request, bounded frame/timeouts, and no overlapping MT5 operations | Partial: single pipe instance, 64 KiB frames, 2-second client/server limits and concurrent client tests; no app queue. Existing Python runtime serialization regression remains passing on Linux; Windows soak unverified |
| A13 | Unknown execution outcome is never blindly replayed | Use fake service/fake broker contract fixture to drop response after synthetic dispatch; assert `OUTCOME_UNKNOWN` and no retry without reconciliation | No live or test-account order operations; zero-trade simulation required |
| A14 | Diagnostics do not expose secrets | Seed synthetic canary secrets; inspect UI, logs, exports and error paths | Not executed; bundle absent |
| A15 | Support export is previewable and never sent without explicit consent | Preview exact files/manifest; cancel; assert zero network transmission; if remote upload is later added, separate explicit consent/audit test | Local export only in Option A; remote support deferred |
| A16 | Reproducible WPF build and minimal deployment package work on a prepared host | Build, hash and test the exact artifact; validate user-scope extraction on the required Phase 5 OS | Windows 10 WPF build and executable hash recorded. Pipeline #46 passed its existing `package:windows` Agent job, but no WPF package/extraction or same-WPF-artifact promotion was tested. Windows 11/Server rows are `DEFERRED — PRODUCT OWNER VALIDATION`, outside Phase 5 OS test scope. |
| A17 | Windows and desktop CI tests pass | Build/analysis/unit/contract tests on Windows build runner; UI Automation on interactive desktop runner; Python regressions unchanged | Phase 5 closure Pipeline [#48](http://gitlab.local/root/agent/-/pipelines/48) passed all 9 jobs on commit `bb7013f30c43ddf940212f9332341c0fb51ba55d`; GitLab reports 632 tests. Interactive Windows UI and the manual DACL probe have separate evidence; CI does not exercise the test-only DACL helper. |
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

**Phase 5 OS scope:** Windows 10 x64 only. Windows 11 x64, Server 2022 Desktop
Experience, and Server 2025 Desktop Experience are `DEFERRED — PRODUCT OWNER
VALIDATION`. They are not Phase 5 blockers and are not marked passed.

### Phase 5 current acceptance evidence

| Acceptance area | Windows 10 Phase 5 result | Evidence / limitation |
|---|---|---|
| Interactive WPF | **PASS for pages and close-to-tray; tray menu Exit remains UIA-limited.** App launched in console Session 1 without Agent; existing UIA run covered all implemented pages, themes, keyboard focus, resize and prior restore flow. A follow-up saved `CloseToTray=true`, closed the window and observed the process alive with no main window. | [`tray-close-to-tray-result.json`](../evidence/v0.1.4/phase5/windows10-19045/tray-close-to-tray-result.json) and [`tray-uia-tree.json`](../evidence/v0.1.4/phase5/windows10-19045/tray-uia-tree.json) show the process lifecycle and that Windows UIA exposes only an aggregate taskbar notification toolbar, not the app icon/menu. Exit was not invoked; this is isolated as an automation surface limitation, not recorded as a pass. User preference was restored after testing. |
| Offline behavior | **PASS.** UI starts with no Agent Service; Dashboard, Runtime, Logs and Diagnostics show unavailable/timeout without fabricating runtime data. | Offline screenshots and C# tests. |
| Build/regression | **PASS.** Official .NET Framework 4.8 targeting pack; MSBuild `4.8.9037.0`; clean x64 rebuild without `FrameworkPathOverride`; C# 41/41; Windows Python 318 passed/2 skipped; Linux 276/36. | Two ACL skips are not counted as passes; isolated Session 0 tests separately passed 2/2 with exact DACL rollback. |
| Visual/accessibility | **PARTIAL.** Both themes, 1280×800, WPF window 1180×760 and resized 1050×680; keyboard focus and named UIA controls verified. | 96 DPI only; 125/150/200%, contrast instrument, and screen reader untested. |
| SCM/Agent Service lifecycle | **PASS for the isolated integration harness; product Service remains unimplemented.** Temporary demand-start `MT5AgentPhase5Test` (.NET Framework `ServiceBase`) ran the real Python Agent Core as a Session 0 child, with the production Management Named Pipe and a deliberately disabled Runtime adapter. SCM start, running, stop, restart and pipe recovery were observed. The test Service and generated artifacts were rolled back. | Reproducible evidence and harness are linked below. This does not verify a productized Python Service installer or customer configuration. No Worker/MT5 process existed and none was started. |
| Management IPC security | **PASS for the temporary Session 0 SCM harness and tested allowlist.** Authorized Administrator SID `S-1-5-21-950479549-2068523145-3370569714-500` opened the Pipe and completed `status.get` and bounded `logs.query`. A temporary Users-only account SID `S-1-5-21-950479549-2068523145-3370569714-1011`, not in Administrators or the allowlist, failed `CreateFile` with Win32 error 5 at the Pipe DACL boundary. Observed DACL: `D:(A;;FA;;;SY)(A;;0x12019b;;;LA)`; its local Administrator alias maps to the allowlisted Administrator SID. Default-deny forged-claim regression remains covered by the test suite. | Full details in [`negative-dacl-test-raw.json`](../evidence/v0.1.4/phase5/windows10-19045/negative-dacl-test-raw.json). Temporary account/profile/SCM service/probe were removed. This does not verify the future product Service's deployed identity/ACL. Earlier NetworkService task failure `0x80070005` is not classified as a DACL result. No privileged operation or trade exists. |
| UI/Agent lifecycle | **PASS for tested cases.** WPF launched offline with Service stopped; WPF navigated against live read-only status while test Service was running; explicit UI process exit left SCM Service RUNNING. Service stop removed its Python child and pipe; restart restored authenticated status. | UI screenshot and SCM/process/pipe evidence below. No Worker was provisioned; Worker independence is verified by existing code/tests, not a live lifecycle run. |
| Worker lifecycle/security | **PASS for the Worker ACL fixture only.** Session 0 LocalSystem launched a controlled test Worker into interactive Session 1; designated-user identity and duplicate launch rejection passed; Window Station/Desktop DACL restored and hash-verified. | This is not an installed MT5 Runtime/Worker test; no trade. |
| RDP/multi-session/reboot | **PENDING.** Console Session 1 and Session 0 Service were exercised; no RDP user session was active. | Shared Runner was not disconnected, logged off, or rebooted. Release impact: RDP reconnect/logoff and boot recovery remain unverified; assess on an isolated interactive host before commercial deployment. |
| Performance | **PARTIAL.** Existing startup N=5 median 152.7ms/P95(max) 198.0ms; idle 20s CPU 0.155%, private bytes median 55.7MiB/max 58.4MiB; offline refresh N=10 median 2018.1ms/P95(max) 2099.4ms; navigation during refresh N=10 median 27.9ms/P95(max) 51.1ms. Against the test Service: read-only status IPC N=30 median 0.32ms/P95 32.89ms/max 33.15ms; bounded `logs.query` N=10, up to 10 events, median 0.30ms/P95 31.57ms. | Small test Service and process-level probe; no successful UI refresh latency percentile, reconnect timing, 5-minute CPU, 10-minute memory, 8-hour soak, or production load. |
| GitLab | **PASS.** Pipeline [#48](http://gitlab.local/root/agent/-/pipelines/48) passed all 9 jobs on `bb7013f30c43ddf940212f9332341c0fb51ba55d`; GitLab reports 632 tests. | This pipeline validates the closure source/evidence commit. Its Python/C# suites cover repository regressions; the isolated Windows DACL probe was separately compiled and executed manually and is not a CI job. |
| Trading | **PASS.** No real trade or order command executed. | Only safe status and controlled Worker ACL fixture. |

The temporary SCM harness and the new standard-user DACL test close the
Management Pipe allow/deny evidence for the exercised test configuration, but
do not supply a product Service installer or provisioned Worker. The earlier
NetworkService Scheduled Task error was a harness failure and is superseded by
the actual Users-only token/DACL test; RDP/session behavior and the product
Service identity remain open. The tray close-to-tray process lifecycle passed,
while UI Automation did not expose the tray context menu; this limitation is
explicitly assessed and is not reported as an Exit pass. The three deferred OS
tests do not prevent Phase 5 completion.
Commercial release remains a separate decision and is not automatically
authorized by this phase.

## Phase 6 package acceptance addendum

The Phase 6 release artifact is a user-scope ZIP containing the WPF application
only. It must not provision or replace the Python Agent/Worker. The mandatory
CI chain is one clean WPF build, tests against the compiled outputs, and a
package-verification job that consumes the same ZIP without rebuilding.

| ID | Phase 6 criterion | Evidence | Result |
|---|---|---|---|
| A21 | Versioned Desktop ZIP contains only approved WPF files, documentation, manifest and checksums | Pipeline #53 build job #438 and downstream verifier #446 | PASS for declared package contents; no separate secret-canary scanner run |
| A22 | SHA-256 and commit/pipeline/build-job provenance match the tested artifact | Build report/manifest; source commit `246b1f109e56c32ba7174d23a1bb5708805750e4`; pipeline 53; build job 438; ZIP SHA-256 `01db0addfc3e85993fcb429ec124d5ce14fd48dabd5271d52fc0f00f51e40cff` | PASS |
| A23 | Exact CI ZIP extracts and launches on Windows 10 without developer tooling/source checkout | Job #446 extracted and verified the build artifact, then kept the packaged EXE alive for a 3-second non-interactive smoke | PASS for extraction/process smoke; interactive UI remains PENDING |
| A24 | User settings survive side-by-side upgrade and rollback and live outside installation folder | Job #441 preference tests; no package replacement/rollback walkthrough | PARTIAL; automated persistence passes, package upgrade/rollback PENDING |
| A25 | Package removal leaves preferences, Agent/Worker, machine config and Service state unchanged | No interactive clean-host removal inventory; ZIP-only package by design | PENDING |
| A26 | Package integrity checks reject unsafe paths, duplicates, missing or undeclared files and changed hashes | Job #446 positive validation of the exact ZIP; no tampered-archive negative fixture in this pipeline | PARTIAL; positive integrity verified, adversarial negative fixture PENDING |
| A27 | No secrets, test credentials, private keys, PDBs, test binaries, Python Agent or Worker are packaged | Job #446 verified exact manifest-declared payload; builder allowlists Desktop runtime files and adds docs/manifest/checksums; no separate secret scanner | PARTIAL; package boundary verified, independent canary scan PENDING |
| A28 | Production Authenticode signing is verified before commercial publication | Authorized certificate validation | BLOCKED for commercial release; internal Phase 6 artifact remains unsigned |

Windows 11, Server 2022 Desktop Experience and Server 2025 Desktop Experience
remain `DEFERRED — PRODUCT OWNER VALIDATION`; they are not Phase 6 Codex test
requirements and are not a Phase 6 implementation blocker. A commercial release
still requires separate Product Owner authorization and closure of applicable
signing/lifecycle gates. See [Distribution](DISTRIBUTION.md) and the
[Release Checklist](RELEASE_CHECKLIST.md).
