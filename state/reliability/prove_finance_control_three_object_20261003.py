#!/usr/bin/env python3
"""Local prove — three-object freeze + history detail + throwaway cancel.

Not under scripts/tests/ so canonical Beta writes for throwaway rows are allowed.
Does NOT cancel or mutate preserved VDC-87202768….
staff_ready / eng_proved remain false.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os")
sys.path.insert(0, str(ROOT / "scripts"))

from core import bzg_daily_close as bzg  # noqa: E402
from core import venue_close as vc  # noqa: E402

PRESERVED = "VDC-87202768-55af-4c8e-abc3-382a5496b8c6"
CATALOG = ROOT / "catalog" / "content_library.sqlite"


def main() -> int:
    c = sqlite3.connect(str(CATALOG))
    c.row_factory = sqlite3.Row
    results: list[str] = []

    row = c.execute(
        "SELECT close_id, business_date, outlet_id, state, taken_by_person_id, "
        "esb_fingerprint_sha256, esb_totals_json FROM venue_daily_closes WHERE close_id=?",
        (PRESERVED,),
    ).fetchone()
    assert row, "preserved missing"
    assert row["business_date"] == "2026-10-02"
    assert row["outlet_id"] == "BZG-UMA"
    assert row["state"] == "DATA_CAPTURED"
    assert row["taken_by_person_id"] == "PERS-MATT"
    before_fp = row["esb_fingerprint_sha256"]
    before_totals = row["esb_totals_json"]
    photos = list((ROOT / "state/bzg-daily-close/receipts").glob("EVD-CLOSE-*"))
    assert len(photos) >= 5, f"photos {len(photos)}"
    results.append("preserved_intact")

    close = vc.get_close(PRESERVED, conn=c)
    objs = vc.three_close_objects(close)
    assert objs["dated_closing_snapshot"]["frozen"] is True
    assert objs["live_esb_operational"]["mutates_close"] is False
    results.append("three_objects")

    out = vc.capture_esb_snapshot(
        PRESERVED, verified_person_id="PERS-MATT", conn=c, commit=True
    )
    assert out.get("snapshot_frozen") is True
    assert out.get("mutated") is False
    after = c.execute(
        "SELECT esb_fingerprint_sha256, esb_totals_json, state, taken_by_person_id "
        "FROM venue_daily_closes WHERE close_id=?",
        (PRESERVED,),
    ).fetchone()
    assert after["esb_fingerprint_sha256"] == before_fp
    assert after["esb_totals_json"] == before_totals
    assert after["state"] == "DATA_CAPTURED"
    assert after["taken_by_person_id"] == "PERS-MATT"
    # API cash must remain the stored figure (not forced to receipt 2,735,000).
    totals = json.loads(after["esb_totals_json"])
    assert float(totals["cash_from_payments"]) == 2855000.0
    results.append("freeze_no_overwrite")

    hist = bzg.history_detail(PRESERVED, conn=c)
    assert hist["live_esb_used"] is False
    assert hist["api_vs_receipt"]["api_cash"] == 2855000.0
    assert hist["api_vs_receipt"]["receipt_cash"] == 2735000.0
    assert hist["api_vs_receipt"]["difference_visible"] is True
    assert hist["api_vs_receipt"]["cause_invented"] is False
    banks = {str(x.get("bank") or "").upper() for x in (hist.get("bank_cards") or {}).get("cards") or []}
    assert {"MANDIRI", "BNI", "BRI"} <= banks
    results.append("history_detail")

    range_hist = vc.closing_history(
        date_from="2026-10-01", date_to="2026-10-03", outlet_id="BZG-UMA", conn=c
    )
    assert range_hist["live_esb_used"] is False
    assert range_hist["consolidated"]["excludes_superseded_edc_attempts"] is True
    results.append("range_totals")

    cid = f"VDC-TEST-{uuid.uuid4()}"
    ts = "2026-10-03T12:00:00Z"
    try:
        c.execute(
            """
            INSERT INTO venue_daily_closes (
              close_id, entity_id, venue_brand_id, business_date, state,
              fingerprint_stale, submitted_by_person_id, created_at, updated_at,
              outlet_id, taken_by_person_id, taken_at
            ) VALUES (?, 'ENT-BZG', 'BZG-UMA', '2099-02-02', 'OPEN',
              0, 'PERS-MATT', ?, ?, 'BZG-UMA', 'PERS-MATT', ?)
            """,
            (cid, ts, ts, ts),
        )
        c.commit()
        cancelled = vc.cancel_unfinished_close(
            cid,
            verified_person_id="PERS-MATT",
            reason="three-object prove throwaway",
            conn=c,
            commit=True,
        )
        assert cancelled["cancelled"] is True
        assert cancelled["close"]["state"] == "CANCELLED"
    finally:
        c.execute("DELETE FROM venue_daily_closes WHERE close_id=?", (cid,))
        c.commit()
    final = c.execute(
        "SELECT state, taken_by_person_id FROM venue_daily_closes WHERE close_id=?",
        (PRESERVED,),
    ).fetchone()
    assert final["state"] == "DATA_CAPTURED"
    assert final["taken_by_person_id"] == "PERS-MATT"
    results.append("throwaway_cancel_preserved_ok")

    c.close()
    print("PASS", " ".join(results))
    print("staff_ready=false eng_proved=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
