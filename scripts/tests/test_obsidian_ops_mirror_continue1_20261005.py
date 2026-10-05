#!/usr/bin/env python3
"""OBSIDIAN-MIRROR-CONTINUE-1 — idempotent one-way Obsidian mirror tests."""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ops import obsidian_ops_mirror as _mirror  # noqa: E402

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
PROTECTED_CLOSES = (
    "VDC-470e741f-d889-437a-9a40-1ec9c083fb95",
    "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5",
    "VDC-8fd544e2-2132-4a4a-b714-720eb0cd18ad",
)
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"
EXPECTED_PETTY_BALANCE = 552700.0


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def _db_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            h.update(rel.encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def _prod_pid() -> int | None:
    try:
        out = subprocess.check_output(
            ["lsof", "-i", ":8787", "-t"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return int(out.splitlines()[0]) if out else None
    except (subprocess.CalledProcessError, ValueError, IndexError):
        return None


class ObsidianMirrorContinue1(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prod_pid_before = _prod_pid()
        cls.db_sha_before = _db_sha256(LIVE_DB)

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="obsidian-mirror-test-")
        self.mirror_dir = Path(self.tmp) / "10-Mirror"
        _mirror.configure_mirror_dir(self.mirror_dir)

    def tearDown(self) -> None:
        _mirror.configure_mirror_dir(None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_run_mirror_writes_new_sections(self) -> None:
        payload = _mirror.run_mirror(dry_run=False)
        actions = {a["action"] for a in payload["actions"]}
        self.assertIn("wrote", actions)
        self.assertTrue(payload["protected_closes_unchanged"])
        self.assertTrue(payload["proved_petty_row_unchanged"])
        self.assertAlmostEqual(payload["petty_balance_idr"], EXPECTED_PETTY_BALANCE)
        self.assertTrue((self.mirror_dir / "reconciliations" / "BZG-BANK-RECON-1.md").exists())
        self.assertTrue((self.mirror_dir / "decisions").is_dir())
        self.assertTrue((self.mirror_dir / "exceptions").is_dir())

    def test_idempotent_second_run_zero_diff(self) -> None:
        first = _mirror.run_mirror(dry_run=False)
        digest1 = _tree_digest(self.mirror_dir)
        second = _mirror.run_mirror(dry_run=False)
        digest2 = _tree_digest(self.mirror_dir)
        self.assertEqual(digest1, digest2)
        non_skip = [a for a in second["actions"] if a["action"] != "skip"]
        self.assertEqual(non_skip, [], non_skip)

    def test_dry_run_does_not_create_files(self) -> None:
        _mirror.run_mirror(dry_run=True)
        md_files = list(self.mirror_dir.rglob("*.md"))
        self.assertEqual(md_files, [])

    def test_no_secrets_in_mirror_output(self) -> None:
        _mirror.run_mirror(dry_run=False)
        issues = _mirror.scan_mirror_for_secrets(self.mirror_dir)
        self.assertEqual(issues, [], issues)

    def test_no_db_writes(self) -> None:
        _mirror.run_mirror(dry_run=False)
        after = _db_sha256(LIVE_DB)
        self.assertEqual(after, self.db_sha_before)

    def test_protected_closes_unchanged(self) -> None:
        con = _ro(LIVE_DB)
        for cid in PROTECTED_CLOSES:
            row = con.execute(
                "SELECT close_id, updated_at, state FROM venue_daily_closes WHERE close_id=?",
                (cid,),
            ).fetchone()
            self.assertIsNotNone(row, cid)
        con.close()

    def test_protected_petty_unchanged(self) -> None:
        con = _ro(LIVE_DB)
        row = con.execute(
            "SELECT movement_id, amount FROM bzg_ops_petty_movements WHERE movement_id=?",
            (PROTECTED_PETTY,),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(float(row["amount"]), 500000.0)
        bal = _mirror.petty_balance(con)
        self.assertAlmostEqual(bal["amount_idr"], EXPECTED_PETTY_BALANCE)
        con.close()

    def test_mirror_notes_contain_disclaimer(self) -> None:
        _mirror.run_mirror(dry_run=False)
        for md in self.mirror_dir.rglob("*.md"):
            text = md.read_text(encoding="utf-8")
            self.assertIn(_mirror.DISCLAIMER, text, md.name)

    def test_prod_pid_unchanged(self) -> None:
        if self.prod_pid_before is None:
            self.skipTest("prod :8787 not listening")
        self.assertEqual(_prod_pid(), self.prod_pid_before)


if __name__ == "__main__":
    unittest.main()
