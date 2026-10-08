[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ArchivePath,
    [Parameter(Mandatory = $true)][string]$BuildReportPath,
    [Parameter(Mandatory = $true)][string]$ExpectedCommit,
    [Parameter(Mandatory = $true)][string]$ExpectedPipelineId,
    [Parameter(Mandatory = $true)][string]$ExtractionDirectory,
    [switch]$LaunchSmoke
)

$ErrorActionPreference = 'Stop'
$archive = (Resolve-Path -LiteralPath $ArchivePath).Path
$buildReportFile = (Resolve-Path -LiteralPath $BuildReportPath).Path
$report = Get-Content -LiteralPath $buildReportFile -Raw | ConvertFrom-Json
$archiveBefore = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($archiveBefore -ne $report.package_sha256) { throw 'Package archive hash differs from the immutable build report.' }
if ($report.source_commit -ne $ExpectedCommit -or $report.pipeline_id -ne $ExpectedPipelineId) {
    throw 'Build report provenance does not match the current pipeline.'
}

$workingDirectory = (Get-Location).ProviderPath
if ([System.IO.Path]::IsPathRooted($ExtractionDirectory)) {
    $target = [System.IO.Path]::GetFullPath($ExtractionDirectory)
} else {
    $target = [System.IO.Path]::GetFullPath((Join-Path $workingDirectory $ExtractionDirectory))
}
if (Test-Path -LiteralPath $target) {
    if ((Get-ChildItem -LiteralPath $target -Force | Measure-Object).Count -gt 0) {
        throw "Extraction directory must be empty: $target"
    }
} else { New-Item -ItemType Directory -Path $target -Force | Out-Null }

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($archive)
try {
    $seen = @{}
    $expandedBytes = [long]0
    foreach ($entry in $zip.Entries) {
        $name = $entry.FullName.Replace('\', '/')
        if ($name.StartsWith('/') -or $name -match '(^|/)\.\.?(/|$)' -or $name -match '^[A-Za-z]:') {
            throw "Archive contains an unsafe path: $name"
        }
        if ($seen.ContainsKey($name)) { throw "Archive contains a duplicate entry: $name" }
        $seen[$name] = $true
        $expandedBytes += [long]$entry.Length
        if ($expandedBytes -gt 268435456) { throw 'Package expands beyond the 256 MiB validation limit.' }
    }
} finally { $zip.Dispose() }
[System.IO.Compression.ZipFile]::ExtractToDirectory($archive, $target)

$roots = @(Get-ChildItem -LiteralPath $target -Directory)
if ($roots.Count -ne 1 -or $roots[0].Name -ne 'MT5Agent-Desktop-v0.1.4-windows-x64' -or
    @(Get-ChildItem -LiteralPath $target -File).Count -ne 0) {
    throw 'Package does not have the expected single versioned root directory.'
}
$packageRoot = $roots[0].FullName
$manifestPath = Join-Path $packageRoot 'MANIFEST.json'
$checksumsPath = Join-Path $packageRoot 'SHA256SUMS.txt'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.version -ne '0.1.4' -or $manifest.architecture -ne 'x64' -or
    $manifest.framework_target -ne '.NET Framework 4.8' -or
    $manifest.source_commit -ne $ExpectedCommit -or $manifest.pipeline_id -ne $ExpectedPipelineId -or
    $manifest.build_job_id -ne $report.build_job_id) {
    throw 'Embedded package manifest has mismatched product/build provenance.'
}

$rootPrefix = $packageRoot.TrimEnd('\') + '\'
$expectedFiles = @{}
foreach ($item in $manifest.files) {
    $manifestRelative = [string]$item.path
    if ($manifestRelative.StartsWith('/') -or $manifestRelative -match '(^|/)\.\.?(/|$)' -or $manifestRelative -match '^[A-Za-z]:') {
        throw "Manifest contains an unsafe path: $manifestRelative"
    }
    if ($expectedFiles.ContainsKey($manifestRelative)) { throw "Manifest contains a duplicate path: $manifestRelative" }
    $expectedFiles[$manifestRelative] = [string]$item.sha256
    $relative = $item.path.Replace('/', '\')
    $fullPath = [System.IO.Path]::GetFullPath((Join-Path $packageRoot $relative))
    if (-not $fullPath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Manifest file escaped package root: $($item.path)"
    }
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) { throw "Manifest file is missing: $($item.path)" }
    $actual = (Get-FileHash -LiteralPath $fullPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $item.sha256) { throw "Manifest hash mismatch: $($item.path)" }
    if ((Get-Item -LiteralPath $fullPath).Length -ne [long]$item.size_bytes) { throw "Manifest size mismatch: $($item.path)" }
}

$checksumFiles = @{}
foreach ($line in Get-Content -LiteralPath $checksumsPath) {
    if ($line -notmatch '^([0-9a-f]{64})  (.+)$') { throw 'SHA256SUMS.txt contains an invalid row.' }
    $expectedHash = $Matches[1]
    $relativeName = $Matches[2]
    if ($checksumFiles.ContainsKey($relativeName)) { throw "SHA256SUMS.txt contains a duplicate path: $relativeName" }
    $checksumFiles[$relativeName] = $expectedHash
    $relative = $relativeName.Replace('/', '\')
    $fullPath = [System.IO.Path]::GetFullPath((Join-Path $packageRoot $relative))
    if (-not $fullPath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath $fullPath -PathType Leaf)) { throw "Checksum path is missing or unsafe: $relative" }
    $actual = (Get-FileHash -LiteralPath $fullPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $expectedHash) { throw "Checksum mismatch: $relative" }
}

if ($checksumFiles.Count -ne ($expectedFiles.Count + 1) -or -not $checksumFiles.ContainsKey('MANIFEST.json')) {
    throw 'SHA256SUMS.txt does not cover exactly the manifest and declared package payload.'
}
foreach ($path in $expectedFiles.Keys) {
    if (-not $checksumFiles.ContainsKey($path) -or $checksumFiles[$path] -ne $expectedFiles[$path]) {
        throw "Checksum list and manifest disagree for: $path"
    }
}
$actualPayloadPaths = @(Get-ChildItem -LiteralPath $packageRoot -File -Recurse | ForEach-Object {
    $_.FullName.Substring($packageRoot.Length).TrimStart('\').Replace('\', '/')
} | Where-Object { $_ -ne 'MANIFEST.json' -and $_ -ne 'SHA256SUMS.txt' })
if ($actualPayloadPaths.Count -ne $expectedFiles.Count) { throw 'Extracted package contains undeclared or missing payload files.' }
foreach ($path in $actualPayloadPaths) {
    if (-not $expectedFiles.ContainsKey($path)) { throw "Extracted package contains an undeclared payload file: $path" }
}

$appPath = Join-Path $packageRoot 'app\MT5Agent.Desktop.exe'
if (-not (Test-Path -LiteralPath $appPath -PathType Leaf)) { throw 'Desktop executable is missing from the package.' }
$appHash = (Get-FileHash -LiteralPath $appPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($appHash -ne $report.desktop_executable_sha256) { throw 'Packaged executable differs from the built/tested executable.' }
$signing = Get-AuthenticodeSignature -LiteralPath $appPath
$launchResult = 'NOT_RUN'
if ($LaunchSmoke) {
    $process = Start-Process -FilePath $appPath -WorkingDirectory (Split-Path -Parent $appPath) -PassThru
    try {
        Start-Sleep -Seconds 3
        $process.Refresh()
        if ($process.HasExited) { throw "Packaged WPF app exited during startup smoke (code $($process.ExitCode))." }
        $launchResult = 'PROCESS_ALIVE_AFTER_3S_NONINTERACTIVE'
    } finally {
        if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    }
}
$archiveAfter = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($archiveAfter -ne $archiveBefore) { throw 'Package archive changed during validation.' }

[ordered]@{
    schema_version = 1
    status = 'PASS'
    archive_sha256_before = $archiveBefore
    archive_sha256_after = $archiveAfter
    desktop_executable_sha256 = $appHash
    source_commit = $ExpectedCommit
    pipeline_id = $ExpectedPipelineId
    build_job_id = $report.build_job_id
    file_count = @($manifest.files).Count
    authenticode_status = [string]$signing.Status
    launch_smoke = $launchResult
    extraction_directory = $target
} | ConvertTo-Json -Depth 5
