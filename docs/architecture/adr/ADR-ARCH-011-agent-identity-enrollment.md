# ADR-ARCH-011: Agent Identity and Central Enrollment

- **Status:** Deferred to v0.2.x; identity-separation requirements accepted, protocol open
- **Date:** 2026-10-08

## Context

Future multi-tenant operations need separate tenant, user, device, Agent,
account and runtime identities. Current repository has local Agent identity
contracts but no production tenant enrollment or credential lifecycle.

## Decision

Defer central enrollment implementation until an identity protocol defines
provisioning, device binding, key storage, rotation, revocation, token audience,
offline behavior and audit. Never reuse broker credentials, billing credits,
Windows account identity or user login as Agent identity.

## Alternatives considered

- Reuse one customer API key for all devices — rejected due revocation and
  least-privilege limitations.
- Treat Windows username as cloud Agent identity — rejected; users and
  installations have different lifecycles.
- Implement enrollment in v0.1.4 — deferred to keep release client-side.

## Consequences

No cloud connection is claimed for v0.1.4. Local mode must be explicit and not
pretend an Agent is centrally enrolled.

## Risks

Poor key lifecycle can allow device cloning, replay or long-lived unauthorized
access.

## Verification strategy

Protocol/security review; enrollment/revocation/rotation, cloned image,
offline expiry and tenant isolation tests before central release.

## Related documents

[Product vision](../PRODUCT_VISION.md) · [Domain model](../DOMAIN_MODEL.md) ·
[Security](../SECURITY_MODEL.md) · [Roadmap](../ROADMAP.md)
