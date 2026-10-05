#!/usr/bin/env python3
"""BZG-BANK-RECON-1 migration — backup catalog, apply deterministic bank recon states."""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core import bzg_bank_recon1 as recon  # noqa: E402
from core import bzg_history_import1 as hist  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"

# Owner P0 5 Oct 2026: retention/free-space guard (docs/BACKUP-RETENTION.md)
import sys as _bp_sys  # noqa: E402
if str(ROOT / "scripts") not in _bp_sys.path:
    _bp_sys.path.insert(0, str(ROOT / "scripts"))
from core.backup_policy import premig_backup  # noqa: E402
RESULT_PATH = ROOT / "state" / "reliability" / "BZG-BANK-RECON-1-RESULT-2026-10-05.json"
TEST_FILE = ROOT / "scripts" / "tests" / "test_bzg_bank_recon1_20261005.py"
TZ8 = timezone(timedelta(hours=8))
PROD_PID = 1297
PROD_PORT = 8787
BETA_PORT = 8788


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(TZ8).strftime("%Y%m%d-%H%M%S")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def _beta_listener_count() -> int:
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{BETA_PORT}", "-sTCP:LISTEN", "-t"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if not out:
            return 0
        return len([ln for ln in out.splitlines() if ln.strip()])
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 0


def _run_tests() -> tuple[dict[str, int], dict[str, int], int]:
    proc = subprocess.run(
        [sys.executable, str(TEST_FILE)],
        cwd=str(ROOT),
        env={"PYTHONPATH": str(SCRIPTS)},
        capture_output=True,
        text=True,
    )
    passed = proc.returncode == 0
    count = 0
    for line in (proc.stderr + proc.stdout).splitlines():
        if line.startswith("Ran "):
            try:
                count = int(line.split()[1])
            except (IndexError, ValueError):
                count = 0
    if passed:
        return {"test_bzg_bank_recon1_20261005.py": count}, {}, proc.returncode
    return {}, {"test_bzg_bank_recon1_20261005.py": max(count, 1)}, proc.returncode


def _reload_beta() -> dict[str, Any]:
    listeners = _beta_listener_count()
    if listeners != 1:
        return {
            "beta_reloaded": False,
            "reload_held": True,
            "reload_reason": f"expected exactly one listener on {BETA_PORT}, found {listeners}",
        }
    before = _listener_pid(BETA_PORT)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "beta_restart.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    after = _listener_pid(BETA_PORT)
    return {
        "beta_reloaded": proc.returncode == 0,
        "reload_held": proc.returncode != 0,
        "beta_listener_pid_before": before,
        "beta_listener_pid": after,
        "beta_port": BETA_PORT,
    }


def run(db_path: Path | None = None) -> dict:
    path = Path(db_path) if db_path else DB
    ts = now_iso()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bak = BACKUP_DIR / f"pre-bzg-bank-recon1-{stamp()}.sqlite"
    bak = premig_backup(path, bak)
    digest = _sha256(bak)

    ro = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    ro.row_factory = sqlite3.Row
    protected_before = hist.protected_close_checksums(ro)
    ro.close()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        apply_result = recon.apply_recon_states(conn, commit=True)
        summary = recon.recon_summary(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (
                recon.MIGRATION_ID,
                ts,
                f"{recon.PACK}; txns={summary['transaction_count']}; matched={summary['state_counts'].get('MATCHED', 0)}",
            ),
        )
        conn.commit()
        protected_after = hist.protected_close_checksums(conn)
    finally:
        conn.close()

    tests_pass, tests_fail, test_exit = _run_tests()
    reload_info = _reload_beta()
    prod_pid = _listener_pid(PROD_PORT)

    result: dict[str, Any] = {
        "pack": recon.PACK,
        "finished_at": ts,
        "backup": str(bak),
        "backup_sha256": digest,
        "migration": "scripts/migrations/migrate_bzg_bank_recon1_20261005.py",
        "core": "scripts/core/bzg_bank_recon1.py",
        "test_file": str(TEST_FILE.relative_to(ROOT)),
        "apply_result": apply_result,
        "summary": summary,
        "tests_pass": tests_pass,
        "tests_fail": tests_fail,
        "exit_code": 0 if test_exit == 0 else 1,
        "status": "IMPLEMENTATION_DONE" if test_exit == 0 else "BLOCKED tests failed",
        "prod_pid_unchanged": prod_pid == PROD_PID,
        "prod_port": PROD_PORT,
        "protected_closes_unchanged": protected_before == protected_after,
        "staff_ready": False,
        "human_commissioned": False,
        "zayen_ready": False,
        "no_commit": True,
        "no_money_movement": True,
        "read_only": True,
        "files_changed": [
            "scripts/core/bzg_bank_recon1.py",
            "scripts/migrations/migrate_bzg_bank_recon1_20261005.py",
            "scripts/core/bzg_finance_usability_ro.py",
            "scripts/core/bzg_finance_desk.py",
            "dashboards/bzg-finance.html",
            "scripts/tests/test_bzg_bank_recon1_20261005.py",
        ],
        **reload_info,
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
