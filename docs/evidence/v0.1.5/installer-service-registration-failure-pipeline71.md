# Pipeline 71 live installer failure — service registration

## Observed evidence

- The approved Pipeline 71 installer passed the expected SHA-256 check on
  Ubuntu and Windows and completed file deployment on Windows 10 x64.
- Inno Setup recorded process exit code `1` for
  `Install-MT5AgentService.ps1 -Action Install`, but the installer process
  returned `0` and finalized its Uninstall entry.
- Windows PowerShell Operational Event 4100 recorded the uncaught
  `SERVICE_CREATE_FAILED` error from the service installation script.
- Read-only diagnostics confirmed Windows PowerShell `5.1.19041.2673` in a
  64-bit process, the expected Program Files root, the service host and script
  files, `sc.exe`, and an elevated Administrator context. The Management Pipe
  SID registry value written before service creation was present; the Service
  itself was absent.
- The former script discarded `sc.exe create` output with `Out-Null`, then
  threw the generic `SERVICE_CREATE_FAILED` error. The native SCM result and
  error text were therefore unavailable in Setup or the PowerShell event.

## Root cause and certainty

The failing step is established: the old `sc.exe create MT5Agent ...` call
returned a nonzero result. The exact Win32/SCM reason cannot be reconstructed
from the surviving evidence because the command output was discarded. The
current evidence does not prove that quoting, ACLs, PowerShell policy, or the
service-host path was the underlying cause; those checks did not identify a
problem. The unattended installer falsely reported success because its
`[Run]` entry logged the child exit code without converting it into a setup
failure.

## Corrective changes

- Use the Windows PowerShell Service cmdlets for Service creation/configuration
  and capture errors with error ID, category, message, script line and stack in
  the protected ProgramData service log.
- Verify the service binary path, LocalSystem account, automatic start mode and
  Running state before returning success.
- Preserve an existing matching service and Management Pipe allowlist on a
  partial-install retry; refuse a name/path/account collision. If this run
  created a new service and later installation fails, remove only that exact
  newly created service and restore the prior allowlist.
- Route required Service and configured Worker setup through an Inno Setup
  `Exec` helper that checks the child exit code, reports the failure, and sets
  Inno's `GetCustomSetupExitCode` result so both interactive and silent setup
  finish with a nonzero process exit code.
- On post-install failure, keep the installed files and Uninstall entry for
  repair/uninstall. Automatic deletion is avoided because Setup has finalized
  its uninstall record and must not erase user configuration, logs, or MT5 data.

## Validation boundary

The PowerShell 5.1 tests simulate Service API success, SCM failure, and retry
from a stopped partial state without registering a Service on the shared CI
runner or this VM. Inno smoke tests exercise zero and nonzero child exit codes
in `/SILENT` and `/VERYSILENT`. A live Service registration test remains for a
separate disposable Windows VM run; this VM remains unchanged by diagnostics.
