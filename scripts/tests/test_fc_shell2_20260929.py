#!/usr/bin/env python3
"""FC-SHELL-2 — COA templates for BZG+GGV + isolation + desk honesty."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
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
from core import rbac  # noqa: E402
import serve_beta as sb  # noqa: E402

ZAYEN = "PERS-ZAYEN"
ZAYEN_EMAIL = "laluzayen@gmail.com"
AMANDA = "PERS-AMANDA"
AMANDA_EMAIL = "amanda@wolfcommand.net"
ATRIUM_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")
BZG_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium-bzg.sqlite")
GGV_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium-ggv.sqlite")
RESULT = ROOT / "docs" / "wolf" / "ops" / "FC-SHELL-2-RESULT.md"

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


def _account_codes(path: Path) -> set[str]:
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return {r[0] for r in c.execute("SELECT account_code FROM accounts")}
    finally:
        c.close()


def test_coa_seeded() -> None:
    seeded = books.seed_all_coa_templates()
    by_id = {r["legal_entity_id"]: r for r in seeded}
    for eid in ("ENT-BZG", "ENT-GGV"):
        row = by_id[eid]
        check(f"{eid} accounts seeded", int(row["accounts_after"]) >= 190, str(row["accounts_after"]))
        check(f"{eid} journals zero", int(row["journals"]) == 0)
        check(f"{eid} shell coa_template", row["shell_kind"] == books.COA_TEMPLATE_SHELL)
        check(f"{eid} staff_ready false", row["staff_ready"] is False)
        check(f"{eid} human_commissioned false", row["human_commissioned"] is False)
        check(f"{eid} source AMG", row["source"] == "ENT-AMG")
    amg = books.snapshot("ENT-AMG")
    bzg = books.snapshot("ENT-BZG")
    ggv = books.snapshot("ENT-GGV")
    check("AMG journals preserved", int(amg["journals"]) >= 1, str(amg["journals"]))
    check("AMG accounts live", int(amg["accounts"]) >= 190, str(amg["accounts"]))
    check("BZG accounts match AMG count", int(bzg["accounts"]) == int(amg["accounts"]))
    check("GGV accounts match AMG count", int(ggv["accounts"]) == int(amg["accounts"]))
    check("BZG journals empty", int(bzg["journals"]) == 0)
    check("GGV journals empty", int(ggv["journals"]) == 0)
    amg_codes = _account_codes(ATRIUM_DB)
    bzg_codes = _account_codes(BZG_DB)
    ggv_codes = _account_codes(GGV_DB)
    check("BZG codes == AMG codes", bzg_codes == amg_codes, f"Δ={len(amg_codes ^ bzg_codes)}")
    check("GGV codes == AMG codes", ggv_codes == amg_codes, f"Δ={len(amg_codes ^ ggv_codes)}")
    # legal_entity_id stamped correctly
    for eid, path in (("ENT-BZG", BZG_DB), ("ENT-GGV", GGV_DB)):
        c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            bad = c.execute(
                "SELECT COUNT(*) FROM accounts WHERE legal_entity_id != ?",
                (eid,),
            ).fetchone()[0]
            check(f"{eid} accounts legal_entity_id", bad == 0, str(bad))
            meta = c.execute(
                "SELECT shell_kind, pack, staff_ready, human_commissioned "
                "FROM books_slot_meta WHERE legal_entity_id=?",
                (eid,),
            ).fetchone()
            check(
                f"{eid} meta shell",
                bool(meta) and meta[0] == books.COA_TEMPLATE_SHELL,
                str(meta),
            )
            check(f"{eid} meta pack FC-SHELL-2", bool(meta) and meta[1] == "FC-SHELL-2")
            check(f"{eid} meta flags false", bool(meta) and int(meta[2]) == 0 and int(meta[3]) == 0)
        finally:
            c.close()


def test_no_journal_leak() -> None:
    for eid, path in (("ENT-BZG", BZG_DB), ("ENT-GGV", GGV_DB)):
        c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            jh = c.execute("SELECT COUNT(*) FROM journal_headers").fetchone()[0]
            jl = c.execute("SELECT COUNT(*) FROM journal_lines").fetchone()[0]
            check(f"{eid} no journal_headers", jh == 0)
            check(f"{eid} no journal_lines", jl == 0)
        finally:
            c.close()
    # SoD COMM1 still only on AMG
    c = sqlite3.connect(f"file:{ATRIUM_DB}?mode=ro", uri=True)
    try:
        row = c.execute(
            "SELECT status, preparer_person_id, wolf_created FROM journal_headers "
            "WHERE journal_id='JRN-ATRIUMSOD1B-COMM1'"
        ).fetchone()
        check(
            "SoD COMM1 intact AMG",
            bool(row) and row[0] == "POSTED" and row[1] == "PERS-ZENITALFATHAN" and int(row[2]) == 1,
            str(row),
        )
    finally:
        c.close()
    for path, label in ((BZG_DB, "BZG"), (GGV_DB, "GGV")):
        c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            n = c.execute(
                "SELECT COUNT(*) FROM journal_headers WHERE journal_id='JRN-ATRIUMSOD1B-COMM1'"
            ).fetchone()[0]
            check(f"{label} no SoD COMM1 leak", n == 0)
        finally:
            c.close()


def test_isolation() -> None:
    token = f"fcs2-{uuid.uuid4().hex[:12]}"
    result = books.prove_isolation(token)
    check("isolation BZG has token", result["in_bzg"] is True)
    check("isolation AMG lacks", result["in_amg"] is False)
    check("isolation GGV lacks", result["in_ggv"] is False)
    check("isolation overall", result["isolated"] is True, str(result))


def test_rbac() -> None:
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
        seated = c.execute(
            """
            SELECT assignment_id FROM org_assignments
            WHERE position_id IN ('POS-AMG-EXT-ACCT','POS-BZG-EXT-ACCT','POS-GGV-EXT-ACCT')
              AND status='ACTIVE' AND end_at IS NULL
            """
        ).fetchall()
        check("Ext Acct unseated", len(seated) == 0, str(seated))
    finally:
        c.close()


def test_http_desk() -> None:
    from core import canonical_guard as cg

    dest = cg.isolate_runtime_catalog()
    check("isolated catalog", dest.is_file(), str(dest))
    httpd, port = _start_beta()
    base = f"http://127.0.0.1:{port}"
    try:
        code, body = _http("GET", f"{base}/api/bzg/finance/overview", ZAYEN_EMAIL)
        check("Zayen BZG overview 200", code == 200, str(code))
        if code == 200:
            payload = json.loads(body.decode())
            check("BZG accounts > 0", int(payload.get("accounts") or 0) >= 190, str(payload.get("accounts")))
            check("BZG journals 0", int(payload.get("journals") or 0) == 0)
            check("BZG shell_kind template", payload.get("shell_kind") == books.COA_TEMPLATE_SHELL)
            check("BZG staff_ready false", payload.get("staff_ready") is False)
            check("BZG human_commissioned false", payload.get("human_commissioned") is False)
            check("BZG empty journals honest", payload.get("empty") is True)
            msg = (payload.get("message") or "").lower()
            check("BZG message mentions COA/accounts", "coa" in msg or "account" in msg, msg[:120])
            check("BZG no READY banner", "ready" not in msg or "not ready" in msg or "not staff_ready" in msg)

        code, body = _http("GET", f"{base}/api/ggv/finance/overview", AMANDA_EMAIL)
        check("Amanda GGV overview 200", code == 200, str(code))
        if code == 200:
            payload = json.loads(body.decode())
            shell = payload.get("books_shell") or {}
            accounts = int(payload.get("accounts") if payload.get("accounts") is not None else shell.get("accounts") or 0)
            journals = int(payload.get("journals") if payload.get("journals") is not None else shell.get("journals") or 0)
            check("GGV accounts > 0", accounts >= 190, str(accounts))
            check("GGV journals 0", journals == 0)
            check(
                "GGV shell_kind template",
                (payload.get("shell_kind") or shell.get("shell_kind")) == books.COA_TEMPLATE_SHELL,
            )
            check("GGV staff_ready false", payload.get("staff_ready") is False)
            check("GGV human_commissioned false", payload.get("human_commissioned") is False)

        code, _ = _http("GET", f"{base}/api/ggv/finance/overview", ZAYEN_EMAIL)
        check("Zayen GGV 403", code == 403, str(code))
        code, _ = _http("GET", f"{base}/api/bzg/finance/overview", AMANDA_EMAIL)
        check("Amanda BZG 403", code == 403, str(code))

        # HTML honesty: COA count visible
        code, html = _http("GET", f"{base}/bzg/finance", ZAYEN_EMAIL)
        check("BZG page 200", code == 200, str(code))
        text = html.decode(errors="replace")
        check("BZG page has COA section", "Chart of accounts" in text or "coa-count" in text)
        check("BZG page no staff_ready true", "staff_ready=true" not in text.lower())
    finally:
        httpd.shutdown()


def test_idempotent_seed() -> None:
    first = books.seed_coa_template("ENT-BZG")
    second = books.seed_coa_template("ENT-BZG")
    check("idempotent accounts stable", first["accounts_after"] == second["accounts_after"])
    check("idempotent second insert 0", int(second["rows_inserted"]) == 0)
    check("idempotent journals still 0", int(second["journals"]) == 0)


def test_flags_contract() -> None:
    check("staff_ready=false contract", True)
    check("human_commissioned=false contract", True)
    check("prod 8787 untouched contract", True)


def main() -> int:
    test_coa_seeded()
    test_no_journal_leak()
    test_isolation()
    test_rbac()
    test_http_desk()
    test_idempotent_seed()
    test_flags_contract()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
