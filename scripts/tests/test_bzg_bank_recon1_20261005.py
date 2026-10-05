#!/usr/bin/env python3
"""BZG-BANK-RECON-1 — deterministic bank reconciliation states on real imported txns."""
from __future__ import annotations

import re
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

from core import bzg_bank_recon1 as _recon  # noqa: E402
from core import bzg_finance_desk as _desk  # noqa: E402
from core import bzg_finance_usability_ro as _browse  # noqa: E402
from core import bzg_history_import1 as _hist  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
DASHBOARD = ROOT / "dashboards" / "bzg-finance.html"
ZAYEN = "PERS-ZAYEN"

PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
)
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"

FORBIDDEN = (
    "Reconcile</button>",
    "reconcile</button>",
    "payment.execute",
    "payment.approve",
)


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


class BzgBankReconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not LIVE_CATALOG.is_file():
            raise unittest.SkipTest("live catalog missing")

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "test.sqlite"
        shutil.copy2(LIVE_CATALOG, self.db)
        self.conn = _rw(self.db)
        _recon.apply_recon_states(self.conn, commit=True)

    def tearDown(self) -> None:
        self.conn.close()
        self.tmp.cleanup()

    def test_parsed_import_and_txn_counts(self) -> None:
        stats = _recon.import_stats(self.conn)
        self.assertEqual(stats["parsed_import_count"], 10)
        self.assertEqual(stats["transaction_count"], 1257)
        self.assertEqual(stats["import_total"], 15)
        self.assertEqual(stats["parse_exception_import_count"], 5)

    def test_state_counts_sum_to_txn_count(self) -> None:
        summary = _recon.recon_summary(self.conn)
        self.assertTrue(summary["counts_match_transactions"])
        self.assertEqual(summary["transaction_count"], 1257)
        self.assertEqual(summary["state_sum"], 1257)
        for state in _recon.STATES:
            self.assertIn(state, summary["state_counts"])

    def test_matched_reproducible(self) -> None:
        first = _recon.matched_snapshot(self.conn)
        _recon.apply_recon_states(self.conn, commit=True)
        second = _recon.matched_snapshot(self.conn)
        self.assertEqual(first, second)
        self.assertGreater(len(first), 0)

    def test_missing_months_needs_from_matt(self) -> None:
        missing = _recon.missing_statement_months(self.conn)
        self.assertGreaterEqual(len(missing), 6)
        for row in missing:
            self.assertEqual(row["status"], "NEEDS FROM MATT")
            self.assertIn(row["month"], {"2026-09", "2026-10"})
        months = {(m["account_label"], m["month"]) for m in missing}
        self.assertIn(("Mandiri-1610555335558", "2026-09"), months)
        self.assertIn(("BRI-19101003489305", "2026-10"), months)
        self.assertIn(("BNI-2177177110", "2026-09"), months)

    def test_no_manufactured_matches_beyond_deterministic(self) -> None:
        matched = self.conn.execute(
            """
            SELECT txn_id, matched_ledger_source_id, match_confidence, notes
            FROM bzg_bank_transactions
            WHERE recon_status='MATCHED'
            """
        ).fetchall()
        for row in matched:
            self.assertTrue(row["matched_ledger_source_id"])
            self.assertTrue(row["match_confidence"])
            self.assertIn(
                row["match_confidence"],
                {
                    "INTER_ACCOUNT_TRANSFER",
                    "EXACT_LEDGER_BILL",
                    "EXACT_LEDGER_AP",
                    "EXACT_LEDGER_PETTY",
                },
            )

    def test_possible_match_has_candidates_not_posted(self) -> None:
        rows = self.conn.execute(
            """
            SELECT notes FROM bzg_bank_transactions
            WHERE recon_status='POSSIBLE MATCH'
            LIMIT 20
            """
        ).fetchall()
        self.assertGreater(len(rows), 0)
        for row in rows:
            meta = _recon._decode_notes(row["notes"])
            self.assertGreaterEqual(len(meta.get("candidates") or []), 1)

    def test_bank_browse_filter_and_read_only(self) -> None:
        all_bank = _browse.list_bank(self.conn, limit=20)
        self.assertTrue(all_bank["ok"])
        self.assertEqual(all_bank["transaction_count"], 1257)
        self.assertGreater(len(all_bank["missing_statement_months"]), 0)

        matched = _browse.list_bank(self.conn, recon_status="MATCHED", limit=50)
        self.assertTrue(matched["ok"])
        for txn in matched["transactions"]:
            self.assertEqual(txn["recon_status"], "MATCHED")

        possible = _browse.list_bank(self.conn, recon_status="POSSIBLE MATCH", limit=20)
        self.assertTrue(possible["ok"])
        for txn in possible["transactions"]:
            self.assertEqual(txn["recon_status"], "POSSIBLE MATCH")
            self.assertTrue(txn.get("proposed_not_confirmed"))

        html = DASHBOARD.read_text(encoding="utf-8")
        lower = html.lower()
        for term in FORBIDDEN:
            self.assertNotIn(term.lower(), lower, f"forbidden {term}")
        self.assertIn("bank-tabs", html)
        self.assertIn("bank-tab-counts", html)
        self.assertNotIn("reconcile</button>", lower)

    def test_desk_recon_api(self) -> None:
        summary = _desk.dispatch("GET", "/api/bzg/finance/bank/recon", ZAYEN, self.conn)
        self.assertTrue(summary["ok"])
        self.assertFalse(summary["staff_ready"])
        self.assertEqual(summary["transaction_count"], 1257)
        self.assertTrue(summary["counts_match_transactions"])

    def test_protected_closes_and_petty_unchanged_on_temp_copy(self) -> None:
        live = _ro(LIVE_CATALOG)
        try:
            for cid in PROTECTED_CLOSES:
                live_row = live.execute(
                    "SELECT state, declared_cash_amount, variance_cash_amount, updated_at FROM venue_daily_closes WHERE close_id=?",
                    (cid,),
                ).fetchone()
                tmp_row = self.conn.execute(
                    "SELECT state, declared_cash_amount, variance_cash_amount, updated_at FROM venue_daily_closes WHERE close_id=?",
                    (cid,),
                ).fetchone()
                self.assertIsNotNone(live_row)
                self.assertEqual(dict(live_row), dict(tmp_row))
            petty = _hist.petty_balance(live)
            self.assertEqual(float(petty["amount_idr"]), 552700.0)
            mov = live.execute(
                "SELECT movement_id FROM bzg_ops_petty_movements WHERE movement_id=?",
                (PROTECTED_PETTY,),
            ).fetchone()
            self.assertIsNotNone(mov)
        finally:
            live.close()

    def test_live_db_mode_ro_counts_if_present(self) -> None:
        live = _ro(LIVE_CATALOG)
        try:
            stats = _recon.import_stats(live)
            self.assertEqual(stats["transaction_count"], 1257)
            self.assertEqual(stats["parsed_import_count"], 10)
        finally:
            live.close()


if __name__ == "__main__":
    unittest.main()
