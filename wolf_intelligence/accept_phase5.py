"""Phase 5 accept: Owner UI loads phone-size board; jargon not in primary labels."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from .paths import OWNER_UI_HOST, OWNER_UI_PORT, UI_DIR, ensure_dirs


def accept() -> dict:
    ensure_dirs()
    html = (UI_DIR / "owner.html").read_text(encoding="utf-8")
    checks = []
    checks.append({"name": "html_exists", "ok": bool(html)})
    checks.append({"name": "has_needs_you", "ok": "Needs you" in html})
    checks.append({"name": "has_ready", "ok": "Ready to test" in html})
    checks.append({"name": "has_decisions", "ok": "Decisions" in html})
    checks.append({"name": "has_exceptions", "ok": "Exceptions" in html})
    checks.append({"name": "has_running", "ok": "Running" in html})
    checks.append({"name": "tech_optional", "ok": "Technical details" in html})
    primary = html.split("Technical details")[0]
    jargon = ["Anthropic", "OpenAI", "Ollama", "bf_cursor", "dispatcher", "JSONL"]
    checks.append({"name": "no_jargon_primary", "ok": not any(j.lower() in primary.lower() for j in jargon)})
    checks.append({"name": "phone_viewport", "ok": "device-width" in html})

    base = f"http://{OWNER_UI_HOST}:{OWNER_UI_PORT}"
    try:
        with urllib.request.urlopen(f"{base}/api/health", timeout=2) as resp:
            health = json.loads(resp.read().decode())
        checks.append({"name": "health_ok", "ok": health.get("ok") is True, "detail": f"pid={health.get('pid')}"})
        from .owner_ui_server import ui_token
        token = ui_token()
        board_req = urllib.request.Request(
            f"{base}/api/owner-board",
            headers={"Authorization": "Bearer " + token} if token else {},
        )
        with urllib.request.urlopen(board_req, timeout=2) as resp:
            board = json.loads(resp.read().decode())
        checks.append(
            {
                "name": "board_keys",
                "ok": all(k in board for k in ("NEEDS_YOU", "READY_TO_TEST", "DECISIONS", "EXCEPTIONS", "RUNNING")),
            }
        )
        checks.append({"name": "store_sqlite", "ok": (board.get("_tech") or {}).get("store", {}).get("canonical") == "sqlite"})
        with urllib.request.urlopen(f"{base}/", timeout=2) as resp:
            page = resp.read().decode()
        checks.append({"name": "page_served", "ok": "Wolf Intelligence" in page})
        checks.append({"name": "launchagent_or_live", "ok": True, "detail": "probed live :8799"})
    except Exception as e:
        checks.append({"name": "server_probe", "ok": False, "detail": type(e).__name__})

    passed = all(c["ok"] for c in checks)
    out = {
        "phase": 5,
        "passed": passed,
        "checks": checks,
        "owner_ui_link": f"{base}/",
        "how_to": "Open http://127.0.0.1:8799/ on Studio; LaunchAgent com.wolfcommand.wolf-intelligence-owner-ui KeepAlive",
    }
    Path("/Users/wolfterminal/beta-os/state/wolf-intelligence/audit/phase5-accept.json").write_text(
        json.dumps(out, indent=2) + "\n"
    )
    return out
