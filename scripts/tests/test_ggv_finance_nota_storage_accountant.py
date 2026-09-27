#!/usr/bin/env python3
"""GGV Finance nota storage + external accountant. Beta catalog copy only."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import shutil
import sqlite3
import sys
import threading
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
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
from core import nas_library as nas  # noqa: E402
from core import rbac as rbac  # noqa: E402

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
ACCT = "fixture.ggv.external.accountant@wolfcommand.test"
ACCT_ID = "PERS-GGV-EXT-ACCT-FIXTURE"

NOTA_TEXT = """Vendor: Bali Supplies
Invoice INV-100
Date: 2026-09-01
Total: 250000
Currency: IDR
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


def wire(db_path: Path, store: Path) -> None:
    for module in (fin, evidence, approvals, identity, rbac):
        module.CATALOG_DB = db_path
    store.mkdir(parents=True, exist_ok=True)
    fin.set_media_root(store)
    fin.set_legacy_blob_dir(None)


def seed_accountant(conn: sqlite3.Connection) -> None:
    ts = "2026-09-24T00:00:00Z"
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES (?, 'GGV external accountant fixture', 'GGV external accountant fixture', 'ACTIVE', ?, ?)
        """,
        (ACCT_ID, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_auth_identities (
          auth_identity_id, person_id, provider, identifier, status, is_primary, created_at, updated_at
        ) VALUES ('AUTH-GGV-EXT-ACCT-FIXTURE', ?, 'email', ?, 'ACTIVE', 1, ?, ?)
        """,
        (ACCT_ID, ACCT, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status, is_primary, created_at, updated_at
        ) VALUES ('ASG-GGV-EXT-ACCT-FIXTURE', ?, 'POS-GGV-EXT-ACCT', ?, NULL, 'ACTIVE', 1, ?, ?)
        """,
        (ACCT_ID, ts, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_assignment_scopes (
          assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
        ) VALUES ('ASG-GGV-EXT-ACCT-FIXTURE', 'SCOPE-GGV-FINANCE', ?, NULL, 'ACTIVE', ?, ?)
        """,
        (ts, ts, ts),
    )
    conn.commit()


def test_contract_and_ui() -> None:
    html = (ROOT / "dashboards" / "ggv-finance.html").read_text(encoding="utf-8")
    check("accountant tab", "Accountant" in html)
    check("year month copy", "Year, then month, then each nota" in html)
    check("export is a copy", "Each original file stays separate." in html)
    check("no fake total sentence", "No accounting total" in html)
    check("backup label honest", "Backup:" in html and "BACKED UP" not in html)
    source = (ROOT / "scripts" / "core" / "ggv_finance_nota.py").read_text(encoding="utf-8")
    check("local store is not canonical", "STORE_DIR =" not in source)
    check("b2 not proven", "B2_FINANCE_PROVEN = False" in source)
    saved = fin._MEDIA_ROOT
    fin.set_media_root(None)
    try:
        root = fin.finance_nota_root()
        check(
            "path under media library",
            root == nas.MEDIA_LIBRARY / "Finance" / "GGV" / "Notas",
            str(root),
        )
        check("no second nas root", str(root).startswith(str(nas.MEDIA_LIBRARY)))
    finally:
        fin.set_media_root(saved)


def test_storage_and_accountant(conn: sqlite3.Connection, store: Path, legacy: Path) -> None:
    fin.ensure_schema(conn)
    seeded = fin.ensure_rbac(conn, commit=True)
    check("role seeded without a person", seeded.get("accountant_person_seeded") is False)
    assigned = conn.execute(
        """
        SELECT COUNT(*) FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        WHERE p.role_id='ROLE-GGV-EXTERNAL-ACCOUNTANT' AND a.status='ACTIVE'
        """
    ).fetchone()[0]
    check("no real accountant assignment", assigned == 0, str(assigned))
    role = conn.execute(
        "SELECT display_name FROM org_roles WHERE role_id='ROLE-GGV-EXTERNAL-ACCOUNTANT'"
    ).fetchone()
    check("role name is a seat", role is not None and role[0] == "GGV external accountant", str(role))
    scope = conn.execute(
        """
        SELECT target_id FROM org_scope_targets
        WHERE scope_id='SCOPE-GGV-FINANCE' AND target_type='entity'
        """
    ).fetchone()
    check("scope is GGV", scope is not None and scope[0] == "ENT-GGV", str(scope))

    seed_accountant(conn)
    allow = {
        "finance.nota.read": True,
        "vendor.read": True,
        "finance.nota.review": True,
        "finance.evidence.export": True,
        "finance.nota.create": False,
        "finance.nota.edit": False,
        "vendor.create": False,
        "vendor.edit": False,
        "evidence.create": False,
        "payment.approve": False,
        "payment.execute": False,
        "vendor.bank.change": False,
        "finance.policy.admin": False,
    }
    for code, expect in allow.items():
        got = fin.person_can(ACCT_ID, code, conn)
        check(f"accountant {code}", got is expect, str(got))
    check(
        "accountant read denied on other entity",
        rbac.can(ACCT_ID, "finance.nota.read", {"entity_id": "ENT-BZG"}, conn=conn) is False,
    )
    check("b2 flag stays false", fin.B2_FINANCE_PROVEN is False)
    try:
        fin.assert_backup_state("BACKED_UP", proof={"proof_id": "not-real"})
        check("backed up refused without proof", False)
    except fin.FinanceNotaError as exc:
        check("backed up refused without proof", exc.code == "backup_unproven")
    check("pending is allowed", fin.assert_backup_state("PENDING") == "PENDING")
    check("unknown is allowed", fin.assert_backup_state("UNKNOWN") == "UNKNOWN")

    missing = store / "missing-nas-root"
    fin.set_media_root(missing)
    try:
        fin.create_upload("PERS-AMANDA", [b64_file("a.txt", b"Total: 1", "text/plain")], conn=conn)
        check("unmounted storage blocks upload", False)
    except fin.FinanceNotaError as exc:
        check("unmounted storage blocks upload", exc.code == "nas_unmounted", exc.code)
    leaked = list(fin.LEGACY_BLOB_DIR.rglob("*")) if fin.LEGACY_BLOB_DIR.exists() else []
    check("unmounted upload did not write local blobs", not any(p.is_file() for p in leaked))
    fin.set_media_root(store)

    amanda = "PERS-AMANDA"
    uploaded = fin.create_upload(amanda, [b64_file("nota.txt", NOTA_TEXT.encode(), "text/plain")], conn=conn)
    upload_id = uploaded["upload_id"]
    row = conn.execute("SELECT * FROM ggv_nota_files WHERE upload_id=?", (upload_id,)).fetchone()
    needed = (
        "original_filename",
        "canonical_filename",
        "sha256",
        "size_bytes",
        "content_type",
        "nota_id",
        "vendor_id",
        "upload_id",
        "upload_timestamp",
        "source_provenance",
        "backup_state",
        "nas_rel_path",
        "storage_root_id",
    )
    missing_cols = [name for name in needed if name not in row.keys()]
    check("metadata columns present", not missing_cols, ",".join(missing_cols))
    check("original filename kept", row["original_filename"] == "nota.txt")
    check("canonical name is unique", row["canonical_filename"] and row["canonical_filename"] != row["original_filename"])
    check("hash stored", row["sha256"] == hashlib.sha256(NOTA_TEXT.encode()).hexdigest())
    check("size stored", row["size_bytes"] == len(NOTA_TEXT.encode()))
    check("backup pending not backed up", row["backup_state"] == "PENDING", row["backup_state"])
    check("storage root id", row["storage_root_id"] == "01-Media-Library")
    check("relative nas key", row["nas_rel_path"].startswith("Finance/GGV/Notas/") and not row["nas_rel_path"].startswith("/"))
    check("not local blob path", "state/ggv-finance-nota/blobs" not in row["nas_rel_path"])
    path = fin.evidence_path(row["nas_rel_path"])
    check(
        "file is under year month",
        path.parent.parent.parent.name == "Notas"
        and path.parent.name.isdigit()
        and len(path.parent.name) == 2
        and path.parent.parent.name.isdigit(),
    )
    check("physical file matches hash", hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"])
    public = fin._file_row(row)
    blob = json.dumps(public)
    check("client payload has no absolute volume", "/Volumes/" not in blob and "01-Media-Library" == public["storage_root_id"])

    fin.read_upload(amanda, upload_id, conn=conn)
    fin.check_vendor(amanda, upload_id, conn=conn)
    vendor = fin.create_vendor(amanda, {"display_name": "Bali Supplies Storage"}, conn=conn)
    vendor_id = vendor["vendor"]["vendor_id"]
    saved = fin.save_nota(
        amanda,
        {
            "upload_id": upload_id,
            "vendor_id": vendor_id,
            "invoice_no": "INV-100",
            "date": "2026-09-01",
            "amount": "250000",
            "currency": "IDR",
            "confirm": {"vendor": True, "date": True, "amount": True, "currency": True},
        },
        conn=conn,
    )
    nota_id = saved["nota"]["nota_id"]
    file_public = saved["nota"]["files"][0]
    check("saved file backup label", file_public["backup_label"] == "Pending", str(file_public.get("backup_label")))
    check("saved file vendor id", file_public["vendor_id"] == vendor_id)
    before_path = file_public["nas_rel_path"]
    before_bytes = fin.evidence_path(before_path).read_bytes()
    grouped = fin.search_history(amanda, {"year": ["2026"], "month": ["09"]}, conn=conn)
    check("year month group finds nota", any(item["nota_id"] == nota_id for item in grouped["results"]))
    check("group does not claim mutation", grouped.get("grouping_mutates_evidence") is False)
    check("path unchanged by year month view", fin.evidence_path(before_path).read_bytes() == before_bytes)
    edited = fin.edit_nota(
        amanda,
        nota_id,
        {
            "vendor_id": vendor_id,
            "invoice_no": "INV-100",
            "date": "2026-10-15",
            "amount": "250000",
            "currency": "IDR",
            "confirm": {"vendor": True, "date": True, "amount": True, "currency": True},
        },
        conn=conn,
    )
    after = conn.execute(
        "SELECT nas_rel_path, sha256, backup_state FROM ggv_nota_files WHERE nota_id=?",
        (nota_id,),
    ).fetchone()
    check("date edit leaves nas path", after["nas_rel_path"] == before_path, after["nas_rel_path"])
    check("date edit leaves bytes", fin.evidence_path(after["nas_rel_path"]).read_bytes() == before_bytes)
    check("logical october group", any(
        item["nota_id"] == nota_id
        for item in fin.search_history(ACCT_ID, {"year": ["2026"], "month": ["10"]}, conn=conn)["results"]
    ))
    check("september group dropped the moved date", nota_id not in {
        item["nota_id"]
        for item in fin.search_history(amanda, {"year": ["2026"], "month": ["09"]}, conn=conn)["results"]
    })
    check("edit did not mark backed up", after["backup_state"] == "PENDING")
    desk = fin.accountant_desk(ACCT_ID, conn=conn)
    check("desk has no accounting total", desk.get("accounting_total") is None and desk.get("books_complete") is False)
    check("desk note", "No accounting total" in desk.get("note", ""))
    reviewed = fin.review_nota(ACCT_ID, nota_id, {"comment": "Please confirm the date.", "request_correction": True}, conn=conn)
    check("accountant can request correction", reviewed.get("action") == "correction_requested")
    check("review leaves evidence path", reviewed.get("evidence_paths_unchanged") is True)
    try:
        fin.review_nota(ACCT_ID, nota_id, {"comment": "pay it", "paid": True}, conn=conn)
        check("accountant cannot pay from review", False)
    except fin.FinanceNotaError as exc:
        check("accountant cannot pay from review", exc.http_status == 405)
    try:
        fin.create_upload(ACCT_ID, [b64_file("x.txt", b"Total: 2", "text/plain")], conn=conn)
        check("accountant cannot upload", False)
    except fin.FinanceNotaError as exc:
        check("accountant cannot upload", exc.http_status == 403)
    try:
        fin.search_history(ACCT_ID, {"entity": ["ENT-AMG"]}, conn=conn)
        check("search outside GGV denied", False)
    except fin.FinanceNotaError as exc:
        check("search outside GGV denied", exc.http_status == 403)

    pack = fin.export_month_pack(ACCT_ID, {"year": ["2026"], "month": ["10"]}, conn=conn)
    data = pack["_file"]["data"]
    check("export is a zip product", pack["_file"]["content_type"] == "application/zip" and data[:2] == b"PK")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        check("zip is not canonical", manifest.get("canonical_storage") is False and manifest.get("zip_is_canonical") is False)
        check("zip has the nota file", any(item.get("nas_rel_path") == before_path for item in manifest.get("files") or []))
        check("zip has no books total", manifest.get("accounting_total") is None)
    check("nas individual still present", fin.evidence_path(before_path).is_file())
    check("zip was not stored on the media root", not list(store.rglob("*.zip")))
    try:
        fin.export_month_pack(ACCT_ID, {"year": ["2026"], "month": ["10"], "entity": ["ENT-AMG"]}, conn=conn)
        check("export outside GGV denied", False)
    except fin.FinanceNotaError as exc:
        check("export outside GGV denied", exc.http_status == 403)
    try:
        fin.export_month_pack("PERS-HAIKAL", {"year": ["2026"], "month": ["10"]}, conn=conn)
        check("haikal export denied", False)
    except fin.FinanceNotaError as exc:
        check("haikal export denied", exc.http_status == 403)

    legacy.mkdir(parents=True, exist_ok=True)
    payload = b"legacy-nota-bytes"
    source = legacy / "old-nota.bin"
    source.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    conn.execute(
        """
        INSERT INTO ggv_nota_files (
          file_id, upload_id, nota_id, filename, content_type, sha256, rel_path, role, evidence_id, created_at
        ) VALUES ('FILE-LEGACY-1', NULL, NULL, 'old-nota.bin', 'application/octet-stream', ?, ?, 'primary', NULL, '2026-08-02T00:00:00Z')
        """,
        (digest, str(source)),
    )
    conn.commit()
    fin.set_legacy_blob_dir(legacy)
    moved = fin.migrate_legacy_blobs(conn)
    check("legacy migrated", moved.get("migrated") == 1 and moved.get("deleted_sources") == 1, str(moved))
    check("legacy source removed only after copy", not source.exists())
    migrated = conn.execute("SELECT * FROM ggv_nota_files WHERE file_id='FILE-LEGACY-1'").fetchone()
    check("migrated path on nas", str(migrated["nas_rel_path"]).startswith("Finance/GGV/Notas/2026/08"))
    check(
        "migrated hash matches",
        hashlib.sha256(fin.evidence_path(migrated["nas_rel_path"]).read_bytes()).hexdigest() == digest,
    )
    check("migrated backup still pending", migrated["backup_state"] == "PENDING")

    bad = legacy / "bad.bin"
    bad.write_bytes(b"not-the-hash")
    conn.execute(
        """
        INSERT INTO ggv_nota_files (
          file_id, upload_id, nota_id, filename, content_type, sha256, rel_path, role, evidence_id, created_at
        ) VALUES ('FILE-LEGACY-BAD', NULL, NULL, 'bad.bin', 'application/octet-stream', ?, ?, 'primary', NULL, '2026-08-03T00:00:00Z')
        """,
        ("a" * 64, str(bad)),
    )
    conn.commit()
    failed = fin.migrate_legacy_blobs(conn)
    check("hash mismatch keeps source", bad.exists() and failed.get("failed", 0) >= 1, str(failed))
    bad_row = conn.execute("SELECT backup_state FROM ggv_nota_files WHERE file_id='FILE-LEGACY-BAD'").fetchone()
    check("hash mismatch is failed not backed up", bad_row["backup_state"] == "FAILED")

    held = edited["nota"]["files"][0]["nas_rel_path"]
    check("october view did not rewrite september file", held == before_path and "2026/09" in before_path)


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
            return res.status, res.read(), res.headers.get("Content-Type", "")
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
            ("accountant page", "GET", "/ggv/finance", ACCT, 200),
            ("accountant hidden finance", "GET", "/ggv-finance.html", ACCT, 200),
            ("accountant overview", "GET", "/api/ggv/finance/overview", ACCT, 200),
            ("accountant history", "GET", "/api/ggv/finance/history?year=2026&month=10", ACCT, 200),
            ("accountant search", "GET", "/api/ggv/finance/search?q=INV-100", ACCT, 200),
            ("accountant desk", "GET", "/api/ggv/finance/accountant", ACCT, 200),
            ("accountant export", "GET", "/api/ggv/finance/export/month?year=2026&month=10", ACCT, 200),
            ("accountant other entity search", "GET", "/api/ggv/finance/search?entity=ENT-AMG", ACCT, 403),
            ("accountant other entity export", "GET", "/api/ggv/finance/export/month?year=2026&month=10&entity=ENT-BZG", ACCT, 403),
            ("accountant content page", "GET", "/content-2.0", ACCT, 403),
            ("accountant ops page", "GET", "/ggv-ops-pack", ACCT, 403),
            ("accountant bzg page", "GET", "/bzg", ACCT, 403),
            ("accountant hidden content", "GET", "/dashboards/content-2.0.html", ACCT, 403),
            ("matt still on finance", "GET", "/ggv/finance", MATT, 200),
            ("matt content still open", "GET", "/content-2.0", MATT, 200),
            ("haikal finance still denied", "GET", "/ggv/finance", HAIKAL, 403),
            ("haikal export", "GET", "/api/ggv/finance/export/month?year=2026&month=10", HAIKAL, 403),
        ]
        for name, method, path, email, expect in cases:
            status, raw, ctype = call(base, method, path, email)
            check(name, status == expect, f"status={status} body={raw[:160]!r}")
            if name == "accountant export":
                check("export content type zip", status == 200 and "zip" in ctype, ctype)
        status, raw, _ctype = call(base, "POST", "/api/ggv/finance/pay", ACCT, {})
        check("accountant pay denied", status == 405, str(status))
        status, raw, _ctype = call(base, "POST", "/api/ggv/finance/uploads", ACCT, {"files": [b64_file("a.txt", b"Total: 9", "text/plain")]})
        check("accountant upload api denied", status == 403, str(status))
        status, raw, _ctype = call(base, "POST", "/api/ggv/finance/vendors/VEND-X/bank", ACCT, {"account": "1"})
        check("accountant bank api denied", status == 405, str(status))
        status, raw, _ctype = call(base, "GET", "/wolf-tokens.css", ACCT)
        check("shell chrome not scope-denied", status != 403, str(status))
    finally:
        httpd.shutdown()
        httpd.server_close()


def main() -> int:
    test_contract_and_ui()
    tmp = ROOT / "state" / ".tmp-ggv-finance-storage"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    db_path = tmp / "catalog.sqlite"
    store = tmp / "media"
    legacy = tmp / "legacy-blobs"
    shutil.copy(ROOT / "catalog" / "content_library.sqlite", db_path)
    wire(db_path, store)
    conn = fin.db_connect(db_path)
    try:
        test_storage_and_accountant(conn, store, legacy)
    finally:
        conn.close()
    test_http(db_path, store)
    fin.set_media_root(None)
    fin.set_legacy_blob_dir(None)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
