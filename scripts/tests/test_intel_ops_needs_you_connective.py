#!/usr/bin/env python3
"""Intel Ops × Needs-You connective — Beta :8788 only.

Derived Intel-scoped commissioning / intel connective / learning-policy
rows on the existing Intel Ops Pack. No invent staff_ready / PROVEN /
READY / Haikal done / Devi done. No auto-promote. No false-resolve.
"""
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

from core import intel_ops_pack as pack  # noqa: E402
from core import owner_commissioning_queue as ocq  # noqa: E402
from core import owner_progress_needs_you_depth as nye  # noqa: E402
from core import request_auth as ra  # noqa: E402
from core import wolf_shell  # noqa: E402

PASS = 0
FAIL = 0

CATALOG = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HTML = ROOT / "dashboards" / "intel-ops-pack.html"
CR_05 = "CR-be51980bd1194448"
CR_AU = "CR-dca0ad62e1b0032e"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
FOREIGN = (
    "CMQ-AMG-DAY",
    "CMQ-AMANDA-GGV",
    "CMQ-NAS-HAIKAL",
    "CMQ-DEVI-UMA-MOBILE",
    "CMQ-GLOBAL-NAV-OWNER",
    "CMQ-PROGRESS-NEEDS-YOU",
    "CMQ-SMART-UPLOAD-RETEST",
    "CMQ-INTEGRATION-HEALTH",
)
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
FIXTURE = "PERS-INTEL-FIXTURE"
_REAL_SEAT = pack.seat_for
_REAL_SEED = ocq.seed_templates


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _cr(cr_id: str) -> str | None:
    conn = sqlite3.connect(str(CATALOG))
    try:
        row = conn.execute(
            "SELECT state FROM wolf_completion_items WHERE id=?",
            (cr_id,),
        ).fetchone()
    finally:
        conn.close()
    return None if row is None else str(row[0])


def _ids(payload: dict) -> set[str]:
    return {str(row.get("object_id") or "") for row in (payload.get("items") or [])}


def _intel_templates() -> list[dict]:
    base = _REAL_SEED()
    extra = [
        {
            "id": "CMQ-INTEL-OWNER",
            "task": "Intel Owner commissioning seed",
            "priority": "P0",
            "business": "INTEL",
            "person_to_test": "Matt",
            "audience": "NEEDS_MATT",
            "open_href": "/intel-ops-pack",
            "do_this": ["Open Intel home."],
            "check": "Owner sees the Intel-scoped seed. proven stays false.",
            "capability": "CAP-INTEL-05",
            "criterion": "intel_owner_seed",
            "surface": "intel_ops",
            "route": "/intel-ops-pack",
            "source": "test-fixture",
            "confidence": "DERIVED",
            "skip_if_known_broken": False,
        },
        {
            "id": "CMQ-INTEL-FIXTURE",
            "task": "Intel Fixture seat commissioning seed",
            "priority": "P1",
            "business": "INTEL",
            "person_to_test": "Intel Fixture",
            "audience": "NEEDS_STAFF",
            "open_href": "/intel-ops-pack",
            "do_this": ["Open the in-scope Intel row."],
            "check": "Named intel seat sees this row. Owner-only rows stay off this seat.",
            "capability": "CAP-INTEL-01",
            "criterion": "intel_fixture_seed",
            "surface": "intel_ops",
            "route": "/intel-ops-pack",
            "source": "test-fixture",
            "confidence": "DERIVED",
            "skip_if_known_broken": False,
        },
    ]
    return list(base) + extra


def _fixture_seat(person_id: str | None):
    if person_id == FIXTURE:
        return {
            "person_id": FIXTURE,
            "seat": "intel_holder",
            "can_read": True,
            "can_ask": True,
            "can_recall": True,
            "can_note": True,
            "gate": "role",
            "permissions": ["intel.rule.read", "decision.memory.read"],
            "money": False,
            "finance": False,
            "hr": False,
            "trading": False,
        }
    return _REAL_SEAT(person_id)


def test_honesty_and_seats() -> None:
    check("shell flag", wolf_shell.honesty_flags().get("intel_ops_needs_you_connective") is True)
    flags = pack.honesty_flags()
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("cap 01 built", flags.get("cap_intel_01") == "BUILT" and ledger["CAP-INTEL-01"][0] == "BUILT")
    check("cap 05 specified", flags.get("cap_intel_05") == "SPECIFIED" and ledger["CAP-INTEL-05"][0] == "SPECIFIED")
    check("ledger denom", len(ledger) == 77, str(len(ledger)))
    check("caps not raised", flags.get("caps_raised") is False)
    check(
        "honesty false",
        flags.get("proven") is False
        and flags.get("ready") is False
        and flags.get("staff_ready") is False
        and flags.get("invented_proven") is False
        and flags.get("invented_ready") is False
        and flags.get("invented_staff_ready") is False,
    )
    check(
        "humans uninvented",
        flags.get("haikal_human") == "not_started"
        and flags.get("devi_retest") == "parked"
        and flags.get("invented_haikal_human") is False
        and flags.get("invented_devi_done") is False,
    )
    check("au not started", flags.get("au_intel_02_wolf_started") is False)
    check("no auto", flags.get("auto_promote") is False and flags.get("auto_execute") is False)
    check("connective ids", flags.get("connective_claim_id") == pack.CONNECTIVE_CLAIM_ID)
    check("connective schema", flags.get("connective_schema") == pack.CONNECTIVE_SCHEMA_ID)
    check("connective bound", flags.get("connective_bound") == "beta-intel-safe")
    check("owner seat", (pack.seat_for("PERS-MATT") or {}).get("seat") == "owner")
    for person in ("PERS-DEVI", "PERS-AMANDA", "PERS-HAIKAL", "PERS-MISA", "PERS-OUTSIDER"):
        check(f"seat none {person}", pack.seat_for(person) is None)
    for fn, code in (
        (pack.refuse_haikal_done, "haikal_done_refused"),
        (pack.refuse_devi_done, "devi_done_refused"),
        (pack.refuse_staff_ready, "staff_ready_refused"),
        (pack.refuse_promote, "promote_refused"),
        (pack.refuse_execute, "execute_refused"),
        (pack.refuse_proven, "proven_refused"),
        (pack.refuse_ready, "ready_refused"),
    ):
        try:
            fn({})
            check(code, False)
        except pack.IntelOpsPackError as exc:
            check(code, exc.code == code and (exc.http_status in {None, 405} or str(exc.code).endswith("_refused")))
    check(
        "refuse haikal path",
        pack.connective_refuse_code("/api/intel/ops-pack/needs-you/haikal-done") == "haikal_done",
    )
    check(
        "refuse promote path",
        pack.connective_refuse_code("/api/intel/ops-pack/needs-you/promote") == "promote",
    )
    check(
        "strip not refused",
        pack.connective_refuse_code("/api/intel/ops-pack/needs-you") is None,
    )


def test_owner_live_strip() -> None:
    owner = pack.needs_you_connective_strip(verified_person_id="PERS-MATT")
    ids = _ids(owner)
    check("owner ok", owner.get("ok") is True and owner.get("bound") == "beta-intel-safe")
    check("owner schema", owner.get("schema") == "wolf.intel-ops-needs-you-connective.v1")
    check("owner count matches", owner.get("count") == len(owner.get("items") or []))
    check("owner sees full", (owner.get("seat") or {}).get("sees_full_intel") is True)
    check("owner not invented", owner.get("invented") is False and owner.get("invented_count") is False)
    check(
        "owner honesty",
        owner.get("staff_ready") is False
        and owner.get("proven") is False
        and owner.get("ready") is False
        and owner.get("haikal_human") == "not_started"
        and owner.get("devi_retest") == "parked"
        and owner.get("auto_promote") is False
        and owner.get("auto_execute") is False
        and owner.get("live_rule") is False
        and owner.get("duplicate_mutate_surface") is False,
    )
    caps = owner.get("caps") or {}
    check("strip cap 01", caps.get("cap_intel_01") == "BUILT")
    check("strip cap 05", caps.get("cap_intel_05") == "SPECIFIED")
    check("strip cr05 open", caps.get("cr_05") == "OPEN" and caps.get("cr_05_resolved") is False)
    check("strip cr au open", caps.get("cr_au") == "OPEN" and caps.get("au_intel_02_wolf_started") is False)
    progress = caps.get("progress_core_crs") or {}
    for cr in nye.TARGET_CRS:
        check(f"strip progress {cr[:8]}", progress.get(cr) == "OPEN", str(progress.get(cr)))
    for foreign in FOREIGN:
        check(f"owner excludes {foreign}", foreign not in ids)
    by_kind = owner.get("by_kind") or {}
    check("by kind keys", set(pack.CONNECTIVE_KINDS) <= set(by_kind))
    check("by kind sum", sum(by_kind.values()) == owner.get("count"))
    if owner.get("count"):
        nxt = owner.get("next_action") or {}
        check(
            "owner next connective",
            nxt.get("code") == "needs_you_connective" and nxt.get("preferred_over_pack") is True,
        )
        check("owner next not invented", nxt.get("invented") is False and nxt.get("staff_ready") is False)
        check("owner not empty", owner.get("empty") is False)
    else:
        check("owner empty honest", owner.get("empty") is True and owner.get("next_action") is None)
        check("owner empty message", "EMPTY" in str(owner.get("empty_message") or ""))
    desk = pack.build_desk(verified_person_id="PERS-MATT")
    check("desk strip", isinstance(desk.get("needs_you_connective"), dict))
    check("desk count", (desk.get("needs_you_connective") or {}).get("count") == owner.get("count"))
    desk_next = desk.get("next_action") or {}
    if owner.get("count"):
        check(
            "desk prefers connective",
            desk_next.get("code") == "needs_you_connective"
            and desk_next.get("preferred_over_pack") is True,
        )
    else:
        check(
            "desk pack href",
            desk_next.get("code") == "pack_href" and desk_next.get("href") == "/intel-ops-pack",
        )
    check("desk no promote", desk.get("auto_promote") is False and desk.get("staff_ready") is False)
    try:
        pack.connective_item_detail("CMQ-AMG-DAY", verified_person_id="PERS-MATT")
        check("foreign detail 404", False)
    except pack.IntelOpsPackError as exc:
        check("foreign detail 404", exc.code == "not_found" and exc.http_status == 404)
    try:
        pack.connective_item_detail("CMQ-DEVI-UMA-MOBILE", verified_person_id="PERS-MATT")
        check("devi detail 404", False)
    except pack.IntelOpsPackError as exc:
        check("devi detail 404", exc.code == "not_found")
    for person in ("PERS-AMANDA", "PERS-DEVI", "PERS-HAIKAL", "PERS-MISA", "PERS-OUTSIDER", ""):
        try:
            pack.needs_you_connective_strip(verified_person_id=person)
            check(f"strip forbidden {person or 'anon'}", False)
        except pack.IntelOpsPackError as exc:
            check(f"strip forbidden {person or 'anon'}", exc.code == "forbidden")


def test_scope_and_ack() -> None:
    real_seed = ocq.seed_templates
    real_seat = pack.seat_for
    ocq.seed_templates = _intel_templates
    pack.seat_for = _fixture_seat
    state = Path(tempfile.mkdtemp(prefix="intel-nye-")) / "state.json"
    events = Path(tempfile.mkdtemp(prefix="intel-nye-ev-")) / "events.jsonl"
    try:
        owner = pack.needs_you_connective_strip(
            verified_person_id="PERS-MATT",
            state_path=state,
        )
        holder = pack.needs_you_connective_strip(
            verified_person_id=FIXTURE,
            state_path=state,
        )
        owner_ids = _ids(owner)
        holder_ids = _ids(holder)
        check("fixture owner sees owner seed", "CMQ-INTEL-OWNER" in owner_ids)
        check("fixture owner sees named seed", "CMQ-INTEL-FIXTURE" in owner_ids)
        check("fixture holder sees named", "CMQ-INTEL-FIXTURE" in holder_ids)
        check("fixture holder misses owner-only", "CMQ-INTEL-OWNER" not in holder_ids)
        check("holder not full intel flag", (holder.get("seat") or {}).get("sees_full_intel") is False)
        check("holder count", holder.get("count") == len(holder.get("items") or []))
        check("owner count fixture", owner.get("count") == len(owner.get("items") or []))
        check("owner count gt holder or equal", (owner.get("count") or 0) >= (holder.get("count") or 0))
        for foreign in FOREIGN:
            check(f"fixture excludes {foreign}", foreign not in owner_ids and foreign not in holder_ids)
        nxt = owner.get("next_action") or {}
        check(
            "fixture next preferred",
            nxt.get("code") == "needs_you_connective"
            and nxt.get("preferred_over_pack") is True
            and nxt.get("object_id") == "CMQ-INTEL-OWNER",
            str(nxt.get("object_id")),
        )
        detail = pack.connective_item_detail(
            "CMQ-INTEL-FIXTURE",
            verified_person_id=FIXTURE,
            state_path=state,
        )
        check(
            "holder detail",
            (detail.get("object") or {}).get("object_id") == "CMQ-INTEL-FIXTURE"
            and detail.get("reuse_needs_you_depth") is True
            and detail.get("staff_ready") is False
            and detail.get("auto_promote") is False,
        )
        try:
            pack.connective_item_detail(
                "CMQ-INTEL-OWNER",
                verified_person_id=FIXTURE,
                state_path=state,
            )
            check("holder owner-only 403", False)
        except pack.IntelOpsPackError as exc:
            check("holder owner-only 403", exc.code == "forbidden" and exc.http_status == 403)
        try:
            pack.acknowledge_handoff(
                "CMQ-INTEL-OWNER",
                verified_person_id=FIXTURE,
                state_path=state,
                events_path=events,
            )
            check("holder ack owner-only 403", False)
        except pack.IntelOpsPackError as exc:
            check("holder ack owner-only 403", exc.code == "forbidden")
        ack = pack.acknowledge_handoff(
            "CMQ-INTEL-FIXTURE",
            verified_person_id=FIXTURE,
            note="seen",
            state_path=state,
            events_path=events,
        )
        event = ack.get("event") or {}
        check(
            "ack recorded",
            ack.get("ok") is True
            and ack.get("recorded") is True
            and ack.get("duplicate_mutate_surface") is False
            and ack.get("reuse_needs_you_depth") is True
            and ack.get("commissioned") is False
            and ack.get("staff_ready") is False
            and ack.get("cr_resolved") is False
            and ack.get("auto_promote") is False,
        )
        check(
            "ack actor fixture",
            event.get("person_id") == FIXTURE and event.get("human_commissioned") is False,
        )
        saved = json.loads(state.read_text(encoding="utf-8"))
        row = (saved.get("items") or {}).get("CMQ-INTEL-FIXTURE") or {}
        check(
            "state acknowledged",
            row.get("operator_status") == "ACKNOWLEDGED"
            and row.get("staff_ready") is False
            and row.get("haikal_human") == "not_started"
            and row.get("devi_retest") == "parked",
        )
        check("live state untouched", "CMQ-INTEL-FIXTURE" not in (nye._load_operator_state().get("items") or {}))
    finally:
        ocq.seed_templates = real_seed
        pack.seat_for = real_seat


def test_empty_and_handoff() -> None:
    real = pack._intel_candidates

    def _empty(**_kwargs):
        return []

    pack._intel_candidates = _empty
    try:
        quiet = pack.needs_you_connective_strip(verified_person_id="PERS-MATT")
    finally:
        pack._intel_candidates = real
    check("empty honest", quiet.get("empty") is True and quiet.get("count") == 0)
    check("empty next null", quiet.get("next_action") is None and quiet.get("items") == [])
    check("empty message", "EMPTY" in str(quiet.get("empty_message") or ""))
    check("empty no invent", quiet.get("invented") is False and quiet.get("staff_ready") is False)

    real_rows = pack._intel_connective_rows

    def _one(**_kwargs):
        return [
            {
                "object_id": "REC-TEST-INTEL",
                "kind": "intel_connective",
                "title": "Test connective attention",
                "audience": "INTEL_SEAT",
                "priority": "P1",
                "status": "open",
                "business": "INTEL",
                "surface": "ggv",
                "href": "/intel-ops-pack#operator-depth",
                "open_href": "/intel-ops-pack#operator-depth",
                "invented": False,
                "auto_promote": False,
                "auto_execute": False,
            }
        ]

    pack._intel_connective_rows = _one
    try:
        detail = pack.connective_item_detail(
            "REC-TEST-INTEL",
            verified_person_id="PERS-MATT",
        )
        check(
            "connective detail handoff",
            detail.get("reuse_needs_you_depth") is False
            and (detail.get("handoff") or {}).get("reuse_intel_connective") is True
            and "operator" in str((detail.get("handoff") or {}).get("detail") or ""),
        )
        try:
            pack.acknowledge_handoff(
                "REC-TEST-INTEL",
                verified_person_id="PERS-MATT",
            )
            check("connective ack handoff only", False)
        except pack.IntelOpsPackError as exc:
            check(
                "connective ack handoff only",
                exc.code == "handoff_only" and exc.http_status == 405,
            )
    finally:
        pack._intel_connective_rows = real_rows


def test_files_and_crs() -> None:
    for cr in (CR_05, CR_AU, *nye.TARGET_CRS):
        check(f"cr open {cr[:12]}", _cr(cr) == "OPEN", str(_cr(cr)))
    text = HTML.read_text(encoding="utf-8")
    check("html connective", "Needs-You connective" in text and 'id="needs-you-connective"' in text)
    check("html empty", "EMPTY" in text and "staff_ready" in text and "No auto-promote" in text)
    check("html no orphan copy", "PROVEN" in text and "not_started" in text or "not started" in text)
    check("no orphan dashboard", not (ROOT / "dashboards" / "intel-ops-needs-you.html").exists())
    source = (SCRIPTS / "core" / "intel_ops_pack.py").read_text(encoding="utf-8")
    check("source schema id", "wolf.intel-ops-needs-you-connective.v1" in source)
    for name in WIP:
        check(f"module skips {Path(name).name}", Path(name).name not in source)
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
                    return resp.status, {"raw": raw[:120]}
        except HTTPError as exc:
            raw = exc.read()
            try:
                payload = json.loads(raw.decode())
            except json.JSONDecodeError:
                payload = {"raw": raw[:200]}
            return exc.code, payload

    try:
        status, _payload = call("GET", "/api/intel/ops-pack/needs-you", None)
        check("http anon strip", status == 403, str(status))
        status, _payload = call("GET", "/api/intel/ops-pack/needs-you/items/CMQ-AMG-DAY", None)
        check("http anon detail", status == 403, str(status))
        status, _payload = call(
            "POST",
            "/api/intel/ops-pack/needs-you/items/CMQ-AMG-DAY/acknowledge",
            None,
            {},
        )
        check("http anon ack", status == 403, str(status))
        status, payload = call("GET", "/api/intel/ops-pack/needs-you", MATT)
        check(
            "http owner strip",
            status == 200
            and payload.get("ok") is True
            and payload.get("count") == len(payload.get("items") or [])
            and payload.get("staff_ready") is False
            and payload.get("bound") == "beta-intel-safe",
            str(status),
        )
        ids = _ids(payload)
        check("http owner no amg", "CMQ-AMG-DAY" not in ids)
        check("http owner no devi", "CMQ-DEVI-UMA-MOBILE" not in ids)
        status, desk = call("GET", "/api/intel/ops-pack", MATT)
        check(
            "http desk",
            status == 200 and isinstance(desk.get("needs_you_connective"), dict),
            str(status),
        )
        if (payload.get("count") or 0) > 0:
            check(
                "http desk next",
                (desk.get("next_action") or {}).get("code") == "needs_you_connective",
            )
        else:
            check(
                "http desk pack href",
                (desk.get("next_action") or {}).get("code") == "pack_href",
            )
        status, missing = call("GET", "/api/intel/ops-pack/needs-you/items/CMQ-AMG-DAY", MATT)
        check("http foreign 404", status == 404 and missing.get("error") == "not_found", str(status))
        for subject, label in (
            (AMANDA, "amanda"),
            (DEVI, "devi"),
            (HAIKAL, "haikal"),
            (MISA, "misa"),
            (OUTSIDER, "outsider"),
        ):
            status, body = call("GET", "/api/intel/ops-pack/needs-you", subject)
            check(f"http {label} 403", status == 403, f"{status} {body.get('error')}")
        status, body = call("POST", "/api/intel/ops-pack/needs-you/haikal-done", MATT, {})
        check(
            "http haikal done",
            status == 405 and body.get("error") == "haikal_done_refused",
            f"{status} {body.get('error')}",
        )
        status, body = call("POST", "/api/intel/ops-pack/needs-you/devi-done", MATT, {})
        check(
            "http devi done",
            status == 405 and body.get("error") == "devi_done_refused",
            f"{status} {body.get('error')}",
        )
        status, body = call("POST", "/api/intel/ops-pack/needs-you/promote", MATT, {})
        check(
            "http promote",
            status == 405 and body.get("error") == "promote_refused",
            f"{status} {body.get('error')}",
        )
        status, body = call("POST", "/api/intel/ops-pack/needs-you/staff-ready", MATT, {})
        check(
            "http staff ready",
            status == 405 and body.get("error") == "staff_ready_refused",
            f"{status} {body.get('error')}",
        )
        status, _page = call("GET", "/intel-ops-pack", None)
        check("http anon page", status == 403, str(status))
    finally:
        httpd.shutdown()


def main() -> int:
    test_honesty_and_seats()
    test_owner_live_strip()
    test_scope_and_ack()
    test_empty_and_handoff()
    test_files_and_crs()
    test_http()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
