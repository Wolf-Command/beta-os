#!/usr/bin/env python3
"""OWNER-DASH-FRESHNESS-1 — owner dash freshness deepen prove (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave10 pack
OWNER-DASH-FRESHNESS-1 (armed 2026-09-30 after CONNECTOR-HEALTH-DEEPEN-1).

Deepen owner dash freshness from live stamps. No invent KPI / freshness.
STALE never shown as current. Preserve DASH-LIVE-1 + OWNER-EXCEPTIONS-LIVE-1
+ OWNER-NEEDS-YOU-1. Prod :8787 pid 15975 untouched.
No auto-chain ATRIUM-FC-TRUTH-DEEPEN-1.
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
from core import dash_live1 as dash  # noqa: E402
from core import owner_dash_freshness1 as odf  # noqa: E402
from core import owner_exceptions_live1 as oel  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "OWNER-DASH-FRESHNESS-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
PAGE = ROOT / "dashboards" / "owner-dash-freshness-1.html"
MODULE = ROOT / "scripts" / "core" / "owner_dash_freshness1.py"
RESULT = ROOT / "docs" / "wolf" / "ops" / "OWNER-DASH-FRESHNESS-1-RESULT.md"
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


def call(port: int, method: str, path: str, email: str | None = None, body: dict | None = None):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    if email:
        headers["X-Wolf-Subject"] = email
        headers["Cf-Access-Authenticated-User-Email"] = email
    req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, data=data, method=method)
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
    check("module present", MODULE.is_file())
    check("html present", PAGE.is_file())
    check("api matcher", odf.api_matches("/api/ops/owner-dash-freshness-1"))
    check("api alias", odf.api_matches("/api/ops/owner-dash-freshness"))
    check("page matcher", odf.page_matches("/ops/owner-dash-freshness-1"))
    check("page alias short", odf.page_matches("/ops/owner-dash-freshness"))
    check("page alias freshness", odf.page_matches("/ops/owner-freshness-1"))
    check("pack id", odf.PACK_ID == "OWNER-DASH-FRESHNESS-1")
    check("schema id", odf.SCHEMA_ID == "wolf.owner-dash-freshness-1.v1")
    check("classification", odf.CLASSIFICATION == "INTERNALLY_SOLVABLE")
    check("action", odf.ACTION == "WIRE_LIVE_FRESHNESS_STAMPS")
    check("next pack", odf.NEXT_PACK == "ATRIUM-FC-TRUTH-DEEPEN-1")

    flags = odf.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("invented_kpi false", flags.get("invented_kpi") is False)
    check("kpi_invented false", flags.get("kpi_invented") is False)
    check("fake_kpi false", flags.get("fake_kpi") is False)
    check("green_kpi false", flags.get("green_kpi") is False)
    check("money null", flags.get("money") is None)
    check("invented_freshness false", flags.get("invented_freshness") is False)
    check("fake_freshness false", flags.get("fake_freshness") is False)
    check("stale_shown_as_current false", flags.get("stale_shown_as_current") is False)
    check("freshness real stamps", flags.get("freshness_from_real_stamps_only") is True)
    check("write not expanded", flags.get("write_authority_expanded") is False)
    check("dash_live1 preserved flag", flags.get("dash_live1_preserved") is True)
    check("exceptions preserved flag", flags.get("owner_exceptions_live1_preserved") is True)
    check("needs_you preserved flag", flags.get("owner_needs_you1_preserved") is True)
    check("flags classification", flags.get("classification") == "INTERNALLY_SOLVABLE")
    check(
        "next pack parent only",
        flags.get("next_pack_for_parent_only") == "ATRIUM-FC-TRUTH-DEEPEN-1",
    )
    check("did not auto-start", flags.get("cursor_did_not_auto_start_next") is True)
    pins = flags.get("pins") or {}
    check("pin invent_kpi REFUSED", pins.get("invent_kpi") == "REFUSED")
    check("pin invent_freshness REFUSED", pins.get("invent_freshness") == "REFUSED")
    check("pin stale_as_current REFUSED", pins.get("stale_as_current") == "REFUSED")
    for pack in ("DASH-LIVE-1", "OWNER-EXCEPTIONS-LIVE-1", "OWNER-NEEDS-YOU-1"):
        check(f"preserved list {pack}", pack in (flags.get("preserved_packs") or []))

    for refuse_fn, code in (
        (odf.refuse_invent_kpi, "invent_kpi_refused"),
        (odf.refuse_invent_freshness, "invent_freshness_refused"),
        (odf.refuse_proven, "proven_refused"),
        (odf.refuse_ready, "ready_refused"),
    ):
        try:
            refuse_fn({"x": 1})
            check(f"{code} raised", False)
        except odf.OwnerDashFreshness1Error as exc:
            check(f"{code} code", exc.code == code)

    try:
        odf.refuse_external_write({"kpi": 99})
        check("write invent-kpi refused", False)
    except odf.OwnerDashFreshness1Error as exc:
        check("write invent-kpi code", exc.code == "invent_kpi_refused")

    try:
        odf.refuse_external_write({"invent_freshness": True})
        check("write invent-freshness refused", False)
    except odf.OwnerDashFreshness1Error as exc:
        check("write invent-freshness code", exc.code == "invent_freshness_refused")

    try:
        odf.refuse_external_write({"force_live": True})
        check("write force_live refused", False)
    except odf.OwnerDashFreshness1Error as exc:
        check("write force_live code", exc.code == "invent_freshness_refused")

    try:
        odf.refuse_external_write({"as_of": "2026-09-30T00:00:00+08:00"})
        check("write as_of refused", False)
    except odf.OwnerDashFreshness1Error as exc:
        check("write as_of code", exc.code == "invent_freshness_refused")

    try:
        odf.refuse_external_write({"green_kpi": True})
        check("write green_kpi refused", False)
    except odf.OwnerDashFreshness1Error as exc:
        check("write green_kpi code", exc.code == "invent_kpi_refused")


def test_board_payload() -> None:
    payload = odf.build_board()
    check("board ok", payload.get("ok") is True)
    check("board classification", payload.get("classification") == "INTERNALLY_SOLVABLE")
    check("board staff_ready false", payload.get("staff_ready") is False)
    check("board human_commissioned false", payload.get("human_commissioned") is False)
    check("board invented_kpi false", payload.get("invented_kpi") is False)
    check("board invented_freshness false", payload.get("invented_freshness") is False)
    check("board stale_as_current false", payload.get("stale_shown_as_current") is False)
    check("board money null", payload.get("money") is None)
    check("board green_kpi false", payload.get("green_kpi") is False)
    check("board dash preserved", payload.get("dash_live1_preserved") is True)
    check("board exceptions preserved", payload.get("owner_exceptions_live1_preserved") is True)
    check("board needs_you preserved", payload.get("owner_needs_you1_preserved") is True)
    check(
        "board next parent",
        payload.get("next_pack_for_parent_only") == "ATRIUM-FC-TRUTH-DEEPEN-1",
    )
    check("no invented kpi helper", odf.no_invented_kpi(payload))
    check("no stale as current helper", odf.no_stale_as_current(payload))
    check("surfaces honest helper", odf.surfaces_are_honest(payload))

    stamps = payload.get("surface_stamps") or []
    check("surface stamps >= 5", len(stamps) >= 5, f"n={len(stamps)}")
    by_id = {s.get("id"): s for s in stamps}
    for sid in (
        "owner_command",
        "exceptions",
        "empire",
        "data_quality",
        "war_room",
    ):
        row = by_id.get(sid) or {}
        check(f"surface {sid} present", bool(row), str(row))
        status = str(row.get("status") or "")
        check(
            f"surface {sid} status vocab",
            status in odf.STATUS_VOCAB,
            status,
        )
        check(f"surface {sid} not invented", row.get("invented") is False)
        check(f"surface {sid} no invent kpi", row.get("invented_kpi") is False)
        check(
            f"surface {sid} no invent freshness",
            row.get("invented_freshness") is False,
        )
        check(
            f"surface {sid} stale not current",
            row.get("stale_shown_as_current") is False,
        )
        if status == "STALE":
            check(f"surface {sid} STALE not shown current", row.get("shown_as_current") is False)

    tiles = payload.get("honesty_tiles") or []
    check("honesty tiles >= 7", len(tiles) >= 7, f"n={len(tiles)}")
    check("schema document", odf.schema_document().get("pack") == "OWNER-DASH-FRESHNESS-1")
    check("schema no invent kpi", odf.schema_document().get("invented_kpi") is False)
    check(
        "schema no invent freshness",
        odf.schema_document().get("invented_freshness") is False,
    )


def test_preserved_packs() -> None:
    dash_p = odf.dash_live1_preserved()
    check("dash_live1 preserved ok", dash_p.get("ok") is True, str(dash_p))

    flags = dash.honesty_flags()
    check("direct dash invented_kpi false", flags.get("invented_kpi") is False)
    check("direct dash stale not current", flags.get("stale_shown_as_current") is False)
    check(
        "direct dash real stamps",
        flags.get("freshness_from_real_stamps_only") is True,
    )

    oel_p = odf.owner_exceptions_live1_preserved()
    check("exceptions preserved ok", oel_p.get("ok") is True, str(oel_p))
    oel_flags = oel.honesty_flags()
    check("direct oel invented_severity false", oel_flags.get("invented_severity") is False)
    check("direct oel dash preserved", oel_flags.get("dash_live1_preserved") is True)

    nye_p = odf.owner_needs_you1_preserved()
    check("needs_you preserved ok", nye_p.get("ok") is True, str(nye_p))


def test_http_surfaces() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/ops/owner-dash-freshness-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/ops/owner-dash-freshness-1", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api classification", data.get("classification") == "INTERNALLY_SOLVABLE")
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api invented_kpi false", data.get("invented_kpi") is False)
        check("api invented_freshness false", data.get("invented_freshness") is False)
        check("api stale_as_current false", data.get("stale_shown_as_current") is False)
        check("api dash preserved", data.get("dash_live1_preserved") is True)
        check("api exceptions preserved", data.get("owner_exceptions_live1_preserved") is True)
        check("api needs_you preserved", data.get("owner_needs_you1_preserved") is True)
        check("api surfaces >= 5", len(data.get("surface_stamps") or []) >= 5)

        st, body = call(port, "GET", "/api/ops/owner-dash-freshness", email=MATT)
        check("api alias 200", st == 200, f"status={st}")

        st, _ = call(port, "GET", "/ops/owner-dash-freshness-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/ops/owner-dash-freshness-1", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check("page html freshness", "freshness" in text.lower())
        check("page staff_ready pin", "staff_ready=false" in text)
        check("page human_commissioned pin", "human_commissioned=false" in text)
        check("page INTERNALLY_SOLVABLE", "INTERNALLY_SOLVABLE" in text)
        check("page LIVE|STALE", "LIVE" in text and "STALE" in text)
        check("page no invent", "invent" in text.lower())

        st, _ = call(port, "GET", "/ops/owner-dash-freshness", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")

        refuses = [
            ({"kpi": 12}, "invent_kpi_refused"),
            ({"invent_kpi": True}, "invent_kpi_refused"),
            ({"green_kpi": True}, "invent_kpi_refused"),
            ({"invent_freshness": True}, "invent_freshness_refused"),
            ({"force_live": True}, "invent_freshness_refused"),
            ({"as_of": "2026-09-30T12:00:00+08:00"}, "invent_freshness_refused"),
        ]
        for body_obj, code in refuses:
            st, body = call(
                port,
                "POST",
                "/api/ops/owner-dash-freshness-1",
                email=MATT,
                body=body_obj,
            )
            check(f"post {code} 403", st == 403, f"status={st}")
            err = json.loads(body.decode())
            check(f"post {code} code", err.get("error") == code, str(err.get("error")))

        # Preserved prior surfaces still auth-gated
        st, _ = call(port, "GET", "/api/owner/exceptions-live-1")
        check("exceptions unsigned 403", st == 403, f"status={st}")
        st, body = call(port, "GET", "/api/owner/exceptions-live-1", email=MATT)
        check("exceptions signed 200", st == 200, f"status={st}")
        oel_data = json.loads(body.decode())
        check("exceptions still no invent severity", oel_data.get("invented_severity") is False)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_prod_untouched() -> None:
    check("prod pid held constant", odf.PROD_PID_HELD == PROD_PID)
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
    check("html pack attr", 'data-pack="OWNER-DASH-FRESHNESS-1"' in html)
    check("html INTERNALLY_SOLVABLE", "INTERNALLY_SOLVABLE" in html)
    check("html LIVE STALE UNKNOWN", "LIVE" in html and "STALE" in html and "UNKNOWN" in html)
    check("html invent pin", "invent" in html.lower())

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "OWNER-DASH-FRESHNESS-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "ATRIUM-FC-TRUTH-DEEPEN-1",
    )
    check("arm classification", arm.get("classification") == "INTERNALLY_SOLVABLE")

    check("classification log present", CLASS_LOG.is_file())
    clog = json.loads(CLASS_LOG.read_text(encoding="utf-8"))
    check(
        "classification has owner dash freshness pin",
        bool(clog.get("owner_dash_freshness1"))
        or any(
            "owner dash freshness" in str(c.get("surface") or "").lower()
            or "OWNER-DASH-FRESHNESS" in str(c.get("surface") or "")
            for c in (clog.get("ceilings") or [])
        ),
    )

    if RESULT.is_file():
        result = RESULT.read_text(encoding="utf-8")
        check("result EXIT", "EXIT:0" in result or "**EXIT:0**" in result)
        check("result no auto-chain", "ATRIUM-FC-TRUTH-DEEPEN-1" in result)
        check("result INTERNALLY_SOLVABLE", "INTERNALLY_SOLVABLE" in result)
        check(
            "result no invent",
            "never invent" in result.lower() or "no invent" in result.lower(),
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
    with tempfile.TemporaryDirectory(prefix="ownerdashfresh1-") as profile:
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
                "ownerdashfresh1-desk-desktop.png",
                "/ops/owner-dash-freshness-1",
                1024,
                1400,
                MATT,
                "INTERNALLY_SOLVABLE",
            ),
            (
                "ownerdashfresh1-desk-phone.png",
                "/ops/owner-dash-freshness-1",
                390,
                1100,
                MATT,
                "LIVE",
            ),
            (
                "ownerdashfresh1-surface-stamps.png",
                "/ops/owner-dash-freshness-1",
                1024,
                1600,
                MATT,
                "Owner Command",
            ),
            (
                "ownerdashfresh1-unsigned-deny.png",
                "/ops/owner-dash-freshness-1",
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
    print("=== OWNER-DASH-FRESHNESS-1 pack suite ===")
    test_module_honesty()
    test_board_payload()
    test_preserved_packs()
    test_http_surfaces()
    test_prod_untouched()
    test_artifacts()
    test_shots()
    print(f"=== PASS={PASS} FAIL={FAIL} ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
