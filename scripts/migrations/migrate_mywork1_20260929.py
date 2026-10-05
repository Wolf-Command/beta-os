#!/usr/bin/env python3
"""MYWORK-1 — assignments, schema, commissioning seed, legacy import (Beta).

Decision served: Matt 29 Sep 2026 07:20 P0 UNIVERSAL MY WORK.
Extends Wolf Core Work Items / Assignment / Scope / Evidence. No second task engine.
Nobody becomes staff_ready or human_commissioned. No ClickUp/ESB/Xero writes.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

DB = ROOT / "catalog" / "content_library.sqlite"
SQL = Path(__file__).resolve().parent / "030_mywork1_universal.sql"
BACKUP_DIR = ROOT / "catalog" / "backups"

# Owner P0 5 Oct 2026: retention/free-space guard (docs/BACKUP-RETENTION.md)
import sys as _bp_sys  # noqa: E402
if str(ROOT / "scripts") not in _bp_sys.path:
    _bp_sys.path.insert(0, str(ROOT / "scripts"))
from core.backup_policy import premig_backup  # noqa: E402
LEGACY_PROPOSAL = ROOT / "state" / "legacy" / "proposed-migration.json"
CUT_LINE = ROOT / "state" / "legacy" / "clickup-cut-line.json"
IMPORT_RECEIPT = ROOT / "state" / "legacy" / "mywork1-import-receipt.json"
TZ8 = timezone(timedelta(hours=8))
MIGRATION_ID = "030_mywork1_universal"

# --- Part A constants ---
ZAYEN = "PERS-ZAYEN"
OLD_ZAYEN_ASG = "ASG-ZAYEN-FIN-1"
NEW_ZAYEN_ASG = "ASG-ZAYEN-FC-1"
ROLE_FC = "ROLE-AMG-FINANCIAL-CONTROLLER"
ROLE_OFFICER = "ROLE-AMG-FINANCE-OFFICER"
POS_FC = "POS-AMG-FINANCIAL-CONTROLLER-1"
SCOPE_AMG_FINANCE = "SCOPE-AMG-FINANCE"
ENTITY_AMG = "ENT-AMG"

DEVI = "PERS-DEVI"
DEVI_CLOSER_ASG = "ASG-DEVI-CLOSER-UMA-1"
POS_CLOSER = "POS-BZG-CLOSER-UMA-1"
ROLE_CLOSER = "ROLE-BZG-CLOSER"
SCOPE_UMA = "SCOPE-BZG-UMA"
BRAND_UMA = "BZG-UMA"
ENTITY_BZG = "ENT-BZG"

MATT = "PERS-MATT"
MATT_ASG = "ASG-MATT-OWNER-1"
SCOPE_AMG_DAY = "SCOPE-AMG-ATR-DAY"

ZAYEN_END_REASON = (
    "MYWORK-1 Matt 29 Sep 2026: seat renamed to Atrium Financial Controller. "
    "Prior Finance Officer assignment ended; history preserved. Authority matrix unchanged "
    "(draft/read only — not pay, bank, approve/post, identity/admin, or Owner)."
)

from core.scope import upsert_assignment_scope  # noqa: E402
from core.staff_access import (  # noqa: E402
    ATRIUM_DENIED,
    ATRIUM_GRANTS,
    ATRIUM_HELD_BACK,
    ATRIUM_SUBMIT,
    _ensure_permission,
    _grant,
)


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(TZ8).strftime("%Y%m%d-%H%M%S")


def _backup(db: Path) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"content_library-mywork1-{stamp()}.sqlite"
    dest = premig_backup(db, dest)
    return dest


def _ensure_end_reason(conn: sqlite3.Connection) -> None:
    cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(org_assignments)")}
    if "end_reason" not in cols:
        conn.execute("ALTER TABLE org_assignments ADD COLUMN end_reason TEXT")


def _end_assignment(conn: sqlite3.Connection, aid: str, reason: str, ts: str) -> None:
    row = conn.execute(
        "SELECT status, end_at FROM org_assignments WHERE assignment_id=?", (aid,)
    ).fetchone()
    if not row:
        return
    if str(row[0] or "") == "ENDED" or row[1]:
        conn.execute(
            "UPDATE org_assignments SET end_reason=COALESCE(NULLIF(end_reason,''), ?), updated_at=? WHERE assignment_id=?",
            (reason, ts, aid),
        )
        return
    conn.execute(
        """
        UPDATE org_assignments
        SET status='ENDED', end_at=?, is_primary=0, end_reason=?, updated_at=?
        WHERE assignment_id=? AND status='ACTIVE' AND end_at IS NULL
        """,
        (ts, reason, ts, aid),
    )
    conn.execute(
        """
        UPDATE org_assignment_scopes
        SET status='ENDED', end_at=?, updated_at=?
        WHERE assignment_id=? AND status='ACTIVE' AND end_at IS NULL
        """,
        (ts, ts, aid),
    )


def _attach_scope(conn: sqlite3.Connection, aid: str, scope_id: str, ts: str) -> None:
    row = conn.execute(
        """
        SELECT 1 FROM org_assignment_scopes
        WHERE assignment_id=? AND scope_id=? AND status='ACTIVE' AND end_at IS NULL
        """,
        (aid, scope_id),
    ).fetchone()
    if row:
        return
    start = conn.execute(
        "SELECT start_at FROM org_assignments WHERE assignment_id=?", (aid,)
    ).fetchone()
    start_at = str(start[0]) if start and start[0] else ts
    upsert_assignment_scope(conn, aid, scope_id, start_at, ts)


def _grant_role_perms(conn: sqlite3.Connection, role_id: str, ts: str) -> None:
    for perm_id, code, resource, action, desc in ATRIUM_GRANTS + ATRIUM_HELD_BACK:
        _ensure_permission(conn, perm_id, code, resource, action, desc, ts)
    for _perm_id, code, *_rest in ATRIUM_GRANTS:
        _grant(conn, role_id, code, ts)
    _grant(conn, role_id, ATRIUM_SUBMIT, ts)
    # Explicitly do NOT grant held-back approve/post codes.
    held_ids = [row[0] for row in ATRIUM_HELD_BACK]
    if held_ids:
        marks = ",".join("?" for _ in held_ids)
        conn.execute(
            f"DELETE FROM org_role_permissions WHERE role_id=? AND permission_id IN ({marks})",
            (role_id, *held_ids),
        )


def _rebuild_work_items(conn: sqlite3.Connection) -> None:
    """Empty table rebuild — add statuses + MYWORK columns. History N/A (0 rows)."""
    n = conn.execute("SELECT COUNT(*) FROM core_work_items").fetchone()[0]
    if n != 0:
        # Additive columns only when rows already exist.
        cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(core_work_items)")}
        for col, typ in (
            ("accountable_person_id", "TEXT"),
            ("executor_person_id", "TEXT"),
            ("requested_by_person_id", "TEXT"),
            ("origin", "TEXT"),
            ("import_label", "TEXT"),
            ("instructions", "TEXT"),
            ("evidence_required", "TEXT"),
            ("checklist_json", "TEXT"),
            ("scope_label", "TEXT"),
            ("commissioning_capability_id", "TEXT"),
            ("commissioning_result", "TEXT"),
            ("what_happens_next", "TEXT"),
        ):
            if col not in cols:
                conn.execute(f"ALTER TABLE core_work_items ADD COLUMN {col} {typ}")
        return

    conn.execute("ALTER TABLE core_work_items RENAME TO core_work_items_pre_mywork1")
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
            'REASSIGNED', 'COMPLETED', 'VERIFIED', 'CANCELLED'
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
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          CHECK (
            (created_by_actor_type = 'SYSTEM' AND created_by_person_id IS NULL)
            OR (created_by_actor_type = 'PERSON' AND created_by_person_id IS NOT NULL)
          )
        )
        """
    )
    conn.execute("DROP TABLE core_work_items_pre_mywork1")
    for idx_sql in (
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_entity ON core_work_items(owning_entity_id)",
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_owner ON core_work_items(owner_person_id)",
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_status ON core_work_items(status)",
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_due ON core_work_items(due_at)",
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_parent ON core_work_items(parent_work_item_id)",
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_executor ON core_work_items(executor_person_id)",
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_accountable ON core_work_items(accountable_person_id)",
        "CREATE INDEX IF NOT EXISTS idx_core_work_items_origin ON core_work_items(origin)",
    ):
        conn.execute(idx_sql)


def part_a_assignments(conn: sqlite3.Connection, ts: str) -> dict:
    _ensure_end_reason(conn)

    # Zayen → Financial Controller (end officer assignment; preserve row).
    conn.execute(
        """
        INSERT INTO org_roles (
          role_id, display_name, department_id, role_type, status, created_at, updated_at
        ) VALUES (?, 'Atrium Financial Controller', NULL, 'OPERATING', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO UPDATE SET
          display_name='Atrium Financial Controller', status='ACTIVE', updated_at=excluded.updated_at
        """,
        (ROLE_FC, ts, ts),
    )
    _grant_role_perms(conn, ROLE_FC, ts)
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, location_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES (?, ?, ?, NULL, NULL, NULL, 'Atrium Financial Controller', 'ACTIVE', 1.0, ?, ?)
        ON CONFLICT(position_id) DO UPDATE SET
          role_id=excluded.role_id,
          position_label='Atrium Financial Controller',
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (POS_FC, ROLE_FC, ENTITY_AMG, ts, ts),
    )
    _end_assignment(conn, OLD_ZAYEN_ASG, ZAYEN_END_REASON, ts)
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET
          status='ACTIVE', end_at=NULL, is_primary=1, position_id=excluded.position_id,
          updated_at=excluded.updated_at
        """,
        (NEW_ZAYEN_ASG, ZAYEN, POS_FC, ts, ts, ts),
    )
    _attach_scope(conn, NEW_ZAYEN_ASG, SCOPE_AMG_FINANCE, ts)

    # Devi → Uma Blu Daily Closer (additional seat; FB Ops Lead stays).
    conn.execute(
        """
        UPDATE org_positions
        SET position_label='Closing Operator · Uma Blu',
            status='ACTIVE',
            updated_at=?
        WHERE position_id=?
        """,
        (ts, POS_CLOSER),
    )
    existing_closer = conn.execute(
        """
        SELECT assignment_id FROM org_assignments
        WHERE person_id=? AND position_id=? AND status='ACTIVE' AND end_at IS NULL
        """,
        (DEVI, POS_CLOSER),
    ).fetchone()
    if existing_closer is None:
        conn.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at, status,
              is_primary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 0, ?, ?)
            ON CONFLICT(assignment_id) DO UPDATE SET
              status='ACTIVE', end_at=NULL, is_primary=0, updated_at=excluded.updated_at
            """,
            (DEVI_CLOSER_ASG, DEVI, POS_CLOSER, ts, ts, ts),
        )
        closer_asg = DEVI_CLOSER_ASG
    else:
        closer_asg = str(existing_closer[0])
    _attach_scope(conn, closer_asg, SCOPE_UMA, ts)
    conn.execute(
        """
        INSERT INTO venue_closer_roster (
          roster_id, brand_id, position_id, person_id, assignment_id,
          status, note, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'ACTIVE',
          'Configurable closer list — add more ACTIVE rows later without code change. Cash-variance tolerance UNSET.',
          ?, ?)
        ON CONFLICT(roster_id) DO UPDATE SET
          person_id=excluded.person_id,
          assignment_id=excluded.assignment_id,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        ("VCR-UMA-1", BRAND_UMA, POS_CLOSER, DEVI, closer_asg, ts, ts),
    )
    # Cash-variance tolerance stays UNSET — do not insert venue_close_variance_policies.

    # Matt OVERWATCH — attach AMG scopes; Owner seat already covers BZG/GGV.
    for sid in (SCOPE_AMG_FINANCE, SCOPE_AMG_DAY):
        exists = conn.execute(
            "SELECT 1 FROM org_scopes WHERE scope_id=?", (sid,)
        ).fetchone()
        if exists:
            _attach_scope(conn, MATT_ASG, sid, ts)

    # Work-loop grants so seated staff can execute commissioning tasks on their items.
    for role_id, codes in (
        (ROLE_FC, ("work.read", "work.update", "work.complete", "evidence.record.submit", "evidence.record.read")),
        (ROLE_CLOSER, ("work.read", "work.update", "work.complete", "evidence.record.submit", "evidence.record.read")),
        ("ROLE-BZG-FB-OPS-LEAD", ("work.read", "work.update", "work.complete", "evidence.record.submit")),
        ("ROLE-GGV-CREATIVE-DIRECTOR", ("work.complete", "evidence.record.submit")),
        ("ROLE-CONTENT-CREATOR", ("work.complete", "evidence.record.submit")),
        ("ROLE-GGV-FINANCE-OPERATOR", ("work.update", "work.complete", "evidence.record.submit", "evidence.record.read")),
        ("ROLE-CONTENT-MGMT", ("work.read", "work.update", "work.complete", "evidence.record.submit")),
    ):
        for code in codes:
            try:
                _grant(conn, role_id, code, ts)
            except RuntimeError:
                pass

    return {
        "zayen_ended": OLD_ZAYEN_ASG,
        "zayen_new": NEW_ZAYEN_ASG,
        "devi_closer": closer_asg,
        "matt_overwatch_scopes": [SCOPE_AMG_FINANCE, SCOPE_AMG_DAY],
        "cash_variance_tolerance": "UNSET",
        "atrium_denied_unchanged": list(ATRIUM_DENIED),
    }


def apply_sql(conn: sqlite3.Connection) -> None:
    conn.executescript(SQL.read_text(encoding="utf-8"))


def run(db_path: Path | None = None) -> dict:
    path = Path(db_path) if db_path else DB
    if "beta-os" not in str(path.resolve()):
        raise RuntimeError(f"refuses non-beta DB: {path}")
    bak = _backup(path)
    ts = now_iso()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        # Rebuild work_items BEFORE creating child tables — SQLite retargets FKs on RENAME.
        _rebuild_work_items(conn)
        apply_sql(conn)
        assign_info = part_a_assignments(conn, ts)

        # Seed commissioning + legacy via universal_my_work (same process).
        from core import universal_my_work as umw

        commission = umw.issue_commissioning_tasks(conn=conn, commit=False)
        legacy = umw.import_legacy_migration(
            proposal_path=LEGACY_PROPOSAL,
            conn=conn,
            commit=False,
        )
        cut = umw.write_clickup_cut_line(CUT_LINE)
        umw.mark_derived_views_stale(conn=conn, commit=False)
        conn.commit()

        receipt = {
            "migration_id": MIGRATION_ID,
            "ran_at": ts,
            "backup": str(bak),
            "assignments": assign_info,
            "commissioning": commission,
            "legacy_import": legacy,
            "clickup_cut_line": cut,
            "staff_ready": False,
            "human_commissioned": False,
        }
        IMPORT_RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        IMPORT_RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return receipt
    finally:
        conn.close()


if __name__ == "__main__":
    out = run()
    print(json.dumps({k: out[k] for k in ("migration_id", "assignments", "commissioning", "legacy_import")}, indent=2))
    print("RESULT: PASS")
