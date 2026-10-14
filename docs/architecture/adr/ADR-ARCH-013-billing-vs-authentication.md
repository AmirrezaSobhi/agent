# ADR-ARCH-013: Billing Credits Are Not Authentication

- **Status:** Accepted product constraint; commercial billing policy details remain Open
- **Date:** 2026-10-08

## Context

The planned business model primarily consumes usage-based credits. A balance
can change independently of user/device identity, authorization, or existing
market exposure.

## Decision

Keep wallet, usage record and pricing policy separate from authentication
tokens, identity and execution authorization. Credit exhaustion may deny new
discretionary operations only through explicit policy. It must not
automatically terminate availability, monitoring or permitted protective
management of existing positions.

## Alternatives considered

- Encode credit balance into token validity — rejected because billing state is
  not identity and would couple revocation/settlement to security.
- Stop every Agent operation at zero credit — rejected as unsafe for existing
  position monitoring/protection.
- Allow unlimited offline trading — rejected pending explicit risk policy.

## Consequences

Metering needs auditable, versioned transaction events and safe offline
behavior. Grace, debt settlement and protective command set remain open.

## Risks

Duplicate/lost usage records or unclear exhaustion policy may cause billing
disputes or unsafe command denial.

## Verification strategy

Ledger reconciliation, replay/duplicate event handling, credit exhaustion
matrix, offline buffering and position-protection policy tests.

## Related documents

[Product vision](../PRODUCT_VISION.md) · [Trading safety](../TRADING_SAFETY.md) ·
[Domain](../DOMAIN_MODEL.md)
