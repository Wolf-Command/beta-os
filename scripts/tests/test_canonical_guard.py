#!/usr/bin/env python3
"""Prove the canonical guard refuses prod and test writes to Beta."""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["WOLF_ALLOW_LIVE_AUDIT"] = "1"
os.environ["WOLF_CANONICAL_WRITE_OVERRIDE"] = "1"

from core.canonical_guard import (  # noqa: E402
    BETA_CATALOG,
    CanonicalGuardError,
    assert_write_allowed,
    backup_catalog,
    decide,
    install,
)

PASS = 0
FAIL = 0
PROD_PATH = Path("/Users/wolfterminal/.openclaw/workspace/wolf-system/catalog/content_library.sqlite")
PRESERVED = "EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _ro_count(sql: str) -> int:
    conn = sqlite3.connect(f"file:{BETA_CATALOG}?mode=ro", uri=True)
    try:
        return int(conn.execute(sql).fetchone()[0])
    finally:
        conn.close()


def main() -> int:
    install()
    before = _ro_count("SELECT COUNT(*) FROM core_evidence_records")
    decisions = _ro_count("SELECT COUNT(*) FROM core_approval_decisions")
    exceptions = _ro_count("SELECT COUNT(*) FROM core_governance_exceptions")

    check("test read of canonical beta is allowed", decide(BETA_CATALOG, write=False, test_process=True) == "allow")
    check(
        "test write of canonical beta is refused",
        decide(BETA_CATALOG, write=True, test_process=True, override=True) == "refuse",
    )
    check(
        "legacy bypass does not allow a test write",
        decide(BETA_CATALOG, write=True, test_process=True, override=False) == "refuse",
    )
    check(
        "non-test prod write is refused",
        decide(PROD_PATH, write=True, test_process=False) == "refuse",
    )
    check(
        "test prod read is refused",
        decide(PROD_PATH, write=False, test_process=True) == "refuse",
    )
    check(
        "non-test beta write without override is allowed for the server",
        decide(BETA_CATALOG, write=True, test_process=False, override=False) == "allow",
    )
    check(
        "non-test beta override is the logged allow",
        decide(BETA_CATALOG, write=True, test_process=False, override=True) == "allow-override",
    )

    refused = False
    try:
        assert_write_allowed(BETA_CATALOG)
    except CanonicalGuardError:
        refused = True
    check("assert_write_allowed refuses this test process", refused)

    prod_refused = False
    try:
        sqlite3.connect(str(PROD_PATH))
    except CanonicalGuardError:
        prod_refused = True
    check("opening a prod path from a test raises before connect", prod_refused)

    write_refused = False
    conn = sqlite3.connect(str(BETA_CATALOG))
    try:
        conn.execute(
            "INSERT INTO core_evidence_records (evidence_id) VALUES ('EVD-F1-SHOULD-NOT-LAND')"
        )
        conn.commit()
    except (CanonicalGuardError, sqlite3.DatabaseError, sqlite3.OperationalError, sqlite3.IntegrityError):
        write_refused = True
    finally:
        conn.close()
    check("insert into canonical beta evidence is refused", write_refused)

    after = _ro_count("SELECT COUNT(*) FROM core_evidence_records")
    check("evidence count unchanged", before == after, f"{before} -> {after}")
    check(
        "approval decision count unchanged",
        decisions == _ro_count("SELECT COUNT(*) FROM core_approval_decisions"),
    )
    check(
        "exception count unchanged",
        exceptions == _ro_count("SELECT COUNT(*) FROM core_governance_exceptions"),
    )
    status = sqlite3.connect(f"file:{BETA_CATALOG}?mode=ro", uri=True).execute(
        "SELECT status, invalidate_reason FROM core_evidence_records WHERE evidence_id=?",
        (PRESERVED,),
    ).fetchone()
    check(
        "EVD-50e827bd stays INVALIDATED",
        status is not None and status[0] == "INVALIDATED" and status[1] == "P4-TEST cleanup",
        str(status),
    )
    triggers = {
        row[0]
        for row in sqlite3.connect(f"file:{BETA_CATALOG}?mode=ro", uri=True).execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE '%no_delete%'"
        )
    }
    for name in (
        "trg_core_evidence_records_no_delete",
        "trg_core_governance_exceptions_no_delete",
        "trg_core_approval_decisions_no_delete",
    ):
        check(f"trigger remains {name}", name in triggers)

    iso = backup_catalog()
    copy = sqlite3.connect(str(iso))
    try:
        copied = int(copy.execute("SELECT COUNT(*) FROM core_evidence_records").fetchone()[0])
        check("temp copy has the evidence rows", copied == before, str(copied))
        copy.execute("CREATE TABLE f1_guard_probe (id INTEGER)")
        copy.commit()
        check(
            "temp copy accepts a write",
            copy.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='f1_guard_probe'"
            ).fetchone()
            is not None,
        )
    finally:
        copy.close()
    check(
        "temp write did not change canonical evidence",
        _ro_count("SELECT COUNT(*) FROM core_evidence_records") == before,
    )

    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
