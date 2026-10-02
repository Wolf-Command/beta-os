#!/usr/bin/env python3
"""BZG-DAILY-CLOSE-DEPLOYED-UX-ESB-PHOTO-1 — mobile/desktop prove shots."""
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
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"
sys.path.insert(0, str(ROOT / "scripts"))

import serve_beta as sb  # noqa: E402

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
EMAIL = "izazaen00@gmail.com"


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

    _b1, b2 = read(2)
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


def capture(port: int, width: int, height: int, dest: Path) -> dict:
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
            if not port_file.is_file():
                return {"ok": False, "error": "no DevToolsActivePort"}
            dbg_port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
            with urlopen(f"http://127.0.0.1:{dbg_port}/json/list", timeout=5) as resp:
                tabs = json.loads(resp.read().decode())
            page = next(tab for tab in tabs if tab.get("type") == "page")
            ws_path = page["webSocketDebuggerUrl"].split("/", 3)[-1]
            sock = _ws_connect("127.0.0.1", dbg_port, "/" + ws_path)
            sock.settimeout(90)
            state = {"seq": 0}

            def cdp(method: str, params: dict | None = None) -> dict:
                state["seq"] += 1
                ident = state["seq"]
                _ws_send(
                    sock, json.dumps({"id": ident, "method": method, "params": params or {}})
                )
                while True:
                    msg = json.loads(_ws_recv(sock))
                    if msg.get("id") == ident:
                        return msg

            cdp("Network.enable")
            cdp(
                "Network.setExtraHTTPHeaders",
                {
                    "headers": {
                        "X-Wolf-Subject": EMAIL,
                        "Cf-Access-Authenticated-User-Email": EMAIL,
                    }
                },
            )
            cdp("Page.enable")
            cdp(
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": width,
                    "height": height,
                    "deviceScaleFactor": 1,
                    "mobile": width < 500,
                },
            )
            cdp("Page.navigate", {"url": f"http://127.0.0.1:{port}/uma-blu-close"})
            found = False
            text = ""
            deadline = time.time() + 40
            while time.time() < deadline:
                got = cdp(
                    "Runtime.evaluate",
                    {
                        "expression": "document.body ? document.body.innerText : ''",
                        "returnByValue": True,
                    },
                )
                text = str(
                    ((got.get("result") or {}).get("result") or {}).get("value") or ""
                )
                if "Take Photo" in text and "Upload Photo" in text:
                    found = True
                    break
                time.sleep(0.3)
            over = cdp(
                "Runtime.evaluate",
                {
                    "expression": (
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth + 1"
                    ),
                    "returnByValue": True,
                },
            )
            overflow = bool(
                ((over.get("result") or {}).get("result") or {}).get("value")
            )
            btns = cdp(
                "Runtime.evaluate",
                {
                    "expression": (
                        "Array.from(document.querySelectorAll('button'))"
                        ".map(b=>b.textContent.trim())"
                        ".filter(t=>/Take Photo|Upload Photo/.test(t))"
                    ),
                    "returnByValue": True,
                },
            )
            btn_list = ((btns.get("result") or {}).get("result") or {}).get("value")
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            data = base64.b64decode(((shot.get("result") or {}).get("data") or ""))
            dest.write_bytes(data)
            sock.close()
            return {
                "ok": found and not overflow and isinstance(btn_list, list) and len(btn_list) >= 4,
                "marker_found": found,
                "overflow": overflow,
                "buttons": btn_list,
                "size": dest.stat().st_size,
                "text_snip": text[:180],
            }
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
        req = Request(
            f"http://127.0.0.1:{port}/uma-blu-close",
            headers={"X-Wolf-Subject": EMAIL},
        )
        with urlopen(req, timeout=10) as r:
            body = r.read().decode("utf-8", "replace")
            code = r.status
        html_checks = {
            "http_200": code == 200,
            "Take Photo": "Take Photo" in body,
            "Upload Photo": "Upload Photo" in body,
            'capture="environment"': 'capture="environment"' in body,
            "ESB DATA UNAVAILABLE": "ESB DATA UNAVAILABLE" in body,
            "btnEsbTakePhoto": "btnEsbTakePhoto" in body,
            "btnEdcTakePhoto": "btnEdcTakePhoto" in body,
            "no photo:// placeholder": 'placeholder="photo://esb-close' not in body,
        }
        print("AUTH_HTML", json.dumps(html_checks))
        if not all(html_checks.values()):
            return 1
        phone = capture(port, 390, 844, SHOTS / "bzgclose-ux-photo1-desk-phone.png")
        print("PHONE", json.dumps(phone))
        desk = capture(port, 1024, 1400, SHOTS / "bzgclose-ux-photo1-desk-desktop.png")
        print("DESK", json.dumps(desk))
        if not phone.get("ok") or not desk.get("ok"):
            return 1
    finally:
        httpd.shutdown()
    print("DEPLOYED_UX_PROVE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
