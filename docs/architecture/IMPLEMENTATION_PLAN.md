# v0.1.4 WPF Implementation Plan

**Status:** Phase 1 foundation and read-only slice of Phase 2 are implemented;
remaining Phase 2 gates and Phases 3–6 remain open. Python Core remains Python.

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

- **Dependencies:** feature-complete candidate and interactive UI runner.
- **Likely files/modules:** all WPF project tests, packaging manifest, test
  harnesses, non-destructive CI job additions in a separately authorized change.
- **Deliverables:** four-OS compatibility evidence, UI automation, performance,
  accessibility, cross-user session tests, crash/pipe failure handling, Python
  regression proof.
- **Acceptance:** pass applicable [20 quality gates](QUALITY_GATES.md); no
  functional regressions in Python Agent, Worker, Named Pipe or safe reads.
- **Tests:** automated tests in CI; Windows UIA on interactive runner; Service
  Session 0 and MT5 Runtime tests remain separate jobs/hosts.
- **Risks:** CI Session 0 cannot exercise an interactive WPF desktop; Server
  editions and Windows 10 lifecycle servicing availability require prepared
  VMs and customer-facing support policy.

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

Minimum additional infrastructure: Windows 11 x64 interactive UIA VM with
fixed display resolution/scale and resettable snapshot; build runner with
Visual Studio/MSBuild; prepared Desktop Experience validation VMs for Server
2022 and 2025. Existing Windows 10 Session 0 runners cannot substitute for
interactive UI testing; current runner inventory has no Server 2022/2025 or
verified UI automation lane.

## Related documents

[WPF Solution](WPF_SOLUTION.md) · [IPC Contract](IPC_CONTRACT.md) ·
[Quality Gates](QUALITY_GATES.md) · [Acceptance](ACCEPTANCE_V0.1.4.md) ·
[Roadmap](ROADMAP.md)

### Phase 5 execution result — 2026-10-08

The Phase 5 worktree was created at the verified Phase 4 final commit
`59a6b7c97326f0ac22ba26f5243117972b623ade`. Inventory found Windows 10 Pro
build 19045 x64 runners only and no installed MT5Agent Agent Service. The
execution environment could not attach to the remote interactive desktop for
WPF UI Automation or screenshots. No permitted source defect was confirmed;
therefore no application implementation was changed in this evidence update.

Blocked/pending deliverables: actual installed-Service lifecycle; two gated
Worker ACL tests; RDP/logoff/reboot and multi-session validation; Windows 11,
Server 2022 Desktop Experience, Server 2025 Desktop Experience; interactive
visual/DPI/accessibility checks; repeatable CPU/memory/latency/soak data; and
Phase 5 CI pipeline evidence. See the [Phase 5 baseline](IMPLEMENTATION_BASELINE.md#phase-5-verification-snapshot-2026-10-08)
and [compatibility matrix](WINDOWS_COMPATIBILITY.md). Do not mark Phase 5 or
commercial readiness complete until required blockers are cleared.
