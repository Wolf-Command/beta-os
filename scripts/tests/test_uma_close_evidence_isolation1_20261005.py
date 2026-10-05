#!/usr/bin/env python3
"""UMA-CLOSE-EVIDENCE-ISOLATION-1 — guard test: probe-style writes never hit live receipts."""
from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

LIVE_RECEIPTS = ROOT / "state" / "bzg-daily-close" / "receipts"
LIVE_CATALOG = ROOT / "catalog" / "content_library.sqlite"


def _live_receipt_snapshot() -> dict[str, str]:
    snap: dict[str, str] = {}
    if not LIVE_RECEIPTS.is_dir():
        return snap
    for p in LIVE_RECEIPTS.iterdir():
        if p.is_file():
            snap[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return snap


class EvidenceIsolationGuardTest(unittest.TestCase):
    def test_probe_style_write_zero_live_files(self) -> None:
        before = _live_receipt_snapshot()
        scratch = Path(tempfile.mkdtemp(prefix="uma-close-evidence-isolation-"))
        evidence_root = scratch / "evidence"
        db_path = scratch / "catalog.sqlite"
        shutil.copy2(LIVE_CATALOG, db_path)
        os.environ["WOLF_TEST_MODE"] = "1"
        os.environ["WOLF_EVIDENCE_ROOT"] = str(evidence_root)
        try:
            from core import bzg_daily_close as bzg
            from core import venue_close as vc

            vc.CATALOG_DB = db_path
            bzg.CLOSE_RECEIPT_DIR = evidence_root / "bzg-daily-close" / "receipts"
            data = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xcf"
                b"\xc0\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4\xef\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            stored = bzg.save_close_receipt_bytes(
                data=data,
                kind="esb",
                close_id="VDC-PROBE-ISOLATION-TEST",
                filename="probe-test.png",
                content_type="image/png",
            )
            self.assertTrue(stored.get("ok"))
            self.assertTrue((bzg.CLOSE_RECEIPT_DIR / Path(stored["path"]).name).is_file())
            after = _live_receipt_snapshot()
            self.assertEqual(before, after, "live receipt dir must be unchanged")
        finally:
            os.environ.pop("WOLF_TEST_MODE", None)
            os.environ.pop("WOLF_EVIDENCE_ROOT", None)
            shutil.rmtree(scratch, ignore_errors=True)

    def test_live_write_refused_without_evidence_root(self) -> None:
        scratch = Path(tempfile.mkdtemp(prefix="uma-close-evidence-refuse-"))
        db_path = scratch / "catalog.sqlite"
        shutil.copy2(LIVE_CATALOG, db_path)
        os.environ["WOLF_TEST_MODE"] = "1"
        os.environ.pop("WOLF_EVIDENCE_ROOT", None)
        try:
            from core import bzg_daily_close as bzg
            from core import venue_close as vc

            vc.CATALOG_DB = db_path
            bzg.CLOSE_RECEIPT_DIR = LIVE_RECEIPTS
            probe_png = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xcf"
                b"\xc0\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4\xef\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            with self.assertRaises(RuntimeError):
                bzg.save_close_receipt_bytes(
                    data=probe_png,
                    kind="esb",
                    close_id="VDC-PROBE-REFUSE",
                    filename="probe.png",
                    content_type="image/png",
                )
        finally:
            os.environ.pop("WOLF_TEST_MODE", None)
            shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
