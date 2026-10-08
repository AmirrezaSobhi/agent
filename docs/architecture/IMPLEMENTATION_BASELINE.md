# Implementation Baseline

**Audit date:** 2026-10-08. **Audited commit:** `d99182211696ef877171fda287dee01ef6e3fce7` (`origin/develop`).
This is a source and tracked-evidence audit; claims do not imply commercial
readiness. The detailed historical snapshot remains at
[Phase 0 evidence](../evidence/v0.1.4/phase0-baseline-and-architecture.md).

## Repository and branch baseline

| Ref | SHA observed | Meaning |
|---|---|---|
| `origin/develop` | `d99182211696ef877171fda287dee01ef6e3fce7` | Blueprint starting baseline; contains Phase 0 record. |
| `origin/staging` | `e34d6d783e42c5d2fb5f1448af5f5e01d01cf095` | Promotion branch, separate from current develop head. |
| `origin/main` | `dbca8ca7fe65ca14a95a106d215cc9fa439ac01f` | Released baseline. |
| tag `v0.1.3` | `970c04712853295fd065094b11a2bd541b5a9db8` | Released v0.1.3 source. |

Remote: GitLab `origin`, `ssh://git@gitlab.local:2222/root/agent.git`.
The fetched local tracking ref was used; the contents of this table are a
point-in-time audit and may change after this draft.

## Implemented and evidenced

| Capability | Evidence in repository | Boundary / limitation |
|---|---|---|
| CLI startup, version and inspection diagnostics | `agent/main.py`: `run`; `agent/application/diagnostics.py`: `diagnose`; tests `tests/test_diagnostics_logging.py`, `tests/test_hosting.py` | CLI/process, not a desktop app or Windows Service installer. Diagnose is inspection-only and explicitly does not prove broker authorization or HTTP availability. |
| Composition and Agent lifecycle | `agent/composition.py`: `compose_agent`, `_default_mt5_adapter`; `agent/core/agent.py`: `Agent.start/stop`; `agent/application/host.py`: `ApplicationHost` | Windows selects `RuntimeWorkerMT5Adapter`, reading `HKLM\SOFTWARE\MT5Agent\Runtime`; missing runtime config degrades instead of terminating Agent. |
| Interactive MT5 Worker boundary | `agent/infrastructure/interactive_mt5_worker.py`; `agent/adapters/runtime_worker_mt5_adapter.py`; tests `tests/test_interactive_mt5_worker.py`, `tests/test_runtime_worker_adapter.py` | Worker owns MT5 API on interactive Windows session; supported operations are allowlisted safe reads/health. No production order execution is enabled. |
| Windows Named Pipe | `agent/infrastructure/windows_named_pipe.py`: `PIPE_NAME`, `MAX_MESSAGE_BYTES`, pipe server; tests `tests/test_windows_named_pipe.py`, `tests/test_windows_named_pipe_errors.py` | `\\.\pipe\MT5Agent.Runtime.v1`, 65,536-byte message bound, local/peer ACL and protocol protections. This is Agent-to-Worker IPC, not a UI management API. |
| HTTP command transport | `agent/adapters/http_transport.py`: `HTTPTransportAdapter`, `PATH`; `agent/infrastructure/http_server_host.py`; tests `tests/test_http_transport.py`, `tests/test_secure_transport.py` | `/command`, loopback default from `agent/infrastructure/environment_config.py`; `ThreadingHTTPServer`. `ApplicationBoundary` defaults to `AllowAllAuthenticator` and `AllowAllAuthorizer` in `agent/application/boundary.py`; do not use for privileged UI commands. |
| Configuration | `agent/contracts/configuration.py`; `agent/infrastructure/environment_config.py`; Windows registry lookup in `agent/composition.py`; tests `tests/test_configuration_composition.py` | Environment-backed HTTP/logging values and machine registry runtime values. No complete machine/user/central policy store or production credential store. |
| Structured command, identity, capability and contracts | `agent/contracts/`; `agent/application/dispatcher.py`; tests `tests/test_identity.py`, `tests/test_protocol_registry.py`, `tests/test_capability_discovery.py` | Foundations do not establish tenant enrollment, account registry, centralized policy, or execution lease. |
| Runtime serialization | Worker runtime locking and adapter locking; tests `tests/test_runtime_worker.py`, `tests/test_runtime_worker_adapter.py` | Serialized MT5 operations are current safety posture. HTTP handlers themselves are concurrent. `BoundedScheduler` (`agent/application/scheduler.py`) is not composed into production request handling. |
| Logging and diagnostics | `agent/infrastructure/logging_observability.py`; `agent/application/diagnostics.py`; tests `tests/test_diagnostics_logging.py`, `tests/test_operational_observability.py` | Sanitized fixed operational evidence; no full UI viewer, bundle preview/consent, or established bounded retention/rotation product policy. |
| Build and release automation | `.gitlab-ci.yml`, `deployment/ci.ps1`, `tools/release_sync/`; tests `tests/test_ci_topology.py`, `tests/test_ci_evidence.py`, `tests/test_gitlab_release_publish.py`, `tests/test_github_release_sync.py` | Current CI has Linux, Windows-no-MT5, Windows-MT5 validation lanes and packages Windows executable. It has no Desktop UI automation job. Preserve same-artifact promotion. |
| Runtime startup lab | `docs/MT5_RUNTIME_PROVISIONING.md`, `docs/ADR/ADR-001-unattended-mt5-runtime-hosting.md`, `docs/evidence/v0.1.3/phase4d-live-ci-acceptance.md` | Session 0 Agent and nonzero interactive Worker cold-boot lab path accepted. Autologon and `AtLogOn` are lab provisioning, not customer installer approval. |

## Partial, documented, or absent

| Area | Finding |
|---|---|
| Desktop shell/tray | No Desktop UI or tray package/dependency is present. Product Owner has since approved C#/WPF/XAML/.NET Framework 4.8/MVVM; the prior Kivy planning record is superseded history, not the active direction. |
| Productized Windows Service | Current control process can run Session 0; no customer-ready service installer, service recovery, or general setup flow is evidenced. |
| UI local API | No dedicated API. Existing `/command` uses allow-all composition defaults and is not a privileged UI contract. |
| Account and tenant model | No productized multi-tenant Agent/Device/Account/Runtime registry or account switching workflow. Existing runtime identity metadata is not a customer account-management service. |
| Trading | No production order submission, modification, close-position command, or independent trading strategy engine is enabled. |
| Central platform / AI / billing | No production control plane, AI brain, wallet, usage ledger, or central web console. |
| Secure config ownership | No complete split machine/user/central configuration ownership, schema migration, or credential lifecycle. |
| Recovery | Worker lifecycle/retry foundations exist; customer-profile recovery semantics for cold boot, logoff, RDP disconnect, service stop, and failure classes remain incomplete. |
| UI tests | Windows runner evidence exists for current runtime, but no UI automation, rendering, accessibility, tray, or interactive setup test harness was verified. |
| WPF toolchain and package | No C# solution, net48 WPF project, Visual Studio/MSBuild job, desktop artifact, or deployment package exists at this baseline. These are planned additions; current Windows runners are Windows 10 and do not establish Server 2022/2025 coverage. |
| Updater/support | Existing update-policy foundation and release pipeline are not a complete customer auto-updater with rollback. No reviewed support bundle or remote support product is present. |

## CI and release evidence

The tracked Phase 0 report records pipelines at the time of its snapshot,
including successful eight-job post-merge develop Pipeline #35; the current
branch audit summary reports later develop Pipeline #37 as successful. These
are evidence of those commits/jobs only, not a claim that this documentation
branch ran CI. `.gitlab-ci.yml` stages currently include validate, test, build,
smoke, package, release publish, and release sync. Build artifact flows through
MT5 runtime smoke and packaging by `needs`; release evidence emphasizes
Build Once → Test Same Artifact → Release Same Artifact. UI-specific criteria
are infrastructure gaps until a Windows UI runner/harness is established.

The Phase 0 report records release automation conditions that need recheck
before a future release: configured GitLab API endpoint uses HTTP while the
publisher requires HTTPS; protected release-owner variable was absent at that
audit; effective job-token write permissions and full automatic publication
path were not proven. These are not altered by this blueprint.

## Binding v0.1.4 update to the baseline

The code baseline above remains Python. WPF is a new management client and
must not replace/rewrite `agent/main.py`, `agent/composition.py`, the Python
Agent, or the interactive Worker. The approved commercial UI matrix is Windows
10/11 x64 and Server 2022/2025 x64 Desktop Experience only. Option A packages
the WPF UI for an already provisioned Agent; it does not claim or implement a
commercial installer or Windows Service provisioning.

## Phase 1 implementation update — 2026-10-08

The point-in-time audit above describes its audited commit and remains intact.
On the implementation branch from architecture commit
`648662473370abc34c4aa5f90cb52b30ecaf924c`, a new two-project solution now
exists under `src/desktop/`. It implements the WPF shell, MVVM primitives,
navigation, light/dark resources, per-user theme preference, English
localization, unavailable-only status presentation and a console test runner.
It does not connect to Python or execute Agent/Worker operations.

The Windows 10 no-MT5 Runner rebuilt the Release solution and reported 19/19
automated tests passing. This was a direct MSBuild invocation using the
installed framework runtime assemblies because that Runner has no .NET
Framework 4.8 Developer/Targeting Pack. The compile succeeded, but clean
reference-pack build evidence is still required. No interactive UI display
verification was done: the SSH process was in Session 0. On Linux, the Python
regression suite reported 255 passed and 34 skipped; existing Python files
were not modified. Detailed commands and caveats are in
[`src/desktop/README.md`](../../src/desktop/README.md).

`.gitlab-ci.yml` remains unchanged. Existing Windows runner tags have no WPF
build/test job; they lack the Developer Pack/Visual Studio Build Tools and an
interactive UI Automation lane. CI integration is therefore pending runner
prerequisites and a separate validated pipeline change.

## Phase 2 Management IPC and Windows build evidence — 2026-10-08

**Status: Implemented (read-only v1), with production provisioning and OS
matrix gaps.** The Python Agent now exposes `MT5Agent.Management.v1` through
`agent/infrastructure/management_named_pipe.py`, composed into the normal Agent
host by `agent/infrastructure/composite_host.py` and `agent/composition.py`.
`protocol.negotiate` and `status.get` are the only accepted operations. The
existing `/command` composition and `MT5Agent.Runtime.v1` Worker path were not
changed. The listener is disabled when
`MT5_AGENT_MANAGEMENT_ALLOWED_SIDS` is empty. Configure a comma-separated list
of exact Windows user SIDs in the Agent Service environment to enable read-only
status; no local reader group provisioning is implemented.

`ManagementNamedPipeServer._caller_sid` calls
`ImpersonateNamedPipeClient`, opens the thread token, reads `TokenUser`, closes
the token, and always attempts `RevertToSelf`; identity/revert failures fail
closed. The pipe DACL includes the Agent process identity and only the
configured user SID values. JSON SID/PID/name/session are not treated as
authentication evidence. Authorization is an explicit SID allowlist plus an
operation allowlist; no privileged or trading operation exists. Audit records
contain a correlation ID, operation and status code; caller SID is redacted.

An isolated Windows security spike ran a disposable LocalSystem service
(`S-1-5-18`) in Session 0 and clients in Session 1 and Session 0. It observed
the real interactive Administrator caller `TokenUser` SID (redacted as
`S-1-5-21-REDACTED-500`, Session 1), denied the different LocalService caller
(`S-1-5-19`, Session 0) at pipe open, verified impersonation
restoration after a callback exception and fail-closed behavior on injected
identity failure, and ignored a forged JSON SID. The spike uses
`tools/windows_security_spike/`; it is not a production Service account
qualification or a complete multi-user matrix.

Cross-language smoke connected the Python mock server in Session 0 to the C#
client in interactive Session 1 and reported
`IPC_SMOKE_PASS session=1 protocol=1 agent=AGENT_RUNNING worker=READY
mt5_connected=true`. The fields came from an explicitly synthetic fixture; no
Agent runtime, terminal, account, broker or trade was accessed. The actual
WPF Dashboard now polls via `NamedPipeManagementClient` and shows unavailable
until an authenticated status response arrives. Service-start controls and
all write operations remain absent.

### Official .NET Framework 4.8 build

The Windows 10 Pro 22H2 x64 build runner initially lacked the .NET Framework
4.8 Developer/Targeting Pack. The official Microsoft Developer Pack installer
was downloaded from the [official Microsoft .NET Framework 4.8 download
page](https://dotnet.microsoft.com/en-us/download/dotnet-framework/net48); its
Authenticode signature was valid and signer was Microsoft Corporation. Silent
install completed with exit code 0 and no restart. Reference assemblies are
present under `C:\Program Files (x86)\Reference Assemblies\Microsoft\Framework\.NETFramework\v4.8`.
The installer SHA-256 was
`B37882CDA5610B291B2A984E4C2270F67A448F79D6B1F78337736C95B35C5A7F`.

MSBuild version `4.8.9037.0` performed a clean x64 Release rebuild without
`FrameworkPathOverride`:

```powershell
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\MSBuild.exe .\src\desktop\MT5Agent.Desktop.sln /t:Rebuild /p:Configuration=Release /p:Platform=x64 /m:1 /nologo /verbosity:minimal
```

Result: build succeeded; WPF/ViewModel/IPC console suite **27 passed, 0
failed**. Windows Python Management IPC tests **15 passed**. Linux Python
regression suite: **268 passed, 36 skipped** (`--ignore=tests/test_windows_worker_launcher.py`);
the skips include platform/optional-capability cases and were not counted as
passes. Windows cross-language smoke used a synthetic status provider. These
results do not establish UI rendering, Windows 11, Windows Server 2022/2025,
interactive UI automation, full Windows Python regression, or production Agent
Service deployment. No real trades were executed.

`.gitlab-ci.yml` has a separate `test:wpf-management` job that requires the
official reference pack and runs WPF tests, Management IPC Python tests, and a
cross-process Windows Named Pipe smoke. This CI job evidence validates the real
Agent/ApplicationHost lifecycle with a deterministic Runtime test adapter; it
is not a deployed Service, live Worker/MT5, or interactive desktop test.

## Phase 3 Live Dashboard and runtime integration — 2026-10-08

**Status: Implemented and CI-validated on Windows 10 x64; installed Service and
interactive UI validation remain open.** Pipeline 43 passed on commit
`7b64af90c460fdf17a66594c0f63110858eba0a4` ([pipeline](http://gitlab.local/root/agent/-/pipelines/43)).
The WPF job built against the .NET Framework 4.8 reference assemblies and ran
29/29 C# tests plus 16/16 Windows Management IPC tests. The Linux regression
suite passed 270 tests with 36 skipped. GitLab CI Lint was valid with no
warnings.
The Management Pipe remains in the normal Agent hosting lifecycle and shares
its shutdown path. The Runtime Worker adapter now marks Worker availability
only after a validated Worker health response and clears it when IPC fails.
Service state is `UNKNOWN` because the Agent currently has no SCM query; a
successful pipe response proves Agent responsiveness and local IPC connectivity
only. The status projection does not infer trading authorization.

The Dashboard displays Windows Service, Agent, Runtime Worker, MT5, local
Management IPC, central-management, and trading-capability states. It polls
every five seconds while visible, prevents overlapping refreshes, cancels
pending work when leaving the view, reports unavailable/error states, and
labels source observations older than 15 seconds or more than two minutes in
the future as stale. A pipe failure is shown as offline while prior runtime
values are marked stale. Each status response carries UTC observation time,
source identity, freshness, error code, and the request correlation ID.

The Phase 3 `test:wpf-management` fixture runs the actual Agent and
ApplicationHost/CompositeHostingPort lifecycle with a deterministic test
Runtime adapter, then connects the .NET Framework client through a Windows
Named Pipe. The existing `smoke:mt5-runtime` job now also receives the compiled
WPF client test artifact, starts the candidate Agent with a process-scoped
allowlist containing only the current CI caller SID, and queries live Worker
and MT5 status through the Management Pipe. That job uses only the existing
safe-read integration checks; it does not execute trading operations or alter
host identity/configuration. Pipeline 43 recorded `AGENT_RUNNING`,
`WORKER_READY`, `MT5 CONNECTED`, fresh source status, and a 90 ms single
Management IPC round trip from the Session 0 C# client. This is one sample, not
a P95 latency measurement. The candidate Agent executable was started by CI;
this does not prove the installed Windows Service lifecycle or interactive WPF
rendering. Those and Windows 11/Server 2022/2025 compatibility remain explicit
validation gates.

## Assumptions requiring validation

1. v0.1.3 split-session Runtime Worker behavior remains compatible with a
   productized Windows Service; packaging and supported Windows matrix need
   explicit validation.
2. RDP disconnect, lock, logoff, Windows restart, and account credential
   rotation must be tested with each startup profile; cold-boot lab success
   alone does not establish all recovery semantics.
3. The current Worker/account observations must not be conflated with a durable
   customer Trading Account registry.
4. At least one reliable Windows UI automation/rendering host or repeatable
   manual acceptance procedure is needed for v0.1.4.
5. Clock synchronization condition, release transport TLS, release-owner
   approval and publisher write access must be rechecked at release time.

## Phase 4 Desktop Operations — 2026-10-08

**Implementation state: implemented and committed in the Phase 4 branch;
Windows build, automated regression, interactive Windows 10 desktop session,
and GitLab pipeline verified. Broader compatibility and commercial release
gates remain open.** The
branch starts from Phase 3 commit `01d94d11958dbc74e40252c671dfe61b75a9125a`.

- Clean Windows x64 Release rebuild succeeded with MSBuild `4.8.9037.0`, the
  official .NET Framework 4.8 targeting assemblies, and no
  `FrameworkPathOverride`.
- C# WPF/ViewModel/Management suite: **40 passed, 0 failed** on the Windows
  runner. Full Windows Python regression: **317 passed, 2 skipped, 0 failed**;
  skips are dedicated Runtime Worker ACL experiment gates. Management IPC
  contract/security suite: **23 passed, 0 skipped**.
- Active Windows console Session 1 validation launched the WPF application
  without requiring the Agent. UI Automation navigated Dashboard, Runtime,
  Settings, Logs, Diagnostics and About and switched from dark to light theme.
  The test exercised minimize-to-tray, tray restore, close-to-tray retention,
  and explicit tray Exit; the UI process survived minimize/close-to-tray and
  exited via Exit. Screenshots are captured in
  [`../evidence/v0.1.4/phase4/`](../evidence/v0.1.4/phase4/). These are one
  Windows 10 Pro 22H2 desktop's results, not four-OS/DPI/accessibility coverage.
- Diagnostics reads the Windows product/build labels from the local Current
  Version registry key because an unmanifested .NET Framework executable can
  receive a compatibility-shimmed `Environment.OSVersion` value. No credentials
  or machine paths are collected. Recognized pipe offline/timeout outcomes
  remain local connection states rather than generic global error banners.
- `logs.query` returns a bounded count of fixed-message in-memory Management
  events only. It does not expose file paths, file contents, credentials,
  arbitrary commands, Service controls, Worker-pipe access, or trading.
- GitLab pipeline [#45](http://gitlab.local/root/agent/-/pipelines/45) passed
  all 9 jobs on commit `438c80f7`. The pipeline was started through the GitLab
  web form because push pipelines are restricted by the existing workflow.
  `.gitlab-ci.yml`, release publication behavior and tags were not changed.
- CPU/RAM and percentile responsiveness, high-DPI, accessibility, multi-user
  and RDP behavior, installed Service lifecycle, Windows 11/Server
  2022/2025, and production-like package validation are still pending.
  No real trade was executed.

## Evidence rules

Evidence paths above are repository-relative and symbols/tests are named where
available. A file or test existing does not itself prove production wiring;
pipeline passes only prove the tested commit and runner scenario. The complete
acceptance checklist is [v0.1.4 acceptance](ACCEPTANCE_V0.1.4.md).

## Phase 5 verification snapshot — 2026-10-08

**Status:** Windows 10 source/build/tests, interactive UI, a reversible SCM
integration harness, and an actual low-privilege Management Pipe DACL denial
were executed. Tray close-to-tray is verified; UI Automation cannot expose the
tray context menu on this host, so the Exit menu item remains uninvoked. Product
Service packaging, shared-host RDP/DPI cases, and commercial release gates remain
open. This is not release readiness.

The branch baseline was `9286e4f5640c979ccaf345b7fdf64a962d7e77bc` on
`feat/v0.1.4-phase5-hardening`. The tested source bundle includes that commit
plus the Phase 5 working-tree changes and has SHA-256
`ee4417298240cfa8cb555b7f66cf774e76f66e9be3c040ac1d71e82f3d80778f`.

| Area | Actual result | Evidence / limitation |
|---|---|---|
| Windows environment | Windows 10 Pro x64 22H2, build 19045.6466, host `WINDOW10-TEST`; .NET Framework 4.8.09037/release 533325; official v4.8 targeting assemblies; MSBuild 4.8.9037.0 | [`WINDOWS_COMPATIBILITY.md`](WINDOWS_COMPATIBILITY.md); full details in [`phase5/windows10-19045`](../evidence/v0.1.4/phase5/windows10-19045/). |
| WPF build | Clean x64 Release `/t:Rebuild` succeeded without `FrameworkPathOverride`; app SHA-256 `3471c491722cc1b947f05e0caaff732764851e830c5f9de721c840a32a00a714`; C# test executable SHA-256 `aec6ac6b5db2aed8608b037e61d863e30a4dc468e67bf253e699afac78b6c050` | Build command/transcript and test count in evidence bundle. |
| C# tests | **41 passed, 0 failed**, including regression asserting Dashboard status card text wraps. | Build transcript and `MT5Agent.Desktop.Tests.exe` output. |
| Python Windows | **318 passed, 2 skipped**, 0 failed. Two skips were the dedicated fail-closed Worker ACL experiments. | `windows-python.log` and JUnit. Both skips were separately executed and passed 2/2. |
| Python Linux | **276 passed, 36 skipped**, 0 failed (`tests/test_windows_worker_launcher.py` excluded on Linux). | Executed with isolated target dependencies; system Python was not modified. |
| Worker ACL security experiment | **2 passed, 6 deselected** in Session 0 LocalSystem; interactive worker fixture Session 1; duplicate rejected; cleanup true; exact DACL rollback true. | Caller SID `S-1-5-18`; target local Administrator SID `S-1-5-21-950479549-2068523145-3370569714-500`; raw identity/log/hash evidence in bundle. |
| Interactive WPF | UIA launched the rebuilt Phase 5 app in console Session 1 without Agent Service; navigated all six implemented pages; both themes; keyboard focus; resize; minimize/restore; close-to-tray and tray restore. A follow-up run saved `CloseToTray=true`, closed the window, and observed the process alive with no main window. | Existing page screenshots plus `tray-close-to-tray-result.json` and `tray-uia-tree.json`. The taskbar exposes only `User Promoted Notification Area` (`ToolbarWindow32`) and not an individual tray icon/menu item to UIA. Tray `Exit` was not executed; the UIA limitation is isolated, not treated as an application pass. User preference was restored after the test. |
| Offline / runtime status | Dashboard, Runtime, Logs and Diagnostics correctly showed unavailable/timeout with no fabricated Agent/Worker/MT5 values. | Offline screenshots; no Agent Service/MT5 process was present on selected host. |
| DPI/accessibility | WPF window reported 96 DPI (100% scale), screen 1280×800; keyboard Tab focus and UIA names exercised. | 125/150/200% scaling, screen reader and instrumented contrast remain untested. |
| Performance | Startup N=5 median 152.7ms/P95(max) 198.0ms; idle N=20 for 20.2s CPU 0.155% total processor capacity, private bytes median 55.7MiB/max 58.4MiB; offline refresh completion N=10 median 2018.1ms/P95(max) 2099.4ms; navigation during refresh N=10 median 27.9ms/P95(max) 51.1ms; read-only test-Service status IPC N=30 median 0.32ms/P95 32.89ms/max 33.15ms; `logs.query` N=10 median 0.30ms/P95 31.57ms. | Raw method/sample evidence in `performance-measurements.txt` and `management-performance-probe.json`. Test Service did not include a Worker; no reconnect-time percentile or production load. |
| Installed Agent Service | **Test harness verified; product installer absent.** With explicit Product Owner authorization, a demand-start `MT5AgentPhase5Test` Service was installed on `window10-test`. A temporary .NET Framework `ServiceBase` wrapper ran the real Python Agent Core child in Session 0; the Runtime adapter was configuration-disabled; the Management pipe served authenticated read-only status/logs. SCM start/stop/restart and pipe disconnect/reconnect were observed; test Service/artifacts were removed. | [`service-lifecycle.txt`](../evidence/v0.1.4/phase5/windows10-19045/service-lifecycle.txt), live screenshot and JSON probes. Not a productized Service wrapper/installer; no Worker/MT5. |
| Management IPC authorization | **PASS for the isolated test Service identity and allowlist.** The authorized Administrator SID opened the pipe and completed 30/30 `status.get` plus 10/10 bounded `logs.query`. A temporary local Users-only account (`S-1-5-21-950479549-2068523145-3370569714-1011`) was not in Administrators or the allowlist; while impersonating its verified TokenUser, `CreateFile` failed with Win32 5 at the Windows Pipe DACL boundary before any protocol payload. Runtime SDDL was `D:(A;;FA;;;SY)(A;;0x12019b;;;LA)`, with `LA` resolving to the explicitly allowlisted local Administrator SID. Account, profile, service and files were removed. Existing forged-caller-claim/default-deny test remains covered in the regression suite. | [`negative-dacl-test-raw.json`](../evidence/v0.1.4/phase5/windows10-19045/negative-dacl-test-raw.json) and [`Phase5ManagementPipeDaclProbe.cs`](../../tests/windows/Phase5ManagementPipeDaclProbe.cs). This verifies the temporary test harness ACL; the eventual product Service identity/ACL provisioning still requires verification. The earlier NetworkService Scheduled Task `0x80070005` remains a harness failure, not DACL evidence. |
| RDP/session lifecycle | Session 0→Session 1 worker ACL fixture passed; only console Session 1 active. RDP disconnect/reconnect, logoff/login and reboot not run. | Do not infer an installed Service or production Worker lifecycle from the ACL fixture. |
| OS compatibility | Windows 10 evidence only. | Windows 11, Server 2022 and Server 2025 are exactly `DEFERRED — PRODUCT OWNER VALIDATION`; no tests were attempted and their deferral is not a Phase 5 blocker. |
| GitLab CI | **PASS:** Closure Pipeline [#48](http://gitlab.local/root/agent/-/pipelines/48) passed all 9 jobs on `bb7013f30c43ddf940212f9332341c0fb51ba55d`; GitLab reports 632 tests. | The test-only DACL caller probe is manual Windows 10 evidence and is not a pipeline job; the forged-claim regression is in the existing Python suite. |
| Trading | No real trade or order command executed. | Only status/diagnostic and controlled Worker sleeper fixture. |

A confirmed visual defect (long Dashboard status value clipped at tested width)
was fixed by enabling wrapping and adding the WPF regression test. The ACL test
harness defect (interactive helper calling privileged `WTSQueryUserToken`) was
fixed to verify the helper's own session and token identity before reading its
logon SID. No application security privilege was added.

## Phase 6 — Windows Desktop package baseline

**Status at Phase 6 branch start:** Accepted Phase 5 commit
`12826f42989cda7cee3e3847632cbf39bf1a21dc` on
`feat/v0.1.4-phase5-hardening`; Phase 6 branch
`feat/v0.1.4-phase6-packaging` was created directly from that commit. The Phase
5 baseline pipeline #49 passed 9/9 on the accepted commit. This is not Phase 6
package evidence.

**Test runner inventory:** `WINDOW10-TEST`, Windows 10 Pro x64 build 19045,
.NET Framework release key 533325, official .NET Framework v4.8 reference
assemblies present, active console Session 1, GitHub Actions Runner service
running. The host scan found no MT5 or Python Agent processes and no Agent
Service. No candidate authorized production code-signing certificate with
private key was identified (count only; certificate material was not read or
exported). The Windows 10 runner is shared infrastructure; tests must remain
bounded and must not alter existing sessions or Service configuration.

Phase 6 adds a ZIP-only WPF distribution workflow; it does not package or
modify the Agent/Worker. See [Distribution](DISTRIBUTION.md) for the exact
package boundary and the final pipeline/artifact evidence. Windows 11 and
Windows Server 2022/2025 remain `DEFERRED — PRODUCT OWNER VALIDATION`.
