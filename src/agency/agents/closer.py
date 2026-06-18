"""
✍️ Closer — Outreach.

Rédige un email de premier contact PERSONNALISÉ et NATUREL, fondé sur le vrai
problème détecté par le Scout. Produit un BROUILLON uniquement : jamais d'envoi
automatique (conformité RGPD / CAN-SPAM). Le brouillon part dans
`outreach/drafts/` et est marqué « À RELIRE ET ENVOYER MANUELLEMENT ».

Le Closer s'auto-évalue contre une grille « humain, pas spam » :
court, un seul appel à l'action, ton parlé, pas de jargon ni de superlatifs.
"""
from __future__ import annotations

from .. import llm, utils
from ..state import RunState
from .base import AgentResult, voice

_RGPD = ("\n\n— — —\nBrouillon généré par l'agent Closer (à relire et envoyer manuellement). "
         "Vous pouvez vous opposer à toute reprise de contact en répondant « STOP ». "
         "Coordonnées professionnelles publiques utilisées au titre de l'intérêt légitime "
         "(RGPD art. 6.1.f).")


def _ai_email(client: dict, audit: dict) -> dict | None:
    if not llm.available():
        return None
    contact = client.get("contact", {})
    first = (contact.get("name", "").split() or [""])[0]
    task = (f"Prospect : {client.get('name')}\nMétier : {client.get('craft')}\n"
            f"Ville : {client.get('location')}\nPrénom du contact : {first or '(inconnu)'}\n"
            f"Problème réel détecté sur son site actuel : {audit.get('headline_problem')}\n\n"
            "Écris un email de premier contact : un OBJET court et une accroche concrète "
            "fondée sur ce problème réel, un corps de moins de 150 mots, ton humain et direct, "
            "UNE seule question/appel à l'action, zéro jargon, zéro superlatif. "
            "Ne mets pas de mention légale (elle est ajoutée automatiquement).")
    schema = {"type": "object", "additionalProperties": False,
              "properties": {"subject": {"type": "string"}, "body": {"type": "string"}},
              "required": ["subject", "body"]}
    data = llm.agent_json("closer", task, schema)
    if not data or not data.get("body"):
        return None
    return {"to": contact.get("email"),
            "subject": data.get("subject", f"Une remarque sur le site de {client.get('name')}"),
            "body": data["body"].rstrip() + _RGPD}

# Mots/tournures qui sentent le mailing de masse -> pénalité.
SPAM_MARKERS = [
    "offre exceptionnelle", "100% gratuit", "cliquez ici", "meilleur prix",
    "sans engagement", "garanti", "promotion", "!!!", "révolutionnaire",
    "leader du marché", "solution clé en main", "n°1", "urgent",
]


def _draft_email(client: dict, audit: dict) -> dict:
    contact = client.get("contact", {})
    first = (contact.get("name", "").split() or [""])[0] or "Bonjour"
    problem = audit.get("headline_problem", "votre site")
    # On dégage la formulation problème en une accroche concrète et concrète.
    hook = {
        "Pas de HTTPS": "votre site s'ouvre encore en « non sécurisé » sur Chrome",
        "Site non responsive": "votre site est difficile à lire depuis un téléphone",
        "Chargement lent": "votre site met plusieurs secondes à s'afficher",
        "Dernière mise à jour": "votre site n'a plus bougé depuis quelques années",
    }
    accroche = next((v for k, v in hook.items() if problem.startswith(k)),
                    "votre site mériterait un petit coup de neuf")

    name = client.get("name", "votre maison")
    city = (client.get("location", "") or "").split(",")[0]
    metier = client.get("craft", "votre activité")

    subject = f"Une remarque sur le site de {name.split('—')[0].strip()}"
    body = f"""Bonjour {first},

Je suis tombé sur le site de {name.split('—')[0].strip()} en cherchant un {metier} {('à ' + city) if city else 'dans la région'}, et une chose m'a sauté aux yeux : {accroche}. Pour une maison comme la vôtre, c'est dommage — la qualité du travail ne se retrouve pas en ligne.

Je conçois des sites sur-mesure pour des artisans et commerces qui veulent une vitrine à la hauteur de leur métier (rien de générique, chaque site est dessiné pour le client). Je serais ravi de vous montrer, sans engagement, une maquette d'accueil pensée pour vous.

Seriez-vous disponible pour un échange de 15 minutes la semaine prochaine ?

Bien à vous,
L'équipe — Atelier Web

— — —
Brouillon généré par l'agent Closer. Vous pouvez vous opposer à toute reprise de
contact en répondant « STOP ». Coordonnées professionnelles publiques utilisées
au titre de l'intérêt légitime (RGPD art. 6.1.f)."""
    return {"to": contact.get("email"), "subject": subject, "body": body}


def _humanity_score(email: dict) -> tuple[float, list]:
    body = email["body"]
    issues = []
    score = 100.0

    # 1) Longueur : un email court convertit mieux.
    words = len(body.split())
    if words > 220:
        score -= 20
        issues.append(f"Trop long ({words} mots) — viser < 160.")

    # 2) Un seul appel à l'action.
    cta_count = body.count("?")
    if cta_count > 2:
        score -= 15
        issues.append("Plus d'un appel à l'action — n'en garder qu'un.")

    # 3) Marqueurs spam.
    low = body.lower()
    for m in SPAM_MARKERS:
        if m in low:
            score -= 12
            issues.append(f"Tournure marketing à bannir : « {m} ».")

    # 4) Personnalisation présente (nom + problème réel).
    if "{" in body or "[" in body:
        score -= 25
        issues.append("Champs non remplis (placeholder).")

    return max(0.0, score), issues


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    client = run.client
    audit = run.get("audit", {})
    voice(run, "closer", "je rédige une approche personnelle (brouillon, jamais envoyée)…")

    email = _ai_email(client, audit) or _draft_email(client, audit)
    score, problems = _humanity_score(email)

    slug = utils.slugify(client.get("name", "prospect"))
    path = utils.OUTREACH_DIR / f"{slug}.md"
    md = (f"# Brouillon d'email — {client.get('name')}\n\n"
          f"> ⚠️ **À RELIRE ET ENVOYER MANUELLEMENT.** Aucun envoi automatique.\n\n"
          f"**À :** {email['to']}  \n"
          f"**Objet :** {email['subject']}\n\n---\n\n{email['body']}\n")
    utils.write_text(path, md)

    run.put("outreach", {"subject": email["subject"], "to": email["to"],
                         "draft_path": str(path), "humanity_score": score})
    voice(run, "closer", f"brouillon prêt → {path.name} (score humain {score:.0f}/100). "
                         f"En attente de validation/envoi humain.")

    ok = score >= 70
    return AgentResult(ok=ok, score=score,
                       summary=f"Brouillon outreach ({score:.0f}/100)",
                       issues=problems, artifacts=[path])
