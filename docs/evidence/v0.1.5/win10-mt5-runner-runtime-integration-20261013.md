# MT5Agent v0.1.5 — MT5 Integration Runner Evidence (2026-10-13)

**Result: PARTIAL; the interactive Worker and terminal have been preserved, and
Agent↔Worker IPC now works under the correct service identity.** Pipeline #84
was manually installed by the Product Owner. We did not run that Installer.
The exact installed components match Job #862's manifest. A fresh integrated
15-minute observation is in progress; an initial reconnect transition was
observed after a controlled Worker API shutdown. This is live Windows evidence,
not CI-only validation.

## Artifact and installation

- Pipeline #84, Build Job #862, Verify Job #863; source commit
  `91d5f6b47181375dc76975ebf61081746d0d136b`.
- Installer: `MT5Agent-Setup-v0.1.5-windows-x64.exe`, 22,455,095 bytes,
  SHA-256 `2606c179c2744cddda54915140f264029adac1a35c9b372596a586192d1927de`.
  The local executable, Job #862 manifest and sidecar matched; Windows verified
  the same SHA-256. Pipeline #84 passed 14/14 jobs.
- The Product Owner performed the installation manually. Installer PID and
  numeric Exit Code were not captured, so those values are **NOT RECORDED**.
  All nine installed components checked against the Job #862 manifest by size
  and SHA-256.
- Evidence directory:
  `C:\MT5Agent-Test\Evidence\RuntimeIntegration-Pipeline84-Install-20261013-151000\`.
  It contains manifest/sidecar copies, the component verification report,
  pre-install state, security snapshots, migration rollback plan, process and
  IPC probes, and stability samples.

## Machine and security configuration

- `WIN10-MT5-RUNNE`, Windows 10 Pro x64, build 19045; SSH administration was
  elevated Administrator in Session 0. The active console session is
  `MT5RuntimeUser`, Session 1, standard user SID
  `S-1-5-21-2457279486-2650524583-4089100399-1003`; it is not in
  Administrators or Remote Desktop Users.
- Initial runtime configuration targeted `MT5RuntimeUser` and the existing
  MT5 profile, but had `ControlPrincipal=WIN10-MT5-RUNNE\Administrator`.
  This did not match the installed Service's `LocalSystem` identity and caused
  `RUNTIME_IPC_FAILED`.
- After recording values and ACLs and saving `rollback-plan.md`, the installed,
  manifest-verified `Set-MT5RuntimeConfiguration.ps1` was used to set
  `ControlPrincipal=NT AUTHORITY\SYSTEM` (`S-1-5-18`). RuntimePrincipal,
  terminal/profile paths, Worker paths and pipe name were retained. The script
  preserved the standard-user boundary, protected Worker code ACL, registry
  ACL and no-write access for RuntimePrincipal. No account, credential,
  Windows policy, task definition, MT5 profile or snapshot was changed.
- After migration, an Administrator connection to the Worker pipe was rejected
  with WinError 5. A temporary read-only health probe running as LocalSystem,
  the intended control identity, succeeded. RuntimeUser's temporary
  read-only Management request was also rejected with WinError 5; its temporary
  scheduled task was removed. No DACL was broadened.

## Process and session topology

| Component | Process ID | Session | Identity | Evidence |
|---|---:|---:|---|---|
| MT5Agent Service | 4088 | 0 | LocalSystem | SCM/CIM readback; Automatic; Running |
| Agent packaged parent/child | 7236 / 7016 | 0 | LocalSystem | Process tree; Agent status replies |
| Worker launcher / Worker | 4832 / 7032 | 1 | MT5RuntimeUser | Existing interactive task and authenticated Worker identity |
| MetaTrader 5 terminal | 7944 | 1 | MT5RuntimeUser | Exact installed terminal path; retained through Worker restart |

The existing `MT5 Agent Interactive Runtime Worker - MT5RuntimeUser` task is
Running with an interactive, limited token. The legacy Administrator task
remains Disabled. No duplicate Worker process was observed. Two WPF process
instances were visible in Session 1; we did not launch, close, or interact with
them, and WPF smoke testing on this runner is **NOT TESTED**.

## Runtime and IPC observations

- Before the Agent install, Worker PID 6852 returned `WORKER_READY`,
  `MT5_CONNECTED`, initialized, terminal build 6249, and no error. Safe reads
  returned terminal version `(500, 6249, 8 Oct 2026)` and 12,303 symbols.
- Worker-only soak: 32/32 successful health samples over 15m34s, one Worker PID
  6852 in Session 1, one terminal PID 7944 in Session 1, and no health errors.
  Worker CPU was 0.859–1.016 seconds and working set 7.2–7.9 MB. Terminal CPU
  was 212.234–220.016 seconds and working set 10.4–17.8 MB.
- After ControlPrincipal migration, authorized Management requests returned
  30/30 `status.get` and 10/10 `logs.query` responses. A fresh reply reported
  Agent running, Worker ready, MT5 connected, and `FRESH`. The Agent status
  omitted `worker_session_id` (`null`) even though authenticated Worker health
  and Windows process inspection both showed Session 1. This is a source defect:
  the adapter verified the Worker identity but did not copy its session number
  into the management health model.
- Regression fix is in the working tree: expose only the validated integer
  Worker session number. Focused tests passed (36 passed, 2 skipped); full Linux
  suite passed (290 passed, 37 skipped; Windows-only launcher tests excluded).
  A new verified Installer and Windows retest are still required before this
  fix can be accepted operationally.
- Live negative checks: an `order_send` request to the Worker was rejected as
  `IPC_UNSUPPORTED_OPERATION`; no order was submitted. Administrator access to
  the Worker pipe and RuntimeUser access to Management were both denied.
- A separate integrated soak began at 11:48 UTC. It first observed a connected
  Agent/Worker/MT5 state, then a temporary `MT5_NOT_CONNECTED` and retry-exhausted
  interval after the controlled Worker API shutdown/restart. Direct LocalSystem
  health and a subsequent Management read recovered to `MT5_CONNECTED` by
  11:54:32 UTC. This run must not be reported as a clean stability PASS; its
  final sample count and transition record will be appended after completion.
- No account identifier, balance, order, quote, credentials or secrets were
  requested. Trading capability remains `UNSUPPORTED`; no trade was executed.

## Events and limits

From the post-install/reconfiguration review window, one informational
MT5Agent Application event and one informational Service Control Manager event
were found; no .NET Runtime, Application Error or MT5Agent error event was
found. Agent logs used fixed messages and redacted caller SIDs.

Windows 11/Server compatibility, RDP disconnect/logoff, WPF UI behavior, a
separate Worker-unavailable injection, and a clean 15-minute integrated soak
remain **NOT TESTED** or **BLOCKED**. The local regression fix is not present in
the manually installed Pipeline #84 binary. Do not use this report as release
approval.
