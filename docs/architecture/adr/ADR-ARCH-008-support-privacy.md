# ADR-ARCH-008: Support Privacy and Diagnostic Bundles

- **Status:** Accepted privacy workflow requirements; collection/upload implementation remains Proposed
- **Date:** 2026-10-08

## Context

Diagnostics can expose machine, runtime and account details. Future support
must work across customer types and roles without silently transmitting data.

## Decision

Collect minimum necessary data, redact secrets, build a manifest, allow
customer preview, and require explicit consent before any future transmission.
Local bundle generation is distinct from central upload. Never include
passwords, access tokens, private keys or broker credentials. Remote support is
time-bound, narrow-scope, revocable and audited.

## Alternatives considered

- Upload automatically when an error occurs — rejected due privacy and consent.
- Collect full logs/config for convenience — rejected by data minimization.
- Treat bundle creation as consent to send — rejected; separate user actions.

## Consequences

Requires allowlisted collection, redaction tests, retention and partial-bundle
reporting before v0.1.4 export.

## Risks

Unknown fields may contain secrets; redaction can remove necessary evidence or
miss nested sensitive values.

## Verification strategy

Synthetic secret canaries in every source; inspect preview and archive; verify
cancel produces no transmission and consent is auditable.

## Related documents

[Operations](../OPERATIONS.md) · [Security](../SECURITY_MODEL.md) ·
[Acceptance](../ACCEPTANCE_V0.1.4.md)
