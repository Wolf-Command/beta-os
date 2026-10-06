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

SECRET_ENV_RE = re.compile(r"(API_KEY|_TOKEN|SECRET)", re.IGNORECASE)
KNOWN_SECRET_KEYS = frozenset({
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY", "CODEX_API_KEY",
    "XAI_API_KEY", "GROK_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "CURSOR_API_KEY",
})


def _expand(path: str, base: Path | None = None) -> Path:
    p = Path(os.path.expanduser(path))
    if not p.is_absolute() and base is not None:
        p = base / p
    return p.resolve()


def _resolve_cwd(cwd: str) -> Path | None:
    p = Path(os.path.expanduser(cwd))
    if not p.is_absolute():
        return None
    return p.resolve()


def _scope_config(policy: dict[str, Any] | None) -> dict[str, Any]:
    defaults = fail_closed_policy().get("worker_execution_scope") or {}
    if policy is None:
        return defaults
    if "worker_execution_scope" not in policy:
        return {}
    cfg = policy.get("worker_execution_scope")
    if not isinstance(cfg, dict):
        return {}
    return {**defaults, **cfg}


def _detect_cli(argv: list[str]) -> str | None:
    for part in argv:
        name = Path(part).name.lower()
        if name in ("cursor-agent", "cursor") or "cursor-agent" in name or name == "cursor":
            return "cursor"
        if name == "codex" or name.startswith("codex"):
            return "codex"
        if name == "claude" or name.startswith("claude"):
            return "claude"
    if not argv:
        return None
    name = Path(argv[0]).name.lower()
    if "cursor" in name:
        return "cursor"
    if "codex" in name:
        return "codex"
    if "claude" in name:
        return "claude"
    return None


def _all_flag_values(argv: list[str], flag: str) -> list[str]:
    short = flag if flag.startswith("-") else f"--{flag}"
    vals: list[str] = []
    i = 0
    while i < len(argv):
        part = argv[i]
        if part == short and i + 1 < len(argv):
            vals.append(argv[i + 1])
            i += 2
            continue
        if part.startswith(short + "="):
            vals.append(part.split("=", 1)[1])
        i += 1
    return vals


def _last_flag_value(argv: list[str], flag: str) -> str | None:
    vals = _all_flag_values(argv, flag)
    return vals[-1] if vals else None


def _collect_add_dirs(argv: list[str], base: Path) -> list[Path]:
    paths: list[Path] = []
    i = 0
    while i < len(argv):
        part = argv[i]
        if part == "--add-dir":
            i += 1
            while i < len(argv) and not argv[i].startswith("-"):
                paths.append(_expand(argv[i], base))
                i += 1
            continue
        if part.startswith("--add-dir="):
            paths.append(_expand(part.split("=", 1)[1], base))
        i += 1
    return paths


def _workspace_paths(argv: list[str], cwd: Path) -> list[Path]:
    paths: list[Path] = []
    cli = _detect_cli(argv)
    if cli == "cursor":
        ws = _last_flag_value(argv, "--workspace")
        paths.append(_expand(ws or str(cwd), cwd if ws and not Path(os.path.expanduser(ws)).is_absolute() else None))
    elif cli == "codex":
        ws = (
            _last_flag_value(argv, "-C")
            or _last_flag_value(argv, "--cd")
            or _last_flag_value(argv, "--cwd")
        )
        paths.append(_expand(ws or str(cwd), cwd if ws and not Path(os.path.expanduser(ws)).is_absolute() else None))
    else:
        paths.append(cwd)
    paths.extend(_collect_add_dirs(argv, cwd))
    return paths


def _flag_conflict(argv: list[str], flag: str) -> bool:
    vals = _all_flag_values(argv, flag)
    return len(vals) > 1 and len(set(vals)) > 1


def _codex_sandbox_modes(argv: list[str]) -> list[str]:
    modes = _all_flag_values(argv, "-s") + _all_flag_values(argv, "--sandbox")
    if "danger-full-access" in argv:
        modes.append("danger-full-access")
    return modes


def _has_bypass(argv: list[str]) -> bool:
    cli = _detect_cli(argv)
    if cli == "cursor":
        if _flag_conflict(argv, "--force") or _flag_conflict(argv, "--yolo"):
            return True
        return any(f in argv for f in ("--force", "--yolo", "-f"))
    if cli == "codex":
        if "--dangerously-bypass-approvals-and-sandbox" in argv:
            return True
        if "--full-auto" in argv:
            return True
        if _flag_conflict(argv, "-s") or _flag_conflict(argv, "--sandbox"):
            return True
        modes = _codex_sandbox_modes(argv)
        return any(m in ("danger-full-access", "workspace-write") for m in modes)
    if cli == "claude":
        if "--dangerously-skip-permissions" in argv:
            return True
        if _flag_conflict(argv, "--permission-mode"):
            return True
        mode = _last_flag_value(argv, "--permission-mode")
        return mode == "bypassPermissions"
    return False


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


def _strict_worktree(path: Path, sandbox_root: Path, zdotdir_empty: Path) -> bool:
    if path == sandbox_root:
        return False
    if path == zdotdir_empty or zdotdir_empty in path.parents:
        return False
    return _under_sandbox(path, sandbox_root)


def _path_allowed(
    path: Path,
    *,
    sandbox_root: Path,
    zdotdir_empty: Path,
    globs: list[str],
    allow_temp: bool,
    allow_sandbox_root: bool = False,
) -> bool:
    if path == sandbox_root:
        return allow_sandbox_root
    if _strict_worktree(path, sandbox_root, zdotdir_empty):
        return True
    if allow_temp and _under_sandbox(path, sandbox_root) and path != sandbox_root:
        if path == zdotdir_empty or zdotdir_empty in path.parents:
            return False
        return True
    return _glob_allowed(path, globs)


def _env_secret_violation(env: dict[str, str]) -> list[str]:
    reasons: list[str] = []
    for key, val in env.items():
        if not val:
            continue
        if key in KNOWN_SECRET_KEYS or SECRET_ENV_RE.search(key):
            reasons.append("METERED_KEY_IN_ENV")
            break
    return reasons


def _env_allowed(env: dict[str, str], allowlist: list[str]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    allowed = set(allowlist)
    for key in env:
        if key not in allowed:
            reasons.append("ENV_NOT_ALLOWLISTED")
            break
    reasons.extend(_env_secret_violation(env))
    return (not reasons, reasons)


def _zdotdir_isolated(zdot: str, zdotdir_empty: Path) -> bool:
    if not zdot:
        return False
    resolved = _expand(zdot)
    if resolved != zdotdir_empty:
        return False
    if not resolved.is_dir():
        return False
    try:
        return not any(resolved.iterdir())
    except OSError:
        return False


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
    cwd_path = _resolve_cwd(cwd)
    if cwd_path is None:
        reasons.append("SCOPE_CWD_NOT_ABSOLUTE")

    sandbox_root = _expand(str(cfg.get("isolated_sandbox_root", HOME / "wi-sandboxes")))
    zdotdir_empty = _expand(str(cfg.get("zdotdir_empty", sandbox_root / ".zdotdir-empty")))
    denied = [_expand(str(p)) for p in (cfg.get("denied_paths") or [])]
    globs = list(cfg.get("allowed_workspace_globs") or [])
    allow_temp = bool(cfg.get("allowed_temp_under_sandbox", True))
    env_allowlist = list(cfg.get("env_allowlist") or ["PATH", "HOME", "USER", "TERM", "LANG", "TMPDIR", "ZDOTDIR"])

    cli = _detect_cli(argv)
    if cli is None:
        reasons.append("SCOPE_CLI_UNRECOGNIZED")

    reasons.extend(_env_secret_violation(env))

    if cli == "codex" and "danger-full-access" in _codex_sandbox_modes(argv):
        reasons.append("CODEX_DANGER_FULL_ACCESS")

    bypass = _has_bypass(argv)
    zdot = env.get("ZDOTDIR", "")
    zdot_ok = _zdotdir_isolated(zdot, zdotdir_empty)
    allow_sandbox_root = bypass and zdot_ok

    if cwd_path is not None:
        for ws in _workspace_paths(argv, cwd_path):
            if ws == HOME or ws == Path("/"):
                reasons.append("SCOPE_HOME_GLOBAL")
            if ws == BETA or BETA in ws.parents:
                reasons.append("SCOPE_LIVE_REPO")
            for deny in denied:
                if ws == deny or deny in ws.parents or ws == deny:
                    if deny == BETA or BETA in deny.parents:
                        reasons.append("SCOPE_LIVE_REPO")
                    else:
                        reasons.append("SCOPE_DENIED_PATH")
            if not _path_allowed(
                ws,
                sandbox_root=sandbox_root,
                zdotdir_empty=zdotdir_empty,
                globs=globs,
                allow_temp=allow_temp,
                allow_sandbox_root=allow_sandbox_root and ws == sandbox_root,
            ):
                reasons.append("SCOPE_WORKSPACE_NOT_ALLOWED")

    if cli == "claude":
        if "--permission-mode" not in argv:
            reasons.append("CLAUDE_PERMISSION_MODE_IMPLICIT")
        if _flag_conflict(argv, "--permission-mode"):
            reasons.append("SCOPE_FLAG_CONFLICT")

    if cli == "codex" and (_flag_conflict(argv, "-s") or _flag_conflict(argv, "--sandbox")):
        reasons.append("SCOPE_FLAG_CONFLICT")

    if cli == "cursor" and (_flag_conflict(argv, "--force") or _flag_conflict(argv, "--yolo")):
        reasons.append("SCOPE_FLAG_CONFLICT")

    codex_modes = _codex_sandbox_modes(argv)
    if cli == "codex" and "workspace-write" in codex_modes and cwd_path is not None:
        if not all(
            _strict_worktree(p, sandbox_root, zdotdir_empty)
            for p in _workspace_paths(argv, cwd_path)
        ):
            reasons.append("BYPASS_OUTSIDE_SANDBOX")

    if bypass and cwd_path is not None:
        if not all(
            _strict_worktree(p, sandbox_root, zdotdir_empty)
            or (allow_sandbox_root and p == sandbox_root)
            or (allow_temp and _under_sandbox(p, sandbox_root) and p != sandbox_root)
            for p in _workspace_paths(argv, cwd_path)
        ):
            reasons.append("BYPASS_OUTSIDE_SANDBOX")
        ok_env, env_reasons = _env_allowed(env, env_allowlist)
        if not ok_env:
            reasons.extend(env_reasons)
        if not zdot_ok:
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
