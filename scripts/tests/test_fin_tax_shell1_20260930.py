#!/usr/bin/env python3
"""FIN-TAX-SHELL-1 — tax calendar shell honesty (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack FIN-TAX-SHELL-1
(armed 2026-09-30 after SOP-LESSON-LIVE-1 PASS_VERIFIED).

UNKNOWN until facts. No fake filings / invented tax due amounts.
Preserves FC-SHELL-2. Unsigned API/page 403. Invent-filing writes refused.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain BZG-INVENTORY-TRUTH-1 / HEADCHEF / Exit Report.
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
from core import fin_tax_shell1 as tax  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "FIN-TAX-SHELL-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "fin-tax-shell-1.html"
MODULE = ROOT / "scripts" / "core" / "fin_tax_shell1.py"
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
    check("page matcher /fin/tax-shell-1", tax.page_matches("/fin/tax-shell-1"))
    check("page matcher alias", tax.page_matches("/fin-tax-shell-1.html"))
    check("page matcher short", tax.page_matches("/fin/tax-shell"))
    check("api matcher", tax.api_matches("/api/fin/tax-shell-1"))
    check("api no mutate path", not tax.api_matches("/api/fin/tax-shell-1/mutate"))

    flags = tax.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("invented_filing false", flags.get("invented_filing") is False)
    check("invented_amount false", flags.get("invented_amount") is False)
    check("fake_filings false", flags.get("fake_filings") is False)
    check("fake_tax_amounts false", flags.get("fake_tax_amounts") is False)
    check("live_filing false", flags.get("live_filing") is False)
    check("live_tax false", flags.get("live_tax") is False)
    check("dues_unknown", flags.get("dues_unknown") is True)
    check("fc_shell2 preserved flag", flags.get("fc_shell2_preserved") is True)
    check("cap_fin_tax_proven false", flags.get("cap_fin_tax_proven") is False)
    check("cap_fin_tax_ready false", flags.get("cap_fin_tax_ready") is False)
    check("ceiling BUILT", flags.get("cap_fin_tax_ceiling") == "BUILT")
    check("maturity SPECIFIED", flags.get("cap_fin_tax_maturity") == "SPECIFIED")
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "BZG-INVENTORY-TRUTH-1")
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("prod pid held const", tax.PROD_PID_HELD == PROD_PID)

    try:
        tax.refuse_invent_filing({"filing": True})
        check("refuse_invent_filing raises", False)
    except tax.FinTaxShell1Error as exc:
        check("refuse_invent_filing raises", True)
        check("refuse_invent_filing code", exc.code == "invent_filing_refused")
    try:
        tax.refuse_invent_amount({"amount": 999})
        check("refuse_invent_amount raises", False)
    except tax.FinTaxShell1Error as exc:
        check("refuse_invent_amount raises", True)
        check("refuse_invent_amount code", exc.code == "invent_amount_refused")

    try:
        tax.refuse_external_write({"filing": True})
        check("refuse write filing raises", False)
    except tax.FinTaxShell1Error as exc:
        check("refuse write filing", exc.code == "invent_filing_refused")
    try:
        tax.refuse_external_write({"amount": 1000})
        check("refuse write amount raises", False)
    except tax.FinTaxShell1Error as exc:
        check("refuse write amount", exc.code == "invent_amount_refused")
    try:
        tax.refuse_external_write({"due": 1})
        check("refuse write due raises", False)
    except tax.FinTaxShell1Error as exc:
        check("refuse write due", exc.code == "invent_amount_refused")
    try:
        tax.refuse_external_write({"proven": True})
        check("refuse write proven raises", False)
    except tax.FinTaxShell1Error as exc:
        check("refuse write proven", exc.code == "proven_refused")
    try:
        tax.refuse_external_write({"noop": True})
        check("refuse write generic raises", False)
    except tax.FinTaxShell1Error as exc:
        check("refuse write generic", exc.code == "write_refused")


def test_desk_payload() -> None:
    payload = tax.build_slice()
    check("ok", payload.get("ok") is True)
    check("payload staff_ready false", payload.get("staff_ready") is False)
    check("payload human_commissioned false", payload.get("human_commissioned") is False)
    check("payload invented_filing false", payload.get("invented_filing") is False)
    check("payload invented_amount false", payload.get("invented_amount") is False)
    check("payload fake_filings false", payload.get("fake_filings") is False)
    check("payload live_filing false", payload.get("live_filing") is False)
    check("payload live_tax false", payload.get("live_tax") is False)
    check("payload dues_unknown", payload.get("dues_unknown") is True)
    check("payload calendars_unknown", payload.get("calendars_unknown") is True)
    check("payload filing_count 0", payload.get("filing_count") == 0)
    check("payload fc_shell2 preserved", payload.get("fc_shell2_preserved") is True)
    check("payload cap_fin_tax not proven", payload.get("cap_fin_tax_proven") is False)
    check("payload ceiling BUILT", payload.get("cap_fin_tax_ceiling") == "BUILT")
    check("payload next parent", payload.get("next_pack_for_parent_only") == "BZG-INVENTORY-TRUTH-1")
    check("payload no auto-chain", payload.get("cursor_did_not_auto_start_next_pack") is True)
    check("no fake filings helper", tax.no_fake_filings(payload) is True)

    calendars = payload.get("calendars") or []
    check("calendars >= 3", len(calendars) >= 3, str(len(calendars)))
    check("all calendars unknown", tax.all_calendars_unknown(payload) is True)
    for s in calendars:
        check(f"{s['id']} due_amount null", s.get("due_amount") is None)
        check(f"{s['id']} due_on null", s.get("due_on") is None)
        check(f"{s['id']} not filed", s.get("filed") is False)
        check(f"{s['id']} filing 0", s.get("filing_count") == 0)
        check(f"{s['id']} not invented filing", s.get("invented_filing") is False)
        check(f"{s['id']} not invented amount", s.get("invented_amount") is False)
        check(f"{s['id']} status unk", s.get("status") in ("EMPTY", "UNKNOWN"))

    obligations = payload.get("obligations") or []
    check("obligations >= 4", len(obligations) >= 4, str(len(obligations)))
    check("all obligations unknown", tax.all_obligations_unknown(payload) is True)
    for s in obligations:
        check(f"obl {s['id']} due null", s.get("due_amount") is None)
        check(f"obl {s['id']} not filed", s.get("filed") is False)
        check(f"obl {s['id']} not invented", s.get("invented_filing") is False)

    tiles = {t.get("id") for t in (payload.get("honesty_tiles") or [])}
    for tid in (
        "tax_calendar",
        "invented_filing",
        "invented_amount",
        "fc_shell2",
        "cap_fin_tax",
    ):
        check(f"tile {tid}", tid in tiles)

    links = {l.get("id") for l in (payload.get("desk_links") or [])}
    check("link cash", "fin_cash_truth_1" in links)
    check("link recon", "fin_recon_shell_1" in links)

    schema = tax.schema_document()
    check("schema writes false", schema.get("writes_accepted") is False)
    check("schema due_amount false", schema.get("due_amount_property") is False)
    check("schema filing false", schema.get("filing_property") is False)


def test_fc_shell2_preserved() -> None:
    books = tax.fc_shell2_books_preserved()
    check("fc books ok", books.get("ok") is True, str(books))


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/fin/tax-shell-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/fin/tax-shell-1", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api invented_filing false", data.get("invented_filing") is False)
        check("api invented_amount false", data.get("invented_amount") is False)
        check("api fake_filings false", data.get("fake_filings") is False)
        check("api dues unknown", data.get("dues_unknown") is True)
        check("api fc_shell2 preserved", data.get("fc_shell2_preserved") is True)
        check("api calendars unknown helper", tax.all_calendars_unknown(data) is True)
        check("api no fake filings", tax.no_fake_filings(data) is True)

        st, _ = call(port, "GET", "/fin/tax-shell-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/fin/tax-shell-1", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check(
            "page html tax",
            "Tax calendar" in text or "UNKNOWN until facts" in text,
        )
        check("page staff_ready pin", "staff_ready=false" in text)
        check("page human_commissioned pin", "human_commissioned=false" in text)
        check(
            "page no fake filings",
            "fake filings" in text.lower() or "No fake filings" in text or "No invented due" in text,
        )

        st, _ = call(port, "GET", "/fin-tax-shell-1", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")

        st, body = call(
            port, "POST", "/api/fin/tax-shell-1", email=MATT, body={"filing": True}
        )
        check("post filing 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post filing refused code", err.get("error") == "invent_filing_refused")

        st, body = call(
            port, "POST", "/api/fin/tax-shell-1", email=MATT, body={"amount": 50000}
        )
        check("post amount 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post amount refused code", err.get("error") == "invent_amount_refused")

        st, body = call(
            port, "POST", "/api/fin/tax-shell-1", email=MATT, body={"due": 1}
        )
        check("post due 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post due refused code", err.get("error") == "invent_amount_refused")
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
            " const live=document.body && document.body.getAttribute('data-live-tax');"
            " const fil=document.body && document.body.getAttribute('data-invented-filing');"
            " const amt=document.body && document.body.getAttribute('data-invented-amount');"
            " const du=document.body && document.body.getAttribute('data-dues-unknown');"
            " const fp=document.body && document.body.getAttribute('data-fc-preserved');"
            " const proven=document.body && document.body.getAttribute('data-cap-proven');"
            " const sr=document.body && document.body.getAttribute('data-staff-ready');"
            " const hc=document.body && document.body.getAttribute('data-human-commissioned');"
            " const t=document.body ? document.body.innerText : '';"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const cals=(document.querySelectorAll('[data-calendar]')||[]).length;"
            " const obls=(document.querySelectorAll('[data-obligation]')||[]).length;"
            " const unk=document.querySelector('[data-calendars=\"unknown\"]');"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && live==='0' && fil==='0' && amt==='0'"
            "  && du==='1' && fp==='1' && proven==='0' && sr==='0' && hc==='0'"
            "  && stamps>=4 && cals>=3 && obls>=4 && !!unk"
            "  && t.includes('UNKNOWN') && t.includes('Tax calendar')"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && t.includes('Tax calendar shell'),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, cals:cals, obls:obls,"
            " ready:ready, du:du, fp:fp};"
            "})()"
        )
        for width, name in (
            (1024, "fintaxshell1-desk-desktop.png"),
            (390, "fintaxshell1-desk-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/fin/tax-shell-1", desk_expr
            ):
                check(f"desk ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"dues unknown {name}", value.get("du") == "1")
                    check(f"calendars visible {name}", (value.get("cals") or 0) >= 3)
                    check(f"obligations visible {name}", (value.get("obls") or 0) >= 4)
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/fin/tax-shell-1",
            desk_expr,
        ):
            check("unknown calendar shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "fintaxshell1-calendar-unknown.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot calendar-unknown", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/fin/tax-shell-1",
            desk_expr,
        ):
            check("preserved shot ready", bool(value and value.get("ok")), str(value)[:200])
            if value:
                check("fc shell2 preserved attr", value.get("fp") == "1")
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "fintaxshell1-fc-shell2-preserved.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot fc-shell2-preserved", dest.is_file() and dest.stat().st_size > 3000)

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
            f"http://127.0.0.1:{port}/fin/tax-shell-1",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "fintaxshell1-unsigned-deny.png"
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
    check("html pack attr", 'data-pack="FIN-TAX-SHELL-1"' in html)
    check(
        "html no fake",
        "fake filings" in html.lower() or "No invented due" in html or "UNKNOWN until facts" in html,
    )

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "FIN-TAX-SHELL-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "BZG-INVENTORY-TRUTH-1"
        or arm.get("next_pack_for_parent_only") == "BZG-INVENTORY-TRUTH-1",
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
        "fintaxshell1-desk-desktop.png",
        "fintaxshell1-desk-phone.png",
        "fintaxshell1-calendar-unknown.png",
        "fintaxshell1-fc-shell2-preserved.png",
        "fintaxshell1-unsigned-deny.png",
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
    print("=== FIN-TAX-SHELL-1 pack suite ===")
    test_module_and_honesty()
    test_desk_payload()
    test_fc_shell2_preserved()
    test_http_api_and_page()
    test_shots()
    test_artifacts_and_prod_ro()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
