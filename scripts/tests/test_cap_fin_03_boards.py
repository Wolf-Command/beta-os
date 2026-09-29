#!/usr/bin/env python3
"""CAP-FIN-03 entity finance boards. No new person. The accountant seat stays empty.

A green matrix does not seat anyone and does not open the books.
The ledger stays BUILT.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sqlite3
import subprocess
import sys
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)
os.environ.pop("WOLF_CANONICAL_WRITE_OVERRIDE", None)

from core import fin_entity_boards as boards  # noqa: E402
from core.canonical_guard import CanonicalGuardError, assert_write_allowed  # noqa: E402
from core.ggv_finance_nota import (  # noqa: E402
    OPERATING_ROLES,
    POSITION_EXTERNAL_ACCOUNTANT,
    ROLE_EXTERNAL_ACCOUNTANT,
)

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
TMP = ROOT / "state" / "build-factory" / "tmp-f1"
PROD_PID = "15975"
ORIGIN = ("127.0.0.1", 8788)
PUBLIC_HOST = "beta.wolfcommand.net"
EVIDENCE_ID = "EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153"
SPOOF = "spoofed@example.invalid"
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


def _origin_port(port: int, path: str) -> tuple[int, dict]:
    conn = HTTPConnection("127.0.0.1", port, timeout=8)
    try:
        conn.request("GET", path)
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


def _public(path: str) -> tuple[int, str, str]:
    conn = HTTPSConnection(PUBLIC_HOST, timeout=15)
    try:
        conn.request("GET", path, headers={"User-Agent": "wolf-p1-fin-03"})
        resp = conn.getresponse()
        resp.read(256)
        status = int(resp.status)
        location = resp.getheader("Location") or ""
        server = resp.getheader("Server") or ""
    finally:
        conn.close()
    return status, location, server


def _canonical() -> tuple[int, int, int, str | None, int, int, int]:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        evidence = int(conn.execute("SELECT COUNT(*) FROM core_evidence_records").fetchone()[0])
        exceptions = int(conn.execute("SELECT COUNT(*) FROM core_governance_exceptions").fetchone()[0])
        approvals = int(conn.execute("SELECT COUNT(*) FROM core_approval_decisions").fetchone()[0])
        status = conn.execute(
            "SELECT status FROM core_evidence_records WHERE evidence_id=?",
            (EVIDENCE_ID,),
        ).fetchone()
        resolved = conn.execute(
            """
            SELECT COUNT(*) FROM wolf_completion_items
            WHERE capability=? AND state='RESOLVED'
            """,
            (boards.CAP_ID,),
        ).fetchone()
        persons = int(conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0])
        assignments = int(conn.execute("SELECT COUNT(*) FROM org_assignments").fetchone()[0])
    finally:
        conn.close()
    return (
        evidence,
        exceptions,
        approvals,
        None if status is None else str(status[0]),
        int(resolved[0] if resolved else 0),
        persons,
        assignments,
    )


def _closed(report: dict) -> bool:
    return (
        report.get("books_opened") is False
        and report.get("green_test_opens_books") is False
        and report.get("green_test_seats_accountant") is False
        and report.get("sample_opened") is False
        and report.get("typed_balance_closes_row") is False
        and report.get("amounts_parsed") is False
        and report.get("payment_executed") is False
        and report.get("person_created") is False
        and report.get("assignment_created") is False
        and report.get("ledger_write") is False
        and report.get("cr_resolved") is False
        and report.get("money") is None
        and report.get("staff_ready") is False
        and report.get("human_commissioned") is False
        and report.get("proven") is False
        and report.get("ready") is False
    )


def _expect(name: str, fn, code: str) -> None:
    try:
        fn()
    except boards.EntityBoardError as exc:
        check(name, exc.code == code, exc.code)
        return
    check(name, False, "no error")


def _source_lines(fn) -> list[str]:
    return [
        line
        for line in inspect.getsource(fn).splitlines()
        if not line.strip().startswith("#")
    ]


def test_refuses() -> None:
    _expect("typed balance is refused", lambda: boards.read_entity_finance_boards(balance="1"), "balance_refused")
    _expect("zero balance is refused", lambda: boards.read_entity_finance_boards(balance=0), "balance_refused")
    _expect("typed amount is refused", lambda: boards.read_entity_finance_boards(amount="9"), "balance_refused")
    _expect("payment argument is refused", lambda: boards.read_entity_finance_boards(payment="1"), "payment_refused")
    _expect("open books flag is refused", lambda: boards.read_entity_finance_boards(open_books=True), "books_open_refused")
    _expect("seat argument is refused", lambda: boards.read_entity_finance_boards(seat="PERS-X"), "seat_refused")
    _expect("person argument is refused", lambda: boards.read_entity_finance_boards(person="PERS-X"), "seat_refused")
    _expect("assign argument is refused", lambda: boards.read_entity_finance_boards(assign=True), "seat_refused")
    body = "\n".join(_source_lines(boards.read_entity_finance_boards))
    check("reader has no insert", "INSERT" not in body.upper())
    check("reader has no update", "UPDATE " not in body.upper())
    check("reader has no delete", "DELETE" not in body.upper())
    ro_src = "\n".join(_source_lines(boards._ro))
    check("catalog open is read-only", "mode=ro" in ro_src and "sqlite3.connect" in ro_src)
    check("seat constants match the finance module", boards.POSITION_EXTERNAL_ACCOUNTANT == POSITION_EXTERNAL_ACCOUNTANT)
    check("role constant matches the finance module", boards.ROLE_EXTERNAL_ACCOUNTANT == ROLE_EXTERNAL_ACCOUNTANT)
    check("content role is an operating role", boards.CONTENT_ROLE in OPERATING_ROLES)
    check("content role is not the accountant role", boards.CONTENT_ROLE != ROLE_EXTERNAL_ACCOUNTANT)
    try:
        assert_write_allowed(CATALOG)
    except CanonicalGuardError as exc:
        check("guard refuses canonical write", "test process refuses canonical Beta write" in str(exc))
    else:
        check("guard refuses canonical write", False, "no raise")


def test_live(before_ledger: str, before_canon: tuple) -> None:
    report = boards.read_entity_finance_boards(balance="")
    check("empty balance is not a typed balance", report.get("ok") is True and report.get("money") is None)
    check("live matrix does not seat or open books", _closed(report))
    check("ledger stays BUILT", report.get("ledger_state") == "BUILT", str(report.get("ledger_state")))
    check("ledger digest unchanged", _ledger_digest() == before_ledger)
    check("canonical counts unchanged", _canonical() == before_canon, str(_canonical()))
    check("one shared matrix", report.get("shared") is True and report.get("board_count") == 3)
    check(
        "three stored entities are covered",
        report.get("entities_covered") == ["ENT-GGV", "ENT-AMG", "ENT-BZG"],
        str(report.get("entities_covered")),
    )
    check("no entity is missing", report.get("entities_missing") == [])
    by_id = {row["board_id"]: row for row in report["boards"]}
    ggv = by_id["GGV"]
    atrium = by_id["ATRIUM"]
    uma = by_id["UMA"]
    check("ggv desk is the notes page", ggv["href"] == "/ggv/finance" and ggv["kind"] == "notes")
    check("ggv sentence is present", ggv["page_present"] is True and ggv["sentence_present"] is True)
    check("ggv notas are stored zeros and not cash", ggv["nota_rows"] == 0 and ggv["vendor_rows"] == 0 and ggv["nota_rows_are_cash"] is False)
    check("ggv money is null", ggv["money"] is None and ggv["cash_figure"] is None and ggv["books_source"] == "UNAVAILABLE")
    check("atrium desk is the closed hotel page", atrium["href"] == "/amg-ops-pack" and atrium["kind"] == "closed_desk")
    check("atrium sentence is present", atrium["sentence_present"] is True)
    check("atrium books file is absent and unopened", atrium["commissioned_books_present"] is False and atrium["sample_opened"] is False)
    check("uma desk is operations under ENT-BZG", uma["entity_id"] == "ENT-BZG" and uma["kind"] == "operations")
    check("uma sentence is present", uma["sentence_present"] is True)
    # MYWORK-1 seated Devi on ROLE-BZG-CLOSER; this read still does not invent a seat.
    check(
        "uma closer roster is live and not invented by this read",
        uma["closer_active_assignments"] >= 1 and uma["closer_seated_by_this_read"] is False,
        str(uma.get("closer_active_assignments")),
    )
    check("uma money is null", uma["money"] is None and uma["books_source"] == "UNAVAILABLE")
    check("accountant position is stored on GGV", report["accountant_position_stored"] is True and report["accountant_entity_id"] == "ENT-GGV")
    check("accountant seat is empty", report["accountant_seat_empty"] is True and report["accountant_active_assignments"] == 0)
    content = report["content_assignments"]
    check("one content-management assignment is stored", len(content) == 1, str(content))
    check(
        "content assignment is not the accountant seat",
        content[0]["assignment_id"] == "ASG-AMANDA-CM-1"
        and content[0]["position_id"] == "POS-CONTENT-MGMT-1"
        and content[0]["role_id"] == boards.CONTENT_ROLE
        and report["content_assignment_is_accountant_seat"] is False
        and report["content_assignment_is_accountant_role"] is False,
        str(content),
    )
    check("finance display stays unavailable", report.get("finance_display") == "UNAVAILABLE", str(report.get("finance_display")))
    check("engineering row stays open", report.get("cr_id") == boards.ENGINEERING_CR and report.get("engineering_state") == "OPEN")
    check("four completion rows stay open", report.get("cr_open") == 4 and report.get("cr_resolved_count") == 0)
    check("no completion row was resolved", _canonical()[4] == 0)
    print(
        "NOTE  "
        f"boards={report['board_count']} seat_empty={report['accountant_seat_empty']} "
        f"accountant_active={report['accountant_active_assignments']} "
        f"content_is_seat={report['content_assignment_is_accountant_seat']} "
        f"display={report['finance_display']} cr_open={report['cr_open']}"
    )


def test_fixture_does_not_seat(before_canon: tuple) -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    path = TMP / "cap-fin-03-boards.sqlite"
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE org_entities (entity_id TEXT, entity_type TEXT, status TEXT)")
        conn.execute("CREATE TABLE org_positions (position_id TEXT, role_id TEXT, entity_id TEXT, status TEXT)")
        conn.execute(
            """
            CREATE TABLE org_assignments (
              assignment_id TEXT, position_id TEXT, status TEXT, end_at TEXT
            )
            """
        )
        conn.execute("INSERT INTO org_entities VALUES ('ENT-GGV', 'LEGAL_ENTITY', 'LIVE')")
        conn.execute("INSERT INTO org_entities VALUES ('ENT-AMG', 'LEGAL_ENTITY', 'LIVE')")
        conn.execute("INSERT INTO org_entities VALUES ('ENT-BZG', 'LEGAL_ENTITY', 'LIVE')")
        conn.execute(
            "INSERT INTO org_positions VALUES (?, ?, 'ENT-GGV', 'ACTIVE')",
            (boards.POSITION_EXTERNAL_ACCOUNTANT, boards.ROLE_EXTERNAL_ACCOUNTANT),
        )
        conn.commit()
    finally:
        conn.close()
    empty = boards.read_entity_finance_boards(path, balance="")
    check("fixture without an assignment stays empty", empty.get("accountant_seat_empty") is True)
    check("fixture does not create a person", empty.get("person_created") is False and _closed(empty))
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "INSERT INTO org_assignments VALUES ('ASG-FIXTURE-ACCT', ?, 'ACTIVE', NULL)",
            (boards.POSITION_EXTERNAL_ACCOUNTANT,),
        )
        conn.commit()
    finally:
        conn.close()
    occupied = boards.read_entity_finance_boards(path, balance="")
    check(
        "fixture assignment is read and not written back",
        occupied.get("accountant_active_assignments") == 1 and occupied.get("accountant_seat_empty") is False,
    )
    check("fixture read still creates nobody", occupied.get("person_created") is False and occupied.get("assignment_created") is False)
    live = boards.read_entity_finance_boards(balance="")
    check("live seat stays empty after the fixture", live.get("accountant_seat_empty") is True and live.get("accountant_active_assignments") == 0)
    check("live counts unchanged after the fixture", _canonical() == before_canon, str(_canonical()))
    path.unlink()


def test_routes(beta_pid: str) -> None:
    health, _ = _origin("GET", "/api/health")
    check("beta health 200", health == 200, str(health))
    cases = (
        ("GET", "/ggv/finance", None),
        ("GET", "/amg-ops-pack", None),
        ("GET", "/bzg/uma-blu", None),
        ("GET", "/bzg/uma-blu/bills", None),
        ("GET", "/ggv/finance", {"Cf-Access-Authenticated-User-Email": SPOOF}),
        ("GET", "/ggv/finance", {"X-Wolf-Subject": "PERS-MATT"}),
        ("GET", "/amg-ops-pack", {"Cf-Access-Jwt-Assertion": BAD_JWT}),
        ("POST", "/api/ggv/finance/pay", None),
    )
    for method, path, headers in cases:
        status, body = _origin(method, path, headers)
        check(f"unsigned {method} {path} denied", status == 403, str(status))
        check(
            f"unsigned {method} {path} is not a seated board",
            body.get("accountant_seat_empty") is not True and body.get("money") is None,
        )
    prod_health, _ = _origin_port(8787, "/api/health")
    check("prod health 200", prod_health == 200, str(prod_health))
    check("prod pid unchanged", _listener(PROD_PID).endswith("serve.py 8787"), _listener(PROD_PID))
    check("beta pid unchanged", _beta_pid() == beta_pid, _beta_pid())
    status, location, server = _public("/ggv/finance")
    check("public finance redirects", status == 302, str(status))
    check("public redirect is access", "cloudflareaccess.com" in location, location.split("?")[0])
    check("public server is cloudflare", "cloudflare" in server.lower(), server)


def main() -> int:
    before_ledger = _ledger_digest()
    before_canon = _canonical()
    beta_pid = _beta_pid()
    test_refuses()
    test_live(before_ledger, before_canon)
    test_fixture_does_not_seat(before_canon)
    test_routes(beta_pid)
    evidence, exceptions, approvals, status, resolved, persons, assignments = _canonical()
    print(
        "COUNTS "
        f"evidence={evidence} exceptions={exceptions} approvals={approvals} "
        f"evidence_status={status} fin03_resolved={resolved} persons={persons} assignments={assignments}"
    )
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
