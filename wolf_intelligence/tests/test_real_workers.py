"""Tests for the REAL worker path: billing separation, gating, evidence isolation, routing, graders.

No provider is called: subprocess/HTTP are mocked. State and REAL evidence roots are temp dirs.
"""
from __future__ import annotations

# --- State isolation (Vesper M1) — must run before any wolf_intelligence import.
import atexit as _atexit
import os as _os
import shutil as _shutil
import sys as _sys
import tempfile as _tempfile

if not _os.environ.get("WI_TEST_STATE_ISOLATED"):
    if "wolf_intelligence.paths" in _sys.modules:
        raise RuntimeError("wolf_intelligence.paths imported before test state isolation")
    _TEST_STATE_ROOT = _tempfile.mkdtemp(prefix="wi-test-state-")
    _os.environ["WOLF_INTELLIGENCE_STATE_ROOT"] = _TEST_STATE_ROOT
    _os.environ["WI_TEST_STATE_ISOLATED"] = _TEST_STATE_ROOT
    _atexit.register(_shutil.rmtree, _TEST_STATE_ROOT, True)
_REAL_TMP = _tempfile.mkdtemp(prefix="wi-test-real-")
_os.environ["WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT"] = _REAL_TMP
_atexit.register(_shutil.rmtree, _REAL_TMP, True)
# ---------------------------------------------------------------------------

import json
import os
import unittest
from pathlib import Path
from unittest import mock

from wolf_intelligence import paths, real_evidence, routing_policy, worker_registry
from wolf_intelligence.adapters import ADAPTER_REGISTRY
from wolf_intelligence.adapters import subscription_cli as sc
from wolf_intelligence.adapters.base import AdapterResult
from wolf_intelligence.real_dispatch import dispatch_real

if paths.STATE_ROOT == paths.LIVE_STATE_ROOT or str(paths.STATE_ROOT).startswith("/Users/wolfterminal/beta-os"):
    raise RuntimeError("refusing to run tests against live Wolf Intelligence state")

FAKE_KEY = "fake-value-for-test-only"


def _fresh_real_root(tc: unittest.TestCase) -> Path:
    d = Path(_tempfile.mkdtemp(prefix="wi-test-real-case-"))
    p = mock.patch.dict(os.environ, {"WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT": str(d)})
    p.start()
    tc.addCleanup(p.stop)
    tc.addCleanup(_shutil.rmtree, d, True)
    return d


class RealEvidenceStoreTests(unittest.TestCase):
    def test_refuses_live_state_and_beta_tree(self):
        for bad in (str(paths.LIVE_STATE_ROOT), str(paths.LIVE_STATE_ROOT / "real"), str(paths.BETA_ROOT / "state" / "x")):
            with mock.patch.dict(os.environ, {"WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT": bad}):
                with self.assertRaises(real_evidence.RealEvidenceError):
                    real_evidence.root()

    def test_records_are_real_and_synthetic_rows_ignored(self):
        root = _fresh_real_root(self)
        real_evidence.append("dispatch", {"worker": "x", "ok": True})
        with (root / "records" / "dispatch.jsonl").open("a") as fh:
            fh.write(json.dumps({"worker": "y", "evidence_class": "SYNTHETIC", "synthetic": True}) + "\n")
        rows = real_evidence.read("dispatch")
        self.assertEqual([r["worker"] for r in rows], ["x"])
        self.assertEqual(rows[0]["evidence_class"], "REAL")

    def test_secret_shaped_record_refused(self):
        _fresh_real_root(self)
        with self.assertRaises(real_evidence.RealEvidenceError):
            real_evidence.append("dispatch", {"note": "sk-ant-" + "a" * 30})

    def test_artifact_redacts(self):
        root = _fresh_real_root(self)
        rel = real_evidence.write_artifact("raw/t.txt", "token AIza" + "b" * 35)
        self.assertNotIn("AIza", (root / rel).read_text())


class BillingSeparationTests(unittest.TestCase):
    def test_scrubbed_env_drops_every_provider_key(self):
        env = {k: FAKE_KEY for k in sc.ALL_PROVIDER_KEYS}
        with mock.patch.dict(os.environ, env):
            child = sc.scrubbed_env()
        for k in sc.ALL_PROVIDER_KEYS:
            self.assertNotIn(k, child)

    def test_claude_preflight_refuses_api_key_auth(self):
        a = ADAPTER_REGISTRY["claude_pro_sub"]
        status = json.dumps({"loggedIn": True, "authMethod": "api_key", "apiKeySource": "ANTHROPIC_API_KEY"})
        with mock.patch.object(sc, "_run", return_value=(0, status, "", 5.0, None)):
            pf = a.preflight()
        self.assertFalse(pf.ok)
        self.assertEqual(pf.status, "BILLING_MISMATCH")

    def test_claude_live_child_env_has_no_api_key_even_if_parent_does(self):
        a = ADAPTER_REGISTRY["claude_pro_sub"]
        seen = []
        status = json.dumps({"loggedIn": True, "authMethod": "claude.ai", "subscriptionType": "pro", "email": "e"})
        reply = json.dumps({"result": "OK", "modelUsage": {"m": {}}, "is_error": False})

        def fake_run(argv, *, env, cwd, timeout, stdin=None, worker_id=None):
            seen.append((argv, env))
            return (0, status if "auth" in argv else reply, "", 1.0, None)

        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": FAKE_KEY, "WOLF_INTELLIGENCE_LIVE_SUBMIT": "1"}), \
                mock.patch.object(sc, "_run", side_effect=fake_run):
            res = a.submit({"execute": True, "prompt": "hi"})
        self.assertTrue(res.ok)
        self.assertTrue(seen)
        for argv, env in seen:
            self.assertNotIn("ANTHROPIC_API_KEY", env)
            self.assertNotIn("--dangerously-skip-permissions", argv)
        self.assertEqual(res.data["billing_class"], "subscription")

    def test_codex_argv_forces_chatgpt_and_scrubs_openai_key(self):
        a = ADAPTER_REGISTRY["codex_sub"]
        seen = []

        def fake_run(argv, *, env, cwd, timeout, stdin=None, worker_id=None):
            seen.append((argv, env))
            if "exec" in argv:
                Path(argv[argv.index("-o") + 1]).write_text("OK")
            return (0, "Logged in using ChatGPT" if "login" in argv else "", "", 1.0, None)

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": FAKE_KEY, "CODEX_API_KEY": FAKE_KEY, "WOLF_INTELLIGENCE_LIVE_SUBMIT": "1"}), \
                mock.patch.object(sc, "_run", side_effect=fake_run), \
                mock.patch.object(sc.CodexSubAdapter, "preflight", return_value=AdapterResult(True, "CONNECTED", "ok", {})):
            res = a.submit({"execute": True, "prompt": "hi"})
        self.assertTrue(res.ok, res.message)
        argv, env = seen[-1]
        self.assertIn('forced_login_method="chatgpt"', argv)
        self.assertIn("--ignore-user-config", argv)
        self.assertEqual(argv[argv.index("-s") + 1], "read-only")
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("CODEX_API_KEY", env)

    def test_cursor_refuses_unscoped_workspace(self):
        for bad in (str(Path.home()), "/", "/Users", "/Users/wolfterminal/beta-os"):
            with self.assertRaises(ValueError):
                sc.safe_workspace(bad, "x")

    def test_gemini_refuses_non_free_model(self):
        a = ADAPTER_REGISTRY["gemini_free"]
        with mock.patch.dict(os.environ, {"WOLF_INTELLIGENCE_LIVE_SUBMIT": "1", "GEMINI_API_KEY": FAKE_KEY}):
            res = a.submit({"execute": True, "prompt": "hi", "model": "gemini-3-pro"})
        self.assertFalse(res.ok)
        self.assertEqual(res.status, "REFUSED")

    def test_live_flag_required(self):
        a = ADAPTER_REGISTRY["ollama_local"]
        with mock.patch.dict(os.environ, {"WOLF_INTELLIGENCE_LIVE_SUBMIT": ""}):
            res = a.submit({"execute": True, "prompt": "hi"})
        self.assertEqual(res.status, "LIVE_DISABLED")


class DispatchGatingTests(unittest.TestCase):
    def test_metered_workers_gated_without_owner_approval(self):
        _fresh_real_root(self)
        for w in ("anthropic_api", "openai_api", "xai_api", "gemini_paid"):
            boom = mock.Mock(side_effect=AssertionError("provider must not be called"))
            with mock.patch.dict(ADAPTER_REGISTRY, {}), mock.patch.object(ADAPTER_REGISTRY.get("anthropic_api"), "submit", boom):
                r = dispatch_real(w, "hi", purpose="test")
            self.assertEqual(r["status"], "GATED")
            self.assertFalse(r["ok"])
            self.assertFalse(r.get("provider_called"))

    def test_no_fallback_on_failure(self):
        _fresh_real_root(self)
        fail = AdapterResult(False, "ERROR", "down", {"provider_called": True})
        others = {w: mock.patch.object(ADAPTER_REGISTRY[w], "submit", side_effect=AssertionError("fallback!"))
                  for w in ("codex_sub", "cursor_sub", "gemini_free", "ollama_local", "anthropic_api")}
        for p in others.values():
            p.start()
            self.addCleanup(p.stop)
        with mock.patch.object(ADAPTER_REGISTRY["claude_pro_sub"], "submit", return_value=fail):
            r = dispatch_real("claude_pro_sub", "hi", purpose="test")
        self.assertFalse(r["ok"])
        self.assertFalse(r["fallback_used"])

    def test_grok_is_pull_only(self):
        _fresh_real_root(self)
        r = dispatch_real("grok_bot_sub", "hi", purpose="test", request_id="rq-test1")
        self.assertEqual(r["status"], "QUEUED_FOR_PULL")
        self.assertFalse(r["ok"])
        self.assertEqual(ADAPTER_REGISTRY["grok_bot_sub"].result("rq-test1").status, "PENDING")


class RegistryRoutingTests(unittest.TestCase):
    def test_every_billing_path_is_its_own_worker(self):
        ids = set(worker_registry.WORKERS)
        for w in ("claude_pro_sub", "anthropic_api", "codex_sub", "openai_api", "cursor_sub", "grok_bot_sub",
                  "xai_api", "gemini_free", "gemini_paid", "ollama_local"):
            self.assertIn(w, ids)
        for w, d in worker_registry.WORKERS.items():
            if d["billing_class"] == worker_registry.METERED:
                self.assertTrue(d["gated"], w)

    def test_snapshot_has_no_secrets_and_metered_not_routable(self):
        _fresh_real_root(self)
        reg = worker_registry.build(live_preflight=False)
        self.assertFalse(real_evidence.contains_secret(json.dumps(reg)))
        for w, r in reg["workers"].items():
            if worker_registry.is_metered(w):
                self.assertFalse(r["routable"])

    def test_policy_uses_real_only_and_never_routes_metered(self):
        root = _fresh_real_root(self)
        real_evidence.append("bench_runs", {"task_class": "coding", "worker": "codex_sub", "quality_score": 0.9, "completion": "COMPLETED", "latency_ms": 10})
        real_evidence.append("bench_runs", {"task_class": "coding", "worker": "anthropic_api", "quality_score": 1.0, "completion": "COMPLETED", "latency_ms": 1})
        with (root / "records" / "bench_runs.jsonl").open("a") as fh:
            fh.write(json.dumps({"task_class": "coding", "worker": "ollama_local", "quality_score": 1.0, "evidence_class": "SYNTHETIC", "synthetic": True}) + "\n")
        pol = routing_policy.learn()
        order = pol["task_classes"]["coding"]["order"]
        self.assertEqual(order, ["codex_sub"])
        self.assertIn("n=1", pol["task_classes"]["coding"]["confidence"])
        reg = {"workers": {"codex_sub": {"routable": True}, "anthropic_api": {"routable": True}}}
        self.assertEqual(routing_policy.route("coding", pol, reg), ["codex_sub"])


class GraderTests(unittest.TestCase):
    def test_reference_answers_score_full(self):
        from wolf_intelligence.real_bench import tasks_a as A, tasks_b as B
        fin = {"ggv_bank_closing_rp": 141275000, "variance_bank_minus_books_rp": 420000,
               "variance_components": [{"type": "deposit in transit", "rp": 300000}, {"type": "transposition", "rp": 720000}],
               "ggv_revenue_rp": 28550000, "ggv_operating_net_rp": 24225000,
               "intercompany_at_5_oct": {"BZG_owes_GGV_rp": 7500000, "AMG_owes_GGV_rp": 3000000},
               "misattributed_statement_lines": [3, 7]}
        self.assertEqual(A.grade_finance(json.dumps(fin))["quality_score"], 1.0)
        self.assertEqual(str(B.optimal_golive()), "2026-10-21")
        bad = "```python\ndef allocate_service_charge(t, p):\n    s = sum(p.values())\n    return {k: round(t*v/s) for k, v in p.items()}\n```"
        self.assertLess(A.grade_coding(bad)["quality_score"], 0.5)

    def test_decoy_flag_is_penalised(self):
        from wolf_intelligence.real_bench import tasks_a as A
        all_hits = [{"line": l} for l in (10, 37, 43, 58, 62)]
        clean = A.grade_security(json.dumps({"findings": all_hits}))["quality_score"]
        noisy = A.grade_security(json.dumps({"findings": all_hits + [{"line": A.SEC_DECOYS["subprocess_list_args"][0]}]}))["quality_score"]
        self.assertGreater(clean, noisy)


if __name__ == "__main__":
    unittest.main()
