"""
Contrat commun à tous les agents.

Chaque agent expose une fonction `run(run, attempt, issues) -> AgentResult`.
Le Manager ne connaît que ce contrat : c'est ce qui rend l'équipe modulaire
(ajouter/retirer un agent ne casse rien tant qu'il respecte ce contrat).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .. import personas
from ..state import RunState


@dataclass
class AgentResult:
    ok: bool                          # critère d'acceptation atteint ?
    score: float = 0.0                # qualité 0-100
    summary: str = ""                 # résumé lisible en une ligne
    issues: list = field(default_factory=list)      # problèmes (bloquants ou non)
    rework: list = field(default_factory=list)      # agents à relancer (veto QA)
    artifacts: list = field(default_factory=list)   # fichiers produits

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "score": self.score,
            "summary": self.summary,
            "issues": self.issues,
            "rework": self.rework,
            "artifacts": [str(a) for a in self.artifacts],
        }


def persona_for(key: str):
    """Charge la persona d'un agent depuis `.claude/agents/<key>.md`."""
    return personas.load_persona(key)


def voice(run: RunState, key: str, line: str) -> None:
    """Fait « parler » l'agent dans le journal de la mission et en console."""
    from .. import utils

    p = personas.load_persona(key)
    utils.say(f"   {p.emoji}  {p.name} — {line}")
    run.log_event(key, line)
    run.save()       # rend la ligne visible tout de suite dans le dashboard
    utils.pace()     # cadence (0 en CLI, ralenti pour l'affichage live)
