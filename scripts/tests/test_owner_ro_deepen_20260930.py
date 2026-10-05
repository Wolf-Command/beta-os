#!/usr/bin/env python3
"""Deepen tests: Trading/Fitness/Travel/Learning RO. No broker. No prod."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

CORE = Path("/Users/wolfterminal/beta-os/scripts/core")
sys.path.insert(0, str(CORE))

import owner_trading_ro as trading  # noqa: E402
import owner_fitness_ro as fitness  # noqa: E402
import owner_travel_ro as travel  # noqa: E402
import owner_learning_ro as learning  # noqa: E402


class TradingDeepenTests(unittest.TestCase):
    def test_history_cap_and_paper_excerpts(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            desk = td_path / "trading-desk"
            desk.mkdir()
            (desk / "QUANT_PROGRAM.md").write_text("# Quant\nPaper only.\n" + ("x\n" * 50), encoding="utf-8")
            (desk / "PAPER_QUANT_PRACTICE_BRIEF.md").write_text("# Practice\nExpectancy.\n", encoding="utf-8")
            journal = desk / "journal.jsonl"
            lines = [json.dumps({"id": f"j{i}", "act": "add", "ticker": f"T{i}", "side": "long", "when": f"2026-09-{i:02d}"}) for i in range(1, 6)]
            journal.write_text("\n".join(lines) + "\n", encoding="utf-8")
            holdings = td_path / "H.md"
            holdings.write_text("- BTC\n", encoding="utf-8")
            trading.TRADING_DESK = desk
            trading.JOURNAL_PATH = journal
            trading.HOLDINGS_PATH = holdings
            payload = trading.load_trading_ro()
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["journal"]["journal_rows"], 5)
            self.assertEqual(len(payload["journal"]["journal_history"]), 5)
            self.assertEqual(payload["holdings"]["holdings_status"], "PRESENT")
            self.assertIn("Paper only", payload["paper_quant"]["lock"])
            self.assertEqual(payload["paper_quant"]["quant_program"]["status"], "PRESENT")
            self.assertFalse(payload["live_broker"])
            hist = trading.load_trading_history(limit=2)
            self.assertEqual(hist["requested_limit"], 2)
            self.assertEqual(len(hist["journal"]["journal_history"]), 2)

    def test_template_holdings_still_unknown(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            desk = td_path / "d"
            desk.mkdir()
            (desk / "QUANT_PROGRAM.md").write_text("paper\n", encoding="utf-8")
            trading.TRADING_DESK = desk
            trading.JOURNAL_PATH = desk / "missing.jsonl"
            holdings = td_path / "H.md"
            holdings.write_text("Example shape:\n\n- BTC 0\n- ASX:?? 0\n", encoding="utf-8")
            trading.HOLDINGS_PATH = holdings
            payload = trading.load_trading_ro()
            self.assertEqual(payload["holdings"]["holdings_status"], "UNKNOWN")
            self.assertEqual(payload["holdings"]["holdings_count"], 0)


class FitnessDeepenTests(unittest.TestCase):
    def test_peptide_schedule_and_lifts(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            db = td_path / "s.sqlite"
            pep = td_path / "peptides.json"
            pep.write_text(json.dumps({
                "law": "Logged, not law.",
                "fresh_start": "2026-08-24",
                "compounds": [{"id": "nad", "name": "NAD+", "dose": "1ml", "when": "daily", "cycle": "12w", "route": "subcut"}],
            }), encoding="utf-8")
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE training_log (ts TEXT, date TEXT, lift TEXT, entry TEXT)")
            conn.execute("CREATE TABLE lift_sessions (date TEXT, lift_key TEXT, sets_json TEXT, progressed INTEGER, PRIMARY KEY(date,lift_key))")
            conn.execute("CREATE TABLE peptide_log (date TEXT, compound TEXT, status TEXT)")
            conn.execute("CREATE TABLE days (date TEXT, wo1_done INTEGER, wo2_done INTEGER, logged_closed INTEGER)")
            conn.execute("INSERT INTO training_log VALUES ('t','2026-09-01','squat','secret-entry-should-not-leak')")
            conn.execute("INSERT INTO lift_sessions VALUES ('2026-09-01','squat','[]',1)")
            conn.execute("INSERT INTO peptide_log VALUES ('2026-09-01','nad','done')")
            conn.execute("INSERT INTO days VALUES ('2026-09-01',1,0,1)")
            conn.commit()
            conn.close()
            fitness.DB_PATH = db
            fitness.PEPTIDES_PATH = pep
            payload = fitness.load_fitness_ro()
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["fitness_ne_hr"])
            self.assertFalse(payload["pii_in_response"])
            self.assertEqual(payload["peptide_schedule"]["status"], "PRESENT")
            self.assertEqual(payload["peptide_schedule"]["compounds"][0]["id"], "nad")
            self.assertEqual(payload["recent_workouts"][0]["lift"], "squat")
            self.assertNotIn("secret-entry", json.dumps(payload))
            self.assertEqual(payload["recent_lifts"][0]["lift_key"], "squat")
            self.assertEqual(payload["peptide_log_recent"][0]["compound"], "nad")


class TravelROTests(unittest.TestCase):
    def test_extract_tiles_no_booking(self):
        with tempfile.TemporaryDirectory() as td:
            board = Path(td) / "travel.html"
            board.write_text(
                "<html><body><h3>Europe</h3><p>Draft plan. Nobody books.</p>"
                "<a href=\"https://all.accor.com/x\">x</a>"
                "<h3>Vegas</h3><p>Idea only.</p></body></html>",
                encoding="utf-8",
            )
            travel.BOARD_PATH = board
            payload = travel.load_travel_ro()
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["live_booking"])
            self.assertEqual(len(payload["tiles"]), 2)
            self.assertEqual(payload["tiles"][0]["title"], "Europe")
            self.assertIn("accor", payload["tiles"][0]["outbound_hints"])


class LearningROTests(unittest.TestCase):
    def test_tracks_inbox_no_preview_dump(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            tracks = td_path / "tracks.json"
            inbox = td_path / "inbox.jsonl"
            tracks.write_text(json.dumps({
                "tracks": {"ttc-trading": {"id": "ttc-trading", "status": "open", "started_at": "2026-08-29", "item_ids": ["a", "b"]}}
            }), encoding="utf-8")
            inbox.write_text(
                json.dumps({"id": "ln-1", "title": "Macro", "status": "transcribed", "track": "ttc-trading", "preview": "SECRET_PREVIEW_BODY"}) + "\n",
                encoding="utf-8",
            )
            learning.STATE_DIR = td_path
            learning.TRACKS_PATH = tracks
            learning.INBOX_PATH = inbox
            learning.TRADING_DESK = td_path / "no-desk"
            payload = learning.load_learning_ro()
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["live_quant"])
            self.assertEqual(payload["tracks"]["track_count"], 1)
            self.assertEqual(payload["inbox"]["counts"]["all"], 1)
            self.assertEqual(payload["inbox"]["recent"][0]["title"], "Macro")
            self.assertNotIn("SECRET_PREVIEW_BODY", json.dumps(payload))
            self.assertEqual(payload["distinct_from"], "/intel/learning")


if __name__ == "__main__":
    unittest.main()
