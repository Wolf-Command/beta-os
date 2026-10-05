#!/usr/bin/env python3
"""022 Progress Dashboard — Matt-only progress.read permission (Beta).

Idempotent. No schema tables beyond org_permissions grant.
No Habitat / Uma / ESB / Metricool mutations.
"""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "catalog" / "content_library.sqlite"
MIGRATION_ID = "022_progress_dashboard"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))
BACKUP_DIR = ROOT / "catalog" / "backups"

# Owner P0 5 Oct 2026: retention/free-space guard (docs/BACKUP-RETENTION.md)
import sys as _bp_sys  # noqa: E402
if str(ROOT / "scripts") not in _bp_sys.path:
    _bp_sys.path.insert(0, str(ROOT / "scripts"))
from core.backup_policy import premig_backup  # noqa: E402
STATE_DIR = ROOT / "state"

PERM_ID = "PERM-PROGRESS-READ"
PERM_CODE = "progress.read"
ROLE_MATT = "ROLE-MATT"


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

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    ts = now_iso()
    bak = BACKUP_DIR / f"pre-progress-dashboard-{stamp()}.sqlite"
    bak = premig_backup(db_path, bak)
    digest = _sha256(bak)
    sha_path = STATE_DIR / f"progress-dashboard-backup-{bak.stem.replace('pre-progress-dashboard-', '')}.sha256"
    sha_path.write_text(digest + "\n", encoding="utf-8")
    print(f"backup={bak}")
    print(f"sha256={digest}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET
              code=excluded.code,
              resource=excluded.resource,
              action=excluded.action,
              description=excluded.description,
              status=excluded.status,
              updated_at=excluded.updated_at
            """,
            (
                PERM_ID,
                PERM_CODE,
                "progress",
                "read",
                "Read Matt Progress Dashboard (Owner / PERS-MATT only)",
                ts,
                ts,
            ),
        )
        conn.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET
              effect=excluded.effect,
              updated_at=excluded.updated_at
            """,
            (ROLE_MATT, PERM_ID, ts, ts),
        )
        conn.execute(
            """
            DELETE FROM org_role_permissions
            WHERE permission_id=? AND role_id != ?
            """,
            (PERM_ID, ROLE_MATT),
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        matt_grant = conn.execute(
            """
            SELECT effect FROM org_role_permissions
            WHERE role_id=? AND permission_id=?
            """,
            (ROLE_MATT, PERM_ID),
        ).fetchone()
        other = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions
            WHERE permission_id=? AND role_id != ?
            """,
            (PERM_ID, ROLE_MATT),
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (
                MIGRATION_ID,
                ts,
                (
                    f"progress.read → {ROLE_MATT}; "
                    f"matt_grant={matt_grant[0] if matt_grant else None}; "
                    f"other_grants={other}"
                ),
            ),
        )
        conn.commit()
        print(f"  {PERM_CODE} → {ROLE_MATT} effect={matt_grant[0] if matt_grant else None}")
        print(f"  other_role_grants={other}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        if other != 0 or not matt_grant or matt_grant[0] != "ALLOW":
            return 2
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
