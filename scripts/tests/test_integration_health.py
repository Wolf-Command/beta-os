#!/usr/bin/env python3
"""Integration Health read-only panel. Temp fixtures. No live network. No ledger writes."""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import shutil
import sqlite3
import subprocess
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

from core import integration_health as health  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
ENV_KEYS = (
    "BETA_AUTH_MODE",
    "BETA_CF_ACCESS_AUD",
    "BETA_CF_ACCESS_TEAM_DOMAIN",
    "BETA_METRICOOL_ENABLED",
    "BETA_METRICOOL_WRITE_ENABLED",
    "BETA_METRICOOL_CREDS_PATH",
    "WOLF_ESB_SQLITE",
    "WOLF_ALCHEMIST_DB",
)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


class _Env:
    def __enter__(self):
        self.saved = {k: os.environ.get(k) for k in ENV_KEYS}
        ra._ENV_LOADED = True
        return self

    def __exit__(self, *_exc):
        for key, val in self.saved.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
        ra._ENV_LOADED = True


def _by_id(report: dict) -> dict:
    return {row["cap_id"]: row for row in report["connectors"]}


def _no_green(report: dict) -> bool:
    blob = json.dumps(report)
    if "GREEN" in blob:
        return False
    return all(row["status"] in health.ALLOWED for row in report["connectors"])


def _sales_db(path: Path, *, with_sales: bool = True) -> None:
    conn = sqlite3.connect(path)
    if with_sales:
        conn.execute("CREATE TABLE sales (nk TEXT, biz_date TEXT, raw TEXT, pulled_at TEXT)")
    else:
        conn.execute("CREATE TABLE other (id INTEGER)")
    conn.commit()
    conn.close()


def _alc_db(path: Path, *, with_pr: bool = True) -> None:
    conn = sqlite3.connect(path)
    if with_pr:
        conn.execute("CREATE TABLE pr_orders (id INTEGER)")
    else:
        conn.execute("CREATE TABLE other (id INTEGER)")
    conn.commit()
    conn.close()


def _separation_tree(path: Path, *, git: bool = True, track_env: bool = False, drop_pem: bool = False) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / ".env.example").write_text("OPENAI_API_KEY=\nBETA_METRICOOL_ENABLED=false\n", encoding="utf-8")
    gi = ".env\n.env.*\n!.env.example\n*.pem\n*.key\n*credentials*\n*secret*\n"
    if drop_pem:
        gi = gi.replace("*.pem\n", "")
    (path / ".gitignore").write_text(gi, encoding="utf-8")
    docs = path / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "RULE-Beta-Construction-Production-Sacred-2026-09-16.md").write_text(
        "PRODUCTION IS SACRED\n", encoding="utf-8"
    )
    if not git:
        return
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    if track_env:
        (path / ".env").write_text("X=1\n", encoding="utf-8")
        subprocess.run(["git", "add", "-f", ".env"], cwd=path, check=True, capture_output=True)


def test_guard_and_absent() -> None:
    check("refuses GREEN token", health._status("GREEN") == "ERROR")
    check("keeps READ_OK token", health._status("READ_OK") == "READ_OK")
    with _Env():
        os.environ["BETA_AUTH_MODE"] = "development_assertion"
        os.environ["BETA_METRICOOL_ENABLED"] = "false"
        os.environ["BETA_METRICOOL_WRITE_ENABLED"] = "false"
        os.environ["BETA_METRICOOL_CREDS_PATH"] = ""
        missing = ROOT / "state" / "no-such-esb-integration-health.sqlite"
        report = health.build_report(esb_path=missing, alchemist_path=missing, env_root=ROOT / "state" / "no-such-env-root")
    ids = [row["cap_id"] for row in report["connectors"]]
    check("seven connectors", ids == [f"CAP-INTG-0{n}" for n in range(1, 8)], str(ids))
    by = _by_id(report)
    check("yanolja not configured", by["CAP-INTG-01"]["status"] == "NOT_CONFIGURED")
    check("yanolja stays ABSENT note", by["CAP-INTG-01"]["ledger_maturity_unchanged"] == "ABSENT")
    check("workspace not probed", by["CAP-INTG-03"]["status"] == "NOT_CONFIGURED")
    check("bank not probed", by["CAP-INTG-04"]["status"] == "NOT_CONFIGURED")
    check("registry not configured", by["CAP-INTG-06"]["status"] == "NOT_CONFIGURED")
    check("missing esb not configured", by["CAP-INTG-02"]["status"] == "NOT_CONFIGURED", by["CAP-INTG-02"]["status"])
    check("missing env not configured", by["CAP-INTG-07"]["status"] == "NOT_CONFIGURED", by["CAP-INTG-07"]["status"])
    check("intg07 note stays SPECIFIED", by["CAP-INTG-07"]["ledger_maturity_unchanged"] == "SPECIFIED")
    check("no green in report", _no_green(report))
    check("ledger write false", report["ledger_write"] is False)
    check("network probes false", report["network_probes"] is False)
    check("external writes false", report["external_writes"] is False)
    check("promotes ledger false", all(row["promotes_ledger"] is False for row in report["connectors"]))


def test_esb_and_alchemist(td: Path) -> None:
    good = td / "esb.sqlite"
    thin = td / "thin.sqlite"
    junk = td / "junk.sqlite"
    _sales_db(good, with_sales=True)
    _sales_db(thin, with_sales=False)
    junk.write_bytes(b"not a database")
    with _Env():
        os.environ["BETA_AUTH_MODE"] = "development_assertion"
        os.environ["BETA_METRICOOL_ENABLED"] = "false"
        os.environ["BETA_METRICOOL_WRITE_ENABLED"] = "false"
        ok = health.build_report(esb_path=good, alchemist_path=td / "missing-alc.sqlite", env_root=td / "no-env")
        degraded = health.build_report(esb_path=thin, alchemist_path=td / "missing-alc.sqlite", env_root=td / "no-env")
        broken = health.build_report(esb_path=junk, alchemist_path=td / "missing-alc.sqlite", env_root=td / "no-env")
        refused = health.build_report(
            esb_path=Path("/tmp/wolf-system/esb.sqlite"),
            alchemist_path=td / "missing-alc.sqlite",
            env_root=td / "no-env",
        )
    check("esb sales READ_OK", _by_id(ok)["CAP-INTG-02"]["status"] == "READ_OK")
    check("esb missing table DEGRADED", _by_id(degraded)["CAP-INTG-02"]["status"] == "DEGRADED")
    check("esb junk ERROR", _by_id(broken)["CAP-INTG-02"]["status"] == "ERROR", _by_id(broken)["CAP-INTG-02"]["status"])
    check("wolf-system path ERROR", _by_id(refused)["CAP-INTG-02"]["status"] == "ERROR")
    check("esb reports do not say GREEN", _no_green(ok) and _no_green(degraded) and _no_green(broken))

    alc = td / "alchemist.sqlite"
    bare = td / "bare.sqlite"
    _alc_db(alc, with_pr=True)
    _alc_db(bare, with_pr=False)
    with _Env():
        os.environ["BETA_METRICOOL_ENABLED"] = "false"
        present = health.build_report(esb_path=td / "no-esb.sqlite", alchemist_path=alc, env_root=td / "no-env")
        partial = health.build_report(esb_path=td / "no-esb.sqlite", alchemist_path=bare, env_root=td / "no-env")
        gone = health.build_report(esb_path=td / "no-esb.sqlite", alchemist_path=td / "no-alc.sqlite", env_root=td / "no-env")
    src = {row["source_id"]: row for row in present["sources"]}
    check("alchemist schema READ_OK", src["alchemist"]["status"] == "READ_OK", src["alchemist"]["evidence"][:180])
    check("alchemist flag still in evidence", "INACCESSIBLE" in src["alchemist"]["evidence"])
    partial_src = {row["source_id"]: row for row in partial["sources"]}
    check("alchemist missing table DEGRADED", partial_src["alchemist"]["status"] == "DEGRADED")
    gone_src = {row["source_id"]: row for row in gone["sources"]}
    check("alchemist missing NOT_CONFIGURED", gone_src["alchemist"]["status"] == "NOT_CONFIGURED")


def test_metricool_and_cf() -> None:
    with _Env():
        os.environ["BETA_AUTH_MODE"] = "development_assertion"
        os.environ["BETA_METRICOOL_ENABLED"] = "false"
        os.environ["BETA_METRICOOL_WRITE_ENABLED"] = "false"
        os.environ["BETA_METRICOOL_CREDS_PATH"] = str(ROOT / "private" / "metricool.local.json")
        off = health.build_report(esb_path=ROOT / "no-esb.sqlite", alchemist_path=ROOT / "no-alc.sqlite", env_root=ROOT / "no-env-root")
        os.environ["BETA_METRICOOL_ENABLED"] = "true"
        os.environ["BETA_METRICOOL_WRITE_ENABLED"] = "true"
        armed = health.build_report(esb_path=ROOT / "no-esb.sqlite", alchemist_path=ROOT / "no-alc.sqlite", env_root=ROOT / "no-env-root")
        os.environ["BETA_METRICOOL_CREDS_PATH"] = ""
        no_path = health.build_report(esb_path=ROOT / "no-esb.sqlite", alchemist_path=ROOT / "no-alc.sqlite", env_root=ROOT / "no-env-root")
    check("metricool disabled NOT_CONFIGURED", _by_id(off)["CAP-INTG-05"]["status"] == "NOT_CONFIGURED")
    check("metricool path set is UNKNOWN", _by_id(armed)["CAP-INTG-05"]["status"] == "UNKNOWN", _by_id(armed)["CAP-INTG-05"]["status"])
    check("metricool never READ_OK from status", _by_id(armed)["CAP-INTG-05"]["status"] != "READ_OK")
    check("metricool no path NOT_CONFIGURED", _by_id(no_path)["CAP-INTG-05"]["status"] == "NOT_CONFIGURED")
    check("cf dev mode NOT_CONFIGURED", {s["source_id"]: s for s in off["sources"]}["cf_access"]["status"] == "NOT_CONFIGURED")

    with _Env():
        os.environ["BETA_AUTH_MODE"] = "cloudflare_access"
        os.environ.pop("BETA_CF_ACCESS_AUD", None)
        os.environ["BETA_CF_ACCESS_TEAM_DOMAIN"] = "https://wolfcommand.cloudflareaccess.com"
        ra._ENV_LOADED = True
        bare_cf = health._read_cf_presence()
        os.environ["BETA_CF_ACCESS_AUD"] = "test-aud"
        present_cf = health._read_cf_presence()
        os.environ["BETA_CF_ACCESS_TEAM_DOMAIN"] = "http://not-access.example"
        bad_cf = health._read_cf_presence()
    check("cf missing aud NOT_CONFIGURED", bare_cf["status"] == "NOT_CONFIGURED", bare_cf["status"])
    check("cf config present UNKNOWN", present_cf["status"] == "UNKNOWN", present_cf["evidence"][:160])
    check("cf bad domain ERROR", bad_cf["status"] == "ERROR", bad_cf["status"])
    check("cf never READ_OK", present_cf["status"] != "READ_OK")


def test_env_fixtures(td: Path) -> None:
    empty = td / "empty-env"
    empty.mkdir()
    full = td / "full-env"
    _separation_tree(full, git=True, track_env=False)
    partial = td / "partial-env"
    _separation_tree(partial, git=True, drop_pem=True)
    tracked = td / "tracked-env"
    _separation_tree(tracked, git=True, track_env=True)
    no_git = td / "nogit-env"
    _separation_tree(no_git, git=False)
    with _Env():
        os.environ["BETA_AUTH_MODE"] = "development_assertion"
        os.environ["BETA_METRICOOL_ENABLED"] = "false"
        os.environ["BETA_METRICOOL_WRITE_ENABLED"] = "false"
        missing = health.build_report(esb_path=td / "no.sqlite", alchemist_path=td / "no.sqlite", env_root=empty)
        ok = health.build_report(esb_path=td / "no.sqlite", alchemist_path=td / "no.sqlite", env_root=full)
        deg = health.build_report(esb_path=td / "no.sqlite", alchemist_path=td / "no.sqlite", env_root=partial)
        err = health.build_report(esb_path=td / "no.sqlite", alchemist_path=td / "no.sqlite", env_root=tracked)
        ungitted = health.build_report(esb_path=td / "no.sqlite", alchemist_path=td / "no.sqlite", env_root=no_git)
    check("empty env NOT_CONFIGURED", _by_id(missing)["CAP-INTG-07"]["status"] == "NOT_CONFIGURED")
    check("full env READ_OK", _by_id(ok)["CAP-INTG-07"]["status"] == "READ_OK", _by_id(ok)["CAP-INTG-07"]["evidence"][:200])
    check("partial env DEGRADED", _by_id(deg)["CAP-INTG-07"]["status"] == "DEGRADED", _by_id(deg)["CAP-INTG-07"]["evidence"][:200])
    check("tracked dotenv ERROR", _by_id(err)["CAP-INTG-07"]["status"] == "ERROR", _by_id(err)["CAP-INTG-07"]["evidence"][:200])
    check("no git index DEGRADED", _by_id(ungitted)["CAP-INTG-07"]["status"] == "DEGRADED")
    check("env READ_OK is not a ledger promote", _by_id(ok)["CAP-INTG-07"]["promotes_ledger"] is False)


def test_ledger_and_source() -> None:
    before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    src = (SCRIPTS / "core" / "integration_health.py").read_text(encoding="utf-8")
    check("module does not import urllib", "urllib" not in src and "requests" not in src)
    check("module does not call project_prs", "project_prs" not in src)
    check("module does not call snapshot_day", "snapshot_day" not in src)
    check("module does not name GREEN", "GREEN" not in src)
    with _Env():
        os.environ["BETA_AUTH_MODE"] = "development_assertion"
        os.environ["BETA_METRICOOL_ENABLED"] = "false"
        os.environ["BETA_METRICOOL_WRITE_ENABLED"] = "false"
        health.build_report(esb_path=ROOT / "no-esb.sqlite", alchemist_path=ROOT / "no-alc.sqlite", env_root=ROOT / "no-env-root")
    check("ledger bytes unchanged", LEDGER.read_bytes() == before)
    check("score history unchanged", HISTORY.read_bytes() == history_before)
    doc = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("ledger still 77", len(doc) == 77, str(len(doc)))
    check("CAP-INTG-01 stays ABSENT", doc["CAP-INTG-01"][0] == "ABSENT")
    check("CAP-INTG-07 stays SPECIFIED", doc["CAP-INTG-07"][0] == "SPECIFIED")
    for rel, digest in wip_before.items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        check(f"WIP untouched {Path(rel).name}", got == digest)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/integration-health" in serve)
    check("identity entry used", "resolve_request_identity" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)


def test_api(td: Path) -> None:
    esb = td / "api-esb.sqlite"
    _sales_db(esb, with_sales=True)
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
            req = Request(f"http://127.0.0.1:{port}{url_path}", headers=headers, method=method)
            try:
                with urlopen(req, timeout=20) as resp:
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

        st, _anon = call("GET", "/api/integration-health", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/integration-health", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/integration-health", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            by = _by_id(owner)
            check("owner sees yanolja NOT_CONFIGURED", by["CAP-INTG-01"]["status"] == "NOT_CONFIGURED")
            check("owner sees esb READ_OK", by["CAP-INTG-02"]["status"] == "READ_OK", by["CAP-INTG-02"]["status"])
            check("owner payload has no GREEN", _no_green(owner))
            check("owner person", owner.get("person_id") == "PERS-MATT")
        st, page_anon = call("GET", "/integration-health", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/integration-health", MATT)
        check(
            "owner page 200",
            st == 200 and isinstance(page, bytes) and b"CAP-INTG-01" in page and b"CAP-INTG-07" in page,
            str(st),
        )
        st, _post_anon = call("POST", "/api/integration-health", None)
        check("anon POST 403", st == 403, str(st))
        st, posted = call("POST", "/api/integration-health", MATT)
        check(
            "owner POST refused",
            st == 405 and isinstance(posted, dict) and posted.get("error") == "writes_refused",
            str(posted)[:200],
        )
    finally:
        httpd.shutdown()
        os.environ.pop("WOLF_ESB_SQLITE", None)


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="intg-health-"))
    ledger_before = LEDGER.read_bytes()
    try:
        test_guard_and_absent()
        test_esb_and_alchemist(td)
        test_metricool_and_cf()
        test_env_fixtures(td)
        test_ledger_and_source()
        test_api(td)
    finally:
        shutil.rmtree(td, ignore_errors=True)
        os.environ.pop("WOLF_ESB_SQLITE", None)
        os.environ.pop("WOLF_ALCHEMIST_DB", None)
    check("ledger file still unchanged at exit", LEDGER.read_bytes() == ledger_before)
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
