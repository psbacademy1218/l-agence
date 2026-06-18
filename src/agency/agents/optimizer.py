"""
📈 Optimizer — SEO technique & mesure.

Sur le site validé par l'Inspector, ajoute : canonical, meta robots, Open Graph
complété, Twitter Card, données structurées JSON-LD (LocalBusiness), un
`sitemap.xml`, un `robots.txt`, et un emplacement de tracking respectueux de la
vie privée (désactivé par défaut, RGPD). N'altère jamais le rendu : il enrichit
l'en-tête au point d'insertion prévu par le Builder.
"""
from __future__ import annotations

import json

from .. import utils
from ..state import RunState
from .base import AgentResult, voice

SITE_URL = "https://www.exemple-client.fr"  # domaine cible (à brancher au lancement)


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    build = run.get("build", {})
    copy = run.get("copy", {})
    client = run.client
    src = utils.ROOT / build.get("dir", "")
    index = src / "index.html"

    voice(run, "optimizer", "j'ajoute le SEO technique : données structurées, "
                            "sitemap, robots, balises sociales…")

    if not index.exists():
        return AgentResult(ok=False, score=0, summary="Pas de site à optimiser.",
                           issues=["index.html absent."])

    html = utils.read_text(index)

    # 1) Données structurées LocalBusiness
    jsonld = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": copy["brand"]["name_full"],
        "description": copy["meta"]["description"],
        "url": SITE_URL,
        "email": copy["contact"]["email"],
        "telephone": copy["contact"]["phone"],
        "address": {"@type": "PostalAddress",
                    "addressLocality": copy["contact"]["address"],
                    "addressCountry": "FR"},
        "areaServed": client.get("location", ""),
        "knowsAbout": copy["meta"]["keywords"],
    }
    head_block = (
        f'<link rel="canonical" href="{SITE_URL}/">\n'
        f'<meta name="robots" content="index, follow">\n'
        f'<meta property="og:url" content="{SITE_URL}/">\n'
        f'<meta property="og:locale" content="fr_FR">\n'
        f'<meta name="twitter:card" content="summary_large_image">\n'
        f'<meta name="twitter:title" content="{copy["meta"]["title"]}">\n'
        f'<meta name="twitter:description" content="{copy["meta"]["description"]}">\n'
        f'<script type="application/ld+json">\n'
        f'{json.dumps(jsonld, ensure_ascii=False, indent=2)}\n</script>\n'
        f'<!-- Mesure d\'audience respectueuse (RGPD) : décommentez pour activer, '
        f'sans cookie ni traçage personnel.\n'
        f'<script defer data-domain="exemple-client.fr" '
        f'src="https://plausible.io/js/script.js"></script> -->\n'
    )

    added = False
    if "<!-- AGENCY:HEAD -->" in html:
        html = html.replace("<!-- AGENCY:HEAD -->", head_block + "<!-- AGENCY:HEAD -->")
        added = True
    utils.write_text(index, html)

    # 2) sitemap.xml (page noindex exclue)
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{SITE_URL}/</loc><changefreq>monthly</changefreq>'
        f'<priority>1.0</priority></url>\n'
        '</urlset>\n')
    utils.write_text(src / "sitemap.xml", sitemap)

    # 3) robots.txt
    robots = ("User-agent: *\n"
              "Allow: /\n"
              "Disallow: /mentions-legales.html\n"
              f"Sitemap: {SITE_URL}/sitemap.xml\n")
    utils.write_text(src / "robots.txt", robots)

    run.put("seo", {
        "jsonld_type": "LocalBusiness",
        "head_injected": added,
        "sitemap": True, "robots": True,
        "tracking": "Plausible (sans cookie), désactivé par défaut",
    })

    checks = [added, (src / "sitemap.xml").exists(), (src / "robots.txt").exists(),
              "application/ld+json" in html]
    score = round(100 * sum(checks) / len(checks), 1)
    voice(run, "optimizer",
          f"SEO en place : JSON-LD {'OK' if added else 'KO'}, sitemap.xml, robots.txt. "
          f"Tracking prêt mais désactivé (RGPD).")
    ok = score >= 75
    return AgentResult(ok=ok, score=score,
                       summary="SEO technique appliqué",
                       issues=[] if ok else ["Injection SEO incomplète."],
                       artifacts=[src / "sitemap.xml", src / "robots.txt", index])
