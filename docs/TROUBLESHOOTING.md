# Troubleshooting

Start with read-only evidence: Agent health/diagnostics, Worker health over the
configured pipe, task history, Windows session inventory, and process owner/SID/
SessionId/path. Do not include passwords, broker credentials, Autologon
secrets, or full account-information payloads in reports.

| Symptom | Likely boundary | Checks and safe response |
| --- | --- | --- |
| Worker unavailable | Session, task, process, or pipe | Confirm designated user session exists; inspect task last-run/result and Worker process; verify pipe path and machine config. Do not manually start before capturing failure evidence in an acceptance test. |
| Pipe unavailable | Worker listener or endpoint | Confirm the Worker is running in the expected nonzero session and serving the configured pipe. Avoid TCP fallback. |
| Authorization rejected | Pipe DACL/control identity/session policy | Compare configured `ControlPrincipal` SID with caller identity and verify caller SessionId is 0. Do not broaden pipe ACLs or grant `SeImpersonatePrivilege` as a guess. |
| Protocol mismatch | Agent/Worker version skew | Compare protocol versions and deployed package hashes; deploy a compatible pair through controlled release. Unknown versions fail closed. |
| Worker in Session 0 or wrong account | Task/logon configuration | Check task logon type, runtime principal, session state, and process token. Do not accept username alone as session proof. |
| Terminal in wrong session/account | Terminal lifecycle/profile | Compare terminal owner SID and SessionId with Worker. Never reuse a Session 0 or unrelated terminal as evidence. Do not kill by process name. |
| MT5 initialization failure | Worker profile, package, install, or runtime | Verify explicit terminal path, per-user profile/origin mapping, Worker dependency environment, and Worker error code. Do not call MetaTrader5 from Session 0 or copy another user's profile. |
| MT5 disconnected | Terminal or broker/network runtime | Check Worker health and terminal state, then allow bounded reconnect. Safe reads may fail while degraded; no trade retry is implied. |
| Terminal process exits/crashes | Worker-owned MT5 runtime | Observe the Worker state and its bounded reconnect policy; verify a replacement terminal remains in the same owner/session/path. Do not launch a second terminal manually or terminate unrelated processes. |
| Scheduled Task not running | User logon/task policy | Verify the runtime user has a real interactive session; inspect task enablement, trigger, InteractiveToken, result, and restart policy. `Run whether user is logged on or not` is not the interactive Worker mode. |
| Runtime session missing after reboot | Automatic-logon bootstrap | Collect boot time, session inventory, and safe Autologon metadata only. Do not inspect the stored credential or manually log in during unattended acceptance. |
| MT5 runtime smoke fails on startup | Worker/session/terminal startup path | Preserve the failed job trace and report first. Pipeline #17 Job #132 failed and later Job #134 passed, but the initial cause is unknown. Do not assume a timing defect or treat one successful retry as resolution. |
| Agent degraded but HTTP server alive | Expected split-runtime behavior | `AGENT_RUNNING` is process/lifecycle state; inspect `runtime_state`, Worker availability, and MT5 connectivity separately. Agent remains alive to report runtime loss. |
| CI candidate hash mismatch | Artifact provenance | Compare build evidence, source commit, pipeline ID, artifact filename and SHA-256 at each gate. Fail closed; do not rebuild or substitute a binary after smoke. |
| Account read succeeds but output appears in logs | Privacy boundary | Stop sharing the evidence, remove/redact it according to incident policy, and inspect logging/evidence code. CI should record only success and limited field count. |
| `release:github-sync` reports protected tag required | GitLab tag policy | Configure an authorized protected `v*` tag rule; do not expose the GitHub token to an unprotected tag pipeline. See the [Release sync runbook](GITHUB_RELEASE_SYNC.md). |
| `release:github-sync` reports missing token or HTTP 401 | GitHub credential | Add/rotate the masked protected `GITHUB_RELEASE_TOKEN` with repository Contents:write. Never print the token. |
| GitLab Release/assets not ready | Release lifecycle | Publish the authoritative GitLab Release and all Generic Package links, then retry the failed sync job in the same tag pipeline. Do not create another tag. |
| GitHub tag target or asset checksum conflict | Mirror/data integrity | Stop; preserve both sides and investigate. The sync job will not overwrite the tag, release metadata, or conflicting asset. |

## Clock skew

If host timestamps disagree, preserve the raw observations with host/UTC context;
correlate commit, pipeline, hash, request IDs and process/session identity rather
than sorting all logs by wall time. The accepted MT5 host showed about 10h30m
skew. Use the separately authorized
[operations remediation plan](OPERATIONS.md#clock-skew-and-audit-correlation);
do not repair time or restart the runtime as a diagnostic shortcut.

Pipeline #16's release record states that UTC accuracy and timestamp correlation
were checked for the tag pipeline. It does not establish autonomous polling or
synchronization persistence after reboot/network transitions; those remain
operational follow-up.

## Escalation evidence

Capture timestamps, source commit/artifact hash, Agent state, Worker principal/
PID/session/protocol, terminal PID/owner/session/path/build where available,
task state/result, and bounded error codes. Do not collect credentials, LSA
secrets, private account values, or unrelated user process data.
