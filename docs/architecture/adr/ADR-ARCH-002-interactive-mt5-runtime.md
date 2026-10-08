# ADR-ARCH-002: Interactive MT5 Runtime Worker

- **Status:** Accepted; aligns with repository [ADR-001](../../ADR/ADR-001-unattended-mt5-runtime-hosting.md)
- **Date:** 2026-10-08

## Context

The supported Windows production path keeps the Agent/control plane in Session
0 and the GUI-dependent MT5 Python API in an interactive session. Repository
source and accepted v0.1.3 lab evidence document authenticated Named Pipe IPC.

## Decision

Keep MT5 API ownership in one interactive Runtime Worker under a configured
runtime principal. Session 0 Agent communicates through the bounded,
authenticated, allowlisted local IPC. Desktop UI uses a distinct local
management contract and never connects directly to Worker IPC.

## Alternatives considered

- Service directly uses MT5 GUI/API — rejected as unsupported session model.
- Desktop-interaction Service hack — rejected for security and lifecycle risk.
- Every UI session owns an independent terminal — rejected for duplicate
  ownership and runtime instability.

## Consequences

Worker and Service lifecycle/recovery need separate state and observability.
The existing lab Autologon/task sequence does not approve a general installer.

## Risks

Windows policy, RDP, logoff and credential handling affect session readiness.
Cold-boot success does not prove all profile behavior.

## Verification strategy

Maintain Session 0/nonzero-session identity, pipe authorization, safe-read and
no-broad-process-kill checks; test boot, disconnect, logoff, crash and restart
on each supported OS/profile.

## Related documents

[Runtime](../WINDOWS_RUNTIME.md) · [Security](../SECURITY_MODEL.md) ·
[Existing ADR-001](../../ADR/ADR-001-unattended-mt5-runtime-hosting.md)
