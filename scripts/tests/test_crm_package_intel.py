#!/usr/bin/env python3
"""CAP-CRM-03 package register. Empty is not a price. No booking. No PROVEN."""
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
os.environ.pop("WOLF_CRM_PACKAGE_DB", None)
os.environ.pop("WOLF_ALLOW_LIVE_CRM_PACKAGE", None)

from core import crm_package_intel as pkg  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "crm_package_intel.py"
CR_ID = "CR-e5ff219bb1d585f7"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
VALID = {
    "name": "Fixture stay",
    "brand": "habitat",
    "status": "NAMED",
    "evidence_refs": ["EV-fixture-note"],
}


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
            conn.execute(
                "SELECT COUNT(*) FROM wolf_completion_items WHERE state='RESOLVED'"
            ).fetchone()[0]
        )
    finally:
        conn.close()


def _package_table() -> str | None:
    conn = sqlite3.connect(str(CATALOG_DB))
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE name='package_products'"
        ).fetchone()
    finally:
        conn.close()
    return None if row is None else row[0]


def test_empty_register() -> None:
    report = pkg.build_register()
    check("empty flag", report["empty"] is True and report["recorded_count"] == 0)
    check("market unread", report["market_package_count"] is None and report["empty_is_market_census"] is False)
    check("price unread", report["price"] is None and report["pricing_is_truth"] is False and report["margin"] is None)
    check("demand unread", report["demand"] is None)
    check("no booking", report["booking_mutated"] is False)
    check("no products", report["products"] == [])
    check("schema id", report["schema_id"] == pkg.SCHEMA_ID and report["schema"]["additionalProperties"] is False)
    check("schema no price", report["schema"]["price_property"] is False and report["schema"]["status_enum"] == ["NAMED"])
    check("skeleton label", report["framework_skeleton"] == "BUILT")
    check("ledger not written", report["ledger_write"] is False and report["cr_resolved"] is False)
    flags = report["honesty"]
    check("cap bound", flags["cap"] == "CAP-CRM-03" and flags["cr_id"] == CR_ID)
    check("ledger stays specified", flags["maturity"] == "SPECIFIED" and flags["ledger_maturity"] == "SPECIFIED")
    check("ceiling label built", flags["maturity_ceiling"] == "BUILT" and flags["slice_label"] == "BUILT")
    check("not proven ready", flags["proven"] is False and flags["ready"] is False and flags["invented_proven"] is False)
    check("cr open", flags["cr_state"] == "OPEN" and flags["cr_resolved"] is False and flags["cr_blocker"] == "NEEDS_ENGINEERING")
    check("cr next action", flags["cr_next_action"] == "Implementation" and flags["cr_capability"] == "CAP-CRM-03")
    brands = report["brands"]
    check("brands read", isinstance(brands, list) and report["brand_allowlist_unread"] is False and len(brands) >= 1)
    ids = {row["brand_id"] for row in brands or []}
    check("habitat is a brand not a package", "habitat" in ids and "BZG-UMA" in ids)
    check(
        "brand rows carry no package",
        all(row["package"] is None and row["price"] is None for row in brands or []),
    )
    check("live db absent", not pkg.DEFAULT_DB.exists())


def test_register_and_refuses(td: Path) -> None:
    db = td / "packages.sqlite"
    booking = td / "bookings.sqlite"
    booking.write_bytes(b"sentinel-booking")
    before = booking.read_bytes()
    try:
        pkg.register_product(dict(VALID), person_id="PERS-OTHER", db_path=db)
        check("staff register refused", False)
    except pkg.PackageIntelError as exc:
        check("staff register refused", exc.code == "forbidden", exc.code)
    check("refused register wrote nothing", not db.exists())
    try:
        pkg.register_product({}, person_id="PERS-MATT", db_path=db)
        check("empty body refused", False)
    except pkg.PackageIntelError as exc:
        check("empty body refused", exc.code == "extra_field_refused" or exc.code == "fields_required", exc.code)
    bare = {"name": "Fixture stay", "brand": "habitat", "status": "NAMED"}
    try:
        pkg.register_product(bare, person_id="PERS-MATT", db_path=db)
        check("missing evidence refused", False)
    except pkg.PackageIntelError as exc:
        check("missing evidence refused", exc.code == "evidence_required", exc.code)
    priced = dict(VALID)
    priced["price"] = "1500000"
    try:
        pkg.register_product(priced, person_id="PERS-MATT", db_path=db)
        check("price key refused", False)
    except pkg.PackageIntelError as exc:
        check("price key refused", exc.code == "price_refused", exc.code)
    named_price = dict(VALID)
    named_price["name"] = "1500000"
    try:
        pkg.register_product(named_price, person_id="PERS-MATT", db_path=db)
        check("numeric name refused", False)
    except pkg.PackageIntelError as exc:
        check("numeric name refused", exc.code == "price_refused", exc.code)
    bad_ref = dict(VALID)
    bad_ref["evidence_refs"] = ["1500000"]
    try:
        pkg.register_product(bad_ref, person_id="PERS-MATT", db_path=db)
        check("numeric evidence refused", False)
    except pkg.PackageIntelError as exc:
        check("numeric evidence refused", exc.code == "price_refused", exc.code)
    booked = dict(VALID)
    booked["booking"] = "BK-1"
    try:
        pkg.register_product(booked, person_id="PERS-MATT", db_path=db)
        check("booking key refused", False)
    except pkg.PackageIntelError as exc:
        check("booking key refused", exc.code == "booking_refused", exc.code)
    check("booking sentinel unchanged", booking.read_bytes() == before)
    try:
        pkg.register_product(dict(VALID), person_id="PERS-MATT", db_path=booking)
        check("booking path refused", False)
    except pkg.PackageIntelError as exc:
        check("booking path refused", exc.code == "booking_refused", exc.code)
    check("booking sentinel still unchanged", booking.read_bytes() == before)
    for status, code in (
        ("PROVEN", "proven_refused"),
        ("READY", "ready_refused"),
        ("PRICED", "price_refused"),
        ("BOOKED", "booking_refused"),
        ("LIVE", "status_refused"),
    ):
        body = dict(VALID)
        body["status"] = status
        try:
            pkg.register_product(body, person_id="PERS-MATT", db_path=db)
            check(f"status {status} refused", False)
        except pkg.PackageIntelError as exc:
            check(f"status {status} refused", exc.code == code, exc.code)
    unknown = dict(VALID)
    unknown["brand"] = "NOT-A-BRAND"
    try:
        pkg.register_product(unknown, person_id="PERS-MATT", db_path=db)
        check("unknown brand refused", False)
    except pkg.PackageIntelError as exc:
        check("unknown brand refused", exc.code == "brand_unknown", exc.code)
    check("refuses left db absent", not db.exists())
    row = pkg.register_product(dict(VALID), person_id="PERS-MATT", db_path=db)
    check("register ok", row["ok"] is True and row["status"] == "NAMED" and row["brand"] == "habitat")
    check("register has evidence", row["evidence_refs"] == ["EV-fixture-note"] and row["price"] is None)
    check("register no booking", row["booking_mutated"] is False and row["market_package_count"] is None)
    check("register no ledger", row["ledger_write"] is False and row["cr_resolved"] is False)
    conn = sqlite3.connect(str(db))
    try:
        cols = [item[1] for item in conn.execute("PRAGMA table_info(package_products)")]
        count = conn.execute("SELECT COUNT(*) FROM package_products").fetchone()[0]
    finally:
        conn.close()
    check("no price column", "price" not in cols and "amount" not in cols, str(cols))
    check("one row stored", count == 1)
    listed = pkg.list_products(db)
    check("list one", len(listed) == 1 and listed[0]["id"] == row["id"] and listed[0]["price"] is None)
    built = pkg.build_register(db)
    check("built not a census", built["empty"] is False and built["recorded_count"] == 1 and built["market_package_count"] is None)
    check("built price null", built["price"] is None and built["pricing_is_truth"] is False and built["booking_mutated"] is False)
    found = pkg.read_product(row["id"], db)
    check("read row", found["ok"] is True and found["product"]["name"] == "Fixture stay" and found["price"] is None)
    try:
        pkg.read_product("NO-SUCH", db)
        check("unknown id refused", False)
    except pkg.PackageIntelError as exc:
        check("unknown id refused", exc.code == "not_found", exc.code)
    try:
        pkg.register_product(dict(VALID), person_id="PERS-MATT", db_path=None)
        check("live guard", False)
    except pkg.PackageIntelError as exc:
        check("live guard", exc.code == "live_guard", exc.code)
    check("live db still absent", not pkg.DEFAULT_DB.exists())
    try:
        pkg.register_product(dict(VALID), person_id="PERS-MATT", db_path=td / "alchemist" / "pkg.sqlite")
        check("alchemist path refused", False)
    except pkg.PackageIntelError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    try:
        pkg.register_product(dict(VALID), person_id="PERS-MATT", db_path=CATALOG_DB)
        check("catalog path refused", False)
    except pkg.PackageIntelError as exc:
        check("catalog path refused", exc.code == "catalog_refused", exc.code)
    try:
        pkg.register_product(dict(VALID), person_id="PERS-MATT", db_path=td / "production" / "pkg.sqlite")
        check("production path refused", False)
    except pkg.PackageIntelError as exc:
        check("production path refused", exc.code == "not_beta", exc.code)
    try:
        pkg.refuse_proven({})
        check("proven helper", False)
    except pkg.PackageIntelError as exc:
        check("proven helper", exc.code == "proven_refused", exc.code)
    try:
        pkg.refuse_ready({})
        check("ready helper", False)
    except pkg.PackageIntelError as exc:
        check("ready helper", exc.code == "ready_refused", exc.code)
    try:
        pkg.resolve_cr()
        check("resolve helper", False)
    except pkg.PackageIntelError as exc:
        check("resolve helper", exc.code == "resolve_refused", exc.code)
    try:
        pkg.mark_proven()
        check("mark proven helper", False)
    except pkg.PackageIntelError as exc:
        check("mark proven helper", exc.code == "proven_refused", exc.code)
    try:
        pkg.refuse_fill({})
        check("fill helper", False)
    except pkg.PackageIntelError as exc:
        check("fill helper", exc.code == "slots_refused", exc.code)
    try:
        pkg.refuse_invent_metrics({})
        check("metrics helper", False)
    except pkg.PackageIntelError as exc:
        check("metrics helper", exc.code == "invent_metrics_refused", exc.code)
    try:
        pkg.guard_query(price="0")
        check("query price refused", False)
    except pkg.PackageIntelError as exc:
        check("query price refused", exc.code == "price_refused", exc.code)
    try:
        pkg.guard_query(demand="0")
        check("query demand refused", False)
    except pkg.PackageIntelError as exc:
        check("query demand refused", exc.code == "invent_metrics_refused", exc.code)
    check("catalog has no package table", _package_table() is None)


def test_ledger_ceiling(td: Path) -> None:
    def write(state: str) -> Path:
        path = td / f"ledger-{state}.json"
        path.write_text(json.dumps({"CAP-CRM-03": [state, "note"]}), encoding="utf-8")
        return path

    specified = write("SPECIFIED")
    before = specified.read_bytes()
    flags = pkg.honesty_flags(specified, CATALOG_DB)
    check("specified ceiling", flags["maturity"] == "SPECIFIED" and flags["maturity_ceiling"] == "BUILT")
    check("specified file untouched", specified.read_bytes() == before)
    proven = write("PROVEN")
    proven_before = proven.read_bytes()
    flags = pkg.honesty_flags(proven, CATALOG_DB)
    check("already proven stays", flags["maturity"] == "PROVEN" and flags["maturity_ceiling"] == "PROVEN" and flags["invented_proven"] is False)
    check("proven file untouched", proven.read_bytes() == proven_before)
    ready = write("READY")
    ready_before = ready.read_bytes()
    flags = pkg.honesty_flags(ready, CATALOG_DB)
    check("already ready stays", flags["maturity"] == "READY" and flags["maturity_ceiling"] == "READY" and flags["invented_ready"] is False)
    check("ready file untouched", ready.read_bytes() == ready_before)
    green = write("GREEN")
    flags = pkg.honesty_flags(green, CATALOG_DB)
    check("green is unknown", flags["maturity"] == "UNKNOWN" and flags["maturity_ceiling"] == "BUILT")
    missing = pkg.honesty_flags(td / "missing-ledger.json", CATALOG_DB)
    check("missing ledger unknown", missing["maturity"] == "UNKNOWN" and missing["maturity_ceiling"] == "BUILT")


def test_source() -> None:
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
    check("module does not json.dump(", "json.dump(" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    check("module does not update completion", "UPDATE wolf_completion" not in src and "INSERT INTO wolf_completion" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/crm/package-intel" in serve)
    check("page route registered", "/crm-package-intel" in serve)
    check("price route refused", "/api/crm/package-intel/price" in serve)
    check("booking route refused", "/api/crm/package-intel/booking" in serve)
    check("prove route refused", "/api/crm/package-intel/prove" in serve)
    check("resolve route refused", "/api/crm/package-intel/resolve" in serve)
    check("register route present", "/api/crm/package-intel/register" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "crm-package-intel.html").read_text(encoding="utf-8")
    check("page says not a price", "not a price" in page and "No booking" in page)
    check("page does not resolve", "does not resolve" in page and "CAP-CRM-03" in page)


def test_api(td: Path) -> None:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ.pop("WOLF_ALCHEMIST_DB", None)
    os.environ["WOLF_CRM_PACKAGE_DB"] = str(td / "http-packages.sqlite")
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
        def call(method: str, url_path: str, subject: str | None, body: dict | None = None):
            headers = {"Accept": "application/json"}
            if subject:
                headers["X-Wolf-Subject"] = subject
            data = None
            if method != "GET":
                data = json.dumps({} if body is None else body).encode()
                headers["Content-Type"] = "application/json"
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

        st, _anon = call("GET", "/api/crm/package-intel", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/crm/package-intel", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/crm/package-intel", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner empty", owner.get("empty") is True and owner.get("recorded_count") == 0 and owner.get("products") == [])
            check("owner market null", owner.get("market_package_count") is None and owner.get("demand") is None)
            check("owner price null", owner.get("price") is None and owner.get("pricing_is_truth") is False)
            check("owner no booking", owner.get("booking_mutated") is False and owner.get("cr_resolved") is False)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner skeleton", owner.get("framework_skeleton") == "BUILT")
            flags = owner.get("honesty") or {}
            check("owner honesty", flags.get("cr_id") == CR_ID and flags.get("cr_state") == "OPEN")
            check("owner ceiling", flags.get("maturity") == "SPECIFIED" and flags.get("maturity_ceiling") == "BUILT")
            brands = owner.get("brands") or []
            check(
                "owner brands not packages",
                isinstance(brands, list)
                and any(row.get("brand_id") == "habitat" for row in brands)
                and all(row.get("package") is None and row.get("price") is None for row in brands),
            )
        st, schema = call("GET", "/api/crm/package-intel/schema", MATT)
        check(
            "owner schema 200",
            st == 200 and isinstance(schema, dict) and (schema.get("schema") or {}).get("schema_id") == pkg.SCHEMA_ID,
            str(st),
        )
        st, products = call("GET", "/api/crm/package-intel/products", MATT)
        check("owner products 200", st == 200 and isinstance(products, dict) and products.get("recorded_count") == 0, str(st))
        st, brands = call("GET", "/api/crm/package-intel/brands", MATT)
        check(
            "owner brands 200",
            st == 200 and isinstance(brands, dict) and brands.get("brands_are_not_packages") is True,
            str(st),
        )
        st, missing = call("GET", "/api/crm/package-intel/PKG-00000000-0000-0000-0000-000000000000", MATT)
        check("unknown id 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(st))
        st, page = call("GET", "/crm-package-intel", MATT)
        check(
            "owner page 200",
            st == 200 and isinstance(page, (bytes, bytearray)) and b"not a price" in page and b"No booking" in page,
            str(st),
        )
        st, _page_anon = call("GET", "/crm-package-intel", None)
        check("anon page 403", st == 403, str(st))
        st, _post_anon = call("POST", "/api/crm/package-intel/register", None, VALID)
        check("anon POST 403", st == 403, str(st))
        st, priced = call("POST", "/api/crm/package-intel/price", MATT, {"price": 100})
        check("price POST 405", st == 405 and isinstance(priced, dict) and priced.get("error") == "price_refused", str(priced)[:180])
        st, booked = call("POST", "/api/crm/package-intel/booking", MATT, {})
        check("booking POST 405", st == 405 and isinstance(booked, dict) and booked.get("error") == "booking_refused", str(booked)[:180])
        st, proved = call("POST", "/api/crm/package-intel/prove", MATT, {})
        check("prove POST 405", st == 405 and isinstance(proved, dict) and proved.get("error") == "proven_refused", str(proved)[:180])
        st, ready = call("POST", "/api/crm/package-intel/ready", MATT, {})
        check("ready POST 405", st == 405 and isinstance(ready, dict) and ready.get("error") == "ready_refused", str(ready)[:180])
        st, resolve = call("POST", "/api/crm/package-intel/resolve", MATT, {})
        check("resolve POST 405", st == 405 and isinstance(resolve, dict) and resolve.get("error") == "resolve_refused", str(resolve)[:180])
        st, prod = call("POST", "/api/crm/package-intel/production", MATT, {})
        check("production POST 405", st == 405 and isinstance(prod, dict) and prod.get("error") == "production_refused", str(prod)[:180])
        st, fill = call("POST", "/api/crm/package-intel/fill", MATT, {})
        check("fill POST 405", st == 405 and isinstance(fill, dict) and fill.get("error") == "slots_refused", str(fill)[:180])
        st, bare = call("POST", "/api/crm/package-intel", MATT, {})
        check("bare POST 405", st == 405 and isinstance(bare, dict) and bare.get("error") == "writes_refused", str(bare)[:180])
        st, put = call("PUT", "/api/crm/package-intel", MATT, VALID)
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:180])
        st, patch = call("PATCH", "/api/crm/package-intel", MATT, VALID)
        check("owner PATCH 405", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:180])
        st, qprice = call("GET", "/api/crm/package-intel?price=0", MATT)
        check("query price http refused", st == 405 and isinstance(qprice, dict) and qprice.get("error") == "price_refused", str(qprice)[:180])
        st, qbook = call("GET", "/api/crm/package-intel?booking=1", MATT)
        check("query booking http refused", st == 405 and isinstance(qbook, dict) and qbook.get("error") == "booking_refused", str(qbook)[:180])
        st, bad = call("POST", "/api/crm/package-intel/register", MATT, {"name": "Fixture stay", "brand": "habitat", "status": "NAMED"})
        check("http missing evidence", st == 400 and isinstance(bad, dict) and bad.get("error") == "evidence_required", str(bad)[:180])
        st, created = call("POST", "/api/crm/package-intel/register", MATT, VALID)
        check(
            "owner register 200",
            st == 200 and isinstance(created, dict) and created.get("ok") is True and created.get("price") is None and created.get("booking_mutated") is False,
            str(created)[:240],
        )
        st, again = call("GET", "/api/crm/package-intel", MATT)
        check(
            "owner sees one row",
            st == 200 and isinstance(again, dict) and again.get("recorded_count") == 1 and again.get("market_package_count") is None and again.get("price") is None,
            str(again)[:240],
        )
        if isinstance(again, dict):
            row = (again.get("products") or [{}])[0]
            check("row fields", row.get("name") == "Fixture stay" and row.get("brand") == "habitat" and row.get("status") == "NAMED")
            check("row evidence", row.get("evidence_refs") == ["EV-fixture-note"] and row.get("price") is None)
        st, still = call("GET", "/api/crm/package-intel/products", MATT)
        check("products count one", st == 200 and isinstance(still, dict) and still.get("recorded_count") == 1 and still.get("market_package_count") is None, str(st))
    finally:
        httpd.shutdown()
        os.environ.pop("WOLF_CRM_PACKAGE_DB", None)


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="crm-package-intel-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    credits_before = hashlib.sha256(CREDITS.read_bytes()).hexdigest()
    cr_before = _cr_row()
    resolved_before = _resolved_count()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    live_existed = pkg.DEFAULT_DB.exists()
    try:
        test_empty_register()
        test_register_and_refuses(td)
        test_ledger_ceiling(td)
        test_source()
        test_api(td)
    finally:
        shutil.rmtree(td, ignore_errors=True)
        os.environ.pop("WOLF_CRM_PACKAGE_DB", None)
        os.environ.pop("WOLF_ESB_SQLITE", None)
        os.environ.pop("WOLF_ALCHEMIST_DB", None)
    check("ledger file still unchanged at exit", LEDGER.read_bytes() == ledger_before)
    check("score history unchanged", HISTORY.read_bytes() == history_before)
    check("credits unchanged", hashlib.sha256(CREDITS.read_bytes()).hexdigest() == credits_before)
    check("cr row unchanged", _cr_row() == cr_before, str(_cr_row()))
    check("resolved count unchanged", _resolved_count() == resolved_before)
    for rel, digest in wip_before.items():
        check(f"wip unchanged {Path(rel).name}", hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest)
    check("live register still absent" if not live_existed else "live register untouched", not pkg.DEFAULT_DB.exists() if not live_existed else True)
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
