# Windows Desktop Distribution — v0.1.4

**Status:** Implemented internal ZIP workflow. Windows 10 CI evidence below is
for the exact Phase 6 branch commit and artifact; interactive release
validation and commercial release approval remain separate gates.

## Package boundary

The distribution is a versioned, user-scope ZIP named
`MT5Agent-Desktop-v0.1.4-windows-x64.zip`. It contains only the WPF application
files, `MANIFEST.json`, `SHA256SUMS.txt`, and short installation documents.
The Python Agent, Windows Service, Runtime Worker, MT5, account profiles,
machine configuration, credentials, test binaries, and developer files are
excluded. The ZIP does not change any existing Agent/Worker installation.

The application targets .NET Framework 4.8. The prepared Windows host needs
.NET Framework 4.8 or later. The .NET Framework 4.8 Developer/Targeting Pack,
64-bit MSBuild and Python test dependencies are build/CI prerequisites, not
end-user package requirements. The selected Windows 10 test runner reports
framework release key `533325` and has the official v4.8 reference assemblies.

## Build and integrity contract

`.gitlab-ci.yml` schedules `desktop:build-package` once per pipeline. That job
performs one clean Release x64 solution rebuild, runs
`deployment/desktop/New-DesktopPackage.ps1`, and emits the immutable ZIP,
build report, and already-built C# test outputs. `test:wpf-management` runs
those test outputs without rebuilding the WPF solution. The downstream
`desktop:package-verify` job consumes the same ZIP and build report, extracts
the package, rejects unsafe/duplicate paths and undeclared files, validates
manifest and SHA-256 coverage, checks the packaged EXE against the tested build
hash, and confirms that the ZIP hash did not change during validation.

The manifest records product version, source commit, pipeline ID, build job ID,
build-host framework version, framework reference assembly version, file
lengths and SHA-256. The sidecar `desktop-build.json` records archive and EXE
hashes plus MSBuild version. No downstream WPF rebuild is permitted in this
artifact chain. Python Agent build/smoke/package jobs remain independent and
unchanged.

Package ZIP entries use sorted paths and a fixed timestamp. The compiler build
is deterministic where supported by the existing project. Provenance fields
vary per pipeline by design; therefore “reproducible” means a traceable clean
build and immutable tested artifact, not a byte-identical archive across
different pipeline IDs.

## Installation, replacement and removal

See [`deployment/desktop/INSTALL.md`](../../deployment/desktop/INSTALL.md),
which is also included in the ZIP. Extract to a versioned user-writable
directory such as `%LOCALAPPDATA%\Programs\MT5Agent\Desktop\v0.1.4` and launch
`app\MT5Agent.Desktop.exe`. The existing Agent must be separately provisioned;
an administrator must separately configure the Management Pipe SID allowlist.

For upgrades, exit the UI and unpack into a new version directory. Repoint the
shortcut only after checking the new build, and retain the old directory for
manual rollback. Remove only the selected Desktop version directory and
shortcut. Per-user preferences at
`%LOCALAPPDATA%\MT5Agent\Desktop\preferences.v1` are outside the package and
are retained. Machine configuration and Agent/Worker files are untouched.

User preference writes are validated and use a temporary file followed by an
atomic move/replacement (`src/desktop/MT5Agent.Desktop/Services/UserPreferencesStore.cs`).
Corrupt or inaccessible preferences fall back to safe defaults. No secret is
stored in the Desktop preferences schema.

## Signing and release boundary

The package is unsigned. No authorized production code-signing certificate or
signing infrastructure was identified in the inspected Windows runner; CI
must not create a self-signed production identity. This is a **commercial
release blocker**, not a Phase 6 package-build blocker. The archive is for
controlled internal validation only. No release is published by this workflow.

Windows 10 x64 is the only Codex validation target for Phase 6. Windows 11,
Windows Server 2022 Desktop Experience, and Windows Server 2025 Desktop
Experience remain `DEFERRED — PRODUCT OWNER VALIDATION`; no result on Windows 10
implies their compatibility.

## Phase 6 evidence

| Gate | Evidence | Result |
|---|---|---|
| Branch baseline | Accepted Phase 5 SHA `12826f42989cda7cee3e3847632cbf39bf1a21dc`; Phase 6 branch created directly from it | PASS |
| Windows 10 Release build | Pipeline [#53](http://gitlab.local/root/agent/-/pipelines/53), commit `246b1f109e56c32ba7174d23a1bb5708805750e4`; build job [#438](http://gitlab.local/root/agent/-/jobs/438), runner `WINDOW10-TEST`, Windows 10 Pro x64 build 19045; MSBuild `4.8.9037.0 built by: NET481REL1`; official .NET Framework 4.8 reference assembly `4.8.3761.0`; framework release key `533325` | PASS |
| Build Once → Test Same Artifact | Job #438 performed one clean Release x64 rebuild and uploaded app/test outputs and ZIP; [test:wpf-management #441](http://gitlab.local/root/agent/-/jobs/441) consumed those outputs without rebuilding and passed 41 C# tests, 23 Python Management IPC tests and deterministic cross-process status smoke; [package verifier #446](http://gitlab.local/root/agent/-/jobs/446) consumed the ZIP from #438 | PASS |
| Package SHA-256 and provenance | `MT5Agent-Desktop-v0.1.4-windows-x64.zip`, 55,230 bytes; SHA-256 `01db0addfc3e85993fcb429ec124d5ce14fd48dabd5271d52fc0f00f51e40cff`; source `246b1f109e56c32ba7174d23a1bb5708805750e4`; pipeline 53; build job 438; packaged EXE SHA-256 `f191b65826acf57b80819205a0b4337ff37a73e85de7cfe926aa5ce7d8e5df97` | PASS |
| Clean extraction and package integrity | Job #446 extracted the exact job #438 ZIP; validated safe/unique paths, manifest, SHA256SUMS, declared file set, provenance, executable hash, and unchanged archive hash. Packaged executable remained alive for the three-second CI launch smoke. | PASS (non-interactive package smoke) |
| C#/Python and integration regression | Pipeline #53 passed all 11 jobs; GitLab test summary showed 634 tests; job #441 reported 41/41 C# tests, 23/23 Windows Management IPC tests and deterministic cross-process status smoke (one 72 ms sample). Existing Linux/Windows Python, Agent build, smoke and Agent package jobs also passed. | PASS for executed CI suites; no live trading |
| Packaged interactive pages, themes, tray, preferences, clean removal/upgrade, and installed-Service IPC | Shared runner has no installed Agent Service; CI launch is non-interactive. These scenarios were not executed against the packaged artifact. Phase 5 screenshots are historical WPF evidence, not proof for this ZIP. | PENDING |
| Settings persistence and offline behavior | Same-build C# tests in job #441 cover preference persistence, invalid preference fallback, expected offline pipe state, Dashboard unavailable data and responsiveness. No interactive walkthrough used the extracted package. | PASS for automated logic; package-level interactive behavior PENDING |
| Windows 10 interactive screenshots and tray behavior | No authorized interactive Windows desktop control was available for this Phase 6 run. | PENDING |
| Windows 11 / Server OS validation | Not requested in this phase | `DEFERRED — PRODUCT OWNER VALIDATION` |
| Production code signing | No authorized signer found in runner inspection | BLOCKED for commercial publication |

Retained machine-readable build and validation reports are GitLab artifacts
from jobs #438 and #446. The verification job passed only after its report
returned `status=PASS`; its launch smoke is process-liveness evidence, not
visual UI validation. Pipeline #52's verification wrapper incorrectly checked
stale PowerShell `$LASTEXITCODE` after a `.ps1` call; the wrapper now verifies
the structured report status, and pipeline #53 passed on the corrected commit.
See the checked-in [pipeline evidence record](../evidence/v0.1.4/phase6/pipeline-53.md)
and [Release Checklist](RELEASE_CHECKLIST.md).
