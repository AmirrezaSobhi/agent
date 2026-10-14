[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$InstallerPath,[Parameter(Mandatory=$true)][string]$ManifestPath)
$ErrorActionPreference = 'Stop'
$installer = (Resolve-Path -LiteralPath $InstallerPath).Path
$manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
$version = & (Join-Path $PSScriptRoot '..\Get-MT5AgentVersion.ps1')
if ($manifest.schema_version -ne 1 -or $manifest.product -ne 'MT5Agent' -or $manifest.version -ne $version -or
    $manifest.architecture -ne 'x64' -or $manifest.setup_filename -ne (Split-Path -Leaf $installer)) { throw 'Installer manifest identity/provenance is invalid.' }
$hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -ne $manifest.setup_sha256) { throw 'Installer SHA-256 differs from its build manifest.' }
$sum = (Get-Content -LiteralPath ([IO.Path]::ChangeExtension($installer, '.sha256')) -Raw).Trim()
if ($sum -ne "$hash  $(Split-Path -Leaf $installer)") { throw 'Installer SHA-256 sidecar does not match setup bytes.' }
if ($manifest.source_commit -ne $env:CI_COMMIT_SHA -or $manifest.pipeline_id -ne $env:CI_PIPELINE_ID -or
    $manifest.installer_build_job_id -ne $env:INSTALLER_BUILD_JOB_ID -or $manifest.installer_build_job_id -notmatch '^\d+$') { throw 'Installer build provenance does not match this verification job.' }
foreach ($job in @($manifest.component_build_jobs.PSObject.Properties.Value)) { if ([string]$job -notmatch '^\d+$') { throw 'Component build job provenance is incomplete.' } }
if (@($manifest.files | Where-Object { $_.path -like 'Agent/*' }).Count -lt 1 -or
    @($manifest.files | Where-Object { $_.path -like 'Worker/*' }).Count -lt 1 -or
    @($manifest.files | Where-Object { $_.path -like 'Desktop/*' }).Count -lt 1 -or
    @($manifest.files | Where-Object { $_.path -like 'Service/*' }).Count -lt 1) { throw 'Manifest does not prove all four product payloads.' }
if ($manifest.files | Where-Object { $_.path -match '(?i)(password|token|secret|credential)' }) { throw 'Potential secret-bearing path found in packaged manifest.' }
$signature = Get-AuthenticodeSignature -FilePath $installer
if ($signature.Status -notin @('NotSigned','Valid')) { throw 'Setup Authenticode signature is invalid.' }
[ordered]@{schema_version=1; status='PASS'; installer=(Split-Path -Leaf $installer); sha256=$hash; installer_size_bytes=[long](Get-Item $installer).Length; manifest_sha256=(Get-FileHash -LiteralPath $ManifestPath -Algorithm SHA256).Hash.ToLowerInvariant(); sidecar_sha256=(Get-FileHash -LiteralPath ([IO.Path]::ChangeExtension($installer, '.sha256')) -Algorithm SHA256).Hash.ToLowerInvariant(); source_commit=$env:CI_COMMIT_SHA; pipeline_id=$env:CI_PIPELINE_ID; installer_build_job_id=$env:INSTALLER_BUILD_JOB_ID; installer_verify_job_id=$env:CI_JOB_ID; install_smoke='DEFERRED: packaging job does not perform real VM installation'; components=@('Desktop','Python Agent executable','Windows Service host','Python MT5 Worker executable') } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath './reports/unified-installer-verification.json' -Encoding utf8
