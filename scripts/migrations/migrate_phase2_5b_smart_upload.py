#!/usr/bin/env python3
"""Phase 2.5B — additive smart-upload metadata columns (idempotent)."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DB = Path("/Users/wolfterminal/beta-os/catalog/content_library.sqlite")

STAGED_COLS = [
    ("original_filename", "TEXT"),
    ("canonical_filename", "TEXT"),
    ("subject", "TEXT"),
    ("detail", "TEXT"),
    ("location", "TEXT"),
    ("shoot_date", "TEXT"),
    ("sequence_token", "TEXT"),
    ("media_type", "TEXT"),
    ("uploaded_by", "TEXT"),
    ("uploaded_at", "TEXT"),
    ("content_plan_id", "INTEGER"),
    ("content_card_id", "INTEGER"),
    ("processing_status", "TEXT"),
    ("library_status", "TEXT"),
    ("data_lane", "TEXT"),
    ("batch_id", "TEXT"),
]

ASSET_COLS = list(STAGED_COLS)  # same set


def existing_cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def add_cols(conn: sqlite3.Connection, table: str, cols: list[tuple[str, str]]) -> list[str]:
    have = existing_cols(conn, table)
    added = []
    for name, typ in cols:
        if name in have:
            continue
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")
        added.append(f"{table}.{name}")
    return added


def main() -> int:
    if not DB.is_file():
        print(f"ERROR: DB missing {DB}", file=sys.stderr)
        return 2
    conn = sqlite3.connect(str(DB))
    try:
        added = []
        added += add_cols(conn, "staged_assets", STAGED_COLS)
        added += add_cols(conn, "assets", ASSET_COLS)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_assets_canonical ON assets(canonical_filename)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_assets_meta ON assets(brand, stage, shoot_date, subject)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_assets_lane ON assets(data_lane)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_staged_canonical ON staged_assets(canonical_filename)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_staged_batch ON staged_assets(batch_id)"
        )
        # Backfill data_lane default for existing rows (NULL → operational)
        conn.execute(
            "UPDATE assets SET data_lane='operational' WHERE data_lane IS NULL OR data_lane=''"
        )
        conn.execute(
            "UPDATE staged_assets SET data_lane='operational' WHERE data_lane IS NULL OR data_lane=''"
        )
        conn.commit()
        print(f"OK phase2.5b migration; added={len(added)}")
        for a in added:
            print(f"  + {a}")
        if not added:
            print("  (already applied)")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
