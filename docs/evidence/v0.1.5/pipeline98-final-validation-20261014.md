# MT5Agent v0.1.5 — Pipeline #98 final Windows validation

**Outcome: PASS for the tested Windows 10 v0.1.5 internal candidate; READY FOR RELEASE PREPARATION.** This is not public-release approval. No trade was placed, no MT5 account/profile/credential was changed, and no merge/tag/release was made.

## Identity and artifact provenance

| Field | Value |
|---|---|
| Host | `win10-mt5-runner`, Windows hostname `WIN10-MT5-RUNNE` |
| OS tested | Windows 10 Pro x64, build 19045 |
| Branch / source commit | `feat/v0.1.5-desktop-integration` / `54f47a6dad8541984b3930051cb6610f85bb95cc` |
| Pipeline | #98, 14/14 jobs passed |
| Runtime smoke | Job #1055, `smoke:mt5-runtime`, PASS |
| Installer build / verify | Job #1058 / #1059, PASS |
| Installer | `MT5Agent-Setup-v0.1.5-windows-x64.exe`, 22,457,638 bytes |
| Installer SHA-256 | `409d930b46d16b17d546a1dd89a609d05d53447ecf12d4ce180fcf4e898320d4` |
| Manifest / sidecar | Both agree with the installer and source commit; verification status PASS |
| Signature | Unsigned internal artifact; public distribution is prohibited |

Pipeline #98's 14 passing jobs were: #1046 `validate:windows`, #1047
`desktop:build-package`, #1048 `test:linux`, #1049 `test:windows`, #1050
`test:wpf-management`, #1051 `build:windows`, #1052 `worker:build`, #1053
`smoke:invalid-configuration`, #1054 `smoke:control-plane`, #1055
`smoke:mt5-runtime`, #1056 `desktop:package-verify`, #1057 `package:windows`,
#1058 `installer:build`, and #1059 `installer:verify`.

## Installation record

The exact verified Pipeline #98 installer was transferred to the integration
VM and its SHA-256 was checked there before execution. Two initial launches
exited with code 5 because the existing hidden-to-tray Desktop process held an
installed file open. The first invocation also used `/NOCLOSEAPPLICATIONS`,
which prevents Inno Setup from closing applications; the second could not
close the hidden tray process through Restart Manager because it had no visible
main window. These were file-lock conditions, not an Installer or Service
configuration defect.

The old Desktop PID 4292 was identified by its exact installed path, owner,
Session 1, process state, and unchanged user preference before it was closed.
The original preference file was backed up and its SHA-256 was verified after
restoration. Worker and MT5 were not stopped. After the Desktop lock was
cleared, the exact same verified artifact installed successfully:

| Field | Value |
|---|---|
| Successful Installer PID | 5648 |
| Exit code | 0 |
| Start / end | `2026-10-13T23:35:05.6197979Z` / `2026-10-13T23:35:11.6821545Z` |
| Duration | 6.062 seconds |
| Arguments | `/VERYSILENT /SUPPRESSMSGBOXES /SP- /NORESTART /LOG=<absolute path>` |
| Installer log | `C:\MT5Agent-Test\Evidence\Final-RC-Pipeline98-20261013T232744Z\installer-pipeline98-final.log` |
| Process receipt | `...\installer-pipeline98-final-receipt.json` |

The installed component manifest paths are source/staging-relative. Inno Setup
maps the three `Support/` files to `{app}\maintenance`; checking those at the
product root initially produced a path-only false mismatch. The corrected
comparison used the actual installer destinations. All nine files match the
Pipeline #98 manifest by size and SHA-256:

| Installed path relative to `C:\Program Files\MT5Agent` | SHA-256 |
|---|---|
| `Agent/MT5Agent-v0.1.3.exe` | `27782d1a53d650b3a5389346c79ad21f7a177d74903dce88b1898ba9396c8ca5` |
| `Desktop/MT5Agent.Desktop.exe` | `2d11ffe63e66cb1858c33e7c06b5b1d4fb732873966347f38c1d7c825700f832` |
| `Service/MT5Agent.Service.exe` | `3d84e1b1fe033ec3daa8b3b03bc406afe0859f8d820c1f815572c51c87217cf5` |
| `maintenance/Install-MT5AgentService.ps1` | `8c4aa147302a8fd8a8d4926b2dcdb42f733ecc0cd5b95f3453a3c782a5f3accd` |
| `maintenance/Save-MT5AgentUserSettings.ps1` | `a5325371914b64dde60ad1f2404804e8002aa1697c36d764f844d1f0b66f1051` |
| `maintenance/Set-MT5RuntimeConfiguration.ps1` | `1b3b0722cf5125b699cf53dbcfd8d018d4f4dae1e461504fb7c228b736950f63` |
| `Worker/MT5AgentWorker-v0.1.3.exe` | `2bce8e992b67acb38f9033ae39af227c6b1bce9be8dc91373f78009062176d09` |
| `Worker/Register-PackagedMT5Worker.ps1` | `b52c33585c22f340deb24b4fb27f595ff772a43fa8dcbd6206880f572fcc09b1` |
| `Worker/Unregister-PackagedMT5Worker.ps1` | `102d8b70fd98b8c1c218fae400fd5ed0247adb7650a8bb1782cc2a58907618d5` |

## Security and process topology

Runtime policy remained unchanged:

- `ControlPrincipal=NT AUTHORITY\SYSTEM`, SID `S-1-5-18`.
- `RuntimePrincipal=WIN10-MT5-RUNNE\MT5RuntimeUser`, SID
  `S-1-5-21-2457279486-2650524583-4089100399-1003`.
- Worker pipe: `\\.\pipe\MT5Agent.Runtime.v1`.
- MT5 terminal: `C:\Program Files\MetaTrader 5\terminal64.exe`.
- Existing MT5 profile path was inspected and left untouched.
- No Administrator ACE was added to the Worker pipe; no authentication or
  security policy was weakened.

After the controlled Service restart, the current process inventory showed:

| Component | PID(s) | Session | Identity / evidence |
|---|---:|---:|---|
| Service host | 3560 | 0 | LocalSystem; Automatic; Running |
| Agent process tree | 3572, 3364 | 0 | LocalSystem; installed Agent path |
| Worker bootstrap / child | 4332, 6276 | 1 | `MT5RuntimeUser`; single Worker process tree |
| MT5 terminal | 6168 | 1 | `MT5RuntimeUser`; existing terminal |
| WPF Desktop tray process | 6032 | 1 | `MT5RuntimeUser`; installed Desktop executable |

The Service was confirmed `RUNNING`, `AUTO_START`, LocalSystem, with Recovery
actions for restart after 5 and 15 seconds and the non-crash failure flag read
back as `TRUE`. After restart the Service and Agent PIDs changed, but the
Worker and MT5 PIDs were preserved. A later process inventory found no
leftover `RuntimeSmoke`, Management smoke, or probe scheduled tasks.

### CI identity boundary

The CI runner itself is Administrator and cannot directly authenticate to the
Worker pipe. Job #1055 used a one-shot protected Scheduled Task to execute the
fixed, hash-validated read-only test as LocalSystem in Session 0. The test
preserved the configured ControlPrincipal and RuntimePrincipal separation,
validated source/build/test receipts and file ACLs, serialized access to the
shared MT5 runtime, applied bounded timeouts, and removed only its own task and
stage. It reported a successful runtime round trip (104 ms in the captured CI
receipt). Administrator access to the Worker pipe was denied as expected.

For installed Management IPC, an authorized Administrator caller succeeded.
An attempted Management call from the unlisted `MT5RuntimeUser` in Session 1
returned `ACCESS_DENIED`. The allowed-SID list was not changed.

## Live health and stability

Installed Management Health after installation and again after the controlled
Service restart returned `AGENT_RUNNING`, `WORKER_READY`, `MT5_CONNECTED`,
`FRESH`, `stale=false`, protocol 1, and `worker_session_id=1`. The reported
Session ID matched the actual Windows Session ID of the authenticated Worker.
The underlying correction validates the authenticated Worker identity and
does not accept a caller-injected health Session ID.

A clean soak ran from `2026-10-13T23:52:13.5066176Z` to
`2026-10-14T00:07:14.5048552Z` (901 seconds), with 31 samples about 30 seconds
apart:

- Health and process topology: 31/31 pass; zero failures.
- MT5: `CONNECTED` and health `FRESH` for every sample.
- Worker Session ID: 1 for all samples.
- Process identity/topology: stable; no duplicate Worker/terminal and no
  unexpected restart.
- Management latency: minimum 25 ms, median 26 ms, p95 85 ms, maximum 93 ms.
- Aggregate sampled CPU for Service/Agent/Worker/MT5 processes: average
  0.338%, maximum 0.696%.
- Aggregate sampled working set: 67.08–82.81 MiB; private memory
  185.77–186.28 MiB.
- No trading operation was sent.

The earlier soak interval contained one `MT5_DISCONNECTED` sample when the
Product Owner intentionally restarted MetaTrader 5 after it requested a
restart to apply newly received price data. That restart was operator-directed
and is **not an MT5Agent defect**. The interrupted interval is preserved, not
counted as the clean soak. The subsequent 901-second interval began after MT5
reconnected and passed without a failure.

The controlled Service restart completed in about 3.44 seconds, returned to
Running, and retained the Worker and MT5 PIDs. Fresh health immediately after
restart was connected and reported Worker Session 1.

## Desktop, logs, and evidence location

The installed WPF Desktop was launched visibly in Session 1 as
`MT5RuntimeUser`, PID 6032, with the manifest-matching executable hash. Closing
the window followed the configured close-to-tray behavior; the Desktop process
remained in the tray, while Service, Worker, MT5, and Management health
continued. This was a basic launch/close-to-tray smoke, not a complete
accessibility, high-DPI, settings, or keyboard-navigation audit.

The evidence directory on the Windows VM is:

`C:\MT5Agent-Test\Evidence\Final-RC-Pipeline98-20261013T232744Z\`

It includes the initial system state, artifact/manifest/sidecar, Installer
logs and receipts, Service configuration/recovery, process/security topology,
Management authorization probes, WPF smoke, soak samples/summary, controlled
restart, and Application/SCM event exports. Application/.NET error review
found no relevant application crash events in the observed window; log review
found no secret-like values. The product was left installed and healthy.

## Acceptance matrix and remaining scope

| Criterion | Result | Scope |
|---|---|---|
| CI and live runtime smoke | **PASS** | Pipeline #98, 14/14; protected SYSTEM smoke Job #1055 |
| Exact artifact integrity | **PASS** | Manifest, sidecar, Ubuntu and Windows hash; 9/9 installed files |
| Installation | **PASS** | PID 5648, exit 0 |
| Service and Agent in Session 0 | **PASS** | LocalSystem; Running/Automatic; observed after restart |
| Worker and MT5 in interactive Session 1 | **PASS** | `MT5RuntimeUser`; current observed PIDs above |
| Authenticated IPC and denial cases | **PASS for tested callers** | SYSTEM runtime caller succeeds; Administrator Worker-pipe and RuntimeUser Management access denied |
| Live Session ID health | **PASS** | Installed Management Health reports Session 1 matching the real process |
| 15-minute clean stability soak | **PASS** | 31/31 samples over 901 seconds |
| Basic WPF behavior | **PASS** | Visible launch, close-to-tray, Service/Worker/MT5 remain active |
| Worker unavailable/recovery, RDP/logoff, reboot | **NOT TESTED** | Not exercised to avoid disrupting the existing interactive MT5 session |
| Windows 11 / Windows Server | **NOT TESTED** | No target evidence |
| Full WPF accessibility/high-DPI coverage | **NOT TESTED** | Only basic interactive smoke performed |
| Code signing/public release | **BLOCKED** | Artifact unsigned and internal-only |

The installer verifier's `install_smoke=DEFERRED` field means its isolated
packaging environment did not install the product; it is superseded for this
artifact's deployment claim by the separately captured real installation and
runtime evidence above. CI success is not treated as proof of operational
deployment.

## Git state at validation

The tested executable source and artifact correspond to commit
`54f47a6dad8541984b3930051cb6610f85bb95cc` on
`feat/v0.1.5-desktop-integration`. The working tree was clean for tracked files
before this evidence/documentation update. An unrelated untracked `.trigger-tree/`
directory was preserved and not included.
