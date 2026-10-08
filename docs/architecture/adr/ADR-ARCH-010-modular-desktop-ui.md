# ADR-ARCH-010: Modular Desktop Management Console

- **Status:** Proposed; product direction accepted, technology open
- **Date:** 2026-10-08

## Context

Product planning confirms an independent Windows management UI and proposed
modules. No framework, tray or UI package is implemented. KivyMD is conditional
on compatibility, accessibility and packaging.

## Decision

Use a modular shell with Dashboard, Runtime, Accounts, Security, Settings,
Logs, Diagnostics, Updates, Support and About. Default English with i18n
foundation for future Persian/RTL; dark/light-ready tokens; progressive
disclosure. Role controls actions; experience only controls presentation.
Keep UI separate from Service and Worker lifecycle.

## Alternatives considered

- Embed management UI in Service process — rejected due lifecycle/session coupling.
- Finalize KivyMD immediately — deferred pending Windows compatibility and
  accessibility evidence.
- Expose all future modules as operational — rejected as misleading.

## Consequences

Framework choice and accessibility/package feasibility spike precede UI
implementation. Navigation can show unavailable modules as planned/disabled.

## Risks

Framework tray behavior, screen-reader, DPI scaling and Windows packaging may
not meet requirements; RTL correctness can be superficial without full tests.

## Verification strategy

Prototype framework/tray and installer artifact; test keyboard/screen reader,
scaling, colors, service-offline startup, i18n and UI crash isolation.

## Related documents

[Desktop UI](../DESKTOP_UI.md) · [Acceptance](../ACCEPTANCE_V0.1.4.md) ·
[Roadmap](../ROADMAP.md)
