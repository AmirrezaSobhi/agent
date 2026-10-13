# MT5Agent v0.1.5 — MT5 Integration Runner Evidence (2026-10-13)

**Result: PARTIAL; a clean 15-minute Agent↔Worker↔MT5 soak and a controlled
Service restart passed, but the installed Pipeline #84 binary still has a
health-reporting defect and the source fix has no verified artifact yet.**
Pipeline #84 was manually installed by the Product Owner. We did not run that
Installer. The exact installed components match Job #862's manifest. This is
live Windows evidence, not CI-only validation.

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
them, and WPF smoke testing on this runner is **NOT TESTED**. After the
controlled Service restart the Service PID changed from 4088 to 2368 and the
Agent packaged parent/child changed to 8092/6544 in Session 0. Worker PID 7032
and MT5 terminal PID 7944 remained in Session 1 under `MT5RuntimeUser`.

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
- After the controlled Worker API shutdown/restart, an initial integrated run
  recorded a temporary `MT5_NOT_CONNECTED` / retry-exhausted interval and one
  probe collision (`ERROR_PIPE_BUSY`) from concurrent Management access. Direct
  LocalSystem health and a subsequent Management read recovered to
  `MT5_CONNECTED` by 11:54:32 UTC. This run is not counted as a clean stability
  pass.
- A separate, clean integrated soak then ran from 12:06:48.908Z to
  12:22:24.195Z: **32/32** samples reported fresh `MT5_CONNECTED` health, with
  no probe errors, over 15m35s. Management response latency was 25.76–191.72 ms
  (median 52.18 ms). Worker PID 7032 stayed in Session 1; its working set was
  6.58–7.18 MiB and CPU time rose from 0.562 to 0.703 s. MT5 PID 7944 stayed
  in Session 1; its working set was 8.46–76.47 MiB and CPU time rose from
  242.844 to 253.000 s. Service PID 4088 stayed in Session 0 during this soak;
  its working set was 4.64–5.13 MiB and CPU time remained 0.094 s. The soak
  confirms stable health during that interval; it does not erase the earlier
  reconnect transition.
- A subsequent controlled `Restart-Service MT5Agent` completed successfully:
  the Service returned Running as LocalSystem/Automatic under PID 2368, a fresh
  Management response reported Worker ready, MT5 connected and `FRESH`, and
  Worker PID 7032 plus terminal PID 7944 were preserved. This was one Service
  restart, not a Worker or terminal restart.
- Management contract probes run as the authorized LocalSystem control identity
  returned structured `TIMEOUT` in 2,015 ms when no request was sent and
  `UNSUPPORTED_OPERATION` for `service.restart`; neither performed a trading
  action or restarted the Service. The temporary scheduled task was removed.
- The installed Pipeline #84 artifact still returned `worker_session_id: null`
  after the Service restart. The source correction is committed as
  `a5b8a6f4f872af019450e9f94100edda41083899`; it exposes the validated Worker
  session number and has a regression test. Pipeline #85's Windows tests and
  WPF Management tests passed, but its two build jobs failed because the
  configured `package-mirror.liara.ir` endpoint timed out while fetching Pillow.
  Documentation follow-up Pipeline #86 passed Windows tests, WPF Management
  tests, and Desktop package verification, but Linux tests failed before test
  execution when the same endpoint timed out fetching `Pillow==12.3.0`; the
  build and Installer stages were consequently skipped. Pipeline #87 repeated
  that same failure; Windows tests, WPF Management, and Desktop package
  verification passed, while build and Installer stages were skipped. Job #894
  shows five connection timeouts to `package-mirror.liara.ir` followed by “No
  matching distribution found” before pytest ran. No replacement Installer was
  produced, and no CI source, package source, or quality gate was changed.
  Therefore this correction has **not** been validated in a Windows binary.
- After the operator powered the dedicated VMs back on, a fresh read-only audit
  at 22:01Z confirmed Windows 10 Pro 19045 x64, active `MT5RuntimeUser` Session
  1, Service Automatic/LocalSystem in Session 0, Worker task Running, and the
  preserved runtime configuration (`ControlPrincipal=SYSTEM`, existing
  `RuntimePrincipal`, terminal path and pipe). Worker PID 6276 brought up the
  existing terminal as PID 7308 under Session 1; Worker PID 6276 is its parent.
  Service PID 2940 and Agent packaged parent/child 3560/3696 were in Session 0.
  An authorized Admin `status.get` request returned fresh Worker-ready and
  MT5-connected health; the installed binary still returned
  `worker_session_id: null`. No credentials, accounts, profiles or trading
  data were queried.
- Post-boot integrated soak ran from 22:01:59.188Z to 22:17:33.039Z: **32/32**
  authorized Management samples were `FRESH`, Worker-ready and `MT5_CONNECTED`
  with zero probe/health errors over 15m34s. Latency was 25.56–58.01 ms
  (median 25.99 ms; p95 57.23 ms). Service PID 2940 and Agent PIDs 3560/3696
  remained in Session 0; Worker PID 6276 and terminal PID 7308 remained in
  Session 1, both owned by `MT5RuntimeUser`, with no duplicate Worker or
  terminal observed. During the interval, Worker CPU rose 0.203→0.562 s and
  working set ranged 6.22–19.62 MiB; terminal CPU rose 7.516→10.547 s and
  working set ranged 16.19–159.25 MiB; Service CPU remained 0.078 s and
  working set ranged 17.70–18.39 MiB. Agent child CPU rose 0.062→0.094 s and
  its working set ranged 25.55–25.59 MiB. This separate post-boot soak
  preserved the previous samples and summary.
- No account identifier, balance, order, quote, credentials or secrets were
  requested. Trading capability remains `UNSUPPORTED`; no trade was executed.

## Events and limits

In the final audit after Service restart, two informational MT5Agent Application
events were found; no .NET Runtime, Application Error, Service Control Manager
failure or MT5Agent error event was found in that review window. Earlier
post-install/reconfiguration review found one informational MT5Agent event and
one informational Service Control Manager event. Agent logs used fixed
messages and redacted caller SIDs. The final audit also confirmed no Installer
process was active, the Worker task remained Running, and Service recovery
settings still included 5 s/15 s restart actions plus non-crash failures
enabled.

Windows 11/Server compatibility, RDP disconnect/logoff, WPF UI behavior, and a
separate Worker-unavailable injection remain **NOT TESTED**. During the earlier
supported Worker API shutdown/restart, MT5 stayed running and had CIM ParentPid
6852 (the prior Worker), even though replacement Worker PID 7032 reconnected;
the terminal was intentionally not terminated to preserve the active session.
After the normal machine boot, the current terminal PID 7308 was a child of the
current Worker PID 6276. The local health-reporting fix is not present in the
installed Pipeline #84 binary. Do not use this report as release approval.
