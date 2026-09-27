#!/usr/bin/env python3
"""MSC asset operator depth — Owner detail/actions, no invented inventory."""
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
os.environ.pop("WOLF_MSC_ASSET_DB", None)
os.environ.pop("WOLF_MSC_ASSET_OPS_EVENTS", None)

from core import msc_asset_operator_depth as ops  # noqa: E402
from core import msc_asset_register as reg  # noqa: E402
from core import msc_mgmt_cluster as msc  # noqa: E402
from core import msc_ops_needs_you_connective as nye  # noqa: E402
from core import owner_progress_needs_you_depth as progress  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
AU_FILE = ROOT / "state" / "model-e-au-discovery.json"
HTML_CLUSTER = ROOT / "dashboards" / "msc-mgmt-cluster.html"
HTML_ASSETS = ROOT / "dashboards" / "msc-assets.html"
MODULE = SCRIPTS / "core" / "msc_asset_operator_depth.py"
SERVE = SCRIPTS / "serve_beta.py"
BETA = "http://127.0.0.1:8788"
PROD = "http://127.0.0.1:8787"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
NOTE = "Owner touch only. Service was not proved."
VALID = {
    "venue": "LOC-ATRIUM-LOMBOK",
    "type": "pump",
    "status": "NOTED",
    "last_service": "Owner note only. Service was not proved.",
}
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
MSC_CRS = nye.MSC_TARGET_CRS
PROGRESS_CRS = progress.TARGET_CRS


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
        with urlopen(req, timeout=20) as resp:
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


def _ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_honesty_and_rbac() -> None:
    flags = ops.honesty_flags()
    check("01 bound", flags.get("bound") == "beta-core-safe")
    check("02 schema", flags.get("schema_id") == ops.SCHEMA_ID)
    check("03 claim", flags.get("claim_id") == "bf-msc-asset-operator-depth-20260923")
    check("04 proven false", flags.get("proven") is False)
    check("05 ready false", flags.get("ready") is False)
    check("06 staff_ready false", flags.get("staff_ready") is False)
    check("07 inventory not complete", flags.get("inventory_complete") is False)
    check("08 inventory count null", flags.get("inventory_count") is None)
    check("09 compliance not done", flags.get("compliance_done") is False)
    check("10 mfa not live", flags.get("mfa_live") is False)
    check("11 legal hold inactive", flags.get("legal_hold_active") is False)
    check("12 haikal not started", flags.get("haikal_human") == "not_started")
    check("13 devi parked", flags.get("devi_retest") == "parked")
    check("14 no permission grant", flags.get("invented_permission_grant") is False)
    check("15 no bzg compose", flags.get("bzg_compose") is False)
    check("16 no secret mint", flags.get("secret_mint") is False)
    check("17 no access mutate", flags.get("cf_access_include_mutated") is False)
    check("18 intg not reopened", flags.get("intg_reopened") is False)
    check("19 cap 01 specified", flags.get("cap_msc_01") == "SPECIFIED", str(flags.get("caps")))
    check("20 cap 02 built", flags.get("cap_msc_02") == "BUILT")
    check("21 cap 03 specified", (flags.get("caps") or {}).get("CAP-MSC-03") == "SPECIFIED")
    check("22 cap 04 specified", (flags.get("caps") or {}).get("CAP-MSC-04") == "SPECIFIED")
    check("23 cap 05 specified", (flags.get("caps") or {}).get("CAP-MSC-05") == "SPECIFIED")
    check("24 au not started", flags.get("au_msc_02_cf_doors") == "NOT STARTED")
    check("25 ceiling specified", flags.get("maturity_ceiling") == "SPECIFIED")
    for cr in MSC_CRS:
        check(f"26 msc {cr} open", (flags.get("msc_crs") or {}).get(cr) == "OPEN", str((flags.get("msc_crs") or {}).get(cr)))
    for cr in PROGRESS_CRS:
        check(
            f"27 progress {cr} open",
            (flags.get("progress_core_crs") or {}).get(cr) == "OPEN",
            str((flags.get("progress_core_crs") or {}).get(cr)),
        )

    shell_flags = shell.honesty_flags()
    check("28 shell flag", shell_flags.get("msc_asset_operator_depth") is True)
    check("29 shell staff_ready false", shell_flags.get("staff_ready") is False)

    schema = ops.schema_document()
    check("30 schema no inventory", schema.get("inventory_complete_accepted") is False)
    check("31 schema no mfa", schema.get("mfa_live_accepted") is False)
    check("32 empty id", schema.get("empty_object_id") == ops.EMPTY_ID)

    check("33 desk not refused", ops.refuse_code("/api/msc/assets/operator-depth") is None)
    check("34 rbac not refused", ops.refuse_code("/api/msc/mgmt-cluster/operator-depth/rbac") is None)
    check("35 register not this refuse", ops.refuse_code("/api/msc/assets/register") is None)
    check(
        "36 proven refused",
        ops.refuse_code("/api/msc/assets/operator-depth/proven") == "proven_refused",
    )
    check(
        "37 inventory refused",
        ops.refuse_code("/api/msc/assets/operator-depth/inventory-complete") == "inventory_refused",
    )
    check(
        "38 compliance refused",
        ops.refuse_code("/api/msc/mgmt-cluster/operator-depth/compliance-done") == "compliance_refused",
    )
    check(
        "39 mfa refused",
        ops.refuse_code("/api/msc/assets/operator-depth/mfa-live") == "mfa_refused",
    )
    check(
        "40 legal hold refused",
        ops.refuse_code("/api/msc/assets/operator-depth/legal-hold") == "legal_hold_refused",
    )
    check(
        "41 compose refused",
        ops.refuse_code("/api/msc/mgmt-cluster/operator-depth/bzg-compose") == "bzg_compose_refused",
    )
    check(
        "42 access refused",
        ops.refuse_code("/api/msc/assets/operator-depth/access-include") == "access_refused",
    )
    check(
        "43 secret refused",
        ops.refuse_code("/api/msc/assets/operator-depth/secret-mint") == "secret_refused",
    )
    check(
        "44 money refused",
        ops.refuse_code("/api/msc/assets/operator-depth/money") == "money_refused",
    )
    check(
        "45 staff ready refused",
        ops.refuse_code("/api/msc/assets/operator-depth/staff-ready") == "staff_ready_refused",
    )
    check(
        "46 production refused",
        ops.refuse_code("/api/msc/assets/operator-depth/production") == "production_refused",
    )

    serve = SERVE.read_text(encoding="utf-8")
    check("47 serve route", "/api/msc/assets/operator-depth" in serve)
    check("48 serve cluster route", "/api/msc/mgmt-cluster/operator-depth" in serve)
    cluster_html = HTML_CLUSTER.read_text(encoding="utf-8")
    assets_html = HTML_ASSETS.read_text(encoding="utf-8")
    check("49 cluster panel", 'id="asset-depth"' in cluster_html)
    check("50 assets panel", 'id="asset-depth"' in assets_html)
    check(
        "51 no orphan dashboard",
        not (ROOT / "dashboards" / "msc-asset-operator-depth.html").exists(),
    )
    check("52 module present", MODULE.is_file())

    try:
        ops.require_seat(None)
        check("53 anon seat refused", False)
    except ops.AssetDepthError as exc:
        check("53 anon seat refused", exc.code == "denied" and exc.http_status == 403)
    try:
        ops.require_seat("PERS-HAIKAL")
        check("54 haikal seat refused", False)
    except ops.AssetDepthError as exc:
        check("54 haikal seat refused", exc.code == "outsider")
    try:
        ops.require_seat("PERS-DEVI")
        check("55 devi seat refused", False)
    except ops.AssetDepthError as exc:
        check("55 devi seat refused", exc.code == "outsider")
    seat = ops.require_seat("PERS-MATT")
    check("56 owner seat", seat.get("seat") == "owner" and seat.get("invented_permission_grant") is False)
    rbac = ops.prove_rbac(person_id="PERS-MATT")
    check("57 rbac note", (rbac.get("actions") or {}).get("note") is True)
    check("58 rbac inventory false", (rbac.get("actions") or {}).get("inventory_complete") is False)
    check("59 rbac compose false", (rbac.get("actions") or {}).get("bzg_compose") is False)
    check("60 rbac access false", (rbac.get("actions") or {}).get("access_include") is False)


def test_desk_actions() -> None:
    au_before = AU_FILE.read_bytes()
    ledger_before = LEDGER.read_bytes()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        empty_db = root / "empty.sqlite"
        events = root / "events.jsonl"
        empty = ops.operator_depth_desk(
            verified_person_id="PERS-MATT",
            db_path=empty_db,
            events_file=events,
        )
        check("61 empty desk", empty.get("empty") is True and empty.get("ok") is True)
        check("62 empty not inventory", empty.get("inventory_count") is None and empty.get("inventory_complete") is False)
        check("63 placeholder present", (empty.get("empty_placeholder") or {}).get("object_id") == ops.EMPTY_ID)
        check("64 no asset rows", empty.get("asset_count") == 0)
        check("65 msc objects", len(empty.get("msc_objects") or []) == 5)
        check("66 needs you refresh", isinstance(empty.get("needs_you"), dict))
        check("67 msc desk refresh", (empty.get("msc_desk") or {}).get("module_count") == 5)
        check("68 desk staff_ready false", empty.get("staff_ready") is False)
        check("69 desk cap ceiling", (empty.get("honesty") or {}).get("cap_msc_01") == "SPECIFIED")

        detail = ops.object_detail(
            ops.EMPTY_ID,
            verified_person_id="PERS-MATT",
            db_path=empty_db,
            events_file=events,
        )
        check("70 empty detail", detail.get("object_kind") == "empty_placeholder" and detail.get("service_proved") is False)
        note = ops.record_operator_action(
            ops.EMPTY_ID,
            verified_person_id="PERS-MATT",
            kind="note",
            note=NOTE,
            db_path=empty_db,
            events_file=events,
        )
        check("71 empty note recorded", note.get("ok") is True and note.get("kind") == "note")
        check("72 register unchanged", note.get("register_rows_unchanged") is True and note.get("register_mutated") is False)
        check("73 note refreshes desk", isinstance(note.get("msc_desk"), dict) and isinstance(note.get("needs_you"), dict))
        check("74 note no inventory", note.get("inventory_complete") is False and note.get("inventory_count") is None)
        nxt = ops.record_operator_action(
            ops.EMPTY_ID,
            verified_person_id="PERS-MATT",
            kind="next-action-touch",
            note="Next touch stays a note.",
            db_path=empty_db,
            events_file=events,
        )
        check("75 next action", nxt.get("kind") == "next_action" and nxt.get("register_mutated") is False)
        hand = ops.record_operator_action(
            "MSC-DESK-cyber_baseline",
            verified_person_id="PERS-MATT",
            kind="handoff-touch",
            note="Handoff touch only. MFA stays unread.",
            db_path=empty_db,
            events_file=events,
        )
        check("76 handoff", hand.get("kind") == "handoff_touch" and hand.get("mfa_live") is False)
        review = ops.record_operator_action(
            "MSC-DESK-compliance_pack",
            verified_person_id="PERS-MATT",
            kind="review-decision",
            decision="still_specified",
            note="Still specified.",
            db_path=empty_db,
            events_file=events,
        )
        check("77 review still specified", review.get("decision") == "still_specified" and review.get("compliance_done") is False)
        kept = ops.record_operator_action(
            "MSC-DESK-records_defensibility",
            verified_person_id="PERS-MATT",
            kind="review_decision",
            decision="keep_as_note",
            db_path=empty_db,
            events_file=events,
        )
        check("78 keep as note", kept.get("decision") == "keep_as_note" and kept.get("legal_hold_active") is False)
        try:
            ops.record_operator_action(
                ops.EMPTY_ID,
                verified_person_id="PERS-MATT",
                kind="review-decision",
                decision="inventory_complete",
                db_path=empty_db,
                events_file=events,
            )
            check("79 inventory decision refused", False)
        except ops.AssetDepthError as exc:
            check("79 inventory decision refused", exc.code == "inventory_refused" and exc.http_status == 403)
        try:
            ops.record_operator_action(
                "MSC-DESK-cyber_baseline",
                verified_person_id="PERS-MATT",
                kind="review-decision",
                decision="mfa_live",
                db_path=empty_db,
                events_file=events,
            )
            check("80 mfa decision refused", False)
        except ops.AssetDepthError as exc:
            check("80 mfa decision refused", exc.code == "mfa_refused")
        try:
            ops.record_operator_action(
                ops.EMPTY_ID,
                verified_person_id="PERS-MATT",
                kind="proven",
                note=NOTE,
                db_path=empty_db,
                events_file=events,
            )
            check("81 proven kind refused", False)
        except ops.AssetDepthError as exc:
            check("81 proven kind refused", exc.code == "proven_refused")
        try:
            ops.record_operator_action(
                ops.EMPTY_ID,
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"inventory_complete": True, "note": NOTE, "kind": "note"},
                db_path=empty_db,
                events_file=events,
            )
            check("82 inventory field refused", False)
        except ops.AssetDepthError as exc:
            check("82 inventory field refused", exc.code == "inventory_refused")
        try:
            ops.record_operator_action(
                ops.EMPTY_ID,
                verified_person_id="PERS-MATT",
                kind="note",
                note="12 units on the floor",
                db_path=empty_db,
                events_file=events,
            )
            check("83 count note refused", False)
        except ops.AssetDepthError as exc:
            check("83 count note refused", exc.code == "inventory_refused")
        try:
            ops.record_operator_action(
                ops.EMPTY_ID,
                verified_person_id="PERS-HAIKAL",
                kind="note",
                note=NOTE,
                db_path=empty_db,
                events_file=events,
            )
            check("84 outsider action refused", False)
        except ops.AssetDepthError as exc:
            check("84 outsider action refused", exc.code == "outsider")
        dismissed = ops.record_operator_action(
            ops.EMPTY_ID,
            verified_person_id="PERS-MATT",
            kind="dismiss-noise",
            note="Noise only.",
            db_path=empty_db,
            events_file=events,
        )
        check("85 dismiss", dismissed.get("kind") == "dismiss_noise" and dismissed.get("register_mutated") is False)
        after = ops.operator_depth_desk(
            verified_person_id="PERS-MATT",
            db_path=empty_db,
            events_file=events,
        )
        placeholder = after.get("empty_placeholder") or {}
        check("86 dismissed placeholder", placeholder.get("dismissed_noise") is True and after.get("empty") is True)
        check("87 still not inventory", after.get("inventory_count") is None)

        filled_db = root / "filled.sqlite"
        created = reg.register_asset(dict(VALID), person_id="PERS-MATT", db_path=filled_db)
        asset_id = created["id"]
        before_count = len(reg.list_assets(filled_db))
        filled = ops.operator_depth_desk(
            verified_person_id="PERS-MATT",
            db_path=filled_db,
            events_file=events,
        )
        check("88 filled not empty", filled.get("empty") is False and filled.get("asset_count") == 1)
        check("89 maintenance projected", filled.get("maintenance_count") == 1)
        check("90 no placeholder when rows", filled.get("empty_placeholder") is None)
        asset_detail = ops.object_detail(
            asset_id,
            verified_person_id="PERS-MATT",
            db_path=filled_db,
            events_file=events,
        )
        check(
            "91 asset detail note",
            asset_detail.get("object_kind") == "asset"
            and (asset_detail.get("maintenance") or {}).get("service_proved") is False,
        )
        maint_id = f"MAINT-{asset_id}"
        maint = ops.record_operator_action(
            maint_id,
            verified_person_id="PERS-MATT",
            kind="next-action-touch",
            note="Maintenance touch stays a note.",
            db_path=filled_db,
            events_file=events,
        )
        check("92 maintenance action", maint.get("object_id") == maint_id and maint.get("service_proved") is False)
        check("93 rows unchanged", len(reg.list_assets(filled_db)) == before_count and maint.get("register_rows_unchanged") is True)
        try:
            ops.object_detail(
                ops.EMPTY_ID,
                verified_person_id="PERS-MATT",
                db_path=filled_db,
                events_file=events,
            )
            check("94 placeholder hidden", False)
        except ops.AssetDepthError as exc:
            check("94 placeholder hidden", exc.code == "not_found")
        try:
            ops.record_operator_action(
                asset_id,
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"compose": True, "kind": "note", "note": NOTE},
                db_path=filled_db,
                events_file=events,
            )
            check("95 compose field refused", False)
        except ops.AssetDepthError as exc:
            check("95 compose field refused", exc.code == "bzg_compose_refused")
        try:
            ops.events_path(root / "money.sqlite")
            check("96 money path refused", False)
        except ops.AssetDepthError as exc:
            check("96 money path refused", exc.code == "money_refused")

    check("97 au file unchanged", AU_FILE.read_bytes() == au_before)
    check("98 ledger unchanged", LEDGER.read_bytes() == ledger_before)
    for cr in MSC_CRS:
        check(f"99 cr {cr} still open", _cr(cr) == "OPEN", str(_cr(cr)))
    ledger = _ledger()
    check("100 ledger cap 01", ledger["CAP-MSC-01"][0] == "SPECIFIED")
    check("101 ledger cap 02", ledger["CAP-MSC-02"][0] == "BUILT")


def test_live() -> None:
    check("102 port 8788", port_up(8788))
    check("103 port 8787", port_up(8787))
    if not port_up(8788):
        for name in (
            "104 anon 403",
            "105 owner desk",
            "106 owner rbac",
            "107 outsider 403",
            "108 haikal 403",
            "109 devi 403",
            "110 cluster desk",
            "111 detail",
            "112 action refresh",
            "113 inventory refuse",
            "114 proven refuse",
            "115 page cluster",
            "116 page assets",
            "117 prod 404",
        ):
            check(name, False, "beta down")
        return

    st, anon = http("GET", "/api/msc/assets/operator-depth")
    check("104 anon 403", st == 403, str(anon)[:180])
    st, desk = http(
        "GET",
        "/api/msc/assets/operator-depth",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "105 owner desk",
        st == 200 and desk.get("ok") is True and desk.get("staff_ready") is False and desk.get("inventory_count") is None,
        str(desk)[:240],
    )
    check(
        "105b owner caps",
        ((desk.get("honesty") or {}).get("caps") or {}).get("CAP-MSC-01") == "SPECIFIED"
        and ((desk.get("honesty") or {}).get("caps") or {}).get("CAP-MSC-02") == "BUILT"
        and (desk.get("honesty") or {}).get("au_msc_02_cf_doors") == "NOT STARTED",
        str((desk.get("honesty") or {}).get("caps")),
    )
    st, rbac = http(
        "GET",
        "/api/msc/assets/operator-depth/rbac",
        headers={"X-Wolf-Subject": MATT},
    )
    check("106 owner rbac", st == 200 and rbac.get("can_asset_operator") is True, str(rbac)[:180])
    st, out = http(
        "GET",
        "/api/msc/assets/operator-depth",
        headers={"X-Wolf-Subject": OUTSIDER},
    )
    check("107 outsider 403", st == 403, str(out)[:160])
    st, haikal = http(
        "GET",
        "/api/msc/mgmt-cluster/operator-depth",
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("108 haikal 403", st == 403, str(haikal)[:160])
    st, devi = http(
        "GET",
        "/api/msc/assets/operator-depth/rbac",
        headers={"X-Wolf-Subject": DEVI},
    )
    check("109 devi 403", st == 403, str(devi)[:160])
    st, cluster = http(
        "GET",
        "/api/msc/mgmt-cluster/operator-depth",
        headers={"X-Wolf-Subject": MATT},
    )
    check("110 cluster desk", st == 200 and cluster.get("schema_id") == ops.SCHEMA_ID, str(cluster)[:180])
    objects = cluster.get("objects") or []
    target = None
    if cluster.get("empty"):
        target = ops.EMPTY_ID
    elif objects:
        target = objects[0].get("object_id")
    if target:
        st, detail = http(
            "GET",
            f"/api/msc/assets/operator-depth/objects/{target}",
            headers={"X-Wolf-Subject": MATT},
        )
        check(
            "111 detail",
            st == 200 and detail.get("inventory_complete") is False and detail.get("service_proved") is False,
            str(detail)[:220],
        )
        st, touch = http(
            "POST",
            f"/api/msc/mgmt-cluster/operator-depth/objects/{target}/next-action-touch",
            body={"note": "Live Beta touch. Not an inventory count."},
            headers={"X-Wolf-Subject": MATT},
        )
        check(
            "112 action refresh",
            st == 200
            and touch.get("kind") == "next_action"
            and touch.get("register_mutated") is False
            and isinstance(touch.get("needs_you"), dict)
            and isinstance(touch.get("msc_desk"), dict),
            str(touch)[:240],
        )
    else:
        check("111 detail", False, "no object")
        check("112 action refresh", False, "no object")
    st, inv = http(
        "POST",
        "/api/msc/assets/operator-depth/inventory-complete",
        body={"note": NOTE},
        headers={"X-Wolf-Subject": MATT},
    )
    check("113 inventory refuse", st == 403 and (inv.get("error") == "inventory_refused"), str(inv)[:180])
    st, proven = http(
        "GET",
        "/api/msc/assets/operator-depth/proven",
        headers={"X-Wolf-Subject": MATT},
    )
    check("114 proven refuse", st == 403 and proven.get("error") == "proven_refused", str(proven)[:180])
    st, page = http("GET", "/msc-mgmt-cluster", headers={"X-Wolf-Subject": MATT})
    check(
        "115 cluster soft-lands off the depth panel",
        st == 200
        and isinstance(page, str)
        and 'id="asset-depth"' not in page
        and "Asset operator depth" not in page,
        str(page)[:120],
    )
    st, assets_page = http("GET", "/msc-assets", headers={"X-Wolf-Subject": MATT})
    check("116 page assets", st == 200 and isinstance(assets_page, str) and 'id="asset-depth"' in assets_page)
    st, amanda = http(
        "GET",
        "/api/msc/assets/operator-depth",
        headers={"X-Wolf-Subject": AMANDA},
    )
    check("116b amanda 403", st == 403, str(amanda)[:120])
    st, misa = http(
        "GET",
        "/api/msc/assets/operator-depth",
        headers={"X-Wolf-Subject": MISA},
    )
    check("116c misa 403", st == 403, str(misa)[:120])
    st, prod = http("GET", "/api/msc/assets/operator-depth", base=PROD)
    check("117 prod depth 404", st == 404, str(prod)[:120])
    for cr in MSC_CRS:
        check(f"118 live cr {cr}", _cr(cr) == "OPEN")
    for cr in PROGRESS_CRS:
        check(f"119 live progress {cr}", _cr(cr) == "OPEN")


def test_wip_untouched(before: str) -> None:
    after = subprocess.check_output(["git", "hash-object", *WIP], cwd=str(ROOT), text=True)
    check("120 wip unchanged", before == after)
    prod_pid = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True
    ).strip().splitlines()[0]
    check("121 prod pid", prod_pid == "15975", prod_pid)


def main() -> None:
    before = subprocess.check_output(["git", "hash-object", *WIP], cwd=str(ROOT), text=True)
    test_honesty_and_rbac()
    test_desk_actions()
    test_live()
    test_wip_untouched(before)
    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAILED")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
