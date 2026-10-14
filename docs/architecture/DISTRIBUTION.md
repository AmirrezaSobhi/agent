# Windows Desktop Distribution — v0.1.4

**Status:** COMPLETE — INTERNAL DEVELOPMENT MILESTONE. Windows 10 CI evidence
below covers the exact executable/package artifact. Interactive package
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

Product Owner fast-track scope accepts the verified CI package for internal
development closure. No interactive package session was available for this
closure, so visual package validation remains deferred. This acceptance does
not change commercial release gates.

| Gate | Evidence | Result |
|---|---|---|
| Branch baseline | Accepted Phase 5 SHA `12826f42989cda7cee3e3847632cbf39bf1a21dc`; Phase 6 branch created directly from it | PASS |
| Windows 10 Release build | Pipeline [#54](http://gitlab.local/root/agent/-/pipelines/54), executable/package source commit `567c6810292c92ec4b00d8b9ae01e458fcabb88c`; build job [#449](http://gitlab.local/root/agent/-/jobs/449), Windows 10 x64 runner; official .NET Framework 4.8 build prerequisites | PASS |
| Build Once → Test Same Artifact | Job #449 built Release x64 once; tests consumed the build outputs and package verifier [#457](http://gitlab.local/root/agent/-/jobs/457) consumed the same ZIP without rebuilding | PASS |
| Package SHA-256 and provenance | `MT5Agent-Desktop-v0.1.4-windows-x64.zip`; SHA-256 `ad32e673cc7a3f18f4eb64e25cbfb4f64fe438e103d9c139aed4c21b1bc5ac63`; source `567c6810292c92ec4b00d8b9ae01e458fcabb88c`; pipeline 54; build job 449 | PASS |
| Clean extraction and package integrity | Job #457 extracted the exact job #449 ZIP, validated manifest/checksums/provenance and unchanged artifact hash, then completed a bounded non-interactive executable launch smoke | PASS for package integrity and process smoke; not visual UI evidence |
| C#/Python and integration regression | Pipeline #54 passed all 11 jobs; C# tests 41 passed, Python tests passed, IPC tests passed, and deterministic cross-process smoke passed. Existing Agent build/runtime smoke and package gates also passed. | PASS for executed CI suites; no live trades |
| Settings and offline behavior | Existing automated tests cover user preference persistence, safe fallback, offline state and UI responsiveness. Package-specific replacement/rollback/removal was not rehearsed. | PASS for automated logic; package replacement/removal DEFERRED |
| Packaged interactive pages, themes, tray, and installed-Service IPC | No interactive desktop or installed product Service was used for this fast-track closure. | DEFERRED |
| Windows 10 package interactive launch | Optional focused interactive smoke was not immediately available in this environment. | DEFERRED; does not block internal milestone |
| Windows 11 / Server OS validation | Not requested in this phase | `DEFERRED — PRODUCT OWNER VALIDATION` |
| Production code signing | Package is unsigned; no authorized production signer is configured | `UNSIGNED — ACCEPTED FOR INTERNAL DEVELOPMENT`; `CODE SIGNING REQUIRED — RELEASE BLOCKED` for public/commercial release |

Retained machine-readable build and validation reports are GitLab artifacts
from jobs #449 and #457. The package smoke proves extraction, integrity, and
process liveness only; it is not visual UI validation. See the [Release
Checklist](RELEASE_CHECKLIST.md). Pipeline #54 covers the executable and CI
configuration at commit `567c681`; this documentation-only closure does not
change that artifact or its test applicability.

## Develop integration evidence

Phase 6 was fast-forward integrated into `develop` at
`ad497956dbd2c6700830da5d1a067f3b7074bd2e`, preserving the 26 source-branch
commits and the pre-existing `develop` history. Pipeline [#55](http://gitlab.local/root/agent/-/pipelines/55)
passed 11/11 jobs on that commit. Build job #460 produced
`MT5Agent-Desktop-v0.1.4-windows-x64.zip` (55,226 bytes), SHA-256
`3187027cd997348c293d0a4b7940c5902f4444dd68fc3d995bde2bfc81cad656`, with
packaged EXE SHA-256
`b845a8ab1c06639468cad29e93800281eedb6b6a1d10f3e9dc81b23537706082`;
verifier job #468 consumed that build artifact and passed. The archive differs
from Phase 6 Pipeline #54 because provenance embeds the source commit and
pipeline. See also [Implementation Baseline](IMPLEMENTATION_BASELINE.md).
