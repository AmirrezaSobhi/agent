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

`.gitlab-ci.yml` now has a separate `test:wpf-management` job that requires
the official reference pack and runs WPF tests plus Management IPC Python
tests. It does not modify Python gates or release publication jobs. No GitLab
pipeline for this feature branch was run; CI job execution remains unverified.

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

## Evidence rules

Evidence paths above are repository-relative and symbols/tests are named where
available. A file or test existing does not itself prove production wiring;
pipeline passes only prove the tested commit and runner scenario. The complete
acceptance checklist is [v0.1.4 acceptance](ACCEPTANCE_V0.1.4.md).
