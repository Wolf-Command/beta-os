#!/usr/bin/env python3
"""FCR-BZG-17 — wrong-date protection on venue-close capture and submit.

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
    td = Path(tempfile.mkdtemp(prefix="fcr-bzg-17-", dir=str(ROOT / "catalog" / "backups")))
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


def close_row(conn: sqlite3.Connection, close_id: str) -> dict | None:
    row = conn.execute(
        """
        SELECT close_id, business_date, state, esb_fingerprint_sha256,
               declared_cash_amount, esb_totals_json
        FROM venue_daily_closes WHERE close_id=?
        """,
        (close_id,),
    ).fetchone()
    if not row:
        return None
    return dict(row)


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    import core.audit as audit
    import core.bzg_daily_close as bzg
    import core.evidence as evidence
    import core.rbac as rbac
    import core.venue_close as vc

    biz = "2099-06-01"
    wrong_biz = "2099-06-02"
    cash_amt = 333000.0

    db = temp_catalog()
    td = db.parent
    esb_path = td / "esb.sqlite"
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
        check("closer actor from roster/assignment", bool(closer))

        opened = vc.open_or_get(biz, verified_person_id=closer, conn=conn, commit=True)
        cid = str(opened["close_id"])
        before_open = close_row(conn, cid)
        check("close opened for target date", before_open and before_open["business_date"] == biz)
        check("close starts OPEN", before_open and before_open["state"] == "OPEN")

        # Wrong-date capture must reject and leave row unchanged.
        cap_rejected = False
        cap_code = ""
        try:
            vc.capture_esb_snapshot(
                cid,
                verified_person_id=closer,
                business_date=wrong_biz,
                esb_path=esb_path,
                conn=conn,
                commit=True,
            )
        except vc.VenueCloseError as exc:
            cap_rejected = True
            cap_code = str(exc.code or "")
        check("wrong-date capture rejected", cap_rejected)
        check("wrong-date capture code", cap_code == "wrong_business_date", cap_code)

        after_bad_cap = close_row(conn, cid)
        check(
            "close unchanged after wrong-date capture",
            after_bad_cap == before_open,
            f"before={before_open} after={after_bad_cap}",
        )

        # Same-date capture succeeds.
        cap_ok = vc.capture_esb_snapshot(
            cid,
            verified_person_id=closer,
            business_date=biz,
            esb_path=esb_path,
            conn=conn,
            commit=True,
        )
        after_good_cap = close_row(conn, cid)
        check("same-date capture not wrong-date error", cap_ok.get("ok") is True)
        check(
            "same-date capture writes fingerprint",
            bool(after_good_cap and after_good_cap.get("esb_fingerprint_sha256")),
        )
        check(
            "same-date capture state DATA_CAPTURED",
            after_good_cap and after_good_cap["state"] == "DATA_CAPTURED",
        )

        # Capture without pinned date still allowed when close date matches warehouse.
        cap2 = vc.capture_esb_snapshot(
            cid,
            verified_person_id=closer,
            esb_path=esb_path,
            conn=conn,
            commit=True,
        )
        check("capture without business_date idempotent", cap2.get("idempotent") is True)

        before_submit = close_row(conn, cid)

        # Wrong-date submit must reject and leave row unchanged.
        sub_rejected = False
        sub_code = ""
        try:
            bzg.staff_submit_close(
                cid,
                declared_cash_amount=cash_amt,
                verified_person_id=closer,
                business_date=wrong_biz,
                allow_test_write=True,
                conn=conn,
                commit=True,
            )
        except vc.VenueCloseError as exc:
            sub_rejected = True
            sub_code = str(exc.code or "")
        check("wrong-date submit rejected", sub_rejected)
        check("wrong-date submit code", sub_code == "wrong_business_date", sub_code)

        after_bad_sub = close_row(conn, cid)
        check(
            "close unchanged after wrong-date submit",
            after_bad_sub == before_submit,
            f"before={before_submit} after={after_bad_sub}",
        )

        # Same-date submit proceeds (not rejected as wrong date).
        sub_ok = bzg.staff_submit_close(
            cid,
            declared_cash_amount=cash_amt,
            verified_person_id=closer,
            business_date=biz,
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        check(
            "same-date submit not wrong-date error",
            sub_ok.get("staff_result") in ("CLOSE COMPLETE", "PLEASE RECOUNT CASH", "NEEDS MANAGER REVIEW"),
            str(sub_ok.get("staff_result")),
        )
        check("same-date submit ok flag", sub_ok.get("ok") is True)

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
                    invalidate_reason='FCR-BZG-17 test cleanup',
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
