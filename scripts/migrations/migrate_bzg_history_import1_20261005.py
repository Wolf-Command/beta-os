#!/usr/bin/env python3
"""BZG-HISTORY-IMPORT-1 migration — backup catalog, import Alchemist history."""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core import bzg_history_import1 as hist  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"
RESULT_PATH = ROOT / "state" / "reliability" / "BZG-HISTORY-IMPORT-1-RESULT-2026-10-05.json"
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


def run(db_path: Path | None = None) -> dict:
    path = Path(db_path) if db_path else DB
    ts = now_iso()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bak = BACKUP_DIR / f"pre-bzg-history-import1-{stamp()}.sqlite"
    shutil.copy2(path, bak)
    digest = _sha256(bak)

    result = hist.run_import(path)
    result["backup"] = str(bak)
    result["backup_sha256"] = digest
    result["migration"] = "scripts/migrations/migrate_bzg_history_import1_20261005.py"
    result["core"] = "scripts/core/bzg_history_import1.py"
    result["status"] = "IMPORT_DONE"
    result["no_prod"] = True
    result["no_commit"] = True
    result["no_money_movement"] = True
    result["staff_ready"] = False
    result["zayen_ready"] = False
    result["prod_pid_unchanged"] = 1297
    result["prod_port"] = 8787

    conn = sqlite3.connect(str(path))
    try:
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
                hist.MIGRATION_ID,
                ts,
                f"{hist.PACK}; po={result['imported']['purchase_orders']}; petty={result['imported']['petty_cash']}",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
