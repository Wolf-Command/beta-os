#!/usr/bin/env python3
"""Beta Owner Fitness / Spartacus — READ-ONLY summary loader (deepened).

Fail-closed. DB opened mode=ro only. No writes. No PII row dumps.
Aggregates + recent workouts + peptide schedule meta.
Fitness ≠ HR. staff_ready=false. NOT REBUILT+PROVEN.

Mount: GET /api/owner/fitness-ro
Prod :8787 untouched. Never copy DB into git.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))

DEFAULT_DB = Path.home() / ".openclaw/personal/health/spartacus.sqlite"
DB_PATH = Path(os.environ.get("BETA_SPARTACUS_DB", str(DEFAULT_DB)))
DEFAULT_PEPTIDES = Path.home() / (
    ".openclaw/workspace/wolf-system/dashboards/data/spartacus-peptides.json"
)
PEPTIDES_PATH = Path(os.environ.get("BETA_SPARTACUS_PEPTIDES", str(DEFAULT_PEPTIDES)))

COUNT_TABLES = (
    "body_log", "contacts", "days", "food_log", "habit_ticks", "habits", "journal",
    "lift_sessions", "lift_weights", "metrics_log", "peptide_log", "plans", "profile",
    "pt141_log", "quotes", "reading_log", "resets", "sched_fired", "training_log",
    "water_log", "weekly",
)


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")


def _stamp(ok: bool, reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "ok": ok,
        "reason": reason,
        "staff_ready": False,
        "fitness_ne_hr": True,
        "claim": "NOT_REBUILT_PLUS_PROVEN",
        "migration_state": "PARTIAL",
        "read_only": True,
        "pii_in_response": False,
        "as_of_wita": _now_wita(),
        "honesty": "PARTIAL · Owner personal · Fitness ≠ HR · no PII dumps",
    }
    out.update(extra)
    return out


def _connect_ro(path: Path) -> sqlite3.Connection:
    uri = f"file:{path}?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=5.0)


def _peptide_schedule() -> dict[str, Any]:
    """Safe schedule meta from spartacus-peptides.json — no injection log PII."""
    if not PEPTIDES_PATH.is_file():
        return {
            "status": "MISSING",
            "path": str(PEPTIDES_PATH),
            "compounds": [],
            "note": "peptide schedule SoT not found; do not invent",
        }
    try:
        raw = json.loads(PEPTIDES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return {
            "status": "ERROR",
            "path": str(PEPTIDES_PATH),
            "compounds": [],
            "error": str(e),
        }
    compounds_out = []
    for c in (raw.get("compounds") or [])[:20]:
        if not isinstance(c, dict):
            continue
        compounds_out.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "dose": c.get("dose"),
            "when": c.get("when"),
            "cycle": c.get("cycle"),
            "route": c.get("route"),
        })
    return {
        "status": "PRESENT",
        "path": str(PEPTIDES_PATH),
        "law": raw.get("law"),
        "fresh_start": raw.get("fresh_start"),
        "protocol_dated": raw.get("protocol_dated"),
        "weekday_note": raw.get("weekday_note"),
        "rotate_sites": raw.get("rotate_sites"),
        "compounds": compounds_out,
        "note": "schedule meta only · logged not law · never Day-0 reset invent",
    }


def load_fitness_ro(recent_limit: int = 12) -> dict[str, Any]:
    provenance = {
        "db_path": str(DB_PATH),
        "open_mode": "ro",
        "peptides_json": str(PEPTIDES_PATH),
    }
    peptide_sched = _peptide_schedule()

    if not DB_PATH.is_file():
        return _stamp(
            False,
            "NO_SOT_YET",
            surface="owner_fitness",
            provenance=provenance,
            table_counts={},
            recent_workouts=[],
            recent_lifts=[],
            peptide_log_recent=[],
            peptide_schedule=peptide_sched,
            today_day=None,
            today_plan=None,
            banner="V1 Spartacus DB SoT not found; no invented workouts. Fitness ≠ HR.",
            error="spartacus.sqlite missing",
        )

    try:
        conn = _connect_ro(DB_PATH)
    except sqlite3.Error as e:
        return _stamp(
            False,
            "DB_OPEN_ERROR",
            surface="owner_fitness",
            provenance=provenance,
            table_counts={},
            recent_workouts=[],
            recent_lifts=[],
            peptide_log_recent=[],
            peptide_schedule=peptide_sched,
            today_day=None,
            today_plan=None,
            banner="Could not open Spartacus DB read-only.",
            error=str(e),
        )

    counts: dict[str, int | None] = {}
    recent: list[dict[str, Any]] = []
    recent_lifts: list[dict[str, Any]] = []
    peptide_recent: list[dict[str, Any]] = []
    day_stats: dict[str, Any] = {}
    workout_error: str | None = None
    today_day: dict[str, Any] | None = None
    today_plan: dict[str, Any] | None = None
    try:
        cur = conn.cursor()
        existing = {
            r[0]
            for r in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for t in COUNT_TABLES:
            if t not in existing:
                counts[t] = None
                continue
            try:
                counts[t] = int(cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0])
            except sqlite3.Error:
                counts[t] = None

        if "training_log" in existing:
            try:
                rows = cur.execute(
                    "SELECT date, lift, ts FROM training_log "
                    "ORDER BY COALESCE(ts, date) DESC LIMIT ?",
                    (recent_limit,),
                ).fetchall()
                for date_v, lift_v, ts_v in rows:
                    recent.append({"date": date_v, "lift": lift_v, "ts": ts_v})
            except sqlite3.Error as e:
                recent = []
                workout_error = str(e)
        else:
            workout_error = "training_log table missing"

        if "lift_sessions" in existing:
            try:
                rows = cur.execute(
                    "SELECT date, lift_key, progressed FROM lift_sessions "
                    "ORDER BY date DESC LIMIT ?",
                    (recent_limit,),
                ).fetchall()
                for date_v, key_v, prog in rows:
                    recent_lifts.append({
                        "date": date_v,
                        "lift_key": key_v,
                        "progressed": bool(prog) if prog is not None else None,
                    })
            except sqlite3.Error:
                recent_lifts = []

        if "peptide_log" in existing:
            try:
                rows = cur.execute(
                    "SELECT date, compound, status FROM peptide_log "
                    "ORDER BY date DESC LIMIT ?",
                    (recent_limit,),
                ).fetchall()
                for date_v, compound_v, status_v in rows:
                    peptide_recent.append({
                        "date": date_v,
                        "compound": compound_v,
                        "status": status_v,
                    })
            except sqlite3.Error:
                peptide_recent = []

        if "days" in existing:
            try:
                day_stats["days_rows"] = counts.get("days")
                day_stats["days_with_wo"] = int(
                    cur.execute(
                        "SELECT COUNT(*) FROM days WHERE wo1_done=1 OR wo2_done=1"
                    ).fetchone()[0]
                )
                day_stats["days_closed"] = int(
                    cur.execute(
                        "SELECT COUNT(*) FROM days WHERE logged_closed=1"
                    ).fetchone()[0]
                )
            except sqlite3.Error:
                day_stats = {"days_rows": counts.get("days")}

        today_day = None
        today_plan = None
        today = datetime.now(WITA).strftime("%Y-%m-%d")
        if "days" in existing:
            try:
                row = cur.execute(
                    "SELECT date, day_num, water_ml, wo1_done, wo2_done, "
                    "meditation_done, reading_done, breathwork_done, diet_status, "
                    "logged_closed, verdict, perfect "
                    "FROM days WHERE date=? LIMIT 1",
                    (today,),
                ).fetchone()
                if row:
                    today_day = {
                        "date": row[0],
                        "day_num": row[1],
                        "water_ml": row[2],
                        "wo1_done": bool(row[3]),
                        "wo2_done": bool(row[4]),
                        "meditation_done": bool(row[5]),
                        "reading_done": bool(row[6]),
                        "breathwork_done": bool(row[7]),
                        "diet_status": row[8] or "",
                        "logged_closed": bool(row[9]),
                        "verdict": row[10] or "",
                        "perfect": bool(row[11]),
                    }
                else:
                    # nearest prior day for glance
                    row = cur.execute(
                        "SELECT date, day_num, water_ml, wo1_done, wo2_done, "
                        "meditation_done, reading_done, breathwork_done, diet_status, "
                        "logged_closed, verdict, perfect "
                        "FROM days ORDER BY date DESC LIMIT 1"
                    ).fetchone()
                    if row:
                        today_day = {
                            "date": row[0],
                            "day_num": row[1],
                            "water_ml": row[2],
                            "wo1_done": bool(row[3]),
                            "wo2_done": bool(row[4]),
                            "meditation_done": bool(row[5]),
                            "reading_done": bool(row[6]),
                            "breathwork_done": bool(row[7]),
                            "diet_status": row[8] or "",
                            "logged_closed": bool(row[9]),
                            "verdict": row[10] or "",
                            "perfect": bool(row[11]),
                            "note": "latest day row (today empty)",
                        }
            except sqlite3.Error as e:
                today_day = {"error": str(e)}
        if "plans" in existing:
            try:
                prow = cur.execute(
                    "SELECT date, proposal, confirmed, tasks FROM plans "
                    "WHERE date=? LIMIT 1",
                    (today,),
                ).fetchone()
                if not prow:
                    prow = cur.execute(
                        "SELECT date, proposal, confirmed, tasks FROM plans "
                        "ORDER BY date DESC LIMIT 1"
                    ).fetchone()
                if prow:
                    tasks_raw = prow[3] or "[]"
                    try:
                        tasks = json.loads(tasks_raw) if isinstance(tasks_raw, str) else tasks_raw
                    except json.JSONDecodeError:
                        tasks = []
                    if not isinstance(tasks, list):
                        tasks = []
                    # strip to name/done only — no PII invent
                    tasks_out = []
                    for t in tasks[:12]:
                        if isinstance(t, dict):
                            tasks_out.append({
                                "name": t.get("name"),
                                "done": bool(t.get("done")),
                            })
                    try:
                        prop = json.loads(prow[1]) if isinstance(prow[1], str) else (prow[1] or {})
                    except json.JSONDecodeError:
                        prop = {}
                    if not isinstance(prop, dict):
                        prop = {}
                    today_plan = {
                        "date": prow[0],
                        "confirmed": bool(prow[2]),
                        "task_count": len(tasks_out),
                        "tasks": tasks_out,
                        "blocks": {
                            "b1": prop.get("b1"),
                            "b2": prop.get("b2"),
                            "cal_ok": prop.get("cal_ok"),
                        },
                    }
            except sqlite3.Error as e:
                today_plan = {"error": str(e)}
    finally:
        conn.close()

    return _stamp(
        True,
        "V1_RO_OK",
        surface="owner_fitness",
        provenance=provenance,
        table_counts=counts,
        recent_workouts=recent,
        recent_lifts=recent_lifts,
        peptide_log_recent=peptide_recent,
        peptide_schedule=peptide_sched,
        day_stats=day_stats,
        today_day=today_day,
        today_plan=today_plan,
        workout_error=workout_error,
        banner="Owner personal Fitness · Spartacus V1 DB read-only · Fitness ≠ HR · no PII dumps",
        ui_hints={
            "sections": ["honesty", "today", "program", "recent_workouts", "recent_lifts", "peptides", "counts"],
            "writes": False,
            "fitness_ne_hr": True,
        },
    )


def as_json_bytes(payload: dict[str, Any] | None = None) -> bytes:
    data = payload if payload is not None else load_fitness_ro()
    return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")


if __name__ == "__main__":
    print(as_json_bytes().decode("utf-8"))
