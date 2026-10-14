# ADR-ARCH-015: C# WPF Desktop Client Technology

- **Status:** Accepted by Product Owner
- **Decision date:** 2026-10-08

## Context

MT5Agent's operational Agent Core and MT5 Runtime Worker are implemented in
Python. v0.1.4 needs a commercial Windows desktop management client without
rewriting that runtime. The former KivyMD proposal was conditional and is now
superseded.

## Decision

Implement the v0.1.4 Desktop Client in **C# using WPF, XAML, .NET Framework
4.8, and MVVM**. Use a hybrid C# UI + Python Agent/Worker architecture. C# is a
management client and must communicate with the Python Agent only over the new
secure management IPC boundary. Python Agent and Worker remain the existing
operational foundation. Do not create a Python-based desktop GUI.

Commercial UI OS support is limited to Windows 10 x64, Windows 11 x64, Windows
Server 2022 x64, and Windows Server 2025 x64. Server installs require Desktop
Experience; Server Core is unsupported. Other Windows versions are out of
scope. Windows 10 lifecycle/security exposure is a separate, disclosed risk;
the matrix is not silently narrowed by this ADR.

For UI libraries, prefer stock WPF controls with project-owned XAML
ResourceDictionaries and tokens. Do not add a broad UI library initially.
MahApps.Metro is a contingency only if a prototype shows material benefit and
a stable net48-compatible release passes dependency/license/packaging review.
Do not use Kivy/KivyMD, FluentWPF, or a prerelease dependency in the first UI
build.

## Alternatives considered

- Kivy/KivyMD and Python desktop UI — superseded; does not match the approved
  C#/.NET desktop technology.
- Rewrite Agent/Worker in C# — rejected; preserve Python runtime and reduce
  runtime regression risk.
- MahApps.Metro or FluentWPF as a mandatory shell framework — not selected;
  standard WPF plus custom design system minimizes package and supply-chain
  dependencies. Compatibility evidence is documented in `WPF_SOLUTION.md`.
- WinUI or modern .NET WPF — not selected for this release because Product
  Owner has fixed WPF on .NET Framework 4.8.

## Consequences

Adds a C# WPF solution and a cross-language management contract. Requires a
Windows Build Tools/.NET Framework targeting-pack lane, x64 package validation,
MVVM tests and interactive UI Automation runner. It does not add Service
provisioning or replace Python CI/runtime tests.

## Risks

.NET Framework 4.8 is Windows-bound and follows the lifecycle of its OS.
Windows 10 22H2 is past general support. WPF compatibility at the framework
level does not prove application compatibility, Server GUI availability,
accessibility, DPI or packaging. Maintain a support lifecycle review.

## Verification strategy

Reproducible x64 build; package launch and WPF UIA tests on all four approved
targets; Server Desktop Experience check; .NET runtime release-key capture;
accessibility, scaling, startup/performance and application regression gates.

## Related documents

[WPF Solution](../WPF_SOLUTION.md) · [Desktop UI](../DESKTOP_UI.md) ·
[Quality Gates](../QUALITY_GATES.md) · [Implementation Plan](../IMPLEMENTATION_PLAN.md) ·
[superseded ADR-ARCH-010](ADR-ARCH-010-modular-desktop-ui.md)
