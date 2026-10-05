#!/usr/bin/env python3
"""UMA-CLOSE-6STEP-REBUILD-4 — confirmed EDIT figures drive banks/cash/resume/lists."""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
sys.path.insert(0, str(SCRIPTS))

PASS = 0
FAIL = 0

SEP29 = "VDC-8fd544e2-2132-4a4a-b714-720eb0cd18ad"
SEP03 = "2026-09-03"
MATT = "PERS-MATT"

FIGURES = {
    "gross_sales_rp": 8_000_000,
    "bills": 40,
    "pax": 80,
    "cash_rp": 3_000_000,
    "edc_bni_rp": 2_000_000,
    "qris_bni_rp": 100_000,
    "edc_bri_rp": 3_000_000,
    "qris_bri_rp": 500_000,
    "scott_etik_rp": 0,
    "non_sales_executive_chef_rp": 0,
}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def temp_catalog() -> Path:
    td = Path(tempfile.mkdtemp(prefix="tmp-uma-6step-r4-", dir=str(ROOT / "catalog" / "backups")))
    db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, db)
    return db


def wire_modules(db: Path) -> dict:
    import core.audit as audit
    import core.bzg_daily_close as bzg
    import core.evidence as evidence
    import core.rbac as rbac
    import core.uma_hist_close_queue1 as q
    import core.venue_close as vc

    saved: dict = {}
    for mod in (vc, bzg, q, evidence, audit, rbac):
        if hasattr(mod, "CATALOG_DB"):
            saved[mod] = mod.CATALOG_DB
            mod.CATALOG_DB = db  # type: ignore[attr-defined]
    return saved


def restore_modules(saved: dict) -> None:
    for mod, val in saved.items():
        mod.CATALOG_DB = val  # type: ignore[attr-defined]


def _open_sep03(conn: sqlite3.Connection):
    from core import bzg_daily_close as bzg

    opened = bzg.ensure_close_on_evidence(
        SEP03, verified_person_id=MATT, identity={"person_id": MATT}, conn=conn
    )
    close = opened.get("close") or opened
    cid = str(close.get("close_id") or "")
    ref = "close-receipt://EVD-CLOSE-ESB-R4-SEP03.jpg"
    ch = "c" * 64
    bzg.register_shift_report_photo(
        cid,
        object_ref=ref,
        content_hash=ch,
        verified_person_id=MATT,
        conn=conn,
        commit=True,
    )
    return cid, ref, ch


def test_a_edit_confirm_drives_banks_and_cash() -> None:
    from core import bzg_daily_close as bzg

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    cid, ref, ch = _open_sep03(conn)
    bzg.save_shift_human_corrections(
        cid,
        verified_person_id=MATT,
        figures=FIGURES,
        object_ref=ref,
        content_hash=ch,
        extracted={},
        identity={"person_id": MATT},
        allow_test_write=True,
        conn=conn,
        commit=True,
    )
    bzg.confirm_shift_figures_yes(
        cid,
        verified_person_id=MATT,
        object_ref=ref,
        content_hash=ch,
        extracted=FIGURES,
        conn=conn,
        commit=True,
    )
    printed = bzg.printed_shift_source(cid, conn=conn)
    check("A printed cash from edit", printed.get("cash_rp") == 3_000_000, str(printed.get("cash_rp")))
    check("A printed BNI EDC", printed.get("edc_bni_rp") == 2_000_000, str(printed.get("edc_bni_rp")))
    cards = bzg.wizard_bank_cards(cid, conn=conn).get("cards") or []
    bni = next((c for c in cards if c.get("bank") == "BNI"), {})
    bri = next((c for c in cards if c.get("bank") == "BRI"), {})
    check("A BNI not NOT_USED", bni.get("status") != "NOT_USED", str(bni))
    check("A BRI not NOT_USED", bri.get("status") != "NOT_USED", str(bri))
    check("A BNI expected EDC", bni.get("expected_edc") == 2_000_000, str(bni))
    check("A BRI expected EDC", bri.get("expected_edc") == 3_000_000, str(bri))
    cash = bzg.wizard_cash_summary(cid, conn=conn)
    check("A shift report cash", cash.get("shift_report_cash") == 3_000_000, str(cash))
    check("A expected cash computed", cash.get("expected_cash_in_till") is not None, str(cash))
    review = bzg.wizard_review_board(cid, conn=conn)
    check("A review sales from confirmed", review.get("sales_rp") == 8_000_000, str(review.get("sales_rp")))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_b_resume_bank_step_with_slips() -> None:
    from core import bzg_daily_close as bzg

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    cid, ref, ch = _open_sep03(conn)
    bzg.save_shift_human_corrections(
        cid,
        verified_person_id=MATT,
        figures=FIGURES,
        object_ref=ref,
        content_hash=ch,
        extracted={},
        identity={"person_id": MATT},
        allow_test_write=True,
        conn=conn,
        commit=True,
    )
    bzg.confirm_shift_figures_yes(
        cid,
        verified_person_id=MATT,
        object_ref=ref,
        content_hash=ch,
        extracted=FIGURES,
        conn=conn,
        commit=True,
    )
    bzg.ack_esb_data_difference(cid, verified_person_id=MATT, conn=conn, commit=True)
    resume = bzg.workflow_resume_step(cid, conn=conn)
    check("B resume bank step", resume.get("screen") == "bank_receipts", str(resume))
    disc = bzg.discover_unlinked_evidence_for_date(SEP03, conn=conn)
    check("B 3 Sep slips remain", len(disc.get("edc_receipts") or []) >= 4, str(disc))
    cards = bzg.wizard_bank_cards(cid, conn=conn).get("cards") or []
    need = [c for c in cards if c.get("status") == "RECEIPT_REQUIRED"]
    check("B banks need receipt", len(need) >= 2, str(need))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_c_search_register_matches_queue_and_empty_read_msg() -> None:
    from core import bzg_daily_close as bzg
    from core import uma_hist_close_queue1 as q

    html = (ROOT / "dashboards" / "uma-blu-close.html").read_text(encoding="utf-8")
    check("C empty read guard in readShiftReport", "shiftFiguresReadable(mergedShiftFigures())" in html)
    check("C refresh lists after submit", "await loadQueue()" in html and "await loadCalendar" in html)

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    reg = bzg.close_date_register(
        date_from="2026-09-25",
        date_to="2026-10-02",
        verified_person_id=MATT,
        conn=conn,
    )
    queue = q.owner_history_queue(verified_person_id=MATT, conn=conn)
    sep29_reg = next(
        (d for d in (reg.get("days") or []) if d.get("business_date") == "2026-09-29"),
        {},
    )
    sep29_q = next(
        (r for r in (queue.get("queue") or []) if r.get("business_date") == "2026-09-29"),
        {},
    )
    check(
        "C 29 Sep register CONTINUE",
        sep29_reg.get("action_label") == "CONTINUE",
        str(sep29_reg.get("action_label")),
    )
    check(
        "C 29 Sep queue/register action match",
        sep29_reg.get("action_label") == sep29_q.get("action_label"),
        f"{sep29_reg.get('action_label')} vs {sep29_q.get('action_label')}",
    )
    exc = next((r for r in (queue.get("queue") or []) if r.get("status") == "EXCEPTION"), None)
    if exc:
        exc_date = str(exc.get("business_date") or "")
        reg_exc = bzg.close_date_register(
            search=exc_date,
            verified_person_id=MATT,
            conn=conn,
        )
        day = next(
            (d for d in (reg_exc.get("days") or []) if d.get("business_date") == exc_date),
            {},
        )
        check("C exception REVIEW EXCEPTION", exc.get("action_label") == "REVIEW EXCEPTION")
        check(
            "C exception register label match",
            day.get("action_label") == exc.get("action_label"),
            f"{day.get('action_label')} vs {exc.get('action_label')}",
        )
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    test_a_edit_confirm_drives_banks_and_cash()
    test_b_resume_bank_step_with_slips()
    test_c_search_register_matches_queue_and_empty_read_msg()
    print(f"\nSUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
