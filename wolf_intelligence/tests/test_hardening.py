"""Unit tests for Wolf Intelligence hardening. Provider calls are mocked."""
from __future__ import annotations

# --- State isolation (Vesper M1) -------------------------------------------
# Runs before any wolf_intelligence import so paths.STATE_ROOT resolves to a
# throwaway temp dir. No test can read or write the live Beta WI state.
import atexit as _atexit
import os as _os
import shutil as _shutil
import sys as _sys
import tempfile as _tempfile

if not _os.environ.get("WI_TEST_STATE_ISOLATED"):
    # Remember the configured (live) root so the guard can refuse it even if it moves out of beta-os.
    _os.environ["WI_TEST_CONFIGURED_STATE_ROOT"] = _os.environ.get("WOLF_INTELLIGENCE_STATE_ROOT", "")
    _TEST_STATE_ROOT = _tempfile.mkdtemp(prefix="wi-test-state-")
    _os.environ["WOLF_INTELLIGENCE_STATE_ROOT"] = _TEST_STATE_ROOT
    _os.environ["WI_TEST_STATE_ISOLATED"] = _TEST_STATE_ROOT
    _os.environ.pop("WOLF_INTELLIGENCE_CONFIG_MIRROR", None)
    _atexit.register(_shutil.rmtree, _TEST_STATE_ROOT, True)
    if "wolf_intelligence.paths" in _sys.modules:
        from wolf_intelligence.paths import rebind_state_paths

        rebind_state_paths()
# ---------------------------------------------------------------------------

import http.client
import json
import os
import socket
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from wolf_intelligence import factory_history, learning, ledger, paths, shadow_compare, stats_store
from wolf_intelligence.adapters.base import AdapterResult
from wolf_intelligence.adapters.live_gate import (
    LIVE_SUBMIT_ENV,
    MAX_COST_ENV,
    PROVIDER_MOCK_ENV,
    cost_cap,
    estimate_call_cost_usd,
    model_price,
)

def _live_state_roots() -> list[Path]:
    """Live roots derived from configuration, not a hardcoded path: the package's
    LIVE_STATE_ROOT plus any WOLF_INTELLIGENCE_STATE_ROOT configured before isolation."""
    roots = [Path(paths.LIVE_STATE_ROOT).resolve()]
    configured = os.environ.get("WI_TEST_CONFIGURED_STATE_ROOT", "").strip()
    if configured:
        roots.append(Path(configured).expanduser().resolve())
    return roots


def _related(a: Path, b: Path) -> bool:
    return a == b or a.is_relative_to(b) or b.is_relative_to(a)


def assert_test_state_root_is_safe(root: Path) -> None:
    root = Path(root).resolve()
    for live in _live_state_roots():
        if _related(root, live):
            raise RuntimeError("refusing to run tests against live Wolf Intelligence state")
    if not root.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise RuntimeError("refusing to run tests outside the system temp dir")


assert_test_state_root_is_safe(paths.STATE_ROOT)


def _verified_price_table(tmpdir: str) -> Path:
    """A copy of the shipped price table with every entry marked verified (tests only)."""
    from wolf_intelligence.adapters import live_gate
    data = json.loads(live_gate.PRICE_CEILINGS_PATH.read_text(encoding="utf-8"))
    for entry in data["models"].values():
        entry["verified"] = True
    out = Path(tmpdir) / "price-ceilings.verified.json"
    out.write_text(json.dumps(data), encoding="utf-8")
    return out


def _owner_caps(per_call: str = "1.0", daily: str = "1.0") -> None:
    os.environ[MAX_COST_ENV] = per_call
    os.environ["WOLF_INTELLIGENCE_MAX_DAILY_COST_USD"] = daily


class StateIsolationTests(unittest.TestCase):
    def test_every_state_path_is_under_the_temp_root(self) -> None:
        from wolf_intelligence import events, owner_ui_server, work_items
        root = Path(os.environ["WOLF_INTELLIGENCE_STATE_ROOT"]).resolve()
        self.assertEqual(paths.STATE_ROOT, root)
        self.assertNotEqual(paths.STATE_ROOT, paths.LIVE_STATE_ROOT)
        for live in _live_state_roots():
            self.assertFalse(_related(root, live), str(live))
        for p in (
            paths.WORK_ITEMS_DIR, paths.EVENTS_PATH, paths.AUDIT_DIR, paths.LEDGER_DIR,
            paths.LEARNING_DIR, paths.SHADOW_DIR, paths.WORKERS_DIR, paths.SQLITE_PATH,
            paths.MIRROR_DIR, work_items.SQLITE_PATH, work_items.WORK_ITEMS_DIR,
            events.EVENTS_PATH, events.AUDIT_DIR, learning.OUTCOMES_PATH, learning.WEIGHTS_PATH,
            stats_store.STATS_PATH, stats_store.SUMMARY_PATH, owner_ui_server.AUDIT_DIR,
            ledger._ledger_path() if hasattr(ledger, "_ledger_path") else paths.LEDGER_DIR,
            ledger.SNAPSHOT_PATH, ledger.LEDGER_PATH,
        ):
            self.assertTrue(Path(p).resolve().is_relative_to(root), str(p))

    def test_ledger_snapshot_never_writes_live_state(self) -> None:
        snap_path = ledger.SNAPSHOT_PATH.resolve()
        live_snap = (paths.LIVE_STATE_ROOT / "ledger" / "snapshot.json").resolve()
        self.assertTrue(snap_path.is_relative_to(paths.STATE_ROOT))
        self.assertNotEqual(snap_path, live_snap)
        ledger.snapshot()
        self.assertTrue(snap_path.exists())
        self.assertTrue(snap_path.is_relative_to(paths.STATE_ROOT))
        self.assertNotEqual(snap_path, live_snap)

    def test_work_item_create_lands_in_temp_store(self) -> None:
        from wolf_intelligence import work_items
        wi = work_items.create(title="isolation probe", kind="review", isolated_safe=True)
        self.assertTrue(work_items.SQLITE_PATH.exists())
        self.assertTrue(work_items.SQLITE_PATH.resolve().is_relative_to(paths.STATE_ROOT))
        self.assertEqual(work_items.get(wi["id"])["title"], "isolation probe")

    def test_state_root_env_override(self) -> None:
        with mock.patch.dict(os.environ, {paths.STATE_ROOT_ENV: "/tmp/wi-elsewhere"}):
            self.assertEqual(paths._state_root(), Path("/tmp/wi-elsewhere").resolve())
        with mock.patch.dict(os.environ, {paths.STATE_ROOT_ENV: ""}):
            self.assertEqual(paths._state_root(), paths.LIVE_STATE_ROOT)

    def test_generated_summaries_stay_out_of_config(self) -> None:
        with mock.patch.dict(os.environ, {paths.CONFIG_MIRROR_ENV: ""}):
            self.assertEqual(paths.mirror_path("stats-summary.json").parent, paths.MIRROR_DIR)
        with mock.patch.dict(os.environ, {paths.CONFIG_MIRROR_ENV: "1"}):
            self.assertEqual(paths.mirror_path("stats-summary.json").parent, paths.CONFIG_DIR)
        self.assertEqual(stats_store.SUMMARY_PATH.parent, paths.MIRROR_DIR)
        self.assertEqual(shadow_compare._phase6_path().parent, paths.MIRROR_DIR)


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
        os.environ.pop("WOLF_INTELLIGENCE_MAX_DAILY_COST_USD", None)

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
        self.assertEqual(cmd[1:6], ["--print", "--mode", "ask", "--trust", "--workspace"])
        self.assertIn("wi-cursor-ask-", cmd[6])
        self.assertEqual(cmd[-1], shadow_compare.TINY_PROMPT)
        self.assertFalse(Path(cmd[6]).exists())
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

        _owner_caps()
        with mock.patch("wolf_intelligence.adapters.live_gate.PRICE_CEILINGS_PATH", _verified_price_table(self.tmp.name)), \
             mock.patch("wolf_intelligence.adapters.live_gate.urllib.request.urlopen", return_value=_Resp()):
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


    def test_cost_cap_is_a_real_ceiling(self) -> None:
        from wolf_intelligence.adapters.anthropic_worker import AnthropicAPIAdapter
        from wolf_intelligence.adapters.gemini import GeminiAdapter
        from wolf_intelligence.adapters.openai_worker import OpenAIAPIAdapter
        os.environ[LIVE_SUBMIT_ENV] = "1"
        os.environ["OPENAI_API_KEY"] = "unit-test-openai-key"
        os.environ["ANTHROPIC_API_KEY"] = "unit-test-anthropic-key"
        os.environ["GEMINI_API_KEY"] = "unit-test-gemini-key"
        _owner_caps()
        with mock.patch("wolf_intelligence.adapters.live_gate.PRICE_CEILINGS_PATH", _verified_price_table(self.tmp.name)), \
             mock.patch("wolf_intelligence.adapters.live_gate.urllib.request.urlopen") as opened:
            tiny_cap = OpenAIAPIAdapter().submit({"execute": True, "max_cost_usd": 0.0000001, "prompt": "tiny"})
            self.assertEqual(tiny_cap.status, "GATED")
            self.assertIn("exceeds", tiny_cap.message)
            self.assertGreater(tiny_cap.data["estimated_max_usd"], tiny_cap.data["max_cost_usd"])
            big_prompt = AnthropicAPIAdapter().submit(
                {"execute": True, "max_cost_usd": 0.0005, "prompt": "x" * 20000, "num_predict": 128}
            )
            self.assertEqual(big_prompt.status, "GATED")
            self.assertIn("exceeds", big_prompt.message)
            unknown = OpenAIAPIAdapter().submit({"execute": True, "max_cost_usd": 5, "model": "gpt-imaginary-9", "prompt": "tiny"})
            self.assertEqual(unknown.status, "GATED")
            self.assertIn("no price ceiling", unknown.message)
            gemini_zero = GeminiAdapter().submit({"execute": True, "max_cost_usd": 0, "prompt": "tiny"})
            self.assertEqual(gemini_zero.status, "GATED")
            opened.assert_not_called()

    def test_cost_estimate_is_worst_case_and_matches_model_family(self) -> None:
        self.assertIsNotNone(model_price("claude-3-5-haiku-latest"))
        self.assertEqual(model_price("claude-3-5-haiku-20241022"), model_price("claude-3-5-haiku"))
        self.assertEqual(model_price("gpt-4o-mini"), {"input": 0.15, "output": 0.60})
        self.assertNotEqual(model_price("gpt-4o-mini"), model_price("gpt-4o"))
        self.assertIsNone(model_price("unknown-model"))
        small = estimate_call_cost_usd("gpt-4o-mini", "hi", 1)
        large = estimate_call_cost_usd("gpt-4o-mini", "x" * 5000, 128)
        self.assertGreater(small, 0)
        self.assertGreater(large, small)
        self.assertIsNone(estimate_call_cost_usd("unknown-model", "hi", 1))

    def test_call_under_cap_proceeds_and_reports_estimate(self) -> None:
        from wolf_intelligence.adapters.anthropic_worker import AnthropicAPIAdapter
        os.environ[LIVE_SUBMIT_ENV] = "1"
        os.environ[PROVIDER_MOCK_ENV] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "unit-test-anthropic-key"
        payload = {"content": [{"text": "{\"ok\":true,\"n\":42}"}]}

        class _Resp:
            def read(self):
                return json.dumps(payload).encode()
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        _owner_caps()
        with mock.patch("wolf_intelligence.adapters.live_gate.PRICE_CEILINGS_PATH", _verified_price_table(self.tmp.name)), \
             mock.patch("wolf_intelligence.adapters.live_gate.urllib.request.urlopen", return_value=_Resp()) as opened:
            result = AnthropicAPIAdapter().submit({"execute": True, "max_cost_usd": 0.01, "prompt": "tiny"})
        self.assertTrue(opened.called)
        self.assertEqual(result.status, "LIVE_OK")
        usage = result.data["usage"]
        self.assertLessEqual(usage["estimated_max_usd"], usage["max_cost_usd"])
        self.assertNotIn("unit-test-anthropic-key", json.dumps(result.data))


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


class LiveSubmitDefaultsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = os.environ.copy()
        os.environ.pop(LIVE_SUBMIT_ENV, None)
        os.environ.pop(MAX_COST_ENV, None)
        os.environ.pop(PROVIDER_MOCK_ENV, None)
        os.environ.pop("OPENAI_API_KEY", None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env)

    def test_live_submit_off_unless_execute_and_env(self) -> None:
        from wolf_intelligence.__main__ import main
        from wolf_intelligence.adapters.cursor import CursorAdapter
        from wolf_intelligence.adapters.ollama import OllamaAdapter
        with mock.patch("wolf_intelligence.adapters.ollama.urllib.request.urlopen") as opened, \
             mock.patch("wolf_intelligence.adapters.cursor.subprocess.run") as run:
            missing_env = OllamaAdapter().submit({"execute": True, "prompt": "ping"})
            self.assertEqual(missing_env.status, "LIVE_DISABLED")
            os.environ[LIVE_SUBMIT_ENV] = "1"
            missing_execute = OllamaAdapter().submit({"shadow_isolated": True, "prompt": "ping"})
            self.assertEqual(missing_execute.status, "SHADOW_OK")
            self.assertFalse(missing_execute.data.get("provider_called"))
            os.environ.pop(LIVE_SUBMIT_ENV, None)
            cursor_off = CursorAdapter().submit({"execute": True, "prompt": "ping"})
            self.assertEqual(cursor_off.status, "LIVE_DISABLED")
            self.assertEqual(main(["live-submit", "--worker", "ollama", "--execute"]), 2)
            os.environ[LIVE_SUBMIT_ENV] = "1"
            self.assertEqual(main(["live-submit", "--worker", "ollama"]), 2)
        opened.assert_not_called()
        run.assert_not_called()

    def test_paid_cost_cap_on_by_default(self) -> None:
        from wolf_intelligence.adapters.openai_worker import OpenAIAPIAdapter
        os.environ[LIVE_SUBMIT_ENV] = "1"
        os.environ["OPENAI_API_KEY"] = "unit-test-openai-key"
        self.assertIsNone(os.environ.get(MAX_COST_ENV))
        self.assertIsNone(cost_cap({}))
        with mock.patch("wolf_intelligence.adapters.live_gate.urllib.request.urlopen") as opened:
            result = OpenAIAPIAdapter().submit({"execute": True, "prompt": "tiny"})
        self.assertEqual(result.status, "GATED")
        self.assertFalse(result.data.get("provider_called"))
        opened.assert_not_called()

    def test_no_hardcoded_cursor_hint(self) -> None:
        root = Path(paths.PKG_ROOT)
        hint = re.compile(
            r"""last_worker_hint\s*[:=]\s*['\"]cursor['\"]"""
            r"""|recommended_worker\s*=\s*['\"]cursor['\"]"""
            r"""|default\s*=\s*['\"]cursor['\"]"""
        )
        hits = []
        for path in root.rglob("*.py"):
            if "tests" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for i, line in enumerate(text.splitlines(), start=1):
                if hint.search(line):
                    hits.append(f"{path.name}:{i}:{line.strip()}")
        self.assertEqual(hits, [])
        router_src = (root / "router.py").read_text(encoding="utf-8")
        self.assertNotIn('"cursor"', router_src)
        self.assertNotIn("'cursor'", router_src)
        from wolf_intelligence.router import recommend
        with mock.patch("wolf_intelligence.router.ADAPTER_REGISTRY", {}):
            out = recommend({"id": "wi_no_default", "kind": "code_debug"})
        self.assertIsNone(out["recommendation"]["recommended_worker"])
        self.assertNotEqual(out["recommendation"]["recommended_worker"], "cursor")


class LearningActorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self._outcomes = learning.OUTCOMES_PATH
        self._weights = learning.WEIGHTS_PATH
        self._stats = stats_store.STATS_PATH
        self._summary = stats_store.SUMMARY_PATH
        learning.OUTCOMES_PATH = base / "outcomes.jsonl"
        learning.WEIGHTS_PATH = base / "weights.json"
        stats_store.STATS_PATH = base / "stats.json"
        stats_store.SUMMARY_PATH = base / "stats-summary.json"

    def tearDown(self) -> None:
        learning.OUTCOMES_PATH = self._outcomes
        learning.WEIGHTS_PATH = self._weights
        stats_store.STATS_PATH = self._stats
        stats_store.SUMMARY_PATH = self._summary
        self.tmp.cleanup()

    def test_outcome_without_actor_never_counts_as_human(self) -> None:
        rec = learning.record_outcome(
            "wi_x",
            human_passed=True,
            human_rating=4,
            notes="no actor",
            source="owner_ui",
        )
        self.assertIn(rec.get("actor"), (None, ""))
        self.assertEqual(rec.get("source"), "synthetic")
        self.assertEqual(rec.get("effective_source"), "synthetic")
        self.assertTrue(rec.get("synthetic"))
        self.assertFalse(learning.is_real_human_outcome(rec))
        stats = stats_store.recompute()
        self.assertEqual(stats["outcomes_total"], 1)
        self.assertEqual(stats["outcomes_human"], 0)
        self.assertEqual(stats["human_passes"], 0)
        weights = json.loads(learning.WEIGHTS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(weights["models"], {})

    def test_outcome_with_actor_counts_as_human(self) -> None:
        rec = learning.record_outcome(
            "wi_y",
            human_passed=True,
            human_rating=4,
            actor="matt",
            source="owner_ui",
        )
        self.assertEqual(rec.get("actor"), "matt")
        self.assertEqual(rec.get("source"), "owner_ui")
        self.assertEqual(rec.get("effective_source"), "human")
        self.assertTrue(learning.is_real_human_outcome(rec))
        stats = stats_store.recompute()
        self.assertEqual(stats["outcomes_human"], 1)
        self.assertEqual(stats["human_passes"], 1)

    def test_existing_actorless_rows_recompute_to_zero(self) -> None:
        rows = [
            {"effective_source": "human", "human_passed": True, "notes": "human wins", "source": None},
            {"effective_source": "human_passed_bool", "human_passed": True, "notes": "harden human pass sample"},
            {"effective_source": "human", "human_passed": True, "actor": "", "source": "owner_ui", "notes": "owner ui harden test"},
        ]
        learning.OUTCOMES_PATH.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )
        stats = stats_store.recompute()
        self.assertEqual(stats["outcomes_total"], 3)
        self.assertEqual(stats["outcomes_human"], 0)
        self.assertEqual(stats["human_passes"], 0)


class OwnerUiAuthTests(unittest.TestCase):
    TOKEN = "ui-test-tok"

    def setUp(self) -> None:
        from wolf_intelligence import owner_ui_server

        self._env = os.environ.copy()
        os.environ.pop(paths.UI_TOKEN_ENV, None)
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self._outcomes = learning.OUTCOMES_PATH
        self._weights = learning.WEIGHTS_PATH
        self._stats = stats_store.STATS_PATH
        self._summary = stats_store.SUMMARY_PATH
        self._audit_dir = owner_ui_server.AUDIT_DIR
        self.ui = owner_ui_server
        learning.OUTCOMES_PATH = base / "outcomes.jsonl"
        learning.WEIGHTS_PATH = base / "weights.json"
        stats_store.STATS_PATH = base / "stats.json"
        stats_store.SUMMARY_PATH = base / "stats-summary.json"
        owner_ui_server.AUDIT_DIR = base / "audit"
        owner_ui_server.AUDIT_DIR.mkdir()
        self.addCleanup(self._restore_ui_globals)
        from wolf_intelligence.owner_ui_server import Handler, ReuseHTTPServer

        try:
            self.server = ReuseHTTPServer(("127.0.0.1", 0), Handler)
        except OSError as exc:
            raise unittest.SkipTest(f"socket bind denied: {exc}") from exc
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown_server)
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def _shutdown_server(self) -> None:
        if not hasattr(self, "server"):
            return
        self.server.shutdown()
        self.server.server_close()
        if hasattr(self, "thread"):
            self.thread.join(timeout=3)

    def _restore_ui_globals(self) -> None:
        learning.OUTCOMES_PATH = self._outcomes
        learning.WEIGHTS_PATH = self._weights
        stats_store.STATS_PATH = self._stats
        stats_store.SUMMARY_PATH = self._summary
        self.ui.AUDIT_DIR = self._audit_dir
        os.environ.clear()
        os.environ.update(self._env)
        if hasattr(self, "tmp"):
            self.tmp.cleanup()

    def test_missing_host_header_refused(self) -> None:
        host, port = self.server.server_address
        sock = socket.create_connection((host, port))
        sock.sendall(b"GET /api/health HTTP/1.0\r\n\r\n")
        resp = sock.recv(4096)
        sock.close()
        self.assertIn(b"403", resp.split(b"\r\n", 1)[0])

    def test_host_allowed_requires_loopback_pin(self) -> None:
        port = 18765
        self.assertFalse(self.ui.host_allowed({}, port))
        self.assertTrue(self.ui.host_allowed({"Host": f"127.0.0.1:{port}"}, port))

    def _post(self, body: dict, headers: dict | None = None):
        host, port = self.server.server_address
        req = urllib.request.Request(
            f"http://{host}:{port}/api/human-decision",
            data=json.dumps(body).encode(),
            headers=headers or {},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, exc.read()

    def _raw(self, method: str, path: str, headers: dict | None = None, body: bytes | None = None):
        host, port = self.server.server_address
        conn = http.client.HTTPConnection(host, port, timeout=3)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            resp = conn.getresponse()
            return resp.status, {k.lower(): v for k, v in resp.getheaders()}, resp.read()
        finally:
            conn.close()

    def test_board_get_needs_token(self) -> None:
        os.environ[paths.UI_TOKEN_ENV] = self.TOKEN
        for p in ("/api/owner-board", "/api/wolf-intelligence/board"):
            code, _h, raw = self._raw("GET", p)
            self.assertEqual(code, 401, p)
            self.assertNotIn(b"NEEDS_YOU", raw)
            code, _h, _raw = self._raw("GET", p, {"Authorization": "Bearer wrong-token"})
            self.assertEqual(code, 401, p)
        code, _h, raw = self._raw("GET", "/api/owner-board", {"Authorization": "Bearer " + self.TOKEN})
        self.assertEqual(code, 200, raw)
        board = json.loads(raw.decode())
        self.assertIn("_tech", board)
        code, _h, _raw = self._raw("GET", "/api/owner-board", {"X-Wolf-Session": self.TOKEN})
        self.assertEqual(code, 200)
        log = (self.ui.AUDIT_DIR / "owner-ui-access.log").read_text(encoding="utf-8")
        self.assertNotIn(self.TOKEN, log)

    def test_board_closed_when_token_unset(self) -> None:
        os.environ.pop(paths.UI_TOKEN_ENV, None)
        code, _h, _raw = self._raw("GET", "/api/owner-board", {"Authorization": "Bearer anything"})
        self.assertEqual(code, 401)

    def test_no_wildcard_cors_on_any_response(self) -> None:
        os.environ[paths.UI_TOKEN_ENV] = self.TOKEN
        auth = {"Authorization": "Bearer " + self.TOKEN}
        for method, p, hdrs in (
            ("GET", "/", {}),
            ("GET", "/api/health", {}),
            ("GET", "/api/owner-board", {}),
            ("GET", "/api/owner-board", auth),
            ("GET", "/nope", {}),
            ("POST", "/api/human-decision", {}),
        ):
            code, headers, _raw = self._raw(method, p, hdrs, b"{}" if method == "POST" else None)
            self.assertNotIn("access-control-allow-origin", headers, (method, p, code))

    def test_foreign_host_is_403_even_with_token(self) -> None:
        os.environ[paths.UI_TOKEN_ENV] = self.TOKEN
        port = self.server.server_address[1]
        auth = {"Authorization": "Bearer " + self.TOKEN}
        for host in (f"evil.example:{port}", "evil.example", f"127.0.0.1:{port + 1}", f"192.168.1.5:{port}"):
            code, _h, raw = self._raw("GET", "/api/owner-board", {**auth, "Host": host})
            self.assertEqual(code, 403, host)
            self.assertNotIn(b"NEEDS_YOU", raw)
            code, _h, _raw = self._raw("GET", "/api/health", {"Host": host})
            self.assertEqual(code, 403, host)
            code, _h, _raw = self._raw(
                "POST", "/api/human-decision", {**auth, "Host": host},
                json.dumps({"work_item_id": "wi", "decision": "PASS", "actor": "matt"}).encode(),
            )
            self.assertEqual(code, 403, host)
        code, _h, _raw = self._raw("GET", "/api/owner-board", {**auth, "Host": f"localhost:{port}"})
        self.assertEqual(code, 200)

    def test_cross_origin_is_403(self) -> None:
        os.environ[paths.UI_TOKEN_ENV] = self.TOKEN
        port = self.server.server_address[1]
        auth = {"Authorization": "Bearer " + self.TOKEN}
        code, _h, _raw = self._raw("GET", "/api/owner-board", {**auth, "Origin": "http://evil.example"})
        self.assertEqual(code, 403)
        code, _h, _raw = self._raw("GET", "/api/owner-board", {**auth, "Origin": "http://127.0.0.1:8788"})
        self.assertEqual(code, 403)
        code, _h, _raw = self._raw(
            "POST", "/api/human-decision", {**auth, "Origin": "http://evil.example"},
            json.dumps({"work_item_id": "wi", "decision": "PASS", "actor": "matt"}).encode(),
        )
        self.assertEqual(code, 403)
        code, _h, _raw = self._raw("GET", "/api/owner-board", {**auth, "Origin": f"http://127.0.0.1:{port}"})
        self.assertEqual(code, 200)

    def test_no_token_gives_401(self) -> None:
        os.environ.pop(paths.UI_TOKEN_ENV, None)
        code, raw = self._post({"work_item_id": "wi", "decision": "PASS", "actor": "matt"})
        self.assertEqual(code, 401)
        self.assertNotIn(self.TOKEN.encode(), raw)
        log = (self.ui.AUDIT_DIR / "owner-ui-access.log").read_text(encoding="utf-8")
        self.assertNotIn(self.TOKEN, log)

    def test_wrong_token_gives_401(self) -> None:
        os.environ[paths.UI_TOKEN_ENV] = self.TOKEN
        code, raw = self._post(
            {"work_item_id": "wi", "decision": "PASS", "actor": "matt"},
            {"Authorization": "Bearer wrong-token"},
        )
        self.assertEqual(code, 401)
        self.assertNotIn(self.TOKEN.encode(), raw)
        log = (self.ui.AUDIT_DIR / "owner-ui-access.log").read_text(encoding="utf-8")
        self.assertNotIn(self.TOKEN, log)
        self.assertNotIn("wrong-token", log)

    def test_right_token_gives_200(self) -> None:
        from wolf_intelligence import work_items
        os.environ[paths.UI_TOKEN_ENV] = self.TOKEN
        wi = work_items.create(title="ui auth unit", kind="review", isolated_safe=True)
        code, raw = self._post(
            {"work_item_id": wi["id"], "decision": "PASS", "actor": "matt"},
            {"Authorization": "Bearer " + self.TOKEN},
        )
        self.assertEqual(code, 200, raw)
        body = json.loads(raw.decode())
        self.assertTrue(body["ok"])
        rows = [
            json.loads(line)
            for line in learning.OUTCOMES_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertTrue(any(row.get("actor") == "matt" and row.get("source") == "owner_ui" for row in rows))
        log = (self.ui.AUDIT_DIR / "owner-ui-access.log").read_text(encoding="utf-8")
        self.assertNotIn(self.TOKEN, log)

    def test_right_token_without_actor_is_400(self) -> None:
        from wolf_intelligence import work_items
        os.environ[paths.UI_TOKEN_ENV] = self.TOKEN
        wi = work_items.create(title="ui actor required", kind="review", isolated_safe=True)
        code, _raw = self._post(
            {"work_item_id": wi["id"], "decision": "PASS"},
            {"Authorization": "Bearer " + self.TOKEN},
        )
        self.assertEqual(code, 400)

    def test_suite_has_no_pytest_dependency(self) -> None:
        text = Path(__file__).read_text(encoding="utf-8")
        imports = [
            line.strip()
            for line in text.splitlines()
            if line.startswith("import ") or line.startswith("from ")
        ]
        self.assertTrue(imports)
        self.assertFalse(any("pytest" in line for line in imports))


if __name__ == "__main__":
    unittest.main()
