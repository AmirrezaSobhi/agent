[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$AgentPath,
  [Parameter(Mandatory=$true)][string]$DesktopPath,
  [Parameter(Mandatory=$true)][string]$WorkerPath,
  [Parameter(Mandatory=$true)][string]$ServicePath,
  [Parameter(Mandatory=$true)][string]$OutputPath
)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$version = '0.1.5'
$arch = 'windows-x64'
$stage = Join-Path $repo 'deployment\installer\stage'
if ([IO.Path]::IsPathRooted($OutputPath)) {
  $output = [IO.Path]::GetFullPath($OutputPath)
} else {
  $output = [IO.Path]::GetFullPath((Join-Path $repo $OutputPath))
}
if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stage, $output | Out-Null
$agent = Get-ChildItem -LiteralPath $AgentPath -File -Filter 'MT5Agent-v*.exe' | Select-Object -First 1
$worker = Get-ChildItem -LiteralPath $WorkerPath -File -Filter 'MT5AgentWorker-v*.exe' | Select-Object -First 1
foreach ($item in @($agent, $worker)) { if (-not $item) { throw 'Agent or bundled interactive Worker executable is missing.' } }
$desktopExe = Join-Path $DesktopPath 'MT5Agent.Desktop.exe'
$serviceExe = Join-Path $ServicePath 'MT5Agent.Service.exe'
foreach ($path in @($desktopExe, $serviceExe)) { if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required installer component missing: $path" } }
$agentReport = Get-Content -LiteralPath (Join-Path $repo 'reports\build.json') -Raw | ConvertFrom-Json
$desktopReport = Get-Content -LiteralPath (Join-Path $repo 'reports\desktop-build.json') -Raw | ConvertFrom-Json
$workerReport = Get-Content -LiteralPath (Join-Path $repo 'reports\worker-build.json') -Raw | ConvertFrom-Json
foreach ($report in @($agentReport,$desktopReport,$workerReport)) {
  if ($report.source_commit -ne $env:CI_COMMIT_SHA -or $report.pipeline_id -ne $env:CI_PIPELINE_ID -or -not $report.build_job_id) { throw 'Component build provenance is absent or from another source pipeline.' }
}
if ($agentReport.candidate_sha256 -ne (Get-FileHash $agent.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -or
    $desktopReport.desktop_executable_sha256 -ne (Get-FileHash $desktopExe -Algorithm SHA256).Hash.ToLowerInvariant() -or
    $workerReport.sha256 -ne (Get-FileHash $worker.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -or
    $workerReport.interactive_session_required -ne $true -or $workerReport.terminal_included -ne $false) {
  throw 'At least one installer component differs from its original build evidence.'
}
foreach ($jobId in @($env:AGENT_BUILD_JOB_ID,$env:DESKTOP_BUILD_JOB_ID,$env:WORKER_BUILD_JOB_ID)) {
  if ($jobId -notmatch '^\d+$') { throw 'Component artifact job provenance is missing.' }
}
foreach ($component in @('Agent','Worker','Desktop','Service','Support')) { New-Item -ItemType Directory -Force -Path (Join-Path $stage $component) | Out-Null }
Copy-Item -LiteralPath $agent.FullName -Destination (Join-Path $stage 'Agent')
Copy-Item -LiteralPath $worker.FullName -Destination (Join-Path $stage 'Worker')
Get-ChildItem -LiteralPath $DesktopPath -File | Where-Object { $_.Extension -ne '.pdb' } | Copy-Item -Destination (Join-Path $stage 'Desktop')
Copy-Item -LiteralPath $serviceExe -Destination (Join-Path $stage 'Service')
Copy-Item -LiteralPath (Join-Path $repo 'deployment\Install-MT5AgentService.ps1') -Destination (Join-Path $stage 'Support\Install-MT5AgentService.ps1')
Copy-Item -LiteralPath (Join-Path $repo 'deployment\Register-PackagedMT5Worker.ps1') -Destination (Join-Path $stage 'Worker\Register-PackagedMT5Worker.ps1')
Copy-Item -LiteralPath (Join-Path $repo 'deployment\Unregister-PackagedMT5Worker.ps1') -Destination (Join-Path $stage 'Worker\Unregister-PackagedMT5Worker.ps1')
Copy-Item -LiteralPath (Join-Path $repo 'deployment\Save-MT5AgentUserSettings.ps1') -Destination (Join-Path $stage 'Support\Save-MT5AgentUserSettings.ps1')
Copy-Item -LiteralPath (Join-Path $repo 'deployment\Set-MT5RuntimeConfiguration.ps1') -Destination (Join-Path $stage 'Support\Set-MT5RuntimeConfiguration.ps1')
if (-not (Test-Path -LiteralPath (Join-Path $stage 'Desktop\MT5Agent.Desktop.exe'))) { throw 'Desktop payload copy failed.' }

$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
  $tools = Join-Path $env:TEMP ('mt5agent-inno-' + [Guid]::NewGuid().ToString('N'))
  New-Item -ItemType Directory -Path $tools | Out-Null
  $download = Join-Path $tools 'innosetup.exe'
  $url = 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe'
  Invoke-WebRequest -Uri $url -OutFile $download -UseBasicParsing
  $signature = Get-AuthenticodeSignature -FilePath $download
  if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Pyrsys') { throw 'Downloaded Inno Setup compiler signature could not be verified.' }
  $innoRoot = Join-Path $tools 'compiler'
  $install = Start-Process -FilePath $download -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER',"/DIR=$innoRoot") -PassThru -Wait
  if ($install.ExitCode -ne 0) { throw 'Could not provision the pinned Inno Setup compiler in the build job.' }
  $isccPath = Join-Path $innoRoot 'ISCC.exe'
} else { $isccPath = $iscc.Source }
if (-not (Test-Path -LiteralPath $isccPath -PathType Leaf)) { throw 'ISCC.exe is unavailable.' }
$setupScript = Join-Path $PSScriptRoot 'MT5Agent.iss'
& $isccPath "/DSourceRoot=$repo" "/DProductVersion=$version" "/DOutputRoot=$output" $setupScript
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed with code $LASTEXITCODE" }
$setupFile = Join-Path $output "MT5Agent-Setup-v$version-$arch.exe"
if (-not (Test-Path -LiteralPath $setupFile -PathType Leaf)) { throw 'Inno Setup did not produce the expected single-file installer.' }
$payload = @()
Get-ChildItem -LiteralPath $stage -File -Recurse | Sort-Object FullName | ForEach-Object {
  $payload += [ordered]@{ path=$_.FullName.Substring($stage.Length).TrimStart('\').Replace('\','/'); size_bytes=[long]$_.Length; sha256=(Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
}
$manifest = [ordered]@{
  schema_version=1; product='MT5Agent'; version=$version; architecture='x64'; installer='Inno Setup 6.7.3'
  install_scope='per-machine, elevated only for Service/files under Program Files'; service_identity='LocalSystem'
  worker_identity='separate configured interactive Windows principal; no password or autologon stored'
  mt5='external existing terminal only; no MT5 installer redistributed'
  source_commit=$env:CI_COMMIT_SHA; pipeline_id=$env:CI_PIPELINE_ID; installer_build_job_id=$env:CI_JOB_ID
  component_build_jobs=[ordered]@{desktop=$env:DESKTOP_BUILD_JOB_ID;agent=$env:AGENT_BUILD_JOB_ID;worker=$env:WORKER_BUILD_JOB_ID;service=$env:CI_JOB_ID}
  setup_filename=(Split-Path -Leaf $setupFile); setup_size_bytes=[long](Get-Item $setupFile).Length
  setup_sha256=(Get-FileHash $setupFile -Algorithm SHA256).Hash.ToLowerInvariant()
  signing='unsigned internal artifact; public distribution prohibited'; files=$payload
}
$manifestPath = Join-Path $output 'MT5Agent-Setup-v0.1.5-windows-x64.manifest.json'
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
$sumPath = Join-Path $output 'MT5Agent-Setup-v0.1.5-windows-x64.sha256'
Set-Content -LiteralPath $sumPath -Value "$($manifest.setup_sha256)  $(Split-Path -Leaf $setupFile)" -Encoding ascii
Write-Host "Built $setupFile SHA-256 $($manifest.setup_sha256)"
