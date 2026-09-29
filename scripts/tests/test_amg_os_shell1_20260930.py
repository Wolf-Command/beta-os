#!/usr/bin/env python3
"""AMG-OS-SHELL-1 — AMG operating shell prove (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack AMG-OS-SHELL-1
(armed 2026-09-30) — CAP-AMG-02 / CAP-AMG-04 / MB-008 structure only.

PMS tiles BLOCKED_EXTERNAL + UNKNOWN display. No fake occupancy/arrivals.
Yanolja stays blocked. CAP-AMG-01 not unblocked. Unsigned API 403.
Prod :8787 pid 15975 untouched. Never flips commissioning flags.
Does not auto-chain GGV-CONTENT-PROVE-1 / HEADCHEF / Exit Report.
"""
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
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["BETA_AUTH_MODE"] = "development_assertion"
os.environ["WOLF_TEST_MODE"] = "1"
sys.path.insert(0, str(ROOT / "scripts"))

import serve_beta as sb  # noqa: E402
from core import amg_os_shell as shell  # noqa: E402
from core import intg_truth_board as board  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "AMG-OS-SHELL-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "amg-os-shell.html"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
PROD_PID = 15975
PROD_PORT = 8787

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def call(port: int, method: str, path: str, email: str | None = None):
    headers = {"Accept": "application/json"}
    if email:
        headers["X-Wolf-Subject"] = email
        headers["Cf-Access-Authenticated-User-Email"] = email
    req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, method=method)
    try:
        with urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _start_beta() -> tuple[ThreadingHTTPServer, int]:
    port = _free_port()

    class H(sb.BetaHandler):
        pass

    H.directory = str(ROOT / "dashboards")
    httpd = ThreadingHTTPServer(("127.0.0.1", port), H)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    time.sleep(0.25)
    return httpd, port


def test_shell_payload() -> None:
    check("html present", HTML.is_file())
    check("api matcher", shell.api_matches("/api/amg/os-shell"))
    check("page matcher", shell.page_matches("/amg/os-shell"))
    check("page matcher alias", shell.page_matches("/amg-os-shell"))
    payload = shell.build_shell()
    check("ok", payload.get("ok") is True)
    check("pack", payload.get("pack") == "AMG-OS-SHELL-1")
    check("staff_ready false", payload.get("staff_ready") is False)
    check("human_commissioned false", payload.get("human_commissioned") is False)
    check("cap_amg_01 not unblocked", payload.get("cap_amg_01_unblocked") is False)
    check("yanolja_live false", payload.get("yanolja_live") is False)
    check("fake_pms false", payload.get("fake_pms_data") is False)
    check("invented_occupancy false", payload.get("invented_occupancy") is False)
    check("invented_arrivals false", payload.get("invented_arrivals") is False)
    check("all pms blocked helper", shell.all_pms_tiles_blocked(payload) is True)

    tiles = payload.get("pms_tiles") or []
    needed = {"arrivals", "departures", "rooms", "guest_requests", "occupancy"}
    got = {t.get("id") for t in tiles}
    check("pms tile set", needed.issubset(got), str(got))
    for t in tiles:
        tid = t.get("id")
        check(f"{tid} BLOCKED_EXTERNAL", t.get("status") == "BLOCKED_EXTERNAL")
        check(f"{tid} display UNKNOWN", t.get("display") == "UNKNOWN")
        check(f"{tid} value null", t.get("value") is None)
        check(f"{tid} count null", t.get("count") is None)
        check(f"{tid} occupancy_pct null", t.get("occupancy_pct") is None)
        check(f"{tid} board link", t.get("honesty_board_href") == "/ops/integrations-status")
        check(f"{tid} not live", t.get("yanolja_live") is False)

    yan = payload.get("yanolja") or {}
    check("yanolja audit blocked", yan.get("audit_status") == "BLOCKED_EXTERNAL")
    check("yanolja last_success null", yan.get("last_success") is None)
    check("yanolja blocked_confirmed", yan.get("blocked_confirmed") is True)

    links = {l.get("id"): l for l in (payload.get("structure_links") or [])}
    for lid in ("my_work", "amg_today", "finance_desk", "integrations_honesty"):
        check(f"structure link {lid}", lid in links, str(list(links)))
    check(
        "honesty board href",
        (links.get("integrations_honesty") or {}).get("href") == "/ops/integrations-status",
    )

    # Align with INTG board
    b = board.build_board(persist_audit=False)
    yan_b = next(c for c in b["connectors"] if c["integration_id"] == "INT-YAN-WOLF")
    check("intg board also blocked", yan_b.get("audit_status") == "BLOCKED_EXTERNAL")

    html = HTML.read_text(encoding="utf-8")
    check("html BLOCKED_EXTERNAL", "BLOCKED_EXTERNAL" in html)
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html honesty board link", "/ops/integrations-status" in html)
    check("html no invented zero occupancy", "occupancy_pct" not in html or "UNKNOWN" in html)


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, body = call(port, "GET", "/api/amg/os-shell")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/amg/os-shell", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api cap_amg_01 false", data.get("cap_amg_01_unblocked") is False)
        check("api fake_pms false", data.get("fake_pms_data") is False)
        check("api all tiles blocked", shell.all_pms_tiles_blocked(data) is True)
        arrivals = next(t for t in data["pms_tiles"] if t["id"] == "arrivals")
        check("api arrivals UNKNOWN", arrivals.get("display") == "UNKNOWN")
        check("api arrivals not zero", arrivals.get("count") is None and arrivals.get("value") is None)

        st, body = call(port, "GET", "/amg/os-shell")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/amg/os-shell", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check("page html shell", "AMG operating shell" in text or "amg-os-shell" in text.lower())
        check("page has BLOCKED", "BLOCKED_EXTERNAL" in text)

        # Alias path
        st, _ = call(port, "GET", "/amg-os-shell", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")
    finally:
        httpd.shutdown()
        httpd.server_close()


def _ws_connect(host: str, port: int, path: str):
    sock = socket.create_connection((host, port), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    sock.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("no upgrade")
        buf += chunk
    return sock


def _ws_send(sock, data: str) -> None:
    payload = data.encode()
    header = bytearray([0x81])
    n = len(payload)
    mask = os.urandom(4)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack(">H", n))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack(">Q", n))
    header.extend(mask)
    sock.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))


def _ws_recv(sock) -> str:
    def read(n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("socket closed")
            buf += chunk
        return buf

    head = read(2)
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
    return payload.decode()


def _with_cdp(width: int, email: str | None, url: str, wait_expr: str, wait_seconds: float = 45.0):
    with tempfile.TemporaryDirectory(dir=str(ROOT / "state")) as profile:
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
                f"--window-size={width},1100",
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

            def evaluate(expression: str):
                got = cdp("Runtime.evaluate", {"expression": expression, "returnByValue": True})
                return ((got.get("result") or {}).get("result") or {}).get("value")

            cdp("Network.enable")
            headers = {}
            if email:
                headers["X-Wolf-Subject"] = email
                headers["Cf-Access-Authenticated-User-Email"] = email
            if headers:
                cdp("Network.setExtraHTTPHeaders", {"headers": headers})
            cdp("Page.enable")
            cdp("Page.navigate", {"url": url})
            value = None
            end = time.time() + wait_seconds
            while time.time() < end:
                value = evaluate(wait_expr)
                if value and value.get("ok"):
                    break
                time.sleep(0.35)
            yield cdp, evaluate, value
        finally:
            proc.kill()
            proc.wait(timeout=5)


def test_shots() -> None:
    if not CHROME.is_file():
        check("chrome present", False, "missing")
        return
    SHOTS.mkdir(parents=True, exist_ok=True)
    httpd, port = _start_beta()
    try:
        shell_expr = (
            "(() => {"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const blocked=document.body && document.body.getAttribute('data-yanolja-blocked');"
            " const fake=document.body && document.body.getAttribute('data-fake-pms');"
            " const t=document.body ? document.body.innerText : '';"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const arrivals=document.querySelector('[data-tile=\"arrivals\"]');"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && blocked==='1' && fake==='0'"
            "  && stamps>=4 && !!arrivals"
            "  && t.includes('BLOCKED_EXTERNAL') && t.includes('UNKNOWN')"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && t.includes('Integrations honesty board'),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, ready:ready, blocked:blocked};"
            "})()"
        )
        for width, name in (
            (1024, "amgoshell1-shell-desktop.png"),
            (390, "amgoshell1-shell-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/amg/os-shell", shell_expr
            ):
                check(f"shell ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"yanolja blocked attr {name}", value.get("blocked") == "1")
                    check(f"stamps visible {name}", (value.get("stamps") or 0) >= 4)
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        # Dedicated blocked stamps close-up (full page with stamps in view)
        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/amg/os-shell",
            shell_expr,
        ):
            check("blocked stamps shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "amgoshell1-yanolja-blocked.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot yanolja-blocked", dest.is_file() and dest.stat().st_size > 3000)

        deny_expr = (
            "(() => {"
            " const t=document.body ? document.body.innerText : '';"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const deny=document.body && document.body.getAttribute('data-deny');"
            " const statusHint=/403|forbidden|sign.?in|unauthor|denied|identity/i.test(t);"
            " const notLoaded=ready!=='1';"
            " return {ok: statusHint || notLoaded || deny==='403',"
            " text:t.slice(0,400), ready:ready, deny:deny, statusHint:statusHint};"
            "})()"
        )
        for cdp, _ev, value in _with_cdp(
            1024,
            None,
            f"http://127.0.0.1:{port}/amg/os-shell",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "amgoshell1-unsigned-deny.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot unsigned-deny", dest.is_file() and dest.stat().st_size > 800)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_arm_flags() -> None:
    if ARM.is_file():
        arm = json.loads(ARM.read_text(encoding="utf-8"))
        check("arm staff_ready false", arm.get("staff_ready") is False)
        check("arm human_commissioned false", arm.get("human_commissioned") is False)
        check("arm no_push", arm.get("no_push") is True)
        check("arm prod_mutate false", arm.get("prod_mutate") is False)
        check(
            "arm does_not_unblock CAP-AMG-01",
            "CAP-AMG-01" in (arm.get("does_not_unblock") or []),
        )
    else:
        check("arm present", False, "missing")


def test_prod_pid_untouched() -> None:
    out = subprocess.check_output(
        ["lsof", "-nP", f"-iTCP:{PROD_PORT}", "-sTCP:LISTEN"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    check("prod pid still 15975", str(PROD_PID) in out and f":{PROD_PORT}" in out, out[:200])


def main() -> int:
    test_shell_payload()
    test_http_api_and_page()
    test_shots()
    test_arm_flags()
    test_prod_pid_untouched()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("RESULT: PASS" if FAIL == 0 else f"RESULT: FAIL {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
