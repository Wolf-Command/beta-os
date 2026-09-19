#!/usr/bin/env python3
"""008 Assignment Scope — idempotent Beta-only migration.

WHERE only. Does NOT build RBAC/Authority/real auth. Does NOT touch production.
Conservative seed: GGV scopes for known Beta assignments only.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
DB = ROOT / "catalog" / "content_library.sqlite"
SQL = Path(__file__).resolve().parent / "008_assignment_scope.sql"
MIGRATION_ID = "008_assignment_scope"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def upsert_scope(conn, scope_id, scope_type, display_name, status, ts):
    conn.execute(
        """
        INSERT INTO org_scopes (
          scope_id, scope_type, display_name, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(scope_id) DO UPDATE SET
          scope_type=excluded.scope_type,
          display_name=excluded.display_name,
          status=excluded.status,
          updated_at=excluded.updated_at
        """,
        (scope_id, scope_type, display_name, status, ts, ts),
    )


def upsert_target(conn, scope_id, target_type, target_id, ts):
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
        """,
        (scope_id, target_type, target_id, ts),
    )


def upsert_asg_scope(conn, assignment_id, scope_id, start_at, end_at, status, ts, *, revive: bool = False):
    """Seed an assignment-scope. Default does not revive ENDED rows.

    revive=True is Owner-only. main() and other migrate/seed/test callers
    must not pass it.
    """
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(
        conn,
        assignment_id,
        scope_id,
        start_at,
        ts,
        end_at=end_at,
        status=status,
        revive=revive,
    )


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
    start = "2026-09-16T00:00:00+08:00"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SQL.read_text(encoding="utf-8"))
        print("DDL applied")

        upsert_scope(conn, "SCOPE-GGV-ALL", "entity", "GGV (all entity)", "ACTIVE", ts)
        upsert_target(conn, "SCOPE-GGV-ALL", "entity", "ENT-GGV", ts)

        upsert_scope(
            conn, "SCOPE-GGV-CONTENT", "department",
            "GGV Content department", "ACTIVE", ts,
        )
        upsert_target(conn, "SCOPE-GGV-CONTENT", "department", "DEPT-GGV-CONTENT", ts)

        # Matt: multi-scope (entity + department)
        upsert_asg_scope(conn, "ASG-MATT-OWNER-1", "SCOPE-GGV-ALL", start, None, "ACTIVE", ts)
        upsert_asg_scope(conn, "ASG-MATT-OWNER-1", "SCOPE-GGV-CONTENT", start, None, "ACTIVE", ts)
        upsert_asg_scope(conn, "ASG-AMANDA-CM-1", "SCOPE-GGV-CONTENT", start, None, "ACTIVE", ts)
        upsert_asg_scope(conn, "ASG-HAIKAL-VE-1", "SCOPE-GGV-CONTENT", start, None, "ACTIVE", ts)
        upsert_asg_scope(conn, "ASG-MISA-CC-1", "SCOPE-GGV-CONTENT", start, None, "ACTIVE", ts)

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
            (MIGRATION_ID, ts, "Assignment Scope; conservative GGV seed; no RBAC"),
        )
        conn.commit()

        for tname in (
            "org_scopes", "org_scope_targets", "org_assignment_scopes",
            "org_assignments", "permissions",
        ):
            n = conn.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()[0]
            print(f"  {tname}={n}")
        print("--- assignment scopes ---")
        for r in conn.execute(
            """
            SELECT assignment_id, scope_id, status, end_at
            FROM org_assignment_scopes
            ORDER BY assignment_id, scope_id
            """
        ):
            print(f"  {r['assignment_id']} → {r['scope_id']} ({r['status']}) end={r['end_at']}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
