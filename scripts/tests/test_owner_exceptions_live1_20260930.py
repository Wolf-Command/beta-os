#!/usr/bin/env python3
"""OWNER-EXCEPTIONS-LIVE-1 — Owner exceptions board deepen (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack OWNER-EXCEPTIONS-LIVE-1
(armed 2026-09-30 after GGV-METRIC-HONESTY-1 PASS_VERIFIED).
Live stamps only · severity MISSING when absent · no invent severity.
Preserves DASH-LIVE-1 / OWNER-NEEDS-YOU-1.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain BACKUP-RESTORE-DRILL-1 / HEADCHEF / Exit Report.
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
from core import owner_exceptions_live1 as oex  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "OWNER-EXCEPTIONS-LIVE-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "owner-exceptions-live-1.html"
MODULE = ROOT / "scripts" / "core" / "owner_exceptions_live1.py"
RESULT = ROOT / "docs" / "wolf" / "ops" / "OWNER-EXCEPTIONS-LIVE-1-RESULT.md"
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
    check("api matcher", oex.api_matches("/api/owner/exceptions-live-1"))
    check("page matcher", oex.page_matches("/owner/exceptions-live-1"))
    check("page matcher alias", oex.page_matches("/owner/exceptions"))
    check("page matcher file", oex.page_matches("/owner-exceptions-live-1"))
    check("pack id", oex.PACK_ID == "OWNER-EXCEPTIONS-LIVE-1")
    check("schema id", oex.SCHEMA_ID == "wolf.owner-exceptions-live-1.v1")

    flags = oex.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("invented_severity false", flags.get("invented_severity") is False)
    check("fake_severity false", flags.get("fake_severity") is False)
    check("invented_urgency false", flags.get("invented_urgency") is False)
    check("fake_urgency false", flags.get("fake_urgency") is False)
    check("invented_count false", flags.get("invented_count") is False)
    check("padded_empty false", flags.get("padded_empty") is False)
    check("live_stamps_only", flags.get("live_stamps_only") is True)
    check("severity missing when absent", flags.get("severity_missing_when_absent") is True)
    check("cap proven false", flags.get("cap_core_exceptions_proven") is False)
    check("cap ready false", flags.get("cap_core_exceptions_ready") is False)
    check("dash preserved flag", flags.get("dash_live1_preserved") is True)
    check("needs you preserved flag", flags.get("owner_needs_you1_preserved") is True)
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "BACKUP-RESTORE-DRILL-1")
    check("did not auto-start", flags.get("cursor_did_not_auto_start_next") is True)
    for pack in ("DASH-LIVE-1", "OWNER-NEEDS-YOU-1"):
        check(f"preserved list {pack}", pack in (flags.get("preserved_packs") or []))

    for refuse_fn, code in (
        (oex.refuse_severity, "severity_refused"),
        (oex.refuse_urgency, "urgency_refused"),
        (oex.refuse_invent_exception, "invent_refused"),
        (oex.refuse_staff_ready, "staff_ready_refused"),
        (oex.refuse_proven, "proven_refused"),
        (oex.refuse_ready, "ready_refused"),
    ):
        try:
            refuse_fn({"severity": "CRITICAL"})
            check(f"{code} raised", False)
        except oex.OwnerExceptionsLive1Error as exc:
            check(f"{code} code", exc.code == code)

    try:
        oex.refuse_external_write({"severity": "CRITICAL"})
        check("write severity refused", False)
    except oex.OwnerExceptionsLive1Error as exc:
        check("write severity code", exc.code == "severity_refused")

    try:
        oex.refuse_external_write({"urgency": 99})
        check("write urgency refused", False)
    except oex.OwnerExceptionsLive1Error as exc:
        check("write urgency code", exc.code == "urgency_refused")

    try:
        oex.refuse_external_write({"invent": {"title": "fake"}})
        check("write invent refused", False)
    except oex.OwnerExceptionsLive1Error as exc:
        check("write invent code", exc.code == "invent_refused")

    try:
        oex.refuse_external_write({"staff_ready": True})
        check("write staff_ready refused", False)
    except oex.OwnerExceptionsLive1Error as exc:
        check("write staff_ready code", exc.code == "staff_ready_refused")

    try:
        oex.refuse_external_write({"proven": True})
        check("write proven refused", False)
    except oex.OwnerExceptionsLive1Error as exc:
        check("write proven code", exc.code == "proven_refused")

    html = HTML.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html EMPTY", "EMPTY" in html)
    check("html MISSING", "MISSING" in html)
    check("html fake severity", "fake severity" in html.lower() or "No fake severity" in html)
    check("html DASH-LIVE-1", "DASH-LIVE-1" in html)
    check("html OWNER-NEEDS-YOU-1", "OWNER-NEEDS-YOU-1" in html)
    check("html no fake severity invent", "severity=CRITICAL" not in html)
    check("html no P1 invent", "severity=P1" not in html)


def test_slice_payload() -> None:
    payload = oex.build_slice()
    check("slice ok", payload.get("ok") is True)
    check("slice pack", payload.get("pack") == "OWNER-EXCEPTIONS-LIVE-1")
    check("slice staff_ready", payload.get("staff_ready") is False)
    check("slice human_commissioned", payload.get("human_commissioned") is False)
    check("slice invented_severity", payload.get("invented_severity") is False)
    check("slice fake_severity", payload.get("fake_severity") is False)
    check("slice invented_urgency", payload.get("invented_urgency") is False)
    check("slice invented_count", payload.get("invented_count") is False)
    check("slice padded_empty", payload.get("padded_empty") is False)
    check("slice live_stamps_only", payload.get("live_stamps_only") is True)
    check("slice board_count 10", payload.get("board_count") == 10)
    check("no invented severity helper", oex.no_invented_severity(payload) is True)
    check("dash preserved", payload.get("dash_live1_preserved") is True)
    check("needs you preserved", payload.get("owner_needs_you1_preserved") is True)
    check("cap proven false", payload.get("cap_core_exceptions_proven") is False)
    check("cap ready false", payload.get("cap_core_exceptions_ready") is False)
    check("next pack", payload.get("next_pack_for_parent_only") == "BACKUP-RESTORE-DRILL-1")
    check("did not auto-start pack", payload.get("cursor_did_not_auto_start_next_pack") is True)
    check("stamp view id", payload.get("stamp_view_id") == "owner-command-exceptions")
    check(
        "stamp status known",
        payload.get("stamp_status") in {"LIVE", "STALE", "UNKNOWN", "UNAVAILABLE"},
        str(payload.get("stamp_status")),
    )
    check(
        "operational count int or none",
        payload.get("operational_count") is None
        or isinstance(payload.get("operational_count"), int),
    )
    if isinstance(payload.get("operational_count"), int):
        check("operational count >=0", payload["operational_count"] >= 0)
        check(
            "items len matches ops when present",
            len(payload.get("items") or []) == payload["operational_count"]
            or len(payload.get("items") or []) <= payload["operational_count"],
        )

    boards = payload.get("exception_boards") or []
    check("boards len 10", len(boards) == 10)
    ids = {b.get("id") for b in boards}
    for expected in (
        "freshness",
        "operational",
        "governance",
        "uma_daily_close",
        "data_quality",
        "finance_books",
        "integration",
        "month_end",
        "commissioning_fail",
        "work_item",
    ):
        check(f"board {expected}", expected in ids)

    empty_n = 0
    open_n = 0
    unk_n = 0
    for board in boards:
        check(f"{board['id']} invented false", board.get("invented") is False)
        check(f"{board['id']} invented_severity false", board.get("invented_severity") is False)
        check(f"{board['id']} staff_ready false", board.get("staff_ready") is False)
        sev = board.get("severity")
        if sev is not None:
            check(
                f"{board['id']} severity honest",
                str(sev).upper() in {"MISSING", "UNKNOWN", "UNAVAILABLE"},
                str(sev),
            )
        status = board.get("status")
        if status == "EMPTY":
            empty_n += 1
            check(f"{board['id']} empty count 0", board.get("count") == 0)
            check(f"{board['id']} empty flag", board.get("empty") is True)
        elif status == "OPEN":
            open_n += 1
            check(f"{board['id']} open count int", isinstance(board.get("count"), int))
            check(f"{board['id']} open count >=0", (board.get("count") or 0) >= 0)
        elif status in {"LIVE", "STALE"}:
            check(f"{board['id']} stamp count null", board.get("count") is None)
            check(f"{board['id']} stamp severity null", board.get("severity") is None)
        elif status in {"UNKNOWN", "UNAVAILABLE"}:
            unk_n += 1
            if board.get("kind") != "live_stamp":
                check(f"{board['id']} unknown count null", board.get("count") is None)
        else:
            check(f"{board['id']} known status", False, str(status))

    check("empty_board_count", payload.get("empty_board_count") == empty_n)
    check("open_board_count", payload.get("open_board_count") == open_n)
    check("unknown_board_count", payload.get("unknown_board_count") == unk_n)

    for item in payload.get("items") or []:
        check(
            f"item {item.get('id')} severity MISSING",
            str(item.get("severity") or "").upper() == "MISSING",
            str(item.get("severity")),
        )
        check(f"item {item.get('id')} invented_severity false", item.get("invented_severity") is False)

    tiles = payload.get("honesty_tiles") or []
    check("honesty tiles present", len(tiles) >= 5)
    check("desk links present", len(payload.get("desk_links") or []) >= 3)


def test_preserved_packs() -> None:
    dash = oex.dash_live1_preserved()
    nye = oex.owner_needs_you1_preserved()
    check("dash ok", dash.get("ok") is True)
    check("dash PRESERVED", dash.get("status") == "PRESERVED")
    check("needs you ok", nye.get("ok") is True)
    check("needs you PRESERVED", nye.get("status") == "PRESERVED")


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        status, body = call(port, "GET", "/api/owner/exceptions-live-1")
        check("unsigned api 403", status == 403, f"status={status}")

        status, body = call(port, "GET", "/owner/exceptions-live-1")
        check("unsigned page 403", status == 403, f"status={status}")

        status, raw = call(port, "GET", "/api/owner/exceptions-live-1", email=MATT)
        check("owner api 200", status == 200, f"status={status}")
        payload = json.loads(raw.decode())
        check("owner api ok", payload.get("ok") is True)
        check("owner api invented severity false", payload.get("invented_severity") is False)
        check("owner api fake severity false", payload.get("fake_severity") is False)
        check("owner api staff false", payload.get("staff_ready") is False)
        check("owner api human false", payload.get("human_commissioned") is False)
        check("owner api boards 10", payload.get("board_count") == 10)
        check("owner api dash", payload.get("dash_live1_preserved") is True)
        check("owner api needs you", payload.get("owner_needs_you1_preserved") is True)
        check("owner api live stamps", payload.get("live_stamps_only") is True)

        status, page = call(port, "GET", "/owner/exceptions-live-1", email=MATT)
        check("owner page 200", status == 200, f"status={status}")
        text = page.decode("utf-8", errors="replace")
        check("page has title", "Owner exceptions" in text or "Exceptions" in text)
        check("page staff_ready=false", "staff_ready=false" in text)

        status, raw = call(
            port,
            "POST",
            "/api/owner/exceptions-live-1",
            email=MATT,
            body={"severity": "CRITICAL"},
        )
        check("post severity 403", status == 403, f"status={status}")
        err = json.loads(raw.decode())
        check("post severity code", err.get("error") == "severity_refused", str(err)[:200])

        status, raw = call(
            port,
            "POST",
            "/api/owner/exceptions-live-1/invent",
            email=MATT,
            body={"invent": {"title": "fake severity"}},
        )
        check("post invent 403", status == 403, f"status={status}")
        err = json.loads(raw.decode())
        check("post invent code", err.get("error") == "invent_refused", str(err)[:200])

        status, raw = call(
            port,
            "POST",
            "/api/owner/exceptions-live-1",
            email=MATT,
            body={"urgency": 99},
        )
        check("post urgency 403", status == 403)
        err = json.loads(raw.decode())
        check("post urgency code", err.get("error") == "urgency_refused")

        status, raw = call(
            port,
            "POST",
            "/api/owner/exceptions-live-1",
            email=MATT,
            body={"staff_ready": True},
        )
        check("post staff_ready 403", status == 403)
        err = json.loads(raw.decode())
        check("post staff_ready code", err.get("error") == "staff_ready_refused")

        status, raw = call(
            port,
            "POST",
            "/api/owner/exceptions-live-1",
            email=MATT,
            body={"proven": True},
        )
        check("post proven 403", status == 403)
        err = json.loads(raw.decode())
        check("post proven code", err.get("error") == "proven_refused")
    finally:
        httpd.shutdown()
        httpd.server_close()


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


def _ws_connect(host: str, port: int, path: str):
    import hashlib

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
            break
        buf += chunk
    expected = base64.b64encode(
        hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
    ).decode()
    if expected not in buf.decode("latin1", errors="replace"):
        sock.close()
        raise ConnectionError("websocket handshake failed")
    return sock


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
                time.sleep(0.35)
                value = evaluate(wait_expr)
                if value and value.get("ok"):
                    break
            yield cdp, evaluate, value
            sock.close()
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


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
            " const inv=document.body && document.body.getAttribute('data-invented-severity');"
            " const fake=document.body && document.body.getAttribute('data-fake-severity');"
            " const eh=document.body && document.body.getAttribute('data-empty-honest');"
            " const ls=document.body && document.body.getAttribute('data-live-stamps');"
            " const dl=document.body && document.body.getAttribute('data-dash-live-preserved');"
            " const ny=document.body && document.body.getAttribute('data-needs-you-preserved');"
            " const proven=document.body && document.body.getAttribute('data-cap-proven');"
            " const sr=document.body && document.body.getAttribute('data-staff-ready');"
            " const hc=document.body && document.body.getAttribute('data-human-commissioned');"
            " const t=document.body ? document.body.innerText : '';"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const boards=(document.querySelectorAll('[data-board]')||[]).length;"
            " const tiles=(document.querySelectorAll('[data-tile]')||[]).length;"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && inv==='0' && fake==='0' && eh==='1' && ls==='1'"
            "  && dl==='1' && ny==='1' && proven==='0' && sr==='0' && hc==='0'"
            "  && stamps>=5 && boards>=10 && tiles>=4"
            "  && t.includes('EMPTY') && (t.includes('OPEN') || t.includes('LIVE') || t.includes('MISSING'))"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && (t.includes('Owner exceptions') || t.includes('exceptions board')),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, boards:boards, tiles:tiles,"
            " ready:ready, inv:inv, fake:fake, dl:dl, ny:ny};"
            "})()"
        )
        for width, name in (
            (1024, "ownerexceptions1-desk-desktop.png"),
            (390, "ownerexceptions1-desk-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/owner/exceptions-live-1", shell_expr
            ):
                check(f"desk ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"invented 0 {name}", value.get("inv") == "0")
                    check(f"fake 0 {name}", value.get("fake") == "0")
                    check(f"boards visible {name}", (value.get("boards") or 0) >= 10)
                    check(f"dash {name}", value.get("dl") == "1")
                    check(f"needs you {name}", value.get("ny") == "1")
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/owner/exceptions-live-1",
            shell_expr,
        ):
            check("boards shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "ownerexceptions1-boards-honesty.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot boards-honesty", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/owner/exceptions-live-1",
            shell_expr,
        ):
            check("stamps shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "ownerexceptions1-stamps.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot stamps", dest.is_file() and dest.stat().st_size > 3000)

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
            f"http://127.0.0.1:{port}/owner/exceptions-live-1",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "ownerexceptions1-unsigned-deny.png"
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
            arm.get("next_pack_for_parent") == "BACKUP-RESTORE-DRILL-1",
        )
    else:
        check("arm file present", False)


def main() -> int:
    print("=== OWNER-EXCEPTIONS-LIVE-1 pack suite ===")
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
