"""
🎨 Designer — Direction artistique unique (anti-template).

Le Designer ne pioche pas dans un thème tout fait : il COMPOSE une direction
artistique propre au client à partir de quatre leviers, choisis selon le métier,
les valeurs et une graine déterministe (donc reproductible mais distincte d'un
client à l'autre) :

  1. un ARCHÉTYPE de mise en page (composition, traitement des titres, décor) ;
  2. une PALETTE engagée (jamais le bleu Bootstrap par défaut) ;
  3. un APPARIEMENT TYPOGRAPHIQUE caractériel (jamais Arial/Inter/Roboto) ;
  4. des TOKENS (rayons, échelle d'espacement, mouvement, texture, grille).

Sortie : un jeu de tokens + un parti pris écrit (le Builder s'en sert pour
générer le CSS, le Copywriter pour caler le ton).
"""
from __future__ import annotations

from .. import utils
from ..state import RunState
from .base import AgentResult, voice

# --------------------------------------------------------------------------- #
# Palettes curées (toutes vérifiées pour le contraste texte/fond WCAG AA).
# --------------------------------------------------------------------------- #
PALETTES = {
    "atelier": {  # papier chaud / noyer / terre cuite — artisanat du bois
        "mood": "chaleureuse, matière, papier", "scheme": "light",
        "bg": "#F4EEE2", "surface": "#FBF7EF", "ink": "#2A211A", "muted": "#6B5D4F",
        "line": "#D8CDB8", "accent": "#9A3B1B", "accent2": "#3E5C3A", "on_accent": "#FBF7EF",
    },
    "atelier_nuit": {  # noyer profond — artisanat, version sombre
        "mood": "intime, feu de bois, sombre", "scheme": "dark",
        "bg": "#1B1714", "surface": "#241E19", "ink": "#EDE4D6", "muted": "#B6A693",
        "line": "#3A2E22", "accent": "#D2823F", "accent2": "#8FA98A", "on_accent": "#1B1714",
    },
    "ardoise": {  # ardoise & laiton — services, juridique
        "mood": "sobre, institutionnelle, premium", "scheme": "dark",
        "bg": "#14181C", "surface": "#1C2127", "ink": "#E9E5DC", "muted": "#9FA8B2",
        "line": "#2C333B", "accent": "#C9A227", "accent2": "#6F94A8", "on_accent": "#14181C",
    },
    "serre": {  # botanique — fleuriste, nature
        "mood": "végétale, fraîche, vivante", "scheme": "light",
        "bg": "#F2F1E8", "surface": "#FCFBF6", "ink": "#1F2F28", "muted": "#566B60",
        "line": "#D3D9C6", "accent": "#2F6B4F", "accent2": "#C2562F", "on_accent": "#FCFBF6",
    },
    "oxblood": {  # oxblood & crème — commerce de bouche
        "mood": "gourmande, généreuse, franche", "scheme": "light",
        "bg": "#FAF4EC", "surface": "#FFFFFF", "ink": "#2A1A19", "muted": "#6E5651",
        "line": "#E6D8CB", "accent": "#7C1E22", "accent2": "#3C6E4F", "on_accent": "#FAF4EC",
    },
    "garage": {  # charbon & orange signal — automobile, industriel
        "mood": "robuste, technique, sans détour", "scheme": "dark",
        "bg": "#15171A", "surface": "#1E2126", "ink": "#ECEEF0", "muted": "#9AA1A9",
        "line": "#2A2E34", "accent": "#E4572E", "accent2": "#4FA3A1", "on_accent": "#15171A",
    },
}

# --------------------------------------------------------------------------- #
# Appariements typographiques (display + body), avec import et solides
# fallbacks système pour rester beaux même hors-ligne.
# --------------------------------------------------------------------------- #
TYPE_PAIRS = {
    "fraunces_newsreader": {
        "mood": "éditorial, chaud, lettré",
        "display": "Fraunces", "body": "Newsreader",
        "display_stack": '"Fraunces", "Iowan Old Style", Palatino, Georgia, serif',
        "body_stack": '"Newsreader", Georgia, "Times New Roman", serif',
        "import": "Fraunces:opsz,wght@9..144,400;9..144,600;9..144,900&family=Newsreader:opsz,wght@6..72,400;6..72,500",
    },
    "playfair_source": {
        "mood": "classique, contrasté, élégant",
        "display": "Playfair Display", "body": "Source Serif 4",
        "display_stack": '"Playfair Display", "Hoefler Text", Georgia, serif',
        "body_stack": '"Source Serif 4", Georgia, serif',
        "import": "Playfair+Display:wght@500;700;900&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500",
    },
    "bricolage_plex": {
        "mood": "contemporain, franc, lisible",
        "display": "Bricolage Grotesque", "body": "IBM Plex Sans",
        "display_stack": '"Bricolage Grotesque", "Helvetica Neue", Arial, sans-serif',
        "body_stack": '"IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif',
        "import": "Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=IBM+Plex+Sans:wght@400;500;600",
    },
    "syne_hanken": {
        "mood": "moderne, géométrique, vif",
        "display": "Syne", "body": "Hanken Grotesk",
        "display_stack": '"Syne", "Helvetica Neue", Arial, sans-serif',
        "body_stack": '"Hanken Grotesk", "Segoe UI", system-ui, sans-serif',
        "import": "Syne:wght@600;700;800&family=Hanken+Grotesk:wght@400;500;600",
    },
    "dmserif_mulish": {
        "mood": "raffiné, doux, premium",
        "display": "DM Serif Display", "body": "Mulish",
        "display_stack": '"DM Serif Display", Georgia, "Times New Roman", serif',
        "body_stack": '"Mulish", "Segoe UI", system-ui, sans-serif',
        "import": "DM+Serif+Display:ital@0;1&family=Mulish:wght@400;500;700",
    },
    "archivo_spline": {
        "mood": "industriel, affirmé, technique",
        "display": "Archivo", "body": "Spline Sans",
        "display_stack": '"Archivo", "Arial Narrow", Arial, sans-serif',
        "body_stack": '"Spline Sans", "Segoe UI", system-ui, sans-serif',
        "import": "Archivo:wght@600;700;900&family=Spline+Sans:wght@400;500;600",
    },
}

# --------------------------------------------------------------------------- #
# Archétypes de mise en page : la « grammaire visuelle ».
# --------------------------------------------------------------------------- #
ARCHETYPES = {
    "editorial-craft": {
        "tagline": "Magazine d'atelier : grille asymétrique, gros numéros de section, filets fins, matière papier.",
        "radius": "2px", "space": 1.15, "motion": "posé", "texture": "grain",
        "hero": "split-left", "headings": "numbered-rule", "container": "78rem",
        "border": "1px solid var(--line)",
    },
    "swiss-minimal": {
        "tagline": "Suisse : grille stricte, blancs généreux, filets capillaires, capitales espacées.",
        "radius": "0px", "space": 1.3, "motion": "discret", "texture": "none",
        "hero": "grid-baseline", "headings": "smallcaps-label", "container": "72rem",
        "border": "1px solid var(--line)",
    },
    "organic-soft": {
        "tagline": "Organique : formes douces, ombres tendres, courbes, respirations.",
        "radius": "22px", "space": 1.2, "motion": "fluide", "texture": "blob",
        "hero": "centered-soft", "headings": "underline-curve", "container": "70rem",
        "border": "1px solid var(--line)",
    },
    "retro-print": {
        "tagline": "Imprimé rétro : ombres décalées, bichromie, condensé, esprit affiche.",
        "radius": "0px", "space": 1.05, "motion": "net", "texture": "halftone",
        "hero": "poster", "headings": "offset-shadow", "container": "74rem",
        "border": "2px solid var(--ink)",
    },
    "industrial-utilitarian": {
        "tagline": "Industriel : sombre, accent signal, lignes de grille, étiquettes monospace.",
        "radius": "4px", "space": 1.1, "motion": "sec", "texture": "grid",
        "hero": "data-block", "headings": "mono-index", "container": "80rem",
        "border": "1px solid var(--line)",
    },
}

# Préférences métier -> (archétype, palettes candidates, paires typo candidates)
INDUSTRY_MAP = {
    "artisanat": ("editorial-craft", ["atelier", "atelier_nuit"], ["fraunces_newsreader", "playfair_source"]),
    "commerce de bouche": ("retro-print", ["oxblood", "atelier"], ["playfair_source", "dmserif_mulish"]),
    "commerce de détail": ("organic-soft", ["serre", "oxblood"], ["dmserif_mulish", "syne_hanken"]),
    "services professionnels": ("swiss-minimal", ["ardoise"], ["playfair_source", "bricolage_plex"]),
    "automobile": ("industrial-utilitarian", ["garage"], ["archivo_spline", "bricolage_plex"]),
}
DEFAULT_MAP = ("editorial-craft", ["atelier", "serre", "ardoise"],
               ["fraunces_newsreader", "bricolage_plex", "syne_hanken"])


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    client = run.client
    voice(run, "designer", "je compose une direction artistique rien que pour cette maison…")

    seed = utils.seed_from(client.get("name", "client") + client.get("location", ""))
    industry = (client.get("industry") or "").lower()
    arch_key, palette_opts, type_opts = INDUSTRY_MAP.get(industry, DEFAULT_MAP)

    archetype = ARCHETYPES[arch_key]
    palette_key = utils.pick(palette_opts, seed)
    type_key = utils.pick(type_opts, seed // 7)
    palette = PALETTES[palette_key]
    typo = TYPE_PAIRS[type_key]

    # Score de distinctivité : on s'interdit le générique.
    distinct = 100
    generic_blues = {"#0d6efd", "#007bff", "#2563eb", "#1d4ed8"}
    if palette["accent"].lower() in generic_blues:
        distinct -= 50
    if typo["body"] in ("Arial", "Inter", "Roboto", "Helvetica"):
        distinct -= 40

    design = {
        "art_direction": (
            f"« {palette['mood'].capitalize()} » — archétype {arch_key} avec {typo['display']} "
            f"en titrage et {typo['body']} en lecture. {archetype['tagline']}"),
        "archetype": arch_key,
        "archetype_props": archetype,
        "palette_key": palette_key,
        "palette": palette,
        "type_key": type_key,
        "typography": typo,
        "tokens": {
            "radius": archetype["radius"],
            "space_scale": archetype["space"],
            "container": archetype["container"],
            "motion": archetype["motion"],
            "texture": archetype["texture"],
            "border": archetype["border"],
        },
        "voice": _voice_for(palette, archetype),
        "distinctiveness": distinct,
    }
    run.put("design", design)

    # Trace écrite du parti pris (artefact lisible par l'humain).
    slug = utils.slugify(client.get("name", "client"))
    brief = (f"# Direction artistique — {client.get('name')}\n\n"
             f"**Parti pris :** {design['art_direction']}\n\n"
             f"- Archétype : `{arch_key}` — {archetype['tagline']}\n"
             f"- Palette : `{palette_key}` ({palette['mood']}) — fond {palette['bg']}, "
             f"encre {palette['ink']}, accent {palette['accent']}\n"
             f"- Typographies : **{typo['display']}** (titres) + **{typo['body']}** (texte)\n"
             f"- Tokens : rayon {archetype['radius']}, texture {archetype['texture']}, "
             f"mouvement {archetype['motion']}, conteneur {archetype['container']}\n"
             f"- Distinctivité : {distinct}/100\n")
    art_path = run.dir / "design-brief.md"
    utils.write_text(art_path, brief)

    voice(run, "designer", f"parti pris : {design['art_direction']}")
    voice(run, "designer", f"palette « {palette_key} », typo {typo['display']} × {typo['body']}, "
                           f"distinctivité {distinct}/100.")

    ok = distinct >= 70
    return AgentResult(ok=ok, score=float(distinct),
                       summary=f"DA « {arch_key} / {palette_key} »",
                       issues=[] if ok else ["Direction trop générique."],
                       artifacts=[art_path])


def _voice_for(palette: dict, archetype: dict) -> dict:
    """Indications de ton transmises au Copywriter, alignées sur la DA."""
    return {
        "tone": f"sobre et incarné, à l'image d'une direction {palette['mood']}",
        "person": "nous (la maison), en s'adressant à « vous » (le client)",
        "do": ["phrases concrètes", "détails de métier", "preuves vérifiables",
               "vocabulaire du savoir-faire"],
        "dont": ["superlatifs creux", "jargon marketing", "promesses vagues",
                 "tournures passe-partout"],
    }
