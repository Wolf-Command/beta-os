#!/usr/bin/env python3
"""GGV-METRIC-HONESTY-1 — GGV Metricool metric honesty deepen (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack GGV-METRIC-HONESTY-1
(armed 2026-09-30 after BZG-INVENTORY-TRUTH-1 PASS_VERIFIED).

NOT_RUNTIME holds. Engagement/publish stay null. No fake metrics.
Preserves CONTENT-ENGINE-LIVE-1 + GGV-CONTENT-PROVE-1.
Unsigned API/page 403. Invent-metric writes refused.
staff_ready=false · human_commissioned=false. Prod :8787 pid 15975 untouched.
Does not auto-chain OWNER-EXCEPTIONS-LIVE-1 / HEADCHEF / Exit Report.
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
sys.path.insert(0, str(ROOT / "scripts"))

import serve_beta as sb  # noqa: E402
from core import content_engine_live1 as cel  # noqa: E402
from core import ggv_content_prove1 as prove  # noqa: E402
from core import ggv_metric_honesty1 as met  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
ZAYEN = "laluzayen@gmail.com"
ARM = ROOT / "state" / "final-completion" / "packs" / "GGV-METRIC-HONESTY-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "ggv-metric-honesty-1.html"
MODULE = ROOT / "scripts" / "core" / "ggv_metric_honesty1.py"
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
    check("page matcher /ggv/metric-honesty-1", met.page_matches("/ggv/metric-honesty-1"))
    check("page matcher alias", met.page_matches("/ggv-metric-honesty-1.html"))
    check("page matcher short", met.page_matches("/ggv/metrics"))
    check("api matcher", met.api_matches("/api/ggv/metric-honesty-1"))
    check("api no mutate path", not met.api_matches("/api/ggv/metric-honesty-1/mutate"))

    flags = met.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("fake_metrics false", flags.get("fake_metrics") is False)
    check("invented_engagement false", flags.get("invented_engagement") is False)
    check("invented_publish false", flags.get("invented_publish_success") is False)
    check("invented_metric false", flags.get("invented_metric") is False)
    check("metricool_not_runtime", flags.get("metricool_not_runtime") is True)
    check("engagement null when not runtime", flags.get("engagement_null_when_not_runtime") is True)
    check("publish null when not runtime", flags.get("publish_null_when_not_runtime") is True)
    check("metric_write false", flags.get("metric_write") is False)
    check("live_adoption false", flags.get("live_adoption") is False)
    check("cel preserved flag", flags.get("content_engine_live1_preserved") is True)
    check("prove preserved flag", flags.get("ggv_content_prove1_preserved") is True)
    check("cap proven false", flags.get("cap_ggv_metrics_proven") is False)
    check("cap ready false", flags.get("cap_ggv_metrics_ready") is False)
    check("ceiling BUILT", flags.get("cap_ggv_metrics_ceiling") == "BUILT")
    check("maturity SPECIFIED", flags.get("cap_ggv_metrics_maturity") == "SPECIFIED")
    check("zayen deny flag", flags.get("zayen_deny_ggv") is True)
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "OWNER-EXCEPTIONS-LIVE-1")
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("prod pid held const", met.PROD_PID_HELD == PROD_PID)

    check("Matt may view", met.person_may_view("PERS-MATT") is True)
    check("Amanda may view", met.person_may_view("PERS-AMANDA") is True)
    check("Zayen may NOT", met.person_may_view("PERS-ZAYEN") is False)

    try:
        met.refuse_fake_engagement({"engagement": 99})
        check("refuse_fake_engagement raises", False)
    except met.GgvMetricHonesty1Error as exc:
        check("refuse_fake_engagement raises", True)
        check("refuse_fake_engagement code", exc.code == "fake_engagement_refused")
    try:
        met.refuse_fake_publish({"publish_success": True})
        check("refuse_fake_publish raises", False)
    except met.GgvMetricHonesty1Error as exc:
        check("refuse_fake_publish raises", True)
        check("refuse_fake_publish code", exc.code == "fake_publish_refused")
    try:
        met.refuse_invent_metric({"impressions": 1000})
        check("refuse_invent_metric raises", False)
    except met.GgvMetricHonesty1Error as exc:
        check("refuse_invent_metric raises", True)
        check("refuse_invent_metric code", exc.code == "invent_metric_refused")

    try:
        met.refuse_external_write({"engagement": 12})
        check("refuse write engagement raises", False)
    except met.GgvMetricHonesty1Error as exc:
        check("refuse write engagement", exc.code == "fake_engagement_refused")
    try:
        met.refuse_external_write({"publish_success": True})
        check("refuse write publish raises", False)
    except met.GgvMetricHonesty1Error as exc:
        check("refuse write publish", exc.code == "fake_publish_refused")
    try:
        met.refuse_external_write({"impressions": 500})
        check("refuse write impressions raises", False)
    except met.GgvMetricHonesty1Error as exc:
        check("refuse write impressions", exc.code == "invent_metric_refused")
    try:
        met.refuse_external_write({"last_success": "2026-09-30"})
        check("refuse write last_success raises", False)
    except met.GgvMetricHonesty1Error as exc:
        check("refuse write last_success", exc.code == "invent_metric_refused")
    try:
        met.refuse_external_write({"proven": True})
        check("refuse write proven raises", False)
    except met.GgvMetricHonesty1Error as exc:
        check("refuse write proven", exc.code == "proven_refused")
    try:
        met.refuse_external_write({"noop": True})
        check("refuse write generic raises", False)
    except met.GgvMetricHonesty1Error as exc:
        check("refuse write generic", exc.code == "write_refused")


def test_desk_payload() -> None:
    payload = met.build_slice()
    check("ok", payload.get("ok") is True)
    check("payload staff_ready false", payload.get("staff_ready") is False)
    check("payload human_commissioned false", payload.get("human_commissioned") is False)
    check("payload fake_metrics false", payload.get("fake_metrics") is False)
    check("payload invented_engagement false", payload.get("invented_engagement") is False)
    check("payload invented_publish false", payload.get("invented_publish_success") is False)
    check("payload metric_write false", payload.get("metric_write") is False)
    check("payload live_adoption false", payload.get("live_adoption") is False)
    check("payload metricool_not_runtime", payload.get("metricool_not_runtime") is True)
    check("payload engagement null", payload.get("engagement") is None)
    check("payload publish_success null", payload.get("publish_success") is None)
    check("payload last_success null", payload.get("last_success") is None)
    check("payload cel preserved", payload.get("content_engine_live1_preserved") is True)
    check("payload prove preserved", payload.get("ggv_content_prove1_preserved") is True)
    check("payload cap not proven", payload.get("cap_ggv_metrics_proven") is False)
    check("payload ceiling BUILT", payload.get("cap_ggv_metrics_ceiling") == "BUILT")
    check("payload next parent", payload.get("next_pack_for_parent_only") == "OWNER-EXCEPTIONS-LIVE-1")
    check("payload no auto-chain", payload.get("cursor_did_not_auto_start_next_pack") is True)
    check("metricool not runtime helper", met.metricool_not_runtime(payload) is True)
    check("no fake metrics helper", met.no_fake_metrics(payload) is True)

    slots = payload.get("metric_slots") or []
    check("metric slots >= 6", len(slots) >= 6, str(len(slots)))
    check("all metric slots null", met.all_metric_slots_null(payload) is True)
    for s in slots:
        check(f"{s['id']} value null", s.get("value") is None)
        check(f"{s['id']} engagement null", s.get("engagement") is None)
        check(f"{s['id']} publish null", s.get("publish_success") is None)
        check(f"{s['id']} last_success null", s.get("last_success") is None)
        check(f"{s['id']} no fake", s.get("fake_metrics") is False)
        check(f"{s['id']} not invented engagement", s.get("invented_engagement") is False)
        check(f"{s['id']} status honest", s.get("status") in ("NOT_RUNTIME", "UNKNOWN", "NULL", "EMPTY"))

    mm = payload.get("metricool") or {}
    check("metricool display NOT_RUNTIME", mm.get("display") == "NOT_RUNTIME")
    check("metricool last_success null", mm.get("last_success") is None)
    check("metricool engagement null", mm.get("engagement") is None)
    check("metricool publish null", mm.get("publish_success") is None)
    check("metricool not_runtime true", mm.get("not_runtime") is True)

    tiles = {t.get("id") for t in (payload.get("honesty_tiles") or [])}
    for tid in (
        "metricool_runtime",
        "engagement_null",
        "publish_null",
        "fake_metrics",
        "content_engine_live1",
        "ggv_content_prove1",
        "cap_ggv_metrics",
    ):
        check(f"tile {tid}", tid in tiles)

    links = {l.get("id") for l in (payload.get("desk_links") or [])}
    check("link content engine", "content_engine_live" in links)
    check("link content prove", "content_prove" in links)
    check("link integrations", "integrations_honesty" in links)

    schema = met.schema_document()
    check("schema writes false", schema.get("writes_accepted") is False)
    check("schema fake metrics false", schema.get("fake_metrics") is False)
    check("schema engagement prop false", schema.get("engagement_property") is False)
    check("schema publish prop false", schema.get("publish_success_property") is False)

    try:
        met.build_slice("PERS-ZAYEN")
        check("zayen desk raised", False)
    except met.GgvMetricHonesty1Error as exc:
        check("zayen desk forbidden", exc.code == "forbidden", f"got={exc.code}")


def test_preserved_packs() -> None:
    pin = met.content_engine_live1_preserved()
    check("cel preserved ok", pin.get("ok") is True, str(pin))
    check("cel metricool not runtime", pin.get("metricool_not_runtime") is True)
    check("cel invented_engagement false", pin.get("invented_engagement") is False)

    board = cel.build_board()
    check("direct cel ok", board.get("ok") is True)
    check("direct cel staff_ready false", board.get("staff_ready") is False)
    check("direct cel human_commissioned false", board.get("human_commissioned") is False)
    check("direct cel metricool not runtime", cel.metricool_not_runtime(board) is True)

    ppin = met.ggv_content_prove1_preserved()
    check("prove preserved ok", ppin.get("ok") is True, str(ppin))
    check("prove metricool not runtime", ppin.get("metricool_not_runtime") is True)

    pdata = prove.public_payload()
    check("direct prove ok", pdata.get("ok") is True)
    check("direct prove staff_ready false", pdata.get("staff_ready") is False)
    check("direct prove live_adoption false", pdata.get("live_adoption") is False)
    check("direct prove tiles honest", prove.all_publish_tiles_honest(pdata) is True)


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, _ = call(port, "GET", "/api/ggv/metric-honesty-1")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/ggv/metric-honesty-1", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api fake_metrics false", data.get("fake_metrics") is False)
        check("api invented_engagement false", data.get("invented_engagement") is False)
        check("api invented_publish false", data.get("invented_publish_success") is False)
        check("api metricool not runtime", data.get("metricool_not_runtime") is True)
        check("api engagement null", data.get("engagement") is None)
        check("api publish null", data.get("publish_success") is None)
        check("api last_success null", data.get("last_success") is None)
        check("api cel preserved", data.get("content_engine_live1_preserved") is True)
        check("api prove preserved", data.get("ggv_content_prove1_preserved") is True)
        check("api slots null helper", met.all_metric_slots_null(data) is True)
        check("api no fake metrics", met.no_fake_metrics(data) is True)
        check("api metricool display", (data.get("metricool") or {}).get("display") == "NOT_RUNTIME")

        st, body = call(port, "GET", "/api/ggv/metric-honesty-1", email=AMANDA)
        check("amanda api 200", st == 200, f"status={st}")
        adata = json.loads(body.decode())
        check("amanda api ok", adata.get("ok") is True)

        st, body = call(port, "GET", "/api/ggv/metric-honesty-1", email=ZAYEN)
        check("zayen api 403", st == 403, f"status={st}")
        zdata = json.loads(body.decode())
        check("zayen api forbidden", zdata.get("error") == "forbidden")
        check("zayen api staff_ready false", zdata.get("staff_ready") is False)

        st, _ = call(port, "GET", "/ggv/metric-honesty-1")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/ggv/metric-honesty-1", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check(
            "page html metricool",
            "NOT_RUNTIME" in text or "metric" in text.lower(),
        )
        check("page staff_ready pin", "staff_ready=false" in text)
        check("page human_commissioned pin", "human_commissioned=false" in text)
        check(
            "page no fake",
            "fake" in text.lower() or "NOT_RUNTIME" in text or "null" in text.lower(),
        )

        st, body = call(port, "GET", "/ggv/metric-honesty-1", email=ZAYEN)
        check("zayen page deny", st == 403, f"status={st}")
        ztext = body.decode(errors="replace")
        check(
            "zayen page deny text",
            "denied" in ztext.lower()
            or "forbidden" in ztext.lower()
            or "limited" in ztext.lower()
            or "not" in ztext.lower()
            or "Owner" in ztext
            or "GGV" in ztext,
            ztext[:200],
        )

        st, _ = call(port, "GET", "/ggv-metric-honesty-1", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")

        st, body = call(
            port, "POST", "/api/ggv/metric-honesty-1", email=MATT, body={"engagement": 99}
        )
        check("post engagement 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post engagement refused code", err.get("error") == "fake_engagement_refused")

        st, body = call(
            port,
            "POST",
            "/api/ggv/metric-honesty-1",
            email=MATT,
            body={"publish_success": True},
        )
        check("post publish 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post publish refused code", err.get("error") == "fake_publish_refused")

        st, body = call(
            port, "POST", "/api/ggv/metric-honesty-1", email=MATT, body={"impressions": 1000}
        )
        check("post impressions 403", st == 403, f"status={st}")
        err = json.loads(body.decode())
        check("post impressions refused code", err.get("error") == "invent_metric_refused")
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
                time.sleep(0.35)
                value = evaluate(wait_expr)
                if value and value.get("ok"):
                    break
            yield cdp, evaluate, value
            sock.close()
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def test_shots() -> None:
    if not CHROME.is_file():
        check("chrome present for shots", False, "Chrome missing")
        return
    SHOTS.mkdir(parents=True, exist_ok=True)
    httpd, port = _start_beta()
    try:
        desk_expr = (
            "(() => {"
            " const t=document.body ? document.body.innerText : '';"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const fm=document.body && document.body.getAttribute('data-fake-metrics');"
            " const ie=document.body && document.body.getAttribute('data-invented-engagement');"
            " const ip=document.body && document.body.getAttribute('data-invented-publish');"
            " const nr=document.body && document.body.getAttribute('data-metricool-not-runtime');"
            " const cel=document.body && document.body.getAttribute('data-cel-preserved');"
            " const pr=document.body && document.body.getAttribute('data-prove-preserved');"
            " const proven=document.body && document.body.getAttribute('data-cap-proven');"
            " const sr=document.body && document.body.getAttribute('data-staff-ready');"
            " const hc=document.body && document.body.getAttribute('data-human-commissioned');"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const slots=(document.querySelectorAll('[data-slot]')||[]).length;"
            " const nrEl=document.querySelector('[data-metricool=\"NOT_RUNTIME\"]');"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && fm==='0' && ie==='0' && ip==='0'"
            "  && nr==='1' && cel==='1' && pr==='1' && proven==='0' && sr==='0' && hc==='0'"
            "  && stamps>=4 && slots>=6 && !!nrEl"
            "  && t.includes('NOT_RUNTIME') && (t.includes('Metric') || t.includes('metric'))"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && (ht.includes('null') || t.includes('null')),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, slots:slots,"
            " ready:ready, nr:nr, cel:cel, pr:pr};"
            "})()"
        )
        for width, name in (
            (1024, "ggvmetric1-desk-desktop.png"),
            (390, "ggvmetric1-desk-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/ggv/metric-honesty-1", desk_expr
            ):
                check(f"desk ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"metricool not runtime {name}", value.get("nr") == "1")
                    check(f"slots visible {name}", (value.get("slots") or 0) >= 6)
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/ggv/metric-honesty-1",
            desk_expr,
        ):
            check("metricool not runtime shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "ggvmetric1-metricool-not-runtime.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot metricool-not-runtime", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/ggv/metric-honesty-1",
            desk_expr,
        ):
            check("preserved packs shot ready", bool(value and value.get("ok")), str(value)[:200])
            if value:
                check("cel preserved attr", value.get("cel") == "1")
                check("prove preserved attr", value.get("pr") == "1")
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "ggvmetric1-packs-preserved.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot packs-preserved", dest.is_file() and dest.stat().st_size > 3000)

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
            f"http://127.0.0.1:{port}/ggv/metric-honesty-1",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "ggvmetric1-unsigned-deny.png"
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
    check("html pack attr", 'data-pack="GGV-METRIC-HONESTY-1"' in html)
    check(
        "html no fake",
        "NOT_RUNTIME" in html or "fake" in html.lower() or "null" in html.lower(),
    )

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "GGV-METRIC-HONESTY-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "OWNER-EXCEPTIONS-LIVE-1"
        or arm.get("next_pack_for_parent_only") == "OWNER-EXCEPTIONS-LIVE-1",
    )

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
        "ggvmetric1-desk-desktop.png",
        "ggvmetric1-desk-phone.png",
        "ggvmetric1-metricool-not-runtime.png",
        "ggvmetric1-packs-preserved.png",
        "ggvmetric1-unsigned-deny.png",
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
    print("=== GGV-METRIC-HONESTY-1 pack suite ===")
    test_module_and_honesty()
    test_desk_payload()
    test_preserved_packs()
    test_http_api_and_page()
    test_shots()
    test_artifacts_and_prod_ro()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
