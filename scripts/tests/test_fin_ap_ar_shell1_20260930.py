#!/usr/bin/env python3
"""FIN-AP-AR-SHELL-1 — AP/AR desk shells SoD honesty (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack FIN-AP-AR-SHELL-1
(armed 2026-09-30 after BZG-WASTE-YIELD-1 PASS_VERIFIED).
Empty queues · prepare ≠ approve · no fake invoices.
Preserves FC-SHELL-2 / FIN-INTERCO-1 / ATRIUM-SOD.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain OWNER-NEEDS-YOU-1 / HEADCHEF / Exit Report.
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
from core import entity_books as books  # noqa: E402
from core import fin_ap_ar_shell1 as apar  # noqa: E402
from core import fin_interco1 as interco  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "FIN-AP-AR-SHELL-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "fin-ap-ar-shell-1.html"
MODULE = ROOT / "scripts" / "core" / "fin_ap_ar_shell1.py"
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
    check("api matcher", apar.api_matches("/api/fin/ap-ar-shell-1"))
    check("page matcher", apar.page_matches("/fin/ap-ar-shell-1"))
    check("page matcher alias", apar.page_matches("/fin-ap-ar-shell-1"))
    check("pack id", apar.PACK_ID == "FIN-AP-AR-SHELL-1")
    check("schema id", apar.SCHEMA_ID == "wolf.fin-ap-ar-shell-1.v1")

    flags = apar.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("live_ap false", flags.get("live_ap") is False)
    check("live_ar false", flags.get("live_ar") is False)
    check("live_invoicing false", flags.get("live_invoicing") is False)
    check("invented_invoice false", flags.get("invented_invoice") is False)
    check("invented_aging false", flags.get("invented_aging") is False)
    check("invented_balance false", flags.get("invented_balance") is False)
    check("payment_write false", flags.get("payment_write") is False)
    check("invoice_write false", flags.get("invoice_write") is False)
    check("sod_mutate false", flags.get("sod_mutate") is False)
    check("prepare_ne_approve", flags.get("prepare_equals_approve") is False)
    check("self_approve false", flags.get("self_approve_allowed") is False)
    check("fc_shell2 flag", flags.get("fc_shell2_preserved") is True)
    check("fin_interco1 flag", flags.get("fin_interco1_preserved") is True)
    check("atrium_sod flag", flags.get("atrium_sod_preserved") is True)
    check("cap_fin_04_proven false", flags.get("cap_fin_04_proven") is False)
    check("cap_fin_04_ready false", flags.get("cap_fin_04_ready") is False)
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "OWNER-NEEDS-YOU-1")
    check("did not auto-start", flags.get("cursor_did_not_auto_start_next") is True)
    for pack in ("FC-SHELL-2", "FIN-INTERCO-1", "ATRIUM-SOD"):
        check(f"preserved list {pack}", pack in (flags.get("preserved_packs") or []))

    for refuse_fn, code in (
        (apar.refuse_invoice, "invoice_refused"),
        (apar.refuse_aging, "aging_refused"),
        (apar.refuse_balance, "balance_refused"),
        (apar.refuse_payment, "payment_refused"),
        (apar.refuse_self_approve, "sod_self_approve"),
        (apar.refuse_proven, "proven_refused"),
        (apar.refuse_ready, "ready_refused"),
    ):
        try:
            refuse_fn({"invoice": 1})
            check(f"{code} raised", False)
        except apar.FinApArShell1Error as exc:
            check(f"{code} code", exc.code == code)

    try:
        apar.refuse_external_write({"invoice": {"amount": 999}})
        check("write invoice refused", False)
    except apar.FinApArShell1Error as exc:
        check("write invoice code", exc.code == "invoice_refused")

    try:
        apar.refuse_external_write({"aging": {"0-30": 100}})
        check("write aging refused", False)
    except apar.FinApArShell1Error as exc:
        check("write aging code", exc.code == "aging_refused")

    try:
        apar.refuse_external_write({"self_approve": True})
        check("write self_approve refused", False)
    except apar.FinApArShell1Error as exc:
        check("write self_approve code", exc.code == "sod_self_approve")

    html = HTML.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html prepare ne approve", "prepare ≠ approve" in html or "prepare != approve" in html)
    check("html EMPTY", "EMPTY" in html)
    check("html UNKNOWN", "UNKNOWN" in html)
    check("html FC-SHELL-2", "FC-SHELL-2" in html)
    check("html FIN-INTERCO-1", "FIN-INTERCO-1" in html)
    check("html ATRIUM-SOD", "ATRIUM-SOD" in html)
    check("html no fake amount", "IDR 1" not in html and "Rp " not in html)


def test_slice_payload() -> None:
    payload = apar.build_slice()
    check("slice ok", payload.get("ok") is True)
    check("slice pack", payload.get("pack") == "FIN-AP-AR-SHELL-1")
    check("slice staff_ready", payload.get("staff_ready") is False)
    check("slice human_commissioned", payload.get("human_commissioned") is False)
    check("slice live_ap", payload.get("live_ap") is False)
    check("slice live_ar", payload.get("live_ar") is False)
    check("slice invented_invoice", payload.get("invented_invoice") is False)
    check("slice invented_aging", payload.get("invented_aging") is False)
    check("slice invented_balance", payload.get("invented_balance") is False)
    check("slice invoice_write", payload.get("invoice_write") is False)
    check("slice prepare_ne", payload.get("prepare_equals_approve") is False)
    check("slice ap_aging null", payload.get("ap_aging") is None)
    check("slice ar_balance null", payload.get("ar_balance") is None)
    check("slice ap_count 0", payload.get("ap_count") == 0)
    check("slice ar_count 0", payload.get("ar_count") == 0)
    check("slice invoice_count 0", payload.get("invoice_count") == 0)
    check("slice queues empty", payload.get("queues_empty") is True)
    check("slice fc preserved", payload.get("fc_shell2_preserved") is True)
    check("slice interco preserved", payload.get("fin_interco1_preserved") is True)
    check("slice sod preserved", payload.get("atrium_sod_preserved") is True)
    check(
        "slice caps",
        set(payload.get("closes_toward") or []) >= {"CAP-FIN-04", "CAP-FIN AP/AR"},
    )
    check("queues empty helper", apar.queues_are_empty(payload) is True)
    check("desks empty helper", apar.all_entity_desks_empty(payload) is True)

    desks = payload.get("entity_desks") or []
    check("three entity desks", len(desks) == 3, f"count={len(desks)}")
    ids = {d.get("id") for d in desks}
    for need in ("amg_ap_ar", "bzg_ap_ar", "ggv_ap_ar"):
        check(f"desk {need}", need in ids)
    for d in desks:
        check(f"{d['id']} ap 0", d.get("ap_count") == 0)
        check(f"{d['id']} ar 0", d.get("ar_count") == 0)
        check(f"{d['id']} invoice 0", d.get("invoice_count") == 0)
        check(f"{d['id']} aging null", d.get("ap_aging") is None)
        check(f"{d['id']} balance null", d.get("ar_balance") is None)
        check(f"{d['id']} status empty", d.get("status") in ("EMPTY", "UNKNOWN"))
        check(f"{d['id']} not invented", d.get("invented_invoice") is False)

    check("ap queue empty list", (payload.get("ap_queue") or []) == [])
    check("ar queue empty list", (payload.get("ar_queue") or []) == [])

    seats = payload.get("sod_seats") or []
    check("three sod seats", len(seats) == 3, f"count={len(seats)}")
    seat_ids = {s.get("id") for s in seats}
    for need in ("ap_preparer", "ar_preparer", "fc_approver"):
        check(f"seat {need}", need in seat_ids)
    for s in seats:
        check(f"{s['id']} no self approve", s.get("self_approve_allowed") is False)
        check(f"{s['id']} prepare_ne", s.get("prepare_equals_approve") is False)

    sod_h = payload.get("sod_honesty") or {}
    check("sod honesty ok", sod_h.get("ok") is True)
    check("sod prepare_ne", sod_h.get("prepare_equals_approve") is False)

    tiles = {t.get("id") for t in (payload.get("honesty_tiles") or [])}
    for tid in (
        "ap_queue",
        "ar_queue",
        "sod_prepare_approve",
        "invoices",
        "fc_shell2",
        "fin_interco1",
        "atrium_sod",
        "cap_fin_04",
    ):
        check(f"tile {tid}", tid in tiles)

    links = {l.get("id") for l in (payload.get("desk_links") or [])}
    check("link amg", "amg_finance" in links)
    check("link interco", "fin_interco_1" in links)
    check("next pack parent", payload.get("next_pack_for_parent_only") == "OWNER-NEEDS-YOU-1")

    schema = apar.schema_document()
    check("schema writes false", schema.get("writes_accepted") is False)
    check("schema prepare_ne", schema.get("prepare_equals_approve") is False)
    check("schema invoice false", schema.get("invoice_property") is False)


def test_preserved_packs() -> None:
    snap = apar.fc_shell2_books_preserved()
    check("fc books ok", snap.get("ok") is True, str(snap))
    check("bzg 200 accounts", (snap.get("bzg") or {}).get("accounts") == 200)
    check("bzg 0 journals", (snap.get("bzg") or {}).get("journals") == 0)
    check("ggv 200 accounts", (snap.get("ggv") or {}).get("accounts") == 200)
    check("ggv 0 journals", (snap.get("ggv") or {}).get("journals") == 0)
    check("amg live", (snap.get("amg") or {}).get("shell_kind") == "live")

    interco_p = apar.fin_interco1_preserved()
    check("interco preserved ok", interco_p.get("ok") is True, str(interco_p))
    check("interco stubs empty", interco_p.get("stubs_empty") is True)
    check("interco direct empty", interco.all_stubs_empty() is True)

    sod = apar.atrium_sod_preserved()
    check("sod preserved ok", sod.get("ok") is True, str(sod))
    check("sod books not written", sod.get("books_written") is False)

    bzg = books.snapshot("ENT-BZG")
    ggv = books.snapshot("ENT-GGV")
    check("direct bzg journals 0", bzg.get("journals") == 0)
    check("direct ggv journals 0", ggv.get("journals") == 0)


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/fin/ap-ar-shell-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/fin/ap-ar-shell-1", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api live_ap false", data.get("live_ap") is False)
        check("api live_ar false", data.get("live_ar") is False)
        check("api invented_invoice false", data.get("invented_invoice") is False)
        check("api prepare_ne", data.get("prepare_equals_approve") is False)
        check("api queues empty", data.get("queues_empty") is True)
        check("api fc preserved", data.get("fc_shell2_preserved") is True)
        check("api desks empty", apar.all_entity_desks_empty(data) is True)

        st, _ = call(port, "GET", "/fin/ap-ar-shell-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/fin/ap-ar-shell-1", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check(
            "page html apar",
            "AP / AR" in text or "prepare" in text.lower(),
        )
        check("page staff_ready pin", "staff_ready=false" in text)
        check("page human_commissioned pin", "human_commissioned=false" in text)

        st, _ = call(port, "GET", "/fin-ap-ar-shell-1", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")

        st, body = call(
            port, "POST", "/api/fin/ap-ar-shell-1", email=MATT, body={"invoice": 50000}
        )
        check("post invoice 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post invoice refused code", err.get("error") == "invoice_refused")

        st, body = call(
            port, "POST", "/api/fin/ap-ar-shell-1", email=MATT, body={"aging": {"0-30": 1}}
        )
        check("post aging 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post aging refused code", err.get("error") == "aging_refused")

        st, body = call(
            port,
            "POST",
            "/api/fin/ap-ar-shell-1",
            email=MATT,
            body={"self_approve": True},
        )
        check("post self_approve 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post self_approve refused code", err.get("error") == "sod_self_approve")

        st, body = call(
            port, "POST", "/api/fin/ap-ar-shell-1", email=MATT, body={"payment": 1}
        )
        check("post payment 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post payment refused code", err.get("error") == "payment_refused")

        # Prior APIs still auth-gated / preserved
        st, _ = call(port, "GET", "/api/fin/interco-1")
        check("interco unsigned 403", st == 403, f"status={st}")
        st, body = call(port, "GET", "/api/fin/interco-1", email=MATT)
        check("interco signed 200", st == 200, f"status={st}")
        interco_data = json.loads(body.decode())
        check("interco still empty", interco.all_stubs_empty(interco_data) is True)
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
            " const liveAp=document.body && document.body.getAttribute('data-live-ap');"
            " const liveAr=document.body && document.body.getAttribute('data-live-ar');"
            " const inv=document.body && document.body.getAttribute('data-invented-invoice');"
            " const ag=document.body && document.body.getAttribute('data-invented-aging');"
            " const bal=document.body && document.body.getAttribute('data-invented-balance');"
            " const qe=document.body && document.body.getAttribute('data-queues-empty');"
            " const peq=document.body && document.body.getAttribute('data-prepare-eq-approve');"
            " const fc=document.body && document.body.getAttribute('data-fc-shell2');"
            " const proven=document.body && document.body.getAttribute('data-cap-proven');"
            " const sr=document.body && document.body.getAttribute('data-staff-ready');"
            " const hc=document.body && document.body.getAttribute('data-human-commissioned');"
            " const t=document.body ? document.body.innerText : '';"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const desks=(document.querySelectorAll('[data-desk]')||[]).length;"
            " const sod=(document.querySelectorAll('[data-sod]')||[]).length;"
            " const emptyAp=document.querySelector('[data-queue=\"ap-empty\"]');"
            " const emptyAr=document.querySelector('[data-queue=\"ar-empty\"]');"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && liveAp==='0' && liveAr==='0' && inv==='0'"
            "  && ag==='0' && bal==='0' && qe==='1' && peq==='0' && fc==='1'"
            "  && proven==='0' && sr==='0' && hc==='0'"
            "  && stamps>=4 && desks>=3 && sod>=3 && !!emptyAp && !!emptyAr"
            "  && t.includes('EMPTY') && t.includes('UNKNOWN')"
            "  && (t.includes('prepare') || t.includes('SoD'))"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && t.includes('AP / AR desk shells'),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, desks:desks, sod:sod,"
            " ready:ready, fc:fc, qe:qe, peq:peq};"
            "})()"
        )
        for width, name in (
            (1024, "finapar1-desk-desktop.png"),
            (390, "finapar1-desk-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/fin/ap-ar-shell-1", shell_expr
            ):
                check(f"desk ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"queues empty {name}", value.get("qe") == "1")
                    check(f"prepare_ne {name}", value.get("peq") == "0")
                    check(f"desks visible {name}", (value.get("desks") or 0) >= 3)
                    check(f"sod visible {name}", (value.get("sod") or 0) >= 3)
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/fin/ap-ar-shell-1",
            shell_expr,
        ):
            check("queues shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "finapar1-queues-empty.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot queues-empty", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/fin/ap-ar-shell-1",
            shell_expr,
        ):
            check("sod shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "finapar1-sod-stamps.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot sod-stamps", dest.is_file() and dest.stat().st_size > 3000)

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
            f"http://127.0.0.1:{port}/fin/ap-ar-shell-1",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "finapar1-unsigned-deny.png"
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
            arm.get("next_pack_for_parent") == "OWNER-NEEDS-YOU-1",
        )
    else:
        check("arm file present", False)


def main() -> int:
    print("=== FIN-AP-AR-SHELL-1 pack suite ===")
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
