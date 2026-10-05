#!/usr/bin/env python3
"""PETTY-OWNER-CASH-IN-1 — isolated fixture sqlite. Never copies live catalog."""
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
MIGRATIONS = SCRIPTS / "migrations"
LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
PROVENANCE = ROOT / "state/reliability/PETTY-BALANCE-PROVENANCE-2026-10-05.md"
BIZ = "2026-10-05"
TS = "2026-10-05T08:00:00+08:00"
PERM_OUT_ID = "PERM-PETTY-CASH-RECORD-OUT"
PERM_OUT_CODE = "petty_cash.record_out"
PERM_IN_ID = "PERM-PETTY-CASH-RECORD-IN"
PERM_IN_CODE = "petty_cash.record_in"
PERM_RECON_ID = "PERM-PETTY-CASH-RECONCILE"
PERM_RECON_CODE = "petty_cash.reconcile"
IZA_OUT_IDS = ("PETTY-UMA-6E512800FE", "PETTY-UMA-80867C2504")
PRE_ANCHOR_OUT = "PETTY-UMA-2321496C6D"
PROVED_BALANCE = 52700.0

sys.path.insert(0, str(SCRIPTS))

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


def bootstrap_org(conn: sqlite3.Connection) -> None:
    for sql_name in (
        "005_org_registry.sql",
        "006_person_auth_identity.sql",
        "007_role_position_assignment.sql",
        "008_assignment_scope.sql",
        "009_rbac_permissions.sql",
    ):
        conn.executescript((MIGRATIONS / sql_name).read_text(encoding="utf-8"))
    conn.executescript((MIGRATIONS / "011_audit_evidence_spine.sql").read_text(encoding="utf-8"))
    conn.executescript((MIGRATIONS / "021_uma_blu_daily_close.sql").read_text(encoding="utf-8"))
    sql_031 = MIGRATIONS / "031_bzg_daily_close_till_edc.sql"
    if sql_031.is_file():
        conn.executescript(sql_031.read_text(encoding="utf-8"))


def seed_permissions(conn: sqlite3.Connection) -> None:
    for perm_id, code, action in (
        (PERM_OUT_ID, PERM_OUT_CODE, "record_out"),
        (PERM_IN_ID, PERM_IN_CODE, "record_in"),
        (PERM_RECON_ID, PERM_RECON_CODE, "reconcile"),
    ):
        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description, status, created_at, updated_at
            ) VALUES (?, ?, 'petty_cash', ?, 'test seed', 'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
            """,
            (perm_id, code, action, TS, TS),
        )
    conn.execute(
        """
        INSERT INTO org_entities (
          entity_id, legal_name, display_name, entity_type, status, saleable, created_at, updated_at
        ) VALUES ('ENT-BZG', 'Blu Zone Group', 'Blu Zone Group', 'OPERATING', 'ACTIVE', 0, ?, ?)
        ON CONFLICT(entity_id) DO NOTHING
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_brands (
          brand_id, entity_id, display_name, brand_type, status, created_at, updated_at
        ) VALUES ('BZG-UMA', 'ENT-BZG', 'Uma Blu', 'VENUE', 'ACTIVE', ?, ?)
        ON CONFLICT(brand_id) DO NOTHING
        """,
        (TS, TS),
    )
    roles = {
        "ROLE-OWNER": (PERM_OUT_ID, PERM_IN_ID, PERM_RECON_ID),
        "ROLE-BZG-CAPTAIN": (PERM_OUT_ID,),
        "ROLE-BZG-FINANCIAL-CONTROLLER": (PERM_OUT_ID, PERM_IN_ID, PERM_RECON_ID),
    }
    for role_id, perms in roles.items():
        conn.execute(
            """
            INSERT INTO org_roles (role_id, display_name, department_id, role_type, status, created_at, updated_at)
            VALUES (?, ?, 'DEPT-BZG-FB', 'OPERATING', 'ACTIVE', ?, ?)
            ON CONFLICT(role_id) DO NOTHING
            """,
            (role_id, role_id, TS, TS),
        )
        for perm_id in perms:
            conn.execute(
                """
                INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
                VALUES (?, ?, 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW'
                """,
                (role_id, perm_id, TS, TS),
            )
    conn.commit()


def seed_scope(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO org_scopes (scope_id, scope_type, display_name, status, created_at, updated_at)
        VALUES ('SCOPE-BZG-UMA', 'brand', 'Uma Blu', 'ACTIVE', ?, ?)
        ON CONFLICT(scope_id) DO NOTHING
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES ('SCOPE-BZG-UMA', 'brand', 'BZG-UMA', ?)
        ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
        """,
        (TS,),
    )
    from core.scope import upsert_assignment_scope

    for asg in ("ASG-TEST-OWNER-1", "ASG-TEST-CAPTAIN-1", "ASG-TEST-FC-1"):
        upsert_assignment_scope(conn, asg, "SCOPE-BZG-UMA", TS, TS)
    conn.commit()


def seed_person(
    conn: sqlite3.Connection,
    person_id: str,
    name: str,
    assignment_id: str,
    position_id: str,
    role_id: str,
) -> str:
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES (?, ?, 'ENT-BZG', 'BZG-UMA', 'DEPT-BZG-FB', ?, 'ACTIVE', 1.0, ?, ?)
        ON CONFLICT(position_id) DO NOTHING
        """,
        (position_id, role_id, name, TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES (?, ?, NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE'
        """,
        (person_id, name, TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET status='ACTIVE', end_at=NULL
        """,
        (assignment_id, person_id, position_id, TS, TS, TS),
    )
    conn.commit()
    return person_id


def seed_proved_chain(conn: sqlite3.Connection) -> None:
    """Minimal chain reproducing Rp52,700 derived balance — fixture only."""
    conn.execute(
        """
        INSERT INTO bzg_ops_petty_days (
          venue, business_date, state, opening_float, opening_float_source,
          opening_float_set_by, opening_float_set_at, opening_float_kind,
          counted_amount, expected_amount, note, example, created_at, updated_at
        ) VALUES ('BZG-UMA', '2026-10-02', 'OPEN', 56000, 'human_supplied',
                  'Matt Goss', '2026-10-01T23:52:23Z', 'human_supplied_opening_balance',
                  NULL, NULL, 'anchor', 0, ?, ?)
        """,
        (TS, TS),
    )
    moves = [
        ("PETTY-UMA-2321496C6D", "2026-10-01", "OUT", 50000, None),
        ("PETTY-UMA-6E512800FE", "2026-10-04", "OUT", 430000, "Iza Zainatulloh Hulhidayati"),
        ("PETTY-UMA-80867C2504", "2026-10-04", "OUT", 21000, "Iza Zainatulloh Hulhidayati"),
    ]
    # Simplified intermediate chain to land at 52700 from 56000 anchor.
    extras = [
        ("PETTY-UMA-36743CB1E2", "2026-10-02", "IN", 500000, "Owner"),
        ("PETTY-UMA-898F771D08", "2026-10-02", "OUT", 26000, "Owner"),
        ("PETTY-UMA-535A0CBDE0", "2026-10-02", "OUT", 45300, "Owner"),
        ("PETTY-UMA-3E3916F24A", "2026-10-02", "OUT", 42000, "Owner"),
        ("PETTY-UMA-E53F9B191A", "2026-10-02", "OUT", 20000, "Owner"),
        ("PETTY-UMA-3B76ACAAB3", "2026-10-02", "OUT", 14000, "Owner"),
        ("PETTY-UMA-588D5C787F", "2026-10-02", "OUT", 350000, "Owner"),
        ("PETTY-UMA-266BD262E4", "2026-10-02", "IN", 500000, "Owner"),
        ("PETTY-UMA-0153380282", "2026-10-02", "OUT", 500000, "Owner"),
        ("PETTY-UMA-9EE4DF7AFB", "2026-10-02", "IN", 500000, "Owner"),
        ("PETTY-UMA-A172457171", "2026-10-03", "OUT", 490000, "Owner"),
        ("PETTY-UMA-74588A9330", "2026-10-03", "OUT", 50000, "Owner"),
        ("PETTY-UMA-7883C01A50", "2026-10-03", "OUT", 15000, "Owner"),
        ("PETTY-UMA-060F581083", "2026-10-03", "IN", 500000, "Owner"),
    ]
    for mid, biz, direc, amt, actor in moves + extras:
        conn.execute(
            """
            INSERT INTO bzg_ops_petty_movements (
              movement_id, venue, business_date, direction, amount, currency,
              purpose, example, created_at, logged_by, category
            ) VALUES (?, 'BZG-UMA', ?, ?, ?, 'IDR', 'fixture', 0, ?, ?, 'Transport')
            """,
            (mid, biz, direc, amt, TS, actor),
        )
    conn.commit()


def make_esb(path: Path, cash: float = 500000.0) -> None:
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
            "salesPayments": [{"paymentMethodTypeName": "CASH", "paymentAmount": cash}],
        }
        conn.execute(
            "INSERT INTO sales (nk, biz_date, raw, pulled_at) VALUES (?,?,?,?)",
            ("BLZ|S1", BIZ, json.dumps(raw), f"{BIZ}T20:00:00+08:00"),
        )
        conn.commit()
    finally:
        conn.close()


def live_balance() -> float | None:
    if not LIVE_DB.is_file():
        return None
    conn = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        from core import uma_ops_console as ops

        ops.CATALOG_DB = LIVE_DB
        recon = ops.reconcile_petty_balance(as_of_date="2026-10-05", conn=conn)
        return recon.get("derived_balance")
    finally:
        conn.close()


def main() -> int:
    global PASS, FAIL
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"

    balance_before = live_balance()
    check("provenance file exists", PROVENANCE.is_file())
    check("live balance before tests is 52700", balance_before == PROVED_BALANCE, str(balance_before))

    td = tempfile.mkdtemp(prefix="petty-in-", dir=str(ROOT / "state"))
    try:
        db = Path(td) / "content_library.sqlite"
        esb_db = Path(td) / "esb.sqlite"
        make_esb(esb_db)
        os.environ["WOLF_ESB_SQLITE"] = str(esb_db)

        from core import audit as au
        from core import bzg_daily_close as bzg
        from core import bzg_outlet_registry as outlets
        from core import rbac as rb
        from core import uma_ops_console as ops

        for mod in (ops, bzg, outlets, rb, au):
            if hasattr(mod, "CATALOG_DB"):
                mod.CATALOG_DB = db

        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        bootstrap_org(conn)
        ops.ensure_schema(conn)
        bzg.ensure_schema(conn)
        outlets.ensure_schema(conn)
        seed_permissions(conn)
        seed_scope(conn)
        owner = seed_person(
            conn, "PERS-TEST-OWNER", "Test Owner",
            "ASG-TEST-OWNER-1", "POS-TEST-OWNER-1", "ROLE-OWNER",
        )
        captain = seed_person(
            conn, "PERS-TEST-CAPTAIN", "Test Captain",
            "ASG-TEST-CAPTAIN-1", "POS-TEST-CAPTAIN-1", "ROLE-BZG-CAPTAIN",
        )
        conn.execute(
            """
            INSERT INTO org_outlet_registry (
              outlet_id, legal_entity_id, brand_id, display_name, outlet_kind, status, created_at, updated_at
            ) VALUES ('BZG-UMA', 'ENT-BZG', 'BZG-UMA', 'Uma Blu', 'BRAND', 'OPEN', ?, ?)
            ON CONFLICT(outlet_id) DO NOTHING
            """,
            (TS, TS),
        )
        conn.commit()
        seed_proved_chain(conn)

        recon_before = ops.reconcile_petty_balance(as_of_date="2026-10-05", conn=conn)
        check("fixture derived balance 52700", recon_before.get("derived_balance") == PROVED_BALANCE, str(recon_before))

        for mid in IZA_OUT_IDS:
            row = conn.execute(
                "SELECT amount, direction FROM bzg_ops_petty_movements WHERE movement_id=?", (mid,)
            ).fetchone()
            check(f"protected {mid} present", row is not None, str(mid))
        pre = conn.execute(
            "SELECT amount FROM bzg_ops_petty_movements WHERE movement_id=?", (PRE_ANCHOR_OUT,)
        ).fetchone()
        check("pre-anchor OUT 50000 present", pre and float(pre[0]) == 50000.0, str(pre))

        check("owner can record_in", rb.can(owner, PERM_IN_CODE, {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}, conn=conn))
        check("owner can record_out", rb.can(owner, PERM_OUT_CODE, {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}, conn=conn))
        check("captain cannot record_in", not rb.can(captain, PERM_IN_CODE, {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}, conn=conn))
        check("captain can record_out", rb.can(captain, PERM_OUT_CODE, {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}, conn=conn))

        bal0 = recon_before.get("derived_balance")
        mv_in = ops.record_petty_ops(
            person_id=owner,
            business_date=BIZ,
            direction="IN",
            amount=100000,
            purpose="Owner top-up test",
            photo_evidence_id="EVD-TEST-IN-1",
            receipt_path="/tmp/topup.jpg",
            idempotency_key="idem-in-1",
            conn=conn,
            commit=True,
        )
        check("1 owner CASH IN", mv_in.get("direction") == "IN" and mv_in.get("amount") == 100000.0, str(mv_in))
        bal1 = ops.reconcile_petty_balance(as_of_date=BIZ, conn=conn).get("derived_balance")
        check("6 IN changes balance once", bal1 == bal0 + 100000.0, f"{bal0} -> {bal1}")

        dup = ops.record_petty_ops(
            person_id=owner,
            business_date=BIZ,
            direction="IN",
            amount=100000,
            purpose="Owner top-up test",
            idempotency_key="idem-in-1",
            conn=conn,
            commit=True,
        )
        bal_dup = ops.reconcile_petty_balance(as_of_date=BIZ, conn=conn).get("derived_balance")
        check("8 duplicate IN idempotent", dup.get("idempotent") is True, str(dup))
        check("8 balance unchanged after dup", bal_dup == bal1, f"{bal_dup} vs {bal1}")

        mv_out = ops.record_petty_ops(
            person_id=owner,
            business_date=BIZ,
            direction="OUT",
            amount=25000,
            purpose="supplies",
            category="Supplies",
            photo_evidence_id="EVD-TEST-OUT-1",
            conn=conn,
            commit=True,
        )
        check("2 owner CASH OUT", mv_out.get("direction") == "OUT", str(mv_out))
        bal2 = ops.reconcile_petty_balance(as_of_date=BIZ, conn=conn).get("derived_balance")
        check("7 OUT changes balance once", bal2 == bal1 - 25000.0, f"{bal1} -> {bal2}")

        mv_cap = ops.record_petty_ops(
            person_id=captain,
            business_date=BIZ,
            direction="OUT",
            amount=15000,
            purpose="market run",
            category="Transport",
            photo_evidence_id="EVD-TEST-CAP-1",
            conn=conn,
            commit=True,
        )
        check("3 captain CASH OUT", mv_cap.get("direction") == "OUT", str(mv_cap))

        try:
            ops.record_petty_ops(
                person_id=captain,
                business_date=BIZ,
                direction="IN",
                amount=50000,
                purpose="captain top-up",
                conn=conn,
                commit=False,
            )
            check("4 captain IN blocked", False, "should have raised")
        except ops.UmaOpsError as exc:
            check("4 captain IN blocked", exc.code == "forbidden", str(exc))

        try:
            ops.record_petty_ops(
                person_id=owner,
                business_date=BIZ,
                direction="IN",
                amount=1000,
                purpose="wrong outlet",
                outlet="Wrong Outlet",
                conn=conn,
                commit=False,
            )
            check("5 outlet override blocked", False, "should have raised")
        except ops.UmaOpsError as exc:
            check("5 outlet override blocked", exc.code == "outlet_forbidden", str(exc))

        row_ev = conn.execute(
            "SELECT photo_evidence_id, receipt_path FROM bzg_ops_petty_movements WHERE movement_id=?",
            (mv_in.get("movement_id"),),
        ).fetchone()
        check("9 evidence attached", row_ev and row_ev[0] == "EVD-TEST-IN-1", str(row_ev))

        events = au.list_events(entity_id="ENT-BZG", source="uma_ops_console", limit=30, conn=conn)
        petty_events = [e for e in events if e.get("action") == "bzg.petty.movement"]
        check("10 audit petty movements", len(petty_events) >= 3, str(len(petty_events)))
        last = petty_events[0] if petty_events else {}
        meta = last.get("metadata") or {}
        check("10 audit has amount", meta.get("amount") is not None, str(meta))
        check("10 audit has type/status", meta.get("status") in ("IN", "OUT"), str(meta))

        conn.execute(
            """
            INSERT INTO venue_close_outlet_config (
              outlet_id, entity_id, venue_brand_id, owner_title, human_close_enabled,
              till_float_idr, created_at, updated_at
            ) VALUES ('BZG-UMA', 'ENT-BZG', 'BZG-UMA', 'Uma Blu', 1, 500000, ?, ?)
            ON CONFLICT(outlet_id) DO UPDATE SET till_float_idr=excluded.till_float_idr
            """,
            (TS, TS),
        )
        close_id = f"VDC-TEST-PETTY-IN-{uuid.uuid4().hex[:8]}"
        conn.execute(
            """
            INSERT INTO venue_daily_closes (
              close_id, entity_id, venue_brand_id, business_date, state,
              esb_totals_json, declared_cash_amount, created_at, updated_at
            ) VALUES (?, 'ENT-BZG', 'BZG-UMA', ?, 'DATA_CAPTURED', ?, ?, ?, ?)
            """,
            (close_id, BIZ, json.dumps({"cash_from_payments": 500000.0}), 1075000.0, TS, TS),
        )
        conn.commit()
        cr = bzg.cash_reconciliation_with_petty(close_id, conn=conn)
        petty_in = cr.get("petty_in_total")
        petty_out = cr.get("petty_out_total")
        check("11 close reads petty IN", petty_in == 100000.0, str(petty_in))
        check("11 close reads petty OUT", petty_out == 40000.0, str(petty_out))
        check(
            "11 expected includes IN once",
            cr.get("expected_closing_cash") == 500000.0 + 500000.0 - 40000.0 + 100000.0,
            str(cr.get("expected_closing_cash")),
        )

        rec = ops.reconcile_petty_cash_ops(
            person_id=owner,
            notes_total=152000.0,
            coins_total=0.0,
            reason="end of day count",
            conn=conn,
            commit=True,
        )
        check("reconcile records count", rec.get("ok") is True, str(rec))
        check("reconcile shows unproved diff", rec.get("unproved") is True, str(rec))
        check("reconcile no adjustment", rec.get("adjustment_posted") is False, str(rec))

        conn.close()
    finally:
        shutil.rmtree(td, ignore_errors=True)

    balance_after = live_balance()
    check("12 live balance unchanged after tests", balance_after == PROVED_BALANCE, str(balance_after))
    check("12 live balance matches before", balance_after == balance_before, f"{balance_before} -> {balance_after}")

    print(f"\nTOTAL PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
