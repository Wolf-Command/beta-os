#!/usr/bin/env python3
"""CAP-CORE-12 independence read. Names the owner retain set. Marks no day done."""
from __future__ import annotations

import inspect
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)
os.environ.pop("WOLF_CANONICAL_WRITE_OVERRIDE", None)

from core import escalation_burndown as burn  # noqa: E402
from core.canonical_guard import CanonicalGuardError, assert_write_allowed  # noqa: E402
from core.staff_home import _founder  # noqa: E402
from core.work_loop import founder_dependency  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
EVIDENCE_ID = "EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153"
CR_ID = "CR-6e3fd7b9d7edca0e"
WINDOWS = (7, 30, 90, 365)
NOW = datetime(2026, 9, 19, 12, 0, tzinfo=burn.WITA)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def _ledger_counts() -> tuple[int, int, int, str | None, int, int]:
    conn = _ro(CATALOG)
    try:
        evidence = int(conn.execute("SELECT COUNT(*) FROM core_evidence_records").fetchone()[0])
        exceptions = int(conn.execute("SELECT COUNT(*) FROM core_governance_exceptions").fetchone()[0])
        approvals = int(conn.execute("SELECT COUNT(*) FROM core_approval_decisions").fetchone()[0])
        status = conn.execute(
            "SELECT status FROM core_evidence_records WHERE evidence_id=?",
            (EVIDENCE_ID,),
        ).fetchone()
        needs = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM wolf_completion_items
                WHERE blocker_class='NEEDS_MATT' AND state!='RESOLVED'
                """
            ).fetchone()[0]
        )
        delegations = int(conn.execute("SELECT COUNT(*) FROM core_delegations").fetchone()[0])
    finally:
        conn.close()
    return (
        evidence,
        exceptions,
        approvals,
        None if status is None else str(status[0]),
        needs,
        delegations,
    )


def _expected_retain() -> list[str]:
    names: list[str] = []
    for name, label in founder_dependency().items():
        if label == "RETAIN" and name not in names:
            names.append(name)
    for name, label in _founder("owner_pulse").items():
        if label == "RETAIN" and name not in names:
            names.append(name)
    return names


def _schema(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE wolf_completion_items (
          id TEXT PRIMARY KEY,
          state TEXT,
          blocker_class TEXT,
          capability TEXT,
          domain TEXT,
          item_type TEXT,
          first_seen TEXT,
          resolved_at TEXT,
          resolution_evidence TEXT
        );
        CREATE TABLE core_delegations (
          delegation_id TEXT PRIMARY KEY,
          status TEXT,
          effective_from TEXT,
          effective_to TEXT
        );
        """
    )
    conn.commit()
    conn.close()


def _iso(day: datetime) -> str:
    return day.astimezone(burn.WITA).isoformat(timespec="seconds")


def _forbidden(value: object, prefix: str = "") -> str:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"person_id", "delegator_person_id", "delegate_person_id", "identifier", "email"}:
                return prefix + key
            found = _forbidden(item, prefix + key + ".")
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _forbidden(item, prefix)
            if found:
                return found
    elif isinstance(value, str) and ("@" in value or value.startswith("PERS-")):
        return prefix + value
    return ""


def test_fixture(td: Path) -> None:
    clear_db = td / "clear.sqlite"
    _schema(clear_db)
    conn = sqlite3.connect(clear_db)
    conn.execute(
        """
        INSERT INTO wolf_completion_items
          (id, state, blocker_class, capability, domain, item_type, first_seen)
        VALUES ('CR-STAFF', 'OPEN', 'NEEDS_STAFF', 'CAP-X', 'CORE', 'NOTE', ?)
        """,
        (_iso(NOW - timedelta(days=1)),),
    )
    conn.commit()
    conn.close()
    clear = burn.read_owner_independence(clear_db, now=NOW, ledger_path=td / "missing.json")
    check(
        "clear window is not a finished day",
        all(row["independence"] == "CLEAR" and row["independence_day_done"] is False for row in clear["windows"]),
    )
    check("clear days list stays empty", clear["independence_days_done"] == [] and clear["any_independence_day_done"] is False)
    check("fixture retain names stay", clear["retain_names"] == _expected_retain())
    check("fixture needs matt empty is not independence", clear["needs_matt_labeled"] == 0 and clear["empty_needs_matt_is_independence"] is False)
    check("fixture delegation not evidenced", clear["delegated_decision"]["evidenced"] is False)

    open_db = td / "open.sqlite"
    _schema(open_db)
    conn = sqlite3.connect(open_db)
    conn.execute(
        """
        INSERT INTO wolf_completion_items
          (id, state, blocker_class, capability, domain, item_type, first_seen)
        VALUES ('CR-MATT', 'OPEN', 'NEEDS_MATT', 'CAP-FIN-05', 'FIN', 'NOTE', ?)
        """,
        (_iso(NOW - timedelta(days=2)),),
    )
    conn.execute(
        """
        INSERT INTO wolf_completion_items
          (id, state, blocker_class, capability, domain, item_type, first_seen)
        VALUES ('CR-POL', 'OPEN', 'NEEDS_POLICY', NULL, 'BZG', 'POLICY_BOUNDARY', ?)
        """,
        (_iso(NOW - timedelta(days=2)),),
    )
    conn.commit()
    conn.close()
    opened = burn.read_owner_independence(open_db, now=NOW, ledger_path=td / "missing.json")
    check(
        "open needs matt is named",
        opened["needs_matt_items"] == [
            {
                "id": "CR-MATT",
                "capability": "CAP-FIN-05",
                "state": "OPEN",
                "dated": True,
                "independence_day_done": False,
            }
        ],
    )
    check("open window stays open and undone", opened["windows"][0]["independence"] == "OPEN" and opened["windows"][0]["independence_day_done"] is False)
    check("policy row is not reclassified", opened["policy_not_reclassified"] == 1 and opened["policy_items"][0]["reclassified"] is False)
    check("named owner list keeps the capability", "CAP-FIN-05" in opened["still_requires_owner"])

    missing = burn.read_owner_independence(td / "nope.sqlite", now=NOW, ledger_path=td / "missing.json")
    check("missing catalog does not invent a zero", missing["needs_matt_items"] is None and missing["still_requires_owner"] is None)
    check("missing catalog still names retain", missing["retain_names"] == _expected_retain())
    check("missing catalog marks no day", missing["any_independence_day_done"] is False)


def main() -> int:
    ledger_before = LEDGER.read_bytes()
    before = _ledger_counts()
    with tempfile.TemporaryDirectory() as raw:
        test_fixture(Path(raw))
    report = burn.read_owner_independence()
    expected = _expected_retain()
    check("live read", report["ok"] is True and report["read_only"] is True and report["cap"] == "CAP-CORE-12")
    check("four windows", [row["days"] for row in report["windows"]] == list(WINDOWS))
    check(
        "no independence day done",
        report["independence_days_done"] == []
        and report["any_independence_day_done"] is False
        and all(row["independence_day_done"] is False and row["proven"] is False and row["operating_test"] is False for row in report["windows"]),
    )
    check("retain names match the existing labels", report["retain_names"] == expected, str(report.get("retain_names")))
    check(
        "retain rows are unmeasured",
        [row["name"] for row in report["retain"]]
        == [name for name, label in founder_dependency().items() if label == "RETAIN"]
        + [name for name, label in _founder("owner_pulse").items() if label == "RETAIN"]
        and all(
            row["measured"] is False and row["independence_day_done"] is False and row["label"] == "RETAIN"
            for row in report["retain"]
        ),
    )
    check(
        "labeled needs matt matches the store",
        report["needs_matt_labeled"] == before[4]
        and report["needs_matt_open"] == before[4]
        and report["empty_needs_matt_is_independence"] is False
        and report["still_requires_owner"] == expected,
    )
    check(
        "delegations stored match the table",
        report["delegation_rows"] == before[5]
        and report["delegation_status"] == "READ"
        and report["delegated_decision"]["label"] == "ELIMINATE"
        and report["delegated_decision"]["evidenced"] is False
        and report["delegated_decision"]["audit_is_current_grant"] is False
        and report["delegated_decision"]["independence_day_done"] is False,
    )
    audit = report.get("delegation_audit") or {}
    conn = _ro(CATALOG)
    try:
        created = int(
            conn.execute(
                "SELECT COUNT(*) FROM core_audit_events WHERE action='delegation.created'"
            ).fetchone()[0]
        )
        used = int(
            conn.execute(
                "SELECT COUNT(*) FROM core_audit_events WHERE action='delegation.used'"
            ).fetchone()[0]
        )
        revoked = int(
            conn.execute(
                "SELECT COUNT(*) FROM core_audit_events WHERE action='delegation.revoked'"
            ).fetchone()[0]
        )
        policy = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM wolf_completion_items
                WHERE blocker_class='NEEDS_POLICY' AND state!='RESOLVED'
                """
            ).fetchone()[0]
        )
        cr = conn.execute(
            "SELECT state, blocker_class, capability FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
    finally:
        conn.close()
    check(
        "audit counts are not a current grant",
        report["delegation_audit_status"] == "READ"
        and audit.get("delegation.created") == created
        and audit.get("delegation.used") == used
        and audit.get("delegation.revoked") == revoked,
        str(audit),
    )
    check("policy rows stay policy", report["policy_not_reclassified"] == policy and policy == 5, str(policy))
    check(
        "cr stays engineering",
        cr == ("OPEN", "NEEDS_ENGINEERING", "CAP-CORE-12")
        and report["cr_resolved"] is False
        and (report.get("honesty") or {}).get("cr_state") == "OPEN"
        and (report.get("honesty") or {}).get("cr_blocker") == "NEEDS_ENGINEERING",
        str(cr),
    )
    flags = report.get("honesty") or {}
    check(
        "ledger stays built",
        flags.get("maturity") == "BUILT"
        and flags.get("proven") is False
        and report["proven"] is False
        and report["operating_test"] is False
        and json.loads(LEDGER.read_text(encoding="utf-8"))["CAP-CORE-12"][0] == "BUILT",
    )
    check(
        "gates stay unset",
        report["staff_ready"] is False
        and report["human_commissioned"] is False
        and report["operating_adoption"] == "NOT MEASURED"
        and report["catalog_write"] is False
        and report["ledger_write"] is False
        and report["needs_matt_auto_cleared"] is False,
    )
    check("ids stay out of the report", _forbidden(report) == "", _forbidden(report))
    reader = inspect.getsource(burn.read_owner_independence)
    check("reader has no store statement", "INSERT INTO" not in reader and "UPDATE " not in reader and "DELETE " not in reader)
    check("reader does not select a person id", "person_id" not in reader)
    check("reader opens read-only", "mode=ro" in inspect.getsource(burn._open_ro))
    try:
        burn.read_owner_independence("/tmp/wolf-system/not-a-catalog.sqlite")
        check("outside path refused", False, "no raise")
    except burn.BurndownError as exc:
        check("outside path refused", exc.code == "not_beta", exc.code)
    try:
        burn.refuse_needs_matt_clear({"id": CR_ID})
        check("clear refused", False, "no raise")
    except burn.BurndownError as exc:
        check("clear refused", exc.code == "writes_refused", exc.code)
    try:
        assert_write_allowed(CATALOG)
        check("guard refuses canonical write", False, "no raise")
    except CanonicalGuardError as exc:
        text = str(exc)
        print(text)
        check("guard refuses canonical write", "test process refuses canonical Beta write" in text, text)
    insert_refused = False
    conn = sqlite3.connect(str(CATALOG))
    try:
        conn.execute(
            """
            INSERT INTO core_delegations (
              delegation_id, delegator_person_id, delegator_assignment_id,
              delegate_person_id, delegate_assignment_id, entity_id, scope_id,
              permission_id, permission_code, effective_from, effective_to,
              status, created_at, created_by_person_id, correlation_id, allow_redelegation
            ) VALUES (
              'DLG-PACK-F6', 'x', 'x', 'y', 'y', 'ENT-GGV', 'x', 'x', 'x',
              '2026-09-28T00:00:00Z', '2026-10-28T00:00:00Z', 'ACTIVE',
              '2026-09-28T00:00:00Z', 'x', 'x', 0
            )
            """
        )
        conn.commit()
    except sqlite3.Error:
        insert_refused = True
    finally:
        conn.close()
    check("guard denies delegation insert", insert_refused)

    after = _ledger_counts()
    check("evidence count unchanged", after[0] == before[0] == 4, str(after[0]))
    check("exception count unchanged", after[1] == before[1] == 3, str(after[1]))
    check("approval count unchanged", after[2] == before[2] == 9, str(after[2]))
    check("preserved evidence stays invalidated", before[3] == "INVALIDATED" and after[3] == "INVALIDATED", str(after[3]))
    check("needs matt unchanged", after[4] == before[4], f"{before[4]} -> {after[4]}")
    check("delegations unchanged", after[5] == before[5], f"{before[5]} -> {after[5]}")
    check("ledger file unchanged", LEDGER.read_bytes() == ledger_before)
    day_state = ",".join(str(row["independence"]) for row in report["windows"])
    print(
        "COUNTS needs_matt={needs} delegations={dlg} windows={windows} "
        "days_done=0 retain={retain} policy_not_reclassified={policy} "
        "audit_created={created} audit_used={used} audit_revoked={revoked} "
        "evidenced={evidenced}".format(
            needs=report.get("needs_matt_labeled"),
            dlg=report.get("delegation_rows"),
            windows=day_state,
            retain=",".join(report.get("retain_names") or []),
            policy=report.get("policy_not_reclassified"),
            created=audit.get("delegation.created"),
            used=audit.get("delegation.used"),
            revoked=audit.get("delegation.revoked"),
            evidenced=report["delegated_decision"]["evidenced"],
        )
    )
    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAILED")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
