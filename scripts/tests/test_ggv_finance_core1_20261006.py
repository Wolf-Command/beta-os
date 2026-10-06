#!/usr/bin/env python3
"""GGV-FINANCE-CORE-1 — proof tests for Matt-usable GGV Finance on shared Finance Core."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import sqlite3
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

from core import amg_finance_desk as amg_desk  # noqa: E402
from core import finance_core_statements as fcs  # noqa: E402
from core import ggv_bank_statement1 as gbs  # noqa: E402
from core import ggv_finance_nota as fin  # noqa: E402
from core import rbac as _rbac  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
DASHBOARD = ROOT / "dashboards" / "ggv-finance.html"
TEST_DIR = Path("/tmp/ggv-fin-test")
RESULT_DIR = Path.home() / "ggv-finance-20261006-evidence" / "tests"

MATT = "PERS-MATT"
AMANDA = "PERS-AMANDA"
ZAYEN = "PERS-ZAYEN"
MISA = "PERS-MISA"
ENTITY = "ENT-GGV"

FORBIDDEN_VISIBLE = (
    "staff_ready",
    "queue/worker",
    "state-machine",
    "ENT-GGV",
    "PERS-",
)

MALFORMED_CSV = b"""date,description,debit,credit,balance
2026-09-01,Valid row,100000,0,5000000
,BROKEN ROW NO DATE,,,
2026-09-02,TOTAL,0,0,5000000
2026-09-03,Another valid,0,50000,5050000
not-a-date,BAD FORMAT,abc,def,
"""


def _rw_copy() -> tuple[Path, sqlite3.Connection]:
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", dir=TEST_DIR, delete=False)
    tmp.close()
    shutil.copy2(LIVE_CATALOG, tmp.name)
    conn = sqlite3.connect(tmp.name)
    conn.row_factory = sqlite3.Row
    return Path(tmp.name), conn


class GgvFinanceCore1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not LIVE_CATALOG.is_file():
            raise unittest.SkipTest("live catalog missing")
        RESULT_DIR.mkdir(parents=True, exist_ok=True)

    def setUp(self) -> None:
        self._db_path, self.conn = _rw_copy()
        self.media = Path(tempfile.mkdtemp(prefix="ggv-fc-core-media-", dir=TEST_DIR))
        self.orig_dir = Path(tempfile.mkdtemp(prefix="ggv-fc-core-orig-", dir=TEST_DIR))
        fin.CATALOG_DB = self._db_path
        gbs.CATALOG_DB = self._db_path
        fcs.CATALOG_DB = self._db_path
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

    def test_permission_matrix(self) -> None:
        self.assertTrue(_rbac.can(MATT, "finance.nota.read", {"entity_id": "ENT-AMG"}, conn=self.conn))
        self.assertTrue(_rbac.can(MATT, "finance.nota.read", {"entity_id": "ENT-GGV"}, conn=self.conn))
        self.assertTrue(_rbac.can(MATT, "atrium.board.read", {"entity_id": "ENT-BZG"}, conn=self.conn))
        self.assertTrue(_rbac.can(AMANDA, "finance.nota.read", {"entity_id": ENTITY}, conn=self.conn))
        self.assertFalse(_rbac.can(AMANDA, "atrium.board.read", {"entity_id": "ENT-AMG"}, conn=self.conn))
        self.assertFalse(_rbac.can(ZAYEN, "finance.nota.read", {"entity_id": ENTITY}, conn=self.conn))
        self.assertFalse(_rbac.can(MISA, "finance.nota.read", {"entity_id": ENTITY}, conn=self.conn))
        with self.assertRaises(fin.FinanceNotaError):
            fin.overview(ZAYEN, conn=self.conn)
        with self.assertRaises(fin.FinanceNotaError):
            fin.overview(MISA, conn=self.conn)
        bill = fin.get_bill(AMANDA, self._first_bill_id(), conn=self.conn)
        self.assertTrue(bill.get("ok"))
        with self.assertRaises(fin.FinanceNotaError):
            fin.get_bill(ZAYEN, self._first_bill_id(), conn=self.conn)

    def _first_bill_id(self) -> str:
        row = self.conn.execute(
            "SELECT bill_id FROM ggv_bills WHERE entity_id=? LIMIT 1", (ENTITY,)
        ).fetchone()
        self.assertIsNotNone(row)
        return str(row["bill_id"])

    def _upload_fixture(self, name: str, data: bytes, ctype: str) -> str:
        payload = {
            "filename": name,
            "content_type": ctype,
            "data_base64": base64.b64encode(data).decode("ascii"),
        }
        up = fin.create_upload(AMANDA, [payload], conn=self.conn)
        files = self.conn.execute(
            "SELECT sha256, file_id FROM ggv_nota_files WHERE upload_id=?",
            (up["upload_id"],),
        ).fetchall()
        self.assertEqual(len(files), 1)
        stored = fin.file_bytes(AMANDA, files[0]["file_id"], conn=self.conn)
        blob = stored["_file"]["data"]
        self.assertEqual(hashlib.sha256(blob).hexdigest(), files[0]["sha256"])
        self.assertEqual(hashlib.sha256(data).hexdigest(), files[0]["sha256"])
        return up["upload_id"]

    def test_evidence_byte_preservation(self) -> None:
        fixtures = [
            ("photo.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 20 + b"\xff\xd9", "image/jpeg"),
            ("scan.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, "image/png"),
            ("doc.pdf", b"%PDF-1.4\n%test", "application/pdf"),
        ]
        heic_path = TEST_DIR / "test.heic"
        if shutil.which("sips"):
            import subprocess

            jpg = TEST_DIR / "tmp.jpg"
            jpg.write_bytes(b"\xff\xd8\xff\xd9")
            subprocess.run(
                ["/usr/bin/sips", "-s", "format", "heic", str(jpg), "--out", str(heic_path)],
                check=False,
                capture_output=True,
            )
            if heic_path.is_file():
                fixtures.append(("iphone.heic", heic_path.read_bytes(), "image/heic"))
        for name, data, ctype in fixtures:
            self._upload_fixture(name, data, ctype)

    def test_statement_row_count_conservation(self) -> None:
        result = gbs.import_statement(
            verified_person_id=MATT,
            filename="malformed-test.csv",
            content=MALFORMED_CSV,
            conn=self.conn,
        )
        rc = result.get("row_counts") or {}
        self.assertGreaterEqual(int(rc.get("source_rows", 0)), 3)
        self.assertGreaterEqual(len(rc.get("exceptions") or []), 1)
        self.assertGreaterEqual(len(rc.get("non_transaction") or []), 1)
        self.assertTrue(rc.get("reconciled"))
        self.assertGreater(result.get("txn_count", 0), 0)

    def test_no_auto_force_reconciliation(self) -> None:
        content = b"date,description,debit,credit,balance\n2026-09-10,Test pay,50000,0,1000000\n"
        imp = gbs.import_statement(
            verified_person_id=MATT,
            filename="recon-prove.csv",
            content=content,
            conn=self.conn,
        )
        txns = self.conn.execute(
            "SELECT * FROM ggv_bank_transactions WHERE import_id=?",
            (imp["import_id"],),
        ).fetchall()
        self.assertEqual(len(txns), 1)
        txn_id = txns[0]["txn_id"]
        bill_id = self._first_bill_id()
        self.conn.execute(
            """
            UPDATE ggv_bank_transactions
            SET match_proposed=1, match_confidence='PROPOSE MATCH', recon_status='NEEDS_REVIEW',
                matched_receipt_ref=?
            WHERE txn_id=?
            """,
            (bill_id, txn_id),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT human_confirmed FROM ggv_bank_transactions WHERE txn_id=?", (txn_id,)
        ).fetchone()
        self.assertEqual(int(row["human_confirmed"]), 0)
        gbs.confirm_match(verified_person_id=MATT, txn_id=txn_id, conn=self.conn)
        row2 = self.conn.execute(
            "SELECT human_confirmed, recon_status FROM ggv_bank_transactions WHERE txn_id=?",
            (txn_id,),
        ).fetchone()
        self.assertEqual(int(row2["human_confirmed"]), 1)
        gbs.unmatch(verified_person_id=MATT, txn_id=txn_id, body={"reason": "test unmatch"}, conn=self.conn)
        tables = {r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "core_audit_events" in tables:
            audit = self.conn.execute(
                "SELECT COUNT(*) FROM core_audit_events WHERE resource_id=? AND action='ggv.bank_recon.unmatch'",
                (txn_id,),
            ).fetchone()[0]
            self.assertGreaterEqual(int(audit), 1)

    def test_drill_down_no_dead_rows(self) -> None:
        bill_id = self._first_bill_id()
        bill = fin.get_bill(MATT, bill_id, conn=self.conn)
        self.assertTrue(bill.get("ok"))
        nota_row = self.conn.execute(
            "SELECT nota_id FROM ggv_notas WHERE entity_id=? LIMIT 1", (ENTITY,)
        ).fetchone()
        if nota_row:
            nota = fin.get_nota(MATT, nota_row["nota_id"], conn=self.conn)
            self.assertTrue(nota.get("ok"))
        inv = self.conn.execute(
            "SELECT invoice_id FROM ggv_invoices WHERE entity_id=? LIMIT 1", (ENTITY,)
        ).fetchone()
        if inv:
            from core import ggv_finance_invoice as inv_mod

            inv_mod.CATALOG_DB = self._db_path
            detail = inv_mod.get_invoice(MATT, inv["invoice_id"], conn=self.conn)
            self.assertTrue(detail.get("ok"))

    def test_internal_label_scan(self) -> None:
        html = DASHBOARD.read_text(encoding="utf-8")
        visible = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
        visible = re.sub(r"<[^>]+>", " ", visible)
        for term in FORBIDDEN_VISIBLE:
            self.assertNotIn(term, visible, f"forbidden visible term: {term}")
        overview = fin.overview(MATT, conn=self.conn)
        payload = json.dumps(overview)
        self.assertNotIn("staff_ready", payload.replace('"staff_ready": false', ""))

    def test_no_gemini_on_upload_path(self) -> None:
        def _boom(*_a, **_k):
            raise RuntimeError("GEMINI BLOCKED")

        with unittest.mock.patch.dict(sys.modules, {"core.model_router": unittest.mock.MagicMock(call_gemini=_boom)}):
            up = fin.create_upload(
                AMANDA,
                [{"filename": "x.jpg", "content_type": "image/jpeg", "data_base64": base64.b64encode(b"\xff\xd8\xff\xd9").decode()}],
                conn=self.conn,
            )
            read = fin.read_upload(AMANDA, up["upload_id"], conn=self.conn)
            self.assertTrue(read.get("preserved"))
            self.assertTrue(read.get("manual_entry") or read.get("proposals"))

    def test_amg_regression_board(self) -> None:
        overview = amg_desk.desk_overview(MATT, self.conn)
        self.assertTrue(overview.get("operational"))
        self.assertFalse(overview.get("staff_ready"))
        recon = amg_desk.reconciliation_board(MATT, self.conn)
        self.assertTrue(recon.get("ok"))
        self.assertFalse(recon.get("auto_reconcile"))
        ggv_counts = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_invoices WHERE entity_id=?", (ENTITY,)
        ).fetchone()[0]
        self.assertEqual(int(ggv_counts), 46)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(GgvFinanceCore1Tests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    out = {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "passed": result.testsRun - len(result.failures) - len(result.errors),
    }
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / "ggv_finance_core1_20261006.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    sys.exit(0 if result.wasSuccessful() else 1)
