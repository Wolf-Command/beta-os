"""Gemini: CONNECTED / BILLING UNVERIFIED / SPEND BLOCKED (Owner order 2026-10-06 09:39, Vesper B4-1).

Proves every Gemini execution path in wolf_intelligence passes the single canonical spend gate
(live_gate.gemini_spend_gate == the f7c78f2 cap policy) and is DENIED before any provider call,
including dispatch, retry, fallback, the benchmark harness, and a registry 'free' declaration.
No network: urlopen is patched to fail the test if reached.
"""
from __future__ import annotations

import ast
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from wolf_intelligence import paths, real_evidence, routing_policy, worker_registry
from wolf_intelligence.adapters import ADAPTER_REGISTRY, live_gate
from wolf_intelligence.adapters.gemini import GeminiAdapter
from wolf_intelligence.real_dispatch import dispatch_real

if paths.STATE_ROOT == paths.LIVE_STATE_ROOT or str(paths.STATE_ROOT).startswith("/Users/wolfterminal/beta-os"):
    raise RuntimeError("refusing to run tests against live Wolf Intelligence state")

PKG = Path(__file__).resolve().parents[1]
STATE = "CONNECTED / BILLING UNVERIFIED / SPEND BLOCKED"


def _boom(*_a, **_k):
    raise AssertionError("a Gemini provider endpoint was reached")


class GeminiGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = os.environ.copy()
        self.real = tempfile.mkdtemp(prefix="wi-test-gemini-real-")
        os.environ.update({"WOLF_INTELLIGENCE_LIVE_SUBMIT": "1", "GEMINI_API_KEY": "unit-test-gemini-key",
                           "WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT": self.real})
        for k in ("WOLF_INTELLIGENCE_MAX_COST_USD", "WOLF_INTELLIGENCE_MAX_DAILY_COST_USD", "WOLF_INTELLIGENCE_PROVIDER_MOCK"):
            os.environ.pop(k, None)
        p1 = mock.patch("urllib.request.urlopen", side_effect=_boom)
        p2 = mock.patch("wolf_intelligence.adapters.live_gate.urllib.request.urlopen", side_effect=_boom)
        p3 = mock.patch("wolf_intelligence.adapters.subscription_cli.urllib.request.urlopen", side_effect=_boom)
        for p in (p1, p2, p3):
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self.real, ignore_errors=True)

    def _assert_denied(self, res) -> None:
        self.assertFalse(res.ok if hasattr(res, "ok") else res.get("ok"))
        status = res.status if hasattr(res, "status") else res.get("status")
        msg = res.message if hasattr(res, "message") else res.get("message")
        self.assertEqual(status, "GATED")
        self.assertIn(live_gate.OWNER_ACTION_REQUIRED, msg)
        data = res.data if hasattr(res, "data") else res
        self.assertFalse(data.get("provider_called"))

    def test_registry_state_string_exact(self):
        self.assertEqual(worker_registry.WORKERS["gemini_free"]["state"], STATE)
        self.assertEqual(live_gate.GEMINI_STATE, STATE)
        self.assertEqual(worker_registry.WORKERS["gemini_free"]["billing_status"], "UNVERIFIED")

    def test_free_path_adapter_denied_every_allowlisted_model(self):
        a = ADAPTER_REGISTRY["gemini_free"]
        for model in ("gemini-flash-latest", "gemini-flash-lite-latest"):
            with self.subTest(model=model):
                self._assert_denied(a.submit({"execute": True, "prompt": "hi", "model": model}))

    def test_free_path_denied_even_with_owner_caps_but_unverified_prices(self):
        os.environ["WOLF_INTELLIGENCE_MAX_COST_USD"] = "0.5"
        os.environ["WOLF_INTELLIGENCE_MAX_DAILY_COST_USD"] = "1.0"
        self._assert_denied(ADAPTER_REGISTRY["gemini_free"].submit({"execute": True, "prompt": "hi"}))
        self._assert_denied(GeminiAdapter().submit({"execute": True, "prompt": "hi", "model": "gemini-2.0-flash"}))

    def test_registry_free_declaration_is_not_a_bypass(self):
        patched = dict(worker_registry.WORKERS["gemini_free"], billing_status="VERIFIED_FREE", billing_status_evidence="x")
        with mock.patch.dict(worker_registry.WORKERS, {"gemini_free": patched}):
            self._assert_denied(ADAPTER_REGISTRY["gemini_free"].submit({"execute": True, "prompt": "hi"}))

    def test_legacy_gemini_adapter_denied(self):
        self._assert_denied(GeminiAdapter().submit({"execute": True, "prompt": "hi"}))

    def test_dispatch_and_retry_denied_without_fallback(self):
        for attempt in range(3):  # a caller retrying re-enters the same gate every time
            r = dispatch_real("gemini_free", "hi", purpose=f"test-retry-{attempt}", task_class="coding")
            self.assertEqual(r["status"], "GATED")
            self.assertFalse(r["provider_called"])
            self.assertFalse(r["fallback_used"])
        recs = [x for x in real_evidence.read("dispatch") if x.get("worker") == "gemini_free"]
        self.assertEqual(len(recs), 3)
        self.assertTrue(all(x["status"] == "GATED" for x in recs))
        self.assertEqual({x.get("worker") for x in real_evidence.read("dispatch")}, {"gemini_free"})  # no fallback worker

    def test_fallback_never_lands_on_gemini(self):
        # a failing primary must not fall back to Gemini: dispatch has no fallback, routing excludes unverified billing
        with mock.patch.object(ADAPTER_REGISTRY["claude_pro_sub"], "preflight",
                               return_value=live_gate.AdapterResult(False, "UNAVAILABLE", "test")):
            r = dispatch_real("claude_pro_sub", "hi", purpose="test-fallback", task_class="coding")
        self.assertFalse(r["ok"])
        self.assertNotIn("gemini_free", {x.get("worker") for x in real_evidence.read("dispatch")})
        policy = {"task_classes": {"coding": {"order": ["gemini_free", "codex_sub"]}}}
        registry = {"workers": {"gemini_free": {"routable": True}, "codex_sub": {"routable": True}}}
        self.assertEqual(routing_policy.route("coding", policy, registry), ["codex_sub"])

    def test_gen1_harness_does_not_use_gemini(self):
        from wolf_intelligence.real_bench import runner
        self.assertNotIn("gemini_free", runner.REVIEWERS)

    def test_static_audit_every_endpoint_is_behind_the_gate(self):
        """Every file in wolf_intelligence that names a Gemini endpoint or SDK must call gemini_spend_gate
        before the endpoint appears, and no google SDK import exists."""
        hits = []
        for f in PKG.rglob("*.py"):
            if "tests" in f.parts:
                continue
            src = f.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"import\s+google\.(genai|generativeai)|from\s+google\s+import\s+genai", src), f)
            for m in re.finditer(r"https://generativelanguage\.googleapis\.com", src):
                hits.append(f.name)
                gate_pos = src.rfind("gemini_spend_gate(", 0, m.start())
                self.assertNotEqual(gate_pos, -1, f"{f}: endpoint at offset {m.start()} not preceded by gemini_spend_gate")
        self.assertEqual(sorted(hits), ["gemini.py", "subscription_cli.py"])

    # ---- red-team follow-ups (Cursor review 09:55, evidence b4-1-review/cursor-redteam.txt) ----

    def test_static_audit_gate_in_same_function_before_endpoint(self):
        """AST check (not text position): the function that builds a Gemini endpoint URL must itself call
        gemini_spend_gate, return on refusal, and do so on an earlier line than the URL."""
        checked = 0
        for f in PKG.rglob("*.py"):
            if "tests" in f.parts:
                continue
            tree = ast.parse(f.read_text(encoding="utf-8"))
            for fn in ast.walk(tree):
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                url_lines = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                             and "generativelanguage.googleapis.com" in n.value]
                if not url_lines:
                    continue
                checked += 1
                gate_lines = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Call)
                              and getattr(n.func, "id", getattr(n.func, "attr", "")) == "gemini_spend_gate"]
                self.assertTrue(gate_lines, f"{f.name}:{fn.name} builds a Gemini URL without calling gemini_spend_gate")
                self.assertLess(min(gate_lines), min(url_lines), f"{f.name}:{fn.name} gate must precede the URL")
                returns = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Return) and min(gate_lines) < n.lineno < min(url_lines)]
                self.assertTrue(returns, f"{f.name}:{fn.name} has no early return between gate and URL")
        self.assertEqual(checked, 2)

    def test_gate_denies_even_if_cost_cap_would_allow(self):
        """A future verified price row (cost cap allows) must not re-open spend while billing is UNVERIFIED."""
        with mock.patch.object(live_gate, "enforce_cost_cap", return_value=(None, 1.0, 0.01)) as cap:
            res, c, e = live_gate.gemini_spend_gate({"execute": True}, model_id="gemini-flash-latest", prompt="hi",
                                                    max_output_tokens=10)
            self._assert_denied(res)
            self.assertEqual(res.data["denied_by"], "billing_unverified")
            self.assertIsNone(c)
            cap.assert_not_called()
            self._assert_denied(ADAPTER_REGISTRY["gemini_free"].submit({"execute": True, "prompt": "hi"}))
            self._assert_denied(GeminiAdapter().submit({"execute": True, "prompt": "hi"}))

    def test_verified_without_evidence_is_still_unverified(self):
        patched = dict(worker_registry.WORKERS["gemini_free"], billing_status="VERIFIED", billing_status_evidence=None)
        with mock.patch.dict(worker_registry.WORKERS, {"gemini_free": patched}):
            self.assertTrue(worker_registry.billing_unverified("gemini_free"))
            self.assertFalse(worker_registry.gemini_billing_verified())
            self._assert_denied(ADAPTER_REGISTRY["gemini_free"].submit({"execute": True, "prompt": "hi"}))

    def test_gemini_paid_unverified_and_never_routed(self):
        self.assertEqual(worker_registry.WORKERS["gemini_paid"]["state"], STATE)
        self.assertTrue(worker_registry.billing_unverified("gemini_paid"))
        policy = {"task_classes": {"coding": {"order": ["gemini_paid", "gemini_free", "codex_sub"]}}}
        registry = {"workers": {w: {"routable": True} for w in ("gemini_paid", "gemini_free", "codex_sub")}}
        self.assertEqual(routing_policy.route("coding", policy, registry), ["codex_sub"])

    def test_unknown_google_worker_defaults_unverified(self):
        with mock.patch.dict(worker_registry.WORKERS, {"gemini_new": {"provider_family": "google"}}):
            self.assertTrue(worker_registry.billing_unverified("gemini_new"))

    def test_legacy_worker_id_dispatch_denied(self):
        for wid in ("gemini", "gemini_free"):
            with self.subTest(worker=wid):
                r = dispatch_real(wid, "hi", purpose="test-legacy-id", task_class="coding")
                self.assertFalse(r["ok"])
                self.assertFalse(r.get("provider_called"))
                self.assertFalse(r.get("fallback_used"))
                # legacy id has no dispatch path at all (REFUSED unknown worker); the free id is GATED by the spend gate
                self.assertEqual(r["status"], "REFUSED" if wid == "gemini" else "GATED")

    def test_provider_mock_env_is_not_a_bypass(self):
        os.environ["WOLF_INTELLIGENCE_PROVIDER_MOCK"] = "1"
        self._assert_denied(ADAPTER_REGISTRY["gemini_free"].submit({"execute": True, "prompt": "hi"}))
        self._assert_denied(GeminiAdapter().submit({"execute": True, "prompt": "hi"}))

    def test_real_bench_default_workers_exclude_gemini(self):
        from wolf_intelligence.real_bench import runner
        src = Path(runner.__file__).read_text(encoding="utf-8")
        m = re.search(r'"--workers"[^\n]*default=([^\n]+)', src)
        self.assertIsNotNone(m)
        self.assertNotIn("gemini", m.group(1))

    def test_preflight_does_not_authorize(self):
        pf = ADAPTER_REGISTRY["gemini_free"].preflight()
        self.assertEqual(pf.data.get("state"), STATE)
        self.assertTrue(pf.data.get("spend_blocked"))
        self.assertFalse(pf.data.get("authorizes_calls"))


if __name__ == "__main__":
    unittest.main()
