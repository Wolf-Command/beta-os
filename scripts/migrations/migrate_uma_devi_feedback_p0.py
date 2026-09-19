#!/usr/bin/env python3
"""Devi feedback P0 receipt tables — Beta catalog only.

Creates empty append-only bzg_ops_receipt_* tables.
Does not grant permissions. Does not write Alchemist. Does not touch Production.
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

from core.uma_devi_p0 import ensure_receipt_schema  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"
MIGRATION_ID = "022_uma_devi_feedback_p0"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")


def stamp() -> str:
    return datetime.now(TZ8).strftime("%Y%m%d-%H%M%S")


def main() -> int:
    resolved = str(DB.resolve())
    for bad in FORBIDDEN:
        if bad in resolved:
            print(f"REFUSE {bad}")
            return 1
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"pre-uma-devi-feedback-p0-{stamp()}.sqlite"
    shutil.copy2(DB, dest)
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    print(f"BACKUP={dest}")
    print(f"SHA256={digest}")
    conn = sqlite3.connect(str(DB))
    try:
        ensure_receipt_schema(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
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
            (
                MIGRATION_ID,
                datetime.now(TZ8).isoformat(timespec="seconds"),
                "append-only receipt tables; no permission grants; no Alchemist writes",
            ),
        )
        conn.commit()
        n_events = conn.execute("SELECT COUNT(*) FROM bzg_ops_receipt_events").fetchone()[0]
        n_lines = conn.execute("SELECT COUNT(*) FROM bzg_ops_receipt_lines").fetchone()[0]
        pay = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions rp
            JOIN org_permissions p ON p.permission_id = rp.permission_id
            WHERE rp.role_id='ROLE-BZG-HFB' AND p.code='bzg.pr.payment_approve'
            """
        ).fetchone()[0]
        receive = conn.execute(
            "SELECT COUNT(*) FROM org_permissions WHERE code='venue.receive'"
        ).fetchone()[0]
        print(f"receipt_events={n_events}")
        print(f"receipt_lines={n_lines}")
        print(f"hfb_payment_approve_grants={pay}")
        print(f"venue_receive_permissions={receive}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
