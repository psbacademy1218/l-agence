"""🔬 Chercheur — recherche client : cible, attentes, points de douleur (non bloquant)."""
from __future__ import annotations

from ..state import RunState
from .base import AgentResult, voice

SECTOR_PAINS = {
    "commerce de bouche": ["savoir si c'est frais / fait maison", "horaires à jour", "commander pour une occasion"],
    "restauration": ["voir la carte et les prix", "réserver facilement", "ambiance et avis"],
    "beauté & bien-être": ["prendre rendez-vous en ligne", "voir les prestations et tarifs", "être rassuré par des photos"],
    "artisanat": ["preuve du savoir-faire", "obtenir un devis", "délais et sérieux"],
    "automobile": ["prendre rendez-vous", "devis clair", "confiance et proximité"],
    "santé": ["prendre rendez-vous", "infos pratiques claires", "réassurance"],
    "immobilier": ["voir les biens", "être recontacté vite", "confiance"],
}


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    client = run.client
    ind = (client.get("industry") or "").lower()
    craft = client.get("craft") or "professionnel"
    city = (client.get("location", "") or "").split(",")[-1].strip()
    pains = SECTOR_PAINS.get(ind, ["trouver vite l'info utile", "être mis en confiance",
                                   "contacter sans friction"])
    research = {
        "persona": f"Clients locaux{(' à ' + city) if city else ''} cherchant un {craft} de confiance",
        "attentes": ["preuve du sérieux", "facilité de contact", "réassurance (avis, photos, transparence)"],
        "douleurs": pains,
    }
    run.put("research", research)
    md = (f"# Recherche client — {client.get('name')}\n\n"
          f"**Cible :** {research['persona']}\n\n"
          f"**Attentes :**\n" + "".join(f"- {a}\n" for a in research["attentes"]) +
          f"\n**Points de douleur :**\n" + "".join(f"- {d}\n" for d in pains))
    art = run.dir / "research.md"
    from .. import utils
    utils.write_text(art, md)
    voice(run, "chercheur",
          f"cible et attentes cernées ; {len(pains)} points de douleur identifiés.")
    return AgentResult(ok=True, score=88.0, summary="Recherche client", artifacts=[art])
