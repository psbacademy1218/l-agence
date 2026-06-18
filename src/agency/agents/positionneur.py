"""🧲 Positionneur — l'angle qui démarque. IA si dispo, repli déterministe."""
from __future__ import annotations

from .. import llm, utils
from ..state import RunState
from .base import AgentResult, voice

_SCHEMA = {"type": "object", "additionalProperties": False, "properties": {
    "promise": {"type": "string"},
    "differentiators": {"type": "array", "items": {"type": "string"}}},
    "required": ["promise", "differentiators"]}


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    client = run.client
    name = client.get("name", "La maison").split("—")[0].split("|")[0].strip()
    craft = client.get("craft") or "votre métier"
    city = (client.get("location", "") or "").split(",")[-1].strip()
    values = client.get("values", [])
    research = run.get("research", {}) or {}

    promise = differentiators = None
    if llm.available():
        task = (f"Entreprise : {name}\nMétier : {craft}\nVille : {city}\n"
                + (f"Valeurs : {', '.join(values)}\n" if values else "")
                + (f"À propos : {client.get('about')}\n" if client.get("about") else "")
                + (f"Cible : {research.get('persona')}\n" if research.get("persona") else "")
                + (f"Douleurs clients : {', '.join(research.get('douleurs', []))}\n" if research.get("douleurs") else "")
                + "\nFormule une PROMESSE de positionnement en une phrase (mémorable, "
                  "spécifique, sans superlatif creux) et 3 différenciateurs concrets "
                  "(ce qui distingue vraiment cette maison de la concurrence locale).")
        data = llm.agent_json("positionneur", task, _SCHEMA)
        if data and data.get("promise"):
            promise = data["promise"]
            differentiators = [d for d in data.get("differentiators", []) if d][:3]

    if not promise:  # repli déterministe
        promise = (f"{name} : {craft}{(' à ' + city) if city else ''}, "
                   "le travail bien fait et un contact qui répond vraiment.")
    base = ["Un interlocuteur unique, du devis à la livraison",
            "Des réponses claires et des délais tenus", "La qualité avant la quantité"]
    if not differentiators:
        differentiators = [v.capitalize() for v in values][:3] or base
    while len(differentiators) < 3:
        differentiators.append(base[len(differentiators)])

    run.put("positioning", {"promise": promise, "differentiators": differentiators[:3]})
    md = (f"# Positionnement — {client.get('name')}\n\n**Promesse :** {promise}\n\n"
          "**Différenciateurs :**\n" + "".join(f"- {d}\n" for d in differentiators[:3]))
    art = run.dir / "positioning.md"
    utils.write_text(art, md)
    voice(run, "positionneur", f"angle : « {promise} »"
          + (" (IA)" if llm.available() else ""))
    return AgentResult(ok=True, score=88.0, summary="Positionnement défini", artifacts=[art])
