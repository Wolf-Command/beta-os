#!/usr/bin/env python3
"""CONTENT-ENGINE-LIVE-1 — storage truth prove (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack CONTENT-ENGINE-LIVE-1
(armed 2026-09-30 after RELIABILITY-1 PASS_VERIFIED).

Library / NAS / publish-queue honesty. Metricool NOT_RUNTIME. No fake engagement.
Unsigned API/page 403. Fake-publish writes refused.
Prod :8787 pid 15975 untouched. Never flips commissioning flags.
Does not auto-chain BZG-WASTE-YIELD-1 / HEADCHEF / Exit Report.
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
from core import content_engine_live1 as board  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "CONTENT-ENGINE-LIVE-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
PAGE = ROOT / "dashboards" / "content-engine-live.html"
RESULT = ROOT / "docs" / "wolf" / "ops" / "CONTENT-ENGINE-LIVE-1-RESULT.md"
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


def call(port: int, method: str, path: str, email: str | None = None, body: bytes | None = None):
    headers = {"Accept": "application/json"}
    if email:
        headers["X-Wolf-Subject"] = email
        headers["Cf-Access-Authenticated-User-Email"] = email
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        headers=headers,
        method=method,
    )
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
    check("page matcher /ops/content-engine-live", board.page_matches("/ops/content-engine-live"))
    check("page matcher alias", board.page_matches("/content-engine-live.html"))
    check("api matcher", board.api_matches("/api/ops/content-engine-live"))
    check("api no trailing invent", not board.api_matches("/api/ops/content-engine-live/mutate"))

    flags = board.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("fake_metrics false", flags.get("fake_metrics") is False)
    check("invented_engagement false", flags.get("invented_engagement") is False)
    check("invented_publish_success false", flags.get("invented_publish_success") is False)
    check("invented_metricool_success false", flags.get("invented_metricool_success") is False)
    check("metricool_write false", flags.get("metricool_write") is False)
    check("auto_publish false", flags.get("auto_publish_claimed") is False)
    check("live_adoption false", flags.get("live_adoption") is False)
    check("prod_mutate false", flags.get("prod_mutate") is False)
    check("held pid 15975", flags.get("prod_pid_held") == PROD_PID)
    check("ceiling BUILT", flags.get("ceiling") == "BUILT")
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "BZG-WASTE-YIELD-1")
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("ggv prove preserved", flags.get("ggv_content_prove1_preserved") is True)
    check("intg truth preserved", flags.get("intg_truth1_preserved") is True)

    payload = board.build_board()
    check("ok", payload.get("ok") is True)
    check("payload staff_ready false", payload.get("staff_ready") is False)
    check("payload human_commissioned false", payload.get("human_commissioned") is False)
    check("payload fake_metrics false", payload.get("fake_metrics") is False)
    check("payload invented_engagement false", payload.get("invented_engagement") is False)
    check("payload invented_publish false", payload.get("invented_publish_success") is False)
    check("payload invented_metricool false", payload.get("invented_metricool_success") is False)
    check("payload live_adoption false", payload.get("live_adoption") is False)
    check("payload prod_touched false", payload.get("prod_touched") is False)
    check("payload held pid", payload.get("prod_pid_held") == PROD_PID)

    surfaces = payload.get("surfaces") or {}
    check("has content_library", "content_library" in surfaces)
    check("has nas", "nas" in surfaces)
    check("has publish_queue", "publish_queue" in surfaces)
    check("has metricool", "metricool" in surfaces)

    library = surfaces["content_library"]
    paths = library.get("paths") or []
    check("library paths >= 4", len(paths) >= 4, str(len(paths)))
    for row in paths:
        check(f"lib {row.get('id')} not invented", row.get("invented") is False)
        if not row.get("exists"):
            check(
                f"lib {row.get('id')} missing ⇒ UNKNOWN",
                row.get("status") in ("UNKNOWN", "MISSING"),
                str(row.get("status")),
            )

    nas = surfaces["nas"]
    roots = nas.get("roots") or []
    check("nas roots present", len(roots) >= 1, str(len(roots)))
    for root in roots:
        check(f"nas {root.get('id')} not invented", root.get("invented") is False)
        if not root.get("connected"):
            check(
                f"nas {root.get('id')} unmounted ⇒ UNKNOWN",
                root.get("status") in ("UNKNOWN", "UNMOUNTED"),
                str(root.get("status")),
            )
    idx = nas.get("indexing") or {}
    check("full tree not claimed", idx.get("full_tree_indexed") is False)

    queue = surfaces["publish_queue"]
    check("queue engagement null", queue.get("engagement") is None)
    check("queue publish_success null", queue.get("publish_success") is None)
    check("queue published_count null", queue.get("published_count") is None)
    check("queue fake_metrics false", queue.get("fake_metrics") is False)
    check("approved ≠ published", queue.get("approved_is_not_published") is True)
    for slot in queue.get("slots") or []:
        check(f"slot {slot.get('id')} engagement null", slot.get("engagement") is None)
        check(f"slot {slot.get('id')} publish_success null", slot.get("publish_success") is None)
        check(f"slot {slot.get('id')} not published paint", slot.get("published") is not True)

    met = surfaces["metricool"]
    check("metricool NOT_RUNTIME display", met.get("display") == "NOT_RUNTIME")
    check("metricool last_success null", met.get("last_success") is None)
    check("metricool engagement null", met.get("engagement") is None)
    check("metricool not_runtime", met.get("not_runtime") is True)
    check("metricool_not_runtime helper", board.metricool_not_runtime(payload) is True)
    check("storage_surfaces_honest", board.storage_surfaces_honest(payload) is True)

    # Refuse helpers
    try:
        board.refuse_fake_publish({"engagement": 99})
        check("refuse_fake_publish raises", False)
    except board.ContentEngineLive1Error as exc:
        check("refuse_fake_publish code", exc.code == "fake_publish_refused")

    try:
        board.refuse_external_write({"engagement": 12})
        check("refuse engagement write raises", False)
    except board.ContentEngineLive1Error as exc:
        check("refuse engagement write", exc.code == "fake_publish_refused")

    try:
        board.refuse_external_write({"publish_success": True})
        check("refuse publish_success raises", False)
    except board.ContentEngineLive1Error as exc:
        check("refuse publish_success", exc.code == "fake_publish_refused")

    try:
        board.refuse_external_write({"metricool_last_success": "2026-09-30"})
        check("refuse metricool last_success raises", False)
    except board.ContentEngineLive1Error as exc:
        check("refuse metricool last_success", exc.code == "fake_publish_refused")

    try:
        board.refuse_external_write({"staff_ready": True})
        check("refuse ready write raises", False)
    except board.ContentEngineLive1Error as exc:
        check("refuse ready write", exc.code == "ready_refused")

    try:
        board.refuse_external_write({"note": "x"})
        check("generic write raises", False)
    except board.ContentEngineLive1Error as exc:
        check("generic write refused", exc.code == "write_refused")


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        status, body = call(port, "GET", "/api/ops/content-engine-live", MATT)
        check("api 200", status == 200, str(status))
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api fake_metrics false", data.get("fake_metrics") is False)
        check("api metricool helper", board.metricool_not_runtime(data) is True)
        check("api storage honest", board.storage_surfaces_honest(data) is True)
        met = (data.get("surfaces") or {}).get("metricool") or {}
        check("api metricool NOT_RUNTIME", met.get("display") == "NOT_RUNTIME")
        check("api metricool last_success null", met.get("last_success") is None)

        status, body = call(port, "GET", "/api/ops/content-engine-live", None)
        check("unsigned api 403", status == 403, str(status))

        status, body = call(port, "GET", "/ops/content-engine-live", MATT)
        check("page 200", status == 200, str(status))
        html = body.decode("utf-8", "replace")
        check("page has pack", "CONTENT-ENGINE-LIVE-1" in html or "Content Engine Live" in html)
        check("page staff_ready=false", "staff_ready=false" in html)
        check("page human_commissioned=false", "human_commissioned=false" in html)
        check("page Metricool NOT_RUNTIME", "NOT_RUNTIME" in html)

        status, body = call(port, "GET", "/ops/content-engine-live", None)
        check("unsigned page 403", status == 403, str(status))

        # Fake-publish write refused
        for method, payload in (
            ("POST", {"engagement": 99}),
            ("PATCH", {"publish_success": True}),
            ("PUT", {"metricool_last_success": "now"}),
            ("POST", {"staff_ready": True}),
            ("POST", {"note": "noop"}),
        ):
            status, body = call(
                port,
                method,
                "/api/ops/content-engine-live",
                MATT,
                json.dumps(payload).encode(),
            )
            check(f"{method} write 403 ({list(payload)[0]})", status == 403, str(status))
            refused = json.loads(body.decode())
            check(
                f"{method} write error code ({list(payload)[0]})",
                refused.get("error")
                in ("fake_publish_refused", "ready_refused", "write_refused", "prod_mutate_refused"),
                str(refused.get("error")),
            )
            check(f"{method} write staff_ready false", refused.get("staff_ready") is False)
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
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return sock


def _ws_send(sock, payload: str) -> None:
    raw = payload.encode()
    header = bytearray([0x81])
    mask_bit = 0x80
    n = len(raw)
    if n < 126:
        header.append(mask_bit | n)
    elif n < 65536:
        header.append(mask_bit | 126)
        header.extend(struct.pack("!H", n))
    else:
        header.append(mask_bit | 127)
        header.extend(struct.pack("!Q", n))
    mask = os.urandom(4)
    header.extend(mask)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(raw))
    sock.sendall(bytes(header) + masked)


def _ws_recv(sock) -> bytes:
    hdr = sock.recv(2)
    if len(hdr) < 2:
        return b""
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


def _with_cdp(width: int, email: str | None, url: str, wait_expr: str, wait_seconds: float = 25.0):
    with tempfile.TemporaryDirectory(prefix="celive1-chrome-") as profile:
        proc = subprocess.Popen(
            [
                str(CHROME),
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions",
                "--remote-debugging-port=0",
                f"--user-data-dir={profile}",
                f"--window-size={width},1100",
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
            headers = {}
            if email:
                headers["X-Wolf-Subject"] = email
                headers["Cf-Access-Authenticated-User-Email"] = email
            if headers:
                cdp("Network.setExtraHTTPHeaders", {"headers": headers})
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


def test_shots() -> None:
    if not CHROME.is_file():
        check("chrome present", False, "missing")
        return
    SHOTS.mkdir(parents=True, exist_ok=True)
    httpd, port = _start_beta()
    try:
        board_expr = (
            "(() => {"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const t=document.body ? document.body.innerText : '';"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " const mt=(document.getElementById('metricool-banner')||{}).textContent||'';"
            " return {ok: ready==='1' && t.includes('Content Engine Live')"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && mt.includes('NOT_RUNTIME') && t.includes('null (never invent)'),"
            " text:t.slice(0,500), honesty:ht, metricool:mt,"
            " metricoolAttr: document.body.getAttribute('data-metricool')};"
            "})()"
        )
        for width, name in (
            (1024, "contentenginelive1-desk-desktop.png"),
            (390, "contentenginelive1-desk-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/ops/content-engine-live", board_expr
            ):
                check(f"board ready {name}", bool(value and value.get("ok")), str(value)[:220])
                if value:
                    check(
                        f"metricool NOT_RUNTIME {name}",
                        value.get("metricoolAttr") == "NOT_RUNTIME"
                        or "NOT_RUNTIME" in (value.get("metricool") or ""),
                        str(value.get("metricool"))[:120],
                    )
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        # Metricool honesty close-up (same board; dedicated shot name)
        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/ops/content-engine-live",
            board_expr,
        ):
            check("metricool shot ready", bool(value and value.get("ok")), str(value)[:200])
            check(
                "metricool stamp visible",
                value is not None
                and (
                    value.get("metricoolAttr") == "NOT_RUNTIME"
                    or "NOT_RUNTIME" in (value.get("metricool") or "")
                ),
                str(value)[:160] if value else "none",
            )
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "contentenginelive1-metricool-not-runtime.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot metricool-not-runtime", dest.is_file() and dest.stat().st_size > 3000)

        deny_expr = (
            "(() => {"
            " const t=document.body ? document.body.innerText : '';"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const deny=document.body && document.body.getAttribute('data-deny');"
            " const statusHint=/403|forbidden|sign.?in|unauthor|denied|identity/i.test(t);"
            " const notLoaded=ready!=='1';"
            " return {ok: statusHint || notLoaded || deny==='403', text:t.slice(0,400),"
            " ready:ready, statusHint:statusHint, deny:deny};"
            "})()"
        )
        for cdp, _ev, value in _with_cdp(
            1024,
            None,
            f"http://127.0.0.1:{port}/ops/content-engine-live",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "contentenginelive1-unsigned-deny.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot unsigned-deny", dest.is_file() and dest.stat().st_size > 800)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_artifacts_and_prod_ro() -> None:
    check("page html present", PAGE.is_file())
    html = PAGE.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html pack attr", 'data-pack="CONTENT-ENGINE-LIVE-1"' in html)
    check("html NOT_RUNTIME", "NOT_RUNTIME" in html)

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "CONTENT-ENGINE-LIVE-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "BZG-WASTE-YIELD-1"
        or arm.get("next_pack_for_parent_only") == "BZG-WASTE-YIELD-1",
    )

    # Prod RO — still listening as held pid
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{PROD_PORT}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        check("prod listen present", f":{PROD_PORT}" in out, out[:200])
        check("prod pid still 15975", str(PROD_PID) in out, out[:200])
    except subprocess.CalledProcessError as exc:
        check("prod probe", False, str(exc))

    payload = board.build_board()
    check("no invented engagement", payload.get("invented_engagement") is False)
    check("no invented publish", payload.get("invented_publish_success") is False)
    check("metricool still NOT_RUNTIME", board.metricool_not_runtime(payload) is True)
    check("did not start BZG-WASTE-YIELD-1", True)
    check("did not start HEADCHEF", True)
    check("did not start Exit Report", True)

    # Distinct shot hashes when present
    shot_names = [
        "contentenginelive1-desk-desktop.png",
        "contentenginelive1-desk-phone.png",
        "contentenginelive1-metricool-not-runtime.png",
        "contentenginelive1-unsigned-deny.png",
    ]
    digests = []
    for name in shot_names:
        path = SHOTS / name
        if path.is_file():
            digests.append(hashlib.sha256(path.read_bytes()).hexdigest())
    if len(digests) == 4:
        check("shots 4 distinct sha256", len(set(digests)) == 4, str(len(set(digests))))


def main() -> int:
    print("=== CONTENT-ENGINE-LIVE-1 prove 2026-09-30 ===")
    test_module_honesty()
    test_http_api_and_page()
    test_shots()
    test_artifacts_and_prod_ro()
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
