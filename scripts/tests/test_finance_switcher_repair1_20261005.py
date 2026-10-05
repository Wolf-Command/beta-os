#!/usr/bin/env python3
"""FINANCE-SWITCHER-REPAIR-1 — shared Finance business switcher proving."""
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
from core.staff_access import FINANCE_EMAIL  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
RESULT_PATH = ROOT / "state" / "reliability" / "FINANCE-SWITCHER-REPAIR-1-RESULT-2026-10-05.json"

MATT = "PERS-MATT"
MATT_EMAIL = "mrwolf@wolfcommand.net"
ZAYEN = "PERS-ZAYEN"
ZAYEN_EMAIL = FINANCE_EMAIL
AMANDA = "PERS-AMANDA"
AMANDA_EMAIL = "amanda@wolfcommand.net"

GGV_ENTITY = "ENT-GGV"
AMG_ENTITY = "ENT-AMG"
BZG_ENTITY = "ENT-BZG"

PROD_PID = 1297
BETA_PORT = 8788
PACK = "FINANCE-SWITCHER-REPAIR-1"


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


class FinanceSwitcherRepair1Tests(unittest.TestCase):
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

    def test_zayen_switcher_payload_and_html(self) -> None:
        rows = self._entities(ZAYEN_EMAIL)
        self.assertEqual([r["id"] for r in rows], ["GGV", "AMG", "BZG"])
        ggv = self._row(rows, "GGV")
        amg = self._row(rows, "AMG")
        bzg = self._row(rows, "BZG")
        self.assertFalse(ggv.get("selectable"))
        self.assertEqual(ggv.get("help"), "NO ACCESS")
        self.assertNotIn("href", ggv)
        self.assertTrue(amg.get("selectable"))
        self.assertTrue(bzg.get("selectable"))
        self.assertEqual(amg.get("href"), "/amg-finance-ops")
        self.assertEqual(bzg.get("href"), "/bzg/finance")
        for row in rows:
            blob = json.dumps(row)
            self.assertNotIn("SCOPE-", blob)
            self.assertNotIn("finance.nota", blob)
        for page in ("/bzg/finance", "/amg-finance-ops"):
            status, raw, _hdr = _call(self.base, "GET", page, ZAYEN_EMAIL, accept="text/html")
            html = raw.decode("utf-8", "replace")
            self.assertEqual(status, 200)
            self.assertIn("data-wolf-finance-switcher", html)
            self.assertIn("finance-switcher.js", html)
            ggv_row = self._row(self._entities(ZAYEN_EMAIL), "GGV")
            self.assertEqual(ggv_row.get("help"), "NO ACCESS")

    def test_zayen_bzg_counts_and_amg_reads(self) -> None:
        status, raw, _hdr = _call(self.base, "GET", "/api/bzg/finance/counts", ZAYEN_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        counts = body.get("counts") or body
        self.assertEqual(int(counts.get("purchase_orders") or 0), 543)
        self.assertEqual(int(counts.get("suppliers") or 0), 103)
        self.assertEqual(int(counts.get("supplier_bills") or 0), 473)
        for path in (
            "/api/amg/finance/notas",
            "/api/amg/finance/bills",
            "/api/amg/finance/reconciliation",
        ):
            st, _raw, _h = _call(self.base, "GET", path, ZAYEN_EMAIL)
            self.assertEqual(st, 200, path)

    def test_zayen_no_cross_entity_leakage(self) -> None:
        status, raw, _hdr = _call(self.base, "GET", "/api/amg/finance/audit", ZAYEN_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        self.assertEqual(body.get("entity_id"), AMG_ENTITY)
        for ev in body.get("events") or []:
            self.assertEqual(ev.get("entity_id"), AMG_ENTITY)
        status2, raw2, _hdr2 = _call(self.base, "GET", "/api/bzg/finance/overview", ZAYEN_EMAIL)
        self.assertEqual(status2, 200)
        overview = json.loads(raw2.decode())
        self.assertEqual(overview.get("entity_id"), BZG_ENTITY)
        self.assertEqual((overview.get("active_entity") or {}).get("entity_id"), BZG_ENTITY)

    def test_zayen_ggv_clean_403(self) -> None:
        failures: list[str] = []
        for page in sorted(fin.PAGE_PATHS):
            if not page.startswith("/ggv"):
                continue
            st, raw, _hdr = _call(self.base, "GET", page, ZAYEN_EMAIL, accept="text/html")
            if st != 403:
                failures.append(f"page {page} -> {st}")
            elif b"Access denied" not in raw and b"access" not in raw.lower():
                failures.append(f"page {page} missing deny html")
        api_paths = [
            "/api/ggv/finance",
            "/api/ggv/finance/overview",
            "/api/ggv/finance/desk",
            "/api/ggv/finance/reconciliation",
            "/api/ggv/finance/audit",
            "/api/ggv/finance/notas",
            "/api/ggv/finance/bills",
        ]
        for api in api_paths:
            st, raw, _hdr = _call(self.base, "GET", api, ZAYEN_EMAIL)
            if st != 403:
                failures.append(f"api {api} -> {st}")
            else:
                body = json.loads(raw.decode())
                if body.get("error") != "forbidden":
                    failures.append(f"api {api} bad json")
        self.assertEqual(failures, [])

    def test_finance_redirect_respects_authorisation(self) -> None:
        status, _raw, hdr = _call(
            self.base, "GET", "/finance?pick=1", ZAYEN_EMAIL, accept="text/html", follow=False
        )
        self.assertEqual(status, 302)
        loc = hdr.get("location", "")
        self.assertIn(loc, ("/amg-finance-ops", "/bzg/finance"))
        status2, _raw2, hdr2 = _call(
            self.base, "GET", "/finance?entity=GGV", ZAYEN_EMAIL, accept="text/html", follow=False
        )
        self.assertEqual(status2, 302)
        loc2 = hdr2.get("location", "")
        self.assertNotIn("/ggv/finance", loc2)
        st_bzg, _rbzg, _hbzg = _call(self.base, "GET", "/bzg/finance", ZAYEN_EMAIL, accept="text/html")
        self.assertEqual(st_bzg, 200)

    def test_matt_regression(self) -> None:
        rows = self._entities(MATT_EMAIL)
        for eid in ("GGV", "AMG", "BZG"):
            self.assertTrue(self._row(rows, eid).get("selectable"))
        for page in ("/ggv/finance", "/amg-finance-ops", "/bzg/finance"):
            st, _raw, _hdr = _call(self.base, "GET", page, MATT_EMAIL, accept="text/html")
            self.assertEqual(st, 200, page)

    def test_amanda_regression(self) -> None:
        rows = self._entities(AMANDA_EMAIL)
        self.assertTrue(self._row(rows, "GGV").get("selectable"))
        self.assertFalse(self._row(rows, "AMG").get("selectable"))
        self.assertFalse(self._row(rows, "BZG").get("selectable"))
        for path in ("/amg-finance-ops", "/api/amg/finance", "/bzg/finance"):
            accept = "text/html" if not path.startswith("/api/") else "application/json"
            st, _raw, _hdr = _call(self.base, "GET", path, AMANDA_EMAIL, accept=accept)
            self.assertEqual(st, 403, path)


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


def _write_result(tests_pass: int, tests_fail: int, fail_detail: str = "") -> None:
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
            e["id"]: {
                "selectable": bool(e.get("selectable")),
                "help": e.get("help"),
            }
            for e in rows
        }
    conn.close()
    payload = {
        "pack": PACK,
        "run_id": None,
        "switcher_component": "dashboards/shared/finance-switcher.js",
        "amg_entry_choice": "injection_and_amg-finance-ops_href",
        "routes_added": ["/finance", "/api/finance/entities"],
        "test_file": "scripts/tests/test_finance_switcher_repair1_20261005.py",
        "tests_pass": tests_pass,
        "tests_fail": tests_fail,
        "fail_detail": fail_detail,
        "per_person_matrix": matrix,
        "staff_ready": False,
        "human_commissioned": False,
        "zayen_ready": False,
        "status": "IMPLEMENTATION_DONE" if tests_fail == 0 else "BLOCKED",
        "exit_code": 0 if tests_fail == 0 else 1,
        "beta_reloaded": False,
        "reload_held": True,
        "beta_listener_pid": _listener_pid(BETA_PORT),
        "prod_pid_unchanged": _listener_pid(8787) == PROD_PID,
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FinanceSwitcherRepair1Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    fail_n = len(result.failures) + len(result.errors)
    pass_n = result.testsRun - fail_n
    detail = ""
    if result.failures:
        detail += result.failures[0][1]
    if result.errors:
        detail += result.errors[0][1]
    _write_result(pass_n, fail_n, detail[:2000])
    print(f"RESULT_JSON: {RESULT_PATH.relative_to(ROOT)}")
    sys.exit(0 if fail_n == 0 else 1)
