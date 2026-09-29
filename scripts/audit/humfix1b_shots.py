#!/usr/bin/env python3
"""HUMFIX-1B shots — copy opsfix2 CDP pattern (short-lived BetaHandler)."""
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

# Reopen held RETESTs before serve_beta installs write guard
import sqlite3
from datetime import datetime, timezone

RETEST_IDS = (
    "WI-1e3435eb-4d39-4559-a2fa-3cf13b523ec2",
    "WI-2a6edd45-1659-446a-91ea-8b533faf580e",
    "WI-fa0f1e2e-9564-41f6-8edf-cbc76a3173e2",
    "WI-cbbbaf8c-55bf-4167-a7ae-6d0f974d5b9f",
    "WI-4049b070-1938-4b33-bc6f-abcf195d4298",
    "WI-1b6f3982-7112-4ff9-9147-97e0ed1c645d",
    "WI-41cd93c3-a8d5-48ad-9368-db17d44e80a4",
    "WI-a3a4044c-843d-41f4-86eb-8d738f78e2b1",
    "WI-4e4566db-72bf-4710-b6a9-0b02f64bbc2b",
    "WI-1804769a-551b-4df0-9e8c-231dd4131417",
    "WI-2649ab6e-653a-472b-b632-dfb236ee64f2",
    "WI-3e07075e-72cb-4e5f-bea4-97003d7c678f",
)
_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
_c = sqlite3.connect(str(ROOT / "catalog" / "content_library.sqlite"))
for wid in RETEST_IDS:
    _c.execute(
        "UPDATE core_work_items SET routing_state=NULL, routing_reason=NULL, updated_at=? WHERE work_item_id=? AND routing_state='HELD'",
        (_ts, wid),
    )
_c.commit()
_c.close()

import serve_beta as sb  # noqa: E402

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"

EMAIL = {
    "PERS-ZAYEN": "laluzayen@gmail.com",
    "PERS-HAIKAL": "haikalqilbari123@gmail.com",
    "PERS-YUDI": "widiatmika.11@gmail.com",
    "PERS-RAPP": "evetrovert@gmail.com",
}

# name, person, path, width, height, marker, open_dropdown ("", "drone", "brand")
SPECS = [
    ("humfix1b-zayen-gl-desktop.png", "PERS-ZAYEN", "/amg/finance#ledger", 1024, 900, "General Ledger", ""),
    ("humfix1b-zayen-gl-phone.png", "PERS-ZAYEN", "/amg/finance#ledger", 390, 844, "General Ledger", ""),
    ("humfix1b-zayen-journals-desktop.png", "PERS-ZAYEN", "/amg/finance#workbench", 1024, 900, "Journal", ""),
    ("humfix1b-zayen-journals-phone.png", "PERS-ZAYEN", "/amg/finance#workbench", 390, 844, "Journal", ""),
    ("humfix1b-zayen-title-desktop.png", "PERS-ZAYEN", "/amg/finance#workbench", 1024, 900, "Financial Controller", ""),
    ("humfix1b-zayen-title-phone.png", "PERS-ZAYEN", "/amg/finance#ledger", 390, 844, "Financial Controller", ""),
    ("humfix1b-haikal-plan-desktop.png", "PERS-HAIKAL", "/content-2.0?brand=habitat#plan", 1024, 900, "plan", ""),
    ("humfix1b-haikal-plan-phone.png", "PERS-HAIKAL", "/content-2.0?brand=habitat#plan", 390, 844, "plan", ""),
    ("humfix1b-haikal-drone-desktop.png", "PERS-HAIKAL", "/content-2.0?brand=habitat#upload", 1024, 900, "Upload", "drone"),
    ("humfix1b-haikal-drone-phone.png", "PERS-HAIKAL", "/content-2.0?brand=habitat#upload", 390, 844, "Upload", "drone"),
    ("humfix1b-yudi-brands-desktop.png", "PERS-YUDI", "/content-2.0", 1024, 900, "Hi", "brand"),
    ("humfix1b-yudi-brands-phone.png", "PERS-YUDI", "/content-2.0", 390, 844, "Hi", "brand"),
    ("humfix1b-haikal-retest-mywork-desktop.png", "PERS-HAIKAL", "/my-work", 1024, 900, "Retest", ""),
    ("humfix1b-haikal-retest-mywork-phone.png", "PERS-HAIKAL", "/my-work", 390, 844, "Retest", ""),
    ("humfix1b-zayen-retest-mywork-desktop.png", "PERS-ZAYEN", "/my-work", 1024, 900, "Retest", ""),
    ("humfix1b-zayen-retest-mywork-phone.png", "PERS-ZAYEN", "/my-work", 390, 844, "Retest", ""),
    ("humfix1b-rapp-mywork-phone.png", "PERS-RAPP", "/my-work", 390, 844, "Rapp", ""),
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


def capture(port: int, path: str, email: str, width: int, height: int, dest: Path, marker: str, open_dd: bool) -> str:
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
            if open_dd == "drone":
                cdp(
                    "Runtime.evaluate",
                    {
                        "expression": """
                        (() => {
                          const uploadNav = Array.from(document.querySelectorAll('a,button,[role=tab],.nav-link'))
                            .find(el => /^UPLOAD$/i.test((el.textContent||'').trim()));
                          if (uploadNav) uploadNav.click();
                          const show = () => {
                            const sel = document.getElementById('upMediaType');
                            if (!sel) return 'missing-upMediaType';
                            sel.focus();
                            sel.size = Math.min(sel.options.length, 8);
                            sel.style.height = 'auto';
                            sel.style.zIndex = '9999';
                            sel.style.position = 'relative';
                            return Array.from(sel.options).map(o => o.textContent.trim()).join('|');
                          };
                          return show();
                        })()
                        """,
                        "returnByValue": True,
                    },
                )
                # wait until upload panel paints Media type
                deadline2 = time.time() + 12
                while time.time() < deadline2:
                    got = cdp(
                        "Runtime.evaluate",
                        {
                            "expression": """
                            (() => {
                              const uploadNav = Array.from(document.querySelectorAll('a,button,[role=tab],.nav-link'))
                                .find(el => /^UPLOAD$/i.test((el.textContent||'').trim()));
                              if (uploadNav) uploadNav.click();
                              const sel = document.getElementById('upMediaType');
                              if (!sel) return '';
                              sel.size = Math.min(sel.options.length, 8);
                              sel.style.height = 'auto';
                              return Array.from(sel.options).map(o => o.textContent.trim()).join('|');
                            })()
                            """,
                            "returnByValue": True,
                        },
                    )
                    opts = str(((got.get("result") or {}).get("result") or {}).get("value") or "")
                    if "Drone" in opts:
                        break
                    time.sleep(0.25)
                time.sleep(0.35)
            elif open_dd == "brand":
                cdp(
                    "Runtime.evaluate",
                    {
                        "expression": """
                        (() => {
                          const btn = document.querySelector('[aria-label*=brand i], .brand-select, #brandSelect, button.brand, .topbar select')
                            || Array.from(document.querySelectorAll('button,select')).find(el => /habitat|all brands/i.test(el.textContent||''));
                          if (btn && btn.tagName === 'SELECT') {
                            btn.size = Math.min(btn.options.length, 12);
                            btn.style.height = 'auto';
                            return btn.options.length;
                          }
                          if (btn) btn.click();
                          return !!btn;
                        })()
                        """,
                        "returnByValue": True,
                    },
                )
                time.sleep(0.5)
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
    for name, person, path, w, h, marker, open_dd in SPECS:
        dest = SHOTS / name
        try:
            text = capture(port, path, EMAIL[person], w, h, dest, marker, open_dd)
            good = dest.is_file() and dest.stat().st_size > 3000
            print(("PASS" if good else "FAIL"), name, dest.stat().st_size if dest.is_file() else 0, text[:90].replace("\n", " "))
            if good:
                ok += 1
        except Exception as exc:
            print("FAIL", name, exc)
    httpd.shutdown()
    print(f"SHOTS ok={ok}/{len(SPECS)}")
    return 0 if ok >= len(SPECS) - 2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
