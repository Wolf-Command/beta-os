#!/usr/bin/env python3
"""IZA-CLOSE-TONIGHT-2026-10-03 — bank supersede + NOT_USED before shift receipt.

Temp DB only. One CURRENT counted row per bank; superseded history kept.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
MIG031 = SCRIPTS / "migrations" / "migrate_bzg_daily_close_till_edc_1.py"
MIG032 = SCRIPTS / "migrations" / "migrate_bzg_daily_close_multi_edc_vision_1.py"
UMA_MIG = SCRIPTS / "migrations" / "migrate_uma_blu_daily_close.py"
PASS = 0
FAIL = 0
TS = "2026-10-03T00:00:00+08:00"
BIZ = "2026-10-03"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def make_esb(path: Path, *, biz_date: str = BIZ) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("DROP TABLE IF EXISTS sales")
        conn.execute(
            "CREATE TABLE sales (nk TEXT PRIMARY KEY, biz_date TEXT, raw TEXT, pulled_at TEXT)"
        )
        raw = {
            "branchCode": "BLZ",
            "salesNum": "S1",
            "billNum": "B1",
            "statusName": "Finished",
            "grandTotal": 150000.0,
            "paymentTotal": 150000.0,
            "salesPayments": [
                {"paymentMethodTypeName": "CASH", "paymentAmount": 50000.0},
                {"paymentMethodTypeName": "EDC Mandiri", "paymentAmount": 50000.0},
                {"paymentMethodTypeName": "QRIS BNI", "paymentAmount": 50000.0},
            ],
        }
        conn.execute(
            "INSERT INTO sales (nk, biz_date, raw, pulled_at) VALUES (?,?,?,?)",
            ("BLZ|S1", biz_date, json.dumps(raw), f"{biz_date}T20:00:00+08:00"),
        )
        conn.commit()
    finally:
        conn.close()


def seed_test_closer(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES ('PERS-TEST-CLOSER', 'Test Closer', NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES ('ASG-TEST-CLOSER-1', 'PERS-TEST-CLOSER', 'POS-BZG-CLOSER-UMA-1',
                  ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET status='ACTIVE', end_at=NULL, updated_at=excluded.updated_at
        """,
        (TS, TS, TS),
    )
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(conn, "ASG-TEST-CLOSER-1", "SCOPE-BZG-UMA", TS, TS)
    conn.execute(
        """
        INSERT INTO venue_closer_roster (
          roster_id, brand_id, position_id, person_id, assignment_id,
          status, note, created_at, updated_at
        ) VALUES (
          'VCR-UMA-TEST-1', 'BZG-UMA', 'POS-BZG-CLOSER-UMA-1', 'PERS-TEST-CLOSER',
          'ASG-TEST-CLOSER-1', 'ACTIVE', 'test closer roster', ?, ?
        )
        ON CONFLICT(roster_id) DO UPDATE SET
          person_id=excluded.person_id,
          assignment_id=excluded.assignment_id,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (TS, TS),
    )
    conn.commit()


def shift_doc_with_banks(
    *,
    mandiri_edc: float = 50000.0,
    bni_edc: float = 0.0,
    bni_qris: float = 0.0,
    bri_edc: float = 0.0,
    bri_qris: float = 0.0,
) -> dict:
    return {
        "document_kind": "ESB_CLOSING_RECEIPT",
        "schema_version": 1,
        "sections": [
            {
                "raw_title": "Payment Method Summary",
                "normalized_type": "PAYMENT_METHODS",
                "classification": "KNOWN",
                "lines": [
                    {
                        "raw_label": "CASH",
                        "normalized_type": "CASH",
                        "amount": 50000.0,
                        "human_confirmed_value": 50000.0,
                    },
                    {
                        "raw_label": "EDC MANDIRI",
                        "normalized_type": "EDC",
                        "bank_acquirer": "MANDIRI",
                        "amount": mandiri_edc,
                        "human_confirmed_value": mandiri_edc,
                    },
                    {
                        "raw_label": "EDC BNI",
                        "normalized_type": "EDC",
                        "bank_acquirer": "BNI",
                        "amount": bni_edc,
                        "human_confirmed_value": bni_edc,
                    },
                    {
                        "raw_label": "QRIS BNI",
                        "normalized_type": "QRIS",
                        "bank_acquirer": "BNI",
                        "amount": bni_qris,
                        "human_confirmed_value": bni_qris,
                    },
                    {
                        "raw_label": "EDC BRI",
                        "normalized_type": "EDC",
                        "bank_acquirer": "BRI",
                        "amount": bri_edc,
                        "human_confirmed_value": bri_edc,
                    },
                    {
                        "raw_label": "QRIS BRI",
                        "normalized_type": "QRIS",
                        "bank_acquirer": "BRI",
                        "amount": bri_qris,
                        "human_confirmed_value": bri_qris,
                    },
                ],
            }
        ],
    }


def wire(tmp_db: Path, esb_path: Path):
    import core.venue_close as vc
    import core.bzg_daily_close as bzg
    import core.esb_close_snapshot as esb
    import core.evidence as ev
    import core.audit as au
    import core.work_items as wi
    import core.rbac as rb
    import core.organisation as org
    import core.scope as sc
    import core.identity as ident
    import core.bzg_outlet_registry as outlets
    import core.bzg_close_vision as vision

    for mod in (vc, bzg, ev, au, wi, rb, org, sc, ident, outlets, esb, vision):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = tmp_db
    os.environ["WOLF_ESB_SQLITE"] = str(esb_path)
    os.environ["WOLF_CLOSE_VISION_DRY"] = "0"
    return vc, bzg


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"

    td = Path(tempfile.mkdtemp(prefix="bzg-bank-sup-", dir=str(ROOT / "catalog" / "backups")))
    tmp_db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, tmp_db)
    esb_path = td / "esb.sqlite"
    make_esb(esb_path)

    for mig_path, name in (
        (UMA_MIG, "migrate_uma_blu_daily_close"),
        (MIG031, "migrate_bzg_daily_close_till_edc_1"),
        (MIG032, "migrate_bzg_daily_close_multi_edc_vision_1"),
    ):
        mig = load_mod(mig_path, name)
        mig.DB = tmp_db
        check(f"{name} migrate", mig.main() == 0)

    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    seed_test_closer(conn)
    conn.close()

    vc, bzg = wire(tmp_db, esb_path)

    opened = bzg.open_human_close(
        BIZ,
        verified_person_id="PERS-TEST-CLOSER",
        outlet_id="BZG-UMA",
    )
    cid = opened["close_id"]
    vc.capture_esb_snapshot(cid, verified_person_id="PERS-TEST-CLOSER")

    # Before shift receipt — banks must NOT be NOT_USED_TODAY
    pre = bzg.bank_cards(cid)
    pre_statuses = {c["bank"]: c["status"] for c in pre.get("cards") or []}
    check(
        "pre-shift not NOT_USED",
        all(s != "NOT_USED_TODAY" for s in pre_statuses.values()),
        str(pre_statuses),
    )
    check(
        "pre-shift needs shift report",
        all(s == "SHIFT_RECEIPT_NEEDED" for s in pre_statuses.values()),
        str(pre_statuses),
    )

    doc_zero_bri = shift_doc_with_banks()
    bzg.confirm_esb_closing_receipt(
        cid,
        verified_person_id="PERS-TEST-CLOSER",
        action="confirm",
        object_ref="photo://esb-shift-20261003",
        cash_amount=50000.0,
        edc_card_amount=50000.0,
        qris_amount=50000.0,
        confirmed_overrides={"document": doc_zero_bri},
        allow_test_write=True,
    )

    post = bzg.bank_cards(cid)
    by_bank = {c["bank"]: c for c in post.get("cards") or []}
    check("mandiri expected from shift", by_bank.get("MANDIRI", {}).get("esb_edc_expected") == 50000.0)
    check("bri NOT_USED explicit 0/0", by_bank.get("BRI", {}).get("status") == "NOT_USED_TODAY")
    check("bri no photo required", by_bank.get("BRI", {}).get("receipt_required") is False)

    # Two confirms same bank — supersede; totals count one receipt only
    r1 = bzg.confirm_edc_receipt(
        cid,
        verified_person_id="PERS-TEST-CLOSER",
        acquirer_label="Mandiri",
        edc_card_amount=50000.0,
        qris_amount=0.0,
        action="confirm",
        object_ref="photo://mandiri-1",
        content_hash="a" * 64,
        settlement_batch_date=BIZ,
        allow_test_write=True,
    )
    r2 = bzg.confirm_edc_receipt(
        cid,
        verified_person_id="PERS-TEST-CLOSER",
        acquirer_label="MANDIRI",
        edc_card_amount=50000.0,
        qris_amount=0.0,
        action="confirm",
        object_ref="photo://mandiri-2",
        content_hash="b" * 64,
        settlement_batch_date=BIZ,
        allow_test_write=True,
    )
    rt = r2.get("receipt_totals") or {}
    check("supersede one CURRENT mandiri", rt.get("confirmed_receipt_count") == 1, str(rt))
    check("TOTAL_EDC single receipt", rt.get("TOTAL_EDC") == 50000.0, str(rt.get("TOTAL_EDC")))
    check("TOTAL_QRIS zero", rt.get("TOTAL_QRIS") == 0.0, str(rt.get("TOTAL_QRIS")))

    receipts = bzg.list_edc_receipts(cid)
    mandiri_rows = [r for r in receipts if (r.get("acquirer_label") or "").upper().startswith("MAND")]
    current_m = [
        r
        for r in mandiri_rows
        if str(r.get("evidence_role") or "CURRENT").upper() == "CURRENT"
        and int(r.get("counted_in_totals") if r.get("counted_in_totals") is not None else 1) == 1
    ]
    superseded_m = [
        r for r in mandiri_rows if str(r.get("evidence_role") or "").upper() == "SUPERSEDED"
    ]
    check("mandiri exactly one CURRENT counted", len(current_m) == 1, str(len(current_m)))
    check("mandiri superseded history kept", len(superseded_m) >= 1, str(len(superseded_m)))
    check("duplicate warn allowed", r2.get("duplicate_warn") in (True, False))

    post_cards = bzg.bank_cards(cid)
    mandiri_card = next(c for c in post_cards.get("cards") or [] if c["bank"] == "MANDIRI")
    check("mandiri MATCH after confirm", mandiri_card.get("status") == "MATCH")

    print(f"\npass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
