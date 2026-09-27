#!/usr/bin/env python3
"""CRM Ops × Needs-You connective — CRM/Lead/Habitat projection on Lead Spine."""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import crm_ops_needs_you_connective as ops  # noqa: E402
from core import lead_spine as spine  # noqa: E402
from core import owner_progress_needs_you_depth as nye  # noqa: E402
from core import request_auth as ra  # noqa: E402
from core import wolf_shell  # noqa: E402

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HTML = ROOT / "dashboards" / "lead-spine.html"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
OUT_OF_CRM = (
    "CMQ-AMG-DAY",
    "CMQ-AMANDA-GGV",
    "CMQ-NAS-HAIKAL",
    "CMQ-SMART-UPLOAD-RETEST",
    "CMQ-GLOBAL-NAV-OWNER",
    "CMQ-PROGRESS-NEEDS-YOU",
    "CMQ-INTEGRATION-HEALTH",
    "CMQ-DEVI-UMA-MOBILE",
)
TRIAGE_LEADS = (
    "LEAD-356124ad-10dd-4aad-b2bd-96977f63f62f",
    "LEAD-be064c4e-159c-446e-8ed3-f0a58d3e3d35",
    "LEAD-d01bc410-87a5-4277-a9d0-27b0b98de057",
)
QUIET_LEADS = (
    "LEAD-1fd19c82-a5e1-4075-b2ac-284084105d3f",
    "LEAD-d887ab10-707b-45c6-b3a8-2693daa2c1ec",
    "LEAD-7322d81e-b38b-4982-a9c6-bd479aac2503",
    "LEAD-667c83f5-67b8-46d1-a3a5-9d11b90f8314",
    "LEAD-a6309daf-3035-4794-bba7-712719079e5a",
)
NEXT_LEAD = "LEAD-356124ad-10dd-4aad-b2bd-96977f63f62f"
CAP_EXPECT = {
    "CAP-CRM-01": "BUILT",
    "CAP-CRM-02": "SPECIFIED",
    "CAP-CRM-03": "SPECIFIED",
    "CAP-CRM-04": "BUILT",
}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _ids(strip: dict) -> set[str]:
    return {str(i.get("object_id")) for i in (strip.get("items") or [])}


def _cr(item_id: str) -> str:
    conn = sqlite3.connect(str(CATALOG))
    try:
        row = conn.execute(
            "SELECT state FROM wolf_completion_items WHERE id=?",
            (item_id,),
        ).fetchone()
    finally:
        conn.close()
    return str(row[0]) if row and row[0] else "MISSING"


def test_honesty() -> None:
    check("schema", ops.CONNECTIVE_SCHEMA_ID == "wolf.crm-ops-needs-you-connective.v1")
    check("bound", ops.CONNECTIVE_BOUND == "beta-crm-loop-safe")
    check("claim id", ops.CONNECTIVE_CLAIM_ID == "bf-crm-ops-needs-you-connective-20260923")
    check("not ggv schema", "ggv-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("shell flag", wolf_shell.honesty_flags().get("crm_ops_needs_you_connective") is True)
    check("au not started", ops.au_crm_habitat_state() == "NOT STARTED")
    try:
        ops.refuse_staff_ready({})
        check("staff_ready raises", False)
    except spine.LeadSpineError as exc:
        check("staff_ready refused", exc.code == "staff_ready_refused" and exc.http_status == 405)
    try:
        ops.refuse_haikal_done({})
        check("haikal raises", False)
    except spine.LeadSpineError as exc:
        check("haikal refused", exc.code == "haikal_done_refused")
    try:
        ops.refuse_devi_done({})
        check("devi raises", False)
    except spine.LeadSpineError as exc:
        check("devi refused", exc.code == "devi_done_refused")
    try:
        ops.refuse_habitat_done({})
        check("habitat raises", False)
    except spine.LeadSpineError as exc:
        check("habitat refused", exc.code == "habitat_done_refused")
    try:
        ops.refuse_money({})
        check("money raises", False)
    except spine.LeadSpineError as exc:
        check("money refused", exc.code == "money_refused")
    try:
        ops.refuse_crm_cutover({})
        check("cutover raises", False)
    except spine.LeadSpineError as exc:
        check("cutover refused", exc.code == "crm_cutover_refused")
    try:
        ops.refuse_klaviyo({})
        check("klaviyo raises", False)
    except spine.LeadSpineError as exc:
        check("klaviyo refused", exc.code == "klaviyo_write_refused")
    try:
        ops.refuse_metricool({})
        check("metricool raises", False)
    except spine.LeadSpineError as exc:
        check("metricool refused", exc.code == "metricool_write_refused")
    try:
        ops.refuse_bzg_compose({})
        check("compose raises", False)
    except spine.LeadSpineError as exc:
        check("compose refused", exc.code == "bzg_compose_refused")
    try:
        ops.refuse_proven({})
        check("proven raises", False)
    except spine.LeadSpineError as exc:
        check("proven refused", exc.code == "proven_refused")
    try:
        ops.refuse_ready({})
        check("ready raises", False)
    except spine.LeadSpineError as exc:
        check("ready refused", exc.code == "ready_refused")
    check(
        "refuse paths",
        ops.connective_refuse_code("/api/leads/needs-you/staff-ready") == "staff_ready"
        and ops.connective_refuse_code("/api/leads/haikal-done") == "haikal_done"
        and ops.connective_refuse_code("/api/leads/devi-done") == "devi_done"
        and ops.connective_refuse_code("/api/leads/habitat-done") == "habitat_done"
        and ops.connective_refuse_code("/api/leads/needs-you/proven") == "proven"
        and ops.connective_refuse_code("/api/leads/needs-you/ready") == "ready"
        and ops.connective_refuse_code("/api/leads/needs-you/money") == "money"
        and ops.connective_refuse_code("/api/leads/needs-you/crm-cutover") == "crm_cutover"
        and ops.connective_refuse_code("/api/leads/needs-you/klaviyo") == "klaviyo"
        and ops.connective_refuse_code("/api/leads/needs-you/metricool") == "metricool"
        and ops.connective_refuse_code("/api/leads/needs-you/bzg-compose") == "bzg_compose",
    )
    check("lead list not stolen", ops.connective_refuse_code("/api/leads") is None)
    check("triage not stolen", ops.connective_refuse_code("/api/leads/triage") is None)


def test_scope_filter() -> None:
    check("ggv amanda seed out", ops._is_crm_scoped({
        "object_id": "CMQ-AMANDA-GGV",
        "business": "GGV",
        "capability": "CAP-GGV-04",
        "surface": "ggv_ops",
        "kind": "morning_seed",
    }) is False)
    check("bzg seed out", ops._is_crm_scoped({
        "object_id": "CMQ-DEVI-UMA-MOBILE",
        "business": "BZG",
        "capability": "CAP-BZG-03",
        "kind": "morning_seed",
    }) is False)
    check("nas seed out", ops._is_crm_scoped({
        "object_id": "CMQ-NAS-HAIKAL",
        "business": "GGV",
        "surface": "nas_library",
        "kind": "morning_seed",
    }) is False)
    check("crm cap in", ops._is_crm_scoped({
        "object_id": "CMQ-CRM-AMANDA",
        "business": "CRM",
        "capability": "CAP-CRM-01",
        "surface": "lead_spine",
        "kind": "morning_seed",
        "href": "/lead-spine",
    }) is True)
    check("habitat lead loop in", ops._is_crm_scoped({
        "kind": "lead_loop",
        "brand_id": "habitat",
        "object_id": "LEAD-x",
    }) is True)
    check("other brand loop out", ops._is_crm_scoped({
        "kind": "lead_loop",
        "brand_id": "atrium",
        "object_id": "LEAD-y",
    }) is False)


def test_projection_scope() -> None:
    owner = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
    check("owner strip ok", owner.get("ok") is True and owner.get("bound") == ops.CONNECTIVE_BOUND)
    check("owner schema", owner.get("schema") == ops.CONNECTIVE_SCHEMA_ID)
    owner_ids = _ids(owner)
    check("owner not empty", owner.get("empty") is False and owner.get("count", 0) > 0, str(owner.get("count")))
    check("owner count matches items", owner.get("count") == len(owner.get("items") or []))
    by_kind = owner.get("by_kind") or {}
    check(
        "owner kind sum",
        sum(by_kind.get(k, 0) for k in ops.CONNECTIVE_KINDS) == owner.get("count"),
        str(by_kind),
    )
    check("owner morning empty", by_kind.get("morning_seed") == 0, str(by_kind))
    check("owner lead loop count", by_kind.get("lead_loop") == len(TRIAGE_LEADS), str(by_kind))
    for oid in TRIAGE_LEADS:
        check(f"owner sees {oid[:12]}", oid in owner_ids)
    for oid in QUIET_LEADS:
        check(f"owner skips quiet {oid[:12]}", oid not in owner_ids)
    for oid in OUT_OF_CRM:
        check(f"owner excludes {oid}", oid not in owner_ids)
    check("owner no ggv duplicate", "CMQ-AMANDA-GGV" not in owner_ids)
    check("owner money empty", owner.get("money") is None)
    check("owner no cutover", owner.get("crm_cutover") is False and owner.get("klaviyo_write") is False)
    check("owner no metricool", owner.get("metricool_write") is False and owner.get("bzg_compose") is False)
    check("owner habitat not commissioned", owner.get("live_habitat_commission") is False)
    check("owner au flag", owner.get("au_crm_01_habitat") == "NOT STARTED")
    check("owner next connective", (owner.get("next_action") or {}).get("code") == "needs_you_connective")
    check("owner next preferred", (owner.get("next_action") or {}).get("preferred_over_pack") is True)
    check(
        "owner next is lead loop",
        (owner.get("next_action") or {}).get("object_id") == NEXT_LEAD
        and (owner.get("next_action") or {}).get("kind") == "lead_loop",
        str((owner.get("next_action") or {}).get("object_id")),
    )
    check("owner pack href kept", (owner.get("pack_next_action") or {}).get("code") == "pack_href")
    check("owner staff_ready false", owner.get("staff_ready") is False and owner.get("proven") is False)
    check("owner ready false", owner.get("ready") is False)
    check("owner haikal flag", owner.get("haikal_human") == "not_started" and owner.get("devi_retest") == "parked")
    check("owner sees full", (owner.get("seat") or {}).get("sees_full_crm") is True)
    check("owner ggv strip not copied", owner.get("ggv_strip_duplicated") is False)
    caps = (owner.get("caps") or {}).get("caps") or {}
    for cap, expect in CAP_EXPECT.items():
        check(f"{cap} {expect}", caps.get(cap) == expect, str(caps.get(cap)))
    demo_rows = [i for i in (owner.get("items") or []) if i.get("demo") is True]
    check("owner demo rows marked", len(demo_rows) == len(TRIAGE_LEADS), str(len(demo_rows)))

    amanda = ops.needs_you_connective_strip(verified_person_id="PERS-AMANDA")
    amanda_ids = _ids(amanda)
    check("amanda strip ok", amanda.get("ok") is True and amanda.get("empty") is False)
    check("amanda count honest", amanda.get("count") == len(amanda.get("items") or []))
    check("amanda seat crm", (amanda.get("seat") or {}).get("seat") == "crm_lead")
    check("amanda not full owner", (amanda.get("seat") or {}).get("sees_full_crm") is False)
    check("amanda commission not invented", (amanda.get("seat") or {}).get("invented_commission") is False)
    check("amanda habitat not live", amanda.get("live_habitat_commission") is False)
    for oid in TRIAGE_LEADS:
        check(f"amanda sees loop {oid[:12]}", oid in amanda_ids)
    for oid in OUT_OF_CRM:
        check(f"amanda excludes {oid}", oid not in amanda_ids)
    check(
        "amanda next preferred",
        (amanda.get("next_action") or {}).get("preferred_over_pack") is True
        and (amanda.get("next_action") or {}).get("object_id") == NEXT_LEAD,
    )

    for person in ("PERS-HAIKAL", "PERS-MISA", "PERS-DEVI", "PERS-OUTSIDER"):
        try:
            ops.needs_you_connective_strip(verified_person_id=person)
            check(f"{person} forbidden", False)
        except spine.LeadSpineError as exc:
            check(f"{person} forbidden", exc.code == "forbidden" and exc.http_status == 403)

    detail = ops.connective_item_detail(NEXT_LEAD, verified_person_id="PERS-MATT")
    check(
        "owner detail lead handoff",
        detail.get("reuse_needs_you_depth") is False
        and (detail.get("handoff") or {}).get("reuse_lead_loop") is True
        and (detail.get("handoff") or {}).get("read_only_here") is True,
    )
    check("detail no cutover", detail.get("crm_cutover") is False and detail.get("money") is None)
    try:
        ops.connective_item_detail("CMQ-AMG-DAY", verified_person_id="PERS-MATT")
        check("foreign detail 404", False)
    except spine.LeadSpineError as exc:
        check("foreign detail 404", exc.code == "not_found" and exc.http_status == 404)
    try:
        ops.connective_item_detail(NEXT_LEAD, verified_person_id="PERS-HAIKAL")
        check("haikal detail forbidden", False)
    except spine.LeadSpineError as exc:
        check("haikal detail forbidden", exc.code == "forbidden")
    amanda_detail = ops.connective_item_detail(NEXT_LEAD, verified_person_id="PERS-AMANDA")
    check("amanda own detail", amanda_detail.get("ok") is True and amanda_detail.get("human_done") is False)


def test_owner_only_and_lead_loop_ack() -> None:
    real = ops._commissioning_rows

    def _with_owner_only(*, state_path=None):
        rows = real(state_path=state_path)
        rows.append(
            {
                "object_id": "CMQ-CRM-OWNER-ONLY",
                "kind": "needs_you",
                "title": "Owner only CRM commissioning",
                "who": "Matt",
                "audience": "NEEDS_MATT",
                "person_to_test": "Matt",
                "priority": "P0",
                "business": "CRM",
                "capability": "CAP-CRM-01",
                "surface": "lead_spine",
                "href": "/lead-spine",
            }
        )
        return rows

    ops._commissioning_rows = _with_owner_only
    try:
        owner = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
        amanda = ops.needs_you_connective_strip(verified_person_id="PERS-AMANDA")
        check("owner sees owner-only", "CMQ-CRM-OWNER-ONLY" in _ids(owner))
        check("amanda misses owner-only", "CMQ-CRM-OWNER-ONLY" not in _ids(amanda))
        check(
            "owner-only is owner next",
            (owner.get("next_action") or {}).get("object_id") == "CMQ-CRM-OWNER-ONLY",
        )
        check(
            "owner-only not on amanda next",
            (amanda.get("next_action") or {}).get("object_id") != "CMQ-CRM-OWNER-ONLY",
        )
    finally:
        ops._commissioning_rows = real

    try:
        ops.acknowledge_handoff(NEXT_LEAD, verified_person_id="PERS-AMANDA", note="no")
        check("lead loop ack 405", False)
    except spine.LeadSpineError as exc:
        check("lead loop ack handoff_only", exc.code == "handoff_only" and exc.http_status == 405)


def test_empty_and_unauthorised_amanda() -> None:
    real_rows = ops._crm_candidates
    ops._crm_candidates = lambda **_k: []
    try:
        quiet = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
        check("empty honesty", quiet.get("empty") is True and quiet.get("count") == 0)
        check("empty next null", quiet.get("next_action") is None)
        check("empty not invented", quiet.get("invented") is False and quiet.get("invented_count") is False)
        check("empty message", "EMPTY" in str(quiet.get("empty_message") or ""))
        desk = {"ok": True}
        ops._attach_needs_you_connective(desk, person_id="PERS-MATT")
        check(
            "empty desk keeps pack",
            (desk.get("next_action") or {}).get("code") == "pack_href"
            and (desk.get("needs_you_connective") or {}).get("count") == 0,
        )
    finally:
        ops._crm_candidates = real_rows

    with tempfile.TemporaryDirectory() as td:
        bare = Path(td) / "empty.sqlite"
        sqlite3.connect(bare).close()
        check("amanda not authorised on bare catalog", ops._amanda_already_authorised(bare) is False)
        try:
            ops.needs_you_connective_strip(verified_person_id="PERS-AMANDA", catalog_db=bare)
            check("bare amanda forbidden", False)
        except spine.LeadSpineError as exc:
            check(
                "bare amanda forbidden",
                exc.code == "forbidden" and "not invented" in str(exc).lower(),
            )
        owner = ops.needs_you_connective_strip(verified_person_id="PERS-MATT", catalog_db=bare)
        check("owner still full without amanda catalog", (owner.get("seat") or {}).get("sees_full_crm") is True)


def test_acknowledge_temp_state() -> None:
    real = ops._is_crm_scoped

    def _wider(item: dict) -> bool:
        if str(item.get("object_id") or "") == "CMQ-AMG-DAY":
            item["business"] = "CRM"
            item["capability"] = "CAP-CRM-01"
            item["surface"] = "lead_spine"
            item["person_to_test"] = "Amanda"
            item["who"] = "Amanda"
            item["audience"] = "NEEDS_STAFF"
            item["href"] = "/lead-spine"
            item["open_href"] = "/lead-spine"
            return True
        return real(item)

    ops._is_crm_scoped = _wider
    try:
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state.json"
            events = Path(td) / "events.jsonl"
            ack = ops.acknowledge_handoff(
                "CMQ-AMG-DAY",
                verified_person_id="PERS-AMANDA",
                note="crm connective prove",
                state_path=state,
                events_path=events,
            )
            check("ack recorded", ack.get("recorded") is True and ack.get("commissioned") is False)
            check("ack no human done", ack.get("human_done") is False and ack.get("devi_retest") == "parked")
            check("ack no money", ack.get("money") is None and ack.get("crm_cutover") is False)
            check(
                "ack same surface",
                ack.get("duplicate_mutate_surface") is False and ack.get("reuse_needs_you_depth") is True,
            )
            event = ack.get("event") or {}
            check(
                "ack actor amanda",
                event.get("person_id") == "PERS-AMANDA" and event.get("human_commissioned") is False,
            )
            saved = json.loads(state.read_text(encoding="utf-8"))
            row = (saved.get("items") or {}).get("CMQ-AMG-DAY") or {}
            check(
                "state acknowledged",
                row.get("operator_status") == "ACKNOWLEDGED" and row.get("staff_ready") is False,
            )
            check(
                "state not commissioned",
                row.get("commissioned") is False and row.get("haikal_human") == "not_started",
            )
            try:
                ops.acknowledge_handoff(
                    "CMQ-AMG-DAY",
                    verified_person_id="PERS-HAIKAL",
                    note="no",
                    state_path=state,
                    events_path=events,
                )
                check("ack haikal forbidden", False)
            except spine.LeadSpineError as exc:
                check("ack haikal forbidden", exc.code == "forbidden")
    finally:
        ops._is_crm_scoped = real


def test_desk_prefers_connective() -> None:
    desk: dict = {"ok": True}
    spine._attach_needs_you_connective(desk, person_id="PERS-MATT")
    check("desk strip", isinstance(desk.get("needs_you_connective"), dict))
    check(
        "desk count matches",
        (desk.get("needs_you_connective") or {}).get("count")
        == len((desk.get("needs_you_connective") or {}).get("items") or []),
    )
    nxt = desk.get("next_action") or {}
    check(
        "desk next preferred",
        nxt.get("code") == "needs_you_connective" and nxt.get("preferred_over_pack") is True,
        str(nxt.get("code")),
    )
    check("desk pack next kept", (desk.get("pack_next_action") or {}).get("href") == "/lead-spine")
    check("desk no money", (desk.get("needs_you_connective") or {}).get("money") is None)


def test_crs_and_files() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    for cap, expect in CAP_EXPECT.items():
        check(f"ledger {cap}", ledger.get(cap, [None])[0] == expect, str(ledger.get(cap, [None])[0]))
    check("ledger denom", len(ledger) == 77, str(len(ledger)))
    for cr in ops.CRM_TARGET_CRS:
        check(f"crm cr open {cr[:12]}", _cr(cr) == "OPEN", _cr(cr))
    for cr in nye.TARGET_CRS:
        check(f"progress cr open {cr[:12]}", _cr(cr) == "OPEN", _cr(cr))
    text = HTML.read_text(encoding="utf-8")
    check("html connective", "Needs-You connective" in text and 'id="needs-you-connective"' in text)
    check("html empty honesty", "EMPTY" in text and "staff_ready" in text)
    check("html devi parked", "Devi retest stays parked" in text)
    check("html no cutover", "CRM cutover" in text and "Klaviyo" in text)
    check("no orphan dashboard", not (ROOT / "dashboards" / "crm-ops-needs-you.html").exists())
    source = (SCRIPTS / "core" / "crm_ops_needs_you_connective.py").read_text(encoding="utf-8")
    check("source schema id", "wolf.crm-ops-needs-you-connective.v1" in source)
    check("source not ggv strip", "wolf.ggv-ops-needs-you-connective.v1" not in source)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("serve route", "/api/leads/needs-you" in serve)
    before = subprocess.check_output(["git", "hash-object"] + list(WIP), cwd=str(ROOT), text=True)
    check("wip hashes readable", len(before.split()) == 4, before[:80])


def test_http() -> None:
    ra._ENV_LOADED = True
    import inspect
    import serve_beta as sb

    Handler = None
    for _, obj in inspect.getmembers(sb, inspect.isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            Handler = obj
            break
    check("handler found", Handler is not None)
    if Handler is None:
        return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    def call(method: str, url_path: str, subject: str | None, body: dict | None = None):
        headers = {"Accept": "application/json"}
        if subject:
            headers["X-Wolf-Subject"] = subject
        data = None
        if method != "GET":
            data = json.dumps({} if body is None else body).encode()
            headers["Content-Type"] = "application/json"
        req = Request(
            f"http://127.0.0.1:{port}{url_path}",
            headers=headers,
            method=method,
            data=data,
        )
        try:
            with urlopen(req, timeout=60) as resp:
                raw = resp.read()
                try:
                    return resp.status, json.loads(raw.decode())
                except json.JSONDecodeError:
                    return resp.status, raw
        except HTTPError as exc:
            raw = exc.read()
            try:
                parsed = json.loads(raw.decode())
            except json.JSONDecodeError:
                parsed = raw
            return exc.code, parsed

    try:
        for path in (
            "/api/leads/needs-you",
            f"/api/leads/needs-you/items/{NEXT_LEAD}",
        ):
            st, payload = call("GET", path, None)
            check(
                f"anon 403 {path.rsplit('/', 1)[-1][:24]}",
                st == 403 and (payload or {}).get("error") == "missing_subject",
                f"{st} {(payload or {}).get('error') if isinstance(payload, dict) else ''}",
            )
        st, payload = call("GET", "/lead-spine", None)
        check("anon page 403", st == 403, str(st))

        st, payload = call("GET", "/api/leads/needs-you", MATT)
        check("owner needs-you 200", st == 200 and payload.get("ok") is True, str(st))
        check("owner http bound", payload.get("bound") == ops.CONNECTIVE_BOUND, str(payload.get("bound")))
        check("owner http count", payload.get("count") == len(payload.get("items") or []))
        check("owner http staff_ready", payload.get("staff_ready") is False)
        check("owner http money", payload.get("money") is None and payload.get("crm_cutover") is False)
        check("owner http has lead", NEXT_LEAD in _ids(payload))
        check("owner http excludes amg", "CMQ-AMG-DAY" not in _ids(payload))
        check("owner http excludes ggv", "CMQ-AMANDA-GGV" not in _ids(payload))
        check("owner http devi parked", payload.get("devi_retest") == "parked")
        check(
            "owner http next",
            (payload.get("next_action") or {}).get("code") == "needs_you_connective"
            and (payload.get("next_action") or {}).get("object_id") == NEXT_LEAD,
        )

        st, payload = call("GET", "/api/leads/needs-you", AMANDA)
        check("amanda http 200", st == 200 and payload.get("ok") is True, str(st))
        check("amanda http seat", (payload.get("seat") or {}).get("seat") == "crm_lead")
        check("amanda http sees lead", NEXT_LEAD in _ids(payload))

        st, payload = call("GET", f"/api/leads/needs-you/items/{NEXT_LEAD}", HAIKAL)
        check("haikal wrong seat 403", st == 403, str(st))
        st, payload = call("GET", f"/api/leads/needs-you/items/{NEXT_LEAD}", AMANDA)
        check(
            "amanda detail 200",
            st == 200 and (payload.get("handoff") or {}).get("reuse_lead_loop") is True,
        )
        st, payload = call("GET", "/api/leads/needs-you/items/CMQ-AMG-DAY", MATT)
        check("foreign http 404", st == 404 and (payload or {}).get("error") == "not_found", str(st))
        st, _ = call("GET", "/api/leads/needs-you", OUTSIDER)
        check("outsider 403", st == 403, str(st))
        st, _ = call("GET", "/api/leads/needs-you", HAIKAL)
        check("haikal http 403", st == 403, str(st))
        st, _ = call("GET", "/api/leads/needs-you", MISA)
        check("misa http 403", st == 403, str(st))
        st, _ = call("GET", "/api/leads/needs-you", DEVI)
        check("devi http 403", st == 403, str(st))

        st, payload = call(
            "POST",
            f"/api/leads/needs-you/items/{NEXT_LEAD}/acknowledge",
            AMANDA,
            {"note": "no second surface"},
        )
        check(
            "ack lead loop 405",
            st == 405 and (payload or {}).get("error") == "handoff_only",
            str(payload)[:180],
        )
        st, payload = call("POST", "/api/leads/haikal-done", MATT, {})
        check("haikal-done refuse", st == 405 and payload.get("error") == "haikal_done_refused", str(payload)[:160])
        st, payload = call("POST", "/api/leads/devi-done", MATT, {})
        check("devi-done refuse", st == 405 and payload.get("error") == "devi_done_refused", str(payload)[:160])
        st, payload = call("POST", "/api/leads/habitat-done", MATT, {})
        check("habitat-done refuse", st == 405 and payload.get("error") == "habitat_done_refused", str(payload)[:160])
        st, payload = call("POST", "/api/leads/needs-you/proven", MATT, {})
        check("proven refuse", st == 405 and payload.get("error") == "proven_refused", str(payload)[:120])
        st, payload = call("POST", "/api/leads/needs-you/money", MATT, {})
        check("money route refuse", st == 405 and payload.get("error") == "money_refused", str(payload)[:120])
        st, payload = call("POST", "/api/leads/needs-you/crm-cutover", MATT, {})
        check("cutover route refuse", st == 405 and payload.get("error") == "crm_cutover_refused", str(payload)[:120])
        st, payload = call("POST", "/api/leads/needs-you/klaviyo", MATT, {})
        check("klaviyo route refuse", st == 405 and payload.get("error") == "klaviyo_write_refused", str(payload)[:120])
        st, payload = call("POST", "/api/leads/needs-you/bzg-compose", MATT, {})
        check("compose route refuse", st == 405 and payload.get("error") == "bzg_compose_refused", str(payload)[:120])
    finally:
        httpd.shutdown()


def main() -> None:
    test_honesty()
    test_scope_filter()
    test_projection_scope()
    test_owner_only_and_lead_loop_ack()
    test_empty_and_unauthorised_amanda()
    test_acknowledge_temp_state()
    test_desk_prefers_connective()
    test_crs_and_files()
    test_http()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        raise SystemExit(1)
    print("EXIT: SUCCESS")


if __name__ == "__main__":
    main()
