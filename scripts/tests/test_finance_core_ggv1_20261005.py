#!/usr/bin/env python3
"""FINANCE-CORE-GGV-1 — GGV Finance operational desk + nota + bank statement proving."""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"

from core import finance_core_statements as fcs  # noqa: E402
from core import ggv_bank_statement1 as gbs  # noqa: E402
from core import ggv_finance_desk as desk  # noqa: E402
from core import ggv_finance_nota as fin  # noqa: E402
from core import rbac as _rbac  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
DASHBOARD = ROOT / "dashboards" / "ggv-finance.html"

MATT = "PERS-MATT"
AMANDA = "PERS-AMANDA"
ZAYEN = "PERS-ZAYEN"
ENTITY = "ENT-GGV"

PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
)
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"
PROD_PID = 1297

OPERATIONAL_SECTIONS = (
    "Overview",
    "Banking",
    "Transactions",
    "Receipts/Notas",
    "Bills",
    "Invoices",
    "Reconciliation",
    "Suppliers",
    "Missing Evidence",
    "Reports",
    "Audit",
)

FORBIDDEN_HTML = (
    "Reconcile</button>",
    'id="btnReconcile"',
    ">Reconcile<",
    "payment.execute",
    "payment.approve",
)

GENERIC_CSV = b"""date,description,debit,credit,balance
2026-09-01,Test payment GGV FC1,100000,0,5000000
2026-09-02,Deposit GGV FC1,0,250000,5250000
"""

DIFFERENT_PERIOD_CSV = b"""date,description,debit,credit,balance
2026-11-01,Different month no overlap,75000,0,4000000
"""


def _ro(path: Path | None = None) -> sqlite3.Connection:
    p = path or LIVE_CATALOG
    conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def _rw_copy() -> sqlite3.Connection:
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    shutil.copy2(LIVE_CATALOG, tmp.name)
    conn = sqlite3.connect(tmp.name)
    conn.row_factory = sqlite3.Row
    return conn


def _listener_pid(port: int) -> int | None:
    try:
        out = subprocess.check_output(
            ["lsof", "-i", f":{port}", "-t"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if out:
            return int(out.splitlines()[0])
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None
    return None


def _b64_file(name: str, content: bytes, content_type: str) -> dict:
    return {
        "filename": name,
        "content_type": content_type,
        "data_base64": base64.b64encode(content).decode("ascii"),
    }


class FinanceCoreGgv1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not LIVE_CATALOG.is_file():
            raise unittest.SkipTest("live catalog missing")

    def setUp(self) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        tmp.close()
        self._db_path = Path(tmp.name)
        shutil.copy2(LIVE_CATALOG, self._db_path)
        self.conn = sqlite3.connect(str(self._db_path))
        self.conn.row_factory = sqlite3.Row
        self.media = Path(tempfile.mkdtemp(prefix="ggv-fc1-media-"))
        fin.CATALOG_DB = self._db_path
        gbs.CATALOG_DB = self._db_path
        fcs.CATALOG_DB = self._db_path
        self.orig_dir = Path(tempfile.mkdtemp(prefix="ggv-fc1-orig-"))
        self._orig_patch = unittest.mock.patch.object(fcs, "_originals_dir", lambda entity_id=None: self.orig_dir)
        self._orig_patch.start()
        fin.set_media_root(self.media)
        fin.ensure_schema(self.conn)
        fin.ensure_rbac(self.conn, commit=True)
        gbs.ensure_schema(self.conn)
        fcs.ensure_schema(self.conn)
        self.conn.commit()

    def tearDown(self) -> None:
        self._orig_patch.stop()
        fin.set_media_root(None)
        self.conn.close()
        shutil.rmtree(self.media, ignore_errors=True)
        shutil.rmtree(self.orig_dir, ignore_errors=True)
        if self._db_path.is_file():
            self._db_path.unlink(missing_ok=True)

    def test_operational_sections_on_desk_and_html(self) -> None:
        body = desk.desk_overview(MATT, self.conn)
        self.assertTrue(body["operational"])
        self.assertFalse(body["completeness_only"])
        labels = [s["label"] for s in body["operational_sections"]]
        for section in OPERATIONAL_SECTIONS:
            self.assertIn(section, labels)
        html = DASHBOARD.read_text(encoding="utf-8")
        for section in OPERATIONAL_SECTIONS:
            self.assertIn(section, html, f"missing tab {section}")
        self.assertIn("OPERATIONAL_SECTIONS", html)
        lower = html.lower()
        for term in FORBIDDEN_HTML:
            self.assertNotIn(term.lower(), lower, f"forbidden {term}")

    def test_history_counts_ro_and_searchable(self) -> None:
        ro = _ro()
        counts = desk.desk_counts(ro)
        ro.close()
        self.assertEqual(counts["invoices"], 46)
        self.assertEqual(counts["notas"], 33)
        self.assertEqual(counts["bills"], 605)
        inv = self.conn.execute(
            "SELECT invoice_id FROM ggv_invoices WHERE entity_id=? LIMIT 1", (ENTITY,)
        ).fetchone()
        self.assertIsNotNone(inv)
        hist = fin.search_history(MATT, {"q": [""]}, conn=self.conn)
        self.assertTrue(hist.get("ok"))
        bills = fin.list_bills(MATT, conn=self.conn)
        self.assertGreaterEqual(bills.get("bill_count", 0), 1)
        notas = fin.list_notas(MATT, conn=self.conn)
        self.assertGreaterEqual(len(notas.get("notas") or []), 1)

    def test_nota_upload_evidence_first_queue_audit(self) -> None:
        image = _b64_file("fc1-photo.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")
        up = fin.create_upload(AMANDA, [image], conn=self.conn)
        self.assertTrue(up.get("evidence_saved_first"))
        self.assertEqual(up.get("stage"), "uploading")
        self.assertIn("NEEDS", up.get("queue_state", ""))
        upload_id = up["upload_id"]
        files_before = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_nota_files WHERE upload_id=?", (upload_id,)
        ).fetchone()[0]
        self.assertGreater(files_before, 0)
        read = fin.read_upload(AMANDA, upload_id, conn=self.conn)
        self.assertTrue(read.get("preserved"))
        self.assertIn("queue_state", read)
        payload = json.dumps(read)
        for banned in ("ocr", "tesseract", "google vision", "openai", "api error", "provider"):
            self.assertNotIn(banned, payload.lower())
        self.assertTrue(read.get("manual_entry") or read["proposals"].get("message"))
        audit_n = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_nota_history WHERE action='upload_saved'"
        ).fetchone()[0]
        self.assertGreaterEqual(audit_n, 1)

    def test_bank_statement_idempotent_and_fields(self) -> None:
        content = GENERIC_CSV
        first = gbs.import_statement(
            verified_person_id=MATT,
            filename="fc1-ggv-statement.csv",
            content=content,
            conn=self.conn,
        )
        self.assertTrue(first.get("original_retrievable"))
        self.assertGreater(first.get("txn_count", 0), 0)
        imp_id = first["import_id"]
        txns = self.conn.execute(
            "SELECT * FROM ggv_bank_transactions WHERE import_id=?", (imp_id,)
        ).fetchall()
        self.assertGreater(len(txns), 0)
        for t in txns:
            self.assertEqual(t["entity_id"], ENTITY)
            self.assertIsNotNone(t["txn_id"])
            self.assertIn(t["recon_status"], ("UNIDENTIFIED", "NEEDS_REVIEW", "NEEDS_RECEIPT"))
        with self.assertRaises(gbs.GgvBankStatementError) as ctx:
            gbs.import_statement(
                verified_person_id=MATT,
                filename="fc1-ggv-statement.csv",
                content=content,
                conn=self.conn,
            )
        self.assertEqual(ctx.exception.code, "already_imported")
        self.assertIn("ALREADY IMPORTED", str(ctx.exception))
        second = gbs.import_statement(
            verified_person_id=MATT,
            filename="fc1-ggv-statement.csv",
            content=DIFFERENT_PERIOD_CSV,
            conn=self.conn,
        )
        self.assertTrue(second.get("ok"))
        self.assertNotEqual(second["import_id"], imp_id)
        listed = gbs.list_transactions(verified_person_id=MATT, conn=self.conn)
        labels = {t.get("match_label") for t in listed.get("transactions") or []}
        self.assertTrue(labels.issubset({"PROPOSE MATCH", "HUMAN REVIEW", "UNMATCHED"}))

    def test_permissions_no_hardcoded_people(self) -> None:
        self.assertTrue(_rbac.can(MATT, "finance.nota.read", {"entity_id": ENTITY}, conn=self.conn))
        self.assertTrue(_rbac.can(AMANDA, "finance.nota.create", {"entity_id": ENTITY}, conn=self.conn))
        self.assertFalse(_rbac.can(ZAYEN, "finance.nota.read", {"entity_id": ENTITY}, conn=self.conn))
        with self.assertRaises(fin.FinanceNotaError):
            fin.overview(ZAYEN, conn=self.conn)
        chain = self.conn.execute(
            """
            SELECT a.assignment_id, p.position_id, r.role_id, perm.code
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            JOIN org_roles r ON r.role_id = p.role_id
            JOIN org_role_permissions rp ON rp.role_id = r.role_id AND rp.effect='ALLOW'
            JOIN org_permissions perm ON perm.permission_id = rp.permission_id
            WHERE a.person_id=? AND a.status='ACTIVE' AND perm.code='finance.nota.create'
            """,
            (AMANDA,),
        ).fetchall()
        self.assertGreater(len(chain), 0)
        src = (SCRIPTS / "core" / "ggv_finance_desk.py").read_text(encoding="utf-8")
        self.assertNotIn('== "PERS-MATT"', src)
        self.assertNotIn("== 'PERS-MATT'", src)
        self.assertNotIn('== "PERS-AMANDA"', src)

    def test_entity_isolation_smoke(self) -> None:
        before_amg = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_notas WHERE entity_id='ENT-AMG'"
        ).fetchone()[0]
        before_bzg = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_notas WHERE entity_id='ENT-BZG'"
        ).fetchone()[0]
        gbs.import_statement(
            verified_person_id=MATT,
            filename="fc1-isolation.csv",
            content=GENERIC_CSV,
            conn=self.conn,
        )
        after_amg = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_notas WHERE entity_id='ENT-AMG'"
        ).fetchone()[0]
        after_bzg = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_notas WHERE entity_id='ENT-BZG'"
        ).fetchone()[0]
        before_bank_amg = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id='ENT-AMG'"
        ).fetchone()[0]
        before_bank_bzg = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id='ENT-BZG'"
        ).fetchone()[0]
        after_bank_amg = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id='ENT-AMG'"
        ).fetchone()[0]
        after_bank_bzg = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id='ENT-BZG'"
        ).fetchone()[0]
        self.assertEqual(before_amg, after_amg)
        self.assertEqual(before_bzg, after_bzg)
        self.assertEqual(before_bank_amg, after_bank_amg)
        self.assertEqual(before_bank_bzg, after_bank_bzg)

    def test_protected_closes_petty_prod_unchanged(self) -> None:
        ro = _ro()
        for cid in PROTECTED_CLOSES:
            row = ro.execute(
                "SELECT state FROM venue_daily_closes WHERE close_id=?", (cid,)
            ).fetchone()
            self.assertIsNotNone(row, cid)
        petty = ro.execute(
            "SELECT movement_id, amount FROM bzg_ops_petty_movements WHERE movement_id=?",
            (PROTECTED_PETTY,),
        ).fetchone()
        self.assertIsNotNone(petty)
        from core import bzg_history_import1 as _hist

        balance = _hist.petty_balance(ro)
        ro.close()
        self.assertEqual(float(balance["amount_idr"]), 552700.0)
        try:
            os.kill(PROD_PID, 0)
            prod_alive = True
        except OSError:
            prod_alive = False
        self.assertTrue(prod_alive, f"prod pid {PROD_PID} should remain running")

    def test_reconciliation_api(self) -> None:
        board = desk.reconciliation_board(MATT, self.conn)
        self.assertTrue(board.get("ok"))
        self.assertFalse(board.get("auto_reconcile"))
        self.assertIn("summary", board)


if __name__ == "__main__":
    unittest.main()
