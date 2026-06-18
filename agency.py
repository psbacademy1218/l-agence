#!/usr/bin/env python3
"""
Agence digitale autonome — point d'entrée en ligne de commande.

    python agency.py dashboard [port]      # 🖥️ interface "L'agence" + Mission Control
    python agency.py prospect <ville> <secteur>   # PROSPECTION RÉELLE (OpenStreetMap + audit live)
    python agency.py mission <url>         # MISSION RÉELLE : audite une vraie URL et produit le site
    python agency.py demo                  # démonstration bout-en-bout (vivier local)
    python agency.py scout                 # liste qualifiée (vivier local)
    python agency.py outreach [n]          # brouillons d'emails (jamais envoyés)
    python agency.py accept <slug|index>   # le prospect accepte -> production + déploiement
    python agency.py serve <slug>          # (re)servir le site livré en local
    python agency.py status                # état de la dernière mission
    python agency.py team                  # présenter l'équipe d'agents
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from agency import personas, state, utils          # noqa: E402
from agency.agents import scout, launcher          # noqa: E402
from agency.manager import Manager                 # noqa: E402


# --------------------------------------------------------------------------- #
def cmd_team() -> None:
    utils.rule("═")
    utils.say("  L'ÉQUIPE DE L'AGENCE DIGITALE AUTONOME")
    utils.rule("═")
    for p in personas.all_personas():
        utils.say(f"\n{p.emoji}  {p.name} — {p.description}")
        if p.personality:
            utils.say(f"     « {p.personality} »")
        if p.reads:
            utils.say(f"     ⟵ lit   : {', '.join(p.reads)}")
        if p.writes:
            utils.say(f"     ⟶ écrit : {', '.join(p.writes)}")


def cmd_scout() -> list[dict]:
    utils.ensure_dirs()
    utils.rule("═")
    utils.say("🔍  PROSPECTION — recherche d'entreprises au site daté/cassé")
    utils.rule("═")
    qualified = scout.qualify_pool()
    utils.write_json(utils.STATE_DIR / "prospects.json", qualified)
    for i, q in enumerate(qualified, 1):
        flag = "✅ qualifié" if q["qualified"] else "—  écarté"
        utils.say(f"\n{i}. {q['name']}  [{flag}]  score {q['opportunity_score']}/100")
        utils.say(f"   {q['url']}  ·  {q.get('location','')}")
        utils.say(f"   Problème majeur : {q['headline_problem']}")
        utils.say(f"   Contact : {q['contact'].get('name','?')} <{q['contact'].get('email','?')}>")
    utils.say(f"\n→ Liste enregistrée : {utils.STATE_DIR / 'prospects.json'}")
    return qualified


def cmd_outreach(n: int = 3) -> None:
    qualified = [q for q in cmd_scout() if q["qualified"]][:n]
    utils.rule("═")
    utils.say("✍️   OUTREACH — brouillons d'emails (AUCUN envoi automatique)")
    utils.rule("═")
    for q in qualified:
        client = dict(q["raw"]); client["accepted"] = False
        run = state.new_run(client)
        mgr = Manager(run)
        mgr.run_stage("scout")
        mgr.run_stage("closer")
        run.status = "awaiting_reply"; run.save()
    utils.say(f"\n→ Brouillons dans : {utils.OUTREACH_DIR}")
    utils.say("  Relisez-les, personnalisez si besoin, puis envoyez-les VOUS-MÊME.")


def _select_prospect(selector: str) -> dict:
    qualified = scout.qualify_pool()
    if selector.isdigit():
        idx = int(selector) - 1
        if 0 <= idx < len(qualified):
            return qualified[idx]["raw"]
    for q in qualified:
        if utils.slugify(q["name"]) == utils.slugify(selector) \
                or selector.lower() in q["name"].lower():
            return q["raw"]
    raise SystemExit(f"Prospect introuvable : {selector}")


def cmd_accept(selector: str) -> state.RunState:
    client = _select_prospect(selector)
    client["accepted"] = True  # le prospect a répondu favorablement
    run = state.new_run(client)
    utils.rule("═")
    utils.say(f"🤝  ACCEPTATION — {client['name']} lance la production")
    utils.rule("═")
    Manager(run).deliver()
    return run


def cmd_prospect(city: str, sector: str) -> list[dict]:
    utils.ensure_dirs()
    utils.rule("═")
    utils.say(f"🔍  PROSPECTION RÉELLE — {sector} à {city} (OpenStreetMap + audit live)")
    utils.rule("═")
    res = scout.qualify_live(city, sector, limit=10)
    if not res:
        utils.say("Aucun résultat en ligne — repli sur le vivier local.")
        res = scout.qualify_pool()
    utils.write_json(utils.STATE_DIR / "prospects.json", res)
    for i, q in enumerate(res, 1):
        flag = "✅ qualifié" if q["qualified"] else "—  écarté"
        utils.say(f"\n{i}. {q['name']}  [{flag}]  {q['opportunity_score']}/100")
        utils.say(f"   {q['url']}")
        utils.say(f"   Problème majeur : {q['headline_problem']}")
    utils.say(f"\n→ {len(res)} prospects enregistrés dans {utils.STATE_DIR / 'prospects.json'}")
    utils.say("  Lance la production : python agency.py accept 1")
    return res


def cmd_mission(url: str) -> state.RunState:
    utils.ensure_dirs()
    client = scout.client_from_url(url)
    client["accepted"] = True
    run = state.new_run(client)
    utils.rule("═")
    utils.say(f"🚀  MISSION RÉELLE — {client['name']}  ({url})")
    utils.rule("═")
    Manager(run).deliver()
    _recap(run)
    return run


def cmd_demo() -> state.RunState:
    utils.ensure_dirs()
    utils.rule("═")
    utils.say("  ✨  DÉMONSTRATION DE BOUT EN BOUT  ✨")
    utils.say("  Détection → approche → (acceptation simulée) → site déployé")
    utils.rule("═")

    qualified = scout.qualify_pool()
    top = qualified[0]
    utils.say(f"\n🔍 Scout a retenu le meilleur prospect : « {top['name']} » "
              f"(opportunité {top['opportunity_score']}/100)")
    utils.say(f"   Problème principal : {top['headline_problem']}")

    client = dict(top["raw"])
    client["accepted"] = True  # on simule une réponse favorable du prospect
    run = state.new_run(client)
    Manager(run).deliver()
    _recap(run)
    return run


def cmd_serve(slug: str) -> None:
    dist = utils.DELIVERABLES_DIR / utils.slugify(slug) / "dist"
    if not dist.exists():
        raise SystemExit(f"Aucun build à servir : {dist}. Lancez d'abord `accept`/`demo`.")
    launcher.serve_blocking(dist, port=8800)


def cmd_status() -> None:
    run = state.latest_run()
    if not run:
        utils.say("Aucune mission pour l'instant. Lancez `python agency.py demo`.")
        return
    utils.rule("═")
    utils.say(f"  ÉTAT DE MISSION — {run.client.get('name')}  ({run.status})")
    utils.rule("═")
    for s in run.stages:
        icon = {"passed": "✅", "failed": "❌", "running": "⏳",
                "pending": "·", "skipped": "—"}.get(s["status"], "?")
        score = f" {s['score']:.0f}/100" if s.get("score") is not None else ""
        utils.say(f"  {icon} {s['name']:<12} {s['status']:<9}"
                  f"  tentatives:{s['attempts']}{score}")
    deploy = run.get("deploy", {})
    if deploy:
        utils.say(f"\n  🚀 Déploiement : {deploy.get('serve_command')}")


# --------------------------------------------------------------------------- #
def _recap(run: state.RunState) -> None:
    bb = run.blackboard
    utils.say("")
    utils.rule("═")
    utils.say("  📋  RÉCAP DE MISSION")
    utils.rule("═")
    utils.say(f"  Client  : {run.client.get('name')}")
    utils.say(f"  Statut  : {run.status}")
    site_type = bb.get('build', {}).get('site_type', '?')
    utils.say(f"  Site    : {site_type}  ·  DA : "
              f"{bb.get('design', {}).get('archetype','?')} / "
              f"{bb.get('design', {}).get('palette_key','?')}")
    deploy = bb.get("deploy", {})
    if deploy:
        utils.say(f"  Déployé : {deploy.get('verified')}  →  {deploy.get('serve_command')}")
    utils.say(f"  État    : {run.path.relative_to(utils.ROOT)}")


HELP = __doc__


def main(argv: list[str]) -> int:
    if not argv:
        utils.say(HELP); return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "demo":
        cmd_demo()
    elif cmd == "prospect":
        if len(rest) < 2:
            raise SystemExit('Usage : python agency.py prospect "<ville>" "<secteur>"')
        cmd_prospect(rest[0], rest[1])
    elif cmd == "mission":
        if not rest:
            raise SystemExit("Usage : python agency.py mission <url>")
        cmd_mission(rest[0])
    elif cmd == "scout":
        cmd_scout()
    elif cmd == "outreach":
        cmd_outreach(int(rest[0]) if rest else 3)
    elif cmd == "accept":
        if not rest:
            raise SystemExit("Usage : python agency.py accept <slug|index>")
        cmd_accept(rest[0])
    elif cmd == "serve":
        if not rest:
            raise SystemExit("Usage : python agency.py serve <slug>")
        cmd_serve(rest[0])
    elif cmd in ("dashboard", "ui", "mission-control"):
        from agency import dashboard
        port = next((int(a) for a in rest if a.isdigit()), None)
        host = "0.0.0.0" if "public" in rest else None
        dashboard.serve(port=port, host=host, open_browser=("noopen" not in rest))
    elif cmd in ("status", "state"):
        cmd_status()
    elif cmd in ("team", "agents"):
        cmd_team()
    else:
        utils.say(f"Commande inconnue : {cmd}\n"); utils.say(HELP); return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
