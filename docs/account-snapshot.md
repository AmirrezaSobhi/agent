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
