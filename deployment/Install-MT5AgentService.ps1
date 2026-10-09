[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Install', 'Uninstall', 'Stop')]
    [string] $Action,

    [Parameter(Mandatory = $true)]
    [string] $InstallRoot
)

$ErrorActionPreference = 'Stop'

function Write-MT5AgentServiceLog {
    param(
        [Parameter(Mandatory = $true)][ValidateSet('INFO', 'WARN', 'ERROR')][string] $Level,
        [Parameter(Mandatory = $true)][string] $Message,
        [Parameter(Mandatory = $true)][string] $LogPath
    )

    $safeMessage = $Message -replace '(?i)(password|token|secret|credential)\s*[:=]\s*\S+', '$1=[REDACTED]'
    $line = '{0} [{1}] {2}{3}' -f (Get-Date).ToString('o'), $Level, $safeMessage, [Environment]::NewLine
    $directory = Split-Path -Parent $LogPath
    if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
    [IO.File]::AppendAllText($LogPath, $line, [Text.Encoding]::UTF8)
}

function Get-MT5AgentServiceBinaryPath {
    param([Parameter(Mandatory = $true)][string] $ImagePath)

    $value = $ImagePath.Trim()
    if ($value.StartsWith('"')) {
        $closingQuote = $value.IndexOf('"', 1)
        if ($closingQuote -lt 2) { throw 'SERVICE_IMAGE_PATH_QUOTING_INVALID' }
        return $value.Substring(1, $closingQuote - 1)
    }

    $space = $value.IndexOf(' ')
    if ($space -ge 0) { return $value.Substring(0, $space) }
    return $value
}

function Invoke-MT5AgentScCommand {
    param(
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [Parameter(Mandatory = $true)][string] $LogPath
    )

    $output = @(& $script:MT5AgentScPath @Arguments 2>&1 | ForEach-Object { [string]$_ })
    $exitCode = $LASTEXITCODE
    foreach ($line in $output) {
        if (-not [string]::IsNullOrWhiteSpace($line)) {
            Write-MT5AgentServiceLog -Level INFO -Message ("SCM: {0}" -f $line) -LogPath $LogPath
        }
    }
    if ($exitCode -ne 0) {
        throw ("SCM command '{0}' failed with exit code {1}. Output: {2}" -f $Arguments[0], $exitCode, ($output -join ' '))
    }
}

function Invoke-MT5AgentService {
    param(
        [Parameter(Mandatory = $true)][ValidateSet('Install', 'Uninstall', 'Stop')][string] $RequestedAction,
        [Parameter(Mandatory = $true)][string] $RequestedInstallRoot,
        [Parameter(Mandatory = $true)][string] $LogPath
    )

    $serviceName = 'MT5Agent'
    $description = 'MT5Agent Python control and runtime orchestration service.'
    $managementPath = 'HKLM:\SOFTWARE\MT5Agent\Management'
    $managementValueExisted = $false
    $previousAllowedSids = @()
    $managementUpdated = $false
    $createdByThisRun = $false
    $root = $null
    $serviceExe = $null
    $script:MT5AgentScPath = Join-Path $env:SystemRoot 'System32\sc.exe'

    try {
        $root = [IO.Path]::GetFullPath($RequestedInstallRoot).TrimEnd('\') + '\'
        $expectedRoot = [IO.Path]::GetFullPath((Join-Path $env:ProgramFiles 'MT5Agent')).TrimEnd('\') + '\'
        if (-not [string]::Equals($root, $expectedRoot, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'INSTALL_ROOT_MUST_BE_THE_PROTECTED_PROGRAM_FILES_MT5AGENT_DIRECTORY'
        }
        if (-not (Test-Path -LiteralPath $script:MT5AgentScPath -PathType Leaf)) { throw 'SCM_TOOL_UNAVAILABLE' }
        $serviceExe = [IO.Path]::GetFullPath((Join-Path $root 'Service\MT5Agent.Service.exe'))
        Write-MT5AgentServiceLog -Level INFO -Message ("Action={0}; InstallRoot={1}; PowerShell={2}; Is64BitProcess={3}" -f $RequestedAction, $root, $PSVersionTable.PSVersion, [Environment]::Is64BitProcess) -LogPath $LogPath

        $service = Get-CimInstance Win32_Service -Filter "Name='$serviceName'" -ErrorAction Stop
        if ($RequestedAction -in @('Stop', 'Uninstall')) {
            if (-not $service) {
                Write-MT5AgentServiceLog -Level INFO -Message 'No MT5Agent service is registered; operation is already complete.' -LogPath $LogPath
                return 0
            }

            $existingBinary = [IO.Path]::GetFullPath((Get-MT5AgentServiceBinaryPath -ImagePath ([string]$service.PathName)))
            if (-not $existingBinary.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'REFUSING_TO_CHANGE_SERVICE_OUTSIDE_MT5AGENT_INSTALL_ROOT'
            }
            if ($RequestedAction -eq 'Stop') {
                if ($service.State -eq 'Running') {
                    Stop-Service -Name $serviceName -ErrorAction Stop
                    $deadline = [DateTime]::UtcNow.AddSeconds(20)
                    do {
                        Start-Sleep -Milliseconds 250
                        $service = Get-CimInstance Win32_Service -Filter "Name='$serviceName'" -ErrorAction Stop
                    } while ($service -and $service.State -ne 'Stopped' -and [DateTime]::UtcNow -lt $deadline)
                    if ($service -and $service.State -ne 'Stopped') { throw 'SERVICE_DID_NOT_STOP_WITHIN_TIMEOUT' }
                }
                Write-MT5AgentServiceLog -Level INFO -Message 'MT5Agent service is stopped.' -LogPath $LogPath
                return 0
            }

            if ($service.State -eq 'Running') {
                Stop-Service -Name $serviceName -ErrorAction Stop
                $deadline = [DateTime]::UtcNow.AddSeconds(20)
                do {
                    Start-Sleep -Milliseconds 250
                    $service = Get-CimInstance Win32_Service -Filter "Name='$serviceName'" -ErrorAction Stop
                } while ($service -and $service.State -ne 'Stopped' -and [DateTime]::UtcNow -lt $deadline)
                if ($service -and $service.State -ne 'Stopped') { throw 'SERVICE_DID_NOT_STOP_WITHIN_TIMEOUT' }
            }
            Invoke-MT5AgentScCommand -Arguments @('delete', $serviceName) -LogPath $LogPath
            Write-MT5AgentServiceLog -Level INFO -Message 'MT5Agent service removal was requested.' -LogPath $LogPath
            return 0
        }

        if (-not (Test-Path -LiteralPath $serviceExe -PathType Leaf)) { throw 'SERVICE_HOST_BINARY_MISSING' }
        $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        if ($sid -notmatch '^S-1-') { throw 'CONTROL_PRINCIPAL_SID_UNAVAILABLE' }

        if (-not (Test-Path -LiteralPath $managementPath)) { New-Item -Path $managementPath -Force | Out-Null }
        $management = Get-ItemProperty -LiteralPath $managementPath -Name AllowedUserSids -ErrorAction SilentlyContinue
        if ($management -and $management.AllowedUserSids) {
            $managementValueExisted = $true
            $previousAllowedSids = @($management.AllowedUserSids | Where-Object { $_ })
        }
        $controlSids = @($previousAllowedSids + $sid)
        $runtime = Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\MT5Agent\Runtime' -Name ControlPrincipal -ErrorAction SilentlyContinue
        if ($runtime -and -not [string]::IsNullOrWhiteSpace([string]$runtime.ControlPrincipal)) {
            try {
                $controlIdentity = [Security.Principal.NTAccount]::new([string]$runtime.ControlPrincipal)
                $controlSids += $controlIdentity.Translate([Security.Principal.SecurityIdentifier]).Value
            } catch {
                throw ("CONFIGURED_CONTROL_PRINCIPAL_SID_RESOLUTION_FAILED: {0}" -f $_.Exception.Message)
            }
        }
        $controlSids = @($controlSids | Where-Object { $_ } | Sort-Object -Unique)

        if ($service) {
            $existingBinary = [IO.Path]::GetFullPath((Get-MT5AgentServiceBinaryPath -ImagePath ([string]$service.PathName)))
            if (-not [string]::Equals($existingBinary, $serviceExe, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'SERVICE_NAME_COLLISION_REFUSED'
            }
            if ([string]$service.StartName -notmatch '^(LocalSystem|NT AUTHORITY\\SYSTEM)$') {
                throw 'SERVICE_ACCOUNT_COLLISION_REFUSED'
            }
            Write-MT5AgentServiceLog -Level INFO -Message 'Matching MT5Agent service already exists; applying idempotent configuration.' -LogPath $LogPath
        } else {
            $binaryPathName = '"{0}"' -f $serviceExe
            try {
                New-Service -Name $serviceName -BinaryPathName $binaryPathName -DisplayName 'MT5Agent Python Agent' -StartupType Automatic -Description $description -ErrorAction Stop | Out-Null
                $createdByThisRun = $true
            } catch {
                throw ("SERVICE_CREATE_FAILED: {0}" -f $_.Exception.Message)
            }
        }

        New-ItemProperty -LiteralPath $managementPath -Name AllowedUserSids -PropertyType MultiString -Value $controlSids -Force -ErrorAction Stop | Out-Null
        $managementUpdated = $true
        Set-Service -Name $serviceName -StartupType Automatic -Description $description -ErrorAction Stop

        $service = Get-CimInstance Win32_Service -Filter "Name='$serviceName'" -ErrorAction Stop
        if (-not $service) { throw 'SERVICE_REGISTRATION_NOT_VISIBLE_TO_SCM' }
        $registeredBinary = [IO.Path]::GetFullPath((Get-MT5AgentServiceBinaryPath -ImagePath ([string]$service.PathName)))
        if (-not [string]::Equals($registeredBinary, $serviceExe, [StringComparison]::OrdinalIgnoreCase)) { throw 'SERVICE_BINARY_PATH_VERIFICATION_FAILED' }
        if ([string]$service.StartName -notmatch '^(LocalSystem|NT AUTHORITY\\SYSTEM)$') { throw 'SERVICE_ACCOUNT_VERIFICATION_FAILED' }

        $currentService = Get-Service -Name $serviceName -ErrorAction Stop
        if ($currentService.Status -ne [System.ServiceProcess.ServiceControllerStatus]::Running) {
            Start-Service -Name $serviceName -ErrorAction Stop
        }
        $deadline = [DateTime]::UtcNow.AddSeconds(30)
        do {
            $currentService = Get-Service -Name $serviceName -ErrorAction Stop
            if ($currentService.Status -eq [System.ServiceProcess.ServiceControllerStatus]::Running) { break }
            Start-Sleep -Milliseconds 250
        } while ([DateTime]::UtcNow -lt $deadline)
        if ($currentService.Status -ne [System.ServiceProcess.ServiceControllerStatus]::Running) {
            $service = Get-CimInstance Win32_Service -Filter "Name='$serviceName'" -ErrorAction Stop
            throw ("SERVICE_START_FAILED: state={0}; win32ExitCode={1}; serviceSpecificExitCode={2}" -f $service.State, $service.ExitCode, $service.ServiceSpecificExitCode)
        }

        Write-MT5AgentServiceLog -Level INFO -Message ("Service verified: Name={0}; State=Running; StartName={1}; BinaryPath={2}" -f $service.Name, $service.StartName, $service.PathName) -LogPath $LogPath
        return 0
    } catch {
        $record = $_
        try {
            Write-MT5AgentServiceLog -Level ERROR -Message ("Action={0}; ErrorId={1}; Category={2}; Message={3}; Script={4}; Line={5}; Stack={6}" -f $RequestedAction, $record.FullyQualifiedErrorId, $record.CategoryInfo.Category, $record.Exception.Message, $record.InvocationInfo.ScriptName, $record.InvocationInfo.ScriptLineNumber, $record.ScriptStackTrace) -LogPath $LogPath
        } catch {
            [Console]::Error.WriteLine(('MT5Agent service diagnostic log could not be written: {0}' -f $_.Exception.Message))
        }

        if ($managementUpdated) {
            try {
                if ($managementValueExisted) {
                    New-ItemProperty -LiteralPath $managementPath -Name AllowedUserSids -PropertyType MultiString -Value $previousAllowedSids -Force -ErrorAction Stop | Out-Null
                } else {
                    Remove-ItemProperty -LiteralPath $managementPath -Name AllowedUserSids -ErrorAction SilentlyContinue
                }
                Write-MT5AgentServiceLog -Level WARN -Message 'Restored the Management pipe SID allowlist after the failed service installation.' -LogPath $LogPath
            } catch {
                Write-MT5AgentServiceLog -Level ERROR -Message ("Failed to restore Management pipe SID allowlist: {0}" -f $_.Exception.Message) -LogPath $LogPath
            }
        }

        if ($createdByThisRun -and $serviceExe) {
            try {
                $createdService = Get-CimInstance Win32_Service -Filter "Name='$serviceName'" -ErrorAction SilentlyContinue
                if ($createdService) {
                    $createdBinary = [IO.Path]::GetFullPath((Get-MT5AgentServiceBinaryPath -ImagePath ([string]$createdService.PathName)))
                    if ([string]::Equals($createdBinary, $serviceExe, [StringComparison]::OrdinalIgnoreCase)) {
                        if ($createdService.State -eq 'Running') { Stop-Service -Name $serviceName -ErrorAction Stop }
                        Invoke-MT5AgentScCommand -Arguments @('delete', $serviceName) -LogPath $LogPath
                        Write-MT5AgentServiceLog -Level WARN -Message 'Removed the service created by this failed installation attempt.' -LogPath $LogPath
                    }
                }
            } catch {
                Write-MT5AgentServiceLog -Level ERROR -Message ("Could not roll back the newly created service: {0}" -f $_.Exception.Message) -LogPath $LogPath
            }
        }
        return 1
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    $logPath = Join-Path $env:ProgramData 'MT5Agent\Logs\service-install.log'
    $exitCode = Invoke-MT5AgentService -RequestedAction $Action -RequestedInstallRoot $InstallRoot -LogPath $logPath
    exit $exitCode
}
