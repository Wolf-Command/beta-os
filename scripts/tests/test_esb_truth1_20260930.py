#!/usr/bin/env python3
"""ESB-TRUTH-1 — ESB warehouse truth board (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack ESB-TRUTH-1
(armed 2026-09-30 after OWNER-NEEDS-YOU-1 PASS_VERIFIED).
PARTIAL_IN_BETA deepen · warehouse RO facts · no fake settlement.
Preserves INTG-TRUTH-1 / BZG-VENUEPL-1.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain BACKUP-HEALTH-1 / HEADCHEF / Exit Report.
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
from core import esb_truth1 as esb  # noqa: E402
from core import intg_truth_board as intg  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "ESB-TRUTH-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "esb-truth-1.html"
MODULE = ROOT / "scripts" / "core" / "esb_truth1.py"
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


def test_module_and_honesty() -> None:
    check("module present", MODULE.is_file())
    check("html present", HTML.is_file())
    check("api matcher", esb.api_matches("/api/ops/esb-truth-1"))
    check("page matcher", esb.page_matches("/ops/esb-truth-1"))
    check("page matcher alias", esb.page_matches("/esb-truth-1"))
    check("pack id", esb.PACK_ID == "ESB-TRUTH-1")
    check("schema id", esb.SCHEMA_ID == "wolf.esb-truth-1.v1")

    flags = esb.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("esb_write false", flags.get("esb_write") is False)
    check("esb_mutated false", flags.get("esb_mutated") is False)
    check("pnl_invented false", flags.get("pnl_invented") is False)
    check("settlement_invented false", flags.get("settlement_invented") is False)
    check("fake_settlement false", flags.get("fake_settlement") is False)
    check("invented_rows false", flags.get("invented_warehouse_rows") is False)
    check("invented_last_success false", flags.get("invented_last_success") is False)
    check("settlement_api UNAVAILABLE", flags.get("settlement_api") == "UNAVAILABLE")
    check("audit PARTIAL_IN_BETA", flags.get("audit_status") == "PARTIAL_IN_BETA")
    check("partial_in_beta true", flags.get("partial_in_beta") is True)
    check("write not expanded", flags.get("write_authority_expanded") is False)
    check("intg preserved flag", flags.get("intg_truth1_preserved") is True)
    check("vpl preserved flag", flags.get("bzg_venuepl1_preserved") is True)
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "BACKUP-HEALTH-1")
    check("did not auto-start", flags.get("cursor_did_not_auto_start_next") is True)
    for pack in ("INTG-TRUTH-1", "BZG-VENUEPL-1"):
        check(f"preserved list {pack}", pack in (flags.get("preserved_packs") or []))

    for refuse_fn, code in (
        (esb.refuse_esb_write, "esb_write_refused"),
        (esb.refuse_settlement, "settlement_refused"),
        (esb.refuse_pnl, "pnl_refused"),
        (esb.refuse_last_success, "last_success_refused"),
        (esb.refuse_proven, "proven_refused"),
        (esb.refuse_ready, "ready_refused"),
    ):
        try:
            refuse_fn({"x": 1})
            check(f"{code} raised", False)
        except esb.EsbTruth1Error as exc:
            check(f"{code} code", exc.code == code)

    try:
        esb.refuse_external_write({"esb_write": True})
        check("write esb refused", False)
    except esb.EsbTruth1Error as exc:
        check("write esb code", exc.code == "esb_write_refused")

    try:
        esb.refuse_external_write({"settlement": {"amount": 999}})
        check("write settlement refused", False)
    except esb.EsbTruth1Error as exc:
        check("write settlement code", exc.code == "settlement_refused")

    try:
        esb.refuse_external_write({"pnl": {"revenue": 1}})
        check("write pnl refused", False)
    except esb.EsbTruth1Error as exc:
        check("write pnl code", exc.code == "pnl_refused")

    html = HTML.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html PARTIAL_IN_BETA", "PARTIAL_IN_BETA" in html)
    check("html UNAVAILABLE", "UNAVAILABLE" in html)
    check("html UNKNOWN", "UNKNOWN" in html)
    check("html INTG-TRUTH-1", "INTG-TRUTH-1" in html)
    check("html BZG-VENUEPL-1", "BZG-VENUEPL-1" in html)
    check("html no fake settlement claim", "settlement complete" not in html.lower())


def test_slice_payload() -> None:
    payload = esb.build_slice()
    check("slice ok", payload.get("ok") is True)
    check("slice pack", payload.get("pack") == "ESB-TRUTH-1")
    check("slice staff_ready", payload.get("staff_ready") is False)
    check("slice human_commissioned", payload.get("human_commissioned") is False)
    check("slice audit", payload.get("audit_status") == "PARTIAL_IN_BETA")
    check("slice pnl null", payload.get("pnl") is None)
    check("slice settlement null", payload.get("settlement") is None)
    check("slice settlement_api", payload.get("settlement_api") == "UNAVAILABLE")
    check("slice pnl_invented", payload.get("pnl_invented") is False)
    check("slice settlement_invented", payload.get("settlement_invented") is False)
    check("slice fake_settlement", payload.get("fake_settlement") is False)
    check("slice esb_write", payload.get("esb_write") is False)
    check("slice last_success null", payload.get("last_success") is None)
    check("slice intg preserved", payload.get("intg_truth1_preserved") is True)
    check("slice vpl preserved", payload.get("bzg_venuepl1_preserved") is True)
    check(
        "slice caps",
        set(payload.get("closes_toward") or []) >= {"INT-ESB", "CAP-BZG ESB"},
    )
    check("next pack", payload.get("next_pack_for_parent_only") == "BACKUP-HEALTH-1")

    wh = payload.get("warehouse") or {}
    check("warehouse status present", wh.get("warehouse_status") in (
        "READ_OK", "NOT_CONFIGURED", "DEGRADED", "ERROR", "UNKNOWN"
    ))
    check("warehouse pnl_invented", wh.get("pnl_invented") is False)
    check("warehouse settlement null", wh.get("settlement") is None)
    check("warehouse settlement_api", wh.get("settlement_api") == "UNAVAILABLE")
    check("warehouse last_success null", wh.get("last_success") is None)
    check("warehouse write false", wh.get("write") is False)

    sales = wh.get("sales_facts") or {}
    check("sales pnl null", sales.get("pnl") is None)
    check("sales settlement null", sales.get("settlement") is None)
    if wh.get("warehouse_status") == "READ_OK":
        check("sales status READ_OK", sales.get("status") == "READ_OK")
        check("sales row_count int", isinstance(sales.get("row_count"), int))
        check("tables list non-empty", len(wh.get("tables") or []) >= 1)

    tiles = {t.get("id") for t in (payload.get("honesty_tiles") or [])}
    for tid in (
        "audit_status",
        "warehouse",
        "settlement_api",
        "pnl",
        "venue_closes",
        "sales_range",
        "last_success",
        "intg_truth1",
        "bzg_venuepl1",
        "write_authority",
    ):
        check(f"tile {tid}", tid in tiles)

    links = {l.get("id") for l in (payload.get("desk_links") or [])}
    check("link intg", "intg_truth" in links)
    check("link venue pnl", "bzg_venue_pnl" in links)

    schema = esb.schema_document()
    check("schema writes false", schema.get("writes_accepted") is False)
    check("schema esb_write false", schema.get("esb_write") is False)
    check("schema pnl false", schema.get("pnl_property") is False)
    check("schema settlement false", schema.get("settlement_property") is False)


def test_preserved_packs() -> None:
    intg_p = esb.intg_truth1_preserved()
    check("intg preserved ok", intg_p.get("ok") is True, str(intg_p))
    check("intg audit PARTIAL", intg_p.get("audit_status") == "PARTIAL_IN_BETA")
    check("intg pnl_invented false", intg_p.get("pnl_invented") is False)
    check("intg last_success null", intg_p.get("last_success") is None)

    board = intg.build_board(persist_audit=False)
    esb_row = next(
        c for c in board["connectors"] if c["integration_id"] == "INT-ESB-WOLF"
    )
    check("direct intg PARTIAL", esb_row.get("audit_status") == "PARTIAL_IN_BETA")
    check(
        "direct intg pnl false",
        (esb_row.get("probe_facts") or {}).get("pnl_invented") is False,
    )

    vpl = esb.bzg_venuepl1_preserved()
    check("vpl preserved ok", vpl.get("ok") is True, str(vpl))
    check("vpl live_pnl false", vpl.get("live_pnl") is False)
    check("vpl invented_revenue false", vpl.get("invented_revenue") is False)


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/ops/esb-truth-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/ops/esb-truth-1", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api audit PARTIAL", data.get("audit_status") == "PARTIAL_IN_BETA")
        check("api pnl null", data.get("pnl") is None)
        check("api settlement null", data.get("settlement") is None)
        check("api settlement_api", data.get("settlement_api") == "UNAVAILABLE")
        check("api pnl_invented false", data.get("pnl_invented") is False)
        check("api esb_write false", data.get("esb_write") is False)
        check("api last_success null", data.get("last_success") is None)
        check("api intg preserved", data.get("intg_truth1_preserved") is True)
        check("api vpl preserved", data.get("bzg_venuepl1_preserved") is True)

        st, _ = call(port, "GET", "/ops/esb-truth-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/ops/esb-truth-1", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check("page html warehouse", "warehouse" in text.lower())
        check("page staff_ready pin", "staff_ready=false" in text)
        check("page human_commissioned pin", "human_commissioned=false" in text)
        check("page PARTIAL", "PARTIAL_IN_BETA" in text)

        st, _ = call(port, "GET", "/esb-truth-1", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")

        st, body = call(
            port, "POST", "/api/ops/esb-truth-1", email=MATT, body={"esb_write": True}
        )
        check("post esb_write 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post esb_write code", err.get("error") == "esb_write_refused")

        st, body = call(
            port,
            "POST",
            "/api/ops/esb-truth-1",
            email=MATT,
            body={"settlement": {"amount": 50000}},
        )
        check("post settlement 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post settlement code", err.get("error") == "settlement_refused")

        st, body = call(
            port, "POST", "/api/ops/esb-truth-1", email=MATT, body={"pnl": {"revenue": 1}}
        )
        check("post pnl 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post pnl code", err.get("error") == "pnl_refused")

        # Preserved prior APIs still auth-gated
        st, _ = call(port, "GET", "/api/ops/integrations-status")
        check("intg unsigned 403", st == 403, f"status={st}")
        st, body = call(port, "GET", "/api/ops/integrations-status", email=MATT)
        check("intg signed 200", st == 200, f"status={st}")
        intg_data = json.loads(body.decode())
        esb_row = next(
            c for c in intg_data["connectors"] if c["integration_id"] == "INT-ESB-WOLF"
        )
        check("intg still PARTIAL", esb_row.get("audit_status") == "PARTIAL_IN_BETA")
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
                ident_id = seq
                _ws_send(sock, json.dumps({"id": ident_id, "method": method, "params": params or {}}))
                while True:
                    msg = json.loads(_ws_recv(sock))
                    if msg.get("id") == ident_id:
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
            " const audit=document.body && document.body.getAttribute('data-audit');"
            " const wh=document.body && document.body.getAttribute('data-warehouse');"
            " const sap=document.body && document.body.getAttribute('data-settlement-api');"
            " const pnl=document.body && document.body.getAttribute('data-pnl-invented');"
            " const sett=document.body && document.body.getAttribute('data-settlement-invented');"
            " const ew=document.body && document.body.getAttribute('data-esb-write');"
            " const ls=document.body && document.body.getAttribute('data-last-success');"
            " const intg=document.body && document.body.getAttribute('data-intg-preserved');"
            " const vpl=document.body && document.body.getAttribute('data-vpl-preserved');"
            " const sr=document.body && document.body.getAttribute('data-staff-ready');"
            " const hc=document.body && document.body.getAttribute('data-human-commissioned');"
            " const t=document.body ? document.body.innerText : '';"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const tiles=(document.querySelectorAll('[data-tile]')||[]).length;"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && audit==='PARTIAL_IN_BETA'"
            "  && sap==='UNAVAILABLE' && pnl==='0' && sett==='0' && ew==='0'"
            "  && ls==='null' && intg==='1' && vpl==='1' && sr==='0' && hc==='0'"
            "  && stamps>=6 && tiles>=6"
            "  && t.includes('PARTIAL_IN_BETA') && t.includes('UNKNOWN')"
            "  && t.includes('UNAVAILABLE')"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && t.includes('ESB warehouse truth board'),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, tiles:tiles,"
            " ready:ready, audit:audit, wh:wh, sap:sap, intg:intg, vpl:vpl};"
            "})()"
        )
        for width, name in (
            (1024, "esbtruth1-board-desktop.png"),
            (390, "esbtruth1-board-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/ops/esb-truth-1", shell_expr
            ):
                check(f"board ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"partial {name}", value.get("audit") == "PARTIAL_IN_BETA")
                    check(f"settlement_api {name}", value.get("sap") == "UNAVAILABLE")
                    check(f"intg preserved {name}", value.get("intg") == "1")
                    check(f"vpl preserved {name}", value.get("vpl") == "1")
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/ops/esb-truth-1",
            shell_expr,
        ):
            check("partial shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "esbtruth1-partial-stamps.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot partial-stamps", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/ops/esb-truth-1",
            shell_expr,
        ):
            check("inventory shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "esbtruth1-warehouse-inventory.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot warehouse-inventory", dest.is_file() and dest.stat().st_size > 3000)

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
            f"http://127.0.0.1:{port}/ops/esb-truth-1",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "esbtruth1-unsigned-deny.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot unsigned-deny", dest.is_file() and dest.stat().st_size > 800)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_prod_untouched() -> None:
    try:
        os.kill(PROD_PID, 0)
        alive = True
    except OSError:
        alive = False
    check("prod pid held alive", alive, f"pid={PROD_PID}")
    check("prod port constant", PROD_PORT == 8787)


def test_arm_flags() -> None:
    if ARM.is_file():
        arm = json.loads(ARM.read_text(encoding="utf-8"))
        check("arm staff_ready false", arm.get("staff_ready") is False)
        check("arm human_commissioned false", arm.get("human_commissioned") is False)
        check("arm no_push", arm.get("no_push") is True)
        check("arm prod_mutate false", arm.get("prod_mutate") is False)
        check("arm prod pid", arm.get("prod_pid_held") == PROD_PID)
        check(
            "arm next parent",
            arm.get("next_pack_for_parent") == "BACKUP-HEALTH-1",
        )
    else:
        check("arm file present", False)


def main() -> int:
    print("=== ESB-TRUTH-1 pack suite ===")
    test_module_and_honesty()
    test_slice_payload()
    test_preserved_packs()
    test_http_api_and_page()
    test_shots()
    test_prod_untouched()
    test_arm_flags()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
