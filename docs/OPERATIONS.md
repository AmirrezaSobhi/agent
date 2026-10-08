# Operations Runbook

This runbook covers the current split-session runtime. Lab validation is not a
substitute for a supported customer installer or live release pipeline.

## Ownership boundaries

| Component | Owns | Does not own |
| --- | --- | --- |
| Agent/control plane | HTTP/application lifecycle, Worker discovery, health, bounded client retry, degraded status | MetaTrader5 API, terminal process, interactive session creation |
| Runtime Worker | Persistent MT5 API connection, serialized allowlisted reads, MT5 health/reconnect, API shutdown | Windows user logon bootstrap, broad Agent service configuration |
| `terminal64.exe` | MT5 terminal process and its per-user terminal profile | Agent/Worker lifecycle policy |
| Windows runtime session | User token/profile and interactive desktop required by MT5 | Agent service/control-plane lifecycle |
| Scheduled Task | Starts/restarts the Worker after the configured user's logon within bounded policy | Creating a session at cold boot or initializing Agent readiness |
| Autologon bootstrap | Creates the designated interactive user session after boot | Worker/MT5 health or CI validation |

Do not confuse account identity with session placement. The Worker and terminal
must be in the same configured runtime account and nonzero interactive session;
the Agent/control process is expected in Session 0.

## Normal startup and readiness

1. Windows starts the Session 0 control process. Its health may be degraded if
   the runtime session or Worker is not yet available.
2. The configured runtime user obtains its interactive session. The task starts
   the persistent Worker using an interactive token.
3. The Agent connects to the local authenticated pipe, validates protocol and
   Worker identity/session, then requests Worker health.
4. If MT5 is not initialized, the Agent requests initialization through IPC.
   The Worker selects the configured terminal/profile and performs initialization.
5. The Agent reports runtime-ready only after connected health and required
   safe-read validation. A live HTTP server or `AGENT_RUNNING` alone is not
   MT5 readiness.

The Agent uses bounded retries/readiness checks. Operators should inspect the
reported state and logs rather than adding arbitrary startup sleeps.

## Health checks

Use the application's health command/HTTP path or the packaged Agent's
inspection-only `--diagnose --json`. Diagnostics read machine runtime policy
and query the authenticated Worker; they do not call MetaTrader5 locally or
initialize it. A successful diagnostic is a current health observation, not a
broker authorization or trading-readiness claim.

Check these signals separately:

- Agent process is alive and HTTP/application host responds.
- Worker pipe responds and its principal, SID, protocol version, and SessionId
  match policy; Worker SessionId is nonzero.
- MT5 runtime state is `MT5_CONNECTED` and `mt5_connected` is true.
- Terminal identity/session/path match the Worker where independently
  observable.
- Safe reads succeed through the Agent application boundary.

Do not copy account-information payloads into tickets or logs. Report only
success/failure and the minimum redacted fields needed for diagnosis.

## Degraded operation and recovery

| Observation | Operator action |
| --- | --- |
| Agent alive; Worker unavailable | Inspect runtime-user session and task history, machine config, pipe ACL, and Worker logs. Do not change ACLs broadly. |
| Worker ready; MT5 not initialized | Let the Agent's bounded startup flow request initialization; inspect Worker error if it remains uninitialized. |
| MT5 disconnected/reconnecting | Allow bounded Worker recovery; verify terminal and broker/network status without launching a second terminal. |
| Runtime session absent | Treat runtime as unavailable. Restore the designated session through approved Windows bootstrap/admin procedure. |
| Explicit runtime-user logoff | Worker and terminal may exit. Agent remains degraded; do not force-create a session or use fake RDP. |
| Pipe authorization/protocol failure | Verify configured principals, SID, SessionId, and matching deployed protocol. Do not weaken the DACL or grant impersonation privilege as a workaround. |

Task Scheduler is the Worker process restart owner; the Worker owns API
reconnect; the Agent observes and reports. Avoid duplicate supervisors.

## Reboot recovery

The lab's cold-boot sequence has passed without RDP/console login. For a
deployed host, verify automatic logon metadata without inspecting credentials,
then check session, task result, Worker health, MT5 connection, terminal
identity, and safe read through the Agent. Do not manually start the task or
terminal before collecting failure evidence. Do not treat the lab test as
proof of customer installation/support readiness.

## Worker startup reliability observation

The post-release Pipeline #17 history contains an initial failed
`smoke:mt5-runtime` Job #132 followed by successful Job #134. Job #132's trace
records a script exception and does not contain the expected runtime report;
its root cause is unknown. Job #134 recorded `MT5_CONNECTED`, Agent Session 0,
Worker and terminal Session 1, and three successful safe reads. The reported
Windows reboot and manual retry are operational observations, not facts
independently proven by the GitLab API. This single recovery sequence does not
prove a startup-timing cause or resolve Worker startup reliability. Preserve
failure evidence before any operator retry and investigate the lifecycle in a
separately scoped reliability effort. See
[post-release validation](evidence/v0.1.3/post-release-validation.md).

## Safe shutdown

Use the supported Agent stop path and let the control client detach. The Agent
must not send runtime shutdown merely because a request or client process ends.
If an explicit maintenance shutdown is required, use the approved Worker
runtime-shutdown operation, then verify Worker/API state. `MetaTrader5.shutdown()`
does not guarantee `terminal64.exe` exits. Never kill `terminal64.exe` by image
name, log off the runtime user casually, disable its task, or change Autologon
to clear a health problem. Preserve process/session evidence and escalate if
ownership is unclear.

MT5 Agent provisioning must not manage BitLocker, TPM, Secure Boot, or recovery
keys; those remain machine-owner/VPS-provider responsibilities.

## Clock skew and audit correlation

Phase 4D acceptance in Pipeline #11 observed approximately **10h30m** MT5-host
UTC skew relative to Linux UTC.
[Pipeline #11 evidence](evidence/v0.1.3/phase4d-live-ci-acceptance.md) retains
commit, pipeline, and artifact hash as provenance; the Worker and terminal
survived candidate cleanup. The later release record for Pipeline #16 states
that W32Time synchronization was established with an active external source,
UTC accuracy was independently checked, and tag-pipeline timestamps correlated
with GitLab timestamps. This release-gate observation does not establish
autonomous time polling or persistence through reboot/network transitions.

Skew can distort command-age/deadline interpretation, duplicate/replay windows,
log ordering, telemetry freshness, certificate validity checks, and incident
correlation wherever host wall time is used. These are risk surfaces, not claims
that every future subsystem is active. Use correlation IDs and observed
process/session identity alongside timestamps; record host/UTC offset when
collecting evidence. Do not change timestamps in historical acceptance records.

The previously observed offset was addressed for the v0.1.3 release acceptance;
the remaining operational follow-up is to evaluate autonomous time polling and
validate synchronization persistence through reboot and network transitions.
Commercial operations still need a defined clock-monitoring and tolerance policy.

If monitoring shows drift again, use a separately approved maintenance plan to
compare guest/host UTC, timezone presentation, hypervisor synchronization,
Windows Time Service source/status, and network reachability. Assess large
clock-step effects on the persistent runtime before authorizing any correction.
Verify the measured UTC offset and stability, then repeat relevant health,
safe-read, deadline/replay, and observability validation. Do not modify host
time, NTP, timezone, Windows Time Service, Worker/task, or MT5 configuration
under an ordinary CI/documentation task.
