#!/usr/bin/env python3
"""Beta Gatekeeper — READ-ONLY daily MD vault glance.

No outbound automation. staff_ready=false. Beta only.
"""
from __future__ import annotations
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))
DEFAULT_GK = Path.home() / "WolfCommandSystem/WolfCommand/01-Wolf-Command/Gatekeeper"
GK_PATH = Path(os.environ.get("BETA_GATEKEEPER_DIR", str(DEFAULT_GK)))

def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")

def _stamp(ok: bool, reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "ok": ok, "reason": reason, "staff_ready": False,
        "claim": "NOT_REBUILT_PLUS_PROVEN", "migration_state": "PARTIAL",
        "read_only": True, "outbound_send": False, "as_of_wita": _now_wita(),
        "surface": "gatekeeper",
    }
    out.update(extra)
    return out

def load_gatekeeper_ro(recent_limit: int = 12) -> dict[str, Any]:
    prov = {"dir": str(GK_PATH)}
    if not GK_PATH.is_dir():
        return _stamp(False, "NO_SOT_YET", provenance=prov, entries=[], latest=None,
                      banner="Gatekeeper vault missing; no invented daily logs.")
    mds = sorted([p for p in GK_PATH.glob("20*.md") if p.is_file()])
    others = sorted([p.name for p in GK_PATH.iterdir() if p.is_file() and not p.name.startswith("20")])
    recent = [{"name": p.name, "bytes": p.stat().st_size,
               "mtime_wita": datetime.fromtimestamp(p.stat().st_mtime, WITA).strftime("%Y-%m-%dT%H:%M:%S%z")}
              for p in mds[-recent_limit:]]
    latest = None
    if mds:
        p = mds[-1]
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
            latest = {"name": p.name, "bytes": len(txt),
                      "excerpt": "\n".join(txt.splitlines()[:40])}
        except OSError as e:
            latest = {"name": p.name, "error": str(e)}
    return _stamp(
        True, "V1_RO_OK", provenance=prov,
        daily_md_count=len(mds), other_files=others[:30], recent_daily=recent,
        latest=latest,
        banner="Gatekeeper daily vault RO. Display only — no outbound send.",
    )

if __name__ == "__main__":
    import json
    print(json.dumps(load_gatekeeper_ro(), indent=2)[:2000])
