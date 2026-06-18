"""💬 Social — calendrier de publications de démarrage. IA si dispo, repli déterministe."""
from __future__ import annotations

from .. import llm, utils
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
    "Mise en avant d'un produit / service phare",
    "Remerciement / coulisses d'une belle commande",
]

_SCHEMA = {"type": "object", "additionalProperties": False, "properties": {
    "posts": {"type": "array", "items": {"type": "string"}}},
    "required": ["posts"]}


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    client = run.client
    craft = client.get("craft") or "activité"
    city = (client.get("location", "") or "").split(",")[-1].strip()

    posts = None
    if llm.available():
        task = (f"Métier : {craft}\nVille : {city}\n\nPropose 10 idées de publications "
                "(une ligne chacune, concrètes et adaptées à ce métier) pour lancer la "
                "présence sociale, à raison de 5 par semaine sur 2 semaines.")
        data = llm.agent_json("social", task, _SCHEMA)
        if data and data.get("posts"):
            posts = [p for p in data["posts"] if p][:10]

    if not posts:  # repli
        posts = [IDEAS[i % len(IDEAS)] for i in range(10)]

    run.put("social_plan", {"days": len(posts)})
    lines = [f"- **Jour {i+1}** : {p}" for i, p in enumerate(posts)]
    md = (f"# Calendrier social (2 semaines) — {client.get('name')}\n\n"
          "Rythme conseillé : 5 posts / semaine.\n\n" + "\n".join(lines) + "\n")
    art = run.dir / "social-plan.md"
    utils.write_text(art, md)
    voice(run, "social", "calendrier de publications livré"
          + (" (IA)." if llm.available() else "."))
    return AgentResult(ok=True, score=84.0, summary="Calendrier social livré", artifacts=[art])
