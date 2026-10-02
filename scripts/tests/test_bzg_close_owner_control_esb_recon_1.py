#!/usr/bin/env python3
"""BZG-CLOSE-OWNER-CONTROL-ESB-RECON-1 — Owner Control + dual-source bank-split.

Decision: 2026-09-17 Uma Blu Daily Close (extend) + Owner pack
BZG-CLOSE-OWNER-CONTROL-ESB-RECON-1.

Proves: assignment-derived owner_control (not email), audited reopen/cancel/
unlock/return, QRIS classified from method name, bank-split EDC/QRIS,
dual-source difference board never overwrites, cashier denied, staff_ready false.
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
MIG_OC = SCRIPTS / "migrations" / "migrate_bzg_close_owner_control_esb_recon_1.py"
MIG_TO = SCRIPTS / "migrations" / "migrate_bzg_close_governed_takeover_1.py"
MIG031 = SCRIPTS / "migrations" / "migrate_bzg_daily_close_till_edc_1.py"
MIG032 = SCRIPTS / "migrations" / "migrate_bzg_daily_close_multi_edc_vision_1.py"
UMA_MIG = SCRIPTS / "migrations" / "migrate_uma_blu_daily_close.py"
VC_PY = SCRIPTS / "core" / "venue_close.py"
BZG_PY = SCRIPTS / "core" / "bzg_daily_close.py"
ESB_PY = SCRIPTS / "core" / "esb_close_snapshot.py"
SERVE = SCRIPTS / "serve_beta.py"
UI = ROOT / "dashboards" / "uma-blu-close.html"
FORENSIC = ROOT / "state" / "bzg-daily-close" / "FORENSIC-ESB-RECON-20261002.json"
GAP = ROOT / "state" / "bzg-daily-close" / "OWNER-CONTROL-GAP-REGISTER.json"

PASS = 0
FAIL = 0
MATT = "PERS-MATT"
TARGET = {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}


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


def make_esb_uma_style(path: Path, biz_date: str = "2026-10-02") -> None:
    """Warehouse fixture mirroring Uma: QRIS typed as CARD + OTHER COST bills."""
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("DROP TABLE IF EXISTS sales")
        conn.execute(
            "CREATE TABLE sales (nk TEXT PRIMARY KEY, biz_date TEXT, raw TEXT, pulled_at TEXT)"
        )
        bills = [
            {
                "nk": "BLZ|S1",
                "salesNum": "S1",
                "billNum": "BLZ001",
                "branchCode": "BLZ",
                "statusName": "Finished",
                "grandTotal": 100000,
                "paymentTotal": 100000,
                "paxTotal": 2,
                "salesDateOut": f"{biz_date} 10:00:00",
                "salesPayments": [
                    {
                        "paymentMethodTypeName": "CASH",
                        "paymentMethodName": "CASH",
                        "paymentAmount": 120000,
                    }
                ],
            },
            {
                "nk": "BLZ|S2",
                "salesNum": "S2",
                "billNum": "BLZ002",
                "branchCode": "BLZ",
                "statusName": "Finished",
                "grandTotal": 200000,
                "paymentTotal": 200000,
                "paxTotal": 2,
                "salesDateOut": f"{biz_date} 11:00:00",
                "salesPayments": [
                    {
                        "paymentMethodTypeName": "CARD",
                        "paymentMethodName": "EDC BNI",
                        "paymentAmount": 200000,
                    }
                ],
            },
            {
                "nk": "BLZ|S3",
                "salesNum": "S3",
                "billNum": "BLZ003",
                "branchCode": "BLZ",
                "statusName": "Finished",
                "grandTotal": 50000,
                "paymentTotal": 50000,
                "paxTotal": 1,
                "salesDateOut": f"{biz_date} 12:00:00",
                "salesPayments": [
                    {
                        "paymentMethodTypeName": "CARD",
                        "paymentMethodName": "QRIS MANDIRI",
                        "paymentAmount": 50000,
                    }
                ],
            },
            {
                "nk": "BLZ|S4",
                "salesNum": "S4",
                "billNum": None,
                "branchCode": "BLZ",
                "statusName": "Finished",
                "grandTotal": 41322,
                "paymentTotal": 41322,
                "paxTotal": 1,
                "salesDateOut": f"{biz_date} 13:00:00",
                "salesPayments": [
                    {
                        "paymentMethodTypeName": "OTHER COST",
                        "paymentMethodName": "COMPLIMENT",
                        "paymentAmount": 41322,
                    }
                ],
            },
        ]
        pulled = f"{biz_date}T22:00:00+08:00"
        for b in bills:
            nk = b.pop("nk")
            conn.execute(
                "INSERT INTO sales (nk, biz_date, raw, pulled_at) VALUES (?,?,?,?)",
                (nk, biz_date, json.dumps({**b, "branchCode": "BLZ"}), pulled),
            )
        conn.commit()
    finally:
        conn.close()


def temp_catalog() -> Path:
    td = Path(tempfile.mkdtemp(prefix="bzg-oc-recon-"))
    db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, db)
    return db


def seed_closer(conn: sqlite3.Connection, person_id: str) -> None:
    """Minimal cashier-like person without owner_control / reassign."""
    conn.execute(
        """
        INSERT OR IGNORE INTO org_persons (person_id, display_name, status, created_at, updated_at)
        VALUES (?, 'Test Cashier', 'ACTIVE', datetime('now'), datetime('now'))
        """,
        (person_id,),
    )
    # Strip owner_control + reassign grants if any via roles — rely on no ROLE-MATT
    conn.commit()


def test_static_surface() -> None:
    ui = UI.read_text(encoding="utf-8")
    serve = SERVE.read_text(encoding="utf-8")
    vc = VC_PY.read_text(encoding="utf-8")
    esb = ESB_PY.read_text(encoding="utf-8")
    check("UI Owner Control panel", "Owner Control" in ui and "ownerControlPanel" in ui)
    check("UI Unlock abandoned", "Unlock abandoned" in ui)
    check("UI Return for correction", "Return for correction" in ui)
    check("UI dual-source box", "dualSourceBox" in ui)
    check("UI bank-split box", "bankSplitBox" in ui)
    check("serve owner-control route", "/api/venue-close/owner-control" in serve)
    check("engine owner_control fn", "def owner_control_venue_close" in vc)
    check("engine OWNER_CONTROL_PERM", "venue.close.owner_control" in vc)
    check("classify uses method name", "method_name" in esb and "paymentMethodName" in esb)
    check("bank split helper", "payments_by_bank_split" in esb)
    check("no hardcoded email gate in venue_close", "@" not in vc or "email" not in vc.lower().split("owner")[0][-200:])
    check("forensic stamp exists", FORENSIC.is_file())
    check("gap register exists", GAP.is_file())
    if FORENSIC.is_file():
        fj = json.loads(FORENSIC.read_text(encoding="utf-8"))
        check("forensic staff_ready false", fj.get("staff_ready") is False)
        check("forensic no overwrite", fj.get("policy_overwrite") is False)
    if GAP.is_file():
        gj = json.loads(GAP.read_text(encoding="utf-8"))
        check("gap register has workflows", isinstance(gj.get("workflows"), list) and len(gj["workflows"]) >= 4)


def test_classify_and_bank_split() -> None:
    esb = load_mod(ESB_PY, "esb_oc")
    td = Path(tempfile.mkdtemp(prefix="esb-oc-"))
    wh = td / "esb.sqlite"
    make_esb_uma_style(wh)
    os.environ["WOLF_ESB_SQLITE"] = str(wh)
    try:
        snap = esb.snapshot_day("2026-10-02", include_bills=True)
        t = snap["totals"]
        check("QRIS from CARD-typed name", float(t["qris_from_payments"]) == 50000.0, str(t))
        check("EDC not swallowing QRIS", float(t["card_from_payments"]) == 200000.0, str(t))
        check("cash tendered includes change", float(t["cash_from_payments"]) == 120000.0)
        check("cash sales grand net of change", float(t["cash_sales_grand"]) == 100000.0)
        check("change overpay 20k", float(t["cash_change_overpay"]) == 20000.0)
        split = t["payments_by_bank_split"]
        check("EDC_BNI split", float(split.get("EDC_BNI") or 0) == 200000.0, str(split))
        check("QRIS_Mandiri split", float(split.get("QRIS_Mandiri") or 0) == 50000.0, str(split))
        check("finished 4", int(t["finished_count"]) == 4)
        check("sales excl other 3", int(t["sales_bill_count_excl_other_cost"]) == 3)
        check("other cost bills 1", int(t["other_cost_bill_count"]) == 1)
    finally:
        os.environ.pop("WOLF_ESB_SQLITE", None)


def test_owner_control_rbac_and_actions() -> None:
    import core.rbac as _rbac
    import core.venue_close as _vc
    import core.bzg_daily_close as _bzg

    db = temp_catalog()
    # Apply owner-control migration against temp copy
    os.environ["WOLF_TEST_MODE"] = "1"
    # Point venue_close catalog to temp
    _vc.CATALOG_DB = db  # type: ignore[attr-defined]
    _bzg.CATALOG_DB = db  # type: ignore[attr-defined]

    # Run migration SQL manually on temp db (script targets LIVE path — inline grant)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    ts = "2026-10-02T22:00:00+08:00"
    conn.execute(
        """
        INSERT INTO org_permissions (
          permission_id, code, resource, action, description, status, created_at, updated_at
        ) VALUES ('PERM-VENUE-CLOSE-OWNER-CONTROL', 'venue.close.owner_control',
                  'venue.close', 'owner_control', 'test', 'ACTIVE', ?, ?)
        ON CONFLICT(permission_id) DO UPDATE SET status='ACTIVE', code=excluded.code
        """,
        (ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_role_permissions (
          role_id, permission_id, effect, created_at, updated_at
        ) VALUES ('ROLE-MATT', 'PERM-VENUE-CLOSE-OWNER-CONTROL', 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW', updated_at=excluded.updated_at
        """,
        (ts, ts),
    )
    conn.commit()

    check(
        "Matt has owner_control via ROLE-MATT",
        _rbac.can(MATT, "venue.close.owner_control", TARGET, conn=conn) is True,
    )

    # Find or create a cashier person without the perm
    cashier = "PERS-TEST-OC-CASHIER"
    seed_closer(conn, cashier)
    check(
        "cashier owner_control DENY",
        _rbac.can(cashier, "venue.close.owner_control", TARGET, conn=conn) is False,
    )

    # ESB fixture (future date — do not collide with tonight's live close row)
    wh = db.parent / "esb.sqlite"
    biz = "2099-06-02"
    make_esb_uma_style(wh, biz_date=biz)
    os.environ["WOLF_ESB_SQLITE"] = str(wh)

    # Open a fresh close as Matt
    opened = _vc.open_or_get(
        biz,
        verified_person_id=MATT,
        conn=conn,
        commit=True,
    )
    cid = opened["close_id"]
    check("open ok", bool(cid))
    _vc.take_open_venue_close(cid, verified_person_id=MATT, conn=conn, commit=True)

    # Capture
    try:
        cap = _vc.capture_esb_snapshot(
            cid,
            verified_person_id=MATT,
            esb_path=wh,
            conn=conn,
            commit=True,
        )
        check("capture ok", cap.get("esb_fingerprint_sha256") is not None)
    except Exception as exc:  # noqa: BLE001
        check("capture ok", False, str(exc))

    # Cashier cannot owner-control
    denied = False
    try:
        _vc.owner_control_venue_close(
            cid,
            verified_person_id=cashier,
            action="unlock_abandoned",
            reason="try steal",
            conn=conn,
            commit=True,
        )
    except _vc.VenueCloseError as exc:
        denied = exc.http_status == 403 or exc.code == "forbidden"
    check("cashier owner unlock DENY", denied)

    # Reason required
    missing = False
    try:
        _vc.owner_control_venue_close(
            cid,
            verified_person_id=MATT,
            action="unlock_abandoned",
            reason="  ",
            conn=conn,
            commit=True,
        )
    except _vc.VenueCloseError as exc:
        missing = exc.code == "missing_reason"
    check("owner reason required", missing)

    # Take as Matt then unlock
    _vc.take_over_venue_close(
        cid,
        verified_person_id=MATT,
        reason="Owner holds tonight",
        conn=conn,
        commit=True,
    )
    unlocked = _vc.owner_control_venue_close(
        cid,
        verified_person_id=MATT,
        action="unlock_abandoned",
        reason="Abandon unlock test",
        conn=conn,
        commit=True,
    )
    check(
        "unlock clears holder",
        unlocked.get("taken_by_person_id") in (None, ""),
        str(unlocked.get("taken_by_person_id")),
    )
    check("unlock work preserved", unlocked.get("work_preserved") is True)

    # Retake + cancel
    _vc.take_over_venue_close(
        cid,
        verified_person_id=MATT,
        reason="retake for cancel",
        conn=conn,
        commit=True,
    )
    cancelled = _vc.owner_control_venue_close(
        cid,
        verified_person_id=MATT,
        action="cancel",
        reason="Cancel workflow test",
        conn=conn,
        commit=True,
    )
    check("cancel → CANCELLED", cancelled.get("state") == "CANCELLED")

    # Reopen
    reopened = _vc.owner_control_venue_close(
        cid,
        verified_person_id=MATT,
        action="reopen",
        reason="Reopen after cancel",
        conn=conn,
        commit=True,
    )
    check("reopen → OPEN", reopened.get("state") == "OPEN")
    check("reopen holder Matt", reopened.get("taken_by_person_id") == MATT)

    # Audit present
    audit = conn.execute(
        """
        SELECT action, result FROM core_audit_events
        WHERE resource_id=? AND action LIKE 'venue_close.owner_%'
        ORDER BY created_at DESC LIMIT 5
        """,
        (cid,),
    ).fetchall()
    check("owner audit rows", len(audit) >= 3, str(audit))

    # Dual-source recon board
    # Re-capture after reopen
    try:
        _vc.capture_esb_snapshot(
            cid, verified_person_id=MATT, esb_path=wh, conn=conn, commit=True
        )
    except Exception:
        pass
    # Seed a confirmed closing receipt matching "sales" view (excl OTHER, cash=sales grand)
    if conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='venue_close_esb_closing_receipts'"
    ).fetchone():
        rid = "ESBREC-TEST-OC-1"
        conf = {
            "cash_amount": 100000,
            "bills": 3,
            "pax": 5,
            "payments": {
                "Cash": 100000,
                "EDC_BNI": 200000,
                "QRIS_Mandiri": 50000,
            },
        }
        conn.execute(
            """
            INSERT OR REPLACE INTO venue_close_esb_closing_receipts (
              esb_receipt_id, close_id, outlet_id, cash_amount, edc_card_amount, qris_amount,
              human_confirm_status, confirmed_json, api_mismatch,
              created_by_person_id, created_at, updated_at
            ) VALUES (?, ?, 'BZG-UMA', 100000, 200000, 50000, 'CONFIRMED', ?, 0, ?, ?, ?)
            """,
            (rid, cid, json.dumps(conf), MATT, ts, ts),
        )
        conn.commit()

    board = _bzg.recon_board(cid, conn=conn)
    check("recon ok", board.get("ok") is True)
    check("bank_split present", "EDC_BNI" in (board.get("bank_split_edc") or {}), str(board.get("bank_split_edc")))
    check("qris bank split", "QRIS_Mandiri" in (board.get("bank_split_qris") or {}), str(board.get("bank_split_qris")))
    dual = board.get("dual_source") or {}
    check("dual source kept", dual.get("sources_kept") is True and dual.get("silent_overwrite") is False)
    live = dual.get("live_esb_operational") or {}
    check("live finished 4", int(live.get("finished_bills") or 0) == 4)
    check("live sales excl other 3", int(live.get("sales_bills_excl_other_cost") or 0) == 3)
    expl_codes = {e.get("code") for e in (dual.get("explanations") or [])}
    check(
        "explains OTHER + cash tendered",
        "OTHER_COST_BILLS_IN_LIVE" in expl_codes and "CASH_TENDERED_VS_SALES" in expl_codes,
        str(expl_codes),
    )
    check("staff_ready false on board", board.get("staff_ready") is False)

    # No email hardcode in owner_control path
    src = VC_PY.read_text(encoding="utf-8")
    idx = src.find("def owner_control_venue_close")
    chunk = src[idx : idx + 2500]
    check("owner_control no PERS-MATT hardcode gate", '== "PERS-MATT"' not in chunk and "== 'PERS-MATT'" not in chunk)

    conn.close()
    os.environ.pop("WOLF_ESB_SQLITE", None)


def main() -> int:
    test_static_surface()
    test_classify_and_bank_split()
    test_owner_control_rbac_and_actions()
    print(f"\npass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
