#!/usr/bin/env python3
"""CORE Ops × Needs-You connective — CORE / SOP / escalation / harden projection."""
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
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import core_mgmt_cluster as cluster  # noqa: E402
from core import core_ops_needs_you_connective as ops  # noqa: E402
from core import integration_health as health  # noqa: E402
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
HTML = ROOT / "dashboards" / "core-mgmt-cluster.html"
PROGRESS_HTML = ROOT / "dashboards" / "progress.html"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
OUT_OF_CORE = (
    "CMQ-AMG-DAY",
    "CMQ-AMANDA-GGV",
    "CMQ-NAS-HAIKAL",
    "CMQ-SMART-UPLOAD-RETEST",
    "CMQ-GLOBAL-NAV-OWNER",
    "CMQ-PROGRESS-NEEDS-YOU",
    "CMQ-DEVI-UMA-MOBILE",
    "CMQ-INTEGRATION-HEALTH",
)
CAP_EXPECT = {
    "CAP-CORE-11": "SPECIFIED",
    "CAP-CORE-12": "BUILT",
}
CORE_SEED = {
    "object_id": "CMQ-CORE-SOP",
    "kind": "morning_seed",
    "title": "SOP factory morning seed",
    "who": "Matt",
    "audience": "NEEDS_MATT",
    "person_to_test": "Matt",
    "priority": "P0",
    "business": "CORE",
    "domain": "D-CORE",
    "capability": "CAP-CORE-11",
    "surface": "sop_factory",
    "href": "/core-mgmt-cluster#sop_factory",
    "open_href": "/core-mgmt-cluster#sop_factory",
}
LOOP_ROW = {
    "object_id": "sop_factory",
    "kind": "core_loop",
    "title": "SOP draft → approve",
    "who": "Matt",
    "audience": "NEEDS_MATT",
    "priority": "P1",
    "status": "OPEN",
    "business": "CORE",
    "domain": "D-CORE",
    "surface": "sop_factory",
    "capability": "CAP-CORE-11",
    "href": "#sop_factory",
    "open_href": "#sop_factory",
    "reasons": ["recorded_attention"],
    "recorded_count": 1,
    "proven": False,
    "ready": False,
    "staff_ready": False,
    "commissioned": False,
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
    return str(row[0]) if row else "MISSING"


def test_honesty() -> None:
    check("schema", ops.CONNECTIVE_SCHEMA_ID == "wolf.core-ops-needs-you-connective.v1")
    check("bound", ops.CONNECTIVE_BOUND == "beta-connective-safe")
    check("claim id", ops.CONNECTIVE_CLAIM_ID == "bf-core-ops-needs-you-connective-20260923")
    check("not msc schema", "msc-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("not sale schema", "sale-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("not crm schema", "crm-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("not ggv schema", "ggv-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("not bzg schema", "bzg-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("not intg schema", "intg-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("not strat schema", "strat-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("not dr schema", "dr-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("shell flag", wolf_shell.honesty_flags().get("core_ops_needs_you_connective") is True)
    for name, fn, code in (
        ("proven", ops.refuse_proven, "proven_refused"),
        ("ready", ops.refuse_ready, "ready_refused"),
        ("staff_ready", ops.refuse_staff_ready, "staff_ready_refused"),
        ("haikal", ops.refuse_haikal_done, "haikal_done_refused"),
        ("devi", ops.refuse_devi_done, "devi_done_refused"),
        ("money", ops.refuse_money, "money_refused"),
        ("access", ops.refuse_access_include, "access_include_refused"),
        ("secret", ops.refuse_secret_mint, "secret_mint_refused"),
        ("compose", ops.refuse_bzg_compose, "bzg_compose_refused"),
    ):
        try:
            fn()
            check(f"{name} raises", False)
        except ops.ConnectiveError as exc:
            check(f"{name} refused", exc.code == code and exc.http_status == 405)
    check(
        "refuse map proven on strip",
        ops.connective_refuse_code("/api/core/mgmt-cluster/needs-you/proven") == "proven",
    )
    check(
        "refuse map does not steal cluster proven",
        ops.connective_refuse_code("/api/core/mgmt-cluster/proven") is None,
    )
    check(
        "refuse map does not steal cluster access",
        ops.connective_refuse_code("/api/core/mgmt-cluster/access") is None,
    )
    check(
        "refuse map does not steal cluster cloudflare",
        ops.connective_refuse_code("/api/core/mgmt-cluster/cloudflare") is None,
    )


def test_scope_filter() -> None:
    check("ggv amanda seed out", ops._is_core_scoped({
        "kind": "morning_seed", "business": "GGV", "capability": "CAP-GGV-01",
        "surface": "ggv_ops", "object_id": "CMQ-AMANDA-GGV",
    }) is False)
    check("bzg seed out", ops._is_core_scoped({
        "kind": "morning_seed", "business": "BZG", "surface": "bzg_ops",
        "href": "/bzg/uma", "object_id": "CMQ-DEVI-UMA-MOBILE",
    }) is False)
    check("amg seed out", ops._is_core_scoped({
        "kind": "needs_you", "business": "AMG", "capability": "CAP-AMG-01",
        "surface": "amg_ops", "object_id": "CMQ-AMG-DAY",
    }) is False)
    check("sale seed out", ops._is_core_scoped({
        "kind": "needs_you", "business": "SALE", "capability": "CAP-SALE-01",
        "surface": "sale_evidence", "href": "/sale-evidence", "object_id": "CMQ-SALE-EVIDENCE",
    }) is False)
    check("crm seed out", ops._is_core_scoped({
        "kind": "morning_seed", "business": "CRM", "surface": "crm_ops",
        "href": "/crm", "object_id": "CMQ-CRM-LEAD",
    }) is False)
    check("nas seed out", ops._is_core_scoped({
        "kind": "morning_seed", "surface": "nas_library", "href": "/ggv",
        "object_id": "CMQ-NAS-HAIKAL",
    }) is False)
    check("progress seed out", ops._is_core_scoped({
        "kind": "needs_you", "surface": "progress", "href": "/progress",
        "capability": "CAP-CORE-PROGRESS", "object_id": "CMQ-PROGRESS-NEEDS-YOU",
    }) is False)
    check("global nav out", ops._is_core_scoped({
        "kind": "morning_seed", "surface": "progress", "href": "/wolf",
        "capability": "CAP-CORE-NAV", "business": "System",
        "object_id": "CMQ-GLOBAL-NAV-OWNER",
    }) is False)
    check("intg health out", ops._is_core_scoped({
        "kind": "morning_seed", "business": "INTG", "capability": "CAP-INTG-01",
        "surface": "integration_health", "href": "/integration-health",
        "object_id": "CMQ-INTEGRATION-HEALTH",
    }) is False)
    check("msc seed out", ops._is_core_scoped({
        "kind": "morning_seed", "business": "MSC", "capability": "CAP-MSC-01",
        "surface": "msc_assets", "href": "/msc-mgmt-cluster", "object_id": "CMQ-MSC-ASSETS",
    }) is False)
    check("strat seed out", ops._is_core_scoped({
        "kind": "morning_seed", "business": "STRAT", "capability": "CAP-STRAT-01",
        "surface": "12wy", "href": "/12wy-prove", "object_id": "CMQ-STRAT-12WY",
    }) is False)
    check("dr seed out", ops._is_core_scoped({
        "kind": "morning_seed", "business": "DR", "capability": "CAP-DR-01",
        "surface": "restore_drill", "href": "/restore-drill", "object_id": "CMQ-DR-RESTORE",
    }) is False)
    check("sale loop out", ops._is_core_scoped({
        "kind": "sale_loop", "business": "CORE", "capability": "CAP-CORE-11",
    }) is False)
    check("dr loop out", ops._is_core_scoped({
        "kind": "dr_loop", "business": "CORE", "capability": "CAP-CORE-12",
    }) is False)
    check("progress loop out", ops._is_core_scoped({
        "kind": "progress_loop", "capability": "CAP-CORE-11",
    }) is False)
    check("strat loop out", ops._is_core_scoped({
        "kind": "strat_loop", "business": "CORE", "capability": "CAP-CORE-11",
    }) is False)
    check("sop cap in", ops._is_core_scoped({
        "kind": "morning_seed", "capability": "CAP-CORE-11", "business": "CORE",
        "surface": "sop_factory", "object_id": "CMQ-CORE-SOP",
    }) is True)
    check("escalation surface in", ops._is_core_scoped({
        "kind": "needs_you", "surface": "escalation", "business": "CORE",
        "capability": "CAP-CORE-12", "href": "/escalation-burndown",
    }) is True)
    check("harden href in", ops._is_core_scoped({
        "kind": "waiting_others", "href": "/core-harden-pack", "business": "CORE",
        "object_id": "CMQ-CORE-HARDEN",
    }) is True)
    check("core loop in", ops._is_core_scoped({
        "kind": "core_loop", "object_id": "sop_factory", "capability": "CAP-CORE-11",
    }) is True)
    check(
        "owner sees core row",
        ops._in_scope_for_seat({"audience": "NEEDS_MATT"}, {"person_id": "PERS-MATT", "seat": "owner"}) is True,
    )
    check(
        "haikal seat would not see owner row",
        ops._in_scope_for_seat({"audience": "NEEDS_MATT"}, {"person_id": "PERS-HAIKAL", "seat": "staff"}) is False,
    )


def test_live_projection() -> None:
    owner = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
    check("owner strip ok", owner.get("ok") is True and owner.get("bound") == ops.CONNECTIVE_BOUND)
    check("owner schema", owner.get("schema") == ops.CONNECTIVE_SCHEMA_ID)
    check("owner count matches items", owner.get("count") == len(owner.get("items") or []))
    check(
        "owner by_kind sums",
        sum((owner.get("by_kind") or {}).values()) == owner.get("count"),
    )
    for oid in OUT_OF_CORE:
        check(f"owner excludes {oid}", oid not in _ids(owner))
    check("owner excludes strat seed shape", "CMQ-STRAT-12WY" not in _ids(owner))
    check("owner excludes dr seed shape", "CMQ-DR-RESTORE" not in _ids(owner))
    check("owner money empty", owner.get("money") is None)
    check("owner no compose", owner.get("bzg_compose") is False)
    check("owner no access mutate", owner.get("access_mutated") is False)
    check("owner no secret mint", owner.get("secret_mint") is False)
    check("owner no cf seat", owner.get("cf_seat_mint") is False)
    check("owner staff_ready false", owner.get("staff_ready") is False and owner.get("proven") is False)
    check("owner ready false", owner.get("ready") is False)
    check("owner not commissioned", owner.get("commissioned") is False and owner.get("adopted") is False)
    check("owner haikal flag", owner.get("haikal_human") == "not_started" and owner.get("devi_retest") == "parked")
    check("owner sees full", (owner.get("seat") or {}).get("sees_full_core") is True)
    check("owner commission not invented", (owner.get("seat") or {}).get("invented_commission") is False)
    check(
        "strips not copied",
        owner.get("msc_strip_duplicated") is False
        and owner.get("sale_strip_duplicated") is False
        and owner.get("crm_strip_duplicated") is False
        and owner.get("ggv_strip_duplicated") is False
        and owner.get("bzg_strip_duplicated") is False
        and owner.get("intg_strip_duplicated") is False
        and owner.get("strat_strip_duplicated") is False
        and owner.get("dr_strip_duplicated") is False
        and owner.get("progress_strip_duplicated") is False,
    )
    caps = (owner.get("caps") or {}).get("caps") or {}
    for cap, expect in CAP_EXPECT.items():
        check(f"{cap} {expect}", caps.get(cap) == expect, str(caps.get(cap)))
    for cr in ops.CORE_TARGET_CRS:
        check(
            f"strip core cr {cr[:12]} open",
            ((owner.get("caps") or {}).get("core_crs") or {}).get(cr) == "OPEN",
        )
    for cr in nye.TARGET_CRS:
        check(
            f"strip progress cr {cr[:12]} open",
            ((owner.get("caps") or {}).get("progress_core_crs") or {}).get(cr) == "OPEN",
        )
    check("false resolve flag", (owner.get("caps") or {}).get("false_resolve_cr") is False)
    check("cap 11 stays specified", (owner.get("caps") or {}).get("cap_core_11") == "SPECIFIED")
    check("cap 12 stays built", (owner.get("caps") or {}).get("cap_core_12") == "BUILT")
    by_kind = owner.get("by_kind") or {}
    if owner.get("count") == 0:
        check("live empty honesty", owner.get("empty") is True)
        check("live next null", owner.get("next_action") is None)
        check("live core loop empty", by_kind.get("core_loop") == 0)
    else:
        check("live empty flag false", owner.get("empty") is False)
        check(
            "live next preferred",
            (owner.get("next_action") or {}).get("preferred_over_pack") is True
            and (owner.get("next_action") or {}).get("proven") is False
            and (owner.get("next_action") or {}).get("ready") is False,
        )
        check(
            "live rows not invented done",
            all(
                i.get("proven") is False and i.get("ready") is False and i.get("staff_ready") is False
                for i in owner.get("items") or []
            ),
        )
    for person in ("PERS-HAIKAL", "PERS-MISA", "PERS-DEVI", "PERS-AMANDA"):
        try:
            ops.needs_you_connective_strip(verified_person_id=person)
            check(f"{person} forbidden", False)
        except ops.ConnectiveError as exc:
            check(f"{person} forbidden", exc.code == "forbidden" and exc.http_status == 403)
    try:
        ops.connective_item_detail("CMQ-AMG-DAY", verified_person_id="PERS-MATT")
        check("foreign detail 404", False)
    except ops.ConnectiveError as exc:
        check("foreign detail 404", exc.code == "not_found" and exc.http_status == 404)
    try:
        ops.connective_item_detail("CMQ-PROGRESS-NEEDS-YOU", verified_person_id="PERS-MATT")
        check("progress detail 404", False)
    except ops.ConnectiveError as exc:
        check("progress detail 404", exc.code == "not_found" and exc.http_status == 404)
    try:
        ops.connective_item_detail("CMQ-GLOBAL-NAV-OWNER", verified_person_id="PERS-HAIKAL")
        check("haikal detail forbidden", False)
    except ops.ConnectiveError as exc:
        check("haikal detail forbidden", exc.code == "forbidden")


def test_fixture_prefers_and_core_loop() -> None:
    real = ops._commissioning_rows

    def _with_core(*, state_path=None):
        rows = real(state_path=state_path)
        rows.append(dict(CORE_SEED))
        rows.append(
            {
                "object_id": "CMQ-CORE-ESC",
                "kind": "needs_you",
                "title": "Escalation burn-down needs a look",
                "who": "Matt",
                "audience": "NEEDS_MATT",
                "priority": "P1",
                "business": "CORE",
                "capability": "CAP-CORE-12",
                "surface": "escalation",
                "href": "/escalation-burndown",
                "open_href": "/escalation-burndown",
            }
        )
        return rows

    ops._commissioning_rows = _with_core
    try:
        owner = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
        ids = _ids(owner)
        check("fixture sees sop seed", "CMQ-CORE-SOP" in ids)
        check("fixture sees escalation seed", "CMQ-CORE-ESC" in ids)
        check("fixture count matches", owner.get("count") == len(owner.get("items") or []))
        check("fixture still excludes amg", "CMQ-AMG-DAY" not in ids)
        check("fixture still excludes progress", "CMQ-PROGRESS-NEEDS-YOU" not in ids)
        check("fixture still excludes nav", "CMQ-GLOBAL-NAV-OWNER" not in ids)
        check("fixture still excludes dr", "CMQ-DR-RESTORE" not in ids)
        check("fixture still excludes strat", "CMQ-STRAT-12WY" not in ids)
        check(
            "fixture next preferred",
            (owner.get("next_action") or {}).get("code") == "needs_you_connective"
            and (owner.get("next_action") or {}).get("preferred_over_pack") is True
            and (owner.get("next_action") or {}).get("object_id") == "CMQ-CORE-SOP"
            and (owner.get("next_action") or {}).get("proven") is False,
            str((owner.get("next_action") or {}).get("object_id")),
        )
        check("fixture secret false", owner.get("secret_mint") is False and owner.get("bzg_compose") is False)
        detail = ops.connective_item_detail("CMQ-CORE-SOP", verified_person_id="PERS-MATT")
        check(
            "seed detail reuses needs-you",
            detail.get("reuse_needs_you_depth") is True
            and (detail.get("handoff") or {}).get("duplicate_mutate_surface") is False
            and detail.get("proven") is False
            and detail.get("staff_ready") is False,
        )
        desk = {
            "ok": True,
            "primary_next": {
                "code": "draft_sop",
                "label": "Draft an SOP via the factory API",
                "href": "#sop_factory",
            },
        }
        ops._attach_needs_you_connective(desk, person_id="PERS-MATT")
        check(
            "desk prefers connective",
            (desk.get("primary_next") or {}).get("code") == "needs_you_connective"
            and (desk.get("next_action") or {}).get("preferred_over_pack") is True,
        )
        check(
            "desk kept pack href",
            (desk.get("pack_next_action") or {}).get("code") == "draft_sop",
        )
    finally:
        ops._commissioning_rows = real

    real_loop = ops._core_loop_rows
    ops._core_loop_rows = lambda **_k: [dict(LOOP_ROW)]
    try:
        loop = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
        ids = _ids(loop)
        check("core loop sees recorded attention", "sop_factory" in ids)
        check(
            "core loop count",
            (loop.get("by_kind") or {}).get("core_loop", 0) >= 1,
            str(loop.get("by_kind")),
        )
        row = next(i for i in (loop.get("items") or []) if i.get("object_id") == "sop_factory")
        check("core loop not proven", row.get("proven") is False and row.get("ready") is False)
        check("core loop no secret", row.get("secret_mint") is False and row.get("staff_ready") is False)
        detail = ops.connective_item_detail(
            "sop_factory", verified_person_id="PERS-MATT"
        )
        check(
            "core loop detail handoff",
            detail.get("reuse_needs_you_depth") is False
            and (detail.get("handoff") or {}).get("read_only_here") is True
            and (detail.get("handoff") or {}).get("reuse_core_loop") is True,
        )
        try:
            ops.acknowledge_handoff(
                "sop_factory",
                verified_person_id="PERS-MATT",
                note="no second surface",
            )
            check("core loop ack 405", False)
        except ops.ConnectiveError as exc:
            check("core loop ack handoff_only", exc.code == "handoff_only" and exc.http_status == 405)
    finally:
        ops._core_loop_rows = real_loop


def test_empty_desk() -> None:
    real_rows = ops._core_candidates
    ops._core_candidates = lambda **_k: []
    try:
        quiet = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
        check("empty honesty", quiet.get("empty") is True and quiet.get("count") == 0)
        check("empty next null", quiet.get("next_action") is None)
        check("empty not invented", quiet.get("invented") is False and quiet.get("invented_count") is False)
        check("empty message", "EMPTY" in str(quiet.get("empty_message") or ""))
        desk = {
            "ok": True,
            "primary_next": {
                "code": "draft_sop",
                "label": "Draft an SOP via the factory API",
                "href": "#sop_factory",
            },
        }
        ops._attach_needs_you_connective(desk, person_id="PERS-MATT")
        check(
            "empty desk keeps pack",
            (desk.get("primary_next") or {}).get("code") == "draft_sop"
            and (desk.get("next_action") or {}).get("code") == "draft_sop"
            and (desk.get("needs_you_connective") or {}).get("count") == 0,
        )
    finally:
        ops._core_candidates = real_rows


def test_acknowledge_temp_state() -> None:
    real = ops._is_core_scoped

    def _wider(item: dict) -> bool:
        if str(item.get("object_id") or "") == "CMQ-AMG-DAY":
            item["business"] = "CORE"
            item["capability"] = "CAP-CORE-11"
            item["surface"] = "sop_factory"
            item["domain"] = "D-CORE"
            item["person_to_test"] = "Matt"
            item["who"] = "Matt"
            item["audience"] = "NEEDS_MATT"
            item["href"] = "/core-mgmt-cluster#sop_factory"
            item["open_href"] = "/core-mgmt-cluster#sop_factory"
            return True
        return real(item)

    ops._is_core_scoped = _wider
    try:
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state.json"
            events = Path(td) / "events.jsonl"
            ack = ops.acknowledge_handoff(
                "CMQ-AMG-DAY",
                verified_person_id="PERS-MATT",
                note="core connective prove",
                state_path=state,
                events_path=events,
            )
            check("ack recorded", ack.get("recorded") is True and ack.get("commissioned") is False)
            check("ack no human done", ack.get("human_done") is False and ack.get("devi_retest") == "parked")
            check("ack no money", ack.get("money") is None and ack.get("bzg_compose") is False)
            check("ack no proven", ack.get("proven") is False and ack.get("ready") is False)
            check("ack no secret", ack.get("secret_mint") is False and ack.get("access_mutated") is False)
            check("ack cr not resolved", ack.get("cr_resolved") is False)
            check(
                "ack same surface",
                ack.get("duplicate_mutate_surface") is False and ack.get("reuse_needs_you_depth") is True,
            )
            event = ack.get("event") or {}
            check(
                "ack actor owner",
                event.get("person_id") == "PERS-MATT" and event.get("human_commissioned") is False,
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
    finally:
        ops._is_core_scoped = real


def test_crs_and_files() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("denominator 77", len(ledger) == 77, str(len(ledger)))
    for cap, expect in CAP_EXPECT.items():
        got = ledger.get(cap, [None])[0]
        check(f"ledger {cap}", got == expect, str(got))
    for cr in ops.CORE_TARGET_CRS:
        check(f"core cr {cr} open", _cr(cr) == "OPEN", _cr(cr))
    for cr in nye.TARGET_CRS:
        check(f"progress cr {cr} open", _cr(cr) == "OPEN", _cr(cr))
    text = HTML.read_text(encoding="utf-8")
    check("html connective", "Needs-You connective" in text and 'id="needs-you-connective"' in text)
    check("html still cluster bound", "beta-core-safe" in text)
    check("html kicker", "CORE / SOP / escalation / harden" in text)
    check("html no orphan", "core-ops-needs-you.html" not in text)
    check("html no dr copy", "DR / restore drill" not in text)
    progress = PROGRESS_HTML.read_text(encoding="utf-8") if PROGRESS_HTML.is_file() else ""
    check("progress html has no core strip", "CORE / SOP / escalation / harden" not in progress)
    source = (SCRIPTS / "core" / "core_ops_needs_you_connective.py").read_text(encoding="utf-8")
    check("source schema id", "wolf.core-ops-needs-you-connective.v1" in source)
    check("source not msc strip", "wolf.msc-ops-needs-you-connective.v1" not in source)
    check("source not sale strip", "wolf.sale-ops-needs-you-connective.v1" not in source)
    check("source not crm strip", "wolf.crm-ops-needs-you-connective.v1" not in source)
    check("source not ggv strip", "wolf.ggv-ops-needs-you-connective.v1" not in source)
    check("source not bzg strip", "wolf.bzg-ops-needs-you-connective.v1" not in source)
    check("source not intg strip", "wolf.intg-ops-needs-you-connective.v1" not in source)
    check("source not strat strip", "wolf.strat-ops-needs-you-connective.v1" not in source)
    check("source not dr strip", "wolf.dr-ops-needs-you-connective.v1" not in source)
    report = health.build_report()
    retired = {str(r.get("source_id")): r for r in (report.get("retired") or [])}
    check("clickup retired", (retired.get("clickup") or {}).get("status") == "RETIRED")
    check("telegram retired", (retired.get("telegram") or {}).get("status") == "RETIRED")
    desk = cluster.build_desk(verified_person_id="PERS-MATT")
    check("desk has strip", isinstance(desk.get("needs_you_connective"), dict))
    check(
        "desk strip count",
        (desk.get("needs_you_connective") or {}).get("count")
        == len((desk.get("needs_you_connective") or {}).get("items") or []),
    )
    check("desk proven false", desk.get("proven") is False)
    check("desk ready false", desk.get("ready") is False)
    check("desk money empty", desk.get("money") is None)
    check("desk bound stays cluster", desk.get("bound") == "beta-core-safe")
    check("desk needs nav", any(n.get("id") == "needs" for n in (desk.get("nav") or [])))
    if (desk.get("needs_you_connective") or {}).get("count"):
        check(
            "cluster desk prefers connective",
            (desk.get("primary_next") or {}).get("code") == "needs_you_connective",
            str((desk.get("primary_next") or {}).get("code")),
        )
    else:
        check(
            "cluster desk keeps module next",
            (desk.get("primary_next") or {}).get("code") != "needs_you_connective",
        )
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
            "/api/core/mgmt-cluster/needs-you",
            "/api/core/mgmt-cluster/needs-you/items/CMQ-AMG-DAY",
        ):
            st, payload = call("GET", path, None)
            check(
                f"anon 403 {path.rsplit('/', 1)[-1][:24]}",
                st == 403 and (payload or {}).get("error") == "missing_subject",
                f"{st} {(payload or {}).get('error') if isinstance(payload, dict) else ''}",
            )
        st, payload = call("GET", "/api/core/mgmt-cluster/needs-you", MATT)
        check("owner needs-you 200", st == 200 and payload.get("ok") is True, str(st))
        check("owner http bound", payload.get("bound") == ops.CONNECTIVE_BOUND, str(payload.get("bound")))
        check("owner http count", payload.get("count") == len(payload.get("items") or []))
        check("owner http staff_ready", payload.get("staff_ready") is False)
        check("owner http money", payload.get("money") is None and payload.get("bzg_compose") is False)
        check("owner http proven false", payload.get("proven") is False and payload.get("ready") is False)
        check("owner http no secret", payload.get("secret_mint") is False and payload.get("access_mutated") is False)
        check("owner http excludes amg", "CMQ-AMG-DAY" not in _ids(payload))
        check("owner http excludes ggv", "CMQ-AMANDA-GGV" not in _ids(payload))
        check("owner http excludes bzg", "CMQ-DEVI-UMA-MOBILE" not in _ids(payload))
        check("owner http excludes progress", "CMQ-PROGRESS-NEEDS-YOU" not in _ids(payload))
        check("owner http excludes nav", "CMQ-GLOBAL-NAV-OWNER" not in _ids(payload))
        check("owner http devi parked", payload.get("devi_retest") == "parked")
        if payload.get("count") == 0:
            check("owner http empty next", payload.get("next_action") is None and payload.get("empty") is True)
        else:
            check("owner http next preferred", (payload.get("next_action") or {}).get("preferred_over_pack") is True)

        st, payload = call("GET", "/api/core/mgmt-cluster", MATT)
        check("desk 200", st == 200 and isinstance(payload.get("needs_you_connective"), dict), str(st))
        check(
            "desk strip count",
            (payload.get("needs_you_connective") or {}).get("count")
            == len((payload.get("needs_you_connective") or {}).get("items") or []),
        )
        check("desk cluster bound", payload.get("bound") == "beta-core-safe", str(payload.get("bound")))
        check("desk http proven", payload.get("proven") is False and payload.get("money") is None)

        st, payload = call("GET", "/api/core/mgmt-cluster/needs-you/items/CMQ-AMG-DAY", MATT)
        check("foreign http 404", st == 404 and (payload or {}).get("error") == "not_found", str(st))
        st, _ = call("GET", "/api/core/mgmt-cluster/needs-you", OUTSIDER)
        check("outsider 403", st == 403, str(st))
        st, payload = call("GET", "/api/core/mgmt-cluster/needs-you", HAIKAL)
        check("haikal http 403", st == 403 and (payload or {}).get("error") == "forbidden", str(st))
        st, _ = call("GET", "/api/core/mgmt-cluster/needs-you", MISA)
        check("misa http 403", st == 403, str(st))
        st, _ = call("GET", "/api/core/mgmt-cluster/needs-you", DEVI)
        check("devi http 403", st == 403, str(st))
        st, payload = call("GET", "/api/core/mgmt-cluster/needs-you", AMANDA)
        check("amanda http 403", st == 403 and (payload or {}).get("error") == "forbidden", str(payload)[:120])

        st, page = call("GET", "/core-mgmt-cluster", MATT)
        page_bytes = page if isinstance(page, bytes) else (page.encode() if isinstance(page, str) else b"")
        check(
            "owner page soft-lands without copying strip",
            st == 200
            and b"CORE / SOP / escalation / harden" not in page_bytes,
            str(st),
        )

        class _NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        redir = Request(
            f"http://127.0.0.1:{port}/core-mgmt-cluster",
            headers={"Accept": "text/html", "X-Wolf-Subject": MATT},
            method="GET",
        )
        try:
            with build_opener(_NoRedirect).open(redir, timeout=30) as resp:
                redir_status = resp.status
                location = resp.headers.get("Location")
        except HTTPError as exc:
            redir_status = exc.code
            location = exc.headers.get("Location") if exc.headers else None
        check(
            "cluster route soft-lands on progress",
            redir_status == 302 and location == "/progress",
            f"{redir_status} {location}",
        )
        check(
            "desk html file has connective",
            b"needs-you-connective" in HTML.read_bytes(),
        )
        st, _ = call("GET", "/core-mgmt-cluster", None)
        check("anon page 403", st == 403, str(st))

        st, payload = call(
            "POST",
            "/api/core/mgmt-cluster/needs-you/items/CMQ-AMG-DAY/acknowledge",
            MATT,
            {"note": "no"},
        )
        check("ack missing core row 404", st == 404 and (payload or {}).get("error") == "not_found", str(st))
        st, payload = call("POST", "/api/core/mgmt-cluster/access", MATT, {})
        check(
            "cluster access still refused",
            st == 405 and (payload or {}).get("error") == "cloudflare_refused",
            str(payload)[:160],
        )
        st, payload = call("POST", "/api/core/mgmt-cluster/proven", MATT, {})
        check(
            "cluster proven still refused",
            st == 405 and (payload or {}).get("error") == "proven_refused",
            str(payload)[:160],
        )
        st, payload = call("POST", "/api/core/mgmt-cluster/commission", MATT, {})
        check(
            "cluster commission still refused",
            st == 405 and (payload or {}).get("error") == "commission_refused",
            str(payload)[:160],
        )
        for path, code in (
            ("/api/core/mgmt-cluster/haikal-done", "haikal_done_refused"),
            ("/api/core/mgmt-cluster/devi-done", "devi_done_refused"),
            ("/api/core/mgmt-cluster/secret-mint", "secret_mint_refused"),
            ("/api/core/mgmt-cluster/access-include", "access_include_refused"),
            ("/api/core/mgmt-cluster/bzg-compose", "bzg_compose_refused"),
            ("/api/core/mgmt-cluster/needs-you/proven", "proven_refused"),
            ("/api/core/mgmt-cluster/needs-you/ready", "ready_refused"),
            ("/api/core/mgmt-cluster/needs-you/money", "money_refused"),
            ("/api/core/mgmt-cluster/needs-you/bzg-compose", "bzg_compose_refused"),
            ("/api/core/mgmt-cluster/needs-you/staff-ready", "staff_ready_refused"),
        ):
            st, payload = call("POST", path, MATT, {})
            check(
                f"refuse {path.rsplit('/', 1)[-1]}",
                st == 405 and (payload or {}).get("error") == code,
                str(payload)[:160],
            )
    finally:
        httpd.shutdown()


def main() -> None:
    test_honesty()
    test_scope_filter()
    test_live_projection()
    test_fixture_prefers_and_core_loop()
    test_empty_desk()
    test_acknowledge_temp_state()
    test_crs_and_files()
    test_http()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        raise SystemExit(1)
    print("EXIT: SUCCESS")


if __name__ == "__main__":
    main()
