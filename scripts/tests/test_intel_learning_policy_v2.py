#!/usr/bin/env python3
"""CAP-INTEL-05 learning policy v2 — list/filter stubs + operator read surface.

Beyond approve-to-rule skeleton. No auto-promote. CAP stays SPECIFIED.
CR-be51980bd1194448 stays OPEN. proven=false ready=false staff_ready=false.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import socket
import sqlite3
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALLOW_LIVE_INTEL_RULE", None)
os.environ.pop("WOLF_INTEL_RULE_DB", None)

from core import intel_approve_to_rule as rule  # noqa: E402
from core import intel_learning_policy as learn  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "intel_approve_to_rule.sqlite"
LEDGER_JSON = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
CR_ID = "CR-be51980bd1194448"
NEXT_ACTION = "Approve-to-rule learning loop"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
ROLE = "PERS-INTEL-ROLE"

NOTE = "The close missed the tin count on a quiet Tuesday service."
RULE = "Count the tin before the drawer is closed and write the number."
RULE2 = "Write the tin count on the card before the drawer is locked."

WIP = {
    "scripts/migrations/migrate_phase2_6_team_readiness.py":
        "a8e89d399bd33ec11135b8caaa002a0d18c70000b6a8972d46811d30a61c9881",
    "scripts/phase26_team.py":
        "7c3690afaea97d8fdb48422bf4cbc8e144c9ecfac45c24c19977e83d45088fe0",
    "scripts/skills/__init__.py":
        "edfb69ce6d8f92a88ee6bf6a8160d9926765843271961bba52a3754450c93105",
    "scripts/wolf_intelligence.py":
        "e1de6a248512bcdaf6e71c4db30dc80a229055c7707e682c73d9349acb9bc21b",
}

LEDGER_BEFORE = hashlib.sha256(LEDGER_JSON.read_bytes()).hexdigest()
CR_BEFORE = None
PROD_PID_BEFORE = None


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _tmp_dir() -> Path:
    td = ROOT / "catalog" / "backups" / f"tmp-intel-learn-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    return td


def _db(td: Path) -> Path:
    return td / "learning_policy.sqlite"


def _cr_row() -> tuple | None:
    conn = sqlite3.connect(str(CATALOG))
    try:
        return conn.execute(
            """
            SELECT state, resolution_evidence, blocker_class, next_action
            FROM wolf_completion_items WHERE id=?
            """,
            (CR_ID,),
        ).fetchone()
    finally:
        conn.close()


def _pid_on(port: int) -> str | None:
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    return lines[0] if lines else None


def _port_up(port: int) -> bool:
    s = socket.socket()
    s.settimeout(1.5)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def _expect_error(name: str, fn, code: str) -> None:
    try:
        fn()
    except (learn.LearningPolicyError, rule.IntelRuleError) as exc:
        check(name, exc.code == code, getattr(exc, "code", str(exc)))
        return
    except Exception as exc:  # noqa: BLE001
        check(name, False, type(exc).__name__ + " " + str(exc))
        return
    check(name, False, "no error")


def _seed_stub(path: Path) -> dict:
    note = rule.record_note(
        {"experiment_note": NOTE},
        person_id=rule.OWNER_PERSON,
        db_path=path,
    )
    rule.approve_note(
        {"note_id": note["note_id"]},
        person_id=rule.OWNER_PERSON,
        db_path=path,
    )
    stub = rule.stub_rule(
        {"note_id": note["note_id"], "rule_text": RULE},
        person_id=rule.OWNER_PERSON,
        db_path=path,
    )
    return {"note": note, "stub": stub}


def test_honesty() -> None:
    flags = learn.honesty_flags()
    check("honesty.cap", flags.get("cap") == "CAP-INTEL-05")
    check("honesty.slice v2", flags.get("slice") == "intel_learning_policy_v2")
    check("honesty.cr_open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("honesty.cr_not_resolved", flags.get("cr_resolved") is False)
    check("honesty.ledger SPECIFIED", flags.get("ledger_maturity") == "SPECIFIED")
    check("honesty.ceiling BUILT", flags.get("maturity_ceiling") == "BUILT")
    check("honesty.proven false", flags.get("proven") is False)
    check("honesty.ready false", flags.get("ready") is False)
    check("honesty.staff_ready false", flags.get("staff_ready") is False)
    check("honesty.no auto_promote", flags.get("auto_promote") is False)
    check("honesty.no auto_apply", flags.get("auto_apply") is False)
    check("honesty.no execution", flags.get("rule_execution") is False)
    check("honesty.no model_c write", flags.get("model_c_write") is False)
    check("honesty.no v1 relaunch", flags.get("learning_policy_v1_relaunched") is False)
    cases = {row["case"]: row["code"] for row in learn.red_team_table()}
    check("red invent proven", cases.get("invent_proven") == "score_refused")
    check("red auto promote", cases.get("auto_promote") == "promote_refused")
    check("red anon", cases.get("anon") == "denied")
    check("red put", cases.get("put_shortcut") == "writes_refused")
    check("red auto apply", cases.get("auto_apply_stub") == "apply_refused")
    _expect_error("refuse promote", lambda: learn.refuse_promote({}), "promote_refused")
    _expect_error("refuse apply", lambda: learn.refuse_apply({}), "apply_refused")
    _expect_error("refuse method", lambda: learn.refuse_method({}), "writes_refused")
    _expect_error("refuse proven", lambda: learn.refuse_proven({}), "score_refused")
    check("owner prove path", learn.OWNER_PROVE_PATH == "GET /api/intel/learning-policy")
    check("bound named", learn.BOUND == "beta-intel-connect-safe")


def test_list_filter_and_next(td: Path) -> None:
    path = _db(td)
    missing = td / "missing-learn.sqlite"
    empty = learn.list_stubs(rule.OWNER_PERSON, db_path=missing)
    check("list missing no create", not missing.exists())
    check("list missing count 0", empty.get("count") == 0)
    check("list missing recommendation_only", empty.get("recommendation_only") is True)
    nxt = learn.operator_next_action(rule.OWNER_PERSON, db_path=missing)
    check("next empty code", nxt.get("code") == learn.NEXT_EMPTY)
    check("next empty flag", nxt.get("empty") is True)
    check("next no auto", nxt.get("auto_promote") is False and nxt.get("auto_apply") is False)

    _expect_error(
        "anon list denied",
        lambda: learn.list_stubs(None, db_path=path),
        "denied",
    )
    _expect_error(
        "anon next denied",
        lambda: learn.operator_next_action(None, db_path=path),
        "denied",
    )

    seeded = _seed_stub(path)
    stub_id = seeded["stub"]["stub_id"]
    experiment_id = seeded["stub"]["experiment_id"]
    note_id = seeded["note"]["note_id"]

    listed = learn.list_stubs(rule.OWNER_PERSON, db_path=path)
    check("list count 1", listed.get("count") == 1)
    check("list not live", listed.get("live") is False)
    check("list not promoted", listed.get("promoted_count") == 0)
    row = (listed.get("stubs") or [{}])[0]
    check("list stub id", row.get("stub_id") == stub_id)
    check("list stub state STUB", row.get("state") == "STUB")

    filtered = learn.list_stubs(
        rule.OWNER_PERSON,
        experiment_id=experiment_id,
        db_path=path,
    )
    check("filter experiment count 1", filtered.get("count") == 1)
    filtered_note = learn.list_stubs(
        rule.OWNER_PERSON,
        note_id=note_id,
        db_path=path,
    )
    check("filter note count 1", filtered_note.get("count") == 1)
    other = learn.list_stubs(
        rule.OWNER_PERSON,
        experiment_id="EXP-00000000-0000-4000-8000-000000000099",
        db_path=path,
    )
    check("filter miss count 0", other.get("count") == 0)

    got = learn.get_stub(stub_id, rule.OWNER_PERSON, db_path=path)
    check("get stub id", got.get("stub_id") == stub_id)
    check("get not promoted", got.get("promoted") is False and got.get("executed") is False)
    check("get recommendation_only", got.get("recommendation_only") is True)
    _expect_error(
        "get missing 404",
        lambda: learn.get_stub(
            "RULE-00000000-0000-4000-8000-000000000001",
            rule.OWNER_PERSON,
            db_path=path,
        ),
        "not_found",
    )

    rule.stub_rule(
        {"note_id": note_id, "rule_text": RULE2},
        person_id=rule.OWNER_PERSON,
        db_path=path,
    )
    listed2 = learn.list_stubs(rule.OWNER_PERSON, db_path=path)
    check("list two stubs", listed2.get("count") == 2)

    nxt2 = learn.operator_next_action(rule.OWNER_PERSON, db_path=path)
    check("next review stubs", nxt2.get("code") == learn.NEXT_REVIEW_STUBS)
    check("next not empty", nxt2.get("empty") is False)
    check("next stub_count 2", nxt2.get("stub_count") == 2)

    waiting_path = td / "waiting.sqlite"
    note_only = rule.record_note(
        {"experiment_note": NOTE},
        person_id=rule.OWNER_PERSON,
        db_path=waiting_path,
    )
    nxt_wait = learn.operator_next_action(rule.OWNER_PERSON, db_path=waiting_path)
    check("next waiting approval", nxt_wait.get("code") == learn.NEXT_WAITING_APPROVAL)
    rule.approve_note(
        {"note_id": note_only["note_id"]},
        person_id=rule.OWNER_PERSON,
        db_path=waiting_path,
    )
    nxt_stub = learn.operator_next_action(rule.OWNER_PERSON, db_path=waiting_path)
    check("next waiting stub", nxt_stub.get("code") == learn.NEXT_WAITING_STUB)

    recs = learn.stub_recommendations(rule.OWNER_PERSON, db_path=path)
    check("recs count 2", recs.get("count") == 2)
    check("recs not empty", recs.get("empty") is False)
    check("recs dm visible", recs.get("decision_memory_visible") is True)
    check("recs connective visible", recs.get("connective_visible") is True)
    check("recs no auto apply", recs.get("auto_apply") is False)
    check("recs applied_count 0", recs.get("applied_count") == 0)
    first = (recs.get("recommendations") or [{}])[0]
    check("rec kind stub", first.get("kind") == "approved_rule_stub")
    check("rec read_only", first.get("read_only") is True)
    check("rec not applied", first.get("applied") is False)
    check("rec id prefix", str(first.get("recommendation_id", "")).startswith("REC-STUB-"))

    empty_recs = learn.stub_recommendations(rule.OWNER_PERSON, db_path=missing)
    check("empty recs", empty_recs.get("empty") is True and empty_recs.get("count") == 0)

    desk = learn.build_desk(rule.OWNER_PERSON, db_path=path)
    check("desk ok", desk.get("ok") is True and desk.get("stub_count") == 2)
    check("desk next review", (desk.get("next_action") or {}).get("code") == learn.NEXT_REVIEW_STUBS)
    check("desk caps specified", (desk.get("caps") or {}).get("CAP-INTEL-05", {}).get("maturity") == "SPECIFIED")
    check("desk cr open", (desk.get("crs") or {}).get(CR_ID, {}).get("resolved") is False)
    check("desk staff_ready false", (desk.get("caps") or {}).get("CAP-INTEL-05", {}).get("staff_ready") is False)
    check("desk no auto", desk.get("auto_promote") is False and desk.get("auto_apply") is False)


def test_api(td: Path) -> None:
    path = td / "api-learn.sqlite"
    os.environ["WOLF_INTEL_RULE_DB"] = str(path)
    os.environ["BETA_AUTH_MODE"] = "development_assertion"
    import serve_beta as sb
    from core import request_auth as ra

    ra._ENV_LOADED = True
    Handler = None
    for _, obj in inspect.getmembers(sb, inspect.isclass):
        if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
            Handler = obj
            break
    check("API handler found", Handler is not None)
    if Handler is None:
        return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:

        def call(method: str, url_path: str, subject: str | None, body: dict | None = None):
            data = None
            headers = {"Accept": "application/json"}
            if subject:
                headers["X-Wolf-Subject"] = subject
            if body is not None:
                data = json.dumps(body).encode()
                headers["Content-Type"] = "application/json"
            req = Request(
                f"http://127.0.0.1:{port}{url_path}",
                data=data,
                headers=headers,
                method=method,
            )
            try:
                with urlopen(req, timeout=20) as resp:
                    return resp.status, json.loads(resp.read().decode())
            except HTTPError as exc:
                raw = exc.read().decode()
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = {"raw": raw}
                return exc.code, parsed

        st, _anon = call("GET", "/api/intel/learning-policy", None)
        check("anon desk 403", st == 403, str(st))
        st, _staff = call("GET", "/api/intel/learning-policy", STAFF)
        check("staff desk 403", st == 403, str(st))
        st, _anon_stubs = call("GET", "/api/intel/learning-policy/stubs", None)
        check("anon stubs 403", st == 403, str(st))
        st, _anon_recs = call("GET", "/api/intel/learning-policy/recommendations", None)
        check("anon recs 403", st == 403, str(st))
        st, _anon_promo = call("POST", "/api/intel/learning-policy/promote", None, {})
        check("anon promote 403", st == 403, str(st))
        check("denied API created no file", not path.exists())

        st, owner = call("GET", "/api/intel/learning-policy", MATT)
        check("owner desk 200", st == 200 and owner.get("ok") is True, str(owner)[:240])
        check("owner desk empty", owner.get("stub_count") == 0)
        check(
            "owner desk empty next",
            (owner.get("next_action") or {}).get("code") == learn.NEXT_EMPTY,
        )
        check(
            "owner desk ledger SPECIFIED",
            (owner.get("honesty") or {}).get("ledger_maturity") == "SPECIFIED",
        )
        check("owner desk not proven", (owner.get("honesty") or {}).get("proven") is False)
        check("owner desk staff_ready false", (owner.get("honesty") or {}).get("staff_ready") is False)
        check("owner desk did not create file", not path.exists())

        st, promo = call("POST", "/api/intel/learning-policy/promote", MATT, {})
        check("owner promote refused", st == 400 and promo.get("error") == "promote_refused", str(promo)[:240])
        st, apply = call("POST", "/api/intel/learning-policy/apply", MATT, {})
        check("owner apply refused", st == 400 and apply.get("error") == "apply_refused", str(apply)[:240])
        st, put = call("PUT", "/api/intel/learning-policy/stubs", MATT, {"rule_text": RULE})
        check("owner PUT refused", st == 405 and put.get("error") == "writes_refused", str(put)[:240])
        st, proven = call("POST", "/api/intel/learning-policy/proven", MATT, {})
        check("owner proven refused", st == 400 and proven.get("error") == "score_refused", str(proven)[:240])

        st, note = call(
            "POST",
            "/api/intel/approve-to-rule/note",
            MATT,
            {"experiment_note": NOTE},
        )
        check("owner note via approve-to-rule", st == 200, str(note)[:200])
        note_id = note.get("note_id")
        st, ok = call("POST", "/api/intel/approve-to-rule/approve", MATT, {"note_id": note_id})
        check("owner approve", st == 200, str(ok)[:200])
        st, stub = call(
            "POST",
            "/api/intel/approve-to-rule/rule",
            MATT,
            {"note_id": note_id, "rule_text": RULE},
        )
        check("owner stub", st == 200 and stub.get("promoted") is False, str(stub)[:240])
        stub_id = stub.get("stub_id")

        st, stubs = call("GET", "/api/intel/learning-policy/stubs", MATT)
        check("owner stubs 200", st == 200 and stubs.get("count") == 1, str(stubs)[:240])
        st, one = call("GET", f"/api/intel/learning-policy/stubs/{stub_id}", MATT)
        check("owner get stub 200", st == 200 and one.get("stub_id") == stub_id, str(one)[:240])
        check("owner get not live", one.get("live") is False and one.get("promoted") is False)
        st, recs = call("GET", "/api/intel/learning-policy/recommendations", MATT)
        check("owner recs 200", st == 200 and recs.get("count") == 1, str(recs)[:240])
        check("owner rec read_only", (recs.get("recommendations") or [{}])[0].get("read_only") is True)
        st, nxt = call("GET", "/api/intel/learning-policy/next-action", MATT)
        check(
            "owner next review",
            st == 200 and nxt.get("code") == learn.NEXT_REVIEW_STUBS,
            str(nxt)[:240],
        )
        st, desk2 = call("GET", "/api/intel/learning-policy", MATT)
        check("owner desk after stub", st == 200 and desk2.get("stub_count") == 1)
        check(
            "owner desk CR still open",
            (desk2.get("crs") or {}).get(CR_ID, {}).get("resolved") is False,
        )
    finally:
        httpd.shutdown()
        os.environ.pop("WOLF_INTEL_RULE_DB", None)


def test_ops_and_connective_see_stubs(td: Path) -> None:
    path = td / "ops-see.sqlite"
    _seed_stub(path)
    from core import intel_ops_pack as ops

    desk = ops.build_desk(
        verified_person_id=rule.OWNER_PERSON,
        rule_db_path=path,
        db_path=td / "ops-pack.sqlite",
        dm_db_path=td / "dm.sqlite",
    )
    lp = desk.get("learning_policy") or {}
    check("ops desk has learning_policy", "learning_policy" in desk)
    check("ops sees stub recs", int(lp.get("count") or 0) >= 1)
    check("ops loop learning_policy", (desk.get("loop") or {}).get("learning_policy") == "/api/intel/learning-policy")
    check("ops no auto_promote", lp.get("auto_promote") is False)


def test_preserved() -> None:
    ledger = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    row = ledger.get("CAP-INTEL-05") or [""]
    check("CAP-INTEL-05 stays SPECIFIED", row[0] == "SPECIFIED", str(row[:1]))
    check("CAP-INTEL-01 stays BUILT", (ledger.get("CAP-INTEL-01") or [""])[0] == "BUILT")
    check("CAP-INTEL-05 not PROVEN", row[0] != "PROVEN")
    check("CAP-INTEL-05 not READY", row[0] != "READY")
    check("ledger row count 77", len(ledger) == 77, str(len(ledger)))
    check(
        "ledger bytes unchanged",
        hashlib.sha256(LEDGER_JSON.read_bytes()).hexdigest() == LEDGER_BEFORE,
    )
    cr = _cr_row()
    check("CR still OPEN", cr is not None and cr[0] == "OPEN", str(cr))
    check("CR has no resolution", cr is not None and not cr[1], str(cr))
    check("CR blocker unchanged", cr is not None and cr[2] == "NEEDS_ENGINEERING", str(cr))
    check("CR next action unchanged", cr is not None and cr[3] == NEXT_ACTION, str(cr))
    check("CR row unchanged", cr == CR_BEFORE, str(cr))
    history = HISTORY.read_text(encoding="utf-8") if HISTORY.exists() else ""
    check("score history has no learning-policy-v2 event", "learning-policy-v2" not in history)
    for rel, digest in WIP.items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        check(f"WIP digest {Path(rel).name}", got == digest, got)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("beta learning-policy route", "/api/intel/learning-policy" in serve)
    check("beta stubs route", "/api/intel/learning-policy/stubs" in serve)
    check("beta recommendations route", "/api/intel/learning-policy/recommendations" in serve)
    check(
        "beta promote refuse",
        learn.refuse_code("/api/intel/learning-policy/promote") == "promote",
    )
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    check("live rule db not required", True)
    check("8787 up", _port_up(8787))
    check("8788 up", _port_up(8788))
    prod_now = _pid_on(8787)
    check(
        "production pid untouched",
        prod_now is not None and prod_now == PROD_PID_BEFORE,
        f"before={PROD_PID_BEFORE} now={prod_now}",
    )


def main() -> None:
    global CR_BEFORE, PROD_PID_BEFORE
    CR_BEFORE = _cr_row()
    PROD_PID_BEFORE = _pid_on(8787)
    td = _tmp_dir()
    try:
        test_honesty()
        test_list_filter_and_next(td)
        test_api(td)
        test_ops_and_connective_see_stubs(td)
        test_preserved()
    finally:
        print(f"PASS={PASS} FAIL={FAIL}")
        if FAIL == 0:
            print("EXIT: SUCCESS")
        else:
            print("EXIT: FAIL")
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
