"""
Chargeur de personas.

Les personnalités des agents ne sont PAS codées en dur dans le moteur : elles
vivent dans `.claude/agents/*.md` (un fichier par agent), au format attendu
par les sous-agents Claude Code. Ce module lit leur en-tête (frontmatter) pour
que le moteur Python affiche le bon nom, emoji et la phrase de personnalité,
et pour vérifier que chaque agent du pipeline possède bien sa définition.

Conséquence directe : éditer la personnalité d'un agent = éditer son `.md`,
sans toucher au code. Le même fichier sert de prompt système au sous-agent
Claude correspondant.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import utils


@dataclass
class Persona:
    key: str            # identifiant technique (= nom de fichier sans .md)
    name: str           # nom affiché, ex. "Manager"
    emoji: str          # avatar
    personality: str    # phrase de personnalité
    description: str     # rôle court
    tools: list         # outils déclarés
    reads: list         # entrées attendues
    writes: list        # sorties produites
    system_prompt: str  # corps du fichier = prompt système

    @property
    def label(self) -> str:
        return f"{self.emoji} {self.name}".strip()


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse un frontmatter YAML minimaliste (clé: valeur, listes [a, b])."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    header = text[3:end].strip("\n")
    body = text[end + 4 :].lstrip("\n")

    meta: dict = {}
    for line in header.splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
            meta[key] = [v for v in items if v]
        else:
            meta[key] = value.strip("'\"")
    return meta, body


def load_persona(key: str) -> Persona:
    path = utils.AGENTS_DIR / f"{key}.md"
    if not path.exists():
        raise FileNotFoundError(f"Persona manquante : {path}")
    meta, body = _parse_frontmatter(utils.read_text(path))
    return Persona(
        key=key,
        name=meta.get("display_name", meta.get("name", key.title())),
        emoji=meta.get("emoji", "•"),
        personality=meta.get("personality", ""),
        description=meta.get("description", ""),
        tools=meta.get("tools", []) if isinstance(meta.get("tools"), list) else
              [t.strip() for t in str(meta.get("tools", "")).split(",") if t.strip()],
        reads=meta.get("reads", []) if isinstance(meta.get("reads"), list) else [],
        writes=meta.get("writes", []) if isinstance(meta.get("writes"), list) else [],
        system_prompt=body.strip(),
    )


def all_personas() -> list[Persona]:
    from .state import PIPELINE

    keys = ["manager"] + [name for name, _ in PIPELINE]
    out = []
    for key in keys:
        path = utils.AGENTS_DIR / f"{key}.md"
        if path.exists():
            out.append(load_persona(key))
    return out
