#!/usr/bin/env python3
"""AMG-OCC-TRUTH-1 — occupancy honesty desk (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack AMG-OCC-TRUTH-1
(armed 2026-09-30 after CONN-HEALTH-BOARD-1 PASS_VERIFIED).

UNKNOWN/BLOCKED when PMS blocked. No fake occupancy. Preserves AMG-OS-SHELL-1.
Unsigned API/page 403. Invent-occ writes refused.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain SOP-LESSON-LIVE-1 / HEADCHEF / Exit Report.
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
from core import amg_occ_truth1 as occ  # noqa: E402
from core import amg_os_shell as shell  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "AMG-OCC-TRUTH-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "amg-occ-truth-1.html"
MODULE = ROOT / "scripts" / "core" / "amg_occ_truth1.py"
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
    check("page matcher /amg/occ-truth-1", occ.page_matches("/amg/occ-truth-1"))
    check("page matcher alias", occ.page_matches("/amg-occ-truth-1.html"))
    check("page matcher short", occ.page_matches("/amg/occ-truth"))
    check("api matcher", occ.api_matches("/api/amg/occ-truth-1"))
    check("api no mutate path", not occ.api_matches("/api/amg/occ-truth-1/mutate"))

    flags = occ.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("invented_occupancy false", flags.get("invented_occupancy") is False)
    check("cap_amg_01_unblocked false", flags.get("cap_amg_01_unblocked") is False)
    check("yanolja_live false", flags.get("yanolja_live") is False)
    check("pms_connected false", flags.get("pms_connected") is False)
    check("fake_pms_data false", flags.get("fake_pms_data") is False)
    check("occupancy_unknown", flags.get("occupancy_unknown") is True)
    check("occupancy_blocked", flags.get("occupancy_blocked") is True)
    check("yanolja_blocked", flags.get("yanolja_blocked") is True)
    check("shell preserved flag", flags.get("amg_os_shell1_preserved") is True)
    check("cap_amg_occ_proven false", flags.get("cap_amg_occ_proven") is False)
    check("cap_amg_occ_ready false", flags.get("cap_amg_occ_ready") is False)
    check("ceiling BUILT", flags.get("cap_amg_occ_ceiling") == "BUILT")
    check("maturity SPECIFIED", flags.get("cap_amg_occ_maturity") == "SPECIFIED")
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "SOP-LESSON-LIVE-1")
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("prod pid held const", occ.PROD_PID_HELD == PROD_PID)

    try:
        occ.refuse_invent_occupancy({"occupancy": 88})
        check("refuse_invent_occupancy raises", False)
    except occ.AmgOccTruth1Error as exc:
        check("refuse_invent_occupancy raises", True)
        check("refuse_invent_occupancy code", exc.code == "invent_occupancy_refused")
    try:
        occ.refuse_unblock_pms({"unblock": True})
        check("refuse_unblock_pms raises", False)
    except occ.AmgOccTruth1Error as exc:
        check("refuse_unblock_pms raises", True)
        check("refuse_unblock_pms code", exc.code == "unblock_pms_refused")

    try:
        occ.refuse_external_write({"occupancy": 90})
        check("refuse write occupancy raises", False)
    except occ.AmgOccTruth1Error as exc:
        check("refuse write occupancy", exc.code == "invent_occupancy_refused")
    try:
        occ.refuse_external_write({"occupancy_pct": 75})
        check("refuse write pct raises", False)
    except occ.AmgOccTruth1Error as exc:
        check("refuse write pct", exc.code == "invent_occupancy_refused")
    try:
        occ.refuse_external_write({"unblock_pms": True})
        check("refuse write unblock raises", False)
    except occ.AmgOccTruth1Error as exc:
        check("refuse write unblock", exc.code == "unblock_pms_refused")
    try:
        occ.refuse_external_write({"proven": True})
        check("refuse write proven raises", False)
    except occ.AmgOccTruth1Error as exc:
        check("refuse write proven", exc.code == "proven_refused")
    try:
        occ.refuse_external_write({"ready": True})
        check("refuse write ready raises", False)
    except occ.AmgOccTruth1Error as exc:
        check("refuse write ready", exc.code == "ready_refused")
    try:
        occ.refuse_external_write({"noop": True})
        check("refuse write generic raises", False)
    except occ.AmgOccTruth1Error as exc:
        check("refuse write generic", exc.code == "write_refused")


def test_desk_payload() -> None:
    payload = occ.build_slice()
    check("ok", payload.get("ok") is True)
    check("payload staff_ready false", payload.get("staff_ready") is False)
    check("payload human_commissioned false", payload.get("human_commissioned") is False)
    check("payload invented_occupancy false", payload.get("invented_occupancy") is False)
    check("payload cap_amg_01_unblocked false", payload.get("cap_amg_01_unblocked") is False)
    check("payload yanolja_live false", payload.get("yanolja_live") is False)
    check("payload fake_pms false", payload.get("fake_pms_data") is False)
    check("payload occupancy_unknown", payload.get("occupancy_unknown") is True)
    check("payload occupancy_blocked", payload.get("occupancy_blocked") is True)
    check("payload last_success null", payload.get("last_success") is None)
    check("payload shell preserved", payload.get("amg_os_shell1_preserved") is True)
    check("payload cap_amg_occ not proven", payload.get("cap_amg_occ_proven") is False)
    check("payload ceiling BUILT", payload.get("cap_amg_occ_ceiling") == "BUILT")
    check("payload next parent", payload.get("next_pack_for_parent_only") == "SOP-LESSON-LIVE-1")
    check("payload no auto-chain", payload.get("cursor_did_not_auto_start_next_pack") is True)

    slots = payload.get("occ_slots") or []
    check("occ slots >= 5", len(slots) >= 5, str(len(slots)))
    check("all occ slots unknown", occ.all_occ_slots_unknown(payload) is True)
    need = {"occupancy_pct", "rooms_sold", "rooms_available", "adr", "revpar"}
    ids = {s.get("id") for s in slots}
    check("slot ids present", need.issubset(ids), str(ids))
    for s in slots:
        check(f"{s['id']} value null", s.get("value") is None)
        check(f"{s['id']} pct null", s.get("occupancy_pct") is None)
        check(f"{s['id']} count null", s.get("count") is None)
        check(f"{s['id']} display UNKNOWN", s.get("display") == "UNKNOWN")
        check(f"{s['id']} BLOCKED", s.get("status") == "BLOCKED_EXTERNAL")
        check(f"{s['id']} not invented", s.get("invented_occupancy") is False)
        check(f"{s['id']} not live", s.get("yanolja_live") is False)

    yan = payload.get("yanolja") or {}
    check("yan BLOCKED_EXTERNAL", yan.get("audit_status") == "BLOCKED_EXTERNAL")
    check("yan last_success null", yan.get("last_success") is None)
    check("yanolja stays blocked helper", occ.yanolja_stays_blocked(payload) is True)

    tiles = {t.get("id") for t in (payload.get("honesty_tiles") or [])}
    for tid in (
        "occupancy",
        "yanolja",
        "invented_occupancy",
        "amg_os_shell1",
        "cap_amg_01",
        "cap_amg_occ",
    ):
        check(f"tile {tid}", tid in tiles)

    links = {l.get("id") for l in (payload.get("desk_links") or [])}
    check("link shell", "amg_os_shell" in links)
    check("link intg", "integrations_status" in links)

    schema = occ.schema_document()
    check("schema writes false", schema.get("writes_accepted") is False)
    check("schema occupancy false", schema.get("occupancy_property") is False)
    check("schema pms unblocked false", schema.get("pms_unblocked") is False)


def test_amg_os_shell_preserved() -> None:
    pin = occ.amg_os_shell1_preserved()
    check("shell preserved ok", pin.get("ok") is True, str(pin))
    check("shell pms blocked", pin.get("pms_tiles_blocked") is True)
    check("shell cap not unblocked", pin.get("cap_amg_01_unblocked") is False)
    check("shell no fake", pin.get("fake_pms_data") is False)
    check("shell no invent occ", pin.get("invented_occupancy") is False)
    check("shell yan blocked", pin.get("yanolja_status") == "BLOCKED_EXTERNAL")
    check("shell last_success null", pin.get("last_success") is None)

    direct = shell.build_shell()
    check("direct shell ok", direct.get("ok") is True)
    check("direct all pms blocked", shell.all_pms_tiles_blocked(direct) is True)
    check("direct cap not unblocked", direct.get("cap_amg_01_unblocked") is False)
    check("direct invented_occupancy false", direct.get("invented_occupancy") is False)


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/amg/occ-truth-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/amg/occ-truth-1", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api invented_occupancy false", data.get("invented_occupancy") is False)
        check("api cap not unblocked", data.get("cap_amg_01_unblocked") is False)
        check("api occupancy unknown", data.get("occupancy_unknown") is True)
        check("api occupancy blocked", data.get("occupancy_blocked") is True)
        check("api last_success null", data.get("last_success") is None)
        check("api shell preserved", data.get("amg_os_shell1_preserved") is True)
        check("api slots unknown helper", occ.all_occ_slots_unknown(data) is True)
        check("api yanolja blocked helper", occ.yanolja_stays_blocked(data) is True)

        st, _ = call(port, "GET", "/amg/occ-truth-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/amg/occ-truth-1", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check(
            "page html occ",
            "occupancy truth" in text.lower() or "UNKNOWN when PMS" in text,
        )
        check("page staff_ready pin", "staff_ready=false" in text)
        check("page human_commissioned pin", "human_commissioned=false" in text)
        check(
            "page no invent",
            "invented occupancy" in text.lower() or "No invented occupancy" in text,
        )

        st, _ = call(port, "GET", "/amg-occ-truth-1", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")

        st, body = call(
            port, "POST", "/api/amg/occ-truth-1", email=MATT, body={"occupancy": 88}
        )
        check("post occupancy 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post occupancy refused code", err.get("error") == "invent_occupancy_refused")

        st, body = call(
            port, "POST", "/api/amg/occ-truth-1", email=MATT, body={"occupancy_pct": 75}
        )
        check("post pct 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post pct refused code", err.get("error") == "invent_occupancy_refused")

        st, body = call(
            port, "POST", "/api/amg/occ-truth-1", email=MATT, body={"unblock_pms": True}
        )
        check("post unblock 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post unblock refused code", err.get("error") == "unblock_pms_refused")

        st, body = call(
            port, "POST", "/api/amg/occ-truth-1", email=MATT, body={"proven": True}
        )
        check("post proven 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post proven refused code", err.get("error") == "proven_refused")

        st, _ = call(port, "GET", "/api/amg/os-shell")
        check("shell unsigned 403", st == 403, f"status={st}")
        st, body = call(port, "GET", "/api/amg/os-shell", email=MATT)
        check("shell signed 200", st == 200, f"status={st}")
        shell_data = json.loads(body.decode())
        check("shell still blocked", shell.all_pms_tiles_blocked(shell_data) is True)
        check("shell still no invent", shell_data.get("invented_occupancy") is False)
        check("shell still cap blocked", shell_data.get("cap_amg_01_unblocked") is False)
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
        desk_expr = (
            "(() => {"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const unk=document.body && document.body.getAttribute('data-occupancy-unknown');"
            " const blk=document.body && document.body.getAttribute('data-occupancy-blocked');"
            " const inv=document.body && document.body.getAttribute('data-invented-occupancy');"
            " const cap=document.body && document.body.getAttribute('data-cap-amg-01-unblocked');"
            " const yan=document.body && document.body.getAttribute('data-yanolja-blocked');"
            " const sp=document.body && document.body.getAttribute('data-shell-preserved');"
            " const sr=document.body && document.body.getAttribute('data-staff-ready');"
            " const hc=document.body && document.body.getAttribute('data-human-commissioned');"
            " const t=document.body ? document.body.innerText : '';"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const slots=(document.querySelectorAll('[data-slot]')||[]).length;"
            " const unkBox=document.querySelector('[data-occupancy=\"unknown\"]');"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && unk==='1' && blk==='1' && inv==='0'"
            "  && cap==='0' && yan==='1' && sp==='1' && sr==='0' && hc==='0'"
            "  && stamps>=4 && slots>=5 && !!unkBox"
            "  && t.includes('UNKNOWN') && t.includes('BLOCKED_EXTERNAL')"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && t.includes('occupancy truth desk'),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, slots:slots,"
            " ready:ready, unk:unk, blk:blk, sp:sp, yan:yan};"
            "})()"
        )
        for width, name in (
            (1024, "amgocctruth1-desk-desktop.png"),
            (390, "amgocctruth1-desk-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/amg/occ-truth-1", desk_expr
            ):
                check(f"desk ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"occ unknown {name}", value.get("unk") == "1")
                    check(f"occ blocked {name}", value.get("blk") == "1")
                    check(f"slots visible {name}", (value.get("slots") or 0) >= 5)
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/amg/occ-truth-1",
            desk_expr,
        ):
            check("unknown occ shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "amgocctruth1-occ-unknown.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot occ-unknown", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/amg/occ-truth-1",
            desk_expr,
        ):
            check("shell preserved shot ready", bool(value and value.get("ok")), str(value)[:200])
            if value:
                check("shell preserved attr", value.get("sp") == "1")
                check("yanolja blocked attr", value.get("yan") == "1")
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "amgocctruth1-shell-preserved.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot shell-preserved", dest.is_file() and dest.stat().st_size > 3000)

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
            f"http://127.0.0.1:{port}/amg/occ-truth-1",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "amgocctruth1-unsigned-deny.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot unsigned-deny", dest.is_file() and dest.stat().st_size > 800)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_artifacts_and_prod_ro() -> None:
    check("page html present", HTML.is_file())
    html = HTML.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html pack attr", 'data-pack="AMG-OCC-TRUTH-1"' in html)
    check(
        "html no invent",
        "invented occupancy" in html.lower() or "No invented occupancy" in html,
    )
    check("html UNKNOWN", "UNKNOWN" in html)
    check("html BLOCKED", "BLOCKED" in html or "blocked" in html.lower())

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "AMG-OCC-TRUTH-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "SOP-LESSON-LIVE-1"
        or arm.get("next_pack_for_parent_only") == "SOP-LESSON-LIVE-1",
    )

    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{PROD_PORT}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        out = ""
    check("prod still listening", str(PROD_PID) in out or "LISTEN" in out, out[:120])
    try:
        os.kill(PROD_PID, 0)
        alive = True
    except (OSError, ProcessLookupError):
        alive = False
    check("prod pid 15975 alive untouched", alive is True)

    names = [
        "amgocctruth1-desk-desktop.png",
        "amgocctruth1-desk-phone.png",
        "amgocctruth1-occ-unknown.png",
        "amgocctruth1-shell-preserved.png",
        "amgocctruth1-unsigned-deny.png",
    ]
    hashes = []
    for name in names:
        path = SHOTS / name
        check(f"shot file {name}", path.is_file() and path.stat().st_size > 800)
        if path.is_file():
            hashes.append(path.read_bytes()[:64])
    if len(hashes) == 5:
        check("shots not identical prefixes", len(set(hashes)) >= 2)


def main() -> int:
    print("=== AMG-OCC-TRUTH-1 pack suite ===")
    test_module_and_honesty()
    test_desk_payload()
    test_amg_os_shell_preserved()
    test_http_api_and_page()
    test_shots()
    test_artifacts_and_prod_ro()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
