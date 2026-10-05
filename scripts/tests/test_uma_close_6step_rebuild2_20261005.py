#!/usr/bin/env python3
"""UMA-CLOSE-6STEP-REBUILD-2 — cycle-2 fixes for progressive shift, cash basis, discovery."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import uuid
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


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def temp_catalog() -> Path:
    td = Path(tempfile.mkdtemp(prefix="tmp-uma-6step-r2-", dir=str(ROOT / "catalog" / "backups")))
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


def test_shift_figures_yes_ack() -> None:
    from core import bzg_daily_close as bzg
    from core import venue_close as vc

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    bzg.ensure_owner_typed_printed_source(SEP29, conn=conn, commit=True)
    out = bzg.confirm_shift_figures_yes(SEP29, verified_person_id=MATT, conn=conn, commit=True)
    check("shift figures yes ok", out.get("shift_figures_yes") is True)
    ack = bzg.get_workflow_ack(SEP29, "shift_figures_yes", conn=conn)
    check("shift figures yes ack stored", ack is not None)
    resume = bzg.workflow_resume_step(SEP29, conn=conn)
    check("resume past figures", resume.get("screen") != "shift_report_figures", str(resume))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_register_shift_photo_draft() -> None:
    from core import bzg_daily_close as bzg
    from core import venue_close as vc

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    ref = "close-receipt://EVD-CLOSE-ESB-TESTDRAFT.jpg"
    ch = "a" * 64
    reg = bzg.register_shift_report_photo(
        SEP29, object_ref=ref, content_hash=ch, verified_person_id=MATT, conn=conn, commit=True
    )
    check("draft registered", reg.get("human_confirm_status") == "DRAFT")
    ev = bzg.list_shift_report_evidence(SEP29, conn=conn)
    drafts = [r for r in (ev.get("reports") or []) if r.get("human_confirm_status") == "DRAFT"]
    check("draft in evidence list", len(drafts) >= 1, str(len(drafts)))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_cash_expected_basis_submit() -> None:
    from core import bzg_daily_close as bzg
    from core import venue_close as vc

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    bzg.ensure_owner_typed_printed_source(SEP29, conn=conn, commit=True)
    bzg.confirm_shift_figures_yes(SEP29, verified_person_id=MATT, conn=conn, commit=True)
    bzg.ack_esb_data_difference(SEP29, verified_person_id=MATT, conn=conn, commit=True)
    cash_wiz = bzg.wizard_cash_summary(SEP29, conn=conn)
    expected = cash_wiz.get("expected_cash_in_till")
    counted = 4_400_000.0
    bzg.declare_cash_with_note(
        SEP29,
        declared_cash_amount=counted,
        cash_why_note="Test short",
        verified_person_id=MATT,
        object_ref="close-receipt://EVD-CLOSE-ESB-TESTDRAFT.jpg",
        content_hash="a" * 64,
        allow_test_write=True,
        conn=conn,
        commit=True,
    )
    check("expected cash 4420000", expected == 4_420_000.0, str(expected))
    out = bzg.staff_submit_close(
        SEP29,
        declared_cash_amount=counted,
        verified_person_id=MATT,
        business_date="2026-09-29",
        submit_with_exception=True,
        allow_test_write=True,
        conn=conn,
        commit=True,
    )
    row = vc.get_close(SEP29, conn=conn) or {}
    variance = row.get("variance_cash_amount")
    check("variance vs wizard expected", variance == -20_000.0 or variance == 20000.0, str(variance))
    msg = out.get("staff_message") or ""
    check("formatted submit message", "Rp" in msg and "20" in msg, msg)
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_discover_sep03_unlinked() -> None:
    from core import bzg_daily_close as bzg

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    before = conn.execute("SELECT COUNT(*) FROM venue_daily_closes WHERE business_date=?", (SEP03,)).fetchone()[0]
    disc = bzg.discover_unlinked_evidence_for_date(SEP03, conn=conn)
    peek = bzg.peek_business_date(SEP03, conn=conn)
    after = conn.execute("SELECT COUNT(*) FROM venue_daily_closes WHERE business_date=?", (SEP03,)).fetchone()[0]
    check("3 Sep shift photos", len(disc.get("shift_reports") or []) >= 1, str(disc))
    check("3 Sep edc slips", len(disc.get("edc_receipts") or []) >= 4, str(len(disc.get("edc_receipts") or [])))
    check("peek no close created", before == after)
    check("peek discovered evidence", bool(peek.get("discovered_evidence")))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_date_register_status_unified() -> None:
    from core import bzg_daily_close as bzg
    from core import uma_hist_close_queue1 as q

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    reg = bzg.close_date_register(search="2026-09-29", conn=conn)
    queue = q.owner_history_queue(conn=conn)
    day = next((d for d in (reg.get("days") or []) if d.get("business_date") == "2026-09-29"), {})
    qrow = next((r for r in (queue.get("queue") or []) if r.get("business_date") == "2026-09-29"), {})
    check("29 Sep register status", day.get("status") == qrow.get("status"), f"{day.get('status')} vs {qrow.get('status')}")
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_review_exceptions_include_cash() -> None:
    from core import bzg_daily_close as bzg

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    bzg.ensure_owner_typed_printed_source(SEP29, conn=conn, commit=True)
    bzg.confirm_shift_figures_yes(SEP29, verified_person_id=MATT, conn=conn, commit=True)
    bzg.declare_cash_with_note(
        SEP29,
        declared_cash_amount=4_400_000.0,
        cash_why_note="Short note",
        verified_person_id=MATT,
        object_ref="close-receipt://EVD-CLOSE-ESB-TESTDRAFT.jpg",
        content_hash="a" * 64,
        allow_test_write=True,
        conn=conn,
        commit=True,
    )
    rev = bzg.wizard_review_board(SEP29, conn=conn)
    kinds = [e.get("kind") for e in (rev.get("exceptions") or [])]
    check("review has cash exception", "cash_difference" in kinds, str(kinds))
    check("opening float in review", rev.get("opening_till_float") == 1_000_000.0)
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    test_shift_figures_yes_ack()
    test_register_shift_photo_draft()
    test_cash_expected_basis_submit()
    test_discover_sep03_unlinked()
    test_date_register_status_unified()
    test_review_exceptions_include_cash()
    print(f"\nSUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
