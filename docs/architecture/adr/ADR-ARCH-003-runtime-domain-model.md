# ADR-ARCH-003: Runtime and Account Domain Model

- **Status:** Accepted product/domain constraints; persistence and execution implementation proposed/deferred
- **Date:** 2026-10-08

## Context

v0.1.4 supports one active Runtime, while the product vision includes multiple
Devices, Agents, terminal installations and Trading Accounts. An account may
be visible from multiple Agents without granting simultaneous write authority.

## Decision

Keep Tenant, User/Role/Permission, Device, Agent Instance, Terminal
Installation, Runtime Instance, Runtime Principal, Trading Account, Policy,
Execution Lease, Trading Command/Result and Usage Record as distinct concepts.
These are required domain boundaries; this ADR does not approve a storage
schema or authorize multi-runtime execution in v0.1.4.
Keep one active runtime today, but avoid a global-singleton model that blocks
future explicit selection. Future multi-Agent writes require lease, fencing
epoch, idempotency and broker reconciliation.

## Alternatives considered

- Account equals terminal/runtime — rejected; one terminal can change account
  and account visibility is not runtime identity.
- Allow concurrent Agent writers and deduplicate later — rejected as unsafe.
- Implement full multi-runtime orchestration in v0.1.4 — deferred for scope.

## Consequences

Requires future persistence and registry design; no lease implementation is
authorized by this proposal. Support discovery, manual selection, explicit
confirmation and later web-console management.

## Risks

Stale leases, partitions and broker visibility gaps may cause split-brain or
duplicate execution if not resolved before failover.

## Verification strategy

Review entity ownership/lifecycle; test one-writer fencing, duplicate
suppression, partition handling and reconciliation before multi-Agent release.

## Related documents

[Domain model](../DOMAIN_MODEL.md) · [Trading safety](../TRADING_SAFETY.md) ·
[Roadmap](../ROADMAP.md)
