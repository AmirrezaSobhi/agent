# Local API and IPC Contract

**Status:** Proposed target contract. The existing named pipe is Agent-to-
Worker. The existing HTTP `/command` interface is not an approved privileged
UI endpoint. No proposed operation below is represented as an existing route.

## Candidate operations (conceptual only)

- Health/status; runtime status; capabilities.
- Read/update authorized settings.
- Diagnostics and bounded event query.
- Generate support bundle locally.
- Authorized Runtime restart.
- Authorized Windows Service start/stop via independent OS control path.

No endpoint names, payload fields, or wire schema are approved by this list.
Trading commands should not be exposed through a general local management API.

## HTTP Loopback versus Windows IPC

| Choice | Advantages | Risks / required evidence |
|---|---|---|
| HTTP Loopback | Familiar client tooling, structured versioning, straightforward diagnostics | Loopback is not auth; CSRF/browser origins, port discovery, token/session handling, local-process attacks, concurrent admission and bounded execution. Existing HTTP composition currently uses allow-all defaults. |
| Windows-native IPC | Can bind access to Windows identity/ACL and avoid listening TCP port | ACL design, session identity, impersonation, message framing, timeouts, client compatibility and elevated recovery helper complexity. Existing Worker pipe is purpose-bound and must not be reused as a UI API by default. |

**Open Decision:** choose after threat model, UI framework compatibility spike,
multi-user/session tests, and a least-privilege prototype. Do not add both
transports without a concrete compatibility need and shared authorization layer.

## Required contract properties

- Explicit protocol and schema versions; capability negotiation; reject unknown
  required fields/versions safely.
- Authentication bound to Windows user/process/service principal and request
  audience; authorization per action/resource. Do not trust a caller-provided
  username. Fail closed.
- Least privilege and secret-free responses. Existing permissive development
  authentication is never extended to privileged operations.
- Request/correlation IDs, stable error taxonomy, audit for privileged writes,
  and idempotency keys for retryable management mutations.
- Input/payload/time/concurrency limits; bounded worker pool or admission and
  backpressure; no unbounded threads/queues. Define shutdown drain semantics.
- Concurrent requests must not cause parallel MT5 API calls. Runtime mutations
  must serialize or use an explicit command lane.
- Transport timeout does not prove action cancellation. Report uncertain
  outcomes explicitly; management operation retry must be idempotent or
  reconciled.
- If HTTP is selected: explicit loopback binding, Origin/Host checks, CSRF
  model, no ambient browser credentials, protected random token lifecycle and
  port ownership validation. TLS on loopback may not alone solve local process
  access.

## Error taxonomy proposal

`INVALID_REQUEST`, `UNSUPPORTED_VERSION`, `AUTHENTICATION_REQUIRED`,
`AUTHORIZATION_DENIED`, `RESOURCE_NOT_FOUND`, `CONFLICT`, `STALE_REVISION`,
`BUSY`, `RATE_LIMITED`, `SERVICE_UNAVAILABLE`, `OPERATION_TIMEOUT`,
`OUTCOME_UNKNOWN`, `INTERNAL_ERROR`. Error details are actionable but omit
secrets, raw rejected values and stack traces.

## Independent Service recovery path

Service cannot start itself after it is stopped. Use Service Control Manager
permissions exposed through the UI's OS token/UAC or a narrowly scoped elevated
helper with a signed installation identity, fixed allowlisted service actions,
audit, and no arbitrary command execution. Ordinary users receive clear
permission guidance; never collect or store administrator passwords. Restart
and start behavior is distinct from runtime-worker restart and MT5 terminal
restart.

## v0.1.4 release gate

Before privileged settings or runtime actions are exposed: approve transport,
principal mapping, per-operation permission matrix, request bounds, CSRF/Origin
controls if HTTP, audit schema, elevation flow, and negative tests across users
and sessions. Read-only diagnostic surface may be narrower but still requires
identity/privacy review.
