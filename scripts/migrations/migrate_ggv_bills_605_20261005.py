#!/usr/bin/env python3
"""GGV-BILLS-605 — import money.sqlite bills into Beta catalog ggv_bills.

Decision served: GGV-BILLS-605 (2026-10-05).
Beta only. Read-only source. Idempotent. staff_ready stays false.
"""
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

from core import ggv_bills_import1 as bills  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"
RESULT_DIR = ROOT / "state" / "reliability"
MIGRATION_ID = bills.MIGRATION_ID
PACK = bills.PACK
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")


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
    text = str(db_path.resolve())
    for frag in FORBIDDEN:
        if frag in text:
            return frag
    if "beta-os" not in text:
        return "not-beta-os"
    return None


def run(db_path: Path | None = None) -> dict:
    path = Path(db_path) if db_path else DB
    bad = _refuse_path(path)
    if bad:
        raise RuntimeError(f"REFUSE: {bad} in {path}")

    ts = now_iso()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bak = BACKUP_DIR / f"pre-ggv-bills-605-{stamp()}.sqlite"
    shutil.copy2(path, bak)
    digest = _sha256(bak)

    result = bills.run_import(path)
    result["backup"] = str(bak)
    result["backup_sha256"] = digest
    result["ran_at"] = ts

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
                MIGRATION_ID,
                ts,
                f"{PACK}; bills={result['bills']['imported']}; skipped={result['bills']['skipped']}",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    return result


def main() -> int:
    try:
        out = run()
        print(json.dumps(out, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
