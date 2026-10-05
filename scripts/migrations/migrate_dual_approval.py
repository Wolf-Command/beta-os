#!/usr/bin/env python3
"""015 Dual Approval — idempotent Beta-only migration.

Adds required_decision_count to core_approval_requests (DEFAULT 1).
Unique index: one APPROVED decision per Person per request.
Live org_authority_limits must stay 0. No dual business policy seed.
Backs up Beta DB before apply and prints SHA-256.
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
SQL = Path(__file__).resolve().parent / "015_dual_approval.sql"
MIGRATION_ID = "015_dual_approval"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))
BACKUP_DIR = ROOT / "catalog" / "backups"

# Owner P0 5 Oct 2026: retention/free-space guard (docs/BACKUP-RETENTION.md)
import sys as _bp_sys  # noqa: E402
if str(ROOT / "scripts") not in _bp_sys.path:
    _bp_sys.path.insert(0, str(ROOT / "scripts"))
from core.backup_policy import premig_backup  # noqa: E402


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(TZ8).strftime("%Y%m%d-%H%M%S")


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _backup(db_path: Path) -> tuple[Path, str]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"pre-dual-approval-{stamp()}.sqlite"
    dest = premig_backup(db_path, dest)
    digest = _sha256(dest)
    sha_path = ROOT / "state" / f"dual-approval-backup-{dest.stem.replace('pre-dual-approval-', '')}.sha256"
    sha_path.parent.mkdir(parents=True, exist_ok=True)
    sha_path.write_text(f"{digest}  {dest.relative_to(ROOT)}\n", encoding="utf-8")
    print(f"BACKUP={dest}")
    print(f"SHA256={digest}")
    return dest, digest


def _ensure_required_decision_count(conn: sqlite3.Connection) -> bool:
    """Add column if missing. Returns True if column now present."""
    cols = _column_names(conn, "core_approval_requests")
    if "required_decision_count" in cols:
        # Backfill any NULL (should not happen with NOT NULL DEFAULT)
        conn.execute(
            """
            UPDATE core_approval_requests
            SET required_decision_count=1
            WHERE required_decision_count IS NULL OR required_decision_count < 1
            """
        )
        return True
    conn.execute(
        """
        ALTER TABLE core_approval_requests
        ADD COLUMN required_decision_count INTEGER NOT NULL DEFAULT 1
        """
    )
    return True


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
    # Backup only for live catalog path on first apply (not temp copies / re-runs)
    is_live = db_path == (ROOT / "catalog" / "content_library.sqlite").resolve()
    if is_live:
        probe = sqlite3.connect(str(db_path))
        try:
            tabs = {r[0] for r in probe.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            need_backup = True
            if "core_approval_requests" in tabs:
                cols = {r[1] for r in probe.execute("PRAGMA table_info(core_approval_requests)")}
                mig_done = probe.execute(
                    "SELECT 1 FROM schema_migrations WHERE id=? LIMIT 1",
                    (MIGRATION_ID,),
                ).fetchone() if "schema_migrations" in tabs else None
                if "required_decision_count" in cols and mig_done:
                    need_backup = False
            if need_backup:
                _backup(db_path)
        finally:
            probe.close()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        n_auth = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
        if n_auth != 0:
            print(
                f"REFUSE: live org_authority_limits must stay 0, got {n_auth}",
                file=sys.stderr,
            )
            return 2

        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "core_approval_requests" not in tabs:
            print("REFUSE: core_approval_requests missing (run 013 first)", file=sys.stderr)
            return 2
        if "core_approval_decisions" not in tabs:
            print("REFUSE: core_approval_decisions missing (run 013 first)", file=sys.stderr)
            return 2

        _ensure_required_decision_count(conn)
        print("required_decision_count column ensured")

        conn.executescript(SQL.read_text(encoding="utf-8"))
        print("DDL applied (unique index)")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        cols = _column_names(conn, "core_approval_requests")
        n_req = conn.execute("SELECT COUNT(*) FROM core_approval_requests").fetchone()[0]
        n_dec = conn.execute("SELECT COUNT(*) FROM core_approval_decisions").fetchone()[0]
        n_auth2 = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
        min_count = conn.execute(
            "SELECT MIN(required_decision_count) FROM core_approval_requests"
        ).fetchone()[0]
        idx = conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='index' AND name='idx_core_approval_dec_one_approve_per_person'
            """
        ).fetchone()
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (
                MIGRATION_ID,
                ts,
                (
                    f"Dual approval; requests={n_req}; decisions={n_dec}; "
                    f"auth_limits={n_auth2}; col={'required_decision_count' in cols}; "
                    f"min_count={min_count}; unique_idx={bool(idx)}; no live dual policy"
                ),
            ),
        )
        conn.commit()

        print(f"  core_approval_requests={n_req}")
        print(f"  core_approval_decisions={n_dec}")
        print(f"  org_authority_limits={n_auth2}")
        print(f"  required_decision_count_col={'required_decision_count' in cols}")
        print(f"  unique_approve_per_person_idx={bool(idx)}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        if "required_decision_count" not in cols:
            print("REFUSE: required_decision_count column missing", file=sys.stderr)
            return 2
        if n_auth2 != 0:
            print(
                f"REFUSE: live org_authority_limits must stay 0, got {n_auth2}",
                file=sys.stderr,
            )
            return 2
        if n_req > 0 and (min_count is None or int(min_count) < 1):
            print(
                f"REFUSE: required_decision_count must be >=1 for all rows, min={min_count}",
                file=sys.stderr,
            )
            return 2
        if not idx:
            print("REFUSE: unique approve-per-person index missing", file=sys.stderr)
            return 2
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
