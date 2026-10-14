[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$InstallRoot)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($InstallRoot).TrimEnd('\') + '\'
$expectedRoot = [IO.Path]::GetFullPath((Join-Path $env:ProgramFiles 'MT5Agent')).TrimEnd('\') + '\'
if (-not [string]::Equals($root, $expectedRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'INSTALL_ROOT_MUST_BE_PROTECTED_PROGRAM_FILES_PATH' }
$taskName = 'MT5Agent Interactive MT5 Runtime Worker'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $task) { exit 0 }
$execute = [IO.Path]::GetFullPath([string]$task.Actions[0].Execute)
if (-not $execute.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) { throw 'REFUSING_TO_REMOVE_UNRELATED_SCHEDULED_TASK' }
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
