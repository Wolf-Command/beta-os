#!/usr/bin/env python3
"""FC-BZG-RECEIVE-EVIDENCE-1 migration — schema + receive photo proposals."""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core import bzg_evidence_link1 as evlink  # noqa: E402
from core import bzg_history_import1 as hist  # noqa: E402
from core import bzg_receive_evidence1 as recv  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"
TZ8 = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(TZ8).strftime("%Y%m%d-%H%M%S")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _counts(conn: sqlite3.Connection) -> dict[str, Any]:
    conn.row_factory = sqlite3.Row
    out: dict[str, Any] = {}
    out["unlinked_total"] = int(conn.execute("SELECT COUNT(*) FROM bzg_ops_evidence_unlinked").fetchone()[0])
    out["unlinked_receive"] = int(
        conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_evidence_unlinked WHERE file_kind='receive'"
        ).fetchone()[0]
    )
    out["links"] = int(conn.execute("SELECT COUNT(*) FROM bzg_ops_evidence_links").fetchone()[0])
    out["recon_queue"] = int(conn.execute("SELECT COUNT(*) FROM bzg_ops_evidence_recon_queue").fetchone()[0])
    out.update(recv.queue_counts(conn))
    return out


def run(db_path: Path | None = None) -> dict[str, Any]:
    path = Path(db_path) if db_path else DB
    ts = now_iso()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bak = BACKUP_DIR / f"pre-fc-bzg-receive-evidence1-{stamp()}.sqlite"
    shutil.copy2(path, bak)
    digest = _sha256(bak)

    ro = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    ro.row_factory = sqlite3.Row
    before = _counts(ro)
    protected_before = hist.protected_close_checksums(ro)
    petty_before = hist.petty_balance(ro)
    ro.close()

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        recv.ensure_receive_review_schema(conn)
        apply_result = recv.propose_receive_evidence(conn, commit=True)
        after = _counts(conn)
        protected_after = hist.protected_close_checksums(conn)
        petty_after = hist.petty_balance(conn)
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
                recv.MIGRATION_ID,
                ts,
                f"{recv.PACK}; proposed={after.get('proposed', 0)}",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "pack": recv.PACK,
        "migration": "scripts/migrations/migrate_fc_bzg_receive_evidence1_20261005.py",
        "backup": str(bak),
        "backup_sha256": digest,
        "counts_before": before,
        "counts_after": after,
        "apply_result": apply_result,
        "precision_sample": recv.precision_sample(
            sqlite3.connect(f"file:{path}?mode=ro", uri=True), n=20
        ),
        "protected_closes_unchanged": protected_before == protected_after,
        "petty_balance_before": petty_before,
        "petty_balance_after": petty_after,
        "finished_at": ts,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
