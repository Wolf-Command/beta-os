#!/usr/bin/env python3
"""ATRIUMFIN-UX-1. Atrium Finance is a staff desk. Grants stay as they are.

Beta catalog writes for the approval submit use a temp copy. Does not mark
staff_ready or human_commissioned.
"""
from __future__ import annotations

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
sys.path.insert(0, str(ROOT / "scripts"))
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import atrium_finance_desk as desk  # noqa: E402
from core import rbac  # noqa: E402
from core.staff_access import (  # noqa: E402
    ATRIUM_GRANTS,
    ATRIUM_HELD_BACK,
    ATRIUM_SUBMIT,
    FINANCE_EMAIL,
    ZAYEN_PERSON,
)

CATALOG = ROOT / "catalog" / "content_library.sqlite"
PAGE = ROOT / "dashboards" / "amg-finance.html"
AMG = {"entity_id": "ENT-AMG"}
GGV = {"entity_id": "ENT-GGV"}
BZG = {"entity_id": "ENT-BZG"}
EMAIL = FINANCE_EMAIL
PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def live() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def test_page_and_nav() -> None:
    html = PAGE.read_text(encoding="utf-8")
    for banned in desk.BANNED_UI:
        check(f"page omits {banned[:32]}", banned not in html)
    check("header", "Atrium Finance" in html and 'id="entity"' in html)
    check("entity is Atrium", ">Atrium</p>" in html)
    check("controller line", desk.CONTROLLER_LINE in html)
    check("touch target", "min-height: var(--touch)" in html and "--touch: 44px" in html)
    check("phone rule", "@media (max-width: 860px)" in html)
    check("no horizontal scroll rule", "overflow-x: clip" in html)
    hrefs = [row["href"] for row in desk.navigation()]
    check("nav is board and approvals", hrefs == ["/amg/finance", "/amg/finance/approvals"])
    for href in hrefs:
        check(f"page links {href}", f'href="{href}"' in html)
    for hidden in ("/api/journals", "/api/ledger", "/api/accounts", "/api/trial-balance", "/api/reports/"):
        check(f"page does not link {hidden}", hidden not in html)
    labels = [row["label"] for row in desk.navigation()]
    check("nav labels", labels == ["Board", "Approvals"])
    withheld_ids = {row["id"] for row in desk.withheld()}
    check(
        "withheld capabilities",
        withheld_ids == {"ledger", "chart", "reports", "journal"},
    )


def test_grants_unchanged() -> None:
    conn = live()
    try:
        codes = {
            str(row[0])
            for row in conn.execute(
                """
                SELECT perm.code
                FROM org_assignments a
                JOIN org_positions pos ON pos.position_id = a.position_id
                JOIN org_role_permissions rp ON rp.role_id = pos.role_id
                JOIN org_permissions perm ON perm.permission_id = rp.permission_id
                WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
                  AND rp.effect='ALLOW'
                """,
                (ZAYEN_PERSON,),
            )
        }
        expected = {row[1] for row in ATRIUM_GRANTS} | {ATRIUM_SUBMIT}
        held = {row[1] for row in ATRIUM_HELD_BACK}
        check("grants match the seat", codes == expected, str(sorted(codes)))
        check("approve and post not granted", held.isdisjoint(codes))
        check("board read on Atrium", rbac.can(ZAYEN_PERSON, "atrium.board.read", AMG, conn=conn) is True)
        check("board read not on GGV", rbac.can(ZAYEN_PERSON, "atrium.board.read", GGV, conn=conn) is False)
        check("approval request on Atrium", rbac.can(ZAYEN_PERSON, "approval.request", AMG, conn=conn) is True)
        for code in (
            "atrium.journal.approve",
            "atrium.journal.post",
            "payment.approve",
            "payment.execute",
            "vendor.bank.change",
            "approval.decide",
            "finance.policy.admin",
            "organisation.role.read",
            "core.operator",
        ):
            check(
                f"denied {code}",
                rbac.can(ZAYEN_PERSON, code, AMG, conn=conn) is False
                and rbac.can(ZAYEN_PERSON, code, GGV, conn=conn) is False
                and rbac.can(ZAYEN_PERSON, code, BZG, conn=conn) is False,
            )
    finally:
        conn.close()


def call(port: int, path: str, email: str | None, method: str = "GET", body: dict | None = None, accept: str = "text/html") -> tuple[int, bytes]:
    data = None if body is None else json.dumps(body).encode()
    headers = {"Accept": accept}
    if email:
        headers["X-Wolf-Subject"] = email
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def test_http() -> None:
    import serve_beta as sb
    from core import approvals as apr
    from core import ggv_finance_nota as fin

    handler = None
    for obj in vars(sb).values():
        if isinstance(obj, type) and issubclass(obj, BaseHTTPRequestHandler) and obj.__name__ == "BetaHandler":
            handler = obj
            break
    check("beta handler found", handler is not None)
    if handler is None:
        return
    before = live()
    try:
        approval_before = before.execute("SELECT COUNT(*) FROM core_approval_requests").fetchone()[0]
    finally:
        before.close()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        status, raw = call(port, "/amg/finance", EMAIL)
        text = raw.decode("utf-8", "replace")
        check("board page 200", status == 200 and "Atrium Finance" in text, f"status={status}")
        for banned in desk.BANNED_UI:
            check(f"served page omits {banned[:32]}", banned not in text)
        for row in desk.navigation():
            check(f"served nav {row['href']}", f'href="{row["href"]}"' in text)
        status, raw = call(port, "/amg/finance/approvals", EMAIL)
        approvals_html = raw.decode("utf-8", "replace")
        check("approvals page 200", status == 200 and "Approvals" in approvals_html, f"status={status}")
        for banned in desk.BANNED_UI:
            check("approvals page clean", banned not in approvals_html)
        status, raw = call(port, "/api/amg/finance", EMAIL, accept="application/json")
        body = json.loads(raw.decode())
        check(
            "api entity is AMG only",
            status == 200 and [row.get("id") for row in body.get("finance_entities") or []] == ["AMG"],
            str(body.get("finance_entities")),
        )
        check(
            "api nav matches desk",
            [row.get("href") for row in body.get("navigation") or []] == [row["href"] for row in desk.navigation()],
        )
        check("api has no figure", (body.get("board") or {}).get("figure") is None)
        check("api not staff ready", body.get("staff_ready") is False and body.get("human_commissioned") is False)
        check("api does not move money", body.get("money_movement") is False and body.get("books_opened") is False)
        blob = json.dumps(body)
        for banned in desk.BANNED_UI:
            check(f"api omits {banned[:32]}", banned not in blob)

        denied = (
            ("GET", "/ggv/finance", None),
            ("GET", "/api/ggv/finance/notas", None),
            ("GET", "/bzg/uma-blu", None),
            ("GET", "/wolf", None),
            ("GET", "/api/core/roles", None),
            ("GET", "/api/fin/mgmt-reporting", None),
            ("POST", "/api/journals/sample/approve", {}),
            ("POST", "/api/journals/sample/post", {}),
            ("POST", "/api/ggv/finance/pay", {}),
            ("POST", "/api/ggv/finance/vendors/sample/bank", {}),
            ("POST", "/api/core/approvals/sample/approve", {}),
            ("GET", "/amg/finance", None),
        )
        for method, path, payload in denied[:-1]:
            status, _raw = call(port, path, EMAIL, method=method, body=payload, accept="application/json")
            check(f"Zayen 403 {method} {path}", status == 403, f"status={status}")
        status, _raw = call(port, "/amg/finance", "amanda@wolfcommand.net")
        check("Amanda atrium page 403", status == 403, f"status={status}")
        status, _raw = call(port, "/amg/finance/approvals", "amanda@wolfcommand.net")
        check("Amanda approvals page 403", status == 403, f"status={status}")
        status, _raw = call(port, "/api/amg/finance", EMAIL, method="POST", body={}, accept="application/json")
        check("POST board stays 405", status == 405, f"status={status}")
        refused_payloads = (
            ("amount", {"title": "Pay the vendor", "material_amount": "10", "currency": "IDR"}),
            ("spend", {"title": "Post it", "request_type": "SPEND"}),
            ("other entity", {"title": "Other company", "owning_entity_id": "ENT-GGV"}),
            ("bank permission", {"title": "Change bank", "required_permission_code": "vendor.bank.change"}),
        )
        for label, payload in refused_payloads:
            status, _raw = call(
                port,
                "/api/amg/finance/approvals",
                EMAIL,
                method="POST",
                body=payload,
                accept="application/json",
            )
            check(f"desk refuses {label}", status == 403, f"status={status} body={payload}")

        tmp = Path(tempfile.mkdtemp(prefix="atrium-fin-ux-", dir=str(ROOT / "state")))
        copy = tmp / "catalog.sqlite"
        shutil.copy(CATALOG, copy)
        saved = (fin.CATALOG_DB, apr.CATALOG_DB, rbac.CATALOG_DB)
        fin.CATALOG_DB = copy
        apr.CATALOG_DB = copy
        rbac.CATALOG_DB = copy
        try:
            status, raw = call(
                port,
                "/api/amg/finance/approvals",
                EMAIL,
                method="POST",
                body={"title": "Atrium decision for the week", "description": "Please review."},
                accept="application/json",
            )
            created = json.loads(raw.decode() or b"{}")
            check("general request is accepted", status == 201 and created.get("ok") is True, f"status={status} {created}")
            check("accepted request is not money", (created.get("approval") or {}).get("money_movement") is False)
        finally:
            fin.CATALOG_DB, apr.CATALOG_DB, rbac.CATALOG_DB = saved
            shutil.rmtree(tmp, ignore_errors=True)
    finally:
        httpd.shutdown()
        httpd.server_close()

    after = live()
    try:
        approval_after = after.execute("SELECT COUNT(*) FROM core_approval_requests").fetchone()[0]
    finally:
        after.close()
    check("live approval rows unchanged", approval_before == approval_after, f"{approval_before} -> {approval_after}")


def main() -> None:
    test_page_and_nav()
    test_grants_unchanged()
    test_http()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
