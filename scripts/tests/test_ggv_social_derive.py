#!/usr/bin/env python3
"""CAP-GGV-05 social DERIVE views. Stored Metricool reads only. No invented metrics."""
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
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_GGV_SOCIAL_DB", None)
os.environ.pop("WOLF_ALCHEMIST_DB", None)

from core import ggv_social_derive as soc  # noqa: E402

PASS = 0
FAIL = 0

LEDGER_JSON = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
MODULE_PATH = SCRIPTS / "core" / "ggv_social_derive.py"
CR_ID = "CR-e20099e21930b9a6"
MATT = "mrwolf@wolfcommand.net"
STAFF = "haikalqilbari123@gmail.com"
OWNER = "PERS-MATT"
ROLE = "PERS-GGV-ROLE"
WIP = {
    "scripts/migrations/migrate_phase2_6_team_readiness.py": "a8e89d399bd33ec11135b8caaa002a0d18c70000b6a8972d46811d30a61c9881",
    "scripts/phase26_team.py": "7c3690afaea97d8fdb48422bf4cbc8e144c9ecfac45c24c19977e83d45088fe0",
    "scripts/skills/__init__.py": "edfb69ce6d8f92a88ee6bf6a8160d9926765843271961bba52a3754450c93105",
    "scripts/wolf_intelligence.py": "e1de6a248512bcdaf6e71c4db30dc80a229055c7707e682c73d9349acb9bc21b",
}

SCHEMA = """
CREATE TABLE brand_external_ids (
  id INTEGER PRIMARY KEY,
  brand_key TEXT NOT NULL,
  external_system TEXT NOT NULL,
  external_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE'
);
CREATE TABLE performance_records (
  id INTEGER PRIMARY KEY,
  brand_key TEXT NOT NULL,
  external_system TEXT NOT NULL DEFAULT 'metricool',
  external_profile_id TEXT NOT NULL,
  network TEXT NOT NULL,
  surface TEXT NOT NULL,
  external_post_id TEXT NOT NULL,
  published_at_utc TEXT,
  reach REAL,
  impressions REAL,
  views REAL,
  likes REAL,
  comments REAL,
  shares REAL,
  saves REAL,
  engagement REAL,
  engagement_rate_pct REAL,
  data_lane TEXT NOT NULL DEFAULT 'operational',
  dual_count_risk INTEGER NOT NULL DEFAULT 0
);
"""


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


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


def _seed(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(SCHEMA)
        conn.execute(
            """
            INSERT INTO brand_external_ids
              (brand_key, external_system, external_id, status)
            VALUES ('habitat', 'metricool', '6260634', 'ACTIVE')
            """
        )
        conn.execute(
            """
            INSERT INTO brand_external_ids
              (brand_key, external_system, external_id, status)
            VALUES ('ghost', 'metricool', '1', 'INACTIVE')
            """
        )
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        old = (datetime.now(timezone.utc) - timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = [
            ("habitat", "6260634", "instagram", "post", "p1", now, 10, 12, 8, 1, 0, 0, 0, 3, 1.5, "operational", 0),
            ("habitat", "6260634", "instagram", "post", "p2", now, None, 4, None, None, None, None, None, None, None, "operational", 0),
            ("habitat", "6260634", "instagram", "story", "s1", now, 20, 20, None, None, None, None, None, None, None, "operational", 0),
            ("habitat", "6260634", "instagram", "post", "old", old, 99, 99, 99, 9, 9, 9, 9, 9, 9, "operational", 0),
            ("habitat", "999", "instagram", "post", "wrong", now, 1000, 1000, 1000, 1000, 1, 1, 1, 1000, 50, "operational", 0),
            ("habitat", "6260634", "instagram", "post", "lane", now, 7, 7, 7, 1, 1, 1, 1, 7, 7, "learning", 0),
        ]
        conn.executemany(
            """
            INSERT INTO performance_records (
              brand_key, external_profile_id, network, surface, external_post_id,
              published_at_utc, reach, impressions, views, likes, comments, shares,
              saves, engagement, engagement_rate_pct, data_lane, dual_count_risk
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def _surface(view: dict, surface: str) -> dict:
    return view["by_network"]["instagram"]["by_surface"][surface]


def test_honesty_and_source() -> None:
    src = MODULE_PATH.read_text(encoding="utf-8")
    check("no urllib", "urllib" not in src and "import requests" not in src)
    check("no metricool client", "metricool_read_client" not in src and "sync_metricool" not in src)
    check("no performance insert", "INSERT INTO performance_records" not in src)
    check("no ads spend literal", "paid_ads_spend = 0" not in src and "or 0" not in src)
    flags = soc.honesty_flags()
    check("metricool not called", flags["metricool_called"] is False and flags["metricool_write"] is False)
    check("no invented metrics flag", flags["invented_metrics"] is False)
    check("ads spend null", flags["paid_ads_spend"] is None and flags["ads_spend_invented"] is False)
    check("no blended score", flags["blended_score"] is None and flags["surfaces_blended"] is False)
    check("ceiling BUILT", flags["maturity_ceiling"] == "BUILT", str(flags["maturity_ceiling"]))
    check("ledger BUILT", flags["ledger_maturity"] == "BUILT", str(flags["ledger_maturity"]))
    check("not proven flag", flags["proven"] is False and flags["invented_proven"] is False)
    check("CR bound", flags["cr_id"] == CR_ID and flags["cr_state"] == "OPEN")
    check("CR not resolved", flags["cr_resolved"] is False)
    check(
        "CR next is derive views",
        flags["cr_next_action"] == "Governed DERIVE views + PROVEN red-team",
        str(flags["cr_next_action"]),
    )
    for name, fn, code in (
        ("mark_proven raises", soc.mark_proven, "invented_proven"),
        ("resolve_cr raises", soc.resolve_cr, "cr_resolve_refused"),
        ("metricool write raises", soc.metricool_write, "metricool_write_refused"),
        ("paid ads raises", soc.paid_ads, "paid_ads_refused"),
        ("invent metrics raises", soc.invent_metrics, "invented_metrics"),
        ("write raises", soc.refuse_write, "read_only"),
    ):
        try:
            fn()
            check(name, False)
        except soc.SocialDeriveError as exc:
            check(name, exc.code == code, exc.code)
    higher = Path(tempfile.mkdtemp()) / "ledger.json"
    higher.write_text(json.dumps({"CAP-GGV-05": ["PROVEN", "fixture"]}), encoding="utf-8")
    high = soc.honesty_flags(higher)
    check("already PROVEN stays PROVEN", high["maturity_ceiling"] == "PROVEN" and high["proven"] is True)
    check("PROVEN fixture still no spend", high["paid_ads_spend"] is None and high["invented_metrics"] is False)
    live = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    check("live ledger still BUILT", live["CAP-GGV-05"][0] == "BUILT")
    ready = Path(tempfile.mkdtemp()) / "ready.json"
    ready.write_text(json.dumps({"CAP-GGV-05": ["READY", "fixture"]}), encoding="utf-8")
    high_ready = soc.honesty_flags(ready)
    check("already READY stays READY", high_ready["maturity_ceiling"] == "READY" and high_ready["ready"] is True)


def test_derive_rules(td: Path) -> None:
    db = td / "social.sqlite"
    try:
        soc.derive_view("habitat", person_id=None, catalog_db=db)
        check("anon derive denied", False)
    except soc.SocialDeriveError as exc:
        check("anon derive denied", exc.code == "denied")
    check("anon created no file", not db.exists())
    try:
        soc.derive_view("habitat", person_id=ROLE, role_allowed=False, catalog_db=db)
        check("staff without grant denied", False)
    except soc.SocialDeriveError as exc:
        check("staff without grant denied", exc.code == "denied")
    _seed(db)
    before = db.read_bytes()
    missing = soc.derive_view("notabrand", person_id=OWNER, catalog_db=db)
    check("unknown brand not authorised", missing["authorised"] is False and missing["available"] is False)
    check("unknown brand no network", missing["by_network"] == {} and missing["blended_score"] is None)
    check("unknown brand spend null", missing["paid_ads_spend"] is None and missing["invented_metrics"] is False)
    ghost = soc.derive_view("ghost", person_id=OWNER, catalog_db=db)
    check("inactive mapping not authorised", ghost["authorised"] is False and ghost["available"] is False)
    bare = soc.derive_view(None, person_id=OWNER, catalog_db=db)
    check("missing brand stays empty", bare["available"] is False and bare["brand_key"] is None)
    view = soc.derive_view("habitat", person_id=OWNER, catalog_db=db)
    check("owner gate", view["gate"] == "owner" and view["authorised"] is True and view["available"] is True)
    check("profile is mapped id", view["external_profile_id"] == "6260634")
    check("no metricool call", view["metricool_called"] is False and view["metricool_write"] is False)
    check("no blend", view["blended_score"] is None and view["surfaces_blended"] is False)
    check("no ads", view["paid_ads_spend"] is None and view["ads_spend_invented"] is False)
    post = _surface(view, "post")
    check("null reach excluded", post["n"] == 3 and post["metrics"]["reach"]["n"] == 2, str(post["metrics"]["reach"]))
    check("reach median is not zero-filled", post["metrics"]["reach"]["median"] == 54.5, str(post["metrics"]["reach"]))
    story = _surface(view, "story")
    check("story engagement missing not zero", story["metrics"]["engagement"]["n"] == 0 and story["metrics"]["engagement"]["median"] is None)
    check("story views missing not zero", story["metrics"]["views"]["median"] is None)
    check("reel omitted", "reel" in view["missing_surfaces"] and "reel" not in view["by_network"]["instagram"]["by_surface"])
    check("wrong profile excluded", view["row_count"] == 4, str(view["row_count"]))
    check("learning lane excluded", view["row_count"] == 4)
    window = soc.derive_view("habitat", person_id=OWNER, catalog_db=db, window_days=7)
    wpost = _surface(window, "post")
    check("window drops old row", window["window_applied"] is True and wpost["n"] == 2, str(wpost["n"]))
    check("window reach ignores null", wpost["metrics"]["reach"]["n"] == 1 and wpost["metrics"]["reach"]["median"] == 10)
    try:
        soc.derive_view("habitat", person_id=OWNER, catalog_db=db, window_days=0)
        check("bad window refused", False)
    except soc.SocialDeriveError as exc:
        check("bad window refused", exc.code == "invalid")
    try:
        soc.derive_view("Habitat!", person_id=OWNER, catalog_db=db)
        check("bad brand refused", False)
    except soc.SocialDeriveError as exc:
        check("bad brand refused", exc.code == "invalid_brand")
    staff = soc.derive_view("habitat", person_id=ROLE, role_allowed=True, catalog_db=db)
    check("staff with grant can read", staff["gate"] == "staff" and staff["available"] is True)
    check("read did not write fixture", db.read_bytes() == before)
    empty = td / "empty.sqlite"
    conn = sqlite3.connect(str(empty))
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO brand_external_ids (brand_key, external_system, external_id, status) VALUES ('habitat','metricool','6260634','ACTIVE')"
    )
    conn.commit()
    conn.close()
    none = soc.derive_view("habitat", person_id=OWNER, catalog_db=empty)
    check("authorised empty is not zero", none["authorised"] is True and none["available"] is False and none["by_network"] == {})
    check("empty note is honest", "not zero" in none["note"])
    try:
        soc.derive_view("habitat", person_id=OWNER, catalog_db=td / "alchemist" / "x.sqlite")
        check("alchemist path refused", False)
    except soc.SocialDeriveError as exc:
        check("alchemist path refused", exc.code == "alchemist_refused")
    try:
        soc.derive_view("habitat", person_id=OWNER, catalog_db=Path("/tmp/production/social.sqlite"))
        check("production path refused", False)
    except soc.SocialDeriveError as exc:
        check("production path refused", exc.code == "not_beta", exc.code)


def test_live_store_untouched() -> None:
    before = _count("SELECT COUNT(*) FROM performance_records")
    view = soc.derive_view("habitat", person_id=OWNER)
    after = _count("SELECT COUNT(*) FROM performance_records")
    check("live row count unchanged", before == after and before > 0, f"{before}->{after}")
    check("live habitat authorised", view["authorised"] is True and view["available"] is True, str(view.get("available")))
    check("live no write flags", view["metricool_write"] is False and view["invented_metrics"] is False)
    check("live no blend or spend", view["blended_score"] is None and view["paid_ads_spend"] is None)
    story = view["by_network"].get("instagram", {}).get("by_surface", {}).get("story")
    if story and story["metrics"]["engagement"]["n"] == 0:
        check("live story engagement not zero", story["metrics"]["engagement"]["median"] is None)
    else:
        check("live story engagement not zero", False, "expected stored stories without engagement")
    check("live reel not invented", "reel" in view["missing_surfaces"])
    check("clicks named missing", any("clicks" in item for item in view["missing_information"]))
    check("live CR still open on view", view["cr_state"] == "OPEN" and view["cr_resolved"] is False)
    check("live ceiling BUILT", view["maturity_ceiling"] == "BUILT")


def test_api(td: Path) -> None:
    path = td / "api-social.sqlite"
    _seed(path)
    os.environ["WOLF_GGV_SOCIAL_DB"] = str(path)
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

        st, _anon = call("GET", "/api/ggv/social?brand=habitat", None)
        check("anon GET 403", st == 403, str(st))
        st, _staff = call("GET", "/api/ggv/social?brand=habitat", STAFF)
        check("staff GET 403", st == 403, str(st))
        st, _page = call("GET", "/ggv-social", None)
        check("anon page 403", st == 403, str(st))
        st, page = call("GET", "/ggv-social", MATT)
        html = page.get("html", "").lower()
        check(
            "owner page 200",
            st == 200
            and "missing numbers stay missing" in html
            and "no metricool write" in html
            and "no paid ads spend" in html
            and "not blended" in html,
            str(page)[:220],
        )
        st, owner = call("GET", "/api/ggv/social?brand=habitat", MATT)
        check(
            "owner GET 200",
            st == 200
            and owner.get("available") is True
            and owner.get("blended_score") is None
            and owner.get("paid_ads_spend") is None
            and owner.get("metricool_write") is False
            and owner.get("invented_metrics") is False,
            str(owner)[:280],
        )
        post = owner["by_network"]["instagram"]["by_surface"]["post"]
        check("api null reach not zero", post["metrics"]["reach"]["n"] == 2 and post["n"] == 3)
        st, spend = call("POST", "/api/ggv/social/spend", None, {"spend": 50})
        check("anon spend 403", st == 403, str(spend)[:160])
        st, spend = call("POST", "/api/ggv/social/ads", MATT, {"budget": 20})
        check("owner ads 405", st == 405 and spend.get("error") == "paid_ads_refused", str(spend)[:220])
        st, write = call("POST", "/api/ggv/social/metricool", MATT, {"publish": True})
        check("owner metricool 405", st == 405 and write.get("error") == "metricool_write_refused", str(write)[:220])
        st, invented = call("POST", "/api/ggv/social", MATT, {"reach": 999, "followers": 10})
        check("invent metrics 405", st == 405 and invented.get("error") == "invented_metrics", str(invented)[:220])
        st, put = call("PUT", "/api/ggv/social", MATT, {"blended_score": 9})
        check("PUT read-only 405", st == 405 and put.get("error") == "read_only", str(put)[:200])
        st, patch = call("PATCH", "/api/ggv/social/derive", MATT, {"views": 1})
        check("PATCH read-only 405", st == 405 and patch.get("error") == "read_only", str(patch)[:200])
        check("fixture bytes after API", path.exists())
    finally:
        httpd.shutdown()
        os.environ.pop("WOLF_GGV_SOCIAL_DB", None)


def test_preserved() -> None:
    ledger_bytes = LEDGER_JSON.read_bytes()
    ledger = json.loads(ledger_bytes)
    row = ledger.get("CAP-GGV-05") or [""]
    check("CAP-GGV-05 stays BUILT", row[0] == "BUILT", str(row[:1]))
    check("CAP-GGV-05 not PROVEN", row[0] != "PROVEN")
    check("ledger row count 77", len(ledger) == 77, str(len(ledger)))
    check("ledger bytes unchanged", LEDGER_JSON.read_bytes() == ledger_bytes)
    cr = _cr_row()
    check("CR still OPEN", cr is not None and cr[0] == "OPEN", str(cr))
    check("CR has no resolution", cr is not None and not cr[1], str(cr))
    check("CR blocker unchanged", cr is not None and cr[2] == "NEEDS_ENGINEERING", str(cr))
    check(
        "CR next action unchanged",
        cr is not None and cr[3] == "Governed DERIVE views + PROVEN red-team",
        str(cr),
    )
    credits = (ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md").read_text(encoding="utf-8")
    check("credits SPECIFIED 0.05", "| SPECIFIED | 0.05 |" in credits)
    check("credits BUILT 0.25", "| BUILT | 0.25 |" in credits)
    check("credits PROVEN 0.80", "| PROVEN | 0.80 |" in credits)
    history = HISTORY.read_text(encoding="utf-8") if HISTORY.exists() else ""
    check("score history has no social derive event", "ggv-social" not in history and "CAP-GGV-05" not in history)
    mig = (SCRIPTS / "migrations" / "migrate_ggv_social_permissions.py").read_text(encoding="utf-8")
    check("migration does not grant roles", "INSERT INTO org_role_permissions" not in mig)
    grants = _count(
        """
        SELECT COUNT(*) FROM org_role_permissions
        WHERE permission_id = 'PERM-GGV-SOCIAL-READ'
        """
    )
    perms = _count(
        """
        SELECT COUNT(*) FROM org_permissions
        WHERE permission_id = 'PERM-GGV-SOCIAL-READ' AND status='ACTIVE'
        """
    )
    check("live role grants stay 0", grants == 0, str(grants))
    check("social permission code active", perms == 1, str(perms))
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
    check("beta social route", "/api/ggv/social" in serve)
    check("beta metricool refuse route", "/api/ggv/social/metricool" in serve)
    check("beta ads refuse route", "/api/ggv/social/ads" in serve)
    check("beta default port 8788", "DEFAULT_PORT = 8788" in serve)


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="ggv-social-"))
    try:
        test_honesty_and_source()
        test_derive_rules(td)
        test_live_store_untouched()
        test_api(td)
        test_preserved()
    finally:
        print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
