#!/usr/bin/env python3
"""GGV-RECEIPT-WORKFLOW-1-PROOF-REPAIR-1 — Playwright WebKit rendered workflow for GGV receipt/nota slice."""
from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
ORIG_RESULT = ROOT / "state" / "reliability" / "GGV-RECEIPT-WORKFLOW-1-RESULT-2026-10-05.json"
RESULT_PATH = ROOT / "state" / "reliability" / "GGV-RECEIPT-WORKFLOW-1-PROOF-REPAIR-1-RESULT.json"
SHOT_DIR = ROOT / "state" / "reliability" / "shots" / "GGV-RECEIPT-WORKFLOW-1"
PACK = "GGV-RECEIPT-WORKFLOW-1-PROOF-REPAIR-1"
PROD_PID = 1297
BETA_PORT = 8788
ENTITY = "ENT-GGV"
MATT_EMAIL = "mrwolf@wolfcommand.net"
AMANDA_EMAIL = "amanda@wolfcommand.net"

FORBIDDEN_VISIBLE = ("ENT-GGV", "SCOPE-", "ROLE-", "staff_ready", "human_commissioned", "zayen_ready", "vault_path", "/Users/")

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import canonical_guard as cg  # noqa: E402
from core import ggv_finance_nota as fin  # noqa: E402
from core import ggv_receipt_accounting1 as gra  # noqa: E402


def _http_handler():
    import serve_beta as sb

    for obj in vars(sb).values():
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler":
            return obj
    raise RuntimeError("BetaHandler not found")


def _seed_receipt(conn: sqlite3.Connection, key: str, *, path: Path) -> None:
    gra.ensure_schema(conn)
    ts = "2026-10-05T23:59:59Z"
    extraction = json.dumps({"vendor": "Playwright Vendor", "amount": "100000", "note": "proof repair fixture"})
    conn.execute(
        """
        INSERT OR REPLACE INTO ggv_receipt_accounting (
          receipt_key, entity_id, vault_filename, vault_queue, vault_path,
          content_sha256, accounting_queue, extraction_json, human_confirmed_json,
          duplicate_of, missing_evidence, bank_match_proposed, bank_match_confirmed,
          confirmed_by_person_id, confirmed_at, upload_date, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            key,
            ENTITY,
            key,
            "processed",
            str(path),
            "abc123pw",
            "needs_review",
            extraction,
            None,
            None,
            0,
            None,
            0,
            None,
            None,
            "2026-10-05",
            ts,
            ts,
        ),
    )
    conn.commit()


def _seed_nota(conn: sqlite3.Connection, nota_id: str) -> None:
    fin.ensure_schema(conn)
    ts = "2026-10-05T23:59:59Z"
    proposals = json.dumps(
        {"fields": {"vendor_name": "PW Fixture Vendor", "amount": "50000", "invoice_no": "INV-PW-1"}}
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO ggv_notas (
          nota_id, entity_id, vendor_id, invoice_no, nota_date, currency, amount, tax,
          category, items_json, notes, workflow_state, amount_confirmed, date_confirmed,
          vendor_confirmed, proposals_json, confidence_json, created_by_person_id,
          created_at, updated_at, submitted_at, approval_request_id,
          duplicate_of_nota_id, duplicate_reason
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            nota_id,
            ENTITY,
            None,
            "INV-PW-1",
            "2026-10-01",
            "IDR",
            "50000",
            None,
            "Supplies",
            "[]",
            None,
            "needs_review",
            0,
            0,
            0,
            proposals,
            "{}",
            "PERS-MATT",
            ts,
            ts,
            None,
            None,
            None,
            None,
        ),
    )
    conn.commit()


class IsolatedServer:
    def __init__(self) -> None:
        self.httpd: ThreadingHTTPServer | None = None
        self.base = ""
        self.receipt_key = ""
        self.nota_id = ""

    def start(self) -> None:
        import serve_beta as sb  # noqa: F401

        cg.isolate_runtime_catalog()
        self.db_path = Path(sb.CATALOG_DB)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            gra.ensure_schema(conn)
            fin.ensure_schema(conn)
            tmp = tempfile.mkdtemp()
            img = Path(tmp) / "pw_receipt_fixture.jpg"
            img.write_bytes(b"\xff\xd8\xff\xe0" + b"playwright jpeg fixture")
            self.receipt_key = "pw_receipt_fixture.jpg"
            self.nota_id = "NOTA-PW-REPAIR-1"
            _seed_receipt(conn, self.receipt_key, path=img)
            _seed_nota(conn, self.nota_id)
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
    receipt_key = server.receipt_key
    nota_id = server.nota_id
    headers = {
        "X-Wolf-Subject": AMANDA_EMAIL,
        "Cf-Access-Authenticated-User-Email": AMANDA_EMAIL,
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

            # Step 1: open GGV finance notas tab (receipt queue inline)
            page.goto(f"{base}/ggv/finance/notas", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("h2:has-text('Receipt queue')", timeout=15000)
            page.wait_for_function(
                "() => document.body.innerText.includes('Receipt queue · showing')",
                timeout=20000,
            )
            body_text = page.locator("body").inner_text()
            for bad in FORBIDDEN_VISIBLE:
                if bad in body_text:
                    raise AssertionError(f"Notas page shows forbidden token: {bad}")
            if "Vault receipts for accountant review" not in body_text:
                raise AssertionError("Receipt queue intro not visible on notas tab")
            page.wait_for_selector("button.rx-open-inline", timeout=15000)
            shot("01-notas-receipt-queue.png", page)
            steps.append("open_ggv_finance_notas_receipt_queue")

            # Step 2: open seeded fixture receipt (not first catalog row)
            fixture_btn = page.locator(f"button.rx-open-inline[data-rx-key='{receipt_key}']")
            page.wait_for_selector(f"button.rx-open-inline[data-rx-key='{receipt_key}']", timeout=15000)
            fixture_btn.tap()
            page.wait_for_selector("#rx-detail-inline:not(.hidden)", timeout=10000)
            page.wait_for_selector("#rx-vendor-inline", timeout=10000)
            detail_text = page.locator("#rx-detail-inline").inner_text()
            if "Playwright Vendor" not in detail_text:
                raise AssertionError("Fixture receipt extraction fields not visible")
            shot("02-receipt-detail-extraction.png", page)
            steps.append("open_receipt_detail_inline")

            # Step 3: confirm receipt beside extraction
            page.locator("#rx-confirm-inline").tap()
            page.wait_for_function(
                "() => { const m = document.getElementById('rx-confirm-msg-inline'); "
                "return m && (m.innerText.includes('Confirmed') || m.innerText.includes('extraction kept')); }",
                timeout=20000,
            )
            shot("03-receipt-confirmed.png", page)
            steps.append("confirm_receipt_beside_extraction")

            # Step 4: close receipt and open nota
            page.locator("#rx-detail-close-inline").tap()
            page.wait_for_selector("#rx-detail-inline.hidden", timeout=10000)
            page.wait_for_selector(f"button[data-open='{nota_id}']", timeout=15000)
            page.locator(f"button[data-open='{nota_id}']").tap()
            page.wait_for_selector("#nd-confirm", timeout=15000)
            nota_text = page.locator("body").inner_text()
            if "PW Fixture Vendor" not in nota_text and "INV-PW-1" not in nota_text:
                raise AssertionError("Nota detail not showing fixture vendor/invoice")
            shot("04-nota-detail-extraction.png", page)
            steps.append("open_nota_detail")

            # Step 5: confirm nota beside extraction
            page.locator("#nd-confirm").tap()
            page.wait_for_function(
                "() => { const m = document.getElementById('nd-confirm-msg'); "
                "return m && m.innerText.length > 0 && !m.innerText.includes('Saving'); }",
                timeout=20000,
            )
            confirm_msg = page.locator("#nd-confirm-msg").inner_text()
            if "Saving" in confirm_msg:
                raise AssertionError("Nota confirm still saving")
            shot("05-nota-confirmed.png", page)
            steps.append("confirm_nota_beside_extraction")

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

    test_path = SCRIPTS / "tests" / "test_ggv_receipt_workflow1_20261005.py"
    spec = importlib.util.spec_from_file_location("ggv_receipt_workflow1", test_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(mod.GgvReceiptWorkflow1Tests)
    ut_result = unittest.TextTestRunner(verbosity=1).run(suite)
    tests_pass = ut_result.testsRun - len(ut_result.failures) - len(ut_result.errors) - len(ut_result.skipped)
    tests_fail = len(ut_result.failures) + len(ut_result.errors)

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
        "scripts/tests/prove_ggv_receipt_workflow1_proof_repair1_20261005.py",
    ]

    repair_payload = {
        "pack": PACK,
        "repair_of": "GGV-RECEIPT-WORKFLOW-1",
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
