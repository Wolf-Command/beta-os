#!/usr/bin/env python3
"""Intel evaluation + cost ledger (Beta). No prices invented. Not PROVEN."""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import shutil
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
os.environ.pop("WOLF_ALLOW_LIVE_INTEL_EVAL", None)
os.environ.pop("WOLF_INTEL_EVAL_DB", None)

from core import intel_eval_cost as ledger  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "intel_eval_cost_ledger.sqlite"
LEDGER_JSON = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
MODULE_PATH = SCRIPTS / "core" / "intel_eval_cost.py"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"

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

SCHEMA_COLS = (
    "record_id",
    "model",
    "route",
    "outcome",
    "token_input",
    "token_output",
    "token_total",
    "token_status",
    "cost_estimate",
    "cost_currency",
    "cost_status",
    "cost_source",
    "provenance_json",
    "actor",
    "recorded_at",
)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _tmp_dir() -> Path:
    td = ROOT / "catalog" / "backups" / f"tmp-intel-eval-cost-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    return td


def _db(td: Path) -> Path:
    return td / "intel_eval_cost.sqlite"


def _payload(**overrides: object) -> dict:
    body: dict = {
        "model": "none",
        "route": "intel.orchestrate",
        "outcome": "OK",
        "provenance": {"source": "unit-test", "call_id": "call-1"},
    }
    body.update(overrides)
    return body


def _count(path: Path) -> int:
    if not path.exists():
        return 0
    conn = sqlite3.connect(str(path))
    try:
        return int(
            conn.execute("SELECT COUNT(*) FROM intel_eval_cost_ledger").fetchone()[0]
        )
    finally:
        conn.close()


def _expect_error(name: str, fn, code: str) -> None:
    try:
        fn()
    except ledger.IntelEvalCostError as exc:
        check(name, exc.code == code, exc.code)
        return
    except Exception as exc:  # noqa: BLE001
        check(name, False, type(exc).__name__ + " " + str(exc))
        return
    check(name, False, "no error")


def test_honesty_and_source() -> None:
    flags = ledger.honesty_flags()
    check("honesty.no_invent_prices", flags.get("invent_prices") is False)
    check("honesty.no_spend_api", flags.get("external_spend_api") is False)
    check("honesty.no_billing", flags.get("auto_billing") is False)
    check("honesty.not_proven", flags.get("proven") is False)
    check("honesty.cap_not_proven", flags.get("cap_proven") is False)
    check("honesty.no_maturity_raise", flags.get("model_c_maturity_raised") is False)
    check("honesty.not_a_bill", flags.get("not_a_bill") is True)
    check("honesty.append_only", flags.get("append_only") is True)
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
    check("module has no openai", "openai" not in joined and "anthropic" not in joined)
    check(
        "module has no stripe",
        "stripe" not in joined and "import stripe" not in src,
    )
    check("module has no per-token price", "per_token" not in src and "price_per" not in src)
    check("module does not bind 8787", "8787" not in src)
    check("module does not write model c", "model-c-baseline" not in src)
    banned_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("urlopen", "request", "post"):
                banned_calls.append(node.func.attr)
    check("module has no http client call", not banned_calls, str(banned_calls))


def test_schema_record_read(td: Path) -> None:
    path = _db(td)
    missing = td / "missing-ledger.sqlite"
    empty = ledger.read_summary(ledger.OWNER_PERSON, db_path=missing)
    check("read missing does not create", not missing.exists())
    check("read missing count 0", empty.get("count") == 0)
    check("read missing not a bill", empty.get("not_a_bill") is True)
    check("read missing no sums", empty.get("cost_sums") == [])
    check("read missing summary honest", "No price was invented" in (empty.get("summary") or ""))

    rec = ledger.record_call(_payload(), person_id=ledger.OWNER_PERSON, db_path=path)
    check("record appended", rec.get("appended") is True and str(rec.get("record_id", "")).startswith("IEL-"))
    check("record cost not supplied", rec.get("cost_status") == ledger.COST_NOT_SUPPLIED)
    check("record honesty attached", (rec.get("honesty") or {}).get("invent_prices") is False)

    conn = sqlite3.connect(str(path))
    cols = [str(r[1]) for r in conn.execute("PRAGMA table_info(intel_eval_cost_ledger)")]
    triggers = {
        str(r[0])
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        )
    }
    conn.close()
    check("schema columns", all(c in cols for c in SCHEMA_COLS), str(cols))
    check("schema no-update trigger", "trg_intel_eval_cost_no_update" in triggers)
    check("schema no-delete trigger", "trg_intel_eval_cost_no_delete" in triggers)

    summary = ledger.read_summary(ledger.OWNER_PERSON, db_path=path)
    check("read count 1", summary.get("count") == 1, str(summary.get("count")))
    check("read cost incomplete", summary.get("cost_complete") is False)
    check("read no invented sum", summary.get("cost_sums") == [])
    latest = (summary.get("latest") or [{}])[0]
    check("read model", latest.get("model") == "none")
    check("read route", latest.get("route") == "intel.orchestrate")
    check("read outcome", latest.get("outcome") == "OK")
    check("read provenance label", latest.get("provenance_source") == "unit-test")
    check("summary says not a bill", "not a bill" in (summary.get("summary") or "").lower())

    with_tokens = ledger.record_call(
        _payload(
            tokens={"input": 3, "output": 4},
            provenance={"source": "unit-test"},
        ),
        person_id=ledger.OWNER_PERSON,
        db_path=path,
    )
    check("tokens stored without derived total", with_tokens.get("token_status") == "PROVIDED")
    summary2 = ledger.read_summary(ledger.OWNER_PERSON, db_path=path)
    row = next(r for r in summary2["latest"] if r["token_status"] == "PROVIDED")
    check("token total not invented", row.get("token_total") is None)
    check("token input kept", row.get("token_input") == 3 and row.get("token_output") == 4)
    check("append count 2", summary2.get("count") == 2)

    priced = ledger.record_call(
        _payload(
            cost_estimate="1.25",
            cost_source="caller_supplied",
            currency="USD",
            provenance={"source": "caller"},
        ),
        person_id=ledger.OWNER_PERSON,
        db_path=path,
    )
    check("caller cost accepted", priced.get("cost_status") == "PROVIDED")
    other = ledger.record_call(
        _payload(
            cost_estimate="10",
            cost_source="caller_supplied",
            currency="IDR",
            provenance={"source": "caller"},
        ),
        person_id=ledger.OWNER_PERSON,
        db_path=path,
    )
    check("second currency accepted", other.get("cost_currency") == "IDR")
    mixed = ledger.read_summary(ledger.OWNER_PERSON, db_path=path)
    currencies = {row["currency"] for row in mixed.get("cost_sums") or []}
    check("currencies not merged", currencies == {"USD", "IDR"}, str(mixed.get("cost_sums")))
    check("cost still incomplete", mixed.get("cost_complete") is False)
    usd = next(row for row in mixed["cost_sums"] if row["currency"] == "USD")
    check("usd sum is supplied only", usd.get("sum") == "1.25" and usd.get("rows") == 1)


def test_refuse_paths(td: Path) -> None:
    path = _db(td)
    before = _count(path)

    def record(body: dict, person: str | None = ledger.OWNER_PERSON, db: Path | None = path):
        return ledger.record_call(body, person_id=person, db_path=db)

    _expect_error("refuse non-owner", lambda: record(_payload(), person="PERS-DEVI"), "denied")
    _expect_error("refuse missing person", lambda: record(_payload(), person=None), "denied")
    _expect_error("refuse missing model", lambda: record(_payload(model="")), "bad_model")
    _expect_error("refuse missing route", lambda: record(_payload(route="")), "bad_route")
    _expect_error("refuse bad outcome", lambda: record(_payload(outcome="BILLED")), "bad_outcome")
    _expect_error(
        "refuse negative tokens",
        lambda: record(_payload(tokens={"input": -1})),
        "bad_tokens",
    )
    _expect_error(
        "refuse mismatched token total",
        lambda: record(_payload(tokens={"input": 1, "output": 1, "total": 9})),
        "bad_tokens",
    )
    _expect_error(
        "refuse float price",
        lambda: record(_payload(cost_estimate=0.01, cost_source="caller_supplied")),
        "price_refused",
    )
    _expect_error(
        "refuse unsourced price",
        lambda: record(_payload(cost_estimate="0.50")),
        "price_refused",
    )
    _expect_error(
        "refuse price lookup",
        lambda: record(_payload(lookup_price=True)),
        "price_refused",
    )
    _expect_error(
        "refuse rate card",
        lambda: record(_payload(rate_card={"none": "0.01"})),
        "price_refused",
    )
    _expect_error(
        "refuse compute cost",
        lambda: record(_payload(compute_cost=True)),
        "price_refused",
    )
    _expect_error(
        "refuse billing",
        lambda: record(_payload(auto_billing=True)),
        "billing_refused",
    )
    _expect_error(
        "refuse spend api",
        lambda: record(_payload(spend_api="https://api.example/usage")),
        "spend_api_refused",
    )
    _expect_error(
        "refuse billing route",
        lambda: record(_payload(route="openai.billing.usage")),
        "spend_api_refused",
    )
    _expect_error(
        "refuse missing provenance",
        lambda: record(_payload(provenance=None)),
        "bad_provenance",
    )
    check("refuses wrote no rows", _count(path) == before, f"{_count(path)} != {before}")

    raised_u = False
    try:
        ledger.update_record("IEL-x")
    except NotImplementedError:
        raised_u = True
    check("update_record refused", raised_u)
    raised_d = False
    try:
        ledger.delete_record("IEL-x")
    except NotImplementedError:
        raised_d = True
    check("delete_record refused", raised_d)

    rid = ledger.record_call(_payload(), person_id=ledger.OWNER_PERSON, db_path=path)["record_id"]
    conn = sqlite3.connect(str(path))
    upd_blocked = False
    try:
        conn.execute(
            "UPDATE intel_eval_cost_ledger SET model=? WHERE record_id=?",
            ("rewritten", rid),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        upd_blocked = "append-only" in str(exc)
    del_blocked = False
    try:
        conn.execute(
            "DELETE FROM intel_eval_cost_ledger WHERE record_id=?",
            (rid,),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        del_blocked = "append-only" in str(exc)
    conn.close()
    check("sql UPDATE blocked", upd_blocked)
    check("sql DELETE blocked", del_blocked)
    check("row survived rewrite attempt", _count(path) == before + 1)

    outside = Path("/tmp") / f"intel-eval-not-beta-{os.getpid()}.sqlite"
    _expect_error(
        "refuse non-beta path",
        lambda: ledger.record_call(_payload(), person_id=ledger.OWNER_PERSON, db_path=outside),
        "not_beta",
    )
    check("non-beta file not created", not outside.exists())

    alchemist = td / "alchemist-ledger.sqlite"
    _expect_error(
        "refuse alchemist path",
        lambda: ledger.record_call(_payload(), person_id=ledger.OWNER_PERSON, db_path=alchemist),
        "alchemist_refused",
    )
    check("alchemist file not created", not alchemist.exists())

    prod = td / "money.sqlite"
    _expect_error(
        "refuse money.sqlite",
        lambda: ledger.record_call(_payload(), person_id=ledger.OWNER_PERSON, db_path=prod),
        "not_beta",
    )
    check("money.sqlite not created", not prod.exists())

    live_before = LIVE_DB.exists()
    _expect_error(
        "refuse live db in tests",
        lambda: ledger.record_call(_payload(), person_id=ledger.OWNER_PERSON, db_path=None),
        "live_guard",
    )
    check("live db not created by tests", LIVE_DB.exists() == live_before)


def test_model_c_and_wip() -> None:
    ledger_doc = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    check("model c still 77", len(ledger_doc) == 77, str(len(ledger_doc)))
    check("CAP-INTEL-01 stays BUILT", (ledger_doc.get("CAP-INTEL-01") or [""])[0] == "BUILT")
    check("CAP-INTEL-01 not PROVEN", (ledger_doc.get("CAP-INTEL-01") or [""])[0] != "PROVEN")
    check("CAP-INTEL-05 stays SPECIFIED", (ledger_doc.get("CAP-INTEL-05") or [""])[0] == "SPECIFIED")
    history = HISTORY.read_text(encoding="utf-8")
    check("score history has no eval ledger event", "intel-eval-cost" not in history)
    credits = (ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md").read_text(encoding="utf-8")
    check("credits SPECIFIED 0.05", "| SPECIFIED | 0.05 |" in credits)
    check("credits PROVEN 0.80", "| PROVEN | 0.80 |" in credits)
    for rel, digest in WIP.items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        check(f"WIP digest {Path(rel).name}", got == digest, got)
    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    for path in FORBIDDEN_STAGE:
        check(f"WIP not staged {Path(path).name}", path not in staged, str(staged))
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("beta route registered", "/api/intel/eval-cost" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)


def test_api(td: Path) -> None:
    path = td / "api-ledger.sqlite"
    os.environ["WOLF_INTEL_EVAL_DB"] = str(path)
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

        st, _anon = call("GET", "/api/intel/eval-cost", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/intel/eval-cost", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, _anon_post = call("POST", "/api/intel/eval-cost", None, _payload())
        check("anon POST 403", st == 403, str(st))
        st, _staff_post = call("POST", "/api/intel/eval-cost", STAFF, _payload())
        check("staff POST 403", st == 403, str(st))
        check("denied writes created no file", not path.exists())

        st, owner = call("GET", "/api/intel/eval-cost", MATT)
        check("owner GET 200", st == 200 and owner.get("ok") is True, str(owner)[:240])
        check("owner GET empty", owner.get("count") == 0)
        check("owner GET honesty", (owner.get("honesty") or {}).get("auto_billing") is False)
        check("owner GET did not create file", not path.exists())

        st, bad = call("POST", "/api/intel/eval-cost", MATT, _payload(model=""))
        check("owner bad model 400", st == 400 and bad.get("appended") is False, str(bad)[:200])
        st, price = call(
            "POST",
            "/api/intel/eval-cost",
            MATT,
            _payload(fetch_price=True),
        )
        check("owner price lookup 400", st == 400 and price.get("error") == "price_refused", str(price)[:200])
        st, bill = call(
            "POST",
            "/api/intel/eval-cost",
            MATT,
            _payload(charge=True),
        )
        check("owner billing 400", st == 400 and bill.get("error") == "billing_refused", str(bill)[:200])
        check("refused API wrote no file", not path.exists())

        st, ok = call("POST", "/api/intel/eval-cost", MATT, _payload())
        check("owner POST 200", st == 200 and ok.get("appended") is True, str(ok)[:240])
        check("owner POST no price", ok.get("cost_status") == "NOT_SUPPLIED")
        st, again = call("GET", "/api/intel/eval-cost", MATT)
        check("owner read after record", st == 200 and again.get("count") == 1, str(again)[:240])
        check("api summary not a bill", again.get("not_a_bill") is True)
    finally:
        httpd.shutdown()
        os.environ.pop("WOLF_INTEL_EVAL_DB", None)


def main() -> int:
    td = _tmp_dir()
    try:
        test_honesty_and_source()
        test_schema_record_read(td)
        test_refuse_paths(td)
        test_model_c_and_wip()
        test_api(td)
    finally:
        shutil.rmtree(td, ignore_errors=True)
        os.environ.pop("WOLF_INTEL_EVAL_DB", None)
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
