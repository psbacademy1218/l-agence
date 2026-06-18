"""🧲 Positionneur — promesse + différenciateurs (non bloquant, nourrit le Copywriter)."""
from __future__ import annotations

from .. import utils
from ..state import RunState
from .base import AgentResult, voice


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    client = run.client
    name = client.get("name", "La maison").split("—")[0].split("|")[0].strip()
    craft = client.get("craft") or "votre métier"
    city = (client.get("location", "") or "").split(",")[-1].strip()
    values = client.get("values", [])

    promise = (f"{name} : {craft}{(' à ' + city) if city else ''}, "
               "le travail bien fait et un contact qui répond vraiment.")
    base_diffs = [
        "Un interlocuteur unique, du devis à la livraison",
        "Des réponses claires et des délais tenus",
        "La qualité avant la quantité",
    ]
    diffs = [v.capitalize() for v in values][:3] or base_diffs
    while len(diffs) < 3:
        diffs.append(base_diffs[len(diffs)])

    run.put("positioning", {"promise": promise, "differentiators": diffs[:3]})
    md = (f"# Positionnement — {client.get('name')}\n\n**Promesse :** {promise}\n\n"
          "**Différenciateurs :**\n" + "".join(f"- {d}\n" for d in diffs[:3]))
    art = run.dir / "positioning.md"
    utils.write_text(art, md)
    voice(run, "positionneur", f"angle trouvé : « {promise} »")
    return AgentResult(ok=True, score=88.0, summary="Positionnement défini", artifacts=[art])
