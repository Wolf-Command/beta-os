#!/usr/bin/env python3
"""Beta Owner Travel — READ-ONLY V1 draft surface loader.

No booking. No spend. No hotel mail. Fail-closed.
staff_ready=false. NOT REBUILT+PROVEN.

Mount: GET /api/owner/travel-ro
Prod :8787 untouched.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))

DEFAULT_BOARD = Path.home() / ".openclaw/workspace/wolf-system/dashboards/travel.html"
BOARD_PATH = Path(os.environ.get("BETA_TRAVEL_BOARD", str(DEFAULT_BOARD)))


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")


def _stamp(ok: bool, reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "ok": ok,
        "reason": reason,
        "staff_ready": False,
        "live_booking": False,
        "claim": "NOT_REBUILT_PLUS_PROVEN",
        "migration_state": "PARTIAL",
        "read_only": True,
        "as_of_wita": _now_wita(),
        "honesty": "PARTIAL · draft only · nobody books from here · no spend",
    }
    out.update(extra)
    return out


def _extract_tiles(html: str) -> list[dict[str, Any]]:
    """Pull h3 section titles + short following paragraph snippet (no invent)."""
    tiles: list[dict[str, Any]] = []
    # Split on h3
    parts = re.split(r'<h3[^>]*>', html, flags=re.I)
    for part in parts[1:]:
        m = re.match(r'([^<]+)</h3>\s*(.*)', part, flags=re.S | re.I)
        if not m:
            continue
        title = re.sub(r'\s+', ' ', m.group(1)).strip()
        body = m.group(2)
        # stop at next major section-ish
        body = re.split(r'<h3\b|<h2\b', body, maxsplit=1, flags=re.I)[0]
        # first <p> text
        pm = re.search(r'<p[^>]*>(.*?)</p>', body, flags=re.S | re.I)
        snippet = ""
        if pm:
            snippet = re.sub(r'<[^>]+>', ' ', pm.group(1))
            snippet = re.sub(r'\s+', ' ', snippet).strip()[:280]
        # external links count (Accor / Google Flights) — names only
        links = re.findall(r'href="(https?://[^"]+)"', body)
        host_hint = []
        for u in links[:6]:
            if "accor" in u.lower():
                host_hint.append("accor")
            elif "google.com/travel" in u.lower() or "google.com/flights" in u.lower():
                host_hint.append("google_flights")
            elif "expedia" in u.lower() or "booking.com" in u.lower():
                host_hint.append("ota_link")
        tiles.append({
            "title": title,
            "snippet": snippet,
            "outbound_hints": sorted(set(host_hint)),
            "outbound_link_count": len(links),
        })
    return tiles


def load_travel_ro() -> dict[str, Any]:
    provenance = {"v1_board": str(BOARD_PATH), "booking_api": None}
    party = {
        "adults": 2,
        "kids_ages": [5, 7],
        "label": "Matthew + Amanda · 2 adults + kids 5 and 7",
    }
    law = [
        "Nobody books from here.",
        "No spend. No hotel mail.",
        "Draft / plan only — Peaches plans; Scout does not book.",
    ]

    if not BOARD_PATH.is_file():
        return _stamp(
            False,
            "NO_SOT_YET",
            surface="owner_travel",
            provenance=provenance,
            party=party,
            law=law,
            tiles=[],
            banner="V1 travel.html not found. No invented itinerary. No booking.",
            error="travel.html missing",
        )

    try:
        html = BOARD_PATH.read_text(encoding="utf-8")
    except OSError as e:
        return _stamp(
            False,
            "READ_ERROR",
            surface="owner_travel",
            provenance=provenance,
            party=party,
            law=law,
            tiles=[],
            banner="Could not read V1 travel board.",
            error=str(e),
        )

    tiles = _extract_tiles(html)
    # Banner / party from V1 if present
    if "Matthew and Amanda" in html or "2 adults" in html:
        party["sourced_from_v1"] = True

    return _stamp(
        True,
        "V1_RO_OK",
        surface="owner_travel",
        provenance=provenance,
        party=party,
        law=law,
        tiles=tiles,
        board_bytes=len(html.encode("utf-8")),
        banner="Draft only. Nobody books from here. Read-only V1 mirror. No booking API.",
        ui_hints={"sections": ["honesty", "party", "tiles"], "booking": False},
    )


def as_json_bytes(payload: dict[str, Any] | None = None) -> bytes:
    import json
    data = payload if payload is not None else load_travel_ro()
    return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")


if __name__ == "__main__":
    print(as_json_bytes().decode("utf-8"))
