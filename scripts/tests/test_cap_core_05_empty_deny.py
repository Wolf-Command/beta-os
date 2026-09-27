#!/usr/bin/env python3
"""CAP-CORE-05 empty authority-limit deny.

An action is evaluated on a copy of the catalog that has no authority-limit
rows. The copy is removed. No limit row is inserted. The live
org_authority_limits count is recorded before and after and must stay 0.
Unsigned, spoofed, and bad-JWT callers stay denied on Beta. A seated check
is not minted. The ledger is not raised. A displayed 0 is the row count,
not a tolerance.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import authority as auth  # noqa: E402

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
PROD_PID = "15975"
ORIGIN = ("127.0.0.1", 8788)
PUBLIC_HOST = "beta.wolfcommand.net"
LOGIN_HOST = "wolfcommand.cloudflareaccess.com"
LOGIN_PATH = "/cdn-cgi/access/login/beta.wolfcommand.net"
PATHS = ("/api/core/authority/check", "/api/core/me/authority-limits")
SPOOF_EMAIL = "spoofed@example.invalid"
BAD_JWT = "a.b.c"
PERSON = "PERS-MATT"
OTHER = "PERS-HAIKAL"
CODE = "content.plan.approve"
OTHER_CODE = "content.plan.edit"
TARGET = {"entity_id": "ENT-GGV", "department_id": "DEPT-GGV-CONTENT"}
AMOUNT = {"amount": 100, "currency": "IDR"}

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


def _live_limit_count() -> int:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        return int(conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0])
    finally:
        conn.close()


def _origin(path: str, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    conn = HTTPConnection(ORIGIN[0], ORIGIN[1], timeout=8)
    try:
        conn.request("GET", path, headers=headers or {})
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
        conn.request("GET", path, headers={"User-Agent": "wolf-p0-limits"})
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


def _denied_for_no_row(ev: dict) -> bool:
    return (
        ev.get("allowed") is False
        and ev.get("reason") == "higher_approval_required"
        and ev.get("detail") == "no_matching_authority_limit"
        and ev.get("matched_limit") is None
    )


def test_empty_copy_denies(live_before: int) -> None:
    td = ROOT / "catalog" / "backups" / f"tmp-cap-core-05-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    tmp_db = td / "content_library.sqlite"
    try:
        shutil.copy2(CATALOG, tmp_db)
        resolved = tmp_db.resolve()
        check("temp copy is under beta-os", "beta-os" in str(resolved))
        check("temp copy is not the live catalog", resolved != CATALOG.resolve())
        conn = sqlite3.connect(str(resolved))
        conn.row_factory = sqlite3.Row
        try:
            copied = int(conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0])
            check("temp copy starts with the live count", copied == live_before, str(copied))
            check("temp copy has no authority-limit row", copied == 0, str(copied))

            matt = auth.within_authority(PERSON, CODE, TARGET, AMOUNT, conn=conn)
            check("Matt action with no limit row is denied", _denied_for_no_row(matt), str(matt.get("reason")))
            check(
                "deny names the person id",
                matt.get("person_id") == PERSON and matt.get("person_id", "").startswith("PERS-"),
                str(matt.get("person_id")),
            )
            check("deny does not allow", matt.get("allowed") is False)

            haikal = auth.within_authority(OTHER, OTHER_CODE, TARGET, AMOUNT, conn=conn)
            check(
                "Haikal edit with no limit row is denied",
                _denied_for_no_row(haikal),
                str(haikal.get("reason")),
            )

            email = auth.within_authority(
                "mrwolf@wolfcommand.net", CODE, TARGET, AMOUNT, conn=conn
            )
            check("email string is not an allow", email.get("allowed") is False, str(email.get("reason")))

            after = int(conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0])
            check("temp copy still has no authority-limit row", after == 0, str(after))
        finally:
            conn.close()
        print("NOTE  empty_deny=higher_approval_required no_matching_authority_limit")
    finally:
        shutil.rmtree(td, ignore_errors=True)
    check("temp copy removed", not td.exists())
    live_after = _live_limit_count()
    check("live authority-limit count unchanged", live_after == live_before, str(live_after))
    check("live authority-limit count is still 0", live_after == 0, str(live_after))


def test_origin_denies() -> None:
    cases = (
        ("unsigned", None, "missing_auth"),
        ("spoofed email", {"Cf-Access-Authenticated-User-Email": SPOOF_EMAIL}, "missing_auth"),
        ("spoofed subject", {"X-Wolf-Subject": PERSON}, "missing_auth"),
        ("bad jwt", {"Cf-Access-Jwt-Assertion": BAD_JWT}, "invalid_token"),
    )
    for path in PATHS:
        for label, headers, expect in cases:
            status, body = _origin(path, headers)
            check(
                f"{label} GET {path} 403 {expect}",
                status == 403 and body.get("error") == expect and body.get("ok") is not True,
                f"status={status} error={body.get('error')}",
            )
            check(
                f"{label} GET {path} no limit body",
                "authority_limits" not in body
                and "decision" not in body
                and "threshold_value" not in body
                and body.get("person_id") in (None, ""),
                f"keys={sorted(body)}",
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


def test_ledger(before: str, live_before: int) -> None:
    live_after = _live_limit_count()
    print(f"NOTE  live_authority_limits_after={live_after}")
    check("live authority-limit count still matches the start", live_after == live_before, str(live_after))
    check("ledger digest unchanged", _ledger_digest() == before)
    ledger = json.loads(LEDGER.read_text())
    row = ledger.get("CAP-CORE-05") or []
    check("ledger CAP-CORE-05 stays PROVEN", bool(row) and row[0] == "PROVEN", str(row[:1]))
    check("ledger length stays 77", len(ledger) == 77, str(len(ledger)))
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        found = conn.execute(
            "SELECT COUNT(*) FROM wolf_completion_items WHERE capability=?",
            ("CAP-CORE-05",),
        ).fetchone()
        check("no completion row was inserted for CAP-CORE-05", int(found[0]) == 0, str(found[0]))
    finally:
        conn.close()


def main() -> int:
    before = _ledger_digest()
    live_before = _live_limit_count()
    beta_pid = _beta_pid()
    print(f"NOTE  beta_pid={beta_pid or 'absent'} prod_pid={PROD_PID}")
    print(f"NOTE  live_authority_limits={live_before}")
    test_listeners(beta_pid)
    test_empty_copy_denies(live_before)
    test_origin_denies()
    test_public_login()
    test_ledger(before, live_before)
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
