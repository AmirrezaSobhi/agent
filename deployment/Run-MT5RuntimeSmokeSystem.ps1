param([Parameter(Mandatory = $true)] [string]$StageRoot)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$startedUtc = [DateTime]::UtcNow
$exitCode = 1
$resultPath = Join-Path $StageRoot 'task-result.json'
$result = $null
$context = $null
$identity = $null
$callerSid = $null
$callerSessionId = $null

function Get-AccountSid {
    param([string]$Account)
    return ([System.Security.Principal.NTAccount]::new($Account)).Translate(
        [System.Security.Principal.SecurityIdentifier]).Value
}

function Assert-ProtectedStage {
    param([string]$Path)
    $fullPath = [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
    $expectedBase = [System.IO.Path]::GetFullPath((Join-Path $env:ProgramFiles 'MT5Agent\CiRuntimeSmoke')).TrimEnd('\')
    if ($fullPath -notmatch ('^' + [regex]::Escape($expectedBase) + '\\\d+_\d+$')) {
        throw 'System smoke stage path is outside the allowlisted protected directory'
    }
    $item = Get-Item -LiteralPath $fullPath -Force -ErrorAction Stop
    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'System smoke stage cannot be a reparse point'
    }
    $acl = Get-Acl -LiteralPath $fullPath -ErrorAction Stop
    if (-not $acl.AreAccessRulesProtected) { throw 'System smoke stage ACL is inheriting permissions' }
    $allowedSids = @('S-1-5-18', 'S-1-5-32-544')
    foreach ($rule in $acl.Access) {
        $sid = $rule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
        if ($sid -notin $allowedSids -or $rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow -or
            ($rule.FileSystemRights -band [System.Security.AccessControl.FileSystemRights]::FullControl) -eq 0) {
            throw 'System smoke stage grants unexpected filesystem access'
        }
    }
}

try {
    $stageFullPath = [System.IO.Path]::GetFullPath($StageRoot).TrimEnd('\')
    Assert-ProtectedStage -Path $stageFullPath
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $callerSid = $identity.User.Value
    $callerSessionId = (Get-Process -Id $PID -ErrorAction Stop).SessionId
    if ($callerSid -cne 'S-1-5-18' -or $identity.Name -ine 'NT AUTHORITY\SYSTEM' -or $callerSessionId -ne 0) {
        throw 'Scheduled smoke task did not execute as LocalSystem in Session 0'
    }

    $contextPath = Join-Path $stageFullPath 'task-context.json'
    $receiptPath = Join-Path $stageFullPath 'task-context.sha256'
    if (-not (Test-Path -LiteralPath $contextPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $receiptPath -PathType Leaf)) {
        throw 'System smoke context or its integrity receipt is missing'
    }
    $expectedContextHash = (Get-Content -LiteralPath $receiptPath -Raw).Trim().ToLowerInvariant()
    $actualContextHash = (Get-FileHash -LiteralPath $contextPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($expectedContextHash -notmatch '^[0-9a-f]{64}$' -or $actualContextHash -cne $expectedContextHash) {
        throw 'System smoke context integrity check failed'
    }
    if (Test-Path -LiteralPath $resultPath) { throw 'Stale System smoke result is present in a fresh task stage' }
    $context = Get-Content -LiteralPath $contextPath -Raw | ConvertFrom-Json
    if ($context.schema_version -ne '1' -or $context.expected_control_sid -cne $callerSid -or
        $context.source_commit -notmatch '^[0-9a-f]{40}$' -or $context.pipeline_id -notmatch '^\d+$' -or
        $context.smoke_job_id -notmatch '^\d+$' -or $context.task_name -ne "MT5AgentRuntimeSmoke_$($context.pipeline_id)_$($context.smoke_job_id)" -or
        $context.artifact_name -notmatch '^MT5Agent-v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$') {
        throw 'System smoke context provenance or task allowlist validation failed'
    }

    $allowedFiles = [ordered]@{
        'deployment/ci.ps1' = [string]$context.ci_sha256
        'deployment/Run-MT5RuntimeSmokeSystem.ps1' = [string]$context.task_payload_sha256
        'agent/__init__.py' = [string]$context.agent_version_sha256
        "dist/$($context.artifact_name).exe" = [string]$context.candidate_sha256
        'src/desktop/MT5Agent.Desktop.Tests/bin/Release/MT5Agent.Desktop.Tests.exe' = [string]$context.desktop_smoke_sha256
        'reports/management-ipc-build.json' = [string]$context.desktop_smoke_provenance_sha256
    }
    foreach ($entry in $allowedFiles.GetEnumerator()) {
        if ($entry.Value -notmatch '^[0-9a-f]{64}$') { throw 'System smoke payload manifest contains an invalid digest' }
        $payloadPath = Join-Path $stageFullPath ($entry.Key -replace '/', '\')
        if (-not (Test-Path -LiteralPath $payloadPath -PathType Leaf)) { throw "System smoke payload is missing: $($entry.Key)" }
        $actualHash = (Get-FileHash -LiteralPath $payloadPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -cne $entry.Value) { throw "System smoke payload integrity check failed: $($entry.Key)" }
    }

    $desktopRoot = Join-Path $stageFullPath 'src/desktop/MT5Agent.Desktop.Tests/bin/Release'
    $desktopManifest = @($context.desktop_smoke_files)
    if ($desktopManifest.Count -eq 0) { throw 'System smoke Management test inventory is empty' }
    $expectedDesktopFiles = @{}
    foreach ($entry in $desktopManifest) {
        $relative = [string]$entry.relative_path
        $segments = $relative -split '/'
        if ($relative -notmatch '^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$' -or
            @($segments | Where-Object { $_ -in @('', '.', '..') }).Count -gt 0 -or
            $entry.sha256 -notmatch '^[0-9a-f]{64}$' -or [long]$entry.size -lt 0 -or
            $expectedDesktopFiles.ContainsKey($relative)) {
            throw 'System smoke Management test inventory is invalid or contains duplicate paths'
        }
        $expectedDesktopFiles[$relative] = $entry
    }
    $actualDesktopFiles = @(Get-ChildItem -LiteralPath $desktopRoot -File -Recurse -Force -ErrorAction Stop)
    if ($actualDesktopFiles.Count -ne $expectedDesktopFiles.Count) {
        throw 'System smoke Management test inventory does not cover every staged file'
    }
    foreach ($file in $actualDesktopFiles) {
        if (($file.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'System smoke Management test inventory contains a reparse point'
        }
        $relative = $file.FullName.Substring($desktopRoot.TrimEnd('\').Length + 1).Replace('\', '/')
        if (-not $expectedDesktopFiles.ContainsKey($relative)) { throw 'Staged Management test payload contains an unreceipted file' }
        $expected = $expectedDesktopFiles[$relative]
        if ([long]$file.Length -ne [long]$expected.size -or
            (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$expected.sha256) {
            throw "Staged Management test payload integrity check failed: $relative"
        }
    }

    $runtimePolicy = Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\MT5Agent\Runtime' -ErrorAction Stop
    $controlSid = Get-AccountSid -Account ([string]$runtimePolicy.ControlPrincipal)
    $runtimeSid = Get-AccountSid -Account ([string]$runtimePolicy.RuntimePrincipal)
    if ($controlSid -cne 'S-1-5-18' -or $runtimeSid -cne [string]$context.expected_runtime_sid -or $runtimeSid -eq $controlSid) {
        throw 'Machine runtime identity policy differs from the verified smoke context'
    }

    $env:CI_COMMIT_SHA = [string]$context.source_commit
    $env:CI_PIPELINE_ID = [string]$context.pipeline_id
    $env:CI_JOB_ID = [string]$context.smoke_job_id
    $env:ARTIFACT_NAME = [string]$context.artifact_name
    $ciScript = Join-Path $stageFullPath 'deployment/ci.ps1'
    $childStdout = Join-Path $stageFullPath 'reports/task.stdout.log'
    $childStderr = Join-Path $stageFullPath 'reports/task.stderr.log'
    New-Item -ItemType Directory -Path (Join-Path $stageFullPath 'reports') -Force | Out-Null
    $powershellPath = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
    if (-not (Test-Path -LiteralPath $powershellPath -PathType Leaf)) { throw 'Windows PowerShell host is unavailable' }
    $arguments = '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned ' +
        '-File "' + $ciScript + '" -Task smoke-mt5-runtime-system ' +
        '-ArtifactName "' + [string]$context.artifact_name + '" ' +
        '-SourceCommit "' + [string]$context.source_commit + '" ' +
        '-PipelineId "' + [string]$context.pipeline_id + '" ' +
        '-RuntimeSmokeJobId "' + [string]$context.smoke_job_id + '"'
    $process = Start-Process -FilePath $powershellPath -ArgumentList $arguments -WorkingDirectory $stageFullPath `
        -PassThru -WindowStyle Hidden -Wait -RedirectStandardOutput $childStdout -RedirectStandardError $childStderr
    $exitCode = [int]$process.ExitCode
    if ($exitCode -ne 0) { throw 'Allowlisted MT5 runtime smoke command returned a failure status' }
    $result = [ordered]@{
        schema_version = '1'; status = 'PASS'; exit_code = 0; pipeline_id = $context.pipeline_id
        smoke_job_id = $context.smoke_job_id; source_commit = $context.source_commit
        task_name = $context.task_name; caller = $identity.Name; caller_sid = $callerSid
        caller_session_id = $callerSessionId; candidate_sha256 = $context.candidate_sha256
        started_utc = $startedUtc.ToString('o'); completed_utc = [DateTime]::UtcNow.ToString('o')
    }
}
catch {
    $result = [ordered]@{
        schema_version = '1'; status = 'FAIL'; exit_code = 1; pipeline_id = if ($context) { $context.pipeline_id } else { $null }
        smoke_job_id = if ($context) { $context.smoke_job_id } else { $null }
        source_commit = if ($context) { $context.source_commit } else { $null }
        task_name = if ($context) { $context.task_name } else { $null }
        caller = if ($identity) { $identity.Name } else { $null }
        caller_sid = if ($callerSid) { $callerSid } else { $null }
        caller_session_id = if ($null -ne $callerSessionId) { $callerSessionId } else { $null }
        failure = $_.Exception.Message; started_utc = $startedUtc.ToString('o')
        completed_utc = [DateTime]::UtcNow.ToString('o')
    }
}
finally {
    if ($result) {
        $temporaryPath = "$resultPath.tmp"
        $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $temporaryPath -Encoding utf8
        Move-Item -LiteralPath $temporaryPath -Destination $resultPath -Force
    }
}
exit $exitCode
