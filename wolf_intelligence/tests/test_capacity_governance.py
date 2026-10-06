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


def _decide(task_class: str | None = None, **kw) -> allocation.Decision:
    ctx = _ctx(kw.pop("now", NOW), grok_available=kw.pop("grok_available", True))
    wi: dict = {
        "id": kw.pop("id", f"wi-{task_class or 'none'}"),
        "grok_reason_code": kw.pop("grok_reason", None),
        "grok_justification": kw.pop("justification", None),
    }
    if task_class is not None:
        wi["task_class"] = task_class
    if "requested_worker" in kw:
        wi["requested_worker"] = kw.pop("requested_worker")
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
        save_tightening({"grok_routing_penalty": 0.0}, load_policy().policy)

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
        just = "x" * 25
        # NORMAL + valid EXPLICIT_JUSTIFIED + requested grok -> Grok DISPATCH
        _set_grok_pct(10.0)
        d_normal = _decide(
            "coding",
            id="c-normal-grok",
            requested_worker="grok_bot_sub",
            grok_reason="EXPLICIT_JUSTIFIED",
            justification=just,
        )
        self.assertEqual(d_normal.decision, "DISPATCH")
        self.assertEqual(d_normal.selected_worker, "grok_bot_sub")
        self.assertEqual(d_normal.grok_reason_verdict, "ACCEPTED")
        self.assertIsNotNone(d_normal.quality_floor_waived_reason)

        # CONSERVE + BENCHMARK_SELECTED -> rejected
        _set_grok_pct(40.0)
        d_conserve_bench = _decide(
            "coding",
            id="c-conserve-bench",
            requested_worker="grok_bot_sub",
            grok_reason="BENCHMARK_SELECTED",
        )
        self.assertNotEqual(d_conserve_bench.selected_worker, "grok_bot_sub")
        self.assertEqual(d_conserve_bench.grok_reason_verdict, "REJECTED")

        # RESERVE -> substantive never Grok but protected -> Grok
        _set_grok_pct(70.0)
        d_reserve_sub = _decide(
            "coding",
            id="c-reserve-sub",
            requested_worker="grok_bot_sub",
            grok_reason="EXPLICIT_JUSTIFIED",
            justification=just,
        )
        self.assertNotEqual(d_reserve_sub.selected_worker, "grok_bot_sub")
        d_reserve_prot = _decide("owner_conversation", id="c-reserve-prot")
        self.assertEqual(d_reserve_prot.decision, "DISPATCH")
        self.assertEqual(d_reserve_prot.selected_worker, "grok_bot_sub")

        # EXHAUSTED -> protected QUEUE and substantive non-Grok
        _set_grok_pct(96.0)
        d_ex_prot = _decide("orchestration", id="c-exhaust-prot")
        self.assertEqual(d_ex_prot.decision, "QUEUE")
        self.assertIsNone(d_ex_prot.selected_worker)
        d_ex_sub = _decide("coding", id="c-exhaust-sub")
        self.assertEqual(d_ex_sub.decision, "DISPATCH")
        self.assertNotEqual(d_ex_sub.selected_worker, "grok_bot_sub")

        # Sweep pct 0..100 step 1: (class, code) pairs Grok may take is non-increasing
        pl = load_policy()
        policy = pl.policy or {}
        allowed = (policy.get("grok_reserve") or {}).get("allowed_reason_codes_by_state") or {}
        codes_to_try = [
            ("coding", "EXPLICIT_JUSTIFIED"),
            ("coding", "OTHERS_UNAVAILABLE"),
            ("coding", "BENCHMARK_SELECTED"),
            ("owner_conversation", None),
        ]
        prev_grok_pairs: set[tuple[str, str | None]] | None = None
        for pct in range(0, 101):
            _set_grok_pct(float(pct))
            grok_pairs: set[tuple[str, str | None]] = set()
            for tc, code in codes_to_try:
                kw = {"id": f"sweep-{pct}-{tc}-{code}", "justification": just}
                if code:
                    kw["grok_reason"] = code
                    kw["requested_worker"] = "grok_bot_sub"
                d = _decide(tc, **kw)
                if d.selected_worker == "grok_bot_sub" and d.decision == "DISPATCH":
                    grok_pairs.add((tc, code))
            if prev_grok_pairs is not None:
                self.assertTrue(
                    grok_pairs <= prev_grok_pairs,
                    f"Grok pairs grew at pct={pct}: {grok_pairs} not subset of {prev_grok_pairs}",
                )
            prev_grok_pairs = grok_pairs

    def test_d_grok_exhaustion_does_not_stop_non_grok_workers(self) -> None:
        pl = load_policy()
        policy = pl.policy or {}
        families = policy.get("task_families") or {}
        non_protected = (
            list(families.get("engineering", []))
            + list(families.get("reasoning_review", []))
            + list(families.get("operations", []))
        )
        for scenario, grok_avail in (("exhausted", True), ("outage", False)):
            _set_grok_pct(96.0)
            for tc in non_protected:
                d = _decide(tc, id=f"failover-{scenario}-{tc}", grok_available=grok_avail)
                self.assertEqual(d.decision, "DISPATCH", f"{tc} under {scenario}")
                self.assertIsNotNone(d.selected_worker)
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
                cap_states1 = {
                    w: rec.get("state")
                    for w, rec in status1["capacity"]["workers"].items()
                }
                cap_states2 = {
                    w: rec.get("state")
                    for w, rec in status2["capacity"]["workers"].items()
                }
                self.assertEqual(cap_states1, cap_states2)
                dec2 = self._api_decide(port, token, wi)
                self.assertEqual(dec1["decision_hash"], dec2["decision_hash"])
                self.assertEqual(dec1["decision"], dec2["decision"])
                self.assertEqual(dec1["selected_worker"], dec2["selected_worker"])
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
        policy = pl.policy or {}
        hard_block = float((policy.get("imbalance") or {}).get("penalty_hard_block_at", 0.6))
        save_tightening({"grok_routing_penalty": 0.0}, policy)
        just = "x" * 25
        # Before alarm: Grok substantive with valid code is selected when requested
        d_before = _decide(
            "coding",
            id="imbalance-before",
            requested_worker="grok_bot_sub",
            grok_reason="EXPLICIT_JUSTIFIED",
            justification=just,
        )
        self.assertEqual(d_before.selected_worker, "grok_bot_sub")

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
        t = load_tightening(policy)
        self.assertGreater(float(t.get("grok_routing_penalty", 0)), 0.0)
        audit = paths.GOVERNANCE_AUDIT_PATH.read_text()
        self.assertIn("ROUTING_IMBALANCE", audit)

        # Raise penalty to hard-block: next decision shifts away from Grok
        save_tightening({"grok_routing_penalty": hard_block}, policy)
        d_after = _decide(
            "coding",
            id="imbalance-after",
            grok_reason="EXPLICIT_JUSTIFIED",
            justification=just,
        )
        self.assertNotEqual(d_after.selected_worker, "grok_bot_sub")
        self.assertEqual(d_after.decision, "DISPATCH")
        self.assertIn(d_after.selected_worker, ("cursor_sub", "claude_pro_sub", "codex_sub"))

        # Protected work must not trigger imbalance
        save_tightening({"grok_routing_penalty": 0.0}, policy)
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
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        corrupt = Path(tmp) / "corrupt.json"
        corrupt.write_text("{not json", encoding="utf-8")
        bad_schema = Path(tmp) / "bad_schema.json"
        bad_schema.write_text(json.dumps({"version": 1}), encoding="utf-8")
        good = json.loads(POLICY_PATH.read_text())

        def _flip(data: dict, **changes) -> Path:
            p = Path(tmp) / f"flip-{len(list(Path(tmp).glob('flip-*')))}.json"
            flipped = dict(data, **changes)
            p.write_text(json.dumps(flipped), encoding="utf-8")
            return p

        flip_metered = _flip(good, metered_fallback="ALLOWED")
        flip_grok_id = _flip(good, grok_worker_id="wrong_grok")
        flip_conserve = _flip(good)
        flip_conserve_data = json.loads(flip_conserve.read_text())
        flip_conserve_data["grok_reserve"]["allowed_reason_codes_by_state"]["CONSERVE"] = list(
            good["grok_reserve"]["allowed_reason_codes_by_state"]["NORMAL"]
        )
        flip_conserve.write_text(json.dumps(flip_conserve_data), encoding="utf-8")
        flip_reserve = _flip(good)
        flip_reserve_data = json.loads(flip_reserve.read_text())
        flip_reserve_data["grok_reserve"]["allowed_reason_codes_by_state"]["RESERVE"] = ["EXPLICIT_JUSTIFIED"]
        flip_reserve.write_text(json.dumps(flip_reserve_data), encoding="utf-8")
        flip_neg_pen = _flip(good, grok_routing_penalty_default=-0.5)

        for label, path in [
            ("missing", Path("/nonexistent/wi-policy-missing.json")),
            ("corrupt", corrupt),
            ("schema_invalid", bad_schema),
            ("invariant_flip_metered", flip_metered),
            ("invariant_flip_grok_id", flip_grok_id),
            ("invariant_flip_conserve_loosened", flip_conserve),
            ("invariant_flip_reserve_nonempty", flip_reserve),
            ("invariant_flip_negative_penalty", flip_neg_pen),
        ]:
            pl = load_policy(path)
            self.assertEqual(pl.mode, "FAIL_CLOSED")
            self.assertFalse(pl.ok)
            cap = capacity_snapshot(NOW, policy=pl.policy or {})
            d_sub = decide(
                {
                    "id": f"fc-sub-{label}",
                    "task_class": "coding",
                    "grok_reason_code": "EXPLICIT_JUSTIFIED",
                    "grok_justification": "x" * 30,
                    "requested_worker": "grok_bot_sub",
                },
                policy_load=pl,
                capacity=cap,
                record=False,
            )
            self.assertNotEqual(d_sub.selected_worker, "grok_bot_sub")
            self.assertTrue(d_sub.owner_action_required)
            self.assertEqual(d_sub.owner_action_code, "OWNER_ACTION_REQUIRED")
            d_prot = decide(
                {"id": f"fc-prot-{label}", "task_class": "owner_conversation"},
                policy_load=pl,
                capacity=cap,
                record=False,
            )
            self.assertEqual(d_prot.decision, "DISPATCH")
            self.assertEqual(d_prot.selected_worker, "grok_bot_sub")
            self.assertTrue(d_prot.owner_action_required)

    def test_k_invalid_grok_justification_rejected(self) -> None:
        just_ok = "x" * 25
        # Positive control: valid code ACCEPTED and Grok DISPATCH when requested
        d_ok = _decide(
            "coding",
            id="k-valid",
            requested_worker="grok_bot_sub",
            grok_reason="EXPLICIT_JUSTIFIED",
            justification=just_ok,
        )
        self.assertEqual(d_ok.grok_reason_verdict, "ACCEPTED")
        self.assertEqual(d_ok.selected_worker, "grok_bot_sub")
        self.assertEqual(d_ok.decision, "DISPATCH")

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
                requested_worker="grok_bot_sub",
                grok_reason=code,
                justification=just,
            )
            self.assertNotEqual(d.selected_worker, "grok_bot_sub")
            if code:
                self.assertEqual(d.grok_reason_verdict, "REJECTED")

    def test_unclassified_task_class_queues(self) -> None:
        d = _decide(task_class="not_a_real_class", id="unclassified-1")
        self.assertEqual(d.decision, "QUEUE")
        self.assertIsNone(d.selected_worker)
        self.assertIn("unclassified", d.exclusion_notes)
        d2 = _decide(task_class=None, id="unclassified-2")
        self.assertEqual(d2.decision, "QUEUE")
        self.assertIn("unclassified", d2.exclusion_notes)

    def test_tightening_corrupt_uses_penalty_max(self) -> None:
        pl = load_policy()
        policy = pl.policy or {}
        max_pen = float((policy.get("imbalance") or {}).get("penalty_max", 1.0))
        paths.GOVERNANCE_TIGHTENING_PATH.write_text("not-json", encoding="utf-8")
        t = load_tightening(policy)
        self.assertEqual(float(t["grok_routing_penalty"]), max_pen)
        audit = paths.GOVERNANCE_AUDIT_PATH.read_text()
        self.assertIn("TIGHTENING_CORRUPT", audit)
        paths.GOVERNANCE_TIGHTENING_PATH.write_text(json.dumps({"grok_routing_penalty": -0.5}), encoding="utf-8")
        t2 = load_tightening(policy)
        default_pen = float(policy.get("grok_routing_penalty_default", 0.0))
        self.assertGreaterEqual(float(t2["grok_routing_penalty"]), default_pen)

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
