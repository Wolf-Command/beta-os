#!/usr/bin/env python3
"""Pack 7 — guest stay reads Yanolja rooms and does not invent guests."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import amg_guest_stay_pack7 as stay  # noqa: E402
from core.yanolja_last_read_ro import occupancy_from_last  # noqa: E402

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
    last_path = stay.load_last_read()["_path"]
    last_mtime = Path(last_path).stat().st_mtime_ns
    res_mtime = stay.RESERVATIONS.stat().st_mtime_ns
    data = stay.load_guest_stay()
    occ = occupancy_from_last()
    check("staff not ready", data.get("staff_ready") is False and data.get("human_proven") is False)
    check("writes off", data.get("writes") is False and data.get("bookings_write") is False and data.get("xero_write") is False)
    check("no invented adr", data.get("adr") is None and data.get("revpar") is None and data.get("guests") is None)
    check("last-read unread", Path(last_path).stat().st_mtime_ns == last_mtime)
    check("reservations unread", stay.RESERVATIONS.stat().st_mtime_ns == res_mtime)

    card = data["stay"]
    check("stay partial", card.get("state") == "PARTIAL" and card.get("question") == "vacant_versus_rooms")
    check("stay opens sales occ", card.get("opens_desk") is True and card.get("href") == "/amg/sales-desk#occ")
    check(
        "yanolja rooms kept",
        card.get("rooms_total") == occ.get("rooms_total")
        and card.get("rooms_vacant") == occ.get("vacant")
        and card.get("occupancy_pct") == occ.get("pct")
        and card.get("rooms_total") == 114
        and card.get("rooms_vacant") == 13
        and card.get("occupancy_pct") == 88.6,
        str((card.get("rooms_total"), card.get("rooms_vacant"), card.get("occupancy_pct"))),
    )
    check("in-house unknown", card.get("in_house") == "UNKNOWN" and card.get("pack3_in_house") == "UNKNOWN" and card.get("guests") is None)
    check("v1 not merged", card.get("v1_not_merged") is True and card.get("v1_master_val") not in (None, card.get("display"), card.get("occupancy_pct")))
    check("pack3 question kept", data.get("pack3_occupancy_question") == "vacant_versus_rooms")

    pre = data["pre_arrival"]
    check(
        "pre-arrival unavailable",
        pre.get("state") == "UNAVAILABLE" and pre.get("opens_desk") is False and pre.get("href") is None and pre.get("count") is None and pre.get("means_no_guests") is False,
    )
    check("pre template not operating", pre["template"]["exists"] is True and pre["template"]["operating"] is False)
    arrival = pre["endpoint"]
    check(
        "arrival list not zero",
        arrival.get("state") == "UNAVAILABLE" and arrival.get("row_count") is None and arrival.get("means_no_guests") is False,
        str(arrival.get("error_codes")),
    )

    post = data["post_stay"]
    check(
        "post-stay unavailable",
        post.get("state") == "UNAVAILABLE" and post.get("folio") is None and post.get("opens_desk") is False and post.get("means_no_guests") is False,
    )
    check("post template not operating", post["template"]["exists"] is True and post["template"]["operating"] is False)

    house = data["housekeeping"]
    check("housekeeping later", house.get("state") == "OUT_OF_SCOPE" and house.get("later_pack") is True and house.get("href") is None)

    reservations = data["reservations"]
    sample = reservations.get("sample") or {}
    check(
        "cafe row is not a hotel book",
        reservations.get("row_count") == 1
        and reservations.get("hotel_history") is False
        and reservations.get("means_no_guests") is False
        and reservations.get("state") == "UNAVAILABLE"
        and sample.get("venue") == "Uma Blu Cafe"
        and sample.get("party_size") == 4,
        str(sample),
    )
    check("pii omitted", reservations.get("pii") == "omitted" and "guest_name" not in sample and "email" not in sample)

    booked = data["bookings"]
    dated = booked["bookings_dated"]
    check("bookings write off", booked.get("write") is False and booked.get("finish_wolf") == "off" and booked.get("treated_as_guest_list") is False)
    check(
        "dated probe is not a guest list",
        dated.get("ok") is True and dated.get("row_count") is None and dated.get("row_count_raw_null") is True and dated.get("state") == "UNAVAILABLE" and dated.get("writable") is False and dated.get("write_attempted") is False,
        str(dated),
    )
    check("bookings denied", booked["bookings"].get("denied") is True and booked["bookings"].get("state") == "UNAVAILABLE")
    check("inhouse not a guest count", data["inhouse_endpoint"].get("state") == "UNAVAILABLE" and data["inhouse_endpoint"].get("row_count") is None)

    refused = stay.refuse_write()
    check("refuse write", refused.get("error") == "writes_off" and refused.get("bookings_write") is False and refused.get("staff_ready") is False)
    check("files still unread", Path(last_path).stat().st_mtime_ns == last_mtime and stay.RESERVATIONS.stat().st_mtime_ns == res_mtime)

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
