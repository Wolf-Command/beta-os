#!/usr/bin/env python3
"""027 Uma Blu ops console — idempotent Beta-only migration.

PR operational table + payment-approve permission (no authority limit seeded).
Seeds at most 3 example PRs. No float. No staff seats. No ledger accounts.
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
MIGRATION_ID = "027_uma_ops_console"
FORBIDDEN = ("wolf-system", "money.sqlite")
TZ8 = timezone(timedelta(hours=8))

PERM_ID = "PERM-BZG-PR-PAYMENT-APPROVE"
PERM_CODE = "bzg.pr.payment_approve"


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
    conn.execute(
        """
        INSERT INTO org_permissions (
          permission_id, code, resource, action, description, status, created_at, updated_at
        ) VALUES (?, ?, 'bzg', 'payment_approve',
                  'Approve Uma Blu PR payment request (requires authority limit)',
                  'ACTIVE', ?, ?)
        ON CONFLICT(permission_id) DO UPDATE SET
          code=excluded.code,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (PERM_ID, PERM_CODE, ts, ts),
    )
    # No role grants. No authority limits. Live monetary authority stays 0.
    fixtures = ops.seed_fixture_prs(conn)
    detail = (
        f"uma ops console; prs={len(fixtures)}; "
        f"perm={PERM_CODE}; authority_limits_seeded=0; staff_grants=0"
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
    return {"fixtures": len(fixtures), "detail": detail}


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
