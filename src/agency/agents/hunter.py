"""🏹 Hunter — qualification commerciale du prospect (non bloquant)."""
from __future__ import annotations

from ..state import RunState
from .base import AgentResult, voice


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    audit = run.get("audit", {})
    problems = audit.get("problems", [])
    crit = sum(1 for p in problems if p.get("severity") == "critique")
    urgency = "élevée" if crit >= 2 else ("moyenne" if problems else "faible")
    client = run.client
    channel = "email" if client.get("contact", {}).get("email") else "téléphone / formulaire"
    lead = {"urgency": urgency, "opportunity": audit.get("opportunity_score", 0),
            "channel": channel,
            "sector": client.get("industry") or client.get("craft") or "—"}
    run.put("lead", lead)
    voice(run, "hunter",
          f"prospect qualifié — urgence {urgency}, {len(problems)} signaux, "
          f"canal conseillé : {channel}.")
    return AgentResult(ok=True, score=85.0, summary=f"Lead qualifié (urgence {urgency})")
