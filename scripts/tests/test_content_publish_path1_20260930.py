#!/usr/bin/env python3
"""CONTENT-PUBLISH-PATH-1 — Publish path honesty (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave8 pack
CONTENT-PUBLISH-PATH-1 (armed 2026-09-30 after CRM-PIPELINE-TRUTH-1 PASS_VERIFIED).

Document publish path; keep Metricool write DISABLED / NOT_RUNTIME.
Never invent publish success. Preserves METRICOOL-RUNTIME-WIRE-1,
CONTENT-ENGINE-LIVE-1, GGV-METRIC-HONESTY-1.
Unsigned API/page 403. Writes refused.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain OCCUPANCY-EXTERNAL-HOLD-1 / HEADCHEF / Exit Report.
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
# Keep Metricool write disabled for honesty suite.
os.environ.pop("BETA_METRICOOL_WRITE_ENABLED", None)
sys.path.insert(0, str(ROOT / "scripts"))

import serve_beta as sb  # noqa: E402
from core import content_engine_live1 as cel  # noqa: E402
from core import content_publish_path1 as pub  # noqa: E402
from core import ggv_metric_honesty1 as ggv  # noqa: E402
from core import metricool_runtime_wire1 as mw  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
ZAYEN = "laluzayen@gmail.com"
ARM = ROOT / "state" / "final-completion" / "packs" / "CONTENT-PUBLISH-PATH-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "content-publish-path-1.html"
MODULE = ROOT / "scripts" / "core" / "content_publish_path1.py"
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
    check(
        "page matcher /ops/content-publish-path-1",
        pub.page_matches("/ops/content-publish-path-1"),
    )
    check("page matcher alias html", pub.page_matches("/content-publish-path-1.html"))
    check("page matcher content path", pub.page_matches("/content/publish-path-1"))
    check("page matcher ggv", pub.page_matches("/ggv/content-publish-path-1"))
    check("api matcher", pub.api_matches("/api/ops/content-publish-path-1"))
    check("api alias ggv", pub.api_matches("/api/ggv/content-publish-path-1"))
    check("api no mutate path", not pub.api_matches("/api/ops/content-publish-path-1/mutate"))

    flags = pub.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("classification HUMAN_COMMISSIONING", flags.get("classification") == "HUMAN_COMMISSIONING")
    check(
        "pack classification",
        flags.get("pack_classification") == "HUMAN_COMMISSIONING_OR_EXTERNAL",
    )
    check("invented_publish_success false", flags.get("invented_publish_success") is False)
    check("invented_engagement false", flags.get("invented_engagement") is False)
    check("fake_metrics false", flags.get("fake_metrics") is False)
    check("metricool_write false", flags.get("metricool_write") is False)
    check("metricool_write_disabled true", flags.get("metricool_write_disabled") is True)
    check("publish_success null", flags.get("publish_success") is None)
    check("engagement null", flags.get("engagement") is None)
    check("last_success null", flags.get("last_success") is None)
    check("real_external_publish NO", flags.get("real_external_publish") == "NO")
    check("approved not published", flags.get("approved_is_not_published") is True)
    check("live_publish false", flags.get("live_publish") is False)
    check("mw preserved flag", flags.get("metricool_runtime_wire1_preserved") is True)
    check("cel preserved flag", flags.get("content_engine_live1_preserved") is True)
    check("ggv preserved flag", flags.get("ggv_metric_honesty1_preserved") is True)
    check("cap proven false", flags.get("cap_ggv_publish_proven") is False)
    check("cap ready false", flags.get("cap_ggv_publish_ready") is False)
    check("ceiling BUILT", flags.get("cap_ggv_publish_ceiling") == "BUILT")
    check("maturity SPECIFIED", flags.get("cap_ggv_publish_maturity") == "SPECIFIED")
    check(
        "next pack parent only",
        flags.get("next_pack_for_parent_only") == "OCCUPANCY-EXTERNAL-HOLD-1",
    )
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("prod pid held const", pub.PROD_PID_HELD == PROD_PID)

    check("Matt may view", pub.person_may_view("PERS-MATT") is True)
    check("Amanda may view", pub.person_may_view("PERS-AMANDA") is True)
    check("Zayen may NOT", pub.person_may_view("PERS-ZAYEN") is False)

    try:
        pub.refuse_fake_publish({"publish_success": True})
        check("refuse_fake_publish raises", False)
    except pub.ContentPublishPath1Error as exc:
        check("refuse_fake_publish raises", True)
        check("refuse_fake_publish code", exc.code == "fake_publish_refused")
    try:
        pub.refuse_invent_publish({"published": 12})
        check("refuse_invent_publish raises", False)
    except pub.ContentPublishPath1Error as exc:
        check("refuse_invent_publish raises", True)
        check("refuse_invent_publish code", exc.code == "invent_publish_refused")
    try:
        pub.refuse_metricool_write({"metricool_write": True})
        check("refuse_metricool_write raises", False)
    except pub.ContentPublishPath1Error as exc:
        check("refuse_metricool_write raises", True)
        check("refuse_metricool_write code", exc.code == "metricool_write_refused")
    try:
        pub.refuse_fake_engagement({"engagement": 99})
        check("refuse_fake_engagement raises", False)
    except pub.ContentPublishPath1Error as exc:
        check("refuse_fake_engagement raises", True)
        check("refuse_fake_engagement code", exc.code == "engagement_refused")

    try:
        pub.refuse_external_write({"publish_success": True})
        check("refuse write publish_success raises", False)
    except pub.ContentPublishPath1Error as exc:
        check(
            "refuse write publish_success",
            exc.code in ("fake_publish_refused", "invent_publish_refused"),
            f"got={exc.code}",
        )
    try:
        pub.refuse_external_write({"metricool_write": True})
        check("refuse write metricool_write raises", False)
    except pub.ContentPublishPath1Error as exc:
        check("refuse write metricool_write", exc.code == "metricool_write_refused")
    try:
        pub.refuse_external_write({"engagement": 1})
        check("refuse write engagement raises", False)
    except pub.ContentPublishPath1Error as exc:
        check("refuse write engagement", exc.code == "engagement_refused")
    try:
        pub.refuse_external_write({"proven": True})
        check("refuse write proven raises", False)
    except pub.ContentPublishPath1Error as exc:
        check("refuse write proven", exc.code == "proven_refused")
    try:
        pub.refuse_external_write({"noop": True})
        check("refuse write generic raises", False)
    except pub.ContentPublishPath1Error as exc:
        check("refuse write generic", exc.code == "write_refused")


def test_desk_payload() -> None:
    write = pub.metricool_write_surface()
    check("write status NOT_RUNTIME", write.get("status") == "NOT_RUNTIME")
    check("write_status DISABLED", write.get("write_status") == "DISABLED")
    check("write_enabled false", write.get("write_enabled") is False)
    check("write real_external NO", write.get("real_external_publish") == "NO")
    check("write publish_success null", write.get("publish_success") is None)

    pub_surf = pub.publish_success_surface()
    check("pub surface NOT_RUNTIME", pub_surf.get("status") == "NOT_RUNTIME")
    check("pub surface value null", pub_surf.get("value") is None)
    check("pub surface publish_success null", pub_surf.get("publish_success") is None)

    eng = pub.engagement_surface()
    check("eng surface NOT_RUNTIME", eng.get("status") == "NOT_RUNTIME")
    check("eng surface engagement null", eng.get("engagement") is None)

    payload = pub.build_slice()
    check("ok", payload.get("ok") is True)
    check("payload staff_ready false", payload.get("staff_ready") is False)
    check("payload human_commissioned false", payload.get("human_commissioned") is False)
    check(
        "payload classification",
        payload.get("classification") == "HUMAN_COMMISSIONING",
    )
    check(
        "payload pack classification",
        payload.get("pack_classification") == "HUMAN_COMMISSIONING_OR_EXTERNAL",
    )
    check("payload invented_publish false", payload.get("invented_publish_success") is False)
    check("payload publish_success null", payload.get("publish_success") is None)
    check("payload engagement null", payload.get("engagement") is None)
    check("payload last_success null", payload.get("last_success") is None)
    check("payload metricool_write false", payload.get("metricool_write") is False)
    check("payload write disabled", payload.get("metricool_write_disabled") is True)
    check("payload real_external NO", payload.get("real_external_publish") == "NO")
    check("payload mw preserved", payload.get("metricool_runtime_wire1_preserved") is True)
    check("payload cel preserved", payload.get("content_engine_live1_preserved") is True)
    check("payload ggv preserved", payload.get("ggv_metric_honesty1_preserved") is True)
    check("payload cap not proven", payload.get("cap_ggv_publish_proven") is False)
    check("payload ceiling BUILT", payload.get("cap_ggv_publish_ceiling") == "BUILT")
    check(
        "payload next parent",
        payload.get("next_pack_for_parent_only") == "OCCUPANCY-EXTERNAL-HOLD-1",
    )
    check(
        "payload no auto-chain",
        payload.get("cursor_did_not_auto_start_next_pack") is True,
    )
    check("no invented helper", pub.no_invented_publish_success(payload) is True)
    check("surfaces honest helper", pub.surfaces_are_honest(payload) is True)

    steps = payload.get("path_steps") or []
    check("path steps == 4", len(steps) == 4, str(len(steps)))
    for s in steps:
        check(f"step {s.get('step')} DOCUMENTED", s.get("status") == "DOCUMENTED")
        check(f"step {s.get('step')} publish null", s.get("publish_success") is None)

    surfaces = {s.get("id"): s for s in (payload.get("surfaces") or [])}
    check("surface metricool_write", "metricool_write" in surfaces)
    check("surface publish_success", "publish_success" in surfaces)
    check("surface engagement", "engagement_values" in surfaces)
    check(
        "surface write NOT_RUNTIME",
        surfaces["metricool_write"].get("status") == "NOT_RUNTIME",
    )
    check(
        "surface pub NOT_RUNTIME",
        surfaces["publish_success"].get("status") == "NOT_RUNTIME",
    )

    tiles = {t.get("id") for t in (payload.get("honesty_tiles") or [])}
    for tid in (
        "classification",
        "metricool_write",
        "publish_success",
        "engagement_values",
        "invent_publish",
        "metricool_runtime_wire_1",
        "content_engine_live_1",
        "ggv_metric_honesty_1",
        "cap_ggv_publish",
    ):
        check(f"tile {tid}", tid in tiles)

    links = {l.get("id") for l in (payload.get("desk_links") or [])}
    check("link metricool", "metricool_runtime_wire_1" in links)
    check("link content engine", "content_engine_live_1" in links)
    check("link ggv metric", "ggv_metric_honesty_1" in links)

    schema = pub.schema_document()
    check("schema writes false", schema.get("writes_accepted") is False)
    check("schema invented publish false", schema.get("invented_publish_success") is False)
    check("schema publish_success null", schema.get("publish_success") is None)

    try:
        pub.build_slice("PERS-ZAYEN")
        check("zayen desk raised", False)
    except pub.ContentPublishPath1Error as exc:
        check("zayen desk forbidden", exc.code == "forbidden", f"got={exc.code}")


def test_preserved_packs() -> None:
    pin = pub.metricool_runtime_wire1_preserved()
    check("mw preserved ok", pin.get("ok") is True, str(pin))
    check("mw publish_success null", pin.get("publish_success") is None)
    check("mw engagement null", pin.get("engagement") is None)
    check("mw pub status NOT_RUNTIME", pin.get("publish_success_status") == "NOT_RUNTIME")
    check("mw eng status NOT_RUNTIME", pin.get("engagement_status") == "NOT_RUNTIME")

    board = mw.build_board()
    check("direct mw staff_ready false", board.get("staff_ready") is False)
    check("direct mw publish_success null", board.get("publish_success") is None)
    check("direct mw engagement null", board.get("engagement") is None)
    check("direct mw honest", mw.surfaces_are_honest(board) is True)

    cel_pin = pub.content_engine_live1_preserved()
    check("cel preserved ok", cel_pin.get("ok") is True, str(cel_pin))
    check("cel invented publish false", cel_pin.get("invented_publish_success") is False)

    cboard = cel.build_board()
    check("direct cel staff_ready false", cboard.get("staff_ready") is False)
    check("direct cel invented publish false", cboard.get("invented_publish_success") is False)

    ggv_pin = pub.ggv_metric_honesty1_preserved()
    check("ggv preserved ok", ggv_pin.get("ok") is True, str(ggv_pin))
    check("ggv fake_metrics false", ggv_pin.get("fake_metrics") is False)

    gflags = ggv.honesty_flags()
    check("direct ggv staff_ready false", gflags.get("staff_ready") is False)
    check("direct ggv metricool_not_runtime", gflags.get("metricool_not_runtime") is True)


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/ops/content-publish-path-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/ops/content-publish-path-1", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api classification", data.get("classification") == "HUMAN_COMMISSIONING")
        check("api invented_publish false", data.get("invented_publish_success") is False)
        check("api publish_success null", data.get("publish_success") is None)
        check("api engagement null", data.get("engagement") is None)
        check("api metricool_write false", data.get("metricool_write") is False)
        check("api mw preserved", data.get("metricool_runtime_wire1_preserved") is True)
        check("api cel preserved", data.get("content_engine_live1_preserved") is True)
        check("api ggv preserved", data.get("ggv_metric_honesty1_preserved") is True)
        check("api no invent helper", pub.no_invented_publish_success(data) is True)
        check("api surfaces honest", pub.surfaces_are_honest(data) is True)

        st, body = call(port, "GET", "/api/ops/content-publish-path-1", email=AMANDA)
        check("amanda api 200", st == 200, f"status={st}")
        adata = json.loads(body.decode())
        check("amanda api ok", adata.get("ok") is True)

        st, body = call(port, "GET", "/api/ops/content-publish-path-1", email=ZAYEN)
        check("zayen api 403", st == 403, f"status={st}")
        zdata = json.loads(body.decode())
        check("zayen api forbidden", zdata.get("error") == "forbidden")
        check("zayen api staff_ready false", zdata.get("staff_ready") is False)

        st, _ = call(port, "GET", "/ops/content-publish-path-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/ops/content-publish-path-1", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check(
            "page html publish",
            "publish" in text.lower() or "NOT_RUNTIME" in text,
        )
        check("page staff_ready pin", "staff_ready=false" in text)
        check("page human_commissioned pin", "human_commissioned=false" in text)
        check("page invent pin", "invent" in text.lower())
        check("page pack attr", 'data-pack="CONTENT-PUBLISH-PATH-1"' in text)
        check("page NOT_RUNTIME", "NOT_RUNTIME" in text)

        st, body = call(port, "GET", "/ops/content-publish-path-1", email=ZAYEN)
        check("zayen page deny", st == 403, f"status={st}")

        st, _ = call(port, "GET", "/content-publish-path-1", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")

        st, body = call(
            port,
            "POST",
            "/api/ops/content-publish-path-1",
            email=MATT,
            body={"publish_success": True},
        )
        check("post publish_success 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check(
            "post publish_success refused code",
            err.get("error") in ("fake_publish_refused", "invent_publish_refused"),
            f"got={err.get('error')}",
        )

        st, body = call(
            port,
            "POST",
            "/api/ops/content-publish-path-1",
            email=MATT,
            body={"metricool_write": True},
        )
        check("post metricool_write 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check(
            "post metricool_write refused",
            err.get("error") == "metricool_write_refused",
            f"got={err.get('error')}",
        )

        st, body = call(
            port,
            "POST",
            "/api/ops/content-publish-path-1",
            email=MATT,
            body={"engagement": 50},
        )
        check("post engagement 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post engagement refused code", err.get("error") == "engagement_refused")

        st, body = call(
            port,
            "POST",
            "/api/ops/content-publish-path-1",
            email=MATT,
            body={"proven": True},
        )
        check("post proven 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post proven refused code", err.get("error") == "proven_refused")

        st, body = call(port, "GET", "/api/ops/metricool-runtime-wire-1", email=MATT)
        check("metricool wire still 200", st == 200, f"status={st}")
        mdata = json.loads(body.decode())
        check("metricool wire still ok", mdata.get("ok") is True)
        check("metricool wire publish null", mdata.get("publish_success") is None)
        check("metricool wire engagement null", mdata.get("engagement") is None)

        st, body = call(port, "GET", "/api/ops/content-engine-live", email=MATT)
        check("content engine still 200", st == 200, f"status={st}")
        cdata = json.loads(body.decode())
        check("content engine still ok", cdata.get("ok") is True)
        check(
            "content engine invented publish false",
            cdata.get("invented_publish_success") is False,
        )
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


def _with_cdp(width: int, email: str | None, url: str, wait_expr: str, wait_seconds: float = 45.0):
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
                ident_id = seq
                _ws_send(sock, json.dumps({"id": ident_id, "method": method, "params": params or {}}))
                while True:
                    msg = json.loads(_ws_recv(sock))
                    if msg.get("id") == ident_id:
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
        desk_expr = (
            "(() => {"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const ps=document.body && document.body.getAttribute('data-publish-success');"
            " const wd=document.body && document.body.getAttribute('data-write-disabled');"
            " const wn=document.body && document.body.getAttribute('data-write-not-runtime');"
            " const ip=document.body && document.body.getAttribute('data-invented-publish');"
            " const mw=document.body && document.body.getAttribute('data-metricool-preserved');"
            " const cel=document.body && document.body.getAttribute('data-content-preserved');"
            " const ggv=document.body && document.body.getAttribute('data-ggv-preserved');"
            " const sr=document.body && document.body.getAttribute('data-staff-ready');"
            " const hc=document.body && document.body.getAttribute('data-human-commissioned');"
            " const cls=document.body && document.body.getAttribute('data-classification');"
            " const t=document.body ? document.body.innerText : '';"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const steps=(document.querySelectorAll('[data-step]')||[]).length;"
            " const surfaces=(document.querySelectorAll('[data-surface]')||[]).length;"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && ps==='null' && wd==='1' && wn==='1' && ip==='0'"
            "  && mw==='1' && cel==='1' && ggv==='1'"
            "  && sr==='0' && hc==='0' && cls==='HUMAN_COMMISSIONING'"
            "  && stamps>=4 && steps>=4 && surfaces>=3"
            "  && t.includes('NOT_RUNTIME') && ht.includes('staff_ready=false')"
            "  && ht.includes('human_commissioned=false')"
            "  && (t.toLowerCase().includes('publish') || t.includes('DISABLED')),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, steps:steps,"
            " surfaces:surfaces, ready:ready, ps:ps, wd:wd, mw:mw, cel:cel, ggv:ggv,"
            " ip:ip, cls:cls};"
            "})()"
        )
        for width, name in (
            (1024, "contentpublish1-desk-desktop.png"),
            (390, "contentpublish1-desk-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width,
                MATT,
                f"http://127.0.0.1:{port}/ops/content-publish-path-1",
                desk_expr,
            ):
                check(f"desk ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"publish null {name}", value.get("ps") == "null")
                    check(f"write disabled {name}", value.get("wd") == "1")
                    check(f"mw preserved {name}", value.get("mw") == "1")
                    check(f"invented publish false {name}", value.get("ip") == "0")
                    check(f"steps visible {name}", (value.get("steps") or 0) >= 4)
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/ops/content-publish-path-1",
            desk_expr,
        ):
            check("write-disabled shot ready", bool(value and value.get("ok")), str(value)[:200])
            if value:
                check("write-disabled attr", value.get("wd") == "1")
                check("write-disabled classification", value.get("cls") == "HUMAN_COMMISSIONING")
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "contentpublish1-write-disabled.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot write-disabled", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/ops/content-publish-path-1",
            desk_expr,
        ):
            check("metricool preserved shot ready", bool(value and value.get("ok")), str(value)[:200])
            if value:
                check("metricool preserved attr", value.get("mw") == "1")
                check("content preserved attr", value.get("cel") == "1")
                check("ggv preserved attr", value.get("ggv") == "1")
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "contentpublish1-metricool-preserved.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot metricool-preserved", dest.is_file() and dest.stat().st_size > 3000)

        deny_expr = (
            "(() => {"
            " const t=document.body ? document.body.innerText : '';"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const deny=document.body && document.body.getAttribute('data-deny');"
            " const statusHint=/403|forbidden|sign.?in|unauthor|denied|identity|Owner/i.test(t);"
            " const notLoaded=ready!=='1';"
            " return {ok: statusHint || notLoaded || deny==='403',"
            " text:t.slice(0,400), ready:ready, deny:deny, statusHint:statusHint};"
            "})()"
        )
        for cdp, _ev, value in _with_cdp(
            1024,
            None,
            f"http://127.0.0.1:{port}/ops/content-publish-path-1",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "contentpublish1-unsigned-deny.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot unsigned-deny", dest.is_file() and dest.stat().st_size > 800)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_artifacts_and_prod_ro() -> None:
    check("page html present", HTML.is_file())
    html = HTML.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html pack attr", 'data-pack="CONTENT-PUBLISH-PATH-1"' in html)
    check("html invent", "invent" in html.lower())
    check("html NOT_RUNTIME", "NOT_RUNTIME" in html)
    check("html METRICOOL preserved", "METRICOOL-RUNTIME-WIRE-1" in html)
    check("html CONTENT preserved", "CONTENT-ENGINE-LIVE-1" in html)
    check("html GGV preserved", "GGV-METRIC-HONESTY-1" in html)

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "CONTENT-PUBLISH-PATH-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "OCCUPANCY-EXTERNAL-HOLD-1"
        or arm.get("next_pack_for_parent_only") == "OCCUPANCY-EXTERNAL-HOLD-1",
    )

    for name in (
        "contentpublish1-desk-desktop.png",
        "contentpublish1-desk-phone.png",
        "contentpublish1-write-disabled.png",
        "contentpublish1-metricool-preserved.png",
        "contentpublish1-unsigned-deny.png",
    ):
        p = SHOTS / name
        check(f"artifact {name}", p.is_file() and p.stat().st_size > 800)

    result = ROOT / "docs" / "wolf" / "ops" / "CONTENT-PUBLISH-PATH-1-RESULT.md"
    check("result md present", result.is_file())
    if result.is_file():
        rtext = result.read_text(encoding="utf-8")
        check("result EXIT:0", "EXIT:0" in rtext)
        check("result no auto-chain", "OCCUPANCY-EXTERNAL-HOLD-1" in rtext)
        check(
            "result classification",
            "HUMAN_COMMISSIONING" in rtext or "NOT_RUNTIME" in rtext,
        )

    check("prod pid constant", pub.PROD_PID_HELD == PROD_PID)
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{PROD_PORT}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        out = ""
    check("prod still listening", str(PROD_PID) in out or "LISTEN" in out, out[:120])
    try:
        os.kill(PROD_PID, 0)
        alive = True
    except (OSError, ProcessLookupError):
        alive = False
    check("prod pid 15975 alive untouched", alive is True)

    names = [
        "contentpublish1-desk-desktop.png",
        "contentpublish1-desk-phone.png",
        "contentpublish1-write-disabled.png",
        "contentpublish1-metricool-preserved.png",
        "contentpublish1-unsigned-deny.png",
    ]
    hashes = []
    for name in names:
        path = SHOTS / name
        check(f"shot file {name}", path.is_file() and path.stat().st_size > 800)
        if path.is_file():
            hashes.append(path.read_bytes()[:64])
    if len(hashes) == 5:
        check("shots not identical prefixes", len(set(hashes)) >= 2)


def main() -> int:
    print("=== CONTENT-PUBLISH-PATH-1 suite ===")
    test_module_and_honesty()
    test_desk_payload()
    test_preserved_packs()
    test_http_api_and_page()
    test_shots()
    test_artifacts_and_prod_ro()
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
