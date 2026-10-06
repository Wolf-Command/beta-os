"""Regression tests for deterministic worker failover."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from wolf_intelligence import failover, orchestrator as orch
from wolf_intelligence.governance import GROK_WORKER_ID
from wolf_intelligence.paths import rebind_state_paths

FIXTURES = Path(__file__).resolve().parent / "fixtures"
OK_WORKER = str(FIXTURES / "orch_worker_ok.py")


class FailoverTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._prev = os.environ.get("WOLF_INTELLIGENCE_STATE_ROOT")
        self.state_root = tempfile.mkdtemp(prefix="wi-failover-test-")
        os.environ["WOLF_INTELLIGENCE_STATE_ROOT"] = self.state_root
        rebind_state_paths()
        orch.rebind_orchestrator_paths()
        self.worktree = tempfile.mkdtemp(prefix="wi-failover-wt-")
        self._init_registry()
        orch.save_config(
            {
                "claude_paused": False,
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
                    "claude_pro_sub": [
                        "python3",
                        OK_WORKER,
                        str(orch.ORCH_DIR / "runtime" / "{item_id}-{attempt}.completion.json"),
                        "PASS",
                        "claude review ok",
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

    def _init_registry(self) -> None:
        reg = failover.default_registry()
        workers = reg["workers"]
        for wid in ("claude_pro_sub", "codex_sub", "cursor_sub"):
            workers[wid]["commissioning_state"] = "commissioned"
        workers["ollama_local"]["commissioning_state"] = "not_commissioned"
        workers["claude_pro_sub"]["benchmark_eligibility"]["review_reasoning"] = 0.95
        workers["codex_sub"]["benchmark_eligibility"]["review_reasoning"] = 0.85
        workers["codex_sub"]["benchmark_eligibility"]["build"] = 0.82
        workers["cursor_sub"]["benchmark_eligibility"]["build"] = 0.90
        workers["anthropic_api"] = {
            "worker_id": "anthropic_api",
            "capabilities": list(failover.CAPABILITIES),
            "commissioning_state": "commissioned",
            "benchmark_eligibility": {c: 1.0 for c in failover.CAPABILITIES},
            "billing_class": "metered",
            "context_limit": 200_000,
        }
        failover.save_registry(reg)
        failover.save_availability({"workers": {}})
        failover.save_failover_config(
            {
                "wait_window_minutes": 90,
                "benchmark_delta_threshold": 0.15,
                "operational_blocker": False,
                "min_benchmark_score": 0.5,
            }
        )
        failover.save_spend_policy({"owner_approved": False, "records": []})
        failover.save_flags({"peaches_chat_degraded": False})

    def _capacity(self, **states: str) -> dict:
        workers = {
            "claude_pro_sub": {"state": states.get("claude", "NORMAL")},
            "cursor_sub": {"state": states.get("cursor", "NORMAL")},
            "codex_sub": {"state": states.get("codex", "NORMAL")},
            GROK_WORKER_ID: {
                "state": states.get("grok", "NORMAL"),
                "grok_available": states.get("grok_available", "true") != "false",
            },
        }
        return {"workers": workers}

    def test_failover_claude_limit_codex_inherits_review(self) -> None:
        failover.set_worker_availability(
            "claude_pro_sub",
            "session_limit",
            reset_time="2026-10-06T13:00:00+08:00",
            evidence=["session limit reached"],
        )
        item = {
            "id": "rev-1",
            "kind": "review",
            "spec": {"parent": "b-1", "review_type": "reasoning"},
        }
        items = {"b-1": {"id": "b-1", "kind": "build", "last_worker": "cursor_sub"}}
        d = failover.decide_routing(
            item,
            capacity=self._capacity(),
            items=items,
            now="2026-10-06T12:00:00+08:00",
        )
        self.assertEqual(d["action"], "FAILOVER")
        self.assertEqual(d["worker_id"], "codex_sub")

    def test_failover_cursor_limit_engineering_replacement(self) -> None:
        failover.set_worker_availability("cursor_sub", "weekly_limit", evidence=["weekly limit"])
        item = {"id": "build-1", "kind": "build", "spec": {}}
        d = failover.decide_routing(
            item,
            capacity=self._capacity(cursor="EXHAUSTED"),
            now="2026-10-06T12:00:00+08:00",
        )
        self.assertEqual(d["action"], "FAILOVER")
        self.assertEqual(d["worker_id"], "codex_sub")

    def test_failover_grok_exhaustion_wolf_continues(self) -> None:
        failover.set_worker_availability(GROK_WORKER_ID, "weekly_limit", evidence=["grok exhausted"])
        cap = self._capacity(grok="EXHAUSTED", grok_available="false")
        failover.update_grok_capacity_flag(cap)
        build = failover.decide_routing(
            {"id": "b-grok", "kind": "build", "spec": {}},
            capacity=cap,
            now="2026-10-06T12:00:00+08:00",
        )
        review = failover.decide_routing(
            {
                "id": "r-grok",
                "kind": "review",
                "spec": {"parent": "b-grok", "review_type": "reasoning"},
            },
            capacity=cap,
            items={"b-grok": {"id": "b-grok", "kind": "build", "last_worker": "cursor_sub"}},
            now="2026-10-06T12:00:00+08:00",
        )
        self.assertEqual(build["worker_id"], "cursor_sub")
        self.assertIn(review["worker_id"], ("claude_pro_sub", "codex_sub"))
        self.assertTrue(failover.peaches_chat_degraded())

    def test_failover_claude_codex_unavailable_no_paid_fallback(self) -> None:
        failover.set_worker_availability("claude_pro_sub", "weekly_limit", evidence=["weekly"])
        failover.set_worker_availability("codex_sub", "session_limit", evidence=["session"])
        item = {
            "id": "rev-paid",
            "kind": "review",
            "spec": {"parent": "b-paid", "review_type": "reasoning"},
        }
        items = {"b-paid": {"id": "b-paid", "kind": "build", "last_worker": "cursor_sub"}}
        d = failover.decide_routing(
            item,
            capacity=self._capacity(claude="EXHAUSTED", codex="EXHAUSTED"),
            items=items,
            now="2026-10-06T12:00:00+08:00",
        )
        self.assertEqual(d["action"], "WAITING_FOR_CAPACITY")
        self.assertIsNone(d["worker_id"])
        audit = (Path(self.state_root) / "failover" / "audit.jsonl").read_text()
        self.assertNotIn("anthropic_api", audit)
        self.assertNotIn("openai_api", audit)

    def test_failover_all_unavailable_waiting_for_capacity(self) -> None:
        failover.set_worker_availability("claude_pro_sub", "weekly_limit", evidence=["w"])
        failover.set_worker_availability("cursor_sub", "weekly_limit", evidence=["w"])
        failover.set_worker_availability("codex_sub", "weekly_limit", evidence=["w"])
        d = failover.decide_routing(
            {"id": "all-down", "kind": "build", "spec": {}},
            capacity=self._capacity(claude="EXHAUSTED", cursor="EXHAUSTED", codex="EXHAUSTED"),
            now="2026-10-06T12:00:00+08:00",
        )
        self.assertEqual(d["action"], "WAITING_FOR_CAPACITY")

    def test_failover_restart_policy_persists(self) -> None:
        failover.set_worker_availability(
            "claude_pro_sub",
            "session_limit",
            reset_time="2026-10-06T13:30:00+08:00",
            evidence=["persist"],
        )
        reg_before = failover.load_registry()
        avail_before = failover.load_availability()
        rebind_state_paths()
        orch.rebind_orchestrator_paths()
        self.assertEqual(failover.load_registry(), reg_before)
        self.assertEqual(failover.load_availability(), avail_before)

    def test_builder_never_reviews_own_work(self) -> None:
        item = {
            "id": "rev-ind",
            "kind": "review",
            "spec": {"parent": "b-ind", "review_type": "reasoning"},
        }
        items = {"b-ind": {"id": "b-ind", "kind": "build", "last_worker": "codex_sub"}}
        reg = failover.load_registry()
        reg["workers"]["codex_sub"]["capabilities"].append("review_reasoning")
        reg["workers"]["claude_pro_sub"]["commissioning_state"] = "suspended"
        failover.save_registry(reg)
        failover.set_worker_availability("claude_pro_sub", "weekly_limit", evidence=["down"])
        d = failover.decide_routing(
            item,
            capacity=self._capacity(claude="EXHAUSTED"),
            items=items,
            now="2026-10-06T12:00:00+08:00",
        )
        self.assertNotEqual(d.get("worker_id"), "codex_sub")
        self.assertEqual(d["action"], "WAITING_FOR_CAPACITY")

    def test_wait_when_reset_soon_and_non_urgent(self) -> None:
        reg = failover.load_registry()
        reg["workers"]["codex_sub"]["benchmark_eligibility"]["review_reasoning"] = 0.70
        failover.save_registry(reg)
        failover.set_worker_availability(
            "claude_pro_sub",
            "session_limit",
            reset_time="2026-10-06T13:00:00+08:00",
            evidence=["session"],
        )
        item = {
            "id": "rev-wait",
            "kind": "review",
            "spec": {"parent": "b-w", "review_type": "reasoning", "urgent": False},
            "urgent": False,
        }
        items = {"b-w": {"id": "b-w", "kind": "build", "last_worker": "cursor_sub"}}
        d = failover.decide_routing(
            item,
            capacity=self._capacity(),
            items=items,
            now="2026-10-06T12:00:00+08:00",
        )
        self.assertEqual(d["action"], "WAIT")

    def test_failover_when_urgent(self) -> None:
        failover.set_worker_availability(
            "claude_pro_sub",
            "session_limit",
            reset_time="2026-10-06T13:00:00+08:00",
            evidence=["session"],
        )
        item = {
            "id": "rev-urgent",
            "kind": "review",
            "spec": {"parent": "b-u", "review_type": "reasoning"},
            "urgent": True,
        }
        items = {"b-u": {"id": "b-u", "kind": "build", "last_worker": "cursor_sub"}}
        d = failover.decide_routing(
            item,
            capacity=self._capacity(),
            items=items,
            now="2026-10-06T12:00:00+08:00",
        )
        self.assertEqual(d["action"], "FAILOVER")
        self.assertEqual(d["worker_id"], "codex_sub")

    def test_metered_only_with_owner_spend_record(self) -> None:
        failover.set_worker_availability("claude_pro_sub", "weekly_limit", evidence=["w"])
        failover.set_worker_availability("codex_sub", "weekly_limit", evidence=["w"])
        failover.set_worker_availability("cursor_sub", "weekly_limit", evidence=["w"])
        failover.save_spend_policy({"owner_approved": True, "records": [{"approved_by": "owner"}]})
        item = {"id": "m-build", "kind": "build", "spec": {}}
        reg = failover.load_registry()
        reg["workers"]["anthropic_api"]["capabilities"].append("build")
        failover.save_registry(reg)
        with mock.patch("wolf_intelligence.failover.metered_allowed", return_value=True):
            d = failover.decide_routing(
                item,
                capacity=self._capacity(claude="EXHAUSTED", cursor="EXHAUSTED", codex="EXHAUSTED"),
                now="2026-10-06T12:00:00+08:00",
            )
        self.assertEqual(d["worker_id"], "anthropic_api")

    def test_selection_uses_capability_not_model_name(self) -> None:
        item = {
            "id": "rev-cap",
            "kind": "review",
            "spec": {"review_type": "security", "model": "claude-opus-5-5"},
        }
        d = failover.decide_routing(item, capacity=self._capacity(), now="2026-10-06T12:00:00+08:00")
        self.assertEqual(d["capability"], "review_security")
        self.assertEqual(d["worker_id"], "claude_pro_sub")

    def test_availability_from_stderr_patterns(self) -> None:
        out = failover.record_availability_from_dispatch(
            "claude_pro_sub",
            exit_code=1,
            stderr="Error: weekly limit exceeded for subscription",
            now="2026-10-06T12:00:00+08:00",
        )
        self.assertTrue(out["updated"])
        self.assertEqual(out["state"], "weekly_limit")
        avail = failover.load_availability()
        self.assertEqual(avail["workers"]["claude_pro_sub"]["state"], "weekly_limit")

    def test_audit_record_fields(self) -> None:
        failover.set_worker_availability("claude_pro_sub", "session_limit", reset_time="2026-10-06T13:00:00+08:00")
        item = {
            "id": "audit-1",
            "kind": "review",
            "spec": {"parent": "b-a", "review_type": "reasoning"},
            "urgent": True,
        }
        items = {"b-a": {"id": "b-a", "kind": "build", "last_worker": "cursor_sub"}}
        failover.decide_routing(
            item,
            capacity=self._capacity(),
            items=items,
            now="2026-10-06T12:00:00+08:00",
        )
        audit_path = Path(self.state_root) / "failover" / "audit.jsonl"
        rec = json.loads(audit_path.read_text().strip().splitlines()[-1])
        for key in (
            "PREFERRED_WORKER",
            "UNAVAILABLE_REASON",
            "RESET_TIME",
            "REPLACEMENT_WORKER",
            "WHY_SELECTED",
            "WAIT_OR_FAILOVER",
            "EVIDENCE",
            "BILLING_CLASS",
            "timestamp",
            "work_item_id",
        ):
            self.assertIn(key, rec)


if __name__ == "__main__":
    unittest.main()
