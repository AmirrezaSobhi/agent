# ADR-ARCH-017: Dedicated WPF-to-Agent Management Named Pipe

- **Status:** Proposed technical recommendation; requires security proof before implementation
- **Decision date:** 2026-10-08

## Context

The Python Agent's current `/command` path composes
`AllowAllAuthenticator` and `AllowAllAuthorizer` by default. The existing
`MT5Agent.Runtime.v1` Named Pipe is a distinct Agent-to-interactive-Worker
boundary. A WPF client needs local status, diagnostics, preferences and a
narrow set of authorized Runtime management operations.

## Decision

Implement a **separate Windows Named Pipe** management channel, proposed name
`\\.\pipe\MT5Agent.Management.v1`, from the C# WPF client to the Python Agent
Service. Use one bounded UTF-8 JSON object per message-mode pipe message, OS
DACL restricted to explicitly provisioned local SID(s)/group, server-derived
caller SID from the actual pipe client token's `TokenUser`, and per-operation
application authorization. Fail closed on identity/auth/version failure. Do
not use `/command`, do not expose the internal Worker pipe to WPF, and do not
accept a caller-provided SID as identity. Existing Worker `peer()` maps a
configured exclusive principal and does not establish arbitrary UI caller
identity; it is not sufficient for this management authorization.

Use a contract v1 with request/correlation IDs, operation, deadline, payload;
response includes matching IDs, stable code, sanitized message, observed time
and data. Limit message to 64 KiB, management work to 4 accepted/16 queued,
serialize all Agent/MT5 work, return `BUSY` on overflow. Initial status polling
is every 5 s; stale status after 15 s. Exact proposed envelope and error/status
schema are in `IPC_CONTRACT.md`.

Service start/stop uses SCM ACL/UAC outside this pipe. Initial pipe operations
are status, protocol negotiation, allowlisted diagnostics, paged logs,
per-user UI preferences, and Runtime restart only after an explicit manage
permission. Trading capability is `UNSUPPORTED` in v0.1.4.

## Alternatives considered

- Existing HTTP Loopback `/command` — rejected: current authentication and
  authorization defaults allow all; loopback does not identify a Windows SID.
- New authenticated HTTP endpoint — viable future option only if a concrete
  cross-platform/remote need appears; adds token, CSRF/Origin and local-process
  controls that are unnecessary for this Windows desktop client.
- Reuse existing internal Worker pipe — rejected because UI would bypass Agent
  authorization and bind directly to the MT5 process boundary.
- Separate Named Pipe — preferred because Windows ACL and token identity are
  native to the client/service boundary; needs a tested Python SID/token path.

## Consequences

Adds a new Python ingress/security adapter and a C# client. Protocol fixtures
are language-neutral; C# and Python tests share vectors. Two pipes remain
purpose-separated. Existing Worker protocol and lifecycle must not regress.

## Risks

Pipe DACL may be overbroad; token impersonation may not work under actual
Service identity/session; an authorized but compromised UI can request
operations allowed to its SID; 4/16 limits may need adjustment from profiling.
The current Service principal and installation group provisioning must be
verified before DACL is finalized.

## Verification strategy

Windows integration tests validate exact DACL, actual caller SID/token,
impersonation revert, unauthorized operation denial, multiple user sessions,
message bounds, protocol mismatch, timeout/cancel, backpressure, audit and
sanitized output. Fake Worker/broker only; no real orders. Prove WPF never opens
`MT5Agent.Runtime.v1` and current `/command` remains excluded.

## Related documents

[IPC Contract](../IPC_CONTRACT.md) · [Local API](../LOCAL_API.md) ·
[Security](../SECURITY_MODEL.md) · [WPF Solution](../WPF_SOLUTION.md) ·
[Acceptance](../ACCEPTANCE_V0.1.4.md)
