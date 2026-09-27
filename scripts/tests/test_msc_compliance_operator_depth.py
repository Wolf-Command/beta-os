#!/usr/bin/env python3
"""MSC compliance operator depth — Owner seat, empty pack, no invented licence."""
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
os.environ.pop("WOLF_MSC_COMPLIANCE_OPS_EVENTS", None)

from core import msc_compliance_operator_depth as ops  # noqa: E402
from core import msc_compliance_pack as pack  # noqa: E402
from core import msc_ops_needs_you_connective as nye  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HTML = ROOT / "dashboards" / "msc-compliance.html"
HTML_CLUSTER = ROOT / "dashboards" / "msc-mgmt-cluster.html"
MODULE = SCRIPTS / "core" / "msc_compliance_operator_depth.py"
SERVE = SCRIPTS / "serve_beta.py"
BETA = "http://127.0.0.1:8788"
PROD = "http://127.0.0.1:8787"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
NOTE = "Owner touch. Compliance slots stay empty."
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


def _events() -> Path:
    return Path(tempfile.gettempdir()) / f"msc-comp-depth-{os.getpid()}.jsonl"


def _refused(kind: str, code: str) -> None:
    try:
        ops.record_operator_action(
            ops.EMPTY_ID,
            verified_person_id="PERS-MATT",
            kind=kind,
            note=NOTE,
            events_file=_events(),
        )
        check(f"refuse {kind}", False, "accepted")
    except ops.ComplianceDepthError as exc:
        check(f"refuse {kind}", exc.code == code and exc.http_status == 403, exc.code)


def test_honesty_and_rbac() -> None:
    flags = ops.honesty_flags()
    check("bound", flags.get("bound") == "beta-msc-loop-safe")
    check("schema id", flags.get("schema_id") == ops.SCHEMA_ID)
    check("claim", flags.get("claim_id") == "bf-msc-compliance-operator-depth-20260923")
    check("proven false", flags.get("proven") is False)
    check("ready false", flags.get("ready") is False)
    check("staff_ready false", flags.get("staff_ready") is False)
    check("licence null", flags.get("licence_status") is None)
    check("not current", flags.get("current") is False)
    check("not proved", flags.get("compliance_proved") is False)
    check("payment null", flags.get("payment") is None)
    check("money null", flags.get("money") is None)
    check("empty not compliance", flags.get("empty_is_compliance") is False)
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
    check("pack not mutated", flags.get("pack_mutated") is False)
    check("cap 03 specified", flags.get("cap_msc_03") == "SPECIFIED", str(flags.get("cap_msc_03")))
    check("cap 01 specified", flags.get("cap_msc_01") == "SPECIFIED", str(flags.get("cap_msc_01")))
    check("cap 02 built", flags.get("cap_msc_02") == "BUILT", str(flags.get("cap_msc_02")))
    check("cap 04 specified", flags.get("cap_msc_04") == "SPECIFIED", str(flags.get("cap_msc_04")))
    check("cap 05 specified", flags.get("cap_msc_05") == "SPECIFIED", str(flags.get("cap_msc_05")))
    check("ceiling specified", flags.get("maturity_ceiling") == "SPECIFIED")
    check("skeleton ceiling built", flags.get("skeleton_ceiling") == "BUILT")
    check("au not started", flags.get("au_msc_02_cf_doors") == "NOT STARTED", str(flags.get("au_msc_02_cf_doors")))
    check("cr open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("cr id", flags.get("cr_id") == "CR-1f93c785c88e9564")
    check("false resolve false", flags.get("false_resolve_cr") is False)
    for cr in nye.MSC_TARGET_CRS:
        check(
            f"msc {cr} open",
            (flags.get("msc_crs") or {}).get(cr) == "OPEN",
            str((flags.get("msc_crs") or {}).get(cr)),
        )
    for cr in ops.PROGRESS_CRS:
        check(
            f"progress {cr} open",
            (flags.get("progress_core_crs") or {}).get(cr) == "OPEN",
            str((flags.get("progress_core_crs") or {}).get(cr)),
        )
    nav = flags.get("global_nav_crs") or {}
    check("nav rows read", set(nav) == set(ops.NAV_CRS), str(sorted(nav)))
    for cr in ops.NAV_CRS:
        expected = _cr(cr) or "OPEN"
        check(f"nav {cr} as-is", nav.get(cr) == expected, f"{nav.get(cr)} != {expected}")
    shell_flags = shell.honesty_flags()
    check("shell flag", shell_flags.get("msc_compliance_operator_depth") is True)
    check("shell staff_ready false", shell_flags.get("staff_ready") is False)
    schema = ops.schema_document()
    check("schema no licence current", schema.get("licence_current_accepted") is False)
    check("schema no compliance proved", schema.get("compliance_proved_accepted") is False)
    check("schema no payment", schema.get("payment_accepted") is False)
    check("schema no guest blast", schema.get("guest_blast_accepted") is False)
    check("schema no public post", schema.get("public_post_accepted") is False)
    check("empty id", schema.get("empty_object_id") == ops.EMPTY_ID)
    check("six slots", len(schema.get("slot_object_ids") or {}) == 6)
    check("chain", schema.get("chain") == list(ops.CHAIN))
    check("desk not refused", ops.refuse_code("/api/msc/compliance/operator-depth") is None)
    check("rbac not refused", ops.refuse_code("/api/msc/compliance/operator-depth/rbac") is None)
    check("pack payment not this refuse", ops.refuse_code("/api/msc/compliance/payment") is None)
    check(
        "proven path refused",
        ops.refuse_code("/api/msc/compliance/operator-depth/proven") == "proven_refused",
    )
    check(
        "licence current path refused",
        ops.refuse_code("/api/msc/compliance/operator-depth/invent-licence-current")
        == "licence_current_refused",
    )
    check(
        "compliance proved path refused",
        ops.refuse_code("/api/msc/compliance/operator-depth/invent-compliance-proved")
        == "compliance_proved_refused",
    )
    check(
        "compose path refused",
        ops.refuse_code("/api/msc/compliance/operator-depth/bzg-compose") == "bzg_compose_refused",
    )
    check(
        "guest blast path refused",
        ops.refuse_code("/api/msc/compliance/operator-depth/guest-blast") == "guest_blast_refused",
    )
    check(
        "public post path refused",
        ops.refuse_code("/api/msc/compliance/operator-depth/public-post") == "public_post_refused",
    )
    check(
        "access path refused",
        ops.refuse_code("/api/msc/compliance/operator-depth/access-include") == "access_refused",
    )
    check(
        "secret path refused",
        ops.refuse_code("/api/msc/compliance/operator-depth/secret-mint") == "secret_refused",
    )
    seat = ops.require_seat("PERS-MATT")
    check("owner seat", seat.get("seat") == "owner" and seat.get("invented_permission_grant") is False)
    for pid, label in (
        ("", "anon"),
        ("PERS-DEVI", "devi"),
        ("PERS-AMANDA", "amanda"),
        ("PERS-HAIKAL", "haikal"),
        ("PERS-MISA", "misa"),
        ("PERS-OUT", "outsider"),
    ):
        try:
            ops.require_seat(pid)
            check(f"seat {label} refused", False, "accepted")
        except ops.ComplianceDepthError as exc:
            check(f"seat {label} refused", exc.http_status == 403, exc.code)
    rbac = ops.prove_rbac(person_id="PERS-MATT")
    check("rbac operator", rbac.get("can_compliance_operator") is True)
    check("rbac no licence", (rbac.get("actions") or {}).get("licence_current") is False)
    check("rbac no proved", (rbac.get("actions") or {}).get("compliance_proved") is False)
    check("rbac no payment", (rbac.get("actions") or {}).get("payment") is False)
    check("rbac no compose", (rbac.get("actions") or {}).get("bzg_compose") is False)
    check("rbac no staff ready", (rbac.get("actions") or {}).get("staff_ready") is False)
    html = HTML.read_text(encoding="utf-8")
    check("panel anchor", 'id="compliance-depth"' in html)
    check("panel copy", "CAP-MSC-03 stays SPECIFIED" in html)
    check("no orphan file", not (ROOT / "dashboards" / "msc-compliance-operator-depth.html").exists())
    cluster = HTML_CLUSTER.read_text(encoding="utf-8")
    check("cluster link", "/msc-compliance#compliance-depth" in cluster)
    serve = SERVE.read_text(encoding="utf-8")
    check("serve route", "/api/msc/compliance/operator-depth" in serve)
    check("module present", MODULE.is_file())
    for kind, code in (
        ("proven", "proven_refused"),
        ("ready", "ready_refused"),
        ("staff_ready", "staff_ready_refused"),
        ("payment", "payment_refused"),
        ("bank", "bank_refused"),
        ("books", "books_refused"),
        ("alchemist-write", "alchemist_refused"),
        ("money", "money_refused"),
        ("invent-licence-current", "licence_current_refused"),
        ("invent-compliance-proved", "compliance_proved_refused"),
        ("guest-blast", "guest_blast_refused"),
        ("public-post", "public_post_refused"),
        ("access-include", "access_refused"),
        ("secret-mint", "secret_refused"),
        ("bzg-compose", "bzg_compose_refused"),
        ("production", "production_refused"),
        ("resolve", "resolve_refused"),
    ):
        _refused(kind, code)


def test_desk_actions() -> None:
    events = _events()
    if events.exists():
        events.unlink()
    stamp_before = ops._pack_stamp()
    desk = ops.operator_depth_desk(verified_person_id="PERS-MATT", events_file=events)
    check("desk ok", desk.get("ok") is True and desk.get("empty") is True)
    check("slot count", desk.get("slot_count") == 6)
    check("recorded zero", desk.get("recorded_count") == 0)
    check("licence null desk", desk.get("licence_status") is None)
    check("not proved desk", desk.get("compliance_proved") is False)
    check("payment null desk", desk.get("payment") is None)
    check("staff ready desk", desk.get("staff_ready") is False)
    check("pack not mutated desk", desk.get("pack_mutated") is False)
    check("placeholder", (desk.get("empty_placeholder") or {}).get("object_id") == ops.EMPTY_ID)
    ids = [row.get("object_id") for row in desk.get("slots") or []]
    check("slot ids", ids == list(ops.SLOT_OBJECT_IDS.values()), str(ids))
    for row in desk.get("slots") or []:
        check(
            f"slot {row.get('slot')} empty",
            row.get("empty") is True and row.get("licence_status") is None and row.get("current") is False,
        )
    chain = [item.get("slot") for item in (desk.get("objects") or []) if item.get("slot")]
    check("chain order", chain == list(ops.CHAIN), str(chain))
    nye_row = desk.get("needs_you") or {}
    check("needs you in scope", nye_row.get("in_scope") is True and nye_row.get("staff_ready") is False)
    msc = desk.get("msc_desk") or {}
    check("msc desk modules", msc.get("module_count") == 5 and msc.get("caps_raised") is False)
    hrefs = {
        row.get("id"): row.get("operator_depth_href")
        for row in (msc.get("modules") or [])
    }
    check(
        "compliance href",
        hrefs.get("compliance_pack") == "/msc-compliance#compliance-depth",
        str(hrefs.get("compliance_pack")),
    )
    detail = ops.object_detail("COMP-LICENCE", verified_person_id="PERS-MATT", events_file=events)
    check(
        "licence detail",
        detail.get("ok") is True
        and detail.get("empty") is True
        and detail.get("cap_state") == "SPECIFIED"
        and detail.get("licence_status") is None
        and detail.get("compliance_proved") is False
        and detail.get("payment") is None,
        str(detail.get("cap_state")),
    )
    for oid in ("COMP-STATUTORY", "COMP-POLICY", "COMP-EVIDENCE", "COMP-OWNER", "COMP-DUE", ops.EMPTY_ID):
        row = ops.object_detail(oid, verified_person_id="PERS-MATT", events_file=events)
        check(
            f"detail {oid}",
            row.get("empty") is True and row.get("current") is False and row.get("compliance_proved") is False,
        )
    note = ops.record_operator_action(
        "COMP-POLICY",
        verified_person_id="PERS-MATT",
        kind="note",
        note=NOTE,
        events_file=events,
    )
    check("note recorded", note.get("kind") == "note" and note.get("pack_mutated") is False)
    nxt = ops.record_operator_action(
        ops.EMPTY_ID,
        verified_person_id="PERS-MATT",
        kind="next-action-touch",
        note=NOTE,
        events_file=events,
    )
    check(
        "next refresh",
        nxt.get("kind") == "next_action"
        and nxt.get("register_unchanged") is True
        and nxt.get("pack_mutated") is False
        and (nxt.get("msc_desk") or {}).get("caps_raised") is False
        and (nxt.get("needs_you") or {}).get("staff_ready") is False
        and nxt.get("licence_status") is None
        and nxt.get("compliance_proved") is False
        and nxt.get("payment") is None
        and nxt.get("bzg_compose") is False,
        str(nxt.get("register_unchanged")),
    )
    hand = ops.record_operator_action(
        "COMP-OWNER",
        verified_person_id="PERS-MATT",
        kind="handoff-touch",
        note=NOTE,
        events_file=events,
    )
    check("handoff", hand.get("kind") == "handoff_touch" and hand.get("guest_blast") is False)
    review = ops.record_operator_action(
        "COMP-DUE",
        verified_person_id="PERS-MATT",
        kind="review-decision",
        decision="still_specified",
        events_file=events,
    )
    check(
        "review still specified",
        review.get("decision") == "still_specified" and review.get("compliance_proved") is False,
    )
    for decision in ("not_compliance_proof", "keep_as_note"):
        row = ops.record_operator_action(
            "COMP-EVIDENCE",
            verified_person_id="PERS-MATT",
            kind="review_decision",
            decision=decision,
            events_file=events,
        )
        check(f"review {decision}", row.get("decision") == decision and row.get("current") is False)
    before_open = ops.operator_depth_desk(verified_person_id="PERS-MATT", events_file=events).get("open_count")
    dismissed = ops.record_operator_action(
        "COMP-STATUTORY",
        verified_person_id="PERS-MATT",
        kind="dismiss-noise",
        events_file=events,
    )
    after = ops.operator_depth_desk(verified_person_id="PERS-MATT", events_file=events)
    check(
        "dismiss",
        dismissed.get("kind") == "dismiss_noise" and after.get("open_count") == (before_open or 0) - 1,
        f"{before_open} -> {after.get('open_count')}",
    )
    check("stamp unchanged", ops._pack_stamp() == stamp_before)
    check("pack file absent", not pack.LIVE_DEFAULT_DB.is_file())
    try:
        ops.record_operator_action(
            ops.EMPTY_ID,
            verified_person_id="PERS-MATT",
            kind="note",
            note="This pack is proven and ready",
            events_file=events,
        )
        check("banned note", False, "accepted")
    except ops.ComplianceDepthError as exc:
        check("banned note", exc.http_status == 403, exc.code)
    try:
        ops.record_operator_action(
            ops.EMPTY_ID,
            verified_person_id="PERS-MATT",
            kind="note",
            note=NOTE,
            body={"licence_status": "current"},
            events_file=events,
        )
        check("banned body", False, "accepted")
    except ops.ComplianceDepthError as exc:
        check("banned body", exc.code == "licence_current_refused" and exc.http_status == 403, exc.code)
    try:
        ops.record_operator_action(
            "MISSING",
            verified_person_id="PERS-MATT",
            kind="note",
            note=NOTE,
            events_file=events,
        )
        check("missing object", False, "accepted")
    except ops.ComplianceDepthError as exc:
        check("missing object", exc.http_status == 404, exc.code)
    try:
        ops.events_path(pack.LIVE_DEFAULT_DB)
        check("events refuse pack store", False, "accepted")
    except ops.ComplianceDepthError as exc:
        check("events refuse pack store", exc.code == "register_refused", exc.code)
    try:
        ops.events_path(ROOT / "money.sqlite")
        check("events refuse money", False, "accepted")
    except ops.ComplianceDepthError as exc:
        check("events refuse money", exc.http_status == 403, exc.code)
    ledger = _ledger()
    check("ledger cap 03", ledger["CAP-MSC-03"][0] == "SPECIFIED")
    check("ledger cap 02", ledger["CAP-MSC-02"][0] == "BUILT")
    check("ledger denominator", len(ledger) == 77, str(len(ledger)))


def test_live() -> None:
    check("port 8788", port_up(8788))
    check("port 8787", port_up(8787))
    if not port_up(8788):
        for name in (
            "anon 403",
            "owner desk",
            "owner rbac",
            "amanda 403",
            "haikal 403",
            "misa 403",
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
    st, anon = http("GET", "/api/msc/compliance/operator-depth")
    check("anon 403", st == 403, str(anon)[:180])
    st, desk = http(
        "GET",
        "/api/msc/compliance/operator-depth",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "owner desk",
        st == 200
        and isinstance(desk, dict)
        and desk.get("ok") is True
        and desk.get("empty") is True
        and desk.get("staff_ready") is False
        and desk.get("licence_status") is None
        and desk.get("compliance_proved") is False
        and desk.get("payment") is None
        and desk.get("slot_count") == 6
        and desk.get("recorded_count") == 0,
        str(desk)[:240],
    )
    check(
        "owner cap",
        isinstance(desk, dict)
        and ((desk.get("honesty") or {}).get("cap_msc_03") == "SPECIFIED")
        and (desk.get("honesty") or {}).get("cr_state") == "OPEN",
        str((desk.get("honesty") or {}).get("cap_msc_03")),
    )
    st, rbac = http(
        "GET",
        "/api/msc/compliance/operator-depth/rbac",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "owner rbac",
        st == 200 and isinstance(rbac, dict) and rbac.get("can_compliance_operator") is True,
        str(rbac)[:180],
    )
    for email, label in (
        (AMANDA, "amanda"),
        (HAIKAL, "haikal"),
        (MISA, "misa"),
        (OUTSIDER, "outsider"),
        (DEVI, "devi"),
    ):
        st, body = http(
            "GET",
            "/api/msc/compliance/operator-depth/desk",
            headers={"X-Wolf-Subject": email},
        )
        check(f"{label} 403", st == 403, str(body)[:160])
    st, detail = http(
        "GET",
        "/api/msc/compliance/operator-depth/objects/COMP-LICENCE",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "detail",
        st == 200
        and isinstance(detail, dict)
        and detail.get("empty") is True
        and detail.get("licence_status") is None
        and detail.get("compliance_proved") is False
        and detail.get("payment") is None
        and detail.get("cap_state") == "SPECIFIED",
        str(detail)[:220],
    )
    st, touch = http(
        "POST",
        "/api/msc/compliance/operator-depth/objects/EMPTY-MSC-COMP/next-action-touch",
        body={"note": "Live Beta touch. Compliance slots stay empty."},
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "action refresh",
        st == 200
        and isinstance(touch, dict)
        and touch.get("kind") == "next_action"
        and touch.get("pack_mutated") is False
        and touch.get("register_mutated") is False
        and (touch.get("needs_you") or {}).get("staff_ready") is False
        and (touch.get("msc_desk") or {}).get("caps_raised") is False
        and touch.get("licence_status") is None
        and touch.get("compliance_proved") is False
        and touch.get("payment") is None
        and touch.get("bzg_compose") is False
        and touch.get("guest_blast") is False,
        str(touch)[:280],
    )
    for path, code, label in (
        ("/api/msc/compliance/operator-depth/proven", "proven_refused", "proven refuse"),
        (
            "/api/msc/compliance/operator-depth/invent-licence-current",
            "licence_current_refused",
            "licence refuse",
        ),
        (
            "/api/msc/compliance/operator-depth/invent-compliance-proved",
            "compliance_proved_refused",
            "proved refuse",
        ),
        ("/api/msc/compliance/operator-depth/payment", "payment_refused", "payment refuse"),
        ("/api/msc/compliance/operator-depth/bzg-compose", "bzg_compose_refused", "compose refuse"),
        ("/api/msc/compliance/operator-depth/guest-blast", "guest_blast_refused", "guest blast refuse"),
        ("/api/msc/compliance/operator-depth/public-post", "public_post_refused", "public post refuse"),
        ("/api/msc/compliance/operator-depth/access-include", "access_refused", "access refuse"),
    ):
        st, refused = http("POST", path, body={"note": NOTE}, headers={"X-Wolf-Subject": MATT})
        check(
            label,
            st == 403 and isinstance(refused, dict) and refused.get("error") == code,
            str(refused)[:180],
        )
    st, page = http("GET", "/msc-compliance", headers={"X-Wolf-Subject": MATT})
    raw = page if isinstance(page, str) else json.dumps(page)
    check(
        "page",
        st == 200 and "compliance-depth" in raw and "CAP-MSC-03 stays SPECIFIED" in raw,
        str(st),
    )
    st, devi_page = http("GET", "/msc-compliance", headers={"X-Wolf-Subject": DEVI})
    check("devi page 403", st == 403, str(devi_page)[:160])
    st, put = http(
        "PUT",
        "/api/msc/compliance/operator-depth",
        body={"note": NOTE},
        headers={"X-Wolf-Subject": MATT},
    )
    check("put refused", st == 403, str(put)[:160])
    st, prod = http("GET", "/api/msc/compliance/operator-depth", base=PROD)
    check("prod 404", st == 404, str(prod)[:120])
    check("live ledger unchanged", LEDGER.read_bytes() == ledger_before)
    check("live assignments unchanged", _assign_count() == assign_before)
    check("live pack absent", not pack.LIVE_DEFAULT_DB.is_file())
    for cr in nye.MSC_TARGET_CRS:
        check(f"live msc {cr}", _cr(cr) == "OPEN", str(_cr(cr)))
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
