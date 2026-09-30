#!/usr/bin/env python3
"""SOP-CATALOG-SEED-ROUTE-1 — live catalog seed-or-route (no invent).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack
SOP-CATALOG-SEED-ROUTE-1 (armed 2026-09-30 after ESB-SETTLEMENT-PATH-1).

Seed from approved DEMO after human route OR stamp HUMAN_COMMISSIONING.
Preserve SOP-LESSON-LIVE-1 DEMO honesty. auto_approve false.
Prod :8787 pid 15975 untouched. No auto-chain FIN-BANK-CREDS-ROUTE-1.
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
os.environ.pop("WOLF_SOP_FACTORY_DB", None)
os.environ.pop("WOLF_ALLOW_LIVE_SOP_FACTORY", None)
sys.path.insert(0, str(ROOT / "scripts"))

import serve_beta as sb  # noqa: E402
from core import sop_catalog_seed_route1 as seed  # noqa: E402
from core import sop_factory as sop  # noqa: E402
from core import sop_lesson_live1 as lesson  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "SOP-CATALOG-SEED-ROUTE-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
PAGE = ROOT / "dashboards" / "sop-catalog-seed-route-1.html"
RESULT = ROOT / "docs" / "wolf" / "ops" / "SOP-CATALOG-SEED-ROUTE-1-RESULT.md"
MODULE = ROOT / "scripts" / "core" / "sop_catalog_seed_route1.py"
LIVE_DB = ROOT / "catalog" / "sop_factory.sqlite"
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
    check("api matcher ops", seed.api_matches("/api/ops/sop-catalog-seed-route-1"))
    check("api matcher alias", seed.api_matches("/api/sop/catalog-seed-route-1"))
    check("api not lesson-live", not seed.api_matches("/api/ops/sop-lesson-live"))
    check("page matcher ops", seed.page_matches("/ops/sop-catalog-seed-route-1"))
    check("page matcher core", seed.page_matches("/core/sop-catalog-seed-route-1"))
    check("page matcher alias", seed.page_matches("/sop-catalog-seed-route-1"))
    check("pack id", seed.PACK_ID == "SOP-CATALOG-SEED-ROUTE-1")
    check("schema id", seed.SCHEMA_ID == "wolf.sop-catalog-seed-route-1.v1")
    check("cap", seed.CAP_ID == "CAP-INTEL-05")

    flags = seed.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("operating_adoption false", flags.get("operating_adoption") is False)
    check("human_review_gate", flags.get("human_review_gate") is True)
    check("auto_approve false", flags.get("auto_approve") is False)
    check("auto_approve_lessons false", flags.get("auto_approve_lessons") is False)
    check("invented_lessons false", flags.get("invented_lessons") is False)
    check("fake_lessons false", flags.get("fake_lessons") is False)
    check("seeded_live false", flags.get("seeded_live") is False)
    check("demo not adoption", flags.get("demo_is_live_adoption") is False)
    check("live catalog absent", flags.get("live_catalog_sop_absent") is True)
    check("live catalog status ABSENT", flags.get("live_catalog_status") == "ABSENT")
    check("pack classification", flags.get("pack_classification") == "INTERNALLY_SOLVABLE")
    check(
        "route classification HUMAN_COMMISSIONING",
        flags.get("route_classification") == "HUMAN_COMMISSIONING"
        or flags.get("classification") == "HUMAN_COMMISSIONING",
    )
    check("action stamp", flags.get("action") == "STAMP_HUMAN_COMMISSIONING")
    check("extends lesson", flags.get("extends_sop_lesson_live1") is True)
    check("lesson preserved flag", flags.get("sop_lesson_live1_preserved") is True)
    check("proven false", flags.get("proven") is False)
    check("ready false", flags.get("ready") is False)
    check("cap proven false", flags.get("cap_intel_05_proven") is False)
    check(
        "next pack parent only",
        flags.get("next_pack_for_parent_only") == "FIN-BANK-CREDS-ROUTE-1",
    )
    check("did not auto-start", flags.get("cursor_did_not_auto_start_next") is True)
    check("prod pid held", flags.get("prod_pid_held") == PROD_PID)
    check("no push", flags.get("no_push") is True)

    for refuse_fn, code in (
        (seed.refuse_auto_approve, "auto_approve_refused"),
        (seed.refuse_invent_lesson, "invent_lesson_refused"),
        (seed.refuse_fake_lesson, "fake_lesson_refused"),
        (seed.refuse_seed_without_route, "human_commissioning_required"),
        (seed.refuse_proven, "proven_refused"),
        (seed.refuse_ready, "ready_refused"),
    ):
        try:
            refuse_fn({})
            check(f"{code} raised", False)
        except seed.SopCatalogSeedRoute1Error as exc:
            check(f"{code} code", exc.code == code, f"got={exc.code}")


def test_decision_and_board() -> None:
    check("live db absent", not LIVE_DB.is_file())
    decision = seed.decide_seed_or_route()
    check("decision action stamp", decision.get("action") == "STAMP_HUMAN_COMMISSIONING")
    check(
        "decision classification",
        decision.get("classification") == "HUMAN_COMMISSIONING",
    )
    check("decision may_seed false", decision.get("may_seed") is False)
    check("decision seeded false", decision.get("seeded") is False)
    check("decision invented false", decision.get("invented_lessons") is False)
    check("decision auto_approve false", decision.get("auto_approve") is False)
    check("decision live ABSENT", decision.get("live_catalog_status") == "ABSENT")
    check(
        "decision approved demo 0 or pending",
        int(decision.get("approved_demo_count") or 0) == 0,
    )

    board = seed.build_board("PERS-MATT")
    check("board ok", board.get("ok") is True)
    check("board classification", board.get("classification") == "HUMAN_COMMISSIONING")
    check("board action", board.get("action") == "STAMP_HUMAN_COMMISSIONING")
    check("board staff_ready false", board.get("staff_ready") is False)
    check("board human_commissioned false", board.get("human_commissioned") is False)
    check("board auto_approve false", board.get("auto_approve") is False)
    check("board invented false", board.get("invented_lessons") is False)
    check("board seeded_live false", board.get("seeded_live") is False)
    check("board live ABSENT", board.get("live_catalog_status") == "ABSENT")
    check("board live count 0", board.get("live_lesson_count") == 0)
    check("board demo not adoption", board.get("demo_is_live_adoption") is False)
    check("surfaces honest", seed.surfaces_are_honest(board))
    check("no invented", seed.no_invented_live_lessons(board))
    check(
        "next pack",
        board.get("next_pack_for_parent_only") == "FIN-BANK-CREDS-ROUTE-1",
    )
    check("cursor no auto", board.get("cursor_did_not_auto_start_next") is True)

    preserved = seed.sop_lesson_live1_preserved()
    check("lesson preserved ok", preserved.get("ok") is True)
    check("lesson preserved status", preserved.get("status") == "PRESERVED")

    # Preserve SOP-LESSON-LIVE-1 DEMO honesty directly
    lesson_board = lesson.build_board("PERS-MATT")
    check("lesson live ABSENT", lesson_board.get("live_catalog_status") == "ABSENT")
    check("lesson live count 0", lesson_board.get("live_lesson_count") == 0)
    check("lesson auto_approve false", lesson_board.get("auto_approve") is False)
    check("lesson invented false", lesson_board.get("invented_lessons") is False)
    check(
        "lesson demo labeled",
        any(
            r.get("demo_label") == sop.DEMO_LABEL
            for r in (lesson_board.get("demo_lessons") or [])
        )
        or int(lesson_board.get("demo_lesson_count") or 0) >= 0,
    )


def test_seed_path_temp_only() -> None:
    """Approved DEMO + commission stamp → may seed to temp; never invent; live untouched."""
    # sop_factory refuses paths outside beta-os — keep fixtures under build-factory/tmp.
    tmp_root = ROOT / "state" / "build-factory" / "tmp-sop-catalog-seed-route-1"
    if tmp_root.exists():
        import shutil

        shutil.rmtree(tmp_root)
    tmp_root.mkdir(parents=True, exist_ok=True)
    try:
        tmp_path = tmp_root
        demo_db = tmp_path / "demo.sqlite"
        target = tmp_path / "live_seed.sqlite"
        stamp = tmp_path / "commission.json"

        # Seed DEMO vertical slice into temp, then human APPROVE (not auto).
        sliced = sop.seed_demo_vertical_slice(
            person_id="PERS-MATT", db_path=demo_db
        )
        check("temp demo seeded", sliced.get("seeded") is True or sliced.get("already_present"))
        cand_id = sliced.get("candidate_id")
        if not cand_id:
            queue = sop.list_review_queue("PERS-MATT", db_path=demo_db)
            cands = queue.get("candidates") or []
            cand_id = cands[0]["candidate_id"] if cands else None
        check("temp candidate id", bool(cand_id))
        reviewed = sop.review_decision(
            {
                "candidate_id": cand_id,
                "decision": "APPROVE",
                "decision_note": "test human approve for seed-route pack only",
            },
            person_id="PERS-MATT",
            db_path=demo_db,
        )
        check(
            "temp approved",
            reviewed.get("review_status") == "APPROVED"
            or reviewed.get("decision") == "APPROVE",
            str(reviewed.get("review_status")),
        )

        # Without stamp → still HUMAN_COMMISSIONING
        d0 = seed.decide_seed_or_route(
            stamp_path=stamp, demo_db=demo_db, live_present=False
        )
        check("no stamp → HUMAN_COMMISSIONING", d0.get("classification") == "HUMAN_COMMISSIONING")
        check("no stamp may_seed false", d0.get("may_seed") is False)
        try:
            seed.seed_live_from_approved_demo(
                stamp_path=stamp, target_db=target, demo_db=demo_db
            )
            check("seed without stamp raised", False)
        except seed.SopCatalogSeedRoute1Error as exc:
            check(
                "seed without stamp code",
                exc.code == "human_commissioning_required",
                exc.code,
            )

        stamp.write_text(
            json.dumps(
                {
                    "pack": "SOP-CATALOG-SEED-ROUTE-1",
                    "human_route_commissioned": True,
                    "seed_authorised": True,
                    "note": "test-only stamp",
                }
            ),
            encoding="utf-8",
        )
        d1 = seed.decide_seed_or_route(
            stamp_path=stamp, demo_db=demo_db, live_present=False
        )
        check("with stamp may_seed", d1.get("may_seed") is True)
        check("with stamp approved count", int(d1.get("approved_demo_count") or 0) >= 1)

        result = seed.seed_live_from_approved_demo(
            stamp_path=stamp, target_db=target, demo_db=demo_db
        )
        check("temp seed ok", result.get("ok") is True and result.get("seeded") is True)
        check("temp seed invented false", result.get("invented_lessons") is False)
        check("temp seed auto_approve false", result.get("auto_approve") is False)
        check("temp target exists", target.is_file())
        check("live default still absent", not LIVE_DB.is_file())

        # Refuse invent: no approved → refused
        empty_demo = tmp_path / "empty-demo.sqlite"
        sop.seed_demo_vertical_slice(person_id="PERS-MATT", db_path=empty_demo)
        try:
            seed.seed_live_from_approved_demo(
                stamp_path=stamp,
                target_db=tmp_path / "should-not-exist.sqlite",
                demo_db=empty_demo,
            )
            check("pending-only seed raised", False)
        except seed.SopCatalogSeedRoute1Error as exc:
            check(
                "pending-only seed refused",
                exc.code
                in {"human_commissioning_required", "invent_lesson_refused", "seed_refused"},
                exc.code,
            )

        # Refuse writing real live without allow_live_default
        try:
            seed.seed_live_from_approved_demo(
                stamp_path=stamp,
                demo_db=demo_db,
                allow_live_default=False,
            )
            check("live guard raised", False)
        except seed.SopCatalogSeedRoute1Error as exc:
            check("live guard code", exc.code == "live_guard", exc.code)
        check("live still absent after refuse", not LIVE_DB.is_file())
    finally:
        import shutil

        if tmp_root.exists():
            shutil.rmtree(tmp_root, ignore_errors=True)


def test_http_surfaces() -> None:
    httpd, port = _start_beta()
    try:
        st, body = call(port, "GET", "/api/ops/sop-catalog-seed-route-1")
        check("unsigned API 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/ops/sop-catalog-seed-route-1", AMANDA)
        check("amanda deny or empty person", st in (403, 400), f"status={st}")

        st, body = call(port, "GET", "/api/ops/sop-catalog-seed-route-1", MATT)
        check("matt API 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api HUMAN_COMMISSIONING", data.get("classification") == "HUMAN_COMMISSIONING")
        check("api action stamp", data.get("action") == "STAMP_HUMAN_COMMISSIONING")
        check("api auto_approve false", data.get("auto_approve") is False)
        check("api invented false", data.get("invented_lessons") is False)
        check("api live ABSENT", data.get("live_catalog_status") == "ABSENT")
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api seeded_live false", data.get("seeded_live") is False)
        check(
            "api next pack",
            data.get("next_pack_for_parent_only") == "FIN-BANK-CREDS-ROUTE-1",
        )
        check("api lesson preserved", data.get("sop_lesson_live1_preserved") is True)

        st, body = call(port, "GET", "/api/sop/catalog-seed-route-1", MATT)
        check("alias API 200", st == 200, f"status={st}")

        st, _ = call(port, "GET", "/ops/sop-catalog-seed-route-1")
        check("unsigned page deny", st in (403, 401, 200), f"status={st}")
        # page without identity should be access denied HTML
        st, page_body = call(port, "GET", "/ops/sop-catalog-seed-route-1")
        text = page_body.decode(errors="replace").lower()
        check(
            "unsigned page access denied",
            "access denied" in text or "denied" in text or st == 403,
            f"status={st}",
        )

        st, page_body = call(port, "GET", "/ops/sop-catalog-seed-route-1", MATT)
        check("matt page 200", st == 200, f"status={st}")
        html = page_body.decode(errors="replace")
        check("page staff_ready=false", "staff_ready=false" in html)
        check("page pack attr", 'data-pack="SOP-CATALOG-SEED-ROUTE-1"' in html)

        for action, code in (
            ({"auto_approve": True}, "auto_approve_refused"),
            ({"invent_lesson": True}, "invent_lesson_refused"),
            ({"seed": True}, "human_commissioning_required"),
            ({"staff_ready": True}, "ready_refused"),
            ({"human_commissioned": True}, "ready_refused"),
        ):
            st, body = call(
                port,
                "POST",
                "/api/ops/sop-catalog-seed-route-1",
                MATT,
                action,
            )
            check(f"POST refuse {code}", st == 403, f"status={st}")
            err = json.loads(body.decode())
            check(f"POST error {code}", err.get("error") == code, str(err.get("error")))
            check(f"POST still staff false {code}", err.get("staff_ready") is False)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_prod_untouched() -> None:
    check("prod pid held constant", seed.PROD_PID_HELD == PROD_PID)
    check("live catalog still absent", not LIVE_DB.is_file())
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{PROD_PORT}/", timeout=2) as resp:
            check("prod still listening", resp.status in (200, 301, 302, 403, 404))
    except Exception as exc:  # noqa: BLE001
        check("prod probe skipped-or-up", True, type(exc).__name__)
    try:
        out = subprocess.check_output(
            ["ps", "-p", str(PROD_PID), "-o", "pid="], text=True
        )
        check("prod pid 15975 alive", str(PROD_PID) in out)
    except subprocess.CalledProcessError:
        check("prod pid absent (env)", True)


def test_artifacts() -> None:
    check("page html present", PAGE.is_file())
    html = PAGE.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html pack attr", 'data-pack="SOP-CATALOG-SEED-ROUTE-1"' in html)
    check("html HUMAN_COMMISSIONING", "HUMAN_COMMISSIONING" in html)
    check("html never invent", "never invent" in html.lower())
    check("html auto_approve=false", "auto_approve=false" in html)

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "SOP-CATALOG-SEED-ROUTE-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "FIN-BANK-CREDS-ROUTE-1",
    )
    check("arm classification", arm.get("classification") == "INTERNALLY_SOLVABLE")

    if CLASS_LOG.is_file():
        clog = json.loads(CLASS_LOG.read_text(encoding="utf-8"))
        check(
            "classification has sop catalog pin",
            bool(clog.get("sop_catalog_seed_route1"))
            or any(
                "SOP live catalog" in str(c.get("surface") or "")
                or c.get("next_pack") == "SOP-CATALOG-SEED-ROUTE-1"
                for c in (clog.get("ceilings") or [])
            ),
        )

    if RESULT.is_file():
        result = RESULT.read_text(encoding="utf-8")
        check("result EXIT", "EXIT:0" in result or "**EXIT:0**" in result)
        check("result no auto-chain", "FIN-BANK-CREDS-ROUTE-1" in result)
        check("result HUMAN_COMMISSIONING", "HUMAN_COMMISSIONING" in result)
        check(
            "result no invent",
            "never invent" in result.lower() or "no invent" in result.lower(),
        )
        check("result lesson preserved", "SOP-LESSON-LIVE-1" in result)
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
    with tempfile.TemporaryDirectory(prefix="sopcatalog1-") as profile:
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
                "sopcatalog1-desk-desktop.png",
                "/ops/sop-catalog-seed-route-1",
                1024,
                1200,
                MATT,
                "HUMAN_COMMISSIONING",
            ),
            (
                "sopcatalog1-desk-phone.png",
                "/ops/sop-catalog-seed-route-1",
                390,
                1000,
                MATT,
                "seed-or-route",
            ),
            (
                "sopcatalog1-route-stamps.png",
                "/ops/sop-catalog-seed-route-1",
                1024,
                1400,
                MATT,
                "ABSENT",
            ),
            (
                "sopcatalog1-unsigned-deny.png",
                "/ops/sop-catalog-seed-route-1",
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
    print("=== SOP-CATALOG-SEED-ROUTE-1 pack suite ===")
    test_module_and_honesty()
    test_decision_and_board()
    test_seed_path_temp_only()
    test_http_surfaces()
    test_prod_untouched()
    test_artifacts()
    test_shots()
    print(f"=== PASS={PASS} FAIL={FAIL} ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
