"""Worker execution scope guard tests."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from wolf_intelligence.governance import load_policy
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
