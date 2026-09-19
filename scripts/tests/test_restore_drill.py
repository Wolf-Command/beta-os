#!/usr/bin/env python3
"""CAP-DR-01 restore-drill framework. Read-only. No live restore. No READY."""
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

from core import restore_drill as drill  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "restore_drill.py"
CR_ID = "CR-667f31959d1bbe82"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
STEP_IDS = (
    "CHK-TARGET-TEMP",
    "CHK-SOURCE-IDENTITY",
    "CHK-NO-NAS-DELETE",
    "CHK-NO-B2-DELETE",
    "CHK-NO-PRODUCTION",
    "CHK-COPY-TEMP",
    "CHK-SHA256",
    "CHK-SECRETS",
    "CHK-LOG-NOT-RUN",
)


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
    return json.loads(json.dumps(drill.not_run_log()))


def test_live_framework() -> None:
    report = drill.build_framework()
    steps = report["checklist"]
    check("nine steps", [row["id"] for row in steps] == list(STEP_IDS), str([row["id"] for row in steps]))
    check("none executed", all(row["executed"] is False and row["result"] == "NOT_RUN" and row["required"] is True for row in steps))
    check("executed count zero", report["checklist_executed"] == 0 and report["checklist_count"] == 9)
    check("status not run", report["status"] == "NOT_RUN" and report["live_restore"] is False)
    check("stores untouched", all(row["contacted"] is False and row["destructive"] is False for row in report["stores"]))
    check("store ids", {row["id"] for row in report["stores"]} == {"NAS", "B2", "PRODUCTION"})
    tiers = report["tiers"]
    check("three empty tiers", len(tiers) == 3 and all(row["rto"] is None and row["rpo"] is None and row["slot"] == "EMPTY" for row in tiers))
    hist = report["historical"]
    check("historical is not this drill", hist["is_this_drill"] is False and hist["counts_as_live_success"] is False and hist["counts_as_ready"] is False)
    check("historical id retained", hist["id"] == "B2-RESTORE-DRILL-2026-08-29")
    schema = report["schema"]
    check("schema id", schema["schema_id"] == drill.SCHEMA_ID and schema["additionalProperties"] is False)
    check("schema only not-run", schema["status_enum"] == ["NOT_RUN"])
    check("schema names refused success", "SUCCESS" in schema["refused_status"] and "READY" in schema["refused_status"])
    log = report["log"]
    check("log not run", log["status"] == "NOT_RUN" and log["result"] == "NOT_RUN" and log["drill_id"] is None)
    check("log claims nothing", log["live_restore"] is False and log["production_mutated"] is False and log["nas_destructive"] is False and log["b2_destructive"] is False)
    check("log does not claim ready", log["ready_claimed"] is False and log["proven_claimed"] is False and log["historical_counts_as_this_drill"] is False)
    check("log valid", report["log_valid"] is True)
    dumped_log = json.dumps(log)
    check("log text has no success word", "SUCCESS" not in dumped_log and "RESTORED" not in dumped_log)
    flags = report["honesty"]
    check("honesty.cr_bound", flags.get("cr_id") == CR_ID and flags.get("cr_bound") is True)
    check("honesty.cr_present", flags.get("cr_present") is True)
    check("honesty.cr_open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("honesty.cr_not_resolved", flags.get("cr_resolved") is False)
    check("honesty.cr_cap", flags.get("cr_capability") == "CAP-DR-01")
    check("honesty.cr_blocker", flags.get("cr_blocker") == "NEEDS_ENGINEERING", str(flags.get("cr_blocker")))
    check("honesty.maturity_is_ledger", flags.get("maturity") == flags.get("ledger_maturity") == "SPECIFIED")
    check("honesty.ceiling_built", flags.get("maturity_ceiling") == "BUILT")
    check("honesty.skeleton", flags.get("framework_skeleton") == "BUILT")
    check("honesty.not_proven", flags.get("proven") is False and flags.get("ready") is False)
    check("honesty.not_invented", flags.get("invented_proven") is False and flags.get("invented_ready") is False)
    check("honesty.no_raise", flags.get("model_c_maturity_raised") is False and flags.get("model_c_write") is False)
    check("honesty.no_restore", flags.get("live_restore") is False and flags.get("nas_destructive") is False and flags.get("b2_destructive") is False)
    check("pack flags", report["ledger_write"] is False and report["external_writes"] is False and report["production_mutated"] is False)
    one = drill.read_step("CHK-SHA256")
    check("read sha step", one["ok"] is True and one["step"]["executed"] is False and one["step"]["result"] == "NOT_RUN")
    check("read step bound", (one.get("honesty") or {}).get("cr_id") == CR_ID)
    validated = drill.validate_log(drill.not_run_log())
    check("validate exemplar", validated["ok"] is True and validated["valid"] is True and validated["live_restore"] is False)


def test_refuses(td: Path) -> None:
    before = list(td.iterdir())
    cases = [
        ("live restore flag", {"live_restore": True}, "live_restore_refused"),
        ("production flag", {"production_mutated": True}, "production_refused"),
        ("nas flag", {"nas_destructive": True}, "nas_destructive_refused"),
        ("b2 flag", {"b2_destructive": True}, "b2_destructive_refused"),
        ("ready flag", {"ready_claimed": True}, "ready_refused"),
        ("proven flag", {"proven_claimed": True}, "proven_refused"),
        ("success status", {"status": "SUCCESS"}, "success_refused"),
        ("restored result", {"result": "RESTORED"}, "success_refused"),
        ("ready status", {"status": "READY"}, "ready_refused"),
        ("secrets flag", {"secrets_written": True}, "writes_refused"),
        ("source deleted", {"source_deleted": True}, "writes_refused"),
        ("historical as proof", {"historical_counts_as_this_drill": True}, "historical_not_proof"),
    ]
    for name, patch, code in cases:
        payload = _copy_log()
        payload.update(patch)
        try:
            drill.validate_log(payload)
            check(name, False, "accepted")
        except drill.RestoreDrillError as exc:
            check(name, exc.code == code, exc.code)
    executed = _copy_log()
    executed["checklist"][5]["executed"] = True
    executed["checklist"][5]["result"] = "SUCCESS"
    try:
        drill.validate_log(executed)
        check("executed step refused", False)
    except drill.RestoreDrillError as exc:
        check("executed step refused", exc.code == "live_restore_refused", exc.code)
    short = _copy_log()
    short["checklist"] = short["checklist"][:8]
    try:
        drill.validate_log(short)
        check("short checklist refused", False)
    except drill.RestoreDrillError as exc:
        check("short checklist refused", exc.code == "bad_log", exc.code)
    extra = _copy_log()
    extra["bytes_restored"] = 1
    try:
        drill.validate_log(extra)
        check("extra field refused", False)
    except drill.RestoreDrillError as exc:
        check("extra field refused", exc.code == "bad_log", exc.code)
    stamped = _copy_log()
    stamped["drill_id"] = "DRILL-LIVE"
    stamped["recorded_at"] = "2026-09-19T00:00:00Z"
    try:
        drill.validate_log(stamped)
        check("stamped log refused", False)
    except drill.RestoreDrillError as exc:
        check("stamped log refused", exc.code == "bad_log", exc.code)
    try:
        drill.validate_log(["not", "a", "log"])  # type: ignore[arg-type]
        check("non object refused", False)
    except drill.RestoreDrillError as exc:
        check("non object refused", exc.code == "bad_log", exc.code)
    try:
        drill.read_step("CHK-NO-SUCH")
        check("missing step refused", False)
    except drill.RestoreDrillError as exc:
        check("missing step refused", exc.code == "not_found", exc.code)
    try:
        drill.read_step("run")
        check("run id refused", False)
    except drill.RestoreDrillError as exc:
        check("run id refused", exc.code == "live_restore_refused", exc.code)
    try:
        drill.read_step("nas")
        check("nas id refused", False)
    except drill.RestoreDrillError as exc:
        check("nas id refused", exc.code == "nas_destructive_refused", exc.code)
    try:
        drill.guard_query(restore="1")
        check("query restore refused", False)
    except drill.RestoreDrillError as exc:
        check("query restore refused", exc.code == "live_restore_refused", exc.code)
    try:
        drill.guard_query(delete="nas")
        check("query nas delete refused", False)
    except drill.RestoreDrillError as exc:
        check("query nas delete refused", exc.code == "nas_destructive_refused", exc.code)
    try:
        drill.guard_query(b2="yes")
        check("query b2 refused", False)
    except drill.RestoreDrillError as exc:
        check("query b2 refused", exc.code == "b2_destructive_refused", exc.code)
    try:
        drill.guard_query(production="1")
        check("query production refused", False)
    except drill.RestoreDrillError as exc:
        check("query production refused", exc.code == "production_refused", exc.code)
    try:
        drill.guard_query(ready="1")
        check("query ready refused", False)
    except drill.RestoreDrillError as exc:
        check("query ready refused", exc.code == "ready_refused", exc.code)
    try:
        drill.refuse_external_write({"rclone": True})
        check("rclone refused", False)
    except drill.RestoreDrillError as exc:
        check("rclone refused", exc.code == "writes_refused", exc.code)
    try:
        drill.refuse_external_write({})
        check("empty write refused", False)
    except drill.RestoreDrillError as exc:
        check("empty write refused", exc.code == "writes_refused", exc.code)
    try:
        drill.ledger_cap_state(Path("/tmp/wolf-system/ledger.json"))
        check("wolf-system path refused", False)
    except drill.RestoreDrillError as exc:
        check("wolf-system path refused", exc.code == "not_beta", exc.code)
    try:
        drill.ledger_cap_state(td / "alchemist" / "ledger.json")
        check("alchemist path refused", False)
    except drill.RestoreDrillError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    try:
        drill.ledger_cap_state(Path("b2://wolf-bucket/ledger.json"))
        check("b2 path refused", False)
    except drill.RestoreDrillError as exc:
        check("b2 path refused", exc.code == "b2_destructive_refused", exc.code)
    try:
        drill.ledger_cap_state(Path("/tmp/production/money.sqlite"))
        check("production path refused", False)
    except drill.RestoreDrillError as exc:
        check("production path refused", exc.code == "production_refused", exc.code)
    check("refuse left no files", list(td.iterdir()) == before)


def test_ledger_ceiling(td: Path) -> None:
    before = LEDGER.read_bytes()
    higher = json.loads(before.decode())
    higher["CAP-DR-01"] = ["PROVEN", "fixture only"]
    path = td / "higher.json"
    path.write_text(json.dumps(higher), encoding="utf-8")
    flags = drill.honesty_flags(path)
    check("already higher ceiling", flags["maturity"] == "PROVEN" and flags["maturity_ceiling"] == "PROVEN")
    check("already higher is not a write", flags["model_c_write"] is False and flags["invented_proven"] is False)
    check("higher still not a live restore", flags["live_restore"] is False and flags["ready"] is False)
    ready = json.loads(before.decode())
    ready["CAP-DR-01"] = ["READY", "fixture only"]
    ready_path = td / "ready.json"
    ready_path.write_text(json.dumps(ready), encoding="utf-8")
    ready_flags = drill.honesty_flags(ready_path)
    check("ready fixture ceiling", ready_flags["maturity"] == "READY" and ready_flags["maturity_ceiling"] == "READY" and ready_flags["invented_ready"] is False)
    check("live ledger still bytes", LEDGER.read_bytes() == before)
    junk = json.loads(before.decode())
    junk["CAP-DR-01"] = ["GREEN", "no"]
    junk_path = td / "junk.json"
    junk_path.write_text(json.dumps(junk), encoding="utf-8")
    junk_flags = drill.honesty_flags(junk_path)
    check("non maturity becomes UNKNOWN", junk_flags["ledger_maturity"] == "UNKNOWN", junk_flags["ledger_maturity"])
    check("unknown ceiling stays BUILT", junk_flags["maturity_ceiling"] == "BUILT" and junk_flags["proven"] is False and junk_flags["ready"] is False)
    missing_db = td / "no-cr.sqlite"
    sqlite3.connect(missing_db).close()
    absent = drill.honesty_flags(catalog_db=missing_db)
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
    check("route registered", "/api/restore-drill" in serve)
    check("page route registered", "/restore-drill" in serve)
    check("run route refused in server", "/api/restore-drill/run" in serve)
    check("nas route refused in server", "/api/restore-drill/nas" in serve)
    check("b2 route refused in server", "/api/restore-drill/b2" in serve)
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

        st, _anon = call("GET", "/api/restore-drill", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/restore-drill", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/restore-drill", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner nine steps", owner.get("checklist_count") == 9 and owner.get("checklist_executed") == 0)
            check("owner status", owner.get("status") == "NOT_RUN" and owner.get("live_restore") is False)
            check("owner log quiet", (owner.get("log") or {}).get("status") == "NOT_RUN" and (owner.get("log") or {}).get("live_restore") is False)
            check("owner no production mutate", owner.get("production_mutated") is False and owner.get("nas_destructive") is False and owner.get("b2_destructive") is False)
            check("owner honesty bound", (owner.get("honesty") or {}).get("cr_id") == CR_ID)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner skeleton", owner.get("framework_skeleton") == "BUILT")
            check("owner historical not success", (owner.get("historical") or {}).get("counts_as_live_success") is False)
        st, steps = call("GET", "/api/restore-drill/checklist", MATT)
        check("owner checklist 200", st == 200 and isinstance(steps, dict) and steps.get("checklist_count") == 9, str(st))
        st, schema = call("GET", "/api/restore-drill/schema", MATT)
        check("owner schema 200", st == 200 and isinstance(schema, dict) and (schema.get("schema") or {}).get("schema_id") == drill.SCHEMA_ID, str(st))
        st, log = call("GET", "/api/restore-drill/log", MATT)
        check("owner log 200", st == 200 and isinstance(log, dict) and (log.get("log") or {}).get("result") == "NOT_RUN", str(st))
        st, missing = call("GET", "/api/restore-drill/NO-SUCH", MATT)
        check("owner missing 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(missing)[:180])
        st, one = call("GET", "/api/restore-drill/CHK-NO-PRODUCTION", MATT)
        check("owner one 200", st == 200 and isinstance(one, dict) and (one.get("step") or {}).get("executed") is False, str(st))
        st, page_anon = call("GET", "/restore-drill", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/restore-drill", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page, bytes)
            and b"CAP-DR-01" in page
            and b"Live restore is refused" in page
            and b"NOT_RUN" in page,
            str(st),
        )
        st, _post_anon = call("POST", "/api/restore-drill", None)
        check("anon POST 403", st == 403, str(st))
        st, posted = call("POST", "/api/restore-drill", MATT)
        check("owner POST refused", st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused", str(posted)[:200])
        st, put = call("PUT", "/api/restore-drill", MATT)
        check("owner PUT refused", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:160])
        st, patch = call("PATCH", "/api/restore-drill", MATT)
        check("owner PATCH refused", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:160])
        st, run = call("POST", "/api/restore-drill/run", MATT)
        check("owner run refused", st == 405 and isinstance(run, dict) and run.get("error") == "live_restore_refused", str(run)[:200])
        st, nas = call("POST", "/api/restore-drill/nas", MATT)
        check("owner nas refused", st == 405 and isinstance(nas, dict) and nas.get("error") == "nas_destructive_refused", str(nas)[:200])
        st, b2 = call("POST", "/api/restore-drill/b2", MATT)
        check("owner b2 refused", st == 405 and isinstance(b2, dict) and b2.get("error") == "b2_destructive_refused", str(b2)[:200])
        st, prod = call("POST", "/api/restore-drill/production", MATT)
        check("owner production refused", st == 405 and isinstance(prod, dict) and prod.get("error") == "production_refused", str(prod)[:200])
        st, qrestore = call("GET", "/api/restore-drill?restore=1", MATT)
        check("query restore refused", st == 405 and isinstance(qrestore, dict) and qrestore.get("error") == "live_restore_refused", str(qrestore)[:180])
        st, qready = call("GET", "/api/restore-drill?ready=1", MATT)
        check("query ready refused", st == 405 and isinstance(qready, dict) and qready.get("error") == "ready_refused", str(qready)[:180])
    finally:
        httpd.shutdown()


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="restore-drill-"))
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
    check("resolved count unchanged", _resolved_count() == resolved_before, str(_resolved_count()))
    for rel, digest in wip_before.items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        check(f"WIP untouched {Path(rel).name}", got == digest)
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
