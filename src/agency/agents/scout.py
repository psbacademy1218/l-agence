"""
🔍 Scout — Prospection (RÉELLE et autonome).

Capacités réelles, sans aucune clé API :
  • discover(ville, secteur) : trouve de VRAIES entreprises via l'API publique
    OpenStreetMap/Overpass (commerces ayant un site web).
  • audit_url(url) : télécharge et analyse un VRAI site (HTTPS, responsive,
    vitesse mesurée, liens cassés, techno, meta, sitemap, année de copyright…).
  • qualify_live(ville, secteur) : découvre + audite + classe (prospection auto).
  • qualify_pool() : repli sur le vivier local si hors-ligne / pas de résultats.

Le reste de l'agence ne voit qu'une liste de prospects qualifiés : le passage
du simulé au réel est transparent.
"""
from __future__ import annotations

import json
import re
import socket
import time
import urllib.parse
import urllib.request
from datetime import datetime

from .. import utils
from ..state import RunState
from .base import AgentResult, voice

UA = "AgenceAutonome/1.0 (+https://example.com; prospection responsable)"
OVERPASS = ["https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter"]

# Secteur (saisi par l'utilisateur) -> filtre OpenStreetMap
SECTOR_TAGS = {
    "boulangerie": 'shop=bakery', "pâtisserie": 'shop=pastry', "patisserie": 'shop=pastry',
    "restaurant": 'amenity=restaurant', "café": 'amenity=cafe', "cafe": 'amenity=cafe',
    "coiffeur": 'shop=hairdresser', "fleuriste": 'shop=florist',
    "boucherie": 'shop=butcher', "garage": 'shop=car_repair',
    "opticien": 'shop=optician', "institut de beauté": 'shop=beauty',
    "beauté": 'shop=beauty', "menuisier": 'craft=carpenter', "ébéniste": 'craft=carpenter',
    "artisan": 'craft=carpenter', "plombier": 'craft=plumber',
    "électricien": 'craft=electrician', "electricien": 'craft=electrician',
    "avocat": 'office=lawyer', "agence immobilière": 'office=estate_agent',
    "immobilier": 'office=estate_agent', "dentiste": 'amenity=dentist',
    "vétérinaire": 'amenity=veterinary', "veterinaire": 'amenity=veterinary',
    "hôtel": 'tourism=hotel', "hotel": 'tourism=hotel',
}
SECTOR_LABEL = {
    'shop=bakery': ("boulangerie", "commerce de bouche"),
    'shop=pastry': ("pâtisserie", "commerce de bouche"),
    'amenity=restaurant': ("restaurant", "restauration"),
    'amenity=cafe': ("café", "restauration"),
    'shop=hairdresser': ("salon de coiffure", "beauté & bien-être"),
    'shop=florist': ("fleuriste", "commerce de détail"),
    'shop=butcher': ("boucherie", "commerce de bouche"),
    'shop=car_repair': ("garage automobile", "automobile"),
    'shop=optician': ("opticien", "santé & optique"),
    'shop=beauty': ("institut de beauté", "beauté & bien-être"),
    'craft=carpenter': ("menuisier / ébéniste", "artisanat"),
    'craft=plumber': ("plombier", "artisanat"),
    'craft=electrician': ("électricien", "artisanat"),
    'office=lawyer': ("cabinet d'avocats", "services professionnels"),
    'office=estate_agent': ("agence immobilière", "immobilier"),
    'amenity=dentist': ("cabinet dentaire", "santé"),
    'amenity=veterinary': ("cabinet vétérinaire", "santé"),
    'tourism=hotel': ("hôtel", "hôtellerie"),
}


# --------------------------------------------------------------------------- #
# HTTP bas niveau
# --------------------------------------------------------------------------- #
def _fetch(url: str, timeout: float = 12.0, method: str = "GET"):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "text/html,*/*"}, method=method)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read(600_000) if method == "GET" else b""
        return {"status": r.status, "html": body.decode("utf-8", "replace"),
                "elapsed": time.time() - t0, "final_url": r.geturl(),
                "bytes": len(body)}


def _normalize(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


# --------------------------------------------------------------------------- #
# AUDIT RÉEL d'un site
# --------------------------------------------------------------------------- #
def audit_url(url: str, deep: bool = False) -> dict:
    socket.setdefaulttimeout(15)
    url = _normalize(url)
    res = {"reachable": False, "url": url, "signals": {}, "extracted": {}}
    if not url:
        return res

    page = None
    https = url.startswith("https://")
    try:
        page = _fetch(url, timeout=12)
        https = page["final_url"].startswith("https://")
    except Exception:
        # tentative en http si https échoue
        try:
            page = _fetch("http://" + url.split("://", 1)[1], timeout=10)
            https = False
        except Exception:
            return res

    html = page["html"]
    low = html.lower()
    res["reachable"] = True

    # --- signaux techniques réels ---
    sig = {}
    sig["https"] = https
    sig["load_time_s"] = round(page["elapsed"], 2)
    sig["responsive"] = ('name="viewport"' in low) or ("name='viewport'" in low)
    sig["mobile_friendly"] = sig["responsive"]
    sig["meta_description"] = ('name="description"' in low)
    sig["page_kb"] = round(page["bytes"] / 1024, 1)

    tech = []
    if ".swf" in low or "shockwave" in low or "flash" in low:
        tech.append("Flash")
    if "wp-content" in low or 'name="generator" content="wordpress' in low:
        tech.append("WordPress")
    if "wix.com" in low or "_wix" in low:
        tech.append("Wix")
    if "shopify" in low:
        tech.append("Shopify")
    if low.count("<table") >= 6:
        tech.append("mise en page en tableaux (daté)")
    sig["tech"] = ", ".join(tech) if tech else "—"

    # année de dernière mise à jour estimée (copyright)
    years = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)[^\d]{0,12}(20\d{2})", low)]
    years += [int(y) for y in re.findall(r"(20\d{2})\s*[-–]\s*(?:tous droits|all rights)", low)]
    if years:
        sig["last_updated_year"] = max(years)

    # sitemap & favicon
    try:
        base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(page["final_url"]))
        sm = _fetch(base + "/sitemap.xml", timeout=6, method="HEAD")
        sig["sitemap"] = sm["status"] == 200
    except Exception:
        sig["sitemap"] = False
    sig["favicon"] = ("rel=\"icon\"" in low or "rel='icon'" in low or "shortcut icon" in low)
    sig["contact_form"] = ("<form" in low)

    # estimation perf (proxy) à partir du temps de chargement et du poids
    perf = 100 - int(sig["load_time_s"] * 9) - (15 if sig["page_kb"] > 600 else 0)
    sig["lighthouse_perf"] = max(5, min(99, perf))

    # liens cassés (échantillon) — uniquement en audit profond
    if deep:
        sig["broken_links"] = _broken_link_sample(html, page["final_url"])

    res["signals"] = sig

    # --- contenu réel extrait (utile au Copywriter) ---
    res["extracted"] = _extract_content(html)
    return res


def _broken_link_sample(html: str, base_url: str, limit: int = 4) -> int:
    base = urllib.parse.urlsplit(base_url)
    hrefs = re.findall(r'href=["\']([^"\'#]+)["\']', html)
    seen, checked, broken = set(), 0, 0
    for h in hrefs:
        if h.startswith(("mailto:", "tel:", "javascript:")):
            continue
        full = urllib.parse.urljoin(base_url, h)
        sp = urllib.parse.urlsplit(full)
        if sp.netloc != base.netloc or full in seen:
            continue
        seen.add(full)
        checked += 1
        try:
            r = _fetch(full, timeout=5, method="HEAD")
            if r["status"] >= 400:
                broken += 1
        except Exception:
            broken += 1
        if checked >= limit:
            break
    return broken


def _extract_content(html: str) -> dict:
    def first(pat):
        m = re.search(pat, html, re.I | re.S)
        return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    title = first(r"<title[^>]*>(.*?)</title>")
    desc = first(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']')
    site_name = first(r'<meta\s+property=["\']og:site_name["\']\s+content=["\'](.*?)["\']')
    og_title = first(r'<meta\s+property=["\']og:title["\']\s+content=["\'](.*?)["\']')
    h1 = re.sub(r"<[^>]+>", "", first(r"<h1[^>]*>(.*?)</h1>"))
    h2s = [re.sub(r"<[^>]+>", "", x).strip()
           for x in re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.I | re.S)]
    h2s = [re.sub(r"\s+", " ", x) for x in h2s if 3 < len(x.strip()) < 70][:6]
    return {"title": title[:160], "description": desc[:200], "h1": h1[:120],
            "site_name": site_name[:80], "og_title": og_title[:120], "headings": h2s}


# --------------------------------------------------------------------------- #
# DÉCOUVERTE RÉELLE (OpenStreetMap / Overpass)
# --------------------------------------------------------------------------- #
def discover(city: str, sector: str, limit: int = 12) -> list[dict]:
    tag = SECTOR_TAGS.get((sector or "").strip().lower())
    if not tag:
        tag = 'shop=bakery'  # repli raisonnable
    craft, industry = SECTOR_LABEL.get(tag, (sector or "commerce", "commerce de détail"))
    query = (
        f'[out:json][timeout:25];'
        f'area["name"="{city}"]["boundary"="administrative"]->.a;'
        f'( nwr[{tag}]["website"](area.a); nwr[{tag}]["contact:website"](area.a); );'
        f'out tags center {limit * 3};')
    data = urllib.parse.urlencode({"data": query}).encode()
    elements = []
    for ep in OVERPASS:
        try:
            req = urllib.request.Request(ep, data=data,
                                         headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                elements = json.loads(r.read()).get("elements", [])
            if elements:
                break
        except Exception:
            continue

    out, seen = [], set()
    for el in elements:
        t = el.get("tags", {})
        site = t.get("website") or t.get("contact:website")
        name = t.get("name")
        if not site or not name:
            continue
        host = urllib.parse.urlsplit(_normalize(site)).netloc.replace("www.", "")
        if host in seen:
            continue
        seen.add(host)
        addr = " ".join(filter(None, [t.get("addr:housenumber"), t.get("addr:street")]))
        out.append({
            "name": name, "url": site, "industry": industry, "craft": craft,
            "location": f"{addr+', ' if addr else ''}{city}".strip(", "),
            "contact": {"name": "", "role": "", "email": t.get("contact:email") or t.get("email", "")},
            "values": [], "about": t.get("description", ""),
            "signals": {},
        })
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------------------- #
# Diagnostic (signaux -> problèmes + score d'opportunité) — inchangé
# --------------------------------------------------------------------------- #
def diagnose(prospect: dict) -> dict:
    s = prospect.get("signals", {}) or {}
    problems: list[dict] = []
    score = 0
    year = datetime.now().year

    def add(weight, label, severity):
        nonlocal score
        score += weight
        problems.append({"weight": weight, "severity": severity, "label": label})

    if not s.get("https", True):
        add(18, "Pas de HTTPS : navigateurs affichent « site non sécurisé »", "critique")
    if not s.get("mobile_friendly", True) or not s.get("responsive", True):
        add(18, "Site non responsive : inutilisable sur smartphone (60 %+ du trafic)", "critique")
    lt = float(s.get("load_time_s", 0) or 0)
    if lt >= 4:
        add(min(15, int((lt - 3) * 4)), f"Chargement lent ({lt:.1f}s) : abandons avant affichage", "élevée")
    last = int(s.get("last_updated_year", year) or year)
    age = max(0, year - last)
    if age >= 3:
        add(min(15, age * 2), f"Dernière mise à jour vers {last} ({age} ans) : image datée", "élevée")
    bl = int(s.get("broken_links", 0) or 0)
    if bl:
        add(min(10, bl * 3), f"{bl} lien(s) cassé(s) détecté(s) : parcours interrompu", "moyenne")
    perf = int(s.get("lighthouse_perf", 100) or 100)
    if perf < 50:
        add(min(12, (50 - perf) // 3), f"Performance estimée {perf}/100 : trop faible", "élevée")
    tech = str(s.get("tech", ""))
    if any(k in tech.lower() for k in ("flash", "tableau", "daté", "wix")):
        add(8, f"Technologie datée : {tech}", "élevée")
    if not s.get("meta_description", True):
        add(6, "Aucune meta description : extraits Google peu engageants", "moyenne")
    if not s.get("sitemap", True):
        add(6, "Aucun sitemap.xml : indexation partielle", "moyenne")
    if not s.get("contact_form", True):
        add(5, "Aucun formulaire de contact : friction pour les demandes", "moyenne")

    score = min(100, score)
    problems.sort(key=lambda p: p["weight"], reverse=True)
    headline = problems[0]["label"] if problems else "Site fonctionnel — faible opportunité"
    return {"opportunity_score": score, "headline_problem": headline,
            "problems": problems, "qualified": score >= 45, "signals": s}


# --------------------------------------------------------------------------- #
# Vivier -> liste qualifiée
# --------------------------------------------------------------------------- #
def _entry(p: dict, diag: dict) -> dict:
    return {"name": p["name"], "url": p.get("url"), "industry": p.get("industry"),
            "location": p.get("location"), "contact": p.get("contact", {}),
            "headline_problem": diag["headline_problem"],
            "opportunity_score": diag["opportunity_score"],
            "qualified": diag["qualified"], "raw": p, "diagnostic": diag}


def client_from_url(url: str) -> dict:
    """Construit une fiche client à partir d'une vraie URL (pour une mission directe)."""
    a = audit_url(url, deep=False)
    ext = a.get("extracted", {})
    host = urllib.parse.urlsplit(_normalize(url)).netloc.replace("www.", "")
    raw = (ext.get("site_name") or ext.get("og_title") or ext.get("title")
           or ext.get("h1") or host)
    name = re.split(r"[|—–·]| - ", raw)[0].strip() or host
    if name.lower() in ("", "accueil", "home", "bienvenue") or name == host:
        name = host  # à défaut, on garde le domaine (l'utilisateur pourra renommer)
    return {"name": name, "url": url, "craft": "", "industry": "", "location": "",
            "contact": {"email": ""}, "values": [], "about": ext.get("description", "")}


def qualify_pool() -> list[dict]:
    """Vivier local (repli déterministe, hors-ligne)."""
    pool = utils.read_json(utils.DATA_DIR / "prospect_pool.json")
    out = [_entry(p, diagnose(p)) for p in pool.get("prospects", [])]
    out.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return out


def qualify_live(city: str, sector: str, limit: int = 10) -> list[dict]:
    """Prospection RÉELLE : découverte + audit + classement."""
    prospects = discover(city, sector, limit=limit)
    out = []
    for p in prospects:
        a = audit_url(p["url"], deep=False)
        if a["reachable"]:
            p["signals"] = a["signals"]
            if a["extracted"].get("description") and not p.get("about"):
                p["about"] = a["extracted"]["description"]
            p["_extracted"] = a["extracted"]
        diag = diagnose(p)
        out.append(_entry(p, diag))
    out.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return out


# --------------------------------------------------------------------------- #
# Étape de mission : audit RÉEL du prospect retenu
# --------------------------------------------------------------------------- #
def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    client = run.client
    url = client.get("url")
    voice(run, "scout", f"j'audite le site réel de « {client.get('name')} »…"
          if url else "aucun site existant : j'évalue le potentiel de présence en ligne…")

    extracted = {}
    if url and not client.get("_audited"):
        a = audit_url(url, deep=True)
        if a["reachable"]:
            client["signals"] = a["signals"]
            extracted = a["extracted"]
            client["_audited"] = True
        else:
            client["_unreachable"] = True

    if client.get("signals"):
        diag = diagnose(client)
    else:
        # pas de site (ou injoignable) : forte opportunité, présence à créer
        diag = {"opportunity_score": 85,
                "headline_problem": ("Site injoignable" if client.get("_unreachable")
                                     else "Aucun site existant") + " : présence en ligne à bâtir",
                "problems": [{"weight": 30, "severity": "critique",
                              "label": "Pas de vitrine en ligne exploitable"}],
                "qualified": True, "signals": {}}

    run.put("audit", {"url": url, "opportunity_score": diag["opportunity_score"],
                      "headline_problem": diag["headline_problem"],
                      "problems": diag["problems"], "signals": diag["signals"],
                      "extracted": extracted, "reachable": not client.get("_unreachable", False)})

    top = "; ".join(p["label"] for p in diag["problems"][:3]) or "rien à signaler"
    voice(run, "scout", f"score d'opportunité {diag['opportunity_score']}/100. {top}.")

    # Une mission acceptée se construit toujours : le score d'opportunité est
    # informatif (il sert à filtrer les prospects, pas à bloquer un client choisi).
    score = float(min(99, 78 + diag["opportunity_score"] // 4))
    return AgentResult(ok=True, score=score,
                       summary=f"{len(diag['problems'])} problèmes, opportunité {diag['opportunity_score']}/100")
