"""Unit tests for Wolf Intelligence hardening. Provider calls are mocked."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from wolf_intelligence import factory_history, ledger, paths, shadow_compare
from wolf_intelligence.adapters.base import AdapterResult
from wolf_intelligence.adapters.live_gate import LIVE_SUBMIT_ENV, MAX_COST_ENV, PROVIDER_MOCK_ENV


class FactoryHistoryTests(unittest.TestCase):
    def test_implied_primary_cursor_is_not_a_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "build-factory"
            root.mkdir()
            cfg = Path(tmp) / "factory-history-workers.json"
            cfg.write_text(json.dumps({
                "implied_primary_from_bf_cursor_launch": "cursor",
                "parsed_counts": {"cursor": 96, "unknown": 4},
                "sample_keys_example": {"file": "BF-ae8e2ebfc9ed.json", "worker": "cursor"},
            }))
            found = factory_history.collect_actual_workers(factory_root=root, config_path=cfg)
        self.assertEqual(found["last_worker_hint"], "UNKNOWN")
        self.assertEqual(found["jobs"], [])
        self.assertFalse(found["hint_defaulted"])

    def test_cursor_pid_on_a_job_is_per_job_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir(parents=True)
            job = runs / "BF-abc.json"
            job.write_text(json.dumps({"run_id": "BF-abc", "cursor_pid": 42, "updated_at": "2026-10-06T01:00:00+08:00"}))
            (runs / "BF-empty.json").write_text(json.dumps({"run_id": "BF-empty", "final_state": "DONE"}))
            found = factory_history.collect_actual_workers(factory_root=Path(tmp), config_path=Path(tmp) / "missing.json")
        self.assertEqual([row["worker"] for row in found["jobs"]], ["cursor"])
        self.assertEqual(found["jobs"][0]["evidence"], "cursor_pid_or_cursor_log")
        self.assertGreaterEqual(found["skipped_without_worker"], 1)

    def test_directory_without_marker_is_not_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "runs" / "BF-nomarker"
            run.mkdir(parents=True)
            (run / "notes.txt").write_text("no worker")
            found = factory_history.collect_actual_workers(factory_root=Path(tmp), config_path=Path(tmp) / "nope.json")
        self.assertEqual(found["last_worker_hint"], "UNKNOWN")
        self.assertEqual(found["skipped_without_worker"], 1)

    def test_config_job_list_needs_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "factory-history-workers.json"
            cfg.write_text(json.dumps({
                "jobs": [
                    {"job_id": "BF-1", "worker": "cursor", "evidence": "implied"},
                    {"job_id": "BF-2", "worker": "cursor", "cursor_pid": 7, "evidence": "cursor_pid_or_cursor_log", "at": "2026-10-06T02:00:00+08:00"},
                ]
            }))
            found = factory_history.collect_actual_workers(factory_root=Path(tmp), config_path=cfg)
        self.assertEqual(len(found["jobs"]), 1)
        self.assertEqual(found["jobs"][0]["job_id"], "BF-2")


class QualityAndShadowRecordTests(unittest.TestCase):
    def test_quality_unknown_without_paired_outputs(self) -> None:
        value, reason = shadow_compare.compute_quality_diff(paired=False, primary_pass=True, shadow_pass=True)
        self.assertEqual(value, "UNKNOWN")
        self.assertEqual(reason, "no_paired_outputs")

    def test_quality_from_rubric_when_paired(self) -> None:
        value, reason = shadow_compare.compute_quality_diff(paired=True, primary_pass=True, shadow_pass=False)
        self.assertEqual(value, 1)
        self.assertEqual(reason, "automated_rubric")

    def test_shadow_proved_requires_every_field(self) -> None:
        cost = ledger.capacity_for_worker("cursor")
        self.assertTrue(cost["known"])
        self.assertEqual(cost["capacity_monthly_usd"], 300)
        full = shadow_compare.assemble_record(
            label="SHADOW",
            synthetic=False,
            mocked=False,
            recommended_worker="ollama",
            actual_current_system_worker="cursor",
            actual_worker_source="/tmp/BF-1.json",
            outcome={"current_system": {"worker": "cursor", "output": "{\"ok\":true,\"n\":42}"}},
            test_result="pass",
            cost_or_capacity=cost,
            quality_diff=0,
            quality_diff_reason="automated_rubric",
        )
        self.assertTrue(full["shadow_proved"])
        self.assertEqual(full["truth_label"], "SHADOW PROVED")
        for key in shadow_compare.REQUIRED_KEYS:
            broken = dict(full)
            if key == "actual_current_system_worker":
                broken[key] = None
            elif key == "test_result":
                broken[key] = "UNKNOWN"
            elif key == "outcome":
                broken[key] = "UNKNOWN"
            elif key == "cost_or_capacity":
                broken[key] = {"known": False}
            elif key == "at":
                broken[key] = ""
            else:
                broken[key] = None
            broken["missing_for_shadow_proved"] = shadow_compare.missing_for_shadow_proved(broken)
            broken["shadow_proved"] = not broken["missing_for_shadow_proved"]
            self.assertFalse(broken["shadow_proved"], key)
            self.assertIn(key, broken["missing_for_shadow_proved"])

    def test_mocked_record_is_not_shadow_proved(self) -> None:
        row = shadow_compare.assemble_record(
            label="SHADOW",
            synthetic=False,
            mocked=True,
            recommended_worker="cursor",
            actual_current_system_worker="cursor",
            outcome={"current_system": "output"},
            test_result="pass",
            cost_or_capacity=ledger.capacity_for_worker("cursor"),
        )
        self.assertFalse(row["shadow_proved"])
        self.assertIn("mocked_not_evidence", row["missing_for_shadow_proved"])
        self.assertNotEqual(row["truth_label"], "SHADOW PROVED")


class AdapterGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = os.environ.copy()
        self.tmp = tempfile.TemporaryDirectory()
        self._ledger = paths.LEDGER_DIR
        paths.LEDGER_DIR = Path(self.tmp.name)
        paths.LEDGER_DIR.mkdir(exist_ok=True)
        os.environ.pop(LIVE_SUBMIT_ENV, None)
        os.environ.pop(MAX_COST_ENV, None)
        os.environ.pop(PROVIDER_MOCK_ENV, None)
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("GEMINI_API_KEY", None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env)
        paths.LEDGER_DIR = self._ledger
        self.tmp.cleanup()

    def test_ollama_shadow_does_not_generate(self) -> None:
        from wolf_intelligence.adapters.ollama import OllamaAdapter
        with mock.patch("wolf_intelligence.adapters.ollama.urllib.request.urlopen") as opened:
            result = OllamaAdapter().submit({"shadow_isolated": True, "prompt": "ping"})
        opened.assert_not_called()
        self.assertEqual(result.status, "SHADOW_OK")
        self.assertFalse(result.data.get("provider_called"))

    def test_ollama_execute_without_env_does_not_call(self) -> None:
        from wolf_intelligence.adapters.ollama import OllamaAdapter
        with mock.patch("wolf_intelligence.adapters.ollama.urllib.request.urlopen") as opened:
            result = OllamaAdapter().submit({"execute": True, "prompt": "ping"})
        opened.assert_not_called()
        self.assertEqual(result.status, "LIVE_DISABLED")

    def test_ollama_live_is_mocked_and_ledgered(self) -> None:
        from wolf_intelligence.adapters.ollama import OllamaAdapter
        os.environ[LIVE_SUBMIT_ENV] = "1"
        os.environ[PROVIDER_MOCK_ENV] = "1"
        body = json.dumps({"response": "{\"ok\":true,\"n\":42}", "prompt_eval_count": 53, "eval_count": 10}).encode()

        class _Resp:
            def read(self):
                return body
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        with mock.patch("wolf_intelligence.adapters.ollama.urllib.request.urlopen", return_value=_Resp()) as opened:
            result = OllamaAdapter().submit({"execute": True, "prompt": shadow_compare.TINY_PROMPT, "work_item_id": "wi_test"})
        self.assertTrue(opened.called)
        request = opened.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/api/generate"))
        self.assertEqual(result.status, "LIVE_OK")
        self.assertTrue(result.data.get("mocked"))
        self.assertEqual(result.data["usage"]["metered_usd"], 0.0)
        lines = (paths.LEDGER_DIR / "ledger.jsonl").read_text().strip().splitlines()
        self.assertIn("ollama_local", lines[-1])
        self.assertNotIn("sk-", lines[-1])

    def test_cursor_live_mocked(self) -> None:
        from wolf_intelligence.adapters.cursor import CursorAdapter
        os.environ[LIVE_SUBMIT_ENV] = "1"
        os.environ[PROVIDER_MOCK_ENV] = "1"

        class _Done:
            returncode = 0
            stdout = '{"ok":true,"n":42}\n'
            stderr = ""

        with mock.patch("wolf_intelligence.adapters.cursor._cursor_bin", return_value="/tmp/cursor-agent"), \
             mock.patch("wolf_intelligence.adapters.cursor.subprocess.run", return_value=_Done()) as run:
            result = CursorAdapter().submit({"execute": True, "prompt": shadow_compare.TINY_PROMPT, "work_item_id": "wi_cursor"})
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[1:4], ["--print", "--mode", "ask"])
        self.assertEqual(result.status, "LIVE_OK")
        self.assertTrue(result.data.get("mocked"))
        self.assertEqual(result.data["usage"]["metered_usd"], "UNKNOWN")
        self.assertEqual(result.data["usage"]["pool_id"], "cursor_sub_300")
        text = (paths.LEDGER_DIR / "ledger.jsonl").read_text()
        self.assertIn("cursor_sub_300", text)
        self.assertNotIn("Authorization", text)

    def test_paid_adapters_gated(self) -> None:
        from wolf_intelligence.adapters.anthropic_worker import AnthropicAPIAdapter
        from wolf_intelligence.adapters.gemini import GeminiAdapter
        from wolf_intelligence.adapters.openai_worker import OpenAIAPIAdapter
        os.environ[LIVE_SUBMIT_ENV] = "1"
        with mock.patch("wolf_intelligence.adapters.live_gate.urllib.request.urlopen") as opened:
            no_key = OpenAIAPIAdapter().submit({"execute": True, "max_cost_usd": 0.01})
            self.assertEqual(no_key.status, "UNAVAILABLE")
            os.environ["OPENAI_API_KEY"] = "unit-test-openai-key"
            no_cap = OpenAIAPIAdapter().submit({"execute": True})
            self.assertEqual(no_cap.status, "GATED")
            zero = OpenAIAPIAdapter().submit({"execute": True, "max_cost_usd": 0})
            self.assertEqual(zero.status, "GATED")
            os.environ["ANTHROPIC_API_KEY"] = "unit-test-anthropic-key"
            self.assertEqual(AnthropicAPIAdapter().submit({"execute": True}).status, "GATED")
            os.environ["GEMINI_API_KEY"] = "unit-test-gemini-key"
            self.assertEqual(GeminiAdapter().submit({"execute": True}).status, "GATED")
            opened.assert_not_called()

    def test_paid_openai_mocked_call_redacts_key(self) -> None:
        from wolf_intelligence.adapters.openai_worker import OpenAIAPIAdapter
        os.environ[LIVE_SUBMIT_ENV] = "1"
        os.environ[PROVIDER_MOCK_ENV] = "1"
        os.environ["OPENAI_API_KEY"] = "unit-test-openai-key"
        payload = {"choices": [{"message": {"content": "{\"ok\":true,\"n\":42}"}}]}

        class _Resp:
            def read(self):
                return json.dumps(payload).encode()
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        with mock.patch("wolf_intelligence.adapters.live_gate.urllib.request.urlopen", return_value=_Resp()):
            result = OpenAIAPIAdapter().submit({"execute": True, "max_cost_usd": 0.02, "prompt": "tiny"})
        blob = json.dumps(result.data)
        self.assertNotIn("unit-test-openai-key", blob)
        self.assertEqual(result.status, "LIVE_OK")
        self.assertTrue(result.data.get("mocked"))

    def test_health_only_workers_are_unsupported(self) -> None:
        from wolf_intelligence.adapters.anthropic_worker import ClaudeSubAdapter
        from wolf_intelligence.adapters.grok_bot import GrokBotAdapter
        from wolf_intelligence.adapters.openai_worker import OpenAIChatGPTAdapter
        from wolf_intelligence.adapters.peaches import PeachesAdapter
        os.environ[LIVE_SUBMIT_ENV] = "1"
        for adapter in (GrokBotAdapter(), PeachesAdapter(), OpenAIChatGPTAdapter(), ClaudeSubAdapter()):
            result = adapter.submit({"execute": True, "prompt": "tiny"})
            self.assertEqual(result.status, "UNSUPPORTED", adapter.worker_id)
            self.assertFalse(result.data.get("provider_called"))


class LedgerAndRealShadowTests(unittest.TestCase):
    def test_pool_separation_and_known_amounts(self) -> None:
        cap = ledger.load_capacity()
        pools = {row["id"]: row for row in cap["pools"]}
        self.assertEqual(pools["cursor_sub_300"]["monthly_usd"], 300)
        self.assertEqual(pools["cursor_sub_300"]["per_call_metered_usd"], "UNKNOWN")
        self.assertEqual(pools["claude_sub_25"]["monthly_usd"], 25)
        self.assertEqual(pools["claude_sub_25"]["separate_from_pool"], "anthropic_api")
        self.assertIsNone(pools["grok_sub"]["monthly_usd"])
        self.assertEqual(pools["grok_sub"]["plan_name"], "UNKNOWN")
        self.assertIsNone(pools["chatgpt_sub"]["monthly_usd"])
        self.assertEqual(pools["chatgpt_sub"]["plan_name"], "UNKNOWN")
        self.assertEqual(pools["gemini_free"]["monthly_usd"], 0)
        self.assertTrue(ledger.SUBSCRIPTION_POOLS.isdisjoint(ledger.API_POOLS))
        with self.assertRaises(KeyError):
            ledger.record_usage(pool_id="anthropic_api", amount_usd=0, worker_id="claude_sub", note="should fail")

    def test_real_shadow_refuses_when_flag_off(self) -> None:
        os.environ.pop(LIVE_SUBMIT_ENV, None)
        with tempfile.TemporaryDirectory() as tmp:
            shadow = Path(tmp) / "shadow"
            shadow.mkdir()
            cfg = Path(tmp) / "phase6.json"
            old_shadow = paths.SHADOW_DIR
            paths.SHADOW_DIR = shadow
            try:
                with mock.patch("wolf_intelligence.shadow_compare._phase6_path", return_value=cfg):
                    out = shadow_compare.run_real_shadow(1, primary_worker="cursor", shadow_worker="ollama")
            finally:
                paths.SHADOW_DIR = old_shadow
        self.assertEqual(out["status"], "NOT_RUN")
        self.assertFalse(out["shadow_proved"])
        self.assertEqual(out["label"], "SHADOW")
        self.assertFalse(out["took_action"])

    def test_real_shadow_mocked_parallel_is_not_proved_without_factory_worker(self) -> None:
        os.environ[LIVE_SUBMIT_ENV] = "1"
        os.environ[PROVIDER_MOCK_ENV] = "1"
        calls = []

        def _submit(job):
            calls.append(job["worker_id"])
            self.assertTrue(job["execute"])
            return AdapterResult(True, "LIVE_OK", "mocked provider", {
                "output": '{"ok":true,"n":42}',
                "latency_ms": 3,
                "mocked": True,
                "provider_called": True,
                "model_id": "mock",
                "usage": {"amount_usd": 0.0, "metered_usd": 0.0},
            })

        class _Adapter:
            supports = frozenset({"submit"})
            def __init__(self, worker):
                self.worker_id = worker
            def submit(self, job):
                job = dict(job)
                job["worker_id"] = self.worker_id
                return _submit(job)

        with tempfile.TemporaryDirectory() as tmp:
            shadow = Path(tmp) / "shadow"
            shadow.mkdir()
            cfg = Path(tmp) / "phase6.json"
            old_shadow = paths.SHADOW_DIR
            paths.SHADOW_DIR = shadow
            try:
                with mock.patch("wolf_intelligence.shadow_compare._phase6_path", return_value=cfg), \
                     mock.patch("wolf_intelligence.shadow_compare.collect_actual_workers", return_value={
                         "jobs": [],
                         "last_worker_hint": "UNKNOWN",
                         "last_worker_hint_source": "UNKNOWN",
                         "last_worker_hint_sample_counts": {},
                         "skipped_without_worker": 0,
                         "hint_defaulted": False,
                     }), \
                     mock.patch("wolf_intelligence.shadow_compare.recommend", return_value={
                         "recommendation": {"recommended_worker": "cursor", "recommended_model_id": "cursor-agent", "mode": "SHADOW"},
                         "scores": [],
                     }), \
                     mock.patch("wolf_intelligence.shadow_compare.work_items.create", return_value={"id": "wi_shadow", "kind": "code_debug"}), \
                     mock.patch("wolf_intelligence.shadow_compare.work_items.update_fields"), \
                     mock.patch("wolf_intelligence.shadow_compare.get_adapter", side_effect=lambda wid: _Adapter(wid)), \
                     mock.patch("wolf_intelligence.shadow_compare.events.emit"):
                    out = shadow_compare.run_real_shadow(1, primary_worker="cursor", shadow_worker="ollama")
            finally:
                paths.SHADOW_DIR = old_shadow
                os.environ.pop(LIVE_SUBMIT_ENV, None)
                os.environ.pop(PROVIDER_MOCK_ENV, None)
        self.assertEqual(sorted(calls), ["cursor", "ollama"])
        self.assertEqual(out["label"], "SHADOW")
        self.assertFalse(out["shadow_proved"])
        self.assertTrue(out["mocked"])
        row = out["runs"][0]
        for key in shadow_compare.REQUIRED_KEYS:
            self.assertIn(key, row)
        self.assertIsNone(row["actual_current_system_worker"])
        self.assertEqual(row["recommended_worker"], "cursor")
        self.assertEqual(row["test_result"], "UNKNOWN")
        self.assertNotEqual(row["truth_label"], "SHADOW PROVED")


if __name__ == "__main__":
    unittest.main()
