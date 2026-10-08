# ADR-ARCH-017: Dedicated WPF-to-Agent Management Named Pipe

- **Status:** Accepted for the read-only v1 implementation slice; production
  Service provisioning and multi-session authorization remain open
- **Decision date:** 2026-10-08

## Context

The Python Agent's current `/command` path composes
`AllowAllAuthenticator` and `AllowAllAuthorizer` by default. The existing
`MT5Agent.Runtime.v1` Named Pipe is the distinct Agent-to-interactive-Worker
MT5 boundary. WPF requires an authorized local status channel that does not
reuse either boundary.

## Decision

Use the dedicated Windows Named Pipe `\\.\pipe\MT5Agent.Management.v1` from
C# WPF to the Python Agent host. Use one bounded UTF-8 JSON message per pipe
message, a 65,536-byte bound, server-derived caller SID from the actual pipe
client token `TokenUser`, an explicit DACL and operation authorization. Fail
closed on identity, impersonation restoration, authorization, framing or
protocol-version failure. Do not trust caller-provided SID/PID/username/session
claims. Do not use `/command` or expose the internal Worker pipe to WPF.

The DACL allows the Agent process token SID and only user SIDs configured with
`MT5_AGENT_MANAGEMENT_ALLOWED_SIDS`; an empty list disables the endpoint. The
only implemented operations are read-only `protocol.negotiate` and
`status.get`. Status reports the existing Agent health projection, Central
`NOT_CONFIGURED`, Trading capability `UNSUPPORTED`, and authorization
`NOT_AUTHORIZED`. It never performs order execution. The client uses async
Named Pipe I/O, two-second timeout/cancellation, correlation IDs, bounded
reconnect attempts and typed status mapping. Dashboard polling is every five
seconds; data older than 15 seconds is labeled stale. One pipe instance is
served at a time; there is no application queue.

Service start/stop remains outside the pipe and governed by Windows SCM ACL and
UAC. Diagnostics, logs, preferences, Runtime restart, and trading operations
are not implemented. Production service identity/group provisioning is not
resolved by this decision; current SID list configuration is a manual machine
administration step.

## Alternatives considered

- Existing HTTP Loopback `/command` — rejected because authentication and
  authorization default to allow-all and loopback does not identify the Windows
  caller SID.
- New authenticated HTTP endpoint — deferred unless an approved remote or
  cross-platform need appears; it adds token, CSRF/Origin and local-process
  controls that are unnecessary for the Windows desktop client.
- Reuse the internal Worker pipe — rejected because it bypasses Agent
  management authorization and couples the UI to the MT5 process boundary.
- Dedicated Named Pipe — selected for native Windows DACL and OS-token identity
  at the local client/service boundary.

## Consequences

Adds an independent Python ingress adapter and a C# IPC client. The Python
Agent and interactive Worker remain operational foundations. Existing Worker
protocol and `/command` implementation are unchanged. Management remains
read-only until separate authorization decisions and tests permit more.

## Risks

The isolated security spike used a LocalSystem test service, not every
production Agent service principal. Local SID provisioning is manual. A
multi-user/session authorization matrix, auditable configuration lifecycle,
GitLab job evidence and supported OS matrix remain release gates. An authorized
compromised UI can still read the status available to its SID.

## Verification strategy

The Windows security spike verified actual caller `TokenUser` SID, DACL
allow/deny, impersonation restoration and fail-closed paths, forged-claim
rejection, and Session 0 service to interactive Session 1. Python Management
IPC tests (15) and C# tests (included in 27) cover framing, authorization,
version/error handling, cancellation, reconnect and synthetic status. A
cross-language synthetic status smoke also passed. Production Service
qualification, multi-user/multi-session testing, interactive UI automation and
the GitLab pipeline job remain open. No real orders were sent. Confirm the WPF
client opens only `MT5Agent.Management.v1` and the allow-all `/command` path
remains unused for UI management.

## Related documents

[IPC Contract](../IPC_CONTRACT.md) · [Local API](../LOCAL_API.md) ·
[Security](../SECURITY_MODEL.md) · [WPF Solution](../WPF_SOLUTION.md) ·
[Acceptance](../ACCEPTANCE_V0.1.4.md)
