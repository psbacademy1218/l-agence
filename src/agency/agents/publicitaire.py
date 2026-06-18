"""📣 Publicitaire — brouillons d'annonces (livrable, non bloquant, jamais diffusé auto)."""
from __future__ import annotations

from .. import utils
from ..state import RunState
from .base import AgentResult, voice


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    client = run.client
    name = client.get("name", "").split("—")[0].strip()
    craft = client.get("craft") or "service"
    city = (client.get("location", "") or "").split(",")[-1].strip() or "votre ville"
    headlines = [f"{craft.capitalize()} à {city}", f"{name} — devis rapide",
                 "Le travail bien fait, près de chez vous"]
    descriptions = [f"{name}, {craft} à {city}. Demandez votre devis gratuit en 2 minutes.",
                    "Un interlocuteur unique, des délais tenus. Contactez-nous aujourd'hui."]
    run.put("ads", {"headlines": headlines, "descriptions": descriptions})
    md = (f"# Annonces (brouillons) — {client.get('name')}\n\n"
          "> À relire et valider avant toute diffusion.\n\n**Titres :**\n"
          + "".join(f"- {h}\n" for h in headlines)
          + "\n**Descriptions :**\n" + "".join(f"- {d}\n" for d in descriptions))
    art = run.dir / "ads.md"
    utils.write_text(art, md)
    voice(run, "publicitaire", f"{len(headlines)} accroches d'annonces rédigées (brouillons).")
    return AgentResult(ok=True, score=84.0, summary="Annonces rédigées", artifacts=[art])
