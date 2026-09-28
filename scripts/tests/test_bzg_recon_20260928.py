"""Read-only checks for the 28 Sep Uma Blu / BZG reconciliation.

Does not call ESB, does not write a database, and does not open secret values.
"""
from __future__ import annotations

import re
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "wolf" / "bzg" / "UMA-BLU-BZG-RECONCILIATION.md"
ESB = Path.home() / ".openclaw" / "data" / "esb.sqlite"

REQUIRED = (
    "## ESB STATUS",
    "FOUND + USABLE",
    "FOUND NEEDS VALIDATION",
    "## Capability matrix",
    "## Canonical chain",
    "## Ops chain",
    "## Shareholder reporting",
    "## Fastest to Beta",
    "## Proposed build order",
    "## Questions only Matt can answer",
    "EXIT:0",
    "RESULT: PASS",
)

# Key names are allowed. A value after an assignment, or a bearer token, is not.
LEAK = re.compile(
    r"(password\s*=\s*\S+|bearer\s+[A-Za-z0-9._\-]{8,}|BEGIN PRIVATE)",
    re.I,
)


class ReconNote(unittest.TestCase):
    def test_required_sections(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        missing = [line for line in REQUIRED if line not in text]
        self.assertEqual(missing, [])
        self.assertIsNone(LEAK.search(text))

    def test_esb_warehouse_opens_readonly(self) -> None:
        self.assertTrue(ESB.is_file())
        conn = sqlite3.connect(f"file:{ESB}?mode=ro", uri=True)
        try:
            names = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertIn("sales", names)
            self.assertIn("goods_receipts", names)
            self.assertIn("material_usage", names)
            count = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
            self.assertIsInstance(count, int)
            self.assertGreater(count, 0)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
