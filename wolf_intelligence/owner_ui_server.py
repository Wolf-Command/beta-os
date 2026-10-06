"""Simple Owner Beta UI server — phone-size board. No jargon in primary UI.

Listens on 127.0.0.1:8799 only. Does not touch Production :8787.
Durable via LaunchAgent com.wolfcommand.wolf-intelligence-owner-ui.

Access rules:
- No CORS headers. Other origins cannot read responses.
- Every request needs Host 127.0.0.1:<port> or localhost:<port> (blocks DNS rebinding).
- A browser Origin header, when sent, must be the same loopback origin.
- The board API (GET) and every POST need the Owner UI token.
- The HTML shell and /api/health carry no work data and need no token.
"""
from __future__ import annotations

import hmac
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer as _ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from . import work_items
from . import stats_store
from .paths import OWNER_UI_HOST, UI_DIR, UI_TOKEN_ENV, WORKER_STATUS_PATH, ensure_dirs, AUDIT_DIR, owner_ui_port

TZ = ZoneInfo("Asia/Makassar")

# Governance context: policy loaded once at startup; capacity refreshed per request.
_GOVERNANCE_CTX: dict | None = None


def load_governance_startup() -> dict:
    """Load policy once at startup (read-only). Capacity is refreshed per request."""
    from .allocation import load_tightening
    from .governance import load_policy

    pl = load_policy()
    return {
        "policy_load": pl,
        "tightening": load_tightening(pl.policy),
    }


def governance_ctx() -> dict:
    global _GOVERNANCE_CTX
    if _GOVERNANCE_CTX is None:
        _GOVERNANCE_CTX = load_governance_startup()
    return _GOVERNANCE_CTX


def _capacity_for_request() -> dict:
    """Capacity always uses the server clock; client-supplied time is ignored."""
    from .capacity import capacity_snapshot

    ctx = governance_ctx()
    pl = ctx["policy_load"]
    return capacity_snapshot(
        datetime.now(TZ),
        policy=pl.policy,
        policy_mode=pl.mode,
    )

HTML = UI_DIR / "owner.html"
_SESSION_COOKIE = "wolf_intelligence_session"


def ui_token() -> str:
    """Read the Owner UI token. Callers must not log the return value."""
    return os.environ.get(UI_TOKEN_ENV, "").strip()


def presented_token(headers) -> str:
    auth = headers.get("Authorization") or ""
    if len(auth) >= 7 and auth[:7].lower() == "bearer ":
        return auth[7:].strip()
    session = (headers.get("X-Wolf-Session") or "").strip()
    if session:
        return session
    cookie = headers.get("Cookie") or ""
    for part in cookie.split(";"):
        name, _, value = part.strip().partition("=")
        if name == _SESSION_COOKIE and value.strip():
            return value.strip()
    return ""


def token_matches(presented: str, expected: str) -> bool:
    if not presented or not expected:
        return False
    left = presented.encode("utf-8")
    right = expected.encode("utf-8")
    if len(left) != len(right):
        return False
    return hmac.compare_digest(left, right)


def post_authorized(headers) -> bool:
    """POST is allowed only when the env token is set and the request presents it."""
    expected = ui_token()
    if not expected:
        return False
    return token_matches(presented_token(headers), expected)


# Board reads use the same token as writes.
board_authorized = post_authorized

_LOOPBACK_NAMES = ("127.0.0.1", "localhost")


def allowed_hosts(port: int) -> frozenset[str]:
    return frozenset(f"{name}:{port}" for name in _LOOPBACK_NAMES)


def host_allowed(headers, port: int) -> bool:
    host = (headers.get("Host") or "").strip().lower()
    return host in allowed_hosts(port)


def origin_allowed(headers, port: int) -> bool:
    """No Origin header (curl, same-origin GET) is fine. A sent Origin must be loopback:port."""
    origin = (headers.get("Origin") or "").strip().lower()
    if not origin:
        return True
    return origin in {f"http://{h}" for h in allowed_hosts(port)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        """Log method and path only. Never the headers, so the token is not written."""
        try:
            ensure_dirs()
            AUDIT_DIR.mkdir(parents=True, exist_ok=True)
            path = urlparse(self.path).path
            line = "%s %s %s\n" % (self.log_date_time_string(), self.command, path)
            with (AUDIT_DIR / "owner-ui-access.log").open("a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Vary", "Authorization, Cookie, X-Wolf-Session")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _port(self) -> int:
        return int(self.server.server_address[1])

    def _request_scope_ok(self) -> bool:
        """Host allowlist + same-origin check. Sends 403 and returns False on failure."""
        port = self._port()
        if not host_allowed(self.headers, port):
            self._send(403, b'{"ok":false,"error":"host_not_allowed"}', "application/json")
            return False
        if not origin_allowed(self.headers, port):
            self._send(403, b'{"ok":false,"error":"origin_not_allowed"}', "application/json")
            return False
        return True

    def do_GET(self) -> None:  # noqa: N802
        if not self._request_scope_ok():
            return
        ensure_dirs()
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/owner", "/wolf-intelligence", "/owner/intelligence"):
            body = HTML.read_bytes()
            self._send(200, body, "text/html; charset=utf-8")
            return
        if path in ("/api/owner-board", "/api/wolf-intelligence/board"):
            if not board_authorized(self.headers):
                self._send(401, b'{"ok":false,"error":"unauthorized"}', "application/json")
                return
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
            port = self._port()
            payload = {
                "ok": True,
                "service": "wolf-intelligence-owner-ui",
                "port": port,
                "pid": os.getpid(),
                "how_to_open": f"http://{OWNER_UI_HOST}:{port}/",
                "board_auth": "token",
            }
            self._send(200, json.dumps(payload).encode(), "application/json")
            return
        if path == "/api/governance/status":
            if not board_authorized(self.headers):
                self._send(401, b'{"ok":false,"error":"unauthorized"}', "application/json")
                return
            ctx = governance_ctx()
            pl = ctx["policy_load"]
            cap = _capacity_for_request()
            from .allocation import load_tightening
            tightening = load_tightening(pl.policy)
            payload = {
                "ok": True,
                "policy_mode": pl.mode,
                "policy_sha256": pl.sha256,
                "policy_sha256_prefix": pl.sha256[:12] if pl.sha256 else "",
                "policy_version": (pl.policy or {}).get("version"),
                "policy_id": (pl.policy or {}).get("policy_id"),
                "capacity": cap,
                "grok_routing_penalty": tightening.get("grok_routing_penalty", 0.0),
            }
            self._send(200, json.dumps(payload).encode(), "application/json")
            return
        self._send(404, b"not found", "text/plain")


    def do_POST(self) -> None:  # noqa: N802
        if not self._request_scope_ok():
            return
        ensure_dirs()
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        if not post_authorized(self.headers):
            self._send(401, b'{"ok":false,"error":"unauthorized"}', "application/json")
            return
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
            actor = body.get("actor")
            actor_s = actor.strip() if isinstance(actor, str) else ""
            if not wid or decision not in ("PASS", "FAIL", "NEEDS_YOU"):
                self._send(400, b'{"ok":false,"error":"need work_item_id and decision PASS|FAIL|NEEDS_YOU"}', "application/json")
                return
            if decision in ("PASS", "FAIL") and not actor_s:
                self._send(400, b'{"ok":false,"error":"actor_required"}', "application/json")
                return
            from . import learning, work_items
            item = work_items.get(wid)
            if not item:
                self._send(404, b'{"ok":false,"error":"not_found"}', "application/json")
                return
            if decision == "PASS":
                learning.record_outcome(
                    wid,
                    human_passed=True,
                    human_rating=int(rating) if rating else 4,
                    notes=notes or "owner pass",
                    source="owner_ui",
                    actor=actor_s,
                )
            elif decision == "FAIL":
                learning.record_outcome(
                    wid,
                    human_passed=False,
                    human_rating=int(rating) if rating else 1,
                    notes=notes or "owner fail",
                    source="owner_ui",
                    actor=actor_s,
                )
            else:
                if item["state"] in ("READY_TO_TEST", "RUNNING", "RECOMMENDED"):
                    work_items.transition(wid, "NEEDS_YOU", reason=notes or "owner flagged")
                learning.record_outcome(wid, notes=notes or "needs you", self_eval_rating=None, source="owner_ui", actor=actor_s or None)
            item = work_items.get(wid)
            self._send(200, json.dumps({"ok": True, "item": {"id": wid, "state": item["state"]}}).encode(), "application/json")
            return
        if path == "/api/governance/decide":
            from .allocation import decide, LedgerView
            from .imbalance import check_imbalance
            ctx = governance_ctx()
            cap = _capacity_for_request()
            server_now = datetime.now(TZ)
            dec = decide(
                body,
                policy_load=ctx["policy_load"],
                capacity=cap,
                ledger_view=LedgerView(),
                now=server_now,
                record=True,
            )
            check_imbalance(ctx["policy_load"], LedgerView(), now=server_now)
            self._send(200, json.dumps({"ok": True, "decision": dec.to_dict()}).encode(), "application/json")
            return
        self._send(404, b"not found", "text/plain")


def _qa_harness_in_memory_only() -> bool:
    """QA harnesses use in-memory handlers; ephemeral bind breaks their http() helper."""
    root = os.environ.get("WOLF_INTELLIGENCE_STATE_ROOT", "")
    return "qa-" in root or "qa-r2" in root or "/qa-" in root


class ThreadingHTTPServer(_ThreadingHTTPServer):
    def server_bind(self) -> None:
        if _qa_harness_in_memory_only():
            raise PermissionError("QA harness in-memory UI only")
        super().server_bind()


class ReuseHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def main() -> int:
    global _GOVERNANCE_CTX
    if OWNER_UI_HOST != "127.0.0.1":
        print("OWNER_UI refusing non-loopback bind", flush=True)
        return 2
    try:
        port = owner_ui_port()
    except ValueError as exc:
        print(f"OWNER_UI {exc}", flush=True)
        return 2
    ensure_dirs()
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    _GOVERNANCE_CTX = load_governance_startup()
    pl = _GOVERNANCE_CTX["policy_load"]
    cap = _capacity_for_request()
    sha_prefix = pl.sha256[:12] if pl.sha256 else "none"
    grok_state = cap.get("grok_state", "UNKNOWN")
    print(
        f"GOVERNANCE policy={sha_prefix} mode={pl.mode} grok_state={grok_state}",
        flush=True,
    )
    pid_path = AUDIT_DIR / "owner-ui.pid"
    pid_path.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    server = ReuseHTTPServer((OWNER_UI_HOST, port), Handler)
    post_mode = "auth" if ui_token() else "read-only"
    print(
        f"OWNER_UI http://{OWNER_UI_HOST}:{port}/ pid={os.getpid()} post={post_mode}",
        flush=True,
    )
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
