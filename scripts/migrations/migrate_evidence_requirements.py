#!/usr/bin/env python3
"""018 Evidence Requirement Enforcement — idempotent Beta-only migration.

Creates core_evidence_types + core_evidence_records + core_evidence_requirements.
Seeds evidence.record.submit / .read / evidence.requirement.manage permission codes
(Matt manage+read+submit grants; no broad grants to other roles).
NO live requirement or evidence record seed. Live Authority/Policies/SoD stay 0.
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
SQL = Path(__file__).resolve().parent / "018_evidence_requirements.sql"
MIGRATION_ID = "018_evidence_requirements"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))
BACKUP_DIR = ROOT / "catalog" / "backups"

# Owner P0 5 Oct 2026: retention/free-space guard (docs/BACKUP-RETENTION.md)
import sys as _bp_sys  # noqa: E402
if str(ROOT / "scripts") not in _bp_sys.path:
    _bp_sys.path.insert(0, str(ROOT / "scripts"))
from core.backup_policy import premig_backup  # noqa: E402
ROLE_MATT = "ROLE-MATT"

PERMS = (
    (
        "PERM-EVIDENCE-RECORD-SUBMIT",
        "evidence.record.submit",
        "evidence",
        "submit",
        "Submit evidence records within Entity+Permission scope",
    ),
    (
        "PERM-EVIDENCE-RECORD-READ",
        "evidence.record.read",
        "evidence",
        "read",
        "Read evidence records within Entity+Permission scope",
    ),
    (
        "PERM-EVIDENCE-REQUIREMENT-MANAGE",
        "evidence.requirement.manage",
        "evidence",
        "manage",
        "Manage evidence requirements (Matt defaults; no broad live grants)",
    ),
)

# Catalog types only — not live business requirements / evidence rows.
CATALOG_TYPES = (
    ("receiving_document", "Receiving / delivery document"),
    ("photo", "Photographic evidence"),
    ("invoice", "Invoice or billing document"),
    ("delivery_note", "Delivery note"),
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
    dest = BACKUP_DIR / f"pre-evidence-requirements-{stamp()}.sqlite"
    dest = premig_backup(db_path, dest)
    digest = _sha256(dest)
    sha_path = (
        ROOT
        / "state"
        / f"evidence-requirements-backup-{dest.stem.replace('pre-evidence-requirements-', '')}.sha256"
    )
    sha_path.parent.mkdir(parents=True, exist_ok=True)
    sha_path.write_text(f"{digest}  {dest.relative_to(ROOT)}\n", encoding="utf-8")
    print(f"BACKUP={dest}")
    print(f"SHA256={digest}")
    return dest, digest


def _seed_permission_codes(conn: sqlite3.Connection, ts: str) -> None:
    """Catalog codes. Matt gets submit/read/manage. No other role grants."""
    for perm_id, code, resource, action, desc in PERMS:
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
        # manage + read stay Matt-only. submit may be granted by Habitat pilot (020)
        # to CONTENT-MGMT / CONTENT-CREW — do not wipe those on re-run.
        if perm_id != "PERM-EVIDENCE-RECORD-SUBMIT":
            conn.execute(
                """
                DELETE FROM org_role_permissions
                WHERE permission_id=? AND role_id != ?
                """,
                (perm_id, ROLE_MATT),
            )
        conn.execute(
            """
            INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
            VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET
              effect=excluded.effect,
              updated_at=excluded.updated_at
            """,
            (ROLE_MATT, perm_id, ts, ts),
        )


def _seed_catalog_types(conn: sqlite3.Connection, ts: str) -> None:
    for etype, desc in CATALOG_TYPES:
        conn.execute(
            """
            INSERT INTO core_evidence_types (
              evidence_type, description, status, created_at, updated_at
            ) VALUES (?, ?, 'ACTIVE', ?, ?)
            ON CONFLICT(evidence_type) DO UPDATE SET
              description=excluded.description,
              status=excluded.status,
              updated_at=excluded.updated_at
            """,
            (etype, desc, ts, ts),
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
            if (
                "core_evidence_types" in tabs
                and "core_evidence_records" in tabs
                and "core_evidence_requirements" in tabs
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

        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

        conn.executescript(SQL.read_text(encoding="utf-8"))
        print(
            "DDL applied (core_evidence_types + core_evidence_records + "
            "core_evidence_requirements)"
        )

        _seed_catalog_types(conn, ts)
        print("catalog evidence types seeded (not requirements/records)")

        if "org_permissions" in tabs:
            _seed_permission_codes(conn, ts)
            print("evidence.* permission codes seeded (Matt-only grants)")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        n_req = conn.execute("SELECT COUNT(*) FROM core_evidence_requirements").fetchone()[0]
        n_rec = conn.execute("SELECT COUNT(*) FROM core_evidence_records").fetchone()[0]
        n_types = conn.execute("SELECT COUNT(*) FROM core_evidence_types").fetchone()[0]
        n_auth2 = conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0]
        n_pol = (
            conn.execute("SELECT COUNT(*) FROM core_governance_policies").fetchone()[0]
            if "core_governance_policies" in tabs
            else 0
        )
        n_sod = (
            conn.execute("SELECT COUNT(*) FROM core_sod_constraints").fetchone()[0]
            if "core_sod_constraints" in tabs
            else 0
        )
        # submit may be Habitat-granted; manage+read must stay Matt-only
        non_matt_grants = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions
            WHERE permission_id IN (
              'PERM-EVIDENCE-RECORD-READ',
              'PERM-EVIDENCE-REQUIREMENT-MANAGE'
            ) AND role_id != ?
            """,
            (ROLE_MATT,),
        ).fetchone()[0]
        matt_manage = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions
            WHERE role_id=? AND permission_id='PERM-EVIDENCE-REQUIREMENT-MANAGE'
            """,
            (ROLE_MATT,),
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
                    f"evidence requirements; req={n_req}; records={n_rec}; types={n_types}; "
                    f"auth_limits={n_auth2}; gov_policies={n_pol}; sod={n_sod}; "
                    f"matt_manage={matt_manage}; non_matt_grants={non_matt_grants}; "
                    f"no live requirement/evidence seed"
                ),
            ),
        )
        conn.commit()

        print(f"  core_evidence_requirements={n_req}")
        print(f"  core_evidence_records={n_rec}")
        print(f"  core_evidence_types={n_types}")
        print(f"  org_authority_limits={n_auth2}")
        print(f"  core_governance_policies={n_pol}")
        print(f"  core_sod_constraints={n_sod}")
        print(f"  matt_manage_grant={matt_manage}")
        print(f"  non_matt_grants={non_matt_grants}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        if n_auth2 != 0:
            print(
                f"REFUSE: live org_authority_limits must stay 0, got {n_auth2}",
                file=sys.stderr,
            )
            return 2
        # Habitat pilot (020) may seed exactly EVR-HABITAT-CONTENT-PUBLISH + GPO.
        n_req_extra = conn.execute(
            """
            SELECT COUNT(*) FROM core_evidence_requirements
            WHERE NOT (requirement_id='EVR-HABITAT-CONTENT-PUBLISH' AND requirement_version=1)
            """
        ).fetchone()[0]
        if n_req_extra != 0 and is_live:
            print(
                f"REFUSE: non-Habitat evidence requirements must stay 0, got {n_req_extra}",
                file=sys.stderr,
            )
            return 2
        if n_rec != 0 and is_live:
            print(
                f"REFUSE: live evidence records must stay 0, got {n_rec}",
                file=sys.stderr,
            )
            return 2
        n_pol_extra = conn.execute(
            """
            SELECT COUNT(*) FROM core_governance_policies
            WHERE NOT (policy_id='GPO-HABITAT-CONTENT-PUBLISH' AND policy_version=1)
            """
        ).fetchone()[0]
        if n_pol_extra != 0 and is_live:
            print(
                f"REFUSE: non-Habitat governance policies must stay 0, got {n_pol_extra}",
                file=sys.stderr,
            )
            return 2
        if n_sod != 0 and is_live:
            print(
                f"REFUSE: live SoD constraints must stay 0, got {n_sod}",
                file=sys.stderr,
            )
            return 2
        if non_matt_grants != 0:
            print(
                f"REFUSE: evidence manage/read must have 0 non-Matt grants, got {non_matt_grants}",
                file=sys.stderr,
            )
            return 2
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
