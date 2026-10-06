"""PR #4 hardening (Vesper grill 2026-10-06): routing policy labelled DRAFT - NOT WIRED; cursor worker sandboxed."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from wolf_intelligence import paths, routing_policy
from wolf_intelligence.adapters import subscription_cli as sc

if paths.STATE_ROOT == paths.LIVE_STATE_ROOT or str(paths.STATE_ROOT).startswith("/Users/wolfterminal/beta-os"):
    raise RuntimeError("refusing to run tests against live Wolf Intelligence state")

CFG = Path(__file__).resolve().parents[1] / "config" / "routing-policy-real.json"


class PR4Hardening(unittest.TestCase):
    def test_routing_policy_snapshot_is_draft_not_wired(self):
        d = json.loads(CFG.read_text())
        self.assertEqual(d["label"], "DRAFT - NOT WIRED")
        self.assertEqual(d["status"], "DRAFT")
        self.assertFalse(d["wired"])
        self.assertFalse(d["active"])

    def test_learned_policy_is_draft_not_wired(self):
        real = tempfile.mkdtemp(prefix="wi-test-pr4-real-")
        self.addCleanup(shutil.rmtree, real, True)
        with mock.patch.dict(os.environ, {"WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT": real}):
            pol = routing_policy.learn()
        self.assertEqual(pol["label"], "DRAFT - NOT WIRED")
        self.assertFalse(pol["wired"])

    def test_cursor_runs_sandboxed_read_only(self):
        seen = {}

        def fake_run(argv, **_kw):
            seen["argv"] = argv
            return 0, json.dumps({"result": "ok", "is_error": False}), "", 1.0, None

        a = sc.CursorSubAdapter()
        with mock.patch.object(a, "binary", return_value="/bin/echo"), mock.patch.object(sc, "_run", side_effect=fake_run):
            a._live({"prompt": "hi", "timeout_s": 5})
        argv = seen["argv"]
        self.assertIn("--sandbox", argv)
        self.assertEqual(argv[argv.index("--sandbox") + 1], "enabled")
        self.assertEqual(argv[argv.index("--mode") + 1], "ask")
        self.assertIn("--workspace", argv)
        self.assertNotIn(os.path.expanduser("~"), argv[argv.index("--workspace") + 1:argv.index("--workspace") + 2])


if __name__ == "__main__":
    unittest.main()
