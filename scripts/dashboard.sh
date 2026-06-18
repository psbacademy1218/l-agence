#!/usr/bin/env bash
# Lance l'interface "Mission Control" (tableau de bord web local)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python "$ROOT/agency.py" dashboard "${1:-7000}"
