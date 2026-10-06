"""Worker execution scope guard — workspace and env isolation before CLI spawn."""
from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any

from .governance import fail_closed_policy, load_policy

HOME = Path.home()
BETA = Path("/Users/wolfterminal/beta-os")

BYPASS_FLAGS = {
    "cursor": {"--force", "--yolo"},
    "codex": {"--dangerously-bypass-approvals-and-sandbox", "-s"},
    "claude": {"--dangerously-skip-permissions", "--permission-mode"},
}

SECRET_ENV_RE = re.compile(r"(API_KEY|_TOKEN|SECRET)", re.IGNORECASE)


def _expand(path: str) -> Path:
    return Path(os.path.expanduser(path)).resolve()


def _scope_config(policy: dict[str, Any] | None) -> dict[str, Any]:
    defaults = fail_closed_policy().get("worker_execution_scope") or {}
    if not policy:
        return defaults
    cfg = policy.get("worker_execution_scope")
    if not isinstance(cfg, dict):
        return {}
    return {**defaults, **cfg}


def _detect_cli(argv: list[str]) -> str | None:
    if not argv:
        return None
    name = Path(argv[0]).name
    if "cursor" in name:
        return "cursor"
    if "codex" in name:
        return "codex"
    if "claude" in name:
        return "claude"
    return None


def _flag_value(argv: list[str], flag: str) -> str | None:
    for i, part in enumerate(argv):
        if part == flag and i + 1 < len(argv):
            return argv[i + 1]
        if part.startswith(flag + "="):
            return part.split("=", 1)[1]
    return None


def _workspace_paths(argv: list[str], cwd: str) -> list[Path]:
    paths: list[Path] = []
    cli = _detect_cli(argv)
    if cli == "cursor":
        ws = _flag_value(argv, "--workspace")
        paths.append(_expand(ws or cwd))
    elif cli == "codex":
        ws = _flag_value(argv, "-C") or _flag_value(argv, "--cwd")
        paths.append(_expand(ws or cwd))
    else:
        paths.append(_expand(cwd))
    i = 0
    while i < len(argv):
        if argv[i] == "--add-dir" and i + 1 < len(argv):
            paths.append(_expand(argv[i + 1]))
            i += 2
            continue
        i += 1
    return paths


def _has_bypass(argv: list[str]) -> bool:
    cli = _detect_cli(argv)
    if cli == "cursor":
        return any(f in argv for f in ("--force", "--yolo"))
    if cli == "codex":
        if "--dangerously-bypass-approvals-and-sandbox" in argv:
            return True
        mode = _flag_value(argv, "-s")
        return mode in ("danger-full-access", "workspace-write")
    if cli == "claude":
        if "--dangerously-skip-permissions" in argv:
            return True
        mode = _flag_value(argv, "--permission-mode")
        return mode == "bypassPermissions"
    return False


def _codex_sandbox_mode(argv: list[str]) -> str | None:
    if _detect_cli(argv) != "codex":
        return None
    return _flag_value(argv, "-s")


def _glob_allowed(path: Path, globs: list[str]) -> bool:
    s = str(path)
    home_s = str(HOME)
    for pattern in globs:
        pat = os.path.expanduser(pattern)
        if fnmatch.fnmatch(s, pat) or fnmatch.fnmatch(s, str(_expand(pat))):
            return True
        if pat.startswith("~/") and fnmatch.fnmatch(s, pat.replace("~", home_s, 1)):
            return True
    return False


def _under_sandbox(path: Path, sandbox_root: Path) -> bool:
    try:
        return path.is_relative_to(sandbox_root)
    except AttributeError:
        return str(path).startswith(str(sandbox_root))


def _env_allowed(env: dict[str, str], allowlist: list[str]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    allowed = set(allowlist)
    for key in env:
        if key not in allowed:
            reasons.append("ENV_NOT_ALLOWLISTED")
            break
        if SECRET_ENV_RE.search(key):
            reasons.append("METERED_KEY_IN_ENV")
            break
    for secret_key in (
        "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY", "CODEX_API_KEY",
    ):
        if env.get(secret_key):
            reasons.append("METERED_KEY_IN_ENV")
            break
    return (not reasons, reasons)


def check_invocation(
    worker_id: str,
    argv: list[str],
    cwd: str,
    env: dict[str, str],
    *,
    policy: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    """Return (ok, machine-readable reason codes). FAIL_CLOSED when policy section missing."""
    pl = load_policy() if policy is None else None
    effective = policy if policy is not None else (pl.policy if pl and pl.policy else None)
    cfg = _scope_config(effective)
    if not cfg:
        return False, ["SCOPE_POLICY_FAIL_CLOSED"]

    reasons: list[str] = []
    sandbox_root = _expand(str(cfg.get("isolated_sandbox_root", HOME / "wi-sandboxes")))
    zdotdir_empty = _expand(str(cfg.get("zdotdir_empty", sandbox_root / ".zdotdir-empty")))
    denied = [_expand(str(p)) for p in (cfg.get("denied_paths") or [])]
    globs = list(cfg.get("allowed_workspace_globs") or [])
    allow_temp = bool(cfg.get("allowed_temp_under_sandbox", True))
    env_allowlist = list(cfg.get("env_allowlist") or ["PATH", "HOME", "USER", "TERM", "LANG", "TMPDIR", "ZDOTDIR"])

    for ws in _workspace_paths(argv, cwd):
        if ws == HOME:
            reasons.append("SCOPE_HOME_GLOBAL")
        if ws == Path("/"):
            reasons.append("SCOPE_HOME_GLOBAL")
        if ws == BETA or BETA in ws.parents:
            reasons.append("SCOPE_LIVE_REPO")
        for deny in denied:
            if ws == deny or deny in ws.parents:
                if deny == BETA or BETA in deny.parents:
                    reasons.append("SCOPE_LIVE_REPO")
                else:
                    reasons.append("SCOPE_DENIED_PATH")
        allowed = _glob_allowed(ws, globs)
        if allow_temp and _under_sandbox(ws, sandbox_root):
            allowed = True
        if not allowed:
            reasons.append("SCOPE_WORKSPACE_NOT_ALLOWED")

    cli = _detect_cli(argv)
    if cli == "claude" and "--permission-mode" not in argv:
        reasons.append("CLAUDE_PERMISSION_MODE_IMPLICIT")

    codex_mode = _codex_sandbox_mode(argv)
    if codex_mode == "workspace-write":
        if not all(_under_sandbox(p, sandbox_root) for p in _workspace_paths(argv, cwd)):
            reasons.append("BYPASS_OUTSIDE_SANDBOX")

    bypass = _has_bypass(argv)
    if bypass:
        if not all(_under_sandbox(p, sandbox_root) for p in _workspace_paths(argv, cwd)):
            reasons.append("BYPASS_OUTSIDE_SANDBOX")
        ok_env, env_reasons = _env_allowed(env, env_allowlist)
        if not ok_env:
            reasons.extend(env_reasons)
        zdot = env.get("ZDOTDIR", "")
        if not zdot or _expand(zdot) != zdotdir_empty:
            reasons.append("ZDOTDIR_NOT_ISOLATED")

    return (len(reasons) == 0, sorted(set(reasons)))


def scope_check_json(argv: list[str], cwd: str, env: dict[str, str]) -> dict[str, Any]:
    pl = load_policy()
    policy = pl.policy if pl.mode == "ENFORCED" else None
    ok, reasons = check_invocation("cli", argv, cwd, env, policy=policy)
    return {
        "ok": ok,
        "reasons": reasons,
        "policy_mode": pl.mode,
        "env_keys": sorted(env.keys()),
    }
