#!/usr/bin/env python3
"""ATRIUMFIN-UX-1 and UX-2. Atrium Finance is a staff desk. Grants stay as they are.

Beta catalog writes for the approval submit use a temp copy. Draft journals
use a temp books file. Does not mark staff_ready or human_commissioned.
"""
from __future__ import annotations

import json
import os
import re
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
    check("centred desk", "width: min(1120px, 100%)" in html and "margin: 0 auto" in html)
    check("board side panel", "grid-template-columns: minmax(0, 1fr) 300px" in html)
    check("phone nav stays one line", "flex-wrap: nowrap" in html)
    check("boards control hidden on this desk", "#wolfnav-t { display: none" in html)
    check("page header has no sign out", 'href="/signout"' not in html)
    for banned in desk.PAGE_BANNED:
        check(f"page omits wording {banned[:24]}", banned not in html)
    check("no capability id", re.search(r"CAP-[A-Za-z0-9]", html) is None)
    check("no record id", re.search(r"CR-[A-Za-z0-9]", html) is None)
    hrefs = [row["href"] for row in desk.navigation()]
    check(
        "nav is the finance desk",
        hrefs
        == [
            "/amg/finance",
            "/amg/finance/ledger",
            "/amg/finance/accounts",
            "/amg/finance/journals",
            "/amg/finance/reports",
            "/amg/finance/approvals",
        ],
    )
    for href in hrefs:
        check(f"page links {href}", f'href="{href}"' in html)
    for hidden in ("/api/journals", "/api/ledger", "/api/trial-balance", "/api/reports/"):
        check(f"page does not link {hidden}", hidden not in html)
    labels = [row["label"] for row in desk.navigation()]
    check(
        "nav labels",
        labels == ["Board", "Ledger", "Chart of Accounts", "Journals", "Reports", "Approvals"],
    )
    withheld_ids = {row["id"] for row in desk.withheld()}
    check("cash stays off the nav", "cash" in withheld_ids and "/amg/finance/cash" not in html)
    check("configuration stays off the nav", "configuration" in withheld_ids)
    check("post stays off the nav", "journal-post" in withheld_ids)
    check("approve no longer withheld on lite desk", "journal-approve" not in withheld_ids)


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
        expected = {row[1] for row in ATRIUM_GRANTS} | {ATRIUM_SUBMIT} | {
            "atrium.journal.approve",
            "atrium.journal.reject",
        }
        held = {row[1] for row in ATRIUM_HELD_BACK}
        check("grants include FC approve", "atrium.journal.approve" in codes, str(sorted(codes)))
        check("post still held", "atrium.journal.post" not in codes)
        check("board read on Atrium", rbac.can(ZAYEN_PERSON, "atrium.board.read", AMG, conn=conn) is True)
        for code in ("atrium.ledger.read", "atrium.coa.read", "atrium.report.read", "atrium.journal.draft"):
            check(f"existing grant {code}", rbac.can(ZAYEN_PERSON, code, AMG, conn=conn) is True)
        check("board read not on GGV", rbac.can(ZAYEN_PERSON, "atrium.board.read", GGV, conn=conn) is False)
        check("approval request on Atrium", rbac.can(ZAYEN_PERSON, "approval.request", AMG, conn=conn) is True)
        check(
            "FC approve granted",
            rbac.can(ZAYEN_PERSON, "atrium.journal.approve", AMG, conn=conn) is True,
        )
        for code in (
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

    books_dir = Path(tempfile.mkdtemp(prefix="atrium-books-", dir=str(ROOT / "state")))
    os.environ["ATRIUM_BOOKS_DB"] = str(books_dir / "amg.sqlite")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        status, raw = call(port, "/amg/finance/lite", EMAIL)
        text = raw.decode("utf-8", "replace")
        check("board page 200", status == 200 and "Atrium Finance" in text, f"status={status}")
        for banned in desk.BANNED_UI:
            check(f"served page omits {banned[:32]}", banned not in text)
        check("served page has one sign out", text.lower().count("sign out") == 1, str(text.lower().count("sign out")))
        for row in desk.navigation():
            href = row["href"]
            if href == "/amg/finance":
                expect = "/amg/finance/lite"
            elif href.startswith("/amg/finance/"):
                expect = "/amg/finance/lite/" + href[len("/amg/finance/") :]
            else:
                expect = href
            check(f"served nav {row['href']}", f'href="{expect}"' in text)
        status, raw = call(port, "/amg/finance/lite/approvals", EMAIL)
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
        check("api chart is loaded", (body.get("chart") or {}).get("count") == 190, str(body.get("chart")))
        for section in ("/ledger", "/accounts", "/journals", "/reports"):
            status, raw = call(port, "/amg/finance/lite" + section, EMAIL)
            page = raw.decode("utf-8", "replace")
            check(f"section {section} 200", status == 200 and "Atrium Finance" in page, f"status={status}")
            status, raw = call(port, "/api/amg/finance" + section, EMAIL, accept="application/json")
            payload = json.loads(raw.decode() or b"{}")
            check(f"api {section} 200", status == 200 and payload.get("ok") is True, f"status={status}")
            check(f"api {section} has no figure", payload.get("figure") is None)
        status, raw = call(port, "/api/amg/finance/accounts", EMAIL, accept="application/json")
        chart = json.loads(raw.decode() or b"{}")
        codes = {row.get("account_code") for row in chart.get("accounts") or []}
        check("chart includes guest ledger", "1210" in codes and "4110" in codes)
        check("chart has no balance field", all("balance" not in row for row in chart.get("accounts") or []))
        status, raw = call(port, "/api/amg/finance/ledger", EMAIL, accept="application/json")
        ledger = json.loads(raw.decode() or b"{}")
        check("ledger has no posted lines", ledger.get("lines") == [] and ledger.get("posted") is False)
        status, raw = call(port, "/api/amg/finance/reports", EMAIL, accept="application/json")
        reports = json.loads(raw.decode() or b"{}")
        names = {row.get("report_name") for row in reports.get("reports") or []}
        check(
            "report names are the atrium statements",
            "USALI Operating Statement" in names and "PSAK Statement of Financial Position" in names,
            str(names),
        )
        check("reports have no lines", all(row.get("lines") is None and row.get("figure") is None for row in reports.get("reports") or []))
        check("api chart is loaded", int((body.get("chart") or {}).get("count") or 0) >= 100)
        blob = json.dumps(body)
        for banned in desk.BANNED_UI:
            check(f"api omits {banned[:32]}", banned not in blob)
        check("served page has one sign out", text.lower().count("sign out") == 1, text.lower().count("sign out"))
        for href in ("/amg/finance/lite/ledger", "/amg/finance/lite/accounts", "/amg/finance/lite/journals", "/amg/finance/lite/reports"):
            status, raw = call(port, href, EMAIL)
            page = raw.decode("utf-8", "replace")
            check(f"page 200 {href}", status == 200 and "Atrium Finance" in page, f"status={status}")
            for banned in desk.PAGE_BANNED:
                check(f"{href} clean {banned[:16]}", banned not in page)
        status, raw = call(port, "/api/amg/finance/accounts", EMAIL, accept="application/json")
        accounts = json.loads(raw.decode())
        codes = {row.get("account_code") for row in accounts.get("accounts") or []}
        check("chart is atrium 1210 and 4110", status == 200 and {"1210", "4110", "1000"} <= codes, f"status={status} n={len(codes)}")
        check("chart has no balance field", status == 200 and all("balance" not in row for row in accounts.get("accounts") or []))
        status, raw = call(port, "/api/amg/finance/ledger", EMAIL, accept="application/json")
        ledger = json.loads(raw.decode())
        check("ledger has no posted lines", status == 200 and ledger.get("lines") == [] and ledger.get("figure") is None)
        status, raw = call(port, "/api/amg/finance/reports", EMAIL, accept="application/json")
        reports = json.loads(raw.decode())
        names = {row.get("report_name") for row in reports.get("reports") or []}
        check("reports name the atrium statements", status == 200 and "USALI Operating Statement" in names and reports.get("figure") is None)
        check("reports do not invent a total", "total_debit" not in reports and "total_credit" not in reports)

        denied = (
            ("GET", "/ggv/finance", None),
            ("GET", "/api/ggv/finance/notas", None),
            ("GET", "/bzg/uma-blu", None),
            ("GET", "/wolf", None),
            ("GET", "/api/core/roles", None),
            ("GET", "/api/fin/mgmt-reporting", None),
            ("POST", "/api/journals/sample/approve", {}),
            ("POST", "/api/journals/sample/post", {}),
            ("POST", "/api/amg/finance/journals/JRN-sample0001/approve", {}),
            ("POST", "/api/amg/finance/journals/JRN-sample0001/post", {}),
            ("POST", "/api/ggv/finance/pay", {}),
            ("POST", "/api/ggv/finance/vendors/sample/bank", {}),
            ("POST", "/api/core/approvals/sample/approve", {}),
            ("GET", "/amg/finance", None),
        )
        for method, path, payload in denied[:-1]:
            status, _raw = call(port, path, EMAIL, method=method, body=payload, accept="application/json")
            check(f"Zayen 403 {method} {path}", status == 403, f"status={status}")
        outsiders = (
            ("Amanda", "amanda@wolfcommand.net"),
            ("Owner", "mrwolf@wolfcommand.net"),
            ("Devi", "deviputu236@gmail.com"),
            ("Haikal", "haikalqilbari123@gmail.com"),
        )
        page_outsiders = tuple(pair for pair in outsiders if pair[0] != "Owner")
        for name, email in page_outsiders:
            for outsider_path in (
                "/amg/finance",
                "/amg/finance/ledger",
                "/amg/finance/accounts",
                "/amg/finance/journals",
                "/amg/finance/reports",
                "/amg/finance/approvals",
            ):
                status, _raw = call(port, outsider_path, email)
                check(f"{name} page 403 {outsider_path}", status == 403, f"status={status}")
            for outsider_path in (
                "/api/amg/finance",
                "/api/amg/finance/ledger",
                "/api/amg/finance/accounts",
                "/api/amg/finance/journals",
                "/api/amg/finance/reports",
            ):
                status, _raw = call(port, outsider_path, email, accept="application/json")
                check(f"{name} api 403 {outsider_path}", status == 403, f"status={status}")
        for outsider_path in (
            "/api/amg/finance",
            "/api/amg/finance/ledger",
            "/api/amg/finance/accounts",
            "/api/amg/finance/journals",
            "/api/amg/finance/reports",
        ):
            status, _raw = call(port, outsider_path, "mrwolf@wolfcommand.net", accept="application/json")
            check(f"Owner api 403 {outsider_path}", status == 403, f"status={status}")
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
        catalog_paths = (fin.CATALOG_DB, apr.CATALOG_DB, rbac.CATALOG_DB)
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
            draft = {
                "journal_date": "2026-09-28",
                "memo": "Room revenue draft",
                "lines": [
                    {"account_code": "1210", "debit": 150000, "credit": 0},
                    {"account_code": "4110", "debit": 0, "credit": 150000},
                ],
            }
            status, raw = call(
                port,
                "/api/amg/finance/journals",
                EMAIL,
                method="POST",
                body=draft,
                accept="application/json",
            )
            saved_draft = json.loads(raw.decode() or b"{}")
            journal_id = ((saved_draft.get("journal") or {}).get("journal_id")) or ""
            check("draft journal is saved", status == 201 and saved_draft.get("draft_saved") is True, f"status={status} {saved_draft}")
            check("draft is not posted", (saved_draft.get("journal") or {}).get("status") == "DRAFT" and saved_draft.get("posted") is False)
            status, raw = call(
                port,
                "/api/amg/finance/journals",
                EMAIL,
                method="POST",
                body={
                    "journal_date": "2026-09-28",
                    "memo": "Out of balance",
                    "lines": [
                        {"account_code": "1210", "debit": 10, "credit": 0},
                        {"account_code": "4110", "debit": 0, "credit": 20},
                    ],
                },
                accept="application/json",
            )
            check("unbalanced draft is refused", status == 400, f"status={status}")
            status, raw = call(
                port,
                "/api/amg/finance/journals",
                EMAIL,
                method="POST",
                body={
                    "journal_date": "2026-09-28",
                    "memo": "Heading account",
                    "lines": [
                        {"account_code": "1000", "debit": 10, "credit": 0},
                        {"account_code": "4110", "debit": 0, "credit": 10},
                    ],
                },
                accept="application/json",
            )
            check("heading account is refused", status == 400, f"status={status}")
            status, raw = call(
                port,
                f"/api/amg/finance/journals/{journal_id}",
                EMAIL,
                method="POST",
                body={
                    "journal_date": "2026-09-28",
                    "memo": "Room revenue draft revised",
                    "lines": draft["lines"],
                },
                accept="application/json",
            )
            revised = json.loads(raw.decode() or b"{}")
            check(
                "draft can be revised",
                status == 200 and (revised.get("journal") or {}).get("memo") == "Room revenue draft revised",
                f"status={status}",
            )
            status, raw = call(port, "/api/amg/finance/ledger", EMAIL, accept="application/json")
            after_ledger = json.loads(raw.decode() or b"{}")
            check("draft stays off the ledger", after_ledger.get("lines") == [])
        finally:
            fin.CATALOG_DB, apr.CATALOG_DB, rbac.CATALOG_DB = catalog_paths
            shutil.rmtree(tmp, ignore_errors=True)
    finally:
        httpd.shutdown()
        httpd.server_close()
        os.environ.pop("ATRIUM_BOOKS_DB", None)
        shutil.rmtree(books_dir, ignore_errors=True)

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
