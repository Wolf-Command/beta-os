"""Subscription / billing-unverified API / local workers driven through their own CLIs or local APIs.

Billing is decided EXPLICITLY here, never by environment precedence:

* Each worker builds its child environment from a scrubbed copy of os.environ.
  Every variable that could silently switch the CLI to metered API billing is
  removed (e.g. ANTHROPIC_API_KEY for Claude Code, OPENAI_API_KEY/CODEX_API_KEY
  for Codex, CURSOR_API_KEY for cursor-agent).
* Before every live call a billing preflight runs with that same scrubbed env
  (claude auth status / codex login status / cursor-agent status). If the CLI
  does not report the subscription login, the call is refused (BILLING_MISMATCH)
  and no model call is made.
* These workers are outside the metered cost-cap path (they are flat-rate
  subscription, billing-unverified API key or local) but every result carries billing_class.

Never logs or returns secret values.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .base import AdapterResult, WorkerAdapter, register
from .live_gate import env_enabled, execute_requested, live_disabled, safe_excerpt

HOME = Path.home()
BETA = Path("/Users/wolfterminal/beta-os")

# Variables that would move a CLI off its subscription login onto metered API billing.
CLAUDE_METERED_ENV = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
    "ANTHROPIC_BEDROCK_BASE_URL", "ANTHROPIC_VERTEX_PROJECT_ID", "AWS_BEARER_TOKEN_BEDROCK",
)
CODEX_METERED_ENV = (
    "OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL", "OPENAI_API_BASE",
    "AZURE_OPENAI_API_KEY", "OPENAI_ORG_ID", "OPENAI_PROJECT_ID",
)
CURSOR_METERED_ENV = ("CURSOR_API_KEY", "CURSOR_API_ENDPOINT")
# Never hand any provider key to any child, whichever family it is.
ALL_PROVIDER_KEYS = CLAUDE_METERED_ENV + CODEX_METERED_ENV + CURSOR_METERED_ENV + (
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "XAI_API_KEY", "GROK_API_KEY",
)


def scrubbed_env(extra_drop: tuple[str, ...] = ()) -> dict[str, str]:
    env = dict(os.environ)
    for k in ALL_PROVIDER_KEYS + extra_drop:
        env.pop(k, None)
    # Keep live-state isolation explicit for any child that imports WI.
    env.pop("WOLF_INTELLIGENCE_LIVE_SUBMIT", None)
    return env


def _which(name: str, *fallbacks: Path) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for fb in fallbacks:
        if fb.is_file():
            return str(fb)
    return None


def safe_workspace(path: str | None, prefix: str) -> tuple[str, bool]:
    """Return (workspace, created). Refuses $HOME, its parents and the live beta tree."""
    if not path:
        return tempfile.mkdtemp(prefix=prefix), True
    p = Path(path).expanduser().resolve()
    home = HOME.resolve()
    if p == home or p in home.parents or p == Path("/") or p == BETA or BETA in p.parents:
        raise ValueError(f"refusing unscoped workspace {p}")
    p.mkdir(parents=True, exist_ok=True)
    return str(p), False


def _stage_files(workspace: str, files: list[str] | None) -> list[str]:
    staged = []
    for f in files or []:
        src = Path(f)
        dst = Path(workspace) / src.name
        shutil.copyfile(src, dst)
        staged.append(str(dst))
    return staged


def _run(argv: list[str], *, env: dict[str, str], cwd: str, timeout: float, stdin: str | None = None) -> tuple[int | None, str, str, float, str | None]:
    """Run a CLI in its own session and reap the whole process group afterwards.

    cursor-agent leaves node workers behind after --print returns (seen 2026-10-06); killing the group
    on exit/timeout prevents orphaned workers holding a deleted temp workspace.
    """
    started = time.perf_counter()
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=cwd,
                                start_new_session=True)
    except OSError as exc:
        return None, "", "", 0.0, type(exc).__name__
    err = None
    try:
        out, err_txt = proc.communicate(input=stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        err = "TIMEOUT"
        _kill_group(proc)
        out, err_txt = proc.communicate()
    finally:
        _kill_group(proc)
    rc = None if err else proc.returncode
    return rc, out or "", err_txt or "", round((time.perf_counter() - started) * 1000, 1), err


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _limit_hint(text: str) -> bool:
    t = (text or "").lower()
    return any(s in t for s in ("usage limit", "rate limit", "limit reached", "quota", "too many requests",
                                "out of credits", "upgrade your plan", "weekly limit", "5-hour limit"))


class _CliSubAdapter(WorkerAdapter):
    billing_class = "subscription"
    supports = frozenset({"health", "submit", "preflight"})

    def preflight(self) -> AdapterResult:  # pragma: no cover - overridden
        return AdapterResult(False, "UNAVAILABLE", "no preflight")

    def health(self) -> AdapterResult:
        pf = self.preflight()
        return AdapterResult(pf.ok, "CONNECTED" if pf.ok else pf.status, pf.message, pf.data)

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        if not execute_requested(job):
            return AdapterResult(False, "SHADOW_SKIPPED", "execute=True required for a live subscription call",
                                 {"provider_called": False})
        if not env_enabled():
            return live_disabled()
        pf = self.preflight()
        if not pf.ok:
            return AdapterResult(False, "BILLING_MISMATCH" if pf.status == "BILLING_MISMATCH" else pf.status,
                                 f"preflight refused live call: {pf.message}",
                                 {"provider_called": False, "billing_preflight": pf.data})
        try:
            res = self._live(job)
        except ValueError as exc:
            return AdapterResult(False, "REFUSED", str(exc), {"provider_called": False})
        res.data.setdefault("billing_class", self.billing_class)
        res.data["billing_preflight"] = pf.data
        return res

    def _live(self, job: dict[str, Any]) -> AdapterResult:  # pragma: no cover
        raise NotImplementedError


# --------------------------------------------------------------------------- Claude Pro
class ClaudeProSubAdapter(_CliSubAdapter):
    worker_id = "claude_pro_sub"
    label = "Claude Code — Claude Pro subscription (env-scrubbed)"

    def binary(self) -> str | None:
        return _which("claude", HOME / ".local" / "bin" / "claude")

    def env(self) -> dict[str, str]:
        return scrubbed_env(CLAUDE_METERED_ENV)

    def preflight(self) -> AdapterResult:
        b = self.binary()
        if not b:
            return AdapterResult(False, "UNAVAILABLE", "claude CLI not found")
        rc, out, _err, ms, err = _run([b, "auth", "status", "--json"], env=self.env(), cwd=tempfile.gettempdir(), timeout=30)
        try:
            st = json.loads(out)
        except (json.JSONDecodeError, TypeError):
            return AdapterResult(False, "UNAVAILABLE", f"claude auth status unreadable ({err or rc})")
        facts = {
            "authMethod": st.get("authMethod"),
            "apiKeySource": st.get("apiKeySource"),
            "subscriptionType": st.get("subscriptionType"),
            "email": st.get("email"),
            "apiProvider": st.get("apiProvider"),
            "env_scrubbed": [k for k in CLAUDE_METERED_ENV if k in os.environ],
            "check": "claude auth status --json (scrubbed env)",
        }
        ok = (st.get("loggedIn") is True and st.get("authMethod") == "claude.ai"
              and not st.get("apiKeySource") and st.get("subscriptionType") in {"pro", "max", "team", "enterprise"})
        if ok:
            return AdapterResult(True, "CONNECTED", f"subscription login {facts['subscriptionType']} ({facts['email']})", facts)
        return AdapterResult(False, "BILLING_MISMATCH", "claude would not use the claude.ai subscription", facts)

    def _live(self, job: dict[str, Any]) -> AdapterResult:
        b = self.binary()
        workspace, created = safe_workspace(job.get("workspace"), "wi-claude-")
        try:
            staged = _stage_files(workspace, job.get("files"))
            prompt = str(job.get("prompt") or "")
            if staged:
                prompt += "\n\nFiles available in the current directory: " + ", ".join(Path(s).name for s in staged)
            argv = [b, "-p", "--output-format", "json", "--no-session-persistence", "--strict-mcp-config",
                    "--permission-mode", "dontAsk", "--tools", "Read" if staged else ""]
            if job.get("model"):
                argv += ["--model", str(job["model"])]
            rc, out, err_txt, ms, err = _run(argv, env=self.env(), cwd=workspace,
                                             timeout=float(job.get("timeout_s") or 300), stdin=prompt)
            data: dict[str, Any] = {"latency_ms": ms, "exit_code": rc, "provider_called": True,
                                    "execution_path": "claude -p (ANTHROPIC_API_KEY & co removed from child env)",
                                    "workspace_scoped": True}
            try:
                j = json.loads(out)
            except (json.JSONDecodeError, TypeError):
                j = {}
            text = str(j.get("result") or "") if j else ""
            models = sorted((j.get("modelUsage") or {}).keys()) if j else []
            data.update({
                "output": text,
                "model_observed": ",".join(models) or "UNKNOWN",
                "notional_cost_usd_reported_by_cli": j.get("total_cost_usd"),
                "usage": j.get("usage"),
                "num_turns": j.get("num_turns"),
            })
            ok = rc == 0 and bool(text) and not j.get("is_error")
            if not ok:
                blob = text + out[-400:] + err_txt[-400:]
                data["limit_hit"] = _limit_hint(blob)
                data["error_excerpt"] = safe_excerpt(blob)
                return AdapterResult(False, "LIMIT" if data["limit_hit"] else ("TIMEOUT" if err == "TIMEOUT" else "ERROR"),
                                     err or "claude -p failed", data)
            return AdapterResult(True, "LIVE_OK", "claude -p subscription", data)
        finally:
            if created:
                shutil.rmtree(workspace, ignore_errors=True)


# --------------------------------------------------------------------------- Codex (ChatGPT)
class CodexSubAdapter(_CliSubAdapter):
    worker_id = "codex_sub"
    label = "OpenAI Codex CLI — ChatGPT/Codex subscription (OPENAI_API_KEY scrubbed, forced chatgpt login)"

    def binary(self) -> str | None:
        return _which("codex", Path("/opt/homebrew/bin/codex"))

    def env(self) -> dict[str, str]:
        return scrubbed_env(CODEX_METERED_ENV)

    def preflight(self) -> AdapterResult:
        b = self.binary()
        if not b:
            return AdapterResult(False, "UNAVAILABLE", "codex CLI not found")
        rc, out, err_txt, ms, err = _run([b, "login", "status"], env=self.env(), cwd=tempfile.gettempdir(), timeout=30)
        status_line = (out + err_txt).strip().splitlines()[-1:] or [""]
        auth_mode = None
        api_key_field_set = None
        try:
            a = json.loads((HOME / ".codex" / "auth.json").read_text(encoding="utf-8"))
            auth_mode = a.get("auth_mode")
            api_key_field_set = bool(a.get("OPENAI_API_KEY"))
        except (OSError, json.JSONDecodeError):
            pass
        facts = {"login_status": status_line[0][:120], "auth_json_auth_mode": auth_mode,
                 "auth_json_api_key_field_set": api_key_field_set,
                 "env_scrubbed": [k for k in CODEX_METERED_ENV if k in os.environ],
                 "forced_login_method": "chatgpt",
                 "check": "codex login status (scrubbed env) + auth.json auth_mode (names only)"}
        ok = "chatgpt" in status_line[0].lower() and auth_mode == "chatgpt" and not api_key_field_set
        if ok:
            return AdapterResult(True, "CONNECTED", "ChatGPT/Codex subscription login", facts)
        return AdapterResult(False, "BILLING_MISMATCH", "codex is not on the ChatGPT login", facts)

    def _live(self, job: dict[str, Any]) -> AdapterResult:
        b = self.binary()
        workspace, created = safe_workspace(job.get("workspace"), "wi-codex-")
        try:
            staged = _stage_files(workspace, job.get("files"))
            last = Path(workspace) / ".wi-last-message.txt"
            argv = [b, "exec", "--json", "--ephemeral", "--skip-git-repo-check", "--ignore-user-config",
                    "-s", "read-only", "-C", workspace, "--color", "never",
                    "-c", 'forced_login_method="chatgpt"', "-o", str(last)]
            for s in staged:
                if s.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    argv += ["-i", s]
            if job.get("model"):
                argv += ["-m", str(job["model"])]
            argv.append("-")
            rc, out, err_txt, ms, err = _run(argv, env=self.env(), cwd=workspace,
                                             timeout=float(job.get("timeout_s") or 300), stdin=str(job.get("prompt") or ""))
            text = last.read_text(encoding="utf-8") if last.exists() else ""
            usage = None
            model = None
            for line in out.splitlines():
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if ev.get("type") == "turn.completed":
                    usage = ev.get("usage")
                if isinstance(ev.get("model"), str):
                    model = ev["model"]
                if ev.get("type") in {"turn.failed", "error"}:
                    text = text or ""
            data = {"latency_ms": ms, "exit_code": rc, "provider_called": True, "output": text,
                    "usage": usage, "model_observed": model or "account default (not reported by codex exec)",
                    "execution_path": "codex exec --ignore-user-config -s read-only (OPENAI/CODEX keys removed, forced_login_method=chatgpt)",
                    "workspace_scoped": True}
            ok = rc == 0 and bool(text.strip())
            if not ok:
                blob = out[-600:] + err_txt[-600:]
                data["limit_hit"] = _limit_hint(blob)
                data["error_excerpt"] = safe_excerpt(blob)
                return AdapterResult(False, "LIMIT" if data["limit_hit"] else ("TIMEOUT" if err == "TIMEOUT" else "ERROR"),
                                     err or "codex exec failed", data)
            return AdapterResult(True, "LIVE_OK", "codex exec ChatGPT subscription", data)
        finally:
            if created:
                shutil.rmtree(workspace, ignore_errors=True)


# --------------------------------------------------------------------------- Cursor
class CursorSubAdapter(_CliSubAdapter):
    worker_id = "cursor_sub"
    label = "cursor-agent — Cursor subscription (scoped --workspace, CURSOR_API_KEY scrubbed)"

    def binary(self) -> str | None:
        return _which("cursor-agent", HOME / ".local" / "bin" / "cursor-agent")

    def env(self) -> dict[str, str]:
        return scrubbed_env(CURSOR_METERED_ENV)

    def preflight(self) -> AdapterResult:
        b = self.binary()
        if not b:
            return AdapterResult(False, "UNAVAILABLE", "cursor-agent not found")
        rc, out, err_txt, ms, err = _run([b, "status"], env=self.env(), cwd=tempfile.gettempdir(), timeout=45)
        line = next((l.strip() for l in (out + err_txt).splitlines() if "logged in" in l.lower()), "")
        facts = {"status_line": line[:120].replace("✓", "").strip(),
                 "env_scrubbed": [k for k in CURSOR_METERED_ENV if k in os.environ],
                 "check": "cursor-agent status (scrubbed env)"}
        if line and "not logged" not in line.lower():
            return AdapterResult(True, "CONNECTED", facts["status_line"], facts)
        return AdapterResult(False, "BILLING_MISMATCH", "cursor-agent not logged in to the subscription", facts)

    def _live(self, job: dict[str, Any]) -> AdapterResult:
        b = self.binary()
        workspace, created = safe_workspace(job.get("workspace"), "wi-cursor-")
        try:
            staged = _stage_files(workspace, job.get("files"))
            prompt = str(job.get("prompt") or "")
            if staged:
                prompt += "\n\nFiles available in the workspace: " + ", ".join(Path(s).name for s in staged)
            model = str(job.get("model") or "composer-2.5")
            argv = [b, "--print", "--output-format", "json", "--mode", "ask", "--trust",
                    "--workspace", workspace, "--model", model, prompt]
            rc, out, err_txt, ms, err = _run(argv, env=self.env(), cwd=workspace, timeout=float(job.get("timeout_s") or 300))
            text = ""
            j: dict[str, Any] = {}
            try:
                j = json.loads(out.strip().splitlines()[-1]) if out.strip() else {}
                text = str(j.get("result") or "")
            except (json.JSONDecodeError, IndexError):
                text = out
            data = {"latency_ms": ms, "exit_code": rc, "provider_called": True, "output": text,
                    "model_observed": model + " (requested; cli-config selectedModel)",
                    "usage": j.get("usage") if isinstance(j, dict) else None,
                    "execution_path": f"cursor-agent --print --mode ask --trust --workspace <scoped tmp>",
                    "workspace": workspace, "workspace_scoped": True}
            ok = rc == 0 and bool(text.strip()) and not j.get("is_error")
            if not ok:
                blob = out[-600:] + err_txt[-600:]
                data["limit_hit"] = _limit_hint(blob)
                data["error_excerpt"] = safe_excerpt(blob)
                return AdapterResult(False, "LIMIT" if data["limit_hit"] else ("TIMEOUT" if err == "TIMEOUT" else "ERROR"),
                                     err or "cursor-agent failed", data)
            return AdapterResult(True, "LIVE_OK", "cursor-agent subscription", data)
        finally:
            if created:
                shutil.rmtree(workspace, ignore_errors=True)


# --------------------------------------------------------------------------- Gemini (billing unverified)
GEMINI_CRED_FILE_ENV = "WOLF_INTELLIGENCE_GEMINI_CRED_FILE"
DEFAULT_GEMINI_CRED = HOME / ".openclaw" / "credentials" / "google-gemini.json"
GEMINI_FLASH_ALLOWLIST = ("gemini-flash-latest", "gemini-flash-lite-latest")


def _gemini_key() -> tuple[str, str]:
    """Return (key, source_label). Never returned to callers outside this module's request."""
    if os.environ.get("GEMINI_API_KEY", "").strip():
        return os.environ["GEMINI_API_KEY"].strip(), "env:GEMINI_API_KEY"
    path = Path(os.environ.get(GEMINI_CRED_FILE_ENV) or DEFAULT_GEMINI_CRED)
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        k = str(d.get("api_key") or "").strip()
        if k:
            return k, f"file:{path}"
    except (OSError, json.JSONDecodeError):
        pass
    return "", "none"


class GeminiApiAdapter(_CliSubAdapter):
    worker_id = "gemini_api"
    label = "Gemini API — billing unverified (flash allowlist only)"
    billing_class = "billing_unverified"

    def preflight(self) -> AdapterResult:
        key, src = _gemini_key()
        facts = {"key_source": src, "key_present": bool(key), "allowed_models": list(GEMINI_FLASH_ALLOWLIST),
                 "billing_note": "Billing UNVERIFIED. Project billing status is not observable from the key; "
                                 "only flash models are allowed; per-response serviceTier is recorded."}
        if not key:
            return AdapterResult(False, "UNAVAILABLE", "no Gemini key configured", facts)
        return AdapterResult(True, "CONNECTED", "Gemini key present (billing unverified, flash allowlist only)", facts)

    def _live(self, job: dict[str, Any]) -> AdapterResult:
        key, _src = _gemini_key()
        model = str(job.get("model") or GEMINI_FLASH_ALLOWLIST[0])
        if model not in GEMINI_FLASH_ALLOWLIST:
            raise ValueError(f"model {model} not on the Gemini flash allowlist")
        parts: list[dict[str, Any]] = [{"text": str(job.get("prompt") or "")}]
        for f in job.get("files") or []:
            ext = Path(f).suffix.lower()
            mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(ext)
            if mime:
                parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(Path(f).read_bytes()).decode()}})
        payload = {"contents": [{"parts": parts}],
                   "generationConfig": {"maxOutputTokens": int(job.get("max_output_tokens") or 8192), "temperature": 0}}
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            data=json.dumps(payload).encode(), method="POST",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"})
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=float(job.get("timeout_s") or 180)) as resp:
                body = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
            ms = round((time.perf_counter() - started) * 1000, 1)
            txt = safe_excerpt(exc.read().decode("utf-8", errors="replace"), [key])
            return AdapterResult(False, "LIMIT" if exc.code == 429 else "ERROR", f"HTTP {exc.code}",
                                 {"latency_ms": ms, "provider_called": True, "error_excerpt": txt,
                                  "limit_hit": exc.code == 429})
        except Exception as exc:  # noqa: BLE001
            ms = round((time.perf_counter() - started) * 1000, 1)
            return AdapterResult(False, "ERROR", type(exc).__name__, {"latency_ms": ms, "provider_called": True})
        ms = round((time.perf_counter() - started) * 1000, 1)
        try:
            text = "".join(p.get("text", "") for p in body["candidates"][0]["content"]["parts"] if not p.get("thought"))
        except (KeyError, IndexError, TypeError):
            text = ""
        um = body.get("usageMetadata") or {}
        data = {"latency_ms": ms, "provider_called": True, "output": text,
                "model_observed": body.get("modelVersion") or model,
                "usage": {k: um.get(k) for k in ("promptTokenCount", "candidatesTokenCount", "thoughtsTokenCount", "totalTokenCount", "serviceTier")},
                "execution_path": "generativelanguage v1beta generateContent (flash allowlist)"}
        if not text:
            data["error_excerpt"] = safe_excerpt(json.dumps(body)[:600], [key])
            return AdapterResult(False, "ERROR", "empty Gemini response", data)
        return AdapterResult(True, "LIVE_OK", "gemini flash allowlist (billing unverified)", data)


# --------------------------------------------------------------------------- Ollama local
class OllamaLocalAdapter(_CliSubAdapter):
    worker_id = "ollama_local"
    label = "Ollama local :11434"
    billing_class = "local"

    def preflight(self) -> AdapterResult:
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as resp:
                models = [m.get("name") for m in json.loads(resp.read().decode()).get("models") or []]
        except Exception as exc:  # noqa: BLE001
            return AdapterResult(False, "UNAVAILABLE", f"ollama unreachable: {type(exc).__name__}")
        gen = [m for m in models if "embed" not in (m or "")]
        return AdapterResult(bool(gen), "CONNECTED" if gen else "UNAVAILABLE", f"models={models}",
                             {"models": models, "generative_models": gen})

    def _live(self, job: dict[str, Any]) -> AdapterResult:
        if job.get("files"):
            return AdapterResult(False, "UNSUPPORTED", "no vision model installed (llama3.2:3b is text-only)",
                                 {"provider_called": False})
        model = str(job.get("model") or "llama3.2:3b")
        payload = {"model": model, "prompt": str(job.get("prompt") or ""), "stream": False,
                   "options": {"num_predict": int(job.get("max_output_tokens") or 2048), "temperature": 0,
                               "num_ctx": int(job.get("num_ctx") or 16384)}}
        req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=float(job.get("timeout_s") or 600)) as resp:
                body = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception as exc:  # noqa: BLE001
            return AdapterResult(False, "ERROR", type(exc).__name__,
                                 {"latency_ms": round((time.perf_counter() - started) * 1000, 1), "provider_called": True})
        ms = round((time.perf_counter() - started) * 1000, 1)
        text = str(body.get("response") or "")
        data = {"latency_ms": ms, "provider_called": True, "output": text, "model_observed": body.get("model") or model,
                "usage": {"prompt_eval_count": body.get("prompt_eval_count"), "eval_count": body.get("eval_count")},
                "execution_path": "ollama /api/generate 127.0.0.1:11434"}
        return AdapterResult(bool(text), "LIVE_OK" if text else "ERROR", "ollama local", data)


register(ClaudeProSubAdapter())
register(CodexSubAdapter())
register(CursorSubAdapter())
register(GeminiApiAdapter())
register(OllamaLocalAdapter())
