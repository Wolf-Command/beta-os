#!/usr/bin/env python3
"""Cheap fail-closed tests for Trading/Fitness RO loaders. No broker. No prod."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import owner_trading_ro as trading  # noqa: E402
import owner_fitness_ro as fitness  # noqa: E402


class TradingROTests(unittest.TestCase):
    def test_missing_sot_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            os.environ["BETA_TRADING_DESK"] = str(td_path / "no-desk")
            os.environ["BETA_TRADING_JOURNAL"] = str(td_path / "no-journal.jsonl")
            os.environ["BETA_HOLDINGS_MD"] = str(td_path / "no-holdings.md")
            # reload paths via module attrs
            trading.TRADING_DESK = Path(os.environ["BETA_TRADING_DESK"])
            trading.JOURNAL_PATH = Path(os.environ["BETA_TRADING_JOURNAL"])
            trading.HOLDINGS_PATH = Path(os.environ["BETA_HOLDINGS_MD"])
            payload = trading.load_trading_ro()
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["reason"], "NO_SOT_YET")
            self.assertFalse(payload["live_broker"])
            self.assertFalse(payload["staff_ready"])
            self.assertEqual(payload["claim"], "NOT_REBUILT_PLUS_PROVEN")
            self.assertEqual(payload["holdings"]["holdings_count"], 0)

    def test_template_holdings_unknown_not_invented(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            desk = td_path / "trading-desk"
            desk.mkdir()
            (desk / "QUANT_PROGRAM.md").write_text("paper only\n", encoding="utf-8")
            journal = desk / "journal.jsonl"
            journal.write_text(
                json.dumps({"ts": "2026-09-01", "note": "paper entry"}) + "\n",
                encoding="utf-8",
            )
            holdings = td_path / "HOLDINGS-PERSONAL.md"
            holdings.write_text(
                "# Personal holdings (fill)\n\nHow to fill:\n\n"
                "Example shape:\n\n- BTC 0\n- ASX:?? 0\n\n"
                "If this list is empty, the brief will say holdings unknown.\n",
                encoding="utf-8",
            )
            trading.TRADING_DESK = desk
            trading.JOURNAL_PATH = journal
            trading.HOLDINGS_PATH = holdings
            payload = trading.load_trading_ro()
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["holdings"]["holdings_status"], "UNKNOWN")
            self.assertEqual(payload["holdings"]["holdings_count"], 0)
            self.assertEqual(payload["journal"]["journal_rows"], 1)
            self.assertFalse(payload["live_broker"])

    def test_real_holding_line_counted(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            desk = td_path / "trading-desk"
            desk.mkdir()
            trading.TRADING_DESK = desk
            trading.JOURNAL_PATH = desk / "missing.jsonl"
            holdings = td_path / "H.md"
            holdings.write_text("- ETH 1.5\n- ASX:BHP 10\n", encoding="utf-8")
            trading.HOLDINGS_PATH = holdings
            payload = trading.load_trading_ro()
            self.assertEqual(payload["holdings"]["holdings_status"], "PRESENT")
            self.assertEqual(payload["holdings"]["holdings_count"], 2)


class FitnessROTests(unittest.TestCase):
    def test_missing_db_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fitness.DB_PATH = Path(td) / "no.sqlite"
            payload = fitness.load_fitness_ro()
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["reason"], "NO_SOT_YET")
            self.assertTrue(payload["fitness_ne_hr"])
            self.assertFalse(payload["staff_ready"])
            self.assertEqual(payload["recent_workouts"], [])

    def test_ro_counts_and_recent_no_pii_fields(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "spartacus.sqlite"
            conn = sqlite3.connect(db)
            conn.executescript(
                """
                CREATE TABLE training_log (ts TEXT, date TEXT, lift TEXT, entry TEXT);
                CREATE TABLE days (
                  date TEXT PRIMARY KEY, day_num INTEGER,
                  water_ml INTEGER DEFAULT 0,
                  wo1_done INTEGER DEFAULT 0, wo1_outdoor INTEGER DEFAULT 0,
                  wo2_done INTEGER DEFAULT 0, wo2_outdoor INTEGER DEFAULT 0,
                  meditation_done INTEGER DEFAULT 0, reading_done INTEGER DEFAULT 0,
                  diet_status TEXT DEFAULT '',
                  logged_closed INTEGER DEFAULT 0, verdict TEXT DEFAULT '',
                  reset_reason TEXT DEFAULT ''
                );
                CREATE TABLE food_log (ts TEXT, item TEXT);
                INSERT INTO training_log VALUES ('2026-09-29T10:00:00','2026-09-29','squat','secret note');
                INSERT INTO training_log VALUES ('2026-09-28T10:00:00','2026-09-28','bench','other');
                INSERT INTO days (date, day_num, wo1_done, logged_closed) VALUES ('2026-09-29',1,1,1);
                INSERT INTO food_log VALUES ('t','do-not-leak');
                """
            )
            conn.commit()
            conn.close()
            fitness.DB_PATH = db
            payload = fitness.load_fitness_ro()
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["table_counts"]["training_log"], 2)
            self.assertEqual(payload["table_counts"]["food_log"], 1)
            self.assertEqual(len(payload["recent_workouts"]), 2)
            self.assertEqual(payload["recent_workouts"][0]["lift"], "squat")
            # no entry / food item fields
            for w in payload["recent_workouts"]:
                self.assertNotIn("entry", w)
            blob = json.dumps(payload)
            self.assertNotIn("secret note", blob)
            self.assertNotIn("do-not-leak", blob)
            self.assertFalse(payload["pii_in_response"])


if __name__ == "__main__":
    unittest.main()
