#!/usr/bin/env bash
# Démonstration complète bout-en-bout (détection -> site déployé en local)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python "$ROOT/agency.py" demo
