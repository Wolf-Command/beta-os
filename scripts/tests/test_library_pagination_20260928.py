#!/usr/bin/env python3
"""LIBPAGE-1 — library page window, server page size, and address-bar state.

Temp catalog for the search checks. Screenshots use a short-lived Beta handler
in development_assertion. Does not switch the live :8788 process.
"""
from __future__ import annotations

import base64
import inspect
import json
import os
import socket
import sqlite3
import struct
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
import sys

sys.path.insert(0, str(SCRIPTS))

from core import content_engine_repair as repair  # noqa: E402

HTML = ROOT / "dashboards" / "content-2.0.html"
SHOTS = ROOT / "docs" / "wolf" / "staff" / "shots"
HAIKAL = "haikalqilbari123@gmail.com"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

PASS = 0
FAIL = 0


def log(ok: bool, name: str, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def extract_function(src: str, name: str) -> str:
    needle = f"function {name}("
    start = src.find(needle)
    if start < 0:
        raise AssertionError(f"missing {name}")
    brace = src.find("{", start)
    depth = 0
    for idx in range(brace, len(src)):
        char = src[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return src[start : idx + 1]
    raise AssertionError(f"unclosed {name}")


def test_window() -> None:
    cases = [
        (1, 10, 2, [1, 2, 3, "ellipsis", 10]),
        (2, 10, 2, [1, 2, 3, 4, "ellipsis", 10]),
        (5, 10, 2, [1, 2, 3, 4, 5, 6, 7, "ellipsis", 10]),
        (10, 20, 1, [1, "ellipsis", 9, 10, 11, "ellipsis", 20]),
        (1, 1, 2, [1]),
        (0, 5, 2, [1, 2, 3, 4, 5]),
        (99, 4, 2, [1, 2, 3, 4]),
        (3, 0, 2, []),
    ]
    for current, pages, neighbours, expect in cases:
        got = repair.library_page_window(current, pages, neighbours)
        log(got == expect, f"window {current}/{pages} n={neighbours}", str(got))
    log(repair.clamp_library_page(0, 8) == 1, "clamp low")
    log(repair.clamp_library_page(40, 8) == 8, "clamp high")
    log(repair.clamp_library_page(3, 8) == 3, "clamp inside")


def seed(path: Path, count: int = 120) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE assets (id INTEGER PRIMARY KEY)")
    repair._nas_index_columns(conn)
    for n in range(count):
        conn.execute(
            """
            INSERT INTO nas_index (
              original_path, original_filename, rel, size, brand_slug, index_state, classification
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (
                f"/tmp/libpage-{n}.jpg",
                f"clip-{n:04d}.jpg",
                f"Atrium/clip-{n:04d}.jpg",
                100 + n,
                "atrium",
                "INDEXED",
                "image",
            ),
        )
    conn.commit()
    return conn


def test_server_page() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        conn = seed(Path(tmp) / "catalog.sqlite", 120)
        try:
            scopes = ["SCOPE-WOLF-CONTENT-ALL-BRANDS"]
            wide = repair.nas_library_search(conn, scopes, "atrium", limit=500, page=1)
            log(wide["limit"] == 48, "limit caps at 48", str(wide["limit"]))
            log(len(wide["cards"]) == 48, "page returns 48", str(len(wide["cards"])))
            log(wide["matched"] == 120 and wide["total"] == 120, "total is the index count", str(wide["total"]))
            log(wide["pages"] == 3 and wide["page"] == 1, "three pages", f"{wide['page']}/{wide['pages']}")
            log(wide["staff_ready"] is False, "staff_ready stays false")
            second = repair.nas_library_search(conn, scopes, "atrium", limit=48, page=2)
            third = repair.nas_library_search(conn, scopes, "atrium", limit=10, page=2)
            log(second["total"] == wide["total"] == 120, "total stable across pages", str(second["total"]))
            log(second["matched"] == wide["matched"], "matched stable across pages")
            log(len(third["cards"]) == 10 and third["limit"] == 10, "smaller limit honoured", str(third["limit"]))
            ids1 = {c["id"] for c in wide["cards"]}
            ids2 = {c["id"] for c in second["cards"]}
            log(ids1.isdisjoint(ids2) and len(ids2) == 48, "page 2 is a different slice", str(len(ids2)))
            log(len(wide["cards"]) < wide["matched"], "browser page is not the full match set")
            clamped = repair.nas_library_search(conn, scopes, "atrium", limit=48, page=99999)
            log(
                clamped["page"] == 3 and clamped["offset"] == 96 and clamped["total"] == 120 and len(clamped["cards"]) == 24,
                "high page clamps to the last page",
                f"page={clamped['page']} offset={clamped['offset']} n={len(clamped['cards'])}",
            )
            low = repair.nas_library_search(conn, scopes, "atrium", limit=48, page=0)
            log(low["page"] == 1 and low["offset"] == 0 and low["total"] == 120, "page 0 clamps to 1")
            by_offset = repair.nas_library_search(conn, scopes, "atrium", limit=48, offset=100000)
            log(
                by_offset["page"] == 3 and by_offset["offset"] == 96 and by_offset["total"] == 120,
                "high offset clamps",
                f"page={by_offset['page']} offset={by_offset['offset']}",
            )
            prefer = repair.nas_library_search(conn, scopes, "atrium", limit=48, offset=0, page=2)
            log(prefer["page"] == 2 and prefer["offset"] == 48, "page wins over offset")
            log("matched" in wide and "limit" in wide and "offset" in wide, "existing page fields stay")
        finally:
            conn.close()


def test_url_and_markup() -> None:
    raw = HTML.read_text(encoding="utf-8")
    log('id="libPrev"' in raw and ">PREV<" in raw, "previous control")
    log('id="libNext"' in raw and ">NEXT<" in raw, "next control")
    log('aria-current="page"' in raw, "current page marker")
    log("history.pushState" in raw and "popstate" in raw, "history push and pop")
    log('q.set("nas_limit", "48")' in raw and 'q.set("page"' in raw, "request is one page")
    log("indexed files match · Showing" in raw, "staff count sentence")
    log("The whole NAS is not complete." not in raw, "count sentence has no engineering tail")
    log('id="libDownloadSel"' in raw and "/api/assets/zip" in raw, "zip download stays")
    log("min-height: 44px" in raw and "overflow-x: clip" in raw, "tap target and clip")
    route = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    log('"nas_matched"' in route and '"nas_total"' in route and '"page":' in route, "api keeps matched and adds total/page")
    try:
        js = "\n".join(
            extract_function(raw, name)
            for name in ("libraryClampPage", "libraryPageWindow", "libraryUrlQuery")
        )
    except AssertionError as exc:
        log(False, "extract pager script", str(exc))
        return
    script = js + r"""
const windowCases = [
  [1, 10, 2, [1, 2, 3, "ellipsis", 10]],
  [10, 20, 1, [1, "ellipsis", 9, 10, 11, "ellipsis", 20]],
  [99, 4, 2, [1, 2, 3, 4]],
];
for (const [current, pages, neighbours, expect] of windowCases) {
  const got = libraryPageWindow(current, pages, neighbours);
  if (JSON.stringify(got) !== JSON.stringify(expect)) {
    console.log("FAIL window", current, JSON.stringify(got));
    process.exit(1);
  }
}
if (libraryClampPage(0, 8) !== 1 || libraryClampPage(40, 8) !== 8) {
  console.log("FAIL clamp");
  process.exit(1);
}
const q = libraryUrlQuery({
  q: "pool",
  brand: "atrium",
  media_type: "video",
  stage: "FINAL",
  readiness: "READY_TO_USE",
  shoot_date: "2026-09-01",
  subject: "lobby",
  location: "lombok",
  sort: "newest",
  page: 3,
});
const params = new URLSearchParams(q);
for (const key of ["q", "brand", "media_type", "stage", "readiness", "shoot_date", "subject", "location", "sort", "page"]) {
  if (!params.get(key)) {
    console.log("FAIL missing", key, q);
    process.exit(1);
  }
}
if (params.get("page") !== "3" || params.get("brand") !== "atrium" || params.get("sort") !== "newest") {
  console.log("FAIL values", q);
  process.exit(1);
}
const first = new URLSearchParams(libraryUrlQuery({ q: "pool", brand: "atrium", sort: "newest", page: 1 }));
if (first.has("page")) {
  console.log("FAIL page 1 should omit page");
  process.exit(1);
}
console.log("OK");
"""
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=20)
    log(proc.returncode == 0 and "OK" in proc.stdout, "js window and url", (proc.stdout or proc.stderr)[-240:])


def _handler():
    os.environ["BETA_AUTH_MODE"] = "development_assertion"
    import serve_beta as sb

    for _, obj in inspect.getmembers(sb, inspect.isclass):
        if obj is BaseHTTPRequestHandler or not issubclass(obj, BaseHTTPRequestHandler):
            continue
        if obj.__name__ == "BetaHandler" or hasattr(obj, "_try_serve_shell_html"):
            return obj
    return None


def _get(port: int, path: str, subject: str | None) -> tuple[int, dict | str]:
    headers = {"Accept": "application/json"}
    if subject:
        headers["X-Wolf-Subject"] = subject
    req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, method="GET")
    try:
        with urlopen(req, timeout=30) as resp:
            body = resp.read()
            code = resp.status
    except HTTPError as exc:
        body = exc.read()
        code = exc.code
    try:
        return code, json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return code, body.decode("utf-8", "replace")


_TINY_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////"
    "2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAj/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAGf/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9k="
)


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
    elif length < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack(">H", length))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack(">Q", length))
    header.extend(mask)
    masked = bytes(byte ^ mask[i % 4] for i, byte in enumerate(data))
    sock.sendall(bytes(header) + masked)


def _ws_recv(sock: socket.socket) -> str:
    def read(n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("socket closed")
            buf += chunk
        return buf

    while True:
        head = read(2)
        opcode = head[0] & 0x0F
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
        fin = head[0] & 0x80
        if opcode == 8:
            raise ConnectionError("websocket closed")
        if opcode == 9:
            continue
        if opcode in (0, 1, 2):
            parts = [payload]
            while not fin:
                head = read(2)
                fin = head[0] & 0x80
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
                parts.append(payload)
            if opcode == 2:
                continue
            return b"".join(parts).decode()


def _capture(chrome: Path, proxy_port: int, path: str, width: int, height: int, dest: Path) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:
        proc = subprocess.Popen(
            [
                str(chrome),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--no-first-run",
                "--disable-extensions",
                "--remote-debugging-port=0",
                f"--user-data-dir={profile}",
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
            page = next((tab for tab in tabs if tab.get("type") == "page"), None)
            if page is None:
                raise RuntimeError(f"no page target: {tabs!r}"[:300])
            ws_url = page["webSocketDebuggerUrl"]
            ws_path = ws_url.split("/", 3)[-1]
            sock = _ws_connect("127.0.0.1", dbg_port, "/" + ws_path)
            sock.settimeout(40)
            seq = 0

            def call(method: str, params: dict | None = None) -> dict:
                nonlocal seq
                seq += 1
                ident = seq
                _ws_send(sock, json.dumps({"id": ident, "method": method, "params": params or {}}))
                while True:
                    msg = json.loads(_ws_recv(sock))
                    if msg.get("id") == ident:
                        return msg

            call("Page.enable")
            call("Emulation.setDeviceMetricsOverride", {
                "width": width,
                "height": height,
                "deviceScaleFactor": 1,
                "mobile": width < 500,
            })
            nav = call("Page.navigate", {"url": f"http://127.0.0.1:{proxy_port}{path}"})
            if (nav.get("result") or {}).get("errorText"):
                raise RuntimeError(str(nav.get("result"))[:300])
            probe = """
              (() => {
                const note = document.getElementById("libPageNote");
                const cur = document.querySelector("[aria-current='page']");
                const btn = document.querySelector(".lib-page-btn");
                const box = btn ? btn.getBoundingClientRect() : null;
                return {
                  note: note ? note.textContent : "",
                  current: cur ? cur.textContent : "",
                  prevDisabled: !!(document.getElementById("libPrev") || {}).disabled,
                  scroll: document.documentElement.scrollWidth,
                  client: document.documentElement.clientWidth,
                  tap: box ? Math.round(box.height) : 0,
                };
              })()
            """
            facts: dict = {}
            deadline = time.time() + 25
            while time.time() < deadline:
                got = call("Runtime.evaluate", {"expression": probe, "returnByValue": True})
                facts = ((got.get("result") or {}).get("result") or {}).get("value") or {}
                if "indexed files match" in str(facts.get("note") or ""):
                    break
                time.sleep(0.3)
            else:
                raise RuntimeError(f"pager did not paint: {facts}")
            call("Page.stopLoading")
            shot = call("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            data = base64.b64decode(((shot.get("result") or {}).get("data") or ""))
            dest.write_bytes(data)
            sock.close()
            return facts
        finally:
            proc.kill()
            proc.wait(timeout=5)


def test_route_and_shots() -> None:
    if not CHROME.is_file():
        log(False, "chrome for screenshots", "Chrome missing")
        return
    Handler = _handler()
    if Handler is None:
        log(False, "beta handler", "not found")
        return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    class _Proxy(BaseHTTPRequestHandler):
        def log_message(self, *_args):  # noqa: ANN002
            return

        def do_GET(self):  # noqa: N802
            bare = self.path.split("?", 1)[0]
            if bare.endswith("/preview"):
                body = _TINY_JPEG
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            req = Request(
                f"http://127.0.0.1:{port}{self.path}",
                headers={"X-Wolf-Subject": HAIKAL, "Accept": self.headers.get("Accept") or "*/*"},
                method="GET",
            )
            try:
                with urlopen(req, timeout=60) as resp:
                    body = resp.read()
                    ctype = resp.headers.get("Content-Type") or "text/html"
                    code = resp.status
            except HTTPError as exc:
                body = exc.read()
                ctype = exc.headers.get("Content-Type") if exc.headers else "text/html"
                code = exc.code
            except (URLError, TimeoutError, ConnectionError):
                body = b""
                ctype = "text/plain"
                code = 502
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    proxy = ThreadingHTTPServer(("127.0.0.1", 0), _Proxy)
    pport = proxy.server_address[1]
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    try:
        unsigned, _ = _get(port, "/api/assets?brand=atrium&page=1&limit=48", None)
        log(unsigned == 403, "unsigned assets stay 403 on the harness", str(unsigned))
        code1, page1 = _get(port, "/api/assets?brand=atrium&page=1&nas_limit=48", HAIKAL)
        code2, page2 = _get(port, "/api/assets?brand=atrium&page=2&limit=48", HAIKAL)
        code_hi, page_hi = _get(port, "/api/assets?brand=atrium&page=99999&limit=48", HAIKAL)
        ok_pages = (
            code1 == 200
            and code2 == 200
            and isinstance(page1, dict)
            and isinstance(page2, dict)
        )
        log(ok_pages, "signed library pages", f"{code1}/{code2}")
        if ok_pages:
            total1 = int(page1.get("total") if page1.get("total") is not None else page1.get("nas_total") or -1)
            total2 = int(page2.get("total") if page2.get("total") is not None else page2.get("nas_total") or -2)
            nas1 = [a for a in page1.get("assets") or [] if str(a.get("id", "")).startswith("nas:")]
            nas2 = [a for a in page2.get("assets") or [] if str(a.get("id", "")).startswith("nas:")]
            log(total1 == total2 and total1 > 48, "route total stable", f"{total1}")
            log(len(nas1) <= 48 and len(nas2) <= 48, "route page size", f"{len(nas1)}/{len(nas2)}")
            log("nas_matched" in page1 and page1.get("page") == 1 and page2.get("page") == 2, "route page field")
            log(
                isinstance(page_hi, dict) and int(page_hi.get("page") or 0) >= 2 and int(page_hi.get("total") or -1) == total1,
                "route clamps a high page",
                str(page_hi.get("page") if isinstance(page_hi, dict) else code_hi),
            )
        desk = "/content-2.0?brand=atrium&sort=newest#library"
        page3 = "/content-2.0?brand=atrium&q=atrium&media_type=video&sort=newest&page=3#library"
        desktop = SHOTS / "library-pagination-desktop.png"
        phone = SHOTS / "library-pagination-phone.png"
        third = SHOTS / "library-pagination-page3-desktop.png"
        desk_facts = _capture(CHROME, pport, desk, 1280, 900, desktop)
        phone_facts = _capture(CHROME, pport, desk, 390, 844, phone)
        page3_facts = _capture(CHROME, pport, page3, 1280, 900, third)
        for name, path in (("desktop", desktop), ("phone", phone), ("page 3", third)):
            log(path.is_file() and path.stat().st_size > 5000, f"screenshot {name}", str(path.stat().st_size if path.is_file() else 0))
        log("indexed files match" in str(desk_facts.get("note") or ""), "desktop count sentence", str(desk_facts.get("note")))
        log(str(desk_facts.get("current") or "") == "1", "desktop opens on page 1", str(desk_facts.get("current")))
        log(bool(desk_facts.get("prevDisabled")), "previous is disabled on the first page")
        log(str(page3_facts.get("current") or "") == "3", "page 3 is the current page", str(page3_facts.get("current")))
        log("indexed files match" in str(page3_facts.get("note") or ""), "page 3 count sentence", str(page3_facts.get("note")))
        scroll = int(phone_facts.get("scroll") or 0)
        client = int(phone_facts.get("client") or 0)
        log(client > 0 and scroll <= client + 1, "phone has no horizontal scroll", f"scroll={scroll} client={client}")
        log(int(phone_facts.get("tap") or 0) >= 44, "phone page button is at least 44px", str(phone_facts.get("tap")))
    finally:
        proxy.shutdown()
        httpd.shutdown()


def main() -> None:
    test_window()
    test_server_page()
    test_url_and_markup()
    test_route_and_shots()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
