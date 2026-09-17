#!/usr/bin/env python3
"""Prove clean UI route aliases against the REAL Beta stack on :8788.

NOT an ephemeral ThreadingHTTPServer test. Hits http://127.0.0.1:8788 so a
stale serve_beta process cannot hide behind unit-test greens.

Override base via BETA_BASE_URL or WOLF_BETA_BASE.
No Production host. No Cloudflare write. No ESB/Metricool.

Exit non-zero on any RED. Prints a one-line matrix + PASS/FAIL lines.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from typing import List, Tuple
from urllib.parse import urlparse

BASE = (
    os.environ.get("BETA_BASE_URL")
    or os.environ.get("WOLF_BETA_BASE")
    or "http://127.0.0.1:8788"
).rstrip("/")

_parsed = urlparse(BASE)
HOST = _parsed.hostname or "127.0.0.1"
PORT = _parsed.port or (443 if _parsed.scheme == "https" else 80)

# (path, required_marker_substring)
ROUTES: List[Tuple[str, str]] = [
    ("/progress", "Wolf · Progress"),
    ("/progress.html", "Wolf · Progress"),
    ("/dashboards/progress.html", "Wolf · Progress"),
    ("/habitat-operator", "Habitat Operator"),
    ("/habitat-operator.html", "Habitat Operator"),
    ("/dashboards/habitat-operator.html", "Habitat Operator"),
    ("/uma-blu-close", "Uma Blu · Daily Close"),
    ("/uma-blu-close.html", "Uma Blu · Daily Close"),
    ("/dashboards/uma-blu-close.html", "Uma Blu · Daily Close"),
]


def port_listening(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2.0):
            return True
    except OSError:
        return False


def listener_blob(port: int) -> str:
    try:
        return subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        return f"<lsof unavailable: {exc}>"


def http_get(path: str, timeout: float = 8.0) -> Tuple[int, bytes]:
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, method="GET", headers={"Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as e:
        return int(e.code), e.read() if e.fp else b""
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"FAIL: request {url} errored: {exc}") from exc


def main() -> int:
    print(f"prove_deployed_routes BASE={BASE}")
    if HOST not in ("127.0.0.1", "localhost") or PORT == 8787:
        print(f"FAIL refused base (Beta :8788 only): {BASE}", file=sys.stderr)
        return 2

    if not port_listening(HOST, PORT):
        print(f"FAIL :{PORT} not listening — Beta unreachable (no silent-pass)")
        return 1
    print(f"PASS :{PORT} listening")

    blob = listener_blob(PORT).lower()
    if "serve_beta" not in blob and "python" not in blob:
        print(f"FAIL :{PORT} listener does not look like serve_beta/python:\n{blob}")
        return 1
    if "serve_beta" not in blob:
        print(f"WARN: serve_beta string not in lsof; python listener present:\n{blob}")
    else:
        print(f"PASS listener: serve_beta on :{PORT}")

    cells: List[str] = []
    failed = 0
    for path, marker in ROUTES:
        code, body = http_get(path)
        text = body.decode("utf-8", "replace")
        ok = code == 200 and code != 404 and marker in text
        tag = "GREEN" if ok else "RED"
        cells.append(f"{path}={tag}({code})")
        if ok:
            print(f"PASS GET {path} — status={code} marker={marker!r}")
        else:
            failed += 1
            print(
                f"FAIL GET {path} — status={code} bytes={len(body)} "
                f"marker_ok={marker in text}"
            )

    print("MATRIX " + " | ".join(cells))
    if failed:
        print(f"FAIL prove_deployed_routes — {failed} RED")
        return 1
    print("PASS all deployed-route checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
