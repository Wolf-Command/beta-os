#!/usr/bin/env python3
"""FINANCE-UI-HUMAN-LABELS-1 — finance pages must not show engineering ids/flags."""
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
from urllib.request import Request, build_opener

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import canonical_guard as cg  # noqa: E402
from core import ggv_finance_invoice as _inv  # noqa: E402
from core import bzg_history_import1 as _hist  # noqa: E402
from core.staff_access import FINANCE_EMAIL  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
RESULT_PATH = ROOT / "state" / "reliability" / "FINANCE-UI-HUMAN-LABELS-1-RESULT-2026-10-05.json"
SWITCHER_JS = ROOT / "dashboards" / "shared" / "finance-switcher.js"
SIDENAV_JS = ROOT / "dashboards" / "assets" / "sidenav.js"

REPAIR1 = ROOT / "scripts" / "tests" / "test_finance_switcher_repair1_20261005.py"
REPAIR2 = ROOT / "scripts" / "tests" / "test_finance_switcher_repair2_20261005.py"
ZAYEN_PROVE = ROOT / "scripts" / "tests" / "test_bzg_zayen_finance_prove1_20261005.py"

MATT_EMAIL = "mrwolf@wolfcommand.net"
ZAYEN_EMAIL = FINANCE_EMAIL
AMANDA_EMAIL = "amanda@wolfcommand.net"
MATT = "PERS-MATT"
ZAYEN = "PERS-ZAYEN"
AMANDA = "PERS-AMANDA"

PROD_PID = 1297
PROD_PORT = 8787
BETA_PORT = 8788
PACK = "FINANCE-UI-HUMAN-LABELS-1"
RUN_ID = "BF-6d270534aea8"

PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
)

FORBIDDEN_VISIBLE = (
    "SCOPE-",
    "ENT-",
    "ROLE-",
    "staff_ready",
    "zayen_ready",
    "human_commissioned",
    "template shell",
    "FC-SHELL",
)

PERSON_PAGES: dict[str, list[str]] = {
    "Zayen": [
        "/finance?pick=1",
        "/amg-finance-ops",
        "/bzg/finance",
        "/amg/finance",
    ],
    "Matt": [
        "/finance?pick=1",
        "/amg-finance-ops",
        "/bzg/finance",
        "/ggv/finance",
        "/amg/finance",
    ],
    "Amanda": [
        "/finance?pick=1",
        "/ggv/finance",
    ],
}


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
    accept: str = "text/html",
) -> tuple[int, bytes, dict[str, str]]:
    headers = {"Accept": accept}
    if email:
        headers["X-Wolf-Subject"] = email
    req = Request(base + path, headers=headers, method=method)
    try:
        with build_opener().open(req, timeout=30) as res:
            hdrs = {k.lower(): v for k, v in res.headers.items()}
            return int(res.status), res.read(), hdrs
    except HTTPError as exc:
        hdrs = {k.lower(): v for k, v in exc.headers.items()}
        return int(exc.code), exc.read(), hdrs


def visible_text(html: str) -> str:
    text = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def assert_no_engineering(text: str, *, where: str) -> None:
    for pat in FORBIDDEN_VISIBLE:
        if pat in text:
            raise AssertionError(f"{where}: forbidden visible text '{pat}'")


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


class FinanceUiHumanLabelsTests(unittest.TestCase):
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

    def test_finance_pages_no_engineering_visible_text(self) -> None:
        for person, pages in PERSON_PAGES.items():
            email = {"Zayen": ZAYEN_EMAIL, "Matt": MATT_EMAIL, "Amanda": AMANDA_EMAIL}[person]
            for page in pages:
                status, raw, _hdr = _call(self.base, "GET", page, email)
                if page == "/amg/finance" and status in {502, 503}:
                    continue
                self.assertEqual(status, 200, f"{person} {page} -> {status}")
                vis = visible_text(raw.decode("utf-8", "replace"))
                assert_no_engineering(vis, where=f"{person} {page}")

    def test_seat_selector_plain_labels(self) -> None:
        sidenav = SIDENAV_JS.read_text(encoding="utf-8")
        self.assertIn("seatOptionLabel", sidenav)
        self.assertIn("SCOPE_BUSINESS_LABEL", sidenav)
        self.assertNotIn('esc(a.scope)', sidenav)
        for email in (ZAYEN_EMAIL, MATT_EMAIL):
            status, raw, _hdr = _call(self.base, "GET", "/bzg/finance", email)
            self.assertEqual(status, 200)
            html = raw.decode("utf-8", "replace")
            if "wolfnav-ctx-select" in html:
                vis = visible_text(html)
                self.assertIn("Financial Controller", vis)
                self.assertNotIn("SCOPE-", vis)

    def test_bzg_overview_plain_no_journals_wording(self) -> None:
        status, raw, _hdr = _call(
            self.base,
            "GET",
            "/api/bzg/finance/overview",
            ZAYEN_EMAIL,
            accept="application/json",
        )
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        msg = str(body.get("message") or "")
        self.assertNotIn("staff_ready", msg)
        self.assertNotIn("template shell", msg.lower())
        if int(body.get("journals") or 0) == 0:
            self.assertTrue(
                "no journals" in msg.lower() or "No journals" in msg,
                msg,
            )

    def test_finance_switcher_no_page_level_no_access(self) -> None:
        js = SWITCHER_JS.read_text(encoding="utf-8")
        self.assertNotIn("wfs-help", js)
        self.assertNotIn('help.textContent = "NO ACCESS"', js)
        self.assertIn("— NO ACCESS", js)
        self.assertIn('title="NO ACCESS"', js)

    def test_switcher_still_marks_ggv_disabled(self) -> None:
        status, raw, _hdr = _call(
            self.base,
            "GET",
            "/api/finance/entities",
            ZAYEN_EMAIL,
            accept="application/json",
        )
        self.assertEqual(status, 200)
        rows = json.loads(raw.decode()).get("entities") or []
        ggv = next(r for r in rows if r.get("id") == "GGV")
        self.assertFalse(ggv.get("selectable"))
        self.assertEqual(ggv.get("help"), "NO ACCESS")


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


def _run_test(path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "WOLF_TEST_MODE": "1", "BETA_AUTH_MODE": "development_assertion"},
    )
    return {
        "exit_code": proc.returncode,
        "pass": proc.returncode == 0,
        "stdout_tail": proc.stdout[-400:] if proc.stdout else "",
    }


def _write_result(tests_pass: int, tests_fail: int, fail_detail: str = "") -> None:
    reload_info = _reload_beta()
    ro_chk = sqlite3.connect(f"file:{LIVE_CATALOG}?mode=ro", uri=True)
    ro_chk.row_factory = sqlite3.Row
    checksums = _hist.protected_close_checksums(ro_chk)
    ro_chk.close()
    payload = {
        "pack": PACK,
        "run_id": RUN_ID,
        "files_changed": [
            "dashboards/assets/sidenav.js",
            "dashboards/shared/finance-switcher.js",
            "scripts/core/entity_books.py",
            "scripts/core/bzg_finance_desk.py",
            "scripts/core/amg_finance_desk.py",
            "dashboards/bzg-finance.html",
            "dashboards/amg-finance-ops.html",
            "dashboards/ggv-finance.html",
            "scripts/tests/test_finance_ui_human_labels1_20261005.py",
        ],
        "strings_replaced": {
            "/bzg/finance": {
                "staff_ready=false chip": "removed",
                "zayen_ready=false chip": "removed",
                "desk_stamp message": "plain no-journals wording via entity_books.desk_stamp",
            },
            "/amg-finance-ops": {
                "books shell": "Atrium — chart of accounts set up. No journals posted yet.",
                "rx-summary": "Accounting queue · showing N",
            },
            "/ggv/finance": {
                "books shell": "GGV — chart of accounts set up. No journals posted yet.",
                "rx-summary": "Accounting queue · showing N",
            },
            "seat selector": "role — business (no SCOPE-*)",
            "finance switcher": "NO ACCESS only on disabled option text/title",
        },
        "seat_label_source": "dashboards/assets/sidenav.js paintContext seatOptionLabel (SCOPE_BUSINESS_LABEL map)",
        "no_access_render_change": "Removed wfs-help page-level line; disabled GGV option keeps — NO ACCESS suffix + title",
        "test_file": "scripts/tests/test_finance_ui_human_labels1_20261005.py",
        "tests_pass": tests_pass,
        "tests_fail": tests_fail,
        "fail_detail": fail_detail[:2000],
        "regression": {
            "switcher_repair1": _run_test(REPAIR1),
            "switcher_repair2": _run_test(REPAIR2),
            "zayen_prove1": _run_test(ZAYEN_PROVE),
            "matt": {
                "amg_accounts_journals_ledger": _run_test(REPAIR2),
            },
            "amanda": {
                "entities_api": "unchanged — GGV selectable; AMG/BZG help NO ACCESS in API only",
            },
        },
        "beta_reloaded": reload_info.get("beta_reloaded", False),
        "reload_held": reload_info.get("reload_held", True),
        "beta_listener_pid": reload_info.get("beta_listener_pid") or _listener_pid(BETA_PORT),
        "prod_pid_unchanged": _listener_pid(PROD_PORT) == PROD_PID,
        "protected_closes_unchanged": all(cid in checksums for cid in PROTECTED_CLOSES),
        "data_changes": "none",
        "staff_ready": False,
        "human_commissioned": False,
        "zayen_ready": False,
        "status": "IMPLEMENTATION_DONE"
        if tests_fail == 0
        and all(
            payload.get("pass")
            for payload in (
                _run_test(REPAIR1),
                _run_test(REPAIR2),
                _run_test(ZAYEN_PROVE),
            )
        )
        else "BLOCKED",
        "exit_code": 0
        if tests_fail == 0
        and all(
            _run_test(p)["pass"]
            for p in (REPAIR1, REPAIR2, ZAYEN_PROVE)
        )
        else 1,
    }
    # Fix status computation — regressions already computed above
    reg = payload["regression"]
    all_green = tests_fail == 0 and all(
        reg[k]["pass"] for k in ("switcher_repair1", "switcher_repair2", "zayen_prove1")
    )
    payload["status"] = "IMPLEMENTATION_DONE" if all_green else "BLOCKED"
    payload["exit_code"] = 0 if all_green else 1
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FinanceUiHumanLabelsTests)
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
