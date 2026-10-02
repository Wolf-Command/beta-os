#!/usr/bin/env python3
"""BZG-CLOSE-GOVERNED-TAKEOVER-1 — venue.close.reassign (Beta only).

Decision served: 2026-09-17 · PICK Uma Blu Daily Close (extend) + Owner
order BZG-CLOSE-GOVERNED-TAKEOVER-1 (tonight Uma lock / Iza mid-flow).

Adds PERM-VENUE-CLOSE-REASSIGN (venue.close.reassign). Grants to Captain,
HFB, FB-Ops-Lead, Matt only — NOT Cashier / CLOSER seats.
Does not delete closes, clear ownership rows, or weaken concurrency.
staff_ready / human_commissioned stay false.
"""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"
MIGRATION_ID = "bzg_close_governed_takeover_1"
PACK = "BZG-CLOSE-GOVERNED-TAKEOVER-1"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")

PERM_ID = "PERM-VENUE-CLOSE-REASSIGN"
PERM_CODE = "venue.close.reassign"

GRANT_ROLES = (
    "ROLE-BZG-CAPTAIN",
    "ROLE-BZG-HFB",
    "ROLE-BZG-FB-OPS-LEAD",
    "ROLE-MATT",
)
DENY_ROLES = (
    "ROLE-BZG-CASHIER",
    "ROLE-BZG-CLOSER",
)


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(TZ8).strftime("%Y%m%d-%H%M%S")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _refuse_path(db_path: Path) -> str | None:
    s = str(db_path.resolve())
    for frag in FORBIDDEN:
        if frag in s:
            return frag
    if "beta-os" not in s:
        return "not-beta-os"
    return None


def main() -> int:
    db_path = DB.resolve()
    bad = _refuse_path(db_path)
    if bad:
        print(f"REFUSE: {bad} in {db_path}", file=sys.stderr)
        return 2

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"pre-bzg-close-governed-takeover-1-{stamp()}.sqlite"
    shutil.copy2(db_path, dest)
    digest = _sha256(dest)
    print(f"BACKUP={dest}")
    print(f"SHA256={digest}")

    ts = now_iso()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        closes_before = int(
            conn.execute("SELECT COUNT(*) FROM venue_daily_closes").fetchone()[0]
        )
        taken_before = conn.execute(
            """
            SELECT close_id, taken_by_person_id, state
            FROM venue_daily_closes
            WHERE business_date=? AND venue_brand_id='BZG-UMA'
            """,
            (datetime.now(TZ8).date().isoformat(),),
        ).fetchone()

        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description, status,
              created_at, updated_at
            ) VALUES (?, ?, 'venue.close', 'reassign',
                      'Governed take-over / reassign of an active venue close (reason + audit)',
                      'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET
              code=excluded.code,
              resource=excluded.resource,
              action=excluded.action,
              description=excluded.description,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (PERM_ID, PERM_CODE, ts, ts),
        )

        for role_id in GRANT_ROLES:
            role = conn.execute(
                "SELECT role_id FROM org_roles WHERE role_id=?", (role_id,)
            ).fetchone()
            if not role:
                print(f"SKIP grant — role missing: {role_id}")
                continue
            conn.execute(
                """
                INSERT INTO org_role_permissions (
                  role_id, permission_id, effect, created_at, updated_at
                ) VALUES (?, ?, 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET
                  effect='ALLOW', updated_at=excluded.updated_at
                """,
                (role_id, PERM_ID, ts, ts),
            )
            print(f"GRANT {PERM_CODE} → {role_id}")

        # Explicit: cashier / closer seats must not inherit reassign.
        for role_id in DENY_ROLES:
            row = conn.execute(
                """
                SELECT effect FROM org_role_permissions
                WHERE role_id=? AND permission_id=?
                """,
                (role_id, PERM_ID),
            ).fetchone()
            if row is not None:
                conn.execute(
                    """
                    DELETE FROM org_role_permissions
                    WHERE role_id=? AND permission_id=?
                    """,
                    (role_id, PERM_ID),
                )
                print(f"REVOKED stray {PERM_CODE} on {role_id}")

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
                f"{PACK}: {PERM_CODE} for Captain/HFB/FB-Ops/Matt; cashiers cannot steal",
            ),
        )
        conn.commit()

        closes_after = int(
            conn.execute("SELECT COUNT(*) FROM venue_daily_closes").fetchone()[0]
        )
        taken_after = conn.execute(
            """
            SELECT close_id, taken_by_person_id, state
            FROM venue_daily_closes
            WHERE business_date=? AND venue_brand_id='BZG-UMA'
            """,
            (datetime.now(TZ8).date().isoformat(),),
        ).fetchone()
        if closes_after != closes_before:
            print("REFUSE: venue_daily_closes count changed", file=sys.stderr)
            return 2
        if (taken_before is None) != (taken_after is None):
            print("REFUSE: tonight close row mutated", file=sys.stderr)
            return 2
        if taken_before and (
            str(taken_before["taken_by_person_id"] or "")
            != str(taken_after["taken_by_person_id"] or "")
            or str(taken_before["state"] or "") != str(taken_after["state"] or "")
        ):
            print("REFUSE: tonight ownership/state mutated by migration", file=sys.stderr)
            return 2

        for role_id in GRANT_ROLES:
            ok = conn.execute(
                """
                SELECT 1 FROM org_role_permissions
                WHERE role_id=? AND permission_id=? AND effect='ALLOW'
                """,
                (role_id, PERM_ID),
            ).fetchone()
            if role_id != "ROLE-OWNER" and conn.execute(
                "SELECT 1 FROM org_roles WHERE role_id=?", (role_id,)
            ).fetchone():
                if not ok:
                    print(f"REFUSE: missing grant {role_id}", file=sys.stderr)
                    return 2
        for role_id in DENY_ROLES:
            bad_grant = conn.execute(
                """
                SELECT 1 FROM org_role_permissions
                WHERE role_id=? AND permission_id=? AND effect='ALLOW'
                """,
                (role_id, PERM_ID),
            ).fetchone()
            if bad_grant:
                print(f"REFUSE: {role_id} must not have {PERM_CODE}", file=sys.stderr)
                return 2

        print(f"permission={PERM_CODE}")
        print(f"venue_daily_closes={closes_after} (unchanged)")
        if taken_after:
            print(
                f"tonight_holder={taken_after['taken_by_person_id']} "
                f"state={taken_after['state']} close_id={taken_after['close_id']}"
            )
        print("staff_ready=false")
        print(f"integrity_check={conn.execute('PRAGMA integrity_check').fetchone()[0]}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
