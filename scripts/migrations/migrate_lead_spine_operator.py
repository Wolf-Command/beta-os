#!/usr/bin/env python3
"""024 Lead Spine operator fixtures — Beta only.

Seeds PERS-LEAD-DEMO + habitat-scoped lead.* role (fixture only).
Seeds exactly 8 DEMO leads on brand habitat / ENT-GGV / source_system=fixture.
Idempotent. No staff role grants. No live import. No external writes.
Bound: beta-lead-spine-operator.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

DB = ROOT / "catalog" / "content_library.sqlite"
MIGRATION_ID = "024_lead_spine_operator"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))

ENTITY = "ENT-GGV"
BRAND = "habitat"
SOURCE_SYSTEM = "fixture"

PERS_DEMO = "PERS-LEAD-DEMO"
ROLE_DEMO = "ROLE-LEAD-DEMO-FIXTURE"
POS_DEMO = "POS-LEAD-DEMO-FIXTURE"
ASG_DEMO = "ASG-LEAD-DEMO-FIXTURE"
SCOPE_DEMO = "SCOPE-LEAD-DEMO-HAB"
EVIDENCE_ID = "EVD-LEAD-DEMO-VERIFIED"
WORK_ITEM_ID = "WI-LEAD-DEMO-FIXTURE"  # optional; not required on cards

LEAD_PERMS = (
    "PERM-LEAD-READ",
    "PERM-LEAD-CREATE",
    "PERM-LEAD-EVENT",
    "PERM-LEAD-ASSIGN",
)

STAFF_ROLES = (
    "ROLE-MATT",
    "ROLE-OWNER",
    "ROLE-AMANDA",
    "ROLE-HAIKAL",
    "ROLE-MISA",
    "ROLE-DEVI",
)

# (source_id, label, source_stage, assign_demo, claim, verify, touch_offset_hours)
# wolf_stage comes from map; banana stays null.
DEMOS: list[tuple[str, str, str, bool, bool, bool, int | None]] = [
    ("demo-01", "DEMO Open unassigned", "new", False, False, False, None),
    ("demo-02", "DEMO Active assigned", "process", True, False, False, 2),
    ("demo-03", "DEMO Parked", "parked", False, False, False, None),
    ("demo-04", "DEMO Closed no conversion", "closed", False, False, False, None),
    ("demo-05", "DEMO Closed claimed", "won", False, True, False, None),
    ("demo-06", "DEMO Closed verified", "reserved/bought", False, False, True, None),
    ("demo-07", "DEMO Active no touch", "followup", False, False, False, None),
    ("demo-08", "DEMO Unmapped banana", "banana", False, False, False, None),
]


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def observed_at(hours_ago: int = 24) -> str:
    return (datetime.now(TZ8) - timedelta(hours=hours_ago)).isoformat(timespec="seconds")


def assert_beta(db_path: Path) -> None:
    s = str(db_path.resolve())
    for frag in FORBIDDEN:
        if frag in s:
            raise SystemExit(f"REFUSE: {frag} in {s}")
    if "beta-os" not in s:
        raise SystemExit(f"REFUSE: not beta-os: {s}")


def seed_demo_person(conn: sqlite3.Connection, ts: str) -> None:
    conn.execute(
        """
        INSERT INTO org_persons (
          person_id, display_name, legal_name, status, created_at, updated_at
        ) VALUES (?, 'Demo operator', NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET
          display_name='Demo operator',
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (PERS_DEMO, ts, ts),
    )
    # No authentication email / Cloudflare binding — deliberately omit auth tables.
    conn.execute(
        """
        INSERT INTO org_roles (
          role_id, display_name, department_id, role_type, status, created_at, updated_at
        ) VALUES (?, 'Lead Spine Demo Fixture', NULL, 'fixture', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO UPDATE SET
          status='ACTIVE', role_type='fixture', updated_at=excluded.updated_at
        """,
        (ROLE_DEMO, ts, ts),
    )
    for perm_id in LEAD_PERMS:
        conn.execute(
            """
            INSERT INTO org_role_permissions (
              role_id, permission_id, effect, created_at, updated_at
            ) VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET
              effect='ALLOW', updated_at=excluded.updated_at
            """,
            (ROLE_DEMO, perm_id, ts, ts),
        )
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, location_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES (?, ?, ?, NULL, ?, NULL, 'Lead Spine Demo', 'ACTIVE', 1.0, ?, ?)
        ON CONFLICT(position_id) DO UPDATE SET
          status='ACTIVE', brand_id=excluded.brand_id, updated_at=excluded.updated_at
        """,
        (POS_DEMO, ROLE_DEMO, ENTITY, BRAND, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at,
          status, is_primary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET
          status='ACTIVE', end_at=NULL, person_id=excluded.person_id,
          updated_at=excluded.updated_at
        """,
        (ASG_DEMO, PERS_DEMO, POS_DEMO, ts, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_scopes (
          scope_id, scope_type, display_name, status, created_at, updated_at
        ) VALUES (?, 'brand', 'Lead Spine Demo Habitat', 'ACTIVE', ?, ?)
        ON CONFLICT(scope_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (SCOPE_DEMO, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES (?, 'brand', ?, ?)
        ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
        """,
        (SCOPE_DEMO, BRAND, ts),
    )
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(conn, ASG_DEMO, SCOPE_DEMO, ts, ts)


def find_lead(conn: sqlite3.Connection, source_id: str) -> dict | None:
    row = conn.execute(
        """
        SELECT * FROM core_leads
        WHERE entity_id=? AND brand_id=? AND source_system=? AND source_id=?
        """,
        (ENTITY, BRAND, SOURCE_SYSTEM, source_id),
    ).fetchone()
    return dict(row) if row else None


def ensure_evidence(conn: sqlite3.Connection, lead_id: str, ts: str) -> None:
    conn.execute(
        """
        INSERT INTO core_evidence_types (evidence_type, description, status, created_at, updated_at)
        VALUES ('LEAD_CONVERSION', 'Lead conversion fixture', 'ACTIVE', ?, ?)
        ON CONFLICT(evidence_type) DO NOTHING
        """,
        (ts, ts),
    )
    conn.execute(
        """
        INSERT INTO core_evidence_records (
          evidence_id, entity_id, scope_id, evidence_type, source_type, source_reference,
          object_ref, content_hash, submitted_by_person_id, submitted_by_assignment_id,
          submitted_at, captured_at, status, verification_status,
          verified_by_person_id, verified_at, verification_reason,
          governed_object_type, governed_object_id, classification, metadata_json,
          created_at, updated_at, invalidated_at, invalidate_reason
        ) VALUES (
          ?, ?, NULL, 'LEAD_CONVERSION', 'SYSTEM', 'fixture',
          NULL, NULL, ?, NULL,
          ?, NULL, 'ACTIVE', 'VERIFIED',
          ?, ?, 'demo verified evidence',
          'lead', ?, NULL, ?,
          ?, ?, NULL, NULL
        )
        ON CONFLICT(evidence_id) DO UPDATE SET
          verification_status='VERIFIED', status='ACTIVE',
          governed_object_id=excluded.governed_object_id,
          updated_at=excluded.updated_at
        """,
        (
            EVIDENCE_ID,
            ENTITY,
            PERS_DEMO,
            ts,
            PERS_DEMO,
            ts,
            lead_id,
            json.dumps({"demo": True}, separators=(",", ":"), sort_keys=True),
            ts,
            ts,
        ),
    )


def seed_leads(conn: sqlite3.Connection, ts: str) -> int:
    import core.lead_spine as ls

    ls.ensure_schema(conn)
    created_or_kept = 0
    for source_id, label, source_stage, assign, claim, verify, touch_h in DEMOS:
        existing = find_lead(conn, source_id)
        if existing:
            created_or_kept += 1
            continue
        obs = observed_at(30)
        result = ls.ingest_observation(
            entity_id=ENTITY,
            brand_id=BRAND,
            source_system=SOURCE_SYSTEM,
            source_id=source_id,
            source_observed_at=obs,
            source_stage=source_stage,
            provenance={"demo": True, "label": label},
            payload={"label": label},
            observation_key=f"fixture:{source_id}:observe",
            actor_type="SYSTEM",
            conn=conn,
        )
        lead = result["lead"]
        lead_id = lead["lead_id"]
        if assign:
            ls.assign_owner(
                lead_id,
                PERS_DEMO,
                owner_assignment_id=ASG_DEMO,
                verified_person_id=PERS_DEMO,
                conn=conn,
            )
        if touch_h is not None:
            touch_ts = (
                datetime.fromisoformat(obs.replace("Z", "+00:00"))
                if obs.endswith("Z")
                else datetime.fromisoformat(obs)
            ) + timedelta(hours=touch_h)
            ls.record_human_touch(
                lead_id,
                touched_at=touch_ts.isoformat(timespec="seconds"),
                actor_type="SYSTEM",
                conn=conn,
            )
        if claim:
            ls.claim_conversion(lead_id, actor_type="SYSTEM", conn=conn)
        if verify:
            ensure_evidence(conn, lead_id, ts)
            # claim then verify so status path is honest
            cur = find_lead(conn, source_id)
            if cur and cur.get("conversion_status") != "VERIFIED":
                if cur.get("conversion_status") != "CLAIMED":
                    ls.claim_conversion(lead_id, actor_type="SYSTEM", conn=conn)
                ls.verify_conversion(
                    lead_id, EVIDENCE_ID, actor_type="SYSTEM", conn=conn
                )
        created_or_kept += 1
    return created_or_kept


def staff_lead_grants(conn: sqlite3.Connection) -> int:
    placeholders = ",".join("?" * len(STAFF_ROLES))
    return conn.execute(
        f"""
        SELECT COUNT(*) FROM org_role_permissions
        WHERE permission_id IN ({",".join("?" * len(LEAD_PERMS))})
          AND role_id IN ({placeholders})
        """,
        (*LEAD_PERMS, *STAFF_ROLES),
    ).fetchone()[0]


def fixture_role_grants(conn: sqlite3.Connection) -> int:
    return conn.execute(
        """
        SELECT COUNT(*) FROM org_role_permissions
        WHERE role_id=? AND permission_id IN (
          'PERM-LEAD-READ','PERM-LEAD-CREATE','PERM-LEAD-EVENT','PERM-LEAD-ASSIGN'
        )
        """,
        (ROLE_DEMO,),
    ).fetchone()[0]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    db_path = Path(args[0]).resolve() if args else DB.resolve()
    assert_beta(db_path)

    ts = now_iso()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        seed_demo_person(conn, ts)
        conn.commit()

        n = seed_leads(conn, ts)
        conn.commit()

        # Sanity: demo-08 wolf_stage null, source banana
        banana = find_lead(conn, "demo-08")
        if banana and banana.get("source_stage") != "banana":
            print("WARN: demo-08 source_stage not banana", file=sys.stderr)
            return 2
        if banana and banana.get("wolf_stage") is not None:
            print("WARN: demo-08 wolf_stage should be null", file=sys.stderr)
            return 2

        verified = find_lead(conn, "demo-06")
        if verified and verified.get("conversion_status") != "VERIFIED":
            print("WARN: demo-06 not VERIFIED", file=sys.stderr)
            return 2

        staff = staff_lead_grants(conn)
        fixture_grants = fixture_role_grants(conn)
        n_leads = conn.execute(
            """
            SELECT COUNT(*) FROM core_leads
            WHERE brand_id=? AND source_system=?
            """,
            (BRAND, SOURCE_SYSTEM),
        ).fetchone()[0]

        # Ensure PERS-LEAD-DEMO has no auth identity row if table exists
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        auth_rows = 0
        if "org_auth_identities" in tabs:
            cols = {
                r[1]
                for r in conn.execute("PRAGMA table_info(org_auth_identities)").fetchall()
            }
            if "person_id" in cols:
                auth_rows = conn.execute(
                    "SELECT COUNT(*) FROM org_auth_identities WHERE person_id=?",
                    (PERS_DEMO,),
                ).fetchone()[0]

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
                (
                    f"operator fixtures; leads={n_leads}; fixture_grants={fixture_grants}; "
                    f"staff_lead_grants={staff}; auth_bindings={auth_rows}"
                ),
            ),
        )
        conn.commit()

        print(f"  demo leads kept/created pass={n} fixture_leads={n_leads}")
        print(f"  fixture role grants={fixture_grants}")
        print(f"  staff lead grants={staff}")
        print(f"  PERS-LEAD-DEMO auth bindings={auth_rows}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        if fixture_grants != 4:
            print(f"WARN: expected 4 fixture grants, got {fixture_grants}", file=sys.stderr)
            return 2
        if staff != 0:
            print(f"REFUSE: staff lead grants must be 0, got {staff}", file=sys.stderr)
            return 2
        if auth_rows != 0:
            print(f"REFUSE: demo person must have no auth binding, got {auth_rows}", file=sys.stderr)
            return 2
        if n_leads < 8:
            print(f"WARN: expected >=8 fixture leads, got {n_leads}", file=sys.stderr)
            return 2
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
