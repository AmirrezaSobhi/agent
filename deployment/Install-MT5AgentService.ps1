[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateSet('Install','Uninstall','Stop')][string]$Action,
      [Parameter(Mandatory=$true)][string]$InstallRoot)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($InstallRoot).TrimEnd('\') + '\'
$expectedRoot = [IO.Path]::GetFullPath((Join-Path $env:ProgramFiles 'MT5Agent')).TrimEnd('\') + '\'
if (-not [string]::Equals($root, $expectedRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'INSTALL_ROOT_MUST_BE_THE_PROTECTED_PROGRAM_FILES_MT5AGENT_DIRECTORY'
}
$serviceName = 'MT5Agent'
$serviceExe = [IO.Path]::GetFullPath((Join-Path $root 'Service\MT5Agent.Service.exe'))
$sc = Join-Path $env:SystemRoot 'System32\sc.exe'
if (-not (Test-Path -LiteralPath $sc -PathType Leaf)) { throw 'SCM_TOOL_UNAVAILABLE' }
$service = Get-CimInstance Win32_Service -Filter "Name='$serviceName'" -ErrorAction SilentlyContinue
if ($Action -in @('Uninstall','Stop')) {
    if (-not $service) { exit 0 }
    $existing = [IO.Path]::GetFullPath([string]$service.PathName.Trim('"'))
    if (-not $existing.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'REFUSING_TO_REMOVE_SERVICE_OUTSIDE_MT5AGENT_INSTALL_ROOT'
    }
    if ($service.State -eq 'Running') { & $sc stop $serviceName | Out-Null; if ($LASTEXITCODE -gt 1) { throw 'SERVICE_STOP_FAILED' } }
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    do { Start-Sleep -Milliseconds 250; $service = Get-CimInstance Win32_Service -Filter "Name='$serviceName'" -ErrorAction SilentlyContinue } while ($service -and $service.State -ne 'Stopped' -and [DateTime]::UtcNow -lt $deadline)
    if ($service -and $service.State -ne 'Stopped') { throw 'SERVICE_DID_NOT_STOP_WITHIN_TIMEOUT' }
    if ($Action -eq 'Stop') { exit 0 }
    & $sc delete $serviceName | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'SERVICE_DELETE_FAILED' }
    exit 0
}
if (-not (Test-Path -LiteralPath $serviceExe -PathType Leaf)) { throw 'SERVICE_HOST_BINARY_MISSING' }
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
if ($sid -notmatch '^S-1-') { throw 'CONTROL_PRINCIPAL_SID_UNAVAILABLE' }
$keyPath = 'HKLM:\SOFTWARE\MT5Agent\Management'
New-Item -Path $keyPath -Force | Out-Null
$management = Get-ItemProperty -LiteralPath $keyPath -Name AllowedUserSids -ErrorAction SilentlyContinue
$old = @()
if ($management -and $management.AllowedUserSids) { $old = @($management.AllowedUserSids | Where-Object { $_ }) }
$controlSids = @($sid)
$runtime = Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\MT5Agent\Runtime' -Name ControlPrincipal -ErrorAction SilentlyContinue
if ($runtime -and -not [string]::IsNullOrWhiteSpace([string]$runtime.ControlPrincipal)) {
    try {
        $controlIdentity = [Security.Principal.NTAccount]::new([string]$runtime.ControlPrincipal)
        $controlSids += $controlIdentity.Translate([Security.Principal.SecurityIdentifier]).Value
    } catch { throw 'CONFIGURED_CONTROL_PRINCIPAL_SID_RESOLUTION_FAILED' }
}
$old = @($old + $controlSids | Sort-Object -Unique)
New-ItemProperty -LiteralPath $keyPath -Name AllowedUserSids -PropertyType MultiString -Value $old -Force | Out-Null
if ($service) {
    $existing = [IO.Path]::GetFullPath([string]$service.PathName.Trim('"'))
    if (-not $existing.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) { throw 'SERVICE_NAME_COLLISION_REFUSED' }
    if ($service.State -eq 'Running') { & $sc stop $serviceName | Out-Null; if ($LASTEXITCODE -gt 1) { throw 'SERVICE_STOP_FAILED' } }
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    do { Start-Sleep -Milliseconds 250; $service = Get-CimInstance Win32_Service -Filter "Name='$serviceName'" -ErrorAction SilentlyContinue } while ($service -and $service.State -ne 'Stopped' -and [DateTime]::UtcNow -lt $deadline)
    if ($service -and $service.State -ne 'Stopped') { throw 'SERVICE_DID_NOT_STOP_WITHIN_TIMEOUT' }
    & $sc config $serviceName "binPath= `"$serviceExe`"" start= auto obj= LocalSystem | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'SERVICE_CONFIGURE_FAILED' }
} else {
    & $sc create $serviceName "binPath= `"$serviceExe`"" start= auto obj= LocalSystem DisplayName= 'MT5Agent Python Agent' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'SERVICE_CREATE_FAILED' }
}
& $sc description $serviceName 'MT5Agent Python control and runtime orchestration service.' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'SERVICE_DESCRIPTION_FAILED' }
& $sc start $serviceName | Out-Null
if ($LASTEXITCODE -gt 1) { throw 'SERVICE_START_FAILED' }
