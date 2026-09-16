#!/usr/bin/env python3
"""Phase 2.5A — data-driven permission matrix (emails as subjects).

Idempotent. Does NOT delete content_plans / test fixtures.
Removes can_create_plan from Haikal + Misa; grants full matrix per role.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DB = Path("/Users/wolfterminal/beta-os/catalog/content_library.sqlite")
TZ = ZoneInfo("Asia/Makassar")

ALL_PERMS = (
    "can_create_plan",
    "can_edit_plan",
    "can_approve_plan",
    "can_view_plan",
    "can_update_production",
    "can_upload",
    "can_use_wolf_intelligence",
)

# Matt + Amanda: full set including can_create_plan
MANAGEMENT = (
    "mrwolf@wolfcommand.net",
    "amanda@wolfcommand.net",
)

# Haikal + Misa: everything EXCEPT can_create_plan
TEAM = (
    "haikalqilbari123@gmail.com",
    "mlsary111@gmail.com",
)

TEAM_PERMS = tuple(p for p in ALL_PERMS if p != "can_create_plan")


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def grant(conn: sqlite3.Connection, subject: str, permission: str, ts: str) -> None:
    exists = conn.execute(
        """
        SELECT 1 FROM permissions
        WHERE lower(subject)=lower(?) AND permission=? AND ifnull(brand_id,'')=''
        """,
        (subject, permission),
    ).fetchone()
    if exists:
        return
    conn.execute(
        """
        INSERT INTO permissions (subject, permission, brand_id, granted_at, granted_by)
        VALUES (?, ?, NULL, ?, 'phase2-5a-seed')
        """,
        (subject, permission, ts),
    )


def revoke(conn: sqlite3.Connection, subject: str, permission: str) -> int:
    cur = conn.execute(
        """
        DELETE FROM permissions
        WHERE lower(subject)=lower(?) AND permission=? AND ifnull(brand_id,'')=''
        """,
        (subject, permission),
    )
    return cur.rowcount


def main() -> int:
    ts = now_iso()
    conn = sqlite3.connect(str(DB))
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        # Management: full matrix
        for subj in MANAGEMENT:
            for perm in ALL_PERMS:
                grant(conn, subj, perm, ts)
        # Team: all except create; explicitly remove create if present
        for subj in TEAM:
            removed = revoke(conn, subj, "can_create_plan")
            print(f"revoked can_create_plan from {subj}: {removed}")
            for perm in TEAM_PERMS:
                grant(conn, subj, perm, ts)
        conn.commit()
        print("--- permissions matrix ---")
        rows = conn.execute(
            """
            SELECT subject, permission FROM permissions
            ORDER BY subject, permission
            """
        ).fetchall()
        for s, p in rows:
            print(f"{s}\t{p}")
        print(f"total_rows={len(rows)}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
