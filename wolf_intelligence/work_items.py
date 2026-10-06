"""Canonical work-item store (SQLite primary + JSON mirror). Models/agents do NOT own this state."""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import events
from .paths import SQLITE_PATH, WORK_ITEMS_DIR, ensure_dirs

TZ = ZoneInfo("Asia/Makassar")
_lock = threading.Lock()

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


def _connect() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(str(SQLITE_PATH), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS work_items (
          id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          kind TEXT NOT NULL,
          state TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          isolated_safe INTEGER NOT NULL DEFAULT 1,
          allow_expensive INTEGER NOT NULL DEFAULT 0,
          payload_json TEXT NOT NULL DEFAULT '{}',
          tags_json TEXT NOT NULL DEFAULT '[]',
          recommendation_json TEXT,
          scores_json TEXT,
          dispatch_json TEXT,
          result_json TEXT,
          usage_json TEXT,
          outcomes_json TEXT NOT NULL DEFAULT '[]',
          history_json TEXT NOT NULL DEFAULT '[]'
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_work_items_state ON work_items(state)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_work_items_updated ON work_items(updated_at)")
    conn.commit()


def _row_to_item(row: sqlite3.Row) -> dict[str, Any]:
    def loads(v: str | None, default: Any) -> Any:
        if v is None or v == "":
            return default
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return default

    return {
        "id": row["id"],
        "title": row["title"],
        "kind": row["kind"],
        "state": row["state"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "isolated_safe": bool(row["isolated_safe"]),
        "allow_expensive": bool(row["allow_expensive"]),
        "payload": loads(row["payload_json"], {}),
        "tags": loads(row["tags_json"], []),
        "recommendation": loads(row["recommendation_json"], None),
        "scores": loads(row["scores_json"], []),
        "dispatch": loads(row["dispatch_json"], None),
        "result": loads(row["result_json"], None),
        "usage": loads(row["usage_json"], None),
        "outcomes": loads(row["outcomes_json"], []),
        "history": loads(row["history_json"], []),
    }


def _mirror_json(item: dict[str, Any]) -> None:
    """JSON mirror for humans/debugging — SQLite is canonical."""
    ensure_dirs()
    path = WORK_ITEMS_DIR / f"{item['id']}.json"
    path.write_text(json.dumps(item, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _migrate_json_files(conn: sqlite3.Connection) -> int:
    """One-time import of any pre-SQLite JSON work items."""
    n = 0
    for p in WORK_ITEMS_DIR.glob("wi_*.json"):
        try:
            item = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        wid = item.get("id")
        if not wid:
            continue
        existing = conn.execute("SELECT 1 FROM work_items WHERE id=?", (wid,)).fetchone()
        if existing:
            continue
        conn.execute(
            """
            INSERT INTO work_items (
              id, title, kind, state, created_at, updated_at, isolated_safe, allow_expensive,
              payload_json, tags_json, recommendation_json, scores_json, dispatch_json,
              result_json, usage_json, outcomes_json, history_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                wid,
                item.get("title") or wid,
                item.get("kind") or "generic",
                item.get("state") or "QUEUED",
                item.get("created_at") or now_iso(),
                item.get("updated_at") or now_iso(),
                1 if item.get("isolated_safe", True) else 0,
                1 if item.get("allow_expensive") else 0,
                json.dumps(item.get("payload") or {}),
                json.dumps(item.get("tags") or []),
                json.dumps(item.get("recommendation")) if item.get("recommendation") is not None else None,
                json.dumps(item.get("scores") or []),
                json.dumps(item.get("dispatch")) if item.get("dispatch") is not None else None,
                json.dumps(item.get("result")) if item.get("result") is not None else None,
                json.dumps(item.get("usage")) if item.get("usage") is not None else None,
                json.dumps(item.get("outcomes") or []),
                json.dumps(item.get("history") or []),
            ),
        )
        n += 1
    if n:
        conn.commit()
    return n


_bootstrapped = False


def bootstrap() -> dict[str, Any]:
    global _bootstrapped
    with _lock:
        conn = _connect()
        try:
            _init_schema(conn)
            migrated = _migrate_json_files(conn)
            count = conn.execute("SELECT COUNT(*) AS n FROM work_items").fetchone()["n"]
            _bootstrapped = True
            return {"sqlite": str(SQLITE_PATH), "migrated_json": migrated, "count": count}
        finally:
            conn.close()


def store_info() -> dict[str, Any]:
    ensure_dirs()
    info = {
        "canonical": "sqlite",
        "sqlite_path": str(SQLITE_PATH),
        "sqlite_exists": SQLITE_PATH.exists(),
        "json_mirror_dir": str(WORK_ITEMS_DIR),
    }
    if SQLITE_PATH.exists():
        conn = _connect()
        try:
            _init_schema(conn)
            info["count"] = conn.execute("SELECT COUNT(*) AS n FROM work_items").fetchone()["n"]
        finally:
            conn.close()
    return info


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
    if not _bootstrapped:
        bootstrap()
    wid = f"wi_{uuid.uuid4().hex[:12]}"
    ts = now_iso()
    item = {
        "id": wid,
        "title": title,
        "kind": kind,
        "state": "QUEUED",
        "created_at": ts,
        "updated_at": ts,
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
        "history": [{"at": ts, "state": "QUEUED", "reason": "created"}],
    }
    with _lock:
        conn = _connect()
        try:
            _init_schema(conn)
            conn.execute(
                """
                INSERT INTO work_items (
                  id, title, kind, state, created_at, updated_at, isolated_safe, allow_expensive,
                  payload_json, tags_json, recommendation_json, scores_json, dispatch_json,
                  result_json, usage_json, outcomes_json, history_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    wid,
                    title,
                    kind,
                    "QUEUED",
                    ts,
                    ts,
                    1 if isolated_safe else 0,
                    1 if allow_expensive else 0,
                    json.dumps(item["payload"]),
                    json.dumps(item["tags"]),
                    None,
                    "[]",
                    None,
                    None,
                    None,
                    "[]",
                    json.dumps(item["history"]),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        _mirror_json(item)
    events.emit("work_item.created", {"title": title, "kind": kind, "state": "QUEUED"}, work_item_id=wid)
    return item


def get(wid: str) -> dict[str, Any] | None:
    if not _bootstrapped:
        bootstrap()
    conn = _connect()
    try:
        _init_schema(conn)
        row = conn.execute("SELECT * FROM work_items WHERE id=?", (wid,)).fetchone()
        return _row_to_item(row) if row else None
    finally:
        conn.close()


def list_items(*, state: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    if not _bootstrapped:
        bootstrap()
    conn = _connect()
    try:
        _init_schema(conn)
        if state:
            rows = conn.execute(
                "SELECT * FROM work_items WHERE state=? ORDER BY updated_at DESC LIMIT ?",
                (state, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM work_items ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_item(r) for r in rows]
    finally:
        conn.close()


def _persist(conn: sqlite3.Connection, item: dict[str, Any], *, commit: bool = True) -> None:
    conn.execute(
        """
        UPDATE work_items SET
          title=?, kind=?, state=?, updated_at=?, isolated_safe=?, allow_expensive=?,
          payload_json=?, tags_json=?, recommendation_json=?, scores_json=?, dispatch_json=?,
          result_json=?, usage_json=?, outcomes_json=?, history_json=?
        WHERE id=?
        """,
        (
            item["title"],
            item["kind"],
            item["state"],
            item["updated_at"],
            1 if item.get("isolated_safe") else 0,
            1 if item.get("allow_expensive") else 0,
            json.dumps(item.get("payload") or {}),
            json.dumps(item.get("tags") or []),
            json.dumps(item.get("recommendation")) if item.get("recommendation") is not None else None,
            json.dumps(item.get("scores") or []),
            json.dumps(item.get("dispatch")) if item.get("dispatch") is not None else None,
            json.dumps(item.get("result")) if item.get("result") is not None else None,
            json.dumps(item.get("usage")) if item.get("usage") is not None else None,
            json.dumps(item.get("outcomes") or []),
            json.dumps(item.get("history") or []),
            item["id"],
        ),
    )
    if commit:
        conn.commit()
    _mirror_json(item)


def _save(conn: sqlite3.Connection, item: dict[str, Any]) -> None:
    _persist(conn, item, commit=True)


def transition(wid: str, new_state: str, *, reason: str = "", extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if new_state not in STATES:
        raise ValueError(f"unknown state: {new_state}")
    with _lock:
        conn = _connect()
        try:
            _init_schema(conn)
            row = conn.execute("SELECT * FROM work_items WHERE id=?", (wid,)).fetchone()
            if not row:
                raise KeyError(wid)
            item = _row_to_item(row)
            cur = item["state"]
            allowed = TRANSITIONS.get(cur, frozenset())
            if new_state not in allowed:
                raise ValueError(f"illegal transition {cur} → {new_state}")
            item["state"] = new_state
            item["updated_at"] = now_iso()
            hist = {"at": item["updated_at"], "state": new_state, "reason": reason or ""}
            if extra:
                hist["extra_keys"] = sorted(extra.keys())
                for k, v in extra.items():
                    if k in ("recommendation", "scores", "dispatch", "result", "usage"):
                        item[k] = v
            item.setdefault("history", []).append(hist)
            _save(conn, item)
        finally:
            conn.close()
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


def transition_if(wid: str, expected: str, new_state: str, *, reason: str = "") -> dict[str, Any] | None:
    """Compare-and-set transition: one direct legal step, applied only if the item is still `expected`.

    Runs inside BEGIN IMMEDIATE so no other writer can move the item between the check and the write.
    Returns the updated item, or None (nothing written) if the item is no longer in `expected`.
    Used by the Grok bridge so a worker result can never walk an item through, or out of, an Owner gate.
    """
    if new_state not in TRANSITIONS.get(expected, frozenset()):
        raise ValueError(f"illegal transition {expected} -> {new_state}")
    with _lock:
        conn = _connect()
        try:
            _init_schema(conn)
            conn.isolation_level = None
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute("SELECT * FROM work_items WHERE id=?", (wid,)).fetchone()
                if not row:
                    raise KeyError(wid)
                item = _row_to_item(row)
                if item["state"] != expected:
                    conn.execute("ROLLBACK")
                    return None
                item["state"] = new_state
                item["updated_at"] = now_iso()
                item.setdefault("history", []).append({"at": item["updated_at"], "state": new_state,
                                                       "reason": reason or ""})
                _persist(conn, item, commit=False)
                conn.execute("COMMIT")
            except BaseException:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
        finally:
            conn.close()
    events.emit("work_item.state_changed", {"from": expected, "to": new_state, "reason": reason}, work_item_id=wid)
    if new_state == "EXCEPTION":
        events.emit("exception.raised", {"reason": reason}, work_item_id=wid)
    return item


def update_fields(wid: str, **fields: Any) -> dict[str, Any]:
    with _lock:
        conn = _connect()
        try:
            _init_schema(conn)
            row = conn.execute("SELECT * FROM work_items WHERE id=?", (wid,)).fetchone()
            if not row:
                raise KeyError(wid)
            item = _row_to_item(row)
            for k, v in fields.items():
                if k in ("id", "created_at", "state"):
                    continue
                item[k] = v
            item["updated_at"] = now_iso()
            _save(conn, item)
        finally:
            conn.close()
    return item


def by_ui_bucket() -> dict[str, list[dict[str, Any]]]:
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
