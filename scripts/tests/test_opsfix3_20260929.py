#!/usr/bin/env python3
"""OPSFIX-3. Honest Owner Command, data-quality exceptions, human cards, three defects.

Uses a short-lived Beta handler in development_assertion. Does not switch
the live :8788 process and does not touch production :8787.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
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
sys.path.insert(0, str(ROOT / "scripts"))

import serve_beta as sb  # noqa: E402
from core import data_quality_exceptions as dq  # noqa: E402
from core import ggv_invoice_history as history  # noqa: E402
from core import owner_command  # noqa: E402
from core import owner_operational_exceptions as ops_ex  # noqa: E402
from core.staff_home import build_home  # noqa: E402

OWNER = "mrwolf@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
DEVI = "deviputu236@gmail.com"
AMANDA = "amanda@wolfcommand.net"
ZAYEN = "laluzayen@gmail.com"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
ATRIUM = Path("/Users/wolfterminal/atrium-finance")
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


def call(port: int, method: str, path: str, email: str | None = None, accept: str = "application/json"):
    headers = {"Accept": accept}
    if email:
        headers["X-Wolf-Subject"] = email
    last: Exception | None = None
    for _ in range(3):
        req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, method=method)
        try:
            with urlopen(req, timeout=120) as resp:
                return resp.status, resp.read(), resp.headers.get("Content-Type") or ""
        except HTTPError as exc:
            return exc.code, exc.read(), (exc.headers.get("Content-Type") if exc.headers else "") or ""
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(0.4)
    raise last if last else RuntimeError("call failed")


def test_owner_not_falsely_green() -> None:
    register = dq.build_register(write=True)
    check("data-quality register written", (ROOT / "state/ops/data-quality-exceptions.json").is_file())
    check("three data-quality items", register.get("open_count") == 3, str(register.get("open_count")))
    ids = {item.get("id") for item in register.get("items") or []}
    check(
        "cash occupancy alchemist traced",
        {"dq-cash-owed-to-you", "dq-atrium-occupancy", "dq-alchemist-broken-payable"} <= ids,
        str(ids),
    )
    cash = next(item for item in register["items"] if item["id"] == "dq-cash-owed-to-you")
    check("cash is apartment pipeline not AR", "orderbook" in (cash.get("plain_english") or "").lower() or "apartment" in (cash.get("plain_english") or "").lower())
    check("cash says do not act", "Do not act" in (cash.get("do_not_act") or ""))
    broken = next(item for item in register["items"] if item["id"] == "dq-alchemist-broken-payable")
    br = broken.get("broken") or {}
    check("broken count is 55", br.get("count") == 55, str(br.get("count")))
    counts = br.get("counts") or {}
    check(
        "55 classifications sum",
        counts.get("ESTABLISHED", 0) + counts.get("PARTIAL", 0) + counts.get("NO EVIDENCE", 0) == 55,
        str(counts),
    )
    check("no bank-beats-alchemist rule", "bank beats" not in json.dumps(register).lower())
    check(
        "bank not used as AP proof",
        "does not establish" in json.dumps(register).lower() or "proves bank transactions only" in json.dumps(register).lower(),
    )

    ops = ops_ex.collect()
    check("operational exceptions open", ops.get("count", 0) > 0, str(ops.get("count")))
    kinds = {row.get("kind") for row in ops.get("items") or []}
    check("uma close in rollup", "uma_daily_close" in kinds, str(kinds))
    check("data quality in rollup", "data_quality" in kinds, str(kinds))
    check("month end in rollup", "month_end" in kinds, str(kinds))

    report = owner_command.build_command(verified_person_id="PERS-MATT")
    answers = {row.get("id"): row.get("answer") or "" for row in report.get("answers") or []}
    wrong = answers.get("wrong") or ""
    money = answers.get("money") or ""
    blocked = answers.get("blocked") or ""
    check("wrong is not falsely green", "Nothing is going wrong" not in wrong, wrong[:200])
    check("wrong shows a count", "exceptions are open" in wrong, wrong[:200])
    check("money mentions risk", "money" in money.lower() or "Finance books" in money, money[:200])
    check("blocked mentions blockers", "blocker" in blocked.lower() or int(re.search(r"(\d+)", blocked).group(1) if re.search(r"(\d+)", blocked) else 0) > 0, blocked[:200])
    check("operational payload present", (report.get("operational_exceptions") or {}).get("count", 0) > 0)
    check("data quality href", report.get("data_quality_href") == "/owner/data-quality")


def test_staff_defects() -> None:
    my_work = (ROOT / "dashboards/my-work.html").read_text(encoding="utf-8")
    check("my work uses staff footnote", "staff_footnote" in my_work)
    check("my work hides engineering origin line", "origin ${esc(it.origin)}" not in my_work)
    uma = (ROOT / "dashboards/bzg-uma-blu.html").read_text(encoding="utf-8")
    check("uma today plain footnote", "Not yet checked in Wolf" in uma)
    check("uma today no verified_by_wolf text", "verified_by_wolf false" not in uma)
    ggv = (ROOT / "dashboards/ggv-finance.html").read_text(encoding="utf-8")
    check("amanda invoices hide source_path", "source_path" not in ggv or "row.source_path" not in ggv)
    check("amanda keeps open file", "Open file" in ggv)
    sidenav = (ROOT / "dashboards/assets/sidenav.js").read_text(encoding="utf-8")
    check("role follows active context", "roleForActiveContext" in sidenav)

    conn = __import__("sqlite3").connect(f"file:{CATALOG}?mode=ro", uri=True)
    conn.row_factory = __import__("sqlite3").Row
    try:
        home = build_home("PERS-HAIKAL", conn=conn)
        items = [
            row for row in home["sections"][0]["items"]
            if row.get("origin") == "historical" or row.get("source_system") == "content_plans"
        ]
        ids = [row.get("source_id") for row in items]
        # HUMFIX-1C: current-window only — stale habitat fortnight must not top TODAY.
        check(
            "habitat stale plans absent from TODAY",
            all("2026-09-14" not in str(row.get("title") or "") for row in items),
            str([(r.get("title"), r.get("date_range")) for r in items]),
        )
        check("habitat duplicates collapsed", len(ids) == len(set(ids)), str(ids))
        check(
            "plain footnotes on plans",
            all(
                not items
                or "Not yet checked in Wolf" in (row.get("staff_footnote") or "")
                for row in items
            ),
        )
        check(
            "engineering words off footnotes",
            all(
                "verified_by_wolf" not in (row.get("staff_footnote") or "")
                and "content_plans" not in (row.get("staff_footnote") or "")
                for row in items
            ),
        )
    finally:
        conn.close()

    hist = history.projection()
    row = hist["by_number"]["066A"]
    check("invoice staff footnote", "Not yet checked in Wolf" in (row.get("staff_footnote") or ""))
    check("invoice provenance still on API", row.get("origin") == "historical" and row.get("source_path"))


def test_human_cards() -> None:
    matrix = json.loads((ROOT / "state/ops/testability-matrix.json").read_text(encoding="utf-8"))
    check("staff_ready stays false", matrix.get("staff_ready") is False)
    check("human_commissioned stays false", matrix.get("human_commissioned") is False)
    fail_kept = any(
        "FAIL" in (row.get("last_human_result") or "").upper()
        or any("FAIL" in (h.get("result") or "").upper() for h in row.get("human_results") or [])
        for row in matrix.get("surfaces") or []
    )
    check("earlier FAILs kept", fail_kept)
    cards = [row for row in matrix.get("surfaces") or [] if row.get("test_card")]
    who = " ".join((row.get("test_card") or {}).get("who") or "" for row in cards)
    check("devi card", "Devi" in who)
    check("amanda card", "Amanda" in who)
    check("zayen card", "Zayen" in who)
    check("haikal card", "Haikal" in who)
    for row in cards:
        card = row["test_card"]
        check(f"card steps {row['surface'][:24]}", 5 <= len(card.get("steps") or []) <= 8, str(len(card.get("steps") or [])))
        check(f"card pass {row['surface'][:24]}", bool(card.get("pass_looks_like")))
        check(f"card urls {row['surface'][:24]}", bool(card.get("urls")))


def test_atrium_idr_source() -> None:
    for name in (
        "GeneralLedgerView.tsx",
        "TrialBalanceView.tsx",
        "JournalWorkbenchView.tsx",
        "ManualJournalModal.tsx",
    ):
        text = (ATRIUM / "src/components" / name).read_text(encoding="utf-8")
        check(f"{name} uses formatMoneyIDR", "formatMoneyIDR" in text)
        check(f"{name} dropped en-US money", "toLocaleString('en-US'" not in text)
        check(f"{name} no $ money headers", "Debit ($)" not in text and "Credit ($)" not in text)
    util = (ATRIUM / "src/utils/idrFormat.ts").read_text(encoding="utf-8")
    check("idr util has Rp", "Rp" in util and "id-ID" in util)


def _ws_connect(host: str, port: int, path: str):
    import socket

    sock = socket.create_connection((host, port), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall(
        (
            f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ).encode()
    )
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
    return sock


def _ws_send(sock, text: str) -> None:
    data = text.encode()
    mask = os.urandom(4)
    length = len(data)
    header = bytearray([0x81])
    if length < 126:
        header.append(0x80 | length)
    else:
        header.append(0x80 | 126)
        header.extend(struct.pack(">H", length))
    header.extend(mask)
    sock.sendall(bytes(header) + bytes(byte ^ mask[i % 4] for i, byte in enumerate(data)))


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


def _capture(port: int, path: str, email: str, width: int, dest: Path, marker: str, ready_attr: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:
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
                f"--window-size={width},900",
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
            cdp("Network.setExtraHTTPHeaders", {"headers": {"X-Wolf-Subject": email}})
            cdp("Page.enable")
            cdp(
                "Emulation.setDeviceMetricsOverride",
                {"width": width, "height": 900, "deviceScaleFactor": 1, "mobile": width < 500},
            )
            cdp("Page.navigate", {"url": f"http://127.0.0.1:{port}{path}"})
            text = ""
            deadline = time.time() + 55
            while time.time() < deadline:
                got = cdp(
                    "Runtime.evaluate",
                    {"expression": "document.body ? document.body.innerText : ''", "returnByValue": True},
                )
                text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")
                ready = cdp(
                    "Runtime.evaluate",
                    {
                        "expression": f"document.body && document.body.getAttribute('{ready_attr}')",
                        "returnByValue": True,
                    },
                )
                flag = str(((ready.get("result") or {}).get("result") or {}).get("value") or "")
                ready_ok = (not ready_attr) or (flag not in {"", "null", "None", "0"})
                if marker in text and ready_ok:
                    break
                time.sleep(0.4)
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            sock.close()
            check(f"shot {dest.name}", dest.is_file() and dest.stat().st_size > 4000 and marker in text, text[:180])
        finally:
            proc.kill()
            proc.wait(timeout=5)


def test_http_and_shots() -> None:
    from core import ggv_finance_nota as fin
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    scratch = Path(tempfile.mkdtemp(prefix="opsfix3-catalog-", dir=ROOT / "state"))
    copy = scratch / "content_library.sqlite"
    shutil.copy(CATALOG, copy)
    fin.CATALOG_DB = copy
    sb.CATALOG_DB = copy

    handler = next(
        obj
        for obj in vars(sb).values()
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler"
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, body, _ = call(port, "GET", "/api/health")
        check("unsigned health 200", status == 200, str(status))
        status, _, _ = call(port, "GET", "/wolf")
        check("unsigned wolf 403", status == 403, str(status))
        status, body, _ = call(port, "GET", "/api/owner/command", OWNER)
        check("owner command 200", status == 200, str(status))
        data = json.loads(body.decode())
        wrong = next((row["answer"] for row in data.get("answers") or [] if row.get("id") == "wrong"), "")
        check("http wrong not green", "Nothing is going wrong" not in wrong, wrong[:160])
        check("http ops count", (data.get("operational_exceptions") or {}).get("count", 0) > 0)

        status, body, _ = call(port, "GET", "/api/owner/data-quality", OWNER)
        check("data-quality api 200", status == 200, str(status))
        dq_data = json.loads(body.decode())
        check("data-quality items", len(dq_data.get("items") or []) == 3)

        status, _, _ = call(port, "GET", "/api/owner/data-quality", HAIKAL)
        check("haikal data-quality 403", status == 403, str(status))

        status, body, _ = call(port, "GET", "/api/owner/war-room/testability", OWNER)
        check("testability 200", status == 200, str(status))
        room = json.loads(body.decode())
        check("give human title", room.get("title") == "GIVE THIS TO A HUMAN NOW")
        # MYWORK-1: queue is real commissioning Work Items (not OPSFIX-3 test_card list).
        work_queue = [
            row for row in (room.get("queue") or [])
            if isinstance(row, dict) and (row.get("work_item_id") or row.get("href") or row.get("test_card"))
        ]
        check("commissioning work queue populated", len(work_queue) >= 4, str(len(work_queue)))

        status, body, _ = call(port, "GET", "/api/staff/home", HAIKAL)
        home = json.loads(body.decode())
        items = ((home.get("sections") or [{}])[0].get("items") or [])
        check("haikal home plans", len(items) >= 1)

        status, body, _ = call(port, "GET", "/ggv/finance/invoices", AMANDA, accept="text/html")
        check("amanda finance page 200", status == 200, str(status))
        status, body, _ = call(port, "GET", "/assets/sidenav.js", AMANDA, accept="*/*")
        check("sidenav has context role", b"roleForActiveContext" in body)

        status, body, _ = call(port, "GET", "/amg/finance", ZAYEN, accept="text/html")
        check("zayen atrium page reachable", status in {200, 502, 503}, str(status))

        if CHROME.is_file():
            _capture(port, "/wolf", OWNER, 1024, SHOTS / "opsfix3-owner-wolf.png", "exceptions are open", "data-command-ready")
            _capture(port, "/owner/data-quality", OWNER, 1024, SHOTS / "opsfix3-data-quality.png", "Do not act", "data-dq-ready")
            _capture(port, "/finish-war-room", OWNER, 1024, SHOTS / "opsfix3-war-room-human-queue.png", "GIVE THIS TO A HUMAN NOW", "data-testability-ready")
            _capture(port, "/my-work", HAIKAL, 1024, SHOTS / "opsfix3-haikal-mywork.png", "Retest", "data-ready")
            _capture(port, "/ggv/finance/invoices", AMANDA, 1024, SHOTS / "opsfix3-amanda-invoices.png", "Open file", "data-historical")
            _capture(port, "/bzg/uma-blu", DEVI, 1024, SHOTS / "opsfix3-uma-today.png", "Not yet checked in Wolf", "data-ready")
            _capture(port, "/amg/finance", ZAYEN, 1024, SHOTS / "opsfix3-atrium-finance-idr.png", "Command", "")
        else:
            check("chrome present for shots", False, "Chrome missing")
    finally:
        server.shutdown()
        server.server_close()


def main() -> int:
    test_owner_not_falsely_green()
    test_staff_defects()
    test_human_cards()
    test_atrium_idr_source()
    test_http_and_shots()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    if FAIL:
        print(f"RESULT: FAIL {FAIL} checks failed")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
