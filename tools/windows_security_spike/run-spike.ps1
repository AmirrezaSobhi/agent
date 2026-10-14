$ErrorActionPreference = 'Stop'
$msbuild = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\MSBuild.exe'
$project = Join-Path $PSScriptRoot 'WindowsSecuritySpike.csproj'
$builtExe = Join-Path $PSScriptRoot 'bin\Release\MT5Agent.WindowsSecuritySpike.exe'
$testDir = Join-Path $env:ProgramData 'MT5AgentSecuritySpike'
$exe = Join-Path $testDir 'MT5Agent.WindowsSecuritySpike.exe'
$serverName = 'MT5AgentManagementSecuritySpike'
$deniedName = 'MT5AgentManagementSecuritySpikeDeniedClient'
$taskName = 'MT5AgentManagementSecuritySpikeInteractiveClient'
$out = Join-Path $testDir 'authorized.json'
$deniedOut = Join-Path $testDir 'denied.json'
$serverCreated = $false
$deniedCreated = $false
$taskCreated = $false
New-Item -ItemType Directory -Path $testDir -Force | Out-Null
try {
    & $msbuild $project /t:Rebuild /p:Configuration=Release /p:Platform=x64 /m:1 /nologo /verbosity:minimal
    if ($LASTEXITCODE -ne 0) { throw 'Security spike build failed' }
    Copy-Item $builtExe $exe -Force
    $allowedSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & sc.exe create $serverName binPath= "`"$exe`" --service $allowedSid" start= demand obj= LocalSystem | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the disposable LocalSystem spike service' }
    $serverCreated = $true
    Start-Service $serverName
    $deadline = [DateTime]::UtcNow.AddSeconds(8)
    while ((Get-Service $serverName).Status -ne 'Running' -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 100 }
    if ((Get-Service $serverName).Status -ne 'Running') { throw 'Security spike service did not reach Running' }

    $principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
    $action = New-ScheduledTaskAction -Execute $exe -Argument "--client `"$out`""
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds 15) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $taskName -InputObject (New-ScheduledTask -Action $action -Principal $principal -Settings $settings) -Force | Out-Null
    $taskCreated = $true
    Start-ScheduledTask -TaskName $taskName
    $deadline = [DateTime]::UtcNow.AddSeconds(12)
    while (-not (Test-Path $out) -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 100 }
    if (-not (Test-Path $out)) { throw 'Authorized interactive client did not write evidence' }
    $authorized = Get-Content $out -Raw | ConvertFrom-Json
    if ($authorized.client_session -ne 1 -or -not $authorized.response.authorized -or
        -not $authorized.response.claimed_sid_ignored -or -not $authorized.response.impersonation_failure_denied -or
        -not $authorized.response.restoration_after_callback_exception -or
        $authorized.response.service_session -ne 0 -or
        $authorized.client_sid -notmatch 'S-1-5-21-REDACTED-' -or
        $authorized.response.actual_client_sid -notmatch 'S-1-5-21-REDACTED-') {
        throw 'Authorized Session 1 identity/restoration assertions failed'
    }

    & sc.exe create $deniedName binPath= "`"$exe`" --client-service `"$deniedOut`"" start= demand obj= 'NT AUTHORITY\LocalService' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the disposable denied-client service' }
    $deniedCreated = $true
    Start-Service $deniedName
    $deadline = [DateTime]::UtcNow.AddSeconds(8)
    while (-not (Test-Path $deniedOut) -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 100 }
    if (-not (Test-Path $deniedOut)) { throw 'Unauthorized LocalService client did not write evidence' }
    $denied = Get-Content $deniedOut -Raw | ConvertFrom-Json
    if (-not $denied.expected_denied -or $denied.client_sid -ne 'S-1-5-19' -or $denied.client_session -ne 0) {
        throw 'Unauthorized LocalService client was not rejected by the pipe DACL'
    }

    [pscustomobject]@{
        service_identity = 'LocalSystem (S-1-5-18)'
        service_session = $authorized.response.service_session
        authorized_client_sid = $authorized.response.actual_client_sid
        authorized_client_session = $authorized.client_session
        impersonation_failure_denied = $authorized.response.impersonation_failure_denied
        restoration_after_callback_exception = $authorized.response.restoration_after_callback_exception
        caller_claim_ignored = $authorized.response.claimed_sid_ignored
        denied_client_sid = $denied.client_sid
        denied_client_session = $denied.client_session
        unauthorized_pipe_open_denied = $denied.expected_denied
    } | ConvertTo-Json -Compress
} finally {
    if ($taskCreated) { Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue }
    if ($deniedCreated) {
        Stop-Service $deniedName -Force -ErrorAction SilentlyContinue
        & sc.exe delete $deniedName | Out-Null
    }
    if ($serverCreated) {
        Stop-Service $serverName -Force -ErrorAction SilentlyContinue
        & sc.exe delete $serverName | Out-Null
    }
    Start-Sleep -Milliseconds 250
    Remove-Item $testDir -Recurse -Force -ErrorAction SilentlyContinue
}
