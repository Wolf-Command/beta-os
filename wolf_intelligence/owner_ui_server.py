"""Simple Owner Beta UI server — phone-size board. No jargon in primary UI.

Listens on 127.0.0.1:8799 only. Does not touch Production :8787.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import work_items
from .paths import OWNER_UI_HOST, OWNER_UI_PORT, UI_DIR, WORKER_STATUS_PATH, ensure_dirs


HTML = UI_DIR / "owner.html"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # quieter
        pass

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        ensure_dirs()
        path = urlparse(self.path).path
        if path in ("/", "/owner", "/wolf-intelligence"):
            body = HTML.read_bytes()
            self._send(200, body, "text/html; charset=utf-8")
            return
        if path == "/api/owner-board":
            buckets = work_items.by_ui_bucket()
            tech = {
                "mode": "SHADOW",
                "production_touched": False,
                "workers": None,
            }
            if WORKER_STATUS_PATH.exists():
                try:
                    tech["workers"] = json.loads(WORKER_STATUS_PATH.read_text()).get("summary")
                except json.JSONDecodeError:
                    pass
            # Strip jargon from primary cards — keep raw under _tech
            slim = {}
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
            body = json.dumps(slim).encode()
            self._send(200, body, "application/json")
            return
        if path == "/api/health":
            self._send(200, b'{"ok":true,"service":"wolf-intelligence-owner-ui","port":8799}', "application/json")
            return
        self._send(404, b"not found", "text/plain")


def main() -> int:
    ensure_dirs()
    server = ThreadingHTTPServer((OWNER_UI_HOST, OWNER_UI_PORT), Handler)
    print(f"OWNER_UI http://{OWNER_UI_HOST}:{OWNER_UI_PORT}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
