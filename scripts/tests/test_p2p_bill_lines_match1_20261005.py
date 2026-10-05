#!/usr/bin/env python3
"""P2P-BILL-LINES-MATCH-1 — Bill lines, line-level three-way match, difference SoD, historical AP label."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
MIGRATIONS = SCRIPTS / "migrations"
LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
PACK = "P2P-BILL-LINES-MATCH-1"
TS = "2026-10-05T20:00:00+08:00"
PROD_PID = 1297
PROD_PORT = 8787
BETA_PORT = 8788
TEST_SUPPLIER = {"supplier_id": "SUP-TEST-1", "name": "Test Supplier Co"}
PERM_PO = "PERM-BZG-PO-CREATE"
PERM_PR = "PERM-BZG-PR-CREATE"
PERM_RECV = "PERM-VENUE-RECEIVE"
PERM_BILL = "PERM-BZG-BILL-CAPTURE"
PERM_MATCH = "PERM-BZG-MATCH-RUN"
PERM_MATCH_ACCEPT = "PERM-BZG-MATCH-ACCEPT"
PERM_AP_MARK = "PERM-BZG-AP-MARK-READY"
WORK_COMPLETE = "PERM-WORK-COMPLETE"
ZAYEN_EMAIL = "zayen@bluzonegroup.com"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import canonical_guard as cg  # noqa: E402
from core.staff_access import FINANCE_EMAIL  # noqa: E402


def _http_handler():
    import serve_beta as sb

    cg.isolate_runtime_catalog()
    for obj in vars(sb).values():
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler":
            return obj
    raise RuntimeError("BetaHandler not found")


def _call(
    base: str,
    method: str,
    path: str,
    email: str | None = None,
    *,
    body: dict | None = None,
    accept: str = "application/json",
) -> tuple[int, bytes]:
    headers = {"Accept": accept}
    data = None
    if email:
        headers["X-Wolf-Subject"] = email
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = Request(base + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as res:
            return int(res.status), res.read()
    except HTTPError as exc:
        return int(exc.code), exc.read()


def _listener_pid(port: int) -> int | None:
    try:
        out = subprocess.check_output(
            ["lsof", "-i", f":{port}", "-t"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if out:
            return int(out.splitlines()[0])
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None
    return None


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
        (PERM_PO, "bzg.po.create", "po_create"),
        (PERM_RECV, "venue.receive", "receive"),
        (PERM_BILL, "bzg.bill.capture", "bill_capture"),
        (PERM_MATCH, "bzg.match.run", "match_run"),
        (PERM_MATCH_ACCEPT, "bzg.match.accept", "match_accept"),
        (PERM_AP_MARK, "bzg.ap.mark_ready", "ap_mark_ready"),
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
    for perm_id in (
        PERM_PR,
        PERM_PO,
        PERM_RECV,
        PERM_BILL,
        PERM_MATCH,
        PERM_MATCH_ACCEPT,
        PERM_AP_MARK,
        WORK_COMPLETE,
        "PERM-WORK-UPDATE",
    ):
        conn.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES ('ROLE-BZG-FB-OPS-LEAD', ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW'
            """,
            (perm_id, TS, TS),
        )
    for pos_id, label in (
        ("POS-BZG-FB-OPS-1", "Matcher"),
        ("POS-BZG-FB-OPS-2", "Acceptor"),
        ("POS-BZG-FB-OPS-3", "Approver"),
    ):
        conn.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, brand_id, department_id,
              position_label, status, fte, created_at, updated_at
            ) VALUES (?, 'ROLE-BZG-FB-OPS-LEAD', 'ENT-BZG', 'BZG-UMA', 'DEPT-BZG-FB', ?, 'ACTIVE', 1.0, ?, ?)
            ON CONFLICT(position_id) DO NOTHING
            """,
            (pos_id, label, TS, TS),
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


def seed_operator(
    conn: sqlite3.Connection, person_id: str, assignment_id: str, position_id: str = "POS-BZG-FB-OPS-1"
) -> str:
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES (?, ?, NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE'
        """,
        (person_id, f"Test {person_id}", TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET status='ACTIVE'
        """,
        (assignment_id, person_id, position_id, TS, TS, TS),
    )
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(conn, assignment_id, "SCOPE-BZG-UMA", TS, TS)
    conn.commit()
    return person_id


class SessionHttpFixture:
    def __init__(self) -> None:
        self.httpd: ThreadingHTTPServer | None = None
        self.base = ""

    def setUp(self) -> None:
        handler = _http_handler()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None


class P2pBillLinesMatch1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.td = tempfile.mkdtemp(prefix="p2p-blm1-", dir=str(ROOT / "state"))
        cls.db = Path(cls.td) / "content_library.sqlite"
        from core import audit as au
        from core import bzg_ap_ready as ap
        from core import bzg_finance_usability_ro as browse
        from core import bzg_goods_receiving as gr
        from core import bzg_outlet_registry as outlets
        from core import bzg_purchase_order as po
        from core import bzg_purchase_request as pr
        from core import bzg_supplier_bill as bill
        from core import bzg_three_way_match as match
        from core import rbac as rb
        from core import uma_devi_p0 as p0
        from core import uma_ops_console as ops

        cls.match_mod = match
        cls.bill_mod = bill
        cls.ap_mod = ap
        cls.browse = browse

        for mod in (ops, pr, po, gr, bill, match, ap, rb, au, outlets, p0, browse):
            if hasattr(mod, "CATALOG_DB"):
                mod.CATALOG_DB = cls.db

        po._supplier_resolver = lambda sid: TEST_SUPPLIER if sid == TEST_SUPPLIER["supplier_id"] else None
        bill.NOTA_PHOTO_DIR = Path(cls.td) / "nota-photos"

        conn = sqlite3.connect(str(cls.db))
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
        ap.ensure_ap_schema(conn)
        seed_permissions(conn)
        cls.matcher = seed_operator(conn, "PERS-MATCH", "ASG-MATCH-1", "POS-BZG-FB-OPS-1")
        cls.acceptor = seed_operator(conn, "PERS-ACCEPT", "ASG-ACCEPT-1", "POS-BZG-FB-OPS-2")
        cls.approver = seed_operator(conn, "PERS-APP", "ASG-APP-1", "POS-BZG-FB-OPS-3")
        conn.close()

        cls.photo_ref = bill.save_nota_photo_bytes(
            data=b"\xff\xd8\xff\xe0" + b"fake-jpeg",
            filename="nota.jpg",
            content_type="image/jpeg",
        )["photo_object_ref"]

        if LIVE_CATALOG.is_file():
            cls._session = SessionHttpFixture()
            cls._session.setUp()
            cls.base = cls._session.base
        else:
            cls._session = None
            cls.base = ""

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._session:
            cls._session.tearDown()

    def _build_chain(self, *, pr_id: str, bill_qty: float = 10, nota_number: str = "NOTA-BLM1") -> dict:
        from core import bzg_goods_receiving as gr
        from core import bzg_purchase_order as po
        from core import uma_ops_console as ops

        conn = sqlite3.connect(str(self.db))
        conn.row_factory = sqlite3.Row
        ops.insert_pr_row(pr_id=pr_id, state="APPROVED", purpose="test", example=False, conn=conn)
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
            (dec_id, req_id, self.approver, TS, f"corr-{dec_id}", TS),
        )
        conn.execute(
            """
            UPDATE bzg_ops_purchase_requests
            SET outlet_id='BZG-UMA', entity_id='ENT-BZG', requester_person_id=?, requester_assignment_id='ASG-X'
            WHERE pr_id=?
            """,
            (self.approver, pr_id),
        )
        conn.execute(
            "INSERT INTO bzg_ops_pr_lines (line_id, pr_id, item, qty, unit, created_at) VALUES (?, ?, 'Oil', 10, 'L', ?)",
            (f"PRL-{pr_id[-4:]}", pr_id, TS),
        )
        conn.commit()
        saved_po = po.create_purchase_order(
            person_id=self.approver,
            pr_id=pr_id,
            supplier_id=TEST_SUPPLIER["supplier_id"],
            lines=[{"item": "Oil", "qty": 10, "unit": "L"}],
            conn=conn,
            commit=True,
        )
        po_line_id = saved_po["lines"][0]["line_id"]
        full_gr = gr.create_goods_receipt(
            person_id=self.matcher,
            po_id=saved_po["po_id"],
            lines=[{"po_line_id": po_line_id, "received_qty": 10}],
            conn=conn,
            commit=True,
        )
        gr_line_id = full_gr["lines"][0]["line_id"]
        saved_bill = self.bill_mod.create_supplier_bill(
            person_id=self.matcher,
            gr_id=full_gr["gr_id"],
            nota_number=nota_number,
            nota_date="2026-10-05",
            photo_object_ref=self.photo_ref,
            stated_total=bill_qty * 100_000,
            lines=[{"gr_line_id": gr_line_id, "billed_qty": bill_qty, "billed_unit_price": 100_000}],
            conn=conn,
            commit=True,
        )
        conn.close()
        return {
            "bill_id": saved_bill["bill_id"],
            "gr_id": full_gr["gr_id"],
            "po_id": saved_po["po_id"],
            "lines": saved_bill["lines"],
        }

    def test_bill_lines_persisted(self) -> None:
        chain = self._build_chain(pr_id="PR-BLM-LINES01")
        self.assertEqual(len(chain["lines"]), 1)
        self.assertAlmostEqual(chain["lines"][0]["billed_qty"], 10.0)
        self.assertAlmostEqual(chain["lines"][0]["billed_unit_price"], 100_000.0)

    def test_line_level_match_persists_row(self) -> None:
        chain = self._build_chain(pr_id="PR-BLM-MATCH01", nota_number="NOTA-MATCH-BLM")
        conn = sqlite3.connect(str(self.db))
        conn.row_factory = sqlite3.Row
        matched = self.match_mod.run_three_way_match(
            person_id=self.matcher,
            bill_id=chain["bill_id"],
            conn=conn,
            commit=True,
        )
        row = conn.execute(
            "SELECT match_id FROM bzg_ops_three_way_matches WHERE bill_id=?",
            (chain["bill_id"],),
        ).fetchone()
        line_cnt = conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_bill_lines WHERE bill_id=?",
            (chain["bill_id"],),
        ).fetchone()[0]
        conn.close()
        self.assertEqual(matched["result"], "MATCH")
        self.assertIsNotNone(row)
        self.assertEqual(line_cnt, 1)
        self.assertTrue(matched.get("line_details"))
        self.assertIn("ordered_qty", matched["line_details"][0])

    def test_difference_not_ap_eligible_until_accepted(self) -> None:
        chain = self._build_chain(pr_id="PR-BLM-DIFF01", bill_qty=8, nota_number="NOTA-DIFF-BLM")
        conn = sqlite3.connect(str(self.db))
        conn.row_factory = sqlite3.Row
        diff = self.match_mod.run_three_way_match(
            person_id=self.matcher,
            bill_id=chain["bill_id"],
            conn=conn,
            commit=True,
        )
        self.assertEqual(diff["result"], "DIFFERENCE")
        self.assertFalse(diff.get("ap_eligible"))
        with self.assertRaises(self.ap_mod.ApReadyError) as exc:
            self.ap_mod.mark_ap_ready(person_id=self.acceptor, bill_id=chain["bill_id"], conn=conn, commit=False)
        self.assertEqual(exc.exception.code, "difference_not_accepted")
        with self.assertRaises(self.match_mod.MatchError) as exc2:
            self.match_mod.accept_match_difference(
                person_id=self.matcher,
                bill_id=chain["bill_id"],
                reason="test",
                conn=conn,
                commit=False,
            )
        self.assertEqual(exc2.exception.code, "sod_matcher")
        accepted = self.match_mod.accept_match_difference(
            person_id=self.acceptor,
            bill_id=chain["bill_id"],
            reason="Supplier short-delivered last crate",
            conn=conn,
            commit=True,
        )
        self.assertTrue(accepted.get("exception_accepted"))
        self.assertTrue(accepted.get("ap_eligible"))
        ready = self.ap_mod.mark_ap_ready(
            person_id=self.acceptor,
            bill_id=chain["bill_id"],
            conn=conn,
            commit=True,
        )
        self.assertEqual(ready["bill_id"], chain["bill_id"])
        conn.close()

    def test_historical_ap_shows_previous_system_label(self) -> None:
        if not LIVE_CATALOG.is_file():
            self.skipTest("live catalog missing")
        ro = sqlite3.connect(f"file:{LIVE_CATALOG}?mode=ro", uri=True)
        ro.row_factory = sqlite3.Row
        sample = ro.execute(
            "SELECT match_id FROM bzg_ops_ap_ready WHERE match_id LIKE 'MATCH-HIST-%' LIMIT 1"
        ).fetchone()
        ro.close()
        self.assertIsNotNone(sample)
        label = self.match_mod.historical_match_label(str(sample["match_id"]))
        self.assertEqual(label, "Matched in the previous system")
        status, raw = _call(self.base, "GET", "/api/bzg/finance/ap?limit=5&offset=0", FINANCE_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        rows = body.get("ap_ready") or []
        self.assertTrue(rows)
        hist = [r for r in rows if r.get("match_label")]
        self.assertTrue(hist, "expected historical AP rows with match_label")
        vis = json.dumps(rows)
        self.assertNotIn("MATCH-HIST-", vis)

    def test_purchase_orders_page_has_line_entry_and_match_ui(self) -> None:
        if not self.base:
            self.skipTest("no http session")
        status, raw = _call(self.base, "GET", "/bzg/uma-blu/purchase-orders", FINANCE_EMAIL, accept="text/html")
        self.assertEqual(status, 200)
        html = raw.decode("utf-8", "replace")
        self.assertIn("Billed qty", html)
        self.assertIn("Unit price", html)
        self.assertIn("three-way-match/accept", html)
        self.assertIn("Accept difference", html)
        self.assertNotIn("overflow-x: scroll", html.lower())

    def test_finance_ap_api_no_match_hist_ids(self) -> None:
        if not self.base:
            self.skipTest("no http session")
        status, raw = _call(self.base, "GET", "/api/bzg/finance/ap?limit=20&offset=0", FINANCE_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        vis = json.dumps(body)
        self.assertNotIn("MATCH-HIST-", vis)
        labels = [r.get("match_label") for r in body.get("ap_ready") or [] if r.get("match_label")]
        self.assertTrue(labels)
        self.assertIn("Matched in the previous system", labels[0])


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(P2pBillLinesMatch1Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
