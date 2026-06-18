"""🖌️ Illustrateur — brief visuel cohérent avec la direction artistique (non bloquant)."""
from __future__ import annotations

from .. import utils
from ..state import RunState
from .base import AgentResult, voice

MOTIFS = {
    "editorial-craft": "matière & assemblage (lignes du bois, queue d'aronde)",
    "swiss-minimal": "grille stricte et filets capillaires",
    "organic-soft": "formes douces et courbes organiques",
    "retro-print": "trame sérigraphie et ombres décalées",
    "industrial-utilitarian": "lignes techniques et repères de grille",
}


def run(run: RunState, attempt: int = 1, issues: list | None = None) -> AgentResult:
    design = run.get("design", {})
    arch = design.get("archetype", "")
    visuals = {
        "motif": MOTIFS.get(arch, "motif géométrique sobre"),
        "icons": "pictogrammes linéaires fins, trait régulier",
        "photo": "lumière naturelle, gros plans sur le métier, peu de banque d'images",
    }
    run.put("visuals", visuals)
    md = (f"# Brief visuel — {run.client.get('name')}\n\n"
          f"- Motif signature : {visuals['motif']}\n"
          f"- Icônes : {visuals['icons']}\n"
          f"- Direction photo : {visuals['photo']}\n")
    art = run.dir / "visual-brief.md"
    utils.write_text(art, md)
    voice(run, "illustrateur", f"motif signature retenu : {visuals['motif']}.")
    return AgentResult(ok=True, score=85.0, summary="Brief visuel", artifacts=[art])
