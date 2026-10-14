[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$CompilerPath
)
$ErrorActionPreference = 'Stop'
$compiler = (Resolve-Path -LiteralPath $CompilerPath).Path
$testRoot = Join-Path $env:TEMP ('mt5agent-wizard-smoke-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null
try {
  $setupPath = Join-Path $testRoot 'MT5Agent-Wizard-Smoke.exe'
  $issPath = Join-Path $PSScriptRoot 'tests\WizardSmoke.iss'
  & $compiler "/DOutputRoot=$testRoot" $issPath
  if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $setupPath -PathType Leaf)) {
    throw 'The shared Wizard smoke setup did not compile.'
  }

  foreach ($mode in @('/SILENT','/VERYSILENT')) {
    $modeName = $mode.TrimStart('/').ToLowerInvariant()
    $logPath = Join-Path $testRoot "wizard-$modeName.log"
    $installDir = Join-Path $testRoot 'Install'
    $argumentLine = "$mode /SUPPRESSMSGBOXES /SP- /NORESTART /DIR=`"$installDir`" /LOG=`"$logPath`""
    $process = Start-Process -FilePath $setupPath -ArgumentList $argumentLine -Wait -PassThru
    if ($process.ExitCode -ne 0) {
      $logText = if (Test-Path -LiteralPath $logPath -PathType Leaf) { Get-Content -LiteralPath $logPath -Raw } else { 'No installer log was created.' }
      throw "$mode Wizard smoke failed with exit code $($process.ExitCode). Log: $logPath`n$logText"
    }
    if (-not (Test-Path -LiteralPath $logPath -PathType Leaf)) { throw "$mode Wizard smoke did not produce an Inno Setup log." }
    $log = Get-Content -LiteralPath $logPath -Raw
    if ($log -match 'InitializeWizard raised an exception|List index out of bounds|is empty') {
      throw "$mode Wizard smoke log contains an initialization failure. Log: $logPath"
    }
    if ($log -notmatch 'MT5AgentWizard\.InitializeWizard completed \(silent\)\.') {
      throw "$mode log does not confirm the silent Wizard path completed. Log: $logPath"
    }
    if ($log -notmatch 'MT5AgentWizard\.GetTerminalPath completed:') { throw "$mode did not safely read the terminal path result. Log: $logPath" }
    Write-Host "$mode Wizard smoke PASS (exit $($process.ExitCode)); log: $logPath"
  }
}
finally {
  Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}
