#!/usr/bin/env python3
"""GGV Finance invoices — Beta catalog copy only. No payment and no email send."""
from __future__ import annotations

import json
import os
import shutil
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import ggv_finance_invoice as inv  # noqa: E402
from core import ggv_finance_nota as fin  # noqa: E402
from core import rbac as rbac  # noqa: E402
from core import staff_access  # noqa: E402
from core import staff_home  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

PASS = 0
FAIL = 0
AMANDA = "PERS-AMANDA"
ZAYEN = "PERS-ZAYEN"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def wire(db_path: Path) -> None:
    fin.CATALOG_DB = db_path
    shell._CATALOG_DB = db_path


def customer(conn, person: str, name: str, **extra):
    body = {"legal_name": name, "email": extra.get("email"), "billing_address": extra.get("billing_address")}
    body.update(extra)
    return inv.create_customer(person, body, conn)


def lines(count: int = 1, **over):
    row = {"description": "Design fee", "qty": "2", "unit_price": "10000.4", "tax_rate": "10"}
    row.update(over)
    return [dict(row) for _ in range(count)]


def draft_body(customer_id: str, items: list | None = None) -> dict:
    return {
        "customer_id": customer_id,
        "invoice_date": "2026-09-28",
        "due_date": "2026-10-12",
        "terms": "14 days",
        "currency": "IDR",
        "notes": "Beta test",
        "reference": "PO-1",
        "payment_method": "Bank transfer",
        "payment_reference": "GGV operating account",
        "lines": items or lines(4),
        "grand_total": "1",
    }


def test_static() -> None:
    html = (ROOT / "dashboards" / "ggv-finance.html").read_text(encoding="utf-8")
    for label in (
        "Overview",
        "Invoices",
        "Notas / Bills",
        "Vendors",
        "Customers",
        "History",
        "Reports",
        "+ New Invoice",
        "Add line",
        "Preview",
        "Save draft",
        "Issue",
    ):
        check(f"page has {label}", label in html)
    check("mobile width", "@media (max-width: 430px)" in html)
    check("no data table", "<table" not in html.lower())
    check("accountant word kept", "Accountant" in html)
    check("no person name", "Amanda" not in html and "Matt" not in html)
    check("number assigned on issue", "Number assigned on issue" in html)
    check("operator number field removed", 'id="inv-number"' not in html)
    check(
        "gmail next step named",
        "Generate Gmail draft with PDF attachment — human review/send, never automatic" in html,
    )
    amg = (ROOT / "dashboards" / "amg-finance.html").read_text(encoding="utf-8")
    check("amg entity slot", 'id="entity"' in amg)


def test_flow(conn) -> None:
    staff_access.apply(conn)
    seat = conn.execute(
        "SELECT is_primary, status FROM org_assignments WHERE assignment_id=?",
        (staff_access.AMANDA_FINANCE_ASSIGNMENT,),
    ).fetchone()
    check(
        "amanda assignment",
        seat is not None and int(seat[0]) == 0 and seat[1] == "ACTIVE",
        str(tuple(seat) if seat else None),
    )
    check(
        "role is not her name",
        conn.execute(
            "SELECT display_name FROM org_roles WHERE role_id=?",
            (inv.ROLE_OPERATOR,),
        ).fetchone()[0]
        == "GGV Finance Operator",
    )
    check(
        "amanda still one person",
        conn.execute(
            "SELECT COUNT(*) FROM org_persons WHERE person_id=?",
            (AMANDA,),
        ).fetchone()[0]
        == 1,
    )
    entities = inv.finance_entities(AMANDA, conn)
    check("amanda finance entity is GGV only", [row["id"] for row in entities] == ["GGV"])
    zayen = inv.finance_entities(ZAYEN, conn)
    check("zayen finance entity is AMG only", [row["id"] for row in zayen] == ["AMG"])
    check(
        "amanda cannot pay",
        rbac.can(AMANDA, "payment.execute", {"entity_id": "ENT-GGV"}, conn=conn) is False,
    )
    check(
        "amanda cannot open atrium board",
        rbac.can(AMANDA, "atrium.board.read", {"entity_id": "ENT-AMG"}, conn=conn) is False,
    )
    check(
        "amanda can create an invoice",
        rbac.can(AMANDA, "finance.invoice.create", {"entity_id": "ENT-GGV"}, conn=conn) is True,
    )
    home = staff_home.build_home(AMANDA, conn=conn)
    check(
        "my work links GGV finance",
        any(item.get("href") == "/ggv/finance" for item in home.get("desk") or []),
    )
    inv.ensure_schema(conn)
    from migrations.migrate_ggv_invoice_sequences import apply as apply_sequence

    apply_sequence(conn)
    conn.commit()
    apply_sequence(conn)
    conn.commit()
    numbering = inv.numbering_status(conn, AMANDA)
    check("sequence starts at 067A", numbering["next"] == "067A" and numbering["next_value"] == 67)
    check("number assigned at issue", numbering["assignment"] == "issue" and numbering["operator_types_number"] is False)
    check("operator cannot import", numbering["can_import"] is False)
    owner_audit = conn.execute(
        "SELECT COUNT(*) FROM fin_invoice_sequence_audit WHERE actor=? AND reason LIKE ?",
        ("Matthew", "%13:17%"),
    ).fetchone()[0]
    check("owner decision audited once", owner_audit == 1)
    invented = conn.execute(
        """
        SELECT COUNT(*) FROM ggv_invoices
        WHERE entity_id='ENT-GGV' AND invoice_number IN ('064A', '065A', '066A')
        """
    ).fetchone()[0]
    check("historical numbers not created", invented == 0)
    known = inv.known_customer_links(conn)
    check("the one not invented", known["the_one"] is None and known["seeded"] is False)
    check("keen eye not invented", known["keen_eye"] is None)

    made = customer(conn, AMANDA, "North Shore Client", email="north@example.com", billing_address="Ubud")
    cid = made["customer"]["customer_id"]
    try:
        customer(conn, AMANDA, "North Shore Client")
        check("duplicate customer refused", False)
    except fin.FinanceNotaError as exc:
        check("duplicate customer refused", exc.code == "duplicate_customer")
    try:
        inv.create_invoice(AMANDA, draft_body(cid) | {"invoice_number": "070A", "number_confirmed": True}, conn)
        check("operator cannot set number", False)
    except fin.FinanceNotaError as exc:
        check("operator cannot set number", exc.code == "number_assigned_on_issue")

    priced = inv.price_lines(
        [{"description": "Design fee", "qty": "1", "unit_price": "10.5", "tax_rate": ""}],
        "IDR",
    )
    check("idr half up", priced["subtotal"] == "11" and priced["grand_total"] == "11", priced["grand_total"])
    taxed = inv.price_lines(
        [{"description": "Print", "qty": "1", "unit_price": "333", "tax_rate": "10"}],
        "IDR",
    )
    check("idr tax rounded per line", taxed["tax_total"] == "33" and taxed["grand_total"] == "366", str(taxed))
    usd = inv.price_lines(
        [{"description": "Consult", "qty": "1", "unit_price": "10.005", "tax_rate": ""}],
        "USD",
    )
    check("usd two decimals", usd["grand_total"] == "10.01", usd["grand_total"])
    try:
        inv.price_lines(
            [{"description": "Design 2 x 5 and print 1 x 2", "qty": "1", "unit_price": "10"}],
            "IDR",
        )
        check("combined line refused", False)
    except fin.FinanceNotaError:
        check("combined line refused", True)

    four = lines(4)
    four[1]["description"] = "Hosting"
    four[2]["description"] = "Photo"
    four[3]["description"] = "Travel"
    saved = inv.create_invoice(AMANDA, draft_body(cid, four), conn)
    invoice = saved["invoice"]
    check("typed total ignored", invoice["grand_total"] != "1")
    check("four lines", len(invoice["lines"]) == 4)
    check("draft status", invoice["status"] == "DRAFT")
    check("draft has no number", invoice["invoice_number"] is None and invoice["number_label"] == "Number assigned on issue")
    check("created by amanda", invoice["created_by"] == AMANDA)
    edited_lines = invoice["lines"][:3]
    for row in edited_lines:
        row["tax_rate"] = row["tax_rate"] or ""
    edited = inv.edit_invoice(
        AMANDA,
        invoice["invoice_id"],
        draft_body(cid, edited_lines),
        conn,
    )
    check("line deleted", len(edited["invoice"]["lines"]) == 3)
    check("total changed after delete", edited["invoice"]["grand_total"] != invoice["grand_total"])
    second = inv.create_invoice(AMANDA, draft_body(cid), conn)
    check("second draft has no number", second["invoice"]["invoice_number"] is None)

    issued = inv.issue_invoice(AMANDA, invoice["invoice_id"], conn)
    check("first issue is 067A", issued["invoice"]["invoice_number"] == "067A" and issued["invoice"]["number_source"] == "sequence")
    check("issued", issued["invoice"]["status"] == "ISSUED")
    check("finalised by", issued["invoice"]["finalised_by"] == AMANDA)
    check("pdf reproducible", issued["pdf_reproducible"] is True)
    check("email not sent", issued["email_sent"] is False and issued["draft_email"]["gmail_called"] is False)
    check(
        "gmail step not built",
        issued["draft_email"].get("next_integration")
        == "Generate Gmail draft with PDF attachment — human review/send, never automatic"
        and issued["draft_email"]["gmail_draft_created"] is False,
    )
    pdf = inv.invoice_pdf(AMANDA, invoice["invoice_id"], conn)
    check("pdf bytes", pdf["_file"]["data"].startswith(b"%PDF"))
    import hashlib

    again = inv.render_pdf(issued["invoice"])
    check("pdf stable", hashlib.sha256(again).hexdigest() == issued["pdf_sha256"])
    history = issued["invoice"]["history"]
    check("history kept", any(item["action"] == "issue" for item in history))
    try:
        inv.edit_invoice(AMANDA, invoice["invoice_id"], draft_body(cid, edited_lines), conn)
        check("issued edit refused", False)
    except fin.FinanceNotaError:
        check("issued edit refused", True)
    try:
        inv.edit_invoice(
            AMANDA,
            invoice["invoice_id"],
            draft_body(cid, edited_lines) | {"invoice_number": "099A"},
            conn,
        )
        check("issued number immutable", False)
    except fin.FinanceNotaError as exc:
        check("issued number immutable", exc.code == "number_immutable")
    issued_again = inv.issue_invoice(AMANDA, second["invoice"]["invoice_id"], conn)
    check("second issue is 068A", issued_again["invoice"]["invoice_number"] == "068A")
    voided = inv.void_invoice(AMANDA, second["invoice"]["invoice_id"], conn)
    after_void = inv.numbering_status(conn)
    check(
        "void keeps number",
        voided["invoice"]["invoice_number"] == "068A" and voided["invoice"]["status"] == "VOID",
    )
    check("void does not recycle", after_void["next"] == "069A" and after_void["next_value"] == 69)
    third = inv.create_invoice(AMANDA, draft_body(cid), conn)
    third_issued = inv.issue_invoice(AMANDA, third["invoice"]["invoice_id"], conn)
    check("next after void is 069A", third_issued["invoice"]["invoice_number"] == "069A")
    try:
        inv.import_historical(AMANDA, draft_body(cid) | {"invoice_number": "064A"}, conn)
        check("amanda import denied", False)
    except fin.FinanceNotaError as exc:
        check("amanda import denied", exc.http_status == 403)
    imported = inv.import_historical("PERS-MATT", draft_body(cid) | {"invoice_number": "064A"}, conn)
    kept = inv.numbering_status(conn)
    check(
        "import preserves 064A",
        imported["invoice"]["invoice_number"] == "064A" and imported["invoice"]["number_source"] == "imported",
    )
    check("import does not rewind", kept["next_value"] == 70)
    try:
        inv.import_historical("PERS-MATT", draft_body(cid) | {"invoice_number": "064A"}, conn)
        check("import conflict", False)
    except fin.FinanceNotaError as exc:
        check("import conflict", exc.code == "duplicate_number" and (exc.extra or {}).get("conflict") is True)
    advanced = inv.import_historical("PERS-MATT", draft_body(cid) | {"invoice_number": "090A"}, conn)
    check("import advances past number", advanced["numbering"]["next_value"] == 91 and advanced["invoice"]["invoice_number"] == "090A")
    still = conn.execute(
        "SELECT COUNT(*) FROM ggv_invoices WHERE invoice_number IN ('065A', '066A')"
    ).fetchone()[0]
    check("065A and 066A still absent", still == 0)
    claimed = inv.claim_paid(AMANDA, invoice["invoice_id"], conn)
    check("claimed is not verified", claimed["invoice"]["status"] == "PAID_CLAIMED" and claimed["verified"] is False)
    try:
        fin.dispatch("POST", "/api/ggv/finance/pay", {}, {}, AMANDA)
        check("pay refused", False)
    except fin.FinanceNotaError as exc:
        check("pay refused", exc.http_status == 405)
    try:
        fin.dispatch("POST", f"/api/ggv/finance/invoices/{invoice['invoice_id']}/verify", {}, {}, AMANDA)
        check("verify refused", False)
    except fin.FinanceNotaError as exc:
        check("verify refused", exc.http_status == 405)
    try:
        fin.dispatch("POST", f"/api/ggv/finance/invoices/{invoice['invoice_id']}/part-paid", {}, {}, AMANDA)
        check("part paid refused", False)
    except fin.FinanceNotaError as exc:
        check("part paid refused", exc.http_status == 405)
    try:
        inv.create_invoice(ZAYEN, draft_body(cid), conn)
        check("zayen invoice denied", False)
    except fin.FinanceNotaError as exc:
        check("zayen invoice denied", exc.http_status == 403)
    report = inv.reports(AMANDA, conn)
    check("cash unknown", report["cash"] is None and report["profit_and_loss"] is None)
    check("ageing unknown", report["ar_ageing"] is None and report["margin"] is None and report["tax_position"] is None)
    desk = inv.desk_snapshot(AMANDA, conn)
    check("desk has real claim", desk["payment_unverified"] == 1 and desk["cash"] is None)
    page = fin.dispatch("GET", "/ggv/finance/invoices", {}, {}, AMANDA)
    check("invoice page", page.get("_html") is True)


def call(base: str, method: str, path: str, email: str | None):
    headers = {}
    data = None
    if email:
        headers["X-Wolf-Subject"] = email
    if method == "POST":
        headers["Content-Type"] = "application/json"
        data = b"{}"
    req = Request(base + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=10) as res:
            return res.status, res.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def test_http(db_path: Path) -> None:
    wire(db_path)
    import serve_beta as sb

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sb.BetaHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        status, raw = call(base, "GET", "/ggv/finance/invoices", "amanda@wolfcommand.net")
        text = raw.decode("utf-8", "replace")
        check("desktop invoice page", status == 200 and "+ New Invoice" in text and "Add line" in text)
        check("served page hides operator number", 'id="inv-number"' not in text and "Number assigned on issue" in text)
        check("mobile css served", status == 200 and "max-width: 430px" in text)
        status, _raw = call(base, "GET", "/amg/finance", "amanda@wolfcommand.net")
        check("amanda atrium denied", status == 403)
        status, _raw = call(base, "GET", "/ggv/finance", "laluzayen@gmail.com")
        check("zayen ggv finance denied", status == 403)
        status, _raw = call(base, "POST", "/api/ggv/finance/pay", "amanda@wolfcommand.net")
        check("amanda pay route denied", status == 405)
        status, raw = call(base, "GET", "/api/ggv/finance/entities", "amanda@wolfcommand.net")
        body = json.loads(raw.decode())
        check(
            "amanda entity payload",
            status == 200 and [row["id"] for row in body.get("finance_entities") or []] == ["GGV"],
        )
        status, raw = call(base, "GET", "/api/amg/finance", "laluzayen@gmail.com")
        body = json.loads(raw.decode())
        check(
            "zayen entity payload",
            status == 200 and [row["id"] for row in body.get("finance_entities") or []] == ["AMG"],
        )
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_concurrency(db_path: Path) -> None:
    wire(db_path)
    conn = fin.db_connect(db_path)
    try:
        start = int(inv.numbering_status(conn)["next_value"])
        cid = conn.execute(
            "SELECT counterparty_id FROM fin_counterparties WHERE entity_id='ENT-GGV' LIMIT 1"
        ).fetchone()[0]
        ids = []
        for _ in range(6):
            made = inv.create_invoice(AMANDA, draft_body(cid), conn)
            ids.append(made["invoice"]["invoice_id"])
    finally:
        conn.close()
    numbers: list[str] = []
    errors: list[str] = []
    lock = threading.Lock()

    def worker(invoice_id: str) -> None:
        local = fin.db_connect(db_path)
        try:
            result = inv.issue_invoice(AMANDA, invoice_id, local)
            with lock:
                numbers.append(str(result["invoice"]["invoice_number"]))
        except Exception as exc:  # noqa: BLE001
            with lock:
                errors.append(f"{type(exc).__name__}: {exc}")
        finally:
            local.close()

    threads = [threading.Thread(target=worker, args=(invoice_id,)) for invoice_id in ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    expected = [f"{start + offset:03d}A" for offset in range(6)]
    check("concurrency finished", all(not thread.is_alive() for thread in threads))
    check("concurrency no errors", errors == [], " | ".join(errors))
    check("concurrency no duplicates", len(numbers) == 6 and len(set(numbers)) == 6, str(numbers))
    check("concurrency matches sequence", sorted(numbers) == expected, f"{sorted(numbers)} != {expected}")


def main() -> int:
    test_static()
    tmp = ROOT / "state" / ".tmp-ggv-finance-invoice"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    db_path = tmp / "catalog.sqlite"
    shutil.copy(ROOT / "catalog" / "content_library.sqlite", db_path)
    wire(db_path)
    conn = fin.db_connect(db_path)
    try:
        test_flow(conn)
    finally:
        conn.close()
    test_concurrency(db_path)
    test_http(db_path)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
