[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $SourceRoot,

    [Parameter(Mandatory = $true)]
    [string] $RuntimePrincipal,

    [string] $Python311 = 'C:\Program Files\Python311\python.exe',

    [string] $InstallRoot = 'C:\ProgramData\MT5Agent\RuntimeWorker',

    [string] $Wheelhouse,

    [string] $TaskName = 'MT5 Agent Interactive Runtime Worker - MT5RuntimeUser',

    [switch] $UpdateExistingTask,

    [switch] $AllowPrivilegedLabPrincipal
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Python311 -PathType Leaf)) {
    throw "Python 3.11 executable not found: $Python311"
}
$sourceAgent = Join-Path (Resolve-Path -LiteralPath $SourceRoot) 'agent'
$requirements = Join-Path (Resolve-Path -LiteralPath $SourceRoot) 'requirements-mt5-worker.txt'
if (-not (Test-Path -LiteralPath $sourceAgent -PathType Container) -or
    -not (Test-Path -LiteralPath $requirements -PathType Leaf)) {
    throw 'SourceRoot must contain agent/ and requirements-mt5-worker.txt.'
}
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask -and -not $UpdateExistingTask) {
    throw "Task already exists; pass -UpdateExistingTask to update it: $TaskName"
}
$principalParts = $RuntimePrincipal -split '\\', 2
if ($principalParts.Count -ne 2 -or $principalParts[0] -ne $env:COMPUTERNAME) {
    throw 'RuntimePrincipal must be a local account in COMPUTERNAME\User form.'
}
$runtimeUser = Get-LocalUser -Name $principalParts[1] -ErrorAction SilentlyContinue
if (-not $runtimeUser -or -not $runtimeUser.Enabled) {
    throw "An enabled local runtime account is required: $RuntimePrincipal"
}
$adminSids = @((Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction Stop).SID | ForEach-Object { $_.Value })
$rdpSids = @((Get-LocalGroupMember -SID 'S-1-5-32-555' -ErrorAction SilentlyContinue).SID | ForEach-Object { $_.Value })
if (-not $AllowPrivilegedLabPrincipal -and
    ($adminSids -contains $runtimeUser.SID.Value -or $rdpSids -contains $runtimeUser.SID.Value)) {
    throw 'The runtime task account must not be an Administrator or Remote Desktop Users member.'
}
$runnerGroups = Get-LocalGroup | Where-Object { $_.Name -match 'gitlab|runner' }
foreach ($group in $runnerGroups) {
    $members = Get-LocalGroupMember -Group $group -ErrorAction SilentlyContinue
    if ($members.SID -contains $runtimeUser.SID) {
        throw "The runtime task account belongs to runner-related group $($group.Name)."
    }
}
$runtimeConfiguration = Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\MT5Agent\Runtime' -ErrorAction Stop
if (-not [string]::Equals([string]$runtimeConfiguration.RuntimePrincipal, $RuntimePrincipal, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'RuntimePrincipal does not match HKLM\SOFTWARE\MT5Agent\Runtime configuration.'
}
if (-not [string]::Equals([string]$runtimeConfiguration.WorkerInstallPath, [IO.Path]::GetFullPath($InstallRoot), [StringComparison]::OrdinalIgnoreCase)) {
    throw 'InstallRoot does not match configured WorkerInstallPath.'
}

New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null

# Lock down the new/empty root before copying executable code into it.
$configurationScript = Join-Path (Split-Path -Parent $PSCommandPath) 'Set-MT5RuntimeConfiguration.ps1'
$configurationArguments = @{
    RuntimePrincipal = $RuntimePrincipal
    ControlPrincipal = [string]$runtimeConfiguration.ControlPrincipal
    TerminalPath = [string]$runtimeConfiguration.TerminalPath
    ProfilePath = [string]$runtimeConfiguration.ProfilePath
    WorkerInstallPath = $InstallRoot
    WorkerDataPath = [string]$runtimeConfiguration.WorkerDataPath
    PipeName = [string]$runtimeConfiguration.PipeName
}
if ($AllowPrivilegedLabPrincipal) { $configurationArguments.AllowPrivilegedLabPrincipal = $true }
& $configurationScript @configurationArguments

Copy-Item -LiteralPath $sourceAgent -Destination $InstallRoot -Recurse -Force
Copy-Item -LiteralPath $requirements -Destination (Join-Path $InstallRoot 'requirements-mt5-worker.txt') -Force

$python = Join-Path $InstallRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    & $Python311 -m venv (Join-Path $InstallRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw "Python venv creation failed with exit code $LASTEXITCODE" }
}
$pipArguments = @('-m', 'pip', 'install', '--disable-pip-version-check')
if ($Wheelhouse) {
    if (-not (Test-Path -LiteralPath $Wheelhouse -PathType Container)) {
        throw "Wheelhouse directory not found: $Wheelhouse"
    }
    $pipArguments += @('--no-index', '--find-links', $Wheelhouse)
}
$pipArguments += @('--requirement', (Join-Path $InstallRoot 'requirements-mt5-worker.txt'))
& $python @pipArguments
if ($LASTEXITCODE -ne 0) { throw "Worker dependency installation failed with exit code $LASTEXITCODE" }

# The user task receives an interactive token only after that user logs on.
# No password or reusable credential is supplied to Task Scheduler.
$action = New-ScheduledTaskAction `
    -Execute $python `
    -Argument '-B -m agent.infrastructure.interactive_mt5_worker' `
    -WorkingDirectory $InstallRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $RuntimePrincipal
$principal = New-ScheduledTaskPrincipal `
    -UserId $RuntimePrincipal `
    -LogonType Interactive `
    -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -DontStopOnIdleEnd `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Force `
    -Description 'Starts the local MT5 Worker inside the designated user session after logon.' | Out-Null

Write-Output "Registered interactive logon task '$TaskName' for $RuntimePrincipal."
Write-Output "Worker: $python -B -m agent.infrastructure.interactive_mt5_worker"
Write-Output "Working directory: $InstallRoot"
