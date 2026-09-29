#!/usr/bin/env python3
"""BZG-LABOR-COST-1 — BZG labor cost honesty shell (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack BZG-LABOR-COST-1
(armed 2026-09-30 after FIN-CASH-TRUTH-1 PASS_VERIFIED).

UNKNOWN when no facts. No fake payroll. HR deferred preserved.
Preserves BZG-OPS-DESK-1. Unsigned API/page 403. Writes refused.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain GGV-PIPELINE-TRUTH-1 / HEADCHEF / Exit Report.
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
from core import bzg_labor_cost1 as labor  # noqa: E402
from core import bzg_ops_desk1 as ops  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ZAYEN = "laluzayen@gmail.com"
AMANDA = "amanda@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "BZG-LABOR-COST-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "bzg-labor-cost-1.html"
MODULE = ROOT / "scripts" / "core" / "bzg_labor_cost1.py"
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
    check("page matcher /bzg/labor-cost-1", labor.page_matches("/bzg/labor-cost-1"))
    check("page matcher alias", labor.page_matches("/bzg-labor-cost-1.html"))
    check("page matcher short", labor.page_matches("/bzg/labor-cost"))
    check("api matcher", labor.api_matches("/api/bzg/labor-cost-1"))
    check("api no mutate path", not labor.api_matches("/api/bzg/labor-cost-1/mutate"))

    flags = labor.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("fake_payroll false", flags.get("fake_payroll") is False)
    check("invented_labor_cost false", flags.get("invented_labor_cost") is False)
    check("invented_wages false", flags.get("invented_wages") is False)
    check("invented_headcount false", flags.get("invented_headcount") is False)
    check("payroll_executed false", flags.get("payroll_executed") is False)
    check("payroll_write false", flags.get("payroll_write") is False)
    check("live_payroll false", flags.get("live_payroll") is False)
    check("labor_unknown", flags.get("labor_unknown") is True)
    check("unknown when missing", flags.get("unknown_when_facts_missing") is True)
    check("hr_deferred true", flags.get("hr_deferred") is True)
    check("hr not flipped", flags.get("hr_deferred_not_flipped") is True)
    check("hr preserved flag", flags.get("hr_deferred_preserved") is True)
    check("ops preserved flag", flags.get("bzg_ops_desk1_preserved") is True)
    check("cap proven false", flags.get("cap_bzg_labor_proven") is False)
    check("cap ready false", flags.get("cap_bzg_labor_ready") is False)
    check("ceiling BUILT", flags.get("cap_bzg_labor_ceiling") == "BUILT")
    check("maturity SPECIFIED", flags.get("cap_bzg_labor_maturity") == "SPECIFIED")
    check("amanda deny flag", flags.get("amanda_deny_bzg") is True)
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "GGV-PIPELINE-TRUTH-1")
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("prod pid held const", labor.PROD_PID_HELD == PROD_PID)

    check("Zayen may view", labor.person_may_view("PERS-ZAYEN") is True)
    check("Matt may view", labor.person_may_view("PERS-MATT") is True)
    check("Amanda may NOT", labor.person_may_view("PERS-AMANDA") is False)

    try:
        labor.refuse_fake_payroll({"payroll": True})
        check("refuse_fake_payroll raises", False)
    except labor.BzgLaborCost1Error as exc:
        check("refuse_fake_payroll raises", True)
        check("refuse_fake_payroll code", exc.code == "fake_payroll_refused")
    try:
        labor.refuse_invent_labor({"wage": 1000})
        check("refuse_invent_labor raises", False)
    except labor.BzgLaborCost1Error as exc:
        check("refuse_invent_labor raises", True)
        check("refuse_invent_labor code", exc.code == "invent_labor_refused")

    try:
        labor.refuse_external_write({"payroll": True})
        check("refuse write payroll raises", False)
    except labor.BzgLaborCost1Error as exc:
        check("refuse write payroll", exc.code == "fake_payroll_refused")
    try:
        labor.refuse_external_write({"wage": 5000})
        check("refuse write wage raises", False)
    except labor.BzgLaborCost1Error as exc:
        check("refuse write wage", exc.code == "invent_labor_refused")
    try:
        labor.refuse_external_write({"headcount": 12})
        check("refuse write headcount raises", False)
    except labor.BzgLaborCost1Error as exc:
        check("refuse write headcount", exc.code == "invent_labor_refused")
    try:
        labor.refuse_external_write({"hr_deferred": False})
        check("refuse write hr flip raises", False)
    except labor.BzgLaborCost1Error as exc:
        check("refuse write hr flip", exc.code == "hr_flip_refused")
    try:
        labor.refuse_external_write({"proven": True})
        check("refuse write proven raises", False)
    except labor.BzgLaborCost1Error as exc:
        check("refuse write proven", exc.code == "proven_refused")
    try:
        labor.refuse_external_write({"noop": True})
        check("refuse write generic raises", False)
    except labor.BzgLaborCost1Error as exc:
        check("refuse write generic", exc.code == "write_refused")


def test_desk_payload() -> None:
    payload = labor.build_slice()
    check("ok", payload.get("ok") is True)
    check("payload staff_ready false", payload.get("staff_ready") is False)
    check("payload human_commissioned false", payload.get("human_commissioned") is False)
    check("payload fake_payroll false", payload.get("fake_payroll") is False)
    check("payload invented_labor false", payload.get("invented_labor_cost") is False)
    check("payload payroll_write false", payload.get("payroll_write") is False)
    check("payload live_payroll false", payload.get("live_payroll") is False)
    check("payload labor_unknown", payload.get("labor_unknown") is True)
    check("payload fact_count 0", payload.get("fact_count") == 0)
    check("payload last_success null", payload.get("last_success") is None)
    check("payload hr deferred", payload.get("hr_deferred") is True)
    check("payload hr not flipped", payload.get("hr_deferred_not_flipped") is True)
    check("payload ops preserved", payload.get("bzg_ops_desk1_preserved") is True)
    check("payload cap not proven", payload.get("cap_bzg_labor_proven") is False)
    check("payload ceiling BUILT", payload.get("cap_bzg_labor_ceiling") == "BUILT")
    check("payload next parent", payload.get("next_pack_for_parent_only") == "GGV-PIPELINE-TRUTH-1")
    check("payload no auto-chain", payload.get("cursor_did_not_auto_start_next_pack") is True)

    slots = payload.get("labor_slots") or []
    check("labor slots >= 6", len(slots) >= 6, str(len(slots)))
    check("all labor slots unknown", labor.all_labor_slots_unknown(payload) is True)
    for s in slots:
        check(f"{s['id']} value null", s.get("value") is None)
        check(f"{s['id']} amount null", s.get("amount") is None)
        check(f"{s['id']} fact 0", s.get("fact_count") == 0)
        check(f"{s['id']} no fake payroll", s.get("fake_payroll") is False)
        check(f"{s['id']} not invented", s.get("invented_labor_cost") is False)
        check(f"{s['id']} status unk", s.get("status") in ("EMPTY", "UNKNOWN"))

    hr = payload.get("hr_deferred_stamp") or {}
    check("hr stamp ok", hr.get("ok") is True, str(hr))
    check("hr stamp deferred", hr.get("hr_deferred") is True)
    check("hr stamp status DEFERRED", hr.get("status") == "DEFERRED")

    tiles = {t.get("id") for t in (payload.get("honesty_tiles") or [])}
    for tid in (
        "labor_slots",
        "fake_payroll",
        "hr_deferred",
        "bzg_ops_desk1",
        "cap_bzg_labor",
    ):
        check(f"tile {tid}", tid in tiles)

    links = {l.get("id") for l in (payload.get("desk_links") or [])}
    check("link ops desk", "bzg_ops_desk" in links)
    check("link v1 status", "v1_status" in links)

    schema = labor.schema_document()
    check("schema writes false", schema.get("writes_accepted") is False)
    check("schema fake payroll false", schema.get("fake_payroll") is False)
    check("schema labor value false", schema.get("labor_value_property") is False)
    check("schema hr deferred", schema.get("hr_deferred") is True)

    try:
        labor.build_slice("PERS-AMANDA")
        check("amanda desk raised", False)
    except labor.BzgLaborCost1Error as exc:
        check("amanda desk forbidden", exc.code == "forbidden", f"got={exc.code}")


def test_ops_and_hr_preserved() -> None:
    pin = labor.bzg_ops_desk1_preserved()
    check("ops preserved ok", pin.get("ok") is True, str(pin))
    check("ops invented_sales false", pin.get("invented_sales") is False)
    check("ops master insufficient", pin.get("master_insufficient_facts") is True)

    desk = ops.build_desk("PERS-MATT")
    check("direct ops ok", desk.get("ok") is True)
    check("direct ops staff_ready false", desk.get("staff_ready") is False)
    check("direct ops human_commissioned false", desk.get("human_commissioned") is False)
    flags = ops.honesty_flags()
    check("direct ops invented_sales false", flags.get("invented_sales") is False)

    hr = labor.hr_deferred_stamp()
    check("hr deferred ok", hr.get("ok") is True, str(hr))
    check("hr deferred true", hr.get("hr_deferred") is True)
    check("hr not in queue", hr.get("hr_deferred_not_in_queue") is True)
    check("hr not flipped", hr.get("hr_deferred_not_flipped") is True)


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/bzg/labor-cost-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/bzg/labor-cost-1", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api fake_payroll false", data.get("fake_payroll") is False)
        check("api invented_labor false", data.get("invented_labor_cost") is False)
        check("api labor unknown", data.get("labor_unknown") is True)
        check("api last_success null", data.get("last_success") is None)
        check("api hr deferred", data.get("hr_deferred") is True)
        check("api ops preserved", data.get("bzg_ops_desk1_preserved") is True)
        check("api slots unknown helper", labor.all_labor_slots_unknown(data) is True)

        st, body = call(port, "GET", "/api/bzg/labor-cost-1", email=ZAYEN)
        check("zayen api 200", st == 200, f"status={st}")
        zdata = json.loads(body.decode())
        check("zayen api ok", zdata.get("ok") is True)

        st, body = call(port, "GET", "/api/bzg/labor-cost-1", email=AMANDA)
        check("amanda api 403", st == 403, f"status={st}")
        adata = json.loads(body.decode())
        check("amanda api forbidden", adata.get("error") == "forbidden")
        check("amanda api staff_ready false", adata.get("staff_ready") is False)

        st, _ = call(port, "GET", "/bzg/labor-cost-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/bzg/labor-cost-1", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check(
            "page html labor",
            "labor cost" in text.lower() or "UNKNOWN" in text,
        )
        check("page staff_ready pin", "staff_ready=false" in text)
        check("page human_commissioned pin", "human_commissioned=false" in text)
        check(
            "page no fake payroll",
            "fake payroll" in text.lower() or "No fake payroll" in text,
        )

        st, body = call(port, "GET", "/bzg/labor-cost-1", email=AMANDA)
        check("amanda page deny", st == 403, f"status={st}")
        atext = body.decode(errors="replace")
        check(
            "amanda page deny text",
            "denied" in atext.lower() or "not" in atext.lower() or "Owner" in atext,
        )

        st, _ = call(port, "GET", "/bzg-labor-cost-1", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")

        st, body = call(
            port, "POST", "/api/bzg/labor-cost-1", email=MATT, body={"payroll": True}
        )
        check("post payroll 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post payroll refused code", err.get("error") == "fake_payroll_refused")

        st, body = call(
            port, "POST", "/api/bzg/labor-cost-1", email=MATT, body={"wage": 10000}
        )
        check("post wage 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post wage refused code", err.get("error") == "invent_labor_refused")

        st, body = call(
            port, "POST", "/api/bzg/labor-cost-1", email=MATT, body={"headcount": 8}
        )
        check("post headcount 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post headcount refused code", err.get("error") == "invent_labor_refused")

        st, body = call(
            port, "POST", "/api/bzg/labor-cost-1", email=MATT, body={"hr_deferred": False}
        )
        check("post hr flip 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post hr flip refused code", err.get("error") == "hr_flip_refused")

        st, _ = call(port, "GET", "/api/bzg/ops-desk")
        check("ops unsigned 403", st == 403, f"status={st}")
        st, body = call(port, "GET", "/api/bzg/ops-desk", email=MATT)
        check("ops signed 200", st == 200, f"status={st}")
        ops_data = json.loads(body.decode())
        check("ops still ok", ops_data.get("ok") is True)
        check("ops still staff_ready false", ops_data.get("staff_ready") is False)
        check("ops still no invent sales", (ops_data.get("honesty") or {}).get("invented_sales") is False)
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
            " const fp=document.body && document.body.getAttribute('data-fake-payroll');"
            " const il=document.body && document.body.getAttribute('data-invented-labor');"
            " const lu=document.body && document.body.getAttribute('data-labor-unknown');"
            " const hd=document.body && document.body.getAttribute('data-hr-deferred');"
            " const op=document.body && document.body.getAttribute('data-ops-preserved');"
            " const proven=document.body && document.body.getAttribute('data-cap-proven');"
            " const sr=document.body && document.body.getAttribute('data-staff-ready');"
            " const hc=document.body && document.body.getAttribute('data-human-commissioned');"
            " const t=document.body ? document.body.innerText : '';"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const slots=(document.querySelectorAll('[data-slot]')||[]).length;"
            " const unk=document.querySelector('[data-labor=\"unknown\"]');"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && fp==='0' && il==='0'"
            "  && lu==='1' && hd==='1' && op==='1' && proven==='0' && sr==='0' && hc==='0'"
            "  && stamps>=4 && slots>=6 && !!unk"
            "  && t.includes('UNKNOWN') && ht.includes('staff_ready=false')"
            "  && ht.includes('human_commissioned=false')"
            "  && t.includes('labor cost'),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, slots:slots,"
            " ready:ready, lu:lu, hd:hd, op:op};"
            "})()"
        )
        for width, name in (
            (1024, "bzglaborcost1-desk-desktop.png"),
            (390, "bzglaborcost1-desk-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/bzg/labor-cost-1", desk_expr
            ):
                check(f"desk ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"labor unknown {name}", value.get("lu") == "1")
                    check(f"hr deferred {name}", value.get("hd") == "1")
                    check(f"slots visible {name}", (value.get("slots") or 0) >= 6)
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/bzg/labor-cost-1",
            desk_expr,
        ):
            check("unknown labor shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "bzglaborcost1-labor-unknown.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot labor-unknown", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/bzg/labor-cost-1",
            desk_expr,
        ):
            check("preserved shot ready", bool(value and value.get("ok")), str(value)[:200])
            if value:
                check("ops preserved attr", value.get("op") == "1")
                check("hr deferred attr", value.get("hd") == "1")
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "bzglaborcost1-hr-deferred.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot hr-deferred", dest.is_file() and dest.stat().st_size > 3000)

        deny_expr = (
            "(() => {"
            " const t=document.body ? document.body.innerText : '';"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const deny=document.body && document.body.getAttribute('data-deny');"
            " const statusHint=/403|forbidden|sign.?in|unauthor|denied|identity|Owner/i.test(t);"
            " const notLoaded=ready!=='1';"
            " return {ok: statusHint || notLoaded || deny==='403',"
            " text:t.slice(0,400), ready:ready, deny:deny, statusHint:statusHint};"
            "})()"
        )
        for cdp, _ev, value in _with_cdp(
            1024,
            None,
            f"http://127.0.0.1:{port}/bzg/labor-cost-1",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "bzglaborcost1-unsigned-deny.png"
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
    check("html pack attr", 'data-pack="BZG-LABOR-COST-1"' in html)
    check(
        "html no fake payroll",
        "fake payroll" in html.lower() or "No fake payroll" in html,
    )
    check("html UNKNOWN", "UNKNOWN" in html)
    check("html HR deferred", "HR deferred" in html or "hr deferred" in html.lower())

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "BZG-LABOR-COST-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "GGV-PIPELINE-TRUTH-1"
        or arm.get("next_pack_for_parent_only") == "GGV-PIPELINE-TRUTH-1",
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
        "bzglaborcost1-desk-desktop.png",
        "bzglaborcost1-desk-phone.png",
        "bzglaborcost1-labor-unknown.png",
        "bzglaborcost1-hr-deferred.png",
        "bzglaborcost1-unsigned-deny.png",
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
    print("=== BZG-LABOR-COST-1 pack suite ===")
    test_module_and_honesty()
    test_desk_payload()
    test_ops_and_hr_preserved()
    test_http_api_and_page()
    test_shots()
    test_artifacts_and_prod_ro()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
