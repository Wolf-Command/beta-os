#!/usr/bin/env python3
"""GM-SCORE — frozen God Mode register projection (Beta only).

Read-only projection of state/god-mode/GOD-MODE-REGISTER-2026-10-04.json.
Does not mutate tasks, states, or the register file.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
REGISTER_PATH = BETA_ROOT / "state" / "god-mode" / "GOD-MODE-REGISTER-2026-10-04.json"
SCHEMA = "wolf.god-mode-register-ro.v1"
PACK = "GM-SCORE"

IN_PROGRESS_STATES = frozenset(
    {"DESIGNED", "BUILT", "DEPLOYED", "REAL DATA", "ENGINEERING PROVED"}
)
COMPLETE_STATE = "HUMAN COMMISSIONED"
READY_STATE = "READY FOR HUMAN TEST"
BLOCKED_STATE = "BLOCKED EXTERNALLY"
NOT_STARTED_STATE = "NOT STARTED"


def register_path() -> Path:
    return REGISTER_PATH


def load_raw_register(path: Path | None = None) -> dict[str, Any]:
    p = path or REGISTER_PATH
    with p.open(encoding="utf-8") as fh:
        return json.load(fh)


def filter_bucket(state: str) -> str:
    st = str(state or "").strip()
    if st == COMPLETE_STATE:
        return "complete"
    if st == READY_STATE:
        return "ready_for_human_test"
    if st in IN_PROGRESS_STATES:
        return "in_progress"
    if st == BLOCKED_STATE:
        return "blocked_externally"
    if st == NOT_STARTED_STATE:
        return "not_started"
    if st == "DISCOVERED":
        return "discovered"
    return "other"


def load_god_mode_register(path: Path | None = None) -> dict[str, Any]:
    raw = load_raw_register(path)
    tasks = list(raw.get("tasks") or [])
    for t in tasks:
        t["filter_bucket"] = filter_bucket(t.get("state"))
    return {
        "ok": True,
        "pack": PACK,
        "schema": SCHEMA,
        "staff_ready": False,
        "human_commissioned": False,
        "frozen": bool(raw.get("frozen")),
        "frozen_at": raw.get("frozen_at"),
        "source": str(p if (p := (path or REGISTER_PATH)) else REGISTER_PATH),
        "headline": {
            "numerator_complete": raw.get("numerator_complete"),
            "denominator": raw.get("denominator"),
            "percent": raw.get("percent"),
            "movement_today": (raw.get("movement") or {}).get("today"),
        },
        "rollup": dict(raw.get("rollup") or {}),
        "movement": dict(raw.get("movement") or {}),
        "by_system": list(raw.get("by_system") or []),
        "tasks": tasks,
        "filter_vocab": {
            "complete": COMPLETE_STATE,
            "ready_for_human_test": READY_STATE,
            "in_progress": sorted(IN_PROGRESS_STATES),
            "blocked_externally": BLOCKED_STATE,
            "not_started": NOT_STARTED_STATE,
        },
    }
