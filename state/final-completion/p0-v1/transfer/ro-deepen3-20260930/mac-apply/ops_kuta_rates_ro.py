#!/usr/bin/env python3
"""Beta Kuta / competitor rates — READ-ONLY from V1 status+brief+DB.

Honesty: competitor_rates and rate_signals may be EMPTY — do not invent.
atrium_rates RO counts/recent only. No booking. No Telegram. No approval write.
staff_ready=false. Beta only.
"""
from __future__ import annotations
import json, os, sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))
WS = Path.home() / ".openclaw/workspace/wolf-system"
DEFAULT_STATUS = WS / "dashboards/data/kuta-rates.status.json"
DEFAULT_BRIEF_DIR = WS / "dashboards/data"
DEFAULT_DB = Path.home() / ".openclaw/data/competitor-rates.db"
STATUS_PATH = Path(os.environ.get("BETA_KUTA_STATUS", str(DEFAULT_STATUS)))
BRIEF_DIR = Path(os.environ.get("BETA_KUTA_BRIEF_DIR", str(DEFAULT_BRIEF_DIR)))
DB_PATH = Path(os.environ.get("BETA_COMPETITOR_RATES_DB", str(DEFAULT_DB)))

def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")

def _stamp(ok: bool, reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "ok": ok, "reason": reason, "staff_ready": False,
        "claim": "NOT_REBUILT_PLUS_PROVEN", "migration_state": "PARTIAL",
        "read_only": True, "live_booking": False, "telegram_send": False,
        "as_of_wita": _now_wita(), "surface": "kuta_rates",
    }
    out.update(extra)
    return out

def _latest_brief() -> dict[str, Any]:
    if not BRIEF_DIR.is_dir():
        return {"brief_status": "MISSING_DIR", "path": None, "excerpt": None}
    briefs = sorted(BRIEF_DIR.glob("kuta-rates-brief-20*.md"))
    # prefer non-block
    briefs = [b for b in briefs if "block" not in b.name] or briefs
    if not briefs:
        return {"brief_status": "NONE", "path": None, "excerpt": None}
    p = briefs[-1]
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"brief_status": "READ_ERROR", "path": str(p), "error": str(e), "excerpt": None}
    return {"brief_status": "PRESENT", "path": str(p), "name": p.name,
            "excerpt": "\n".join(txt.splitlines()[:18]), "bytes": len(txt)}

def _db_ro() -> dict[str, Any]:
    if not DB_PATH.is_file():
        return {"db_status": "MISSING", "path": str(DB_PATH), "table_counts": {}}
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5.0)
    except sqlite3.Error as e:
        return {"db_status": "ERROR", "path": str(DB_PATH), "error": str(e), "table_counts": {}}
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
        counts = {}
        for t in tables:
            try:
                counts[t] = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
            except sqlite3.Error:
                counts[t] = None
        atrium_recent = []
        if "atrium_rates" in tables:
            try:
                rows = conn.execute(
                    "SELECT scrape_date, stay_date, room_name, rate, currency "
                    "FROM atrium_rates ORDER BY scrape_date DESC, stay_date DESC LIMIT 8"
                ).fetchall()
                atrium_recent = [
                    {"scrape_date": a, "stay_date": b, "room_name": c, "rate": d, "currency": e}
                    for a, b, c, d, e in rows
                ]
            except sqlite3.Error as e:
                atrium_recent = [{"error": str(e)}]
        return {
            "db_status": "PRESENT", "path": str(DB_PATH), "open_mode": "ro",
            "table_counts": counts,
            "competitor_rates_empty": counts.get("competitor_rates") == 0,
            "rate_signals_empty": counts.get("rate_signals") == 0,
            "atrium_recent": atrium_recent,
            "honesty": "Empty competitor_rates/rate_signals reported honestly — no invented rows",
        }
    finally:
        conn.close()

def load_kuta_rates_ro() -> dict[str, Any]:
    status = None
    status_err = None
    if STATUS_PATH.is_file():
        try:
            status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            status_err = str(e)
    else:
        status_err = "status json missing"
    brief = _latest_brief()
    db = _db_ro()
    ok = status is not None or brief.get("brief_status") == "PRESENT" or db.get("db_status") == "PRESENT"
    reason = "V1_RO_OK" if ok else "NO_SOT_YET"
    return _stamp(
        ok, reason,
        provenance={"status_path": str(STATUS_PATH), "brief_dir": str(BRIEF_DIR), "db_path": str(DB_PATH)},
        status=status, status_error=status_err, brief=brief, db=db,
        banner="Kuta rates RO: status+brief+DB counts. LEARN/intel only. Nobody books from here.",
    )

if __name__ == "__main__":
    import json as _j
    print(_j.dumps(load_kuta_rates_ro(), indent=2)[:2500])
