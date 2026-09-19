#!/usr/bin/env python3
"""CAP-INTG-07 secrets/env separation. Empty is not proof. Not a live vault. No payment."""
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
os.environ.pop("WOLF_ALLOW_LIVE_INTG_SECRETS", None)

from core import intg_secrets_env as base  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "intg_secrets_env.py"
CR_ID = "CR-273f30371bd52c8a"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
KINDS = ["vault", "rotation", "beta-prod"]
POINTERS = ["env-example", "gitignore", "sacred-rule"]


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
    report = base.build_register()
    check("empty flag", report["empty"] is True and report["recorded_count"] == 0 and report["rows"] == [])
    check(
        "empty is not separation",
        report["empty_is_separation"] is False and report["separation_proved"] is False,
    )
    check("not a live vault", report["live_vault"] is False and report["vault"] is None and report["current"] is False)
    check("rotation unread", report["rotation"] is None and report["separation"] is None)
    check("payment unread", report["payment"] is None and report["money"] is None)
    check("edge not mutated", report["cloudflare_mutated"] is False and report["access_mutated"] is False)
    check("secret store quiet", report["secret_store_write"] is False and report["contents_read"] is False)
    check("not on disk", report["on_disk"] is False)
    check("bound", report["bound"] == "beta-integration-health-readonly")
    check("schema id", report["schema_id"] == base.SCHEMA_ID and report["schema"]["additionalProperties"] is False)
    check(
        "schema refuses writes",
        report["schema"]["writes_accepted"] is False
        and report["schema"]["payment_property"] is False
        and report["schema"]["vault_property"] is False
        and report["schema"]["rotation_property"] is False
        and report["schema"]["separation_property"] is False
        and report["schema"]["live_vault_property"] is False
        and report["schema"]["current_property"] is False
        and report["schema"]["secret_store_property"] is False
        and report["schema"]["cloudflare_property"] is False
        and report["schema"]["access_property"] is False
        and report["schema"]["pointer_is_proof"] is False
        and report["schema"]["kind_enum"] == KINDS,
    )
    check("skeleton label", report["framework_skeleton"] == "BUILT")
    check("ledger not written", report["ledger_write"] is False and report["cr_resolved"] is False)
    kinds = report["kinds"]
    check("three kinds", [row["kind"] for row in kinds] == KINDS)
    check(
        "every slot empty",
        all(
            row["slot"] == "empty"
            and row["evidence"] is None
            and row["vault"] is None
            and row["rotation"] is None
            and row["separation"] is None
            and row["live_vault"] is False
            and row["current"] is False
            and row["separation_proved"] is False
            and row["payment"] is None
            for row in kinds
        ),
    )
    pointers = report["pointers"]
    check("three pointers", [row["id"] for row in pointers] == POINTERS)
    check(
        "pointers are not proof",
        report["pointer_is_proof"] is False
        and report["checks_are_proof"] is False
        and all(
            row["role"] == "evidence_pointer"
            and row["proves_separation"] is False
            and row["live_vault"] is False
            and row["contents_read"] is False
            and isinstance(row["present"], bool)
            for row in pointers
        ),
    )
    blob = json.dumps(report)
    check("payload has no secret material", "sk-" not in blob and "BEGIN PRIVATE" not in blob)
    flags = report["honesty"]
    check("cap bound", flags["cap"] == "CAP-INTG-07" and flags["cr_id"] == CR_ID)
    check("ledger stays specified", flags["maturity"] == "SPECIFIED" and flags["ledger_maturity"] == "SPECIFIED")
    check("ceiling label built", flags["maturity_ceiling"] == "BUILT" and flags["slice_label"] == "BUILT")
    check(
        "not proven ready",
        flags["proven"] is False
        and flags["ready"] is False
        and flags["invented_proven"] is False
        and flags["invented_ready"] is False,
    )
    row = _cr_row()
    check("cr row present", row is not None)
    if row is not None:
        check("cr open", row[0] == "OPEN" and flags["cr_state"] == "OPEN" and flags["cr_resolved"] is False)
        check("cr blocker", row[1] == "NEEDS_ENGINEERING" and flags["cr_blocker"] == "NEEDS_ENGINEERING")
        check("cr capability", row[2] == "CAP-INTG-07" and flags["cr_capability"] == "CAP-INTG-07")
        check(
            "cr next action",
            row[3] == "Deterministic vault/rotation/separation prove for PROVEN; vault product for READY"
            and flags["cr_next_action"] == row[3],
        )
    check("gaps name the empty framework", "An empty framework is not proof of separation." in report["gaps"])
    check("gaps name the vault", "An empty framework is not a live vault." in report["gaps"])
    check("gaps name pointers", "Repo checks are evidence pointers only." in report["gaps"])
    check("live db absent", not base.DEFAULT_DB.exists())
    one = base.read_kind("vault")
    check(
        "vault slot read",
        one["ok"] is True
        and one["kind"]["kind"] == "vault"
        and one["empty"] is True
        and one["separation_proved"] is False
        and one["live_vault"] is False
        and one["vault"] is None
        and one["current"] is False,
    )
    try:
        base.read_kind("access")
        check("access is not a slot", False)
    except base.SecretsEnvError as exc:
        check("access is not a slot", exc.code == "not_found", exc.code)
    try:
        base.read_kind("current")
        check("current is not a slot", False)
    except base.SecretsEnvError as exc:
        check("current is not a slot", exc.code == "not_found", exc.code)
    try:
        base.read_kind("env-example")
        check("pointer is not a slot", False)
    except base.SecretsEnvError as exc:
        check("pointer is not a slot", exc.code == "not_found", exc.code)


def test_refuses(td: Path) -> None:
    money = td / "money.sqlite"
    money.write_bytes(b"sentinel-money")
    before = money.read_bytes()
    media_before = _media_count()
    try:
        base.refuse_store(money)
        check("money path refused", False)
    except base.SecretsEnvError as exc:
        check("money path refused", exc.code == "not_beta", exc.code)
    check("money sentinel unchanged", money.read_bytes() == before)
    try:
        base.refuse_store(CATALOG_DB)
        check("catalog path refused", False)
    except base.SecretsEnvError as exc:
        check("catalog path refused", exc.code == "catalog_refused", exc.code)
    check("media table count unchanged", _media_count() == media_before)
    try:
        base.refuse_store(td / "alchemist-register.sqlite")
        check("alchemist path refused", False)
    except base.SecretsEnvError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    check("alchemist file absent", not (td / "alchemist-register.sqlite").exists())
    try:
        base.refuse_store(td / "doppler-store.sqlite")
        check("secret store path refused", False)
    except base.SecretsEnvError as exc:
        check("secret store path refused", exc.code == "secret_store_refused", exc.code)
    check("secret store file absent", not (td / "doppler-store.sqlite").exists())
    dest = td / "register.sqlite"
    try:
        base.refuse_store(dest)
        check("store refused", False)
    except base.SecretsEnvError as exc:
        check("store refused", exc.code == "slots_refused", exc.code)
    check("store wrote nothing", not dest.exists())
    try:
        base.refuse_store(base.DEFAULT_DB)
        check("live guard", False)
    except base.SecretsEnvError as exc:
        check("live guard", exc.code == "live_guard", exc.code)
    check("live still absent after guard", not base.DEFAULT_DB.exists())
    try:
        base.refuse_fill({"kind": "rotation", "status": "NOTED"})
        check("fill refused", False)
    except base.SecretsEnvError as exc:
        check("fill refused", exc.code == "slots_refused", exc.code)
    try:
        base.refuse_payment({"payment": "1500000"})
        check("payment refused", False)
    except base.SecretsEnvError as exc:
        check("payment refused", exc.code == "payment_refused", exc.code)
    try:
        base.refuse_current({"current": True})
        check("current refused", False)
    except base.SecretsEnvError as exc:
        check("current refused", exc.code == "current_refused", exc.code)
    try:
        base.refuse_secret_store({})
        check("secret store refused", False)
    except base.SecretsEnvError as exc:
        check("secret store refused", exc.code == "secret_store_refused", exc.code)
    try:
        base.refuse_cloudflare({})
        check("cloudflare refused", False)
    except base.SecretsEnvError as exc:
        check("cloudflare refused", exc.code == "cloudflare_refused", exc.code)
    try:
        base.refuse_access({})
        check("access refused", False)
    except base.SecretsEnvError as exc:
        check("access refused", exc.code == "access_refused", exc.code)
    try:
        base.mark_current()
        check("current helper", False)
    except base.SecretsEnvError as exc:
        check("current helper", exc.code == "current_refused", exc.code)
    try:
        base.mark_live_vault()
        check("live vault helper", False)
    except base.SecretsEnvError as exc:
        check("live vault helper", exc.code == "current_refused", exc.code)
    try:
        base.mark_proven()
        check("prove helper", False)
    except base.SecretsEnvError as exc:
        check("prove helper", exc.code == "proven_refused", exc.code)
    try:
        base.resolve_cr()
        check("resolve helper", False)
    except base.SecretsEnvError as exc:
        check("resolve helper", exc.code == "resolve_refused", exc.code)
    try:
        base.refuse_external_write({"payment": 1})
        check("body payment refused", False)
    except base.SecretsEnvError as exc:
        check("body payment refused", exc.code == "payment_refused", exc.code)
    try:
        base.refuse_external_write({"vault": "live"})
        check("body vault refused", False)
    except base.SecretsEnvError as exc:
        check("body vault refused", exc.code == "current_refused", exc.code)
    try:
        base.refuse_external_write({"rotation": "90d"})
        check("body rotation refused", False)
    except base.SecretsEnvError as exc:
        check("body rotation refused", exc.code == "current_refused", exc.code)
    try:
        base.refuse_external_write({"secret": "not-a-real-value"})
        check("body secret refused", False)
    except base.SecretsEnvError as exc:
        check("body secret refused", exc.code == "secret_store_refused", exc.code)
    try:
        base.refuse_external_write({"cloudflare": "flip"})
        check("body cloudflare refused", False)
    except base.SecretsEnvError as exc:
        check("body cloudflare refused", exc.code == "cloudflare_refused", exc.code)
    try:
        base.refuse_external_write({"access": "mutate"})
        check("body access refused", False)
    except base.SecretsEnvError as exc:
        check("body access refused", exc.code == "access_refused", exc.code)
    try:
        base.guard_query(payment="1")
        check("query payment refused", False)
    except base.SecretsEnvError as exc:
        check("query payment refused", exc.code == "payment_refused", exc.code)
    try:
        base.guard_query(current="1")
        check("query current refused", False)
    except base.SecretsEnvError as exc:
        check("query current refused", exc.code == "current_refused", exc.code)
    try:
        base.guard_query(rotation="1")
        check("query rotation refused", False)
    except base.SecretsEnvError as exc:
        check("query rotation refused", exc.code == "current_refused", exc.code)
    try:
        base.guard_query(secret="1")
        check("query secret refused", False)
    except base.SecretsEnvError as exc:
        check("query secret refused", exc.code == "secret_store_refused", exc.code)
    try:
        base.guard_query(cloudflare="1")
        check("query cloudflare refused", False)
    except base.SecretsEnvError as exc:
        check("query cloudflare refused", exc.code == "cloudflare_refused", exc.code)
    try:
        base.guard_query(access="1")
        check("query access refused", False)
    except base.SecretsEnvError as exc:
        check("query access refused", exc.code == "access_refused", exc.code)
    check("refuses created no live file", not base.DEFAULT_DB.exists())


def test_ledger_ceiling(td: Path) -> None:
    def write(state: str) -> Path:
        path = td / f"ledger-{state}.json"
        path.write_text(json.dumps({"CAP-INTG-07": [state, "note"]}), encoding="utf-8")
        return path

    specified = write("SPECIFIED")
    before = specified.read_bytes()
    flags = base.honesty_flags(specified, CATALOG_DB)
    check("specified ceiling", flags["maturity"] == "SPECIFIED" and flags["maturity_ceiling"] == "BUILT")
    check("specified file untouched", specified.read_bytes() == before)
    proven = write("PROVEN")
    proven_before = proven.read_bytes()
    flags = base.honesty_flags(proven, CATALOG_DB)
    check(
        "already proven stays",
        flags["maturity"] == "PROVEN" and flags["maturity_ceiling"] == "PROVEN" and flags["invented_proven"] is False,
    )
    check("proven file untouched", proven.read_bytes() == proven_before)
    ready = write("READY")
    ready_before = ready.read_bytes()
    flags = base.honesty_flags(ready, CATALOG_DB)
    check(
        "already ready stays",
        flags["maturity"] == "READY" and flags["maturity_ceiling"] == "READY" and flags["invented_ready"] is False,
    )
    check("ready file untouched", ready.read_bytes() == ready_before)
    green = write("GREEN")
    flags = base.honesty_flags(green, CATALOG_DB)
    check("green is unknown", flags["maturity"] == "UNKNOWN" and flags["maturity_ceiling"] == "BUILT")
    missing = base.honesty_flags(td / "missing-ledger.json", CATALOG_DB)
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
    check("module does not import cloudflare", "cloudflare" not in joined)
    check("module has no urllib", "urllib" not in joined and "requests" not in joined)
    check("module has no subprocess", "subprocess" not in joined)
    check("module does not bind 8787", "8787" not in src)
    check("module does not call cloudflare", "api.cloudflare.com" not in src)
    check("module does not json.dump(", "json.dump(" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)
    check("module does not update completion", "UPDATE wolf_completion" not in src and "INSERT INTO wolf_completion" not in src)
    check("module does not insert evidence", "INSERT INTO" not in src and "CREATE TABLE" not in src)
    check("module does not read dotenv values", "git ls-files" not in src and ".env\"" not in src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/intg/secrets" in serve)
    check("page route registered", "/intg-secrets" in serve)
    check("payment route refused", "/api/intg/secrets/payment" in serve)
    check("live vault route refused", "/api/intg/secrets/live-vault" in serve)
    check("rotation status route refused", "/api/intg/secrets/rotation-status" in serve)
    check("secret store route refused", "/api/intg/secrets/secret-store" in serve)
    check("cloudflare route refused", "/api/intg/secrets/cloudflare" in serve)
    check("access route refused", "/api/intg/secrets/access" in serve)
    check("prove route refused", "/api/intg/secrets/prove" in serve)
    check("resolve route refused", "/api/intg/secrets/resolve" in serve)
    check("fill route refused", "/api/intg/secrets/fill" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "intg-secrets.html").read_text(encoding="utf-8")
    check("page says not proof", "not proof of separation" in page and "not a live vault" in page.lower())
    check("page does not resolve", "does not resolve" in page and "CAP-INTG-07" in page)
    check("page does not mutate edge", "does not mutate Cloudflare" in page and "Access" in page)
    check("page says rotation", "Rotation is not current" in page)
    check("page says pointers", "evidence pointers only" in page)


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

        st, _anon = call("GET", "/api/intg/secrets", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/intg/secrets", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/intg/secrets", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner empty", owner.get("empty") is True and owner.get("recorded_count") == 0 and owner.get("rows") == [])
            check("owner not proof", owner.get("empty_is_separation") is False and owner.get("separation_proved") is False)
            check("owner vault unread", owner.get("live_vault") is False and owner.get("vault") is None and owner.get("current") is False)
            check("owner rotation unread", owner.get("rotation") is None and owner.get("separation") is None)
            check("owner payment null", owner.get("payment") is None and owner.get("money") is None)
            check("owner edge quiet", owner.get("cloudflare_mutated") is False and owner.get("access_mutated") is False)
            check("owner pointers not proof", owner.get("pointer_is_proof") is False and owner.get("contents_read") is False)
            check("owner no resolve", owner.get("cr_resolved") is False and owner.get("on_disk") is False)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner skeleton", owner.get("framework_skeleton") == "BUILT")
            flags = owner.get("honesty") or {}
            check("owner honesty", flags.get("cr_id") == CR_ID and flags.get("cr_state") == "OPEN")
            check("owner ceiling", flags.get("maturity") == "SPECIFIED" and flags.get("maturity_ceiling") == "BUILT")
            kinds = owner.get("kinds") or []
            check(
                "owner kinds empty",
                [row.get("kind") for row in kinds] == KINDS
                and all(
                    row.get("slot") == "empty"
                    and row.get("current") is False
                    and row.get("live_vault") is False
                    and row.get("vault") is None
                    and row.get("rotation") is None
                    and row.get("separation") is None
                    for row in kinds
                ),
            )
            pointers = owner.get("pointers") or []
            check(
                "owner pointers",
                [row.get("id") for row in pointers] == POINTERS
                and all(row.get("proves_separation") is False and row.get("contents_read") is False for row in pointers),
            )
        st, schema = call("GET", "/api/intg/secrets/schema", MATT)
        check(
            "owner schema 200",
            st == 200 and isinstance(schema, dict) and (schema.get("schema") or {}).get("schema_id") == base.SCHEMA_ID,
            str(st),
        )
        st, listed = call("GET", "/api/intg/secrets/register", MATT)
        check("owner register view 200", st == 200 and isinstance(listed, dict) and listed.get("recorded_count") == 0, str(st))
        st, kinds = call("GET", "/api/intg/secrets/kinds", MATT)
        check(
            "owner kinds 200",
            st == 200 and isinstance(kinds, dict) and kinds.get("empty_is_separation") is False,
            str(st),
        )
        st, pointed = call("GET", "/api/intg/secrets/pointers", MATT)
        check(
            "owner pointers 200",
            st == 200
            and isinstance(pointed, dict)
            and pointed.get("pointer_is_proof") is False
            and pointed.get("checks_are_proof") is False
            and pointed.get("contents_read") is False,
            str(st),
        )
        st, slot = call("GET", "/api/intg/secrets/rotation", MATT)
        check(
            "rotation slot 200",
            st == 200
            and isinstance(slot, dict)
            and (slot.get("kind") or {}).get("kind") == "rotation"
            and slot.get("separation_proved") is False
            and slot.get("current") is False,
            str(slot)[:180],
        )
        st, held = call("GET", "/api/intg/secrets/beta-prod", MATT)
        check(
            "beta-prod slot 200",
            st == 200
            and isinstance(held, dict)
            and (held.get("kind") or {}).get("kind") == "beta-prod"
            and held.get("separation") is None
            and held.get("live_vault") is False,
            str(held)[:180],
        )
        st, missing = call("GET", "/api/intg/secrets/no-such", MATT)
        check("unknown slot 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(st))
        st, page = call("GET", "/intg-secrets", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page, (bytes, bytearray))
            and b"not proof of separation" in page
            and b"not a live vault" in page.lower()
            and b"does not resolve" in page,
            str(st),
        )
        st, _page_anon = call("GET", "/intg-secrets", None)
        check("anon page 403", st == 403, str(st))
        st, paid = call("POST", "/api/intg/secrets/payment", MATT, {"payment": 100})
        check("payment POST 405", st == 405 and isinstance(paid, dict) and paid.get("error") == "payment_refused", str(paid)[:180])
        st, current = call("POST", "/api/intg/secrets/current", MATT, {})
        check("current POST 405", st == 405 and isinstance(current, dict) and current.get("error") == "current_refused", str(current)[:180])
        st, vault = call("POST", "/api/intg/secrets/live-vault", MATT, {})
        check("live-vault POST 405", st == 405 and isinstance(vault, dict) and vault.get("error") == "current_refused", str(vault)[:180])
        st, rotation = call("POST", "/api/intg/secrets/rotation-status", MATT, {})
        check(
            "rotation-status POST 405",
            st == 405 and isinstance(rotation, dict) and rotation.get("error") == "current_refused",
            str(rotation)[:180],
        )
        st, store = call("POST", "/api/intg/secrets/secret-store", MATT, {})
        check(
            "secret-store POST 405",
            st == 405 and isinstance(store, dict) and store.get("error") == "secret_store_refused",
            str(store)[:180],
        )
        st, cf = call("POST", "/api/intg/secrets/cloudflare", MATT, {})
        check("cloudflare POST 405", st == 405 and isinstance(cf, dict) and cf.get("error") == "cloudflare_refused", str(cf)[:180])
        st, access = call("POST", "/api/intg/secrets/access", MATT, {})
        check("access POST 405", st == 405 and isinstance(access, dict) and access.get("error") == "access_refused", str(access)[:180])
        st, proved = call("POST", "/api/intg/secrets/prove", MATT, {})
        check("prove POST 405", st == 405 and isinstance(proved, dict) and proved.get("error") == "proven_refused", str(proved)[:180])
        st, ready = call("POST", "/api/intg/secrets/ready", MATT, {})
        check("ready POST 405", st == 405 and isinstance(ready, dict) and ready.get("error") == "ready_refused", str(ready)[:180])
        st, resolve = call("POST", "/api/intg/secrets/resolve", MATT, {})
        check("resolve POST 405", st == 405 and isinstance(resolve, dict) and resolve.get("error") == "resolve_refused", str(resolve)[:180])
        st, prod = call("POST", "/api/intg/secrets/production", MATT, {})
        check("production POST 405", st == 405 and isinstance(prod, dict) and prod.get("error") == "production_refused", str(prod)[:180])
        st, fill = call("POST", "/api/intg/secrets/fill", MATT, {})
        check("fill POST 405", st == 405 and isinstance(fill, dict) and fill.get("error") == "slots_refused", str(fill)[:180])
        st, note = call("POST", "/api/intg/secrets/note", MATT, {"kind": "rotation", "status": "NOTED"})
        check("note POST 405", st == 405 and isinstance(note, dict) and note.get("error") == "slots_refused", str(note)[:180])
        st, bare = call("POST", "/api/intg/secrets", MATT, {})
        check("bare POST 405", st == 405 and isinstance(bare, dict) and bare.get("error") == "writes_refused", str(bare)[:180])
        st, put = call("PUT", "/api/intg/secrets", MATT, {})
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:180])
        st, patch = call("PATCH", "/api/intg/secrets", MATT, {})
        check("owner PATCH 405", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:180])
        st, qpay = call("GET", "/api/intg/secrets?payment=1", MATT)
        check("query payment http refused", st == 405 and isinstance(qpay, dict) and qpay.get("error") == "payment_refused", str(qpay)[:180])
        st, qcur = call("GET", "/api/intg/secrets?current=1", MATT)
        check("query current http refused", st == 405 and isinstance(qcur, dict) and qcur.get("error") == "current_refused", str(qcur)[:180])
        st, qsec = call("GET", "/api/intg/secrets?secret=1", MATT)
        check(
            "query secret http refused",
            st == 405 and isinstance(qsec, dict) and qsec.get("error") == "secret_store_refused" and "sk-" not in json.dumps(qsec),
            str(qsec)[:180],
        )
        st, qcf = call("GET", "/api/intg/secrets?cloudflare=1", MATT)
        check("query cloudflare http refused", st == 405 and isinstance(qcf, dict) and qcf.get("error") == "cloudflare_refused", str(qcf)[:180])
        st, again = call("GET", "/api/intg/secrets", MATT)
        check(
            "owner still empty",
            st == 200
            and isinstance(again, dict)
            and again.get("empty") is True
            and again.get("separation_proved") is False
            and again.get("live_vault") is False
            and again.get("vault") is None
            and again.get("rotation") is None
            and again.get("separation") is None
            and again.get("payment") is None
            and again.get("pointer_is_proof") is False,
            str(again)[:240],
        )
        check("http left no live file", not base.DEFAULT_DB.exists())
    finally:
        httpd.shutdown()


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="intg-secrets-env-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    credits_before = hashlib.sha256(CREDITS.read_bytes()).hexdigest()
    cr_before = _cr_row()
    resolved_before = _resolved_count()
    media_before = _media_count()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    live_existed = base.DEFAULT_DB.exists()
    try:
        test_empty_register()
        test_refuses(td)
        test_ledger_ceiling(td)
        test_source()
        test_api(td)
    finally:
        shutil.rmtree(td, ignore_errors=True)
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
    check(
        "live register still absent" if not live_existed else "live register untouched",
        (not base.DEFAULT_DB.exists()) if not live_existed else True,
    )
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
