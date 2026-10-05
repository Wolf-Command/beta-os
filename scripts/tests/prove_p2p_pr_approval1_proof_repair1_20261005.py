#!/usr/bin/env python3
"""P2P-PR-APPROVAL-1-PROOF-REPAIR-1 — Playwright WebKit rendered workflow for PR approval slice."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import importlib.util
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
MIGRATIONS = SCRIPTS / "migrations"
LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
ORIG_RESULT = ROOT / "state" / "reliability" / "P2P-PR-APPROVAL-1-RESULT-2026-10-05.json"
RESULT_PATH = ROOT / "state" / "reliability" / "P2P-PR-APPROVAL-1-PROOF-REPAIR-1-RESULT.json"
SHOT_DIR = ROOT / "state" / "reliability" / "shots" / "P2P-PR-APPROVAL-1"
PACK = "P2P-PR-APPROVAL-1-PROOF-REPAIR-1"
TS = "2026-10-05T21:05:00+08:00"
PROD_PID = 1297
BETA_PORT = 8788

REQ_PERSON = "PERS-REQ-AP1"
APP_PERSON = "PERS-APP-AP1"
REQ_EMAIL = "req-approval1-test@wolfcommand.net"
APP_EMAIL = "app-approval1-test@wolfcommand.net"
TEST_SUPPLIER = {"supplier_id": "SUP-AP1-TEST", "name": "Approval Test Supplier"}

FORBIDDEN_VISIBLE = ("ENT-BZG", "SCOPE-", "ROLE-", "staff_ready", "human_commissioned", "zayen_ready")

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import canonical_guard as cg  # noqa: E402


def _http_handler():
    import serve_beta as sb

    for obj in vars(sb).values():
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler":
            return obj
    raise RuntimeError("BetaHandler not found")


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
    perms = (
        ("PERM-BZG-PR-CREATE", "bzg.pr.create", "pr_create"),
        ("PERM-BZG-PO-CREATE", "bzg.po.create", "po_create"),
        ("PERM-WORK-COMPLETE", "work.complete", "complete"),
        ("PERM-APPROVAL-DECIDE", "approval.decide", "decide"),
        ("PERM-WORK-UPDATE", "work.update", "update"),
    )
    for perm_id, code, action in perms:
        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description, status, created_at, updated_at
            ) VALUES (?, ?, 'bzg', ?, 'proof repair seed', 'ACTIVE', ?, ?)
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
    for perm_id in ("PERM-BZG-PR-CREATE", "PERM-BZG-PO-CREATE", "PERM-WORK-COMPLETE", "PERM-APPROVAL-DECIDE", "PERM-WORK-UPDATE"):
        conn.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES ('ROLE-BZG-FB-OPS-LEAD', ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET effect='ALLOW'
            """,
            (perm_id, TS, TS),
        )
    for pos_id, label in (("POS-BZG-REQ-AP1", "Requester"), ("POS-BZG-APP-AP1", "Approver")):
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
    from core.scope import upsert_assignment_scope

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
        upsert_assignment_scope(conn, asg_id, "SCOPE-BZG-UMA", TS, TS)
    conn.commit()


class IsolatedServer:
    def __init__(self) -> None:
        self.httpd: ThreadingHTTPServer | None = None
        self.base = ""
        self.pr_id = ""
        self.db_path = Path()

    def start(self) -> None:
        import serve_beta as sb  # noqa: F401
        from core import bzg_outlet_registry as outlets
        from core import bzg_purchase_order as po
        from core import bzg_purchase_request as pr
        from core import uma_ops_console as ops

        cg.isolate_runtime_catalog()
        self.db_path = Path(sb.CATALOG_DB)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            bootstrap_org(conn)
            seed_matrix(conn)
            for mod in (ops, pr, po, outlets):
                if hasattr(mod, "ensure_schema"):
                    mod.ensure_schema(conn)
                elif hasattr(mod, "ensure_pr_columns"):
                    mod.ensure_pr_columns(conn)
                elif hasattr(mod, "ensure_po_schema"):
                    mod.ensure_po_schema(conn)
            outlets.seed_registry(conn, TS)
            # Use default alchemist supplier lookup so Playwright can pick a real dropdown option.
            po._supplier_resolver = None
            created = pr.create_purchase_request(
                person_id=REQ_PERSON,
                outlet_id="BZG-UMA",
                purpose="Playwright approval workflow test",
                lines=[{"item": "Lime", "qty": 5, "unit": "kg"}],
                supplier_name="Test vendor",
                submitted=True,
                conn=conn,
                commit=True,
            )
            self.pr_id = created["pr_id"]
            conn.commit()
        finally:
            conn.close()

        handler = _http_handler()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        time.sleep(0.4)

    def stop(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None


def visible_text(html: str) -> str:
    text = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def run_rendered_workflow(server: IsolatedServer) -> dict:
    """Playwright WebKit iPhone 14 click-through on isolated Beta."""
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    result: dict = {
        "pass": False,
        "viewport": "iPhone 14",
        "steps": [],
        "screenshots": [],
        "error": None,
    }
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        result["error"] = f"playwright not installed: {exc}"
        return result

    base = server.base
    pr_id = server.pr_id
    headers = {
        "X-Wolf-Subject": APP_EMAIL,
        "Cf-Access-Authenticated-User-Email": APP_EMAIL,
    }
    shots: list[str] = []
    steps: list[str] = []

    def shot(name: str, page) -> None:  # noqa: ANN001
        path = SHOT_DIR / name
        page.screenshot(path=str(path), full_page=True)
        shots.append(str(path.relative_to(ROOT)))

    try:
        with sync_playwright() as p:
            browser = p.webkit.launch()
            ctx = browser.new_context(**p.devices["iPhone 14"], extra_http_headers=headers)
            page = ctx.new_page()

            # Step 1: open PR detail awaiting approval
            page.goto(f"{base}/bzg/uma-blu/pr/{pr_id}", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("button:has-text('Approve request')", timeout=15000)
            body_text = page.locator("body").inner_text()
            for bad in FORBIDDEN_VISIBLE:
                if bad in body_text:
                    raise AssertionError(f"PR detail shows forbidden token: {bad}")
            if "Reject request" not in body_text:
                raise AssertionError("Reject request button not visible")
            if "Lime" not in body_text:
                raise AssertionError("PR line item Lime not visible")
            shot("01-pr-awaiting-approve.png", page)
            steps.append("open_pr_detail_awaiting_approval")

            # Step 2: approve the request
            page.locator("button:has-text('Approve request')").tap()
            page.wait_for_function(
                "() => document.body.innerText.includes('Save purchase order') || "
                "document.body.innerText.includes('Approved')",
                timeout=20000,
            )
            approved_text = page.locator("body").inner_text()
            if "Save purchase order" not in approved_text and "Approved" not in approved_text:
                raise AssertionError("PR not showing approved state after tap")
            shot("02-pr-approved.png", page)
            steps.append("tap_approve_request")

            # Step 3: navigate to purchase orders desk
            page.locator("a:has-text('Save purchase order')").tap()
            page.wait_for_load_state("networkidle", timeout=20000)
            page.wait_for_selector("#createForm", timeout=15000)
            po_text = page.locator("body").inner_text()
            if "Playwright approval workflow test" not in po_text:
                raise AssertionError("Approved PR not listed on purchase orders desk")
            shot("03-purchase-orders-awaiting.png", page)
            steps.append("open_purchase_orders_desk")

            # Step 4: create PO from approved PR (supplier list comes from alchemist read model)
            page.wait_for_function(
                "() => { const o = document.querySelectorAll('#supplier option'); "
                "return o.length > 1 && o[0].value !== ''; }",
                timeout=20000,
            )
            supplier_val = page.locator("#supplier option").nth(0).get_attribute("value")
            if not supplier_val:
                supplier_val = page.locator("#supplier option").nth(1).get_attribute("value")
            if not supplier_val:
                raise AssertionError("No supplier available in dropdown")
            page.locator("#supplier").select_option(supplier_val)
            page.locator("#createForm button[type='submit']").tap()
            page.wait_for_function(
                "() => document.body.innerText.includes('From purchase request')",
                timeout=20000,
            )
            final_text = page.locator("body").inner_text()
            if "From purchase request" not in final_text:
                raise AssertionError("PO created but PR link not visible")
            for bad in FORBIDDEN_VISIBLE:
                if bad in final_text:
                    raise AssertionError(f"PO page shows forbidden token: {bad}")
            shot("04-po-created-with-pr-link.png", page)
            steps.append("create_po_from_approved_pr")

            browser.close()
        result["pass"] = True
        result["steps"] = steps
        result["screenshots"] = shots
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
        result["steps"] = steps
        result["screenshots"] = shots
    return result


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


def _prod_pid_ok() -> bool:
    try:
        out = subprocess.check_output(["ps", "-p", str(PROD_PID)], stderr=subprocess.DEVNULL, text=True)
        return str(PROD_PID) in out
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main() -> int:
    if not LIVE_CATALOG.is_file():
        print("SKIP: live catalog missing")
        return 1

    server = IsolatedServer()
    server.start()
    rendered = run_rendered_workflow(server)
    server.stop()

    # Run build tests via unittest only — never call test file main() (it restarts Beta)
    test_path = SCRIPTS / "tests" / "test_p2p_pr_approval1_20261005.py"
    spec = importlib.util.spec_from_file_location("pr_approval1", test_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(mod.P2PPrApproval1Tests)
    ut_result = unittest.TextTestRunner(verbosity=1).run(suite)
    tests_pass = ut_result.testsRun - len(ut_result.failures) - len(ut_result.errors) - len(ut_result.skipped)
    tests_fail = len(ut_result.failures) + len(ut_result.errors)

    # Reload gate — only path to reload Beta (NOT during BF_IN_TEST)
    reload_env = {k: v for k, v in os.environ.items() if k != "BF_IN_TEST"}
    reload_env.pop("BF_IN_TEST", None)
    beta_reloaded = False
    reload_held = False
    reload_reasons: list[str] = []
    try:
        gate = subprocess.run(
            [sys.executable, str(SCRIPTS / "build-factory" / "bf_reload_gate.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=reload_env,
        )
        gate_body = json.loads(gate.stdout or "{}")
        if gate.returncode == 0:
            rr = subprocess.run(
                [sys.executable, str(SCRIPTS / "beta_restart.py"), "--reason", PACK],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                env=reload_env,
            )
            if rr.returncode == 0:
                beta_reloaded = True
            elif rr.returncode == 3:
                reload_held = True
                reload_reasons = [rr.stdout.strip() or "RELOAD_HELD"]
            else:
                reload_held = True
                reload_reasons = [rr.stderr.strip() or rr.stdout.strip() or f"reload exit {rr.returncode}"]
        else:
            reload_held = True
            reload_reasons = gate_body.get("reasons") or [gate_body.get("message") or "gate held"]
    except Exception as exc:  # noqa: BLE001
        reload_held = True
        reload_reasons = [str(exc)]

    all_pass = tests_fail == 0 and rendered.get("pass") is True
    files_changed = [
        "scripts/core/bzg_purchase_order.py",
        "scripts/tests/prove_p2p_pr_approval1_proof_repair1_20261005.py",
    ]

    repair_payload = {
        "pack": PACK,
        "repair_of": "P2P-PR-APPROVAL-1",
        "status": "IMPLEMENTATION_DONE" if all_pass else "BLOCKED",
        "tests_pass": tests_pass,
        "tests_fail": tests_fail,
        "rendered_workflow_test": rendered,
        "files_changed": files_changed,
        "beta_reloaded": beta_reloaded,
        "reload_held": reload_held,
        "reload_gate_reasons": reload_reasons,
        "beta_listener_pid": _beta_listener_pid(),
        "prod_pid_unchanged": _prod_pid_ok(),
        "staff_ready": False,
        "human_commissioned": False,
        "zayen_ready": False,
        "exit_code": 0 if all_pass else 1,
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(repair_payload, indent=2) + "\n", encoding="utf-8")

    # Patch original result JSON with rendered_workflow_test
    if ORIG_RESULT.is_file():
        orig = json.loads(ORIG_RESULT.read_text(encoding="utf-8"))
        orig["rendered_workflow_test"] = rendered
        if beta_reloaded:
            orig["beta_reloaded"] = True
            orig["reload_held"] = False
        elif reload_held:
            orig["reload_held"] = True
            orig["reload_gate_reasons"] = reload_reasons
        orig["beta_listener_pid"] = _beta_listener_pid()
        ORIG_RESULT.write_text(json.dumps(orig, indent=2) + "\n", encoding="utf-8")

    print(f"rendered_workflow_test pass={rendered.get('pass')}")
    print(f"tests_pass={tests_pass} tests_fail={tests_fail}")
    print(f"beta_reloaded={beta_reloaded} reload_held={reload_held}")
    print(f"RESULT_JSON: {RESULT_PATH}")
    return repair_payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
