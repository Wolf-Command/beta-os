#!/usr/bin/env python3
"""Owner commissioning operator depth — card detail/actions, no invented commission."""
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
os.environ.pop("WOLF_OWNER_CMQ_OPS_EVENTS", None)
os.environ.pop("WOLF_COMMISSIONING_STATE_DIR", None)

from core import owner_commissioning_operator_depth as ops  # noqa: E402
from core import owner_commissioning_queue as ocq  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
STUB = (
    ROOT
    / "state"
    / "completion-register"
    / "wolf-owner-commissioning-queue-20260922.json"
)
EVIDENCE = ROOT / "state" / "progress" / "commissioning-evidence.jsonl"
QUEUE_STATE = ROOT / "state" / "progress" / "commissioning-queue-state.json"
HTML = ROOT / "dashboards" / "progress.html"
MODULE = SCRIPTS / "core" / "owner_commissioning_operator_depth.py"
SERVE = SCRIPTS / "serve_beta.py"
BETA = "http://127.0.0.1:8788"
PROD = "http://127.0.0.1:8787"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
DEVI = "deviputu236@gmail.com"
OUTSIDER = "not-a-seat@example.com"
NOTE = "Owner commissioning touch only. Not a PASS."
HAIKAL_CARD = "CMQ-NAS-HAIKAL"
DEVI_CARD = "CMQ-DEVI-UMA-MOBILE"
OWNER_CARD = "CMQ-PROGRESS-NEEDS-YOU"
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


def _bytes(path: Path) -> bytes:
    return path.read_bytes() if path.is_file() else b""


def _pass_evidence(state_dir: Path) -> None:
    """Fixture submit evidence so the open queue is clear. Not an operator action."""
    state_dir.mkdir(parents=True, exist_ok=True)
    lines = []
    for tmpl in ocq.seed_templates():
        lines.append(
            json.dumps(
                {
                    "task_id": tmpl["id"],
                    "feedback": "PASS",
                    "criterion_satisfied": True,
                    "proven": False,
                    "ready": False,
                    "staff_ready": False,
                }
            )
        )
    (state_dir / ocq.EVIDENCE_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_honesty_and_rbac() -> None:
    flags = ops.honesty_flags()
    check("01 bound", flags.get("bound") == "beta-owner-progress-safe")
    check("02 schema", flags.get("schema_id") == ops.SCHEMA_ID)
    check("03 claim", flags.get("claim_id") == "bf-owner-commissioning-operator-depth-20260923")
    check("04 proven false", flags.get("proven") is False)
    check("05 ready false", flags.get("ready") is False)
    check("06 staff_ready false", flags.get("staff_ready") is False)
    check("07 no invented human commissioned", flags.get("invented_human_commissioned") is False)
    check("08 pass submit only", flags.get("pass_submit_is_only_commission_evidence") is True)
    check("09 haikal not started", flags.get("haikal_human") == "not_started")
    check("10 devi parked", flags.get("devi_retest") == "parked")
    check("11 no bzg compose", flags.get("bzg_compose") is False)
    check("12 no secret mint", flags.get("secret_mint") is False)
    check("13 no access mutate", flags.get("cf_access_include_mutated") is False)
    check("14 intg not reopened", flags.get("intg_reopened") is False)
    check("15 w12 not reopened", flags.get("w12_fin_reopened") is False)
    check("16 cap 11 specified", flags.get("cap_core_11") == "SPECIFIED", str(flags.get("cap_core_11")))
    check("17 cap 12 built", flags.get("cap_core_12") == "BUILT", str(flags.get("cap_core_12")))
    check("18 stub built", flags.get("commissioning_queue_stub_status") == "BUILT")
    for cr in ops.PROGRESS_CRS:
        check(
            f"19 progress {cr} open",
            (flags.get("progress_core_crs") or {}).get(cr) == "OPEN",
            str((flags.get("progress_core_crs") or {}).get(cr)),
        )
    nav = flags.get("global_nav_crs") or {}
    check("20 nav design in progress", nav.get("531f29b41f5dfb381503889cacdcfb39") == "IN_PROGRESS")
    check("21 nav responsive open", nav.get("e4bee2462ff81803287fa3562776d8ec") == "OPEN")
    check("22 nav resolved stays", nav.get("CR-5a5e660e41f782a4") == "RESOLVED")
    check("23 nav design resolved stays", nav.get("CR-26989486969627cd") == "RESOLVED")
    check("24 false resolve false", flags.get("false_resolve_cr") is False)

    shell_flags = shell.honesty_flags()
    check("25 shell flag", shell_flags.get("owner_commissioning_operator_depth") is True)
    check("26 shell staff_ready false", shell_flags.get("staff_ready") is False)

    schema = ops.schema_document()
    check("27 schema no human commissioned", schema.get("human_commissioned_accepted") is False)
    check("28 schema no pass bypass", schema.get("pass_submit_bypass_accepted") is False)
    check("29 empty id", schema.get("empty_object_id") == ops.EMPTY_ID)

    check("30 desk not refused", ops.refuse_code("/api/progress/commissioning/operator-depth") is None)
    check("31 rbac not refused", ops.refuse_code("/api/progress/commissioning/operator-depth/rbac") is None)
    check("32 submit not this refuse", ops.refuse_code("/api/progress/commissioning/submit") is None)
    check(
        "33 proven refused",
        ops.refuse_code("/api/progress/commissioning/operator-depth/proven") == "proven_refused",
    )
    check(
        "34 ready refused",
        ops.refuse_code("/api/progress/commissioning/operator-depth/ready") == "ready_refused",
    )
    check(
        "35 staff ready refused",
        ops.refuse_code("/api/progress/commissioning/operator-depth/staff-ready") == "staff_ready_refused",
    )
    check(
        "36 human commissioned refused",
        ops.refuse_code("/api/progress/commissioning/operator-depth/human-commissioned")
        == "human_commissioned_invent_refused",
    )
    check(
        "37 pass refused",
        ops.refuse_code("/api/progress/commissioning/operator-depth/pass") == "pass_submit_only",
    )
    check(
        "38 haikal refused",
        ops.refuse_code("/api/progress/commissioning/operator-depth/haikal-done") == "haikal_done_refused",
    )
    check(
        "39 devi refused",
        ops.refuse_code("/api/progress/commissioning/operator-depth/devi-done") == "devi_done_refused",
    )
    check(
        "40 compose refused",
        ops.refuse_code("/api/progress/commissioning/operator-depth/bzg-compose") == "bzg_compose_refused",
    )
    check(
        "41 access refused",
        ops.refuse_code("/api/progress/commissioning/operator-depth/access-include") == "access_refused",
    )
    check(
        "42 secret refused",
        ops.refuse_code("/api/progress/commissioning/operator-depth/secret-mint") == "secret_refused",
    )
    check(
        "43 money refused",
        ops.refuse_code("/api/progress/commissioning/operator-depth/money") == "money_refused",
    )
    check(
        "44 production refused",
        ops.refuse_code("/api/progress/commissioning/operator-depth/production") == "production_refused",
    )
    check(
        "45 resolve refused",
        ops.refuse_code("/api/progress/commissioning/operator-depth/resolve") == "resolve_refused",
    )

    serve = SERVE.read_text(encoding="utf-8")
    html = HTML.read_text(encoding="utf-8")
    src = MODULE.read_text(encoding="utf-8")
    check("46 serve route", "/api/progress/commissioning/operator-depth" in serve)
    check("47 serve submit kept", "/api/progress/commissioning/submit" in serve)
    check("48 panel", 'id="cmq-operator-depth"' in html)
    check("49 no orphan dashboard", not (ROOT / "dashboards" / "owner-commissioning-operator-depth.html").exists())
    check("50 module present", MODULE.is_file())
    check("51 no submit_feedback call", "submit_feedback(" not in src)

    try:
        ops.require_seat(None)
        check("52 anon seat refused", False)
    except ops.CommissionDepthError as exc:
        check("52 anon seat refused", exc.code == "denied" and exc.http_status == 403)
    try:
        ops.require_seat("PERS-HAIKAL")
        check("53 haikal seat refused", False)
    except ops.CommissionDepthError as exc:
        check("53 haikal seat refused", exc.code == "outsider")
    try:
        ops.require_seat("PERS-DEVI")
        check("54 devi seat refused", False)
    except ops.CommissionDepthError as exc:
        check("54 devi seat refused", exc.code == "outsider")
    try:
        ops.require_seat("PERS-AMANDA")
        check("55 amanda seat refused", False)
    except ops.CommissionDepthError as exc:
        check("55 amanda seat refused", exc.code == "outsider")
    try:
        ops.require_seat("PERS-MISA")
        check("56 misa seat refused", False)
    except ops.CommissionDepthError as exc:
        check("56 misa seat refused", exc.code == "outsider")
    seat = ops.require_seat("PERS-MATT")
    check("57 owner seat", seat.get("seat") == "owner" and seat.get("invented_permission_grant") is False)
    rbac = ops.prove_rbac(person_id="PERS-MATT")
    actions = rbac.get("actions") or {}
    check("58 rbac note", actions.get("note") is True)
    check("59 rbac human commissioned false", actions.get("human_commissioned") is False)
    check("60 rbac pass false", actions.get("pass_submit") is False)
    check("61 rbac compose false", actions.get("bzg_compose") is False)
    check("62 rbac access false", actions.get("access_include") is False)


def test_desk_actions() -> None:
    stub_before = _bytes(STUB)
    ledger_before = _bytes(LEDGER)
    evidence_before = _bytes(EVIDENCE)
    queue_before = _bytes(QUEUE_STATE)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        state = root / "queue"
        events = root / "events.jsonl"
        state.mkdir()
        open_desk = ops.operator_depth_desk(
            verified_person_id="PERS-MATT",
            state_override=state,
            events_file=events,
        )
        check("63 open desk", open_desk.get("ok") is True and open_desk.get("empty") is False)
        check("64 cards present", (open_desk.get("card_count") or 0) >= 8)
        check("65 no placeholder while open", open_desk.get("empty_placeholder") is None)
        check("66 counters refresh", isinstance((open_desk.get("counters") or {}).get("READY_TO_TEST"), int))
        check("67 needs you refresh", isinstance((open_desk.get("needs_you") or {}).get("count"), int))
        check("68 desk staff_ready false", open_desk.get("staff_ready") is False)
        haikal = next((c for c in open_desk.get("cards") or [] if c.get("object_id") == HAIKAL_CARD), None)
        devi = next((c for c in open_desk.get("cards") or [] if c.get("object_id") == DEVI_CARD), None)
        check("69 haikal card not started", bool(haikal) and haikal.get("haikal_human") == "not_started")
        check("70 devi card parked", bool(devi) and devi.get("devi_retest") == "parked")
        detail = ops.object_detail(
            OWNER_CARD,
            verified_person_id="PERS-MATT",
            state_override=state,
            events_file=events,
        )
        check(
            "71 owner card detail",
            detail.get("object_kind") == "commissioning_card" and detail.get("human_commissioned") is False,
        )
        note = ops.record_operator_action(
            OWNER_CARD,
            verified_person_id="PERS-MATT",
            kind="note",
            note=NOTE,
            state_override=state,
            events_file=events,
        )
        check("72 note recorded", note.get("ok") is True and note.get("kind") == "note")
        check("73 evidence unchanged", note.get("evidence_unchanged") is True and note.get("evidence_mutated") is False)
        check("74 queue unchanged", note.get("queue_unchanged") is True and note.get("counters_unchanged") is True)
        check(
            "75 note refreshes",
            isinstance(note.get("needs_you"), dict) and isinstance(note.get("commissioning"), dict),
        )
        nxt = ops.record_operator_action(
            OWNER_CARD,
            verified_person_id="PERS-MATT",
            kind="next-action-touch",
            note="Next touch stays a note.",
            state_override=state,
            events_file=events,
        )
        check("76 next action", nxt.get("kind") == "next_action" and nxt.get("pass_submit_bypassed") is False)
        hand = ops.record_operator_action(
            HAIKAL_CARD,
            verified_person_id="PERS-MATT",
            kind="handoff-touch",
            note="Handoff touch only. Haikal stays not started.",
            state_override=state,
            events_file=events,
        )
        check("77 handoff haikal stays", hand.get("kind") == "handoff_touch" and hand.get("haikal_human") == "not_started")
        devi_touch = ops.record_operator_action(
            DEVI_CARD,
            verified_person_id="PERS-MATT",
            kind="note",
            note="Devi card stays parked.",
            state_override=state,
            events_file=events,
        )
        check("78 devi stays parked", devi_touch.get("devi_retest") == "parked" and devi_touch.get("human_commissioned") is False)
        review = ops.record_operator_action(
            OWNER_CARD,
            verified_person_id="PERS-MATT",
            kind="review-decision",
            decision="still_open",
            note="Still open.",
            state_override=state,
            events_file=events,
        )
        check("79 review still open", review.get("decision") == "still_open" and review.get("human_commissioned") is False)
        not_done = ops.record_operator_action(
            DEVI_CARD,
            verified_person_id="PERS-MATT",
            kind="review-decision",
            decision="not_commissioned",
            state_override=state,
            events_file=events,
        )
        check("80 not commissioned", not_done.get("decision") == "not_commissioned")
        kept = ops.record_operator_action(
            HAIKAL_CARD,
            verified_person_id="PERS-MATT",
            kind="review_decision",
            decision="keep_as_note",
            state_override=state,
            events_file=events,
        )
        check("81 keep as note", kept.get("decision") == "keep_as_note" and kept.get("staff_ready") is False)
        try:
            ops.record_operator_action(
                OWNER_CARD,
                verified_person_id="PERS-MATT",
                kind="review-decision",
                decision="human_commissioned",
                state_override=state,
                events_file=events,
            )
            check("82 human decision refused", False)
        except ops.CommissionDepthError as exc:
            check("82 human decision refused", exc.code == "human_commissioned_invent_refused" and exc.http_status == 403)
        try:
            ops.record_operator_action(
                OWNER_CARD,
                verified_person_id="PERS-MATT",
                kind="proven",
                note=NOTE,
                state_override=state,
                events_file=events,
            )
            check("83 proven kind refused", False)
        except ops.CommissionDepthError as exc:
            check("83 proven kind refused", exc.code == "proven_refused")
        try:
            ops.record_operator_action(
                OWNER_CARD,
                verified_person_id="PERS-MATT",
                kind="pass",
                note=NOTE,
                state_override=state,
                events_file=events,
            )
            check("84 pass kind refused", False)
        except ops.CommissionDepthError as exc:
            check("84 pass kind refused", exc.code == "pass_submit_only")
        try:
            ops.record_operator_action(
                OWNER_CARD,
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"human_commissioned": True, "note": NOTE, "kind": "note"},
                state_override=state,
                events_file=events,
            )
            check("85 human field refused", False)
        except ops.CommissionDepthError as exc:
            check("85 human field refused", exc.code == "human_commissioned_invent_refused")
        try:
            ops.record_operator_action(
                OWNER_CARD,
                verified_person_id="PERS-MATT",
                kind="note",
                note="Send payment of 50 usd",
                state_override=state,
                events_file=events,
            )
            check("86 money note refused", False)
        except ops.CommissionDepthError as exc:
            check("86 money note refused", exc.code == "money_refused")
        try:
            ops.record_operator_action(
                OWNER_CARD,
                verified_person_id="PERS-MATT",
                kind="note",
                note="This card is proven",
                state_override=state,
                events_file=events,
            )
            check("87 proven note refused", False)
        except ops.CommissionDepthError as exc:
            check("87 proven note refused", exc.code == "refused_field")
        try:
            ops.record_operator_action(
                OWNER_CARD,
                verified_person_id="PERS-HAIKAL",
                kind="note",
                note=NOTE,
                state_override=state,
                events_file=events,
            )
            check("88 outsider action refused", False)
        except ops.CommissionDepthError as exc:
            check("88 outsider action refused", exc.code == "outsider")
        dismissed = ops.record_operator_action(
            OWNER_CARD,
            verified_person_id="PERS-MATT",
            kind="dismiss-noise",
            note="Noise only.",
            state_override=state,
            events_file=events,
        )
        check("89 dismiss", dismissed.get("kind") == "dismiss_noise" and dismissed.get("counters_unchanged") is True)
        after = ops.operator_depth_desk(
            verified_person_id="PERS-MATT",
            state_override=state,
            events_file=events,
        )
        touched = next((c for c in after.get("cards") or [] if c.get("object_id") == OWNER_CARD), {})
        check("90 dismissed card", touched.get("dismissed_noise") is True and after.get("empty") is False)
        check("91 still not commissioned", after.get("human_commissioned") is False)
        try:
            ops.object_detail(
                ops.EMPTY_ID,
                verified_person_id="PERS-MATT",
                state_override=state,
                events_file=events,
            )
            check("92 placeholder hidden", False)
        except ops.CommissionDepthError as exc:
            check("92 placeholder hidden", exc.code == "not_found")
        try:
            ops.record_operator_action(
                OWNER_CARD,
                verified_person_id="PERS-MATT",
                kind="note",
                note=NOTE,
                body={"compose": True, "kind": "note", "note": NOTE},
                state_override=state,
                events_file=events,
            )
            check("93 compose field refused", False)
        except ops.CommissionDepthError as exc:
            check("93 compose field refused", exc.code == "bzg_compose_refused")

        cleared = root / "cleared"
        cleared_events = root / "cleared-events.jsonl"
        _pass_evidence(cleared)
        evidence_fixture = (cleared / ocq.EVIDENCE_NAME).read_bytes()
        empty = ops.operator_depth_desk(
            verified_person_id="PERS-MATT",
            state_override=cleared,
            events_file=cleared_events,
        )
        check("94 empty desk", empty.get("empty") is True and empty.get("card_count") == 0)
        check("95 placeholder present", (empty.get("empty_placeholder") or {}).get("object_id") == ops.EMPTY_ID)
        check("96 empty not invent", empty.get("human_commissioned") is False and empty.get("pass_submit_bypassed") is False)
        check(
            "97 commissioned counter from evidence",
            (empty.get("counters") or {}).get("COMMISSIONED") == len(ocq.seed_templates()),
            str(empty.get("counters")),
        )
        empty_note = ops.record_operator_action(
            ops.EMPTY_ID,
            verified_person_id="PERS-MATT",
            kind="note",
            note=NOTE,
            state_override=cleared,
            events_file=cleared_events,
        )
        check("98 empty note", empty_note.get("ok") is True and empty_note.get("evidence_unchanged") is True)
        check("99 fixture evidence untouched", (cleared / ocq.EVIDENCE_NAME).read_bytes() == evidence_fixture)
        try:
            ops.object_detail(
                OWNER_CARD,
                verified_person_id="PERS-MATT",
                state_override=cleared,
                events_file=cleared_events,
            )
            check("100 commissioned card not open", False)
        except ops.CommissionDepthError as exc:
            check("100 commissioned card not open", exc.code == "not_open")
        try:
            ops.events_path(root / "money.sqlite")
            check("101 money path refused", False)
        except ops.CommissionDepthError as exc:
            check("101 money path refused", exc.code == "money_refused")
        try:
            ops.events_path(root / ocq.EVIDENCE_NAME)
            check("102 evidence path refused", False)
        except ops.CommissionDepthError as exc:
            check("102 evidence path refused", exc.code == "pass_submit_only")
        try:
            ops.events_path(Path("/Users/wolfterminal/alchemist/events.jsonl"))
            check("103 production path refused", False)
        except ops.CommissionDepthError as exc:
            check("103 production path refused", exc.code == "production_refused")

    check("104 stub unchanged", _bytes(STUB) == stub_before)
    check("105 ledger unchanged", _bytes(LEDGER) == ledger_before)
    check("106 live evidence untouched", _bytes(EVIDENCE) == evidence_before)
    check("107 live queue untouched", _bytes(QUEUE_STATE) == queue_before)
    for cr in ops.PROGRESS_CRS:
        check(f"108 cr {cr} still open", _cr(cr) == "OPEN", str(_cr(cr)))
    for cr, expect in ops.NAV_AS_IS.items():
        check(f"109 nav {cr}", _cr(cr) == expect, str(_cr(cr)))


def test_live() -> None:
    check("110 port 8788", port_up(8788))
    check("111 port 8787", port_up(8787))
    if not port_up(8788):
        for name in (
            "112 anon 403",
            "113 owner desk",
            "114 owner rbac",
            "115 outsider 403",
            "116 haikal 403",
            "117 devi 403",
            "118 amanda 403",
            "119 misa 403",
            "120 detail",
            "121 action refresh",
            "122 human refuse",
            "123 proven refuse",
            "124 page",
            "125 prod 404",
        ):
            check(name, False, "beta down")
        return

    evidence_before = _bytes(EVIDENCE)
    queue_before = _bytes(QUEUE_STATE)
    stub_before = _bytes(STUB)
    st, anon = http("GET", "/api/progress/commissioning/operator-depth")
    check("112 anon 403", st == 403, str(anon)[:180])
    st, desk = http(
        "GET",
        "/api/progress/commissioning/operator-depth",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "113 owner desk",
        st == 200
        and isinstance(desk, dict)
        and desk.get("ok") is True
        and desk.get("staff_ready") is False
        and desk.get("human_commissioned") is False
        and desk.get("schema_id") == ops.SCHEMA_ID,
        str(desk)[:240],
    )
    st, rbac = http(
        "GET",
        "/api/progress/commissioning/operator-depth/rbac",
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "114 owner rbac",
        st == 200 and isinstance(rbac, dict) and rbac.get("can_commissioning_operator") is True,
        str(rbac)[:180],
    )
    st, out = http(
        "GET",
        "/api/progress/commissioning/operator-depth",
        headers={"X-Wolf-Subject": OUTSIDER},
    )
    check("115 outsider 403", st == 403, str(out)[:160])
    st, haikal = http(
        "GET",
        "/api/progress/commissioning/operator-depth",
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("116 haikal 403", st == 403, str(haikal)[:160])
    st, devi = http(
        "GET",
        "/api/progress/commissioning/operator-depth/rbac",
        headers={"X-Wolf-Subject": DEVI},
    )
    check("117 devi 403", st == 403, str(devi)[:160])
    st, amanda = http(
        "GET",
        "/api/progress/commissioning/operator-depth",
        headers={"X-Wolf-Subject": AMANDA},
    )
    check("118 amanda 403", st == 403, str(amanda)[:120])
    st, misa = http(
        "GET",
        "/api/progress/commissioning/operator-depth",
        headers={"X-Wolf-Subject": MISA},
    )
    check("119 misa 403", st == 403, str(misa)[:120])
    target = None
    if isinstance(desk, dict) and desk.get("empty"):
        target = ops.EMPTY_ID
    elif isinstance(desk, dict):
        cards = desk.get("cards") or []
        if cards:
            target = cards[0].get("object_id")
    if target:
        st, detail = http(
            "GET",
            f"/api/progress/commissioning/operator-depth/objects/{target}",
            headers={"X-Wolf-Subject": MATT},
        )
        check(
            "120 detail",
            st == 200
            and isinstance(detail, dict)
            and detail.get("human_commissioned") is False
            and detail.get("pass_submit_bypassed") is False,
            str(detail)[:220],
        )
        st, touch = http(
            "POST",
            f"/api/progress/commissioning/operator-depth/objects/{target}/next-action-touch",
            body={"note": "Live Beta commissioning touch. Not a PASS."},
            headers={"X-Wolf-Subject": MATT},
        )
        check(
            "121 action refresh",
            st == 200
            and isinstance(touch, dict)
            and touch.get("kind") == "next_action"
            and touch.get("evidence_unchanged") is True
            and touch.get("counters_unchanged") is True
            and isinstance(touch.get("needs_you"), dict)
            and isinstance(touch.get("commissioning"), dict)
            and _bytes(EVIDENCE) == evidence_before
            and _bytes(QUEUE_STATE) == queue_before
            and _bytes(STUB) == stub_before,
            str(touch)[:240],
        )
    else:
        check("120 detail", False, "no object")
        check("121 action refresh", False, "no object")
    st, human = http(
        "POST",
        "/api/progress/commissioning/operator-depth/human-commissioned",
        body={"note": NOTE},
        headers={"X-Wolf-Subject": MATT},
    )
    check(
        "122 human refuse",
        st == 403 and isinstance(human, dict) and human.get("error") == "human_commissioned_invent_refused",
        str(human)[:180],
    )
    st, proven = http(
        "GET",
        "/api/progress/commissioning/operator-depth/proven",
        headers={"X-Wolf-Subject": MATT},
    )
    check("123 proven refuse", st == 403 and isinstance(proven, dict) and proven.get("error") == "proven_refused", str(proven)[:180])
    st, passed = http(
        "POST",
        "/api/progress/commissioning/operator-depth/pass",
        body={"note": NOTE},
        headers={"X-Wolf-Subject": MATT},
    )
    check("124 pass refuse", st == 403 and isinstance(passed, dict) and passed.get("error") == "pass_submit_only", str(passed)[:180])
    st, page = http("GET", "/progress", headers={"X-Wolf-Subject": MATT})
    check(
        "125 page panel",
        st == 200 and isinstance(page, str) and 'id="cmq-operator-depth"' in page,
        str(page)[:160],
    )
    st, prod = http("GET", "/api/progress/commissioning/operator-depth", base=PROD)
    check("126 prod depth 404", st == 404, str(prod)[:120])
    for cr in ops.PROGRESS_CRS:
        check(f"127 live progress {cr}", _cr(cr) == "OPEN")
    for cr, expect in ops.NAV_AS_IS.items():
        check(f"128 live nav {cr}", _cr(cr) == expect, str(_cr(cr)))
    check("129 stub still built", json.loads(STUB.read_text(encoding="utf-8")).get("status") == "BUILT")


def test_wip_untouched(before: str, prod_pid_before: str) -> None:
    after = subprocess.check_output(["git", "hash-object", *WIP], cwd=str(ROOT), text=True)
    check("130 wip unchanged", before == after)
    prod_pid = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True
    ).strip().splitlines()[0]
    check("131 prod pid", prod_pid == prod_pid_before, prod_pid)


def main() -> None:
    before = subprocess.check_output(["git", "hash-object", *WIP], cwd=str(ROOT), text=True)
    prod_pid = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-sTCP:LISTEN", "-t"], text=True
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
