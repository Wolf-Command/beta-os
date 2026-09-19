#!/usr/bin/env python3
"""GGV speed-to-lead triage board on Beta Lead Spine.

CAP-GGV-04 stays BUILT. Temp sqlite under catalog/backups/. No live catalog writes.
No invented leads. No invented SLA. No Metricool write.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
MIG_SPINE = SCRIPTS / "migrations" / "migrate_lead_spine.py"
MIG_OP = SCRIPTS / "migrations" / "migrate_lead_spine_operator.py"
PAGE = ROOT / "dashboards" / "lead-spine.html"
SERVE = SCRIPTS / "serve_beta.py"
MODEL_C = ROOT / "state" / "model-c-baseline-assessments.json"
WIP = (
    ROOT / "scripts" / "migrations" / "migrate_phase2_6_team_readiness.py",
    ROOT / "scripts" / "phase26_team.py",
    ROOT / "scripts" / "skills" / "__init__.py",
    ROOT / "scripts" / "wolf_intelligence.py",
)

PASS = 0
FAIL = 0

ENTITY = "ENT-GGV"
BRAND_HAB = "habitat"
BRAND_OTHER = "fixture-selo-speed"
PERS_DEMO = "PERS-LEAD-DEMO"
PERS_DENIED = "PERS-FIXTURE-DENIED-SPEED"
ROLE_DENIED = "ROLE-FIXTURE-DENIED-SPEED"
POS_DENIED = "POS-FIXTURE-DENIED-SPEED"
ASG_DENIED = "ASG-FIXTURE-DENIED-SPEED"
SCOPE_OTHER = "SCOPE-FIXTURE-OTHER-SPEED"
WI = "WI-SPEED-TO-LEAD-TEST"
TS = "2026-09-19T09:00:00+08:00"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_other_brand(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO org_brands (
          brand_id, entity_id, display_name, brand_type, status, created_at, updated_at
        ) VALUES (?, ?, 'Other speed brand', 'fixture', 'ACTIVE', ?, ?)
        ON CONFLICT(brand_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (BRAND_OTHER, ENTITY, TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_persons (
          person_id, display_name, legal_name, status, created_at, updated_at
        ) VALUES (?, 'Denied speed operator', NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (PERS_DENIED, TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_roles (
          role_id, display_name, department_id, role_type, status, created_at, updated_at
        ) VALUES (?, 'Denied Speed Role', NULL, 'fixture', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (ROLE_DENIED, TS, TS),
    )
    for perm_id in (
        "PERM-LEAD-READ",
        "PERM-LEAD-CREATE",
        "PERM-LEAD-EVENT",
        "PERM-LEAD-ASSIGN",
    ):
        conn.execute(
            """
            INSERT INTO org_role_permissions (
              role_id, permission_id, effect, created_at, updated_at
            ) VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET
              effect='ALLOW', updated_at=excluded.updated_at
            """,
            (ROLE_DENIED, perm_id, TS, TS),
        )
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, location_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES (?, ?, ?, NULL, ?, NULL, 'Denied', 'ACTIVE', 1.0, ?, ?)
        ON CONFLICT(position_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (POS_DENIED, ROLE_DENIED, ENTITY, BRAND_OTHER, TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at,
          status, is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET
          status='ACTIVE', end_at=NULL, updated_at=excluded.updated_at
        """,
        (ASG_DENIED, PERS_DENIED, POS_DENIED, TS, TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_scopes (
          scope_id, scope_type, display_name, status, created_at, updated_at
        ) VALUES (?, 'brand', 'Other speed scope', 'ACTIVE', ?, ?)
        ON CONFLICT(scope_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (SCOPE_OTHER, TS, TS),
    )
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES (?, 'brand', ?, ?)
        ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
        """,
        (SCOPE_OTHER, BRAND_OTHER, TS),
    )
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(conn, ASG_DENIED, SCOPE_OTHER, TS, TS)
    conn.commit()


def insert_work_item(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO core_work_items (
          work_item_id, title, description, work_type, status, priority,
          owning_entity_id, source_type, source_id, created_by_actor_type,
          created_by_person_id, owner_person_id, owner_org_assignment_id,
          due_at, started_at, completed_at, verified_at, outcome,
          completion_evidence_reference, parent_work_item_id, created_at, updated_at
        ) VALUES (
          ?, 'Speed test work', NULL, 'FOLLOW_UP', 'OPEN', 3,
          'ENT-GGV', 'SYSTEM', NULL, 'SYSTEM',
          NULL, NULL, NULL,
          NULL, NULL, NULL, NULL, NULL,
          NULL, NULL, ?, ?
        )
        ON CONFLICT(work_item_id) DO NOTHING
        """,
        (WI, TS, TS),
    )
    conn.commit()


def lead_by_source(conn: sqlite3.Connection, source_id: str, brand: str = BRAND_HAB) -> dict | None:
    row = conn.execute(
        """
        SELECT * FROM core_leads
        WHERE brand_id=? AND source_system='fixture' AND source_id=?
        """,
        (brand, source_id),
    ).fetchone()
    return dict(row) if row else None


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    model_before = sha256(MODEL_C)
    wip_before = {str(p): sha256(p) for p in WIP}
    cap = json.loads(MODEL_C.read_text(encoding="utf-8"))["CAP-GGV-04"][0]

    mig_spine = load_mod(MIG_SPINE, "migrate_lead_spine_speed")
    mig_op = load_mod(MIG_OP, "migrate_lead_spine_operator_speed")

    td = ROOT / "catalog" / "backups" / f"tmp-ggv-speed-{os.getpid()}"
    if td.exists():
        shutil.rmtree(td)
    td.mkdir(parents=True, exist_ok=True)
    tmp_db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, tmp_db)

    check("temp spine migrate exit 0", mig_spine.main([str(tmp_db)]) == 0)
    check("temp operator seed exit 0", mig_op.main([str(tmp_db)]) == 0)

    import core.identity as identity
    import core.rbac as rbac
    import core.scope as scope
    import core.lead_spine as ls

    for mod in (identity, rbac, scope, ls):
        if hasattr(mod, "CATALOG_DB"):
            mod.CATALOG_DB = tmp_db

    conn = ls.db_connect(tmp_db)
    seed_other_brand(conn)
    insert_work_item(conn)

    before_rows = conn.execute("SELECT COUNT(*) FROM core_leads").fetchone()[0]
    board = ls.api_triage_board(
        verified_person_id=PERS_DEMO, brand_id=BRAND_HAB, conn=conn
    )
    after_rows = conn.execute("SELECT COUNT(*) FROM core_leads").fetchone()[0]
    check("triage read does not insert a lead", before_rows == after_rows, f"{before_rows}->{after_rows}")
    check("triage ok", board.get("ok") is True)
    check("queue count matches rows", board["count"] == len(board["queue"]))

    listed = ls.api_list_leads(
        verified_person_id=PERS_DEMO, brand_id=BRAND_HAB, conn=conn
    )
    list_ids = {c["lead_id"] for c in listed["leads"]}
    queue_ids = {c["lead_id"] for c in board["queue"]}
    check("queue is a subset of the brand list", queue_ids <= list_ids, str(queue_ids - list_ids))

    by_source = {}
    for sid in (
        "demo-01",
        "demo-02",
        "demo-03",
        "demo-04",
        "demo-05",
        "demo-06",
        "demo-07",
        "demo-08",
    ):
        row = lead_by_source(conn, sid)
        check(f"{sid} fixture present", row is not None)
        if row:
            by_source[sid] = row

    want = {"demo-01", "demo-07", "demo-08"}
    skip = {"demo-02", "demo-03", "demo-04", "demo-05", "demo-06"}
    got = set()
    for sid, row in by_source.items():
        if row["lead_id"] in queue_ids:
            got.add(sid)
    check("open or unanswered fixtures are in triage", want <= got, str(sorted(got)))
    check("parked closed and answered active stay off triage", got.isdisjoint(skip), str(sorted(got & skip)))

    honesty = board["honesty"]
    check("no invented SLA target", honesty.get("sla_target_seconds") is None)
    check("invented_sla false", honesty.get("invented_sla") is False)
    check("invented_leads false", honesty.get("invented_leads") is False)
    check("metricool write false", honesty.get("metricool_write") is False)
    check("maturity stays BUILT", honesty.get("maturity") == "BUILT" and honesty.get("proven") is False)
    check("catalog CAP-GGV-04 still BUILT", cap == "BUILT", cap)

    demo1 = by_source["demo-01"]
    card1 = next(c for c in board["queue"] if c["lead_id"] == demo1["lead_id"])
    speed1 = card1["speed"]
    check("unanswered open lead is WAITING", speed1["status"] == "WAITING", speed1["status"])
    check(
        "waiting seconds come from the source clock",
        isinstance(speed1.get("waiting_seconds"), (int, float)) and speed1["waiting_seconds"] > 0,
        str(speed1.get("waiting_seconds")),
    )
    check("card SLA target is null", speed1.get("sla_target_seconds") is None)
    check("card SLA breached is null", speed1.get("sla_breached") is None)
    check("next action is Record touch", card1["next_action"]["code"] == "touch", str(card1["next_action"]))
    check("work item hook does not create", card1["work_item_hook"]["creates_work_item"] is False)
    check("claim hook does not verify on an open lead", card1["claim_hook"]["verifies"] is False)
    check("claim is not the open-lead step", card1["claim_hook"]["available"] is False)

    demo2 = by_source["demo-02"]
    sig2 = ls.speed_to_lead_signal(demo2)
    check("answered fixture is MEASURED", sig2["status"] == "MEASURED", sig2["status"])
    check(
        "measured seconds are a number",
        isinstance(sig2.get("response_seconds"), (int, float)),
        str(sig2.get("response_seconds")),
    )

    # Missing receipt clock must not become 0 or a fake SLA.
    missing = ls.ingest_observation(
        entity_id=ENTITY,
        brand_id=BRAND_HAB,
        source_system="fixture",
        source_id="speed-no-clock",
        source_observed_at=None,
        source_stage="new",
        provenance={"demo": True, "label": "DEMO no clock"},
        actor_type="SYSTEM",
        conn=conn,
    )
    missing_id = missing["lead"]["lead_id"]
    board2 = ls.api_triage_board(
        verified_person_id=PERS_DEMO, brand_id=BRAND_HAB, conn=conn
    )
    card_missing = next(c for c in board2["queue"] if c["lead_id"] == missing_id)
    sig_m = card_missing["speed"]
    check("missing source clock is UNAVAILABLE", sig_m["status"] == "UNAVAILABLE", sig_m["status"])
    check("missing clock waiting_seconds is None", sig_m.get("waiting_seconds") is None, str(sig_m))
    check("missing clock words are unavailable", sig_m.get("words") == "unavailable", sig_m.get("words"))
    check("missing clock is not zero seconds", "0 seconds" not in str(sig_m.get("words")))
    waiting_ids = [
        c["lead_id"] for c in board2["queue"] if (c.get("speed") or {}).get("status") == "WAITING"
    ]
    check(
        "waiting leads sort ahead of unavailable",
        waiting_ids and board2["queue"][0]["lead_id"] in waiting_ids
        and board2["queue"].index(card_missing) > 0,
        board2["queue"][0]["lead_id"],
    )

    # Other brand: one closed lead only. Empty queue, no invented row.
    closed_other = ls.ingest_observation(
        entity_id=ENTITY,
        brand_id=BRAND_OTHER,
        source_system="fixture",
        source_id="other-closed",
        source_observed_at="2026-09-19T01:00:00+08:00",
        source_stage="closed",
        provenance={"demo": True, "label": "OTHER closed"},
        actor_type="SYSTEM",
        conn=conn,
    )
    other_id = closed_other["lead"]["lead_id"]
    n_before = conn.execute("SELECT COUNT(*) FROM core_leads").fetchone()[0]
    other_board = ls.api_triage_board(
        verified_person_id=PERS_DENIED, brand_id=BRAND_OTHER, conn=conn
    )
    n_after = conn.execute("SELECT COUNT(*) FROM core_leads").fetchone()[0]
    check("empty triage does not invent a lead", n_before == n_after and other_board["count"] == 0)
    check(
        "empty message is explicit",
        other_board["empty"] is True and other_board["empty_message"] == "No open leads need triage.",
        str(other_board.get("empty_message")),
    )
    check("closed other-brand lead is not queued", other_id not in {c["lead_id"] for c in other_board["queue"]})
    hab_again = ls.api_triage_board(
        verified_person_id=PERS_DEMO, brand_id=BRAND_HAB, conn=conn
    )
    check("habitat triage hides the other brand", other_id not in {c["lead_id"] for c in hab_again["queue"]})

    denied = False
    denied_code = ""
    try:
        ls.api_triage_board(verified_person_id=PERS_DENIED, brand_id=BRAND_HAB, conn=conn)
    except ls.LeadSpineError as exc:
        denied = exc.code == "denied"
        denied_code = exc.code
    check("denied person triage is denied", denied, denied_code)

    # Touch → assign → link existing work item. Still open, so still on the board.
    touched = ls.record_human_touch(
        demo1["lead_id"],
        touched_at=demo1["source_observed_at"],
        verified_person_id=PERS_DEMO,
        actor_type="PERSON",
        conn=conn,
    )
    check(
        "after touch next is assign",
        ls.next_action_for_lead(touched["lead"])["code"] == "assign",
        str(ls.next_action_for_lead(touched["lead"])),
    )
    assigned = ls.assign_owner(
        demo1["lead_id"], PERS_DEMO, verified_person_id=PERS_DEMO, conn=conn
    )
    check(
        "after assign next is link work item",
        ls.next_action_for_lead(assigned["lead"])["code"] == "work-item",
    )
    wi_before = conn.execute("SELECT COUNT(*) FROM core_work_items").fetchone()[0]
    linked = ls.link_work_item(
        demo1["lead_id"], WI, verified_person_id=PERS_DEMO, actor_type="PERSON", conn=conn
    )
    wi_after = conn.execute("SELECT COUNT(*) FROM core_work_items").fetchone()[0]
    check("link uses the existing work item", linked["lead"]["current_work_item_id"] == WI)
    check("link does not create a work item", wi_before == wi_after, f"{wi_before}->{wi_after}")
    check(
        "open lead with a work item asks for Wolf lifecycle",
        ls.next_action_for_lead(linked["lead"])["code"] == "stage",
        str(ls.next_action_for_lead(linked["lead"])),
    )
    still = ls.api_triage_board(
        verified_person_id=PERS_DEMO, brand_id=BRAND_HAB, conn=conn
    )
    still_ids = {c["lead_id"] for c in still["queue"]}
    check("touched open lead stays visible until it leaves Open", demo1["lead_id"] in still_ids)

    lead4 = by_source["demo-04"]
    claimed = ls.claim_conversion(
        lead4["lead_id"], verified_person_id=PERS_DEMO, actor_type="PERSON", conn=conn
    )
    check("claim sets CLAIMED", claimed["lead"]["conversion_status"] == "CLAIMED")
    check("claim does not verify", claimed["lead"]["conversion_status"] != "VERIFIED")
    check("claim hook never verifies", ls.claim_hook(claimed["lead"])["verifies"] is False)
    after_claim = ls.api_triage_board(
        verified_person_id=PERS_DEMO, brand_id=BRAND_HAB, conn=conn
    )
    check(
        "closed claimed lead stays off the hot queue",
        lead4["lead_id"] not in {c["lead_id"] for c in after_claim["queue"]},
    )

    # Fixed clock so a future source time cannot be reported as zero.
    future = ls.ingest_observation(
        entity_id=ENTITY,
        brand_id=BRAND_HAB,
        source_system="fixture",
        source_id="speed-future-clock",
        source_observed_at="2099-01-01T00:00:00+00:00",
        source_stage="new",
        provenance={"demo": True, "label": "DEMO future clock"},
        actor_type="SYSTEM",
        conn=conn,
    )
    fixed = datetime(2026, 9, 19, 1, 0, tzinfo=timezone.utc)
    sig_f = ls.speed_to_lead_signal(future["lead"], now=fixed)
    check("future source clock is UNAVAILABLE not zero", sig_f["status"] == "UNAVAILABLE", sig_f["status"])
    check("future waiting_seconds is None", sig_f.get("waiting_seconds") is None)

    page = PAGE.read_text(encoding="utf-8")
    check("page has Needs triage", "Needs triage" in page)
    check("page says no SLA number is invented", "No SLA number is invented." in page)
    check("page fetches the triage route", "/api/leads/triage?brand=" in page)
    check("page links an existing work item", "Link work item" in page)
    check("page says claim does not verify", "Claim does not verify." in page)
    check("page keeps the demo banner", "Demo data. Not live leads." in page)
    check(
        "page keeps closed-is-not-a-sale",
        "Closed is not a sale and not verified revenue." in page,
    )

    serve = SERVE.read_text(encoding="utf-8")
    triage_at = serve.find('path == "/api/leads/triage"')
    id_at = serve.find(r'^/api/leads/([^/]+)$')
    check("serve has triage route before lead id", 0 <= triage_at < id_at, f"{triage_at} {id_at}")
    check("triage handler uses lead identity", "def _get_leads_triage" in serve and "_lead_identity" in serve)
    check(
        "touch uses server clock when the body omits touched_at",
        "now_utc_iso()" in serve and "record_human_touch" in serve,
    )
    check("identity resolver is resolve_request_identity", "resolve_request_identity" in serve)

    conn.close()
    shutil.rmtree(td, ignore_errors=True)

    check("model C file bytes unchanged", sha256(MODEL_C) == model_before)
    for path in WIP:
        check(f"WIP untouched {path.name}", sha256(path) == wip_before[str(path)])
    check("temp DB path used", "backups" in str(tmp_db) and "tmp-ggv-speed-" in str(tmp_db))

    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
