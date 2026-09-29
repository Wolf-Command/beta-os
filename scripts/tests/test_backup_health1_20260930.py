#!/usr/bin/env python3
"""BACKUP-HEALTH-1 — Backup/recovery health stamps prove (Beta only).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack BACKUP-HEALTH-1
(armed 2026-09-30 after ESB-TRUTH-1 PASS_VERIFIED).

Beta catalog + atrium RO stamps. No fake backup success / invent restore PASS.
Unsigned API/page 403. Writes refused. Prod :8787 pid 15975 untouched.
Never flips commissioning flags. Preserves RELIABILITY-1.
Does not auto-chain FIN-CASH-TRUTH-1 / HEADCHEF / Exit Report.
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
from core import backup_health1 as board  # noqa: E402

MATT = "mrwolf@wolfcommand.net"
ARM = ROOT / "state" / "final-completion" / "packs" / "BACKUP-HEALTH-1-ARM.json"
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
PAGE = ROOT / "dashboards" / "backup-health-1.html"
RESULT = ROOT / "docs" / "wolf" / "ops" / "BACKUP-HEALTH-1-RESULT.md"
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
    check("page matcher /ops/backup-health-1", board.page_matches("/ops/backup-health-1"))
    check("page matcher alias", board.page_matches("/backup-health-1.html"))
    check("page matcher short", board.page_matches("/ops/backup-health"))
    check("api matcher", board.api_matches("/api/ops/backup-health-1"))
    check("api no mutate path", not board.api_matches("/api/ops/backup-health-1/mutate"))

    flags = board.honesty_flags()
    check("staff_ready false", flags.get("staff_ready") is False)
    check("human_commissioned false", flags.get("human_commissioned") is False)
    check("fake_backup_success false", flags.get("fake_backup_success") is False)
    check("invented_restore_pass false", flags.get("invented_restore_pass") is False)
    check("restore_drill_pass_invented false", flags.get("restore_drill_pass_invented") is False)
    check("prod_mutate false", flags.get("prod_mutate") is False)
    check("prod RO", flags.get("prod_probe_read_only") is True)
    check("held pid 15975", flags.get("prod_pid_held") == PROD_PID)
    check("ceiling BUILT", flags.get("ceiling") == "BUILT")
    check("next pack parent only", flags.get("next_pack_for_parent_only") == "FIN-CASH-TRUTH-1")
    check("no auto-chain", flags.get("cursor_did_not_auto_start_next") is True)
    check("reliability1 preserved flag", flags.get("reliability1_preserved") is True)

    payload = board.build_board()
    check("ok", payload.get("ok") is True)
    check("payload staff_ready false", payload.get("staff_ready") is False)
    check("payload human_commissioned false", payload.get("human_commissioned") is False)
    check("payload fake_backup_success false", payload.get("fake_backup_success") is False)
    check("payload invented_restore_pass false", payload.get("invented_restore_pass") is False)
    check("payload restore_drill_pass_invented false", payload.get("restore_drill_pass_invented") is False)
    check("payload prod_mutate false", payload.get("prod_mutate") is False)
    check("payload prod_touched false", payload.get("prod_touched") is False)
    check("payload held pid", payload.get("prod_pid_held") == PROD_PID)
    check("payload ceiling BUILT", payload.get("ceiling") == "BUILT")
    check("proven_claimed false", payload.get("proven_claimed") is False)
    check("ready_claimed false", payload.get("ready_claimed") is False)

    stamps = payload.get("stamps") or []
    check("stamps >= 6", len(stamps) >= 6, str(len(stamps)))
    by_id = {t.get("id"): t for t in stamps}
    for needed in (
        "last_backup",
        "restore_drill",
        "cap_dr_01",
        "historical_b2_drill",
        "atrium_snapshot",
        "reliability1",
    ):
        check(f"has {needed}", needed in by_id)

    for tid, row in by_id.items():
        check(f"{tid} success not invented", row.get("success_invented") is False)
        check(
            f"{tid} status non-empty",
            bool(row.get("status")),
            str(row.get("status")),
        )

    restore = by_id["restore_drill"]
    check(
        "restore NOT_RUN or UNKNOWN",
        str(restore.get("status") or "").upper() in ("NOT_RUN", "UNKNOWN", "MISSING"),
        str(restore.get("status")),
    )
    check("restore not PASS", str(restore.get("status") or "").upper() not in (
        "SUCCESS", "PASS", "PASSED", "RESTORED", "OK", "DONE", "COMPLETE", "COMPLETED",
    ))
    check("restore live_restore false", restore.get("live_restore") is False)
    check("restore pass_invented false", restore.get("pass_invented") is False)
    check("restore_drill_is_honest", board.restore_drill_is_honest(payload) is True)

    hist = by_id["historical_b2_drill"]
    check("historical status HISTORICAL", hist.get("status") == "HISTORICAL")
    check("historical not this drill", hist.get("is_this_drill") is False)
    check("historical not live success", hist.get("counts_as_live_success") is False)

    cap = by_id["cap_dr_01"]
    check(
        "cap not invented PROVEN by pack",
        cap.get("proven_claimed") is False,
    )
    check("cap maturity_raised false", cap.get("maturity_raised") is False)
    # Ledger may be SPECIFIED — never invent READY
    check(
        "cap not READY claimed",
        cap.get("ready_claimed") is False,
        str(cap.get("status")),
    )

    last = by_id["last_backup"]
    check(
        "last_backup status honest",
        last.get("status") in ("PRESENT", "MISSING", "UNKNOWN"),
        str(last.get("status")),
    )
    check("last_backup fake false", last.get("fake_backup_success") is False)

    rel = by_id["reliability1"]
    check(
        "reliability1 preserved or unknown",
        rel.get("status") in ("PRESERVED", "UNKNOWN", "BROKEN"),
        str(rel.get("status")),
    )
    if rel.get("status") == "PRESERVED":
        check("reliability1 sidecar honest", rel.get("sidecar_honest") is True)

    honesty = payload.get("honesty") or {}
    check("honesty last≠restore", honesty.get("last_backup_is_not_restore") is True)
    check("honesty historical not this", honesty.get("historical_not_this_drill") is True)
    check("honesty restore not pass", honesty.get("restore_drill_not_pass") is True)

    # Refuse helpers
    try:
        board.refuse_fake_backup_success({"backup_success": True})
        check("refuse_fake_backup raises", False)
    except board.BackupHealth1Error as exc:
        check("refuse_fake_backup code", exc.code == "backup_success_refused")

    try:
        board.refuse_fake_restore_pass({"restore_pass": True})
        check("refuse_fake_restore raises", False)
    except board.BackupHealth1Error as exc:
        check("refuse_fake_restore code", exc.code == "restore_pass_refused")

    try:
        board.refuse_prod_mutate({"prod": "restart"})
        check("refuse_prod_mutate raises", False)
    except board.BackupHealth1Error as exc:
        check("refuse_prod_mutate code", exc.code == "prod_mutate_refused")

    try:
        board.refuse_external_write({"backup_success": True})
        check("refuse backup write raises", False)
    except board.BackupHealth1Error as exc:
        check(
            "refuse backup write",
            exc.code in ("backup_success_refused", "write_refused"),
            str(exc.code),
        )

    try:
        board.refuse_external_write({"restore_pass": True})
        check("refuse restore write raises", False)
    except board.BackupHealth1Error as exc:
        check(
            "refuse restore write",
            exc.code in ("restore_pass_refused", "write_refused"),
            str(exc.code),
        )

    try:
        board.refuse_external_write({"staff_ready": True})
        check("refuse ready write raises", False)
    except board.BackupHealth1Error as exc:
        check("refuse ready write", exc.code == "ready_refused")

    try:
        board.refuse_external_write({"note": "x"})
        check("generic write raises", False)
    except board.BackupHealth1Error as exc:
        check("generic write refused", exc.code == "write_refused")


def test_http_api_and_page() -> None:
    httpd, port = _start_beta()
    try:
        status, body = call(port, "GET", "/api/ops/backup-health-1", MATT)
        check("api 200", status == 200, str(status))
        data = json.loads(body.decode())
        check("api ok", data.get("ok") is True)
        check("api staff_ready false", data.get("staff_ready") is False)
        check("api human_commissioned false", data.get("human_commissioned") is False)
        check("api fake_backup_success false", data.get("fake_backup_success") is False)
        check("api invented_restore_pass false", data.get("invented_restore_pass") is False)
        check("api prod_mutate false", data.get("prod_mutate") is False)
        stamps = data.get("stamps") or []
        check("api stamps >= 6", len(stamps) >= 6, str(len(stamps)))
        restore = next((s for s in stamps if s.get("id") == "restore_drill"), {})
        check(
            "api restore not PASS",
            str(restore.get("status") or "").upper()
            not in ("SUCCESS", "PASS", "PASSED", "RESTORED", "OK"),
            str(restore.get("status")),
        )

        status, body = call(port, "GET", "/api/ops/backup-health-1")
        check("unsigned api 403", status == 403, str(status))

        status, body = call(port, "GET", "/ops/backup-health-1", MATT)
        check("page 200", status == 200, str(status))
        text = body.decode("utf-8", errors="replace")
        check("page title", "Backup Health" in text)
        check("page honesty staff_ready", "staff_ready=false" in text)
        check("page honesty human_commissioned", "human_commissioned=false" in text)
        check(
            "page no fake backup copy",
            "no fake backup success" in text.lower() or "fake backup" in text.lower(),
        )
        check(
            "page restore NOT_RUN honesty",
            "NOT_RUN" in text or "restore-drill" in text.lower(),
        )

        status, _ = call(port, "GET", "/ops/backup-health-1")
        check("unsigned page 403", status == 403, str(status))

        # Alias page
        status, body = call(port, "GET", "/ops/backup-health", MATT)
        check("alias page 200", status == 200, str(status))

        # Write refuse — invent backup success
        status, body = call(
            port,
            "POST",
            "/api/ops/backup-health-1",
            MATT,
            body=json.dumps({"backup_success": True}).encode(),
        )
        check("post backup_success 403", status == 403, str(status))
        refused = json.loads(body.decode())
        check("post backup refused ok false", refused.get("ok") is False)
        check(
            "post backup error",
            refused.get("error") in ("backup_success_refused", "write_refused"),
            str(refused.get("error")),
        )
        check("post backup fake pin", refused.get("fake_backup_success") is False)

        status, body = call(
            port,
            "POST",
            "/api/ops/backup-health-1",
            MATT,
            body=json.dumps({"restore_pass": True, "live_restore": True}).encode(),
        )
        check("post restore_pass 403", status == 403, str(status))
        refused = json.loads(body.decode())
        check(
            "post restore error",
            refused.get("error") in ("restore_pass_refused", "write_refused"),
            str(refused.get("error")),
        )
        check("post restore invent pin", refused.get("invented_restore_pass") is False)

        status, body = call(
            port,
            "POST",
            "/api/ops/backup-health-1",
            MATT,
            body=json.dumps({"prod_mutate": True, "15975": "kill"}).encode(),
        )
        check("post prod 403", status == 403, str(status))
        refused = json.loads(body.decode())
        check(
            "post prod error",
            refused.get("error") in ("prod_mutate_refused", "write_refused"),
            str(refused.get("error")),
        )
        check("post prod mutate pin", refused.get("prod_mutate") is False)

        status, body = call(
            port,
            "PATCH",
            "/api/ops/backup-health-1",
            MATT,
            body=json.dumps({"drill_pass": True}).encode(),
        )
        check("patch drill_pass 403", status == 403, str(status))

        status, body = call(
            port,
            "PUT",
            "/api/ops/backup-health-1/force-ok",
            MATT,
            body=json.dumps({"force_success": True}).encode(),
        )
        check("put force-ok 403", status == 403, str(status))
    finally:
        httpd.shutdown()
        httpd.server_close()


def _ws_connect(host: str, port: int, path: str):
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
        board_expr = (
            "(() => {"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const t=document.body ? document.body.innerText : '';"
            " const ht=(document.getElementById('honesty')||{}).textContent||'';"
            " const restore=document.querySelector('tr[data-id=\"restore_drill\"]');"
            " const restoreStatus=restore && restore.getAttribute('data-status');"
            " return {ok: ready==='1' && t.includes('Backup Health')"
            "  && ht.includes('staff_ready=false') && ht.includes('human_commissioned=false')"
            "  && t.includes('last_backup') && t.includes('restore_drill') && t.includes('cap_dr_01'),"
            " text:t.slice(0,500), honesty:ht, restoreStatus:restoreStatus,"
            " hasNotRun: (restoreStatus==='NOT_RUN') || t.includes('NOT_RUN')};"
            "})()"
        )
        for width, name in (
            (1024, "backuphealth1-board-desktop.png"),
            (390, "backuphealth1-board-phone.png"),
        ):
            for cdp, _ev, value in _with_cdp(
                width, MATT, f"http://127.0.0.1:{port}/ops/backup-health-1", board_expr
            ):
                check(f"board ready {name}", bool(value and value.get("ok")), str(value)[:220])
                if value:
                    check(
                        f"NOT_RUN visible {name}",
                        value.get("hasNotRun") is True,
                        str(value.get("restoreStatus")),
                    )
                shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                dest = SHOTS / name
                dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
                check(f"shot {name}", dest.is_file() and dest.stat().st_size > 3000)

        # Stamps honesty shot (restore NOT_RUN + last_backup)
        for cdp, _ev, value in _with_cdp(
            1024,
            MATT,
            f"http://127.0.0.1:{port}/ops/backup-health-1",
            board_expr,
        ):
            check("stamps shot ready", bool(value and value.get("ok")), str(value)[:200])
            if value:
                check(
                    "restore NOT_RUN on stamps shot",
                    value.get("restoreStatus") in ("NOT_RUN", "UNKNOWN", "MISSING"),
                    str(value.get("restoreStatus")),
                )
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "backuphealth1-stamps-honesty.png"
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            check("shot stamps-honesty", dest.is_file() and dest.stat().st_size > 3000)

        deny_expr = (
            "(() => {"
            " const t=document.body ? document.body.innerText : '';"
            " const ready=document.body && document.body.getAttribute('data-ready');"
            " const statusHint=/403|forbidden|sign.?in|unauthor|denied|identity/i.test(t);"
            " const notLoaded=ready!=='1';"
            " return {ok: statusHint || notLoaded, text:t.slice(0,400), ready:ready, statusHint:statusHint};"
            "})()"
        )
        for cdp, _ev, value in _with_cdp(
            1024,
            None,
            f"http://127.0.0.1:{port}/ops/backup-health-1",
            deny_expr,
            wait_seconds=20.0,
        ):
            check("unsigned deny page", bool(value and value.get("ok")), str(value)[:220])
            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest = SHOTS / "backuphealth1-unsigned-deny.png"
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
    check("html pack attr", 'data-pack="BACKUP-HEALTH-1"' in html)
    check("html no fake backup", "no fake backup success" in html.lower())

    check("arm present", ARM.is_file())
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    check("arm pack", arm.get("pack") == "BACKUP-HEALTH-1")
    check("arm staff_ready false", arm.get("staff_ready") is False)
    check("arm human_commissioned false", arm.get("human_commissioned") is False)
    check("arm prod_mutate false", arm.get("prod_mutate") is False)
    check("arm no_push", arm.get("no_push") is True)
    check("arm held pid", arm.get("prod_pid_held") == PROD_PID)
    check(
        "arm next parent",
        arm.get("next_pack_for_parent") == "FIN-CASH-TRUTH-1"
        or arm.get("next_pack_for_parent_only") == "FIN-CASH-TRUTH-1",
    )

    # Prod RO — still listening as held pid
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

    # Shots distinct
    names = [
        "backuphealth1-board-desktop.png",
        "backuphealth1-board-phone.png",
        "backuphealth1-stamps-honesty.png",
        "backuphealth1-unsigned-deny.png",
    ]
    hashes = []
    for name in names:
        path = SHOTS / name
        check(f"shot file {name}", path.is_file() and path.stat().st_size > 800)
        if path.is_file():
            hashes.append(path.read_bytes()[:64])
    if len(hashes) == 4:
        check("shots not identical prefixes", len(set(hashes)) >= 2)


def main() -> int:
    test_module_honesty()
    test_http_api_and_page()
    test_shots()
    test_artifacts_and_prod_ro()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
