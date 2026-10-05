#!/usr/bin/env python3
"""CAPTAIN-PETTY-OUT-1 — temp schema-only sqlite. Never copies live catalog."""
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
sys.path.insert(0, str(SCRIPTS))

OPS_PY = SCRIPTS / "core" / "uma_ops_console.py"
MIG = SCRIPTS / "migrations" / "migrate_petty_cash_record_out_1.py"
PROTECTED_CLOSE = "VDC-470e741f-d889-437a-9a40-1ec9c083fb95"
BIZ = "2026-10-04"
TS = "2026-10-04T08:00:00+08:00"
PERM_ID = "PERM-PETTY-CASH-RECORD-OUT"
PERM_CODE = "petty_cash.record_out"
# Real expense account from ENT-BZG entity books (not invented).
ACCT_TRANSPORT = "5210"
ACCT_GAS = "5220"

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


def seed_permission(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO org_permissions (
          permission_id, code, resource, action, description, status, created_at, updated_at
        ) VALUES (?, ?, 'petty_cash', 'record_out', 'test seed', 'ACTIVE', ?, ?)
        ON CONFLICT(permission_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (PERM_ID, PERM_CODE, TS, TS),
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
    for role in ("ROLE-BZG-CAPTAIN", "ROLE-BZG-HFB", "ROLE-BZG-FB-OPS-LEAD"):
        conn.execute(
            """
            INSERT INTO org_roles (role_id, display_name, department_id, role_type, status, created_at, updated_at)
            VALUES (?, ?, 'DEPT-BZG-FB', 'OPERATING', 'ACTIVE', ?, ?)
            ON CONFLICT(role_id) DO NOTHING
            """,
            (role, role, TS, TS),
        )
        conn.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW'
            """,
            (role, PERM_ID, TS, TS),
        )
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES ('POS-BZG-CAPTAIN-UMA-1', 'ROLE-BZG-CAPTAIN', 'ENT-BZG', 'BZG-UMA', 'DEPT-BZG-FB',
                  'Captain Uma', 'ACTIVE', 1.0, ?, ?)
        ON CONFLICT(position_id) DO NOTHING
        """,
        (TS, TS),
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

    upsert_assignment_scope(conn, "ASG-TEST-CAPTAIN-1", "SCOPE-BZG-UMA", TS, TS)
    upsert_assignment_scope(conn, "ASG-TEST-CASHIER-1", "SCOPE-BZG-UMA", TS, TS)
    conn.commit()


def seed_captain(conn: sqlite3.Connection) -> str:
    """Example assignee only — production paths use assignment + role, not hardcoded person."""
    person_id = "PERS-TEST-CAPTAIN"
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES (?, 'Test Captain', NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE'
        """,
        (person_id, TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES ('ASG-TEST-CAPTAIN-1', ?, 'POS-BZG-CAPTAIN-UMA-1', ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET status='ACTIVE', end_at=NULL
        """,
        (person_id, TS, TS, TS),
    )
    conn.commit()
    return person_id


def seed_cashier(conn: sqlite3.Connection, person_id: str = "PERS-TEST-CASHIER") -> str:
    conn.execute(
        """
        INSERT INTO org_roles (role_id, display_name, department_id, role_type, status, created_at, updated_at)
        VALUES ('ROLE-BZG-CASHIER', 'Cashier', 'DEPT-BZG-FB', 'OPERATING', 'SPECIFIED', ?, ?)
        ON CONFLICT(role_id) DO NOTHING
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES ('POS-TEST-CASHIER-1', 'ROLE-BZG-CASHIER', 'ENT-BZG', 'BZG-UMA', 'DEPT-BZG-FB',
                  'Test Cashier', 'ACTIVE', 1.0, ?, ?)
        ON CONFLICT(position_id) DO NOTHING
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES (?, 'Test Cashier', NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE'
        """,
        (person_id, TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES ('ASG-TEST-CASHIER-1', ?, 'POS-TEST-CASHIER-1', ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET
          person_id=excluded.person_id, status='ACTIVE', end_at=NULL
        """,
        (person_id, TS, TS, TS),
    )
    conn.commit()
    return person_id


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


def main() -> int:
    global PASS, FAIL
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"

    check("migration file exists", MIG.is_file())
    check("ops defines PERM_PETTY_RECORD_OUT", "petty_cash.record_out" in OPS_PY.read_text())
    check("no hardcoded PERS-IZA in ops", "PERS-IZA" not in OPS_PY.read_text())

    td = tempfile.mkdtemp(prefix="petty-out-", dir=str(ROOT / "state"))
    try:
        db = Path(td) / "content_library.sqlite"
        esb_db = Path(td) / "esb.sqlite"
        make_esb(esb_db)
        os.environ["WOLF_ESB_SQLITE"] = str(esb_db)

        from core import audit as au
        from core import bzg_daily_close as bzg
        from core import bzg_outlet_registry as outlets
        from core import esb_close_snapshot as esb
        from core import evidence as ev
        from core import identity as ident
        from core import organisation as org
        from core import rbac as rb
        from core import scope as sc
        from core import uma_ops_console as ops
        from core import venue_close as vc
        from core import work_items as wi

        for mod in (ops, bzg, vc, rb, au, esb, ev, wi, org, sc, ident, outlets):
            if hasattr(mod, "CATALOG_DB"):
                mod.CATALOG_DB = db

        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        bootstrap_org(conn)
        ops.ensure_schema(conn)
        bzg.ensure_schema(conn)
        outlets.ensure_schema(conn)
        seed_permission(conn)
        captain = seed_captain(conn)
        cashier = seed_cashier(conn)
        seed_scope(conn)

        mappings = ops.list_petty_accounting_mappings(conn=conn)
        check(
            "accounting mappings from entity books",
            any(m.get("code") == ACCT_TRANSPORT for m in mappings),
            str(mappings[:3]),
        )

        check(
            "captain has petty_cash.record_out",
            rb.can(captain, PERM_CODE, {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}, conn=conn),
        )
        check(
            "cashier denied petty_cash.record_out",
            not rb.can(cashier, PERM_CODE, {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}, conn=conn),
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

        try:
            ops.record_petty_ops(
                person_id=cashier,
                business_date=BIZ,
                direction="OUT",
                amount=50000,
                purpose="test supplies",
                category="Supplies",
                photo_evidence_id="EVD-TEST-PHOTO-1",
                conn=conn,
                commit=False,
            )
            check("cashier record denied", False, "should have raised")
        except ops.UmaOpsError as exc:
            check("cashier record denied", exc.code == "forbidden", str(exc))

        try:
            ops.record_petty_ops(
                person_id=captain,
                business_date=BIZ,
                direction="IN",
                amount=50000,
                purpose="top up",
                category="Top-up",
                photo_evidence_id="EVD-TEST-PHOTO-2",
                conn=conn,
                commit=False,
            )
            check("IN direction blocked", False, "should have raised")
        except ops.UmaOpsError as exc:
            check("IN direction blocked", exc.code == "forbidden", str(exc))

        mv = ops.record_petty_ops(
            person_id=captain,
            business_date=BIZ,
            direction="OUT",
            amount=75000,
            purpose="transport to market",
            category="Transport",
            payee="Driver",
            photo_evidence_id="EVD-TEST-PHOTO-3",
            receipt_path=None,
            conn=conn,
            commit=True,
        )
        check("OUT recorded", mv.get("direction") == "OUT" and mv.get("amount") == 75000.0, str(mv))
        check("amount not zero", float(mv.get("amount") or 0) == 75000.0, str(mv.get("amount")))
        check(
            "missing receipt → receipt_missing flag",
            mv.get("receipt_missing") is True,
            str(mv),
        )
        row1 = conn.execute(
            "SELECT receipt_status, proof_status FROM bzg_ops_petty_movements WHERE amount=75000"
        ).fetchone()
        check(
            "missing receipt → EVIDENCE_EXCEPTION stored",
            row1 and row1[0] == ops.PETTY_RECEIPT_EXCEPTION,
            str(row1),
        )
        check(
            "missing receipt → proof INCOMPLETE stored",
            row1 and row1[1] == ops.PETTY_PROOF_INCOMPLETE,
            str(row1),
        )

        mv2 = ops.record_petty_ops(
            person_id=captain,
            business_date=BIZ,
            direction="OUT",
            amount=25000,
            purpose="gas refill",
            category="Kitchen Supplies",
            photo_evidence_id="EVD-TEST-PHOTO-4",
            receipt_path="/tmp/receipt-test.jpg",
            conn=conn,
            commit=True,
        )
        check(
            "receipt provided → receipt_attached",
            mv2.get("receipt_attached") is True and mv2.get("receipt_missing") is False,
            str(mv2),
        )
        row2 = conn.execute(
            "SELECT receipt_status, proof_status FROM bzg_ops_petty_movements WHERE amount=25000"
        ).fetchone()
        check(
            "receipt provided → PROVIDED stored",
            row2 and row2[0] == ops.PETTY_RECEIPT_PROVIDED,
            str(row2),
        )
        check(
            "receipt provided → proof RECORDED stored",
            row2 and row2[1] == ops.PETTY_PROOF_RECORDED,
            str(row2),
        )

        total = ops.sum_petty_out_for_date(BIZ, conn=conn)
        check("petty OUT sum", total == 100000.0, str(total))

        protected = conn.execute(
            "SELECT close_id FROM venue_daily_closes WHERE close_id=?",
            (PROTECTED_CLOSE,),
        ).fetchone()
        check("protected close not in temp db", protected is None)

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
        conn.commit()

        close_id = f"VDC-TEST-PETTY-OUT-{uuid.uuid4().hex[:8]}"
        conn.execute(
            """
            INSERT INTO venue_daily_closes (
              close_id, entity_id, venue_brand_id, business_date, state,
              esb_totals_json, declared_cash_amount, created_at, updated_at
            ) VALUES (?, 'ENT-BZG', 'BZG-UMA', ?, 'DATA_CAPTURED', ?, ?, ?, ?)
            """,
            (
                close_id,
                BIZ,
                json.dumps({"cash_from_payments": 500000.0}),
                900000.0,
                TS,
                TS,
            ),
        )
        conn.commit()
        check("test close seeded", close_id is not None)

        recon = bzg.cash_reconciliation_with_petty(close_id, conn=conn)
        check("recon ok", recon.get("ok") is True, str(recon))
        check("opening float from config", recon.get("opening_float") == 500000.0, str(recon))
        check("cash sales present", recon.get("cash_sales") == 500000.0, str(recon.get("cash_sales")))
        check("petty out total", recon.get("petty_out_total") == 100000.0, str(recon))
        check(
            "expected closing",
            recon.get("expected_closing_cash") == 900000.0,
            str(recon.get("expected_closing_cash")),
        )
        check("counted cash", recon.get("counted_cash") == 900000.0, str(recon.get("counted_cash")))
        check("difference zero", recon.get("difference") == 0.0, str(recon.get("difference")))
        check("no double count", recon.get("double_count_avoided") is True)
        check("no staff retype", recon.get("staff_retype_required") is False)

        board = bzg.recon_board(close_id, conn=conn)
        check(
            "recon_board includes cash_reconciliation",
            "cash_reconciliation" in board,
            str(board.keys()),
        )
        cr = board.get("cash_reconciliation") or {}
        check("board petty out", cr.get("petty_out_total") == 100000.0, str(cr))

        events = au.list_events(entity_id="ENT-BZG", source="uma_ops_console", limit=20, conn=conn)
        check(
            "audit trail for petty OUT",
            any(e.get("action") == "bzg.petty.movement" for e in events),
            str([e.get("action") for e in events[:5]]),
        )

        conn.close()
    finally:
        shutil.rmtree(td, ignore_errors=True)

    print(f"\nTOTAL PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
