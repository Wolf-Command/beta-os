#!/usr/bin/env python3
"""UMAREAL-1. Provenance, no example rows, incomplete cost stays blank, no ESB write."""
from __future__ import annotations

import base64
import json
import os
import re
import socket
import sqlite3
import struct
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["BETA_AUTH_MODE"] = "development_assertion"
os.environ["UMA_REAL_DRAFT_DB"] = str(Path(tempfile.mkdtemp(prefix="umareal-draft-")) / "drafts.sqlite")

import sys

sys.path.insert(0, str(ROOT / "scripts"))

from core import uma_real_projection as real  # noqa: E402
from core.staff_access import FINANCE_EMAIL  # noqa: E402

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SHOTS = ROOT / "docs" / "wolf" / "staff" / "shots"
DEVI = "deviputu236@gmail.com"
AMANDA = "amanda@wolfcommand.net"
REGISTER = ROOT / "state" / "bzg" / "data-source-register.json"
NEW_FILES = (
    ROOT / "scripts" / "core" / "uma_real_projection.py",
    ROOT / "dashboards" / "bzg-uma-blu-real.html",
)
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


def ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only=ON")
    return conn


def live_count(path: Path, sql: str) -> int:
    conn = ro(path)
    try:
        return int(conn.execute(sql).fetchone()[0])
    finally:
        conn.close()


def test_projection() -> None:
    recipes = real.list_recipes(limit=127)
    check("127 dishes", recipes["count"] == 127, str(recipes["count"]))
    check("no example flag on recipes", recipes["example_rows_included"] is False)
    incomplete = next(row for row in recipes["recipes"] if row["food_cost_status"] != "COMPLETE")
    dish = real.get_recipe(incomplete["recipe_id"])
    assert dish is not None
    for row in (dish, *dish["lines"]):
        missing = [key for key in real.PROVENANCE_KEYS if key not in row]
        check(f"provenance {row.get('source_id')}", not missing, str(missing))
        check(
            f"unverified {row.get('source_id')}",
            row["verified_by_wolf"] is False and row["origin"] == "historical",
        )
    check("dish provenance", all(key in dish for key in real.PROVENANCE_KEYS))
    check("missing cost has no dish total", dish["food_cost"] is None and dish["food_cost_status"] == "INCOMPLETE")
    check(
        "missing line has no extended cost",
        any(line["cost_badge"] == "MISSING COST" and line["extended_cost"] is None for line in dish["lines"]),
    )
    synthetic = real.rollup_food_cost(
        [
            {"cost_badge": None, "extended_cost": 10},
            {"cost_badge": "MISSING COST", "extended_cost": None},
        ]
    )
    check("synthetic missing cost is not numeric", synthetic["food_cost"] is None)
    orders = real.list_orders(limit=50)
    blob = json.dumps(orders)
    check("orders are alchemist historical", orders["count"] == 504 and "PR-UMA-EXAMPLE" not in blob, str(orders["count"]))
    suppliers = real.list_suppliers(limit=200)
    check("103 suppliers", suppliers["count"] == 103, str(suppliers["count"]))
    check("supplier provenance", all(key in suppliers["suppliers"][0] for key in real.PROVENANCE_KEYS))
    receipts = real.list_receipts(limit=1)
    check("452 receipt lines", receipts["count"] == 452, str(receipts["count"]))
    sales = real.list_sales(limit=3)
    check("8762 sales", sales["count"] == 8762 and sales["biz_date_max"] == "2026-09-27")
    check("no esb call", sales["inline_call_issued"] is False)
    check("sales provenance", all(key in sales["sales"][0] for key in real.PROVENANCE_KEYS))
    check("sales omits contact fields", "phoneNumber" not in sales["sales"][0] and "email" not in sales["sales"][0])
    report = real.menu_map_report()
    check("no guessed confirmed maps", report["guessed_confirmed"] == 0)
    check(
        "map partitions recipes",
        report["mapped"] + report["ambiguous"] + report["recipes_without_esb_item"] == report["recipe_count"],
    )
    theory = real.theoretical_consumption(date_from="2026-09-27", date_to="2026-09-27")
    check("theoretical label", theory["label"] == "THEORETICAL" and theory["finished_bills"] == 61)
    if theory["lines"]:
        check("theoretical provenance", all(key in theory["lines"][0] for key in real.PROVENANCE_KEYS))
    closes = real.daily_close_history()
    check("daily close none found", closes["status"] == "NONE FOUND" and closes["threshold"] is None)
    conn = ro(real.RECIPES_DB)
    try:
        before_at = conn.execute("SELECT updated_at FROM recipes WHERE id='buddha-bowl-tempeh'").fetchone()[0]
    finally:
        conn.close()
    draft = real.create_draft("buddha-bowl-tempeh", "beta draft note", created_by="PERS-DEVI")
    conn = ro(real.RECIPES_DB)
    try:
        after_at = conn.execute("SELECT updated_at FROM recipes WHERE id='buddha-bowl-tempeh'").fetchone()[0]
    finally:
        conn.close()
    check("draft does not rewrite history", before_at == after_at and draft["origin"] == "wolf_draft")
    check("draft unverified", draft["verified_by_wolf"] is False and draft["historical_overwritten"] is False)


def test_register() -> None:
    payload = json.loads(REGISTER.read_text(encoding="utf-8"))
    by_source = {row["source"]: row["record_count"] for row in payload["datasets"]}
    expect = {
        "wolf-system/uma-blu/recipes.sqlite recipes": live_count(real.RECIPES_DB, "SELECT COUNT(*) FROM recipes"),
        "wolf-system/uma-blu/recipes.sqlite recipe_lines": live_count(real.RECIPES_DB, "SELECT COUNT(*) FROM recipe_lines"),
        "alchemist.db suppliers": live_count(real.ALCHEMIST_DB, "SELECT COUNT(*) FROM suppliers"),
        "alchemist.db pr_orders": live_count(real.ALCHEMIST_DB, "SELECT COUNT(*) FROM pr_orders"),
        "alchemist.db pr_receipt_lines": live_count(real.ALCHEMIST_DB, "SELECT COUNT(*) FROM pr_receipt_lines"),
        "esb.sqlite sales": live_count(real.ESB_DB, "SELECT COUNT(*) FROM sales"),
        "esb.sqlite menus": live_count(real.ESB_DB, "SELECT COUNT(*) FROM menus"),
        "catalog content_library.sqlite venue_daily_closes": live_count(
            real.CATALOG_DB, "SELECT COUNT(*) FROM venue_daily_closes"
        ),
        "catalog content_library.sqlite bzg_ops_purchase_requests example=1": live_count(
            real.CATALOG_DB, "SELECT COUNT(*) FROM bzg_ops_purchase_requests WHERE example=1"
        ),
    }
    for source, count in expect.items():
        check(f"register {source}", by_source.get(source) == count, f"file={by_source.get(source)} live={count}")
    files = [path for path in real.NOTAS_DIR.iterdir() if path.is_file() and path.suffix.lower() == ".jpg"]
    check(
        "register nota files",
        by_source.get("alchemist/notas jpg files") == len(files),
        f"file={by_source.get('alchemist/notas jpg files')} live={len(files)}",
    )
    check("cut lines present", len(payload["cut_lines"]) == 10)
    check("commissioning dates null", all(row["wolf_commissioning_date"] is None for row in payload["cut_lines"]))


def test_source_hygiene() -> None:
    import inspect
    import serve_beta

    handler = next(
        obj
        for obj in vars(serve_beta).values()
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler"
    )
    text = "\n".join(path.read_text(encoding="utf-8") for path in NEW_FILES)
    text += "\n" + inspect.getsource(handler._uma_real_get)
    text += "\n" + inspect.getsource(handler._uma_real_draft)
    check("no esb host", "esb.co.id" not in text)
    check("no http client", "urllib.request" not in text and "requests." not in text)
    check("no sales insert", "INSERT INTO sales" not in text and "INSERT INTO menus" not in text)
    check("no secret assignment", re.search(r"(password\s*=\s*\S+|bearer\s+[A-Za-z0-9._\-]{8,})", text, re.I) is None)
    check("draft insert is local", "INSERT INTO recipe_drafts" in (ROOT / "scripts" / "core" / "uma_real_projection.py").read_text(encoding="utf-8"))


def _ws_connect(host: str, port: int, path: str) -> socket.socket:
    sock = socket.create_connection((host, port), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall(
        (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode()
    )
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
    return sock


def _ws_send(sock: socket.socket, text: str) -> None:
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


def _ws_recv(sock: socket.socket) -> str:
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


def _capture(port: int, path: str, width: int, dest: Path, marker: str) -> None:
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
            cdp("Network.setExtraHTTPHeaders", {"headers": {"X-Wolf-Subject": DEVI}})
            cdp("Page.enable")
            cdp(
                "Emulation.setDeviceMetricsOverride",
                {"width": width, "height": 900, "deviceScaleFactor": 1, "mobile": width < 500},
            )
            cdp("Page.navigate", {"url": f"http://127.0.0.1:{port}{path}"})
            text = ""
            deadline = time.time() + 40
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
                time.sleep(0.3)
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            sock.close()
            check(f"shot {dest.name}", dest.is_file() and dest.stat().st_size > 5000 and marker in text, text[:180])
        finally:
            proc.kill()
            proc.wait(timeout=5)


def test_http_and_shots() -> None:
    import serve_beta

    handler = next(
        obj
        for obj in vars(serve_beta).values()
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler"
    )
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def call(path: str, email: str | None, method: str = "GET", body: bytes | None = None) -> tuple[int, bytes]:
        sock = socket.create_connection(("127.0.0.1", port), timeout=60)
        headers = [f"{method} {path} HTTP/1.1", "Host: 127.0.0.1", "Connection: close"]
        if email:
            headers.append(f"X-Wolf-Subject: {email}")
        if body is not None:
            headers.append("Content-Type: application/json")
            headers.append(f"Content-Length: {len(body)}")
        sock.sendall(("\r\n".join(headers) + "\r\n\r\n").encode() + (body or b""))
        data = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
        sock.close()
        status = int(data.split(b" ", 2)[1])
        return status, data.split(b"\r\n\r\n", 1)[-1]

    try:
        status, _body = call("/api/bzg/uma-blu/real/recipes", None)
        check("unsigned recipes 403", status == 403, str(status))
        status, _body = call("/bzg/uma-blu/recipes", AMANDA)
        check("ggv recipes page 403", status == 403, str(status))
        status, _body = call("/api/bzg/uma-blu/real/sales", FINANCE_EMAIL)
        check("amg sales 403", status == 403, str(status))
        status, body = call("/api/bzg/uma-blu/real/recipes?limit=127", DEVI)
        payload = json.loads(body.decode())
        check("devi sees 127", status == 200 and payload.get("count") == 127, str(status))
        status, page = call("/bzg/uma-blu/recipes", DEVI)
        check("devi recipe page", status == 200 and b"umareal" not in b"" and b"Recipes" in page, str(status))
        nota = next(path.name for path in real._evidence_files() if path.name.startswith("nota_"))
        status, body = call("/api/bzg/uma-blu/real/evidence/" + quote(nota) + "/file", DEVI)
        check("nota file is jpeg", status == 200 and body[:3] == b"\xff\xd8\xff", str(status))
        status, body = call("/api/bzg/uma-blu/real/evidence/" + quote(nota) + "/file", AMANDA)
        check("ggv nota 403", status == 403, str(status))
        if not CHROME.is_file():
            check("chrome for screenshots", False, "Chrome missing")
            return
        shots = (
            ("/bzg/uma-blu/recipes", 1280, "umareal-recipes-desktop.png", "127 dishes"),
            ("/bzg/uma-blu/recipes", 390, "umareal-recipes-phone.png", "127 dishes"),
            ("/bzg/uma-blu/recipes/buddha-bowl-tempeh", 1280, "umareal-recipe-detail-desktop.png", "MISSING COST"),
            ("/bzg/uma-blu/recipes/buddha-bowl-tempeh", 390, "umareal-recipe-detail-phone.png", "MISSING COST"),
            ("/bzg/uma-blu/purchasing", 1280, "umareal-purchasing-desktop.png", "103 suppliers"),
            ("/bzg/uma-blu/purchasing", 390, "umareal-purchasing-phone.png", "103 suppliers"),
            (f"/bzg/uma-blu/notas/{quote(nota)}", 1280, "umareal-nota-desktop.png", "Alchemist historical"),
            (f"/bzg/uma-blu/notas/{quote(nota)}", 390, "umareal-nota-phone.png", "Alchemist historical"),
            ("/bzg/uma-blu/sales", 1280, "umareal-sales-desktop.png", "8762"),
            ("/bzg/uma-blu/sales", 390, "umareal-sales-phone.png", "8762"),
            ("/bzg/uma-blu/menu-map", 1280, "umareal-menu-map-desktop.png", "Mapped"),
            ("/bzg/uma-blu/menu-map", 390, "umareal-menu-map-phone.png", "Mapped"),
        )
        for path, width, name, marker in shots:
            _capture(port, path, width, SHOTS / name, marker)
    finally:
        httpd.shutdown()


def main() -> int:
    test_projection()
    test_register()
    test_source_hygiene()
    test_http_and_shots()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
