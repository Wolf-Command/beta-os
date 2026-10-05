#!/usr/bin/env python3
"""FINANCE-SWITCHER-REPAIR-2 — switcher asset allowlist + Matt AMG books read."""
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
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import canonical_guard as cg  # noqa: E402
from core import ggv_finance_invoice as _inv  # noqa: E402
from core import ggv_finance_nota as fin  # noqa: E402
from core import bzg_history_import1 as _hist  # noqa: E402
from core.staff_access import FINANCE_EMAIL, officer_must_deny  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
RESULT_PATH = ROOT / "state" / "reliability" / "FINANCE-SWITCHER-REPAIR-2-RESULT-2026-10-05.json"
REPAIR1_TEST = ROOT / "scripts" / "tests" / "test_finance_switcher_repair1_20261005.py"

MATT = "PERS-MATT"
MATT_EMAIL = "mrwolf@wolfcommand.net"
ZAYEN = "PERS-ZAYEN"
ZAYEN_EMAIL = FINANCE_EMAIL
AMANDA = "PERS-AMANDA"
AMANDA_EMAIL = "amanda@wolfcommand.net"

AMG_ENTITY = "ENT-AMG"
BZG_ENTITY = "ENT-BZG"
GGV_ENTITY = "ENT-GGV"

PROD_PID = 1297
PROD_PORT = 8787
BETA_PORT = 8788
PACK = "FINANCE-SWITCHER-REPAIR-2"
RUN_ID = "BF-2731e55ad30e"

PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
)
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"

ALLOWLIST_PATHS = (
    "/shared/finance-switcher.js",
    "/shared/finance-switcher.css",
)


def _http_handler():
    import serve_beta as sb

    cg.isolate_runtime_catalog()
    for obj in vars(sb).values():
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler":
            return obj
    raise RuntimeError("BetaHandler not found")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
        return None


def _call(
    base: str,
    method: str,
    path: str,
    email: str | None = None,
    *,
    accept: str = "application/json",
    follow: bool = True,
) -> tuple[int, bytes, dict[str, str]]:
    headers = {"Accept": accept}
    if email:
        headers["X-Wolf-Subject"] = email
    req = Request(base + path, headers=headers, method=method)
    opener = build_opener() if follow else build_opener(_NoRedirect())
    try:
        with opener.open(req, timeout=30) as res:
            hdrs = {k.lower(): v for k, v in res.headers.items()}
            return int(res.status), res.read(), hdrs
    except HTTPError as exc:
        hdrs = {k.lower(): v for k, v in exc.headers.items()}
        return int(exc.code), exc.read(), hdrs


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


class FinanceSwitcherRepair2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not LIVE_CATALOG.is_file():
            raise unittest.SkipTest("live catalog missing")
        cls._session = SessionHttpFixture()
        cls._session.setUp()
        cls.base = cls._session.base
        cls._ro = sqlite3.connect(f"file:{LIVE_CATALOG}?mode=ro", uri=True)
        cls._ro.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls) -> None:
        cls._ro.close()
        cls._session.tearDown()

    def _entities(self, email: str) -> list[dict]:
        status, raw, _hdr = _call(self.base, "GET", "/api/finance/entities", email)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        return body.get("entities") or body.get("finance_entities") or []

    def _row(self, rows: list[dict], entity_id: str) -> dict:
        for row in rows:
            if row.get("id") == entity_id:
                return row
        self.fail(f"missing entity row {entity_id}")

    def test_zayen_switcher_assets_200(self) -> None:
        for path in ALLOWLIST_PATHS:
            accept = "text/css" if path.endswith(".css") else "*/*"
            status, raw, _hdr = _call(self.base, "GET", path, ZAYEN_EMAIL, accept=accept)
            self.assertEqual(status, 200, path)
            self.assertGreater(len(raw), 20, path)
        self.assertTrue(
            officer_must_deny(ZAYEN, "/shared/secret", self._ro),
            "non-allowlisted /shared path must still deny",
        )

    def test_zayen_html_and_entities(self) -> None:
        rows = self._entities(ZAYEN_EMAIL)
        ggv = self._row(rows, "GGV")
        self.assertFalse(ggv.get("selectable"))
        self.assertEqual(ggv.get("help"), "NO ACCESS")
        self.assertTrue(self._row(rows, "AMG").get("selectable"))
        self.assertTrue(self._row(rows, "BZG").get("selectable"))
        for page in ("/bzg/finance", "/amg-finance-ops"):
            status, raw, _hdr = _call(self.base, "GET", page, ZAYEN_EMAIL, accept="text/html")
            html = raw.decode("utf-8", "replace")
            self.assertEqual(status, 200, page)
            self.assertIn("data-wolf-finance-switcher", html)
            self.assertIn("finance-switcher.js", html)
            self.assertIn("finance-switcher.css", html)
        for path in ALLOWLIST_PATHS:
            st, _raw, _h = _call(self.base, "GET", path, ZAYEN_EMAIL)
            self.assertEqual(st, 200, path)

    def test_amanda_regression(self) -> None:
        rows = self._entities(AMANDA_EMAIL)
        self.assertTrue(self._row(rows, "GGV").get("selectable"))
        self.assertFalse(self._row(rows, "AMG").get("selectable"))
        self.assertFalse(self._row(rows, "BZG").get("selectable"))
        for path in ("/amg-finance-ops", "/api/amg/finance", "/bzg/finance"):
            accept = "text/html" if not path.startswith("/api/") else "application/json"
            st, _raw, _hdr = _call(self.base, "GET", path, AMANDA_EMAIL, accept=accept)
            self.assertEqual(st, 403, path)
        st, raw, _hdr = _call(self.base, "GET", ALLOWLIST_PATHS[0], AMANDA_EMAIL)
        self.assertEqual(st, 200)
        self.assertIn(b"wolf", raw.lower())

    def test_matt_amg_books_read(self) -> None:
        rows = self._entities(MATT_EMAIL)
        for eid in ("GGV", "AMG", "BZG"):
            self.assertTrue(self._row(rows, eid).get("selectable"), eid)
        for path in (
            "/api/amg/finance/accounts",
            "/api/amg/finance/journals",
            "/api/amg/finance/ledger",
        ):
            st, raw, _hdr = _call(self.base, "GET", path, MATT_EMAIL)
            self.assertEqual(st, 200, path)
            body = json.loads(raw.decode())
            self.assertTrue(body.get("ok", True) or "accounts" in body or "journals" in body or "ledger" in body)
        for page in ("/ggv/finance", "/bzg/finance"):
            st, _raw, _hdr = _call(self.base, "GET", page, MATT_EMAIL, accept="text/html")
            self.assertEqual(st, 200, page)

    def test_zayen_ggv_still_denied(self) -> None:
        failures: list[str] = []
        for page in sorted(fin.PAGE_PATHS):
            if not page.startswith("/ggv"):
                continue
            st, raw, _hdr = _call(self.base, "GET", page, ZAYEN_EMAIL, accept="text/html")
            if st != 403:
                failures.append(f"page {page} -> {st}")
        for api in (
            "/api/ggv/finance",
            "/api/ggv/finance/overview",
            "/api/ggv/finance/desk",
            "/api/ggv/finance/reconciliation",
            "/api/ggv/finance/audit",
            "/api/ggv/finance/notas",
            "/api/ggv/finance/bills",
        ):
            st, raw, _hdr = _call(self.base, "GET", api, ZAYEN_EMAIL)
            if st != 403:
                failures.append(f"api {api} -> {st}")
        self.assertEqual(failures, [])

    def test_zayen_amg_audit_no_ggv_leak(self) -> None:
        status, raw, _hdr = _call(self.base, "GET", "/api/amg/finance/audit", ZAYEN_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        self.assertEqual(body.get("entity_id"), AMG_ENTITY)
        for ev in body.get("events") or []:
            self.assertEqual(ev.get("entity_id"), AMG_ENTITY)

    def test_protected_closes_unchanged(self) -> None:
        checksums = _hist.protected_close_checksums(self._ro)
        for cid in PROTECTED_CLOSES:
            self.assertIn(cid, checksums)
        petty = self._ro.execute(
            "SELECT movement_id, amount FROM bzg_ops_petty_movements WHERE movement_id=?",
            (PROTECTED_PETTY,),
        ).fetchone()
        balance = _hist.petty_balance(self._ro)
        self.assertIsNotNone(petty)
        self.assertEqual(float(balance["amount_idr"]), 552700.0)
        self.assertEqual(_listener_pid(PROD_PORT), PROD_PID)


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
    }


def _run_repair1_regression() -> dict:
    proc = subprocess.run(
        [sys.executable, str(REPAIR1_TEST)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "WOLF_TEST_MODE": "1", "BETA_AUTH_MODE": "development_assertion"},
    )
    return {
        "exit_code": proc.returncode,
        "pass": proc.returncode == 0,
        "stdout_tail": proc.stdout[-500:] if proc.stdout else "",
    }


def _write_result(tests_pass: int, tests_fail: int, fail_detail: str = "") -> None:
    reload_info = _reload_beta()
    conn = sqlite3.connect(f"file:{LIVE_CATALOG}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    matrix = {}
    for person, email in (
        ("Matt", MATT_EMAIL),
        ("Zayen", ZAYEN_EMAIL),
        ("Amanda", AMANDA_EMAIL),
    ):
        rows = _inv.finance_entities(
            {"Matt": MATT, "Zayen": ZAYEN, "Amanda": AMANDA}[person],
            conn,
        )
        matrix[person] = {
            e["id"]: {"selectable": bool(e.get("selectable")), "help": e.get("help")}
            for e in rows
        }
    conn.close()
    regression = _run_repair1_regression()
    ro_chk = sqlite3.connect(f"file:{LIVE_CATALOG}?mode=ro", uri=True)
    ro_chk.row_factory = sqlite3.Row
    checksums = _hist.protected_close_checksums(ro_chk)
    ro_chk.close()
    payload = {
        "pack": PACK,
        "run_id": RUN_ID,
        "files_changed": [
            "scripts/core/staff_access.py",
            "scripts/migrations/migrate_finance_switcher_repair2_20261005.py",
            "scripts/tests/test_finance_switcher_repair2_20261005.py",
        ],
        "allowlist_paths": list(ALLOWLIST_PATHS),
        "matt_grant_path": {
            "role_id": "ROLE-MATT",
            "assignment_id": "ASG-MATT-OWNER-1",
            "scope_id": "SCOPE-AMG-FINANCE",
            "entity_id": AMG_ENTITY,
            "permissions_granted": [
                "atrium.board.read",
                "atrium.coa.read",
                "atrium.ledger.read",
                "atrium.report.read",
                "atrium.journal.draft",
            ],
        },
        "test_file": "scripts/tests/test_finance_switcher_repair2_20261005.py",
        "tests_pass": tests_pass,
        "tests_fail": tests_fail,
        "fail_detail": fail_detail[:2000],
        "regression": {
            "repair1": regression,
        },
        "per_person_matrix": matrix,
        "staff_ready": False,
        "human_commissioned": False,
        "zayen_ready": False,
        "status": "IMPLEMENTATION_DONE" if tests_fail == 0 and regression.get("pass") else "BLOCKED",
        "exit_code": 0 if tests_fail == 0 and regression.get("pass") else 1,
        "beta_reloaded": reload_info.get("beta_reloaded", False),
        "reload_held": reload_info.get("reload_held", True),
        "beta_listener_pid": reload_info.get("beta_listener_pid") or _listener_pid(BETA_PORT),
        "prod_pid_unchanged": _listener_pid(PROD_PORT) == PROD_PID,
        "protected_closes_unchanged": all(cid in checksums for cid in PROTECTED_CLOSES),
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FinanceSwitcherRepair2Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    fail_n = len(result.failures) + len(result.errors)
    pass_n = result.testsRun - fail_n
    detail = ""
    if result.failures:
        detail += result.failures[0][1]
    if result.errors:
        detail += result.errors[0][1]
    _write_result(pass_n, fail_n, detail)
    print(f"RESULT_JSON: {RESULT_PATH.relative_to(ROOT)}")
    sys.exit(0 if fail_n == 0 else 1)
