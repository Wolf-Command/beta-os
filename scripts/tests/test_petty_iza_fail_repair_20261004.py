#!/usr/bin/env python3
"""PETTY-IZA-FAIL-REPAIR — schema-only temp sqlite. Never copies live catalog."""
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
PETTY_HTML = ROOT / "dashboards" / "bzg-uma-blu-petty.html"
REF_ANCHORS = ROOT / "state/reliability/PETTY-CHAIN-VERIFICATION-ANCHORS.json"
PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-87202768-55af-4c8e-abc3-382a5496b8c6",
)
BIZ = "2026-10-04"
TS = "2026-10-04T08:00:00+08:00"
PERM_ID = "PERM-PETTY-CASH-RECORD-OUT"
PERM_CODE = "petty_cash.record_out"
IZA_NOTAS = ("PETTY-UMA-6E512800FE", "PETTY-UMA-80867C2504")

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
    for role in ("ROLE-BZG-CAPTAIN", "ROLE-BZG-CASHIER"):
        conn.execute(
            """
            INSERT INTO org_roles (role_id, display_name, department_id, role_type, status, created_at, updated_at)
            VALUES (?, ?, 'DEPT-BZG-FB', 'OPERATING', 'ACTIVE', ?, ?)
            ON CONFLICT(role_id) DO NOTHING
            """,
            (role, role, TS, TS),
        )
        if role == "ROLE-BZG-CAPTAIN":
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


def seed_scope(conn: sqlite3.Connection, assignment_id: str) -> None:
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

    upsert_assignment_scope(conn, assignment_id, "SCOPE-BZG-UMA", TS, TS)
    conn.commit()


def seed_captain(conn: sqlite3.Connection, person_id: str = "PERS-TEST-CAPTAIN") -> str:
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


def seed_chain_movements(conn: sqlite3.Connection, ops) -> None:
    """Import real movement pattern from live sources (amounts + dates only)."""
    rows = [
        ("2026-10-03", "OUT", 490000.0, "Nasi", "Staff"),
        ("2026-10-03", "OUT", 50000.0, "Coconut", "Supplies"),
        ("2026-10-03", "OUT", 15000.0, "Laundry", "Other"),
        ("2026-10-03", "IN", 500000.0, "Petty cash", "Top-up"),
        ("2026-10-04", "OUT", 430000.0, "Nasi bungkus", "Staff"),
        ("2026-10-04", "OUT", 21000.0, "Laundry", "Supplies"),
    ]
    for biz, direc, amt, purpose, cat in rows:
        ops.insert_petty_movement(
            business_date=biz,
            direction=direc,
            amount=amt,
            purpose=purpose,
            category=cat,
            outlet="Uma Blu",
            logged_by="Owner" if biz < "2026-10-04" else "Floor Captain",
            accounting_code="6140" if direc == "OUT" else None,
            accounting_classification=ops.PETTY_ACCT_MAPPED if direc == "OUT" else None,
            conn=conn,
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


def main() -> int:
    global PASS, FAIL
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"

    ph = PETTY_HTML.read_text(encoding="utf-8")
    check("page has no outlet dropdown", 'id="outlet"' not in ph)
    check("page has no accounting mapping", 'id="accounting_code"' not in ph)
    check("page shows locked outlet", "locked" in ph)
    check("page ledger section", ">Ledger<" in ph or ">Ledger</" in ph)
    check("page no GL post", "accounting_code" not in ph)
    check("ref anchors file exists", REF_ANCHORS.is_file())

    td = tempfile.mkdtemp(prefix="petty-iza-repair-", dir=str(ROOT / "state"))
    try:
        db = Path(td) / "content_library.sqlite"
        esb_db = Path(td) / "esb.sqlite"
        make_esb(esb_db)
        os.environ["WOLF_ESB_SQLITE"] = str(esb_db)

        from core import bzg_daily_close as bzg
        from core import bzg_outlet_registry as outlets
        from core import rbac as rb
        from core import uma_ops_console as ops

        for mod in (ops, bzg, rb, outlets):
            if hasattr(mod, "CATALOG_DB"):
                mod.CATALOG_DB = db
        ops.PETTY_CHAIN_REF_PATH = REF_ANCHORS

        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        bootstrap_org(conn)
        ops.ensure_schema(conn)
        bzg.ensure_schema(conn)
        outlets.ensure_schema(conn)
        seed_permission(conn)
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
        captain = seed_captain(conn)
        seed_scope(conn, "ASG-TEST-CAPTAIN-1")
        seed_chain_movements(conn, ops)

        recon = ops.reconcile_petty_balance(as_of_date=BIZ, conn=conn)
        check("balance derived", recon.get("derived_balance") is not None, str(recon))
        oct3_src = [s for s in recon.get("sources", []) if s.get("kind") == "verification_oct3_out_total"]
        check("oct3 out source", len(oct3_src) == 1, str(oct3_src))
        if oct3_src:
            check("oct3 out total 555000", oct3_src[0].get("out_idr") == 555000.0, str(oct3_src[0]))
        derived = float(recon.get("derived_balance") or 0)
        check("derived balance 54000", derived == 54000.0, str(derived))
        gap = recon.get("gap_vs_owner_stated")
        check("gap vs owner 1000", gap == 1000.0, str(gap))

        outlet = ops.resolve_petty_outlet_for_person(captain, conn=conn)
        check("outlet derived Uma Blu", outlet.get("display_name") == "Uma Blu", str(outlet))
        check("outlet locked id", outlet.get("outlet_id") == "BZG-UMA", str(outlet))

        try:
            ops.record_petty_ops(
                person_id=captain,
                business_date=BIZ,
                direction="OUT",
                amount=1000,
                purpose="wrong outlet test",
                category="Transport",
                outlet="Pool Bar",
                conn=conn,
                commit=False,
            )
            check("wrong outlet rejected", False, "should have raised")
        except ops.UmaOpsError as exc:
            check("wrong outlet rejected", exc.code == "outlet_forbidden", str(exc))

        try:
            ops.record_petty_ops(
                person_id=captain,
                business_date=BIZ,
                direction="OUT",
                amount=1000,
                purpose="gl test",
                category="Transport",
                accounting_code="5210",
                conn=conn,
                commit=False,
            )
            check("captain cannot set GL", False, "should have raised")
        except ops.UmaOpsError as exc:
            check("captain cannot set GL", exc.code == "accounting_forbidden", str(exc))

        try:
            ops.record_petty_ops(
                person_id=captain,
                business_date=BIZ,
                direction="IN",
                amount=1000,
                purpose="top up",
                category="Top-up",
                conn=conn,
                commit=False,
            )
            check("IN blocked", False, "should have raised")
        except ops.UmaOpsError as exc:
            check("IN blocked", exc.code == "forbidden", str(exc))

        mv = ops.record_petty_ops(
            person_id=captain,
            business_date=BIZ,
            direction="OUT",
            amount=5000,
            purpose="test transport",
            category="Transport",
            conn=conn,
            commit=True,
        )
        check("OUT without captain GL", mv.get("direction") == "OUT", str(mv))
        check(
            "missing receipt is exception",
            mv.get("receipt_missing") is True,
            str(mv),
        )

        listed = ops.list_petty(person_id=captain, conn=conn)
        check("GET no accounting_mappings", "accounting_mappings" not in listed)
        check("GET outlet_locked", listed.get("outlet_locked", {}).get("locked") is True)
        check("GET captain_view", listed.get("captain_view") is True)
        cats = listed.get("categories") or []
        check("categories operational not GL", "Administrative" not in cats and "5210" not in cats)

        for nid in IZA_NOTAS:
            row = conn.execute(
                "SELECT movement_id FROM bzg_ops_petty_movements WHERE movement_id=?",
                (nid,),
            ).fetchone()
            check(f"iza nota {nid} in live — skip temp", row is None)

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

        close_id = f"VDC-TEST-PETTY-IZA-{uuid.uuid4().hex[:8]}"
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

        petty_before = ops.sum_petty_out_for_date(BIZ, conn=conn)
        ops.record_petty_ops(
            person_id=captain,
            business_date=BIZ,
            direction="OUT",
            amount=10000,
            purpose="close prove once",
            category="Cleaning",
            conn=conn,
            commit=True,
        )
        petty_after = ops.sum_petty_out_for_date(BIZ, conn=conn)
        check("same-day OUT counted once", petty_after - petty_before == 10000.0, f"{petty_before}->{petty_after}")

        recon_close = bzg.cash_reconciliation_with_petty(close_id, conn=conn)
        check("daily close recon ok", recon_close.get("ok") is True, str(recon_close))
        check("no double count", recon_close.get("double_count_avoided") is True)

        for cid in PROTECTED_CLOSES:
            row = conn.execute(
                "SELECT close_id FROM venue_daily_closes WHERE close_id=?", (cid,)
            ).fetchone()
            check(f"protected close {cid[:12]} not in temp db", row is None)

        check(
            "captain has record_out",
            rb.can(captain, PERM_CODE, {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}, conn=conn),
        )

        conn.close()
    finally:
        shutil.rmtree(td, ignore_errors=True)

    print(f"\nTOTAL PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
