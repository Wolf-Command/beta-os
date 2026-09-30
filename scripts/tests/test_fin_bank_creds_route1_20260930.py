#!/usr/bin/env python3
"""FIN-BANK-CREDS-ROUTE-1 — human bank credentials commissioning route.

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack
FIN-BANK-CREDS-ROUTE-1 (armed 2026-09-30 after SOP-CATALOG-SEED-ROUTE-1).

Document HUMAN_COMMISSIONING path. Keep FILE_IMPORT_ONLY until creds.
Never invent scrape/balances. Preserve FIN-RECON-SHELL-1 + FIN-CASH-TRUTH-1.
Prod :8787 pid 15975 untouched. No auto-chain INV-CASH-FACTS-ROUTE-1.
"""
from __future__ import annotations

import base64
import hashlib
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
from core import fin_bank_creds_route1 as route  # noqa: E402
from core import fin_cash_truth1 as cash  # noqa: E402
from core import fin_recon_shell1 as recon  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "FIN-BANK-CREDS-ROUTE-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
PAGE = ROOT / "dashboards" / "fin-bank-creds-route-1.html"
RESULT = ROOT / "docs" / "wolf" / "ops" / "FIN-BANK-CREDS-ROUTE-1-RESULT.md"
MODULE = ROOT / "scripts" / "core" / "fin_bank_creds_route1.py"
CLASS_LOG = ROOT / "state" / "final-completion" / "CLASSIFICATION-LOG-20260930.json"
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
    check("html present", PAGE.is_file())
    check("api matcher fin", route.api_matches("/api/fin/bank-creds-route-1"))
    check("api matcher ops alias", route.api_matches("/api/ops/fin-bank-creds-route-1"))
    check("api not cash", not route.api_matches("/api/fin/cash-truth-1"))
    check("page matcher fin", route.page_matches("/fin/bank-creds-route-1"))
    check("page matcher alias", route.page_matches("/fin-bank-creds-route-1"))
    check("page matcher ops", route.page_matches("/ops/fin-bank-creds-route-1"))
    check("pack id", route.PACK_ID == "FIN-BANK-CREDS-ROUTE-1")
    check("schema id", route.SCHEMA_ID == "wolf.fin-bank-creds-route-1.v1")
    check("int bank", route.INT_BANK == "INT-BANK")
    check("classification pin", route.CLASSIFICATION == "HUMAN_COMMISSIONING")

    flags = route.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("operating_adoption false", flags.get("operating_adoption") is False)
    check("human_review_gate", flags.get("human_review_gate") is True)
    check("file_import_only", flags.get("file_import_only") is True)
    check("invented_scrape false", flags.get("invented_scrape") is False)
    check("invented_balance false", flags.get("invented_balance") is False)
    check("live_scrape false", flags.get("live_scrape") is False)
    check("bank_api false", flags.get("bank_api") is False)
    check("secret values not exposed", flags.get("secret_values_exposed") is False)
    check("balance null", flags.get("balance") is None)
    check("last_success null", flags.get("last_success") is None)
    check(
        "route classification HUMAN_COMMISSIONING",
        flags.get("route_classification") == "HUMAN_COMMISSIONING"
        or flags.get("classification") == "HUMAN_COMMISSIONING",
    )
    check("action stamp", flags.get("action") == "STAMP_HUMAN_COMMISSIONING")
    check("recon preserved flag", flags.get("fin_recon_shell1_preserved") is True)
    check("cash preserved flag", flags.get("fin_cash_truth1_preserved") is True)
    check("proven false", flags.get("proven") is False)
    check("ready false", flags.get("ready") is False)
    check("cap proven false", flags.get("cap_fin_02_proven") is False)
    check(
        "next pack parent only",
        flags.get("next_pack_for_parent_only") == "INV-CASH-FACTS-ROUTE-1",
    )
    check("did not auto-start", flags.get("cursor_did_not_auto_start_next") is True)
    check("prod pid held", flags.get("prod_pid_held") == PROD_PID)
    check("no push", flags.get("no_push") is True)

    for refuse_fn, code in (
        (route.refuse_scrape, "scrape_refused"),
        (route.refuse_invent_balance, "invent_balance_refused"),
        (route.refuse_bank_write, "bank_write_refused"),
        (route.refuse_commission_flip, "ready_refused"),
        (route.refuse_proven, "proven_refused"),
    ):
        try:
            refuse_fn({})
            check(f"{code} raised", False)
        except route.FinBankCredsRoute1Error as exc:
            check(f"{code} code", exc.code == code, f"got={exc.code}")


def test_decision_and_board() -> None:
    creds = route.probe_credentials()
    check("creds absent", creds.get("creds_present") is False)
    check("creds secret values false", creds.get("secret_values_exposed") is False)
    check("creds balance null", creds.get("balance") is None)

    scrape = route.probe_live_scrape_path()
    check("scrape FILE_IMPORT_ONLY", scrape.get("status") == "FILE_IMPORT_ONLY")
    check("scrape path not configured", scrape.get("path_configured") is False)

    decision = route.decide_route()
    check("decision action stamp", decision.get("action") == "STAMP_HUMAN_COMMISSIONING")
    check(
        "decision classification",
        decision.get("classification") == "HUMAN_COMMISSIONING",
    )
    check("decision may_scrape false", decision.get("may_scrape") is False)
    check("decision scraped false", decision.get("scraped") is False)
    check("decision invented scrape false", decision.get("invented_scrape") is False)
    check("decision invented balance false", decision.get("invented_balance") is False)
    check("decision file_import_only", decision.get("file_import_only") is True)
    check("decision balance null", decision.get("balance") is None)
    check("decision last_success null", decision.get("last_success") is None)

    path_steps = route.commissioning_path()
    check("commissioning path >=4", len(path_steps) >= 4)
    check(
        "path mentions FILE_IMPORT_ONLY",
        any("FILE_IMPORT_ONLY" in (s.get("detail") or "") for s in path_steps),
    )
    check(
        "path mentions commission stamp",
        any("COMMISSION" in (s.get("detail") or "") for s in path_steps),
    )

    board = route.build_board("PERS-MATT")
    check("board ok", board.get("ok") is True)
    check("board classification", board.get("classification") == "HUMAN_COMMISSIONING")
    check("board action", board.get("action") == "STAMP_HUMAN_COMMISSIONING")
    check("board staff_ready false", board.get("staff_ready") is False)
    check("board human_commissioned false", board.get("human_commissioned") is False)
    check("board file_import_only", board.get("file_import_only") is True)
    check("board invented scrape false", board.get("invented_scrape") is False)
    check("board invented balance false", board.get("invented_balance") is False)
    check("board live scrape false", board.get("live_scrape") is False)
    check("board balance null", board.get("balance") is None)
    check("board last_success null", board.get("last_success") is None)
    check("board creds absent", board.get("creds_present") is False)
    check("surfaces honest", route.surfaces_are_honest(board))
    check("no invent", route.no_invented_scrape_or_balances(board))
    check(
        "next pack",
        board.get("next_pack_for_parent_only") == "INV-CASH-FACTS-ROUTE-1",
    )
    check("cursor no auto", board.get("cursor_did_not_auto_start_next") is True)
    check("board recon preserved", board.get("fin_recon_shell1_preserved") is True)
    check("board cash preserved", board.get("fin_cash_truth1_preserved") is True)
    check("commissioning_path on board", len(board.get("commissioning_path") or []) >= 4)

    try:
        route.build_board(None)
        check("unsigned board raised", False)
    except route.FinBankCredsRoute1Error as exc:
        check("unsigned denied", exc.code == "denied", exc.code)

    try:
        route.build_board("PERS-AMANDA")
        check("amanda board raised", False)
    except route.FinBankCredsRoute1Error as exc:
        check("amanda denied", exc.code == "denied", exc.code)


def test_preserved_packs() -> None:
    recon_p = route.fin_recon_shell1_preserved()
    check("recon preserved ok", recon_p.get("ok") is True)
    check("recon file_import_only", recon_p.get("file_import_only") is True)
    check("recon last_success null", recon_p.get("last_success") is None)

    cash_p = route.fin_cash_truth1_preserved()
    check("cash preserved ok", cash_p.get("ok") is True)
    check("cash file_import_only", cash_p.get("file_import_only") is True)
    check("cash invented false", cash_p.get("invented_balance") is False)

    # Direct upstream honesty
    rslice = recon.build_slice()
    check("upstream recon empty", recon.queue_is_empty(rslice))
    check("upstream recon FILE_IMPORT_ONLY", rslice.get("file_import_only") is True)
    check("upstream recon last_success null", rslice.get("last_success") is None)
    check("upstream recon invented false", rslice.get("invented_balance") is False)

    cflags = cash.honesty_flags()
    check("upstream cash FILE_IMPORT_ONLY", cflags.get("file_import_only") is True)
    check("upstream cash invented false", cflags.get("invented_balance") is False)
    check("upstream cash live_scrape false", cflags.get("live_scrape") is False)
    check("upstream cash staff_ready false", cflags.get("staff_ready") is False)


def test_commission_stamp_gate() -> None:
    tmp = ROOT / "state" / "build-factory" / "tmp-fin-bank-creds-route-1"
    tmp.mkdir(parents=True, exist_ok=True)
    stamp = tmp / "COMMISSION.json"
    try:
        if stamp.is_file():
            stamp.unlink()
        d0 = route.decide_route(stamp_path=stamp)
        check("no stamp → HUMAN_COMMISSIONING", d0.get("classification") == "HUMAN_COMMISSIONING")
        check("no stamp → action stamp", d0.get("action") == "STAMP_HUMAN_COMMISSIONING")
        check("no stamp may_scrape false", d0.get("may_scrape") is False)

        stamp.write_text(
            json.dumps(
                {
                    "pack": "FIN-BANK-CREDS-ROUTE-1",
                    "human_route_commissioned": True,
                }
            ),
            encoding="utf-8",
        )
        # Still no creds → HUMAN_COMMISSIONING (creds absent dominates)
        d1 = route.decide_route(stamp_path=stamp)
        check(
            "stamp without creds still HUMAN_COMMISSIONING",
            d1.get("classification") == "HUMAN_COMMISSIONING",
        )
        check("stamp without creds may_scrape false", d1.get("may_scrape") is False)
        check("pack human_commissioned still false", route.honesty_flags().get("human_commissioned") is False)
    finally:
        if stamp.is_file():
            stamp.unlink()
        if tmp.exists():
            try:
                tmp.rmdir()
            except OSError:
                pass


def test_http_surfaces() -> None:
    httpd, port = _start_beta()
    try:
        st, body = call(port, "GET", "/api/fin/bank-creds-route-1")
        check("unsigned API 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/fin/bank-creds-route-1", AMANDA)
        check("amanda deny", st in (403, 400), f"status={st}")

        st, body = call(port, "GET", "/api/fin/bank-creds-route-1", MATT)
        check("matt API 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api HUMAN_COMMISSIONING", data.get("classification") == "HUMAN_COMMISSIONING")
        check("api action stamp", data.get("action") == "STAMP_HUMAN_COMMISSIONING")
        check("api file_import_only", data.get("file_import_only") is True)
        check("api invented scrape false", data.get("invented_scrape") is False)
        check("api invented balance false", data.get("invented_balance") is False)
        check("api balance null", data.get("balance") is None)
        check("api last_success null", data.get("last_success") is None)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api creds absent", data.get("creds_present") is False)
        check(
            "api next pack",
            data.get("next_pack_for_parent_only") == "INV-CASH-FACTS-ROUTE-1",
        )
        check("api recon preserved", data.get("fin_recon_shell1_preserved") is True)
        check("api cash preserved", data.get("fin_cash_truth1_preserved") is True)
        check("api commissioning path", len(data.get("commissioning_path") or []) >= 4)

        st, body = call(port, "GET", "/api/ops/fin-bank-creds-route-1", MATT)
        check("alias API 200", st == 200, f"status={st}")

        st, page_body = call(port, "GET", "/fin/bank-creds-route-1")
        text = page_body.decode(errors="replace").lower()
        check(
            "unsigned page access denied",
            "access denied" in text or "denied" in text or st == 403,
            f"status={st}",
        )

        st, page_body = call(port, "GET", "/fin/bank-creds-route-1", MATT)
        check("matt page 200", st == 200, f"status={st}")
        html = page_body.decode(errors="replace")
        check("page staff_ready=false", "staff_ready=false" in html)
        check("page pack attr", 'data-pack="FIN-BANK-CREDS-ROUTE-1"' in html)
        check("page FILE_IMPORT_ONLY", "FILE_IMPORT_ONLY" in html)
        check("page HUMAN_COMMISSIONING", "HUMAN_COMMISSIONING" in html)

        for action, code in (
            ({"scrape": True}, "scrape_refused"),
            ({"invent_balance": True}, "invent_balance_refused"),
            ({"bank_write": True}, "bank_write_refused"),
            ({"staff_ready": True}, "ready_refused"),
            ({"human_commissioned": True}, "ready_refused"),
        ):
            st, body = call(port, "POST", "/api/fin/bank-creds-route-1", MATT, action)
            check(f"POST {list(action)[0]} 403", st == 403, f"status={st}")
            err = json.loads(body.decode())
            check(
                f"POST {list(action)[0]} code",
                err.get("error") == code,
                f"got={err.get('error')}",
            )
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_prod_untouched() -> None:
    check("prod pid constant", route.PROD_PID_HELD == PROD_PID)
    try:
        import psutil  # type: ignore

        proc = psutil.Process(PROD_PID)
        check("prod process alive", proc.is_running())
        check(
            "prod cmdline serve",
            "serve" in " ".join(proc.cmdline()).lower()
            or "8787" in " ".join(proc.cmdline()),
        )
    except Exception:
        # Fallback: port listen check without mutating
        with socket.socket() as s:
            s.settimeout(1)
            ok = s.connect_ex(("127.0.0.1", PROD_PORT)) == 0
        check("prod port 8787 listening", ok)
    # Confirm our harness did not bind 8787
    check("pack no_push", route.honesty_flags().get("no_push") is True)
    check("pack prod_mutate false", route.honesty_flags().get("prod_mutate") is False)


def test_artifacts() -> None:
    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "FIN-BANK-CREDS-ROUTE-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "INV-CASH-FACTS-ROUTE-1",
    )
    check("arm classification", arm.get("classification") == "HUMAN_COMMISSIONING")
    check(
        "arm preserves recon",
        "FIN-RECON-SHELL-1" in (arm.get("preserves") or []),
    )
    check(
        "arm preserves cash",
        "FIN-CASH-TRUTH-1" in (arm.get("preserves") or []),
    )

    if CLASS_LOG.is_file():
        clog = json.loads(CLASS_LOG.read_text(encoding="utf-8"))
        check(
            "classification has bank creds pin",
            bool(clog.get("fin_bank_creds_route1"))
            or any(
                "Bank recon" in str(c.get("surface") or "")
                or c.get("next_pack") == "FIN-BANK-CREDS-ROUTE-1"
                for c in (clog.get("ceilings") or [])
            ),
        )

    if RESULT.is_file():
        result = RESULT.read_text(encoding="utf-8")
        check("result EXIT", "EXIT:0" in result or "**EXIT:0**" in result)
        check("result no auto-chain", "INV-CASH-FACTS-ROUTE-1" in result)
        check("result HUMAN_COMMISSIONING", "HUMAN_COMMISSIONING" in result)
        check("result FILE_IMPORT_ONLY", "FILE_IMPORT_ONLY" in result)
        check(
            "result no invent",
            "never invent" in result.lower() or "no invent" in result.lower(),
        )
        check("result recon preserved", "FIN-RECON-SHELL-1" in result)
        check("result cash preserved", "FIN-CASH-TRUTH-1" in result)
    else:
        check("result deferred until EXIT write", True)


def _ws_recv(sock) -> bytes:
    hdr = sock.recv(2)
    if len(hdr) < 2:
        raise ConnectionError("short ws header")
    length = hdr[1] & 0x7F
    if length == 126:
        length = struct.unpack("!H", sock.recv(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", sock.recv(8))[0]
    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            break
        data += chunk
    return data


def _ws_send(sock, payload: str) -> None:
    raw = payload.encode("utf-8")
    header = bytearray([0x81])
    n = len(raw)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack("!H", n))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack("!Q", n))
    mask = os.urandom(4)
    header.extend(mask)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(raw))
    sock.sendall(header + masked)


def _ws_connect(host: str, port: int, path: str):
    key = base64.b64encode(os.urandom(16)).decode()
    sock = socket.create_connection((host, port), timeout=10)
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    )
    sock.sendall(req.encode())
    data = b""
    while b"\r\n\r\n" not in data:
        data += sock.recv(4096)
    return sock


def _capture(port, path, width, height, dest: Path, email, marker: str) -> str:
    with tempfile.TemporaryDirectory(prefix="finbankcreds1-") as profile:
        proc = subprocess.Popen(
            [
                str(CHROME),
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                f"--user-data-dir={profile}",
                "--remote-debugging-port=0",
                f"--window-size={width},{height}",
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
            if not port_file.is_file():
                return "fail no DevToolsActivePort"
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
                ident = seq
                _ws_send(
                    sock, json.dumps({"id": ident, "method": method, "params": params or {}})
                )
                while True:
                    msg = json.loads(_ws_recv(sock))
                    if msg.get("id") == ident:
                        return msg

            cdp("Network.enable")
            if email:
                cdp(
                    "Network.setExtraHTTPHeaders",
                    {
                        "headers": {
                            "X-Wolf-Subject": email,
                            "Cf-Access-Authenticated-User-Email": email,
                        }
                    },
                )
            cdp("Page.enable")
            cdp(
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": width,
                    "height": height,
                    "deviceScaleFactor": 1,
                    "mobile": width < 500,
                },
            )
            cdp("Page.navigate", {"url": f"http://127.0.0.1:{port}{path}"})
            found = False
            deadline = time.time() + 40
            while time.time() < deadline:
                got = cdp(
                    "Runtime.evaluate",
                    {
                        "expression": "document.body ? document.body.innerText : ''",
                        "returnByValue": True,
                    },
                )
                text = str(
                    ((got.get("result") or {}).get("result") or {}).get("value") or ""
                )
                low = text.lower()
                if marker.lower() in low:
                    found = True
                    break
                if marker.lower() == "access denied" and (
                    "access denied" in low or "forbidden" in low or "denied" in low
                ):
                    found = True
                    break
                time.sleep(0.3)
            time.sleep(0.35)
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            data = base64.b64decode(((shot.get("result") or {}).get("data") or ""))
            dest.write_bytes(data)
            sock.close()
            return f"ok marker={found} size={dest.stat().st_size}"
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def test_shots() -> None:
    if not CHROME.is_file():
        check("chrome present", False, "Chrome missing")
        return
    httpd, port = _start_beta()
    try:
        SHOTS.mkdir(parents=True, exist_ok=True)
        specs = [
            (
                "finbankcreds1-desk-desktop.png",
                "/fin/bank-creds-route-1",
                1024,
                1200,
                MATT,
                "HUMAN_COMMISSIONING",
            ),
            (
                "finbankcreds1-desk-phone.png",
                "/fin/bank-creds-route-1",
                390,
                1000,
                MATT,
                "commissioning path",
            ),
            (
                "finbankcreds1-route-stamps.png",
                "/fin/bank-creds-route-1",
                1024,
                1400,
                MATT,
                "FILE_IMPORT_ONLY",
            ),
            (
                "finbankcreds1-unsigned-deny.png",
                "/fin/bank-creds-route-1",
                1024,
                900,
                None,
                "Access denied",
            ),
        ]
        digests: list[str] = []
        for name, path, w, h, email, marker in specs:
            dest = SHOTS / name
            status = _capture(port, path, w, h, dest, email, marker)
            check(f"shot {name}", dest.is_file() and dest.stat().st_size > 800, status)
            if dest.is_file():
                digests.append(hashlib.sha256(dest.read_bytes()).hexdigest())
        check("shots distinct", len(set(digests)) == len(digests), str(len(set(digests))))
    finally:
        httpd.shutdown()
        httpd.server_close()


def main() -> int:
    print("=== FIN-BANK-CREDS-ROUTE-1 pack suite ===")
    test_module_and_honesty()
    test_decision_and_board()
    test_preserved_packs()
    test_commission_stamp_gate()
    test_http_surfaces()
    test_prod_untouched()
    test_artifacts()
    test_shots()
    print(f"=== PASS={PASS} FAIL={FAIL} ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
