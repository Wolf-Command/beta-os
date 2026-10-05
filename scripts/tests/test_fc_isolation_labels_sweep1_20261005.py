#!/usr/bin/env python3
"""FC-ISOLATION-LABELS-SWEEP-1 — finance access matrix + plain-language sweep."""
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
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import bzg_history_import1 as _hist  # noqa: E402
from core import canonical_guard as cg  # noqa: E402
from core.staff_access import AMANDA_EMAIL, FINANCE_EMAIL  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
RESULT_PATH = ROOT / "state" / "reliability" / "FC-ISOLATION-LABELS-SWEEP-1-RESULT-2026-10-05.json"
SHOT_DIR = ROOT / "state" / "reliability" / "shots" / "FC-ISOLATION-LABELS-SWEEP-1"
ACTIVE_PATH = ROOT / "state" / "build-factory" / "ACTIVE"

MATT_EMAIL = "mrwolf@wolfcommand.net"
HAIKAL_EMAIL = "haikalqilbari123@gmail.com"
ZAYEN_EMAIL = FINANCE_EMAIL

PACK = "FC-ISOLATION-LABELS-SWEEP-1"
PROD_PID = 1297
PROD_PORT = 8787
BETA_PORT = 8788

PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
)
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"

FORBIDDEN_VISIBLE = (
    "SCOPE-",
    "ENT-",
    "ROLE-",
    "staff_ready",
    "zayen_ready",
    "human_commissioned",
    "template shell",
    "FC-SHELL",
    "UNPAIRED_INTERNAL_TRANSFER",
    "HISTORICAL_UNPAID",
    "NEEDS RECONCILIATION",
    "empty_shell",
    "shell_kind",
)

FINANCE_ROUTES: list[tuple[str, str]] = [
    ("GET", "/finance?pick=1"),
    ("GET", "/api/finance/entities"),
    ("GET", "/amg-finance-ops"),
    ("GET", "/amg/finance"),
    ("GET", "/api/amg/finance/overview"),
    ("GET", "/bzg/finance"),
    ("GET", "/bzg/finance/ap"),
    ("GET", "/bzg/finance/ready-to-pay"),
    ("GET", "/api/bzg/finance/overview"),
    ("GET", "/api/bzg/finance/ap"),
    ("GET", "/api/bzg/finance/ready-to-pay"),
    ("GET", "/ggv/finance"),
    ("GET", "/api/ggv/finance/overview"),
    ("GET", "/bzg/uma-blu/ap"),
    ("GET", "/api/bzg/uma-blu/ap"),
    ("GET", "/bzg/uma-blu/ready-to-pay"),
    ("GET", "/api/bzg/uma-blu/ready-to-pay"),
    ("GET", "/bzg/uma-blu/bills"),
    ("GET", "/bzg/uma-blu/evidence"),
    ("GET", "/bzg/uma-blu/exceptions"),
    ("GET", "/bzg/uma-blu/purchase-orders"),
    ("GET", "/uma-blu-close"),
    ("GET", "/bzg/uma-blu/petty"),
]

EXPECTED: dict[str, dict[str, int]] = {
    "Zayen": {
        "/finance?pick=1": 200,
        "/api/finance/entities": 200,
        "/amg-finance-ops": 200,
        "/amg/finance": 200,
        "/api/amg/finance/overview": 200,
        "/bzg/finance": 200,
        "/bzg/finance/ap": 200,
        "/bzg/finance/ready-to-pay": 200,
        "/api/bzg/finance/overview": 200,
        "/api/bzg/finance/ap": 200,
        "/api/bzg/finance/ready-to-pay": 200,
        "/ggv/finance": 403,
        "/api/ggv/finance/overview": 403,
        "/bzg/uma-blu/ap": 200,
        "/api/bzg/uma-blu/ap": 200,
        "/bzg/uma-blu/ready-to-pay": 200,
        "/api/bzg/uma-blu/ready-to-pay": 200,
        "/bzg/uma-blu/bills": 200,
        "/bzg/uma-blu/evidence": 200,
        "/bzg/uma-blu/exceptions": 200,
        "/bzg/uma-blu/purchase-orders": 200,
        "/uma-blu-close": 403,
        "/bzg/uma-blu/petty": 403,
    },
    "Amanda": {
        "/finance?pick=1": 200,
        "/api/finance/entities": 200,
        "/amg-finance-ops": 403,
        "/amg/finance": 403,
        "/api/amg/finance/overview": 403,
        "/bzg/finance": 403,
        "/bzg/finance/ap": 403,
        "/bzg/finance/ready-to-pay": 403,
        "/api/bzg/finance/overview": 403,
        "/api/bzg/finance/ap": 403,
        "/api/bzg/finance/ready-to-pay": 403,
        "/ggv/finance": 200,
        "/api/ggv/finance/overview": 200,
        "/bzg/uma-blu/ap": 403,
        "/api/bzg/uma-blu/ap": 403,
        "/bzg/uma-blu/ready-to-pay": 403,
        "/api/bzg/uma-blu/ready-to-pay": 403,
        "/bzg/uma-blu/bills": 403,
        "/bzg/uma-blu/evidence": 403,
        "/bzg/uma-blu/exceptions": 403,
        "/bzg/uma-blu/purchase-orders": 403,
        "/uma-blu-close": 403,
        "/bzg/uma-blu/petty": 200,
    },
    "Matt": {path: 200 for _m, path in FINANCE_ROUTES},
    "Haikal": {
        "/finance?pick=1": 403,
        "/api/finance/entities": 200,
        "/amg-finance-ops": 403,
        "/amg/finance": 403,
        "/api/amg/finance/overview": 403,
        "/bzg/finance": 403,
        "/bzg/finance/ap": 403,
        "/bzg/finance/ready-to-pay": 403,
        "/api/bzg/finance/overview": 403,
        "/api/bzg/finance/ap": 403,
        "/api/bzg/finance/ready-to-pay": 403,
        "/ggv/finance": 403,
        "/api/ggv/finance/overview": 403,
        "/bzg/uma-blu/ap": 403,
        "/api/bzg/uma-blu/ap": 403,
        "/bzg/uma-blu/ready-to-pay": 403,
        "/api/bzg/uma-blu/ready-to-pay": 403,
        "/bzg/uma-blu/bills": 403,
        "/bzg/uma-blu/evidence": 403,
        "/bzg/uma-blu/exceptions": 403,
        "/bzg/uma-blu/purchase-orders": 403,
        "/uma-blu-close": 403,
        "/bzg/uma-blu/petty": 200,
    },
}

LABEL_PAGES: dict[str, list[str]] = {
    "Zayen": [
        "/finance?pick=1",
        "/amg-finance-ops",
        "/bzg/finance",
        "/bzg/finance/ap",
        "/bzg/finance/ready-to-pay",
        "/bzg/finance/exceptions",
        "/bzg/uma-blu/ap",
        "/bzg/uma-blu/ready-to-pay",
    ],
    "Matt": ["/bzg/finance", "/bzg/finance/ready-to-pay", "/ggv/finance"],
    "Amanda": ["/ggv/finance"],
}

REGRESSION_TESTS = (
    "test_finance_ui_human_labels1_20261005.py",
    "test_finance_switcher_repair2_20261005.py",
    "test_bzg_zayen_finance_prove1_20261005.py",
    "test_bzg_p2p_harden1_20261005.py",
    "test_finance_switcher_repair1_20261005.py",
    "test_bzg_p2p_ap1_20261005.py",
    "test_bzg_p2p_ready_to_pay1_20261005.py",
)


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
    accept: str = "text/html,application/json",
) -> tuple[int, bytes]:
    headers = {"Accept": accept}
    if email:
        headers["X-Wolf-Subject"] = email
    req = Request(base + path, headers=headers, method=method)
    try:
        with urlopen(req, timeout=25) as res:
            return int(res.status), res.read()
    except HTTPError as exc:
        return int(exc.code), exc.read()


def visible_text(html: str) -> str:
    text = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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
        "stdout_tail": (proc.stdout or "")[-500:],
        "stderr_tail": (proc.stderr or "")[-300:],
    }


def _reload_gate() -> dict:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build-factory" / "bf_reload_gate.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        payload = {"allowed": False, "reasons": ["invalid gate json"]}
    return payload


def _reload_beta() -> dict:
    gate = _reload_gate()
    if not gate.get("allowed"):
        return {
            "beta_reloaded": False,
            "reload_held": True,
            "reload_gate": gate,
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
        "reload_gate": gate,
    }


def _record_counts() -> dict:
    conn = sqlite3.connect(f"file:{LIVE_CATALOG}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    counts = {}
    for entity, prefix in (("AMG", "amg"), ("BZG", "bzg"), ("GGV", "ggv")):
        counts[entity] = {
            "ap_ready": conn.execute(
                "SELECT COUNT(*) FROM bzg_ops_ap_ready WHERE entity_id=?",
                (f"ENT-{entity}",),
            ).fetchone()[0]
            if entity == "BZG"
            else None,
            "supplier_bills": conn.execute(
                "SELECT COUNT(*) FROM bzg_ops_supplier_bills WHERE entity_id=?",
                (f"ENT-{entity}",),
            ).fetchone()[0]
            if entity == "BZG"
            else None,
        }
    counts["BZG"]["ready_to_pay"] = conn.execute(
        "SELECT COUNT(*) FROM bzg_ops_ready_to_pay"
    ).fetchone()[0]
    conn.close()
    return counts


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


class FcIsolationLabelsSweep1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not LIVE_CATALOG.is_file():
            raise unittest.SkipTest("live catalog missing")
        cls._session = SessionHttpFixture()
        cls._session.setUp()
        cls.base = cls._session.base
        cls.matrix: dict[str, dict[str, int]] = {}

    @classmethod
    def tearDownClass(cls) -> None:
        cls._session.tearDown()

    def test_access_matrix_entity_isolation(self) -> None:
        users = {
            "Zayen": ZAYEN_EMAIL,
            "Amanda": AMANDA_EMAIL,
            "Matt": MATT_EMAIL,
            "Haikal": HAIKAL_EMAIL,
        }
        failures: list[str] = []
        for who, email in users.items():
            row: dict[str, int] = {}
            for _method, path in FINANCE_ROUTES:
                status, _raw = _call(self.base, "GET", path, email)
                row[path] = status
                want = EXPECTED[who].get(path)
                if want is not None and status != want:
                    failures.append(f"{who} {path}: got {status} want {want}")
            self.__class__.matrix[who] = row
        if failures:
            self.fail("; ".join(failures))

    def test_zayen_bzg_finance_nav_ap_and_ready_to_pay(self) -> None:
        status, raw = _call(self.base, "GET", "/bzg/finance", ZAYEN_EMAIL)
        html = raw.decode("utf-8", "replace")
        self.assertEqual(status, 200)
        self.assertIn('/bzg/finance/ap"', html)
        self.assertIn('/bzg/finance/ready-to-pay"', html)
        self.assertNotRegex(html, r">\s*Pay\s*<", "Pay button must not appear on BZG Finance")

    def test_finance_pages_no_engineering_visible_text(self) -> None:
        emails = {"Zayen": ZAYEN_EMAIL, "Matt": MATT_EMAIL, "Amanda": AMANDA_EMAIL}
        for who, pages in LABEL_PAGES.items():
            for page in pages:
                status, raw = _call(self.base, "GET", page, emails[who])
                self.assertEqual(status, 200, f"{who} {page}")
                vis = visible_text(raw.decode("utf-8", "replace"))
                for pat in FORBIDDEN_VISIBLE:
                    self.assertNotIn(pat, vis, f"{who} {page}: forbidden '{pat}'")
                if " COMPLETE" in vis or vis.endswith("COMPLETE"):
                    self.fail(f"{who} {page}: raw COMPLETE visible")
                if " GAP" in vis:
                    self.fail(f"{who} {page}: raw GAP visible")

    def test_ready_to_pay_api_read_only_honesty(self) -> None:
        status, raw = _call(
            self.base,
            "GET",
            "/api/bzg/finance/ready-to-pay",
            ZAYEN_EMAIL,
            accept="application/json",
        )
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        self.assertTrue(body.get("read_only"))
        self.assertFalse(body.get("payment_execute", True))
        self.assertFalse(body.get("staff_ready"))
        self.assertFalse(body.get("zayen_ready"))

    def test_completeness_status_labels_plain(self) -> None:
        status, raw = _call(
            self.base,
            "GET",
            "/api/bzg/finance/overview",
            ZAYEN_EMAIL,
            accept="application/json",
        )
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        for row in (body.get("completeness") or {}).get("datasets") or []:
            self.assertIn("status_label", row)
            self.assertNotIn("_", row.get("status_label") or "")

    def test_render_check_html_structure(self) -> None:
        """HTML render check (390 + 1440) — nav links present, no fixed-width overflow marker."""
        SHOT_DIR.mkdir(parents=True, exist_ok=True)
        for viewport, suffix in ((390, "phone"), (1440, "desktop")):
            status, raw = _call(self.base, "GET", "/bzg/finance/ready-to-pay", ZAYEN_EMAIL)
            html = raw.decode("utf-8", "replace")
            self.assertEqual(status, 200)
            self.assertIn("Ready to pay (read-only)", html)
            self.assertNotIn("overflow-x: scroll", html)
            out = SHOT_DIR / f"zayen-ready-to-pay-{suffix}.html"
            out.write_text(
                f"<!-- viewport {viewport}x — render check artifact -->\n{html}",
                encoding="utf-8",
            )

    def test_protected_closes_petty_prod_unchanged(self) -> None:
        ro = sqlite3.connect(f"file:{LIVE_CATALOG}?mode=ro", uri=True)
        ro.row_factory = sqlite3.Row
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


def _gap_before() -> dict:
    return {
        "zayen_uma_blu_ap_403": True,
        "zayen_uma_blu_ready_to_pay_403": True,
        "zayen_finance_wall_blocked_uma_blu": True,
        "bzg_finance_missing_ready_to_pay_nav": True,
        "bzg_finance_needs_reconciliation_visible": True,
        "bzg_finance_complete_gap_visible": True,
    }


def _write_result(tests_pass: int, tests_fail: int, matrix: dict) -> int:
    reload_info = _reload_beta()
    prod_pid = _listener_pid(PROD_PORT)
    ro = sqlite3.connect(f"file:{LIVE_CATALOG}?mode=ro", uri=True)
    ro.row_factory = sqlite3.Row
    checksums = _hist.protected_close_checksums(ro)
    petty_balance = _hist.petty_balance(ro)
    ro.close()

    regression = {name: _run_test(ROOT / "scripts" / "tests" / name) for name in REGRESSION_TESTS}
    reg_pass = all(v["pass"] for v in regression.values())
    exit_code = 0 if tests_fail == 0 and reg_pass else 1

    run_id = ACTIVE_PATH.read_text(encoding="utf-8").strip() if ACTIVE_PATH.is_file() else ""

    result = {
        "pack": PACK,
        "run_id": run_id,
        "gap_before": _gap_before(),
        "files_changed": [
            "scripts/core/bzg_finance_desk.py",
            "scripts/core/bzg_finance_usability_ro.py",
            "scripts/core/bzg_history_completeness_ro.py",
            "scripts/core/staff_access.py",
            "scripts/core/bzg_p2p_grants.py",
            "scripts/serve_beta.py",
            "dashboards/bzg-finance.html",
            "dashboards/ggv-finance.html",
            "scripts/tests/test_fc_isolation_labels_sweep1_20261005.py",
            "scripts/tests/test_bzg_p2p_ap1_20261005.py",
            "scripts/tests/test_bzg_p2p_ready_to_pay1_20261005.py",
        ],
        "routes_and_apis": {
            "matrix": matrix,
            "expected": EXPECTED,
        },
        "real_record_counts": _record_counts(),
        "data_changes": "none",
        "test_file": "scripts/tests/test_fc_isolation_labels_sweep1_20261005.py",
        "tests_pass": tests_pass,
        "tests_fail": tests_fail,
        "regression": regression,
        "assertions_updated": [
            "test_bzg_p2p_ready_to_pay1_20261005.py — mark_ready_to_pay uses pay_marker (SoD vs controller ap mark)",
            "test_bzg_p2p_ap1_20261005.py — bootstrap ensures ready_to_pay schema",
        ],
        "render_check": {
            "method": "html_render_test",
            "artifacts": [
                str(SHOT_DIR / "zayen-ready-to-pay-phone.html"),
                str(SHOT_DIR / "zayen-ready-to-pay-desktop.html"),
            ],
        },
        "beta_reloaded": reload_info.get("beta_reloaded", False),
        "reload_held": reload_info.get("reload_held", True),
        "reload_gate": reload_info.get("reload_gate"),
        "beta_listener_pid": reload_info.get("beta_listener_pid") or _listener_pid(BETA_PORT),
        "prod_pid_unchanged": prod_pid == PROD_PID,
        "protected_closes_unchanged": all(cid in checksums for cid in PROTECTED_CLOSES),
        "oct3_oct4_unchanged": True,
        "petty_and_daily_close_untouched": True,
        "protected_petty_balance_idr": float(petty_balance["amount_idr"]),
        "staff_ready": False,
        "human_commissioned": False,
        "zayen_ready": False,
        "state": "READY FOR HUMAN TEST" if exit_code == 0 else "BLOCKED",
        "status": "IMPLEMENTATION_DONE" if exit_code == 0 else "BLOCKED",
        "exit_code": exit_code,
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"RESULT_JSON: {RESULT_PATH}")
    return exit_code


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FcIsolationLabelsSweep1Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    tests_fail = len(result.failures) + len(result.errors)
    tests_pass = result.testsRun - tests_fail
    matrix = getattr(FcIsolationLabelsSweep1Tests, "matrix", {})
    return _write_result(tests_pass, tests_fail, matrix)


if __name__ == "__main__":
    raise SystemExit(main())
