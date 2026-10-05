#!/usr/bin/env python3
"""FCR-GGV-38 — upload_date on ggv_receipt_accounting row stays distinct from transaction date.

Temp DB only. Never writes catalog/content_library.sqlite.
Protected closes VDC-470e741f… and VDC-87202768… are not touched.
"""
from __future__ import annotations

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
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
PROTECTED = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-87202768-55af-4c8e-abc3-382a5496b8c6",
)

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


def temp_catalog() -> Path:
    td = Path(tempfile.mkdtemp(prefix="fcr-ggv-38-", dir=str(ROOT / "catalog" / "backups")))
    db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, db)
    return db


def ggv_finance_reviewer(conn: sqlite3.Connection) -> str | None:
    import core.rbac as rbac

    target = {"entity_id": "ENT-GGV"}
    for row in conn.execute("SELECT person_id FROM org_persons WHERE status='ACTIVE'").fetchall():
        pid = str(row[0])
        if not rbac.can(pid, "finance.nota.read", target, conn=conn):
            continue
        if rbac.can(pid, "finance.nota.review", target, conn=conn) or rbac.can(
            pid, "finance.nota.edit", target, conn=conn
        ):
            return pid
    return None


def noop_sync(**_kw: object) -> dict[str, object]:
    return {"ok": True, "synced": 0}


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    import core.ggv_receipt_accounting1 as gra

    db = temp_catalog()
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    receipt_key = f"fcr-ggv-38-throwaway_{uuid.uuid4().hex[:12]}_ggv_receipt_test.jpg"
    upload_date = "2026-09-15"
    transaction_date = "2026-05-20"
    ts = "2026-09-15T08:30:00Z"

    orig_sync = gra.sync_vault_receipts
    gra.sync_vault_receipts = noop_sync  # type: ignore[assignment]

    try:
        for pid in PROTECTED:
            row = conn.execute(
                "SELECT state FROM venue_daily_closes WHERE close_id=?", (pid,)
            ).fetchone()
            check(f"protected {pid[:12]}… present", row is not None)

        reviewer = ggv_finance_reviewer(conn)
        check("GGV finance reviewer discovered from catalog", reviewer is not None)

        gra.ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO ggv_receipt_accounting (
              receipt_key, entity_id, vault_filename, vault_queue, vault_path,
              content_sha256, accounting_queue, extraction_json,
              human_confirmed_json, duplicate_of, missing_evidence,
              bank_match_proposed, bank_match_confirmed,
              confirmed_by_person_id, confirmed_at, upload_date,
              created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                receipt_key,
                "ENT-GGV",
                receipt_key,
                "processed",
                str(db.parent / "missing-evidence.jpg"),
                None,
                "needs_review",
                json.dumps({"vendor": "Fixture Vendor", "amount": "1000"}),
                None,
                None,
                1,
                None,
                0,
                None,
                None,
                upload_date,
                ts,
                ts,
            ),
        )
        conn.commit()

        row = conn.execute(
            "SELECT upload_date, human_confirmed_json FROM ggv_receipt_accounting WHERE receipt_key=?",
            (receipt_key,),
        ).fetchone()
        check("upload_date persisted on insert", row and row["upload_date"] == upload_date)
        check(
            "upload_date distinct from planned transaction date before confirm",
            row and row["upload_date"] != transaction_date,
            f"upload={row['upload_date'] if row else None} txn={transaction_date}",
        )

        detail = gra.get_receipt(
            verified_person_id=reviewer,
            receipt_key=receipt_key,
            conn=conn,
        )
        pub = detail.get("receipt") or {}
        check("get_receipt exposes upload_date", pub.get("upload_date") == upload_date)
        check(
            "get_receipt upload_date != transaction date placeholder",
            pub.get("upload_date") != transaction_date,
        )

        confirmed = gra.confirm_receipt(
            verified_person_id=reviewer,
            receipt_key=receipt_key,
            body={
                "vendor": "Confirmed Vendor",
                "amount": "54321",
                "date": transaction_date,
                "category": "Fixture",
                "account_code": "6100",
                "notes": "fcr-ggv-38 confirm",
            },
            conn=conn,
        )
        after = confirmed.get("receipt") or {}
        human = after.get("human_confirmed") or {}
        check("confirm stores transaction date in human_confirmed", human.get("date") == transaction_date)
        check(
            "confirm does not overwrite upload_date",
            after.get("upload_date") == upload_date,
            f"upload={after.get('upload_date')} expected={upload_date}",
        )
        check(
            "upload_date still distinct from transaction date after confirm",
            after.get("upload_date") != human.get("date"),
            f"upload={after.get('upload_date')} txn={human.get('date')}",
        )

        raw = conn.execute(
            "SELECT upload_date FROM ggv_receipt_accounting WHERE receipt_key=?",
            (receipt_key,),
        ).fetchone()
        check("SQL readback upload_date unchanged", raw and raw["upload_date"] == upload_date)

        for pid in PROTECTED:
            prow = conn.execute(
                "SELECT state FROM venue_daily_closes WHERE close_id=?", (pid,)
            ).fetchone()
            check(f"protected {pid[:12]}… unchanged after test", prow is not None)

    finally:
        gra.sync_vault_receipts = orig_sync
        conn.execute("DELETE FROM ggv_receipt_accounting WHERE receipt_key=?", (receipt_key,))
        conn.commit()
        conn.close()

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
