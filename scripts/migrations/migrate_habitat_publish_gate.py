#!/usr/bin/env python3
"""020 Habitat Publish Gate — idempotent Beta-only migration.

Org: brand habitat under ENT-GGV; ROLE-GGV-CREATIVE-DIRECTOR;
perms content.habitat.approve / content.habitat.publish.request;
evidence type content_draft; ONE governance policy + ONE evidence requirement
for HABITAT.CONTENT.PUBLISH (ENT-GGV / SCOPE-GGV-CONTENT).

content_planner columns + content_versions append table.
LIVE monetary authority stays 0. No SoD / Exception seed.
Backs up Beta DB before apply and prints SHA-256.
"""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "catalog" / "content_library.sqlite"
SQL = Path(__file__).resolve().parent / "020_habitat_publish_gate.sql"
MIGRATION_ID = "020_habitat_publish_gate"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))
BACKUP_DIR = ROOT / "catalog" / "backups"

# Owner P0 5 Oct 2026: retention/free-space guard (docs/BACKUP-RETENTION.md)
import sys as _bp_sys  # noqa: E402
if str(ROOT / "scripts") not in _bp_sys.path:
    _bp_sys.path.insert(0, str(ROOT / "scripts"))
from core.backup_policy import premig_backup  # noqa: E402

ENTITY = "ENT-GGV"
SCOPE = "SCOPE-GGV-CONTENT"
BRAND_ID = "habitat"
ACTION = "HABITAT.CONTENT.PUBLISH"
POLICY_ID = "GPO-HABITAT-CONTENT-PUBLISH"
EVR_ID = "EVR-HABITAT-CONTENT-PUBLISH"
ROLE_CD = "ROLE-GGV-CREATIVE-DIRECTOR"

PERM_APPROVE = (
    "PERM-CONTENT-HABITAT-APPROVE",
    "content.habitat.approve",
    "content.habitat",
    "approve",
    "Approve Habitat content for publish gate",
)
PERM_PUBLISH_REQ = (
    "PERM-CONTENT-HABITAT-PUBLISH-REQUEST",
    "content.habitat.publish.request",
    "content.habitat",
    "publish.request",
    "Request Habitat content publish approval",
)

APPROVE_ROLES = (
    "ROLE-MATT",
    ROLE_CD,
    "ROLE-CONTENT-MGMT",
    "ROLE-GGV-EDIT",
    "ROLE-CONTENT-CREW",
)
# Publish request + evidence submit + work.create + approval.request for schedulers
PUBLISH_REQ_ROLES = (
    "ROLE-MATT",
    "ROLE-CONTENT-MGMT",
    "ROLE-CONTENT-CREW",
)
# Core decide required for Habitat approve path (in addition to content.habitat.approve)
DECIDE_ROLES = APPROVE_ROLES
# Supporting Core perms so Habitat path is usable by granted roles
SUPPORT_PERMS_FOR_APPROVE = ("PERM-APPROVAL-DECIDE",)
SUPPORT_PERMS_FOR_PUBLISH = (
    "PERM-APPROVAL-REQUEST",
    "PERM-EVIDENCE-RECORD-SUBMIT",
    "PERM-WORK-CREATE",
)

PLANNER_COLS = (
    ("content_version_hash", "TEXT"),
    ("work_item_id", "TEXT"),
    ("core_approval_request_id", "TEXT"),
    ("approved_version_hash", "TEXT"),
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


def _backup(db_path: Path) -> tuple[Path, str]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"pre-habitat-publish-gate-{stamp()}.sqlite"
    dest = premig_backup(db_path, dest)
    digest = _sha256(dest)
    sha_path = (
        ROOT
        / "state"
        / f"habitat-publish-gate-backup-{dest.stem.replace('pre-habitat-publish-gate-', '')}.sha256"
    )
    sha_path.parent.mkdir(parents=True, exist_ok=True)
    sha_path.write_text(f"{digest}  {dest.relative_to(ROOT)}\n", encoding="utf-8")
    print(f"BACKUP={dest}")
    print(f"SHA256={digest}")
    return dest, digest


def col_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return col in {r[1] for r in rows}


def add_col(conn: sqlite3.Connection, table: str, col: str, decl: str) -> None:
    if not col_exists(conn, table, col):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        print(f"  + {table}.{col}")
    else:
        print(f"  = {table}.{col} exists")


def upsert_perm(conn: sqlite3.Connection, perm: tuple, ts: str) -> None:
    perm_id, code, resource, action, desc = perm
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
          status=excluded.status,
          updated_at=excluded.updated_at
        """,
        (perm_id, code, resource, action, desc, ts, ts),
    )


def grant(conn: sqlite3.Connection, role_id: str, permission_id: str, ts: str) -> None:
    # Role may not exist yet for CREATIVE-DIRECTOR — caller seeds role first
    exists = conn.execute(
        "SELECT 1 FROM org_roles WHERE role_id=?", (role_id,)
    ).fetchone()
    if not exists:
        return
    conn.execute(
        """
        INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES (?, ?, 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET
          effect=excluded.effect,
          updated_at=excluded.updated_at
        """,
        (role_id, permission_id, ts, ts),
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
    is_live = db_path == (ROOT / "catalog" / "content_library.sqlite").resolve()
    if is_live:
        probe = sqlite3.connect(str(db_path))
        try:
            tabs = {r[0] for r in probe.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            need_backup = True
            mig_done = (
                probe.execute(
                    "SELECT 1 FROM schema_migrations WHERE id=? LIMIT 1",
                    (MIGRATION_ID,),
                ).fetchone()
                if "schema_migrations" in tabs
                else None
            )
            planner_ok = False
            if "content_planner" in tabs:
                cols = {r[1] for r in probe.execute("PRAGMA table_info(content_planner)")}
                planner_ok = all(c in cols for c, _ in PLANNER_COLS)
            if (
                "content_versions" in tabs
                and planner_ok
                and mig_done
            ):
                need_backup = False
            if need_backup:
                _backup(db_path)
        finally:
            probe.close()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        n_auth = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
        if n_auth != 0:
            print(
                f"REFUSE: live org_authority_limits must stay 0, got {n_auth}",
                file=sys.stderr,
            )
            return 2

        n_sod = 0
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "core_sod_constraints" in tabs:
            n_sod = conn.execute("SELECT COUNT(*) FROM core_sod_constraints").fetchone()[0]
        if n_sod != 0:
            print(
                f"REFUSE: live SoD constraints must stay 0, got {n_sod}",
                file=sys.stderr,
            )
            return 2

        conn.executescript(SQL.read_text(encoding="utf-8"))
        print("DDL applied (content_versions)")

        if "content_planner" in tabs:
            for col, decl in PLANNER_COLS:
                add_col(conn, "content_planner", col, decl)

        # --- Brand habitat under ENT-GGV ---
        if "org_brands" in tabs:
            ent = conn.execute(
                "SELECT entity_id FROM org_entities WHERE entity_id=?", (ENTITY,)
            ).fetchone()
            if not ent:
                print(f"REFUSE: missing entity {ENTITY}", file=sys.stderr)
                return 2
            conn.execute(
                """
                INSERT INTO org_brands (
                  brand_id, entity_id, display_name, brand_type, status, created_at, updated_at
                ) VALUES (?, ?, 'Habitat', 'CLIENT_BRAND', 'LIVE', ?, ?)
                ON CONFLICT(brand_id) DO UPDATE SET
                  entity_id=excluded.entity_id,
                  display_name=excluded.display_name,
                  brand_type=excluded.brand_type,
                  status=excluded.status,
                  updated_at=excluded.updated_at
                """,
                (BRAND_ID, ENTITY, ts, ts),
            )
            print(f"brand {BRAND_ID} under {ENTITY}")
            # Align Content Machine brands.org_brand_id when column exists
            if col_exists(conn, "brands", "org_brand_id"):
                conn.execute(
                    "UPDATE brands SET org_brand_id=? WHERE id=?",
                    (BRAND_ID, BRAND_ID),
                )
            if col_exists(conn, "brand_external_ids", "org_brand_id"):
                conn.execute(
                    "UPDATE brand_external_ids SET org_brand_id=? WHERE brand_key=?",
                    (BRAND_ID, BRAND_ID),
                )

        # --- Creative Director role (empty seat OK) ---
        if "org_roles" in tabs:
            conn.execute(
                """
                INSERT INTO org_roles (
                  role_id, display_name, department_id, role_type, status, created_at, updated_at
                ) VALUES (?, 'Creative Director', 'DEPT-GGV-CONTENT', 'OPERATING', 'SPECIFIED', ?, ?)
                ON CONFLICT(role_id) DO UPDATE SET
                  display_name=excluded.display_name,
                  department_id=excluded.department_id,
                  role_type=excluded.role_type,
                  status=excluded.status,
                  updated_at=excluded.updated_at
                """,
                (ROLE_CD, ts, ts),
            )
            print(f"role {ROLE_CD}")

        # --- Permissions ---
        if "org_permissions" in tabs:
            upsert_perm(conn, PERM_APPROVE, ts)
            upsert_perm(conn, PERM_PUBLISH_REQ, ts)
            for role in APPROVE_ROLES:
                grant(conn, role, PERM_APPROVE[0], ts)
                for pid in SUPPORT_PERMS_FOR_APPROVE:
                    if conn.execute(
                        "SELECT 1 FROM org_permissions WHERE permission_id=?", (pid,)
                    ).fetchone():
                        grant(conn, role, pid, ts)
            for role in PUBLISH_REQ_ROLES:
                grant(conn, role, PERM_PUBLISH_REQ[0], ts)
                for pid in SUPPORT_PERMS_FOR_PUBLISH:
                    if conn.execute(
                        "SELECT 1 FROM org_permissions WHERE permission_id=?", (pid,)
                    ).fetchone():
                        grant(conn, role, pid, ts)
            print("habitat approve/publish.request grants applied")

        # --- Evidence type content_draft ---
        if "core_evidence_types" in tabs:
            conn.execute(
                """
                INSERT INTO core_evidence_types (
                  evidence_type, description, status, created_at, updated_at
                ) VALUES ('content_draft', 'Habitat content draft / slot fingerprint', 'ACTIVE', ?, ?)
                ON CONFLICT(evidence_type) DO UPDATE SET
                  description=excluded.description,
                  status=excluded.status,
                  updated_at=excluded.updated_at
                """,
                (ts, ts),
            )
            print("evidence type content_draft")

        # --- ONE governance policy ---
        if "core_governance_policies" in tabs:
            conn.execute(
                """
                INSERT INTO core_governance_policies (
                  policy_id, policy_version, entity_id, scope_id, action_type, request_type,
                  required_permission_code, authority_required, approval_required,
                  required_decision_count, evidence_required, prohibited,
                  amount_min, amount_max, currency,
                  effective_from, effective_to, status, created_at, updated_at,
                  created_by_person_id
                ) VALUES (
                  ?, 1, ?, ?, ?, 'GENERAL',
                  'content.habitat.approve', 0, 1,
                  1, 1, 0,
                  NULL, NULL, NULL,
                  '2026-01-01T00:00:00Z', NULL, 'ACTIVE', ?, ?,
                  'PERS-MATT'
                )
                ON CONFLICT(policy_id, policy_version) DO UPDATE SET
                  entity_id=excluded.entity_id,
                  scope_id=excluded.scope_id,
                  action_type=excluded.action_type,
                  request_type=excluded.request_type,
                  required_permission_code=excluded.required_permission_code,
                  authority_required=excluded.authority_required,
                  approval_required=excluded.approval_required,
                  required_decision_count=excluded.required_decision_count,
                  evidence_required=excluded.evidence_required,
                  prohibited=excluded.prohibited,
                  status=excluded.status,
                  updated_at=excluded.updated_at
                """,
                (POLICY_ID, ENTITY, SCOPE, ACTION, ts, ts),
            )
            print(f"governance policy {POLICY_ID}")

        # --- ONE evidence requirement ---
        if "core_evidence_requirements" in tabs:
            conn.execute(
                """
                INSERT INTO core_evidence_requirements (
                  requirement_id, requirement_version, entity_id, scope_id,
                  action_type, request_type, evidence_type, min_count,
                  verification_needed, effective_from, effective_to, status,
                  created_at, updated_at, created_by_person_id
                ) VALUES (
                  ?, 1, ?, ?,
                  ?, 'GENERAL', 'content_draft', 1,
                  0, '2026-01-01T00:00:00Z', NULL, 'ACTIVE',
                  ?, ?, 'PERS-MATT'
                )
                ON CONFLICT(requirement_id, requirement_version) DO UPDATE SET
                  entity_id=excluded.entity_id,
                  scope_id=excluded.scope_id,
                  action_type=excluded.action_type,
                  request_type=excluded.request_type,
                  evidence_type=excluded.evidence_type,
                  min_count=excluded.min_count,
                  verification_needed=excluded.verification_needed,
                  status=excluded.status,
                  updated_at=excluded.updated_at
                """,
                (EVR_ID, ENTITY, SCOPE, ACTION, ts, ts),
            )
            print(f"evidence requirement {EVR_ID}")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )

        n_auth2 = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
        n_pol = (
            conn.execute("SELECT COUNT(*) FROM core_governance_policies").fetchone()[0]
            if "core_governance_policies" in tabs or True
            else 0
        )
        n_pol_extra = conn.execute(
            """
            SELECT COUNT(*) FROM core_governance_policies
            WHERE NOT (policy_id=? AND policy_version=1)
            """,
            (POLICY_ID,),
        ).fetchone()[0]
        n_evr = conn.execute("SELECT COUNT(*) FROM core_evidence_requirements").fetchone()[0]
        n_evr_extra = conn.execute(
            """
            SELECT COUNT(*) FROM core_evidence_requirements
            WHERE NOT (requirement_id=? AND requirement_version=1)
            """,
            (EVR_ID,),
        ).fetchone()[0]
        n_sod2 = (
            conn.execute("SELECT COUNT(*) FROM core_sod_constraints").fetchone()[0]
            if "core_sod_constraints" in {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            else 0
        )
        n_exc = 0
        if "core_governance_exceptions" in {
            r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }:
            n_exc = conn.execute("SELECT COUNT(*) FROM core_governance_exceptions").fetchone()[0]

        habitat_pol = conn.execute(
            "SELECT COUNT(*) FROM core_governance_policies WHERE policy_id=?",
            (POLICY_ID,),
        ).fetchone()[0]
        habitat_evr = conn.execute(
            "SELECT COUNT(*) FROM core_evidence_requirements WHERE requirement_id=?",
            (EVR_ID,),
        ).fetchone()[0]
        brand_ok = conn.execute(
            "SELECT COUNT(*) FROM org_brands WHERE brand_id=? AND entity_id=?",
            (BRAND_ID, ENTITY),
        ).fetchone()[0]
        role_ok = conn.execute(
            "SELECT COUNT(*) FROM org_roles WHERE role_id=?", (ROLE_CD,)
        ).fetchone()[0]

        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (
                MIGRATION_ID,
                ts,
                (
                    f"habitat publish gate; brand={brand_ok}; role_cd={role_ok}; "
                    f"pol={habitat_pol}; evr={habitat_evr}; auth_limits={n_auth2}; "
                    f"sod={n_sod2}; exceptions={n_exc}; "
                    f"extra_pol={n_pol_extra}; extra_evr={n_evr_extra}"
                ),
            ),
        )
        conn.commit()

        print(f"  org_authority_limits={n_auth2}")
        print(f"  core_governance_policies={n_pol} (habitat={habitat_pol}, extra={n_pol_extra})")
        print(f"  core_evidence_requirements={n_evr} (habitat={habitat_evr}, extra={n_evr_extra})")
        print(f"  core_sod_constraints={n_sod2}")
        print(f"  core_governance_exceptions={n_exc}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")

        if n_auth2 != 0:
            print(f"REFUSE: org_authority_limits must stay 0, got {n_auth2}", file=sys.stderr)
            return 2
        if n_sod2 != 0:
            print(f"REFUSE: SoD must stay 0, got {n_sod2}", file=sys.stderr)
            return 2
        if n_exc != 0:
            print(f"REFUSE: exceptions must stay 0, got {n_exc}", file=sys.stderr)
            return 2
        if n_pol_extra != 0:
            print(
                f"REFUSE: non-Habitat governance policies must stay 0, got {n_pol_extra}",
                file=sys.stderr,
            )
            return 2
        if n_evr_extra != 0:
            print(
                f"REFUSE: non-Habitat evidence requirements must stay 0, got {n_evr_extra}",
                file=sys.stderr,
            )
            return 2
        if habitat_pol != 1:
            print(f"REFUSE: expected 1 Habitat policy, got {habitat_pol}", file=sys.stderr)
            return 2
        if habitat_evr != 1:
            print(f"REFUSE: expected 1 Habitat evidence req, got {habitat_evr}", file=sys.stderr)
            return 2
        if brand_ok != 1:
            print(f"REFUSE: habitat brand missing under ENT-GGV", file=sys.stderr)
            return 2
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
