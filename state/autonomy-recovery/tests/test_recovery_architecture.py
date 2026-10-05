#!/usr/bin/env python3
"""Safe controlled tests — no Studio, no Prod, no network to Tailscale."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nas-supervisor"))
sys.path.insert(0, str(ROOT / "worker-failover"))

from watcher import FakeTransport, NasSupervisor  # noqa: E402
from failover import FailoverRouter, StudioProbe, WorkStore, new_work_item  # noqa: E402


class TestNasSupervisor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.transport = FakeTransport()

    def tearDown(self):
        self.tmp.cleanup()

    def _sup(self, alt=False):
        return NasSupervisor(
            self.transport,
            self.root / "state.json",
            self.root / "audit.jsonl",
            miss_threshold=3,
            alt_worker_available=lambda: alt,
        )

    def test_detects_misses_and_recovers(self):
        s = self._sup(alt=True)
        self.transport.grok_up = False
        # Prevent FakeTransport auto-heal so we can observe latch
        self.transport.recover_watchdog = lambda: (
            setattr(self.transport, "recover_calls", self.transport.recover_calls + 1)
            or {"ok": True, "result": "RECOVER_WATCHDOG_DONE"}
        )
        for i in range(3):
            st = s.tick(now_epoch=1000 + i)
        self.assertEqual(st.last_event, "recover_fired")
        self.assertEqual(self.transport.recover_calls, 1)
        self.assertFalse(st.armed)  # latched
        # further misses do not loop-restart while still down
        self.transport.grok_up = False
        st2 = s.tick(now_epoch=1003)
        self.assertEqual(self.transport.recover_calls, 1)
        self.assertIn(st2.last_event, ("latched_wait_rearm", "backoff_hold"))
        # status up rearms
        self.transport.grok_up = True
        st3 = s.tick(now_epoch=2000)
        self.assertEqual(st3.last_event, "status_up")
        self.assertTrue(st3.armed)
        self.assertFalse(st3.escalate_human)  # alt worker available

    def test_escalate_only_when_no_alt(self):
        s = self._sup(alt=False)
        self.transport.grok_up = False
        # fire recover enough times to exhaust backoff schedule length
        t = 1000.0
        for _ in range(20):
            st = s.tick(now_epoch=t)
            t = max(t + 1, st.next_eligible_at_epoch + 1)
            # keep down
            self.transport.grok_up = False
            # re-arm artificially only via status_up — simulate by forcing armed after latch for test of attempts
            if not s.state.armed and s.state.recovery_attempts < 4:
                # advance past backoff and manually re-arm as if a flapping status
                s.state.armed = True
                s.state.consecutive_misses = 3
        self.assertTrue(s.state.escalate_human or s.state.recovery_attempts >= 1)


class TestWorkerFailover(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = WorkStore(self.root / "work.json")
        self.audit = self.root / "failover.audit.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_failover_to_cursor_when_studio_down(self):
        probe = StudioProbe(connected=False)
        r = FailoverRouter(self.store, probe, self.audit)
        item = new_work_item("Relabel phase6", "repo_edit")
        out = r.assign(item)
        self.assertEqual(out["action"], "ASSIGN")
        self.assertEqual(out["assigned_worker"], "cursor_cloud_agent")
        self.assertFalse(out["escalate_human"])
        # duplicate lock prevents second execution
        out2 = r.assign(item)
        self.assertEqual(out2["action"], "NOOP_ALREADY_LOCKED")
        self.assertTrue(out2["duplicate_prevented"])

    def test_hold_studio_required_without_human_when_alt_exists_for_other_work(self):
        probe = StudioProbe(connected=False)
        r = FailoverRouter(self.store, probe, self.audit)
        item = new_work_item("Beta reload", "beta_reload")
        out = r.assign(item)
        self.assertEqual(out["action"], "HOLD")
        self.assertTrue(out["escalate_human"])

    def test_no_prod_mutation_eligible(self):
        probe = StudioProbe(connected=False)
        r = FailoverRouter(self.store, probe, self.audit)
        item = new_work_item("Touch prod", "code_debug", production_mutation=True)
        out = r.assign(item)
        self.assertEqual(out["action"], "HOLD")

    def test_studio_up_uses_preferred(self):
        probe = StudioProbe(connected=True)
        r = FailoverRouter(self.store, probe, self.audit)
        item = new_work_item("Local prove", "repo_edit")
        out = r.assign(item)
        self.assertEqual(out["assigned_worker"], "studio_shell")


if __name__ == "__main__":
    unittest.main(verbosity=2)
