#!/usr/bin/env python3
"""CAP-FIN-01 core read. No typed balance. No Atrium book is opened.

A green read does not open the books. The ledger stays BUILT.
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

from core import fin_accounting_core as core  # noqa: E402
from core.canonical_guard import CanonicalGuardError, assert_write_allowed  # noqa: E402

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


def _stat(path: Path) -> tuple[bool, int | None, int | None]:
    if not path.is_file():
        return False, None, None
    st = path.stat()
    return True, st.st_size, st.st_mtime_ns


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


def _public(path: str) -> tuple[int, str, str]:
    conn = HTTPSConnection(PUBLIC_HOST, timeout=15)
    try:
        conn.request("GET", path, headers={"User-Agent": "wolf-p1-fin-01"})
        resp = conn.getresponse()
        resp.read(256)
        status = int(resp.status)
        location = resp.getheader("Location") or ""
        server = resp.getheader("Server") or ""
    finally:
        conn.close()
    return status, location, server


def _canonical() -> tuple[int, int, int, str | None, int]:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        evidence = int(conn.execute("SELECT COUNT(*) FROM core_evidence_records").fetchone()[0])
        exceptions = int(
            conn.execute("SELECT COUNT(*) FROM core_governance_exceptions").fetchone()[0]
        )
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
            (core.CAP_ID,),
        ).fetchone()
    finally:
        conn.close()
    return (
        evidence,
        exceptions,
        approvals,
        None if status is None else str(status[0]),
        int(resolved[0] if resolved else 0),
    )


def _closed(report: dict) -> bool:
    return (
        report.get("books_opened") is False
        and report.get("green_test_opens_books") is False
        and report.get("sample_opened") is False
        and report.get("typed_balance_closes_row") is False
        and report.get("amounts_parsed") is False
        and report.get("journals_read") is False
        and report.get("journal_count") is None
        and report.get("consolidation_figure") is None
        and report.get("balance") is None
        and report.get("payment_executed") is False
        and report.get("books_written") is False
        and report.get("ledger_write") is False
        and report.get("cr_resolved") is False
        and report.get("books_source") == "UNAVAILABLE"
        and report.get("staff_ready") is False
        and report.get("human_commissioned") is False
        and report.get("proven") is False
        and report.get("ready") is False
    )


def _expect(name: str, fn, code: str) -> None:
    try:
        fn()
    except core.AccountingCoreError as exc:
        check(name, exc.code == code, exc.code)
        return
    check(name, False, "no error")


def test_refuses() -> None:
    _expect("typed balance is refused", lambda: core.read_accounting_core(balance="1"), "balance_refused")
    _expect("zero balance is refused", lambda: core.read_accounting_core(balance=0), "balance_refused")
    _expect("typed amount is refused", lambda: core.read_accounting_core(amount="9"), "balance_refused")
    _expect("typed books figure is refused", lambda: core.read_accounting_core(books="9"), "balance_refused")
    _expect("opening figure is refused", lambda: core.read_accounting_core(opening="1"), "balance_refused")
    _expect("closing figure is refused", lambda: core.read_accounting_core(closing=0), "balance_refused")
    _expect("payment argument is refused", lambda: core.read_accounting_core(payment="1"), "payment_refused")
    _expect("open books flag is refused", lambda: core.read_accounting_core(open_books=True), "books_open_refused")
    _expect(
        "open books path is refused",
        lambda: core.read_accounting_core(open_books="data/atrium.sqlite"),
        "books_open_refused",
    )
    calls = [
        line
        for line in inspect.getsource(core.read_accounting_core).splitlines()
        if "sqlite3.connect" in line and not line.strip().startswith("#")
    ]
    check("atrium path is not passed to sqlite", calls == [], " ".join(calls))
    check("catalog open is read-only", "mode=ro" in inspect.getsource(core._ro))
    check("reader does not select a legal name", "legal_name" not in inspect.getsource(core._entities))
    try:
        assert_write_allowed(CATALOG)
    except CanonicalGuardError as exc:
        check("guard refuses canonical write", "test process refuses canonical Beta write" in str(exc))
    else:
        check("guard refuses canonical write", False, "no raise")


def test_live(before_ledger: str, before_canon: tuple, before_sample: tuple, before_live: tuple) -> None:
    real_connect = sqlite3.connect

    def guarded(target, *args, **kwargs):
        text = str(target)
        if "atrium-finance" in text or "atrium.sqlite" in text:
            raise AssertionError("atrium books were opened")
        return real_connect(target, *args, **kwargs)

    sqlite3.connect = guarded
    try:
        report = core.read_accounting_core(balance="")
    finally:
        sqlite3.connect = real_connect
    check("empty balance is not a typed balance", report.get("ok") is True and report.get("balance") is None)
    check("live read does not open books", _closed(report))
    check("ledger stays BUILT", report.get("ledger_state") == "BUILT", str(report.get("ledger_state")))
    check("ledger digest unchanged", _ledger_digest() == before_ledger)
    check("canonical counts unchanged", _canonical() == before_canon, str(_canonical()))
    check("catalog was read", report.get("catalog_read") is True)
    check("three legal entities", report.get("entity_count") == 3, str(report.get("entity_count")))
    ids = [row.get("entity_id") for row in report.get("entities") or []]
    check("entities are the stored three", ids == ["ENT-AMG", "ENT-BZG", "ENT-GGV"], str(ids))
    check(
        "each entity books source is unavailable",
        all(row.get("books_source") == "UNAVAILABLE" and row.get("consolidation_figure") is None for row in report["entities"]),
    )
    check("no consolidation map is stored", report.get("mapping_stored") is False and report.get("mapping_rows") is None)
    check("finance display is unavailable", report.get("finance_display") == "UNAVAILABLE", str(report.get("finance_display")))
    check("finance is not shown as current", report.get("finance_shown_as_current") is False)
    check("commissioned books file is absent", report.get("commissioned_books_present") is False)
    check("sample file is present and not opened", report.get("sample_present") is True and report.get("sample_opened") is False)
    check("sample file stat unchanged", _stat(core.SAMPLE_BOOKS) == before_sample)
    check("commissioned path still absent", _stat(core.COMMISSIONED_BOOKS) == before_live == (False, None, None))
    check("completion row stays open", report.get("cr_id") == core.CR_ID and report.get("cr_state") == "OPEN")
    check("completion row was not resolved", _canonical()[4] == 0)
    print(
        "NOTE  "
        f"entities={report['entity_count']} display={report['finance_display']} "
        f"books_source={report['books_source']} books_opened={report['books_opened']} "
        f"sample_present={report['sample_present']} commissioned_present={report['commissioned_books_present']} "
        f"cr={report['cr_state']}"
    )


def test_fixture_does_not_open(before_sample: tuple) -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    path = TMP / "cap-fin-01-entities.sqlite"
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "CREATE TABLE org_entities (entity_id TEXT, entity_type TEXT, status TEXT)"
        )
        conn.execute(
            "INSERT INTO org_entities VALUES ('ENT-FIXTURE', 'LEGAL_ENTITY', 'LIVE')"
        )
        conn.commit()
    finally:
        conn.close()
    report = core.read_accounting_core(path)
    check("fixture entity is not a books open", _closed(report))
    check("fixture does not become the live entity count", report.get("entity_count") == 1)
    check("fixture books source stays unavailable", report["entities"][0]["books_source"] == "UNAVAILABLE")
    check("fixture did not open the sample", _stat(core.SAMPLE_BOOKS) == before_sample and report["sample_opened"] is False)
    path.unlink()


def test_routes(beta_pid: str) -> None:
    health, _ = _origin("GET", "/api/health")
    check("beta health 200", health == 200, str(health))
    cases = (
        ("GET", "/api/fin/mgmt-reporting", None),
        ("GET", "/api/owner/command", None),
        ("GET", "/api/owner/command?balance=1", None),
        ("GET", "/api/fin/mgmt-reporting", {"Cf-Access-Authenticated-User-Email": SPOOF}),
        ("GET", "/api/owner/command", {"X-Wolf-Subject": "PERS-MATT"}),
        ("GET", "/api/owner/command", {"Cf-Access-Jwt-Assertion": BAD_JWT}),
        ("POST", "/api/fin/mgmt-reporting/books", None),
    )
    for method, path, headers in cases:
        status, body = _origin(method, path, headers)
        check(f"unsigned {method} {path} denied", status == 403, str(status))
        check(
            f"unsigned {method} {path} is not a balance",
            body.get("balance") is None and body.get("books_opened") is not True,
        )
    prod_health, _ = _origin_port(8787, "/api/health")
    check("prod health 200", prod_health == 200, str(prod_health))
    check("prod pid unchanged", _listener(PROD_PID).endswith("serve.py 8787"), _listener(PROD_PID))
    check("beta pid unchanged", _beta_pid() == beta_pid, _beta_pid())
    status, location, server = _public("/api/owner/command")
    check("public owner command redirects", status == 302, str(status))
    check("public redirect is access", "cloudflareaccess.com" in location, location.split("?")[0])
    check("public server is cloudflare", "cloudflare" in server.lower(), server)


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


def main() -> int:
    before_ledger = _ledger_digest()
    before_canon = _canonical()
    before_sample = _stat(core.SAMPLE_BOOKS)
    before_live = _stat(core.COMMISSIONED_BOOKS)
    beta_pid = _beta_pid()
    test_refuses()
    test_live(before_ledger, before_canon, before_sample, before_live)
    test_fixture_does_not_open(before_sample)
    test_routes(beta_pid)
    evidence, exceptions, approvals, status, resolved = _canonical()
    print(
        "COUNTS "
        f"evidence={evidence} exceptions={exceptions} approvals={approvals} "
        f"evidence_status={status} fin01_resolved={resolved}"
    )
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
