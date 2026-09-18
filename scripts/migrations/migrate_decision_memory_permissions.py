#!/usr/bin/env python3
"""026 Decision Memory permissions — idempotent Beta-only migration.

Adds decision.memory.read and decision.memory.record permission codes.
Does NOT grant them to any live staff role. Does NOT hard-code person grants.
Does NOT create decision rows. Bound: CAP-INTEL-04 live prove.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "catalog" / "content_library.sqlite"
MIGRATION_ID = "026_decision_memory_permissions"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))

STAFF_ROLES = (
    "ROLE-MATT",
    "ROLE-OWNER",
    "ROLE-AMANDA",
    "ROLE-HAIKAL",
    "ROLE-MISA",
    "ROLE-DEVI",
    "ROLE-CONTENT-MGMT",
    "ROLE-GGV-EDIT",
    "ROLE-CONTENT-CREW",
)

PERMS = (
    (
        "PERM-DECISION-MEMORY-READ",
        "decision.memory.read",
        "decision.memory",
        "read",
        "Recall / read Decision Memory rows",
    ),
    (
        "PERM-DECISION-MEMORY-RECORD",
        "decision.memory.record",
        "decision.memory",
        "record",
        "Record a Decision Memory row",
    ),
)


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    db_path = Path(args[0]).resolve() if args else DB.resolve()
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
        for perm_id, code, resource, action, desc in PERMS:
            conn.execute(
                """
                INSERT INTO org_permissions (
                  permission_id, code, resource, action, description,
                  status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                ON CONFLICT(permission_id) DO UPDATE SET
                  code=excluded.code,
                  resource=excluded.resource,
                  action=excluded.action,
                  description=excluded.description,
                  status=excluded.status,
                  updated_at=excluded.updated_at
                """,
                (perm_id, code, resource, action, desc, ts, ts),
            )
        # Explicitly do NOT insert into org_role_permissions for staff roles.

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        n_perms = conn.execute(
            """
            SELECT COUNT(*) FROM org_permissions
            WHERE permission_id IN (
              'PERM-DECISION-MEMORY-READ','PERM-DECISION-MEMORY-RECORD'
            ) AND status='ACTIVE'
            """
        ).fetchone()[0]
        marks = ",".join("?" * len(STAFF_ROLES))
        staff_grants = conn.execute(
            f"""
            SELECT COUNT(*) FROM org_role_permissions
            WHERE permission_id IN (
              'PERM-DECISION-MEMORY-READ','PERM-DECISION-MEMORY-RECORD'
            ) AND role_id IN ({marks})
            """,
            STAFF_ROLES,
        ).fetchone()[0]
        note = (
            f"decision.memory perms={n_perms}; staff_role_grants={staff_grants} "
            "(must stay 0)"
        )
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              applied_at=excluded.applied_at, note=excluded.note
            """,
            (MIGRATION_ID, ts, note),
        )
        conn.commit()
        print(f"OK {MIGRATION_ID}: {note}")
        if staff_grants != 0:
            print("REFUSE: staff role grants must stay 0", file=sys.stderr)
            return 2
        if n_perms != 2:
            print("REFUSE: expected 2 ACTIVE decision.memory perms", file=sys.stderr)
            return 2
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
