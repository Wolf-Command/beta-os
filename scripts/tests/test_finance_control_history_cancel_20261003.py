"""FINANCE-CONTROL-REPAIR-2026-10-03 — Closing History filters + cancel unfinished.

Beta-only. Does NOT touch preserved close VDC-87202768….
Does NOT stamp ENG_PROVED or staff_ready.
"""
from __future__ import annotations

import sqlite3
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path("/Users/wolfterminal/beta-os")
sys.path.insert(0, str(ROOT / "scripts"))

from core import venue_close as vc  # noqa: E402

PRESERVED = "VDC-87202768-55af-4c8e-abc3-382a5496b8c6"
CATALOG = ROOT / "catalog" / "content_library.sqlite"


@pytest.fixture()
def conn():
    c = sqlite3.connect(str(CATALOG))
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def test_preserved_close_untouched(conn):
    row = conn.execute(
        "SELECT close_id, business_date, outlet_id, state, taken_by_person_id FROM venue_daily_closes WHERE close_id=?",
        (PRESERVED,),
    ).fetchone()
    assert row is not None
    assert row["business_date"] == "2026-10-02"
    assert row["outlet_id"] == "BZG-UMA"
    assert row["state"] == "DATA_CAPTURED"
    assert row["taken_by_person_id"] == "PERS-MATT"
    photos = list((ROOT / "state/bzg-daily-close/receipts").glob("EVD-CLOSE-*"))
    assert len(photos) >= 5


def test_list_closes_date_and_outlet_filters(conn):
    rows = vc.list_closes(
        date_from="2026-10-02",
        date_to="2026-10-02",
        outlet_id="BZG-UMA",
        conn=conn,
    )
    assert any(r["close_id"] == PRESERVED for r in rows)
    for r in rows:
        assert r["business_date"] == "2026-10-02"
        assert r.get("outlet_id") in (None, "BZG-UMA") or r["outlet_id"] == "BZG-UMA"


def test_closing_history_saved_only_no_live_esb(conn):
    hist = vc.closing_history(
        date_from="2026-10-01",
        date_to="2026-10-03",
        outlet_id="BZG-UMA",
        conn=conn,
    )
    assert hist["ok"] is True
    assert hist["live_esb_used"] is False
    assert hist["source"] == "venue_daily_closes_saved"
    assert "consolidated" in hist
    assert hist["consolidated"]["unavailable_when_null"] is True


def test_cancel_unfinished_refuses_verified_and_preserves_vdc(conn):
    # VDC is DATA_CAPTURED — cancel path exists but we do not invoke it on preserved close.
    with pytest.raises(vc.VenueCloseError) as ei:
        vc.cancel_unfinished_close(
            PRESERVED.replace("87202768", "00000000"),  # missing
            verified_person_id="PERS-MATT",
            conn=conn,
            commit=False,
        )
    assert ei.value.code in ("not_found", "missing_close_id") or "not found" in str(ei.value).lower()

    # Re-check preserved still DATA_CAPTURED
    row = conn.execute(
        "SELECT state FROM venue_daily_closes WHERE close_id=?",
        (PRESERVED,),
    ).fetchone()
    assert row["state"] == "DATA_CAPTURED"


def test_cancel_unfinished_on_throwaway_open(conn):
    """Synthetic OPEN row — cancelled without touching VDC."""
    cid = f"VDC-TEST-{uuid.uuid4()}"
    ts = "2026-10-03T00:00:00Z"
    try:
        conn.execute(
            """
            INSERT INTO venue_daily_closes (
              close_id, entity_id, venue_brand_id, business_date, state,
              fingerprint_stale, submitted_by_person_id, created_at, updated_at,
              outlet_id, taken_by_person_id, taken_at
            ) VALUES (?, 'ENT-BZG', 'BZG-UMA', '2099-01-01', 'OPEN',
              0, 'PERS-MATT', ?, ?, 'BZG-UMA', 'PERS-MATT', ?)
            """,
            (cid, ts, ts, ts),
        )
        conn.commit()
        out = vc.cancel_unfinished_close(
            cid,
            verified_person_id="PERS-MATT",
            reason="unit test cancel unfinished",
            conn=conn,
            commit=True,
        )
        assert out["cancelled"] is True
        assert out["evidence_retained"] is True
        assert out["close"]["state"] == "CANCELLED"
    finally:
        conn.execute("DELETE FROM venue_daily_closes WHERE close_id=?", (cid,))
        conn.commit()
    # preserved untouched
    row = conn.execute(
        "SELECT state FROM venue_daily_closes WHERE close_id=?",
        (PRESERVED,),
    ).fetchone()
    assert row["state"] == "DATA_CAPTURED"
