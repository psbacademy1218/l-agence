# Prospection : liste qualifiée de prospects
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
python "$root\agency.py" scout
