#!/usr/bin/env python3
"""029 Devi BZG F&B Operations Lead — Beta catalog only.

Owner decision DEC-DEVI-BZG-FB-OPS-LEAD-2026-09-19.
Creates venue.receive, ROLE-BZG-FB-OPS-LEAD, SCOPE-BZG-FB, and
ASG-DEVI-FB-OPS-1. Ends the Uma-only HFB assignment so verify is not
inherited. Does not resurrect ENDED SCOPE-BZG-ENTITY. Does not grant
payment approve, close verify, progress, or Owner. No Alchemist writes.
No Production.
"""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core.scope import upsert_assignment_scope  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"

# Owner P0 5 Oct 2026: retention/free-space guard (docs/BACKUP-RETENTION.md)
import sys as _bp_sys  # noqa: E402
if str(ROOT / "scripts") not in _bp_sys.path:
    _bp_sys.path.insert(0, str(ROOT / "scripts"))
from core.backup_policy import premig_backup  # noqa: E402
MIGRATION_ID = "029_devi_fb_ops_lead"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")

DEVI = "PERS-DEVI"
ENTITY = "ENT-BZG"
BRAND = "BZG-UMA"
DEPT = "DEPT-BZG-FB"
ROLE = "ROLE-BZG-FB-OPS-LEAD"
ROLE_DISPLAY = "BZG F&B OPERATIONS LEAD"
POS = "POS-BZG-FB-OPS-1"
ASG = "ASG-DEVI-FB-OPS-1"
ASG_HFB = "ASG-DEVI-HFB-UMA-1"
SCOPE_FB = "SCOPE-BZG-FB"
SCOPE_UMA = "SCOPE-BZG-UMA"
SCOPE_ENTITY = "SCOPE-BZG-ENTITY"
START = "2026-09-19T00:00:00+08:00"
PERM_RECEIVE = "PERM-VENUE-RECEIVE"

GRANT_CODES = (
    "work.read",
    "work.create",
    "work.update",
    "work.complete",
    "work.assign",
    "evidence.record.read",
    "evidence.record.submit",
    "venue.close.read",
    "venue.close.submit",
    "venue.close.resolve_exception",
    "venue.receive",
)
DENY_CODES = (
    "venue.close.verify",
    "bzg.pr.payment_approve",
    "progress.read",
    "approval.decide",
    "test.spend.approve",
    "work.verify",
)


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(TZ8).strftime("%Y%m%d-%H%M%S")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _refuse_path(db_path: Path) -> str | None:
    s = str(db_path.resolve())
    for frag in FORBIDDEN:
        if frag in s:
            return frag
    if "beta-os" not in s:
        return "not-beta-os"
    return None


def main() -> int:
    db_path = Path(DB)
    bad = _refuse_path(db_path)
    if bad:
        print(f"REFUSE: {bad} in {db_path}", file=sys.stderr)
        return 2

    ts = now_iso()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        planner_before = (
            conn.execute("SELECT COUNT(*) FROM content_planner").fetchone()[0]
            if "content_planner" in tabs
            else None
        )
        auth_before = (
            conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
            if "org_authority_limits" in tabs
            else 0
        )
        ent_before = conn.execute(
            """
            SELECT status, end_at FROM org_assignment_scopes
            WHERE assignment_id=? AND scope_id=?
            """,
            (ASG_HFB, SCOPE_ENTITY),
        ).fetchone()

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        dest = BACKUP_DIR / f"pre-devi-fb-ops-lead-{stamp()}.sqlite"
        dest = premig_backup(db_path, dest)
        digest = _sha256(dest)
        print(f"BACKUP={dest}")
        print(f"SHA256={digest}")

        conn.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description, status, created_at, updated_at
            ) VALUES (?, 'venue.receive', 'venue', 'receive',
                      'Receive goods against a BZG venue order in scope', 'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET
              code='venue.receive',
              resource='venue',
              action='receive',
              description=excluded.description,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (PERM_RECEIVE, ts, ts),
        )
        # If an older row used this code under another id, keep that row ACTIVE.
        conn.execute(
            """
            UPDATE org_permissions
            SET status='ACTIVE', updated_at=?
            WHERE code='venue.receive' AND status!='ACTIVE'
            """,
            (ts,),
        )

        conn.execute(
            """
            INSERT INTO org_roles (
              role_id, display_name, department_id, role_type, status, created_at, updated_at
            ) VALUES (?, ?, ?, 'OPERATING', 'SPECIFIED', ?, ?)
            ON CONFLICT(role_id) DO UPDATE SET
              display_name=excluded.display_name,
              department_id=excluded.department_id,
              role_type='OPERATING',
              status='SPECIFIED',
              updated_at=excluded.updated_at
            """,
            (ROLE, ROLE_DISPLAY, DEPT, ts, ts),
        )

        for code in GRANT_CODES:
            row = conn.execute(
                "SELECT permission_id, status FROM org_permissions WHERE code=?",
                (code,),
            ).fetchone()
            if not row or row["status"] != "ACTIVE":
                print(f"REFUSE: missing ACTIVE permission {code}", file=sys.stderr)
                conn.rollback()
                return 2
            conn.execute(
                """
                INSERT INTO org_role_permissions (
                  role_id, permission_id, effect, created_at, updated_at
                ) VALUES (?, ?, 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET
                  effect='ALLOW', updated_at=excluded.updated_at
                """,
                (ROLE, row["permission_id"], ts, ts),
            )

        denied = conn.execute(
            f"""
            SELECT p.code FROM org_role_permissions rp
            JOIN org_permissions p ON p.permission_id=rp.permission_id
            WHERE rp.role_id=? AND rp.effect='ALLOW'
              AND p.code IN ({",".join("?" for _ in DENY_CODES)})
            """,
            (ROLE, *DENY_CODES),
        ).fetchall()
        if denied:
            print(
                "REFUSE: denied codes granted: " + ",".join(r["code"] for r in denied),
                file=sys.stderr,
            )
            conn.rollback()
            return 2

        conn.execute(
            """
            INSERT INTO org_scopes (
              scope_id, scope_type, display_name, status, created_at, updated_at
            ) VALUES (?, 'brand', 'BZG F&B venues (Uma now)', 'ACTIVE', ?, ?)
            ON CONFLICT(scope_id) DO UPDATE SET
              display_name=excluded.display_name,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (SCOPE_FB, ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
            VALUES (?, 'brand', ?, ?)
            ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
            """,
            (SCOPE_FB, BRAND, ts),
        )

        conn.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, location_id, brand_id, department_id,
              position_label, status, fte, created_at, updated_at
            ) VALUES (?, ?, ?, NULL, ?, ?, 'BZG F&B Operations Lead', 'ACTIVE', 1.0, ?, ?)
            ON CONFLICT(position_id) DO UPDATE SET
              role_id=excluded.role_id,
              entity_id=excluded.entity_id,
              brand_id=excluded.brand_id,
              department_id=excluded.department_id,
              position_label=excluded.position_label,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (POS, ROLE, ENTITY, BRAND, DEPT, ts, ts),
        )

        # End Uma-only HFB so close.verify is not inherited. Do not touch its scopes.
        conn.execute(
            """
            UPDATE org_assignments
            SET status='ENDED', end_at=?, is_primary=0, updated_at=?
            WHERE assignment_id=? AND status='ACTIVE' AND end_at IS NULL
            """,
            (ts, ts, ASG_HFB),
        )

        conn.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at, status,
              is_primary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
            ON CONFLICT(assignment_id) DO UPDATE SET
              person_id=excluded.person_id,
              position_id=excluded.position_id,
              status='ACTIVE',
              end_at=NULL,
              is_primary=1,
              updated_at=excluded.updated_at
            WHERE org_assignments.status!='ENDED' OR org_assignments.assignment_id=?
            """,
            (ASG, DEVI, POS, START, ts, ts, ASG),
        )
        upsert_assignment_scope(conn, ASG, SCOPE_FB, START, ts, revive=False)
        upsert_assignment_scope(conn, ASG, SCOPE_UMA, START, ts, revive=False)

        ent_after = conn.execute(
            """
            SELECT status, end_at FROM org_assignment_scopes
            WHERE assignment_id=? AND scope_id=?
            """,
            (ASG_HFB, SCOPE_ENTITY),
        ).fetchone()
        if ent_before is None or ent_after is None:
            print("REFUSE: SCOPE-BZG-ENTITY row missing", file=sys.stderr)
            conn.rollback()
            return 2
        if (
            ent_after["status"] != ent_before["status"]
            or ent_after["end_at"] != ent_before["end_at"]
            or ent_after["status"] != "ENDED"
            or not ent_after["end_at"]
        ):
            print(
                f"REFUSE: ENTITY scope changed {tuple(ent_before)} -> {tuple(ent_after)}",
                file=sys.stderr,
            )
            conn.rollback()
            return 2

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (
                MIGRATION_ID,
                ts,
                "ROLE-BZG-FB-OPS-LEAD; venue.receive; ASG-DEVI-FB-OPS-1; HFB assignment ended; ENTITY not revived",
            ),
        )

        if planner_before is not None:
            planner_after = conn.execute("SELECT COUNT(*) FROM content_planner").fetchone()[0]
            if planner_after != planner_before:
                print("REFUSE: content_planner mutated", file=sys.stderr)
                conn.rollback()
                return 2
        if "org_authority_limits" in tabs:
            auth_after = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
            if auth_after != auth_before:
                print("REFUSE: authority limits changed", file=sys.stderr)
                conn.rollback()
                return 2

        conn.commit()
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        print(f"role={ROLE}")
        print(f"assignment={ASG}")
        print(f"entity={ent_after['status']} {ent_after['end_at']}")
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
