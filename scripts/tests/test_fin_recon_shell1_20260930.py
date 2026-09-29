#!/usr/bin/env python3
"""FIN-RECON-SHELL-1 — bank file-import recon shell (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack FIN-RECON-SHELL-1
(armed 2026-09-30 after BZG-OPS-DESK-1 PASS_VERIFIED).
FILE_IMPORT_ONLY · empty/UNKNOWN when no imports · last_success null.
No payment write. Preserves FC-SHELL-2 / FIN-INTERCO-1 / ATRIUM-SOD.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain DASH-LIVE-1 / HEADCHEF / Exit Report.
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
from core import fin_interco1 as interco  # noqa: E402
from core import fin_recon_shell1 as recon  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "FIN-RECON-SHELL-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "fin-recon-shell-1.html"
MODULE = ROOT / "scripts" / "core" / "fin_recon_shell1.py"
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
    check("api matcher", recon.api_matches("/api/fin/recon-shell-1"))
    check("page matcher", recon.page_matches("/fin/recon-shell-1"))
    check("page matcher alias", recon.page_matches("/fin-recon-shell-1"))
    check("pack id", recon.PACK_ID == "FIN-RECON-SHELL-1")
    check("schema id", recon.SCHEMA_ID == "wolf.fin-recon-shell-1.v1")

    flags = recon.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("live_recon false", flags.get("live_recon") is False)
    check("file_import_only", flags.get("file_import_only") is True)
    check("invented_import false", flags.get("invented_import") is False)
    check("invented_last_success false", flags.get("invented_last_success") is False)
    check("invented_statement_feed false", flags.get("invented_statement_feed") is False)
    check("payment_executed false", flags.get("payment_executed") is False)
    check("payment_write false", flags.get("payment_write") is False)
    check("bank_write false", flags.get("bank_write") is False)
    check("bank_api false", flags.get("bank_api") is False)
    check("books_write false", flags.get("books_write") is False)
    check("last_success_null", flags.get("last_success_null") is True)
    check("fc_shell2 flag", flags.get("fc_shell2_preserved") is True)
    check("fin_interco1 flag", flags.get("fin_interco1_preserved") is True)
    check("atrium_sod flag", flags.get("atrium_sod_preserved") is True)
    check("cap_fin_02_proven false", flags.get("cap_fin_02_proven") is False)
    check("cap_fin_02_ready false", flags.get("cap_fin_02_ready") is False)
    check("cap_fin_08 not closed", flags.get("cap_fin_08_closed_by_this_pack") is False)
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "DASH-LIVE-1")
    check("did not auto-start", flags.get("cursor_did_not_auto_start_next") is True)
    for pack in ("FC-SHELL-2", "FIN-INTERCO-1", "ATRIUM-SOD"):
        check(f"preserved list {pack}", pack in (flags.get("preserved_packs") or []))

    for refuse_fn, code in (
        (recon.refuse_payment, "payment_refused"),
        (recon.refuse_bank_write, "bank_write_refused"),
        (recon.refuse_invented_feed, "feed_refused"),
        (recon.refuse_balance, "balance_refused"),
        (recon.refuse_proven, "proven_refused"),
        (recon.refuse_ready, "ready_refused"),
    ):
        try:
            refuse_fn({"payment": 1})
            check(f"{code} raised", False)
        except recon.FinReconShell1Error as exc:
            check(f"{code} code", exc.code == code)

    try:
        recon.refuse_external_write({"payment": 999})
        check("write payment refused", False)
    except recon.FinReconShell1Error as exc:
        check("write payment code", exc.code == "payment_refused")

    try:
        recon.refuse_external_write({"last_success": "2026-09-30T00:00:00+08:00"})
        check("write last_success refused", False)
    except recon.FinReconShell1Error as exc:
        check("write last_success code", exc.code == "feed_refused")

    html = HTML.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html FILE_IMPORT_ONLY", "FILE_IMPORT_ONLY" in html)
    check("html EMPTY", "EMPTY" in html)
    check("html UNKNOWN", "UNKNOWN" in html)
    check("html last_success=null", "last_success=null" in html)
    check("html FC-SHELL-2", "FC-SHELL-2" in html)
    check("html FIN-INTERCO-1", "FIN-INTERCO-1" in html)
    check("html ATRIUM-SOD", "ATRIUM-SOD" in html)
    check("html no fake amount", "IDR 1" not in html and "Rp " not in html)


def test_slice_payload() -> None:
    payload = recon.build_slice()
    check("slice ok", payload.get("ok") is True)
    check("slice pack", payload.get("pack") == "FIN-RECON-SHELL-1")
    check("slice staff_ready", payload.get("staff_ready") is False)
    check("slice human_commissioned", payload.get("human_commissioned") is False)
    check("slice live_recon", payload.get("live_recon") is False)
    check("slice file_import_only", payload.get("file_import_only") is True)
    check("slice invented_import", payload.get("invented_import") is False)
    check("slice invented_last_success", payload.get("invented_last_success") is False)
    check("slice payment_write", payload.get("payment_write") is False)
    check("slice bank_api", payload.get("bank_api") is False)
    check("slice last_success null", payload.get("last_success") is None)
    check("slice import_count 0", payload.get("import_count") == 0)
    check("slice queue empty", payload.get("queue_empty") is True)
    check("slice fc preserved", payload.get("fc_shell2_preserved") is True)
    check("slice interco preserved", payload.get("fin_interco1_preserved") is True)
    check("slice sod preserved", payload.get("atrium_sod_preserved") is True)
    check("slice caps", set(payload.get("closes_toward") or []) >= {"CAP-FIN-02", "INT-BANK"})
    check("queue empty helper", recon.queue_is_empty(payload) is True)
    check("accounts empty helper", recon.all_account_stubs_empty(payload) is True)

    stubs = payload.get("account_stubs") or []
    check("three account stubs", len(stubs) == 3, f"count={len(stubs)}")
    ids = {s.get("id") for s in stubs}
    for need in ("mandiri_ggv", "bni_amg", "bri_bzg"):
        check(f"stub {need}", need in ids)
    for s in stubs:
        check(f"{s['id']} import 0", s.get("import_count") == 0)
        check(f"{s['id']} balance null", s.get("balance") is None)
        check(f"{s['id']} last_success null", s.get("last_success") is None)
        check(f"{s['id']} payment null", s.get("payment") is None)
        check(f"{s['id']} status empty", s.get("status") in ("EMPTY", "UNKNOWN"))
        check(f"{s['id']} fio", s.get("file_import_only") is True)
        check(f"{s['id']} not invented", s.get("invented_import") is False)

    queue = payload.get("recon_queue") or []
    check("recon queue empty list", queue == [])

    bank = payload.get("bank_path") or {}
    check("bank FILE_IMPORT_ONLY", bank.get("probe_status") == "FILE_IMPORT_ONLY")
    check("bank last_success null", bank.get("last_success") is None)

    tiles = {t.get("id") for t in (payload.get("honesty_tiles") or [])}
    for tid in (
        "recon_queue",
        "bank_path",
        "last_success",
        "balances",
        "fc_shell2",
        "fin_interco1",
        "atrium_sod",
        "cap_fin_02",
    ):
        check(f"tile {tid}", tid in tiles)

    links = {l.get("id") for l in (payload.get("desk_links") or [])}
    check("link intg", "integrations_status" in links)
    check("link interco", "fin_interco_1" in links)
    check("next pack parent", payload.get("next_pack_for_parent_only") == "DASH-LIVE-1")

    schema = recon.schema_document()
    check("schema writes false", schema.get("writes_accepted") is False)
    check("schema fio", schema.get("file_import_only") is True)
    check("schema last_success false", schema.get("last_success_property") is False)


def test_preserved_packs() -> None:
    snap = recon.fc_shell2_books_preserved()
    check("fc books ok", snap.get("ok") is True, str(snap))
    check("bzg 200 accounts", (snap.get("bzg") or {}).get("accounts") == 200)
    check("bzg 0 journals", (snap.get("bzg") or {}).get("journals") == 0)
    check("ggv 200 accounts", (snap.get("ggv") or {}).get("accounts") == 200)
    check("ggv 0 journals", (snap.get("ggv") or {}).get("journals") == 0)
    check("amg live", (snap.get("amg") or {}).get("shell_kind") == "live")

    interco_p = recon.fin_interco1_preserved()
    check("interco preserved ok", interco_p.get("ok") is True, str(interco_p))
    check("interco stubs empty", interco_p.get("stubs_empty") is True)
    check("interco direct empty", interco.all_stubs_empty() is True)

    sod = recon.atrium_sod_preserved()
    check("sod preserved ok", sod.get("ok") is True, str(sod))
    check("sod books not written", sod.get("books_written") is False)

    bzg = books.snapshot("ENT-BZG")
    ggv = books.snapshot("ENT-GGV")
    check("direct bzg journals 0", bzg.get("journals") == 0)
    check("direct ggv journals 0", ggv.get("journals") == 0)


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/fin/recon-shell-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/fin/recon-shell-1", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api live_recon false", data.get("live_recon") is False)
        check("api fio", data.get("file_import_only") is True)
        check("api invented_import false", data.get("invented_import") is False)
        check("api invented_last_success false", data.get("invented_last_success") is False)
        check("api last_success null", data.get("last_success") is None)
        check("api queue empty", data.get("queue_empty") is True)
        check("api fc preserved", data.get("fc_shell2_preserved") is True)
        check("api accounts empty", recon.all_account_stubs_empty(data) is True)

        st, _ = call(port, "GET", "/fin/recon-shell-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/fin/recon-shell-1", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check(
            "page html recon",
            "reconcil" in text.lower() or "FILE_IMPORT_ONLY" in text,
        )
        check("page staff_ready pin", "staff_ready=false" in text)
        check("page human_commissioned pin", "human_commissioned=false" in text)

        st, _ = call(port, "GET", "/fin-recon-shell-1", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")

        st, body = call(
            port, "POST", "/api/fin/recon-shell-1", email=MATT, body={"payment": 50000}
        )
        check("post payment 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post payment refused code", err.get("error") == "payment_refused")

        st, body = call(
            port,
            "POST",
            "/api/fin/recon-shell-1",
            email=MATT,
            body={"last_success": "2026-09-30T12:00:00+08:00"},
        )
        check("post last_success 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post last_success refused code", err.get("error") == "feed_refused")

        st, body = call(
            port, "POST", "/api/fin/recon-shell-1", email=MATT, body={"bank": "mutate"}
        )
        check("post bank 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post bank refused code", err.get("error") == "bank_write_refused")

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
            " const live=document.body && document.body.getAttribute('data-live-recon');"
            " const imp=document.body && document.body.getAttribute('data-invented-import');"
            " const ls=document.body && document.body.getAttribute('data-invented-last-success');"
            " const fio=document.body && document.body.getAttribute('data-file-import-only');"
            " const qe=document.body && document.body.getAttribute('data-queue-empty');"
            " const fc=document.body && document.body.getAttribute('data-fc-shell2');"
            " const proven=document.body && document.body.getAttribute('data-cap-proven');"
            " const sr=document.body && document.body.getAttribute('data-staff-ready');"
            " const hc=document.body && document.body.getAttribute('data-human-commissioned');"
            " const t=document.body ? document.body.innerText : '';"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const stubs=(document.querySelectorAll('[data-stub]')||[]).length;"
            " const emptyQ=document.querySelector('[data-queue=\"empty\"]');"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && live==='0' && imp==='0' && ls==='0'"
            "  && fio==='1' && qe==='1' && fc==='1' && proven==='0' && sr==='0' && hc==='0'"
            "  && stamps>=4 && stubs>=3 && !!emptyQ"
            "  && t.includes('EMPTY') && t.includes('UNKNOWN')"
            "  && t.includes('FILE_IMPORT_ONLY')"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && t.includes('Bank reconciliation shell'),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, stubs:stubs,"
            " ready:ready, fc:fc, fio:fio, qe:qe};"
            "})()"
        )
        for width, name in (
            (1024, "finreconshell1-desk-desktop.png"),
            (390, "finreconshell1-desk-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/fin/recon-shell-1", shell_expr
            ):
                check(f"desk ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"fio attr {name}", value.get("fio") == "1")
                    check(f"queue empty {name}", value.get("qe") == "1")
                    check(f"stubs visible {name}", (value.get("stubs") or 0) >= 3)
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/fin/recon-shell-1",
            shell_expr,
        ):
            check("queue shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "finreconshell1-queue-empty.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot queue-empty", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/fin/recon-shell-1",
            shell_expr,
        ):
            check("preserved shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "finreconshell1-preserved-packs.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot preserved", dest.is_file() and dest.stat().st_size > 3000)

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
            f"http://127.0.0.1:{port}/fin/recon-shell-1",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "finreconshell1-unsigned-deny.png"
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
    else:
        check("arm file present", False)


def main() -> int:
    print("=== FIN-RECON-SHELL-1 pack suite ===")
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
