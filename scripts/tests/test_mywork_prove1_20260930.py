#!/usr/bin/env python3
"""MYWORK-PROVE-1 — Universal My Work prove / harden (Beta only).

Decision served: Matt 29 Sep 2026 07:20 P0 UNIVERSAL MY WORK (extend;
FINAL_WOLF_COMPLETION_MISSION Phase 2 pack 4).

Hardens: delegation chain, evidence trail under write guard, commissioning
WI holds remain holds, WITA display, MYWORK-1B contrast, honesty banners
(staff_ready/human_commissioned stay false). Never flips commissioning
flags. Never mutates prod :8787. Fixtures stay on temp catalog only.
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
os.environ["WOLF_TEST_MODE"] = "1"
sys.path.insert(0, str(ROOT / "scripts"))

import serve_beta as sb  # noqa: E402
from core import canonical_guard  # noqa: E402
from core import universal_my_work as umw  # noqa: E402
from core import work_items as wi  # noqa: E402
from core.staff_home import build_home  # noqa: E402

OWNER = "mrwolf@wolfcommand.net"
DEVI = "deviputu236@gmail.com"
AMANDA = "amanda@wolfcommand.net"
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


def test_contrast_regressions() -> None:
    item = (ROOT / "dashboards" / "my-work-item.html").read_text(encoding="utf-8")
    report = (ROOT / "dashboards" / "execution-report.html").read_text(encoding="utf-8")
    work = (ROOT / "dashboards" / "my-work.html").read_text(encoding="utf-8")
    check("item pins work-ink", "--work-ink: #1c1915" in item and "--work-card: #fffdf8" in item)
    check("report pins work-ink", "--work-ink: #1c1915" in report)
    check("ink on cream AA", contrast("#1c1915", "#fffdf8") >= 4.5)
    check("muted on cream AA", contrast("#3f3422", "#fffdf8") >= 4.5)
    check("honesty banner my-work", "human_commissioned" in work and 'id="honesty"' in work)
    check("honesty banner item", 'id="honesty"' in item and "human_commissioned" in item)
    check("honesty banner report", 'id="honesty"' in report and "human_commissioned" in report)
    check("item forces card ink", "color: var(--work-ink) !important" in item)


def test_timezone_wita() -> None:
    shown = umw.format_wita("2026-09-29T00:36:43Z")
    check("utc Z becomes WITA", shown.endswith(" WITA") and "2026-09-29 08:36" in shown, shown)
    check("empty stays empty", umw.format_wita("") == "")
    check("garbage passthrough", umw.format_wita("not-a-date") == "not-a-date")
    offset = umw.format_wita("2026-09-29T00:36:43+00:00")
    check("offset form WITA", offset.endswith(" WITA") and "08:36" in offset, offset)


def test_delegation_chain_harden() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="tmp-myworkprove1-chain-", dir=str(ROOT / "state")))
    db = tmp / "c.sqlite"
    blobs = tmp / "blobs"
    blobs.mkdir()
    os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = str(blobs)
    shutil.copy2(CATALOG, db)
    conn = wi.db_connect(db)
    try:
        it = wi.create_work_item(
            title="MYWORK-PROVE-1 chain fixture",
            owning_entity_id="ENT-GGV",
            source_type="SYSTEM",
            created_by_actor_type="SYSTEM",
            owner_person_id="PERS-MATT",
            conn=conn,
            commit=False,
        )
        wid = it["work_item_id"]
        conn.execute(
            "UPDATE core_work_items SET origin='test', accountable_person_id='PERS-MATT', "
            "executor_person_id='PERS-MATT' WHERE work_item_id=?",
            (wid,),
        )
        d1 = umw.delegate_work(
            wid, from_person_id="PERS-MATT", to_person_id="PERS-HAIKAL", note="CD", conn=conn, commit=False
        )
        d2 = umw.delegate_work(
            wid, from_person_id="PERS-HAIKAL", to_person_id="PERS-YUDI", note="creator", conn=conn, commit=False
        )
        check("hop1 ok", d1.get("ok") is True)
        check("hop2 ok", d2.get("ok") is True)
        conn.execute(
            "UPDATE core_work_delegations SET offered_at=?, accepted_at=? WHERE work_item_id=?",
            ("2026-09-29T16:00:00Z", "2026-09-29T16:05:00Z", wid),
        )
        chain = umw.delegation_chain(wid, conn=conn)
        check("chain length 2", len(chain) == 2, str(len(chain)))
        item = wi.get_work_item(wid, conn=conn)
        check("accountable Matt", item.get("accountable_person_id") == "PERS-MATT")
        check("executor Yudi", item.get("executor_person_id") == "PERS-YUDI")
        for hop in chain:
            raw = str(hop.get("accepted_at") or hop.get("offered_at") or "")
            disp = str(hop.get("accepted_at_display") or hop.get("offered_at_display") or "")
            check(f"hop raw Z {hop.get('to_person_id')}", raw.endswith("Z") or "+00:00" in raw, raw)
            check(
                f"hop display WITA {hop.get('to_person_id')}",
                disp.endswith(" WITA") and "T" not in disp.replace(" WITA", ""),
                disp,
            )
        conn.commit()
        leaked = sqlite3.connect(str(CATALOG)).execute(
            "SELECT COUNT(*) FROM core_work_items WHERE title='MYWORK-PROVE-1 chain fixture'"
        ).fetchone()[0]
        check("chain fixture not on live", leaked == 0, str(leaked))
    finally:
        conn.close()
        os.environ.pop("WOLF_WORK_EVIDENCE_BLOBS", None)
        shutil.rmtree(tmp, ignore_errors=True)


def test_evidence_trail_under_write_guard() -> None:
    """Attach + read evidence on temp catalog; live catalog must refuse writes."""
    # Live write must be refused for this test process.
    decision = canonical_guard.decide(CATALOG, write=True, test_process=True)
    check("live catalog write refused", decision == "refuse", decision)

    tmp = Path(tempfile.mkdtemp(prefix="tmp-myworkprove1-ev-", dir=str(ROOT / "state")))
    db = tmp / "c.sqlite"
    blobs = tmp / "blobs"
    blobs.mkdir()
    prev_blobs = os.environ.get("WOLF_WORK_EVIDENCE_BLOBS")
    os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = str(blobs)
    shutil.copy2(CATALOG, db)
    conn = wi.db_connect(db)
    try:
        it = wi.create_work_item(
            title="MYWORK-PROVE-1 evidence fixture",
            owning_entity_id="ENT-GGV",
            source_type="SYSTEM",
            created_by_actor_type="SYSTEM",
            owner_person_id="PERS-AMANDA",
            conn=conn,
            commit=False,
        )
        wid = it["work_item_id"]
        conn.execute(
            "UPDATE core_work_items SET origin='test', executor_person_id='PERS-AMANDA' WHERE work_item_id=?",
            (wid,),
        )
        payload = b"prove1-evidence-bytes"
        stored = umw.store_evidence_file(
            wid,
            filename="prove1-note.txt",
            content=payload,
            uploaded_by_person_id="PERS-AMANDA",
            note="prove attach",
            conn=conn,
            commit=False,
        )
        check("evidence store ok", stored.get("ok") is True and stored.get("file_id"), str(stored))
        path = Path(stored.get("storage_path") or "")
        check("blob under temp root", str(blobs) in str(path) and path.is_file(), str(path))
        check("blob bytes match", path.read_bytes() == payload)
        files = umw.list_evidence_files(wid, conn=conn)
        check("list evidence count 1", len(files) == 1, str(len(files)))
        row = files[0]
        check("list filename", row.get("filename") == "prove1-note.txt")
        check("list sha256", row.get("sha256") == stored.get("sha256"))
        check("list path under blobs", str(blobs) in str(row.get("storage_path") or ""))
        check(
            "list created display WITA or empty",
            (not row.get("created_at"))
            or str(row.get("created_at_display") or "").endswith(" WITA")
            or str(row.get("created_at_display") or "") == str(row.get("created_at") or ""),
            str(row.get("created_at_display")),
        )
        # Live catalog never received the fixture or the blob.
        live = sqlite3.connect(str(CATALOG))
        leaked = live.execute(
            "SELECT COUNT(*) FROM core_work_items WHERE title='MYWORK-PROVE-1 evidence fixture'"
        ).fetchone()[0]
        live_files = live.execute(
            "SELECT COUNT(*) FROM core_work_evidence_files WHERE filename='prove1-note.txt'"
        ).fetchone()[0]
        live.close()
        check("evidence fixture not on live", leaked == 0, str(leaked))
        check("evidence filename not on live", live_files == 0, str(live_files))
        live_blobs = ROOT / "state" / "work-evidence" / "blobs"
        check(
            "no live blob for fixture wi",
            not (live_blobs / wid).exists(),
            str(live_blobs / wid),
        )
        conn.commit()
    finally:
        conn.close()
        if prev_blobs is None:
            os.environ.pop("WOLF_WORK_EVIDENCE_BLOBS", None)
        else:
            os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = prev_blobs
        shutil.rmtree(tmp, ignore_errors=True)


def test_commissioning_holds_remain() -> None:
    """Read-only: open commissioning / retest WIs must stay open holds."""
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        open_comm = conn.execute(
            """
            SELECT COUNT(*) FROM core_work_items
            WHERE origin='commissioning' AND status='OPEN'
            """
        ).fetchone()[0]
        open_retest = conn.execute(
            """
            SELECT COUNT(*) FROM core_work_items
            WHERE origin='commissioning-retest' AND status='OPEN'
            """
        ).fetchone()[0]
        total_comm = conn.execute(
            "SELECT COUNT(*) FROM core_work_items WHERE origin='commissioning'"
        ).fetchone()[0]
        legacy = conn.execute(
            "SELECT COUNT(*) FROM core_work_items WHERE origin='legacy'"
        ).fetchone()[0]
        probes = conn.execute(
            "SELECT COUNT(*) FROM core_work_items WHERE title='STALE probe'"
        ).fetchone()[0]
        chain_shot = conn.execute(
            "SELECT COUNT(*) FROM core_work_items WHERE title='Chain view shot'"
        ).fetchone()[0]
        prove_leak = conn.execute(
            "SELECT COUNT(*) FROM core_work_items WHERE title LIKE 'MYWORK-PROVE-1%'"
        ).fetchone()[0]
        check("open commissioning holds >= 20", open_comm >= 20, str(open_comm))
        check("open retest holds >= 8", open_retest >= 8, str(open_retest))
        check("commissioning total 39", total_comm == 39, str(total_comm))
        check("legacy untouched 148", legacy == 148, str(legacy))
        check("no STALE probe", probes == 0, str(probes))
        check("no Chain view shot", chain_shot == 0, str(chain_shot))
        check("no prove fixture leak", prove_leak == 0, str(prove_leak))
        # Devi commissioning stays OPEN (not auto-completed)
        devi_open = conn.execute(
            """
            SELECT COUNT(*) FROM core_work_items
            WHERE origin='commissioning' AND owner_person_id='PERS-DEVI' AND status='OPEN'
            """
        ).fetchone()[0]
        check("Devi commissioning holds open", devi_open >= 4, str(devi_open))
    finally:
        conn.close()


def test_honesty_flags_never_true() -> None:
    for pid, label in (("PERS-MATT", "Owner"), ("PERS-DEVI", "Devi"), ("PERS-AMANDA", "Amanda")):
        home = build_home(pid)
        check(f"{label} staff_ready false", home.get("staff_ready") is False)
        check(f"{label} human_commissioned false", home.get("human_commissioned") is False)
    report = umw.execution_report(period="week", viewer_person_id="PERS-MATT")
    check("report ok", report.get("ok") is True)
    check("report staff_ready false", report.get("staff_ready") is False)
    check("report human_commissioned false", report.get("human_commissioned") is False)
    queue = umw.war_room_commissioning_queue()
    check("war room staff_ready false", queue.get("staff_ready") is False)
    check("war room human_commissioned false", queue.get("human_commissioned") is False)


def test_single_today_devi() -> None:
    home = build_home("PERS-DEVI")
    dash = (home.get("dashboard") or {}).get("sections") or []
    titles = [s.get("title") for s in dash if s.get("title") == "TODAY"]
    prompts = [s.get("prompt") for s in dash if s.get("prompt") == "TODAY"]
    check("one TODAY title", len(titles) == 1, str(titles))
    check("no TODAY prompt", len(prompts) == 0, str(prompts))


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


def _with_cdp(width: int, email: str, url: str, wait_expr: str, wait_seconds: float = 55.0):
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


def test_http_evidence_and_shots() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="tmp-myworkprove1-http-", dir=str(ROOT / "state")))
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
        status, body = call(port, "GET", "/api/staff/home", DEVI)
        check("devi home 200", status == 200, str(status))
        home = json.loads(body.decode())
        check("api human_commissioned false", home.get("human_commissioned") is False)
        check("api staff_ready false", home.get("staff_ready") is False)

        status, _ = call(port, "GET", "/api/staff/home")
        check("unsigned home 403", status == 403, str(status))

        # Seed chain + evidence on temp DB
        c2 = wi.db_connect(db)
        it = wi.create_work_item(
            title="MYWORK-PROVE-1 shot chain",
            owning_entity_id="ENT-GGV",
            source_type="SYSTEM",
            created_by_actor_type="SYSTEM",
            owner_person_id="PERS-MATT",
            conn=c2,
            commit=False,
        )
        chain_id = it["work_item_id"]
        c2.execute(
            "UPDATE core_work_items SET origin='test', accountable_person_id='PERS-MATT', "
            "executor_person_id='PERS-MATT' WHERE work_item_id=?",
            (chain_id,),
        )
        umw.delegate_work(
            chain_id, from_person_id="PERS-MATT", to_person_id="PERS-HAIKAL", conn=c2, commit=False
        )
        c2.execute(
            "UPDATE core_work_delegations SET offered_at=?, accepted_at=? WHERE work_item_id=?",
            ("2026-09-29T00:36:43Z", "2026-09-29T00:36:43Z", chain_id),
        )
        amanda_row = c2.execute(
            """
            SELECT work_item_id FROM core_work_items
            WHERE origin='commissioning' AND owner_person_id='PERS-AMANDA' AND status='OPEN'
            LIMIT 1
            """
        ).fetchone()
        amanda_wid = amanda_row[0]
        stored = umw.store_evidence_file(
            amanda_wid,
            filename="prove1-amanda.txt",
            content=b"amanda prove",
            uploaded_by_person_id="PERS-AMANDA",
            conn=c2,
            commit=False,
        )
        c2.commit()
        c2.close()
        check("amanda evidence stored", stored.get("ok") is True)

        status, body = call(port, "GET", f"/api/my-work/items/{amanda_wid}/evidence-files", AMANDA)
        ev = json.loads(body.decode())
        check("evidence-files api 200", status == 200, str(status))
        check("evidence-files count >=1", (ev.get("count") or 0) >= 1, str(ev))
        check("evidence-files honesty", ev.get("human_commissioned") is False and ev.get("staff_ready") is False)

        status, body = call(port, "GET", f"/api/my-work/items/{chain_id}/chain", OWNER)
        chain_api = json.loads(body.decode())
        check("chain api 200", status == 200 and chain_api.get("ok") is True, str(status))
        hops = chain_api.get("chain") or []
        check("chain api hop", len(hops) >= 1, str(len(hops)))
        if hops:
            disp = hops[0].get("accepted_at_display") or hops[0].get("offered_at_display") or ""
            check("chain api WITA", disp.endswith(" WITA"), disp)

        status, body = call(port, "GET", f"/api/work-loop/items/{amanda_wid}", AMANDA)
        detail = json.loads(body.decode())
        check("work-loop detail 200", status == 200, str(status))
        check("detail human_commissioned false", detail.get("human_commissioned") is False)
        check("detail evidence_files list", isinstance(detail.get("evidence_files"), list))
        check("detail evidence_files non-empty", len(detail.get("evidence_files") or []) >= 1)

        if not CHROME.is_file():
            check("chrome for shots", False, "missing")
            return

        SHOTS.mkdir(parents=True, exist_ok=True)
        honesty_expr = (
            "(() => {"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const t=document.body ? document.body.innerText : '';"
            " const h=document.getElementById('honesty');"
            " const ht=h ? h.textContent : '';"
            " return {ok: ready==='1' && t.length>20 && ht.includes('human_commissioned=false'),"
            " text:t.slice(0,240), honesty:ht,"
            " hasFalse: ht.includes('human_commissioned=false'),"
            " hasTrue: /human_commissioned\\s*=\\s*true/i.test(ht)};"
            "})()"
        )
        page_shots = [
            ("/my-work", OWNER, 1024, "myworkprove1-owner-mywork-desktop.png", honesty_expr),
            ("/my-work", OWNER, 390, "myworkprove1-owner-mywork-phone.png", honesty_expr),
            ("/my-work", DEVI, 1024, "myworkprove1-devi-mywork-desktop.png", honesty_expr),
            ("/my-work", DEVI, 390, "myworkprove1-devi-mywork-phone.png", honesty_expr),
            ("/my-work", AMANDA, 1024, "myworkprove1-amanda-mywork-desktop.png", honesty_expr),
            ("/my-work", AMANDA, 390, "myworkprove1-amanda-mywork-phone.png", honesty_expr),
            (
                f"/my-work/item/{chain_id}",
                OWNER,
                1024,
                "myworkprove1-delegation-chain.png",
                (
                    "(() => {"
                    " const ready=document.body && document.body.getAttribute('data-ready');"
                    " const t=document.body ? document.body.innerText : '';"
                    " const h=document.getElementById('honesty');"
                    " const ht=h ? h.textContent : '';"
                    " return {ok: ready==='1' && t.includes('Delegation') && ht.includes('human_commissioned=false'),"
                    " text:t.slice(0,400), honesty:ht,"
                    " hasWita:t.includes('WITA'),"
                    " hasZ:/\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z/.test(t)};"
                    "})()"
                ),
            ),
            (
                f"/my-work/item/{amanda_wid}",
                AMANDA,
                1024,
                "myworkprove1-amanda-evidence.png",
                (
                    "(() => {"
                    " const ready=document.body && document.body.getAttribute('data-ready');"
                    " const t=document.body ? document.body.innerText : '';"
                    " const h=document.getElementById('honesty');"
                    " const ht=h ? h.textContent : '';"
                    " return {ok: ready==='1' && ht.includes('human_commissioned=false'),"
                    " text:t.slice(0,400), honesty:ht,"
                    " hasEvidence: t.includes('prove1-amanda') || t.includes('file') || t.includes('Evidence')};"
                    "})()"
                ),
            ),
            (
                "/execution-report",
                OWNER,
                1024,
                "myworkprove1-execution-report.png",
                (
                    "(() => {"
                    " const ready=document.body && document.body.getAttribute('data-ready');"
                    " const t=document.body ? document.body.innerText : '';"
                    " const h=document.getElementById('honesty');"
                    " const ht=h ? h.textContent : '';"
                    " const card=document.querySelector('article.card');"
                    " if (ready!=='1' || !t.includes('Assigned') || !ht.includes('human_commissioned=false'))"
                    "   return {ok:false, honesty:ht, text:t.slice(0,200)};"
                    " const p=card ? (card.querySelector('.sentence, p') || card) : null;"
                    " const cs=card ? getComputedStyle(card) : null;"
                    " const ps=p ? getComputedStyle(p) : null;"
                    " return {ok:true, text:t.slice(0,240), honesty:ht,"
                    " bg: cs && cs.backgroundColor, fg: ps && ps.color};"
                    "})()"
                ),
            ),
        ]
        for path, email, width, name, expr in page_shots:
            for cdp, _evaluate, value in _with_cdp(
                width, email, f"http://127.0.0.1:{port}{path}", expr
            ):
                check(f"page ready {name}", bool(value and value.get("ok")), str(value)[:200])
                if value:
                    check(
                        f"honesty false {name}",
                        "human_commissioned=false" in str(value.get("honesty") or ""),
                        str(value.get("honesty"))[:160],
                    )
                    check(
                        f"honesty not true {name}",
                        value.get("hasTrue") is not True,
                        str(value.get("honesty"))[:160],
                    )
                if name.endswith("delegation-chain.png") and value:
                    check("chain shows WITA", value.get("hasWita") is True, str(value.get("text"))[:200])
                    check("chain hides raw Z", value.get("hasZ") is not True, str(value.get("text"))[:200])
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
            "SELECT COUNT(*) FROM core_work_items WHERE title LIKE 'MYWORK-PROVE-1%'"
        ).fetchone()[0]
        check("shot fixtures stayed off live", live_leak == 0, str(live_leak))
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


def test_prod_pid_untouched() -> None:
    out = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN"], text=True, stderr=subprocess.DEVNULL
    )
    check("prod pid 15975 still listening", "15975" in out and ":8787" in out, out[:200])


def main() -> int:
    canonical_guard.install()
    test_contrast_regressions()
    test_timezone_wita()
    test_delegation_chain_harden()
    test_evidence_trail_under_write_guard()
    test_commissioning_holds_remain()
    test_honesty_flags_never_true()
    test_single_today_devi()
    test_http_evidence_and_shots()
    test_prod_pid_untouched()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("RESULT: PASS" if FAIL == 0 else f"RESULT: FAIL {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
