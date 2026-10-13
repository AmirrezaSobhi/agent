# Secure LocalSystem Runtime Smoke

`smoke:mt5-runtime` must exercise the same Service-to-Worker boundary used in
production. The MT5 runner's GitLab Runner service currently runs as an
Administrator account, while the installed Worker accepts only its configured
`ControlPrincipal` (`NT AUTHORITY\SYSTEM`, SID `S-1-5-18`). The CI test must not
change that identity or widen the Worker pipe ACL.

## Execution flow

```mermaid
sequenceDiagram
    participant CI as GitLab Runner (elevated Session 0)
    participant Stage as Protected Program Files stage
    participant Task as One-shot Scheduled Task (LocalSystem, Session 0)
    participant Agent as Candidate Agent
    participant Worker as Existing interactive Worker
    participant MT5 as Existing MetaTrader 5
    CI->>CI: Verify commit, build receipt, and test executable receipt
    CI->>Stage: Copy allowlisted inputs; verify copied hashes
    CI->>Task: Register fixed PowerShell entrypoint and fixed arguments
    Task->>Task: Verify SYSTEM SID, Session 0, stage ACL, context receipt, and payload hashes
    Task->>Agent: Start candidate with a fixed ephemeral Management endpoint
    Agent->>Worker: Authenticated Runtime IPC as configured ControlPrincipal
    Worker->>MT5: Existing initialized terminal; read-only requests only
    Task-->>CI: Structured result, provenance, task exit status, and evidence
    CI->>Task: Remove only the task created by this job
    CI->>Stage: Remove only this job's stage after task exit
```

The coordinator checks that the installed `ControlPrincipal` resolves to
LocalSystem, that `RuntimePrincipal` is a distinct SID, and that the
Administrator runner cannot open the Worker pipe (the expected denial is
WinError 5). It serializes runtime jobs with a GitLab `resource_group` and a
machine-wide mutex. The task name and entry point are fixed by the coordinator;
there is no caller-supplied command or script argument.

Inputs are copied under `Program Files\MT5Agent\CiRuntimeSmoke\<pipeline>_<job>`
with an explicit, non-inheriting DACL granting Full Control only to LocalSystem
and Administrators. The installed product directory must itself be non-reparse
and not writable by unprivileged principals. Source scripts are compared with
the selected commit's Git blob before and after copy. The candidate executable
and WPF Management test client are checked against same-pipeline build receipts
before and after copy. The System task independently validates the protected
context receipt, file hashes, registry identity policy, its own SID, and
Session 0 before it can run the fixed smoke operation.

The task has a strict 12-minute scheduler limit and the coordinator has an
11-minute result deadline. A missing, stale, malformed, failed, or mismatched
result fails closed. On completion, the job validates task exit status and
copies evidence back before removing its own scheduled task and stage. A task
that cannot be confirmed stopped leaves its protected stage in place for
investigation rather than deleting files it may still be using. Pipeline
serialization plus a global mutex prevents two jobs from controlling the same
interactive Worker/MT5 session concurrently.

The System smoke permits only the existing non-trading health and terminal
read operations (`mt5.get_symbols_total`, `mt5.get_terminal_version`, and
`mt5.get_account_information`) plus Management health checks. Unsupported
trading operations remain rejected by the Worker protocol. The test does not
start, stop, or reconfigure the existing Worker or MetaTrader terminal.

## Verification status

The source and structural regression tests are not proof that Windows Task
Scheduler, ACL translation, and the live Worker pipe behave as expected. Those
claims remain pending until a feature-branch Pipeline runs the System task on
`win10-mt5-runner` and publishes its structured receipt. After CI, deployment
must still use the exact verified Installer from that pipeline and verify live
Management Health and a fresh stability soak.
