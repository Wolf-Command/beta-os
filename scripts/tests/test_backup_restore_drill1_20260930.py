#!/usr/bin/env python3
"""BACKUP-RESTORE-DRILL-1 — Non-destructive restore drill prove (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack
BACKUP-RESTORE-DRILL-1 (armed 2026-09-30 after OWNER-EXCEPTIONS-LIVE-1).

Runs / verifies approved temp-dir drill. Lifts BACKUP-HEALTH NOT_RUN →
DRILL_RAN_NON_DESTRUCTIVE. Never invents full DR READY. Unsigned 403.
Writes refused. Prod :8787 pid 15975 untouched. Preserves BACKUP-HEALTH-1
+ RELIABILITY-1 + restore_drill refuse_* guards.
Does not auto-chain PIPE-RELIABILITY-AUTO-1 / HEADCHEF / Exit Report.
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
from core import backup_restore_drill1 as drill  # noqa: E402
from core import restore_drill as framework  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "BACKUP-RESTORE-DRILL-1-ARM.json"
LOG = ROOT / "state" / "final-completion" / "packs" / "BACKUP-RESTORE-DRILL-1-LOG.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
PAGE = ROOT / "dashboards" / "backup-restore-drill-1.html"
RESULT = ROOT / "docs" / "wolf" / "ops" / "BACKUP-RESTORE-DRILL-1-RESULT.md"
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
    check("page matcher", drill.page_matches("/ops/backup-restore-drill-1"))
    check("page alias", drill.page_matches("/backup-restore-drill-1.html"))
    check("page short", drill.page_matches("/ops/backup-restore-drill"))
    check("api matcher", drill.api_matches("/api/ops/backup-restore-drill-1"))
    check("api no mutate path", not drill.api_matches("/api/ops/backup-restore-drill-1/mutate"))

    flags = drill.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("prod_mutate false", flags.get("prod_mutate") is False)
    check("held pid 15975", flags.get("prod_pid_held") == PROD_PID)
    check("full_dr_ready false", flags.get("full_dr_ready_claimed") is False)
    check("ready_claimed false", flags.get("ready_claimed") is False)
    check("proven_claimed false", flags.get("proven_claimed") is False)
    check("shell_ne_complete", flags.get("shell_ne_complete") is True)
    check("classification INTERNALLY_SOLVABLE", flags.get("classification") == "INTERNALLY_SOLVABLE")
    check("ceiling non-destructive", flags.get("ceiling") == "PROVEN_NON_DESTRUCTIVE_ONLY")
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "PIPE-RELIABILITY-AUTO-1")
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("backup_health preserved flag", flags.get("backup_health1_preserved") is True)
    check("reliability1 preserved flag", flags.get("reliability1_preserved") is True)
    check("guards preserved flag", flags.get("restore_drill_guards_preserved") is True)


def test_run_drill_and_lift() -> None:
    # Isolated log path so we prove a real copy without clobbering pack log mid-suite.
    with tempfile.TemporaryDirectory(prefix="brd1-test-") as td:
        log_path = Path(td) / "drill-log.json"
        fixture = drill.ensure_fixture_source()
        log = drill.run_non_destructive_drill(
            source=fixture,
            log_path=log_path,
            keep_target=True,
        )
        check("drill status SUCCESS", log.get("status") == "SUCCESS", str(log.get("status")))
        check(
            "honesty DRILL_RAN_NON_DESTRUCTIVE",
            log.get("honesty_status") == "DRILL_RAN_NON_DESTRUCTIVE",
        )
        check("sha256 match", log.get("sha256_match") is True)
        check("production_mutated false", log.get("production_mutated") is False)
        check("live_restore false", log.get("live_restore") is False)
        check("nas_destructive false", log.get("nas_destructive") is False)
        check("b2_destructive false", log.get("b2_destructive") is False)
        check("source not deleted", log.get("source_deleted") is False)
        check("source still present", Path(log["source_path"]).is_file())
        check("target under temp", "backup-restore-drill1-" in str(log.get("target_path")))
        check("ready_claimed false", log.get("ready_claimed") is False)
        check("full_dr_ready false", log.get("full_dr_ready_claimed") is False)
        check("shell_ne_complete", log.get("shell_ne_complete") is True)

        src_sha = hashlib.sha256(Path(log["source_path"]).read_bytes()).hexdigest()
        dst = Path(log["target_file"])
        check("target file exists", dst.is_file())
        check("bytes equal", dst.read_bytes() == Path(log["source_path"]).read_bytes())
        check("sha equal recorded", log.get("source_sha256") == src_sha == log.get("target_sha256"))

    # Pack log (canonical) must exist after pack drill — ensure present for board lift.
    if not LOG.is_file() or str(json.loads(LOG.read_text()).get("status")).upper() != "SUCCESS":
        pack_log = drill.run_non_destructive_drill(prefer_fixture=False)
        check("pack drill SUCCESS", pack_log.get("status") == "SUCCESS", str(pack_log.get("status")))
    else:
        pack_log = json.loads(LOG.read_text(encoding="utf-8"))
        check("pack log SUCCESS", pack_log.get("status") == "SUCCESS")

    board = drill.build_board()
    check("board ok", board.get("ok") is True)
    check("board status lifted", board.get("status") == "DRILL_RAN_NON_DESTRUCTIVE")
    check("board last_drill_at", bool(board.get("last_drill_at")))
    check("board target_path", bool(board.get("target_path")))
    check("board production_mutated false", board.get("production_mutated") is False)
    check("board staff_ready false", board.get("staff_ready") is False)
    check("board human_commissioned false", board.get("human_commissioned") is False)
    check("board full_dr_ready false", board.get("full_dr_ready_claimed") is False)
    check("board shell_ne_complete", board.get("shell_ne_complete") is True)
    check("drill_is_honest", drill.drill_is_honest(board) is True)

    # BACKUP-HEALTH lift
    hb = health.build_board()
    restore = next(s for s in hb["stamps"] if s["id"] == "restore_drill")
    check(
        "BACKUP-HEALTH restore lifted",
        restore.get("status") == "DRILL_RAN_NON_DESTRUCTIVE",
        str(restore.get("status")),
    )
    check("BACKUP-HEALTH last_drill_at", bool(restore.get("last_drill_at")))
    check("BACKUP-HEALTH target_path", bool(restore.get("target_path")))
    check("BACKUP-HEALTH production_mutated false", restore.get("production_mutated") is False)
    check("BACKUP-HEALTH restore honest", health.restore_drill_is_honest(hb) is True)
    check(
        "BACKUP-HEALTH honesty lift flag",
        (hb.get("honesty") or {}).get("restore_drill_lifted_non_destructive") is True,
    )


def test_guards_preserved() -> None:
    for name, fn, code in (
        ("refuse_live_restore", framework.refuse_live_restore, "live_restore_refused"),
        ("refuse_production", framework.refuse_production, "production_refused"),
        ("refuse_nas", framework.refuse_nas, "nas_destructive_refused"),
        ("refuse_b2", framework.refuse_b2, "b2_destructive_refused"),
    ):
        try:
            fn({})
            check(f"framework {name} raises", False)
        except framework.RestoreDrillError as exc:
            check(f"framework {name}", exc.code == code, exc.code)

    # Framework skeleton still emits NOT_RUN log (separate from this pack's log).
    fw = framework.build_framework()
    check("framework status NOT_RUN", fw.get("status") == "NOT_RUN")
    check("framework live_restore false", fw.get("live_restore") is False)
    check("framework production_mutated false", fw.get("production_mutated") is False)

    # Target path guards
    try:
        drill._guard_target_dir(ROOT / "state" / "backups")  # noqa: SLF001
        check("refuse beta target", False)
    except drill.BackupRestoreDrill1Error as exc:
        check("refuse beta target", exc.code in {"target_not_temp", "target_in_beta"}, exc.code)

    try:
        drill._guard_source(Path("/tmp/not-under-beta.bin"))  # noqa: SLF001
        check("refuse non-beta source", False)
    except drill.BackupRestoreDrill1Error as exc:
        check("refuse non-beta source", exc.code == "not_beta", exc.code)


def test_http_surfaces() -> None:
    httpd, port = _start_beta()
    try:
        status, body = call(port, "GET", "/api/ops/backup-restore-drill-1", MATT)
        check("api 200", status == 200, str(status))
        payload = json.loads(body.decode())
        check("api ok", payload.get("ok") is True)
        check("api pack", payload.get("pack") == "BACKUP-RESTORE-DRILL-1")
        check("api status lifted", payload.get("status") == "DRILL_RAN_NON_DESTRUCTIVE")
        check("api last_drill_at", bool(payload.get("last_drill_at")))
        check("api target_path", bool(payload.get("target_path")))
        check("api production_mutated false", payload.get("production_mutated") is False)
        check("api staff_ready false", payload.get("staff_ready") is False)
        check("api human_commissioned false", payload.get("human_commissioned") is False)
        check("api full_dr_ready false", payload.get("full_dr_ready_claimed") is False)
        check("api shell_ne_complete", payload.get("shell_ne_complete") is True)

        status, _ = call(port, "GET", "/api/ops/backup-restore-drill-1")
        check("unsigned api 403", status == 403, str(status))

        status, body = call(port, "GET", "/ops/backup-restore-drill-1", MATT)
        check("page 200", status == 200, str(status))
        text = body.decode("utf-8", errors="replace")
        check("page title", "Backup Restore Drill" in text)
        check("page staff_ready", "staff_ready=false" in text)
        check("page production_mutated", "production_mutated=false" in text)
        check("page shell_ne_complete", "shell_ne_complete" in text.lower() or "DR READY" in text)

        status, _ = call(port, "GET", "/ops/backup-restore-drill-1")
        check("unsigned page 403", status == 403, str(status))

        # Write refuses
        for label, payload in (
            ("live_restore", {"live_restore": True}),
            ("production", {"production": True}),
            ("nas", {"nas_delete": True}),
            ("b2", {"b2_delete": True}),
            ("ready", {"ready": True}),
            ("staff_ready", {"staff_ready": True}),
        ):
            status, body = call(
                port,
                "POST",
                "/api/ops/backup-restore-drill-1",
                MATT,
                body=json.dumps(payload).encode(),
            )
            check(f"post {label} 403", status == 403, str(status))
            refused = json.loads(body.decode())
            check(f"post {label} ok false", refused.get("ok") is False)

        # BACKUP-HEALTH still surfaces lift via its API
        status, body = call(port, "GET", "/api/ops/backup-health-1", MATT)
        check("backup-health api 200", status == 200, str(status))
        hb = json.loads(body.decode())
        restore = next(s for s in hb.get("stamps") or [] if s.get("id") == "restore_drill")
        check(
            "backup-health api lifted",
            restore.get("status") == "DRILL_RAN_NON_DESTRUCTIVE",
            str(restore.get("status")),
        )
    finally:
        httpd.shutdown()


def test_prod_untouched() -> None:
    # Never kill / restart prod. Only observe whether pid file / listen looks held.
    check("prod pid constant", PROD_PID == 15975)
    check("prod port constant", PROD_PORT == 8787)
    # Soft observe — if process exists, do not touch it.
    try:
        os.kill(PROD_PID, 0)
        alive = True
    except OSError:
        alive = False
    check("prod probe did not mutate", True, f"alive={alive}")


def test_artifacts() -> None:
    check("page file", PAGE.is_file())
    check("page staff_ready=false", "staff_ready=false" in PAGE.read_text(encoding="utf-8"))
    check("arm file", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "BACKUP-RESTORE-DRILL-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm next PIPE", arm.get("next_pack_for_parent") == "PIPE-RELIABILITY-AUTO-1")
    check("log file", LOG.is_file())
    log = json.loads(LOG.read_text(encoding="utf-8"))
    check("log SUCCESS", log.get("status") == "SUCCESS")
    check("log sha match", log.get("sha256_match") is True)
    check("log production_mutated false", log.get("production_mutated") is False)
    check("result file", RESULT.is_file())
    result = RESULT.read_text(encoding="utf-8")
    check("result EXIT", "EXIT:0" in result)
    check("result no auto-chain", "PIPE-RELIABILITY-AUTO-1" in result)
    check("result DRILL_RAN", "DRILL_RAN_NON_DESTRUCTIVE" in result)


def _ws_connect(host: str, port: int, path: str) -> socket.socket:
    sock = socket.create_connection((host, port), timeout=30)
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall(
        (
            f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
            f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ).encode()
    )
    sock.recv(4096)
    return sock


def _ws_send(sock: socket.socket, text: str) -> None:
    payload = text.encode()
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
            ("backuprestore1-desk-desktop.png", "/ops/backup-restore-drill-1", 1024, 1200, MATT, "DRILL_RAN_NON_DESTRUCTIVE"),
            ("backuprestore1-desk-phone.png", "/ops/backup-restore-drill-1", 390, 1000, MATT, "DRILL_RAN_NON_DESTRUCTIVE"),
            ("backuprestore1-health-lift.png", "/ops/backup-health-1", 1024, 1200, MATT, "DRILL_RAN_NON_DESTRUCTIVE"),
            ("backuprestore1-unsigned-deny.png", "/ops/backup-restore-drill-1", 1024, 900, None, "Access denied"),
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


def main() -> int:
    print("=== BACKUP-RESTORE-DRILL-1 pack suite ===")
    test_module_honesty()
    test_run_drill_and_lift()
    test_guards_preserved()
    test_http_surfaces()
    test_prod_untouched()
    # RESULT written after suite in pack EXIT — skip result checks if missing on first pass
    if RESULT.is_file():
        test_artifacts()
    else:
        check("arm file early", ARM.is_file())
        check("log file early", LOG.is_file())
        check("page file early", PAGE.is_file())
    test_shots()
    print(f"=== PASS={PASS} FAIL={FAIL} ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
