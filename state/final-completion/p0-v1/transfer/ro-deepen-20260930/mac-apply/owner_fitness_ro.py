#!/usr/bin/env python3
"""Beta Owner Fitness / Spartacus — READ-ONLY summary loader.

Fail-closed. DB opened mode=ro only. No writes. No PII row dumps.
Aggregates + recent workout summaries (date/lift only).
Fitness ≠ HR. staff_ready=false. NOT REBUILT+PROVEN.

Intended mount (Mac apply): beta-os serve route
  GET /api/owner/fitness-ro
Prod :8787 must remain untouched. Never copy DB into git.
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

# Safe tables for COUNT(*) — all OK. Never SELECT * from food_log/body_log/contacts/journal/profile values.
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
    }
    out.update(extra)
    return out


def _connect_ro(path: Path) -> sqlite3.Connection:
    # URI mode=ro — refuses write; fail if missing
    uri = f"file:{path}?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=5.0)


def load_fitness_ro(recent_limit: int = 8) -> dict[str, Any]:
    provenance = {"db_path": str(DB_PATH), "open_mode": "ro"}

    if not DB_PATH.is_file():
        return _stamp(
            False,
            "NO_SOT_YET",
            surface="owner_fitness",
            provenance=provenance,
            table_counts={},
            recent_workouts=[],
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
            banner="Could not open Spartacus DB read-only.",
            error=str(e),
        )

    counts: dict[str, int | None] = {}
    recent: list[dict[str, Any]] = []
    day_stats: dict[str, Any] = {}
    workout_error: str | None = None
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

        # recent workouts: date + lift only (no free-text entry dump)
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
    finally:
        conn.close()

    return _stamp(
        True,
        "V1_RO_OK",
        surface="owner_fitness",
        provenance=provenance,
        table_counts=counts,
        recent_workouts=recent,
        day_stats=day_stats,
        workout_error=workout_error,
        banner="Owner personal Fitness · Spartacus V1 DB read-only · Fitness ≠ HR · no PII dumps",
    )


def as_json_bytes(payload: dict[str, Any] | None = None) -> bytes:
    data = payload if payload is not None else load_fitness_ro()
    return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")


if __name__ == "__main__":
    print(as_json_bytes().decode("utf-8"))
