"""
🔎 Inspector — Contrôle qualité (droit de veto).

Audite le site RÉELLEMENT généré (il relit les fichiers, il ne fait pas
confiance aux agents) sur six axes : structure HTML, accessibilité, contraste,
responsive, performance, et surtout l'ANTI-GÉNÉRIQUE (un rendu qui « sent l'IA »
est rejeté). Chaque problème est étiqueté avec l'agent à qui renvoyer le travail
(`rework`), ce qui pilote la boucle QA du Manager.
"""
from __future__ import annotations

import json
import re

from .. import llm, utils
from ..state import RunState
from .base import AgentResult, voice

# Formules / tournures qui trahissent un site générique ou de remplissage.
BANNED_PHRASES = [
    "bienvenue sur notre site", "lorem ipsum", "votre texte ici", "texte ici",
    "click here", "cliquez ici", "your company", "nom de l'entreprise",
    "solution clé en main", "leader du marché", "placeholder",
]
GENERIC_BLUES = {"#0d6efd", "#007bff", "#2563eb", "#1d4ed8", "#3b82f6"}
GENERIC_FONTS = {"inter", "roboto", "arial", "helvetica", "system-ui"}


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    build = run.get("build", {})
    design = run.get("design", {})
    src = utils.ROOT / build.get("dir", "")
    index = src / "index.html"
    css_path = src / "assets" / "styles.css"

    voice(run, "inspector", "j'inspecte le rendu : structure, a11y, contraste, "
                            "responsive, perfs et… le syndrome du site générique.")

    if not index.exists():
        return AgentResult(ok=False, score=0, summary="Aucun index.html à inspecter.",
                           issues=["Build absent."], rework=["builder"])

    html = utils.read_text(index)
    css = utils.read_text(css_path) if css_path.exists() else ""
    text = _strip_tags(html).lower()

    checks: list[dict] = []  # {name, ok, weight, msg, owner}

    def check(name, ok, weight, msg, owner):
        checks.append({"name": name, "ok": bool(ok), "weight": weight,
                       "msg": msg, "owner": owner})

    # 1) Structure / SEO de base
    check("doctype", html.lower().startswith("<!doctype html>"), 4, "Doctype HTML5", "builder")
    check("lang", 'lang="fr"' in html, 3, "Attribut lang", "builder")
    check("title", "<title>" in html and "</title>" in html, 4, "Balise <title>", "builder")
    check("viewport", 'name="viewport"' in html, 5, "Meta viewport (mobile)", "builder")
    check("description", 'name="description"' in html, 4, "Meta description", "builder")

    # 2) Repères sémantiques
    for tag in ("header", "nav", "main", "footer"):
        check(f"landmark-{tag}", f"<{tag}" in html, 2, f"Repère <{tag}>", "builder")

    # 3) Accessibilité
    check("skip-link", 'class="skip-link"' in html, 6,
          "Lien d'évitement vers le contenu", "builder")
    # toute <img> doit avoir alt
    imgs = re.findall(r"<img\b[^>]*>", html, flags=re.I)
    imgs_ok = all("alt=" in tag for tag in imgs)
    check("img-alt", imgs_ok, 5, "Attribut alt sur les images", "builder")
    # le visuel héro (porteur de sens) doit avoir un nom accessible
    hero = re.search(r'<svg class="hero__svg"[^>]*>', html)
    hero_named = bool(hero and ("aria-label=" in hero.group(0) or 'role="img"' in hero.group(0)))
    check("hero-a11y", hero_named, 6,
          "Nom accessible sur l'illustration principale", "builder")

    # 4) Anti-générique : tournures bannies
    found = [b for b in BANNED_PHRASES if b in text]
    check("no-generic-copy", not found, 12,
          f"Formules génériques : {', '.join(found)}" if found else "Pas de copie générique",
          "copywriter")

    # 5) Anti-générique : direction artistique distincte
    accent = design.get("palette", {}).get("accent", "").lower()
    body_font = design.get("typography", {}).get("body", "").lower()
    distinct = design.get("distinctiveness", 0)
    da_ok = (accent not in GENERIC_BLUES and body_font not in GENERIC_FONTS
             and distinct >= 70)
    check("distinct-da", da_ok, 10,
          "Direction artistique distinctive" if da_ok else
          "DA trop proche d'un template (bleu/police par défaut)", "designer")

    # 6) Contraste WCAG AA sur les paires clés
    pal = design.get("palette", {})
    contrast_fail = []
    if pal:
        pairs = [("texte/fond", pal["ink"], pal["bg"], 4.5),
                 ("secondaire/fond", pal["muted"], pal["bg"], 4.5),
                 ("bouton", pal["on_accent"], pal["accent"], 4.5)]
        for label, fg, bg, need in pairs:
            ratio = utils.contrast_ratio(fg, bg)
            if ratio < need:
                contrast_fail.append(f"{label} {ratio}:1 < {need}")
    check("contrast", not contrast_fail, 8,
          "Contraste AA" if not contrast_fail else "; ".join(contrast_fail), "designer")

    # 7) Responsive + motion
    check("responsive", "@media" in css, 5, "Requêtes média (responsive)", "builder")
    check("reduced-motion", "prefers-reduced-motion" in css, 3,
          "Respect de prefers-reduced-motion", "builder")

    # 8) Liens internes : toute ancre #x doit pointer vers un id existant
    ids = set(re.findall(r'id="([^"]+)"', html))
    anchors = re.findall(r'href="#([^"]*)"', html)
    broken = [a for a in anchors if a == "" or a not in ids]
    check("anchors", not broken, 6,
          "Ancres internes valides" if not broken else f"Ancres cassées : {broken}",
          "builder")

    # 9) Perf proxy : poids total maîtrisé
    weight = sum((src / f).stat().st_size for f in
                 ("index.html", "assets/styles.css", "assets/main.js")
                 if (src / f).exists())
    kb = weight / 1024
    check("poids", kb < 220, 4, f"Poids total {kb:.0f} Ko (< 220 Ko)", "builder")

    # 10) Critique IA anti-générique (une seule passe par mission, droit de veto)
    if llm.available() and not run.get("qa_ai", {}).get("done"):
        cp = run.get("copy", {})
        sample = {
            "accroche": cp.get("hero", {}).get("headline"),
            "sous_titre": cp.get("hero", {}).get("sub"),
            "piliers": [it.get("title") for it in cp.get("savoir_faire", {}).get("items", [])],
            "prestations": [it.get("title") for it in cp.get("realisations", {}).get("items", [])],
            "a_propos": cp.get("atelier", {}).get("paragraphs", []),
        }
        task = ("Voici le contenu d'un site vitrine pour « "
                + f"{run.client.get('name')} » ({run.client.get('craft')}).\n\n"
                + json.dumps(sample, ensure_ascii=False)[:3000]
                + "\n\nCe contenu est-il VRAIMENT sur-mesure et crédible pour CETTE maison, "
                  "ou bien générique / interchangeable / « fait par IA » ? Sois exigeant.")
        schema = {"type": "object", "additionalProperties": False, "properties": {
            "generic": {"type": "boolean"}, "verdict": {"type": "string"},
            "fixes": {"type": "array", "items": {"type": "string"}}},
            "required": ["generic", "verdict", "fixes"]}
        verdict = llm.agent_json("inspector", task, schema)
        if verdict:
            run.put("qa_ai", {"done": True, "generic": bool(verdict.get("generic"))})
            if verdict.get("generic"):
                check("ia-anti-generique", False, 8,
                      "Critique IA : " + (verdict.get("verdict") or "contenu trop générique"),
                      "copywriter")
                if verdict.get("fixes"):
                    run.put("qa_fixes", verdict["fixes"][:4])
            else:
                check("ia-anti-generique", True, 2,
                      "Critique IA : contenu jugé sur-mesure ✓", "copywriter")

    # --- Synthèse -------------------------------------------------------- #
    total_w = sum(c["weight"] for c in checks)
    got_w = sum(c["weight"] for c in checks if c["ok"])
    score = round(100 * got_w / total_w, 1)
    failed = [c for c in checks if not c["ok"]]
    rework = sorted({c["owner"] for c in failed})
    issue_msgs = [f"[{c['owner']}] {c['msg']}" for c in failed]

    # Rapport QA écrit (artefact).
    report = ["# Rapport QA — " + run.client.get("name", ""), "",
              f"**Score : {score}/100** — {len(failed)} problème(s).", ""]
    for c in checks:
        report.append(f"- {'✅' if c['ok'] else '❌'} **{c['name']}** "
                      f"(poids {c['weight']}) — {c['msg']}")
    report_path = run.dir / "qa-report.md"
    utils.write_text(report_path, "\n".join(report))

    if failed:
        voice(run, "inspector",
              f"VETO — score {score}/100. À corriger : "
              + "; ".join(issue_msgs[:4]) + (" …" if len(issue_msgs) > 4 else ""))
        voice(run, "inspector", f"je renvoie vers : {', '.join(rework)}.")
    else:
        voice(run, "inspector",
              f"validé — score {score}/100. Rien de générique, rendu propre. ✅")

    ok = score >= 85 and not any(c["weight"] >= 6 and not c["ok"] for c in checks)
    return AgentResult(ok=ok, score=score,
                       summary=f"QA {score}/100 ({len(failed)} problèmes)",
                       issues=issue_msgs, rework=rework, artifacts=[report_path])
