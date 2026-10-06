"""Subscription allowance probes (read-only w.r.t. credentials: no token files are read).

* Codex: one tiny non-ephemeral `codex exec` in a dedicated temp cwd; the CLI's own rollout file for THAT session
  (matched by cwd) carries the server-reported rate_limits (weekly window used_percent, plan_type).
* Claude Pro: the official CLI's `/usage` screen, driven in a pty with metered keys scrubbed. Guarded: any
  'auto mode' nudge is dismissed with Esc (keeps the current mode) and ~/.claude/settings.json must be byte-identical
  before/after, otherwise the probe reports SETTINGS_CHANGED and the run must stop.
* Cursor: `cursor-agent about` (subscription tier); on-demand billing is not observable from the CLI, so outputs are
  scanned for usage-based / on-demand wording and Cursor is stopped if any appears.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import pty
import re
import select
import shutil
import struct
import subprocess
import tempfile
import termios
import time
from pathlib import Path

METERED = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY", "CODEX_API_KEY", "CLAUDE_CODE_USE_BEDROCK",
           "CLAUDE_CODE_USE_VERTEX", "XAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")


def _env() -> dict[str, str]:
    e = {k: v for k, v in os.environ.items() if k not in METERED}
    e.setdefault("PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin")
    return e


def codex_limits(timeout: float = 120) -> dict:
    codex = shutil.which("codex") or "/opt/homebrew/bin/codex"
    d = tempfile.mkdtemp(prefix="wi-gen2-codex-allow-")
    t0 = time.time()
    try:
        cp = subprocess.run([codex, "exec", "--json", "--skip-git-repo-check", "--ignore-user-config", "-s", "read-only",
                             "-c", 'forced_login_method="chatgpt"', "Reply exactly: OK"], cwd=d, env=_env(),
                            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    sess = Path.home() / ".codex" / "sessions"
    best = None
    for f in sorted(sess.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]:
        if f.stat().st_mtime < t0 - 5:
            break
        rl, cwd = None, None
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("type") == "session_meta":
                cwd = (e.get("payload") or {}).get("cwd")
            p = e.get("payload") or {}
            if isinstance(p, dict) and p.get("rate_limits"):
                rl = p["rate_limits"]
        if cwd and os.path.realpath(cwd) == os.path.realpath(d) and rl:
            best = rl
            break
    shutil.rmtree(d, ignore_errors=True)
    if not best:
        return {"ok": False, "error": "rate_limits not found", "exit": cp.returncode}
    prim = best.get("primary") or {}
    sec = best.get("secondary") or {}
    return {"ok": True, "plan_type": best.get("plan_type"), "primary_used_percent": prim.get("used_percent"),
            "primary_window_minutes": prim.get("window_minutes"), "primary_resets_at_epoch": prim.get("resets_at"),
            "secondary_used_percent": sec.get("used_percent"), "secondary_window_minutes": sec.get("window_minutes"),
            "credits": best.get("credits"), "rate_limit_reached_type": best.get("rate_limit_reached_type"),
            "probe_cost": "one tiny codex exec (~16k cached-input tokens)"}


def claude_usage(cwd: str, raw_path: str | None = None) -> dict:
    sett = Path.home() / ".claude" / "settings.json"
    h0 = hashlib.sha256(sett.read_bytes()).hexdigest() if sett.exists() else None
    os.makedirs(cwd, exist_ok=True)
    env = _env()
    env["TERM"] = "xterm-256color"
    claude = shutil.which("claude", path=env.get("PATH")) or "claude"
    pid, fd = pty.fork()
    if pid == 0:
        os.chdir(cwd)
        os.execvpe(claude, [claude, "--strict-mcp-config"], env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 50, 160, 0, 0))
    buf = bytearray()

    def pump(t):
        end = time.time() + t
        while time.time() < end:
            r, _, _ = select.select([fd], [], [], 0.2)
            if r:
                try:
                    buf.extend(os.read(fd, 65536))
                except OSError:
                    return

    def clean(b) -> str:
        s = bytes(b).decode("utf-8", "replace")
        s = re.sub(r"\x1b\[[0-9;?<>=]*[ -/]*[@-~]", " ", s)
        return re.sub(r"\x1b\][^\x07]*\x07", "", s)

    def tail() -> str:
        return clean(buf)[-3000:].lower()

    try:
        pump(8)
        if "trust this folder" in tail():
            os.write(fd, b"\x1b[B"); pump(0.5); os.write(fd, b"\r"); pump(8)
        for _ in range(3):
            if "auto mode your default" in tail() or "set auto mode" in tail():
                os.write(fd, b"\x1b"); pump(2)
        mark = len(buf)
        os.write(fd, b"/usage"); pump(1.5); os.write(fd, b"\r"); pump(10)
        out = clean(buf[mark:])
        os.write(fd, b"\x1b"); pump(1); os.write(fd, b"/exit\r"); pump(2)
    finally:
        try:
            os.kill(pid, 9)
            os.waitpid(pid, 0)
        except Exception:
            pass
    out = re.sub(r"sk-[A-Za-z0-9_\-]{8,}", "[REDACTED]", out)
    if raw_path:
        Path(raw_path).write_text(out[-20000:], encoding="utf-8")
    flat = re.sub(r"\s+", " ", out)
    res = {"ok": False}
    m = re.search(r"Current session.{0,40}?(\d+)% used.{0,20}?Resets ([^C]{3,40}?\))", flat)
    if m:
        res.update({"session_used_percent": int(m.group(1)), "session_resets": m.group(2).strip()})
    m = re.search(r"Current week \(all models\).{0,40}?(\d+)% used.{0,20}?Resets ([^W]{3,40}?\))", flat)
    if m:
        res.update({"week_all_models_used_percent": int(m.group(1)), "week_resets": m.group(2).strip()})
    m = re.search(r"Current week \((Opus|Sonnet)[^)]*\).{0,40}?(\d+)% used", flat)
    if m:
        res[f"week_{m.group(1).lower()}_used_percent"] = int(m.group(2))
    res["usage_credits_off"] = "usage credits are off" in flat.lower()
    res["ok"] = "session_used_percent" in res or "week_all_models_used_percent" in res
    h1 = hashlib.sha256(sett.read_bytes()).hexdigest() if sett.exists() else None
    res["settings_unchanged"] = h0 == h1
    return res


def cursor_about() -> dict:
    b = shutil.which("cursor-agent") or "cursor-agent"
    try:
        cp = subprocess.run([b, "about"], env=_env(), capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    except Exception as e:  # pragma: no cover
        return {"ok": False, "error": str(e)}
    tier = re.search(r"Subscription Tier\s+(.+)", cp.stdout)
    model = re.search(r"Model\s+(.+)", cp.stdout)
    return {"ok": cp.returncode == 0, "subscription_tier": tier.group(1).strip() if tier else None,
            "default_model": model.group(1).strip() if model else None,
            "on_demand_visibility": "not exposed by the CLI; outputs scanned for usage-based/on-demand wording"}


ON_DEMAND = re.compile(r"(?i)usage[- ]based|on[- ]demand (usage|pricing|spend)|exceeded your (included|plan)|"
                       r"additional (usage|charges)|you('ve| have) (hit|reached) your (usage|plan) limit")


def snapshot(evidence_root: Path, label: str, workers: list[str]) -> dict:
    snap = {"label": label, "taken_at": time.strftime("%Y-%m-%d %H:%M:%S WITA")}
    adir = evidence_root / "allowance"
    adir.mkdir(parents=True, exist_ok=True)
    if "codex_sub" in workers:
        snap["codex"] = codex_limits()
    if "claude_pro_sub" in workers:
        snap["claude"] = claude_usage(str(evidence_root / "allowance" / "claude-usage-cwd"),
                                      str(adir / f"claude-usage-raw-{label}.txt"))
    if "cursor_sub" in workers:
        snap["cursor"] = cursor_about()
    return snap
