#!/usr/bin/env python3
"""HUMFIX-1B — hold premature RETESTs, scope dedupe, fresh SoD journal.

Decision served: Matt relay 29 Sep 2026 ~11:14 WITA / HUMFIX-1 (Peaches eye gaps 29 Sep).
Extends HUMFIX-1. Beta catalog + atrium beta DB only. Does not flip staff_ready.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import work_items as wi  # noqa: E402

CATALOG = ROOT / "catalog" / "content_library.sqlite"
ATRIUM_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")

RETEST_IDS = (
    # Haikal
    "WI-1e3435eb-4d39-4559-a2fa-3cf13b523ec2",
    "WI-2a6edd45-1659-446a-91ea-8b533faf580e",
    "WI-fa0f1e2e-9564-41f6-8edf-cbc76a3173e2",
    "WI-cbbbaf8c-55bf-4167-a7ae-6d0f974d5b9f",
    # Zayen
    "WI-4049b070-1938-4b33-bc6f-abcf195d4298",
    "WI-1b6f3982-7112-4ff9-9147-97e0ed1c645d",
    "WI-41cd93c3-a8d5-48ad-9368-db17d44e80a4",
    "WI-a3a4044c-843d-41f4-86eb-8d738f78e2b1",
    "WI-4e4566db-72bf-4710-b6a9-0b02f64bbc2b",
    "WI-1804769a-551b-4df0-9e8c-231dd4131417",
    "WI-2649ab6e-653a-472b-b632-dfb236ee64f2",
    "WI-3e07075e-72cb-4e5f-bea4-97003d7c678f",
)

ROUTING_HELD = "HELD"
HELD_REASON = "Repair in progress — HUMFIX-1B"
FRESH_JOURNAL = "JRN-HUMFIX-PREP2"
CONTENT_TEAM = (
    "PERS-HAIKAL",
    "PERS-MISA",
    "PERS-ZARAH",
    "PERS-FRAIL",
    "PERS-YUDI",
    "PERS-GERY",
    "PERS-ALAM",
    "PERS-TJ",
    "PERS-NATA",
    "PERS-RAPP",
)


def _ts() -> str:
    return wi.now_utc_iso()


def hold_premature_retests(conn: sqlite3.Connection) -> dict:
    """Mark HUMFIX-1 RETESTs HELD so staff do not FAIL on half-fixed screens."""
    ts = _ts()
    held = []
    for wid in RETEST_IDS:
        row = conn.execute(
            "SELECT work_item_id, status, routing_state FROM core_work_items WHERE work_item_id=?",
            (wid,),
        ).fetchone()
        if not row:
            continue
        conn.execute(
            """
            UPDATE core_work_items
            SET routing_state=?, routing_reason=?, updated_at=?
            WHERE work_item_id=?
            """,
            (ROUTING_HELD, HELD_REASON, ts, wid),
        )
        held.append(wid)
    return {"held": held, "count": len(held)}


def reopen_held_retests(conn: sqlite3.Connection) -> dict:
    """Clear HELD after HUMFIX-1B checks pass — history kept, status unchanged."""
    ts = _ts()
    opened = []
    for wid in RETEST_IDS:
        row = conn.execute(
            "SELECT routing_state FROM core_work_items WHERE work_item_id=?",
            (wid,),
        ).fetchone()
        if not row:
            continue
        if (row[0] or "") != ROUTING_HELD:
            continue
        conn.execute(
            """
            UPDATE core_work_items
            SET routing_state=NULL, routing_reason=NULL, updated_at=?
            WHERE work_item_id=?
            """,
            (ts, wid),
        )
        opened.append(wid)
    return {"reopened": opened, "count": len(opened)}


def dedupe_assignment_scopes(conn: sqlite3.Connection) -> dict:
    """Non-destructive: end-date duplicate ACTIVE (assignment, scope) rows; keep earliest."""
    ts = _ts()
    dups = conn.execute(
        """
        SELECT assignment_id, scope_id, COUNT(*) AS n
        FROM org_assignment_scopes
        WHERE status='ACTIVE'
        GROUP BY assignment_id, scope_id
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    ended = 0
    kept = 0
    for assignment_id, scope_id, _n in dups:
        rows = conn.execute(
            """
            SELECT start_at, created_at
            FROM org_assignment_scopes
            WHERE assignment_id=? AND scope_id=? AND status='ACTIVE'
            ORDER BY created_at ASC, start_at ASC
            """,
            (assignment_id, scope_id),
        ).fetchall()
        if len(rows) < 2:
            continue
        keep_start = rows[0][0]
        kept += 1
        for start_at, _created in rows[1:]:
            conn.execute(
                """
                UPDATE org_assignment_scopes
                SET status='ENDED', end_at=?, updated_at=?
                WHERE assignment_id=? AND scope_id=? AND start_at=? AND status='ACTIVE'
                """,
                (ts, ts, assignment_id, scope_id, start_at),
            )
            ended += 1
            _ = keep_start  # kept row untouched
    return {"duplicate_groups": len(dups), "ended": ended, "kept_groups": kept}


def seed_fresh_sod_journal(atrium_path: Path) -> dict:
    """VALIDATED commissioning journal prepared by Owner (not Zayen). Live Beta fixture."""
    if not atrium_path.is_file():
        return {"ok": False, "error": "atrium db missing", "path": str(atrium_path)}
    a = sqlite3.connect(str(atrium_path))
    try:
        existing = a.execute(
            "SELECT journal_id, status, created_by FROM journal_headers WHERE journal_id=?",
            (FRESH_JOURNAL,),
        ).fetchone()
        if existing and existing[1] == "VALIDATED":
            return {
                "ok": True,
                "journal_id": FRESH_JOURNAL,
                "status": existing[1],
                "created_by": existing[2],
                "already": True,
            }
        a.execute("DELETE FROM journal_lines WHERE journal_id=?", (FRESH_JOURNAL,))
        a.execute("DELETE FROM journal_headers WHERE journal_id=?", (FRESH_JOURNAL,))
        a.execute(
            """
            INSERT INTO journal_headers (
              journal_id, journal_date, period, status, source_type,
              source_reference, created_by, approved_by, posted_at
            ) VALUES (?, '2026-09-29', '2026-09', 'VALIDATED', 'MANUAL',
              'HUMFIX-1B commissioning test journal (SoD approve)',
              'Owner (Matt)', '', '')
            """,
            (FRESH_JOURNAL,),
        )
        a.execute(
            """
            INSERT INTO journal_lines (
              journal_id, line_no, account_code, department_code, debit, credit, description
            ) VALUES
              (?, 1, '1020', '100', 150000.0, 0.0, 'HUMFIX-1B commissioning float'),
              (?, 2, '4000', '100', 0.0, 150000.0, 'HUMFIX-1B commissioning offset')
            """,
            (FRESH_JOURNAL, FRESH_JOURNAL),
        )
        a.commit()
        return {
            "ok": True,
            "journal_id": FRESH_JOURNAL,
            "status": "VALIDATED",
            "created_by": "Owner (Matt)",
            "already": False,
        }
    finally:
        a.close()


def content_team_brand_table(conn: sqlite3.Connection) -> list[dict]:
    from core import nas_library as nas
    from core import staff_access as sa

    out = []
    for pid in CONTENT_TEAM:
        person = conn.execute(
            "SELECT display_name FROM org_persons WHERE person_id=?", (pid,)
        ).fetchone()
        name = person[0] if person else pid
        asg = conn.execute(
            """
            SELECT assignment_id FROM org_assignments
            WHERE person_id=? AND status='ACTIVE'
            ORDER BY is_primary DESC, updated_at DESC LIMIT 1
            """,
            (pid,),
        ).fetchone()
        scopes = []
        brands: list[str] = []
        if asg:
            scopes = [
                r[0]
                for r in conn.execute(
                    """
                    SELECT scope_id FROM org_assignment_scopes
                    WHERE assignment_id=? AND status='ACTIVE'
                    """,
                    (asg[0],),
                ).fetchall()
            ]
            brands = nas.brands_for_scopes(scopes)
        out.append(
            {
                "person_id": pid,
                "name": name,
                "assignment_id": asg[0] if asg else None,
                "brand_count": len(brands),
                "brands": brands,
                "scopes": scopes,
                "has_content_all": nas.CONTENT_ALL_BRANDS_SCOPE in scopes,
            }
        )
    return out


def verify_mulzij_preparer(atrium_path: Path) -> dict:
    if not atrium_path.is_file():
        return {"journal_id": "JRN-MULZIJ3N-117", "found": False}
    a = sqlite3.connect(str(atrium_path))
    try:
        row = a.execute(
            "SELECT created_by, status FROM journal_headers WHERE journal_id=?",
            ("JRN-MULZIJ3N-117",),
        ).fetchone()
        if not row:
            return {"journal_id": "JRN-MULZIJ3N-117", "found": False}
        created_by = row[0] or ""
        zayen_prepared = "zayen" in created_by.lower()
        return {
            "journal_id": "JRN-MULZIJ3N-117",
            "found": True,
            "created_by": created_by,
            "status": row[1],
            "zayen_prepared": zayen_prepared,
            "approve_must_hide_for_zayen": zayen_prepared,
        }
    finally:
        a.close()


def posted_ledger_probe(atrium_path: Path) -> dict:
    if not atrium_path.is_file():
        return {"posted_journals": 0, "posted_lines": 0, "source": "missing"}
    a = sqlite3.connect(str(atrium_path))
    try:
        posted = a.execute(
            "SELECT COUNT(*) FROM journal_headers WHERE status='POSTED'"
        ).fetchone()[0]
        lines = a.execute(
            """
            SELECT COUNT(*) FROM journal_lines jl
            JOIN journal_headers j ON j.journal_id=jl.journal_id
            WHERE j.status='POSTED'
            """
        ).fetchone()[0]
        prop = a.execute(
            "SELECT property_name FROM system_settings LIMIT 1"
        ).fetchone()
        return {
            "posted_journals": int(posted),
            "posted_lines": int(lines),
            "property_name": (prop[0] if prop else "") or "",
            "source": str(atrium_path),
            "real_posted_data_present": int(posted) > 0,
        }
    finally:
        a.close()


def run(
    *,
    db_path: Path | None = None,
    atrium_path: Path | None = None,
    hold: bool = True,
    reopen: bool = False,
    dedupe: bool = True,
    seed_journal: bool = True,
) -> dict:
    catalog = Path(db_path or CATALOG)
    atrium = Path(atrium_path or ATRIUM_DB)
    conn = wi.db_connect(catalog)
    try:
        out: dict = {"catalog": str(catalog), "atrium": str(atrium)}
        if reopen:
            out["reopen"] = reopen_held_retests(conn)
        elif hold:
            out["hold"] = hold_premature_retests(conn)
        if dedupe:
            out["dedupe"] = dedupe_assignment_scopes(conn)
        if seed_journal:
            out["fresh_journal"] = seed_fresh_sod_journal(atrium)
        out["mulzij"] = verify_mulzij_preparer(atrium)
        out["ledger_probe"] = posted_ledger_probe(atrium)
        out["content_team"] = content_team_brand_table(conn)
        conn.commit()
        return out
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--db", type=Path, default=None)
    ap.add_argument("--atrium", type=Path, default=None)
    ap.add_argument("--reopen", action="store_true", help="Re-open held RETESTs")
    ap.add_argument("--no-hold", action="store_true")
    ap.add_argument("--no-dedupe", action="store_true")
    ap.add_argument("--no-journal", action="store_true")
    args = ap.parse_args()
    out = run(
        db_path=args.db,
        atrium_path=args.atrium,
        hold=not args.no_hold and not args.reopen,
        reopen=args.reopen,
        dedupe=not args.no_dedupe,
        seed_journal=not args.no_journal,
    )
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
