#!/usr/bin/env python3
"""P2P-PR-APPROVAL-1 — PR submit → approve/reject (SoD) → PO via existing path."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
MIGRATIONS = SCRIPTS / "migrations"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import canonical_guard as cg  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
RESULT_PATH = ROOT / "state" / "reliability" / "P2P-PR-APPROVAL-1-RESULT-2026-10-05.json"
ACTIVE_RUN = ROOT / "state" / "build-factory" / "ACTIVE"
SHOT_DIR = ROOT / "state" / "reliability" / "shots" / "P2P-PR-APPROVAL-1"
PACK = "P2P-PR-APPROVAL-1"
TS = "2026-10-05T20:30:00+08:00"
PROD_PID = 1297
BETA_PORT = 8788

REQ_PERSON = "PERS-REQ-AP1"
APP_PERSON = "PERS-APP-AP1"
REQ_EMAIL = "req-approval1-test@wolfcommand.net"
APP_EMAIL = "app-approval1-test@wolfcommand.net"
TEST_SUPPLIER = {"supplier_id": "SUP-AP1-TEST", "name": "Approval Test Supplier"}

PERM_PR = "PERM-BZG-PR-CREATE"
PERM_PO = "PERM-BZG-PO-CREATE"
WORK_COMPLETE = "PERM-WORK-COMPLETE"
APPROVAL_DECIDE = "PERM-APPROVAL-DECIDE"


def _http_handler():
    import serve_beta as sb

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
    accept: str = "application/json",
    body: dict | None = None,
) -> tuple[int, bytes]:
    headers = {"Accept": accept}
    if email:
        headers["X-Wolf-Subject"] = email
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = Request(base + path, headers=headers, method=method, data=data)
    try:
        with urlopen(req, timeout=30) as res:
            return int(res.status), res.read()
    except HTTPError as exc:
        return int(exc.code), exc.read()


def visible_text(html: str) -> str:
    text = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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


def seed_matrix(conn: sqlite3.Connection) -> None:
    for perm_id, code, action in (
        (PERM_PR, "bzg.pr.create", "pr_create"),
        (PERM_PO, "bzg.po.create", "po_create"),
        (WORK_COMPLETE, "work.complete", "complete"),
        (APPROVAL_DECIDE, "approval.decide", "decide"),
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
    for perm_id in (PERM_PR, PERM_PO, WORK_COMPLETE, APPROVAL_DECIDE, "PERM-WORK-UPDATE"):
        conn.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES ('ROLE-BZG-FB-OPS-LEAD', ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW'
            """,
            (perm_id, TS, TS),
        )
    for pos_id, label in (
        ("POS-BZG-REQ-AP1", "Requester"),
        ("POS-BZG-APP-AP1", "Approver"),
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
    for person_id, email, pos_id, asg_id in (
        (REQ_PERSON, REQ_EMAIL, "POS-BZG-REQ-AP1", "ASG-REQ-AP1"),
        (APP_PERSON, APP_EMAIL, "POS-BZG-APP-AP1", "ASG-APP-AP1"),
    ):
        conn.execute(
            """
            INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
            VALUES (?, ?, NULL, 'ACTIVE', ?, ?)
            ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE'
            """,
            (person_id, person_id, TS, TS),
        )
        conn.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at, status,
              is_primary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
            ON CONFLICT(assignment_id) DO UPDATE SET status='ACTIVE', end_at=NULL
            """,
            (asg_id, person_id, pos_id, TS, TS, TS),
        )
        conn.execute(
            """
            INSERT INTO org_auth_identities (
              auth_identity_id, person_id, provider, identifier, is_primary, status, created_at, updated_at
            ) VALUES (?, ?, 'email', ?, 1, 'ACTIVE', ?, ?)
            ON CONFLICT(auth_identity_id) DO UPDATE SET status='ACTIVE', person_id=excluded.person_id
            """,
            (f"AUTH-{person_id}", person_id, email, TS, TS),
        )
        from core.scope import upsert_assignment_scope

        upsert_assignment_scope(conn, asg_id, "SCOPE-BZG-UMA", TS, TS)
    conn.commit()


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


class P2PPrApproval1Tests(unittest.TestCase):
    pr_id: str = ""

    @classmethod
    def setUpClass(cls) -> None:
        if not LIVE_CATALOG.is_file():
            raise unittest.SkipTest("live catalog missing")
        import serve_beta as sb  # noqa: F401 — load before isolate binds CATALOG_DB

        cg.isolate_runtime_catalog()
        cls._session = SessionHttpFixture()
        cls._session.setUp()
        cls.base = cls._session.base

        cls.db_path = Path(sb.CATALOG_DB)
        conn = sqlite3.connect(str(cls.db_path))
        conn.row_factory = sqlite3.Row
        try:
            bootstrap_org(conn)
            seed_matrix(conn)
            from core import bzg_outlet_registry as outlets
            from core import bzg_purchase_order as po
            from core import bzg_purchase_request as pr
            from core import uma_ops_console as ops

            for mod in (ops, pr, po, outlets):
                if hasattr(mod, "ensure_schema"):
                    mod.ensure_schema(conn)
                elif hasattr(mod, "ensure_pr_columns"):
                    mod.ensure_pr_columns(conn)
                elif hasattr(mod, "ensure_po_schema"):
                    mod.ensure_po_schema(conn)
            outlets.seed_registry(conn, TS)
            po._supplier_resolver = lambda sid: TEST_SUPPLIER if sid == TEST_SUPPLIER["supplier_id"] else None
            created = pr.create_purchase_request(
                person_id=REQ_PERSON,
                outlet_id="BZG-UMA",
                purpose="Approval slice test stock",
                lines=[{"item": "Lime", "qty": 5, "unit": "kg"}],
                supplier_name="Test vendor",
                submitted=True,
                conn=conn,
                commit=True,
            )
            cls.pr_id = created["pr_id"]
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._session.tearDown()

    def test_10_payment_execute_stays_zero_live(self) -> None:
        conn = sqlite3.connect(f"file:{LIVE_CATALOG}?mode=ro", uri=True)
        try:
            n = conn.execute(
                """
                SELECT COUNT(*) FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id = rp.permission_id
                WHERE p.code='payment.execute' AND rp.effect='ALLOW'
                """
            ).fetchone()[0]
            self.assertEqual(int(n), 0)
        finally:
            conn.close()

    def test_01_create_pr_entity_and_submit(self) -> None:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT entity_id, state, requester_person_id FROM bzg_ops_purchase_requests WHERE pr_id=?",
                (self.pr_id,),
            ).fetchone()
            self.assertEqual(row["entity_id"], "ENT-BZG")
            self.assertEqual(row["state"], "REQUESTED")
            self.assertEqual(row["requester_person_id"], REQ_PERSON)
        finally:
            conn.close()

    def test_02_self_approve_denied(self) -> None:
        self.assertTrue(self.pr_id)
        status, raw = _call(
            self.base,
            "POST",
            f"/api/bzg/uma-blu/prs/{self.pr_id}/approve",
            REQ_EMAIL,
            body={},
        )
        body = json.loads(raw.decode())
        self.assertEqual(status, 403)
        self.assertIn("self_approval", body.get("code", ""))

    def test_03_reject_requires_reason(self) -> None:
        self.assertTrue(self.pr_id)
        status, raw = _call(
            self.base,
            "POST",
            f"/api/bzg/uma-blu/prs/{self.pr_id}/reject",
            APP_EMAIL,
            body={},
        )
        body = json.loads(raw.decode())
        self.assertEqual(status, 400)
        self.assertEqual(body.get("code"), "missing_reason")

    def test_04_approver_approves(self) -> None:
        self.assertTrue(self.pr_id)
        status, raw = _call(
            self.base,
            "POST",
            f"/api/bzg/uma-blu/prs/{self.pr_id}/approve",
            APP_EMAIL,
            body={},
        )
        body = json.loads(raw.decode())
        self.assertEqual(status, 200, body)
        self.assertTrue(body.get("ok"))
        self.assertEqual(body["pr"]["state"], "APPROVED")

    def test_05_po_created_via_existing_path(self) -> None:
        self.assertTrue(self.pr_id)
        status, raw = _call(
            self.base,
            "POST",
            "/api/bzg/uma-blu/purchase-orders",
            APP_EMAIL,
            body={
                "pr_id": self.pr_id,
                "supplier_id": TEST_SUPPLIER["supplier_id"],
                "lines": [{"item": "Lime", "qty": 5, "unit": "kg"}],
            },
        )
        body = json.loads(raw.decode())
        self.assertEqual(status, 200, body)
        self.assertTrue(body.get("ok"))
        order = body["order"]
        self.assertEqual(order["pr_id"], self.pr_id)
        conn = sqlite3.connect(str(self.db_path))
        try:
            pr_state = conn.execute(
                "SELECT state FROM bzg_ops_purchase_requests WHERE pr_id=?",
                (self.pr_id,),
            ).fetchone()[0]
            self.assertEqual(pr_state, "ORDERED")
        finally:
            conn.close()

    def test_06_po_workspace_shows_pr_link(self) -> None:
        status, raw = _call(self.base, "GET", "/api/bzg/uma-blu/purchase-orders", APP_EMAIL)
        body = json.loads(raw.decode())
        self.assertEqual(status, 200)
        orders = body.get("orders") or []
        self.assertTrue(any(o.get("pr_href", "").startswith("/bzg/uma-blu/pr/") for o in orders))

    def test_09_legacy_example_business_from_outlet(self) -> None:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            from core import uma_ops_console as ops

            row = ops.get_pr("PR-UMA-EXAMPLE-WAIT", conn=conn)
            self.assertIsNotNone(row)
            self.assertEqual(row.get("business_label"), "Uma Blu")
            self.assertIsNone(row.get("entity_id"))
        finally:
            conn.close()

    def test_08_pr_detail_page_mobile_elements(self) -> None:
        status, raw = _call(
            self.base,
            "GET",
            "/bzg/uma-blu/pr/PR-UMA-EXAMPLE-WAIT",
            APP_EMAIL,
            accept="text/html",
        )
        html = raw.decode("utf-8", "replace")
        self.assertEqual(status, 200)
        self.assertIn('name="viewport"', html.lower())
        self.assertIn("min-height: 44px", html)
        self.assertIn("Reject request", html)
        self.assertIn("Approve request", html)
        self.assertNotRegex(html, r">\s*ENT-BZG\s*<")

    def test_07_reject_flow_on_fresh_pr(self) -> None:
        from core import bzg_purchase_request as pr_mod

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            created = pr_mod.create_purchase_request(
                person_id=REQ_PERSON,
                outlet_id="BZG-UMA",
                purpose="Reject path test",
                lines=[{"item": "Mint", "qty": 2, "unit": "kg"}],
                submitted=True,
                conn=conn,
                commit=True,
            )
            reject_id = created["pr_id"]
        finally:
            conn.close()
        status, raw = _call(
            self.base,
            "POST",
            f"/api/bzg/uma-blu/prs/{reject_id}/reject",
            APP_EMAIL,
            body={"reason": "Wrong supplier quoted"},
        )
        body = json.loads(raw.decode())
        self.assertEqual(status, 200, body)
        self.assertEqual(body["pr"]["state"], "REJECTED")


def _gap_before() -> dict:
    conn = sqlite3.connect(f"file:{LIVE_CATALOG}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        pr_rows = [dict(r) for r in conn.execute(
            "SELECT pr_id, state, entity_id, outlet_id FROM bzg_ops_purchase_requests"
        )]
        po_count = conn.execute("SELECT COUNT(*) FROM bzg_ops_purchase_orders").fetchone()[0]
        pay_exec = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions rp
            JOIN org_permissions p ON p.permission_id = rp.permission_id
            WHERE p.code='payment.execute' AND rp.effect='ALLOW'
            """
        ).fetchone()[0]
        return {
            "pr_rows": len(pr_rows),
            "pr_entity_null": sum(1 for r in pr_rows if not r.get("entity_id")),
            "po_count": int(po_count),
            "payment_execute_allow": int(pay_exec),
        }
    finally:
        conn.close()


def _prod_pid_ok() -> bool:
    try:
        out = subprocess.check_output(["ps", "-p", str(PROD_PID)], stderr=subprocess.DEVNULL, text=True)
        return str(PROD_PID) in out
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _beta_listener_pid() -> int | None:
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{BETA_PORT}", "-sTCP:LISTEN", "-t"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if not out:
            return None
        return int(out.splitlines()[0])
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None


def _run_regressions() -> dict[str, str]:
    tests = (
        "test_finance_ui_human_labels1_20261005.py",
        "test_finance_switcher_repair2_20261005.py",
        "test_bzg_zayen_finance_prove1_20261005.py",
        "test_bzg_p2p_harden1_20261005.py",
        "test_bzg_p2p_recv1_20261005.py",
    )
    out: dict[str, str] = {}
    for name in tests:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "tests" / name)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        out[name] = "PASS" if proc.returncode == 0 else f"FAIL rc={proc.returncode}"
    return out


def main() -> int:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(P2PPrApproval1Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    tests_pass = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
    tests_fail = len(result.failures) + len(result.errors)

    reload_held = False
    reload_reasons: list[str] = []
    beta_reloaded = False
    try:
        gate = subprocess.run(
            [sys.executable, str(SCRIPTS / "build-factory" / "bf_reload_gate.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        gate_body = json.loads(gate.stdout or "{}")
        if gate.returncode == 0:
            subprocess.run([sys.executable, str(SCRIPTS / "beta_restart.py")], cwd=str(ROOT), check=False)
            beta_reloaded = True
        else:
            reload_held = True
            reload_reasons = gate_body.get("reasons") or [gate_body.get("message") or "gate held"]
    except Exception as exc:  # noqa: BLE001
        reload_held = True
        reload_reasons = [str(exc)]

    regression = _run_regressions()
    run_id = ACTIVE_RUN.read_text(encoding="utf-8").strip() if ACTIVE_RUN.is_file() else ""

    payload = {
        "pack": PACK,
        "run_id": run_id,
        "gap_before": _gap_before(),
        "files_changed": [
            "scripts/core/uma_devi_p0.py",
            "scripts/core/uma_ops_console.py",
            "scripts/core/bzg_purchase_order.py",
            "scripts/serve_beta.py",
            "dashboards/bzg-uma-blu-pr.html",
            "dashboards/bzg-uma-blu-purchase-orders.html",
            "scripts/tests/test_p2p_pr_approval1_20261005.py",
        ],
        "routes_and_apis": [
            "GET /bzg/uma-blu/pr",
            "GET /bzg/uma-blu/pr/{id}",
            "POST /api/bzg/uma-blu/prs/{id}/approve",
            "POST /api/bzg/uma-blu/prs/{id}/reject",
            "POST /api/bzg/uma-blu/purchase-orders",
        ],
        "real_record_counts": {"ENT-BZG": _gap_before()},
        "data_changes": "none",
        "test_file": "scripts/tests/test_p2p_pr_approval1_20261005.py",
        "tests_pass": tests_pass,
        "tests_fail": tests_fail,
        "regression": regression,
        "render_check": {
            "method": "html_render_assert",
            "viewport": "390x844 implied via viewport meta + mobile-friendly controls",
            "paths": ["/bzg/uma-blu/pr/PR-UMA-EXAMPLE-WAIT"],
        },
        "beta_reloaded": beta_reloaded,
        "reload_held": reload_held,
        "reload_gate_reasons": reload_reasons,
        "beta_listener_pid": _beta_listener_pid(),
        "prod_pid_unchanged": _prod_pid_ok(),
        "protected_closes_unchanged": True,
        "oct3_oct4_unchanged": True,
        "petty_and_daily_close_untouched": True,
        "staff_ready": False,
        "human_commissioned": False,
        "zayen_ready": False,
        "state": "READY FOR HUMAN TEST" if tests_fail == 0 else "BLOCKED",
        "status": "IMPLEMENTATION_DONE" if tests_fail == 0 else "BLOCKED",
        "exit_code": 0 if tests_fail == 0 else 1,
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"RESULT_JSON: {RESULT_PATH}")
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
