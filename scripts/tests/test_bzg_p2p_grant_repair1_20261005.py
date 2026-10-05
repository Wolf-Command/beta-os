#!/usr/bin/env python3
"""BZG-P2P-GRANT-REPAIR-1 — GGV content deny + one-person chain deny regression."""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
MIGRATIONS = SCRIPTS / "migrations"
LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
PROTECTED_CLOSE = "VDC-470e741f-d889-437a-9a40-1ec9c083fb95"
TS = "2026-10-05T10:00:00+08:00"

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


def seed_fixture_matrix(conn: sqlite3.Connection) -> None:
    from core import bzg_p2p_grants as grants

    ts = TS
    conn.execute(
        """
        INSERT INTO org_entities (
          entity_id, legal_name, display_name, entity_type, status, saleable, created_at, updated_at
        ) VALUES ('ENT-BZG', 'Blu Zone Group', 'Blu Zone Group', 'OPERATING', 'ACTIVE', 0, ?, ?)
        ON CONFLICT(entity_id) DO NOTHING
        """,
        (ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_entities (
          entity_id, legal_name, display_name, entity_type, status, saleable, created_at, updated_at
        ) VALUES ('ENT-GGV', 'GGV', 'GGV', 'OPERATING', 'ACTIVE', 0, ?, ?)
        ON CONFLICT(entity_id) DO NOTHING
        """,
        (ts, ts),
    )
    for brand_id in ("BZG-UMA", "BZG-RAIN"):
        conn.execute(
            """
            INSERT INTO org_brands (
              brand_id, entity_id, display_name, brand_type, status, created_at, updated_at
            ) VALUES (?, 'ENT-BZG', ?, 'VENUE', 'ACTIVE', ?, ?)
            ON CONFLICT(brand_id) DO NOTHING
            """,
            (brand_id, brand_id, ts, ts),
        )
    for perm_id, code, action in (
        ("PERM-BZG-PO-CREATE", "bzg.po.create", "po_create"),
        ("PERM-BZG-BILL-CAPTURE", "bzg.bill.capture", "bill_capture"),
        ("PERM-BZG-AP-MARK-READY", "bzg.ap.mark_ready", "ap_mark_ready"),
        ("PERM-BZG-PAY-LIST-READY", "bzg.pay.list_ready", "pay_list_ready"),
        ("PERM-BZG-PAY-MARK-READY", "bzg.pay.mark_ready", "pay_mark_ready"),
        ("PERM-WORK-COMPLETE", "work.complete", "complete"),
    ):
        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description, status, created_at, updated_at
            ) VALUES (?, ?, 'bzg', ?, 'test seed', 'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET status='ACTIVE'
            """,
            (perm_id, code, action, ts, ts),
        )
    conn.execute(
        """
        INSERT INTO org_roles (role_id, display_name, department_id, role_type, status, created_at, updated_at)
        VALUES ('ROLE-GGV-CREATIVE-DIRECTOR', 'CD', 'DEPT-GGV-CONTENT', 'OPERATING', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO NOTHING
        """,
        (ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES ('ROLE-GGV-CREATIVE-DIRECTOR', 'PERM-WORK-COMPLETE', 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW'
        """,
        (ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_scopes (scope_id, scope_type, display_name, status, created_at, updated_at)
        VALUES ('SCOPE-WOLF-CONTENT-ALL-BRANDS', 'brand', 'All brands content', 'ACTIVE', ?, ?)
        ON CONFLICT(scope_id) DO NOTHING
        """,
        (ts, ts),
    )
    for brand_id in ("BZG-UMA", "BZG-RAIN", "GGV-CONTENT"):
        conn.execute(
            """
            INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
            VALUES ('SCOPE-WOLF-CONTENT-ALL-BRANDS', 'brand', ?, ?)
            ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
            """,
            (brand_id, ts),
        )
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES ('POS-GGV-CD-1', 'ROLE-GGV-CREATIVE-DIRECTOR', 'ENT-GGV', NULL, 'DEPT-GGV-CONTENT',
                  'Creative Director', 'ACTIVE', 1.0, ?, ?)
        ON CONFLICT(position_id) DO NOTHING
        """,
        (ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES ('PERS-HAIKAL', 'Haikal', NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO NOTHING
        """,
        (ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, status, start_at, end_at, created_at, updated_at
        ) VALUES ('ASG-HAIKAL-CD-1', 'PERS-HAIKAL', 'POS-GGV-CD-1', 'ACTIVE', ?, NULL, ?, ?)
        ON CONFLICT(assignment_id) DO NOTHING
        """,
        (ts, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_assignment_scopes (
          assignment_id, scope_id, status, start_at, end_at, created_at, updated_at
        ) VALUES ('ASG-HAIKAL-CD-1', 'SCOPE-WOLF-CONTENT-ALL-BRANDS', 'ACTIVE', ?, NULL, ?, ?)
        """,
        (ts, ts, ts),
    )
    grants.revoke_all_p2p_grants(conn, ts)
    grants.apply_p2p_grant_matrix(conn, ts)
    conn.commit()


def test_ggv_content_deny_on_fixture(conn: sqlite3.Connection) -> None:
    from core import bzg_outlet_registry as outlets
    from core import bzg_p2p_grants as grants
    from core import bzg_purchase_request as pr
    from core import rbac as rb

    outlets.ensure_schema(conn)
    outlets.seed_registry(conn, TS)
    for person in grants.GGV_CONTENT_DENY_PERSONS[:1]:
        for outlet_id in grants.GGV_CONTENT_DENY_OUTLETS:
            target = pr.outlet_rbac_target(outlet_id, conn)
            for code in grants.GGV_CONTENT_DENY_PERMISSIONS:
                ev = rb.evaluate(person, code, target, conn=conn)
                check(
                    f"fixture {person} DENY {code} on {outlet_id}",
                    not ev.get("allowed"),
                    ev.get("reason", ""),
                )
    bare = rb.evaluate("PERS-HAIKAL", "bzg.ap.mark_ready", {}, conn=conn)
    check(
        "bzg.ap.mark_ready bare target DENY entity_scope_required",
        not bare.get("allowed") and bare.get("reason") == "entity_scope_required",
        str(bare),
    )
    bare_pay = rb.evaluate("PERS-HAIKAL", "bzg.pay.mark_ready", {}, conn=conn)
    check(
        "bzg.pay.mark_ready bare target DENY entity_scope_required",
        not bare_pay.get("allowed") and bare_pay.get("reason") == "entity_scope_required",
        str(bare_pay),
    )


def test_segregation_on_fixture(conn: sqlite3.Connection, db_path: Path) -> None:
    from core import bzg_ap_ready as ap
    from core import bzg_goods_receiving as gr
    from core import bzg_outlet_registry as outlets
    from core import bzg_purchase_order as po
    from core import bzg_purchase_request as pr
    from core import bzg_supplier_bill as bill
    from core import bzg_three_way_match as match
    from core import uma_ops_console as ops

    for mod in (ops, pr, po, gr, bill, match, ap, outlets):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = db_path

    outlets.ensure_schema(conn)
    outlets.seed_registry(conn, TS)
    ops.ensure_schema(conn)
    pr.ensure_pr_columns(conn)
    po.ensure_po_schema(conn)
    gr.ensure_gr_schema(conn)
    bill.ensure_bill_schema(conn)
    match.ensure_match_schema(conn)
    ap.ensure_ap_schema(conn)

    ts = TS
    for perm_id, code, action in (
        ("PERM-VENUE-RECEIVE", "venue.receive", "receive"),
        ("PERM-BZG-MATCH-RUN", "bzg.match.run", "match_run"),
    ):
        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description, status, created_at, updated_at
            ) VALUES (?, ?, 'bzg', ?, 'test seed', 'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET status='ACTIVE'
            """,
            (perm_id, code, action, ts, ts),
        )
    for role_id, perms in (
        (
            "ROLE-BZG-FB-OPS-LEAD",
            (
                "PERM-BZG-PO-CREATE",
                "PERM-VENUE-RECEIVE",
                "PERM-BZG-BILL-CAPTURE",
                "PERM-BZG-MATCH-RUN",
                "PERM-BZG-AP-MARK-READY",
                "PERM-BZG-PAY-MARK-READY",
            ),
        ),
    ):
        conn.execute(
            """
            INSERT INTO org_roles (role_id, display_name, department_id, role_type, status, created_at, updated_at)
            VALUES (?, 'Ops', 'DEPT-BZG-FB', 'OPERATING', 'ACTIVE', ?, ?)
            ON CONFLICT(role_id) DO NOTHING
            """,
            (role_id, ts, ts),
        )
        for perm_id in perms:
            conn.execute(
                """
                INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
                VALUES (?, ?, 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW'
                """,
                (role_id, perm_id, ts, ts),
            )
    for pos_id, person_id, asg_id in (
        ("POS-PO-1", "PERS-PO", "ASG-PO-1"),
        ("POS-CAP-1", "PERS-CAP", "ASG-CAP-1"),
        ("POS-CTRL-1", "PERS-CTRL", "ASG-CTRL-1"),
    ):
        conn.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, brand_id, department_id,
              position_label, status, fte, created_at, updated_at
            ) VALUES (?, 'ROLE-BZG-FB-OPS-LEAD', 'ENT-BZG', 'BZG-UMA', 'DEPT-BZG-FB',
                      ?, 'ACTIVE', 1.0, ?, ?)
            ON CONFLICT(position_id) DO NOTHING
            """,
            (pos_id, pos_id, ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
            VALUES (?, ?, NULL, 'ACTIVE', ?, ?)
            ON CONFLICT(person_id) DO NOTHING
            """,
            (person_id, person_id, ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, status, start_at, end_at, created_at, updated_at
            ) VALUES (?, ?, ?, 'ACTIVE', ?, NULL, ?, ?)
            ON CONFLICT(assignment_id) DO NOTHING
            """,
            (asg_id, person_id, pos_id, ts, ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_assignment_scopes (
              assignment_id, scope_id, status, start_at, end_at, created_at, updated_at
            ) VALUES (?, 'SCOPE-BZG-UMA', 'ACTIVE', ?, NULL, ?, ?)
            """,
            (asg_id, ts, ts, ts),
        )
    conn.execute(
        """
        INSERT INTO org_scopes (scope_id, scope_type, display_name, status, created_at, updated_at)
        VALUES ('SCOPE-BZG-UMA', 'brand', 'Uma Blu', 'ACTIVE', ?, ?)
        ON CONFLICT(scope_id) DO NOTHING
        """,
        (ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES ('SCOPE-BZG-UMA', 'brand', 'BZG-UMA', ?)
        ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
        """,
        (ts,),
    )
    conn.commit()

    ops.insert_pr_row(
        pr_id="PR-SOD-1",
        state="APPROVED",
        purpose="Segregation probe",
        example=False,
        conn=conn,
    )
    conn.execute(
        """
        UPDATE bzg_ops_purchase_requests
        SET outlet_id=?, entity_id='ENT-BZG', requester_person_id=?, requester_assignment_id='ASG-REQ'
        WHERE pr_id=?
        """,
        ("BZG-UMA", "PERS-REQ", "PR-SOD-1"),
    )
    conn.execute(
        """
        INSERT INTO bzg_ops_pr_lines (line_id, pr_id, item, qty, unit, created_at)
        VALUES ('PRL-SOD-1', 'PR-SOD-1', 'Cooking oil', 10, 'L', ?)
        """,
        (ts,),
    )
    conn.commit()
    po._supplier_resolver = lambda sid: {"supplier_id": sid, "name": "Sup"} if sid else None
    saved_po = po.create_purchase_order(
        person_id="PERS-PO",
        pr_id="PR-SOD-1",
        supplier_id="SUP-1",
        lines=[{"item": "Cooking oil", "qty": 10, "unit": "L"}],
        conn=conn,
        commit=True,
    )
    full_gr = gr.create_goods_receipt(
        person_id="PERS-CAP",
        po_id=saved_po["po_id"],
        lines=[{"po_line_id": saved_po["lines"][0]["line_id"], "received_qty": 10}],
        conn=conn,
        commit=True,
    )
    bill.NOTA_PHOTO_DIR = db_path.parent / "nota-photos"
    saved_photo = bill.save_nota_photo_bytes(
        data=b"\xff\xd8\xff\xe0" + b"fake-jpeg-bytes-for-test",
        filename="nota.jpg",
        content_type="image/jpeg",
    )
    photo = saved_photo["photo_object_ref"]
    saved_bill = bill.create_supplier_bill(
        person_id="PERS-CAP",
        gr_id=full_gr["gr_id"],
        nota_number="NOTA-SOD-1",
        nota_date="2026-10-05",
        photo_object_ref=photo,
        lines=[
            {
                "gr_line_id": full_gr["lines"][0]["line_id"],
                "billed_qty": 10,
                "billed_unit_price": 100_000,
            }
        ],
        stated_total=1_000_000,
        conn=conn,
        commit=True,
    )
    match.run_three_way_match(
        person_id="PERS-CTRL",
        bill_id=saved_bill["bill_id"],
        conn=conn,
        commit=True,
    )
    try:
        ap.mark_ap_ready(person_id="PERS-PO", bill_id=saved_bill["bill_id"], conn=conn, commit=False)
        check("po creator DENY ap.mark_ready", False, "should raise")
    except ap.ApReadyError as exc:
        check("po creator DENY ap.mark_ready", exc.code == "po_creator_cannot_mark_pay_ready", str(exc))
    try:
        ap.mark_ap_ready(person_id="PERS-CAP", bill_id=saved_bill["bill_id"], conn=conn, commit=False)
        check("nota recorder DENY ap.mark_ready", False, "should raise")
    except ap.ApReadyError as exc:
        check(
            "nota recorder DENY ap.mark_ready",
            exc.code == "nota_recorder_cannot_mark_pay_ready",
            str(exc),
        )
    ready = ap.mark_ap_ready(
        person_id="PERS-CTRL",
        bill_id=saved_bill["bill_id"],
        conn=conn,
        commit=True,
    )
    check("controller may mark ap ready", ready.get("bill_id") == saved_bill["bill_id"])


def test_live_catalog() -> None:
    if not LIVE_DB.is_file():
        check("live catalog present", False, str(LIVE_DB))
        return
    from core import bzg_p2p_grants as grants
    from core import bzg_purchase_request as pr
    from core import rbac as rb

    conn = sqlite3.connect(str(LIVE_DB))
    conn.row_factory = sqlite3.Row
    try:
        for person in grants.GGV_CONTENT_DENY_PERSONS:
            for outlet_id in grants.GGV_CONTENT_DENY_OUTLETS:
                try:
                    target = pr.outlet_rbac_target(outlet_id, conn)
                except Exception:
                    continue
                for code in grants.GGV_CONTENT_DENY_PERMISSIONS:
                    ev = rb.evaluate(person, code, target, conn=conn)
                    check(
                        f"live {person} DENY {code} on {outlet_id}",
                        not ev.get("allowed"),
                        ev.get("reason", ""),
                    )
        for person in grants.CHAIN_DENY_LIVE_PERSONS:
            outlets = pr.person_outlets(person, conn) or [{"outlet_id": "BZG-UMA"}]
            for outlet in outlets:
                oid = str(outlet.get("outlet_id") or "")
                if not oid:
                    continue
                target = pr.outlet_rbac_target(oid, conn)
                full = grants.person_holds_full_chain(
                    person, oid, conn, rbac_can=rb.can, outlet_target=pr.outlet_rbac_target
                )
                check(
                    f"live {person} cannot hold full chain on {oid}",
                    not full,
                    str({c: rb.can(person, c, target, conn=conn) for c in grants.CHAIN_DENY_PERMISSIONS}),
                )
        row = conn.execute(
            "SELECT state FROM venue_daily_closes WHERE close_id=?",
            (PROTECTED_CLOSE,),
        ).fetchone()
        check("protected close untouched", row is not None, PROTECTED_CLOSE)
    finally:
        conn.close()


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "content_library.sqlite"
        shutil.copy(LIVE_DB, db) if LIVE_DB.is_file() else db.touch()
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        try:
            bootstrap_org(conn)
            seed_fixture_matrix(conn)
            test_ggv_content_deny_on_fixture(conn)
            test_segregation_on_fixture(conn, db)
        finally:
            conn.close()
    test_live_catalog()
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
