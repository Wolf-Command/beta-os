#!/usr/bin/env python3
"""Beta Habitat Investment 2026 — READ-ONLY extract from V1 static HTML SoT.

Fail-closed. Do NOT invent financials/IRR/unit prices.
staff_ready=false. NOT REBUILT+PROVEN. Beta only — never prod :8787.
"""
from __future__ import annotations
import os, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))
DEFAULT_HTML = Path.home() / ".openclaw/workspace/wolf-system/dashboards/habitat-investment-2026.html"
HTML_PATH = Path(os.environ.get("BETA_HABITAT_HTML", str(DEFAULT_HTML)))

def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")

def _stamp(ok: bool, reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "ok": ok, "reason": reason, "staff_ready": False,
        "claim": "NOT_REBUILT_PLUS_PROVEN", "migration_state": "PARTIAL",
        "read_only": True, "invent_financials": False, "as_of_wita": _now_wita(),
        "surface": "habitat_investment_2026",
    }
    out.update(extra)
    return out

def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", " ", s)
def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", _strip_tags(s)).strip()

def load_habitat_investment_ro() -> dict[str, Any]:
    prov = {"html_path": str(HTML_PATH), "sot_kind": "STATIC_HTML_REPORT"}
    if not HTML_PATH.is_file():
        return _stamp(False, "NO_SOT_YET", provenance=prov, title=None, sections=[],
                      banner="V1 habitat-investment-2026.html missing; no invented investment numbers.")
    try:
        text = HTML_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return _stamp(False, "READ_ERROR", provenance=prov, error=str(e))
    title_m = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    h1s = [_clean(x) for x in re.findall(r"<h1[^>]*>(.*?)</h1>", text, re.I | re.S)]
    h2s = [_clean(x) for x in re.findall(r"<h2[^>]*>(.*?)</h2>", text, re.I | re.S)]
    mailto = re.findall(r"mailto:([^\"]+)", text)
    phones = re.findall(r"\+62[\d\s]{8,}", text)
    sites = re.findall(r"https?://thehabitatlombok\.com", text)
    assets = sorted(set(re.findall(r"/assets/habitat-investment/[a-zA-Z0-9._-]+", text)))
    # Money-like strings as *quoted excerpts only* — not computed valuations
    money_excerpts = [_clean(m) for m in re.findall(
        r"(?:IDR|USD|Rp)\s*[\d.,]+(?:\s*(?:jt|juta|million|m))?", text, re.I)][:20]
    return _stamp(
        True, "V1_RO_OK",
        provenance=prov,
        title=_clean(title_m.group(1)) if title_m else (h1s[0] if h1s else None),
        h1=h1s[:8],
        sections=h2s[:24],
        contact={"emails": mailto[:3], "phones": [p.strip() for p in phones[:3]],
                 "sites": list(dict.fromkeys(sites))[:3]},
        asset_refs=assets[:20],
        money_excerpts_quoted=money_excerpts,
        money_note="Excerpts from static HTML only — not live valuations; do not invent IRR/unit book",
        html_bytes=len(text.encode("utf-8", errors="replace")),
        banner="Habitat Investment 2026 report RO from V1 HTML SoT. No invent financials.",
    )

if __name__ == "__main__":
    import json
    print(json.dumps(load_habitat_investment_ro(), indent=2)[:2000])
