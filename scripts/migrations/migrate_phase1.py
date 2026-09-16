#!/usr/bin/env python3
"""Idempotent Phase 1 intelligence schema migration + seeds."""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DB = BETA_ROOT / "catalog" / "content_library.sqlite"
SQL_FILE = BETA_ROOT / "scripts" / "migrations" / "001_phase1_intelligence.sql"
TZ = ZoneInfo("Asia/Makassar")


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def main() -> int:
    if not DB.exists():
        print(f"DB missing: {DB}", file=sys.stderr)
        return 1
    sql = SQL_FILE.read_text(encoding="utf-8")
    conn = sqlite3.connect(str(DB))
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(sql)
        ts = now_iso()
        cadence = json.dumps({
            "fortnight_feed_target": 3,
            "fortnight_story_target": 14,
            "update_note": "Every Friday 09:00 WITA developer update (from brand kit)",
        })
        aliases = json.dumps(["Habitat", "Habitat-Villas", "Habitat Villas"])
        conn.execute(
            """
            INSERT INTO brands (id, display_name, aliases_json, cadence_json, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              display_name=excluded.display_name,
              aliases_json=excluded.aliases_json,
              cadence_json=excluded.cadence_json,
              updated_at=excluded.updated_at
            """,
            ("habitat", "Habitat / Habitat-Villas", aliases, cadence, ts, ts),
        )
        subjects = [
            "amanda@wolfcommand.net",
            "haikalqilbari123@gmail.com",
            "mlsary111@gmail.com",
            "mrwolf@wolfcommand.net",
        ]
        for subj in subjects:
            exists = conn.execute(
                "SELECT 1 FROM permissions WHERE subject=? AND permission=? AND ifnull(brand_id,'')=''",
                (subj, "can_create_plan"),
            ).fetchone()
            if not exists:
                conn.execute(
                    """
                    INSERT INTO permissions (subject, permission, brand_id, granted_at, granted_by)
                    VALUES (?, 'can_create_plan', NULL, ?, 'phase1-seed')
                    """,
                    (subj, ts),
                )
        conn.commit()
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        if ok != "ok":
            return 2
        for t in (
            "brands", "permissions", "memory_items", "evidence_items",
            "content_plans", "plan_revisions", "content_cards", "card_revisions", "skill_runs",
        ):
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"{t}: {n}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
