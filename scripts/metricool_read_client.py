#!/usr/bin/env python3
"""Metricool READ-ONLY client for Beta OS (:8788).

GET helpers only. Never schedule/upload/delete/publish.
Does NOT import wolf-system write/publish modules.
Credentials loaded in-process from ~/.openclaw/credentials/metricool.json —
never logged or placed in exception messages.
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

CREDS_PATH = Path.home() / ".openclaw" / "credentials" / "metricool.json"
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


class MetricoolReadError(Exception):
    """Soft-fail error with no secrets."""


def _load_creds() -> dict:
    if not CREDS_PATH.is_file():
        raise MetricoolReadError("Metricool credentials file missing")
    try:
        with open(CREDS_PATH, "r", encoding="utf-8") as f:
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
        # Do not include headers/body that might echo auth
        raise MetricoolReadError(f"Metricool HTTP {exc.code} on GET {path}") from None
    except urllib.error.URLError as exc:
        raise MetricoolReadError(f"Metricool network error on GET {path}: {type(exc.reason).__name__ if hasattr(exc, 'reason') else 'URLError'}") from None
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
    "list_profiles",
    "analytics_posts",
    "analytics_reels",
    "analytics_stories",
    "analytics_all_content",
    "window_days_range",
    "TZ_DISPLAY",
]
