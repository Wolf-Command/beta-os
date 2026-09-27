#!/usr/bin/env python3
"""GGV intercompany client operator depth — existing GGV seats, empty billing."""
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
os.environ.pop("WOLF_GGV_IC_OPS_EVENTS", None)

from core import ggv_intercompany_client as ic  # noqa: E402
from core import ggv_intercompany_client_operator_depth as ops  # noqa: E402
from core import ggv_ops_pack as pack  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HTML = ROOT / "dashboards" / "ggv-intercompany-client.html"
HTML_CLUSTER = ROOT / "dashboards" / "ggv-mgmt-cluster.html"
MODULE = SCRIPTS / "core" / "ggv_intercompany_client_operator_depth.py"
SERVE = SCRIPTS / "serve_beta.py"
BETA = "http://127.0.0.1:8788"
PROD = "http://127.0.0.1:8787"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
NOTE = "Owner touch. Slots stay empty."
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
            events_file=Path(tempfile.gettempdir()) / "ggv-ic-depth-refuse.jsonl",
        )
        check(f"refuse {kind}", False, "accepted")
    except ops.IntercoDepthError as exc:
        check(f"refuse {kind}", exc.code == code and exc.http_status == 403, exc.code)


def test_honesty_and_rbac() -> None:
    flags = ops.honesty_flags()
    check("bound", flags.get("bound") == "beta-ggv-ops-safe")
    check("schema", flags.get("schema_id") == ops.SCHEMA_ID)
    check("claim", flags.get("claim_id") == "bf-ggv-intercompany-client-operator-depth-20260923")
    check("proven false", flags.get("proven") is False)
    check("ready false", flags.get("ready") is False)
    check("staff_ready false", flags.get("staff_ready") is False)
    check("service record null", flags.get("service_record") is None)
    check("invoice null", flags.get("invoice") is None)
    check("allocation null", flags.get("allocation") is None)
    check("arms length null", flags.get("arms_length") is None)
    check("ar ap null", flags.get("ar_ap") is None)
    check("tax null", flags.get("tax_treatment") is None)
    check("tax not claimed", flags.get("tax_claimed") is False)
    check("payment null", flags.get("payment") is None)
    check("no live billing", flags.get("live_billing") is False)
    check("no client machinery", flags.get("client_machinery") is False)
    check("no invented invoice", flags.get("invented_invoice") is False)
    check("no invented allocation", flags.get("invented_allocation") is False)
    check("no invented ar ap", flags.get("invented_ar_ap") is False)
    check("no invented tax", flags.get("invented_tax") is False)
    check("no pnl revenue", "revenue" not in flags)
    check("no pnl cost", "cost" not in flags)
    check("no pnl margin", "margin" not in flags)
    check("no pnl fx", "fx" not in flags)
    check("no alchemist", flags.get("alchemist_write") is False)
    check("no books", flags.get("books_write") is False)
    check("no bank", flags.get("bank_write") is False)
    check("no guest blast", flags.get("guest_blast") is False)
    check("no public post", flags.get("public_post") is False)
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
    check("cap 06 specified", flags.get("cap_ggv_06") == "SPECIFIED", str(flags.get("cap_ggv_06")))
    check("ceiling specified", flags.get("maturity_ceiling") == "SPECIFIED")
    check("skeleton ceiling built", flags.get("skeleton_ceiling") == "BUILT")
    check("cr open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("cr id", flags.get("cr_id") == "CR-6a19c9221cab0178")
    check("false resolve false", flags.get("false_resolve_cr") is False)
    for cr in pack.GGV_TARGET_CRS:
        check(
            f"ggv {cr} open",
            (flags.get("ggv_crs") or {}).get(cr) == "OPEN",
            str((flags.get("ggv_crs") or {}).get(cr)),
        )
    for cr in ops.PROGRESS_CRS:
        check(
            f"progress {cr} open",
            (flags.get("progress_core_crs") or {}).get(cr) == "OPEN",
            str((flags.get("progress_core_crs") or {}).get(cr)),
        )
    nav = flags.get("global_nav_crs") or {}
    check("nav rows read", set(nav) == set(ops.NAV_CRS), str(sorted(nav)))
    shell_flags = shell.honesty_flags()
    check("shell flag", shell_flags.get("ggv_intercompany_client_operator_depth") is True)
    check("shell staff_ready false", shell_flags.get("staff_ready") is False)
    schema = ops.schema_document()
    check("schema no payment", schema.get("payment_accepted") is False)
    check("schema no bank", schema.get("bank_accepted") is False)
    check("schema no books", schema.get("books_accepted") is False)
    check("schema no alchemist", schema.get("alchemist_write_accepted") is False)
    check("schema no live billing", schema.get("live_billing_accepted") is False)
    check("schema no invoice", schema.get("invoice_accepted") is False)
    check("schema no allocation", schema.get("allocation_accepted") is False)
    check("schema no ar ap", schema.get("ar_ap_accepted") is False)
    check("schema no tax", schema.get("tax_accepted") is False)
    check("schema no guest blast", schema.get("guest_blast_accepted") is False)
    check("schema no public post", schema.get("public_post_accepted") is False)
    check("empty id", schema.get("empty_object_id") == ops.EMPTY_ID)
    check("six slots", len(schema.get("slot_object_ids") or {}) == 6)
    check("desk not refused", ops.refuse_code("/api/ggv/intercompany-client/operator-depth") is None)
    check("rbac not refused", ops.refuse_code("/api/ggv/intercompany-client/operator-depth/rbac") is None)
    check("skeleton invoice not this refuse", ops.refuse_code("/api/ggv/intercompany-client/invoice") is None)
    check("skeleton payment not this refuse", ops.refuse_code("/api/ggv/intercompany-client/payment") is None)
    check(
        "proven path refused",
        ops.refuse_code("/api/ggv/intercompany-client/operator-depth/proven") == "proven_refused",
    )
    check(
        "payment path refused",
        ops.refuse_code("/api/ggv/intercompany-client/operator-depth/payment") == "payment_refused",
    )
    check(
        "live billing path refused",
        ops.refuse_code("/api/ggv/intercompany-client/operator-depth/invent-live-billing")
        == "live_billing_refused",
    )
    check(
        "invoice path refused",
        ops.refuse_code("/api/ggv/intercompany-client/operator-depth/invent-invoice")
        == "invent_invoice_refused",
    )
    check(
        "allocation path refused",
        ops.refuse_code("/api/ggv/intercompany-client/operator-depth/allocation")
        == "invent_allocation_refused",
    )
    check(
        "ar ap path refused",
        ops.refuse_code("/api/ggv/intercompany-client/operator-depth/ar-ap") == "invent_ar_ap_refused",
    )
    check(
        "tax path refused",
        ops.refuse_code("/api/ggv/intercompany-client/operator-depth/tax-write") == "tax_refused",
    )
    check(
        "alchemist path refused",
        ops.refuse_code("/api/ggv/intercompany-client/operator-depth/alchemist-write")
        == "alchemist_refused",
    )
    check(
        "guest blast path refused",
        ops.refuse_code("/api/ggv/intercompany-client/operator-depth/guest-blast") == "guest_blast_refused",
    )
    check(
        "public post path refused",
        ops.refuse_code("/api/ggv/intercompany-client/operator-depth/public-post") == "public_post_refused",
    )
    check(
        "books path refused",
        ops.refuse_code("/api/ggv/intercompany-client/operator-depth/books") == "books_refused",
    )
    check(
        "access path refused",
        ops.refuse_code("/api/ggv/intercompany-client/operator-depth/access-include") == "access_refused",
    )
    check(
        "compose path refused",
        ops.refuse_code("/api/ggv/intercompany-client/operator-depth/bzg-compose") == "bzg_compose_refused",
    )
    check(
        "secret path refused",
        ops.refuse_code("/api/ggv/intercompany-client/operator-depth/secret-mint") == "secret_refused",
    )
    try:
        ops.require_seat(None)
        check("anon denied", False)
    except ops.IntercoDepthError as exc:
        check("anon denied", exc.code == "denied" and exc.http_status == 403)
    owner = ops.require_seat("PERS-MATT")
    check("owner seat", owner.get("seat") == "owner" and owner.get("invented_permission_grant") is False)
    for pid, label, seat_name in (
        ("PERS-AMANDA", "amanda", "content_management"),
        ("PERS-HAIKAL", "haikal", "editor"),
        ("PERS-MISA", "misa", "crew"),
    ):
        seat = ops.require_seat(pid)
        check(
            f"{label} existing ggv seat",
            seat.get("person_id") == pid and seat.get("seat") == seat_name,
            str(seat),
        )
    for pid, label in (
        ("PERS-DEVI", "devi"),
        ("PERS-OUTSIDER", "outsider"),
    ):
        try:
            ops.require_seat(pid)
            check(f"{label} outsider", False, "granted")
        except ops.IntercoDepthError as exc:
            check(f"{label} outsider", exc.code == "outsider" and exc.http_status == 403, exc.code)
    prove = ops.prove_rbac(person_id="PERS-MATT")
    check("rbac note", (prove.get("actions") or {}).get("note") is True)
    check("rbac proven false", (prove.get("actions") or {}).get("proven") is False)
    check("rbac payment false", (prove.get("actions") or {}).get("payment") is False)
    check("rbac live billing false", (prove.get("actions") or {}).get("live_billing") is False)
    check("rbac invoice false", (prove.get("actions") or {}).get("invoice") is False)
    check("rbac allocation false", (prove.get("actions") or {}).get("allocation") is False)
    check("rbac ar ap false", (prove.get("actions") or {}).get("ar_ap") is False)
    check("rbac tax false", (prove.get("actions") or {}).get("tax_write") is False)
    check("rbac alchemist false", (prove.get("actions") or {}).get("alchemist_write") is False)
    check("rbac guest blast false", (prove.get("actions") or {}).get("guest_blast") is False)
    check("rbac public post false", (prove.get("actions") or {}).get("public_post") is False)
    check("rbac money false", (prove.get("actions") or {}).get("money") is False)
    check("rbac interco operator", prove.get("can_interco_operator") is True)
    src = MODULE.read_text(encoding="utf-8")
    check("no seat insert", "ensure_operator_depth_rbac" not in src)
    check("no bzg import", "import bzg" not in src and "from core import bzg" not in src)
    check("no completion write", "UPDATE wolf_completion" not in src and "INSERT INTO wolf_completion" not in src)
    check("no intg recover", "intg_connector" not in src)
    check("no fin restart", "fin_mgmt" not in src and "fin_budget" not in src)
    check("no yanolja", "yanolja" not in src.lower())
    serve = SERVE.read_text(encoding="utf-8")
    check("route registered", "/api/ggv/intercompany-client/operator-depth" in serve)
    check("skeleton route kept", "/api/ggv/intercompany-client" in serve)
    check(
        "no orphan dashboard",
        not (ROOT / "dashboards" / "ggv-intercompany-client-operator-depth.html").exists(),
    )
    page = HTML.read_text(encoding="utf-8")
    check("panel anchor", 'id="interco-depth"' in page)
    check("panel api", "/api/ggv/intercompany-client/operator-depth" in page)
    check("page still specified", "CAP-GGV-06 stays SPECIFIED" in page)
    check("page still not live billing", "not live intercompany billing" in page)
    cluster = HTML_CLUSTER.read_text(encoding="utf-8")
    check("cluster links interco depth", "/ggv-intercompany-client#interco-depth" in cluster)
    check("cluster still empty honesty", "Empty stays empty" in cluster)


def test_desk_actions() -> None:
    ledger_before = LEDGER.read_bytes()
    assign_before = _assign_count()
    cr_before = {cr: _cr(cr) for cr in (*pack.GGV_TARGET_CRS, *ops.PROGRESS_CRS, *ops.NAV_CRS)}
    with tempfile.TemporaryDirectory(prefix="ggv-ic-depth-") as tmp:
        root = Path(tmp)
        events = root / "events.jsonl"
        desk = ops.operator_depth_desk(verified_person_id="PERS-MATT", events_file=events)
        check("desk ok", desk.get("ok") is True and desk.get("empty") is True)
        check("desk slots", desk.get("slot_count") == 6, str(desk.get("slot_count")))
        check("desk recorded 0", desk.get("recorded_count") == 0)
        check(
            "desk metrics null",
            desk.get("service_record") is None
            and desk.get("invoice") is None
            and desk.get("allocation") is None
            and desk.get("arms_length") is None
            and desk.get("ar_ap") is None
            and desk.get("tax_treatment") is None
            and desk.get("payment") is None
            and desk.get("live_billing") is False
            and desk.get("client_machinery") is False
            and desk.get("guest_blast") is False
            and desk.get("public_post") is False,
        )
        check("desk no pnl strip", "revenue" not in desk and "margin" not in desk)
        check("desk not alchemist", desk.get("alchemist_write") is False)
        check("desk staff_ready", desk.get("staff_ready") is False)
        check(
            "desk ggv refresh",
            (desk.get("ggv_desk") or {}).get("module_count") == 5
            and (desk.get("ggv_desk") or {}).get("caps_raised") is False,
            str((desk.get("ggv_desk") or {}).get("module_count")),
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
            {
                "IC-SERVICE-RECORD",
                "IC-INVOICE",
                "IC-ALLOCATION",
                "IC-ARMS-LENGTH",
                "IC-AR-AP",
                "IC-NOTES",
            }
            <= ids,
            str(sorted(ids)),
        )
        detail = ops.object_detail(ops.EMPTY_ID, verified_person_id="PERS-MATT", events_file=events)
        check(
            "empty detail",
            detail.get("object_kind") == "empty_placeholder"
            and detail.get("invoice") is None
            and detail.get("ar_ap") is None
            and detail.get("payment") is None
            and detail.get("live_billing") is False
            and detail.get("cap_state") == "SPECIFIED",
            str(detail.get("cap_state")),
        )
        service = ops.object_detail(
            "IC-SERVICE-RECORD",
            verified_person_id="PERS-AMANDA",
            events_file=events,
        )
        check(
            "amanda slot detail",
            service.get("object_kind") == "interco_slot"
            and (service.get("slot") or {}).get("kind") == "service_record"
            and service.get("live_billing") is False
            and service.get("invoice") is None
            and service.get("payment") is None
            and (service.get("seat") or {}).get("seat") == "content_management",
        )
        invoice_slot = ops.object_detail("IC-INVOICE", verified_person_id="PERS-MATT", events_file=events)
        check(
            "invoice slot empty",
            (invoice_slot.get("slot") or {}).get("kind") == "invoice"
            and invoice_slot.get("empty") is True
            and invoice_slot.get("invoice") is None
            and invoice_slot.get("live_billing") is False,
        )
        try:
            ops.object_detail("IC-INVENTED", verified_person_id="PERS-MATT", events_file=events)
            check("unknown card", False)
        except ops.IntercoDepthError as exc:
            check("unknown card", exc.code == "not_found")
        try:
            ops.record_operator_action(
                "IC-SERVICE-RECORD",
                verified_person_id="PERS-DEVI",
                kind="note",
                note=NOTE,
                events_file=events,
            )
            check("devi action refused", False)
        except ops.IntercoDepthError as exc:
            check("devi action refused", exc.code == "outsider")
        touched = ops.record_operator_action(
            "IC-SERVICE-RECORD",
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
            and (touched.get("ggv_desk") or {}).get("module_count") == 5
            and touched.get("invoice") is None
            and touched.get("allocation") is None
            and touched.get("ar_ap") is None
            and touched.get("payment") is None
            and touched.get("live_billing") is False
            and touched.get("alchemist_write") is False
            and touched.get("guest_blast") is False
            and touched.get("staff_ready") is False,
            str(touched)[:300],
        )
        handed = ops.record_operator_action(
            "IC-INVOICE",
            verified_person_id="PERS-HAIKAL",
            kind="handoff-touch",
            note="Editor handoff. Intercompany slots stay empty.",
            events_file=events,
        )
        check(
            "haikal handoff",
            handed.get("kind") == "handoff_touch"
            and handed.get("framework_mutated") is False
            and handed.get("invoice") is None
            and handed.get("live_billing") is False
            and (handed.get("seat") or {}).get("seat") == "editor",
        )
        noted = ops.record_operator_action(
            ops.DESK_OBJECT_ID,
            verified_person_id="PERS-MISA",
            kind="note",
            note=NOTE,
            events_file=events,
        )
        check(
            "misa desk note",
            noted.get("object_id") == ops.DESK_OBJECT_ID
            and noted.get("bzg_compose") is False
            and (noted.get("seat") or {}).get("seat") == "crew",
        )
        reviewed = ops.record_operator_action(
            "IC-ALLOCATION",
            verified_person_id="PERS-MATT",
            kind="review-decision",
            note="Keep the named slot empty.",
            decision="still_specified",
            events_file=events,
        )
        check(
            "review still specified",
            reviewed.get("decision") == "still_specified" and reviewed.get("invoice") is None,
        )
        kept = ops.record_operator_action(
            "IC-ARMS-LENGTH",
            verified_person_id="PERS-MATT",
            kind="review-decision",
            decision="not_live_billing",
            events_file=events,
        )
        check(
            "review not live billing",
            kept.get("decision") == "not_live_billing" and kept.get("live_billing") is False,
        )
        kept_note = ops.record_operator_action(
            "IC-AR-AP",
            verified_person_id="PERS-MATT",
            kind="review-decision",
            decision="keep_as_note",
            events_file=events,
        )
        check("review keep as note", kept_note.get("decision") == "keep_as_note")
        try:
            ops.record_operator_action(
                "IC-NOTES",
                verified_person_id="PERS-MATT",
                kind="review-decision",
                decision="proven",
                events_file=events,
            )
            check("review proven refused", False)
        except ops.IntercoDepthError as exc:
            check("review proven refused", exc.code == "proven_refused")
        try:
            ops.record_operator_action(
                "IC-NOTES",
                verified_person_id="PERS-MATT",
                kind="review-decision",
                decision="invent-live-billing",
                events_file=events,
            )
            check("review live billing refused", False)
        except ops.IntercoDepthError as exc:
            check("review live billing refused", exc.code == "live_billing_refused")
        try:
            ops.record_operator_action(
                "IC-NOTES",
                verified_person_id="PERS-MATT",
                kind="review-decision",
                decision="invent-invoice",
                events_file=events,
            )
            check("review invoice refused", False)
        except ops.IntercoDepthError as exc:
            check("review invoice refused", exc.code == "invent_invoice_refused")
        try:
            ops.record_operator_action(
                "IC-NOTES",
                verified_person_id="PERS-MATT",
                kind="review-decision",
                decision="tax-write",
                events_file=events,
            )
            check("review tax refused", False)
        except ops.IntercoDepthError as exc:
            check("review tax refused", exc.code == "tax_refused")
        try:
            ops.record_operator_action(
                "IC-NOTES",
                verified_person_id="PERS-MATT",
                kind="review-decision",
                decision="improved",
                events_file=events,
            )
            check("review invalid", False)
        except ops.IntercoDepthError as exc:
            check("review invalid", exc.code == "invalid_decision")
        try:
            ops.record_operator_action(
                "IC-NOTES",
                verified_person_id="PERS-MATT",
                kind="note",
                note="",
                events_file=events,
            )
            check("blank note", False)
        except ops.IntercoDepthError as exc:
            check("blank note", exc.code == "missing_note")
        try:
            ops.record_operator_action(
                "IC-NOTES",
                verified_person_id="PERS-MATT",
                kind="note",
                note="This slot is proven and ready.",
                events_file=events,
            )
            check("maturity note refused", False)
        except ops.IntercoDepthError as exc:
            check("maturity note refused", exc.code == "refused_field")
        try:
            ops.record_operator_action(
                "IC-SERVICE-RECORD",
                verified_person_id="PERS-MATT",
                kind="note",
                note="payment recorded for this client",
                events_file=events,
            )
            check("payment note refused", False)
        except ops.IntercoDepthError as exc:
            check("payment note refused", exc.code == "refused_field")
        try:
            ops.record_operator_action(
                "IC-SERVICE-RECORD",
                verified_person_id="PERS-MATT",
                kind="note",
                note="invoice recorded for this slot",
                events_file=events,
            )
            check("invoice note refused", False)
        except ops.IntercoDepthError as exc:
            check("invoice note refused", exc.code == "refused_field")
        try:
            ops.record_operator_action(
                "IC-SERVICE-RECORD",
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"compose": True, "kind": "note", "note": NOTE},
                events_file=events,
            )
            check("compose field refused", False)
        except ops.IntercoDepthError as exc:
            check("compose field refused", exc.code == "bzg_compose_refused")
        try:
            ops.record_operator_action(
                "IC-SERVICE-RECORD",
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"money": 1, "kind": "note", "note": NOTE},
                events_file=events,
            )
            check("money field refused", False)
        except ops.IntercoDepthError as exc:
            check("money field refused", exc.code == "money_refused")
        try:
            ops.record_operator_action(
                "IC-INVOICE",
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"invoice": 4, "kind": "note", "note": NOTE},
                events_file=events,
            )
            check("invoice field refused", False)
        except ops.IntercoDepthError as exc:
            check("invoice field refused", exc.code == "invent_invoice_refused")
        try:
            ops.record_operator_action(
                "IC-ALLOCATION",
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"allocation": 1, "kind": "note", "note": NOTE},
                events_file=events,
            )
            check("allocation field refused", False)
        except ops.IntercoDepthError as exc:
            check("allocation field refused", exc.code == "invent_allocation_refused")
        try:
            ops.record_operator_action(
                "IC-AR-AP",
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"ar_ap": 9, "kind": "note", "note": NOTE},
                events_file=events,
            )
            check("ar ap field refused", False)
        except ops.IntercoDepthError as exc:
            check("ar ap field refused", exc.code == "invent_ar_ap_refused")
        try:
            ops.record_operator_action(
                "IC-NOTES",
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"tax": True, "kind": "note", "note": NOTE},
                events_file=events,
            )
            check("tax field refused", False)
        except ops.IntercoDepthError as exc:
            check("tax field refused", exc.code == "tax_refused")
        try:
            ops.record_operator_action(
                "IC-ARMS-LENGTH",
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"alchemist": True, "kind": "note", "note": NOTE},
                events_file=events,
            )
            check("alchemist field refused", False)
        except ops.IntercoDepthError as exc:
            check("alchemist field refused", exc.code == "alchemist_refused")
        try:
            ops.record_operator_action(
                "IC-SERVICE-RECORD",
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"guest_blast": True, "kind": "note", "note": NOTE},
                events_file=events,
            )
            check("guest blast field refused", False)
        except ops.IntercoDepthError as exc:
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
            and after.get("invoice") is None
            and after.get("live_billing") is False,
        )
        framework = ic.build_framework()
        check("framework still empty", framework.get("recorded_count") == 0 and framework.get("on_disk") is False)
        try:
            ops.events_path(root / "money.sqlite")
            check("money path refused", False)
        except ops.IntercoDepthError as exc:
            check("money path refused", exc.code == "money_refused")
        try:
            ops.events_path(ic.DEFAULT_DB)
            check("framework path refused", False)
        except ops.IntercoDepthError as exc:
            check("framework path refused", exc.code == "framework_refused")
        try:
            ops.events_path(root / "invoice.jsonl")
            check("invoice path refused", False)
        except ops.IntercoDepthError as exc:
            check("invoice path refused", exc.code == "invent_invoice_refused")
    for kind, code in (
        ("proven", "proven_refused"),
        ("ready", "ready_refused"),
        ("staff-ready", "staff_ready_refused"),
        ("payment", "payment_refused"),
        ("bank", "bank_refused"),
        ("books", "books_refused"),
        ("alchemist-write", "alchemist_refused"),
        ("invent-live-billing", "live_billing_refused"),
        ("live-billing", "live_billing_refused"),
        ("invent-invoice", "invent_invoice_refused"),
        ("allocation", "invent_allocation_refused"),
        ("tax-write", "tax_refused"),
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
    for cr, state in cr_before.items():
        check(f"cr unchanged {cr}", _cr(cr) == state, f"{_cr(cr)} vs {state}")
    ledger = _ledger()
    check("ledger cap 06", ledger["CAP-GGV-06"][0] == "SPECIFIED")
    check("ledger denominator", len(ledger) == 77, str(len(ledger)))


def test_live() -> None:
    check("port 8788", port_up(8788))
    check("port 8787", port_up(8787))
    if not port_up(8788):
        for name in (
            "anon 403",
            "owner desk",
            "owner rbac",
            "amanda desk",
            "haikal desk",
            "misa desk",
            "outsider 403",
            "devi 403",
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
    st, anon = http("GET", "/api/ggv/intercompany-client/operator-depth")
    check("anon 403", st == 403, str(anon)[:180])
    st, desk = http(
        "GET",
        "/api/ggv/intercompany-client/operator-depth",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "owner desk",
        st == 200
        and isinstance(desk, dict)
        and desk.get("ok") is True
        and desk.get("empty") is True
        and desk.get("staff_ready") is False
        and desk.get("invoice") is None
        and desk.get("allocation") is None
        and desk.get("ar_ap") is None
        and desk.get("payment") is None
        and desk.get("live_billing") is False
        and desk.get("slot_count") == 6
        and desk.get("recorded_count") == 0,
        str(desk)[:240],
    )
    check(
        "owner cap",
        isinstance(desk, dict)
        and ((desk.get("honesty") or {}).get("cap_ggv_06") == "SPECIFIED")
        and (desk.get("honesty") or {}).get("cr_state") == "OPEN",
        str((desk.get("honesty") or {}).get("cap_ggv_06")),
    )
    st, rbac = http(
        "GET",
        "/api/ggv/intercompany-client/operator-depth/rbac",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "owner rbac",
        st == 200 and isinstance(rbac, dict) and rbac.get("can_interco_operator") is True,
        str(rbac)[:180],
    )
    for email, label, seat_name in (
        (AMANDA, "amanda", "content_management"),
        (HAIKAL, "haikal", "editor"),
        (MISA, "misa", "crew"),
    ):
        st, body = http(
            "GET",
            "/api/ggv/intercompany-client/operator-depth/desk",
            headers={"X-Wolf-Subject": email},
        )
        check(
            f"{label} existing seat",
            st == 200
            and isinstance(body, dict)
            and (body.get("seat") or {}).get("seat") == seat_name
            and body.get("invented_permission_grant") is not True
            and ((body.get("seat") or {}).get("invented_permission_grant") is False),
            str(body)[:220],
        )
    for email, label in (
        (OUTSIDER, "outsider"),
        (DEVI, "devi"),
    ):
        st, body = http(
            "GET",
            "/api/ggv/intercompany-client/operator-depth",
            headers={"X-Wolf-Subject": email},
        )
        check(f"{label} 403", st == 403, str(body)[:160])
    st, detail = http(
        "GET",
        "/api/ggv/intercompany-client/operator-depth/objects/IC-INVOICE",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "detail",
        st == 200
        and isinstance(detail, dict)
        and detail.get("live_billing") is False
        and detail.get("invoice") is None
        and detail.get("payment") is None
        and detail.get("cap_state") == "SPECIFIED",
        str(detail)[:220],
    )
    st, touch = http(
        "POST",
        "/api/ggv/intercompany-client/operator-depth/objects/EMPTY-GGV-IC/next-action-touch",
        body={"note": "Live Beta touch. Intercompany slots stay empty."},
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "action refresh",
        st == 200
        and isinstance(touch, dict)
        and touch.get("kind") == "next_action"
        and touch.get("framework_mutated") is False
        and (touch.get("needs_you") or {}).get("staff_ready") is False
        and (touch.get("ggv_desk") or {}).get("caps_raised") is False
        and touch.get("invoice") is None
        and touch.get("live_billing") is False
        and touch.get("alchemist_write") is False
        and touch.get("guest_blast") is False
        and touch.get("bzg_compose") is False,
        str(touch)[:280],
    )
    for path, code, label in (
        ("/api/ggv/intercompany-client/operator-depth/proven", "proven_refused", "proven refuse"),
        (
            "/api/ggv/intercompany-client/operator-depth/invent-live-billing",
            "live_billing_refused",
            "live billing refuse",
        ),
        (
            "/api/ggv/intercompany-client/operator-depth/invent-invoice",
            "invent_invoice_refused",
            "invoice refuse",
        ),
        ("/api/ggv/intercompany-client/operator-depth/payment", "payment_refused", "payment refuse"),
        (
            "/api/ggv/intercompany-client/operator-depth/alchemist-write",
            "alchemist_refused",
            "alchemist refuse",
        ),
        (
            "/api/ggv/intercompany-client/operator-depth/guest-blast",
            "guest_blast_refused",
            "guest blast refuse",
        ),
        ("/api/ggv/intercompany-client/operator-depth/books", "books_refused", "books refuse"),
        (
            "/api/ggv/intercompany-client/operator-depth/tax-write",
            "tax_refused",
            "tax refuse",
        ),
        (
            "/api/ggv/intercompany-client/operator-depth/bzg-compose",
            "bzg_compose_refused",
            "compose refuse",
        ),
    ):
        st, refused = http("POST", path, body={"note": NOTE}, headers={"X-Wolf-Subject": MATT})
        check(
            label,
            st == 403 and isinstance(refused, dict) and refused.get("error") == code,
            str(refused)[:180],
        )
    st, page = http("GET", "/ggv-intercompany-client", headers={"X-Wolf-Subject": MATT})
    raw = page if isinstance(page, str) else json.dumps(page)
    check(
        "page",
        st == 200 and "interco-depth" in raw and "CAP-GGV-06 stays SPECIFIED" in raw,
        str(st),
    )
    st, skeleton = http(
        "GET",
        "/api/ggv/intercompany-client/invoice",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "skeleton invoice still empty",
        st == 200
        and isinstance(skeleton, dict)
        and skeleton.get("invoice") is None
        and skeleton.get("live_billing") is False,
        str(skeleton)[:180],
    )
    st, prod = http("GET", "/api/ggv/intercompany-client/operator-depth", base=PROD)
    check("prod 404", st == 404, str(prod)[:120])
    check("live ledger unchanged", LEDGER.read_bytes() == ledger_before)
    check("live assignments unchanged", _assign_count() == assign_before)
    for cr in pack.GGV_TARGET_CRS:
        check(f"live ggv {cr}", _cr(cr) == "OPEN", str(_cr(cr)))
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
