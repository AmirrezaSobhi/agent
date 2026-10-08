# Windows Compatibility Matrix

**Product support matrix:** Windows 10 x64, Windows 11 x64, Windows Server 2022
x64 with Desktop Experience, and Windows Server 2025 x64 with Desktop
Experience. Server Core is unsupported because the WPF client needs an
interactive desktop.

**Phase 5 test scope:** Windows 10 x64 only, by explicit Product Owner
instruction. Do not provision or test the other three systems during Phase 5;
their status is exactly `DEFERRED — PRODUCT OWNER VALIDATION` and is not a
Phase 5 blocker. A deferred row is not a compatibility pass.

| Operating system | Desktop requirement | Phase 5 result |
|---|---|---|
| Windows 10 x64 | Interactive desktop | **PASS for the executed Phase 5 closure cases; other listed gates remain pending.** Windows 10 Pro build 19045 x64; official .NET Framework 4.8 targeting pack, clean x64 rebuild, 41 C# tests, 318 Windows Python tests (2 gated skips run separately and passed), interactive WPF/UIA at 96 DPI, offline/live Management status, reversible SCM Agent integration, authorized read-only Pipe calls, and Users-only unauthorized DACL rejection (`ERROR_ACCESS_DENIED` at `CreateFile`). Final closure pipeline evidence is recorded in the evidence bundle after execution. Product Service packaging, tray Exit manual invocation, RDP/multi-session, higher DPI, and long soak remain pending. |
| Windows 11 x64 | Interactive desktop | `DEFERRED — PRODUCT OWNER VALIDATION` |
| Windows Server 2022 x64 | Desktop Experience only; Server Core unsupported | `DEFERRED — PRODUCT OWNER VALIDATION` |
| Windows Server 2025 x64 | Desktop Experience only; Server Core unsupported | `DEFERRED — PRODUCT OWNER VALIDATION` |

Windows 7 is legacy Runtime testing only, not a commercial Desktop Client
target. Windows 8/8.1, Windows Server 2012/2012 R2/2016/2019, Server Core,
and all other Windows versions are outside the approved matrix.

## Windows 10 test environment

| Host | Evidence |
|---|---|
| `window10-test` (`win10-runner`) | Windows 10 Pro x64, version 22H2, build 19045.6466; 64-bit; active local console user `Administrator`, Session 1 for interactive UI tests. Session 0 was used for the LocalSystem Worker ACL experiment. No MT5Agent Agent Service and no active MT5 terminal/runtime were present. |
| Framework/build | .NET Framework `4.8.09037`, release key `533325`; official v4.8 targeting assemblies present; MSBuild `4.8.9037.0`. `FrameworkPathOverride` was not used. |
| Display | 1280×800; actual WPF window DPI 96 (100% scale). No shared display settings were changed. 125%, 150%, and 200% scaling were not tested. |
| Regression | Windows Python `318 passed, 2 skipped`; both dedicated ACL cases were then executed separately in Session 0 and passed. WPF/C# `41 passed, 0 failed`; Linux portable suite `276 passed, 36 skipped`. |
| Interactive evidence | Navigation, Dashboard, Runtime, Settings, Logs, Diagnostics, About, both themes, keyboard focus, resize, minimize/restore and close-to-tray/restore were exercised. Screenshots and raw reports are in [`../evidence/v0.1.4/phase5/windows10-19045/`](../evidence/v0.1.4/phase5/windows10-19045/). The tray context Exit menu was not exposed to UI Automation in this run; Phase 4 had historical Exit evidence, but Phase 5 interactive Exit remains unverified. |
| Service/RDP | A temporary `MT5AgentPhase5Test` SCM harness (with explicit approval) hosted the real Python Agent Core in Session 0. The additional low-privilege DACL test used that same harness and was rolled back. The product does not have an installer/service wrapper. RDP disconnect/reconnect, logoff and reboot were not run because no RDP user session was active on the shared Runner. See [Windows Runtime](WINDOWS_RUNTIME.md) and [service evidence](../evidence/v0.1.4/phase5/windows10-19045/service-lifecycle.txt). |

The two available Windows 10 Runner machines are not interchangeable. The
second host, `win10-mt5-runner`, had active Python and MT5 terminal processes
in an interactive user session and was not touched. All Phase 5 interactive
screenshots and Windows tests came from the isolated `window10-test` host.

## Microsoft lifecycle is separate from compatibility

Windows 10 Home/Pro 22H2 general support ended 2025-10-14; edition/program-
specific ESU may apply. This is a lifecycle and servicing risk, not a statement
that technical compatibility failed or passed. Before commercial release, the
Product Owner must define supported Windows 10 editions/builds and any servicing
or ESU requirement. Lifecycle dates for Windows 11 and Server releases must be
rechecked when Product Owner validation and release planning occur.

Sources checked 2026-10-08: [Windows 10 lifecycle](https://learn.microsoft.com/en-us/lifecycle/products/windows-10-home-and-pro),
[Windows Server 2022 lifecycle](https://learn.microsoft.com/en-us/lifecycle/products/windows-server-2022),
[Windows Server 2025 lifecycle](https://learn.microsoft.com/en-us/lifecycle/products/windows-server-2025),
[Windows 11 lifecycle](https://learn.microsoft.com/en-us/lifecycle/products/windows-11-home-and-pro),
[Windows Server installation options](https://learn.microsoft.com/en-us/windows-server/get-started/install-options-server-core-desktop-experience).

## Phase 5 evidence requirements and boundaries

The Windows 10 result is limited to the exact OS/build, .NET targeting pack,
source bundle, and tests recorded in the linked evidence directory. Compilation
alone does not establish runtime compatibility. No Windows 11 or Server test
was performed or requested. No commercial package, installer, signing, or
release artifact was produced. Windows 10 compatibility is not fully closed
until installed-Service/runtime lifecycle and remaining P0 security gates are
resolved; this does not turn the three deferred OS rows into Phase 5 blockers.

## Phase 6 package validation status

Codex test scope remains Windows 10 x64 only. Record the Phase 6 clean package
run, interactive launch and exact archive SHA in
[Distribution](DISTRIBUTION.md) after the final pipeline artifact is available.
Windows 11 x64, Windows Server 2022 Desktop Experience and Windows Server 2025
Desktop Experience remain exactly `DEFERRED — PRODUCT OWNER VALIDATION`; no
compatibility pass is inferred from the Windows 10 result. Their deferral does
not block Phase 6 implementation completion.
