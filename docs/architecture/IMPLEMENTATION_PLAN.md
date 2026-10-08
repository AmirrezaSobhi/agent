# v0.1.4 WPF Implementation Plan

**Status:** Ready for planning review; this document does not begin
implementation. Each phase is a small implementation mission with explicit
entry/exit criteria. Python Core remains Python; no feature work is authorized
by this plan itself.

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

## Phase 2 — Secure Local Communication

- **Dependencies:** Service principal/SID and local roles approved; dedicated
  pipe name and permission matrix; operational provisioning method agreed.
- **Likely files/modules:** new Python management adapter/authorization under
  `agent/application` and `agent/infrastructure`; new .NET
  `Services/Management/NamedPipeManagementClient`; JSON contract fixtures;
  tests near existing `tests/test_windows_named_pipe*.py` and WPF Tests.
- **Deliverables:** separate management pipe, independent from
  `MT5Agent.Runtime.v1`; OS DACL + server-derived client SID + per-operation
  authz; v1 bounded JSON contract, correlation/errors, timeout and backpressure.
- **Acceptance:** unknown SID/operation/version denied; no `Everyone` DACL;
  64 KiB limit; request/response correlation; 4 active/16 queued admission
  limits under proposed policy; `BUSY` on overflow; current `/command` remains
  unmodified and is not used by the UI.
- **Tests:** Python ACL/token/authorization negatives; C# protocol serializer,
  timeout/cancel/reconnect; shared malformed/oversized/versioned fixtures;
  cross-user Windows integration test.
- **Risks:** Python Named Pipe peer-token/impersonation behavior must be proven;
  current Service identity may not be provisioned for cross-SID pipe access.

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

- **Dependencies:** Phase 1 shell and Phase 2 permission contract; support
  collection allowlist/privacy review.
- **Likely files/modules:** Runtime, Settings, Logs, Diagnostics, Support,
  Updates informational page, About, per-user preferences and tray/notices.
- **Deliverables:** safe read-only runtime page; per-user preferences;
  diagnostic summary and bounded log paging; local support export preview;
  tray/close preference; documented SCM/UAC recovery guidance. Central/updates
  modules show unavailable states, not simulated functions.
- **Acceptance:** no machine setting writes from ordinary preferences; log list
  virtualizes 10,000 fake rows; support cancel has no network transmission;
  closing tray/UI leaves Agent and Worker running; SCM actions remain OS-ACL
  governed, no custom helper.
- **Tests:** user-scope storage isolation; log paging/performance; redaction
  canaries; UI lifecycle and service-offline integration.
- **Risks:** accessing protected Service logs may be denied; show that condition
  cleanly without expanding permissions.

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

1. `desktop:restore-build` on Windows x64 runner with pinned Visual Studio
   Build Tools, .NET Framework 4.8 Developer Pack and NuGet restore; emits one
   immutable WPF artifact and build manifest.
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
7. Release publication promotes the exact tested package; no rebuild between
   test and release. Keep current `.gitlab-ci.yml` unchanged until a separate
   implementation task authorizes CI work.

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
