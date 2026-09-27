#!/usr/bin/env python3
"""AMG guest experience / SLA incident operator depth — existing seats, empty trail."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"
os.environ.pop("WOLF_AMG_SLA_OPS_EVENTS", None)

from core import amg_ops_pack as pack  # noqa: E402
from core import amg_sla_incident as sla_fw  # noqa: E402
from core import amg_sla_incident_operator_depth as ops  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HTML = ROOT / "dashboards" / "amg-sla-incident.html"
HTML_CLUSTER = ROOT / "dashboards" / "amg-mgmt-cluster.html"
MODULE = SCRIPTS / "core" / "amg_sla_incident_operator_depth.py"
SERVE = SCRIPTS / "serve_beta.py"
BETA = "http://127.0.0.1:8788"
PROD = "http://127.0.0.1:8787"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
NOTE = "Owner touch. Slot stays empty."
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def http(
    method: str,
    path: str,
    *,
    body: dict | None = None,
    headers: dict | None = None,
    base: str = BETA,
) -> tuple[int, dict | str]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    hdrs = {"Accept": "application/json"}
    if body is not None:
        hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)
    req = Request(base + path, data=data, headers=hdrs, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def port_up(port: int) -> bool:
    s = socket.socket()
    s.settimeout(1.5)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def _cr(item_id: str) -> str | None:
    conn = sqlite3.connect(str(LIVE_DB))
    try:
        row = conn.execute(
            "SELECT state FROM wolf_completion_items WHERE id=?",
            (item_id,),
        ).fetchone()
    finally:
        conn.close()
    return None if row is None else str(row[0])


def _assign_count() -> int:
    conn = sqlite3.connect(str(LIVE_DB))
    try:
        row = conn.execute("SELECT COUNT(*) FROM org_assignments").fetchone()
    finally:
        conn.close()
    return int(row[0])


def _ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def _refused(kind: str, code: str) -> None:
    try:
        ops.record_operator_action(
            ops.EMPTY_ID,
            verified_person_id="PERS-MATT",
            kind=kind,
            note=NOTE,
            events_file=Path(tempfile.gettempdir()) / "amg-sla-depth-refuse.jsonl",
        )
        check(f"refuse {kind}", False, "accepted")
    except ops.SlaDepthError as exc:
        check(f"refuse {kind}", exc.code == code and exc.http_status == 403, exc.code)


def test_honesty_and_rbac() -> None:
    flags = ops.honesty_flags()
    check("bound", flags.get("bound") == "beta-amg-day-safe")
    check("schema", flags.get("schema_id") == ops.SCHEMA_ID)
    check("claim", flags.get("claim_id") == "bf-amg-sla-incident-operator-depth-20260923")
    check("proven false", flags.get("proven") is False)
    check("ready false", flags.get("ready") is False)
    check("staff_ready false", flags.get("staff_ready") is False)
    check("incident number null", flags.get("incident_number") is None)
    check("sla timer null", flags.get("sla_timer") is None)
    check("escalation outcome null", flags.get("escalation_outcome") is None)
    check("no live incident", flags.get("live_incident") is False)
    check("no live sla", flags.get("live_sla") is False)
    check("no live hotel", flags.get("live_hotel") is False)
    check("no guest machinery", flags.get("guest_experience_machinery") is False)
    check("no guest blast", flags.get("guest_blast") is False)
    check("no public post", flags.get("public_post") is False)
    check("no yanolja write", flags.get("yanolja_write") is False)
    check("haikal not started", flags.get("haikal_human") == "not_started")
    check("devi parked", flags.get("devi_retest") == "parked")
    check("no permission grant", flags.get("invented_permission_grant") is False)
    check("no bzg compose", flags.get("bzg_compose") is False)
    check("no secret mint", flags.get("secret_mint") is False)
    check("no access mutate", flags.get("cf_access_include_mutated") is False)
    check("intg not reopened", flags.get("intg_reopened") is False)
    check("w12 not reopened", flags.get("w12_fin_reopened") is False)
    check("clickup retired", flags.get("clickup_retired") is True)
    check("telegram retired", flags.get("telegram_retired") is True)
    check("cap 06 specified", flags.get("cap_amg_06") == "SPECIFIED", str(flags.get("cap_amg_06")))
    check("ceiling specified", flags.get("maturity_ceiling") == "SPECIFIED")
    check("cr open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("cr id", flags.get("cr_id") == "CR-e9b3d23e63c1c8a7")
    check("false resolve false", flags.get("false_resolve_cr") is False)
    for cr in pack.AMG_TARGET_CRS:
        check(f"amg {cr} open", (flags.get("amg_crs") or {}).get(cr) == "OPEN", str((flags.get("amg_crs") or {}).get(cr)))
    for cr in ops.PROGRESS_CRS:
        check(
            f"progress {cr} open",
            (flags.get("progress_core_crs") or {}).get(cr) == "OPEN",
            str((flags.get("progress_core_crs") or {}).get(cr)),
        )
    nav = flags.get("global_nav_crs") or {}
    check("nav rows read", set(nav) == set(ops.NAV_CRS), str(sorted(nav)))
    shell_flags = shell.honesty_flags()
    check("shell flag", shell_flags.get("amg_sla_incident_operator_depth") is True)
    check("shell staff_ready false", shell_flags.get("staff_ready") is False)
    schema = ops.schema_document()
    check("schema no yanolja", schema.get("yanolja_write_accepted") is False)
    check("schema no payment", schema.get("payment_accepted") is False)
    check("schema no live incident", schema.get("live_incident_accepted") is False)
    check("schema no live sla", schema.get("live_sla_accepted") is False)
    check("schema no sla timer", schema.get("sla_timer_accepted") is False)
    check("schema no escalation", schema.get("escalation_outcome_accepted") is False)
    check("schema no guest blast", schema.get("guest_blast_accepted") is False)
    check("schema no public post", schema.get("public_post_accepted") is False)
    check("empty id", schema.get("empty_object_id") == ops.EMPTY_ID)
    check("six slots", len(schema.get("slot_object_ids") or {}) == 6)
    check("desk not refused", ops.refuse_code("/api/amg/sla-incident/operator-depth") is None)
    check("rbac not refused", ops.refuse_code("/api/amg/sla-incident/operator-depth/rbac") is None)
    check("skeleton not this refuse", ops.refuse_code("/api/amg/sla-incident/payment") is None)
    check(
        "proven path refused",
        ops.refuse_code("/api/amg/sla-incident/operator-depth/proven") == "proven_refused",
    )
    check(
        "yanolja path refused",
        ops.refuse_code("/api/amg/sla-incident/operator-depth/yanolja-write") == "yanolja_refused",
    )
    check(
        "payment path refused",
        ops.refuse_code("/api/amg/sla-incident/operator-depth/payment") == "payment_refused",
    )
    check(
        "live incident path refused",
        ops.refuse_code("/api/amg/sla-incident/operator-depth/invent-live-incident") == "live_incident_refused",
    )
    check(
        "sla timer path refused",
        ops.refuse_code("/api/amg/sla-incident/operator-depth/sla-timer") == "sla_timer_refused",
    )
    check(
        "escalation path refused",
        ops.refuse_code("/api/amg/sla-incident/operator-depth/escalation-outcome")
        == "escalation_outcome_refused",
    )
    check(
        "guest blast path refused",
        ops.refuse_code("/api/amg/sla-incident/operator-depth/guest-blast") == "guest_blast_refused",
    )
    check(
        "public post path refused",
        ops.refuse_code("/api/amg/sla-incident/operator-depth/public-post") == "public_post_refused",
    )
    check(
        "live hotel path refused",
        ops.refuse_code("/api/amg/sla-incident/operator-depth/live-hotel") == "live_hotel_refused",
    )
    check(
        "access path refused",
        ops.refuse_code("/api/amg/sla-incident/operator-depth/access-include") == "access_refused",
    )
    check(
        "compose path refused",
        ops.refuse_code("/api/amg/sla-incident/operator-depth/bzg-compose") == "bzg_compose_refused",
    )
    check(
        "secret path refused",
        ops.refuse_code("/api/amg/sla-incident/operator-depth/secret-mint") == "secret_refused",
    )
    try:
        ops.require_seat(None)
        check("anon denied", False)
    except ops.SlaDepthError as exc:
        check("anon denied", exc.code == "denied" and exc.http_status == 403)
    owner = ops.require_seat("PERS-MATT")
    check("owner seat", owner.get("seat") == "owner" and owner.get("invented_permission_grant") is False)
    misa = ops.require_seat("PERS-MISA")
    check(
        "misa existing hotel ops",
        misa.get("person_id") == "PERS-MISA" and misa.get("seat") == "hotel_ops",
        str(misa),
    )
    for pid, label in (
        ("PERS-HAIKAL", "haikal"),
        ("PERS-DEVI", "devi"),
        ("PERS-AMANDA", "amanda"),
        ("PERS-OUTSIDER", "outsider"),
    ):
        try:
            ops.require_seat(pid)
            check(f"{label} outsider", False, "granted")
        except ops.SlaDepthError as exc:
            check(f"{label} outsider", exc.code == "outsider" and exc.http_status == 403, exc.code)
    prove = ops.prove_rbac(person_id="PERS-MATT")
    check("rbac note", (prove.get("actions") or {}).get("note") is True)
    check("rbac proven false", (prove.get("actions") or {}).get("proven") is False)
    check("rbac yanolja false", (prove.get("actions") or {}).get("yanolja_write") is False)
    check("rbac live incident false", (prove.get("actions") or {}).get("live_incident") is False)
    check("rbac sla timer false", (prove.get("actions") or {}).get("sla_timer") is False)
    check("rbac guest blast false", (prove.get("actions") or {}).get("guest_blast") is False)
    check("rbac public post false", (prove.get("actions") or {}).get("public_post") is False)
    check("rbac money false", (prove.get("actions") or {}).get("money") is False)
    check("rbac sla operator", prove.get("can_sla_operator") is True)
    src = MODULE.read_text(encoding="utf-8")
    check("no seat insert", "ensure_operator_depth_rbac" not in src)
    check("no bzg import", "import bzg" not in src and "from core import bzg" not in src)
    check("no completion write", "UPDATE wolf_completion" not in src and "INSERT INTO wolf_completion" not in src)
    check("no intg recover", "intg_connector" not in src)
    check("no fin restart", "fin_mgmt" not in src and "fin_budget" not in src)
    check("no yanolja connector", "cap-amg-01" not in src.lower() and "pms_orchestration" not in src)
    serve = SERVE.read_text(encoding="utf-8")
    check("route registered", "/api/amg/sla-incident/operator-depth" in serve)
    check("skeleton route kept", "/api/amg/sla-incident" in serve)
    check("no orphan dashboard", not (ROOT / "dashboards" / "amg-sla-incident-operator-depth.html").exists())
    page = HTML.read_text(encoding="utf-8")
    check("panel anchor", 'id="sla-depth"' in page)
    check("panel api", "/api/amg/sla-incident/operator-depth" in page)
    check("page still specified", "CAP-AMG-06 stays SPECIFIED" in page)
    check("page still not live trail", "not a live SLA/incident trail" in page)
    check("page still no invented incidents", "does not invent live incidents" in page)
    cluster = HTML_CLUSTER.read_text(encoding="utf-8")
    check("cluster links sla depth", "/amg-sla-incident#sla-depth" in cluster)
    check("cluster still empty honesty", "Empty stays empty" in cluster)


def test_desk_actions() -> None:
    ledger_before = LEDGER.read_bytes()
    assign_before = _assign_count()
    ops_before = list(pack.hotel_ops_ids())
    cr_before = {cr: _cr(cr) for cr in (*pack.AMG_TARGET_CRS, *ops.PROGRESS_CRS, *ops.NAV_CRS)}
    with tempfile.TemporaryDirectory(prefix="amg-sla-depth-") as tmp:
        root = Path(tmp)
        events = root / "events.jsonl"
        desk = ops.operator_depth_desk(verified_person_id="PERS-MATT", events_file=events)
        check("desk ok", desk.get("ok") is True and desk.get("empty") is True)
        check("desk slots", desk.get("slot_count") == 6, str(desk.get("slot_count")))
        check("desk recorded 0", desk.get("recorded_count") == 0)
        check(
            "desk metrics null",
            desk.get("incident_number") is None
            and desk.get("sla_timer") is None
            and desk.get("escalation_outcome") is None
            and desk.get("live_incident") is False
            and desk.get("guest_experience_machinery") is False
            and desk.get("guest_blast") is False
            and desk.get("public_post") is False,
        )
        check("desk not live hotel", desk.get("live_hotel") is False)
        check("desk staff_ready", desk.get("staff_ready") is False)
        check(
            "desk amg refresh",
            (desk.get("amg_desk") or {}).get("module_count") == 6
            and (desk.get("amg_desk") or {}).get("caps_raised") is False,
            str((desk.get("amg_desk") or {}).get("module_count")),
        )
        check(
            "desk needs you",
            isinstance((desk.get("needs_you") or {}).get("count"), int)
            and (desk.get("needs_you") or {}).get("staff_ready") is False
            and (desk.get("needs_you") or {}).get("duplicate_mutate_surface") is False,
            str(desk.get("needs_you"))[:240],
        )
        ids = {row.get("object_id") for row in desk.get("objects") or []}
        check("empty object", ops.EMPTY_ID in ids)
        check(
            "stage cards",
            {"SLA-REQUEST", "SLA-INCIDENT", "SLA-SLA", "SLA-ESCALATION", "SLA-TRAIL", "SLA-NOTES"} <= ids,
            str(sorted(ids)),
        )
        detail = ops.object_detail(ops.EMPTY_ID, verified_person_id="PERS-MATT", events_file=events)
        check(
            "empty detail",
            detail.get("object_kind") == "empty_placeholder"
            and detail.get("incident_number") is None
            and detail.get("sla_timer") is None
            and detail.get("live_incident") is False
            and detail.get("cap_state") == "SPECIFIED",
            str(detail.get("cap_state")),
        )
        request = ops.object_detail("SLA-REQUEST", verified_person_id="PERS-MISA", events_file=events)
        check(
            "misa slot detail",
            request.get("object_kind") == "sla_slot"
            and (request.get("slot") or {}).get("kind") == "request"
            and request.get("live_incident") is False
            and request.get("sla_timer") is None
            and request.get("escalation_outcome") is None,
        )
        sla_slot = ops.object_detail("SLA-SLA", verified_person_id="PERS-MATT", events_file=events)
        check("sla slot", (sla_slot.get("slot") or {}).get("kind") == "sla" and sla_slot.get("empty") is True)
        try:
            ops.object_detail("SLA-INVENTED", verified_person_id="PERS-MATT", events_file=events)
            check("unknown card", False)
        except ops.SlaDepthError as exc:
            check("unknown card", exc.code == "not_found")
        try:
            ops.record_operator_action(
                "SLA-REQUEST",
                verified_person_id="PERS-HAIKAL",
                kind="note",
                note=NOTE,
                events_file=events,
            )
            check("haikal action refused", False)
        except ops.SlaDepthError as exc:
            check("haikal action refused", exc.code == "outsider")
        touched = ops.record_operator_action(
            "SLA-REQUEST",
            verified_person_id="PERS-MATT",
            kind="next-action-touch",
            note=NOTE,
            events_file=events,
        )
        check(
            "next action refresh",
            touched.get("kind") == "next_action"
            and touched.get("framework_mutated") is False
            and touched.get("framework_unchanged") is True
            and (touched.get("needs_you") or {}).get("ok") is True
            and (touched.get("amg_desk") or {}).get("module_count") == 6
            and touched.get("incident_number") is None
            and touched.get("sla_timer") is None
            and touched.get("live_incident") is False
            and touched.get("yanolja_write") is False
            and touched.get("guest_blast") is False
            and touched.get("staff_ready") is False,
            str(touched)[:300],
        )
        handed = ops.record_operator_action(
            "SLA-INCIDENT",
            verified_person_id="PERS-MISA",
            kind="handoff-touch",
            note="Hotel ops handoff. SLA slots stay empty.",
            events_file=events,
        )
        check(
            "misa handoff",
            handed.get("kind") == "handoff_touch"
            and handed.get("framework_mutated") is False
            and handed.get("incident_number") is None
            and handed.get("live_incident") is False
            and (handed.get("seat") or {}).get("seat") == "hotel_ops",
        )
        noted = ops.record_operator_action(
            ops.DESK_OBJECT_ID,
            verified_person_id="PERS-MATT",
            kind="note",
            note=NOTE,
            events_file=events,
        )
        check("desk note", noted.get("object_id") == ops.DESK_OBJECT_ID and noted.get("bzg_compose") is False)
        reviewed = ops.record_operator_action(
            "SLA-ESCALATION",
            verified_person_id="PERS-MATT",
            kind="review-decision",
            note="Keep the named slot empty.",
            decision="still_specified",
            events_file=events,
        )
        check(
            "review still specified",
            reviewed.get("decision") == "still_specified" and reviewed.get("sla_timer") is None,
        )
        kept = ops.record_operator_action(
            "SLA-SLA",
            verified_person_id="PERS-MATT",
            kind="review-decision",
            decision="not_live_incident",
            events_file=events,
        )
        check("review not live incident", kept.get("decision") == "not_live_incident" and kept.get("live_incident") is False)
        kept_note = ops.record_operator_action(
            "SLA-TRAIL",
            verified_person_id="PERS-MATT",
            kind="review-decision",
            decision="keep_as_note",
            events_file=events,
        )
        check("review keep as note", kept_note.get("decision") == "keep_as_note")
        try:
            ops.record_operator_action(
                "SLA-NOTES",
                verified_person_id="PERS-MATT",
                kind="review-decision",
                decision="proven",
                events_file=events,
            )
            check("review proven refused", False)
        except ops.SlaDepthError as exc:
            check("review proven refused", exc.code == "proven_refused")
        try:
            ops.record_operator_action(
                "SLA-NOTES",
                verified_person_id="PERS-MATT",
                kind="review-decision",
                decision="invent-live-incident",
                events_file=events,
            )
            check("review live incident refused", False)
        except ops.SlaDepthError as exc:
            check("review live incident refused", exc.code == "live_incident_refused")
        try:
            ops.record_operator_action(
                "SLA-NOTES",
                verified_person_id="PERS-MATT",
                kind="review-decision",
                decision="escalated",
                events_file=events,
            )
            check("review invalid", False)
        except ops.SlaDepthError as exc:
            check("review invalid", exc.code == "invalid_decision")
        try:
            ops.record_operator_action(
                "SLA-NOTES",
                verified_person_id="PERS-MATT",
                kind="note",
                note="",
                events_file=events,
            )
            check("blank note", False)
        except ops.SlaDepthError as exc:
            check("blank note", exc.code == "missing_note")
        try:
            ops.record_operator_action(
                "SLA-NOTES",
                verified_person_id="PERS-MATT",
                kind="note",
                note="This slot is proven and ready.",
                events_file=events,
            )
            check("maturity note refused", False)
        except ops.SlaDepthError as exc:
            check("maturity note refused", exc.code == "refused_field")
        try:
            ops.record_operator_action(
                "SLA-NOTES",
                verified_person_id="PERS-MATT",
                kind="note",
                note="sla timer is 4",
                events_file=events,
            )
            check("sla timer note refused", False)
        except ops.SlaDepthError as exc:
            check("sla timer note refused", exc.code == "refused_field")
        try:
            ops.record_operator_action(
                "SLA-REQUEST",
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"compose": True, "kind": "note", "note": NOTE},
                events_file=events,
            )
            check("compose field refused", False)
        except ops.SlaDepthError as exc:
            check("compose field refused", exc.code == "bzg_compose_refused")
        try:
            ops.record_operator_action(
                "SLA-REQUEST",
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"money": 1, "kind": "note", "note": NOTE},
                events_file=events,
            )
            check("money field refused", False)
        except ops.SlaDepthError as exc:
            check("money field refused", exc.code == "money_refused")
        try:
            ops.record_operator_action(
                "SLA-INCIDENT",
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"incident_number": 3, "kind": "note", "note": NOTE},
                events_file=events,
            )
            check("incident number field refused", False)
        except ops.SlaDepthError as exc:
            check("incident number field refused", exc.code == "incident_number_refused")
        try:
            ops.record_operator_action(
                "SLA-SLA",
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"sla_timer": 80, "kind": "note", "note": NOTE},
                events_file=events,
            )
            check("sla timer field refused", False)
        except ops.SlaDepthError as exc:
            check("sla timer field refused", exc.code == "sla_timer_refused")
        try:
            ops.record_operator_action(
                "SLA-ESCALATION",
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"guest_blast": True, "kind": "note", "note": NOTE},
                events_file=events,
            )
            check("guest blast field refused", False)
        except ops.SlaDepthError as exc:
            check("guest blast field refused", exc.code == "guest_blast_refused")
        dismissed = ops.record_operator_action(
            ops.EMPTY_ID,
            verified_person_id="PERS-MATT",
            kind="dismiss-noise",
            note="Noise only.",
            events_file=events,
        )
        check("dismiss", dismissed.get("kind") == "dismiss_noise" and dismissed.get("framework_mutated") is False)
        after = ops.operator_depth_desk(verified_person_id="PERS-MATT", events_file=events)
        placeholder = after.get("empty_placeholder") or {}
        check(
            "dismissed placeholder",
            placeholder.get("dismissed_noise") is True
            and after.get("empty") is True
            and after.get("sla_timer") is None
            and after.get("live_incident") is False,
        )
        framework = sla_fw.build_framework()
        check("framework still empty", framework.get("recorded_count") == 0 and framework.get("on_disk") is False)
        try:
            ops.events_path(root / "money.sqlite")
            check("money path refused", False)
        except ops.SlaDepthError as exc:
            check("money path refused", exc.code == "money_refused")
        try:
            ops.events_path(sla_fw.DEFAULT_DB)
            check("framework path refused", False)
        except ops.SlaDepthError as exc:
            check("framework path refused", exc.code == "framework_refused")
    for kind, code in (
        ("proven", "proven_refused"),
        ("ready", "ready_refused"),
        ("staff-ready", "staff_ready_refused"),
        ("yanolja-write", "yanolja_refused"),
        ("payment", "payment_refused"),
        ("bank", "bank_refused"),
        ("books", "books_refused"),
        ("live-hotel", "live_hotel_refused"),
        ("invent-live-incident", "live_incident_refused"),
        ("live-incident", "live_incident_refused"),
        ("sla-timer", "sla_timer_refused"),
        ("escalation-outcome", "escalation_outcome_refused"),
        ("guest-blast", "guest_blast_refused"),
        ("public-post", "public_post_refused"),
        ("access-include", "access_refused"),
        ("secret-mint", "secret_refused"),
        ("bzg-compose", "bzg_compose_refused"),
        ("production", "production_refused"),
        ("resolve", "resolve_refused"),
        ("money", "money_refused"),
    ):
        _refused(kind, code)
    check("ledger unchanged", LEDGER.read_bytes() == ledger_before)
    check("assignments unchanged", _assign_count() == assign_before, f"{_assign_count()} vs {assign_before}")
    check("hotel ops unchanged", list(pack.hotel_ops_ids()) == ops_before, str(pack.hotel_ops_ids()))
    for cr, state in cr_before.items():
        check(f"cr unchanged {cr}", _cr(cr) == state, f"{_cr(cr)} vs {state}")
    ledger = _ledger()
    check("ledger cap 06", ledger["CAP-AMG-06"][0] == "SPECIFIED")
    check("ledger denominator", len(ledger) == 77, str(len(ledger)))


def test_live() -> None:
    check("port 8788", port_up(8788))
    check("port 8787", port_up(8787))
    if not port_up(8788):
        for name in (
            "anon 403",
            "owner desk",
            "owner rbac",
            "misa desk",
            "outsider 403",
            "haikal 403",
            "devi 403",
            "amanda 403",
            "detail",
            "action refresh",
            "proven refuse",
            "page",
            "prod 404",
        ):
            check(name, False, "beta down")
        return
    ledger_before = LEDGER.read_bytes()
    assign_before = _assign_count()
    st, anon = http("GET", "/api/amg/sla-incident/operator-depth")
    check("anon 403", st == 403, str(anon)[:180])
    st, desk = http(
        "GET",
        "/api/amg/sla-incident/operator-depth",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "owner desk",
        st == 200
        and isinstance(desk, dict)
        and desk.get("ok") is True
        and desk.get("empty") is True
        and desk.get("staff_ready") is False
        and desk.get("incident_number") is None
        and desk.get("sla_timer") is None
        and desk.get("live_incident") is False
        and desk.get("slot_count") == 6
        and desk.get("recorded_count") == 0,
        str(desk)[:240],
    )
    check(
        "owner cap",
        isinstance(desk, dict)
        and ((desk.get("honesty") or {}).get("cap_amg_06") == "SPECIFIED")
        and (desk.get("honesty") or {}).get("cr_state") == "OPEN",
        str((desk.get("honesty") or {}).get("cap_amg_06")),
    )
    st, rbac = http(
        "GET",
        "/api/amg/sla-incident/operator-depth/rbac",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "owner rbac",
        st == 200 and isinstance(rbac, dict) and rbac.get("can_sla_operator") is True,
        str(rbac)[:180],
    )
    st, misa = http(
        "GET",
        "/api/amg/sla-incident/operator-depth/desk",
        headers={"X-Wolf-Subject": MISA},
    )
    check(
        "misa existing seat",
        st == 200
        and isinstance(misa, dict)
        and (misa.get("seat") or {}).get("seat") == "hotel_ops"
        and misa.get("invented_permission_grant") is not True
        and ((misa.get("seat") or {}).get("invented_permission_grant") is False),
        str(misa)[:220],
    )
    for email, label in (
        (OUTSIDER, "outsider"),
        (HAIKAL, "haikal"),
        (DEVI, "devi"),
        (AMANDA, "amanda"),
    ):
        st, body = http(
            "GET",
            "/api/amg/sla-incident/operator-depth",
            headers={"X-Wolf-Subject": email},
        )
        check(f"{label} 403", st == 403, str(body)[:160])
    st, detail = http(
        "GET",
        "/api/amg/sla-incident/operator-depth/objects/SLA-REQUEST",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "detail",
        st == 200
        and isinstance(detail, dict)
        and detail.get("live_incident") is False
        and detail.get("sla_timer") is None
        and detail.get("escalation_outcome") is None
        and detail.get("cap_state") == "SPECIFIED",
        str(detail)[:220],
    )
    st, touch = http(
        "POST",
        "/api/amg/sla-incident/operator-depth/objects/EMPTY-AMG-SLA/next-action-touch",
        body={"note": "Live Beta touch. SLA slots stay empty."},
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "action refresh",
        st == 200
        and isinstance(touch, dict)
        and touch.get("kind") == "next_action"
        and touch.get("framework_mutated") is False
        and (touch.get("needs_you") or {}).get("staff_ready") is False
        and (touch.get("amg_desk") or {}).get("caps_raised") is False
        and touch.get("incident_number") is None
        and touch.get("live_incident") is False
        and touch.get("yanolja_write") is False
        and touch.get("guest_blast") is False
        and touch.get("bzg_compose") is False,
        str(touch)[:280],
    )
    st, refused = http(
        "POST",
        "/api/amg/sla-incident/operator-depth/proven",
        body={"note": NOTE},
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "proven refuse",
        st == 403 and isinstance(refused, dict) and refused.get("error") == "proven_refused",
        str(refused)[:180],
    )
    st, yanolja = http(
        "POST",
        "/api/amg/sla-incident/operator-depth/yanolja-write",
        body={},
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "yanolja refuse",
        st == 403 and isinstance(yanolja, dict) and yanolja.get("error") == "yanolja_refused",
        str(yanolja)[:160],
    )
    st, live_i = http(
        "POST",
        "/api/amg/sla-incident/operator-depth/invent-live-incident",
        body={},
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "live incident refuse",
        st == 403 and isinstance(live_i, dict) and live_i.get("error") == "live_incident_refused",
        str(live_i)[:160],
    )
    st, timer = http(
        "POST",
        "/api/amg/sla-incident/operator-depth/sla-timer",
        body={},
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "sla timer refuse",
        st == 403 and isinstance(timer, dict) and timer.get("error") == "sla_timer_refused",
        str(timer)[:160],
    )
    st, blast = http(
        "POST",
        "/api/amg/sla-incident/operator-depth/guest-blast",
        body={},
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "guest blast refuse",
        st == 403 and isinstance(blast, dict) and blast.get("error") == "guest_blast_refused",
        str(blast)[:160],
    )
    st, page = http("GET", "/amg-sla-incident", headers={"X-Wolf-Subject": MATT})
    raw = page if isinstance(page, str) else json.dumps(page)
    check(
        "page",
        st == 200 and "sla-depth" in raw and "CAP-AMG-06 stays SPECIFIED" in raw,
        str(st),
    )
    st, prod = http("GET", "/api/amg/sla-incident/operator-depth", base=PROD)
    check("prod 404", st == 404, str(prod)[:120])
    check("live ledger unchanged", LEDGER.read_bytes() == ledger_before)
    check("live assignments unchanged", _assign_count() == assign_before)
    for cr in pack.AMG_TARGET_CRS:
        check(f"live amg {cr}", _cr(cr) == "OPEN", str(_cr(cr)))
    for cr in ops.PROGRESS_CRS:
        check(f"live progress {cr}", _cr(cr) == "OPEN", str(_cr(cr)))


def test_wip_untouched(before: str, prod_pid: str) -> None:
    after = subprocess.check_output(["git", "hash-object", *WIP], cwd=str(ROOT), text=True)
    check("wip unchanged", before == after)
    now = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"],
        text=True,
    ).strip().splitlines()[0]
    check("prod pid untouched", now == prod_pid and bool(prod_pid), now)


def main() -> None:
    before = subprocess.check_output(["git", "hash-object", *WIP], cwd=str(ROOT), text=True)
    prod_pid = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"],
        text=True,
    ).strip().splitlines()[0]
    test_honesty_and_rbac()
    test_desk_actions()
    test_live()
    test_wip_untouched(before, prod_pid)
    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAILED")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
