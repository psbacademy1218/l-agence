"""⚙️ Automatiseur — check-list d'automatisations post-lancement (livrable, non bloquant)."""
from __future__ import annotations

from .. import utils
from ..state import RunState
from .base import AgentResult, voice

CHECKLIST = [
    "Formulaire de contact → email instantané (et copie au client)",
    "Mesure d'audience sans cookie (Plausible) — prête, à activer",
    "Prise de rendez-vous en ligne (si pertinent)",
    "Demande d'avis automatique après prestation",
    "Sauvegarde du site et certificat HTTPS auto-renouvelé",
    "Réponse automatique hors horaires d'ouverture",
]


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    run.put("automations", {"items": len(CHECKLIST)})
    md = (f"# Automatisations conseillées — {run.client.get('name')}\n\n"
          + "".join(f"- [ ] {c}\n" for c in CHECKLIST))
    art = run.dir / "automations.md"
    utils.write_text(art, md)
    voice(run, "automatiseur", f"{len(CHECKLIST)} automatisations recommandées listées.")
    return AgentResult(ok=True, score=84.0, summary="Check-list automatisations", artifacts=[art])
