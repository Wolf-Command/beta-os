#!/usr/bin/env python3
"""FINANCE-CORE-AMG-PROVE-1 — AMG Finance Core entity isolation proving."""
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

from core import amg_bank_statement1 as gbs  # noqa: E402
from core import finance_core_statements as fcs  # noqa: E402
from core import amg_finance_core as core  # noqa: E402
from core import amg_finance_desk as desk  # noqa: E402
from core import finance_core_entity as _fce  # noqa: E402
from core import ggv_finance_nota as fin  # noqa: E402
from core import rbac as _rbac  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
DASHBOARD = ROOT / "dashboards" / "amg-finance-ops.html"

MATT = "PERS-MATT"
AMANDA = "PERS-AMANDA"
ZAYEN = "PERS-ZAYEN"
ENTITY = "ENT-AMG"
GGV_ENTITY = "ENT-GGV"

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
2026-09-01,Test payment AMG FC1,100000,0,5000000
2026-09-02,Deposit AMG FC1,0,250000,5250000
"""


def _ro(path: Path | None = None) -> sqlite3.Connection:
    p = path or LIVE_CATALOG
    conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def _b64_file(name: str, content: bytes, content_type: str) -> dict:
    return {
        "filename": name,
        "content_type": content_type,
        "data_base64": base64.b64encode(content).decode("ascii"),
    }


class FinanceCoreAmgProve1Tests(unittest.TestCase):
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
        self.media = Path(tempfile.mkdtemp(prefix="amg-fc1-media-"))
        fin.CATALOG_DB = self._db_path
        fcs.CATALOG_DB = self._db_path
        self.orig_dir = Path(tempfile.mkdtemp(prefix="amg-fc1-orig-"))
        self._orig_patch = unittest.mock.patch.object(fcs, "_originals_dir", lambda entity_id=None: self.orig_dir)
        self._orig_patch.start()
        gbs.ensure_schema(self.conn)
        fcs.ensure_schema(self.conn)
        fin.ensure_schema(self.conn)
        fin.ensure_rbac(self.conn, commit=True)
        fin.set_media_root(self.media)
        self.conn.commit()

    def tearDown(self) -> None:
        self._orig_patch.stop()
        fin.set_media_root(None)
        _fce._entity_ctx.set(_fce.DEFAULT_ENTITY)
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
        lower = html.lower()
        for term in FORBIDDEN_HTML:
            self.assertNotIn(term.lower(), lower, f"forbidden {term}")

    def test_permissions_matt_zayen_amanda(self) -> None:
        ctx = {"entity_id": ENTITY}
        self.assertTrue(_rbac.can(MATT, "finance.nota.read", ctx, conn=self.conn))
        self.assertTrue(_rbac.can(MATT, "finance.nota.create", ctx, conn=self.conn))
        self.assertTrue(_rbac.can(ZAYEN, "atrium.board.read", ctx, conn=self.conn))
        self.assertTrue(desk._can_read_finance(ZAYEN, self.conn))
        self.assertFalse(_rbac.can(AMANDA, "finance.nota.create", ctx, conn=self.conn))
        self.assertFalse(_rbac.can(AMANDA, "atrium.board.read", ctx, conn=self.conn))
        self.assertFalse(desk._can_read_finance(AMANDA, self.conn))
        with self.assertRaises(fin.FinanceNotaError):
            with _fce.entity_scope(ENTITY):
                fin.overview(AMANDA, conn=self.conn)
        src = (SCRIPTS / "core" / "amg_finance_desk.py").read_text(encoding="utf-8")
        self.assertNotIn('== "PERS-MATT"', src)
        self.assertNotIn("== 'PERS-MATT'", src)

    def test_amg_upload_entity_isolation(self) -> None:
        before_ggv = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_notas WHERE entity_id=?", (GGV_ENTITY,)
        ).fetchone()[0]
        before_bzg = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_notas WHERE entity_id='ENT-BZG'"
        ).fetchone()[0]
        with _fce.entity_scope(ENTITY):
            up = fin.create_upload(MATT, [_b64_file("amg-fc1.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")], conn=self.conn)
        self.assertTrue(up.get("evidence_saved_first"))
        upload_id = up["upload_id"]
        row = self.conn.execute(
            "SELECT entity_id FROM ggv_uploads WHERE upload_id=?", (upload_id,)
        ).fetchone()
        self.assertEqual(row["entity_id"], ENTITY)
        gbs.import_statement(
            verified_person_id=MATT,
            filename="amg-fc1-statement.csv",
            content=GENERIC_CSV,
            conn=self.conn,
        )
        after_ggv = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_notas WHERE entity_id=?", (GGV_ENTITY,)
        ).fetchone()[0]
        after_bzg = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_notas WHERE entity_id='ENT-BZG'"
        ).fetchone()[0]
        bank_ggv = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id=?", (GGV_ENTITY,)
        ).fetchone()[0]
        bank_bzg = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id='ENT-BZG'"
        ).fetchone()[0]
        bank_amg = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id=?", (ENTITY,)
        ).fetchone()[0]
        self.assertEqual(before_ggv, after_ggv)
        self.assertEqual(before_bzg, after_bzg)
        self.assertGreater(bank_amg, 0)
        imp_row = self.conn.execute(
            "SELECT entity_id FROM ggv_bank_statement_imports ORDER BY uploaded_at DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(imp_row["entity_id"], ENTITY)
        for eid in (GGV_ENTITY, "ENT-BZG"):
            leak = self.conn.execute(
                "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id=? AND description LIKE '%AMG FC1%'",
                (eid,),
            ).fetchone()[0]
            self.assertEqual(leak, 0)

    def test_ggv_history_counts_unchanged_ro(self) -> None:
        ro = _ro()
        counts = {
            "invoices": int(ro.execute("SELECT COUNT(*) FROM ggv_invoices WHERE entity_id=?", (GGV_ENTITY,)).fetchone()[0]),
            "notas": int(ro.execute("SELECT COUNT(*) FROM ggv_notas WHERE entity_id=?", (GGV_ENTITY,)).fetchone()[0]),
            "bills": int(ro.execute("SELECT COUNT(*) FROM ggv_bills WHERE entity_id=?", (GGV_ENTITY,)).fetchone()[0]),
        }
        ro.close()
        self.assertEqual(counts["invoices"], 46)
        self.assertEqual(counts["notas"], 33)
        self.assertEqual(counts["bills"], 605)

    def test_nota_upload_pipeline_and_bank_idempotent(self) -> None:
        with _fce.entity_scope(ENTITY):
            up = fin.create_upload(MATT, [_b64_file("amg-photo.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")], conn=self.conn)
        self.assertIn("NEEDS", up.get("queue_state", ""))
        with _fce.entity_scope(ENTITY):
            read = fin.read_upload(MATT, up["upload_id"], conn=self.conn)
        payload = json.dumps(read)
        for banned in ("ocr", "tesseract", "google vision", "openai", "api error", "provider"):
            self.assertNotIn(banned, payload.lower())
        first = gbs.import_statement(
            verified_person_id=MATT,
            filename="amg-idem.csv",
            content=GENERIC_CSV,
            conn=self.conn,
        )
        self.assertTrue(first.get("original_retrievable"))
        with self.assertRaises(gbs.GgvBankStatementError) as ctx:
            gbs.import_statement(
                verified_person_id=MATT,
                filename="amg-idem.csv",
                content=GENERIC_CSV,
                conn=self.conn,
            )
        self.assertEqual(ctx.exception.code, "already_imported")

    def test_reconciliation_and_honesty(self) -> None:
        board = desk.reconciliation_board(MATT, self.conn)
        self.assertTrue(board.get("ok"))
        self.assertFalse(board.get("auto_reconcile"))
        self.assertFalse(board.get("payment_execute"))
        self.assertFalse(board.get("staff_ready"))
        self.assertFalse(board.get("human_commissioned"))

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

    def test_core_matches_routes(self) -> None:
        self.assertTrue(core.matches("/amg/finance/notas"))
        self.assertTrue(core.matches("/api/amg/finance/desk"))
        self.assertFalse(core.matches("/amg/finance"))
        self.assertFalse(core.matches("/api/amg/finance/ledger"))


if __name__ == "__main__":
    unittest.main()
