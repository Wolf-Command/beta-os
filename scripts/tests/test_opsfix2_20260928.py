#!/usr/bin/env python3
"""OPSFIX-2. Peaches contrast, real Uma day, GGV invoice files.

Uses a short-lived Beta handler in development_assertion. Does not switch
the live :8788 process and does not touch production :8787.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["BETA_AUTH_MODE"] = "development_assertion"
sys.path.insert(0, str(ROOT / "scripts"))

import serve_beta as sb  # noqa: E402
from core import ggv_invoice_history as history  # noqa: E402
from core import owner_command  # noqa: E402
from core import uma_real_projection as real  # noqa: E402
from core.staff_home import build_home  # noqa: E402

OWNER = "mrwolf@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
DEVI = "deviputu236@gmail.com"
AMANDA = "amanda@wolfcommand.net"
YUDI = "widiatmika.11@gmail.com"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
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


def _lin(channel: int) -> float:
    value = channel / 255
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def contrast(fore: str, back: str) -> float:
    def lum(hex_color: str) -> float:
        red, green, blue = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        return 0.2126 * _lin(red) + 0.7152 * _lin(green) + 0.0722 * _lin(blue)

    lighter, darker = sorted((lum(fore), lum(back)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def call(port: int, method: str, path: str, email: str | None = None, accept: str = "application/json"):
    headers = {"Accept": accept}
    if email:
        headers["X-Wolf-Subject"] = email
    req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, method=method)
    try:
        with urlopen(req, timeout=120) as resp:
            return resp.status, resp.read(), resp.headers.get("Content-Type") or ""
    except HTTPError as exc:
        return exc.code, exc.read(), (exc.headers.get("Content-Type") if exc.headers else "") or ""


def test_contrast_and_plans() -> None:
    page = (ROOT / "dashboards" / "my-work.html").read_text(encoding="utf-8")
    check("truth card text on white passes AA", contrast("#1c1915", "#fffdf8") >= 4.5)
    check("work card text on gold passes AA", contrast("#1c1408", "#f4e4c4") >= 4.5)
    check("footnote on gold passes AA", contrast("#3f3422", "#f4e4c4") >= 4.5)
    check("page pins those colours", "#1c1915" in page and "#f4e4c4" in page and "#1c1408" in page)
    check("open plan is the action", "next_step" in page and "footnote" in page and "work-title" in page)
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        stored = conn.execute(
            "SELECT COUNT(*) FROM content_plans WHERE lower(brand_id)='habitat' AND data_lane='test'"
        ).fetchone()[0]
        check("test plans remain stored", stored == 3, str(stored))
        home = build_home("PERS-HAIKAL", conn=conn)
        items = home["sections"][0]["items"]
        ids = [row["source_id"] for row in items]
        check("staff list hides test plans", all(int(i) >= 4 for i in ids) and not any(i in {"1", "2", "3"} for i in ids), str(ids))
        # OPSFIX-3: same title+period+status collapses; Working_Draft and Human_Approved both stay.
        check("duplicate fortnight drafts collapse to one status each", len(ids) == 2, str(ids))
        check(
            "cards say what to do",
            all(row.get("next_step") == "Open plan" and row.get("date_range") and row.get("status_label") for row in items),
        )
        check("provenance stays on the row", all(row.get("origin") == "historical" and row.get("verified_by_wolf") is False for row in items))
        check("data lane is not on the staff row", all("data_lane" not in row for row in items))
        check(
            "staff footnote is plain",
            all(row.get("staff_footnote") and "verified_by_wolf" not in (row.get("staff_footnote") or "") for row in items),
        )
    finally:
        conn.close()


def test_owner_words() -> None:
    report = owner_command.build_command(verified_person_id="PERS-MATT")
    answers = {row.get("id"): row.get("answer") or "" for row in report.get("answers") or []}
    changed = answers.get("changed") or ""
    wrong = answers.get("wrong") or ""
    check("changed is plain english", "ggv.invoice" not in changed and "INVALID/TEST" not in changed and "GGV" in changed, changed[:180])
    check("changed names the invoice number", "next invoice number was set" in changed, changed[:180])
    check(
        "wrong never pretends green while exceptions are open",
        "Nothing is going wrong" not in wrong and "exceptions are open" in wrong,
        wrong[:220],
    )

def test_uma_and_invoices() -> None:
    day = real.operating_day()
    latest = (day.get("sales") or {}).get("latest") or {}
    from datetime import datetime, timedelta, timezone

    wita_today = datetime.now(timezone(timedelta(hours=8))).date()
    latest_day = datetime.strptime(latest["biz_date"], "%Y-%m-%d").date()
    expect_stale = latest_day < (wita_today - timedelta(days=1))
    check(
        "stale banner follows the day before yesterday",
        day["sales"]["stale"] is expect_stale and bool(day["sales"].get("stale_banner")) is expect_stale,
        str(day["sales"].get("stale_banner")),
    )
    check("latest sales day is present", bool(latest.get("biz_date")) and latest.get("bills", 0) > 0, str(latest.get("biz_date")))
    check("idr has no decimals", bool(re.fullmatch(r"Rp -?[\d,]+", latest.get("net_sales_idr") or "")), latest.get("net_sales_idr"))
    check("trend is seven days", len((day.get("sales") or {}).get("trend") or []) == 7)
    ex = day.get("exceptions") or {}
    check("missing cost is counted", (ex.get("missing_cost") or {}).get("count", 0) > 0)
    check("duplicate suppliers include bake house", any("bake house" in (row.get("sentence") or "").lower() for row in ex.get("duplicate_suppliers") or []))
    close = ex.get("daily_close") or {}
    check("close branch is blocked and the page is not", close.get("branch_blocked") is True and close.get("page_blocked") is False and close.get("status") == "BLOCKED")
    orders = real.list_orders(limit=5)
    check("order book is the alchemist history", orders.get("count") == 504 and orders.get("orders"), str(orders.get("count")))
    check(
        "each order names its nota or says the file is missing",
        all((row.get("photo") or {}).get("href") or (row.get("photo") or {}).get("message") == "EVIDENCE FILE NOT RECOVERABLE" for row in orders["orders"]),
    )
    check("example requests stay out", orders.get("example_rows_included") is False)
    pack = history.projection()
    numbers = [row["invoice_number"] for row in pack["invoices"]]
    check("064A 065A 066A are real files", {"064A", "065A", "066A"} <= set(numbers), str(numbers[-6:]))
    check("projection did not insert", pack.get("inserted") is False)
    row = pack["by_number"]["066A"]
    check("066A has provenance", row.get("origin") == "historical" and row.get("verified_by_wolf") is False and row.get("source_path"))
    check("066A total was read", row.get("grand_total_idr") == "Rp 263,050,160", str(row.get("grand_total_idr")))
    check("searched places are recorded", any("Gmail" in item for item in pack["searched"]) and any("pdfs" in item for item in pack["searched"]))


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


def _capture(port: int, path: str, email: str, width: int, dest: Path, marker: str) -> None:
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
            deadline = time.time() + 50
            while time.time() < deadline:
                got = cdp(
                    "Runtime.evaluate",
                    {"expression": "document.body ? document.body.innerText : ''", "returnByValue": True},
                )
                text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")
                ready = cdp(
                    "Runtime.evaluate",
                    {"expression": "document.body && document.body.getAttribute('data-ready')", "returnByValue": True},
                )
                flag = str(((ready.get("result") or {}).get("result") or {}).get("value") or "")
                if marker in text and flag == "1":
                    break
                time.sleep(0.4)
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            sock.close()
            check(f"shot {dest.name}", dest.is_file() and dest.stat().st_size > 5000 and marker in text, text[:160])
        finally:
            proc.kill()
            proc.wait(timeout=5)


def test_http_and_shots() -> None:
    from core import ggv_finance_nota as fin

    scratch = Path(tempfile.mkdtemp(prefix="opsfix2-catalog-", dir=ROOT / "state"))
    copy = scratch / "content_library.sqlite"
    shutil.copy(CATALOG, copy)
    fin.CATALOG_DB = copy
    handler = next(
        obj
        for obj in vars(sb).values()
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler"
    )
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        status, raw, _ctype = call(port, "GET", "/bzg/uma-blu")
        check("unsigned uma today 403", status == 403, str(status))
        status, raw, _ctype = call(port, "GET", "/api/staff/home", HAIKAL)
        home = json.loads(raw.decode() or "{}")
        today = ((home.get("sections") or [{}])[0]).get("items") or []
        check("haikal api hides test plans", status == 200 and len(today) == 2 and "1" not in [row.get("source_id") for row in today], str([row.get("source_id") for row in today]))
        status, raw, _ctype = call(port, "GET", "/api/owner/command", OWNER)
        body = json.loads(raw.decode() or "{}")
        answers = {row.get("id"): row.get("answer") or "" for row in body.get("answers") or []}
        check("owner http changed is plain", "ggv.invoice" not in answers.get("changed", "") and "On " in answers.get("changed", ""))
        status, raw, _ctype = call(port, "GET", "/api/bzg/uma-blu/real/operating-day", DEVI)
        day = json.loads(raw.decode() or "{}")
        check("devi operating day", status == 200 and (day.get("sales") or {}).get("latest"), str(status))
        status, raw, _ctype = call(port, "GET", "/api/bzg/uma-blu/real/operating-day", YUDI)
        check("creator operating day 403", status == 403, str(status))
        status, raw, _ctype = call(port, "GET", "/api/ggv/finance/invoices", AMANDA)
        invoices = json.loads(raw.decode() or "{}")
        hist = invoices.get("historical") or {}
        nums = {row.get("invoice_number") for row in hist.get("invoices") or []}
        check("amanda sees 064A to 066A", status == 200 and {"064A", "065A", "066A"} <= nums, str(status))
        check("next number stays 067A", (invoices.get("numbering") or {}).get("next") == "067A")
        status, raw, ctype = call(port, "GET", "/api/ggv/finance/invoices/historical/066A/file", AMANDA, accept="application/pdf")
        check("066A file is a pdf", status == 200 and raw[:4] == b"%PDF" and "pdf" in ctype, f"{status} {ctype}")
        status, _raw, _ctype = call(port, "GET", "/api/ggv/finance/invoices/historical/066A/file", DEVI, accept="application/pdf")
        check("devi cannot open a ggv invoice file", status == 403, str(status))
        if not CHROME.is_file():
            check("chrome for screenshots", False, "Chrome missing")
            return
        shots = (
            ("/my-work", HAIKAL, 1024, "opsfix2-haikal-mywork.png", "Open plan"),
            ("/wolf", OWNER, 1024, "opsfix2-owner-wolf.png", "next invoice number was set"),
            ("/bzg/uma-blu", DEVI, 1024, "opsfix2-uma-today-desktop.png", "bills"),
            ("/bzg/uma-blu", DEVI, 390, "opsfix2-uma-today-phone.png", "bills"),
            ("/bzg/uma-blu/bills", DEVI, 1024, "opsfix2-uma-bills.png", "EVIDENCE FILE NOT RECOVERABLE"),
            ("/ggv/finance/invoices", AMANDA, 1024, "opsfix2-amanda-invoices.png", "066A"),
        )
        for path, email, width, name, marker in shots:
            _capture(port, path, email, width, SHOTS / name, marker)
    finally:
        httpd.shutdown()
        httpd.server_close()
        shutil.rmtree(scratch, ignore_errors=True)


def main() -> int:
    test_contrast_and_plans()
    test_owner_words()
    test_uma_and_invoices()
    test_http_and_shots()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    if FAIL:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
