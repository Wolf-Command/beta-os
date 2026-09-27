#!/usr/bin/env python3
"""MSC Ops × Needs-You connective — MSC/asset/posture/compliance/cyber/records projection."""
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

from core import integration_health as health  # noqa: E402
from core import msc_mgmt_cluster as msc  # noqa: E402
from core import msc_ops_needs_you_connective as ops  # noqa: E402
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
HTML = ROOT / "dashboards" / "msc-mgmt-cluster.html"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
OUT_OF_MSC = (
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
    "CAP-MSC-01": "SPECIFIED",
    "CAP-MSC-02": "BUILT",
    "CAP-MSC-03": "SPECIFIED",
    "CAP-MSC-04": "SPECIFIED",
    "CAP-MSC-05": "SPECIFIED",
}
MSC_SEED = {
    "object_id": "CMQ-MSC-ASSETS",
    "kind": "morning_seed",
    "title": "Asset register morning seed",
    "who": "Matt",
    "audience": "NEEDS_MATT",
    "person_to_test": "Matt",
    "priority": "P0",
    "business": "MSC",
    "domain": "D-MSC",
    "capability": "CAP-MSC-01",
    "surface": "msc_assets",
    "href": "/msc-assets",
    "open_href": "/msc-assets",
}
LOOP_ROW = {
    "object_id": "asset_register",
    "kind": "msc_loop",
    "title": "Asset register recorded attention",
    "who": "Matt",
    "audience": "NEEDS_MATT",
    "priority": "P1",
    "status": "OPEN",
    "business": "MSC",
    "domain": "D-MSC",
    "surface": "assets",
    "capability": "CAP-MSC-01",
    "href": "/msc-assets",
    "open_href": "/msc-assets",
    "reasons": ["recorded_attention"],
    "live_mfa": False,
    "compliance_done": False,
    "legal_hold": False,
    "recorded_count": 1,
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
    check("schema", ops.CONNECTIVE_SCHEMA_ID == "wolf.msc-ops-needs-you-connective.v1")
    check("bound", ops.CONNECTIVE_BOUND == "beta-connective-safe")
    check("claim id", ops.CONNECTIVE_CLAIM_ID == "bf-msc-ops-needs-you-connective-20260923")
    check("not sale schema", "sale-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("not crm schema", "crm-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("not ggv schema", "ggv-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("not bzg schema", "bzg-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("not intg schema", "intg-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("shell flag", wolf_shell.honesty_flags().get("msc_ops_needs_you_connective") is True)
    for name, fn, code in (
        ("staff_ready", ops.refuse_staff_ready, "staff_ready_refused"),
        ("haikal", ops.refuse_haikal_done, "haikal_done_refused"),
        ("devi", ops.refuse_devi_done, "devi_done_refused"),
        ("live mfa", ops.refuse_live_mfa, "live_mfa_refused"),
        ("compliance done", ops.refuse_compliance_done, "compliance_done_refused"),
        ("legal hold", ops.refuse_legal_hold, "legal_hold_refused"),
        ("access include", ops.refuse_access_include, "access_include_refused"),
        ("secret mint", ops.refuse_secret_mint, "secret_mint_refused"),
        ("money", ops.refuse_money, "money_refused"),
        ("compose", ops.refuse_bzg_compose, "bzg_compose_refused"),
        ("proven", ops.refuse_proven, "proven_refused"),
        ("ready", ops.refuse_ready, "ready_refused"),
    ):
        try:
            fn({})
            check(f"{name} raises", False)
        except ops.ConnectiveError as exc:
            check(f"{name} refused", exc.code == code and exc.http_status == 405)
    check(
        "refuse paths",
        ops.connective_refuse_code("/api/msc/mgmt-cluster/needs-you/staff-ready") == "staff_ready"
        and ops.connective_refuse_code("/api/msc/mgmt-cluster/haikal-done") == "haikal_done"
        and ops.connective_refuse_code("/api/msc/mgmt-cluster/devi-done") == "devi_done"
        and ops.connective_refuse_code("/api/msc/mgmt-cluster/live-mfa") == "live_mfa"
        and ops.connective_refuse_code("/api/msc/mgmt-cluster/compliance-done") == "compliance_done"
        and ops.connective_refuse_code("/api/msc/mgmt-cluster/secret-mint") == "secret_mint"
        and ops.connective_refuse_code("/api/msc/mgmt-cluster/access-include") == "access_include"
        and ops.connective_refuse_code("/api/msc/mgmt-cluster/needs-you/legal-hold") == "legal_hold"
        and ops.connective_refuse_code("/api/msc/mgmt-cluster/needs-you/proven") == "proven"
        and ops.connective_refuse_code("/api/msc/mgmt-cluster/needs-you/ready") == "ready"
        and ops.connective_refuse_code("/api/msc/mgmt-cluster/needs-you/money") == "money"
        and ops.connective_refuse_code("/api/msc/mgmt-cluster/needs-you/bzg-compose") == "bzg_compose"
        and ops.connective_refuse_code("/api/msc/mgmt-cluster") is None
        and ops.connective_refuse_code("/api/msc/mgmt-cluster/access") is None
        and ops.connective_refuse_code("/api/msc/mgmt-cluster/secret") is None,
    )


def test_scope_filter() -> None:
    check("ggv amanda seed out", ops._is_msc_scoped({
        "object_id": "CMQ-AMANDA-GGV",
        "business": "GGV",
        "capability": "CAP-GGV-04",
        "surface": "ggv_ops",
        "kind": "morning_seed",
    }) is False)
    check("bzg seed out", ops._is_msc_scoped({
        "object_id": "CMQ-DEVI-UMA-MOBILE",
        "business": "BZG",
        "capability": "CAP-BZG-03",
        "kind": "morning_seed",
    }) is False)
    check("amg seed out", ops._is_msc_scoped({
        "object_id": "CMQ-AMG-DAY",
        "business": "AMG",
        "capability": "CAP-AMG-04",
        "surface": "amg_ops",
        "kind": "morning_seed",
    }) is False)
    check("sale seed out", ops._is_msc_scoped({
        "object_id": "CMQ-SALE-EVIDENCE",
        "business": "SALE",
        "capability": "CAP-SALE-01",
        "surface": "sale_evidence",
        "href": "/sale-evidence-pack",
        "kind": "morning_seed",
    }) is False)
    check("crm seed out", ops._is_msc_scoped({
        "object_id": "CMQ-CRM-AMANDA",
        "business": "CRM",
        "capability": "CAP-CRM-01",
        "surface": "lead_spine",
        "href": "/lead-spine",
        "kind": "morning_seed",
    }) is False)
    check("nas seed out", ops._is_msc_scoped({
        "object_id": "CMQ-NAS-HAIKAL",
        "business": "GGV",
        "surface": "nas_library",
        "kind": "morning_seed",
    }) is False)
    check("progress seed out", ops._is_msc_scoped({
        "object_id": "CMQ-PROGRESS-NEEDS-YOU",
        "business": "System",
        "capability": "CAP-CORE-PROGRESS",
        "surface": "progress",
        "kind": "morning_seed",
    }) is False)
    check("intg health out", ops._is_msc_scoped({
        "object_id": "CMQ-INTEGRATION-HEALTH",
        "business": "System",
        "capability": "CAP-INTG-HEALTH",
        "surface": "integration_health",
        "open_href": "/integration-health",
        "kind": "morning_seed",
    }) is False)
    check("sale loop out", ops._is_msc_scoped({
        "kind": "sale_loop",
        "object_id": "sale_evidence_pack",
        "business": "SALE",
    }) is False)
    check("intg loop out", ops._is_msc_scoped({
        "kind": "intg_loop",
        "object_id": "intg_connector_cap_tests",
        "business": "INTG",
    }) is False)
    check("msc cap in", ops._is_msc_scoped({
        "object_id": "CMQ-MSC-ASSETS",
        "business": "MSC",
        "capability": "CAP-MSC-01",
        "surface": "msc_assets",
        "kind": "morning_seed",
        "href": "/msc-assets",
    }) is True)
    check("posture surface in", ops._is_msc_scoped({
        "object_id": "CMQ-MSC-POSTURE",
        "business": "MSC",
        "capability": "CAP-MSC-02",
        "surface": "msc_posture",
        "href": "/msc-posture",
        "kind": "needs_you",
    }) is True)
    check("msc loop in", ops._is_msc_scoped({
        "kind": "msc_loop",
        "object_id": "asset_register",
        "business": "MSC",
    }) is True)
    owner_only = dict(MSC_SEED)
    check(
        "non-owner misses owner-only",
        ops._in_scope_for_seat(owner_only, {"person_id": "PERS-AMANDA", "seat": "staff"}) is False,
    )
    check(
        "owner sees owner-only",
        ops._in_scope_for_seat(owner_only, {"person_id": "PERS-MATT", "seat": "owner"}) is True,
    )


def test_live_projection() -> None:
    owner = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
    check("owner strip ok", owner.get("ok") is True and owner.get("bound") == ops.CONNECTIVE_BOUND)
    check("owner schema", owner.get("schema") == ops.CONNECTIVE_SCHEMA_ID)
    check("owner count matches items", owner.get("count") == len(owner.get("items") or []))
    by_kind = owner.get("by_kind") or {}
    check(
        "owner kind sum",
        sum(by_kind.get(k, 0) for k in ops.CONNECTIVE_KINDS) == owner.get("count"),
        str(by_kind),
    )
    for oid in OUT_OF_MSC:
        check(f"owner excludes {oid}", oid not in _ids(owner))
    check("owner money empty", owner.get("money") is None)
    check("owner no compose", owner.get("bzg_compose") is False)
    check("owner mfa not live", owner.get("live_mfa") is False and owner.get("compliance_done") is False)
    check("owner no legal hold", owner.get("legal_hold") is False and owner.get("access_mutated") is False)
    check("owner no secret mint", owner.get("secret_mint") is False)
    check("owner staff_ready false", owner.get("staff_ready") is False and owner.get("proven") is False)
    check("owner ready false", owner.get("ready") is False)
    check("owner haikal flag", owner.get("haikal_human") == "not_started" and owner.get("devi_retest") == "parked")
    check("owner sees full", (owner.get("seat") or {}).get("sees_full_msc") is True)
    check("owner commission not invented", (owner.get("seat") or {}).get("invented_commission") is False)
    check(
        "strips not copied",
        owner.get("sale_strip_duplicated") is False
        and owner.get("crm_strip_duplicated") is False
        and owner.get("ggv_strip_duplicated") is False
        and owner.get("bzg_strip_duplicated") is False
        and owner.get("intg_strip_duplicated") is False,
    )
    caps = (owner.get("caps") or {}).get("caps") or {}
    for cap, expect in CAP_EXPECT.items():
        check(f"{cap} {expect}", caps.get(cap) == expect, str(caps.get(cap)))
    for row in owner.get("items") or []:
        check(
            f"row honest {row.get('object_id')}",
            row.get("live_mfa") is False
            and row.get("compliance_done") is False
            and row.get("legal_hold") is False
            and row.get("staff_ready") is False,
        )
    if owner.get("count") == 0:
        check("live empty honesty", owner.get("empty") is True)
        check("live next null", owner.get("next_action") is None)
        check("live msc loop empty", by_kind.get("msc_loop") == 0)
    else:
        check("live empty flag false", owner.get("empty") is False)
        check(
            "live next preferred",
            (owner.get("next_action") or {}).get("preferred_over_pack") is True
            and (owner.get("next_action") or {}).get("live_mfa") is False,
        )
        check(
            "live loop only recorded",
            by_kind.get("msc_loop") == sum(
                1 for row in (owner.get("items") or []) if row.get("kind") == "msc_loop"
            ),
        )
    for person in ("PERS-HAIKAL", "PERS-MISA", "PERS-DEVI", "PERS-AMANDA", "PERS-OUTSIDER"):
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
        ops.connective_item_detail("CMQ-INTEGRATION-HEALTH", verified_person_id="PERS-HAIKAL")
        check("haikal detail forbidden", False)
    except ops.ConnectiveError as exc:
        check("haikal detail forbidden", exc.code == "forbidden")


def test_fixture_prefers_and_msc_loop() -> None:
    real = ops._commissioning_rows

    def _with_msc(*, state_path=None):
        rows = real(state_path=state_path)
        rows.append(dict(MSC_SEED))
        rows.append(
            {
                "object_id": "CMQ-MSC-CYBER",
                "kind": "needs_you",
                "title": "Cyber baseline needs a look",
                "who": "Matt",
                "audience": "NEEDS_MATT",
                "priority": "P1",
                "business": "MSC",
                "capability": "CAP-MSC-04",
                "surface": "msc_cyber",
                "href": "/msc-cyber",
                "open_href": "/msc-cyber",
            }
        )
        return rows

    ops._commissioning_rows = _with_msc
    try:
        owner = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
        ids = _ids(owner)
        check("fixture sees asset seed", "CMQ-MSC-ASSETS" in ids)
        check("fixture sees cyber seed", "CMQ-MSC-CYBER" in ids)
        check("fixture count matches", owner.get("count") == len(owner.get("items") or []))
        check("fixture still excludes amg", "CMQ-AMG-DAY" not in ids)
        check("fixture still excludes intg", "CMQ-INTEGRATION-HEALTH" not in ids)
        check("fixture still excludes sale", "CMQ-SALE-EVIDENCE" not in ids)
        check(
            "fixture next preferred",
            (owner.get("next_action") or {}).get("code") == "needs_you_connective"
            and (owner.get("next_action") or {}).get("preferred_over_pack") is True
            and (owner.get("next_action") or {}).get("object_id") == "CMQ-MSC-ASSETS",
            str((owner.get("next_action") or {}).get("object_id")),
        )
        check("fixture mfa not live", owner.get("live_mfa") is False and owner.get("secret_mint") is False)
        detail = ops.connective_item_detail("CMQ-MSC-ASSETS", verified_person_id="PERS-MATT")
        check(
            "seed detail reuses needs-you",
            detail.get("reuse_needs_you_depth") is True
            and (detail.get("handoff") or {}).get("duplicate_mutate_surface") is False
            and detail.get("live_mfa") is False
            and detail.get("legal_hold") is False,
        )
        desk = {
            "ok": True,
            "primary_next": {
                "code": "open_msc_assets",
                "label": "Open MSC Asset Register desk",
                "href": "/msc-assets",
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
            (desk.get("pack_next_action") or {}).get("code") == "open_msc_assets",
        )
    finally:
        ops._commissioning_rows = real

    real_loop = ops._msc_loop_rows
    ops._msc_loop_rows = lambda **_k: [dict(LOOP_ROW)]
    try:
        loop = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
        ids = _ids(loop)
        check("msc loop sees recorded attention", "asset_register" in ids)
        check(
            "msc loop count",
            (loop.get("by_kind") or {}).get("msc_loop", 0) >= 1,
            str(loop.get("by_kind")),
        )
        row = next(i for i in (loop.get("items") or []) if i.get("object_id") == "asset_register")
        check("msc loop not live mfa", row.get("live_mfa") is False and row.get("compliance_done") is False)
        check("msc loop no legal hold", row.get("legal_hold") is False and row.get("secret_mint") is False)
        detail = ops.connective_item_detail(
            "asset_register", verified_person_id="PERS-MATT"
        )
        check(
            "msc loop detail handoff",
            detail.get("reuse_needs_you_depth") is False
            and (detail.get("handoff") or {}).get("read_only_here") is True
            and (detail.get("handoff") or {}).get("reuse_msc_loop") is True,
        )
        try:
            ops.acknowledge_handoff(
                "asset_register",
                verified_person_id="PERS-MATT",
                note="no second surface",
            )
            check("msc loop ack 405", False)
        except ops.ConnectiveError as exc:
            check("msc loop ack handoff_only", exc.code == "handoff_only" and exc.http_status == 405)
    finally:
        ops._msc_loop_rows = real_loop


def test_empty_desk() -> None:
    real_rows = ops._msc_candidates
    ops._msc_candidates = lambda **_k: []
    try:
        quiet = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
        check("empty honesty", quiet.get("empty") is True and quiet.get("count") == 0)
        check("empty next null", quiet.get("next_action") is None)
        check("empty not invented", quiet.get("invented") is False and quiet.get("invented_count") is False)
        check("empty message", "EMPTY" in str(quiet.get("empty_message") or ""))
        desk = {
            "ok": True,
            "primary_next": {
                "code": "open_msc_assets",
                "label": "Open MSC Asset Register desk",
                "href": "/msc-assets",
            },
        }
        ops._attach_needs_you_connective(desk, person_id="PERS-MATT")
        check(
            "empty desk keeps pack",
            (desk.get("primary_next") or {}).get("code") == "open_msc_assets"
            and (desk.get("next_action") or {}).get("code") == "open_msc_assets"
            and (desk.get("needs_you_connective") or {}).get("count") == 0,
        )
    finally:
        ops._msc_candidates = real_rows


def test_acknowledge_temp_state() -> None:
    real = ops._is_msc_scoped

    def _wider(item: dict) -> bool:
        if str(item.get("object_id") or "") == "CMQ-AMG-DAY":
            item["business"] = "MSC"
            item["capability"] = "CAP-MSC-01"
            item["surface"] = "msc_assets"
            item["domain"] = "D-MSC"
            item["person_to_test"] = "Matt"
            item["who"] = "Matt"
            item["audience"] = "NEEDS_MATT"
            item["href"] = "/msc-assets"
            item["open_href"] = "/msc-assets"
            return True
        return real(item)

    ops._is_msc_scoped = _wider
    try:
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state.json"
            events = Path(td) / "events.jsonl"
            ack = ops.acknowledge_handoff(
                "CMQ-AMG-DAY",
                verified_person_id="PERS-MATT",
                note="msc connective prove",
                state_path=state,
                events_path=events,
            )
            check("ack recorded", ack.get("recorded") is True and ack.get("commissioned") is False)
            check("ack no human done", ack.get("human_done") is False and ack.get("devi_retest") == "parked")
            check("ack no money", ack.get("money") is None and ack.get("bzg_compose") is False)
            check("ack no live mfa", ack.get("live_mfa") is False and ack.get("secret_mint") is False)
            check("ack no legal hold", ack.get("legal_hold") is False and ack.get("compliance_done") is False)
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
        ops._is_msc_scoped = real


def test_crs_and_files() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("denominator 77", len(ledger) == 77, str(len(ledger)))
    for cap, expect in CAP_EXPECT.items():
        got = ledger.get(cap, [None])[0]
        check(f"ledger {cap}", got == expect, str(got))
    for cr in ops.MSC_TARGET_CRS:
        check(f"msc cr {cr} open", _cr(cr) == "OPEN", _cr(cr))
    for cr in nye.TARGET_CRS:
        check(f"progress cr {cr} open", _cr(cr) == "OPEN", _cr(cr))
    text = HTML.read_text(encoding="utf-8")
    check("html connective", "Needs-You connective" in text and 'id="needs-you-connective"' in text)
    check("html still cluster bound", "beta-core-safe" in text)
    check("html no orphan", "msc-ops-needs-you.html" not in text)
    source = (SCRIPTS / "core" / "msc_ops_needs_you_connective.py").read_text(encoding="utf-8")
    check("source schema id", "wolf.msc-ops-needs-you-connective.v1" in source)
    check("source not sale strip", "wolf.sale-ops-needs-you-connective.v1" not in source)
    check("source not crm strip", "wolf.crm-ops-needs-you-connective.v1" not in source)
    check("source not ggv strip", "wolf.ggv-ops-needs-you-connective.v1" not in source)
    check("source not bzg strip", "wolf.bzg-ops-needs-you-connective.v1" not in source)
    check("source not intg strip", "wolf.intg-ops-needs-you-connective.v1" not in source)
    report = health.build_report()
    retired = {str(r.get("source_id")): r for r in (report.get("retired") or [])}
    check("clickup retired", (retired.get("clickup") or {}).get("status") == "RETIRED")
    check("telegram retired", (retired.get("telegram") or {}).get("status") == "RETIRED")
    desk = msc.build_desk(verified_person_id="PERS-MATT")
    check("desk has strip", isinstance(desk.get("needs_you_connective"), dict))
    check(
        "desk strip count",
        (desk.get("needs_you_connective") or {}).get("count")
        == len((desk.get("needs_you_connective") or {}).get("items") or []),
    )
    check("desk no live mfa", desk.get("mfa_status") is None and desk.get("legal_hold") is None)
    check("desk access not mutated", desk.get("access_mutated") is False)
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
            "/api/msc/mgmt-cluster/needs-you",
            "/api/msc/mgmt-cluster/needs-you/items/CMQ-AMG-DAY",
        ):
            st, payload = call("GET", path, None)
            check(
                f"anon 403 {path.rsplit('/', 1)[-1][:24]}",
                st == 403 and (payload or {}).get("error") == "missing_subject",
                f"{st} {(payload or {}).get('error') if isinstance(payload, dict) else ''}",
            )
        st, payload = call("GET", "/api/msc/mgmt-cluster/needs-you", MATT)
        check("owner needs-you 200", st == 200 and payload.get("ok") is True, str(st))
        check("owner http bound", payload.get("bound") == ops.CONNECTIVE_BOUND, str(payload.get("bound")))
        check("owner http count", payload.get("count") == len(payload.get("items") or []))
        check("owner http staff_ready", payload.get("staff_ready") is False)
        check("owner http money", payload.get("money") is None and payload.get("bzg_compose") is False)
        check("owner http mfa not live", payload.get("live_mfa") is False and payload.get("secret_mint") is False)
        check("owner http no legal hold", payload.get("legal_hold") is False and payload.get("compliance_done") is False)
        check("owner http excludes amg", "CMQ-AMG-DAY" not in _ids(payload))
        check("owner http excludes ggv", "CMQ-AMANDA-GGV" not in _ids(payload))
        check("owner http excludes bzg", "CMQ-DEVI-UMA-MOBILE" not in _ids(payload))
        check("owner http excludes intg", "CMQ-INTEGRATION-HEALTH" not in _ids(payload))
        check("owner http devi parked", payload.get("devi_retest") == "parked")
        if payload.get("count") == 0:
            check("owner http empty next", payload.get("next_action") is None and payload.get("empty") is True)
        else:
            check("owner http next preferred", (payload.get("next_action") or {}).get("preferred_over_pack") is True)

        st, payload = call("GET", "/api/msc/mgmt-cluster", MATT)
        check("desk 200", st == 200 and isinstance(payload.get("needs_you_connective"), dict), str(st))
        check(
            "desk strip count",
            (payload.get("needs_you_connective") or {}).get("count")
            == len((payload.get("needs_you_connective") or {}).get("items") or []),
        )
        check("desk cluster bound", payload.get("bound") == "beta-core-safe", str(payload.get("bound")))

        st, payload = call("GET", "/api/msc/mgmt-cluster/needs-you/items/CMQ-AMG-DAY", MATT)
        check("foreign http 404", st == 404 and (payload or {}).get("error") == "not_found", str(st))
        st, _ = call("GET", "/api/msc/mgmt-cluster/needs-you", OUTSIDER)
        check("outsider 403", st == 403, str(st))
        st, payload = call("GET", "/api/msc/mgmt-cluster/needs-you", HAIKAL)
        check("haikal http 403", st == 403 and (payload or {}).get("error") == "forbidden", str(st))
        st, _ = call("GET", "/api/msc/mgmt-cluster/needs-you", MISA)
        check("misa http 403", st == 403, str(st))
        st, _ = call("GET", "/api/msc/mgmt-cluster/needs-you", DEVI)
        check("devi http 403", st == 403, str(st))
        st, payload = call("GET", "/api/msc/mgmt-cluster/needs-you", AMANDA)
        check("amanda http 403", st == 403 and (payload or {}).get("error") == "forbidden", str(payload)[:120])

        st, page = call("GET", "/msc-mgmt-cluster", MATT)
        page_bytes = page if isinstance(page, bytes) else (page.encode() if isinstance(page, str) else b"")
        check(
            "owner page soft-lands without copying strip",
            st == 200 and b"needs-you-connective" not in page_bytes and b"MSC / asset / posture" not in page_bytes,
            str(st),
        )
        check(
            "desk html file has connective",
            b"needs-you-connective" in HTML.read_bytes(),
        )
        st, _ = call("GET", "/msc-mgmt-cluster", None)
        check("anon page 403", st == 403, str(st))

        st, payload = call("POST", "/api/msc/mgmt-cluster/needs-you/items/CMQ-AMG-DAY/acknowledge", MATT, {"note": "no"})
        check("ack missing msc row 404", st == 404 and (payload or {}).get("error") == "not_found", str(st))
        st, payload = call("POST", "/api/msc/mgmt-cluster/access", MATT, {})
        check(
            "cluster access still refused",
            st == 405 and (payload or {}).get("error") == "cloudflare_refused",
            str(payload)[:160],
        )
        for path, code in (
            ("/api/msc/mgmt-cluster/haikal-done", "haikal_done_refused"),
            ("/api/msc/mgmt-cluster/devi-done", "devi_done_refused"),
            ("/api/msc/mgmt-cluster/live-mfa", "live_mfa_refused"),
            ("/api/msc/mgmt-cluster/compliance-done", "compliance_done_refused"),
            ("/api/msc/mgmt-cluster/secret-mint", "secret_mint_refused"),
            ("/api/msc/mgmt-cluster/access-include", "access_include_refused"),
            ("/api/msc/mgmt-cluster/needs-you/legal-hold", "legal_hold_refused"),
            ("/api/msc/mgmt-cluster/needs-you/proven", "proven_refused"),
            ("/api/msc/mgmt-cluster/needs-you/ready", "ready_refused"),
            ("/api/msc/mgmt-cluster/needs-you/money", "money_refused"),
            ("/api/msc/mgmt-cluster/needs-you/bzg-compose", "bzg_compose_refused"),
            ("/api/msc/mgmt-cluster/needs-you/staff-ready", "staff_ready_refused"),
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
    test_fixture_prefers_and_msc_loop()
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
