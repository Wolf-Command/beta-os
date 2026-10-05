#!/usr/bin/env python3
"""FINANCE-CORE-STATEMENTS-1 — shared bank statement library proving."""
from __future__ import annotations

import hashlib
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

from core import finance_core_entity as _fce  # noqa: E402
from core import finance_core_statements as fcs  # noqa: E402
from core import ggv_bank_statement1 as gbs  # noqa: E402
from core import ggv_finance_desk as gdesk  # noqa: E402
from core import ggv_finance_nota as fin  # noqa: E402
from core import rbac as _rbac  # noqa: E402

LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"
DASHBOARD = ROOT / "dashboards" / "ggv-finance.html"

MATT = "PERS-MATT"
AMANDA = "PERS-AMANDA"
ZAYEN = "PERS-ZAYEN"

GGV_HIST = Path(
    "~/.openclaw/workspace/wolf-system/state/shareholder-bank-statements/GGV/Mandiri-1610015100972"
).expanduser()
GGV_PDF = GGV_HIST / "account_statement_asof_20260630.pdf"
GGV_MAY_CSV = GGV_HIST / "Acc_Statement_1610015100972_2026-05-01_2026-05-31_20260603180944.csv"
GGV_JUL_AUG_CSV = GGV_HIST / "Acc_Statement_1610015100972_2026-07-01_2026-08-31_matthew-drop-20260905.csv"
AMG_STMT_DIR = Path("~/.openclaw/workspace/wolf-system/atrium/statements").expanduser()
CIMB_PDF = AMG_STMT_DIR / "CKM-800203739400-2026-08-CIMB-E-Statement.pdf"
BZG_BRI = ROOT / "state/bzg-bank-statements/originals"
BZG_BNI = ROOT / "state/bzg-bank-statements/originals/BNI-2177177110_2026-04.xls"

PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
)
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"
PROD_PID = 1297

GGV_PROVE_FIXTURE_IDS = (
    "GBSI-cf68360b-e9c0-47eb-84d9-ae11f38364b7",
    "GBSI-2608830d-db1b-4966-8d14-f114d45a2a6d",
)

STATEMENT_TABLES = (
    "ggv_bank_transactions",
    "ggv_bank_statement_imports",
    "bzg_bank_transactions",
    "bzg_bank_statement_imports",
)


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def _clear_statement_tables(conn: sqlite3.Connection) -> None:
    """Empty statement import/txn rows in temp DB only — live catalog stays read-only."""
    tables = _table_names(conn)
    for table in STATEMENT_TABLES:
        if table in tables:
            conn.execute(f"DELETE FROM {table}")
    conn.commit()


def _seed_ggv_prove_fixtures(conn: sqlite3.Connection) -> None:
    ts = "2026-10-03T00:00:00Z"
    for n, import_id in enumerate(GGV_PROVE_FIXTURE_IDS):
        conn.execute(
            """
            INSERT INTO ggv_bank_statement_imports (
              import_id, entity_id, bank_label, original_filename, original_path,
              content_sha256, uploaded_by_person_id, uploaded_at, txn_count, parse_status
            ) VALUES (?, 'ENT-GGV', 'MANDIRI', 'ggv-prove-statement.csv', ?, ?, ?, ?, 0, 'OK')
            """,
            (
                import_id,
                f"fixture/{import_id}.csv",
                f"prove-fixture-sha256-{n}",
                MATT,
                ts,
            ),
        )


def _ro(path: Path | None = None) -> sqlite3.Connection:
    p = path or LIVE_CATALOG
    conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


class FinanceCoreStatements1Tests(unittest.TestCase):
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
        self.orig_ggv = Path(tempfile.mkdtemp(prefix="stmt1-ggv-orig-"))
        self.orig_amg = Path(tempfile.mkdtemp(prefix="stmt1-amg-orig-"))
        self.orig_bzg = Path(tempfile.mkdtemp(prefix="stmt1-bzg-orig-"))
        fin.CATALOG_DB = self._db_path
        fcs.CATALOG_DB = self._db_path
        gbs.CATALOG_DB = self._db_path

        def _orig(entity_id=None):
            eid = entity_id or _fce.active_entity()
            if eid == "ENT-AMG":
                return self.orig_amg
            if eid == "ENT-BZG":
                return self.orig_bzg
            return self.orig_ggv

        self._orig_patch = unittest.mock.patch.object(fcs, "_originals_dir", _orig)
        self._orig_patch.start()
        fin.ensure_schema(self.conn)
        fin.ensure_rbac(self.conn, commit=True)
        fcs.ensure_schema(self.conn)
        _clear_statement_tables(self.conn)
        _seed_ggv_prove_fixtures(self.conn)
        fcs.flag_ggv_prove_fixtures(self.conn)
        self.conn.commit()

    def tearDown(self) -> None:
        self._orig_patch.stop()
        _fce._entity_ctx.set(_fce.DEFAULT_ENTITY)
        self.conn.close()
        shutil.rmtree(self.orig_ggv, ignore_errors=True)
        shutil.rmtree(self.orig_amg, ignore_errors=True)
        shutil.rmtree(self.orig_bzg, ignore_errors=True)
        if self._db_path.is_file():
            self._db_path.unlink(missing_ok=True)

    def _import_ggv_historical(self) -> None:
        if GGV_PDF.is_file():
            fcs.import_statement(
                verified_person_id=MATT,
                filename=GGV_PDF.name,
                content=GGV_PDF.read_bytes(),
                conn=self.conn,
                entity_id="ENT-GGV",
            )

    def test_library_hides_ggv_prove_fixtures(self) -> None:
        lib = fcs.list_library(verified_person_id=MATT, conn=self.conn, entity_id="ENT-GGV")
        ids = {s.get("statement_id") for s in lib.get("statements") or []}
        self.assertNotIn("GBSI-cf68360b-e9c0-47eb-84d9-ae11f38364b7", ids)
        self.assertNotIn("GBSI-2608830d-db1b-4966-8d14-f114d45a2a6d", ids)
        flagged = self.conn.execute(
            "SELECT COUNT(*) FROM ggv_bank_statement_imports WHERE is_test_fixture=1 AND entity_id='ENT-GGV'"
        ).fetchone()[0]
        self.assertGreaterEqual(int(flagged), 2)

    def test_entity_isolation(self) -> None:
        self._import_ggv_historical()
        with _fce.entity_scope("ENT-GGV"):
            ggv = fcs.list_library(verified_person_id=MATT, conn=self.conn)
        with _fce.entity_scope("ENT-AMG"):
            amg = fcs.list_library(verified_person_id=MATT, conn=self.conn)
        bzg = fcs.list_library(verified_person_id=ZAYEN, conn=self.conn, entity_id="ENT-BZG")
        ggv_ids = {s["statement_id"] for s in ggv.get("statements") or []}
        self.assertTrue(ggv_ids)
        for sid in ggv_ids:
            with self.assertRaises(fcs.FinanceStatementError):
                fcs.get_statement(verified_person_id=MATT, import_id=sid, conn=self.conn, entity_id="ENT-AMG")
        if (amg.get("statements") or []):
            for sid in {s["statement_id"] for s in amg["statements"]}:
                with self.assertRaises(fcs.FinanceStatementError):
                    fcs.get_statement(verified_person_id=MATT, import_id=sid, conn=self.conn, entity_id="ENT-GGV")

    def test_idempotency_and_overlap(self) -> None:
        if not GGV_PDF.is_file() or not GGV_MAY_CSV.is_file():
            self.skipTest("GGV historical fixtures missing")
        pdf_bytes = GGV_PDF.read_bytes()
        first = fcs.import_statement(
            verified_person_id=MATT, filename=GGV_PDF.name, content=pdf_bytes, conn=self.conn, entity_id="ENT-GGV"
        )
        before = self.conn.execute(
            """
            SELECT COUNT(*) FROM ggv_bank_transactions t
            JOIN ggv_bank_statement_imports i ON i.import_id=t.import_id
            WHERE t.entity_id='ENT-GGV' AND COALESCE(i.is_test_fixture,0)=0
            """
        ).fetchone()[0]
        with self.assertRaises(fcs.FinanceStatementError) as ctx:
            fcs.import_statement(
                verified_person_id=MATT, filename=GGV_PDF.name, content=pdf_bytes, conn=self.conn, entity_id="ENT-GGV"
            )
        self.assertEqual(ctx.exception.code, "already_imported")
        after_dup = self.conn.execute(
            """
            SELECT COUNT(*) FROM ggv_bank_transactions t
            JOIN ggv_bank_statement_imports i ON i.import_id=t.import_id
            WHERE t.entity_id='ENT-GGV' AND COALESCE(i.is_test_fixture,0)=0
            """
        ).fetchone()[0]
        self.assertEqual(before, after_dup)
        with self.assertRaises(fcs.FinanceStatementError) as ctx2:
            fcs.import_statement(
                verified_person_id=MATT,
                filename=GGV_MAY_CSV.name,
                content=GGV_MAY_CSV.read_bytes(),
                conn=self.conn,
                entity_id="ENT-GGV",
            )
        self.assertEqual(ctx2.exception.code, "possible_duplicate_import")
        after_overlap = self.conn.execute(
            """
            SELECT COUNT(*) FROM ggv_bank_transactions t
            JOIN ggv_bank_statement_imports i ON i.import_id=t.import_id
            WHERE t.entity_id='ENT-GGV' AND COALESCE(i.is_test_fixture,0)=0
            """
        ).fetchone()[0]
        self.assertEqual(before, after_overlap)

    def test_raw_preserved(self) -> None:
        if not GGV_JUL_AUG_CSV.is_file():
            self.skipTest("GGV Jul-Aug CSV missing")
        content = GGV_JUL_AUG_CSV.read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        imp = fcs.import_statement(
            verified_person_id=MATT,
            filename=GGV_JUL_AUG_CSV.name,
            content=content,
            conn=self.conn,
            entity_id="ENT-GGV",
        )
        raw, _mime, _fname = fcs.original_bytes(
            verified_person_id=MATT, import_id=imp["import_id"], conn=self.conn, entity_id="ENT-GGV"
        )
        self.assertEqual(hashlib.sha256(raw).hexdigest(), sha)
        detail = fcs.get_statement(
            verified_person_id=MATT, import_id=imp["import_id"], conn=self.conn, entity_id="ENT-GGV"
        )
        txns = detail["statement"].get("transactions") or []
        self.assertGreater(len(txns), 0)
        self.assertIn("raw", txns[0])

    def test_parsers_real_files(self) -> None:
        if GGV_MAY_CSV.is_file():
            meta, rows, notes = fcs.parse_statement_bytes(GGV_MAY_CSV.read_bytes(), GGV_MAY_CSV.name)
            self.assertEqual(meta.get("bank_label"), "MANDIRI")
            self.assertTrue(meta.get("account_number"))
            self.assertGreater(len(rows), 0)
            self.assertIn("mandiri", notes)
        if GGV_PDF.is_file():
            meta, rows, notes = fcs.parse_statement_bytes(GGV_PDF.read_bytes(), GGV_PDF.name)
            self.assertEqual(meta.get("bank_label"), "MANDIRI")
            self.assertIsNotNone(meta.get("opening_balance"))
            self.assertIsNotNone(meta.get("closing_balance"))
            self.assertGreater(len(rows), 0)
        bri_files = list(BZG_BRI.glob("Acc_Statement_*BRI*.csv")) + list(BZG_BRI.glob("Acc_Statement_1610555335558*.csv"))
        if bri_files:
            content = bri_files[0].read_bytes()
            meta, rows, notes = fcs.parse_statement_bytes(content, bri_files[0].name)
            self.assertIn(meta.get("bank_label"), ("MANDIRI", "BRI"))
            self.assertGreater(len(rows), 0)
        if CIMB_PDF.is_file():
            meta, rows, notes = fcs.parse_statement_bytes(CIMB_PDF.read_bytes(), CIMB_PDF.name)
            self.assertEqual(meta.get("bank_label"), "CIMB")
            self.assertTrue(meta.get("account_number"))
        if BZG_BNI.is_file():
            with self.assertRaises(fcs.FinanceStatementError):
                fcs.parse_statement_bytes(BZG_BNI.read_bytes(), BZG_BNI.name)

    def test_completeness_strip_missing_months(self) -> None:
        self._import_ggv_historical()
        comp = fcs.month_completeness(verified_person_id=MATT, conn=self.conn, entity_id="ENT-GGV", as_of="2026-10-05")
        acct = (comp.get("accounts") or [None])[0]
        self.assertIsNotNone(acct)
        labels = [m.get("label", "") for m in acct.get("months") or []]
        self.assertTrue(any("MISSING STATEMENT" in l for l in labels))
        self.assertTrue(any("CURRENT" in l or "ON FILE" in l for l in labels))

    def test_permissions(self) -> None:
        self.assertTrue(_rbac.can(MATT, "finance.nota.read", {"entity_id": "ENT-GGV"}, conn=self.conn))
        self.assertTrue(_rbac.can(MATT, "finance.nota.read", {"entity_id": "ENT-AMG"}, conn=self.conn))
        self.assertTrue(_rbac.can(ZAYEN, "atrium.board.read", {"entity_id": "ENT-BZG"}, conn=self.conn))
        self.assertFalse(_rbac.can(ZAYEN, "finance.nota.read", {"entity_id": "ENT-GGV"}, conn=self.conn))
        self.assertTrue(_rbac.can(ZAYEN, "atrium.board.read", {"entity_id": "ENT-AMG"}, conn=self.conn))
        self.assertTrue(_rbac.can(ZAYEN, "atrium.board.read", {"entity_id": "ENT-BZG"}, conn=self.conn))
        self.assertTrue(_rbac.can(AMANDA, "finance.nota.read", {"entity_id": "ENT-GGV"}, conn=self.conn))
        self.assertFalse(_rbac.can(AMANDA, "atrium.board.read", {"entity_id": "ENT-AMG"}, conn=self.conn))
        with self.assertRaises(gdesk.GgvFinanceDeskError) as ctx:
            gdesk.desk_overview(ZAYEN, self.conn)
        self.assertEqual(ctx.exception.code, "forbidden")
        with unittest.mock.patch.object(fin, "_open_ready", lambda: self.conn):
            with self.assertRaises(fin.FinanceNotaError) as ctx2:
                fin.dispatch("GET", "/api/ggv/finance/desk", {}, None, ZAYEN)
        self.assertEqual(ctx2.exception.code, "forbidden")
        self.assertEqual(ctx2.exception.http_status, 403)

    def test_ggv_home_primary_actions(self) -> None:
        html = DASHBOARD.read_text(encoding="utf-8")
        for label in (
            "UPLOAD STATEMENT",
            "UPLOAD NOTA / RECEIPT",
            "HISTORICAL STATEMENTS",
            "RECONCILIATION",
        ):
            self.assertIn(label, html)

    def test_ggv_history_counts_unchanged(self) -> None:
        ro = _ro()
        counts = gdesk.desk_counts(ro)
        ro.close()
        self.assertEqual(counts["invoices"], 46)
        self.assertEqual(counts["notas"], 33)
        self.assertEqual(counts["bills"], 605)

    def test_protected_closes_petty_prod(self) -> None:
        ro = _ro()
        for cid in PROTECTED_CLOSES:
            self.assertIsNotNone(
                ro.execute("SELECT state FROM venue_daily_closes WHERE close_id=?", (cid,)).fetchone()
            )
        from core import bzg_history_import1 as _hist

        balance = _hist.petty_balance(ro)
        ro.close()
        self.assertEqual(float(balance["amount_idr"]), 552700.0)
        try:
            os.kill(PROD_PID, 0)
            alive = True
        except OSError:
            alive = False
        self.assertTrue(alive)


if __name__ == "__main__":
    unittest.main()
