#!/usr/bin/env python3
"""BZG-FINANCE-USABILITY-1 — browse imported BZG history on Finance desk."""
from __future__ import annotations

import re
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core import bzg_finance_desk as _desk  # noqa: E402
from core import bzg_finance_usability_ro as _browse  # noqa: E402
from core import bzg_history_import1 as _hist  # noqa: E402
from core import rbac as _rbac  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
DASHBOARD = ROOT / "dashboards" / "bzg-finance.html"

ZAYEN = "PERS-ZAYEN"
HAIKAL = "PERS-HAIKAL"
AMANDA = "PERS-AMANDA"

E2E_PO = "PO-HIST-15"
E2E_VENDOR = "SUP-ALC-7"
E2E_GR = "GR-HIST-LEDGER-16"
E2E_BILL = "BILL-HIST-16"
E2E_SOURCE_PR = "PR-1001"

PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
)
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"

FORBIDDEN_FINANCE_ACTIONS = (
    "payment.execute",
    "payment.approve",
    "bzg.pr.payment_approve",
    "vendor.bank.change",
    "bzg.ap.mark_ready",
    "bzg.pay.",
)
CAPTAIN_GL_TERMS = (
    "Reconcile</button>",
    'id="btnReconcile"',
    ">Reconcile<",
)


def _ro(path: Path | None = None) -> sqlite3.Connection:
    p = path or LIVE_CATALOG
    conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _rw_copy() -> sqlite3.Connection:
    import shutil
    import tempfile

    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    shutil.copy2(LIVE_CATALOG, tmp.name)
    conn = sqlite3.connect(tmp.name)
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


class BzgFinanceUsabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not LIVE_CATALOG.is_file():
            raise unittest.SkipTest("live catalog missing")

    def setUp(self) -> None:
        self.conn = _rw_copy()

    def tearDown(self) -> None:
        self.conn.close()

    def test_supplier_search_returns_imported_suppliers(self) -> None:
        body = _browse.search_suppliers("Banneton", self.conn)
        self.assertTrue(body["ok"])
        names = [s["display_name"] for s in body["suppliers"]]
        self.assertTrue(any("Banneton" in n for n in names))
        detail = _browse.supplier_detail(E2E_VENDOR, self.conn)
        self.assertTrue(detail["ok"])
        self.assertEqual(detail["vendor"]["display_name"], "Banneton")
        self.assertGreater(detail["po_count"], 0)
        self.assertGreater(detail["nota_count"], 0)

    def test_end_to_end_path_real_imported_record(self) -> None:
        suppliers = _browse.search_suppliers("Banneton", self.conn)
        vendor_ids = {s["vendor_id"] for s in suppliers["suppliers"]}
        self.assertIn(E2E_VENDOR, vendor_ids)

        sup = _browse.supplier_detail(E2E_VENDOR, self.conn)
        po_ids = {p["po_id"] for p in sup["purchase_orders"]}
        self.assertIn(E2E_PO, po_ids)

        po = _browse.po_detail(E2E_PO, self.conn)
        self.assertTrue(po["ok"])
        self.assertEqual(po["reconciliation"]["source_pr_num"], E2E_SOURCE_PR)
        db_lines = self.conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_po_lines WHERE po_id=?",
            (E2E_PO,),
        ).fetchone()[0]
        self.assertEqual(po["po"]["line_count"], db_lines)
        self.assertGreater(db_lines, 0)

        gr_ids = {r["gr_id"] for r in po["receipts"]}
        self.assertIn(E2E_GR, gr_ids)
        gr = _browse.receipt_detail(E2E_GR, self.conn)
        self.assertTrue(gr["ok"])

        bill_ids = {n["bill_id"] for n in po["notas"]}
        self.assertIn(E2E_BILL, bill_ids)
        nota = _browse.nota_detail(E2E_BILL, self.conn)
        self.assertTrue(nota["ok"])
        self.assertFalse(nota["nota"]["evidence"]["linked"])
        self.assertEqual(nota["nota"]["evidence"]["message"], "no evidence linked")
        self.assertEqual(nota["nota"]["photo_object_ref"], "UNKNOWN")
        self.assertIn("migration_status", nota["reconciliation"])

    def test_desk_counts_match_live_db(self) -> None:
        ro = _ro()
        beta = _hist.beta_counts(ro)
        desk = _browse.desk_counts(ro)
        ro.close()
        c = desk["counts"]
        self.assertEqual(c["purchase_orders"], beta["bzg_ops_purchase_orders"])
        self.assertEqual(c["purchase_orders"], 543)
        self.assertEqual(c["po_lines"], 2017)
        self.assertEqual(c["supplier_bills"], 473)
        self.assertEqual(c["ap_ready"], beta["bzg_ops_ap_ready"])
        self.assertEqual(c["petty_historical"], 442)
        self.assertEqual(c["bank_transactions"], beta["bzg_bank_transactions"])

    def test_petty_and_bank_browse(self) -> None:
        petty = _browse.list_petty(self.conn, historical_only=True, limit=10)
        self.assertTrue(petty["ok"])
        self.assertGreater(petty["total"], 0)
        self.assertGreater(len(petty["movements"]), 0)

        bank = _browse.list_bank(self.conn, limit=10)
        self.assertTrue(bank["ok"])
        self.assertGreater(bank["total"], 0)
        self.assertGreater(bank["unmatched_total"], 0)
        statuses = {t["recon_status"] for t in bank["transactions"]}
        self.assertTrue(statuses.issubset({"UNMATCHED", "MATCHED"}) or "UNMATCHED" in statuses)

    def test_ap_and_exceptions_read_only(self) -> None:
        ap = _browse.list_ap(self.conn, limit=20)
        self.assertTrue(ap["ok"])
        self.assertTrue(ap["read_only"])
        self.assertGreater(ap["total"], 0)
        self.assertGreater(len(ap["ap_ready"]), 0)

        exc = _browse.list_exceptions(self.conn, limit=20)
        self.assertTrue(exc["ok"])
        self.assertTrue(exc["read_only"])
        self.assertGreater(exc["total"], 0)
        for row in exc["exceptions"]:
            self.assertEqual(row["record_type"] or "", row["record_type"])

        html = DASHBOARD.read_text(encoding="utf-8")
        lower = html.lower()
        for term in FORBIDDEN_FINANCE_ACTIONS:
            self.assertNotIn(term.lower(), lower, f"forbidden action {term} in HTML")

    def test_zayen_allowed_haikal_denied(self) -> None:
        overview = _desk.overview(ZAYEN, self.conn)
        self.assertTrue(overview["ok"])
        self.assertIn("browse_nav", overview)

        denied = _rbac.can(HAIKAL, _desk.BOARD_PERM, {"entity_id": "ENT-BZG"}, conn=self.conn)
        self.assertFalse(denied)
        with self.assertRaises(_desk.BzgFinanceError):
            _desk.require_board(HAIKAL, self.conn)

        amanda_denied = _rbac.can(AMANDA, _desk.BOARD_PERM, {"entity_id": "ENT-BZG"}, conn=self.conn)
        self.assertFalse(amanda_denied)

    def test_finance_page_not_completeness_only(self) -> None:
        html = DASHBOARD.read_text(encoding="utf-8")
        self.assertIn("/bzg/finance/suppliers", html)
        self.assertIn("/bzg/finance/petty", html)
        self.assertIn("/bzg/finance/bank", html)
        self.assertIn("/bzg/finance/ap", html)
        self.assertIn("/bzg/finance/exceptions", html)
        self.assertIn("data-tab", html)
        nav_hrefs = re.findall(r'href="/bzg/finance/[^"]+"', html)
        self.assertGreaterEqual(len(nav_hrefs), 5)

    def test_captain_pages_no_gl_terms(self) -> None:
        captain_pages = [
            ROOT / "dashboards" / "bzg-uma-blu.html",
            ROOT / "dashboards" / "bzg-uma-blu-petty.html",
        ]
        for page in captain_pages:
            if not page.is_file():
                continue
            text = page.read_text(encoding="utf-8")
            for term in CAPTAIN_GL_TERMS:
                self.assertNotIn(term, text, f"{page.name} contains {term}")
            self.assertNotIn("general ledger", text.lower())

    def test_api_dispatch_routes(self) -> None:
        qs = {"q": ["Banneton"]}
        body = _desk.dispatch("GET", "/api/bzg/finance/suppliers", ZAYEN, self.conn, qs=qs)
        self.assertTrue(body["ok"])
        po = _desk.dispatch("GET", f"/api/bzg/finance/po/{E2E_PO}", ZAYEN, self.conn)
        self.assertTrue(po["ok"])
        with self.assertRaises(_desk.BzgFinanceError):
            _desk.dispatch("POST", "/api/bzg/finance/ap", ZAYEN, self.conn)

    def test_matches_subroutes(self) -> None:
        self.assertTrue(_desk.matches("/bzg/finance/suppliers"))
        self.assertTrue(_desk.matches("/bzg/finance/po/PO-HIST-15"))
        self.assertTrue(_desk.matches("/api/bzg/finance/exceptions"))

    def test_protected_closes_unchanged_on_live(self) -> None:
        ro = _ro()
        checksums = _hist.protected_close_checksums(ro)
        vdc = checksums[PROTECTED_CLOSES[0]]
        self.assertEqual(vdc["state"], "EXCEPTION")
        self.assertAlmostEqual(vdc["declared_cash_amount"], 3225000.0)
        self.assertEqual(vdc["updated_at"], "2026-10-03T13:47:39Z")
        vdc2 = checksums[PROTECTED_CLOSES[1]]
        self.assertEqual(vdc2["state"], "DATA_CAPTURED")
        self.assertEqual(vdc2["updated_at"], "2026-10-04T13:56:05Z")
        petty = ro.execute(
            "SELECT movement_id, amount, direction FROM bzg_ops_petty_movements WHERE movement_id=?",
            (PROTECTED_PETTY,),
        ).fetchone()
        ro.close()
        self.assertIsNotNone(petty)
        self.assertEqual(petty["movement_id"], PROTECTED_PETTY)

    def test_prod_pid_1297_on_8787(self) -> None:
        pid = _listener_pid(8787)
        self.assertEqual(pid, 1297)


if __name__ == "__main__":
    unittest.main()
