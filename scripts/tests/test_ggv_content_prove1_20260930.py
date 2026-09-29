#!/usr/bin/env python3
"""GGV-CONTENT-PROVE-1 — GGV Content Machine prove/harden (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack GGV-CONTENT-PROVE-1
(armed 2026-09-30) — CAP-GGV-01 / IL-R6 content / MB-006 prove+harden.

No fake engagement/publish/success metrics. INT-MET-WOLF NOT_RUNTIME.
staff_ready=false · human_commissioned=false. Extends existing Content path.
Prod :8787 pid 15975 untouched. Does not auto-chain CRM-IDENTITY-1 /
HEADCHEF / Exit Report.
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
from core import ggv_content_ops_depth as ops_depth  # noqa: E402
from core import ggv_content_prove1 as prove  # noqa: E402
from core import ggv_ops_pack as ops  # noqa: E402
from core import ggv_social_derive as social  # noqa: E402
from core import ggv_strategy_machine as strategy  # noqa: E402
from core import intg_truth_board as board  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "GGV-CONTENT-PROVE-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
HTML = ROOT / "dashboards" / "ggv-content-prove.html"
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


def call(port: int, method: str, path: str, email: str | None = None):
    headers = {"Accept": "application/json"}
    if email:
        headers["X-Wolf-Subject"] = email
        headers["Cf-Access-Authenticated-User-Email"] = email
    req = Request(f"http://127.0.0.1:{port}{path}", headers=headers, method=method)
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


def test_prove_payload() -> None:
    check("html present", HTML.is_file())
    check("api matcher", prove.api_matches("/api/ggv/content-prove"))
    check("page matcher", prove.page_matches("/ggv/content-prove"))
    check("page matcher alias", prove.page_matches("/ggv-content-prove"))
    payload = prove.build_prove()
    check("ok", payload.get("ok") is True)
    check("pack", payload.get("pack") == "GGV-CONTENT-PROVE-1")
    check("staff_ready false", payload.get("staff_ready") is False)
    check("human_commissioned false", payload.get("human_commissioned") is False)
    check("live_adoption false", payload.get("live_adoption") is False)
    check("fake_metrics false", payload.get("fake_metrics") is False)
    check("invented_engagement false", payload.get("invented_engagement") is False)
    check(
        "invented_publish_success false",
        payload.get("invented_publish_success") is False,
    )
    check(
        "invented_metricool_success false",
        payload.get("invented_metricool_success") is False,
    )
    check("metricool_publish false", payload.get("metricool_publish") is False)
    check("cap_ggv_01 not proven", payload.get("cap_ggv_01_proven") is False)
    check("cap_ggv_01 ceiling BUILT", payload.get("cap_ggv_01_ceiling") == "BUILT")
    check("second system false", payload["honesty"].get("second_content_system") is False)
    check("extends existing", payload["honesty"].get("extends_existing_path") is True)
    check("all publish tiles honest", prove.all_publish_tiles_honest(payload) is True)
    check("metricool not runtime helper", prove.metricool_not_runtime(payload) is True)

    tiles = payload.get("publish_honesty_tiles") or []
    needed = {"metricool_runtime", "publish_success", "live_adoption"}
    got = {t.get("id") for t in tiles}
    check("publish tile set", needed.issubset(got), str(got))
    for t in tiles:
        tid = t.get("id")
        check(f"{tid} value null", t.get("value") is None)
        check(f"{tid} count null", t.get("count") is None)
        check(f"{tid} engagement null", t.get("engagement") is None)
        check(f"{tid} publish_success null", t.get("publish_success") is None)
        check(f"{tid} fake_metrics false", t.get("fake_metrics") is False)
        check(
            f"{tid} honest display",
            t.get("display") in ("NOT_RUNTIME", "UNKNOWN", "NOT_LIVE"),
            str(t.get("display")),
        )

    met = payload.get("metricool") or {}
    check("metricool probe NOT_RUNTIME", met.get("probe_status") == "NOT_RUNTIME")
    check("metricool last_success null", met.get("last_success") is None)
    check("metricool not_runtime", met.get("not_runtime") is True)
    check("metricool board link", met.get("honesty_board_href") == "/ops/integrations-status")

    links = {l.get("id"): l for l in (payload.get("desk_links") or [])}
    for lid in (
        "content_desk",
        "content_ops_depth",
        "strategy_machine",
        "ops_pack",
        "social_derive",
        "integrations_honesty",
    ):
        check(f"desk link {lid}", lid in links, str(list(links)))
    check("content desk href", (links.get("content_desk") or {}).get("href") == "/content-2.0")
    check(
        "honesty board href",
        (links.get("integrations_honesty") or {}).get("href") == "/ops/integrations-status",
    )

    eng = payload.get("engagement_scaffold") or {}
    check("engagement empty", eng.get("empty") is True)
    check("live_engagement false", eng.get("live_engagement") is False)
    check("engagement revenue null", eng.get("revenue") is None)

    # Align with INTG board
    b = board.build_board(persist_audit=False)
    met_b = next(c for c in b["connectors"] if c["integration_id"] == "INT-MET-WOLF")
    check("intg board met probe NOT_RUNTIME", met_b.get("probe_status") == "NOT_RUNTIME")
    check("intg board met last_success null", met_b.get("last_success") is None)

    # Prior path honesty still honest
    od = ops_depth.honesty_flags()
    check("ops_depth staff_ready false", od.get("staff_ready") is False)
    check("ops_depth metricool_publish false", od.get("metricool_publish") is False)
    check("ops_depth invented metrics false", od.get("invented_metricool_metrics") is False)
    st = strategy.honesty_flags()
    check("strategy not live", st.get("live_strategy_machine") is False)
    check("strategy not invent proven", st.get("invented_proven") is False)
    so = social.honesty_flags()
    check("social metricool_called false", so.get("metricool_called") is False)
    check("social metricool_write false", so.get("metricool_write") is False)
    op = ops.honesty_flags()
    check("ops_pack staff_ready false", op.get("staff_ready") is False)
    check("ops_pack metricool_publish false", op.get("metricool_publish") is False)

    prior = payload.get("prior_path_honesty") or {}
    check(
        "prior publish DISABLED",
        (prior.get("publish_gate") or {}).get("metricool_write_status") == "DISABLED",
    )

    html = HTML.read_text(encoding="utf-8")
    check("html NOT_RUNTIME", "NOT_RUNTIME" in html)
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html live_adoption=false", "live_adoption=false" in html)
    check("html fake_metrics=false", "fake_metrics=false" in html)
    check("html honesty board link", "/ops/integrations-status" in html)
    check("html no invent success count", "engagement_count" not in html)


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        st, body = call(port, "GET", "/api/ggv/content-prove")
        check("unsigned api 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/api/ggv/content-prove", email=MATT)
        check("signed api 200", st == 200, f"status={st}")
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api live_adoption false", data.get("live_adoption") is False)
        check("api fake_metrics false", data.get("fake_metrics") is False)
        check("api tiles honest", prove.all_publish_tiles_honest(data) is True)
        check("api metricool not runtime", prove.metricool_not_runtime(data) is True)
        runtime = next(t for t in data["publish_honesty_tiles"] if t["id"] == "metricool_runtime")
        check("api runtime NOT_RUNTIME", runtime.get("display") == "NOT_RUNTIME")
        check("api runtime no count", runtime.get("count") is None and runtime.get("value") is None)

        st, body = call(port, "GET", "/ggv/content-prove")
        check("unsigned page 403", st == 403, f"status={st}")

        st, body = call(port, "GET", "/ggv/content-prove", email=MATT)
        check("signed page 200", st == 200, f"status={st}")
        text = body.decode(errors="replace")
        check(
            "page html prove",
            "GGV Content Machine prove" in text or "ggv-content-prove" in text.lower(),
        )
        check("page has NOT_RUNTIME", "NOT_RUNTIME" in text)

        st, _ = call(port, "GET", "/ggv-content-prove", email=MATT)
        check("alias page reachable", st in (200, 302), f"status={st}")
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
        shell_expr = (
            "(() => {"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const nr=document.body && document.body.getAttribute('data-metricool-not-runtime');"
            " const fake=document.body && document.body.getAttribute('data-fake-metrics');"
            " const live=document.body && document.body.getAttribute('data-live-adoption');"
            " const t=document.body ? document.body.innerText : '';"
            " const stamps=(document.querySelectorAll('.stamp')||[]).length;"
            " const runtime=document.querySelector('[data-tile=\"metricool_runtime\"]');"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " return {ok: ready==='1' && nr==='1' && fake==='0' && live==='0'"
            "  && stamps>=3 && !!runtime"
            "  && t.includes('NOT_RUNTIME') && t.includes('UNKNOWN')"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && t.includes('Integrations honesty board'),"
            " text:t.slice(0,500), honesty:ht, stamps:stamps, ready:ready, nr:nr};"
            "})()"
        )
        for width, name in (
            (1024, "ggvcontentprove1-desk-desktop.png"),
            (390, "ggvcontentprove1-desk-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/ggv/content-prove", shell_expr
            ):
                check(f"desk ready {name}", bool(value and value.get("ok")), str(value)[:240])
                if value:
                    check(f"metricool nr attr {name}", value.get("nr") == "1")
                    check(f"stamps visible {name}", (value.get("stamps") or 0) >= 3)
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/ggv/content-prove",
            shell_expr,
        ):
            check("metricool stamps shot ready", bool(value and value.get("ok")), str(value)[:200])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "ggvcontentprove1-metricool-not-runtime.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot metricool-not-runtime", dest.is_file() and dest.stat().st_size > 3000)

        deny_expr = (
            "(() => {"
            " const t=document.body ? document.body.innerText : '';"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const deny=document.body && document.body.getAttribute('data-deny');"
            " const statusHint=/403|forbidden|sign.?in|unauthor|denied|identity/i.test(t);"
            " const notLoaded=ready!=='1';"
            " return {ok: statusHint || notLoaded || deny==='403',"
            " text:t.slice(0,400), ready:ready, deny:deny, statusHint:statusHint};"
            "})()"
        )
        for cdp, _ev, value in _with_cdp(
            1024,
            None,
            f"http://127.0.0.1:{port}/ggv/content-prove",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "ggvcontentprove1-unsigned-deny.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot unsigned-deny", dest.is_file() and dest.stat().st_size > 800)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_arm_flags() -> None:
    if ARM.is_file():
        arm = json.loads(ARM.read_text(encoding="utf-8"))
        check("arm staff_ready false", arm.get("staff_ready") is False)
        check("arm human_commissioned false", arm.get("human_commissioned") is False)
        check("arm no_push", arm.get("no_push") is True)
        check("arm prod_mutate false", arm.get("prod_mutate") is False)
    else:
        check("arm present", False, "missing")


def test_prod_pid_untouched() -> None:
    out = subprocess.check_output(
        ["lsof", "-nP", f"-iTCP:{PROD_PORT}", "-sTCP:LISTEN"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    check("prod pid still 15975", str(PROD_PID) in out and f":{PROD_PORT}" in out, out[:200])


def main() -> int:
    test_prove_payload()
    test_http_api_and_page()
    test_shots()
    test_arm_flags()
    test_prod_pid_untouched()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("RESULT: PASS" if FAIL == 0 else f"RESULT: FAIL {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
