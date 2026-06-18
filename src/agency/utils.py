"""
Utilitaires transverses de l'agence autonome.

Pur Python (bibliothèque standard uniquement) pour rester portable sur
Windows / macOS / Linux sans aucune dépendance à installer.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

# --------------------------------------------------------------------------- #
# Chemins racine du projet
# --------------------------------------------------------------------------- #
# utils.py -> agency -> src -> <racine projet>
ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "state"
RUNS_DIR = STATE_DIR / "runs"
OUTREACH_DIR = ROOT / "outreach" / "drafts"
DELIVERABLES_DIR = ROOT / "deliverables"
DATA_DIR = ROOT / "data"
AGENTS_DIR = ROOT / ".claude" / "agents"


def ensure_dirs() -> None:
    """Crée les dossiers de travail s'ils n'existent pas encore."""
    for path in (STATE_DIR, RUNS_DIR, OUTREACH_DIR, DELIVERABLES_DIR, DATA_DIR):
        path.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Console : sortie UTF-8 fiable (emojis + accents) y compris sous Windows
# --------------------------------------------------------------------------- #
def _init_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:  # Python 3.7+
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass


_init_console()


def say(message: str = "") -> None:
    """Affiche une ligne en console, en tolérant les terminaux capricieux."""
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        safe = message.encode("ascii", "replace").decode("ascii")
        print(safe, flush=True)


def rule(char: str = "─", width: int = 72) -> None:
    say(char * width)


# --------------------------------------------------------------------------- #
# Horodatage
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


# --------------------------------------------------------------------------- #
# Lecture / écriture fichiers (toujours en UTF-8)
# --------------------------------------------------------------------------- #
def read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def read_json(path: Path) -> dict:
    return json.loads(read_text(path))


def write_json(path: Path, data) -> Path:
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def write_text_atomic(path: Path, content: str) -> Path:
    """Écriture atomique : indispensable quand le dashboard lit pendant qu'on écrit."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)  # atomique sur le même système de fichiers (Windows inclus)
    return path


def write_json_atomic(path: Path, data) -> Path:
    return write_text_atomic(path, json.dumps(data, ensure_ascii=False, indent=2))


def read_json_safe(path: Path, retries: int = 3):
    """Lecture tolérante (réessaie si un écrivain est en plein milieu)."""
    last = None
    for _ in range(retries):
        try:
            return read_json(path)
        except (json.JSONDecodeError, FileNotFoundError) as exc:
            last = exc
            time.sleep(0.02)
    if isinstance(last, FileNotFoundError):
        raise last
    return None


# --------------------------------------------------------------------------- #
# Cadence : ralentit volontairement l'exécution pour rendre les agents
# « visibles en action » dans le dashboard. 0 = vitesse maximale (CLI).
# --------------------------------------------------------------------------- #
PACE = float(os.environ.get("AGENCY_PACE", "0") or 0)


def set_pace(seconds: float) -> None:
    global PACE
    PACE = max(0.0, float(seconds))


def pace(factor: float = 1.0) -> None:
    if PACE > 0:
        time.sleep(PACE * factor)


# --------------------------------------------------------------------------- #
# Slug & graine déterministe
# --------------------------------------------------------------------------- #
def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "client"


def seed_from(text: str) -> int:
    """Graine entière stable dérivée d'une chaîne (reproductible)."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def pick(seq, seed: int):
    """Sélection déterministe dans une séquence à partir d'une graine."""
    return seq[seed % len(seq)]


# --------------------------------------------------------------------------- #
# Couleurs & accessibilité (contraste WCAG)
# --------------------------------------------------------------------------- #
def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _relative_luminance(hex_color: str) -> float:
    def channel(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _hex_to_rgb(hex_color)
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(fg: str, bg: str) -> float:
    """Ratio de contraste WCAG 2.1 entre deux couleurs hex (1 -> 21)."""
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def passes_aa(fg: str, bg: str, large: bool = False) -> bool:
    return contrast_ratio(fg, bg) >= (3.0 if large else 4.5)
