"""Unit tests for non-Grok orchestrator control plane."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from wolf_intelligence import orchestrator as orch
from wolf_intelligence.governance import GROK_WORKER_ID
from wolf_intelligence.paths import rebind_state_paths

FIXTURES = Path(__file__).resolve().parent / "fixtures"
OK_WORKER = str(FIXTURES / "orch_worker_ok.py")
FAIL_WORKER = str(FIXTURES / "orch_worker_fail.py")
SLOW_WORKER = str(FIXTURES / "orch_worker_slow.py")


class OrchestratorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._prev = os.environ.get("WOLF_INTELLIGENCE_STATE_ROOT")
        self.state_root = tempfile.mkdtemp(prefix="wi-orch-test-")
        os.environ["WOLF_INTELLIGENCE_STATE_ROOT"] = self.state_root
        rebind_state_paths()
        orch.rebind_orchestrator_paths()
        self.worktree = tempfile.mkdtemp(prefix="wi-orch-wt-")
        orch.save_config(
            {
                "claude_paused": True,
                "worktree_cwd": self.worktree,
                "worker_cmds": {
                    "cursor_sub": [
                        "python3",
                        OK_WORKER,
                        str(orch.ORCH_DIR / "runtime" / "{item_id}-{attempt}.completion.json"),
                        "PASS",
                        "build ok",
                    ],
                    "codex_sub": [
                        "python3",
                        OK_WORKER,
                        str(orch.ORCH_DIR / "runtime" / "{item_id}-{attempt}.completion.json"),
                        "PASS",
                        "review ok",
                    ],
                },
            }
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.state_root, ignore_errors=True)
        shutil.rmtree(self.worktree, ignore_errors=True)
        if self._prev is None:
            os.environ.pop("WOLF_INTELLIGENCE_STATE_ROOT", None)
        else:
            os.environ["WOLF_INTELLIGENCE_STATE_ROOT"] = self._prev
        rebind_state_paths()

    def _submit_build(self, item_id: str = "wi-build-1", **kw) -> dict:
        return orch.submit(
            {
                "id": item_id,
                "kind": "build",
                "spec": {"prompt": "add hello"},
                "acceptance": "hello() returns hello",
                "reviewer_gate": True,
                "timeout_s": 5,
                "max_attempts": 2,
                **kw,
            },
            now="2026-10-06T12:00:00+08:00",
        )

    def test_dispatch_with_fake_worker(self) -> None:
        self._submit_build()
        out = orch.run_once(now="2026-10-06T12:00:01+08:00")
        self.assertGreaterEqual(len(out["processed"]), 1)
        self.assertEqual(out["processed"][0]["action"], "dispatched")
        self.assertTrue(out["processed"][0]["ok"])
        item = orch.show("wi-build-1")
        self.assertEqual(item["status"], "CLOSED")
        self.assertIn("wi-build-1-review", orch.load_items())
        self.assertEqual(orch.show("wi-build-1-review")["status"], "CLOSED")

    def test_exactly_once_double_claim_refused(self) -> None:
        self._submit_build()
        claimed, key = orch.claim("wi-build-1", now="2026-10-06T12:00:01+08:00")
        self.assertIsNotNone(claimed)
        leases = orch.load_leases()
        leases[key]["dispatched"] = True
        orch.save_leases(leases)
        self.assertTrue(orch.refuse_double_claim("wi-build-1", 1))
        out = orch.dispatch_item(
            claimed,
            "cursor_sub",
            worktree=self.worktree,
            config=orch.load_config(),
            now="2026-10-06T12:00:02+08:00",
        )
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "already_dispatched")

    def test_restart_mid_lease_no_double_dispatch(self) -> None:
        self._submit_build()
        orch.claim("wi-build-1", now="2026-10-06T12:00:01+08:00")
        leases = orch.load_leases()
        key = "wi-build-1:1"
        leases[key]["dispatched"] = True
        leases[key]["expires_at"] = "2026-10-06T13:00:00+08:00"
        orch.save_leases(leases)
        items = orch.load_items()
        items["wi-build-1"]["status"] = "RUNNING"
        orch.save_items(items)
        out = orch.run_once(now="2026-10-06T12:00:05+08:00")
        self.assertEqual(out["processed"], [])

    def test_timeout(self) -> None:
        cfg = orch.load_config()
        cfg["worker_cmds"]["cursor_sub"] = ["python3", SLOW_WORKER]
        orch.save_config(cfg)
        self._submit_build(timeout_s=1)
        out = orch.run_once(now="2026-10-06T12:00:01+08:00")
        self.assertEqual(out["processed"][0]["status"], "TIMED_OUT")
        self.assertEqual(orch.show("wi-build-1")["status"], "QUEUED")

    def test_failure_reassignment(self) -> None:
        cfg = orch.load_config()
        cfg["worker_cmds"]["cursor_sub"] = ["python3", FAIL_WORKER, str(orch.ORCH_DIR / "runtime" / "{item_id}-{attempt}.completion.json")]
        orch.save_config(cfg)
        self._submit_build()
        out = orch.run_once(now="2026-10-06T12:00:01+08:00")
        self.assertEqual(out["processed"][0]["status"], "FAILED")
        self.assertEqual(orch.show("wi-build-1")["status"], "QUEUED")

    def test_review_gate_pass_and_fail(self) -> None:
        self._submit_build(reviewer_gate=True)
        orch.run_once(now="2026-10-06T12:00:01+08:00")
        orch.run_once(now="2026-10-06T12:00:02+08:00")
        self.assertEqual(orch.show("wi-build-1")["status"], "CLOSED")
        self.assertEqual(orch.show("wi-build-1-review")["status"], "CLOSED")

        cfg = orch.load_config()
        cfg["worker_cmds"]["codex_sub"][3] = "FAIL"
        cfg["worker_cmds"]["codex_sub"][4] = "review rejected"
        orch.save_config(cfg)
        orch.submit(
            {
                "id": "wi-build-2",
                "kind": "build",
                "spec": {},
                "acceptance": "x",
                "reviewer_gate": True,
                "timeout_s": 5,
                "max_attempts": 2,
            },
            now="2026-10-06T12:10:00+08:00",
        )
        orch.run_once(now="2026-10-06T12:10:01+08:00")
        self.assertEqual(orch.show("wi-build-2")["status"], "QUEUED")
        self.assertEqual(orch.show("wi-build-2-review")["status"], "FAILED")
        cfg["worker_cmds"]["codex_sub"][3] = "PASS"
        orch.save_config(cfg)
        orch.run_once(now="2026-10-06T12:10:02+08:00")
        self.assertEqual(orch.show("wi-build-2")["status"], "CLOSED")

    def test_completion_record_schema(self) -> None:
        self._submit_build(reviewer_gate=False)
        orch.run_once(now="2026-10-06T12:00:01+08:00")
        comp = list(orch.COMPLETIONS_DIR.glob("wi-build-1-1.json"))[0]
        rec = json.loads(comp.read_text())
        self.assertEqual(set(rec.keys()), set(orch.COMPLETION_FIELDS))
        md = comp.with_suffix(".md")
        self.assertTrue(md.exists())
        for key in orch.COMPLETION_FIELDS:
            self.assertIn(key, md.read_text())

    def test_grok_exhausted_still_completes(self) -> None:
        cap = {
            "workers": {
                GROK_WORKER_ID: {"state": "EXHAUSTED", "grok_available": False},
                "cursor_sub": {"state": "NORMAL"},
                "codex_sub": {"state": "NORMAL"},
            }
        }
        self._submit_build(reviewer_gate=False)
        with mock.patch.object(orch, "capacity_snapshot", return_value=cap):
            out = orch.run_once(now="2026-10-06T12:00:01+08:00")
        self.assertEqual(out["processed"][0]["worker"], "cursor_sub")
        self.assertTrue(out["processed"][0]["ok"])

    def test_notifications_only_when_required(self) -> None:
        self._submit_build(reviewer_gate=False)
        orch.run_once(now="2026-10-06T12:00:01+08:00")
        self.assertFalse(orch.NOTIFICATIONS_PATH.exists())

        cfg = orch.load_config()
        cfg["worker_cmds"]["cursor_sub"] = ["python3", FAIL_WORKER, str(orch.ORCH_DIR / "runtime" / "{item_id}-{attempt}.completion.json")]
        orch.save_config(cfg)
        orch.submit(
            {
                "id": "wi-fail-term",
                "kind": "build",
                "spec": {},
                "acceptance": "",
                "reviewer_gate": False,
                "timeout_s": 5,
                "max_attempts": 1,
            },
            now="2026-10-06T12:05:00+08:00",
        )
        orch.run_once(now="2026-10-06T12:05:01+08:00")
        notes = orch.NOTIFICATIONS_PATH.read_text().strip().splitlines()
        self.assertEqual(len(notes), 1)

    def test_health(self) -> None:
        self._submit_build()
        with mock.patch.object(orch.shutil, "which", side_effect=lambda b: f"/usr/bin/{b}"):
            h = orch.health(now="2026-10-06T12:00:00+08:00")
        self.assertIn("ok", h)
        self.assertIn("issues", h)
        self.assertIn("workers", h)

    def test_run_until_idle_review_chain(self) -> None:
        self._submit_build()
        out = orch.run_until_idle(now="2026-10-06T12:00:01+08:00")
        self.assertEqual(out["pending"], 0)
        self.assertEqual(orch.grok_invocation_count(), 0)


if __name__ == "__main__":
    unittest.main()
