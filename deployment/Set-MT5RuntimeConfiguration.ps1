[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $RuntimePrincipal,
    [Parameter(Mandatory = $true)] [string] $ControlPrincipal,
    [Parameter(Mandatory = $true)] [string] $TerminalPath,
    [Parameter(Mandatory = $true)] [string] $ProfilePath,
    [string] $WorkerInstallPath = 'C:\ProgramData\MT5Agent\RuntimeWorker',
    [string] $WorkerDataPath = '%LOCALAPPDATA%\MT5Agent\RuntimeWorker',
    [string] $PipeName = '\\.\pipe\MT5Agent.Runtime.v1',
    [switch] $AllowPrivilegedLabPrincipal
)

$ErrorActionPreference = 'Stop'
$registryPath = 'HKLM:\SOFTWARE\MT5Agent\Runtime'

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$currentPrincipal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this configuration script from an elevated PowerShell session.'
}
if (-not $PipeName.StartsWith('\\.\pipe\') -or $PipeName.Contains('..')) {
    throw 'PipeName must be a local named-pipe path.'
}
if (-not (Test-Path -LiteralPath $TerminalPath -PathType Leaf)) {
    throw "MT5 terminal executable not found: $TerminalPath"
}
if (-not (Test-Path -LiteralPath $ProfilePath -PathType Container)) {
    throw "MT5 profile directory not found: $ProfilePath"
}
if (-not (Test-Path -LiteralPath $WorkerInstallPath -PathType Container)) {
    throw "Worker installation directory not found: $WorkerInstallPath"
}

$terminal = [IO.Path]::GetFullPath($TerminalPath)
$profile = [IO.Path]::GetFullPath($ProfilePath)
$workerInstall = [IO.Path]::GetFullPath($WorkerInstallPath)
$originFile = Join-Path $profile 'origin.txt'
if (-not (Test-Path -LiteralPath $originFile -PathType Leaf)) {
    throw 'MT5 profile must contain origin.txt before it can be configured.'
}
$originBytes = [IO.File]::ReadAllBytes($originFile)
$originEncoding = if ($originBytes.Length -ge 2 -and $originBytes[0] -eq 0xFF -and $originBytes[1] -eq 0xFE) {
    [Text.Encoding]::Unicode
} else {
    [Text.UTF8Encoding]::new($true)
}
$originText = $originEncoding.GetString($originBytes).Trim().TrimStart([char]0xFEFF, [char]0xFFFE)
$origin = [IO.Path]::GetFullPath($originText)
if (-not [string]::Equals($origin, (Split-Path -Parent $terminal), [StringComparison]::OrdinalIgnoreCase)) {
    throw 'MT5 profile origin does not match the selected terminal installation.'
}

$runtimeName = ($RuntimePrincipal -split '\\')[-1]
if ($RuntimePrincipal -notlike "$env:COMPUTERNAME\*") {
    throw 'RuntimePrincipal must name a local account on this machine.'
}
$runtimeUser = Get-LocalUser -Name $runtimeName -ErrorAction SilentlyContinue
if (-not $runtimeUser) { throw "Runtime account does not exist: $RuntimePrincipal" }
$adminSids = @((Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction Stop).SID | ForEach-Object { $_.Value })
$rdpSids = @((Get-LocalGroupMember -SID 'S-1-5-32-555' -ErrorAction SilentlyContinue).SID | ForEach-Object { $_.Value })
if (-not $AllowPrivilegedLabPrincipal -and
    ($adminSids -contains $runtimeUser.SID.Value -or $rdpSids -contains $runtimeUser.SID.Value)) {
    throw 'RuntimePrincipal must not be an Administrator or Remote Desktop Users member.'
}
$runnerGroups = Get-LocalGroup | Where-Object { $_.Name -match 'gitlab|runner' }
foreach ($group in $runnerGroups) {
    $members = Get-LocalGroupMember -Group $group -ErrorAction SilentlyContinue
    if ($members.SID -contains $runtimeUser.SID) {
        throw "RuntimePrincipal belongs to runner-related group $($group.Name)."
    }
}

$runtimeSid = $runtimeUser.SID
$controlSid = ([Security.Principal.NTAccount]::new($ControlPrincipal)).Translate([Security.Principal.SecurityIdentifier])
$systemSid = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$adminsSid = [Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')

# Existing Worker descendants were inspected before use of this script. Refuse
# to change the root if a child has a protected ACL that would not inherit it.
$protectedChildren = Get-ChildItem -LiteralPath $WorkerInstallPath -Force -Recurse -ErrorAction Stop |
    Where-Object { (Get-Acl -LiteralPath $_.FullName).AreAccessRulesProtected }
if ($protectedChildren) {
    throw 'Worker installation contains protected child ACLs; inspect and normalize them explicitly first.'
}
$fileAcl = Get-Acl -LiteralPath $WorkerInstallPath
$fileAcl.SetAccessRuleProtection($true, $false)
$fileRules = @(
    [Security.AccessControl.FileSystemAccessRule]::new($systemSid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'),
    [Security.AccessControl.FileSystemAccessRule]::new($adminsSid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'),
    [Security.AccessControl.FileSystemAccessRule]::new($runtimeSid, 'ReadAndExecute', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
)
foreach ($rule in @($fileAcl.Access)) { [void] $fileAcl.RemoveAccessRuleAll($rule) }
foreach ($rule in $fileRules) { $fileAcl.AddAccessRule($rule) }
Set-Acl -LiteralPath $WorkerInstallPath -AclObject $fileAcl

New-Item -Path $registryPath -Force | Out-Null
foreach ($setting in @{
    RuntimePrincipal = $RuntimePrincipal
    ControlPrincipal = $ControlPrincipal
    TerminalPath = $terminal
    ProfilePath = $profile
    WorkerInstallPath = $workerInstall
    WorkerDataPath = $WorkerDataPath
    PipeName = $PipeName
}.GetEnumerator()) {
    New-ItemProperty -LiteralPath $registryPath -Name $setting.Key -Value $setting.Value -PropertyType String -Force | Out-Null
}

$registryKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(
    'SOFTWARE\MT5Agent\Runtime',
    [Microsoft.Win32.RegistryKeyPermissionCheck]::ReadWriteSubTree,
    [Security.AccessControl.RegistryRights]::FullControl
)
if (-not $registryKey) { throw 'Could not open the MT5 runtime registry key for ACL configuration.' }
$registryAcl = $registryKey.GetAccessControl()
$registryAcl.SetAccessRuleProtection($true, $false)
$registryRules = @(
    [Security.AccessControl.RegistryAccessRule]::new($systemSid, 'FullControl', 'ContainerInherit', 'None', 'Allow'),
    [Security.AccessControl.RegistryAccessRule]::new($adminsSid, 'FullControl', 'ContainerInherit', 'None', 'Allow'),
    [Security.AccessControl.RegistryAccessRule]::new($runtimeSid, 'ReadKey', 'ContainerInherit', 'None', 'Allow'),
    [Security.AccessControl.RegistryAccessRule]::new($controlSid, 'ReadKey', 'ContainerInherit', 'None', 'Allow')
)
foreach ($rule in @($registryAcl.Access)) { [void] $registryAcl.RemoveAccessRuleAll($rule) }
foreach ($rule in $registryRules) { $registryAcl.AddAccessRule($rule) }
$registryKey.SetAccessControl($registryAcl)
$registryKey.Close()

Write-Output "Configured machine-local MT5 runtime policy for $RuntimePrincipal."
Write-Output "Worker installation: $workerInstall (runtime read/execute only)."
Write-Output "Worker mutable data: $WorkerDataPath (expanded inside that user's profile)."
