#!/usr/bin/env python3
"""021 Uma Blu Daily Close — idempotent Beta-only migration.

Creates venue_daily_closes + empty venue_close_variance_policies.
Seeds PERS-DEVI (HR-authorised email), ROLE-BZG-CLOSER (no person),
ROLE-BZG-HFB position/assignment + SCOPE-BZG-UMA, close.* permissions.
Live variance thresholds = 0. Live monetary authority unchanged.
No Habitat / content_planner mutations. No ESB writes.
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
DB = ROOT / "catalog" / "content_library.sqlite"
SQL = Path(__file__).resolve().parent / "021_uma_blu_daily_close.sql"
MIGRATION_ID = "021_uma_blu_daily_close"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))
BACKUP_DIR = ROOT / "catalog" / "backups"

# Owner P0 5 Oct 2026: retention/free-space guard (docs/BACKUP-RETENTION.md)
import sys as _bp_sys  # noqa: E402
if str(ROOT / "scripts") not in _bp_sys.path:
    _bp_sys.path.insert(0, str(ROOT / "scripts"))
from core.backup_policy import premig_backup  # noqa: E402

# HR-authorised — Notion Employees / HR master. Do not invent another email.
DEVI_PERSON = "PERS-DEVI"
DEVI_AUTH = "AUTH-DEVI-EMAIL"
DEVI_EMAIL = "deviputu236@gmail.com"
DEVI_DISPLAY = "Ni Putu Devi Parwati"
DEVI_LEGAL = "Ni Putu Devi Parwati"

ENTITY = "ENT-BZG"
BRAND = "BZG-UMA"
DEPT = "DEPT-BZG-FB"
ROLE_HFB = "ROLE-BZG-HFB"
ROLE_CLOSER = "ROLE-BZG-CLOSER"
ROLE_MATT = "ROLE-MATT"

SCOPE_UMA = "SCOPE-BZG-UMA"
SCOPE_BZG = "SCOPE-BZG-ENTITY"

POS_HFB = "POS-BZG-HFB-UMA-1"
POS_CLOSER = "POS-BZG-CLOSER-UMA-1"
ASG_DEVI = "ASG-DEVI-HFB-UMA-1"
ASG_MATT = "ASG-MATT-OWNER-1"

START = "2026-09-17T00:00:00+08:00"

PERMS = (
    (
        "PERM-VENUE-CLOSE-READ",
        "venue.close.read",
        "venue.close",
        "read",
        "Read Uma Blu / venue daily close records in scope",
    ),
    (
        "PERM-VENUE-CLOSE-SUBMIT",
        "venue.close.submit",
        "venue.close",
        "submit",
        "Open close, capture ESB snapshot, submit declared cash evidence",
    ),
    (
        "PERM-VENUE-CLOSE-RESOLVE",
        "venue.close.resolve_exception",
        "venue.close",
        "resolve_exception",
        "Resolve variance exception with evidence (Head of F&B)",
    ),
    (
        "PERM-VENUE-CLOSE-VERIFY",
        "venue.close.verify",
        "venue.close",
        "verify",
        "Verify closed day / exception (SoD: not sole self-verify on own exception)",
    ),
)

# Role grants (no if-Devi — assignment + role only)
HFB_GRANTS = (
    "PERM-VENUE-CLOSE-READ",
    "PERM-VENUE-CLOSE-RESOLVE",
    "PERM-VENUE-CLOSE-VERIFY",
    "PERM-WORK-CREATE",
    "PERM-WORK-READ",
    "PERM-WORK-UPDATE",
    "PERM-EVIDENCE-RECORD-SUBMIT",
    "PERM-EVIDENCE-RECORD-READ",
)
CLOSER_GRANTS = (
    "PERM-VENUE-CLOSE-READ",
    "PERM-VENUE-CLOSE-SUBMIT",
    "PERM-EVIDENCE-RECORD-SUBMIT",
    "PERM-EVIDENCE-RECORD-READ",
)
MATT_GRANTS = (
    "PERM-VENUE-CLOSE-READ",
    "PERM-VENUE-CLOSE-SUBMIT",
    "PERM-VENUE-CLOSE-RESOLVE",
    "PERM-VENUE-CLOSE-VERIFY",
)

EVIDENCE_TYPE = "cash_count"


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


def _backup(db_path: Path) -> tuple[Path, str]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"pre-uma-blu-daily-close-{stamp()}.sqlite"
    dest = premig_backup(db_path, dest)
    digest = _sha256(dest)
    sha_path = (
        ROOT
        / "state"
        / f"uma-blu-daily-close-backup-{dest.stem.replace('pre-uma-blu-daily-close-', '')}.sha256"
    )
    sha_path.parent.mkdir(parents=True, exist_ok=True)
    sha_path.write_text(f"{digest}  {dest.relative_to(ROOT)}\n", encoding="utf-8")
    print(f"BACKUP={dest}")
    print(f"SHA256={digest}")
    return dest, digest


def upsert_perm(conn, perm_id, code, resource, action, desc, ts):
    conn.execute(
        """
        INSERT INTO org_permissions (
          permission_id, code, resource, action, description, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
        ON CONFLICT(permission_id) DO UPDATE SET
          code=excluded.code,
          resource=excluded.resource,
          action=excluded.action,
          description=excluded.description,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (perm_id, code, resource, action, desc, ts, ts),
    )


def grant(conn, role_id, perm_id, ts):
    conn.execute(
        """
        INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES (?, ?, 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET
          effect='ALLOW', updated_at=excluded.updated_at
        """,
        (role_id, perm_id, ts, ts),
    )


def upsert_scope(conn, scope_id, scope_type, display_name, ts):
    conn.execute(
        """
        INSERT INTO org_scopes (
          scope_id, scope_type, display_name, status, created_at, updated_at
        ) VALUES (?, ?, ?, 'ACTIVE', ?, ?)
        ON CONFLICT(scope_id) DO UPDATE SET
          scope_type=excluded.scope_type,
          display_name=excluded.display_name,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (scope_id, scope_type, display_name, ts, ts),
    )


def upsert_target(conn, scope_id, target_type, target_id, ts):
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
        """,
        (scope_id, target_type, target_id, ts),
    )


def upsert_asg_scope(conn, assignment_id, scope_id, ts, *, revive: bool = False):
    """Seed an assignment-scope. Default does not revive ENDED rows.

    revive=True is Owner-only. main() and other migrate/seed/test callers
    must not pass it.
    """
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(
        conn,
        assignment_id,
        scope_id,
        START,
        ts,
        end_at=None,
        status="ACTIVE",
        revive=revive,
    )


def main() -> int:
    db_path = DB.resolve()
    s = str(db_path)
    for frag in FORBIDDEN:
        if frag in s:
            print(f"REFUSE: {frag} in {s}", file=sys.stderr)
            return 2
    if "beta-os" not in s:
        print(f"REFUSE: not beta-os: {s}", file=sys.stderr)
        return 2

    ts = now_iso()
    planner_before = None
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "content_planner" in tabs:
            planner_before = conn.execute("SELECT COUNT(*) FROM content_planner").fetchone()[0]

        auth_before = (
            conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
            if "org_authority_limits" in tabs
            else 0
        )

        _backup(db_path)

        conn.executescript(SQL.read_text(encoding="utf-8"))
        print("DDL applied")

        # --- permissions ---
        for perm_id, code, resource, action, desc in PERMS:
            upsert_perm(conn, perm_id, code, resource, action, desc, ts)

        # Ensure ROLE-BZG-CLOSER exists (no named person → WAITING)
        conn.execute(
            """
            INSERT INTO org_roles (
              role_id, display_name, department_id, role_type, status, created_at, updated_at
            ) VALUES (?, 'Venue Closing Operator', ?, 'OPERATING', 'SPECIFIED', ?, ?)
            ON CONFLICT(role_id) DO UPDATE SET
              display_name=excluded.display_name,
              department_id=excluded.department_id,
              status='SPECIFIED',
              updated_at=excluded.updated_at
            """,
            (ROLE_CLOSER, DEPT, ts, ts),
        )
        # ROLE-BZG-HFB already seeded by 007 — ensure ACTIVE/SPECIFIED
        conn.execute(
            """
            UPDATE org_roles SET status='SPECIFIED', updated_at=?
            WHERE role_id=?
            """,
            (ts, ROLE_HFB),
        )

        for pid in HFB_GRANTS:
            # only grant if permission exists
            row = conn.execute(
                "SELECT permission_id FROM org_permissions WHERE permission_id=?",
                (pid,),
            ).fetchone()
            if row:
                grant(conn, ROLE_HFB, pid, ts)
        for pid in CLOSER_GRANTS:
            row = conn.execute(
                "SELECT permission_id FROM org_permissions WHERE permission_id=?",
                (pid,),
            ).fetchone()
            if row:
                grant(conn, ROLE_CLOSER, pid, ts)
        for pid in MATT_GRANTS:
            grant(conn, ROLE_MATT, pid, ts)

        # --- scopes ---
        upsert_scope(conn, SCOPE_UMA, "brand", "Uma Blu (BZG-UMA)", ts)
        upsert_target(conn, SCOPE_UMA, "brand", BRAND, ts)
        upsert_scope(conn, SCOPE_BZG, "entity", "BZG entity (all)", ts)
        upsert_target(conn, SCOPE_BZG, "entity", ENTITY, ts)

        # --- Devi person + auth (HR-authorised email only) ---
        ident = DEVI_EMAIL.strip().lower()
        conn.execute(
            """
            INSERT INTO org_persons (
              person_id, display_name, legal_name, status, created_at, updated_at
            ) VALUES (?, ?, ?, 'ACTIVE', ?, ?)
            ON CONFLICT(person_id) DO UPDATE SET
              display_name=excluded.display_name,
              legal_name=COALESCE(excluded.legal_name, org_persons.legal_name),
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (DEVI_PERSON, DEVI_DISPLAY, DEVI_LEGAL, ts, ts),
        )
        existing = conn.execute(
            """
            SELECT person_id FROM org_auth_identities
            WHERE provider='email' AND lower(identifier)=?
            """,
            (ident,),
        ).fetchone()
        if existing and existing["person_id"] != DEVI_PERSON:
            print(
                f"REFUSE: email {ident} already mapped to {existing['person_id']}",
                file=sys.stderr,
            )
            return 2
        row = conn.execute(
            "SELECT auth_identity_id, person_id FROM org_auth_identities "
            "WHERE provider='email' AND lower(identifier)=?",
            (ident,),
        ).fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO org_auth_identities (
                  auth_identity_id, person_id, provider, identifier, status,
                  is_primary, created_at, updated_at, last_verified_at
                ) VALUES (?, ?, 'email', ?, 'ACTIVE', 1, ?, ?, NULL)
                """,
                (DEVI_AUTH, DEVI_PERSON, ident, ts, ts),
            )
        else:
            conn.execute(
                """
                UPDATE org_auth_identities
                SET status='ACTIVE', is_primary=1, updated_at=?,
                    auth_identity_id=?, person_id=?
                WHERE provider='email' AND lower(identifier)=?
                """,
                (ts, DEVI_AUTH, DEVI_PERSON, ident),
            )

        # --- positions ---
        conn.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, location_id, brand_id, department_id,
              position_label, status, fte, created_at, updated_at
            ) VALUES (?, ?, ?, NULL, ?, ?, 'Head of F&B · Uma Blu', 'ACTIVE', 1.0, ?, ?)
            ON CONFLICT(position_id) DO UPDATE SET
              role_id=excluded.role_id,
              entity_id=excluded.entity_id,
              brand_id=excluded.brand_id,
              department_id=excluded.department_id,
              position_label=excluded.position_label,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (POS_HFB, ROLE_HFB, ENTITY, BRAND, DEPT, ts, ts),
        )
        # Closer seat exists for commissioning — NO assignment (WAITING)
        conn.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, location_id, brand_id, department_id,
              position_label, status, fte, created_at, updated_at
            ) VALUES (?, ?, ?, NULL, ?, ?,
                      'Closing Operator · Uma Blu (WAITING roster)', 'ACTIVE', 1.0, ?, ?)
            ON CONFLICT(position_id) DO UPDATE SET
              role_id=excluded.role_id,
              entity_id=excluded.entity_id,
              brand_id=excluded.brand_id,
              department_id=excluded.department_id,
              position_label=excluded.position_label,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (POS_CLOSER, ROLE_CLOSER, ENTITY, BRAND, DEPT, ts, ts),
        )

        # Devi ACTIVE assignment to HFB Uma
        conn.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at, status,
              is_primary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
            ON CONFLICT(assignment_id) DO UPDATE SET
              person_id=excluded.person_id,
              position_id=excluded.position_id,
              start_at=excluded.start_at,
              end_at=NULL,
              status='ACTIVE',
              is_primary=1,
              updated_at=excluded.updated_at
            WHERE org_assignments.status!='ENDED' AND org_assignments.end_at IS NULL
            """,
            (ASG_DEVI, DEVI_PERSON, POS_HFB, START, ts, ts),
        )
        upsert_asg_scope(conn, ASG_DEVI, SCOPE_UMA, ts)
        upsert_asg_scope(conn, ASG_DEVI, SCOPE_BZG, ts)

        # Matt owner: BZG entity scope so exception verify path works (oversight)
        upsert_asg_scope(conn, ASG_MATT, SCOPE_BZG, ts)
        upsert_asg_scope(conn, ASG_MATT, SCOPE_UMA, ts)

        # Evidence type for declared till cash (DECLARED ≠ VERIFIED)
        if "core_evidence_types" in tabs or True:
            conn.execute(
                """
                INSERT INTO core_evidence_types (
                  evidence_type, description, status, created_at, updated_at
                ) VALUES (?,
                          'Operator-declared till cash at close — DECLARED not VERIFIED',
                          'ACTIVE', ?, ?)
                ON CONFLICT(evidence_type) DO UPDATE SET
                  description=excluded.description,
                  status='ACTIVE',
                  updated_at=excluded.updated_at
                """,
                (EVIDENCE_TYPE, ts, ts),
            )

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
                "Uma Blu daily close; Devi HFB seed; variance policies live=0",
            ),
        )
        conn.commit()

        # --- honesty checks ---
        n_pol = conn.execute("SELECT COUNT(*) FROM venue_close_variance_policies").fetchone()[0]
        n_auth = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
        n_close = conn.execute("SELECT COUNT(*) FROM venue_daily_closes").fetchone()[0]
        closer_asg = conn.execute(
            """
            SELECT COUNT(*) FROM org_assignments a
            JOIN org_positions p ON p.position_id=a.position_id
            WHERE p.role_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
            """,
            (ROLE_CLOSER,),
        ).fetchone()[0]
        planner_after = (
            conn.execute("SELECT COUNT(*) FROM content_planner").fetchone()[0]
            if "content_planner" in {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            else None
        )

        print(f"venue_close_variance_policies={n_pol}")
        print(f"org_authority_limits={n_auth} (before={auth_before})")
        print(f"venue_daily_closes={n_close}")
        print(f"ROLE-BZG-CLOSER active assignments={closer_asg}")
        print(
            "commissioning=WAITING FOR VERIFIED CLOSING OPERATOR"
            if closer_asg == 0
            else "commissioning=CLOSER_ASSIGNED"
        )
        if planner_before is not None:
            print(f"content_planner before={planner_before} after={planner_after}")
            if planner_after != planner_before:
                print("REFUSE: content_planner mutated", file=sys.stderr)
                return 2
        if n_pol != 0:
            print("REFUSE: live variance policies must be 0", file=sys.stderr)
            return 2
        if n_auth != auth_before:
            print("REFUSE: monetary authority limits changed", file=sys.stderr)
            return 2

        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
