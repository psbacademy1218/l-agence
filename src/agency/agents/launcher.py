"""
🚀 Launcher — Build & déploiement.

Finalise le build (copie `src/` -> `dist/`), déploie EN LOCAL via un serveur
HTTP statique, puis VÉRIFIE le déploiement (codes HTTP, présence du contenu clé,
fichiers SEO servis). Pour la démo, il vérifie puis libère le port et fournit la
commande exacte pour reservir le site à la demande.

Le type de déploiement s'adapterait au `site_type` (statique -> hébergeur
statique/Netlify ; CMS -> serveur PHP/MySQL) ; ici, statique en local.
"""
from __future__ import annotations

import functools
import shutil
import socket
import threading
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from .. import utils
from ..state import RunState
from .base import AgentResult, voice


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def serve(directory: str, port: int) -> ThreadingHTTPServer:
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(directory))
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def serve_blocking(directory: str, port: int | None = None) -> None:
    """Utilisé par la commande `agency.py serve` (bloquant, Ctrl+C pour stopper)."""
    port = port or 8800
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(directory))
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}/"
    utils.say(f"🚀 Site servi sur {url} — Ctrl+C pour arrêter.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()
        utils.say("\n🛑 Serveur arrêté.")


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    build = run.get("build", {})
    copy = run.get("copy", {})
    src = utils.ROOT / build.get("dir", "")
    slug = utils.slugify(run.client.get("name", "client"))
    dist = utils.DELIVERABLES_DIR / slug / "dist"

    voice(run, "launcher", "je finalise le build et je déploie en local…")

    if not src.exists():
        return AgentResult(ok=False, score=0, summary="Rien à déployer.",
                           issues=["Dossier src absent."])

    # 1) Build : src -> dist
    if dist.exists():
        shutil.rmtree(dist)
    shutil.copytree(src, dist)

    # 2) Déploiement local + vérification
    port = _free_port()
    httpd = serve(dist, port)
    base = f"http://127.0.0.1:{port}"
    verifications = []
    try:
        # page d'accueil
        with urllib.request.urlopen(base + "/", timeout=5) as r:
            body = r.read().decode("utf-8", "replace")
            verifications.append(("GET /", r.status, r.status == 200))
            headline = copy.get("hero", {}).get("headline", "")
            content_ok = headline and headline in body
            verifications.append(("Contenu héro présent", "ok" if content_ok else "absent",
                                  bool(content_ok)))
        for path in ("/sitemap.xml", "/robots.txt", "/mentions-legales.html"):
            try:
                with urllib.request.urlopen(base + path, timeout=5) as r:
                    verifications.append((f"GET {path}", r.status, r.status == 200))
            except Exception as exc:
                verifications.append((f"GET {path}", str(exc), False))
    finally:
        httpd.shutdown()

    ok = all(v[2] for v in verifications)
    score = round(100 * sum(v[2] for v in verifications) / len(verifications), 1)

    deploy = {
        "dist": str(dist),
        "verified": ok,
        "checks": [{"check": c, "result": str(s), "ok": o} for c, s, o in verifications],
        "url": f"http://127.0.0.1:8800/",
        "serve_command": f'python agency.py serve {slug}',
        "site_type": build.get("site_type", "html-statique"),
    }
    run.put("deploy", deploy)

    # Rapport de déploiement
    report = [f"# Déploiement — {run.client.get('name')}", "",
              f"- Type de site : **{deploy['site_type']}**",
              f"- Build : `{dist.relative_to(utils.ROOT)}`",
              f"- Vérifié : {'✅ oui' if ok else '❌ non'} ({score}/100)", "",
              "## Vérifications"]
    for c, s, o in verifications:
        report.append(f"- {'✅' if o else '❌'} {c} → {s}")
    report += ["", "## Servir le site",
               f"```\n{deploy['serve_command']}\n```",
               f"Puis ouvrir : {deploy['url']}"]
    rp = run.dir / "deploy-report.md"
    utils.write_text(rp, "\n".join(report))

    for c, s, o in verifications:
        voice(run, "launcher", f"{'✅' if o else '❌'} {c} → {s}")
    voice(run, "launcher",
          f"déploiement vérifié ({score}/100). Pour (re)servir : {deploy['serve_command']}")

    return AgentResult(ok=ok, score=score,
                       summary=f"Déployé en local ({score}/100)",
                       issues=[] if ok else ["Vérification de déploiement incomplète."],
                       artifacts=[rp])
