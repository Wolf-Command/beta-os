#!/usr/bin/env python3
"""CORE-ENT-1 shots — Zayen AMG/BZG finance + GGV deny (1024 / 390)."""
from __future__ import annotations

import base64
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"
sys.path.insert(0, str(ROOT / "scripts"))

import serve_beta as sb  # noqa: E402
from core import canonical_guard as cg  # noqa: E402

# Import serve_beta first so CATALOG_DB globals exist, then retarget to a writable copy.
cg.isolate_runtime_catalog()

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
ZAYEN = "laluzayen@gmail.com"

SPECS = [
    ("coreent1-zayen-amg-finance-desktop.png", "/amg/finance/lite", 1024, 900, "Atrium Finance"),
    ("coreent1-zayen-amg-finance-phone.png", "/amg/finance/lite", 390, 844, "Atrium Finance"),
    ("coreent1-zayen-bzg-finance-desktop.png", "/bzg/finance", 1024, 900, "BZG Finance"),
    ("coreent1-zayen-bzg-finance-phone.png", "/bzg/finance", 390, 844, "BZG Finance"),
    ("coreent1-zayen-ggv-deny-desktop.png", "/ggv/finance", 1024, 900, "do not have access"),
    ("coreent1-zayen-ggv-deny-phone.png", "/ggv/finance", 390, 844, "do not have access"),
]


def _ws_connect(host: str, port: int, path: str) -> socket.socket:
    sock = socket.create_connection((host, port), timeout=30)
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall(
        (
            f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
            f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ).encode()
    )
    sock.recv(4096)
    return sock


def _ws_send(sock: socket.socket, text: str) -> None:
    payload = text.encode()
    header = bytearray([0x81])
    n = len(payload)
    mask = os.urandom(4)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack("!H", n))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack("!Q", n))
    header.extend(mask)
    header.extend(bytearray(b ^ mask[i % 4] for i, b in enumerate(payload)))
    sock.sendall(header)


def _ws_recv(sock: socket.socket) -> str:
    def read(n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("closed")
            buf += chunk
        return buf

    b1, b2 = read(2)
    length = b2 & 0x7F
    if length == 126:
        length = struct.unpack("!H", read(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", read(8))[0]
    if b2 & 0x80:
        mask = read(4)
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(read(length)))
    else:
        payload = read(length)
    return payload.decode()


def capture(port: int, path: str, width: int, height: int, dest: Path, marker: str) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:
        proc = subprocess.Popen(
            [
                str(CHROME),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--no-first-run",
                "--disable-extensions",
                "--remote-debugging-port=0",
                f"--user-data-dir={profile}",
                f"--window-size={width},{height}",
                "--force-device-scale-factor=1",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            port_file = Path(profile) / "DevToolsActivePort"
            deadline = time.time() + 15
            while time.time() < deadline and not port_file.is_file():
                time.sleep(0.1)
            dbg_port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
            with urlopen(f"http://127.0.0.1:{dbg_port}/json/list", timeout=5) as resp:
                tabs = json.loads(resp.read().decode())
            page = next(tab for tab in tabs if tab.get("type") == "page")
            ws_path = page["webSocketDebuggerUrl"].split("/", 3)[-1]
            sock = _ws_connect("127.0.0.1", dbg_port, "/" + ws_path)
            sock.settimeout(90)
            seq = 0

            def cdp(method: str, params: dict | None = None) -> dict:
                nonlocal seq
                seq += 1
                ident = seq
                _ws_send(sock, json.dumps({"id": ident, "method": method, "params": params or {}}))
                while True:
                    msg = json.loads(_ws_recv(sock))
                    if msg.get("id") == ident:
                        return msg

            cdp("Network.enable")
            cdp(
                "Network.setExtraHTTPHeaders",
                {
                    "headers": {
                        "X-Wolf-Subject": ZAYEN,
                        "Cf-Access-Authenticated-User-Email": ZAYEN,
                    }
                },
            )
            cdp("Page.enable")
            cdp(
                "Emulation.setDeviceMetricsOverride",
                {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": width < 500},
            )
            cdp("Page.navigate", {"url": f"http://127.0.0.1:{port}{path}"})
            text = ""
            deadline = time.time() + 40
            found = False
            while time.time() < deadline:
                got = cdp(
                    "Runtime.evaluate",
                    {"expression": "document.body ? document.body.innerText : ''", "returnByValue": True},
                )
                text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")
                low = text.lower()
                if (
                    marker.lower() in low
                    or "forbidden" in low
                    or "do not have access" in low
                    or "access denied" in low
                ):
                    found = True
                    break
                time.sleep(0.3)
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            data = base64.b64decode(((shot.get("result") or {}).get("data") or ""))
            dest.write_bytes(data)
            sock.close()
            return f"ok marker={found} size={dest.stat().st_size}"
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> int:
    if not CHROME.is_file():
        print("REFUSE: Chrome missing", file=sys.stderr)
        return 2
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sb.BetaHandler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.4)
    try:
        for name, path, w, h, marker in SPECS:
            dest = SHOTS / name
            status = capture(port, path, w, h, dest, marker)
            print(f"{name} {status}")
    finally:
        httpd.shutdown()
    missing = [n for n, *_ in SPECS if not (SHOTS / n).is_file() or (SHOTS / n).stat().st_size < 800]
    if missing:
        print("MISSING", missing, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
