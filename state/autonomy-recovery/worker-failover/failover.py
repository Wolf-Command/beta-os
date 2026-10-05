#!/usr/bin/env python3
"""Worker failover: when Studio control path is DOWN, route repo-eligible work
to Cursor cloud agents (no Studio needed) with idempotency lock.

Canonical work item records reassignment. Duplicate execution prevented by lock.
Escalate to Matt only when auto recovery failed AND no safe alternative exists.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Makassar")

REPO_ELIGIBLE_KINDS = {
    "code_debug",
    "review",
    "security",
    "docs",
    "test",
    "repo_edit",
    "shadow_routing",
}

STUDIO_REQUIRED_KINDS = {
    "local_shell",
    "beta_reload",
    "prod_touch",  # never auto
    "daily_close",  # frozen / human
    "petty_cash",  # frozen / human
}


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


@dataclass
class WorkItem:
    id: str
    title: str
    kind: str
    status: str = "QUEUED"
    assigned_worker: Optional[str] = None
    preferred_worker: str = "studio_shell"
    repo_eligible: bool = False
    idempotency_key: Optional[str] = None
    failover_history: list | None = None
    lock_holder: Optional[str] = None
    lock_until: Optional[str] = None
    production_mutation: bool = False


class WorkStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"items": {}})

    def _read(self) -> dict:
        return json.loads(self.path.read_text())

    def _write(self, data: dict) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n")
        tmp.replace(self.path)

    def upsert(self, item: WorkItem) -> WorkItem:
        data = self._read()
        d = asdict(item)
        if d.get("failover_history") is None:
            d["failover_history"] = []
        data["items"][item.id] = d
        self._write(data)
        return item

    def get(self, wid: str) -> Optional[dict]:
        return self._read()["items"].get(wid)

    def try_acquire_lock(self, wid: str, holder: str) -> bool:
        data = self._read()
        item = data["items"].get(wid)
        if not item:
            return False
        if item.get("lock_holder") and item["lock_holder"] != holder:
            return False
        item["lock_holder"] = holder
        item["lock_until"] = now_iso()
        data["items"][wid] = item
        self._write(data)
        return True


class StudioProbe:
    """Returns control-path health. Box uses ListMachines-equivalent injection."""

    def __init__(self, connected: bool = False):
        self.connected = connected

    def studio_up(self) -> bool:
        return bool(self.connected)


def classify_repo_eligible(kind: str, production_mutation: bool = False) -> bool:
    if production_mutation:
        return False
    if kind in STUDIO_REQUIRED_KINDS:
        return False
    if kind in REPO_ELIGIBLE_KINDS:
        return True
    # default: treat generic code work as repo-eligible
    return kind not in STUDIO_REQUIRED_KINDS


class FailoverRouter:
    def __init__(self, store: WorkStore, probe: StudioProbe, audit_path: Path):
        self.store = store
        self.probe = probe
        self.audit_path = audit_path
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    def _audit(self, event: str, detail: dict) -> None:
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts_wita": now_iso(), "event": event, **detail}) + "\n")

    def assign(self, item: WorkItem) -> dict[str, Any]:
        item.repo_eligible = classify_repo_eligible(item.kind, item.production_mutation)
        if item.idempotency_key is None:
            item.idempotency_key = f"idem-{item.id}"

        # Idempotency: if already assigned+locked to a worker, do not reassign
        existing = self.store.get(item.id)
        if existing and existing.get("assigned_worker") and existing.get("lock_holder"):
            self._audit("duplicate_prevented", {"id": item.id, "holder": existing["lock_holder"]})
            return {
                "action": "NOOP_ALREADY_LOCKED",
                "assigned_worker": existing["assigned_worker"],
                "duplicate_prevented": True,
                "item": existing,
            }

        studio_up = self.probe.studio_up()
        if studio_up:
            worker = item.preferred_worker or "studio_shell"
            reason = "studio_control_path_up"
        elif item.repo_eligible:
            worker = "cursor_cloud_agent"
            reason = "studio_down_repo_eligible_failover"
        else:
            worker = None
            reason = "studio_down_not_repo_eligible_hold"
            item.status = "HELD_NEEDS_STUDIO"
            item.failover_history = (item.failover_history or []) + [
                {"at": now_iso(), "event": "hold", "reason": reason}
            ]
            self.store.upsert(item)
            self._audit("held_needs_studio", {"id": item.id, "kind": item.kind})
            human = True  # no safe alt for this item
            return {
                "action": "HOLD",
                "assigned_worker": None,
                "reason": reason,
                "escalate_human": human,
                "duplicate_prevented": False,
                "item": asdict(item),
            }

        item.assigned_worker = worker
        item.status = "ASSIGNED"
        item.failover_history = (item.failover_history or []) + [
            {"at": now_iso(), "event": "assign", "worker": worker, "reason": reason}
        ]
        self.store.upsert(item)
        got = self.store.try_acquire_lock(item.id, holder=f"{worker}:{item.idempotency_key}")
        self._audit(
            "assigned",
            {
                "id": item.id,
                "worker": worker,
                "reason": reason,
                "lock": got,
                "studio_up": studio_up,
            },
        )
        return {
            "action": "ASSIGN",
            "assigned_worker": worker,
            "reason": reason,
            "escalate_human": False,
            "duplicate_prevented": False,
            "lock_acquired": got,
            "item": self.store.get(item.id),
        }


def new_work_item(title: str, kind: str, **kwargs) -> WorkItem:
    return WorkItem(id=f"WI-{uuid.uuid4().hex[:12]}", title=title, kind=kind, **kwargs)
