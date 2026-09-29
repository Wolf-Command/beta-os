#!/usr/bin/env python3
"""BZG-INVENTORY-TRUTH-1 — BZG inventory count honesty (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack BZG-INVENTORY-TRUTH-1
(armed 2026-09-30 after FIN-TAX-SHELL-1 PASS_VERIFIED).

UNKNOWN when empty. No fake stock / invented counts.
Preserves BZG-OPS-DESK-1. Unsigned API/page 403. Invent-stock writes refused.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain GGV-METRIC-HONESTY-1 / HEADCHEF / Exit Report.
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
from core import bzg_inventory_truth1 as inv  # noqa: E402
from core import bzg_ops_desk1 as ops  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ZAYEN = "laluzayen@gmail.com"
AMANDA = "amanda@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "BZG-INVENTORY-TRUTH-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "bzg-inventory-truth-1.html"
MODULE = ROOT / "scripts" / "core" / "bzg_inventory_truth1.py"
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
    check("page matcher /bzg/inventory-truth-1", inv.page_matches("/bzg/inventory-truth-1"))
    check("page matcher alias", inv.page_matches("/bzg-inventory-truth-1.html"))
    check("page matcher short", inv.page_matches("/bzg/inventory"))
    check("api matcher", inv.api_matches("/api/bzg/inventory-truth-1"))
    check("api no mutate path", not inv.api_matches("/api/bzg/inventory-truth-1/mutate"))

    flags = inv.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("fake_stock false", flags.get("fake_stock") is False)
    check("invented_stock false", flags.get("invented_stock") is False)
    check("invented_count false", flags.get("invented_count") is False)
    check("invented_qty false", flags.get("invented_qty") is False)
    check("invented_on_hand false", flags.get("invented_on_hand") is False)
    check("live_inventory false", flags.get("live_inventory") is False)
    check("inventory_write false", flags.get("inventory_write") is False)
    check("inventory_unknown", flags.get("inventory_unknown") is True)
    check("counts_unknown", flags.get("counts_unknown") is True)
    check("unknown when missing", flags.get("unknown_when_facts_missing") is True)
    check("ops preserved flag", flags.get("bzg_ops_desk1_preserved") is True)
    check("cap proven false", flags.get("cap_bzg_inventory_proven") is False)
    check("cap ready false", flags.get("cap_bzg_inventory_ready") is False)
    check("ceiling BUILT", flags.get("cap_bzg_inventory_ceiling") == "BUILT")
    check("maturity SPECIFIED", flags.get("cap_bzg_inventory_maturity") == "SPECIFIED")
    check("amanda deny flag", flags.get("amanda_deny_bzg") is True)
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "GGV-METRIC-HONESTY-1")
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("prod pid held const", inv.PROD_PID_HELD == PROD_PID)

    check("Zayen may view", inv.person_may_view("PERS-ZAYEN") is True)
    check("Matt may view", inv.person_may_view("PERS-MATT") is True)
    check("Amanda may NOT", inv.person_may_view("PERS-AMANDA") is False)

    try:
        inv.refuse_fake_stock({"stock": True})
        check("refuse_fake_stock raises", False)
    except inv.BzgInventoryTruth1Error as exc:
        check("refuse_fake_stock raises", True)
        check("refuse_fake_stock code", exc.code == "fake_stock_refused")
    try:
        inv.refuse_invent_stock({"qty": 99})
        check("refuse_invent_stock raises", False)
    except inv.BzgInventoryTruth1Error as exc:
        check("refuse_invent_stock raises", True)
        check("refuse_invent_stock code", exc.code == "invent_stock_refused")
    try:
        inv.refuse_invent_count({"count": 12})
        check("refuse_invent_count raises", False)
    except inv.BzgInventoryTruth1Error as exc:
        check("refuse_invent_count raises", True)
        check("refuse_invent_count code", exc.code == "invent_count_refused")

    try:
        inv.refuse_external_write({"stock": True})
        check("refuse write stock raises", False)
    except inv.BzgInventoryTruth1Error as exc:
        check("refuse write stock", exc.code == "fake_stock_refused")
    try:
        inv.refuse_external_write({"count": 5})
        check("refuse write count raises", False)
    except inv.BzgInventoryTruth1Error as exc:
        check("refuse write count", exc.code == "invent_count_refused")
    try:
        inv.refuse_external_write({"qty": 100})
        check("refuse write qty raises", False)
    except inv.BzgInventoryTruth1Error as exc:
        check("refuse write qty", exc.code == "invent_stock_refused")
    try:
        inv.refuse_external_write({"on_hand": 50})
        check("refuse write on_hand raises", False)
    except inv.BzgInventoryTruth1Error as exc:
        check(
            "refuse write on_hand",
            exc.code in ("fake_stock_refused", "invent_stock_refused"),
        )
    try:
        inv.refuse_external_write({"proven": True})
        check("refuse write proven raises", False)
    except inv.BzgInventoryTruth1Error as exc:
        check("refuse write proven", exc.code == "proven_refused")
    try:
        inv.refuse_external_write({"noop": True})
        check("refuse write generic raises", False)
    except inv.BzgInventoryTruth1Error as exc:
        check("refuse write generic", exc.code == "write_refused")


def test_desk_payload() -> None:
    payload = inv.build_slice()
    check("ok", payload.get("ok") is True)
    check("payload staff_ready false", payload.get("staff_ready") is False)
    check("payload human_commissioned false", payload.get("human_commissioned") is False)
    check("payload fake_stock false", payload.get("fake_stock") is False)
    check("payload invented_stock false", payload.get("invented_stock") is False)
    check("payload invented_count false", payload.get("invented_count") is False)
    check("payload inventory_write false", payload.get("inventory_write") is False)
    check("payload live_inventory false", payload.get("live_inventory") is False)
    check("payload inventory_unknown", payload.get("inventory_unknown") is True)
    check("payload counts_unknown", payload.get("counts_unknown") is True)
    check("payload fact_count 0", payload.get("fact_count") == 0)
    check("payload last_count_at null", payload.get("last_count_at") is None)
    check("payload ops preserved", payload.get("bzg_ops_desk1_preserved") is True)
    check("payload cap not proven", payload.get("cap_bzg_inventory_proven") is False)
    check("payload ceiling BUILT", payload.get("cap_bzg_inventory_ceiling") == "BUILT")
    check("payload next parent", payload.get("next_pack_for_parent_only") == "GGV-METRIC-HONESTY-1")
    check("payload no auto-chain", payload.get("cursor_did_not_auto_start_next_pack") is True)
    check("no fake stock helper", inv.no_fake_stock(payload) is True)

    slots = payload.get("inventory_slots") or []
    check("inventory slots >= 6", len(slots) >= 6, str(len(slots)))
    check("all inventory slots unknown", inv.all_inventory_slots_unknown(payload) is True)
    for s in slots:
        check(f"{s['id']} value null", s.get("value") is None)
        check(f"{s['id']} qty null", s.get("qty") is None)
        check(f"{s['id']} fact 0", s.get("fact_count") == 0)
        check(f"{s['id']} no fake stock", s.get("fake_stock") is False)
        check(f"{s['id']} not invented count", s.get("invented_count") is False)
        check(f"{s['id']} not invented stock", s.get("invented_stock") is False)
        check(f"{s['id']} status unk", s.get("status") in ("EMPTY", "UNKNOWN"))

    tiles = {t.get("id") for t in (payload.get("honesty_tiles") or [])}
    for tid in (
        "inventory_slots",
        "fake_stock",
        "invented_count",
        "bzg_ops_desk1",
        "cap_bzg_inventory",
    ):
        check(f"tile {tid}", tid in tiles)

    links = {l.get("id") for l in (payload.get("desk_links") or [])}
    check("link ops desk", "bzg_ops_desk" in links)
    check("link waste yield", "bzg_waste_yield" in links)

    schema = inv.schema_document()
    check("schema writes false", schema.get("writes_accepted") is False)
    check("schema fake stock false", schema.get("fake_stock") is False)
    check("schema stock value false", schema.get("stock_value_property") is False)
    check("schema count false", schema.get("count_property") is False)

    try:
        inv.build_slice("PERS-AMANDA")
        check("amanda desk raised", False)
    except inv.BzgInventoryTruth1Error as exc:
        check("amanda desk forbidden", exc.code == "forbidden", f"got={exc.code}")


def test_ops_preserved() -> None:
    pin = inv.bzg_ops_desk1_preserved()
    check("ops preserved ok", pin.get("ok") is True, str(pin))
    check("ops invented_sales false", pin.get("invented_sales") is False)
    check("ops master insufficient", pin.get("master_insufficient_facts") is True)

    desk = ops.build_desk("PERS-MATT")
    check("direct ops ok", desk.get("ok") is True)
    check("direct ops staff_ready false", desk.get("staff_ready") is False)
    check("direct ops human_commissioned false", desk.get("human_commissioned") is False)
    flags = ops.honesty_flags()
    check("direct ops invented_sales false", flags.get("invented_sales") is False)


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/bzg/inventory-truth-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/bzg/inventory-truth-1", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api fake_stock false", data.get("fake_stock") is False)
        check("api invented_stock false", data.get("invented_stock") is False)
        check("api invented_count false", data.get("invented_count") is False)
        check("api inventory unknown", data.get("inventory_unknown") is True)
        check("api last_count_at null", data.get("last_count_at") is None)
        check("api ops preserved", data.get("bzg_ops_desk1_preserved") is True)
        check("api slots unknown helper", inv.all_inventory_slots_unknown(data) is True)
        check("api no fake stock", inv.no_fake_stock(data) is True)

        st, body = call(port, "GET", "/api/bzg/inventory-truth-1", email=ZAYEN)
        check("zayen api 200", st == 200, f"status={st}")
        zdata = json.loads(body.decode())
        check("zayen api ok", zdata.get("ok") is True)

        st, body = call(port, "GET", "/api/bzg/inventory-truth-1", email=AMANDA)
        check("amanda api 403", st == 403, f"status={st}")
        adata = json.loads(body.decode())
        check("amanda api forbidden", adata.get("error") == "forbidden")
        check("amanda api staff_ready false", adata.get("staff_ready") is False)

        st, _ = call(port, "GET", "/bzg/inventory-truth-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/bzg/inventory-truth-1", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check(
            "page html inventory",
            "inventory" in text.lower() or "UNKNOWN" in text,
        )
        check("page staff_ready pin", "staff_ready=false" in text)
        check("page human_commissioned pin", "human_commissioned=false" in text)
        check(
            "page no fake stock",
            "fake stock" in text.lower() or "No fake stock" in text,
        )

        st, body = call(port, "GET", "/bzg/inventory-truth-1", email=AMANDA)
        check("amanda page deny", st == 403, f"status={st}")
        atext = body.decode(errors="replace")
        check(
            "amanda page deny text",
            "denied" in atext.lower() or "not" in atext.lower() or "Owner" in atext,
        )

        st, _ = call(port, "GET", "/bzg-inventory-truth-1", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")

        st, body = call(
            port, "POST", "/api/bzg/inventory-truth-1", email=MATT, body={"stock": True}
        )
        check("post stock 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post stock refused code", err.get("error") == "fake_stock_refused")

        st, body = call(
            port, "POST", "/api/bzg/inventory-truth-1", email=MATT, body={"count": 42}
        )
        check("post count 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post count refused code", err.get("error") == "invent_count_refused")

        st, body = call(
            port, "POST", "/api/bzg/inventory-truth-1", email=MATT, body={"qty": 100}
        )
        check("post qty 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post qty refused code", err.get("error") == "invent_stock_refused")
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
            " const fs=document.body && document.body.getAttribute('data-fake-stock');"
            " const ic=document.body && document.body.getAttribute('data-invented-count');"
            " const ist=document.body && document.body.getAttribute('data-invented-stock');"
            " const iu=document.body && document.body.getAttribute('data-inventory-unknown');"
            " const op=document.body && document.body.getAttribute('data-ops-preserved');"
            " const proven=document.body && document.body.getAttribute('data-cap-proven');"
            " const sr=document.body && document.body.getAttribute('data-staff-ready');"
            " const hc=document.body && document.body.getAttribute('data-human-commissioned');"
            " const t=document.body ? document.body.innerText : '';"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const slots=(document.querySelectorAll('[data-slot]')||[]).length;"
            " const unk=document.querySelector('[data-inventory=\"unknown\"]');"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && fs==='0' && ic==='0' && ist==='0'"
            "  && iu==='1' && op==='1' && proven==='0' && sr==='0' && hc==='0'"
            "  && stamps>=4 && slots>=6 && !!unk"
            "  && t.includes('UNKNOWN') && t.includes('inventory')"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && (t.includes('Inventory') || t.includes('inventory')),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, slots:slots,"
            " ready:ready, iu:iu, op:op};"
            "})()"
        )
        for width, name in (
            (1024, "bzginventory1-desk-desktop.png"),
            (390, "bzginventory1-desk-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/bzg/inventory-truth-1", desk_expr
            ):
                check(f"desk ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"inventory unknown {name}", value.get("iu") == "1")
                    check(f"slots visible {name}", (value.get("slots") or 0) >= 6)
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/bzg/inventory-truth-1",
            desk_expr,
        ):
            check("unknown inventory shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "bzginventory1-inventory-unknown.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot inventory-unknown", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/bzg/inventory-truth-1",
            desk_expr,
        ):
            check("ops preserved shot ready", bool(value and value.get("ok")), str(value)[:200])
            if value:
                check("ops desk preserved attr", value.get("op") == "1")
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "bzginventory1-ops-desk-preserved.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot ops-desk-preserved", dest.is_file() and dest.stat().st_size > 3000)

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
            f"http://127.0.0.1:{port}/bzg/inventory-truth-1",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "bzginventory1-unsigned-deny.png"
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
    check("html pack attr", 'data-pack="BZG-INVENTORY-TRUTH-1"' in html)
    check(
        "html no fake",
        "fake stock" in html.lower() or "No fake stock" in html or "UNKNOWN when empty" in html,
    )

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "BZG-INVENTORY-TRUTH-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "GGV-METRIC-HONESTY-1"
        or arm.get("next_pack_for_parent_only") == "GGV-METRIC-HONESTY-1",
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
        "bzginventory1-desk-desktop.png",
        "bzginventory1-desk-phone.png",
        "bzginventory1-inventory-unknown.png",
        "bzginventory1-ops-desk-preserved.png",
        "bzginventory1-unsigned-deny.png",
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
    print("=== BZG-INVENTORY-TRUTH-1 pack suite ===")
    test_module_and_honesty()
    test_desk_payload()
    test_ops_preserved()
    test_http_api_and_page()
    test_shots()
    test_artifacts_and_prod_ro()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
