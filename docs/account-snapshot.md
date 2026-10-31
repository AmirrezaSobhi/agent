# Authorized account snapshot (Server contract v1.0)

The Server authority is `root/server/docs/account-snapshot.md` at commit
58b9fa1b00bda9b06dabffaf214c1855f4fde875. No wire changes are introduced here.

The existing trusted local Gateway settings file can explicitly grant a read:
`account_read: {"permission":"account-read","expires_at":<UTC epoch>}`.
Optional `interval_seconds` defaults to 15 and must be finite, from 5 to 300.
Grant expiry cannot exceed the WSS credential expiry. Absent/invalid/expired
configuration denies reads. Existing configurations remain connectivity-only.
No real configuration or credential is changed by this patch.

Composition supplies the existing command dispatcher to a dedicated
ApplicationBoundary using the existing IdentityAuthority authorizer. Its process
local credential has only `account-read`; the authorizer rechecks the trusted
local grant on every request. It never confers trade permission. The local config
is the operator trust boundary, not a remote authorization claim. WSS hello_ack
must succeed before any sampling is scheduled, and permission is rechecked before
read and before send. Revocation or expiry suppresses results of in-flight reads.

A single daemon read worker is retained across reconnects, with no work queue.
An outstanding read prevents another read; the wire loop continues servicing
ping/pong. After four seconds an unknown/null snapshot may be sent once, while the
old read still occupies its slot. Python cannot forcibly terminate that worker.
Old connection results are discarded on reconnect; the next eligible interval
tries fresh work. Authorization is checked again inside ApplicationBoundary.
MT5 read failures and invalid data map to mt5_connected=false and null fields.
Successful account_information establishes MT5 status independently of WSS.
Only six selected fields are sent; login/owner/broker details are discarded.
Unexpected handler failures no longer log exception text/traceback, which could
contain financial data. Payloads and credentials never enter Gateway event logs.

This source is not installed or released by this change. A real DEMO test requires
separate version provenance, explicit configuration and Product Owner approval.

## Type-only DEMO verification (Story #49, Micro-step 5A)

The existing management Named Pipe adds `account.demo_status` with an empty
payload. The existing Windows caller-token SID allowlist is checked before any
read. Composition supplies a dedicated ApplicationBoundary/IdentityAuthority
with only `command:mt5.get_account_demo_status`; no trading or full-account
permission is granted. The handler uses the existing Worker-backed
`account_information` adapter and discards everything except trade mode before
returning. `data` contains only `demo_verified`: JSON true for DEMO, false for
CONTEST/REAL, or the literal string `unknown` for unavailable, invalid, denied
or unsupported results. Missing modes, booleans and numeric strings cannot
prove DEMO. MetaQuotes account mode reference:
https://www.mql5.com/en/docs/constants/environment_state/accountinformation

This is an explicit local management read, not an automatic WSS grant. WSS
`account-read` opt-in/expiry and snapshot v1.0 are unchanged. No account number,
financial values or exception text is logged or returned by this operation.
The management protocol envelope retains request/correlation IDs but its data
projection is type-only. Invalid nonempty payloads are rejected before reading.

Local tests cover DEMO/CONTEST/REAL/unknown, denied SID without a read, rejected
payload, credential denial, runtime failure, and sensitive-field projection.
Existing installed binaries do not gain this operation until a separately
approved installation. A read-only live probe returned UNSUPPORTED_OPERATION;
current independent DEMO proof is therefore NOT VERIFIED, not false. This
change does not authorize installing/restarting services or changing grants.

## Explicit snapshot command over WSS

After `hello_ack`, the Agent may receive a version 1.0 `snapshot_request`
containing `agent_id`, `command_id`, `correlation_id` and a bounded absolute
`expires_at`. The matching `snapshot_response` has the same request identifiers
and expiry, a result status and, on success, the validated projected snapshot.
The response envelope correlates with the request message ID. The existing
`account-read` grant is checked before reading, after reading and before sending;
only DEMO account data is returned. Periodic and command reads share one
non-queuing reader. A busy reader reports unavailable. A process-local bounded
ledger rejects duplicate command IDs until expiry, including across reconnects
in the same process. It is not durable across process restart; reads are strictly
read-only. Stale results from an earlier connection are discarded. Neither
financial payloads nor credentials are written to Agent logs.
