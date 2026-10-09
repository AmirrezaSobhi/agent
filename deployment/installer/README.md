# Unified MT5Agent Windows Setup

The internal setup is a single Inno Setup 6.7.3 executable. Inno Setup was
selected because it emits one x64 Windows setup file, supports UAC, stable
upgrade/uninstall identity, shortcuts, repair/reinstall, and file rollback with
less bootstrapper code than WiX Burn. The build downloads a pinned version and
checks its Authenticode publisher before compiling. Inno's commercial-use
license must be resolved before commercial distribution.

The installer packages four built components: WPF Desktop, Python Agent
executable, a .NET Framework 4.8 Windows Service host, and a separately frozen
Python MT5 Worker executable. Python and the Worker dependency set are bundled;
the user does not install Python. MetaTrader 5 itself is never redistributed.

## Installation behavior

- Per-machine installation under Program Files; UAC is required for the real
  Windows Service and machine files. No permission is silently elevated.
- Service `MT5Agent` runs as LocalSystem because the existing Worker launcher
  requires Session 0 token/session APIs. The service starts only the fixed
  Agent executable below its protected install root and tracks that process
  tree in a kill-on-close Job Object. SCM's default ACL is kept.
- The Agent Management Pipe allowlist is seeded from the Windows SID that
  launched elevated Setup. Pipe ACL and token SID validation remain enforced;
  all other callers are denied by default.
- The Worker executable is installed independently and never starts in Session
  0. Its scheduled task must be registered for a preconfigured standard local
  Runtime Principal with a real interactive logon and matching MT5 terminal and
  profile configuration. No credentials are saved and Autologon is not enabled.
- Setup detects the conventional `Program Files\MetaTrader 5\terminal64.exe`
  location or accepts another terminal folder. That path is saved in the
  original non-elevated user's settings, even when UAC credentials came from a
  different administrator account. The profile path and Runtime Principal still need
  explicit provisioning before a live Worker task can safely be registered.
- The Service installer uses Windows PowerShell 5.1 `New-Service`, `Set-Service`,
  and `Start-Service` APIs instead of constructing `sc.exe create` arguments.
  It verifies the registered binary, LocalSystem identity, automatic start mode,
  and Running state. Service diagnostics are written to
  `%ProgramData%\MT5Agent\Logs\service-install.log`; exception message, error
  identifier, source line, and stack are recorded with credential-like values
  redacted.
- Service and configured Worker registration are required operations. Inno
  Setup checks their actual child-process exit codes and fails both interactive
  and silent installation if either operation fails. Its own setup log records
  the operation and exit code. Because these checks run after Inno has finalized
  the uninstall record, a failed operation intentionally leaves the application
  files and Uninstall entry available for diagnosis and repair/uninstall. Setup
  does not delete user configuration, logs, or MT5 data as an automatic rollback.
  Re-running installation is idempotent for a matching Service binary and
  preserves existing Management Pipe allowlist entries; a Service name/path or
  account collision is refused.
- Desktop preferences remain per-user. Setup does not modify account data,
  MT5 profiles, trading permissions, or credentials. Uninstall removes the
  MT5Agent service and application files but preserves configuration and logs.

If the Worker identity/configuration was provisioned separately, an elevated
administrator can register the bundled Worker task without installing Python:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  "C:\Program Files\MT5Agent\Worker\Register-PackagedMT5Worker.ps1" `
  -InstallRoot "C:\Program Files\MT5Agent"
```

For a fresh setup, first create or designate a standard local Runtime Principal
and a separate Control Principal. Sign in as the Runtime Principal once and
open MT5 so its profile directory and `origin.txt` exist. Then use the bundled
machine-configuration script from an elevated PowerShell session:

```powershell
$root = 'C:\Program Files\MT5Agent'
& "$root\maintenance\Set-MT5RuntimeConfiguration.ps1" `
  -RuntimePrincipal "$env:COMPUTERNAME\MT5RuntimeUser" `
  -ControlPrincipal "$env:COMPUTERNAME\MT5ControlUser" `
  -TerminalPath 'C:\Program Files\MetaTrader 5\terminal64.exe' `
  -ProfilePath 'C:\Users\MT5RuntimeUser\AppData\Roaming\MetaQuotes\Terminal\<instance>' `
  -WorkerInstallPath "$root\Worker"
& "$root\maintenance\Install-MT5AgentService.ps1" -Action Install -InstallRoot $root
& "$root\Worker\Register-PackagedMT5Worker.ps1" -InstallRoot $root
```

Replace the account names and paths with values verified on that machine. The
configuration script checks `origin.txt`, standard-user membership, pipe name,
and protected file/registry ACLs. Worker registration fails closed unless the
account is enabled, distinct from Control Principal, non-administrative, and
the configured terminal/profile are valid. Sign in interactively as that
account for the Worker to start. No credentials are stored; the Installer does
not create the account or enable Autologon.

## CI artifact

`installer:build` publishes:

- `dist/installer/MT5Agent-Setup-v0.1.5-windows-x64.exe`
- `dist/installer/MT5Agent-Setup-v0.1.5-windows-x64.manifest.json`
- `dist/installer/MT5Agent-Setup-v0.1.5-windows-x64.sha256`

Download all three from the `installer:build` job artifacts in the develop
pipeline. The downstream `installer:verify` job consumes those exact artifacts
and checks commit/pipeline/build provenance, required payload records, and the
SHA-256. Before publishing the package, `installer:build` compiles a disposable
smoke setup from the same `MT5AgentWizard.issinc` used by the product and runs
it with `/SILENT` and `/VERYSILENT`. The test requires exit code zero, an Inno
log, and an initialization marker in each mode. Its setup has no product
payload, Service commands, or MT5 actions and writes only under a unique
temporary directory. Interactive UI behavior is not exercised by this
noninteractive CI check. Setup is unsigned and internal only. The CI verifier
does not install the product or remove a Service on its persistent runner.

## Validation and limitations

- The MT5 path Wizard creates its `InputDirWizardPage` field with `Add` before
  reading `Values[0]`. Silent runs skip the UI page entirely and safely detect
  only the conventional MT5 path if its executable exists. The same shared
  `MT5AgentWizard.issinc` is used by the product and CI smoke setup.
- Windows CI exercises mocked Service creation success, a simulated SCM failure
  with detailed log output, and retry from a stopped partially installed Service.
  A separate Inno smoke setup verifies required-operation exit-code handling in
  `/SILENT` and `/VERYSILENT`. It does not register a real Service on the shared
  build runner; live Service installation remains a disposable-VM validation.
- Windows 10 x64 build and packaging are CI targets. A disposable Windows 10 VM
  was not available for clean install/upgrade/repair/uninstall validation, so
  live SCM lifecycle and installer installation remain deferred.
- Worker packaging is separate from Worker runtime activation. Runtime account,
  MT5 profile discovery and first interactive logon need a later guided setup
  page before the product can claim one-click operational readiness.
- Windows 11 and Windows Server 2022/2025 validation is `DEFERRED — PRODUCT
  OWNER VALIDATION`; Server requires Desktop Experience.
- No public release, tag, staging/main merge, signing, real trade, MT5 installer,
  account creation, or autologon is part of this internal package.
