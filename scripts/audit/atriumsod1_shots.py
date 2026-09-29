#!/usr/bin/env python3
"""ATRIUM-SOD-1C shots — distinct SoD deny, posted GL 1020, honest empty history, My Work SOD cards."""
from __future__ import annotations

import base64
import json
import os
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"
sys.path.insert(0, str(ROOT / "scripts"))

import serve_beta as sb  # noqa: E402

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SHOTS = ROOT / "docs" / "wolf" / "ops" / "shots"
ATRIUM_DIR = Path("/Users/wolfterminal/atrium-finance")
ATRIUM_DB = ATRIUM_DIR / "data" / "beta" / "atrium.sqlite"
SIDECAR_LOG = ROOT / "state" / "build-factory" / "logs" / "atrium-sidecar-1c.log"

EMAIL = {
    "PERS-ZAYEN": "laluzayen@gmail.com",
    "PERS-ZENITALFATHAN": "zenitalfathan@gmail.com",
    "PERS-MATT": "mrwolf@wolfcommand.net",
}

# Keep AP prepare shots (already correct with SoD on COMM1 prepare). Recapture the rest.
SPECS = [
    ("atriumsod1-zayen-review-desktop.png", "PERS-ZAYEN", "/amg/finance#workbench", 1024, 900, "JRN-ATRIUMSOD1B-COMM1", "review"),
    ("atriumsod1-zayen-review-phone.png", "PERS-ZAYEN", "/amg/finance#workbench", 390, 844, "JRN-ATRIUMSOD1B-COMM1", "review"),
    ("atriumsod1-sod-self-deny-desktop.png", "PERS-ZAYEN", "/amg/finance#workbench", 1024, 900, "segregation of duties", "sod"),
    ("atriumsod1-sod-self-deny-phone.png", "PERS-ZAYEN", "/amg/finance#workbench", 390, 844, "segregation of duties", "sod"),
    ("atriumsod1-zayen-posted-gl-desktop.png", "PERS-ZAYEN", "/amg/finance#ledger", 1024, 900, "JRN-ATRIUMSOD1B-COMM1", "posted_gl"),
    ("atriumsod1-zayen-posted-gl-phone.png", "PERS-ZAYEN", "/amg/finance#ledger", 390, 844, "JRN-ATRIUMSOD1B-COMM1", "posted_gl"),
    ("atriumsod1-gl-history-desktop.png", "PERS-ZAYEN", "/amg/finance#ledger", 1024, 900, "No posted journal lines", "gl_history"),
    ("atriumsod1-gl-history-phone.png", "PERS-ZAYEN", "/amg/finance#ledger", 390, 844, "No posted journal lines", "gl_history"),
    ("atriumsod1-zayen-mywork-desktop.png", "PERS-ZAYEN", "/my-work", 1024, 900, "Review / return", "mywork"),
    ("atriumsod1-zayen-mywork-phone.png", "PERS-ZAYEN", "/my-work", 390, 844, "Review / return", "mywork"),
]


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


def _listener_pid(port: int) -> int | None:
    try:
        out = subprocess.check_output(
            ["lsof", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        return None
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    return None


def _restart_sidecar() -> None:
    """Reload atrium sqlite into Node memory. Never touch :8787."""
    old = _listener_pid(8790)
    if old:
        print(f"restart_sidecar kill pid={old}")
        try:
            os.kill(old, signal.SIGTERM)
        except ProcessLookupError:
            pass
        deadline = time.time() + 15
        while time.time() < deadline and _listener_pid(8790) == old:
            time.sleep(0.2)
        still = _listener_pid(8790)
        if still == old:
            os.kill(old, signal.SIGKILL)
            time.sleep(0.5)
    SIDECAR_LOG.parent.mkdir(parents=True, exist_ok=True)
    logf = open(SIDECAR_LOG, "ab")
    starter = ROOT / "scripts" / "serve_atrium_finance.sh"
    proc = subprocess.Popen(
        ["bash", str(starter)],
        cwd=str(ATRIUM_DIR),
        stdout=logf,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    print(f"restart_sidecar spawn pid={proc.pid} via serve_atrium_finance.sh")
    deadline = time.time() + 40
    while time.time() < deadline:
        if _listener_pid(8790):
            try:
                from core import atrium_full_mount as m

                secret = m.load_assertion_secret()
                tok = m.sign_assertion(
                    secret,
                    "GET",
                    "/api/journals",
                    "PERS-ZAYEN",
                    EMAIL["PERS-ZAYEN"],
                    m.FINANCE_ROLE_CONTROLLER,
                )
                req = __import__("urllib.request").request.Request(
                    "http://127.0.0.1:8790/api/journals",
                    headers={"X-Wolf-Assertion": tok, "Accept": "application/json"},
                )
                with urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        print("restart_sidecar ready")
                        return
            except Exception:
                pass
        time.sleep(0.4)
    raise RuntimeError("sidecar failed to come up on :8790")


def capture(
    port: int,
    path: str,
    email: str,
    width: int,
    height: int,
    dest: Path,
    marker: str,
    kind: str,
) -> str:
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
                _ws_send(sock, json.dumps({"id": ident, "method": method, "params": params or {}}))
                while True:
                    msg = json.loads(_ws_recv(sock))
                    if msg.get("id") == ident:
                        return msg

            cdp("Network.enable")
            cdp("Network.setExtraHTTPHeaders", {"headers": {"X-Wolf-Subject": email}})
            cdp("Page.enable")
            cdp(
                "Emulation.setDeviceMetricsOverride",
                {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": width < 500},
            )
            cdp("Page.navigate", {"url": f"http://127.0.0.1:{port}{path}"})
            text = ""
            deadline = time.time() + 30
            while time.time() < deadline:
                got = cdp(
                    "Runtime.evaluate",
                    {"expression": "document.body ? document.body.innerText : ''", "returnByValue": True},
                )
                text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")
                if (
                    marker.lower() in text.lower()
                    and "Checking session" not in text
                    and "Initializing Atrium" not in text
                    and "sidecar_unavailable" not in text
                ):
                    # For sod/posted_gl need post-nav actions before accepting
                    if kind in {"sod", "posted_gl", "gl_history", "mywork", "review"}:
                        break
                    break
                time.sleep(0.35)

            if kind == "sod":
                # SUBMITTED filter → only Zayen's self-prepared journal + SoD deny
                cdp(
                    "Runtime.evaluate",
                    {
                        "expression": """
                        (() => {
                          const btn = Array.from(document.querySelectorAll('button'))
                            .find(b => (b.textContent||'').trim() === 'SUBMITTED');
                          if (btn) btn.click();
                          return !!btn;
                        })()
                        """,
                        "returnByValue": True,
                    },
                )
                time.sleep(0.55)
                cdp(
                    "Runtime.evaluate",
                    {
                        "expression": """
                        (() => {
                          const self = Array.from(document.querySelectorAll('tr,article,section,div,li'))
                            .find(n => /JRN-ATRIUMSOD1B-SELF/i.test(n.textContent||''));
                          if (self) self.scrollIntoView({block:'center'});
                          const el = Array.from(document.querySelectorAll('button,div,span,p,li'))
                            .find(n => /segregation of duties|you prepared this journal/i.test(n.textContent||''));
                          if (el) el.scrollIntoView({block:'center'});
                          return !!(self && el);
                        })()
                        """,
                        "returnByValue": True,
                    },
                )
                time.sleep(0.45)
            elif kind == "review":
                # POSTED filter → commissioning journal only (distinct from SoD self-deny)
                cdp(
                    "Runtime.evaluate",
                    {
                        "expression": """
                        (() => {
                          const btn = Array.from(document.querySelectorAll('button'))
                            .find(b => (b.textContent||'').trim() === 'POSTED');
                          if (btn) btn.click();
                          return !!btn;
                        })()
                        """,
                        "returnByValue": True,
                    },
                )
                time.sleep(0.55)
                cdp(
                    "Runtime.evaluate",
                    {
                        "expression": """
                        (() => {
                          const el = Array.from(document.querySelectorAll('tr,article,section,div,li'))
                            .find(n => /JRN-ATRIUMSOD1B-COMM1/i.test(n.textContent||'')
                              && !/JRN-ATRIUMSOD1B-SELF/i.test(n.textContent||''));
                          if (el) el.scrollIntoView({block:'center'});
                          return !!el;
                        })()
                        """,
                        "returnByValue": True,
                    },
                )
                time.sleep(0.4)
            elif kind == "posted_gl":
                cdp(
                    "Runtime.evaluate",
                    {
                        "expression": """
                        (() => {
                          const sel = document.querySelector('#select-ledger-account, select');
                          if (!sel) return false;
                          const opt = Array.from(sel.options).find(o => /^\\[?1020\\]?/.test(o.value) || o.value === '1020'
                            || /1020/.test(o.textContent||''));
                          if (!opt) return false;
                          sel.value = opt.value;
                          sel.dispatchEvent(new Event('change', { bubbles: true }));
                          sel.dispatchEvent(new Event('input', { bubbles: true }));
                          return true;
                        })()
                        """,
                        "returnByValue": True,
                    },
                )
                deadline = time.time() + 12
                while time.time() < deadline:
                    got = cdp(
                        "Runtime.evaluate",
                        {"expression": "document.body ? document.body.innerText : ''", "returnByValue": True},
                    )
                    text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")
                    if "JRN-ATRIUMSOD1B-COMM1" in text and "1020" in text:
                        break
                    time.sleep(0.35)
            elif kind == "gl_history":
                cdp(
                    "Runtime.evaluate",
                    {
                        "expression": """
                        (() => {
                          const sel = document.querySelector('#select-ledger-account, select');
                          if (!sel) return false;
                          const opt = Array.from(sel.options).find(o => o.value === '1000'
                            || /^\\[?1000\\]?/.test(o.value)
                            || /\\[1000\\]/.test(o.textContent||''));
                          if (!opt) return false;
                          sel.value = opt.value;
                          sel.dispatchEvent(new Event('change', { bubbles: true }));
                          sel.dispatchEvent(new Event('input', { bubbles: true }));
                          return true;
                        })()
                        """,
                        "returnByValue": True,
                    },
                )
                deadline = time.time() + 12
                while time.time() < deadline:
                    got = cdp(
                        "Runtime.evaluate",
                        {"expression": "document.body ? document.body.innerText : ''", "returnByValue": True},
                    )
                    text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")
                    if "0 posted record" in text.lower() or "no posted journal lines" in text.lower():
                        break
                    time.sleep(0.35)
            elif kind == "mywork":
                cdp(
                    "Runtime.evaluate",
                    {
                        "expression": """
                        (() => {
                          const el = Array.from(document.querySelectorAll('h2,h3,.work-title,li,article,section *'))
                            .find(n => /Review \\/ return commissioning|Approve commissioning journal|Post approved commissioning|Confirm posted lines in General Ledger|Temporary Accounts Receivable/i
                              .test((n.textContent||'').trim()));
                          if (el) el.scrollIntoView({block:'start', inline:'nearest'});
                          return !!el;
                        })()
                        """,
                        "returnByValue": True,
                    },
                )
                time.sleep(0.45)
                got = cdp(
                    "Runtime.evaluate",
                    {"expression": "document.body ? document.body.innerText : ''", "returnByValue": True},
                )
                text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")

            # Re-read text after actions for validation
            got = cdp(
                "Runtime.evaluate",
                {"expression": "document.body ? document.body.innerText : ''", "returnByValue": True},
            )
            text = str(((got.get("result") or {}).get("result") or {}).get("value") or "")

            shot = cdp("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            dest.write_bytes(base64.b64decode(((shot.get("result") or {}).get("data") or "")))
            sock.close()
            return text
        finally:
            proc.kill()
            proc.wait(timeout=5)


def _seed_self_deny_and_ensure_posted() -> None:
    """Seed Zayen-prepared SUBMITTED journal for SoD UI; ensure COMM1 POSTED for GL."""
    import sqlite3

    from core import atrium_fc_authority as fc
    from core import work_items as wi

    a = sqlite3.connect(str(ATRIUM_DB))
    try:
        fc._ensure_schema(a)
        jid = "JRN-ATRIUMSOD1B-SELF"
        a.execute("DELETE FROM journal_lines WHERE journal_id=?", (jid,))
        a.execute("DELETE FROM journal_headers WHERE journal_id=?", (jid,))
        a.execute(
            """
            INSERT INTO journal_headers (
              journal_id, journal_date, period, status, source_type, source_reference,
              created_by, preparer_person_id, wolf_created, evidence_ref
            ) VALUES (?, '2026-09-29', '2026-09', 'SUBMITTED', 'MANUAL',
              'ATRIUM-SOD-1C SoD self-deny demo (Zayen AR prep) — not a real hotel txn',
              'Zayen (Accounts Receivable temp)', 'PERS-ZAYEN', 1, '')
            """,
            (jid,),
        )
        a.execute(
            """
            INSERT INTO journal_lines VALUES
              (?, 1, '1020', '100', 25000, 0, 'SoD self-deny demo debit'),
              (?, 2, '4000', '100', 0, 25000, 'SoD self-deny demo credit')
            """,
            (jid, jid),
        )
        a.commit()
        print(f"seeded {jid} SUBMITTED preparer=PERS-ZAYEN")
    finally:
        a.close()

    conn = wi.db_connect(ROOT / "catalog" / "content_library.sqlite")
    try:
        st = sqlite3.connect(str(ATRIUM_DB)).execute(
            "SELECT status FROM journal_headers WHERE journal_id='JRN-ATRIUMSOD1B-COMM1'"
        ).fetchone()
        if st and st[0] == "SUBMITTED":
            fc.approve_journal(
                "PERS-ZAYEN",
                "JRN-ATRIUMSOD1B-COMM1",
                wolf_conn=conn,
                approver_name="Zayen",
                atrium_db=ATRIUM_DB,
            )
            fc.post_journal(
                "PERS-ZAYEN",
                "JRN-ATRIUMSOD1B-COMM1",
                wolf_conn=conn,
                poster_name="Zayen",
                atrium_db=ATRIUM_DB,
            )
            conn.commit()
            print("posted JRN-ATRIUMSOD1B-COMM1")
        else:
            print(f"commission status={st}")
        try:
            fc.approve_journal(
                "PERS-ZAYEN",
                "JRN-ATRIUMSOD1B-SELF",
                wolf_conn=conn,
                approver_name="Zayen",
                atrium_db=ATRIUM_DB,
            )
            print("FAIL expected sod_self_approve")
        except fc.FcAuthorityError as exc:
            print(f"sod_self_deny ok code={exc.code}")
    finally:
        conn.close()


def _validate(kind: str, text: str, dest: Path) -> bool:
    if not dest.is_file() or dest.stat().st_size < 8000:
        return False
    if "sidecar_unavailable" in text:
        return False
    low = text.lower()
    if kind == "sod":
        return (
            "jrn-atriumsod1b-self" in low
            and "segregation of duties" in low
            and "you prepared this journal" in low
            and "jrn-atriumsod1b-comm1" not in low  # filtered to SUBMITTED only
        )
    if kind == "review":
        return (
            "jrn-atriumsod1b-comm1" in low
            and "posted" in low
            and "jrn-atriumsod1b-self" not in low  # filtered to POSTED only
        )
    if kind == "posted_gl":
        return "jrn-atriumsod1b-comm1" in low and "1020" in text and "0 posted record" not in low
    if kind == "gl_history":
        return "1000" in text and ("0 posted record" in low or "no posted journal lines" in low)
    if kind == "mywork":
        return any(
            needle in text
            for needle in (
                "Review / return",
                "Approve commissioning",
                "Post approved commissioning",
                "Confirm posted lines",
                "Temporary Accounts Receivable",
            )
        )
    return True


def main() -> int:
    if not CHROME.is_file():
        print("FAIL chrome missing")
        return 1
    # Never touch prod
    prod = _listener_pid(8787)
    print(f"prod_8787_pid={prod} (untouched)")
    _seed_self_deny_and_ensure_posted()
    _restart_sidecar()

    handler = next(
        obj
        for obj in vars(sb).values()
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler"
    )
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"beta_temp={port}")
    ok = 0
    for name, person, path, w, h, marker, kind in SPECS:
        dest = SHOTS / name
        try:
            text = capture(port, path, EMAIL[person], w, h, dest, marker, kind)
            good = _validate(kind, text, dest)
            print(
                ("PASS" if good else "FAIL"),
                name,
                dest.stat().st_size if dest.is_file() else 0,
                text[:140].replace("\n", " "),
            )
            if good:
                ok += 1
        except Exception as exc:
            print("FAIL", name, exc)
    httpd.shutdown()

    from core import atrium_fc_authority as fc

    fc.archive_test_artifact(
        "JRN-ATRIUMSOD1B-SELF",
        reason="automated test artifact — ATRIUM-SOD-1C SoD self-deny shot",
        atrium_db=ATRIUM_DB,
    )
    # Reload so archived SELF leaves working queue for humans
    try:
        _restart_sidecar()
    except Exception as exc:
        print("WARN post-archive sidecar restart:", exc)

    print(f"SHOTS ok={ok}/{len(SPECS)}")
    print("NOTE atriumsod1-ap-prepare-* kept (not recaptured — already correct)")
    return 0 if ok == len(SPECS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
