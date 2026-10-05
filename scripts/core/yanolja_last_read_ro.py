#!/usr/bin/env python3
"""Yanolja last-read RO consumer for Beta House.

Reads Inventory+RoomInfo snapshot only. Never invents guests, ADR, RevPAR,
folio, or arrivals. Occupancy = vacant vs rooms, NOT guest invent.
0% ≠ guest count. UNKNOWN when endpoint / field missing.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_LAST_READ = BETA_ROOT / "state" / "yanolja" / "last-read.json"
FALLBACK_LAST_READ = Path(
    "/Users/wolfterminal/.openclaw/workspace/wolf-system/state/yanolja/last-read.json"
)
WITA = timezone(timedelta(hours=8))
HOTEL_CODE = "63221"
INTEGRATION_ID = "INT-YAN-WOLF"
SOURCE_LABEL = "yanolja_last_read"


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def resolve_last_read_path(path: Path | str | None = None) -> Path:
    if path is not None:
        return Path(path).resolve()
    env = (os.environ.get("WOLF_YANOLJA_LAST_READ") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    if DEFAULT_LAST_READ.is_file():
        return DEFAULT_LAST_READ.resolve()
    if FALLBACK_LAST_READ.is_file():
        return FALLBACK_LAST_READ.resolve()
    return DEFAULT_LAST_READ.resolve()


def load_last_read(path: Path | str | None = None) -> dict[str, Any]:
    pth = resolve_last_read_path(path)
    if not pth.is_file():
        return {"_load_error": "last-read missing", "path": str(pth)}
    try:
        data = json.loads(pth.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"_load_error": f"last-read unreadable: {type(exc).__name__}", "path": str(pth)}
    if not isinstance(data, dict):
        return {"_load_error": "last-read must be a JSON object", "path": str(pth)}
    data = dict(data)
    data.pop("creds_path", None)  # never surface credential paths
    data["_path"] = str(pth)
    return data


def occupancy_from_last(last: dict[str, Any] | None = None) -> dict[str, Any]:
    """Usable occupancy from last-read only. Never invent guests."""
    if last is None:
        last = load_last_read()
    if last.get("_load_error"):
        return {
            "usable": False,
            "value": None,
            "pct": None,
            "vacant": None,
            "rooms_total": None,
            "occupied_rooms": None,
            "display": "UNKNOWN",
            "guests": None,
            "reason": last.get("_load_error"),
            "source": SOURCE_LABEL,
            "yanolja_live": False,
            "pms_connected": False,
            "state": "BLOCKED",
        }
    if last.get("ok") is False or last.get("denied") or last.get("invented"):
        return {
            "usable": False,
            "value": None,
            "pct": None,
            "vacant": None,
            "rooms_total": last.get("rooms_total"),
            "occupied_rooms": None,
            "display": "UNKNOWN",
            "guests": None,
            "reason": last.get("error") or "last-read not ok / denied / invented",
            "source": SOURCE_LABEL,
            "yanolja_live": False,
            "pms_connected": False,
            "state": "BLOCKED",
            "written_at": last.get("written_at"),
        }
    occ_raw = last.get("occupancy") if isinstance(last.get("occupancy"), dict) else {}
    total = occ_raw.get("rooms_total")
    if not isinstance(total, int):
        total = last.get("rooms_total")
    vacant = occ_raw.get("rooms_vacant")
    occupied = occ_raw.get("rooms_occupied")
    pct = occ_raw.get("pct_occupied")
    if not isinstance(total, int) or total <= 0 or not isinstance(vacant, int):
        # Prefer occupancy_usable flag + integers only
        return {
            "usable": False,
            "value": None,
            "pct": None,
            "vacant": vacant if isinstance(vacant, int) else None,
            "rooms_total": total if isinstance(total, int) else None,
            "occupied_rooms": occupied if isinstance(occupied, int) else None,
            "display": "UNKNOWN",
            "guests": None,
            "reason": (
                "occupancy UNKNOWN — last-read has no vacant/rooms integers "
                "(vacant vs rooms, not guests)"
            ),
            "source": SOURCE_LABEL,
            "yanolja_live": bool(last.get("ok") and last.get("http") == 200),
            "pms_connected": False,
            "state": "UNKNOWN",
            "written_at": last.get("written_at"),
            "kind": last.get("kind"),
        }
    if occupied is None:
        occupied = total - vacant
    if pct is None and total:
        pct = round((occupied / total) * 100, 2)
    usable = bool(last.get("occupancy_usable", True)) and not last.get("invented")
    display = f"{pct:.0f}% · {vacant} vacant / {total} rooms"
    return {
        "usable": usable,
        "value": pct,
        "pct": pct,
        "vacant": vacant,
        "rooms_total": total,
        "occupied_rooms": occupied,
        "rooms_occupied": occupied,
        "display": display,
        "copy": "vacant vs rooms, not guests",
        "guests": None,  # NEVER invent guest count from occupancy
        "in_house": occ_raw.get("in_house"),  # may be None → UNKNOWN
        "arrivals": occ_raw.get("arrivals"),  # may be None → UNKNOWN
        "reason": None if usable else "occupancy_usable false",
        "source": occ_raw.get("source") or "Yanolja Inventory+RoomInfo",
        "yanolja_live": usable,
        "pms_connected": usable,
        "state": "LIVE" if usable else "PARTIAL",
        "written_at": last.get("written_at"),
        "kind": last.get("kind"),
        "hotel_code": last.get("hotel_code") or HOTEL_CODE,
        "http": last.get("http"),
        "room_type_count": last.get("room_type_count") or last.get("roominfo_type_count"),
        "freshness": last.get("written_at"),
        "note": last.get("note"),
    }



def guest_depth_honesty(path: Path | str | None = None) -> dict[str, Any]:
    """Honesty map for arrivals/in-house/bookings. Never invents guests/ADR/RevPAR.

    Reads last-read endpoints block and/or guest-depth probe stamp if present.
    """
    last = load_last_read(path)
    ends = last.get("endpoints") if isinstance(last.get("endpoints"), dict) else {}
    probe_path = Path(last.get("_path") or "").parent / "guest-depth-probe-latest.json"
    probe = {}
    if probe_path.is_file():
        try:
            probe = json.loads(probe_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            probe = {}
    probe_ends = (probe.get("endpoints") or probe.get("results") or {}) if isinstance(probe, dict) else {}

    def _status(name: str, aliases: list[str] | None = None) -> dict[str, Any]:
        block = ends.get(name) if isinstance(ends, dict) else None
        if not isinstance(block, dict):
            for a in aliases or []:
                block = ends.get(a) if isinstance(ends, dict) else None
                if isinstance(block, dict):
                    break
        if not isinstance(block, dict):
            # fall back to probe
            for a in [name] + (aliases or []):
                block = probe_ends.get(a) if isinstance(probe_ends, dict) else None
                if isinstance(block, dict):
                    break
        if not isinstance(block, dict):
            return {
                "state": "UNKNOWN",
                "count": None,
                "reason": f"{name} not probed / not in last-read",
            }
        if block.get("denied") or (block.get("error_codes") and "302" in [str(x) for x in (block.get("error_codes") or [])]):
            return {
                "state": "DENIED",
                "count": None,
                "reason": (
                    block.get("error")
                    or str((block.get("error_codes") or [None])[0:2])
                    or "integration not allowed"
                ),
                "http": block.get("http"),
                "probed_at": block.get("probed_at"),
            }
        if block.get("ok") and isinstance(block.get("row_count"), int):
            return {
                "state": "LIVE",
                "count": block.get("row_count"),
                "reason": None,
                "http": block.get("http"),
                "probed_at": block.get("probed_at"),
            }
        # error without denial → UNKNOWN
        return {
            "state": "UNKNOWN",
            "count": block.get("row_count"),
            "reason": (
                block.get("error")
                or str(block.get("error_codes") or block.get("Error") or "endpoint did not return guest rows")
            ),
            "http": block.get("http"),
            "probed_at": block.get("probed_at"),
        }

    arrivals = _status("arrival_list", ["ArrivalList", "ArrivalList+FromTo", "listing_ArrivalList_error"])
    bookings = _status("bookings", ["Bookings", "bookings_dated", "Bookings+FromTo"])
    inhouse = _status(
        "inhouse_room_status",
        ["Retrieve Inhouse Room Status", "kiosk-flat", "inhousePOST:/pmsinterface/housekeeping.php"],
    )
    any_live = any(x.get("state") == "LIVE" for x in (arrivals, bookings, inhouse))
    return {
        "guest_depth": "PARTIAL" if any_live else "UNKNOWN",
        "arrivals": arrivals,
        "bookings": bookings,
        "inhouse": inhouse,
        "guests": None if not any_live else {
            "arrivals_count": arrivals.get("count"),
            "bookings_count": bookings.get("count"),
            "inhouse_guest_count": inhouse.get("count"),
        },
        "adr": None,
        "revpar": None,
        "invented": False,
        "why": (
            "Guest-depth probed 2026-10-01 with seated AuthCode. "
            "Bookings → 302 Integration not allowed. "
            "ArrivalList → From Date / Bad request type. "
            "Inhouse kiosk → 500. Guests stay UNKNOWN. ADR/RevPAR not invented."
            if not any_live
            else "Some guest endpoints returned rows — counts only; no ADR/RevPAR invented."
        ),
        "probe_stamp": str(probe_path.name) if probe_path.is_file() else None,
        "as_of_wita": _now_wita(),
    }


def connection_stamp(path: Path | str | None = None) -> dict[str, Any]:
    """Honest connector stamp for INTG / conn-health / OS shell."""
    last = load_last_read(path)
    occ = occupancy_from_last(last)
    if last.get("_load_error"):
        return {
            "integration_id": INTEGRATION_ID,
            "audit_status": "BLOCKED_EXTERNAL",
            "blocked_external": True,
            "probe_status": "LAST_READ_MISSING",
            "last_success": None,
            "yanolja_live": False,
            "pms_connected": False,
            "occupancy": occ,
            "why": last.get("_load_error"),
            "source": SOURCE_LABEL,
            "as_of_wita": _now_wita(),
        }
    if occ.get("usable"):
        gd = guest_depth_honesty(path)
        return {
            "integration_id": INTEGRATION_ID,
            "audit_status": "LIVE_READ_OK",
            "blocked_external": False,
            "probe_status": "INVENTORY_ROOMINFO_READ_OK",
            "last_success": last.get("written_at"),
            "yanolja_live": True,
            "pms_connected": True,
            "occupancy": occ,
            "guest_depth": gd.get("guest_depth", "UNKNOWN"),
            "guest_depth_map": gd,
            "adr": None,
            "revpar": None,
            "why": (
                "Yanolja Inventory+RoomInfo last-read LIVE. "
                "Occupancy = vacant vs rooms (not guests). "
                "Arrivals/in-house/ADR/RevPAR UNKNOWN — guest endpoints probed; Bookings 302 / ArrivalList date-shape / Inhouse 500 with seated AuthCode."
            ),
            "source": SOURCE_LABEL,
            "kind": last.get("kind"),
            "hotel_code": last.get("hotel_code") or HOTEL_CODE,
            "http": last.get("http"),
            "as_of_wita": _now_wita(),
            "path_basename": Path(last.get("_path") or "").name,
        }
    # Partial / blocked
    live_http = last.get("ok") and last.get("http") == 200
    return {
        "integration_id": INTEGRATION_ID,
        "audit_status": "PARTIAL_IN_BETA" if live_http else "BLOCKED_EXTERNAL",
        "blocked_external": not live_http,
        "probe_status": "LAST_READ_PARTIAL" if live_http else "LAST_READ_DENIED",
        "last_success": last.get("written_at") if live_http else None,
        "yanolja_live": bool(live_http),
        "pms_connected": False,
        "occupancy": occ,
        "why": occ.get("reason") or "occupancy not usable from last-read",
        "source": SOURCE_LABEL,
        "as_of_wita": _now_wita(),
    }


if __name__ == "__main__":
    print(json.dumps(connection_stamp(), indent=2, default=str))
