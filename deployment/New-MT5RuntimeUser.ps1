[CmdletBinding()]
param(
    [string] $UserName = 'MT5RuntimeUser'
)

$ErrorActionPreference = 'Stop'

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this provisioning script from an elevated PowerShell session.'
}
if (Get-LocalUser -Name $UserName -ErrorAction SilentlyContinue) {
    throw "Local account already exists; inspect it before making changes: $UserName"
}

# ReadHost collects the password as a SecureString. It is never an argument,
# written to disk, emitted to output, or included in a log.
$securePassword = Read-Host "Set a unique password for local account $UserName" -AsSecureString
if ($securePassword.Length -lt 1) {
    $securePassword.Dispose()
    throw 'An empty password is not accepted.'
}
try {
    $user = New-LocalUser `
        -Name $UserName `
        -FullName 'MT5 Runtime User' `
        -Description 'Standard local identity for the interactive MT5 runtime.' `
        -Password $securePassword
    $usersGroup = Get-LocalGroup -SID 'S-1-5-32-545'
    $usersMembers = Get-LocalGroupMember -Group $usersGroup -ErrorAction SilentlyContinue
    if ($usersMembers.SID -notcontains $user.SID) {
        Add-LocalGroupMember -Group $usersGroup -Member $user
    }
} finally {
    $securePassword.Dispose()
}

$created = Get-LocalUser -Name $UserName
if (-not $created.Enabled) { throw 'Runtime user was created disabled.' }
$admins = Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction Stop
$rdpUsers = Get-LocalGroupMember -SID 'S-1-5-32-555' -ErrorAction SilentlyContinue
if ($admins.SID -contains $created.SID -or $rdpUsers.SID -contains $created.SID) {
    throw 'Runtime user unexpectedly belongs to a privileged or Remote Desktop group.'
}
$runnerGroups = Get-LocalGroup | Where-Object { $_.Name -match 'gitlab|runner' }
foreach ($group in $runnerGroups) {
    $members = Get-LocalGroupMember -Group $group -ErrorAction SilentlyContinue
    if ($members.SID -contains $created.SID) {
        throw "Runtime user unexpectedly belongs to runner-related group $($group.Name)."
    }
}
Write-Output "Created standard local runtime account $env:COMPUTERNAME\$UserName."
Write-Output 'No password was displayed or stored by this script.'
