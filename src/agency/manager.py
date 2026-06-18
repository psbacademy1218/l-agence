"""
🧭 Manager — l'orchestrateur.

Responsabilités :
  • découpe la mission en étapes (le PIPELINE) ;
  • assigne chaque étape à l'agent compétent ;
  • applique des CRITÈRES D'ACCEPTATION explicites par étape ;
  • gère les erreurs et relance (retries) avec back-off logique ;
  • orchestre la BOUCLE QA : si l'Inspector pose son veto, le Manager
    renvoie le travail aux agents concernés puis re-teste, jusqu'à
    validation ou épuisement des tentatives ;
  • tranche : livraison, ou abandon argumenté.

Le Manager ne contient AUCUNE logique métier d'agent : il ne connaît que le
contrat `AgentResult`. On peut donc ajouter un agent sans le modifier.
"""
from __future__ import annotations

import importlib

from . import personas, utils
from .agents.base import AgentResult
from .state import PIPELINE, RunState

# --------------------------------------------------------------------------- #
# Politique d'orchestration : critères d'acceptation par étape.
#   min_score      : qualité minimale pour valider l'étape
#   max_attempts   : nombre de tentatives avant échec
#   blocking       : un échec définitif interrompt-il la mission ?
# --------------------------------------------------------------------------- #
POLICY: dict[str, dict] = {
    "scout":      {"min_score": 60, "max_attempts": 2, "blocking": True},
    "hunter":     {"min_score": 50, "max_attempts": 1, "blocking": False},
    "chercheur":  {"min_score": 50, "max_attempts": 1, "blocking": False},
    "closer":     {"min_score": 70, "max_attempts": 3, "blocking": True},
    "strategist": {"min_score": 70, "max_attempts": 2, "blocking": True},
    "positionneur": {"min_score": 50, "max_attempts": 1, "blocking": False},
    "designer":   {"min_score": 70, "max_attempts": 3, "blocking": True},
    "illustrateur": {"min_score": 50, "max_attempts": 1, "blocking": False},
    "copywriter": {"min_score": 70, "max_attempts": 3, "blocking": True},
    "relecteur":  {"min_score": 50, "max_attempts": 1, "blocking": False},
    "builder":    {"min_score": 70, "max_attempts": 3, "blocking": True},
    "inspector":  {"min_score": 85, "max_attempts": 1, "blocking": True},
    "optimizer":  {"min_score": 75, "max_attempts": 2, "blocking": True},
    "launcher":   {"min_score": 80, "max_attempts": 2, "blocking": True},
    "referenceur": {"min_score": 50, "max_attempts": 1, "blocking": False},
    "publicitaire": {"min_score": 50, "max_attempts": 1, "blocking": False},
    "social":     {"min_score": 50, "max_attempts": 1, "blocking": False},
    "automatiseur": {"min_score": 50, "max_attempts": 1, "blocking": False},
}

# Boucle QA : si l'Inspector refuse, qui re-travaille, et combien de tours max.
QA_MAX_ROUNDS = 3


class Manager:
    def __init__(self, run: RunState):
        self.run = run
        self.persona = personas.load_persona("manager")

    # ------------------------------------------------------------------ #
    # Helpers de présentation
    # ------------------------------------------------------------------ #
    def announce(self, message: str) -> None:
        utils.say(f"\n🧭 Manager — {message}")
        self.run.log_event("manager", message)

    def _agent_module(self, name: str):
        return importlib.import_module(f"agency.agents.{name}")

    # ------------------------------------------------------------------ #
    # Exécution d'une étape unique, avec retries et critère d'acceptation
    # ------------------------------------------------------------------ #
    def run_stage(self, name: str, issues: list | None = None) -> AgentResult:
        policy = POLICY[name]
        module = self._agent_module(name)
        p = personas.load_persona(name)
        issues = issues or []

        self.run.set_stage(name, status="running", started_at=utils.now_iso())
        last: AgentResult = AgentResult(ok=False, summary="non exécuté")

        for attempt in range(1, policy["max_attempts"] + 1):
            stage = self.run.set_stage(name, attempts=attempt)
            if attempt > 1:
                utils.say(f"   ↻ Manager relance {p.emoji} {p.name} "
                          f"(tentative {attempt}/{policy['max_attempts']})")
            try:
                last = module.run(self.run, attempt=attempt, issues=issues)
            except Exception as exc:  # robustesse : un agent qui plante = échec géré
                last = AgentResult(ok=False, score=0,
                                   summary=f"exception : {exc}", issues=[str(exc)])
                self.run.log_event(name, f"EXCEPTION {exc}", level="error")

            accepted = last.ok and last.score >= policy["min_score"]
            stage.update(score=last.score,
                         notes=(last.issues or []) + ([last.summary] if last.summary else []))
            self.run.save()

            if accepted:
                self.run.set_stage(name, status="passed", ended_at=utils.now_iso())
                utils.say(f"   ✅ {p.emoji} {p.name} validé "
                          f"(score {last.score:.0f}/100 ≥ {policy['min_score']})")
                self.run.save()
                return last

            issues = last.issues or [last.summary]
            utils.say(f"   ⚠️  {p.emoji} {p.name} non validé "
                      f"(score {last.score:.0f} < {policy['min_score']}) : "
                      f"{'; '.join(issues[:3])}")

        # Toutes les tentatives ont échoué
        self.run.set_stage(name, status="failed", ended_at=utils.now_iso())
        self.run.save()
        return last

    # ------------------------------------------------------------------ #
    # Boucle QA dédiée autour de l'Inspector
    # ------------------------------------------------------------------ #
    def quality_loop(self) -> AgentResult:
        self.announce("Passage en contrôle qualité (Inspector a droit de veto).")
        result = self.run_stage("inspector")

        rounds = 0
        while not (result.ok and result.score >= POLICY["inspector"]["min_score"]):
            rounds += 1
            if rounds > QA_MAX_ROUNDS:
                self.announce("Boucle QA épuisée — escalade nécessaire. ⛔")
                return result
            targets = result.rework or ["builder"]
            utils.say(f"\n   🔁 Tour QA {rounds}/{QA_MAX_ROUNDS} — "
                      f"l'Inspector renvoie vers : {', '.join(targets)}")
            # Les agents de contenu/DA corrigent d'abord le tableau blanc…
            for tgt in (t for t in targets if t != "builder"):
                self.run_stage(tgt, issues=result.issues)
            # …puis le Builder RECONSTRUIT systématiquement, pour que le fichier
            # inspecté reflète bien les correctifs (sinon l'Inspector relit du périmé).
            self.run_stage("builder", issues=result.issues)
            result = self.run_stage("inspector", issues=result.issues)

        self.announce("Contrôle qualité validé. Aucun rendu générique détecté. ✅")
        return result

    # ------------------------------------------------------------------ #
    # Orchestration de bout en bout
    # ------------------------------------------------------------------ #
    def deliver(self) -> bool:
        """Déroule tout le pipeline. Retourne True si le site est livré."""
        self.run.status = "running"
        self.run.save()

        self.announce(
            f"Nouvelle mission « {self.run.client.get('name')} ». "
            f"Je découpe en {len(PIPELINE)} étapes et j'assigne l'équipe.")

        # 1) Prospection (audit approfondi + qualification + recherche client)
        if not self._must_pass("scout"):
            return self._abort("Audit prospect impossible.")
        self.run_stage("hunter")       # qualification commerciale (non bloquant)
        self.run_stage("chercheur")    # recherche client (non bloquant)

        # 2) Outreach (brouillon d'email — jamais envoyé)
        if not self._must_pass("closer"):
            return self._abort("Rédaction de l'approche impossible.")

        # 3) Porte d'acceptation : on ne produit QUE si le prospect a accepté
        if not self.run.client.get("accepted"):
            self.announce(
                "Brouillon d'email prêt. En attente de la réponse du prospect — "
                "AUCUN envoi automatique (conformité RGPD/CAN-SPAM). "
                "La production démarrera à l'acceptation.")
            self.run.status = "awaiting_reply"
            self.run.save()
            return True
        self.announce("✱ Le prospect a accepté la proposition. Lancement de la production.")

        # 4) Cadrage + positionnement
        if not self._must_pass("strategist"):
            return self._abort("Cadrage en échec.")
        self.run_stage("positionneur")     # angle / promesse (non bloquant)

        # 5) Création (DA + visuels + contenu + relecture)
        if not self._must_pass("designer"):
            return self._abort("Direction artistique en échec.")
        self.run_stage("illustrateur")     # brief visuel (non bloquant)
        if not self._must_pass("copywriter"):
            return self._abort("Rédaction du contenu en échec.")
        self.run_stage("relecteur")        # relecture (non bloquant)

        # 6) Construction
        if not self._must_pass("builder"):
            return self._abort("Construction du site en échec.")

        # 7) Boucle QA (Inspector + reprises)
        qa = self.quality_loop()
        if not (qa.ok and qa.score >= POLICY["inspector"]["min_score"]):
            return self._abort("Le site n'a pas franchi le contrôle qualité.")

        # 8) Optimisation (SEO technique, sitemap, données structurées, tracking)
        if not self._must_pass("optimizer"):
            return self._abort("Optimisation en échec.")

        # 9) Lancement (build + déploiement local + vérification)
        if not self._must_pass("launcher"):
            return self._abort("Déploiement en échec.")

        # 10) Croissance — livrables post-lancement (non bloquants)
        self.announce("Le site est en ligne. L'équipe croissance prépare les livrables.")
        for stage in ("referenceur", "publicitaire", "social", "automatiseur"):
            self.run_stage(stage)

        self.run.status = "delivered"
        self.run.save()
        deploy = self.run.get("deploy", {})
        self.announce(
            f"Mission livrée. 🎉 Site servi en local : {deploy.get('url', '?')}")
        return True

    # ------------------------------------------------------------------ #
    def _must_pass(self, name: str) -> bool:
        result = self.run_stage(name)
        ok = result.ok and result.score >= POLICY[name]["min_score"]
        return ok or not POLICY[name]["blocking"]

    def _abort(self, reason: str) -> bool:
        self.run.status = "aborted"
        self.run.save()
        self.announce(f"Mission interrompue : {reason} ⛔")
        return False
