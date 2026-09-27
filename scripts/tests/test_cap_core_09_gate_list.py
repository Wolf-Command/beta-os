#!/usr/bin/env python3
"""CAP-CORE-09 evidence-gate inventory.

Names each material action already in Wolf Core as gated or not gated.
Reads the live catalog. Inserts no evidence row and no requirement row.
The ledger is not raised. A seated session is not minted.
The live evidence count was 3 before scripts/tests/test_work_loop.py.
That suite left one invalidated row because hard delete is refused.
This test does not drop the trigger and does not delete that row.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
PROD_PID = "15975"
CR_ID = "CR-e594ea7dc79599e7"
LIVE_REQUIREMENT = "EVR-HABITAT-CONTENT-PUBLISH"
LIVE_ACTION = "HABITAT.CONTENT.PUBLISH"
# The inventory does not insert these. test_work_loop.py writes the live catalog
# and its cleanup invalidates evidence instead of deleting it. The no-delete
# trigger stays. The fourth row is that residue from 2026-09-27T10:06:44Z.
ORIGINAL_EVIDENCE = (
    "EVD-LEAD-DEMO-VERIFIED",
    "EVD-f537c61a-6541-4fa7-8ea5-c972eab2ef95",
    "EVD-ebe6df48-4676-4e69-ad70-fd7e54882d2f",
)
SUITE_EVIDENCE = "EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153"
SUITE_DECISIONS = (
    "APD-94bacc16-d184-4f8f-86d5-b46cb246791f",
    "APD-0208eeb0-2d4a-453a-8946-32cfcd44ed46",
    "APD-1b7a9d12-8ff3-4159-b054-dd79318e8a02",
)

# action, relative path, function, gate, needle
# gated: needle must appear in the function.
# not_gated: needle must not appear. Those actions stay open.
ACTIONS = (
    (
        "approval.request",
        "scripts/core/approvals.py",
        "create_approval_request",
        "gated",
        "_enforce_evidence_gate",
    ),
    (
        "approval.decide",
        "scripts/core/approvals.py",
        "_decide",
        "gated",
        "_enforce_evidence_gate",
    ),
    (
        "work.loop.submit",
        "scripts/core/work_loop.py",
        "submit_item",
        "gated",
        "missing_required_evidence",
    ),
    (
        "HABITAT.CONTENT.PUBLISH",
        "scripts/core/content_publish.py",
        "assert_habitat_publish_allowed",
        "gated",
        "evaluate_evidence_requirements",
    ),
    (
        "HABITAT.CONTENT.PUBLISH.submit",
        "scripts/core/content_publish.py",
        "submit_for_approval",
        "gated",
        "enforce_evidence=True",
    ),
    (
        "SPEND_APPROVE",
        "scripts/core/governance_policy.py",
        "REQUEST_TYPE_TO_ACTION",
        "gated",
        '"SPEND": "SPEND_APPROVE"',
    ),
    (
        "EXCEPTION",
        "scripts/core/governance_policy.py",
        "REQUEST_TYPE_TO_ACTION",
        "gated",
        '"EXCEPTION": "EXCEPTION"',
    ),
    (
        "GENERAL_MATERIAL",
        "scripts/core/governance_policy.py",
        "REQUEST_TYPE_TO_ACTION",
        "gated",
        '"GENERAL": "GENERAL_MATERIAL"',
    ),
    (
        "venue.close.declare_cash",
        "scripts/core/venue_close.py",
        "attach_declared_cash",
        "not_gated",
        "evaluate_evidence_requirements",
    ),
    (
        "venue.close.resolve_exception",
        "scripts/core/venue_close.py",
        "resolve_exception",
        "not_gated",
        "evaluate_evidence_requirements",
    ),
    (
        "venue.close.verify",
        "scripts/core/venue_close.py",
        "verify_close",
        "not_gated",
        "evaluate_evidence_requirements",
    ),
    (
        "ggv.nota.submit",
        "scripts/core/ggv_finance_nota.py",
        "submit_nota",
        "not_gated",
        "evaluate_evidence_requirements",
    ),
    (
        "uma.receive_goods",
        "scripts/core/uma_devi_p0.py",
        "receive_goods",
        "not_gated",
        "evaluate_evidence_requirements",
    ),
    (
        "work.item.complete",
        "scripts/core/work_loop.py",
        "decide_item",
        "not_gated",
        "evaluate_evidence_requirements",
    ),
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


def _function_source(text: str, name: str) -> str:
    if name == "REQUEST_TYPE_TO_ACTION":
        marker = "REQUEST_TYPE_TO_ACTION = {"
        start = text.find(marker)
        if start < 0:
            return ""
        end = text.find("\n}", start)
        if end < 0:
            return ""
        return text[start : end + 2]
    marker = f"def {name}("
    start = text.find(marker)
    if start < 0:
        return ""
    rest = text[start + 1 :]
    nxt = rest.find("\ndef ")
    if nxt < 0:
        return text[start:]
    return text[start : start + 1 + nxt]


def _live(conn: sqlite3.Connection) -> dict:
    records = int(conn.execute("SELECT COUNT(*) FROM core_evidence_records").fetchone()[0])
    requirements = int(
        conn.execute("SELECT COUNT(*) FROM core_evidence_requirements").fetchone()[0]
    )
    active = conn.execute(
        """
        SELECT requirement_id, action_type, status
        FROM core_evidence_requirements
        WHERE status='ACTIVE'
        ORDER BY requirement_id
        """
    ).fetchall()
    cr = conn.execute(
        "SELECT state FROM wolf_completion_items WHERE id=?",
        (CR_ID,),
    ).fetchone()
    return {
        "records": records,
        "requirements": requirements,
        "active": [(str(r[0]), str(r[1]), str(r[2])) for r in active],
        "cr": None if cr is None else str(cr[0]),
    }


def test_list() -> None:
    gated = [row[0] for row in ACTIONS if row[3] == "gated"]
    open_actions = [row[0] for row in ACTIONS if row[3] == "not_gated"]
    check("list names gated actions", len(gated) == 8, str(gated))
    check("list names open actions", len(open_actions) == 6, str(open_actions))
    check("every action is gated or not_gated", all(row[3] in {"gated", "not_gated"} for row in ACTIONS))
    seen: set[str] = set()
    for action, rel, fn, gate, needle in ACTIONS:
        path = ROOT / rel
        text = path.read_text(encoding="utf-8")
        body = _function_source(text, fn)
        check(f"{action} function {fn} exists", bool(body), rel)
        if not body:
            continue
        key = f"{rel}:{fn}:{action}"
        check(f"{action} listed once per function role", key not in seen)
        seen.add(key)
        if gate == "gated":
            check(f"{action} calls the gate", needle in body, needle)
        else:
            check(f"{action} stays not gated", needle not in body, "evaluator present")
    policy = (ROOT / "scripts/core/governance_policy.py").read_text(encoding="utf-8")
    check("SPEND maps through the approval action", '"SPEND": "SPEND_APPROVE"' in policy)
    check("EXCEPTION maps through the approval action", '"EXCEPTION": "EXCEPTION"' in policy)
    check("GENERAL maps through the approval action", '"GENERAL": "GENERAL_MATERIAL"' in policy)
    approvals = (ROOT / "scripts/core/approvals.py").read_text(encoding="utf-8")
    create = _function_source(approvals, "create_approval_request")
    check(
        "bound approval uses the mapped action type",
        "action_type_for_request_type" in create,
    )
    nota = _function_source(
        (ROOT / "scripts/core/ggv_finance_nota.py").read_text(encoding="utf-8"),
        "submit_nota",
    )
    check("nota submit does not force the evidence flag", "enforce_evidence=False" in nota)
    receive = _function_source(
        (ROOT / "scripts/core/uma_devi_p0.py").read_text(encoding="utf-8"),
        "receive_goods",
    )
    check("receive evidence flag defaults off", "require_evidence: bool = False" in receive)
    decide = _function_source(
        (ROOT / "scripts/core/work_loop.py").read_text(encoding="utf-8"),
        "decide_item",
    )
    check("work complete moves to COMPLETED", '"COMPLETED"' in decide)
    check("work complete does not evaluate evidence itself", "evaluate_evidence_requirements" not in decide)
    print("NOTE  gated=" + ",".join(gated))
    print("NOTE  not_gated=" + ",".join(open_actions))


def test_live(before: dict, digest: str, beta_pid: str) -> None:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        after = _live(conn)
        ids = {str(r[0]) for r in conn.execute("SELECT evidence_id FROM core_evidence_records")}
        residue = conn.execute(
            """
            SELECT status, invalidate_reason
            FROM core_evidence_records
            WHERE evidence_id=?
            """,
            (SUITE_EVIDENCE,),
        ).fetchone()
        decisions = int(conn.execute("SELECT COUNT(*) FROM core_approval_decisions").fetchone()[0])
        decision_ids = {
            str(r[0])
            for r in conn.execute("SELECT approval_decision_id FROM core_approval_decisions")
        }
    finally:
        conn.close()
    check(
        "inventory does not change the evidence count",
        before["records"] == after["records"] == 4,
        str(after["records"]),
    )
    check(
        "count is 4 after the work-loop residue, not the earlier 3",
        after["records"] == 4,
        str(after["records"]),
    )
    check("original three evidence ids remain", set(ORIGINAL_EVIDENCE).issubset(ids), str(sorted(ids)))
    check("work-loop residue id is present", SUITE_EVIDENCE in ids)
    check(
        "work-loop residue stays invalidated",
        residue is not None and residue[0] == "INVALIDATED" and residue[1] == "P4-TEST cleanup",
        str(residue),
    )
    check(
        "live evidence requirements stay 1",
        before["requirements"] == 1 and after["requirements"] == 1,
        str(after["requirements"]),
    )
    check(
        "only live requirement is Habitat publish",
        after["active"] == [(LIVE_REQUIREMENT, LIVE_ACTION, "ACTIVE")],
        str(after["active"]),
    )
    check("approval decisions are 9 after the same suite", decisions == 9, str(decisions))
    check(
        "the three new decision ids remain",
        set(SUITE_DECISIONS).issubset(decision_ids),
    )
    check("completion row stays OPEN", before["cr"] == "OPEN" and after["cr"] == "OPEN", str(after["cr"]))
    check("ledger file unchanged", _ledger_digest() == digest)
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    row = data.get("CAP-CORE-09")
    check("ledger CAP-CORE-09 stays PROVEN", isinstance(row, list) and row and row[0] == "PROVEN", str(row[:1] if row else None))
    check("ledger row count stays 77", len(data) == 77, str(len(data)))
    prod = _listener(PROD_PID)
    check("production pid 15975 still serve.py", "serve.py" in prod and "8787" in prod, prod[:120])
    check("beta pid unchanged", _beta_pid() == beta_pid and bool(beta_pid), beta_pid)
    beta_cmd = _listener(beta_pid) if beta_pid else ""
    check("beta command is serve_beta.py", "serve_beta.py" in beta_cmd, beta_cmd[:120])


def main() -> int:
    digest = _ledger_digest()
    beta_pid = _beta_pid()
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        before = _live(conn)
    finally:
        conn.close()
    print(f"NOTE  beta_pid={beta_pid or 'absent'} prod_pid={PROD_PID}")
    print(
        "NOTE  live_evidence_records="
        f"{before['records']} live_requirements={before['requirements']} "
        f"active={before['active']}"
    )
    test_list()
    test_live(before, digest, beta_pid)
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
