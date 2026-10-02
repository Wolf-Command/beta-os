#!/usr/bin/env python3
"""IZA-UMA-CAPTAIN-CASHIER-1 — Person/Role/Assignment/roster seed (Beta only).

Decision served: Owner order IZA-UMA-CAPTAIN-CASHIER-DAILY-CLOSE-20261002
(credit_override=OWNER_ORDER). HR emp BZG26023002 (Iza Zainatulloh Hulhidayati)
— emp id noted here only; not written into org_persons.

Creates PERS-IZA + AUTH-IZA-EMAIL, ROLE-BZG-CASHIER + ROLE-BZG-CAPTAIN with
identical CASHIER_BUNDLE grants (reuse existing permission_ids), Uma Captain
position/assignment scoped SCOPE-BZG-UMA only, and venue_closer_roster VCR-UMA-2.
Does not modify VCR-UMA-1 / Devi. No finance/bank/Owner/admin/HR/AMG/GGV grants.
No invented EDC IDs or variance tolerances. staff_ready / human_commissioned stay false.
"""
from __future__ import annotations

import hashlib
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

from core.scope import upsert_assignment_scope  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"
MIGRATION_ID = "iza_uma_captain_cashier_1"
PACK = "IZA-UMA-CAPTAIN-CASHIER-1"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")

# HR-authorised — employees.db BZG26023002. Do not invent another email/name.
IZA = "PERS-IZA"
IZA_AUTH = "AUTH-IZA-EMAIL"
IZA_EMAIL = "izazaen00@gmail.com"
IZA_DISPLAY = "Iza Zainatulloh Hulhidayati"
IZA_LEGAL = "Iza Zainatulloh Hulhidayati"
# HR emp id BZG26023002 — migration comment only; not an org_persons column.

ENTITY = "ENT-BZG"
BRAND = "BZG-UMA"
DEPT = "DEPT-BZG-FB"
SCOPE_UMA = "SCOPE-BZG-UMA"

ROLE_CASHIER = "ROLE-BZG-CASHIER"
ROLE_CAPTAIN = "ROLE-BZG-CAPTAIN"
POS_CAPTAIN = "POS-BZG-CAPTAIN-UMA-1"
ASG_IZA = "ASG-IZA-CAPTAIN-UMA-1"
ROSTER_IZA = "VCR-UMA-2"
ROSTER_DEVI = "VCR-UMA-1"
DEVI = "PERS-DEVI"

START = "2026-10-02T00:00:00+08:00"

# Identical bundle on Cashier + Captain (composition = inheritance). Reuse live ids.
CASHIER_BUNDLE = (
    "venue.close.read",
    "venue.close.submit",
    "evidence.record.read",
    "evidence.record.submit",
    "work.read",
    "work.update",
    "work.complete",
)

DENY_ASSERT = (
    "payment.approve",
    "payment.execute",
    "vendor.bank.change",
    "bzg.pr.payment_approve",
    "finance.nota.read",
    "finance.invoice.read",
    "atrium.ledger.read",
    "atrium.journal.approve",
    "atrium.journal.post",
    "organisation.role.read",
    "organisation.person.read",
    "governance.exception.authorise",
    "venue.close.verify",
    "progress.read",
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


def _ensure_person(conn: sqlite3.Connection, ts: str) -> None:
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
        (IZA, IZA_DISPLAY, IZA_LEGAL, ts, ts),
    )
    existing = conn.execute(
        """
        SELECT person_id FROM org_auth_identities
        WHERE provider='email' AND lower(identifier)=?
        """,
        (IZA_EMAIL,),
    ).fetchone()
    if existing is None:
        conn.execute(
            """
            INSERT INTO org_auth_identities (
              auth_identity_id, person_id, provider, identifier, status,
              is_primary, created_at, updated_at
            ) VALUES (?, ?, 'email', ?, 'ACTIVE', 1, ?, ?)
            """,
            (IZA_AUTH, IZA, IZA_EMAIL, ts, ts),
        )
    elif str(existing[0]) != IZA:
        raise RuntimeError(
            f"REFUSE: {IZA_EMAIL} already bound to {existing[0]} (want {IZA})"
        )
    else:
        conn.execute(
            """
            UPDATE org_auth_identities
            SET status='ACTIVE', is_primary=1, updated_at=?
            WHERE provider='email' AND lower(identifier)=?
            """,
            (ts, IZA_EMAIL),
        )
    owners = conn.execute(
        """
        SELECT person_id FROM org_auth_identities
        WHERE provider='email' AND lower(identifier)=?
        """,
        (IZA_EMAIL,),
    ).fetchall()
    if len(owners) != 1 or str(owners[0][0]) != IZA:
        raise RuntimeError(f"email ownership assert failed: {owners}")


def _upsert_role(conn: sqlite3.Connection, role_id: str, display_name: str, ts: str) -> None:
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
        (role_id, display_name, DEPT, ts, ts),
    )


def _grant_bundle(conn: sqlite3.Connection, role_id: str, ts: str) -> list[str]:
    granted: list[str] = []
    for code in CASHIER_BUNDLE:
        row = conn.execute(
            "SELECT permission_id, status FROM org_permissions WHERE code=?",
            (code,),
        ).fetchone()
        if not row or str(row[1]) != "ACTIVE":
            raise RuntimeError(f"REFUSE: missing ACTIVE permission {code}")
        conn.execute(
            """
            INSERT INTO org_role_permissions (
              role_id, permission_id, effect, created_at, updated_at
            ) VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET
              effect='ALLOW', updated_at=excluded.updated_at
            """,
            (role_id, row[0], ts, ts),
        )
        granted.append(code)
    return granted


def _assert_no_forbidden(conn: sqlite3.Connection, role_id: str) -> None:
    rows = conn.execute(
        """
        SELECT p.code FROM org_role_permissions rp
        JOIN org_permissions p ON p.permission_id = rp.permission_id
        WHERE rp.role_id=? AND rp.effect='ALLOW'
        """,
        (role_id,),
    ).fetchall()
    allowed = {r[0] for r in rows}
    leaked = [c for c in DENY_ASSERT if c in allowed]
    if leaked:
        raise RuntimeError(f"REFUSE: {role_id} must not have {leaked}")
    extra = allowed - set(CASHIER_BUNDLE)
    if extra:
        raise RuntimeError(f"REFUSE: {role_id} has unexpected grants {sorted(extra)}")


def _ensure_scope_uma(conn: sqlite3.Connection, ts: str) -> None:
    row = conn.execute(
        "SELECT scope_id FROM org_scopes WHERE scope_id=?", (SCOPE_UMA,)
    ).fetchone()
    if not row:
        raise RuntimeError(f"REFUSE: missing scope {SCOPE_UMA}")
    # Do not invent targets — SCOPE-BZG-UMA already brand-scoped in catalog.


def _seat_captain(conn: sqlite3.Connection, ts: str) -> None:
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, location_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES (?, ?, ?, NULL, ?, ?, 'Floor Captain · Uma Blu', 'ACTIVE', 1.0, ?, ?)
        ON CONFLICT(position_id) DO UPDATE SET
          role_id=excluded.role_id,
          entity_id=excluded.entity_id,
          brand_id=excluded.brand_id,
          department_id=excluded.department_id,
          position_label='Floor Captain · Uma Blu',
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (POS_CAPTAIN, ROLE_CAPTAIN, ENTITY, BRAND, DEPT, ts, ts),
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
        """,
        (ASG_IZA, IZA, POS_CAPTAIN, START, ts, ts),
    )
    # SCOPE-BZG-UMA only — never SCOPE-BZG-ENTITY / finance / AMG / GGV.
    existing = conn.execute(
        """
        SELECT 1 FROM org_assignment_scopes
        WHERE assignment_id=? AND scope_id=? AND status='ACTIVE' AND end_at IS NULL
        """,
        (ASG_IZA, SCOPE_UMA),
    ).fetchone()
    if not existing:
        upsert_assignment_scope(conn, ASG_IZA, SCOPE_UMA, START, ts)

    scopes = {
        str(r[0])
        for r in conn.execute(
            """
            SELECT scope_id FROM org_assignment_scopes
            WHERE assignment_id=? AND status='ACTIVE' AND end_at IS NULL
            """,
            (ASG_IZA,),
        )
    }
    if scopes != {SCOPE_UMA}:
        raise RuntimeError(f"REFUSE: Iza scopes must be {{{SCOPE_UMA}}} only, got {scopes}")


def _roster_multi_closer(conn: sqlite3.Connection, ts: str) -> None:
    # Preserve Devi row — do not UPDATE/END VCR-UMA-1.
    devi = conn.execute(
        """
        SELECT roster_id, person_id, status FROM venue_closer_roster
        WHERE roster_id=?
        """,
        (ROSTER_DEVI,),
    ).fetchone()
    if not devi:
        raise RuntimeError(f"REFUSE: expected existing {ROSTER_DEVI} (Devi closer)")
    if str(devi[1]) != DEVI or str(devi[2]) != "ACTIVE":
        raise RuntimeError(
            f"REFUSE: {ROSTER_DEVI} must stay ACTIVE PERS-DEVI, got {dict(devi)}"
        )

    conn.execute(
        """
        INSERT INTO venue_closer_roster (
          roster_id, brand_id, position_id, person_id, assignment_id,
          status, note, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'ACTIVE',
          'Multi-closer via ACTIVE roster rows. Captain seat; Devi VCR-UMA-1 untouched.',
          ?, ?)
        ON CONFLICT(roster_id) DO UPDATE SET
          brand_id=excluded.brand_id,
          position_id=excluded.position_id,
          person_id=excluded.person_id,
          assignment_id=excluded.assignment_id,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (ROSTER_IZA, BRAND, POS_CAPTAIN, IZA, ASG_IZA, ts, ts),
    )


def run(db_path: Path | None = None) -> dict:
    path = Path(db_path) if db_path else DB
    bad = _refuse_path(path)
    if bad:
        raise RuntimeError(f"REFUSE: {bad} in {path}")

    ts = now_iso()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bak = BACKUP_DIR / f"pre-iza-uma-captain-cashier-1-{stamp()}.sqlite"
    shutil.copy2(path, bak)
    digest = _sha256(bak)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        _ensure_person(conn, ts)
        _upsert_role(conn, ROLE_CASHIER, "Cashier", ts)
        _upsert_role(conn, ROLE_CAPTAIN, "Floor Captain", ts)
        cashier_grants = _grant_bundle(conn, ROLE_CASHIER, ts)
        captain_grants = _grant_bundle(conn, ROLE_CAPTAIN, ts)
        if cashier_grants != captain_grants:
            raise RuntimeError("REFUSE: Cashier/Captain bundles must be identical")
        _assert_no_forbidden(conn, ROLE_CASHIER)
        _assert_no_forbidden(conn, ROLE_CAPTAIN)
        _ensure_scope_uma(conn, ts)
        _seat_captain(conn, ts)
        _roster_multi_closer(conn, ts)

        # Honesty: variance policies + EDC terminals untouched (no invent).
        pol = int(
            conn.execute(
                "SELECT COUNT(*) FROM venue_close_variance_policies WHERE status='ACTIVE'"
            ).fetchone()[0]
        )
        edc = 0
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "venue_close_edc_terminals" in tabs:
            edc = int(conn.execute("SELECT COUNT(*) FROM venue_close_edc_terminals").fetchone()[0])

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY,
              applied_at TEXT NOT NULL,
              note TEXT
            )
            """
        )
        note = (
            f"{PACK}; HR emp BZG26023002; Captain⊇Cashier composition; "
            f"VCR-UMA-2 multi-closer; Devi {ROSTER_DEVI} preserved"
        )
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (MIGRATION_ID, ts, note),
        )
        conn.commit()

        receipt = {
            "migration_id": MIGRATION_ID,
            "pack": PACK,
            "ran_at": ts,
            "backup": str(bak),
            "backup_sha256": digest,
            "person_id": IZA,
            "auth_identity_id": IZA_AUTH,
            "email": IZA_EMAIL,
            "roles": [ROLE_CASHIER, ROLE_CAPTAIN],
            "cashier_bundle": list(CASHIER_BUNDLE),
            "position_id": POS_CAPTAIN,
            "assignment_id": ASG_IZA,
            "scope_ids": [SCOPE_UMA],
            "roster_id": ROSTER_IZA,
            "devi_roster_preserved": ROSTER_DEVI,
            "active_variance_policies": pol,
            "edc_terminals_count": edc,
            "staff_ready": False,
            "human_commissioned": False,
        }
        return receipt
    finally:
        conn.close()


if __name__ == "__main__":
    out = run()
    print(json.dumps(out, indent=2))
    print("RESULT: PASS")
