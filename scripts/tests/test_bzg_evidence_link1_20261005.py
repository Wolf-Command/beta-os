#!/usr/bin/env python3
"""BZG-EVIDENCE-LINK-1 — deterministic evidence linkage on real imported BZG history."""
from __future__ import annotations

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

from core import bzg_evidence_link1 as _evlink  # noqa: E402
from core import bzg_finance_usability_ro as _browse  # noqa: E402
from core import bzg_history_import1 as _hist  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
E2E_PO = "PO-HIST-389"
E2E_RECV_FILE = "recv_5495355205_AQAD3BNrGwTIOFV-.jpg"

PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
)
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def _rw(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=60)
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


class BzgEvidenceLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not LIVE_CATALOG.is_file():
            raise unittest.SkipTest("live catalog missing")

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "test.sqlite"
        shutil.copy2(LIVE_CATALOG, self.db)
        self.conn = _rw(self.db)
        self.total_queue = self.conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_evidence_unlinked"
        ).fetchone()[0]
        self.before_unlinked = self.conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_evidence_unlinked WHERE migration_status='EVIDENCE UNLINKED'"
        ).fetchone()[0]
        self.before_linked = self.conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_evidence_links"
        ).fetchone()[0] if self.conn.execute(
            "SELECT name FROM sqlite_master WHERE name='bzg_ops_evidence_links'"
        ).fetchone() else 0
        _evlink.apply_evidence_links(self.conn, commit=True)

    def tearDown(self) -> None:
        self.conn.close()
        self.tmp.cleanup()

    def test_counts_before_after_mode_ro(self) -> None:
        after_unlinked = self.conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_evidence_unlinked WHERE migration_status='EVIDENCE UNLINKED'"
        ).fetchone()[0]
        linked = self.conn.execute("SELECT COUNT(*) FROM bzg_ops_evidence_links").fetchone()[0]
        recon = self.conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_evidence_unlinked WHERE migration_status='NEEDS RECONCILIATION'"
        ).fetchone()[0]
        self.assertEqual(self.total_queue, after_unlinked + linked + recon)
        self.assertGreaterEqual(linked, self.before_linked)
        self.assertEqual(after_unlinked, self.before_unlinked - (linked - self.before_linked))

        ro = _ro(self.db)
        counts = _evlink.link_counts(ro)
        ro.close()
        self.assertEqual(counts["linked"], linked)
        self.assertEqual(counts["unlinked"], after_unlinked)

    def test_auto_link_reproducible(self) -> None:
        first = _evlink.matched_snapshot(self.conn)
        _evlink.apply_evidence_links(self.conn, commit=True)
        second = _evlink.matched_snapshot(self.conn)
        self.assertEqual(first, second)
        self.assertGreater(len(first), 0)
        for link in first:
            self.assertTrue(_evlink.reproduce_link(self.conn, link))
            self.assertIn(link["match_rule"], {
                "exact_path_ref",
                "exact_filename_ref",
                "exact_document_number",
                "exact_supplier_date_amount_unique",
            })
            self.assertEqual(link["confidence"], "HIGH")

    def test_zero_links_on_ambiguous_candidates(self) -> None:
        recon = self.conn.execute("SELECT * FROM bzg_ops_evidence_recon_queue").fetchall()
        for row in recon:
            candidates = []
            if row["candidates_json"]:
                import json

                candidates = json.loads(row["candidates_json"])
            if len(candidates) > 1:
                linked = self.conn.execute(
                    "SELECT 1 FROM bzg_ops_evidence_links WHERE file_path=?",
                    (row["file_path"],),
                ).fetchone()
                self.assertIsNone(linked, f"ambiguous file linked: {row['file_path']}")

    def test_no_row_invented(self) -> None:
        tables = [
            "bzg_ops_purchase_orders",
            "bzg_ops_supplier_bills",
            "bzg_ops_goods_receipts",
            "bzg_ops_petty_movements",
            "bzg_bank_statement_imports",
        ]
        live = _ro(LIVE_CATALOG)
        for table in tables:
            live_n = live.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
            test_n = self.conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
            self.assertEqual(live_n, test_n, table)
        live.close()

    def test_po_recv_file_linked(self) -> None:
        link = self.conn.execute(
            "SELECT * FROM bzg_ops_evidence_links WHERE record_type='purchase_order' AND record_id=?",
            (E2E_PO,),
        ).fetchone()
        self.assertIsNotNone(link)
        self.assertIn(E2E_RECV_FILE, str(link["file_path"]))
        self.assertIn(link["match_rule"], {"exact_path_ref", "exact_filename_ref"})

    def test_finance_desk_shows_linked_evidence(self) -> None:
        po = _browse.po_detail(E2E_PO, self.conn)
        self.assertTrue(po["ok"])
        self.assertTrue(po["po"]["evidence"]["linked"])
        self.assertIn(E2E_RECV_FILE, str(po["po"]["evidence"].get("evidence_ref") or ""))

    def test_unknown_nota_not_fabricated(self) -> None:
        unknown = self.conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_supplier_bills WHERE photo_object_ref='UNKNOWN'"
        ).fetchone()[0]
        linked_bills = self.conn.execute(
            """
            SELECT COUNT(*) FROM bzg_ops_supplier_bills b
            JOIN bzg_ops_evidence_links l ON l.record_type='supplier_bill' AND l.record_id=b.bill_id
            WHERE b.photo_object_ref != 'UNKNOWN'
            """
        ).fetchone()[0]
        self.assertEqual(linked_bills, self.conn.execute(
            "SELECT COUNT(*) FROM bzg_ops_evidence_links WHERE record_type='supplier_bill'"
        ).fetchone()[0])
        self.assertGreater(unknown, 0)

    def test_protected_closes_and_petty_unchanged(self) -> None:
        live = _ro(LIVE_CATALOG)
        for close_id in PROTECTED_CLOSES:
            live_row = live.execute(
                "SELECT state, declared_cash_amount FROM venue_daily_closes WHERE close_id=?",
                (close_id,),
            ).fetchone()
            test_row = self.conn.execute(
                "SELECT state, declared_cash_amount FROM venue_daily_closes WHERE close_id=?",
                (close_id,),
            ).fetchone()
            self.assertEqual(dict(live_row), dict(test_row))
        petty_live = live.execute(
            "SELECT amount FROM bzg_ops_petty_movements WHERE movement_id=?",
            (PROTECTED_PETTY,),
        ).fetchone()[0]
        petty_test = self.conn.execute(
            "SELECT amount FROM bzg_ops_petty_movements WHERE movement_id=?",
            (PROTECTED_PETTY,),
        ).fetchone()[0]
        self.assertEqual(petty_live, petty_test)
        live.close()

    def test_prod_pid_unchanged(self) -> None:
        pid = _listener_pid(8787)
        if pid is not None:
            self.assertEqual(pid, 1297)


if __name__ == "__main__":
    unittest.main()
