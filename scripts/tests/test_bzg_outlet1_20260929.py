#!/usr/bin/env python3
"""BZG-OUTLET-1 — outlet registry statuses, hierarchy scopes, Pool Bar OU."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

import sys

sys.path.insert(0, str(ROOT / "scripts"))

from core import bzg_outlet_registry as outlets  # noqa: E402
from core import rbac  # noqa: E402
from core import scope as _scope  # noqa: E402
import serve_beta as sb  # noqa: E402

HARI = "PERS-HARIYANTO"
DEVI = "PERS-DEVI"
ZAYEN = "PERS-ZAYEN"
AMANDA = "PERS-AMANDA"
MATT = "PERS-MATT"
HARI_EMAIL = "carolus.haryanto@gmail.com"
DEVI_EMAIL = "deviputu236@gmail.com"
ZAYEN_EMAIL = "laluzayen@gmail.com"
AMANDA_EMAIL = "amanda@wolfcommand.net"
MATT_EMAIL = "mrwolf@wolfcommand.net"

CATALOG = ROOT / "catalog" / "content_library.sqlite"
ATRIUM_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")
OU_DOC = ROOT / "state" / "finance-core-sprint" / "BZG-OPERATING-UNITS.json"
REG_DOC = ROOT / "state" / "finance-core-sprint" / "BZG-OUTLET-REGISTRY.json"
COMM_FLAGS = ROOT / "state" / "commissioning" / "LAST-HUMAN-COMM-LOOP-FINGERPRINT.json"

ALLOWED = outlets.ALLOWED_STATUSES
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


def test_registry_seed() -> None:
    rows = outlets.list_outlets()
    by_id = {r["outlet_id"]: r for r in rows}
    check("registry has 7 outlets", len(rows) == 7, str(sorted(by_id)))
    check("Uma OPEN", by_id.get("BZG-UMA", {}).get("status") == "OPEN")
    check(
        "Rainforest PRE-OPENING",
        by_id.get("BZG-RAIN", {}).get("status") == "PRE-OPENING",
    )
    pool = by_id.get("OU-BZG-RAIN-POOL") or {}
    check("Pool Bar PRE-OPENING", pool.get("status") == "PRE-OPENING")
    check("Pool Bar under BZG-RAIN", pool.get("parent_outlet_id") == "BZG-RAIN")
    check("Pool Bar brand_id BZG-RAIN", pool.get("brand_id") == "BZG-RAIN")
    check(
        "Pool Bar is OPERATING_UNIT",
        pool.get("outlet_kind") == "OPERATING_UNIT",
    )
    check(
        "Pool Bar operating_unit_id",
        pool.get("operating_unit_id") == "OU-BZG-RAIN-POOL",
    )
    for oid in ("BZG-MERAH", "BZG-ROOF", "BZG-RS", "BZG-CAT"):
        check(
            f"{oid} not OPEN",
            by_id.get(oid, {}).get("status") != "OPEN",
            by_id.get(oid, {}).get("status"),
        )
    for r in rows:
        check(
            f"status allowed {r['outlet_id']}",
            r["status"] in ALLOWED,
            r["status"],
        )
        check(
            f"legal entity ENT-BZG {r['outlet_id']}",
            r["legal_entity_id"] == "ENT-BZG",
        )
        # No fake ops metrics columns invented as totals
        check(
            f"cost_centre nullable {r['outlet_id']}",
            r.get("cost_centre_id") is None,
        )
        check(
            f"revenue_centre nullable {r['outlet_id']}",
            r.get("revenue_centre_id") is None,
        )


def test_hierarchy_scopes() -> None:
    ctx_fb = _scope.resolve_effective_scope_context("SCOPE-BZG-FB")
    covered = ctx_fb.get("structurally_covered") or {}
    check("SCOPE-BZG-FB found", ctx_fb.get("found") is True)
    check("SCOPE-BZG-FB covers ENT-BZG", "ENT-BZG" in (covered.get("entities") or []))
    check(
        "SCOPE-BZG-FB covers BZG-UMA brand",
        "BZG-UMA" in (covered.get("brands") or []),
    )
    check(
        "SCOPE-BZG-FB covers Pool Bar outlet",
        "OU-BZG-RAIN-POOL" in (covered.get("outlets") or []),
        str(covered.get("outlets")),
    )
    check(
        "SCOPE-BZG-FB covers OU operating unit",
        "OU-BZG-RAIN-POOL" in (covered.get("operating_units") or []),
    )
    # No hardcoded brand targets on SCOPE-BZG-FB
    c = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        brand_tgts = c.execute(
            "SELECT target_id FROM org_scope_targets "
            "WHERE scope_id='SCOPE-BZG-FB' AND target_type='brand'"
        ).fetchall()
        check("SCOPE-BZG-FB no brand hardcodes", len(brand_tgts) == 0, str(brand_tgts))
    finally:
        c.close()

    ctx_uma = _scope.resolve_effective_scope_context("SCOPE-BZG-UMA")
    cu = ctx_uma.get("structurally_covered") or {}
    check("SCOPE-BZG-UMA covers BZG-UMA outlet", "BZG-UMA" in (cu.get("outlets") or []))
    check(
        "SCOPE-BZG-UMA excludes Rainforest outlet",
        "BZG-RAIN" not in (cu.get("outlets") or []),
        str(cu.get("outlets")),
    )
    check(
        "SCOPE-BZG-UMA excludes Pool Bar",
        "OU-BZG-RAIN-POOL" not in (cu.get("outlets") or []),
    )

    hari = {o["outlet_id"] for o in outlets.outlets_for_person(HARI)}
    check("Hariyanto covers Uma via hierarchy", "BZG-UMA" in hari)
    check("Hariyanto covers Rainforest via hierarchy", "BZG-RAIN" in hari)
    check("Hariyanto covers Pool Bar via hierarchy", "OU-BZG-RAIN-POOL" in hari)

    devi = {o["outlet_id"] for o in outlets.outlets_for_person(DEVI)}
    check("Devi covers Uma via hierarchy", "BZG-UMA" in devi)
    # Devi has SCOPE-BZG-FB (entity) + SCOPE-BZG-UMA — entity expands all
    check("Devi FB entity also covers Rainforest", "BZG-RAIN" in devi)

    hier = outlets.hierarchy_for_outlet("OU-BZG-RAIN-POOL")
    check(
        "hierarchy LEGAL→OUTLET→centres",
        bool(hier)
        and hier["legal_entity_id"] == "ENT-BZG"
        and hier["parent_outlet_id"] == "BZG-RAIN"
        and hier["cost_centre_id"] is None
        and hier["revenue_centre_id"] is None,
        str(hier),
    )


def test_finance_isolation_untouched() -> None:
    c = rbac.db_connect()
    try:
        check(
            "Zayen BZG board still allow",
            rbac.can(ZAYEN, "atrium.board.read", {"entity_id": "ENT-BZG"}, conn=c)
            is True,
        )
        check(
            "Zayen GGV still deny",
            rbac.can(ZAYEN, "finance.nota.read", {"entity_id": "ENT-GGV"}, conn=c)
            is False,
        )
        check(
            "Zayen AMG SoD approve still",
            rbac.can(ZAYEN, "atrium.journal.approve", {"entity_id": "ENT-AMG"}, conn=c)
            is True,
        )
        row = c.execute(
            "SELECT status, end_at FROM org_assignments WHERE assignment_id=?",
            ("ASG-ZAYEN-BZG-FC-1",),
        ).fetchone()
        check(
            "ASG-ZAYEN-BZG-FC-1 ACTIVE",
            bool(row) and row[0] == "ACTIVE" and row[1] is None,
        )
    finally:
        c.close()


def test_docs_and_sidecar() -> None:
    ou = json.loads(OU_DOC.read_text(encoding="utf-8"))
    units = ou.get("units") or []
    check("OU doc pack BZG-OUTLET-1", ou.get("pack") == "BZG-OUTLET-1")
    check(
        "OU doc Pool Bar PRE-OPENING",
        any(
            u.get("operating_unit_id") == "OU-BZG-RAIN-POOL"
            and u.get("status") == "PRE-OPENING"
            for u in units
        ),
        str(units),
    )
    reg = json.loads(REG_DOC.read_text(encoding="utf-8"))
    check("registry doc exists", reg.get("pack") == "BZG-OUTLET-1")
    check("registry doc 7 outlets", len(reg.get("outlets") or []) == 7)

    if ATRIUM_DB.is_file():
        ac = sqlite3.connect(f"file:{ATRIUM_DB}?mode=ro", uri=True)
        try:
            row = ac.execute(
                "SELECT status, parent_brand_id FROM operating_unit_registry "
                "WHERE operating_unit_id='OU-BZG-RAIN-POOL'"
            ).fetchone()
            check(
                "atrium OU PRE-OPENING under BZG-RAIN",
                bool(row) and row[0] == "PRE-OPENING" and row[1] == "BZG-RAIN",
                str(row),
            )
            cols = {r[1] for r in ac.execute("PRAGMA table_info(journal_lines)")}
            check("journal_lines.outlet_id present", "outlet_id" in cols)
            check(
                "journal_lines.operating_unit_id present",
                "operating_unit_id" in cols,
            )
        finally:
            ac.close()
    else:
        check("atrium db present", False, "missing")


def test_flags_false() -> None:
    check("honesty staff_ready false", outlets.HONESTY["staff_ready"] is False)
    check(
        "honesty human_commissioned false",
        outlets.HONESTY["human_commissioned"] is False,
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
        # Owner / Matt
        st, body = _http("GET", f"{base}/api/bzg/outlets/overview", MATT_EMAIL)
        check("Matt outlets 200", st == 200, f"status={st}")
        if st == 200:
            data = json.loads(body.decode())
            check("Matt sees outlets list", len(data.get("outlets") or []) == 7)
            check("no invented sales flag", data.get("invented_sales") is False)
            check("empty_ops_metrics", data.get("empty_ops_metrics") is True)
            statuses = {o["outlet_id"]: o["status"] for o in data["outlets"]}
            check("API Uma OPEN", statuses.get("BZG-UMA") == "OPEN")
            check(
                "API Rainforest non-OPEN",
                statuses.get("BZG-RAIN") == "PRE-OPENING",
            )
            check(
                "API Pool Bar non-OPEN",
                statuses.get("OU-BZG-RAIN-POOL") == "PRE-OPENING",
            )

        st, _ = _http("GET", f"{base}/bzg/outlets", HARI_EMAIL)
        check("Hariyanto page 200", st == 200, f"status={st}")

        st, _ = _http("GET", f"{base}/api/bzg/outlets/overview", DEVI_EMAIL)
        check("Devi API 200", st == 200, f"status={st}")

        st, body = _http("GET", f"{base}/api/bzg/outlets/overview", ZAYEN_EMAIL)
        check("Zayen outlets 200", st == 200, f"status={st}")

        st, body = _http("GET", f"{base}/api/bzg/outlets/overview", AMANDA_EMAIL)
        check("Amanda outlets deny", st == 403, f"status={st} body={body[:120]!r}")

        st, _ = _http("GET", f"{base}/bzg/outlets", AMANDA_EMAIL)
        check("Amanda page deny", st == 403, f"status={st}")
    finally:
        httpd.shutdown()


def main() -> int:
    test_registry_seed()
    test_hierarchy_scopes()
    test_finance_isolation_untouched()
    test_docs_and_sidecar()
    test_flags_false()
    test_http()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
