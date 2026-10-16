# Native Agent Core Gateway connectivity — Phase 2.2

This opt-in transport is hosted by the existing Python Agent Core in Session 0,
under the existing Windows Service process ownership and shutdown event. WPF,
secure management IPC, Runtime Worker and MT5 capability dispatch are unchanged.
No Gateway message reaches the command dispatcher or a trading API.

## Configuration and authentication

By default the Core reads `C:\ProgramData\MT5Agent\Gateway\config.json` when
present in a real Service-owned Core (identified by its existing shutdown event);
`MT5_AGENT_GATEWAY_CONFIG` can explicitly select a test-specific path for console
operation. CI candidate processes do not consume machine settings automatically. Absent file
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

## Recorded VM evidence — 2026-10-16

Initial native candidate commit `e32ae2fda08fcd40aea98049b8e2c59fe667b240`
passed the complete Agent Pipeline [154](https://gitlab.local/root/agent/-/pipelines/154).
Portable tests passed 384 with 49 platform skips; Windows tests, clean build,
WPF/IPC tests, MT5 read-only smoke, packaging and installer verification passed.
Follow-up tests add response-deadline and automatic-config ownership coverage.

On win10-mt5-runner, the unchanged MT5Agent Windows Service launched the native
candidate in Session 0 (Service PID 6272 → bootloader 8508 → Core PID 756).
The Core owned TCP `192.168.122.71:50194 → 178.239.147.37:443` and completed
validated TLS/WSS to the current `agent-gateway-svb-forex-ai.runflare.cloud`
domain. Agent ID is `win10-native-agent-01`. The existing independent .NET
client was not run. Gateway remained staging revision
`045c78032897a8816f7d7ef0cdcec361aa265297`, Runflare v5.

Hello ID `27ddcf48-6e43-4a7a-886c-b7c0a73e8d2c` received a matching hello_ack;
echo request `67aacd66-884f-4e57-806f-9f269ad23597` was correlated in both Core
and Gateway logs. The Core answered server pings and verified its client pong.
Controlled Service stops/restarts changed the Core PID and reauthenticated.
A valid-format wrong credential produced InvalidStatus in the Core and
ws_auth_rejected in the Gateway. Expired local credentials failed closed before
network connection; increasing retry delays were observed. Restoring valid
settings recovered normal exchanges (Core PID 8904).

The first manually built candidate omitted the existing pywin32 build dependency
and failed startup. The prewritten rollback restored the original executable
and service successfully; installing pywin32 only in the private build venv
corrected the build. No SCM, Worker, disk or security policy was changed.
Original executable SHA256:
`09040AB8305694D049BF87401028359F75EE20A8AB9050D4972DCF4F0C4B50E2`.
Its backup and Rollback.ps1 remain in the restricted
`C:\ProgramData\MT5AgentNativeWssTest` directory.

The existing Worker brought its configured terminal online during normal Agent
startup; the WSS transport neither starts it nor invokes any MT5 operation.
No trade/order request was issued. Existing CI's MT5 smoke remains read-only.
Public domain and test credentials expire; these receipts prove the timestamped
trial, not perpetual production availability. Final process/connection, log,
credential-redaction and reconnect evidence is recorded separately in ignored
Server `reports/phase22-*` files to avoid putting runtime credentials in Git.
