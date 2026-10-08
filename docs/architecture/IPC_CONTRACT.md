# Local Management IPC and Status Contract

**Status:** Implemented, limited read-only v1 contract (2026-10-08). Only
`protocol.negotiate` and `status.get` are supported. Diagnostics, log queries,
preferences, and Runtime restart remain planned and unauthorized. Current
evidence is summarized in [Implementation Baseline](IMPLEMENTATION_BASELINE.md).

## Recommendation: a separate Windows Named Pipe

Use a dedicated local named pipe, implemented name
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

1. **Server identity:** the isolated proof used a LocalSystem service in
   Session 0; production uses the already provisioned Agent process identity.
   The UI does not impersonate the Service and receives no Service secret.
2. **Client identity:** the pipe DACL grants access only to the Service process
   token SID and explicitly configured user SID values. It adds no `Everyone`
   or generic interactive-user ACE. Configure
   `MT5_AGENT_MANAGEMENT_ALLOWED_SIDS` in the Agent Service environment with
   comma-separated SIDs, then restart the Agent. An empty list disables the
   endpoint.
3. **Server verification:** Python calls `ImpersonateNamedPipeClient`, opens
   the thread token for query, reads `TokenUser`, closes the token, then calls
   `RevertToSelf` in `finally`. Caller-claimed SID, PID, username, and session
   are ignored. Identity or restoration failure denies the request; restoration
   failure stops the management listener. `GetNamedPipeClientProcessId` is not
   authentication.
4. **Per-operation authorization:** allowlist authorization currently covers
   only read-only `protocol.negotiate` and `status.get`. Service start/stop is
   outside the pipe and subject to SCM ACL/UAC. Trading, diagnostics,
   preferences, and Runtime mutations are absent.
5. **Multiple sessions:** each Windows user has a distinct SID and preference
   store. The Service can accept clients from approved SIDs but returns only
   permitted projections; one user's layout or credentials never leak to
   another. Worker remains under its separate runtime principal/session.

Product provisioning of a durable local reader group and service principal is
unresolved. For now, a machine administrator provisions individual SID values;
never copy an SID from an untrusted UI request.

## Protocol v1 proposal

Message-mode pipe, one UTF-8 JSON object per complete Windows pipe message,
maximum 65,536 bytes inclusive of envelope. The management listener is a
separate endpoint and does not reuse the Worker protocol. The C# client sends
one status request per connection; the server replies and the client sends an
ACK before disconnect. `protocol.negotiate` is supported by the server; the
Dashboard currently requests status and validates the version on every
response. Unknown major versions fail closed. No bulk data is transferred.

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

### Implemented operations

`protocol.negotiate` returns supported major versions. `status.get` projects
the existing Agent health report: Agent lifecycle/responsiveness, Worker
availability/state, runtime and MT5 state, source identity, UTC observation
time, freshness and bounded error code. The response echoes the request
correlation ID. Windows Service state is `UNKNOWN` because Agent Core does not
query SCM. Central management is `NOT_CONFIGURED`; trading capability is
`UNSUPPORTED`, authorization is `UNKNOWN`, and readiness is `UNAVAILABLE`.
The Agent cannot prove user trading authorization. It does not submit, modify,
or close orders. Diagnostics, logs, preferences and Runtime/Service controls
are not implemented. No generic `command.execute`, arbitrary path, terminal
process launch/kill, central credential, or trading operation exists.

## Limits, concurrency, timeout, and cancellation

Implemented v1 bounds:

- Maximum frame: 65,536 bytes in each direction; contract tests reject
  oversized requests/responses.
- Exactly one pipe instance and one request are handled at a time; there is no
  application queue. Concurrent clients wait at the OS pipe and the C# client
  retries `PIPE_BUSY`/not-found at bounded 100/200 ms intervals (three total
  attempts). `BUSY` is reserved but the current server does not emit it.
- Dashboard polls every 5 s. Client request timeout is 2 s. Cancellation
  disposes the client pipe to interrupt .NET Framework 4.8 reads. Server
  request/ACK timeout is 2 s. A status provider already executing in
  Agent/Worker code may outlive client cancellation; this is read-only and
  does not prove server-side work was cancelled.
- No operation is mutating, so no replay/idempotency promise is made. Any
  future mutation requires reconciliation and separate authorization review.
- Reconnection is bounded per status request; periodic Dashboard refresh tries
  again every 5 s. Exponential backoff/jitter remains future work.

## Status schema and freshness

Every `status.get` response includes `observed_at_utc`, `source_identity`,
`freshness`, `error_code`, and the envelope `correlation_id`, with per-domain
state values. The client calculates age from the UTC observation timestamp:
older than 15 seconds or more than two minutes in the future is STALE. Missing
state is UNKNOWN. A failed request is OFFLINE; it does not replace cached
values with a current state. The Dashboard refreshes every five seconds while
loaded, bounds each IPC call to two seconds, suppresses overlapping refreshes,
and cancels pending work on navigation/unload.

| Dimension | Source | Stale/unknown rule |
|---|---|---|
| `SERVICE_STATE` | Not currently queried by Agent or Desktop | UNKNOWN; no running state is inferred from Agent responsiveness. |
| `LOCAL_MANAGEMENT` | successful authenticated Management Pipe response | Connected for the response; a failed request shows Offline; last runtime observation is Stale. |
| `LOCAL_AGENT_RESPONSIVE` | successful management-pipe status response | Current response proves Agent process responsiveness. Source timestamp >15 s is STALE. |
| `WORKER_READY` | Agent's authenticated Worker health projection | READY only after a valid Worker response; IPC/auth/configuration failure is disconnected/error, missing evidence is UNKNOWN; >15 s is STALE. |
| `MT5_CONNECTED` | Agent/Worker safe health read | Explicit connected/disconnected/initializing/error; absent observation is UNKNOWN; >15 s is STALE. |
| `CENTRAL_CONNECTED` | verified central endpoint only | Local Setup = NOT_CONFIGURED; no central endpoint is invented in v0.1.4. |
| `TRADING_CAPABILITY` | versioned Agent capability registry | v0.1.4 = UNSUPPORTED; no enable toggle. |
| `TRADING_AUTHORIZED` | explicit central/local policy and capability | UNKNOWN and readiness UNAVAILABLE when no policy source exists; never inferred from MT5 connectivity, account visibility or credit. |

Use UTC Agent timestamps and compute age with the Desktop's UTC clock.
Timestamps more than two minutes in the future are STALE and are never
presented as current. Cache only
sanitized status for the current Windows user. Persist offline UI event history
as a bounded per-user file: maximum 1 MiB or 7 days, whichever comes first;
mark each record as cached/local and do not merge it into security audit.

## Error taxonomy and recovery

`PIPE_NOT_FOUND` → Management Pipe unavailable; Service state remains UNKNOWN
until a separate SCM query exists. `ACCESS_DENIED` → explain current SID lacks operation permission;
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

## Current contract tests and remaining gates

Python tests cover malformed/oversized requests, version mismatch, unsupported
operation, SID allowlist, ignored caller-claimed SID, safe status projection,
and Windows live-pipe caller-token identity. C# tests cover status
serialization/mapping, version mismatch, oversized responses,
timeout/cancellation, unavailable Service, reconnection and concurrent reads.
An isolated Windows security spike additionally verified DACL allow/deny,
Session 0 service to Session 1 client, token SID extraction, impersonation
restoration, and a forged SID claim. Full multi-user/multi-session matrix,
production Service-account provisioning, queue-full, mutation idempotency and
interactive Service lifecycle tests remain open. Tests use synthetic status;
no live Agent trading operation or order is involved.

## Related documents

[Local API](LOCAL_API.md) · [Security Model](SECURITY_MODEL.md) ·
[WPF Solution](WPF_SOLUTION.md) · [ADR-ARCH-017](adr/ADR-ARCH-017-management-ipc.md)
