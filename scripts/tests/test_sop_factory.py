#!/usr/bin/env python3
"""SOP Factory v1 (Beta). Draft is not live. CAP-CORE-11 not raised. Not PROVEN."""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
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
os.environ.pop("WOLF_ALLOW_LIVE_SOP_FACTORY", None)
os.environ.pop("WOLF_SOP_FACTORY_DB", None)

from core import sop_factory as sop  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "sop_factory.sqlite"
LEDGER_JSON = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "sop_factory.py"
CR_ID = "CR-c4ed4e3fa9f15a40"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
ROLE = "PERS-SOP-ROLE"

NOTE = "Shift note: tin count was skipped on the Uma close."
NOTE2 = "Second note: the tin count step was written down after the miss."
BODY = "Count the tin before the drawer is closed and record the number."
BODY2 = "Count the tin, then write the number on the close card before lockup."

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


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _tmp_dir() -> Path:
    td = ROOT / "catalog" / "backups" / f"tmp-sop-factory-{os.getpid()}"
    td.mkdir(parents=True, exist_ok=True)
    return td


def _db(td: Path) -> Path:
    return td / "sop_factory.sqlite"


def _draft(**overrides: object) -> dict:
    body: dict = {"title": "Tin count", "body": BODY, "evidence_note": NOTE}
    body.update(overrides)
    return body


def _expect_error(name: str, fn, code: str) -> None:
    try:
        fn()
    except sop.SopFactoryError as exc:
        check(name, exc.code == code, exc.code)
        return
    except Exception as exc:  # noqa: BLE001
        check(name, False, type(exc).__name__ + " " + str(exc))
        return
    check(name, False, "no error")


def _cr_row() -> tuple | None:
    conn = sqlite3.connect(str(CATALOG))
    try:
        return conn.execute(
            "SELECT state, resolution_evidence, blocker_class FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
    finally:
        conn.close()


def test_honesty_and_source() -> None:
    flags = sop.honesty_flags()
    check("honesty.cr_bound", flags.get("cr_id") == CR_ID and flags.get("cr_bound") is True)
    check("honesty.cr_present", flags.get("cr_present") is True)
    check("honesty.cr_open", flags.get("cr_state") == "OPEN", str(flags.get("cr_state")))
    check("honesty.cr_not_resolved", flags.get("cr_resolved") is False)
    check("honesty.cr_not_mutated", flags.get("cr_mutated") is False)
    check("honesty.cap", flags.get("cap") == "CAP-CORE-11")
    check("honesty.maturity_is_ledger", flags.get("maturity") == flags.get("ledger_maturity"))
    check("honesty.ledger_specified", flags.get("ledger_maturity") == "SPECIFIED", str(flags.get("ledger_maturity")))
    check("honesty.ceiling_built", flags.get("maturity_ceiling") == "BUILT")
    check("honesty.not_proven", flags.get("proven") is False)
    check("honesty.not_ready", flags.get("ready") is False)
    check("honesty.loop_present", flags.get("full_loop") is True)
    check("honesty.no_train", flags.get("train_staff") is False and flags.get("auto_train") is False)
    check("honesty.not_staff_ready", flags.get("staff_ready") is False)
    check("honesty.not_commissioned", flags.get("human_commissioned") is False)
    check("honesty.adoption_unset", flags.get("operating_adoption") is False)
    check("honesty.file_not_version", flags.get("file_rewrite_is_version") is False)
    check("honesty.not_live_without_approve", flags.get("live_without_approve") is False)
    check("honesty.no_model_c_write", flags.get("model_c_write") is False)
    check("honesty.no_maturity_raise", flags.get("model_c_maturity_raised") is False)
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
    check("module does not bind 8787", "8787" not in src)
    check("module does not json.dump", "json.dump" not in src)
    check("module does not write_text", ".write_text" not in src)
    check("module does not mark_resolved", "mark_resolved" not in src)


def test_schema_draft_approve(td: Path) -> None:
    path = _db(td)
    missing = td / "missing-sop.sqlite"
    empty = sop.list_sops(sop.OWNER_PERSON, db_path=missing)
    check("list missing does not create", not missing.exists())
    check("list missing count 0", empty.get("count") == 0)
    check("list missing honesty", (empty.get("honesty") or {}).get("proven") is False)

    _expect_error(
        "anon draft denied",
        lambda: sop.create_draft(_draft(), person_id=None, db_path=path),
        "denied",
    )
    _expect_error(
        "other person denied",
        lambda: sop.create_draft(_draft(), person_id="PERS-OTHER", db_path=path),
        "denied",
    )
    check("denied writes created no file", not path.exists())

    _expect_error(
        "empty evidence refused",
        lambda: sop.create_draft(_draft(evidence_note="   "), person_id=sop.OWNER_PERSON, db_path=path),
        "invalid",
    )
    _expect_error(
        "maturity-word note refused",
        lambda: sop.create_draft(
            _draft(evidence_note="PROVEN"),
            person_id=sop.OWNER_PERSON,
            db_path=path,
        ),
        "missing_evidence",
    )
    _expect_error(
        "client live field refused",
        lambda: sop.create_draft(
            {**_draft(), "live": True},
            person_id=sop.OWNER_PERSON,
            db_path=path,
        ),
        "refused_field",
    )
    check("refused writes created no file", not path.exists())

    rec = sop.create_draft(_draft(), person_id=sop.OWNER_PERSON, db_path=path)
    check("draft appended", rec.get("appended") is True and str(rec.get("sop_id", "")).startswith("SOP-"))
    check("draft is not live", rec.get("live") is False and rec.get("state") == "DRAFT")
    check("draft gate owner", rec.get("gate") == "owner")
    sop_id = rec["sop_id"]
    version_id = rec["version_id"]

    conn = sqlite3.connect(str(path))
    cols = [str(r[1]) for r in conn.execute("PRAGMA table_info(sop_versions)")]
    triggers = {
        str(r[0])
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    }
    conn.close()
    check("schema version columns", "evidence_note" in cols and "state" in cols, str(cols))
    check("schema no-update trigger", "trg_sop_versions_no_update" in triggers)
    check("schema no-delete trigger", "trg_sop_versions_no_delete" in triggers)
    check("schema approval no-update", "trg_sop_approvals_no_update" in triggers)

    listed = sop.list_sops(sop.OWNER_PERSON, db_path=path)
    check("list count 1", listed.get("count") == 1)
    row = (listed.get("sops") or [{}])[0]
    check("list draft not live", row.get("live") is False and row.get("live_version_id") is None)

    got = sop.read_sop(sop_id, sop.OWNER_PERSON, db_path=path)
    check("read one version", len(got.get("versions") or []) == 1)
    check("read not approved", (got.get("versions") or [{}])[0].get("approved") is False)
    check("read not live", got.get("live") is False)

    approved = sop.approve(
        {"version_id": version_id},
        person_id=sop.OWNER_PERSON,
        db_path=path,
    )
    check("approve appended", approved.get("appended") is True and str(approved.get("approval_id", "")).startswith("APR-"))
    check("approve makes live", approved.get("live") is True)
    check("approve does not rewrite version", approved.get("version_unchanged") is True)

    again = sop.list_sops(sop.OWNER_PERSON, db_path=path)
    live_row = (again.get("sops") or [{}])[0]
    check("list live after approve", live_row.get("live") is True and live_row.get("live_version_n") == 1)

    nxt = sop.append_version(
        {
            "sop_id": sop_id,
            "title": "Tin count v2",
            "body": BODY2,
            "evidence_note": NOTE2,
        },
        person_id=sop.OWNER_PERSON,
        db_path=path,
    )
    check("version 2 drafted", nxt.get("version_n") == 2 and nxt.get("live") is False)
    check("version 2 does not replace live", nxt.get("live_version_id") == version_id)

    read2 = sop.read_sop(sop_id, sop.OWNER_PERSON, db_path=path)
    versions = read2.get("versions") or []
    check("read keeps both versions", len(versions) == 2)
    check("v1 still live", versions[0].get("live") is True and versions[0].get("approved") is True)
    check("v2 not live", versions[1].get("live") is False and versions[1].get("state") == "DRAFT")

    _expect_error(
        "second approve refused",
        lambda: sop.approve(
            {"version_id": version_id},
            person_id=sop.OWNER_PERSON,
            db_path=path,
        ),
        "already_approved",
    )
    conn = sqlite3.connect(str(path))
    n_apr = conn.execute("SELECT COUNT(*) FROM sop_approvals").fetchone()[0]
    conn.close()
    check("still one approval", n_apr == 1, str(n_apr))

    role_path = td / "role.sqlite"
    role_draft = sop.create_draft(
        _draft(),
        person_id=ROLE,
        role_allowed=True,
        db_path=role_path,
    )
    check("role can draft", role_draft.get("gate") == "role" and role_draft.get("live") is False)
    role_ok = sop.approve(
        {"version_id": role_draft["version_id"]},
        person_id=ROLE,
        role_allowed=True,
        db_path=role_path,
    )
    check("role can approve", role_ok.get("gate") == "role" and role_ok.get("live") is True)
    _expect_error(
        "role flag without person still denied",
        lambda: sop.create_draft(_draft(), person_id=ROLE, role_allowed=False, db_path=td / "nope.sqlite"),
        "denied",
    )
    check("role deny created no file", not (td / "nope.sqlite").exists())


def test_append_only_and_refuse(td: Path) -> None:
    path = _db(td)
    rec = sop.create_draft(_draft(title="Lock"), person_id=sop.OWNER_PERSON, db_path=path)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            "UPDATE sop_versions SET title=? WHERE version_id=?",
            ("rewritten", rec["version_id"]),
        )
        conn.commit()
        check("update aborted", False, "update committed")
    except sqlite3.IntegrityError as exc:
        check("update aborted", "append-only" in str(exc), str(exc))
    try:
        conn.execute("DELETE FROM sop_versions WHERE version_id=?", (rec["version_id"],))
        conn.commit()
        check("delete aborted", False, "delete committed")
    except sqlite3.IntegrityError as exc:
        check("delete aborted", "append-only" in str(exc), str(exc))
    finally:
        conn.close()

    missing = td / "approve-missing.sqlite"
    _expect_error(
        "approve missing does not create",
        lambda: sop.approve(
            {"version_id": rec["version_id"]},
            person_id=sop.OWNER_PERSON,
            db_path=missing,
        ),
        "not_found",
    )
    check("approve missing created no file", not missing.exists())
    _expect_error(
        "version missing sop",
        lambda: sop.append_version(
            {
                "sop_id": "SOP-00000000-0000-4000-8000-000000000001",
                "title": "Nope",
                "body": BODY,
                "evidence_note": NOTE,
            },
            person_id=sop.OWNER_PERSON,
            db_path=missing,
        ),
        "not_found",
    )
    check("version missing created no file", not missing.exists())
    _expect_error(
        "alchemist path refused",
        lambda: sop.list_sops(
            sop.OWNER_PERSON,
            db_path=ROOT / "catalog" / "alchemist-sop.sqlite",
        ),
        "alchemist_refused",
    )


def test_preserved() -> None:
    ledger = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    row = ledger.get("CAP-CORE-11") or [""]
    check("CAP-CORE-11 stays SPECIFIED", row[0] == "SPECIFIED", str(row[:1]))
    check("CAP-CORE-11 not PROVEN", row[0] != "PROVEN")
    check("CAP-CORE-11 not READY", row[0] != "READY")
    check("ledger row count 77", len(ledger) == 77, str(len(ledger)))
    cr = _cr_row()
    check("CR still OPEN", cr is not None and cr[0] == "OPEN", str(cr))
    check("CR has no resolution", cr is not None and not cr[1], str(cr))
    check("CR blocker unchanged", cr is not None and cr[2] == "NEEDS_ENGINEERING", str(cr))
    credits = (ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md").read_text(encoding="utf-8")
    check("credits SPECIFIED 0.05", "| SPECIFIED | 0.05 |" in credits)
    check("credits BUILT 0.25", "| BUILT | 0.25 |" in credits)
    check("credits PROVEN 0.80", "| PROVEN | 0.80 |" in credits)
    history = HISTORY.read_text(encoding="utf-8") if HISTORY.exists() else ""
    check("score history has no sop event", "sop-factory" not in history and "CAP-CORE-11" not in history)
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
    check("beta draft route", "/api/sop/draft" in serve)
    check("beta approve route", "/api/sop/approve" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    check("live sop db not created by tests", not LIVE_DB.exists())


def test_api(td: Path) -> None:
    path = td / "api-sop.sqlite"
    os.environ["WOLF_SOP_FACTORY_DB"] = str(path)
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

        st, _anon = call("GET", "/api/sop", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/sop", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, _anon_post = call("POST", "/api/sop/draft", None, _draft())
        check("anon POST 403", st == 403, str(st))
        st, _staff_post = call("POST", "/api/sop/approve", STAFF, {"version_id": "VER-x"})
        check("staff POST 403", st == 403, str(st))
        check("denied API created no file", not path.exists())

        st, owner = call("GET", "/api/sop", MATT)
        check("owner GET 200", st == 200 and owner.get("ok") is True, str(owner)[:240])
        check("owner GET empty", owner.get("count") == 0)
        check("owner GET bound to CR", (owner.get("honesty") or {}).get("cr_id") == CR_ID)
        check("owner GET did not create file", not path.exists())

        st, bad = call("POST", "/api/sop/draft", MATT, {**_draft(), "live": True})
        check("owner live field 400", st == 400 and bad.get("error") == "refused_field", str(bad)[:240])
        check("bad field created no file", not path.exists())

        st, made = call("POST", "/api/sop/draft", MATT, _draft())
        check("owner draft 200", st == 200 and made.get("live") is False, str(made)[:240])
        check("owner draft file exists", path.exists())
        version_id = made.get("version_id")
        sop_id = made.get("sop_id")

        st, listed = call("GET", "/api/sop", MATT)
        check("owner list not live", st == 200 and listed.get("count") == 1)
        check(
            "owner list draft",
            ((listed.get("sops") or [{}])[0].get("live") is False),
        )

        st, ok = call("POST", "/api/sop/approve", MATT, {"version_id": version_id})
        check("owner approve 200", st == 200 and ok.get("live") is True, str(ok)[:240])
        st, one = call("GET", f"/api/sop/{sop_id}", MATT)
        check("owner read live", st == 200 and one.get("live") is True, str(one)[:240])
        check(
            "read version still DRAFT row",
            ((one.get("versions") or [{}])[0].get("state") == "DRAFT"),
        )
    finally:
        httpd.shutdown()
        os.environ.pop("WOLF_SOP_FACTORY_DB", None)


def main() -> None:
    td = _tmp_dir()
    try:
        test_honesty_and_source()
        test_schema_draft_approve(td)
        test_append_only_and_refuse(td)
        test_api(td)
        test_preserved()
    finally:
        print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
