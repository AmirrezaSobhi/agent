# Windows Desktop Distribution — v0.1.4

**Status:** Proposed distribution workflow; Windows 10 package evidence is
recorded below only after the matching CI artifact has been validated.

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
| Clean Windows 10 extraction, application launch, settings persistence, offline/authorized IPC, tray, and removal | Pending final Windows 10 run on the pipeline ZIP | PENDING |
| Build once / test same binary | Pending final pipeline/job evidence | PENDING |
| Package SHA-256 and provenance | Pending final pipeline artifact | PENDING |
| Windows 10 interactive screenshots | Pending final package launch | PENDING |
| Windows 11 / Server OS validation | Not requested in this phase | `DEFERRED — PRODUCT OWNER VALIDATION` |
| Production code signing | No authorized signer found in runner inspection | BLOCKED for commercial publication |

Final evidence should include pipeline URL, commit SHA, build and verification
job IDs, artifact SHA-256, Windows build/runtime, test identity/session, and
screenshots/report paths. See [Release Checklist](RELEASE_CHECKLIST.md).
