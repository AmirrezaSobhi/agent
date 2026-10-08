# ADR-ARCH-014: Offline Authorization Behavior

- **Status:** Deferred for v0.1.4; safety requirements accepted, future command-class policy open
- **Date:** 2026-10-08

## Context

Agent/runtime may remain available during central disconnection. Continuing
some actions improves resilience, while stale authorization or risk policy can
permit unsafe execution. Existing-position protection and new trading have
different needs. In v0.1.4, central connectivity and trading capability are
not configured or available; no offline trading authorization is implied.

## Decision

For future authorized trading, require a command-class offline policy with
explicit policy freshness window, cached policy integrity, audit buffering
limits and recovery reconciliation.
No broad offline trading grant is made in this ADR. On policy expiry or missing
authorization, fail closed for new discretionary execution; continue only
explicitly permitted observation/reporting/protective actions. Exact set and
validity duration remain open for Product Owner/risk approval.

## Alternatives considered

- Deny all work offline — rejected as a default assumption because it may
  abandon protective monitoring.
- Permit all commands using last-known policy indefinitely — rejected as
  unsafe.
- Use wallet balance or cached token as offline permission — rejected because
  billing and authentication are separate.

## Consequences

Central release cannot finalize until policy expiry, clock-skew, revocation,
offline queue, and reconciliation behavior are approved and tested.

## Risks

Clock drift, prolonged partition, revoked identity or stale policy can make a
cached authorization invalid.

## Verification strategy

Inject central outage, policy expiry, clock skew, token revocation, disk full
and reconnect; verify command-class matrix, audit continuity and reconciliation.

## Related documents

[Trading safety](../TRADING_SAFETY.md) · [Configuration](../CONFIGURATION.md) ·
[Product vision](../PRODUCT_VISION.md) · [Risk register](../RISK_REGISTER.md)
