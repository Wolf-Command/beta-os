#!/usr/bin/env python3
"""CAP-CORE-07 approval route, without a new policy row.

The engine is read on a copy of the catalog. The copy is removed. No
approval request and no governance policy are inserted. The six stored
decisions are not treated as a pack. Unsigned, spoofed, and bad-JWT
callers stay denied on Beta. A seated read is not minted. The ledger is
not raised.
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

from core import approvals as apr  # noqa: E402
from core import work_items as wi  # noqa: E402

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
CR_ID = "CR-fb1af5c252e28d77"
PROD_PID = "15975"
ORIGIN = ("127.0.0.1", 8788)
PUBLIC_HOST = "beta.wolfcommand.net"
LOGIN_HOST = "wolfcommand.cloudflareaccess.com"
LOGIN_PATH = "/cdn-cgi/access/login/beta.wolfcommand.net"
PATHS = ("/api/core/approvals", "/api/core/approvals/APR-NONE")
SPOOF_EMAIL = "spoofed@example.invalid"
BAD_JWT = "a.b.c"
PERSON = "PERS-MATT"
EMAIL = "mrwolf@wolfcommand.net"
POST_BODY = b'{"title":"must-not-land","owning_entity_id":"ENT-GGV","required_permission_code":"approval.read"}'

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


def _counts(conn: sqlite3.Connection) -> tuple[int, int, int, tuple[str, ...], int]:
    requests = int(conn.execute("SELECT COUNT(*) FROM core_approval_requests").fetchone()[0])
    decisions = int(conn.execute("SELECT COUNT(*) FROM core_approval_decisions").fetchone()[0])
    policies = int(conn.execute("SELECT COUNT(*) FROM core_governance_policies").fetchone()[0])
    policy_ids = tuple(
        row[0]
        for row in conn.execute(
            "SELECT policy_id FROM core_governance_policies ORDER BY policy_id"
        ).fetchall()
    )
    approval_audits = int(
        conn.execute(
            "SELECT COUNT(*) FROM core_audit_events WHERE source='approvals'"
        ).fetchone()[0]
    )
    return requests, decisions, policies, policy_ids, approval_audits


def _live_counts() -> tuple[int, int, int, tuple[str, ...], int]:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        return _counts(conn)
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
        conn.request("GET", path, headers={"User-Agent": "wolf-p0-approvals"})
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


def test_copy_reads_without_a_new_row(live_before: tuple[int, int, int, tuple[str, ...], int]) -> None:
    td = ROOT / "catalog" / "backups" / f"tmp-cap-core-07-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    tmp_db = td / "content_library.sqlite"
    try:
        shutil.copy2(CATALOG, tmp_db)
        resolved = tmp_db.resolve()
        check("temp copy is under beta-os", "beta-os" in str(resolved))
        check("temp copy is not the live catalog", resolved != CATALOG.resolve())
        apr.CATALOG_DB = resolved
        wi.CATALOG_DB = resolved
        conn = sqlite3.connect(str(resolved))
        conn.row_factory = sqlite3.Row
        try:
            copied = _counts(conn)
            check("temp copy matches the live request count", copied[0] == live_before[0], str(copied[0]))
            check("temp copy matches the live decision count", copied[1] == live_before[1], str(copied[1]))
            check("temp copy matches the live policy count", copied[2] == live_before[2], str(copied[2]))
            check("temp copy matches the live policy ids", copied[3] == live_before[3], str(copied[3]))
            check("stored request table is empty", copied[0] == 0, str(copied[0]))

            visible = wi.visible_entity_ids_for_person(PERSON, conn=conn)
            check(
                "Matt resolves entities by person id",
                bool(visible) and all(str(eid).startswith("ENT-") for eid in visible),
                str(sorted(visible)),
            )
            check(
                "email string resolves no entity",
                wi.visible_entity_ids_for_person(EMAIL, conn=conn) == set(),
            )
            print("NOTE  visible=" + ",".join(sorted(visible)))
            print("NOTE  policy_ids=" + ",".join(copied[3]))

            writes = conn.total_changes
            items = apr.list_approval_requests(PERSON, conn=conn)
            emailed = apr.list_approval_requests(EMAIL, conn=conn)
            check("engine read did not write the copy", conn.total_changes == writes, str(conn.total_changes))
            check("Matt list is the stored empty request table", items == [], str(items)[:200])
            check("email string is not an approval list", emailed == [], str(emailed)[:200])
            check("list actor is a person id", PERSON.startswith("PERS-") and "@" not in PERSON)

            after = _counts(conn)
            check("copy request count unchanged", after[0] == copied[0], str(after[0]))
            check("copy decision count unchanged", after[1] == copied[1], str(after[1]))
            check("copy policy count unchanged", after[2] == copied[2], str(after[2]))
            check("copy policy ids unchanged", after[3] == copied[3], str(after[3]))
            check("six stored decisions were not turned into requests", after[0] == 0 and after[1] == copied[1])
            print(
                f"NOTE  copy_requests={after[0]} copy_decisions={after[1]} "
                f"copy_policies={after[2]}"
            )
        finally:
            conn.close()
    finally:
        apr.CATALOG_DB = CATALOG
        wi.CATALOG_DB = CATALOG
        shutil.rmtree(td, ignore_errors=True)
    check("temp copy removed", not td.exists())
    live_after = _live_counts()
    check("live request count unchanged after the copy", live_after[0] == live_before[0], str(live_after[0]))
    check("live decision count unchanged after the copy", live_after[1] == live_before[1], str(live_after[1]))
    check("live policy count unchanged after the copy", live_after[2] == live_before[2], str(live_after[2]))
    check("live policy ids unchanged after the copy", live_after[3] == live_before[3], str(live_after[3]))
    check(
        "live approval audits unchanged after the copy",
        live_after[4] == live_before[4],
        str(live_after[4]),
    )


def test_origin_denies() -> None:
    cases = (
        ("unsigned", None, "missing_auth"),
        ("spoofed email", {"Cf-Access-Authenticated-User-Email": SPOOF_EMAIL}, "missing_auth"),
        ("spoofed subject", {"X-Wolf-Subject": PERSON}, "missing_auth"),
        ("bad jwt", {"Cf-Access-Jwt-Assertion": BAD_JWT}, "invalid_token"),
    )
    for path in PATHS:
        for label, headers, expect in cases:
            status, body = _origin("GET", path, headers)
            check(
                f"{label} GET {path} 403 {expect}",
                status == 403 and body.get("error") == expect and body.get("ok") is not True,
                f"status={status} error={body.get('error')}",
            )
            check(
                f"{label} GET {path} no approval body",
                "approval" not in body
                and "approvals" not in body
                and "decisions" not in body
                and body.get("person_id") in (None, ""),
                f"keys={sorted(body)}",
            )
    status, body = _origin(
        "POST",
        "/api/core/approvals",
        {"Content-Type": "application/json"},
        POST_BODY,
    )
    check(
        "unsigned POST /api/core/approvals 403",
        status == 403 and body.get("ok") is not True and "approval" not in body,
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


def test_ledger(before: str, live_before: tuple[int, int, int, tuple[str, ...], int]) -> None:
    live_after = _live_counts()
    print(
        f"NOTE  live_requests_after={live_after[0]} live_decisions_after={live_after[1]} "
        f"live_policies_after={live_after[2]} live_approval_audits_after={live_after[4]}"
    )
    check("live request count still matches the start", live_after[0] == live_before[0], str(live_after[0]))
    check("live decision count still matches the start", live_after[1] == live_before[1], str(live_after[1]))
    check("live policy count still matches the start", live_after[2] == live_before[2], str(live_after[2]))
    check("live policy ids still match the start", live_after[3] == live_before[3], str(live_after[3]))
    check(
        "live approval audits still match the start",
        live_after[4] == live_before[4],
        str(live_after[4]),
    )
    check("live request count is still 0", live_after[0] == 0, str(live_after[0]))
    check("ledger digest unchanged", _ledger_digest() == before)
    ledger = json.loads(LEDGER.read_text())
    row = ledger.get("CAP-CORE-07") or []
    check("ledger CAP-CORE-07 stays PROVEN", bool(row) and row[0] == "PROVEN", str(row[:1]))
    check("ledger length stays 77", len(ledger) == 77, str(len(ledger)))
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        found = conn.execute(
            "SELECT state, capability FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
        check(
            f"{CR_ID} stays OPEN",
            found is not None and found[0] == "OPEN" and found[1] == "CAP-CORE-07",
            str(found),
        )
    finally:
        conn.close()


def main() -> int:
    before = _ledger_digest()
    live_before = _live_counts()
    beta_pid = _beta_pid()
    print(f"NOTE  beta_pid={beta_pid or 'absent'} prod_pid={PROD_PID}")
    print(
        f"NOTE  live_requests={live_before[0]} live_decisions={live_before[1]} "
        f"live_policies={live_before[2]} live_approval_audits={live_before[4]}"
    )
    test_listeners(beta_pid)
    test_copy_reads_without_a_new_row(live_before)
    test_origin_denies()
    test_public_login()
    test_ledger(before, live_before)
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
