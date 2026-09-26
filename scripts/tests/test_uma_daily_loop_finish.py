#!/usr/bin/env python3
"""Uma Blu daily loop finish — close, variance, exception, owner visibility.

Temp catalog for the close chain. Phone proof at 390px for the F&B operations
lead and the existing venue closing operator role. The closing operator is a
temporary seat on ROLE-BZG-CLOSER and is removed. No production. No payment.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import request_auth as ra  # noqa: E402
from core import staff_home as home  # noqa: E402
from core import uma_devi_p0 as p0  # noqa: E402
from core import uma_ops_console as ops  # noqa: E402

PASS = 0
FAIL = 0
LIVE = ROOT / "catalog" / "content_library.sqlite"
TS = "2026-09-27T03:00:00+08:00"
BIZ = "2099-01-15"
DEVI = "deviputu236@gmail.com"
CLOSER_ID = "PERS-P5-CLOSER"
CLOSER_EMAIL = "p5-closer@seed.invalid"
CLOSER_ASG = "ASG-P5-CLOSER"
CLOSER_POS_NEW = "POS-P5-CLOSER"
CLOSER_ROLE = "ROLE-BZG-CLOSER"
EXISTING_POS = "POS-BZG-CLOSER-UMA-1"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def listener_pid(port: int) -> str:
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            text=True,
        ).strip().splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return out[0] if out else ""


def live_counts() -> tuple[int, int]:
    c = sqlite3.connect(str(LIVE))
    try:
        tabs = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        policies = (
            c.execute("SELECT COUNT(*) FROM venue_close_variance_policies").fetchone()[0]
            if "venue_close_variance_policies" in tabs
            else 0
        )
        closes = (
            c.execute("SELECT COUNT(*) FROM venue_daily_closes").fetchone()[0]
            if "venue_daily_closes" in tabs
            else 0
        )
        return int(policies), int(closes)
    finally:
        c.close()


def make_esb(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            "CREATE TABLE sales (nk TEXT PRIMARY KEY, biz_date TEXT, raw TEXT, pulled_at TEXT)"
        )
        raw = {
            "branchCode": "BLZ",
            "salesNum": "S1",
            "billNum": "B1",
            "statusName": "Finished",
            "grandTotal": 200000,
            "paymentTotal": 200000,
            "salesPayments": [{"paymentMethodTypeName": "CASH", "paymentAmount": 200000}],
        }
        conn.execute(
            "INSERT INTO sales (nk, biz_date, raw, pulled_at) VALUES (?,?,?,?)",
            ("BLZ|S1", BIZ, json.dumps(raw), "2099-01-15T20:00:00+08:00"),
        )
        conn.commit()
    finally:
        conn.close()


def seed_closer(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES (?, 'Closing operator', NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (CLOSER_ID, TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET
          status='ACTIVE', end_at=NULL, updated_at=excluded.updated_at
        """,
        (CLOSER_ASG, CLOSER_ID, EXISTING_POS, TS, TS, TS),
    )
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(conn, CLOSER_ASG, "SCOPE-BZG-UMA", TS, TS)
    conn.commit()


def _catalog_modules():
    import core.audit as audit
    import core.evidence as evidence
    import core.identity as identity
    import core.organisation as org
    import core.rbac as rbac
    import core.scope as scope
    import core.venue_close as vc
    import core.work_items as wi

    return (vc, evidence, audit, wi, rbac, org, scope, identity, ops, p0)


def wire(tmp: Path):
    saved = {}
    for mod in _catalog_modules():
        if hasattr(mod, "CATALOG_DB"):
            saved[mod] = mod.CATALOG_DB
            mod.CATALOG_DB = tmp
    return saved


def restore(saved: dict) -> None:
    for mod, path in saved.items():
        mod.CATALOG_DB = path


def test_chain() -> None:
    before = live_counts()
    td = Path(tempfile.mkdtemp(prefix="uma-loop-", dir=str(ROOT / "state")))
    tmp = td / "content_library.sqlite"
    esb_path = td / "esb.sqlite"
    saved: dict = {}
    try:
        shutil.copy2(LIVE, tmp)
        make_esb(esb_path)
        esb_hash = esb_path.read_bytes()
        saved = wire(tmp)
        import core.venue_close as vc

        conn = sqlite3.connect(str(tmp))
        conn.row_factory = sqlite3.Row
        try:
            seed_closer(conn)
            opened = vc.open_or_get(BIZ, verified_person_id=CLOSER_ID, conn=conn, commit=True)
            vc.capture_esb_snapshot(
                opened["close_id"],
                verified_person_id=CLOSER_ID,
                esb_path=esb_path,
                conn=conn,
                commit=True,
            )
            vc.attach_declared_cash(
                opened["close_id"],
                declared_cash_amount=150000,
                verified_person_id=CLOSER_ID,
                allow_test_write=True,
                conn=conn,
                commit=True,
            )
            rec = vc.reconcile(
                opened["close_id"],
                verified_person_id=CLOSER_ID,
                esb_path=esb_path,
                conn=conn,
                commit=True,
            )
            check("variance requires a policy", rec["state"] == "VARIANCE_REQUIRES_POLICY", rec["state"])
            check("variance is declared minus ESB cash", rec.get("variance_cash_amount") == -50000.0)
            early = ops.owner_exception_strip(conn=conn)
            early_labels = " ".join(str(r.get("label") or "") for r in (early.get("exceptions") or []))
            check("variance alone is not an owner exception", BIZ not in early_labels, early_labels[:180])
            ex = vc.open_exception(opened["close_id"], verified_person_id=CLOSER_ID, conn=conn, commit=True)
            check("exception opened", ex["state"] == "EXCEPTION", ex.get("state"))
            check("work item linked", bool(ex.get("work_item_id")))
            owner = ops.owner_exception_strip(conn=conn)
            labels = [str(r.get("label") or "") for r in (owner.get("exceptions") or [])]
            check("owner visibility sees the close", any(BIZ in label for label in labels), str(labels[:6]))
            check("owner strip is not money", owner.get("money") is None and owner.get("payment_execution") is False)
            evidence = ops.list_daily_evidence(conn=conn)
            evid_labels = " ".join(str(r.get("label") or "") for r in evidence.get("rows") or [])
            check("cash count evidence recorded", BIZ in evid_labels, evid_labels[:180])
            check("evidence invents no amount", "150000" not in evid_labels and "200000" not in evid_labels)
            lead = home.build_home("PERS-DEVI", conn=conn)
            today_titles = []
            for section in lead.get("sections") or []:
                if section.get("key") == "today":
                    today_titles = [str(i.get("title") or "") for i in section.get("items") or []]
            check(
                "operations lead My Work has the exception",
                any(BIZ in title for title in today_titles),
                str(today_titles[:4]),
            )
            check("lead cannot move money", lead["authority"]["move_money"] is False)
            check("lead seat is operations", "day's operations" in (p0.operator_view("PERS-DEVI", conn=conn).get("seat_line") or ""))
            closer_line = p0.operator_view(CLOSER_ID, conn=conn).get("seat_line") or ""
            check("closer seat counts the till", "count the till" in closer_line, closer_line)
            check("closer cannot pay", "cannot pay" in closer_line)
            buttons = p0.operator_view(CLOSER_ID, conn=conn)["buttons"]
            check("closer has no payment button", buttons.get("payment_approve") is False)
            check("closer is not given verify", buttons.get("verify_close") is False)
        finally:
            conn.close()
        check("ESB file unchanged", esb_path.read_bytes() == esb_hash)
    finally:
        restore(saved)
        shutil.rmtree(td, ignore_errors=True)
    check("live variance policies unchanged", live_counts()[0] == before[0], str(live_counts()))
    check("live closes unchanged", live_counts()[1] == before[1], str(live_counts()))


def _live():
    c = sqlite3.connect(str(LIVE), timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c


def _wipe_closer(drop_position: bool) -> None:
    c = _live()
    try:
        c.execute("DELETE FROM org_assignment_scopes WHERE assignment_id=?", (CLOSER_ASG,))
        c.execute("DELETE FROM org_assignments WHERE assignment_id=?", (CLOSER_ASG,))
        c.execute(
            "DELETE FROM org_auth_identities WHERE person_id=? OR lower(identifier)=?",
            (CLOSER_ID, CLOSER_EMAIL),
        )
        c.execute("DELETE FROM org_persons WHERE person_id=?", (CLOSER_ID,))
        if drop_position:
            c.execute("DELETE FROM org_positions WHERE position_id=?", (CLOSER_POS_NEW,))
        c.commit()
    finally:
        c.close()


def _seat_live_closer() -> str:
    """Seat the existing closing role. Returns the position id used."""
    c = _live()
    try:
        busy = c.execute(
            """
            SELECT assignment_id FROM org_assignments
            WHERE position_id=? AND status='ACTIVE' AND end_at IS NULL
            """,
            (EXISTING_POS,),
        ).fetchone()
        pos = EXISTING_POS
        if busy:
            src = c.execute(
                "SELECT entity_id, position_label FROM org_positions WHERE position_id=?",
                (EXISTING_POS,),
            ).fetchone()
            pos = CLOSER_POS_NEW
            c.execute(
                """
                INSERT INTO org_positions (
                  position_id, role_id, entity_id, location_id, brand_id, department_id,
                  position_label, status, fte, created_at, updated_at
                ) VALUES (?, ?, ?, NULL, NULL, NULL, ?, 'ACTIVE', 1, ?, ?)
                """,
                (
                    pos,
                    CLOSER_ROLE,
                    src["entity_id"] if src else None,
                    (src["position_label"] if src else None) or "Venue Closing Operator",
                    TS,
                    TS,
                ),
            )
        c.execute(
            """
            INSERT INTO org_persons (
              person_id, display_name, legal_name, status, created_at, updated_at
            ) VALUES (?, 'Closing operator', NULL, 'ACTIVE', ?, ?)
            """,
            (CLOSER_ID, TS, TS),
        )
        c.execute(
            """
            INSERT INTO org_auth_identities (
              auth_identity_id, person_id, provider, identifier, status,
              is_primary, created_at, updated_at
            ) VALUES (?, ?, 'email', ?, 'ACTIVE', 1, ?, ?)
            """,
            (f"AUTH-{CLOSER_ASG}", CLOSER_ID, CLOSER_EMAIL, TS, TS),
        )
        c.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at, status,
              is_primary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
            """,
            (CLOSER_ASG, CLOSER_ID, pos, TS, TS, TS),
        )
        c.execute(
            """
            INSERT INTO org_assignment_scopes (
              assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
            ) VALUES (?, 'SCOPE-BZG-UMA', ?, NULL, 'ACTIVE', ?, ?)
            """,
            (CLOSER_ASG, TS, TS, TS),
        )
        c.commit()
        return pos
    finally:
        c.close()


def test_phone() -> None:
    ra._ENV_LOADED = True
    import serve_beta as sb

    Handler = None
    for _, obj in __import__("inspect").getmembers(sb, __import__("inspect").isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            Handler = obj
            break
    check("handler found", Handler is not None)
    if Handler is None:
        return
    drop_position = False
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    class _Proxy(BaseHTTPRequestHandler):
        subject = DEVI

        def log_message(self, *_args):  # noqa: ANN002
            return

        def do_GET(self):  # noqa: N802
            req = Request(
                f"http://127.0.0.1:{port}{self.path}",
                headers={"X-Wolf-Subject": _Proxy.subject, "Accept": "*/*"},
                method="GET",
            )
            try:
                with urlopen(req, timeout=30) as resp:
                    body = resp.read()
                    ctype = resp.headers.get("Content-Type") or "text/html"
                    code = resp.status
            except HTTPError as exc:
                body = exc.read()
                ctype = exc.headers.get("Content-Type") if exc.headers else "text/html"
                code = exc.code
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    proxy = ThreadingHTTPServer(("127.0.0.1", 0), _Proxy)
    pport = proxy.server_address[1]
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    check("chrome present", chrome.is_file())
    try:
        pos = _seat_live_closer()
        drop_position = pos == CLOSER_POS_NEW
        if not chrome.is_file():
            return
        for label, subject, path, needle in (
            ("lead-today", DEVI, "/bzg/uma-blu", "You run the day's operations"),
            ("lead-evidence", DEVI, "/bzg/uma-blu/evidence", "No close evidence recorded in Wolf yet."),
            ("lead-exceptions", DEVI, "/bzg/uma-blu/exceptions", "Exceptions"),
            ("closer-today", CLOSER_EMAIL, "/bzg/uma-blu", "You count the till"),
        ):
            _Proxy.subject = subject
            proc = subprocess.run(
                [
                    str(chrome),
                    "--headless=new",
                    "--disable-gpu",
                    "--virtual-time-budget=8000",
                    "--window-size=390,844",
                    "--dump-dom",
                    f"http://127.0.0.1:{pport}{path}",
                ],
                capture_output=True,
                text=True,
                timeout=40,
            )
            dom = proc.stdout or ""
            check(f"{label} shows {needle}", needle in dom, (proc.stderr or dom)[-240:])
            check(f"{label} links My Work", 'href="/my-work"' in dom or ">My Work<" in dom)
            check(f"{label} no sideways scroll", 'data-overflow="no"' in dom, "overflow missing")
            if path == "/bzg/uma-blu":
                check(f"{label} engineering record hidden", 'id="engineering-record" hidden' in dom)
                check(f"{label} daily close link", ">Daily Close<" in dom)
                check(f"{label} says cannot pay", "cannot pay" in dom.lower() or "does not pay" in dom.lower())
    finally:
        _wipe_closer(drop_position)
        proxy.shutdown()
        httpd.shutdown()
        c = _live()
        try:
            left = c.execute(
                "SELECT person_id FROM org_persons WHERE person_id=?",
                (CLOSER_ID,),
            ).fetchone()
        finally:
            c.close()
        check("temporary closer removed", left is None)


def test_ports(prod_pid: str, beta_pid: str) -> None:
    def up(port: int) -> bool:
        s = socket.socket()
        s.settimeout(1.5)
        try:
            return s.connect_ex(("127.0.0.1", port)) == 0
        finally:
            s.close()

    check("prod 8787 up", up(8787))
    check("beta 8788 up", up(8788))
    check("prod pid unchanged", listener_pid(8787) == prod_pid and prod_pid != "", prod_pid)
    check("beta pid unchanged during test", listener_pid(8788) == beta_pid and beta_pid != "", beta_pid)


def main() -> int:
    prod = listener_pid(8787)
    beta = listener_pid(8788)
    print(f"prod pid {prod or 'down'}")
    print(f"beta pid {beta or 'down'}")
    test_chain()
    test_phone()
    test_ports(prod, beta)
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
