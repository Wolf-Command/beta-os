#!/usr/bin/env python3
"""028 BZG reputation observe permissions — idempotent Beta-only migration.

Adds bzg.reputation.read and bzg.reputation.observe.
Does NOT grant them to any role. Does NOT create observation rows.
Does NOT scrape, reply, or write Production.
Bound: CAP-BZG-07 reputation observe v1.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "catalog" / "content_library.sqlite"
MIGRATION_ID = "028_bzg_reputation_permissions"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "alchemist")
TZ8 = timezone(timedelta(hours=8))

PERMS = (
    (
        "PERM-BZG-REPUTATION-READ",
        "bzg.reputation.read",
        "bzg.reputation",
        "read",
        "Read BZG review observations and the empty honesty view",
    ),
    (
        "PERM-BZG-REPUTATION-OBSERVE",
        "bzg.reputation.observe",
        "bzg.reputation",
        "observe",
        "Store one review observation with provenance",
    ),
)


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    db_path = Path(args[0]).resolve() if args else DB.resolve()
    s = str(db_path)
    low = s.lower()
    for frag in FORBIDDEN:
        if frag.lower() in low:
            print(f"REFUSE: {frag} in {s}", file=sys.stderr)
            return 2
    if "beta-os" not in s:
        print(f"REFUSE: not beta-os: {s}", file=sys.stderr)
        return 2
    if db_path.name != "content_library.sqlite":
        print(f"REFUSE: permissions live only on the Beta catalog: {s}", file=sys.stderr)
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
        # Explicitly do NOT insert into org_role_permissions.

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        ids = tuple(row[0] for row in PERMS)
        marks = ",".join("?" * len(ids))
        n_perms = conn.execute(
            f"""
            SELECT COUNT(*) FROM org_permissions
            WHERE permission_id IN ({marks}) AND status='ACTIVE'
            """,
            ids,
        ).fetchone()[0]
        grants = conn.execute(
            f"""
            SELECT COUNT(*) FROM org_role_permissions
            WHERE permission_id IN ({marks})
            """,
            ids,
        ).fetchone()[0]
        note = (
            f"bzg.reputation perms={n_perms}; role_grants={grants} (must stay 0)"
        )
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              applied_at=excluded.applied_at,
              note=excluded.note
            """,
            (MIGRATION_ID, ts, note),
        )
        conn.commit()
    finally:
        conn.close()
    print(note)
    if n_perms != len(PERMS) or grants != 0:
        print("REFUSE: permission shape drifted", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
