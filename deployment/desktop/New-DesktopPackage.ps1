[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$BuildOutputPath,
    [Parameter(Mandatory = $true)][string]$TestOutputPath,
    [Parameter(Mandatory = $true)][string]$TestArtifactDirectory,
    [Parameter(Mandatory = $true)][string]$OutputDirectory,
    [Parameter(Mandatory = $true)][string]$SourceCommit,
    [Parameter(Mandatory = $true)][string]$PipelineId,
    [Parameter(Mandatory = $true)][string]$BuildJobId
)

$ErrorActionPreference = 'Stop'
$version = '0.1.4'
$architecture = 'windows-x64'
$archiveName = "MT5Agent-Desktop-v$version-$architecture.zip"
$folderName = "MT5Agent-Desktop-v$version-$architecture"
$buildOutput = (Resolve-Path -LiteralPath $BuildOutputPath).Path
$testOutput = (Resolve-Path -LiteralPath $TestOutputPath).Path
$workingDirectory = (Get-Location).ProviderPath
if ([System.IO.Path]::IsPathRooted($TestArtifactDirectory)) {
    $testArtifact = [System.IO.Path]::GetFullPath($TestArtifactDirectory)
} else {
    $testArtifact = [System.IO.Path]::GetFullPath((Join-Path $workingDirectory $TestArtifactDirectory))
}
if ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
    $outputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
} else {
    $outputDirectory = [System.IO.Path]::GetFullPath((Join-Path $workingDirectory $OutputDirectory))
}

if ($SourceCommit -notmatch '^[0-9a-f]{40}$') { throw 'SourceCommit must be a full lowercase Git SHA.' }
if ($PipelineId -notmatch '^\d+$' -or $BuildJobId -notmatch '^\d+$') { throw 'Pipeline and build job IDs must be numeric.' }

$appExe = Join-Path $buildOutput 'MT5Agent.Desktop.exe'
$testExe = Join-Path $testOutput 'MT5Agent.Desktop.Tests.exe'
$testAppExe = Join-Path $testOutput 'MT5Agent.Desktop.exe'
if (-not (Test-Path -LiteralPath $appExe -PathType Leaf)) { throw 'Release WPF executable is missing.' }
if (-not (Test-Path -LiteralPath $testExe -PathType Leaf)) { throw 'Release WPF test executable is missing.' }
if (-not (Test-Path -LiteralPath $testAppExe -PathType Leaf)) { throw 'WPF test output is missing its project-reference executable.' }

$versionInfo = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($appExe)
if ($versionInfo.FileVersion -ne "$version.0") { throw "WPF executable version '$($versionInfo.FileVersion)' does not match $version.0." }
$appHash = (Get-FileHash -LiteralPath $appExe -Algorithm SHA256).Hash.ToLowerInvariant()
$testReferenceHash = (Get-FileHash -LiteralPath $testAppExe -Algorithm SHA256).Hash.ToLowerInvariant()
if ($appHash -ne $testReferenceHash) { throw 'WPF test project reference differs from the packaged executable.' }
$frameworkRelease = (Get-ItemProperty -LiteralPath 'HKLM:SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full' -ErrorAction Stop).Release
$referenceAssemblies = 'C:\Program Files (x86)\Reference Assemblies\Microsoft\Framework\.NETFramework\v4.8'
if (-not (Test-Path -LiteralPath (Join-Path $referenceAssemblies 'PresentationFramework.dll'))) {
    throw '.NET Framework 4.8 reference assemblies are missing from the build host.'
}
$frameworkReferenceVersion = [System.Diagnostics.FileVersionInfo]::GetVersionInfo(
    (Join-Path $referenceAssemblies 'PresentationFramework.dll')).FileVersion

$readmePath = Join-Path $PSScriptRoot 'README.md'
$installPath = Join-Path $PSScriptRoot 'INSTALL.md'
foreach ($required in @($readmePath, $installPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Required distribution document is missing: $required" }
}

if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}
$archivePath = Join-Path $outputDirectory $archiveName
$reportPath = Join-Path $outputDirectory 'desktop-build.json'
if (Test-Path -LiteralPath $archivePath) { throw "Refusing to overwrite existing package: $archivePath" }

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('mt5agent-desktop-package-' + [Guid]::NewGuid().ToString('N'))
$stageRoot = Join-Path $tempRoot $folderName
$payloadRoot = Join-Path $stageRoot 'app'
$docsRoot = Join-Path $stageRoot 'docs'
try {
    New-Item -ItemType Directory -Path $payloadRoot, $docsRoot, $testArtifact -Force | Out-Null
    $allowedRuntimeNames = @('MT5Agent.Desktop.exe', 'MT5Agent.Desktop.exe.config', 'MT5Agent.Desktop.exe.manifest')
    $unexpectedBuildFiles = @(Get-ChildItem -LiteralPath $buildOutput -File | Where-Object {
        $_.Extension -ne '.pdb' -and $_.Name -notin $allowedRuntimeNames
    })
    if ($unexpectedBuildFiles.Count -gt 0) {
        throw "Unreviewed WPF build output would be excluded from the package: $($unexpectedBuildFiles.Name -join ', ')"
    }
    $releaseFiles = @(Get-ChildItem -LiteralPath $buildOutput -File | Where-Object {
        $_.Name -in $allowedRuntimeNames
    } | Sort-Object Name)
    if ($releaseFiles.Count -eq 0) { throw 'No allowed WPF runtime files were selected.' }
    foreach ($file in $releaseFiles) {
        Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $payloadRoot $file.Name)
    }
    Copy-Item -LiteralPath $readmePath -Destination (Join-Path $docsRoot 'README.md')
    Copy-Item -LiteralPath $installPath -Destination (Join-Path $docsRoot 'INSTALL.md')

    if (Test-Path -LiteralPath $testArtifact) {
        if ((Get-ChildItem -LiteralPath $testArtifact -Force | Measure-Object).Count -gt 0) {
            throw "Test artifact directory must be empty: $testArtifact"
        }
    }
    Get-ChildItem -LiteralPath $testOutput -File | Where-Object { $_.Extension -ne '.pdb' } | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $testArtifact $_.Name)
    }

    $payloadFiles = @(Get-ChildItem -LiteralPath $stageRoot -File -Recurse | Sort-Object FullName)
    $fileEntries = @()
    foreach ($file in $payloadFiles) {
        $relative = $file.FullName.Substring($stageRoot.Length).TrimStart('\').Replace('\', '/')
        $fileEntries += [ordered]@{
            path = $relative
            size_bytes = [long]$file.Length
            sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }

    $manifest = [ordered]@{
        schema_version = 1
        product = 'MT5Agent Desktop'
        version = $version
        architecture = 'x64'
        framework_target = '.NET Framework 4.8'
        runtime_prerequisite = '.NET Framework 4.8 or later; Windows 10 x64 is the Phase 6 validation target'
        source_commit = $SourceCommit
        pipeline_id = $PipelineId
        build_job_id = $BuildJobId
        code_signing = 'unsigned; not authorized for public distribution'
        dependencies = @('Microsoft .NET Framework WPF and Windows Forms assemblies supplied by the operating system')
        build_host_framework_release = [long]$frameworkRelease
        framework_reference_assembly_version = $frameworkReferenceVersion
        files = $fileEntries
    }
    $manifestJson = $manifest | ConvertTo-Json -Depth 8
    [System.IO.File]::WriteAllText((Join-Path $stageRoot 'MANIFEST.json'), $manifestJson + "`n", [System.Text.UTF8Encoding]::new($false))

    $sumLines = @()
    $sumTargets = @(Get-ChildItem -LiteralPath $stageRoot -File -Recurse | Sort-Object FullName)
    foreach ($file in $sumTargets) {
        $relative = $file.FullName.Substring($stageRoot.Length).TrimStart('\').Replace('\', '/')
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $sumLines += "$hash  $relative"
    }
    [System.IO.File]::WriteAllLines((Join-Path $stageRoot 'SHA256SUMS.txt'), $sumLines, [System.Text.UTF8Encoding]::new($false))

    Add-Type -AssemblyName System.IO.Compression
    $fileStream = [System.IO.FileStream]::new($archivePath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
    try {
        $zip = [System.IO.Compression.ZipArchive]::new($fileStream, [System.IO.Compression.ZipArchiveMode]::Create, $true)
        try {
            $epoch = [System.DateTimeOffset]::new(1980, 1, 1, 0, 0, 0, [System.TimeSpan]::Zero)
            $archiveFiles = @(Get-ChildItem -LiteralPath $tempRoot -File -Recurse | Sort-Object FullName)
            foreach ($file in $archiveFiles) {
                $relative = $file.FullName.Substring($tempRoot.Length).TrimStart('\').Replace('\', '/')
                $entry = $zip.CreateEntry($relative, [System.IO.Compression.CompressionLevel]::Optimal)
                $entry.LastWriteTime = $epoch
                $input = [System.IO.File]::OpenRead($file.FullName)
                try {
                    $entryStream = $entry.Open()
                    try { $input.CopyTo($entryStream) } finally { $entryStream.Dispose() }
                } finally { $input.Dispose() }
            }
        } finally { $zip.Dispose() }
    } finally { $fileStream.Dispose() }

    $report = [ordered]@{
        schema_version = 1
        product_version = $version
        source_commit = $SourceCommit
        pipeline_id = $PipelineId
        build_job_id = $BuildJobId
        msbuild_version = [System.Diagnostics.FileVersionInfo]::GetVersionInfo('C:\Windows\Microsoft.NET\Framework64\v4.0.30319\MSBuild.exe').FileVersion
        framework_runtime_release_on_build_host = [long]$frameworkRelease
        framework_reference_assembly_version = $frameworkReferenceVersion
        package_filename = $archiveName
        package_size_bytes = (Get-Item -LiteralPath $archivePath).Length
        package_sha256 = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
        desktop_executable_sha256 = $appHash
        test_project_reference_sha256 = $testReferenceHash
        status = 'BUILT'
    }
    [System.IO.File]::WriteAllText($reportPath, ($report | ConvertTo-Json -Depth 5) + "`n", [System.Text.UTF8Encoding]::new($false))
    $report | ConvertTo-Json -Depth 5
}
finally {
    if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
}
