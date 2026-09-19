#!/usr/bin/env python3
"""ENDED assignment-scopes must survive migrate/seed upserts (Beta).

Insert ACTIVE → end to ENDED → upsert without revive → still ENDED.
Temp DB only. Does not write the live catalog.
"""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

MIG_CLOSE = SCRIPTS / "migrations" / "migrate_uma_blu_daily_close.py"
MIG_ASG = SCRIPTS / "migrations" / "migrate_assignment_scope.py"

PASS = 0
FAIL = 0

DDL = """
CREATE TABLE org_assignment_scopes (
  assignment_id TEXT NOT NULL,
  scope_id TEXT NOT NULL,
  start_at TEXT NOT NULL,
  end_at TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (assignment_id, scope_id, start_at)
);
"""


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def fresh() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(DDL)
    return conn


def row(conn: sqlite3.Connection, assignment_id: str, scope_id: str) -> sqlite3.Row:
    return conn.execute(
        """
        SELECT status, end_at, start_at FROM org_assignment_scopes
        WHERE assignment_id=? AND scope_id=?
        """,
        (assignment_id, scope_id),
    ).fetchone()


def end_row(conn: sqlite3.Connection, assignment_id: str, scope_id: str, end_at: str) -> None:
    conn.execute(
        """
        UPDATE org_assignment_scopes
           SET status='ENDED', end_at=?, updated_at=?
         WHERE assignment_id=? AND scope_id=?
        """,
        (end_at, end_at, assignment_id, scope_id),
    )


def prove_daily_close(mig) -> None:
    conn = fresh()
    ts = "2026-09-19T13:00:00+08:00"
    end_at = "2026-09-19T12:00:00+08:00"
    mig.upsert_asg_scope(conn, "ASG-DEVI-HFB-UMA-1", "SCOPE-BZG-ENTITY", ts)
    before = row(conn, "ASG-DEVI-HFB-UMA-1", "SCOPE-BZG-ENTITY")
    check("daily-close insert starts ACTIVE", before["status"] == "ACTIVE" and before["end_at"] is None)
    end_row(conn, "ASG-DEVI-HFB-UMA-1", "SCOPE-BZG-ENTITY", end_at)
    mig.upsert_asg_scope(conn, "ASG-DEVI-HFB-UMA-1", "SCOPE-BZG-ENTITY", "2026-09-19T13:05:00+08:00")
    after = row(conn, "ASG-DEVI-HFB-UMA-1", "SCOPE-BZG-ENTITY")
    check(
        "daily-close upsert leaves ENDED",
        after["status"] == "ENDED" and after["end_at"] == end_at,
        f"status={after['status']!r} end_at={after['end_at']!r}",
    )
    # Sibling scope that was never ended still seeds ACTIVE.
    mig.upsert_asg_scope(conn, "ASG-DEVI-HFB-UMA-1", "SCOPE-BZG-UMA", ts)
    uma = row(conn, "ASG-DEVI-HFB-UMA-1", "SCOPE-BZG-UMA")
    check("daily-close still seeds a new ACTIVE scope", uma["status"] == "ACTIVE" and uma["end_at"] is None)
    # end_at set without status ENDED is also not cleared.
    conn.execute(
        """
        UPDATE org_assignment_scopes
           SET status='ACTIVE', end_at=?
         WHERE assignment_id=? AND scope_id='SCOPE-BZG-UMA'
        """,
        (end_at, "ASG-DEVI-HFB-UMA-1"),
    )
    mig.upsert_asg_scope(conn, "ASG-DEVI-HFB-UMA-1", "SCOPE-BZG-UMA", ts)
    kept = row(conn, "ASG-DEVI-HFB-UMA-1", "SCOPE-BZG-UMA")
    check(
        "daily-close upsert does not clear a set end_at",
        kept["end_at"] == end_at,
        f"status={kept['status']!r} end_at={kept['end_at']!r}",
    )
    check(
        "set end_at is not rewritten into a live ACTIVE scope",
        not (kept["status"] == "ACTIVE" and kept["end_at"] is None),
        repr(dict(kept)),
    )
    src = MIG_CLOSE.read_text(encoding="utf-8")
    main = src.split("def main", 1)[1]
    check("daily-close main does not pass revive=True", "revive=True" not in main)
    # Owner-only opt-in still works; migrate callers must not use it.
    mig.upsert_asg_scope(
        conn, "ASG-DEVI-HFB-UMA-1", "SCOPE-BZG-ENTITY", ts, revive=True,
    )
    revived = row(conn, "ASG-DEVI-HFB-UMA-1", "SCOPE-BZG-ENTITY")
    check(
        "explicit revive=True is the only reactivation path",
        revived["status"] == "ACTIVE" and revived["end_at"] is None,
        repr(dict(revived)),
    )
    conn.close()


def prove_assignment_scope(mig) -> None:
    conn = fresh()
    start = "2026-09-16T00:00:00+08:00"
    ts = "2026-09-19T13:00:00+08:00"
    end_at = "2026-09-19T11:00:00+08:00"
    mig.upsert_asg_scope(conn, "ASG-MATT-OWNER-1", "SCOPE-GGV-ALL", start, None, "ACTIVE", ts)
    end_row(conn, "ASG-MATT-OWNER-1", "SCOPE-GGV-ALL", end_at)
    mig.upsert_asg_scope(conn, "ASG-MATT-OWNER-1", "SCOPE-GGV-ALL", start, None, "ACTIVE", ts)
    after = row(conn, "ASG-MATT-OWNER-1", "SCOPE-GGV-ALL")
    check(
        "assignment-scope upsert leaves ENDED",
        after["status"] == "ENDED" and after["end_at"] == end_at,
        f"status={after['status']!r} end_at={after['end_at']!r}",
    )
    src = MIG_ASG.read_text(encoding="utf-8")
    main = src.split("def main", 1)[1]
    check("assignment-scope main does not pass revive=True", "revive=True" not in main)
    conn.close()


def prove_peers_delegate() -> None:
    peers = (
        "scripts/migrations/migrate_uma_blu_daily_close.py",
        "scripts/migrations/migrate_assignment_scope.py",
        "scripts/core/decision_memory.py",
        "scripts/migrations/migrate_lead_spine_operator.py",
        "scripts/tests/test_uma_blu_daily_close.py",
        "scripts/tests/test_lead_spine.py",
        "scripts/tests/test_lead_spine_operator.py",
    )
    for rel in peers:
        text = (ROOT / rel).read_text(encoding="utf-8")
        check(
            f"{rel} does not raw-upsert assignment scopes",
            "ON CONFLICT(assignment_id, scope_id, start_at)" not in text,
        )


def main() -> int:
    prove_daily_close(load(MIG_CLOSE, "migrate_uma_blu_daily_close_ended"))
    prove_assignment_scope(load(MIG_ASG, "migrate_assignment_scope_ended"))
    prove_peers_delegate()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
