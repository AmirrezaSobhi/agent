# ADR-ARCH-001: Independent Desktop UI and Agent Service

- **Status:** Accepted product direction (implementation remains future work)
- **Date:** 2026-10-08

## Context

The v0.1.4 planning record confirms that the Agent must operate without an open
UI; closing or crashing the UI must not stop Agent Core or the Worker. The
current repository has no Desktop UI or productized Service installer.

## Decision

Treat Desktop UI, Windows Agent Service/Core, and interactive Runtime Worker as
independently managed components. The UI is a management/observation client,
not runtime owner. A service-offline UI still opens and offers diagnostics.
UI status must not be used as a proxy for service/runtime state.

## Alternatives considered

- UI process owns Agent and Worker lifecycle — rejected because closing UI
  would stop execution and couple desktop state to service availability.
- UI directly operates MT5 — rejected because it bypasses the service policy
  boundary and fails when the desktop session closes.

## Consequences

Needs a separate local management contract, service lifecycle and OS-mediated
recovery path. UI crash/exit tests are release acceptance requirements.

## Risks

Two independently supervised processes can race unless desired state and
restart ownership are explicit. A stopped Service cannot answer its own API.

## Verification strategy

Windows integration tests close/crash UI while asserting Service and Worker
health; launch UI with Service stopped; verify status and recovery behavior.

## Related documents

[Blueprint](../BLUEPRINT.md) · [Desktop UI](../DESKTOP_UI.md) ·
[Windows Runtime](../WINDOWS_RUNTIME.md) · [Acceptance](../ACCEPTANCE_V0.1.4.md)
