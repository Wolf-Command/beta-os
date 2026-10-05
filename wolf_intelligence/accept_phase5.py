"""Phase 5 accept: Owner UI loads phone-size board; jargon not in primary labels."""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from pathlib import Path

from .owner_ui_server import Handler
from .paths import OWNER_UI_HOST, OWNER_UI_PORT, UI_DIR, ensure_dirs
from http.server import ThreadingHTTPServer


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
    # no provider jargon in primary visible titles (allow in optional tech)
    primary = html.split("Technical details")[0]
    jargon = ["Anthropic", "OpenAI", "Ollama", "bf_cursor", "dispatcher", "JSONL"]
    checks.append({"name": "no_jargon_primary", "ok": not any(j.lower() in primary.lower() for j in jargon)})
    checks.append({"name": "phone_viewport", "ok": "viewport" in html and "390" not in html or "device-width" in html})

    # spin server briefly
    server = ThreadingHTTPServer((OWNER_UI_HOST, OWNER_UI_PORT), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.3)
    try:
        with urllib.request.urlopen(f"http://{OWNER_UI_HOST}:{OWNER_UI_PORT}/api/health", timeout=2) as resp:
            health = json.loads(resp.read().decode())
        checks.append({"name": "health_ok", "ok": health.get("ok") is True})
        with urllib.request.urlopen(f"http://{OWNER_UI_HOST}:{OWNER_UI_PORT}/api/owner-board", timeout=2) as resp:
            board = json.loads(resp.read().decode())
        checks.append({"name": "board_keys", "ok": all(k in board for k in ("NEEDS_YOU", "READY_TO_TEST", "DECISIONS", "EXCEPTIONS", "RUNNING"))})
        with urllib.request.urlopen(f"http://{OWNER_UI_HOST}:{OWNER_UI_PORT}/", timeout=2) as resp:
            page = resp.read().decode()
        checks.append({"name": "page_served", "ok": "Wolf Intelligence" in page})
    except Exception as e:
        checks.append({"name": "server_probe", "ok": False, "detail": type(e).__name__})
    finally:
        server.shutdown()

    passed = all(c["ok"] for c in checks)
    out = {
        "phase": 5,
        "passed": passed,
        "checks": checks,
        "owner_ui_link": f"http://{OWNER_UI_HOST}:{OWNER_UI_PORT}/",
    }
    Path("/Users/wolfterminal/beta-os/state/wolf-intelligence/audit/phase5-accept.json").write_text(
        json.dumps(out, indent=2) + "\n"
    )
    return out
