#!/usr/bin/env python3
"""GGV-NOTA-CAPTURE-1 — mobile review, local OCR, UNKNOWN, isolation."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import approvals  # noqa: E402
from core import evidence  # noqa: E402
from core import ggv_finance_nota as fin  # noqa: E402
from core import ggv_nota_local_read as local_read  # noqa: E402
from core import identity  # noqa: E402
from core import rbac  # noqa: E402

PASS = 0
FAIL = 0
MATT_NOTA = Path(
    "/Users/wolfterminal/ggv-finance-20261006-evidence/HUMAN-FAIL-NOTA-20261006/ORIGINAL-COPY-FILE-01E2F5C9CF7B-image.jpg"
)
EXPECTED_SHA = "1f5c392019d0ea314ba7a1449ea3349d0167862a4d01dca1a70e7f167de134e0"
AMANDA = "PERS-AMANDA"
ZAYEN = "PERS-ZAYEN"
MATT = "PERS-MATT"
RECEIPT_OCR = """UMA BLU
LOMBOK TENGAH KAB
DATE 5 Oct 2026
REF NO: 000064002219
Rp510.000
"""


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def wire(db_path: Path, store: Path) -> None:
    for module in (fin, evidence, approvals, identity, rbac):
        module.CATALOG_DB = db_path
    store.mkdir(parents=True, exist_ok=True)
    fin.set_media_root(store)


def test_html_markup() -> None:
    html = (ROOT / "dashboards" / "ggv-finance.html").read_text(encoding="utf-8")
    for needle in (
        "SAVE FOR LATER",
        "CONFIRM NOTA",
        "MORE VENDOR DETAILS",
        "nota-action-bar",
        "action-row",
        "Review Wolf's reading",
        "EXTRACTED",
        "CHECK THIS",
        "SUGGESTED MATCH",
        "NOT READ",
        'type="date"',
        "IDR (default)",
        "env(safe-area-inset-bottom)",
        "function resetReviewForm",
        "nota-result",
        "nota-action-msg",
        "date-raw-hint",
        "Same nota — use this one",
        "HUMAN-CONFIRMED",
        "Nota says:",
    ):
        check(f"markup {needle}", needle in html)


def test_unknown_and_blocking(conn: sqlite3.Connection) -> None:
    body = {
        "upload_id": "skip",
        "vendor_id": "VEND-X",
        "invoice_no": fin.UNKNOWN_SENTINEL,
        "date": "2026-10-05",
        "amount": "510000",
        "tax": fin.UNKNOWN_SENTINEL,
        "currency": "IDR",
        "category": fin.UNKNOWN_SENTINEL,
        "confirm": {"vendor": True, "date": True, "amount": True, "tax": True, "currency": True, "category": True},
    }
    fields = fin._apply_nota_fields(body)
    check("unknown invoice stored", fields["invoice_no"] == fin.UNKNOWN_SENTINEL)
    check("unknown tax stored", fields["tax"] == fin.UNKNOWN_SENTINEL)
    check("unknown category stored", fields["category"] == fin.UNKNOWN_SENTINEL)
    check("idr default", fields["currency"] == "IDR")
    check("blocking set documented", "vendor_id" in fin.BLOCKING_CONFIRM_FIELDS)
    state = fin._state_for(fields)
    check("ready when vendor date amount confirmed", state == "ready", state)


def test_extraction_fixture() -> None:
    fixture = ROOT / "state" / ".tmp-nota1-fixture.txt"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(RECEIPT_OCR, encoding="utf-8")
    os.environ["GGV_NOTA_OCR_FIXTURE"] = str(fixture)
    proposal = fin.propose_from_bytes(b"\xff\xd8\xff", "image/jpeg", "nota.jpg")
    fields = proposal["fields"]
    check("fixture vendor", fields.get("vendor_name") == "UMA BLU", str(fields))
    check("fixture amount", fields.get("amount") == "510000", str(fields))
    check("fixture date", fields.get("nota_date") == "2026-10-05", str(fields))
    check("fixture currency idr", fields.get("currency") == "IDR")
    check("provenance extracted", proposal.get("provenance", {}).get("amount") == "extracted")
    os.environ.pop("GGV_NOTA_OCR_FIXTURE", None)
    fixture.unlink(missing_ok=True)


def test_extraction_failure_message() -> None:
    proposal = fin.propose_from_text("")
    check("empty not read", proposal["provenance"]["amount"] == "not_read")
    check("failure message honest", "couldn't read" in fin.propose_from_bytes(b"\xff\xd8\xff\xd9", "image/jpeg", "x.jpg")["message"].lower())


def test_garbled_ocr_not_truncated() -> None:
    cases = [
        ("Total: Rp51O.000", "amount", "51O.000"),
        ("Total: EUR10O,50", "amount", "10O,50"),
        ("Tax: Rp1O.000", "tax", "1O.000"),
    ]
    for text, key, expected_raw in cases:
        proposal = fin.propose_from_text(text)
        fields = proposal["fields"]
        check(f"garbled {key} not normalized {text!r}", fields.get(key) is None, str(fields))
        check(f"garbled {key} raw kept {text!r}", fields.get(f"{key}_raw") == expected_raw, str(fields))
        check(
            f"garbled {key} not read_from_document {text!r}",
            proposal["confidence"].get(key) != "read_from_document",
            str(proposal["confidence"]),
        )


def test_tax_only_does_not_invent_total() -> None:
    proposal = fin.propose_from_text("Vendor: Shop\nDate: 2026-10-06\nTax: Rp10000")
    fields = proposal["fields"]
    check("tax-only amount absent", fields.get("amount") is None, str(fields))
    check("tax-only amount missing", proposal["confidence"].get("amount") == "missing")
    check("tax-only tax extracted", fields.get("tax") == "10000", str(fields))


def test_unicode_corruption_not_truncated() -> None:
    proposal = fin.propose_from_text("Vendor: Shop\nDate: 2026-10-06\nTotal: Rp51\ufffd000")
    fields = proposal["fields"]
    check("unicode amount absent", fields.get("amount") is None, str(fields))
    check("unicode raw kept", fields.get("amount_raw") == "51\ufffd000", str(fields))
    check("unicode check_this", proposal["confidence"].get("amount") == "check_this")


def test_minimal_vendor(conn: sqlite3.Connection) -> None:
    created = fin.create_vendor(AMANDA, {"display_name": "Uma Blu"}, conn=conn)
    check("minimal vendor", created.get("created") is True and created["vendor"]["name"] == "Uma Blu")


def test_unknown_invoice_not_duplicate(conn: sqlite3.Connection) -> None:
    vend = fin.create_vendor(AMANDA, {"display_name": "Daily Supplies"}, conn=conn)
    vendor_id = vend["vendor"]["vendor_id"]
    up1 = fin.create_upload(
        AMANDA,
        [{"filename": "a.txt", "content_type": "text/plain", "data_base64": __import__("base64").b64encode(b"x").decode()}],
        conn=conn,
    )
    body = {
        "upload_id": up1["upload_id"],
        "vendor_id": vendor_id,
        "invoice_no": fin.UNKNOWN_SENTINEL,
        "date": "2026-10-05",
        "amount": "510000",
        "currency": "IDR",
        "confirm": {"vendor": True, "date": True, "amount": True, "currency": True},
    }
    fin.save_nota(AMANDA, body, conn=conn)
    up2 = fin.create_upload(
        AMANDA,
        [{"filename": "b.txt", "content_type": "text/plain", "data_base64": __import__("base64").b64encode(b"y").decode()}],
        conn=conn,
    )
    body2 = {**body, "upload_id": up2["upload_id"]}
    second = fin.save_nota(AMANDA, body2, conn=conn)
    check("unknown invoice not duplicate block", second.get("error") != "possible_duplicate_nota", str(second))


def test_fuzzy_vendor_duplicate_guard(conn: sqlite3.Connection) -> None:
    fin.create_vendor(AMANDA, {"display_name": "Uma Blu"}, conn=conn)
    dup = fin.create_vendor(AMANDA, {"display_name": "Ima Blu"}, conn=conn)
    check("fuzzy vendor caught", dup.get("error") == "possible_duplicate_vendor", str(dup))


def test_check_this_provenance() -> None:
    proposal = fin.propose_from_text("Vendor: Shop\nTanggal 05/10/2026\nTotal: Rp510.000")
    check("slash date check_this", proposal["provenance"].get("nota_date") == "check_this")
    check("slash date iso candidate", proposal["fields"].get("nota_date") == "2026-10-05", str(proposal["fields"]))
    check("slash date raw kept", proposal["fields"].get("nota_date_raw") == "05/10/2026")
    check("slash date low confidence", "nota_date" in proposal.get("low_confidence", []))


def test_bare_month_date() -> None:
    proposal = fin.propose_from_text("UMA BLU\n06 Okt 2026\nRp510.000")
    check("bare month date", proposal["fields"].get("nota_date") == "2026-10-06", str(proposal["fields"]))


def test_currency_source_default() -> None:
    fields = fin._apply_nota_fields(
        {
            "vendor_id": "VEND-X",
            "date": "2026-10-05",
            "amount": "510000",
            "currency": "",
            "confirm": {"vendor": True, "date": True, "amount": True, "currency": False},
        }
    )
    check("currency default idr", fields["currency"] == "IDR")
    check("currency source default", fields.get("currency_source") == "default")


def test_extracted_usd_persisted_not_idr() -> None:
    proposal = fin.propose_from_text("Vendor: Shop\nDate: 2026-10-06\nTOTAL USD 120.00")
    check("usd proposal currency", proposal["fields"].get("currency") == "USD", str(proposal["fields"]))
    body = {
        "vendor_id": "VEND-X",
        "date": "2026-10-06",
        "amount": "120.00",
        "currency": "USD",
        "confirm": {"vendor": True, "date": True, "amount": True, "currency": False},
    }
    fields = fin._apply_nota_fields(body)
    fin._reconcile_currency_from_proposal(fields, proposal)
    check("usd stored not idr", fields["currency"] == "USD", str(fields))
    check("usd source extracted", fields.get("currency_source") == "extracted")
    check("usd blocks ready", fin._state_for(fields) == "needs_review", fields.get("currency_source"))


def test_extracted_idr_source_not_default() -> None:
    proposal = fin.propose_from_text(RECEIPT_OCR)
    body = {
        "vendor_id": "VEND-X",
        "date": "2026-10-05",
        "amount": "510000",
        "currency": "IDR",
        "confirm": {"vendor": True, "date": True, "amount": True, "currency": False},
    }
    fields = fin._apply_nota_fields(body)
    fin._reconcile_currency_from_proposal(fields, proposal)
    check("idr extracted source", fields.get("currency_source") == "extracted", str(fields))
    check("idr extracted ready", fin._state_for(fields) == "ready", fields.get("workflow_state"))


def test_unknown_provenance_on_read_path() -> None:
    proposal = fin.propose_from_text("UMA BLU\n06 Okt 2026\nRp510.000")
    prov = proposal.get("provenance") or {}
    check("invoice unknown provenance", prov.get("invoice_no") == "unknown", str(prov))
    body = {
        "vendor_id": "VEND-X",
        "date": proposal["fields"]["nota_date"],
        "amount": proposal["fields"]["amount"],
        "currency": proposal["fields"]["currency"],
        "invoice_no": fin.UNKNOWN_SENTINEL,
        "tax": fin.UNKNOWN_SENTINEL,
        "category": fin.UNKNOWN_SENTINEL,
        "confirm": {"vendor": True, "date": True, "amount": True, "currency": False},
    }
    fields = fin._apply_nota_fields(body)
    check("unknown invoice stored from read", fields["invoice_no"] == fin.UNKNOWN_SENTINEL)


def test_digit_only_vendor_names_allowed(conn: sqlite3.Connection) -> None:
    fin.create_vendor(AMANDA, {"display_name": "Toko Bangunan 1"}, conn=conn)
    second = fin.create_vendor(AMANDA, {"display_name": "Toko Bangunan 2"}, conn=conn)
    check("digit-only vendor allowed", second.get("created") is True, str(second))


def test_isolation(conn: sqlite3.Connection) -> None:
    check("amanda can create", fin.person_can(AMANDA, "finance.nota.create", conn))
    check("zayen denied", not fin.person_can(ZAYEN, "finance.nota.read", conn))
    try:
        fin.overview(ZAYEN, conn=conn)
        check("zayen overview denied", False)
    except fin.FinanceNotaError as exc:
        check("zayen overview denied", exc.http_status == 403)


def test_hash_and_workflow(conn: sqlite3.Connection, store: Path) -> None:
    doc = {
        "filename": "nota.txt",
        "content_type": "text/plain",
        "data_base64": __import__("base64").b64encode(
            b"Vendor: Hash Test\nDate: 2026-10-05\nTotal: 100000\nCurrency: IDR\n"
        ).decode(),
    }
    up = fin.create_upload(AMANDA, [doc], conn=conn)
    row = conn.execute(
        "SELECT sha256 FROM ggv_nota_files WHERE upload_id=?",
        (up["upload_id"],),
    ).fetchone()
    sha_before = row[0]
    fin.read_upload(AMANDA, up["upload_id"], conn=conn)
    fin.check_vendor(AMANDA, up["upload_id"], conn=conn)
    vend = fin.create_vendor(AMANDA, {"display_name": "Hash Test"}, conn=conn)
    body = {
        "upload_id": up["upload_id"],
        "vendor_id": vend["vendor"]["vendor_id"],
        "date": "2026-10-05",
        "amount": "100000",
        "currency": "IDR",
        "confirm": {"vendor": True, "date": True, "amount": True, "currency": True},
    }
    saved = fin.save_nota(AMANDA, body, conn=conn)
    sha_after = conn.execute(
        "SELECT sha256 FROM ggv_nota_files WHERE upload_id=?",
        (up["upload_id"],),
    ).fetchone()[0]
    check("hash preserved", sha_before == sha_after, f"{sha_before} vs {sha_after}")
    nota_id = saved["nota"]["nota_id"]
    submitted = fin.submit_nota(AMANDA, nota_id, conn=conn)
    check("confirm transition", submitted["nota"]["state"] == "waiting_approval")


def test_unknown_confirm_stays_needs_review(conn: sqlite3.Connection) -> None:
    vend = fin.create_vendor(AMANDA, {"display_name": "Unknown Amount Vendor"}, conn=conn)
    up = fin.create_upload(
        AMANDA,
        [
            {
                "filename": "nota.txt",
                "content_type": "text/plain",
                "data_base64": __import__("base64").b64encode(b"Vendor: X\nDate: 2026-10-06\n").decode(),
            }
        ],
        conn=conn,
    )
    body = {
        "upload_id": up["upload_id"],
        "vendor_id": vend["vendor"]["vendor_id"],
        "date": "2026-10-06",
        "amount": fin.UNKNOWN_SENTINEL,
        "currency": "IDR",
        "confirm": {"vendor": True, "date": True, "amount": True, "currency": True},
    }
    nota_id = fin.save_nota(AMANDA, body, conn=conn)["nota"]["nota_id"]
    fin.confirm_nota(AMANDA, nota_id, {}, conn=conn)
    row = conn.execute("SELECT amount, amount_confirmed, workflow_state FROM ggv_notas WHERE nota_id=?", (nota_id,)).fetchone()
    check("unknown amount stored", row[0] == fin.UNKNOWN_SENTINEL)
    check("unknown amount not confirmed", int(row[1] or 0) == 0)
    check("unknown amount not ready", row[2] == "needs_review", row[2])


def test_vendor_use_existing_no_matches(conn: sqlite3.Connection) -> None:
    try:
        fin.create_vendor(
            AMANDA,
            {"display_name": "Unique No Match", "duplicate_decision": "use_existing"},
            conn=conn,
        )
        check("use_existing without matches rejected", False)
    except fin.FinanceNotaError as exc:
        check("use_existing without matches rejected", exc.code == "vendor_not_found")


def test_approval_and_terminal_lock(conn: sqlite3.Connection) -> None:
    vend = fin.create_vendor(AMANDA, {"display_name": "Lock Test Vendor"}, conn=conn)
    vendor_id = vend["vendor"]["vendor_id"]
    alt = fin.create_vendor(AMANDA, {"display_name": "Alt Payee"}, conn=conn)["vendor"]["vendor_id"]
    up = fin.create_upload(
        AMANDA,
        [
            {
                "filename": "lock.txt",
                "content_type": "text/plain",
                "data_base64": __import__("base64").b64encode(b"Lock test nota\n").decode(),
            }
        ],
        conn=conn,
    )
    body = {
        "upload_id": up["upload_id"],
        "vendor_id": vendor_id,
        "date": "2026-10-06",
        "amount": "510000",
        "currency": "IDR",
        "confirm": {"vendor": True, "date": True, "amount": True, "currency": True},
    }
    saved = fin.save_nota(AMANDA, body, conn=conn)
    nota_id = saved["nota"]["nota_id"]
    fin.submit_nota(AMANDA, nota_id, conn=conn)
    before = conn.execute(
        "SELECT vendor_id,currency,amount,approval_request_id FROM ggv_notas WHERE nota_id=?",
        (nota_id,),
    ).fetchone()
    for key, value in [
        ("currency", "USD"),
        ("vendor_id", alt),
        ("vendor_id", ""),
        ("currency", "UNKNOWN"),
    ]:
        fin.edit_nota(AMANDA, nota_id, {key: value}, conn=conn)
        after = conn.execute(
            "SELECT vendor_id,currency,amount,approval_request_id FROM ggv_notas WHERE nota_id=?",
            (nota_id,),
        ).fetchone()
        check(f"pending lock {key}", tuple(after) == tuple(before), f"{before} -> {after}")
    for state in ("approved", "paid_claimed", "payment_verified"):
        conn.execute("UPDATE ggv_notas SET workflow_state=? WHERE nota_id=?", (state, nota_id))
        conn.commit()
        try:
            fin.edit_nota(AMANDA, nota_id, {"amount": "999999"}, conn=conn)
            locked = conn.execute("SELECT amount FROM ggv_notas WHERE nota_id=?", (nota_id,)).fetchone()[0]
            check(f"terminal lock {state}", locked == "510000", f"amount={locked}")
        except fin.FinanceNotaError:
            check(f"terminal lock {state}", True)


def test_matt_nota_image() -> None:
    if not MATT_NOTA.is_file():
        check("matt nota fixture present", False, "missing copy")
        return
    data = MATT_NOTA.read_bytes()
    check("matt sha256", hashlib.sha256(data).hexdigest() == EXPECTED_SHA)
    text, meta = local_read.read_image_bytes(data)
    proposal = fin.propose_from_bytes(data, "image/jpeg", "image.jpg")
    check("local reader used", meta.get("reader") in {"macos_vision", "tesseract", "fixture"})
    check("read something from matt nota", proposal.get("read_something") is True, f"chars={len(text)} meta={meta}")
    fields = proposal.get("fields") or {}
    check("matt vendor extracted", "UMA" in (fields.get("vendor_name") or ""), str(fields))
    check("matt amount extracted", fields.get("amount") == "510000", str(fields))


def test_stale_edit_after_submit(conn: sqlite3.Connection) -> None:
    vend = fin.create_vendor(AMANDA, {"display_name": "Race Vendor"}, conn=conn)
    up = fin.create_upload(
        AMANDA,
        [
            {
                "filename": "race.txt",
                "content_type": "text/plain",
                "data_base64": __import__("base64").b64encode(b"Race test\n").decode(),
            }
        ],
        conn=conn,
    )
    body = {
        "upload_id": up["upload_id"],
        "vendor_id": vend["vendor"]["vendor_id"],
        "date": "2026-10-06",
        "amount": "510000",
        "currency": "IDR",
        "confirm": {"vendor": True, "date": True, "amount": True, "currency": True},
    }
    nota_id = fin.save_nota(AMANDA, body, conn=conn)["nota"]["nota_id"]
    original = fin._apply_nota_fields
    submitted = False

    def submit_after_read(body_in):
        nonlocal submitted
        if not submitted:
            submitted = True
            fin.submit_nota(AMANDA, nota_id, conn=conn)
        return original(body_in)

    import unittest.mock as mock

    with mock.patch.object(fin, "_apply_nota_fields", side_effect=submit_after_read):
        try:
            fin.edit_nota(AMANDA, nota_id, {"amount": "999999"}, conn=conn)
            check("stale edit rejected", False, "no 409")
        except fin.FinanceNotaError as exc:
            check("stale edit rejected", exc.http_status == 409, exc.code)
    row = conn.execute(
        "SELECT workflow_state, amount FROM ggv_notas WHERE nota_id=?",
        (nota_id,),
    ).fetchone()
    check("amount unchanged after stale edit", row[1] == "510000", str(row))
    check("still waiting approval", row[0] == "waiting_approval", str(row))


def main() -> int:
    test_html_markup()
    test_extraction_fixture()
    test_extraction_failure_message()
    test_garbled_ocr_not_truncated()
    test_tax_only_does_not_invent_total()
    test_unicode_corruption_not_truncated()
    test_check_this_provenance()
    test_bare_month_date()
    test_currency_source_default()
    test_extracted_usd_persisted_not_idr()
    test_extracted_idr_source_not_default()
    test_unknown_provenance_on_read_path()
    td = tempfile.mkdtemp(prefix="ggv-nota1-", dir="/tmp")
    db_path = Path(td) / "catalog.sqlite"
    store = Path(td) / "blobs"
    shutil.copy(ROOT / "catalog" / "content_library.sqlite", db_path)
    wire(db_path, store)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        fin.ensure_schema(conn)
        fin.ensure_rbac(conn, commit=True)
        test_unknown_and_blocking(conn)
        test_minimal_vendor(conn)
        test_unknown_invoice_not_duplicate(conn)
        test_fuzzy_vendor_duplicate_guard(conn)
        test_digit_only_vendor_names_allowed(conn)
        test_isolation(conn)
        test_hash_and_workflow(conn, store)
        test_unknown_confirm_stays_needs_review(conn)
        test_vendor_use_existing_no_matches(conn)
        test_approval_and_terminal_lock(conn)
        test_stale_edit_after_submit(conn)
    finally:
        conn.close()
        shutil.rmtree(td, ignore_errors=True)
    test_matt_nota_image()
    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
