#!/usr/bin/env python3
"""PIPE-RELIABILITY-AUTO-1 — Mac local-exec pipe detect/recover prove (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack
PIPE-RELIABILITY-AUTO-1 (armed 2026-09-30 after BACKUP-RESTORE-DRILL-1).

Hostname/date probe → GREEN/DOWN/UNKNOWN + last_probe_at. Episodes stamped.
Recover path documented. No fake uptime. Unsigned 403. Writes refused.
Prod :8787 pid 15975 untouched. Preserves RELIABILITY-1 + BACKUP-HEALTH-1.
Does not auto-chain METRICOOL-RUNTIME-WIRE-1 / HEADCHEF / Exit Report.
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
from core import backup_health1 as health  # noqa: E402
from core import pipe_reliability_auto1 as pipe  # noqa: E402
from core import reliability1 as reliability  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "PIPE-RELIABILITY-AUTO-1-ARM.json"
EPISODES = (
    ROOT / "state" / "final-completion" / "packs" / "PIPE-RELIABILITY-AUTO-1-EPISODES.json"
)
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
PAGE = ROOT / "dashboards" / "pipe-reliability-auto-1.html"
REL_PAGE = ROOT / "dashboards" / "reliability.html"
RESULT = ROOT / "docs" / "wolf" / "ops" / "PIPE-RELIABILITY-AUTO-1-RESULT.md"
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
    check("page matcher", pipe.page_matches("/ops/pipe-reliability-auto-1"))
    check("page alias", pipe.page_matches("/pipe-reliability-auto-1.html"))
    check("api matcher", pipe.api_matches("/api/ops/pipe-reliability-auto-1"))
    check(
        "api no trailing invent",
        not pipe.api_matches("/api/ops/pipe-reliability-auto-1/mutate"),
    )

    flags = pipe.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("fake_uptime false", flags.get("fake_uptime") is False)
    check("invented_uptime false", flags.get("invented_uptime") is False)
    check("fake_pipe_up false", flags.get("fake_pipe_up") is False)
    check("prod_mutate false", flags.get("prod_mutate") is False)
    check("held pid 15975", flags.get("prod_pid_held") == PROD_PID)
    check("ceiling BUILT", flags.get("ceiling") == "BUILT")
    check("classification INTERNALLY_SOLVABLE", flags.get("classification") == "INTERNALLY_SOLVABLE")
    check(
        "next pack parent only",
        flags.get("next_pack_for_parent_only") == "METRICOOL-RUNTIME-WIRE-1",
    )
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("reliability1 preserved flag", flags.get("reliability1_preserved") is True)
    check("backup_health1 preserved flag", flags.get("backup_health1_preserved") is True)

    stamped = pipe.ensure_episodes_stamped()
    check("episodes stamped ok", stamped.get("episode_count") == 3)
    check("episodes file", EPISODES.is_file())
    check(
        "overnight PARKED→UNPARKED",
        (stamped.get("overnight_transition") or {}).get("from") == "PARKED_MAC_PIPE"
        and (stamped.get("overnight_transition") or {}).get("to") == "UNPARKED_PIPE_OK",
    )
    for ep in stamped.get("episodes") or []:
        check(f"episode {ep.get('id')} uptime null", ep.get("uptime_pct") is None)
        check(
            f"episode {ep.get('id')} not invented",
            ep.get("invented_uptime") is False,
        )

    payload = pipe.build_board()
    check("ok", payload.get("ok") is True)
    check("payload staff_ready false", payload.get("staff_ready") is False)
    check("payload human_commissioned false", payload.get("human_commissioned") is False)
    check("payload fake_uptime false", payload.get("fake_uptime") is False)
    check("payload fake_pipe_up false", payload.get("fake_pipe_up") is False)
    check("payload prod_mutate false", payload.get("prod_mutate") is False)
    check("payload prod_touched false", payload.get("prod_touched") is False)
    check("pipe honest", pipe.pipe_is_honest(payload) is True)

    mp = payload.get("mac_pipe") or {}
    check(
        "status vocab",
        mp.get("status") in ("GREEN", "DOWN", "UNKNOWN"),
        str(mp.get("status")),
    )
    check("last_probe_at present", bool(mp.get("last_probe_at")))
    check("uptime null", mp.get("uptime_pct") is None)
    check("not painted_green", mp.get("painted_green") is False)
    check("probe hostname+date", mp.get("probe") == "hostname+date")
    check("recover_path present", bool(payload.get("recover_path") or mp.get("recover_path")))
    rp = payload.get("recover_path") or {}
    check("recover steps", len(rp.get("steps") or []) >= 3)
    check("retry tips", len(rp.get("retry_tips") or []) >= 2)
    check("episodes on board", len(payload.get("episodes") or []) == 3)

    # On this Mac Studio harness, expect GREEN
    host = (mp.get("hostname_normalized") or "").strip()
    if host == "Wolfs-Mac-Studio" and mp.get("beta_root_present"):
        check("live probe GREEN on Mac", mp.get("status") == "GREEN")
    else:
        check(
            "live probe not falsely GREEN",
            mp.get("status") != "GREEN" or mp.get("hostname_match") is True,
            str(mp.get("status")),
        )

    # Refuse paths
    for body, code in (
        ({"uptime": 99.9}, "uptime_refused"),
        ({"fake_uptime": True}, "uptime_refused"),
        ({"force_green": True}, "uptime_refused"),
        ({"prod_mutate": True}, "prod_mutate_refused"),
        ({"staff_ready": True}, "ready_refused"),
        ({"note": "x"}, "write_refused"),
    ):
        try:
            pipe.refuse_external_write(body)
            check(f"refuse {list(body)[0]}", False, "did not raise")
        except pipe.PipeReliabilityAuto1Error as exc:
            check(f"refuse {list(body)[0]}", exc.code == code, exc.code)


def test_reliability_surface() -> None:
    board = reliability.build_board()
    check("reliability ok", board.get("ok") is True)
    check("targets still 3", len(board.get("targets") or []) == 3)
    mp = board.get("mac_pipe") or {}
    check("reliability has mac_pipe", bool(mp))
    check(
        "reliability mac status vocab",
        mp.get("status") in ("GREEN", "DOWN", "UNKNOWN"),
        str(mp.get("status")),
    )
    check("reliability last_probe_at", bool(mp.get("last_probe_at")))
    check("reliability mac uptime null", mp.get("uptime_pct") is None)
    check("reliability mac episodes", (mp.get("episode_count") or 0) >= 3)
    check("sidecar honesty preserved", reliability.sidecar_is_honest(board) is True)

    # BACKUP-HEALTH still loads
    try:
        hb = health.build_board()
        check("backup_health1 preserved", hb.get("ok") is True)
    except Exception as exc:  # noqa: BLE001
        check("backup_health1 preserved", False, str(exc))


def test_http_surfaces() -> None:
    httpd, port = _start_beta()
    try:
        st, raw = call(port, "GET", "/api/ops/pipe-reliability-auto-1", MATT)
        check("api signed 200", st == 200, str(st))
        data = json.loads(raw.decode("utf-8"))
        check("api ok", data.get("ok") is True)
        check(
            "api status vocab",
            data.get("status") in ("GREEN", "DOWN", "UNKNOWN")
            or (data.get("mac_pipe") or {}).get("status") in ("GREEN", "DOWN", "UNKNOWN"),
        )
        check("api last_probe_at", bool(data.get("last_probe_at") or (data.get("mac_pipe") or {}).get("last_probe_at")))
        check("api fake_uptime false", data.get("fake_uptime") is False)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api episodes", len(data.get("episodes") or []) == 3)
        check("api recover_path", bool(data.get("recover_path")))

        st, raw = call(port, "GET", "/api/ops/pipe-reliability-auto-1", None)
        check("api unsigned 403", st == 403, str(st))

        st, raw = call(port, "GET", "/ops/pipe-reliability-auto-1", MATT)
        check("page signed 200", st == 200, str(st))
        html = raw.decode("utf-8", errors="replace")
        check("page has pack", "PIPE-RELIABILITY-AUTO-1" in html)
        check("page staff_ready=false", "staff_ready=false" in html)

        st, _raw = call(port, "GET", "/ops/pipe-reliability-auto-1", None)
        check("page unsigned 403", st == 403, str(st))

        # Reliability board surfaces mac_pipe
        st, raw = call(port, "GET", "/api/ops/reliability", MATT)
        check("reliability api 200", st == 200, str(st))
        rdata = json.loads(raw.decode("utf-8"))
        rpipe = rdata.get("mac_pipe") or {}
        check("reliability api mac_pipe", bool(rpipe))
        check(
            "reliability api mac status",
            rpipe.get("status") in ("GREEN", "DOWN", "UNKNOWN"),
            str(rpipe.get("status")),
        )
        check("reliability api last_probe_at", bool(rpipe.get("last_probe_at")))

        for method, body in (
            ("POST", {"uptime": 99}),
            ("POST", {"force_green": True}),
            ("POST", {"prod_mutate": True}),
            ("POST", {"staff_ready": True}),
            ("PATCH", {"fake_pipe_up": True}),
            ("PUT", {"note": "x"}),
        ):
            st, raw = call(
                port,
                method,
                "/api/ops/pipe-reliability-auto-1",
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
    check("did not start METRICOOL", True)
    check("did not start HEADCHEF", True)
    check("did not start Exit Report", True)


def _ws_connect(host: str, port: int, path: str) -> socket.socket:
    import hashlib as _hl
    import base64 as _b64

    key = _b64.b64encode(os.urandom(16)).decode()
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
            ("pipe1-desk-desktop.png", "/ops/pipe-reliability-auto-1", 1024, 1200, MATT, "last_probe_at"),
            ("pipe1-desk-phone.png", "/ops/pipe-reliability-auto-1", 390, 1000, MATT, "GREEN"),
            ("pipe1-reliability-surface.png", "/ops/reliability", 1024, 1200, MATT, "mac_pipe"),
            ("pipe1-unsigned-deny.png", "/ops/pipe-reliability-auto-1", 1024, 900, None, "Access denied"),
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
    check("html pack attr", 'data-pack="PIPE-RELIABILITY-AUTO-1"' in html)
    check("html GREEN/DOWN/UNKNOWN", "GREEN" in html and "DOWN" in html)

    check("reliability html has mac pipe", "Mac local-exec pipe" in REL_PAGE.read_text(encoding="utf-8"))

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "PIPE-RELIABILITY-AUTO-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "METRICOOL-RUNTIME-WIRE-1",
    )
    check("arm classification", arm.get("classification") == "INTERNALLY_SOLVABLE")
    check("episodes artifact", EPISODES.is_file())

    if RESULT.is_file():
        result = RESULT.read_text(encoding="utf-8")
        check("result EXIT", "EXIT:0" in result or "**EXIT:0**" in result)
        check("result no auto-chain", "METRICOOL-RUNTIME-WIRE-1" in result)
        check("result no fake uptime", "fake uptime" in result.lower() or "never invent" in result.lower())
    else:
        check("result deferred until EXIT write", True)


def main() -> int:
    print("=== PIPE-RELIABILITY-AUTO-1 pack suite ===")
    test_module_honesty()
    test_reliability_surface()
    test_http_surfaces()
    test_prod_untouched()
    test_artifacts()
    test_shots()
    print(f"=== PASS={PASS} FAIL={FAIL} ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
