"""FINANCE-CONTROL-REPAIR-2026-10-03 — three-object freeze + history detail.

Beta-only. Does NOT touch / cancel preserved close VDC-87202768….
Does NOT stamp ENG_PROVED or staff_ready.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from pathlib import Path

try:
    import pytest
except ModuleNotFoundError:  # pragma: no cover — local prove without pytest
    pytest = None  # type: ignore

ROOT = Path("/Users/wolfterminal/beta-os")
sys.path.insert(0, str(ROOT / "scripts"))

from core import bzg_daily_close as bzg  # noqa: E402
from core import venue_close as vc  # noqa: E402

PRESERVED = "VDC-87202768-55af-4c8e-abc3-382a5496b8c6"
CATALOG = ROOT / "catalog" / "content_library.sqlite"


if pytest is not None:

    @pytest.fixture()
    def conn():
        c = sqlite3.connect(str(CATALOG))
        c.row_factory = sqlite3.Row
        yield c
        c.close()


def _preserved_fingerprint(conn) -> str:
    row = conn.execute(
        "SELECT esb_fingerprint_sha256, esb_totals_json, state, taken_by_person_id "
        "FROM venue_daily_closes WHERE close_id=?",
        (PRESERVED,),
    ).fetchone()
    assert row is not None
    assert row["state"] == "DATA_CAPTURED"
    assert row["taken_by_person_id"] == "PERS-MATT"
    return str(row["esb_fingerprint_sha256"])


def test_preserved_still_intact(conn):
    fp = _preserved_fingerprint(conn)
    assert len(fp) == 64
    photos = list((ROOT / "state/bzg-daily-close/receipts").glob("EVD-CLOSE-*"))
    assert len(photos) >= 5


def test_three_objects_shape(conn):
    row = vc.get_close(PRESERVED, conn=conn)
    assert row
    objs = vc.three_close_objects(row)
    assert objs["dated_closing_snapshot"]["object"] == "DATED_CLOSING_SNAPSHOT"
    assert objs["dated_closing_snapshot"]["frozen"] is True
    assert objs["dated_closing_snapshot"]["business_date"] == "2026-10-02"
    assert objs["live_esb_operational"]["mutates_close"] is False
    assert objs["final_historical_close"]["is_final"] is False
    assert objs["api_and_receipt_are_separate_sources"] is True


def test_capture_does_not_overwrite_frozen_snapshot(conn):
    """Re-capture on DATA_CAPTURED must keep stored API totals (no live overwrite)."""
    before = conn.execute(
        "SELECT esb_fingerprint_sha256, esb_totals_json FROM venue_daily_closes WHERE close_id=?",
        (PRESERVED,),
    ).fetchone()
    before_fp = before["esb_fingerprint_sha256"]
    before_totals = before["esb_totals_json"]

    out = vc.capture_esb_snapshot(
        PRESERVED,
        verified_person_id="PERS-MATT",
        conn=conn,
        commit=True,
    )
    assert out.get("snapshot_frozen") is True
    assert out.get("mutated") is False
    assert out.get("recaptured") is False
    assert out.get("three_objects", {}).get("dated_closing_snapshot", {}).get("frozen") is True

    after = conn.execute(
        "SELECT esb_fingerprint_sha256, esb_totals_json, state, taken_by_person_id "
        "FROM venue_daily_closes WHERE close_id=?",
        (PRESERVED,),
    ).fetchone()
    assert after["esb_fingerprint_sha256"] == before_fp
    assert after["esb_totals_json"] == before_totals
    assert after["state"] == "DATA_CAPTURED"
    assert after["taken_by_person_id"] == "PERS-MATT"


def test_history_detail_api_vs_receipt_and_banks(conn):
    hist = bzg.history_detail(PRESERVED, conn=conn)
    assert hist["ok"] is True
    assert hist["live_esb_used"] is False
    assert hist["snapshot_frozen"] is True
    assert hist["source_snapshot"]["esb_fingerprint_sha256"]
    avr = hist["api_vs_receipt"]
    # Known dual source on 2026-10-02 — do not force agreement.
    assert avr["api_cash"] == 2855000.0
    assert avr["receipt_cash"] == 2735000.0
    assert avr["difference_visible"] is True
    assert avr["cause_invented"] is False
    assert avr["silent_overwrite"] is False
    cards = (hist.get("bank_cards") or {}).get("cards") or []
    labels = {str(c.get("bank") or "").upper() for c in cards}
    assert "MANDIRI" in labels
    assert "BNI" in labels
    assert "BRI" in labels
    assert hist["edc"]["superseded_excluded"] is True
    assert hist["cancel_unfinished_rewrites_history"] is False


def test_closing_history_excludes_cancelled_from_totals(conn):
    hist = vc.closing_history(
        date_from="2026-10-01",
        date_to="2026-10-03",
        outlet_id="BZG-UMA",
        conn=conn,
    )
    assert hist["live_esb_used"] is False
    assert hist["consolidated"]["excludes_cancelled_and_open"] is True
    assert hist["consolidated"]["excludes_superseded_edc_attempts"] is True
    assert any(r["close_id"] == PRESERVED for r in hist["closes"])


def test_throwaway_cancel_leaves_preserved(conn):
    cid = f"VDC-TEST-{uuid.uuid4()}"
    ts = "2026-10-03T12:00:00Z"
    try:
        conn.execute(
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
        conn.commit()
        out = vc.cancel_unfinished_close(
            cid,
            verified_person_id="PERS-MATT",
            reason="three-object prove throwaway",
            conn=conn,
            commit=True,
        )
        assert out["cancelled"] is True
        assert out["close"]["state"] == "CANCELLED"
    finally:
        conn.execute("DELETE FROM venue_daily_closes WHERE close_id=?", (cid,))
        conn.commit()
    row = conn.execute(
        "SELECT state, taken_by_person_id FROM venue_daily_closes WHERE close_id=?",
        (PRESERVED,),
    ).fetchone()
    assert row["state"] == "DATA_CAPTURED"
    assert row["taken_by_person_id"] == "PERS-MATT"


if __name__ == "__main__":
    # Manual runner when pytest module unavailable.
    c = sqlite3.connect(str(CATALOG))
    c.row_factory = sqlite3.Row
    try:
        test_preserved_still_intact(c)
        test_three_objects_shape(c)
        test_capture_does_not_overwrite_frozen_snapshot(c)
        test_history_detail_api_vs_receipt_and_banks(c)
        test_closing_history_excludes_cancelled_from_totals(c)
        test_throwaway_cancel_leaves_preserved(c)
        print("PASS finance_control_three_object_history_20261003")
    finally:
        c.close()
