"""🔬 Chercheur — recherche client/marché. Recherche web réelle + synthèse IA, repli déterministe."""
from __future__ import annotations

from .. import llm, utils
from ..state import RunState
from .base import AgentResult, voice

SECTOR_PAINS = {
    "commerce de bouche": ["savoir si c'est frais / fait maison", "horaires à jour", "commander pour une occasion"],
    "restauration": ["voir la carte et les prix", "réserver facilement", "ambiance et avis"],
    "beauté & bien-être": ["prendre rendez-vous en ligne", "voir prestations et tarifs", "être rassuré par des photos"],
    "artisanat": ["preuve du savoir-faire", "obtenir un devis", "délais et sérieux"],
    "automobile": ["prendre rendez-vous", "devis clair", "confiance et proximité"],
    "santé": ["prendre rendez-vous", "infos pratiques claires", "réassurance"],
    "immobilier": ["voir les biens", "être recontacté vite", "confiance"],
}

_SCHEMA = {"type": "object", "additionalProperties": False, "properties": {
    "persona": {"type": "string"},
    "attentes": {"type": "array", "items": {"type": "string"}},
    "douleurs": {"type": "array", "items": {"type": "string"}}},
    "required": ["persona", "attentes", "douleurs"]}


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    client = run.client
    ind = (client.get("industry") or "").lower()
    craft = client.get("craft") or "professionnel"
    city = (client.get("location", "") or "").split(",")[-1].strip()

    voice(run, "chercheur", "j'étudie la cible et le marché local…")
    brief = ""
    if llm.available():
        q = (f"J'aide à concevoir le site d'un(e) {craft}" + (f" à {city}" if city else "")
             + ". Recherche : clients types, ce qu'ils cherchent en priorité, "
               "3-4 points de douleur concrets, et 1-2 spécificités locales ou "
               "concurrentielles utiles. Synthèse factuelle.")
        brief = llm.agent_research("chercheur", q)

    research = None
    if llm.available():
        task = (f"Métier : {craft}\nVille : {city}\n"
                + (f"À propos : {client.get('about')}\n" if client.get("about") else "")
                + (f"Recherche web :\n{brief}\n" if brief else "")
                + "\nDéduis la cible (persona en une phrase), 3 attentes clés et "
                  "3-4 points de douleur, propres à ce métier et cette ville.")
        data = llm.agent_json("chercheur", task, _SCHEMA)
        if data and data.get("persona"):
            research = {"persona": data["persona"],
                        "attentes": [a for a in data.get("attentes", []) if a][:4],
                        "douleurs": [d for d in data.get("douleurs", []) if d][:4],
                        "brief": brief}

    if research is None:  # repli déterministe
        pains = SECTOR_PAINS.get(ind, ["trouver vite l'info utile", "être mis en confiance",
                                       "contacter sans friction"])
        research = {"persona": f"Clients locaux{(' à ' + city) if city else ''} cherchant un {craft} de confiance",
                    "attentes": ["preuve du sérieux", "facilité de contact", "réassurance"],
                    "douleurs": pains, "brief": brief}

    run.put("research", research)
    md = (f"# Recherche client — {client.get('name')}\n\n"
          f"**Cible :** {research['persona']}\n\n"
          "**Attentes :**\n" + "".join(f"- {a}\n" for a in research["attentes"])
          + "\n**Points de douleur :**\n" + "".join(f"- {d}\n" for d in research["douleurs"])
          + (f"\n**Recherche web :**\n{brief}\n" if brief else ""))
    art = run.dir / "research.md"
    utils.write_text(art, md)
    via = "IA + web" if (llm.available() and brief) else ("IA" if llm.available() else "déterministe")
    voice(run, "chercheur", f"cible et attentes cernées ({via}).")
    return AgentResult(ok=True, score=88.0, summary=f"Recherche client ({via})", artifacts=[art])
