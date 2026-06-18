# Lance l'interface "Mission Control" (tableau de bord web local)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$port = if ($args.Count -gt 0) { $args[0] } else { 7000 }
python "$root\agency.py" dashboard $port
