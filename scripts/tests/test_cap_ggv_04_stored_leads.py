#!/usr/bin/env python3
"""CAP-GGV-04 stored-lead read. Counts leads already stored. Writes nothing."""
from __future__ import annotations

import inspect
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)
os.environ.pop("WOLF_CANONICAL_WRITE_OVERRIDE", None)

from core import ggv_speed_to_lead_prove as prove  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
EVIDENCE_ID = "EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153"
CR_ID = "CR-f089b11530ab4673"
GAP = "Governed speed-to-lead capability with tests/red-team"
FORBIDDEN_KEYS = {
    "lead_id",
    "source_id",
    "email",
    "provenance_json",
    "label",
    "owner_person_id",
    "person_id",
    "display_name",
    "name",
    "payload_json",
    "note",
}


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


def _parse_ts(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _bucket(observed_raw: str | None, touch_raw: str | None, clock: datetime) -> tuple[str, str]:
    observed = _parse_ts(str(observed_raw or ""))
    touch_text = str(touch_raw or "").strip()
    touch = _parse_ts(touch_text) if touch_text else None
    if touch_text and touch is None:
        receipt = "UNREADABLE"
    elif touch is None:
        receipt = "ABSENT"
    else:
        receipt = "PRESENT"
    if observed is None:
        return "UNAVAILABLE", receipt
    if receipt != "PRESENT":
        if receipt == "ABSENT":
            if (clock - observed).total_seconds() < 0:
                return "UNAVAILABLE", receipt
            return "WAITING", receipt
        return "UNAVAILABLE", receipt
    if touch is None or (touch - observed).total_seconds() < 0:
        return "UNAVAILABLE", receipt
    return "MEASURED", receipt


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
        persons = int(conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0])
        leads = int(conn.execute("SELECT COUNT(*) FROM core_leads").fetchone()[0])
    finally:
        conn.close()
    return evidence, exceptions, approvals, None if status is None else str(status[0]), persons, leads


def _oracle(clock: datetime) -> dict:
    conn = _ro(CATALOG)
    try:
        rows = conn.execute(
            """
            SELECT brand_id, source_system, source_observed_at, first_human_touch_at,
                   wolf_stage, source_stage, conversion_status,
                   CASE
                     WHEN owner_person_id IS NOT NULL AND length(trim(owner_person_id)) > 0
                     THEN 1 ELSE 0
                   END,
                   CASE
                     WHEN current_work_item_id IS NOT NULL
                      AND length(trim(current_work_item_id)) > 0
                     THEN 1 ELSE 0
                   END,
                   CASE
                     WHEN provenance_json LIKE '%"demo": true%'
                       OR provenance_json LIKE '%"demo":true%'
                     THEN 1 ELSE 0
                   END
            FROM core_leads
            """
        ).fetchall()
        lane = conn.execute("PRAGMA table_info(core_leads)").fetchall()
        events = conn.execute(
            "SELECT event_type, COUNT(*) FROM core_lead_events GROUP BY event_type ORDER BY event_type"
        ).fetchall()
        event_leads = int(conn.execute("SELECT COUNT(DISTINCT lead_id) FROM core_lead_events").fetchone()[0])
        persons = int(conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0])
        owner_matches = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM core_leads AS lead
                WHERE lead.owner_person_id IS NOT NULL
                  AND length(trim(lead.owner_person_id)) > 0
                  AND EXISTS (
                    SELECT 1 FROM org_persons AS person
                    WHERE person.person_id = lead.owner_person_id
                  )
                """
            ).fetchone()[0]
        )
        ivy = int(conn.execute("SELECT COUNT(*) FROM core_leads WHERE lower(brand_id)='ivy'").fetchone()[0])
        cr = conn.execute(
            "SELECT state, next_action FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
    finally:
        conn.close()
    speed = {"WAITING": 0, "MEASURED": 0, "UNAVAILABLE": 0}
    operational_speed = {"WAITING": 0, "MEASURED": 0, "UNAVAILABLE": 0}
    receipts = {"PRESENT": 0, "ABSENT": 0, "UNREADABLE": 0}
    operational_receipts = {"PRESENT": 0, "ABSENT": 0, "UNREADABLE": 0}
    demo = 0
    closed = 0
    owner_set = 0
    work_item = 0
    other_brand = 0
    for row in rows:
        brand, source, observed, touch, stage, source_stage, conversion, owner, work, demo_flag = row
        is_demo = bool(demo_flag)
        if is_demo:
            demo += 1
        status, receipt = _bucket(observed, touch, clock)
        speed[status] += 1
        receipts[receipt] += 1
        if not is_demo:
            operational_speed[status] += 1
            operational_receipts[receipt] += 1
        if str(stage or "").upper() == "CLOSED":
            closed += 1
        owner_set += int(owner)
        work_item += int(work)
        if str(brand or "").strip().lower() != "habitat":
            other_brand += 1
    return {
        "rows": len(rows),
        "demo": demo,
        "operational": len(rows) - demo,
        "speed": speed,
        "operational_speed": operational_speed,
        "receipts": receipts,
        "operational_receipts": operational_receipts,
        "closed": closed,
        "owner_set": owner_set,
        "work_item": work_item,
        "other_brand": other_brand,
        "persons": persons,
        "owner_matches": owner_matches,
        "events": [{"event_type": row[0] or "", "rows": int(row[1])} for row in events],
        "event_rows": sum(int(row[1]) for row in events),
        "event_leads": event_leads,
        "ivy": ivy,
        "lane_column": any(col[1] == "data_lane" for col in lane),
        "cr": None if cr is None else (cr[0], cr[1]),
    }


def _forbidden(obj: object, trail: str = "") -> str:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_KEYS:
                return trail + "." + str(key)
            found = _forbidden(value, trail + "." + str(key))
            if found:
                return found
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            found = _forbidden(value, f"{trail}[{index}]")
            if found:
                return found
    return ""


def _speed_block(block: dict, speed: dict, receipts: dict, rows: int) -> bool:
    return (
        block.get("status") == "READ"
        and block.get("rows") == rows
        and block.get("waiting") == speed["WAITING"]
        and block.get("measured") == speed["MEASURED"]
        and block.get("unavailable") == speed["UNAVAILABLE"]
        and block.get("receipt_present") == receipts["PRESENT"]
        and block.get("receipt_absent") == receipts["ABSENT"]
        and block.get("receipt_unreadable") == receipts["UNREADABLE"]
        and block.get("waiting", 0) + block.get("measured", 0) + block.get("unavailable", 0) == rows
    )


def main() -> int:
    before = _ledger_counts()
    ledger_before = LEDGER.read_bytes()
    clock = datetime.now(timezone.utc)
    oracle = _oracle(clock)
    report = prove.read_stored_leads(now=clock)
    again = prove.read_stored_leads(now=clock)
    check("two reads match", report == again)
    check("read ok", report.get("ok") is True and report.get("cap") == "CAP-GGV-04")
    check("read is stored leads", report.get("read") == "stored_leads")
    check(
        "lane column absent",
        report.get("data_lane") == "UNKNOWN" and report.get("lane_column") is False and oracle["lane_column"] is False,
    )
    check(
        "stored count matches",
        report.get("stored_rows") == oracle["rows"] and oracle["rows"] > 0,
        str(report.get("stored_rows")),
    )
    check(
        "demo stays out of operational",
        report.get("demo_rows") == oracle["demo"]
        and report.get("operational_rows") == oracle["operational"]
        and report.get("demo_counted_as_operational") is False
        and report.get("operational_rows") == report.get("stored_rows") - report.get("demo_rows"),
        str(report.get("operational_rows")),
    )
    stored_speed = report.get("stored_speed") or {}
    operational_speed = report.get("operational_speed") or {}
    check(
        "stored speed matches",
        _speed_block(stored_speed, oracle["speed"], oracle["receipts"], oracle["rows"]),
        str(stored_speed),
    )
    check(
        "operational speed matches",
        _speed_block(
            operational_speed,
            oracle["operational_speed"],
            oracle["operational_receipts"],
            oracle["operational"],
        ),
        str(operational_speed),
    )
    if oracle["demo"] == oracle["rows"]:
        check(
            "fixtures are not an operating board",
            report.get("operating_board") is False
            and operational_speed.get("empty") is True
            and report.get("operational_rows") == 0
            and "demo fixture" in str(report.get("why")),
        )
    else:
        check("mixed store is still not a board", report.get("operating_board") is False)
    check(
        "no invented control figures",
        report.get("sla_target_seconds") is None
        and report.get("sla_breached") is None
        and report.get("sales") is None
        and report.get("closed_is_not_a_sale") is True
        and report.get("closed_rows") == oracle["closed"]
        and report.get("receipts_invented") == 0
        and report.get("leads_invented") is False
        and report.get("leads_created") == 0
        and report.get("persons_created") == 0
        and report.get("proved") is False
        and report.get("current") is False,
    )
    check(
        "owner and work counts",
        report.get("owner_set_rows") == oracle["owner_set"]
        and report.get("owner_matches_stored_person") == oracle["owner_matches"]
        and report.get("work_item_set_rows") == oracle["work_item"]
        and report.get("person_id_listed") is False
        and report.get("persons_stored") == oracle["persons"],
    )
    check(
        "events match",
        report.get("events") == oracle["events"]
        and report.get("event_rows") == oracle["event_rows"]
        and report.get("event_leads") == oracle["event_leads"],
    )
    check("other brands", report.get("other_brand_rows") == oracle["other_brand"])
    ivy = report.get("ivy") or {}
    if oracle["ivy"] == 0:
        check("ivy absent not zero", ivy.get("status") == "ABSENT" and ivy.get("rows") is None)
    else:
        check("ivy counted", ivy.get("status") == "PRESENT" and ivy.get("rows") == oracle["ivy"])
    check(
        "no external write",
        report.get("catalog_write") is False
        and report.get("ledger_write") is False
        and report.get("klaviyo_called") is False
        and report.get("klaviyo_write") is False
        and report.get("metricool_write") is False
        and report.get("activecampaign_called") is False
        and report.get("external_crm_write") is False
        and report.get("payment_executed") is False
        and report.get("esb_write") is False
        and report.get("cr_resolved") is False,
    )
    check(
        "crm stays the other row",
        report.get("crm_cap") == "CAP-CRM-01" and report.get("crm_tested_here") is False,
    )
    check(
        "people gates stay unset",
        report.get("staff_ready") is False
        and report.get("human_commissioned") is False
        and report.get("operating_adoption") == "NOT MEASURED",
    )
    flags = report.get("honesty") or {}
    check(
        "ledger stays built",
        flags.get("maturity") == "BUILT" and flags.get("proven") is False and flags.get("ledger_rows") == 77,
    )
    check(
        "cr stays open",
        flags.get("cr_state") == "OPEN"
        and flags.get("cr_resolved") is False
        and flags.get("cr_next_action") == GAP
        and oracle["cr"] == ("OPEN", GAP),
    )
    check("identity fields stay out", _forbidden(report) == "", _forbidden(report))
    dumped = json.dumps(report)
    check("no email text", "@" not in dumped)
    reader = inspect.getsource(prove.read_stored_leads)
    check("reader has no store statement", "INSERT INTO" not in reader and "UPDATE " not in reader)
    check("reader opens read-only", "mode=ro" in inspect.getsource(prove._ro))
    refused = False
    try:
        prove.read_stored_leads("/tmp/wolf-system/not-a-catalog.sqlite")
    except prove.ProveError as exc:
        refused = exc.code == "not_beta"
    check("outside path refused", refused)

    after = _ledger_counts()
    check("evidence count unchanged", after[0] == before[0] == 4, str(after[0]))
    check("exception count unchanged", after[1] == before[1] == 3, str(after[1]))
    check("approval count unchanged", after[2] == before[2] == 9, str(after[2]))
    check(
        "preserved evidence stays invalidated",
        before[3] == "INVALIDATED" and after[3] == "INVALIDATED",
        str(after[3]),
    )
    check("persons unchanged", after[4] == before[4] == oracle["persons"], str(after[4]))
    check("leads unchanged", after[5] == before[5] == oracle["rows"], str(after[5]))
    check("ledger file unchanged", LEDGER.read_bytes() == ledger_before)
    print(
        "COUNTS stored={stored} demo={demo} operational={operational} "
        "waiting={waiting} measured={measured} unavailable={unavailable} "
        "persons={persons}".format(
            stored=report.get("stored_rows"),
            demo=report.get("demo_rows"),
            operational=report.get("operational_rows"),
            waiting=stored_speed.get("waiting"),
            measured=stored_speed.get("measured"),
            unavailable=stored_speed.get("unavailable"),
            persons=report.get("persons_stored"),
        )
    )
    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAILED")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
