#!/usr/bin/env python3
"""Beta Ads Studio — LEARN-only READ surface.

REFUSE Meta/Google spend/publish/boost. No Marketing API calls.
staff_ready=false. Beta only.
"""
from __future__ import annotations
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))
WS = Path.home() / ".openclaw/workspace/wolf-system"
DEFAULT_HTML = WS / "dashboards/ads-studio.html"
DEFAULT_PY = WS / "dashboards/content_ads_studio.py"
DEFAULT_BRIEFS = [
    WS / "briefs/2026-09-09-ads-studio-nolive.md",
    WS / "briefs/2026-09-09-ads-studio-phase0.md",
]
HTML_PATH = Path(os.environ.get("BETA_ADS_HTML", str(DEFAULT_HTML)))

def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")

def _stamp(ok: bool, reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "ok": ok, "reason": reason, "staff_ready": False,
        "claim": "NOT_REBUILT_PLUS_PROVEN", "migration_state": "PARTIAL",
        "read_only": True, "mode": "LEARN_ONLY",
        "meta_api": False, "google_ads_api": False, "spend": False,
        "publish": False, "boost": False, "as_of_wita": _now_wita(),
        "surface": "ads_studio",
    }
    out.update(extra)
    return out

def load_ads_studio_ro() -> dict[str, Any]:
    html_ok = HTML_PATH.is_file()
    py_path = Path(os.environ.get("BETA_ADS_PY", str(DEFAULT_PY)))
    briefs = []
    for b in DEFAULT_BRIEFS:
        if b.is_file():
            try:
                txt = b.read_text(encoding="utf-8", errors="replace")
                briefs.append({"name": b.name, "bytes": len(txt),
                               "excerpt": "\n".join(txt.splitlines()[:24])})
            except OSError as e:
                briefs.append({"name": b.name, "error": str(e)})
        else:
            briefs.append({"name": b.name, "present": False})
    assets = []
    for rel in ("dashboards/assets/ads-studio.js", "dashboards/assets/ads-studio.css"):
        p = WS / rel
        assets.append({"path": rel, "present": p.is_file(),
                       "bytes": (p.stat().st_size if p.is_file() else None)})
    ok = html_ok or any(b.get("bytes") for b in briefs if "bytes" in b)
    return _stamp(
        ok, "V1_RO_OK" if ok else "NO_SOT_YET",
        provenance={"html": str(HTML_PATH), "py": str(py_path)},
        html_present=html_ok,
        html_bytes=(HTML_PATH.stat().st_size if html_ok else None),
        py_present=py_path.is_file(),
        briefs=briefs, assets=assets,
        refuse=["Meta Graph/Marketing API", "Google Ads client", "spend", "publish", "boost"],
        banner="Ads Studio LEARN-only RO. Spend/publish connectors intentionally ABSENT.",
    )

if __name__ == "__main__":
    import json
    print(json.dumps(load_ads_studio_ro(), indent=2)[:2000])
