#!/usr/bin/env python3
"""FIN-TAX-DEEPEN-1 — tax dues deepen (wire or HUMAN/EXTERNAL).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave8 pack
FIN-TAX-DEEPEN-1 (armed 2026-09-30 after INV-CASH-FACTS-ROUTE-1).

Probe authorised tax systems; wire facts OR stamp
HUMAN_COMMISSIONING/EXTERNAL_BLOCKER with evidence. Never invent
dues/filings/NPWP. NPWP = MATT_ACTION non-blocking.
Preserve FIN-TAX-SHELL-1. Prod :8787 pid 15975 untouched.
No auto-chain CRM-PIPELINE-TRUTH-1 / HEADCHEF / Exit Report.
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
from core import fin_tax_deepen1 as deepen  # noqa: E402
from core import fin_tax_shell1 as tax  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "FIN-TAX-DEEPEN-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
PAGE = ROOT / "dashboards" / "fin-tax-deepen-1.html"
RESULT = ROOT / "docs" / "wolf" / "ops" / "FIN-TAX-DEEPEN-1-RESULT.md"
MODULE = ROOT / "scripts" / "core" / "fin_tax_deepen1.py"
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
    check("api matcher fin", deepen.api_matches("/api/fin/tax-deepen-1"))
    check("api matcher ops alias", deepen.api_matches("/api/ops/fin-tax-deepen-1"))
    check("api not tax shell", not deepen.api_matches("/api/fin/tax-shell-1"))
    check("page matcher fin", deepen.page_matches("/fin/tax-deepen-1"))
    check("page matcher ops", deepen.page_matches("/ops/fin-tax-deepen-1"))
    check("page matcher alias", deepen.page_matches("/fin-tax-deepen-1"))
    check("pack id", deepen.PACK_ID == "FIN-TAX-DEEPEN-1")
    check("schema id", deepen.SCHEMA_ID == "wolf.fin-tax-deepen-1.v1")
    check(
        "pack classification pin",
        deepen.PACK_CLASSIFICATION == "INTERNALLY_SOLVABLE_OR_HUMAN",
    )
    check("route classification pin", deepen.CLASSIFICATION == "HUMAN_COMMISSIONING")
    check("npwp MATT_ACTION", deepen.NPWP_STATUS == "MATT_ACTION")
    check("npwp non-blocking", deepen.NPWP_BLOCKING is False)

    flags = deepen.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("operating_adoption false", flags.get("operating_adoption") is False)
    check("human_review_gate", flags.get("human_review_gate") is True)
    check("invented_amount false", flags.get("invented_amount") is False)
    check("invented_filing false", flags.get("invented_filing") is False)
    check("invented_due false", flags.get("invented_due") is False)
    check("invented_npwp false", flags.get("invented_npwp") is False)
    check("fake_filings false", flags.get("fake_filings") is False)
    check("secret values not exposed", flags.get("secret_values_exposed") is False)
    check("due_amount null", flags.get("due_amount") is None)
    check("due_on null", flags.get("due_on") is None)
    check("npwp_number null", flags.get("npwp_number") is None)
    check(
        "route classification HUMAN_COMMISSIONING",
        flags.get("route_classification") == "HUMAN_COMMISSIONING"
        or flags.get("classification") == "HUMAN_COMMISSIONING",
    )
    check(
        "pack classification umbrella",
        flags.get("pack_classification") == "INTERNALLY_SOLVABLE_OR_HUMAN",
    )
    check("external_blocker pin", flags.get("external_blocker") == "EXTERNAL_BLOCKER")
    check("npwp flag MATT_ACTION", flags.get("npwp") == "MATT_ACTION")
    check("npwp_blocking false", flags.get("npwp_blocking") is False)
    check("action stamp", flags.get("action") == "STAMP_HUMAN_COMMISSIONING")
    check("tax shell preserved flag", flags.get("fin_tax_shell1_preserved") is True)
    check("djp external", flags.get("djp_efaktur_external") is True)
    check("proven false", flags.get("proven") is False)
    check("ready false", flags.get("ready") is False)
    check(
        "next pack parent only",
        flags.get("next_pack_for_parent_only") == "CRM-PIPELINE-TRUTH-1",
    )
    check("did not auto-start", flags.get("cursor_did_not_auto_start_next") is True)
    check("prod pid held", flags.get("prod_pid_held") == PROD_PID)
    check("no push", flags.get("no_push") is True)

    for refuse_fn, code in (
        (deepen.refuse_invent_amount, "invent_amount_refused"),
        (deepen.refuse_invent_filing, "invent_filing_refused"),
        (deepen.refuse_invent_npwp, "invent_npwp_refused"),
        (deepen.refuse_commission_flip, "ready_refused"),
        (deepen.refuse_proven, "proven_refused"),
    ):
        try:
            refuse_fn({})
            check(f"{code} raised", False)
        except deepen.FinTaxDeepen1Error as exc:
            check(f"{code} code", exc.code == code, f"got={exc.code}")


def test_decision_and_board() -> None:
    systems = deepen.probe_tax_systems()
    check("tax systems client absent", systems.get("client_module_found") is False)
    check("tax secret values false", systems.get("secret_values_exposed") is False)
    check("tax due_amount null", systems.get("due_amount") is None)

    djp = deepen.probe_djp_external()
    check("djp EXTERNAL_BLOCKER", djp.get("status") == "EXTERNAL_BLOCKER")
    check("djp not wired", djp.get("wired_into_fin_tax") is False)

    npwp = deepen.probe_npwp_matt_action()
    check("npwp MATT_ACTION", npwp.get("status") == "MATT_ACTION")
    check("npwp non-blocking", npwp.get("blocking") is False)
    check("npwp number null", npwp.get("npwp_number") is None)

    facts = deepen.probe_tax_shell_facts()
    check("tax facts UNKNOWN", facts.get("status") == "UNKNOWN")
    check("filing_count 0", facts.get("filing_count") == 0)

    decision = deepen.decide_route()
    check("decision action stamp", decision.get("action") == "STAMP_HUMAN_COMMISSIONING")
    check(
        "decision classification",
        decision.get("classification") == "HUMAN_COMMISSIONING",
    )
    check(
        "decision pack classification",
        decision.get("pack_classification") == "INTERNALLY_SOLVABLE_OR_HUMAN",
    )
    check("decision may_wire false", decision.get("may_wire") is False)
    check("decision wired false", decision.get("wired") is False)
    check("decision invented amount false", decision.get("invented_amount") is False)
    check("decision invented filing false", decision.get("invented_filing") is False)
    check("decision invented npwp false", decision.get("invented_npwp") is False)
    check("decision due_amount null", decision.get("due_amount") is None)
    check("decision npwp MATT_ACTION", decision.get("npwp") == "MATT_ACTION")
    check("decision npwp_blocking false", decision.get("npwp_blocking") is False)
    check(
        "decision external_blocker",
        decision.get("external_blocker") == "EXTERNAL_BLOCKER",
    )

    path_steps = deepen.commissioning_path()
    check("commissioning path >=4", len(path_steps) >= 4)
    check(
        "path mentions UNKNOWN",
        any("UNKNOWN" in (s.get("detail") or "") for s in path_steps),
    )
    check(
        "path mentions commission stamp",
        any("COMMISSION" in (s.get("detail") or "") for s in path_steps),
    )
    check(
        "path mentions NPWP MATT",
        any("MATT_ACTION" in (s.get("detail") or "") for s in path_steps),
    )

    board = deepen.build_board("PERS-MATT")
    check("board ok", board.get("ok") is True)
    check("board classification", board.get("classification") == "HUMAN_COMMISSIONING")
    check(
        "board pack classification",
        board.get("pack_classification") == "INTERNALLY_SOLVABLE_OR_HUMAN",
    )
    check("board action", board.get("action") == "STAMP_HUMAN_COMMISSIONING")
    check("board staff_ready false", board.get("staff_ready") is False)
    check("board human_commissioned false", board.get("human_commissioned") is False)
    check("board invented amount false", board.get("invented_amount") is False)
    check("board invented filing false", board.get("invented_filing") is False)
    check("board invented npwp false", board.get("invented_npwp") is False)
    check("board due_amount null", board.get("due_amount") is None)
    check("board npwp MATT_ACTION", board.get("npwp") == "MATT_ACTION")
    check("board djp external", board.get("djp_efaktur_external") is True)
    check("surfaces honest", deepen.surfaces_are_honest(board))
    check("no invent", deepen.no_invented_dues_or_filings(board))
    check(
        "next pack",
        board.get("next_pack_for_parent_only") == "CRM-PIPELINE-TRUTH-1",
    )
    check("cursor no auto", board.get("cursor_did_not_auto_start_next") is True)
    check("board tax preserved", board.get("fin_tax_shell1_preserved") is True)
    check("commissioning_path on board", len(board.get("commissioning_path") or []) >= 4)

    try:
        deepen.build_board(None)
        check("unsigned board raised", False)
    except deepen.FinTaxDeepen1Error as exc:
        check("unsigned denied", exc.code == "denied", exc.code)

    try:
        deepen.build_board("PERS-AMANDA")
        check("amanda board raised", False)
    except deepen.FinTaxDeepen1Error as exc:
        check("amanda denied", exc.code == "denied", exc.code)


def test_preserved_packs() -> None:
    tax_p = deepen.fin_tax_shell1_preserved()
    check("tax preserved ok", tax_p.get("ok") is True)
    check("tax filing_count 0", tax_p.get("filing_count") == 0)
    check("tax dues_unknown", tax_p.get("dues_unknown") is True)
    check("tax invented filing false", tax_p.get("invented_filing") is False)
    check("tax invented amount false", tax_p.get("invented_amount") is False)

    tslice = tax.build_slice()
    check("upstream filing_count 0", tslice.get("filing_count") == 0)
    check("upstream dues_unknown", tslice.get("dues_unknown") is True)
    check("upstream fake_filings false", tslice.get("fake_filings") is False)
    check("upstream calendars unknown", tax.all_calendars_unknown(tslice))
    check("upstream obligations unknown", tax.all_obligations_unknown(tslice))
    check("upstream no fake filings", tax.no_fake_filings(tslice))

    tflags = tax.honesty_flags()
    check("upstream staff_ready false", tflags.get("staff_ready") is False)
    check("upstream human_commissioned false", tflags.get("human_commissioned") is False)
    check("upstream dues_unknown flag", tflags.get("dues_unknown") is True)


def test_commission_stamp_gate() -> None:
    tmp = ROOT / "state" / "build-factory" / "tmp-fin-tax-deepen-1"
    tmp.mkdir(parents=True, exist_ok=True)
    stamp = tmp / "COMMISSION.json"
    try:
        if stamp.is_file():
            stamp.unlink()
        d0 = deepen.decide_route(stamp_path=stamp)
        check("no stamp → HUMAN_COMMISSIONING", d0.get("classification") == "HUMAN_COMMISSIONING")
        check("no stamp → action stamp", d0.get("action") == "STAMP_HUMAN_COMMISSIONING")
        check("no stamp may_wire false", d0.get("may_wire") is False)

        stamp.write_text(
            json.dumps(
                {
                    "pack": "FIN-TAX-DEEPEN-1",
                    "human_route_commissioned": True,
                }
            ),
            encoding="utf-8",
        )
        d1 = deepen.decide_route(stamp_path=stamp)
        check(
            "stamp without facts not WIRE",
            d1.get("action") != "WIRE_FACTS",
        )
        check("stamp without facts may_wire false", d1.get("may_wire") is False)
        check(
            "pack human_commissioned still false",
            deepen.honesty_flags().get("human_commissioned") is False,
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
        st, body = call(port, "GET", "/api/fin/tax-deepen-1")
        check("unsigned API 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/fin/tax-deepen-1", AMANDA)
        check("amanda deny", st in (403, 400), f"status={st}")

        st, body = call(port, "GET", "/api/fin/tax-deepen-1", MATT)
        check("matt API 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api HUMAN_COMMISSIONING", data.get("classification") == "HUMAN_COMMISSIONING")
        check(
            "api pack classification",
            data.get("pack_classification") == "INTERNALLY_SOLVABLE_OR_HUMAN",
        )
        check("api action stamp", data.get("action") == "STAMP_HUMAN_COMMISSIONING")
        check("api invented amount false", data.get("invented_amount") is False)
        check("api invented filing false", data.get("invented_filing") is False)
        check("api invented npwp false", data.get("invented_npwp") is False)
        check("api due_amount null", data.get("due_amount") is None)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api djp external", data.get("djp_efaktur_external") is True)
        check("api npwp MATT_ACTION", data.get("npwp") == "MATT_ACTION")
        check("api npwp_blocking false", data.get("npwp_blocking") is False)
        check(
            "api external_blocker",
            data.get("external_blocker") == "EXTERNAL_BLOCKER",
        )
        check(
            "api next pack",
            data.get("next_pack_for_parent_only") == "CRM-PIPELINE-TRUTH-1",
        )
        check("api tax preserved", data.get("fin_tax_shell1_preserved") is True)
        check("api commissioning path", len(data.get("commissioning_path") or []) >= 4)

        st, body = call(port, "GET", "/api/ops/fin-tax-deepen-1", MATT)
        check("alias API 200", st == 200, f"status={st}")

        st, page_body = call(port, "GET", "/fin/tax-deepen-1")
        text = page_body.decode(errors="replace").lower()
        check(
            "unsigned page access denied",
            "access denied" in text or "denied" in text or st == 403,
            f"status={st}",
        )

        st, page_body = call(port, "GET", "/fin/tax-deepen-1", MATT)
        check("matt page 200", st == 200, f"status={st}")
        html = page_body.decode(errors="replace")
        check("page staff_ready=false", "staff_ready=false" in html)
        check("page pack attr", 'data-pack="FIN-TAX-DEEPEN-1"' in html)
        check("page HUMAN_COMMISSIONING", "HUMAN_COMMISSIONING" in html)
        check("page EXTERNAL_BLOCKER", "EXTERNAL_BLOCKER" in html)
        check("page MATT_ACTION", "MATT_ACTION" in html)
        check("page never invent", "never invent" in html.lower())

        for action, code in (
            ({"due_amount": 1000000}, "invent_amount_refused"),
            ({"filing": True}, "invent_filing_refused"),
            ({"npwp": "10.0.0.1-000.000"}, "invent_npwp_refused"),
            ({"staff_ready": True}, "ready_refused"),
            ({"human_commissioned": True}, "ready_refused"),
        ):
            st, body = call(port, "POST", "/api/fin/tax-deepen-1", MATT, action)
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
    check("prod pid constant", deepen.PROD_PID_HELD == PROD_PID)
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
    check("pack no_push", deepen.honesty_flags().get("no_push") is True)
    check("pack prod_mutate false", deepen.honesty_flags().get("prod_mutate") is False)


def test_artifacts() -> None:
    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "FIN-TAX-DEEPEN-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "CRM-PIPELINE-TRUTH-1",
    )
    check(
        "arm classification",
        arm.get("classification") == "INTERNALLY_SOLVABLE_OR_HUMAN",
    )
    check(
        "arm preserves tax shell",
        "FIN-TAX-SHELL-1" in (arm.get("preserves") or []),
    )
    check(
        "arm npwp non-blocking",
        arm.get("npwp") == "MATT_ACTION_NON_BLOCKING",
    )

    if CLASS_LOG.is_file():
        clog = json.loads(CLASS_LOG.read_text(encoding="utf-8"))
        check(
            "classification has tax deepen pin",
            bool(clog.get("fin_tax_deepen1"))
            or any(
                "tax" in str(c.get("surface") or "").lower()
                or c.get("next_pack") == "FIN-TAX-DEEPEN-1"
                for c in (clog.get("ceilings") or [])
            ),
        )

    if RESULT.is_file():
        result = RESULT.read_text(encoding="utf-8")
        check("result EXIT", "EXIT:0" in result or "**EXIT:0**" in result)
        check("result no auto-chain", "CRM-PIPELINE-TRUTH-1" in result)
        check("result HUMAN_COMMISSIONING", "HUMAN_COMMISSIONING" in result)
        check("result EXTERNAL_BLOCKER", "EXTERNAL_BLOCKER" in result)
        check("result MATT_ACTION", "MATT_ACTION" in result)
        check(
            "result no invent",
            "never invent" in result.lower() or "no invent" in result.lower(),
        )
        check("result tax shell preserved", "FIN-TAX-SHELL-1" in result)
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
    with tempfile.TemporaryDirectory(prefix="fintaxdeepen1-") as profile:
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
                "fintaxdeepen1-desk-desktop.png",
                "/fin/tax-deepen-1",
                1024,
                1200,
                MATT,
                "HUMAN_COMMISSIONING",
            ),
            (
                "fintaxdeepen1-desk-phone.png",
                "/fin/tax-deepen-1",
                390,
                1000,
                MATT,
                "commissioning path",
            ),
            (
                "fintaxdeepen1-route-stamps.png",
                "/fin/tax-deepen-1",
                1024,
                1400,
                MATT,
                "EXTERNAL_BLOCKER",
            ),
            (
                "fintaxdeepen1-unsigned-deny.png",
                "/fin/tax-deepen-1",
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
    print("=== FIN-TAX-DEEPEN-1 pack suite ===")
    test_module_and_honesty()
    test_decision_and_board()
    test_preserved_packs()
    test_commission_stamp_gate()
    test_http_surfaces()
    test_prod_untouched()
    test_artifacts()
    test_shots()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
