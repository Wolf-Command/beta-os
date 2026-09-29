#!/usr/bin/env python3
"""MYWORK-1B — readability repair after MYWORK-1 (Beta only).

Decision served: Matt 29 Sep 2026 07:20 P0 UNIVERSAL MY WORK (extend).
Contrast, header overlap, WITA timestamps, single TODAY, fixture isolation.
Uses a short-lived Beta handler. Does not touch production :8787.
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
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["BETA_AUTH_MODE"] = "development_assertion"
sys.path.insert(0, str(ROOT / "scripts"))

import serve_beta as sb  # noqa: E402
from core import universal_my_work as umw  # noqa: E402
from core import work_items as wi  # noqa: E402
from core.staff_home import build_home  # noqa: E402

OWNER = "mrwolf@wolfcommand.net"
DEVI = "deviputu236@gmail.com"
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
    value = channel / 255.0
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def contrast(fore: str, back: str) -> float:
    def lum(hex_color: str) -> float:
        red, green, blue = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        return 0.2126 * _lin(red) + 0.7152 * _lin(green) + 0.0722 * _lin(blue)

    lighter, darker = sorted((lum(fore), lum(back)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def call(port: int, method: str, path: str, email: str | None = None, body: dict | None = None):
    headers = {"Accept": "application/json"}
    data = None
    if email:
        headers["X-Wolf-Subject"] = email
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, data=data, method=method)
    try:
        with urlopen(req, timeout=120) as resp:
            return resp.status, resp.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def test_contrast_tokens() -> None:
    item = (ROOT / "dashboards" / "my-work-item.html").read_text(encoding="utf-8")
    report = (ROOT / "dashboards" / "execution-report.html").read_text(encoding="utf-8")
    work = (ROOT / "dashboards" / "my-work.html").read_text(encoding="utf-8")
    check("item pins work-ink", "--work-ink: #1c1915" in item and "--work-card: #fffdf8" in item)
    check("item pins work-muted", "--work-muted: #3f3422" in item)
    check("report pins work-ink", "--work-ink: #1c1915" in report and ".sentence" in report)
    check("ink on cream AA", contrast("#1c1915", "#fffdf8") >= 4.5)
    check("muted on cream AA", contrast("#3f3422", "#fffdf8") >= 4.5)
    check("work card meta AA", contrast("#3f3422", "#f4e4c4") >= 4.5)
    check("pale shell text fails on cream", contrast("#eaf3f2", "#fffdf8") < 4.5)
    check("item forces card ink", "color: var(--work-ink) !important" in item)
    check("report forces card ink", "color: var(--work-ink) !important" in report)
    check("my-work hides duplicate prompt", "display: none" in work and "MYWORK-1B" in work)
    shell = (ROOT / "dashboards" / "assets" / "wolf-shell.css").read_text(encoding="utf-8")
    check("shell select min-width 0", "min-width: 0" in shell and "MYWORK-1B" in shell)


def test_timezone_wita() -> None:
    shown = umw.format_wita("2026-09-29T00:36:43Z")
    check("utc Z becomes WITA", shown.endswith(" WITA") and "2026-09-29 08:36" in shown, shown)
    check("empty stays empty", umw.format_wita("") == "")
    check("garbage passthrough", umw.format_wita("not-a-date") == "not-a-date")

    tmp = Path(tempfile.mkdtemp(prefix="tmp-mywork1b-tz-", dir=str(ROOT / "state")))
    db = tmp / "c.sqlite"
    blobs = tmp / "blobs"
    blobs.mkdir()
    os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = str(blobs)
    shutil.copy2(CATALOG, db)
    conn = wi.db_connect(db)
    try:
        it = wi.create_work_item(
            title="MYWORK-1B tz fixture",
            owning_entity_id="ENT-GGV",
            source_type="SYSTEM",
            created_by_actor_type="SYSTEM",
            owner_person_id="PERS-MATT",
            conn=conn,
            commit=False,
        )
        wid = it["work_item_id"]
        conn.execute(
            "UPDATE core_work_items SET origin='test', accountable_person_id='PERS-MATT', executor_person_id='PERS-MATT' WHERE work_item_id=?",
            (wid,),
        )
        umw.delegate_work(wid, from_person_id="PERS-MATT", to_person_id="PERS-HAIKAL", conn=conn, commit=False)
        conn.execute(
            "UPDATE core_work_delegations SET offered_at=?, accepted_at=? WHERE work_item_id=?",
            ("2026-09-29T00:36:43Z", "2026-09-29T00:36:43Z", wid),
        )
        chain = umw.delegation_chain(wid, conn=conn)
        hop = chain[0]
        check("store raw stays Z", str(hop.get("accepted_at") or "").endswith("Z"), str(hop.get("accepted_at")))
        disp = hop.get("accepted_at_display") or ""
        check(
            "display is WITA",
            disp.endswith(" WITA") and "T" not in disp.replace(" WITA", ""),
            disp,
        )
        conn.commit()
        leaked = sqlite3.connect(str(CATALOG)).execute(
            "SELECT COUNT(*) FROM core_work_items WHERE title='MYWORK-1B tz fixture'"
        ).fetchone()[0]
        check("tz fixture not on live", leaked == 0, str(leaked))
    finally:
        conn.close()
        os.environ.pop("WOLF_WORK_EVIDENCE_BLOBS", None)
        shutil.rmtree(tmp, ignore_errors=True)


def test_single_today() -> None:
    home = build_home("PERS-DEVI")
    dash = (home.get("dashboard") or {}).get("sections") or []
    today = next((s for s in dash if s.get("key") == "today"), None)
    check("devi has today block", today is not None)
    check("today title once", (today or {}).get("title") == "TODAY")
    check("today prompt empty", not (today or {}).get("prompt"), str((today or {}).get("prompt")))
    titles = [s.get("title") for s in dash if s.get("title") == "TODAY"]
    prompts = [s.get("prompt") for s in dash if s.get("prompt") == "TODAY"]
    check("one TODAY title", len(titles) == 1, str(titles))
    check("no TODAY prompt", len(prompts) == 0, str(prompts))


def test_live_store_clean() -> None:
    conn = sqlite3.connect(str(CATALOG))
    probes = conn.execute("SELECT COUNT(*) FROM core_work_items WHERE title='STALE probe'").fetchone()[0]
    chain = conn.execute("SELECT COUNT(*) FROM core_work_items WHERE title='Chain view shot'").fetchone()[0]
    legacy = conn.execute("SELECT COUNT(*) FROM core_work_items WHERE origin='legacy'").fetchone()[0]
    comm = conn.execute("SELECT COUNT(*) FROM core_work_items WHERE origin='commissioning'").fetchone()[0]
    conn.close()
    check("no STALE probe on live", probes == 0, str(probes))
    check("no Chain view shot on live", chain == 0, str(chain))
    check("legacy untouched 148", legacy == 148, str(legacy))
    check("commissioning untouched 28", comm == 28, str(comm))
    blobs = ROOT / "state" / "work-evidence" / "blobs"
    leftover = list(blobs.glob("WI-*")) if blobs.is_dir() else []
    check("no orphan live evidence blobs", leftover == [], str(leftover))


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


def _rgb_to_hex(s: str) -> str | None:
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", s or "")
    if not m:
        return None
    return "#{:02x}{:02x}{:02x}".format(int(m[1]), int(m[2]), int(m[3]))


def _rects_overlap(a: dict, b: dict, pad: float = 0.5) -> bool:
    return not (
        a["x"] + a["width"] <= b["x"] + pad
        or b["x"] + b["width"] <= a["x"] + pad
        or a["y"] + a["height"] <= b["y"] + pad
        or b["y"] + b["height"] <= a["y"] + pad
    )


def _with_cdp(width: int, email: str, url: str, wait_expr: str, wait_seconds: float = 55.0):
    """Yield (cdp, evaluate) against a headless Chrome page. Caller must not keep the browser."""
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

            def evaluate(expression: str):
                got = cdp("Runtime.evaluate", {"expression": expression, "returnByValue": True})
                return ((got.get("result") or {}).get("result") or {}).get("value")

            cdp("Network.enable")
            cdp("Network.setExtraHTTPHeaders", {"headers": {"X-Wolf-Subject": email}})
            cdp("Page.enable")
            cdp(
                "Emulation.setDeviceMetricsOverride",
                {"width": width, "height": 900, "deviceScaleFactor": 1, "mobile": width < 500},
            )
            cdp("Page.navigate", {"url": url})
            value = None
            deadline = time.time() + wait_seconds
            while time.time() < deadline:
                value = evaluate(wait_expr)
                if value and value.get("ok"):
                    break
                time.sleep(0.35)
            yield cdp, evaluate, value
        finally:
            proc.kill()
            proc.wait(timeout=5)


def test_header_and_shots() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="tmp-mywork1b-http-", dir=str(ROOT / "state")))
    db = tmp / "content_library.sqlite"
    blobs = tmp / "blobs"
    blobs.mkdir()
    shutil.copy2(CATALOG, db)
    prev = {
        "sb": getattr(sb, "CATALOG_DB", None),
        "wi": wi.CATALOG_DB,
        "umw": getattr(umw, "CATALOG_DB", None),
        "blobs": os.environ.get("WOLF_WORK_EVIDENCE_BLOBS"),
        "wolf_cat": os.environ.get("WOLF_CATALOG_DB"),
    }
    sb.CATALOG_DB = db  # type: ignore[attr-defined]
    wi.CATALOG_DB = db
    umw.CATALOG_DB = db  # type: ignore[attr-defined]
    os.environ["WOLF_CATALOG_DB"] = str(db)
    os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = str(blobs)

    server = ThreadingHTTPServer(("127.0.0.1", 0), sb.BetaHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, _ = call(port, "GET", "/api/health")
        check("temp beta health", status == 200, str(status))
        status, _ = call(port, "GET", "/wolf")
        check("unsigned wolf 403", status == 403, str(status))

        c2 = wi.db_connect(db)
        it = wi.create_work_item(
            title="Chain view shot",
            owning_entity_id="ENT-GGV",
            source_type="SYSTEM",
            created_by_actor_type="SYSTEM",
            owner_person_id="PERS-MATT",
            conn=c2,
            commit=False,
        )
        c2.execute(
            "UPDATE core_work_items SET origin='test', accountable_person_id='PERS-MATT', executor_person_id='PERS-MATT' WHERE work_item_id=?",
            (it["work_item_id"],),
        )
        umw.delegate_work(
            it["work_item_id"],
            from_person_id="PERS-MATT",
            to_person_id="PERS-HAIKAL",
            conn=c2,
            commit=False,
        )
        c2.execute(
            "UPDATE core_work_delegations SET offered_at=?, accepted_at=? WHERE work_item_id=?",
            ("2026-09-29T00:36:43Z", "2026-09-29T00:36:43Z", it["work_item_id"]),
        )
        c2.commit()
        c2.close()
        chain_id = it["work_item_id"]

        if not CHROME.is_file():
            check("chrome for shots", False, "missing")
            return

        SHOTS.mkdir(parents=True, exist_ok=True)

        header_expr = (
            "(() => {"
            " const hello=document.querySelector('#wolfnav-hello');"
            " const ctx=document.querySelector('#wolfnav-ctx:not([hidden])');"
            " const ht=(hello && hello.textContent || '').trim();"
            " if (!ht.includes('ROLE-MATT')) return {ok:false};"
            " const hr=hello.getBoundingClientRect();"
            " const cr=ctx ? ctx.getBoundingClientRect() : null;"
            " return {ok:true, hello:{x:hr.x,y:hr.y,width:hr.width,height:hr.height,text:ht},"
            " ctx: cr && cr.width ? {x:cr.x,y:cr.y,width:cr.width,height:cr.height} : null};"
            "})()"
        )
        for width in (390, 768, 1024, 1440):
            for cdp, _evaluate, value in _with_cdp(
                width, OWNER, f"http://127.0.0.1:{port}/wolf", header_expr
            ):
                check(f"owner chrome ready @{width}", bool(value and value.get("ok")), str(value)[:160])
                ctx, hello = (value or {}).get("ctx"), (value or {}).get("hello")
                if ctx and hello:
                    check(
                        f"no header overlap @{width}",
                        not _rects_overlap(ctx, hello),
                        f"ctx={ctx} hello={hello}",
                    )
                else:
                    check(f"ctx+hello present @{width}", bool(ctx) and bool(hello), str(value))
                if width in (390, 1024):
                    shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                    dest = SHOTS / f"mywork1b-owner-header-{width}.png"
                    dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                    check(f"shot {dest.name}", dest.is_file() and dest.stat().st_size > 4000)

        page_shots = [
            (
                "/execution-report",
                OWNER,
                1024,
                "mywork1b-execution-report.png",
                (
                    "(() => {"
                    " const ready=document.body && document.body.getAttribute('data-ready');"
                    " const t=document.body ? document.body.innerText : '';"
                    " if (ready!=='1' || !t.includes('Assigned')) return {ok:false};"
                    " const card=document.querySelector('article.card');"
                    " if (!card) return {ok:false};"
                    " const p=card.querySelector('.sentence, p') || card;"
                    " const cs=getComputedStyle(card); const ps=getComputedStyle(p);"
                    " return {ok:true, text:t.slice(0,240), bg:cs.backgroundColor, fg:ps.color};"
                    "})()"
                ),
            ),
            (
                f"/my-work/item/{chain_id}",
                OWNER,
                1024,
                "mywork1b-delegation-chain.png",
                (
                    "(() => {"
                    " const ready=document.body && document.body.getAttribute('data-ready');"
                    " const t=document.body ? document.body.innerText : '';"
                    " if (ready!=='1' || !t.includes('Delegation')) return {ok:false};"
                    " const hop=document.querySelector('.chain-hop') || document.querySelector('#chain p');"
                    " const card=document.querySelector('#chain, .card');"
                    " if (!card || !hop) return {ok:false, text:t.slice(0,240)};"
                    " const cs=getComputedStyle(card); const ps=getComputedStyle(hop);"
                    " return {ok:true, text:t.slice(0,400), bg:cs.backgroundColor, fg:ps.color,"
                    " hasWita:t.includes('WITA'), hasZ:/\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z/.test(t)};"
                    "})()"
                ),
            ),
            (
                "/my-work",
                DEVI,
                390,
                "mywork1b-devi-mywork-phone.png",
                (
                    "(() => {"
                    " const ready=document.body && document.body.getAttribute('data-ready');"
                    " const t=document.body ? document.body.innerText : '';"
                    " if (ready!=='1' || !t.includes('TODAY')) return {ok:false};"
                    " const n=Array.from(document.querySelectorAll('#sections h2')"
                    " ).filter(h => h.textContent.trim()==='TODAY').length;"
                    " return {ok:true, text:t.slice(0,240), todayH2:n};"
                    "})()"
                ),
            ),
            (
                "/finish-war-room",
                OWNER,
                1024,
                "mywork1b-war-room-tasks.png",
                (
                    "(() => {"
                    " const ready=document.body && document.body.getAttribute('data-testability-ready');"
                    " const t=document.body ? document.body.innerText : '';"
                    " return {ok: ready==='1' && t.includes('GIVE THIS TO A HUMAN NOW'), text:t.slice(0,200)};"
                    "})()"
                ),
            ),
        ]
        for path, email, width, name, expr in page_shots:
            for cdp, _evaluate, value in _with_cdp(
                width, email, f"http://127.0.0.1:{port}{path}", expr
            ):
                check(f"page ready {name}", bool(value and value.get("ok")), str(value)[:180])
                if name.endswith("delegation-chain.png") and value:
                    check("chain shows WITA", value.get("hasWita") is True, str(value.get("text"))[:200])
                    check("chain hides raw Z", value.get("hasZ") is not True, str(value.get("text"))[:200])
                if name.endswith("devi-mywork-phone.png") and value:
                    check("one TODAY h2 on Devi phone", value.get("todayH2") == 1, str(value.get("todayH2")))
                if value and value.get("fg") and value.get("bg"):
                    fg = _rgb_to_hex(value["fg"])
                    bg = _rgb_to_hex(value["bg"])
                    if fg and bg:
                        ratio = contrast(fg, bg)
                        check(
                            f"computed contrast AA {name}",
                            ratio >= 4.5,
                            f"{fg} on {bg} = {ratio:.2f}",
                        )
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 4000)

        live_leak = sqlite3.connect(str(CATALOG)).execute(
            "SELECT COUNT(*) FROM core_work_items WHERE title='Chain view shot'"
        ).fetchone()[0]
        check("shot fixture stayed off live", live_leak == 0, str(live_leak))
    finally:
        server.shutdown()
        server.server_close()
        if prev["sb"] is not None:
            sb.CATALOG_DB = prev["sb"]  # type: ignore[attr-defined]
        wi.CATALOG_DB = prev["wi"]
        if prev["umw"] is not None:
            umw.CATALOG_DB = prev["umw"]  # type: ignore[attr-defined]
        if prev["blobs"] is None:
            os.environ.pop("WOLF_WORK_EVIDENCE_BLOBS", None)
        else:
            os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = prev["blobs"]
        if prev["wolf_cat"] is None:
            os.environ.pop("WOLF_CATALOG_DB", None)
        else:
            os.environ["WOLF_CATALOG_DB"] = prev["wolf_cat"]
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    test_contrast_tokens()
    test_timezone_wita()
    test_single_today()
    test_live_store_clean()
    test_header_and_shots()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("RESULT: PASS" if FAIL == 0 else f"RESULT: FAIL {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
