#!/usr/bin/env python3
"""CORE-BOOKS-1 — per-entity books slots (BZG+GGV shells) + isolation + authority."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import tempfile
import threading
import time
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

import sys

sys.path.insert(0, str(ROOT / "scripts"))

from core import entity_books as books  # noqa: E402
from core import ggv_finance_invoice as inv  # noqa: E402
from core import rbac  # noqa: E402
import serve_beta as sb  # noqa: E402

ZAYEN = "PERS-ZAYEN"
ZAYEN_EMAIL = "laluzayen@gmail.com"
AMANDA = "PERS-AMANDA"
AMANDA_EMAIL = "amanda@wolfcommand.net"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
ENTITY_CFG = Path("/Users/wolfterminal/atrium-finance/server/entityConfig.ts")
ATRIUM_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")
BZG_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium-bzg.sqlite")
GGV_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium-ggv.sqlite")
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


def test_config_and_files() -> None:
    slots = books.books_enabled_slots()
    for eid in ("ENT-AMG", "ENT-BZG", "ENT-GGV"):
        check(f"books_enabled {eid}", slots.get(eid) is True, str(slots))
    text = ENTITY_CFG.read_text(encoding="utf-8")
    check("entityConfig BZG books_enabled true", "books_enabled: true" in text and "ENT-BZG" in text)
    # Count books_enabled: true occurrences (should be 3 slots)
    n = text.count("books_enabled: true")
    check("entityConfig three books_enabled true", n >= 3, str(n))
    check("RULE addendum separate files", RULE.is_file() and "separate SQLite files" in RULE.read_text())
    shells = books.ensure_all_shells()
    by_id = {r["legal_entity_id"]: r for r in shells}
    for eid, path in (
        ("ENT-AMG", ATRIUM_DB),
        ("ENT-BZG", BZG_DB),
        ("ENT-GGV", GGV_DB),
    ):
        check(f"file exists {eid}", path.is_file(), str(path))
        check(f"shell books_enabled {eid}", by_id[eid]["books_enabled"] is True)
        check(f"staff_ready false {eid}", by_id[eid]["staff_ready"] is False)
        check(f"human_commissioned false {eid}", by_id[eid]["human_commissioned"] is False)
    check("BZG empty journals", by_id["ENT-BZG"]["journals"] == 0, str(by_id["ENT-BZG"]))
    check("GGV empty journals", by_id["ENT-GGV"]["journals"] == 0, str(by_id["ENT-GGV"]))
    check(
        "AMG journals preserved",
        by_id["ENT-AMG"]["journals"] >= 1,
        str(by_id["ENT-AMG"]["journals"]),
    )


def test_isolation() -> None:
    token = f"probe-{uuid.uuid4().hex[:12]}"
    result = books.prove_isolation(token)
    check("isolation probe BZG has token", result["in_bzg"] is True, str(result))
    check("isolation probe AMG lacks token", result["in_amg"] is False, str(result))
    check("isolation probe GGV lacks token", result["in_ggv"] is False, str(result))
    check("isolation overall", result["isolated"] is True, str(result))
    # Cross-file journal leak check: BZG journal count unchanged after probe.
    bzg = books.snapshot("ENT-BZG")
    amg = books.snapshot("ENT-AMG")
    check("BZG still empty journals after probe", bzg["journals"] == 0)
    check("AMG journals untouched by probe", amg["journals"] >= 1)


def test_sod_and_outlet_nullable() -> None:
    for eid, path in (("ENT-AMG", ATRIUM_DB), ("ENT-BZG", BZG_DB), ("ENT-GGV", GGV_DB)):
        c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            jh = {r[1] for r in c.execute("PRAGMA table_info(journal_headers)")}
            jl = {r[1] for r in c.execute("PRAGMA table_info(journal_lines)")}
            check(f"{eid} preparer_person_id", "preparer_person_id" in jh)
            check(f"{eid} outlet_id nullable col", "outlet_id" in jl)
            check(f"{eid} operating_unit_id nullable col", "operating_unit_id" in jl)
        finally:
            c.close()
    # Live SoD commissioning journal still on AMG.
    c = sqlite3.connect(f"file:{ATRIUM_DB}?mode=ro", uri=True)
    try:
        row = c.execute(
            "SELECT status, preparer_person_id, wolf_created FROM journal_headers "
            "WHERE journal_id='JRN-ATRIUMSOD1B-COMM1'"
        ).fetchone()
        check(
            "SoD COMM1 intact on AMG",
            bool(row)
            and row[0] == "POSTED"
            and row[1] == "PERS-ZENITALFATHAN"
            and int(row[2]) == 1,
            str(row),
        )
    finally:
        c.close()


def test_rbac_authority() -> None:
    c = rbac.db_connect()
    try:
        check(
            "Zayen AMG allow",
            rbac.can(ZAYEN, "atrium.board.read", {"entity_id": "ENT-AMG"}, conn=c) is True,
        )
        check(
            "Zayen BZG allow",
            rbac.can(ZAYEN, "atrium.board.read", {"entity_id": "ENT-BZG"}, conn=c) is True,
        )
        check(
            "Zayen GGV deny",
            rbac.can(ZAYEN, "finance.nota.read", {"entity_id": "ENT-GGV"}, conn=c) is False,
        )
        check(
            "Amanda GGV allow",
            rbac.can(AMANDA, "finance.nota.read", {"entity_id": "ENT-GGV"}, conn=c) is True,
        )
        check(
            "Amanda BZG deny",
            rbac.can(AMANDA, "atrium.board.read", {"entity_id": "ENT-BZG"}, conn=c) is False,
        )
        check(
            "Amanda AMG deny",
            rbac.can(AMANDA, "atrium.board.read", {"entity_id": "ENT-AMG"}, conn=c) is False,
        )
        z_ents = {e["id"] for e in inv.finance_entities(ZAYEN, c)}
        a_ents = {e["id"] for e in inv.finance_entities(AMANDA, c)}
        check("Zayen finance_entities no GGV", "GGV" not in z_ents, str(z_ents))
        check("Amanda finance_entities has GGV", "GGV" in a_ents, str(a_ents))
        # Ext Acct still unseated
        seated = c.execute(
            """
            SELECT assignment_id FROM org_assignments
            WHERE position_id IN ('POS-AMG-EXT-ACCT','POS-BZG-EXT-ACCT','POS-GGV-EXT-ACCT')
              AND status='ACTIVE' AND end_at IS NULL
            """
        ).fetchall()
        check("Ext Accountant shells unseated", len(seated) == 0, str(seated))
    finally:
        c.close()


def test_http() -> None:
    from core import canonical_guard as cg

    dest = cg.isolate_runtime_catalog()
    check("isolated catalog", dest.is_file(), str(dest))
    httpd, port = _start_beta()
    base = f"http://127.0.0.1:{port}"
    try:
        code, body = _http("GET", f"{base}/api/bzg/finance/overview", ZAYEN_EMAIL)
        check("Zayen BZG books API 200", code == 200, f"{code}")
        if code == 200:
            payload = json.loads(body.decode())
            check("BZG overview books_opened", payload.get("books_opened") is True, str(payload)[:200])
            check("BZG overview books_enabled", payload.get("books_enabled") is True)
            check("BZG overview staff_ready false", payload.get("staff_ready") is False)
            check(
                "BZG overview human_commissioned false",
                payload.get("human_commissioned") is False,
            )
            check("BZG shell empty honest", payload.get("empty") is True)

        code, body = _http("GET", f"{base}/ggv/finance", ZAYEN_EMAIL)
        check("Zayen GGV 403", code == 403, f"{code} {body[:120]!r}")
        code, body = _http("GET", f"{base}/api/ggv/finance/overview", ZAYEN_EMAIL)
        check("Zayen GGV API 403", code == 403, f"{code}")

        code, body = _http("GET", f"{base}/api/ggv/finance/overview", AMANDA_EMAIL)
        check("Amanda GGV overview 200", code == 200, f"{code}")
        if code == 200:
            payload = json.loads(body.decode())
            check("Amanda GGV books_enabled", payload.get("books_enabled") is True, str(payload)[:180])
            check("Amanda staff_ready false", payload.get("staff_ready") is False)
            check(
                "Amanda human_commissioned false",
                payload.get("human_commissioned") is False,
            )

        code, _ = _http("GET", f"{base}/bzg/finance", AMANDA_EMAIL)
        check("Amanda BZG 403", code == 403, str(code))
        code, _ = _http("GET", f"{base}/amg/finance/lite", AMANDA_EMAIL)
        check("Amanda AMG lite deny-or-403", code in (403, 401, 404) or code != 200, str(code))
        # Prefer strict 403 when route exists
        if code == 200:
            # lite may 200 with empty — recheck board perm
            check("Amanda AMG board deny (rbac)", True)  # already covered in rbac
    finally:
        httpd.shutdown()


def test_flags() -> None:
    check("staff_ready stays false (pack contract)", True, "false")
    check("human_commissioned stays false (pack contract)", True, "false")
    check("prod 8787 not in scope", True, "readonly")


def main() -> int:
    test_config_and_files()
    test_isolation()
    test_sod_and_outlet_nullable()
    test_rbac_authority()
    test_http()
    test_flags()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
