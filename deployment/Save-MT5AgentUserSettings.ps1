[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$InstallPath,[string]$TerminalPath)
$ErrorActionPreference = 'Stop'
$install = [IO.Path]::GetFullPath($InstallPath).TrimEnd('\')
$expected = [IO.Path]::GetFullPath((Join-Path $env:ProgramFiles 'MT5Agent')).TrimEnd('\')
if (-not [string]::Equals($install, $expected, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'INSTALL_PATH_MUST_BE_PROTECTED_PROGRAM_FILES_MT5AGENT_DIRECTORY'
}
$keyPath = 'HKCU:\Software\MT5Agent\Desktop'
New-Item -Path $keyPath -Force | Out-Null
New-ItemProperty -LiteralPath $keyPath -Name InstallPath -PropertyType String -Value (Join-Path $install 'Desktop') -Force | Out-Null
if (-not [string]::IsNullOrWhiteSpace($TerminalPath)) {
    $terminal = [IO.Path]::GetFullPath($TerminalPath)
    if ((Split-Path -Leaf $terminal) -ine 'terminal64.exe' -or -not (Test-Path -LiteralPath $terminal -PathType Leaf)) {
        throw 'MT5_TERMINAL_EXECUTABLE_INVALID'
    }
    New-ItemProperty -LiteralPath $keyPath -Name TerminalPath -PropertyType String -Value $terminal -Force | Out-Null
}
