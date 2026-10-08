# Local Management IPC and Status Contract

**Status:** Proposed implementation contract for v0.1.4. It is a new,
purpose-built management channel. No source code or existing Worker pipe is
changed by this document.

## Recommendation: a separate Windows Named Pipe

Use a dedicated local named pipe, proposed name
`\\.\pipe\MT5Agent.Management.v1`, hosted by the existing Python Agent
service process. The C# WPF app is a client. Keep
`\\.\pipe\MT5Agent.Runtime.v1` exclusively for the internal Agent↔MT5 Worker
path; the UI never opens it.

Named Pipes are preferred over HTTP Loopback because this is Windows-only,
single-machine management with a desktop caller, and Windows ACLs can limit
connectivity to authorized local SIDs without introducing a listening TCP port,
browser Origin/CSRF or bearer-token bootstrap problem. Reuse framing/OS IPC
primitives where technically sound, but not the Worker endpoint, operations,
identity allowlist, or authorization scope. Preserve an application-layer
authorization check after the OS pipe ACL.

HTTP Loopback is not selected: the current Python `/command` composition binds
to loopback by default but defaults to `AllowAllAuthenticator` and
`AllowAllAuthorizer` (`agent/application/boundary.py` and
`agent/contracts/security.py`). The host is environment-configurable. Loopback
does not identify which local Windows user called it and does not protect
against another local process. If later required, HTTP needs a separately
reviewed authenticated design; it must not reuse `/command` as-is.

## Windows identity and authorization

1. **Server identity:** Agent Windows Service runs under a named, least-
   privilege service principal selected by the provisioned Agent installation.
   The UI does not impersonate this principal and never receives its secrets.
2. **Client identity:** caller is identified by the OS-authenticated pipe
   client token/SID, not a SID/string supplied in JSON. The pipe DACL allows
   only the installing user SID and/or an explicitly provisioned local group
   with manage/read roles; never `Everyone` or generic interactive users.
3. **Server verification:** on connection, Python must obtain the *actual
   connecting user's* token and `TokenUser` SID using a supported Named Pipe
   client-token API, map it to a local permission set, and always revert
   impersonation in `finally`. `GetNamedPipeClientProcessId` alone identifies
   a process, not its authorized user. The existing Worker pipe's `peer()`
   reports its configured exclusive principal; it does not prove arbitrary
   desktop callers' SIDs and must not be reused as that proof. Validate client
   process/session where policy requires it. Failure to obtain identity denies
   the request.
4. **Per-operation authorization:** read status/diagnostics can be granted to
   configured local operators; user preferences are scoped to client SID;
   machine config and Runtime restart require an explicit local manage role.
   Start/stop Agent Service is outside the pipe and subject to SCM ACL/UAC.
   Trading operations are absent and return `UNSUPPORTED_CAPABILITY`.
5. **Multiple sessions:** each Windows user has a distinct SID and preference
   store. The Service can accept clients from approved SIDs but returns only
   permitted projections; one user's layout or credentials never leak to
   another. Worker remains under its separate runtime principal/session.

The exact Windows service principal and group provisioning are technical
choices for Phase 2. They must be verified against the existing product
provisioning, not guessed from CI runner accounts. If existing install cannot
safely provision a group, start with a single configured user SID and
administrative manual provisioning.

## Protocol v1 proposal

Message-mode pipe, one UTF-8 JSON object per complete Windows pipe message,
with a maximum message size of 65,536 bytes inclusive of envelope. The Python
Worker IPC implementation already uses message-mode named pipes and enforces
a 65,536-byte message bound; reuse only these framing primitives if the new
management endpoint can maintain independent identity, ACL, authorization,
and lifecycle boundaries. Do not transmit bulk log files. The client must
set/read message mode and detect an incomplete message correctly. Protocol
version is negotiated with every connection; unknown major version fails
closed. Additive optional fields are allowed only within the same major
version. Cross-language framing and truncation behavior remain a Phase 2
contract-test gate.

Request envelope:

```json
{
  "protocol_version": 1,
  "request_id": "uuid",
  "correlation_id": "uuid",
  "operation": "status.get",
  "deadline_utc": "RFC3339 timestamp",
  "payload": {}
}
```

Response envelope:

```json
{
  "protocol_version": 1,
  "request_id": "same uuid",
  "correlation_id": "same uuid",
  "result": "ok | error",
  "code": "OK",
  "message": "sanitized user-facing summary",
  "observed_at_utc": "RFC3339 timestamp or null",
  "data": {}
}
```

Actor SID is derived by server and included in audit, never trusted from the
request. Do not include passwords, access tokens, broker secrets, command
payloads or full filesystem contents. Responses include per-status source,
freshness and capability values. Correlation IDs join UI request, Python
service log and diagnostics without carrying identity secrets.

### Initial allowed operations

`protocol.negotiate`, `status.get`, `diagnostics.collect` (strictly allowlisted
and bounded), `logs.query` (paged metadata/messages only), `preferences.get`,
`preferences.update` (per-user namespace only), and `runtime.restart` only
after explicit manage authorization and release-gate review. No generic
`command.execute`, arbitrary path, terminal process launch/kill, central login
credential, or trading operation. Settings that change machine/service
configuration are not writable in the initial contract.

## Limits, concurrency, timeout, and cancellation

Proposed initial measurable policy:

- Maximum frame: 64 KiB; logs page ≤200 entries and ≤48 KiB serialized.
- One active Agent/MT5 work request at a time; at most 4 accepted management
  requests in process and at most 16 queued. Overflow returns `BUSY` without
  creating an unbounded thread or queue. Status requests may coalesce per SID.
- Dashboard polls every 5 s, at most one poll in flight per UI process. Manual
  refresh cancels/supersedes a pending read. Background diagnostics limited to
  one active collection per client SID.
- Connect timeout 1 s; ordinary status/log read deadline 2 s; diagnostic
  deadline 30 s; runtime restart acknowledgement 5 s then report
  `OUTCOME_UNKNOWN` if the Service cannot confirm state. These are proposed
  starting thresholds to measure on supported Windows hosts.
- Cancellation before dispatch prevents execution. After a request reaches
  Agent/Worker, cancellation is best effort and does not prove the operation
  stopped. Mutating operations must be idempotent or return unknown and require
  state reconciliation. v0.1.4 carries no trading mutation.
- Client reconnect uses exponential backoff with jitter (0.5 s, 1 s, 2 s,
  4 s, then capped at 10 s); user can manually retry. Close/cancel tears down
  stream, timer and event subscriptions.

## Status schema and freshness

Every status includes `state`, `observed_at_utc`, `source`, `age_ms`, and
`reason_code`. State vocabulary: `READY`, `DEGRADED`, `DISCONNECTED`,
`STALE`, `UNKNOWN`, `UNSUPPORTED`, `NOT_CONFIGURED`, `NOT_AUTHORIZED`.
`CENTRAL_CONNECTED` in Local Setup is `NOT_CONFIGURED`, never false-ready.
`TRADING_CAPABILITY` is `UNSUPPORTED` in v0.1.4; `TRADING_AUTHORIZED` is
`NOT_AUTHORIZED` or `UNSUPPORTED` depending on capability, never `READY`.

| Dimension | Source | Stale/unknown rule |
|---|---|---|
| `SERVICE_RUNNING` | SCM query by UI; monotonic process observation | Probe within 2 s; beyond 10 s without a fresh successful probe show UNKNOWN, not cached running. |
| `LOCAL_AGENT_RESPONSIVE` | successful management-pipe status response | Response ≤5 s is current; age >15 s is STALE; pipe failure is DISCONNECTED with last-known timestamp. |
| `WORKER_READY` | Agent authenticated health projection of Worker/session identity | Only current Agent response plus live Worker evidence is READY; >15 s is STALE. |
| `MT5_CONNECTED` | Agent/Worker safe health read | >15 s is STALE; missing terminal/broker observation is UNKNOWN/DISCONNECTED with reason. |
| `CENTRAL_CONNECTED` | verified central endpoint only | Local Setup = NOT_CONFIGURED; no central endpoint is invented in v0.1.4. |
| `TRADING_CAPABILITY` | versioned Agent capability registry | v0.1.4 = UNSUPPORTED; no enable toggle. |
| `TRADING_AUTHORIZED` | explicit central/local policy and capability | If no capability or policy source, = UNSUPPORTED/NOT_AUTHORIZED, never inferred from account visibility or credit. |

Use UTC server timestamps and monotonic local age. Reject timestamps >5 minutes
in the future as `CLOCK_SKEW`; do not present them as current. Cache only
sanitized status for the current Windows user. Persist offline UI event history
as a bounded per-user file: maximum 1 MiB or 7 days, whichever comes first;
mark each record as cached/local and do not merge it into security audit.

## Error taxonomy and recovery

`PIPE_NOT_FOUND` → Service stopped/unavailable; show SCM status and recovery
guidance. `ACCESS_DENIED` → explain current SID lacks operation permission;
do not prompt for or store admin credentials. `PROTOCOL_MISMATCH` → stop
requests and show installed version mismatch. `BUSY` → short retry suggestion.
`TIMEOUT` → label outcome unknown for a mutating management operation; status
poll can retry. `STALE_STATUS` → display observation time and refresh action.
`SERVICE_START_REQUIRES_ELEVATION` → user invokes Windows-approved SCM/UAC
flow. `UNSUPPORTED_CAPABILITY`/`NOT_CONFIGURED` → no action offered.
`INTERNAL_ERROR` returns correlation ID and sanitized text only.

Service restart, Runtime Worker restart, MT5 terminal restart and UI restart
are distinct operations with distinct permission, confirmation and evidence.
SCM start/stop is outside IPC. Runtime restart must only target the owned
Worker and must not kill arbitrary `terminal64.exe` processes.

## Contract tests

Share JSON fixtures for valid, malformed, oversized, old-major, missing-field,
SID mismatch, unauthorized operation, timeout, cancellation, queue-full,
duplicate request ID and sanitized error. Python tests verify DACL, the actual
caller `TokenUser` SID (not merely the configured Worker principal),
impersonation revert and authorization; C# tests verify serialization,
correlation, timeouts and ViewModel behavior. Windows integration tests use a disposable service/pipe
instance and synthetic data; no MT5 order or live trade is involved.

## Related documents

[Local API](LOCAL_API.md) · [Security Model](SECURITY_MODEL.md) ·
[WPF Solution](WPF_SOLUTION.md) · [ADR-ARCH-017](adr/ADR-ARCH-017-management-ipc.md)
