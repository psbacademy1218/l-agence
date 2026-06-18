#!/usr/bin/env bash
# Sert le site livré en local : ./serve.sh <slug>
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ $# -lt 1 ]; then echo "Usage : ./serve.sh <slug>"; exit 1; fi
python "$ROOT/agency.py" serve "$1"
