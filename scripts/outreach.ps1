# Outreach : génère les brouillons d'emails (jamais envoyés)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$n = if ($args.Count -gt 0) { $args[0] } else { 3 }
python "$root\agency.py" outreach $n
