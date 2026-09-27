#!/usr/bin/env python3
"""CRM package intelligence operator depth — existing CRM seats, empty register."""
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
os.environ.pop("WOLF_CRM_PKG_OPS_EVENTS", None)
os.environ.pop("WOLF_CRM_PACKAGE_DB", None)

from core import crm_ops_needs_you_connective as nye  # noqa: E402
from core import crm_package_intel as pkg  # noqa: E402
from core import crm_package_intel_operator_depth as ops  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HTML = ROOT / "dashboards" / "crm-package-intel.html"
HTML_CLUSTER = ROOT / "dashboards" / "crm-mgmt-cluster.html"
MODULE = SCRIPTS / "core" / "crm_package_intel_operator_depth.py"
SERVE = SCRIPTS / "serve_beta.py"
BETA = "http://127.0.0.1:8788"
PROD = "http://127.0.0.1:8787"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
NOTE = "Owner touch. Package slots stay empty."
VALID = {
    "name": "Fixture stay",
    "brand": "habitat",
    "status": "NAMED",
    "evidence_refs": ["EV-fixture-stay"],
}
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
            events_file=Path(tempfile.gettempdir()) / "crm-pkg-depth-refuse.jsonl",
        )
        check(f"refuse {kind}", False, "accepted")
    except ops.PackageDepthError as exc:
        check(f"refuse {kind}", exc.code == code and exc.http_status == 403, exc.code)


def test_honesty_and_rbac() -> None:
    flags = ops.honesty_flags()
    check("bound", flags.get("bound") == "beta-crm-loop-safe")
    check("schema", flags.get("schema_id") == ops.SCHEMA_ID)
    check("claim", flags.get("claim_id") == "bf-crm-package-intel-operator-depth-20260923")
    check("proven false", flags.get("proven") is False)
    check("ready false", flags.get("ready") is False)
    check("staff_ready false", flags.get("staff_ready") is False)
    check("price null", flags.get("price") is None)
    check("margin null", flags.get("margin") is None)
    check("pricing not truth", flags.get("pricing_is_truth") is False)
    check("price not market", flags.get("price_as_market") is False)
    check("census null", flags.get("market_package_count") is None)
    check("no live census", flags.get("live_census") is False)
    check("no invented census", flags.get("invented_live_census") is False)
    check("no live booking", flags.get("live_booking_write") is False)
    check("booking not mutated", flags.get("booking_mutated") is False)
    check("no habitat", flags.get("habitat_commissioned") is False)
    check("no habitat cutover", flags.get("habitat_cutover") is False)
    check("no klaviyo", flags.get("klaviyo_write") is False)
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
    check("register not mutated", flags.get("register_mutated") is False)
    check("cap 03 specified", flags.get("cap_crm_03") == "SPECIFIED", str(flags.get("cap_crm_03")))
    check("cap 01 built", flags.get("cap_crm_01") == "BUILT", str(flags.get("cap_crm_01")))
    check("cap 02 specified", flags.get("cap_crm_02") == "SPECIFIED", str(flags.get("cap_crm_02")))
    check("cap 04 built", flags.get("cap_crm_04") == "BUILT", str(flags.get("cap_crm_04")))
    check("ceiling specified", flags.get("maturity_ceiling") == "SPECIFIED")
    check("skeleton ceiling built", flags.get("skeleton_ceiling") == "BUILT")
    check("habitat au", flags.get("au_crm_01_habitat") == "NOT STARTED", str(flags.get("au_crm_01_habitat")))
    check("cr open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("cr id", flags.get("cr_id") == "CR-e5ff219bb1d585f7")
    check("false resolve false", flags.get("false_resolve_cr") is False)
    for cr in nye.CRM_TARGET_CRS:
        check(
            f"crm {cr} open",
            (flags.get("crm_crs") or {}).get(cr) == "OPEN",
            str((flags.get("crm_crs") or {}).get(cr)),
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
    check("shell flag", shell_flags.get("crm_package_intel_operator_depth") is True)
    check("shell staff_ready false", shell_flags.get("staff_ready") is False)
    schema = ops.schema_document()
    check("schema no price", schema.get("price_accepted") is False)
    check("schema no market price", schema.get("price_as_market_accepted") is False)
    check("schema no census", schema.get("live_census_accepted") is False)
    check("schema no booking", schema.get("live_booking_accepted") is False)
    check("schema no habitat", schema.get("habitat_cutover_accepted") is False)
    check("schema no klaviyo", schema.get("klaviyo_write_accepted") is False)
    check("schema no guest blast", schema.get("guest_blast_accepted") is False)
    check("schema no public post", schema.get("public_post_accepted") is False)
    check("empty id", schema.get("empty_object_id") == ops.EMPTY_ID)
    check("six slots", len(schema.get("slot_object_ids") or {}) == 6)
    check("chain", schema.get("chain") == list(ops.CHAIN))
    check("desk not refused", ops.refuse_code("/api/crm/package-intel/operator-depth") is None)
    check("rbac not refused", ops.refuse_code("/api/crm/package-intel/operator-depth/rbac") is None)
    check("register price not this refuse", ops.refuse_code("/api/crm/package-intel/price") is None)
    check("register booking not this refuse", ops.refuse_code("/api/crm/package-intel/booking") is None)
    check(
        "proven path refused",
        ops.refuse_code("/api/crm/package-intel/operator-depth/proven") == "proven_refused",
    )
    check(
        "census path refused",
        ops.refuse_code("/api/crm/package-intel/operator-depth/invent-live-census")
        == "live_census_refused",
    )
    check(
        "booking path refused",
        ops.refuse_code("/api/crm/package-intel/operator-depth/invent-booking")
        == "live_booking_refused",
    )
    check(
        "price path refused",
        ops.refuse_code("/api/crm/package-intel/operator-depth/price-as-market")
        == "price_as_market_refused",
    )
    check(
        "habitat path refused",
        ops.refuse_code("/api/crm/package-intel/operator-depth/habitat-cutover")
        == "habitat_refused",
    )
    check(
        "klaviyo path refused",
        ops.refuse_code("/api/crm/package-intel/operator-depth/klaviyo-write")
        == "klaviyo_refused",
    )
    check(
        "compose path refused",
        ops.refuse_code("/api/crm/package-intel/operator-depth/bzg-compose")
        == "bzg_compose_refused",
    )
    check(
        "guest blast path refused",
        ops.refuse_code("/api/crm/package-intel/operator-depth/guest-blast")
        == "guest_blast_refused",
    )
    check(
        "access path refused",
        ops.refuse_code("/api/crm/package-intel/operator-depth/access-include")
        == "access_refused",
    )
    check(
        "secret path refused",
        ops.refuse_code("/api/crm/package-intel/operator-depth/secret-mint")
        == "secret_refused",
    )
    check(
        "staff ready path refused",
        ops.refuse_code("/api/crm/package-intel/operator-depth/staff-ready")
        == "staff_ready_refused",
    )
    slot = "PKG-CHANNEL"
    check("slot tail allowed", ops.refuse_code(f"/api/crm/package-intel/operator-depth/objects/{slot}") is None)
    try:
        ops.require_seat(None)
        check("anon seat", False, "allowed")
    except ops.PackageDepthError as exc:
        check("anon seat", exc.code == "denied" and exc.http_status == 403, exc.code)
    try:
        ops.require_seat("PERS-DEVI")
        check("devi seat", False, "allowed")
    except ops.PackageDepthError as exc:
        check("devi seat", exc.code == "outsider" and exc.http_status == 403, exc.code)
    try:
        ops.require_seat("PERS-OUTSIDER")
        check("outsider seat", False, "allowed")
    except ops.PackageDepthError as exc:
        check("outsider seat", exc.code == "outsider", exc.code)
    owner = ops.require_seat("PERS-MATT")
    check("owner seat", owner.get("seat") == "owner" and owner.get("invented_permission_grant") is False)
    for pid, label in (("PERS-AMANDA", "amanda"), ("PERS-HAIKAL", "haikal"), ("PERS-MISA", "misa")):
        seat = ops.require_seat(pid)
        check(
            f"{label} existing seat",
            seat.get("seat") == "crm" and seat.get("invented_permission_grant") is False,
            str(seat),
        )
    prove = ops.prove_rbac(person_id="PERS-AMANDA")
    check("amanda operator", prove.get("can_package_operator") is True)
    check("amanda note", (prove.get("actions") or {}).get("note") is True)
    check("amanda review", (prove.get("actions") or {}).get("review_decision") is True)
    check("amanda census refused", (prove.get("actions") or {}).get("live_census") is False)
    check("amanda price refused", (prove.get("actions") or {}).get("price_as_market") is False)
    check("amanda booking refused", (prove.get("actions") or {}).get("live_booking") is False)
    check("amanda habitat refused", (prove.get("actions") or {}).get("habitat_cutover") is False)
    check("amanda klaviyo refused", (prove.get("actions") or {}).get("klaviyo_write") is False)
    check("amanda compose refused", (prove.get("actions") or {}).get("bzg_compose") is False)
    check("amanda staff_ready refused", (prove.get("actions") or {}).get("staff_ready") is False)
    src = MODULE.read_text(encoding="utf-8")
    check("module no subprocess", "subprocess" not in src)
    check("module does not bind 8787", "8787" not in src)
    check("module no completion update", "UPDATE wolf_completion" not in src)
    serve = SERVE.read_text(encoding="utf-8")
    check("route registered", "/api/crm/package-intel/operator-depth" in serve)
    check("page anchor file", 'id="package-intel-depth"' in HTML.read_text(encoding="utf-8"))
    cluster_html = HTML_CLUSTER.read_text(encoding="utf-8")
    check("cluster links depth", "operator_depth_href" in cluster_html)
    page = HTML.read_text(encoding="utf-8")
    check("page not a price", "not a price" in page and "No booking" in page)
    check("page specified", "CAP-CRM-03 stays SPECIFIED" in page)
    check("page does not resolve", "does not resolve" in page)


def test_desk_actions() -> None:
    ledger_before = LEDGER.read_bytes()
    assign_before = _assign_count()
    cr_ids = (*nye.CRM_TARGET_CRS, *ops.PROGRESS_CRS, *ops.NAV_CRS)
    cr_before = {cr: _cr(cr) for cr in cr_ids}
    live_register = pkg.DEFAULT_DB
    live_existed = live_register.is_file()
    with tempfile.TemporaryDirectory(prefix="crm-pkg-depth-") as tmp:
        root = Path(tmp)
        events = root / "events.jsonl"
        desk = ops.operator_depth_desk(verified_person_id="PERS-MATT", events_file=events)
        check("desk ok", desk.get("ok") is True and desk.get("empty") is True)
        check("desk slots", desk.get("slot_count") == 6, str(desk.get("slot_count")))
        check("desk recorded 0", desk.get("recorded_count") == 0)
        check(
            "desk metrics null",
            desk.get("price") is None
            and desk.get("margin") is None
            and desk.get("pricing_is_truth") is False
            and desk.get("market_package_count") is None
            and desk.get("live_census") is False
            and desk.get("live_booking_write") is False
            and desk.get("habitat_cutover") is False
            and desk.get("klaviyo_write") is False
            and desk.get("guest_blast") is False,
        )
        check("desk staff_ready", desk.get("staff_ready") is False)
        check("desk chain", desk.get("chain") == list(ops.CHAIN))
        check(
            "desk crm refresh",
            (desk.get("crm_desk") or {}).get("module_count") == 4
            and (desk.get("crm_desk") or {}).get("caps_raised") is False
            and (desk.get("crm_desk") or {}).get("register_mutated") is False,
            str((desk.get("crm_desk") or {}).get("module_count")),
        )
        check(
            "desk needs you",
            isinstance((desk.get("needs_you") or {}).get("count"), int)
            and (desk.get("needs_you") or {}).get("in_scope") is True
            and (desk.get("needs_you") or {}).get("staff_ready") is False
            and (desk.get("needs_you") or {}).get("duplicate_mutate_surface") is False,
            str(desk.get("needs_you"))[:240],
        )
        ids = {row.get("object_id") for row in desk.get("objects") or []}
        check("empty object", ops.EMPTY_ID in ids)
        check("channel object", "PKG-CHANNEL" in ids)
        check("margin object", "PKG-MARGIN-NOTE" in ids)
        check("evidence object", "PKG-EVIDENCE" in ids)
        check("owner object", "PKG-OWNER" in ids)
        check("due object", "PKG-DUE" in ids)
        check("package slot object", "PKG-SLOT" in ids)
        for slot in desk.get("slots") or []:
            check(
                f"slot {slot.get('slot')} empty",
                slot.get("empty") is True and slot.get("price") is None and slot.get("margin") is None,
                str(slot.get("slot_state")),
            )
        detail = ops.object_detail(
            "PKG-MARGIN-NOTE",
            verified_person_id="PERS-MATT",
            events_file=events,
        )
        check(
            "margin detail",
            detail.get("empty") is True
            and detail.get("margin") is None
            and detail.get("pricing_is_truth") is False
            and detail.get("cap_state") == "SPECIFIED",
            str(detail.get("cap_state")),
        )
        channel = ops.object_detail(
            "PKG-CHANNEL",
            verified_person_id="PERS-HAIKAL",
            events_file=events,
        )
        check(
            "haikal channel",
            channel.get("ok") is True
            and channel.get("channel") is None
            and (channel.get("seat") or {}).get("person_id") == "PERS-HAIKAL",
        )
        haikal_desk = ops.operator_depth_desk(
            verified_person_id="PERS-HAIKAL",
            events_file=events,
        )
        check(
            "haikal nye out",
            (haikal_desk.get("needs_you") or {}).get("in_scope") is False,
            str(haikal_desk.get("needs_you"))[:180],
        )
        touched = ops.record_operator_action(
            ops.EMPTY_ID,
            verified_person_id="PERS-MATT",
            kind="next-action-touch",
            note=NOTE,
            events_file=events,
        )
        check("touch kind", touched.get("kind") == "next_action")
        check("touch register unchanged", touched.get("register_unchanged") is True)
        check("touch register flag", touched.get("register_mutated") is False)
        check("touch price null", touched.get("price") is None and touched.get("margin") is None)
        check("touch census false", touched.get("live_census") is False)
        check("touch booking false", touched.get("live_booking_write") is False)
        check(
            "touch crm desk",
            (touched.get("crm_desk") or {}).get("module_count") == 4
            and (touched.get("crm_desk") or {}).get("caps_raised") is False,
        )
        check(
            "touch needs you",
            (touched.get("needs_you") or {}).get("in_scope") is True
            and (touched.get("needs_you") or {}).get("staff_ready") is False,
        )
        reviewed = ops.record_operator_action(
            "PKG-DUE",
            verified_person_id="PERS-AMANDA",
            kind="review-decision",
            decision="still_specified",
            events_file=events,
        )
        check("amanda review", reviewed.get("decision") == "still_specified" and reviewed.get("ok") is True)
        check("amanda no grant", (reviewed.get("seat") or {}).get("invented_permission_grant") is False)
        noted = ops.record_operator_action(
            "PKG-EVIDENCE",
            verified_person_id="PERS-MISA",
            kind="note",
            note="Evidence slot stays empty until a register row exists.",
            events_file=events,
        )
        check("misa note", noted.get("kind") == "note" and noted.get("register_mutated") is False)
        handed = ops.record_operator_action(
            "PKG-OWNER",
            verified_person_id="PERS-MATT",
            kind="handoff-touch",
            note="Handoff stays on the package desk.",
            events_file=events,
        )
        check("handoff", handed.get("kind") == "handoff_touch")
        dismissed = ops.record_operator_action(
            "PKG-CHANNEL",
            verified_person_id="PERS-MATT",
            kind="dismiss-noise",
            events_file=events,
        )
        check("dismiss", dismissed.get("kind") == "dismiss_noise" and dismissed.get("price") is None)
        kept = ops.record_operator_action(
            "PKG-SLOT",
            verified_person_id="PERS-MATT",
            kind="review_decision",
            decision="not_market_truth",
            events_file=events,
        )
        check("not market", kept.get("decision") == "not_market_truth" and kept.get("price_as_market") is False)
        separate = ops.record_operator_action(
            ops.DESK_OBJECT_ID,
            verified_person_id="PERS-MATT",
            kind="review-decision",
            decision="keep_as_note",
            events_file=events,
        )
        check("keep note", separate.get("decision") == "keep_as_note")
        after = ops.operator_depth_desk(verified_person_id="PERS-MATT", events_file=events)
        check("still empty", after.get("empty") is True and after.get("recorded_count") == 0)
        check("still no file" if not live_existed else "live file stayed", (not live_register.is_file()) or live_existed)
        for kind, code in (
            ("proven", "proven_refused"),
            ("ready", "ready_refused"),
            ("staff_ready", "staff_ready_refused"),
            ("price-as-market", "price_as_market_refused"),
            ("invent-live-census", "live_census_refused"),
            ("invent-booking", "live_booking_refused"),
            ("habitat-cutover", "habitat_refused"),
            ("klaviyo-write", "klaviyo_refused"),
            ("payment", "payment_refused"),
            ("guest-blast", "guest_blast_refused"),
            ("public-post", "public_post_refused"),
            ("bzg-compose", "bzg_compose_refused"),
            ("access-include", "access_refused"),
            ("secret-mint", "secret_refused"),
            ("money", "money_refused"),
            ("resolve", "resolve_refused"),
            ("production", "production_refused"),
            ("alchemist-write", "alchemist_refused"),
        ):
            _refused(kind, code)
        try:
            ops.record_operator_action(
                ops.EMPTY_ID,
                verified_person_id="PERS-MATT",
                kind="note",
                note="This note says proven.",
                events_file=events,
            )
            check("banned note", False, "accepted")
        except ops.PackageDepthError as exc:
            check("banned note", exc.code == "refused_field" and exc.http_status == 403, exc.code)
        try:
            ops.record_operator_action(
                ops.EMPTY_ID,
                verified_person_id="PERS-MATT",
                kind="review-decision",
                decision="proven",
                events_file=events,
            )
            check("banned decision", False, "accepted")
        except ops.PackageDepthError as exc:
            check("banned decision", exc.code == "proven_refused", exc.code)
        try:
            ops.record_operator_action(
                ops.EMPTY_ID,
                verified_person_id="PERS-MATT",
                kind="note",
                body={"price": 10, "note": NOTE},
                events_file=events,
            )
            check("banned body", False, "accepted")
        except ops.PackageDepthError as exc:
            check("banned body", exc.http_status == 403, exc.code)
        try:
            ops.record_operator_action(
                "NO-SUCH",
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                events_file=events,
            )
            check("missing object", False, "accepted")
        except ops.PackageDepthError as exc:
            check("missing object", exc.code == "not_found" and exc.http_status == 404, exc.code)
        db = root / "packages.sqlite"
        row = pkg.register_product(VALID, person_id="PERS-MATT", db_path=db)
        before_bytes = db.read_bytes()
        filled = ops.operator_depth_desk(
            verified_person_id="PERS-MATT",
            events_file=events,
            db_path=db,
        )
        check("filled not empty", filled.get("empty") is False and filled.get("recorded_count") == 1)
        check("filled price null", filled.get("price") is None and filled.get("margin") is None)
        check("filled census false", filled.get("live_census") is False and filled.get("market_package_count") is None)
        by_slot = {item.get("slot"): item for item in filled.get("slots") or []}
        check("package slot named", (by_slot.get("package") or {}).get("empty") is False)
        check("channel stays empty", (by_slot.get("channel") or {}).get("empty") is True and (by_slot.get("channel") or {}).get("channel") is None)
        check("margin stays empty", (by_slot.get("margin_note") or {}).get("empty") is True and (by_slot.get("margin_note") or {}).get("margin") is None)
        check("evidence named", (by_slot.get("evidence") or {}).get("empty") is False)
        check("due stays empty", (by_slot.get("due") or {}).get("empty") is True and (by_slot.get("due") or {}).get("due") is None)
        check("no empty placeholder", filled.get("empty_placeholder") is None)
        opened = ops.object_detail(
            row["id"],
            verified_person_id="PERS-MATT",
            events_file=events,
            db_path=db,
        )
        product = opened.get("product") or {}
        check(
            "row detail",
            opened.get("object_kind") == "package_row"
            and product.get("price") is None
            and product.get("status") == "NAMED"
            and product.get("brand") == "habitat"
            and opened.get("live_booking_write") is False,
            str(product)[:180],
        )
        try:
            ops.object_detail(ops.EMPTY_ID, verified_person_id="PERS-MATT", db_path=db, events_file=events)
            check("empty hidden when filled", False, "found")
        except ops.PackageDepthError as exc:
            check("empty hidden when filled", exc.code == "not_found", exc.code)
        acted = ops.record_operator_action(
            row["id"],
            verified_person_id="PERS-MATT",
            kind="note",
            note="Named row is not a market price.",
            events_file=events,
            db_path=db,
        )
        check(
            "row action keeps register",
            acted.get("register_unchanged") is True
            and acted.get("register_mutated") is False
            and db.read_bytes() == before_bytes
            and (acted.get("package_desk") or {}).get("recorded_count") == 1,
        )
        check("live register absent" if not live_existed else "live register untouched flag", not live_register.is_file() or live_existed)
    check("ledger bytes", LEDGER.read_bytes() == ledger_before)
    check("assignments", _assign_count() == assign_before)
    for cr, state in cr_before.items():
        check(f"cr unchanged {cr}", _cr(cr) == state, f"{state}->{_cr(cr)}")
    ledger = _ledger()
    check("ledger cap 03", ledger["CAP-CRM-03"][0] == "SPECIFIED")
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
    st, anon = http("GET", "/api/crm/package-intel/operator-depth")
    check("anon 403", st == 403, str(anon)[:180])
    st, desk = http(
        "GET",
        "/api/crm/package-intel/operator-depth",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "owner desk",
        st == 200
        and isinstance(desk, dict)
        and desk.get("ok") is True
        and desk.get("empty") is True
        and desk.get("staff_ready") is False
        and desk.get("price") is None
        and desk.get("margin") is None
        and desk.get("live_census") is False
        and desk.get("slot_count") == 6
        and desk.get("recorded_count") == 0,
        str(desk)[:240],
    )
    check(
        "owner cap",
        isinstance(desk, dict)
        and ((desk.get("honesty") or {}).get("cap_crm_03") == "SPECIFIED")
        and (desk.get("honesty") or {}).get("cr_state") == "OPEN",
        str((desk.get("honesty") or {}).get("cap_crm_03")),
    )
    st, rbac = http(
        "GET",
        "/api/crm/package-intel/operator-depth/rbac",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "owner rbac",
        st == 200 and isinstance(rbac, dict) and rbac.get("can_package_operator") is True,
        str(rbac)[:180],
    )
    for email, label in (
        (AMANDA, "amanda"),
        (HAIKAL, "haikal"),
        (MISA, "misa"),
    ):
        st, body = http(
            "GET",
            "/api/crm/package-intel/operator-depth/desk",
            headers={"X-Wolf-Subject": email},
        )
        check(
            f"{label} existing seat",
            st == 200
            and isinstance(body, dict)
            and (body.get("seat") or {}).get("seat") == "crm"
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
            "/api/crm/package-intel/operator-depth",
            headers={"X-Wolf-Subject": email},
        )
        check(f"{label} 403", st == 403, str(body)[:160])
    st, detail = http(
        "GET",
        "/api/crm/package-intel/operator-depth/objects/PKG-MARGIN-NOTE",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "detail",
        st == 200
        and isinstance(detail, dict)
        and detail.get("live_census") is False
        and detail.get("margin") is None
        and detail.get("price") is None
        and detail.get("cap_state") == "SPECIFIED",
        str(detail)[:220],
    )
    st, touch = http(
        "POST",
        "/api/crm/package-intel/operator-depth/objects/EMPTY-CRM-PKG/next-action-touch",
        body={"note": "Live Beta touch. Package slots stay empty."},
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "action refresh",
        st == 200
        and isinstance(touch, dict)
        and touch.get("kind") == "next_action"
        and touch.get("register_mutated") is False
        and (touch.get("needs_you") or {}).get("staff_ready") is False
        and (touch.get("crm_desk") or {}).get("caps_raised") is False
        and touch.get("price") is None
        and touch.get("live_census") is False
        and touch.get("live_booking_write") is False
        and touch.get("klaviyo_write") is False
        and touch.get("guest_blast") is False
        and touch.get("bzg_compose") is False,
        str(touch)[:280],
    )
    for path, code, label in (
        ("/api/crm/package-intel/operator-depth/proven", "proven_refused", "proven refuse"),
        (
            "/api/crm/package-intel/operator-depth/invent-live-census",
            "live_census_refused",
            "census refuse",
        ),
        (
            "/api/crm/package-intel/operator-depth/invent-booking",
            "live_booking_refused",
            "booking refuse",
        ),
        (
            "/api/crm/package-intel/operator-depth/price-as-market",
            "price_as_market_refused",
            "price refuse",
        ),
        (
            "/api/crm/package-intel/operator-depth/habitat-cutover",
            "habitat_refused",
            "habitat refuse",
        ),
        (
            "/api/crm/package-intel/operator-depth/klaviyo-write",
            "klaviyo_refused",
            "klaviyo refuse",
        ),
        (
            "/api/crm/package-intel/operator-depth/bzg-compose",
            "bzg_compose_refused",
            "compose refuse",
        ),
        (
            "/api/crm/package-intel/operator-depth/guest-blast",
            "guest_blast_refused",
            "guest blast refuse",
        ),
    ):
        st, refused = http("POST", path, body={"note": NOTE}, headers={"X-Wolf-Subject": MATT})
        check(
            label,
            st == 403 and isinstance(refused, dict) and refused.get("error") == code,
            str(refused)[:180],
        )
    st, page = http("GET", "/crm-package-intel", headers={"X-Wolf-Subject": MATT})
    raw = page if isinstance(page, str) else json.dumps(page)
    check(
        "page",
        st == 200 and "package-intel-depth" in raw and "CAP-CRM-03 stays SPECIFIED" in raw,
        str(st),
    )
    st, amanda_page = http("GET", "/crm-package-intel", headers={"X-Wolf-Subject": AMANDA})
    amanda_raw = amanda_page if isinstance(amanda_page, str) else json.dumps(amanda_page)
    check(
        "amanda page",
        st == 200 and "package-intel-depth" in amanda_raw,
        str(amanda_page)[:160],
    )
    st, prod = http("GET", "/api/crm/package-intel/operator-depth", base=PROD)
    check("prod 404", st == 404, str(prod)[:120])
    check("live ledger unchanged", LEDGER.read_bytes() == ledger_before)
    check("live assignments unchanged", _assign_count() == assign_before)
    for cr in nye.CRM_TARGET_CRS:
        check(f"live crm {cr}", _cr(cr) == "OPEN", str(_cr(cr)))
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
    raise SystemExit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
