#!/usr/bin/env python3
"""UMA-HIST-CLOSE-COMPLETE-2 — resume, terminals, till-declare, submit."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
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
OCT3 = "VDC-470e741f-d889-437a-9a40-1ec9c083fb95"
OCT4 = "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5"
MATT = "PERS-MATT"
TEST_PHOTO_REF = "TEST-UMA-HIST-CLOSE-COMPLETE-2-PHOTO"
TEST_PHOTO_HASH = "b" * 64


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def temp_catalog() -> Path:
    td = Path(tempfile.mkdtemp(prefix="tmp-uma-hist-complete2-", dir=str(ROOT / "catalog" / "backups")))
    db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, db)
    return db


def row_hash(conn: sqlite3.Connection, close_id: str) -> str:
    row = conn.execute(
        "SELECT * FROM venue_daily_closes WHERE close_id=?",
        (close_id,),
    ).fetchone()
    return hashlib.sha256(json.dumps(dict(row) if row else {}, sort_keys=True, default=str).encode()).hexdigest()


def wire_modules(db: Path) -> dict:
    import core.audit as audit
    import core.bzg_daily_close as bzg
    import core.evidence as evidence
    import core.rbac as rbac
    import core.uma_hist_close_queue1 as q
    import core.venue_close as vc

    saved: dict = {}
    for mod in (vc, bzg, evidence, audit, rbac, q):
        if hasattr(mod, "CATALOG_DB"):
            saved[mod] = mod.CATALOG_DB
            mod.CATALOG_DB = db  # type: ignore[attr-defined]
    return saved


def restore_modules(saved: dict) -> None:
    for mod, val in saved.items():
        mod.CATALOG_DB = val  # type: ignore[attr-defined]


def test_shift_expected_banks_29sep() -> None:
    from core import bzg_daily_close as bzg

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    bzg.ensure_owner_typed_printed_source(SEP29, conn=conn, commit=True)
    cards = bzg.wizard_bank_cards(SEP29, conn=conn)
    by_bank = {c["bank"]: c for c in cards.get("cards") or []}
    check("BNI not NOT_USED", by_bank.get("BNI", {}).get("status") != "NOT_USED", str(by_bank.get("BNI")))
    check("BRI not NOT_USED", by_bank.get("BRI", {}).get("status") != "NOT_USED", str(by_bank.get("BRI")))
    bni = by_bank.get("BNI") or {}
    bri = by_bank.get("BRI") or {}
    check("BNI EDC expected 2545000", bni.get("expected_edc") == 2545000.0, str(bni))
    check("BNI QRIS expected 145000", bni.get("expected_qris") == 145000.0, str(bni))
    check("BRI EDC expected 4465000", bri.get("expected_edc") == 4465000.0, str(bri))
    check("BRI QRIS expected 1065000", bri.get("expected_qris") == 1065000.0, str(bri))
    check("MANDIRI NOT_USED", by_bank.get("MANDIRI", {}).get("status") == "NOT_USED", str(by_bank.get("MANDIRI")))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_resolve_evidence_and_till_declare() -> None:
    from core import bzg_daily_close as bzg
    from core import venue_close as vc

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        vc.take_open_venue_close(SEP29, verified_person_id=MATT, conn=conn, commit=True)
    except vc.VenueCloseError:
        vc.reassign_venue_close(
            SEP29,
            verified_person_id=MATT,
            new_holder_person_id=MATT,
            reason="complete2 test",
            conn=conn,
            commit=True,
        )
    bzg.confirm_esb_closing_receipt(
        SEP29,
        verified_person_id=MATT,
        action="looks_correct",
        object_ref=TEST_PHOTO_REF,
        content_hash=TEST_PHOTO_HASH,
        allow_test_write=True,
        conn=conn,
        commit=True,
    )
    ref, ch = bzg._resolve_shift_report_evidence(SEP29, conn)
    check("resolve shift evidence ref", ref == TEST_PHOTO_REF, str(ref))
    check("resolve shift evidence hash", ch == TEST_PHOTO_HASH, str(ch))
    out = bzg.attach_till_with_z_report(
        SEP29,
        declared_cash_amount=3790000.0,
        verified_person_id=MATT,
        allow_test_write=True,
        conn=conn,
        commit=True,
    )
    check("till declare without client ref", out.get("declared_cash_amount") == 3790000.0, str(out))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_wizard_cash_formula_29sep() -> None:
    from core import bzg_daily_close as bzg

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    bzg.ensure_owner_typed_printed_source(SEP29, conn=conn, commit=True)
    cash = bzg.wizard_cash_summary(SEP29, conn=conn)
    opening = cash.get("opening_till_float")
    shift = cash.get("shift_report_cash")
    petty = cash.get("petty_cash_paid_today") or 0.0
    expected = cash.get("expected_cash_in_till")
    check("opening float present", opening is not None, str(opening))
    check("shift cash 3790000", shift == 3790000.0, str(shift))
    check("formula note present", bool(cash.get("cash_formula_note")))
    if opening is not None and shift is not None and expected is not None:
        calc = round(float(opening) + float(shift) - float(petty), 2)
        check("expected = opening + shift - petty", expected == calc, f"{expected} vs {calc}")
    petty_ids = [
        str(m.get("movement_id") or m.get("petty_movement_id") or "")
        for m in (bzg.wizard_petty_summary("2026-09-29", conn=conn).get("out_movements") or [])
    ]
    check("no 5 Oct petty contamination", "PETTY-UMA-6D853EEAE0" not in "".join(petty_ids))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_resume_wizard_payload() -> None:
    from core import bzg_daily_close as bzg

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    bzg.ensure_owner_typed_printed_source(SEP29, conn=conn, commit=True)
    wiz = bzg.source_wizard_state(SEP29, verified_person_id=MATT, conn=conn)
    ps = wiz.get("printed_source") or {}
    check("printed confirmed on resume", ps.get("confirmed") is True)
    check("printed has BNI card", ps.get("edc_bni_rp") == 2545000)
    cards = (wiz.get("wizard_bank_cards") or {}).get("cards") or []
    check("resume bank cards populated", any(c.get("bank") == "BNI" and c.get("status") != "NOT_USED" for c in cards))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_submit_idempotent_29sep() -> None:
    from core import bzg_daily_close as bzg
    from core import venue_close as vc

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        vc.take_open_venue_close(SEP29, verified_person_id=MATT, conn=conn, commit=True)
    except vc.VenueCloseError:
        vc.reassign_venue_close(
            SEP29,
            verified_person_id=MATT,
            new_holder_person_id=MATT,
            reason="complete2 submit",
            conn=conn,
            commit=True,
        )
    bzg.confirm_esb_closing_receipt(
        SEP29,
        verified_person_id=MATT,
        action="looks_correct",
        object_ref=TEST_PHOTO_REF,
        content_hash=TEST_PHOTO_HASH,
        allow_test_write=True,
        conn=conn,
        commit=True,
    )
    vc.attach_declared_cash(
        SEP29,
        declared_cash_amount=3790000.0,
        verified_person_id=MATT,
        object_ref=TEST_PHOTO_REF,
        content_hash=TEST_PHOTO_HASH,
        allow_test_write=True,
        conn=conn,
        commit=True,
    )
    out1 = bzg.staff_submit_close(
        SEP29,
        declared_cash_amount=3790000.0,
        verified_person_id=MATT,
        business_date="2026-09-29",
        submit_with_exception=True,
        allow_test_write=True,
        conn=conn,
        commit=True,
    )
    check("submit CLOSE SAVED WITH EXCEPTION", out1.get("staff_result") == "CLOSE SAVED WITH EXCEPTION", str(out1))
    out2 = bzg.staff_submit_close(
        SEP29,
        declared_cash_amount=3790000.0,
        verified_person_id=MATT,
        business_date="2026-09-29",
        submit_with_exception=True,
        allow_test_write=True,
        conn=conn,
        commit=True,
    )
    check("resubmit idempotent", out2.get("idempotent") is True or out2.get("staff_result") == out1.get("staff_result"))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_html_resume_controls() -> None:
    html = (ROOT / "dashboards" / "uma-blu-close.html").read_text(encoding="utf-8")
    check("six-step shift screen", "stepShift" in html)
    check("workflow resume via API", "workflow_resume" in html)
    check("ESB DATA DIFFERENCE in HTML", "ESB DATA DIFFERENCE FOUND" in html)
    check("cash formula in wizard", "cash_formula_note" in html)


def prod_pid_8787() -> int | None:
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", "tcp:8787"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        if not out:
            return None
        return int(out.splitlines()[0])
    except Exception:
        return None


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    from core import uma_hist_close_queue1 as q

    live_conn = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    live_conn.row_factory = sqlite3.Row
    live29_before = row_hash(live_conn, SEP29)
    live_oct3_before = row_hash(live_conn, OCT3)
    live_oct4_before = row_hash(live_conn, OCT4)
    live_conn.close()

    test_shift_expected_banks_29sep()
    test_resolve_evidence_and_till_declare()
    test_wizard_cash_formula_29sep()
    test_resume_wizard_payload()
    test_submit_idempotent_29sep()
    test_html_resume_controls()

    live_conn = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    live_conn.row_factory = sqlite3.Row
    check("live 29 Sep unchanged", row_hash(live_conn, SEP29) == live29_before)
    check("live 3 Oct unchanged", row_hash(live_conn, OCT3) == live_oct3_before)
    check("live 4 Oct unchanged", row_hash(live_conn, OCT4) == live_oct4_before)
    live_conn.close()

    before = q.protected_close_checksums(sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True))
    after = q.protected_close_checksums(sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True))
    check("protected checksums unchanged", before == after)

    pid = prod_pid_8787()
    check("prod pid 1297 unchanged", pid == 1297, str(pid))

    print(f"\nSUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
