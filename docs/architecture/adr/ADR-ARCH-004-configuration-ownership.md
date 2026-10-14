# ADR-ARCH-004: Configuration Ownership and Precedence

- **Status:** Accepted for ownership separation; storage/migration/precedence implementation remains Proposed
- **Date:** 2026-10-08

## Context

Current runtime registry and environment settings are partial; future UI
preferences, machine configuration and central policy have different owners
and security implications.

## Decision

Separate machine configuration, per-Windows-user preferences and future
central policy. Give each value one authoritative owner, schema version,
revision and validation rule. Mandatory local safety may restrict policy;
ordinary user preferences cannot override security/trading controls. Store
secrets separately under the consuming identity.

## Alternatives considered

- One shared config file — rejected because ownership and ACLs become ambiguous.
- Merge all values by last-write-wins — rejected because stale UI preference
  writes could override policy.
- Store secrets as encrypted text in user settings — rejected until identity,
  rotation and recovery are proven.

## Consequences

Needs migrations, atomic revisioned writes, access-control tests and an offline
policy. Existing config remains unchanged until implementation is approved.

## Risks

Incorrect consumer identity can make secret protection unusable or expose
values to another user; central/user conflict handling is unresolved.

## Verification strategy

Cross-user ACL tests, revision-conflict/migration tests, secret canary scans,
failure rollback and offline expiry tests.

## Related documents

[Configuration](../CONFIGURATION.md) · [Security](../SECURITY_MODEL.md) ·
[Acceptance](../ACCEPTANCE_V0.1.4.md)
