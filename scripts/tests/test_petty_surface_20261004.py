#!/usr/bin/env python3
"""PETTY-SURFACE-2026-10-04 — staff petty OUT page + recorder wiring.

Temp sqlite via schema helper only. Never copies catalog/content_library.sqlite.
Protected close VDC-470e741f never written.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
MIGRATIONS = SCRIPTS / "migrations"
PETTY_HTML = ROOT / "dashboards" / "bzg-uma-blu-petty.html"
PROTECTED_CLOSE = "VDC-470e741f-d889-437a-9a40-1ec9c083fb95"
BIZ = "2026-10-04"
TS = "2026-10-04T08:00:00+08:00"
PERM_ID = "PERM-PETTY-CASH-RECORD-OUT"
PERM_CODE = "petty_cash.record_out"
# Real expense account from ENT-BZG entity books (not invented).
ACCT_CODE = "5210"

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
        INSERT INTO org_roles (role_id, display_name, department_id, role_type, status, created_at, updated_at)
        VALUES ('ROLE-BZG-CAPTAIN', 'Floor Captain', 'DEPT-BZG-FB', 'OPERATING', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO NOTHING
        """,
        (TS, TS),
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
    conn.execute(
        """
        INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES ('ROLE-BZG-CAPTAIN', ?, 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW'
        """,
        (PERM_ID, TS, TS),
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
    conn.commit()


def seed_captain(conn: sqlite3.Connection) -> str:
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
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"

    ph = PETTY_HTML.read_text(encoding="utf-8")
    check("page IN tab gated on canRecordIn", "canRecordIn" in ph and "actionTabs" in ph)
    check("page has no accounting mapping field", 'id="accounting_code"' not in ph)
    check("page does not post accounting_code", "accounting_code" not in ph)
    check("page has no outlet dropdown", 'id="outlet"' not in ph)
    check("page no free-text person field", 'id="logged_by"' not in ph)
    check("page receipt optional copy", "evidence exception" in ph.lower())
    check("page posts direction from activeDirection", "direction: fields.direction" in ph)

    td = tempfile.mkdtemp(prefix="petty-surface-", dir=str(ROOT / "state"))
    try:
        db = Path(td) / "content_library.sqlite"
        esb_db = Path(td) / "esb.sqlite"
        os.environ["WOLF_ESB_SQLITE"] = str(esb_db)
        make_esb(esb_db)

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

        for mod in (ops, bzg, vc, rb, au, esb, ev, org, sc, ident, outlets):
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
        seed_scope(conn)
        conn.commit()

        mappings = ops.list_petty_accounting_mappings(conn=conn)
        check("accounting mappings from entity books", any(m.get("code") == ACCT_CODE for m in mappings), str(mappings[:3]))

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

        listed = ops.list_petty(person_id=captain, conn=conn)
        check("GET captain view no accounting_mappings", "accounting_mappings" not in listed)
        check("GET business_label", listed.get("business_label") == "Uma Blu")
        check("GET outlet_locked", listed.get("outlet_locked", {}).get("locked") is True)

        try:
            ops.record_petty_ops(
                person_id=captain,
                business_date=BIZ,
                direction="IN",
                amount=50000,
                purpose="top up",
                category="Top-up",
                outlet="Uma Blu",
                accounting_code=ACCT_CODE,
                conn=conn,
                commit=False,
            )
            check("IN direction blocked", False, "should have raised")
        except ops.UmaOpsError as exc:
            check("IN direction blocked", exc.code == "forbidden", str(exc))

        try:
            ops.record_petty_ops(
                person_id=captain,
                business_date=BIZ,
                direction="OUT",
                amount=50000,
                purpose="test",
                category="Supplies",
                outlet="Pool Bar",
                conn=conn,
                commit=False,
            )
            check("wrong outlet refused", False, "should have raised")
        except ops.UmaOpsError as exc:
            check("wrong outlet refused", exc.code == "outlet_forbidden", str(exc))

        try:
            ops.record_petty_ops(
                person_id=captain,
                business_date=BIZ,
                direction="OUT",
                amount=50000,
                purpose="test",
                category="Supplies",
                accounting_code=ACCT_CODE,
                conn=conn,
                commit=False,
            )
            check("captain GL forbidden", False, "should have raised")
        except ops.UmaOpsError as exc:
            check("captain GL forbidden", exc.code == "accounting_forbidden", str(exc))

        mv = ops.record_petty_ops(
            person_id=captain,
            business_date=BIZ,
            direction="OUT",
            amount=75000,
            purpose="transport to market",
            category="Transport",
            payee="Driver",
            receipt_path=None,
            conn=conn,
            commit=True,
        )
        check("OUT with real code accepted", mv.get("amount") == 75000.0, str(mv))
        check("missing receipt flagged on movement", mv.get("receipt_missing") is True, str(mv))
        check("no fake receipt path", not mv.get("receipt_path"))
        row = conn.execute(
            "SELECT receipt_status, proof_status FROM bzg_ops_petty_movements WHERE example=0 LIMIT 1"
        ).fetchone()
        check("stored receipt_status EVIDENCE_EXCEPTION", row and row[0] == ops.PETTY_RECEIPT_EXCEPTION)
        check("stored proof_status INCOMPLETE", row and row[1] == ops.PETTY_PROOF_INCOMPLETE)

        public = ops.list_petty_movements(conn=conn, business_date=BIZ)[0]
        check("staff list includes movement id", public.get("movement_id") is not None)
        check("staff list receipt_missing", public.get("receipt_missing") is True)

        close_id = f"VDC-TEST-SURFACE-{uuid.uuid4().hex[:8]}"
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
                925000.0,
                TS,
                TS,
            ),
        )
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

        recon = bzg.cash_reconciliation_with_petty(close_id, conn=conn)
        check("recon ok", recon.get("ok") is True, str(recon))
        check("petty out once", recon.get("petty_out_total") == 75000.0, str(recon))
        check(
            "expected closing includes petty OUT once",
            recon.get("expected_closing_cash") == 925000.0,
            str(recon.get("expected_closing_cash")),
        )
        check("no double count", recon.get("double_count_avoided") is True)

        protected = conn.execute(
            "SELECT close_id FROM venue_daily_closes WHERE close_id=?",
            (PROTECTED_CLOSE,),
        ).fetchone()
        check("protected close not present in temp db", protected is None)

        conn.close()
    finally:
        import shutil

        shutil.rmtree(td, ignore_errors=True)

    print(f"\nTOTAL PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
