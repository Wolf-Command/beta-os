#!/usr/bin/env python3
"""GGV-FINANCE-CORE-1 — one-time propose_matches backfill with commit.

Runs audited backfill once at deploy; must not run on every page load.
Decision served: GGV-FINANCE-CORE-1 fix round (2026-10-06).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core import ggv_bank_statement1 as gbs  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
MIGRATION_ID = "ggv_bank_recon_backfill_20261006"
TZ8 = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def run(db_path: Path | None = None) -> dict:
    path = Path(db_path) if db_path else DB
    import sqlite3

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        gbs.ensure_schema(conn, run_backfill=False)
        result = gbs.maybe_backfill_propose_matches(conn, commit=True)
        conn.commit()
        out = {
            "ok": True,
            "migration_id": MIGRATION_ID,
            "ran_at": now_iso(),
            "result": result,
        }
        (ROOT / "state" / "reliability").mkdir(parents=True, exist_ok=True)
        (
            ROOT / "state" / "reliability" / f"{MIGRATION_ID}-RESULT.json"
        ).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        return out
    finally:
        conn.close()


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
