# v0.1.4 Desktop Package Validation Checklist

This checklist separates Phase 6 implementation completion from commercial
publication authorization. A passing Phase 6 package does not authorize a
public release.

## Phase 6 implementation gates

- [x] Build WPF Release x64 once on the Windows 10 runner (pipeline #53,
  job #438).
- [x] Run compiled C# and Management IPC tests without rebuilding the
  WPF application.
- [x] Produce the versioned Desktop ZIP and record commit, pipeline, build job,
  framework reference version, MSBuild version, and SHA-256.
- [x] Validate the exact ZIP in a downstream job: safe extraction, no duplicate
  or traversal path, complete manifest/checksum coverage, expected file list,
  unchanged archive hash, packaged EXE hash equal to the tested build, and a
  three-second non-interactive launch smoke (pipeline #53, job #446).
- [x] Extract the CI ZIP into a fresh CI validation directory without relying on
  Visual Studio or source files; the packaged process stayed alive in the
  bounded non-interactive launch smoke.
- [ ] Interactively verify Dashboard, Runtime, Settings, Logs, Diagnostics,
  About, theme and
  preferences persistence, tray behavior where interactive, offline behavior,
  authorized read-only Management IPC behavior, and controlled exit.
- [ ] Verify user preferences survive replacement and rollback; verify removal
  deletes only the Desktop version folder/shortcut and leaves Agent, Worker,
  machine configuration and user settings unchanged.
- [ ] Scan package contents for secrets, private keys, test credentials,
  development endpoints, PDBs, test assemblies and Python runtime files.
- [x] Run C#, Windows/Python, Linux/Python, IPC, smoke, and existing Agent
  packaging gates without weakening any job (all 11 jobs passed in pipeline #53).
- [x] Confirm the tested branch commit has a successful GitLab pipeline and
  retain the exact tested artifact and evidence.
- [ ] No real trade, tag, release publication, production deployment, Service
  reconfiguration or automatic provisioning occurs in Phase 6.

## Commercial/public release gates

- [ ] Production code signing with an authorized certificate and protected
  signing process.
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

Pipeline #53 passed on commit `246b1f109e56c32ba7174d23a1bb5708805750e4`.
Build job #438 produced the 55,230-byte ZIP with SHA-256
`01db0addfc3e85993fcb429ec124d5ce14fd48dabd5271d52fc0f00f51e40cff`;
package verification job #446 consumed that artifact and passed. The unchecked
interactive package, replacement, rollback and removal gates remain open.
Public release is blocked on authorized code signing and applicable commercial
validation gates.
