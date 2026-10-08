# ADR-ARCH-005: Local Management API Security

- **Status:** Proposed (separate SID-authorized Named Pipe recommended; exact OS identity/DACL still requires security verification)
- **Date:** 2026-10-08

## Context

The UI needs status/config/diagnostics and limited authorized management. The
current HTTP `/command` composition defaults to allow-all authentication and
authorization. The existing Named Pipe is the Agent-to-Worker boundary.

## Decision

Require a separate, versioned, authenticated, authorized, least-privilege,
bounded, correlated and audited local interface. Do not extend permissive
development auth to privileged UI actions or expose the Worker pipe to UI.
Prefer a separate Windows Named Pipe management endpoint after verification of
OS client SID/DACL behavior. Do not reuse either `/command` HTTP or the internal
Worker pipe. Service start when stopped uses SCM/UAC permissions, not the
Service's API. Detailed protocol proposal is ADR-ARCH-017.

## Alternatives considered

- Reuse `/command` — rejected because of permissive defaults and command scope.
- Let UI access Worker pipe — rejected because it bypasses Core authorization.
- HTTP Loopback — not selected because it needs an additional caller identity,
  Origin/CSRF and local-process defense surface; revisit only for a real
  cross-platform or remote requirement.
- Separate Named Pipe — preferred technical proposal; SID/ACL/token handling
  and cross-session behavior require proof before acceptance.

## Consequences

Privileged UI features are gated until transport, principal mapping, operation
matrix, request bounds and negative tests are approved.

## Risks

Local processes can attack a loopback port; an elevated helper can become a
privilege-escalation broker if too broad.

## Verification strategy

Negative tests across Windows users/sessions, replay/concurrency/oversize tests,
audit review, CSRF/Origin tests if HTTP, and stopped-service UAC tests.

## Related documents

[Local API](../LOCAL_API.md) · [IPC Contract](../IPC_CONTRACT.md) ·
[Security](../SECURITY_MODEL.md) · [ADR-ARCH-017](ADR-ARCH-017-management-ipc.md)
