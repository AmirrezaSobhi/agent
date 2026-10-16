# Native Agent Core Gateway connectivity — Phase 2.2

This opt-in transport is hosted by the existing Python Agent Core in Session 0,
under the existing Windows Service process ownership and shutdown event. WPF,
secure management IPC, Runtime Worker and MT5 capability dispatch are unchanged.
No Gateway message reaches the command dispatcher or a trading API.

## Configuration and authentication

By default the Core reads `C:\ProgramData\MT5Agent\Gateway\config.json` when
present; `MT5_AGENT_GATEWAY_CONFIG` can select a test-specific path. Absent file
preserves the previous hosting behavior. Present but invalid configuration fails
closed for WSS and retries with backoff, without stopping local management.

The JSON object has exactly `url` (full wss endpoint), `agent_id` (stable lower-case
ID), `token_file` (absolute file path), and `expires_at` (UTC epoch seconds).
Provision both files in an administrator/SYSTEM-only ACL directory. Never place
credentials in source, process arguments, logs, build inputs or the UI. Settings
and token are reread on every reconnect. To change domains immediately, update
configuration atomically and restart the Agent Service. To revoke, remove the
Gateway verifier and stop the client. This TEST-ONLY bearer expires after 24h;
mTLS remains the future design and is not established at Runflare ingress.

TLS uses the Python system trust store and hostname validation. The transport
uses pinned websockets 16.1.1 instead of implementing WebSocket framing/TLS in
house. It is the Core's first third-party runtime dependency; MT5/NumPy remain
excluded from the control-plane executable. Library wire logs are suppressed to
prevent Authorization headers appearing at DEBUG level. Only allowlisted JSON
connection events, IDs, process ID, exception class and retry delay are emitted.

## Lifecycle and bounds

One supervisor thread owns one connection and the existing host owns its stop.
Retries use exponential backoff with jitter, 0.75–1s initially and at most 60s;
waits are interruptible. Healthy sessions lasting 30s reset backoff. Shutdown
closes the socket and joins the supervisor. Handshake timeout is 3s, hello and
request deadlines 5s, inactivity 25s, protocol ping 10s / timeout 5s. Receive
frames are limited to 16KiB and a queue of 8; compression is disabled. There is
no application outbound queue; at most two locally initiated requests are
pending. Duplicate IDs have a bounded 64-entry window and messages are limited
to 20/s. Invalid schemas, unsolicited response correlations and sensitive
message types terminate the session. No busy retry loop is used.

The v1.0 protocol sends hello, verifies correlated hello_ack, answers the
Gateway's ping, and performs one harmless echo plus client ping per session.
No BUY/SELL, arbitrary command invocation, Kafka or PostgreSQL is involved.
The Gateway's existing five-minute lifetime deliberately causes periodic
reconnections; an expired credential cannot reconnect successfully.

## VM validation / rollback procedure

Build an internal executable from the recorded GitLab commit using the existing
PyInstaller specification; retain product version 0.1.5 (not a public release).
Before replacing the Agent executable, stop the existing service, back up its
exact executable and SHA256 in a restricted test directory, preserve the Service
Host and Worker, then copy the candidate into the existing Agent executable
path. Restart the same service and prove its Session 0 child PID owns the WSS
connection. If startup or acceptance fails, stop the service, restore the
backed-up executable, remove only the newly provisioned Gateway config, and
restart. Never uninstall/re-register the service or change SCM security.

Tests in `tests/test_gateway_wss.py` cover configuration expiry, schema/identity,
correlation, redaction, reconnect/backoff, duplicate start and lifecycle cleanup.
Real Windows service evidence is separate from the earlier independent .NET
probe and must correlate Agent process logs with Gateway message UUIDs.
