"""📣 Publicitaire — brouillons d'annonces. IA si dispo, repli déterministe. Jamais diffusé auto."""
from __future__ import annotations

from .. import llm, utils
from ..state import RunState
from .base import AgentResult, voice

_SCHEMA = {"type": "object", "additionalProperties": False, "properties": {
    "headlines": {"type": "array", "items": {"type": "string"}},
    "descriptions": {"type": "array", "items": {"type": "string"}}},
    "required": ["headlines", "descriptions"]}


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    client = run.client
    name = client.get("name", "").split("—")[0].strip()
    craft = client.get("craft") or "service"
    city = (client.get("location", "") or "").split(",")[-1].strip() or "votre ville"
    pos = run.get("positioning", {}) or {}

    heads = descs = None
    if llm.available():
        task = (f"Annonceur : {name}\nMétier : {craft}\nVille : {city}\n"
                + (f"Positionnement : {pos.get('promise')}\n" if pos.get("promise") else "")
                + "\nRédige des annonces Google/Meta : 3 titres (≤ 30 caractères chacun) et "
                  "2 descriptions (≤ 90 caractères), incitatifs mais honnêtes, ancrés local.")
        data = llm.agent_json("publicitaire", task, _SCHEMA)
        if data and data.get("headlines"):
            heads = [h for h in data["headlines"] if h][:4]
            descs = [d for d in data.get("descriptions", []) if d][:3]

    if not heads:  # repli
        heads = [f"{craft.capitalize()} à {city}", f"{name} — devis rapide",
                 "Le travail bien fait, près de chez vous"]
        descs = [f"{name}, {craft} à {city}. Demandez votre devis gratuit en 2 minutes.",
                 "Un interlocuteur unique, des délais tenus. Contactez-nous aujourd'hui."]

    run.put("ads", {"headlines": heads, "descriptions": descs})
    md = (f"# Annonces (brouillons) — {client.get('name')}\n\n"
          "> À relire et valider avant toute diffusion.\n\n**Titres :**\n"
          + "".join(f"- {h}\n" for h in heads)
          + "\n**Descriptions :**\n" + "".join(f"- {d}\n" for d in descs))
    art = run.dir / "ads.md"
    utils.write_text(art, md)
    voice(run, "publicitaire", f"{len(heads)} annonces rédigées"
          + (" (IA)." if llm.available() else " (brouillons)."))
    return AgentResult(ok=True, score=84.0, summary="Annonces rédigées", artifacts=[art])
