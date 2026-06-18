"""
Système d'état partagé sur fichiers (le « tableau blanc » de l'agence).

Chaque mission (run) possède un dossier `state/runs/<run_id>/` contenant un
unique `state.json`. C'est le canal par lequel un agent transmet son travail
au suivant : chaque agent lit le `blackboard`, y écrit sa section, et le
Manager met à jour le statut des étapes.

Le format est volontairement simple et lisible (JSON) pour pouvoir être
inspecté à la main pendant ou après une mission.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import utils

# Ordre canonique du pipeline. Ajouter un agent ici (+ son module) suffit :
# le Manager itère sur cette liste, rien d'autre n'est à modifier.
PIPELINE = [
    ("scout", "🔍 Scout"),
    ("closer", "✍️  Closer"),
    ("strategist", "🎯 Strategist"),
    ("designer", "🎨 Designer"),
    ("copywriter", "🖊️  Copywriter"),
    ("builder", "💻 Builder"),
    ("inspector", "🔎 Inspector"),
    ("optimizer", "📈 Optimizer"),
    ("launcher", "🚀 Launcher"),
]


@dataclass
class Stage:
    name: str
    agent: str
    status: str = "pending"  # pending | running | passed | failed | skipped
    attempts: int = 0
    score: float | None = None
    notes: list = field(default_factory=list)
    started_at: str | None = None
    ended_at: str | None = None


@dataclass
class RunState:
    run_id: str
    created_at: str
    status: str = "created"  # created | running | delivered | aborted
    client: dict = field(default_factory=dict)
    blackboard: dict = field(default_factory=dict)
    stages: list = field(default_factory=list)
    log: list = field(default_factory=list)

    # ---- persistance --------------------------------------------------- #
    @property
    def dir(self) -> Path:
        return utils.RUNS_DIR / self.run_id

    @property
    def path(self) -> Path:
        return self.dir / "state.json"

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        utils.write_json_atomic(self.path, self.to_dict())

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "status": self.status,
            "client": self.client,
            "blackboard": self.blackboard,
            "stages": [asdict(s) if isinstance(s, Stage) else s for s in self.stages],
            "log": self.log,
        }

    # ---- journal ------------------------------------------------------- #
    def log_event(self, agent: str, message: str, level: str = "info") -> None:
        self.log.append(
            {"ts": utils.now_iso(), "agent": agent, "level": level, "message": message}
        )

    # ---- accès aux étapes ---------------------------------------------- #
    def stage(self, name: str) -> dict | None:
        for s in self.stages:
            if s["name"] == name:
                return s
        return None

    def set_stage(self, name: str, **fields) -> dict:
        s = self.stage(name)
        if s is None:
            s = {"name": name, "agent": name, "status": "pending", "attempts": 0,
                 "score": None, "notes": [], "started_at": None, "ended_at": None}
            self.stages.append(s)
        s.update(fields)
        return s

    # ---- tableau blanc ------------------------------------------------- #
    def put(self, key: str, value) -> None:
        self.blackboard[key] = value

    def get(self, key: str, default=None):
        return self.blackboard.get(key, default)


# --------------------------------------------------------------------------- #
# Fabrique & chargement
# --------------------------------------------------------------------------- #
def new_run(client: dict) -> RunState:
    utils.ensure_dirs()
    slug = utils.slugify(client.get("name", "client"))
    run_id = f"{slug}-{utils.stamp()}"
    run = RunState(run_id=run_id, created_at=utils.now_iso(), client=client)
    for name, _label in PIPELINE:
        run.set_stage(name, agent=name, status="pending")
    run.save()
    return run


def load_run(run_id: str) -> RunState:
    data = utils.read_json(utils.RUNS_DIR / run_id / "state.json")
    run = RunState(
        run_id=data["run_id"],
        created_at=data["created_at"],
        status=data.get("status", "created"),
        client=data.get("client", {}),
        blackboard=data.get("blackboard", {}),
        stages=data.get("stages", []),
        log=data.get("log", []),
    )
    return run


def latest_run() -> RunState | None:
    if not utils.RUNS_DIR.exists():
        return None
    runs = sorted(
        (p for p in utils.RUNS_DIR.iterdir() if (p / "state.json").exists()),
        key=lambda p: p.stat().st_mtime,
    )
    if not runs:
        return None
    return load_run(runs[-1].name)
