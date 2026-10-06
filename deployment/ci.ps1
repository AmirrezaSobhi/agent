param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('metadata', 'validate', 'test', 'build', 'smoke-invalid', 'smoke-control-plane', 'smoke-mt5-runtime', 'package')]
    [string]$Task,
    [string]$PythonExecutable = 'python',
    [string]$ArtifactName = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$versionSource = Get-Content -LiteralPath (Join-Path $repoRoot 'agent/__init__.py') -Raw
$versionMatch = [regex]::Match($versionSource, '(?m)^__version__ = "((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))"\r?$')
if (-not $versionMatch.Success) { throw 'Missing stable semantic version in agent/__init__.py' }
$version = $versionMatch.Groups[1].Value
$expectedArtifactName = "MT5Agent-v$version"
if ($ArtifactName -and $ArtifactName -ne $expectedArtifactName) {
    throw "ArtifactName must match the source version: $expectedArtifactName"
}
$ArtifactName = $expectedArtifactName
$env:ARTIFACT_NAME = $ArtifactName
if ($env:CI_COMMIT_TAG -and $env:CI_COMMIT_TAG -cne "v$version") {
    throw "Tag $env:CI_COMMIT_TAG does not match source version v$version"
}
$sourceCommit = (& git -C $repoRoot rev-parse HEAD)
if ($LASTEXITCODE -ne 0) { throw 'Cannot determine source commit' }
if ($env:CI_COMMIT_SHA -and $env:CI_COMMIT_SHA -ne $sourceCommit) {
    throw 'Checkout HEAD does not match CI_COMMIT_SHA'
}
$pipelineId = [string]$env:CI_PIPELINE_ID
$exePath = Join-Path $repoRoot "dist\$ArtifactName.exe"
$reportRoot = Join-Path $repoRoot 'reports'
$buildEvidencePath = Join-Path $reportRoot 'build.json'

function Invoke-Python {
    param([string[]]$Arguments)
    & $PythonExecutable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
}

function Get-BinaryHash {
    if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
        throw "Expected executable does not exist: $exePath"
    }
    return (Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Read-BuildEvidence {
    if (-not (Test-Path -LiteralPath $buildEvidencePath -PathType Leaf)) {
        throw 'Build evidence is missing'
    }
    return (Get-Content -LiteralPath $buildEvidencePath -Raw | ConvertFrom-Json)
}

function Assert-BuildEvidence {
    $build = Read-BuildEvidence
    if ($build.schema_version -ne '1' -or $build.candidate_filename -ne "$ArtifactName.exe" -or
        $build.candidate_version -ne $version -or $build.candidate_sha256 -ne (Get-BinaryHash) -or
        [long]$build.candidate_size -ne [long](Get-Item -LiteralPath $exePath).Length -or
        $build.commit_sha -ne $sourceCommit -or $build.pipeline_id -ne $pipelineId -or
        $build.metatrader5_present_in_build_environment -ne $false -or
        $build.numpy_present_in_build_environment -ne $false -or -not $build.python_version -or
        $build.archive_inspection_success -ne $true -or @($build.archive_forbidden_module_matches).Count -ne 0) {
        throw 'Missing or mismatched clean-build evidence for this commit/pipeline/artifact'
    }
    return $build
}

function Invoke-CandidateCommand {
    param([string]$Name, [string[]]$Arguments, [int]$TimeoutMilliseconds = 30000)
    $stdout = Join-Path $reportRoot "$Name.stdout.log"
    $stderr = Join-Path $reportRoot "$Name.stderr.log"
    $process = Start-Process -FilePath $exePath -ArgumentList $Arguments -WorkingDirectory $repoRoot `
        -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    try {
        if (-not $process.WaitForExit($TimeoutMilliseconds)) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            throw "$Name exceeded its bounded inspection timeout"
        }
        $process.WaitForExit()
        return [pscustomobject]@{
            ExitCode = $process.ExitCode
            Output = if (Test-Path -LiteralPath $stdout) { Get-Content -LiteralPath $stdout -Raw } else { '' }
            ErrorOutput = if (Test-Path -LiteralPath $stderr) { Get-Content -LiteralPath $stderr -Raw } else { '' }
        }
    }
    finally { $process.Dispose() }
}

function Get-CandidateDiagnostics {
    $versionResult = Invoke-CandidateCommand -Name 'version' -Arguments @('--version')
    if ($versionResult.ExitCode -ne 0 -or $versionResult.Output.Trim() -cne $version) {
        throw 'Candidate --version failed or disagrees with source metadata'
    }
    $result = Invoke-CandidateCommand -Name 'diagnostics' -Arguments @('--diagnose', '--json') -TimeoutMilliseconds 30000
    try { $inspection = $result.Output | ConvertFrom-Json -ErrorAction Stop }
    catch { throw 'Candidate diagnostics did not return valid JSON' }
    $expectedExit = if ($inspection.ready) { 0 } else { 1 }
    if ($result.ExitCode -ne $expectedExit -or $inspection.schema_version -ne '2' -or
        $inspection.agent_version -ne $version -or $inspection.inspection_only -ne $true -or
        $inspection.configuration.valid -ne $true -or
        -not ($inspection.runtime.worker_available -is [bool]) -or
        -not ($inspection.runtime.runtime_state -is [string]) -or
        $inspection.PSObject.Properties.Name -contains 'terminal') {
        throw 'Candidate diagnostics violate the Worker-aware control-plane contract'
    }
    return $inspection
}

function Test-CandidateCLI {
    $null = Assert-BuildEvidence
    $inspection = Get-CandidateDiagnostics
    $null = Assert-BuildEvidence
    return $inspection
}

function Get-FreeLoopbackPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    try {
        $listener.Start()
        return [int]$listener.LocalEndpoint.Port
    }
    finally { $listener.Stop() }
}

function New-AgentCommandBody {
    param([string]$CommandType)
    $correlationId = [guid]::NewGuid().ToString()
    return @{
        request_id = [guid]::NewGuid().ToString()
        correlation_id = $correlationId
        command = @{
            command_id = [guid]::NewGuid().ToString()
            command_type = $CommandType
            schema_version = '1'
            correlation_id = $correlationId
            timestamp = [DateTimeOffset]::Now.ToString('o')
            payload = @{}
        }
    } | ConvertTo-Json -Depth 8 -Compress
}

function Invoke-AgentCommand {
    param([int]$Port, [string]$CommandType, [int]$TimeoutSeconds = 30)
    $body = New-AgentCommandBody -CommandType $CommandType
    return Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$Port/command" `
        -ContentType 'application/json' -Body $body -TimeoutSec $TimeoutSeconds -ErrorAction Stop
}

function Test-HasProperty {
    param($Value, [string]$Name)
    return ($null -ne $Value -and $Value.PSObject.Properties.Name -contains $Name)
}

function Assert-CommandSuccess {
    param($Response, [string]$CommandType)
    if ($Response.success -ne $true -or $Response.command_id -eq '' -or $Response.code -ne 'ok') {
        throw "Candidate application command failed: $CommandType"
    }
}

function Get-ProcessEvidence {
    param([int]$ProcessId)
    $process = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
    if (-not $process) { throw "Expected process $ProcessId is not running" }
    $ownerResult = Invoke-CimMethod -InputObject $process -MethodName GetOwner -ErrorAction Stop
    $sidResult = Invoke-CimMethod -InputObject $process -MethodName GetOwnerSid -ErrorAction Stop
    if ($ownerResult.ReturnValue -ne 0 -or $sidResult.ReturnValue -ne 0 -or -not $sidResult.Sid) {
        throw "Cannot establish Windows owner for process $ProcessId"
    }
    $owner = if ($ownerResult.Domain) { "$($ownerResult.Domain)\$($ownerResult.User)" } else { [string]$ownerResult.User }
    return [ordered]@{
        pid = [int]$process.ProcessId
        parent_pid = [int]$process.ParentProcessId
        principal = $owner
        sid = [string]$sidResult.Sid
        session_id = [int]$process.SessionId
        executable = [string]$process.ExecutablePath
        created_utc = if ($process.CreationDate) { ([datetime]$process.CreationDate).ToUniversalTime().ToString('o') } else { $null }
    }
}

function Start-CandidateAgent {
    param([int]$Port)
    $names = @('MT5_AGENT_HTTP_HOST', 'MT5_AGENT_HTTP_PORT', 'MT5_AGENT_HTTP_MAX_REQUEST_BYTES', 'MT5_AGENT_LOG_LEVEL')
    $previous = @{}
    foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
    $env:MT5_AGENT_HTTP_HOST = '127.0.0.1'
    $env:MT5_AGENT_HTTP_PORT = [string]$Port
    $env:MT5_AGENT_HTTP_MAX_REQUEST_BYTES = '1048576'
    $env:MT5_AGENT_LOG_LEVEL = 'WARNING'
    $stdout = Join-Path $reportRoot 'candidate-agent.stdout.log'
    $stderr = Join-Path $reportRoot 'candidate-agent.stderr.log'
    try {
        return Start-Process -FilePath $exePath -WorkingDirectory $repoRoot -PassThru -WindowStyle Hidden `
            -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    }
    catch { throw 'Could not start the candidate Agent process' }
    finally {
        foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
    }
}

function Stop-CandidateAgent {
    param($Process)
    if ($null -eq $Process) { return }
    $current = Get-Process -Id $Process.Id -ErrorAction SilentlyContinue
    if ($current) {
        # PyInstaller one-file uses a bootloader parent and an application child.
        # Only stop direct children whose executable is this exact candidate;
        # never target the persistent Worker, terminal, a name, or a process tree.
        $children = @(Get-CimInstance -ClassName Win32_Process -Filter "ParentProcessId = $($Process.Id)" -ErrorAction Stop |
            Where-Object { $_.ExecutablePath -ieq $exePath })
        foreach ($child in $children) {
            Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
        $null = $current.WaitForExit(10000)
    }
    $Process.Dispose()
}

function Wait-CandidateHealth {
    param([int]$Port, [int]$TimeoutSeconds, [switch]$RequireConnected)
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $lastResponse = $null
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($script:CandidateProcess -and $script:CandidateProcess.HasExited) {
            throw 'Candidate Agent exited before its HTTP health endpoint became ready'
        }
        try {
            $response = Invoke-AgentCommand -Port $Port -CommandType 'agent.get_health' -TimeoutSeconds 30
            Assert-CommandSuccess -Response $response -CommandType 'agent.get_health'
            $lastResponse = $response
            $health = $response.data
            if ($health.agent_state -eq 'AGENT_RUNNING' -and
                (-not $RequireConnected -or ($health.runtime_state -eq 'MT5_CONNECTED' -and $health.runtime.mt5_connected -eq $true))) {
                return $health
            }
        }
        catch {
            if ($script:CandidateProcess -and $script:CandidateProcess.HasExited) { throw }
        }
        Start-Sleep -Milliseconds 500
    }
    if ($lastResponse) {
        throw "Candidate did not reach required health state before timeout; last runtime_state=$($lastResponse.data.runtime_state)"
    }
    throw 'Candidate HTTP health endpoint did not become available before timeout'
}

function Write-JsonEvidence {
    param([string]$Path, $Value)
    $Value | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Path -Encoding utf8
}

function Get-ConfiguredRuntime {
    try { $configuration = Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\MT5Agent\Runtime' -ErrorAction Stop }
    catch { throw 'Configured Runtime Worker policy is unavailable on this Runner' }
    foreach ($name in @('RuntimePrincipal', 'ControlPrincipal', 'TerminalPath', 'ProfilePath', 'PipeName')) {
        if (-not [string]$configuration.$name) { throw "Runtime Worker policy is missing $name" }
    }
    return $configuration
}

function Assert-WorkerTaskAndPreflight {
    param($RuntimeConfiguration, $Inspection)
    $expectedRuntime = [string]$RuntimeConfiguration.RuntimePrincipal
    $expectedControl = [string]$RuntimeConfiguration.ControlPrincipal
    $currentToken = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $currentIdentity = $currentToken.Name
    $currentSid = $currentToken.User.Value
    $expectedControlSid = ([System.Security.Principal.NTAccount]$expectedControl).Translate([System.Security.Principal.SecurityIdentifier]).Value
    $expectedRuntimeSid = ([System.Security.Principal.NTAccount]$expectedRuntime).Translate([System.Security.Principal.SecurityIdentifier]).Value
    $controlSession = (Get-Process -Id $PID -ErrorAction Stop).SessionId
    if ($controlSession -ne 0) { throw 'MT5 integration control client is not in Session 0' }
    if ($currentIdentity -ine $expectedControl -or $currentSid -ine $expectedControlSid) {
        throw 'CI caller does not match configured ControlPrincipal SID'
    }
    $task = Get-ScheduledTask -TaskName 'MT5 Agent Interactive Runtime Worker - MT5RuntimeUser' -ErrorAction Stop
    $taskPrincipal = [string]$task.Principal.UserId
    $taskSid = if ($taskPrincipal -match '^S-1-') {
        ([System.Security.Principal.SecurityIdentifier]$taskPrincipal).Value
    } else {
        ([System.Security.Principal.NTAccount]$taskPrincipal).Translate([System.Security.Principal.SecurityIdentifier]).Value
    }
    # ScheduledTasks CIM calls this enum Interactive; task XML calls it
    # InteractiveToken. Both represent TASK_LOGON_INTERACTIVE_TOKEN (3).
    if ($task.State.ToString() -ne 'Running' -or -not $task.Settings.Enabled -or
        $taskSid -ine $expectedRuntimeSid -or [int]$task.Principal.LogonType -ne 3) {
        throw 'Dedicated interactive Worker task is not running under the configured principal and logon type'
    }
    $runtime = $Inspection.runtime
    $identity = $runtime.worker_identity
    if ($runtime.worker_available -ne $true -or $runtime.protocol_version -ne '1' -or
        $runtime.control_session_id -ne 0 -or $identity.account -ine $expectedRuntime -or
        $identity.sid -ine $expectedRuntimeSid -or $identity.session_id -le 0 -or $identity.pid -le 0 -or $identity.protocol_version -ne '1') {
        throw 'Authenticated Worker handshake, identity, Session 0 caller, or protocol precondition failed'
    }
    if ($runtime.runtime_state -notin @('MT5_CONNECTED', 'MT5_NOT_INITIALIZED', 'MT5_DISCONNECTED', 'MT5_RECONNECTING', 'MT5_ERROR')) {
        throw "Worker reported an unexpected runtime state: $($runtime.runtime_state)"
    }
    if ((Test-HasProperty -Value $runtime -Name 'terminal_session_id') -and $runtime.terminal_session_id -and
        [int]$runtime.terminal_session_id -ne [int]$identity.session_id) {
        throw 'Pre-existing configured terminal does not share the Worker session'
    }
    return [pscustomobject]@{ Caller = $currentIdentity; RuntimePrincipal = $expectedRuntime; Task = $task; Worker = $identity }
}

Push-Location $repoRoot
try {
    New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null
    switch ($Task) {
        'metadata' {
            Write-Output "Source $sourceCommit; version $version; executable $ArtifactName.exe"
        }
        'validate' {
            $historical = @(Get-ChildItem -LiteralPath $repoRoot -Directory | Where-Object { $_.Name -like 'Version *' })
            if ($historical.Count -gt 0) { throw 'Historical version directories must not be present in the active tree' }
            Invoke-Python -Arguments @('-m', 'compileall', '-q', 'agent', 'main.py')
            Invoke-Python -Arguments @('-c', 'from pathlib import Path; import agent, agent.main, agent.composition, agent.__main__, main; assert Path(agent.__file__).resolve() == Path("agent/__init__.py").resolve(); assert main.run is agent.main.run; print("Active package and both entry points imported successfully")')
        }
        'test' {
            Invoke-Python -Arguments @('-m', 'pytest', '-q', '--durations=20', '--junitxml=reports/pytest.xml')
        }
        'build' {
            if (Test-Path -LiteralPath $exePath) { Remove-Item -LiteralPath $exePath }
            foreach ($name in @('build', 'invalid-configuration', 'control-plane', 'mt5-runtime', 'release-evidence')) {
                $path = Join-Path $reportRoot "$name.json"
                if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path }
            }
            $mt5Present = & $PythonExecutable -c 'import importlib.util; print("true" if importlib.util.find_spec("MetaTrader5") else "false")'
            if ($LASTEXITCODE -ne 0 -or $mt5Present.Trim() -ne 'false') {
                throw 'MetaTrader5 must be absent from the isolated Agent build environment'
            }
            $numpyPresent = & $PythonExecutable -c 'import importlib.util; print("true" if importlib.util.find_spec("numpy") else "false")'
            if ($LASTEXITCODE -ne 0 -or $numpyPresent.Trim() -ne 'false') {
                throw 'NumPy must be absent from the isolated Agent build environment'
            }
            Invoke-Python -Arguments @('deployment/make_icon.py')
            Invoke-Python -Arguments @('-m', 'PyInstaller', 'deployment/Agent.spec', '--clean', '--noconfirm')
            $archiveViewer = Join-Path (Split-Path -Parent $PythonExecutable) 'pyi-archive_viewer.exe'
            if (-not (Test-Path -LiteralPath $archiveViewer -PathType Leaf)) { throw 'PyInstaller archive viewer is missing from the isolated build environment' }
            $archiveOutput = (& $archiveViewer -r $exePath 2>&1 | Out-String)
            if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the Agent PyInstaller archive' }
            $forbiddenPatterns = @(
                '(?i)(?<![A-Za-z0-9_])MetaTrader5(?![A-Za-z0-9_])',
                '(?i)(?<![A-Za-z0-9_])numpy(?![A-Za-z0-9_])',
                '(?i)(?<![A-Za-z0-9_])agent[./\\]infrastructure[./\\]interactive_mt5_worker(?![A-Za-z0-9_])',
                '(?i)(?<![A-Za-z0-9_])agent[./\\]adapters[./\\]mt5_adapter(?![A-Za-z0-9_])',
                '(?i)(?<![A-Za-z0-9_])agent[./\\]infrastructure[./\\]terminal_inspection(?![A-Za-z0-9_])'
            )
            $archiveMatches = @()
            foreach ($pattern in $forbiddenPatterns) {
                foreach ($match in [regex]::Matches($archiveOutput, $pattern)) { $archiveMatches += $match.Value }
            }
            if ($archiveMatches.Count -gt 0) { throw "Forbidden MT5/Worker-only modules found in Agent archive: $($archiveMatches -join ', ')" }
            $pythonVersion = (& $PythonExecutable -c 'import platform; print(platform.python_version())').Trim()
            if ($LASTEXITCODE -ne 0) { throw 'Could not determine isolated build Python version' }
            $buildEvidence = [ordered]@{
                schema_version = '1'
                pipeline_id = $pipelineId
                commit_sha = $sourceCommit
                source_commit = $sourceCommit
                candidate_version = $version
                version = $version
                candidate_filename = "$ArtifactName.exe"
                executable = "$ArtifactName.exe"
                candidate_size = (Get-Item -LiteralPath $exePath).Length
                candidate_sha256 = Get-BinaryHash
                sha256 = Get-BinaryHash
                python_version = $pythonVersion
                metatrader5_present_in_build_environment = $false
                numpy_present_in_build_environment = $false
                archive_inspection_success = $true
                archive_forbidden_module_matches = @($archiveMatches)
            }
            Write-JsonEvidence -Path $buildEvidencePath -Value $buildEvidence
            Write-Output "Built $ArtifactName.exe; size=$($buildEvidence.candidate_size); SHA256=$($buildEvidence.candidate_sha256); Python=$pythonVersion; MetaTrader5=absent; forbidden archive modules=0"
        }
        'smoke-invalid' {
            $null = Assert-BuildEvidence
            $inspection = Test-CandidateCLI
            if ($inspection.ready -or $inspection.runtime.worker_available) { throw 'Control build smoke unexpectedly found a ready MT5 runtime' }
            $previousPort = [Environment]::GetEnvironmentVariable('MT5_AGENT_HTTP_PORT', 'Process')
            try {
                $env:MT5_AGENT_HTTP_PORT = 'invalid'
                $result = Invoke-CandidateCommand -Name 'invalid-configuration' -Arguments @() -TimeoutMilliseconds 30000
                if ($result.ExitCode -ne 2 -or $result.ErrorOutput -notmatch 'Invalid startup configuration: MT5_AGENT_HTTP_PORT must be an integer') {
                    throw 'Candidate invalid-configuration behavior did not match the established contract'
                }
                $build = Assert-BuildEvidence
                Write-JsonEvidence -Path (Join-Path $reportRoot 'invalid-configuration.json') -Value ([ordered]@{
                    schema_version = '1'; test = 'invalid-configuration'; status = 'PASS'; expected_exit = 2; actual_exit = $result.ExitCode
                    candidate_filename = $build.candidate_filename; candidate_sha256 = $build.candidate_sha256
                    commit_sha = $sourceCommit; pipeline_id = $pipelineId
                })
            }
            finally { [Environment]::SetEnvironmentVariable('MT5_AGENT_HTTP_PORT', $previousPort, 'Process') }
        }
        'smoke-control-plane' {
            $build = Assert-BuildEvidence
            $inspection = Test-CandidateCLI
            if ($inspection.ready -or $inspection.runtime.worker_available -or
                $inspection.runtime.runtime_state -notin @('RUNTIME_CONFIGURATION_UNAVAILABLE', 'RUNTIME_UNAVAILABLE')) {
                throw 'No-MT5 Runner did not report the expected unavailable/degraded Worker state'
            }
            $port = Get-FreeLoopbackPort
            $script:CandidateProcess = $null
            try {
                $script:CandidateProcess = Start-CandidateAgent -Port $port
                $agentEvidence = Get-ProcessEvidence -ProcessId $script:CandidateProcess.Id
                if ($agentEvidence.session_id -ne 0) { throw 'Control-plane candidate Agent is not running in Session 0' }
                $health = Wait-CandidateHealth -Port $port -TimeoutSeconds 45
                if ($health.agent_state -ne 'AGENT_RUNNING' -or $health.ok -ne $false -or
                    $health.runtime_state -notin @('RUNTIME_CONFIGURATION_UNAVAILABLE', 'RUNTIME_UNAVAILABLE') -or
                    ((Test-HasProperty -Value $health.runtime -Name 'worker_available') -and $health.runtime.worker_available -eq $true)) {
                    throw 'Candidate did not remain alive in the expected degraded no-Worker state'
                }
                $null = Assert-BuildEvidence
                Write-JsonEvidence -Path (Join-Path $reportRoot 'control-plane.json') -Value ([ordered]@{
                    schema_version = '1'; test = 'control-plane-degraded-startup'; status = 'PASS'
                    pipeline_id = $pipelineId; commit_sha = $sourceCommit; candidate_version = $version
                    candidate_filename = $build.candidate_filename; candidate_sha256 = $build.candidate_sha256
                    agent = $agentEvidence
                    runtime_state = $health.runtime_state; worker_available = $false; health = 'AGENT_RUNNING_DEGRADED'
                })
                Write-Output "Control-plane candidate stayed alive in Session 0; runtime_state=$($health.runtime_state); SHA256=$($build.candidate_sha256)"
            }
            finally { Stop-CandidateAgent -Process $script:CandidateProcess; $script:CandidateProcess = $null }
        }
        'smoke-mt5-runtime' {
            $build = Assert-BuildEvidence
            $runtimeConfiguration = Get-ConfiguredRuntime
            $inspection = Test-CandidateCLI
            $preflight = Assert-WorkerTaskAndPreflight -RuntimeConfiguration $runtimeConfiguration -Inspection $inspection
            $port = Get-FreeLoopbackPort
            $script:CandidateProcess = $null
            try {
                $script:CandidateProcess = Start-CandidateAgent -Port $port
                $agentEvidence = Get-ProcessEvidence -ProcessId $script:CandidateProcess.Id
                if ($agentEvidence.session_id -ne 0 -or $agentEvidence.principal -ine $preflight.Caller) {
                    throw 'Candidate Agent process identity/session differs from the Session 0 control caller'
                }
                $health = Wait-CandidateHealth -Port $port -TimeoutSeconds 240 -RequireConnected
                if ($health.agent_state -ne 'AGENT_RUNNING' -or $health.runtime_state -ne 'MT5_CONNECTED') {
                    throw 'Candidate did not reach AGENT_RUNNING + MT5_CONNECTED'
                }
                $runtime = $health.runtime
                $worker = $runtime.worker_identity
                if ($worker.account -ine $preflight.RuntimePrincipal -or $worker.session_id -le 0 -or
                    $worker.session_id -ne $runtime.terminal_session_id -or $runtime.mt5_connected -ne $true) {
                    throw 'Live Worker and terminal health identity/session validation failed'
                }
                $terminal = Get-ProcessEvidence -ProcessId ([int]$runtime.terminal_pid)
                if ($terminal.principal -ine $preflight.RuntimePrincipal -or $terminal.sid -ine $worker.sid -or
                    $terminal.session_id -ne $worker.session_id -or
                    $terminal.executable -ine [string]$runtimeConfiguration.TerminalPath) {
                    throw 'Independent terminal owner/session/path validation failed'
                }
                $symbols = Invoke-AgentCommand -Port $port -CommandType 'mt5.get_symbols_total' -TimeoutSeconds 30
                Assert-CommandSuccess -Response $symbols -CommandType 'mt5.get_symbols_total'
                if ((Test-HasProperty -Value $symbols.data -Name 'error') -or
                    ($symbols.data.result -isnot [int] -and $symbols.data.result -isnot [long]) -or $symbols.data.result -lt 0) {
                    throw 'symbols_total safe read returned an invalid result'
                }
                $terminalVersion = Invoke-AgentCommand -Port $port -CommandType 'mt5.get_terminal_version' -TimeoutSeconds 30
                Assert-CommandSuccess -Response $terminalVersion -CommandType 'mt5.get_terminal_version'
                if ((Test-HasProperty -Value $terminalVersion.data -Name 'error') -or
                    $terminalVersion.data.result -isnot [array] -or $terminalVersion.data.result.Count -lt 2) {
                    throw 'Terminal version safe read returned an invalid result'
                }
                $account = Invoke-AgentCommand -Port $port -CommandType 'mt5.get_account_information' -TimeoutSeconds 30
                Assert-CommandSuccess -Response $account -CommandType 'mt5.get_account_information'
                if ((Test-HasProperty -Value $account.data -Name 'error') -or $null -eq $account.data.result) {
                    throw 'Account-information safe read returned an invalid result'
                }
                if ($account.data.result -is [System.Collections.IDictionary]) {
                    $accountFieldCount = $account.data.result.Count
                } else {
                    $accountFieldCount = @($account.data.result.PSObject.Properties).Count
                }
                $finalResponse = Invoke-AgentCommand -Port $port -CommandType 'agent.get_health' -TimeoutSeconds 30
                Assert-CommandSuccess -Response $finalResponse -CommandType 'agent.get_health'
                $finalHealth = $finalResponse.data
                if ($finalHealth.agent_state -ne 'AGENT_RUNNING' -or $finalHealth.runtime_state -ne 'MT5_CONNECTED' -or
                    $finalHealth.runtime.mt5_connected -ne $true -or
                    $finalHealth.runtime.worker_identity.pid -ne $worker.pid) {
                    throw 'Persistent final health or Worker identity changed after safe reads'
                }
                $terminalBuild = $finalHealth.runtime.terminal_build
                if (-not $terminalBuild) { $terminalBuild = $terminalVersion.data.result[1] }
                $null = Assert-BuildEvidence
                $afterHash = Get-BinaryHash
                if ($afterHash -ne $build.candidate_sha256) { throw 'Candidate SHA-256 changed during runtime integration' }
                Write-JsonEvidence -Path (Join-Path $reportRoot 'mt5-runtime.json') -Value ([ordered]@{
                    schema_version = '1'; pipeline_id = $pipelineId; commit_sha = $sourceCommit
                    candidate_version = $version; candidate_filename = $build.candidate_filename
                    candidate_sha256 = $build.candidate_sha256; candidate_sha256_after = $afterHash; status = 'PASS'
                    agent = $agentEvidence
                    worker = [ordered]@{ principal = $worker.account; pid = $worker.pid; sid = $worker.sid
                        session_id = $worker.session_id; protocol_version = $runtime.protocol_version }
                    terminal = [ordered]@{ pid = $terminal.pid; principal = $terminal.principal; sid = $terminal.sid
                        session_id = $terminal.session_id; path = $terminal.executable; build = $terminalBuild }
                    runtime_state = $finalHealth.runtime_state
                    symbols_total_success = $true; symbols_total = $symbols.data.result
                    terminal_version_success = $true; terminal_version = @($terminalVersion.data.result)
                    account_information_success = $true; account_information_field_count = $accountFieldCount
                    final_health = 'AGENT_RUNNING + MT5_CONNECTED'
                })
                Write-Output "Runtime integration passed; Worker=$($worker.account) session=$($worker.session_id); terminal_pid=$($terminal.pid); symbols_total=$($symbols.data.result); terminal_build=$terminalBuild; account fields=$accountFieldCount; SHA256=$afterHash"
            }
            finally { Stop-CandidateAgent -Process $script:CandidateProcess; $script:CandidateProcess = $null }
        }
        'package' {
            $checksumPath = Join-Path $repoRoot 'sha256.txt'
            $releaseEvidencePath = Join-Path $reportRoot 'release-evidence.json'
            if (Test-Path -LiteralPath $checksumPath) { Remove-Item -LiteralPath $checksumPath }
            if (Test-Path -LiteralPath $releaseEvidencePath) { Remove-Item -LiteralPath $releaseEvidencePath }
            $build = Assert-BuildEvidence
            $binaryHash = Get-BinaryHash
            $control = Get-Content -LiteralPath (Join-Path $reportRoot 'control-plane.json') -Raw | ConvertFrom-Json
            $runtime = Get-Content -LiteralPath (Join-Path $reportRoot 'mt5-runtime.json') -Raw | ConvertFrom-Json
            foreach ($receipt in @($control, $runtime)) {
                if ($receipt.schema_version -ne '1' -or $receipt.status -ne 'PASS' -or
                    $receipt.pipeline_id -ne $pipelineId -or $receipt.commit_sha -ne $sourceCommit -or
                    $receipt.candidate_version -ne $version -or $receipt.candidate_filename -ne "$ArtifactName.exe" -or
                    $receipt.candidate_sha256 -ne $binaryHash) {
                    throw 'Control-plane/runtime evidence provenance does not match the packaged candidate'
                }
            }
            if ($control.test -ne 'control-plane-degraded-startup' -or $control.health -ne 'AGENT_RUNNING_DEGRADED' -or
                $control.worker_available -ne $false -or
                $control.runtime_state -notin @('RUNTIME_CONFIGURATION_UNAVAILABLE', 'RUNTIME_UNAVAILABLE')) {
                throw 'No-MT5 control-plane evidence is incomplete or inconsistent'
            }
            if ($runtime.candidate_sha256_after -ne $binaryHash -or $runtime.runtime_state -ne 'MT5_CONNECTED' -or
                $runtime.final_health -ne 'AGENT_RUNNING + MT5_CONNECTED' -or
                $runtime.symbols_total_success -ne $true -or $runtime.terminal_version_success -ne $true -or
                $runtime.account_information_success -ne $true -or $runtime.agent.session_id -ne 0 -or
                $runtime.worker.protocol_version -ne '1' -or $runtime.worker.session_id -le 0 -or
                $runtime.terminal.session_id -ne $runtime.worker.session_id -or
                $runtime.terminal.principal -ine $runtime.worker.principal -or
                $runtime.terminal.sid -ine $runtime.worker.sid -or
                [long]$runtime.account_information_field_count -lt 0) {
                throw 'Runtime acceptance evidence is incomplete or inconsistent'
            }
            "SHA256=$binaryHash" | Set-Content -LiteralPath (Join-Path $repoRoot 'sha256.txt') -Encoding utf8
            Write-JsonEvidence -Path (Join-Path $reportRoot 'release-evidence.json') -Value ([ordered]@{
                schema_version = '1'; pipeline_id = $pipelineId; commit_sha = $sourceCommit
                candidate_version = $version; candidate_filename = "$ArtifactName.exe"
                candidate_sha256 = $binaryHash; build_once = $true; post_smoke_rebuild = $false
                control_plane_gate = 'PASS'; mt5_runtime_gate = 'PASS'; release_eligible = $true
            })
            Write-Output "Packaging the exact smoke-tested binary without rebuilding: SHA256=$binaryHash"
        }
    }
}
finally {
    Pop-Location
}
