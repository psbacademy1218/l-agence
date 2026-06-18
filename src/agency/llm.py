"""
🧠 Cerveau IA (Claude) — optionnel, activé par la clé ANTHROPIC_API_KEY.

Quand la clé est présente ET le SDK `anthropic` installé, les agents peuvent
rédiger un contenu vraiment sur-mesure avec Claude. Sinon, tout retombe
automatiquement sur le moteur déterministe (le site se construit quand même).

La clé n'est JAMAIS écrite dans le code : elle est lue dans l'environnement
(local : `setx ANTHROPIC_API_KEY ...` ; en ligne : variable d'env Render).
Modèle par défaut : claude-opus-4-8 (réglable via AGENCY_LLM_MODEL).
"""
from __future__ import annotations

import json
import os
import re

from . import utils

MODEL = os.environ.get("AGENCY_LLM_MODEL", "claude-opus-4-8")


def available() -> bool:
    """Vrai si une clé est présente et le SDK importable."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except Exception:
        return False


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):                       # enlève les ```json … ```
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    i, j = text.find("{"), text.rfind("}")
    if i != -1 and j != -1 and j > i:
        text = text[i:j + 1]
    return json.loads(text)


def _text_of(resp) -> str:
    return next((b.text for b in resp.content if getattr(b, "type", "") == "text"), "")


def generate_json(system: str, user: str, schema: dict,
                  max_tokens: int = 12000) -> dict | None:
    """Appelle Claude et renvoie un dict JSON. None si tout échoue (repli déterministe)."""
    if not available():
        return None
    try:
        import anthropic
        client = anthropic.Anthropic()  # clé lue dans l'environnement

        # Tentative 1 — sortie JSON structurée + réflexion adaptative.
        try:
            resp = client.messages.create(
                model=MODEL, max_tokens=max_tokens, system=system,
                messages=[{"role": "user", "content": user}],
                thinking={"type": "adaptive"},
                output_config={"effort": "medium",
                               "format": {"type": "json_schema", "schema": schema}},
            )
            txt = _text_of(resp)
            if txt:
                return _extract_json(txt)
        except Exception as exc1:
            utils.say(f"   [IA] sortie structurée indisponible, 2e tentative… ({exc1})")

        # Tentative 2 — JSON simple (compatible SDK/modèles plus anciens).
        resp = client.messages.create(
            model=MODEL, max_tokens=4000,
            system=system + " Réponds UNIQUEMENT par un objet JSON valide conforme au "
                            "format demandé, sans texte ni balises autour.",
            messages=[{"role": "user", "content": user}],
        )
        txt = _text_of(resp)
        return _extract_json(txt) if txt else None
    except Exception as exc:  # clé invalide, quota, réseau…
        utils.say(f"   [IA] indisponible, repli déterministe : {exc}")
        return None
