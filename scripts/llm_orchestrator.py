#!/usr/bin/env python3
"""
Isolated Multi-LLM orchestrator for beta-os Content Engine (:8788 only).

Uses stdlib urllib against official REST APIs — no new pip deps.
Never imports wolf-system. Keys loaded only from beta-os/.env.
"""

from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_ENV_PATH = BETA_ROOT / ".env"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
TZ = ZoneInfo("Asia/Makassar")

# role → (provider, model)
ROLE_ROUTING: dict[str, tuple[str, str]] = {
    "hook_generation": ("openai", "gpt-4o-mini"),
    "caption_writer": ("anthropic", "claude-3-5-haiku-latest"),
    "brand_alignment": ("gemini", "gemini-1.5-flash"),
}
DEFAULT_PROVIDER = ("openai", "gpt-4o-mini")

BRAND_TEMPLATES: dict[str, str] = {
    "hook_generation": (
        "Write 3 short scroll-stopping social hooks for brand '{brand}'. "
        "Keep each under 12 words. Return plain text, one per line."
    ),
    "caption_writer": (
        "Write one engaging social caption for brand '{brand}'. "
        "Include a soft CTA. Keep under 80 words. Plain text only."
    ),
    "brand_alignment": (
        "Review this brand voice for '{brand}' and suggest 3 alignment tips "
        "for short-form video. Plain text, numbered list."
    ),
}


def load_env(path: str | Path = DEFAULT_ENV_PATH) -> dict[str, str]:
    """Load KEY=VALUE pairs from .env into a dict (and os.environ if unset)."""
    env_path = Path(path)
    loaded: dict[str, str] = {}
    if not env_path.is_file():
        return loaded
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        return loaded
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if not key:
            continue
        loaded[key] = val
        if key not in os.environ or not (os.environ.get(key) or "").strip():
            os.environ[key] = val
    return loaded


def _now_iso() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")


def ensure_llm_logs_table(db_path: Path | str = CATALOG_DB) -> None:
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_logs (
              id INTEGER PRIMARY KEY,
              created_at DATETIME,
              brand TEXT,
              role TEXT,
              provider TEXT,
              model TEXT,
              prompt TEXT,
              response TEXT,
              input_tokens INTEGER,
              output_tokens INTEGER,
              status TEXT,
              error TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def log_llm(
    *,
    brand: str,
    role: str,
    provider: str,
    model: str,
    prompt: str,
    response: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
    status: str,
    error: str | None = None,
    db_path: Path | str = CATALOG_DB,
) -> None:
    ensure_llm_logs_table(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            INSERT INTO llm_logs (
              created_at, brand, role, provider, model,
              prompt, response, input_tokens, output_tokens, status, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now_iso(),
                brand,
                role,
                provider,
                model,
                prompt,
                response,
                input_tokens,
                output_tokens,
                status,
                error,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _http_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float = 60.0,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {err_body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network error: {exc.reason}") from exc


def call_openai(prompt: str, model: str, api_key: str) -> tuple[str, int, int]:
    result = _http_json(
        "https://api.openai.com/v1/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        },
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    choices = result.get("choices") or []
    if not choices:
        raise RuntimeError("openai: empty choices")
    text = ((choices[0].get("message") or {}).get("content") or "").strip()
    usage = result.get("usage") or {}
    return text, int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)


def call_anthropic(prompt: str, model: str, api_key: str) -> tuple[str, int, int]:
    result = _http_json(
        "https://api.anthropic.com/v1/messages",
        {
            "model": model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        },
        {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    blocks = result.get("content") or []
    parts = []
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text") or "")
    text = "\n".join(parts).strip()
    usage = result.get("usage") or {}
    return text, int(usage.get("input_tokens") or 0), int(usage.get("output_tokens") or 0)


def call_gemini(prompt: str, model: str, api_key: str) -> tuple[str, int, int]:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    result = _http_json(
        url,
        {"contents": [{"parts": [{"text": prompt}]}]},
        {"Content-Type": "application/json"},
    )
    cands = result.get("candidates") or []
    text = ""
    if cands:
        content = (cands[0].get("content") or {})
        parts = content.get("parts") or []
        text = "\n".join(
            (p.get("text") or "") for p in parts if isinstance(p, dict)
        ).strip()
    meta = result.get("usageMetadata") or {}
    return (
        text,
        int(meta.get("promptTokenCount") or 0),
        int(meta.get("candidatesTokenCount") or 0),
    )


def _resolve_key(provider: str, env: dict[str, str]) -> str | None:
    def pick(*names: str) -> str | None:
        for n in names:
            v = (env.get(n) or os.environ.get(n) or "").strip()
            if v:
                return v
        return None

    if provider == "openai":
        return pick("OPENAI_API_KEY")
    if provider == "anthropic":
        return pick("ANTHROPIC_API_KEY")
    if provider == "gemini":
        return pick("GEMINI_API_KEY", "GOOGLE_API_KEY")
    return None


def _default_prompt(role: str, brand: str) -> str:
    tmpl = BRAND_TEMPLATES.get(role) or (
        "Generate a short useful social-content suggestion for brand '{brand}'."
    )
    return tmpl.format(brand=brand)


def dispatch_task(
    role: str,
    prompt: str | None,
    brand: str,
    *,
    env_path: str | Path = DEFAULT_ENV_PATH,
    db_path: Path | str = CATALOG_DB,
) -> dict[str, Any]:
    """
    Route role → provider/model, call API (or dry-run), log to sqlite.
    Always returns a structured dict; never raises to the HTTP layer.
    """
    role = (role or "").strip() or "unknown"
    brand = (brand or "").strip() or "unknown"
    env = load_env(env_path)
    provider, model = ROLE_ROUTING.get(role, DEFAULT_PROVIDER)

    user_prompt = (prompt or "").strip()
    if not user_prompt:
        user_prompt = _default_prompt(role, brand)

    # Process env wins so BETA_LLM_DRY_RUN=1 on the serve_beta process is not
    # overridden by BETA_LLM_DRY_RUN=0 sitting in .env.
    dry_raw = (os.environ.get("BETA_LLM_DRY_RUN") or "").strip()
    if not dry_raw:
        dry_raw = (env.get("BETA_LLM_DRY_RUN") or "").strip()
    dry_run = dry_raw.lower() in ("1", "true", "yes", "on")

    result: dict[str, Any] = {
        "ok": False,
        "role": role,
        "brand": brand,
        "provider": provider,
        "model": model,
        "text": None,
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "error": None,
        "dry_run": dry_run,
    }

    try:
        if dry_run:
            fake = (
                f"[DRY_RUN] role={role} brand={brand} provider={provider} model={model}\n"
                f"Echo prompt ({len(user_prompt)} chars): {user_prompt[:240]}"
            )
            result["ok"] = True
            result["text"] = fake
            result["usage"] = {"input_tokens": 0, "output_tokens": 0}
            log_llm(
                brand=brand,
                role=role,
                provider=provider,
                model=model,
                prompt=user_prompt,
                response=fake,
                input_tokens=0,
                output_tokens=0,
                status="ok",
                error=None,
                db_path=db_path,
            )
            return result

        api_key = _resolve_key(provider, env)
        if not api_key:
            key_hint = {
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "gemini": "GEMINI_API_KEY or GOOGLE_API_KEY",
            }.get(provider, "API key")
            err = f"missing API key for provider '{provider}' ({key_hint}). Paste into beta-os/.env"
            result["error"] = err
            log_llm(
                brand=brand,
                role=role,
                provider=provider,
                model=model,
                prompt=user_prompt,
                response=None,
                input_tokens=None,
                output_tokens=None,
                status="error",
                error=err,
                db_path=db_path,
            )
            return result

        if provider == "openai":
            text, inp, out = call_openai(user_prompt, model, api_key)
        elif provider == "anthropic":
            text, inp, out = call_anthropic(user_prompt, model, api_key)
        elif provider == "gemini":
            text, inp, out = call_gemini(user_prompt, model, api_key)
        else:
            raise RuntimeError(f"unknown provider: {provider}")

        result["ok"] = True
        result["text"] = text
        result["usage"] = {"input_tokens": inp, "output_tokens": out}
        log_llm(
            brand=brand,
            role=role,
            provider=provider,
            model=model,
            prompt=user_prompt,
            response=text,
            input_tokens=inp,
            output_tokens=out,
            status="ok",
            error=None,
            db_path=db_path,
        )
        return result

    except Exception as exc:  # noqa: BLE001 — never crash serve_beta
        err = str(exc)
        result["error"] = err
        try:
            log_llm(
                brand=brand,
                role=role,
                provider=provider,
                model=model,
                prompt=user_prompt,
                response=None,
                input_tokens=None,
                output_tokens=None,
                status="error",
                error=err,
                db_path=db_path,
            )
        except Exception:  # noqa: BLE001
            pass
        return result


if __name__ == "__main__":
    ensure_llm_logs_table()
    load_env()
    os.environ.setdefault("BETA_LLM_DRY_RUN", "1")
    out = dispatch_task("hook_generation", None, "habitat")
    print(json.dumps(out, indent=2))
