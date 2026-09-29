#!/usr/bin/env python3
"""INTG-TRUTH-1 — Integration honesty board prove (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack INTG-TRUTH-1
(armed 2026-09-30) — MB-015 / INT-* SPECIFIED honesty.

No invented last_success. No fake connector success. Yanolja BLOCKED_EXTERNAL.
ESB PARTIAL_IN_BETA warehouse facts only. Metricool AGENT_HOST_ONLY / NOT_RUNTIME.
Unsigned API 403. Prod :8787 pid 15975 untouched. Never flips commissioning flags.
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
from core import intg_truth_board as board  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
CSV = ROOT / "docs" / "canon" / "build-dashboard" / "Integrations.csv"
AUDIT = ROOT / "state" / "final-completion" / "PHASE3-INTEGRATIONS-AUDIT.json"
ARM = ROOT / "state" / "final-completion" / "packs" / "INTG-TRUTH-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
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


def test_registry_honesty() -> None:
    check("csv present", CSV.is_file())
    check("audit present", AUDIT.is_file())
    payload = board.build_board(persist_audit=False)
    check("ok", payload.get("ok") is True)
    check("staff_ready false", payload.get("staff_ready") is False)
    check("human_commissioned false", payload.get("human_commissioned") is False)
    check("secrets_exposed false", payload.get("secrets_exposed") is False)
    check("write not expanded", payload.get("write_authority_expanded") is False)
    check("no invented last_success flag", payload.get("invented_last_success") is False)
    check("no fake feeds flag", payload.get("fake_live_feeds") is False)

    connectors = payload.get("connectors") or []
    check("connectors >= 5 csv", len(connectors) >= 5, str(len(connectors)))
    ids = {c.get("integration_id") for c in connectors}
    for needed in (
        "INT-YAN-WOLF",
        "INT-ESB-WOLF",
        "INT-GWS-WOLF",
        "INT-BANK-WOLF",
        "INT-MET-WOLF",
        "MCP-Metricool",
    ):
        check(f"has {needed}", needed in ids)

    for c in connectors:
        check(
            f"write NONE {c.get('integration_id')}",
            c.get("write_authority") == "NONE_EXPANDED",
        )
        check(
            f"secrets false {c.get('integration_id')}",
            c.get("secrets_exposed") is False,
        )
        check(
            f"last_success null-or-real {c.get('integration_id')}",
            c.get("last_success") is None or bool(c.get("last_success")),
            str(c.get("last_success")),
        )
        # Never invent a success timestamp string for unknown connectors
        if c.get("integration_id") in (
            "INT-YAN-WOLF",
            "INT-ESB-WOLF",
            "INT-BANK-WOLF",
            "INT-MET-WOLF",
            "INT-GWS-WOLF",
            "MCP-Metricool",
        ):
            check(
                f"last_success null {c.get('integration_id')}",
                c.get("last_success") is None,
            )

    yan = next(c for c in connectors if c["integration_id"] == "INT-YAN-WOLF")
    check("yanolja BLOCKED_EXTERNAL", yan.get("audit_status") == "BLOCKED_EXTERNAL")
    check("yanolja blocked flag", yan.get("blocked_external") is True)
    check("yanolja probe blocker", yan.get("probe_status") == "DOCUMENTED_BLOCKER")
    check("helper yanolja_blocked", board.yanolja_blocked(connectors) is True)

    esb = next(c for c in connectors if c["integration_id"] == "INT-ESB-WOLF")
    check("esb PARTIAL_IN_BETA", esb.get("audit_status") == "PARTIAL_IN_BETA")
    check("esb last_success null", esb.get("last_success") is None)
    check(
        "esb probe warehouse",
        "WAREHOUSE" in str(esb.get("probe_status") or ""),
        str(esb.get("probe_status")),
    )
    facts = esb.get("probe_facts") or {}
    check("esb pnl not invented", facts.get("pnl_invented") is False)

    bank = next(c for c in connectors if c["integration_id"] == "INT-BANK-WOLF")
    check("bank FILE_IMPORT_ONLY", bank.get("probe_status") == "FILE_IMPORT_ONLY")

    met = next(c for c in connectors if c["integration_id"] == "INT-MET-WOLF")
    check(
        "metricool wolf NOT_RUNTIME or STATUS_",
        str(met.get("probe_status") or "").startswith("NOT_RUNTIME")
        or str(met.get("probe_status") or "").startswith("STATUS_"),
        str(met.get("probe_status")),
    )

    mcp = next(c for c in connectors if c["integration_id"] == "MCP-Metricool")
    check("mcp metricool AGENT_HOST_ONLY", mcp.get("audit_status") == "AGENT_HOST_ONLY")


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        status, body = call(port, "GET", "/api/ops/integrations-status", MATT)
        check("api 200", status == 200, str(status))
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api secrets false", data.get("secrets_exposed") is False)
        connectors = data.get("connectors") or []
        check("api connectors >= 5", len(connectors) >= 5, str(len(connectors)))
        yan = next((c for c in connectors if c.get("integration_id") == "INT-YAN-WOLF"), None)
        check("api yanolja present", yan is not None)
        if yan:
            check("api yanolja blocked", yan.get("audit_status") == "BLOCKED_EXTERNAL")
            check("api yanolja last_success null", yan.get("last_success") is None)

        status, body = call(port, "GET", "/api/ops/integrations-status")
        check("unsigned api 403", status == 403, str(status))

        status, body = call(port, "GET", "/ops/integrations-status", MATT)
        check("page 200", status == 200, str(status))
        text = body.decode("utf-8", errors="replace")
        check("page title", "Integrations Status" in text)
        check("page honesty staff_ready", "staff_ready=false" in text)
        check("page honesty human_commissioned", "human_commissioned=false" in text)

        status, _ = call(port, "GET", "/ops/integrations-status")
        check("unsigned page 403", status == 403, str(status))
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
            " const yan=document.querySelector('tr[data-id=\"INT-YAN-WOLF\"]');"
            " const blocked=yan && yan.getAttribute('data-blocked')==='1';"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && blocked && t.includes('INT-YAN-WOLF')"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false'),"
            " text:t.slice(0,500), honesty:ht, blocked:!!blocked,"
            " hasBlockedLabel: t.includes('BLOCKED_EXTERNAL')};"
            "})()"
        )
        for width, name in (
            (1024, "intgtruth1-board-desktop.png"),
            (390, "intgtruth1-board-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/ops/integrations-status", board_expr
            ):
                check(f"board ready {name}", bool(value and value.get("ok")), str(value)[:220])
                if value:
                    check(f"yanolja blocked visible {name}", value.get("blocked") is True)
                    check(
                        f"BLOCKED_EXTERNAL text {name}",
                        value.get("hasBlockedLabel") is True,
                        str(value.get("text"))[:160],
                    )
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        # Dedicated Yanolja blocked row crop-equivalent full page shot
        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/ops/integrations-status",
            board_expr,
        ):
            check("yanolja row shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "intgtruth1-yanolja-blocked.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot yanolja-blocked", dest.is_file() and dest.stat().st_size > 3000)

        # Unsigned deny — page should fail closed (403 body or deny UI)
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
            f"http://127.0.0.1:{port}/ops/integrations-status",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "intgtruth1-unsigned-deny.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot unsigned-deny", dest.is_file() and dest.stat().st_size > 800)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_persist_audit_and_arm() -> None:
    # Persist board statuses into PHASE3 audit (still read-only posture).
    payload = board.build_board(persist_audit=True)
    check("persist ok", payload.get("ok") is True)
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    check("audit staff_ready false", audit.get("staff_ready") is False)
    check("audit human_commissioned false", audit.get("human_commissioned") is False)
    check("audit secrets false", audit.get("secrets_exposed") is False)
    check("audit write not expanded", audit.get("write_authority_expanded") is False)
    check(
        "audit status BOARD_SYNCED",
        audit.get("status") == "BOARD_SYNCED_READ_ONLY",
        str(audit.get("status")),
    )
    yan = next(
        (c for c in audit.get("connectors") or [] if c.get("integration_id") == "INT-YAN-WOLF"),
        None,
    )
    check("audit yanolja blocked", yan is not None and yan.get("audit_status") == "BLOCKED_EXTERNAL")
    if yan:
        check("audit yanolja last_success null", yan.get("last_success") is None)

    if ARM.is_file():
        arm = json.loads(ARM.read_text(encoding="utf-8"))
        check("arm staff_ready false", arm.get("staff_ready") is False)
        check("arm human_commissioned false", arm.get("human_commissioned") is False)
        check("arm no_push", arm.get("no_push") is True)
        check("arm prod_mutate false", arm.get("prod_mutate") is False)


def test_prod_pid_untouched() -> None:
    out = subprocess.check_output(
        ["lsof", "-nP", f"-iTCP:{PROD_PORT}", "-sTCP:LISTEN"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    check("prod pid still 15975", str(PROD_PID) in out and f":{PROD_PORT}" in out, out[:200])


def main() -> int:
    test_registry_honesty()
    test_http_api_and_page()
    test_shots()
    test_persist_audit_and_arm()
    test_prod_pid_untouched()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("RESULT: PASS" if FAIL == 0 else f"RESULT: FAIL {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
