"""Filesystem roots for Wolf Intelligence control plane (Beta only)."""
from __future__ import annotations

import os
from pathlib import Path

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
PKG_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PKG_ROOT / "config"
UI_DIR = PKG_ROOT / "ui"

# Runtime store (gitignored). Canonical work state lives HERE — not in models/agents.
# WOLF_INTELLIGENCE_STATE_ROOT overrides it (tests always point it at a temp dir).
STATE_ROOT_ENV = "WOLF_INTELLIGENCE_STATE_ROOT"
LIVE_STATE_ROOT = BETA_ROOT / "state" / "wolf-intelligence"


def _state_root() -> Path:
    raw = os.environ.get(STATE_ROOT_ENV, "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return LIVE_STATE_ROOT


def rebind_state_paths() -> None:
    """Recompute module-level paths after WOLF_INTELLIGENCE_STATE_ROOT changes."""
    global STATE_ROOT, WORK_ITEMS_DIR, EVENTS_PATH, AUDIT_DIR, LEDGER_DIR
    global BENCHMARKS_DIR, LEARNING_DIR, SHADOW_DIR, WORKERS_DIR, TMP_DIR
    global SQLITE_PATH, SCORECARD_PATH, WORKER_STATUS_PATH, SHADOW_COMPARE_PATH
    global MIRROR_DIR, GOVERNANCE_DIR, GOVERNANCE_AUDIT_PATH
    global GOVERNANCE_DISPATCH_LEDGER_PATH, GOVERNANCE_CAPACITY_OBSERVATIONS_PATH
    global GOVERNANCE_TIGHTENING_PATH

    root = _state_root()
    STATE_ROOT = root
    WORK_ITEMS_DIR = STATE_ROOT / "work_items"
    EVENTS_PATH = STATE_ROOT / "events" / "events.jsonl"
    AUDIT_DIR = STATE_ROOT / "audit"
    LEDGER_DIR = STATE_ROOT / "ledger"
    BENCHMARKS_DIR = STATE_ROOT / "benchmarks"
    LEARNING_DIR = STATE_ROOT / "learning"
    SHADOW_DIR = STATE_ROOT / "shadow"
    WORKERS_DIR = STATE_ROOT / "workers"
    TMP_DIR = STATE_ROOT / "tmp"
    SQLITE_PATH = STATE_ROOT / "control_plane.sqlite"
    SCORECARD_PATH = STATE_ROOT / "benchmarks" / "model-scorecard.json"
    WORKER_STATUS_PATH = STATE_ROOT / "workers" / "status.json"
    SHADOW_COMPARE_PATH = STATE_ROOT / "shadow" / "compare.jsonl"
    MIRROR_DIR = STATE_ROOT / "mirror"
    GOVERNANCE_DIR = STATE_ROOT / "governance"
    GOVERNANCE_AUDIT_PATH = GOVERNANCE_DIR / "audit.jsonl"
    GOVERNANCE_DISPATCH_LEDGER_PATH = GOVERNANCE_DIR / "dispatch-ledger.jsonl"
    GOVERNANCE_CAPACITY_OBSERVATIONS_PATH = GOVERNANCE_DIR / "capacity-observations.jsonl"
    GOVERNANCE_TIGHTENING_PATH = GOVERNANCE_DIR / "tightening.json"
    _propagate_state_paths()


def _propagate_state_paths() -> None:
    """Re-sync modules that cached path constants before STATE_ROOT was isolated."""
    import sys

    mod = sys.modules.get(__name__)
    if mod is None:
        return

    def _set(target: str, attr: str, value) -> None:
        loaded = sys.modules.get(target)
        if loaded is not None:
            setattr(loaded, attr, value)

    for name in ("EVENTS_PATH", "AUDIT_DIR", "LEDGER_DIR", "SQLITE_PATH", "WORK_ITEMS_DIR", "GOVERNANCE_DIR",
                 "GOVERNANCE_AUDIT_PATH", "GOVERNANCE_DISPATCH_LEDGER_PATH",
                 "GOVERNANCE_CAPACITY_OBSERVATIONS_PATH", "GOVERNANCE_TIGHTENING_PATH"):
        if hasattr(mod, name):
            val = getattr(mod, name)
            for target in (
                "wolf_intelligence.events",
                "wolf_intelligence.work_items",
                "wolf_intelligence.owner_ui_server",
                "wolf_intelligence.overnight_tick",
                "wolf_intelligence.accept_phase1",
                "wolf_intelligence.governance",
                "wolf_intelligence.allocation",
                "wolf_intelligence.capacity",
                "wolf_intelligence.imbalance",
                "wolf_intelligence.failover",
            ):
                _set(target, name, val)

    _set("wolf_intelligence.learning", "LEARNING_DIR", LEARNING_DIR)
    learning = sys.modules.get("wolf_intelligence.learning")
    if learning is not None:
        learning.OUTCOMES_PATH = LEARNING_DIR / "outcomes.jsonl"
        learning.WEIGHTS_PATH = LEARNING_DIR / "weights.json"

    ledger = sys.modules.get("wolf_intelligence.ledger")
    if ledger is not None:
        ledger.LEDGER_PATH = LEDGER_DIR / "ledger.jsonl"
        ledger.SNAPSHOT_PATH = LEDGER_DIR / "snapshot.json"

    stats = sys.modules.get("wolf_intelligence.stats_store")
    if stats is not None:
        stats.STATS_PATH = LEARNING_DIR / "stats.json"
        stats.SUMMARY_PATH = mirror_path("stats-summary.json")


rebind_state_paths()
BUILD_FACTORY_DIR = BETA_ROOT / "state" / "build-factory"
FACTORY_HISTORY_PATH = CONFIG_DIR / "factory-history-workers.json"

OWNER_UI_HOST = "127.0.0.1"
UI_PORT_ENV = "WOLF_INTELLIGENCE_UI_PORT"
FORBIDDEN_UI_PORTS = frozenset({8787, 8788})


def owner_ui_port() -> int:
    """Owner UI listen port. Refuses 8787 and 8788 (production default 8799)."""
    raw = os.environ.get(UI_PORT_ENV, "8799").strip()
    try:
        port = int(raw)
    except ValueError:
        raise ValueError(f"invalid {UI_PORT_ENV}: {raw!r}")
    if port in FORBIDDEN_UI_PORTS:
        raise ValueError(f"refusing forbidden Owner UI port {port}")
    return port


# Back-compat alias; prefer owner_ui_port() at runtime (tests override via env).
OWNER_UI_PORT = owner_ui_port() if UI_PORT_ENV in os.environ else 8799

# Live provider calls stay off unless the process sets this to 1/true/yes/on.
LIVE_SUBMIT_ENV = "WOLF_INTELLIGENCE_LIVE_SUBMIT"
MAX_COST_ENV = "WOLF_INTELLIGENCE_MAX_COST_USD"
PROVIDER_MOCK_ENV = "WOLF_INTELLIGENCE_PROVIDER_MOCK"
# Owner UI writes require this bearer or session token. Unset → POST is refused.
UI_TOKEN_ENV = "WOLF_INTELLIGENCE_UI_TOKEN"
# Set to 1 to also rewrite the tracked config/ copies (commit-time refresh only).
CONFIG_MIRROR_ENV = "WOLF_INTELLIGENCE_CONFIG_MIRROR"


def mirror_path(name: str) -> Path:
    """Where a generated summary is written. Runtime writes stay out of the git tree."""
    if os.environ.get(CONFIG_MIRROR_ENV, "").strip().lower() in {"1", "true", "yes", "on"}:
        return CONFIG_DIR / name
    return MIRROR_DIR / name


def mirror_read_path(name: str) -> Path:
    """Read the runtime copy when it exists, else the committed config/ copy."""
    runtime = MIRROR_DIR / name
    return runtime if runtime.exists() else CONFIG_DIR / name


def ensure_dirs() -> None:
    for d in (
        WORK_ITEMS_DIR,
        EVENTS_PATH.parent,
        AUDIT_DIR,
        LEDGER_DIR,
        BENCHMARKS_DIR,
        LEARNING_DIR,
        SHADOW_DIR,
        WORKERS_DIR,
        TMP_DIR,
        MIRROR_DIR,
        GOVERNANCE_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)
