#!/usr/bin/env python3
"""CAP-CRM-01 stored-lead read. Counts leads already stored. Writes nothing."""
from __future__ import annotations

import inspect
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)
os.environ.pop("WOLF_CANONICAL_WRITE_OVERRIDE", None)

from core import crm_lead_cap_prove as prove  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
EVIDENCE_ID = "EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153"
CR_ID = "CR-ff42f3a7c49caa79"
GAP = "CAP-bound tests/red-team"
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
    "owner_assignment_id",
    "assignment_id",
    "source_observed_at",
    "first_human_touch_at",
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


def _ledger_counts() -> tuple[int, int, int, str | None, int, int, int]:
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
        assignments = int(conn.execute("SELECT COUNT(*) FROM org_assignments").fetchone()[0])
        leads = int(conn.execute("SELECT COUNT(*) FROM core_leads").fetchone()[0])
    finally:
        conn.close()
    return (
        evidence,
        exceptions,
        approvals,
        None if status is None else str(status[0]),
        persons,
        assignments,
        leads,
    )


def _bound(rows: list[dict]) -> dict[str, int]:
    owned = aged = followed = 0
    for row in rows:
        owned += int(row["owner_set"])
        aged += int(row["aged"])
        followed += int(row["followed"])
    count = len(rows)
    return {
        "rows": count,
        "owned": owned,
        "unowned": count - owned,
        "aged": aged,
        "not_aged": count - aged,
        "followed": followed,
        "not_followed": count - followed,
    }


def _oracle() -> dict:
    conn = _ro(CATALOG)
    try:
        rows = conn.execute(
            """
            SELECT
              CASE
                WHEN entity_id IS NOT NULL AND length(trim(entity_id)) > 0
                THEN entity_id ELSE ''
              END,
              CASE
                WHEN brand_id IS NOT NULL AND length(trim(brand_id)) > 0
                THEN brand_id ELSE ''
              END,
              source_system,
              CASE
                WHEN owner_person_id IS NOT NULL AND length(trim(owner_person_id)) > 0
                THEN 1 ELSE 0
              END,
              CASE
                WHEN owner_assignment_id IS NOT NULL AND length(trim(owner_assignment_id)) > 0
                THEN 1 ELSE 0
              END,
              CASE
                WHEN source_observed_at IS NOT NULL AND length(trim(source_observed_at)) > 0
                THEN 1 ELSE 0
              END,
              CASE
                WHEN first_human_touch_at IS NOT NULL AND length(trim(first_human_touch_at)) > 0
                THEN 1 ELSE 0
              END,
              wolf_stage,
              conversion_status,
              CASE
                WHEN provenance_json LIKE '%"demo": true%'
                  OR provenance_json LIKE '%"demo":true%'
                THEN 1 ELSE 0
              END
            FROM core_leads
            """
        ).fetchall()
        columns = [str(col[1]) for col in conn.execute("PRAGMA table_info(core_leads)").fetchall()]
        persons = int(conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0])
        assignments = int(conn.execute("SELECT COUNT(*) FROM org_assignments").fetchone()[0])
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
        assignment_matches = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM core_leads AS lead
                WHERE lead.owner_assignment_id IS NOT NULL
                  AND length(trim(lead.owner_assignment_id)) > 0
                  AND EXISTS (
                    SELECT 1 FROM org_assignments AS assignment
                    WHERE assignment.assignment_id = lead.owner_assignment_id
                  )
                """
            ).fetchone()[0]
        )
        cr = conn.execute(
            "SELECT state, next_action FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
    finally:
        conn.close()
    parsed = []
    for row in rows:
        parsed.append(
            {
                "entity_id": row[0] or "",
                "brand_id": row[1] or "",
                "source_system": row[2] or "",
                "owner_set": bool(row[3]),
                "assignment_set": bool(row[4]),
                "aged": bool(row[5]),
                "followed": bool(row[6]),
                "wolf_stage": row[7] or "",
                "conversion_status": row[8] or "",
                "demo": bool(row[9]),
            }
        )
    demo = [row for row in parsed if row["demo"]]
    operational = [row for row in parsed if not row["demo"]]
    habitat = [row for row in parsed if row["brand_id"] == "habitat"]
    brands: dict[str, dict[str, int]] = {}
    entities: dict[str, dict[str, int]] = {}
    sources: dict[str, int] = {}
    for row in parsed:
        brand = brands.setdefault(row["brand_id"], {"rows": 0, "demo": 0, "operational": 0})
        entity = entities.setdefault(row["entity_id"], {"rows": 0, "demo": 0, "operational": 0})
        brand["rows"] += 1
        entity["rows"] += 1
        sources[row["source_system"]] = sources.get(row["source_system"], 0) + 1
        if row["demo"]:
            brand["demo"] += 1
            entity["demo"] += 1
        else:
            brand["operational"] += 1
            entity["operational"] += 1
    return {
        "rows": len(parsed),
        "demo": len(demo),
        "operational": len(operational),
        "stored_bound": _bound(parsed),
        "operational_bound": _bound(operational),
        "habitat_bound": _bound(habitat),
        "operational_habitat_bound": _bound([row for row in habitat if not row["demo"]]),
        "brands": [{"brand_id": key, **brands[key]} for key in sorted(brands)],
        "entities": [{"entity_id": key, **entities[key]} for key in sorted(entities)],
        "sources": [{"source_system": key, "rows": sources[key]} for key in sorted(sources)],
        "other_brand": sum(1 for row in parsed if row["brand_id"] != "habitat"),
        "atrium": sum(1 for row in parsed if row["brand_id"] == "atrium"),
        "missing_entity": sum(1 for row in parsed if not row["entity_id"]),
        "missing_brand": sum(1 for row in parsed if not row["brand_id"]),
        "closed": sum(1 for row in parsed if str(row["wolf_stage"]).strip().upper() == "CLOSED"),
        "claimed": sum(
            1 for row in parsed if str(row["conversion_status"]).strip().upper() == "CLAIMED"
        ),
        "verified": sum(
            1 for row in parsed if str(row["conversion_status"]).strip().upper() == "VERIFIED"
        ),
        "owner_set": sum(1 for row in parsed if row["owner_set"]),
        "assignment_set": sum(1 for row in parsed if row["assignment_set"]),
        "person_without_assignment": sum(
            1 for row in parsed if row["owner_set"] and not row["assignment_set"]
        ),
        "assignment_without_person": sum(
            1 for row in parsed if row["assignment_set"] and not row["owner_set"]
        ),
        "persons": persons,
        "assignments": assignments,
        "owner_matches": owner_matches,
        "assignment_matches": assignment_matches,
        "lane_column": "data_lane" in columns,
        "email_column": any("email" in name.lower() for name in columns),
        "cr": None if cr is None else (cr[0], cr[1]),
        "habitat_rows": habitat,
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


def _block_matches(block: dict, expect: dict) -> bool:
    return (
        block.get("status") == "READ"
        and block.get("rows") == expect["rows"]
        and block.get("owned") == expect["owned"]
        and block.get("unowned") == expect["unowned"]
        and block.get("aged") == expect["aged"]
        and block.get("not_aged") == expect["not_aged"]
        and block.get("followed") == expect["followed"]
        and block.get("not_followed") == expect["not_followed"]
        and block.get("empty") is (expect["rows"] == 0)
        and block.get("operating_board") is False
        and block.get("age_threshold_days") is None
        and block.get("follow_policy") is None
        and block.get("aged_definition") == "source_observed_at present"
        and block.get("followed_definition") == "first_human_touch_at present"
        and block.get("owned", 0) + block.get("unowned", 0) == expect["rows"]
    )


def main() -> int:
    before = _ledger_counts()
    ledger_before = LEDGER.read_bytes()
    oracle = _oracle()
    report = prove.read_stored_crm()
    again = prove.read_stored_crm()
    check("two reads match", report == again)
    check("read ok", report.get("ok") is True and report.get("cap") == "CAP-CRM-01")
    check("read is stored crm", report.get("read") == "stored_crm")
    check(
        "lane column absent or named",
        report.get("lane_column") is oracle["lane_column"]
        and (
            (oracle["lane_column"] is False and report.get("data_lane") == "UNKNOWN")
            or oracle["lane_column"] is True
        ),
    )
    check("email column flag", report.get("email_column") is oracle["email_column"])
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
    check(
        "stored bound matches",
        _block_matches(report.get("stored_bound") or {}, oracle["stored_bound"]),
        str(report.get("stored_bound")),
    )
    check(
        "operational bound matches",
        _block_matches(report.get("operational_bound") or {}, oracle["operational_bound"]),
        str(report.get("operational_bound")),
    )
    check(
        "habitat bound matches",
        _block_matches(report.get("habitat_bound") or {}, oracle["habitat_bound"]),
        str(report.get("habitat_bound")),
    )
    check(
        "operational habitat bound matches",
        _block_matches(
            report.get("operational_habitat_bound") or {},
            oracle["operational_habitat_bound"],
        ),
        str(report.get("operational_habitat_bound")),
    )
    if oracle["demo"] == oracle["rows"]:
        check(
            "fixtures are not an operating board",
            report.get("operating_board") is False
            and (report.get("operational_bound") or {}).get("empty") is True
            and report.get("operational_rows") == 0
            and "demo fixture" in str(report.get("why")),
        )
    else:
        check("mixed store is still not a board", report.get("operating_board") is False)
    if oracle["missing_entity"] == 0 and oracle["missing_brand"] == 0:
        check(
            "client boundary held",
            report.get("boundary") == "HELD"
            and report.get("rows_missing_entity") == 0
            and report.get("rows_missing_brand") == 0,
        )
    else:
        check(
            "client boundary breached",
            report.get("boundary") == "BREACHED"
            and report.get("rows_missing_entity") == oracle["missing_entity"]
            and report.get("rows_missing_brand") == oracle["missing_brand"],
        )
    classified = prove.classify_bound(
        [
            {
                "entity_id": "present" if row["entity_id"] else "",
                "brand_id": "habitat",
                "owner_person_id": "set" if row["owner_set"] else "",
                "source_observed_at": "set" if row["aged"] else "",
                "first_human_touch_at": "set" if row["followed"] else "",
                "wolf_stage": row["wolf_stage"],
                "conversion_status": row["conversion_status"],
                "demo": row["demo"],
            }
            for row in oracle["habitat_rows"]
            if row["entity_id"]
        ],
        brand_id="habitat",
    )
    habitat = report.get("habitat_bound") or {}
    if oracle["missing_entity"] == 0 and oracle["habitat_bound"]["rows"] == classified["rows"]:
        check(
            "classifier agrees on habitat",
            classified["boundary"] == "HELD"
            and classified["owned"] == habitat.get("owned")
            and classified["aged"] == habitat.get("aged")
            and classified["followed"] == habitat.get("followed")
            and classified["operating_board"] is False
            and classified["sales"] is None,
        )
    else:
        check("classifier not forced over a breach", habitat.get("operating_board") is False)
    try:
        prove.classify_bound(
            [{"entity_id": "present", "brand_id": "atrium", "demo": True}],
            brand_id="habitat",
        )
        check("cross brand refused", False, "no raise")
    except prove.ProveError as exc:
        check("cross brand refused", exc.code == "boundary_breach", exc.code)
    check(
        "no invented control figures",
        report.get("sales") is None
        and report.get("closed_is_not_a_sale") is True
        and report.get("closed_rows") == oracle["closed"]
        and report.get("claimed_conversion") == oracle["claimed"]
        and report.get("verified_conversion") == oracle["verified"]
        and report.get("leads_created") == 0
        and report.get("persons_created") == 0
        and report.get("assignments_created") == 0
        and report.get("proved") is False
        and report.get("current") is False,
    )
    check(
        "owner is not an assignment",
        report.get("owner_person_set_rows") == oracle["owner_set"]
        and report.get("owner_assignment_set_rows") == oracle["assignment_set"]
        and report.get("person_without_assignment_rows") == oracle["person_without_assignment"]
        and report.get("assignment_without_person_rows") == oracle["assignment_without_person"]
        and report.get("owner_matches_stored_person") == oracle["owner_matches"]
        and report.get("assignment_matches_stored") == oracle["assignment_matches"]
        and report.get("person_id_listed") is False
        and report.get("assignment_id_listed") is False
        and report.get("identity_fields_selected") is False
        and report.get("persons_stored") == oracle["persons"]
        and report.get("assignments_stored") == oracle["assignments"],
    )
    check("brands match", report.get("brands") == oracle["brands"])
    check("entities match", report.get("entities") == oracle["entities"])
    check("sources match", report.get("source_systems") == oracle["sources"])
    check("other brands", report.get("other_brand_rows") == oracle["other_brand"])
    atrium = report.get("atrium") or {}
    if oracle["atrium"] == 0:
        check("atrium absent not zero", atrium.get("status") == "ABSENT" and atrium.get("rows") is None)
    else:
        check("atrium counted", atrium.get("status") == "PRESENT" and atrium.get("rows") == oracle["atrium"])
    check(
        "no external write",
        report.get("catalog_write") is False
        and report.get("ledger_write") is False
        and report.get("klaviyo_called") is False
        and report.get("klaviyo_write") is False
        and report.get("metricool_write") is False
        and report.get("external_crm_write") is False
        and report.get("payment_executed") is False
        and report.get("esb_write") is False
        and report.get("cr_resolved") is False,
    )
    check(
        "speed-to-lead stays the other row",
        report.get("ggv_cap") == "CAP-GGV-04" and report.get("ggv_tested_here") is False
        and report.get("speed_tested_here") is False,
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
        flags.get("maturity") == "BUILT"
        and flags.get("proven") is False
        and flags.get("ledger_rows") == 77
        and flags.get("cap_crm_02_not_this_prove") is True,
    )
    check(
        "cr stays open",
        flags.get("cr_id") == CR_ID
        and flags.get("cr_state") == "OPEN"
        and flags.get("cr_resolved") is False
        and flags.get("cr_next_action") == GAP
        and oracle["cr"] == ("OPEN", GAP),
    )
    check("identity fields stay out", _forbidden(report) == "", _forbidden(report))
    dumped = json.dumps(report)
    check("no email text", "@" not in dumped)
    reader = inspect.getsource(prove.read_stored_crm)
    check("reader has no store statement", "INSERT INTO" not in reader and "UPDATE " not in reader)
    check("reader opens read-only", "mode=ro" in inspect.getsource(prove._ro))
    check("reader does not select lead id", "lead_id" not in reader)
    refused = False
    try:
        prove.read_stored_crm("/tmp/wolf-system/not-a-catalog.sqlite")
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
    check("assignments unchanged", after[5] == before[5] == oracle["assignments"], str(after[5]))
    check("leads unchanged", after[6] == before[6] == oracle["rows"], str(after[6]))
    check("ledger file unchanged", LEDGER.read_bytes() == ledger_before)
    stored_bound = report.get("stored_bound") or {}
    print(
        "COUNTS stored={stored} demo={demo} operational={operational} "
        "owned={owned} unowned={unowned} aged={aged} followed={followed} "
        "persons={persons} assignments={assignments} boundary={boundary}".format(
            stored=report.get("stored_rows"),
            demo=report.get("demo_rows"),
            operational=report.get("operational_rows"),
            owned=stored_bound.get("owned"),
            unowned=stored_bound.get("unowned"),
            aged=stored_bound.get("aged"),
            followed=stored_bound.get("followed"),
            persons=report.get("persons_stored"),
            assignments=report.get("assignments_stored"),
            boundary=report.get("boundary"),
        )
    )
    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAILED")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
