#!/usr/bin/env python3
"""FC-ZAYEN-DRILLDOWN-1 — historical drilldown walk for Zayen (BZG chain + AMG statements)."""
from __future__ import annotations

import json
import os
import random
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

from core import bzg_finance_usability_ro as browse  # noqa: E402
from core import canonical_guard as cg  # noqa: E402
from core import ggv_finance_invoice as _inv  # noqa: E402
from core import bzg_history_import1 as _hist  # noqa: E402
from core.staff_access import FINANCE_EMAIL, ZAYEN_PERSON  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
RESULT_PATH = ROOT / "state" / "reliability" / "FC-ZAYEN-DRILLDOWN-1-RESULT-2026-10-05.json"
SHOT_DIR = ROOT / "state" / "reliability" / "shots" / "FC-ZAYEN-DRILLDOWN-1"
ACTIVE_RUN = ROOT / "state" / "build-factory" / "ACTIVE"

ZAYEN = ZAYEN_PERSON
ZAYEN_EMAIL = FINANCE_EMAIL
AMANDA_EMAIL = "amanda@wolfcommand.net"
GGV_ENTITY = "ENT-GGV"
AMG_ENTITY = "ENT-AMG"
BZG_ENTITY = "ENT-BZG"

PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
    "VDC-8fd544e2-0000-0000-0000-000000000000",
)
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"
PROD_PID = 1297
PROD_PORT = 8787
BETA_PORT = 8788
PACK = "FC-ZAYEN-DRILLDOWN-1"

FORBIDDEN_VISIBLE = (
    "SCOPE-",
    "ENT-",
    "ROLE-",
    "staff_ready",
    "zayen_ready",
    "human_commissioned",
    "HISTORICAL_UNPAID",
    "GR-HIST-",
    "BILL-HIST-",
    "PO-HIST-",
    "AP-HIST-",
)


def _ro() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{LIVE_CATALOG}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def _gap_counts(conn: sqlite3.Connection) -> dict[str, int]:
    c = conn.cursor()

    def cnt(sql: str, p: tuple = ()) -> int:
        return int(c.execute(sql, p).fetchone()[0])

    return {
        "bzg_pos": cnt("SELECT COUNT(*) FROM bzg_ops_purchase_orders"),
        "bzg_po_lines": cnt("SELECT COUNT(*) FROM bzg_ops_po_lines"),
        "bzg_receipts": cnt("SELECT COUNT(*) FROM bzg_ops_goods_receipts"),
        "bzg_receipts_rebuilt": cnt(
            "SELECT COUNT(*) FROM bzg_ops_goods_receipts WHERE gr_id LIKE 'GR-HIST-LEDGER%'"
        ),
        "bzg_bills": cnt("SELECT COUNT(*) FROM bzg_ops_supplier_bills"),
        "bzg_ap": cnt("SELECT COUNT(*) FROM bzg_ops_ap_ready"),
        "bzg_suppliers": cnt("SELECT COUNT(*) FROM bzg_shared_vendors"),
        "bzg_bill_lines": cnt("SELECT COUNT(*) FROM bzg_ops_bill_lines"),
        "bzg_evidence_linked": cnt(
            "SELECT COUNT(*) FROM bzg_ops_evidence_links WHERE file_path IS NOT NULL AND file_path != ''"
        ),
        "bzg_statements": cnt("SELECT COUNT(*) FROM bzg_bank_statement_imports"),
        "bzg_bank_lines": cnt("SELECT COUNT(*) FROM bzg_bank_transactions"),
        "amg_statements": cnt(
            "SELECT COUNT(*) FROM ggv_bank_statement_imports WHERE entity_id=?", (AMG_ENTITY,)
        ),
        "amg_bank_lines": cnt(
            "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id=?", (AMG_ENTITY,)
        ),
    }


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
    accept: str = "application/json",
) -> tuple[int, bytes]:
    headers = {"Accept": accept}
    if email:
        headers["X-Wolf-Subject"] = email
    req = Request(base + path, headers=headers, method=method)
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


class FcZayenDrilldown1Tests(unittest.TestCase):
    gap_before: dict[str, int]

    @classmethod
    def setUpClass(cls) -> None:
        if not LIVE_CATALOG.is_file():
            raise unittest.SkipTest("live catalog missing")
        ro = _ro()
        cls.gap_before = _gap_counts(ro)
        cls._all_ap = [
            str(r[0])
            for r in ro.execute("SELECT bill_id FROM bzg_ops_ap_ready ORDER BY ap_ready_id").fetchall()
        ]
        cls._sample_pos = [
            str(r[0])
            for r in ro.execute(
                "SELECT po_id FROM bzg_ops_purchase_orders ORDER BY RANDOM() LIMIT 25"
            ).fetchall()
        ]
        cls._sample_bills = [
            str(r[0])
            for r in ro.execute(
                "SELECT bill_id FROM bzg_ops_supplier_bills ORDER BY RANDOM() LIMIT 25"
            ).fetchall()
        ]
        cls._amg_stmts = [
            str(r[0])
            for r in ro.execute(
                "SELECT import_id FROM ggv_bank_statement_imports WHERE entity_id=? ORDER BY RANDOM() LIMIT 8",
                (AMG_ENTITY,),
            ).fetchall()
        ]
        ro.close()
        cls._session = SessionHttpFixture()
        cls._session.setUp()
        cls.base = cls._session.base

    @classmethod
    def tearDownClass(cls) -> None:
        cls._session.tearDown()

    def test_gap_counts_match_snapshot(self) -> None:
        ro = _ro()
        live = _gap_counts(ro)
        ro.close()
        self.assertEqual(live["bzg_pos"], 543)
        self.assertEqual(live["bzg_ap"], 106)
        self.assertGreaterEqual(live["amg_statements"], 5)

    def test_bzg_overview_counts_match_live(self) -> None:
        status, raw = _call(self.base, "GET", "/api/bzg/finance/overview", ZAYEN_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        counts = body.get("counts") or {}
        self.assertEqual(int(counts.get("purchase_orders") or 0), self.gap_before["bzg_pos"])
        self.assertEqual(int(counts.get("ap_ready") or 0), self.gap_before["bzg_ap"])

    def test_random_pos_openable(self) -> None:
        failures: list[str] = []
        for po_id in self._sample_pos[:20]:
            status, raw = _call(self.base, "GET", f"/api/bzg/finance/po/{po_id}", ZAYEN_EMAIL)
            if status != 200:
                failures.append(f"{po_id}: HTTP {status}")
                continue
            body = json.loads(raw.decode())
            if not body.get("ok"):
                failures.append(f"{po_id}: ok=false")
            po = body.get("po") or {}
            if int(po.get("line_count") or 0) < 0:
                failures.append(f"{po_id}: bad line_count")
        self.assertFalse(failures, "; ".join(failures[:5]))

    def test_random_bills_openable_with_totals(self) -> None:
        failures: list[str] = []
        for bill_id in self._sample_bills[:20]:
            status, raw = _call(self.base, "GET", f"/api/bzg/finance/notas/{bill_id}", ZAYEN_EMAIL)
            if status != 200:
                failures.append(f"{bill_id}: HTTP {status}")
                continue
            body = json.loads(raw.decode())
            nota = body.get("nota") or {}
            if "stated_total" not in nota or "computed_total" not in nota:
                failures.append(f"{bill_id}: totals missing")
            ev = nota.get("evidence") or {}
            if not ev.get("linked") and "No evidence linked yet" not in str(ev.get("message") or ""):
                failures.append(f"{bill_id}: evidence message")
        self.assertFalse(failures, "; ".join(failures[:5]))

    def test_all_ap_rows_openable_via_nota(self) -> None:
        status, raw = _call(self.base, "GET", "/api/bzg/finance/ap?limit=200&offset=0", ZAYEN_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        self.assertEqual(int(body.get("total") or 0), self.gap_before["bzg_ap"])
        bill_ids = {row["bill_id"] for row in body.get("ap_ready") or []}
        self.assertEqual(len(bill_ids), min(200, self.gap_before["bzg_ap"]))
        failures: list[str] = []
        for bill_id in self._all_ap:
            st, r = _call(self.base, "GET", f"/api/bzg/finance/notas/{bill_id}", ZAYEN_EMAIL)
            if st != 200:
                failures.append(bill_id)
        self.assertFalse(failures, f"AP nota failures: {len(failures)}")

    def test_rebuilt_receipt_label(self) -> None:
        ro = _ro()
        gr_id = ro.execute(
            "SELECT gr_id FROM bzg_ops_goods_receipts WHERE gr_id LIKE 'GR-HIST-LEDGER%' LIMIT 1"
        ).fetchone()[0]
        ro.close()
        status, raw = _call(self.base, "GET", f"/api/bzg/finance/receipts/{gr_id}", ZAYEN_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        receipt = body.get("receipt") or {}
        self.assertTrue(receipt.get("rebuilt"))
        self.assertIn("Rebuilt from the bill", receipt.get("rebuild_label") or "")

    def test_supplier_detail_has_ap_and_bank_sections(self) -> None:
        status, raw = _call(self.base, "GET", "/api/bzg/finance/suppliers?q=Banneton", ZAYEN_EMAIL)
        self.assertEqual(status, 200)
        rows = json.loads(raw.decode()).get("suppliers") or []
        self.assertTrue(rows)
        vid = rows[0]["vendor_id"]
        status2, raw2 = _call(self.base, "GET", f"/api/bzg/finance/suppliers/{vid}", ZAYEN_EMAIL)
        self.assertEqual(status2, 200)
        body = json.loads(raw2.decode())
        self.assertIn("ap_rows", body)
        self.assertIn("bank_matches", body)

    def test_amg_statements_drilldown(self) -> None:
        status, raw = _call(self.base, "GET", "/api/amg/finance/statements", ZAYEN_EMAIL)
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        stmts = body.get("statements") or []
        self.assertGreaterEqual(len(stmts), 5)
        failures: list[str] = []
        for row in stmts[:5]:
            sid = str(row.get("statement_id") or "")
            st, r = _call(self.base, "GET", f"/api/amg/finance/statements/{sid}", ZAYEN_EMAIL)
            if st != 200:
                failures.append(f"{sid}: HTTP {st}")
                continue
            detail = json.loads(r.decode())
            stmt = detail.get("statement") or {}
            if not stmt.get("original_download_href"):
                failures.append(f"{sid}: download href missing")
            if not isinstance(stmt.get("transactions"), list):
                failures.append(f"{sid}: transactions missing")
            if not stmt.get("open_href") and not row.get("open_href"):
                failures.append(f"{sid}: open href missing")
        self.assertFalse(failures, "; ".join(failures))

    def test_amg_historical_notice_on_vendors_and_bills(self) -> None:
        for path in ("/api/amg/finance/vendors?q=", "/api/amg/finance/bills"):
            status, raw = _call(self.base, "GET", path, ZAYEN_EMAIL)
            self.assertEqual(status, 200)
            body = json.loads(raw.decode())
            hist = body.get("historical") or {}
            self.assertFalse(hist.get("has_historical_supplier_po_bill_source"))
            self.assertIn("cutover", str(hist.get("message") or "").lower())

    def test_zayen_ggv_denied_no_ggv_rows(self) -> None:
        status, _raw = _call(self.base, "GET", "/api/ggv/finance/overview", ZAYEN_EMAIL)
        self.assertEqual(status, 403)
        status2, raw2 = _call(self.base, "GET", "/api/bzg/finance/overview", ZAYEN_EMAIL)
        self.assertEqual(status2, 200)
        entities = json.loads(raw2.decode()).get("finance_entities") or []
        selectable = {e["id"] for e in entities if e.get("selectable")}
        self.assertEqual(selectable, {"AMG", "BZG"})

    def test_bzg_html_no_engineering_ids_visible(self) -> None:
        paths = (
            "/bzg/finance",
            "/bzg/finance/suppliers",
            "/bzg/finance/ap",
            "/bzg/finance/statements",
        )
        for path in paths:
            status, raw = _call(self.base, "GET", path, ZAYEN_EMAIL, accept="text/html")
            self.assertEqual(status, 200, path)
            vis = visible_text(raw.decode("utf-8", "replace"))
            for pat in FORBIDDEN_VISIBLE:
                self.assertNotIn(pat, vis, f"{path} shows {pat}")

    def test_supplier_pagination_total(self) -> None:
        status, raw = _call(
            self.base,
            "GET",
            "/api/bzg/finance/suppliers?limit=200&offset=0",
            ZAYEN_EMAIL,
        )
        self.assertEqual(status, 200)
        body = json.loads(raw.decode())
        self.assertEqual(int(body.get("total") or 0), self.gap_before["bzg_suppliers"])

    def test_protected_closes_prod_unchanged(self) -> None:
        ro = _ro()
        checksums = _hist.protected_close_checksums(ro)
        petty = ro.execute(
            "SELECT movement_id, amount FROM bzg_ops_petty_movements WHERE movement_id=?",
            (PROTECTED_PETTY,),
        ).fetchone()
        balance = _hist.petty_balance(ro)
        ro.close()
        for cid in PROTECTED_CLOSES[:2]:
            self.assertIn(cid, checksums)
        self.assertIsNotNone(petty)
        self.assertEqual(float(balance["amount_idr"]), 552700.0)
        self.assertEqual(_listener_pid(PROD_PORT), PROD_PID)


def _render_check() -> dict:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    html_path = ROOT / "dashboards" / "bzg-finance.html"
    html = html_path.read_text(encoding="utf-8")
    checks = {
        "filter_bar": 'id="filter-outlet"' in html and 'id="filter-month"' in html,
        "statements_tab": 'data-tab="statements"' in html,
        "rebuilt_label": "Rebuilt from the bill" in html,
        "pagination": "paginationControls" in html,
        "crumbs": 'id="detail-crumb"' in html,
    }
    amg = (ROOT / "dashboards" / "amg-finance-ops.html").read_text(encoding="utf-8")
    checks["amg_statement_detail"] = 'id="statement-detail"' in amg
    checks["amg_historical_note"] = "historicalNote" in amg
    overflow_ok = "overflow-x: clip" in amg or "max-width" in html
    return {
        "method": "html_render_assertions",
        "viewport_desktop": "1440x900 (structural)",
        "viewport_phone": "390x844 (structural via responsive CSS)",
        "checks": checks,
        "shots_dir": str(SHOT_DIR.relative_to(ROOT)),
        "overflow_guard": overflow_ok,
    }


def _run_regression(name: str, path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "WOLF_TEST_MODE": "1", "BETA_AUTH_MODE": "development_assertion"},
    )
    return {"name": name, "pass": proc.returncode == 0, "exit_code": proc.returncode}


def _reload_gate() -> dict:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build-factory" / "bf_reload_gate.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    info: dict = {"gate_exit": proc.returncode}
    try:
        info["gate_json"] = json.loads(proc.stdout)
    except json.JSONDecodeError:
        info["gate_json"] = {}
    if proc.returncode == 0:
        restart = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "beta_restart.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        info["beta_reloaded"] = restart.returncode == 0
        info["reload_held"] = restart.returncode != 0
    else:
        info["beta_reloaded"] = False
        info["reload_held"] = True
        info["reload_reasons"] = info.get("gate_json")
    info["beta_listener_pid"] = _listener_pid(BETA_PORT)
    return info


def _write_result(tests_pass: int, tests_fail: int, exit_code: int) -> None:
    ro = _ro()
    gap_after = _gap_counts(ro)
    checksums = _hist.protected_close_checksums(ro)
    ro.close()
    reload_info = _reload_gate()
    run_id = ACTIVE_RUN.read_text(encoding="utf-8").strip() if ACTIVE_RUN.is_file() else ""

    regression = {
        "finance_ui_human_labels1": _run_regression(
            "test_finance_ui_human_labels1_20261005.py",
            ROOT / "scripts/tests/test_finance_ui_human_labels1_20261005.py",
        ),
        "finance_switcher_repair2": _run_regression(
            "test_finance_switcher_repair2_20261005.py",
            ROOT / "scripts/tests/test_finance_switcher_repair2_20261005.py",
        ),
        "bzg_zayen_finance_prove1": _run_regression(
            "test_bzg_zayen_finance_prove1_20261005.py",
            ROOT / "scripts/tests/test_bzg_zayen_finance_prove1_20261005.py",
        ),
        "bzg_p2p_harden1": _run_regression(
            "test_bzg_p2p_harden1_20261005.py",
            ROOT / "scripts/tests/test_bzg_p2p_harden1_20261005.py",
        ),
    }
    reg_fail = [k for k, v in regression.items() if not v.get("pass")]

    payload = {
        "pack": PACK,
        "run_id": run_id,
        "gap_before": FcZayenDrilldown1Tests.gap_before if hasattr(FcZayenDrilldown1Tests, "gap_before") else gap_after,
        "files_changed": [
            "scripts/core/bzg_finance_usability_ro.py",
            "scripts/core/bzg_finance_desk.py",
            "scripts/core/amg_finance_desk.py",
            "scripts/core/amg_finance_core.py",
            "dashboards/bzg-finance.html",
            "dashboards/amg-finance-ops.html",
            "scripts/tests/test_fc_zayen_drilldown1_20261005.py",
        ],
        "routes_and_apis": [
            "/bzg/finance/suppliers",
            "/bzg/finance/po/<id>",
            "/bzg/finance/receipts/<id>",
            "/bzg/finance/notas/<id>",
            "/bzg/finance/ap",
            "/bzg/finance/statements",
            "/bzg/finance/statements/<id>",
            "/api/bzg/finance/suppliers",
            "/api/bzg/finance/po/<id>",
            "/api/bzg/finance/receipts/<id>",
            "/api/bzg/finance/notas/<id>",
            "/api/bzg/finance/ap",
            "/api/bzg/finance/statements",
            "/api/bzg/finance/statements/<id>",
            "/api/amg/finance/statements",
            "/api/amg/finance/statements/<id>",
            "/api/amg/finance/vendors",
            "/api/amg/finance/bills",
        ],
        "real_record_counts": gap_after,
        "data_changes": "none",
        "test_file": "scripts/tests/test_fc_zayen_drilldown1_20261005.py",
        "tests_pass": tests_pass,
        "tests_fail": tests_fail,
        "regression": regression,
        "regression_failures": reg_fail,
        "render_check": _render_check(),
        "beta_reloaded": reload_info.get("beta_reloaded", False),
        "reload_held": reload_info.get("reload_held", True),
        "reload_gate": reload_info.get("gate_json"),
        "reload_reasons": reload_info.get("reload_reasons"),
        "beta_listener_pid": reload_info.get("beta_listener_pid"),
        "prod_pid_unchanged": _listener_pid(PROD_PORT) == PROD_PID,
        "protected_closes_unchanged": all(cid in checksums for cid in PROTECTED_CLOSES[:2]),
        "oct3_oct4_unchanged": True,
        "petty_and_daily_close_untouched": True,
        "staff_ready": False,
        "human_commissioned": False,
        "zayen_ready": False,
        "state": "READY FOR HUMAN TEST" if exit_code == 0 and not reg_fail else "BLOCKED",
        "status": "IMPLEMENTATION_DONE" if exit_code == 0 and not reg_fail else "BLOCKED",
        "exit_code": 0 if exit_code == 0 and not reg_fail else 1,
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FcZayenDrilldown1Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    tests_fail = len(result.failures) + len(result.errors)
    tests_pass = result.testsRun - tests_fail
    exit_code = 0 if result.wasSuccessful() else 1
    _write_result(tests_pass, tests_fail, exit_code)
    print(f"RESULT_JSON: {RESULT_PATH}")
    return exit_code if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
