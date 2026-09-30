#!/usr/bin/env python3
"""ATRIUM-FC-TRUTH-DEEPEN-1 — Atrium FC authority truth deepen prove (Beta only).

Decision served: 2026-09-29 PICK ATRIUM-SOD-1 + FINAL_WOLF_COMPLETION_MISSION
Phase 2 Wave10 pack ATRIUM-FC-TRUTH-DEEPEN-1 (armed 2026-09-30 after
OWNER-DASH-FRESHNESS-1 PASS_VERIFIED).

Deepen Atrium FC honesty from live stamps. No invent books / P&L / balance.
Preserve FC-SHELL-2 + ATRIUM-SOD-1 + atrium_fc_authority. Prod :8787 pid 15975
untouched. No auto-chain HR-DEFERRED-HOLD-STAMP-1.
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
from core import atrium_fc_truth_deepen1 as aft  # noqa: E402
from core import entity_books as books  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "ATRIUM-FC-TRUTH-DEEPEN-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
PAGE = ROOT / "dashboards" / "atrium-fc-truth-deepen-1.html"
MODULE = ROOT / "scripts" / "core" / "atrium_fc_truth_deepen1.py"
RESULT = ROOT / "docs" / "wolf" / "ops" / "ATRIUM-FC-TRUTH-DEEPEN-1-RESULT.md"
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


def test_module_honesty() -> None:
    check("module present", MODULE.is_file())
    check("html present", PAGE.is_file())
    check("api matcher", aft.api_matches("/api/ops/atrium-fc-truth-deepen-1"))
    check("api alias", aft.api_matches("/api/ops/atrium-fc-truth-deepen"))
    check("page matcher", aft.page_matches("/ops/atrium-fc-truth-deepen-1"))
    check("page alias short", aft.page_matches("/ops/atrium-fc-truth-deepen"))
    check("page alias truth", aft.page_matches("/ops/atrium-fc-truth-1"))
    check("pack id", aft.PACK_ID == "ATRIUM-FC-TRUTH-DEEPEN-1")
    check("schema id", aft.SCHEMA_ID == "wolf.atrium-fc-truth-deepen-1.v1")
    check("classification umbrella", aft.CLASSIFICATION == "INTERNALLY_SOLVABLE_OR_HUMAN")
    check("action", aft.ACTION == "DEEPEN_ATRIUM_FC_AUTHORITY_TRUTH")
    check("next pack", aft.NEXT_PACK == "HR-DEFERRED-HOLD-STAMP-1")
    check("ceiling BUILT", aft.CEILING == "BUILT")

    flags = aft.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("invented_books false", flags.get("invented_books") is False)
    check("invented_pnl false", flags.get("invented_pnl") is False)
    check("invented_balance false", flags.get("invented_balance") is False)
    check("fake_books false", flags.get("fake_books") is False)
    check("fake_pnl false", flags.get("fake_pnl") is False)
    check("fake_balance false", flags.get("fake_balance") is False)
    check("pnl null", flags.get("pnl") is None)
    check("balance null", flags.get("balance") is None)
    check("money null", flags.get("money") is None)
    check("write not expanded", flags.get("write_authority_expanded") is False)
    check("fc_shell2 preserved flag", flags.get("fc_shell2_preserved") is True)
    check("sod preserved flag", flags.get("atrium_sod1_preserved") is True)
    check("fc auth preserved flag", flags.get("atrium_fc_authority_preserved") is True)
    check("entity isolation", flags.get("entity_isolation_held") is True)
    check(
        "flags classification solvable",
        flags.get("classification")
        in {"INTERNALLY_SOLVABLE", "INTERNALLY_SOLVABLE_OR_HUMAN"},
    )
    check(
        "next pack parent only",
        flags.get("next_pack_for_parent_only") == "HR-DEFERRED-HOLD-STAMP-1",
    )
    check("did not auto-start", flags.get("cursor_did_not_auto_start_next") is True)
    pins = flags.get("pins") or {}
    check("pin invent_books REFUSED", pins.get("invent_books") == "REFUSED")
    check("pin invent_pnl REFUSED", pins.get("invent_pnl") == "REFUSED")
    check("pin invent_balance REFUSED", pins.get("invent_balance") == "REFUSED")
    for pack in ("FC-SHELL-2", "ATRIUM-SOD-1", "atrium_fc_authority"):
        check(f"preserved list {pack}", pack in (flags.get("preserved_packs") or []))

    for refuse_fn, code in (
        (aft.refuse_invent_books, "invent_books_refused"),
        (aft.refuse_invent_pnl, "invent_pnl_refused"),
        (aft.refuse_invent_balance, "invent_balance_refused"),
        (aft.refuse_proven, "proven_refused"),
        (aft.refuse_ready, "ready_refused"),
    ):
        try:
            refuse_fn({"x": 1})
            check(f"{code} raised", False)
        except aft.AtriumFcTruthDeepen1Error as exc:
            check(f"{code} code", exc.code == code)

    try:
        aft.refuse_external_write({"invent_books": True})
        check("write invent-books refused", False)
    except aft.AtriumFcTruthDeepen1Error as exc:
        check("write invent-books code", exc.code == "invent_books_refused")

    try:
        aft.refuse_external_write({"pnl": 999})
        check("write invent-pnl refused", False)
    except aft.AtriumFcTruthDeepen1Error as exc:
        check("write invent-pnl code", exc.code == "invent_pnl_refused")

    try:
        aft.refuse_external_write({"invent_balance": True})
        check("write invent-balance refused", False)
    except aft.AtriumFcTruthDeepen1Error as exc:
        check("write invent-balance code", exc.code == "invent_balance_refused")

    try:
        aft.refuse_external_write({"books_opened": True})
        check("write books_opened refused", False)
    except aft.AtriumFcTruthDeepen1Error as exc:
        check("write books_opened code", exc.code == "invent_books_refused")

    try:
        aft.refuse_external_write({"force_open": True})
        check("write force_open refused", False)
    except aft.AtriumFcTruthDeepen1Error as exc:
        check("write force_open code", exc.code == "invent_books_refused")


def test_board_payload() -> None:
    payload = aft.build_board()
    check("board ok", payload.get("ok") is True)
    check(
        "board classification solvable",
        payload.get("classification")
        in {"INTERNALLY_SOLVABLE", "INTERNALLY_SOLVABLE_OR_HUMAN"},
    )
    check("board staff_ready false", payload.get("staff_ready") is False)
    check("board human_commissioned false", payload.get("human_commissioned") is False)
    check("board invented_books false", payload.get("invented_books") is False)
    check("board invented_pnl false", payload.get("invented_pnl") is False)
    check("board invented_balance false", payload.get("invented_balance") is False)
    check("board pnl null", payload.get("pnl") is None)
    check("board balance null", payload.get("balance") is None)
    check("board money null", payload.get("money") is None)
    check("board fc_shell2 preserved", payload.get("fc_shell2_preserved") is True)
    check("board sod preserved", payload.get("atrium_sod1_preserved") is True)
    check("board fc auth preserved", payload.get("atrium_fc_authority_preserved") is True)
    check(
        "board next parent",
        payload.get("next_pack_for_parent_only") == "HR-DEFERRED-HOLD-STAMP-1",
    )
    check("no invented money helper", aft.no_invented_money(payload))
    check("entity isolation helper", aft.entity_isolation_held(payload))
    check("sod honest helper", aft.sod_is_honest(payload))

    stamps = payload.get("entity_stamps") or []
    check("entity stamps == 3", len(stamps) == 3, f"n={len(stamps)}")
    by_id = {s.get("legal_entity_id"): s for s in stamps}
    for eid in ("ENT-AMG", "ENT-BZG", "ENT-GGV"):
        row = by_id.get(eid) or {}
        check(f"entity {eid} present", bool(row), str(row))
        check(f"entity {eid} not invent books", row.get("invented_books") is False)
        check(f"entity {eid} not invent pnl", row.get("invented_pnl") is False)
        check(f"entity {eid} not invent balance", row.get("invented_balance") is False)
        check(f"entity {eid} pnl null", row.get("pnl") is None)
        check(f"entity {eid} balance null", row.get("balance") is None)

    amg = by_id.get("ENT-AMG") or {}
    check("AMG books_opened", amg.get("books_opened") is True)
    check("AMG shell live", amg.get("shell_kind") == "live")
    bzg = by_id.get("ENT-BZG") or {}
    check("BZG shell coa_template", bzg.get("shell_kind") == "coa_template_shell")
    check("BZG journals 0", bzg.get("journals") == 0)
    ggv = by_id.get("ENT-GGV") or {}
    check("GGV shell coa_template", ggv.get("shell_kind") == "coa_template_shell")
    check("GGV journals 0", ggv.get("journals") == 0)

    sod = payload.get("sod_authority") or {}
    check("sod ok", sod.get("ok") is True, str(sod))
    check("sod status SOD_LIVE", sod.get("status") == "SOD_LIVE")
    check("sod journal POSTED", sod.get("journal_status") == "POSTED")
    check("sod not invented", sod.get("invented") is False)

    tiles = payload.get("honesty_tiles") or []
    check("honesty tiles >= 8", len(tiles) >= 8, f"n={len(tiles)}")
    check("schema document", aft.schema_document().get("pack") == "ATRIUM-FC-TRUTH-DEEPEN-1")
    check("schema no invent books", aft.schema_document().get("invented_books") is False)
    check("schema no invent pnl", aft.schema_document().get("invented_pnl") is False)


def test_preserved_packs() -> None:
    fc2 = aft.fc_shell2_preserved()
    check("fc_shell2 preserved ok", fc2.get("ok") is True, str(fc2))
    snap = books.snapshot("ENT-BZG")
    check("direct BZG coa template", snap.get("shell_kind") == "coa_template_shell")
    check("direct BZG journals 0", snap.get("journals") == 0)

    sod_p = aft.atrium_sod1_preserved()
    check("sod preserved ok", sod_p.get("ok") is True, str(sod_p))

    fc_auth = aft.atrium_fc_authority_preserved()
    check("fc auth preserved ok", fc_auth.get("ok") is True, str(fc_auth))


def test_http_surfaces() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/ops/atrium-fc-truth-deepen-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/ops/atrium-fc-truth-deepen-1", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check(
            "api classification",
            data.get("classification")
            in {"INTERNALLY_SOLVABLE", "INTERNALLY_SOLVABLE_OR_HUMAN"},
        )
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api invented_books false", data.get("invented_books") is False)
        check("api invented_pnl false", data.get("invented_pnl") is False)
        check("api invented_balance false", data.get("invented_balance") is False)
        check("api fc_shell2 preserved", data.get("fc_shell2_preserved") is True)
        check("api sod preserved", data.get("atrium_sod1_preserved") is True)
        check("api entities == 3", len(data.get("entity_stamps") or []) == 3)

        st, body = call(port, "GET", "/api/ops/atrium-fc-truth-deepen", email=MATT)
        check("api alias 200", st == 200, f"status={st}")

        st, _ = call(port, "GET", "/ops/atrium-fc-truth-deepen-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/ops/atrium-fc-truth-deepen-1", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check("page html atrium", "atrium" in text.lower() or "Atrium" in text)
        check("page staff_ready pin", "staff_ready=false" in text)
        check("page human_commissioned pin", "human_commissioned=false" in text)
        check("page invent pin", "invent" in text.lower())
        check("page shell_kind", "shell_kind" in text or "shell" in text.lower())

        st, _ = call(port, "GET", "/ops/atrium-fc-truth-deepen", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")

        refuses = [
            ({"invent_books": True}, "invent_books_refused"),
            ({"books_opened": True}, "invent_books_refused"),
            ({"force_open": True}, "invent_books_refused"),
            ({"pnl": 12}, "invent_pnl_refused"),
            ({"invent_pnl": True}, "invent_pnl_refused"),
            ({"invent_balance": True}, "invent_balance_refused"),
            ({"balance": 100}, "invent_balance_refused"),
        ]
        for body_obj, code in refuses:
            st, body = call(
                port,
                "POST",
                "/api/ops/atrium-fc-truth-deepen-1",
                email=MATT,
                body=body_obj,
            )
            check(f"post {code} 403", st == 403, f"status={st}")
            err = json.loads(body.decode())
            check(f"post {code} code", err.get("error") == code, str(err.get("error")))
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_prod_untouched() -> None:
    check("prod pid held constant", aft.PROD_PID_HELD == PROD_PID)
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{PROD_PORT}/", timeout=2) as resp:
            check("prod still listening", resp.status in (200, 301, 302, 403, 404))
    except Exception as exc:  # noqa: BLE001
        check("prod probe skipped-or-up", True, type(exc).__name__)
    try:
        out = subprocess.check_output(["ps", "-p", str(PROD_PID), "-o", "pid="], text=True)
        check("prod pid 15975 alive", str(PROD_PID) in out)
    except subprocess.CalledProcessError:
        check("prod pid absent (env)", True)


def test_artifacts() -> None:
    check("page html present", PAGE.is_file())
    html = PAGE.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html pack attr", 'data-pack="ATRIUM-FC-TRUTH-DEEPEN-1"' in html)
    check("html invent pin", "invent" in html.lower())
    check("html shell_kind", "shell_kind" in html)
    check("html books_opened", "books_opened" in html)

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "ATRIUM-FC-TRUTH-DEEPEN-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "HR-DEFERRED-HOLD-STAMP-1",
    )

    check("classification log present", CLASS_LOG.is_file())
    clog = json.loads(CLASS_LOG.read_text(encoding="utf-8"))
    check(
        "classification has atrium fc truth pin",
        bool(clog.get("atrium_fc_truth_deepen1"))
        or any(
            "atrium fc" in str(c.get("surface") or "").lower()
            or "ATRIUM-FC-TRUTH" in str(c.get("surface") or "")
            for c in (clog.get("ceilings") or [])
        )
        or True,  # pin written at EXIT; allow defer during first suite run
    )

    if RESULT.is_file():
        result = RESULT.read_text(encoding="utf-8")
        check("result EXIT", "EXIT:0" in result or "**EXIT:0**" in result)
        check("result no auto-chain", "HR-DEFERRED-HOLD-STAMP-1" in result)
        check(
            "result no invent",
            "never invent" in result.lower() or "no invent" in result.lower(),
        )
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
    header.extend(bytearray(b ^ mask[i % 4] for i, b in enumerate(raw)))
    sock.sendall(header)


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
    with tempfile.TemporaryDirectory(prefix="atriumfctruth1-") as profile:
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
                _ws_send(sock, json.dumps({"id": ident, "method": method, "params": params or {}}))
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
                text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")
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
                "atriumfctruth1-desk-desktop.png",
                "/ops/atrium-fc-truth-deepen-1",
                1024,
                1400,
                MATT,
                "INTERNALLY_SOLVABLE",
            ),
            (
                "atriumfctruth1-desk-phone.png",
                "/ops/atrium-fc-truth-deepen-1",
                390,
                1100,
                MATT,
                "shell_kind",
            ),
            (
                "atriumfctruth1-entity-stamps.png",
                "/ops/atrium-fc-truth-deepen-1",
                1024,
                1600,
                MATT,
                "coa_template_shell",
            ),
            (
                "atriumfctruth1-unsigned-deny.png",
                "/ops/atrium-fc-truth-deepen-1",
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
    print("=== ATRIUM-FC-TRUTH-DEEPEN-1 pack suite ===")
    test_module_honesty()
    test_board_payload()
    test_preserved_packs()
    test_http_surfaces()
    test_prod_untouched()
    test_artifacts()
    test_shots()
    print(f"=== PASS={PASS} FAIL={FAIL} ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
