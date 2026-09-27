#!/usr/bin/env python3
"""Sale Ops × Needs-You connective — Sale/Evidence/Buyer projection on the Sale desk."""
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

from core import owner_progress_needs_you_depth as nye  # noqa: E402
from core import request_auth as ra  # noqa: E402
from core import sale_mgmt_cluster as sale  # noqa: E402
from core import sale_ops_needs_you_connective as ops  # noqa: E402
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
HTML = ROOT / "dashboards" / "sale-mgmt-cluster.html"
EVIDENCE_HTML = ROOT / "dashboards" / "sale-evidence-pack.html"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
OUT_OF_SALE = (
    "CMQ-AMG-DAY",
    "CMQ-AMANDA-GGV",
    "CMQ-NAS-HAIKAL",
    "CMQ-SMART-UPLOAD-RETEST",
    "CMQ-GLOBAL-NAV-OWNER",
    "CMQ-PROGRESS-NEEDS-YOU",
    "CMQ-INTEGRATION-HEALTH",
    "CMQ-DEVI-UMA-MOBILE",
)
CAP_EXPECT = {
    "CAP-SALE-01": "SPECIFIED",
    "CAP-SALE-02": "SPECIFIED",
    "CAP-SALE-03": "SPECIFIED",
    "CAP-SALE-04": "SPECIFIED",
}
SALE_SEED = {
    "object_id": "CMQ-SALE-EVIDENCE",
    "kind": "morning_seed",
    "title": "Sale evidence morning seed",
    "who": "Matt",
    "audience": "NEEDS_MATT",
    "person_to_test": "Matt",
    "priority": "P0",
    "business": "SALE",
    "domain": "D-SALE",
    "capability": "CAP-SALE-01",
    "surface": "sale_evidence",
    "href": "/sale-evidence-pack",
    "open_href": "/sale-evidence-pack",
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


def _seed_operator(path: Path, *, object_id: str, kind: str, last_kind: str, note: str, nxt: str | None, disposition: str = "open") -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(sale.OPERATOR_SCHEMA_SQL)
        conn.execute(
            """
            INSERT INTO sale_operator_state (
              object_id, module_id, kind, disposition, note, next_action,
              last_kind, updated_by, updated_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                object_id,
                object_id,
                kind,
                disposition,
                note,
                nxt,
                last_kind,
                "PERS-MATT",
                "2026-09-23T00:00:00Z",
                "2026-09-23T00:00:00Z",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_honesty() -> None:
    check("schema", ops.CONNECTIVE_SCHEMA_ID == "wolf.sale-ops-needs-you-connective.v1")
    check("bound", ops.CONNECTIVE_BOUND == "beta-connective-safe")
    check("claim id", ops.CONNECTIVE_CLAIM_ID == "bf-sale-ops-needs-you-connective-20260923")
    check("not crm schema", "crm-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("not ggv schema", "ggv-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("not bzg schema", "bzg-ops-needs-you" not in ops.CONNECTIVE_SCHEMA_ID)
    check("shell flag", wolf_shell.honesty_flags().get("sale_ops_needs_you_connective") is True)
    for name, fn, code in (
        ("staff_ready", ops.refuse_staff_ready, "staff_ready_refused"),
        ("haikal", ops.refuse_haikal_done, "haikal_done_refused"),
        ("devi", ops.refuse_devi_done, "devi_done_refused"),
        ("buyer live", ops.refuse_buyer_live, "buyer_live_refused"),
        ("export", ops.refuse_controlled_export, "controlled_export_refused"),
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
        ops.connective_refuse_code("/api/sale/mgmt-cluster/needs-you/staff-ready") == "staff_ready"
        and ops.connective_refuse_code("/api/sale/mgmt-cluster/haikal-done") == "haikal_done"
        and ops.connective_refuse_code("/api/sale/mgmt-cluster/devi-done") == "devi_done"
        and ops.connective_refuse_code("/api/sale/mgmt-cluster/buyer-live") == "buyer_live"
        and ops.connective_refuse_code("/api/sale/mgmt-cluster/controlled-export") == "controlled_export"
        and ops.connective_refuse_code("/api/sale/mgmt-cluster/needs-you/proven") == "proven"
        and ops.connective_refuse_code("/api/sale/mgmt-cluster/needs-you/ready") == "ready"
        and ops.connective_refuse_code("/api/sale/mgmt-cluster/needs-you/money") == "money"
        and ops.connective_refuse_code("/api/sale/mgmt-cluster/needs-you/bzg-compose") == "bzg_compose"
        and ops.connective_refuse_code("/api/sale/mgmt-cluster") is None,
    )


def test_scope_filter() -> None:
    check("ggv amanda seed out", ops._is_sale_scoped({
        "object_id": "CMQ-AMANDA-GGV",
        "business": "GGV",
        "capability": "CAP-GGV-04",
        "surface": "ggv_ops",
        "kind": "morning_seed",
    }) is False)
    check("bzg seed out", ops._is_sale_scoped({
        "object_id": "CMQ-DEVI-UMA-MOBILE",
        "business": "BZG",
        "capability": "CAP-BZG-03",
        "kind": "morning_seed",
    }) is False)
    check("amg seed out", ops._is_sale_scoped({
        "object_id": "CMQ-AMG-DAY",
        "business": "AMG",
        "capability": "CAP-AMG-04",
        "surface": "amg_ops",
        "kind": "morning_seed",
    }) is False)
    check("crm seed out", ops._is_sale_scoped({
        "object_id": "CMQ-CRM-AMANDA",
        "business": "CRM",
        "capability": "CAP-CRM-01",
        "surface": "lead_spine",
        "href": "/lead-spine",
        "kind": "morning_seed",
    }) is False)
    check("nas seed out", ops._is_sale_scoped({
        "object_id": "CMQ-NAS-HAIKAL",
        "business": "GGV",
        "surface": "nas_library",
        "kind": "morning_seed",
    }) is False)
    check("sale cap in", ops._is_sale_scoped({
        "object_id": "CMQ-SALE-EVIDENCE",
        "business": "SALE",
        "capability": "CAP-SALE-01",
        "surface": "sale_evidence",
        "kind": "morning_seed",
        "href": "/sale-evidence-pack",
    }) is True)
    check("buyer cap in", ops._is_sale_scoped({
        "object_id": "CMQ-SALE-BUYER",
        "business": "SALE",
        "capability": "CAP-SALE-03",
        "surface": "buyer_mode",
        "href": "/buyer-mode",
        "kind": "needs_you",
    }) is True)
    check("sale loop in", ops._is_sale_scoped({
        "kind": "sale_loop",
        "object_id": "sale_evidence_pack",
        "business": "SALE",
    }) is True)
    check("lead loop out", ops._is_sale_scoped({
        "kind": "lead_loop",
        "brand_id": "habitat",
        "object_id": "LEAD-x",
        "business": "CRM",
    }) is False)
    owner_only = dict(SALE_SEED)
    check(
        "non-owner misses owner-only",
        ops._in_scope_for_seat(owner_only, {"person_id": "PERS-AMANDA", "seat": "crm_lead"}) is False,
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
    for oid in OUT_OF_SALE:
        check(f"owner excludes {oid}", oid not in _ids(owner))
    check("owner money empty", owner.get("money") is None)
    check("owner no compose", owner.get("bzg_compose") is False)
    check("owner buyer not live", owner.get("buyer_live") is False and owner.get("buyer_dataroom_live") is False)
    check("owner no export", owner.get("controlled_export") is False and owner.get("controlled_export_send") is False)
    check("owner staff_ready false", owner.get("staff_ready") is False and owner.get("proven") is False)
    check("owner ready false", owner.get("ready") is False)
    check("owner haikal flag", owner.get("haikal_human") == "not_started" and owner.get("devi_retest") == "parked")
    check("owner sees full", (owner.get("seat") or {}).get("sees_full_sale") is True)
    check("owner commission not invented", (owner.get("seat") or {}).get("invented_commission") is False)
    check("strips not copied", owner.get("crm_strip_duplicated") is False and owner.get("ggv_strip_duplicated") is False and owner.get("bzg_strip_duplicated") is False)
    caps = (owner.get("caps") or {}).get("caps") or {}
    for cap, expect in CAP_EXPECT.items():
        check(f"{cap} {expect}", caps.get(cap) == expect, str(caps.get(cap)))
    if not (ROOT / "catalog" / "sale_mgmt_operator.sqlite").is_file():
        check("live sale loop empty", by_kind.get("sale_loop") == 0, str(by_kind))
        check("live morning empty", by_kind.get("morning_seed") == 0, str(by_kind))
        check("live empty honesty", owner.get("empty") is True and owner.get("count") == 0)
        check("live next null", owner.get("next_action") is None)
    else:
        check("live sale loop honest", by_kind.get("sale_loop", 0) == sum(1 for i in owner.get("items") or [] if i.get("kind") == "sale_loop"))
        check("live items not buyer live", all(i.get("buyer_live") is False for i in (owner.get("items") or [])))
        check("live count honest", owner.get("count") == len(owner.get("items") or []))
        check("live next or empty", owner.get("empty") is True or (owner.get("next_action") or {}).get("preferred_over_pack") is True)

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
        ops.connective_item_detail("CMQ-SALE-EVIDENCE", verified_person_id="PERS-HAIKAL")
        check("haikal detail forbidden", False)
    except ops.ConnectiveError as exc:
        check("haikal detail forbidden", exc.code == "forbidden")


def test_fixture_prefers_and_sale_loop() -> None:
    real = ops._commissioning_rows

    def _with_sale(*, state_path=None):
        rows = real(state_path=state_path)
        rows.append(dict(SALE_SEED))
        rows.append(
            {
                "object_id": "CMQ-SALE-BUYER",
                "kind": "needs_you",
                "title": "Buyer mode needs a look",
                "who": "Matt",
                "audience": "NEEDS_MATT",
                "priority": "P1",
                "business": "SALE",
                "capability": "CAP-SALE-02",
                "surface": "buyer_dataroom",
                "href": "/buyer-dataroom",
                "open_href": "/buyer-dataroom",
            }
        )
        return rows

    ops._commissioning_rows = _with_sale
    try:
        owner = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
        ids = _ids(owner)
        check("fixture sees evidence seed", "CMQ-SALE-EVIDENCE" in ids)
        check("fixture sees buyer seed", "CMQ-SALE-BUYER" in ids)
        check("fixture count matches", owner.get("count") == len(owner.get("items") or []))
        check("fixture still excludes amg", "CMQ-AMG-DAY" not in ids)
        check(
            "fixture next preferred",
            (owner.get("next_action") or {}).get("code") == "needs_you_connective"
            and (owner.get("next_action") or {}).get("preferred_over_pack") is True
            and (owner.get("next_action") or {}).get("object_id") == "CMQ-SALE-EVIDENCE",
            str((owner.get("next_action") or {}).get("object_id")),
        )
        check("fixture buyer not live", owner.get("buyer_dataroom_live") is False and owner.get("controlled_export") is False)
        detail = ops.connective_item_detail("CMQ-SALE-EVIDENCE", verified_person_id="PERS-MATT")
        check(
            "seed detail reuses needs-you",
            detail.get("reuse_needs_you_depth") is True
            and (detail.get("handoff") or {}).get("duplicate_mutate_surface") is False
            and detail.get("buyer_live") is False,
        )
        desk = {
            "ok": True,
            "primary_next": {
                "code": "open_sale_evidence_pack",
                "label": "Open Sale Evidence Pack desk",
                "href": "/sale-evidence-pack",
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
            (desk.get("pack_next_action") or {}).get("href") == "/sale-evidence-pack",
        )
    finally:
        ops._commissioning_rows = real

    with tempfile.TemporaryDirectory() as td:
        op = Path(td) / "sale_op.sqlite"
        _seed_operator(
            op,
            object_id="sale_evidence_pack",
            kind="evidence",
            last_kind="note",
            note="evidence still needs a next",
            nxt=None,
        )
        _seed_operator_extra = False
        conn = sqlite3.connect(op)
        try:
            conn.execute(
                """
                INSERT INTO sale_operator_state (
                  object_id, module_id, kind, disposition, note, next_action,
                  last_kind, updated_by, updated_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "sale_buyer_mode",
                    "sale_buyer_mode",
                    "buyer_mode",
                    "open",
                    "named next only",
                    "Open buyer mode desk",
                    "next_action",
                    "PERS-MATT",
                    "2026-09-23T00:00:00Z",
                    "2026-09-23T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO sale_operator_state (
                  object_id, module_id, kind, disposition, note, next_action,
                  last_kind, updated_by, updated_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "sale_attack_audit",
                    "sale_attack_audit",
                    "attack",
                    "dismissed",
                    "noise",
                    None,
                    "dismiss_noise",
                    "PERS-MATT",
                    "2026-09-23T00:00:00Z",
                    "2026-09-23T00:00:00Z",
                ),
            )
            conn.commit()
            _seed_operator_extra = True
        finally:
            conn.close()
        check("operator fixture wrote", _seed_operator_extra)
        loop = ops.needs_you_connective_strip(verified_person_id="PERS-MATT", operator_db=op)
        ids = _ids(loop)
        check("sale loop sees evidence attention", "sale_evidence_pack" in ids)
        check("sale loop skips quiet buyer next", "sale_buyer_mode" not in ids)
        check("sale loop skips dismissed attack", "sale_attack_audit" not in ids)
        check("sale loop count", loop.get("count") == 1 and (loop.get("by_kind") or {}).get("sale_loop") == 1, str(loop.get("by_kind")))
        row = (loop.get("items") or [{}])[0]
        check("sale loop not export", row.get("controlled_export") is False and row.get("buyer_live") is False)
        check(
            "sale loop next",
            (loop.get("next_action") or {}).get("kind") == "sale_loop"
            and (loop.get("next_action") or {}).get("object_id") == "sale_evidence_pack",
        )
        detail = ops.connective_item_detail(
            "sale_evidence_pack", verified_person_id="PERS-MATT", operator_db=op
        )
        check(
            "sale loop detail handoff",
            detail.get("reuse_needs_you_depth") is False
            and (detail.get("handoff") or {}).get("read_only_here") is True
            and (detail.get("handoff") or {}).get("reuse_sale_loop") is True,
        )
        try:
            ops.acknowledge_handoff(
                "sale_evidence_pack",
                verified_person_id="PERS-MATT",
                note="no second surface",
                operator_db=op,
            )
            check("sale loop ack 405", False)
        except ops.ConnectiveError as exc:
            check("sale loop ack handoff_only", exc.code == "handoff_only" and exc.http_status == 405)
        conn = sqlite3.connect(op)
        try:
            events = conn.execute("SELECT COUNT(*) FROM sale_operator_events").fetchone()[0]
        finally:
            conn.close()
        check("sale loop ack wrote no operator event", events == 0, str(events))


def test_empty_desk() -> None:
    real_rows = ops._sale_candidates
    ops._sale_candidates = lambda **_k: []
    try:
        quiet = ops.needs_you_connective_strip(verified_person_id="PERS-MATT")
        check("empty honesty", quiet.get("empty") is True and quiet.get("count") == 0)
        check("empty next null", quiet.get("next_action") is None)
        check("empty not invented", quiet.get("invented") is False and quiet.get("invented_count") is False)
        check("empty message", "EMPTY" in str(quiet.get("empty_message") or ""))
        desk = {
            "ok": True,
            "primary_next": {
                "code": "open_sale_evidence_pack",
                "label": "Open Sale Evidence Pack desk",
                "href": "/sale-evidence-pack",
            },
        }
        ops._attach_needs_you_connective(desk, person_id="PERS-MATT")
        check(
            "empty desk keeps pack",
            (desk.get("primary_next") or {}).get("code") == "open_sale_evidence_pack"
            and (desk.get("next_action") or {}).get("code") == "open_sale_evidence_pack"
            and (desk.get("needs_you_connective") or {}).get("count") == 0,
        )
    finally:
        ops._sale_candidates = real_rows


def test_acknowledge_temp_state() -> None:
    real = ops._is_sale_scoped

    def _wider(item: dict) -> bool:
        if str(item.get("object_id") or "") == "CMQ-AMG-DAY":
            item["business"] = "SALE"
            item["capability"] = "CAP-SALE-01"
            item["surface"] = "sale_evidence"
            item["domain"] = "D-SALE"
            item["person_to_test"] = "Matt"
            item["who"] = "Matt"
            item["audience"] = "NEEDS_MATT"
            item["href"] = "/sale-evidence-pack"
            item["open_href"] = "/sale-evidence-pack"
            return True
        return real(item)

    ops._is_sale_scoped = _wider
    try:
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state.json"
            events = Path(td) / "events.jsonl"
            ack = ops.acknowledge_handoff(
                "CMQ-AMG-DAY",
                verified_person_id="PERS-MATT",
                note="sale connective prove",
                state_path=state,
                events_path=events,
            )
            check("ack recorded", ack.get("recorded") is True and ack.get("commissioned") is False)
            check("ack no human done", ack.get("human_done") is False and ack.get("devi_retest") == "parked")
            check("ack no money", ack.get("money") is None and ack.get("bzg_compose") is False)
            check("ack no buyer live", ack.get("buyer_live") is False and ack.get("controlled_export") is False)
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
            try:
                ops.acknowledge_handoff(
                    "CMQ-AMG-DAY",
                    verified_person_id="PERS-AMANDA",
                    note="no",
                    state_path=state,
                    events_path=events,
                )
                check("ack amanda forbidden", False)
            except ops.ConnectiveError as exc:
                check("ack amanda forbidden", exc.code == "forbidden")
    finally:
        ops._is_sale_scoped = real


def test_crs_and_files() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    for cap, expect in CAP_EXPECT.items():
        check(f"ledger {cap}", ledger.get(cap, [None])[0] == expect, str(ledger.get(cap, [None])[0]))
    check("ledger denom", len(ledger) == 77, str(len(ledger)))
    for cr in ops.SALE_TARGET_CRS:
        check(f"sale cr open {cr[:12]}", _cr(cr) == "OPEN", _cr(cr))
    for cr in nye.TARGET_CRS:
        check(f"progress cr open {cr[:12]}", _cr(cr) == "OPEN", _cr(cr))
    text = HTML.read_text(encoding="utf-8")
    check("html connective", "Needs-You connective" in text and 'id="needs-you-connective"' in text)
    check("html empty honesty", "EMPTY" in text and "staff_ready" in text)
    check("html devi parked", "Devi retest stays parked" in text)
    check("html no export", "controlled export" in text and "buyer data room" in text)
    evidence = EVIDENCE_HTML.read_text(encoding="utf-8")
    check("evidence html connective", "Needs-You connective" in evidence and 'id="needs-you-connective"' in evidence)
    check("no orphan dashboard", not (ROOT / "dashboards" / "sale-ops-needs-you.html").exists())
    source = (SCRIPTS / "core" / "sale_ops_needs_you_connective.py").read_text(encoding="utf-8")
    check("source schema id", "wolf.sale-ops-needs-you-connective.v1" in source)
    check("source not crm strip", "wolf.crm-ops-needs-you-connective.v1" not in source)
    check("source not ggv strip", "wolf.ggv-ops-needs-you-connective.v1" not in source)
    check("source not bzg strip", "wolf.bzg-ops-needs-you-connective.v1" not in source)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("serve route", "/api/sale/mgmt-cluster/needs-you" in serve)
    live = sale.build_desk(verified_person_id="PERS-MATT")
    check("cluster desk has strip", isinstance(live.get("needs_you_connective"), dict))
    check(
        "cluster desk count matches",
        (live.get("needs_you_connective") or {}).get("count")
        == len((live.get("needs_you_connective") or {}).get("items") or []),
    )
    if (live.get("needs_you_connective") or {}).get("count") == 0:
        check(
            "cluster desk keeps module next",
            (live.get("primary_next") or {}).get("code") != "needs_you_connective",
            str((live.get("primary_next") or {}).get("code")),
        )
    else:
        check(
            "cluster desk prefers connective",
            (live.get("primary_next") or {}).get("code") == "needs_you_connective",
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
            "/api/sale/mgmt-cluster/needs-you",
            "/api/sale/mgmt-cluster/needs-you/items/CMQ-AMG-DAY",
        ):
            st, payload = call("GET", path, None)
            check(
                f"anon 403 {path.rsplit('/', 1)[-1][:24]}",
                st == 403 and (payload or {}).get("error") == "missing_subject",
                f"{st} {(payload or {}).get('error') if isinstance(payload, dict) else ''}",
            )
        st, payload = call("GET", "/api/sale/mgmt-cluster/needs-you", MATT)
        check("owner needs-you 200", st == 200 and payload.get("ok") is True, str(st))
        check("owner http bound", payload.get("bound") == ops.CONNECTIVE_BOUND, str(payload.get("bound")))
        check("owner http count", payload.get("count") == len(payload.get("items") or []))
        check("owner http staff_ready", payload.get("staff_ready") is False)
        check("owner http money", payload.get("money") is None and payload.get("bzg_compose") is False)
        check("owner http buyer not live", payload.get("buyer_live") is False and payload.get("controlled_export") is False)
        check("owner http excludes amg", "CMQ-AMG-DAY" not in _ids(payload))
        check("owner http excludes ggv", "CMQ-AMANDA-GGV" not in _ids(payload))
        check("owner http excludes bzg", "CMQ-DEVI-UMA-MOBILE" not in _ids(payload))
        check("owner http devi parked", payload.get("devi_retest") == "parked")
        if payload.get("count") == 0:
            check("owner http empty next", payload.get("next_action") is None and payload.get("empty") is True)
        else:
            check("owner http next preferred", (payload.get("next_action") or {}).get("preferred_over_pack") is True)

        st, payload = call("GET", "/api/sale/mgmt-cluster", MATT)
        check("desk 200", st == 200 and isinstance(payload.get("needs_you_connective"), dict), str(st))
        check(
            "desk strip count",
            (payload.get("needs_you_connective") or {}).get("count")
            == len((payload.get("needs_you_connective") or {}).get("items") or []),
        )
        st, payload = call("GET", "/api/sale-evidence-pack", MATT)
        check("evidence desk strip", st == 200 and isinstance(payload.get("needs_you_connective"), dict), str(st))
        check("evidence no buyer export", payload.get("buyer_export") is False and payload.get("vdr_export") is False)

        st, payload = call("GET", "/api/sale/mgmt-cluster/needs-you/items/CMQ-AMG-DAY", MATT)
        check("foreign http 404", st == 404 and (payload or {}).get("error") == "not_found", str(st))
        st, _ = call("GET", "/api/sale/mgmt-cluster/needs-you", OUTSIDER)
        check("outsider 403", st == 403, str(st))
        st, payload = call("GET", "/api/sale/mgmt-cluster/needs-you", HAIKAL)
        check("haikal http 403", st == 403 and (payload or {}).get("error") == "forbidden", str(st))
        st, _ = call("GET", "/api/sale/mgmt-cluster/needs-you", MISA)
        check("misa http 403", st == 403, str(st))
        st, _ = call("GET", "/api/sale/mgmt-cluster/needs-you", DEVI)
        check("devi http 403", st == 403, str(st))
        st, payload = call("GET", "/api/sale/mgmt-cluster/needs-you", AMANDA)
        check("amanda http 403", st == 403 and (payload or {}).get("error") == "forbidden", str(payload)[:120])

        st, page = call("GET", "/sale-mgmt-cluster", MATT)
        check(
            "owner page connective",
            st == 200 and isinstance(page, (bytes, str)) and b"needs-you-connective" in (page if isinstance(page, bytes) else page.encode()),
            str(st),
        )
        st, _ = call("GET", "/sale-mgmt-cluster", None)
        check("anon page 403", st == 403, str(st))

        st, payload = call("POST", "/api/sale/mgmt-cluster/needs-you/items/CMQ-AMG-DAY/acknowledge", MATT, {"note": "no"})
        check("ack missing sale row 404", st == 404 and (payload or {}).get("error") == "not_found", str(st))
        st, payload = call("POST", "/api/sale/mgmt-cluster/haikal-done", MATT, {})
        check("haikal-done refuse", st == 405 and payload.get("error") == "haikal_done_refused", str(payload)[:160])
        st, payload = call("POST", "/api/sale/mgmt-cluster/devi-done", MATT, {})
        check("devi-done refuse", st == 405 and payload.get("error") == "devi_done_refused", str(payload)[:160])
        st, payload = call("POST", "/api/sale/mgmt-cluster/buyer-live", MATT, {})
        check("buyer-live refuse", st == 405 and payload.get("error") == "buyer_live_refused", str(payload)[:160])
        st, payload = call("POST", "/api/sale/mgmt-cluster/controlled-export", MATT, {})
        check("export refuse", st == 405 and payload.get("error") == "controlled_export_refused", str(payload)[:160])
        st, payload = call("POST", "/api/sale/mgmt-cluster/needs-you/proven", MATT, {})
        check("proven refuse", st == 405 and payload.get("error") == "proven_refused", str(payload)[:120])
        st, payload = call("POST", "/api/sale/mgmt-cluster/needs-you/ready", MATT, {})
        check("ready refuse", st == 405 and payload.get("error") == "ready_refused", str(payload)[:120])
        st, payload = call("POST", "/api/sale/mgmt-cluster/needs-you/money", MATT, {})
        check("money route refuse", st == 405 and payload.get("error") == "money_refused", str(payload)[:120])
        st, payload = call("POST", "/api/sale/mgmt-cluster/needs-you/bzg-compose", MATT, {})
        check("compose route refuse", st == 405 and payload.get("error") == "bzg_compose_refused", str(payload)[:120])
        st, payload = call("POST", "/api/sale/mgmt-cluster/needs-you/staff-ready", MATT, {})
        check("staff-ready refuse", st == 405 and payload.get("error") == "staff_ready_refused", str(payload)[:120])
    finally:
        httpd.shutdown()


def main() -> None:
    test_honesty()
    test_scope_filter()
    test_live_projection()
    test_fixture_prefers_and_sale_loop()
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
