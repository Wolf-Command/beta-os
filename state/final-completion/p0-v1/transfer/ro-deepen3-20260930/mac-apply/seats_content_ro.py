#!/usr/bin/env python3
"""Beta Content seats — READ-ONLY glance (desk/admin).

No Metricool mutate. No Canva mutate. No NAS destroy.
Probes existing CE/library paths fail-closed. staff_ready=false.
"""
from __future__ import annotations
import json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))
WS = Path.home() / ".openclaw/workspace/wolf-system"
BETA = Path.home() / "beta-os"
DEFAULT_LIBRARY_CANDIDATES = [
    Path.home() / ".openclaw/data/wolf-catalogue.sqlite",
    BETA / "data/content_library.sqlite",
    BETA / "state/content_library.sqlite",
]
NAS_GLANCE_MARKERS = [
    Path("/Volumes/Wolf-Library"),
    Path("/Volumes/homes"),
    Path.home() / "Library/CloudStorage",  # presence only, not walk
]

def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")

def _stamp(ok: bool, reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "ok": ok, "reason": reason, "staff_ready": False,
        "claim": "NOT_REBUILT_PLUS_PROVEN", "migration_state": "PARTIAL",
        "read_only": True, "metricool_mutate": False, "canva_mutate": False,
        "nas_destroy": False, "as_of_wita": _now_wita(), "surface": "content_seats",
    }
    out.update(extra)
    return out

def _probe_file(p: Path) -> dict[str, Any]:
    if not p.exists():
        return {"path": str(p), "present": False}
    try:
        st = p.stat()
        return {"path": str(p), "present": True, "is_dir": p.is_dir(),
                "bytes": (None if p.is_dir() else st.st_size)}
    except OSError as e:
        return {"path": str(p), "present": False, "error": str(e)}

def load_content_ro() -> dict[str, Any]:
    # V1 content board status-ish files if present
    v1_hints = []
    for rel in ("dashboards/data/content-board.jsonl",
                "dashboards/atlas.html",
                "dashboards/haikal-desk.html",
                "dashboards/misa.html"):
        v1_hints.append(_probe_file(WS / rel))
    libs = [_probe_file(p) for p in DEFAULT_LIBRARY_CANDIDATES]
    nas = [_probe_file(p) for p in NAS_GLANCE_MARKERS]
    # Metricool snapshots READ only (list names, no write)
    metricool = []
    data_dir = WS / "dashboards/data"
    if data_dir.is_dir():
        for p in sorted(data_dir.glob("metricool-*.json"))[:12]:
            metricool.append({"name": p.name, "bytes": p.stat().st_size})
    # Beta CE board presence
    ce_boards = [_probe_file(BETA / "dashboards" / n) for n in
                 ("content-2.0.html", "content-engine-live.html",
                  "seat-content-desk-1.html", "seat-content-admin-1.html")]
    any_ok = any(x.get("present") for x in libs + v1_hints + ce_boards) or bool(metricool)
    return _stamp(
        any_ok, "V1_RO_OK" if any_ok else "NO_SOT_YET",
        v1_hints=v1_hints, libraries=libs, nas_glance=nas,
        metricool_snapshots_ro=metricool,
        metricool_note="READ glance of snapshot filenames only — mutate FORBIDDEN",
        ce_boards=ce_boards,
        banner="Content seats RO glance. No Metricool/Canva mutate. Staff prove still required.",
        staff_prove_hint="SP-CONTENT-TEAM / Haikal",
    )

if __name__ == "__main__":
    import json as _j
    print(_j.dumps(load_content_ro(), indent=2)[:2500])
