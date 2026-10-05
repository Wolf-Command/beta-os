#!/usr/bin/env python3
"""FINANCE-CORE-BZG-PROVE-1 — BZG Finance Core entity isolation proving."""
from __future__ import annotations

import json
import os
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

from core import bzg_finance_desk as desk  # noqa: E402
from core import bzg_finance_usability_ro as browse  # noqa: E402
from core import finance_core_entity as _fce  # noqa: E402
from core import finance_core_statements as fcs  # noqa: E402
from core import rbac as _rbac  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
DASHBOARD = ROOT / "dashboards" / "bzg-finance.html"

MATT = "PERS-MATT"
AMANDA = "PERS-AMANDA"
ZAYEN = "PERS-ZAYEN"
HAIKAL = "PERS-HAIKAL"
ENTITY = "ENT-BZG"
GGV_ENTITY = "ENT-GGV"
AMG_ENTITY = "ENT-AMG"

PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
)
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"
PROD_PID = 1297

BROWSE_SECTIONS = (
    "Suppliers",
    "Petty cash",
    "Bank",
    "AP ready",
    "Exceptions",
    "Completeness",
)

FORBIDDEN_HTML = (
    "Reconcile</button>",
    'id="btnReconcile"',
    ">Reconcile<",
    "payment.execute",
    "payment.approve",
    "bzg.ap.mark_ready",
    "bzg.pay.",
)

GENERIC_CSV = b"""date,description,debit,credit,balance
2026-09-01,Test payment BZG FC1,100000,0,5000000
2026-09-02,Deposit BZG FC1,0,250000,5250000
"""


def _ro(path: Path | None = None) -> sqlite3.Connection:
    p = path or LIVE_CATALOG
    conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=60)
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


class FinanceCoreBzgProve1Tests(unittest.TestCase):
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
        self.orig_dir = Path(tempfile.mkdtemp(prefix="bzg-fc1-orig-"))
        fcs.CATALOG_DB = self._db_path
        self._orig_patch = unittest.mock.patch.object(fcs, "_originals_dir", lambda entity_id=None: self.orig_dir)
        self._orig_patch.start()
        fcs.ensure_schema(self.conn)
        self.conn.commit()

    def tearDown(self) -> None:
        self._orig_patch.stop()
        _fce._entity_ctx.set(_fce.DEFAULT_ENTITY)
        self.conn.close()
        shutil.rmtree(self.orig_dir, ignore_errors=True)
        if self._db_path.is_file():
            self._db_path.unlink(missing_ok=True)

    def test_shared_core_patterns_on_desk_and_html(self) -> None:
        body = desk.overview(MATT, self.conn)
        self.assertTrue(body["operational"])
        self.assertFalse(body["completeness_only"])
        self.assertEqual(body["entity_id"], ENTITY)
        self.assertIn("shared_core", body)
        self.assertEqual(body["shared_core"]["entity_scope"], "finance_core_entity")
        self.assertEqual(body["shared_core"]["statements"], "finance_core_statements")
        self.assertEqual(body["shared_core"]["page_prefix"], "/bzg/finance")
        labels = [n["label"] for n in body["browse_nav"]]
        for section in BROWSE_SECTIONS:
            self.assertIn(section, labels)
        cfg = _fce.entity_config(ENTITY)
        self.assertEqual(cfg["bound"], "beta-bzg-finance")
        html = DASHBOARD.read_text(encoding="utf-8")
        for href in ("/bzg/finance/suppliers", "/bzg/finance/bank", "/bzg/finance/ap"):
            self.assertIn(href, html)
        lower = html.lower()
        for term in FORBIDDEN_HTML:
            self.assertNotIn(term.lower(), lower, f"forbidden {term}")

    def test_permissions_matt_zayen_haikal_amanda(self) -> None:
        ctx = {"entity_id": ENTITY}
        self.assertTrue(desk._can_read_finance(MATT, self.conn))
        self.assertTrue(desk._can_read_finance(ZAYEN, self.conn))
        self.assertFalse(desk._can_read_finance(HAIKAL, self.conn))
        self.assertFalse(desk._can_read_finance(AMANDA, self.conn))
        self.assertTrue(_rbac.can(MATT, "finance.nota.read", ctx, conn=self.conn))
        self.assertTrue(_rbac.can(ZAYEN, "atrium.board.read", ctx, conn=self.conn))
        self.assertFalse(_rbac.can(HAIKAL, "atrium.board.read", ctx, conn=self.conn))
        self.assertFalse(_rbac.can(AMANDA, "atrium.board.read", ctx, conn=self.conn))
        self.assertTrue(_rbac.can(AMANDA, "finance.nota.create", {"entity_id": GGV_ENTITY}, conn=self.conn))
        with self.assertRaises(desk.BzgFinanceError):
            desk.require_board(HAIKAL, self.conn)
        src = (SCRIPTS / "core" / "bzg_finance_desk.py").read_text(encoding="utf-8")
        self.assertNotIn('== "PERS-MATT"', src)
        self.assertNotIn("== 'PERS-MATT'", src)

    def test_bzg_statement_import_entity_isolation(self) -> None:
        before_ggv = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id=?", (GGV_ENTITY,)
        ).fetchone()[0]
        before_amg = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id=?", (AMG_ENTITY,)
        ).fetchone()[0]
        before_bzg = self.conn.execute(
            "SELECT COUNT(*) FROM bzg_bank_transactions WHERE entity_id=?", (ENTITY,)
        ).fetchone()[0]
        with _fce.entity_scope(ENTITY):
            imp = fcs.import_statement(
                verified_person_id=MATT,
                filename="bzg-fc1-statement.csv",
                content=GENERIC_CSV,
                conn=self.conn,
                entity_id=ENTITY,
            )
        self.assertTrue(imp.get("ok") or imp.get("import_id"))
        import_id = imp.get("import_id")
        self.assertTrue(import_id)
        row = self.conn.execute(
            "SELECT entity_id FROM bzg_bank_statement_imports WHERE import_id=?", (import_id,)
        ).fetchone()
        self.assertEqual(row["entity_id"], ENTITY)
        after_ggv = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id=?", (GGV_ENTITY,)
        ).fetchone()[0]
        after_amg = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id=?", (AMG_ENTITY,)
        ).fetchone()[0]
        after_bzg = self.conn.execute(
            "SELECT COUNT(*) FROM bzg_bank_transactions WHERE entity_id=?", (ENTITY,)
        ).fetchone()[0]
        self.assertEqual(before_ggv, after_ggv)
        self.assertEqual(before_amg, after_amg)
        self.assertGreater(after_bzg, before_bzg)
        for eid, table in ((GGV_ENTITY, "ggv_bank_transactions"), (AMG_ENTITY, "ggv_bank_transactions")):
            leak = self.conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE entity_id=? AND description LIKE '%BZG FC1%'",
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

    def test_amg_prove_artifacts_unchanged_ro(self) -> None:
        ro = _ro()
        amg_bank = int(
            ro.execute(
                "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id=?", (AMG_ENTITY,)
            ).fetchone()[0]
        )
        amg_uploads = int(
            ro.execute("SELECT COUNT(*) FROM ggv_uploads WHERE entity_id=?", (AMG_ENTITY,)).fetchone()[0]
        )
        ro.close()
        self.assertEqual(amg_bank, 525)
        self.assertEqual(amg_uploads, 0)

    def test_statement_library_and_idempotent(self) -> None:
        with _fce.entity_scope(ENTITY):
            lib = fcs.list_library(verified_person_id=ZAYEN, conn=self.conn, entity_id=ENTITY)
        self.assertTrue(lib.get("ok") or lib.get("statements") is not None)
        payload = json.dumps(lib)
        for banned in ("ocr", "tesseract", "google vision", "openai", "api error", "provider"):
            self.assertNotIn(banned, payload.lower())
        first = fcs.import_statement(
            verified_person_id=MATT,
            filename="bzg-idem.csv",
            content=GENERIC_CSV,
            conn=self.conn,
            entity_id=ENTITY,
        )
        self.assertTrue(first.get("import_id") or first.get("ok"))
        with self.assertRaises(fcs.FinanceStatementError) as ctx:
            fcs.import_statement(
                verified_person_id=MATT,
                filename="bzg-idem.csv",
                content=GENERIC_CSV,
                conn=self.conn,
                entity_id=ENTITY,
            )
        self.assertEqual(ctx.exception.code, "already_imported")

    def test_honesty_and_bzg_data_only(self) -> None:
        body = desk.overview(ZAYEN, self.conn)
        self.assertFalse(body["staff_ready"])
        self.assertFalse(body["human_commissioned"])
        self.assertFalse(body["zayen_ready"])
        self.assertFalse(body["payment_execute"])
        self.assertFalse(body["money_movement"])
        counts = browse.desk_counts(self.conn)
        self.assertTrue(counts.get("ok"))
        db_counts = counts.get("counts") or {}
        self.assertGreater(db_counts.get("purchase_orders", 0), 0)
        self.assertGreater(db_counts.get("bank_transactions", 0), 0)
        ro = _ro()
        bzg_only = int(ro.execute("SELECT COUNT(*) FROM bzg_ops_purchase_orders").fetchone()[0])
        ro.close()
        self.assertGreater(bzg_only, 0)

    def test_protected_closes_petty_prod_and_routes(self) -> None:
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
        self.assertTrue(desk.matches("/bzg/finance"))
        self.assertTrue(desk.matches("/bzg/finance/bank"))
        self.assertTrue(desk.matches("/api/bzg/finance/statements/library"))
        self.assertFalse(desk.matches("/ggv/finance"))


if __name__ == "__main__":
    unittest.main()
