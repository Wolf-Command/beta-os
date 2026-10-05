#!/usr/bin/env python3
"""FCR-BZG-28 — manual fallback when receipt image extraction fails.

Temp DB + temp receipt bytes only. Never writes catalog/content_library.sqlite.
Never touches state/bzg-daily-close/receipts/. Protected closes not updated.
Forces vision dry-run (no live provider). No fixture_fields on extract path.
"""
from __future__ import annotations

import hashlib
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
PROTECTED = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-87202768-55af-4c8e-abc3-382a5496b8c6",
)
MIG031 = SCRIPTS / "migrations" / "migrate_bzg_daily_close_till_edc_1.py"
MIG032 = SCRIPTS / "migrations" / "migrate_bzg_daily_close_multi_edc_vision_1.py"
UMA_MIG = SCRIPTS / "migrations" / "migrate_uma_blu_daily_close.py"

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


def load_mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def make_esb(path: Path, biz_date: str) -> None:
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
            "grandTotal": 500000.0,
            "paymentTotal": 500000.0,
            "salesPayments": [
                {"paymentMethodTypeName": "EDC Mandiri", "paymentAmount": 300000.0},
                {"paymentMethodTypeName": "EDC BNI", "paymentAmount": 0.0},
            ],
        }
        conn.execute(
            "INSERT INTO sales (nk, biz_date, raw, pulled_at) VALUES (?,?,?,?)",
            ("BLZ|S1", biz_date, json.dumps(raw), f"{biz_date}T20:00:00+08:00"),
        )
        conn.commit()
    finally:
        conn.close()


def closer_actor(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        """
        SELECT person_id FROM venue_closer_roster
        WHERE brand_id = 'BZG-UMA' AND status = 'ACTIVE'
        LIMIT 1
        """
    ).fetchone()
    if row:
        return str(row[0])
    row = conn.execute(
        """
        SELECT a.person_id
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        WHERE p.role_id = 'ROLE-BZG-CLOSER' AND a.status = 'ACTIVE' AND a.end_at IS NULL
        LIMIT 1
        """
    ).fetchone()
    assert row is not None
    return str(row[0])


def staff_safe(msg: str | None) -> bool:
    if not msg:
        return False
    low = msg.lower()
    banned = ("gemini", "anthropic", "openai", "claude", "gpt", "api_key", "401", "403")
    return "enter" in low and "manual" in low and not any(b in low for b in banned)


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["WOLF_CLOSE_VISION_DRY"] = "1"

    biz = "2099-09-28"
    td = Path(tempfile.mkdtemp(prefix="fcr-bzg-28-", dir=str(ROOT / "catalog" / "backups")))
    tmp_db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, tmp_db)
    esb_path = td / "esb.sqlite"
    receipt_dir = td / "receipts"
    receipt_dir.mkdir()
    make_esb(esb_path, biz)
    os.environ["WOLF_ESB_SQLITE"] = str(esb_path)

    for mig_path, name in (
        (UMA_MIG, "migrate_uma_blu_daily_close"),
        (MIG031, "migrate_bzg_daily_close_till_edc_1"),
        (MIG032, "migrate_bzg_daily_close_multi_edc_vision_1"),
    ):
        mig = load_mod(mig_path, name)
        mig.DB = tmp_db
        check(f"{name} migrate", mig.main() == 0)

    import core.audit as audit
    import core.bzg_daily_close as bzg
    import core.bzg_close_vision as vision
    import core.esb_close_snapshot as esb
    import core.evidence as evidence
    import core.rbac as rbac
    import core.venue_close as vc

    saved_catalog: dict = {}
    for mod in (vc, bzg, evidence, audit, rbac, esb):
        if hasattr(mod, "CATALOG_DB"):
            saved_catalog[mod] = mod.CATALOG_DB
            mod.CATALOG_DB = tmp_db  # type: ignore[attr-defined]
    bzg.CLOSE_RECEIPT_DIR = receipt_dir

    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    cid: str | None = None
    try:
        for pid in PROTECTED:
            row = conn.execute(
                "SELECT state FROM venue_daily_closes WHERE close_id=?", (pid,)
            ).fetchone()
            check(f"protected {pid[:12]}… present", row is not None)

        closer = closer_actor(conn)
        check("closer actor resolved", bool(closer))

        bzg.configure_outlet_settlement_banks("BZG-UMA", conn=conn)

        opened = bzg.open_human_close(
            biz, verified_person_id=closer, outlet_id="BZG-UMA"
        )
        cid = str(opened["close_id"])
        check("close opened (not blocked)", opened.get("state") == "OPEN")

        vc.capture_esb_snapshot(
            cid,
            verified_person_id=closer,
            business_date=biz,
            esb_path=esb_path,
            conn=conn,
            commit=True,
        )

        img = b"FCR-BZG-28-FORCE-EXTRACT-FAIL-BYTES"
        saved = bzg.save_close_receipt_bytes(data=img, kind="edc", close_id=cid)
        img_hash = hashlib.sha256(img).hexdigest()

        draft = bzg.extract_edc_receipt_draft(
            cid,
            verified_person_id=closer,
            image_bytes=img,
            image_object_ref=saved["object_ref"],
            content_hash=img_hash,
            bank_hint="MANDIRI",
            conn=conn,
            commit=True,
        )
        check("extract returns ok (soft fail)", draft.get("ok") is True)
        check(
            "extraction_unavailable flagged",
            draft.get("extraction_unavailable") is True,
            str(draft.get("extraction_unavailable")),
        )
        check(
            "staff-safe failure message",
            staff_safe(draft.get("staff_message") or draft.get("message")),
            str(draft.get("staff_message")),
        )
        check("manual_entry_ok on failure", draft.get("manual_entry_ok") is True)
        check(
            "temporarily unavailable copy",
            "temporarily unavailable" in vision.STAFF_VISION_UNAVAILABLE.lower(),
        )

        ext = draft.get("extracted") or {}
        check(
            "extracted amounts not zero-filled",
            ext.get("edc_card_amount") is None and ext.get("qris_amount") is None,
            str(ext),
        )
        check(
            "extracted not marked confirmed",
            ext.get("extraction_status") == "UNAVAILABLE",
            str(ext.get("extraction_status")),
        )

        rcpt_count = conn.execute(
            "SELECT COUNT(*) FROM venue_close_edc_receipts WHERE close_id=?", (cid,)
        ).fetchone()[0]
        check("no edc receipt row written on fail", int(rcpt_count) == 0, str(rcpt_count))

        zero_rows = conn.execute(
            """
            SELECT COUNT(*) FROM venue_close_edc_receipts
            WHERE close_id=? AND (edc_card_amount=0 AND qris_amount=0)
            """,
            (cid,),
        ).fetchone()[0]
        check("no zero-amount receipt rows", int(zero_rows) == 0, str(zero_rows))

        manual_amt = 275000.0
        confirmed = bzg.confirm_edc_receipt(
            cid,
            verified_person_id=closer,
            acquirer_label="MANDIRI",
            edc_card_amount=manual_amt,
            qris_amount=0.0,
            action="confirm",
            object_ref=saved["object_ref"],
            content_hash=img_hash,
            settlement_batch_date=biz,
            extracted=draft.get("extracted"),
            vision_event_id=draft.get("vision_event_id"),
            manual_entry=True,
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        check("manual confirm ok", confirmed.get("ok") is True)
        check(
            "manual entry_source stored",
            confirmed.get("entry_source") == "MANUAL",
            str(confirmed.get("entry_source")),
        )
        check(
            "not stored as vision-confirmed extract",
            confirmed.get("entry_source") != "VISION_CONFIRMED",
        )
        rec = confirmed["edc_receipts"][-1]
        conf_blob = rec.get("confirmed") or {}
        check(
            "confirmed_json entry_source MANUAL",
            conf_blob.get("entry_source") == "MANUAL",
            str(conf_blob.get("entry_source")),
        )
        check(
            "vision_extract_succeeded false",
            conf_blob.get("vision_extract_succeeded") is False,
        )
        check(
            "manual amount persisted",
            float(rec.get("edc_card_amount") or 0) == manual_amt,
            str(rec.get("edc_card_amount")),
        )

        cards = bzg.bank_cards(cid, conn=conn)
        by_bank = {c["bank"]: c for c in cards.get("cards") or []}
        check("BNI bank card present", "BNI" in by_bank, str(list(by_bank.keys())))
        bni = by_bank.get("BNI") or {}
        check(
            "missing BNI line stays absent not zero",
            bni.get("actual_edc") is None and bni.get("actual_qris") is None,
            str(bni),
        )
        mandiri = by_bank.get("MANDIRI") or {}
        check(
            "MANDIRI manual figure on card",
            float(mandiri.get("actual_edc") or 0) == manual_amt,
            str(mandiri.get("actual_edc")),
        )

        close_row = vc.get_close(cid, conn=conn)
        close_state = str(close_row.get("state") or "")
        check(
            "close not blocked after fail+manual",
            close_state not in vc.TERMINAL,
            close_state,
        )
    finally:
        conn.close()

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
