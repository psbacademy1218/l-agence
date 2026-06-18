"""🧐 Relecteur — relecture du contenu (nettoie + note ; non bloquant)."""
from __future__ import annotations

import re

from ..state import RunState
from .base import AgentResult, voice


def _clean(s: str) -> str:
    return re.sub(r"\s{2,}", " ", s).strip() if isinstance(s, str) else s


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    copy = run.get("copy", {})
    notes = []

    # nettoyage réel des espaces superflus
    if copy.get("hero"):
        copy["hero"]["sub"] = _clean(copy["hero"].get("sub", ""))
        copy["hero"]["headline"] = _clean(copy["hero"].get("headline", ""))
    for sec in ("savoir_faire", "realisations"):
        for it in copy.get(sec, {}).get("items", []):
            it["body"] = _clean(it.get("body", ""))
    run.put("copy", copy)

    head = (copy.get("hero", {}).get("headline", "") or "").lower()
    if head.startswith("bienvenue"):
        notes.append("Accroche générique")
    if len(copy.get("hero", {}).get("sub", "")) < 50:
        notes.append("Sous-titre un peu court")

    score = 93 - 8 * len(notes)
    voice(run, "relecteur",
          "contenu relu et nettoyé — rien à signaler." if not notes
          else f"relu ; remarques : {', '.join(notes)}.")
    return AgentResult(ok=True, score=float(score), summary="Relecture effectuée", issues=notes)
