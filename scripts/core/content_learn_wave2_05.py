#!/usr/bin/env python3
"""Wave 2.05 — Content learn-back read. No loop is written.

performance_records is a Metricool history store. Six planning snapshots
froze a handful of those ids into the previous Habitat fortnight. The
current brief does not carry those ids. Metricool write stays off.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
ENV_FILE = BETA_ROOT / ".env"
CYCLE_FILE = Path(
    "/Users/wolfterminal/.openclaw/workspace/wolf-system/dashboards/data/content-plans/habitat-2026-09-28-11.json"
)
CURRENT_START = "2026-09-28"
CURRENT_END = "2026-10-11"


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=8)
    conn.row_factory = sqlite3.Row
    return conn


def _truthy(raw: str | None) -> bool:
    return (raw or "").strip().lower() in {"1", "true", "yes", "on"}


def _flag(name: str) -> bool:
    """One named flag. Other env lines are not loaded and not returned."""
    if name in os.environ and (os.environ.get(name) or "").strip():
        return _truthy(os.environ.get(name))
    if not ENV_FILE.is_file():
        return False
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        if key.strip() != name:
            continue
        return _truthy(value.strip().strip('"').strip("'"))
    return False


def _performance(conn: sqlite3.Connection) -> dict[str, Any]:
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "performance_records" not in names:
        return {"present": False, "count": None, "why": "performance_records is not in the catalog."}
    count = int(conn.execute("SELECT COUNT(*) FROM performance_records").fetchone()[0])
    brands = {
        row[0]: int(row[1])
        for row in conn.execute(
            "SELECT brand_key, COUNT(*) FROM performance_records GROUP BY brand_key"
        )
    }
    systems = [
        {"external_system": row[0], "data_lane": row[1], "count": int(row[2])}
        for row in conn.execute(
            """
            SELECT external_system, data_lane, COUNT(*)
            FROM performance_records GROUP BY 1, 2
            """
        )
    ]
    engagement_null = int(
        conn.execute(
            "SELECT COUNT(*) FROM performance_records WHERE engagement IS NULL"
        ).fetchone()[0]
    )
    published = conn.execute(
        "SELECT MIN(published_at_utc), MAX(published_at_utc) FROM performance_records"
    ).fetchone()
    fetched = conn.execute(
        "SELECT MIN(fetched_at), MAX(fetched_at) FROM performance_records"
    ).fetchone()
    return {
        "present": True,
        "count": count,
        "brands": brands,
        "systems": systems,
        "engagement_null": engagement_null,
        "published_min": published[0],
        "published_max": published[1],
        "fetched_min": fetched[0],
        "fetched_max": fetched[1],
        "values_omitted": True,
        "why": "This is a history store. A row count is not a learning loop.",
    }


def _snapshots(conn: sqlite3.Connection) -> dict[str, Any]:
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "planning_context_snapshots" not in names:
        return {"present": False, "count": None, "why": "planning_context_snapshots is missing."}
    rows = conn.execute(
        """
        SELECT id, brand_key, plan_id, created_at, snapshot_json
        FROM planning_context_snapshots
        ORDER BY id
        """
    ).fetchall()
    perf_lists = []
    for row in rows:
        try:
            snap = json.loads(row["snapshot_json"] or "{}")
        except json.JSONDecodeError:
            snap = {}
        ids = snap.get("performance_record_ids") if isinstance(snap, dict) else None
        perf_lists.append(len(ids) if isinstance(ids, list) else None)
    plan_ids = [row["plan_id"] for row in rows]
    periods = []
    if plan_ids and "content_plans" in names:
        marks = ",".join("?" for _ in plan_ids)
        periods = [
            {"period_start": row[0], "period_end": row[1], "count": int(row[2])}
            for row in conn.execute(
                f"""
                SELECT period_start, period_end, COUNT(*)
                FROM content_plans WHERE id IN ({marks})
                GROUP BY period_start, period_end
                """,
                plan_ids,
            )
        ]
    current_plans = 0
    if "content_plans" in names:
        current_plans = int(
            conn.execute(
                "SELECT COUNT(*) FROM content_plans WHERE period_start>=?",
                (CURRENT_START,),
            ).fetchone()[0]
        )
    return {
        "present": True,
        "count": len(rows),
        "brands": sorted({row["brand_key"] for row in rows}),
        "plan_ids": plan_ids,
        "performance_ids_per_snapshot": perf_lists,
        "plan_periods": periods,
        "current_cycle_plans": current_plans,
        "why": (
            "These snapshots belong to the previous Habitat fortnight. "
            "They are not attached to the current brief."
        ),
    }


def _cycle() -> dict[str, Any]:
    if not CYCLE_FILE.is_file():
        return {"present": False, "why": "The current Habitat cycle file is missing."}
    try:
        data = json.loads(CYCLE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"present": False, "why": f"Cycle file unreadable ({type(exc).__name__})."}
    if not isinstance(data, dict):
        return {"present": False, "why": "Cycle file is not an object."}
    intro = data.get("intro") if isinstance(data.get("intro"), str) else ""
    cited = re.search(r"Metricool snapshot pulled (\S+)", intro or "")
    blob = json.dumps(data)
    return {
        "present": True,
        "brand_id": data.get("brand_id"),
        "cycle_key": data.get("cycle_key"),
        "cycle_start": data.get("cycle_start"),
        "cycle_end": data.get("cycle_end"),
        "updated_at": data.get("updated_at"),
        "posts": len(data.get("posts") or []),
        "stories": len(data.get("stories") or []),
        "has_performance_record_id": "performance_record" in blob,
        "prose_metricool_snapshot": cited.group(1) if cited else None,
        "why": (
            "The intro names an older Metricool snapshot in prose. "
            "The file has no performance_record id."
        ),
    }


def _queue(conn: sqlite3.Connection) -> dict[str, Any]:
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "content_misa_queue" not in names:
        return {"present": False, "count": None, "why": "content_misa_queue is missing."}
    count = int(conn.execute("SELECT COUNT(*) FROM content_misa_queue").fetchone()[0])
    row = conn.execute(
        "SELECT state, reason, publish FROM content_misa_queue ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return {
        "present": True,
        "count": count,
        "state": row["state"] if row else None,
        "reason": row["reason"] if row else None,
        "publish": row["publish"] if row else None,
        "why": "The tick fallback queue is not a learn-back row.",
    }


def load_learn() -> dict[str, Any]:
    if not CATALOG_DB.is_file():
        performance = {"present": False, "count": None}
        snapshots = {"present": False, "count": None}
        queue = {"present": False, "count": None}
    else:
        conn = _ro(CATALOG_DB)
        try:
            performance = _performance(conn)
            snapshots = _snapshots(conn)
            queue = _queue(conn)
        finally:
            conn.close()
    cycle = _cycle()
    write_on = _flag("BETA_METRICOOL_WRITE_ENABLED")
    read_on = _flag("BETA_METRICOOL_ENABLED")
    fed = bool(cycle.get("has_performance_record_id")) and int(snapshots.get("current_cycle_plans") or 0) > 0
    return {
        "ok": True,
        "pack": "WAVE2-05",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "metricool_write": write_on,
        "metricool_read_enabled": read_on,
        "state": "PARTIAL",
        "performance": performance,
        "snapshots": snapshots,
        "current_brief": cycle,
        "publish_queue": queue,
        "learn": {
            "state": "PARTIAL" if fed else "UNAVAILABLE",
            "fed_into_current_brief": fed,
            "rows_written": False,
            "why": (
                "performance_records does not feed the current brief. "
                "No learn-back row was written."
            ),
        },
        "why": "History is readable. The next brief does not read it as a loop.",
    }


def refuse_write() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "writes_off",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "metricool_write": False,
        "message": "Content learn-back does not write Metricool, a brief, or a learn-back row.",
    }
