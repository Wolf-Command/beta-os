#!/usr/bin/env python3
"""HUMFIX-1C shots — Haikal/Zayen My Work + Zayen header (1024 / 390)."""
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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"
sys.path.insert(0, str(ROOT / "scripts"))

import serve_beta as sb  # noqa: E402

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"

EMAIL = {
    "PERS-ZAYEN": "laluzayen@gmail.com",
    "PERS-HAIKAL": "haikalqilbari123@gmail.com",
}

# name, person, path, width, height, marker, scroll_retest
SPECS = [
    ("humfix1c-haikal-mywork-desktop.png", "PERS-HAIKAL", "/my-work", 1024, 900, "Retest", True),
    ("humfix1c-haikal-mywork-phone.png", "PERS-HAIKAL", "/my-work", 390, 844, "Retest", True),
    ("humfix1c-zayen-mywork-desktop.png", "PERS-ZAYEN", "/my-work", 1024, 900, "Retest", True),
    ("humfix1c-zayen-mywork-phone.png", "PERS-ZAYEN", "/my-work", 390, 844, "approve or reject", True),
    ("humfix1c-zayen-header-desktop.png", "PERS-ZAYEN", "/amg/finance#workbench", 1024, 900, "Atrium Financial Controller", False),
    ("humfix1c-zayen-header-phone.png", "PERS-ZAYEN", "/amg/finance#workbench", 390, 844, "Atrium Financial Controller", False),
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


def capture(
    port: int,
    path: str,
    email: str,
    width: int,
    height: int,
    dest: Path,
    marker: str,
    scroll_retest: bool,
) -> str:
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
            cdp("Network.setExtraHTTPHeaders", {"headers": {"X-Wolf-Subject": email}})
            cdp("Page.enable")
            cdp(
                "Emulation.setDeviceMetricsOverride",
                {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": width < 500},
            )
            cdp("Page.navigate", {"url": f"http://127.0.0.1:{port}{path}"})
            text = ""
            deadline = time.time() + 55
            while time.time() < deadline:
                got = cdp(
                    "Runtime.evaluate",
                    {"expression": "document.body ? document.body.innerText : ''", "returnByValue": True},
                )
                text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")
                if marker.lower() in text.lower() and "Checking session" not in text and "Initializing Atrium" not in text:
                    break
                time.sleep(0.35)
            if scroll_retest:
                cdp(
                    "Runtime.evaluate",
                    {
                        "expression": """
                        (() => {
                          const el = Array.from(document.querySelectorAll('h2,h3,.work-title,li,article,section *'))
                            .find(n => /Retest:/i.test((n.textContent||'').trim()));
                          if (el) el.scrollIntoView({block:'start', inline:'nearest'});
                          const today = Array.from(document.querySelectorAll('h2'))
                            .find(h => (h.textContent||'').trim() === 'TODAY');
                          if (today) today.scrollIntoView({block:'start'});
                          return !!(el || today);
                        })()
                        """,
                        "returnByValue": True,
                    },
                )
                time.sleep(0.35)
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            sock.close()
            return text
        finally:
            proc.kill()
            proc.wait(timeout=5)


def main() -> int:
    if not CHROME.is_file():
        print("FAIL chrome missing")
        return 1
    handler = next(
        obj
        for obj in vars(sb).values()
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler"
    )
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"beta_temp={port}")
    ok = 0
    for name, person, path, w, h, marker, scroll in SPECS:
        dest = SHOTS / name
        try:
            text = capture(port, path, EMAIL[person], w, h, dest, marker, scroll)
            good = dest.is_file() and dest.stat().st_size > 3000
            print(
                ("PASS" if good else "FAIL"),
                name,
                dest.stat().st_size if dest.is_file() else 0,
                text[:100].replace("\n", " "),
            )
            if good:
                ok += 1
        except Exception as exc:
            print("FAIL", name, exc)
    httpd.shutdown()
    print(f"SHOTS ok={ok}/{len(SPECS)}")
    return 0 if ok == len(SPECS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
