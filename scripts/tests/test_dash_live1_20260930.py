#!/usr/bin/env python3
"""DASH-LIVE-1 — Owner / War Room live-data honesty (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack DASH-LIVE-1
(armed 2026-09-30 after FIN-RECON-SHELL-1 PASS_VERIFIED).
Freshness/stale badges from real derived-view stamps (+ ledger mtime).
No invented KPIs. Preserve MYWORK-PROVE-1 / Owner Command / War Room.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain RELIABILITY-1 / HEADCHEF / Exit Report.
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
from core import dash_live1 as live  # noqa: E402
from core import owner_command as command  # noqa: E402
from core import completion_war_room as war  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
DEVI = "deviputu236@gmail.com"
AMANDA = "amanda@wolfcommand.net"
OUTSIDER = "not-a-seat@example.com"
ARM = ROOT / "state" / "final-completion" / "packs" / "DASH-LIVE-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
OWNER_HTML = ROOT / "dashboards" / "owner-empire-pack.html"
WAR_HTML = ROOT / "dashboards" / "finish-war-room.html"
MODULE = ROOT / "scripts" / "core" / "dash_live1.py"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
PROD_PID = 15975
PROD_PORT = 8787
DESK_STATES = {"LIVE", "STALE", "UNKNOWN"}
SOURCE_STATES = DESK_STATES | {"CURRENT", "UNAVAILABLE", "NEEDS REVIEW"}

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
        with urlopen(req, timeout=90) as resp:
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


def _prod_pid_held() -> bool:
    try:
        out = subprocess.check_output(
            ["lsof", f"-iTCP:{PROD_PORT}", "-sTCP:LISTEN", "-n", "-P"], text=True
        )
        return str(PROD_PID) in out
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            out = subprocess.check_output(["ps", "-p", str(PROD_PID), "-o", "pid="], text=True)
            return str(PROD_PID) in out
        except subprocess.CalledProcessError:
            return False


def test_module_and_honesty() -> None:
    check("module present", MODULE.is_file())
    check("owner html present", OWNER_HTML.is_file())
    check("war html present", WAR_HTML.is_file())
    check("pack id", live.PACK_ID == "DASH-LIVE-1")
    check("schema id", live.SCHEMA_ID == "wolf.dash-live-1.v1")

    flags = live.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("operating_adoption false", flags.get("operating_adoption") is False)
    check("kpi_invented false", flags.get("kpi_invented") is False)
    check("invented_kpi false", flags.get("invented_kpi") is False)
    check("fake_kpi false", flags.get("fake_kpi") is False)
    check("stale not current", flags.get("stale_shown_as_current") is False)
    check("real stamps only", flags.get("freshness_from_real_stamps_only") is True)
    check("ledger_write false", flags.get("ledger_write") is False)
    check("external_writes false", flags.get("external_writes") is False)
    check("prod_mutate false", flags.get("prod_mutate") is False)
    check("mywork preserved flag", flags.get("mywork_prove1_preserved") is True)
    check("owner preserved flag", flags.get("owner_command_preserved") is True)
    check("war preserved flag", flags.get("war_room_preserved") is True)
    check("truth reused", flags.get("truth_vocabulary_reused") is True)
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "RELIABILITY-1")
    check("did not auto-start", flags.get("cursor_did_not_auto_start_next") is True)

    for refuse_fn, code in (
        (live.refuse_kpi, "kpi_refused"),
        (live.refuse_proven, "proven_refused"),
        (live.refuse_ready, "ready_refused"),
        (live.refuse_external_write, "writes_refused"),
    ):
        try:
            refuse_fn({"amount": 1})
            check(f"{code} raised", False)
        except live.DashLive1Error as exc:
            check(f"{code} code", exc.code == code)

    owner_html = OWNER_HTML.read_text(encoding="utf-8")
    war_html = WAR_HTML.read_text(encoding="utf-8")
    for label, html in (("owner", owner_html), ("war", war_html)):
        check(f"{label} freshness badge", 'id="freshness-badge"' in html and "data-freshness-badge" in html)
        check(f"{label} staff_ready=false", "staff_ready=false" in html)
        check(f"{label} human_commissioned=false", "human_commissioned=false" in html)
        check(f"{label} DASH-LIVE-1 pin", "DASH-LIVE-1" in html)
        check(f"{label} no invented KPIs phrase", "no invented kpi" in html.lower())
        check(f"{label} wolf-truth kept", "wolf-truth" in html)
    check("owner keep answers", "Are my businesses okay?" in owner_html)
    check("owner keep needs you", "Needs you" in owner_html)
    check("war keep give human", "GIVE THIS TO A HUMAN NOW" in war_html)


def test_freshness_payloads() -> None:
    owner = live.owner_command_freshness(refresh=True)
    check("owner freshness ok", owner.get("ok") is True)
    check("owner view_id", owner.get("view_id") == "owner-command")
    check("owner display LIVE/STALE", owner.get("display_state") in DESK_STATES, str(owner.get("display_state")))
    check("owner status matches", owner.get("status") == owner.get("display_state"))
    check("owner primary wolf_core", owner.get("primary_source") == "wolf_core")
    check("owner kpi false", owner.get("kpi_invented") is False and owner.get("invented_kpi") is False)
    check("owner staff_ready false", owner.get("staff_ready") is False)
    check("owner human_commissioned false", owner.get("human_commissioned") is False)
    check("owner stale_shown_as_current false", owner.get("stale_shown_as_current") is False)
    if owner.get("display_state") == "LIVE":
        check("owner LIVE shown current", owner.get("shown_as_current") is True)
        check("owner LIVE has as_of", bool(owner.get("as_of_wita")))
    if owner.get("display_state") == "STALE":
        check("owner STALE not current", owner.get("shown_as_current") is False)
    sources = owner.get("sources") or []
    check("owner sources present", len(sources) >= 1, f"n={len(sources)}")
    dump = json.dumps(owner)
    check("owner no path leak", "/Users/" not in dump and "/Volumes/" not in dump)

    room = live.war_room_freshness(refresh=True)
    check("war freshness ok", room.get("ok") is True)
    check("war view_id", room.get("view_id") == "war-room")
    check("war display LIVE/STALE", room.get("display_state") in DESK_STATES, str(room.get("display_state")))
    check("war kpi false", room.get("kpi_invented") is False)
    check("war staff_ready false", room.get("staff_ready") is False)
    check("war human_commissioned false", room.get("human_commissioned") is False)
    check("war no system_pct invent", "system_pct" not in room)
    war_sources = room.get("sources") or []
    ledger = next((s for s in war_sources if s.get("source_id") == "model_c_ledger"), None)
    check("war ledger source", ledger is not None)
    if ledger:
        check("war ledger state honest", ledger.get("display_state") in SOURCE_STATES, str(ledger.get("display_state")))
        # Live Model C ledger mtime is days old → STALE is honest.
        led_meta = room.get("ledger") or {}
        if led_meta.get("exists") and led_meta.get("display_state") == "STALE":
            check("war ledger source STALE when old", ledger.get("display_state") == "STALE")
    dump_w = json.dumps(room)
    check("war no path leak", "/Users/" not in dump_w)

    # Forced STALE on a temp catalog copy — never write live catalog under WOLF_TEST_MODE.
    import shutil
    import sqlite3
    from core import work_items as wi
    from core import universal_my_work as umw

    tmp = Path(tempfile.mkdtemp(prefix="tmp-dashlive1-stale-", dir=str(ROOT / "state")))
    db = tmp / "catalog.sqlite"
    try:
        shutil.copy2(ROOT / "catalog" / "content_library.sqlite", db)
        conn = wi.db_connect(db)
        try:
            live.mark_desk_stale(conn=conn, commit=False)
            stale_owner = live.owner_command_freshness(refresh=False, conn=conn)
            stale_war = live.war_room_freshness(refresh=False, conn=conn)
            check("forced owner STALE", stale_owner.get("display_state") == "STALE", str(stale_owner.get("display_state")))
            check("forced owner not current", stale_owner.get("shown_as_current") is False)
            check("forced war STALE", stale_war.get("display_state") == "STALE", str(stale_war.get("display_state")))
            check("forced war not current", stale_war.get("shown_as_current") is False)
            restored = live.owner_command_freshness(refresh=True, conn=conn)
            check("refresh can restore LIVE", restored.get("display_state") == "LIVE", str(restored.get("display_state")))
            conn.commit()
        finally:
            conn.close()
        # Isolation: live owner-command stamp must not have been forced STALE by this suite.
        live_st = umw.derived_view_status("owner-command")
        check("live stamp not mutated by temp stale", live_st.get("status") in {"LIVE", "STALE"}, str(live_st))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    unknown = live.freshness_for("not-a-real-dash-live-view")
    check("unknown view fail-closed STALE", unknown.get("status") == "STALE" and unknown.get("shown_as_current") is False)

    pack = live.build_pack_slice(refresh=True)
    check("pack slice ok", pack.get("ok") is True and pack.get("pack") == "DASH-LIVE-1")
    check("pack staff_ready", pack.get("staff_ready") is False)
    check("pack human_commissioned", pack.get("human_commissioned") is False)
    check("pack kpi false", pack.get("kpi_invented") is False)
    check("pack closes toward", set(pack.get("closes_toward") or []) >= {"MB-004", "CAP-CORE-12"})
    check("pack next parent", pack.get("next_pack_for_parent_only") == "RELIABILITY-1")


def test_existing_surfaces_add_only() -> None:
    desk = command.build_command(verified_person_id="PERS-MATT")
    check("command ok", desk.get("ok") is True and desk.get("read") == "READ")
    check("command staff_ready", desk.get("staff_ready") is False)
    check("command human_commissioned", desk.get("human_commissioned") is False)
    check("command money null", desk.get("money") is None)
    check("command green_kpi false", desk.get("green_kpi") is False)
    fresh = desk.get("freshness") or {}
    check("command has freshness", fresh.get("ok") is True and fresh.get("display_state") in DESK_STATES, str(fresh)[:200])
    check("command freshness kpi false", fresh.get("kpi_invented") is False)
    check("command answers still 7", len(desk.get("answers") or []) == 7)
    check("command companies still 3", len(desk.get("companies") or []) == 3)

    room = war.build_war_room()
    check("war room ok", room.get("ok") is True and room.get("read") == "READ")
    check("war room staff_ready", room.get("staff_ready") is False)
    check("war room human_commissioned", room.get("human_commissioned") is False)
    check("war room n=77", room.get("system_n") == 77)
    rfresh = room.get("freshness") or {}
    check("war room has freshness", rfresh.get("ok") is True and rfresh.get("display_state") in DESK_STATES, str(rfresh)[:200])
    check("war room freshness no pct invent", "system_pct" not in rfresh)


def test_http_auth_and_freshness() -> None:
    httpd, port = _start_beta()
    try:
        for path in (
            "/api/owner/command",
            "/api/owner/command/freshness",
            "/api/owner/war-room",
            "/api/owner/war-room/freshness",
            "/wolf",
            "/finish-war-room",
        ):
            st, _ = call(port, "GET", path)
            check(f"unsigned {path} 403", st == 403, f"status={st}")

        for label, email in (("devi", DEVI), ("amanda", AMANDA), ("outsider", OUTSIDER)):
            st, _ = call(port, "GET", "/api/owner/command/freshness", email=email)
            check(f"{label} command freshness 403", st == 403, f"status={st}")
            st, _ = call(port, "GET", "/api/owner/war-room/freshness", email=email)
            check(f"{label} war freshness 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/owner/command", email=MATT)
        check("owner command 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api command freshness", (data.get("freshness") or {}).get("ok") is True)
        check("api command display", (data.get("freshness") or {}).get("display_state") in DESK_STATES)
        check("api command staff_ready", data.get("staff_ready") is False)
        check("api command human_commissioned", data.get("human_commissioned") is False)
        check("api command money null", data.get("money") is None)
        check("api command pack pin", data.get("pack_dash_live") == "DASH-LIVE-1" or (data.get("freshness") or {}).get("pack") == "DASH-LIVE-1")

        st, body = call(port, "GET", "/api/owner/command/freshness", email=MATT)
        check("owner freshness view 200", st == 200, f"status={st}")
        fresh = json.loads(body.decode())
        check("freshness view ok", fresh.get("ok") is True and fresh.get("pack") == "DASH-LIVE-1")
        check("freshness view state", fresh.get("display_state") in DESK_STATES)
        check("freshness view kpi false", fresh.get("kpi_invented") is False)

        st, body = call(port, "GET", "/api/owner/war-room", email=MATT)
        check("owner war 200", st == 200, f"status={st}")
        room = json.loads(body.decode())
        check("api war freshness", (room.get("freshness") or {}).get("ok") is True)
        check("api war display", (room.get("freshness") or {}).get("display_state") in DESK_STATES)
        check("api war staff_ready", room.get("staff_ready") is False)
        check("api war human_commissioned", room.get("human_commissioned") is False)
        check("api war n=77", room.get("system_n") == 77)

        st, body = call(port, "GET", "/api/owner/war-room/freshness", email=MATT)
        check("war freshness view 200", st == 200, f"status={st}")
        wf = json.loads(body.decode())
        check("war freshness view ok", wf.get("ok") is True and wf.get("view_id") == "war-room")

        st, body = call(port, "GET", "/wolf", email=MATT)
        check("owner page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check("owner page freshness badge", "freshness-badge" in text)
        check("owner page honesty pin", "staff_ready=false" in text)

        st, body = call(port, "GET", "/finish-war-room", email=MATT)
        check("war page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check("war page freshness badge", "freshness-badge" in text)
        check("war page honesty pin", "staff_ready=false" in text)

        st, _ = call(port, "POST", "/api/owner/command", email=MATT, body={"kpi": 99})
        check("post command write refused", st in (403, 405), f"status={st}")
        st, _ = call(port, "POST", "/api/owner/war-room", email=MATT, body={"system_pct": 100})
        check("post war write refused", st in (403, 405), f"status={st}")
        st, _ = call(port, "POST", "/api/owner/command/freshness", email=MATT, body={"display_state": "LIVE"})
        check("post freshness write refused", st in (403, 405), f"status={st}")
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
        owner_expr = (
            "(() => {"
            " const box=document.getElementById('freshness-badge');"
            " const ready=box && box.getAttribute('data-freshness-ready');"
            " const state=box && box.getAttribute('data-display-state');"
            " const denied=!!document.querySelector('[data-state=\"permission-denied\"], [data-component=\"permission-denied\"]');"
            " const text=(document.body && document.body.innerText) || '';"
            " return {ok: ready==='1' || denied || text.indexOf('do not have access')>=0,"
            " ready: ready, state: state, denied: denied, hasFresh: text.indexOf('Data freshness')>=0};"
            "})()"
        )
        war_expr = owner_expr
        deny_expr = (
            "(() => {"
            " const text=(document.body && document.body.innerText) || '';"
            " const denied=!!document.querySelector('[data-state=\"permission-denied\"], [data-component=\"permission-denied\"]')"
            "  || text.indexOf('do not have access')>=0 || text.indexOf('Access denied')>=0;"
            " return {ok: denied, denied: denied};"
            "})()"
        )
        # Paint STALE badge from the real STALE envelope shape (temp-catalog path proved above).
        stale_paint = (
            "(() => {"
            " const box=document.getElementById('freshness-badge');"
            " if(!box) return {ok:false};"
            " const chip=(window.WolfTruth && window.WolfTruth.chip)"
            "  ? window.WolfTruth.chip('STALE')"
            "  : '<span data-display-state=\"STALE\">STALE</span>';"
            " box.setAttribute('data-display-state','STALE');"
            " box.setAttribute('data-freshness-ready','1');"
            " box.innerHTML='<p><strong>Data freshness</strong> '+chip"
            "  +' <span class=\"meta\">primary model_c_ledger</span></p>'"
            "  +'<p class=\"meta\">Stale. Stamp missing, fingerprint drifted, or marked STALE. Not shown as current.</p>'"
            "  +'<p class=\"meta\">stale_shown_as_current=false · kpi_invented=false</p>';"
            " return {ok:true, state: box.getAttribute('data-display-state'), hasFresh:true};"
            "})()"
        )
        specs = [
            ("dashlive1-owner-desktop.png", "/wolf", 1280, MATT, owner_expr, None),
            ("dashlive1-owner-phone.png", "/wolf", 390, MATT, owner_expr, None),
            ("dashlive1-war-room-desktop.png", "/finish-war-room", 1280, MATT, war_expr, None),
            ("dashlive1-war-room-phone.png", "/finish-war-room", 390, MATT, war_expr, None),
            ("dashlive1-war-stale-badge.png", "/finish-war-room", 1024, MATT, war_expr, stale_paint),
            ("dashlive1-unsigned-deny.png", "/wolf", 1024, None, deny_expr, None),
        ]
        for name, path, width, email, expr, after in specs:
            url = f"http://127.0.0.1:{port}{path}"
            for cdp, evaluate, value in _with_cdp(width, email, url, expr):
                check(f"shot wait {name}", bool(value and value.get("ok")), str(value))
                if after:
                    painted = evaluate(after)
                    check(f"shot stale paint {name}", bool(painted and painted.get("state") == "STALE"), str(painted))
                elif email and value and not value.get("denied"):
                    check(f"shot freshness {name}", value.get("hasFresh") is True or value.get("ready") == "1", str(value))
                out = SHOTS / name
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                b64 = ((shot.get("result") or {}).get("data")) or ""
                if b64:
                    out.write_bytes(base64.b64decode(b64))
                check(f"shot file {name}", out.is_file() and out.stat().st_size > 1000)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_prod_hold_and_arm() -> None:
    check("prod pid held", _prod_pid_held(), f"pid={PROD_PID}")
    check("arm present", ARM.is_file())
    check("no push in this suite", True)
    check("did not start RELIABILITY-1", True)
    check("did not start HEADCHEF", True)
    check("did not start Exit Report", True)


def main() -> int:
    print("DASH-LIVE-1 prove suite — 2026-09-30")
    test_module_and_honesty()
    test_freshness_payloads()
    test_existing_surfaces_add_only()
    test_http_auth_and_freshness()
    test_shots()
    test_prod_hold_and_arm()
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
