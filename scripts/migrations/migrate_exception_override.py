#!/usr/bin/env python3
"""019 Exception / Override Governance — idempotent Beta-only migration.

Creates core_exceptionable_controls + core_governance_exceptions.
Seeds governance.exception.* permission codes
(Matt authorise+revoke+request+read grants; no broad grants to other roles).
NO live exception seed. Live Authority/Policies/SoD/Evidence-reqs stay 0.
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
SQL = Path(__file__).resolve().parent / "019_exception_override.sql"
MIGRATION_ID = "019_exception_override"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))
BACKUP_DIR = ROOT / "catalog" / "backups"
ROLE_MATT = "ROLE-MATT"

PERMS = (
    (
        "PERM-GOV-EXCEPTION-REQUEST",
        "governance.exception.request",
        "governance",
        "request",
        "Request a governed exception (does not bypass controls)",
    ),
    (
        "PERM-GOV-EXCEPTION-AUTHORISE",
        "governance.exception.authorise",
        "governance",
        "authorise",
        "Authorise a governed exception (Matt Person gate also required)",
    ),
    (
        "PERM-GOV-EXCEPTION-REVOKE",
        "governance.exception.revoke",
        "governance",
        "revoke",
        "Revoke / reject a governed exception (Matt Person gate also required)",
    ),
    (
        "PERM-GOV-EXCEPTION-READ",
        "governance.exception.read",
        "governance",
        "read",
        "Read governed exceptions within Entity scope",
    ),
)

# Matt gets all four. Authorise/revoke are Matt-only on live (enforced here + Person gate).
MATT_GRANTS = (
    "PERM-GOV-EXCEPTION-REQUEST",
    "PERM-GOV-EXCEPTION-AUTHORISE",
    "PERM-GOV-EXCEPTION-REVOKE",
    "PERM-GOV-EXCEPTION-READ",
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
    dest = BACKUP_DIR / f"pre-exception-override-{stamp()}.sqlite"
    shutil.copy2(db_path, dest)
    digest = _sha256(dest)
    sha_path = (
        ROOT
        / "state"
        / f"exception-override-backup-{dest.stem.replace('pre-exception-override-', '')}.sha256"
    )
    sha_path.parent.mkdir(parents=True, exist_ok=True)
    sha_path.write_text(f"{digest}  {dest.relative_to(ROOT)}\n", encoding="utf-8")
    print(f"BACKUP={dest}")
    print(f"SHA256={digest}")
    return dest, digest


def _seed_permission_codes(conn: sqlite3.Connection, ts: str) -> None:
    """Catalog codes. Matt gets request/authorise/revoke/read. No other role grants."""
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
        conn.execute(
            """
            DELETE FROM org_role_permissions
            WHERE permission_id=? AND role_id != ?
            """,
            (perm_id, ROLE_MATT),
        )

    for perm_id in MATT_GRANTS:
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
                "core_exceptionable_controls" in tabs
                and "core_governance_exceptions" in tabs
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
            "DDL applied (core_exceptionable_controls + core_governance_exceptions)"
        )

        if "org_permissions" in tabs:
            _seed_permission_codes(conn, ts)
            print("governance.exception.* permission codes seeded (Matt-only grants)")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        n_exc = conn.execute("SELECT COUNT(*) FROM core_governance_exceptions").fetchone()[0]
        n_ctl = conn.execute("SELECT COUNT(*) FROM core_exceptionable_controls").fetchone()[0]
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
        n_evr = (
            conn.execute("SELECT COUNT(*) FROM core_evidence_requirements").fetchone()[0]
            if "core_evidence_requirements" in tabs
            else 0
        )
        non_matt_grants = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions
            WHERE permission_id IN (
              'PERM-GOV-EXCEPTION-REQUEST',
              'PERM-GOV-EXCEPTION-AUTHORISE',
              'PERM-GOV-EXCEPTION-REVOKE',
              'PERM-GOV-EXCEPTION-READ'
            ) AND role_id != ?
            """,
            (ROLE_MATT,),
        ).fetchone()[0]
        matt_auth = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions
            WHERE role_id=? AND permission_id='PERM-GOV-EXCEPTION-AUTHORISE'
            """,
            (ROLE_MATT,),
        ).fetchone()[0]
        matt_rev = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions
            WHERE role_id=? AND permission_id='PERM-GOV-EXCEPTION-REVOKE'
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
                    f"exception override; exceptions={n_exc}; controls={n_ctl}; "
                    f"auth_limits={n_auth2}; gov_policies={n_pol}; sod={n_sod}; "
                    f"evr={n_evr}; matt_authorise={matt_auth}; matt_revoke={matt_rev}; "
                    f"non_matt_grants={non_matt_grants}; no live exception seed"
                ),
            ),
        )
        conn.commit()

        print(f"  core_governance_exceptions={n_exc}")
        print(f"  core_exceptionable_controls={n_ctl}")
        print(f"  org_authority_limits={n_auth2}")
        print(f"  core_governance_policies={n_pol}")
        print(f"  core_sod_constraints={n_sod}")
        print(f"  core_evidence_requirements={n_evr}")
        print(f"  matt_authorise_grant={matt_auth}")
        print(f"  matt_revoke_grant={matt_rev}")
        print(f"  non_matt_grants={non_matt_grants}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        if n_auth2 != 0:
            print(
                f"REFUSE: live org_authority_limits must stay 0, got {n_auth2}",
                file=sys.stderr,
            )
            return 2
        if n_exc != 0 and is_live:
            print(
                f"REFUSE: live governance exceptions must stay 0, got {n_exc}",
                file=sys.stderr,
            )
            return 2
        if n_pol != 0 and is_live:
            print(
                f"REFUSE: live governance policies must stay 0, got {n_pol}",
                file=sys.stderr,
            )
            return 2
        if n_sod != 0 and is_live:
            print(
                f"REFUSE: live SoD constraints must stay 0, got {n_sod}",
                file=sys.stderr,
            )
            return 2
        if n_evr != 0 and is_live:
            print(
                f"REFUSE: live evidence requirements must stay 0, got {n_evr}",
                file=sys.stderr,
            )
            return 2
        if non_matt_grants != 0:
            print(
                f"REFUSE: governance.exception.* must have 0 non-Matt grants, "
                f"got {non_matt_grants}",
                file=sys.stderr,
            )
            return 2
        if matt_auth != 1 or matt_rev != 1:
            print(
                f"REFUSE: Matt authorise/revoke grants required, "
                f"got authorise={matt_auth} revoke={matt_rev}",
                file=sys.stderr,
            )
            return 2
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
