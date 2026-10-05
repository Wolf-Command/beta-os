#!/usr/bin/env python3
"""HEAD-CHEF-REVOKE-WORK-UPDATE-1 — Remove work.update from ROLE-BZG-HEAD-CHEF.

Head Chef must not pass uma_ops_console cash gates (opening float, petty count).
Targeted DELETE only — no catalog backup/copy. Beta catalog only.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

DB = ROOT / "catalog" / "content_library.sqlite"
MIGRATION_ID = "headchef_revoke_work_update_20261004"
ROLE = "ROLE-BZG-HEAD-CHEF"
PERM_CODE = "work.update"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def _refuse_path(db_path: Path) -> str | None:
    s = str(db_path.resolve())
    for frag in FORBIDDEN:
        if frag in s:
            return frag
    if "beta-os" not in s:
        return "not-beta-os"
    return None


def run(db_path: Path | None = None) -> dict:
    path = Path(db_path) if db_path else DB
    bad = _refuse_path(path)
    if bad:
        raise RuntimeError(f"REFUSE: {bad} in {path}")

    ts = now_iso()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        perm = conn.execute(
            "SELECT permission_id FROM org_permissions WHERE code=? AND status='ACTIVE'",
            (PERM_CODE,),
        ).fetchone()
        if not perm:
            raise RuntimeError(f"REFUSE: missing ACTIVE permission {PERM_CODE}")

        before = conn.execute(
            """
            SELECT effect FROM org_role_permissions
            WHERE role_id=? AND permission_id=?
            """,
            (ROLE, perm["permission_id"]),
        ).fetchone()

        deleted = 0
        if before is not None:
            cur = conn.execute(
                """
                DELETE FROM org_role_permissions
                WHERE role_id=? AND permission_id=?
                """,
                (ROLE, perm["permission_id"]),
            )
            deleted = int(cur.rowcount or 0)

        after = conn.execute(
            """
            SELECT effect FROM org_role_permissions
            WHERE role_id=? AND permission_id=?
            """,
            (ROLE, perm["permission_id"]),
        ).fetchone()

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
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (
                MIGRATION_ID,
                ts,
                f"Revoke {PERM_CODE} from {ROLE} (cash-control leak)",
            ),
        )
        conn.commit()

        return {
            "migration_id": MIGRATION_ID,
            "role_id": ROLE,
            "permission_code": PERM_CODE,
            "had_grant_before": before is not None,
            "rows_deleted": deleted,
            "grant_after": after is not None,
            "ran_at": ts,
        }
    finally:
        conn.close()


def main() -> int:
    try:
        report = run()
        print(json.dumps(report, indent=2))
        if report.get("grant_after"):
            print("FAIL: grant still present", file=sys.stderr)
            return 1
        print("RESULT: PASS")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
