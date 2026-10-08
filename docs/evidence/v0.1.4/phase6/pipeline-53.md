# Phase 6 Pipeline 53 Evidence

## Provenance

- Branch: `feat/v0.1.4-phase6-packaging`
- Commit: `246b1f109e56c32ba7174d23a1bb5708805750e4`
- Pipeline: [#53](http://gitlab.local/root/agent/-/pipelines/53), **11/11 jobs passed**
- Build job: [desktop:build-package #438](http://gitlab.local/root/agent/-/jobs/438)
- Same-output test job: [test:wpf-management #441](http://gitlab.local/root/agent/-/jobs/441)
- Package verification: [desktop:package-verify #446](http://gitlab.local/root/agent/-/jobs/446)
- Build runner: `WINDOW10-TEST`, Windows 10 Pro x64, build 19045
- Toolchain: MSBuild `4.8.9037.0 built by: NET481REL1`; .NET Framework release key `533325`; .NET Framework 4.8 reference assemblies `4.8.3761.0`

## Desktop artifact

- File: `MT5Agent-Desktop-v0.1.4-windows-x64.zip`
- Size: 55,230 bytes
- SHA-256: `01db0addfc3e85993fcb429ec124d5ce14fd48dabd5271d52fc0f00f51e40cff`
- Packaged executable SHA-256: `f191b65826acf57b80819205a0b4337ff37a73e85de7cfe926aa5ce7d8e5df97`
- Manifest provenance: commit `246b1f109e56c32ba7174d23a1bb5708805750e4`, pipeline `53`, build job `438`
- Authenticode: unsigned. No production signing identity is claimed.

## Validation performed

Build job #438 performed one Release x64 rebuild and emitted the ZIP, build
report, and compiled test outputs. Test job #441 downloaded these outputs and
did not rebuild the WPF solution. It reported 41 C# tests passed, 23 Windows
Management IPC tests passed, and a deterministic cross-process read-only
status smoke (`IPC_SMOKE_PASS`; one 72 ms round-trip sample). Pipeline-wide
GitLab test summary was 634 tests. The Linux/Windows Python, Agent build,
configuration/control-plane/MT5 runtime smoke, and existing Agent packaging
jobs all passed.

Verifier job #446 downloaded the build job's ZIP, safely extracted it in a
fresh CI validation directory, checked manifest and checksum coverage,
provenance, declared payload set, packaged executable hash, and unchanged ZIP
hash. It then launched the packaged WPF executable in the CI session and
observed the process alive after three seconds before controlled test cleanup.
The job succeeded only when the structured verifier report returned
`status=PASS`.

## Limitations

- CI launch was non-interactive. It is not visual verification of Dashboard,
  Runtime, Settings, Logs, Diagnostics, About, themes, tray or notifications.
- No Agent Windows Service is installed on the shared Windows runner; the IPC
  smoke used a deterministic test Agent, not an installed product Service.
- No interactive extraction into a normal user's install folder, settings
  survival across package replacement, rollback, package removal, DPI,
  accessibility, performance benchmark or extended stability run was done
  with this ZIP.
- The runner has no authorized production code-signing certificate.
- Windows 11, Windows Server 2022 and Windows Server 2025 remain
  `DEFERRED — PRODUCT OWNER VALIDATION`.
- No real trade or production deployment occurred.

## CI correction history

Pipeline #52 built and tested successfully but its package verification wrapper
failed after invocation of the PowerShell verifier because it inspected stale
`$LASTEXITCODE`, which is not the success contract for a `.ps1` script. The
verifier's structured status is now parsed and required to equal `PASS`; the
pipeline topology test guards this condition. Pipeline #53 validates the
corrected wrapper and passes all jobs.
