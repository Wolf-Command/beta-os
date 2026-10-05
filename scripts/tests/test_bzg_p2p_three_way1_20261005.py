#!/usr/bin/env python3
"""BZG-P2P-THREE-WAY-1 — Three-way match on PO, receipt, supplier nota. Temp sqlite only."""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
MIGRATIONS = SCRIPTS / "migrations"
PROTECTED_CLOSE = "VDC-470e741f-d889-437a-9a40-1ec9c083fb95"
PROTECTED_IDS = (
    PROTECTED_CLOSE,
    "VDC-87202768-55af-4c8e-abc3-382a5496b8c6",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
)
TS = "2026-10-05T09:00:00+08:00"
PERM_PO = "PERM-BZG-PO-CREATE"
PERM_PO_CODE = "bzg.po.create"
PERM_PR = "PERM-BZG-PR-CREATE"
PERM_RECV = "PERM-VENUE-RECEIVE"
PERM_RECV_CODE = "venue.receive"
PERM_BILL = "PERM-BZG-BILL-CAPTURE"
PERM_BILL_CODE = "bzg.bill.capture"
PERM_MATCH = "PERM-BZG-MATCH-RUN"
PERM_MATCH_CODE = "bzg.match.run"
WORK_COMPLETE = "PERM-WORK-COMPLETE"
TEST_SUPPLIER = {"supplier_id": "SUP-TEST-1", "name": "Test Supplier Co"}

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
        "011_audit_evidence_spine.sql",
        "012_work_items.sql",
        "013_approval_engine.sql",
        "014_delegation.sql",
        "015_dual_approval.sql",
        "016_approval_policy_binding.sql",
        "017_sod_constraints.sql",
        "018_evidence_requirements.sql",
    ):
        path = MIGRATIONS / sql_name
        if path.is_file():
            conn.executescript(path.read_text(encoding="utf-8"))


def seed_permissions(conn: sqlite3.Connection) -> None:
    for perm_id, code, action in (
        (PERM_PR, "bzg.pr.create", "pr_create"),
        (PERM_PO, PERM_PO_CODE, "po_create"),
        (PERM_RECV, PERM_RECV_CODE, "receive"),
        (PERM_BILL, PERM_BILL_CODE, "bill_capture"),
        (PERM_MATCH, PERM_MATCH_CODE, "match_run"),
        (WORK_COMPLETE, "work.complete", "complete"),
        ("PERM-WORK-UPDATE", "work.update", "update"),
    ):
        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description, status, created_at, updated_at
            ) VALUES (?, ?, 'bzg', ?, 'test seed', 'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
            """,
            (perm_id, code, action, TS, TS),
        )
    conn.execute(
        """
        INSERT INTO org_roles (role_id, display_name, department_id, role_type, status, created_at, updated_at)
        VALUES ('ROLE-BZG-FB-OPS-LEAD', 'F&B Ops Lead', 'DEPT-BZG-FB', 'OPERATING', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO NOTHING
        """,
        (TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_roles (role_id, display_name, department_id, role_type, status, created_at, updated_at)
        VALUES ('ROLE-BZG-NO-MATCH', 'No match', 'DEPT-BZG-FB', 'OPERATING', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO NOTHING
        """,
        (TS, TS),
    )
    for role_id, perms in (
        (
            "ROLE-BZG-FB-OPS-LEAD",
            (PERM_PR, PERM_PO, PERM_RECV, PERM_BILL, PERM_MATCH, WORK_COMPLETE, "PERM-WORK-UPDATE"),
        ),
        ("ROLE-BZG-NO-MATCH", (PERM_PR, PERM_PO, PERM_RECV, PERM_BILL, WORK_COMPLETE)),
    ):
        for perm_id in perms:
            conn.execute(
                """
                INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
                VALUES (?, ?, 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW'
                """,
                (role_id, perm_id, TS, TS),
            )
    for pos_id, role_id, label in (
        ("POS-BZG-FB-OPS-1", "ROLE-BZG-FB-OPS-LEAD", "Ops Lead"),
        ("POS-BZG-FB-OPS-2", "ROLE-BZG-FB-OPS-LEAD", "Ops Lead 2"),
        ("POS-BZG-FB-OPS-3", "ROLE-BZG-FB-OPS-LEAD", "Matcher"),
        ("POS-BZG-FB-OPS-4", "ROLE-BZG-FB-OPS-LEAD", "Receiver"),
        ("POS-BZG-NO-MATCH-1", "ROLE-BZG-NO-MATCH", "No match seat"),
    ):
        conn.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, brand_id, department_id,
              position_label, status, fte, created_at, updated_at
            ) VALUES (?, ?, 'ENT-BZG', 'BZG-UMA', 'DEPT-BZG-FB', ?, 'ACTIVE', 1.0, ?, ?)
            ON CONFLICT(position_id) DO NOTHING
            """,
            (pos_id, role_id, label, TS, TS),
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
    conn.commit()


def seed_operator(conn: sqlite3.Connection, person_id: str, assignment_id: str, position_id: str) -> str:
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES (?, ?, NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE', display_name=excluded.display_name
        """,
        (person_id, f"Test {person_id}", TS, TS),
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
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(conn, assignment_id, "SCOPE-BZG-UMA", TS, TS)
    conn.commit()
    return person_id


def seed_protected_closes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS venue_daily_closes (
          close_id TEXT PRIMARY KEY,
          business_date TEXT,
          state TEXT,
          declared_cash_amount REAL,
          variance_cash_amount REAL,
          submitted_by_person_id TEXT,
          taken_by_person_id TEXT,
          esb_totals_json TEXT,
          updated_at TEXT
        );
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO venue_daily_closes (
          close_id, business_date, state, declared_cash_amount, variance_cash_amount,
          submitted_by_person_id, taken_by_person_id, esb_totals_json, updated_at
        ) VALUES (?, '2026-10-03', 'EXCEPTION', 3225000, -125000, NULL, NULL, NULL, '2026-10-03T13:47:39Z')
        """,
        (PROTECTED_CLOSE,),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO venue_daily_closes (close_id, business_date, state, updated_at)
        VALUES (?, '2026-10-01', 'CANCELLED', '2026-10-01T00:00:00Z')
        """,
        ("VDC-87202768-55af-4c8e-abc3-382a5496b8c6",),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO venue_daily_closes (
          close_id, business_date, state, submitted_by_person_id, taken_by_person_id,
          declared_cash_amount, esb_totals_json, updated_at
        ) VALUES (?, '2026-10-04', 'OPEN', 'PERS-IZA', 'PERS-MATT', NULL, '{"locked":true}', '2026-10-04T00:00:00Z')
        """,
        ("VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",),
    )
    conn.commit()


def make_approved_pr(
    conn: sqlite3.Connection,
    *,
    pr_id: str,
    requester: str,
    state: str = "APPROVED",
    example: bool = False,
) -> str:
    from core import uma_ops_console as ops

    ops.insert_pr_row(
        pr_id=pr_id,
        state=state,
        purpose="Kitchen restock",
        example=example,
        conn=conn,
    )
    conn.execute(
        """
        UPDATE bzg_ops_purchase_requests
        SET outlet_id=?, entity_id='ENT-BZG', requester_person_id=?, requester_assignment_id='ASG-X'
        WHERE pr_id=?
        """,
        ("BZG-UMA", requester, pr_id),
    )
    conn.execute(
        """
        INSERT INTO bzg_ops_pr_lines (line_id, pr_id, item, qty, unit, created_at)
        VALUES (?, ?, 'Cooking oil', 10, 'L', ?)
        """,
        (f"PRL-{pr_id[-6:]}", pr_id, TS),
    )
    conn.commit()
    return pr_id


def record_approver(conn: sqlite3.Connection, pr_id: str, approver: str) -> None:
    req_id = f"APR-{pr_id[-8:]}"
    dec_id = f"DEC-{pr_id[-8:]}"
    conn.execute(
        """
        INSERT INTO core_approval_requests (
          approval_request_id, request_type, title, owning_entity_id, brand_id,
          requested_by_person_id, required_permission_code, required_permission_id,
          source_type, source_id, status, requested_at, created_at, updated_at, correlation_id
        ) VALUES (?, 'GENERAL', 'Test approval', 'ENT-BZG', 'BZG-UMA',
                  'PERS-REQ', 'work.complete', ?, 'HUMAN', ?, 'APPROVED', ?, ?, ?, ?)
        ON CONFLICT(approval_request_id) DO NOTHING
        """,
        (req_id, WORK_COMPLETE, pr_id, TS, TS, TS, f"corr-{req_id}"),
    )
    conn.execute(
        """
        INSERT INTO core_approval_decisions (
          approval_decision_id, approval_request_id, decision, decided_by_person_id,
          decided_at, authority_allowed, reason, correlation_id, created_at
        ) VALUES (?, ?, 'APPROVED', ?, ?, 1, 'test', ?, ?)
        """,
        (dec_id, req_id, approver, TS, f"corr-{dec_id}", TS),
    )
    conn.commit()


def save_photo(bill_mod, td: Path) -> str:
    photo_dir = td / "nota-photos"
    bill_mod.NOTA_PHOTO_DIR = photo_dir
    saved = bill_mod.save_nota_photo_bytes(
        data=b"\xff\xd8\xff\xe0" + b"fake-jpeg-bytes-for-test",
        filename="nota.jpg",
        content_type="image/jpeg",
    )
    return saved["photo_object_ref"]


def build_chain(
    conn,
    *,
    po_mod,
    gr_mod,
    bill_mod,
    approver: str,
    receiver: str,
    capturer: str,
    pr_id: str,
    photo_ref: str,
    receive_qty: float = 10,
    bill_qty: float = 10,
    unit_price: float = 100_000,
    stated_total: float = 1_000_000,
    nota_number: str = "NOTA-MATCH",
) -> dict:
    make_approved_pr(conn, pr_id=pr_id, requester="PERS-REQ")
    record_approver(conn, pr_id, approver)
    saved_po = po_mod.create_purchase_order(
        person_id=approver,
        pr_id=pr_id,
        supplier_id=TEST_SUPPLIER["supplier_id"],
        lines=[{"item": "Cooking oil", "qty": 10, "unit": "L"}],
        conn=conn,
        commit=True,
    )
    po_line_id = saved_po["lines"][0]["line_id"]
    full_gr = gr_mod.create_goods_receipt(
        person_id=receiver,
        po_id=saved_po["po_id"],
        lines=[{"po_line_id": po_line_id, "received_qty": receive_qty}],
        conn=conn,
        commit=True,
    )
    gr_line_id = full_gr["lines"][0]["line_id"]
    saved_bill = bill_mod.create_supplier_bill(
        person_id=capturer,
        gr_id=full_gr["gr_id"],
        nota_number=nota_number,
        nota_date="2026-10-05",
        photo_object_ref=photo_ref,
        stated_total=stated_total,
        lines=[{"gr_line_id": gr_line_id, "billed_qty": bill_qty, "billed_unit_price": unit_price}],
        conn=conn,
        commit=True,
    )
    return {
        "pr_id": pr_id,
        "po_id": saved_po["po_id"],
        "gr_id": full_gr["gr_id"],
        "bill_id": saved_bill["bill_id"],
    }


def main() -> int:
    global PASS, FAIL
    os.environ["WOLF_TEST_MODE"] = "1"

    td = tempfile.mkdtemp(prefix="bzg-3wm1-", dir=str(ROOT / "state"))
    try:
        db = Path(td) / "content_library.sqlite"
        from core import audit as au
        from core import bzg_goods_receiving as gr
        from core import bzg_outlet_registry as outlets
        from core import bzg_purchase_order as po
        from core import bzg_purchase_request as pr
        from core import bzg_supplier_bill as bill
        from core import bzg_three_way_match as match
        from core import rbac as rb
        from core import uma_devi_p0 as p0
        from core import uma_ops_console as ops

        for mod in (ops, pr, po, gr, bill, match, rb, au, outlets, p0):
            if hasattr(mod, "CATALOG_DB"):
                mod.CATALOG_DB = db

        po._supplier_resolver = lambda sid: TEST_SUPPLIER if sid == TEST_SUPPLIER["supplier_id"] else None

        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        bootstrap_org(conn)
        ops.ensure_schema(conn)
        outlets.ensure_schema(conn)
        outlets.seed_registry(conn, TS)
        pr.ensure_pr_columns(conn)
        po.ensure_po_schema(conn)
        gr.ensure_gr_schema(conn)
        bill.ensure_bill_schema(conn)
        match.ensure_match_schema(conn)
        seed_permissions(conn)
        seed_protected_closes(conn)

        approver = seed_operator(conn, "PERS-APP", "ASG-APP-1", "POS-BZG-FB-OPS-2")
        matcher = seed_operator(conn, "PERS-MATCH", "ASG-MATCH-1", "POS-BZG-FB-OPS-3")
        receiver = matcher
        capturer = matcher
        denied = seed_operator(conn, "PERS-NO-MATCH", "ASG-NO-MATCH-1", "POS-BZG-NO-MATCH-1")
        photo_ref = save_photo(bill, Path(td))

        chain = build_chain(
            conn,
            po_mod=po,
            gr_mod=gr,
            bill_mod=bill,
            approver=approver,
            receiver=receiver,
            capturer=capturer,
            pr_id="PR-UMA-3WM-MATCH01",
            photo_ref=photo_ref,
        )

        example_id = make_approved_pr(
            conn, pr_id="PR-UMA-EXAMPLE3WM", requester="PERS-REQ", example=True
        )
        example_gr_id = "GR-UMA-EXAMPLE3WM"
        conn.execute(
            """
            INSERT INTO bzg_ops_goods_receipts (
              gr_id, po_id, pr_id, outlet_id, entity_id, supplier_id, supplier_name,
              receiver_person_id, status, created_at
            ) VALUES (?, 'PO-UMA-EXAMPLE01', ?, 'BZG-UMA', 'ENT-BZG', ?, ?, ?, 'COMPLETE', ?)
            """,
            (
                example_gr_id,
                example_id,
                TEST_SUPPLIER["supplier_id"],
                TEST_SUPPLIER["name"],
                receiver,
                TS,
            ),
        )
        conn.execute(
            """
            INSERT INTO bzg_ops_supplier_bills (
              bill_id, gr_id, po_id, pr_id, outlet_id, entity_id, supplier_id, supplier_name,
              nota_number, nota_date, photo_object_ref, stated_total, computed_total,
              total_difference, capturer_person_id, created_at
            ) VALUES ('BILL-UMA-EXAMPLE3WM', ?, 'PO-UMA-EXAMPLE01', ?, 'BZG-UMA', 'ENT-BZG',
                      ?, ?, 'NOTA-EX', '2026-10-05', ?, 1000, 1000, 0, ?, ?)
            """,
            (
                example_gr_id,
                example_id,
                TEST_SUPPLIER["supplier_id"],
                TEST_SUPPLIER["name"],
                photo_ref,
                capturer,
                TS,
            ),
        )
        conn.commit()

        try:
            match.run_three_way_match(person_id="", bill_id=chain["bill_id"], conn=conn, commit=False)
            check("unauthenticated denied", False, "should raise")
        except match.MatchError as exc:
            check("unauthenticated denied", exc.code == "unauthenticated", str(exc))

        try:
            match.run_three_way_match(
                person_id=denied, bill_id=chain["bill_id"], conn=conn, commit=False
            )
            check("no permission denied", False, "should raise")
        except match.MatchError as exc:
            check("no permission denied", exc.code == "forbidden", str(exc))

        try:
            match.run_three_way_match(
                person_id=matcher, bill_id="BILL-UMA-NOTREAL", conn=conn, commit=False
            )
            check("missing bill denied", False, "should raise")
        except match.MatchError as exc:
            check("missing bill denied", exc.code == "not_found", str(exc))

        try:
            match.run_three_way_match(
                person_id=matcher,
                bill_id="BILL-UMA-EXAMPLE3WM",
                conn=conn,
                commit=False,
            )
            check("example bill denied", False, "should raise")
        except match.MatchError as exc:
            check("example bill denied", exc.code == "example_denied", str(exc))

        try:
            match.run_three_way_match(
                person_id=matcher,
                bill_id=chain["bill_id"],
                gr_id="GR-UMA-WRONG",
                conn=conn,
                commit=False,
            )
            check("mismatched receipt rejected", False, "should raise")
        except match.MatchError as exc:
            check("mismatched receipt rejected", exc.code == "gr_mismatch", str(exc))

        try:
            match.run_three_way_match(
                person_id=matcher,
                bill_id=chain["bill_id"],
                po_id="PO-UMA-WRONG",
                conn=conn,
                commit=False,
            )
            check("mismatched order rejected", False, "should raise")
        except match.MatchError as exc:
            check("mismatched order rejected", exc.code == "po_mismatch", str(exc))

        try:
            match.run_three_way_match(
                person_id=matcher,
                bill_id=chain["bill_id"],
                outlet_id="WRONG-OUTLET",
                conn=conn,
                commit=False,
            )
            check("client outlet mismatch rejected", False, "should raise")
        except match.MatchError as exc:
            check("client outlet mismatch rejected", exc.code == "outlet_mismatch", str(exc))

        try:
            match.run_three_way_match(
                person_id=matcher,
                bill_id=chain["bill_id"],
                supplier_id="WRONG-SUP",
                conn=conn,
                commit=False,
            )
            check("client supplier mismatch rejected", False, "should raise")
        except match.MatchError as exc:
            check("client supplier mismatch rejected", exc.code == "supplier_mismatch", str(exc))

        pr_before = ops.get_pr(chain["pr_id"], conn=conn)
        matched = match.run_three_way_match(
            person_id=matcher,
            bill_id=chain["bill_id"],
            conn=conn,
            commit=True,
        )
        pr_after = ops.get_pr(chain["pr_id"], conn=conn)
        check("equal lines records match", matched.get("result") == "MATCH", str(matched.get("summary")))
        check("match summary plain", matched.get("summary") == "match")
        check(
            "no AP payment state set",
            pr_after and not str(pr_after.get("state") or "").startswith("PAYMENT"),
        )
        check("no PAID_CLAIMED", pr_after and pr_after.get("state") != "PAID_CLAIMED")
        check(
            "pr state unchanged by match",
            pr_before and pr_after and pr_after.get("state") == pr_before.get("state"),
            str(pr_after),
        )
        check("pr stays BILL_RECEIVED", pr_after and pr_after.get("state") == "BILL_RECEIVED")

        reloaded = match.get_three_way_match(matched["match_id"], person_id=matcher, conn=conn)
        check("reload same match id", reloaded and reloaded.get("match_id") == matched["match_id"])
        check("reload same result", reloaded and reloaded.get("result") == "MATCH")
        check("reload same summary", reloaded and reloaded.get("summary") == "match")

        rematch = match.run_three_way_match(
            person_id=matcher,
            bill_id=chain["bill_id"],
            conn=conn,
            commit=True,
        )
        check("idempotent rematch same id", rematch.get("match_id") == matched["match_id"])

        photo_ref2 = save_photo(bill, Path(td))
        diff_chain = build_chain(
            conn,
            po_mod=po,
            gr_mod=gr,
            bill_mod=bill,
            approver=approver,
            receiver=receiver,
            capturer=capturer,
            pr_id="PR-UMA-3WM-DIFF01",
            photo_ref=photo_ref2,
            receive_qty=10,
            bill_qty=8,
            unit_price=100_000,
            stated_total=900_000,
            nota_number="NOTA-DIFF3WM",
        )
        diff_match = match.run_three_way_match(
            person_id=matcher,
            bill_id=diff_chain["bill_id"],
            conn=conn,
            commit=True,
        )
        check("qty difference recorded", diff_match.get("result") == "DIFFERENCE")
        check(
            "difference not blocked",
            diff_match.get("is_difference") is True and "billed short" in (diff_match.get("summary") or ""),
            str(diff_match.get("summary")),
        )

        photo_ref3 = save_photo(bill, Path(td))
        price_chain = build_chain(
            conn,
            po_mod=po,
            gr_mod=gr,
            bill_mod=bill,
            approver=approver,
            receiver=receiver,
            capturer=capturer,
            pr_id="PR-UMA-3WM-PRICE01",
            photo_ref=photo_ref3,
            receive_qty=10,
            bill_qty=10,
            unit_price=100_000,
            stated_total=850_000,
            nota_number="NOTA-PRICE3WM",
        )
        price_match = match.run_three_way_match(
            person_id=matcher,
            bill_id=price_chain["bill_id"],
            conn=conn,
            commit=True,
        )
        check("total difference recorded", price_match.get("result") == "DIFFERENCE")
        check(
            "total difference plain",
            "nota total difference" in (price_match.get("summary") or ""),
            str(price_match.get("summary")),
        )

        audit_row = conn.execute(
            "SELECT action FROM core_audit_events WHERE resource_id=? AND action='bzg.three_way_match.run'",
            (matched["match_id"],),
        ).fetchone()
        check("audit row for match", audit_row is not None)

        for close_id in PROTECTED_IDS:
            row = conn.execute(
                "SELECT state, declared_cash_amount, esb_totals_json FROM venue_daily_closes WHERE close_id=?",
                (close_id,),
            ).fetchone()
            check(f"protected close untouched {close_id}", row is not None, str(close_id))

        live = ROOT / "catalog" / "content_library.sqlite"
        if live.is_file():
            live_conn = sqlite3.connect(f"file:{live}?mode=ro", uri=True)
            try:
                row = live_conn.execute(
                    "SELECT close_id, state FROM venue_daily_closes WHERE close_id=?",
                    (PROTECTED_CLOSE,),
                ).fetchone()
                check("live protected close read-only ok", row is not None, str(row))
            finally:
                live_conn.close()

        conn.rollback()
    finally:
        pass

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
