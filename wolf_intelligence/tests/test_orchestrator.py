"""Unit tests for non-Grok orchestrator control plane."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from wolf_intelligence import orchestrator as orch
from wolf_intelligence.governance import GROK_WORKER_ID, load_policy
from wolf_intelligence.paths import rebind_state_paths
from wolf_intelligence import failover
from wolf_intelligence.scope_guard import build_worker_env, check_invocation

FIXTURES = Path(__file__).resolve().parent / "fixtures"
OK_WORKER = str(FIXTURES / "orch_worker_ok.py")
FAIL_WORKER = str(FIXTURES / "orch_worker_fail.py")
SLOW_WORKER = str(FIXTURES / "orch_worker_slow.py")
IGNORE_TERM_WORKER = str(FIXTURES / "orch_worker_ignore_term.py")


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
                "allow_fixture_workers": True,
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
        self.assertIn("wi-build-1-review-1", orch.load_items())
        self.assertEqual(orch.show("wi-build-1-review-1")["status"], "CLOSED")

    def test_exactly_once_double_claim_refused(self) -> None:
        self._submit_build()
        claimed, key = orch.claim("wi-build-1", now="2026-10-06T12:00:01+08:00")
        self.assertIsNotNone(claimed)
        second, reason = orch.claim("wi-build-1", now="2026-10-06T12:00:01+08:00")
        self.assertIsNone(second)
        self.assertEqual(reason, "lease_active")
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
        self.assertEqual(out["idempotency_key"], "wi-build-1:1")

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
        self.assertEqual(orch.show("wi-build-1-review-1")["status"], "CLOSED")

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
        self.assertEqual(orch.show("wi-build-2-review-1")["status"], "FAILED")
        cfg["worker_cmds"]["codex_sub"][3] = "PASS"
        orch.save_config(cfg)
        orch.run_once(now="2026-10-06T12:10:02+08:00")
        self.assertEqual(orch.show("wi-build-2")["status"], "CLOSED")
        self.assertEqual(orch.show("wi-build-2-review-2")["status"], "CLOSED")

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

    def test_fixture_worker_refused_without_allow_flag(self) -> None:
        cfg = orch.load_config()
        cfg.pop("allow_fixture_workers", None)
        orch.save_config(cfg)
        self._submit_build(reviewer_gate=False)
        out = orch.run_once(now="2026-10-06T12:00:01+08:00")
        self.assertEqual(out["processed"][0]["status"], "FAILED")
        self.assertIn("fixture_worker_refused", out["processed"][0]["completion"]["EXCEPTIONS"])
        comp = list(orch.COMPLETIONS_DIR.glob("wi-build-1-1.json"))[0]
        rec = json.loads(comp.read_text())
        self.assertIn(OK_WORKER, rec["EXECUTED_BY"])

    def test_real_worker_cmd_has_no_fixture_path(self) -> None:
        cfg = {"worktree_cwd": self.worktree}
        item = {"id": "wi-real-1", "kind": "build", "attempt": 1, "spec": {"prompt": "x", "model": "composer-2.5"}}
        argv = orch._worker_cmd("cursor_sub", cfg, item, self.worktree)
        self.assertFalse(orch.is_fixture_worker_cmd(argv))
        self.assertEqual(argv[0], "cursor-agent")
        review = {"id": "wi-real-1-review", "kind": "review", "attempt": 1, "spec": {"parent": "wi-real-1"}, "acceptance": "ok"}
        rargv = orch._worker_cmd("codex_sub", cfg, review, self.worktree)
        self.assertEqual(rargv[0], "codex")
        self.assertIn("read-only", rargv)
        self.assertIn("VERDICT", rargv[-1])
        build_argv = orch._worker_cmd("codex_sub", cfg, item, self.worktree)
        self.assertIn("workspace-write", build_argv)
        claude_review = orch._worker_cmd("claude_pro_sub", cfg, review, self.worktree)
        self.assertIn("--permission-mode", claude_review)
        self.assertEqual(claude_review[claude_review.index("--permission-mode") + 1], "plan")
        self.assertEqual(orch._worker_cmd("ollama_local", cfg, item, self.worktree), [])

    def test_build_awaits_review_before_close(self) -> None:
        self._submit_build()
        orch.claim("wi-build-1", now="2026-10-06T12:00:01+08:00")
        claimed = orch.show("wi-build-1")
        out = orch.dispatch_item(
            claimed,
            "cursor_sub",
            worktree=self.worktree,
            config=orch.load_config(),
            now="2026-10-06T12:00:01+08:00",
        )
        self.assertTrue(out["ok"])
        self.assertEqual(orch.show("wi-build-1")["status"], "AWAITING_REVIEW")
        self.assertIn("wi-build-1-review-1", orch.load_items())

    def test_concurrent_claim_one_wins(self) -> None:
        import threading

        self._submit_build()
        results: list[tuple[dict | None, str]] = []

        def _claim_worker() -> None:
            results.append(orch.claim("wi-build-1", now="2026-10-06T12:00:01+08:00"))

        t1 = threading.Thread(target=_claim_worker)
        t2 = threading.Thread(target=_claim_worker)
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)
        wins = [r for r in results if r[0] is not None]
        self.assertEqual(len(wins), 1)
        leases = orch.load_leases()
        active = [k for k, v in leases.items() if v.get("work_item_id") == "wi-build-1"]
        self.assertEqual(len(active), 1)

    def test_timeout_sigkill_within_grace(self) -> None:
        cfg = orch.load_config()
        cfg["worker_cmds"]["cursor_sub"] = ["python3", IGNORE_TERM_WORKER]
        cfg["timeout_kill_grace_s"] = 0.2
        orch.save_config(cfg)
        self._submit_build(timeout_s=1)
        started = time.perf_counter()
        out = orch.run_once(now="2026-10-06T12:00:01+08:00")
        elapsed = time.perf_counter() - started
        self.assertEqual(out["processed"][0]["status"], "TIMED_OUT")
        self.assertLess(elapsed, 3.0)

    def test_submit_preserves_context_and_urgent(self) -> None:
        rec = orch.submit(
            {
                "id": "wi-ctx",
                "kind": "build",
                "spec": {"prompt": "x"},
                "context_size": 120_000,
                "urgent": True,
                "acceptance": "ok",
                "reviewer_gate": False,
            },
            now="2026-10-06T12:00:00+08:00",
        )
        self.assertEqual(rec["context_size"], 120_000)
        self.assertTrue(rec["urgent"])

    def test_oversized_context_refused(self) -> None:
        orch.submit(
            {
                "id": "wi-huge",
                "kind": "build",
                "spec": {"prompt": "x"},
                "context_size": 9_999_999,
                "acceptance": "ok",
                "reviewer_gate": False,
            },
            now="2026-10-06T12:00:00+08:00",
        )
        item = orch.show("wi-huge")
        cap = orch.capacity_snapshot("2026-10-06T12:00:01+08:00", policy=load_policy().policy, policy_mode="ENFORCED")
        worker, reason = orch.eligibility(item, orch.load_items(), cap, orch.load_config(), now="2026-10-06T12:00:01+08:00")
        self.assertIsNone(worker)
        self.assertEqual(reason, "context_exceeded")

    def test_waiting_for_capacity_resumes_on_health(self) -> None:
        orch.submit(
            {
                "id": "wi-wait",
                "kind": "build",
                "spec": {"prompt": "x"},
                "acceptance": "ok",
                "reviewer_gate": False,
            },
            now="2026-10-06T12:00:00+08:00",
        )
        items = orch.load_items()
        items["wi-wait"]["status"] = "WAITING_FOR_CAPACITY"
        orch.save_items(items)
        with mock.patch.object(
            orch.failover,
            "decide_routing",
            return_value={"action": "WAITING_FOR_CAPACITY", "worker_id": None},
        ):
            self.assertEqual(orch.reevaluate_waiting_for_capacity(), [])
        self.assertEqual(orch.show("wi-wait")["status"], "WAITING_FOR_CAPACITY")
        with mock.patch.object(
            orch.failover,
            "decide_routing",
            return_value={"action": "DISPATCH", "worker_id": "cursor_sub"},
        ):
            resumed = orch.reevaluate_waiting_for_capacity(now="2026-10-06T12:00:06+08:00")
        self.assertEqual(resumed, ["wi-wait"])
        self.assertEqual(orch.show("wi-wait")["status"], "QUEUED")


class DispatchEnvTests(unittest.TestCase):
    """Real-dispatch env isolation — allowlist-only child env for scope guard."""

    SANDBOX = Path.home() / "wi-sandboxes"
    ZDOTDIR_EMPTY = SANDBOX / ".zdotdir-empty"

    def setUp(self) -> None:
        self._prev = os.environ.get("WOLF_INTELLIGENCE_STATE_ROOT")
        self.state_root = tempfile.mkdtemp(prefix="wi-dispatch-env-")
        os.environ["WOLF_INTELLIGENCE_STATE_ROOT"] = self.state_root
        rebind_state_paths()
        orch.rebind_orchestrator_paths()
        self.worktree = self.SANDBOX / "wi-orch-unit-wt"
        self.worktree.mkdir(parents=True, exist_ok=True)
        self.ZDOTDIR_EMPTY.mkdir(parents=True, exist_ok=True)
        self.policy = load_policy().policy

    def tearDown(self) -> None:
        shutil.rmtree(self.state_root, ignore_errors=True)
        shutil.rmtree(self.worktree / ".tmp", ignore_errors=True)
        if self._prev is None:
            os.environ.pop("WOLF_INTELLIGENCE_STATE_ROOT", None)
        else:
            os.environ["WOLF_INTELLIGENCE_STATE_ROOT"] = self._prev
        rebind_state_paths()

    def _minimal_parent(self, *, path_prefix: str = "/usr/bin") -> dict[str, str]:
        return {
            "PATH": path_prefix,
            "HOME": str(Path.home()),
            "USER": os.environ.get("USER", "test"),
            "TERM": "xterm",
            "LANG": "C",
        }

    def test_build_dispatch_env_allowlist_only(self) -> None:
        parent = {
            **self._minimal_parent(),
            "PWD": "/tmp",
            "SHLVL": "2",
            "OLDPWD": "/",
            "_": "/bin/env",
            "WI_TEST_STATE_ISOLATED": "/tmp/x",
            "WOLF_INTELLIGENCE_STATE_ROOT": self.state_root,
            "ZDOTDIR": "/wrong/zdot",
        }
        env, refused = build_worker_env(str(self.worktree), parent, policy=self.policy)
        self.assertEqual(
            set(env.keys()),
            {"PATH", "HOME", "USER", "TERM", "LANG", "TMPDIR", "ZDOTDIR"},
        )
        self.assertEqual(env["TMPDIR"], str(self.worktree / ".tmp"))
        self.assertEqual(env["ZDOTDIR"], str(self.ZDOTDIR_EMPTY.resolve()))
        self.assertIn("PWD", refused)
        self.assertIn("SHLVL", refused)
        self.assertIn("WI_TEST_STATE_ISOLATED", refused)
        self.assertIn("WOLF_INTELLIGENCE_STATE_ROOT", refused)

    def test_refused_env_key_names_reported(self) -> None:
        parent = {**self._minimal_parent(), "PWD": "/tmp", "WI_EXTRA": "1"}
        _, refused = build_worker_env(str(self.worktree), parent, policy=self.policy)
        reported = orch._env_refused_exceptions(refused)
        self.assertIn("env_refused:PWD", reported)
        self.assertIn("env_refused:WI_EXTRA", reported)
        for entry in reported:
            self.assertTrue(entry.startswith("env_refused:"))
            self.assertNotIn("=", entry.split(":", 1)[-1])

    def test_guard_passes_minimal_parent_env(self) -> None:
        parent = self._minimal_parent()
        env, refused = build_worker_env(str(self.worktree), parent, policy=self.policy)
        self.assertEqual(refused, [])
        item = {"id": "wi-scope-1", "kind": "build", "attempt": 1, "spec": {"prompt": "x", "model": "composer-2.5"}}
        cfg = {"worktree_cwd": str(self.worktree)}
        argv = orch._worker_cmd("cursor_sub", cfg, item, str(self.worktree))
        ok, reasons = check_invocation("cursor_sub", argv, str(self.worktree), env, policy=self.policy)
        self.assertTrue(ok, reasons)

    def test_real_dispatch_scope_passes_with_fake_cli(self) -> None:
        fake_bin = Path(tempfile.mkdtemp(prefix="wi-fake-cli-"))
        fake_cursor = fake_bin / "cursor-agent"
        fake_cursor.write_text("#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n", encoding="utf-8")
        fake_cursor.chmod(0o755)
        self.addCleanup(shutil.rmtree, fake_bin, True)

        fixture_dir = self.worktree / "fixture"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        (fixture_dir / "hello.py").write_text("def hello():\n    return 'hello'\n", encoding="utf-8")
        (fixture_dir / "test_hello.py").write_text(
            "from fixture.hello import hello\n\ndef test_hello():\n    assert hello() == 'hello'\n",
            encoding="utf-8",
        )

        orch.save_config({"claude_paused": True, "worktree_cwd": str(self.worktree)})
        item = orch.submit(
            {
                "id": "wi-real-scope",
                "kind": "build",
                "spec": {"prompt": "noop", "model": "composer-2.5"},
                "acceptance": "hello passes",
                "reviewer_gate": False,
                "timeout_s": 10,
                "max_attempts": 1,
            },
            now="2026-10-06T12:10:00+08:00",
        )
        claimed, _ = orch.claim("wi-real-scope", now="2026-10-06T12:10:01+08:00")
        self.assertIsNotNone(claimed)

        parent = self._minimal_parent(path_prefix=f"{fake_bin}:/usr/bin:/bin")
        with mock.patch.dict(os.environ, parent, clear=True):
            out = orch.dispatch_item(
                claimed,
                "cursor_sub",
                worktree=str(self.worktree),
                config=orch.load_config(),
                now="2026-10-06T12:10:02+08:00",
            )
        self.assertTrue(out.get("ok"), out)
        self.assertEqual(out.get("status"), "COMPLETED")
        comp = json.loads((orch.COMPLETIONS_DIR / "wi-real-scope-1.json").read_text())
        self.assertNotIn("ENV_NOT_ALLOWLISTED", comp.get("EXCEPTIONS", []))
        self.assertNotIn("ZDOTDIR_NOT_ISOLATED", comp.get("EXCEPTIONS", []))


if __name__ == "__main__":
    unittest.main()
