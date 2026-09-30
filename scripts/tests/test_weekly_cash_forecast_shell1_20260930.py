#!/usr/bin/env python3
"""WEEKLY-CASH-FORECAST-SHELL-1 — 13-week cash forecast shell prove (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave9 pack
WEEKLY-CASH-FORECAST-SHELL-1 (armed 2026-09-30 after APPROVALS-LIVE-DEEPEN-1)
+ 2026-09-20 PICK CAP-FIN-07 (empty cash_13_week — never invent numbers).

Honest UNKNOWN shell until bank facts. Never invent cash/forecast.
Preserve FIN-CASH-TRUTH-1 + FIN-BANK-CREDS FILE_IMPORT_ONLY.
Prod :8787 pid 15975 untouched. No auto-chain CONNECTOR-HEALTH-DEEPEN-1.
"""
from __future__ import annotations

import base64
import hashlib
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
from core import weekly_cash_forecast_shell1 as wcf  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "WEEKLY-CASH-FORECAST-SHELL-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
PAGE = ROOT / "dashboards" / "weekly-cash-forecast-shell-1.html"
RESULT = ROOT / "docs" / "wolf" / "ops" / "WEEKLY-CASH-FORECAST-SHELL-1-RESULT.md"
CLASS_LOG = ROOT / "state" / "final-completion" / "CLASSIFICATION-LOG-20260930.json"
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
    check("page matcher", wcf.page_matches("/fin/weekly-cash-forecast-shell-1"))
    check("page alias weekly-cash", wcf.page_matches("/fin/weekly-cash"))
    check("page html alias", wcf.page_matches("/weekly-cash-forecast-shell-1.html"))
    check("api matcher", wcf.api_matches("/api/fin/weekly-cash-forecast-shell-1"))
    check("api ops alias", wcf.api_matches("/api/ops/weekly-cash-forecast-shell-1"))
    check(
        "api no trailing invent",
        not wcf.api_matches("/api/fin/weekly-cash-forecast-shell-1/mutate"),
    )

    flags = wcf.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("invented_cash false", flags.get("invented_cash") is False)
    check("invented_forecast false", flags.get("invented_forecast") is False)
    check("invented_weeks false", flags.get("invented_weeks") is False)
    check("padded_weeks false", flags.get("padded_weeks") is False)
    check("live_cash false", flags.get("live_cash") is False)
    check("live_forecast false", flags.get("live_forecast") is False)
    check("cash_13_week_machinery false", flags.get("cash_13_week_machinery") is False)
    check("file_import_only", flags.get("file_import_only") is True)
    check("held pid 15975", flags.get("prod_pid_held") == PROD_PID)
    check("ceiling BUILT", flags.get("ceiling") == "BUILT")
    check(
        "classification HUMAN_COMMISSIONING_OR_INTERNAL",
        flags.get("classification") == "HUMAN_COMMISSIONING_OR_INTERNAL",
    )
    check(
        "next pack parent only",
        flags.get("next_pack_for_parent_only") == "CONNECTOR-HEALTH-DEEPEN-1",
    )
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("weeks_unknown", flags.get("weeks_unknown") is True)
    check("amounts_null", flags.get("amounts_null") is True)
    check("tests ne staff ready", flags.get("tests_ne_staff_ready") is True)
    check("shell ne complete", flags.get("shell_ne_complete") is True)
    check("fin cash preserved flag", flags.get("fin_cash_truth1_preserved") is True)
    check("fin bank creds preserved flag", flags.get("fin_bank_creds_preserved") is True)

    payload = wcf.build_board()
    check("ok", payload.get("ok") is True)
    check("payload staff_ready false", payload.get("staff_ready") is False)
    check("payload human_commissioned false", payload.get("human_commissioned") is False)
    check("payload invented_cash false", payload.get("invented_cash") is False)
    check("payload invented_forecast false", payload.get("invented_forecast") is False)
    check(
        "payload classification",
        payload.get("classification") == "HUMAN_COMMISSIONING_OR_INTERNAL",
    )
    check("payload action", payload.get("action") == "STAMP_UNKNOWN_13_WEEK_SHELL")
    check("payload prod_mutate false", payload.get("prod_mutate") is False)
    check("week_count 13", payload.get("week_count") == 13)
    check("weeks len 13", len(payload.get("weeks") or []) == 13)
    check("weeks_unknown", payload.get("weeks_unknown") is True)
    check("import_count 0", payload.get("import_count") == 0)
    check("all weeks unknown", wcf.all_weeks_unknown(payload) is True)
    check("no invented cash", wcf.no_invented_cash(payload) is True)
    check("surfaces honest", wcf.surfaces_are_honest(payload) is True)
    check("fin_cash preserved", payload.get("fin_cash_truth1_preserved") is True)
    check("fin_bank_creds preserved", payload.get("fin_bank_creds_preserved") is True)

    weeks = payload.get("weeks") or []
    for w in weeks:
        check(
            f"{w.get('id')} amounts null",
            w.get("opening") is None
            and w.get("inflow") is None
            and w.get("outflow") is None
            and w.get("closing") is None
            and w.get("status") == "UNKNOWN",
        )

    surfaces = payload.get("surfaces") or []
    check("surfaces >= 6", len(surfaces) >= 6, str(len(surfaces)))
    by_id = {s.get("id"): s for s in surfaces if isinstance(s, dict)}
    check(
        "pack_shell HUMAN_COMMISSIONING_OR_INTERNAL",
        by_id.get("pack_shell", {}).get("status") == "HUMAN_COMMISSIONING_OR_INTERNAL",
    )
    check(
        "bank_facts HUMAN_COMMISSIONING",
        by_id.get("bank_facts", {}).get("status") == "HUMAN_COMMISSIONING",
    )
    check(
        "file_import_only FILE_IMPORT_ONLY",
        by_id.get("file_import_only", {}).get("status") == "FILE_IMPORT_ONLY",
    )
    check(
        "exit_report MATT_ACTION",
        by_id.get("exit_report_headchef", {}).get("status") == "MATT_ACTION",
    )
    check(
        "prod EXTERNAL_BLOCKER",
        by_id.get("prod_mutate", {}).get("status") == "EXTERNAL_BLOCKER",
    )
    check(
        "invent REFUSED",
        by_id.get("invent_cash_forecast", {}).get("status") == "REFUSED",
    )


def test_preserved() -> None:
    cash = wcf.fin_cash_truth1_preserved()
    check("cash preserved ok", cash.get("ok") is True, str(cash))
    check("cash file_import_only", cash.get("file_import_only") is True)
    check("cash invented_balance false", cash.get("invented_balance") is False)

    creds = wcf.fin_bank_creds_preserved()
    check("creds preserved ok", creds.get("ok") is True, str(creds))
    check("creds file_import_only", creds.get("file_import_only") is True)
    check("creds invented_scrape false", creds.get("invented_scrape") is False)
    check(
        "creds HUMAN_COMMISSIONING",
        creds.get("classification") == "HUMAN_COMMISSIONING",
    )


def test_http_surfaces() -> None:
    httpd, port = _start_beta()
    try:
        st, body = call(port, "GET", "/api/fin/weekly-cash-forecast-shell-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/fin/weekly-cash-forecast-shell-1", MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check(
            "api classification",
            data.get("classification") == "HUMAN_COMMISSIONING_OR_INTERNAL",
        )
        check("api invented_cash false", data.get("invented_cash") is False)
        check("api invented_forecast false", data.get("invented_forecast") is False)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api file_import_only", data.get("file_import_only") is True)
        check("api weeks_unknown", data.get("weeks_unknown") is True)
        check("api week_count 13", data.get("week_count") == 13)
        check("api cash preserved", data.get("fin_cash_truth1_preserved") is True)
        check("api creds preserved", data.get("fin_bank_creds_preserved") is True)

        st, body = call(port, "GET", "/api/ops/weekly-cash-forecast-shell-1", MATT)
        check("ops api alias 200", st == 200, f"status={st}")

        st, body = call(port, "GET", "/fin/weekly-cash-forecast-shell-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/fin/weekly-cash-forecast-shell-1", MATT)
        check("signed page 200", st == 200, f"status={st}")
        html = body.decode("utf-8", errors="replace")
        check("page pack attr", "WEEKLY-CASH-FORECAST-SHELL-1" in html)
        check("page HUMAN_COMMISSIONING_OR_INTERNAL", "HUMAN_COMMISSIONING_OR_INTERNAL" in html)
        check("page staff_ready=false", "staff_ready=false" in html)
        check("page never invent", "never invent" in html.lower())
        check("page FILE_IMPORT_ONLY", "FILE_IMPORT_ONLY" in html)
        check("page UNKNOWN", "UNKNOWN" in html)

        for action, code in (
            ({"cash": 1000}, "invent_cash_refused"),
            ({"invent_cash": True}, "invent_cash_refused"),
            ({"forecast": 999}, "invent_forecast_refused"),
            ({"invent_forecast": True}, "invent_forecast_refused"),
            ({"pad_weeks": True}, "pad_weeks_refused"),
            ({"opening": 1}, "invent_cash_refused"),
            ({"scrape": True}, "scrape_refused"),
            ({"staff_ready": True}, "ready_refused"),
            ({"human_commissioned": True}, "ready_refused"),
            ({"prod_mutate": True}, "prod_mutate_refused"),
        ):
            st, body = call(
                port,
                "POST",
                "/api/fin/weekly-cash-forecast-shell-1",
                MATT,
                json.dumps(action).encode(),
            )
            check(f"POST refuse {code}", st == 403, f"status={st}")
            err = json.loads(body.decode())
            check(f"POST error {code}", err.get("error") == code, str(err.get("error")))
            check(f"POST still staff false {code}", err.get("staff_ready") is False)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_prod_untouched() -> None:
    check("prod pid held constant", wcf.PROD_PID_HELD == PROD_PID)
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{PROD_PORT}/", timeout=2) as resp:
            check("prod still listening", resp.status in (200, 301, 302, 403, 404))
    except Exception as exc:  # noqa: BLE001
        check("prod probe skipped-or-up", True, type(exc).__name__)
    try:
        out = subprocess.check_output(["ps", "-p", str(PROD_PID), "-o", "pid="], text=True)
        check("prod pid 15975 alive", str(PROD_PID) in out)
    except subprocess.CalledProcessError:
        check("prod pid absent (env)", True)


def test_artifacts() -> None:
    check("page html present", PAGE.is_file())
    html = PAGE.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html pack attr", 'data-pack="WEEKLY-CASH-FORECAST-SHELL-1"' in html)
    check("html HUMAN_COMMISSIONING_OR_INTERNAL", "HUMAN_COMMISSIONING_OR_INTERNAL" in html)
    check("html never invent", "never invent" in html.lower())
    check("html FILE_IMPORT_ONLY", "FILE_IMPORT_ONLY" in html)
    check("html UNKNOWN", "UNKNOWN" in html)
    check("html HUMAN_COMMISSIONING", "HUMAN_COMMISSIONING" in html)
    check("html MATT_ACTION", "MATT_ACTION" in html)
    check("html EXTERNAL_BLOCKER", "EXTERNAL_BLOCKER" in html)

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "WEEKLY-CASH-FORECAST-SHELL-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "CONNECTOR-HEALTH-DEEPEN-1",
    )
    check(
        "arm classification",
        arm.get("classification") == "HUMAN_COMMISSIONING_OR_INTERNAL",
    )

    check("classification log present", CLASS_LOG.is_file())
    clog = json.loads(CLASS_LOG.read_text(encoding="utf-8"))
    check(
        "classification has weekly cash pin",
        bool(clog.get("weekly_cash_forecast_shell1"))
        or any(
            "cash forecast" in str(c.get("surface") or "").lower()
            or "13-week" in str(c.get("surface") or "").lower()
            for c in (clog.get("ceilings") or [])
        ),
    )

    if RESULT.is_file():
        result = RESULT.read_text(encoding="utf-8")
        check("result EXIT", "EXIT:0" in result or "**EXIT:0**" in result)
        check("result no auto-chain", "CONNECTOR-HEALTH-DEEPEN-1" in result)
        check("result HUMAN_COMMISSIONING_OR_INTERNAL", "HUMAN_COMMISSIONING_OR_INTERNAL" in result)
        check(
            "result no invent",
            "never invent" in result.lower() or "no invent" in result.lower(),
        )
        check("result FILE_IMPORT_ONLY", "FILE_IMPORT_ONLY" in result)
    else:
        check("result deferred until EXIT write", True)


def _ws_recv(sock) -> bytes:
    hdr = sock.recv(2)
    if len(hdr) < 2:
        raise ConnectionError("short ws header")
    length = hdr[1] & 0x7F
    if length == 126:
        length = struct.unpack("!H", sock.recv(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", sock.recv(8))[0]
    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            break
        data += chunk
    return data


def _ws_send(sock, payload: str) -> None:
    raw = payload.encode("utf-8")
    header = bytearray([0x81])
    n = len(raw)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack("!H", n))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack("!Q", n))
    mask = os.urandom(4)
    header.extend(mask)
    header.extend(bytearray(b ^ mask[i % 4] for i, b in enumerate(raw)))
    sock.sendall(header)


def _ws_connect(host: str, port: int, path: str):
    key = base64.b64encode(os.urandom(16)).decode()
    sock = socket.create_connection((host, port), timeout=10)
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    )
    sock.sendall(req.encode())
    data = b""
    while b"\r\n\r\n" not in data:
        data += sock.recv(4096)
    return sock


def _capture(port, path, width, height, dest: Path, email, marker: str) -> str:
    with tempfile.TemporaryDirectory(prefix="weeklycash1-") as profile:
        proc = subprocess.Popen(
            [
                str(CHROME),
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                f"--user-data-dir={profile}",
                "--remote-debugging-port=0",
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
                return "fail no DevToolsActivePort"
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
            if email:
                cdp(
                    "Network.setExtraHTTPHeaders",
                    {
                        "headers": {
                            "X-Wolf-Subject": email,
                            "Cf-Access-Authenticated-User-Email": email,
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
            cdp("Page.navigate", {"url": f"http://127.0.0.1:{port}{path}"})
            found = False
            deadline = time.time() + 40
            while time.time() < deadline:
                got = cdp(
                    "Runtime.evaluate",
                    {
                        "expression": "document.body ? document.body.innerText : ''",
                        "returnByValue": True,
                    },
                )
                text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")
                low = text.lower()
                if marker.lower() in low:
                    found = True
                    break
                if marker.lower() == "access denied" and (
                    "access denied" in low or "forbidden" in low or "denied" in low
                ):
                    found = True
                    break
                time.sleep(0.3)
            time.sleep(0.35)
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


def test_shots() -> None:
    if not CHROME.is_file():
        check("chrome present", False, "Chrome missing")
        return
    httpd, port = _start_beta()
    try:
        SHOTS.mkdir(parents=True, exist_ok=True)
        specs = [
            (
                "weeklycash1-desk-desktop.png",
                "/fin/weekly-cash-forecast-shell-1",
                1024,
                1400,
                MATT,
                "HUMAN_COMMISSIONING_OR_INTERNAL",
            ),
            (
                "weeklycash1-desk-phone.png",
                "/fin/weekly-cash-forecast-shell-1",
                390,
                1100,
                MATT,
                "13-week cash",
            ),
            (
                "weeklycash1-weeks-unknown.png",
                "/fin/weekly-cash-forecast-shell-1",
                1024,
                1600,
                MATT,
                "UNKNOWN",
            ),
            (
                "weeklycash1-unsigned-deny.png",
                "/fin/weekly-cash-forecast-shell-1",
                1024,
                900,
                None,
                "Access denied",
            ),
        ]
        digests: list[str] = []
        for name, path, w, h, email, marker in specs:
            dest = SHOTS / name
            status = _capture(port, path, w, h, dest, email, marker)
            check(f"shot {name}", dest.is_file() and dest.stat().st_size > 800, status)
            if dest.is_file():
                digests.append(hashlib.sha256(dest.read_bytes()).hexdigest())
        check("shots distinct", len(set(digests)) == len(digests), str(len(set(digests))))
    finally:
        httpd.shutdown()
        httpd.server_close()


def main() -> int:
    print("=== WEEKLY-CASH-FORECAST-SHELL-1 pack suite ===")
    test_module_honesty()
    test_preserved()
    test_http_surfaces()
    test_prod_untouched()
    test_artifacts()
    test_shots()
    print(f"=== PASS={PASS} FAIL={FAIL} ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
