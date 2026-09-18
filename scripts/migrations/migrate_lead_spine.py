#!/usr/bin/env python3
"""023 Lead Spine — idempotent Beta-only migration.

Tables + four permission codes. 0 leads. 0 role grants.
No live import. No Production. Bound: beta-lead-spine-fixtures.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "catalog" / "content_library.sqlite"
MIGRATION_ID = "023_lead_spine"
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production")
TZ8 = timezone(timedelta(hours=8))

PERMS = (
    ("PERM-LEAD-READ", "lead.read", "lead", "read", "Read leads in brand scope"),
    ("PERM-LEAD-CREATE", "lead.create", "lead", "create", "Create / ingest lead observations"),
    (
        "PERM-LEAD-EVENT",
        "lead.event.append",
        "lead",
        "event.append",
        "Append lead events",
    ),
    ("PERM-LEAD-ASSIGN", "lead.assign", "lead", "assign", "Assign lead owner"),
)

STAGE_MAP_SEED: list[tuple[str, str, str | None]] = [
    ("CONTENT-DEMAND-5", "new", "OPEN"),
    ("CONTENT-DEMAND-5", "process", "ACTIVE"),
    ("CONTENT-DEMAND-5", "followup", "ACTIVE"),
    ("CONTENT-DEMAND-5", "parked", "PARKED"),
    ("CONTENT-DEMAND-5", "closed", "CLOSED"),
    ("BAKE-8", "new", "OPEN"),
    ("BAKE-8", "contacted", "ACTIVE"),
    ("BAKE-8", "qualified", "ACTIVE"),
    ("BAKE-8", "viewing", "ACTIVE"),
    ("BAKE-8", "offer", "ACTIVE"),
    ("BAKE-8", "won", "CLOSED"),
    ("BAKE-8", "not_interested", "CLOSED"),
    ("BAKE-8", "parked", "PARKED"),
    ("IMPORT-NOTE-2026-08-21", "new", "OPEN"),
    ("IMPORT-NOTE-2026-08-21", "in process", "ACTIVE"),
    ("IMPORT-NOTE-2026-08-21", "follow-up", "ACTIVE"),
    ("IMPORT-NOTE-2026-08-21", "parked", "PARKED"),
    ("IMPORT-NOTE-2026-08-21", "reserved/bought", "CLOSED"),
]


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS core_leads (
          lead_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          brand_id TEXT NOT NULL,
          source_system TEXT NOT NULL,
          source_id TEXT NOT NULL,
          source_observed_at TEXT NULL,
          wolf_ingested_at TEXT NOT NULL,
          provenance_json TEXT NOT NULL,
          source_stage TEXT NULL,
          wolf_stage TEXT NULL,
          owner_person_id TEXT NULL,
          owner_assignment_id TEXT NULL,
          first_human_touch_at TEXT NULL,
          current_work_item_id TEXT NULL,
          conversion_status TEXT NULL,
          conversion_evidence_id TEXT NULL,
          UNIQUE (entity_id, brand_id, source_system, source_id)
        );

        CREATE TABLE IF NOT EXISTS core_lead_events (
          event_id TEXT PRIMARY KEY,
          lead_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          occurred_at TEXT NULL,
          recorded_at TEXT NOT NULL,
          actor_type TEXT NOT NULL,
          actor_person_id TEXT NULL,
          payload_json TEXT NOT NULL,
          supersedes_event_id TEXT NULL,
          observation_key TEXT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_core_lead_events_obs_key
          ON core_lead_events(lead_id, observation_key)
          WHERE observation_key IS NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_core_lead_events_lead
          ON core_lead_events(lead_id);

        CREATE TABLE IF NOT EXISTS core_lead_stage_maps (
          vocab_id TEXT NOT NULL,
          source_stage TEXT NOT NULL,
          wolf_stage TEXT NULL,
          PRIMARY KEY (vocab_id, source_stage)
        );
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_core_lead_events_no_update
        BEFORE UPDATE ON core_lead_events
        BEGIN
          SELECT RAISE(ABORT, 'core_lead_events is append-only');
        END
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_core_lead_events_no_delete
        BEFORE DELETE ON core_lead_events
        BEGIN
          SELECT RAISE(ABORT, 'core_lead_events is append-only');
        END
        """
    )
    for vocab_id, source_stage, wolf_stage in STAGE_MAP_SEED:
        conn.execute(
            """
            INSERT INTO core_lead_stage_maps (vocab_id, source_stage, wolf_stage)
            VALUES (?, ?, ?)
            ON CONFLICT(vocab_id, source_stage) DO UPDATE SET
              wolf_stage=excluded.wolf_stage
            """,
            (vocab_id, source_stage, wolf_stage),
        )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    db_path = Path(args[0]).resolve() if args else DB.resolve()
    s = str(db_path)
    for frag in FORBIDDEN:
        if frag in s:
            print(f"REFUSE: {frag} in {s}", file=sys.stderr)
            return 2
    if "beta-os" not in s:
        print(f"REFUSE: not beta-os: {s}", file=sys.stderr)
        return 2

    ts = now_iso()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        apply_schema(conn)
        print("DDL applied")

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
        # Explicitly do NOT insert into org_role_permissions.

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT
            )
            """
        )
        n_leads = conn.execute("SELECT COUNT(*) FROM core_leads").fetchone()[0]
        n_maps = conn.execute("SELECT COUNT(*) FROM core_lead_stage_maps").fetchone()[0]
        n_perms = conn.execute(
            """
            SELECT COUNT(*) FROM org_permissions
            WHERE permission_id IN (
              'PERM-LEAD-READ','PERM-LEAD-CREATE','PERM-LEAD-EVENT','PERM-LEAD-ASSIGN'
            ) AND status='ACTIVE'
            """
        ).fetchone()[0]
        role_grants = conn.execute(
            """
            SELECT COUNT(*) FROM org_role_permissions
            WHERE permission_id IN (
              'PERM-LEAD-READ','PERM-LEAD-CREATE','PERM-LEAD-EVENT','PERM-LEAD-ASSIGN'
            )
            """
        ).fetchone()[0]
        vocabs = [
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT vocab_id FROM core_lead_stage_maps ORDER BY vocab_id"
            ).fetchall()
        ]
        conn.execute(
            """
            INSERT INTO schema_migrations (id, applied_at, note) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
            """,
            (
                MIGRATION_ID,
                ts,
                (
                    f"Lead spine; leads={n_leads}; maps={n_maps}; "
                    f"perms={n_perms}; role_grants={role_grants}; vocabs={vocabs}"
                ),
            ),
        )
        conn.commit()

        print(f"  core_leads={n_leads}")
        print(f"  core_lead_stage_maps={n_maps}")
        print(f"  lead permission codes={n_perms}")
        print(f"  lead role grants={role_grants}")
        print(f"  vocabs={vocabs}")
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check={ok}")
        if n_perms != 4:
            print(f"WARN: expected 4 lead perms, got {n_perms}", file=sys.stderr)
            return 2
        if role_grants != 0:
            print(f"WARN: lead role grants must be 0, got {role_grants}", file=sys.stderr)
            return 2
        if n_leads != 0:
            print(f"NOTE: leads already present: {n_leads}")
        return 0 if ok == "ok" else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
