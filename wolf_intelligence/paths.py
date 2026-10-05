"""Filesystem roots for Wolf Intelligence control plane (Beta only)."""
from __future__ import annotations

from pathlib import Path

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
PKG_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PKG_ROOT / "config"
UI_DIR = PKG_ROOT / "ui"

# Runtime store (gitignored). Canonical work state lives HERE — not in models/agents.
STATE_ROOT = BETA_ROOT / "state" / "wolf-intelligence"
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
BUILD_FACTORY_DIR = BETA_ROOT / "state" / "build-factory"
FACTORY_HISTORY_PATH = CONFIG_DIR / "factory-history-workers.json"

OWNER_UI_PORT = 8799
OWNER_UI_HOST = "127.0.0.1"

# Live provider calls stay off unless the process sets this to 1/true/yes/on.
LIVE_SUBMIT_ENV = "WOLF_INTELLIGENCE_LIVE_SUBMIT"
MAX_COST_ENV = "WOLF_INTELLIGENCE_MAX_COST_USD"
PROVIDER_MOCK_ENV = "WOLF_INTELLIGENCE_PROVIDER_MOCK"
# Owner UI writes require this bearer or session token. Unset → POST is refused.
UI_TOKEN_ENV = "WOLF_INTELLIGENCE_UI_TOKEN"


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
    ):
        d.mkdir(parents=True, exist_ok=True)
