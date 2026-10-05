"""Simple Owner Beta UI server — phone-size board. No jargon in primary UI.

Listens on 127.0.0.1:8799 only. Does not touch Production :8787.
Durable via LaunchAgent com.wolfcommand.wolf-intelligence-owner-ui.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import work_items
from . import stats_store
from .paths import OWNER_UI_HOST, OWNER_UI_PORT, UI_DIR, WORKER_STATUS_PATH, ensure_dirs, AUDIT_DIR

HTML = UI_DIR / "owner.html"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        try:
            ensure_dirs()
            line = "%s - %s\n" % (self.log_date_time_string(), fmt % args)
            with (AUDIT_DIR / "owner-ui-access.log").open("a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        ensure_dirs()
        path = urlparse(self.path).path
        if path in ("/", "/owner", "/wolf-intelligence", "/owner/intelligence"):
            body = HTML.read_bytes()
            self._send(200, body, "text/html; charset=utf-8")
            return
        if path in ("/api/owner-board", "/api/wolf-intelligence/board"):
            buckets = work_items.by_ui_bucket()
            tech = {"mode": "SHADOW", "production_touched": False, "workers": None, "store": work_items.store_info(), "stats": stats_store.recompute()}
            if WORKER_STATUS_PATH.exists():
                try:
                    tech["workers"] = json.loads(WORKER_STATUS_PATH.read_text()).get("summary")
                except json.JSONDecodeError:
                    pass
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
            self._send(200, json.dumps(slim).encode(), "application/json")
            return
        if path == "/api/health":
            payload = {
                "ok": True,
                "service": "wolf-intelligence-owner-ui",
                "port": OWNER_UI_PORT,
                "pid": os.getpid(),
                "how_to_open": f"http://{OWNER_UI_HOST}:{OWNER_UI_PORT}/",
                "beta_path_note": "Also /owner/intelligence on Beta :8788 when route wired",
            }
            self._send(200, json.dumps(payload).encode(), "application/json")
            return
        self._send(404, b"not found", "text/plain")


    def do_POST(self) -> None:  # noqa: N802
        ensure_dirs()
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            self._send(400, b'{"ok":false,"error":"bad_json"}', "application/json")
            return
        if path in ("/api/human-decision", "/api/wolf-intelligence/human-decision"):
            wid = body.get("work_item_id")
            decision = (body.get("decision") or "").upper()
            rating = body.get("rating")
            notes = body.get("notes") or ""
            if not wid or decision not in ("PASS", "FAIL", "NEEDS_YOU"):
                self._send(400, b'{"ok":false,"error":"need work_item_id and decision PASS|FAIL|NEEDS_YOU"}', "application/json")
                return
            from . import learning, work_items
            item = work_items.get(wid)
            if not item:
                self._send(404, b'{"ok":false,"error":"not_found"}', "application/json")
                return
            if decision == "PASS":
                learning.record_outcome(wid, human_passed=True, human_rating=int(rating) if rating else 4, notes=notes or "owner pass", source="owner_ui")
            elif decision == "FAIL":
                learning.record_outcome(wid, human_passed=False, human_rating=int(rating) if rating else 1, notes=notes or "owner fail", source="owner_ui")
            else:
                if item["state"] in ("READY_TO_TEST", "RUNNING", "RECOMMENDED"):
                    work_items.transition(wid, "NEEDS_YOU", reason=notes or "owner flagged")
                learning.record_outcome(wid, notes=notes or "needs you", self_eval_rating=None, source="owner_ui")
            item = work_items.get(wid)
            self._send(200, json.dumps({"ok": True, "item": {"id": wid, "state": item["state"]}}).encode(), "application/json")
            return
        self._send(404, b"not found", "text/plain")


class ReuseHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def main() -> int:
    ensure_dirs()
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    pid_path = AUDIT_DIR / "owner-ui.pid"
    pid_path.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    server = ReuseHTTPServer((OWNER_UI_HOST, OWNER_UI_PORT), Handler)
    print(f"OWNER_UI http://{OWNER_UI_HOST}:{OWNER_UI_PORT}/ pid={os.getpid()}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if pid_path.exists() and pid_path.read_text().strip() == str(os.getpid()):
                pid_path.unlink(missing_ok=True)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
