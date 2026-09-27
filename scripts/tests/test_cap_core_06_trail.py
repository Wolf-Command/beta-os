#!/usr/bin/env python3
"""CAP-CORE-06 temporary trail for one work item.

The item is created on a copy of the catalog and walked through the stored
states. The copy is removed. The live catalog is not given a work item.
Unsigned, spoofed, and bad-JWT callers stay denied on Beta. A seated read
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

from core import audit as audit_mod  # noqa: E402
from core import organisation as org_mod  # noqa: E402
from core import scope as scope_mod  # noqa: E402
from core import work_items as wi  # noqa: E402

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
CR_IDS = ("CR-3cd31e220f788bc6", "CR-4b78e43ab35126a8")
PROD_PID = "15975"
ORIGIN = ("127.0.0.1", 8788)
PUBLIC_HOST = "beta.wolfcommand.net"
LOGIN_HOST = "wolfcommand.cloudflareaccess.com"
LOGIN_PATH = "/cdn-cgi/access/login/beta.wolfcommand.net"
PATHS = ("/api/core/work-items", "/api/core/work-items/WI-NONE")
SPOOF_EMAIL = "spoofed@example.invalid"
BAD_JWT = "a.b.c"
PERSON = "PERS-MATT"
ASSIGNMENT = "ASG-MATT-OWNER-1"
ENTITY = "ENT-GGV"
TRAIL = (
    "OPEN",
    "IN_PROGRESS",
    "BLOCKED",
    "IN_PROGRESS",
    "COMPLETED",
    "VERIFIED",
)
ACTIONS = (
    "work.create",
    "work.start",
    "work.block",
    "work.start",
    "work.complete",
    "work.verify",
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


def _live_counts() -> tuple[int, int, int]:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        items = int(conn.execute("SELECT COUNT(*) FROM core_work_items").fetchone()[0])
        audits = int(conn.execute("SELECT COUNT(*) FROM core_audit_events").fetchone()[0])
        work_audits = int(
            conn.execute(
                "SELECT COUNT(*) FROM core_audit_events WHERE source='work_items'"
            ).fetchone()[0]
        )
    finally:
        conn.close()
    return items, audits, work_audits


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
        conn.request("GET", path, headers={"User-Agent": "wolf-p0-work"})
        resp = conn.getresponse()
        resp.read(256)
        status = int(resp.status)
        location = resp.getheader("Location") or ""
        www = resp.getheader("WWW-Authenticate") or ""
        server = resp.getheader("Server") or ""
    finally:
        conn.close()
    return status, location, www, server


def _point_at(tmp_db: Path) -> None:
    for mod in (wi, audit_mod, org_mod, scope_mod):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = tmp_db


def test_listeners(beta_pid: str) -> None:
    prod = _listener(PROD_PID)
    check("prod pid 15975 still serve.py", "serve.py" in prod and "8787" in prod, prod[:160])
    check("beta pid listening", bool(beta_pid), "no listener")
    beta = _listener(beta_pid) if beta_pid else ""
    check("beta command is serve_beta.py", "serve_beta.py" in beta, beta[:160])


def test_temporary_trail(live_before: tuple[int, int, int]) -> None:
    td = ROOT / "catalog" / "backups" / f"tmp-cap-core-06-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    tmp_db = td / "content_library.sqlite"
    try:
        shutil.copy2(CATALOG, tmp_db)
        check("temp copy is under beta-os", "beta-os" in str(tmp_db.resolve()))
        check("temp copy is not the live catalog", tmp_db.resolve() != CATALOG.resolve())
        _point_at(tmp_db)
        check(
            "work_items catalog is the temp copy",
            Path(wi.CATALOG_DB).resolve() == tmp_db.resolve(),
        )

        item = wi.create_work_item(
            title="CAP-CORE-06 temporary trail",
            owning_entity_id=ENTITY,
            work_type="GENERAL",
            source_type="HUMAN",
            created_by_actor_type="PERSON",
            verified_person_id=PERSON,
            owner_person_id=PERSON,
            owner_org_assignment_id=ASSIGNMENT,
            priority=3,
        )
        wid = item["work_item_id"]
        check("create stores OPEN", item["status"] == "OPEN" and item["created_by_person_id"] == PERSON)
        check("creator is a person id", item["created_by_person_id"].startswith("PERS-"))

        wi.start_work_item(wid, verified_person_id=PERSON)
        started = wi.get_work_item(wid)
        check(
            "start stores IN_PROGRESS",
            started is not None and started["status"] == "IN_PROGRESS" and bool(started.get("started_at")),
        )

        illegal = False
        try:
            wi.verify_work_item(wid, verified_person_id=PERSON)
        except wi.WorkItemError as exc:
            illegal = exc.code == "illegal_transition"
        held = wi.get_work_item(wid)
        check("verify from IN_PROGRESS is denied", illegal)
        check(
            "denied verify leaves IN_PROGRESS",
            held is not None and held["status"] == "IN_PROGRESS" and held.get("verified_at") in (None, ""),
        )

        wi.block_work_item(wid, verified_person_id=PERSON)
        check("block stores BLOCKED", (wi.get_work_item(wid) or {}).get("status") == "BLOCKED")
        wi.start_work_item(wid, verified_person_id=PERSON)
        check(
            "restart stores IN_PROGRESS",
            (wi.get_work_item(wid) or {}).get("status") == "IN_PROGRESS",
        )
        done = wi.claim_complete(
            wid,
            verified_person_id=PERSON,
            outcome="temporary trail claimed",
        )
        check(
            "complete stores COMPLETED and not VERIFIED",
            done["status"] == "COMPLETED" and bool(done.get("completed_at")) and done.get("verified_at") in (None, ""),
        )
        verified = wi.verify_work_item(wid, verified_person_id=PERSON)
        check(
            "verify stores VERIFIED",
            verified["status"] == "VERIFIED" and bool(verified.get("verified_at")),
        )

        conn = sqlite3.connect(f"file:{tmp_db}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                """
                SELECT action, metadata_json
                FROM core_audit_events
                WHERE resource_type='work_item' AND resource_id=? AND source='work_items'
                ORDER BY recorded_at, rowid
                """,
                (wid,),
            ).fetchall()
        finally:
            conn.close()
        actions = [row[0] for row in rows]
        statuses = []
        for row in rows:
            meta = json.loads(row[1] or "{}")
            statuses.append(meta.get("status"))
        check("audit actions are the stored trail", tuple(actions) == ACTIONS, str(actions))
        check("audit statuses are the stored trail", tuple(statuses) == TRAIL, str(statuses))
        print("NOTE  trail=" + ">".join(TRAIL))
    finally:
        _point_at(CATALOG)
        shutil.rmtree(td, ignore_errors=True)
    check("temp copy removed", not td.exists())
    after_trail = _live_counts()
    check("live work-item count unchanged after the trail", after_trail[0] == live_before[0], str(after_trail))
    check("live audit count unchanged after the trail", after_trail[1] == live_before[1], str(after_trail))
    check(
        "live work-item audit count unchanged after the trail",
        after_trail[2] == live_before[2],
        str(after_trail),
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
                f"{label} GET {path} no work item",
                "work_item" not in body and "work_items" not in body and body.get("person_id") in (None, ""),
                f"keys={sorted(body)}",
            )
    status, body = _origin(
        "POST",
        "/api/core/work-items",
        {"Content-Type": "application/json"},
        b'{"title":"must-not-land"}',
    )
    check(
        "unsigned POST /api/core/work-items 403",
        status == 403 and body.get("ok") is not True and "work_item" not in body,
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


def test_ledger_and_rows(before: str, live_before: tuple[int, int, int]) -> None:
    after_items, after_audits, after_work_audits = _live_counts()
    print(
        f"NOTE  live_work_items_after={after_items} "
        f"live_audit_events_after={after_audits} "
        f"live_work_item_audits_after={after_work_audits}"
    )
    check("live work-item count still matches the start", after_items == live_before[0], str(after_items))
    check(
        "live work-item audit count still matches the start",
        after_work_audits == live_before[2],
        str(after_work_audits),
    )
    check("live work-item count is the stored empty table", after_items == 0, str(after_items))
    check("ledger digest unchanged", _ledger_digest() == before)
    ledger = json.loads(LEDGER.read_text())
    row = ledger.get("CAP-CORE-06") or []
    check("ledger CAP-CORE-06 stays PROVEN", bool(row) and row[0] == "PROVEN", str(row[:1]))
    check("ledger length stays 77", len(ledger) == 77, str(len(ledger)))
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        for cr_id in CR_IDS:
            found = conn.execute(
                "SELECT state, capability FROM wolf_completion_items WHERE id=?",
                (cr_id,),
            ).fetchone()
            check(
                f"{cr_id} stays OPEN",
                found is not None and found[0] == "OPEN" and found[1] == "CAP-CORE-06",
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
        f"NOTE  live_work_items={live_before[0]} "
        f"live_audit_events={live_before[1]} "
        f"live_work_item_audits={live_before[2]}"
    )
    test_listeners(beta_pid)
    test_temporary_trail(live_before)
    test_origin_denies()
    test_public_login()
    test_ledger_and_rows(before, live_before)
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
