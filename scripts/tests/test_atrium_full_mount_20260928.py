#!/usr/bin/env python3
"""ATRIUMFIN-FULL-1. Zayen's product behind Wolf auth.

Uses a short-lived Beta handler in development_assertion and the loopback
sidecar on 127.0.0.1:8790. Does not switch the live :8788 process.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import sqlite3
import struct
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["BETA_AUTH_MODE"] = "development_assertion"
import sys

sys.path.insert(0, str(ROOT / "scripts"))

from core import atrium_full_mount as mount  # noqa: E402

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SHOTS = ROOT / "docs" / "wolf" / "staff" / "shots"
DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")
ZAYEN = "laluzayen@gmail.com"
OWNER = "mrwolf@wolfcommand.net"
PASS = 0
FAIL = 0

PAGES = (
    "/amg/finance",
    "/amg/finance/api/dashboard",
    "/amg/finance/api/journals",
    "/amg/finance/api/ledger",
    "/amg/finance/api/trial-balance",
    "/amg/finance/api/reports/usali",
    "/amg/finance/api/reports/financial-statements",
    "/amg/finance/api/inventory/dashboard",
    "/amg/finance/api/ar/items",
    "/amg/finance/api/ap/items",
    "/amg/finance/api/accounts",
)
DENIED = (
    ("POST", "/amg/finance/api/ap/payments"),
    ("POST", "/amg/finance/api/tax/payment"),
    ("POST", "/amg/finance/api/bank/transfer"),
    ("GET", "/amg/finance/api/admin/settings"),
    ("POST", "/amg/finance/api/admin/access-control/switch-user"),
    ("POST", "/amg/finance/api/auth/login"),
)
# Officer assertion still blocks approve/post; FC assertion allows both (SoD server-side).
DENIED_OFFICER_APPROVE = ("POST", "/amg/finance/api/journals/JRN-1/approve")
DENIED_OFFICER_POST = ("POST", "/amg/finance/api/journals/JRN-1/post")
SHOT_VIEWS = (
    ("command", "/amg/finance#command-centre", "Control Surface"),
    ("journal", "/amg/finance#workbench", "Journal"),
    ("ledger", "/amg/finance#ledger", "No posted journal lines for ENT-AMG yet"),
    ("trial", "/amg/finance#trial-balance", "Trial Balance Report"),
    ("reports", "/amg/finance#reports", "Rooms Revenue"),
    ("inventory", "/amg/finance#inventory", "Hotel Inventory"),
    ("ar", "/amg/finance#ar", "Accounts Receivable"),
    ("ap", "/amg/finance#ap", "Accounts Payable"),
)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name} {detail}")


def call(port: int, method: str, path: str, headers: dict | None = None, body: bytes | None = None) -> tuple[int, bytes]:
    req = Request(f"http://127.0.0.1:{port}{path}", data=body, headers=headers or {}, method=method)
    try:
        with urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def sidecar_call(method: str, path: str, token: str | None, extra: dict | None = None) -> tuple[int, bytes]:
    headers = {"Accept": "application/json"}
    if token:
        headers["X-Wolf-Assertion"] = token
    if extra:
        headers.update(extra)
    req = Request(f"http://127.0.0.1:8790{path}", headers=headers, method=method, data=b"{}" if method == "POST" else None)
    try:
        with urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def test_data() -> None:
    check("beta db exists", DB.is_file(), str(DB))
    if not DB.is_file():
        return
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        accounts = conn.execute("select count(*) from accounts").fetchone()[0]
        journals = conn.execute("select count(*) from journal_headers").fetchone()[0]
        owners = conn.execute("select count(*) from owner_pool_units").fetchone()[0]
        items = conn.execute("select count(*) from inventory_items").fetchone()[0]
        ids = {row[0] for row in conn.execute("select id from users")}
        check("chart includes the 190 atrium accounts", accounts >= 190, str(accounts))
        check("journals present or empty ok", journals >= 0, str(journals))
        check("no owners", owners == 0, str(owners))
        check("no stock", items == 0, str(items))
        check("no financial controller user", "usr-controller-1" not in ids, str(sorted(ids)))
        check("wolf seats exist", {"PERS-ZAYEN", "PERS-MATT", "PERS-ZENITALFATHAN"} <= ids)
    finally:
        conn.close()
    text = (ROOT / "scripts" / "serve_atrium_finance.sh").read_text(encoding="utf-8")
    check("launcher pins the beta database", "data/beta/atrium.sqlite" in text and "uncommissioned" not in text)
    check("launcher does not import owner json", "owner_pool.json" not in text)


def test_bind() -> None:
    listing = subprocess.check_output(["ifconfig"], text=True, stderr=subprocess.DEVNULL)
    lans = []
    for line in listing.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "inet" and not parts[1].startswith("127."):
            lans.append(parts[1])
    check("a non-loopback address exists", bool(lans), " ".join(lans))
    refused = True
    for lan in lans:
        sock = socket.socket()
        sock.settimeout(1.5)
        try:
            sock.connect((lan, 8790))
            refused = False
        except OSError:
            pass
        finally:
            sock.close()
    check("sidecar refuses every non-loopback address", refused and bool(lans), " ".join(lans))
    try:
        listen = subprocess.check_output(["lsof", "-nP", "-iTCP:8790", "-sTCP:LISTEN"], text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as exc:
        listen = exc.output or ""
    check("sidecar listens on 127.0.0.1:8790", "127.0.0.1:8790" in listen and "*:8790" not in listen, listen.strip())


def test_sidecar_gate() -> None:
    secret = mount.load_assertion_secret()
    status, _ = sidecar_call("GET", "/amg/finance/api/journals", None)
    check("sidecar unsigned api is 403", status == 403, str(status))
    status, _ = sidecar_call("GET", "/amg/finance/api/journals", "v1.forged.sig")
    check("sidecar forged assertion is 403", status == 403, str(status))
    # ATRIUM-SOD-1B: Zayen live seat is Financial Controller (not Officer).
    token = mount.sign_assertion(
        secret, "GET", "/amg/finance/api/auth/me", "PERS-ZAYEN", ZAYEN, mount.FINANCE_ROLE_CONTROLLER
    )
    status, raw = sidecar_call(
        "GET",
        "/amg/finance/api/auth/me",
        token,
        {"X-User-Name": "Financial Controller", "X-Wolf-Person": "usr-controller-1"},
    )
    body = json.loads(raw.decode() or b"{}")
    check(
        "sidecar ignores a client identity header",
        status == 200 and (body.get("user") or {}).get("id") == "PERS-ZAYEN",
        f"status={status} id={(body.get('user') or {}).get('id')}",
    )
    for path in PAGES:
        if path == "/amg/finance":
            continue
        token = mount.sign_assertion(
            secret, "GET", path, "PERS-ZAYEN", ZAYEN, mount.FINANCE_ROLE_CONTROLLER
        )
        status, raw = sidecar_call("GET", path, token)
        check(f"sidecar zayen 200 {path}", status == 200 and b"18000000" not in raw and b"TEST CORE" not in raw, str(status))
    for method, path in DENIED:
        token = mount.sign_assertion(
            secret, method, path, "PERS-ZAYEN", ZAYEN, mount.FINANCE_ROLE_CONTROLLER
        )
        status, _ = sidecar_call(method, path, token)
        check(f"sidecar zayen 403 {method} {path}", status == 403, str(status))
    method, path = DENIED_OFFICER_APPROVE
    # Preparer seat assertion (Officer / AP) must not approve — use AP person.
    token = mount.sign_assertion(
        secret, method, path, "PERS-ZENITALFATHAN", "zenitalfathan@gmail.com", mount.FINANCE_ROLE_AP
    )
    status, _ = sidecar_call(method, path, token)
    check("sidecar AP still 403 approve", status == 403, str(status))
    method_p, path_p = DENIED_OFFICER_POST
    token = mount.sign_assertion(
        secret, method_p, path_p, "PERS-ZENITALFATHAN", "zenitalfathan@gmail.com", mount.FINANCE_ROLE_AP
    )
    status, _ = sidecar_call(method_p, path_p, token)
    check("sidecar AP still 403 post", status == 403, str(status))
    token_fc = mount.sign_assertion(
        secret, method, path, "PERS-ZAYEN", ZAYEN, mount.FINANCE_ROLE_CONTROLLER
    )
    status_fc, raw_fc = sidecar_call(method, path, token_fc)
    # Missing journal → 400; SoD/forbidden would be 403. Not a mount soft-block.
    check(
        "sidecar FC approve not mount-blocked",
        status_fc in {200, 400, 404},
        f"status={status_fc} body={raw_fc[:120]!r}",
    )
    token_fc_post = mount.sign_assertion(
        secret, method_p, path_p, "PERS-ZAYEN", ZAYEN, mount.FINANCE_ROLE_CONTROLLER
    )
    status_fc_post, raw_fc_post = sidecar_call(method_p, path_p, token_fc_post)
    check(
        "sidecar FC post not mount-blocked",
        status_fc_post in {200, 400, 404},
        f"status={status_fc_post} body={raw_fc_post[:120]!r}",
    )
    owner = mount.sign_assertion(
        secret, "GET", "/amg/finance/api/auth/me", "PERS-MATT", OWNER, mount.OWNER_ROLE
    )
    status, raw = sidecar_call("GET", "/amg/finance/api/auth/me", owner)
    body = json.loads(raw.decode() or b"{}")
    check(
        "owner maps to the read role",
        status == 200 and (body.get("user") or {}).get("roleId") == "role-general-manager-owner",
        str((body.get("user") or {}).get("roleId")),
    )


def test_beta(port: int) -> None:
    for path in ("/amg/finance", "/amg/finance/api/journals", "/amg/finance/api/admin/settings", "/amg/finance/lite"):
        status, _ = call(port, "GET", path, {"Accept": "application/json"})
        check(f"unsigned 403 {path}", status == 403, str(status))
    for path in PAGES:
        accept = "text/html" if path == "/amg/finance" else "application/json"
        status, raw = call(port, "GET", path, {"X-Wolf-Subject": ZAYEN, "Accept": accept})
        check(f"beta zayen 200 {path}", status == 200 and b"Atrium Finance" in raw or (path != "/amg/finance" and status == 200), f"status={status}")
        if path == "/amg/finance":
            check("beta page is the product shell", b"<title>Atrium Finance</title>" in raw, raw[:180].decode("utf-8", "replace"))
    for method, path in DENIED:
        headers = {"X-Wolf-Subject": ZAYEN, "Accept": "application/json", "Content-Type": "application/json"}
        body = b"{}" if method == "POST" else None
        status, _ = call(port, method, path, headers, body)
        check(f"beta zayen 403 {method} {path}", status == 403, str(status))
    # HUMFIX-1 / ATRIUM-SOD-1: FC approve+post allowed through Beta (SoD enforced). Missing JRN-1 → not 403 mount block.
    status, raw = call(
        port,
        "POST",
        "/amg/finance/api/journals/JRN-1/approve",
        {"X-Wolf-Subject": ZAYEN, "Accept": "application/json", "Content-Type": "application/json"},
        b"{}",
    )
    check(
        "beta FC approve not soft-blocked",
        status in {200, 400, 404},
        f"status={status} body={raw[:120]!r}",
    )
    status, raw = call(
        port,
        "POST",
        "/amg/finance/api/journals/JRN-1/post",
        {"X-Wolf-Subject": ZAYEN, "Accept": "application/json", "Content-Type": "application/json"},
        b"{}",
    )
    check(
        "beta FC post not soft-blocked",
        status in {200, 400, 404},
        f"status={status} body={raw[:120]!r}",
    )
    status, raw = call(
        port,
        "GET",
        "/amg/finance/api/auth/me",
        {
            "X-Wolf-Subject": ZAYEN,
            "X-Wolf-Assertion": "v1.forged.sig",
            "X-User-Name": "Financial Controller",
            "X-Wolf-Person": "usr-controller-1",
            "Accept": "application/json",
        },
    )
    body = json.loads(raw.decode() or b"{}")
    check(
        "beta strips a forged identity header",
        status == 200 and (body.get("user") or {}).get("id") == "PERS-ZAYEN",
        f"status={status} body={raw[:180]!r}",
    )
    for path in ("/ggv/finance", "/bzg/uma-blu", "/api/ggv/finance/pay"):
        status, _ = call(port, "GET" if path != "/api/ggv/finance/pay" else "POST", path, {"X-Wolf-Subject": ZAYEN, "Accept": "application/json"}, b"{}" if path.endswith("/pay") else None)
        check(f"zayen still 403 {path}", status == 403, str(status))
    status, raw = call(port, "GET", "/amg/finance/lite", {"X-Wolf-Subject": ZAYEN, "Accept": "text/html"})
    text = raw.decode("utf-8", "replace")
    check("lite desk stays available", status == 200 and "Atrium Finance" in text and 'href="/amg/finance/lite"' in text, f"status={status}")


def _ws_connect(host: str, port: int, path: str) -> socket.socket:
    sock = socket.create_connection((host, port), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall(
        (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode()
    )
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
    return sock


def _ws_send(sock: socket.socket, text: str) -> None:
    data = text.encode()
    mask = os.urandom(4)
    length = len(data)
    header = bytearray([0x81])
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack(">H", length))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack(">Q", length))
    header.extend(mask)
    masked = bytes(byte ^ mask[i % 4] for i, byte in enumerate(data))
    sock.sendall(bytes(header) + masked)


def _ws_recv(sock: socket.socket) -> str:
    def read(n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("socket closed")
            buf += chunk
        return buf

    while True:
        head = read(2)
        opcode = head[0] & 0x0F
        length = head[1] & 0x7F
        if length == 126:
            length = struct.unpack(">H", read(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", read(8))[0]
        if head[1] & 0x80:
            mask = read(4)
            payload = bytes(byte ^ mask[i % 4] for i, byte in enumerate(read(length)))
        else:
            payload = read(length)
        fin = head[0] & 0x80
        if opcode == 8:
            raise ConnectionError("websocket closed")
        if opcode == 9:
            continue
        if opcode in (0, 1, 2):
            parts = [payload]
            while not fin:
                head = read(2)
                fin = head[0] & 0x80
                length = head[1] & 0x7F
                if length == 126:
                    length = struct.unpack(">H", read(2))[0]
                elif length == 127:
                    length = struct.unpack(">Q", read(8))[0]
                if head[1] & 0x80:
                    mask = read(4)
                    payload = bytes(byte ^ mask[i % 4] for i, byte in enumerate(read(length)))
                else:
                    payload = read(length)
                parts.append(payload)
            if opcode == 2:
                continue
            return b"".join(parts).decode()


def _capture(proxy_port: int, path: str, width: int, height: int, dest: Path, marker: str) -> str:
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
            sock.settimeout(60)
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

            cdp("Page.enable")
            cdp(
                "Emulation.setDeviceMetricsOverride",
                {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": width < 500},
            )
            cdp("Page.navigate", {"url": f"http://127.0.0.1:{proxy_port}{path}"})
            expression = "document.body ? document.body.innerText : ''"
            text = ""
            deadline = time.time() + 60
            while time.time() < deadline:
                got = cdp("Runtime.evaluate", {"expression": expression, "returnByValue": True})
                text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")
                if marker in text and "Checking session" not in text and "Initializing Atrium Finance ledger" not in text:
                    break
                time.sleep(0.4)
            cdp("Page.stopLoading")
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            sock.close()
            return text
        finally:
            proc.kill()
            proc.wait(timeout=5)


def test_shots(beta_port: int) -> None:
    if not CHROME.is_file():
        check("chrome for screenshots", False, "Chrome missing")
        return

    class _Proxy(BaseHTTPRequestHandler):
        def log_message(self, *_args):  # noqa: ANN002
            return

        def _forward(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None
            headers = {"X-Wolf-Subject": ZAYEN, "Accept": self.headers.get("Accept") or "*/*"}
            if self.headers.get("Content-Type"):
                headers["Content-Type"] = self.headers.get("Content-Type")
            req = Request(
                f"http://127.0.0.1:{beta_port}{self.path}",
                data=body,
                headers=headers,
                method=self.command,
            )
            try:
                with urlopen(req, timeout=120) as resp:
                    payload = resp.read()
                    code = resp.status
                    ctype = resp.headers.get("Content-Type") or "application/octet-stream"
            except HTTPError as exc:
                payload = exc.read()
                code = exc.code
                ctype = exc.headers.get("Content-Type") if exc.headers else "text/plain"
            except (URLError, TimeoutError, ConnectionError):
                payload = b"sidecar"
                code = 502
                ctype = "text/plain"
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):  # noqa: N802
            self._forward()

        def do_POST(self):  # noqa: N802
            self._forward()

        def do_PUT(self):  # noqa: N802
            self._forward()

        def do_PATCH(self):  # noqa: N802
            self._forward()

        def do_DELETE(self):  # noqa: N802
            self._forward()

    proxy = ThreadingHTTPServer(("127.0.0.1", 0), _Proxy)
    pport = proxy.server_address[1]
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    try:
        for name, path, marker in SHOT_VIEWS:
            for label, width, height in (("desktop", 1440, 900), ("phone", 390, 844)):
                dest = SHOTS / f"atrium-full-{name}-{label}.png"
                text = _capture(pport, path, width, height, dest, marker)
                check(
                    f"shot {name} {label}",
                    dest.is_file() and dest.stat().st_size > 8000 and marker in text and "18000000" not in text,
                    f"size={dest.stat().st_size if dest.is_file() else 0} marker={marker in text}",
                )
    finally:
        proxy.shutdown()
        proxy.server_close()


def main() -> None:
    import serve_beta as sb

    test_data()
    test_bind()
    test_sidecar_gate()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sb.BetaHandler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        test_beta(port)
        test_shots(port)
    finally:
        httpd.shutdown()
        httpd.server_close()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
