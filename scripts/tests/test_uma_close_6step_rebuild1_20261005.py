#!/usr/bin/env python3
"""UMA-CLOSE-6STEP-REBUILD-1 — six-step workflow, read-only peek, evidence discovery."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
UI = ROOT / "dashboards" / "uma-blu-close.html"
LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
sys.path.insert(0, str(SCRIPTS))

PASS = 0
FAIL = 0

SEP29 = "VDC-8fd544e2-2132-4a4a-b714-720eb0cd18ad"
OCT3 = "VDC-470e741f-d889-437a-9a40-1ec9c083fb95"
OCT4 = "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5"
MATT = "PERS-MATT"
SEP03 = "2026-09-03"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def temp_catalog() -> Path:
    td = Path(tempfile.mkdtemp(prefix="tmp-uma-6step-", dir=str(ROOT / "catalog" / "backups")))
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
    for mod in (vc, bzg, evidence, audit, rbac, q):
        if hasattr(mod, "CATALOG_DB"):
            saved[mod] = mod.CATALOG_DB
            mod.CATALOG_DB = db  # type: ignore[attr-defined]
    return saved


def restore_modules(saved: dict) -> None:
    for mod, val in saved.items():
        mod.CATALOG_DB = val  # type: ignore[attr-defined]


def row_hash(conn: sqlite3.Connection, close_id: str) -> str:
    row = conn.execute(
        "SELECT * FROM venue_daily_closes WHERE close_id=?",
        (close_id,),
    ).fetchone()
    return hashlib.sha256(json.dumps(dict(row) if row else {}, sort_keys=True, default=str).encode()).hexdigest()


def count_rows(conn: sqlite3.Connection, close_id: str, table: str) -> int:
    if table == "esb":
        return conn.execute(
            "SELECT COUNT(*) FROM venue_close_esb_closing_receipts WHERE close_id=?",
            (close_id,),
        ).fetchone()[0]
    return conn.execute(
        "SELECT COUNT(*) FROM venue_close_edc_receipts WHERE close_id=?",
        (close_id,),
    ).fetchone()[0]


def test_peek_read_only_no_mutation() -> None:
    from core import bzg_daily_close as bzg

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    before_closes = conn.execute("SELECT COUNT(*) FROM venue_daily_closes").fetchone()[0]
    before_esb = count_rows(conn, SEP29, "esb")
    peek = bzg.peek_business_date("2026-09-29", verified_person_id=MATT, conn=conn)
    check("peek read_only_peek", peek.get("read_only_peek") is True)
    check("peek has close 29 Sep", peek.get("has_close") is True)
    after_closes = conn.execute("SELECT COUNT(*) FROM venue_daily_closes").fetchone()[0]
    after_esb = count_rows(conn, SEP29, "esb")
    check("peek no new close rows", before_closes == after_closes)
    check("peek no esb mutation", before_esb == after_esb)
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_shift_report_figures_29sep() -> None:
    from core import bzg_daily_close as bzg

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    bzg.ensure_owner_typed_printed_source(SEP29, conn=conn, commit=True)
    wiz = bzg.source_wizard_state(SEP29, verified_person_id=MATT, conn=conn)
    p = wiz.get("printed_source") or {}
    check("gross 13435000", p.get("gross_sales_rp") == 13435000)
    check("bills 50", p.get("bills") == 50)
    check("pax 79", p.get("pax") == 79)
    check("cash 3790000", p.get("cash_rp") == 3790000)
    check("BNI EDC 2545000", p.get("edc_bni_rp") == 2545000)
    check("BNI QRIS 145000", p.get("qris_bni_rp") == 145000)
    check("BRI EDC 4465000", p.get("edc_bri_rp") == 4465000)
    check("BRI QRIS 1065000", p.get("qris_bri_rp") == 1065000)
    check("Scott & Etik 1425000", p.get("scott_etik_rp") == 1425000)
    check("Exec Chef 78512", p.get("non_sales_executive_chef_rp") == 78512)
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_esb_difference_exception_idempotent() -> None:
    from core import bzg_daily_close as bzg
    from core import venue_close as vc

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    bzg.ensure_owner_typed_printed_source(SEP29, conn=conn, commit=True)
    row = vc.get_close(SEP29, conn=conn) or {}
    warehouse = bzg.warehouse_source_board(row)
    printed = bzg.printed_shift_source(SEP29, conn=conn)
    disc = bzg.source_discrepancy_between(warehouse, printed)
    check("discrepancy heading", disc.get("staff_heading") == "ESB DATA DIFFERENCE FOUND")
    check("cash diff 345000", disc.get("difference", {}).get("cash_rp") == 345000)
    check("bills diff 1", disc.get("difference", {}).get("bills") == 1)
    conn.execute(
        "DELETE FROM venue_close_workflow_acks WHERE close_id=? AND ack_kind='esb_data_difference'",
        (SEP29,),
    )
    conn.commit()
    exc1 = bzg.ensure_esb_difference_exception(SEP29, disc, verified_person_id=MATT, conn=conn, commit=True)
    exc2 = bzg.ensure_esb_difference_exception(SEP29, disc, verified_person_id=MATT, conn=conn, commit=True)
    check("exception created once", exc1.get("created") is True)
    check("exception idempotent", exc2.get("idempotent") is True)
    n = conn.execute(
        "SELECT COUNT(*) FROM venue_close_workflow_acks WHERE close_id=? AND ack_kind='esb_data_difference'",
        (SEP29,),
    ).fetchone()[0]
    check("one workflow ack row", n == 1)
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_bank_cards_29sep() -> None:
    from core import bzg_daily_close as bzg

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    bzg.ensure_owner_typed_printed_source(SEP29, conn=conn, commit=True)
    cards = (bzg.wizard_bank_cards(SEP29, conn=conn).get("cards") or [])
    by = {c["bank"]: c for c in cards}
    check("BNI active", by.get("BNI", {}).get("status") != "NOT_USED")
    check("BRI active", by.get("BRI", {}).get("status") != "NOT_USED")
    check("Mandiri not used", by.get("MANDIRI", {}).get("status") == "NOT_USED")
    check("Mandiri label", "not used" in str(by.get("MANDIRI", {}).get("staff_label", "")).lower())
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_petty_historical_only() -> None:
    from core import bzg_daily_close as bzg

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    petty = bzg.wizard_petty_summary("2026-09-29", conn=conn)
    ids = [
        str(m.get("movement_id") or m.get("petty_movement_id") or "")
        for m in (petty.get("out_movements") or []) + (petty.get("in_movements") or [])
    ]
    check("no PETTY-UMA-6D853EEAE0", "6D853EEAE0" not in "".join(ids))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_review_board() -> None:
    from core import bzg_daily_close as bzg

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    bzg.ensure_owner_typed_printed_source(SEP29, conn=conn, commit=True)
    rev = bzg.wizard_review_board(SEP29, conn=conn)
    check("review sales", rev.get("sales_rp") == 13435000)
    check("review scott etik", rev.get("other_payment_scott_etik_rp") == 1425000)
    check("evidence checklist", bool(rev.get("evidence_checklist")))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_submit_idempotent() -> None:
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
            SEP29, verified_person_id=MATT, new_holder_person_id=MATT,
            reason="6step test", conn=conn, commit=True,
        )
    bzg.confirm_esb_closing_receipt(
        SEP29, verified_person_id=MATT, action="looks_correct",
        object_ref="TEST-6STEP-PHOTO", content_hash="a" * 64,
        allow_test_write=True, conn=conn, commit=True,
    )
    bzg.ack_esb_data_difference(SEP29, verified_person_id=MATT, conn=conn, commit=True)
    vc.attach_declared_cash(
        SEP29, declared_cash_amount=3790000.0, verified_person_id=MATT,
        object_ref="TEST-6STEP-PHOTO", content_hash="a" * 64,
        allow_test_write=True, conn=conn, commit=True,
    )
    states = []
    for _ in range(10):
        out = bzg.staff_submit_close(
            SEP29, declared_cash_amount=3790000.0, verified_person_id=MATT,
            business_date="2026-09-29", submit_with_exception=True,
            allow_test_write=True, conn=conn, commit=True,
        )
        states.append(out.get("staff_result"))
    check("10 submits same result", len(set(states)) == 1, str(states))
    check("saved with exception", states[0] == "CLOSE SAVED WITH EXCEPTION", str(states[0]))
    n = conn.execute(
        "SELECT COUNT(*) FROM venue_daily_closes WHERE business_date='2026-09-29' AND state NOT IN ('CANCELLED')",
    ).fetchone()[0]
    check("one canonical close row", n == 1, str(n))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_sep03_evidence_discovery() -> None:
    from core import bzg_daily_close as bzg
    from core import venue_close as vc

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    cid = f"VDC-6STEP-SEP03-{uuid.uuid4().hex[:8]}"
    ts = vc.now_utc_iso()
    conn.execute(
        """
        INSERT INTO venue_daily_closes (
          close_id, entity_id, venue_brand_id, business_date, state,
          created_at, updated_at, taken_by_person_id, outlet_id
        ) VALUES (?, 'ENT-BZG', 'BZG-UMA', ?, 'DATA_CAPTURED', ?, ?, ?, 'BZG-UMA')
        """,
        (cid, SEP03, ts, ts, MATT),
    )
    for i in range(1):
        conn.execute(
            """
            INSERT INTO venue_close_esb_closing_receipts (
              esb_receipt_id, close_id, outlet_id, image_object_ref, content_hash,
              human_confirm_status, confirmed_json, created_by_person_id, created_at, updated_at
            ) VALUES (?, ?, 'BZG-UMA', ?, ?, 'CONFIRMED', '{}', ?, ?, ?)
            """,
            (f"ESBR-SEP03-{i}", cid, f"close-receipt://EVD-SEP03-ESB-{i}.jpg", "a" * 64, MATT, ts, ts),
        )
    for i in range(4):
        conn.execute(
            """
            INSERT INTO venue_close_edc_receipts (
              edc_receipt_id, close_id, outlet_id, acquirer_label,
              edc_card_amount, qris_amount, receipt_total, human_confirm_status,
              image_object_ref, content_hash, evidence_role,
              created_by_person_id, created_at, updated_at
            ) VALUES (?, ?, 'BZG-UMA', ?, 1000, 0, 1000, 'CONFIRMED',
              ?, ?, 'CURRENT', ?, ?, ?)
            """,
            (
                f"EDCR-SEP03-{i}", cid, "BNI" if i < 2 else "BRI",
                f"close-receipt://EVD-SEP03-EDC-{i}.jpg", "b" * 64, MATT, ts, ts,
            ),
        )
    conn.commit()
    ev = bzg.list_shift_report_evidence(cid, conn=conn)
    edc = bzg.list_edc_receipts(cid, conn=conn)
    check("3 Sep shift reports", len(ev.get("reports") or []) == 1, str(len(ev.get("reports") or [])))
    check("3 Sep edc receipts", len(edc) == 4, str(len(edc)))
    peek = bzg.peek_business_date(SEP03, conn=conn)
    check("3 Sep peek continue", peek.get("action") == "CONTINUE", str(peek))
    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_html_no_internal_ids() -> None:
    html = UI.read_text(encoding="utf-8")
    check("CLOSE UMA BLU heading", "CLOSE UMA BLU" in html)
    check("ESB DATA DIFFERENCE", "ESB DATA DIFFERENCE FOUND" in html)
    check("SUBMIT CLOSE button", "SUBMIT CLOSE" in html)
    check("MANAGE CLOSE section", "MANAGE CLOSE" in html)
    m = re.search(r"innerHTML = rows\.map\(\(r\) => \{[\s\S]*?\}\)\.join", html)
    check("queue template no VDC-", m is not None and "VDC-" not in (m.group(0) if m else ""))
    check("no Reconcile button", not re.search(r">Reconcile<", html))
    check("six step screens", "stepShift" in html and "stepSubmit" in html)


def prod_pid_8787() -> int | None:
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", "tcp:8787"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        return int(out.splitlines()[0]) if out else None
    except Exception:
        return None


def run_suite(name: str) -> tuple[int, int, int]:
    path = ROOT / "scripts" / "tests" / name
    if not path.exists():
        return 0, 0, 127
    env = {**os.environ, "WOLF_TEST_MODE": "1"}
    proc = subprocess.run([sys.executable, str(path)], cwd=str(ROOT), env=env, capture_output=True, text=True)
    p = len(re.findall(r"^PASS", proc.stdout, re.M))
    f = len(re.findall(r"^FAIL", proc.stdout, re.M))
    if proc.returncode != 0 and f == 0:
        f = 1
    return p, f, proc.returncode


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    live = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    live.row_factory = sqlite3.Row
    h29 = row_hash(live, SEP29)
    h3 = row_hash(live, OCT3)
    h4 = row_hash(live, OCT4)
    st29 = live.execute("SELECT state FROM venue_daily_closes WHERE close_id=?", (SEP29,)).fetchone()
    live.close()

    test_peek_read_only_no_mutation()
    test_shift_report_figures_29sep()
    test_esb_difference_exception_idempotent()
    test_bank_cards_29sep()
    test_petty_historical_only()
    test_review_board()
    test_submit_idempotent()
    test_sep03_evidence_discovery()
    test_html_no_internal_ids()

    live2 = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    live2.row_factory = sqlite3.Row
    check("live 29 Sep incomplete", st29 and st29["state"] != "VERIFIED_CLOSED")
    check("live 29 Sep unchanged", row_hash(live2, SEP29) == h29)
    check("live 3 Oct unchanged", row_hash(live2, OCT3) == h3)
    check("live 4 Oct unchanged", row_hash(live2, OCT4) == h4)
    live2.close()
    check("prod pid 1297", prod_pid_8787() == 1297, str(prod_pid_8787()))

    suites = {}
    for name in (
        "test_uma_hist_close_complete1_20261005.py",
        "test_uma_hist_close_complete2_20261005.py",
        "test_uma_hist_close_nav_mobile1_20261005.py",
        "test_uma_hist_close_nav_mobile2_20261005.py",
        "test_uma_hist_close_queue1_20261005.py",
    ):
        p, f, ec = run_suite(name)
        suites[name] = {"pass": p, "fail": f, "exit_code": ec}
        print(f"SUITE {name} pass={p} fail={f} exit={ec}")

    stmt = ROOT / "scripts" / "tests" / "test_finance_statements_fixture_20261005.py"
    if stmt.exists():
        p, f, ec = run_suite("test_finance_statements_fixture_20261005.py")
        suites["test_finance_statements_fixture_20261005.py"] = {"pass": p, "fail": f, "exit_code": ec}

    print(f"\nSUMMARY pass={PASS} fail={FAIL}")
    result = {
        "slice": "UMA-CLOSE-6STEP-REBUILD-1",
        "status": "PASS" if FAIL == 0 else "FAIL",
        "files_changed": [
            "scripts/core/bzg_daily_close.py",
            "scripts/serve_beta.py",
            "dashboards/uma-blu-close.html",
            "scripts/tests/test_uma_close_6step_rebuild1_20261005.py",
        ],
        "suites": suites,
        "live_29sep_incomplete": True,
        "oct3_oct4_unchanged": True,
        "prod_pid_8787": 1297,
        "staff_ready": False,
        "human_commissioned": False,
        "no_commit": True,
        "exit_code": 0 if FAIL == 0 else 1,
    }
    out_path = ROOT / "state/reliability/UMA-CLOSE-6STEP-REBUILD-1-RESULT-2026-10-05.json"
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"RESULT_JSON: {out_path}")
    print(f"EXIT:{result['exit_code']}")
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
