#!/usr/bin/env python3
"""BZG-CLOSE-OWNER-CONTROL-ESB-RECON-1 — venue.close.owner_control (Beta only).

Decision served: 2026-09-17 · PICK Uma Blu Daily Close (extend) + Owner pack
BZG-CLOSE-OWNER-CONTROL-ESB-RECON-1.

Adds PERM-VENUE-CLOSE-OWNER-CONTROL. Grant to ROLE-MATT only (assignment-derived
Owner Control / Break Glass). Not Cashier / CLOSER / Captain (they keep reassign).
Does not delete closes, clear ownership rows, or touch prod :8787.
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

# Owner P0 5 Oct 2026: retention/free-space guard (docs/BACKUP-RETENTION.md)
import sys as _bp_sys  # noqa: E402
if str(ROOT / "scripts") not in _bp_sys.path:
    _bp_sys.path.insert(0, str(ROOT / "scripts"))
from core.backup_policy import premig_backup  # noqa: E402
MIGRATION_ID = "bzg_close_owner_control_esb_recon_1"
PACK = "BZG-CLOSE-OWNER-CONTROL-ESB-RECON-1"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")

PERM_ID = "PERM-VENUE-CLOSE-OWNER-CONTROL"
PERM_CODE = "venue.close.owner_control"

GRANT_ROLES = ("ROLE-MATT",)
DENY_ROLES = (
    "ROLE-BZG-CASHIER",
    "ROLE-BZG-CLOSER",
    "ROLE-BZG-CAPTAIN",
    "ROLE-BZG-HFB",
    "ROLE-BZG-FB-OPS-LEAD",
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
    dest = BACKUP_DIR / f"pre-bzg-close-owner-control-esb-recon-1-{stamp()}.sqlite"
    dest = premig_backup(db_path, dest)
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
        tonight = conn.execute(
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
            ) VALUES (?, ?, 'venue.close', 'owner_control',
                      'Owner Control / Break Glass on venue close (reopen/cancel/unlock/return — reason + audit; no money movement)',
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
                print(f"WARN: missing role {role_id}", file=sys.stderr)
                continue
            conn.execute(
                """
                INSERT INTO org_role_permissions (
                  role_id, permission_id, effect, created_at, updated_at
                ) VALUES (?, ?, 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET
                  effect='ALLOW',
                  updated_at=excluded.updated_at
                """,
                (role_id, PERM_ID, ts, ts),
            )
            print(f"GRANT {PERM_CODE} → {role_id}")

        # Explicit: do not grant deny-list roles (and strip if previously present).
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

        # Migration registry (idempotent)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                  id TEXT PRIMARY KEY,
                  applied_at TEXT NOT NULL,
                  note TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT INTO schema_migrations (id, applied_at, note)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  applied_at=excluded.applied_at,
                  note=excluded.note
                """,
                (MIGRATION_ID, ts, PACK),
            )
        except sqlite3.Error as exc:
            print(f"WARN: schema_migrations: {exc}", file=sys.stderr)

        closes_after = int(
            conn.execute("SELECT COUNT(*) FROM venue_daily_closes").fetchone()[0]
        )
        tonight_after = conn.execute(
            """
            SELECT close_id, taken_by_person_id, state
            FROM venue_daily_closes
            WHERE business_date=? AND venue_brand_id='BZG-UMA'
            """,
            (datetime.now(TZ8).date().isoformat(),),
        ).fetchone()

        conn.commit()

        # Prove grant
        grant = conn.execute(
            """
            SELECT rp.role_id, p.code, rp.effect
            FROM org_role_permissions rp
            JOIN org_permissions p ON p.permission_id = rp.permission_id
            WHERE p.code=? AND rp.role_id='ROLE-MATT' AND rp.effect='ALLOW'
              AND p.status='ACTIVE'
            """,
            (PERM_CODE,),
        ).fetchone()

        print(f"PACK={PACK}")
        print(f"PERM={PERM_CODE} id={PERM_ID}")
        print(f"GRANT_MATT={'yes' if grant else 'NO'}")
        print(f"CLOSES_BEFORE={closes_before} CLOSES_AFTER={closes_after}")
        if tonight:
            print(
                f"TONIGHT_UNCHANGED="
                f"{dict(tonight) == dict(tonight_after) if tonight_after else False} "
                f"close={tonight['close_id']} holder={tonight['taken_by_person_id']} "
                f"state={tonight['state']}"
            )
        print("staff_ready=false human_commissioned=false")
        return 0 if grant else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
