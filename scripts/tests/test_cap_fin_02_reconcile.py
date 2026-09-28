#!/usr/bin/env python3
"""CAP-FIN-02 file-identity reconcile against the CAP-INTG-04 read.

The match is the ingested file. It does not parse an amount, write a book,
or execute a payment. A typed balance is refused and does not close the row.
The ledger stays BUILT.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)
os.environ.pop("WOLF_CANONICAL_WRITE_OVERRIDE", None)

from core import intg_connector_cap_tests as base  # noqa: E402

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
PROD_PID = "15975"
ORIGIN = ("127.0.0.1", 8788)
PUBLIC_HOST = "beta.wolfcommand.net"
RECONCILE_PATH = "/api/intg/connector-cap-tests/reconcile"
PAY_PATH = "/api/intg/connector-cap-tests/payment"
SPOOF = "spoofed@example.invalid"
BAD_JWT = "a.b.c"
EVIDENCE_ID = "EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153"

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


def _public(path: str) -> tuple[int, str, str]:
    conn = HTTPSConnection(PUBLIC_HOST, timeout=15)
    try:
        conn.request("GET", path, headers={"User-Agent": "wolf-p1-fin-02"})
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
            (base.FIN_CAP_ID,),
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


def _no_books(report: dict) -> bool:
    return (
        report.get("payment_executed") is False
        and report.get("bank_api_called") is False
        and report.get("money_moved") is False
        and report.get("amounts_parsed") is False
        and report.get("books_written") is False
        and report.get("books_reconciled") is False
        and report.get("persisted") is False
        and report.get("management_report") is False
        and report.get("ledger_write") is False
        and report.get("balance") is None
        and report.get("typed_balance_closes_row") is False
        and report.get("connected") is False
        and report.get("commissioned") is False
        and report.get("file_identity_only") is True
    )


def _expect(name: str, fn, code: str) -> None:
    try:
        fn()
    except base.ConnectorCapTestsError as exc:
        check(name, exc.code == code, exc.code)
        return
    check(name, False, "no error")


def test_shape(td: Path) -> None:
    sample = td / "sample-statement.pdf"
    sample.write_bytes(b"%PDF-1.4\nnot-a-parsed-amount\n")
    ingest = base.read_authorised_files(td)
    report = base.reconcile_ingested_files(td, ingest)
    check("temp match is the same file", report["match"] is True, str(report["match"]))
    check("temp match does not close the archive row", report["reconciled"] is False)
    check("temp reconcile writes no books", _no_books(report))
    check(
        "temp manifests agree",
        report["ingest_manifest_sha256"] == report["reconcile_manifest_sha256"] == ingest["manifest_sha256"],
    )
    doctored = dict(ingest)
    doctored["manifest_sha256"] = "0" * 64
    missed = base.reconcile_ingested_files(td, doctored)
    check("doctored manifest does not match", missed["match"] is False and missed["reconciled"] is False)
    check("doctored reconcile writes no books", _no_books(missed))
    _expect("typed balance is refused", lambda: base.reconcile_ingested_files(td, ingest, balance="1"), "balance_refused")
    _expect("zero balance is refused", lambda: base.reconcile_ingested_files(td, ingest, balance=0), "balance_refused")
    _expect("typed amount is refused", lambda: base.reconcile_ingested_files(td, ingest, amount="9"), "balance_refused")
    _expect("typed books figure is refused", lambda: base.reconcile_ingested_files(td, ingest, books="9"), "balance_refused")
    priced = dict(ingest)
    priced["balance"] = "1"
    _expect("balance on the ingest is refused", lambda: base.reconcile_ingested_files(td, priced), "balance_refused")
    _expect("payment argument is refused", lambda: base.reconcile_ingested_files(td, ingest, payment="1"), "payment_refused")
    empty = base.reconcile_ingested_files(td, ingest, balance="")
    check("empty balance is not a typed balance", empty["match"] is True and empty["balance"] is None)


def test_archive(before_ledger: str, before_canon: tuple) -> None:
    ingest = base.read_authorised_files()
    report = base.reconcile_ingested_files(ingest=ingest)
    check("ledger digest unchanged by reconcile", _ledger_digest() == before_ledger)
    check("CAP-FIN-02 stays BUILT", base.ledger_cap_state(cap_id=base.FIN_CAP_ID) == "BUILT")
    check("CAP-INTG-04 stays BUILT", base.ledger_cap_state() == "BUILT")
    check("canonical counts unchanged", _canonical() == before_canon, str(_canonical()))
    check("archive reconcile writes no books", _no_books(report))
    if report.get("archive_present") and report.get("file_read"):
        check("authorised reconcile matches the ingest", report["match"] is True and report["reconciled"] is True)
        check(
            "reconcile manifest equals the ingest",
            report["reconcile_manifest_sha256"] == ingest["manifest_sha256"],
        )
        check("opened count is positive", int(report["opened"] or 0) > 0, str(report["opened"]))
        print(
            "NOTE  "
            f"opened={report['opened']} pdf={report['pdf']} csv={report['csv']} "
            f"spreadsheet={report['spreadsheet']} bytes={report['bytes']} "
            f"manifest={report['reconcile_manifest_sha256']} match={report['match']}"
        )
    else:
        check("absent archive does not close the row", report["reconciled"] is False)
        print("NOTE  archive_present=False")


def test_routes() -> None:
    cases = (
        ("GET", RECONCILE_PATH, None),
        ("GET", RECONCILE_PATH + "?balance=1", None),
        ("GET", RECONCILE_PATH + "?amount=1", None),
        ("GET", RECONCILE_PATH, {"Cf-Access-Authenticated-User-Email": SPOOF}),
        ("GET", RECONCILE_PATH, {"X-Wolf-Subject": "PERS-MATT"}),
        ("GET", RECONCILE_PATH, {"Cf-Access-Jwt-Assertion": BAD_JWT}),
        ("POST", RECONCILE_PATH, None),
        ("POST", PAY_PATH, None),
    )
    for method, path, headers in cases:
        status, body = _origin(method, path, headers)
        check(f"{method} {path} denied", status == 403, f"{status} {body.get('error')}")
        check(
            f"{method} {path} body is not a reconcile",
            body.get("match") is not True and body.get("reconciled") is not True and "rows" not in body,
            str(sorted(body.keys())[:8]),
        )
    status, location, server = _public(RECONCILE_PATH)
    host = ""
    if "://" in location:
        host = location.split("/", 3)[2]
    check("public reconcile redirects", status == 302, str(status))
    check(
        "public reconcile goes to Access",
        host == "wolfcommand.cloudflareaccess.com" and "cloudflare" in server.lower(),
        f"{status} {host} {server}",
    )


def main() -> int:
    beta_pid = _beta_pid()
    print(f"NOTE  beta_pid={beta_pid or 'NONE'} prod_pid={PROD_PID}")
    check("prod pid 15975 still serve.py", "serve.py" in _listener(PROD_PID) and "8787" in _listener(PROD_PID))
    check("beta command is serve_beta.py", "serve_beta.py" in _listener(beta_pid) if beta_pid else False)
    before_ledger = _ledger_digest()
    before_canon = _canonical()
    with tempfile.TemporaryDirectory(prefix="cap-fin-02-") as folder:
        test_shape(Path(folder))
    test_archive(before_ledger, before_canon)
    test_routes()
    check("ledger digest unchanged at exit", _ledger_digest() == before_ledger)
    check("canonical counts unchanged at exit", _canonical() == before_canon)
    check("prod pid unchanged at exit", "serve.py" in _listener(PROD_PID))
    print(
        "COUNTS "
        f"evidence={before_canon[0]} exceptions={before_canon[1]} "
        f"approvals={before_canon[2]} evidence_status={before_canon[3]} "
        f"fin02_resolved={before_canon[4]}"
    )
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    if FAIL:
        print("EXIT: FAIL")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
