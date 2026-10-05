#!/usr/bin/env python3
"""MYWORK-1 — Universal My Work + delegation + evidence + commissioning (Beta).

Decision served: Matt 29 Sep 2026 07:20 P0 UNIVERSAL MY WORK.
Uses a short-lived Beta handler. Does not touch production :8787.
"""
from __future__ import annotations

import base64
import json
import os
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
from core import rbac  # noqa: E402
from core import staff_access  # noqa: E402
from core import universal_my_work as umw  # noqa: E402
from core import venue_close  # noqa: E402
from core import work_items as wi  # noqa: E402
from core.staff_home import build_home  # noqa: E402

OWNER = "mrwolf@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
DEVI = "deviputu236@gmail.com"
AMANDA = "amanda@wolfcommand.net"
ZAYEN = "laluzayen@gmail.com"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
CUT = ROOT / "state" / "legacy" / "clickup-cut-line.json"
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


def test_part_a_assignments() -> None:
    conn = sqlite3.connect(str(CATALOG))
    conn.row_factory = sqlite3.Row
    old = conn.execute(
        "SELECT status, end_at, end_reason FROM org_assignments WHERE assignment_id='ASG-ZAYEN-FIN-1'"
    ).fetchone()
    check("zayen officer assignment ended preserved", old is not None and (old["status"] == "ENDED" or old["end_at"]))
    check("zayen end_reason kept", bool(old and old["end_reason"]))
    neu = conn.execute(
        """
        SELECT a.status, a.end_at, p.role_id, r.display_name
        FROM org_assignments a
        JOIN org_positions p ON p.position_id=a.position_id
        JOIN org_roles r ON r.role_id=p.role_id
        WHERE a.assignment_id='ASG-ZAYEN-FC-1'
        """
    ).fetchone()
    check("zayen FC assignment active", neu and neu["status"] == "ACTIVE" and not neu["end_at"])
    check("zayen role is Financial Controller", neu and "Controller" in (neu["display_name"] or ""))
    for code in staff_access.ATRIUM_DENIED:
        ev = rbac.evaluate("PERS-ZAYEN", code, {"entity_id": "ENT-AMG"}, conn=conn)
        check(f"zayen denied {code}", not ev.get("allowed"), str(ev.get("allowed")))
    for code in ("atrium.board.read", "atrium.journal.draft", "atrium.ledger.read", "atrium.journal.approve"):
        ev = rbac.evaluate("PERS-ZAYEN", code, {"entity_id": "ENT-AMG"}, conn=conn)
        check(f"zayen allowed {code}", bool(ev.get("allowed")))
    closer = conn.execute(
        """
        SELECT a.assignment_id FROM org_assignments a
        JOIN org_positions p ON p.position_id=a.position_id
        WHERE a.person_id='PERS-DEVI' AND p.role_id='ROLE-BZG-CLOSER'
          AND a.status='ACTIVE' AND a.end_at IS NULL
        """
    ).fetchone()
    check("devi closer assigned", closer is not None)
    fb = conn.execute(
        """
        SELECT 1 FROM org_assignments a JOIN org_positions p ON p.position_id=a.position_id
        WHERE a.person_id='PERS-DEVI' AND p.role_id='ROLE-BZG-FB-OPS-LEAD'
          AND a.status='ACTIVE' AND a.end_at IS NULL
        """
    ).fetchone()
    check("devi fb ops preserved", fb is not None)
    flags = venue_close.honesty_flags(conn)
    check("cash variance UNSET", flags.get("cash_variance_tolerance") == "UNSET", str(flags.get("cash_variance_tolerance")))
    check("variance display open policy", "needs approval" in str(flags.get("variance_policy_display") or "").lower() or "UNSET" in str(flags.get("variance_policy_display") or ""))
    matt_scopes = {
        r[0]
        for r in conn.execute(
            """
            SELECT scope_id FROM org_assignment_scopes
            WHERE assignment_id='ASG-MATT-OWNER-1' AND status='ACTIVE' AND end_at IS NULL
            """
        )
    }
    check("matt overwatch AMG finance", "SCOPE-AMG-FINANCE" in matt_scopes, str(sorted(matt_scopes)))
    check("matt overwatch AMG day", "SCOPE-AMG-ATR-DAY" in matt_scopes)
    conn.close()


def test_part_b_universal_sections() -> None:
    for pid, email_label in (
        ("PERS-DEVI", "Devi"),
        ("PERS-ZAYEN", "Zayen"),
        ("PERS-AMANDA", "Amanda"),
        ("PERS-HAIKAL", "Haikal"),
        ("PERS-MATT", "Matt"),
    ):
        home = build_home(pid)
        keys = [s.get("key") for s in home.get("sections") or []]
        check(
            f"{email_label} universal keys",
            {"today", "do_this_next", "attention", "waiting", "completed"} <= set(keys),
            str(keys),
        )
        titles = [s.get("title") for s in home.get("sections") or [] if s.get("key") in {
            "today", "do_this_next", "attention", "waiting", "completed"
        }]
        check(
            f"{email_label} plain section titles",
            set(titles) >= {"TODAY", "DO THIS NEXT", "NEEDS ATTENTION", "WAITING", "COMPLETED"},
            str(titles),
        )
        check(f"{email_label} not staff_ready", home.get("staff_ready") is False)
        check(f"{email_label} not human_commissioned", home.get("human_commissioned") is False)


def test_part_c_delegation_and_done_ne_verified() -> Path:
    """Runs against a temp DB copy so live audit/work stay clean for edge cases."""
    tmp = ROOT / "state" / "tmp-mywork1-c"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    db = tmp / "catalog.sqlite"
    blobs = tmp / "blobs"
    blobs.mkdir(parents=True, exist_ok=True)
    os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = str(blobs)
    shutil.copy2(CATALOG, db)
    conn = wi.db_connect(db)
    # Create a chain Matt → (simulate GM as Haikal) → Yudi
    item = wi.create_work_item(
        title="MYWORK-1 delegation chain fixture",
        owning_entity_id="ENT-GGV",
        source_type="SYSTEM",
        created_by_actor_type="SYSTEM",
        owner_person_id="PERS-MATT",
        priority=2,
        conn=conn,
        commit=False,
    )
    wid = item["work_item_id"]
    conn.execute(
        "UPDATE core_work_items SET accountable_person_id='PERS-MATT', executor_person_id='PERS-MATT', origin='test' WHERE work_item_id=?",
        (wid,),
    )
    d1 = umw.delegate_work(
        wid,
        from_person_id="PERS-MATT",
        to_person_id="PERS-HAIKAL",
        note="to CD",
        conn=conn,
        commit=False,
    )
    check("delegate hop 1", d1.get("ok") is True)
    d2 = umw.delegate_work(
        wid,
        from_person_id="PERS-HAIKAL",
        to_person_id="PERS-YUDI",
        note="to creator",
        conn=conn,
        commit=False,
    )
    check("delegate hop 2", d2.get("ok") is True)
    chain = umw.delegation_chain(wid, conn=conn)
    check("chain length 2", len(chain) == 2, str(len(chain)))
    updated = wi.get_work_item(wid, conn=conn)
    check("accountable remains Matt", updated.get("accountable_person_id") == "PERS-MATT")
    check("executor is Yudi", updated.get("executor_person_id") == "PERS-YUDI")
    # Evidence + DONE ≠ VERIFIED
    ev = umw.store_evidence_file(
        wid,
        filename="proof.txt",
        content=b"delegation evidence",
        uploaded_by_person_id="PERS-YUDI",
        note="done with proof",
        conn=conn,
        commit=False,
    )
    check("evidence stored", ev.get("ok") is True and ev.get("file_id"))
    files = conn.execute(
        "SELECT COUNT(*) FROM core_work_evidence_files WHERE work_item_id=?", (wid,)
    ).fetchone()[0]
    check("evidence linked", files == 1)
    done = umw.mark_done(wid, verified_person_id="PERS-YUDI", outcome="claimed", conn=conn, commit=False)
    check("DONE is COMPLETED", done["work_item"]["status"] == "COMPLETED")
    check("DONE not verified flag", done.get("verified") is False)
    check("system percent unchanged on DONE", done.get("system_percent_unchanged") is True)
    after = wi.get_work_item(wid, conn=conn)
    check("status not VERIFIED after DONE", after["status"] == "COMPLETED")
    # Evidence landed only under the isolated blob root.
    check(
        "evidence under temp blobs",
        any(blobs.rglob("*-proof.txt")),
        str(blobs),
    )
    conn.commit()
    conn.close()
    return tmp


def test_part_d_execution_report() -> None:
    report = umw.execution_report(period="week", viewer_person_id="PERS-MATT")
    check("execution report ok", report.get("ok") is True)
    check("no ai judgement", report.get("ai_judgement") is False)
    people = report.get("people") or []
    check("report has people", len(people) >= 5, str(len(people)))
    sample = next((p for p in people if p.get("person_id") == "PERS-MATT"), people[0])
    check("plain sentence present", "Assigned" in (sample.get("sentence") or "") and "verified" in (sample.get("sentence") or "").lower())


def test_part_e_commissioning_flow() -> None:
    conn = sqlite3.connect(str(CATALOG))
    conn.row_factory = sqlite3.Row
    n = conn.execute(
        "SELECT COUNT(*) FROM core_work_items WHERE origin='commissioning'"
    ).fetchone()[0]
    check("commissioning tasks issued", n >= 20, str(n))
    # Pick a Haikal task, DONE, then PASS verify — on a copy under beta-os (path guard).
    tmp = Path(tempfile.mkdtemp(prefix="tmp-mywork1-comm-", dir=str(ROOT / "state")))
    db = tmp / "c.sqlite"
    blobs = tmp / "blobs"
    blobs.mkdir(parents=True, exist_ok=True)
    prev_blobs = os.environ.get("WOLF_WORK_EVIDENCE_BLOBS")
    os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = str(blobs)
    shutil.copy2(CATALOG, db)
    c = wi.db_connect(db)
    row = c.execute(
        """
        SELECT work_item_id FROM core_work_items
        WHERE origin IN ('commissioning','commissioning-retest')
          AND owner_person_id='PERS-HAIKAL' AND status='OPEN'
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        row = c.execute(
            """
            SELECT work_item_id FROM core_work_items
            WHERE origin='commissioning' AND owner_person_id='PERS-HAIKAL'
            ORDER BY created_at LIMIT 1
            """
        ).fetchone()
        check("haikal commissioning available", row is not None)
        c.execute(
            """
            UPDATE core_work_items
            SET status='OPEN', human_result=NULL, human_comment=NULL,
                commissioning_result=NULL, completed_at=NULL, outcome=NULL
            WHERE work_item_id=?
            """,
            (row["work_item_id"],),
        )
    check("haikal commissioning open", row is not None)
    wid = row["work_item_id"]
    wi.start_work_item(wid, verified_person_id="PERS-HAIKAL", conn=c, commit=False)
    umw.store_evidence_file(
        wid,
        filename="shot.txt",
        content=b"phone shot",
        uploaded_by_person_id="PERS-HAIKAL",
        conn=c,
        commit=False,
    )
    # HUMANCOMM-1: DONE needs evidence + employee PASS/FAIL → AWAITING_VERIFY.
    done = umw.mark_done(
        wid,
        verified_person_id="PERS-HAIKAL",
        human_result="PASS",
        human_comment="",
        conn=c,
        commit=False,
    )
    check(
        "pass path awaits verify",
        (done.get("work_item") or {}).get("status") == "AWAITING_VERIFY",
        str((done.get("work_item") or {}).get("status")),
    )
    before_pct_note = "system_percent_unchanged"
    ver = umw.verify_commissioning(
        wid, verifier_person_id="PERS-MATT", result="PASS", note="ok", conn=c, commit=False
    )
    check("verify pass", ver.get("commissioning_result") == "PASS")
    check("verified status", (ver.get("work_item") or {}).get("status") == "VERIFIED")
    check("still not staff_ready", ver.get("staff_ready") is False)
    check("still not human_commissioned", ver.get("human_commissioned") is False)
    check(before_pct_note, ver.get("system_percent_unchanged") is True)
    # FAIL path — employee FAIL creates ENGINEERING repair (not owned by employee).
    row2 = c.execute(
        """
        SELECT work_item_id FROM core_work_items
        WHERE origin='commissioning' AND owner_person_id='PERS-DEVI' AND status='OPEN'
        LIMIT 1
        """
    ).fetchone()
    wid2 = row2["work_item_id"]
    wi.start_work_item(wid2, verified_person_id="PERS-DEVI", conn=c, commit=False)
    umw.store_evidence_file(
        wid2,
        filename="fail.txt",
        content=b"broken screen",
        uploaded_by_person_id="PERS-DEVI",
        conn=c,
        commit=False,
    )
    fail_done = umw.mark_done(
        wid2,
        verified_person_id="PERS-DEVI",
        human_result="FAIL",
        human_comment="Numbers look wrong",
        conn=c,
        commit=False,
    )
    repair = fail_done.get("repair_item") or {}
    check("fail result on item", (fail_done.get("work_item") or {}).get("commissioning_result") == "FAIL"
          or (fail_done.get("work_item") or {}).get("human_result") == "FAIL")
    check("repair item created", bool(repair.get("work_item_id")))
    check(
        "repair owned by engineering queue",
        repair.get("owner_person_id") in (None, "")
        and repair.get("origin") == "commissioning-repair",
        str(repair.get("owner_person_id")),
    )
    check(
        "repair not owned by employee",
        repair.get("owner_person_id") != "PERS-DEVI"
        and repair.get("executor_person_id") != "PERS-DEVI",
        str((repair.get("owner_person_id"), repair.get("executor_person_id"))),
    )
    c.commit()
    c.close()
    if prev_blobs is None:
        os.environ.pop("WOLF_WORK_EVIDENCE_BLOBS", None)
    else:
        os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = prev_blobs
    shutil.rmtree(tmp, ignore_errors=True)
    queue = umw.war_room_commissioning_queue()
    check("war room title", queue.get("title") == "GIVE THIS TO A HUMAN NOW")
    check("war room from work items", queue.get("source") == "core_work_items")
    check("war room queue non-empty", len(queue.get("queue") or []) >= 4)
    check("no passive test cards", queue.get("human_test_cards") == [])
    conn.close()


def test_part_f_legacy_and_cutline() -> None:
    conn = sqlite3.connect(str(CATALOG))
    n = conn.execute("SELECT COUNT(*) FROM core_work_items WHERE origin='legacy'").fetchone()[0]
    check("legacy imported", n >= 100, str(n))
    unknown = conn.execute(
        "SELECT COUNT(*) FROM core_work_items WHERE title LIKE 'UNKNOWN — REVIEW%'"
    ).fetchone()[0]
    check("unknown review items", unknown >= 1, str(unknown))
    conn.close()
    check("clickup cut-line file", CUT.is_file())
    cut = json.loads(CUT.read_text(encoding="utf-8"))
    check("no clickup writes", cut.get("wolf_clickup_writes") is False)
    check("history readable", cut.get("history_readable") is True)
    check("nothing deleted", cut.get("nothing_deleted_in_clickup") is True)


def test_part_g_derived_stale() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="tmp-mywork1-stale-", dir=str(ROOT / "state")))
    db = tmp / "catalog.sqlite"
    blobs = tmp / "blobs"
    blobs.mkdir(parents=True, exist_ok=True)
    prev_blobs = os.environ.get("WOLF_WORK_EVIDENCE_BLOBS")
    os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = str(blobs)
    shutil.copy2(CATALOG, db)
    conn = wi.db_connect(db)
    try:
        umw.mark_derived_views_stale(conn=conn, commit=False)
        st = umw.derived_view_status("my-work", conn=conn)
        check("stale after mark", st.get("status") == "STALE", str(st))
        live = umw.refresh_derived_view("my-work", conn=conn, commit=False)
        check("refresh live", live.get("status") == "LIVE")
        st2 = umw.derived_view_status("my-work", conn=conn)
        check("derived live after refresh", st2.get("status") == "LIVE")
        wi.create_work_item(
            title="STALE probe",
            owning_entity_id="ENT-GGV",
            source_type="SYSTEM",
            created_by_actor_type="SYSTEM",
            owner_person_id="PERS-MATT",
            conn=conn,
            commit=False,
        )
        umw.mark_derived_views_stale(conn=conn, commit=False)
        check(
            "stale after canonical change",
            umw.derived_view_status("execution-report", conn=conn).get("status") == "STALE",
        )
        conn.commit()
        # Isolation: probe must not exist on the live catalog.
        live_conn = sqlite3.connect(str(CATALOG))
        leaked = live_conn.execute(
            "SELECT COUNT(*) FROM core_work_items WHERE title='STALE probe'"
        ).fetchone()[0]
        live_conn.close()
        check("stale probe not leaked to live", leaked == 0, str(leaked))
    finally:
        conn.close()
        if prev_blobs is None:
            os.environ.pop("WOLF_WORK_EVIDENCE_BLOBS", None)
        else:
            os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = prev_blobs
        shutil.rmtree(tmp, ignore_errors=True)


def test_receivers_list() -> None:
    rows = umw.list_work_receivers()
    names = {r["name"] for r in rows}
    check("receivers include Devi", any("Devi" in n for n in names), str(names))
    check("receivers include Zayen", "Zayen" in names)
    check("no demo fixture", not any("Demo" in n for n in names))


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
            check(
                f"shot {dest.name}",
                dest.is_file() and dest.stat().st_size > 4000 and marker in text,
                text[:180],
            )
        finally:
            proc.kill()
            proc.wait(timeout=5)


def test_http_and_shots() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="tmp-mywork1-http-", dir=str(ROOT / "state")))
    db = tmp / "content_library.sqlite"
    blobs = tmp / "blobs"
    blobs.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CATALOG, db)
    # Point modules at temp catalog + isolated evidence blobs (never live store).
    prev_catalog = getattr(sb, "CATALOG_DB", None)
    prev_wi = wi.CATALOG_DB
    prev_umw = getattr(umw, "CATALOG_DB", None)
    prev_blobs = os.environ.get("WOLF_WORK_EVIDENCE_BLOBS")
    prev_wolf_cat = os.environ.get("WOLF_CATALOG_DB")
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
        check("devi has TODAY", any(s.get("title") == "TODAY" for s in (home.get("dashboard") or {}).get("sections") or home.get("sections") or []))

        status, body = call(port, "GET", "/api/my-work/execution-report?period=week", OWNER)
        check("execution report api", status == 200, str(status))

        status, body = call(port, "GET", "/api/owner/war-room/testability", OWNER)
        room = json.loads(body.decode())
        check("war room work items", status == 200 and len(room.get("queue") or []) >= 4)

        status, _ = call(port, "GET", "/api/staff/home")
        check("unsigned home 403", status == 403, str(status))

        # DONE≠VERIFIED via API on a commissioning item in temp DB
        conn = wi.db_connect(db)
        row = conn.execute(
            "SELECT work_item_id FROM core_work_items WHERE origin='commissioning' AND owner_person_id='PERS-AMANDA' AND status='OPEN' LIMIT 1"
        ).fetchone()
        wid = row[0]
        conn.close()
        call(port, "POST", f"/api/my-work/items/{wid}/start", AMANDA, {})
        call(
            port,
            "POST",
            f"/api/my-work/items/{wid}/evidence-file",
            AMANDA,
            {"note": "invoice check", "filename": "n.txt", "content_base64": base64.b64encode(b"ok").decode()},
        )
        status, body = call(
            port,
            "POST",
            f"/api/my-work/items/{wid}/done",
            AMANDA,
            {"outcome": "done", "human_result": "PASS", "human_comment": ""},
        )
        done = json.loads(body.decode())
        check(
            "api DONE",
            status == 200 and (done.get("work_item") or {}).get("status") == "AWAITING_VERIFY",
            f"{status} {(done.get('work_item') or {}).get('status')} {done.get('message')}",
        )
        check("api DONE not verified", done.get("verified") is False)

        if CHROME.is_file():
            SHOTS.mkdir(parents=True, exist_ok=True)
            _capture(port, "/my-work", DEVI, 390, SHOTS / "mywork1-devi-mywork-phone.png", "TODAY", "data-ready")
            _capture(port, "/my-work", ZAYEN, 1024, SHOTS / "mywork1-zayen-mywork.png", "TODAY", "data-ready")
            _capture(port, "/my-work", AMANDA, 1024, SHOTS / "mywork1-amanda-mywork.png", "TODAY", "data-ready")
            _capture(port, "/my-work", HAIKAL, 1024, SHOTS / "mywork1-haikal-mywork.png", "TODAY", "data-ready")
            _capture(port, f"/my-work/item/{wid}", AMANDA, 1024, SHOTS / "mywork1-task-evidence.png", "DONE", "data-ready")
            _capture(port, "/execution-report", OWNER, 1024, SHOTS / "mywork1-execution-report.png", "Assigned", "data-ready")
            _capture(port, "/finish-war-room", OWNER, 1024, SHOTS / "mywork1-war-room-tasks.png", "GIVE THIS TO A HUMAN NOW", "data-testability-ready")
            _capture(port, "/wolf", OWNER, 1024, SHOTS / "mywork1-owner-command-exceptions.png", "exception", "data-command-ready")
            # Delegation chain view — fixture stays on the isolated temp DB only.
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
                "UPDATE core_work_items SET origin='test' WHERE work_item_id=?",
                (it["work_item_id"],),
            )
            umw.delegate_work(
                it["work_item_id"],
                from_person_id="PERS-MATT",
                to_person_id="PERS-HAIKAL",
                conn=c2,
                commit=True,
            )
            c2.close()
            chain_id = it["work_item_id"]
            live_leak = sqlite3.connect(str(CATALOG)).execute(
                "SELECT COUNT(*) FROM core_work_items WHERE title='Chain view shot'"
            ).fetchone()[0]
            check("chain shot fixture not on live", live_leak == 0, str(live_leak))
            _capture(port, f"/my-work/item/{chain_id}", OWNER, 1024, SHOTS / "mywork1-delegation-chain.png", "Delegation", "data-ready")
        else:
            check("chrome for shots", False, "missing")
    finally:
        server.shutdown()
        server.server_close()
        if prev_catalog is not None:
            sb.CATALOG_DB = prev_catalog  # type: ignore[attr-defined]
        wi.CATALOG_DB = prev_wi
        if prev_umw is not None:
            umw.CATALOG_DB = prev_umw  # type: ignore[attr-defined]
        if prev_blobs is None:
            os.environ.pop("WOLF_WORK_EVIDENCE_BLOBS", None)
        else:
            os.environ["WOLF_WORK_EVIDENCE_BLOBS"] = prev_blobs
        if prev_wolf_cat is None:
            os.environ.pop("WOLF_CATALOG_DB", None)
        else:
            os.environ["WOLF_CATALOG_DB"] = prev_wolf_cat
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    test_part_a_assignments()
    test_part_b_universal_sections()
    tmp = test_part_c_delegation_and_done_ne_verified()
    shutil.rmtree(tmp, ignore_errors=True)
    test_part_d_execution_report()
    test_part_e_commissioning_flow()
    test_part_f_legacy_and_cutline()
    test_part_g_derived_stale()
    test_receivers_list()
    test_http_and_shots()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("RESULT: PASS" if FAIL == 0 else f"RESULT: FAIL {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
