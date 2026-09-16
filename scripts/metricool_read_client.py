#!/usr/bin/env python3
"""Metricool client for Beta OS (:8788) — FAIL CLOSED by default.

Default: BETA_METRICOOL_ENABLED=false → no auth, no network, no prod credential load.
Writes: BETA_METRICOOL_WRITE_ENABLED=false → any write/publish path fails visibly.

Credentials (only when ENABLED=true) must come from an explicit Beta-local path
via BETA_METRICOOL_CREDS_PATH under /Users/wolfterminal/beta-os/.
NEVER falls back to shared OpenClaw credential stores or wolf-system paths.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_ENV_PATH = BETA_ROOT / ".env"
DEFAULT_BASE = "https://app.metricool.com/api"
TZ_DISPLAY = ZoneInfo("Asia/Makassar")

# Forbidden write symbols — kept for tests / guardrails
_FORBIDDEN_NAMES = frozenset({
    "schedule_post",
    "upload_media",
    "delete_post",
    "publish_post",
    "delete",
    "post",
    "_post",
})

# Hard-ban substrings for credential paths (production / shared)
_BANNED_CRED_SUBSTR = (
    "/.openclaw/",
    "openclaw/credentials",
    "/wolf-system/",
    "wolf-system/credentials",
)


class MetricoolReadError(Exception):
    """Soft-fail / policy error with no secrets."""


class MetricoolWriteBlocked(Exception):
    """Deterministic block for Metricool write/publish in Beta."""


def _truthy(raw: str | None) -> bool:
    return (raw or "").strip().lower() in {"1", "true", "yes", "on"}


def _load_beta_env() -> None:
    """Load beta-os/.env into os.environ for unset keys only (no overwrite)."""
    path = DEFAULT_ENV_PATH
    if not path.is_file():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and (k not in os.environ or not (os.environ.get(k) or "").strip()):
                os.environ[k] = v
    except OSError:
        return


def metricool_enabled() -> bool:
    _load_beta_env()
    return _truthy(os.environ.get("BETA_METRICOOL_ENABLED"))


def metricool_write_enabled() -> bool:
    _load_beta_env()
    return _truthy(os.environ.get("BETA_METRICOOL_WRITE_ENABLED"))


def metricool_status() -> dict[str, Any]:
    """UI/service status — never opens credential files."""
    enabled = metricool_enabled()
    write_ok = metricool_write_enabled()
    if not enabled:
        return {
            "connected": False,
            "status": "DISABLED IN BETA",
            "enabled": False,
            "write_enabled": False,
            "note": "BETA_METRICOOL_ENABLED=false — no auth, no network, no production credential load",
        }
    path_raw = (os.environ.get("BETA_METRICOOL_CREDS_PATH") or "").strip()
    return {
        "connected": False,  # connected only after successful load; status API does not load
        "status": "NOT CONNECTED" if not path_raw else "CONFIGURED PATH SET (not verified here)",
        "enabled": True,
        "write_enabled": write_ok,
        "creds_path_configured": bool(path_raw),
        "note": "Enabled — credentials must be Beta-local via BETA_METRICOOL_CREDS_PATH",
    }


def assert_metricool_write_allowed(operation: str = "write") -> None:
    """Fail closed for any Metricool write/publish operation."""
    if not metricool_write_enabled():
        raise MetricoolWriteBlocked(
            f"Metricool {operation} blocked: BETA_METRICOOL_WRITE_ENABLED=false"
        )
    if not metricool_enabled():
        raise MetricoolWriteBlocked(
            f"Metricool {operation} blocked: BETA_METRICOOL_ENABLED=false"
        )


def _resolve_beta_creds_path() -> Path:
    """Explicit Beta-only creds path. No production fallback."""
    raw = (os.environ.get("BETA_METRICOOL_CREDS_PATH") or "").strip()
    if not raw:
        raise MetricoolReadError(
            "Metricool enabled but BETA_METRICOOL_CREDS_PATH unset — fail closed (no production fallback)"
        )
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (BETA_ROOT / path).resolve()
    else:
        path = path.resolve()
    resolved = str(path)
    for ban in _BANNED_CRED_SUBSTR:
        if ban in resolved:
            raise MetricoolReadError(
                "Metricool credential path refused — production/shared path not allowed"
            )
    try:
        path.relative_to(BETA_ROOT)
    except ValueError as exc:
        raise MetricoolReadError(
            "Metricool credential path must be under /Users/wolfterminal/beta-os/"
        ) from exc
    return path


def _load_creds() -> dict:
    if not metricool_enabled():
        raise MetricoolReadError(
            "Metricool DISABLED IN BETA (BETA_METRICOOL_ENABLED=false) — no credential load"
        )
    creds_path = _resolve_beta_creds_path()
    if not creds_path.is_file():
        raise MetricoolReadError("Metricool credentials file missing (Beta path)")
    try:
        with open(creds_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: BLE001
        raise MetricoolReadError(f"Metricool credentials unreadable: {type(exc).__name__}") from None
    if not isinstance(data, dict) or not data.get("user_token") or not data.get("user_id"):
        raise MetricoolReadError("Metricool credentials incomplete")
    return data


def _headers(creds: dict) -> dict:
    return {
        "X-Mc-Auth": creds["user_token"],
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _base(creds: dict) -> str:
    return (creds.get("base_url") or DEFAULT_BASE).rstrip("/")


def _uid(creds: dict) -> str:
    return str(creds["user_id"])


def _iso_range(start: Any, end: Any) -> tuple[str, str]:
    def fmt(s: Any, is_end: bool) -> str:
        s = str(s)
        if "T" in s:
            return s
        digits = s.replace("-", "")
        y, m, d = digits[:4], digits[4:6], digits[6:8]
        return f"{y}-{m}-{d}T{'23:59:59' if is_end else '00:00:00'}"
    return fmt(start, False), fmt(end, True)


def _http_get(path: str, params: dict | None = None, *, timeout: int = 45) -> Any:
    """GET only. Soft-fails with MetricoolReadError (no token in message)."""
    if not metricool_enabled():
        raise MetricoolReadError("Metricool DISABLED IN BETA — no network")
    creds = _load_creds()
    params = dict(params or {})
    params.setdefault("userId", _uid(creds))
    qs = urllib.parse.urlencode(params)
    url = f"{_base(creds)}{path}?{qs}"
    req = urllib.request.Request(url, headers=_headers(creds), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise MetricoolReadError(f"Metricool HTTP {exc.code} on GET {path}") from None
    except urllib.error.URLError as exc:
        raise MetricoolReadError(
            f"Metricool network error on GET {path}: {type(exc.reason).__name__ if hasattr(exc, 'reason') else 'URLError'}"
        ) from None
    except json.JSONDecodeError:
        raise MetricoolReadError(f"Metricool invalid JSON on GET {path}") from None
    except MetricoolReadError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise MetricoolReadError(f"Metricool GET failed ({type(exc).__name__})") from None


def list_profiles() -> list:
    """GET /admin/simpleProfiles — brand workspaces."""
    body = _http_get("/admin/simpleProfiles")
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        for k in ("data", "profiles", "brands"):
            if isinstance(body.get(k), list):
                return body[k]
    return []


def analytics_posts(blog_id: int | str, network: str, start: Any, end: Any) -> Any:
    frm, to = _iso_range(start, end)
    return _http_get(
        f"/v2/analytics/posts/{network}",
        {"blogId": str(blog_id), "from": frm, "to": to},
    )


def analytics_reels(blog_id: int | str, network: str, start: Any, end: Any) -> Any:
    frm, to = _iso_range(start, end)
    return _http_get(
        f"/v2/analytics/reels/{network}",
        {"blogId": str(blog_id), "from": frm, "to": to},
    )


def analytics_stories(blog_id: int | str, network: str, start: Any, end: Any) -> Any:
    frm, to = _iso_range(start, end)
    return _http_get(
        f"/v2/analytics/stories/{network}",
        {"blogId": str(blog_id), "from": frm, "to": to},
    )


def analytics_all_content(
    blog_id: int | str,
    network: str = "instagram",
    start: Any = None,
    end: Any = None,
) -> dict:
    """Fetch posts + reels + stories independently. Missing surface → error key, not zeros."""
    if start is None or end is None:
        end_dt = datetime.now(timezone.utc).date()
        start_dt = end_dt - timedelta(days=60)
        start = start or start_dt.isoformat()
        end = end or end_dt.isoformat()
    out: dict[str, Any] = {"posts": [], "reels": [], "stories": [], "_errors": {}}
    for key, fn in (
        ("posts", lambda: analytics_posts(blog_id, network, start, end)),
        ("reels", lambda: analytics_reels(blog_id, network, start, end)),
        ("stories", lambda: analytics_stories(blog_id, network, start, end)),
    ):
        try:
            body = fn()
            out[key] = _rows_of(body)
        except MetricoolReadError as exc:
            out["_errors"][key] = str(exc)
            out[key] = []
    return out


def _rows_of(body: Any) -> list:
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        for k in ("data", "posts", "results"):
            v = body.get(k)
            if isinstance(v, list):
                return v
    return []


def window_days_range(window_days: int = 60) -> tuple[str, str]:
    end_dt = datetime.now(timezone.utc).date()
    start_dt = end_dt - timedelta(days=max(1, int(window_days)))
    return start_dt.isoformat(), end_dt.isoformat()


# Explicit public API (tests assert write names absent)
__all__ = [
    "MetricoolReadError",
    "MetricoolWriteBlocked",
    "metricool_enabled",
    "metricool_write_enabled",
    "metricool_status",
    "assert_metricool_write_allowed",
    "list_profiles",
    "analytics_posts",
    "analytics_reels",
    "analytics_stories",
    "analytics_all_content",
    "window_days_range",
    "TZ_DISPLAY",
]
