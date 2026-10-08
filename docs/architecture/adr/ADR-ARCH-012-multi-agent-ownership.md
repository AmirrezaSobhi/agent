# ADR-ARCH-012: Multi-Agent Single-Writer Ownership

- **Status:** Deferred; required before production multi-Agent execution
- **Date:** 2026-10-08

## Context

One Trading Account may be visible from several Agents in the future. Network
partitions and stale workers make concurrent command delivery unsafe.

## Decision

Do not implement production multi-Agent execution until there is an exclusive,
expiring account Execution Lease with a monotonically increasing fencing epoch.
Every mutation carries owner/epoch and idempotency key. Failover requires
broker-state reconciliation; heartbeat loss alone cannot transfer authority.

## Alternatives considered

- Allow active-active writers — rejected due duplicate/competing orders.
- Depend only on local mutex — rejected because it cannot coordinate devices.
- Lease without fencing — rejected because delayed former owner can still act.

## Consequences

Multi-runtime/fleet work is deferred. Account visibility and monitoring can be
multi-Agent before execution only if authorization remains read-only and clear.

## Risks

Central partition, clock skew, broker eventual consistency and stale commands
can invalidate naive lease assumptions.

## Verification strategy

Partition/failover simulation, stale epoch rejection, duplicate command tests,
lease expiry and broker reconciliation under ambiguous outcome.

## Related documents

[Domain](../DOMAIN_MODEL.md) · [Trading safety](../TRADING_SAFETY.md) ·
[Roadmap](../ROADMAP.md)
