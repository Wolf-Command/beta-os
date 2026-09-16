#!/usr/bin/env python3
"""Idempotent Phase 2 Metricool READ schema + seeds + data_lane backfill."""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DB = BETA_ROOT / "catalog" / "content_library.sqlite"
SQL_FILE = BETA_ROOT / "scripts" / "migrations" / "002_phase2_metricool.sql"
TZ = ZoneInfo("Asia/Makassar")

# Data-driven Metricool blogIds (no Goss Group planning brand; no BZG/AMG aliases).
METRICOOL_SEEDS = [
    ("habitat", "metricool", "6260634", "The Habitat"),
    ("atrium", "metricool", "6260617", "Atrium Lombok"),
    ("umablu", "metricool", "6260631", "Uma Blu Coffee & Brunch"),
    ("selo", "metricool", "6260635", "Selo Properties"),
    ("tropik", "metricool", "6260638", "Tropik Resort Lombok"),
]

DATA_LANE_TABLES = [
    "content_plans",
    "plan_revisions",
    "content_cards",
    "card_revisions",
    "skill_runs",
    "performance_records",
    "planning_context_snapshots",
]


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, decl: str) -> None:
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def main() -> int:
    if not DB.exists():
        print(f"DB missing: {DB}", file=sys.stderr)
        return 1
    sql = SQL_FILE.read_text(encoding="utf-8")
    conn = sqlite3.connect(str(DB))
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(sql)
        ts = now_iso()

        for brand_key, system, ext_id, label in METRICOOL_SEEDS:
            conn.execute(
                """
                INSERT INTO brand_external_ids (
                  brand_key, external_system, external_id, label, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?)
                ON CONFLICT(brand_key, external_system, external_id) DO UPDATE SET
                  label=excluded.label,
                  status='ACTIVE',
                  updated_at=excluded.updated_at
                """,
                (brand_key, system, ext_id, label, ts, ts),
            )

        # Additive data_lane on Phase 1 + Phase 2 tables
        for table in DATA_LANE_TABLES:
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if not exists:
                continue
            _ensure_column(conn, table, "data_lane", "TEXT NOT NULL DEFAULT 'operational'")

        # Backfill Phase 1 fixtures as test (do not delete)
        # Known Phase 1 acceptance plans/cards/revisions/skill_runs for habitat
        conn.execute(
            """
            UPDATE content_plans
            SET data_lane='test'
            WHERE brand_id='habitat'
              AND (ifnull(data_lane,'')='' OR data_lane='operational')
              AND created_at < ?
            """,
            (ts,),
        )
        # Mark revisions/cards/skill_runs tied to those plans as test
        conn.execute(
            """
            UPDATE plan_revisions SET data_lane='test'
            WHERE plan_id IN (SELECT id FROM content_plans WHERE data_lane='test')
            """
        )
        conn.execute(
            """
            UPDATE content_cards SET data_lane='test'
            WHERE plan_id IN (SELECT id FROM content_plans WHERE data_lane='test')
            """
        )
        conn.execute(
            """
            UPDATE card_revisions SET data_lane='test'
            WHERE card_id IN (
              SELECT id FROM content_cards WHERE data_lane='test'
            )
            """
        )
        conn.execute(
            """
            UPDATE skill_runs SET data_lane='test'
            WHERE plan_id IN (SELECT id FROM content_plans WHERE data_lane='test')
               OR (plan_id IS NULL AND brand_id='habitat' AND created_at < ?)
            """,
            (ts,),
        )

        conn.commit()
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        if ok != "ok":
            return 2
        n = conn.execute("SELECT COUNT(*) FROM brand_external_ids WHERE external_system='metricool'").fetchone()[0]
        print(f"brand_external_ids.metricool={n}")
        for t in (
            "brand_external_ids",
            "performance_records",
            "planning_context_snapshots",
            "planning_context_refs",
        ):
            c = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"{t}: {c}")
        test_plans = conn.execute(
            "SELECT COUNT(*) FROM content_plans WHERE data_lane='test'"
        ).fetchone()[0]
        print(f"content_plans.data_lane=test: {test_plans}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
