# Démonstration complète bout-en-bout (détection -> site déployé en local)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
python "$root\agency.py" demo
