"""
🎯 Strategist — Cadrage.

À partir de l'audit et du profil client : définit l'objectif business, la cible,
l'arborescence du site, les KPIs, et CHOISIT DYNAMIQUEMENT le type de site
(HTML statique / Astro-Next / WordPress-CMS) selon les besoins réels du client.
"""
from __future__ import annotations

from .. import llm, utils
from ..state import RunState
from .base import AgentResult, voice


def _choose_site_type(client: dict) -> dict:
    """Décision argumentée du type de site selon le profil client."""
    industry = (client.get("industry") or "").lower()
    needs_ecommerce = bool(client.get("ecommerce"))
    needs_self_edit = bool(client.get("self_edit"))      # le client veut éditer seul
    content_heavy = industry in ("media", "édition", "formation")

    if needs_ecommerce:
        return {"type": "wordpress-woocommerce",
                "why": "Vente en ligne nécessaire : WooCommerce gère catalogue, paiement et stocks."}
    if needs_self_edit or content_heavy:
        return {"type": "wordpress-cms",
                "why": "Mises à jour fréquentes par le client : un CMS lui rend la main sans dev."}
    if content_heavy:
        return {"type": "astro",
                "why": "Beaucoup de contenu éditorial : Astro pour la perf et le SEO."}
    return {"type": "html-statique",
            "why": ("Vitrine sur-mesure, contenu stable, priorité à la vitesse, au coût "
                    "d'hébergement nul et à une direction artistique 100% maîtrisée : "
                    "le HTML statique est le plus pertinent.")}


def _sitemap(client: dict) -> list[dict]:
    metier = client.get("craft", "activité")
    return [
        {"page": "Accueil", "anchor": "accueil",
         "goal": "Capter en 5 secondes : qui, quel savoir-faire, pourquoi cette maison."},
        {"page": "Savoir-faire", "anchor": "savoir-faire",
         "goal": f"Prouver l'expertise de {metier} : méthode, matières, exigence."},
        {"page": "Services", "anchor": "realisations",
         "goal": "Montrer des prestations concrètes (preuve par l'exemple)."},
        {"page": "À propos", "anchor": "atelier",
         "goal": "Incarner : histoire, personnes, lieu, valeurs."},
        {"page": "Contact", "anchor": "contact",
         "goal": "Convertir : demander un devis / prendre rendez-vous (CTA unique)."},
    ]


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    client = run.client
    audit = run.get("audit", {})
    voice(run, "strategist", "je cadre l'objectif, la cible et l'arborescence…")

    site = _choose_site_type(client)
    values = client.get("values", [])
    strategy = {
        "objective": "Transformer le savoir-faire en demandes de devis qualifiées, "
                     "et donner une image à la hauteur du travail réel.",
        "audience": {
            "primary": "Particuliers et prescripteurs locaux cherchant un "
                       f"{client.get('craft', 'professionnel')} de confiance",
            "context": client.get("location", ""),
            "expectations": ["preuve du savoir-faire", "confiance", "facilité de contact"],
        },
        "positioning": f"La maison de référence pour {client.get('craft','le métier')} "
                       f"à {(client.get('location','') or '').split(',')[0]} — "
                       "exigeante, incarnée, sans esbroufe.",
        "site_type": site["type"],
        "site_type_rationale": site["why"],
        "sitemap": _sitemap(client),
        "kpis": [
            "Demandes de devis / mois (objectif : +5 vs 0 aujourd'hui)",
            "Taux de site mobile utilisable : 100 %",
            "Temps de chargement < 1,5 s",
            "Positionnement Google sur « {} {} »".format(
                client.get("craft", "métier"),
                (client.get("location", "") or "").split(",")[0]),
        ],
        "anti_risks": ["Ne JAMAIS ressembler à un template : direction artistique unique.",
                       "Contenu écrit pour ce client précis, pas de texte passe-partout."],
        "values": values,
    }
    # Enrichissement IA de l'objectif / cible / positionnement (repli : déterministe).
    if llm.available():
        research = run.get("strategy_research", {}) or run.get("research", {}) or {}
        task = (f"Métier : {client.get('craft')}\nZone : {client.get('location')}\n"
                + (f"Cible : {research.get('persona')}\n" if research.get("persona") else "")
                + (f"Douleurs : {', '.join(research.get('douleurs', []))}\n" if research.get("douleurs") else "")
                + "\nRédige, pour le site vitrine de cette entreprise : un objectif business "
                  "(une phrase, orienté résultat), la cible principale (une phrase) et un "
                  "positionnement (une phrase, spécifique).")
        schema = {"type": "object", "additionalProperties": False, "properties": {
            "objective": {"type": "string"}, "audience_primary": {"type": "string"},
            "positioning": {"type": "string"}},
            "required": ["objective", "audience_primary", "positioning"]}
        data = llm.agent_json("strategist", task, schema)
        if data:
            if data.get("objective"):
                strategy["objective"] = data["objective"]
            if data.get("audience_primary"):
                strategy["audience"]["primary"] = data["audience_primary"]
            if data.get("positioning"):
                strategy["positioning"] = data["positioning"]

    run.put("strategy", strategy)

    voice(run, "strategist",
          f"type de site retenu : « {site['type']} » — {site['why']}")
    voice(run, "strategist",
          f"arborescence : {' · '.join(p['page'] for p in strategy['sitemap'])}.")

    # Critère d'acceptation : une stratégie complète et exploitable.
    complete = all([strategy["objective"], strategy["sitemap"], strategy["site_type"]])
    score = 92 if complete else 50
    return AgentResult(ok=complete, score=score,
                       summary=f"Cadrage OK — site {site['type']}",
                       issues=[] if complete else ["Stratégie incomplète."])
