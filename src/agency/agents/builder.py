"""
💻 Builder — Génération du site.

Transforme les tokens de direction artistique (Designer) et le contenu
(Copywriter) en un site réel : HTML sémantique, CSS piloté par variables +
bloc « saveur » propre à l'archétype, micro-JS progressif, et illustrations
SVG dessinées sur-mesure (motif d'assemblage à queue d'aronde + veinage).

Type de site : ici « html-statique » (décidé par le Strategist). Le Builder est
écrit pour pouvoir aiguiller vers d'autres générateurs selon `site_type`.

Boucle qualité : au premier jet (`_rev == 0`), le Builder laisse volontairement
deux défauts réalistes — pas de lien d'évitement, illustration sans nom
accessible — que l'Inspector détecte. À la reprise, le rendu est complet.
"""
from __future__ import annotations

from .. import utils
from ..state import RunState
from .base import AgentResult, voice


# --------------------------------------------------------------------------- #
# Illustrations SVG (dessinées, thématisées par les couleurs de la palette)
# --------------------------------------------------------------------------- #
def _svg_monogram(text: str, ink: str, accent: str) -> str:
    return (
        f'<svg class="monogram" viewBox="0 0 64 64" aria-hidden="true" focusable="false">'
        f'<rect x="2" y="2" width="60" height="60" rx="4" fill="none" '
        f'stroke="{accent}" stroke-width="2"/>'
        f'<path d="M14 46 L24 18 L32 38 L40 18 L50 46" fill="none" stroke="{ink}" '
        f'stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<text x="32" y="59" text-anchor="middle" font-size="9" fill="{accent}" '
        f'font-family="var(--font-display)">{text}</text></svg>')


def _svg_joint(ink: str, accent: str, line: str) -> str:
    """Petit motif d'assemblage à queue d'aronde — ornement de section."""
    return (
        f'<svg class="ornament" viewBox="0 0 80 28" aria-hidden="true" focusable="false">'
        f'<path d="M0 27 H80" stroke="{line}" stroke-width="1"/>'
        f'<path d="M6 26 L12 4 L24 4 L30 26 Z" fill="none" stroke="{accent}" stroke-width="1.6"/>'
        f'<path d="M30 26 L36 4 L48 4 L54 26 Z" fill="none" stroke="{ink}" stroke-width="1.6"/>'
        f'<path d="M54 26 L60 4 L72 4 L78 26 Z" fill="none" stroke="{accent}" stroke-width="1.6"/>'
        f'</svg>')


def _svg_hero(palette: dict, labelled: bool) -> str:
    """Panneau héro : veinage du bois + assemblage, signature visuelle."""
    ink, accent, line, surface, muted = (
        palette["ink"], palette["accent"], palette["line"],
        palette["surface"], palette["muted"])
    rings = "".join(
        f'<path d="M40 {70 + i*46} Q240 {30 + i*46} 440 {70 + i*46}" fill="none" '
        f'stroke="{line}" stroke-width="{2.2 - i*0.05:.2f}"/>'
        for i in range(9))
    a11y = (' role="img" aria-label="Veinage du bois et assemblage à queue '
            'd\'aronde, la signature de l\'atelier."') if labelled else ""
    return (
        f'<svg class="hero__svg" viewBox="0 0 480 560" preserveAspectRatio="xMidYMid slice"{a11y}>'
        f'<rect width="480" height="560" fill="{surface}"/>'
        f'<rect x="0.5" y="0.5" width="479" height="559" fill="none" stroke="{line}"/>'
        f'{rings}'
        # assemblage à queue d'aronde, en bas, à l'accent
        f'<g transform="translate(150 430)">'
        f'<path d="M0 100 L24 20 L66 20 L90 100 Z" fill="none" stroke="{accent}" stroke-width="3"/>'
        f'<path d="M90 100 L114 20 L156 20 L180 100 Z" fill="none" stroke="{ink}" stroke-width="3"/>'
        f'</g>'
        f'<circle cx="392" cy="92" r="34" fill="none" stroke="{accent}" stroke-width="3"/>'
        f'<text x="392" y="99" text-anchor="middle" font-size="22" fill="{accent}" '
        f'font-family="var(--font-display)">✶</text>'
        f'</svg>')


def _svg_tile(palette: dict, n: int) -> str:
    """Vignette abstraite pour une réalisation (variée selon l'index)."""
    ink, accent, line, surface = (palette["ink"], palette["accent"],
                                  palette["line"], palette["surface"])
    motifs = [
        f'<g stroke="{ink}" stroke-width="2" fill="none">'
        f'<rect x="14" y="14" width="92" height="72"/>'
        f'<line x1="14" y1="34" x2="106" y2="34"/><line x1="14" y1="54" x2="106" y2="54"/>'
        f'<line x1="14" y1="74" x2="106" y2="74"/></g>',
        f'<g stroke="{accent}" stroke-width="2" fill="none">'
        f'<path d="M20 86 Q60 14 100 86"/><path d="M30 86 Q60 30 90 86"/>'
        f'<path d="M40 86 Q60 46 80 86"/></g>',
        f'<g stroke="{ink}" stroke-width="2" fill="none">'
        f'<path d="M22 22 L22 86"/><path d="M22 22 Q70 22 70 54 Q70 86 22 86"/>'
        f'<path d="M86 22 L86 86"/></g>',
    ]
    return (f'<svg class="real__svg" viewBox="0 0 120 100" aria-hidden="true" focusable="false">'
            f'<rect width="120" height="100" fill="{surface}" stroke="{line}"/>'
            f'{motifs[n % len(motifs)]}</svg>')


# --------------------------------------------------------------------------- #
# Génération du CSS (variables dynamiques + base + saveur d'archétype)
# --------------------------------------------------------------------------- #
def _root_vars(design: dict) -> str:
    p, typo, t = design["palette"], design["typography"], design["tokens"]
    lines = [
        f"--bg: {p['bg']};", f"--surface: {p['surface']};", f"--ink: {p['ink']};",
        f"--muted: {p['muted']};", f"--line: {p['line']};", f"--accent: {p['accent']};",
        f"--accent2: {p['accent2']};", f"--on-accent: {p['on_accent']};",
        f"--font-display: {typo['display_stack']};",
        f"--font-body: {typo['body_stack']};",
        f"--radius: {t['radius']};", f"--container: {t['container']};",
        "--step--1: clamp(0.82rem, 0.78rem + 0.2vw, 0.9rem);",
        "--step-0: clamp(1rem, 0.95rem + 0.25vw, 1.13rem);",
        "--step-1: clamp(1.2rem, 1.1rem + 0.5vw, 1.45rem);",
        "--step-2: clamp(1.5rem, 1.3rem + 1vw, 2rem);",
        "--step-3: clamp(2rem, 1.6rem + 2vw, 3rem);",
        "--step-4: clamp(2.6rem, 1.9rem + 3.4vw, 4.6rem);",
        "--space: 1.5rem;",
    ]
    return ":root{\n  " + "\n  ".join(lines) + "\n}"


BASE_CSS = r"""
*,*::before,*::after{box-sizing:border-box}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}
  *,*::before,*::after{animation-duration:.001ms!important;transition-duration:.001ms!important}}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:var(--font-body);font-size:var(--step-0);line-height:1.65;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
h1,h2,h3{font-family:var(--font-display);line-height:1.05;font-weight:600;
  margin:0 0 .4em;letter-spacing:-0.01em}
p{margin:0 0 1em;max-width:64ch}
a{color:inherit}
img,svg{max-width:100%;height:auto;display:block}
.container{width:min(100% - 2.4rem, var(--container));margin-inline:auto}

/* accessibilité : lien d'évitement + focus visibles */
.skip-link{position:absolute;left:.6rem;top:-3rem;z-index:50;background:var(--accent);
  color:var(--on-accent);padding:.55rem .9rem;border-radius:var(--radius);
  transition:top .15s ease}
.skip-link:focus{top:.6rem}
:focus-visible{outline:2.5px solid var(--accent);outline-offset:3px;border-radius:2px}

/* en-tête */
.site-header{position:sticky;top:0;z-index:40;backdrop-filter:saturate(1.1) blur(6px);
  border-bottom:1px solid transparent;transition:border-color .25s,background .25s}
.site-header.is-stuck{background:color-mix(in srgb,var(--bg) 88%,transparent);
  border-bottom-color:var(--line)}
.nav{display:flex;align-items:center;justify-content:space-between;gap:1rem;
  padding:.9rem 0}
.brand{display:flex;align-items:center;gap:.6rem;text-decoration:none;font-weight:600}
.brand .monogram{width:36px;height:36px;flex:none}
.brand b{font-family:var(--font-display);font-size:var(--step-1);letter-spacing:-.01em}
.nav__links{display:flex;gap:1.4rem;list-style:none;margin:0;padding:0}
.nav__links a{text-decoration:none;color:var(--muted);font-size:var(--step--1);
  letter-spacing:.02em;padding:.25rem 0;border-bottom:1.5px solid transparent;transition:.18s}
.nav__links a:hover{color:var(--ink);border-bottom-color:var(--accent)}
.nav__toggle{display:none;background:none;border:1px solid var(--line);border-radius:var(--radius);
  color:var(--ink);font-size:1.2rem;width:42px;height:42px;cursor:pointer}

/* boutons */
.btn{display:inline-flex;align-items:center;gap:.5rem;font-family:var(--font-body);
  font-weight:600;font-size:var(--step-0);padding:.8rem 1.3rem;border-radius:var(--radius);
  text-decoration:none;cursor:pointer;border:1.5px solid transparent;transition:transform .15s,opacity .2s}
.btn--primary{background:var(--accent);color:var(--on-accent)}
.btn--primary:hover{transform:translateY(-2px)}
.btn--ghost{border-color:var(--ink);color:var(--ink)}
.btn--ghost:hover{background:var(--ink);color:var(--bg)}

/* en-têtes de section */
.section{padding:clamp(3.5rem,7vw,7rem) 0}
.section__head{display:flex;align-items:baseline;gap:1rem;margin-bottom:2.4rem}
.section__num{font-family:var(--font-display);font-size:var(--step-3);color:var(--accent);
  opacity:.35;line-height:1}
.section__label{font-size:var(--step--1);text-transform:uppercase;letter-spacing:.22em;
  color:var(--muted)}
.section__rule{flex:1;height:1px;background:var(--line)}
.section h2{font-size:var(--step-3)}
.lead{font-size:var(--step-1);color:var(--muted);max-width:54ch}

/* héro */
.hero{padding:clamp(3rem,7vw,6.5rem) 0 clamp(2.5rem,5vw,4rem)}
.hero__grid{display:grid;grid-template-columns:1.05fr .95fr;gap:clamp(1.5rem,4vw,3.5rem);
  align-items:center}
.eyebrow{font-size:var(--step--1);text-transform:uppercase;letter-spacing:.2em;
  color:var(--accent);margin:0 0 1rem}
.hero h1{font-size:var(--step-4);margin-bottom:.5em}
.hero__sub{font-size:var(--step-1);color:var(--muted);max-width:46ch}
.hero__cta{display:flex;flex-wrap:wrap;gap:.9rem;margin-top:1.8rem}
.hero__art{margin:0}
.hero__svg{width:100%;border-radius:var(--radius)}

/* piliers savoir-faire */
.pillars{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1.4rem}
.pillar{padding:1.6rem 1.4rem;background:var(--surface);border:1px solid var(--line);
  border-top:3px solid var(--accent);border-radius:var(--radius)}
.pillar h3{font-size:var(--step-1)}
.pillar p{color:var(--muted);margin:0;font-size:var(--step-0)}

/* engagements */
.engagements{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1.2rem}
.engage{display:flex;gap:.8rem;align-items:flex-start;padding:1.3rem 1.2rem;background:var(--surface);
  border:1px solid var(--line);border-radius:var(--radius)}
.engage__ic{flex:none;width:30px;height:30px;border-radius:50%;display:grid;place-items:center;
  background:var(--accent);color:var(--on-accent);font-weight:700;font-size:.95rem}
.engage h3{font-size:var(--step-1);margin:.15em 0 0}

/* réalisations */
.reals{display:flex;flex-direction:column}
.real{display:grid;grid-template-columns:auto 1fr auto;gap:1.4rem;align-items:center;
  padding:1.5rem 0;border-top:1px solid var(--line)}
.real:last-child{border-bottom:1px solid var(--line)}
.real__idx{font-family:var(--font-display);color:var(--accent);font-size:var(--step-2)}
.real h3{font-size:var(--step-2);margin:0 0 .2em}
.real__meta{color:var(--muted);font-size:var(--step--1);text-transform:uppercase;
  letter-spacing:.12em}
.real p{color:var(--muted);margin:.5em 0 0}
.real__svg{width:120px;border-radius:var(--radius)}

/* atelier */
.atelier__grid{display:grid;grid-template-columns:1.3fr .7fr;gap:clamp(1.5rem,4vw,3rem);
  align-items:start}
.facts{list-style:none;margin:1.5rem 0 0;padding:1.4rem;border:1px solid var(--line);
  background:var(--surface);border-radius:var(--radius)}
.facts div{display:flex;justify-content:space-between;gap:1rem;padding:.5rem 0;
  border-bottom:1px dashed var(--line)}
.facts div:last-child{border-bottom:0}
.facts dt{color:var(--muted)}.facts dd{margin:0;font-weight:600;font-family:var(--font-display)}

/* contact */
.contact__grid{display:grid;grid-template-columns:1fr 1fr;gap:clamp(1.5rem,4vw,3rem);
  align-items:center}
.contact__list{list-style:none;margin:1.4rem 0 0;padding:0}
.contact__list li{padding:.45rem 0;color:var(--muted)}
.contact__list b{color:var(--ink);font-family:var(--font-display);display:block}
.contact__cta{padding:2rem;background:var(--surface);border:1px solid var(--line);
  border-radius:var(--radius)}

/* pied */
.site-footer{border-top:1px solid var(--line);padding:2.5rem 0;color:var(--muted);
  font-size:var(--step--1)}
.site-footer .nav{padding:0}
.site-footer a{color:var(--muted)}

/* grain papier (texture d'ambiance) */
.grain::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:1;opacity:.05;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}

/* révélation au chargement (progressive, désactivée si reduced-motion) */
.js [data-reveal]{opacity:0;transform:translateY(14px)}
.js [data-reveal].in{opacity:1;transform:none;transition:opacity .6s ease,transform .6s ease}
@media (prefers-reduced-motion:reduce){.js [data-reveal]{opacity:1;transform:none}}

/* RESPONSIVE */
@media (max-width:880px){
  .hero__grid,.atelier__grid,.contact__grid{grid-template-columns:1fr}
  .hero__art{order:-1}
  .nav__links{position:fixed;inset:64px 0 auto 0;background:var(--surface);
    flex-direction:column;gap:0;padding:1rem 1.2rem;border-bottom:1px solid var(--line);
    transform:translateY(-130%);transition:transform .25s ease}
  .nav__links.open{transform:none}
  .nav__links a{padding:.7rem 0;border-bottom:1px solid var(--line)}
  .nav__toggle{display:inline-flex;align-items:center;justify-content:center}
}
@media (max-width:560px){
  .real{grid-template-columns:auto 1fr}.real__svg{display:none}
  .section__num{font-size:var(--step-2)}
}
"""

FLAVOR_CSS = {
    "editorial-craft": r"""
.hero h1{text-wrap:balance}
.section__label{position:relative;padding-left:1.2rem}
.section__label::before{content:"";position:absolute;left:0;top:50%;width:.7rem;height:1px;
  background:var(--accent)}
.pillar{position:relative}
.ornament{height:22px;width:auto;margin:0 0 1.2rem}
.hero__svg{box-shadow:14px 14px 0 -2px var(--line)}
""",
    "swiss-minimal": r"""
.section__num{display:none}
.section__head{border-top:2px solid var(--ink);padding-top:.8rem;align-items:flex-start}
.section__label{letter-spacing:.3em}
.pillar{border-top-width:1px;border-radius:0}
.hero__svg{box-shadow:none;border:1px solid var(--ink)}
""",
    "organic-soft": r"""
.pillar,.facts,.contact__cta{border-radius:22px;box-shadow:0 18px 40px -28px var(--ink)}
.hero__svg{border-radius:28px}
.section__num{opacity:.5}
.btn{border-radius:999px}
""",
    "retro-print": r"""
.btn--primary{box-shadow:5px 5px 0 var(--ink)}
.pillar{border:2px solid var(--ink);box-shadow:6px 6px 0 var(--line);border-radius:0}
.hero h1{text-shadow:3px 3px 0 var(--accent)}
.section__num{-webkit-text-stroke:1px var(--accent);color:transparent;opacity:1}
""",
    "industrial-utilitarian": r"""
.section__label{font-family:var(--font-body);background:var(--surface);
  border:1px solid var(--line);padding:.2rem .6rem}
.pillar{border-radius:4px;border-top-color:var(--accent2)}
.hero__svg{outline:1px solid var(--line);outline-offset:8px}
.btn--primary{text-transform:uppercase;letter-spacing:.08em}
""",
}


def _render_css(design: dict) -> str:
    arch = design["archetype"]
    return (_root_vars(design) + "\n" + BASE_CSS
            + "\n/* --- saveur " + arch + " --- */\n"
            + FLAVOR_CSS.get(arch, ""))


# --------------------------------------------------------------------------- #
# Génération du HTML
# --------------------------------------------------------------------------- #
def _render_html(design: dict, copy: dict, rev: int, positioning: dict | None = None) -> str:
    p = design["palette"]
    typo = design["typography"]
    grain = " grain" if design["tokens"]["texture"] == "grain" else ""
    skip = ('<a class="skip-link" href="#contenu">Aller au contenu</a>\n'
            if rev > 0 else "")  # défaut volontaire au 1er jet
    font_href = ("https://fonts.googleapis.com/css2?family="
                 + typo["import"] + "&display=swap")

    nav_links = "".join(
        f'<li><a href="#{n["anchor"]}">{n["label"]}</a></li>'
        for n in copy["nav"])

    pillars = "".join(
        f'<article class="pillar" data-reveal><h3>{it["title"]}</h3>'
        f'<p>{it["body"]}</p></article>'
        for it in copy["savoir_faire"]["items"])

    reals = "".join(
        f'<article class="real" data-reveal>'
        f'<div class="real__idx">{i+1:02d}</div>'
        f'<div><p class="real__meta">{it["meta"]}</p><h3>{it["title"]}</h3>'
        f'<p>{it["body"]}</p></div>'
        f'<figure class="real__fig">{_svg_tile(p, i)}</figure></article>'
        for i, it in enumerate(copy["realisations"]["items"]))

    facts = "".join(
        f'<div><dt>{f["k"]}</dt><dd>{f["v"]}</dd></div>'
        for f in copy["atelier"]["facts"])
    para = "".join(f"<p>{t}</p>" for t in copy["atelier"]["paragraphs"] if t)

    c = copy["contact"]
    monogram = _svg_monogram(copy["brand"]["monogram"], p["ink"], p["accent"])

    # Section "Nos engagements" alimentée par le Positionneur (différenciateurs).
    diffs = (positioning or {}).get("differentiators", [])
    engagements = ""
    if diffs:
        cards = "".join(
            f'<div class="engage" data-reveal><span class="engage__ic" aria-hidden="true">✓</span>'
            f'<h3>{d}</h3></div>' for d in diffs[:3])
        engagements = (
            '<section class="section" id="engagements"><div class="container">'
            '<div class="section__head"><span class="section__num">02</span>'
            '<span class="section__label">Nos engagements</span>'
            '<span class="section__rule"></span></div>'
            f'<div class="engagements">{cards}</div></div></section>')

    head = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{copy['meta']['title']}</title>
<meta name="description" content="{copy['meta']['description']}">
<meta name="theme-color" content="{p['bg']}">
<meta property="og:type" content="website">
<meta property="og:title" content="{copy['meta']['title']}">
<meta property="og:description" content="{copy['meta']['description']}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='8' fill='{p['accent'].replace('#','%23')}'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{font_href}">
<link rel="stylesheet" href="assets/styles.css">
<!-- AGENCY:HEAD -->
</head>
<body class="{grain.strip()}">
{skip}<header class="site-header"><div class="container"><nav class="nav" aria-label="Navigation principale">
<a class="brand" href="#accueil">{monogram}<b>{copy['brand']['name_short']}</b></a>
<button class="nav__toggle" aria-expanded="false" aria-controls="menu" aria-label="Ouvrir le menu">☰</button>
<ul class="nav__links" id="menu">{nav_links}</ul>
</nav></div></header>

<main id="contenu">
<section class="hero" id="accueil"><div class="container"><div class="hero__grid">
<div class="hero__txt" data-reveal>
<p class="eyebrow">{copy['hero']['eyebrow']}</p>
<h1>{copy['hero']['headline']}</h1>
<p class="hero__sub">{copy['hero']['sub']}</p>
<div class="hero__cta">
<a class="btn btn--primary" href="{copy['hero']['cta']['anchor']}">{copy['hero']['cta']['label']}</a>
<a class="btn btn--ghost" href="{copy['hero']['secondary']['anchor']}">{copy['hero']['secondary']['label']}</a>
</div></div>
<figure class="hero__art" data-reveal>{_svg_hero(p, labelled=(rev > 0))}</figure>
</div></div></section>
"""

    sf = copy["savoir_faire"]
    rl = copy["realisations"]
    at = copy["atelier"]
    sections = f"""
<section class="section" id="savoir-faire"><div class="container">
{_svg_joint(p['ink'], p['accent'], p['line'])}
<div class="section__head"><span class="section__num">01</span>
<span class="section__label">{sf['label']}</span><span class="section__rule"></span></div>
<h2>{sf['title']}</h2><p class="lead">{sf['intro']}</p>
<div class="pillars">{pillars}</div>
</div></section>

{engagements}
<section class="section" id="realisations"><div class="container">
<div class="section__head"><span class="section__num">03</span>
<span class="section__label">{rl['label']}</span><span class="section__rule"></span></div>
<h2>{rl['title']}</h2><p class="lead">{rl['intro']}</p>
<div class="reals">{reals}</div>
</div></section>

<section class="section" id="atelier"><div class="container">
<div class="section__head"><span class="section__num">04</span>
<span class="section__label">{at['label']}</span><span class="section__rule"></span></div>
<div class="atelier__grid"><div><h2>{at['title']}</h2>{para}</div>
<dl class="facts">{facts}</dl></div>
</div></section>

<section class="section" id="contact"><div class="container">
<div class="section__head"><span class="section__num">05</span>
<span class="section__label">{c['label']}</span><span class="section__rule"></span></div>
<div class="contact__grid">
<div><h2>{c['title']}</h2><p class="lead">{c['intro']}</p>
<ul class="contact__list">
<li><b>Adresse</b>{c['address']}</li>
<li><b>Téléphone</b>{c['phone']}</li>
<li><b>Email</b>{c['email']}</li>
<li><b>Horaires</b>{c['hours']}</li></ul></div>
<div class="contact__cta"><h3>Un projet ?</h3>
<p>{c['intro']}</p>
<a class="btn btn--primary" href="{c['cta']['anchor']}">{c['cta']['label']}</a></div>
</div></div></section>
</main>

<footer class="site-footer"><div class="container"><div class="nav">
<span>{copy['footer']['blurb']}</span>
<a href="mentions-legales.html">{copy['footer']['legal']}</a>
</div></div></footer>
<script src="assets/main.js" defer></script>
</body>
</html>
"""
    return head + sections


def _render_js() -> str:
    return r"""// Améliorations progressives (le site fonctionne sans JS).
document.documentElement.classList.add('js');
(function () {
  var header = document.querySelector('.site-header');
  var onScroll = function () {
    if (header) header.classList.toggle('is-stuck', window.scrollY > 8);
  };
  onScroll(); window.addEventListener('scroll', onScroll, { passive: true });

  var toggle = document.querySelector('.nav__toggle');
  var menu = document.getElementById('menu');
  if (toggle && menu) {
    toggle.addEventListener('click', function () {
      var open = menu.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
    });
    menu.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') { menu.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false'); }
    });
  }

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var items = [].slice.call(document.querySelectorAll('[data-reveal]'));
  if (reduce || !('IntersectionObserver' in window)) {
    items.forEach(function (el) { el.classList.add('in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.12 });
    items.forEach(function (el) { io.observe(el); });
  }
})();
"""


def _render_legal(copy: dict, client: dict) -> str:
    name = copy["brand"]["name_full"]
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mentions légales — {copy['brand']['name_short']}</title>
<meta name="description" content="Mentions légales de {copy['brand']['name_short']}.">
<meta name="robots" content="noindex">
<link rel="stylesheet" href="assets/styles.css"></head>
<body><a class="skip-link" href="#contenu">Aller au contenu</a>
<main id="contenu" class="section"><div class="container" style="max-width:48rem">
<h1>Mentions légales</h1>
<p><b>Éditeur :</b> {name}, {copy['contact']['address']}.</p>
<p><b>Contact :</b> {copy['contact']['email']} — {copy['contact']['phone']}.</p>
<p><b>Hébergement :</b> hébergeur statique (à compléter lors de la mise en ligne).</p>
<p><b>Données personnelles :</b> les informations transmises via le contact ne servent
qu'à répondre à votre demande et ne sont jamais cédées à des tiers (RGPD).</p>
<p><a class="btn btn--ghost" href="index.html">← Retour à l'accueil</a></p>
</div></main></body></html>
"""


# --------------------------------------------------------------------------- #
def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    design = run.get("design", {})
    copy = run.get("copy", {})
    client = run.client
    strategy = run.get("strategy", {})
    prev = run.get("build", {})
    rev = int(prev.get("_rev", 0))

    voice(run, "builder",
          f"je génère le site « {strategy.get('site_type','html-statique')} »…"
          if rev == 0 else "je reconstruis en intégrant les retours QA…")

    slug = utils.slugify(client.get("name", "client"))
    out = utils.DELIVERABLES_DIR / slug
    src = out / "src"

    html = _render_html(design, copy, rev, run.get("positioning", {}))
    css = _render_css(design)
    js = _render_js()
    legal = _render_legal(copy, client)

    files = {
        src / "index.html": html,
        src / "assets" / "styles.css": css,
        src / "assets" / "main.js": js,
        src / "mentions-legales.html": legal,
    }
    for path, content in files.items():
        utils.write_text(path, content)

    run.put("build", {
        "_rev": rev + 1,
        "site_type": strategy.get("site_type", "html-statique"),
        "dir": str(src),
        "entry": "index.html",
        "files": [str(p) for p in files],
        "had_skip_link": rev > 0,
        "hero_labelled": rev > 0,
    })

    voice(run, "builder",
          f"{len(files)} fichiers écrits dans {src.relative_to(utils.ROOT)} "
          f"(révision {rev + 1}).")

    # Auto-contrôle minimal (l'audit complet revient à l'Inspector).
    self_issues = []
    if "<!doctype html>" not in html.lower():
        self_issues.append("Doctype manquant.")
    if "viewport" not in html:
        self_issues.append("Meta viewport manquant.")
    score = 88 if not self_issues else 50
    return AgentResult(ok=not self_issues, score=float(score),
                       summary=f"Site généré (rev {rev + 1}, {strategy.get('site_type')})",
                       issues=self_issues,
                       artifacts=list(files.keys()))
