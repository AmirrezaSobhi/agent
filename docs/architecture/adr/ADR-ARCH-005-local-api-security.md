# ADR-ARCH-005: Local Management API Security

- **Status:** Open (security properties proposed; transport unselected)
- **Date:** 2026-10-08

## Context

The UI needs status/config/diagnostics and limited authorized management. The
current HTTP `/command` composition defaults to allow-all authentication and
authorization. The existing Named Pipe is the Agent-to-Worker boundary.

## Decision

Require a separate, versioned, authenticated, authorized, least-privilege,
bounded, correlated and audited local interface. Do not extend permissive
development auth to privileged UI actions or expose the Worker pipe to UI.
Choose HTTP Loopback versus Windows-native IPC only after threat and
compatibility review. Service start when stopped uses SCM/UAC permissions,
not the Service's API.

## Alternatives considered

- Reuse `/command` — rejected because of permissive defaults and command scope.
- Let UI access Worker pipe — rejected because it bypasses Core authorization.
- HTTP Loopback — viable candidate; still needs identity, origin/CSRF and
  process-level threat controls.
- Native IPC — viable candidate; needs ACL/session compatibility validation.

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

[Local API](../LOCAL_API.md) · [Security](../SECURITY_MODEL.md) ·
[Desktop UI](../DESKTOP_UI.md)
