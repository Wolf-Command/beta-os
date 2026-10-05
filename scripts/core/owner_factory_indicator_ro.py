#!/usr/bin/env python3
"""OWNER-HOME-FACTORY-INDICATOR — read-only God Mode dispatch projection (Beta only).

Projects counts from state/build-factory/GOD-MODE-DISPATCH.json and, when present,
WRITER.lock for live worker truth. Does not mutate queue or lock files.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
BF = BETA_ROOT / "state" / "build-factory"
DISPATCH_PATH = BF / "GOD-MODE-DISPATCH.json"
LOCK_PATH = BF / "WRITER.lock"
SCHEMA = "wolf.owner-factory-indicator-ro.v1"
PACK = "OWNER-HOME-FACTORY-INDICATOR"

STATE_READY = "READY"
STATE_RUNNING = "RUNNING"
STATE_BLOCKED = "BLOCKED"
STATE_HUMAN = "READY FOR HUMAN TEST"


def dispatch_path() -> Path:
    return DISPATCH_PATH


def _pid_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _count_active_workers(items: list[dict[str, Any]], lock: dict[str, Any] | None) -> int:
    """At most one live beta cursor runs; prefer lock truth, then RUNNING item pids."""
    if lock and lock.get("state") == STATE_RUNNING:
        pid = lock.get("cursor_pid") or lock.get("wrapper_pid")
        if _pid_alive(pid):
            return 1
    alive = 0
    for item in items:
        if item.get("state") != STATE_RUNNING:
            continue
        if _pid_alive(item.get("cursor_pid")) or _pid_alive(item.get("wrapper_pid")):
            alive += 1
    return alive


def _format_ts(value: Any) -> str:
    if value is None or value == "":
        return "none yet"
    return str(value)


def load_factory_indicator(
    *,
    dispatch_file: Path | None = None,
    lock_file: Path | None = None,
) -> dict[str, Any]:
    dpath = dispatch_file or DISPATCH_PATH
    lpath = lock_file or LOCK_PATH
    queue = _read_json(dpath) or {}
    lock = _read_json(lpath)
    items = [it for it in (queue.get("items") or []) if isinstance(it, dict)]

    ready_count = sum(1 for it in items if it.get("state") == STATE_READY)
    blocked_count = sum(1 for it in items if it.get("state") == STATE_BLOCKED)
    human_count = sum(1 for it in items if it.get("state") == STATE_HUMAN)
    active_workers = _count_active_workers(items, lock)

    last_completion = queue.get("last_completion_at")
    last_dispatch = queue.get("last_autonomous_dispatch_at")

    line = (
        f"Factory · {active_workers} worker{'s' if active_workers != 1 else ''} · "
        f"{ready_count} ready · {blocked_count} blocked · "
        f"{human_count} for your test · "
        f"last done {_format_ts(last_completion)} · "
        f"last dispatch {_format_ts(last_dispatch)}"
    )

    return {
        "ok": True,
        "pack": PACK,
        "schema": SCHEMA,
        "staff_ready": False,
        "human_commissioned": False,
        "eng_proved": False,
        "read_only": True,
        "source": str(dpath),
        "active_workers": active_workers,
        "ready_queue_count": ready_count,
        "blocked_count": blocked_count,
        "ready_for_human_test_count": human_count,
        "last_completion_at": last_completion,
        "last_autonomous_dispatch_at": last_dispatch,
        "line": line,
        "queue_missing": not dpath.is_file(),
    }
