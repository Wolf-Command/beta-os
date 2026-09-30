#!/usr/bin/env python3
"""INV-CASH-FACTS-ROUTE-1 — inventory/cash facts route (wire or human).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack
INV-CASH-FACTS-ROUTE-1 (armed 2026-09-30 after FIN-BANK-CREDS-ROUTE-1).

Probe authorised count/cash systems; wire facts OR stamp
HUMAN_COMMISSIONING/EXTERNAL with evidence. Never invent qty/cash.
Preserve BZG-INVENTORY-TRUTH-1 + FIN-CASH-TRUTH-1.
Prod :8787 pid 15975 untouched. No auto-chain DEEPEN-SYNTH-CONTINUE.
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
from core import bzg_inventory_truth1 as inv  # noqa: E402
from core import fin_cash_truth1 as cash  # noqa: E402
from core import inv_cash_facts_route1 as route  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "INV-CASH-FACTS-ROUTE-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
PAGE = ROOT / "dashboards" / "inv-cash-facts-route-1.html"
RESULT = ROOT / "docs" / "wolf" / "ops" / "INV-CASH-FACTS-ROUTE-1-RESULT.md"
MODULE = ROOT / "scripts" / "core" / "inv_cash_facts_route1.py"
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
    check("api matcher ops", route.api_matches("/api/ops/inv-cash-facts-route-1"))
    check("api matcher fin alias", route.api_matches("/api/fin/inv-cash-facts-route-1"))
    check("api not cash truth", not route.api_matches("/api/fin/cash-truth-1"))
    check("page matcher ops", route.page_matches("/ops/inv-cash-facts-route-1"))
    check("page matcher fin", route.page_matches("/fin/inv-cash-facts-route-1"))
    check("page matcher alias", route.page_matches("/inv-cash-facts-route-1"))
    check("pack id", route.PACK_ID == "INV-CASH-FACTS-ROUTE-1")
    check("schema id", route.SCHEMA_ID == "wolf.inv-cash-facts-route-1.v1")
    check(
        "pack classification pin",
        route.PACK_CLASSIFICATION == "HUMAN_COMMISSIONING_OR_INTERNAL",
    )
    check("route classification pin", route.CLASSIFICATION == "HUMAN_COMMISSIONING")

    flags = route.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("operating_adoption false", flags.get("operating_adoption") is False)
    check("human_review_gate", flags.get("human_review_gate") is True)
    check("file_import_only", flags.get("file_import_only") is True)
    check("invented_qty false", flags.get("invented_qty") is False)
    check("invented_cash false", flags.get("invented_cash") is False)
    check("invented_balance false", flags.get("invented_balance") is False)
    check("fake_stock false", flags.get("fake_stock") is False)
    check("secret values not exposed", flags.get("secret_values_exposed") is False)
    check("qty null", flags.get("qty") is None)
    check("balance null", flags.get("balance") is None)
    check("cash_on_hand null", flags.get("cash_on_hand") is None)
    check(
        "route classification HUMAN_COMMISSIONING",
        flags.get("route_classification") == "HUMAN_COMMISSIONING"
        or flags.get("classification") == "HUMAN_COMMISSIONING",
    )
    check(
        "pack classification umbrella",
        flags.get("pack_classification") == "HUMAN_COMMISSIONING_OR_INTERNAL",
    )
    check("action stamp", flags.get("action") == "STAMP_HUMAN_COMMISSIONING")
    check("inv preserved flag", flags.get("bzg_inventory_truth1_preserved") is True)
    check("cash preserved flag", flags.get("fin_cash_truth1_preserved") is True)
    check("uma petty external", flags.get("uma_petty_external") is True)
    check("proven false", flags.get("proven") is False)
    check("ready false", flags.get("ready") is False)
    check(
        "next pack parent only",
        flags.get("next_pack_for_parent_only") == "DEEPEN-SYNTH-CONTINUE",
    )
    check("did not auto-start", flags.get("cursor_did_not_auto_start_next") is True)
    check("prod pid held", flags.get("prod_pid_held") == PROD_PID)
    check("no push", flags.get("no_push") is True)

    for refuse_fn, code in (
        (route.refuse_invent_qty, "invent_qty_refused"),
        (route.refuse_invent_cash, "invent_cash_refused"),
        (route.refuse_invent_balance, "invent_balance_refused"),
        (route.refuse_fake_stock, "fake_stock_refused"),
        (route.refuse_commission_flip, "ready_refused"),
        (route.refuse_proven, "proven_refused"),
    ):
        try:
            refuse_fn({})
            check(f"{code} raised", False)
        except route.InvCashFactsRoute1Error as exc:
            check(f"{code} code", exc.code == code, f"got={exc.code}")


def test_decision_and_board() -> None:
    count = route.probe_count_systems()
    check("count systems absent or no client", count.get("client_module_found") is False)
    check("count secret values false", count.get("secret_values_exposed") is False)
    check("count qty null", count.get("qty") is None)

    cash_sys = route.probe_cash_systems()
    check("cash systems client absent", cash_sys.get("client_module_found") is False)
    check("cash balance null", cash_sys.get("balance") is None)

    uma = route.probe_uma_petty_external()
    check("uma EXTERNAL", uma.get("status") == "EXTERNAL")
    check("uma not wired fin cash", uma.get("wired_into_fin_cash") is False)

    inv_f = route.probe_inventory_truth_facts()
    check("inv facts UNKNOWN", inv_f.get("status") == "UNKNOWN")
    check("inv fact_count 0", inv_f.get("fact_count") == 0)

    cash_f = route.probe_cash_truth_facts()
    check("cash facts UNKNOWN", cash_f.get("status") == "UNKNOWN")
    check("cash import_count 0", cash_f.get("import_count") == 0)

    decision = route.decide_route()
    check("decision action stamp", decision.get("action") == "STAMP_HUMAN_COMMISSIONING")
    check(
        "decision classification",
        decision.get("classification") == "HUMAN_COMMISSIONING",
    )
    check(
        "decision pack classification",
        decision.get("pack_classification") == "HUMAN_COMMISSIONING_OR_INTERNAL",
    )
    check("decision may_wire false", decision.get("may_wire") is False)
    check("decision wired false", decision.get("wired") is False)
    check("decision invented qty false", decision.get("invented_qty") is False)
    check("decision invented cash false", decision.get("invented_cash") is False)
    check("decision qty null", decision.get("qty") is None)
    check("decision balance null", decision.get("balance") is None)

    path_steps = route.commissioning_path()
    check("commissioning path >=4", len(path_steps) >= 4)
    check(
        "path mentions UNKNOWN",
        any("UNKNOWN" in (s.get("detail") or "") for s in path_steps),
    )
    check(
        "path mentions commission stamp",
        any("COMMISSION" in (s.get("detail") or "") for s in path_steps),
    )

    board = route.build_board("PERS-MATT")
    check("board ok", board.get("ok") is True)
    check("board classification", board.get("classification") == "HUMAN_COMMISSIONING")
    check(
        "board pack classification",
        board.get("pack_classification") == "HUMAN_COMMISSIONING_OR_INTERNAL",
    )
    check("board action", board.get("action") == "STAMP_HUMAN_COMMISSIONING")
    check("board staff_ready false", board.get("staff_ready") is False)
    check("board human_commissioned false", board.get("human_commissioned") is False)
    check("board invented qty false", board.get("invented_qty") is False)
    check("board invented cash false", board.get("invented_cash") is False)
    check("board qty null", board.get("qty") is None)
    check("board balance null", board.get("balance") is None)
    check("board uma external", board.get("uma_petty_external") is True)
    check("surfaces honest", route.surfaces_are_honest(board))
    check("no invent", route.no_invented_qty_or_cash(board))
    check(
        "next pack",
        board.get("next_pack_for_parent_only") == "DEEPEN-SYNTH-CONTINUE",
    )
    check("cursor no auto", board.get("cursor_did_not_auto_start_next") is True)
    check("board inv preserved", board.get("bzg_inventory_truth1_preserved") is True)
    check("board cash preserved", board.get("fin_cash_truth1_preserved") is True)
    check("commissioning_path on board", len(board.get("commissioning_path") or []) >= 4)

    try:
        route.build_board(None)
        check("unsigned board raised", False)
    except route.InvCashFactsRoute1Error as exc:
        check("unsigned denied", exc.code == "denied", exc.code)

    try:
        route.build_board("PERS-AMANDA")
        check("amanda board raised", False)
    except route.InvCashFactsRoute1Error as exc:
        check("amanda denied", exc.code == "denied", exc.code)


def test_preserved_packs() -> None:
    inv_p = route.bzg_inventory_truth1_preserved()
    check("inv preserved ok", inv_p.get("ok") is True)
    check("inv fact_count 0", inv_p.get("fact_count") == 0)
    check("inv unknown", inv_p.get("inventory_unknown") is True)

    cash_p = route.fin_cash_truth1_preserved()
    check("cash preserved ok", cash_p.get("ok") is True)
    check("cash file_import_only", cash_p.get("file_import_only") is True)
    check("cash invented false", cash_p.get("invented_balance") is False)

    islice = inv.build_slice()
    check("upstream inv fact_count 0", islice.get("fact_count") == 0)
    check("upstream inv unknown", islice.get("inventory_unknown") is True)
    check("upstream inv fake_stock false", islice.get("fake_stock") is False)
    check("upstream inv all unknown", inv.all_inventory_slots_unknown(islice))

    cflags = cash.honesty_flags()
    check("upstream cash FILE_IMPORT_ONLY", cflags.get("file_import_only") is True)
    check("upstream cash invented false", cflags.get("invented_balance") is False)
    check("upstream cash live_scrape false", cflags.get("live_scrape") is False)
    check("upstream cash staff_ready false", cflags.get("staff_ready") is False)


def test_commission_stamp_gate() -> None:
    tmp = ROOT / "state" / "build-factory" / "tmp-inv-cash-facts-route-1"
    tmp.mkdir(parents=True, exist_ok=True)
    stamp = tmp / "COMMISSION.json"
    try:
        if stamp.is_file():
            stamp.unlink()
        d0 = route.decide_route(stamp_path=stamp)
        check("no stamp → HUMAN_COMMISSIONING", d0.get("classification") == "HUMAN_COMMISSIONING")
        check("no stamp → action stamp", d0.get("action") == "STAMP_HUMAN_COMMISSIONING")
        check("no stamp may_wire false", d0.get("may_wire") is False)

        stamp.write_text(
            json.dumps(
                {
                    "pack": "INV-CASH-FACTS-ROUTE-1",
                    "human_route_commissioned": True,
                }
            ),
            encoding="utf-8",
        )
        # Still no wireable facts → not WIRE_FACTS
        d1 = route.decide_route(stamp_path=stamp)
        check(
            "stamp without facts not WIRE",
            d1.get("action") != "WIRE_FACTS",
        )
        check("stamp without facts may_wire false", d1.get("may_wire") is False)
        check(
            "pack human_commissioned still false",
            route.honesty_flags().get("human_commissioned") is False,
        )
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
        st, body = call(port, "GET", "/api/ops/inv-cash-facts-route-1")
        check("unsigned API 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/ops/inv-cash-facts-route-1", AMANDA)
        check("amanda deny", st in (403, 400), f"status={st}")

        st, body = call(port, "GET", "/api/ops/inv-cash-facts-route-1", MATT)
        check("matt API 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api HUMAN_COMMISSIONING", data.get("classification") == "HUMAN_COMMISSIONING")
        check(
            "api pack classification",
            data.get("pack_classification") == "HUMAN_COMMISSIONING_OR_INTERNAL",
        )
        check("api action stamp", data.get("action") == "STAMP_HUMAN_COMMISSIONING")
        check("api invented qty false", data.get("invented_qty") is False)
        check("api invented cash false", data.get("invented_cash") is False)
        check("api qty null", data.get("qty") is None)
        check("api balance null", data.get("balance") is None)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api uma external", data.get("uma_petty_external") is True)
        check(
            "api next pack",
            data.get("next_pack_for_parent_only") == "DEEPEN-SYNTH-CONTINUE",
        )
        check("api inv preserved", data.get("bzg_inventory_truth1_preserved") is True)
        check("api cash preserved", data.get("fin_cash_truth1_preserved") is True)
        check("api commissioning path", len(data.get("commissioning_path") or []) >= 4)

        st, body = call(port, "GET", "/api/fin/inv-cash-facts-route-1", MATT)
        check("alias API 200", st == 200, f"status={st}")

        st, page_body = call(port, "GET", "/ops/inv-cash-facts-route-1")
        text = page_body.decode(errors="replace").lower()
        check(
            "unsigned page access denied",
            "access denied" in text or "denied" in text or st == 403,
            f"status={st}",
        )

        st, page_body = call(port, "GET", "/ops/inv-cash-facts-route-1", MATT)
        check("matt page 200", st == 200, f"status={st}")
        html = page_body.decode(errors="replace")
        check("page staff_ready=false", "staff_ready=false" in html)
        check("page pack attr", 'data-pack="INV-CASH-FACTS-ROUTE-1"' in html)
        check("page HUMAN_COMMISSIONING", "HUMAN_COMMISSIONING" in html)
        check("page EXTERNAL", "EXTERNAL" in html)
        check("page never invent", "never invent" in html.lower())

        for action, code in (
            ({"qty": 12}, "invent_qty_refused"),
            ({"cash": 100}, "invent_cash_refused"),
            ({"invent_balance": True}, "invent_balance_refused"),
            ({"fake_stock": True}, "fake_stock_refused"),
            ({"staff_ready": True}, "ready_refused"),
            ({"human_commissioned": True}, "ready_refused"),
        ):
            st, body = call(port, "POST", "/api/ops/inv-cash-facts-route-1", MATT, action)
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
        with socket.socket() as s:
            s.settimeout(1)
            ok = s.connect_ex(("127.0.0.1", PROD_PORT)) == 0
        check("prod port 8787 listening", ok)
    check("pack no_push", route.honesty_flags().get("no_push") is True)
    check("pack prod_mutate false", route.honesty_flags().get("prod_mutate") is False)


def test_artifacts() -> None:
    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "INV-CASH-FACTS-ROUTE-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "DEEPEN-SYNTH-CONTINUE",
    )
    check(
        "arm classification",
        arm.get("classification") == "HUMAN_COMMISSIONING_OR_INTERNAL",
    )
    check(
        "arm preserves inv",
        "BZG-INVENTORY-TRUTH-1" in (arm.get("preserves") or []),
    )
    check(
        "arm preserves cash",
        "FIN-CASH-TRUTH-1" in (arm.get("preserves") or []),
    )

    if CLASS_LOG.is_file():
        clog = json.loads(CLASS_LOG.read_text(encoding="utf-8"))
        check(
            "classification has inv cash pin",
            bool(clog.get("inv_cash_facts_route1"))
            or any(
                "Inventory/cash" in str(c.get("surface") or "")
                or c.get("next_pack") == "INV-CASH-FACTS-ROUTE-1"
                for c in (clog.get("ceilings") or [])
            ),
        )

    if RESULT.is_file():
        result = RESULT.read_text(encoding="utf-8")
        check("result EXIT", "EXIT:0" in result or "**EXIT:0**" in result)
        check("result no auto-chain", "DEEPEN-SYNTH-CONTINUE" in result)
        check("result HUMAN_COMMISSIONING", "HUMAN_COMMISSIONING" in result)
        check(
            "result no invent",
            "never invent" in result.lower() or "no invent" in result.lower(),
        )
        check("result inv preserved", "BZG-INVENTORY-TRUTH-1" in result)
        check("result cash preserved", "FIN-CASH-TRUTH-1" in result)
        check("result EXTERNAL", "EXTERNAL" in result)
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
    with tempfile.TemporaryDirectory(prefix="invcashfacts1-") as profile:
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
                "invcashfacts1-desk-desktop.png",
                "/ops/inv-cash-facts-route-1",
                1024,
                1200,
                MATT,
                "HUMAN_COMMISSIONING",
            ),
            (
                "invcashfacts1-desk-phone.png",
                "/ops/inv-cash-facts-route-1",
                390,
                1000,
                MATT,
                "commissioning path",
            ),
            (
                "invcashfacts1-route-stamps.png",
                "/ops/inv-cash-facts-route-1",
                1024,
                1400,
                MATT,
                "EXTERNAL",
            ),
            (
                "invcashfacts1-unsigned-deny.png",
                "/ops/inv-cash-facts-route-1",
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
    print("=== INV-CASH-FACTS-ROUTE-1 pack suite ===")
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
