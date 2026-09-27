#!/usr/bin/env python3
"""CAP-CORE-03 live Beta gate for the role, position, and assignment board.

Unsigned, a spoofed email header, an untrusted subject header, and a bad
JWT stay denied on the origin. The public hostname redirects to the
Cloudflare Access login. A seated allow is not minted. The ledger is not
raised. Assignment rows are read, not written. No person is created.
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

from core import rbac  # noqa: E402

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
PROD_PID = "15975"
ORIGIN = ("127.0.0.1", 8788)
PUBLIC_HOST = "beta.wolfcommand.net"
LOGIN_HOST = "wolfcommand.cloudflareaccess.com"
LOGIN_PATH = "/cdn-cgi/access/login/beta.wolfcommand.net"
PATHS = (
    "/api/core/roles",
    "/api/core/roles/ROLE-NOPE",
    "/api/core/roles/ROLE-GGV-CREATIVE-DIRECTOR",
    "/api/core/positions",
    "/api/core/positions/POS-NOPE",
    "/api/core/positions/POS-GGV-CREATIVE-DIRECTOR-1",
    "/api/core/positions/POS-NOPE/assignments",
    "/api/core/positions/POS-GGV-CREATIVE-DIRECTOR-1/assignments",
    "/api/core/persons/PERS-NOPE/assignments",
    "/api/core/persons/PERS-HAIKAL/assignments",
    "/api/core/me/assignments",
)
SPOOF_EMAIL = "spoofed@example.invalid"
BAD_JWT = "a.b.c"
LEAK_KEYS = (
    "roles",
    "role",
    "positions",
    "position",
    "assignments",
    "current_occupants",
    "org_context",
)
# Measured 27 Sep 2026 against the live catalog. Not a new grant.
ROLE_READ = {
    "PERS-AMANDA": True,
    "PERS-DEVI": False,
    "PERS-HAIKAL": False,
    "PERS-LEAD-DEMO": False,
    "PERS-MATT": True,
    "PERS-MISA": False,
}
ACTIVE_ASG = "ASG-HAIKAL-CD-1"
ENDED_ASG = "ASG-HAIKAL-VE-1"

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
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        body = {}
    if not isinstance(body, dict):
        body = {}
    return status, body


def _public(path: str) -> tuple[int, str, str, str]:
    conn = HTTPSConnection(PUBLIC_HOST, timeout=15)
    try:
        conn.request("GET", path, headers={"User-Agent": "wolf-p0-asg"})
        resp = conn.getresponse()
        resp.read(256)
        status = int(resp.status)
        location = resp.getheader("Location") or ""
        www = resp.getheader("WWW-Authenticate") or ""
        server = resp.getheader("Server") or ""
    finally:
        conn.close()
    return status, location, www, server


def _board_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = ("org_persons", "org_roles", "org_positions", "org_assignments")
    return {name: int(conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]) for name in tables}


def test_listeners(beta_pid: str) -> None:
    prod = _listener(PROD_PID)
    check("prod pid 15975 still serve.py", "serve.py" in prod and "8787" in prod, prod[:160])
    check("beta pid listening", bool(beta_pid), "no listener")
    beta = _listener(beta_pid) if beta_pid else ""
    check("beta command is serve_beta.py", "serve_beta.py" in beta, beta[:160])


def test_origin_denies() -> None:
    cases = (
        ("unsigned", None, "missing_auth"),
        ("spoofed email", {"Cf-Access-Authenticated-User-Email": SPOOF_EMAIL}, "missing_auth"),
        ("spoofed subject", {"X-Wolf-Subject": "PERS-MATT"}, "missing_auth"),
        ("bad jwt", {"Cf-Access-Jwt-Assertion": BAD_JWT}, "invalid_token"),
    )
    for path in PATHS:
        for label, headers, expect in cases:
            status, body = _origin(path, headers)
            leaked = [key for key in LEAK_KEYS if key in body]
            check(
                f"{label} {path} 403 {expect}",
                status == 403 and body.get("error") == expect and body.get("ok") is not True,
                f"status={status} error={body.get('error')}",
            )
            check(
                f"{label} {path} no person",
                body.get("person_id") in (None, "") and body.get("email") in (None, ""),
                f"person_id={body.get('person_id')}",
            )
            check(
                f"{label} {path} no board body",
                not leaked,
                ",".join(leaked),
            )
            if headers and "Cf-Access-Authenticated-User-Email" in headers:
                check(
                    f"{label} {path} does not accept the header",
                    SPOOF_EMAIL not in json.dumps(body),
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


def test_catalog_projection(before_counts: dict[str, int]) -> None:
    """Read-only. This is not a seated HTTP allow or deny."""
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        target = rbac.default_content_target()
        people = [r[0] for r in conn.execute("SELECT person_id FROM org_persons ORDER BY person_id")]
        actual = {pid: rbac.can(pid, "organisation.role.read", target, conn=conn) for pid in people}
        check("person set unchanged", actual.keys() == ROLE_READ.keys(), ",".join(people))
        for person_id, allowed in ROLE_READ.items():
            word = "has" if allowed else "lacks"
            check(
                f"catalog {person_id} {word} organisation.role.read",
                actual.get(person_id) is allowed,
            )
        haikal = {
            r["assignment_id"]: r
            for r in conn.execute(
                """
                SELECT assignment_id, status, end_at, is_primary
                FROM org_assignments WHERE person_id='PERS-HAIKAL'
                """
            )
        }
        active = haikal.get(ACTIVE_ASG)
        ended = haikal.get(ENDED_ASG)
        check(
            "stored active seat is ASG-HAIKAL-CD-1",
            active is not None
            and active["status"] == "ACTIVE"
            and active["end_at"] is None
            and int(active["is_primary"]) == 1,
            str(dict(active) if active else None),
        )
        check(
            "stored ended seat is ASG-HAIKAL-VE-1",
            ended is not None and ended["status"] == "ENDED" and ended["end_at"] is not None,
            str(dict(ended) if ended else None),
        )
        active_ids = [
            r[0]
            for r in conn.execute(
                """
                SELECT assignment_id FROM org_assignments
                WHERE person_id='PERS-HAIKAL' AND status='ACTIVE' AND end_at IS NULL
                """
            )
        ]
        check(
            "ended seat is not an active seat",
            active_ids == [ACTIVE_ASG],
            ",".join(active_ids),
        )
        after = _board_counts(conn)
        completion = conn.execute(
            "SELECT COUNT(*) FROM wolf_completion_items WHERE capability='CAP-CORE-03'"
        ).fetchone()[0]
    finally:
        conn.close()
    check("board catalog counts unchanged", after == before_counts, str(after))
    check("no CAP-CORE-03 completion row was inserted", int(completion) == 0, str(completion))


def test_ledger(before: str) -> None:
    after = _ledger_digest()
    check("ledger digest unchanged", before == after)
    ledger = json.loads(LEDGER.read_text())
    row = ledger.get("CAP-CORE-03") or []
    check("ledger CAP-CORE-03 stays PROVEN", bool(row) and row[0] == "PROVEN", str(row[:1]))
    check("ledger length stays 77", len(ledger) == 77, str(len(ledger)))


def main() -> int:
    before = _ledger_digest()
    count_conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    count_conn.row_factory = sqlite3.Row
    try:
        before_counts = _board_counts(count_conn)
    finally:
        count_conn.close()
    beta_pid = _beta_pid()
    print(f"NOTE  beta_pid={beta_pid or 'absent'} prod_pid={PROD_PID}")
    test_listeners(beta_pid)
    test_origin_denies()
    test_public_login()
    test_catalog_projection(before_counts)
    test_ledger(before)
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
