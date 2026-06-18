"""
🖥️ Mission Control — interface web locale de pilotage.

Un serveur HTTP (bibliothèque standard, zéro dépendance) qui sert une interface
« salle de contrôle » : on y voit le Manager piloter toute l'équipe en direct —
quel agent est actif, l'avancement du pipeline, le flux d'activité, et un aperçu
du site produit. Les missions se lancent depuis l'interface (boutons) et
tournent en arrière-plan ; l'état est lu en continu depuis `state/runs/<id>`.

Routes :
  GET  /                 -> l'interface
  GET  /app.css /app.js  -> assets
  GET  /api/team         -> les personas (avatars, rôles)
  GET  /api/state[?run]  -> état de la mission suivie (ou la plus récente)
  GET  /api/status       -> état du pilote (mission en cours ?)
  GET  /api/runs         -> historique des missions
  GET  /api/prospects    -> vivier qualifié
  POST /api/launch       -> lance une mission (demo|scout|outreach|accept)
  GET  /site/<slug>/...  -> sert le site livré (pour l'aperçu intégré)
"""
from __future__ import annotations

import json
import mimetypes
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import llm, personas, state, utils
from .agents import scout
from .manager import Manager

WEB = Path(__file__).resolve().parent / "web"


# --------------------------------------------------------------------------- #
# Pilote : lance les missions en arrière-plan, une à la fois.
# --------------------------------------------------------------------------- #
class Controller:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.active = False
        self.command: str | None = None
        self.current_run_id: str | None = None
        self.error: str | None = None
        self.note: str | None = None
        self.pace = 0.6

    def status(self) -> dict:
        return {"active": self.active, "command": self.command,
                "current_run_id": self.current_run_id, "error": self.error,
                "note": self.note}

    def launch(self, command: str, arg=None, pace: float = 0.6) -> tuple[bool, str]:
        with self._lock:
            if self.active:
                return False, "Une mission est déjà en cours."
            self.active = True
            self.command = command
            self.error = None
            self.note = None
            self.pace = max(0.0, float(pace))
        threading.Thread(target=self._run, args=(command, arg), daemon=True).start()
        return True, f"Mission « {command} » lancée."

    def _select(self, qualified: list, selector) -> dict:
        if selector and str(selector).isdigit():
            i = int(selector) - 1
            if 0 <= i < len(qualified):
                return qualified[i]["raw"]
        for q in qualified:
            if selector and (utils.slugify(q["name"]) == utils.slugify(str(selector))
                             or str(selector).lower() in q["name"].lower()):
                return q["raw"]
        return qualified[0]["raw"]

    def _run(self, command: str, arg) -> None:
        try:
            utils.set_pace(self.pace)
            if command == "scout":
                q = scout.qualify_pool()
                utils.write_json(utils.STATE_DIR / "prospects.json", q)
            elif command == "prospect":
                # PROSPECTION RÉELLE : ville + secteur via OpenStreetMap + audit live
                city = (arg or {}).get("city", "").strip()
                sector = (arg or {}).get("sector", "").strip()
                self.note = f"Prospection en cours : {sector or 'tous secteurs'} à {city}…"
                res = scout.qualify_live(city, sector, limit=10)
                utils.write_json(utils.STATE_DIR / "prospects.json", res)
                self.note = (f"{len(res)} prospect(s) trouvé(s) à {city}. Choisis-en un ci-dessous."
                             if res else
                             f"Aucun prospect (avec site web) trouvé pour « {sector} » à {city}. "
                             f"Essaie une ville plus grande, un autre secteur, ou « Mission sur une URL ».")
            elif command == "mission_url":
                # MISSION DIRECTE sur une vraie URL
                url = arg.get("url") if isinstance(arg, dict) else arg
                client = scout.client_from_url(url)
                client["accepted"] = True
                run = state.new_run(client)
                self.current_run_id = run.run_id
                Manager(run).deliver()
            elif command in ("demo", "accept"):
                if command == "demo":                       # vitrine : toujours le vivier
                    raw = scout.qualify_pool()[0]["raw"]
                else:                                       # le prospect choisi par l'utilisateur
                    raw = self._select(_current_prospects() or scout.qualify_pool(), arg)
                client = dict(raw)
                client["accepted"] = True
                run = state.new_run(client)
                self.current_run_id = run.run_id
                Manager(run).deliver()
            elif command == "outreach":
                for x in [x for x in _current_prospects() if x["qualified"]][:3]:
                    client = dict(x["raw"])
                    client["accepted"] = False
                    run = state.new_run(client)
                    self.current_run_id = run.run_id
                    m = Manager(run)
                    m.run_stage("scout")
                    m.run_stage("closer")
                    run.status = "awaiting_reply"
                    run.save()
        except Exception as exc:  # une mission qui plante ne tue pas le serveur
            self.error = str(exc)
            utils.say(f"[dashboard] erreur de mission : {exc}")
        finally:
            utils.set_pace(0.0)
            with self._lock:
                self.active = False
                self.command = None


CONTROLLER = Controller()


def _current_prospects() -> list:
    """Prospects courants : résultats live (state/prospects.json) sinon vivier local."""
    f = utils.STATE_DIR / "prospects.json"
    if f.exists():
        data = utils.read_json_safe(f)
        if data is not None:        # respecte une liste vide (prospection sans résultat)
            return data
    return scout.qualify_pool()


# --------------------------------------------------------------------------- #
# Serveur HTTP
# --------------------------------------------------------------------------- #
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:  # silence la console
        pass

    # -- envoi --------------------------------------------------------- #
    def _send(self, code: int, ctype: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, data, code: int = 200) -> None:
        self._send(code, "application/json; charset=utf-8",
                   json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send(404, "text/plain; charset=utf-8", b"404")
            return
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in (
                "application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        self._send(200, ctype, path.read_bytes())

    # -- routage ------------------------------------------------------- #
    def do_GET(self) -> None:
        u = urlparse(self.path)
        p = u.path
        if p in ("/", "/index.html", "/agence", "/agence.html"):
            return self._file(WEB / "agence.html")        # page de vente "L'agence"
        if p in ("/app", "/app.html", "/mission-control"):
            return self._file(WEB / "index.html")          # le dashboard Mission Control
        if p in ("/app.css", "/app.js", "/agence.css", "/agence.js"):
            return self._file(WEB / p.lstrip("/"))
        if p == "/roster.json":
            return self._file(utils.DATA_DIR / "roster.json")
        if p.startswith("/avatars/"):
            name = p[len("/avatars/"):]
            target = (WEB / "avatars" / name).resolve()
            adir = (WEB / "avatars").resolve()
            if target == adir or adir in target.parents:
                return self._file(target)
            return self._send(403, "text/plain; charset=utf-8", b"403")
        if p == "/api/ai":
            return self._json(self._ai_diag(parse_qs(u.query)))
        if p == "/api/team":
            return self._json(self._team())
        if p == "/api/status":
            return self._json(CONTROLLER.status())
        if p == "/api/runs":
            return self._json(self._runs())
        if p == "/api/prospects":
            return self._json(self._prospects())
        if p == "/api/state":
            return self._json(self._state(parse_qs(u.query)))
        if p.startswith("/site/"):
            return self._site(p)
        self._send(404, "text/plain; charset=utf-8", b"404")

    def do_POST(self) -> None:
        u = urlparse(self.path)
        if u.path == "/api/launch":
            length = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                data = {}
            ok, msg = CONTROLLER.launch(
                data.get("command", "demo"), data.get("arg"),
                float(data.get("pace", 0.6) or 0.6))
            return self._json(
                {"ok": ok, "message": msg,
                 "current_run_id": CONTROLLER.current_run_id},
                202 if ok else 409)
        self._send(404, "text/plain; charset=utf-8", b"404")

    # -- données ------------------------------------------------------- #
    def _ai_diag(self, qs: dict) -> dict:
        """Diagnostic de l'IA : clé visible ? SDK installé ? appel test ?"""
        info = {"code_version": "ai-enabled",
                "key_present": bool(os.environ.get("ANTHROPIC_API_KEY")),
                "model": llm.MODEL, "available": llm.available()}
        try:
            import anthropic  # noqa: F401
            info["sdk_installed"] = True
        except Exception as exc:
            info["sdk_installed"] = False
            info["sdk_error"] = str(exc)[:200]
        if qs.get("ping") and info["available"]:
            try:
                import anthropic
                c = anthropic.Anthropic()
                r = c.messages.create(model=llm.MODEL, max_tokens=50,
                                      messages=[{"role": "user", "content": "Réponds: OK"}])
                txt = next((b.text for b in r.content if getattr(b, "type", "") == "text"), "")
                info["ping_ok"] = True
                info["ping_text"] = txt[:60]
            except Exception as exc:
                info["ping_ok"] = False
                info["ping_error"] = str(exc)[:300]
        return info

    def _team(self) -> list:
        return [{"key": p.key, "name": p.name, "emoji": p.emoji,
                 "personality": p.personality, "description": p.description,
                 "reads": p.reads, "writes": p.writes}
                for p in personas.all_personas()]

    def _runs(self) -> list:
        out = []
        rd = utils.RUNS_DIR
        if rd.exists():
            for p in sorted(rd.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                f = p / "state.json"
                if f.exists():
                    d = utils.read_json_safe(f)
                    if d:
                        out.append({"run_id": d["run_id"],
                                    "client": d.get("client", {}).get("name"),
                                    "status": d.get("status"),
                                    "created_at": d.get("created_at")})
        return out[:20]

    def _prospects(self) -> list:
        try:
            q = _current_prospects()
        except Exception:
            return []
        return [{"index": i + 1, "name": x["name"], "slug": utils.slugify(x["name"]),
                 "location": x.get("location"), "problem": x["headline_problem"],
                 "score": x["opportunity_score"], "qualified": x["qualified"]}
                for i, x in enumerate(q)]

    def _state(self, qs: dict) -> dict:
        run_id = (qs.get("run") or [None])[0] or CONTROLLER.current_run_id
        run = None
        try:
            run = state.load_run(run_id) if run_id else state.latest_run()
        except Exception:
            run = state.latest_run()
        if run is None:
            return {"run": None, "controller": CONTROLLER.status()}
        d = run.to_dict()
        d["slug"] = utils.slugify(run.client.get("name", "client"))
        return {"run": d, "controller": CONTROLLER.status()}

    def _site(self, p: str) -> None:
        rest = p[len("/site/"):]
        parts = rest.split("/", 1)
        slug = parts[0]
        sub = parts[1] if len(parts) > 1 and parts[1] else "index.html"
        base = (utils.DELIVERABLES_DIR / slug / "dist").resolve()
        target = (base / sub).resolve()
        if target != base and base not in target.parents:  # anti-traversal
            self._send(403, "text/plain; charset=utf-8", b"403")
            return
        self._file(target)


def serve(port: int | None = None, host: str | None = None,
          open_browser: bool = True) -> None:
    utils.ensure_dirs()
    # En hébergement (Render, Railway, Fly…), la plateforme fixe PORT et exige 0.0.0.0.
    hosted = bool(os.environ.get("PORT"))
    port = port or int(os.environ.get("PORT", "7000"))
    host = host or ("0.0.0.0" if hosted else "127.0.0.1")
    open_browser = open_browser and host == "127.0.0.1"
    httpd = ThreadingHTTPServer((host, port), Handler)
    shown = "0.0.0.0" if host == "0.0.0.0" else "127.0.0.1"
    url = f"http://{shown}:{port}/"
    utils.rule("═")
    utils.say(f"  🏢  L'AGENCE — {url}")
    utils.say(f"  • Page de vente / équipe : {url}")
    utils.say(f"  • Salle de contrôle (live) : {url}app")
    if not hosted:
        utils.say("  Ouvre l'adresse dans ton navigateur. Ctrl+C pour arrêter.")
    utils.rule("═")
    if open_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()
        utils.say("\n🛑 Mission Control arrêté.")
