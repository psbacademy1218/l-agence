#!/usr/bin/env bash
# Prospection : liste qualifiée de prospects
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python "$ROOT/agency.py" scout
