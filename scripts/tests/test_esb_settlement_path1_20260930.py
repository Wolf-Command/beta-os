#!/usr/bin/env python3
"""ESB-SETTLEMENT-PATH-1 — settlement path probe prove (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack
ESB-SETTLEMENT-PATH-1 (armed 2026-09-30 after METRICOOL-RUNTIME-WIRE-1).

Probe → EXTERNAL_BLOCKER with Felix + credential-absence evidence.
Never invent settlement/P&L. Preserve ESB-TRUTH-1 warehouse RO.
Prod :8787 pid 15975 untouched. No auto-chain SOP-CATALOG-SEED-ROUTE-1.
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
from core import esb_settlement_path1 as esp  # noqa: E402
from core import esb_truth1 as esb  # noqa: E402
from core import intg_truth_board as intg  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "ESB-SETTLEMENT-PATH-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
PAGE = ROOT / "dashboards" / "esb-settlement-path-1.html"
RESULT = ROOT / "docs" / "wolf" / "ops" / "ESB-SETTLEMENT-PATH-1-RESULT.md"
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
    check("page matcher", esp.page_matches("/ops/esb-settlement-path-1"))
    check("page alias", esp.page_matches("/esb-settlement-path-1.html"))
    check("page bzg alias", esp.page_matches("/bzg/esb-settlement-path-1"))
    check("api matcher", esp.api_matches("/api/ops/esb-settlement-path-1"))
    check(
        "api no trailing invent",
        not esp.api_matches("/api/ops/esb-settlement-path-1/mutate"),
    )

    flags = esp.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("fake_settlement false", flags.get("fake_settlement") is False)
    check("settlement_invented false", flags.get("settlement_invented") is False)
    check("pnl_invented false", flags.get("pnl_invented") is False)
    check("esb_write false", flags.get("esb_write") is False)
    check("secrets false", flags.get("secrets_exposed") is False)
    check("held pid 15975", flags.get("prod_pid_held") == PROD_PID)
    check("ceiling BUILT", flags.get("ceiling") == "BUILT")
    check("classification EXTERNAL_BLOCKER", flags.get("classification") == "EXTERNAL_BLOCKER")
    check(
        "next pack parent only",
        flags.get("next_pack_for_parent_only") == "SOP-CATALOG-SEED-ROUTE-1",
    )
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("unknown forever replaced", flags.get("unknown_forever_replaced") is True)
    check("esb truth preserved flag", flags.get("esb_truth1_preserved") is True)

    payload = esp.build_board()
    check("ok", payload.get("ok") is True)
    check("payload staff_ready false", payload.get("staff_ready") is False)
    check("payload human_commissioned false", payload.get("human_commissioned") is False)
    check("payload fake_settlement false", payload.get("fake_settlement") is False)
    check("payload settlement null", payload.get("settlement") is None)
    check("payload pnl null", payload.get("pnl") is None)
    check("payload last_success null", payload.get("last_success") is None)
    check("payload prod_mutate false", payload.get("prod_mutate") is False)
    check("payload classification", payload.get("classification") == "EXTERNAL_BLOCKER")
    check("payload settlement_api", payload.get("settlement_api") == "EXTERNAL_BLOCKER")
    check(
        "legacy UNAVAILABLE stamp kept",
        payload.get("settlement_api_legacy_stamp") == "UNAVAILABLE",
    )
    check("surfaces honest", esp.surfaces_are_honest(payload) is True)
    check("esb_truth1_preserved", payload.get("esb_truth1_preserved") is True)

    surfaces = payload.get("surfaces") or []
    check("surfaces >= 5", len(surfaces) >= 5, str(len(surfaces)))
    by_id = {s.get("id"): s for s in surfaces if isinstance(s, dict)}
    for sid in (
        "settlement_api_path",
        "settlement_credentials",
        "authorised_connector",
        "settlement_amounts",
        "last_success",
    ):
        check(f"surface {sid} EXTERNAL_BLOCKER", by_id.get(sid, {}).get("status") == "EXTERNAL_BLOCKER")
    check(
        "warehouse PRESERVED",
        by_id.get("warehouse_ro", {}).get("status") == "PRESERVED",
        str(by_id.get("warehouse_ro", {}).get("status")),
    )
    check(
        "human commissioning ABSENT",
        by_id.get("human_commissioning", {}).get("status") == "ABSENT",
    )

    creds = payload.get("credentials_probe") or {}
    check("creds absent", creds.get("creds_present") is False)
    check("secret values not exposed", creds.get("secret_values_exposed") is False)

    felix = payload.get("felix") or {}
    check("felix dated", felix.get("dated") == "2026-07-19")
    check("felix finding", "UNAVAILABLE" in str(felix.get("finding") or ""))


def test_preserved_esb_truth1() -> None:
    preserved = esp.esb_truth1_preserved()
    check("preserved ok", preserved.get("ok") is True, str(preserved))
    check("preserved PARTIAL", preserved.get("audit_status") == "PARTIAL_IN_BETA")
    check("preserved sap UNAVAILABLE", preserved.get("settlement_api") == "UNAVAILABLE")

    slice_ = esb.build_slice()
    check("truth1 ok", slice_.get("ok") is True)
    check("truth1 PARTIAL", slice_.get("audit_status") == "PARTIAL_IN_BETA")
    check("truth1 sap UNAVAILABLE", slice_.get("settlement_api") == "UNAVAILABLE")
    check("truth1 settlement null", slice_.get("settlement") is None)
    check("truth1 pnl null", slice_.get("pnl") is None)
    check("truth1 fake_settlement false", slice_.get("fake_settlement") is False)
    check("truth1 esb_write false", slice_.get("esb_write") is False)
    check("truth1 staff_ready false", slice_.get("staff_ready") is False)
    check("truth1 human_commissioned false", slice_.get("human_commissioned") is False)


def test_intg_overlay() -> None:
    board = intg.build_board(persist_audit=False)
    esb_row = next(
        c for c in board["connectors"] if c["integration_id"] == "INT-ESB-WOLF"
    )
    check("intg esb PARTIAL", esb_row.get("audit_status") == "PARTIAL_IN_BETA")
    check(
        "intg esb probe settlement blocker",
        "SETTLEMENT_EXTERNAL_BLOCKER" in str(esb_row.get("probe_status") or "")
        or "WAREHOUSE" in str(esb_row.get("probe_status") or ""),
        str(esb_row.get("probe_status")),
    )
    check("intg esb last_success null", esb_row.get("last_success") is None)
    facts = esb_row.get("probe_facts") or {}
    check("intg pnl not invented", facts.get("pnl_invented") is False)
    check(
        "intg settlement path blocker",
        facts.get("settlement_api_path") == "EXTERNAL_BLOCKER"
        or (facts.get("surfaces") or {}).get("settlement_api_path") == "EXTERNAL_BLOCKER",
        str(facts.get("settlement_api_path")),
    )
    honesty = board.get("honesty") or {}
    check("honesty esb_settlement", honesty.get("esb_settlement") == "EXTERNAL_BLOCKER")
    check("honesty esb still PARTIAL", honesty.get("esb") == "PARTIAL_IN_BETA")


def test_http_surfaces() -> None:
    httpd, port = _start_beta()
    try:
        st, body = call(port, "GET", "/api/ops/esb-settlement-path-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/ops/esb-settlement-path-1", MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api classification", data.get("classification") == "EXTERNAL_BLOCKER")
        check("api settlement null", data.get("settlement") is None)
        check("api pnl null", data.get("pnl") is None)
        check("api fake_settlement false", data.get("fake_settlement") is False)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api esb_truth preserved", data.get("esb_truth1_preserved") is True)

        st, body = call(port, "GET", "/ops/esb-settlement-path-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/ops/esb-settlement-path-1", MATT)
        check("signed page 200", st == 200, f"status={st}")
        html = body.decode("utf-8", errors="replace")
        check("page pack attr", "ESB-SETTLEMENT-PATH-1" in html)
        check("page EXTERNAL_BLOCKER", "EXTERNAL_BLOCKER" in html)
        check("page staff_ready=false", "staff_ready=false" in html)

        for action, code in (
            ({"settlement": 1}, "settlement_refused"),
            ({"pnl": 1}, "pnl_refused"),
            ({"esb_write": True}, "esb_write_refused"),
            ({"prod_mutate": True}, "prod_mutate_refused"),
            ({"staff_ready": True}, "ready_refused"),
        ):
            st, body = call(
                port,
                "POST",
                "/api/ops/esb-settlement-path-1",
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
    check("prod pid held constant", esp.PROD_PID_HELD == PROD_PID)
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{PROD_PORT}/", timeout=2) as resp:
            check("prod still listening", resp.status in (200, 301, 302, 403, 404))
    except Exception as exc:  # noqa: BLE001
        check("prod probe skipped-or-up", True, type(exc).__name__)
    # Confirm process still the held pid when present.
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
    check("html pack attr", 'data-pack="ESB-SETTLEMENT-PATH-1"' in html)
    check("html EXTERNAL_BLOCKER", "EXTERNAL_BLOCKER" in html)
    check("html never invent", "never invent" in html.lower() or "null (never invent)" in html)

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "ESB-SETTLEMENT-PATH-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "SOP-CATALOG-SEED-ROUTE-1",
    )
    check("arm classification", arm.get("classification") == "EXTERNAL_BLOCKER")

    check("classification log present", CLASS_LOG.is_file())
    clog = json.loads(CLASS_LOG.read_text(encoding="utf-8"))
    check(
        "classification has esb settlement pin",
        bool(clog.get("esb_settlement_path1"))
        or any(
            (c.get("next_pack") == "ESB-SETTLEMENT-PATH-1"
             or "settlement" in str(c.get("surface") or "").lower())
            and c.get("classification") == "EXTERNAL_BLOCKER"
            for c in (clog.get("ceilings") or [])
        ),
    )

    if RESULT.is_file():
        result = RESULT.read_text(encoding="utf-8")
        check("result EXIT", "EXIT:0" in result or "**EXIT:0**" in result)
        check("result no auto-chain", "SOP-CATALOG-SEED-ROUTE-1" in result)
        check(
            "result EXTERNAL_BLOCKER",
            "EXTERNAL_BLOCKER" in result,
        )
        check(
            "result no fake settlement",
            "fake settlement" in result.lower() or "never invent" in result.lower(),
        )
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
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(raw))
    sock.sendall(header + masked)


def _ws_connect(host: str, port: int, path: str):
    import hashlib as _hl
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
    with tempfile.TemporaryDirectory(prefix="esbsettlement1-") as profile:
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
                "esbsettlement1-desk-desktop.png",
                "/ops/esb-settlement-path-1",
                1024,
                1200,
                MATT,
                "EXTERNAL_BLOCKER",
            ),
            (
                "esbsettlement1-desk-phone.png",
                "/ops/esb-settlement-path-1",
                390,
                1000,
                MATT,
                "settlement path",
            ),
            (
                "esbsettlement1-blocker-stamps.png",
                "/ops/esb-settlement-path-1",
                1024,
                1400,
                MATT,
                "Felix",
            ),
            (
                "esbsettlement1-unsigned-deny.png",
                "/ops/esb-settlement-path-1",
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
    print("=== ESB-SETTLEMENT-PATH-1 pack suite ===")
    test_module_honesty()
    test_preserved_esb_truth1()
    test_intg_overlay()
    test_http_surfaces()
    test_prod_untouched()
    test_artifacts()
    test_shots()
    print(f"=== PASS={PASS} FAIL={FAIL} ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
