#!/usr/bin/env python3
"""GGV Finance mobile nota — permission matrix and workflow. Beta catalog copy only."""
from __future__ import annotations

import base64
import json
import os
import shutil
import sqlite3
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import approvals as approvals  # noqa: E402
from core import evidence as evidence  # noqa: E402
from core import ggv_finance_nota as fin  # noqa: E402
from core import identity as identity  # noqa: E402
from core import rbac as rbac  # noqa: E402
from core import wolf_shell as shell  # noqa: E402

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
DEVI = "deviputu236@gmail.com"
MISA = "mlsary111@gmail.com"
CLIENT = "client.habitat@wolfcommand.net"

NOTA_TEXT = """Vendor: Bali Supplies
Invoice INV-100
Date: 2026-09-01
Total: 250000
Tax: 25000
Currency: IDR
Bank BCA 1234567890
"""


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def b64_file(name: str, content: bytes, content_type: str) -> dict:
    return {
        "filename": name,
        "content_type": content_type,
        "data_base64": base64.b64encode(content).decode("ascii"),
    }


def seed_client(db_path: Path) -> None:
    ts = "2026-09-24T00:00:00Z"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES ('PERS-CLIENT-HABITAT', 'Habitat client', 'Habitat client', 'ACTIVE', ?, ?)
        """,
        (ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_auth_identities (
          auth_identity_id, person_id, provider, identifier, status, is_primary, created_at, updated_at
        ) VALUES ('AUTH-CLIENT-HABITAT', 'PERS-CLIENT-HABITAT', 'email', ?, 'ACTIVE', 1, ?, ?)
        """,
        (CLIENT, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_roles (
          role_id, display_name, department_id, role_type, status, created_at, updated_at
        ) VALUES ('ROLE-GGV-CLIENT', 'GGV client', NULL, 'CLIENT', 'ACTIVE', ?, ?)
        """,
        (ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, location_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES (
          'POS-GGV-CLIENT', 'ROLE-GGV-CLIENT', 'ENT-GGV', NULL, NULL, NULL,
          'GGV client', 'ACTIVE', 1, ?, ?
        )
        """,
        (ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status, is_primary, created_at, updated_at
        ) VALUES ('ASG-GGV-CLIENT', 'PERS-CLIENT-HABITAT', 'POS-GGV-CLIENT', ?, NULL, 'ACTIVE', 1, ?, ?)
        """,
        (ts, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_assignment_scopes (
          assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
        ) VALUES ('ASG-GGV-CLIENT', 'SCOPE-GGV-ALL', ?, NULL, 'ACTIVE', ?, ?)
        """,
        (ts, ts, ts),
    )
    conn.commit()
    conn.close()


def wire(db_path: Path, store: Path) -> None:
    for module in (fin, evidence, approvals, identity, rbac):
        module.CATALOG_DB = db_path
    store.mkdir(parents=True, exist_ok=True)
    fin.set_media_root(store)


def test_static() -> None:
    html = (ROOT / "dashboards" / "ggv-finance.html").read_text(encoding="utf-8")
    low = html.lower()
    for label in ("Overview", "Notas / Bills", "Vendors", "History"):
        check(f"tab {label}", label in html)
    for label in ("Uploading", "Reading document", "Checking vendor", "Ready for review", "Saved"):
        check(f"progress {label}", label in html)
    check("boundary sentence", "Payment and full books live with Finance reconciliation later" in html)
    check("not a payment", "Entering a nota is not the same as paying it." in html)
    check("bank not verified", "Bank details seen on a document are not verified." in html)
    check("use existing", "Use existing" in html)
    check("create new", "Create new" in html)
    check("camera input", 'capture="environment"' in html)
    check("pdf input", ".pdf" in html)
    check("no name auth", "Matt" not in html and "Amanda" not in html)
    for banned in ("ocr", "rbac", "jwt", "sqlite", "entity_id", "staff_ready", "telegram retired"):
        check(f"no jargon {banned}", banned not in low)
    check("no wide table", "min-width: 1200" not in html and "overflow-x: scroll" not in low)
    check("touch target", "--touch: 44px" in html)
    grammar = shell.ggv_grammar()
    finance = next(item for item in grammar if item["key"] == "finance")
    check("grammar finance live", finance["href"] == "/ggv/finance" and finance["state"] == "live")
    check("amg finance still empty", next(item for item in shell.amg_grammar() if item["key"] == "finance")["state"] == "EMPTY")
    ops = (ROOT / "dashboards" / "ggv-ops-pack.html").read_text(encoding="utf-8")
    check("ops pack finance link", 'href="/ggv/finance"' in ops)
    source = (ROOT / "scripts" / "core" / "ggv_finance_nota.py").read_text(encoding="utf-8")
    check("no telegram client", "api.telegram" not in source and "telegram_retired\": True" not in source)
    check("zayen note in module", "not a ledger" in source.lower() or "not a ledger" in source)


def test_permissions(conn: sqlite3.Connection) -> None:
    fin.ensure_schema(conn)
    fin.ensure_rbac(conn, commit=True)
    allowed = {
        "PERS-MATT": True,
        "PERS-AMANDA": True,
        "PERS-HAIKAL": False,
        "PERS-MISA": False,
        "PERS-DEVI": False,
        "PERS-CLIENT-HABITAT": False,
        "": False,
    }
    for code in ("finance.nota.read", "finance.nota.create", "finance.nota.edit", "vendor.read", "vendor.create", "vendor.edit", "evidence.create"):
        for person, expect in allowed.items():
            got = fin.person_can(person or None, code, conn)
            check(f"{person or 'anonymous'} {code}", got is expect, str(got))
    held = conn.execute(
        """
        SELECT COUNT(*) FROM org_role_permissions rp
        JOIN org_permissions p ON p.permission_id = rp.permission_id
        WHERE p.code IN ('payment.approve', 'payment.execute', 'vendor.bank.change', 'finance.policy.admin')
          AND rp.role_id IN ('ROLE-MATT', 'ROLE-CONTENT-MGMT')
          AND rp.effect = 'ALLOW'
        """
    ).fetchone()[0]
    check("payment perms not granted to operating roles", held == 0, str(held))


def test_workflow(conn: sqlite3.Connection) -> None:
    amanda = "PERS-AMANDA"
    image = b64_file("photo.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")
    photo = fin.create_upload(amanda, [image], conn=conn)
    check("image upload saved", photo["stage"] == "uploading" and photo["preserved"] is True)
    read_photo = fin.read_upload(amanda, photo["upload_id"], conn=conn)
    amount = (read_photo["proposals"]["fields"] or {}).get("amount")
    check("photo does not invent amount", amount is None, str(amount))

    doc = b64_file("nota.txt", NOTA_TEXT.encode(), "text/plain")
    uploaded = fin.create_upload(amanda, [doc, b64_file("extra.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")], conn=conn)
    upload_id = uploaded["upload_id"]
    blob = conn.execute(
        "SELECT nas_rel_path FROM ggv_nota_files WHERE upload_id=? AND role='primary'",
        (upload_id,),
    ).fetchone()[0]
    full = fin.evidence_path(blob)
    full.unlink()
    try:
        fin.read_upload(amanda, upload_id, conn=conn)
        check("read failure raised", False)
    except fin.FinanceNotaError as exc:
        check("read failure preserves upload", exc.extra.get("preserved") is True and "do not upload" in str(exc).lower())
    row = conn.execute("SELECT stage, preserved FROM ggv_uploads WHERE upload_id=?", (upload_id,)).fetchone()
    check("upload row remains", row is not None and row[1] == 1)
    full.write_bytes(NOTA_TEXT.encode())
    read = fin.read_upload(amanda, upload_id, conn=conn)
    fields = read["proposals"]["fields"]
    check("read vendor", fields.get("vendor_name") == "Bali Supplies", str(fields))
    check("read invoice", fields.get("invoice_no") == "INV-100", str(fields))
    check("read amount", fields.get("amount") == "250000", str(fields))
    check("read date", fields.get("nota_date") == "2026-09-01")
    check("bank observed proposal", "1234567890" in (fields.get("bank_observed") or ""))
    checked = fin.check_vendor(amanda, upload_id, conn=conn)
    check("vendor not found message", "not found" in checked["message"].lower() or "No vendor" in checked["message"])
    created = fin.create_vendor(
        amanda,
        {"display_name": "Bali Supplies", "phone": "08123456789", "email": "bali@example.com"},
        conn=conn,
    )
    check("vendor created", created.get("created") is True and created["vendor"]["vendor_id"].startswith("VEND-"))
    vendor_id = created["vendor"]["vendor_id"]
    again = fin.create_vendor(
        amanda,
        {"display_name": "Bali Supplies", "phone": "08123456789"},
        conn=conn,
    )
    check("duplicate vendor warning", again.get("error") == "possible_duplicate_vendor" and again.get("matches"))
    separate = fin.create_vendor(
        amanda,
        {
            "display_name": "Bali Supplies",
            "phone": "08123456789",
            "duplicate_decision": "create_separate",
            "duplicate_reason": "Different outlet",
        },
        conn=conn,
    )
    check("separate vendor kept", separate.get("created") is True and separate["vendor"]["vendor_id"] != vendor_id)
    used = fin.create_vendor(
        amanda,
        {
            "display_name": "Bali Supplies",
            "duplicate_decision": "use_existing",
            "existing_vendor_id": vendor_id,
        },
        conn=conn,
    )
    check("use existing vendor", used.get("decision") == "use_existing" and used["vendor"]["vendor_id"] == vendor_id)
    renamed = fin.edit_vendor(amanda, vendor_id, {"display_name": "Bali Supplies"}, conn=conn)
    check("vendor edit", renamed["vendor"]["name"] == "Bali Supplies")
    try:
        fin.edit_vendor(amanda, vendor_id, {"bank_verified": True}, conn=conn)
        check("vendor bank verify refused", False)
    except fin.FinanceNotaError as exc:
        check("vendor bank verify refused", exc.http_status == 405)
    body = {
        "upload_id": upload_id,
        "vendor_id": vendor_id,
        "invoice_no": "INV-100",
        "date": "2026-09-01",
        "amount": "250000",
        "tax": "25000",
        "currency": "IDR",
        "category": "Supplies",
        "notes": "Checked on phone",
        "confirm": {"vendor": True, "date": True, "amount": True, "tax": True, "currency": True},
    }
    saved = fin.save_nota(amanda, body, conn=conn)
    check("saved ready", saved["nota"]["state"] == "ready", saved["nota"]["state"])
    check("saved message", saved["message"] == "Saved")
    check("bank observed not verified", saved["nota"]["bank_details"]["verified"] is False and saved["nota"]["bank_details"]["status"] == "OBSERVED")
    check("not paid", saved["nota"]["approved_for_payment"] is False and saved["nota"]["payment_verified"] is False)
    nota_id = saved["nota"]["nota_id"]
    second = fin.create_upload(amanda, [doc], conn=conn)
    fin.read_upload(amanda, second["upload_id"], conn=conn)
    fin.check_vendor(amanda, second["upload_id"], conn=conn)
    dup_body = dict(body)
    dup_body["upload_id"] = second["upload_id"]
    dup = fin.save_nota(amanda, dup_body, conn=conn)
    check("duplicate nota warning", dup.get("error") == "possible_duplicate_nota" and dup.get("preserved") is True)
    dup_body["duplicate_decision"] = "create_separate"
    dup_body["duplicate_reason"] = "Second page of the same delivery"
    separate_nota = fin.save_nota(amanda, dup_body, conn=conn)
    check("separate nota saved", separate_nota.get("saved") is True and separate_nota["nota"]["nota_id"] != nota_id)
    edited = fin.edit_nota(
        amanda,
        nota_id,
        {
            "vendor_id": vendor_id,
            "invoice_no": "INV-100",
            "date": "2026-09-02",
            "amount": "250000",
            "currency": "IDR",
            "category": "Supplies",
            "notes": "Date corrected",
            "confirm": {"vendor": True, "date": True, "amount": True, "currency": True},
        },
        conn=conn,
    )
    check("edited date", edited["nota"]["date"] == "2026-09-02")
    try:
        fin.edit_nota(amanda, nota_id, {"workflow_state": "payment_verified", "confirm": {}}, conn=conn)
        check("money state refused", False)
    except fin.FinanceNotaError as exc:
        check("money state refused", exc.http_status == 405)
    submitted = fin.submit_nota(amanda, nota_id, conn=conn)
    check("submitted waiting", submitted["nota"]["state"] == "waiting_approval", submitted["nota"]["state"])
    check("submit is not payment", "not a payment" in submitted["message"].lower())
    check("submit flags", submitted["nota"]["approved_for_payment"] is False and submitted["payment_execute"] is False)
    found = fin.search_history(amanda, {"invoice": ["INV-100"], "category": ["Supplies"]}, conn=conn)
    check("history search", any(item["nota_id"] == nota_id for item in found["results"]))
    board = fin.overview(amanda, conn=conn)
    check("overview needs real rows", board["waiting_approval"] >= 1 and board["payment_unverified"] >= 1)
    check("no fake pnl", "pnl" not in board and "cash" not in board and "ageing" not in board)
    check("honesty locked", board["staff_ready"] is False and board["commissioned"] is False and board["telegram_retired"] is False)
    try:
        fin.dispatch("POST", "/api/ggv/finance/pay", {}, {}, amanda)
        check("pay refused", False)
    except fin.FinanceNotaError as exc:
        check("pay refused", exc.code == "payment_refused" and exc.http_status == 405)
    try:
        fin.dispatch("POST", f"/api/ggv/finance/vendors/{vendor_id}/bank", {}, {"account": "1"}, amanda)
        check("bank change refused", False)
    except fin.FinanceNotaError as exc:
        check("bank change refused", exc.code == "payment_refused")
    try:
        fin.overview("PERS-HAIKAL", conn=conn)
        check("haikal overview denied", False)
    except fin.FinanceNotaError as exc:
        check("haikal overview denied", exc.http_status == 403)


def call(base: str, method: str, path: str, email: str | None, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    headers = {}
    if email:
        headers["X-Wolf-Subject"] = email
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = Request(base + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=10) as res:
            raw = res.read()
            return res.status, raw, res.headers.get("Content-Type", "")
    except HTTPError as exc:
        return exc.code, exc.read(), exc.headers.get("Content-Type", "")


def test_http(db_path: Path, store: Path) -> None:
    wire(db_path, store)
    import serve_beta as sb

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sb.BetaHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        cases = [
            ("matt page", "GET", "/ggv/finance", MATT, 200),
            ("amanda page", "GET", "/ggv/finance", AMANDA, 200),
            ("amanda hidden html", "GET", "/ggv-finance.html", AMANDA, 200),
            ("haikal page", "GET", "/ggv/finance", HAIKAL, 403),
            ("haikal hidden", "GET", "/dashboards/ggv-finance.html", HAIKAL, 403),
            ("devi page", "GET", "/ggv/finance", DEVI, 403),
            ("misa page", "GET", "/ggv/finance", MISA, 403),
            ("anon page", "GET", "/ggv/finance", None, 403),
            ("client page", "GET", "/ggv/finance", CLIENT, 403),
            ("matt overview", "GET", "/api/ggv/finance/overview", MATT, 200),
            ("amanda overview", "GET", "/api/ggv/finance/overview", AMANDA, 200),
            ("haikal overview", "GET", "/api/ggv/finance/overview", HAIKAL, 403),
            ("anon overview", "GET", "/api/ggv/finance/overview", None, 403),
            ("client overview", "GET", "/api/ggv/finance/overview", CLIENT, 403),
            ("devi vendors", "GET", "/api/ggv/finance/vendors", DEVI, 403),
        ]
        for name, method, path, email, expect in cases:
            status, raw, _ctype = call(base, method, path, email)
            check(name, status == expect, f"status={status} body={raw[:180]!r}")
        status, raw, ctype = call(base, "GET", "/ggv/finance", AMANDA)
        text = raw.decode("utf-8", "replace")
        check("amanda html shell", status == 200 and "Notas / Bills" in text and "wolfnav" in text, ctype)
        status, raw, _ctype = call(base, "POST", "/api/ggv/finance/pay", MATT, {})
        check("matt pay api refused", status == 405)
        status, raw, _ctype = call(
            base,
            "POST",
            "/api/ggv/finance/uploads",
            HAIKAL,
            {"files": [b64_file("a.txt", b"Total: 10", "text/plain")]},
        )
        check("haikal upload denied", status == 403)
        status, raw, _ctype = call(
            base,
            "POST",
            "/api/ggv/finance/uploads",
            CLIENT,
            {"files": [b64_file("a.txt", b"Total: 10", "text/plain")]},
        )
        check("client upload denied", status == 403)
        status, raw, _ctype = call(
            base,
            "POST",
            "/api/ggv/finance/uploads",
            None,
            {"files": [b64_file("a.txt", b"Total: 10", "text/plain")]},
        )
        check("anon upload denied", status == 403)
        status, raw, _ctype = call(
            base,
            "POST",
            "/api/ggv/finance/notas",
            AMANDA,
            {"person_id": "PERS-MATT", "upload_id": "nope"},
        )
        check("spoof refused", status == 400)
        up_status, up_raw, _ctype = call(
            base,
            "POST",
            "/api/ggv/finance/uploads",
            MATT,
            {"files": [b64_file("nota.txt", NOTA_TEXT.encode(), "text/plain")]},
        )
        up = json.loads(up_raw.decode())
        check("matt api upload", up_status == 200 and up.get("upload_id"), up_raw[:200].decode())
        if up.get("upload_id"):
            read_status, read_raw, _ctype = call(
                base, "POST", f"/api/ggv/finance/uploads/{up['upload_id']}/read", MATT, {}
            )
            read = json.loads(read_raw.decode())
            check(
                "matt api read",
                read_status == 200 and (read.get("proposals") or {}).get("fields", {}).get("amount") == "250000",
                read_raw[:240].decode(),
            )
    finally:
        httpd.shutdown()
        httpd.server_close()


def main() -> int:
    test_static()
    tmp = ROOT / "state" / ".tmp-ggv-finance-nota"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    db_path = tmp / "catalog.sqlite"
    store = tmp / "blobs"
    shutil.copy(ROOT / "catalog" / "content_library.sqlite", db_path)
    seed_client(db_path)
    wire(db_path, store)
    conn = fin.db_connect(db_path)
    try:
        test_permissions(conn)
        test_workflow(conn)
    finally:
        conn.close()
    test_http(db_path, store)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
