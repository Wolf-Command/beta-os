#!/usr/bin/env python3
"""Approve-to-rule skeleton (Beta). Stub is not promoted. CAP-INTEL-05 not raised."""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
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

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "intel_approve_to_rule.sqlite"
LEDGER_JSON = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "intel_approve_to_rule.py"
CR_ID = "CR-be51980bd1194448"
NEXT_ACTION = "Approve-to-rule learning loop"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
ROLE = "PERS-INTEL-ROLE"

NOTE = "The close missed the tin count on a quiet Tuesday service."
NOTE2 = "A second note: the miss was on the drawer, not the card."
RULE = "Count the tin before the drawer is closed and write the number."
RULE2 = "Write the tin count on the card before the drawer is locked."

FORBIDDEN_STAGE = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
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


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _tmp_dir() -> Path:
    td = ROOT / "catalog" / "backups" / f"tmp-intel-rule-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    return td


def _db(td: Path) -> Path:
    return td / "approve_to_rule.sqlite"


def _note(**overrides: object) -> dict:
    body: dict = {"experiment_note": NOTE}
    body.update(overrides)
    return body


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


def _expect_error(name: str, fn, code: str) -> None:
    try:
        fn()
    except rule.IntelRuleError as exc:
        check(name, exc.code == code, exc.code)
        return
    except Exception as exc:  # noqa: BLE001
        check(name, False, type(exc).__name__ + " " + str(exc))
        return
    check(name, False, "no error")


def _stub_count(path: Path) -> int:
    if not path.exists():
        return 0
    conn = sqlite3.connect(str(path))
    try:
        return int(conn.execute("SELECT COUNT(*) FROM intel_rule_stubs").fetchone()[0])
    finally:
        conn.close()


def test_honesty_and_source() -> None:
    flags = rule.honesty_flags()
    check("honesty.cr_bound", flags.get("cr_id") == CR_ID and flags.get("cr_bound") is True)
    check("honesty.cr_present", flags.get("cr_present") is True)
    check("honesty.cr_open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("honesty.cr_not_resolved", flags.get("cr_resolved") is False)
    check("honesty.cr_not_mutated", flags.get("cr_mutated") is False)
    check(
        "honesty.cr_next",
        flags.get("cr_next_action") == NEXT_ACTION,
        str(flags.get("cr_next_action")),
    )
    check("honesty.cap", flags.get("cap") == "CAP-INTEL-05")
    check("honesty.maturity_is_ledger", flags.get("maturity") == flags.get("ledger_maturity"))
    check(
        "honesty.ledger_specified",
        flags.get("ledger_maturity") == "SPECIFIED",
        str(flags.get("ledger_maturity")),
    )
    check("honesty.ceiling_built", flags.get("maturity_ceiling") == "BUILT")
    check("honesty.skeleton_label_built", flags.get("framework_skeleton") == "BUILT")
    check("honesty.not_proven", flags.get("proven") is False)
    check("honesty.not_ready", flags.get("ready") is False)
    check("honesty.no_auto_promote", flags.get("auto_promote") is False)
    check("honesty.no_execution", flags.get("rule_execution") is False)
    check("honesty.no_production_rules", flags.get("production_rules") is False)
    check("honesty.no_model_c_write", flags.get("model_c_write") is False)
    check("honesty.append_only", flags.get("append_only") is True)
    check("ceiling specified is BUILT", rule.ceiling_for("SPECIFIED") == "BUILT")
    check("ceiling absent is BUILT", rule.ceiling_for("ABSENT") == "BUILT")
    check("ceiling already PROVEN stays PROVEN", rule.ceiling_for("PROVEN") == "PROVEN")
    check("ceiling already READY stays READY", rule.ceiling_for("READY") == "READY")
    cases = {row["case"]: row["code"] for row in rule.red_team_table()}
    check("red team invent proven", cases.get("invent_proven") == "score_refused")
    check("red team auto promote", cases.get("auto_promote") == "promote_refused")
    check("red team anon", cases.get("anon") == "denied")
    check("red team write without approve", cases.get("write_without_approve") == "approve_required")
    check("owner prove path named", rule.OWNER_PROVE_PATH == "GET /api/intel/approve-to-rule")
    src = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    joined = " ".join(imported)
    check("module does not import wolf_intelligence", "wolf_intelligence" not in joined)
    check("module has no urllib", "urllib" not in joined and "requests" not in joined)
    check("module does not bind 8787", "8787" not in src)
    check("module does not json.dump", "json.dump" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    _expect_error("refuse promote", lambda: rule.refuse_promote({}), "promote_refused")
    _expect_error("refuse proven", lambda: rule.refuse_proven({}), "score_refused")
    _expect_error("refuse execute", lambda: rule.refuse_execute({}), "execute_refused")
    _expect_error("refuse production", lambda: rule.refuse_production({}), "production_refused")


def test_loop(td: Path) -> None:
    path = _db(td)
    missing = td / "missing-rule.sqlite"
    empty = rule.list_experiments(rule.OWNER_PERSON, db_path=missing)
    check("list missing does not create", not missing.exists())
    check("list missing count 0", empty.get("count") == 0)
    check("list missing not live", empty.get("live") is False)
    check("list missing no promote", empty.get("auto_promote") is False)
    check("list missing red team", len(empty.get("red_team") or []) == 4)

    _expect_error(
        "anon note denied",
        lambda: rule.record_note(_note(), person_id=None, db_path=path),
        "denied",
    )
    _expect_error(
        "other person denied",
        lambda: rule.record_note(_note(), person_id="PERS-OTHER", db_path=path),
        "denied",
    )
    check("denied created no file", not path.exists())
    _expect_error(
        "proven field refused",
        lambda: rule.record_note(_note(proven=True), person_id=rule.OWNER_PERSON, db_path=path),
        "score_refused",
    )
    _expect_error(
        "ready word refused",
        lambda: rule.record_note(
            {"experiment_note": "READY"},
            person_id=rule.OWNER_PERSON,
            db_path=path,
        ),
        "score_refused",
    )
    check("score refuse created no file", not path.exists())
    _expect_error(
        "live default write guarded",
        lambda: rule.record_note(_note(), person_id=rule.OWNER_PERSON, db_path=None),
        "live_guard",
    )
    check("live guard created no file", not LIVE_DB.exists())

    rec = rule.record_note(_note(), person_id=rule.OWNER_PERSON, db_path=path)
    check("note appended", rec.get("appended") is True and str(rec.get("note_id", "")).startswith("NOTE-"))
    check("note not a rule", rec.get("rule_created") is False and rec.get("approved") is False)
    check("note not promoted", rec.get("promoted") is False and rec.get("live") is False)
    note_id = rec["note_id"]
    experiment_id = rec["experiment_id"]

    _expect_error(
        "stub without approve",
        lambda: rule.stub_rule(
            {"note_id": note_id, "rule_text": RULE},
            person_id=rule.OWNER_PERSON,
            db_path=path,
        ),
        "approve_required",
    )
    check("unapproved stub count 0", _stub_count(path) == 0)

    missing_stub = td / "stub-missing.sqlite"
    _expect_error(
        "stub missing does not create",
        lambda: rule.stub_rule(
            {"note_id": note_id, "rule_text": RULE},
            person_id=rule.OWNER_PERSON,
            db_path=missing_stub,
        ),
        "not_found",
    )
    check("stub missing created no file", not missing_stub.exists())

    approved = rule.approve_note(
        {"note_id": note_id},
        person_id=rule.OWNER_PERSON,
        db_path=path,
    )
    check("approve appended", approved.get("appended") is True and str(approved.get("approval_id", "")).startswith("APR-"))
    check("approve does not create rule", approved.get("rule_created") is False)
    check("approve does not promote", approved.get("promoted") is False and approved.get("live") is False)
    check("approve leaves note", approved.get("note_unchanged") is True)
    check("still no stub after approve", _stub_count(path) == 0)

    stub = rule.stub_rule(
        {"note_id": note_id, "rule_text": RULE},
        person_id=rule.OWNER_PERSON,
        db_path=path,
    )
    check("stub appended", stub.get("appended") is True and stub.get("version_n") == 1)
    check("stub state", stub.get("state") == "STUB" and stub.get("promoted") is False)
    check("stub not executed", stub.get("executed") is False and stub.get("production") is False)
    check("stub id", str(stub.get("stub_id", "")).startswith("RULE-"))

    stub2 = rule.stub_rule(
        {"note_id": note_id, "rule_text": RULE2},
        person_id=rule.OWNER_PERSON,
        db_path=path,
    )
    check("stub version 2", stub2.get("version_n") == 2 and stub2.get("promoted") is False)
    check("two stubs", _stub_count(path) == 2)

    listed = rule.list_experiments(rule.OWNER_PERSON, db_path=path)
    check("list count 1", listed.get("count") == 1)
    row = (listed.get("experiments") or [{}])[0]
    check("list is stub not live", row.get("state") == "STUB" and row.get("live") is False)
    check("list latest version 2", row.get("latest_stub_version") == 2)
    check("list promoted count 0", listed.get("promoted_count") == 0)
    check("list executed count 0", listed.get("executed_count") == 0)

    got = rule.read_experiment(experiment_id, rule.OWNER_PERSON, db_path=path)
    check("read two stubs", len(got.get("stubs") or []) == 2)
    check("read v1 still stub", (got.get("stubs") or [{}])[0].get("version_n") == 1)
    check("read v1 not promoted", (got.get("stubs") or [{}])[0].get("promoted") is False)
    check("read note approved", (got.get("notes") or [{}])[0].get("approved") is True)
    check("read note still NOTED row", (got.get("notes") or [{}])[0].get("state") == "NOTED")

    _expect_error(
        "second approve refused",
        lambda: rule.approve_note(
            {"note_id": note_id},
            person_id=rule.OWNER_PERSON,
            db_path=path,
        ),
        "already_approved",
    )
    _expect_error(
        "promote field on stub refused",
        lambda: rule.stub_rule(
            {"note_id": note_id, "rule_text": RULE, "promote": True},
            person_id=rule.OWNER_PERSON,
            db_path=path,
        ),
        "promote_refused",
    )
    check("promote field wrote no third stub", _stub_count(path) == 2)

    nxt = rule.record_note(
        {"experiment_note": NOTE2, "experiment_id": experiment_id},
        person_id=rule.OWNER_PERSON,
        db_path=path,
    )
    check("second note appended", nxt.get("note_n") == 2 and nxt.get("approved") is False)
    _expect_error(
        "second note cannot stub",
        lambda: rule.stub_rule(
            {"note_id": nxt["note_id"], "rule_text": RULE},
            person_id=rule.OWNER_PERSON,
            db_path=path,
        ),
        "approve_required",
    )
    check("second note wrote no stub", _stub_count(path) == 2)

    role_path = td / "role.sqlite"
    role_note = rule.record_note(_note(), person_id=ROLE, role_allowed=True, db_path=role_path)
    check("role can note", role_note.get("gate") == "role" and role_note.get("rule_created") is False)
    role_ok = rule.approve_note(
        {"note_id": role_note["note_id"]},
        person_id=ROLE,
        role_allowed=True,
        db_path=role_path,
    )
    check("role can approve", role_ok.get("gate") == "role" and role_ok.get("rule_created") is False)
    role_stub = rule.stub_rule(
        {"note_id": role_note["note_id"], "rule_text": RULE},
        person_id=ROLE,
        role_allowed=True,
        db_path=role_path,
    )
    check("role stub not promoted", role_stub.get("gate") == "role" and role_stub.get("promoted") is False)
    _expect_error(
        "role flag without grant denied",
        lambda: rule.record_note(_note(), person_id=ROLE, role_allowed=False, db_path=td / "nope.sqlite"),
        "denied",
    )
    check("role deny created no file", not (td / "nope.sqlite").exists())


def test_append_only_and_paths(td: Path) -> None:
    path = _db(td)
    rec = rule.record_note(_note(), person_id=rule.OWNER_PERSON, db_path=td / "locks.sqlite")
    lock = td / "locks.sqlite"
    conn = sqlite3.connect(str(lock))
    try:
        conn.execute(
            "UPDATE intel_experiment_notes SET experiment_note=? WHERE note_id=?",
            ("rewritten note text", rec["note_id"]),
        )
        conn.commit()
        check("note update aborted", False, "update committed")
    except sqlite3.IntegrityError as exc:
        check("note update aborted", "append-only" in str(exc), str(exc))
    try:
        conn.execute("DELETE FROM intel_experiment_notes WHERE note_id=?", (rec["note_id"],))
        conn.commit()
        check("note delete aborted", False, "delete committed")
    except sqlite3.IntegrityError as exc:
        check("note delete aborted", "append-only" in str(exc), str(exc))
    finally:
        conn.close()

    approved = rule.approve_note(
        {"note_id": rec["note_id"]},
        person_id=rule.OWNER_PERSON,
        db_path=lock,
    )
    made = rule.stub_rule(
        {"note_id": rec["note_id"], "rule_text": RULE},
        person_id=rule.OWNER_PERSON,
        db_path=lock,
    )
    check("lock stub version 1", made.get("version_n") == 1 and approved.get("rule_created") is False)
    conn = sqlite3.connect(str(lock))
    try:
        conn.execute(
            "UPDATE intel_rule_stubs SET promoted=0 WHERE stub_id=?",
            (made["stub_id"],),
        )
        conn.commit()
        check("stub update aborted", False, "update committed")
    except sqlite3.IntegrityError as exc:
        check("stub update aborted", "append-only" in str(exc), str(exc))
    try:
        conn.execute(
            """
            INSERT INTO intel_rule_stubs (
              stub_id, experiment_id, note_id, approval_id, version_n, rule_text,
              state, promoted, executed, created_by, created_at
            ) VALUES (?, ?, ?, ?, 9, ?, 'STUB', 1, 0, ?, '2026-09-20T00:00:00Z')
            """,
            (
                "RULE-00000000-0000-4000-8000-000000000099",
                made["experiment_id"],
                rec["note_id"],
                approved["approval_id"],
                RULE,
                rule.OWNER_PERSON,
            ),
        )
        conn.commit()
        check("promoted insert aborted", False, "insert committed")
    except sqlite3.IntegrityError as exc:
        check("promoted insert aborted", "CHECK" in str(exc).upper() or "constraint" in str(exc).lower(), str(exc))
    finally:
        conn.close()
    check("promoted insert wrote no row", _stub_count(lock) == 1)

    triggers = set()
    conn = sqlite3.connect(str(lock))
    try:
        triggers = {
            str(row[0])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        }
        tables = {
            str(row[0])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        conn.close()
    check("trigger notes", "trg_intel_notes_no_update" in triggers and "trg_intel_notes_no_delete" in triggers)
    check("trigger approvals", "trg_intel_approvals_no_update" in triggers)
    check("trigger stubs", "trg_intel_stubs_no_update" in triggers and "trg_intel_stubs_no_delete" in triggers)
    check("no production table", "production_rules" not in tables and "intel_rule_stubs" in tables)

    _expect_error(
        "alchemist path refused",
        lambda: rule.list_experiments(
            rule.OWNER_PERSON,
            db_path=ROOT / "catalog" / "alchemist-rule.sqlite",
        ),
        "alchemist_refused",
    )
    _expect_error(
        "production path refused",
        lambda: rule.list_experiments(
            rule.OWNER_PERSON,
            db_path=ROOT / "production" / "rules.sqlite",
        ),
        "not_beta",
    )
    check("unused path arg", path.name == "approve_to_rule.sqlite")


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
    credits = (ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md").read_text(encoding="utf-8")
    check("credits SPECIFIED 0.05", "| SPECIFIED | 0.05 |" in credits)
    check("credits BUILT 0.25", "| BUILT | 0.25 |" in credits)
    check("credits PROVEN 0.80", "| PROVEN | 0.80 |" in credits)
    history = HISTORY.read_text(encoding="utf-8") if HISTORY.exists() else ""
    check("score history has no approve-to-rule event", "approve-to-rule" not in history)
    check("score history has no CAP-INTEL-05 event", "CAP-INTEL-05" not in history)
    for rel, digest in WIP.items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        check(f"WIP digest {Path(rel).name}", got == digest, got)
    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    for rel in FORBIDDEN_STAGE:
        check(f"WIP not staged {Path(rel).name}", rel not in staged, str(staged))
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("beta note route", "/api/intel/approve-to-rule/note" in serve)
    check("beta approve route", "/api/intel/approve-to-rule/approve" in serve)
    check("beta rule route", "/api/intel/approve-to-rule/rule" in serve)
    check("beta promote route", "/api/intel/approve-to-rule/promote" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    check("live rule db not created by tests", not LIVE_DB.exists())


def test_api(td: Path) -> None:
    path = td / "api-rule.sqlite"
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

        st, _anon = call("GET", "/api/intel/approve-to-rule", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/intel/approve-to-rule", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, _anon_post = call("POST", "/api/intel/approve-to-rule/note", None, _note())
        check("anon POST 403", st == 403, str(st))
        st, _anon_rule = call(
            "POST",
            "/api/intel/approve-to-rule/rule",
            None,
            {"note_id": "NOTE-00000000-0000-4000-8000-000000000001", "rule_text": RULE},
        )
        check("anon rule 403", st == 403, str(st))
        st, _anon_promote = call("POST", "/api/intel/approve-to-rule/promote", None, {})
        check("anon promote 403", st == 403, str(st))
        st, _staff_post = call("POST", "/api/intel/approve-to-rule/approve", STAFF, {"note_id": "NOTE-x"})
        check("staff POST 403", st == 403, str(st))
        check("denied API created no file", not path.exists())

        st, owner = call("GET", "/api/intel/approve-to-rule", MATT)
        check("owner GET 200", st == 200 and owner.get("ok") is True, str(owner)[:240])
        check("owner GET empty", owner.get("count") == 0)
        check("owner GET bound to CR", (owner.get("honesty") or {}).get("cr_id") == CR_ID)
        check("owner GET ceiling BUILT", (owner.get("honesty") or {}).get("maturity_ceiling") == "BUILT")
        check("owner GET ledger SPECIFIED", (owner.get("honesty") or {}).get("ledger_maturity") == "SPECIFIED")
        check("owner GET not proven", (owner.get("honesty") or {}).get("proven") is False)
        check("owner prove path", owner.get("owner_prove_path") == rule.OWNER_PROVE_PATH)
        check("owner GET did not create file", not path.exists())

        st, bad = call("POST", "/api/intel/approve-to-rule/note", MATT, {**_note(), "proven": True})
        check("owner invent PROVEN 400", st == 400 and bad.get("error") == "score_refused", str(bad)[:240])
        check("invent PROVEN created no file", not path.exists())
        st, ready = call("POST", "/api/intel/approve-to-rule/proven", MATT, {})
        check("owner proven route refused", st == 400 and ready.get("error") == "score_refused", str(ready)[:240])

        st, made = call("POST", "/api/intel/approve-to-rule/note", MATT, _note())
        check("owner note 200", st == 200 and made.get("rule_created") is False, str(made)[:300])
        note_id = made.get("note_id")
        experiment_id = made.get("experiment_id")
        st, early = call(
            "POST",
            "/api/intel/approve-to-rule/rule",
            MATT,
            {"note_id": note_id, "rule_text": RULE},
        )
        check("write without approve 400", st == 400 and early.get("error") == "approve_required", str(early)[:240])
        check("early rule wrote no stub", _stub_count(path) == 0)

        st, ok = call("POST", "/api/intel/approve-to-rule/approve", MATT, {"note_id": note_id})
        check("owner approve 200", st == 200 and ok.get("rule_created") is False, str(ok)[:240])
        st, stub = call(
            "POST",
            "/api/intel/approve-to-rule/rule",
            MATT,
            {"note_id": note_id, "rule_text": RULE},
        )
        check("owner stub 200", st == 200 and stub.get("promoted") is False and stub.get("version_n") == 1, str(stub)[:240])
        st, promo = call("POST", "/api/intel/approve-to-rule/promote", MATT, {})
        check("owner auto-promote 400", st == 400 and promo.get("error") == "promote_refused", str(promo)[:240])
        st, put = call("PUT", "/api/intel/approve-to-rule/rule", MATT, {"note_id": note_id, "rule_text": RULE2})
        check("owner PUT 405", st == 405 and put.get("error") == "writes_refused", str(put)[:240])
        check("promote and PUT wrote no extra stub", _stub_count(path) == 1)
        st, one = call("GET", f"/api/intel/approve-to-rule/{experiment_id}", MATT)
        check("owner read stub", st == 200 and one.get("live") is False, str(one)[:240])
        check("owner read not promoted", one.get("promoted") is False and one.get("stub_count") == 1)
    finally:
        httpd.shutdown()
        os.environ.pop("WOLF_INTEL_RULE_DB", None)


def main() -> None:
    global CR_BEFORE
    CR_BEFORE = _cr_row()
    td = _tmp_dir()
    try:
        test_honesty_and_source()
        test_loop(td)
        test_append_only_and_paths(td)
        test_api(td)
        test_preserved()
    finally:
        print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
