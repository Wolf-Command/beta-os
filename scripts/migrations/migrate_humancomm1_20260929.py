#!/usr/bin/env python3
"""HUMANCOMM-1 — schema + commissioning copy + legacy routing (Beta catalog).

Decision served: Matt 29 Sep 2026 11:12 START HUMAN COMMISSIONING NOW.
Additive columns + status CHECK rebuild for AWAITING_VERIFY.
Does not touch production :8787 or sidecar :8790.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

BETA_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BETA_ROOT / "scripts"))

from core import universal_my_work as umw  # noqa: E402
from core import work_items as wi  # noqa: E402

CATALOG = BETA_ROOT / "catalog" / "content_library.sqlite"

NEW_COLUMNS = (
    ("human_result", "TEXT"),
    ("human_comment", "TEXT"),
    ("opened_at", "TEXT"),
    ("routing_state", "TEXT"),
    ("routing_reason", "TEXT"),
    ("repair_commit_ref", "TEXT"),
)


def _cols(conn: sqlite3.Connection) -> set[str]:
    return {str(r[1]) for r in conn.execute("PRAGMA table_info(core_work_items)")}


def ensure_columns(conn: sqlite3.Connection) -> list[str]:
    added: list[str] = []
    cols = _cols(conn)
    for col, typ in NEW_COLUMNS:
        if col not in cols:
            conn.execute(f"ALTER TABLE core_work_items ADD COLUMN {col} {typ}")
            added.append(col)
    return added


def status_check_has_awaiting(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='core_work_items'"
    ).fetchone()
    return bool(row and "AWAITING_VERIFY" in (row[0] or ""))


def _rebuild_child_fk(conn: sqlite3.Connection, table: str, create_sql: str) -> None:
    """Recreate a child table so FK points at core_work_items again (SQLite rename quirk)."""
    conn.execute(f"ALTER TABLE {table} RENAME TO {table}_pre_hc1fk")
    conn.execute(create_sql)
    cols = [str(r[1]) for r in conn.execute(f"PRAGMA table_info({table}_pre_hc1fk)")]
    col_list = ", ".join(cols)
    conn.execute(
        f"INSERT INTO {table} ({col_list}) SELECT {col_list} FROM {table}_pre_hc1fk"
    )
    conn.execute(f"DROP TABLE {table}_pre_hc1fk")


def fix_work_item_child_fks(conn: sqlite3.Connection) -> bool:
    """Repair FKs that still point at core_work_items_pre_humancomm1."""
    dirty = False
    for table in ("core_work_evidence_files", "core_work_delegations"):
        fks = conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
        if any("pre_humancomm1" in str(r[2]) for r in fks):
            dirty = True
            break
    if not dirty:
        return False
    conn.execute("PRAGMA foreign_keys=OFF")
    _rebuild_child_fk(
        conn,
        "core_work_evidence_files",
        """
        CREATE TABLE core_work_evidence_files (
          file_id TEXT PRIMARY KEY,
          work_item_id TEXT NOT NULL REFERENCES core_work_items(work_item_id),
          evidence_id TEXT NULL,
          filename TEXT NOT NULL,
          content_type TEXT NULL,
          byte_size INTEGER,
          storage_path TEXT NOT NULL,
          sha256 TEXT NULL,
          uploaded_by_person_id TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
        """,
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_core_work_evidence_files_item "
        "ON core_work_evidence_files(work_item_id)"
    )
    _rebuild_child_fk(
        conn,
        "core_work_delegations",
        """
        CREATE TABLE core_work_delegations (
          delegation_id TEXT PRIMARY KEY,
          work_item_id TEXT NOT NULL REFERENCES core_work_items(work_item_id),
          from_person_id TEXT NOT NULL,
          to_person_id TEXT NOT NULL,
          from_assignment_id TEXT NULL,
          to_assignment_id TEXT NULL,
          status TEXT NOT NULL CHECK (status IN (
            'OFFERED', 'ACCEPTED', 'DECLINED', 'CANCELLED'
          )),
          offered_at TEXT NOT NULL,
          accepted_at TEXT NULL,
          note TEXT NULL,
          created_at TEXT NOT NULL
        )
        """,
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_core_work_delegations_item "
        "ON core_work_delegations(work_item_id)"
    )
    conn.execute("PRAGMA foreign_keys=ON")
    return True


def rebuild_status_check(conn: sqlite3.Connection) -> None:
    """Rebuild table so CHECK allows AWAITING_VERIFY. Preserves all rows."""
    ensure_columns(conn)
    conn.execute("PRAGMA foreign_keys=OFF")
    cols = [
        "work_item_id",
        "title",
        "description",
        "work_type",
        "status",
        "priority",
        "owning_entity_id",
        "source_type",
        "source_id",
        "created_by_actor_type",
        "created_by_person_id",
        "owner_person_id",
        "owner_org_assignment_id",
        "accountable_person_id",
        "executor_person_id",
        "requested_by_person_id",
        "due_at",
        "started_at",
        "completed_at",
        "verified_at",
        "outcome",
        "completion_evidence_reference",
        "parent_work_item_id",
        "origin",
        "import_label",
        "instructions",
        "evidence_required",
        "checklist_json",
        "scope_label",
        "commissioning_capability_id",
        "commissioning_result",
        "what_happens_next",
        "human_result",
        "human_comment",
        "opened_at",
        "routing_state",
        "routing_reason",
        "repair_commit_ref",
        "created_at",
        "updated_at",
    ]
    present = _cols(conn)
    select_cols = ", ".join(c if c in present else f"NULL AS {c}" for c in cols)
    conn.execute("ALTER TABLE core_work_items RENAME TO core_work_items_pre_humancomm1")
    conn.execute(
        """
        CREATE TABLE core_work_items (
          work_item_id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          description TEXT NULL,
          work_type TEXT NOT NULL CHECK (work_type IN (
            'GENERAL', 'FOLLOW_UP', 'EXCEPTION', 'MAINTENANCE',
            'APPROVAL_REQUIRED', 'AUDIT_FINDING', 'CONTENT', 'SYSTEM'
          )),
          status TEXT NOT NULL CHECK (status IN (
            'OPEN', 'IN_PROGRESS', 'BLOCKED', 'WAITING', 'RETURNED',
            'REASSIGNED', 'COMPLETED', 'AWAITING_VERIFY', 'VERIFIED', 'CANCELLED'
          )),
          priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
          owning_entity_id TEXT NOT NULL,
          source_type TEXT NOT NULL CHECK (source_type IN (
            'HUMAN', 'SYSTEM', 'AUDIT', 'ROUTINE', 'RECOMMENDATION_ACCEPTED', 'EXTERNAL'
          )),
          source_id TEXT NULL,
          created_by_actor_type TEXT NOT NULL CHECK (created_by_actor_type IN ('PERSON', 'SYSTEM')),
          created_by_person_id TEXT NULL,
          owner_person_id TEXT NULL,
          owner_org_assignment_id TEXT NULL,
          accountable_person_id TEXT NULL,
          executor_person_id TEXT NULL,
          requested_by_person_id TEXT NULL,
          due_at TEXT NULL,
          started_at TEXT NULL,
          completed_at TEXT NULL,
          verified_at TEXT NULL,
          outcome TEXT NULL,
          completion_evidence_reference TEXT NULL,
          parent_work_item_id TEXT NULL,
          origin TEXT NULL,
          import_label TEXT NULL,
          instructions TEXT NULL,
          evidence_required TEXT NULL,
          checklist_json TEXT NULL,
          scope_label TEXT NULL,
          commissioning_capability_id TEXT NULL,
          commissioning_result TEXT NULL,
          what_happens_next TEXT NULL,
          human_result TEXT NULL,
          human_comment TEXT NULL,
          opened_at TEXT NULL,
          routing_state TEXT NULL,
          routing_reason TEXT NULL,
          repair_commit_ref TEXT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          CHECK (
            (created_by_actor_type = 'SYSTEM' AND created_by_person_id IS NULL)
            OR (created_by_actor_type = 'PERSON' AND created_by_person_id IS NOT NULL)
          )
        )
        """
    )
    conn.execute(
        f"INSERT INTO core_work_items ({', '.join(cols)}) "
        f"SELECT {select_cols} FROM core_work_items_pre_humancomm1"
    )
    conn.execute("DROP TABLE core_work_items_pre_humancomm1")
    for idx_sql in (
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_entity ON core_work_items(owning_entity_id)",
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_owner ON core_work_items(owner_person_id)",
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_status ON core_work_items(status)",
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_due ON core_work_items(due_at)",
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_parent ON core_work_items(parent_work_item_id)",
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_executor ON core_work_items(executor_person_id)",
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_accountable ON core_work_items(accountable_person_id)",
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_origin ON core_work_items(origin)",
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_routing ON core_work_items(routing_state)",
    ):
        conn.execute(idx_sql)
    fix_work_item_child_fks(conn)
    conn.execute("PRAGMA foreign_keys=ON")


def run(*, db_path: Path | None = None, apply_routing: bool = True) -> dict:
    path = Path(db_path) if db_path else CATALOG
    conn = wi.db_connect(path)
    try:
        added = ensure_columns(conn)
        rebuilt = False
        if not status_check_has_awaiting(conn):
            rebuild_status_check(conn)
            rebuilt = True
        fk_fixed = fix_work_item_child_fks(conn)
        copy = umw.refresh_commissioning_copy(conn=conn, commit=False)
        routing = None
        if apply_routing:
            # Idempotent: only route items not already stamped.
            already = conn.execute(
                "SELECT COUNT(*) FROM core_work_items WHERE origin='legacy' AND routing_state IS NOT NULL"
            ).fetchone()[0]
            if int(already or 0) == 0:
                routing = umw.audit_legacy_routing(conn=conn, commit=False)
            else:
                routing = {"skipped": True, "already_stamped": int(already)}
        conn.commit()
        return {
            "ok": True,
            "db": str(path),
            "columns_added": added,
            "status_check_rebuilt": rebuilt,
            "child_fks_fixed": fk_fixed,
            "commissioning_copy": copy,
            "legacy_routing": routing,
        }
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=None)
    ap.add_argument("--skip-routing", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    out = run(db_path=args.db, apply_routing=not args.skip_routing)
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        print(
            f"HUMANCOMM-1 migrate: columns={out['columns_added']} "
            f"rebuilt={out['status_check_rebuilt']} "
            f"copy={out['commissioning_copy']} "
            f"routing_keys={list((out.get('legacy_routing') or {}).keys())}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
