#!/usr/bin/env python3
"""CAP-CORE-04 live Beta gate for the permission catalog and seat-route deny.

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
PROD_PID = "15975"
ORIGIN = ("127.0.0.1", 8788)
PUBLIC_HOST = "beta.wolfcommand.net"
LOGIN_HOST = "wolfcommand.cloudflareaccess.com"
LOGIN_PATH = "/cdn-cgi/access/login/beta.wolfcommand.net"
CATALOG_PATH = "/api/core/permissions"
ME_PATH = "/api/core/me/permissions"
SEAT_ROUTES = (
    ("/content-2.0", "forbidden", "forbidden"),
    ("/bzg/uma-blu", "missing_auth", "invalid_token"),
    ("/wolf", "missing_auth", "invalid_token"),
    ("/ggv/finance", "missing_auth", "invalid_token"),
)
SPOOF_EMAIL = "spoofed@example.invalid"
BAD_JWT = "a.b.c"
LEAK_KEYS = ("permissions", "role_grants", "person_id", "email")
# Catalog projection. Not an HTTP status under a Cloudflare session.
SEAT = {
    "PERS-HAIKAL": {
        "organisation.role.read": False,
        "organisation.entity.read": False,
        "content.plan.read": True,
        "venue.close.read": False,
        "finance.nota.read": False,
        "progress.read": False,
    },
    "PERS-DEVI": {
        "organisation.role.read": False,
        "organisation.entity.read": False,
        "content.plan.read": False,
        "venue.close.read": True,
        "finance.nota.read": False,
        "progress.read": False,
    },
    "PERS-MATT": {
        "organisation.role.read": True,
        "organisation.entity.read": True,
        "content.plan.read": True,
        "venue.close.read": True,
        "finance.nota.read": True,
        "progress.read": True,
    },
    "PERS-AMANDA": {
        "organisation.role.read": True,
        "organisation.entity.read": True,
        "content.plan.read": True,
        "venue.close.read": False,
        "finance.nota.read": True,
        "progress.read": False,
    },
    "PERS-MISA": {
        "organisation.role.read": False,
        "organisation.entity.read": True,
        "content.plan.read": True,
        "venue.close.read": False,
        "finance.nota.read": False,
        "progress.read": False,
    },
    "PERS-LEAD-DEMO": {
        "organisation.role.read": False,
        "organisation.entity.read": False,
        "content.plan.read": False,
        "venue.close.read": False,
        "finance.nota.read": False,
        "progress.read": False,
    },
}
UMA_TARGET = {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}
FINANCE_TARGET = {"entity_id": "ENT-GGV"}

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
        raw = resp.read()
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
        conn.request("GET", path, headers={"User-Agent": "wolf-p0-perm"})
        resp = conn.getresponse()
        resp.read(256)
        status = int(resp.status)
        location = resp.getheader("Location") or ""
        www = resp.getheader("WWW-Authenticate") or ""
        server = resp.getheader("Server") or ""
    finally:
        conn.close()
    return status, location, www, server


def _callers() -> tuple[tuple[str, dict[str, str] | None, str], ...]:
    return (
        ("unsigned", None, "plain"),
        ("spoofed email", {"Cf-Access-Authenticated-User-Email": SPOOF_EMAIL}, "plain"),
        ("spoofed subject", {"X-Wolf-Subject": "PERS-MATT"}, "plain"),
        ("bad jwt", {"Cf-Access-Jwt-Assertion": BAD_JWT}, "jwt"),
    )


def _no_catalog(body: dict) -> list[str]:
    leaked = []
    for key in LEAK_KEYS:
        value = body.get(key)
        if key in ("permissions", "role_grants") and isinstance(value, list):
            leaked.append(key)
        elif key in ("person_id", "email") and value not in (None, ""):
            leaked.append(key)
    return leaked


def test_listeners(beta_pid: str) -> None:
    prod = _listener(PROD_PID)
    check("prod pid 15975 still serve.py", "serve.py" in prod and "8787" in prod, prod[:160])
    check("beta pid listening", bool(beta_pid), "no listener")
    beta = _listener(beta_pid) if beta_pid else ""
    check("beta command is serve_beta.py", "serve_beta.py" in beta, beta[:160])


def test_catalog_route_denies() -> None:
    for label, headers, kind in _callers():
        expect = "invalid_token" if kind == "jwt" else "missing_auth"
        status, body = _origin(CATALOG_PATH, headers)
        leaked = _no_catalog(body)
        check(
            f"{label} {CATALOG_PATH} 403 {expect}",
            status == 403 and body.get("error") == expect and body.get("ok") is not True,
            f"status={status} error={body.get('error')}",
        )
        check(
            f"{label} {CATALOG_PATH} no catalog body",
            not leaked,
            ",".join(leaked),
        )
        if headers and "Cf-Access-Authenticated-User-Email" in headers:
            check(
                f"{label} {CATALOG_PATH} does not accept the header",
                SPOOF_EMAIL not in json.dumps(body),
            )


def test_me_permissions_still_denied() -> None:
    for label, headers, kind in _callers():
        expect = "invalid_token" if kind == "jwt" else "missing_auth"
        status, body = _origin(ME_PATH, headers)
        check(
            f"{label} {ME_PATH} 403 {expect}",
            status == 403 and body.get("error") == expect and body.get("ok") is not True,
            f"status={status} error={body.get('error')}",
        )


def test_seat_routes_still_denied() -> None:
    """Unsigned half of the seat matrix. A seated allow is not this function."""
    for path, plain, jwt_error in SEAT_ROUTES:
        for label, headers, kind in _callers():
            expect = jwt_error if kind == "jwt" else plain
            status, body = _origin(path, headers)
            leaked = _no_catalog(body)
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
                f"{label} {path} no catalog body",
                not leaked,
                ",".join(leaked),
            )


def test_public_login() -> None:
    paths = (CATALOG_PATH, ME_PATH) + tuple(path for path, _, _ in SEAT_ROUTES)
    for path in paths:
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


def _target_for(code: str) -> dict[str, str]:
    if code == "venue.close.read":
        return UMA_TARGET
    if code == "finance.nota.read":
        return FINANCE_TARGET
    return rbac.default_content_target()


def _counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        "org_permissions": int(conn.execute("SELECT COUNT(*) FROM org_permissions").fetchone()[0]),
        "org_role_permissions": int(
            conn.execute("SELECT COUNT(*) FROM org_role_permissions").fetchone()[0]
        ),
        "org_persons": int(conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0]),
    }


def test_catalog_projection(before_counts: dict[str, int]) -> None:
    """Read-only. This is not a seated HTTP allow or deny."""
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        people = [r[0] for r in conn.execute("SELECT person_id FROM org_persons ORDER BY person_id")]
        check("person set unchanged", set(people) == set(SEAT), ",".join(people))
        for person_id, expected in SEAT.items():
            for code, allowed in expected.items():
                actual = rbac.can(person_id, code, _target_for(code), conn=conn)
                word = "has" if allowed else "lacks"
                check(
                    f"catalog {person_id} {word} {code}",
                    actual is allowed,
                )
        cd = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions rp
            JOIN org_permissions p ON p.permission_id = rp.permission_id
            WHERE rp.role_id='ROLE-GGV-CREATIVE-DIRECTOR'
              AND p.code='organisation.entity.read'
            """
        ).fetchone()[0]
        edit = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions rp
            JOIN org_permissions p ON p.permission_id = rp.permission_id
            WHERE rp.role_id='ROLE-GGV-EDIT'
              AND p.code='organisation.entity.read'
            """
        ).fetchone()[0]
        ended = conn.execute(
            """
            SELECT status, end_at FROM org_assignments
            WHERE assignment_id='ASG-HAIKAL-VE-1'
            """
        ).fetchone()
        check("creative director lacks organisation.entity.read", int(cd) == 0, str(cd))
        check("ended edit role still holds organisation.entity.read", int(edit) == 1, str(edit))
        check(
            "ASG-HAIKAL-VE-1 stays ENDED",
            ended is not None and ended["status"] == "ENDED" and ended["end_at"] is not None,
            str(dict(ended) if ended else None),
        )
        check(
            "ended edit grant does not allow PERS-HAIKAL organisation.entity.read",
            rbac.can(
                "PERS-HAIKAL",
                "organisation.entity.read",
                rbac.default_content_target(),
                conn=conn,
            )
            is False,
        )
        after = _counts(conn)
        completion = conn.execute(
            "SELECT COUNT(*) FROM wolf_completion_items WHERE capability='CAP-CORE-04'"
        ).fetchone()[0]
    finally:
        conn.close()
    check("permission catalog counts unchanged", after == before_counts, str(after))
    check("no CAP-CORE-04 completion row was inserted", int(completion) == 0, str(completion))


def test_ledger(before: str) -> None:
    after = _ledger_digest()
    check("ledger digest unchanged", before == after)
    ledger = json.loads(LEDGER.read_text())
    row = ledger.get("CAP-CORE-04") or []
    check("ledger CAP-CORE-04 stays PROVEN", bool(row) and row[0] == "PROVEN", str(row[:1]))
    check("ledger length stays 77", len(ledger) == 77, str(len(ledger)))


def main() -> int:
    before = _ledger_digest()
    count_conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    count_conn.row_factory = sqlite3.Row
    try:
        before_counts = _counts(count_conn)
    finally:
        count_conn.close()
    beta_pid = _beta_pid()
    print(f"NOTE  beta_pid={beta_pid or 'absent'} prod_pid={PROD_PID}")
    test_listeners(beta_pid)
    test_catalog_route_denies()
    test_me_permissions_still_denied()
    test_seat_routes_still_denied()
    test_public_login()
    test_catalog_projection(before_counts)
    test_ledger(before)
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
