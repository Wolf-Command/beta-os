#!/usr/bin/env python3
"""CAP-MSC-02 posture prove framework. Empty is not a prove. Not READY. No payment."""
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
os.environ.pop("WOLF_ALLOW_LIVE_MSC_POSTURE", None)

from core import msc_posture_prove as base  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG_DB = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "msc_posture_prove.py"
CR_ID = "CR-80296d7bc9c35452"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)
KINDS = ["posture", "control", "evidence"]


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


def test_empty_framework() -> None:
    report = base.build_framework()
    check("empty flag", report["empty"] is True and report["recorded_count"] == 0 and report["rows"] == [])
    check(
        "empty is not a prove",
        report["empty_is_prove"] is False and report["proved"] is False and report["empty_is_ready"] is False,
    )
    check("score unread", report["posture_score"] is None and report["current"] is False)
    check("control unread", report["control"] is None and report["evidence"] is None)
    check("payment unread", report["payment"] is None and report["money"] is None)
    check("edge not mutated", report["cloudflare_mutated"] is False and report["access_mutated"] is False)
    check("score unchanged", report["score_changed"] is False)
    check("not on disk", report["on_disk"] is False)
    check("schema id", report["schema_id"] == base.SCHEMA_ID and report["schema"]["additionalProperties"] is False)
    check(
        "schema refuses writes",
        report["schema"]["writes_accepted"] is False
        and report["schema"]["payment_property"] is False
        and report["schema"]["posture_score_property"] is False
        and report["schema"]["current_property"] is False
        and report["schema"]["control_property"] is False
        and report["schema"]["evidence_property"] is False
        and report["schema"]["cloudflare_property"] is False
        and report["schema"]["access_property"] is False
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
            and row["posture_score"] is None
            and row["control"] is None
            and row["current"] is False
            and row["proved"] is False
            and row["payment"] is None
            for row in kinds
        ),
    )
    flags = report["honesty"]
    check("cap bound", flags["cap"] == "CAP-MSC-02" and flags["cr_id"] == CR_ID)
    check("ledger stays built", flags["maturity"] == "BUILT" and flags["ledger_maturity"] == "BUILT")
    check("ceiling label built", flags["maturity_ceiling"] == "BUILT" and flags["slice_label"] == "BUILT")
    check(
        "not proven ready",
        flags["proven"] is False and flags["ready"] is False and flags["invented_proven"] is False and flags["invented_ready"] is False,
    )
    row = _cr_row()
    check("cr row present", row is not None)
    if row is not None:
        check("cr open", row[0] == "OPEN" and flags["cr_state"] == "OPEN" and flags["cr_resolved"] is False)
        check("cr blocker", row[1] == "NEEDS_ENGINEERING" and flags["cr_blocker"] == "NEEDS_ENGINEERING")
        check("cr capability", row[2] == "CAP-MSC-02" and flags["cr_capability"] == "CAP-MSC-02")
        check(
            "cr next action",
            row[3] == "CAP-bound automated posture prove as READY" and flags["cr_next_action"] == row[3],
        )
    check("gaps name the empty framework", "An empty framework is not a prove." in report["gaps"])
    check("gaps name not ready", "An empty framework is not READY." in report["gaps"])
    check("live db absent", not base.DEFAULT_DB.exists())
    one = base.read_kind("posture")
    check(
        "posture slot read",
        one["ok"] is True
        and one["kind"]["kind"] == "posture"
        and one["empty"] is True
        and one["proved"] is False
        and one["posture_score"] is None
        and one["current"] is False,
    )
    try:
        base.read_kind("ready")
        check("ready is not a slot", False)
    except base.PostureProveError as exc:
        check("ready is not a slot", exc.code == "not_found", exc.code)
    try:
        base.read_kind("score")
        check("score is not a slot", False)
    except base.PostureProveError as exc:
        check("score is not a slot", exc.code == "not_found", exc.code)


def test_refuses(td: Path) -> None:
    money = td / "money.sqlite"
    money.write_bytes(b"sentinel-money")
    before = money.read_bytes()
    media_before = _media_count()
    try:
        base.refuse_store(money)
        check("money path refused", False)
    except base.PostureProveError as exc:
        check("money path refused", exc.code == "not_beta", exc.code)
    check("money sentinel unchanged", money.read_bytes() == before)
    try:
        base.refuse_store(CATALOG_DB)
        check("catalog path refused", False)
    except base.PostureProveError as exc:
        check("catalog path refused", exc.code == "catalog_refused", exc.code)
    check("media table count unchanged", _media_count() == media_before)
    try:
        base.refuse_store(td / "alchemist-framework.sqlite")
        check("alchemist path refused", False)
    except base.PostureProveError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused", exc.code)
    check("alchemist file absent", not (td / "alchemist-framework.sqlite").exists())
    dest = td / "framework.sqlite"
    try:
        base.refuse_store(dest)
        check("store refused", False)
    except base.PostureProveError as exc:
        check("store refused", exc.code == "slots_refused", exc.code)
    check("store wrote nothing", not dest.exists())
    try:
        base.refuse_store(base.DEFAULT_DB)
        check("live guard", False)
    except base.PostureProveError as exc:
        check("live guard", exc.code == "live_guard", exc.code)
    check("live still absent after guard", not base.DEFAULT_DB.exists())
    try:
        base.refuse_fill({"kind": "posture", "status": "NOTED"})
        check("fill refused", False)
    except base.PostureProveError as exc:
        check("fill refused", exc.code == "slots_refused", exc.code)
    try:
        base.refuse_payment({"payment": "1500000"})
        check("payment refused", False)
    except base.PostureProveError as exc:
        check("payment refused", exc.code == "payment_refused", exc.code)
    try:
        base.refuse_score({"current": True})
        check("score refused", False)
    except base.PostureProveError as exc:
        check("score refused", exc.code == "score_refused", exc.code)
    try:
        base.refuse_cloudflare({})
        check("cloudflare refused", False)
    except base.PostureProveError as exc:
        check("cloudflare refused", exc.code == "cloudflare_refused", exc.code)
    try:
        base.refuse_access({})
        check("access refused", False)
    except base.PostureProveError as exc:
        check("access refused", exc.code == "access_refused", exc.code)
    try:
        base.mark_current()
        check("current helper", False)
    except base.PostureProveError as exc:
        check("current helper", exc.code == "score_refused", exc.code)
    try:
        base.mark_proven()
        check("prove helper", False)
    except base.PostureProveError as exc:
        check("prove helper", exc.code == "proven_refused", exc.code)
    try:
        base.resolve_cr()
        check("resolve helper", False)
    except base.PostureProveError as exc:
        check("resolve helper", exc.code == "resolve_refused", exc.code)
    try:
        base.refuse_external_write({"payment": 1})
        check("body payment refused", False)
    except base.PostureProveError as exc:
        check("body payment refused", exc.code == "payment_refused", exc.code)
    try:
        base.refuse_external_write({"posture_score": 80})
        check("body score refused", False)
    except base.PostureProveError as exc:
        check("body score refused", exc.code == "score_refused", exc.code)
    try:
        base.refuse_external_write({"cloudflare": "flip"})
        check("body cloudflare refused", False)
    except base.PostureProveError as exc:
        check("body cloudflare refused", exc.code == "cloudflare_refused", exc.code)
    try:
        base.refuse_external_write({"access": "mutate"})
        check("body access refused", False)
    except base.PostureProveError as exc:
        check("body access refused", exc.code == "access_refused", exc.code)
    try:
        base.refuse_external_write({"evidence": "filled"})
        check("body evidence refused", False)
    except base.PostureProveError as exc:
        check("body evidence refused", exc.code == "slots_refused", exc.code)
    try:
        base.guard_query(payment="1")
        check("query payment refused", False)
    except base.PostureProveError as exc:
        check("query payment refused", exc.code == "payment_refused", exc.code)
    try:
        base.guard_query(current="1")
        check("query current refused", False)
    except base.PostureProveError as exc:
        check("query current refused", exc.code == "score_refused", exc.code)
    try:
        base.guard_query(score="1")
        check("query score refused", False)
    except base.PostureProveError as exc:
        check("query score refused", exc.code == "score_refused", exc.code)
    try:
        base.guard_query(cloudflare="1")
        check("query cloudflare refused", False)
    except base.PostureProveError as exc:
        check("query cloudflare refused", exc.code == "cloudflare_refused", exc.code)
    try:
        base.guard_query(access="1")
        check("query access refused", False)
    except base.PostureProveError as exc:
        check("query access refused", exc.code == "access_refused", exc.code)
    check("refuses created no live file", not base.DEFAULT_DB.exists())


def test_ledger_ceiling(td: Path) -> None:
    def write(state: str) -> Path:
        path = td / f"ledger-{state}.json"
        path.write_text(json.dumps({"CAP-MSC-02": [state, "note"]}), encoding="utf-8")
        return path

    specified = write("SPECIFIED")
    before = specified.read_bytes()
    flags = base.honesty_flags(specified, CATALOG_DB)
    check("specified ceiling", flags["maturity"] == "SPECIFIED" and flags["maturity_ceiling"] == "BUILT")
    check("specified file untouched", specified.read_bytes() == before)
    built = write("BUILT")
    built_before = built.read_bytes()
    flags = base.honesty_flags(built, CATALOG_DB)
    check("built ceiling stays built", flags["maturity"] == "BUILT" and flags["maturity_ceiling"] == "BUILT")
    check("built file untouched", built.read_bytes() == built_before)
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
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("route registered", "/api/msc/posture" in serve)
    check("page route registered", "/msc-posture" in serve)
    check("payment route refused", "/api/msc/posture/payment" in serve)
    check("score route refused", "/api/msc/posture/score" in serve)
    check("current route refused", "/api/msc/posture/current" in serve)
    check("cloudflare route refused", "/api/msc/posture/cloudflare" in serve)
    check("access route refused", "/api/msc/posture/access" in serve)
    check("prove route refused", "/api/msc/posture/prove" in serve)
    check("ready route refused", "/api/msc/posture/ready" in serve)
    check("resolve route refused", "/api/msc/posture/resolve" in serve)
    check("fill route refused", "/api/msc/posture/fill" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    page = (ROOT / "dashboards" / "msc-posture.html").read_text(encoding="utf-8")
    check("page says not a prove", "not a prove" in page and "not READY" in page)
    check("page does not resolve", "does not resolve" in page and "CAP-MSC-02" in page)
    check("page does not mutate edge", "does not mutate Cloudflare" in page and "Access" in page)
    check("page says score not current", "A posture score is not current" in page)


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

        st, _anon = call("GET", "/api/msc/posture", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/msc/posture", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, owner = call("GET", "/api/msc/posture", MATT)
        check("owner GET 200", st == 200 and isinstance(owner, dict) and owner.get("ok") is True, str(owner)[:240])
        if isinstance(owner, dict):
            check("owner empty", owner.get("empty") is True and owner.get("recorded_count") == 0 and owner.get("rows") == [])
            check("owner not prove", owner.get("empty_is_prove") is False and owner.get("proved") is False and owner.get("empty_is_ready") is False)
            check("owner score unread", owner.get("posture_score") is None and owner.get("current") is False)
            check("owner slots unread", owner.get("control") is None and owner.get("evidence") is None)
            check("owner payment null", owner.get("payment") is None and owner.get("money") is None)
            check("owner edge quiet", owner.get("cloudflare_mutated") is False and owner.get("access_mutated") is False)
            check("owner no resolve", owner.get("cr_resolved") is False and owner.get("on_disk") is False)
            check("owner person", owner.get("person_id") == "PERS-MATT")
            check("owner skeleton", owner.get("framework_skeleton") == "BUILT")
            flags = owner.get("honesty") or {}
            check("owner honesty", flags.get("cr_id") == CR_ID and flags.get("cr_state") == "OPEN")
            check("owner ceiling", flags.get("maturity") == "BUILT" and flags.get("maturity_ceiling") == "BUILT")
            kinds = owner.get("kinds") or []
            check(
                "owner kinds empty",
                [row.get("kind") for row in kinds] == KINDS
                and all(
                    row.get("slot") == "empty"
                    and row.get("current") is False
                    and row.get("posture_score") is None
                    and row.get("proved") is False
                    for row in kinds
                ),
            )
        st, schema = call("GET", "/api/msc/posture/schema", MATT)
        check(
            "owner schema 200",
            st == 200 and isinstance(schema, dict) and (schema.get("schema") or {}).get("schema_id") == base.SCHEMA_ID,
            str(st),
        )
        st, listed = call("GET", "/api/msc/posture/framework", MATT)
        check("owner framework view 200", st == 200 and isinstance(listed, dict) and listed.get("recorded_count") == 0, str(st))
        st, kinds = call("GET", "/api/msc/posture/kinds", MATT)
        check(
            "owner kinds 200",
            st == 200 and isinstance(kinds, dict) and kinds.get("empty_is_prove") is False,
            str(st),
        )
        st, slot = call("GET", "/api/msc/posture/control", MATT)
        check(
            "control slot 200",
            st == 200
            and isinstance(slot, dict)
            and (slot.get("kind") or {}).get("kind") == "control"
            and slot.get("proved") is False,
            str(slot)[:180],
        )
        st, evidence = call("GET", "/api/msc/posture/evidence", MATT)
        check(
            "evidence slot 200",
            st == 200
            and isinstance(evidence, dict)
            and (evidence.get("kind") or {}).get("kind") == "evidence"
            and evidence.get("current") is False,
            str(evidence)[:180],
        )
        st, missing = call("GET", "/api/msc/posture/no-such", MATT)
        check("unknown slot 404", st == 404 and isinstance(missing, dict) and missing.get("error") == "not_found", str(st))
        st, page = call("GET", "/msc-posture", MATT)
        check(
            "owner page 200",
            st == 200
            and isinstance(page, (bytes, bytearray))
            and b"not a prove" in page
            and b"not READY" in page
            and b"does not resolve" in page,
            str(st),
        )
        st, _page_anon = call("GET", "/msc-posture", None)
        check("anon page 403", st == 403, str(st))
        st, paid = call("POST", "/api/msc/posture/payment", MATT, {"payment": 100})
        check("payment POST 405", st == 405 and isinstance(paid, dict) and paid.get("error") == "payment_refused", str(paid)[:180])
        st, current = call("POST", "/api/msc/posture/current", MATT, {})
        check("current POST 405", st == 405 and isinstance(current, dict) and current.get("error") == "score_refused", str(current)[:180])
        st, score = call("POST", "/api/msc/posture/score", MATT, {})
        check("score POST 405", st == 405 and isinstance(score, dict) and score.get("error") == "score_refused", str(score)[:180])
        st, live = call("POST", "/api/msc/posture/live-score", MATT, {})
        check("live-score POST 405", st == 405 and isinstance(live, dict) and live.get("error") == "score_refused", str(live)[:180])
        st, cf = call("POST", "/api/msc/posture/cloudflare", MATT, {})
        check("cloudflare POST 405", st == 405 and isinstance(cf, dict) and cf.get("error") == "cloudflare_refused", str(cf)[:180])
        st, access = call("POST", "/api/msc/posture/access", MATT, {})
        check("access POST 405", st == 405 and isinstance(access, dict) and access.get("error") == "access_refused", str(access)[:180])
        st, proved = call("POST", "/api/msc/posture/prove", MATT, {})
        check("prove POST 405", st == 405 and isinstance(proved, dict) and proved.get("error") == "proven_refused", str(proved)[:180])
        st, ready = call("POST", "/api/msc/posture/ready", MATT, {})
        check("ready POST 405", st == 405 and isinstance(ready, dict) and ready.get("error") == "ready_refused", str(ready)[:180])
        st, resolve = call("POST", "/api/msc/posture/resolve", MATT, {})
        check("resolve POST 405", st == 405 and isinstance(resolve, dict) and resolve.get("error") == "resolve_refused", str(resolve)[:180])
        st, prod = call("POST", "/api/msc/posture/production", MATT, {})
        check("production POST 405", st == 405 and isinstance(prod, dict) and prod.get("error") == "production_refused", str(prod)[:180])
        st, fill = call("POST", "/api/msc/posture/fill", MATT, {})
        check("fill POST 405", st == 405 and isinstance(fill, dict) and fill.get("error") == "slots_refused", str(fill)[:180])
        st, note = call("POST", "/api/msc/posture/note", MATT, {"kind": "posture", "status": "NOTED"})
        check("note POST 405", st == 405 and isinstance(note, dict) and note.get("error") == "slots_refused", str(note)[:180])
        st, bare = call("POST", "/api/msc/posture", MATT, {})
        check("bare POST 405", st == 405 and isinstance(bare, dict) and bare.get("error") == "writes_refused", str(bare)[:180])
        st, put = call("PUT", "/api/msc/posture", MATT, {})
        check("owner PUT 405", st == 405 and isinstance(put, dict) and put.get("error") == "writes_refused", str(put)[:180])
        st, patch = call("PATCH", "/api/msc/posture", MATT, {})
        check("owner PATCH 405", st == 405 and isinstance(patch, dict) and patch.get("error") == "writes_refused", str(patch)[:180])
        st, anon_post = call("POST", "/api/msc/posture/prove", None, {})
        check("anon POST 403", st == 403, str(anon_post)[:180])
        st, qpay = call("GET", "/api/msc/posture?payment=1", MATT)
        check("query payment http refused", st == 405 and isinstance(qpay, dict) and qpay.get("error") == "payment_refused", str(qpay)[:180])
        st, qcur = call("GET", "/api/msc/posture?current=1", MATT)
        check("query current http refused", st == 405 and isinstance(qcur, dict) and qcur.get("error") == "score_refused", str(qcur)[:180])
        st, qcf = call("GET", "/api/msc/posture?cloudflare=1", MATT)
        check("query cloudflare http refused", st == 405 and isinstance(qcf, dict) and qcf.get("error") == "cloudflare_refused", str(qcf)[:180])
        st, again = call("GET", "/api/msc/posture", MATT)
        check(
            "owner still empty",
            st == 200
            and isinstance(again, dict)
            and again.get("empty") is True
            and again.get("proved") is False
            and again.get("posture_score") is None
            and again.get("control") is None
            and again.get("payment") is None,
            str(again)[:240],
        )
        check("http left no live file", not base.DEFAULT_DB.exists())
    finally:
        httpd.shutdown()


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="msc-posture-prove-"))
    ledger_before = LEDGER.read_bytes()
    history_before = HISTORY.read_bytes()
    credits_before = hashlib.sha256(CREDITS.read_bytes()).hexdigest()
    cr_before = _cr_row()
    resolved_before = _resolved_count()
    media_before = _media_count()
    wip_before = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in WIP}
    live_existed = base.DEFAULT_DB.exists()
    try:
        test_empty_framework()
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
        "live framework still absent" if not live_existed else "live framework untouched",
        (not base.DEFAULT_DB.exists()) if not live_existed else True,
    )
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
