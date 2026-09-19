#!/usr/bin/env python3
"""Completion register + Progress Open Loops (Beta). Temp DB only.

Proves schema, dedup, summary counts, resolve-requires-evidence,
fixture seed does not invent NEEDS_MATT, and the progress payload
carries open_loops. Does not write the live catalog.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALLOW_LIVE_COMPLETION_REGISTER", None)

from core import completion_register as cr  # noqa: E402
from core import progress_read_model as prm  # noqa: E402

PASS = 0
FAIL = 0
HTML = ROOT / "dashboards" / "progress.html"
SUMMARY_KEYS = cr.SUMMARY_KEYS


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM wolf_completion_items").fetchone()[0])


def test_schema_upsert_dedup(conn: sqlite3.Connection) -> None:
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    check("schema wolf_completion_items", "wolf_completion_items" in tables)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(wolf_completion_items)")}
    for col in (
        "id",
        "dedup_key",
        "capability",
        "entity",
        "state",
        "blocker_class",
        "resolution_evidence",
        "resolved_at",
        "first_seen",
        "last_checked",
    ):
        check(f"column {col}", col in cols)
    row = cr.upsert(
        conn,
        capability="CAP-TEST-01",
        item_type="CAPABILITY_DEBT",
        title="CAP-TEST-01 is ABSENT",
        entity="SHARED",
        state="OPEN",
        blocker_class="NEEDS_ENGINEERING",
        evidence="fixture",
        source="fixture",
    )
    check("upsert returns id", str(row["id"]).startswith("CR-"))
    first_seen = row["first_seen"]
    conn.execute(
        "UPDATE wolf_completion_items SET state='IN_PROGRESS', last_checked='2000-01-01T00:00:00+08:00' WHERE id=?",
        (row["id"],),
    )
    conn.commit()
    again = cr.upsert(
        conn,
        capability="CAP-TEST-01",
        item_type="CAPABILITY_DEBT",
        title="CAP-TEST-01 is ABSENT",
        entity="SHARED",
        state="OPEN",
        blocker_class="NEEDS_MATT",
        evidence="fixture-refresh",
        source="fixture",
    )
    check("dedup keeps one row", _count(conn) == 1)
    check("dedup keeps id", again["id"] == row["id"])
    check("dedup does not wipe state", again["state"] == "IN_PROGRESS")
    check("dedup does not reopen or reclass via upsert", again["blocker_class"] == "NEEDS_ENGINEERING")
    check("dedup refreshes last_checked", again["last_checked"] != "2000-01-01T00:00:00+08:00")
    check("dedup keeps first_seen", again["first_seen"] == first_seen)


def test_summary_and_resolve(conn: sqlite3.Connection) -> None:
    matt = cr.upsert(
        conn,
        item_type="EXPLICIT",
        title="Owner-only gate documented as NEEDS_MATT",
        entity="OWNER",
        state="OPEN",
        blocker_class="NEEDS_MATT",
        source="test",
    )
    cr.upsert(
        conn,
        item_type="EXPLICIT",
        title="Policy gap",
        entity="BZG",
        state="BLOCKED",
        blocker_class="NEEDS_POLICY",
        source="test",
    )
    cr.upsert(
        conn,
        item_type="EXPLICIT",
        title="Staff closer",
        entity="BZG",
        state="OPEN",
        blocker_class="NEEDS_STAFF",
        source="test",
    )
    summary = cr.summary_for_owner(conn)
    for key in SUMMARY_KEYS:
        check(f"summary has {key}", key in summary)
    check("needs_matt counts NEEDS_MATT only", summary["needs_matt"] == 1, str(summary["needs_matt"]))
    check("needs_policy counted", summary["needs_policy"] == 1, str(summary["needs_policy"]))
    check("needs_staff counted", summary["needs_staff"] == 1)
    check("blocked counted", summary["blocked"] == 1)
    check(
        "engineering not in oldest material",
        all(item.get("blocker_class") != "NEEDS_ENGINEERING" for item in summary["oldest_material"]),
    )
    try:
        cr.mark_resolved(conn, matt["id"], "")
        check("empty evidence refused", False)
    except cr.CompletionRegisterError as exc:
        check("empty evidence refused", exc.code == "evidence_required")
    try:
        cr.mark_resolved(conn, matt["id"], "READY")
        check("maturity alone refused", False)
    except cr.CompletionRegisterError as exc:
        check("maturity alone refused", exc.code == "maturity_not_proof")
    still = cr.list_open(conn, blocker_class="NEEDS_MATT")
    check("unproven item stays open", len(still) == 1)
    resolved = cr.mark_resolved(
        conn,
        matt["id"],
        "docs/deliveries/GROK-PLAN-COMPLETION-REGISTER-2026-09-19.md",
    )
    check("resolved with evidence", resolved["state"] == "RESOLVED")
    check("resolution_evidence stored", "GROK-PLAN-COMPLETION-REGISTER" in (resolved["resolution_evidence"] or ""))
    check("resolved_at set", bool(resolved["resolved_at"]))
    check("resolved left list_open", cr.list_open(conn, blocker_class="NEEDS_MATT") == [])
    after = cr.summary_for_owner(conn)
    check("resolved NEEDS_MATT no longer counted", after["needs_matt"] == 0)
    check("recently resolved includes the item", any(r["id"] == matt["id"] for r in after["recently_resolved"]))
    try:
        cr.mark_resolved(conn, matt["id"], "docs/deliveries/GROK-PLAN-COMPLETION-REGISTER-2026-09-19.md")
        check("second resolve refused", False)
    except cr.CompletionRegisterError as exc:
        check("second resolve refused", exc.code == "already_resolved")


def test_fixture_seed_does_not_invent_matt(conn: sqlite3.Connection) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ledger = root / "ledger.json"
        ledger.write_text(
            json.dumps(
                {
                    "CAP-FIX-01": [
                        "ABSENT",
                        "fixture evidence",
                        "waiting bar",
                        "UNKNOWN",
                        "HIGH",
                        "Matt might want this later",
                    ],
                    "CAP-FIX-02": ["READY", "done", "none", "HEALTHY", "HIGH", ""],
                    "CAP-FIX-03": ["BUILT", "partial", "prove next", "UNKNOWN", "MED", ""],
                    "CAP-FIX-04": ["PROVEN", "proven", "ready bar", "UNKNOWN", "HIGH", ""],
                }
            ),
            encoding="utf-8",
        )
        aus = root / "aus.json"
        aus.write_text(
            json.dumps(
                [
                    {
                        "au_id": "AU-FIX-1",
                        "cap": "CAP-BZG-03",
                        "name": "Venue Daily Close",
                        "domain": "D-BZG",
                        "scope": "Uma Blu (BZG-UMA)",
                        "appl": "REQUIRED",
                        "state": "NOT STARTED",
                        "missing": "Verified closing operator",
                        "evidence": "no named closer",
                        "founder": "Do not use Matt as closer",
                    },
                    {
                        "au_id": "AU-FIX-2",
                        "cap": "CAP-CORE-02",
                        "name": "Seats",
                        "domain": "D-CORE",
                        "scope": "Wolf seats",
                        "appl": "REQUIRED",
                        "state": "ADOPTED",
                        "founder": "Owner auth is intentional",
                    },
                    {
                        "au_id": "AU-FIX-3",
                        "cap": "CAP-BZG-03",
                        "name": "Venue Daily Close",
                        "domain": "D-BZG",
                        "scope": "BZG Rainforest",
                        "appl": "PLANNED",
                        "state": "NOT STARTED",
                    },
                ]
            ),
            encoding="utf-8",
        )
        claims = root / "claims"
        claims.mkdir()
        (claims / "uma.json").write_text(
            json.dumps(
                {
                    "system": "uma-blu-today",
                    "remaining_blockers": [
                        {
                            "id": "opening_float",
                            "status": "NOT_FOUND",
                            "classification": "NEEDS_POLICY",
                            "why": "No authorised opening-float source was found.",
                        },
                        {
                            "id": "closer",
                            "status": "WAITING FOR VERIFIED CLOSING OPERATOR",
                            "classification": "NEEDS_STAFF",
                            "why": "A named closer has not been assigned.",
                        },
                    ],
                    "cutover_at": None,
                    "HUMAN_COMMISSIONING_STATUS": "READY_FOR_DEVI_PHONE_TEST",
                    "PERSON": "PERS-DEVI",
                    "NOTES": "Waiting Devi phone. Do not mark HUMAN COMMISSIONED from send alone.",
                }
            ),
            encoding="utf-8",
        )
        review = root / "ended.md"
        review.write_text(
            "upsert_asg_scope re-ACTIVATEs ENDED SCOPE-BZG-ENTITY. Follow-up lane.\n",
            encoding="utf-8",
        )
        counts = cr.seed_authorised_evidence(
            conn,
            ledger_path=ledger,
            catalog_path=ROOT / "docs" / "MODEL-C-CAPABILITY-CATALOG.md",
            model_e_path=aus,
            claims_dir=claims,
            cutover_path=root / "missing-cutover.json",
            ended_scope_review=review,
            review_dir=root / "no-reviews",
            use_live_defaults=False,
        )
        check("fixture seeded debt", counts["capability_debt"] == 2, str(counts))
        check("fixture seeded adoption not adopted/planned", counts["adoption"] == 1)
        rows = cr.list_open(conn)
        classes = {r["blocker_class"] for r in rows}
        check("fixture has no NEEDS_MATT", "NEEDS_MATT" not in classes, str(classes))
        by_cap = {r["capability"]: r for r in rows if r["capability"]}
        check("READY not seeded", "CAP-FIX-02" not in by_cap)
        check("PROVEN not seeded", "CAP-FIX-04" not in by_cap)
        check("ABSENT is engineering", by_cap["CAP-FIX-01"]["blocker_class"] == "NEEDS_ENGINEERING")
        check("BUILT is engineering", by_cap["CAP-FIX-03"]["blocker_class"] == "NEEDS_ENGINEERING")
        adoption = [r for r in rows if r["item_type"] == "ADOPTION"]
        check("adoption row present", len(adoption) == 1)
        check("adoption is NEEDS_ADOPTION", adoption[0]["blocker_class"] == "NEEDS_ADOPTION")
        check("founder text did not become NEEDS_MATT", adoption[0]["blocker_class"] != "NEEDS_MATT")
        summary = cr.summary_for_owner(conn)
        check("fixture summary needs_matt is 0", summary["needs_matt"] == 0)
        check("fixture needs_policy from float/cutover", summary["needs_policy"] >= 1)
        check("fixture needs_staff from closer", summary["needs_staff"] >= 1)
        check(
            "fixture commissioning debt",
            summary["commissioning_adoption_debt"] >= 1,
            str(summary["commissioning_adoption_debt"]),
        )
        before = _count(conn)
        cr.seed_authorised_evidence(
            conn,
            ledger_path=ledger,
            model_e_path=aus,
            claims_dir=claims,
            ended_scope_review=review,
            use_live_defaults=False,
        )
        check("re-seed does not duplicate", _count(conn) == before)


def test_live_evidence_temp_db(conn: sqlite3.Connection) -> None:
    counts = cr.seed_authorised_evidence(conn, use_live_defaults=True)
    summary = cr.summary_for_owner(conn)
    check("live harvest non-empty", summary["total_unresolved"] > 0, str(summary["total_unresolved"]))
    check("live harvest needs_matt is 0", summary["needs_matt"] == 0, str(summary["needs_matt"]))
    check("live harvest includes capability debt", counts["capability_debt"] > 0, str(counts))
    check("ended-scope defect seeded", counts["defects"] == 1, str(counts))
    check(
        "oldest material is not an engineering dump",
        len(summary["oldest_material"]) <= cr.OLDEST_LIMIT
        and all(i.get("blocker_class") != "NEEDS_ENGINEERING" for i in summary["oldest_material"]),
    )
    ggv = cr.summary_for_owner(conn, view_key="GGV")
    check("GGV drill is a subset", ggv["total_unresolved"] <= summary["total_unresolved"])
    check("GGV drill needs_matt is 0", ggv["needs_matt"] == 0)
    for key in SUMMARY_KEYS:
        check(f"GGV summary has {key}", key in ggv)


def test_progress_payload(conn: sqlite3.Connection) -> None:
    db_path = Path(conn.execute("PRAGMA database_list").fetchone()[2])
    model = prm.build_read_model(register_db_path=db_path)
    check("payload ok", model.get("ok") is True)
    loops = model.get("open_loops") or {}
    for key in SUMMARY_KEYS:
        check(f"payload open_loops.{key}", key in loops)
    check("payload needs_matt is int", isinstance(loops.get("needs_matt"), int))
    empire = ((model.get("views") or {}).get("Empire") or {}).get("open_loops") or {}
    check("empire view has open_loops", "needs_matt" in empire)
    check("empire needs_matt matches payload", empire.get("needs_matt") == loops.get("needs_matt"))
    for view in ("GGV", "AMG", "BZG", "Wolf Core", "Intelligence", "Integrations", "Sale Readiness", "Build Factory"):
        block = ((model.get("views") or {}).get(view) or {}).get("open_loops") or {}
        check(f"{view} open_loops keys", all(k in block for k in SUMMARY_KEYS))
    html = HTML.read_text(encoding="utf-8")
    check("HTML Open Loops marker", "Open Loops" in html and 'data-section="open-loops"' in html)
    check("HTML counts from payload", 'loopCount(ol, "needs_matt")' in html)
    check("HTML does not hard-code Needs Matt number", "Needs Matt <strong>0" not in html)
    try:
        with urlopen("http://127.0.0.1:8788/progress", timeout=4) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            code = getattr(resp, "status", 200)
        check("GET /progress 200", code == 200, str(code))
        check("GET /progress contains Open Loops", "Open Loops" in body)
    except (URLError, TimeoutError, OSError) as exc:
        check("GET /progress 200", False, str(exc))
        check("GET /progress contains Open Loops", False, str(exc))


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        schema_db = base / "schema.sqlite"
        conn = cr.db_connect(schema_db)
        try:
            test_schema_upsert_dedup(conn)
            test_summary_and_resolve(conn)
        finally:
            conn.close()

        fixture_db = base / "fixture.sqlite"
        conn = cr.db_connect(fixture_db)
        try:
            test_fixture_seed_does_not_invent_matt(conn)
        finally:
            conn.close()

        live_db = base / "live-harvest.sqlite"
        conn = cr.db_connect(live_db)
        try:
            test_live_evidence_temp_db(conn)
            test_progress_payload(conn)
        finally:
            conn.close()

    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
