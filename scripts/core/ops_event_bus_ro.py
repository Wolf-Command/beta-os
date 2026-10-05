#!/usr/bin/env python3
"""Beta Event Bus — READ-ONLY status from ~/.openclaw/state/event_bus.db.

No fake stream. sqlite mode=ro. staff_ready=false. Beta only.
"""
from __future__ import annotations
import os, sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))
DEFAULT_DB = Path.home() / ".openclaw/state/event_bus.db"
DB_PATH = Path(os.environ.get("BETA_EVENT_BUS_DB", str(DEFAULT_DB)))

def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")

def _stamp(ok: bool, reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "ok": ok, "reason": reason, "staff_ready": False,
        "claim": "NOT_REBUILT_PLUS_PROVEN", "migration_state": "PARTIAL",
        "read_only": True, "fake_stream": False, "as_of_wita": _now_wita(),
        "surface": "event_bus",
    }
    out.update(extra)
    return out

def load_event_bus_ro(sample_limit: int = 5) -> dict[str, Any]:
    prov = {"db_path": str(DB_PATH), "open_mode": "ro"}
    if not DB_PATH.is_file():
        return _stamp(False, "NO_SOT_YET", provenance=prov, tables=[],
                      banner="event_bus.db missing; no invented event stream.")
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        return _stamp(False, "READ_ERROR", provenance=prov, error=str(e))
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
        info = []
        for t in tables:
            try:
                n = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
            except sqlite3.Error:
                n = None
            cols = []
            try:
                cols = [c[1] for c in conn.execute(f"PRAGMA table_info([{t}])").fetchall()]
            except sqlite3.Error:
                pass
            sample = []
            if n and n > 0 and cols:
                # Prefer time-ish order if column exists
                order_col = next((c for c in ("created_at","ts","timestamp","at","id") if c in cols), cols[0])
                try:
                    rows = conn.execute(
                        f"SELECT * FROM [{t}] ORDER BY [{order_col}] DESC LIMIT ?",
                        (sample_limit,)).fetchall()
                    for row in rows:
                        d = {k: row[k] for k in row.keys()}
                        # truncate long values
                        sample.append({k: (str(v)[:200] if v is not None else None) for k, v in d.items()})
                except sqlite3.Error as e:
                    sample = [{"error": str(e)}]
            info.append({"table": t, "count": n, "columns": cols, "sample": sample})
        st = DB_PATH.stat()
        return _stamp(
            True, "V1_RO_OK", provenance=prov, tables=info,
            db_bytes=st.st_size,
            mtime_wita=datetime.fromtimestamp(st.st_mtime, WITA).strftime("%Y-%m-%dT%H:%M:%S%z"),
            banner="Event Bus RO status/read model. No fake live stream.",
        )
    finally:
        conn.close()

if __name__ == "__main__":
    import json
    print(json.dumps(load_event_bus_ro(), indent=2)[:2500])
