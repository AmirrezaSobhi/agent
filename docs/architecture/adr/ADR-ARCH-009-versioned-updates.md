# ADR-ARCH-009: Versioned Releases and Safe Updates

- **Status:** Accepted artifact-integrity principle; full auto-update deferred
- **Date:** 2026-10-08

## Context

Repository CI packages a Windows artifact and carries it through tests; a
customer updater with staged install/rollback is not present. Trading runtime
and configuration schema make uncontrolled update timing hazardous.

## Decision

Preserve Build Once → Test Same Artifact → Release Same Artifact. Future updates
require signed manifests, integrity verification, channels, compatibility
checks, staged installation, policy-approved safe windows, health checks,
schema compatibility, rollback and audit. Severity and trading/account policy
govern deferral.

## Alternatives considered

- Download and execute latest installer directly — rejected without signature,
  compatibility and rollback controls.
- Rebuild independently for release after tests — rejected because tested
  provenance would be lost.

## Consequences

v0.1.4 does not require complete auto-update. Define and validate updater as a
later release; verify actual publisher TLS/token permissions before release.

## Risks

Power loss, incompatible config migration, signing-key compromise, and updates
during active trading can prevent recovery.

## Verification strategy

Provenance/hash equality, invalid signature rejection, staged failure/rollback,
schema downgrade, interrupted installation and safe-window tests.

## Related documents

[Operations](../OPERATIONS.md) · [Roadmap](../ROADMAP.md) ·
[Baseline](../IMPLEMENTATION_BASELINE.md)
