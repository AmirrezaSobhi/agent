param(
    [Parameter(Mandatory = $true)] [string]$RepoRoot,
    [Parameter(Mandatory = $true)] [string]$ArtifactName,
    [Parameter(Mandatory = $true)] [string]$SourceCommit,
    [Parameter(Mandatory = $true)] [string]$PipelineId,
    [Parameter(Mandatory = $true)] [string]$RuntimeSmokeJobId,
    [int]$TimeoutSeconds = 660
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-AccountSid {
    param([string]$Account)
    return ([System.Security.Principal.NTAccount]::new($Account)).Translate(
        [System.Security.Principal.SecurityIdentifier]).Value
}

function Assert-ProtectedDirectory {
    param([string]$Path)
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'Privileged smoke staging path cannot be a reparse point'
    }
    $acl = Get-Acl -LiteralPath $Path -ErrorAction Stop
    if (-not $acl.AreAccessRulesProtected) { throw 'Privileged smoke staging ACL must not inherit permissions' }
    $allowedSids = @('S-1-5-18', 'S-1-5-32-544')
    foreach ($rule in $acl.Access) {
        $sid = $rule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
        if ($sid -notin $allowedSids -or $rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow -or
            ($rule.FileSystemRights -band [System.Security.AccessControl.FileSystemRights]::FullControl) -eq 0) {
            throw 'Privileged smoke staging directory has an unexpected access rule'
        }
    }
    foreach ($sid in $allowedSids) {
        $matchingRules = @($acl.Access | Where-Object {
            $_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value -eq $sid -and
            $_.AccessControlType -eq [System.Security.AccessControl.AccessControlType]::Allow -and
            ($_.FileSystemRights -band [System.Security.AccessControl.FileSystemRights]::FullControl) -ne 0
        })
        if ($matchingRules.Count -eq 0) { throw 'Privileged smoke staging ACL is missing a required owner' }
    }
}

function Set-ProtectedDirectory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { New-Item -ItemType Directory -Path $Path -ErrorAction Stop | Out-Null }
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'Privileged smoke staging path cannot be a reparse point'
    }
    $security = [System.Security.AccessControl.DirectorySecurity]::new()
    $security.SetAccessRuleProtection($true, $false)
    $inheritance = [System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
        [System.Security.AccessControl.InheritanceFlags]::ObjectInherit
    $propagation = [System.Security.AccessControl.PropagationFlags]::None
    $allow = [System.Security.AccessControl.AccessControlType]::Allow
    $security.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new(
        [System.Security.Principal.SecurityIdentifier]::new('S-1-5-18'), 'FullControl', $inheritance, $propagation, $allow))
    $security.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new(
        [System.Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'), 'FullControl', $inheritance, $propagation, $allow))
    Set-Acl -Path $Path -AclObject $security -ErrorAction Stop
    Assert-ProtectedDirectory -Path $Path
}

function Get-GitBlobHash {
    param([string]$Commit, [string]$RelativePath)
    $blob = (& git -C $RepoRoot rev-parse "$Commit`:$RelativePath" 2>$null)
    if ($LASTEXITCODE -ne 0 -or [string]$blob -notmatch '^[0-9a-f]{40}$') {
        throw "Cannot resolve committed payload: $RelativePath"
    }
    return [string]$blob
}

function Assert-CommittedFile {
    param([string]$Path, [string]$RelativePath)
    $actual = (& git -C $RepoRoot hash-object $Path 2>$null)
    if ($LASTEXITCODE -ne 0 -or [string]$actual -cne (Get-GitBlobHash -Commit $SourceCommit -RelativePath $RelativePath)) {
        throw "Privileged smoke source differs from the committed payload: $RelativePath"
    }
}

function Assert-FileInventory {
    param([string]$Root, [object[]]$Manifest)
    if (-not $Manifest -or $Manifest.Count -eq 0) { throw 'Management smoke payload inventory is empty' }
    $expected = @{}
    foreach ($entry in $Manifest) {
        $relative = [string]$entry.relative_path
        if ($relative -notmatch '^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$' -or
            $relative.Split('/') -contains '..' -or $entry.sha256 -notmatch '^[0-9a-f]{64}$' -or
            [long]$entry.size -lt 0 -or $expected.ContainsKey($relative)) {
            throw 'Management smoke payload inventory contains an invalid or duplicate entry'
        }
        $expected[$relative] = $entry
    }
    $actualFiles = @(Get-ChildItem -LiteralPath $Root -File -Recurse -Force -ErrorAction Stop)
    if ($actualFiles.Count -ne $expected.Count) { throw 'Management smoke payload file count differs from its receipt' }
    foreach ($file in $actualFiles) {
        if (($file.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'Management smoke payload contains a reparse-point file'
        }
        $relative = $file.FullName.Substring($Root.TrimEnd('\').Length + 1).Replace('\', '/')
        if (-not $expected.ContainsKey($relative)) { throw 'Management smoke payload contains an unreceipted file' }
        $entry = $expected[$relative]
        if ([long]$file.Length -ne [long]$entry.size -or
            (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$entry.sha256) {
            throw "Management smoke payload differs from its receipt: $relative"
        }
    }
}

function Assert-AdministratorCannotOpenWorkerPipe {
    param([string]$ConfiguredPipeName)
    $pipeLeaf = ($ConfiguredPipeName -split '\\')[-1]
    if ($pipeLeaf -notmatch '^MT5Agent\.Runtime\.v1$') { throw 'Runtime pipe name is not the v0.1.5 allowlisted endpoint' }
    $client = [System.IO.Pipes.NamedPipeClientStream]::new('.', $pipeLeaf,
        [System.IO.Pipes.PipeDirection]::InOut, [System.IO.Pipes.PipeOptions]::None)
    $denied = $false
    try {
        $client.Connect(1500)
    }
    catch [System.UnauthorizedAccessException] {
        $denied = $true
    }
    catch [System.IO.IOException] {
        $nativeCode = $_.Exception.HResult -band 0xffff
        if ($nativeCode -ne 5) { throw 'Administrator Worker-pipe probe did not fail with access denied' }
        $denied = $true
    }
    finally { $client.Dispose() }
    if (-not $denied) { throw 'Administrator unexpectedly opened the LocalSystem-only Worker pipe' }
}

if ($PipelineId -notmatch '^\d+$' -or $RuntimeSmokeJobId -notmatch '^\d+$' -or
    $SourceCommit -notmatch '^[0-9a-f]{40}$' -or $ArtifactName -notmatch '^MT5Agent-v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$') {
    throw 'Runtime smoke provenance or artifact name is invalid'
}
if ($TimeoutSeconds -lt 120 -or $TimeoutSeconds -gt 660) { throw 'Runtime smoke timeout is outside its fixed bound' }

$runnerIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$runnerSid = $runnerIdentity.User.Value
$runnerSession = (Get-Process -Id $PID -ErrorAction Stop).SessionId
if ($runnerSession -ne 0 -or -not ([System.Security.Principal.WindowsPrincipal]::new($runnerIdentity)).IsInRole(
    [System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Runtime smoke coordinator must be an elevated Session 0 CI runner'
}

$runtimeConfig = Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\MT5Agent\Runtime' -ErrorAction Stop
$controlSid = Get-AccountSid -Account ([string]$runtimeConfig.ControlPrincipal)
if ($controlSid -cne 'S-1-5-18' -or [string]$runtimeConfig.ControlPrincipal -ine 'NT AUTHORITY\SYSTEM') {
    throw 'Installed Worker ControlPrincipal must remain LocalSystem'
}
$runtimeSid = Get-AccountSid -Account ([string]$runtimeConfig.RuntimePrincipal)
if ($runtimeSid -eq $controlSid) { throw 'RuntimePrincipal and ControlPrincipal must remain distinct' }
Assert-AdministratorCannotOpenWorkerPipe -ConfiguredPipeName ([string]$runtimeConfig.PipeName)

$programFilesRoot = [System.IO.Path]::GetFullPath((Join-Path $env:ProgramFiles 'MT5Agent')).TrimEnd('\')
$stageParent = Join-Path $programFilesRoot 'CiRuntimeSmoke'
$baseItem = Get-Item -LiteralPath $programFilesRoot -Force -ErrorAction Stop
if (($baseItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'Installed product root cannot be a reparse point'
}
$baseAcl = Get-Acl -LiteralPath $programFilesRoot
$trustedWriteSids = @('S-1-5-18', 'S-1-5-32-544', (Get-AccountSid -Account 'NT SERVICE\TrustedInstaller'))
$untrustedSids = @('S-1-1-0', 'S-1-5-11', 'S-1-5-32-545', $runtimeSid)
$untrustedWriteRights = @(
    [System.Security.AccessControl.FileSystemRights]::WriteData,
    [System.Security.AccessControl.FileSystemRights]::AppendData,
    [System.Security.AccessControl.FileSystemRights]::WriteExtendedAttributes,
    [System.Security.AccessControl.FileSystemRights]::WriteAttributes,
    [System.Security.AccessControl.FileSystemRights]::Delete,
    [System.Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles,
    [System.Security.AccessControl.FileSystemRights]::ChangePermissions,
    [System.Security.AccessControl.FileSystemRights]::TakeOwnership
)
foreach ($rule in $baseAcl.Access) {
    if (($rule.PropagationFlags -band [System.Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0) {
        continue
    }
    $sid = $null
    try { $sid = $rule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value }
    catch { $sid = $null }
    $matchingWriteRights = @($untrustedWriteRights | Where-Object {
        ($rule.FileSystemRights -band $_) -eq $_
    })
    if ($rule.AccessControlType -eq [System.Security.AccessControl.AccessControlType]::Allow -and
        $matchingWriteRights.Count -gt 0 -and
        ($sid -in $untrustedSids -or $sid -notin $trustedWriteSids)) {
        throw 'Product root grants write/delete/ACL-change rights to an unprivileged principal; refusing privileged execution'
    }
}
Set-ProtectedDirectory -Path $stageParent

$mutex = [System.Threading.Mutex]::new($false, 'Global\MT5Agent.v0.1.5.RuntimeSmoke')
$hasMutex = $false
$stagePath = Join-Path $stageParent "${PipelineId}_${RuntimeSmokeJobId}"
$taskName = "MT5AgentRuntimeSmoke_${PipelineId}_${RuntimeSmokeJobId}"
$taskCreated = $false
$stageCreated = $false
$resultCopied = $false
$coordinatorStart = [DateTime]::UtcNow
$ciPath = Join-Path $RepoRoot 'deployment/ci.ps1'
$taskPayloadPath = Join-Path $RepoRoot 'deployment/Run-MT5RuntimeSmokeSystem.ps1'
    $agentVersionPath = Join-Path $RepoRoot 'agent/__init__.py'
$candidatePath = Join-Path $RepoRoot "dist\$ArtifactName.exe"
$buildEvidencePath = Join-Path $RepoRoot 'reports/build.json'
    $managementEvidencePath = Join-Path $RepoRoot 'reports/management-ipc-build.json'
$desktopTestsSource = Join-Path $RepoRoot 'src/desktop/MT5Agent.Desktop.Tests/bin/Release'
$reportDestination = Join-Path $RepoRoot 'reports'

try {
    try { $hasMutex = $mutex.WaitOne(0) }
    catch [System.Threading.AbandonedMutexException] { $hasMutex = $true }
    if (-not $hasMutex) { throw 'Another MT5 runtime smoke is already using this Worker/MT5 session' }
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        throw 'A task with this pipeline/job identity already exists; refusing to reuse or remove it'
    }
    if (Test-Path -LiteralPath $stagePath) { throw 'Protected stage path already exists; refusing stale payload reuse' }

    Assert-CommittedFile -Path $ciPath -RelativePath 'deployment/ci.ps1'
    Assert-CommittedFile -Path $taskPayloadPath -RelativePath 'deployment/Run-MT5RuntimeSmokeSystem.ps1'
    Assert-CommittedFile -Path $agentVersionPath -RelativePath 'agent/__init__.py'
    if (-not (Test-Path -LiteralPath $candidatePath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $buildEvidencePath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $managementEvidencePath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $desktopTestsSource -PathType Container)) {
        throw 'A required smoke input is missing'
    }
    $buildEvidence = Get-Content -LiteralPath $buildEvidencePath -Raw | ConvertFrom-Json
    $managementEvidence = Get-Content -LiteralPath $managementEvidencePath -Raw | ConvertFrom-Json
    $candidateHash = (Get-FileHash -LiteralPath $candidatePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($buildEvidence.schema_version -ne '1' -or $buildEvidence.commit_sha -ne $SourceCommit -or
        $buildEvidence.pipeline_id -ne $PipelineId -or $buildEvidence.candidate_filename -ne "$ArtifactName.exe" -or
        $buildEvidence.candidate_sha256 -ne $candidateHash -or
        [long]$buildEvidence.candidate_size -ne [long](Get-Item -LiteralPath $candidatePath).Length) {
        throw 'Candidate binary does not match its commit/pipeline build receipt'
    }
    $desktopSmokeSource = Join-Path $desktopTestsSource 'MT5Agent.Desktop.Tests.exe'
    if ($managementEvidence.schema_version -ne '1' -or $managementEvidence.commit_sha -ne $SourceCommit -or
        $managementEvidence.pipeline_id -ne $PipelineId -or
        $managementEvidence.executable_filename -ne 'MT5Agent.Desktop.Tests.exe' -or
        -not (Test-Path -LiteralPath $desktopSmokeSource -PathType Leaf) -or
        $managementEvidence.executable_sha256 -cne (Get-FileHash -LiteralPath $desktopSmokeSource -Algorithm SHA256).Hash.ToLowerInvariant() -or
        [long]$managementEvidence.executable_size -ne [long](Get-Item -LiteralPath $desktopSmokeSource).Length) {
        throw 'Management IPC test executable does not match its commit/pipeline provenance receipt'
    }
    $managementFiles = @($managementEvidence.files)
    Assert-FileInventory -Root $desktopTestsSource -Manifest $managementFiles

    Set-ProtectedDirectory -Path $stagePath
    $stageCreated = $true
    foreach ($relative in @('deployment', 'agent', 'dist', 'reports', 'src/desktop/MT5Agent.Desktop.Tests/bin/Release')) {
        New-Item -ItemType Directory -Path (Join-Path $stagePath $relative) -Force | Out-Null
    }
    Copy-Item -LiteralPath $ciPath -Destination (Join-Path $stagePath 'deployment/ci.ps1')
    Copy-Item -LiteralPath $taskPayloadPath -Destination (Join-Path $stagePath 'deployment/Run-MT5RuntimeSmokeSystem.ps1')
    Copy-Item -LiteralPath (Join-Path $RepoRoot 'agent/__init__.py') -Destination (Join-Path $stagePath 'agent/__init__.py')
    Copy-Item -LiteralPath $candidatePath -Destination (Join-Path $stagePath "dist\$ArtifactName.exe")
    Copy-Item -LiteralPath $buildEvidencePath -Destination (Join-Path $stagePath 'reports/build.json')
    Copy-Item -LiteralPath $managementEvidencePath -Destination (Join-Path $stagePath 'reports/management-ipc-build.json')
    Copy-Item -Path (Join-Path $desktopTestsSource '*') -Destination (Join-Path $stagePath 'src/desktop/MT5Agent.Desktop.Tests/bin/Release') -Recurse -Force
    Assert-ProtectedDirectory -Path $stagePath
    Assert-FileInventory -Root (Join-Path $stagePath 'src/desktop/MT5Agent.Desktop.Tests/bin/Release') -Manifest $managementFiles

    $stagedExpected = @{
        'deployment/ci.ps1' = (Get-GitBlobHash -Commit $SourceCommit -RelativePath 'deployment/ci.ps1')
        'deployment/Run-MT5RuntimeSmokeSystem.ps1' = (Get-GitBlobHash -Commit $SourceCommit -RelativePath 'deployment/Run-MT5RuntimeSmokeSystem.ps1')
        'agent/__init__.py' = (Get-GitBlobHash -Commit $SourceCommit -RelativePath 'agent/__init__.py')
    }
    foreach ($relative in $stagedExpected.Keys) {
        $stagedPath = Join-Path $stagePath ($relative -replace '/', '\')
        $stagedBlob = (& git -C $RepoRoot hash-object $stagedPath 2>$null)
        if ($LASTEXITCODE -ne 0 -or [string]$stagedBlob -cne $stagedExpected[$relative]) {
            throw "Staged privileged source differs from committed payload: $relative"
        }
    }
    $stagedCandidate = Join-Path $stagePath "dist\$ArtifactName.exe"
    if ((Get-FileHash -LiteralPath $stagedCandidate -Algorithm SHA256).Hash.ToLowerInvariant() -cne $candidateHash) {
        throw 'Staged candidate binary differs from the verified build receipt'
    }
    $stagedManagementReport = Join-Path $stagePath 'reports/management-ipc-build.json'
    if ((Get-FileHash -LiteralPath $stagedManagementReport -Algorithm SHA256).Hash.ToLowerInvariant() -cne
        (Get-FileHash -LiteralPath $managementEvidencePath -Algorithm SHA256).Hash.ToLowerInvariant()) {
        throw 'Staged Management IPC provenance receipt differs from the CI artifact'
    }

    $desktopSmokeExe = Join-Path $stagePath 'src/desktop/MT5Agent.Desktop.Tests/bin/Release/MT5Agent.Desktop.Tests.exe'
    if (-not (Test-Path -LiteralPath $desktopSmokeExe -PathType Leaf)) { throw 'Management IPC smoke executable is missing' }
    $context = [ordered]@{
        schema_version = '1'; pipeline_id = $PipelineId; smoke_job_id = $RuntimeSmokeJobId
        source_commit = $SourceCommit; artifact_name = $ArtifactName; task_name = $taskName
        expected_control_sid = 'S-1-5-18'; expected_runtime_sid = $runtimeSid
        ci_sha256 = (Get-FileHash -LiteralPath (Join-Path $stagePath 'deployment/ci.ps1') -Algorithm SHA256).Hash.ToLowerInvariant()
        task_payload_sha256 = (Get-FileHash -LiteralPath (Join-Path $stagePath 'deployment/Run-MT5RuntimeSmokeSystem.ps1') -Algorithm SHA256).Hash.ToLowerInvariant()
        agent_version_sha256 = (Get-FileHash -LiteralPath (Join-Path $stagePath 'agent/__init__.py') -Algorithm SHA256).Hash.ToLowerInvariant()
        candidate_sha256 = $candidateHash
        desktop_smoke_provenance_sha256 = (Get-FileHash -LiteralPath $stagedManagementReport -Algorithm SHA256).Hash.ToLowerInvariant()
        desktop_smoke_files = $managementFiles
        desktop_smoke_sha256 = (Get-FileHash -LiteralPath $desktopSmokeExe -Algorithm SHA256).Hash.ToLowerInvariant()
        coordinator_identity = $runnerIdentity.Name; coordinator_sid = $runnerSid; coordinator_session_id = $runnerSession
        created_utc = $coordinatorStart.ToString('o')
    }
    $contextPath = Join-Path $stagePath 'task-context.json'
    $context | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $contextPath -Encoding utf8
    # Context integrity is established by a second protected receipt, readable only by SYSTEM/Administrators.
    $receiptPath = Join-Path $stagePath 'task-context.sha256'
    (Get-FileHash -LiteralPath $contextPath -Algorithm SHA256).Hash.ToLowerInvariant() |
        Set-Content -LiteralPath $receiptPath -Encoding ascii

    $taskScriptPath = Join-Path $stagePath 'deployment/Run-MT5RuntimeSmokeSystem.ps1'
    $powershellPath = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $taskArguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File `"$taskScriptPath`" -StageRoot `"$stagePath`""
    $action = New-ScheduledTaskAction -Execute $powershellPath -Argument $taskArguments -WorkingDirectory $stagePath
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 12) -MultipleInstances IgnoreNew `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    $definition = New-ScheduledTask -Action $action -Principal $principal -Settings $settings
    Register-ScheduledTask -TaskName $taskName -TaskPath '\' -InputObject $definition -ErrorAction Stop | Out-Null
    $taskCreated = $true
    $registered = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
    $registeredSid = Get-AccountSid -Account ([string]$registered.Principal.UserId)
    if ($registeredSid -cne 'S-1-5-18' -or [string]$registered.Principal.LogonType -notmatch 'ServiceAccount' -or
        [string]$registered.Actions[0].Execute -ine $powershellPath -or
        [string]$registered.Actions[0].Arguments -notlike "*-File `"$taskScriptPath`"*") {
        throw 'Registered task identity or action differs from the fixed LocalSystem smoke harness'
    }
    Start-ScheduledTask -TaskName $taskName -ErrorAction Stop

    $resultPath = Join-Path $stagePath 'task-result.json'
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-Path -LiteralPath $resultPath -PathType Leaf) {
            $state = (Get-ScheduledTask -TaskName $taskName -ErrorAction Stop).State.ToString()
            if ($state -eq 'Ready') { break }
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not (Test-Path -LiteralPath $resultPath -PathType Leaf) -or
        (Get-ScheduledTask -TaskName $taskName -ErrorAction Stop).State.ToString() -ne 'Ready') {
        Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        $deadlineStop = [DateTime]::UtcNow.AddSeconds(15)
        while ((Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue).State.ToString() -eq 'Running' -and
            [DateTime]::UtcNow -lt $deadlineStop) { Start-Sleep -Milliseconds 250 }
        $candidateProcesses = @(Get-CimInstance Win32_Process | Where-Object {
            $_.ExecutablePath -ieq (Join-Path $stagePath "dist\$ArtifactName.exe")
        })
        foreach ($candidate in $candidateProcesses) { Stop-Process -Id $candidate.ProcessId -Force -ErrorAction SilentlyContinue }
        throw 'LocalSystem runtime smoke exceeded its strict timeout or failed to return a result'
    }
    $taskResult = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
    $taskInfo = Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction Stop
    if ($taskResult.schema_version -ne '1' -or $taskResult.pipeline_id -ne $PipelineId -or
        $taskResult.smoke_job_id -ne $RuntimeSmokeJobId -or $taskResult.source_commit -ne $SourceCommit -or
        $taskResult.task_name -ne $taskName -or $taskResult.status -ne 'PASS' -or
        $taskResult.exit_code -ne 0 -or $taskResult.caller_sid -cne 'S-1-5-18' -or
        $taskResult.caller_session_id -ne 0 -or $taskInfo.LastTaskResult -ne 0) {
        throw 'LocalSystem smoke result, caller identity, provenance, or scheduled-task exit status is invalid'
    }

    foreach ($name in @('mt5-runtime.json', 'management-ipc-live-smoke.txt', 'task.stdout.log', 'task.stderr.log')) {
        $source = Join-Path $stagePath "reports\$name"
        if (Test-Path -LiteralPath $source -PathType Leaf) { Copy-Item -LiteralPath $source -Destination (Join-Path $reportDestination $name) -Force }
    }
    Copy-Item -LiteralPath $resultPath -Destination (Join-Path $reportDestination 'runtime-task-result.json') -Force
    $resultCopied = $true
    if (-not (Test-Path -LiteralPath (Join-Path $reportDestination 'mt5-runtime.json') -PathType Leaf)) {
        throw 'LocalSystem runtime smoke did not produce the acceptance receipt'
    }
    Write-Output "LocalSystem Session 0 runtime smoke passed; Worker and MT5 acceptance receipt captured; task=$taskName"
}
catch {
    if ($stageCreated -and -not $resultCopied) {
        $failure = [ordered]@{ schema_version = '1'; status = 'FAIL'; pipeline_id = $PipelineId
            smoke_job_id = $RuntimeSmokeJobId; source_commit = $SourceCommit; task_name = $taskName
            failure = $_.Exception.Message; coordinator_identity = $runnerIdentity.Name
            coordinator_sid = $runnerSid; coordinator_session_id = $runnerSession
            occurred_utc = [DateTime]::UtcNow.ToString('o') }
        try { $failure | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $reportDestination 'runtime-task-result.json') -Encoding utf8 } catch { }
    }
    throw
}
finally {
    $cleanupError = $null
    $taskStillRunning = $false
    try {
        if ($taskCreated) {
            try {
                $currentTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
                if ($currentTask -and $currentTask.State.ToString() -eq 'Running') {
                    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
                    $stopDeadline = [DateTime]::UtcNow.AddSeconds(20)
                    do {
                        Start-Sleep -Milliseconds 250
                        $currentTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
                    } while ($currentTask -and $currentTask.State.ToString() -eq 'Running' -and [DateTime]::UtcNow -lt $stopDeadline)
                }
                if ($currentTask -and $currentTask.State.ToString() -eq 'Running') {
                    $taskStillRunning = $true
                    throw 'Temporary smoke task did not stop; preserving its protected payload for diagnosis'
                }
                if ($currentTask) { Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction Stop }
            }
            catch { $cleanupError = $_.Exception.Message }
        }
        if ($stageCreated -and (Test-Path -LiteralPath (Join-Path $stagePath 'reports') -PathType Container)) {
            foreach ($stagedReport in Get-ChildItem -LiteralPath (Join-Path $stagePath 'reports') -File -ErrorAction SilentlyContinue) {
                $destination = if ($stagedReport.Name -eq 'task-result.json') {
                    Join-Path $reportDestination 'runtime-task-result.raw.json'
                } else {
                    Join-Path $reportDestination $stagedReport.Name
                }
                Copy-Item -LiteralPath $stagedReport.FullName -Destination $destination -Force -ErrorAction SilentlyContinue
            }
        }
    }
    finally {
        try {
            if ($stageCreated -and -not $taskStillRunning) {
                Remove-Item -LiteralPath $stagePath -Recurse -Force -ErrorAction Stop
            }
        }
        finally {
            if ($hasMutex) { $mutex.ReleaseMutex() }
            $mutex.Dispose()
        }
    }
    if ($cleanupError) { throw "Temporary runtime smoke task cleanup failed: $cleanupError" }
}
