"""
🖊️ Copywriter — Contenu original sur-mesure + SEO (tous secteurs).

Écrit pour CE client précis, quel que soit son métier. Quand le Scout a audité
un vrai site, le Copywriter réutilise le contenu réellement extrait (titre,
description, intitulés de sections) pour ancrer le texte dans la réalité du
client. Sinon, il compose à partir du métier, de la ville et des valeurs.

Boucle qualité : le premier jet pose une accroche encore générique (que
l'Inspector traque) ; à la reprise, il la remplace par une promesse incarnée.
"""
from __future__ import annotations

import re
from datetime import datetime

from .. import llm, utils
from ..state import RunState
from .base import AgentResult, voice

# Schéma de sortie JSON quand l'IA rédige le contenu.
_COPY_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "meta": {"type": "object", "additionalProperties": False, "properties": {
            "title": {"type": "string"}, "description": {"type": "string"},
            "keywords": {"type": "array", "items": {"type": "string"}}},
            "required": ["title", "description", "keywords"]},
        "hero": {"type": "object", "additionalProperties": False, "properties": {
            "eyebrow": {"type": "string"}, "headline": {"type": "string"},
            "sub": {"type": "string"}}, "required": ["eyebrow", "headline", "sub"]},
        "pillars": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "properties": {"title": {"type": "string"}, "body": {"type": "string"}},
            "required": ["title", "body"]}},
        "services": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "properties": {"title": {"type": "string"}, "meta": {"type": "string"},
                           "body": {"type": "string"}}, "required": ["title", "meta", "body"]}},
        "about": {"type": "array", "items": {"type": "string"}},
        "engagements": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["meta", "hero", "pillars", "services", "about", "engagements"],
}


def _ai_overlay(run: RunState, client: dict, audit: dict, copy: dict) -> bool:
    """Réécrit le contenu avec Claude si la clé est dispo. Retourne True si appliqué."""
    if not llm.available():
        return False
    name = client.get("name", "")
    craft = client.get("craft") or "activité"
    city = (client.get("location", "") or "").split(",")[-1].strip()
    ext = audit.get("extracted", {}) or {}
    research = run.get("research", {}) or {}
    positioning = run.get("positioning", {}) or {}
    ctx = [f"Entreprise : {name}", f"Métier : {craft}"]
    if city:
        ctx.append(f"Ville : {city}")
    if client.get("about"):
        ctx.append(f"Présentation : {client['about']}")
    if client.get("values"):
        ctx.append("Valeurs : " + ", ".join(client["values"]))
    if ext.get("title"):
        ctx.append(f"Titre du site actuel : {ext['title']}")
    if ext.get("description"):
        ctx.append(f"Description actuelle : {ext['description']}")
    if ext.get("headings"):
        ctx.append("Rubriques actuelles : " + ", ".join(ext["headings"]))
    if research.get("douleurs"):
        ctx.append("Attentes/douleurs clients : " + ", ".join(research["douleurs"]))
    if positioning.get("promise"):
        ctx.append(f"Positionnement : {positioning['promise']}")

    system = ("Tu es un directeur de création francophone d'une agence web haut de gamme. "
              "Tu écris un contenu de site vitrine sur-mesure, concret, incarné et crédible "
              "pour CE client précis. Interdits absolus : « bienvenue sur notre site », "
              "lorem ipsum, superlatifs creux, jargon, tournures passe-partout. "
              "Tu réponds uniquement dans le format JSON demandé.")
    user = ("Rédige le contenu d'un site vitrine pour cette entreprise :\n\n"
            + "\n".join(ctx)
            + "\n\nContraintes : français, ton juste et chaleureux mais pro ; "
              "accroche (headline) incarnée et propre à ce client ; titre SEO < 60 caractères ; "
              "meta description < 155 caractères ; 3 à 4 piliers de savoir-faire (title+body) ; "
              "3 prestations concrètes (title+meta+body) ; 2 paragraphes « à propos » ; "
              "3 engagements courts (une phrase chacun).")

    data = llm.generate_json(system, user, _COPY_SCHEMA)
    if not data:
        return False

    m = data.get("meta", {})
    if m.get("title"):
        copy["meta"]["title"] = m["title"][:65]
    if m.get("description"):
        copy["meta"]["description"] = m["description"][:158]
    if m.get("keywords"):
        copy["meta"]["keywords"] = [k for k in m["keywords"] if k][:8]
    h = data.get("hero", {})
    for k in ("eyebrow", "headline", "sub"):
        if h.get(k):
            copy["hero"][k] = h[k]
    if data.get("pillars"):
        copy["savoir_faire"]["items"] = [{"title": p.get("title", ""), "body": p.get("body", "")}
                                         for p in data["pillars"][:4] if p.get("title")]
    if data.get("services"):
        copy["realisations"]["items"] = [{"title": s.get("title", ""), "meta": s.get("meta", ""),
                                          "body": s.get("body", "")}
                                         for s in data["services"][:3] if s.get("title")]
    if data.get("about"):
        copy["atelier"]["paragraphs"] = [p for p in data["about"] if p][:3]
    if data.get("engagements"):
        pos = run.get("positioning", {}) or {}
        pos["differentiators"] = [e for e in data["engagements"] if e][:3]
        run.put("positioning", pos)
    copy["seo"]["h1"] = copy["hero"]["headline"]
    return True

# Valeurs connues -> piliers concrets (artisanat / bouche). Repli générique sinon.
VALUE_PILLARS = {
    "bois massif local": ("Bois massif, sourcé près d'ici",
        "Essences choisies en scierie régionale, séchées lentement. Pas de panneau plaqué."),
    "sur-mesure": ("Dessiné pour votre lieu",
        "Chaque pièce est tracée à la main et ajustée au centimètre de votre intérieur."),
    "patience": ("Le temps du bien fait",
        "Assemblages traditionnels, finitions en plusieurs couches. On ne livre pas avant que ce soit juste."),
    "restauration du patrimoine": ("Redonner vie aux pièces anciennes",
        "Placage, marqueterie, sièges, escaliers : restauration dans les règles de l'art."),
    "circuit court": ("Au plus près, au plus juste",
        "Des fournisseurs choisis dans la région, une traçabilité claire."),
    "fait maison": ("Tout est préparé ici",
        "Recettes maison, gestes du métier, rien d'industriel."),
    "conseil": ("Un vrai conseil, pas un argumentaire",
        "On prend le temps de comprendre votre besoin avant de proposer."),
}


def _pillars(client: dict, extracted: dict, positioning: dict | None = None) -> list[dict]:
    craft = (client.get("craft") or "").lower()
    if "ébéniste" in craft or "menuisier" in craft:
        keys = ["bois massif local", "sur-mesure", "patience", "restauration du patrimoine"]
        return [{"title": VALUE_PILLARS[k][0], "body": VALUE_PILLARS[k][1]} for k in keys]

    pillars = []
    for v in client.get("values", []):
        if v in VALUE_PILLARS:
            pillars.append({"title": VALUE_PILLARS[v][0], "body": VALUE_PILLARS[v][1]})

    # à défaut : on s'appuie sur les vraies sections du site existant
    for h in extracted.get("headings", []):
        if len(pillars) >= 4:
            break
        if 3 < len(h) < 60:
            pillars.append({"title": h, "body":
                f"Un point fort de {client.get('name','la maison')}, mis en avant clairement."})

    # puis sur les différenciateurs trouvés par le Positionneur
    for d in (positioning or {}).get("differentiators", []):
        if len(pillars) >= 3:
            break
        if not any(p["title"].lower() == d.lower() for p in pillars):
            pillars.append({"title": d,
                            "body": "Un engagement concret, tenu sur chaque projet."})

    metier = client.get("craft") or "notre métier"
    generic = [
        ("Un savoir-faire qui se voit", f"Ce que nous faisons en {metier}, fait avec soin et régularité."),
        ("Proches de nos clients", "Un interlocuteur unique, des réponses claires, des délais tenus."),
        ("La qualité d'abord", "On préfère bien faire que faire vite. Et ça se ressent sur le résultat."),
    ]
    i = 0
    while len(pillars) < 3:
        pillars.append({"title": generic[i][0], "body": generic[i][1]})
        i += 1
    return pillars[:4]


def _services(client: dict, extracted: dict) -> list[dict]:
    craft = (client.get("craft") or "").lower()
    if "ébéniste" in craft or "menuisier" in craft:
        return [
            {"title": "Bibliothèque toute hauteur, noyer massif", "meta": client.get("location", ""),
             "body": "Montants chevillés, échelle coulissante en laiton, pensée autour d'une collection."},
            {"title": "Restauration de meuble ancien", "meta": "Pièce de famille",
             "body": "Placage repris feuille à feuille, serrures d'origine remontées, finition au tampon."},
            {"title": "Escalier sur-mesure en chêne", "meta": "Maison de ville",
             "body": "Limon cintré, marches en chêne huilé, garde-corps fin. Calculé pour ne pas grincer."},
        ]
    # secteurs variés : on tire de vraies rubriques quand on en a
    heads = [h for h in extracted.get("headings", []) if 3 < len(h) < 60][:3]
    if len(heads) >= 3:
        return [{"title": h, "meta": client.get("location", ""),
                 "body": "Une prestation de la maison, présentée clairement et donnant envie de pousser la porte."}
                for h in heads]
    metier = client.get("craft") or "nos prestations"
    return [
        {"title": f"{metier.capitalize()}", "meta": client.get("location", ""),
         "body": "Notre cœur de métier, exécuté avec exigence."},
        {"title": "Sur rendez-vous", "meta": "Simple et rapide",
         "body": "On convient d'un créneau qui vous arrange, sans attente inutile."},
        {"title": "Devis clair", "meta": "Sans surprise",
         "body": "Un prix annoncé, expliqué, tenu. Pas de mauvaise surprise."},
    ]


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    client = run.client
    strategy = run.get("strategy", {})
    audit = run.get("audit", {})
    extracted = audit.get("extracted", {}) or {}
    prev = run.get("copy", {})
    rev = int(prev.get("_rev", 0))

    voice(run, "copywriter",
          "j'écris un contenu propre à cette maison…" if rev == 0
          else "je reprends l'accroche suite au veto de l'Inspector…")

    name_full = client.get("name", "La Maison")
    name_short = name_full.split("—")[0].split("|")[0].strip()
    city = (client.get("location", "") or "").split(",")[-1].strip() or \
           (client.get("location", "") or "")
    craft = client.get("craft", "") or "votre activité"
    metier = craft if craft and craft != "votre activité" else "artisan"
    founded = client.get("founded")
    years = (datetime.now().year - founded) if founded else None
    monogram = "".join(w[0] for w in re.findall(r"[A-Za-zÀ-ÿ]+", name_short)[:2]).upper() or "AG"

    # --- accroche : générique au 1er jet, incarnée après reprise QA ---
    if rev == 0:
        headline = "Bienvenue sur notre site"
    elif "ébéniste" in craft.lower() or "menuisier" in craft.lower():
        headline = "Le bois, façonné pour durer trois générations."
    elif craft and craft != "votre activité":
        headline = f"{craft.capitalize()} à {city}, avec l'exigence du travail bien fait." \
            if city else f"{craft.capitalize()}, avec l'exigence du travail bien fait."
    else:
        headline = f"{name_short}, le bon réflexe{(' à ' + city) if city else ''}."

    eyebrow = " · ".join(filter(None, [
        (craft.capitalize() if craft != "votre activité" else None), city,
        (f"depuis {founded}" if founded else None)]))

    # sous-titre : description réelle si disponible, sinon composée
    real_desc = (extracted.get("description") or "").strip()
    if real_desc and len(real_desc) > 60 and rev > 0:
        sub = real_desc
    else:
        sub = (f"{name_short}"
               + (f", {craft}" if craft != "votre activité" else "")
               + (f" à {city}" if city else "")
               + ". On fait les choses avec soin, on répond vite, et on tient ce qu'on promet. "
                 "Découvrez ce que nous pouvons faire pour vous.")

    pillars = _pillars(client, extracted, run.get("positioning", {}))
    services = _services(client, extracted)
    about_text = (client.get("about") or real_desc
                  or f"{name_short} accompagne ses clients{(' à ' + city) if city else ''} "
                     f"avec sérieux et proximité.")

    copy = {
        "_rev": rev + 1,
        "meta": {
            "title": (f"{name_short} — {craft}" if craft != "votre activité" else f"{name_short}")
                     + (f" à {city}" if city else ""),
            "description": (real_desc[:158] if real_desc
                            else (f"{name_short}" + (f", {craft} à {city}" if city else "")
                                  + ". Contactez-nous, demandez un devis.")[:158]),
            "keywords": list(filter(None, [craft if craft != "votre activité" else None,
                             (f"{craft} {city}" if city and craft != 'votre activité' else None),
                             city, name_short])),
        },
        "brand": {"name_full": name_full, "name_short": name_short,
                  "monogram": monogram, "tagline": eyebrow or name_short},
        "nav": [{"label": p["page"], "anchor": p["anchor"]} for p in strategy.get("sitemap", [])],
        "hero": {
            "eyebrow": eyebrow or name_short,
            "headline": headline,
            "sub": sub,
            "cta": {"label": "Demander un devis", "anchor": "#contact"},
            "secondary": {"label": "Voir nos services", "anchor": "#realisations"},
        },
        "savoir_faire": {
            "label": "Savoir-faire",
            "title": "Ce que nous savons faire",
            "intro": "Notre métier, mené avec la même exigence du début à la fin.",
            "items": pillars,
        },
        "realisations": {
            "label": "Nos services",
            "title": "Nos prestations",
            "intro": "Un aperçu concret de ce que nous proposons.",
            "items": services,
        },
        "atelier": {
            "label": "À propos",
            "title": f"À propos de {name_short}",
            "paragraphs": list(filter(None, [
                about_text,
                (f"Cela fait {years} ans que nous exerçons" if years else "Nous exerçons")
                + (f" à {city}" if city else "") + ", avec la même idée simple : "
                  "faire bien, être clairs, et mériter votre confiance.",
            ])),
            "facts": list(filter(None, [
                {"k": "Depuis", "v": str(founded)} if founded else None,
                {"k": "Où", "v": city} if city else None,
                {"k": "Activité", "v": craft if craft != "votre activité" else "—"},
            ])),
        },
        "contact": {
            "label": "Contact",
            "title": "Parlons de votre projet",
            "intro": "Une question, une demande, un devis ? Écrivez-nous, on répond vite.",
            "email": client.get("contact", {}).get("email", "") or "contact@exemple.fr",
            "phone": "—",
            "address": client.get("location", "") or "",
            "hours": "Sur rendez-vous",
            "cta": {"label": "Nous écrire", "anchor": "mailto:" +
                    (client.get("contact", {}).get("email", "") or "contact@exemple.fr")},
        },
        "footer": {"blurb": f"{name_short}" + (f" — {craft} à {city}" if city and craft != 'votre activité' else ""),
                   "legal": "Mentions légales"},
        "seo": {"h1": headline if rev > 0 else name_short},
    }

    # Si la clé Claude est présente : on réécrit le contenu sur-mesure par IA.
    ai_used = _ai_overlay(run, client, audit, copy)
    if ai_used:
        voice(run, "copywriter", "contenu rédigé sur-mesure par Claude (IA).")

    run.put("copy", copy)

    issues_found = []
    flat = " ".join([copy["hero"]["headline"], copy["hero"]["sub"],
                     copy["savoir_faire"]["intro"], copy["atelier"]["paragraphs"][0]])
    for bad in ("lorem", "ipsum", "placeholder", "votre texte ici", "todo"):
        if bad in flat.lower():
            issues_found.append(f"Texte de remplissage détecté : {bad}")
    if len(copy["hero"]["sub"]) < 40:
        issues_found.append("Sous-titre trop court.")
    if not copy["savoir_faire"]["items"]:
        issues_found.append("Aucun pilier de savoir-faire.")

    score = 90 - 20 * len(issues_found)
    voice(run, "copywriter",
          f"contenu rédigé ({len(pillars)} piliers, {len(services)} prestations). "
          f"Accroche : « {copy['hero']['headline']} »")
    return AgentResult(ok=not issues_found, score=float(max(0, score)),
                       summary=f"Contenu rédigé (rev {copy['_rev']})", issues=issues_found)
