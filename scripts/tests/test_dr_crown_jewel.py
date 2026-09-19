#!/usr/bin/env python3
"""CAP-DR-02 crown-jewel register. Contents stay closed. Slots stay empty. No restore."""
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

from core import dr_crown_jewel as jewels  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "dr_crown_jewel.py"
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
    "CHK-NAME-SYSTEMS",
    "CHK-CONTENTS-CLOSED",
    "CHK-NAME-DOMAINS",
    "CHK-BETA-NE-PRODUCTION",
    "CHK-NO-COLLAPSE",
    "CHK-NO-LIVE-RESTORE",
    "CHK-NO-NAS",
    "CHK-NO-B2",
    "CHK-NO-PRODUCTION-WRITE",
    "CHK-INDEPENDENCE-SLOT",
)
DOMAIN_IDS = ("DOMAIN-BETA", "DOMAIN-PRODUCTION", "DOMAIN-NAS", "DOMAIN-B2")
SYSTEM_IDS = ("CJ-PLAYBOOK", "CJ-REGISTRY", "CJ-WOLF-IP")


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
    return json.loads(json.dumps(jewels.not_run_log()))


def test_live_framework() -> None:
    report = jewels.build_framework()
    steps = report["checklist"]
    named = report["domains"]
    systems = report["systems"]
    check("ten steps", [row["id"] for row in steps] == list(STEP_IDS), str([row["id"] for row in steps]))
    check(
        "none executed",
        all(row["executed"] is False and row["result"] == "NOT_RUN" and row["slot"] == "EMPTY" and row["required"] is True for row in steps),
    )
    check("executed count zero", report["checklist_executed"] == 0 and report["checklist_count"] == 10)
    check("empty slots", report["empty_slot_count"] == 29 and report["slots_filled"] is False, str(report["empty_slot_count"]))
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
        and split["separation"] == "DOCUMENTED"
        and split["independence_proved"] is False
        and split["slot"] == "EMPTY",
    )
    check("three systems", [row["id"] for row in systems] == list(SYSTEM_IDS) and report["system_count"] == 3)
    check(
        "systems closed",
        all(
            row["class"] == "crown_jewel"
            and row["visibility"] == "HIDDEN"
            and row["opened"] is False
            and row["copied"] is False
            and row["contents"] is None
            and row["protected"] is False
            and row["protection_proved"] is False
            and row["slot"] == "EMPTY"
            and row["identified"] is True
            for row in systems
        ),
    )
    check(
        "each system has its own empty domains",
        all(
            [domain["id"] for domain in row["domains"]] == list(DOMAIN_IDS)
            and all(domain["slot"] == "EMPTY" and domain["independence_proved"] is False and domain["contacted"] is False for domain in row["domains"])
            for row in systems
        ),
    )
    check("naming is not protection", report["identified_count"] == 3 and report["protected_count"] is None and report["identified_is_protected"] is False)
    check("contents stay null", report["contents"] is None and report["crown_jewels_opened"] is False and report["contents_read"] is False and report["protection_proved"] is False)
    check("cr not resolved by the pack", report["cr_resolved"] is False)
    schema = report["schema"]
    check("schema id", schema["schema_id"] == jewels.SCHEMA_ID and schema["additionalProperties"] is False)
    check("schema only not-run", schema["status_enum"] == ["NOT_RUN"] and schema["slot_enum"] == ["EMPTY"] and schema["visibility_enum"] == ["HIDDEN"])
    check("schema names refused success", "PROTECTED" in schema["refused_status"] and "READY" in schema["refused_status"] and "PROVEN" in schema["refused_status"])
    log = report["log"]
    check("log not run", log["status"] == "NOT_RUN" and log["result"] == "NOT_RUN" and log["prove_id"] is None)
    check(
        "log claims nothing",
        log["live_restore"] is False
        and log["production_mutated"] is False
        and log["nas_destructive"] is False
        and log["b2_destructive"] is False
        and log["crown_jewels_opened"] is False
        and log["contents_read"] is False
        and log["protection_proved"] is False
        and log["cr_resolved"] is False
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
    check("honesty.closed", flags.get("crown_jewels_opened") is False and flags.get("protection_proved") is False and flags.get("protected_count") is None)
    check("honesty.not_independent", flags.get("independence_proved") is False and flags.get("beta_equals_production") is False and flags.get("slots_filled") is False)
    check("pack flags", report["ledger_write"] is False and report["external_writes"] is False and report["production_mutated"] is False)
    one = jewels.read_step("CHK-CONTENTS-CLOSED")
    check("read closed step", one["ok"] is True and one["step"]["executed"] is False and one["step"]["slot"] == "EMPTY" and one["crown_jewels_opened"] is False)
    playbook = jewels.read_system("CJ-PLAYBOOK")
    check("read playbook closed", playbook["ok"] is True and playbook["system"]["contents"] is None and playbook["system"]["opened"] is False and playbook["contents"] is None)
    check("read system bound", (playbook.get("honesty") or {}).get("cr_id") == CR_ID and playbook.get("cr_resolved") is False)
    beta = jewels.read_domain("DOMAIN-BETA")
    check("read beta domain", beta["ok"] is True and beta["domain"]["slot"] == "EMPTY" and beta["beta_equals_production"] is False)
    validated = jewels.validate_log(jewels.not_run_log())
    check("validate exemplar", validated["ok"] is True and validated["valid"] is True and validated["protection_proved"] is False and validated["cr_resolved"] is False)


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
        ("opened flag", {"crown_jewels_opened": True}, "playbook_refused"),
        ("contents flag", {"contents_read": True}, "playbook_refused"),
        ("protection flag", {"protection_proved": True}, "protection_refused"),
        ("resolve flag", {"cr_resolved": True}, "resolve_refused"),
        ("ready flag", {"ready_claimed": True}, "ready_refused"),
        ("proven flag", {"proven_claimed": True}, "proven_refused"),
        ("success status", {"status": "SUCCESS"}, "success_refused"),
        ("restored result", {"result": "RESTORED"}, "success_refused"),
        ("proved status", {"status": "PROVED"}, "independence_refused"),
        ("resolved status", {"status": "RESOLVED"}, "resolve_refused"),
        ("ready status", {"status": "READY"}, "ready_refused"),
        ("filled status", {"status": "FILLED"}, "slots_refused"),
    ]
    for name, patch, code in cases:
        payload = _copy_log()
        payload.update(patch)
        try:
            jewels.validate_log(payload)
            check(name, False, "accepted")
        except jewels.CrownJewelError as exc:
            check(name, exc.code == code, exc.code)
    opened = _copy_log()
    opened["systems"][0]["opened"] = True
    opened["systems"][0]["contents"] = "playbook text"
    try:
        jewels.validate_log(opened)
        check("opened system refused", False)
    except jewels.CrownJewelError as exc:
        check("opened system refused", exc.code == "playbook_refused", exc.code)
    protected = _copy_log()
    protected["systems"][1]["protected"] = True
    try:
        jewels.validate_log(protected)
        check("protected system refused", False)
    except jewels.CrownJewelError as exc:
        check("protected system refused", exc.code == "protection_refused", exc.code)
    contacted = _copy_log()
    contacted["systems"][0]["domains"][2]["contacted"] = True
    try:
        jewels.validate_log(contacted)
        check("nested nas contact refused", False)
    except jewels.CrownJewelError as exc:
        check("nested nas contact refused", exc.code == "nas_destructive_refused", exc.code)
    mutated = _copy_log()
    mutated["systems"][2]["domains"][1]["mutated"] = True
    try:
        jewels.validate_log(mutated)
        check("nested production mutate refused", False)
    except jewels.CrownJewelError as exc:
        check("nested production mutate refused", exc.code == "production_refused", exc.code)
    filled = _copy_log()
    filled["systems"][0]["domains"][0]["slot"] = "FILLED"
    try:
        jewels.validate_log(filled)
        check("nested slot refused", False)
    except jewels.CrownJewelError as exc:
        check("nested slot refused", exc.code == "slots_refused", exc.code)
    short = _copy_log()
    short["systems"] = short["systems"][:2]
    try:
        jewels.validate_log(short)
        check("short register refused", False)
    except jewels.CrownJewelError as exc:
        check("short register refused", exc.code == "bad_log", exc.code)
    direct = [
        ("refuse restore", jewels.refuse_live_restore, "live_restore_refused"),
        ("refuse nas", jewels.refuse_nas, "nas_destructive_refused"),
        ("refuse b2", jewels.refuse_b2, "b2_destructive_refused"),
        ("refuse production", jewels.refuse_production, "production_refused"),
        ("refuse prove", jewels.refuse_independence, "independence_refused"),
        ("refuse collapse", jewels.refuse_collapse, "collapse_refused"),
        ("refuse fill", jewels.refuse_fill, "slots_refused"),
        ("refuse playbook", jewels.refuse_playbook, "playbook_refused"),
        ("refuse protect", jewels.refuse_protection, "protection_refused"),
        ("refuse resolve", jewels.refuse_resolve, "resolve_refused"),
        ("refuse ready", jewels.refuse_ready, "ready_refused"),
        ("refuse proven", jewels.refuse_proven, "proven_refused"),
        ("refuse write", jewels.refuse_external_write, "writes_refused"),
    ]
    for name, fn, code in direct:
        try:
            fn({})
            check(name, False, "accepted")
        except jewels.CrownJewelError as exc:
            check(name, exc.code == code, exc.code)
    try:
        jewels.guard_query(open="1")
        check("query open refused", False)
    except jewels.CrownJewelError as exc:
        check("query open refused", exc.code == "playbook_refused", exc.code)
    try:
        jewels.guard_query(protect="1")
        check("query protect refused", False)
    except jewels.CrownJewelError as exc:
        check("query protect refused", exc.code == "protection_refused", exc.code)
    try:
        jewels.guard_query(resolve="1")
        check("query resolve refused", False)
    except jewels.CrownJewelError as exc:
        check("query resolve refused", exc.code == "resolve_refused", exc.code)
    try:
        jewels.read_system("PLAYBOOK")
        check("playbook token refused", False)
    except jewels.CrownJewelError as exc:
        check("playbook token refused", exc.code == "playbook_refused", exc.code)
    try:
        jewels.read_system("NO-SUCH")
        check("unknown system not invented", False)
    except jewels.CrownJewelError as exc:
        check("unknown system not invented", exc.code == "not_found", exc.code)
    check("temp dir untouched", list(td.iterdir()) == before)


def test_ledger_ceiling(td: Path) -> None:
    before = LEDGER.read_bytes()
    higher = json.loads(before.decode())
    higher["CAP-DR-02"] = ["PROVEN", "fixture only"]
    higher_path = td / "proven.json"
    higher_path.write_text(json.dumps(higher), encoding="utf-8")
    flags = jewels.honesty_flags(higher_path)
    check("proven fixture ceiling", flags["maturity"] == "PROVEN" and flags["maturity_ceiling"] == "PROVEN" and flags["invented_proven"] is False)
    check("live ledger still bytes", LEDGER.read_bytes() == before)
    ready = json.loads(before.decode())
    ready["CAP-DR-02"] = ["READY", "fixture only"]
    ready_path = td / "ready.json"
    ready_path.write_text(json.dumps(ready), encoding="utf-8")
    ready_flags = jewels.honesty_flags(ready_path)
    check("ready fixture ceiling", ready_flags["maturity"] == "READY" and ready_flags["maturity_ceiling"] == "READY" and ready_flags["invented_ready"] is False)
    junk = json.loads(before.decode())
    junk["CAP-DR-02"] = ["GREEN", "no"]
    junk_path = td / "junk.json"
    junk_path.write_text(json.dumps(junk), encoding="utf-8")
    junk_flags = jewels.honesty_flags(junk_path)
    check("non maturity becomes UNKNOWN", junk_flags["ledger_maturity"] == "UNKNOWN", junk_flags["ledger_maturity"])
    check("unknown ceiling stays BUILT", junk_flags["maturity_ceiling"] == "BUILT" and junk_flags["proven"] is False and junk_flags["ready"] is False)
    missing_db = td / "no-cr.sqlite"
    sqlite3.connect(missing_db).close()
    absent = jewels.honesty_flags(catalog_db=missing_db)
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
    check("route registered", "/api/crown-jewels" in serve)
    check("page route registered", "/crown-jewels" in serve)
    check("run route refused in server", "/api/crown-jewels/run" in serve)
    check("nas route refused in server", "/api/crown-jewels/nas" in serve)
    check("b2 route refused in server", "/api/crown-jewels/b2" in serve)
    check("open route refused in server", "/api/crown-jewels/open" in serve)
    check("resolve route refused in server", "/api/crown-jewels/resolve" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "crown-jewels.html").read_text(encoding="utf-8")
    check("page names the cap", "CAP-DR-02" in page and "Contents stay closed" in page and "NOT_RUN" in page)


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

        st, _anon = call("GET", "/api/crown-jewels", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/crown-jewels", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/crown-jewels", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner ten steps", owner.get("checklist_count") == 10 and owner.get("checklist_executed") == 0)
            check("owner status", owner.get("status") == "NOT_RUN" and owner.get("live_restore") is False)
            check("owner closed", owner.get("crown_jewels_opened") is False and owner.get("contents") is None and owner.get("protected_count") is None)
            check("owner three systems", owner.get("system_count") == 3 and owner.get("identified_count") == 3 and owner.get("protection_proved") is False)
            check("owner beta split", owner.get("beta_equals_production") is False and (owner.get("separation") or {}).get("slot") == "EMPTY")
            check("owner domains empty", owner.get("domain_count") == 4 and owner.get("independence_proved") is False and owner.get("slots_filled") is False)
            check("owner cr open", owner.get("cr_resolved") is False and (owner.get("honesty") or {}).get("cr_state") == "OPEN")
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner skeleton", owner.get("framework_skeleton") == "BUILT")
            check("owner ceiling", (owner.get("honesty") or {}).get("maturity") == "SPECIFIED" and (owner.get("honesty") or {}).get("maturity_ceiling") == "BUILT")
        st, steps = call("GET", "/api/crown-jewels/checklist", MATT)
        check("owner checklist 200", st == 200 and isinstance(steps, dict) and steps.get("checklist_count") == 10, str(st))
        st, schema = call("GET", "/api/crown-jewels/schema", MATT)
        check("owner schema 200", st == 200 and isinstance(schema, dict) and (schema.get("schema") or {}).get("schema_id") == jewels.SCHEMA_ID, str(st))
        st, named = call("GET", "/api/crown-jewels/register", MATT)
        check(
            "owner register 200",
            st == 200 and isinstance(named, dict) and named.get("system_count") == 3 and named.get("protected_count") is None and named.get("crown_jewels_opened") is False,
            str(st),
        )
        st, missing = call("GET", "/api/crown-jewels/NO-SUCH", MATT)
        check("owner missing 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(missing)[:180])
        st, one = call("GET", "/api/crown-jewels/CJ-PLAYBOOK", MATT)
        check("owner playbook 200", st == 200 and isinstance(one, dict) and (one.get("system") or {}).get("contents") is None and one.get("crown_jewels_opened") is False, str(st))
        st, page_anon = call("GET", "/crown-jewels", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/crown-jewels", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page, bytes)
            and b"CAP-DR-02" in page
            and b"Contents stay closed" in page
            and b"EMPTY" in page
            and b"NOT_RUN" in page,
            str(st),
        )
        st, posted = call("POST", "/api/crown-jewels", MATT)
        check("owner POST refused", st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused", str(posted)[:200])
        st, put = call("PUT", "/api/crown-jewels", MATT)
        check("owner PUT refused", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:160])
        st, patch = call("PATCH", "/api/crown-jewels", MATT)
        check("owner PATCH refused", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:160])
        st, run = call("POST", "/api/crown-jewels/run", MATT)
        check("owner run refused", st == 405 and isinstance(run, dict) and run.get("error") == "live_restore_refused", str(run)[:200])
        st, nas = call("POST", "/api/crown-jewels/nas", MATT)
        check("owner nas refused", st == 405 and isinstance(nas, dict) and nas.get("error") == "nas_destructive_refused", str(nas)[:200])
        st, b2 = call("POST", "/api/crown-jewels/b2", MATT)
        check("owner b2 refused", st == 405 and isinstance(b2, dict) and b2.get("error") == "b2_destructive_refused", str(b2)[:200])
        st, prod = call("POST", "/api/crown-jewels/production", MATT)
        check("owner production refused", st == 405 and isinstance(prod, dict) and prod.get("error") == "production_refused", str(prod)[:200])
        st, opened = call("POST", "/api/crown-jewels/open", MATT)
        check("owner open refused", st == 405 and isinstance(opened, dict) and opened.get("error") == "playbook_refused", str(opened)[:200])
        st, protect = call("POST", "/api/crown-jewels/protect", MATT)
        check("owner protect refused", st == 405 and isinstance(protect, dict) and protect.get("error") == "protection_refused", str(protect)[:200])
        st, resolve = call("POST", "/api/crown-jewels/resolve", MATT)
        check("owner resolve refused", st == 405 and isinstance(resolve, dict) and resolve.get("error") == "resolve_refused" and resolve.get("cr_resolved") is False, str(resolve)[:200])
        st, prove = call("POST", "/api/crown-jewels/prove", MATT)
        check("owner prove refused", st == 405 and isinstance(prove, dict) and prove.get("error") == "independence_refused", str(prove)[:200])
        st, ready = call("POST", "/api/crown-jewels/ready", MATT)
        check("owner ready refused", st == 405 and isinstance(ready, dict) and ready.get("error") == "ready_refused", str(ready)[:200])
        st, qopen = call("GET", "/api/crown-jewels?open=1", MATT)
        check("query open http refused", st == 405 and isinstance(qopen, dict) and qopen.get("error") == "playbook_refused", str(qopen)[:180])
        st, qrestore = call("GET", "/api/crown-jewels?restore=1", MATT)
        check("query restore refused", st == 405 and isinstance(qrestore, dict) and qrestore.get("error") == "live_restore_refused", str(qrestore)[:180])
        st, _post_anon = call("POST", "/api/crown-jewels", None)
        check("anon POST 403", st == 403, str(st))
    finally:
        httpd.shutdown()
        del td


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="crown-jewels-"))
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
