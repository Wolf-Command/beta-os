#!/usr/bin/env python3
"""Pack 7 — AMG guest stay honesty. Read only.

Inventory+RoomInfo stays the live vacant-versus-rooms read. A single cafe
row in reservations.db is not an Atrium stay book and is not "no guests".
Pre-arrival and post-stay stay unavailable. Housekeeping is a later pack.
Bookings write stays off.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from core.amg_sales_desk_ro import _occupancy, _v1_master_atrium
from core.yanolja_last_read_ro import guest_depth_honesty, load_last_read, occupancy_from_last

RESERVATIONS = Path("/Users/wolfterminal/.openclaw/workspace/wolf-system/state/reservations.db")
N8N_PRE = Path("/Users/wolfterminal/.openclaw/workspace/wolf-system/n8n-templates/02-amg-pre-arrival.json")
N8N_POST = Path("/Users/wolfterminal/.openclaw/workspace/wolf-system/n8n-templates/05-amg-post-stay-review.json")
SALES_OCC = "/amg/sales-desk#occ"


def _template(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.is_file(),
        "operating": False,
    }


def _endpoint(name: str) -> dict[str, Any]:
    last = load_last_read()
    ends = last.get("endpoints") if isinstance(last.get("endpoints"), dict) else {}
    block = ends.get(name) if isinstance(ends, dict) else None
    if not isinstance(block, dict):
        return {
            "name": name,
            "present": False,
            "ok": False,
            "row_count": None,
            "means_no_guests": False,
            "state": "UNAVAILABLE",
            "why": f"{name} is not in the Yanolja last-read.",
        }
    row_count = block.get("row_count")
    denied = bool(block.get("denied"))
    ok = bool(block.get("ok"))
    if denied:
        state = "UNAVAILABLE"
        why = "Endpoint denied. No guest rows were read."
    elif ok and isinstance(row_count, int):
        state = "LIVE"
        why = "Endpoint returned an integer row count. That count is not an invented guest list."
    else:
        state = "UNAVAILABLE"
        why = "Endpoint did not return a guest row count. Null is not zero guests."
    return {
        "name": name,
        "present": True,
        "ok": ok,
        "denied": denied,
        "http": block.get("http"),
        "error_codes": block.get("error_codes"),
        "row_count": row_count if isinstance(row_count, int) else None,
        "row_count_raw_null": row_count is None,
        "probed_at": block.get("probed_at"),
        "writable": block.get("writable"),
        "write_attempted": block.get("write_attempted"),
        "means_no_guests": False,
        "state": state,
        "why": why,
    }


def _reservation_stub() -> dict[str, Any]:
    if not RESERVATIONS.is_file():
        return {
            "state": "UNAVAILABLE",
            "path": str(RESERVATIONS),
            "row_count": None,
            "means_no_guests": False,
            "hotel_history": False,
            "why": "reservations.db is missing. That is not a count of zero guests.",
        }
    conn = sqlite3.connect(f"file:{RESERVATIONS}?mode=ro", uri=True, timeout=8)
    conn.row_factory = sqlite3.Row
    try:
        count = int(conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0])
        row = conn.execute(
            "SELECT id, venue, party_size, when_iso, status FROM reservations ORDER BY id LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    shown = None
    if row is not None:
        shown = {
            "id": row["id"],
            "venue": row["venue"],
            "party_size": row["party_size"],
            "when_iso": row["when_iso"],
            "status": row["status"],
        }
    return {
        "state": "UNAVAILABLE",
        "path": str(RESERVATIONS),
        "row_count": count,
        "means_no_guests": False,
        "hotel_history": False,
        "sample": shown,
        "pii": "omitted",
        "why": (
            "The stored row is a cafe reservation, not an Atrium stay book. "
            "Hotel reservation history is UNAVAILABLE. The row count is not a guest count."
        ),
    }


def _stay(occ: dict[str, Any], pack3: dict[str, Any], v1: dict[str, Any]) -> dict[str, Any]:
    usable = bool(occ.get("usable"))
    return {
        "id": "stay",
        "state": "PARTIAL" if usable else "UNAVAILABLE",
        "question": "vacant_versus_rooms",
        "opens_desk": usable,
        "href": SALES_OCC if usable else None,
        "in_house": "UNKNOWN",
        "arrivals": "UNKNOWN",
        "guests": None,
        "adr": None,
        "revpar": None,
        "means_no_guests": False,
        "rooms_total": occ.get("rooms_total") if usable else None,
        "rooms_vacant": occ.get("vacant") if usable else None,
        "rooms_occupied": occ.get("occupied_rooms") if usable else None,
        "occupancy_pct": occ.get("pct") if usable else None,
        "display": occ.get("display") if usable else "UNKNOWN",
        "source": occ.get("source"),
        "freshness": occ.get("written_at"),
        "hotel_code": occ.get("hotel_code"),
        "kind": occ.get("kind"),
        "yanolja_live": bool(occ.get("yanolja_live")) if usable else False,
        "pack3_in_house": pack3.get("in_house"),
        "v1_master_val": v1.get("val"),
        "v1_not_merged": True,
        "why": (
            "Yanolja Inventory+RoomInfo is a vacant-versus-rooms read. "
            "In-house is UNKNOWN. The V1 master tile is a different question and is not merged."
            if usable
            else occ.get("reason") or "Yanolja vacant-versus-rooms is UNAVAILABLE. No occupancy was invented."
        ),
    }


def load_guest_stay() -> dict[str, Any]:
    last = load_last_read()
    occ = occupancy_from_last(last)
    depth = guest_depth_honesty()
    pack3 = _occupancy()
    v1 = _v1_master_atrium()
    reservations = _reservation_stub()
    arrivals = _endpoint("arrival_list")
    bookings = _endpoint("bookings")
    bookings_dated = _endpoint("bookings_dated")
    inhouse = _endpoint("inhouse_room_status")
    pre = {
        "id": "pre-arrival",
        "state": "UNAVAILABLE",
        "opens_desk": False,
        "href": None,
        "count": None,
        "means_no_guests": False,
        "guests": None,
        "endpoint": arrivals,
        "template": _template(N8N_PRE),
        "why": (
            "ArrivalList did not return guest rows. "
            "The n8n pre-arrival file is a template, not an operating workflow."
        ),
    }
    stay = _stay(occ, pack3, v1)
    post = {
        "id": "post-stay",
        "state": "UNAVAILABLE",
        "opens_desk": False,
        "href": None,
        "folio": None,
        "means_no_guests": False,
        "guests": None,
        "template": _template(N8N_POST),
        "why": (
            "No departure folio was read. "
            "The n8n post-stay file is a template, not an operating workflow."
        ),
    }
    housekeeping = {
        "id": "housekeeping",
        "state": "OUT_OF_SCOPE",
        "later_pack": True,
        "href": None,
        "why": "Housekeeping is a later pack. This pack does not open it.",
    }
    return {
        "ok": True,
        "pack": "PACK-07",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "bookings_write": False,
        "xero_write": False,
        "hr": False,
        "adr": None,
        "revpar": None,
        "guests": None,
        "means_no_guests": False,
        "last_read_path": last.get("_path"),
        "last_read_written_at": last.get("written_at"),
        "last_read_kind": last.get("kind"),
        "guest_depth_note": last.get("guest_depth_note"),
        "guest_depth": depth.get("guest_depth"),
        "cards": [pre, stay, post],
        "pre_arrival": pre,
        "stay": stay,
        "post_stay": post,
        "housekeeping": housekeeping,
        "reservations": reservations,
        "bookings": {
            "write": False,
            "finish_wolf": "off",
            "bookings": bookings,
            "bookings_dated": bookings_dated,
            "treated_as_guest_list": False,
            "why": "Bookings write stays off. A dated probe with a null row count is not a guest list.",
        },
        "inhouse_endpoint": inhouse,
        "v1_master": v1,
        "pack3_occupancy_question": pack3.get("question"),
    }


def refuse_write() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "writes_off",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "bookings_write": False,
        "xero_write": False,
        "message": "Guest stay does not write bookings, folios, or Xero.",
    }
