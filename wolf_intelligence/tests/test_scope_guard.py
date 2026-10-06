"""Worker execution scope guard tests."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import json

from wolf_intelligence.governance import GOVERNANCE_CONFIG_DIR, load_policy, validate_policy_invariants
from wolf_intelligence.scope_guard import check_invocation

HOME = Path.home()
SANDBOX = HOME / "wi-sandboxes"
WORKTREE = SANDBOX / "wi-gov-wt"
ZDOTDIR_EMPTY = SANDBOX / ".zdotdir-empty"
ALLOWED_ENV = {
    "PATH": "/usr/bin",
    "HOME": str(HOME),
    "USER": "test",
    "TERM": "xterm",
    "LANG": "C",
    "TMPDIR": str(SANDBOX / ".tmp"),
    "ZDOTDIR": str(ZDOTDIR_EMPTY),
}


class ScopeGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        pl = load_policy()
        self.policy = pl.policy

    def test_cursor_home_global_refused(self) -> None:
        ok, reasons = check_invocation(
            "cursor_sub",
            ["cursor-agent", "--workspace", str(HOME), "--mode", "ask"],
            str(HOME),
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("SCOPE_HOME_GLOBAL", reasons)

    def test_live_repo_workspace_refused(self) -> None:
        ok, reasons = check_invocation(
            "cursor_sub",
            ["cursor-agent", "--workspace", "/Users/wolfterminal/beta-os", "--mode", "ask"],
            "/Users/wolfterminal/beta-os",
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("SCOPE_LIVE_REPO", reasons)

    def test_scoped_worktree_ask_allowed(self) -> None:
        ws = str(WORKTREE)
        ok, reasons = check_invocation(
            "cursor_sub",
            ["cursor-agent", "--workspace", ws, "--mode", "ask", "--sandbox", "enabled"],
            ws,
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertTrue(ok, reasons)

    def test_force_outside_sandbox_refused(self) -> None:
        outside = tempfile.mkdtemp(prefix="wi-outside-", dir="/tmp")
        ok, reasons = check_invocation(
            "cursor_sub",
            ["cursor-agent", "--workspace", outside, "--force", "--mode", "ask"],
            outside,
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("BYPASS_OUTSIDE_SANDBOX", reasons)

    def test_force_inside_sandbox_with_isolated_env_allowed(self) -> None:
        ws = str(SANDBOX / "wi-gov-wt")
        ok, reasons = check_invocation(
            "cursor_sub",
            ["cursor-agent", "--workspace", ws, "--force", "--mode", "ask"],
            ws,
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertTrue(ok, reasons)

    def test_claude_without_permission_mode_refused(self) -> None:
        ws = str(WORKTREE)
        ok, reasons = check_invocation(
            "claude_pro_sub",
            ["claude", "-p"],
            ws,
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("CLAUDE_PERMISSION_MODE_IMPLICIT", reasons)

    def test_env_with_anthropic_key_refused_on_bypass(self) -> None:
        ws = str(WORKTREE)
        env = dict(ALLOWED_ENV)
        env["ANTHROPIC_API_KEY"] = "sk-test"
        ok, reasons = check_invocation(
            "cursor_sub",
            ["cursor-agent", "--workspace", ws, "--force"],
            ws,
            env,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertTrue("METERED_KEY_IN_ENV" in reasons or "ENV_NOT_ALLOWLISTED" in reasons)

    def test_missing_zdotdir_refused_for_bypass(self) -> None:
        ws = str(WORKTREE)
        env = {k: v for k, v in ALLOWED_ENV.items() if k != "ZDOTDIR"}
        ok, reasons = check_invocation(
            "cursor_sub",
            ["cursor-agent", "--workspace", ws, "--force"],
            ws,
            env,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("ZDOTDIR_NOT_ISOLATED", reasons)

    def test_codex_workspace_write_outside_sandbox_refused(self) -> None:
        outside = tempfile.mkdtemp(prefix="wi-codex-", dir="/tmp")
        ok, reasons = check_invocation(
            "codex_sub",
            ["codex", "exec", "-s", "workspace-write", "-C", outside],
            outside,
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("BYPASS_OUTSIDE_SANDBOX", reasons)

    def test_codex_read_only_in_worktree_allowed(self) -> None:
        ws = str(WORKTREE)
        ok, reasons = check_invocation(
            "codex_sub",
            ["codex", "exec", "-s", "read-only", "-C", ws],
            ws,
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertTrue(ok, reasons)

    def test_mixed_cd_flags_last_wins(self) -> None:
        denied = tempfile.mkdtemp(prefix="wi-denied-", dir="/tmp")
        ws = str(WORKTREE)
        ok, reasons = check_invocation(
            "codex_sub",
            ["codex", "exec", "-s", "read-only", "-C", ws, "--cd", denied],
            ws,
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertTrue(
            "SCOPE_DENIED_PATH" in reasons or "SCOPE_WORKSPACE_NOT_ALLOWED" in reasons,
            reasons,
        )

    def test_unknown_argv0_refused(self) -> None:
        ws = str(WORKTREE)
        ok, reasons = check_invocation(
            "codex_sub",
            ["unrecognised-executable", "codex", "exec", "-s", "read-only", "-C", ws],
            ws,
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("SCOPE_CLI_UNRECOGNIZED", reasons)

    def test_sandbox_root_force_refused(self) -> None:
        ws = str(WORKTREE)
        ok, reasons = check_invocation(
            "cursor_sub",
            ["cursor-agent", "--workspace", str(SANDBOX), "-f"],
            ws,
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("BYPASS_OUTSIDE_SANDBOX", reasons)

    def test_scope_glob_invariant_rejects_widening_patterns(self) -> None:
        base = json.loads((GOVERNANCE_CONFIG_DIR / "worker-allocation-policy.json").read_text())
        for bad_globs in (["~/*"], ["/Users/*"], ["/*"], ["~"]):
            policy = json.loads(json.dumps(base))
            policy["worker_execution_scope"]["allowed_workspace_globs"] = bad_globs
            errors = validate_policy_invariants(policy)
            self.assertTrue(
                any("allowed_workspace_globs cannot widen scope" in e for e in errors),
                f"expected rejection for {bad_globs}: {errors}",
            )

    def test_codex_bypass_with_home_cwd_refused(self) -> None:
        ws = str(WORKTREE)
        ok, reasons = check_invocation(
            "codex_sub",
            ["codex", "exec", "--full-auto", "-C", ws],
            str(HOME),
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("SCOPE_HOME_GLOBAL", reasons)

    def test_codex_bypass_with_live_repo_cwd_refused(self) -> None:
        ws = str(WORKTREE)
        ok, reasons = check_invocation(
            "codex_sub",
            ["codex", "exec", "--full-auto", "-C", ws],
            "/Users/wolfterminal/beta-os",
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("SCOPE_LIVE_REPO", reasons)

    def test_cursor_force_with_home_cwd_refused(self) -> None:
        ws = str(WORKTREE)
        ok, reasons = check_invocation(
            "cursor_sub",
            ["cursor-agent", "--workspace", ws, "--force"],
            str(HOME),
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("SCOPE_HOME_GLOBAL", reasons)

    def test_mixed_cd_denied_first_refused(self) -> None:
        ws = str(WORKTREE)
        ok, reasons = check_invocation(
            "codex_sub",
            ["codex", "exec", "-s", "read-only", "-C", "/Users/wolfterminal/beta-os", "--cd", ws],
            ws,
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("SCOPE_LIVE_REPO", reasons)

    def test_unknown_cursor_substring_refused(self) -> None:
        ws = str(WORKTREE)
        ok, reasons = check_invocation(
            "cursor_sub",
            ["qa-unknown-cursor-agent", "--workspace", ws],
            ws,
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("SCOPE_CLI_UNRECOGNIZED", reasons)

    def test_sandbox_root_cwd_and_target_workspace_write_refused(self) -> None:
        policy = json.loads(json.dumps(self.policy))
        policy["worker_execution_scope"]["allowed_workspace_globs"] = []
        ok, reasons = check_invocation(
            "codex_sub",
            ["codex", "exec", "-s", "workspace-write", "-C", str(SANDBOX)],
            str(SANDBOX),
            ALLOWED_ENV,
            policy=policy,
        )
        self.assertFalse(ok)
        self.assertIn("BYPASS_OUTSIDE_SANDBOX", reasons)

    def test_sandbox_root_cwd_and_target_force_refused(self) -> None:
        policy = json.loads(json.dumps(self.policy))
        policy["worker_execution_scope"]["allowed_workspace_globs"] = []
        ok, reasons = check_invocation(
            "cursor_sub",
            ["cursor-agent", "--workspace", str(SANDBOX), "--force"],
            str(SANDBOX),
            ALLOWED_ENV,
            policy=policy,
        )
        self.assertFalse(ok)
        self.assertIn("BYPASS_OUTSIDE_SANDBOX", reasons)

    def test_sandbox_root_cwd_with_flag_worktree_refused_on_bypass(self) -> None:
        ws = str(WORKTREE)
        ok, reasons = check_invocation(
            "codex_sub",
            ["codex", "exec", "--full-auto", "-C", ws],
            str(SANDBOX),
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("BYPASS_OUTSIDE_SANDBOX", reasons)

    def test_scope_glob_invariant_rejects_fnmatch_widening(self) -> None:
        base = json.loads((GOVERNANCE_CONFIG_DIR / "worker-allocation-policy.json").read_text())
        for bad_globs in (["~/**"], ["~/D*"], ["~/Pictures/**"], ["~/wi-secret/**"]):
            policy = json.loads(json.dumps(base))
            policy["worker_execution_scope"]["allowed_workspace_globs"] = bad_globs
            errors = validate_policy_invariants(policy)
            self.assertTrue(
                any("allowed_workspace_globs cannot widen scope" in e for e in errors),
                f"expected rejection for {bad_globs}: {errors}",
            )

    def test_scope_glob_invariant_rejects_wildcard_above_sandbox_root(self) -> None:
        base = json.loads((GOVERNANCE_CONFIG_DIR / "worker-allocation-policy.json").read_text())
        for bad_globs in (["~/wi-good-wt*/**"], ["~/wi-sandboxes*/*"], ["~/wi-sandbox*/**"]):
            policy = json.loads(json.dumps(base))
            policy["worker_execution_scope"]["allowed_workspace_globs"] = bad_globs
            errors = validate_policy_invariants(policy)
            self.assertTrue(
                any("allowed_workspace_globs cannot widen scope" in e for e in errors),
                f"expected rejection for {bad_globs}: {errors}",
            )

    def test_wi_secret_outside_allowed_globs_refused(self) -> None:
        secret = HOME / "wi-secret"
        ok, reasons = check_invocation(
            "codex_sub",
            ["codex", "exec", "-s", "read-only", "-C", str(secret)],
            str(secret),
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("SCOPE_WORKSPACE_NOT_ALLOWED", reasons)

    def test_sandbox_root_default_globs_workspace_write_refused(self) -> None:
        ok, reasons = check_invocation(
            "codex_sub",
            ["codex", "exec", "-s", "workspace-write", "-C", str(SANDBOX)],
            str(SANDBOX),
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("BYPASS_OUTSIDE_SANDBOX", reasons)

    def test_sandbox_root_default_globs_force_refused(self) -> None:
        ok, reasons = check_invocation(
            "cursor_sub",
            ["cursor-agent", "--workspace", str(SANDBOX), "--force"],
            str(SANDBOX),
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertIn("BYPASS_OUTSIDE_SANDBOX", reasons)

    def test_pictures_workspace_refused(self) -> None:
        pictures = str(HOME / "Pictures")
        ok, reasons = check_invocation(
            "cursor_sub",
            ["cursor-agent", "--workspace", pictures, "--mode", "ask"],
            pictures,
            ALLOWED_ENV,
            policy=self.policy,
        )
        self.assertFalse(ok)
        self.assertTrue(
            "SCOPE_WORKSPACE_NOT_ALLOWED" in reasons or "SCOPE_HOME_GLOBAL" in reasons,
            reasons,
        )

    def test_missing_policy_section_fail_closed(self) -> None:
        policy = dict(self.policy or {})
        policy.pop("worker_execution_scope", None)
        ok, reasons = check_invocation(
            "cursor_sub",
            ["cursor-agent", "--workspace", str(WORKTREE)],
            str(WORKTREE),
            ALLOWED_ENV,
            policy=policy,
        )
        self.assertFalse(ok)
        self.assertIn("SCOPE_POLICY_FAIL_CLOSED", reasons)


if __name__ == "__main__":
    unittest.main()
