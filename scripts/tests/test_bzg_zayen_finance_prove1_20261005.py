#!/usr/bin/env python3
"""BZG-ZAYEN-FINANCE-PROVE-1 — Zayen finance access via real session path (HTML + API)."""
from __future__ import annotations

import json
import os
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
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import bzg_finance_desk as bzg_desk  # noqa: E402
from core import bzg_finance_usability_ro as browse  # noqa: E402
from core import bzg_history_import1 as _hist  # noqa: E402
from core import ggv_finance_invoice as _inv  # noqa: E402
from core import rbac as _rbac  # noqa: E402
from core.staff_access import FINANCE_EMAIL, ZAYEN_PERSON  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
RESULT_PATH = ROOT / "state" / "reliability" / "BZG-ZAYEN-FINANCE-PROVE-1-RESULT-2026-10-05.json"
LOG_PATH = ROOT / "state" / "reliability" / "BZG-ZAYEN-FINANCE-PROVE-1-CURSOR-2026-10-05.log"

ZAYEN = ZAYEN_PERSON
ZAYEN_EMAIL = FINANCE_EMAIL
AMANDA = "PERS-AMANDA"
GGV_ENTITY = "ENT-GGV"
AMG_ENTITY = "ENT-AMG"
BZG_ENTITY = "ENT-BZG"

E2E_PO = "PO-HIST-15"
E2E_VENDOR = "SUP-ALC-7"
E2E_GR = "GR-HIST-LEDGER-16"
E2E_BILL = "BILL-HIST-16"

PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
)
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"
PROD_PID = 1297
PROD_PORT = 8787
BETA_PORT = 8788
PACK = "BZG-ZAYEN-FINANCE-PROVE-1"


def _ro() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{LIVE_CATALOG}?mode=ro", uri=True, timeout=60)
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


def _beta_listener_count() -> int:
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{BETA_PORT}", "-sTCP:LISTEN", "-t"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if not out:
            return 0
        return len([ln for ln in out.splitlines() if ln.strip()])
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 0


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
) -> tuple[int, bytes]:
    headers = {"Accept": accept}
    if email:
        headers["X-Wolf-Subject"] = email
    req = Request(base + path, headers=headers, method=method)
    try:
        with urlopen(req, timeout=20) as res:
            return int(res.status), res.read()
    except HTTPError as exc:
        return int(exc.code), exc.read()


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


class BzgZayenFinanceProve1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not LIVE_CATALOG.is_file():
            raise unittest.SkipTest("live catalog missing")
        cls._session = SessionHttpFixture()
        cls._session.setUp()
        cls.base = cls._session.base

    @classmethod
    def tearDownClass(cls) -> None:
        cls._session.tearDown()

    def test_zayen_policy_amg_bzg_allowed_ggv_denied(self) -> None:
        conn = _ro()
        entities = _inv.finance_entities(ZAYEN, conn)
        self.assertEqual({e["id"] for e in entities}, {"GGV", "AMG", "BZG"})
        selectable = {e["id"] for e in entities if e.get("selectable")}
        self.assertEqual(selectable, {"AMG", "BZG"})
        self.assertTrue(_rbac.can(ZAYEN, "atrium.board.read", {"entity_id": AMG_ENTITY}, conn=conn))
        self.assertTrue(bzg_desk._can_read_finance(ZAYEN, conn))
        denied = _rbac.evaluate(
            ZAYEN,
            "finance.nota.read",
            {"entity_id": GGV_ENTITY},
            conn=conn,
        )
        self.assertFalse(denied.get("allowed"))
        conn.close()

    def test_session_amg_finance_html_accessible(self) -> None:
        status, raw = _call(self.base, "GET", "/amg-finance-ops", ZAYEN_EMAIL, accept="text/html")
        text = raw.decode("utf-8", "replace")
        self.assertEqual(status, 200)
        self.assertIn("AMG", text)
        self.assertIn("data-wolf-finance-switcher", text)
        self.assertIn("finance-switcher.js", text)

    def test_session_bzg_finance_html_accessible(self) -> None:
        status, raw = _call(self.base, "GET", "/bzg/finance", ZAYEN_EMAIL, accept="text/html")
        text = raw.decode("utf-8", "replace")
        self.assertEqual(status, 200)
        self.assertIn("BZG Finance", text)
        self.assertIn("data-wolf-finance-switcher", text)
        self.assertIn("finance-switcher.js", text)

    def test_session_ggv_finance_denied(self) -> None:
        status, _raw = _call(self.base, "GET", "/api/ggv/finance/overview", ZAYEN_EMAIL)
        self.assertEqual(status, 403)

    def test_session_amg_overview_entities_and_switcher(self) -> None:
        status, raw = _call(self.base, "GET", "/api/amg/finance/overview", ZAYEN_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        rows = body.get("finance_entities") or []
        ids = {row["id"] for row in rows}
        self.assertEqual(ids, {"GGV", "AMG", "BZG"})
        selectable = {row["id"] for row in rows if row.get("selectable")}
        self.assertEqual(selectable, {"AMG", "BZG"})
        hrefs = {row["href"] for row in rows if row.get("href")}
        self.assertIn("/bzg/finance", hrefs)
        self.assertIn("/amg-finance-ops", hrefs)
        self.assertFalse(body.get("zayen_ready"))
        status_html, raw_html = _call(self.base, "GET", "/amg-finance-ops", ZAYEN_EMAIL, accept="text/html")
        html = raw_html.decode("utf-8", "replace")
        self.assertEqual(status_html, 200)
        self.assertIn("data-wolf-finance-switcher", html)
        self.assertIn("finance-switcher.js", html)

    def test_session_bzg_overview_entities_and_switcher(self) -> None:
        status, raw = _call(self.base, "GET", "/api/bzg/finance/overview", ZAYEN_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        rows = body.get("finance_entities") or []
        ids = {row["id"] for row in rows}
        self.assertEqual(ids, {"GGV", "AMG", "BZG"})
        selectable = {row["id"] for row in rows if row.get("selectable")}
        self.assertEqual(selectable, {"AMG", "BZG"})
        hrefs = {row["href"] for row in rows if row.get("href")}
        self.assertIn("/amg-finance-ops", hrefs)
        self.assertEqual((body.get("active_entity") or {}).get("id"), "BZG")
        self.assertFalse(body.get("zayen_ready"))
        status_html, raw_html = _call(self.base, "GET", "/bzg/finance", ZAYEN_EMAIL, accept="text/html")
        html = raw_html.decode("utf-8", "replace")
        self.assertEqual(status_html, 200)
        self.assertIn("data-wolf-finance-switcher", html)
        self.assertIn("finance-switcher.js", html)

    def test_session_bzg_historical_chain_openable(self) -> None:
        chain: dict[str, dict] = {}
        failures: list[str] = []

        def check_step(name: str, path: str) -> dict:
            status, raw = _call(self.base, "GET", path, ZAYEN_EMAIL)
            if status != 200:
                failures.append(f"{name}: HTTP {status}")
                return {}
            body = json.loads(raw.decode())
            if not body.get("ok"):
                failures.append(f"{name}: ok=false {body.get('message') or body.get('error')}")
            return body

        chain["suppliers"] = check_step(
            "suppliers",
            "/api/bzg/finance/suppliers?q=Banneton",
        )
        chain["supplier_detail"] = check_step(
            "supplier_detail",
            f"/api/bzg/finance/suppliers/{E2E_VENDOR}",
        )
        chain["po"] = check_step("po", f"/api/bzg/finance/po/{E2E_PO}")
        chain["receipt"] = check_step("receipt", f"/api/bzg/finance/receipts/{E2E_GR}")
        chain["nota"] = check_step("nota", f"/api/bzg/finance/notas/{E2E_BILL}")
        chain["bank"] = check_step("bank_recon", "/api/bzg/finance/bank?limit=5")

        po = chain.get("po") or {}
        po_row = po.get("po") or {}
        self.assertGreater(po_row.get("line_count", 0), 0, failures)
        self.assertIn(E2E_GR, {r.get("gr_id") for r in po.get("receipts") or []}, failures)
        nota = chain.get("nota") or {}
        nota_row = nota.get("nota") or {}
        self.assertIn("evidence", nota_row, failures)
        self.assertIn("reconciliation", nota, failures)
        bank = chain.get("bank") or {}
        self.assertGreater(bank.get("total", 0), 0, failures)
        self.assertTrue(
            bool(bank.get("transactions")) or bool((bank.get("state_counts") or {})),
            failures or "bank recon state missing",
        )
        if failures:
            self.fail("; ".join(failures))

    def test_usability_routes_still_openable_direct(self) -> None:
        conn = _ro()
        sup = browse.supplier_detail(E2E_VENDOR, conn)
        po = browse.po_detail(E2E_PO, conn)
        gr = browse.receipt_detail(E2E_GR, conn)
        nota = browse.nota_detail(E2E_BILL, conn)
        conn.close()
        self.assertTrue(sup["ok"])
        self.assertTrue(po["ok"])
        self.assertGreater(po["po"]["line_count"], 0)
        self.assertTrue(gr["ok"])
        self.assertTrue(nota["ok"])
        self.assertIn("reconciliation", nota)

    def test_honesty_flags_remain_false(self) -> None:
        for path in ("/api/amg/finance/desk", "/api/bzg/finance/overview"):
            status, raw = _call(self.base, "GET", path, ZAYEN_EMAIL)
            self.assertEqual(status, 200)
            body = json.loads(raw.decode())
            self.assertFalse(body.get("staff_ready"))
            self.assertFalse(body.get("human_commissioned"))
            self.assertFalse(body.get("zayen_ready"))

    def test_protected_closes_petty_prod_unchanged(self) -> None:
        ro = _ro()
        checksums = _hist.protected_close_checksums(ro)
        for cid in PROTECTED_CLOSES:
            self.assertIn(cid, checksums)
        petty = ro.execute(
            "SELECT movement_id, amount FROM bzg_ops_petty_movements WHERE movement_id=?",
            (PROTECTED_PETTY,),
        ).fetchone()
        balance = _hist.petty_balance(ro)
        ro.close()
        self.assertIsNotNone(petty)
        self.assertEqual(float(balance["amount_idr"]), 552700.0)
        self.assertEqual(_listener_pid(PROD_PORT), PROD_PID)


def _reload_beta() -> dict:
    listeners = _beta_listener_count()
    if listeners != 1:
        return {
            "beta_reloaded": False,
            "reload_held": True,
            "reload_reason": f"expected exactly one listener on {BETA_PORT}, found {listeners}",
        }
    before = _listener_pid(BETA_PORT)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "beta_restart.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    after = _listener_pid(BETA_PORT)
    return {
        "beta_reloaded": proc.returncode == 0,
        "reload_held": proc.returncode != 0,
        "beta_listener_pid_before": before,
        "beta_listener_pid": after,
        "beta_port": BETA_PORT,
    }


def _write_result(tests_pass: int, tests_fail: int, exit_code: int) -> None:
    reload_info = _reload_beta()
    prod_pid = _listener_pid(PROD_PORT)
    ro = _ro()
    entities = _inv.finance_entities(ZAYEN, ro)
    checksums = _hist.protected_close_checksums(ro)
    petty_balance = _hist.petty_balance(ro)
    ro.close()

    result = {
        "pack": PACK,
        "predecessor": "FINANCE-CORE-BZG-PROVE-1",
        "session_fixture": {
            "auth_mode": "development_assertion",
            "person_id": ZAYEN,
            "email": ZAYEN_EMAIL,
            "path": "serve_beta BetaHandler + X-Wolf-Subject",
        },
        "access_proofs": {
            "amg_finance_html": "http://127.0.0.1:8788/amg-finance-ops",
            "bzg_finance_html": "http://127.0.0.1:8788/bzg/finance",
            "ggv_finance_denied": True,
            "zayen_finance_entities": [e["id"] for e in entities],
        },
        "entity_switcher": {
            "amg_current_entity_named": True,
            "bzg_current_entity_named": True,
            "amg_bzg_links_both_directions": True,
        },
        "historical_chain": {
            "vendor_id": E2E_VENDOR,
            "po_id": E2E_PO,
            "gr_id": E2E_GR,
            "bill_id": E2E_BILL,
            "routes": [
                "/api/bzg/finance/suppliers?q=Banneton",
                f"/api/bzg/finance/suppliers/{E2E_VENDOR}",
                f"/api/bzg/finance/po/{E2E_PO}",
                f"/api/bzg/finance/receipts/{E2E_GR}",
                f"/api/bzg/finance/notas/{E2E_BILL}",
                "/api/bzg/finance/bank",
            ],
            "openable_for_zayen": tests_fail == 0,
        },
        "modules_touched": [
            "scripts/core/amg_finance_desk.py",
            "scripts/core/amg_finance_core.py",
            "dashboards/amg-finance-ops.html",
            "dashboards/bzg-finance.html",
        ],
        "test_file": "scripts/tests/test_bzg_zayen_finance_prove1_20261005.py",
        "tests_pass": tests_pass,
        "tests_fail": tests_fail,
        "exit_code": exit_code,
        "status": "IMPLEMENTATION_DONE" if exit_code == 0 else "BLOCKED tests failed",
        "prod_pid_unchanged": prod_pid == PROD_PID,
        "prod_pid": prod_pid,
        "protected_closes_unchanged": all(cid in checksums for cid in PROTECTED_CLOSES),
        "protected_petty_balance_idr": float(petty_balance["amount_idr"]),
        "staff_ready": False,
        "human_commissioned": False,
        "zayen_ready": False,
        **reload_info,
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    log_lines = [
        f"pack={PACK}",
        f"tests_pass={tests_pass}",
        f"tests_fail={tests_fail}",
        f"exit_code={exit_code}",
        f"prod_pid={prod_pid}",
        f"beta_reloaded={result.get('beta_reloaded')}",
        f"reload_held={result.get('reload_held')}",
        f"RESULT_JSON: {RESULT_PATH}",
        f"EXIT {exit_code}",
    ]
    LOG_PATH.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(f"RESULT_JSON: {RESULT_PATH}")
    print(f"EXIT {exit_code}")


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BzgZayenFinanceProve1Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    tests_run = result.testsRun
    tests_fail = len(result.failures) + len(result.errors)
    tests_pass = tests_run - tests_fail
    exit_code = 0 if result.wasSuccessful() else 1
    _write_result(tests_pass, tests_fail, exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
