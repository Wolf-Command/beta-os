"""Canonical work-item store. Models/agents do NOT own this state."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import events
from .paths import WORK_ITEMS_DIR, ensure_dirs

TZ = ZoneInfo("Asia/Makassar")
_lock = threading.Lock()

# Canonical lifecycle (Owner P0):
# QUEUED → ROUTING → RECOMMENDED → DISPATCHED_SHADOW → RUNNING →
# READY_TO_TEST | NEEDS_YOU | DECISION_PENDING | EXCEPTION →
# HUMAN_PASSED | BLOCKED | CANCELLED
STATES = (
    "QUEUED",
    "ROUTING",
    "RECOMMENDED",
    "DISPATCHED_SHADOW",
    "RUNNING",
    "READY_TO_TEST",
    "NEEDS_YOU",
    "DECISION_PENDING",
    "EXCEPTION",
    "HUMAN_PASSED",
    "BLOCKED",
    "CANCELLED",
)
TERMINAL = frozenset({"HUMAN_PASSED", "BLOCKED", "CANCELLED"})

TRANSITIONS: dict[str, frozenset[str]] = {
    "QUEUED": frozenset({"ROUTING", "CANCELLED", "BLOCKED"}),
    "ROUTING": frozenset({"RECOMMENDED", "EXCEPTION", "CANCELLED", "BLOCKED"}),
    "RECOMMENDED": frozenset({"DISPATCHED_SHADOW", "NEEDS_YOU", "DECISION_PENDING", "CANCELLED", "BLOCKED"}),
    "DISPATCHED_SHADOW": frozenset({"RUNNING", "EXCEPTION", "CANCELLED", "BLOCKED"}),
    "RUNNING": frozenset({"READY_TO_TEST", "NEEDS_YOU", "EXCEPTION", "BLOCKED", "CANCELLED"}),
    "READY_TO_TEST": frozenset({"HUMAN_PASSED", "NEEDS_YOU", "BLOCKED", "CANCELLED", "EXCEPTION"}),
    "NEEDS_YOU": frozenset({"DECISION_PENDING", "READY_TO_TEST", "HUMAN_PASSED", "BLOCKED", "CANCELLED"}),
    "DECISION_PENDING": frozenset({"HUMAN_PASSED", "BLOCKED", "CANCELLED", "NEEDS_YOU", "READY_TO_TEST"}),
    "EXCEPTION": frozenset({"NEEDS_YOU", "BLOCKED", "CANCELLED", "QUEUED"}),
    "HUMAN_PASSED": frozenset(),
    "BLOCKED": frozenset({"QUEUED", "CANCELLED"}),
    "CANCELLED": frozenset(),
}


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _path(wid: str) -> Path:
    return WORK_ITEMS_DIR / f"{wid}.json"


def create(
    *,
    title: str,
    kind: str = "generic",
    payload: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    isolated_safe: bool = True,
    allow_expensive: bool = False,
) -> dict[str, Any]:
    ensure_dirs()
    wid = f"wi_{uuid.uuid4().hex[:12]}"
    item = {
        "id": wid,
        "title": title,
        "kind": kind,
        "state": "QUEUED",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "payload": payload or {},
        "tags": tags or [],
        "isolated_safe": bool(isolated_safe),
        "allow_expensive": bool(allow_expensive),
        "recommendation": None,
        "scores": [],
        "dispatch": None,
        "result": None,
        "usage": None,
        "outcomes": [],
        "history": [{"at": now_iso(), "state": "QUEUED", "reason": "created"}],
    }
    with _lock:
        _path(wid).write_text(json.dumps(item, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    events.emit("work_item.created", {"title": title, "kind": kind, "state": "QUEUED"}, work_item_id=wid)
    return item


def get(wid: str) -> dict[str, Any] | None:
    p = _path(wid)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def list_items(*, state: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    ensure_dirs()
    items: list[dict[str, Any]] = []
    for p in sorted(WORK_ITEMS_DIR.glob("wi_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            item = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if state and item.get("state") != state:
            continue
        items.append(item)
        if len(items) >= limit:
            break
    return items


def transition(wid: str, new_state: str, *, reason: str = "", extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if new_state not in STATES:
        raise ValueError(f"unknown state: {new_state}")
    with _lock:
        item = get(wid)
        if not item:
            raise KeyError(wid)
        cur = item["state"]
        allowed = TRANSITIONS.get(cur, frozenset())
        if new_state not in allowed:
            raise ValueError(f"illegal transition {cur} → {new_state}")
        item["state"] = new_state
        item["updated_at"] = now_iso()
        hist = {"at": item["updated_at"], "state": new_state, "reason": reason or ""}
        if extra:
            hist["extra"] = extra
            for k, v in extra.items():
                if k in ("recommendation", "scores", "dispatch", "result", "usage"):
                    item[k] = v
        item.setdefault("history", []).append(hist)
        _path(wid).write_text(json.dumps(item, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    events.emit(
        "work_item.state_changed",
        {"from": cur, "to": new_state, "reason": reason},
        work_item_id=wid,
    )
    if new_state == "HUMAN_PASSED":
        events.emit("work_item.human_passed", {"reason": reason}, work_item_id=wid)
    elif new_state == "BLOCKED":
        events.emit("work_item.blocked", {"reason": reason}, work_item_id=wid)
    elif new_state == "CANCELLED":
        events.emit("work_item.cancelled", {"reason": reason}, work_item_id=wid)
    elif new_state == "EXCEPTION":
        events.emit("exception.raised", {"reason": reason}, work_item_id=wid)
    return item


def update_fields(wid: str, **fields: Any) -> dict[str, Any]:
    with _lock:
        item = get(wid)
        if not item:
            raise KeyError(wid)
        for k, v in fields.items():
            if k in ("id", "created_at", "state"):
                continue
            item[k] = v
        item["updated_at"] = now_iso()
        _path(wid).write_text(json.dumps(item, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return item


def by_ui_bucket() -> dict[str, list[dict[str, Any]]]:
    """Owner UI buckets: NEEDS YOU / READY TO TEST / DECISIONS / EXCEPTIONS / RUNNING."""
    buckets = {
        "NEEDS_YOU": [],
        "READY_TO_TEST": [],
        "DECISIONS": [],
        "EXCEPTIONS": [],
        "RUNNING": [],
    }
    for item in list_items(limit=500):
        s = item.get("state")
        if s == "NEEDS_YOU":
            buckets["NEEDS_YOU"].append(item)
        elif s == "READY_TO_TEST":
            buckets["READY_TO_TEST"].append(item)
        elif s == "DECISION_PENDING":
            buckets["DECISIONS"].append(item)
        elif s == "EXCEPTION":
            buckets["EXCEPTIONS"].append(item)
        elif s in ("RUNNING", "DISPATCHED_SHADOW", "ROUTING", "RECOMMENDED"):
            buckets["RUNNING"].append(item)
    return buckets
