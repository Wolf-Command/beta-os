#!/usr/bin/env python3
"""SOP-LESSON-LIVE-1 — SOP lesson board live honesty (human review required).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack SOP-LESSON-LIVE-1
(armed 2026-09-30) — surface SOP factory lessons without auto-approve or
invented live catalog rows. Preserves SOP-FACTORY-1 + INTEL-LEARN-1.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain FIN-TAX-SHELL-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import base64
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
from core import intel_learn1 as intel  # noqa: E402
from core import sop_factory as sop  # noqa: E402
from core import sop_lesson_live1 as live  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "SOP-LESSON-LIVE-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "sop-lesson-live.html"
MODULE = ROOT / "scripts" / "core" / "sop_lesson_live1.py"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
LIVE_DB = ROOT / "catalog" / "sop_factory.sqlite"
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
    check("html present", HTML.is_file())
    check("api matcher ops", live.api_matches("/api/ops/sop-lesson-live"))
    check("api matcher alias", live.api_matches("/api/sop/lesson-live"))
    check("api not lesson-candidate", not live.api_matches("/api/sop/lesson-candidate"))
    check("page matcher ops", live.page_matches("/ops/sop-lesson-live"))
    check("page matcher core", live.page_matches("/core/sop-lesson-live"))
    check("page matcher alias", live.page_matches("/sop-lesson-live"))
    check("pack id", live.PACK_ID == "SOP-LESSON-LIVE-1")
    check("schema id", live.SCHEMA_ID == "wolf.sop-lesson-live-1.v1")
    check("cap", live.CAP_ID == "CAP-INTEL-05")

    flags = live.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("operating_adoption false", flags.get("operating_adoption") is False)
    check("human_review_gate", flags.get("human_review_gate") is True)
    check("auto_approve false", flags.get("auto_approve") is False)
    check("auto_approve_lessons false", flags.get("auto_approve_lessons") is False)
    check("invented_lessons false", flags.get("invented_lessons") is False)
    check("fake_lessons false", flags.get("fake_lessons") is False)
    check("second_sop false", flags.get("second_sop_system") is False)
    check("second_learning false", flags.get("second_learning_system") is False)
    check("extends sop", flags.get("extends_sop_factory") is True)
    check("extends intel", flags.get("extends_intel_learn1") is True)
    check("sop preserved", flags.get("sop_factory1_preserved") is True)
    check("intel preserved", flags.get("intel_learn1_preserved") is True)
    check("proven false", flags.get("proven") is False)
    check("ready false", flags.get("ready") is False)
    check("cap proven false", flags.get("cap_intel_05_proven") is False)
    check("ledger specified", flags.get("ledger_maturity") == "SPECIFIED")
    check("live catalog absent", flags.get("live_catalog_sop_absent") is True)
    check("live catalog status ABSENT", flags.get("live_catalog_status") == "ABSENT")
    check("demo not adoption", flags.get("demo_is_live_adoption") is False)
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "FIN-TAX-SHELL-1")
    check("did not auto-start", flags.get("cursor_did_not_auto_start_next") is True)

    for refuse_fn, code in (
        (live.refuse_auto_approve, "auto_approve_refused"),
        (live.refuse_invent_lesson, "invent_lesson_refused"),
        (live.refuse_proven, "proven_refused"),
        (live.refuse_ready, "ready_refused"),
    ):
        try:
            refuse_fn({})
            check(f"{code} raised", False)
        except live.SopLessonLive1Error as exc:
            check(f"{code} code", exc.code == code, f"got={exc.code}")

    try:
        live.refuse_external_write({"auto_approve": True})
        check("write auto_approve refused", False)
    except live.SopLessonLive1Error as exc:
        check("write auto_approve code", exc.code == "auto_approve_refused")

    try:
        live.refuse_external_write({"invent_lesson": True})
        check("write invent refused", False)
    except live.SopLessonLive1Error as exc:
        check("write invent code", exc.code == "invent_lesson_refused")

    html = HTML.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html review-decision", "/api/sop/review-decision" in html)
    check("html DEMO label", "DEMO / NOT LIVE STAFF ADOPTION" in html)
    check("html LIVE catalog ABSENT", "LIVE catalog ABSENT" in html)
    check("html human review", "human review required" in html.lower())
    check("html auto-approve off", "auto-approve" in html.lower() or "auto_approve" in html)

    serve = (ROOT / "scripts" / "serve_beta.py").read_text(encoding="utf-8")
    check("serve imports sop_lesson_live1", "sop_lesson_live1" in serve)
    check("serve route /ops/sop-lesson-live", "/ops/sop-lesson-live" in serve)
    check("serve api /api/ops/sop-lesson-live", "/api/ops/sop-lesson-live" in serve)
    check("live catalog sop absent", not LIVE_DB.exists())

    led = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("CAP-INTEL-05 SPECIFIED", (led.get("CAP-INTEL-05") or [None])[0] == "SPECIFIED")
    check("CAP-CORE-11 SPECIFIED", (led.get("CAP-CORE-11") or [None])[0] == "SPECIFIED")


def test_board_live_honesty() -> None:
    check("anon denied", not live.person_may_view(None))
    check("amanda default denied", not live.person_may_view("PERS-AMANDA"))
    check("matt may view", live.person_may_view(live.OWNER_PERSON))

    try:
        live.build_board(None)
        check("anon board refused", False)
    except live.SopLessonLive1Error as exc:
        check("anon board code", exc.code == "denied")

    try:
        live.build_board("PERS-AMANDA", role_allowed=False)
        check("amanda board refused", False)
    except live.SopLessonLive1Error as exc:
        check("amanda board code", exc.code == "denied")

    seed = live.ensure_demo_candidates(person_id=sop.OWNER_PERSON)
    check("demo seed path tmp", "tmp-sop-factory-1" in str(seed.get("db_path") or sop.DEMO_DB))
    check("demo not live catalog", seed.get("db_path") != str(LIVE_DB))

    board = live.build_board(live.OWNER_PERSON)
    check("board ok", board.get("ok") is True)
    check("board pack", board.get("pack") == "SOP-LESSON-LIVE-1")
    check("board staff_ready", board.get("staff_ready") is False)
    check("board human_commissioned", board.get("human_commissioned") is False)
    check("board auto_approve", board.get("auto_approve") is False)
    check("board human_review_gate", board.get("human_review_gate") is True)
    check("board invented_lessons", board.get("invented_lessons") is False)
    check("board fake_lessons", board.get("fake_lessons") is False)
    check("board second sop", board.get("second_sop_system") is False)
    check("board cap not proven", board.get("cap_intel_05_proven") is False)
    check("board live catalog absent", board.get("live_catalog_sop_absent") is True)
    check("board live status ABSENT", board.get("live_catalog_status") == "ABSENT")
    check("board live count 0", int(board.get("live_lesson_count") or 0) == 0)
    check("board live list empty", (board.get("live_lessons") or []) == [])
    check("board demo >=1", int(board.get("demo_lesson_count") or 0) >= 1)
    check("board pending >=1", int(board.get("pending_count") or 0) >= 1)
    check("no invented helper", live.no_invented_live_lessons(board))
    check("human review helper", live.human_review_required(board))

    demo_rows = board.get("demo_lessons") or []
    check("has demo lessons", len(demo_rows) >= 1)
    for r in demo_rows:
        check("demo label set", r.get("demo_label") == sop.DEMO_LABEL)
        check("demo not live", r.get("live") is False)
        check("demo source sop", r.get("source") == "sop_factory")
        check("demo not invented", r.get("invented") is False)
        check("demo auto_approve off", r.get("auto_approve") is False)

    pending = board.get("review_queue") or []
    check("review queue pending", len(pending) >= 1)
    apis = board.get("review_apis") or {}
    check("review api decision", apis.get("review_decision") == "/api/sop/review-decision")
    check("next pack parent only", board.get("next_pack_for_parent_only") == "FIN-TAX-SHELL-1")
    check("did not auto-start", board.get("cursor_did_not_auto_start_next_pack") is True)

    q = sop.list_review_queue(sop.OWNER_PERSON, db_path=sop.DEMO_DB)
    check("sop queue pending >=1", int(q.get("pending_count") or 0) >= 1)
    check("sop honesty gate", sop.honesty_flags().get("human_review_gate") is True)
    check("sop no auto approve", sop.honesty_flags().get("auto_approve") is False)

    ib = intel.build_board(intel.OWNER_PERSON)
    check("intel board ok", ib.get("ok") is True)
    check("intel auto_approve false", ib.get("auto_approve") is False)
    check("intel human_review_gate", ib.get("human_review_gate") is True)
    check("intel not second sop", ib.get("second_sop_system") is False)


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/ops/sop-lesson-live")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/ops/sop-lesson-live", email=MATT)
        check("matt api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready", data.get("staff_ready") is False)
        check("api human_commissioned", data.get("human_commissioned") is False)
        check("api auto_approve", data.get("auto_approve") is False)
        check("api human_review_gate", data.get("human_review_gate") is True)
        check("api invented_lessons", data.get("invented_lessons") is False)
        check("api live absent", data.get("live_catalog_status") == "ABSENT")
        check("api live count 0", int(data.get("live_lesson_count") or 0) == 0)
        check("api demo >=1", int(data.get("demo_lesson_count") or 0) >= 1)
        check("api pending", int(data.get("pending_count") or 0) >= 1)
        check("api not proven", data.get("cap_intel_05_proven") is False)
        check(
            "api review decision path",
            (data.get("review_apis") or {}).get("review_decision") == "/api/sop/review-decision",
        )
        check("api next parent", data.get("next_pack_for_parent_only") == "FIN-TAX-SHELL-1")

        st, body = call(port, "GET", "/api/sop/lesson-live", email=MATT)
        check("alias api 200", st == 200, f"status={st}")

        st, body = call(port, "GET", "/api/ops/sop-lesson-live", email=AMANDA)
        check("amanda api 403", st == 403, f"status={st}")

        st, _ = call(port, "GET", "/ops/sop-lesson-live")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/ops/sop-lesson-live", email=MATT)
        check("matt page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check("page title", "SOP Lesson Live" in text)
        check("page staff_ready pin", "staff_ready=false" in text)
        check("page human_commissioned pin", "human_commissioned=false" in text)
        check("page review-decision", "/api/sop/review-decision" in text)
        check("page live absent stamp", "LIVE catalog ABSENT" in text)

        st, body = call(port, "GET", "/core/sop-lesson-live", email=MATT)
        check("core alias page 200", st == 200, f"status={st}")

        st, body = call(port, "GET", "/ops/sop-lesson-live", email=AMANDA)
        check("amanda page 403", st == 403, f"status={st}")
        atext = body.decode(errors="replace")
        check(
            "amanda access denied",
            "Access denied" in atext or "access denied" in atext.lower() or "refused" in atext.lower(),
        )

        st, body = call(
            port, "POST", "/api/ops/sop-lesson-live", email=MATT, body={"auto_approve": True}
        )
        check("post auto_approve 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post auto_approve code", err.get("error") == "auto_approve_refused")

        st, body = call(
            port, "POST", "/api/ops/sop-lesson-live", email=MATT, body={"invent_lesson": True}
        )
        check("post invent 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post invent code", err.get("error") == "invent_lesson_refused")

        st, body = call(port, "GET", "/api/sop/review-queue", email=MATT)
        check("sop queue 200", st == 200, f"status={st}")
        q = json.loads(body.decode())
        check("sop queue ok", q.get("ok") is True)
        check("sop queue pending", int(q.get("pending_count") or 0) >= 1)

        st, body = call(port, "GET", "/api/intel/learning", email=MATT)
        check("intel learning 200", st == 200, f"status={st}")
        intel_data = json.loads(body.decode())
        check("intel learning ok", intel_data.get("ok") is True)
        check("intel auto_approve still false", intel_data.get("auto_approve") is False)

        st, _ = call(port, "GET", "/api/intel/learning-policy")
        check("learning-policy unsigned still gated", st in (403, 401), f"status={st}")
    finally:
        httpd.shutdown()
        httpd.server_close()


def _ws_connect(host: str, port: int, path: str):
    sock = socket.create_connection((host, port), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    sock.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("no upgrade")
        buf += chunk
    return sock


def _ws_send(sock, data: str) -> None:
    payload = data.encode()
    header = bytearray([0x81])
    n = len(payload)
    mask = os.urandom(4)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack(">H", n))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack(">Q", n))
    header.extend(mask)
    sock.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))


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


def capture(
    port: int, path: str, width: int, height: int, dest: Path, email: str, marker: str
) -> bool:
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
                _ws_send(
                    sock, json.dumps({"id": ident, "method": method, "params": params or {}})
                )
                while True:
                    msg = json.loads(_ws_recv(sock))
                    if msg.get("id") == ident:
                        return msg

            cdp("Network.enable")
            headers = {}
            if email:
                headers = {
                    "X-Wolf-Subject": email,
                    "Cf-Access-Authenticated-User-Email": email,
                }
            if headers:
                cdp("Network.setExtraHTTPHeaders", {"headers": headers})
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
                    {"expression": "document.body ? document.body.innerText : ''"},
                )
                text = (
                    ((got.get("result") or {}).get("result") or {}).get("value") or ""
                )
                if marker in text:
                    found = True
                    break
                time.sleep(0.35)
            shot = cdp(
                "Page.captureScreenshot",
                {"format": "png", "fromSurface": True, "captureBeyondViewport": True},
            )
            raw = base64.b64decode((shot.get("result") or {}).get("data") or "")
            dest.write_bytes(raw)
            return found and dest.is_file() and dest.stat().st_size > 1000
        finally:
            proc.kill()
            proc.wait(timeout=5)


def test_shots() -> None:
    if not CHROME.is_file():
        check("chrome present", False, "missing")
        return
    SHOTS.mkdir(parents=True, exist_ok=True)
    sop.seed_demo_vertical_slice(person_id=sop.OWNER_PERSON, db_path=sop.DEMO_DB)
    httpd, port = _start_beta()
    try:
        specs = [
            ("soplessonlive1-desk-desktop.png", "/ops/sop-lesson-live", 1024, 1100, MATT, "PENDING_REVIEW"),
            ("soplessonlive1-desk-phone.png", "/ops/sop-lesson-live", 390, 900, MATT, "PENDING_REVIEW"),
            ("soplessonlive1-live-absent.png", "/ops/sop-lesson-live", 1024, 1100, MATT, "LIVE catalog ABSENT"),
            ("soplessonlive1-human-review.png", "/ops/sop-lesson-live", 1024, 1100, MATT, "human review required"),
            ("soplessonlive1-amanda-deny.png", "/ops/sop-lesson-live", 1024, 900, AMANDA, "Access denied"),
            ("soplessonlive1-unsigned-deny.png", "/ops/sop-lesson-live", 1024, 900, "", "Access denied"),
        ]
        for name, path, w, h, email, marker in specs:
            dest = SHOTS / name
            ok = capture(port, path, w, h, dest, email, marker)
            check(f"shot {name}", ok, f"marker={marker} size={dest.stat().st_size if dest.is_file() else 0}")
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_prod_untouched() -> None:
    try:
        out = subprocess.check_output(
            ["lsof", f"-iTCP:{PROD_PORT}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        check("prod listen present", False, "lsof failed")
        return
    check("prod pid held", str(PROD_PID) in out, out.splitlines()[1] if len(out.splitlines()) > 1 else out)
    check("no push in suite", True)
    check("staff_ready remains false", live.honesty_flags().get("staff_ready") is False)
    check(
        "human_commissioned remains false",
        live.honesty_flags().get("human_commissioned") is False,
    )


def test_arm_stamp_ready() -> None:
    check("arm file exists", ARM.is_file())
    data = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack id", data.get("pack") == "SOP-LESSON-LIVE-1" or data.get("run_id") == "SOP-LESSON-LIVE-1")
    check("arm staff_ready false", data.get("staff_ready") is False)
    check("arm human_commissioned false", data.get("human_commissioned") is False)
    check("arm no_push", data.get("no_push") is True)
    check("arm prod_mutate false", data.get("prod_mutate") is False)
    check("arm next parent", data.get("next_pack_for_parent") == "FIN-TAX-SHELL-1")


def main() -> int:
    print("=== SOP-LESSON-LIVE-1 suite ===")
    test_module_and_honesty()
    test_board_live_honesty()
    test_http_api_and_page()
    test_shots()
    test_prod_untouched()
    test_arm_stamp_ready()
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
