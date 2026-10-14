# v0.1.4 Desktop Package Validation Checklist

This checklist separates Phase 6 implementation completion from commercial
publication authorization. A passing Phase 6 package does not authorize a
public release.

## Phase 6 implementation gates

- [x] Build WPF Release x64 once on the Windows 10 runner (pipeline #54,
  job #449, executable source commit `567c6810292c92ec4b00d8b9ae01e458fcabb88c`).
- [x] Run compiled C# and Management IPC tests without rebuilding the
  WPF application.
- [x] Produce the versioned Desktop ZIP and record commit, pipeline, build job,
  framework reference version, MSBuild version, and SHA-256.
- [x] Validate the exact ZIP in a downstream job: safe extraction, no duplicate
  or traversal path, complete manifest/checksum coverage, expected file list,
  unchanged archive hash, packaged EXE hash equal to the tested build, and a
  bounded non-interactive launch smoke (pipeline #54, job #457).
- [x] Extract the CI ZIP into a fresh CI validation directory without relying on
  Visual Studio or source files; the packaged process stayed alive in the
  bounded non-interactive launch smoke.
- [ ] Interactive package walkthrough (Dashboard, pages, themes, tray and
  shutdown): **DEFERRED**; optional for this internal milestone.
- [ ] Installed product Service connection through the extracted package:
  **DEFERRED**; existing Phase 5 Service/IPC and Phase 6 deterministic IPC
  fixture evidence remain applicable to their tested scopes.
- [ ] Side-by-side replacement/rollback and removal inventory: **DEFERRED**.
  The manual procedure preserves prior binaries and keeps user preferences
  outside the app folder; it was not rehearsed on Windows in this milestone.
- [ ] Independent secret-canary scan: **DEFERRED**. The CI manifest/allowlist
  validated package contents; no separate canary scan is claimed.
- [x] Run C#, Windows/Python, Linux/Python, IPC, smoke, and existing Agent
  packaging gates without weakening any job (all 11 jobs passed in pipeline #54).
- [x] Confirm the tested branch commit has a successful GitLab pipeline and
  retain the exact tested artifact and evidence.
- [x] No real trade, tag, release publication, production deployment, Service
  reconfiguration or automatic provisioning was performed.

**Internal milestone:** COMPLETE — INTERNAL DEVELOPMENT MILESTONE. Pipeline #54
passed 11/11 jobs for executable source commit `567c6810292c92ec4b00d8b9ae01e458fcabb88c`.
The tested ZIP is `MT5Agent-Desktop-v0.1.4-windows-x64.zip`, SHA-256
`ad32e673cc7a3f18f4eb64e25cbfb4f64fe438e103d9c139aed4c21b1bc5ac63`.
Interactive package testing and other deferred checks do not block this
Product Owner-approved internal milestone. Commercial release remains NOT
APPROVED.

## Commercial/public release gates

- [ ] Production code signing with an authorized certificate and protected
  signing process. Current package status: `UNSIGNED — ACCEPTED FOR INTERNAL
  DEVELOPMENT`; commercial/public release remains blocked.
- [ ] Product-owner review of all Windows 10 release-support/lifecycle
  conditions.
- [ ] Product Owner validation of Windows 11, Windows Server 2022 Desktop
  Experience, and Windows Server 2025 Desktop Experience. Until then each is
  `DEFERRED — PRODUCT OWNER VALIDATION`.
- [ ] Product-grade Agent Service provisioning and recovery procedure, if
  required by the eventual distribution contract.
- [ ] Manual Tray Exit validation if automation cannot invoke the notification
  icon menu.
- [ ] Extended DPI/accessibility and stability evidence as required by the
  commercial quality target.
- [ ] Separate Product Owner authorization for any public release or deployment.

## Evidence record

Record one row per gate in `docs/architecture/DISTRIBUTION.md` or the attached
release evidence bundle. Include status `PASS`, `FAIL`, `BLOCKED`, `PENDING`, or
`DEFERRED`, the tested commit/artifact hash, pipeline/job identity, environment,
test method, evidence path, and limitation. Never infer success from a build,
source inspection, skipped test, or different artifact.

Pipeline #54 passed 11/11 jobs on executable source commit
`567c6810292c92ec4b00d8b9ae01e458fcabb88c`. Build job #449 produced
`MT5Agent-Desktop-v0.1.4-windows-x64.zip` with SHA-256
`ad32e673cc7a3f18f4eb64e25cbfb4f64fe438e103d9c139aed4c21b1bc5ac63`;
verification job #457 consumed that artifact and passed. Interactive package,
installed-Service integration, replacement/rollback/removal, extended DPI,
accessibility and stability checks remain visibly deferred. See
[`DISTRIBUTION.md`](DISTRIBUTION.md). Public release is not approved and
requires authorized code signing and applicable commercial validation gates.
