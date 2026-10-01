#!/usr/bin/env python3
"""Pack 10 — read the approval gate. Do not invent a limit or a live approval."""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import amg_finance_screens as fin  # noqa: E402
from core import approvals_evidence_pack10 as gate  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}  {detail}")


def _request_count() -> int:
    conn = sqlite3.connect(f"file:{gate.CATALOG_DB}?mode=ro", uri=True)
    try:
        return int(conn.execute("SELECT COUNT(*) FROM core_approval_requests").fetchone()[0])
    finally:
        conn.close()


def main() -> int:
    catalog_mtime = gate.CATALOG_DB.stat().st_mtime_ns
    books_mtime = fin.BOOKS.stat().st_mtime_ns
    before = _request_count()
    data = gate.load_gate()
    check("staff not ready", data.get("staff_ready") is False and data.get("human_proven") is False and data.get("writes") is False)
    check("no fake approval", data.get("fake_approval") is False and data.get("authority_limit_invented") is False)
    limits = data["authority_limits"]
    check(
        "limits stay zero",
        limits.get("count") == 0 and limits.get("active_threshold") is None and limits.get("state") == "FAIL_CLOSED",
        str(limits),
    )
    amount = data["amount_gate"]
    check(
        "amount has no limit",
        amount.get("allowed") is False
        and amount.get("reason") == "higher_approval_required"
        and amount.get("detail") == "no_matching_authority_limit"
        and amount.get("matched_limit") is None
        and amount.get("threshold_invented") is False
        and amount.get("probe_source") == "PETTY-UMA-2321496C6D",
        str(amount),
    )
    request = data["live_request"]
    check(
        "one live uma request",
        request.get("present") is True
        and request.get("approval_request_id") == gate.LIVE_REQUEST
        and request.get("request_type") == "GENERAL"
        and request.get("requested_by_person_id") == "PERS-DEVI"
        and request.get("decided_by_person_id") == "PERS-MATT"
        and request.get("self_approved") is False
        and request.get("material_amount") is None
        and request.get("status") == "APPROVED"
        and data["counts"]["core_approval_requests"] == 1,
        str(request),
    )
    orphans = data["orphan_decisions"]
    check(
        "orphan decisions are not authority",
        orphans.get("count") == 9 and orphans.get("treated_as_authority") is False and orphans.get("people_in_org_persons") == [],
        str(orphans),
    )
    check("delegations stay zero", data.get("delegations") == 0)
    seats = {row["person_id"]: row for row in data["who_can_decide"]}
    check("matt can decide bzg", any(item["entity_id"] == "ENT-BZG" for item in seats["PERS-MATT"]["allowed"]))
    check(
        "devi cannot decide bzg",
        any(item["entity_id"] == "ENT-BZG" and item["reason"] == "role_lacks_permission" for item in seats["PERS-DEVI"]["denied"]),
    )
    check(
        "amanda ggv yes amg no",
        any(item["entity_id"] == "ENT-GGV" for item in seats["PERS-AMANDA"]["allowed"])
        and any(item["entity_id"] == "ENT-AMG" for item in seats["PERS-AMANDA"]["denied"]),
    )
    check(
        "zayen cannot decide amg",
        any(item["entity_id"] == "ENT-AMG" and item["reason"] == "role_lacks_permission" for item in seats["PERS-ZAYEN"]["denied"]),
    )
    evidence = data["evidence"]
    check(
        "receipt evidence attached",
        (evidence.get("receipt") or {}).get("evidence_id") == gate.RECEIPT_EVIDENCE
        and (evidence.get("petty_photo") or {}).get("evidence_id") == gate.PETTY_EVIDENCE,
    )
    check(
        "declared cash fail closed",
        evidence.get("declared_cash_attached") is False
        and evidence.get("declared_cash_state") == "FAIL_CLOSED"
        and all(row.get("declared_cash_evidence_id") is None for row in evidence.get("declared_cash_closes") or []),
        str(evidence.get("declared_cash_closes")),
    )
    publish = evidence["publish_gate"]
    check(
        "publish evidence fail closed",
        publish.get("allowed") is False
        and publish.get("reason_code") == "missing_required_evidence"
        and publish.get("publish_executed") is False,
        str(publish),
    )
    sod = data["finance_sod"]
    check(
        "books sod stays segregated",
        sod.get("segregated") is True
        and sod.get("preparer_person_id") == fin.PRODUCER
        and sod.get("self_journal_approved_by") is None
        and sod.get("xero_write") is False,
        str(sod),
    )
    seats_fin = sod["seats"]
    check("zayen ggv seat denied", seats_fin["PERS-ZAYEN"].get("ENT-GGV") is False)
    check("amanda amg seat denied", seats_fin["PERS-AMANDA"].get("ENT-AMG") is False)
    residual = data["human_residual"]
    check("staff must still click", residual.get("state") == "NOT_HUMAN_PROVEN" and residual.get("staff_must_click") is True)

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "reviews.sqlite"
        blocked = fin.submit_review(fin.APPROVER, "close", db, entity_id="ENT-GGV")
        check("cross entity deny", blocked.get("error") == "entity_denied")
        opened = fin.submit_review(fin.PRODUCER, "close", db)
        self_deny = fin.approve_review(fin.PRODUCER, opened["id"], db)
        check("self approve denied", self_deny.get("error") == "self_approval_denied" and self_deny.get("xero_write") is False)
        saved = sqlite3.connect(db)
        try:
            status = saved.execute("SELECT status, approver_id FROM screen_reviews").fetchone()
        finally:
            saved.close()
        check("temp review stays pending", status is not None and status[0] == "PENDING" and status[1] is None, str(status))

    page = (ROOT / "dashboards" / "approvals-evidence.html").read_text(encoding="utf-8")
    check("page title", "<title>Approvals and evidence</title>" in page)
    check("tiles start closed", page.count("<details>") >= 4 and "<details open" not in page)
    check("page says limits are zero", "Authority limits are 0" in page)
    refused = gate.refuse_write()
    check("refuse write", refused.get("error") == "writes_off" and refused.get("authority_limit_invented") is False)
    check("catalog unread", gate.CATALOG_DB.stat().st_mtime_ns == catalog_mtime and fin.BOOKS.stat().st_mtime_ns == books_mtime)
    check("no new live request", _request_count() == before == 1)
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
