#!/usr/bin/env python3
"""CAP-CORE-08 existing self-close deny.

The submitter of a resolved close cannot verify that close. The check runs
on a copy of the catalog. The copy is removed. No SoD constraint row is
inserted. No finance pack is inserted. No cash amount is written. The live
core_sod_constraints count is recorded before and after and must stay 0.
Unsigned, spoofed, and bad-JWT callers stay denied on Beta. A seated check
is not minted. The ledger is not raised.
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

from core import rbac  # noqa: E402
from core import venue_close as vc  # noqa: E402

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
PROD_PID = "15975"
ORIGIN = ("127.0.0.1", 8788)
PUBLIC_HOST = "beta.wolfcommand.net"
LOGIN_HOST = "wolfcommand.cloudflareaccess.com"
LOGIN_PATH = "/cdn-cgi/access/login/beta.wolfcommand.net"
GET_PATH = "/api/venue-close/list"
POST_PATH = "/api/venue-close/verify"
POST_BODY = b'{"close_id":"VDC-NONE"}'
SPOOF_EMAIL = "spoofed@example.invalid"
BAD_JWT = "a.b.c"
SUBMITTER = "PERS-MATT"
RESOLVER = "PERS-DEVI"
OTHER = "PERS-HAIKAL"
EMAIL = "mrwolf@wolfcommand.net"
TARGET = {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}
CLOSE_ID = "VDC-CAP-CORE-08-TEMP"
BUSINESS_DATE = "2026-09-27"
TS = "2026-09-27T00:00:00Z"
CR_ID = "CR-d92de8a365ef37ce"
PERM_IDS = (
    "PERM-SOD-CONSTRAINT-MANAGE",
    "PERM-SOD-CONSTRAINT-READ",
    "PERM-VENUE-CLOSE-VERIFY",
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


def _counts(conn: sqlite3.Connection) -> tuple[int, int, int, int, int, tuple, int]:
    constraints = int(conn.execute("SELECT COUNT(*) FROM core_sod_constraints").fetchone()[0])
    participation = int(conn.execute("SELECT COUNT(*) FROM core_sod_participation").fetchone()[0])
    closes = int(conn.execute("SELECT COUNT(*) FROM venue_daily_closes").fetchone()[0])
    policies = int(conn.execute("SELECT COUNT(*) FROM venue_close_variance_policies").fetchone()[0])
    persons = int(conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0])
    grants = tuple(
        tuple(row)
        for row in conn.execute(
            f"""
            SELECT role_id, permission_id, effect
            FROM org_role_permissions
            WHERE permission_id IN ({",".join("?" * len(PERM_IDS))})
            ORDER BY permission_id, role_id
            """,
            PERM_IDS,
        ).fetchall()
    )
    closer = int(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            WHERE p.role_id = 'ROLE-BZG-CLOSER'
              AND a.status = 'ACTIVE'
              AND a.end_at IS NULL
            """
        ).fetchone()[0]
    )
    return constraints, participation, closes, policies, persons, grants, closer


def _venue_audits(conn: sqlite3.Connection) -> int:
    return int(
        conn.execute(
            "SELECT COUNT(*) FROM core_audit_events WHERE source='venue_close'"
        ).fetchone()[0]
    )


def _live_counts() -> tuple[int, int, int, int, int, tuple, int, int]:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        base = _counts(conn)
        return (*base, _venue_audits(conn))
    finally:
        conn.close()


def _origin(
    method: str, path: str, headers: dict[str, str] | None = None, body: bytes | None = None
) -> tuple[int, dict]:
    conn = HTTPConnection(ORIGIN[0], ORIGIN[1], timeout=8)
    try:
        conn.request(method, path, body=body, headers=headers or {})
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
        conn.request("GET", path, headers={"User-Agent": "wolf-p0-sod"})
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


def _row_still_open(conn: sqlite3.Connection) -> sqlite3.Row:
    return conn.execute(
        """
        SELECT state, submitted_by_person_id, resolved_by_person_id,
               verified_by_person_id, verified_at,
               declared_cash_amount, variance_cash_amount, variance_policy_id
        FROM venue_daily_closes WHERE close_id=?
        """,
        (CLOSE_ID,),
    ).fetchone()


def _still_unverified(row: sqlite3.Row) -> bool:
    return (
        row["state"] == "RESOLVED"
        and row["submitted_by_person_id"] == SUBMITTER
        and row["resolved_by_person_id"] == RESOLVER
        and row["verified_by_person_id"] is None
        and row["verified_at"] is None
        and row["declared_cash_amount"] is None
        and row["variance_cash_amount"] is None
        and row["variance_policy_id"] is None
    )


def _expect_deny(conn: sqlite3.Connection, person_id: str, code: str, label: str) -> None:
    try:
        vc.verify_close(
            CLOSE_ID,
            verified_person_id=person_id,
            conn=conn,
            commit=False,
        )
        check(f"{label} verify denied", False, "returned a close")
    except vc.VenueCloseError as exc:
        check(
            f"{label} verify denied {code}",
            exc.code == code and exc.http_status == 403,
            exc.code,
        )
    row = _row_still_open(conn)
    check(f"{label} left the close unresolved", row is not None and _still_unverified(row))


def test_copy_denies(live_before: tuple) -> None:
    td = ROOT / "catalog" / "backups" / f"tmp-cap-core-08-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    tmp_db = td / "content_library.sqlite"
    saved = vc.CATALOG_DB
    try:
        shutil.copy2(CATALOG, tmp_db)
        resolved = tmp_db.resolve()
        check("temp copy is under beta-os", "beta-os" in str(resolved))
        check("temp copy is not the live catalog", resolved != CATALOG.resolve())
        vc.CATALOG_DB = resolved
        conn = vc.db_connect()
        try:
            copied = _counts(conn)
            audits_before = _venue_audits(conn)
            check("temp copy matches the live constraint count", copied[0] == live_before[0], str(copied[0]))
            check("temp copy has no SoD constraint", copied[0] == 0, str(copied[0]))
            check("temp copy has no SoD participation", copied[1] == 0, str(copied[1]))
            check("temp copy has no venue close", copied[2] == 0, str(copied[2]))
            check("temp copy has no variance policy", copied[3] == 0, str(copied[3]))
            check("temp copy closer seat is empty", copied[6] == 0, str(copied[6]))
            persons_before = copied[4]

            matt = rbac.evaluate(SUBMITTER, "venue.close.verify", TARGET, conn=conn)
            check(
                "Matt verify grant is the stored role",
                matt.get("allowed") is True
                and matt.get("person_id") == SUBMITTER
                and (matt.get("matched") or {}).get("role_id") == "ROLE-MATT"
                and (matt.get("matched") or {}).get("assignment_id") == "ASG-MATT-OWNER-1",
                str(matt.get("reason")),
            )
            devi = rbac.evaluate(RESOLVER, "venue.close.verify", TARGET, conn=conn)
            check(
                "Devi active seat does not hold verify",
                devi.get("allowed") is False and devi.get("person_id") == RESOLVER,
                str(devi.get("reason")),
            )
            haikal = rbac.evaluate(OTHER, "venue.close.verify", TARGET, conn=conn)
            check(
                "Haikal does not hold verify",
                haikal.get("allowed") is False and haikal.get("person_id") == OTHER,
                str(haikal.get("reason")),
            )
            emailed = rbac.evaluate(EMAIL, "venue.close.verify", TARGET, conn=conn)
            check("email string is not a verify allow", emailed.get("allowed") is False, str(emailed.get("reason")))

            display = conn.execute(
                "SELECT display_name FROM org_persons WHERE person_id=?",
                (SUBMITTER,),
            ).fetchone()
            named = "" if display is None or display[0] is None else str(display[0])
            check("stored display name is not the person id", bool(named) and named != SUBMITTER)
            by_name = rbac.evaluate(named, "venue.close.verify", TARGET, conn=conn)
            check("display name is not a verify allow", by_name.get("allowed") is False, str(by_name.get("reason")))

            conn.execute(
                """
                INSERT INTO venue_daily_closes (
                  close_id, entity_id, venue_brand_id, business_date, state,
                  fingerprint_stale, submitted_by_person_id, resolved_by_person_id,
                  created_at, updated_at
                ) VALUES (?, 'ENT-BZG', 'BZG-UMA', ?, 'RESOLVED', 0, ?, ?, ?, ?)
                """,
                (CLOSE_ID, BUSINESS_DATE, SUBMITTER, RESOLVER, TS, TS),
            )
            check("temp close has no cash amount", _still_unverified(_row_still_open(conn)))

            _expect_deny(conn, SUBMITTER, "sod_self_close", SUBMITTER)
            _expect_deny(conn, named, "forbidden", "display name")
            _expect_deny(conn, EMAIL, "forbidden", "email string")
            _expect_deny(conn, RESOLVER, "forbidden", RESOLVER)
            _expect_deny(conn, OTHER, "forbidden", OTHER)

            after = _counts(conn)
            check("copy gained one close row and nothing else", after[2] == 1, str(after[2]))
            check("copy SoD constraint count still 0", after[0] == 0, str(after[0]))
            check("copy SoD participation count still 0", after[1] == 0, str(after[1]))
            check("copy variance policy count still 0", after[3] == 0, str(after[3]))
            check("copy person count unchanged", after[4] == persons_before, str(after[4]))
            check("copy permission grants unchanged", after[5] == copied[5])
            check("copy closer seat still empty", after[6] == 0, str(after[6]))
            audits_after = _venue_audits(conn)
            check(
                "copy venue_close audits unchanged",
                audits_after == audits_before,
                f"{audits_before} -> {audits_after}",
            )
            print(
                f"NOTE  self_close=sod_self_close submitter={SUBMITTER} resolver={RESOLVER} "
                f"copy_constraints={after[0]} copy_closes={after[2]} copy_audits={audits_after}"
            )
        finally:
            conn.close()
    finally:
        vc.CATALOG_DB = saved
        shutil.rmtree(td, ignore_errors=True)
    check("temp copy removed", not td.exists())
    live_after = _live_counts()
    check("live SoD constraint count unchanged", live_after[0] == live_before[0], str(live_after[0]))
    check("live SoD constraint count is still 0", live_after[0] == 0, str(live_after[0]))
    check("live venue close count unchanged", live_after[2] == live_before[2], str(live_after[2]))
    check("live venue close count is still 0", live_after[2] == 0, str(live_after[2]))


def _no_close_body(body: dict) -> bool:
    return (
        "close" not in body
        and "closes" not in body
        and body.get("state") not in ("RESOLVED", "VERIFIED_CLOSED")
        and body.get("person_id") in (None, "")
    )


def test_origin_denies() -> None:
    cases = (
        ("unsigned", None, "missing_auth"),
        ("spoofed email", {"Cf-Access-Authenticated-User-Email": SPOOF_EMAIL}, "missing_auth"),
        ("spoofed subject", {"X-Wolf-Subject": SUBMITTER}, "missing_auth"),
        ("bad jwt", {"Cf-Access-Jwt-Assertion": BAD_JWT}, "invalid_token"),
    )
    for label, headers, expect in cases:
        status, body = _origin("GET", GET_PATH, headers)
        check(
            f"{label} GET {GET_PATH} 403 {expect}",
            status == 403 and body.get("error") == expect and body.get("ok") is not True,
            f"status={status} error={body.get('error')}",
        )
        check(f"{label} GET {GET_PATH} no close body", _no_close_body(body), f"keys={sorted(body)}")
        post_headers = {"Content-Type": "application/json"}
        if headers:
            post_headers.update(headers)
        status, body = _origin("POST", POST_PATH, post_headers, POST_BODY)
        check(
            f"{label} POST {POST_PATH} 403 {expect}",
            status == 403 and body.get("error") == expect and body.get("ok") is not True,
            f"status={status} error={body.get('error')}",
        )
        check(f"{label} POST {POST_PATH} no close body", _no_close_body(body), f"keys={sorted(body)}")


def test_public_login() -> None:
    status, location, www, server = _public(GET_PATH)
    parts = urlsplit(location)
    check(
        f"public {GET_PATH} login redirect",
        status == 302
        and parts.scheme == "https"
        and parts.hostname == LOGIN_HOST
        and parts.path == LOGIN_PATH
        and www.startswith("Cloudflare-Access")
        and server.lower() == "cloudflare",
        f"status={status} host={parts.hostname} path={parts.path} server={server}",
    )


def test_ledger(before: str, live_before: tuple) -> None:
    live_after = _live_counts()
    print(
        f"NOTE  live_constraints_after={live_after[0]} live_closes_after={live_after[2]} "
        f"live_policies_after={live_after[3]} live_venue_audits_after={live_after[7]} "
        f"live_closer_after={live_after[6]}"
    )
    check("live constraint count still matches the start", live_after[0] == live_before[0], str(live_after[0]))
    check("live participation count still matches the start", live_after[1] == live_before[1], str(live_after[1]))
    check("live close count still matches the start", live_after[2] == live_before[2], str(live_after[2]))
    check("live variance policy count still matches the start", live_after[3] == live_before[3], str(live_after[3]))
    check("live person count still matches the start", live_after[4] == live_before[4], str(live_after[4]))
    check("live permission grants still match the start", live_after[5] == live_before[5])
    check("live closer seat still matches the start", live_after[6] == live_before[6], str(live_after[6]))
    check("live venue_close audits still match the start", live_after[7] == live_before[7], str(live_after[7]))
    check("live constraint count is still 0", live_after[0] == 0, str(live_after[0]))
    check("live closer seat is still empty", live_after[6] == 0, str(live_after[6]))
    check("ledger digest unchanged", _ledger_digest() == before)
    ledger = json.loads(LEDGER.read_text())
    row = ledger.get("CAP-CORE-08") or []
    check("ledger CAP-CORE-08 stays PROVEN", bool(row) and row[0] == "PROVEN", str(row[:1]))
    check("ledger length stays 77", len(ledger) == 77, str(len(ledger)))
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        found = conn.execute(
            "SELECT state, capability FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
        check(
            f"{CR_ID} stays OPEN",
            found is not None and found[0] == "OPEN" and found[1] == "CAP-CORE-08",
            str(found),
        )
        planted = conn.execute(
            "SELECT COUNT(*) FROM venue_daily_closes WHERE close_id=?",
            (CLOSE_ID,),
        ).fetchone()
        check("temp close id is absent from the live catalog", int(planted[0]) == 0, str(planted[0]))
    finally:
        conn.close()


def main() -> int:
    before = _ledger_digest()
    live_before = _live_counts()
    beta_pid = _beta_pid()
    print(f"NOTE  beta_pid={beta_pid or 'absent'} prod_pid={PROD_PID}")
    print(
        f"NOTE  live_constraints={live_before[0]} live_closes={live_before[2]} "
        f"live_policies={live_before[3]} live_closer={live_before[6]} "
        f"live_venue_audits={live_before[7]}"
    )
    test_listeners(beta_pid)
    test_copy_denies(live_before)
    test_origin_denies()
    test_public_login()
    test_ledger(before, live_before)
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
