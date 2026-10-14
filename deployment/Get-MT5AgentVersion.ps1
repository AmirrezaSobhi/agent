$ErrorActionPreference = 'Stop'
$source = Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\agent\__init__.py') -Raw
$match = [regex]::Match($source, '(?m)^__version__ = "((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))"\r?$')
if (-not $match.Success) { throw 'Canonical product version is missing or invalid.' }
$match.Groups[1].Value
