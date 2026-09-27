#!/usr/bin/env python3
"""CAP-INTG-04 authorised statement-file read.

The 2026-07-30 decision says there is no bank feed. This reads files the
owner already filed, and a temp file that is not that archive. It does not
parse an amount, write books, call a bank, or move money. CONFIGURED,
CONNECTED, TESTED, and COMMISSIONED stay separate fields. The ledger is
not raised. A seated allow is not minted.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ["WOLF_TEST_MODE"] = "1"

from core import intg_connector_cap_tests as base  # noqa: E402

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
PROD_PID = "15975"
ORIGIN = ("127.0.0.1", 8788)
PUBLIC_HOST = "beta.wolfcommand.net"
READ_PATH = "/api/intg/connector-cap-tests/file-read"
PAY_PATH = "/api/intg/connector-cap-tests/payment"
SPOOF = "spoofed@example.invalid"
BAD_JWT = "a.b.c"
DIGIT_RUN = re.compile(r"\d{4,}")

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
        conn.request("GET", path, headers={"User-Agent": "wolf-p1-intg-04"})
        resp = conn.getresponse()
        resp.read(256)
        status = int(resp.status)
        location = resp.getheader("Location") or ""
        server = resp.getheader("Server") or ""
    finally:
        conn.close()
    return status, location, server


def _cr_state() -> str:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT state FROM wolf_completion_items WHERE id=?",
            (base.CR_ID,),
        ).fetchone()
    finally:
        conn.close()
    return str(row[0] if row else "")


def _names_clean(report: dict) -> bool:
    for row in report.get("rows") or []:
        if DIGIT_RUN.search(str(row.get("name") or "")):
            return False
    return True


def _no_money(report: dict) -> bool:
    return (
        report.get("payment_executed") is False
        and report.get("bank_api_called") is False
        and report.get("bank_feed_called") is False
        and report.get("money_moved") is False
        and report.get("amounts_parsed") is False
        and report.get("persisted") is False
        and report.get("books_written") is False
        and report.get("reconciled") is False
        and report.get("management_report") is False
        and report.get("ledger_write") is False
        and report.get("connected") is False
        and report.get("commissioned") is False
        and report.get("states_collapsed") is False
    )


def test_shape(td: Path) -> None:
    sample = td / "000000000000-note.pdf"
    sample.write_bytes(b"%PDF-1.4\nnot-a-bank-statement\n")
    other = td / "notes.json"
    other.write_text('{"not":"a statement"}', encoding="utf-8")
    report = base.read_authorised_files(td)
    check("temp file is not the authorised archive", report["authorised"] is False)
    check("temp file is not configured as the archive", report["configured"] is False)
    check("temp read opened the pdf", report["opened"] == 1 and report["pdf"] == 1, str(report["opened"]))
    check("temp read skipped json", report["skipped_other"] >= 1, str(report["skipped_other"]))
    check("temp read is not a closure read", report["file_read"] is False)
    check("temp names hide digit runs", _names_clean(report), str([row["name"] for row in report["rows"]]))
    check("temp read moves no money", _no_money(report))
    notes = report["state_notes"]
    check(
        "four state notes stay distinct",
        len({notes["configured"], notes["connected"], notes["tested"], notes["commissioned"]}) == 4,
    )
    try:
        base.read_authorised_files(td, payment="1")
        check("payment argument is refused", False, "read returned")
    except base.ConnectorCapTestsError as exc:
        check("payment argument is refused", exc.code == "payment_refused", exc.code)
    try:
        base.read_authorised_files(ROOT / "scripts" / "core" / "intg_connector_cap_tests.py")
        check("repo path is refused", False, "read returned")
    except base.ConnectorCapTestsError as exc:
        check("repo path is refused", exc.code == "archive_refused", exc.code)


def test_archive(before: str) -> None:
    report = base.read_authorised_files()
    check("ledger digest unchanged by the read", _ledger_digest() == before)
    check("ledger maturity stays BUILT", base.ledger_cap_state() == "BUILT")
    check("completion row stays unresolved", _cr_state() != "RESOLVED", _cr_state())
    check("archive states stay separate", _no_money(report))
    check("archive read is marked tested", report["tested"] is True)
    if report["archive_present"] and report["opened"]:
        check("authorised archive was read", report["authorised"] is True and report["file_read"] is True)
        check("archive is configured and not connected", report["configured"] is True and report["connected"] is False)
        check("opened count is positive", report["opened"] > 0, str(report["opened"]))
        check("names hide digit runs", _names_clean(report))
        check("manifest is 64 hex chars", len(report["manifest_sha256"]) == 64)
        print(
            "NOTE  "
            f"opened={report['opened']} pdf={report['pdf']} csv={report['csv']} "
            f"spreadsheet={report['spreadsheet']} bytes={report['bytes']} "
            f"manifest={report['manifest_sha256']}"
        )
    else:
        check("absent archive is not called connected", report["connected"] is False)
        check("absent archive is not a file read", report["file_read"] is False)
        print("NOTE  archive_present=False opened=0")
    print(
        "NOTE  "
        f"configured={report['configured']} connected={report['connected']} "
        f"tested={report['tested']} commissioned={report['commissioned']}"
    )


def test_routes() -> None:
    cases = (
        ("GET", READ_PATH, None),
        ("GET", READ_PATH, {"Cf-Access-Authenticated-User-Email": SPOOF}),
        ("GET", READ_PATH, {"X-Wolf-Subject": "PERS-MATT"}),
        ("GET", READ_PATH, {"Cf-Access-Jwt-Assertion": BAD_JWT}),
        ("POST", READ_PATH, None),
        ("POST", PAY_PATH, None),
    )
    for method, path, headers in cases:
        status, body = _origin(method, path, headers)
        check(f"{method} {path} denied", status == 403, f"{status} {body.get('error')}")
        check(
            f"{method} {path} body is not a file list",
            "rows" not in body and body.get("file_read") is not True,
            str(sorted(body.keys())[:8]),
        )
    status, location, server = _public(READ_PATH)
    host = ""
    if "://" in location:
        host = location.split("/", 3)[2]
    check("public file-read redirects", status == 302, str(status))
    check(
        "public file-read goes to Access",
        host == "wolfcommand.cloudflareaccess.com" and "cloudflare" in server.lower(),
        f"{status} {host} {server}",
    )


def main() -> int:
    beta_pid = _beta_pid()
    print(f"NOTE  beta_pid={beta_pid or 'NONE'} prod_pid={PROD_PID}")
    check("prod pid 15975 still serve.py", "serve.py" in _listener(PROD_PID) and "8787" in _listener(PROD_PID))
    check("beta command is serve_beta.py", "serve_beta.py" in _listener(beta_pid) if beta_pid else False)
    before = _ledger_digest()
    with tempfile.TemporaryDirectory(prefix="cap-intg-04-") as folder:
        test_shape(Path(folder))
    test_archive(before)
    test_routes()
    check("ledger digest unchanged at exit", _ledger_digest() == before)
    check("prod pid unchanged at exit", "serve.py" in _listener(PROD_PID))
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    if FAIL:
        print("EXIT: FAIL")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
