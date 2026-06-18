"""🔗 Référenceur — plan SEO de contenu (livrable, non bloquant)."""
from __future__ import annotations

from .. import utils
from ..state import RunState
from .base import AgentResult, voice


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    client = run.client
    craft = client.get("craft") or "service"
    city = (client.get("location", "") or "").split(",")[-1].strip() or "votre ville"
    kws = [f"{craft} {city}", f"meilleur {craft} {city}", f"{craft} pas cher {city}",
           f"{craft} avis {city}", f"{craft} ouvert {city}", f"{craft} près de chez moi"]
    ideas = [f"« Comment choisir son {craft} à {city} »",
             f"« {craft.capitalize()} : nos réalisations récentes »",
             "« Questions fréquentes (devis, délais, garanties) »"]
    run.put("seo_plan", {"keywords": kws, "ideas": ideas})
    md = (f"# Plan SEO — {client.get('name')}\n\n**Mots-clés à viser :**\n"
          + "".join(f"- {k}\n" for k in kws)
          + "\n**Idées de contenu :**\n" + "".join(f"- {i}\n" for i in ideas))
    art = run.dir / "seo-plan.md"
    utils.write_text(art, md)
    voice(run, "referenceur", f"{len(kws)} mots-clés et {len(ideas)} idées de contenu livrés.")
    return AgentResult(ok=True, score=86.0, summary="Plan SEO livré", artifacts=[art])
