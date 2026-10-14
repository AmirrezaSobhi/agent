# ADR-ARCH-006: Trading Policy Enforcement

- **Status:** Accepted safety requirements; policy evaluation algorithm remains Proposed
- **Date:** 2026-10-08

## Context

Central orchestration is intended to decide trades; Agent must still enforce
local mandatory constraints and current authorization. No production trading
commands exist in the audited baseline.

## Decision

Authorize by command class and scope. Evaluate authenticated issuer, expiry,
lease, policy revision, mandatory local safety, central risk, organization,
customer, role and account constraints. Applicable denials prevail. Exception
flows exist only where policy explicitly permits them. Treat unknown execution
outcome as unresolved; reconcile broker state before any retry. A stop-loss
change is not assumed risk-reducing.

## Alternatives considered

- Trust central commands without local enforcement — rejected by product
  safety requirement.
- One broad “trading enabled” permission — rejected because reads, new orders,
  modifications, close, account switching and runtime admin differ.
- Retry on timeout — rejected because operation may already have executed.

## Consequences

Requires policy provenance/revision and broker reconciliation before trading is
implemented. No real trades in v0.1.4 documentation/testing mission.

## Risks

Policy staleness, clock drift, partial broker state and ambiguous outcomes can
create unauthorized or duplicated actions.

## Verification strategy

Conflict matrix, role/account negative tests, stale policy/lease rejection,
fault injection after dispatch and broker reconciliation tests.

## Related documents

[Trading safety](../TRADING_SAFETY.md) · [Domain](../DOMAIN_MODEL.md) ·
[Security](../SECURITY_MODEL.md)
