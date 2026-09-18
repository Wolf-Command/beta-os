#!/usr/bin/env python3
"""028 Uma Blu petty cash surface — idempotent Beta-only migration.

Creates operational tin tables. Prefer 0 live movement rows on the real catalog.
Fixtures are for tests (seed_fixture_petty). No float. No cashier. No variance policy.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

DB = ROOT / "catalog" / "content_library.sqlite"
MIGRATION_ID = "028_uma_petty_cash"
FORBIDDEN = ("wolf-system", "money.sqlite")
TZ8 = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def refuse(path: Path) -> None:
    s = str(path.resolve())
    for bad in FORBIDDEN:
        if bad in s:
            raise SystemExit(f"refuses path containing {bad}: {path}")
    if "beta-os" not in s:
        raise SystemExit(f"refuses non-beta path: {path}")


def apply(conn: sqlite3.Connection) -> dict:
    from core import uma_ops_console as ops

    ops.ensure_schema(conn)
    ts = now_iso()
    live_movements = int(
        conn.execute("SELECT COUNT(*) FROM bzg_ops_petty_movements").fetchone()[0]
    )
    live_non_example = int(
        conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_petty_movements WHERE example=0"
        ).fetchone()[0]
    )
    detail = (
        f"uma petty cash; schema=ok; live_movements={live_movements}; "
        f"live_non_example={live_non_example}; float=NOT_FOUND; "
        f"variance_policy_seeded=0; cashier_seeded=0"
    )
    conn.execute(
        """
        INSERT INTO schema_migrations (id, applied_at, note)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          applied_at=excluded.applied_at,
          note=excluded.note
        """,
        (MIGRATION_ID, ts, detail),
    )
    return {
        "live_movements": live_movements,
        "live_non_example": live_non_example,
        "detail": detail,
    }


def main() -> int:
    refuse(DB)
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        result = apply(conn)
        conn.commit()
        print(f"OK {MIGRATION_ID}: {result['detail']}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
