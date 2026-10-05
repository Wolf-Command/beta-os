#!/usr/bin/env python3
"""BZG-HISTORY-IMPORT-1 tests — real Alchemist rows, temp Beta catalog only."""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core import bzg_finance_desk as _bzg_fin  # noqa: E402
from core import bzg_history_import1 as _hist  # noqa: E402
from core import ggv_finance_invoice as _inv  # noqa: E402
from core import ggv_finance_nota as _ggv  # noqa: E402
from core import rbac as _rbac  # noqa: E402
from core import uma_ops_console as _ops  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
ALCHEMIST_DB = _hist.ALCHEMIST_DB

REAL_PO_ID = "15"
REAL_PO_NUM = "PR-1001"
REAL_LEDGER_ID = "16"
REAL_PETTY_ID = "1"

ZAYEN = "PERS-ZAYEN"
MATT = "PERS-MATT"
AMANDA = "PERS-AMANDA"


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
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


class BzgHistoryImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not ALCHEMIST_DB.is_file():
            raise unittest.SkipTest("Alchemist source db missing")
        src = _ro(ALCHEMIST_DB)
        cls.source_counts = _hist.source_counts(src)
        po = src.execute(
            "SELECT id, pr_num FROM pr_orders WHERE id=? AND pr_num=?",
            (int(REAL_PO_ID), REAL_PO_NUM),
        ).fetchone()
        cls.assert_real_po = po is not None
        led = src.execute("SELECT id FROM ledger WHERE id=?", (int(REAL_LEDGER_ID),)).fetchone()
        cls.assert_real_ledger = led is not None
        pet = src.execute("SELECT id FROM petty_cash WHERE id=?", (int(REAL_PETTY_ID),)).fetchone()
        cls.assert_real_petty = pet is not None
        src.close()

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "test.sqlite"
        shutil.copy2(LIVE_CATALOG, self.db)
        self.conn = sqlite3.connect(str(self.db))
        self.conn.row_factory = sqlite3.Row

    def tearDown(self) -> None:
        self.conn.close()
        self.tmp.cleanup()

    def test_source_recount_matches_register(self) -> None:
        self.assertEqual(self.source_counts["pr_orders"], 543)
        self.assertEqual(self.source_counts["pr_order_lines"], 2017)
        self.assertEqual(self.source_counts["pr_receipt_lines"], 477)
        self.assertEqual(self.source_counts["ledger"], 473)
        self.assertEqual(self.source_counts["petty_cash"], 443)
        self.assertEqual(self.source_counts["suppliers"], 103)

    def test_real_alchemist_rows_exist(self) -> None:
        self.assertTrue(self.assert_real_po, f"PR {REAL_PO_NUM} id {REAL_PO_ID}")
        self.assertTrue(self.assert_real_ledger, f"ledger id {REAL_LEDGER_ID}")
        self.assertTrue(self.assert_real_petty, f"petty id {REAL_PETTY_ID}")

    def test_import_counts_match_source_minus_skipped(self) -> None:
        before_petty = _hist.petty_balance(self.conn)
        self.assertAlmostEqual(before_petty["amount_idr"], 52700.0)

        result = _hist.run_import(self.db, source_db=ALCHEMIST_DB)
        conn = _ro(self.db)
        po_count = conn.execute("SELECT COUNT(*) FROM bzg_ops_purchase_orders").fetchone()[0]
        if po_count == 543:
            self.assertEqual(result["skipped"]["purchase_orders"], 543)
            self.assertEqual(result["imported"]["purchase_orders"], 0)
        else:
            self.assertEqual(result["imported"]["purchase_orders"], 543)
            self.assertEqual(result["imported"]["po_lines"], 2017)
            self.assertEqual(result["imported"]["gr_lines"], 477)
            self.assertEqual(result["imported"]["supplier_bills"], 473)
            self.assertEqual(result["imported"]["ap_ready"], 106)
            self.assertEqual(result["imported"]["petty_cash"], 442)
            self.assertEqual(result["skipped"]["petty_cash"], 1)

        self.assertEqual(po_count, 543)
        prov = conn.execute(
            "SELECT beta_id, source_pr_num FROM bzg_ops_history_provenance WHERE source_id=? AND record_type='purchase_order'",
            (REAL_PO_ID,),
        ).fetchone()
        self.assertIsNotNone(prov)
        self.assertEqual(prov["source_pr_num"], REAL_PO_NUM)
        conn.close()

        after_petty = _hist.petty_balance(sqlite3.connect(str(self.db)))
        self.assertAlmostEqual(after_petty["amount_idr"], 52700.0)

    def test_protected_closes_unchanged_on_live_catalog(self) -> None:
        conn = _ro(LIVE_CATALOG)
        checksums = _hist.protected_close_checksums(conn)
        conn.close()
        vdc = checksums["VDC-470e741f-d889-437a-9a40-1ec9c083fb95"]
        self.assertEqual(vdc["state"], "EXCEPTION")
        self.assertAlmostEqual(vdc["declared_cash_amount"], 3225000.0)
        self.assertAlmostEqual(vdc["variance_cash_amount"], -125000.0)
        self.assertEqual(vdc["updated_at"], "2026-10-03T13:47:39Z")

    def test_zayen_denied_ggv_finance(self) -> None:
        conn = sqlite3.connect(str(self.db))
        conn.row_factory = sqlite3.Row
        entities = _inv.finance_entities(ZAYEN, conn)
        ids = {e["id"] for e in entities}
        self.assertIn("AMG", ids)
        self.assertIn("BZG", ids)
        self.assertNotIn("GGV", ids)
        denied = _rbac.evaluate(
            ZAYEN,
            "finance.nota.read",
            {"entity_id": _ggv.ENTITY_GGV},
            conn=conn,
        )
        self.assertFalse(denied.get("allowed"))
        conn.close()

    def test_amanda_ggv_only(self) -> None:
        conn = sqlite3.connect(str(self.db))
        entities = _inv.finance_entities(AMANDA, conn)
        ids = {e["id"] for e in entities}
        self.assertEqual(ids, {"GGV"})
        conn.close()

    def test_matt_sees_three_entities(self) -> None:
        conn = sqlite3.connect(str(self.db))
        entities = _inv.finance_entities(MATT, conn)
        ids = {e["id"] for e in entities}
        self.assertTrue({"GGV", "AMG", "BZG"}.issubset(ids))
        conn.close()

    def test_amg_bzg_finance_desk_isolation(self) -> None:
        conn = sqlite3.connect(str(self.db))
        conn.row_factory = sqlite3.Row
        bzg = _bzg_fin.overview(ZAYEN, conn)
        self.assertEqual(bzg.get("active_entity", {}).get("entity_id"), "ENT-BZG")
        self.assertEqual(bzg.get("completeness", {}).get("entity_id"), "ENT-BZG")
        entities = {e["id"] for e in bzg.get("finance_entities") or []}
        self.assertIn("AMG", entities)
        self.assertIn("BZG", entities)
        self.assertNotIn("GGV", entities)
        with self.assertRaises(_bzg_fin.BzgFinanceError):
            _bzg_fin.require_board(AMANDA, conn)
        conn.close()

    def test_prod_pid_1297_on_8787(self) -> None:
        pid = _listener_pid(8787)
        self.assertEqual(pid, 1297)

    def test_linked_payment_count(self) -> None:
        result = _hist.run_import(self.db, source_db=ALCHEMIST_DB)
        self.assertGreaterEqual(result["linked"]["po_to_ledger"], 464)


if __name__ == "__main__":
    unittest.main()
