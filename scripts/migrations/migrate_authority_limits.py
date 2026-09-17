#!/usr/bin/env python3
"""010 Authority Limits — idempotent Beta-only migration.

HOW MUCH / material conditions. Does NOT seed live staff thresholds.
SEEDED LIVE AUTHORITY LIMITS = 0. No admin UI / delegation / dual approval / SoD / real auth.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "catalog" / "content_library.sqlite"
SQL = Path(__file__).resolve().parent / "010_authority_limits.sql"
MIGRATION_ID = "010_authority_limits"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def main() -> int:
    db_path = DB.resolve()
    s = str(db_path)
    for frag in FORBIDDEN:
        if frag in s:
            print(f"REFUSE: {frag} in {s}", file=sys.stderr)
            return 2
    if "beta-os" not in s:
        print(f"REFUSE: not beta-os: {s}", file=sys.stderr)
        return 2

    ts = now_iso()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SQL.read_text(encoding="utf-8"))
        print("DDL applied")

        # Optional inactive catalog permission for tests — NOT granted to any live role.
        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'INACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET
              code=excluded.code,
              resource=excluded.resource,
              action=excluded.action,
              description=excluded.description,
              status=excluded.status,
              updated_at=excluded.updated_at
            """,
            (
                "PERM-TEST-SPEND",
                "test.spend.approve",
                "test.spend",
                "approve",
                "Test-only spend permission (INACTIVE; not granted to live roles)",
                ts,
                ts,
            ),
        )

        # Do NOT insert any org_authority_limits rows into live Beta DB.
        live_n = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
        print(f"seeded_live_authority_limits={live_n}")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (
                MIGRATION_ID,
                ts,
                f"Authority Limits schema; seeded_live=0; live_rows={live_n}; no admin UI",
            ),
        )
        conn.commit()

        for t in ("org_authority_limits", "org_permissions"):
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}={n}")
        inactive_test = conn.execute(
            "SELECT status FROM org_permissions WHERE permission_id='PERM-TEST-SPEND'"
        ).fetchone()
        print(f"  PERM-TEST-SPEND status={inactive_test[0] if inactive_test else None}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        if live_n != 0:
            print("WARN: live authority limits unexpectedly non-zero", file=sys.stderr)
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
