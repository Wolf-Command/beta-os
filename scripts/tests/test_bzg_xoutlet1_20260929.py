#!/usr/bin/env python3
"""BZG-XOUTLET-1 — cross-outlet foundations, outlet_id hooks, authority sample."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

import sys

sys.path.insert(0, str(ROOT / "scripts"))

from core import bzg_outlet_registry as outlets  # noqa: E402
from core import bzg_xoutlet_foundations as xout  # noqa: E402
from core import rbac  # noqa: E402
from core import scope as _scope  # noqa: E402
import serve_beta as sb  # noqa: E402

ZAYEN = "PERS-ZAYEN"
AMANDA = "PERS-AMANDA"
ZAYEN_EMAIL = "laluzayen@gmail.com"
AMANDA_EMAIL = "amanda@wolfcommand.net"
MATT_EMAIL = "mrwolf@wolfcommand.net"
HARI_EMAIL = "carolus.haryanto@gmail.com"

CATALOG = ROOT / "catalog" / "content_library.sqlite"
BZG_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium-bzg.sqlite")
FOUNDATIONS_DOC = ROOT / "state" / "finance-core-sprint" / "BZG-XOUTLET-FOUNDATIONS.json"
COMM_FLAGS = ROOT / "state" / "commissioning" / "LAST-HUMAN-COMM-LOOP-FINGERPRINT.json"
ARM = ROOT / "state" / "finance-core-sprint" / "BZG-XOUTLET-1-ARM.json"

PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"PASS {name}" + (f" · {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"FAIL {name}" + (f" · {detail}" if detail else ""))


def _http(method: str, url: str, email: str | None = None) -> tuple[int, bytes]:
    headers = {"Accept": "application/json"}
    if email:
        headers["X-Wolf-Subject"] = email
        headers["Cf-Access-Authenticated-User-Email"] = email
    req = Request(url, method=method, headers=headers)
    try:
        with urlopen(req, timeout=20) as resp:
            return resp.status, resp.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _start_beta() -> tuple[ThreadingHTTPServer, int]:
    port = _free_port()

    class H(sb.BetaHandler):
        pass

    H.directory = str(ROOT / "dashboards")
    httpd = ThreadingHTTPServer(("127.0.0.1", port), H)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    time.sleep(0.3)
    return httpd, port


def test_statuses_preserved() -> None:
    rows = outlets.list_outlets()
    by_id = {r["outlet_id"]: r for r in rows}
    check("registry still 7", len(rows) == 7)
    check("Uma OPEN", by_id.get("BZG-UMA", {}).get("status") == "OPEN")
    check(
        "Rainforest PRE-OPENING",
        by_id.get("BZG-RAIN", {}).get("status") == "PRE-OPENING",
    )
    check(
        "Pool Bar PRE-OPENING",
        by_id.get("OU-BZG-RAIN-POOL", {}).get("status") == "PRE-OPENING",
    )
    for oid in ("BZG-MERAH", "BZG-ROOF", "BZG-RS", "BZG-CAT"):
        check(f"{oid} not OPEN", by_id.get(oid, {}).get("status") != "OPEN")
    for r in rows:
        check(
            f"centres still null {r['outlet_id']}",
            r.get("cost_centre_id") is None and r.get("revenue_centre_id") is None,
        )


def test_cross_outlet_hooks() -> None:
    conn = xout.db_connect()
    try:
        hooks = {h["hook_id"]: h for h in xout.hook_status(conn)}
        for hid in ("vendors", "purchase_requests", "daily_close", "books_journal_lines"):
            check(f"hook present {hid}", hid in hooks)
            check(
                f"outlet_id nullable {hid}",
                hooks[hid].get("outlet_id_nullable") is True,
                str(hooks[hid]),
            )

        pr_cols = xout._table_cols(conn, "bzg_ops_purchase_requests")
        close_cols = xout._table_cols(conn, "venue_daily_closes")
        vendor_cols = xout._table_cols(conn, "bzg_shared_vendors")
        check("PR outlet_id col", "outlet_id" in pr_cols)
        check("close outlet_id col", "outlet_id" in close_cols)
        check("vendors table", "outlet_id" in vendor_cols)
        check("vendors empty OK", hooks["vendors"]["row_count"] == 0)
        check(
            "closes empty OK",
            hooks["daily_close"]["row_count"] == 0,
        )

        # Null outlet_id is valid (entity-shared).
        shared = xout.hierarchy_usable(None, conn=conn)
        check("shared hierarchy outlet null", shared["outlet_id"] is None)
        check("shared centres hooks", shared["centres_are_hooks"] is True)
        check("shared centres not populated", shared["centres_populated"] is False)

        uma = xout.hierarchy_usable("BZG-UMA", conn=conn)
        check("Uma hierarchy usable", uma["outlet_id"] == "BZG-UMA")
        check("Uma status OPEN via hierarchy", uma["status"] == "OPEN")
        check("Uma cost centre null", uma["cost_centre_id"] is None)

        rain = xout.hierarchy_usable("BZG-RAIN", conn=conn)
        check("Rain hierarchy PRE-OPENING", rain["status"] == "PRE-OPENING")

        pool = xout.hierarchy_usable("OU-BZG-RAIN-POOL", conn=conn)
        check("Pool hierarchy under Rain", pool.get("parent_outlet_id") == "BZG-RAIN")

        # Invalid outlet rejected
        try:
            xout.resolve_outlet_ref("NOT-A-REAL-OUTLET", conn=conn)
            check("invalid outlet rejected", False, "no exception")
        except xout.BzgXoutletError as exc:
            check("invalid outlet rejected", exc.http_status == 400, str(exc))

        # Example PRs may carry outlet_id when venue matched registry (no invent).
        pr_outlets = [
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT outlet_id FROM bzg_ops_purchase_requests "
                "WHERE outlet_id IS NOT NULL"
            ).fetchall()
        ]
        for oid in pr_outlets:
            check(
                f"PR outlet_id in registry {oid}",
                outlets.get_outlet(oid, conn=conn) is not None,
            )
    finally:
        conn.close()


def test_no_fake_pnl() -> None:
    panel = None
    conn = xout.db_connect()
    try:
        panel = xout.foundations_panel(conn)
    finally:
        conn.close()
    check("no multi-outlet pnl flag", panel.get("no_multi_outlet_pnl") is True)
    check("invented_pnl false", panel.get("invented_pnl") is False)
    check(
        "invented_multi_outlet_totals false",
        panel.get("invented_multi_outlet_totals") is False,
    )
    check("invented_allocations false", panel.get("invented_allocations") is False)
    check("ready false", panel.get("ready") is False)
    check("staff_ready false", panel.get("staff_ready") is False)
    check("human_commissioned false", panel.get("human_commissioned") is False)
    # Panel must not expose money totals
    blob = json.dumps(panel)
    for bad in ("pnl_total", "sales_total", "covers_total", "go_live_revenue"):
        check(f"no fake field {bad}", bad not in blob)


def test_hierarchy_scopes() -> None:
    ctx_fb = _scope.resolve_effective_scope_context("SCOPE-BZG-FB")
    covered = ctx_fb.get("structurally_covered") or {}
    check("SCOPE-BZG-FB covers ENT-BZG", "ENT-BZG" in (covered.get("entities") or []))
    c = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        brand_tgts = c.execute(
            "SELECT target_id FROM org_scope_targets "
            "WHERE scope_id='SCOPE-BZG-FB' AND target_type='brand'"
        ).fetchall()
        check("SCOPE-BZG-FB no brand hardcodes", len(brand_tgts) == 0)
    finally:
        c.close()
    ctx_uma = _scope.resolve_effective_scope_context("SCOPE-BZG-UMA")
    cu = ctx_uma.get("structurally_covered") or {}
    check("SCOPE-BZG-UMA Uma only spirit", "BZG-UMA" in (cu.get("outlets") or []))
    check("SCOPE-BZG-UMA excludes Rain", "BZG-RAIN" not in (cu.get("outlets") or []))


def test_zayen_amanda_isolation() -> None:
    c = rbac.db_connect()
    try:
        check(
            "Zayen BZG allow",
            rbac.can(ZAYEN, "atrium.board.read", {"entity_id": "ENT-BZG"}, conn=c)
            is True,
        )
        check(
            "Zayen AMG allow",
            rbac.can(ZAYEN, "atrium.board.read", {"entity_id": "ENT-AMG"}, conn=c)
            is True,
        )
        check(
            "Zayen GGV deny",
            rbac.can(ZAYEN, "finance.nota.read", {"entity_id": "ENT-GGV"}, conn=c)
            is False,
        )
        check(
            "Amanda GGV allow",
            rbac.can(AMANDA, "finance.nota.read", {"entity_id": "ENT-GGV"}, conn=c)
            is True,
        )
        check(
            "Amanda BZG deny",
            rbac.can(AMANDA, "atrium.board.read", {"entity_id": "ENT-BZG"}, conn=c)
            is False,
        )
    finally:
        c.close()


def test_bzg_books_outlet_hooks() -> None:
    if not BZG_DB.is_file():
        check("bzg books present", False)
        return
    conn = sqlite3.connect(f"file:{BZG_DB}?mode=ro", uri=True)
    try:
        jl = {r[1] for r in conn.execute("PRAGMA table_info(journal_lines)")}
        check("books journal outlet_id", "outlet_id" in jl)
        po = {r[1] for r in conn.execute("PRAGMA table_info(inventory_purchase_orders)")}
        check("books PO outlet_id", "outlet_id" in po)
        n_j = conn.execute("SELECT COUNT(*) FROM journal_headers").fetchone()[0]
        n_a = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        # FC-SHELL-2 may seed COA structure; journals must stay empty (no fake money).
        check("BZG books zero journals", n_j == 0, f"j={n_j} a={n_a}")
        check("BZG books COA present or empty OK", n_a >= 0, f"a={n_a}")
    finally:
        conn.close()


def test_docs_flags() -> None:
    check("foundations doc exists", FOUNDATIONS_DOC.is_file())
    if FOUNDATIONS_DOC.is_file():
        doc = json.loads(FOUNDATIONS_DOC.read_text(encoding="utf-8"))
        check("doc pack XOUTLET", doc.get("pack") == "BZG-XOUTLET-1")
        check("doc no fake pnl", doc.get("no_fake_multi_outlet_pnl") is True)
        check("doc staff_ready false", doc.get("staff_ready") is False)
        check(
            "doc human_commissioned false",
            doc.get("human_commissioned") is False,
        )
        check("owner addendum in doc", "Rebuild Completion" in (doc.get("owner_addendum") or ""))
    if ARM.is_file():
        arm = json.loads(ARM.read_text(encoding="utf-8"))
        check("arm cursor must not auto-start", arm.get("cursor_must_not_auto_start_next") is True)
        check("arm staff_ready false", arm.get("staff_ready") is False)
    check("honesty staff_ready false", xout.HONESTY["staff_ready"] is False)
    check(
        "honesty human_commissioned false",
        xout.HONESTY["human_commissioned"] is False,
    )
    if COMM_FLAGS.is_file():
        data = json.loads(COMM_FLAGS.read_text(encoding="utf-8"))
        check("fingerprint staff_ready false", data.get("staff_ready") is False)
        check(
            "fingerprint human_commissioned false",
            data.get("human_commissioned") is False,
        )


def test_http() -> None:
    httpd, port = _start_beta()
    base = f"http://127.0.0.1:{port}"
    try:
        st, body = _http("GET", f"{base}/api/bzg/outlets/overview", MATT_EMAIL)
        check("Matt overview 200", st == 200, f"status={st}")
        if st == 200:
            data = json.loads(body.decode())
            f = data.get("cross_outlet_foundations") or {}
            check("foundations panel present", bool(f.get("hooks")))
            check("foundations no ready claim", f.get("ready") is False)
            check("Uma OPEN flag", f.get("uma_open") is True)
            check("Rain PRE-OPENING flag", f.get("rainforest_pre_opening") is True)
            check("Pool PRE-OPENING flag", f.get("pool_bar_pre_opening") is True)
            check("no invented sales", data.get("invented_sales") is False)
            statuses = {o["outlet_id"]: o["status"] for o in data.get("outlets") or []}
            check("API Uma OPEN", statuses.get("BZG-UMA") == "OPEN")

        st, body = _http("GET", f"{base}/api/bzg/outlets/foundations", MATT_EMAIL)
        check("foundations endpoint 200", st == 200, f"status={st}")
        if st == 200:
            data = json.loads(body.decode())
            check("foundations ok", data.get("ok") is True)
            check("hierarchy usable", data.get("hierarchy_usable") is True)

        st, _ = _http("GET", f"{base}/bzg/outlets", HARI_EMAIL)
        check("Hariyanto page 200", st == 200, f"status={st}")

        st, body = _http("GET", f"{base}/api/bzg/outlets/overview", ZAYEN_EMAIL)
        check("Zayen outlets 200", st == 200, f"status={st}")

        st, body = _http("GET", f"{base}/api/bzg/outlets/overview", AMANDA_EMAIL)
        check("Amanda outlets deny", st == 403, f"status={st}")

        st, body = _http("GET", f"{base}/api/bzg/finance/overview", ZAYEN_EMAIL)
        check("Zayen BZG finance 200", st == 200, f"status={st}")

        st, body = _http("GET", f"{base}/api/bzg/finance/overview", AMANDA_EMAIL)
        check("Amanda BZG finance deny", st == 403, f"status={st}")
    finally:
        httpd.shutdown()


def main() -> int:
    test_statuses_preserved()
    test_cross_outlet_hooks()
    test_no_fake_pnl()
    test_hierarchy_scopes()
    test_zayen_amanda_isolation()
    test_bzg_books_outlet_hooks()
    test_docs_flags()
    test_http()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
