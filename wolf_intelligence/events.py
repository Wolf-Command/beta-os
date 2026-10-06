"""Canonical event bus (append-only JSONL). Owner-listed control-plane events."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .paths import AUDIT_DIR, EVENTS_PATH, ensure_dirs

TZ = ZoneInfo("Asia/Makassar")
_lock = threading.Lock()

# Owner canonical events for Wolf Intelligence control plane.
CANONICAL_EVENTS = frozenset(
    {
        "work_item.created",
        "work_item.state_changed",
        "work_item.cancelled",
        "work_item.blocked",
        "work_item.human_passed",
        "routing.scored",
        "routing.recommended",
        "dispatch.shadow_submitted",
        "dispatch.shadow_completed",
        "dispatch.shadow_failed",
        "dispatch.shadow_skipped_expensive",
        "worker.health_checked",
        "worker.status_reported",
        "usage.recorded",
        "capacity.updated",
        "capacity.exhausted",
        "outcome.recorded",
        "outcome.human_override",
        "exception.raised",
        "learning.updated",
        "benchmark.started",
        "benchmark.completed",
        "shadow.compare_recorded",
        "ui.owner_viewed",
        "audit.secret_scan",
        # Grok work bridge (claim/lease protocol). Authoritative audit lives in grok_bridge_audit.
        "grok_bridge.offered",
        "grok_bridge.claimed",
        "grok_bridge.renewed",
        "grok_bridge.completed",
        "grok_bridge.failed",
        "grok_bridge.released",
        "grok_bridge.reassign_flagged",
        "grok_bridge.doorbell_rung",
        "grok_bridge.doorbell_failed",
        "grok_bridge.doorbell_closed",
        "grok_bridge.audit_chain_broken",
    }
)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def emit(event_type: str, payload: dict[str, Any] | None = None, *, work_item_id: str | None = None) -> dict[str, Any]:
    if event_type not in CANONICAL_EVENTS:
        raise ValueError(f"non-canonical event: {event_type}")
    ensure_dirs()
    record = {
        "event_id": f"evt_{uuid.uuid4().hex[:16]}",
        "type": event_type,
        "at": now_iso(),
        "work_item_id": work_item_id,
        "payload": payload or {},
    }
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with _lock:
        with EVENTS_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        # Mirror to dated audit file for forensics
        day = datetime.now(TZ).strftime("%Y%m%d")
        audit = AUDIT_DIR / f"events-{day}.jsonl"
        with audit.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    return record


def read_events(*, work_item_id: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    ensure_dirs()
    if not EVENTS_PATH.exists():
        return []
    out: list[dict[str, Any]] = []
    with EVENTS_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if work_item_id and rec.get("work_item_id") != work_item_id:
                continue
            out.append(rec)
    return out[-limit:]
