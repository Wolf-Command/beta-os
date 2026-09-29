#!/usr/bin/env python3
"""HEADCHEF-1 shots — Recipe Builder list/detail/create + denied (1024 / 390)."""
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
_TMP = Path(tempfile.mkdtemp(prefix="headchef1-shots-"))
os.environ["RECIPE_BUILDER_DB"] = str(_TMP / "recipes.sqlite")
sys.path.insert(0, str(ROOT / "scripts"))

from core import recipe_builder as rb  # noqa: E402
import serve_beta as sb  # noqa: E402

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HARI = "carolus.haryanto@gmail.com"

# name, path, width, height, marker, action: list|detail|create|none
SPECS = [
    ("headchef1-recipe-list-desktop.png", "/bzg/recipe-builder", 1024, 900, "Recipe Builder", "list"),
    ("headchef1-recipe-list-phone.png", "/bzg/recipe-builder", 390, 844, "Recipe Builder", "list"),
    ("headchef1-recipe-detail-desktop.png", "/bzg/recipe-builder", 1024, 900, "Sell price", "detail"),
    ("headchef1-recipe-detail-phone.png", "/bzg/recipe-builder", 390, 844, "Sell price", "detail"),
    ("headchef1-recipe-create-desktop.png", "/bzg/recipe-builder", 1024, 900, "New recipe", "create"),
    ("headchef1-recipe-create-phone.png", "/bzg/recipe-builder", 390, 844, "New recipe", "create"),
    ("headchef1-denied-desktop.png", "/wolf", 1024, 900, "Access denied", "none"),
    ("headchef1-denied-phone.png", "/wolf", 390, 844, "Access denied", "none"),
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


def capture(port: int, path: str, width: int, height: int, dest: Path, marker: str, action: str) -> str:
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
                        "X-Wolf-Subject": HARI,
                        "Cf-Access-Authenticated-User-Email": HARI,
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
            while time.time() < deadline:
                got = cdp(
                    "Runtime.evaluate",
                    {"expression": "document.body ? document.body.innerText : ''", "returnByValue": True},
                )
                text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")
                if "Recipe Builder" in text or "do not have access" in text.lower() or "forbidden" in text.lower():
                    break
                time.sleep(0.3)
            if action == "detail":
                cdp(
                    "Runtime.evaluate",
                    {
                        "expression": "var r=document.querySelector('#list [data-id]'); if(r) r.click();",
                        "returnByValue": True,
                    },
                )
                time.sleep(1.0)
            elif action == "create":
                cdp(
                    "Runtime.evaluate",
                    {
                        "expression": "var b=document.getElementById('tab-create'); if(b) b.click();",
                        "returnByValue": True,
                    },
                )
                time.sleep(0.5)
            deadline = time.time() + 20
            while time.time() < deadline:
                got = cdp(
                    "Runtime.evaluate",
                    {"expression": "document.body ? document.body.innerText : ''", "returnByValue": True},
                )
                text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")
                if marker.lower() in text.lower():
                    break
                time.sleep(0.3)
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
    report = rb.import_v1_recipes()
    print("import", report.get("total") or report)
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
    for name, path, w, h, marker, action in SPECS:
        dest = SHOTS / name
        try:
            text = capture(port, path, w, h, dest, marker, action)
            good = dest.is_file() and dest.stat().st_size > 3000 and marker.lower() in text.lower()
            print(
                ("PASS" if good else "FAIL"),
                name,
                dest.stat().st_size if dest.is_file() else 0,
                text[:120].replace("\n", " "),
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
