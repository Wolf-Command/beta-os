#!/usr/bin/env python3
"""Wave 2.02 — housekeeping and room status. Read stored Yanolja probes.

Inventory vacant-versus-rooms is not a clean/dirty board. The housekeeping
paths that were probed returned 404. No status is invented.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.yanolja_last_read_ro import load_last_read, occupancy_from_last

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
PROBE = BETA_ROOT / "state" / "yanolja" / "guest-depth-probe-20261001c.json"
STATUS_PATHS = (
    "inhousePOST:/pmsinterface/getRoomStatus.php",
    "inhousePOST:/pmsinterface/getInhouseRoomStatus.php",
    "inhousePOST:/pmsinterface/housekeeping.php",
    "inhousePOST:/booking/reservation_api/getRoomStatus.php",
    "inhousePOST:/booking/reservation_api/housekeeping.php",
    "inhousePOST:/channelbookings/housekeeping.php",
)


def _probe() -> dict[str, Any]:
    if not PROBE.is_file():
        return {
            "present": False,
            "probed_at": None,
            "paths": [],
            "state": "UNKNOWN",
            "why": "The room-status probe file is missing. No clean or dirty count was invented.",
        }
    try:
        data = json.loads(PROBE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "present": False,
            "probed_at": None,
            "paths": [],
            "state": "UNKNOWN",
            "why": f"The probe file is unreadable ({type(exc).__name__}). No status was invented.",
        }
    results = data.get("results") if isinstance(data.get("results"), dict) else {}
    paths = []
    for key in STATUS_PATHS:
        block = results.get(key) if isinstance(results.get(key), dict) else None
        if block is None:
            paths.append({"path": key, "state": "UNKNOWN", "http": None, "has_roomlist": None})
            continue
        http = block.get("http")
        has_list = block.get("has_roomlist")
        paths.append(
            {
                "path": key,
                "http": http,
                "has_roomlist": has_list,
                "roomlist_n": block.get("roomlist_n"),
                "roomlist_n_is_status_count": False,
                "state": "UNAVAILABLE" if http == 404 and has_list is False else "UNKNOWN",
            }
        )
    unavailable = all(item.get("state") == "UNAVAILABLE" for item in paths) and bool(paths)
    return {
        "present": True,
        "path": str(PROBE),
        "probed_at": data.get("probed_at"),
        "paths": paths,
        "state": "UNAVAILABLE" if unavailable else "UNKNOWN",
        "why": "These paths were probed. A 404 with no room list is not zero dirty rooms.",
    }


def _inhouse(last: dict[str, Any]) -> dict[str, Any]:
    ends = last.get("endpoints") if isinstance(last.get("endpoints"), dict) else {}
    block = ends.get("inhouse_room_status") if isinstance(ends.get("inhouse_room_status"), dict) else None
    if block is None:
        return {
            "state": "UNKNOWN",
            "row_count": None,
            "why": "In-house room status was not in the last read. No status was invented.",
        }
    return {
        "state": "UNKNOWN",
        "ok": block.get("ok"),
        "http": block.get("http"),
        "error_codes": block.get("error_codes"),
        "row_count": block.get("row_count"),
        "request_type": block.get("request_type"),
        "probed_at": block.get("probed_at"),
        "means_no_rooms": False,
        "why": "Retrieve Inhouse Room Status did not return a room list. row_count null is not zero rooms.",
    }


def _bookings(last: dict[str, Any]) -> dict[str, Any]:
    ends = last.get("endpoints") if isinstance(last.get("endpoints"), dict) else {}
    block = ends.get("bookings") if isinstance(ends.get("bookings"), dict) else {}
    return {
        "enabled": False,
        "denied": block.get("denied"),
        "error_codes": block.get("error_codes"),
        "write_attempted": False,
        "why": "Bookings is denied. This desk does not enable it.",
    }


def load_housekeeping() -> dict[str, Any]:
    last = load_last_read()
    occ = occupancy_from_last(last)
    probe = _probe()
    status = {
        "clean": None,
        "dirty": None,
        "inspected": None,
        "out_of_order": None,
        "derived_from_occupancy": False,
        "state": "UNKNOWN",
    }
    return {
        "ok": True,
        "pack": "WAVE2-02",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "bookings_enabled": False,
        "state": probe.get("state") if probe.get("present") else "UNKNOWN",
        "room_status": status,
        "inventory_not_status": {
            "usable": occ.get("usable"),
            "display": occ.get("display"),
            "vacant": occ.get("vacant"),
            "rooms_total": occ.get("rooms_total"),
            "written_at": occ.get("written_at"),
            "source": occ.get("source"),
            "used_as_housekeeping": False,
            "why": "Vacant versus rooms is inventory. It is not clean, dirty, or inspected.",
        },
        "inhouse": _inhouse(last),
        "probes": probe,
        "bookings": _bookings(last),
        "why": (
            "No housekeeping room list was returned. "
            "Clean, dirty, and inspected stay unknown."
        ),
    }


def refuse_write() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "writes_off",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "bookings_enabled": False,
        "message": "Housekeeping does not write a room status or enable Bookings.",
    }
