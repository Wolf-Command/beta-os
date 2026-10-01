#!/usr/bin/env python3
"""ATRIUM-OPS-MAINTENANCE-PM-1 — Maintenance / preventive maintenance workflow (Beta).

Decision served: 2026-10-02 PICK ATRIUM-OPS-MAINTENANCE-PM-1 in
~/.openclaw/wolf-output/decisions.md (Owner order ATRIUM-OPS-FOUR-20261002 /
OWNER law 2 Oct 2026; brief BRIEF-ATRIUM-OPS-MAINTENANCE-PM-1.md).

Builds the job, not a board:
asset register (CAP-MSC-01 SoT) → location → PM schedule → inspection/checklist →
assigned role/person → due/overdue → issue → work order → priority → action →
parts/vendor/cost (optional UNKNOWN) → evidence → verification → closed →
next service date → history → recurring failure flag.

AMG-first vertical slice. V1 amg-preventive-maintenance.json (19 tasks) is
read-only seed — do not invent intervals/assets/serials/rates.
Cloudbeds/ClickUp/Notion/Telegram sinks stay RETIRED. No auto room blocks.
Writes on Beta :8788 only. staff_ready stays false.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))
BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "state" / "maintenance-pm" / "maintenance_pm.sqlite"
SEED_COPY = BETA_ROOT / "state" / "maintenance-pm" / "amg-preventive-maintenance.seed.json"
V1_PM_JSON = (
    Path.home()
    / ".openclaw"
    / "workspace"
    / "wolf-system"
    / "state"
    / "amg-preventive-maintenance.json"
)
ENV_DB = "WOLF_MAINTENANCE_PM_DB"
ENV_SEED = "WOLF_MAINTENANCE_PM_SEED"

PACK_ID = "ATRIUM-OPS-MAINTENANCE-PM-1"
SCHEMA_ID = "wolf.atrium-ops-maintenance-pm-1.v1"
BOUND = "beta-atrium-ops-maintenance-pm"
PROD_PORT = 8787
PROD_PID_HELD = 15975
REGISTER_ID = "need.maintenance"
CAP_ID = "CAP-MSC-01"
ENTITY = "AMG"
ASSET_API = "/api/msc/assets"
ASSET_PAGE = "/msc-assets"

API_PREFIX = "/api/msc/maintenance-pm"
PAGE_PATHS = frozenset(
    {
        "/msc/maintenance-pm",
        "/msc/maintenance-pm/",
        "/msc-maintenance-pm",
        "/msc-maintenance-pm/",
        "/msc-maintenance-pm.html",
        "/atrium-ops-maintenance-pm-1",
        "/atrium-ops-maintenance-pm-1/",
        "/atrium-ops-maintenance-pm-1.html",
        "/dashboards/atrium-ops-maintenance-pm-1.html",
    }
)

WO_STATUSES = frozenset(
    {
        "open",
        "assigned",
        "in_progress",
        "awaiting_parts",
        "verified",
        "closed",
    }
)
WO_KINDS = frozenset({"pm", "reactive"})
EVIDENCE_KINDS = frozenset(
    {
        "note",
        "photo_ref",
        "document_ref",
        "checklist_complete",
        "parts_ref",
        "vendor_ref",
        "other_ref",
    }
)
# Priority 1..4 from seed; reactive may use same scale.
PRIORITIES = frozenset({1, 2, 3, 4})

# Recurring failure: same pm_task_id (or location+issue key) closed >= N times
# within LOOKBACK_DAYS.
RECURRING_THRESHOLD = 2
RECURRING_LOOKBACK_DAYS = 180

HONESTY: dict[str, Any] = {
    "pack": PACK_ID,
    "schema": SCHEMA_ID,
    "bound": BOUND,
    "register_id": REGISTER_ID,
    "cap": CAP_ID,
    "entity_slice": ENTITY,
    "staff_ready": False,
    "human_commissioned": False,
    "human_proven": False,
    "proven_claimed": False,
    "ready_claimed": False,
    "asset_sot": ASSET_API,
    "asset_page": ASSET_PAGE,
    "second_asset_register_invented": False,
    "parts_catalog_invented": False,
    "vendor_rates_invented": False,
    "serials_invented": False,
    "intervals_invented": False,
    "predictive_intelligence": False,
    "auto_room_block": False,
    "cloudbeds_sink": "RETIRED",
    "clickup_sink": "RETIRED",
    "notion_sink": "RETIRED",
    "telegram_sink": "RETIRED",
    "prod_mutate": False,
    "prod_port": PROD_PORT,
    "prod_pid_held": PROD_PID_HELD,
    "v1_pm_writable": False,
    "writes_beta_only": True,
    "evidence_append_only": True,
    "audit_append_only": True,
    "history_append_only": True,
    "delete_evidence_refused": True,
}


class MaintenancePmError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _now() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _today() -> date:
    return datetime.now(WITA).date()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


def db_path(override: Path | None = None) -> Path:
    if override is not None:
        return Path(override)
    env = (os.environ.get(ENV_DB) or "").strip()
    if env:
        return Path(env)
    return DEFAULT_DB


def seed_path(override: Path | None = None) -> Path:
    if override is not None:
        return Path(override)
    env = (os.environ.get(ENV_SEED) or "").strip()
    if env:
        return Path(env)
    if V1_PM_JSON.is_file():
        return V1_PM_JSON
    if SEED_COPY.is_file():
        return SEED_COPY
    return V1_PM_JSON


def assert_beta_db(path: Path) -> Path:
    resolved = path.resolve()
    text = str(resolved)
    if "beta-os" not in text and ENV_DB not in os.environ:
        if (
            "/tmp" not in text
            and "TemporaryDirectory" not in text
            and not text.startswith("/var/folders")
        ):
            raise MaintenancePmError(
                "maintenance PM refuses a non-beta database",
                code="bad_db",
                http_status=500,
            )
    if "wolf-system" in text or "/Production" in text:
        raise MaintenancePmError(
            "maintenance PM refuses production path",
            code="production_refused",
            http_status=500,
        )
    return resolved


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = assert_beta_db(db_path(path))
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pm_schedule (
  task_id TEXT PRIMARY KEY,
  entity TEXT NOT NULL,
  scope TEXT NOT NULL,
  task TEXT NOT NULL,
  interval_days INTEGER NOT NULL,
  priority INTEGER NOT NULL,
  checklist TEXT NOT NULL,
  last_done TEXT,
  last_raised TEXT,
  assigned_role TEXT,
  provenance TEXT NOT NULL,
  seeded_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pm_sched_entity
  ON pm_schedule(entity, priority);

CREATE TABLE IF NOT EXISTS work_orders (
  wo_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  entity TEXT NOT NULL,
  pm_task_id TEXT,
  location TEXT NOT NULL,
  issue TEXT NOT NULL,
  priority INTEGER NOT NULL,
  status TEXT NOT NULL,
  assigned_role TEXT,
  assigned_person TEXT,
  asset_ref TEXT,
  checklist_json TEXT,
  checklist_complete INTEGER NOT NULL DEFAULT 0,
  actions_taken TEXT,
  parts_json TEXT,
  vendor TEXT,
  cost_amount TEXT,
  cost_currency TEXT,
  cost_status TEXT,
  verification_note TEXT,
  verified_by TEXT,
  verified_at TEXT,
  closed_at TEXT,
  closed_by TEXT,
  next_service_date TEXT,
  recurring_failure INTEGER NOT NULL DEFAULT 0,
  room_blocked INTEGER NOT NULL DEFAULT 0,
  provenance TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (pm_task_id) REFERENCES pm_schedule(task_id)
);

CREATE INDEX IF NOT EXISTS idx_wo_status
  ON work_orders(status, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_wo_pm
  ON work_orders(pm_task_id, status);

CREATE TABLE IF NOT EXISTS wo_evidence (
  evidence_id TEXT PRIMARY KEY,
  wo_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  ref_text TEXT NOT NULL,
  note TEXT,
  recorded_by TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  provenance TEXT NOT NULL,
  FOREIGN KEY (wo_id) REFERENCES work_orders(wo_id)
);

CREATE INDEX IF NOT EXISTS idx_wo_ev
  ON wo_evidence(wo_id, recorded_at);

CREATE TABLE IF NOT EXISTS wo_history (
  history_id TEXT PRIMARY KEY,
  wo_id TEXT NOT NULL,
  pm_task_id TEXT,
  entity TEXT NOT NULL,
  location TEXT NOT NULL,
  issue TEXT NOT NULL,
  closed_at TEXT NOT NULL,
  next_service_date TEXT,
  recurring_failure INTEGER NOT NULL DEFAULT 0,
  detail_json TEXT,
  provenance TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_wo_hist_pm
  ON wo_history(pm_task_id, closed_at);

CREATE TABLE IF NOT EXISTS wo_audit (
  audit_id TEXT PRIMARY KEY,
  wo_id TEXT,
  pm_task_id TEXT,
  action TEXT NOT NULL,
  actor_person_id TEXT NOT NULL,
  detail_json TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_wo_audit
  ON wo_audit(wo_id, created_at);

CREATE TRIGGER IF NOT EXISTS trg_wo_evidence_no_update
BEFORE UPDATE ON wo_evidence
BEGIN
  SELECT RAISE(ABORT, 'wo_evidence is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_wo_evidence_no_delete
BEFORE DELETE ON wo_evidence
BEGIN
  SELECT RAISE(ABORT, 'wo_evidence is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_wo_history_no_update
BEFORE UPDATE ON wo_history
BEGIN
  SELECT RAISE(ABORT, 'wo_history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_wo_history_no_delete
BEFORE DELETE ON wo_history
BEGIN
  SELECT RAISE(ABORT, 'wo_history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_wo_audit_no_update
BEFORE UPDATE ON wo_audit
BEGIN
  SELECT RAISE(ABORT, 'wo_audit is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_wo_audit_no_delete
BEFORE DELETE ON wo_audit
BEGIN
  SELECT RAISE(ABORT, 'wo_audit is append-only');
END;
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def stamp(**extra: Any) -> dict[str, Any]:
    out = dict(HONESTY)
    out["ok"] = True
    out.update(extra)
    out["staff_ready"] = False
    out["human_commissioned"] = False
    out["human_proven"] = False
    out["auto_room_block"] = False
    out["prod_mutate"] = False
    out["second_asset_register_invented"] = False
    out["parts_catalog_invented"] = False
    out["vendor_rates_invented"] = False
    out["predictive_intelligence"] = False
    return out


def page_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    return trimmed in PAGE_PATHS or raw in PAGE_PATHS


def api_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw == API_PREFIX or raw.startswith(API_PREFIX + "/")


def _parse_ymd(raw: str | None) -> date | None:
    if not raw:
        return None
    text = str(raw).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _due_info(last_done: str | None, interval_days: int, today: date | None = None) -> dict[str, Any]:
    base = today or _today()
    done = _parse_ymd(last_done)
    if done is None:
        return {
            "next_due": None,
            "days_overdue": None,
            "due_state": "UNKNOWN_LAST_DONE",
        }
    next_due = done + timedelta(days=int(interval_days))
    delta = (base - next_due).days
    if delta > 0:
        state = "OVERDUE"
    elif delta == 0:
        state = "DUE"
    else:
        state = "OK"
    return {
        "next_due": next_due.isoformat(),
        "days_overdue": delta if delta > 0 else 0,
        "days_until_due": -delta if delta < 0 else 0,
        "due_state": state,
    }


def _audit(
    conn: sqlite3.Connection,
    *,
    wo_id: str | None,
    pm_task_id: str | None,
    action: str,
    actor: str,
    detail: dict[str, Any] | None = None,
) -> str:
    audit_id = _new_id("AUD")
    conn.execute(
        """
        INSERT INTO wo_audit (
          audit_id, wo_id, pm_task_id, action, actor_person_id, detail_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            audit_id,
            wo_id,
            pm_task_id,
            action,
            actor,
            json.dumps(detail or {}, ensure_ascii=False, sort_keys=True),
            _now(),
        ),
    )
    return audit_id


def _checklist_items(checklist: str) -> list[dict[str, Any]]:
    parts = [p.strip() for p in (checklist or "").split(",") if p.strip()]
    return [{"item": p, "done": False} for p in parts]


def _row_schedule(row: sqlite3.Row, today: date | None = None) -> dict[str, Any]:
    d = dict(row)
    due = _due_info(d.get("last_done"), int(d.get("interval_days") or 0), today=today)
    d.update(due)
    return d


def _row_wo(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    for key in ("checklist_json", "parts_json"):
        raw = d.get(key)
        if isinstance(raw, str) and raw:
            try:
                d[key.replace("_json", "")] = json.loads(raw)
            except json.JSONDecodeError:
                d[key.replace("_json", "")] = []
        else:
            d[key.replace("_json", "")] = []
        d.pop(key, None)
    d["checklist_complete"] = bool(d.get("checklist_complete"))
    d["recurring_failure"] = bool(d.get("recurring_failure"))
    d["room_blocked"] = False  # never auto-block; field held false
    d["cost"] = {
        "amount": d.get("cost_amount"),
        "currency": d.get("cost_currency"),
        "status": d.get("cost_status") or "UNKNOWN",
    }
    return d


def _get_wo(conn: sqlite3.Connection, wo_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM work_orders WHERE wo_id=?", (wo_id,)).fetchone()
    return _row_wo(row) if row else None


def _get_pm(conn: sqlite3.Connection, task_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM pm_schedule WHERE task_id=?", (task_id,)).fetchone()
    return _row_schedule(row) if row else None


def _evidence_rows(conn: sqlite3.Connection, wo_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM wo_evidence
        WHERE wo_id=?
        ORDER BY recorded_at, evidence_id
        """,
        (wo_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _audit_rows(conn: sqlite3.Connection, wo_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM wo_audit
        WHERE wo_id=?
        ORDER BY created_at, audit_id
        """,
        (wo_id,),
    ).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        try:
            item["detail"] = json.loads(item.pop("detail_json") or "{}")
        except json.JSONDecodeError:
            item["detail"] = {"raw": item.pop("detail_json", None)}
        out.append(item)
    return out


def _history_rows(
    conn: sqlite3.Connection, *, pm_task_id: str | None = None, limit: int = 50
) -> list[dict[str, Any]]:
    if pm_task_id:
        rows = conn.execute(
            """
            SELECT * FROM wo_history
            WHERE pm_task_id=?
            ORDER BY closed_at DESC, history_id
            LIMIT ?
            """,
            (pm_task_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM wo_history
            ORDER BY closed_at DESC, history_id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        item["recurring_failure"] = bool(item.get("recurring_failure"))
        try:
            item["detail"] = json.loads(item.pop("detail_json") or "{}")
        except json.JSONDecodeError:
            item["detail"] = {"raw": item.pop("detail_json", None)}
        out.append(item)
    return out


def _count_recurring(
    conn: sqlite3.Connection,
    *,
    pm_task_id: str | None,
    location: str,
    issue: str,
) -> bool:
    cutoff = (_today() - timedelta(days=RECURRING_LOOKBACK_DAYS)).isoformat()
    if pm_task_id:
        n = conn.execute(
            """
            SELECT COUNT(*) AS n FROM wo_history
            WHERE pm_task_id=? AND closed_at >= ?
            """,
            (pm_task_id, cutoff),
        ).fetchone()["n"]
    else:
        n = conn.execute(
            """
            SELECT COUNT(*) AS n FROM wo_history
            WHERE location=? AND issue=? AND closed_at >= ?
            """,
            (location, issue, cutoff),
        ).fetchone()["n"]
    # +1 for the WO about to close
    return int(n) + 1 >= RECURRING_THRESHOLD


def refuse_room_block(_body: dict | None = None) -> dict[str, Any]:
    return stamp(
        ok=False,
        error="auto_room_block_refused",
        message="PM / maintenance never auto-blocks rooms. Room blocks are out of scope.",
        http_hint=405,
    )


def refuse_retired_sink(sink: str) -> dict[str, Any]:
    return stamp(
        ok=False,
        error="sink_retired",
        message=f"{sink} maintenance sink is RETIRED. Beta work orders are the SoT.",
        sink=sink,
        http_hint=405,
    )


def refuse_prod_mutate(_body: dict | None = None) -> dict[str, Any]:
    return stamp(
        ok=False,
        error="prod_mutate_refused",
        message="Prod :8787 mutate refused. This desk writes Beta state only.",
        http_hint=403,
    )


def refuse_invent_prices(_body: dict | None = None) -> dict[str, Any]:
    return stamp(
        ok=False,
        error="invent_prices_refused",
        message="Parts vendors/prices/serials/rates are not invented. Use cost_status=UNKNOWN.",
        http_hint=400,
    )


def refuse_delete_evidence(_body: dict | None = None) -> dict[str, Any]:
    return stamp(
        ok=False,
        error="evidence_append_only",
        message="Evidence/history/audit rows are append-only. Silent delete is refused.",
        http_hint=405,
    )


def _guard_forbidden_keys(body: dict[str, Any]) -> None:
    for key in body:
        token = str(key).strip().lower().replace("_", "-")
        if token in {
            "room-block",
            "auto-room-block",
            "block-room",
            "cloudbeds-block",
            "pms-block",
        }:
            raise MaintenancePmError(
                "Auto room block refused.",
                code="auto_room_block_refused",
                http_status=405,
            )
        if token in {
            "cloudbeds",
            "clickup",
            "notion",
            "telegram",
            "clickup-task",
            "notion-page",
            "telegram-send",
        }:
            raise MaintenancePmError(
                f"{token} sink is RETIRED.",
                code="sink_retired",
                http_status=405,
            )
        if token in {
            "prod",
            "prod-mutate",
            "prod-write",
            "kill-prod",
            "restart-8787",
        }:
            raise MaintenancePmError(
                "Prod mutate refused.",
                code="prod_mutate_refused",
                http_status=403,
            )
        if token in {
            "invent-price",
            "invent-vendor",
            "invent-serial",
            "invent-rate",
            "supplier-catalog",
            "price-list",
        }:
            raise MaintenancePmError(
                "Invented parts/vendors/prices/serials refused.",
                code="invent_prices_refused",
                http_status=400,
            )


def _normalize_priority(raw: Any, default: int = 3) -> int:
    if raw is None or raw == "":
        return default
    try:
        p = int(raw)
    except (TypeError, ValueError) as exc:
        raise MaintenancePmError(
            "priority must be integer 1..4",
            code="invalid_priority",
        ) from exc
    if p not in PRIORITIES:
        raise MaintenancePmError(
            "priority must be 1..4 (from seed scale)",
            code="invalid_priority",
        )
    return p


def _copy_seed_to_beta(src: Path) -> Path | None:
    """Mirror V1 seed into Beta state for night-shift / offline prove (read-only copy)."""
    try:
        SEED_COPY.parent.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        if not SEED_COPY.is_file() or SEED_COPY.read_bytes() != data:
            SEED_COPY.write_bytes(data)
        return SEED_COPY
    except OSError:
        return None


def seed_pm_schedule(
    *,
    db: Path | None = None,
    seed_file: Path | None = None,
    actor: str = "SYSTEM-SEED",
) -> dict[str, Any]:
    """Load 19-task V1 PM schedule into Beta. Idempotent. Does not invent intervals."""
    src = seed_path(seed_file)
    if not src.is_file():
        return stamp(
            ok=False,
            error="pm_seed_missing",
            seed_path=str(src),
            imported=0,
            skipped=0,
        )
    before = src.stat()
    try:
        payload = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return stamp(ok=False, error="pm_seed_unreadable", message=str(exc), imported=0)
    after = src.stat()
    if before.st_mtime_ns != after.st_mtime_ns:
        raise MaintenancePmError(
            "PM seed mtime changed during read — aborting",
            code="seed_mtime_changed",
            http_status=500,
        )
    tasks = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(tasks, list) or not tasks:
        return stamp(ok=False, error="pm_seed_empty", imported=0, skipped=0)

    # Preserve Beta mirror when seeding from V1 path.
    if src.resolve() == V1_PM_JSON.resolve():
        _copy_seed_to_beta(src)

    conn = connect(db)
    imported = 0
    skipped = 0
    seeded_ids: list[str] = []
    try:
        for task in tasks:
            if not isinstance(task, dict):
                skipped += 1
                continue
            task_id = str(task.get("id") or "").strip()
            if not task_id:
                skipped += 1
                continue
            existing = conn.execute(
                "SELECT task_id FROM pm_schedule WHERE task_id=?",
                (task_id,),
            ).fetchone()
            if existing:
                skipped += 1
                continue
            interval = int(task.get("interval_days"))
            priority = _normalize_priority(task.get("priority"), default=3)
            checklist = str(task.get("checklist") or "").strip()
            scope = str(task.get("scope") or "").strip() or "property"
            title = str(task.get("task") or "").strip()
            if not title or not checklist or interval <= 0:
                skipped += 1
                continue
            last_done = str(task.get("last_done") or "").strip() or None
            last_raised = str(task.get("last_raised") or "").strip() or None
            provenance = f"v1:amg-preventive-maintenance.json#id={task_id}"
            conn.execute(
                """
                INSERT INTO pm_schedule (
                  task_id, entity, scope, task, interval_days, priority, checklist,
                  last_done, last_raised, assigned_role, provenance, seeded_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    ENTITY,
                    scope,
                    title,
                    interval,
                    priority,
                    checklist,
                    last_done,
                    last_raised,
                    "ROLE-AMG-MAINTENANCE",
                    provenance,
                    _now(),
                    _now(),
                ),
            )
            _audit(
                conn,
                wo_id=None,
                pm_task_id=task_id,
                action="seed_pm_task",
                actor=actor,
                detail={"provenance": provenance, "interval_days": interval},
            )
            imported += 1
            seeded_ids.append(task_id)
        conn.commit()
        total = conn.execute("SELECT COUNT(*) AS n FROM pm_schedule").fetchone()["n"]
    finally:
        conn.close()

    final_mtime = src.stat().st_mtime_ns
    return stamp(
        imported=imported,
        skipped=skipped,
        seeded_ids=seeded_ids,
        schedule_count=int(total),
        expected_seed_count=19,
        seed_path=str(src),
        seed_open_mode="ro",
        seed_mtime_unchanged=final_mtime == before.st_mtime_ns,
        provenance_label="v1:amg-preventive-maintenance.json#id=<task_id>",
        seed_version=payload.get("version"),
        seed_seeded=payload.get("seeded"),
    )


def list_schedule(*, db: Path | None = None, due_only: bool = False) -> dict[str, Any]:
    conn = connect(db)
    try:
        rows = conn.execute(
            "SELECT * FROM pm_schedule WHERE entity=? ORDER BY priority, task_id",
            (ENTITY,),
        ).fetchall()
        today = _today()
        schedule = [_row_schedule(r, today=today) for r in rows]
        if due_only:
            schedule = [s for s in schedule if s.get("due_state") in {"DUE", "OVERDUE"}]
        overdue = sum(1 for s in schedule if s.get("due_state") == "OVERDUE")
        due = sum(1 for s in schedule if s.get("due_state") == "DUE")
    finally:
        conn.close()
    return stamp(
        schedule=schedule,
        count=len(schedule),
        overdue_count=overdue,
        due_count=due,
        entity=ENTITY,
    )


def raise_pm_work_order(
    body: dict[str, Any],
    *,
    actor: str,
    db: Path | None = None,
) -> dict[str, Any]:
    """PM due/overdue → work order (does not invent new intervals)."""
    _guard_forbidden_keys(body)
    task_id = str(body.get("pm_task_id") or body.get("task_id") or "").strip()
    if not task_id:
        raise MaintenancePmError("pm_task_id is required", code="missing_pm_task_id")
    conn = connect(db)
    try:
        pm = _get_pm(conn, task_id)
        if pm is None:
            raise MaintenancePmError(
                f"pm task not found: {task_id}",
                code="pm_task_not_found",
                http_status=404,
            )
        open_existing = conn.execute(
            """
            SELECT wo_id FROM work_orders
            WHERE pm_task_id=? AND status != 'closed'
            ORDER BY created_at DESC LIMIT 1
            """,
            (task_id,),
        ).fetchone()
        if open_existing and not body.get("force"):
            existing = _get_wo(conn, open_existing["wo_id"])
            return stamp(
                ok=True,
                work_order=existing,
                workflow_step="already_open",
                idempotent=True,
            )
        location = str(body.get("location") or pm.get("scope") or "").strip()
        if not location:
            raise MaintenancePmError("location is required", code="missing_location")
        assigned_role = str(
            body.get("assigned_role") or pm.get("assigned_role") or "ROLE-AMG-MAINTENANCE"
        ).strip()
        assigned_person = str(body.get("assigned_person") or "").strip() or None
        asset_ref = str(body.get("asset_ref") or "").strip() or None
        priority = _normalize_priority(body.get("priority"), default=int(pm["priority"]))
        checklist = _checklist_items(pm["checklist"])
        wo_id = _new_id("WO")
        status = "assigned" if assigned_person else "open"
        conn.execute(
            """
            INSERT INTO work_orders (
              wo_id, kind, entity, pm_task_id, location, issue, priority, status,
              assigned_role, assigned_person, asset_ref, checklist_json,
              checklist_complete, actions_taken, parts_json, vendor,
              cost_amount, cost_currency, cost_status, verification_note,
              verified_by, verified_at, closed_at, closed_by, next_service_date,
              recurring_failure, room_blocked, provenance, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, '[]', NULL,
                      NULL, NULL, 'UNKNOWN', NULL, NULL, NULL, NULL, NULL, NULL,
                      0, 0, ?, ?, ?)
            """,
            (
                wo_id,
                "pm",
                ENTITY,
                task_id,
                location,
                pm["task"],
                priority,
                status,
                assigned_role,
                assigned_person,
                asset_ref,
                json.dumps(checklist, ensure_ascii=False),
                f"beta:maintenance-pm#raise:{task_id}",
                _now(),
                _now(),
            ),
        )
        conn.execute(
            "UPDATE pm_schedule SET last_raised=?, updated_at=? WHERE task_id=?",
            (_today().isoformat(), _now(), task_id),
        )
        _audit(
            conn,
            wo_id=wo_id,
            pm_task_id=task_id,
            action="raise_pm",
            actor=actor,
            detail={
                "location": location,
                "priority": priority,
                "due_state": pm.get("due_state"),
                "asset_ref": asset_ref,
            },
        )
        conn.commit()
        wo = _get_wo(conn, wo_id)
    finally:
        conn.close()
    return stamp(work_order=wo, workflow_step="raised", pm_task=pm)


def create_reactive_issue(
    body: dict[str, Any],
    *,
    actor: str,
    db: Path | None = None,
) -> dict[str, Any]:
    """Reactive ticket: location + issue + priority → work order."""
    _guard_forbidden_keys(body)
    location = str(body.get("location") or body.get("room") or body.get("area") or "").strip()
    issue = str(body.get("issue") or body.get("details") or "").strip()
    if not location:
        raise MaintenancePmError("location is required", code="missing_location")
    if not issue:
        raise MaintenancePmError("issue is required", code="missing_issue")
    priority = _normalize_priority(body.get("priority"), default=3)
    assigned_role = str(body.get("assigned_role") or "ROLE-AMG-MAINTENANCE").strip()
    assigned_person = str(body.get("assigned_person") or "").strip() or None
    asset_ref = str(body.get("asset_ref") or "").strip() or None
    # Optional link to a PM task if caller provides one — never invent.
    pm_task_id = str(body.get("pm_task_id") or "").strip() or None
    checklist_src = str(body.get("checklist") or "").strip()
    checklist = _checklist_items(checklist_src) if checklist_src else []
    wo_id = _new_id("WO")
    status = "assigned" if assigned_person else "open"
    conn = connect(db)
    try:
        if pm_task_id and _get_pm(conn, pm_task_id) is None:
            raise MaintenancePmError(
                f"pm task not found: {pm_task_id}",
                code="pm_task_not_found",
                http_status=404,
            )
        conn.execute(
            """
            INSERT INTO work_orders (
              wo_id, kind, entity, pm_task_id, location, issue, priority, status,
              assigned_role, assigned_person, asset_ref, checklist_json,
              checklist_complete, actions_taken, parts_json, vendor,
              cost_amount, cost_currency, cost_status, verification_note,
              verified_by, verified_at, closed_at, closed_by, next_service_date,
              recurring_failure, room_blocked, provenance, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, '[]', NULL,
                      NULL, NULL, 'UNKNOWN', NULL, NULL, NULL, NULL, NULL, NULL,
                      0, 0, ?, ?, ?)
            """,
            (
                wo_id,
                "reactive",
                ENTITY,
                pm_task_id,
                location,
                issue,
                priority,
                status,
                assigned_role,
                assigned_person,
                asset_ref,
                json.dumps(checklist, ensure_ascii=False),
                "beta:maintenance-pm#reactive",
                _now(),
                _now(),
            ),
        )
        _audit(
            conn,
            wo_id=wo_id,
            pm_task_id=pm_task_id,
            action="create_reactive",
            actor=actor,
            detail={"location": location, "priority": priority, "asset_ref": asset_ref},
        )
        conn.commit()
        wo = _get_wo(conn, wo_id)
    finally:
        conn.close()
    return stamp(work_order=wo, workflow_step="created")


def assign_work_order(
    wo_id: str,
    body: dict[str, Any],
    *,
    actor: str,
    db: Path | None = None,
) -> dict[str, Any]:
    _guard_forbidden_keys(body)
    person = str(body.get("assigned_person") or body.get("person") or "").strip() or None
    role = str(body.get("assigned_role") or body.get("role") or "").strip() or None
    if not person and not role:
        raise MaintenancePmError(
            "assigned_person or assigned_role required",
            code="missing_assignee",
        )
    conn = connect(db)
    try:
        current = _get_wo(conn, wo_id)
        if current is None:
            raise MaintenancePmError("work order not found", code="not_found", http_status=404)
        if current["status"] == "closed":
            raise MaintenancePmError("closed work order", code="already_closed")
        conn.execute(
            """
            UPDATE work_orders
            SET assigned_person=COALESCE(?, assigned_person),
                assigned_role=COALESCE(?, assigned_role),
                status=?,
                updated_at=?
            WHERE wo_id=?
            """,
            (person, role, "assigned", _now(), wo_id),
        )
        _audit(
            conn,
            wo_id=wo_id,
            pm_task_id=current.get("pm_task_id"),
            action="assign",
            actor=actor,
            detail={"assigned_person": person, "assigned_role": role},
        )
        conn.commit()
        wo = _get_wo(conn, wo_id)
    finally:
        conn.close()
    return stamp(work_order=wo, workflow_step="assigned")


def complete_checklist(
    wo_id: str,
    body: dict[str, Any],
    *,
    actor: str,
    db: Path | None = None,
) -> dict[str, Any]:
    """Mark checklist items done. Accepts items list or complete_all=true."""
    _guard_forbidden_keys(body)
    conn = connect(db)
    try:
        current = _get_wo(conn, wo_id)
        if current is None:
            raise MaintenancePmError("work order not found", code="not_found", http_status=404)
        if current["status"] == "closed":
            raise MaintenancePmError("closed work order", code="already_closed")
        items = list(current.get("checklist") or [])
        if body.get("complete_all"):
            for item in items:
                item["done"] = True
        else:
            done_names = body.get("items") or body.get("done") or []
            if isinstance(done_names, str):
                done_names = [x.strip() for x in done_names.split(",") if x.strip()]
            if not isinstance(done_names, list):
                raise MaintenancePmError("items must be a list", code="invalid_items")
            done_set = {str(x).strip().lower() for x in done_names}
            for item in items:
                if str(item.get("item") or "").strip().lower() in done_set:
                    item["done"] = True
            # Also allow index-based completion
            for idx in body.get("indexes") or []:
                try:
                    i = int(idx)
                except (TypeError, ValueError):
                    continue
                if 0 <= i < len(items):
                    items[i]["done"] = True
        all_done = bool(items) and all(bool(i.get("done")) for i in items)
        # Reactive WOs may have empty checklist — allow explicit complete_all
        if not items and body.get("complete_all"):
            all_done = True
            items = [{"item": "inspection complete", "done": True}]
        status = "in_progress" if current["status"] in {"open", "assigned"} else current["status"]
        if all_done and status == "in_progress":
            status = "in_progress"
        conn.execute(
            """
            UPDATE work_orders
            SET checklist_json=?, checklist_complete=?, status=?, updated_at=?
            WHERE wo_id=?
            """,
            (
                json.dumps(items, ensure_ascii=False),
                1 if all_done else 0,
                status,
                _now(),
                wo_id,
            ),
        )
        if all_done:
            conn.execute(
                """
                INSERT INTO wo_evidence (
                  evidence_id, wo_id, kind, ref_text, note,
                  recorded_by, recorded_at, provenance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _new_id("EVD"),
                    wo_id,
                    "checklist_complete",
                    f"checklist:{wo_id}",
                    "All checklist items marked done",
                    actor,
                    _now(),
                    "beta:maintenance-pm",
                ),
            )
        _audit(
            conn,
            wo_id=wo_id,
            pm_task_id=current.get("pm_task_id"),
            action="checklist",
            actor=actor,
            detail={"complete": all_done, "item_count": len(items)},
        )
        conn.commit()
        wo = _get_wo(conn, wo_id)
    finally:
        conn.close()
    return stamp(work_order=wo, workflow_step="checklist")


def record_action(
    wo_id: str,
    body: dict[str, Any],
    *,
    actor: str,
    db: Path | None = None,
) -> dict[str, Any]:
    _guard_forbidden_keys(body)
    action_text = str(body.get("actions_taken") or body.get("action") or "").strip()
    if not action_text:
        raise MaintenancePmError("actions_taken is required", code="missing_action")
    conn = connect(db)
    try:
        current = _get_wo(conn, wo_id)
        if current is None:
            raise MaintenancePmError("work order not found", code="not_found", http_status=404)
        if current["status"] == "closed":
            raise MaintenancePmError("closed work order", code="already_closed")
        prev = current.get("actions_taken") or ""
        merged = (prev + "\n" + action_text).strip() if prev else action_text
        conn.execute(
            """
            UPDATE work_orders
            SET actions_taken=?, status=?, updated_at=?
            WHERE wo_id=?
            """,
            (merged, "in_progress", _now(), wo_id),
        )
        _audit(
            conn,
            wo_id=wo_id,
            pm_task_id=current.get("pm_task_id"),
            action="record_action",
            actor=actor,
            detail={"actions_taken": action_text},
        )
        conn.commit()
        wo = _get_wo(conn, wo_id)
    finally:
        conn.close()
    return stamp(work_order=wo, workflow_step="actioned")


def record_parts(
    wo_id: str,
    body: dict[str, Any],
    *,
    actor: str,
    db: Path | None = None,
) -> dict[str, Any]:
    """Optional parts/vendor/cost. UNKNOWN cost is honest; inventing rates refused."""
    _guard_forbidden_keys(body)
    if body.get("invent_price") or body.get("invent_vendor") or body.get("price_list"):
        return refuse_invent_prices(body)
    parts = body.get("parts") or []
    if isinstance(parts, str):
        parts = [{"name": parts, "qty": "UNKNOWN", "unit_cost": "UNKNOWN"}]
    if not isinstance(parts, list):
        raise MaintenancePmError("parts must be a list", code="invalid_parts")
    normalized = []
    for p in parts:
        if isinstance(p, str):
            normalized.append({"name": p, "qty": "UNKNOWN", "unit_cost": "UNKNOWN"})
        elif isinstance(p, dict):
            name = str(p.get("name") or p.get("part") or "").strip()
            if not name:
                continue
            normalized.append(
                {
                    "name": name,
                    "qty": p.get("qty") if p.get("qty") is not None else "UNKNOWN",
                    "unit_cost": p.get("unit_cost")
                    if p.get("unit_cost") is not None
                    else "UNKNOWN",
                }
            )
        else:
            raise MaintenancePmError("invalid part entry", code="invalid_parts")
    vendor = str(body.get("vendor") or "").strip() or None
    cost_amount = body.get("cost_amount")
    cost_currency = str(body.get("cost_currency") or "").strip() or None
    if cost_amount is None or cost_amount == "" or str(cost_amount).upper() == "UNKNOWN":
        cost_status = "UNKNOWN"
        cost_amount = None
    else:
        # Accept only explicitly supplied amounts — never invent.
        cost_status = "DECLARED"
        cost_amount = str(cost_amount)
    awaiting = bool(body.get("awaiting_parts"))
    conn = connect(db)
    try:
        current = _get_wo(conn, wo_id)
        if current is None:
            raise MaintenancePmError("work order not found", code="not_found", http_status=404)
        if current["status"] == "closed":
            raise MaintenancePmError("closed work order", code="already_closed")
        status = "awaiting_parts" if awaiting else current["status"]
        if status == "open":
            status = "in_progress"
        conn.execute(
            """
            UPDATE work_orders
            SET parts_json=?, vendor=?, cost_amount=?, cost_currency=?,
                cost_status=?, status=?, updated_at=?
            WHERE wo_id=?
            """,
            (
                json.dumps(normalized, ensure_ascii=False),
                vendor,
                cost_amount,
                cost_currency,
                cost_status,
                status,
                _now(),
                wo_id,
            ),
        )
        _audit(
            conn,
            wo_id=wo_id,
            pm_task_id=current.get("pm_task_id"),
            action="record_parts",
            actor=actor,
            detail={
                "parts": normalized,
                "vendor": vendor,
                "cost_status": cost_status,
            },
        )
        conn.commit()
        wo = _get_wo(conn, wo_id)
    finally:
        conn.close()
    return stamp(
        work_order=wo,
        workflow_step="parts",
        parts_catalog_invented=False,
        vendor_rates_invented=False,
    )


def add_evidence(
    wo_id: str,
    body: dict[str, Any],
    *,
    actor: str,
    db: Path | None = None,
) -> dict[str, Any]:
    _guard_forbidden_keys(body)
    kind = str(body.get("kind") or "note").strip().lower()
    if kind not in EVIDENCE_KINDS:
        raise MaintenancePmError(
            f"kind must be one of {sorted(EVIDENCE_KINDS)}",
            code="invalid_evidence_kind",
        )
    ref_text = str(body.get("ref_text") or body.get("ref") or "").strip()
    if not ref_text:
        raise MaintenancePmError("ref_text is required", code="missing_ref")
    note = str(body.get("note") or "").strip() or None
    conn = connect(db)
    try:
        current = _get_wo(conn, wo_id)
        if current is None:
            raise MaintenancePmError("work order not found", code="not_found", http_status=404)
        if current["status"] == "closed":
            raise MaintenancePmError("closed work order", code="already_closed")
        evidence_id = _new_id("EVD")
        conn.execute(
            """
            INSERT INTO wo_evidence (
              evidence_id, wo_id, kind, ref_text, note,
              recorded_by, recorded_at, provenance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                wo_id,
                kind,
                ref_text,
                note,
                actor,
                _now(),
                "beta:maintenance-pm",
            ),
        )
        if current["status"] in {"open", "assigned"}:
            conn.execute(
                "UPDATE work_orders SET status=?, updated_at=? WHERE wo_id=?",
                ("in_progress", _now(), wo_id),
            )
        _audit(
            conn,
            wo_id=wo_id,
            pm_task_id=current.get("pm_task_id"),
            action="add_evidence",
            actor=actor,
            detail={"evidence_id": evidence_id, "kind": kind},
        )
        conn.commit()
        evidence = dict(
            conn.execute(
                "SELECT * FROM wo_evidence WHERE evidence_id=?",
                (evidence_id,),
            ).fetchone()
        )
        wo = _get_wo(conn, wo_id)
    finally:
        conn.close()
    return stamp(evidence=evidence, work_order=wo, workflow_step="evidence_added")


def verify_work_order(
    wo_id: str,
    body: dict[str, Any],
    *,
    actor: str,
    db: Path | None = None,
) -> dict[str, Any]:
    _guard_forbidden_keys(body)
    note = str(body.get("verification_note") or body.get("note") or "").strip()
    if not note:
        raise MaintenancePmError(
            "verification_note is required",
            code="missing_verification",
        )
    conn = connect(db)
    try:
        current = _get_wo(conn, wo_id)
        if current is None:
            raise MaintenancePmError("work order not found", code="not_found", http_status=404)
        if current["status"] == "closed":
            raise MaintenancePmError("closed work order", code="already_closed")
        if current["kind"] == "pm" and not current.get("checklist_complete"):
            raise MaintenancePmError(
                "PM work order requires checklist complete before verify",
                code="checklist_incomplete",
            )
        verified_at = _now()
        conn.execute(
            """
            UPDATE work_orders
            SET verification_note=?, verified_by=?, verified_at=?, status=?, updated_at=?
            WHERE wo_id=?
            """,
            (note, actor, verified_at, "verified", verified_at, wo_id),
        )
        _audit(
            conn,
            wo_id=wo_id,
            pm_task_id=current.get("pm_task_id"),
            action="verify",
            actor=actor,
            detail={"verification_note": note},
        )
        conn.commit()
        wo = _get_wo(conn, wo_id)
    finally:
        conn.close()
    return stamp(work_order=wo, workflow_step="verified")


def close_work_order(
    wo_id: str,
    body: dict[str, Any] | None = None,
    *,
    actor: str,
    db: Path | None = None,
) -> dict[str, Any]:
    """Close WO, reset PM cycle (last_done), set next_service_date, append history."""
    payload = body or {}
    _guard_forbidden_keys(payload)
    if payload.get("room_block") or payload.get("auto_room_block") or payload.get("block_room"):
        return refuse_room_block(payload)
    closure_note = str(payload.get("closure_note") or payload.get("note") or "").strip()
    if not closure_note:
        raise MaintenancePmError(
            "closure_note is required to close",
            code="missing_closure_note",
        )
    conn = connect(db)
    try:
        current = _get_wo(conn, wo_id)
        if current is None:
            raise MaintenancePmError("work order not found", code="not_found", http_status=404)
        if current["status"] == "closed":
            return stamp(ok=True, work_order=current, workflow_step="already_closed", idempotent=True)
        if current["status"] != "verified" and not payload.get("force_close"):
            # Allow close from verified OR if actions+evidence exist (eng path)
            evidence_count = conn.execute(
                "SELECT COUNT(*) AS n FROM wo_evidence WHERE wo_id=?",
                (wo_id,),
            ).fetchone()["n"]
            if current["status"] not in {"verified", "in_progress", "awaiting_parts"}:
                raise MaintenancePmError(
                    "close requires verify (or in_progress with evidence)",
                    code="not_ready_to_close",
                )
            if int(evidence_count) < 1 and not current.get("actions_taken"):
                raise MaintenancePmError(
                    "close requires verification, evidence, or actions_taken",
                    code="missing_evidence_for_close",
                )
            if current["kind"] == "pm" and not current.get("checklist_complete"):
                raise MaintenancePmError(
                    "PM close requires checklist complete",
                    code="checklist_incomplete",
                )

        closed_at = _now()
        done_day = _today()
        next_service = None
        pm_task_id = current.get("pm_task_id")
        if pm_task_id:
            pm = _get_pm(conn, pm_task_id)
            if pm:
                next_service = (done_day + timedelta(days=int(pm["interval_days"]))).isoformat()
                conn.execute(
                    """
                    UPDATE pm_schedule
                    SET last_done=?, updated_at=?
                    WHERE task_id=?
                    """,
                    (done_day.isoformat(), closed_at, pm_task_id),
                )

        recurring = _count_recurring(
            conn,
            pm_task_id=pm_task_id,
            location=current["location"],
            issue=current["issue"],
        )
        actions = current.get("actions_taken") or ""
        if closure_note:
            actions = (
                (actions + "\n" + f"CLOSE: {closure_note}").strip()
                if actions
                else f"CLOSE: {closure_note}"
            )
        conn.execute(
            """
            UPDATE work_orders
            SET status=?, closed_at=?, closed_by=?, actions_taken=?,
                next_service_date=?, recurring_failure=?, room_blocked=0, updated_at=?
            WHERE wo_id=?
            """,
            (
                "closed",
                closed_at,
                actor,
                actions,
                next_service,
                1 if recurring else 0,
                closed_at,
                wo_id,
            ),
        )
        history_id = _new_id("HIST")
        conn.execute(
            """
            INSERT INTO wo_history (
              history_id, wo_id, pm_task_id, entity, location, issue,
              closed_at, next_service_date, recurring_failure, detail_json, provenance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                history_id,
                wo_id,
                pm_task_id,
                current["entity"],
                current["location"],
                current["issue"],
                closed_at,
                next_service,
                1 if recurring else 0,
                json.dumps(
                    {"closure_note": closure_note, "kind": current["kind"]},
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "beta:maintenance-pm",
            ),
        )
        _audit(
            conn,
            wo_id=wo_id,
            pm_task_id=pm_task_id,
            action="close",
            actor=actor,
            detail={
                "closure_note": closure_note,
                "next_service_date": next_service,
                "recurring_failure": recurring,
            },
        )
        conn.commit()
        wo = _get_wo(conn, wo_id)
        pm_after = _get_pm(conn, pm_task_id) if pm_task_id else None
    finally:
        conn.close()
    return stamp(
        work_order=wo,
        pm_task=pm_after,
        workflow_step="closed",
        next_service_date=next_service,
        recurring_failure=recurring,
        auto_room_block=False,
    )


def list_work_orders(
    *,
    db: Path | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    conn = connect(db)
    try:
        if status:
            rows = conn.execute(
                """
                SELECT * FROM work_orders
                WHERE status=?
                ORDER BY priority, created_at DESC
                """,
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM work_orders
                ORDER BY
                  CASE status
                    WHEN 'open' THEN 0
                    WHEN 'assigned' THEN 1
                    WHEN 'in_progress' THEN 2
                    WHEN 'awaiting_parts' THEN 3
                    WHEN 'verified' THEN 4
                    ELSE 5
                  END,
                  priority, created_at DESC
                """
            ).fetchall()
        orders = [_row_wo(r) for r in rows]
        counts = {
            s: conn.execute(
                "SELECT COUNT(*) AS n FROM work_orders WHERE status=?",
                (s,),
            ).fetchone()["n"]
            for s in sorted(WO_STATUSES)
        }
        evidence_total = conn.execute("SELECT COUNT(*) AS n FROM wo_evidence").fetchone()["n"]
        audit_total = conn.execute("SELECT COUNT(*) AS n FROM wo_audit").fetchone()["n"]
        history_total = conn.execute("SELECT COUNT(*) AS n FROM wo_history").fetchone()["n"]
        schedule_count = conn.execute("SELECT COUNT(*) AS n FROM pm_schedule").fetchone()["n"]
    finally:
        conn.close()
    openish = sum(
        counts[s]
        for s in ("open", "assigned", "in_progress", "awaiting_parts", "verified")
    )
    register_state = "PARTIAL" if (orders or schedule_count) else "MISSING"
    return stamp(
        work_orders=orders,
        count=len(orders),
        status_counts=counts,
        evidence_total=int(evidence_total),
        audit_total=int(audit_total),
        history_total=int(history_total),
        schedule_count=int(schedule_count),
        open_workflow_count=openish,
        register_state=register_state,
        workflow=(
            "asset register (CAP-MSC-01) → location → PM schedule → "
            "inspection/checklist → assigned role/person → due/overdue → "
            "issue → work order → priority → action → parts/vendor/cost "
            "(optional UNKNOWN) → evidence → verification → closed → "
            "next service date → history → recurring failure flag"
        ),
        statuses=sorted(WO_STATUSES),
        kinds=sorted(WO_KINDS),
        evidence_kinds=sorted(EVIDENCE_KINDS),
    )


def get_work_order_detail(wo_id: str, *, db: Path | None = None) -> dict[str, Any]:
    conn = connect(db)
    try:
        wo = _get_wo(conn, wo_id)
        if wo is None:
            raise MaintenancePmError("work order not found", code="not_found", http_status=404)
        evidence = _evidence_rows(conn, wo_id)
        audit = _audit_rows(conn, wo_id)
        history = _history_rows(conn, pm_task_id=wo.get("pm_task_id"), limit=20)
        pm = _get_pm(conn, wo["pm_task_id"]) if wo.get("pm_task_id") else None
    finally:
        conn.close()
    return stamp(
        work_order=wo,
        evidence=evidence,
        audit=audit,
        history=history,
        pm_task=pm,
        workflow_step=wo.get("status"),
    )


def asset_register_pointer() -> dict[str, Any]:
    """Point at CAP-MSC-01 SoT — do not invent a second register."""
    return stamp(
        asset_sot=ASSET_API,
        asset_page=ASSET_PAGE,
        message=(
            "Asset / equipment register SoT is CAP-MSC-01 via /api/msc/assets. "
            "Empty register is honest. Work orders may carry optional asset_ref "
            "linking to that register; this pack does not invent serials or barcodes."
        ),
        inventory_complete=False,
        second_asset_register_invented=False,
    )


def desk(*, db: Path | None = None, seed: bool = True) -> dict[str, Any]:
    seed_result = None
    if seed:
        seed_result = seed_pm_schedule(db=db)
    listing = list_work_orders(db=db)
    schedule = list_schedule(db=db)
    listing["pm_schedule"] = schedule.get("schedule") or []
    listing["overdue_count"] = schedule.get("overdue_count")
    listing["due_count"] = schedule.get("due_count")
    listing["pm_seed"] = seed_result
    listing["asset_register"] = asset_register_pointer()
    listing["page"] = "/msc/maintenance-pm"
    listing["api"] = API_PREFIX
    return listing


def handle_get(path: str, *, db: Path | None = None) -> dict[str, Any]:
    raw = path.split("?")[0]
    rest = raw[len(API_PREFIX) :].strip("/")
    if not rest:
        return desk(db=db)
    if rest == "meta":
        return stamp(
            statuses=sorted(WO_STATUSES),
            kinds=sorted(WO_KINDS),
            evidence_kinds=sorted(EVIDENCE_KINDS),
            priorities=sorted(PRIORITIES),
            workflow=list_work_orders(db=db).get("workflow"),
            asset_sot=ASSET_API,
        )
    if rest == "schedule":
        return list_schedule(db=db)
    if rest == "schedule/due":
        return list_schedule(db=db, due_only=True)
    if rest == "assets" or rest.startswith("assets/"):
        return asset_register_pointer()
    if rest == "history":
        conn = connect(db)
        try:
            hist = _history_rows(conn, limit=100)
        finally:
            conn.close()
        return stamp(history=hist, count=len(hist))
    if rest == "seed" or rest == "import-v1":
        return seed_pm_schedule(db=db)
    if rest in {"room-block", "block-room"}:
        return refuse_room_block()
    wo_id = rest.split("/", 1)[0]
    return get_work_order_detail(wo_id, db=db)


def handle_post(
    path: str,
    body: dict[str, Any] | None,
    *,
    actor: str = "PERS-MATT",
    db: Path | None = None,
) -> tuple[dict[str, Any], int]:
    payload = body if isinstance(body, dict) else {}
    raw = path.split("?")[0]
    rest = raw[len(API_PREFIX) :].strip("/")

    try:
        _guard_forbidden_keys(payload)
        if rest in {"room-block", "block-room", "auto-room-block"} or rest.startswith("room-block/"):
            return refuse_room_block(payload), 405
        if rest in {"cloudbeds", "clickup", "notion", "telegram"} or rest.startswith(
            ("cloudbeds/", "clickup/", "notion/", "telegram/")
        ):
            return refuse_retired_sink(rest.split("/", 1)[0]), 405
        if rest in {"prod", "prod-mutate"} or "prod-mutate" in rest:
            return refuse_prod_mutate(payload), 403
        if rest.endswith("/delete") or rest.endswith("/purge"):
            return refuse_delete_evidence(payload), 405
        if rest in {"invent-price", "invent-prices", "price-list"}:
            return refuse_invent_prices(payload), 400

        if rest in {"seed", "import-v1"}:
            return seed_pm_schedule(db=db, actor=actor), 200

        if rest in {"raise", "raise-pm"}:
            result = raise_pm_work_order(payload, actor=actor, db=db)
            return result, 200 if result.get("ok") else 400

        if rest in {"reactive", "issue", ""}:
            # POST / → reactive create; POST /raise is PM
            if rest == "" and (payload.get("pm_task_id") or payload.get("task_id")):
                result = raise_pm_work_order(payload, actor=actor, db=db)
            else:
                result = create_reactive_issue(payload, actor=actor, db=db)
            return result, 200 if result.get("ok") else 400

        parts = rest.split("/")
        wo_id = parts[0]
        action = parts[1] if len(parts) > 1 else ""

        if action == "assign":
            return assign_work_order(wo_id, payload, actor=actor, db=db), 200
        if action == "checklist":
            return complete_checklist(wo_id, payload, actor=actor, db=db), 200
        if action == "action":
            return record_action(wo_id, payload, actor=actor, db=db), 200
        if action == "parts":
            return record_parts(wo_id, payload, actor=actor, db=db), 200
        if action == "evidence":
            return add_evidence(wo_id, payload, actor=actor, db=db), 200
        if action == "verify":
            return verify_work_order(wo_id, payload, actor=actor, db=db), 200
        if action == "close":
            result = close_work_order(wo_id, payload, actor=actor, db=db)
            code = 200
            if result.get("error") == "auto_room_block_refused":
                code = 405
            return result, code
        if action in {"delete", "purge"}:
            return refuse_delete_evidence(payload), 405
        if action in {"room-block", "block-room"}:
            return refuse_room_block(payload), 405
        return stamp(ok=False, error="unknown_path", path=path), 404
    except MaintenancePmError as exc:
        return (
            stamp(ok=False, error=exc.code, message=str(exc)),
            exc.http_status,
        )
    except sqlite3.Error as exc:
        msg = str(exc)
        if "append-only" in msg:
            return refuse_delete_evidence({"detail": msg}), 405
        return stamp(ok=False, error="db_error", message=msg), 500
