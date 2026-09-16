#!/usr/bin/env python3
"""Person + Authentication Identity repository (Beta).

A human is not an email address. Email is an AuthenticationIdentity identifier.

Role, Position, Assignment and permission engines are out of scope for this module.
Real Cloudflare JWT verification is NOT BUILT.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

IDENTITY_ASSURANCE_DEVELOPMENT = "development_assertion"
IDENTITY_ASSURANCE_NONE = "none"


def db_connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = path.resolve()
    if "beta-os" not in str(resolved):
        raise RuntimeError(f"identity refuses non-beta DB: {resolved}")
    if "wolf-system" in str(resolved):
        raise RuntimeError(f"identity refuses wolf-system path: {resolved}")
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


def list_persons(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    """Minimal public person summaries — no emails."""
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT person_id, display_name, status, created_at, updated_at
            FROM org_persons
            ORDER BY person_id
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def get_person(person_id: str, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    pid = (person_id or "").strip()
    if not pid:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        return _row(
            c.execute(
                """
                SELECT person_id, display_name, legal_name, status, created_at, updated_at
                FROM org_persons WHERE person_id=?
                """,
                (pid,),
            ).fetchone()
        )
    finally:
        if own:
            c.close()


def list_auth_identities_for_person(
    person_id: str, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    pid = (person_id or "").strip()
    if not pid:
        return []
    own = conn is None
    c = conn or db_connect()
    try:
        rows = c.execute(
            """
            SELECT auth_identity_id, person_id, provider, identifier, status,
                   is_primary, created_at, updated_at, last_verified_at
            FROM org_auth_identities
            WHERE person_id=?
            ORDER BY is_primary DESC, auth_identity_id
            """,
            (pid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            c.close()


def resolve_person_from_email(
    email: str | None, conn: sqlite3.Connection | None = None
) -> dict[str, Any] | None:
    """Transitional adapter: permissions.subject email → Person.

    Does not authenticate. Only maps known AuthIdentity provider=email.
    """
    ident = (email or "").strip().lower()
    if not ident or "@" not in ident:
        return None
    own = conn is None
    c = conn or db_connect()
    try:
        row = c.execute(
            """
            SELECT p.person_id, p.display_name, p.legal_name, p.status,
                   p.created_at, p.updated_at,
                   a.auth_identity_id, a.provider, a.identifier AS auth_identifier,
                   a.status AS auth_status
            FROM org_auth_identities a
            JOIN org_persons p ON p.person_id = a.person_id
            WHERE a.provider='email'
              AND lower(a.identifier)=?
              AND a.status='ACTIVE'
              AND p.status='ACTIVE'
            LIMIT 1
            """,
            (ident,),
        ).fetchone()
        return _row(row)
    finally:
        if own:
            c.close()


def person_summary(person: dict[str, Any] | None) -> dict[str, Any] | None:
    if not person:
        return None
    return {
        "person_id": person.get("person_id"),
        "display_name": person.get("display_name"),
        "status": person.get("status"),
    }


def resolve_from_development_assertion(
    asserted_identifier: str | None, conn: sqlite3.Connection | None = None
) -> dict[str, Any]:
    """Resolve Person from DEVELOPMENT identity assertion (spoofable email subject).

    Never claims production authentication.
    """
    person = resolve_person_from_email(asserted_identifier, conn=conn)
    return {
        "identity_assurance": IDENTITY_ASSURANCE_DEVELOPMENT
        if asserted_identifier
        else IDENTITY_ASSURANCE_NONE,
        "asserted_identifier": (asserted_identifier or "").strip().lower() or None,
        "person": person_summary(person),
        "person_id": person["person_id"] if person else None,
        "auth_identity_id": person.get("auth_identity_id") if person else None,
        "real_authentication": False,
        "note": (
            "DEVELOPMENT_IDENTITY_ASSERTION only. "
            "X-Wolf-Subject / JSON subject is spoofable. "
            "Cloudflare Access JWT verification is NOT BUILT."
        ),
    }
