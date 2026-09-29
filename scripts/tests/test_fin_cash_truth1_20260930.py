#!/usr/bin/env python3
"""FIN-CASH-TRUTH-1 — cash / bank truth desk deepen (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack FIN-CASH-TRUTH-1
(armed 2026-09-30 after BACKUP-HEALTH-1 PASS_VERIFIED).

File-import only. Empty/UNKNOWN when no import. No fake balances / scrape invent.
Preserves FIN-RECON-SHELL-1. Unsigned API/page 403. Writes refused.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain BZG-LABOR-COST-1 / HEADCHEF / Exit Report.
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
from core import fin_cash_truth1 as cash  # noqa: E402
from core import fin_recon_shell1 as recon  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "FIN-CASH-TRUTH-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "fin-cash-truth-1.html"
MODULE = ROOT / "scripts" / "core" / "fin_cash_truth1.py"
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
    check("page matcher /fin/cash-truth-1", cash.page_matches("/fin/cash-truth-1"))
    check("page matcher alias", cash.page_matches("/fin-cash-truth-1.html"))
    check("page matcher short", cash.page_matches("/fin/cash-truth"))
    check("api matcher", cash.api_matches("/api/fin/cash-truth-1"))
    check("api no mutate path", not cash.api_matches("/api/fin/cash-truth-1/mutate"))

    flags = cash.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("invented_balance false", flags.get("invented_balance") is False)
    check("invented_scrape false", flags.get("invented_scrape") is False)
    check("live_scrape false", flags.get("live_scrape") is False)
    check("live_cash false", flags.get("live_cash") is False)
    check("bank_api false", flags.get("bank_api") is False)
    check("payment_write false", flags.get("payment_write") is False)
    check("file_import_only", flags.get("file_import_only") is True)
    check("balances_unknown", flags.get("balances_unknown") is True)
    check("fin_recon preserved flag", flags.get("fin_recon_shell1_preserved") is True)
    check("fc_shell2 preserved flag", flags.get("fc_shell2_preserved") is True)
    check("cap_fin_cash_proven false", flags.get("cap_fin_cash_proven") is False)
    check("cap_fin_cash_ready false", flags.get("cap_fin_cash_ready") is False)
    check("ceiling BUILT", flags.get("cap_fin_cash_ceiling") == "BUILT")
    check("maturity SPECIFIED", flags.get("cap_fin_cash_maturity") == "SPECIFIED")
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "BZG-LABOR-COST-1")
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("prod pid held const", cash.PROD_PID_HELD == PROD_PID)

    try:
        cash.refuse_invent_balance({"balance": 999})
        check("refuse_invent_balance raises", False)
    except cash.FinCashTruth1Error as exc:
        check("refuse_invent_balance raises", True)
        check("refuse_invent_balance code", exc.code == "invent_balance_refused")
    try:
        cash.refuse_live_scrape({"scrape": True})
        check("refuse_live_scrape raises", False)
    except cash.FinCashTruth1Error as exc:
        check("refuse_live_scrape raises", True)
        check("refuse_live_scrape code", exc.code == "scrape_refused")

    try:
        cash.refuse_external_write({"balance": 1000})
        check("refuse write balance raises", False)
    except cash.FinCashTruth1Error as exc:
        check("refuse write balance", exc.code == "invent_balance_refused")
    try:
        cash.refuse_external_write({"scrape": "live"})
        check("refuse write scrape raises", False)
    except cash.FinCashTruth1Error as exc:
        check("refuse write scrape", exc.code == "scrape_refused")
    try:
        cash.refuse_external_write({"payment": 1})
        check("refuse write payment raises", False)
    except cash.FinCashTruth1Error as exc:
        check("refuse write payment", exc.code == "payment_refused")
    try:
        cash.refuse_external_write({"bank": "mutate"})
        check("refuse write bank raises", False)
    except cash.FinCashTruth1Error as exc:
        check("refuse write bank", exc.code == "bank_write_refused")
    try:
        cash.refuse_external_write({"proven": True})
        check("refuse write proven raises", False)
    except cash.FinCashTruth1Error as exc:
        check("refuse write proven", exc.code == "proven_refused")
    try:
        cash.refuse_external_write({"noop": True})
        check("refuse write generic raises", False)
    except cash.FinCashTruth1Error as exc:
        check("refuse write generic", exc.code == "write_refused")


def test_desk_payload() -> None:
    payload = cash.build_slice()
    check("ok", payload.get("ok") is True)
    check("payload staff_ready false", payload.get("staff_ready") is False)
    check("payload human_commissioned false", payload.get("human_commissioned") is False)
    check("payload invented_balance false", payload.get("invented_balance") is False)
    check("payload invented_scrape false", payload.get("invented_scrape") is False)
    check("payload live_scrape false", payload.get("live_scrape") is False)
    check("payload live_cash false", payload.get("live_cash") is False)
    check("payload bank_api false", payload.get("bank_api") is False)
    check("payload payment_write false", payload.get("payment_write") is False)
    check("payload fio", payload.get("file_import_only") is True)
    check("payload positions_unknown", payload.get("positions_unknown") is True)
    check("payload import_count 0", payload.get("import_count") == 0)
    check("payload last_success null", payload.get("last_success") is None)
    check("payload fin_recon preserved", payload.get("fin_recon_shell1_preserved") is True)
    check("payload fc_shell2 preserved", payload.get("fc_shell2_preserved") is True)
    check("payload cap_fin_cash not proven", payload.get("cap_fin_cash_proven") is False)
    check("payload ceiling BUILT", payload.get("cap_fin_cash_ceiling") == "BUILT")
    check("payload next parent", payload.get("next_pack_for_parent_only") == "BZG-LABOR-COST-1")
    check("payload no auto-chain", payload.get("cursor_did_not_auto_start_next_pack") is True)

    positions = payload.get("cash_positions") or []
    check("cash positions >= 3", len(positions) >= 3, str(len(positions)))
    check("all cash positions unknown", cash.all_cash_positions_unknown(payload) is True)
    for s in positions:
        check(f"{s['id']} balance null", s.get("balance") is None)
        check(f"{s['id']} cash_on_hand null", s.get("cash_on_hand") is None)
        check(f"{s['id']} bank_available null", s.get("bank_available") is None)
        check(f"{s['id']} import 0", s.get("import_count") == 0)
        check(f"{s['id']} no scrape", s.get("live_scrape") is False)
        check(f"{s['id']} not invented", s.get("invented_balance") is False)
        check(f"{s['id']} fio", s.get("file_import_only") is True)
        check(f"{s['id']} status unk", s.get("status") in ("EMPTY", "UNKNOWN"))

    accounts = payload.get("account_stubs") or []
    check("account stubs >= 3", len(accounts) >= 3, str(len(accounts)))
    for b in accounts:
        check(f"acct {b['id']} balance null", b.get("balance") is None)
        check(f"acct {b['id']} fio", b.get("file_import_only") is True)

    bank = payload.get("bank_path") or {}
    check("bank FILE_IMPORT_ONLY", bank.get("probe_status") == "FILE_IMPORT_ONLY")
    check("bank last_success null", bank.get("last_success") is None)

    tiles = {t.get("id") for t in (payload.get("honesty_tiles") or [])}
    for tid in (
        "cash_positions",
        "bank_path",
        "invented_balance",
        "fin_recon_shell1",
        "fc_shell2",
        "cap_fin_cash",
    ):
        check(f"tile {tid}", tid in tiles)

    links = {l.get("id") for l in (payload.get("desk_links") or [])}
    check("link recon", "fin_recon_shell_1" in links)
    check("link intg", "integrations_status" in links)

    schema = cash.schema_document()
    check("schema writes false", schema.get("writes_accepted") is False)
    check("schema fio", schema.get("file_import_only") is True)
    check("schema balance false", schema.get("balance_property") is False)
    check("schema scrape false", schema.get("scrape_property") is False)


def test_fin_recon_preserved() -> None:
    pin = cash.fin_recon_shell1_preserved()
    check("recon preserved ok", pin.get("ok") is True, str(pin))
    check("recon queue empty", pin.get("queue_empty") is True)
    check("recon fio", pin.get("file_import_only") is True)
    check("recon last_success null", pin.get("last_success") is None)
    check("recon no invent balance", pin.get("invented_balance") is False)

    books = cash.fc_shell2_books_preserved()
    check("fc books ok", books.get("ok") is True, str(books))

    slice_ = recon.build_slice()
    check("direct recon ok", slice_.get("ok") is True)
    check("direct recon queue empty", recon.queue_is_empty(slice_) is True)
    check("direct recon accounts empty", recon.all_account_stubs_empty(slice_) is True)
    check("direct recon fio", slice_.get("file_import_only") is True)
    check("direct recon invented_balance false", slice_.get("invented_balance") is False)


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/fin/cash-truth-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/fin/cash-truth-1", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api fio", data.get("file_import_only") is True)
        check("api invented_balance false", data.get("invented_balance") is False)
        check("api invented_scrape false", data.get("invented_scrape") is False)
        check("api live scrape false", data.get("live_scrape") is False)
        check("api positions unknown", data.get("positions_unknown") is True)
        check("api last_success null", data.get("last_success") is None)
        check("api fin recon preserved", data.get("fin_recon_shell1_preserved") is True)
        check("api positions unknown helper", cash.all_cash_positions_unknown(data) is True)

        st, _ = call(port, "GET", "/fin/cash-truth-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/fin/cash-truth-1", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check(
            "page html cash",
            "Cash / bank truth" in text or "FILE_IMPORT_ONLY" in text,
        )
        check("page staff_ready pin", "staff_ready=false" in text)
        check("page human_commissioned pin", "human_commissioned=false" in text)
        check(
            "page no invent",
            "invented balances" in text.lower() or "No invented balances" in text,
        )

        st, _ = call(port, "GET", "/fin-cash-truth-1", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")

        st, body = call(
            port, "POST", "/api/fin/cash-truth-1", email=MATT, body={"balance": 50000}
        )
        check("post balance 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post balance refused code", err.get("error") == "invent_balance_refused")

        st, body = call(
            port, "POST", "/api/fin/cash-truth-1", email=MATT, body={"scrape": "live"}
        )
        check("post scrape 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post scrape refused code", err.get("error") == "scrape_refused")

        st, body = call(
            port, "POST", "/api/fin/cash-truth-1", email=MATT, body={"payment": 1}
        )
        check("post payment 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post payment refused code", err.get("error") == "payment_refused")

        st, body = call(
            port, "POST", "/api/fin/cash-truth-1", email=MATT, body={"bank": "mutate"}
        )
        check("post bank 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post bank refused code", err.get("error") == "bank_write_refused")

        st, _ = call(port, "GET", "/api/fin/recon-shell-1")
        check("recon unsigned 403", st == 403, f"status={st}")
        st, body = call(port, "GET", "/api/fin/recon-shell-1", email=MATT)
        check("recon signed 200", st == 200, f"status={st}")
        recon_data = json.loads(body.decode())
        check("recon still empty", recon.queue_is_empty(recon_data) is True)
        check("recon still fio", recon_data.get("file_import_only") is True)
        check("recon still no invent balance", recon_data.get("invented_balance") is False)
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
            " const live=document.body && document.body.getAttribute('data-live-cash');"
            " const bal=document.body && document.body.getAttribute('data-invented-balance');"
            " const sc=document.body && document.body.getAttribute('data-invented-scrape');"
            " const fio=document.body && document.body.getAttribute('data-file-import-only');"
            " const pu=document.body && document.body.getAttribute('data-positions-unknown');"
            " const rp=document.body && document.body.getAttribute('data-recon-preserved');"
            " const proven=document.body && document.body.getAttribute('data-cap-proven');"
            " const sr=document.body && document.body.getAttribute('data-staff-ready');"
            " const hc=document.body && document.body.getAttribute('data-human-commissioned');"
            " const t=document.body ? document.body.innerText : '';"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const pos=(document.querySelectorAll('[data-position]')||[]).length;"
            " const stubs=(document.querySelectorAll('[data-stub]')||[]).length;"
            " const unk=document.querySelector('[data-positions=\"unknown\"]');"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && live==='0' && bal==='0' && sc==='0'"
            "  && fio==='1' && pu==='1' && rp==='1' && proven==='0' && sr==='0' && hc==='0'"
            "  && stamps>=4 && pos>=3 && stubs>=3 && !!unk"
            "  && t.includes('UNKNOWN') && t.includes('FILE_IMPORT_ONLY')"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && t.includes('Cash / bank truth desk'),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, pos:pos, stubs:stubs,"
            " ready:ready, fio:fio, pu:pu, rp:rp};"
            "})()"
        )
        for width, name in (
            (1024, "fincashtruth1-desk-desktop.png"),
            (390, "fincashtruth1-desk-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/fin/cash-truth-1", desk_expr
            ):
                check(f"desk ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"fio attr {name}", value.get("fio") == "1")
                    check(f"positions unknown {name}", value.get("pu") == "1")
                    check(f"positions visible {name}", (value.get("pos") or 0) >= 3)
                    check(f"stubs visible {name}", (value.get("stubs") or 0) >= 3)
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/fin/cash-truth-1",
            desk_expr,
        ):
            check("unknown cash shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "fincashtruth1-cash-unknown.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot cash-unknown", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/fin/cash-truth-1",
            desk_expr,
        ):
            check("preserved shot ready", bool(value and value.get("ok")), str(value)[:200])
            if value:
                check("fin recon preserved attr", value.get("rp") == "1")
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "fincashtruth1-recon-preserved.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot recon-preserved", dest.is_file() and dest.stat().st_size > 3000)

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
            f"http://127.0.0.1:{port}/fin/cash-truth-1",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "fincashtruth1-unsigned-deny.png"
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
    check("html pack attr", 'data-pack="FIN-CASH-TRUTH-1"' in html)
    check(
        "html no invent",
        "invented balances" in html.lower() or "No invented balances" in html,
    )
    check("html fio", "FILE_IMPORT_ONLY" in html)

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "FIN-CASH-TRUTH-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "BZG-LABOR-COST-1"
        or arm.get("next_pack_for_parent_only") == "BZG-LABOR-COST-1",
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
        "fincashtruth1-desk-desktop.png",
        "fincashtruth1-desk-phone.png",
        "fincashtruth1-cash-unknown.png",
        "fincashtruth1-recon-preserved.png",
        "fincashtruth1-unsigned-deny.png",
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
    print("=== FIN-CASH-TRUTH-1 pack suite ===")
    test_module_and_honesty()
    test_desk_payload()
    test_fin_recon_preserved()
    test_http_api_and_page()
    test_shots()
    test_artifacts_and_prod_ro()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
