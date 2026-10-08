# v0.1.4 Desktop Package Validation Checklist

This checklist separates Phase 6 implementation completion from commercial
publication authorization. A passing Phase 6 package does not authorize a
public release.

## Phase 6 implementation gates

- [ ] Build WPF Release x64 once on the supported Windows build runner.
- [ ] Run the compiled C# tests and Management IPC tests without rebuilding the
  WPF application.
- [ ] Produce the versioned Desktop ZIP and record commit, pipeline, build job,
  framework reference version, MSBuild version, and SHA-256.
- [ ] Validate the exact ZIP in a downstream job: safe extraction, no duplicate
  or traversal path, complete manifest/checksum coverage, expected file list,
  unchanged archive hash, and packaged EXE hash equal to the tested build.
- [ ] On Windows 10 x64, extract the CI artifact to a clean user-writable path
  with no source tree or Visual Studio present; launch the packaged executable.
- [ ] Verify Dashboard, Runtime, Settings, Logs, Diagnostics, About, theme and
  preferences persistence, tray behavior where interactive, offline behavior,
  authorized read-only Management IPC behavior, and controlled exit.
- [ ] Verify user preferences survive replacement and rollback; verify removal
  deletes only the Desktop version folder/shortcut and leaves Agent, Worker,
  machine configuration and user settings unchanged.
- [ ] Scan package contents for secrets, private keys, test credentials,
  development endpoints, PDBs, test assemblies and Python runtime files.
- [ ] Run C#, Windows/Python, Linux/Python, IPC, smoke, and existing Agent
  packaging gates without weakening any job.
- [ ] Confirm the final branch commit has a successful GitLab pipeline and
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
