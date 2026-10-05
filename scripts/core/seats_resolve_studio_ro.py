#!/usr/bin/env python3
"""Beta Resolve Studio — READ-ONLY projects/reviews from V1 resolve-studio.

No mutate. staff_ready=false. Beta only.
"""
from __future__ import annotations
import json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))
DEFAULT_ROOT = Path.home() / ".openclaw/workspace/wolf-system/resolve-studio"
ROOT = Path(os.environ.get("BETA_RESOLVE_STUDIO", str(DEFAULT_ROOT)))

def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")

def _stamp(ok: bool, reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "ok": ok, "reason": reason, "staff_ready": False,
        "claim": "NOT_REBUILT_PLUS_PROVEN", "migration_state": "PARTIAL",
        "read_only": True, "as_of_wita": _now_wita(), "surface": "resolve_studio",
    }
    out.update(extra)
    return out

def load_resolve_studio_ro() -> dict[str, Any]:
    prov = {"root": str(ROOT)}
    if not ROOT.is_dir():
        return _stamp(False, "NO_SOT_YET", provenance=prov,
                      banner="resolve-studio missing; no invented projects.")
    studio = None
    reviews = None
    readme = None
    sp, rp = ROOT / "studio.json", ROOT / "reviews.json"
    try:
        if sp.is_file():
            studio = json.loads(sp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        studio = {"error": str(e)}
    try:
        if rp.is_file():
            reviews = json.loads(rp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        reviews = {"error": str(e)}
    rm = ROOT / "READ-ME-FIRST.txt"
    if rm.is_file():
        try:
            readme = rm.read_text(encoding="utf-8", errors="replace")[:800]
        except OSError as e:
            readme = f"error:{e}"
    projects = []
    proj_dir = ROOT / "projects"
    if proj_dir.is_dir():
        for p in sorted(proj_dir.iterdir())[:40]:
            projects.append({"name": p.name, "is_dir": p.is_dir(),
                             "bytes": (None if p.is_dir() else p.stat().st_size)})
    return _stamp(
        True, "V1_RO_OK", provenance=prov,
        studio=studio, reviews=reviews, readme_excerpt=readme,
        projects=projects, project_count=len(projects),
        banner="Resolve Studio RO. No project mutate.",
    )

if __name__ == "__main__":
    import json as _j
    print(_j.dumps(load_resolve_studio_ro(), indent=2)[:2000])
