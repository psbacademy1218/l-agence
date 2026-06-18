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


def _extract_json(text: str):
    text = (text or "").strip()
    if text.startswith("```"):                       # enlève les ```json … ```
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    a, b = text.find("["), text.rfind("]")           # objet OU tableau
    o, c = text.find("{"), text.rfind("}")
    if a != -1 and b > a and (o == -1 or a < o):
        text = text[a:b + 1]
    elif o != -1 and c > o:
        text = text[o:c + 1]
    return json.loads(text)


def websearch_json(agent_key: str, task: str, max_tokens: int = 4000):
    """Recherche web réelle (outil web_search) + sortie JSON. Pour trouver de
    vraies entités (entreprises…) depuis le cloud, là où Overpass est bloqué."""
    if not available() or os.environ.get("AGENCY_WEB_SEARCH", "1") not in ("1", "true", "True"):
        return None
    try:
        import anthropic
        client = anthropic.Anthropic()
        system = (_persona_prompt(agent_key) + "\n\nUtilise la recherche web pour des "
                  "informations RÉELLES et à jour. Termine par le JSON demandé, sans texte autour.")
        msgs = [{"role": "user", "content": task}]
        tools = [{"type": "web_search_20260209", "name": "web_search"}]
        resp = None
        for _ in range(4):
            resp = client.messages.create(model=MODEL, max_tokens=max_tokens,
                                          system=system, messages=msgs, tools=tools)
            if getattr(resp, "stop_reason", "") == "pause_turn":
                msgs.append({"role": "assistant", "content": resp.content})
                continue
            break
        txt = "".join(getattr(b, "text", "") for b in resp.content
                      if getattr(b, "type", "") == "text")
        return _extract_json(txt) if txt else None
    except Exception as exc:
        utils.say(f"   [IA:{agent_key}] recherche+JSON KO : {exc}")
        return None


def _text_of(resp) -> str:
    return next((b.text for b in resp.content if getattr(b, "type", "") == "text"), "")


_FORMAT_RULES = (
    "\n\nRÈGLES DE SORTIE : réponds UNIQUEMENT par un JSON valide conforme au schéma "
    "demandé. Français impeccable, concret, incarné, crédible pour CE client précis. "
    "Bannis absolument : lorem ipsum, « bienvenue sur notre site », superlatifs creux, "
    "jargon, anglicismes inutiles, tournures passe-partout.")


def _persona_prompt(agent_key: str) -> str:
    try:
        from . import personas
        return personas.load_persona(agent_key).system_prompt
    except Exception:
        return ""


def agent_json(agent_key: str, task: str, schema: dict, *,
               thinking: bool = False, effort: str = "medium",
               max_tokens: int = 8000) -> dict | None:
    """Fait travailler un agent via Claude, en utilisant SA fiche persona comme
    prompt système. Retourne un dict JSON ou None (repli déterministe)."""
    if not available():
        return None
    system = _persona_prompt(agent_key) + _FORMAT_RULES
    try:
        import anthropic
        client = anthropic.Anthropic()
        kwargs = dict(model=MODEL, max_tokens=max_tokens, system=system,
                      messages=[{"role": "user", "content": task}],
                      output_config={"effort": effort,
                                     "format": {"type": "json_schema", "schema": schema}})
        if thinking:
            kwargs["thinking"] = {"type": "adaptive"}
        resp = client.messages.create(**kwargs)
        txt = _text_of(resp)
        if txt:
            return _extract_json(txt)
    except Exception as exc1:
        utils.say(f"   [IA:{agent_key}] sortie structurée KO, 2e essai ({exc1})")
    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=MODEL, max_tokens=min(4000, max_tokens),
            system=system + " Réponds uniquement par un objet JSON valide, sans texte autour.",
            messages=[{"role": "user", "content": task}])
        txt = _text_of(resp)
        return _extract_json(txt) if txt else None
    except Exception as exc:
        utils.say(f"   [IA:{agent_key}] indisponible : {exc}")
        return None


def agent_research(agent_key: str, query: str, max_tokens: int = 3500) -> str:
    """Recherche web réelle (outil web_search de Claude). Retourne un brief texte
    (vide si indisponible). Activable/désactivable via AGENCY_WEB_SEARCH."""
    if not available() or os.environ.get("AGENCY_WEB_SEARCH", "1") not in ("1", "true", "True"):
        return ""
    try:
        import anthropic
        client = anthropic.Anthropic()
        system = _persona_prompt(agent_key) + ("\n\nUtilise la recherche web pour des faits "
            "récents et locaux. Termine par une synthèse factuelle en français (puces).")
        msgs = [{"role": "user", "content": query}]
        tools = [{"type": "web_search_20260209", "name": "web_search"}]
        resp = None
        for _ in range(3):  # gère les pause_turn de l'outil serveur
            resp = client.messages.create(model=MODEL, max_tokens=max_tokens,
                                          system=system, messages=msgs, tools=tools)
            if getattr(resp, "stop_reason", "") == "pause_turn":
                msgs.append({"role": "assistant", "content": resp.content})
                continue
            break
        text = "".join(getattr(b, "text", "") for b in resp.content
                       if getattr(b, "type", "") == "text")
        return text[:2200]
    except Exception as exc:
        utils.say(f"   [IA:{agent_key}] recherche web KO : {exc}")
        return ""


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
