#!/usr/bin/env python3
"""006 Person + Authentication Identity — idempotent Beta-only migration.

Seeds known Content Machine permission subjects as Person + email AuthIdentity.
Does NOT invent Role/RBAC. Does NOT wire CF JWT. Does NOT touch production.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "catalog" / "content_library.sqlite"
SQL = Path(__file__).resolve().parent / "006_person_auth_identity.sql"
MIGRATION_ID = "006_person_auth_identity"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))

# Known Beta permission subjects → Person (approved / current system only)
# legal_name only where canon supports; else NULL
SEEDS = (
    # person_id, display_name, legal_name, auth_id, email
    ("PERS-MATT", "Matthew Goss", "Matthew Goss", "AUTH-MATT-EMAIL", "mrwolf@wolfcommand.net"),
    ("PERS-AMANDA", "Amanda", "Amanda Goss", "AUTH-AMANDA-EMAIL", "amanda@wolfcommand.net"),
    ("PERS-HAIKAL", "Haikal", None, "AUTH-HAIKAL-EMAIL", "haikalqilbari123@gmail.com"),
    ("PERS-MISA", "Misa", None, "AUTH-MISA-EMAIL", "mlsary111@gmail.com"),
)


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def main() -> int:
    db_path = DB.resolve()
    s = str(db_path)
    for frag in FORBIDDEN:
        if frag in s:
            print(f"REFUSE: {frag} in DB path {s}", file=sys.stderr)
            return 2
    if "beta-os" not in s:
        print(f"REFUSE: not under beta-os: {s}", file=sys.stderr)
        return 2

    ts = now_iso()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SQL.read_text(encoding="utf-8"))
        print("DDL applied")

        for person_id, display_name, legal_name, auth_id, email in SEEDS:
            ident = email.strip().lower()
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
                (person_id, display_name, legal_name, ts, ts),
            )
            # Prevent same email mapping to a different person
            existing = conn.execute(
                """
                SELECT person_id FROM org_auth_identities
                WHERE provider='email' AND lower(identifier)=?
                """,
                (ident,),
            ).fetchone()
            if existing and existing["person_id"] != person_id:
                print(
                    f"REFUSE: email {ident} already mapped to {existing['person_id']}",
                    file=sys.stderr,
                )
                return 2
            # Upsert by stable auth_identity_id; UNIQUE(provider,identifier) also enforced
            row = conn.execute(
                "SELECT auth_identity_id, person_id FROM org_auth_identities WHERE provider='email' AND lower(identifier)=?",
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
                    (auth_id, person_id, ident, ts, ts),
                )
            else:
                if row["person_id"] != person_id:
                    print(
                        f"REFUSE: email {ident} already mapped to {row['person_id']}",
                        file=sys.stderr,
                    )
                    return 2
                conn.execute(
                    """
                    UPDATE org_auth_identities
                    SET status='ACTIVE', is_primary=1, updated_at=?,
                        auth_identity_id=?, person_id=?
                    WHERE provider='email' AND lower(identifier)=?
                    """,
                    (ts, auth_id, person_id, ident),
                )

        # schema_migrations table may exist from 005
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY,
              applied_at TEXT NOT NULL,
              note TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (MIGRATION_ID, ts, "Person + AuthenticationIdentity; transitional email adapter"),
        )
        conn.commit()

        n_p = conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0]
        n_a = conn.execute("SELECT COUNT(*) FROM org_auth_identities").fetchone()[0]
        n_perm = conn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
        print(f"org_persons={n_p} org_auth_identities={n_a} permissions={n_perm}")
        for r in conn.execute(
            """
            SELECT p.person_id, p.display_name, a.identifier
            FROM org_persons p
            JOIN org_auth_identities a ON a.person_id=p.person_id
            ORDER BY p.person_id
            """
        ):
            print(f"  {r['person_id']} | {r['display_name']} | {r['identifier']}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
