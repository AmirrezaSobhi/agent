[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$InstallRoot)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($InstallRoot)
$expectedRoot = [IO.Path]::GetFullPath((Join-Path $env:ProgramFiles 'MT5Agent'))
if (-not [string]::Equals($root, $expectedRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'INSTALL_ROOT_MUST_BE_PROTECTED_PROGRAM_FILES_PATH' }
$worker = Join-Path $root 'Worker\MT5AgentWorker-v0.1.3.exe'
if (-not (Test-Path -LiteralPath $worker -PathType Leaf)) { throw 'BUNDLED_WORKER_EXECUTABLE_MISSING' }
$config = Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\MT5Agent\Runtime' -ErrorAction Stop
foreach ($name in @('RuntimePrincipal','ControlPrincipal','TerminalPath','ProfilePath','WorkerInstallPath','WorkerDataPath')) {
    if ([string]::IsNullOrWhiteSpace([string]$config.$name)) { throw "RUNTIME_CONFIGURATION_MISSING:$name" }
}
if ([IO.Path]::GetFullPath([string]$config.WorkerInstallPath) -ne [IO.Path]::GetFullPath((Join-Path $root 'Worker'))) {
    throw 'RUNTIME_WORKER_PATH_DOES_NOT_MATCH_INSTALLER_PAYLOAD'
}
$principalParts = ([string]$config.RuntimePrincipal) -split '\\', 2
if ($principalParts.Count -ne 2 -or $principalParts[0] -ne $env:COMPUTERNAME) { throw 'RUNTIME_PRINCIPAL_MUST_BE_LOCAL' }
$runtimeUser = Get-LocalUser -Name $principalParts[1] -ErrorAction Stop
if (-not $runtimeUser.Enabled) { throw 'RUNTIME_PRINCIPAL_DISABLED' }
$controlSid = ([Security.Principal.NTAccount]::new([string]$config.ControlPrincipal)).Translate([Security.Principal.SecurityIdentifier])
if ($runtimeUser.SID -eq $controlSid) { throw 'RUNTIME_AND_CONTROL_PRINCIPALS_MUST_BE_DISTINCT' }
$adminSids = @((Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction Stop).SID | ForEach-Object Value)
$rdpSids = @((Get-LocalGroupMember -SID 'S-1-5-32-555' -ErrorAction SilentlyContinue).SID | ForEach-Object Value)
if ($adminSids -contains $runtimeUser.SID.Value -or $rdpSids -contains $runtimeUser.SID.Value) { throw 'RUNTIME_PRINCIPAL_MUST_BE_STANDARD_USER' }
if (-not (Test-Path -LiteralPath ([string]$config.TerminalPath) -PathType Leaf) -or
    -not (Test-Path -LiteralPath ([string]$config.ProfilePath) -PathType Container)) { throw 'MT5_TERMINAL_OR_PROFILE_NOT_AVAILABLE' }
$taskName = 'MT5Agent Interactive MT5 Runtime Worker'
$action = New-ScheduledTaskAction -Execute $worker -WorkingDirectory (Split-Path -Parent $worker)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User ([string]$config.RuntimePrincipal)
$principal = New-ScheduledTaskPrincipal -UserId ([string]$config.RuntimePrincipal) -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force -Description 'Starts the bundled MT5Agent read-only Worker only in its configured interactive Windows session.' | Out-Null
Write-Output "Registered bundled Worker for $($config.RuntimePrincipal). No credentials were stored."
