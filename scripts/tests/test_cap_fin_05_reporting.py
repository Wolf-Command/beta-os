#!/usr/bin/env python3
"""CAP-FIN-05 management report. Books stay unopened, so the report says unavailable.

A typed statement does not close this row. The ledger stays SPECIFIED.
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

from core import fin_mgmt_reporting as core  # noqa: E402
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
FIGURE_KEYS = (
    "pnl",
    "pnl_number",
    "balance_sheet",
    "balance_sheet_number",
    "cash_flow",
    "cash_flow_number",
    "cash",
    "trial_balance",
    "statement",
)

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
        conn.request("GET", path, headers={"User-Agent": "wolf-p1-fin-05"})
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


def _unavailable(report: dict) -> bool:
    figures = all(report.get(key) is None for key in FIGURE_KEYS)
    kinds = report.get("kinds") or []
    kind_figures = True
    for row in kinds:
        if not isinstance(row, dict):
            kind_figures = False
            break
        for key in ("pnl", "pnl_number", "balance_sheet", "balance_sheet_number", "cash_flow", "cash_flow_number"):
            if row.get(key) is not None:
                kind_figures = False
    return (
        figures
        and kind_figures
        and report.get("ok") is True
        and report.get("cap") == core.CAP_ID
        and report.get("report_state") == "UNAVAILABLE"
        and report.get("unavailable_is_a_statement") is False
        and report.get("books_source") == "UNAVAILABLE"
        and report.get("books_opened") is False
        and report.get("statements_rendered") is False
        and report.get("green_test_renders_pack") is False
        and report.get("typed_figure_closes_row") is False
        and report.get("sample_opened") is False
        and report.get("payment_executed") is False
        and report.get("books_written") is False
        and report.get("ledger_write") is False
        and report.get("cr_resolved") is False
        and report.get("staff_ready") is False
        and report.get("human_commissioned") is False
        and report.get("operating_adoption") == "NOT MEASURED"
        and report.get("proven") is False
        and report.get("ready") is False
        and report.get("score_changed") is False
    )


def _expect(name: str, fn, code: str) -> None:
    try:
        fn()
    except core.FinMgmtReportingError as exc:
        check(name, exc.code == code, exc.code)
        return
    check(name, False, "no error")


def test_refuses() -> None:
    _expect("typed pnl is refused", lambda: core.read_management_report(pnl="1"), "current_refused")
    _expect("zero pnl is refused", lambda: core.read_management_report(pnl=0), "current_refused")
    _expect("typed balance sheet is refused", lambda: core.read_management_report(balance_sheet="9"), "current_refused")
    _expect("zero balance sheet is refused", lambda: core.read_management_report(balance_sheet_number=0), "current_refused")
    _expect("typed cash flow is refused", lambda: core.read_management_report(cash_flow="1"), "current_refused")
    _expect("typed cash is refused", lambda: core.read_management_report(cash=0), "current_refused")
    _expect("typed statement is refused", lambda: core.read_management_report(statement="sample"), "current_refused")
    _expect("typed trial balance is refused", lambda: core.read_management_report(trial_balance="1"), "current_refused")
    _expect("typed balance is refused", lambda: core.read_management_report(balance="1"), "current_refused")
    _expect("typed amount is refused", lambda: core.read_management_report(amount=0), "current_refused")
    _expect("payment argument is refused", lambda: core.read_management_report(payment="1"), "payment_refused")
    _expect("open books flag is refused", lambda: core.read_management_report(open_books=True), "books_open_refused")
    _expect(
        "open books path is refused",
        lambda: core.read_management_report(open_books="data/atrium.sqlite"),
        "books_open_refused",
    )
    body = inspect.getsource(core.read_management_report)
    check("report function does not connect sqlite", "sqlite3.connect" not in body)
    check("report function does not name a production port", "8787" not in body)
    try:
        assert_write_allowed(CATALOG)
    except CanonicalGuardError as exc:
        check("guard refuses canonical write", "test process refuses canonical Beta write" in str(exc))
    else:
        check("guard refuses canonical write", False, "no raise")


def test_live(before_ledger: str, before_canon: tuple, before_sample: tuple, before_live: tuple) -> None:
    from core import fin_accounting_core as books

    real_connect = sqlite3.connect

    def guarded(target, *args, **kwargs):
        text = str(target)
        if "atrium-finance" in text or "atrium.sqlite" in text:
            raise AssertionError("atrium books were opened")
        return real_connect(target, *args, **kwargs)

    sqlite3.connect = guarded
    try:
        report = core.read_management_report(pnl="", cash="", statement="", balance="")
    finally:
        sqlite3.connect = real_connect
    check("empty figure strings are not a statement", _unavailable(report))
    check("ledger stays SPECIFIED", report.get("ledger_state") == "SPECIFIED", str(report.get("ledger_state")))
    check("ledger digest unchanged", _ledger_digest() == before_ledger)
    check("canonical counts unchanged", _canonical() == before_canon, str(_canonical()))
    check("finance display is unavailable", report.get("finance_display") == "UNAVAILABLE", str(report.get("finance_display")))
    check("finance is not shown as current", report.get("finance_shown_as_current") is False)
    check("commissioned books file is absent", report.get("commissioned_books_present") is False)
    check("sample file is present and not opened", report.get("sample_present") is True and report.get("sample_opened") is False)
    check("sample file stat unchanged", _stat(books.SAMPLE_BOOKS) == before_sample)
    check("commissioned path still absent", _stat(books.COMMISSIONED_BOOKS) == before_live == (False, None, None))
    check("recorded count is the empty framework", report.get("recorded_count") == 0)
    check("empty count is not cash", report.get("cash") is None and report.get("recorded_count") == 0)
    kinds = [row.get("kind") for row in report.get("kinds") or []]
    check(
        "named slots stay the framework five",
        kinds == ["pnl", "balance_sheet", "cash_flow", "checklist", "notes"],
        str(kinds),
    )
    check("completion row stays open", report.get("cr_id") == core.CR_ID and report.get("cr_state") == "OPEN")
    check("completion row was not resolved", report.get("resolved_rows") == 0 and _canonical()[4] == 0)
    check("live framework file stays absent", core.DEFAULT_DB.is_file() is False)
    print(
        "NOTE  "
        f"report={report['report_state']} display={report['finance_display']} "
        f"books_source={report['books_source']} books_opened={report['books_opened']} "
        f"statements_rendered={report['statements_rendered']} "
        f"sample_present={report['sample_present']} commissioned_present={report['commissioned_books_present']} "
        f"ledger={report['ledger_state']} cr={report['cr_state']}"
    )


def test_fixture_does_not_render(before_sample: tuple) -> None:
    from core import fin_accounting_core as books

    TMP.mkdir(parents=True, exist_ok=True)
    path = TMP / "cap-fin-05-report.sqlite"
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE org_entities (entity_id TEXT, entity_type TEXT, status TEXT)")
        conn.execute("INSERT INTO org_entities VALUES ('ENT-FIXTURE', 'LEGAL_ENTITY', 'LIVE')")
        conn.commit()
    finally:
        conn.close()
    report = core.read_management_report(path)
    check("fixture report stays unavailable", _unavailable(report))
    check("fixture did not open the sample", _stat(books.SAMPLE_BOOKS) == before_sample and report["sample_opened"] is False)
    check("fixture has no completion row to resolve", report.get("cr_present") is False and report.get("resolved_rows") is None)
    path.unlink()


def _not_a_statement(body: dict) -> bool:
    return all(body.get(key) is None for key in FIGURE_KEYS) and body.get("report_state") != "CURRENT"


def test_routes(beta_pid: str) -> None:
    health, _ = _origin("GET", "/api/health")
    check("beta health 200", health == 200, str(health))
    cases = (
        ("GET", "/api/fin/mgmt-reporting", None),
        ("GET", "/api/fin/mgmt-reporting?pnl=1", None),
        ("GET", "/fin-mgmt-reporting", None),
        ("GET", "/api/fin/mgmt-reporting", {"Cf-Access-Authenticated-User-Email": SPOOF}),
        ("GET", "/api/fin/mgmt-reporting", {"X-Wolf-Subject": "PERS-MATT"}),
        ("GET", "/api/fin/mgmt-reporting", {"Cf-Access-Jwt-Assertion": BAD_JWT}),
        ("POST", "/api/fin/mgmt-reporting/books", None),
        ("POST", "/api/fin/mgmt-reporting/current", None),
    )
    for method, path, headers in cases:
        status, body = _origin(method, path, headers)
        check(f"unsigned {method} {path} denied", status == 403, str(status))
        check(f"unsigned {method} {path} is not a statement", _not_a_statement(body))
    prod_health, _ = _origin_port(8787, "/api/health")
    check("prod health 200", prod_health == 200, str(prod_health))
    check("prod pid unchanged", _listener(PROD_PID).endswith("serve.py 8787"), _listener(PROD_PID))
    check("beta pid unchanged", _beta_pid() == beta_pid, _beta_pid())
    status, location, server = _public("/api/fin/mgmt-reporting")
    check("public management report redirects", status == 302, str(status))
    check("public redirect is access", "cloudflareaccess.com" in location, location.split("?")[0])
    check("public server is cloudflare", "cloudflare" in server.lower(), server)


def main() -> int:
    from core import fin_accounting_core as books

    before_ledger = _ledger_digest()
    before_canon = _canonical()
    before_sample = _stat(books.SAMPLE_BOOKS)
    before_live = _stat(books.COMMISSIONED_BOOKS)
    beta_pid = _beta_pid()
    test_refuses()
    test_live(before_ledger, before_canon, before_sample, before_live)
    test_fixture_does_not_render(before_sample)
    test_routes(beta_pid)
    evidence, exceptions, approvals, status, resolved = _canonical()
    print(
        "COUNTS "
        f"evidence={evidence} exceptions={exceptions} approvals={approvals} "
        f"evidence_status={status} fin05_resolved={resolved}"
    )
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
