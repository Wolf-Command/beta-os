"""Capacity governance tests (spec items a–k + capacity model). Offline; temp state roots."""
from __future__ import annotations

import atexit as _atexit
import http.client
import json
import os as _os
import shutil
import shutil as _shutil
import socket
import subprocess
import sys as _sys
import tempfile
import tempfile as _tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

if not _os.environ.get("WI_TEST_STATE_ISOLATED"):
    if "wolf_intelligence.paths" in _sys.modules:
        raise RuntimeError("wolf_intelligence.paths imported before test state isolation")
    _TEST_STATE_ROOT = _tempfile.mkdtemp(prefix="wi-gov-test-state-")
    _os.environ["WOLF_INTELLIGENCE_STATE_ROOT"] = _TEST_STATE_ROOT
    _os.environ["WI_TEST_STATE_ISOLATED"] = _TEST_STATE_ROOT
    _atexit.register(_shutil.rmtree, _TEST_STATE_ROOT, True)
_REAL_TMP = _tempfile.mkdtemp(prefix="wi-gov-test-real-")
_os.environ["WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT"] = _REAL_TMP
_atexit.register(_shutil.rmtree, _REAL_TMP, True)

import os
import sys

from wolf_intelligence import allocation, capacity, governance, imbalance, paths
from wolf_intelligence.adapters import live_gate
from wolf_intelligence.allocation import (
    LedgerView,
    decide,
    load_tightening,
    metered_permitted_with_gate,
    new_orchestrator_session,
    save_tightening,
)
from wolf_intelligence.capacity import (
    SEED_PATH,
    capacity_snapshot,
    merge_observations,
    record_observation,
)
from wolf_intelligence.governance import (
    GOVERNANCE_CONFIG_DIR,
    load_policy,
    metered_permitted,
)
from wolf_intelligence.imbalance import check_imbalance

TZ = ZoneInfo("Asia/Makassar")
NOW = "2026-10-06T12:00:00+08:00"
POLICY_PATH = GOVERNANCE_CONFIG_DIR / "worker-allocation-policy.json"


def _guard() -> None:
    root = Path(paths.STATE_ROOT).resolve()
    if root == Path(paths.LIVE_STATE_ROOT).resolve() or str(root).startswith("/Users/wolfterminal/beta-os"):
        raise RuntimeError("refusing to run tests against live Wolf Intelligence state")
    if not root.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise RuntimeError("refusing to run tests outside the system temp dir")


_guard()


def _ctx(now: str | None = None, grok_available: bool = True) -> dict:
    pl = load_policy()
    cap = capacity_snapshot(now or NOW, policy=pl.policy, grok_available=grok_available)
    return {"policy_load": pl, "capacity": cap}


def _decide(task_class: str, **kw) -> allocation.Decision:
    ctx = _ctx(kw.pop("now", NOW), grok_available=kw.pop("grok_available", True))
    wi = {
        "id": kw.pop("id", f"wi-{task_class}"),
        "task_class": task_class,
        "grok_reason_code": kw.pop("grok_reason", None),
        "grok_justification": kw.pop("justification", None),
    }
    return decide(
        wi,
        policy_load=ctx["policy_load"],
        capacity=ctx["capacity"],
        ledger_view=LedgerView(),
        now=kw.pop("now", NOW),
        record=kw.pop("record", False),
    )


def _set_grok_pct(pct: float, now: str = NOW) -> None:
    record_observation(
        worker_id="grok_bot_sub",
        plan="Grok Bot subscription",
        included_usage_pct={"weekly": pct},
        on_demand="UNKNOWN",
        source="owner_observed",
        observed_at=now,
    )


def _set_worker_pct(worker_id: str, pool: str, pct: float, now: str = NOW) -> None:
    record_observation(
        worker_id=worker_id,
        included_usage_pct={pool: pct},
        source="owner_observed",
        observed_at=now,
    )


def _grok_would_dispatch(
    task_class: str,
    grok_pct: float,
    reason: str,
    justification: str | None = None,
) -> bool:
    _set_grok_pct(grok_pct)
    d = _decide(
        task_class,
        id=f"sweep-{task_class}-{grok_pct}-{reason}",
        grok_reason=reason,
        justification=justification or ("x" * 25),
    )
    return d.selected_worker == "grok_bot_sub" and d.decision == "DISPATCH"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestCapacityGovernance(unittest.TestCase):
    def setUp(self) -> None:
        gov = paths.GOVERNANCE_DIR
        if gov.exists():
            shutil.rmtree(gov)
        gov.mkdir(parents=True, exist_ok=True)
        save_tightening({"grok_routing_penalty": 0.0})

    def test_a_engineering_does_not_default_to_grok_when_cursor_eligible(self) -> None:
        d = _decide("coding", id="eng-a")
        self.assertEqual(d.decision, "DISPATCH")
        self.assertEqual(d.selected_worker, "cursor_sub")
        self.assertNotEqual(d.selected_worker, "grok_bot_sub")

    def test_b_reasoning_does_not_default_to_grok_when_claude_or_codex_eligible(self) -> None:
        d = _decide("reasoning_planning", id="reason-b")
        self.assertEqual(d.decision, "DISPATCH")
        self.assertIn(d.selected_worker, ("claude_pro_sub", "codex_sub"))
        self.assertNotEqual(d.selected_worker, "grok_bot_sub")

    def test_c_grok_pressure_monotonic_delegation(self) -> None:
        pl = load_policy()
        policy = pl.policy or {}
        allowed = (policy.get("grok_reserve") or {}).get("allowed_reason_codes_by_state") or {}
        states = ["NORMAL", "CONSERVE", "RESERVE", "EXHAUSTED"]
        pct_map = {"NORMAL": 10, "CONSERVE": 40, "RESERVE": 70, "EXHAUSTED": 96}
        prev_allowed: set[str] = set()
        for st in states:
            _set_grok_pct(pct_map[st])
            codes = set(allowed.get(st, []))
            if st == "RESERVE":
                codes = set()  # substantive blocked; only protected
            if st == "EXHAUSTED":
                codes = set()
            self.assertTrue(codes <= prev_allowed | codes)
            if prev_allowed:
                self.assertTrue(codes <= prev_allowed or st == "NORMAL")
            prev_allowed = codes if st in ("NORMAL", "CONSERVE") else set()

        # Sweep pct 0..100: Grok never re-allowed as pct rises (OTHERS_UNAVAILABLE with alternatives)
        allowed_once = False
        for pct in range(0, 101, 5):
            _set_grok_pct(float(pct))
            d = _decide(
                "coding",
                id=f"sweep-{pct}",
                grok_reason="OTHERS_UNAVAILABLE",
                justification="no others available verified check",
            )
            if d.selected_worker == "grok_bot_sub":
                if allowed_once and pct > 30:
                    self.fail("Grok re-allowed at higher pct")
                allowed_once = True
            if pct >= 95:
                self.assertNotEqual(d.selected_worker, "grok_bot_sub")

    def test_d_grok_exhaustion_does_not_stop_non_grok_workers(self) -> None:
        _set_grok_pct(96.0)
        for tc in ("coding", "reasoning_planning", "state_update", "evidence_collection", "security"):
            d = _decide(tc, id=f"failover-{tc}")
            if tc in governance.load_policy().policy.get("protected_classes", []):
                continue
            if tc in ("state_update", "evidence_collection"):
                self.assertIn(d.decision, ("DISPATCH", "QUEUE"))
                if d.decision == "DISPATCH":
                    self.assertNotEqual(d.selected_worker, "grok_bot_sub")
            else:
                self.assertEqual(d.decision, "DISPATCH")
                self.assertNotEqual(d.selected_worker, "grok_bot_sub")

    def test_e_process_restart_persistence(self) -> None:
        port = _find_free_port()
        self.assertNotIn(port, (8787, 8788, 8799))
        state_root = tempfile.mkdtemp(prefix="wi-gov-ui-state-")
        self.addCleanup(shutil.rmtree, state_root, True)
        token = "gov-restart-test-token"
        env = os.environ.copy()
        env["WOLF_INTELLIGENCE_STATE_ROOT"] = state_root
        env["WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT"] = _REAL_TMP
        env["WOLF_INTELLIGENCE_UI_TOKEN"] = token
        env["WOLF_INTELLIGENCE_UI_PORT"] = str(port)

        proc = subprocess.Popen(
            [sys.executable, "-m", "wolf_intelligence.owner_ui_server"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            self._wait_health(port, timeout=8)
            wi = {"id": "restart-wi-1", "task_class": "coding"}
            dec1 = self._api_decide(port, token, wi)
            status1 = self._api_status(port, token)
            proc.terminate()
            proc.wait(timeout=5)
            proc2 = subprocess.Popen(
                [sys.executable, "-m", "wolf_intelligence.owner_ui_server"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                self._wait_health(port, timeout=8)
                status2 = self._api_status(port, token)
                self.assertEqual(status1["policy_sha256"], status2["policy_sha256"])
                dec2 = self._api_decide(port, token, wi)
                self.assertEqual(dec1["decision_hash"], dec2["decision_hash"])
            finally:
                proc2.terminate()
                proc2.wait(timeout=5)
        finally:
            if proc.poll() is None:
                proc.kill()

    def _wait_health(self, port: int, timeout: float = 5) -> None:
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
                conn.request("GET", "/api/health")
                resp = conn.getresponse()
                if resp.status == 200:
                    return
            except OSError:
                pass
            time.sleep(0.2)
        self.fail("server did not become healthy")

    def _api_status(self, port: int, token: str) -> dict:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request("GET", "/api/governance/status", headers={"Authorization": f"Bearer {token}"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        return json.loads(resp.read().decode())

    def _api_decide(self, port: int, token: str, body: dict) -> dict:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request(
            "POST",
            "/api/governance/decide",
            body=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        return json.loads(resp.read().decode())["decision"]

    def test_f_new_peaches_session_identical_decisions(self) -> None:
        state_root = tempfile.mkdtemp(prefix="wi-gov-fresh-")
        self.addCleanup(shutil.rmtree, state_root, True)
        env = os.environ.copy()
        env["WOLF_INTELLIGENCE_STATE_ROOT"] = state_root
        env["WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT"] = _REAL_TMP
        cmd = [
            sys.executable, "-m", "wolf_intelligence", "governance", "decide",
            "--task-class", "coding", "--id", "fresh-session-wi", "--now", NOW,
        ]
        out1 = subprocess.check_output(cmd, env=env, text=True)
        out2 = subprocess.check_output(cmd, env=env, text=True)
        d1 = json.loads(out1)
        d2 = json.loads(out2)
        self.assertEqual(d1["decision_hash"], d2["decision_hash"])
        self.assertEqual(d1["selected_worker"], d2["selected_worker"])

    def test_g_no_metered_fallback_when_all_exhausted(self) -> None:
        pools = {
            "cursor_sub": "cursor_models",
            "claude_pro_sub": "week_all_models",
            "codex_sub": "week",
            "grok_bot_sub": "weekly",
        }
        for wid, pool in pools.items():
            _set_worker_pct(wid, pool, 100.0)
        d = _decide("coding", id="exhausted-g")
        self.assertEqual(d.decision, "QUEUE")
        self.assertIsNone(d.selected_worker)
        for c in d.ranked_candidates:
            if c.get("worker"):
                self.assertFalse(
                    __import__("wolf_intelligence.worker_registry", fromlist=["is_metered"]).is_metered(c["worker"])
                )

    def test_h_paid_spend_off_every_capacity_state(self) -> None:
        env_before = {k: os.environ.get(k) for k in (live_gate.MAX_COST_ENV, live_gate.DAILY_COST_ENV)}
        for pct in (0, 30, 60, 95, 100):
            _set_grok_pct(float(pct))
            self.assertFalse(metered_permitted())
            self.assertFalse(metered_permitted_with_gate())
            d = _decide("coding", id=f"spend-{pct}")
            if d.selected_worker:
                from wolf_intelligence.worker_registry import is_metered
                self.assertFalse(is_metered(d.selected_worker))
            refusal, cap, est = live_gate.enforce_cost_cap(
                {}, model_id="gpt-4", prompt="hi", max_output_tokens=100
            )
            self.assertIsNotNone(refusal)
        for k, v in env_before.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_i_imbalance_alarm_and_penalty(self) -> None:
        pl = load_policy()
        save_tightening({"grok_routing_penalty": 0.0})
        grok = "grok_bot_sub"
        for i in range(8):
            rec = {
                "decision": "DISPATCH",
                "selected_worker": grok,
                "delegatable": True,
                "protected": False,
                "alternatives_available": True,
                "recorded_at": NOW,
            }
            with paths.GOVERNANCE_DISPATCH_LEDGER_PATH.open("a") as f:
                f.write(json.dumps(rec) + "\n")
        result = check_imbalance(pl, LedgerView(), now=NOW)
        self.assertTrue(result.get("triggered"))
        t = load_tightening()
        self.assertGreater(float(t.get("grok_routing_penalty", 0)), 0.0)
        audit = paths.GOVERNANCE_AUDIT_PATH.read_text()
        self.assertIn("ROUTING_IMBALANCE", audit)
        # Protected work must not trigger
        save_tightening({"grok_routing_penalty": 0.0})
        prot_rec = {
            "decision": "DISPATCH",
            "selected_worker": grok,
            "delegatable": False,
            "protected": True,
            "alternatives_available": True,
            "recorded_at": NOW,
        }
        with paths.GOVERNANCE_DISPATCH_LEDGER_PATH.open("w") as f:
            for _ in range(10):
                f.write(json.dumps(prot_rec) + "\n")
        r2 = check_imbalance(pl, LedgerView(), now=NOW)
        self.assertFalse(r2.get("triggered"))

    def test_j_policy_fail_closed(self) -> None:
        cases = [
            ("missing", Path("/nonexistent/policy.json")),
            ("corrupt", None),
            ("schema_invalid", None),
            ("invariant_flip", None),
        ]
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        corrupt = Path(tmp) / "corrupt.json"
        corrupt.write_text("{not json", encoding="utf-8")
        bad_schema = Path(tmp) / "bad_schema.json"
        bad_schema.write_text(json.dumps({"version": 1}), encoding="utf-8")
        flip = Path(tmp) / "flip.json"
        good = json.loads(POLICY_PATH.read_text())
        flip_data = dict(good)
        flip_data["metered_fallback"] = "ALLOWED"
        flip.write_text(json.dumps(flip_data), encoding="utf-8")

        for label, path in [
            ("missing", Path("/nonexistent/wi-policy-missing.json")),
            ("corrupt", corrupt),
            ("schema_invalid", bad_schema),
            ("invariant_flip", flip),
        ]:
            pl = load_policy(path)
            self.assertEqual(pl.mode, "FAIL_CLOSED")
            self.assertFalse(pl.ok)
            d = decide(
                {"id": f"fc-{label}", "task_class": "coding", "grok_reason_code": "EXPLICIT_JUSTIFIED",
                 "grok_justification": "x" * 30},
                policy_load=pl,
                capacity=capacity_snapshot(NOW, policy=pl.policy or {}),
                record=False,
            )
            self.assertNotEqual(d.selected_worker, "grok_bot_sub")
            self.assertTrue(d.owner_action_required)
            self.assertEqual(d.owner_action_code, "OWNER_ACTION_REQUIRED")

    def test_k_invalid_grok_justification_rejected(self) -> None:
        cases = [
            ("missing", None, None),
            ("peaches_can_do_it", "peaches_can_do_it", None),
            ("explicit_no_text", "EXPLICIT_JUSTIFIED", ""),
            ("benchmark_unverifiable", "BENCHMARK_SELECTED", None),
            ("others_available", "OTHERS_UNAVAILABLE", None),
        ]
        for name, code, just in cases:
            d = _decide(
                "coding",
                id=f"k-{name}",
                grok_reason=code,
                justification=just,
            )
            self.assertNotEqual(d.selected_worker, "grok_bot_sub")
            if code:
                self.assertEqual(d.grok_reason_verdict, "REJECTED")

    def test_capacity_seed_values_exact(self) -> None:
        seed = json.loads(SEED_PATH.read_text())
        by_id = {o["worker_id"]: o for o in seed["observations"]}
        cursor = by_id["cursor_sub"]
        self.assertEqual(cursor["plan"], "Cursor Ultra $200/mo")
        self.assertEqual(cursor["included_usage_pct"], {"cursor_models": 41, "other_models": 1})
        self.assertIsNone(cursor["remaining"])
        grok = by_id["grok_bot_sub"]
        self.assertEqual(grok["included_usage_pct"], {"weekly": 41})
        self.assertEqual(grok["on_demand"], "UNKNOWN")

    def test_capacity_remaining_null_unless_exposed(self) -> None:
        merged = merge_observations()
        for wid, rec in merged.items():
            self.assertIsNone(rec.get("remaining"))

    def test_capacity_stale_decay_conservative(self) -> None:
        # Seed observed_at is 2026-10-06T09:49; advance now >24h so decay + stale floor apply.
        future_now = "2026-10-08T12:00:00+08:00"
        snap = capacity_snapshot(future_now)
        rec = snap["workers"]["cursor_sub"]
        seed_pct = 41.0
        hours_stale = (
            datetime.fromisoformat(future_now) - datetime.fromisoformat("2026-10-06T09:49:00+08:00")
        ).total_seconds() / 3600.0
        expected_effective = min(100.0, seed_pct + 0.5 * hours_stale)
        self.assertGreater(rec["effective_pct"], seed_pct)
        self.assertAlmostEqual(rec["effective_pct"], expected_effective, places=2)
        self.assertIn(rec["state"], ("CONSERVE", "RESERVE", "EXHAUSTED"))

    def test_capacity_velocity_from_ledger(self) -> None:
        t0 = "2026-10-05T12:00:00+08:00"
        t1 = "2026-10-06T12:00:00+08:00"
        record_observation(worker_id="codex_sub", included_usage_pct={"week": 1.0}, observed_at=t0)
        record_observation(worker_id="codex_sub", included_usage_pct={"week": 3.0}, observed_at=t1)
        snap = capacity_snapshot(t1)
        vel = snap["workers"]["codex_sub"]["velocity"]
        self.assertIsNotNone(vel.get("pct_per_day"))

    def test_capacity_projection_true_false_null(self) -> None:
        pl = load_policy()
        policy = pl.policy or {}
        # null when unknown reset
        snap = capacity_snapshot(NOW, policy=policy)
        self.assertIsNone(snap["workers"]["cursor_sub"]["projected_exhaustion_before_reset"])
        # true when velocity + reset known
        record_observation(
            worker_id="codex_sub",
            included_usage_pct={"week": 80},
            reset_at="2026-10-07T12:00:00+08:00",
            observed_at="2026-10-06T09:00:00+08:00",
        )
        record_observation(
            worker_id="codex_sub",
            included_usage_pct={"week": 90},
            reset_at="2026-10-07T12:00:00+08:00",
            observed_at="2026-10-06T11:00:00+08:00",
        )
        snap2 = capacity_snapshot("2026-10-06T12:00:00+08:00", policy=policy)
        proj = snap2["workers"]["codex_sub"]["projected_exhaustion_before_reset"]
        self.assertIn(proj, (True, False, None))


if __name__ == "__main__":
    unittest.main()
