#!/usr/bin/env python3
"""CAP-CRM-04 connector prove. Klaviyo is not ActiveCampaign. No send. No PROVEN."""
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

from core import crm_connector_prove as prove  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "crm_connector_prove.py"
CR_ID = "CR-c8719063fb940ed4"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
STEP_IDS = (
    "CHK-NAME-KLAVIYO",
    "CHK-NAME-ACTIVECAMPAIGN",
    "CHK-NOT-CONFLATED",
    "CHK-BRAND-SCOPES",
    "CHK-DOCUMENT-GAPS",
    "CHK-NO-SEND",
    "CHK-NO-KLAVIYO-CALL",
    "CHK-NO-CRM-WRITE",
    "CHK-NO-PRODUCTION",
    "CHK-NO-RESOLVE",
)
CONNECTOR_IDS = ("CONN-KLAVIYO", "CONN-ACTIVECAMPAIGN")
BRAND_IDS = (
    "BRAND-HABITAT",
    "BRAND-UMABLU",
    "BRAND-ATRIUM",
    "BRAND-SELO",
    "BRAND-TROPIK",
)
GAP_IDS = (
    "GAP-KLAVIYO-NOT-CALLED",
    "GAP-AC-READER-ABSENT",
    "GAP-NON-HABITAT-ABSENT",
    "GAP-SEND-NOT-A-COUNT",
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
    return json.loads(json.dumps(prove.not_run_log()))


def test_live_framework() -> None:
    report = prove.build_framework()
    steps = report["checklist"]
    named = report["connectors"]
    brands = report["brands"]
    gaps = report["gaps"]
    check("ten steps", [row["id"] for row in steps] == list(STEP_IDS), str([row["id"] for row in steps]))
    check(
        "none executed",
        all(row["executed"] is False and row["result"] == "NOT_RUN" and row["slot"] == "EMPTY" and row["required"] is True for row in steps),
    )
    check("executed count zero", report["checklist_executed"] == 0 and report["checklist_count"] == 10)
    check("empty slots", report["empty_slot_count"] == 17 and report["slots_filled"] is False)
    check("status not run", report["status"] == "NOT_RUN" and report["send"] is False)
    check("two connectors", [row["id"] for row in named] == list(CONNECTOR_IDS) and report["connector_count"] == 2)
    check("five brands", [row["id"] for row in brands] == list(BRAND_IDS) and report["brand_count"] == 5)
    check("four gaps", [row["id"] for row in gaps] == list(GAP_IDS) and report["gap_count"] == 4)
    by_id = {row["id"]: row for row in named}
    check(
        "not conflated",
        report["conflated"] is False
        and by_id["CONN-KLAVIYO"]["source_system"] == "klaviyo"
        and by_id["CONN-ACTIVECAMPAIGN"]["source_system"] == "activecampaign"
        and by_id["CONN-KLAVIYO"]["source_system"] != by_id["CONN-ACTIVECAMPAIGN"]["source_system"]
        and "CONN-ACTIVECAMPAIGN" in by_id["CONN-KLAVIYO"]["not_same_as"]
        and "CONN-KLAVIYO" in by_id["CONN-ACTIVECAMPAIGN"]["not_same_as"]
        and by_id["CONN-KLAVIYO"]["conflated"] is False
        and by_id["CONN-ACTIVECAMPAIGN"]["conflated"] is False,
    )
    check(
        "neither called",
        all(row["called"] is False and row["network"] is False and row["send"] is False and row["external_write"] is False and row["slot"] == "EMPTY" for row in named),
    )
    check(
        "counts stay null",
        all(row["sends"] is None and row["subscribers"] is None and row["profiles_inserted"] is None for row in named)
        and report["sends"] is None
        and report["subscribers"] is None
        and report["profiles_inserted"] is None,
    )
    check(
        "klaviyo file documented not called",
        by_id["CONN-KLAVIYO"]["reader_present"] is True
        and by_id["CONN-KLAVIYO"]["called"] is False
        and by_id["CONN-KLAVIYO"]["brand_scope"] == ["habitat"]
        and by_id["CONN-KLAVIYO"]["entity_scope"] == ["ENT-GGV"],
    )
    check(
        "ac reader absent",
        by_id["CONN-ACTIVECAMPAIGN"]["reader_present"] is False
        and by_id["CONN-ACTIVECAMPAIGN"]["brand_scope"] == []
        and by_id["CONN-ACTIVECAMPAIGN"]["called"] is False,
    )
    by_brand = {row["id"]: row for row in brands}
    check(
        "habitat documented",
        by_brand["BRAND-HABITAT"]["klaviyo_scope"] == "DOCUMENTED"
        and by_brand["BRAND-HABITAT"]["activecampaign_scope"] == "ABSENT"
        and by_brand["BRAND-HABITAT"]["entity_id"] == "ENT-GGV"
        and by_brand["BRAND-HABITAT"]["subscribers"] is None
        and by_brand["BRAND-HABITAT"]["slot"] == "EMPTY"
        and by_brand["BRAND-HABITAT"]["called"] is False,
    )
    check(
        "other brands absent not zero",
        all(
            by_brand[key]["klaviyo_scope"] == "ABSENT"
            and by_brand[key]["activecampaign_scope"] == "ABSENT"
            and by_brand[key]["subscribers"] is None
            and by_brand[key]["entity_id"] is None
            for key in ("BRAND-UMABLU", "BRAND-ATRIUM", "BRAND-SELO", "BRAND-TROPIK")
        ),
    )
    by_gap = {row["id"]: row for row in gaps}
    check(
        "gaps honest",
        by_gap["GAP-KLAVIYO-NOT-CALLED"]["status"] == "DOCUMENTED"
        and by_gap["GAP-KLAVIYO-NOT-CALLED"]["called"] is False
        and by_gap["GAP-AC-READER-ABSENT"]["status"] == "ABSENT"
        and by_gap["GAP-NON-HABITAT-ABSENT"]["status"] == "ABSENT"
        and by_gap["GAP-SEND-NOT-A-COUNT"]["status"] == "REFUSED"
        and all(row["sends"] is None for row in gaps),
    )
    split = report["distinction"]
    check(
        "distinction documented",
        split["klaviyo"] == "CONN-KLAVIYO"
        and split["activecampaign"] == "CONN-ACTIVECAMPAIGN"
        and split["same_connector"] is False
        and split["conflated"] is False
        and split["distinction"] == "DOCUMENTED"
        and split["slot"] == "EMPTY",
    )
    schema = report["schema"]
    check("schema id", schema["schema_id"] == prove.SCHEMA_ID and schema["additionalProperties"] is False)
    check("schema only not-run", schema["status_enum"] == ["NOT_RUN"] and schema["slot_enum"] == ["EMPTY"])
    check("schema names refused success", "SUCCESS" in schema["refused_status"] and "READY" in schema["refused_status"] and "PROVEN" in schema["refused_status"])
    log = report["log"]
    check("log not run", log["status"] == "NOT_RUN" and log["result"] == "NOT_RUN" and log["prove_id"] is None)
    check(
        "log claims nothing",
        log["klaviyo_called"] is False
        and log["ac_called"] is False
        and log["conflated"] is False
        and log["send"] is False
        and log["external_crm_write"] is False
        and log["cr_resolved"] is False
        and log["sends"] is None
        and log["subscribers"] is None,
    )
    check("log does not claim ready", log["ready_claimed"] is False and log["proven_claimed"] is False)
    check("log valid", report["log_valid"] is True)
    dumped_log = json.dumps(log)
    check("log text has no success word", '"SUCCESS"' not in dumped_log and '"SENT"' not in dumped_log)
    flags = report["honesty"]
    check("honesty.cr_bound", flags.get("cr_id") == CR_ID and flags.get("cr_bound") is True)
    check("honesty.cr_present", flags.get("cr_present") is True)
    check("honesty.cr_open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("honesty.cr_not_resolved", flags.get("cr_resolved") is False)
    check("honesty.cr_cap", flags.get("cr_capability") == "CAP-CRM-04")
    check("honesty.cr_blocker", flags.get("cr_blocker") == "NEEDS_ENGINEERING", str(flags.get("cr_blocker")))
    check("honesty.cr_next", flags.get("cr_next_action") == "Honest connector prove", str(flags.get("cr_next_action")))
    check("honesty.maturity_is_ledger", flags.get("maturity") == flags.get("ledger_maturity") == "BUILT")
    check("honesty.ceiling_built", flags.get("maturity_ceiling") == "BUILT")
    check("honesty.skeleton", flags.get("framework_skeleton") == "BUILT")
    check("honesty.not_proven", flags.get("proven") is False and flags.get("ready") is False)
    check("honesty.not_invented", flags.get("invented_proven") is False and flags.get("invented_ready") is False)
    check("honesty.no_raise", flags.get("model_c_maturity_raised") is False and flags.get("model_c_write") is False)
    check("honesty.no_call", flags.get("klaviyo_called") is False and flags.get("ac_called") is False and flags.get("send") is False and flags.get("conflated") is False)
    check("honesty.counts null", flags.get("sends") is None and flags.get("subscribers") is None)
    check("pack flags", report["ledger_write"] is False and report["external_writes"] is False and report["production_mutated"] is False and report["cr_resolved"] is False)
    one = prove.read_step("CHK-NO-SEND")
    check("read send step", one["ok"] is True and one["step"]["executed"] is False and one["step"]["slot"] == "EMPTY" and one["send"] is False)
    check("read step bound", (one.get("honesty") or {}).get("cr_id") == CR_ID)
    klaviyo = prove.read_connector("CONN-KLAVIYO")
    check("read klaviyo", klaviyo["ok"] is True and klaviyo["connector"]["called"] is False and klaviyo["conflated"] is False and klaviyo["connector"]["source_system"] == "klaviyo")
    ac = prove.read_connector("CONN-ACTIVECAMPAIGN")
    check("read ac", ac["connector"]["source_system"] == "activecampaign" and ac["connector"]["reader_present"] is False and ac["ac_called"] is False)
    habitat = prove.read_brand("BRAND-HABITAT")
    check("read habitat", habitat["brand"]["klaviyo_scope"] == "DOCUMENTED" and habitat["brand"]["subscribers"] is None)
    uma = prove.read_brand("umablu")
    check("read uma by brand id", uma["brand"]["id"] == "BRAND-UMABLU" and uma["brand"]["klaviyo_scope"] == "ABSENT")
    gap = prove.read_gap("GAP-AC-READER-ABSENT")
    check("read ac gap", gap["gap"]["status"] == "ABSENT" and gap["gap"]["sends"] is None)
    ref = prove.read_ref("GAP-SEND-NOT-A-COUNT")
    check("read ref gap", ref["gap"]["status"] == "REFUSED")
    validated = prove.validate_log(prove.not_run_log())
    check("validate exemplar", validated["ok"] is True and validated["valid"] is True and validated["send"] is False and validated["conflated"] is False)


def test_refuses(td: Path) -> None:
    before = list(td.iterdir())
    cases = [
        ("send flag", {"send": True}, "send_refused"),
        ("klaviyo called", {"klaviyo_called": True}, "klaviyo_write_refused"),
        ("klaviyo write", {"klaviyo_write": True}, "klaviyo_write_refused"),
        ("ac called", {"ac_called": True}, "ac_write_refused"),
        ("ac write", {"ac_write": True}, "ac_write_refused"),
        ("metricool flag", {"metricool_write": True}, "metricool_write_refused"),
        ("crm write flag", {"external_crm_write": True}, "crm_write_refused"),
        ("conflate flag", {"conflated": True}, "conflate_refused"),
        ("production flag", {"production_mutated": True}, "production_refused"),
        ("resolve flag", {"cr_resolved": True}, "resolve_refused"),
        ("slots flag", {"slots_filled": True}, "slots_refused"),
        ("ready flag", {"ready_claimed": True}, "ready_refused"),
        ("proven flag", {"proven_claimed": True}, "proven_refused"),
        ("success status", {"status": "SUCCESS"}, "success_refused"),
        ("sent result", {"result": "SENT"}, "send_refused"),
        ("proved status", {"status": "PROVED"}, "success_refused"),
        ("ready status", {"status": "READY"}, "ready_refused"),
        ("proven status", {"status": "PROVEN"}, "proven_refused"),
        ("resolved status", {"status": "RESOLVED"}, "resolve_refused"),
        ("filled status", {"status": "FILLED"}, "slots_refused"),
        ("sends zero", {"sends": 0}, "invent_metrics_refused"),
        ("subscribers zero", {"subscribers": 0}, "invent_metrics_refused"),
    ]
    for name, patch, code in cases:
        payload = _copy_log()
        payload.update(patch)
        try:
            prove.validate_log(payload)
            check(name, False, "accepted")
        except prove.ConnectorProveError as exc:
            check(name, exc.code == code, exc.code)
    called = _copy_log()
    called["connectors"][0]["called"] = True
    try:
        prove.validate_log(called)
        check("klaviyo row called refused", False)
    except prove.ConnectorProveError as exc:
        check("klaviyo row called refused", exc.code == "klaviyo_write_refused", exc.code)
    swapped = _copy_log()
    swapped["connectors"][1]["source_system"] = "klaviyo"
    try:
        prove.validate_log(swapped)
        check("ac source swapped refused", False)
    except prove.ConnectorProveError as exc:
        check("ac source swapped refused", exc.code == "conflate_refused", exc.code)
    emptied = _copy_log()
    emptied["connectors"][0]["not_same_as"] = []
    try:
        prove.validate_log(emptied)
        check("empty not_same_as refused", False)
    except prove.ConnectorProveError as exc:
        check("empty not_same_as refused", exc.code == "conflate_refused", exc.code)
    counted = _copy_log()
    counted["brands"][1]["subscribers"] = 0
    try:
        prove.validate_log(counted)
        check("brand zero refused", False)
    except prove.ConnectorProveError as exc:
        check("brand zero refused", exc.code == "invent_metrics_refused", exc.code)
    filled = _copy_log()
    filled["checklist"][3]["slot"] = "FILLED"
    try:
        prove.validate_log(filled)
        check("filled slot refused", False)
    except prove.ConnectorProveError as exc:
        check("filled slot refused", exc.code == "slots_refused", exc.code)
    short = _copy_log()
    short["checklist"] = short["checklist"][:9]
    try:
        prove.validate_log(short)
        check("short checklist refused", False)
    except prove.ConnectorProveError as exc:
        check("short checklist refused", exc.code == "bad_log", exc.code)
    extra = _copy_log()
    extra["campaign_id"] = "cmp_1"
    try:
        prove.validate_log(extra)
        check("extra field refused", False)
    except prove.ConnectorProveError as exc:
        check("extra field refused", exc.code == "bad_log", exc.code)
    stamped = _copy_log()
    stamped["prove_id"] = "PROVE-LIVE"
    stamped["recorded_at"] = "2026-09-20T00:00:00Z"
    try:
        prove.validate_log(stamped)
        check("stamped log refused", False)
    except prove.ConnectorProveError as exc:
        check("stamped log refused", exc.code == "bad_log", exc.code)
    try:
        prove.validate_log(["not", "a", "log"])  # type: ignore[arg-type]
        check("non object refused", False)
    except prove.ConnectorProveError as exc:
        check("non object refused", exc.code == "bad_log", exc.code)
    try:
        prove.read_step("CHK-NO-SUCH")
        check("missing step refused", False)
    except prove.ConnectorProveError as exc:
        check("missing step refused", exc.code == "not_found", exc.code)
    try:
        prove.read_connector("CONN-NO-SUCH")
        check("missing connector refused", False)
    except prove.ConnectorProveError as exc:
        check("missing connector refused", exc.code == "not_found", exc.code)
    try:
        prove.read_brand("BRAND-NO-SUCH")
        check("missing brand refused", False)
    except prove.ConnectorProveError as exc:
        check("missing brand refused", exc.code == "not_found", exc.code)
    try:
        prove.read_step("send")
        check("send id refused", False)
    except prove.ConnectorProveError as exc:
        check("send id refused", exc.code == "send_refused", exc.code)
    try:
        prove.read_connector("klaviyo")
        check("bare klaviyo refused", False)
    except prove.ConnectorProveError as exc:
        check("bare klaviyo refused", exc.code == "klaviyo_write_refused", exc.code)
    try:
        prove.read_connector("activecampaign")
        check("bare ac refused", False)
    except prove.ConnectorProveError as exc:
        check("bare ac refused", exc.code == "ac_write_refused", exc.code)
    try:
        prove.read_step("prove")
        check("prove id refused", False)
    except prove.ConnectorProveError as exc:
        check("prove id refused", exc.code == "proven_refused", exc.code)
    try:
        prove.read_step("resolve")
        check("resolve id refused", False)
    except prove.ConnectorProveError as exc:
        check("resolve id refused", exc.code == "resolve_refused", exc.code)
    try:
        prove.guard_query(send="1")
        check("query send refused", False)
    except prove.ConnectorProveError as exc:
        check("query send refused", exc.code == "send_refused", exc.code)
    try:
        prove.guard_query(prove="1")
        check("query prove refused", False)
    except prove.ConnectorProveError as exc:
        check("query prove refused", exc.code == "proven_refused", exc.code)
    try:
        prove.guard_query(conflate="1")
        check("query conflate refused", False)
    except prove.ConnectorProveError as exc:
        check("query conflate refused", exc.code == "conflate_refused", exc.code)
    try:
        prove.guard_query(subscribers="1")
        check("query subscribers refused", False)
    except prove.ConnectorProveError as exc:
        check("query subscribers refused", exc.code == "invent_metrics_refused", exc.code)
    try:
        prove.guard_query(write="1")
        check("query write refused", False)
    except prove.ConnectorProveError as exc:
        check("query write refused", exc.code == "crm_write_refused", exc.code)
    try:
        prove.guard_query(production="1")
        check("query production refused", False)
    except prove.ConnectorProveError as exc:
        check("query production refused", exc.code == "production_refused", exc.code)
    try:
        prove.guard_query(ready="1")
        check("query ready refused", False)
    except prove.ConnectorProveError as exc:
        check("query ready refused", exc.code == "ready_refused", exc.code)
    try:
        prove.guard_query(resolve="yes")
        check("query resolve refused", False)
    except prove.ConnectorProveError as exc:
        check("query resolve refused", exc.code == "resolve_refused", exc.code)
    try:
        prove.refuse_external_write({})
        check("empty write refused", False)
    except prove.ConnectorProveError as exc:
        check("empty write refused", exc.code == "writes_refused", exc.code)
    try:
        prove.refuse_external_write({"action": "send"})
        check("action send refused", False)
    except prove.ConnectorProveError as exc:
        check("action send refused", exc.code == "send_refused", exc.code)
    try:
        prove.ledger_cap_state(Path("/tmp/wolf-system/ledger.json"))
        check("wolf-system path refused", False)
    except prove.ConnectorProveError as exc:
        check("wolf-system path refused", exc.code == "not_beta", exc.code)
    try:
        prove.ledger_cap_state(td / "alchemist" / "ledger.json")
        check("alchemist path refused", False)
    except prove.ConnectorProveError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    try:
        prove.ledger_cap_state(Path("https://a.klaviyo.com/api/profiles"))
        check("klaviyo network path refused", False)
    except prove.ConnectorProveError as exc:
        check("klaviyo network path refused", exc.code == "klaviyo_write_refused", exc.code)
    try:
        prove.ledger_cap_state(Path("/tmp/production/money.sqlite"))
        check("production path refused", False)
    except prove.ConnectorProveError as exc:
        check("production path refused", exc.code == "production_refused", exc.code)
    check("refuse left no files", list(td.iterdir()) == before)


def test_ledger_ceiling(td: Path) -> None:
    before = LEDGER.read_bytes()
    higher = json.loads(before.decode())
    higher["CAP-CRM-04"] = ["PROVEN", "fixture only"]
    path = td / "higher.json"
    path.write_text(json.dumps(higher), encoding="utf-8")
    flags = prove.honesty_flags(path)
    check("already higher ceiling", flags["maturity"] == "PROVEN" and flags["maturity_ceiling"] == "PROVEN")
    check("already higher is not a write", flags["model_c_write"] is False and flags["invented_proven"] is False)
    check("higher still not a send", flags["send"] is False and flags["klaviyo_called"] is False and flags["ready"] is False)
    ready = json.loads(before.decode())
    ready["CAP-CRM-04"] = ["READY", "fixture only"]
    ready_path = td / "ready.json"
    ready_path.write_text(json.dumps(ready), encoding="utf-8")
    ready_flags = prove.honesty_flags(ready_path)
    check("ready fixture ceiling", ready_flags["maturity"] == "READY" and ready_flags["maturity_ceiling"] == "READY" and ready_flags["invented_ready"] is False)
    check("live ledger still bytes", LEDGER.read_bytes() == before)
    junk = json.loads(before.decode())
    junk["CAP-CRM-04"] = ["GREEN", "no"]
    junk_path = td / "junk.json"
    junk_path.write_text(json.dumps(junk), encoding="utf-8")
    junk_flags = prove.honesty_flags(junk_path)
    check("non maturity becomes UNKNOWN", junk_flags["ledger_maturity"] == "UNKNOWN", junk_flags["ledger_maturity"])
    check("unknown ceiling stays BUILT", junk_flags["maturity_ceiling"] == "BUILT" and junk_flags["proven"] is False and junk_flags["ready"] is False)
    missing_db = td / "no-cr.sqlite"
    sqlite3.connect(missing_db).close()
    absent = prove.honesty_flags(catalog_db=missing_db)
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
    check("module does not import klaviyo reader", "habitat_klaviyo_reader" not in joined)
    check("module has no urllib", "urllib" not in joined and "requests" not in joined)
    check("module has no subprocess", "subprocess" not in joined)
    check("module does not bind 8787", "8787" not in src)
    check("module does not json.dump", "json.dump" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    check("ac reader file absent", not (ROOT / "scripts" / "core" / "activecampaign_reader.py").is_file())
    check("klaviyo reader file present", (ROOT / "scripts" / "core" / "habitat_klaviyo_reader.py").is_file())
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/crm-connector-prove" in serve)
    check("page route registered", "/crm-connector-prove" in serve)
    check("send route refused in server", "/api/crm-connector-prove/send" in serve)
    check("klaviyo write route refused in server", "/api/crm-connector-prove/klaviyo-write" in serve)
    check("ac write route refused in server", "/api/crm-connector-prove/ac-write" in serve)
    check("prove route refused in server", "/api/crm-connector-prove/prove" in serve)
    check("resolve route refused in server", "/api/crm-connector-prove/resolve" in serve)
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

        st, _anon = call("GET", "/api/crm-connector-prove", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/crm-connector-prove", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/crm-connector-prove", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner ten steps", owner.get("checklist_count") == 10 and owner.get("checklist_executed") == 0)
            check("owner status", owner.get("status") == "NOT_RUN" and owner.get("send") is False)
            check("owner not conflated", owner.get("conflated") is False and (owner.get("distinction") or {}).get("slot") == "EMPTY")
            check("owner connectors empty", owner.get("connector_count") == 2 and owner.get("ac_called") is False and owner.get("klaviyo_called") is False)
            check("owner brands", owner.get("brand_count") == 5 and owner.get("subscribers") is None)
            check("owner log quiet", (owner.get("log") or {}).get("status") == "NOT_RUN" and (owner.get("log") or {}).get("send") is False)
            check("owner no crm write", owner.get("external_crm_write") is False and owner.get("production_mutated") is False and owner.get("cr_resolved") is False)
            check("owner honesty bound", (owner.get("honesty") or {}).get("cr_id") == CR_ID and (owner.get("honesty") or {}).get("cr_state") == "OPEN")
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner skeleton", owner.get("framework_skeleton") == "BUILT")
            check("owner ceiling", (owner.get("honesty") or {}).get("maturity") == "BUILT" and (owner.get("honesty") or {}).get("maturity_ceiling") == "BUILT")
            systems = {row["source_system"] for row in owner.get("connectors") or []}
            check("owner systems differ", systems == {"klaviyo", "activecampaign"})
        st, steps = call("GET", "/api/crm-connector-prove/checklist", MATT)
        check("owner checklist 200", st == 200 and isinstance(steps, dict) and steps.get("checklist_count") == 10, str(st))
        st, schema = call("GET", "/api/crm-connector-prove/schema", MATT)
        check("owner schema 200", st == 200 and isinstance(schema, dict) and (schema.get("schema") or {}).get("schema_id") == prove.SCHEMA_ID, str(st))
        st, log = call("GET", "/api/crm-connector-prove/log", MATT)
        check("owner log 200", st == 200 and isinstance(log, dict) and (log.get("log") or {}).get("sends") is None, str(st))
        st, named = call("GET", "/api/crm-connector-prove/connectors", MATT)
        check("owner connectors 200", st == 200 and isinstance(named, dict) and named.get("connector_count") == 2 and named.get("conflated") is False, str(st))
        st, brands = call("GET", "/api/crm-connector-prove/brands", MATT)
        check("owner brands 200", st == 200 and isinstance(brands, dict) and brands.get("brand_count") == 5, str(st))
        st, gaps = call("GET", "/api/crm-connector-prove/gaps", MATT)
        check("owner gaps 200", st == 200 and isinstance(gaps, dict) and gaps.get("gap_count") == 4, str(st))
        st, missing = call("GET", "/api/crm-connector-prove/NO-SUCH", MATT)
        check("missing id 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(missing)[:180])
        st, one = call("GET", "/api/crm-connector-prove/CHK-NOT-CONFLATED", MATT)
        check("one step 200", st == 200 and isinstance(one, dict) and (one.get("step") or {}).get("slot") == "EMPTY", str(one)[:180])
        st, klaviyo = call("GET", "/api/crm-connector-prove/CONN-KLAVIYO", MATT)
        check("klaviyo row 200", st == 200 and isinstance(klaviyo, dict) and (klaviyo.get("connector") or {}).get("called") is False, str(klaviyo)[:180])
        st, habitat = call("GET", "/api/crm-connector-prove/BRAND-HABITAT", MATT)
        check("habitat row 200", st == 200 and isinstance(habitat, dict) and (habitat.get("brand") or {}).get("subscribers") is None, str(habitat)[:180])
        st, page_anon = call("GET", "/crm-connector-prove", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/crm-connector-prove", MATT)
        check(
            "owner page 200",
            st == 200 and isinstance(page, (bytes, bytearray)) and b"Klaviyo is not ActiveCampaign" in page,
            str(st),
        )
        st, _post_anon = call("POST", "/api/crm-connector-prove", None)
        check("anon POST 403", st == 403, str(st))
        st, posted = call("POST", "/api/crm-connector-prove", MATT)
        check("owner POST 405", st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused", str(posted)[:180])
        st, put = call("PUT", "/api/crm-connector-prove", MATT)
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:180])
        st, patch = call("PATCH", "/api/crm-connector-prove", MATT)
        check("owner PATCH 405", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:180])
        st, send = call("POST", "/api/crm-connector-prove/send", MATT)
        check("send POST 405", st == 405 and isinstance(send, dict) and send.get("error") == "send_refused", str(send)[:180])
        st, kwrite = call("POST", "/api/crm-connector-prove/klaviyo-write", MATT)
        check("klaviyo POST 405", st == 405 and isinstance(kwrite, dict) and kwrite.get("error") == "klaviyo_write_refused", str(kwrite)[:180])
        st, awrite = call("POST", "/api/crm-connector-prove/ac-write", MATT)
        check("ac POST 405", st == 405 and isinstance(awrite, dict) and awrite.get("error") == "ac_write_refused", str(awrite)[:180])
        st, crm = call("POST", "/api/crm-connector-prove/crm-write", MATT)
        check("crm POST 405", st == 405 and isinstance(crm, dict) and crm.get("error") == "crm_write_refused", str(crm)[:180])
        st, metricool = call("POST", "/api/crm-connector-prove/metricool", MATT)
        check("metricool POST 405", st == 405 and isinstance(metricool, dict) and metricool.get("error") == "metricool_write_refused", str(metricool)[:180])
        st, conflate = call("POST", "/api/crm-connector-prove/conflate", MATT)
        check("conflate POST 405", st == 405 and isinstance(conflate, dict) and conflate.get("error") == "conflate_refused", str(conflate)[:180])
        st, prod = call("POST", "/api/crm-connector-prove/production", MATT)
        check("production POST 405", st == 405 and isinstance(prod, dict) and prod.get("error") == "production_refused", str(prod)[:180])
        st, proved = call("POST", "/api/crm-connector-prove/prove", MATT)
        check("prove POST 405", st == 405 and isinstance(proved, dict) and proved.get("error") == "proven_refused", str(proved)[:180])
        st, resolve = call("POST", "/api/crm-connector-prove/resolve", MATT)
        check("resolve POST 405", st == 405 and isinstance(resolve, dict) and resolve.get("error") == "resolve_refused", str(resolve)[:180])
        st, fill = call("POST", "/api/crm-connector-prove/fill", MATT)
        check("fill POST 405", st == 405 and isinstance(fill, dict) and fill.get("error") == "slots_refused", str(fill)[:180])
        st, qsend = call("GET", "/api/crm-connector-prove?send=1", MATT)
        check("query send http refused", st == 405 and isinstance(qsend, dict) and qsend.get("error") == "send_refused", str(qsend)[:180])
        st, qready = call("GET", "/api/crm-connector-prove?ready=1", MATT)
        check("query ready http refused", st == 405 and isinstance(qready, dict) and qready.get("error") == "ready_refused", str(qready)[:180])
        st, qprove = call("GET", "/api/crm-connector-prove?prove=1", MATT)
        check("query prove http refused", st == 405 and isinstance(qprove, dict) and qprove.get("error") == "proven_refused", str(qprove)[:180])
        st, qsub = call("GET", "/api/crm-connector-prove?subscribers=9", MATT)
        check("query subscribers http refused", st == 405 and isinstance(qsub, dict) and qsub.get("error") == "invent_metrics_refused", str(qsub)[:180])
    finally:
        httpd.shutdown()


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="crm-connector-prove-"))
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
    check("CAP-CRM-04 stays BUILT", doc["CAP-CRM-04"][0] == "BUILT")
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
