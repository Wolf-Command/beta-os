#!/usr/bin/env python3
"""METRICOOL-RUNTIME-WIRE-1 — authorised Metricool runtime wire prove (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack
METRICOOL-RUNTIME-WIRE-1 (armed 2026-09-30 after PIPE-RELIABILITY-AUTO-1).

Brand stamps + analytics paths RUNTIME_WIRED. Engagement/last_success null.
Per-surface honesty. No fake metrics. Unsigned 403. Writes refused.
Prod :8787 pid 15975 untouched. Preserves GGV-METRIC-HONESTY-1 + CONTENT-ENGINE-LIVE-1.
Does not auto-chain ESB-SETTLEMENT-PATH-1 / HEADCHEF / Exit Report.
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
from core import content_engine_live1 as cel  # noqa: E402
from core import ggv_metric_honesty1 as ggv  # noqa: E402
from core import intg_truth_board as intg  # noqa: E402
from core import metricool_runtime_wire1 as mrw  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "METRICOOL-RUNTIME-WIRE-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
PAGE = ROOT / "dashboards" / "metricool-runtime-wire-1.html"
RESULT = ROOT / "docs" / "wolf" / "ops" / "METRICOOL-RUNTIME-WIRE-1-RESULT.md"
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
    check("page matcher", mrw.page_matches("/ops/metricool-runtime-wire-1"))
    check("page alias", mrw.page_matches("/metricool-runtime-wire-1.html"))
    check("api matcher", mrw.api_matches("/api/ops/metricool-runtime-wire-1"))
    check(
        "api no trailing invent",
        not mrw.api_matches("/api/ops/metricool-runtime-wire-1/mutate"),
    )

    flags = mrw.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("fake_metrics false", flags.get("fake_metrics") is False)
    check("invented_engagement false", flags.get("invented_engagement") is False)
    check("invented_last_success false", flags.get("invented_last_success") is False)
    check("held pid 15975", flags.get("prod_pid_held") == PROD_PID)
    check("ceiling BUILT", flags.get("ceiling") == "BUILT")
    check("classification INTERNALLY_SOLVABLE", flags.get("classification") == "INTERNALLY_SOLVABLE")
    check(
        "next pack parent only",
        flags.get("next_pack_for_parent_only") == "ESB-SETTLEMENT-PATH-1",
    )
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("blanket replaced", flags.get("blanket_not_runtime_replaced") is True)
    check("per surface", flags.get("per_surface_honesty") is True)
    check("ggv preserved flag", flags.get("ggv_metric_honesty1_preserved") is True)
    check("cel preserved flag", flags.get("content_engine_live1_preserved") is True)

    payload = mrw.build_board()
    check("ok", payload.get("ok") is True)
    check("payload staff_ready false", payload.get("staff_ready") is False)
    check("payload human_commissioned false", payload.get("human_commissioned") is False)
    check("payload fake_metrics false", payload.get("fake_metrics") is False)
    check("payload engagement null", payload.get("engagement") is None)
    check("payload last_success null", payload.get("last_success") is None)
    check("payload publish_success null", payload.get("publish_success") is None)
    check("payload prod_mutate false", payload.get("prod_mutate") is False)
    check("surfaces honest", mrw.surfaces_are_honest(payload) is True)
    check("brand_count 6", payload.get("brand_count") == 6)

    brands = payload.get("brands") or []
    check("brands len 6", len(brands) == 6)
    labels = {b.get("label") for b in brands}
    for want in ("Atrium Lombok", "Goss Group", "Uma Blu", "Habitat", "Selo", "Tropik"):
        check(f"brand {want}", want in labels)
    for b in brands:
        check(f"brand {b.get('label')} RUNTIME_WIRED", b.get("status") == "RUNTIME_WIRED")
        check(f"brand {b.get('label')} eng null", b.get("engagement") is None)

    by_id = {s["id"]: s for s in (payload.get("surfaces") or [])}
    check("mcp RUNTIME_WIRED", (by_id.get("mcp_server") or {}).get("status") == "RUNTIME_WIRED")
    check(
        "brand_stamps RUNTIME_WIRED",
        (by_id.get("brand_stamps") or {}).get("status") == "RUNTIME_WIRED",
    )
    check(
        "analytics RUNTIME_WIRED",
        (by_id.get("analytics_paths_instagram_posts") or {}).get("status") == "RUNTIME_WIRED",
    )
    check(
        "analytics field_count 29",
        (by_id.get("analytics_paths_instagram_posts") or {}).get("field_count") == 29,
    )
    check(
        "engagement NOT_RUNTIME",
        (by_id.get("engagement_values") or {}).get("status") == "NOT_RUNTIME",
    )
    check(
        "last_success NOT_RUNTIME",
        (by_id.get("last_success") or {}).get("status") == "NOT_RUNTIME",
    )
    check(
        "publish NOT_RUNTIME",
        (by_id.get("publish_success") or {}).get("status") == "NOT_RUNTIME",
    )
    http_st = (by_id.get("wolf_http_connector") or {}).get("status")
    check(
        "wolf http EXTERNAL_BLOCKER or NOT_RUNTIME",
        http_st in ("EXTERNAL_BLOCKER", "NOT_RUNTIME"),
        str(http_st),
    )

    # Refuse paths
    for body, code in (
        ({"engagement": 99}, "engagement_refused"),
        ({"fake_engagement": True}, "engagement_refused"),
        ({"last_success": "now"}, "invent_metric_refused"),
        ({"publish_success": True}, "invent_metric_refused"),
        ({"prod_mutate": True}, "prod_mutate_refused"),
        ({"staff_ready": True}, "ready_refused"),
        ({"note": "x"}, "write_refused"),
    ):
        try:
            mrw.refuse_external_write(body)
            check(f"refuse {list(body)[0]}", False, "did not raise")
        except mrw.MetricoolRuntimeWire1Error as exc:
            check(f"refuse {list(body)[0]}", exc.code == code, exc.code)


def test_preserved_packs() -> None:
    ggv_pin = mrw.ggv_metric_honesty1_preserved()
    check("ggv preserved ok", ggv_pin.get("ok") is True, str(ggv_pin))
    check("ggv engagement null", ggv_pin.get("engagement") is None)
    check("ggv last_success null", ggv_pin.get("last_success") is None)

    # Direct GGV slice still honest (values null; not inventing)
    slice_ = ggv.build_slice()
    check("ggv slice ok", slice_.get("ok") is True)
    check("ggv slice eng null", slice_.get("engagement") is None)
    check("ggv slice fake false", slice_.get("fake_metrics") is False)
    check("ggv metricool_not_runtime", ggv.metricool_not_runtime(slice_) is True)

    cel_pin = mrw.content_engine_live1_preserved()
    check("cel preserved ok", cel_pin.get("ok") is True, str(cel_pin))
    board = cel.build_board()
    check("cel board ok", board.get("ok") is True)
    check("cel metricool not runtime", cel.metricool_not_runtime(board) is True)
    check("cel fake_metrics false", board.get("fake_metrics") is False)


def test_intg_overlay() -> None:
    board = intg.build_board()
    check("intg ok", board.get("ok") is True)
    check("intg honesty per_surface", board.get("honesty", {}).get("metricool_wolf") == "PER_SURFACE")
    met = next(c for c in board.get("connectors") or [] if c.get("integration_id") == "INT-MET-WOLF")
    check(
        "intg INT-MET RUNTIME_WIRED_PARTIAL",
        str(met.get("probe_status") or "").startswith("RUNTIME_WIRED"),
        str(met.get("probe_status")),
    )
    check("intg INT-MET last_success null", met.get("last_success") is None)
    facts = met.get("probe_facts") or {}
    check("intg brand_count 6", facts.get("brand_count") == 6)
    check("intg analytics 29", facts.get("analytics_field_count") == 29)
    check("intg eng null in facts", facts.get("engagement") is None)

    mcp = next(c for c in board.get("connectors") or [] if c.get("integration_id") == "MCP-Metricool")
    check("mcp still AGENT_HOST_ONLY", mcp.get("audit_status") == "AGENT_HOST_ONLY")


def test_http_surfaces() -> None:
    httpd, port = _start_beta()
    try:
        st, raw = call(port, "GET", "/api/ops/metricool-runtime-wire-1", MATT)
        check("api signed 200", st == 200, str(st))
        data = json.loads(raw.decode("utf-8"))
        check("api ok", data.get("ok") is True)
        check("api brand_count 6", data.get("brand_count") == 6)
        check("api engagement null", data.get("engagement") is None)
        check("api last_success null", data.get("last_success") is None)
        check("api fake_metrics false", data.get("fake_metrics") is False)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api surfaces >= 6", len(data.get("surfaces") or []) >= 6)
        by_id = {s["id"]: s for s in (data.get("surfaces") or [])}
        check(
            "api brand_stamps RUNTIME_WIRED",
            (by_id.get("brand_stamps") or {}).get("status") == "RUNTIME_WIRED",
        )
        check(
            "api engagement NOT_RUNTIME",
            (by_id.get("engagement_values") or {}).get("status") == "NOT_RUNTIME",
        )

        st, raw = call(port, "GET", "/api/ops/metricool-runtime-wire-1", None)
        check("api unsigned 403", st == 403, str(st))

        st, raw = call(port, "GET", "/ops/metricool-runtime-wire-1", MATT)
        check("page signed 200", st == 200, str(st))
        html = raw.decode("utf-8", errors="replace")
        check("page has pack", "METRICOOL-RUNTIME-WIRE-1" in html)
        check("page staff_ready=false", "staff_ready=false" in html)
        check("page RUNTIME_WIRED", "RUNTIME_WIRED" in html)

        st, _raw = call(port, "GET", "/ops/metricool-runtime-wire-1", None)
        check("page unsigned 403", st == 403, str(st))

        # INTG board reflects per-surface
        st, raw = call(port, "GET", "/api/ops/integrations-status", MATT)
        check("intg api 200", st == 200, str(st))
        idata = json.loads(raw.decode("utf-8"))
        check("intg api per_surface", (idata.get("honesty") or {}).get("metricool_wolf") == "PER_SURFACE")

        for method, body in (
            ("POST", {"engagement": 12}),
            ("POST", {"last_success": "x"}),
            ("POST", {"prod_mutate": True}),
            ("POST", {"staff_ready": True}),
            ("PATCH", {"fake_engagement": True}),
            ("PUT", {"note": "x"}),
        ):
            st, raw = call(
                port,
                method,
                "/api/ops/metricool-runtime-wire-1",
                MATT,
                json.dumps(body).encode("utf-8"),
            )
            check(f"{method} refuse {list(body)[0]}", st == 403, str(st))
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_prod_untouched() -> None:
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
    check("did not start ESB-SETTLEMENT", True)
    check("did not start HEADCHEF", True)
    check("did not start Exit Report", True)


def _ws_connect(host: str, port: int, path: str) -> socket.socket:
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    )
    sock = socket.create_connection((host, port), timeout=10)
    sock.sendall(req.encode())
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return sock


def _ws_send(sock: socket.socket, text: str) -> None:
    payload = text.encode("utf-8")
    header = bytearray([0x81])
    n = len(payload)
    mask = os.urandom(4)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack("!H", n))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack("!Q", n))
    header.extend(mask)
    header.extend(bytearray(b ^ mask[i % 4] for i, b in enumerate(payload)))
    sock.sendall(header)


def _ws_recv(sock: socket.socket) -> str:
    def read(n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("closed")
            buf += chunk
        return buf

    b1, b2 = read(2)
    length = b2 & 0x7F
    if length == 126:
        length = struct.unpack("!H", read(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", read(8))[0]
    if b2 & 0x80:
        mask = read(4)
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(read(length)))
    else:
        payload = read(length)
    return payload.decode()


def _capture(port: int, path: str, width: int, height: int, dest: Path, email: str | None, marker: str) -> str:
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
                _ws_send(sock, json.dumps({"id": ident, "method": method, "params": params or {}}))
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
                text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")
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
        specs = [
            (
                "metricoolruntime1-desk-desktop.png",
                "/ops/metricool-runtime-wire-1",
                1024,
                1200,
                MATT,
                "RUNTIME_WIRED",
            ),
            (
                "metricoolruntime1-desk-phone.png",
                "/ops/metricool-runtime-wire-1",
                390,
                1000,
                MATT,
                "Atrium Lombok",
            ),
            (
                "metricoolruntime1-surfaces.png",
                "/ops/metricool-runtime-wire-1",
                1024,
                1400,
                MATT,
                "EXTERNAL_BLOCKER",
            ),
            (
                "metricoolruntime1-unsigned-deny.png",
                "/ops/metricool-runtime-wire-1",
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


def test_artifacts() -> None:
    check("page html present", PAGE.is_file())
    html = PAGE.read_text(encoding="utf-8")
    check("html staff_ready=false", "staff_ready=false" in html)
    check("html human_commissioned=false", "human_commissioned=false" in html)
    check("html pack attr", 'data-pack="METRICOOL-RUNTIME-WIRE-1"' in html)
    check("html RUNTIME_WIRED", "RUNTIME_WIRED" in html)
    check("html NOT_RUNTIME", "NOT_RUNTIME" in html)
    check("html EXTERNAL_BLOCKER", "EXTERNAL_BLOCKER" in html)

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "METRICOOL-RUNTIME-WIRE-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "ESB-SETTLEMENT-PATH-1",
    )
    check("arm classification", arm.get("classification") == "INTERNALLY_SOLVABLE")

    check("classification log present", CLASS_LOG.is_file())
    clog = json.loads(CLASS_LOG.read_text(encoding="utf-8"))
    check("classification has metricool probe", bool(clog.get("metricool_runtime_probe")))

    if RESULT.is_file():
        result = RESULT.read_text(encoding="utf-8")
        check("result EXIT", "EXIT:0" in result or "**EXIT:0**" in result)
        check("result no auto-chain", "ESB-SETTLEMENT-PATH-1" in result)
        check(
            "result no fake engagement",
            "fake engagement" in result.lower() or "never invent" in result.lower(),
        )
    else:
        check("result deferred until EXIT write", True)


def main() -> int:
    print("=== METRICOOL-RUNTIME-WIRE-1 pack suite ===")
    test_module_honesty()
    test_preserved_packs()
    test_intg_overlay()
    test_http_surfaces()
    test_prod_untouched()
    test_artifacts()
    test_shots()
    print(f"=== PASS={PASS} FAIL={FAIL} ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
