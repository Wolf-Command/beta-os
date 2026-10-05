#!/usr/bin/env python3
"""FCR-BZG-19 — original evidence preservation on venue-close path.

Temp DB + temp receipt bytes only. Never writes catalog/content_library.sqlite.
Never touches state/bzg-daily-close/receipts/. Protected closes not updated.
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
            "grandTotal": 100000.0,
            "paymentTotal": 100000.0,
            "salesPayments": [
                {"paymentMethodTypeName": "EDC Mandiri", "paymentAmount": 100000.0},
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


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"

    biz = "2099-09-19"
    td = Path(tempfile.mkdtemp(prefix="fcr-bzg-19-", dir=str(ROOT / "catalog" / "backups")))
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
        check("closer actor from roster/assignment", bool(closer))

        opened = bzg.open_human_close(
            biz, verified_person_id=closer, outlet_id="BZG-UMA"
        )
        cid = str(opened["close_id"])
        check("close opened", opened.get("state") == "OPEN")

        vc.capture_esb_snapshot(
            cid,
            verified_person_id=closer,
            business_date=biz,
            esb_path=esb_path,
            conn=conn,
            commit=True,
        )

        orig_bytes = b"FCR-BZG-19-ORIGINAL-EDC-RECEIPT-BYTES"
        orig_saved = bzg.save_close_receipt_bytes(
            data=orig_bytes, kind="edc", close_id=cid
        )
        orig_hash = hashlib.sha256(orig_bytes).hexdigest()

        r1 = bzg.confirm_edc_receipt(
            cid,
            verified_person_id=closer,
            acquirer_label="MANDIRI",
            edc_card_amount=100000.0,
            qris_amount=0.0,
            action="confirm",
            object_ref=orig_saved["object_ref"],
            content_hash=orig_hash,
            settlement_batch_date=biz,
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        orig_evid = str(r1["evidence"]["evidence_id"])
        orig_rid = str(r1["edc_receipt_id"])

        later_bytes = b"FCR-BZG-19-LATER-EDC-RECEIPT-BYTES-CURRENT"
        later_saved = bzg.save_close_receipt_bytes(
            data=later_bytes, kind="edc", close_id=cid
        )
        later_hash = hashlib.sha256(later_bytes).hexdigest()

        r2 = bzg.confirm_edc_receipt(
            cid,
            verified_person_id=closer,
            acquirer_label="mandiri",
            edc_card_amount=100000.0,
            qris_amount=0.0,
            action="confirm",
            object_ref=later_saved["object_ref"],
            content_hash=later_hash,
            settlement_batch_date=biz,
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        later_evid = str(r2["evidence"]["evidence_id"])
        later_rid = str(r2["edc_receipt_id"])

        orig_read = bzg.read_preserved_close_evidence(orig_evid, conn=conn)
        later_read = bzg.read_preserved_close_evidence(later_evid, conn=conn)

        receipts = bzg.list_edc_receipts(cid, conn=conn)
        orig_rcpt = next(r for r in receipts if r["edc_receipt_id"] == orig_rid)
        current = [
            r
            for r in receipts
            if str(r.get("evidence_role") or "CURRENT").upper() == "CURRENT"
            and r.get("human_confirm_status") in ("CONFIRMED", "EDITED")
        ]

        check("original evidence row readable", orig_read.get("readable") is True)
        check(
            "original bytes unchanged",
            orig_read.get("bytes") == orig_bytes,
            str(orig_read.get("bytes_len")),
        )
        check("original hash still matches", orig_read.get("content_hash_match") is True)
        check("original evidence still ACTIVE", orig_read.get("original_preserved") is True)
        check(
            "original receipt SUPERSEDED not deleted",
            orig_rcpt.get("evidence_role") == "SUPERSEDED",
            str(orig_rcpt.get("evidence_role")),
        )
        check(
            "original evidence_id on receipt unchanged",
            orig_rcpt.get("evidence_id") == orig_evid,
            str(orig_rcpt.get("evidence_id")),
        )

        check("later evidence row readable", later_read.get("readable") is True)
        check("later bytes stored", later_read.get("bytes") == later_bytes)
        check("later is CURRENT", len(current) == 1 and current[0]["edc_receipt_id"] == later_rid)
        check(
            "later evidence_id on CURRENT receipt",
            current[0].get("evidence_id") == later_evid,
        )

        rt = bzg.receipt_totals(cid, conn=conn)
        check("totals count one CURRENT", rt.get("confirmed_receipt_count") == 1)

    finally:
        conn.close()
        for mod, path in saved_catalog.items():
            mod.CATALOG_DB = path  # type: ignore[attr-defined]

    print(f"\npass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
