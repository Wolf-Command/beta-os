#!/usr/bin/env python3
"""Phase 2.6 Team Readiness — idempotent migration (Beta OS :8788 only).

- Permissions: Matt/Amanda create+edit+approve; Haikal/Misa edit+prod+upload+WI (NO create, NO approve)
- Brand theming + default_assignee columns
- Plan review_state for CHANGES PENDING REVIEW flow
- Asset hash/size/detail_tags/readiness for Library + Upload
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "catalog" / "content_library.sqlite"

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"

FULL = (
    "can_create_plan",
    "can_edit_plan",
    "can_approve_plan",
    "can_view_plan",
    "can_update_production",
    "can_upload",
    "can_use_wolf_intelligence",
)
CREW = (
    "can_edit_plan",
    "can_view_plan",
    "can_update_production",
    "can_upload",
    "can_use_wolf_intelligence",
)
# Explicitly revoked for crew
CREW_REVOKE = ("can_create_plan", "can_approve_plan")


def now_iso() -> str:
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def col_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    names = {r[1] for r in rows}
    return col in names


def add_col(conn: sqlite3.Connection, table: str, col: str, decl: str) -> None:
    if not col_exists(conn, table, col):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        print(f"  + {table}.{col}")
    else:
        print(f"  = {table}.{col} exists")


def set_perms(conn: sqlite3.Connection, subject: str, perms: tuple[str, ...], revoke: tuple[str, ...] = ()) -> None:
    ts = now_iso()
    for p in revoke:
        conn.execute(
            "DELETE FROM permissions WHERE lower(subject)=? AND permission=?",
            (subject.lower(), p),
        )
    for p in perms:
        exists = conn.execute(
            "SELECT 1 FROM permissions WHERE lower(subject)=? AND permission=? AND ifnull(brand_id,'')=''",
            (subject.lower(), p),
        ).fetchone()
        if not exists:
            conn.execute(
                """
                INSERT INTO permissions (subject, permission, brand_id, granted_at, granted_by)
                VALUES (?, ?, NULL, ?, ?)
                """,
                (subject.lower(), p, ts, "phase2.6-migration"),
            )


def main() -> int:
    if not DB.exists():
        print(f"ERROR: DB missing {DB}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    print("Phase 2.6 migration…")

    # --- brands theming + default assignee ---
    add_col(conn, "brands", "theme_json", "TEXT")
    add_col(conn, "brands", "default_assignee", "TEXT")
    add_col(conn, "brands", "logo_url", "TEXT")

    # Habitat restrained theme (logo + primary + accent; one common font via app)
    habitat_theme = (
        '{"primary":"#6ea8ff","accent":"#8b7cff","neutral":"#8b95a8",'
        '"font":"Inter, SF Pro Text, system-ui, sans-serif","logo_text":"Habitat"}'
    )
    conn.execute(
        """
        UPDATE brands
        SET theme_json=COALESCE(NULLIF(theme_json,''), ?),
            default_assignee=COALESCE(NULLIF(default_assignee,''), ?),
            updated_at=?
        WHERE id='habitat'
        """,
        (habitat_theme, HAIKAL, now_iso()),
    )

    # --- plan review state (UI: APPROVED / CHANGES PENDING REVIEW) ---
    add_col(conn, "content_plans", "review_state", "TEXT")
    # Backfill: Human_Approved → APPROVED (unless already pending)
    conn.execute(
        """
        UPDATE content_plans
        SET review_state='APPROVED'
        WHERE status IN ('Human_Approved','HUMAN_APPROVED','Approved')
          AND (review_state IS NULL OR review_state='')
        """
    )
    conn.execute(
        """
        UPDATE content_plans
        SET review_state='WORKING'
        WHERE status IN ('Working_Draft','AI_Generated','Draft')
          AND (review_state IS NULL OR review_state='')
        """
    )

    # Preserve last approved snapshot id (optional convenience)
    add_col(conn, "content_plans", "approved_revision_id", "INTEGER")

    # --- assets: hash / size / tags / readiness ---
    for col, decl in (
        ("content_hash", "TEXT"),
        ("file_size", "INTEGER"),
        ("detail_tags_json", "TEXT"),
        ("readiness", "TEXT"),
        ("readiness_note", "TEXT"),
    ):
        add_col(conn, "assets", col, decl)
        add_col(conn, "staged_assets", col, decl)

    conn.execute(
        "UPDATE assets SET readiness=COALESCE(NULLIF(readiness,''), CASE "
        "WHEN library_status IN ('LIBRARY_READY','READY') OR status='VERIFIED' THEN 'READY_TO_USE' "
        "WHEN library_status IN ('CHECKING','UPLOAD_RECEIVED') OR processing_status='CHECKING' THEN 'CHECKING' "
        "WHEN library_status='FAILED' OR processing_status='FAILED' THEN 'FAILED' "
        "ELSE 'CHECKING' END) "
        "WHERE readiness IS NULL OR readiness=''"
    )

    # Indexes (idempotent)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_assets_hash ON assets(content_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_assets_size ON assets(file_size)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_plans_review ON content_plans(review_state)")

    # --- permissions matrix (supersedes 2.5A for Haikal/Misa approve) ---
    print("  permissions matrix…")
    set_perms(conn, MATT, FULL)
    set_perms(conn, AMANDA, FULL)
    set_perms(conn, HAIKAL, CREW, revoke=CREW_REVOKE)
    set_perms(conn, MISA, CREW, revoke=CREW_REVOKE)

    conn.commit()

    print("  permission dump:")
    for row in conn.execute(
        "SELECT subject, group_concat(permission) AS p FROM permissions GROUP BY subject ORDER BY subject"
    ):
        print(f"    {row['subject']} → {row['p']}")

    n = conn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
    plans = conn.execute("SELECT COUNT(*) FROM content_plans").fetchone()[0]
    print(f"  permissions rows={n} plans={plans}")
    conn.close()
    print("DONE phase2.6 migration")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
