#!/usr/bin/env bash
# Outreach : génère les brouillons d'emails (jamais envoyés)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python "$ROOT/agency.py" outreach "${1:-3}"
