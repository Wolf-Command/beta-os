#!/usr/bin/env python3
"""Prove clean UI routes against the REAL Beta stack on :8788.

NOT an ephemeral ThreadingHTTPServer test. Hits http://127.0.0.1:8788 so a
stale serve_beta process cannot hide behind unit-test greens.

Exit non-zero on any FAIL. Prints PASS/FAIL lines.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Optional, Tuple

BASE = os.environ.get("WOLF_BETA_BASE", "http://127.0.0.1:8788").rstrip("/")
HOST, PORT = "127.0.0.1", 8788

PROGRESS_MARKERS = (
    "Progress",
    "progress",
    "dashboard",
    "id=",
)


def _eprint(*a: object) -> None:
    print(*a, file=sys.stderr)


def port_listening(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2.0):
            return True
    except OSError:
        return False


def listener_cmdline(port: int) -> str:
    """Best-effort: who owns the TCP listen on port (macOS lsof)."""
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        return f"<lsof unavailable: {exc}>"
    return out.strip()


def assert_serve_beta_listener(port: int) -> None:
    blob = listener_cmdline(port).lower()
    if "serve_beta" not in blob and "python" not in blob:
        raise SystemExit(
            f"FAIL: :{port} listener does not look like serve_beta/python:\n{blob}"
        )
    if "serve_beta" not in blob:
        # soft warn but continue if python is listening (LaunchAgent may show python3 path)
        print(f"WARN: serve_beta string not in lsof; python listener present:\n{blob}")
    else:
        print(f"PASS listener: serve_beta on :{port}")


def http_get(path: str, timeout: float = 8.0) -> Tuple[int, bytes, dict]:
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, method="GET", headers={"Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read() if e.fp else b"", dict(e.headers or {})
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"FAIL: request {url} errored: {exc}") from exc


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS {name}" + (f" — {detail}" if detail else ""))
    else:
        print(f"FAIL {name}" + (f" — {detail}" if detail else ""))
        raise SystemExit(1)


def main() -> int:
    print(f"prove_deployed_ui_routes BASE={BASE}")
    if not port_listening(HOST, PORT):
        print(f"FAIL :{PORT} not listening")
        return 1
    print(f"PASS :{PORT} listening")
    assert_serve_beta_listener(PORT)

    # /progress clean
    code, body, _ = http_get("/progress")
    text = body.decode("utf-8", "replace")
    markers_hit = [m for m in PROGRESS_MARKERS if m in text]
    check(
        "GET /progress",
        code == 200 and len(markers_hit) >= 1 and ("html" in text.lower() or "<" in text),
        f"status={code} bytes={len(body)} markers={markers_hit[:3]}",
    )

    code, body, _ = http_get("/progress.html")
    check("GET /progress.html", code == 200, f"status={code} bytes={len(body)}")

    # /api/progress unauthenticated — must NOT be 404 (fail-closed auth)
    code, body, _ = http_get("/api/progress")
    text = body.decode("utf-8", "replace")
    not_404 = code != 404
    authish = code in (401, 403) or "missing_auth" in text or "auth" in text.lower()
    check(
        "GET /api/progress (no auth)",
        not_404 and (authish or code in (401, 403)),
        f"status={code} body_snip={text[:120]!r}",
    )

    code, body, _ = http_get("/uma-blu-close")
    check("GET /uma-blu-close", code == 200, f"status={code} bytes={len(body)}")

    code, body, _ = http_get("/habitat-operator")
    check("GET /habitat-operator", code == 200, f"status={code} bytes={len(body)}")

    print("PASS all deployed-route checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
