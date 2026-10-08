# Local Management Interface

**Status:** Implemented read-only Windows Named Pipe v1 for the two allowlisted
operations documented in the [IPC contract](IPC_CONTRACT.md). Privileged
controls, diagnostics, logs, preferences, and Runtime restart remain absent.

## Security baseline

The current Python HTTP `/command` path is not the Desktop Client API.
`agent/application/boundary.py` supplies `AllowAllAuthenticator` and
`AllowAllAuthorizer` when none are injected; the HTTP adapter uses
`ThreadingHTTPServer`; host defaults to loopback but is environment-configured.
Loopback does not establish caller SID or operation permission. Do not expose
this composition for privileged management or route WPF requests through it.

The existing `\\.\pipe\MT5Agent.Runtime.v1` remains the Agent-to-interactive-
Worker MT5 runtime boundary. WPF never connects to it. The implemented Desktop
management endpoint is `\\.\pipe\MT5Agent.Management.v1`, hosted alongside
the existing HTTP host in the Agent lifecycle, with a separate protocol,
DACL, caller-token SID validation, and allowlist authorization.

## Preferred transport and identity model

Use Windows Named Pipes for this Windows-only local desktop client. A pipe
DACL constrains callers without a TCP listener. The server derives the SID
from the client thread token and also checks an explicit per-process-operation
allowlist; pipe access alone is not sufficient. Set the service process
environment variable `MT5_AGENT_MANAGEMENT_ALLOWED_SIDS` to a comma-separated
list of user SIDs and restart Agent. An empty list disables the pipe. Production
service-account/group provisioning is still an operational deployment gap.

HTTP Loopback is not selected. It remains a future alternative only if an
approved non-Windows client or remote management need appears, with explicit
authentication, CSRF/Origin checks, local-process protections, bounded work,
and a dedicated route. The present `/command` implementation is not reused.

## Scope and operation permissions

Implemented operations are `protocol.negotiate` and read-only `status.get`.
The only authorization class today is the configured SID allowlist; there are
no role distinctions because no mutating operation exists. Service start/stop
uses Windows SCM permissions and UAC, not this pipe. Diagnostics, paged log
query, preferences, Runtime restart, and trading endpoint are absent.

Resolve operation permission from server-derived caller SID, operation and
resource scope. Never trust a client-supplied username/SID. Fail closed if
caller identity, version, or authorization cannot be established. Logs and
diagnostics return allowlisted sanitized fields only.

## Protocol and reliability

See [IPC_CONTRACT.md](IPC_CONTRACT.md) for the implemented v1 JSON framing,
correlation IDs, 64 KiB frame limit, single-instance serialized service,
two-second client/server bounds, cancellation, retry, stale status, error
taxonomy and remaining tests. Error responses are sanitized; raw exceptions,
credentials, rejected secret values and MT5 Worker protocol data are not sent.
Requests that the Windows DACL denies never reach Agent-level audit logging;
system-level denied-access auditing is not configured by this change.

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
