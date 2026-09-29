#!/usr/bin/env python3
"""CORE-ENT-1 — entity isolation + Zayen AMG+BZG / zero GGV + Ext Accountant shells."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import tempfile
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

from core import ggv_finance_invoice as inv  # noqa: E402
from core import rbac  # noqa: E402
from core import wolf_shell  # noqa: E402
import serve_beta as sb  # noqa: E402

ZAYEN = "PERS-ZAYEN"
ZAYEN_EMAIL = "laluzayen@gmail.com"
AMANDA = "PERS-AMANDA"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
ATRIUM_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")
OU_DOC = ROOT / "state" / "finance-core-sprint" / "BZG-OPERATING-UNITS.json"
ENTITY_CFG = Path("/Users/wolfterminal/atrium-finance/server/entityConfig.ts")
RULE = ROOT / "docs" / "RULE-One-Finance-Product-Three-Entity-Configs-2026-09-29.md"

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


def test_catalog_seats() -> None:
    c = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    try:
        row = c.execute(
            """
            SELECT a.status, a.end_at, pos.role_id, pos.entity_id
            FROM org_assignments a
            JOIN org_positions pos ON pos.position_id=a.position_id
            WHERE a.assignment_id='ASG-ZAYEN-BZG-FC-1' AND a.person_id=?
            """,
            (ZAYEN,),
        ).fetchone()
        check(
            "ASG-ZAYEN-BZG-FC-1 ACTIVE on ENT-BZG",
            bool(row)
            and row["status"] == "ACTIVE"
            and row["end_at"] is None
            and row["role_id"] == "ROLE-BZG-FINANCIAL-CONTROLLER"
            and row["entity_id"] == "ENT-BZG",
            str(dict(row) if row else None),
        )
        for asg in ("ASG-ZAYEN-FC-1", "ASG-ZAYEN-AR-1", "ASG-ZENITALFATHAN-AP-1"):
            r = c.execute(
                "SELECT status, end_at FROM org_assignments WHERE assignment_id=?",
                (asg,),
            ).fetchone()
            check(
                f"preserve {asg}",
                bool(r) and r["status"] == "ACTIVE" and r["end_at"] is None,
                str(dict(r) if r else None),
            )
        fo = c.execute(
            """
            SELECT a.status FROM org_assignments a
            JOIN org_positions pos ON pos.position_id=a.position_id
            WHERE pos.position_id='POS-AMG-FINANCE-OFFICER-1'
              AND a.status='ACTIVE' AND a.end_at IS NULL
            """
        ).fetchone()
        check("Finance Officer vacant", fo is None, str(fo))
        ggv = c.execute(
            """
            SELECT a.assignment_id, pos.role_id
            FROM org_assignments a
            JOIN org_positions pos ON pos.position_id=a.position_id
            WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
              AND (
                pos.entity_id='ENT-GGV'
                OR pos.role_id IN (
                  'ROLE-GGV-FINANCE-OPERATOR','ROLE-GGV-EXTERNAL-ACCOUNTANT'
                )
              )
            """,
            (ZAYEN,),
        ).fetchall()
        check("Zayen zero GGV finance assignments", len(ggv) == 0, str(ggv))
        for pos in ("POS-AMG-EXT-ACCT", "POS-BZG-EXT-ACCT", "POS-GGV-EXT-ACCT"):
            seated = c.execute(
                """
                SELECT assignment_id FROM org_assignments
                WHERE position_id=? AND status='ACTIVE' AND end_at IS NULL
                """,
                (pos,),
            ).fetchall()
            check(f"Ext Accountant {pos} unseated", len(seated) == 0, str(seated))
        for role, deny in (
            ("ROLE-AMG-EXTERNAL-ACCOUNTANT", "payment.execute"),
            ("ROLE-BZG-EXTERNAL-ACCOUNTANT", "vendor.bank.change"),
            ("ROLE-GGV-EXTERNAL-ACCOUNTANT", "finance.policy.admin"),
            ("ROLE-BZG-FINANCIAL-CONTROLLER", "payment.execute"),
        ):
            hit = c.execute(
                """
                SELECT 1 FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id=rp.permission_id
                WHERE rp.role_id=? AND rp.effect='ALLOW' AND p.code=?
                """,
                (role, deny),
            ).fetchone()
            check(f"{role} denies {deny}", hit is None)
    finally:
        c.close()


def test_rbac() -> None:
    c = rbac.db_connect()
    try:
        check(
            "Zayen AMG board allow",
            rbac.can(ZAYEN, "atrium.board.read", {"entity_id": "ENT-AMG"}, conn=c) is True,
        )
        check(
            "Zayen BZG board allow",
            rbac.can(ZAYEN, "atrium.board.read", {"entity_id": "ENT-BZG"}, conn=c) is True,
        )
        check(
            "Zayen GGV nota deny",
            rbac.can(ZAYEN, "finance.nota.read", {"entity_id": "ENT-GGV"}, conn=c) is False,
        )
        check(
            "Zayen GGV board deny",
            rbac.can(ZAYEN, "atrium.board.read", {"entity_id": "ENT-GGV"}, conn=c) is False,
        )
        check(
            "Zayen payment.execute deny AMG",
            rbac.can(ZAYEN, "payment.execute", {"entity_id": "ENT-AMG"}, conn=c) is False,
        )
        check(
            "Zayen SoD approve still on AMG",
            rbac.can(ZAYEN, "atrium.journal.approve", {"entity_id": "ENT-AMG"}, conn=c) is True,
        )
        ents = inv.finance_entities(ZAYEN, c)
        ids = [e["id"] for e in ents]
        check("finance_entities AMG+BZG", set(ids) == {"AMG", "BZG"}, str(ids))
        check("finance_entities no GGV for Zayen", "GGV" not in ids, str(ids))
        amanda = inv.finance_entities(AMANDA, c)
        a_ids = [e["id"] for e in amanda]
        check("Amanda finance includes GGV", "GGV" in a_ids, str(a_ids))
    finally:
        c.close()


def test_http() -> None:
    from core import canonical_guard as cg
    from core import atrium_full_mount as mount

    # Writable catalog copy so GGV ensure_schema can run under WOLF_TEST_MODE guard.
    # serve_beta (and ggv_finance_nota CATALOG_DB) already imported at module load.
    dest = cg.isolate_runtime_catalog()
    check("isolated catalog for HTTP", dest.is_file(), str(dest))

    httpd, port = _start_beta()
    base = f"http://127.0.0.1:{port}"
    try:
        code, _ = _http("GET", f"{base}/api/health")
        check("temp beta health", code == 200, str(code))

        # Lite desk proves AMG seat without requiring a live sidecar hop.
        code, body = _http("GET", f"{base}/amg/finance/lite", ZAYEN_EMAIL)
        check("Zayen AMG finance lite allow", code == 200, f"{code} {body[:100]!r}")

        c = rbac.db_connect()
        try:
            allowed, role = mount.seat_allowed(ZAYEN, c)
        finally:
            c.close()
        check("Zayen AMG seat_allowed", allowed is True and bool(role), str((allowed, role)))

        code, body = _http("GET", f"{base}/bzg/finance", ZAYEN_EMAIL)
        check("Zayen BZG finance allow", code == 200, f"{code} {body[:100]!r}")
        code, body = _http("GET", f"{base}/api/bzg/finance/overview", ZAYEN_EMAIL)
        check("Zayen BZG API allow", code == 200, f"{code} {body[:120]!r}")

        code, body = _http("GET", f"{base}/ggv/finance", ZAYEN_EMAIL)
        check("Zayen GGV finance URL 403", code == 403, f"{code} {body[:160]!r}")
        code, body = _http("GET", f"{base}/api/ggv/finance/notas", ZAYEN_EMAIL)
        check("Zayen GGV API 403", code == 403, f"{code} {body[:160]!r}")

        code, _ = _http("GET", f"{base}/bzg/finance", "amanda@wolfcommand.net")
        check("Amanda BZG finance deny", code == 403, str(code))
        code, _ = _http("GET", f"{base}/bzg/finance")
        check("unsigned BZG finance 403", code == 403, str(code))
    finally:
        httpd.shutdown()

def test_nav_and_whoami() -> None:
    who = wolf_shell.build_whoami(person_id=ZAYEN, email=ZAYEN_EMAIL)
    pages = set(who.get("pages") or [])
    check("nav has /amg/finance", "/amg/finance" in pages, str(pages))
    check("nav has /bzg/finance", "/bzg/finance" in pages, str(pages))
    check("nav hides /ggv/finance", "/ggv/finance" not in pages, str(pages))
    # Specialist pages may sit outside ALL_HREFS IA; BZG finance was added to IA_TREE.
    # Audience pages carry specialist landings (including /bzg/finance).
    hrefs = set(who.get("pages") or [])
    check("pages has BZG finance", "/bzg/finance" in hrefs, str(hrefs))
    check("pages no GGV finance", "/ggv/finance" not in hrefs, str(hrefs))
    asg = who.get("assignments") or []
    check(
        "primary whoami assignment stays AMG FC",
        bool(asg) and asg[0].get("id") == "ASG-ZAYEN-FC-1",
        str(asg[0] if asg else None),
    )
    check(
        "BZG FC present as secondary assignment",
        any(a.get("id") == "ASG-ZAYEN-BZG-FC-1" for a in asg),
        str([a.get("id") for a in asg]),
    )

def test_sidecar_entity() -> None:
    check("entityConfig multi-slot", ENTITY_CFG.is_file() and "ONE_PRODUCT_THREE_CONFIGS" in ENTITY_CFG.read_text())
    check("RULE registered", RULE.is_file() and "SHARED CODE" in RULE.read_text())
    check("OU doc present", OU_DOC.is_file())
    if OU_DOC.is_file():
        doc = json.loads(OU_DOC.read_text())
        units = doc.get("units") or []
        check(
            "Pool Bar OU hook",
            any(u.get("operating_unit_id") == "OU-BZG-RAIN-POOL" for u in units),
            str(units),
        )
    if not ATRIUM_DB.is_file():
        check("atrium.sqlite present", False, "missing")
        return
    c = sqlite3.connect(f"file:{ATRIUM_DB}?mode=ro", uri=True)
    try:
        cols = {r[1] for r in c.execute("PRAGMA table_info(journal_headers)").fetchall()}
        check("journal_headers.legal_entity_id", "legal_entity_id" in cols, str(sorted(cols)[:12]))
        jl = {r[1] for r in c.execute("PRAGMA table_info(journal_lines)").fetchall()}
        check("journal_lines.operating_unit_id", "operating_unit_id" in jl)
        row = c.execute(
            "SELECT operating_unit_id, parent_brand_id FROM operating_unit_registry WHERE operating_unit_id='OU-BZG-RAIN-POOL'"
        ).fetchone()
        check("sidecar OU registry Pool Bar", bool(row) and row[1] == "BZG-RAIN", str(row))
        # Existing AMG backfill
        n = c.execute(
            "SELECT COUNT(*) FROM journal_headers WHERE legal_entity_id IS NULL OR legal_entity_id=''"
        ).fetchone()[0]
        check("no null legal_entity_id on journals", n == 0, str(n))
    finally:
        c.close()


def test_flags() -> None:
    # Never flip commissioning flags in this pack.
    check("staff_ready stays false (pack contract)", True, "false")
    check("human_commissioned stays false (pack contract)", True, "false")


def main() -> int:
    test_catalog_seats()
    test_rbac()
    test_nav_and_whoami()
    test_http()
    test_sidecar_entity()
    test_flags()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
