"""💬 Social — calendrier de publications de démarrage (livrable, non bloquant)."""
from __future__ import annotations

from .. import utils
from ..state import RunState
from .base import AgentResult, voice

IDEAS = [
    "Présentation : qui sommes-nous, en 3 phrases",
    "Coulisses : une photo de l'équipe / de l'atelier au travail",
    "Avant / après ou réalisation récente",
    "Conseil utile lié au métier",
    "Avis client mis en avant",
    "Question à la communauté (engagement)",
    "Nouveauté / actualité de la maison",
    "Rappel des horaires et du moyen de contact",
]


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    client = run.client
    lines = [f"- **Jour {i+1}** : {IDEAS[i % len(IDEAS)]}" for i in range(10)]
    run.put("social_plan", {"days": len(lines)})
    md = (f"# Calendrier social (2 semaines) — {client.get('name')}\n\n"
          "Rythme conseillé : 5 posts / semaine.\n\n" + "\n".join(lines) + "\n")
    art = run.dir / "social-plan.md"
    utils.write_text(art, md)
    voice(run, "social", "calendrier de publications sur 2 semaines livré.")
    return AgentResult(ok=True, score=84.0, summary="Calendrier social livré", artifacts=[art])
