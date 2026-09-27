#!/usr/bin/env python3
"""CRM identity operator depth — confidence match, human review, no silent merge."""
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
os.environ.pop("WOLF_ALLOW_LIVE_CRM_IDENTITY", None)
os.environ.pop("WOLF_CRM_IDENTITY_DB", None)
os.environ.pop("WOLF_CRM_IDENTITY_OPS_EVENTS", None)

from core import crm_identity_memory as ident  # noqa: E402
from core import crm_identity_operator_depth as ops  # noqa: E402
from core import crm_ops_needs_you_connective as nye  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HTML = ROOT / "dashboards" / "crm-identity.html"
MODULE = SCRIPTS / "core" / "crm_identity_operator_depth.py"
SERVE = SCRIPTS / "serve_beta.py"
BETA = "http://127.0.0.1:8788"
PROD = "http://127.0.0.1:8787"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
PROV = "Owner recorded this on 2026-09-23 from a named guest."
EVID = "Front desk matched the passport name on 2026-09-23."
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
CRM_CRS = nye.CRM_TARGET_CRS
PROGRESS_CRS = (
    "e38d9812128a4535b4a6f59f3a3a0319",
    "CR-c4ed4e3fa9f15a40",
    "CR-6e3fd7b9d7edca0e",
    "CR-7a022a9394592c75",
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


def _seed(db: Path) -> tuple[str, str]:
    cust = ident.register_customer(
        {"display_name": "Ayu Sari", "entity_id": "GGV", "provenance": PROV},
        person_id="PERS-MATT",
        db_path=db,
    )
    cid = cust["customer_id"]
    link = ident.propose_link(
        {
            "customer_id": cid,
            "other_id": "PERS-GUEST-DEPTH",
            "other_kind": "PERSON",
            "evidence_ref": EVID,
            "provenance": PROV,
        },
        person_id="PERS-MATT",
        db_path=db,
    )
    return cid, link["candidate_id"]


def test_honesty_and_rbac() -> None:
    flags = ops.honesty_flags()
    check("01 bound", flags.get("bound") == "beta-crm-loop-safe")
    check("02 schema", flags.get("schema_id") == ops.SCHEMA_ID)
    check("03 claim", flags.get("claim_id") == "bf-crm-identity-operator-depth-20260923")
    check("04 proven false", flags.get("proven") is False)
    check("05 ready false", flags.get("ready") is False)
    check("06 staff_ready false", flags.get("staff_ready") is False)
    check("07 graph false", flags.get("identity_graph_complete") is False)
    check("08 no silent merge", flags.get("silent_merge") is False)
    check("09 haikal not started", flags.get("haikal_human") == "not_started")
    check("10 devi parked", flags.get("devi_retest") == "parked")
    check("11 no permission grant", flags.get("invented_permission_grant") is False)
    check("12 cap 02 specified", flags.get("cap_crm_02") == "SPECIFIED", str(flags.get("caps")))
    check("13 cap 01 built", (flags.get("caps") or {}).get("CAP-CRM-01") == "BUILT")
    check("14 cap 03 specified", (flags.get("caps") or {}).get("CAP-CRM-03") == "SPECIFIED")
    check("15 cap 04 built", (flags.get("caps") or {}).get("CAP-CRM-04") == "BUILT")
    check("16 au not started", flags.get("au_crm_01_habitat") == "NOT STARTED")
    for cr in CRM_CRS:
        check(f"17 crm {cr} open", (flags.get("crm_crs") or {}).get(cr) == "OPEN")
    for cr in PROGRESS_CRS:
        check(f"18 progress {cr} open", (flags.get("progress_core_crs") or {}).get(cr) == "OPEN")

    shell_flags = shell.honesty_flags()
    check("19 shell flag", shell_flags.get("crm_identity_operator_depth") is True)
    check("20 shell staff_ready false", shell_flags.get("staff_ready") is False)

    schema = ops.schema_document()
    check("21 schema no merge", schema.get("merge_accepted") is False)
    check("22 confidence band", schema.get("match_confidence_band") == "uncertain")

    check("23 desk not refused", ops.refuse_code("/api/crm/identity/operator-depth") is None)
    check("24 rbac not refused", ops.refuse_code("/api/crm/identity/operator-depth/rbac") is None)
    check(
        "25 proven refused",
        ops.refuse_code("/api/crm/identity/operator-depth/proven") == "proven_refused",
    )
    check(
        "26 merge refused",
        ops.refuse_code("/api/crm/identity/operator-depth/merge") == "silent_merge_refused",
    )
    check(
        "27 habitat refused",
        ops.refuse_code("/api/crm/identity/operator-depth/habitat-done") == "habitat_refused",
    )
    check(
        "28 klaviyo refused",
        ops.refuse_code("/api/crm/identity/operator-depth/klaviyo") == "klaviyo_refused",
    )
    check(
        "29 legacy merge not stolen",
        ops.refuse_code("/api/crm/identity/merge") is None,
    )

    src = MODULE.read_text(encoding="utf-8")
    check("30 no lead spine import", "import lead_spine" not in src and "from core import lead_spine" not in src)
    check("31 no klaviyo import", "import habitat_klaviyo" not in src and "klaviyo_reader" not in src)
    serve = SERVE.read_text(encoding="utf-8")
    check("32 serve route", "/api/crm/identity/operator-depth" in serve)
    html = HTML.read_text(encoding="utf-8")
    check("33 desk anchor", 'id="identity-depth"' in html)
    check(
        "34 no orphan dashboard",
        not (ROOT / "dashboards" / "crm-identity-operator-depth.html").exists(),
    )

    for person, code in (
        ("", "denied"),
        ("PERS-DEVI", "outsider"),
        ("PERS-OUTSIDER", "outsider"),
    ):
        try:
            ops.require_seat(person)
            check(f"35 deny {person or 'anon'}", False, "allowed")
        except ops.IdentityDepthError as exc:
            check(f"35 deny {person or 'anon'}", exc.code == code and exc.http_status == 403, exc.code)

    for person in ("PERS-MATT", "PERS-AMANDA", "PERS-HAIKAL", "PERS-MISA"):
        seat = ops.require_seat(person)
        check(f"36 seat {person}", seat.get("authorised") is True and seat.get("invented_permission_grant") is False)

    prove = ops.prove_rbac(person_id="PERS-AMANDA")
    check("37 amanda review allowed", (prove.get("actions") or {}).get("review_decision") is True)
    check("38 amanda merge refused", (prove.get("actions") or {}).get("merge") is False)
    check("39 amanda haikal flag", prove.get("haikal_human") == "not_started")


def test_desk_actions() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "identity.sqlite"
        events = Path(tmp) / "events.jsonl"
        empty = ops.operator_depth_desk(
            verified_person_id="PERS-AMANDA",
            db_path=db,
            events_file=events,
        )
        check("40 empty desk", empty.get("empty") is True and empty.get("candidate_count") == 0)
        check("41 empty message", "not a complete identity graph" in str(empty.get("empty_message")))
        check("42 empty graph false", empty.get("identity_graph_complete") is False)
        check("43 empty needs-you", isinstance(empty.get("needs_you"), dict))
        check("44 no second mutate", empty.get("duplicate_mutate_surface") is False)
        check("45 amanda nye in scope", (empty.get("needs_you") or {}).get("in_scope") is True)

        cid, lid = _seed(db)
        desk = ops.operator_depth_desk(
            verified_person_id="PERS-MATT",
            db_path=db,
            events_file=events,
        )
        check("46 one candidate", desk.get("candidate_count") == 1, str(desk.get("candidate_count")))
        check("47 not empty", desk.get("empty") is False)
        cand = (desk.get("link_candidates") or [{}])[0]
        check("48 uncertain", cand.get("match_confidence") == "uncertain")
        check("49 human review", cand.get("human_review_required") is True)
        check("50 not merged", cand.get("merged") is False and cand.get("verified") is False)
        check("51 open review", desk.get("open_review_count") == 1)

        detail = ops.object_detail(
            lid,
            verified_person_id="PERS-AMANDA",
            db_path=db,
            events_file=events,
        )
        check("52 link detail", detail.get("ok") is True)
        check("53 detail uncertain", (detail.get("confidence") or {}).get("match_confidence") == "uncertain")
        check("54 detail review required", (detail.get("confidence") or {}).get("human_review_required") is True)
        check("55 review action on", (detail.get("actions") or {}).get("review_decision") is True)
        check("56 merge action off", (detail.get("actions") or {}).get("merge") is False)

        cust = ops.object_detail(
            cid,
            verified_person_id="PERS-HAIKAL",
            db_path=db,
            events_file=events,
        )
        check("57 customer detail", (cust.get("object") or {}).get("is_customer") is True)
        check("58 customer not lead", (cust.get("object") or {}).get("is_lead") is False)
        check("59 haikal nye out of strip", (cust.get("needs_you") or {}).get("in_scope") is False)

        note = ops.record_operator_action(
            cid,
            verified_person_id="PERS-AMANDA",
            kind="note",
            note="Asked about a Sunday viewing.",
            db_path=db,
            events_file=events,
        )
        check("60 note recorded", note.get("ok") is True and note.get("kind") == "note")
        check("61 note no merge", note.get("merged") is False and note.get("customers_unchanged") is True)
        check("62 note refreshes desk", isinstance(note.get("identity_desk"), dict))
        check("63 note refreshes nye", isinstance(note.get("needs_you"), dict))
        check("64 note spine untouched", note.get("lead_spine_mutated") is False)

        nxt = ops.record_operator_action(
            lid,
            verified_person_id="PERS-MISA",
            kind="next-action-touch",
            note="Call the guest before Thursday.",
            db_path=db,
            events_file=events,
        )
        check("65 next action", nxt.get("kind") == "next_action" and nxt.get("recorded") is True)
        check("66 links unchanged", nxt.get("link_rows_unchanged") is True)

        hand = ops.record_operator_action(
            lid,
            verified_person_id="PERS-MATT",
            kind="handoff_touch",
            note="Hand to Amanda for the viewing note.",
            db_path=db,
            events_file=events,
        )
        check("67 handoff", hand.get("kind") == "handoff_touch")

        still = ops.record_operator_action(
            lid,
            verified_person_id="PERS-AMANDA",
            kind="review-decision",
            decision="still_uncertain",
            note="Still not sure this is the same person.",
            db_path=db,
            events_file=events,
        )
        check("68 still uncertain", still.get("decision") == "still_uncertain")
        check("69 still not merged", still.get("merge_executed") is False and still.get("silent_merge") is False)
        check(
            "70 still open",
            (still.get("identity_desk") or {}).get("open_review_count") == 1,
            str(still.get("identity_desk")),
        )

        try:
            ops.record_operator_action(
                lid,
                verified_person_id="PERS-AMANDA",
                kind="review-decision",
                decision="merge",
                db_path=db,
                events_file=events,
            )
            check("71 merge decision refused", False, "allowed")
        except ops.IdentityDepthError as exc:
            check("71 merge decision refused", exc.code == "silent_merge_refused", exc.code)

        try:
            ops.record_operator_action(
                cid,
                verified_person_id="PERS-AMANDA",
                kind="review_decision",
                decision="keep_separate",
                db_path=db,
                events_file=events,
            )
            check("72 review on customer refused", False, "allowed")
        except ops.IdentityDepthError as exc:
            check("72 review on customer refused", exc.code == "review_target", exc.code)

        kept = ops.record_operator_action(
            lid,
            verified_person_id="PERS-AMANDA",
            kind="review_decision",
            decision="keep_separate",
            note="Keep the two rows apart.",
            db_path=db,
            events_file=events,
        )
        check("73 keep separate", kept.get("decision") == "keep_separate")
        check("74 keep not a graph", kept.get("identity_graph_complete") is False)
        check(
            "75 keep leaves open queue",
            (kept.get("identity_desk") or {}).get("open_review_count") == 0,
            str(kept.get("identity_desk")),
        )
        check("76 candidate remains", (kept.get("identity_desk") or {}).get("candidate_count") == 1)
        after = ops.object_detail(lid, verified_person_id="PERS-MATT", db_path=db, events_file=events)
        conf = after.get("confidence") or {}
        check("77 reviewed uncertain", conf.get("match_confidence") == "uncertain" and conf.get("review_recorded") is True)
        check("78 review not required", conf.get("human_review_required") is False)
        check("79 still not verified", conf.get("verified") is False)

        cid2, lid2 = _seed(db)
        dismissed = ops.record_operator_action(
            lid2,
            verified_person_id="PERS-MATT",
            kind="dismiss-noise",
            note="Duplicate noise from the same desk slip.",
            db_path=db,
            events_file=events,
        )
        check("80 dismiss", dismissed.get("kind") == "dismiss_noise")
        check("81 dismiss no delete", dismissed.get("link_rows_unchanged") is True)
        noise = ops.object_detail(lid2, verified_person_id="PERS-AMANDA", db_path=db, events_file=events)
        check("82 dismissed flag", (noise.get("confidence") or {}).get("dismissed_noise") is True)
        check("83 dismissed not merged", (noise.get("confidence") or {}).get("merged") is False)

        try:
            ops.record_operator_action(
                lid,
                verified_person_id="PERS-AMANDA",
                kind="note",
                note="x",
                body={"note": "x", "graph_complete": True},
                db_path=db,
                events_file=events,
            )
            check("84 graph field refused", False, "allowed")
        except ops.IdentityDepthError as exc:
            check("84 graph field refused", exc.code == "graph_complete_refused", exc.code)

        try:
            ops.record_operator_action(
                "LEAD-not-a-customer-row",
                verified_person_id="PERS-MATT",
                kind="note",
                note="This must not invent a customer.",
                db_path=db,
                events_file=events,
            )
            check("85 lead not invented", False, "allowed")
        except ops.IdentityDepthError as exc:
            check("85 lead not invented", exc.http_status == 404, exc.code)

        try:
            ops.record_operator_action(
                lid,
                verified_person_id="PERS-DEVI",
                kind="note",
                note="Devi is not a CRM seat.",
                db_path=db,
                events_file=events,
            )
            check("86 devi refused", False, "allowed")
        except ops.IdentityDepthError as exc:
            check("86 devi refused", exc.code == "outsider", exc.code)

        final = ops.operator_depth_desk(
            verified_person_id="PERS-MATT",
            db_path=db,
            events_file=events,
        )
        check("87 final graph false", final.get("identity_graph_complete") is False)
        check("88 final staff_ready false", final.get("staff_ready") is False)
        check("89 rows still two customers", final.get("customer_count") == 2, str(final.get("customer_count")))
        # cid2 was a second seed; first seed plus second = 2 customers, 2 links
        check("90 two candidates remain", final.get("candidate_count") == 2)


def test_live() -> None:
    check("91 :8788 up", port_up(8788))
    check("92 :8787 up", port_up(8787))
    prod_pid = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True
    ).strip().splitlines()[0]
    check("93 prod pid", prod_pid == "15975", prod_pid)

    ledger = _ledger()
    check("94 live cap 02", ledger.get("CAP-CRM-02", [None])[0] == "SPECIFIED")
    check("95 live cap 01", ledger.get("CAP-CRM-01", [None])[0] == "BUILT")
    check("96 live cap 03", ledger.get("CAP-CRM-03", [None])[0] == "SPECIFIED")
    check("97 live cap 04", ledger.get("CAP-CRM-04", [None])[0] == "BUILT")
    for cr in list(CRM_CRS) + list(PROGRESS_CRS):
        check(f"98 live {cr} OPEN", _cr(cr) == "OPEN", str(_cr(cr)))

    st, anon = http("GET", "/api/crm/identity/operator-depth")
    check("99 anon desk 403", st in (401, 403), str(anon)[:160])

    st, desk = http(
        "GET",
        "/api/crm/identity/operator-depth",
        headers={"X-Wolf-Subject": AMANDA},
    )
    check("100 amanda desk 200", st == 200 and desk.get("ok") is True, str(desk)[:220])
    check("101 live staff_ready false", isinstance(desk, dict) and desk.get("staff_ready") is False)
    check("102 live proven false", isinstance(desk, dict) and desk.get("proven") is False)
    check("103 live graph false", isinstance(desk, dict) and desk.get("identity_graph_complete") is False)
    check("104 live cap specified", isinstance(desk, dict) and (desk.get("honesty") or {}).get("cap_crm_02") == "SPECIFIED")

    st, rbac = http(
        "GET",
        "/api/crm/identity/operator-depth/rbac",
        headers={"X-Wolf-Subject": AMANDA},
    )
    check("105 rbac 200", st == 200 and rbac.get("can_identity_operator") is True, str(rbac)[:160])

    st, owner = http(
        "GET",
        "/api/crm/identity/operator-depth",
        headers={"X-Wolf-Subject": MATT},
    )
    check("106 owner desk 200", st == 200 and owner.get("ok") is True)

    st, out = http(
        "GET",
        "/api/crm/identity/operator-depth",
        headers={"X-Wolf-Subject": OUTSIDER},
    )
    check("107 outsider 403", st == 403, str(out)[:160])

    st, devi = http(
        "GET",
        "/api/crm/identity/operator-depth",
        headers={"X-Wolf-Subject": DEVI},
    )
    check("108 devi 403", st == 403 and devi.get("error") == "outsider", str(devi)[:160])

    st, page = http("GET", "/crm-identity", headers={"X-Wolf-Subject": AMANDA})
    check(
        "109 amanda page",
        st == 200 and isinstance(page, str) and "identity-depth" in page,
        str(page)[:120],
    )

    st, proven = http(
        "POST",
        "/api/crm/identity/operator-depth/proven",
        body={},
        headers={"X-Wolf-Subject": AMANDA},
    )
    check("110 proven 403", st == 403 and proven.get("error") == "proven_refused", str(proven)[:160])

    st, hab = http(
        "POST",
        "/api/crm/identity/operator-depth/cutover",
        body={},
        headers={"X-Wolf-Subject": MATT},
    )
    check("111 cutover 403", st == 403 and hab.get("error") == "cutover_refused", str(hab)[:160])

    st, reg = http(
        "POST",
        "/api/crm/identity",
        body={"display_name": "Depth fixture guest", "entity_id": "GGV", "provenance": PROV},
        headers={"X-Wolf-Subject": MATT},
    )
    check("112 register 200", st == 200 and reg.get("ok") is True, str(reg)[:180])
    cid = reg.get("customer_id") if isinstance(reg, dict) else ""
    if cid:
        st, link = http(
            "POST",
            "/api/crm/identity/link",
            body={
                "customer_id": cid,
                "other_id": "PERS-DEPTH-LIVE",
                "other_kind": "PERSON",
                "evidence_ref": EVID,
                "provenance": PROV,
            },
            headers={"X-Wolf-Subject": MATT},
        )
        check("113 link candidate", st == 200 and link.get("merged") is False, str(link)[:180])
        lid = link.get("candidate_id") if isinstance(link, dict) else ""
    else:
        check("113 link candidate", False, "no customer")
        lid = ""

    if cid and lid:
        st, detail = http(
            "GET",
            f"/api/crm/identity/operator-depth/objects/{lid}",
            headers={"X-Wolf-Subject": AMANDA},
        )
        check("114 detail 200", st == 200 and detail.get("ok") is True, str(detail)[:180])
        check(
            "115 live uncertain",
            (detail.get("confidence") or {}).get("human_review_required") is True
            and (detail.get("confidence") or {}).get("match_confidence") == "uncertain",
        )
        st, touch = http(
            "POST",
            f"/api/crm/identity/operator-depth/objects/{lid}/review-decision",
            body={"decision": "not_a_match", "note": "Not the same person."},
            headers={"X-Wolf-Subject": AMANDA},
        )
        check("116 review 200", st == 200 and touch.get("ok") is True, str(touch)[:200])
        check("117 review no merge", touch.get("merged") is False and touch.get("merge_executed") is False)
        check("118 review refreshes", isinstance(touch.get("identity_desk"), dict) and isinstance(touch.get("needs_you"), dict))
        check("119 review staff_ready false", touch.get("staff_ready") is False)
        st, nxt = http(
            "POST",
            f"/api/crm/identity/operator-depth/objects/{cid}/next-action-touch",
            body={"note": "Next viewing note only."},
            headers={"X-Wolf-Subject": HAIKAL},
        )
        check("120 haikal next action", st == 200 and nxt.get("kind") == "next_action", str(nxt)[:180])
        check("121 haikal spine false", nxt.get("lead_spine_mutated") is False)
    else:
        for name in (
            "114 detail 200",
            "115 live uncertain",
            "116 review 200",
            "117 review no merge",
            "118 review refreshes",
            "119 review staff_ready false",
            "120 haikal next action",
            "121 haikal spine false",
        ):
            check(name, False, "no ids")

    st, prod = http("GET", "/api/crm/identity/operator-depth", base=PROD)
    check("122 prod depth 404", st == 404, str(prod)[:120])

    prod_pid_after = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True
    ).strip().splitlines()[0]
    check("123 prod pid unchanged", prod_pid_after == "15975", prod_pid_after)


def test_wip_untouched(before: str) -> None:
    after = subprocess.check_output(["git", "hash-object", *WIP], cwd=str(ROOT), text=True)
    check("124 wip unchanged", before == after)


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
