[CmdletBinding()]
param([Parameter(Mandatory = $true)][string] $CompilerPath)

$ErrorActionPreference = 'Stop'
$compiler = (Resolve-Path -LiteralPath $CompilerPath).Path
$testRoot = Join-Path $env:TEMP ('mt5agent-required-operation-' + [Guid]::NewGuid().ToString('N'))
$source = Join-Path $PSScriptRoot 'tests\RequiredOperationSmoke.iss'
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null

try {
    foreach ($expectedExitCode in @(0, 37)) {
        $caseRoot = Join-Path $testRoot ([string]$expectedExitCode)
        New-Item -ItemType Directory -Path $caseRoot -Force | Out-Null
        & $compiler "/DOutputRoot=$caseRoot" "/DExitCode=$expectedExitCode" $source
        if ($LASTEXITCODE -ne 0) { throw "Required operation smoke setup did not compile for child exit $expectedExitCode." }

        foreach ($mode in @('/SILENT', '/VERYSILENT')) {
            $modeName = $mode.TrimStart('/').ToLowerInvariant()
            $logPath = Join-Path $caseRoot "setup-$modeName.log"
            $installPath = Join-Path $caseRoot "install-$modeName"
            $arguments = "$mode /SUPPRESSMSGBOXES /SP- /NORESTART /DIR=`"$installPath`" /LOG=`"$logPath`""
            $process = Start-Process -FilePath (Join-Path $caseRoot 'MT5Agent-Required-Operation-Smoke.exe') -ArgumentList $arguments -Wait -PassThru
            if (-not (Test-Path -LiteralPath $logPath -PathType Leaf)) { throw "$mode did not create an Inno Setup log for child exit $expectedExitCode." }
            $log = Get-Content -LiteralPath $logPath -Raw

            if ($expectedExitCode -eq 0) {
                if ($process.ExitCode -ne 0) { throw "$mode reported failure for a required operation that exited 0. Log: $logPath`n$log" }
                if ($log -notmatch 'Required operation exit code: Synthetic failure probe=0') { throw "$mode did not log the successful required-operation exit code." }
            } else {
                if ($process.ExitCode -eq 0) { throw "$mode returned success although a required operation exited $expectedExitCode. Log: $logPath`n$log" }
                if ($log -notmatch "Required operation exit code: Synthetic failure probe=$expectedExitCode" -or
                    $log -notmatch "Synthetic failure probe failed with exit code $expectedExitCode") {
                    throw "$mode did not preserve the required-operation failure details in its Inno log. Log: $logPath`n$log"
                }
            }
            Write-Host "$mode required-operation propagation PASS (child=$expectedExitCode, setup=$($process.ExitCode))."
        }
    }
}
finally {
    Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}
