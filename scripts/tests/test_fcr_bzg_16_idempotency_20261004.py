#!/usr/bin/env python3
"""FCR-BZG-16 — refresh/idempotency on venue-close path.

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
    td = Path(tempfile.mkdtemp(prefix="fcr-bzg-16-", dir=str(ROOT / "catalog" / "backups")))
    db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, db)
    return db


def make_esb(path: Path, cash: float, biz_date: str) -> None:
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
            "grandTotal": cash,
            "paymentTotal": cash,
            "salesPayments": [
                {"paymentMethodTypeName": "CASH", "paymentAmount": cash}
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


def count_closes(conn: sqlite3.Connection, biz: str) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) FROM venue_daily_closes
        WHERE entity_id='ENT-BZG' AND venue_brand_id='BZG-UMA'
          AND business_date=? AND state != 'CANCELLED'
        """,
        (biz,),
    ).fetchone()
    return int(row[0]) if row else 0


def count_cash_evidence(conn: sqlite3.Connection, close_id: str) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) FROM core_evidence_records
        WHERE governed_object_id=? AND evidence_type='cash_count' AND status='ACTIVE'
        """,
        (close_id,),
    ).fetchone()
    return int(row[0]) if row else 0


def count_reopen_approvals(conn: sqlite3.Connection, close_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM venue_close_reopen_approvals WHERE close_id=?",
        (close_id,),
    ).fetchone()
    return int(row[0]) if row else 0


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    import core.audit as audit
    import core.bzg_daily_close as bzg
    import core.evidence as evidence
    import core.rbac as rbac
    import core.venue_close as vc

    db = temp_catalog()
    td = db.parent
    esb_path = td / "esb.sqlite"
    biz = "2099-05-16"
    cash_amt = 222000.0
    make_esb(esb_path, cash_amt, biz)
    os.environ["WOLF_ESB_SQLITE"] = str(esb_path)

    saved_catalog: dict = {}
    for mod in (vc, bzg, evidence, audit, rbac):
        if hasattr(mod, "CATALOG_DB"):
            saved_catalog[mod] = mod.CATALOG_DB
            mod.CATALOG_DB = db  # type: ignore[attr-defined]

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    cid: str | None = None
    try:
        for pid in PROTECTED:
            row = conn.execute(
                "SELECT state FROM venue_daily_closes WHERE close_id=?", (pid,)
            ).fetchone()
            check(f"protected {pid[:12]}… present", row is not None)

        closer = closer_actor(conn)
        check("closer actor from assignment", bool(closer))

        opened1 = vc.open_or_get(biz, verified_person_id=closer, conn=conn, commit=True)
        cid = str(opened1["close_id"])
        check("first open created", opened1.get("created") is True)
        check("first open not idempotent", not opened1.get("idempotent"))

        opened2 = vc.open_or_get(biz, verified_person_id=closer, conn=conn, commit=True)
        check("second open same close_id", str(opened2["close_id"]) == cid)
        check("second open idempotent", opened2.get("idempotent") is True)
        check("second open created false", opened2.get("created") is False)
        check("only one current close", count_closes(conn, biz) == 1)

        cap1 = vc.capture_esb_snapshot(
            cid,
            verified_person_id=closer,
            esb_path=esb_path,
            conn=conn,
            commit=True,
        )
        check("first capture mutated", cap1.get("mutated") is True)
        fp1 = str(cap1.get("esb_fingerprint_sha256") or "")

        cap2 = vc.capture_esb_snapshot(
            cid,
            verified_person_id=closer,
            esb_path=esb_path,
            conn=conn,
            commit=True,
        )
        check("second capture idempotent", cap2.get("idempotent") is True)
        check("second capture not mutated", cap2.get("mutated") is False)
        check(
            "capture fingerprint unchanged",
            str(cap2.get("esb_fingerprint_sha256") or "") == fp1,
        )

        dec1 = vc.attach_declared_cash(
            cid,
            declared_cash_amount=cash_amt,
            verified_person_id=closer,
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        check("first declare ok", dec1.get("declared_cash_amount") == cash_amt)
        ev1 = count_cash_evidence(conn, cid)

        dec2 = vc.attach_declared_cash(
            cid,
            declared_cash_amount=cash_amt,
            verified_person_id=closer,
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        check("second declare same amount idempotent", dec2.get("idempotent") is True)
        check("cash evidence count unchanged", count_cash_evidence(conn, cid) == ev1)

        dec3 = vc.attach_declared_cash(
            cid,
            declared_cash_amount=cash_amt - 1.0,
            verified_person_id=closer,
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        check(
            "different amount not idempotent",
            not dec3.get("idempotent"),
            str(dec3.get("idempotent")),
        )
        check(
            "different amount adds evidence row",
            count_cash_evidence(conn, cid) == ev1 + 1,
            f"ev={count_cash_evidence(conn, cid)}",
        )

        # Restore matching amount for submit path.
        vc.attach_declared_cash(
            cid,
            declared_cash_amount=cash_amt,
            verified_person_id=closer,
            allow_test_write=True,
            conn=conn,
            commit=True,
        )

        sub1 = bzg.staff_submit_close(
            cid,
            declared_cash_amount=cash_amt,
            verified_person_id=closer,
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        check("first submit complete", sub1.get("staff_result") == "CLOSE COMPLETE")
        appr1 = count_reopen_approvals(conn, cid)

        sub2 = bzg.staff_submit_close(
            cid,
            declared_cash_amount=cash_amt,
            verified_person_id=closer,
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        check("second submit idempotent", sub2.get("idempotent") is True)
        check("second submit complete", sub2.get("staff_result") == "CLOSE COMPLETE")
        check("approval count unchanged", count_reopen_approvals(conn, cid) == appr1)

        sub3 = bzg.staff_submit_close(
            cid,
            declared_cash_amount=cash_amt - 50.0,
            verified_person_id=closer,
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        check("different submit not idempotent", not sub3.get("idempotent"))
        check("different submit cannot submit", sub3.get("staff_result") == "CANNOT SUBMIT")
        check(
            "different submit amount_mismatch",
            sub3.get("cannot_reason") == "amount_mismatch",
        )

        rec = vc.reconcile(
            cid,
            verified_person_id=closer,
            esb_path=esb_path,
            conn=conn,
            commit=True,
        )
        check("reconcile on closed idempotent", rec.get("idempotent") is True)

        for pid in PROTECTED:
            row = conn.execute(
                "SELECT state FROM venue_daily_closes WHERE close_id=?", (pid,)
            ).fetchone()
            check(f"protected {pid[:12]}… unchanged after test", row is not None)

    finally:
        if cid:
            conn.execute("DELETE FROM venue_close_reopen_approvals WHERE close_id=?", (cid,))
            conn.execute("DELETE FROM venue_close_reopen_changes WHERE close_id=?", (cid,))
            conn.execute("DELETE FROM venue_close_reopen_events WHERE close_id=?", (cid,))
            conn.execute("DELETE FROM venue_close_final_history WHERE close_id=?", (cid,))
            conn.execute(
                """
                UPDATE core_evidence_records
                SET status='INVALIDATED',
                    invalidate_reason='FCR-BZG-16 test cleanup',
                    invalidated_at=datetime('now'),
                    updated_at=datetime('now')
                WHERE governed_object_id=?
                """,
                (cid,),
            )
            conn.execute("DELETE FROM venue_daily_closes WHERE close_id=?", (cid,))
            conn.commit()
        conn.close()
        for mod, path in saved_catalog.items():
            mod.CATALOG_DB = path  # type: ignore[attr-defined]
        os.environ.pop("WOLF_ESB_SQLITE", None)

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
