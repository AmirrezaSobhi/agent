# v0.1.4 WPF Implementation Plan

**Status:** Phases 1–4 are implemented. Phase 5 Windows 10 build/tests,
interactive UI validation, reversible SCM integration, and a low-privilege
runtime Pipe DACL rejection have been executed. The latest baseline pipeline
[#47](http://gitlab.local/root/agent/-/pipelines/47) passed all 9 jobs on
`b780a2c703891a2e407be153d547102fab44e58a`; this predates the final closure
evidence and does not validate the closure commit. Python Core remains Python.

## Approved release boundary — Option A

v0.1.4 delivers a C# WPF Desktop Client for an **already installed and
provisioned** Agent/Runtime. The existing Python Agent and MT5 Runtime Worker
remain operational foundation. Release requires reproducible WPF build and a
testable user-scope deployment package suitable for an already prepared host.

It does not require commercial installer, Service provisioning, runtime-account
creation, Autologon setup, enterprise orchestration, central control plane,
production billing, automatic update/rollback, multi-runtime, or multi-Agent
failover. Service restart may use Windows SCM/UAC if the operator has rights;
do not introduce a custom elevated helper in this release absent a separately
approved need. See [ADR-ARCH-016](adr/ADR-ARCH-016-release-boundary-option-a.md).

## Phase 1 — WPF Foundation

**Implementation state:** Implemented with known verification limits. The
two-project shell, MVVM/navigation, themes, per-user theme preference, English
resources, Management IPC-backed Dashboard, and 27-test executable are present.
Windows build and test evidence plus targeting-pack and interactive-UI gaps are
recorded in [`src/desktop/README.md`](../../src/desktop/README.md). CI was not
changed.

- **Dependencies:** approved WPF ADR; Windows build runner with Visual Studio
  Build Tools/.NET Framework 4.8 Developer Pack; no Python code changes needed.
- **Likely files/modules:** `src/desktop/MT5Agent.Desktop.sln`,
  `MT5Agent.Desktop/{App.xaml,Views,ViewModels,Services,Controls,Themes,Resources,Assets}`,
  `MT5Agent.Desktop.Tests`; future `.gitignore` additions only if approved.
- **Deliverables:** two-project solution; x64 WPF shell, MVVM boundaries,
  manual composition root, sidebar navigation, custom design tokens/light-dark,
  resource-based English, accessibility baseline, placeholder states clearly
  labeled unavailable; reproducible local Release build.
- **Acceptance:** builds from clean checkout with pinned toolchain; no Kivy/Python
  UI dependency; no project cycles; 10 navigation destinations work or clearly
  show unavailable; UI remains responsive during a fake 2 s service request.
- **Tests:** build + analyzer, ViewModel binding/navigation tests, theme/token
  resource load tests, UIA keyboard/name smoke in interactive desktop job.
- **Risks:** framework/IDE targeting pack drift; XAML style leakage; Win32 tray
  behavior must not be pulled into shell before its separate test.

## Phase 2 — Secure Local Communication (implemented read-only slice)

- **Status:** Implemented read-only `protocol.negotiate` and `status.get`.
- **Dependencies satisfied for this slice:** separate pipe, 64 KiB limit,
  explicit SID list, OS-token caller identity, fail-closed authorization,
  correlatable JSON responses, 2 s client/server timeout and testable fake
  status host. SID environment must be configured by a machine administrator.
- **Likely files/modules:** `agent/infrastructure/management_named_pipe.py`,
  `agent/infrastructure/composite_host.py`, `agent/composition.py`, C#
  `Services/Management/NamedPipeManagementClient`, and management contract
  tests.
- **Deliverables:** separate `MT5Agent.Management.v1` endpoint. Existing
  `MT5Agent.Runtime.v1` and `/command` were not repurposed. Service start/stop,
  diagnostics, logs, preferences, Runtime restart and trading remain absent.
- **Verified:** security spike proved token SID/DACL and Session 0 ↔ Session 1
  primitives; Python management pipe tests 15/15, C# suite 27/27, synthetic
  cross-language status smoke passed. No production Service or trade was used.
- **Not complete:** Windows multi-user/multi-session matrix, production
  Service-account/group provisioning, Windows 11/Server coverage, active
  GitLab job evidence and UI automation.
- **Remaining risks:** server status-provider work can outlive client
  cancellation; active concurrency is one instance with no application queue;
  provisioned allowlist management requires an administrator; error/log
  telemetry for DACL-denied clients is not observable by the Agent.

## Phase 3 — Real Dashboard

- **Dependencies:** Phase 2 status contract; source/freshness data contract;
  current Agent diagnostics mapped without inventing central or trading data.
- **Likely files/modules:** Dashboard cards/ViewModels, `StatusSnapshot` DTOs,
  management status operations and contract tests.
- **Deliverables:** seven dimensions: `SERVICE_RUNNING`,
  `LOCAL_AGENT_RESPONSIVE`, `WORKER_READY`, `MT5_CONNECTED`,
  `CENTRAL_CONNECTED`, `TRADING_CAPABILITY`, `TRADING_AUTHORIZED`; Local Setup
  uses Central=`NOT_CONFIGURED`; trading capability=`UNSUPPORTED` for v0.1.4.
- **Acceptance:** each dimension includes state/source/UTC timestamp/age/reason;
  current observations stale after defined thresholds; no cached state shown
  as live; Worker readiness requires current Worker health, not Agent process.
- **Tests:** ViewModel state transition tests; fake pipe success/timeouts; live
  prepared-host safe-read tests only; no order calls.
- **Risks:** existing diagnostic schema does not yet include the complete status
  age contract; map every new field to a verified source.

## Phase 4 — Desktop Operations

**Status: Implemented in branch `feat/v0.1.4-phase4-desktop-operations`;
Windows 10 build/tests, interactive desktop validation and GitLab pipeline
validation passed. Broader compatibility and commercial release gates remain
open.**

- **Dependencies:** Phase 1 shell, Phase 2 read-only identity/authorization
  contract and Phase 3 status projection.
- **Deliverables:** Runtime page maps authenticated Agent/Worker/MT5 status and
  labels unavailable runtime identity/process/session fields; Settings persist
  theme, bounded refresh interval, notification and close-to-tray preferences
  under the current user's LocalAppData; Diagnostics show local version,
  framework target, OS and last Agent response/error; Logs query a fixed-message
  in-memory Agent Management ring buffer (200 retained, 100 maximum returned)
  with local severity/search filtering; tray open/minimize/close-to-tray and
  explicit Exit; deduplicated connection notices. Central, accounts, support,
  startup registration and updates remain unavailable.
- **Security boundary:** `logs.query` is read-only, same SID allowlist as status,
  validates a count ≤100 and enumerated severity, returns static messages and
  never accepts paths or reads files. No Service/Worker controls, secrets,
  `/command`, Worker pipe, or trading operation was added.
- **Tests:** Windows Release x64 rebuild passed; 40/40 C# tests passed,
  including new user-preference validation, Runtime projection, log filtering,
  offline diagnostics and Management log serialization tests. Full Python
  regression rerun and interactive desktop evidence are recorded in the
  Phase 4 implementation baseline section.
- **Not included:** support bundle/export, log file retrieval, Windows startup
  registration, persistent notification center and service controls; there is
  no approved source/consent/privilege model for those features yet.
- **Risks:** current log history is volatile and limited to Management events;
  actual process/session identity is not available from current status
  contract. Production Service identity, multiple-session behavior, supported
  OS matrix, package validation, and user-desktop visual evidence remain gates.

## Phase 5 — Hardening

- **Scope decision:** Windows 10 x64 is the only OS required in Phase 5.
  Windows 11, Server 2022 Desktop Experience, and Server 2025 Desktop Experience
  are `DEFERRED — PRODUCT OWNER VALIDATION`, and are not Phase 5 blockers.
- **Dependencies:** Phase 4 candidate and existing interactive Windows 10
  console runner; no new VM provisioning was requested or performed.
- **Completed:** Windows 10 clean x64 rebuild and tests, interactive WPF/UIA,
  two dedicated Worker ACL tests, offline/live status and bounded log view,
  allowed-SID/LocalSystem authorization checks, reversible SCM integration
  harness with the real Python Agent Core in Session 0, stop/restart/pipe
  reconnection, IPC measurements, and Dashboard text wrapping correction.
- **Completed in the final security closure:** an allowlisted Administrator
  opened the live Management Pipe and completed 30 status plus 10 bounded log
  requests; a temporary Users-only account was rejected with Win32
  `ERROR_ACCESS_DENIED (5)` by the actual Pipe DACL at `CreateFile`. The
  NetworkService Scheduled Task failure is retained as a distinct harness
  failure, not security evidence. Tray close-to-tray was observed; the actual
  tray Exit menu remains unverified because UI Automation exposes no app menu.
- **Remaining:** safe RDP/session coverage, higher DPI/accessibility, long
  soak, product Service provisioning, and production packaging/signing. These
  are release limitations; the three other OS validations remain deferred to
  the Product Owner and do not block Phase 5.
- **Risks:** repository still has no productized SCM Service wrapper/installer;
  the temporary .NET ServiceBase wrapper is test evidence only. Shared console
  reboot/RDP interruption was avoided. Other OS tests belong to the Product
  Owner and are explicitly deferred for this phase.

## Phase 6 — Packaging and Release

- **Dependencies:** all P0 gates, target OS decision/build evidence and signed
  review of package contents.
- **Likely files/modules:** WPF Release configuration, packaging script and
  manifest under `deployment/desktop/` (to be designed during implementation),
  future GitLab job definition in a separately authorized CI change.
- **Deliverables:** reproducible x64 ZIP/directory package for user-scope
  deployment on prepared machine; manifest with product version, source commit,
  .NET prerequisite, file list and SHA-256; concise deployment/removal guide.
  No Windows Service installation or mutation.
- **Acceptance:** install/extract under current user's application directory,
  first launch while Service is offline and online, clean remove without
  changing Service/Worker/config, package hash equals the tested artifact.
- **Tests:** package validation, clean VM launch on all four targets, same
  artifact provenance across test and release jobs.
- **Risks:** no signing certificate/process is evidenced in current project;
  decide code signing as a release-policy gate before public distribution.

## Future GitLab CI design (not applied here)

1. `test:wpf-management` now runs on the existing Windows no-MT5 runner. It
   requires the official .NET Framework 4.8 Developer/Targeting Pack, performs
   a clean x64 Release rebuild, runs the WPF test executable and management
   pipe Python contract tests. It does not alter Python regression gates.
2. `desktop:analyzers` and `desktop:unit-tests` consume same commit/source and
   report TRX; parallel Python Linux/Windows regression jobs remain intact.
3. `desktop:ipc-contract` runs Python/C# golden JSON and fake-pipe tests on a
   Windows runner, no MT5 dependency.
4. `desktop:ui-automation` consumes the built artifact on a dedicated
   interactive Windows desktop runner. A Session 0 runner service is not
   assumed to own an interactive desktop; provision a separate runner process
   in an authorized logged-on test session or an equivalent isolated desktop
   VM. Do not use a live trading account.
5. `desktop:runtime-integration` runs existing Agent/Worker safe-read tests on
   the already configured MT5 test runner in its required interactive session;
   remains distinct from UIA.
6. `desktop:package-validate` consumes the same build output, verifies file
   manifest/SHA and starts app on prepared target VMs.
7. Release publication continues promoting the existing Python package and
   was not changed. WPF same-artifact packaging/promotion is future work; this
   job's artifacts are test outputs, not a commercial deployment package.

Phase 5 required no additional operating-system infrastructure beyond the
existing Windows 10 host; Windows 11 and Server 2022/2025 tests are deferred to
Product Owner validation and must not be provisioned for this phase. For later
Product Owner compatibility validation, use authorized prepared Desktop
Experience systems and record separate OS evidence. Interactive tests must run
in a logged-on desktop session; a Session 0 build runner is not an interactive
UI lane. The existing Windows 10 console was used for this Phase 5 run.

## Related documents

[WPF Solution](WPF_SOLUTION.md) · [IPC Contract](IPC_CONTRACT.md) ·
[Quality Gates](QUALITY_GATES.md) · [Acceptance](ACCEPTANCE_V0.1.4.md) ·
[Roadmap](ROADMAP.md)

### Phase 5 execution result — 2026-10-08

Phase 5 continues from Phase 4 final commit `59a6b7c97326f0ac22ba26f5243117972b623ade`;
the Phase 5 baseline is `9286e4f5640c979ccaf345b7fdf64a962d7e77bc`. Windows 10
validation completed on `window10-test` (build 19045.6466): official net48
clean x64 build, C# 41/41, Windows Python 318 passed/2 gated skips, isolated
Worker ACL experiment 2/2, Linux Python 276/36, interactive screenshots,
temporary SCM integration with real Agent Core, read-only Management status/log
requests, and IPC performance samples. See [Implementation Baseline](IMPLEMENTATION_BASELINE.md)
and [Windows Compatibility Matrix](WINDOWS_COMPATIBILITY.md).

The repository still has no productized SCM Service adapter/installer; the
temporary .NET ServiceBase test host was removed after isolated SCM
start/stop/restart and pipe-reconnection tests. RDP/logoff/reboot remain
unexecuted on the shared console host. Windows 11, Server 2022 and Server 2025
are `DEFERRED — PRODUCT OWNER VALIDATION`, not Phase 5 blockers. The runtime
Pipe DACL negative case is now verified with an ordinary Users-only account;
the separate NetworkService task launch failure remains classified as a
harness failure. Tray Exit remains unverified due to the UIA surface limitation.
Pipeline #47 is the previous baseline only. Final closure pipeline evidence is
recorded in the Phase 5 evidence bundle after it executes.
Do not claim commercial readiness.
