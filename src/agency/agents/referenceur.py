"""🔗 Référenceur — plan SEO de contenu. IA si dispo, repli déterministe."""
from __future__ import annotations

from .. import llm, utils
from ..state import RunState
from .base import AgentResult, voice

_SCHEMA = {"type": "object", "additionalProperties": False, "properties": {
    "keywords": {"type": "array", "items": {"type": "string"}},
    "ideas": {"type": "array", "items": {"type": "string"}}},
    "required": ["keywords", "ideas"]}


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    client = run.client
    craft = client.get("craft") or "service"
    city = (client.get("location", "") or "").split(",")[-1].strip() or "votre ville"

    kws = ideas = None
    if llm.available():
        task = (f"Métier : {craft}\nVille : {city}\n\nPropose un plan SEO local : "
                "8 à 10 mots-clés réalistes (intention locale + variantes longue traîne) et "
                "4 idées d'articles/pages utiles à ce métier.")
        data = llm.agent_json("referenceur", task, _SCHEMA)
        if data and data.get("keywords"):
            kws = [k for k in data["keywords"] if k][:12]
            ideas = [i for i in data.get("ideas", []) if i][:6]

    if not kws:  # repli
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
    voice(run, "referenceur", f"{len(kws)} mots-clés et {len(ideas)} idées livrés"
          + (" (IA)." if llm.available() else "."))
    return AgentResult(ok=True, score=86.0, summary="Plan SEO livré", artifacts=[art])
