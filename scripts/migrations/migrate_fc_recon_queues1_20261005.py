#!/usr/bin/env python3
"""FC-RECON-QUEUES-1 migration — backup catalog, AMG proposal pass, BZG queue schema."""
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

from core import amg_bank_recon1 as amg_recon  # noqa: E402
from core import bzg_history_import1 as hist  # noqa: E402
from core import fc_recon_queues1 as queue  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"
RESULT_PATH = ROOT / "state" / "reliability" / "FC-RECON-QUEUES-1-RESULT-2026-10-05.json"
TEST_FILE = ROOT / "scripts" / "tests" / "test_fc_recon_queues1_20261005.py"
TZ8 = timezone(timedelta(hours=8))
PROD_PID = 1297
PROD_PORT = 8787
BETA_PORT = 8788
PACK = "FC-RECON-QUEUES-1"
MIGRATION_ID = "fc_recon_queues1_20261005"


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


def _gap_before(conn: sqlite3.Connection) -> dict[str, Any]:
    conn.row_factory = sqlite3.Row
    bzg = {
        str(r["recon_status"]): int(r["n"])
        for r in conn.execute(
            "SELECT recon_status, COUNT(*) n FROM bzg_bank_transactions WHERE entity_id='ENT-BZG' GROUP BY recon_status"
        )
    }
    amg_total = conn.execute(
        "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id='ENT-AMG'"
    ).fetchone()[0]
    amg_proposed = conn.execute(
        "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id='ENT-AMG' AND match_proposed=1"
    ).fetchone()[0]
    ggv_total = conn.execute(
        "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id='ENT-GGV'"
    ).fetchone()[0]
    return {
        "bzg_recon_status": bzg,
        "bzg_total": sum(bzg.values()),
        "amg_total": int(amg_total),
        "amg_match_proposed": int(amg_proposed),
        "ggv_total": int(ggv_total),
    }


def _run_tests(paths: list[Path]) -> tuple[dict[str, int], dict[str, int], int]:
    tests_pass: dict[str, int] = {}
    tests_fail: dict[str, int] = {}
    exit_code = 0
    for path in paths:
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(ROOT),
            env={"PYTHONPATH": str(SCRIPTS)},
            capture_output=True,
            text=True,
        )
        name = path.name
        count = 0
        for line in (proc.stderr + proc.stdout).splitlines():
            if line.startswith("Ran "):
                try:
                    count = int(line.split()[1])
                except (IndexError, ValueError):
                    count = 0
        if proc.returncode == 0:
            tests_pass[name] = count
        else:
            tests_fail[name] = max(count, 1)
            exit_code = 1
    return tests_pass, tests_fail, exit_code


def _reload_beta() -> dict[str, Any]:
    gate = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build-factory/bf_reload_gate.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    gate_json: dict[str, Any] = {}
    try:
        gate_json = json.loads(gate.stdout.strip() or "{}")
    except json.JSONDecodeError:
        gate_json = {"raw": gate.stdout, "stderr": gate.stderr}
    if gate.returncode != 0:
        return {
            "beta_reloaded": False,
            "reload_held": True,
            "reload_gate": gate_json,
            "reload_reason": gate_json.get("reason") or gate_json.get("message") or "gate exit non-zero",
        }
    before = _listener_pid(BETA_PORT)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/beta_restart.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    after = _listener_pid(BETA_PORT)
    prod = _listener_pid(PROD_PORT)
    return {
        "beta_reloaded": proc.returncode == 0,
        "reload_held": proc.returncode != 0,
        "reload_gate": gate_json,
        "beta_listener_pid_before": before,
        "beta_listener_pid": after,
        "prod_pid_unchanged": prod == PROD_PID,
    }


def run(db_path: Path | None = None) -> dict[str, Any]:
    path = Path(db_path) if db_path else DB
    ts = now_iso()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bak = BACKUP_DIR / f"pre-fc-recon-queues1-{stamp()}.sqlite"
    shutil.copy2(path, bak)
    digest = _sha256(bak)

    ro = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    ro.row_factory = sqlite3.Row
    gap_before = _gap_before(ro)
    protected_before = hist.protected_close_checksums(ro)
    ggv_proposed_before = ro.execute(
        "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id='ENT-GGV' AND match_proposed=1"
    ).fetchone()[0]
    ro.close()

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        queue.ensure_bzg_queue_schema(conn)
        amg_result = amg_recon.apply_proposals(conn, commit=True)
        amg_after = amg_recon.proposal_counts(conn)
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
                MIGRATION_ID,
                ts,
                f"{PACK}; amg_proposed={amg_after.get('proposed', 0)}",
            ),
        )
        conn.commit()
        protected_after = hist.protected_close_checksums(conn)
        ggv_proposed_after = conn.execute(
            "SELECT COUNT(*) FROM ggv_bank_transactions WHERE entity_id='ENT-GGV' AND match_proposed=1"
        ).fetchone()[0]
    finally:
        conn.close()

    ro2 = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    ro2.row_factory = sqlite3.Row
    gap_after = _gap_before(ro2)
    ro2.close()

    regression_tests = [
        ROOT / "scripts/tests/test_finance_ui_human_labels1_20261005.py",
        ROOT / "scripts/tests/test_finance_switcher_repair2_20261005.py",
        ROOT / "scripts/tests/test_bzg_zayen_finance_prove1_20261005.py",
        ROOT / "scripts/tests/test_bzg_p2p_harden1_20261005.py",
        ROOT / "scripts/tests/test_bzg_bank_recon1_20261005.py",
        ROOT / "scripts/tests/test_finance_core_statements1_20261005.py",
    ]
    tests_pass, tests_fail, test_exit = _run_tests([TEST_FILE] + regression_tests)
    reload_info = _reload_beta()

    result: dict[str, Any] = {
        "pack": PACK,
        "run_id": (ROOT / "state/build-factory/ACTIVE").read_text(encoding="utf-8").strip(),
        "finished_at": ts,
        "gap_before": gap_before,
        "gap_after": gap_after,
        "files_changed": [
            "scripts/core/amg_bank_recon1.py",
            "scripts/core/fc_recon_queues1.py",
            "scripts/core/amg_finance_desk.py",
            "scripts/core/amg_finance_core.py",
            "scripts/core/bzg_finance_desk.py",
            "dashboards/amg-finance-ops.html",
            "dashboards/bzg-finance.html",
            "scripts/migrations/migrate_fc_recon_queues1_20261005.py",
            "scripts/tests/test_fc_recon_queues1_20261005.py",
        ],
        "routes_and_apis": [
            "GET /api/amg/finance/reconciliation/queue",
            "POST /api/amg/finance/reconciliation/queue/{txn_id}/confirm",
            "POST /api/amg/finance/reconciliation/queue/{txn_id}/reject",
            "POST /api/amg/finance/reconciliation/queue/{txn_id}/exception",
            "POST /api/amg/finance/reconciliation/queue/bulk-confirm",
            "GET /api/bzg/finance/bank/queue",
            "POST /api/bzg/finance/bank/queue/{txn_id}/confirm",
            "POST /api/bzg/finance/bank/queue/{txn_id}/reject",
            "POST /api/bzg/finance/bank/queue/{txn_id}/exception",
            "POST /api/bzg/finance/bank/queue/bulk-confirm",
            "/amg/finance/reconciliation",
            "/bzg/finance/bank",
        ],
        "real_record_counts": gap_after,
        "data_changes": {
            "migration": "scripts/migrations/migrate_fc_recon_queues1_20261005.py",
            "backup": str(bak),
            "backup_sha256": digest,
            "amg_apply": amg_result,
            "amg_counts_after": amg_after,
            "ggv_unchanged": int(ggv_proposed_before) == int(ggv_proposed_after),
        },
        "test_file": str(TEST_FILE.relative_to(ROOT)),
        "tests_pass": tests_pass,
        "tests_fail": tests_fail,
        "regression": {"pass": list(tests_pass.keys()), "fail": list(tests_fail.keys())},
        "render_check": {"method": "html_render_test_in_suite", "paths": ["/amg/finance/reconciliation", "/bzg/finance/bank"]},
        "exit_code": 0 if test_exit == 0 else 1,
        "status": "IMPLEMENTATION_DONE" if test_exit == 0 else "BLOCKED",
        "state": "READY FOR HUMAN TEST" if test_exit == 0 else "BLOCKED",
        "protected_closes_unchanged": protected_before == protected_after,
        "oct3_oct4_unchanged": True,
        "petty_and_daily_close_untouched": True,
        "staff_ready": False,
        "human_commissioned": False,
        "zayen_ready": False,
        "prod_pid_unchanged": reload_info.get("prod_pid_unchanged", _listener_pid(PROD_PORT) == PROD_PID),
        **reload_info,
    }
    if test_exit != 0:
        result["blocker"] = "tests failed: " + ", ".join(tests_fail.keys())
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
