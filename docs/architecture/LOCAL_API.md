# Local Management Interface

**Status:** Proposed Windows Named Pipe management channel, separate from the
existing Agent-to-Worker pipe. Not implemented in this documentation mission.
The privileged management operation set remains gated by the detailed
[IPC contract](IPC_CONTRACT.md).

## Security baseline

The current Python HTTP `/command` path is not the Desktop Client API.
`agent/application/boundary.py` supplies `AllowAllAuthenticator` and
`AllowAllAuthorizer` when none are injected; the HTTP adapter uses
`ThreadingHTTPServer`; host defaults to loopback but is environment-configured.
Loopback does not establish caller SID or operation permission. Do not expose
this composition for privileged management or route WPF requests through it.

The existing `\\.\pipe\MT5Agent.Runtime.v1` is the Agent-to-interactive-Worker
MT5 runtime boundary. WPF must never connect to it. The proposed Desktop
management endpoint is `\\.\pipe\MT5Agent.Management.v1`, hosted by the Agent
Service with its own protocol, DACL, caller identity validation, and
authorization layer.

## Preferred transport and identity model

Recommend Windows Named Pipes over HTTP Loopback for this Windows-only local
desktop client. A pipe DACL can constrain client SIDs without a TCP listener or
browser CSRF/Origin/token bootstrap surface. The server must also derive and
verify client SID from the OS token, then authorize each operation; pipe access
alone is not sufficient. The exact service account and local reader/manager
group provisioning must be validated against the existing installation model.

HTTP Loopback is not selected. It remains a future alternative only if an
approved non-Windows client or remote management need appears, with explicit
authentication, CSRF/Origin checks, local-process protections, bounded work,
and a dedicated route. The present `/command` implementation is not reused.

## Scope and operation permissions

Initial v0.1.4 contract operations are protocol negotiation, read-only status,
bounded diagnostics, paged log query, per-user preferences read/write, and
Runtime restart only if its permission gate passes. Machine/service config
writes are excluded from the first contract. Service start/stop uses Windows
SCM permissions and UAC, not this pipe. No trading endpoint exists; capability
reports `UNSUPPORTED`.

Resolve operation permission from server-derived caller SID, operation and
resource scope. Never trust a client-supplied username/SID. Fail closed if
caller identity, version, or authorization cannot be established. Logs and
diagnostics return allowlisted sanitized fields only.

## Protocol and reliability

See [IPC_CONTRACT.md](IPC_CONTRACT.md) for proposed v1 request/response JSON,
correlation IDs, 64 KiB frame limit, 4 active/16 queued request bounds, timeout,
cancellation, retry, stale status, freshness, error taxonomy, reconnection and
contract tests. Use error codes stable across C# and Python; never send raw
exceptions, credentials, rejected secret values or MT5 Worker protocol data.

## Independent Service recovery

A stopped Service cannot answer its own API. Option A uses the documented
Windows Service Control Manager/UAC path for operators already authorized by
the machine. Do not create a custom elevated helper, create Windows accounts,
or configure Autologon in v0.1.4. If SCM denies the operation, WPF remains
available and gives clear permission/recovery guidance without collecting
administrator credentials. Service restart, Runtime Worker restart, MT5
terminal restart and UI restart are separate actions.

## Implementation release gates

Before exposing Runtime restart or other privileged operations, approve the SID
to operation matrix, server principal, DACL and impersonation/revert behavior,
per-user isolation, audit schema, bounded admission and negative tests across
Windows sessions. Read-only status still requires confidentiality review.

## Related documents

[Security Model](SECURITY_MODEL.md) · [Windows Runtime](WINDOWS_RUNTIME.md) ·
[WPF Solution](WPF_SOLUTION.md) · [ADR-ARCH-017](adr/ADR-ARCH-017-management-ipc.md)
