#!/usr/bin/env python3
"""Studio pipe-health sensor + HTTP endpoint (Tailscale bind only).

PIPE_OK when Grok Bot main exists, state not stopped/zombie, and AppleEvent
responds within timeout. PIPE_DEAD otherwise (app may still be present).
Never prints secrets. Binds only to TAILSCALE_IP:PORT.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import conn_state as conn_state_mod

TZ = timezone(timedelta(hours=8), name="WITA")
EXACT = "/Applications/Grok Bot.app/Contents/MacOS/Grok Bot"
BIND_HOST = os.environ.get("WOLF_PIPE_BIND", "100.113.26.51")
BIND_PORT = int(os.environ.get("WOLF_PIPE_PORT", "2223"))
HB_PATH = Path(os.environ.get("WOLF_PIPE_HB", "/tmp/wolf-pipe-heartbeat.json"))
AUDIT = Path(os.environ.get("WOLF_PIPE_AUDIT", str(Path.home() / "beta-os/state/mac-reachability/logs/pipe-sensor.audit.jsonl")))
PROBE_TIMEOUT = float(os.environ.get("WOLF_PIPE_PROBE_TIMEOUT", "5"))
REFRESH_SEC = float(os.environ.get("WOLF_PIPE_REFRESH_SEC", "15"))

_lock = threading.Lock()
_latest: dict = {"pipe_ok": False, "pipe": "INIT"}


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def find_main() -> tuple[str | None, str | None]:
    out = subprocess.check_output(["ps", "-ax", "-o", "pid=,state=,command="], text=True, errors="replace")
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        pid, state, cmd = parts[0], parts[1], parts[2]
        if cmd == EXACT:
            return pid, state
    return None, None


def appleevent_ok(timeout: float = PROBE_TIMEOUT) -> tuple[bool, float, str]:
    t0 = time.time()
    try:
        r = subprocess.run(
            ["osascript", "-e", 'tell application "Grok Bot" to get name'],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.time() - t0
        ok = r.returncode == 0 and "Grok Bot" in (r.stdout or "")
        return ok, elapsed, "ok" if ok else f"rc_{r.returncode}"
    except subprocess.TimeoutExpired:
        return False, time.time() - t0, "timeout"
    except Exception as e:
        return False, time.time() - t0, type(e).__name__


def compute() -> dict:
    pid, state = find_main()
    ts = now_iso()
    if not pid:
        d = {
            "ts_wita": ts,
            "app_pid": None,
            "state": None,
            "ae_ok": False,
            "ae_s": None,
            "ae_detail": "no_pid",
            "pipe_ok": False,
            "pipe": "PIPE_DEAD",
            "reason": "GROK_APP_NONE",
        }
        return d
    # T=stopped (SIGSTOP), Z=zombie
    if state and state[0] in ("T", "Z"):
        d = {
            "ts_wita": ts,
            "app_pid": int(pid),
            "state": state,
            "ae_ok": False,
            "ae_s": None,
            "ae_detail": "state_stopped_or_zombie",
            "pipe_ok": False,
            "pipe": "PIPE_DEAD",
            "reason": f"STATE_{state[0]}",
        }
        return d
    ae_ok, ae_s, ae_detail = appleevent_ok()
    pipe_ok = bool(ae_ok)
    d = {
        "ts_wita": ts,
        "app_pid": int(pid),
        "state": state,
        "ae_ok": ae_ok,
        "ae_s": round(ae_s, 3),
        "ae_detail": ae_detail,
        "pipe_ok": pipe_ok,
        "pipe": "PIPE_OK" if pipe_ok else "PIPE_DEAD",
        "reason": "AE_OK" if pipe_ok else f"AE_{ae_detail}",
    }
    # Third signal: WorkspaceConnectionService log state
    try:
        cs = conn_state_mod.scan_live()
        d["conn_state"] = cs.get("conn_state")
        d["conn_state_age_s"] = cs.get("conn_state_age_s")
        d["conn_reason"] = cs.get("conn_reason")
        # Conn votes PIPE_DEAD only when bad state aged >= threshold
        if cs.get("conn_pipe_ok") is False:
            d["pipe_ok"] = False
            d["pipe"] = "PIPE_DEAD"
            d["reason"] = cs.get("conn_reason") or "CONN_DEAD"
        elif pipe_ok:
            d["reason"] = d["reason"] + "+" + (cs.get("conn_reason") or "CONN_NA")
    except Exception as e:
        d["conn_state"] = "unknown"
        d["conn_state_age_s"] = None
        d["conn_reason"] = f"CONN_SCAN_{type(e).__name__}"
    return d


def publish(d: dict) -> None:
    global _latest
    with _lock:
        _latest = d
    HB_PATH.write_text(json.dumps(d, indent=2) + "\n")
    try:
        os.chmod(HB_PATH, 0o644)
    except Exception:
        pass
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "probe", **d}, ensure_ascii=False) + "\n")


def refresher() -> None:
    while True:
        try:
            publish(compute())
        except Exception as e:
            publish(
                {
                    "ts_wita": now_iso(),
                    "pipe_ok": False,
                    "pipe": "PIPE_DEAD",
                    "reason": f"SENSOR_EXC_{type(e).__name__}",
                }
            )
        time.sleep(REFRESH_SEC)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return  # quiet

    def do_GET(self):
        if self.path not in ("/pipe-health", "/health", "/"):
            self.send_response(404)
            self.end_headers()
            return
        with _lock:
            body = json.dumps(_latest).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main() -> None:
    publish(compute())
    threading.Thread(target=refresher, daemon=True).start()
    httpd = ThreadedHTTPServer((BIND_HOST, BIND_PORT), Handler)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
