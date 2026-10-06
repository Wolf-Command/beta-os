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
    _TEST_STATE_ROOT = _tempfile.mkdtemp(prefix="wi-gov-test-state-")
    _os.environ["WOLF_INTELLIGENCE_STATE_ROOT"] = _TEST_STATE_ROOT
    _os.environ["WI_TEST_STATE_ISOLATED"] = _TEST_STATE_ROOT
    _atexit.register(_shutil.rmtree, _TEST_STATE_ROOT, True)
    if "wolf_intelligence.paths" in _sys.modules:
        from wolf_intelligence.paths import rebind_state_paths

        rebind_state_paths()
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
    cap = capacity_snapshot(
        now or NOW,
        policy=pl.policy,
        policy_mode=pl.mode,
        grok_available=grok_available,
    )
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

        d_conserve_explicit = _decide(
            "coding",
            id="c-conserve-explicit",
            requested_worker="grok_bot_sub",
            grok_reason="EXPLICIT_JUSTIFIED",
            justification=just,
        )
        self.assertNotEqual(d_conserve_explicit.selected_worker, "grok_bot_sub")
        self.assertEqual(d_conserve_explicit.grok_reason_verdict, "REJECTED")

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

        gov_dir = Path(state_root) / "governance"
        gov_dir.mkdir(parents=True, exist_ok=True)
        obs_path = gov_dir / "capacity-observations.jsonl"
        tighten_path = gov_dir / "tightening.json"
        ledger_path = gov_dir / "dispatch-ledger.jsonl"
        obs_body = {
            "worker_id": "grok_bot_sub",
            "included_usage_pct": {"weekly": 35.0},
            "observed_at": NOW,
        }
        with obs_path.open("a") as f:
            f.write(json.dumps(obs_body) + "\n")
        tighten_path.write_text(
            json.dumps({"grok_routing_penalty": 0.15}) + "\n",
            encoding="utf-8",
        )
        proc = subprocess.Popen(
            [sys.executable, "-m", "wolf_intelligence.owner_ui_server"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            self._wait_health(port, timeout=8)
            wi = {"id": "restart-wi-1", "task_class": "coding", "now": NOW}
            dec1 = self._api_decide(port, token, wi)
            status1 = self._api_status(port, token, now=NOW)
            ledger_before = ledger_path.read_text() if ledger_path.exists() else ""
            obs_before = obs_path.read_text()
            tighten_before = tighten_path.read_text()
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
                status2 = self._api_status(port, token, now=NOW)
                self.assertEqual(status1["policy_sha256"], status2["policy_sha256"])
                self.assertEqual(
                    status1["grok_routing_penalty"],
                    status2["grok_routing_penalty"],
                )
                cap_states1 = {
                    w: rec.get("state")
                    for w, rec in status1["capacity"]["workers"].items()
                }
                cap_states2 = {
                    w: rec.get("state")
                    for w, rec in status2["capacity"]["workers"].items()
                }
                self.assertEqual(cap_states1, cap_states2)
                self.assertEqual(
                    ledger_path.read_text() if ledger_path.exists() else "",
                    ledger_before,
                )
                self.assertEqual(obs_path.read_text(), obs_before)
                self.assertEqual(tighten_path.read_text(), tighten_before)
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

    def _api_status(self, port: int, token: str, now: str | None = None) -> dict:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        path = "/api/governance/status"
        if now:
            path += f"?now={now}"
        conn.request("GET", path, headers={"Authorization": f"Bearer {token}"})
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
        env["WOLF_INTELLIGENCE_GOVERNANCE_TEST_CLOCK"] = "1"
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
        from itertools import product
        from wolf_intelligence.worker_registry import is_metered

        env_before = {k: os.environ.get(k) for k in (live_gate.MAX_COST_ENV, live_gate.DAILY_COST_ENV)}
        state_pcts = {
            "NORMAL": {"cursor_sub": 10, "claude_pro_sub": 10, "codex_sub": 10, "grok_bot_sub": 10},
            "CONSERVE": {"cursor_sub": 75, "claude_pro_sub": 75, "codex_sub": 75, "grok_bot_sub": 40},
            "RESERVE": {"cursor_sub": 90, "claude_pro_sub": 90, "codex_sub": 90, "grok_bot_sub": 65},
            "EXHAUSTED": {"cursor_sub": 100, "claude_pro_sub": 100, "codex_sub": 100, "grok_bot_sub": 96},
        }
        pools = {
            "cursor_sub": "cursor_models",
            "claude_pro_sub": "week_all_models",
            "codex_sub": "week",
            "grok_bot_sub": "weekly",
        }
        workers = list(state_pcts["NORMAL"].keys())
        states = list(state_pcts.keys())
        for combo in product(states, repeat=len(workers)):
            if paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.exists():
                paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.unlink()
            for wid, st in zip(workers, combo):
                _set_worker_pct(wid, pools[wid], float(state_pcts[st][wid]))
            env_after = {k: os.environ.get(k) for k in (live_gate.MAX_COST_ENV, live_gate.DAILY_COST_ENV)}
            self.assertEqual(env_before, env_after)
            self.assertFalse(metered_permitted())
            self.assertFalse(metered_permitted_with_gate())
            self.assertIsNone(live_gate.cost_cap({}))
            d = _decide("coding", id=f"spend-{'-'.join(combo)}")
            if d.selected_worker:
                self.assertFalse(is_metered(d.selected_worker))
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
        _set_grok_pct(10.0)
        d_before = _decide(
            "coding",
            id="imbalance-before",
            requested_worker="grok_bot_sub",
            grok_reason="EXPLICIT_JUSTIFIED",
            justification=just,
        )
        self.assertEqual(d_before.selected_worker, "grok_bot_sub")
        self.assertEqual(d_before.grok_reason_verdict, "ACCEPTED")

        grok = "grok_bot_sub"
        for i in range(8):
            wi = {
                "id": f"imbalance-dispatch-{i}",
                "task_class": "coding",
                "requested_worker": grok,
                "grok_reason_code": "EXPLICIT_JUSTIFIED",
                "grok_justification": just,
            }
            decide(
                wi,
                policy_load=pl,
                capacity=capacity_snapshot(NOW, policy=policy, policy_mode=pl.mode),
                ledger_view=LedgerView(),
                now=NOW,
                record=True,
            )
            check_imbalance(pl, LedgerView(), now=NOW)
        t = load_tightening(policy)
        self.assertGreaterEqual(float(t.get("grok_routing_penalty", 0)), hard_block)
        audit = paths.GOVERNANCE_AUDIT_PATH.read_text()
        self.assertIn("ROUTING_IMBALANCE", audit)

        d_after = _decide(
            "coding",
            id="imbalance-after",
            requested_worker="grok_bot_sub",
            grok_reason="EXPLICIT_JUSTIFIED",
            justification=just,
        )
        self.assertNotEqual(d_after.selected_worker, "grok_bot_sub")
        self.assertEqual(d_after.grok_reason_verdict, "REJECTED")

        save_tightening({"grok_routing_penalty": 0.0}, policy)
        paths.GOVERNANCE_DISPATCH_LEDGER_PATH.write_text("", encoding="utf-8")
        _set_grok_pct(96.0)
        min_samples = int((policy.get("imbalance") or {}).get("min_samples", 5))
        for i in range(min_samples):
            decide(
                {
                    "id": f"raw-cap-non-grok-{i}",
                    "task_class": "coding",
                    "requested_worker": "cursor_sub",
                },
                policy_load=pl,
                capacity=capacity_snapshot(NOW, policy=policy, policy_mode=pl.mode),
                ledger_view=LedgerView(),
                now=NOW,
                record=True,
            )
        r_capacity = check_imbalance(pl, LedgerView(), now=NOW)
        self.assertFalse(r_capacity.get("triggered"))

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
        flip_paid_on = _flip(good, paid_spend="ON")
        flip_extra_code = _flip(good)
        flip_extra_code_data = json.loads(flip_extra_code.read_text())
        flip_extra_code_data["grok_reason_codes"] = list(good["grok_reason_codes"]) + ["peaches_can_do_it"]
        flip_extra_code.write_text(json.dumps(flip_extra_code_data), encoding="utf-8")
        flip_dup_keys = Path(tmp) / "dup-keys.json"
        flip_dup_keys.write_text(
            json.dumps(good)[:-1] + ',"grok_justification_min_length":1}',
            encoding="utf-8",
        )
        flip_nan_floor = _flip(good)
        flip_nan_data = json.loads(flip_nan_floor.read_text())
        flip_nan_data["quality_floors"]["default"] = float("nan")
        flip_nan_floor.write_text(json.dumps(flip_nan_data), encoding="utf-8")
        missing_schema_dir = Path(tmp) / "no-schema"
        missing_schema_dir.mkdir(exist_ok=True)
        good_policy_copy = missing_schema_dir / "policy.json"
        good_policy_copy.write_text(json.dumps(good), encoding="utf-8")

        for label, path in [
            ("missing", Path("/nonexistent/wi-policy-missing.json")),
            ("corrupt", corrupt),
            ("schema_invalid", bad_schema),
            ("invariant_flip_metered", flip_metered),
            ("invariant_flip_grok_id", flip_grok_id),
            ("invariant_flip_conserve_loosened", flip_conserve),
            ("invariant_flip_reserve_nonempty", flip_reserve),
            ("invariant_flip_negative_penalty", flip_neg_pen),
            ("invariant_flip_paid_on", flip_paid_on),
            ("invariant_flip_extra_reason_code", flip_extra_code),
            ("duplicate_keys", flip_dup_keys),
            ("nan_quality_floor", flip_nan_floor),
            ("missing_schema_file", good_policy_copy),
        ]:
            if paths.GOVERNANCE_AUDIT_PATH.exists():
                paths.GOVERNANCE_AUDIT_PATH.unlink()
            if label == "missing_schema_file":
                with mock.patch.object(governance, "SCHEMA_PATH", missing_schema_dir / "missing.schema.json"):
                    pl = load_policy(path)
            else:
                pl = load_policy(path)
            self.assertEqual(pl.mode, "FAIL_CLOSED")
            self.assertFalse(pl.ok)
            cap = capacity_snapshot(NOW, policy=pl.policy, policy_mode=pl.mode)
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
            self.assertIn(d_sub.decision, ("QUEUE", "DENY"))
            self.assertTrue(d_sub.owner_action_required)
            self.assertEqual(d_sub.owner_action_code, "OWNER_ACTION_REQUIRED")
            self.assertFalse(metered_permitted(pl))
            self.assertFalse(metered_permitted_with_gate(pl))
            audit_text = paths.GOVERNANCE_AUDIT_PATH.read_text() if paths.GOVERNANCE_AUDIT_PATH.exists() else ""
            self.assertIn("GOVERNANCE_POLICY_FAIL_CLOSED", audit_text)
            d_prot = decide(
                {"id": f"fc-prot-{label}", "task_class": "owner_conversation"},
                policy_load=pl,
                capacity=cap,
                record=False,
            )
            if label not in ("missing_schema_file",):
                self.assertEqual(d_prot.decision, "DISPATCH")
                self.assertEqual(d_prot.selected_worker, "grok_bot_sub")
            self.assertTrue(d_prot.owner_action_required)

    def test_k_invalid_grok_justification_rejected(self) -> None:
        just_ok = "x" * 25
        _set_grok_pct(10.0)
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
        grok_obs = [o for o in seed["observations"] if o["worker_id"] == "grok_bot_sub"]
        self.assertEqual(len(grok_obs), 2)
        grok_by_time = {o["observed_at"]: o for o in grok_obs}
        self.assertEqual(
            grok_by_time["2026-10-06T09:49:00+08:00"]["included_usage_pct"]["weekly"],
            41,
        )
        self.assertEqual(
            grok_by_time["2026-10-06T10:34:00+08:00"]["included_usage_pct"]["weekly"],
            49,
        )
        by_id = {o["worker_id"]: o for o in seed["observations"] if o["worker_id"] != "grok_bot_sub"}
        cursor = by_id["cursor_sub"]
        self.assertEqual(cursor["plan"], "Cursor Ultra $200/mo")
        self.assertEqual(cursor["included_usage_pct"], {"cursor_models": 41, "other_models": 1})
        self.assertIsNone(cursor["remaining"])
        self.assertEqual(grok_by_time["2026-10-06T09:49:00+08:00"]["on_demand"], "UNKNOWN")

    def test_capacity_remaining_null_unless_exposed(self) -> None:
        merged, _ = merge_observations()
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
        with mock.patch.object(capacity, "_load_seed", return_value=[]):
            record_observation(worker_id="codex_sub", included_usage_pct={"week": 1.0}, observed_at=t0)
            record_observation(worker_id="codex_sub", included_usage_pct={"week": 3.0}, observed_at=t1)
            for i in range(3):
                rec = {
                    "decision": "DISPATCH",
                    "selected_worker": "codex_sub",
                    "recorded_at": t1,
                }
                with paths.GOVERNANCE_DISPATCH_LEDGER_PATH.open("a") as f:
                    f.write(json.dumps(rec) + "\n")
            snap = capacity_snapshot(t1)
            vel = snap["workers"]["codex_sub"]["velocity"]
            self.assertAlmostEqual(vel.get("pct_per_hour"), 2.0 / 24.0, places=4)
            self.assertAlmostEqual(vel.get("pct_per_day"), 2.0, places=4)
            self.assertEqual(vel.get("dispatch_24h"), 3)
            self.assertEqual(vel.get("dispatch_7d"), 3)

    def test_capacity_projection_true_false_null(self) -> None:
        pl = load_policy()
        policy = pl.policy or {}
        snap = capacity_snapshot(NOW, policy=policy, policy_mode=pl.mode)
        self.assertIsNone(snap["workers"]["cursor_sub"]["projected_exhaustion_before_reset"])
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
        snap2 = capacity_snapshot("2026-10-06T12:00:00+08:00", policy=policy, policy_mode=pl.mode)
        self.assertIs(snap2["workers"]["codex_sub"]["projected_exhaustion_before_reset"], True)
        if paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.exists():
            paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.unlink()
        with mock.patch.object(capacity, "_load_seed", return_value=[]):
            record_observation(
                worker_id="codex_sub",
                included_usage_pct={"week": 80},
                reset_at="2026-10-07T12:00:00+08:00",
                observed_at="2026-10-06T10:00:00+08:00",
            )
            record_observation(
                worker_id="codex_sub",
                included_usage_pct={"week": 80},
                reset_at="2026-10-07T12:00:00+08:00",
                observed_at="2026-10-06T11:00:00+08:00",
            )
            snap3 = capacity_snapshot("2026-10-06T12:00:00+08:00", policy=policy, policy_mode=pl.mode)
            self.assertIs(snap3["workers"]["codex_sub"]["projected_exhaustion_before_reset"], False)

    def test_quality_tie_band_reasoning_share(self) -> None:
        claude_wins = 0
        codex_wins = 0
        for i in range(40):
            d = _decide("ux_product", id=f"ux-tie-{i}")
            self.assertEqual(d.decision, "DISPATCH")
            if d.selected_worker == "claude_pro_sub":
                claude_wins += 1
            elif d.selected_worker == "codex_sub":
                codex_wins += 1
        self.assertGreater(claude_wins, 0)
        self.assertGreater(codex_wins, 0)
        import hashlib as _hashlib
        pl = load_policy()
        prefer = (pl.policy or {})["specialisation"]["reasoning_review"]["prefer_workers"]
        cap_reorder_id = "ux-tie-cap-reorder"
        for i in range(256):
            candidate = f"ux-tie-cap-{i}"
            h = int(_hashlib.sha256(candidate.encode()).hexdigest(), 16)
            rotation = h % len(prefer)
            rotated = prefer[rotation:] + prefer[:rotation]
            if rotated[0] == "codex_sub":
                cap_reorder_id = candidate
                break
        _set_worker_pct("claude_pro_sub", "week_all_models", 90.0)
        _set_worker_pct("codex_sub", "week", 10.0)
        d_cap = _decide("ux_product", id=cap_reorder_id)
        self.assertEqual(d_cap.selected_worker, "codex_sub")

    def _velocity_policy_fixture(self, conserve_at: float = 60) -> dict:
        pl = load_policy()
        policy = json.loads(json.dumps(pl.policy))
        policy["capacity_thresholds"]["grok_bot_sub"] = {
            "conserve_at": conserve_at,
            "reserve_at": 85,
            "exhausted_at": 95,
        }
        return policy

    def test_velocity_owner_data_trips_conserve(self) -> None:
        policy = self._velocity_policy_fixture(conserve_at=60)
        now = "2026-10-06T10:35:00+08:00"
        if paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.exists():
            paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.unlink()
        snap = capacity_snapshot(now, policy=policy, policy_mode="ENFORCED")
        grok = snap["workers"]["grok_bot_sub"]
        self.assertGreaterEqual(
            {"NORMAL": 0, "CONSERVE": 1, "RESERVE": 2, "EXHAUSTED": 3}[grok["state"]],
            1,
        )
        self.assertLess(grok.get("effective_pct", 100), 60)
        self.assertIs(snap["grok_state"], grok["state"])
        d = decide(
            {
                "id": "vel-owner-trip",
                "task_class": "coding",
                "requested_worker": "grok_bot_sub",
                "grok_reason_code": "BENCHMARK_SELECTED",
            },
            policy_load=load_policy(),
            capacity=snap,
            now=now,
            record=False,
        )
        self.assertNotEqual(d.selected_worker, "grok_bot_sub")
        self.assertIsNotNone(d.grok_conserve_conduct)

    def test_velocity_slow_drift_not_tripped(self) -> None:
        policy = self._velocity_policy_fixture(conserve_at=60)
        if paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.exists():
            paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.unlink()
        record_observation(
            worker_id="grok_bot_sub",
            included_usage_pct={"weekly": 41},
            source="owner_observed",
            observed_at="2026-10-02T10:34:00+08:00",
        )
        record_observation(
            worker_id="grok_bot_sub",
            included_usage_pct={"weekly": 49},
            source="owner_observed",
            observed_at="2026-10-06T10:34:00+08:00",
            reset_at="2026-10-09T10:34:00+08:00",
        )
        now = "2026-10-06T10:35:00+08:00"
        snap = capacity_snapshot(now, policy=policy, policy_mode="ENFORCED")
        grok = snap["workers"]["grok_bot_sub"]
        self.assertEqual(grok["state"], "NORMAL")
        self.assertIs(grok.get("projected_exhaustion_before_reset"), False)

    def test_velocity_monotonic_in_velocity(self) -> None:
        policy = self._velocity_policy_fixture(conserve_at=60)
        if paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.exists():
            paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.unlink()
        record_observation(
            worker_id="grok_bot_sub",
            included_usage_pct={"weekly": 41},
            source="owner_observed",
            observed_at="2026-10-06T09:49:00+08:00",
        )
        states: list[str] = []
        for pct, ts in [(45, "2026-10-06T10:00:00+08:00"), (49, "2026-10-06T10:34:00+08:00"), (55, "2026-10-06T10:40:00+08:00")]:
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": float(pct)},
                source="owner_observed",
                observed_at=ts,
            )
            snap = capacity_snapshot(ts, policy=policy, policy_mode="ENFORCED")
            states.append(snap["workers"]["grok_bot_sub"]["state"])
        ranks = [{"NORMAL": 0, "CONSERVE": 1, "RESERVE": 2, "EXHAUSTED": 3}[s] for s in states]
        self.assertEqual(ranks, sorted(ranks))

    def test_velocity_bad_timestamp_conserve(self) -> None:
        policy = self._velocity_policy_fixture(conserve_at=60)
        if paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.exists():
            paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.unlink()
        bad_path = paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_text(
            json.dumps({
                "worker_id": "grok_bot_sub",
                "included_usage_pct": {"weekly": 10},
                "observed_at": "not-an-iso-timestamp",
                "source": "owner_observed",
            })
            + "\n",
            encoding="utf-8",
        )
        with mock.patch.object(capacity, "_load_seed", return_value=[]):
            snap = capacity_snapshot("2026-10-06T10:35:00+08:00", policy=policy, policy_mode="ENFORCED")
        grok = snap["workers"]["grok_bot_sub"]
        self.assertIn(grok["state"], ("CONSERVE", "RESERVE", "EXHAUSTED"))
        audit = paths.GOVERNANCE_AUDIT_PATH.read_text() if paths.GOVERNANCE_AUDIT_PATH.exists() else ""
        self.assertIn("CAPACITY_OBSERVATION_REJECTED", audit)

    def test_velocity_reseed_values_exact(self) -> None:
        seed = json.loads(SEED_PATH.read_text())
        grok = [o for o in seed["observations"] if o["worker_id"] == "grok_bot_sub"]
        times = sorted(o["observed_at"] for o in grok)
        self.assertEqual(times, ["2026-10-06T09:49:00+08:00", "2026-10-06T10:34:00+08:00"])
        pcts = {o["observed_at"]: o["included_usage_pct"]["weekly"] for o in grok}
        self.assertEqual(pcts["2026-10-06T09:49:00+08:00"], 41)
        self.assertEqual(pcts["2026-10-06T10:34:00+08:00"], 49)

    def test_velocity_conduct_flags_present(self) -> None:
        _set_grok_pct(49.0, now="2026-10-06T10:34:00+08:00")
        d = _decide("coding", id="vel-conduct", now="2026-10-06T10:35:00+08:00")
        self.assertIsNotNone(d.grok_conserve_conduct)
        self.assertTrue(d.grok_conserve_conduct.get("no_grok_when_other_qualified"))
        self.assertEqual(d.grok_conserve_conduct.get("polling"), "FORBIDDEN")
        self.assertEqual(d.completion_event_format, "COMPACT")

    def test_velocity_routine_review_never_grok_under_conserve(self) -> None:
        _set_grok_pct(49.0, now="2026-10-06T10:34:00+08:00")
        d = _decide(
            "routine_review",
            id="vel-routine",
            requested_worker="grok_bot_sub",
            grok_reason="EXPLICIT_JUSTIFIED",
            justification="x" * 25,
            now="2026-10-06T10:35:00+08:00",
        )
        self.assertNotEqual(d.selected_worker, "grok_bot_sub")
        self.assertEqual(d.decision, "DISPATCH")

    def test_velocity_final_gate_to_grok_under_conserve(self) -> None:
        _set_grok_pct(49.0, now="2026-10-06T10:34:00+08:00")
        d = _decide("final_gate", id="vel-final-gate", now="2026-10-06T10:35:00+08:00")
        self.assertEqual(d.decision, "DISPATCH")
        self.assertEqual(d.selected_worker, "grok_bot_sub")

    def test_velocity_polling_never_grok_under_conserve(self) -> None:
        _set_grok_pct(49.0, now="2026-10-06T10:34:00+08:00")
        d = _decide(
            "polling",
            id="vel-polling",
            requested_worker="grok_bot_sub",
            now="2026-10-06T10:35:00+08:00",
        )
        self.assertNotEqual(d.selected_worker, "grok_bot_sub")

    def test_velocity_requested_grok_ineligible_falls_back(self) -> None:
        _set_grok_pct(49.0, now="2026-10-06T10:34:00+08:00")
        d = _decide(
            "coding",
            id="vel-k2-fallback",
            requested_worker="grok_bot_sub",
            grok_reason="BENCHMARK_SELECTED",
            now="2026-10-06T10:35:00+08:00",
        )
        self.assertEqual(d.decision, "DISPATCH")
        self.assertNotEqual(d.selected_worker, "grok_bot_sub")
        self.assertIsNotNone(d.requested_worker_rejected)

    def test_peak_raw_pct_resets_after_weekly_drop(self) -> None:
        policy = self._velocity_policy_fixture(conserve_at=60)
        if paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.exists():
            paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.unlink()
        seed_patch = mock.patch.object(capacity, "_load_seed", return_value=[])
        future_reset = "2026-10-13T10:00:00+08:00"
        with seed_patch:
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 95},
                source="owner_observed",
                observed_at="2026-10-05T10:00:00+08:00",
                reset_at=future_reset,
            )
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 5},
                source="owner_observed",
                observed_at="2026-10-06T09:00:00+08:00",
                reset_at=future_reset,
            )
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 6},
                source="owner_observed",
                observed_at="2026-10-06T10:00:00+08:00",
                reset_at=future_reset,
            )
            now = "2026-10-06T10:05:00+08:00"
            snap = capacity_snapshot(now, policy=policy, policy_mode="ENFORCED")
        grok = snap["workers"]["grok_bot_sub"]
        self.assertEqual(grok["state"], "NORMAL")
        self.assertLessEqual(grok.get("effective_pct", 100), 10)

    def test_velocity_slow_drift_over_30h_stays_normal(self) -> None:
        policy = self._velocity_policy_fixture(conserve_at=60)
        if paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.exists():
            paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.unlink()
        future_reset = "2026-10-13T10:00:00+08:00"
        seed_patch = mock.patch.object(capacity, "_load_seed", return_value=[])
        with seed_patch:
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 41},
                source="owner_observed",
                observed_at="2026-10-05T04:00:00+08:00",
                reset_at=future_reset,
            )
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 49},
                source="owner_observed",
                observed_at="2026-10-06T10:00:00+08:00",
                reset_at=future_reset,
            )
            snap = capacity_snapshot("2026-10-06T10:05:00+08:00", policy=policy, policy_mode="ENFORCED")
        grok = snap["workers"]["grok_bot_sub"]
        self.assertEqual(grok["state"], "NORMAL")
        self.assertIs(grok.get("projected_exhaustion_before_reset"), False)

    def test_drop_no_reset_low_tail_retains_exhausted(self) -> None:
        policy = self._velocity_policy_fixture(conserve_at=60)
        if paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.exists():
            paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.unlink()
        with mock.patch.object(capacity, "_load_seed", return_value=[]):
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 96},
                source="owner_observed",
                observed_at="2026-10-06T10:00:00+08:00",
            )
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 5},
                source="owner_observed",
                observed_at="2026-10-06T11:15:00+08:00",
            )
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 6},
                source="owner_observed",
                observed_at="2026-10-06T11:30:00+08:00",
            )
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 7},
                source="owner_observed",
                observed_at="2026-10-06T12:00:00+08:00",
            )
            snap = capacity_snapshot("2026-10-06T12:00:00+08:00", policy=policy, policy_mode="ENFORCED")
        grok = snap["workers"]["grok_bot_sub"]
        self.assertEqual(grok["state"], "EXHAUSTED")

    def test_duplicate_timestamp_takes_conservative_peak(self) -> None:
        policy = self._velocity_policy_fixture(conserve_at=60)
        if paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.exists():
            paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.unlink()
        ts = "2026-10-06T10:00:00+08:00"
        with mock.patch.object(capacity, "_load_seed", return_value=[]):
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 96},
                source="owner_observed",
                observed_at=ts,
            )
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 5},
                source="owner_observed",
                observed_at=ts,
            )
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 5},
                source="owner_observed",
                observed_at=ts,
            )
            snap = capacity_snapshot("2026-10-06T10:05:00+08:00", policy=policy, policy_mode="ENFORCED")
        grok = snap["workers"]["grok_bot_sub"]
        self.assertEqual(grok["state"], "EXHAUSTED")

    def test_k2_fallback_dispatches_at_high_penalty(self) -> None:
        just = "x" * 25
        _set_grok_pct(49.0, now="2026-10-06T10:34:00+08:00")
        policy = load_policy().policy
        save_tightening({"grok_routing_penalty": 0.8}, policy)
        d = _decide(
            "coding",
            id="vel-k2-penalty-08",
            requested_worker="grok_bot_sub",
            grok_reason="EXPLICIT_JUSTIFIED",
            justification=just,
            now="2026-10-06T10:35:00+08:00",
        )
        self.assertEqual(d.decision, "DISPATCH")
        self.assertNotEqual(d.selected_worker, "grok_bot_sub")
        self.assertEqual(d.grok_reason_verdict, "REJECTED")
        self.assertIn("GROK_CONSERVE_CONDUCT", d.requested_worker_rejected or "")

    def test_conserve_conduct_grok_verdict_rejected_with_fallback(self) -> None:
        just = "x" * 25
        policy = self._velocity_policy_fixture(conserve_at=60)
        if paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.exists():
            paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.unlink()
        future_reset = "2026-10-13T10:00:00+08:00"
        with mock.patch.object(capacity, "_load_seed", return_value=[]):
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 41},
                source="owner_observed",
                observed_at="2026-10-06T09:50:00+08:00",
                reset_at=future_reset,
            )
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 49},
                source="owner_observed",
                observed_at="2026-10-06T10:34:00+08:00",
                reset_at=future_reset,
            )
            snap = capacity_snapshot(
                "2026-10-06T10:35:00+08:00",
                policy=policy,
                policy_mode="ENFORCED",
            )
        save_tightening({"grok_routing_penalty": 0.0}, policy)
        d = decide(
            {
                "id": "vel-k2-penalty-0",
                "task_class": "coding",
                "requested_worker": "grok_bot_sub",
                "grok_reason_code": "EXPLICIT_JUSTIFIED",
                "grok_justification": just,
            },
            policy_load=load_policy(),
            capacity=snap,
            now="2026-10-06T10:35:00+08:00",
            record=False,
        )
        self.assertEqual(d.decision, "DISPATCH")
        self.assertNotEqual(d.selected_worker, "grok_bot_sub")
        self.assertEqual(d.grok_reason_verdict, "REJECTED")
        self.assertIsNotNone(d.requested_worker_rejected)

    def test_velocity_sparse_flat_plateau_does_not_reserve(self) -> None:
        policy = self._velocity_policy_fixture(conserve_at=60)
        if paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.exists():
            paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.unlink()
        future_reset = "2026-10-13T10:00:00+08:00"
        with mock.patch.object(capacity, "_load_seed", return_value=[]):
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 41},
                source="owner_observed",
                observed_at="2026-10-06T10:00:00+08:00",
                reset_at=future_reset,
            )
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 46},
                source="owner_observed",
                observed_at="2026-10-06T10:01:00+08:00",
                reset_at=future_reset,
            )
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 46},
                source="owner_observed",
                observed_at="2026-10-06T20:01:00+08:00",
                reset_at=future_reset,
            )
            snap = capacity_snapshot("2026-10-06T20:05:00+08:00", policy=policy, policy_mode="ENFORCED")
        grok = snap["workers"]["grok_bot_sub"]
        self.assertEqual(grok["state"], "NORMAL")
        self.assertIs(grok.get("projected_exhaustion_before_reset"), False)
        self.assertEqual((grok.get("velocity") or {}).get("pct_per_hour"), 0.0)

    def test_conserve_conduct_grok_verdict_rejected_without_velocity(self) -> None:
        just = "x" * 25
        policy = self._velocity_policy_fixture(conserve_at=60)
        if paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.exists():
            paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.unlink()
        with mock.patch.object(capacity, "_load_seed", return_value=[]):
            snap = capacity_snapshot("2026-10-06T10:35:00+08:00", policy=policy, policy_mode="ENFORCED")
        grok_cap = snap["workers"]["grok_bot_sub"]
        grok_cap.pop("velocity", None)
        snap = dict(snap)
        snap["workers"] = dict(snap["workers"])
        snap["workers"]["grok_bot_sub"] = grok_cap
        save_tightening({"grok_routing_penalty": 0.0}, policy)
        d = decide(
            {
                "id": "vel-k2-no-velocity",
                "task_class": "coding",
                "requested_worker": "grok_bot_sub",
                "grok_reason_code": "EXPLICIT_JUSTIFIED",
                "grok_justification": just,
            },
            policy_load=load_policy(),
            capacity=snap,
            now="2026-10-06T10:35:00+08:00",
            record=False,
        )
        self.assertEqual(d.decision, "DISPATCH")
        self.assertNotEqual(d.selected_worker, "grok_bot_sub")
        self.assertEqual(d.grok_reason_verdict, "REJECTED")
        self.assertIsNotNone(d.requested_worker_rejected)

    def test_velocity_burst_then_flat_does_not_reserve(self) -> None:
        policy = self._velocity_policy_fixture(conserve_at=60)
        if paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.exists():
            paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.unlink()
        future_reset = "2026-10-13T10:00:00+08:00"
        with mock.patch.object(capacity, "_load_seed", return_value=[]):
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 41},
                source="owner_observed",
                observed_at="2026-10-06T10:00:00+08:00",
                reset_at=future_reset,
            )
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 46},
                source="owner_observed",
                observed_at="2026-10-06T10:01:00+08:00",
                reset_at=future_reset,
            )
            for hour in range(1, 11):
                record_observation(
                    worker_id="grok_bot_sub",
                    included_usage_pct={"weekly": 46},
                    source="owner_observed",
                    observed_at=f"2026-10-06T{10 + hour:02d}:01:00+08:00",
                    reset_at=future_reset,
                )
            snap = capacity_snapshot("2026-10-06T20:05:00+08:00", policy=policy, policy_mode="ENFORCED")
        grok = snap["workers"]["grok_bot_sub"]
        self.assertEqual(grok["state"], "NORMAL")
        self.assertIs(grok.get("projected_exhaustion_before_reset"), False)

    def test_velocity_one_minute_step_does_not_reserve(self) -> None:
        policy = self._velocity_policy_fixture(conserve_at=60)
        if paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.exists():
            paths.GOVERNANCE_CAPACITY_OBSERVATIONS_PATH.unlink()
        future_reset = "2026-10-13T10:00:00+08:00"
        with mock.patch.object(capacity, "_load_seed", return_value=[]):
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 41},
                source="owner_observed",
                observed_at="2026-10-06T10:00:00+08:00",
                reset_at=future_reset,
            )
            record_observation(
                worker_id="grok_bot_sub",
                included_usage_pct={"weekly": 42},
                source="owner_observed",
                observed_at="2026-10-06T10:01:00+08:00",
                reset_at=future_reset,
            )
            now = "2026-10-06T10:05:00+08:00"
            snap = capacity_snapshot(now, policy=policy, policy_mode="ENFORCED")
        grok = snap["workers"]["grok_bot_sub"]
        self.assertEqual(grok["state"], "NORMAL")
        self.assertIs(grok.get("projected_exhaustion_before_reset"), False)

    def test_r1_first_decision_baseline_survives_restart(self) -> None:
        """Fresh install: first decision writes tightening baseline; restart keeps default penalty."""
        for p in paths.GOVERNANCE_DIR.iterdir():
            if p.is_file():
                p.unlink()
        policy = load_policy().policy
        for i in range(22):
            dec, _ = allocation.decide_and_record({"id": f"r1-wi-{i}", "task_class": "coding"})
            self.assertEqual(dec.decision, "DISPATCH")
        self.assertTrue(paths.GOVERNANCE_TIGHTENING_PATH.exists())
        pen_before = float(load_tightening(policy)["grok_routing_penalty"])
        self.assertEqual(pen_before, 0.0)
        pen_after = float(load_tightening(policy)["grok_routing_penalty"])
        self.assertEqual(pen_after, 0.0)


if __name__ == "__main__":
    unittest.main()
