[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$script:MockService = $null
$script:MockManagementKey = $false
$script:MockAllowedSids = @()
$script:MockNewServiceCalls = 0
$script:MockSetServiceCalls = 0
$script:MockStartServiceCalls = 0
$script:MockFailNewService = $false
$script:MockServiceExe = Join-Path $env:ProgramFiles 'MT5Agent\Service\MT5Agent.Service.exe'

function Test-Path {
    param([string] $LiteralPath, [string] $Path, [string] $PathType)
    $candidate = if ($LiteralPath) { $LiteralPath } else { $Path }
    if ($candidate -eq $script:MockServiceExe -or $candidate -eq (Join-Path $env:SystemRoot 'System32\sc.exe')) { return $true }
    if ($candidate -eq 'HKLM:\SOFTWARE\MT5Agent\Management') { return $script:MockManagementKey }
    if ($PathType) { return Microsoft.PowerShell.Management\Test-Path -LiteralPath $candidate -PathType $PathType }
    return Microsoft.PowerShell.Management\Test-Path -LiteralPath $candidate
}

function New-Item {
    param([string] $Path, [string] $ItemType, [switch] $Force)
    if ($Path -eq 'HKLM:\SOFTWARE\MT5Agent\Management') {
        $script:MockManagementKey = $true
        return [pscustomobject]@{ Name = 'Management' }
    }
    return Microsoft.PowerShell.Management\New-Item -Path $Path -ItemType $ItemType -Force:$Force
}

function Get-ItemProperty {
    param([string] $LiteralPath, [string[]] $Name, $ErrorAction)
    if ($LiteralPath -eq 'HKLM:\SOFTWARE\MT5Agent\Management' -and $script:MockAllowedSids.Count -gt 0) {
        return [pscustomobject]@{ AllowedUserSids = @($script:MockAllowedSids) }
    }
    return $null
}

function New-ItemProperty {
    param([string] $LiteralPath, [string] $Name, [string] $PropertyType, [object[]] $Value, [switch] $Force, $ErrorAction)
    if ($LiteralPath -ne 'HKLM:\SOFTWARE\MT5Agent\Management' -or $Name -ne 'AllowedUserSids') { throw 'Unexpected registry write in service test.' }
    $script:MockManagementKey = $true
    $script:MockAllowedSids = @($Value)
    return [pscustomobject]@{ AllowedUserSids = @($Value) }
}

function Remove-ItemProperty {
    param([string] $LiteralPath, [string] $Name, $ErrorAction)
    $script:MockAllowedSids = @()
}

function Get-CimInstance {
    param([string] $ClassName, [string] $Filter, $ErrorAction)
    if ($ClassName -eq 'Win32_Service' -and $Filter -eq "Name='MT5Agent'") { return $script:MockService }
    return $null
}

function New-Service {
    param([string] $Name, [string] $BinaryPathName, [string] $DisplayName, [string] $StartupType, [string] $Description, $ErrorAction)
    $script:MockNewServiceCalls++
    if ($script:MockFailNewService) { throw [InvalidOperationException]::new('Simulated SCM error 87: parameter incorrect.') }
    $script:MockService = [pscustomobject]@{ Name = $Name; DisplayName = $DisplayName; State = 'Stopped'; StartMode = 'Auto'; StartName = 'LocalSystem'; PathName = $BinaryPathName; ExitCode = 0; ServiceSpecificExitCode = 0 }
    return $script:MockService
}

function Set-Service {
    param([string] $Name, [string] $StartupType, [string] $Description, $ErrorAction)
    $script:MockSetServiceCalls++
}

function Get-Service {
    param([string] $Name, $ErrorAction)
    if (-not $script:MockService) { return $null }
    $status = if ($script:MockService.State -eq 'Running') { [System.ServiceProcess.ServiceControllerStatus]::Running } else { [System.ServiceProcess.ServiceControllerStatus]::Stopped }
    return [pscustomobject]@{ Name = $Name; Status = $status }
}

function Start-Service {
    param([string] $Name, $ErrorAction)
    $script:MockStartServiceCalls++
    $script:MockService.State = 'Running'
}

function Stop-Service {
    param([string] $Name, $ErrorAction)
    $script:MockService.State = 'Stopped'
}

function Start-Sleep {
    param([int] $Milliseconds)
}

$serviceScript = Join-Path $PSScriptRoot 'Install-MT5AgentService.ps1'
$testRoot = Join-Path $env:TEMP ('mt5agent-service-script-tests-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
. $serviceScript -Action Install -InstallRoot (Join-Path $env:ProgramFiles 'MT5Agent')

try {
    $root = Join-Path $env:ProgramFiles 'MT5Agent'

    $script:MockService = $null
    $script:MockManagementKey = $false
    $script:MockAllowedSids = @()
    $script:MockNewServiceCalls = 0
    $script:MockSetServiceCalls = 0
    $script:MockStartServiceCalls = 0
    $script:MockFailNewService = $false
    $successLog = Join-Path $testRoot 'service-success.log'
    $result = Invoke-MT5AgentService -RequestedAction Install -RequestedInstallRoot $root -LogPath $successLog
    if ($result -ne 0 -or $script:MockNewServiceCalls -ne 1 -or $script:MockStartServiceCalls -ne 1 -or $script:MockService.State -ne 'Running') {
        throw 'Successful Service registration simulation did not reach the expected Running state.'
    }
    if ((Get-Content -LiteralPath $successLog -Raw) -notmatch 'Service verified: Name=MT5Agent; State=Running') {
        throw 'Successful Service registration did not produce its completion log record.'
    }
    Write-Host 'Service registration success simulation PASS.'

    $script:MockService = $null
    $script:MockManagementKey = $true
    $script:MockAllowedSids = @('S-1-5-21-previous-control')
    $script:MockNewServiceCalls = 0
    $script:MockSetServiceCalls = 0
    $script:MockStartServiceCalls = 0
    $script:MockFailNewService = $true
    $failureLog = Join-Path $testRoot 'service-failure.log'
    $result = Invoke-MT5AgentService -RequestedAction Install -RequestedInstallRoot $root -LogPath $failureLog
    $failureText = Get-Content -LiteralPath $failureLog -Raw
    if ($result -ne 1 -or $script:MockService -or $failureText -notmatch 'SERVICE_CREATE_FAILED' -or
        $failureText -notmatch 'Simulated SCM error 87: parameter incorrect') {
        throw 'Simulated SCM registration failure did not return failure and preserve the root error in its log.'
    }
    if ($script:MockAllowedSids -notcontains 'S-1-5-21-previous-control') { throw 'The failed install changed the existing Management pipe allowlist.' }
    Write-Host 'Service registration simulated-failure and detailed-log test PASS.'

    $script:MockService = [pscustomobject]@{ Name = 'MT5Agent'; DisplayName = 'MT5Agent Python Agent'; State = 'Stopped'; StartMode = 'Auto'; StartName = 'LocalSystem'; PathName = '"' + $script:MockServiceExe + '"'; ExitCode = 0; ServiceSpecificExitCode = 0 }
    $script:MockManagementKey = $true
    $script:MockAllowedSids = @('S-1-5-21-previous-control')
    $script:MockNewServiceCalls = 0
    $script:MockSetServiceCalls = 0
    $script:MockStartServiceCalls = 0
    $script:MockFailNewService = $false
    $repairLog = Join-Path $testRoot 'partial-reinstall.log'
    $result = Invoke-MT5AgentService -RequestedAction Install -RequestedInstallRoot $root -LogPath $repairLog
    if ($result -ne 0 -or $script:MockNewServiceCalls -ne 0 -or $script:MockSetServiceCalls -ne 1 -or
        $script:MockStartServiceCalls -ne 1 -or $script:MockService.State -ne 'Running' -or
        $script:MockAllowedSids -notcontains 'S-1-5-21-previous-control') {
        throw 'Partial-install retry was not idempotent or did not preserve existing Management permissions.'
    }
    Write-Host 'Partial-install idempotent-retry simulation PASS.'

    $serviceText = Get-Content -LiteralPath $serviceScript -Raw
    if ($serviceText -match '(?im)\b(Stop-Process|Remove-Item)\b.*(terminal64|MetaTrader|MetaQuotes)') {
        throw 'Service installation script contains an unexpected MT5 process or data mutation.'
    }
    $installerText = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'installer\MT5Agent.iss') -Raw
    if ($installerText -match '(?im)^Filename:.*Install-MT5AgentService\.ps1.*Action Install') {
        throw 'Required Service installation must not remain an unchecked [Run] entry.'
    }
    if ($installerText -notmatch "RunRequiredPowerShell\('MT5Agent Service installation'") {
        throw 'Inno Setup does not route Service installation through the checked required-operation helper.'
    }
    Write-Host 'MT5 non-modification source guard PASS.'
}
finally {
    Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}
