#!/usr/bin/env python3
"""Tech & Capability Registry. Read-only. No ledger write. No GREEN health."""
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

from core import tech_capability_registry as reg  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "tech_capability_registry.py"
CR_ID = "CR-44ffb6a57469ff25"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
CONNECTORS = {
    "CONN-YANOLJA",
    "CONN-ESB",
    "CONN-GOOGLE-WORKSPACE",
    "CONN-BANK",
    "CONN-METRICOOL",
    "CONN-KLAVIYO",
    "CONN-ACTIVECAMPAIGN",
}
TECH_ONLY = {"TECH-CLOUDFLARE-ACCESS", "TECH-ALCHEMIST"}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _by_id(report: dict) -> dict:
    return {row["id"]: row for row in report["entries"]}


def _no_green(payload: dict) -> bool:
    return "GREEN" not in json.dumps(payload) and "HEALTHY" not in json.dumps(payload)


def _cr_row() -> tuple | None:
    conn = sqlite3.connect(str(CATALOG_DB))
    try:
        return conn.execute(
            "SELECT state, blocker_class, capability, next_action FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
    finally:
        conn.close()


def _missing_health(**kwargs):
    missing = ROOT / "state" / "no-such-tech-registry.sqlite"
    return reg.build_registry(
        esb_path=kwargs.get("esb_path", missing),
        alchemist_path=kwargs.get("alchemist_path", missing),
        env_root=kwargs.get("env_root", ROOT / "state" / "no-such-tech-env"),
        attach_health=kwargs.get("attach_health", True),
        catalog_path=kwargs.get("catalog_path"),
        ledger_path=kwargs.get("ledger_path"),
        health_report=kwargs.get("health_report"),
        kind=kwargs.get("kind"),
    )


def test_seed_and_honesty() -> None:
    report = reg.build_registry(attach_health=False)
    caps = [row for row in report["entries"] if row["kind"] == "capability"]
    connectors = [row for row in report["entries"] if row["kind"] == "connector"]
    techs = [row for row in report["entries"] if row["kind"] == "technology"]
    check("catalog seed 77", len(caps) == 77, str(len(caps)))
    check("seed count field", report.get("catalog_seed_count") == 77)
    check("seven connectors", {row["id"] for row in connectors} == CONNECTORS, str(sorted(row["id"] for row in connectors)))
    check("technology rows cover systems", TECH_ONLY <= {row["id"] for row in techs})
    check("connector tech pairs", {row["id"].replace("CONN-", "TECH-") for row in connectors} <= {row["id"] for row in techs})
    ids = [row["id"] for row in report["entries"]]
    check("ids unique", len(ids) == len(set(ids)), str(len(ids)))
    check("every row has exit and replace", all(row.get("exit_note") and row.get("replace_note") for row in report["entries"]))
    check("replace not invented", all("does not invent a replacement" in row["replace_note"] for row in report["entries"]))
    by = _by_id(report)
    check("intg06 present", by["CAP-INTG-06"]["status"] == "SPECIFIED", by["CAP-INTG-06"]["status"])
    check("intg06 is maturity", by["CAP-INTG-06"]["status_kind"] == "maturity")
    check("yanolja ledger ABSENT", by["CAP-INTG-01"]["status"] == "ABSENT")
    check("klaviyo not probed", by["CONN-KLAVIYO"]["status"] == "NOT_CONFIGURED" and by["CONN-KLAVIYO"]["source"] == "not_probed")
    check("ac not conflated", "not Klaviyo" in by["CONN-ACTIVECAMPAIGN"]["exit_note"])
    check("ac not probed", by["CONN-ACTIVECAMPAIGN"]["status"] == "NOT_CONFIGURED")
    check("no green in seed", _no_green(report))
    check("external writes false", report["external_writes"] is False and report["ledger_write"] is False)
    check("promotes ledger false", all(row["promotes_ledger"] is False for row in report["entries"]))
    flags = report["honesty"]
    check("honesty.cr_bound", flags.get("cr_id") == CR_ID and flags.get("cr_bound") is True)
    check("honesty.cr_present", flags.get("cr_present") is True)
    check("honesty.cr_open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("honesty.cr_not_resolved", flags.get("cr_resolved") is False)
    check("honesty.cr_cap", flags.get("cr_capability") == "CAP-INTG-06")
    check("honesty.maturity_is_ledger", flags.get("maturity") == flags.get("ledger_maturity") == "SPECIFIED")
    check("honesty.ceiling_built", flags.get("maturity_ceiling") == "BUILT")
    check("honesty.not_proven", flags.get("proven") is False and flags.get("ready") is False)
    check("honesty.no_raise", flags.get("model_c_maturity_raised") is False and flags.get("model_c_write") is False)
    check("honesty.no_cr_mutate", flags.get("cr_mutated") is False)
    check("seeded from catalog", "model_c_catalog" in report["seeded_from"])


def test_health_copy_and_refuse(td: Path) -> None:
    synthetic = {
        "connectors": [
            {"cap_id": "CAP-INTG-01", "status": "NOT_CONFIGURED", "evidence": "no reader"},
            {"cap_id": "CAP-INTG-02", "status": "READ_OK", "evidence": "sales table present"},
            {"cap_id": "CAP-INTG-03", "status": "NOT_CONFIGURED", "evidence": "not probed"},
            {"cap_id": "CAP-INTG-04", "status": "NOT_CONFIGURED", "evidence": "not probed"},
            {"cap_id": "CAP-INTG-05", "status": "UNKNOWN", "evidence": "path set unread"},
            {"cap_id": "CAP-INTG-02b", "status": "GREEN", "evidence": "should not copy"},
        ],
        "sources": [
            {"source_id": "cf_access", "status": "UNKNOWN", "evidence": "aud present"},
            {"source_id": "alchemist", "status": "NOT_CONFIGURED", "evidence": "not attached"},
        ],
    }
    report = reg.build_registry(health_report=synthetic, attach_health=False)
    by = _by_id(report)
    check("yanolja health copied", by["CONN-YANOLJA"]["status"] == "NOT_CONFIGURED")
    check("esb health copied", by["CONN-ESB"]["status"] == "READ_OK" and by["TECH-ESB"]["status"] == "READ_OK")
    check("esb ledger not promoted", by["CONN-ESB"]["ledger_maturity"] == "BUILT" and by["CONN-ESB"]["promotes_ledger"] is False)
    check("metricool unknown copied", by["CONN-METRICOOL"]["status"] == "UNKNOWN")
    check("cf technology copied", by["TECH-CLOUDFLARE-ACCESS"]["status"] == "UNKNOWN")
    check("alchemist not a write", by["TECH-ALCHEMIST"]["status"] == "NOT_CONFIGURED" and "does not write" in by["TECH-ALCHEMIST"]["exit_note"])
    check("synthetic has no green token", _no_green(report))

    poisoned = {
        "connectors": [{"cap_id": "CAP-INTG-02", "status": "GREEN", "evidence": "all GREEN"}],
        "sources": [{"source_id": "alchemist", "status": "HEALTHY", "evidence": "fine"}],
    }
    bad = reg.build_registry(health_report=poisoned)
    bad_by = _by_id(bad)
    check("green status becomes ERROR", bad_by["CONN-ESB"]["status"] == "ERROR", bad_by["CONN-ESB"]["status"])
    check("healthy status becomes ERROR", bad_by["TECH-ALCHEMIST"]["status"] == "ERROR")
    check("poisoned payload has no green", _no_green(bad))

    liveish = _missing_health()
    check("missing local health not green", _no_green(liveish))
    check("missing esb not configured", _by_id(liveish)["CONN-ESB"]["status"] == "NOT_CONFIGURED")

    try:
        reg.build_registry(catalog_path=Path("/tmp/wolf-system/catalog.md"))
        check("wolf-system path refused", False)
    except reg.RegistryError as exc:
        check("wolf-system path refused", exc.code == "not_beta", exc.code)
    try:
        reg.build_registry(ledger_path=Path("/tmp/Production/ledger.json"))
        check("production path refused", False)
    except reg.RegistryError as exc:
        check("production path refused", exc.code == "not_beta", exc.code)
    try:
        reg.build_registry(catalog_path=td / "alchemist-catalog.md")
        check("alchemist path refused", False)
    except reg.RegistryError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    try:
        reg.refuse_external_write({"status": "READ_OK", "proven": True})
        check("write refused", False)
    except reg.RegistryError as exc:
        check("write refused", exc.code == "writes_refused", exc.code)
    try:
        reg.build_registry(kind="healthy")
        check("bad kind refused", False)
    except reg.RegistryError as exc:
        check("bad kind refused", exc.code == "invalid_kind")
    try:
        reg.read_entry("NO-SUCH", attach_health=False)
        check("missing entry refused", False)
    except reg.RegistryError as exc:
        check("missing entry refused", exc.code == "not_found")
    one = reg.read_entry("CAP-INTG-06", attach_health=False)
    check("read one cap", one["ok"] is True and one["entry"]["status"] == "SPECIFIED")
    check("read one bound", (one.get("honesty") or {}).get("cr_id") == CR_ID)


def test_ledger_ceiling(td: Path) -> None:
    before = LEDGER.read_bytes()
    higher = json.loads(before.decode())
    higher["CAP-INTG-06"] = ["PROVEN", "fixture only"]
    path = td / "higher.json"
    path.write_text(json.dumps(higher), encoding="utf-8")
    flags = reg.honesty_flags(path)
    check("already higher ceiling", flags["maturity"] == "PROVEN" and flags["maturity_ceiling"] == "PROVEN")
    check("already higher is ledger not invented write", flags["model_c_write"] is False)
    check("live ledger still bytes", LEDGER.read_bytes() == before)
    junk = json.loads(before.decode())
    junk["CAP-INTG-06"] = ["GREEN", "no"]
    junk_path = td / "junk.json"
    junk_path.write_text(json.dumps(junk), encoding="utf-8")
    junk_flags = reg.honesty_flags(junk_path)
    check("non maturity becomes UNKNOWN", junk_flags["ledger_maturity"] == "UNKNOWN", junk_flags["ledger_maturity"])
    check("unknown ceiling stays BUILT", junk_flags["maturity_ceiling"] == "BUILT" and junk_flags["proven"] is False)
    report = reg.build_registry(ledger_path=junk_path, attach_health=False)
    check("junk ledger payload has no green", _no_green(report))
    check("junk cap status unknown", _by_id(report)["CAP-INTG-06"]["status"] == "UNKNOWN")
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
    check("module does not import klaviyo reader", "habitat_klaviyo" not in joined)
    check("module has no urllib", "urllib" not in joined and "requests" not in joined)
    check("module does not bind 8787", "8787" not in src)
    check("module does not json.dump", "json.dump" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/tech-registry" in serve)
    check("page route registered", "/tech-registry" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)


def test_api(td: Path) -> None:
    esb = td / "api-esb.sqlite"
    import sqlite3 as _sql

    conn = _sql.connect(esb)
    conn.execute("CREATE TABLE sales (nk TEXT)")
    conn.commit()
    conn.close()
    os.environ["WOLF_ESB_SQLITE"] = str(esb)
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ.pop("WOLF_ALCHEMIST_DB", None)
    os.environ["BETA_AUTH_MODE"] = "development_assertion"
    os.environ["BETA_METRICOOL_ENABLED"] = "false"
    os.environ["BETA_METRICOOL_WRITE_ENABLED"] = "false"
    os.environ["BETA_METRICOOL_CREDS_PATH"] = ""
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
            req = Request(f"http://127.0.0.1:{port}{url_path}", headers=headers, method=method, data=b"{}" if method != "GET" else None)
            try:
                with urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                    ctype = resp.headers.get("Content-Type", "")
                    if "json" in ctype:
                        return resp.status, json.loads(raw.decode())
                    return resp.status, raw
            except HTTPError as exc:
                raw = exc.read()
                try:
                    parsed = json.loads(raw.decode())
                except json.JSONDecodeError:
                    parsed = raw
                return exc.code, parsed

        st, _anon = call("GET", "/api/tech-registry", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/tech-registry", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/tech-registry", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            caps = [row for row in owner.get("entries") or [] if row.get("kind") == "capability"]
            by = {row["id"]: row for row in owner.get("entries") or []}
            check("owner sees 77 caps", len(caps) == 77, str(len(caps)))
            check("owner intg06 specified", by["CAP-INTG-06"]["status"] == "SPECIFIED")
            check("owner yanolja connector not configured", by["CONN-YANOLJA"]["status"] == "NOT_CONFIGURED")
            check("owner esb health read ok", by["CONN-ESB"]["status"] == "READ_OK", by["CONN-ESB"]["status"])
            check("owner payload has no green", _no_green(owner))
            check("owner honesty bound", (owner.get("honesty") or {}).get("cr_id") == CR_ID)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner writes false", owner.get("external_writes") is False)
        st, missing = call("GET", "/api/tech-registry/NO-SUCH", MATT)
        check("owner missing 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(missing)[:180])
        st, one = call("GET", "/api/tech-registry/CAP-INTG-06", MATT)
        check("owner one cap 200", st == 200 and isinstance(one, dict) and (one.get("entry") or {}).get("status") == "SPECIFIED", str(st))
        st, page_anon = call("GET", "/tech-registry", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/tech-registry", MATT)
        check(
            "owner page 200",
            st == 200 and isinstance(page, bytes) and b"CAP-INTG-01" in page and b"No replace decision" in page,
            str(st),
        )
        if isinstance(page, bytes):
            check("page has no green word", b"GREEN" not in page)
        st, _post_anon = call("POST", "/api/tech-registry", None)
        check("anon POST 403", st == 403, str(st))
        st, posted = call("POST", "/api/tech-registry", MATT)
        check("owner POST refused", st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused", str(posted)[:200])
        st, put = call("PUT", "/api/tech-registry", MATT)
        check("owner PUT refused", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:160])
    finally:
        httpd.shutdown()
        os.environ.pop("WOLF_ESB_SQLITE", None)


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="tech-registry-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    cr_before = _cr_row()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    try:
        test_seed_and_honesty()
        test_health_copy_and_refuse(td)
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
    check("CAP-INTG-06 stays SPECIFIED", doc["CAP-INTG-06"][0] == "SPECIFIED")
    check("CAP-INTG-01 stays ABSENT", doc["CAP-INTG-01"][0] == "ABSENT")
    check("CR row unchanged", _cr_row() == cr_before, str(_cr_row()))
    for rel, digest in wip_before.items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        check(f"WIP untouched {Path(rel).name}", got == digest)
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
