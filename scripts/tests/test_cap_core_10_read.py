#!/usr/bin/env python3
"""CAP-CORE-10 stored exception read, without a new row.

Owner Command lists the stored governance exceptions. It does not insert
one. A review cadence is not marked done. Unsigned, spoofed, and bad-JWT
callers stay denied on Beta. A seated read is not minted. The ledger is
not raised.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import owner_command as oc  # noqa: E402
from core import owner_empire_pack as empire  # noqa: E402

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
PAGE = ROOT / "dashboards" / "owner-empire-pack.html"
CR_ID = "CR-f9aee8803a25b5ee"
PROD_PID = "15975"
ORIGIN = ("127.0.0.1", 8788)
PUBLIC_HOST = "beta.wolfcommand.net"
LOGIN_HOST = "wolfcommand.cloudflareaccess.com"
LOGIN_PATH = "/cdn-cgi/access/login/beta.wolfcommand.net"
PATHS = ("/api/owner/command", "/wolf")
STORED = (
    "GEX-a8165674-68a6-4033-ab5b-d310d7ded0cd",
    "GEX-0973743f-c838-4545-92c5-25fea51f21c8",
    "GEX-41967006-311f-4ab0-9802-1e6db54ce18e",
)
PERSON = "PERS-MATT"
EMAIL = "mrwolf@wolfcommand.net"
NAME = "Matt"
SPOOF_EMAIL = "spoofed@example.invalid"
BAD_JWT = "a.b.c"

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


def _ledger_digest() -> str:
    return hashlib.sha256(LEDGER.read_bytes()).hexdigest()


def _listener(pid: str) -> str:
    proc = subprocess.run(
        ["ps", "-p", pid, "-o", "command="],
        capture_output=True,
        text=True,
        check=False,
    )
    return (proc.stdout or "").strip()


def _beta_pid() -> str:
    proc = subprocess.run(
        ["lsof", "-nP", "-iTCP:8788", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
        check=False,
    )
    for line in (proc.stdout or "").splitlines():
        if "127.0.0.1:8788" not in line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            return parts[1]
    return ""


def _live() -> tuple[int, tuple[tuple[str, str, str], ...], int, str]:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        count = int(conn.execute("SELECT COUNT(*) FROM core_governance_exceptions").fetchone()[0])
        rows = tuple(
            (str(row[0]), str(row[1]), str(row[2]))
            for row in conn.execute(
                """
                SELECT exception_id, status, entity_id
                FROM core_governance_exceptions
                ORDER BY created_at, exception_id
                """
            ).fetchall()
        )
        audits = int(conn.execute("SELECT COUNT(*) FROM core_audit_events").fetchone()[0])
        trigger = conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='trigger' AND name='trg_core_governance_exceptions_no_delete'
            """
        ).fetchone()
        return count, rows, audits, str(trigger[0] if trigger else "")
    finally:
        conn.close()


def _origin(method: str, path: str, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    conn = HTTPConnection(ORIGIN[0], ORIGIN[1], timeout=8)
    try:
        conn.request(method, path, body=b"{}" if method == "POST" else None, headers=headers or {})
        resp = conn.getresponse()
        raw = resp.read(4096)
        status = int(resp.status)
    finally:
        conn.close()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    return status, parsed


def _public(path: str) -> tuple[int, str, str, str]:
    conn = HTTPSConnection(PUBLIC_HOST, timeout=15)
    try:
        conn.request("GET", path, headers={"User-Agent": "wolf-p0-exceptions"})
        resp = conn.getresponse()
        resp.read(256)
        status = int(resp.status)
        location = resp.getheader("Location") or ""
        www = resp.getheader("WWW-Authenticate") or ""
        server = resp.getheader("Server") or ""
    finally:
        conn.close()
    return status, location, www, server


def test_listeners(beta_pid: str) -> None:
    prod = _listener(PROD_PID)
    check("prod pid 15975 still serve.py", "serve.py" in prod and "8787" in prod, prod[:160])
    check("beta pid listening", bool(beta_pid), "no listener")
    beta = _listener(beta_pid) if beta_pid else ""
    check("beta command is serve_beta.py", "serve_beta.py" in beta, beta[:160])


def test_read_shows_stored(live_before: tuple[int, tuple[tuple[str, str, str], ...], int, str]) -> None:
    count, rows, _audits, trigger = live_before
    check("live exception count is 3", count == 3, str(count))
    check("no-delete trigger remains", trigger == "trg_core_governance_exceptions_no_delete", trigger)
    ids = tuple(row[0] for row in rows)
    check("stored ids are the three observed rows", ids == STORED, str(ids))
    check("every stored row is REJECTED", all(row[1] == "REJECTED" for row in rows), str(rows))
    check("every stored row is ENT-GGV", all(row[2] == "ENT-GGV" for row in rows), str(rows))

    try:
        oc.build_command(verified_person_id=EMAIL)
        check("email string is not an owner read", False, "email was allowed")
    except empire.EmpirePackError as exc:
        check("email string is not an owner read", exc.code == "forbidden", exc.code)
    try:
        oc.build_command(verified_person_id=NAME)
        check("display name is not an owner read", False, "name was allowed")
    except empire.EmpirePackError as exc:
        check("display name is not an owner read", exc.code == "forbidden", exc.code)

    report = oc.build_command(verified_person_id=PERSON)
    block = report.get("exceptions") or {}
    items = block.get("items") or []
    shown = tuple(str(item.get("id")) for item in items)
    print("NOTE  shown=" + ",".join(shown))
    print(
        f"NOTE  stored_count={block.get('stored_count')} open_count={block.get('open_count')} "
        f"cadence_done={block.get('cadence_done')}"
    )
    check("read is READ", block.get("read") == "READ", str(block.get("read")))
    check("stored count is 3", block.get("stored_count") == 3, str(block.get("stored_count")))
    check("open count is 0", block.get("open_count") == 0, str(block.get("open_count")))
    check("cadence is not done", block.get("cadence_done") is False, str(block.get("cadence_done")))
    check("empty sentence is absent", block.get("empty_message") is None, str(block.get("empty_message")))
    check("shown ids match the stored rows", shown == tuple(reversed(STORED)), str(shown))
    check(
        "each shown state is REJECTED",
        len(items) == 3 and all(item.get("state") == "REJECTED" for item in items),
        str([item.get("state") for item in items]),
    )
    check(
        "severity stays MISSING",
        all(item.get("severity") == "MISSING" and item.get("escalation_state") == "MISSING" for item in items),
    )
    cards = {card.get("code"): card for card in report.get("companies") or []}
    ggv = ((cards.get("GGV") or {}).get("exceptions") or {})
    check("GGV card count is the stored rows", ggv.get("state") == "READ" and ggv.get("value") == 3, str(ggv))
    for code in ("AMG", "BZG"):
        card = ((cards.get(code) or {}).get("exceptions") or {})
        check(
            f"{code} card count is 0",
            card.get("state") == "READ" and card.get("value") == 0,
            str(card),
        )
    waiting = [
        item
        for item in (report.get("needs_you") or {}).get("items") or []
        if item.get("kind") == "exception"
    ]
    check("needs you does not list the rejected rows", waiting == [], str([item.get("id") for item in waiting]))
    check("staff ready stays false", report.get("staff_ready") is False)
    check("human commissioned stays false", report.get("human_commissioned") is False)
    wrong = next((row.get("answer") for row in report.get("answers") or [] if row.get("id") == "wrong"), "")
    check(
        "answer names the stored count",
        wrong.startswith("3 governance exceptions are on record."),
        wrong[:120],
    )
    page = PAGE.read_text(encoding="utf-8")
    check("page shows the exception id", "esc(item.id)" in page)
    check("page shows stored and open counts", "ex.stored_count" in page and "ex.open_count" in page)
    check("page does not mark the cadence done by default", 'cadence_done === true ? "done" : "not done"' in page)


def test_origin_denies() -> None:
    cases = (
        ("unsigned", None, "missing_auth"),
        ("spoofed email", {"Cf-Access-Authenticated-User-Email": SPOOF_EMAIL}, "missing_auth"),
        ("spoofed subject", {"X-Wolf-Subject": PERSON}, "missing_auth"),
        ("bad jwt", {"Cf-Access-Jwt-Assertion": BAD_JWT}, "invalid_token"),
    )
    for path in PATHS:
        for label, headers, wolf_error in cases:
            status, body = _origin("GET", path, headers)
            print(f"NOTE  {label} {path} status={status} error={body.get('error')}")
            expect = "forbidden" if path == "/api/owner/command" else wolf_error
            check(
                f"{label} GET {path} 403 {expect}",
                status == 403
                and body.get("error") == expect
                and body.get("ok") is not True
                and "exceptions" not in body,
                f"status={status} error={body.get('error')} keys={sorted(body)[:8]}",
            )
    status, body = _origin("POST", "/api/owner/command", {"Content-Type": "application/json"})
    check(
        "unsigned POST /api/owner/command denied",
        status == 403 and body.get("ok") is not True and "exceptions" not in body,
        f"status={status} error={body.get('error')}",
    )


def test_public_login() -> None:
    for path in PATHS:
        status, location, www, server = _public(path)
        parts = urlsplit(location)
        check(
            f"public {path} login redirect",
            status == 302
            and parts.scheme == "https"
            and parts.hostname == LOGIN_HOST
            and parts.path == LOGIN_PATH
            and www.startswith("Cloudflare-Access")
            and server.lower() == "cloudflare",
            f"status={status} host={parts.hostname} path={parts.path} server={server}",
        )


def test_ledger(before: str, live_before: tuple[int, tuple[tuple[str, str, str], ...], int, str]) -> None:
    live_after = _live()
    print(f"NOTE  live_exceptions_after={live_after[0]} live_audits_after={live_after[2]}")
    check("live exception count unchanged", live_after[0] == live_before[0] == 3, str(live_after[0]))
    check("live exception rows unchanged", live_after[1] == live_before[1], str(live_after[1]))
    added = live_after[2] - live_before[2]
    check(
        "deny probes are the only new audits",
        added == 9,
        str(added),
    )
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        newest = conn.execute(
            """
            SELECT action, result, source
            FROM core_audit_events
            ORDER BY rowid DESC
            LIMIT ?
            """,
            (added,),
        ).fetchall()
    finally:
        conn.close()
    check(
        "new audits are auth.resolve DENIED",
        added == 9 and all(tuple(row) == ("auth.resolve", "DENIED", "cf_access") for row in newest),
        str(newest[:3]),
    )
    check("ledger digest unchanged", _ledger_digest() == before)
    ledger = json.loads(LEDGER.read_text())
    row = ledger.get("CAP-CORE-10") or []
    check("ledger CAP-CORE-10 stays PROVEN", bool(row) and row[0] == "PROVEN", str(row[:1]))
    check("ledger length stays 77", len(ledger) == 77, str(len(ledger)))
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        found = conn.execute(
            "SELECT state, capability FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
        check(
            f"{CR_ID} stays OPEN",
            found is not None and found[0] == "OPEN" and found[1] == "CAP-CORE-10",
            str(found),
        )
    finally:
        conn.close()


def main() -> int:
    before = _ledger_digest()
    live_before = _live()
    beta_pid = _beta_pid()
    print(f"NOTE  beta_pid={beta_pid or 'absent'} prod_pid={PROD_PID}")
    print(f"NOTE  live_exceptions={live_before[0]} live_audits={live_before[2]}")
    test_listeners(beta_pid)
    test_read_shows_stored(live_before)
    test_origin_denies()
    test_public_login()
    test_ledger(before, live_before)
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
