#!/usr/bin/env python3
"""CAP-CORE-01 live Beta gate for the organisation registry reads.

Unsigned, a spoofed email header, an untrusted subject header, and a bad
JWT stay denied on the origin. The public hostname redirects to the
Cloudflare Access login. A seated allow is not minted. The ledger is not
raised. Catalog permission rows are read, not written.
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
CR_ID = "CR-dddbefbb61c98008"
PROD_PID = "15975"
ORIGIN = ("127.0.0.1", 8788)
PUBLIC_HOST = "beta.wolfcommand.net"
LOGIN_HOST = "wolfcommand.cloudflareaccess.com"
LOGIN_PATH = "/cdn-cgi/access/login/beta.wolfcommand.net"
PATHS = (
    "/api/core/entities",
    "/api/core/entities/ENT-NOPE",
    "/api/core/entities/ENT-BZG",
    "/api/core/entities/ENT-BZG/brands",
    "/api/core/entities/ENT-BZG/locations",
    "/api/core/entities/ENT-BZG/departments",
    "/api/core/brands/BZG-UMA",
    "/api/core/brands/NOPE",
)
SPOOF_EMAIL = "spoofed@example.invalid"
BAD_JWT = "a.b.c"
LEAK_KEYS = ("entity", "entities", "brand", "brands", "locations", "departments")

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
        conn.request("GET", path, headers={"User-Agent": "wolf-p0-org"})
        resp = conn.getresponse()
        resp.read(256)
        status = int(resp.status)
        location = resp.getheader("Location") or ""
        www = resp.getheader("WWW-Authenticate") or ""
        server = resp.getheader("Server") or ""
    finally:
        conn.close()
    return status, location, www, server


def _org_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = (
        "org_entities",
        "org_brands",
        "org_locations",
        "org_departments",
        "org_brand_locations",
        "org_persons",
        "org_assignments",
    )
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
                f"{label} {path} no registry body",
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
        denied = ("PERS-HAIKAL", "PERS-DEVI")
        allowed = ("PERS-MATT",)
        for person_id in denied:
            check(
                f"catalog {person_id} lacks organisation.entity.read",
                rbac.can(person_id, "organisation.entity.read", target, conn=conn) is False,
            )
        for person_id in allowed:
            check(
                f"catalog {person_id} has organisation.entity.read",
                rbac.can(person_id, "organisation.entity.read", target, conn=conn) is True,
            )
        after = _org_counts(conn)
    finally:
        conn.close()
    check("org catalog counts unchanged", after == before_counts, str(after))


def test_ledger_and_row(before: str) -> None:
    after = _ledger_digest()
    check("ledger digest unchanged", before == after)
    ledger = json.loads(LEDGER.read_text())
    row = ledger.get("CAP-CORE-01") or []
    check("ledger CAP-CORE-01 stays PROVEN", bool(row) and row[0] == "PROVEN", str(row[:1]))
    check("ledger length stays 77", len(ledger) == 77, str(len(ledger)))
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        found = conn.execute(
            "SELECT state, capability FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
    finally:
        conn.close()
    check(
        "completion row stays OPEN",
        found is not None and found[0] == "OPEN" and found[1] == "CAP-CORE-01",
        str(found),
    )


def main() -> int:
    before = _ledger_digest()
    count_conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    count_conn.row_factory = sqlite3.Row
    try:
        before_counts = _org_counts(count_conn)
    finally:
        count_conn.close()
    beta_pid = _beta_pid()
    print(f"NOTE  beta_pid={beta_pid or 'absent'} prod_pid={PROD_PID}")
    test_listeners(beta_pid)
    test_origin_denies()
    test_public_login()
    test_catalog_projection(before_counts)
    test_ledger_and_row(before)
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
