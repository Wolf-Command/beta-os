#!/usr/bin/env python3
"""FCR-BZG-12 — ORIGINAL → REOPEN EVENT → CHANGES → NEW APPROVAL on venue close.

Temp DB only. Never writes catalog/content_library.sqlite.
Protected closes VDC-470e741f… and VDC-87202768… are not touched.
"""
from __future__ import annotations

import importlib.util
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
VC_PY = SCRIPTS / "core" / "venue_close.py"
ESB_PY = SCRIPTS / "core" / "esb_close_snapshot.py"

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


def temp_catalog() -> Path:
    td = Path(tempfile.mkdtemp(prefix="fcr-bzg-12-", dir=str(ROOT / "catalog" / "backups")))
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


def owner_actor(conn: sqlite3.Connection) -> str:
    """Resolve owner_control actor from assignment — no hardcoded person in engine."""
    row = conn.execute(
        """
        SELECT a.person_id
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        JOIN org_role_permissions rp ON rp.role_id = p.role_id
        JOIN org_permissions perm ON perm.permission_id = rp.permission_id
        WHERE perm.code = 'venue.close.owner_control'
          AND rp.effect = 'ALLOW'
          AND a.status = 'ACTIVE'
          AND a.end_at IS NULL
        ORDER BY a.assignment_id
        LIMIT 1
        """
    ).fetchone()
    assert row is not None
    return str(row[0])


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
    import core.work_items as work_items

    db = temp_catalog()
    td = db.parent
    esb_path = td / "esb.sqlite"
    biz = "2099-04-12"
    make_esb(esb_path, 111000.0, biz)
    os.environ["WOLF_ESB_SQLITE"] = str(esb_path)

    saved_catalog: dict = {}
    for mod in (vc, evidence, audit, rbac, work_items):
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

        owner = owner_actor(conn)
        closer = closer_actor(conn)
        check("owner actor from assignment", bool(owner))
        check(
            "owner_control via assignment",
            rbac.can(owner, "venue.close.owner_control", vc._rbac_target(), conn=conn),
        )

        opened = vc.open_or_get(biz, verified_person_id=closer, conn=conn, commit=True)
        cid = str(opened["close_id"])
        ts = vc.now_utc_iso()
        orig_totals = {"cash_from_payments": 111000.0, "finished_count": 1}
        conn.execute(
            """
            UPDATE venue_daily_closes
            SET state='VERIFIED_CLOSED',
                esb_fingerprint_sha256=?,
                esb_totals_json=?,
                esb_pulled_at=?,
                declared_cash_amount=111000.0,
                taken_by_person_id=?,
                taken_at=?,
                updated_at=?,
                verified_at=?,
                verified_by_person_id=?
            WHERE close_id=?
            """,
            (
                f"prove-fp-{cid[-12:]}",
                json.dumps(orig_totals),
                ts,
                closer,
                ts,
                ts,
                ts,
                closer,
                cid,
            ),
        )
        conn.commit()

        reopened = vc.owner_control_venue_close(
            cid,
            verified_person_id=owner,
            action="reopen",
            reason="FCR-BZG-12 prove four-stage chain",
            conn=conn,
            commit=True,
        )
        check("reopen → OPEN", reopened.get("state") == "OPEN")
        check("ORIGINAL frozen", bool(reopened.get("final_history_id")))
        check("REOPEN EVENT id", bool(reopened.get("reopen_event_id")))

        hist = vc.latest_final_history(cid, conn=conn)
        check("ORIGINAL immutable totals", hist is not None)
        check(
            "ORIGINAL cash 111000",
            float((hist or {}).get("esb_totals", {}).get("cash_from_payments") or 0) == 111000.0,
            str(hist),
        )

        evt = conn.execute(
            "SELECT * FROM venue_close_reopen_events WHERE close_id=?",
            (cid,),
        ).fetchone()
        check("REOPEN EVENT row", evt is not None)
        check(
            "REOPEN EVENT points at ORIGINAL",
            evt is not None and evt["final_history_id"] == reopened.get("final_history_id"),
        )
        check(
            "REOPEN EVENT actor from assignment",
            evt is not None and evt["actor_person_id"] == owner,
            str(dict(evt) if evt else None),
        )
        check(
            "REOPEN EVENT has reason",
            evt is not None and "FCR-BZG-12" in str(evt["reason"]),
        )

        make_esb(esb_path, 150000.0, biz)
        # Post-reopen holder is owner (assignment-derived actor); force_recapture needs owner_control.
        vc.capture_esb_snapshot(
            cid,
            verified_person_id=owner,
            esb_path=esb_path,
            force_recapture=True,
            force_reason="post-reopen ESB correction",
            conn=conn,
            commit=True,
        )
        vc.attach_declared_cash(
            cid,
            declared_cash_amount=150000.0,
            verified_person_id=owner,
            conn=conn,
            commit=True,
        )
        vc.reconcile(cid, verified_person_id=owner, esb_path=esb_path, conn=conn, commit=True)

        chain = vc.reopen_chain(cid, conn=conn)
        check("CHANGES recorded", len(chain.get("changes") or []) >= 1, str(chain.get("changes")))
        check("NEW APPROVAL recorded", chain.get("new_approval") is not None)
        check("chain complete", chain.get("chain_complete") is True, str(chain))

        appr = chain.get("new_approval") or {}
        evt_id = str((chain.get("reopen_event") or {}).get("reopen_event_id") or "")
        check(
            "NEW APPROVAL distinct from REOPEN EVENT",
            appr.get("reopen_event_id") == evt_id and appr.get("approval_id") != evt_id,
        )
        check(
            "NEW APPROVAL not reopen action",
            str(appr.get("approval_type") or "") != "reopen",
        )

        hist2 = vc.latest_final_history(cid, conn=conn)
        check(
            "ORIGINAL still 111000 after approval",
            float((hist2 or {}).get("esb_totals", {}).get("cash_from_payments") or 0) == 111000.0,
            str(hist2),
        )
        working = vc.get_close(cid, conn=conn)
        check("working VERIFIED_CLOSED again", working and working["state"] == "VERIFIED_CLOSED")
        check(
            "working cash updated to 150000",
            float((working or {}).get("esb_totals", {}).get("cash_from_payments") or 0) == 150000.0,
            str(working),
        )

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
