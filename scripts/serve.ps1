# Sert le site livré en local : .\serve.ps1 <slug>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if ($args.Count -lt 1) { Write-Host "Usage : .\serve.ps1 <slug>"; exit 1 }
python "$root\agency.py" serve $args[0]
