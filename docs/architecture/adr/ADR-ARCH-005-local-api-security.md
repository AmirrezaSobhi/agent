# ADR-ARCH-005: Local Management API Security

- **Status:** Accepted security boundary; limited read-only Named Pipe is
  implemented and spike-verified. Production provisioning and full multi-user
  validation remain open.
- **Date:** 2026-10-08

## Context

The UI needs status/config/diagnostics and limited authorized management. The
current HTTP `/command` composition defaults to allow-all authentication and
authorization. The existing Named Pipe is the Agent-to-Worker boundary.

## Decision

Require a separate, versioned, authenticated, authorized, least-privilege,
bounded, correlated and audited local interface. Do not extend permissive
development auth to privileged UI actions or expose the Worker pipe to UI.
Use a separate Windows Named Pipe management endpoint. Do not reuse `/command`
HTTP or the internal Worker pipe. The limited v1 exposes status and protocol
negotiation only. Service start when stopped uses SCM/UAC permissions, not the
Service API. Detailed implementation and test evidence are in ADR-ARCH-017 and
the IPC contract.

## Alternatives considered

- Reuse `/command` — rejected because of permissive defaults and command scope.
- Let UI access Worker pipe — rejected because it bypasses Core authorization.
- HTTP Loopback — not selected because it needs an additional caller identity,
  Origin/CSRF and local-process defense surface; revisit only for a real
  cross-platform or remote requirement.
- Separate Named Pipe — selected for native DACL and caller token identity;
  the isolated Windows spike verified SID/ACL and Session 0/1 primitives.

## Consequences

Privileged mutations remain gated. The current allowlist authorizes only
read-only status; production Service identity, managed SID provisioning and
multi-user/session negative tests remain release gates.

## Risks

Local processes can attack a loopback port; an elevated helper can become a
privilege-escalation broker if too broad.

## Verification strategy

Negative tests across Windows users/sessions, replay/concurrency/oversize tests,
audit review, CSRF/Origin tests if HTTP, and stopped-service UAC tests.

## Related documents

[Local API](../LOCAL_API.md) · [IPC Contract](../IPC_CONTRACT.md) ·
[Security](../SECURITY_MODEL.md) · [ADR-ARCH-017](ADR-ARCH-017-management-ipc.md)
