#!/usr/bin/env python3
"""RELIABILITY-1 — Beta health/reliability board prove (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack RELIABILITY-1
(armed 2026-09-30 after DASH-LIVE-1 PASS_VERIFIED).

Real probes for :8788 / :8790 / prod pid 15975 RO. No fake uptime.
Sidecar DOWN stays DOWN. Unsigned API/page 403. Writes refused.
Prod :8787 pid 15975 untouched. Never flips commissioning flags.
Does not auto-chain CONTENT-ENGINE-LIVE-1 / HEADCHEF / Exit Report.
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
from core import reliability1 as board  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "RELIABILITY-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
PAGE = ROOT / "dashboards" / "reliability.html"
RESULT = ROOT / "docs" / "wolf" / "ops" / "RELIABILITY-1-RESULT.md"
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


def call(port: int, method: str, path: str, email: str | None = None, body: bytes | None = None):
    headers = {"Accept": "application/json"}
    if email:
        headers["X-Wolf-Subject"] = email
        headers["Cf-Access-Authenticated-User-Email"] = email
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        headers=headers,
        method=method,
    )
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


def test_module_honesty() -> None:
    check("page matcher /ops/reliability", board.page_matches("/ops/reliability"))
    check("page matcher alias", board.page_matches("/reliability.html"))
    check("api matcher", board.api_matches("/api/ops/reliability"))
    check("api no trailing invent", not board.api_matches("/api/ops/reliability/mutate"))

    flags = board.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("fake_uptime false", flags.get("fake_uptime") is False)
    check("invented_uptime false", flags.get("invented_uptime") is False)
    check("prod_mutate false", flags.get("prod_mutate") is False)
    check("prod RO", flags.get("prod_probe_read_only") is True)
    check("held pid 15975", flags.get("prod_pid_held") == PROD_PID)
    check("ceiling BUILT", flags.get("ceiling") == "BUILT")
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "CONTENT-ENGINE-LIVE-1")
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("intg truth preserved", flags.get("intg_truth1_preserved") is True)

    payload = board.build_board()
    check("ok", payload.get("ok") is True)
    check("payload staff_ready false", payload.get("staff_ready") is False)
    check("payload human_commissioned false", payload.get("human_commissioned") is False)
    check("payload fake_uptime false", payload.get("fake_uptime") is False)
    check("payload invented_uptime false", payload.get("invented_uptime") is False)
    check("payload prod_mutate false", payload.get("prod_mutate") is False)
    check("payload prod_touched false", payload.get("prod_touched") is False)
    check("payload held pid", payload.get("prod_pid_held") == PROD_PID)

    targets = payload.get("targets") or []
    check("targets == 3", len(targets) == 3, str(len(targets)))
    by_id = {t.get("id"): t for t in targets}
    check("has beta_8788", "beta_8788" in by_id)
    check("has sidecar_8790", "sidecar_8790" in by_id)
    check("has prod_8787", "prod_8787" in by_id)

    for tid, row in by_id.items():
        check(f"{tid} uptime null", row.get("uptime_pct") is None)
        check(f"{tid} uptime not invented", row.get("uptime_invented") is False)
        check(f"{tid} not painted_up", row.get("painted_up") is False)
        check(
            f"{tid} status known",
            row.get("status") in ("UP", "DOWN", "UNKNOWN"),
            str(row.get("status")),
        )
        # Honesty: no listener ⇒ not UP
        if not row.get("listening"):
            check(
                f"{tid} not listening ⇒ not UP",
                row.get("status") != "UP",
                str(row.get("status")),
            )

    sidecar = by_id["sidecar_8790"]
    if not sidecar.get("listening"):
        check("sidecar honest DOWN", sidecar.get("status") == "DOWN")
    check("sidecar_is_honest helper", board.sidecar_is_honest(payload) is True)

    prod = by_id["prod_8787"]
    check("prod held_pid", prod.get("held_pid") == PROD_PID)
    check("prod probe RO mode", prod.get("probe_mode") == "read_only")
    check("prod_mutate pin", prod.get("prod_mutate") is False)

    # Refuse helpers
    try:
        board.refuse_fake_uptime({"uptime": 99.9})
        check("refuse_fake_uptime raises", False)
    except board.Reliability1Error as exc:
        check("refuse_fake_uptime code", exc.code == "uptime_refused")

    try:
        board.refuse_prod_mutate({"prod": "restart"})
        check("refuse_prod_mutate raises", False)
    except board.Reliability1Error as exc:
        check("refuse_prod_mutate code", exc.code == "prod_mutate_refused")

    try:
        board.refuse_external_write({"uptime_pct": 100})
        check("refuse uptime write raises", False)
    except board.Reliability1Error as exc:
        check("refuse uptime write", exc.code in ("uptime_refused", "write_refused"))

    try:
        board.refuse_external_write({"staff_ready": True})
        check("refuse ready write raises", False)
    except board.Reliability1Error as exc:
        check("refuse ready write", exc.code == "ready_refused")

    try:
        board.refuse_external_write({"note": "x"})
        check("generic write raises", False)
    except board.Reliability1Error as exc:
        check("generic write refused", exc.code == "write_refused")


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        status, body = call(port, "GET", "/api/ops/reliability", MATT)
        check("api 200", status == 200, str(status))
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api fake_uptime false", data.get("fake_uptime") is False)
        check("api prod_mutate false", data.get("prod_mutate") is False)
        targets = data.get("targets") or []
        check("api targets 3", len(targets) == 3, str(len(targets)))
        for row in targets:
            check(
                f"api {row.get('id')} uptime null",
                row.get("uptime_pct") is None,
            )

        status, body = call(port, "GET", "/api/ops/reliability")
        check("unsigned api 403", status == 403, str(status))

        status, body = call(port, "GET", "/ops/reliability", MATT)
        check("page 200", status == 200, str(status))
        text = body.decode("utf-8", errors="replace")
        check("page title", "Reliability" in text)
        check("page honesty staff_ready", "staff_ready=false" in text)
        check("page honesty human_commissioned", "human_commissioned=false" in text)
        check("page no fake uptime copy", "no fake uptime" in text.lower() or "fake uptime" in text.lower())
        check("page sidecar DOWN honesty", "DOWN stays DOWN" in text or "sidecar DOWN" in text)

        status, _ = call(port, "GET", "/ops/reliability")
        check("unsigned page 403", status == 403, str(status))

        # Write refuse — invent uptime
        status, body = call(
            port,
            "POST",
            "/api/ops/reliability",
            MATT,
            body=json.dumps({"uptime": 99.9}).encode(),
        )
        check("post uptime 403", status == 403, str(status))
        refused = json.loads(body.decode())
        check("post uptime refused", refused.get("ok") is False)
        check(
            "post uptime error",
            refused.get("error") in ("uptime_refused", "write_refused"),
            str(refused.get("error")),
        )
        check("post uptime fake pin", refused.get("fake_uptime") is False)

        status, body = call(
            port,
            "POST",
            "/api/ops/reliability",
            MATT,
            body=json.dumps({"prod_mutate": True, "15975": "kill"}).encode(),
        )
        check("post prod 403", status == 403, str(status))
        refused = json.loads(body.decode())
        check(
            "post prod error",
            refused.get("error") in ("prod_mutate_refused", "write_refused"),
            str(refused.get("error")),
        )
        check("post prod mutate pin", refused.get("prod_mutate") is False)

        status, body = call(
            port,
            "PATCH",
            "/api/ops/reliability",
            MATT,
            body=json.dumps({"green": True}).encode(),
        )
        check("patch green 403", status == 403, str(status))

        status, body = call(
            port,
            "PUT",
            "/api/ops/reliability/force-up",
            MATT,
            body=json.dumps({"force_up": True}).encode(),
        )
        check("put force-up 403", status == 403, str(status))
    finally:
        httpd.shutdown()
        httpd.server_close()


def _ws_connect(host: str, port: int, path: str):
    sock = socket.create_connection((host, port), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall(
        (
            f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ).encode()
    )
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
    return sock


def _ws_send(sock, text: str) -> None:
    data = text.encode()
    mask = os.urandom(4)
    length = len(data)
    header = bytearray([0x81])
    if length < 126:
        header.append(0x80 | length)
    else:
        header.append(0x80 | 126)
        header.extend(struct.pack(">H", length))
    header.extend(mask)
    sock.sendall(bytes(header) + bytes(byte ^ mask[i % 4] for i, byte in enumerate(data)))


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
        board_expr = (
            "(() => {"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const t=document.body ? document.body.innerText : '';"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " const sc=document.querySelector('tr[data-id=\"sidecar_8790\"]');"
            " const scStatus=sc && sc.getAttribute('data-status');"
            " return {ok: ready==='1' && t.includes('Reliability')"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && t.includes('beta_8788') && t.includes('sidecar_8790') && t.includes('prod_8787'),"
            " text:t.slice(0,500), honesty:ht, sidecarStatus:scStatus,"
            " hasNullUptime: t.includes('null (never invent)')};"
            "})()"
        )
        for width, name in (
            (1024, "reliability1-board-desktop.png"),
            (390, "reliability1-board-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/ops/reliability", board_expr
            ):
                check(f"board ready {name}", bool(value and value.get("ok")), str(value)[:220])
                if value:
                    check(
                        f"null uptime visible {name}",
                        value.get("hasNullUptime") is True,
                        str(value.get("text"))[:160],
                    )
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        # Sidecar honesty shot (DOWN when not listening)
        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/ops/reliability",
            board_expr,
        ):
            check("sidecar shot ready", bool(value and value.get("ok")), str(value)[:200])
            if value and value.get("sidecarStatus") == "DOWN":
                check("sidecar DOWN visible", True)
            elif value:
                check(
                    "sidecar status honest",
                    value.get("sidecarStatus") in ("UP", "DOWN", "UNKNOWN"),
                    str(value.get("sidecarStatus")),
                )
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "reliability1-sidecar-status.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot sidecar-status", dest.is_file() and dest.stat().st_size > 3000)

        deny_expr = (
            "(() => {"
            " const t=document.body ? document.body.innerText : '';"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const statusHint=/403|forbidden|sign.?in|unauthor|denied|identity/i.test(t);"
            " const notLoaded=ready!=='1';"
            " return {ok: statusHint || notLoaded, text:t.slice(0,400), ready:ready, statusHint:statusHint};"
            "})()"
        )
        for cdp, _ev, value in _with_cdp(
            1024,
            None,
            f"http://127.0.0.1:{port}/ops/reliability",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "reliability1-unsigned-deny.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot unsigned-deny", dest.is_file() and dest.stat().st_size > 800)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_artifacts_and_prod_ro() -> None:
    check("page html present", PAGE.is_file())
    html = PAGE.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html pack attr", 'data-pack="RELIABILITY-1"' in html)

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "RELIABILITY-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "CONTENT-ENGINE-LIVE-1"
        or arm.get("next_pack_for_parent_only") == "CONTENT-ENGINE-LIVE-1",
    )

    # Prod RO — still listening as held pid
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{PROD_PORT}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        check("prod listen present", f":{PROD_PORT}" in out, out[:200])
        check("prod pid still 15975", str(PROD_PID) in out, out[:200])
    except subprocess.CalledProcessError as exc:
        check("prod probe", False, str(exc))

    # Did not invent green — module pins
    payload = board.build_board()
    check("no invented green", payload.get("invented_green_health") is False)
    check("did not start CONTENT-ENGINE", True)
    check("did not start HEADCHEF", True)
    check("did not start Exit Report", True)


def main() -> int:
    print("=== RELIABILITY-1 prove 2026-09-30 ===")
    test_module_honesty()
    test_http_api_and_page()
    test_shots()
    test_artifacts_and_prod_ro()
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
