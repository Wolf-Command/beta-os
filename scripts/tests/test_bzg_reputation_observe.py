#!/usr/bin/env python3
"""CAP-BZG-07 reputation observe. No source, no invented 5-star, no scrape, no guest reply."""
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
os.environ.pop("WOLF_ALLOW_LIVE_BZG_REPUTATION", None)
os.environ.pop("WOLF_BZG_REPUTATION_DB", None)
os.environ.pop("WOLF_ALCHEMIST_DB", None)

from core import bzg_reputation_observe as rep  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "bzg_reputation.sqlite"
LEDGER_JSON = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "bzg_reputation_observe.py"
CR_ID = "CR-d1aacda59180eba7"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
OWNER = "PERS-MATT"
ROLE = "PERS-BZG-ROLE"
WIP = {
    "scripts/migrations/migrate_phase2_6_team_readiness.py": "a8e89d399bd33ec11135b8caaa002a0d18c70000b6a8972d46811d30a61c9881",
    "scripts/phase26_team.py": "7c3690afaea97d8fdb48422bf4cbc8e144c9ecfac45c24c19977e83d45088fe0",
    "scripts/skills/__init__.py": "edfb69ce6d8f92a88ee6bf6a8160d9926765843271961bba52a3754450c93105",
    "scripts/wolf_intelligence.py": "e1de6a248512bcdaf6e71c4db30dc80a229055c7707e682c73d9349acb9bc21b",
}
PROV = "Owner read a guest note already in hand on 2026-09-19."
SOURCE = "Uma Blu guest book page 14, 2026-09-19, held at the venue."


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _body(**extra: object) -> dict:
    row = {
        "venue_id": "UMA",
        "source_kind": "OWNER_RECORD",
        "source_ref": SOURCE,
        "provenance": PROV,
    }
    row.update(extra)
    return row


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
    check("no urllib", "urllib" not in src and "import requests" not in src)
    check("no httpx", "httpx" not in src and "BeautifulSoup" not in src)
    check("no selenium", "selenium" not in src and "playwright" not in src)
    check("no lead insert", "INSERT INTO core_leads" not in src)
    check("no default assignment five", "observed_rating = 5" not in src and "or 5" not in src)
    flags = rep.honesty_flags()
    check("source not connected", flags["source_connected"] is False)
    check("no configured sources", flags["configured_sources"] == [])
    check("summary rating null", flags["summary_rating"] is None)
    check("five star not invented", flags["five_star_invented"] is False)
    check("not scraped", flags["scraped"] is False)
    check("no auto reply", flags["auto_reply"] is False and flags["guest_reply_sent"] is False)
    check("does not solicit", flags["solicit_reviews"] is False)
    check("ceiling BUILT", flags["maturity_ceiling"] == "BUILT", str(flags["maturity_ceiling"]))
    check("ledger SPECIFIED", flags["ledger_maturity"] == "SPECIFIED", str(flags["ledger_maturity"]))
    check("not proven flag", flags["proven"] is False and flags["invented_proven"] is False)
    check("CR bound", flags["cr_id"] == CR_ID and flags["cr_state"] == "OPEN")
    check("CR not resolved", flags["cr_resolved"] is False)
    check("CR next is observe path", flags["cr_next_action"] == "Observe/ingest path", str(flags["cr_next_action"]))
    for name, fn, code in (
        ("mark_proven raises", rep.mark_proven, "invented_proven"),
        ("resolve_cr raises", rep.resolve_cr, "cr_resolve_refused"),
        ("invent_five_star raises", rep.invent_five_star, "invented_five_star"),
        ("scrape raises", rep.scrape, "scrape_refused"),
        ("reply raises", rep.reply_to_guest, "auto_reply_refused"),
        ("summary raises", rep.refuse_summary, "summary_refused"),
    ):
        try:
            fn()
            check(name, False)
        except rep.ReputationObserveError as exc:
            check(name, exc.code == code, exc.code)
    higher = Path(tempfile.mkdtemp()) / "ledger.json"
    higher.write_text(json.dumps({"CAP-BZG-07": ["PROVEN", "fixture"]}), encoding="utf-8")
    high = rep.honesty_flags(higher)
    check("already PROVEN stays PROVEN", high["maturity_ceiling"] == "PROVEN" and high["proven"] is True)
    check("PROVEN fixture still no summary", high["summary_rating"] is None and high["five_star_invented"] is False)
    live = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    check("live ledger still SPECIFIED", live["CAP-BZG-07"][0] == "SPECIFIED")
    ready = Path(tempfile.mkdtemp()) / "ready.json"
    ready.write_text(json.dumps({"CAP-BZG-07": ["READY", "fixture"]}), encoding="utf-8")
    high_ready = rep.honesty_flags(ready)
    check("already READY stays READY", high_ready["maturity_ceiling"] == "READY" and high_ready["ready"] is True)


def test_observe_rules(td: Path) -> None:
    db = td / "rep.sqlite"
    try:
        rep.record_observation(_body(), person_id=None, db_path=db)
        check("anon observe denied", False)
    except rep.ReputationObserveError as exc:
        check("anon observe denied", exc.code == "denied")
    check("anon created no file", not db.exists())
    try:
        rep.record_observation(_body(), person_id=ROLE, role_allowed=False, db_path=db)
        check("staff without grant denied", False)
    except rep.ReputationObserveError as exc:
        check("staff without grant denied", exc.code == "denied")
    try:
        rep.record_observation(_body(venue_id="HABITAT"), person_id=OWNER, db_path=db)
        check("unknown venue refused", False)
    except rep.ReputationObserveError as exc:
        check("unknown venue refused", exc.code == "invalid_venue")
    try:
        rep.record_observation({**_body(), "stars": 5}, person_id=OWNER, db_path=db)
        check("stars field refused", False)
    except rep.ReputationObserveError as exc:
        check("stars field refused", exc.code == "invented_five_star")
    try:
        rep.record_observation({**_body(), "rating": 5}, person_id=OWNER, db_path=db)
        check("rating field refused", False)
    except rep.ReputationObserveError as exc:
        check("rating field refused", exc.code == "invented_five_star")
    try:
        rep.record_observation({**_body(), "proven": True}, person_id=OWNER, db_path=db)
        check("proven field refused", False)
    except rep.ReputationObserveError as exc:
        check("proven field refused", exc.code == "refused_field")
    try:
        rep.record_observation(_body(source_kind="SCRAPE"), person_id=OWNER, db_path=db)
        check("scrape kind refused", False)
    except rep.ReputationObserveError as exc:
        check("scrape kind refused", exc.code == "scrape_refused")
    try:
        rep.record_observation({**_body(), "reply": "Thanks for visiting"}, person_id=OWNER, db_path=db)
        check("reply field refused", False)
    except rep.ReputationObserveError as exc:
        check("reply field refused", exc.code == "auto_reply_refused")
    try:
        bare = _body()
        del bare["source_ref"]
        rep.record_observation(bare, person_id=OWNER, db_path=db)
        check("missing source refused", False)
    except rep.ReputationObserveError as exc:
        check("missing source refused", exc.code == "no_source")
    check("missing source created no file", not db.exists())
    try:
        rep.record_observation(_body(source_ref="no-source"), person_id=OWNER, db_path=db)
        check("empty source token refused", False)
    except rep.ReputationObserveError as exc:
        check("empty source token refused", exc.code == "no_source")
    try:
        rep.list_observations(ROLE, role_allowed=True, db_path=db)
        check("staff list needs venue", False)
    except rep.ReputationObserveError as exc:
        check("staff list needs venue", exc.code == "missing_scope")
    empty = rep.list_observations(OWNER, db_path=db)
    check(
        "empty list is honest",
        empty["count"] == 0
        and empty["summary_rating"] is None
        and empty["five_star_invented"] is False
        and empty["source_connected"] is False
        and empty["empty_because"] == "no_source_connected",
        str(empty)[:240],
    )
    check("empty list created no file", not db.exists())
    made = rep.record_observation(_body(), person_id=OWNER, db_path=db)
    check("owner observe stores provenance", made["provenance_stored"] is True and made["scraped"] is False)
    check("omitted rating stays null", made["observed_rating"] is None and made["summary_rating"] is None)
    check("stored row not a five", made["observation"]["observed_rating"] is None)
    check("store does not connect a source", made["source_connected"] is False)
    oid = made["observation"]["observation_id"]
    check("observation id prefix", oid.startswith("OBS-"))
    rated = rep.record_observation(
        _body(
            venue_id="RAINFOREST",
            observed_rating=5,
            rating_scale="1-5",
            excerpt="Guest wrote that the fish was excellent.",
        ),
        person_id=OWNER,
        db_path=db,
    )
    check("explicit five is stored not summarised", rated["observed_rating"] == 5.0 and rated["summary_rating"] is None)
    check("explicit five is not invented", rated["five_star_invented"] is False and rated["rating_defaulted"] is False)
    listed = rep.list_observations(OWNER, db_path=db)
    check("list count 2", listed["count"] == 2, str(listed["count"]))
    check("list summary stays null", listed["summary_rating"] is None and listed["five_star_invented"] is False)
    check("list source still disconnected", listed["source_connected"] is False and listed["configured_sources"] == [])
    scoped = rep.list_observations(ROLE, role_allowed=True, venue="UMA", db_path=db)
    check("staff scoped list", scoped["count"] == 1 and scoped["observations"][0]["venue_id"] == "UMA")
    check("staff scoped rating null", scoped["observations"][0]["observed_rating"] is None)
    try:
        rep.record_observation(
            _body(observed_rating=5),
            person_id=OWNER,
            db_path=db,
        )
        check("five without scale refused", False)
    except rep.ReputationObserveError as exc:
        check("five without scale refused", exc.code == "invalid", exc.code)
    try:
        rep.record_observation(
            _body(source_ref="please scrape the google listing today"),
            person_id=OWNER,
            db_path=db,
        )
        check("scrape text refused", False)
    except rep.ReputationObserveError as exc:
        check("scrape text refused", exc.code == "scrape_refused")
    got = rep.read_observation(oid, OWNER, db_path=db)
    check("read stored row", got["observation"]["provenance"] == PROV and got["summary_rating"] is None)
    try:
        rep.read_observation("LEAD-12345678", OWNER, db_path=db)
        check("non observation id refused", False)
    except rep.ReputationObserveError as exc:
        check("non observation id refused", exc.code == "not_an_observation")
    conn = sqlite3.connect(str(db))
    try:
        try:
            conn.execute(
                "UPDATE bzg_reputation_observations SET excerpt='rewritten' WHERE observation_id=?",
                (oid,),
            )
            check("update refused", False)
        except sqlite3.IntegrityError:
            check("update refused", True)
        try:
            conn.execute(
                "DELETE FROM bzg_reputation_observations WHERE observation_id=?",
                (oid,),
            )
            check("delete refused", False)
        except sqlite3.IntegrityError:
            check("delete refused", True)
    finally:
        conn.close()
    try:
        rep.record_observation(_body(), person_id=OWNER, db_path=td / "alchemist" / "x.sqlite")
        check("alchemist path refused", False)
    except rep.ReputationObserveError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused")
    try:
        rep.record_observation(_body(), person_id=OWNER, db_path=Path("/tmp/production/rep.sqlite"))
        check("production path refused", False)
    except rep.ReputationObserveError as exc:
        check("production path refused", exc.code == "not_beta", exc.code)
    try:
        rep.record_observation(_body(), person_id=OWNER, db_path=LIVE_DB)
        check("live guard", False)
    except rep.ReputationObserveError as exc:
        check("live guard", exc.code == "live_guard")
    check("live db not created", not LIVE_DB.exists())
    half = rep.record_observation(
        _body(venue_id="MERAH", observed_rating=4.5, rating_scale="1-5"),
        person_id=ROLE,
        role_allowed=True,
        db_path=db,
    )
    check("staff with grant can observe", half["gate"] == "staff" and half["observed_rating"] == 4.5)
    try:
        rep.record_observation(
            _body(observed_rating=4.2, rating_scale="1-5"),
            person_id=OWNER,
            db_path=db,
        )
        check("odd step refused", False)
    except rep.ReputationObserveError as exc:
        check("odd step refused", exc.code == "invalid")


def test_api(td: Path) -> None:
    path = td / "api-rep.sqlite"
    os.environ["WOLF_BZG_REPUTATION_DB"] = str(path)
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

        st, _anon = call("GET", "/api/bzg/reputation", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/bzg/reputation", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, _page = call("GET", "/bzg-reputation", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/bzg-reputation", MATT)
        html = page.get("html", "").lower()
        check(
            "owner page 200",
            st == 200 and "does not solicit" in html and "no scrape" in html,
            str(page)[:180],
        )
        st, owner = call("GET", "/api/bzg/reputation", MATT)
        check(
            "owner GET 200 empty",
            st == 200
            and owner.get("count") == 0
            and owner.get("summary_rating") is None
            and owner.get("five_star_invented") is False
            and owner.get("source_connected") is False,
            str(owner)[:240],
        )
        check("owner GET no file", not path.exists())
        st, scrape = call("POST", "/api/bzg/reputation/scrape", None, {})
        check("anon scrape 403", st == 403, str(scrape)[:200])
        st, scrape = call("POST", "/api/bzg/reputation/scrape", MATT, {})
        check("owner scrape 405", st == 405 and scrape.get("error") == "scrape_refused", str(scrape)[:240])
        st, reply = call("POST", "/api/bzg/reputation/reply", MATT, {"reply": "Thanks"})
        check("owner reply 405", st == 405 and reply.get("error") == "auto_reply_refused", str(reply)[:240])
        st, summary = call("POST", "/api/bzg/reputation", MATT, {"stars": 5})
        check("owner summary 405", st == 405 and summary.get("error") == "summary_refused", str(summary)[:240])
        st, made = call("POST", "/api/bzg/reputation/observe", MATT, _body())
        check(
            "owner observe 200",
            st == 200 and made.get("observed_rating") is None and made.get("summary_rating") is None,
            str(made)[:240],
        )
        oid = (made.get("observation") or {}).get("observation_id")
        st, five = call(
            "POST",
            "/api/bzg/reputation/observe",
            MATT,
            {**_body(), "stars": 5},
        )
        check("observe stars 400", st == 400 and five.get("error") == "invented_five_star", str(five)[:240])
        st, put = call("PUT", "/api/bzg/reputation", MATT, {"summary_rating": 5})
        check("PUT append-only 405", st == 405 and put.get("error") == "append_only", str(put)[:200])
        st, missing = call("GET", f"/api/bzg/reputation/{oid}", MATT)
        check("read observation 200", st == 200 and missing.get("summary_rating") is None, str(missing)[:200])
        st, bad = call("GET", "/api/bzg/reputation/GOOGLE-123", MATT)
        check("fake id 404", st == 404 and bad.get("error") == "not_an_observation", str(bad)[:200])
        check("scrape created no extra claim", scrape.get("five_star_invented") is False)
    finally:
        httpd.shutdown()
        os.environ.pop("WOLF_BZG_REPUTATION_DB", None)


def test_preserved() -> None:
    ledger_bytes = LEDGER_JSON.read_bytes()
    ledger = json.loads(ledger_bytes)
    row = ledger.get("CAP-BZG-07") or [""]
    check("CAP-BZG-07 stays SPECIFIED", row[0] == "SPECIFIED", str(row[:1]))
    check("CAP-BZG-07 not PROVEN", row[0] != "PROVEN")
    check("ledger row count 77", len(ledger) == 77, str(len(ledger)))
    check("ledger bytes unchanged", LEDGER_JSON.read_bytes() == ledger_bytes)
    cr = _cr_row()
    check("CR still OPEN", cr is not None and cr[0] == "OPEN", str(cr))
    check("CR has no resolution", cr is not None and not cr[1], str(cr))
    check("CR blocker unchanged", cr is not None and cr[2] == "NEEDS_ENGINEERING", str(cr))
    check("CR next action unchanged", cr is not None and cr[3] == "Observe/ingest path", str(cr))
    credits = (ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md").read_text(encoding="utf-8")
    check("credits SPECIFIED 0.05", "| SPECIFIED | 0.05 |" in credits)
    check("credits BUILT 0.25", "| BUILT | 0.25 |" in credits)
    check("credits PROVEN 0.80", "| PROVEN | 0.80 |" in credits)
    history = HISTORY.read_text(encoding="utf-8") if HISTORY.exists() else ""
    check(
        "score history has no reputation event",
        "bzg-reputation" not in history and "CAP-BZG-07" not in history,
    )
    mig = (SCRIPTS / "migrations" / "migrate_bzg_reputation_permissions.py").read_text(encoding="utf-8")
    check("migration does not grant roles", "INSERT INTO org_role_permissions" not in mig)
    grants = _count(
        """
        SELECT COUNT(*) FROM org_role_permissions
        WHERE permission_id IN (
          'PERM-BZG-REPUTATION-READ','PERM-BZG-REPUTATION-OBSERVE'
        )
        """
    )
    perms = _count(
        """
        SELECT COUNT(*) FROM org_permissions
        WHERE permission_id IN (
          'PERM-BZG-REPUTATION-READ','PERM-BZG-REPUTATION-OBSERVE'
        ) AND status='ACTIVE'
        """
    )
    check("live role grants stay 0", grants == 0, str(grants))
    check("reputation permission codes active", perms == 2, str(perms))
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
    check("beta reputation route", "/api/bzg/reputation" in serve)
    check("beta scrape route", "/api/bzg/reputation/scrape" in serve)
    check("beta reply route", "/api/bzg/reputation/reply" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)
    check("live reputation db not created by tests", not LIVE_DB.exists())


def main() -> None:
    td = Path(tempfile.mkdtemp(prefix="bzg-reputation-"))
    try:
        test_honesty_and_source()
        test_observe_rules(td)
        test_api(td)
        test_preserved()
    finally:
        print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
