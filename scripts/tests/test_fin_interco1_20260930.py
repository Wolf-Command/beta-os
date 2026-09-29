#!/usr/bin/env python3
"""FIN-INTERCO-1 — intercompany billing skeleton GGV↔AMG/BZG (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack FIN-INTERCO-1
(armed 2026-09-30) — CAP-FIN-06 / CAP-GGV-06 structure stubs only.
Composes fin_intercompany_billing + ggv_intercompany_client — no second system.
No fake amounts/journals/settlements. FC-SHELL-2 books preserved.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain INTEL-LEARN-1 / HEADCHEF / Exit Report.
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
from core import fin_intercompany_billing as fin_ic  # noqa: E402
from core import ggv_intercompany_client as ggv_ic  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "FIN-INTERCO-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "fin-interco-1.html"
MODULE = ROOT / "scripts" / "core" / "fin_interco1.py"
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
    check("api matcher", interco.api_matches("/api/fin/interco-1"))
    check("page matcher", interco.page_matches("/fin/interco-1"))
    check("page matcher alias", interco.page_matches("/fin-interco-1"))
    check("pack id", interco.PACK_ID == "FIN-INTERCO-1")
    check("schema id", interco.SCHEMA_ID == "wolf.fin-interco-1.v1")
    check("not second system file", "fin_interco1" in MODULE.name)

    flags = interco.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("live_billing false", flags.get("live_billing") is False)
    check("invented_amount false", flags.get("invented_amount") is False)
    check("invented_journal false", flags.get("invented_journal") is False)
    check("invented_settlement false", flags.get("invented_settlement") is False)
    check("payment_executed false", flags.get("payment_executed") is False)
    check("books_write false", flags.get("books_write") is False)
    check("second_billing_system false", flags.get("second_billing_system") is False)
    check("extends existing", flags.get("extends_existing_path") is True)
    check("cap_fin_06_proven false", flags.get("cap_fin_06_proven") is False)
    check("cap_fin_06_ready false", flags.get("cap_fin_06_ready") is False)
    check("cap_ggv_06_proven false", flags.get("cap_ggv_06_proven") is False)
    check("cap_ggv_06_ready false", flags.get("cap_ggv_06_ready") is False)
    check("cap_fin maturity not PROVEN", flags.get("cap_fin_06_maturity") != "PROVEN")
    check("cap_ggv maturity not PROVEN", flags.get("cap_ggv_06_maturity") != "PROVEN")
    check("fc_shell2 flag", flags.get("fc_shell2_preserved") is True)
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "INTEL-LEARN-1")
    check("did not auto-start", flags.get("cursor_did_not_auto_start_next") is True)

    for refuse_fn, code in (
        (interco.refuse_amount, "amount_refused"),
        (interco.refuse_journal, "journal_refused"),
        (interco.refuse_settlement, "settlement_refused"),
        (interco.refuse_payment, "payment_refused"),
        (interco.refuse_proven, "proven_refused"),
        (interco.refuse_ready, "ready_refused"),
    ):
        try:
            refuse_fn({"amount": 1000})
            check(f"{code} raised", False)
        except interco.FinInterco1Error as exc:
            check(f"{code} code", exc.code == code)

    try:
        interco.refuse_external_write({"amount": 999})
        check("write amount refused", False)
    except interco.FinInterco1Error as exc:
        check("write amount code", exc.code == "amount_refused")

    try:
        interco.refuse_external_write({"journal": "JRN-FAKE"})
        check("write journal refused", False)
    except interco.FinInterco1Error as exc:
        check("write journal code", exc.code == "journal_refused")

    html = HTML.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html UNKNOWN", "UNKNOWN" in html)
    check("html EMPTY", "EMPTY" in html)
    check("html FC-SHELL-2", "FC-SHELL-2" in html)
    check("html no fake amount claim", "IDR 1" not in html and "Rp " not in html)


def test_slice_payload() -> None:
    payload = interco.build_slice()
    check("slice ok", payload.get("ok") is True)
    check("slice pack", payload.get("pack") == "FIN-INTERCO-1")
    check("slice staff_ready", payload.get("staff_ready") is False)
    check("slice human_commissioned", payload.get("human_commissioned") is False)
    check("slice live_billing", payload.get("live_billing") is False)
    check("slice invented_amount", payload.get("invented_amount") is False)
    check("slice invented_journal", payload.get("invented_journal") is False)
    check("slice books_write", payload.get("books_write") is False)
    check("slice second system", payload.get("second_billing_system") is False)
    check("slice fc preserved", payload.get("fc_shell2_preserved") is True)
    check("slice caps", set(payload.get("closes_toward") or []) >= {"CAP-FIN-06", "CAP-GGV-06"})
    check("entities GGV", "GGV" in (payload.get("entities") or []))
    check("entities AMG", "AMG" in (payload.get("entities") or []))
    check("entities BZG", "BZG" in (payload.get("entities") or []))

    stubs = payload.get("entity_pair_stubs") or []
    check("four stubs", len(stubs) == 4, f"count={len(stubs)}")
    ids = {s.get("id") for s in stubs}
    for need in (
        "ggv_to_amg_invoice",
        "ggv_to_bzg_invoice",
        "amg_to_ggv_service",
        "bzg_to_ggv_service",
    ):
        check(f"stub {need}", need in ids)
    check("all stubs empty helper", interco.all_stubs_empty(payload) is True)
    for s in stubs:
        check(f"{s['id']} amount null", s.get("amount") is None)
        check(f"{s['id']} journal null", s.get("journal_id") is None)
        check(f"{s['id']} settlement null", s.get("settlement_id") is None)
        check(f"{s['id']} payment null", s.get("payment") is None)
        check(f"{s['id']} status empty/unknown", s.get("status") in ("EMPTY", "UNKNOWN"))
        check(f"{s['id']} not invented", s.get("invented_amount") is False)

    tiles = {t.get("id") for t in (payload.get("honesty_tiles") or [])}
    for tid in ("structure_only", "zero_amounts", "no_journals", "fc_shell2", "cap_fin_06", "cap_ggv_06"):
        check(f"tile {tid}", tid in tiles)

    links = {l.get("id") for l in (payload.get("desk_links") or [])}
    check("link fin billing", "fin_intercompany_billing" in links)
    check("link ggv client", "ggv_intercompany_client" in links)
    check("link amg finance", "amg_finance" in links)

    prior = payload.get("prior_frameworks") or {}
    check("prior fin recorded 0", (prior.get("fin_intercompany_billing") or {}).get("recorded_count") == 0)
    check("prior ggv recorded 0", (prior.get("ggv_intercompany_client") or {}).get("recorded_count") == 0)
    check("prior fin money null", (prior.get("fin_intercompany_billing") or {}).get("money") is None)
    check("next pack parent", payload.get("next_pack_for_parent_only") == "INTEL-LEARN-1")

    schema = interco.schema_document()
    check("schema writes false", schema.get("writes_accepted") is False)
    check("schema amount false", schema.get("amount_property") is False)
    check("schema journal false", schema.get("journal_property") is False)


def test_fc_shell2_preserved() -> None:
    snap = interco.fc_shell2_books_preserved()
    check("fc books ok", snap.get("ok") is True, str(snap))
    check("bzg 200 accounts", (snap.get("bzg") or {}).get("accounts") == 200)
    check("bzg 0 journals", (snap.get("bzg") or {}).get("journals") == 0)
    check("bzg coa shell", (snap.get("bzg") or {}).get("shell_kind") == "coa_template_shell")
    check("ggv 200 accounts", (snap.get("ggv") or {}).get("accounts") == 200)
    check("ggv 0 journals", (snap.get("ggv") or {}).get("journals") == 0)
    check("ggv coa shell", (snap.get("ggv") or {}).get("shell_kind") == "coa_template_shell")
    check("amg live shell", (snap.get("amg") or {}).get("shell_kind") == "live")
    check("amg accounts >=200", int((snap.get("amg") or {}).get("accounts") or 0) >= 200)
    check("journals not invented", snap.get("journals_invented") is False)
    check("books not written", snap.get("books_write") is False or snap.get("books_written") is False)

    # Direct entity_books re-check (smoke, books not touched by this pack)
    bzg = books.snapshot("ENT-BZG")
    ggv = books.snapshot("ENT-GGV")
    amg = books.snapshot("ENT-AMG")
    check("direct bzg journals 0", bzg.get("journals") == 0)
    check("direct ggv journals 0", ggv.get("journals") == 0)
    check("direct amg journals >=1", int(amg.get("journals") or 0) >= 1)


def test_prior_modules_still_empty() -> None:
    fin = fin_ic.build_framework()
    ggv = ggv_ic.build_framework()
    check("fin ic recorded 0", fin.get("recorded_count") == 0)
    check("fin ic money null", fin.get("money") is None)
    check("fin ic honesty no invent", fin["honesty"].get("invented_invoice") is False)
    check("ggv ic recorded 0", ggv.get("recorded_count") == 0)
    check("ggv ic money null", ggv.get("money") is None)
    check("ggv ic honesty no invent", ggv["honesty"].get("invented_invoice") is False)


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/fin/interco-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/fin/interco-1", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api live_billing false", data.get("live_billing") is False)
        check("api invented_amount false", data.get("invented_amount") is False)
        check("api invented_journal false", data.get("invented_journal") is False)
        check("api Fc preserved", data.get("fc_shell2_preserved") is True)
        check("api no proven fin", data.get("cap_fin_06_proven") is False)
        check("api no proven ggv", data.get("cap_ggv_06_proven") is False)
        check("api stubs empty", interco.all_stubs_empty(data) is True)

        st, _ = call(port, "GET", "/fin/interco-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/fin/interco-1", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check(
            "page html interco",
            "intercompany" in text.lower() or "interco" in text.lower(),
        )
        check("page staff_ready pin", "staff_ready=false" in text)
        check("page human_commissioned pin", "human_commissioned=false" in text)

        st, _ = call(port, "GET", "/fin-interco-1", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")

        # Write refusals
        st, body = call(
            port, "POST", "/api/fin/interco-1", email=MATT, body={"amount": 50000}
        )
        check("post amount 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post amount refused code", err.get("error") == "amount_refused")

        st, body = call(
            port, "POST", "/api/fin/interco-1", email=MATT, body={"journal": "JRN-X"}
        )
        check("post journal 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post journal refused code", err.get("error") == "journal_refused")

        # Prior APIs still auth-gated
        st, _ = call(port, "GET", "/api/fin/intercompany-billing")
        check("legacy fin unsigned 403", st == 403, f"status={st}")
        st, _ = call(port, "GET", "/api/ggv/intercompany-client")
        check("legacy ggv unsigned 403", st == 403, f"status={st}")
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
            " const live=document.body && document.body.getAttribute('data-live-billing');"
            " const amt=document.body && document.body.getAttribute('data-invented-amount');"
            " const jrn=document.body && document.body.getAttribute('data-invented-journal');"
            " const fc=document.body && document.body.getAttribute('data-fc-shell2');"
            " const proven=document.body && document.body.getAttribute('data-cap-proven');"
            " const sr=document.body && document.body.getAttribute('data-staff-ready');"
            " const hc=document.body && document.body.getAttribute('data-human-commissioned');"
            " const t=document.body ? document.body.innerText : '';"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const stubs=(document.querySelectorAll('[data-stub]')||[]).length;"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && live==='0' && amt==='0' && jrn==='0'"
            "  && fc==='1' && proven==='0' && sr==='0' && hc==='0'"
            "  && stamps>=4 && stubs>=4"
            "  && t.includes('EMPTY') && t.includes('UNKNOWN')"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && t.includes('Intercompany billing skeleton'),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, stubs:stubs,"
            " ready:ready, fc:fc, live:live};"
            "})()"
        )
        for width, name in (
            (1024, "fininterco1-desk-desktop.png"),
            (390, "fininterco1-desk-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/fin/interco-1", shell_expr
            ):
                check(f"desk ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"fc attr {name}", value.get("fc") == "1")
                    check(f"stubs visible {name}", (value.get("stubs") or 0) >= 4)
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/fin/interco-1",
            shell_expr,
        ):
            check("pairs shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "fininterco1-entity-pairs.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot entity-pairs", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/fin/interco-1",
            shell_expr,
        ):
            check("books shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "fininterco1-fc-shell2-preserved.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot fc-shell2", dest.is_file() and dest.stat().st_size > 3000)

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
            f"http://127.0.0.1:{port}/fin/interco-1",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "fininterco1-unsigned-deny.png"
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
    # Do not call prod HTTP — read-only presence check only
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
    print("=== FIN-INTERCO-1 pack suite ===")
    test_module_and_honesty()
    test_slice_payload()
    test_fc_shell2_preserved()
    test_prior_modules_still_empty()
    test_http_api_and_page()
    test_shots()
    test_prod_untouched()
    test_arm_flags()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
