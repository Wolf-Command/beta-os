#!/usr/bin/env python3
"""Wave 2.02 — housekeeping stays unknown when Yanolja has no room status."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import amg_housekeeping_wave2_02 as hk  # noqa: E402
from core.yanolja_last_read_ro import resolve_last_read_path  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}  {detail}")


def main() -> int:
    last_path = resolve_last_read_path()
    last_mtime = last_path.stat().st_mtime_ns
    probe_mtime = hk.PROBE.stat().st_mtime_ns
    data = hk.load_housekeeping()
    check("staff not ready", data.get("staff_ready") is False and data.get("human_proven") is False and data.get("writes") is False)
    check("bookings stay off", data.get("bookings_enabled") is False and data["bookings"].get("enabled") is False and data["bookings"].get("denied") is True)
    status = data["room_status"]
    check(
        "status not invented",
        status.get("clean") is None
        and status.get("dirty") is None
        and status.get("inspected") is None
        and status.get("out_of_order") is None
        and status.get("derived_from_occupancy") is False
        and status.get("state") == "UNKNOWN",
        str(status),
    )
    inv = data["inventory_not_status"]
    check(
        "vacant is not housekeeping",
        inv.get("used_as_housekeeping") is False
        and inv.get("vacant") == 13
        and inv.get("rooms_total") == 114
        and inv.get("written_at") == "2026-10-01T07:16:15+08:00"
        and inv.get("source") == "Yanolja Inventory+RoomInfo",
        str(inv),
    )
    check("desk unavailable", data.get("state") == "UNAVAILABLE", str(data.get("state")))
    probes = {item["path"]: item for item in data["probes"]["paths"]}
    check("six probes", set(probes) == set(hk.STATUS_PATHS))
    check(
        "housekeeping php is 404",
        probes["inhousePOST:/pmsinterface/housekeeping.php"].get("http") == 404
        and probes["inhousePOST:/pmsinterface/housekeeping.php"].get("has_roomlist") is False
        and probes["inhousePOST:/pmsinterface/housekeeping.php"].get("state") == "UNAVAILABLE"
        and probes["inhousePOST:/pmsinterface/housekeeping.php"].get("roomlist_n_is_status_count") is False,
    )
    check(
        "probe stamp",
        data["probes"].get("probed_at") == "2026-10-01T07:31:35+08:00" and data["probes"].get("state") == "UNAVAILABLE",
    )
    inn = data["inhouse"]
    check(
        "inhouse unknown",
        inn.get("state") == "UNKNOWN"
        and inn.get("ok") is False
        and inn.get("row_count") is None
        and inn.get("means_no_rooms") is False
        and "Request Type is missing" in (inn.get("error_codes") or []),
        str(inn),
    )
    page = (ROOT / "dashboards" / "amg-housekeeping.html").read_text(encoding="utf-8")
    check("page title", "<title>Housekeeping and room status</title>" in page)
    check("tiles start closed", page.count("<details>") >= 4 and "<details open" not in page)
    check("page refuses a status", "Clean, dirty, and inspected are unknown" in page)
    refused = hk.refuse_write()
    check("refuse write", refused.get("error") == "writes_off" and refused.get("bookings_enabled") is False)
    check("files unread", last_path.stat().st_mtime_ns == last_mtime and hk.PROBE.stat().st_mtime_ns == probe_mtime)
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
