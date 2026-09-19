#!/usr/bin/env python3
"""CAP-MSC-01 asset register. Empty is not an inventory count. No payment. No PROVEN."""
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
os.environ.pop("WOLF_MSC_ASSET_DB", None)
os.environ.pop("WOLF_ALLOW_LIVE_MSC_ASSET", None)

from core import msc_asset_register as reg  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "msc_asset_register.py"
CR_ID = "CR-7ea69933a9d39ba9"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
VALID = {
    "venue": "LOC-ATRIUM-LOMBOK",
    "type": "pump",
    "status": "NOTED",
    "last_service": "Owner note only. Service was not proved.",
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


def _media_count() -> int:
    conn = sqlite3.connect(str(CATALOG_DB))
    try:
        return int(conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0])
    finally:
        conn.close()


def test_empty_register() -> None:
    report = reg.build_register()
    check("empty flag", report["empty"] is True and report["recorded_count"] == 0)
    check(
        "inventory unread",
        report["inventory_count"] is None
        and report["empty_is_inventory"] is False
        and report["recorded_is_inventory"] is False,
    )
    check("payment unread", report["payment"] is None and report["money"] is None)
    check("service not proved", report["service_proved"] is False)
    check("no rows", report["rows"] == [])
    check("schema id", report["schema_id"] == reg.SCHEMA_ID and report["schema"]["additionalProperties"] is False)
    check(
        "schema no payment",
        report["schema"]["payment_property"] is False
        and report["schema"]["inventory_property"] is False
        and report["schema"]["status_enum"] == ["NOTED"],
    )
    check("skeleton label", report["framework_skeleton"] == "BUILT")
    check("ledger not written", report["ledger_write"] is False and report["cr_resolved"] is False)
    flags = report["honesty"]
    check("cap bound", flags["cap"] == "CAP-MSC-01" and flags["cr_id"] == CR_ID)
    check("ledger stays specified", flags["maturity"] == "SPECIFIED" and flags["ledger_maturity"] == "SPECIFIED")
    check("ceiling label built", flags["maturity_ceiling"] == "BUILT" and flags["slice_label"] == "BUILT")
    check("not proven ready", flags["proven"] is False and flags["ready"] is False and flags["invented_proven"] is False)
    check("cr open", flags["cr_state"] == "OPEN" and flags["cr_resolved"] is False and flags["cr_blocker"] == "NEEDS_ENGINEERING")
    check("cr next action", flags["cr_next_action"] == "Register" and flags["cr_capability"] == "CAP-MSC-01")
    venues = report["venues"]
    check("venues read", isinstance(venues, list) and report["venue_allowlist_unread"] is False and len(venues) >= 1)
    ids = {row["location_id"] for row in venues or []}
    check("atrium is a location not an asset", "LOC-ATRIUM-LOMBOK" in ids)
    check(
        "location rows carry no asset",
        all(row["asset"] is None and row["inventory_count"] is None and row["payment"] is None for row in venues or []),
    )
    check("media library not inventory", report["media_library_is_not_inventory"] is True)
    check("live db absent", not reg.DEFAULT_DB.exists())


def test_register_and_refuses(td: Path) -> None:
    db = td / "assets.sqlite"
    money = td / "money.sqlite"
    money.write_bytes(b"sentinel-money")
    before = money.read_bytes()
    media_before = _media_count()
    try:
        reg.register_asset(dict(VALID), person_id="PERS-OTHER", db_path=db)
        check("staff register refused", False)
    except reg.AssetRegisterError as exc:
        check("staff register refused", exc.code == "forbidden", exc.code)
    check("refused register wrote nothing", not db.exists())
    try:
        reg.register_asset({}, person_id="PERS-MATT", db_path=db)
        check("empty body refused", False)
    except reg.AssetRegisterError as exc:
        check("empty body refused", exc.code in {"extra_field_refused", "fields_required", "venue_unknown"}, exc.code)
    bare = {"venue": "LOC-ATRIUM-LOMBOK", "type": "pump", "status": "NOTED"}
    try:
        reg.register_asset(bare, person_id="PERS-MATT", db_path=db)
        check("missing note refused", False)
    except reg.AssetRegisterError as exc:
        check("missing note refused", exc.code == "note_required", exc.code)
    paid = dict(VALID)
    paid["payment"] = "1500000"
    try:
        reg.register_asset(paid, person_id="PERS-MATT", db_path=db)
        check("payment key refused", False)
    except reg.AssetRegisterError as exc:
        check("payment key refused", exc.code == "payment_refused", exc.code)
    counted = dict(VALID)
    counted["inventory_count"] = 9
    try:
        reg.register_asset(counted, person_id="PERS-MATT", db_path=db)
        check("inventory key refused", False)
    except reg.AssetRegisterError as exc:
        check("inventory key refused", exc.code == "inventory_refused", exc.code)
    numeric_type = dict(VALID)
    numeric_type["type"] = "12"
    try:
        reg.register_asset(numeric_type, person_id="PERS-MATT", db_path=db)
        check("numeric type refused", False)
    except reg.AssetRegisterError as exc:
        check("numeric type refused", exc.code == "inventory_refused", exc.code)
    money_note = dict(VALID)
    money_note["last_service"] = "Paid Rp 500000 yesterday"
    try:
        reg.register_asset(money_note, person_id="PERS-MATT", db_path=db)
        check("money note refused", False)
    except reg.AssetRegisterError as exc:
        check("money note refused", exc.code == "payment_refused", exc.code)
    count_note = dict(VALID)
    count_note["last_service"] = "replaced 12 units on site"
    try:
        reg.register_asset(count_note, person_id="PERS-MATT", db_path=db)
        check("count note refused", False)
    except reg.AssetRegisterError as exc:
        check("count note refused", exc.code == "inventory_refused", exc.code)
    unknown = dict(VALID)
    unknown["venue"] = "LOC-INVENTED-SITE"
    try:
        reg.register_asset(unknown, person_id="PERS-MATT", db_path=db)
        check("unknown venue refused", False)
    except reg.AssetRegisterError as exc:
        check("unknown venue refused", exc.code == "venue_unknown", exc.code)
    check("money sentinel unchanged", money.read_bytes() == before)
    try:
        reg.register_asset(dict(VALID), person_id="PERS-MATT", db_path=money)
        check("money path refused", False)
    except reg.AssetRegisterError as exc:
        check("money path refused", exc.code == "not_beta", exc.code)
    check("money sentinel still unchanged", money.read_bytes() == before)
    try:
        reg.register_asset(dict(VALID), person_id="PERS-MATT", db_path=CATALOG_DB)
        check("catalog path refused", False)
    except reg.AssetRegisterError as exc:
        check("catalog path refused", exc.code == "catalog_refused", exc.code)
    check("media table count unchanged", _media_count() == media_before)
    for status, code in (
        ("PROVEN", "proven_refused"),
        ("READY", "ready_refused"),
        ("PAID", "payment_refused"),
        ("COUNTED", "inventory_refused"),
        ("LIVE", "status_refused"),
        ("SERVICED", "status_refused"),
    ):
        body = dict(VALID)
        body["status"] = status
        try:
            reg.register_asset(body, person_id="PERS-MATT", db_path=db)
            check(f"status {status} refused", False)
        except reg.AssetRegisterError as exc:
            check(f"status {status} refused", exc.code == code, exc.code)
    try:
        reg.register_asset(dict(VALID), person_id="PERS-MATT", db_path=None)
        check("live guard", False)
    except reg.AssetRegisterError as exc:
        check("live guard", exc.code == "live_guard", exc.code)
    check("live still absent after guard", not reg.DEFAULT_DB.exists())
    created = reg.register_asset(dict(VALID), person_id="PERS-MATT", db_path=db)
    check(
        "owner note stored",
        created["ok"] is True
        and created["status"] == "NOTED"
        and created["venue"] == "LOC-ATRIUM-LOMBOK"
        and created["type"] == "pump"
        and created["payment"] is None
        and created["inventory_count"] is None
        and created["cr_resolved"] is False
        and created["id"].startswith("AST-"),
    )
    listed = reg.build_register(db)
    check(
        "one note is not a census",
        listed["recorded_count"] == 1
        and listed["inventory_count"] is None
        and listed["recorded_is_inventory"] is False
        and listed["payment"] is None
        and listed["empty"] is False,
    )
    row = listed["rows"][0]
    check(
        "row fields",
        row["last_service"] == VALID["last_service"]
        and row["last_service_is_note"] is True
        and row["service_proved"] is False
        and row["venue_name"] == "Atrium Lombok",
    )
    one = reg.read_asset(created["id"], db_path=db)
    check("read one", one["ok"] is True and one["asset"]["id"] == created["id"] and one["inventory_count"] is None)
    try:
        reg.read_asset("NO-SUCH", db_path=db)
        check("bad id refused", False)
    except reg.AssetRegisterError as exc:
        check("bad id refused", exc.code == "not_found", exc.code)
    try:
        reg.refuse_resolve({})
        check("resolve helper", False)
    except reg.AssetRegisterError as exc:
        check("resolve helper", exc.code == "resolve_refused", exc.code)
    try:
        reg.mark_proven()
        check("prove helper", False)
    except reg.AssetRegisterError as exc:
        check("prove helper", exc.code == "proven_refused", exc.code)
    try:
        reg.guard_query(payment="1")
        check("query payment refused", False)
    except reg.AssetRegisterError as exc:
        check("query payment refused", exc.code == "payment_refused", exc.code)
    try:
        reg.guard_query(inventory="9")
        check("query inventory refused", False)
    except reg.AssetRegisterError as exc:
        check("query inventory refused", exc.code == "inventory_refused", exc.code)


def test_ledger_ceiling(td: Path) -> None:
    def write(state: str) -> Path:
        path = td / f"ledger-{state}.json"
        path.write_text(json.dumps({"CAP-MSC-01": [state, "note"]}), encoding="utf-8")
        return path

    specified = write("SPECIFIED")
    before = specified.read_bytes()
    flags = reg.honesty_flags(specified, CATALOG_DB)
    check("specified ceiling", flags["maturity"] == "SPECIFIED" and flags["maturity_ceiling"] == "BUILT")
    check("specified file untouched", specified.read_bytes() == before)
    proven = write("PROVEN")
    proven_before = proven.read_bytes()
    flags = reg.honesty_flags(proven, CATALOG_DB)
    check(
        "already proven stays",
        flags["maturity"] == "PROVEN" and flags["maturity_ceiling"] == "PROVEN" and flags["invented_proven"] is False,
    )
    check("proven file untouched", proven.read_bytes() == proven_before)
    ready = write("READY")
    ready_before = ready.read_bytes()
    flags = reg.honesty_flags(ready, CATALOG_DB)
    check(
        "already ready stays",
        flags["maturity"] == "READY" and flags["maturity_ceiling"] == "READY" and flags["invented_ready"] is False,
    )
    check("ready file untouched", ready.read_bytes() == ready_before)
    green = write("GREEN")
    flags = reg.honesty_flags(green, CATALOG_DB)
    check("green is unknown", flags["maturity"] == "UNKNOWN" and flags["maturity_ceiling"] == "BUILT")
    missing = reg.honesty_flags(td / "missing-ledger.json", CATALOG_DB)
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
    check("module does not read media assets", "FROM assets" not in src and "INTO assets" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/msc/assets" in serve)
    check("page route registered", "/msc-assets" in serve)
    check("payment route refused", "/api/msc/assets/payment" in serve)
    check("inventory route refused", "/api/msc/assets/inventory" in serve)
    check("prove route refused", "/api/msc/assets/prove" in serve)
    check("resolve route refused", "/api/msc/assets/resolve" in serve)
    check("register route present", "/api/msc/assets/register" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "msc-assets.html").read_text(encoding="utf-8")
    check("page says not an inventory count", "not an inventory count" in page and "not a payment" in page)
    check("page does not resolve", "does not resolve" in page and "CAP-MSC-01" in page)


def test_api(td: Path) -> None:
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ.pop("WOLF_ALCHEMIST_DB", None)
    os.environ["WOLF_MSC_ASSET_DB"] = str(td / "http-assets.sqlite")
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

        st, _anon = call("GET", "/api/msc/assets", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/msc/assets", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/msc/assets", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner empty", owner.get("empty") is True and owner.get("recorded_count") == 0 and owner.get("rows") == [])
            check("owner inventory null", owner.get("inventory_count") is None and owner.get("recorded_is_inventory") is False)
            check("owner payment null", owner.get("payment") is None and owner.get("money") is None)
            check("owner no proof", owner.get("service_proved") is False and owner.get("cr_resolved") is False)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner skeleton", owner.get("framework_skeleton") == "BUILT")
            flags = owner.get("honesty") or {}
            check("owner honesty", flags.get("cr_id") == CR_ID and flags.get("cr_state") == "OPEN")
            check("owner ceiling", flags.get("maturity") == "SPECIFIED" and flags.get("maturity_ceiling") == "BUILT")
            venues = owner.get("venues") or []
            check(
                "owner venues not assets",
                isinstance(venues, list)
                and any(row.get("location_id") == "LOC-ATRIUM-LOMBOK" for row in venues)
                and all(row.get("asset") is None and row.get("payment") is None for row in venues),
            )
        st, schema = call("GET", "/api/msc/assets/schema", MATT)
        check(
            "owner schema 200",
            st == 200 and isinstance(schema, dict) and (schema.get("schema") or {}).get("schema_id") == reg.SCHEMA_ID,
            str(st),
        )
        st, listed = call("GET", "/api/msc/assets/register", MATT)
        check("owner register view 200", st == 200 and isinstance(listed, dict) and listed.get("recorded_count") == 0, str(st))
        st, venues = call("GET", "/api/msc/assets/venues", MATT)
        check(
            "owner venues 200",
            st == 200 and isinstance(venues, dict) and venues.get("locations_are_not_assets") is True,
            str(st),
        )
        st, missing = call("GET", "/api/msc/assets/AST-00000000-0000-0000-0000-000000000000", MATT)
        check("unknown id 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(st))
        st, page = call("GET", "/msc-assets", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page, (bytes, bytearray))
            and b"not an inventory count" in page
            and b"not a payment" in page,
            str(st),
        )
        st, _page_anon = call("GET", "/msc-assets", None)
        check("anon page 403", st == 403, str(st))
        st, _post_anon = call("POST", "/api/msc/assets/register", None, VALID)
        check("anon POST 403", st == 403, str(st))
        st, paid = call("POST", "/api/msc/assets/payment", MATT, {"payment": 100})
        check("payment POST 405", st == 405 and isinstance(paid, dict) and paid.get("error") == "payment_refused", str(paid)[:180])
        st, counted = call("POST", "/api/msc/assets/inventory", MATT, {})
        check("inventory POST 405", st == 405 and isinstance(counted, dict) and counted.get("error") == "inventory_refused", str(counted)[:180])
        st, proved = call("POST", "/api/msc/assets/prove", MATT, {})
        check("prove POST 405", st == 405 and isinstance(proved, dict) and proved.get("error") == "proven_refused", str(proved)[:180])
        st, ready = call("POST", "/api/msc/assets/ready", MATT, {})
        check("ready POST 405", st == 405 and isinstance(ready, dict) and ready.get("error") == "ready_refused", str(ready)[:180])
        st, resolve = call("POST", "/api/msc/assets/resolve", MATT, {})
        check("resolve POST 405", st == 405 and isinstance(resolve, dict) and resolve.get("error") == "resolve_refused", str(resolve)[:180])
        st, prod = call("POST", "/api/msc/assets/production", MATT, {})
        check("production POST 405", st == 405 and isinstance(prod, dict) and prod.get("error") == "production_refused", str(prod)[:180])
        st, fill = call("POST", "/api/msc/assets/fill", MATT, {})
        check("fill POST 405", st == 405 and isinstance(fill, dict) and fill.get("error") == "slots_refused", str(fill)[:180])
        st, bare = call("POST", "/api/msc/assets", MATT, {})
        check("bare POST 405", st == 405 and isinstance(bare, dict) and bare.get("error") == "writes_refused", str(bare)[:180])
        st, put = call("PUT", "/api/msc/assets", MATT, VALID)
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:180])
        st, patch = call("PATCH", "/api/msc/assets", MATT, VALID)
        check("owner PATCH 405", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:180])
        st, qpay = call("GET", "/api/msc/assets?payment=1", MATT)
        check("query payment http refused", st == 405 and isinstance(qpay, dict) and qpay.get("error") == "payment_refused", str(qpay)[:180])
        st, qcount = call("GET", "/api/msc/assets?inventory=9", MATT)
        check("query inventory http refused", st == 405 and isinstance(qcount, dict) and qcount.get("error") == "inventory_refused", str(qcount)[:180])
        st, bad = call("POST", "/api/msc/assets/register", MATT, {"venue": "LOC-ATRIUM-LOMBOK", "type": "pump", "status": "NOTED"})
        check("http missing note", st == 400 and isinstance(bad, dict) and bad.get("error") == "note_required", str(bad)[:180])
        st, created = call("POST", "/api/msc/assets/register", MATT, VALID)
        check(
            "owner register 200",
            st == 200
            and isinstance(created, dict)
            and created.get("ok") is True
            and created.get("payment") is None
            and created.get("inventory_count") is None,
            str(created)[:240],
        )
        st, again = call("GET", "/api/msc/assets", MATT)
        check(
            "owner sees one note",
            st == 200
            and isinstance(again, dict)
            and again.get("recorded_count") == 1
            and again.get("inventory_count") is None
            and again.get("payment") is None,
            str(again)[:240],
        )
        if isinstance(again, dict):
            row = (again.get("rows") or [{}])[0]
            check(
                "http row fields",
                row.get("type") == "pump"
                and row.get("venue") == "LOC-ATRIUM-LOMBOK"
                and row.get("status") == "NOTED"
                and row.get("last_service") == VALID["last_service"],
            )
    finally:
        httpd.shutdown()
        os.environ.pop("WOLF_MSC_ASSET_DB", None)


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="msc-asset-register-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    credits_before = hashlib.sha256(CREDITS.read_bytes()).hexdigest()
    cr_before = _cr_row()
    resolved_before = _resolved_count()
    media_before = _media_count()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    live_existed = reg.DEFAULT_DB.exists()
    try:
        test_empty_register()
        test_register_and_refuses(td)
        test_ledger_ceiling(td)
        test_source()
        test_api(td)
    finally:
        shutil.rmtree(td, ignore_errors=True)
        os.environ.pop("WOLF_MSC_ASSET_DB", None)
        os.environ.pop("WOLF_ESB_SQLITE", None)
        os.environ.pop("WOLF_ALCHEMIST_DB", None)
    check("ledger file still unchanged at exit", LEDGER.read_bytes() == ledger_before)
    check("score history unchanged", HISTORY.read_bytes() == history_before)
    check("credits unchanged", hashlib.sha256(CREDITS.read_bytes()).hexdigest() == credits_before)
    check("cr row unchanged", _cr_row() == cr_before, str(_cr_row()))
    check("resolved count unchanged", _resolved_count() == resolved_before)
    check("media assets count unchanged", _media_count() == media_before)
    for rel, digest in wip_before.items():
        check(f"wip unchanged {Path(rel).name}", hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest)
    check("live register still absent" if not live_existed else "live register untouched", not reg.DEFAULT_DB.exists() if not live_existed else True)
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
