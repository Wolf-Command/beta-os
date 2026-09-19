#!/usr/bin/env python3
"""CAP-DR-02 failure domains. Beta is not Production. Slots stay empty. No restore."""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import shutil
import sqlite3
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
os.environ.pop("WOLF_ALCHEMIST_DB", None)
os.environ.pop("WOLF_ESB_SQLITE", None)

from core import failure_domains as domains  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "failure_domains.py"
CR_ID = "CR-01fc21cfe028333b"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
STEP_IDS = (
    "CHK-NAME-BETA",
    "CHK-NAME-PRODUCTION",
    "CHK-BETA-NE-PRODUCTION",
    "CHK-NO-COLLAPSE",
    "CHK-NO-LIVE-RESTORE",
    "CHK-NO-NAS",
    "CHK-NO-B2",
    "CHK-NO-PRODUCTION-WRITE",
    "CHK-INDEPENDENCE-SLOT",
    "CHK-PLAYBOOK-UNREAD",
)
DOMAIN_IDS = ("DOMAIN-BETA", "DOMAIN-PRODUCTION", "DOMAIN-NAS", "DOMAIN-B2")


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _cr_row() -> tuple | None:
    conn = sqlite3.connect(str(CATALOG_DB))
    try:
        return conn.execute(
            "SELECT state, blocker_class, capability, next_action FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
    finally:
        conn.close()


def _resolved_count() -> int:
    conn = sqlite3.connect(str(CATALOG_DB))
    try:
        return int(
            conn.execute("SELECT COUNT(*) FROM wolf_completion_items WHERE state='RESOLVED'").fetchone()[0]
        )
    finally:
        conn.close()


def _copy_log() -> dict:
    return json.loads(json.dumps(domains.not_run_log()))


def test_live_framework() -> None:
    report = domains.build_framework()
    steps = report["checklist"]
    named = report["domains"]
    check("ten steps", [row["id"] for row in steps] == list(STEP_IDS), str([row["id"] for row in steps]))
    check(
        "none executed",
        all(row["executed"] is False and row["result"] == "NOT_RUN" and row["slot"] == "EMPTY" and row["required"] is True for row in steps),
    )
    check("executed count zero", report["checklist_executed"] == 0 and report["checklist_count"] == 10)
    check("empty slots", report["empty_slot_count"] == 14 and report["slots_filled"] is False)
    check("status not run", report["status"] == "NOT_RUN" and report["live_restore"] is False)
    check("four domains", [row["id"] for row in named] == list(DOMAIN_IDS) and report["domain_count"] == 4)
    check(
        "domains uncontacted",
        all(row["contacted"] is False and row["mutated"] is False and row["independence_proved"] is False and row["slot"] == "EMPTY" for row in named),
    )
    by_id = {row["id"]: row for row in named}
    check(
        "beta is not production",
        report["beta_equals_production"] is False
        and report["domains_collapsed"] is False
        and "DOMAIN-PRODUCTION" in by_id["DOMAIN-BETA"]["distinct_from"]
        and "DOMAIN-BETA" in by_id["DOMAIN-PRODUCTION"]["distinct_from"],
    )
    check("nas and b2 distinct", "DOMAIN-NAS" in by_id["DOMAIN-BETA"]["distinct_from"] and "DOMAIN-B2" in by_id["DOMAIN-PRODUCTION"]["distinct_from"])
    split = report["separation"]
    check(
        "separation documented not proved",
        split["beta"] == "DOMAIN-BETA"
        and split["production"] == "DOMAIN-PRODUCTION"
        and split["beta_equals_production"] is False
        and split["same_failure_domain"] is False
        and split["separation"] == "DOCUMENTED"
        and split["independence_proved"] is False
        and split["slot"] == "EMPTY",
    )
    book = report["playbook"]
    check("playbook unread", book["read"] is False and book["copied"] is False and book["slot"] == "EMPTY")
    schema = report["schema"]
    check("schema id", schema["schema_id"] == domains.SCHEMA_ID and schema["additionalProperties"] is False)
    check("schema only not-run", schema["status_enum"] == ["NOT_RUN"] and schema["slot_enum"] == ["EMPTY"])
    check("schema names refused success", "SUCCESS" in schema["refused_status"] and "READY" in schema["refused_status"] and "PROVEN" in schema["refused_status"])
    log = report["log"]
    check("log not run", log["status"] == "NOT_RUN" and log["result"] == "NOT_RUN" and log["prove_id"] is None)
    check(
        "log claims nothing",
        log["live_restore"] is False
        and log["production_mutated"] is False
        and log["nas_destructive"] is False
        and log["b2_destructive"] is False
        and log["beta_equals_production"] is False
        and log["independence_proved"] is False
        and log["slots_filled"] is False,
    )
    check("log does not claim ready", log["ready_claimed"] is False and log["proven_claimed"] is False and log["playbook_read"] is False)
    check("log valid", report["log_valid"] is True)
    dumped_log = json.dumps(log)
    check("log text has no success word", "SUCCESS" not in dumped_log and "RESTORED" not in dumped_log)
    flags = report["honesty"]
    check("honesty.cr_bound", flags.get("cr_id") == CR_ID and flags.get("cr_bound") is True)
    check("honesty.cr_present", flags.get("cr_present") is True)
    check("honesty.cr_open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("honesty.cr_not_resolved", flags.get("cr_resolved") is False)
    check("honesty.cr_cap", flags.get("cr_capability") == "CAP-DR-02")
    check("honesty.cr_blocker", flags.get("cr_blocker") == "NEEDS_ENGINEERING", str(flags.get("cr_blocker")))
    check("honesty.cr_next", flags.get("cr_next_action") == "Independent failure domains prove", str(flags.get("cr_next_action")))
    check("honesty.maturity_is_ledger", flags.get("maturity") == flags.get("ledger_maturity") == "SPECIFIED")
    check("honesty.ceiling_built", flags.get("maturity_ceiling") == "BUILT")
    check("honesty.skeleton", flags.get("framework_skeleton") == "BUILT")
    check("honesty.not_proven", flags.get("proven") is False and flags.get("ready") is False)
    check("honesty.not_invented", flags.get("invented_proven") is False and flags.get("invented_ready") is False)
    check("honesty.no_raise", flags.get("model_c_maturity_raised") is False and flags.get("model_c_write") is False)
    check("honesty.no_restore", flags.get("live_restore") is False and flags.get("nas_destructive") is False and flags.get("b2_destructive") is False)
    check("honesty.not_independent", flags.get("independence_proved") is False and flags.get("beta_equals_production") is False and flags.get("slots_filled") is False)
    check("pack flags", report["ledger_write"] is False and report["external_writes"] is False and report["production_mutated"] is False and report["independence_proved"] is False)
    one = domains.read_step("CHK-INDEPENDENCE-SLOT")
    check("read independence step", one["ok"] is True and one["step"]["executed"] is False and one["step"]["slot"] == "EMPTY")
    check("read step bound", (one.get("honesty") or {}).get("cr_id") == CR_ID)
    beta = domains.read_domain("DOMAIN-BETA")
    check("read beta domain", beta["ok"] is True and beta["domain"]["slot"] == "EMPTY" and beta["beta_equals_production"] is False)
    prod = domains.read_domain("DOMAIN-PRODUCTION")
    check("read production domain", prod["domain"]["contacted"] is False and prod["domain"]["mutated"] is False and "DOMAIN-BETA" in prod["domain"]["distinct_from"])
    validated = domains.validate_log(domains.not_run_log())
    check("validate exemplar", validated["ok"] is True and validated["valid"] is True and validated["independence_proved"] is False)


def test_refuses(td: Path) -> None:
    before = list(td.iterdir())
    cases = [
        ("live restore flag", {"live_restore": True}, "live_restore_refused"),
        ("production flag", {"production_mutated": True}, "production_refused"),
        ("nas flag", {"nas_destructive": True}, "nas_destructive_refused"),
        ("b2 flag", {"b2_destructive": True}, "b2_destructive_refused"),
        ("collapse flag", {"beta_equals_production": True}, "collapse_refused"),
        ("domains collapsed", {"domains_collapsed": True}, "collapse_refused"),
        ("independence flag", {"independence_proved": True}, "independence_refused"),
        ("slots flag", {"slots_filled": True}, "slots_refused"),
        ("playbook flag", {"playbook_read": True}, "playbook_refused"),
        ("playbook copied", {"playbook_copied": True}, "playbook_refused"),
        ("ready flag", {"ready_claimed": True}, "ready_refused"),
        ("proven flag", {"proven_claimed": True}, "proven_refused"),
        ("success status", {"status": "SUCCESS"}, "success_refused"),
        ("restored result", {"result": "RESTORED"}, "success_refused"),
        ("proved status", {"status": "PROVED"}, "independence_refused"),
        ("ready status", {"status": "READY"}, "ready_refused"),
        ("filled status", {"status": "FILLED"}, "slots_refused"),
    ]
    for name, patch, code in cases:
        payload = _copy_log()
        payload.update(patch)
        try:
            domains.validate_log(payload)
            check(name, False, "accepted")
        except domains.FailureDomainError as exc:
            check(name, exc.code == code, exc.code)
    executed = _copy_log()
    executed["checklist"][4]["executed"] = True
    executed["checklist"][4]["result"] = "SUCCESS"
    try:
        domains.validate_log(executed)
        check("executed step refused", False)
    except domains.FailureDomainError as exc:
        check("executed step refused", exc.code == "live_restore_refused", exc.code)
    filled = _copy_log()
    filled["checklist"][8]["slot"] = "FILLED"
    try:
        domains.validate_log(filled)
        check("filled slot refused", False)
    except domains.FailureDomainError as exc:
        check("filled slot refused", exc.code == "slots_refused", exc.code)
    contacted = _copy_log()
    contacted["domains"][2]["contacted"] = True
    try:
        domains.validate_log(contacted)
        check("nas contact refused", False)
    except domains.FailureDomainError as exc:
        check("nas contact refused", exc.code == "nas_destructive_refused", exc.code)
    mutated = _copy_log()
    mutated["domains"][1]["mutated"] = True
    try:
        domains.validate_log(mutated)
        check("production mutate in domains refused", False)
    except domains.FailureDomainError as exc:
        check("production mutate in domains refused", exc.code == "production_refused", exc.code)
    short = _copy_log()
    short["checklist"] = short["checklist"][:9]
    try:
        domains.validate_log(short)
        check("short checklist refused", False)
    except domains.FailureDomainError as exc:
        check("short checklist refused", exc.code == "bad_log", exc.code)
    extra = _copy_log()
    extra["bytes_restored"] = 1
    try:
        domains.validate_log(extra)
        check("extra field refused", False)
    except domains.FailureDomainError as exc:
        check("extra field refused", exc.code == "bad_log", exc.code)
    stamped = _copy_log()
    stamped["prove_id"] = "PROVE-LIVE"
    stamped["recorded_at"] = "2026-09-20T00:00:00Z"
    try:
        domains.validate_log(stamped)
        check("stamped log refused", False)
    except domains.FailureDomainError as exc:
        check("stamped log refused", exc.code == "bad_log", exc.code)
    try:
        domains.validate_log(["not", "a", "log"])  # type: ignore[arg-type]
        check("non object refused", False)
    except domains.FailureDomainError as exc:
        check("non object refused", exc.code == "bad_log", exc.code)
    try:
        domains.read_step("CHK-NO-SUCH")
        check("missing step refused", False)
    except domains.FailureDomainError as exc:
        check("missing step refused", exc.code == "not_found", exc.code)
    try:
        domains.read_domain("DOMAIN-NO-SUCH")
        check("missing domain refused", False)
    except domains.FailureDomainError as exc:
        check("missing domain refused", exc.code == "not_found", exc.code)
    try:
        domains.read_step("run")
        check("run id refused", False)
    except domains.FailureDomainError as exc:
        check("run id refused", exc.code == "live_restore_refused", exc.code)
    try:
        domains.read_step("prove")
        check("prove id refused", False)
    except domains.FailureDomainError as exc:
        check("prove id refused", exc.code == "independence_refused", exc.code)
    try:
        domains.read_domain("production")
        check("production id refused", False)
    except domains.FailureDomainError as exc:
        check("production id refused", exc.code == "production_refused", exc.code)
    try:
        domains.guard_query(restore="1")
        check("query restore refused", False)
    except domains.FailureDomainError as exc:
        check("query restore refused", exc.code == "live_restore_refused", exc.code)
    try:
        domains.guard_query(prove="1")
        check("query prove refused", False)
    except domains.FailureDomainError as exc:
        check("query prove refused", exc.code == "independence_refused", exc.code)
    try:
        domains.guard_query(collapse="1")
        check("query collapse refused", False)
    except domains.FailureDomainError as exc:
        check("query collapse refused", exc.code == "collapse_refused", exc.code)
    try:
        domains.guard_query(fill="1")
        check("query fill refused", False)
    except domains.FailureDomainError as exc:
        check("query fill refused", exc.code == "slots_refused", exc.code)
    try:
        domains.guard_query(delete="nas")
        check("query nas delete refused", False)
    except domains.FailureDomainError as exc:
        check("query nas delete refused", exc.code == "nas_destructive_refused", exc.code)
    try:
        domains.guard_query(b2="yes")
        check("query b2 refused", False)
    except domains.FailureDomainError as exc:
        check("query b2 refused", exc.code == "b2_destructive_refused", exc.code)
    try:
        domains.guard_query(production="1")
        check("query production refused", False)
    except domains.FailureDomainError as exc:
        check("query production refused", exc.code == "production_refused", exc.code)
    try:
        domains.guard_query(ready="1")
        check("query ready refused", False)
    except domains.FailureDomainError as exc:
        check("query ready refused", exc.code == "ready_refused", exc.code)
    try:
        domains.refuse_external_write({"rclone": True})
        check("rclone refused", False)
    except domains.FailureDomainError as exc:
        check("rclone refused", exc.code == "writes_refused", exc.code)
    try:
        domains.refuse_external_write({})
        check("empty write refused", False)
    except domains.FailureDomainError as exc:
        check("empty write refused", exc.code == "writes_refused", exc.code)
    try:
        domains.ledger_cap_state(Path("/tmp/wolf-system/ledger.json"))
        check("wolf-system path refused", False)
    except domains.FailureDomainError as exc:
        check("wolf-system path refused", exc.code == "not_beta", exc.code)
    try:
        domains.ledger_cap_state(td / "alchemist" / "ledger.json")
        check("alchemist path refused", False)
    except domains.FailureDomainError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    try:
        domains.ledger_cap_state(Path("b2://wolf-bucket/ledger.json"))
        check("b2 path refused", False)
    except domains.FailureDomainError as exc:
        check("b2 path refused", exc.code == "b2_destructive_refused", exc.code)
    try:
        domains.ledger_cap_state(Path("/tmp/production/money.sqlite"))
        check("production path refused", False)
    except domains.FailureDomainError as exc:
        check("production path refused", exc.code == "production_refused", exc.code)
    check("refuse left no files", list(td.iterdir()) == before)


def test_ledger_ceiling(td: Path) -> None:
    before = LEDGER.read_bytes()
    higher = json.loads(before.decode())
    higher["CAP-DR-02"] = ["PROVEN", "fixture only"]
    path = td / "higher.json"
    path.write_text(json.dumps(higher), encoding="utf-8")
    flags = domains.honesty_flags(path)
    check("already higher ceiling", flags["maturity"] == "PROVEN" and flags["maturity_ceiling"] == "PROVEN")
    check("already higher is not a write", flags["model_c_write"] is False and flags["invented_proven"] is False)
    check("higher still not proved independence", flags["independence_proved"] is False and flags["live_restore"] is False and flags["ready"] is False)
    ready = json.loads(before.decode())
    ready["CAP-DR-02"] = ["READY", "fixture only"]
    ready_path = td / "ready.json"
    ready_path.write_text(json.dumps(ready), encoding="utf-8")
    ready_flags = domains.honesty_flags(ready_path)
    check("ready fixture ceiling", ready_flags["maturity"] == "READY" and ready_flags["maturity_ceiling"] == "READY" and ready_flags["invented_ready"] is False)
    check("live ledger still bytes", LEDGER.read_bytes() == before)
    junk = json.loads(before.decode())
    junk["CAP-DR-02"] = ["GREEN", "no"]
    junk_path = td / "junk.json"
    junk_path.write_text(json.dumps(junk), encoding="utf-8")
    junk_flags = domains.honesty_flags(junk_path)
    check("non maturity becomes UNKNOWN", junk_flags["ledger_maturity"] == "UNKNOWN", junk_flags["ledger_maturity"])
    check("unknown ceiling stays BUILT", junk_flags["maturity_ceiling"] == "BUILT" and junk_flags["proven"] is False and junk_flags["ready"] is False)
    missing_db = td / "no-cr.sqlite"
    sqlite3.connect(missing_db).close()
    absent = domains.honesty_flags(catalog_db=missing_db)
    check("missing cr not invented", absent["cr_present"] is False and absent["cr_resolved"] is False and absent["cr_id"] == CR_ID)
    check("live ledger untouched after junk", LEDGER.read_bytes() == before)


def test_source_and_files() -> None:
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
    check("module has no subprocess", "subprocess" not in joined)
    check("module does not bind 8787", "8787" not in src)
    check("module does not json.dump", "json.dump" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/failure-domains" in serve)
    check("page route registered", "/failure-domains" in serve)
    check("run route refused in server", "/api/failure-domains/run" in serve)
    check("nas route refused in server", "/api/failure-domains/nas" in serve)
    check("b2 route refused in server", "/api/failure-domains/b2" in serve)
    check("prove route refused in server", "/api/failure-domains/prove" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)


def test_api(td: Path) -> None:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ.pop("WOLF_ALCHEMIST_DB", None)
    os.environ["BETA_AUTH_MODE"] = "development_assertion"
    ra._ENV_LOADED = True
    import serve_beta as sb

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
        def call(method: str, url_path: str, subject: str | None):
            headers = {"Accept": "application/json"}
            if subject:
                headers["X-Wolf-Subject"] = subject
            data = b"{}" if method != "GET" else None
            req = Request(f"http://127.0.0.1:{port}{url_path}", headers=headers, method=method, data=data)
            try:
                with urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                    ctype = resp.headers.get("Content-Type", "")
                    if "json" in ctype or url_path.startswith("/api/"):
                        try:
                            return resp.status, json.loads(raw.decode())
                        except json.JSONDecodeError:
                            return resp.status, raw
                    return resp.status, raw
            except HTTPError as exc:
                raw = exc.read()
                try:
                    parsed = json.loads(raw.decode())
                except json.JSONDecodeError:
                    parsed = raw
                return exc.code, parsed

        st, _anon = call("GET", "/api/failure-domains", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/failure-domains", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/failure-domains", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner ten steps", owner.get("checklist_count") == 10 and owner.get("checklist_executed") == 0)
            check("owner status", owner.get("status") == "NOT_RUN" and owner.get("live_restore") is False)
            check("owner beta split", owner.get("beta_equals_production") is False and (owner.get("separation") or {}).get("slot") == "EMPTY")
            check("owner domains empty", owner.get("domain_count") == 4 and owner.get("independence_proved") is False and owner.get("slots_filled") is False)
            check("owner log quiet", (owner.get("log") or {}).get("status") == "NOT_RUN" and (owner.get("log") or {}).get("beta_equals_production") is False)
            check("owner no production mutate", owner.get("production_mutated") is False and owner.get("nas_destructive") is False and owner.get("b2_destructive") is False)
            check("owner honesty bound", (owner.get("honesty") or {}).get("cr_id") == CR_ID and (owner.get("honesty") or {}).get("cr_state") == "OPEN")
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner skeleton", owner.get("framework_skeleton") == "BUILT")
            check("owner ceiling", (owner.get("honesty") or {}).get("maturity") == "SPECIFIED" and (owner.get("honesty") or {}).get("maturity_ceiling") == "BUILT")
        st, steps = call("GET", "/api/failure-domains/checklist", MATT)
        check("owner checklist 200", st == 200 and isinstance(steps, dict) and steps.get("checklist_count") == 10, str(st))
        st, schema = call("GET", "/api/failure-domains/schema", MATT)
        check("owner schema 200", st == 200 and isinstance(schema, dict) and (schema.get("schema") or {}).get("schema_id") == domains.SCHEMA_ID, str(st))
        st, log = call("GET", "/api/failure-domains/log", MATT)
        check("owner log 200", st == 200 and isinstance(log, dict) and (log.get("log") or {}).get("result") == "NOT_RUN", str(st))
        st, named = call("GET", "/api/failure-domains/domains", MATT)
        check(
            "owner domains 200",
            st == 200 and isinstance(named, dict) and named.get("domain_count") == 4 and named.get("beta_equals_production") is False,
            str(st),
        )
        st, missing = call("GET", "/api/failure-domains/NO-SUCH", MATT)
        check("owner missing 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(missing)[:180])
        st, one = call("GET", "/api/failure-domains/CHK-BETA-NE-PRODUCTION", MATT)
        check("owner one step 200", st == 200 and isinstance(one, dict) and (one.get("step") or {}).get("slot") == "EMPTY", str(st))
        st, beta = call("GET", "/api/failure-domains/DOMAIN-BETA", MATT)
        check("owner beta domain 200", st == 200 and isinstance(beta, dict) and (beta.get("domain") or {}).get("slot") == "EMPTY", str(st))
        st, page_anon = call("GET", "/failure-domains", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/failure-domains", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page, bytes)
            and b"CAP-DR-02" in page
            and b"Beta is not Production" in page
            and b"EMPTY" in page
            and b"NOT_RUN" in page,
            str(st),
        )
        st, _post_anon = call("POST", "/api/failure-domains", None)
        check("anon POST 403", st == 403, str(st))
        st, posted = call("POST", "/api/failure-domains", MATT)
        check("owner POST refused", st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused", str(posted)[:200])
        st, put = call("PUT", "/api/failure-domains", MATT)
        check("owner PUT refused", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:160])
        st, patch = call("PATCH", "/api/failure-domains", MATT)
        check("owner PATCH refused", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:160])
        st, run = call("POST", "/api/failure-domains/run", MATT)
        check("owner run refused", st == 405 and isinstance(run, dict) and run.get("error") == "live_restore_refused", str(run)[:200])
        st, nas = call("POST", "/api/failure-domains/nas", MATT)
        check("owner nas refused", st == 405 and isinstance(nas, dict) and nas.get("error") == "nas_destructive_refused", str(nas)[:200])
        st, b2 = call("POST", "/api/failure-domains/b2", MATT)
        check("owner b2 refused", st == 405 and isinstance(b2, dict) and b2.get("error") == "b2_destructive_refused", str(b2)[:200])
        st, prod = call("POST", "/api/failure-domains/production", MATT)
        check("owner production refused", st == 405 and isinstance(prod, dict) and prod.get("error") == "production_refused", str(prod)[:200])
        st, prove = call("POST", "/api/failure-domains/prove", MATT)
        check("owner prove refused", st == 405 and isinstance(prove, dict) and prove.get("error") == "independence_refused", str(prove)[:200])
        st, collapse = call("POST", "/api/failure-domains/collapse", MATT)
        check("owner collapse refused", st == 405 and isinstance(collapse, dict) and collapse.get("error") == "collapse_refused", str(collapse)[:200])
        st, fill = call("POST", "/api/failure-domains/fill", MATT)
        check("owner fill refused", st == 405 and isinstance(fill, dict) and fill.get("error") == "slots_refused", str(fill)[:200])
        st, qrestore = call("GET", "/api/failure-domains?restore=1", MATT)
        check("query restore refused", st == 405 and isinstance(qrestore, dict) and qrestore.get("error") == "live_restore_refused", str(qrestore)[:180])
        st, qready = call("GET", "/api/failure-domains?ready=1", MATT)
        check("query ready refused", st == 405 and isinstance(qready, dict) and qready.get("error") == "ready_refused", str(qready)[:180])
        st, qprove = call("GET", "/api/failure-domains?prove=1", MATT)
        check("query prove http refused", st == 405 and isinstance(qprove, dict) and qprove.get("error") == "independence_refused", str(qprove)[:180])
    finally:
        httpd.shutdown()


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="failure-domains-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    cr_before = _cr_row()
    resolved_before = _resolved_count()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    try:
        test_live_framework()
        test_refuses(td)
        test_ledger_ceiling(td)
        test_source_and_files()
        test_api(td)
    finally:
        shutil.rmtree(td, ignore_errors=True)
        os.environ.pop("WOLF_ESB_SQLITE", None)
        os.environ.pop("WOLF_ALCHEMIST_DB", None)
    check("ledger file still unchanged at exit", LEDGER.read_bytes() == ledger_before)
    check("score history unchanged", HISTORY.read_bytes() == history_before)
    doc = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("ledger still 77", len(doc) == 77, str(len(doc)))
    check("CAP-DR-01 stays SPECIFIED", doc["CAP-DR-01"][0] == "SPECIFIED")
    check("CAP-DR-02 stays SPECIFIED", doc["CAP-DR-02"][0] == "SPECIFIED")
    check("CR row unchanged", _cr_row() == cr_before, str(_cr_row()))
    check("CR stays OPEN", cr_before is not None and cr_before[0] == "OPEN")
    check("resolved count unchanged", _resolved_count() == resolved_before, str(_resolved_count()))
    for rel, digest in wip_before.items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        check(f"WIP untouched {Path(rel).name}", got == digest)
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
