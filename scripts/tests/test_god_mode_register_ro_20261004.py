"""GM-SCORE — frozen register projection tests (no live catalog)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core import god_mode_register_ro as gm


SAMPLE = {
    "frozen": True,
    "frozen_at": "2026-10-04T15:31:00+08:00",
    "denominator": 43,
    "numerator_complete": 0,
    "percent": 0.0,
    "fraction": "0/45",
    "rollup": {
        "complete": 0,
        "ready_for_human_test": 2,
        "in_progress": 10,
        "blocked_externally": 0,
        "not_started": 17,
        "discovered": 14,
    },
    "by_system": [{"system": "OWNER", "complete": 0, "total": 3}],
    "movement": {"today": 0},
    "tasks": [
        {
            "id": "GM-001",
            "task": "Sample",
            "business_system": "OWNER",
            "state": "ENGINEERING PROVED",
            "owner_worker": "Matt",
            "real_data": "YES",
            "deployed": "YES",
            "human_test": "NONE",
            "blocker": "x",
            "last_movement": "2026-10-04",
            "evidence": "/tmp/evidence.md",
        }
    ],
}


class GodModeRegisterRoTest(unittest.TestCase):
    def test_loads_headline_from_file_not_fraction(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(SAMPLE, fh)
            path = Path(fh.name)
        try:
            reg = gm.load_god_mode_register(path)
            self.assertTrue(reg["ok"])
            self.assertEqual(reg["headline"]["numerator_complete"], 0)
            self.assertEqual(reg["headline"]["denominator"], 43)
            self.assertEqual(reg["headline"]["percent"], 0.0)
            self.assertEqual(reg["headline"]["movement_today"], 0)
            self.assertEqual(reg["rollup"]["in_progress"], 10)
            self.assertEqual(reg["by_system"][0]["system"], "OWNER")
            self.assertEqual(reg["tasks"][0]["filter_bucket"], "in_progress")
        finally:
            path.unlink(missing_ok=True)

    def test_live_register_denominator_43(self) -> None:
        live = gm.register_path()
        if not live.is_file():
            self.skipTest("frozen register not on disk")
        reg = gm.load_god_mode_register(live)
        self.assertEqual(reg["headline"]["denominator"], 43)
        self.assertEqual(len(reg["tasks"]), 43)


if __name__ == "__main__":
    unittest.main()
