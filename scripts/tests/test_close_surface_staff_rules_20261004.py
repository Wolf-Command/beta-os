#!/usr/bin/env python3
"""Daily Close staff surface — staff-visible rules wired from existing behaviour.

Temp in-memory sqlite only. Never copies catalog/content_library.sqlite.
Protected closes are not touched.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def fresh_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def bootstrap_schema(conn: sqlite3.Connection) -> None:
    sql_021 = (ROOT / "scripts" / "migrations" / "021_uma_blu_daily_close.sql").read_text(
        encoding="utf-8"
    )
    conn.executescript(sql_021)
    from core import bzg_daily_close as bzg

    bzg.ensure_schema(conn)
    conn.commit()


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["WOLF_CLOSE_VISION_DRY"] = "1"

    from core import bzg_daily_close as bzg

    conn = fresh_conn()
    try:
        bootstrap_schema(conn)

        surf_empty = bzg.staff_close_surface("", outlet_id="BZG-UMA", conn=conn)
        check(
            "empty outlet banks say needs setup",
            surf_empty.get("bank_setup") == "needs setup",
            str(surf_empty.get("bank_setup")),
        )

        bzg.configure_outlet_settlement_banks("BZG-UMA", conn=conn)
        surf_ready = bzg.staff_close_surface("", outlet_id="BZG-UMA", conn=conn)
        check(
            "configured outlet bank_setup ready",
            surf_ready.get("bank_setup") == "ready",
            str(surf_ready.get("bank_setup")),
        )

        cid = f"VDC-TEST-SURFACE-{uuid.uuid4()}"
        ts = "2099-09-29T12:00:00Z"
        conn.execute(
            """
            INSERT INTO venue_daily_closes (
              close_id, entity_id, venue_brand_id, business_date, state,
              declared_cash_amount, created_at, updated_at
            ) VALUES (?, 'ENT-BZG', 'BZG-UMA', '2099-09-29', 'DATA_CAPTURED',
                      NULL, ?, ?)
            """,
            (cid, ts, ts),
        )
        conn.commit()

        cards = bzg.bank_cards(cid, conn=conn)
        mandiri = next((c for c in (cards.get("cards") or []) if c.get("bank") == "MANDIRI"), None)
        check("bank card row exists for MANDIRI", mandiri is not None)
        check(
            "blank bank terminal_edc is not zero",
            mandiri is not None and mandiri.get("terminal_edc") is None,
            str(mandiri.get("terminal_edc") if mandiri else None),
        )
        check(
            "blank bank actual_edc is not zero",
            mandiri is not None and mandiri.get("actual_edc") is None,
            str(mandiri.get("actual_edc") if mandiri else None),
        )

        draft = bzg.extract_edc_receipt_draft(
            cid,
            verified_person_id="PERSON-TEST-CLOSER",
            image_bytes=b"FORCE-EXTRACT-FAIL-SURFACE-TEST",
            bank_hint="MANDIRI",
            conn=conn,
            commit=True,
        )
        check("failed photo extraction_unavailable", draft.get("extraction_unavailable") is True)
        check("failed photo manual_entry_ok", draft.get("manual_entry_ok") is True)

        conn.execute(
            """
            UPDATE venue_daily_closes
            SET state='VERIFIED_CLOSED', declared_cash_amount=500000,
                variance_cash_amount=0, verified_at=?, verified_by_person_id=?
            WHERE close_id=?
            """,
            (ts, "PERSON-TEST-CLOSER", cid),
        )
        conn.commit()

        before = conn.execute(
            "SELECT COUNT(*) FROM venue_daily_closes WHERE close_id=?", (cid,)
        ).fetchone()[0]
        out = bzg.staff_submit_close(
            cid,
            declared_cash_amount=500000,
            verified_person_id="PERSON-TEST-CLOSER",
            conn=conn,
            commit=True,
        )
        after = conn.execute(
            "SELECT COUNT(*) FROM venue_daily_closes WHERE close_id=?", (cid,)
        ).fetchone()[0]
        check("repeat submit idempotent flag", out.get("idempotent") is True)
        check("repeat submit not a second close row", before == after == 1, f"{before}/{after}")
        check(
            "repeat submit staff_result CLOSE COMPLETE",
            out.get("staff_result") == "CLOSE COMPLETE",
            str(out.get("staff_result")),
        )

        from core import venue_close as vc

        enriched = bzg.enrich_close(vc.get_close(cid, conn=conn), conn=conn)
        check(
            "enrich_close includes staff_surface",
            isinstance((enriched or {}).get("staff_surface"), dict),
            str(type((enriched or {}).get("staff_surface"))),
        )
    finally:
        conn.close()

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
