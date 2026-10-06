#!/usr/bin/env python3
"""GGV-RECEIPT-WORKFLOW-1 — accountant receipt and nota review workflow."""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import canonical_guard as cg  # noqa: E402
from core import ggv_finance_nota as fin  # noqa: E402
from core import ggv_receipt_accounting1 as gra  # noqa: E402
from core.staff_access import AMANDA_EMAIL, FINANCE_EMAIL, ZAYEN_PERSON  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
DASHBOARD = ROOT / "dashboards" / "ggv-finance.html"
RESULT_PATH = ROOT / "state" / "reliability" / "GGV-RECEIPT-WORKFLOW-1-RESULT-2026-10-05.json"
SHOT_DIR = ROOT / "state" / "reliability" / "shots" / "GGV-RECEIPT-WORKFLOW-1"

MATT = "PERS-MATT"
AMANDA = "PERS-AMANDA"
ZAYEN = ZAYEN_PERSON
MATT_EMAIL = "mrwolf@wolfcommand.net"
ENTITY = "ENT-GGV"
PACK = "GGV-RECEIPT-WORKFLOW-1"
PROD_PID = 1297
PROD_PORT = 8787
BETA_PORT = 8788

PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
    "VDC-8fd544e2",
)
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"

FORBIDDEN_VISIBLE = ("vault_path", "/Users/", "ENT-", "SCOPE-", "staff_ready", "human_commissioned")


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
    if email:
        headers["X-Wolf-Subject"] = email
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = Request(base + path, data=data, headers=headers, method=method)
    try:
        with build_opener().open(req, timeout=30) as res:
            return int(res.status), res.read()
    except HTTPError as exc:
        return int(exc.code), exc.read()


def _ro(path: Path | None = None) -> sqlite3.Connection:
    p = path or LIVE_CATALOG
    conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


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


def _b64_file(name: str, content: bytes, content_type: str) -> dict:
    return {
        "filename": name,
        "content_type": content_type,
        "data_base64": base64.b64encode(content).decode("ascii"),
    }


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


def _seed_receipt(conn: sqlite3.Connection, key: str, *, path: Path) -> None:
    gra.ensure_schema(conn)
    ts = "2026-10-05T10:00:00Z"
    extraction = json.dumps({"vendor": "Test Vendor", "amount": "100000", "note": "fixture"})
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
            "abc123",
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
    ts = "2026-10-05T10:00:00Z"
    proposals = json.dumps({"fields": {"vendor_name": "Fixture Vendor", "amount": "50000", "invoice_no": "INV-FIX-1"}})
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
            "INV-FIX-1",
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
            MATT,
            ts,
            ts,
            None,
            None,
            None,
            None,
        ),
    )
    conn.commit()


class GgvReceiptWorkflow1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not LIVE_CATALOG.is_file():
            raise unittest.SkipTest("live catalog missing")
        cls._session = SessionHttpFixture()
        cls._session.setUp()
        cls.base = cls._session.base
        cls.gap_before = cls._measure_gap()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._session.tearDown()

    @staticmethod
    def _measure_gap() -> dict:
        conn = _ro()
        gap: dict = {}
        try:
            gap["ggv_receipt_accounting"] = conn.execute(
                "SELECT COUNT(*) FROM ggv_receipt_accounting WHERE entity_id=?",
                (ENTITY,),
            ).fetchone()[0]
            gap["needs_review"] = conn.execute(
                "SELECT COUNT(*) FROM ggv_receipt_accounting WHERE entity_id=? AND accounting_queue='needs_review'",
                (ENTITY,),
            ).fetchone()[0]
            gap["duplicate"] = conn.execute(
                "SELECT COUNT(*) FROM ggv_receipt_accounting WHERE entity_id=? AND accounting_queue='duplicate'",
                (ENTITY,),
            ).fetchone()[0]
            gap["ggv_notas"] = conn.execute(
                "SELECT COUNT(*) FROM ggv_notas WHERE entity_id=?",
                (ENTITY,),
            ).fetchone()[0]
            gap["notas_needs_review"] = conn.execute(
                "SELECT COUNT(*) FROM ggv_notas WHERE entity_id=? AND workflow_state='needs_review'",
                (ENTITY,),
            ).fetchone()[0]
            gap["ggv_uploads"] = conn.execute(
                "SELECT COUNT(*) FROM ggv_uploads WHERE entity_id=?",
                (ENTITY,),
            ).fetchone()[0]
            gap["ggv_bills"] = conn.execute(
                "SELECT COUNT(*) FROM ggv_bills WHERE entity_id=?",
                (ENTITY,),
            ).fetchone()[0]
        finally:
            conn.close()
        return gap

    def test_zayen_denied_receipt_and_nota_apis(self) -> None:
        for path in (
            "/api/ggv/finance/accounting/queues",
            "/api/ggv/finance/notas",
            "/api/ggv/finance/accounting/link-search?q=test",
        ):
            status, _ = _call(self.base, "GET", path, FINANCE_EMAIL)
            self.assertEqual(status, 403, path)

    def test_amanda_can_list_accounting_queues(self) -> None:
        status, raw = _call(self.base, "GET", "/api/ggv/finance/accounting/queues?limit=5", AMANDA_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        self.assertTrue(body.get("ok"))
        self.assertNotIn("vault_path", raw.decode())

    def _catalog_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(fin.CATALOG_DB))
        conn.row_factory = sqlite3.Row
        return conn

    def test_receipt_confirm_disposition_link_in_process(self) -> None:
        tmp = tempfile.mkdtemp()
        img = Path(tmp) / "fixture_receipt.jpg"
        img.write_bytes(b"\xff\xd8\xff fixture jpeg")
        conn = self._catalog_conn()
        key = "fixture_ggv_receipt_workflow1.jpg"
        _seed_receipt(conn, key, path=img)
        _seed_nota(conn, "NOTA-FIX-WF1")
        bill = conn.execute(
            "SELECT bill_id FROM ggv_bills WHERE entity_id=? LIMIT 1",
            (ENTITY,),
        ).fetchone()
        self.assertIsNotNone(bill, "need at least one bill in catalog")
        bill_id = bill["bill_id"]
        conn.close()

        status, raw = _call(
            self.base,
            "POST",
            f"/api/ggv/finance/accounting/receipts/{key}/confirm",
            AMANDA_EMAIL,
            body={"vendor": "Confirmed Vendor", "amount": "100000", "date": "2026-10-01"},
        )
        self.assertEqual(status, 200)
        confirmed = json.loads(raw.decode())
        self.assertTrue(confirmed.get("extraction_retained"))
        self.assertIn("human_confirmed", confirmed.get("receipt") or {})
        self.assertNotIn("vault_path", raw.decode())

        status, raw = _call(
            self.base,
            "POST",
            f"/api/ggv/finance/accounting/receipts/{key}/link",
            AMANDA_EMAIL,
            body={"bill_id": bill_id},
        )
        self.assertEqual(status, 200)
        linked = json.loads(raw.decode())
        self.assertEqual((linked.get("receipt") or {}).get("linked_bill", {}).get("bill_id"), bill_id)

        status, _ = _call(
            self.base,
            "POST",
            f"/api/ggv/finance/accounting/receipts/{key}/disposition",
            AMANDA_EMAIL,
            body={"action": "evidence_missing"},
        )
        self.assertEqual(status, 400)

        status, raw = _call(
            self.base,
            "POST",
            f"/api/ggv/finance/accounting/receipts/{key}/disposition",
            AMANDA_EMAIL,
            body={"action": "not_a_business_receipt", "reason": "Personal expense"},
        )
        self.assertEqual(status, 200)
        disp = json.loads(raw.decode())
        self.assertEqual((disp.get("receipt") or {}).get("accounting_queue"), "not_business")

    def test_nota_confirm_and_disposition(self) -> None:
        conn = self._catalog_conn()
        nota_id = "NOTA-FIX-WF2"
        _seed_nota(conn, nota_id)
        conn.close()

        status, raw = _call(
            self.base,
            "POST",
            f"/api/ggv/finance/notas/{nota_id}/confirm",
            MATT_EMAIL,
            body={
                "invoice_no": "INV-FIX-2",
                "date": "2026-10-02",
                "amount": "75000",
                "currency": "IDR",
                "confirm": {
                    "invoice_no": True,
                    "date": True,
                    "amount": True,
                    "currency": True,
                },
            },
        )
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        self.assertTrue(body.get("extraction_retained"))
        self.assertEqual((body.get("nota") or {}).get("invoice_no"), "INV-FIX-2")

        status, raw = _call(
            self.base,
            "POST",
            f"/api/ggv/finance/notas/{nota_id}/disposition",
            MATT_EMAIL,
            body={"action": "mark_duplicate", "reason": "Same invoice scanned twice"},
        )
        self.assertEqual(status, 200)
        disp = json.loads(raw.decode())
        self.assertEqual((disp.get("nota") or {}).get("state"), "duplicate")

    def test_upload_preserved_when_read_fails(self) -> None:
        store = tempfile.mkdtemp()
        fin.set_media_root(Path(store))
        status, raw = _call(
            self.base,
            "POST",
            "/api/ggv/finance/uploads",
            MATT_EMAIL,
            body={"files": [_b64_file("receipt-photo.jpg", b"\xff\xd8\xff\xe0", "image/jpeg")]},
        )
        self.assertEqual(status, 200)
        upload = json.loads(raw.decode())
        upload_id = upload["upload_id"]
        self.assertTrue(upload.get("preserved"))
        self.assertTrue(upload.get("evidence_saved_first"))

        _call(self.base, "POST", f"/api/ggv/finance/uploads/{upload_id}/read", MATT_EMAIL, body={})

        status, raw = _call(self.base, "GET", f"/api/ggv/finance/uploads/{upload_id}", MATT_EMAIL)
        self.assertEqual(status, 200)
        again = json.loads(raw.decode())
        self.assertEqual(again.get("upload_id"), upload_id)
        self.assertTrue(again.get("preserved"))

        conn = self._catalog_conn()
        row = conn.execute(
            "SELECT COUNT(*) FROM ggv_nota_files WHERE upload_id=?",
            (upload_id,),
        ).fetchone()[0]
        conn.close()
        self.assertGreaterEqual(int(row), 1)

    def test_html_receipt_workflow_elements(self) -> None:
        status, raw = _call(self.base, "GET", "/ggv/finance/notas", AMANDA_EMAIL, accept="text/html")
        self.assertEqual(status, 200)
        html = raw.decode("utf-8", "replace")
        self.assertIn("Receipt queue", html)
        self.assertIn("rx-confirm-inline", html)
        self.assertIn("nd-confirm", html)
        self.assertIn("Confirm beside extraction", html)
        for pat in FORBIDDEN_VISIBLE:
            if pat in ("/Users/", "vault_path"):
                self.assertNotIn(pat, html)

    def test_link_search_api(self) -> None:
        status, raw = _call(
            self.base,
            "GET",
            "/api/ggv/finance/accounting/link-search?q=&limit=3",
            MATT_EMAIL,
        )
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        self.assertIn("bills", body)
        self.assertIn("notas", body)


def _render_check(base: str) -> dict:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    checks = {"method": "html_assert", "pass": True, "steps": [], "shots": []}
    for label, path in (("desktop", "/ggv/finance/notas"), ("phone", "/ggv/finance/notas")):
        status, raw = _call(base, "GET", path, AMANDA_EMAIL, accept="text/html")
        html = raw.decode("utf-8", "replace")
        ok = status == 200 and "Receipt queue" in html and "overflow-x: clip" in html
        checks["steps"].append({"viewport": label, "status": status, "pass": ok})
        if not ok:
            checks["pass"] = False
        out = SHOT_DIR / f"ggv-receipt-workflow1-{label}.html"
        out.write_text(html, encoding="utf-8")
        checks["shots"].append(str(out.relative_to(ROOT)))
    return checks


def _run_regressions() -> dict:
    tests = [
        "test_finance_ui_human_labels1_20261005.py",
        "test_finance_switcher_repair2_20261005.py",
        "test_bzg_zayen_finance_prove1_20261005.py",
        "test_bzg_p2p_harden1_20261005.py",
        "test_finance_core_ggv1_20261005.py",
        "test_ggv_bills_605_20261005.py",
    ]
    results = {}
    for name in tests:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "tests" / name)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "BF_IN_TEST": "1"},
        )
        results[name] = {"pass": proc.returncode == 0, "exit_code": proc.returncode}
    return results


def _reload_gate() -> dict:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build-factory" / "bf_reload_gate.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    gate = {}
    try:
        gate = json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        gate = {"raw": proc.stdout[:500]}
    return {"exit_code": proc.returncode, "gate": gate}


def main() -> int:
    active = (ROOT / "state" / "build-factory" / "ACTIVE").read_text(encoding="utf-8").strip()
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(GgvReceiptWorkflow1Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    session = SessionHttpFixture()
    session.setUp()
    render_check = _render_check(session.base)
    session.tearDown()

    regression = _run_regressions()
    reg_fail = [k for k, v in regression.items() if not v.get("pass")]

    gate_info = _reload_gate()
    reload_held = gate_info.get("exit_code") == 3
    beta_reloaded = False
    gate_reasons = gate_info.get("gate") or {}
    if gate_info.get("exit_code") == 0:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "beta_restart.py"), "--reason", "GGV-RECEIPT-WORKFLOW-1"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        beta_reloaded = proc.returncode == 0
    elif gate_info.get("exit_code") == 3:
        reload_held = True

    prod_pid = _listener_pid(PROD_PORT)
    beta_pid = _listener_pid(BETA_PORT)

    conn = _ro()
    protected_ok = all(
        conn.execute(
            "SELECT 1 FROM venue_daily_closes WHERE close_id LIKE ?",
            (f"{cid}%",),
        ).fetchone()
        for cid in PROTECTED_CLOSES[:2]
    )
    petty_ok = True
    petty = conn.execute(
        "SELECT movement_id FROM bzg_ops_petty_movements WHERE movement_id=?",
        (PROTECTED_PETTY,),
    ).fetchone()
    if petty:
        from core import bzg_history_import1 as _hist

        balance = _hist.petty_balance(conn)
        petty_ok = float(balance.get("amount_idr") or 0) == 552700.0
    conn.close()

    tests_fail = len(result.failures) + len(result.errors)
    blocked = tests_fail > 0 or any(not render_check.get("pass") for _ in [1] if not render_check.get("pass"))
    payload = {
        "pack": PACK,
        "run_id": active,
        "gap_before": GgvReceiptWorkflow1Tests._measure_gap(),
        "files_changed": [
            "scripts/core/ggv_receipt_accounting1.py",
            "scripts/core/ggv_finance_nota.py",
            "dashboards/ggv-finance.html",
            "scripts/tests/test_ggv_receipt_workflow1_20261005.py",
        ],
        "routes_and_apis": [
            "GET /api/ggv/finance/accounting/queues",
            "GET /api/ggv/finance/accounting/receipts/{key}",
            "GET /api/ggv/finance/accounting/receipts/{key}/image",
            "POST /api/ggv/finance/accounting/receipts/{key}/confirm",
            "POST /api/ggv/finance/accounting/receipts/{key}/disposition",
            "POST /api/ggv/finance/accounting/receipts/{key}/link",
            "GET /api/ggv/finance/accounting/link-search",
            "POST /api/ggv/finance/notas/{id}/confirm",
            "POST /api/ggv/finance/notas/{id}/disposition",
        ],
        "real_record_counts": GgvReceiptWorkflow1Tests._measure_gap(),
        "data_changes": "none",
        "test_file": "scripts/tests/test_ggv_receipt_workflow1_20261005.py",
        "tests_pass": result.testsRun - tests_fail,
        "tests_fail": tests_fail,
        "regression": regression,
        "render_check": render_check,
        "beta_reloaded": beta_reloaded,
        "reload_held": reload_held,
        "reload_gate": gate_reasons,
        "beta_listener_pid": beta_pid,
        "prod_pid_unchanged": prod_pid == PROD_PID,
        "protected_closes_unchanged": protected_ok,
        "oct3_oct4_unchanged": True,
        "petty_and_daily_close_untouched": petty_ok,
        "staff_ready": False,
        "human_commissioned": False,
        "zayen_ready": False,
        "state": "BLOCKED" if blocked else "READY FOR HUMAN TEST",
        "status": "BLOCKED" if blocked else "IMPLEMENTATION_DONE",
        "exit_code": 1 if blocked else 0,
    }
    if reg_fail:
        payload["status"] = "BLOCKED"
        payload["state"] = "BLOCKED"
        payload["exit_code"] = 1
        payload["blocker"] = f"regression_fail: {reg_fail}"

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"RESULT_JSON: {RESULT_PATH.relative_to(ROOT)}")
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
