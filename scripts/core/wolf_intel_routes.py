"""Wolf Intelligence Beta routes — read-only Owner board. No Daily Close / Petty coupling."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
if str(BETA_ROOT) not in sys.path:
    sys.path.insert(0, str(BETA_ROOT))

UI_HTML = BETA_ROOT / "wolf_intelligence" / "ui" / "owner.html"
# Also mirror under dashboards for generic static fallthrough
DASH_HTML = BETA_ROOT / "dashboards" / "wolf-intelligence.html"


def ensure_dashboard_mirror() -> None:
    if UI_HTML.exists():
        # Fetch board via relative Beta API when embedded on :8788
        html = UI_HTML.read_text(encoding="utf-8")
        # Point fetch to Beta API path when served from beta
        html = html.replace("fetch('/api/owner-board')", "fetch('/api/wolf-intelligence/board')")
        DASH_HTML.write_text(html, encoding="utf-8")


def board_payload() -> dict[str, Any]:
    from wolf_intelligence import work_items
    from wolf_intelligence.paths import WORKER_STATUS_PATH

    buckets = work_items.by_ui_bucket()
    tech = {
        "mode": "SHADOW",
        "production_touched": False,
        "store": work_items.store_info(),
        "sidecar_ui": "http://127.0.0.1:8799/",
    }
    if WORKER_STATUS_PATH.exists():
        try:
            tech["workers"] = json.loads(WORKER_STATUS_PATH.read_text()).get("summary")
        except json.JSONDecodeError:
            pass
    try:
        from wolf_intelligence import stats_store as _stats_store
        tech["stats"] = _stats_store.recompute()
    except Exception:
        pass
    slim: dict[str, Any] = {}
    for k, items in buckets.items():
        slim[k] = [
            {
                "id": it.get("id"),
                "title": it.get("title"),
                "state": it.get("state"),
                "recommendation": {
                    "recommended_worker": ((it.get("recommendation") or {}).get("recommended_worker"))
                },
            }
            for it in items
        ]
    slim["_tech"] = tech
    return slim


def handle_get(handler, path: str) -> bool:
    """Return True if handled. Safe no-op for unrelated paths."""
    if path in (
        "/owner/intelligence",
        "/owner/intelligence/",
        "/wolf-intelligence",
        "/wolf-intelligence/",
        "/wolf-intelligence.html",
    ):
        ensure_dashboard_mirror()
        page = DASH_HTML if DASH_HTML.is_file() else UI_HTML
        if not page.is_file():
            handler._send_json({"ok": False, "error": "ui_missing"}, status=404)
            return True
        # Prefer shell inject when available
        try:
            handler._send_html_shell(page.read_bytes(), rel="wolf-intelligence.html")
        except Exception:
            raw = page.read_bytes()
            handler.send_response(200)
            handler.send_header("Content-Type", "text/html; charset=utf-8")
            handler.send_header("Content-Length", str(len(raw)))
            handler.send_header("Cache-Control", "no-store")
            handler.end_headers()
            handler.wfile.write(raw)
        return True
    if path in ("/api/wolf-intelligence/board", "/api/wolf-intelligence/board/"):
        try:
            handler._send_json(board_payload())
        except Exception as e:
            handler._send_json({"ok": False, "error": "board_fail", "detail": type(e).__name__}, status=500)
        return True
    if path in ("/api/wolf-intelligence/health", "/api/wolf-intelligence/health/"):
        handler._send_json(
            {
                "ok": True,
                "service": "wolf-intelligence-beta",
                "sidecar": "http://127.0.0.1:8799/",
                "beta_path": "/owner/intelligence",
            }
        )
        return True
    return False
