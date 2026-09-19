#!/usr/bin/env python3
"""CAP-CRM-02 customer identity memory. Not a lead. Not a complete graph. Not PROVEN."""
from __future__ import annotations

import hashlib
import inspect
import json
import os
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
os.environ.pop("WOLF_ALLOW_LIVE_CRM_IDENTITY", None)
os.environ.pop("WOLF_CRM_IDENTITY_DB", None)
os.environ.pop("WOLF_ALCHEMIST_DB", None)

from core import crm_identity_memory as ident  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "crm_identity.sqlite"
LEDGER_JSON = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "crm_identity_memory.py"
CR_ID = "CR-820682ce791563fa"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
OWNER = "PERS-MATT"
ROLE = "PERS-CRM-ROLE"
WIP = {
    "scripts/migrations/migrate_phase2_6_team_readiness.py": "a8e89d399bd33ec11135b8caaa002a0d18c70000b6a8972d46811d30a61c9881",
    "scripts/phase26_team.py": "7c3690afaea97d8fdb48422bf4cbc8e144c9ecfac45c24c19977e83d45088fe0",
    "scripts/skills/__init__.py": "edfb69ce6d8f92a88ee6bf6a8160d9926765843271961bba52a3754450c93105",
    "scripts/wolf_intelligence.py": "e1de6a248512bcdaf6e71c4db30dc80a229055c7707e682c73d9349acb9bc21b",
}
PROV = "Owner recorded this on 2026-09-19 from a named guest."
EVID = "Front desk matched the passport name on 2026-09-19."


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _body(**extra: str) -> dict:
    row = {
        "display_name": "Ayu Sari",
        "entity_id": "GGV",
        "provenance": PROV,
    }
    row.update(extra)
    return row


def _note(customer_id: str, body: str = "Asked about a Sunday viewing.") -> dict:
    return {
        "customer_id": customer_id,
        "body": body,
        "provenance": PROV,
    }


def _cr_row() -> tuple | None:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        return conn.execute(
            """
            SELECT state, resolution_evidence, blocker_class, next_action
            FROM wolf_completion_items WHERE id=?
            """,
            (CR_ID,),
        ).fetchone()
    finally:
        conn.close()


def _count(sql: str) -> int:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        return int(conn.execute(sql).fetchone()[0])
    finally:
        conn.close()


def test_honesty_and_source() -> None:
    src = MODULE_PATH.read_text(encoding="utf-8")
    check("no lead insert", "INSERT INTO core_leads" not in src)
    check("no person insert", "INSERT INTO org_persons" not in src)
    check("no urllib", "urllib" not in src and "import requests" not in src)
    check("no lead_spine import", "import lead_spine" not in src)
    flags = ident.honesty_flags()
    check("graph not complete", flags["identity_graph_complete"] is False)
    check("not merged", flags["merged"] is False)
    check("no blast", flags["marketing_blast"] is False)
    check("distinct from lead", flags["distinct_from_lead"] is True)
    check("ceiling BUILT", flags["maturity_ceiling"] == "BUILT", str(flags["maturity_ceiling"]))
    check("ledger SPECIFIED", flags["ledger_maturity"] == "SPECIFIED", str(flags["ledger_maturity"]))
    check("not proven flag", flags["proven"] is False and flags["invented_proven"] is False)
    check("CR bound", flags["cr_id"] == CR_ID and flags["cr_state"] == "OPEN")
    check("CR not resolved", flags["cr_resolved"] is False)
    try:
        ident.mark_proven()
        check("mark_proven raises", False)
    except ident.CrmIdentityError as exc:
        check("mark_proven raises", exc.code == "invented_proven")
    try:
        ident.resolve_cr()
        check("resolve_cr raises", False)
    except ident.CrmIdentityError as exc:
        check("resolve_cr raises", exc.code == "cr_resolve_refused")
    try:
        ident.refuse_marketing({"blast": True})
        check("blast raises", False)
    except ident.CrmIdentityError as exc:
        check("blast raises", exc.code == "marketing_refused")
    higher = Path(tempfile.mkdtemp()) / "ledger.json"
    higher.write_text(json.dumps({"CAP-CRM-02": ["PROVEN", "fixture"]}), encoding="utf-8")
    high = ident.honesty_flags(higher)
    check("already PROVEN stays PROVEN", high["maturity_ceiling"] == "PROVEN" and high["proven"] is True)
    live = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    check("live ledger still SPECIFIED", live["CAP-CRM-02"][0] == "SPECIFIED")


def test_register_notes_rules(td: Path) -> None:
    db = td / "crm.sqlite"
    leads_before = _count("SELECT COUNT(*) FROM core_leads")
    persons_before = _count("SELECT COUNT(*) FROM org_persons")
    try:
        ident.register_customer(_body(), person_id=None, db_path=db)
        check("anon register denied", False)
    except ident.CrmIdentityError as exc:
        check("anon register denied", exc.code == "denied")
    check("anon created no file", not db.exists())
    try:
        ident.register_customer(_body(), person_id=ROLE, role_allowed=False, db_path=db)
        check("staff without grant denied", False)
    except ident.CrmIdentityError as exc:
        check("staff without grant denied", exc.code == "denied")
    try:
        ident.register_customer(_body(display_name="LEAD-abc"), person_id=OWNER, db_path=db)
        check("lead name refused", False)
    except ident.CrmIdentityError as exc:
        check("lead name refused", exc.code == "not_a_customer")
    try:
        ident.register_customer({**_body(), "lead_id": "LEAD-12345678"}, person_id=OWNER, db_path=db)
        check("lead_id field refused", False)
    except ident.CrmIdentityError as exc:
        check("lead_id field refused", exc.code == "refused_field")
    try:
        ident.register_customer({**_body(), "email": "a@b.co"}, person_id=OWNER, db_path=db)
        check("email field refused", False)
    except ident.CrmIdentityError as exc:
        check("email field refused", exc.code == "refused_field")
    try:
        ident.register_customer({**_body(), "proven": True}, person_id=OWNER, db_path=db)
        check("proven field refused", False)
    except ident.CrmIdentityError as exc:
        check("proven field refused", exc.code == "refused_field")
    try:
        ident.register_customer(_body(entity_id="HABITAT"), person_id=OWNER, db_path=db)
        check("unknown entity refused", False)
    except ident.CrmIdentityError as exc:
        check("unknown entity refused", exc.code == "invalid_entity")
    made = ident.register_customer(_body(), person_id=OWNER, db_path=db)
    check("owner register", made["is_lead"] is False and made["is_customer"] is True and made["identity_graph_complete"] is False)
    cid = made["customer_id"]
    check("customer id prefix", cid.startswith("CUST-") and not cid.startswith("LEAD-"))
    again = ident.register_customer(_body(), person_id=OWNER, db_path=db)
    check("same name is not a merge", again["customer_id"] != cid)
    staff = ident.register_customer(
        _body(display_name="Budi Hartono", entity_id="BZG"),
        person_id=ROLE,
        role_allowed=True,
        db_path=db,
    )
    check("staff with grant can register", staff["entity_id"] == "BZG" and staff["gate"] == "staff")
    try:
        ident.list_customers(ROLE, role_allowed=True, db_path=db)
        check("staff list needs entity", False)
    except ident.CrmIdentityError as exc:
        check("staff list needs entity", exc.code == "missing_scope")
    scoped = ident.list_customers(ROLE, role_allowed=True, entity="BZG", db_path=db)
    ids = {row["customer_id"] for row in scoped["customers"]}
    check("staff sees own entity", staff["customer_id"] in ids and cid not in ids, str(ids))
    check("staff list graph false", scoped["identity_graph_complete"] is False)
    owner_list = ident.list_customers(OWNER, db_path=db)
    check("owner sees all", owner_list["count"] == 3, str(owner_list["count"]))
    note = ident.append_note(_note(cid), person_id=OWNER, db_path=db)
    check("note appended", note["rewritten"] is False and note["note_id"].startswith("NOTE-"))
    corr = ident.append_note(
        {**_note(cid, "Corrected: asked about Monday, not Sunday."), "corrects_note_id": note["note_id"]},
        person_id=ROLE,
        role_allowed=True,
        db_path=db,
    )
    check("correction is a new row", corr["note_id"] != note["note_id"] and corr["corrects_note_id"] == note["note_id"])
    card = ident.read_customer(cid, OWNER, db_path=db)
    check("both notes remain", len(card["notes"]) == 2)
    by_id = {row["note_id"]: row for row in card["notes"]}
    check("old note superseded", by_id[note["note_id"]]["superseded"] is True)
    check("correction kept", by_id[corr["note_id"]]["superseded"] is False)
    check("read is not a lead", card["customer"]["is_lead"] is False and card["lead_is_customer"] is False)
    check("read graph false", card["identity_graph_complete"] is False)
    try:
        ident.read_customer("LEAD-12345678", OWNER, db_path=db)
        check("lead path is not a customer", False)
    except ident.CrmIdentityError as exc:
        check("lead path is not a customer", exc.code == "not_a_customer")
    conn = sqlite3.connect(str(db))
    try:
        try:
            conn.execute("UPDATE crm_memory_notes SET body='rewritten' WHERE note_id=?", (note["note_id"],))
            conn.commit()
            check("note update blocked", False)
        except sqlite3.IntegrityError as exc:
            check("note update blocked", "append-only" in str(exc))
        try:
            conn.execute("DELETE FROM crm_customers WHERE customer_id=?", (cid,))
            conn.commit()
            check("customer delete blocked", False)
        except sqlite3.IntegrityError as exc:
            check("customer delete blocked", "append-only" in str(exc))
    finally:
        conn.close()
    still = ident.read_customer(cid, OWNER, db_path=db)
    still_notes = {row["note_id"]: row for row in still["notes"]}
    check(
        "history survived",
        still_notes[note["note_id"]]["body"].startswith("Asked")
        and still["customer"]["display_name"] == "Ayu Sari",
    )
    check("leads unchanged", _count("SELECT COUNT(*) FROM core_leads") == leads_before)
    check("persons unchanged", _count("SELECT COUNT(*) FROM org_persons") == persons_before)


def test_merge_blast_paths(td: Path) -> None:
    db = td / "merge.sqlite"
    left = ident.register_customer(_body(display_name="Left Guest"), person_id=OWNER, db_path=db)
    right = ident.register_customer(_body(display_name="Right Guest", entity_id="AMG"), person_id=OWNER, db_path=db)
    try:
        ident.merge_people(
            {"left_customer_id": left["customer_id"], "right_customer_id": right["customer_id"]},
            person_id=OWNER,
            db_path=db,
        )
        check("merge without evidence refused", False)
    except ident.CrmIdentityError as exc:
        check("merge without evidence refused", exc.code == "merge_without_evidence")
    try:
        ident.merge_people(
            {
                "left_customer_id": left["customer_id"],
                "right_customer_id": right["customer_id"],
                "evidence_ref": EVID,
                "provenance": PROV,
            },
            person_id=ROLE,
            role_allowed=True,
            db_path=db,
        )
        check("staff merge denied", False)
    except ident.CrmIdentityError as exc:
        check("staff merge denied", exc.code == "denied")
    merged = ident.merge_people(
        {
            "left_customer_id": left["customer_id"],
            "right_customer_id": right["customer_id"],
            "evidence_ref": EVID,
            "provenance": PROV,
        },
        person_id=OWNER,
        db_path=db,
    )
    check("evidence does not merge", merged["merged"] is False and merged["merge_executed"] is False)
    check("candidate review", merged["status"] == "REVIEW_REQUIRED" and merged["verified"] is False)
    check("graph still incomplete", merged["identity_graph_complete"] is False)
    listed = ident.list_customers(OWNER, db_path=db)
    check("both people remain", listed["count"] == 2, str(listed["count"]))
    card = ident.read_customer(left["customer_id"], OWNER, db_path=db)
    check("candidate stored", len(card["link_candidates"]) == 1 and card["link_candidates"][0]["merged"] is False)
    lead_link = ident.propose_link(
        {
            "customer_id": left["customer_id"],
            "other_id": "LEAD-1234abcd",
            "other_kind": "LEAD",
            "evidence_ref": EVID,
            "provenance": PROV,
        },
        person_id=OWNER,
        db_path=db,
    )
    check("lead link is not a customer", lead_link["lead_is_customer"] is False and lead_link["other_kind"] == "LEAD")
    check("lead link unverified", lead_link["verified"] is False and lead_link["customers_unchanged"] is True)
    try:
        ident.propose_link(
            {
                "customer_id": left["customer_id"],
                "other_id": "LEAD-1234abcd",
                "other_kind": "LEAD",
                "evidence_ref": EVID,
                "provenance": PROV,
            },
            person_id=ROLE,
            role_allowed=True,
            db_path=db,
        )
        check("staff link denied", False)
    except ident.CrmIdentityError as exc:
        check("staff link denied", exc.code == "denied")
    try:
        ident.register_customer({**_body(), "blast": "all"}, person_id=OWNER, db_path=db)
        check("blast field refused", False)
    except ident.CrmIdentityError as exc:
        check("blast field refused", exc.code == "marketing_refused")
    try:
        ident.register_customer(_body(), person_id=OWNER, db_path=td / "alchemist" / "x.sqlite")
        check("alchemist path refused", False)
    except ident.CrmIdentityError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused")
    try:
        ident.register_customer(_body(), person_id=OWNER, db_path=Path("/tmp/production/crm.sqlite"))
        check("production path refused", False)
    except ident.CrmIdentityError as exc:
        check("production path refused", exc.code == "not_beta", exc.code)
    try:
        ident.register_customer(_body(), person_id=OWNER, db_path=LIVE_DB)
        check("live guard", False)
    except ident.CrmIdentityError as exc:
        check("live guard", exc.code == "live_guard")
    check("live db not created", not LIVE_DB.exists())


def test_api(td: Path) -> None:
    path = td / "api-crm.sqlite"
    os.environ["WOLF_CRM_IDENTITY_DB"] = str(path)
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
                    raw = resp.read()
                    if "application/json" in (resp.headers.get("Content-Type") or ""):
                        return resp.status, json.loads(raw.decode())
                    return resp.status, {"html": raw.decode()[:2500]}
            except HTTPError as exc:
                raw = exc.read().decode()
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = {"raw": raw[:300]}
                return exc.code, parsed

        st, _anon = call("GET", "/api/crm/identity", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/crm/identity", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, _page = call("GET", "/crm-identity", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/crm-identity", MATT)
        check("owner page 200", st == 200 and "not a complete identity graph" in page.get("html", "").lower(), str(page)[:180])
        st, _blast = call("POST", "/api/marketing/blast", MATT, {"audience": "all"})
        check("owner blast 405", st == 405 and _blast.get("error") == "marketing_refused", str(_blast)[:240])
        st, owner = call("GET", "/api/crm/identity", MATT)
        check("owner GET 200 empty", st == 200 and owner.get("count") == 0 and owner.get("identity_graph_complete") is False)
        check("owner GET no file", not path.exists())
        st, made = call("POST", "/api/crm/identity", MATT, _body())
        check("owner register 200", st == 200 and made.get("is_lead") is False, str(made)[:240])
        cid = made.get("customer_id")
        st, noted = call("POST", "/api/crm/identity/note", MATT, _note(cid))
        check("owner note 200", st == 200 and noted.get("rewritten") is False, str(noted)[:200])
        st, bad = call(
            "POST",
            "/api/crm/identity/merge",
            MATT,
            {"left_customer_id": cid, "right_customer_id": cid},
        )
        check("merge without evidence 400", st == 400 and bad.get("error") == "merge_without_evidence", str(bad)[:240])
        st, put = call("PUT", "/api/crm/identity", MATT, {"display_name": "rewritten"})
        check("PUT append-only 405", st == 405 and put.get("error") == "append_only", str(put)[:200])
        st, lead = call("GET", "/api/crm/identity/LEAD-12345678", MATT)
        check("lead GET 404", st == 404 and lead.get("error") == "not_a_customer", str(lead)[:200])
    finally:
        httpd.shutdown()
        os.environ.pop("WOLF_CRM_IDENTITY_DB", None)


def test_preserved() -> None:
    ledger_bytes = LEDGER_JSON.read_bytes()
    ledger = json.loads(ledger_bytes)
    row = ledger.get("CAP-CRM-02") or [""]
    check("CAP-CRM-02 stays SPECIFIED", row[0] == "SPECIFIED", str(row[:1]))
    check("CAP-CRM-02 not PROVEN", row[0] != "PROVEN")
    check("ledger row count 77", len(ledger) == 77, str(len(ledger)))
    check("ledger bytes unchanged", LEDGER_JSON.read_bytes() == ledger_bytes)
    cr = _cr_row()
    check("CR still OPEN", cr is not None and cr[0] == "OPEN", str(cr))
    check("CR has no resolution", cr is not None and not cr[1], str(cr))
    check("CR blocker unchanged", cr is not None and cr[2] == "NEEDS_ENGINEERING", str(cr))
    check("CR next action unchanged", cr is not None and cr[3] == "Identity graph", str(cr))
    resolved = _count("SELECT COUNT(*) FROM wolf_completion_items WHERE state='RESOLVED'")
    check("resolved count readable", isinstance(resolved, int))
    credits = (ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md").read_text(encoding="utf-8")
    check("credits SPECIFIED 0.05", "| SPECIFIED | 0.05 |" in credits)
    check("credits BUILT 0.25", "| BUILT | 0.25 |" in credits)
    check("credits PROVEN 0.80", "| PROVEN | 0.80 |" in credits)
    history = HISTORY.read_text(encoding="utf-8") if HISTORY.exists() else ""
    check("score history has no crm identity event", "crm-identity-memory" not in history and "CAP-CRM-02" not in history)
    mig = (SCRIPTS / "migrations" / "migrate_crm_identity_permissions.py").read_text(encoding="utf-8")
    check("migration does not grant roles", "INSERT INTO org_role_permissions" not in mig)
    grants = _count(
        """
        SELECT COUNT(*) FROM org_role_permissions
        WHERE permission_id IN (
          'PERM-CRM-IDENTITY-READ','PERM-CRM-IDENTITY-NOTE','PERM-CRM-IDENTITY-REGISTER'
        )
        """
    )
    perms = _count(
        """
        SELECT COUNT(*) FROM org_permissions
        WHERE permission_id IN (
          'PERM-CRM-IDENTITY-READ','PERM-CRM-IDENTITY-NOTE','PERM-CRM-IDENTITY-REGISTER'
        ) AND status='ACTIVE'
        """
    )
    check("live role grants stay 0", grants == 0, str(grants))
    check("identity permission codes active", perms == 3, str(perms))
    for rel, digest in WIP.items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        check(f"WIP digest {Path(rel).name}", got == digest, got)
    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    for path in WIP:
        check(f"WIP not staged {Path(path).name}", path not in staged, str(staged))
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("beta identity route", "/api/crm/identity" in serve)
    check("beta blast route", "/api/marketing/blast" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    check("live identity db not created by tests", not LIVE_DB.exists())


def main() -> None:
    td = Path(tempfile.mkdtemp(prefix="crm-identity-"))
    try:
        test_honesty_and_source()
        test_register_notes_rules(td)
        test_merge_blast_paths(td)
        test_api(td)
        test_preserved()
    finally:
        print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
