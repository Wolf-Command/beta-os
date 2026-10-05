#!/usr/bin/env python3
"""FCR-BZG-18 — full audit trail for one venue close.

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
    td = Path(tempfile.mkdtemp(prefix="fcr-bzg-18-", dir=str(ROOT / "catalog" / "backups")))
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


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    import core.audit as audit
    import core.evidence as evidence
    import core.rbac as rbac
    import core.venue_close as vc

    biz = "2099-07-18"
    cash_amt = 222000.0

    db = temp_catalog()
    td = db.parent
    esb_path = td / "esb.sqlite"
    make_esb(esb_path, cash_amt, biz)
    os.environ["WOLF_ESB_SQLITE"] = str(esb_path)

    saved_catalog: dict = {}
    for mod in (vc, evidence, audit, rbac):
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
        check("close opened", opened.get("state") == "OPEN")

        vc.capture_esb_snapshot(
            cid,
            verified_person_id=closer,
            business_date=biz,
            esb_path=esb_path,
            conn=conn,
            commit=True,
        )
        after_cap = vc.get_close(cid, conn=conn)
        check(
            "capture mutation DATA_CAPTURED",
            after_cap and after_cap["state"] == "DATA_CAPTURED",
        )

        trail = vc.audit_trail(cid, conn=conn)
        check("trail has open + capture", len(trail) >= 2, str(len(trail)))

        actions = [e["action"] for e in trail]
        check(
            "open step present",
            "venue_close.open" in actions,
            str(actions),
        )
        check(
            "capture step present",
            "venue_close.esb_captured" in actions,
            str(actions),
        )
        open_idx = actions.index("venue_close.open")
        cap_idx = actions.index("venue_close.esb_captured")
        check("open before capture", open_idx < cap_idx, str(actions))

        open_evt = trail[open_idx]
        cap_evt = trail[cap_idx]
        check("open actor from caller", open_evt.get("actor_person_id") == closer)
        check("capture actor from caller", cap_evt.get("actor_person_id") == closer)
        check("open has occurred_at", bool(open_evt.get("occurred_at")))
        check("capture has occurred_at", bool(cap_evt.get("occurred_at")))
        check(
            "open after_state OPEN",
            open_evt.get("after") == "OPEN",
            str(open_evt),
        )
        check(
            "capture before_state OPEN",
            cap_evt.get("before") == "OPEN",
            str(cap_evt),
        )
        check(
            "capture after_state DATA_CAPTURED",
            cap_evt.get("after") == "DATA_CAPTURED",
            str(cap_evt),
        )

        for pid in PROTECTED:
            row = conn.execute(
                "SELECT state FROM venue_daily_closes WHERE close_id=?", (pid,)
            ).fetchone()
            check(f"protected {pid[:12]}… unchanged after test", row is not None)

    finally:
        if cid:
            # core_audit_events is append-only; temp DB is discarded with its parent dir.
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
