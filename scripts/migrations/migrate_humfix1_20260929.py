#!/usr/bin/env python3
"""HUMFIX-1 — record Matt-relay FAILs, brand-scope repair, FC approve grant.

Decision served: Matt relay 29 Sep 2026 ~11:14 WITA (HUMFIX-1 brief).
Extends HUMANCOMM-1. Beta catalog only. Does not flip staff_ready.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import content_engine_repair as repair  # noqa: E402
from core import nas_library as nas  # noqa: E402
from core import staff_access as sa  # noqa: E402
from core import universal_my_work as umw  # noqa: E402
from core import work_items as wi  # noqa: E402
from core.staff_access import (  # noqa: E402
    ATRIUM_GRANTS,
    ATRIUM_HELD_BACK,
    ATRIUM_SUBMIT,
    ROLE_ATRIUM_FINANCIAL_CONTROLLER,
    ROLE_CONTENT_CREATOR,
    ROLE_CREATIVE_DIRECTOR,
)

SOURCE = "Matt relay 29 Sep 11:14 WITA"

HAIKAL_FAIL = (
    f"[{SOURCE}] "
    "(1) everyone except Haikal and Misa sees only a few brands in Content Engine "
    "instead of all appropriate brands; "
    "(2) wants active Content Plans for each brand directly in the Content Engine; "
    "(3) add Drone as a content type."
)

ZAYEN_FAIL = (
    f"[{SOURCE}] "
    "(1) General Ledger becomes blank when opened; "
    "(2) could not approve a journal entry; says his access/roles need fixing. "
    "evidence_pending: zayen-screenshots-via-matt"
)

# FC may approve/reject journals prepared by someone else. Post stays held back.
FC_APPROVE_PERM = (
    "PERM-ATRIUM-JOURNAL-APPROVE",
    "atrium.journal.approve",
    "atrium.journal",
    "approve",
    "POST /api/journals/:id/approve (and reject/return). SoD: not own prepare.",
)
FC_REJECT_PERM = (
    "PERM-ATRIUM-JOURNAL-REJECT",
    "atrium.journal.reject",
    "atrium.journal",
    "reject",
    "POST /api/journals/:id/reject — return VALIDATED journal to DRAFT. SoD applies.",
)


def _ts() -> str:
    return wi.now_utc_iso()


def _ensure_permission(
    conn: sqlite3.Connection,
    perm_id: str,
    code: str,
    resource: str,
    action: str,
    desc: str,
    ts: str,
) -> None:
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
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (perm_id, code, resource, action, desc, ts, ts),
    )


def _grant(conn: sqlite3.Connection, role_id: str, code: str, ts: str) -> None:
    row = conn.execute(
        "SELECT permission_id FROM org_permissions WHERE code=?",
        (code,),
    ).fetchone()
    if not row:
        raise RuntimeError(f"permission missing: {code}")
    conn.execute(
        """
        INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES (?, ?, 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET
          effect='ALLOW', updated_at=excluded.updated_at
        """,
        (role_id, row[0], ts, ts),
    )


def grant_fc_approve(conn: sqlite3.Connection) -> dict:
    """Grant approve + reject to Financial Controller only. Post stays deleted."""
    ts = _ts()
    for perm in (FC_APPROVE_PERM, FC_REJECT_PERM):
        _ensure_permission(conn, *perm, ts)
        _grant(conn, ROLE_ATRIUM_FINANCIAL_CONTROLLER, perm[1], ts)
    # Keep post held back for FC.
    post_id = "PERM-ATRIUM-JOURNAL-POST"
    conn.execute(
        "DELETE FROM org_role_permissions WHERE role_id=? AND permission_id=?",
        (ROLE_ATRIUM_FINANCIAL_CONTROLLER, post_id),
    )
    # Ensure base ATRIUM_GRANTS remain.
    for _pid, code, *_rest in ATRIUM_GRANTS:
        _grant(conn, ROLE_ATRIUM_FINANCIAL_CONTROLLER, code, ts)
    _grant(conn, ROLE_ATRIUM_FINANCIAL_CONTROLLER, ATRIUM_SUBMIT, ts)
    return {
        "role": ROLE_ATRIUM_FINANCIAL_CONTROLLER,
        "granted": [FC_APPROVE_PERM[1], FC_REJECT_PERM[1]],
        "held_post": True,
    }


def ensure_content_team_brand_scope(conn: sqlite3.Connection) -> dict:
    """Creative Director + Content Creator seats get all active content brands.

    Content Creator assignments carry SCOPE-GGV-CONTENT (team role, not brand
    targets). Brief: when assignment has no brand-specific scope, Content team
    role covers all active content brands. Attach CONTENT-ALL by role.
    """
    base = repair.ensure_content_all_brands_scope(conn)
    scope_id = nas.CONTENT_ALL_BRANDS_SCOPE
    stamp = _ts()
    attached: list[str] = []
    for role_id in (ROLE_CREATIVE_DIRECTOR, ROLE_CONTENT_CREATOR):
        rows = conn.execute(
            """
            SELECT a.assignment_id, a.start_at
            FROM org_assignments a
            JOIN org_positions p ON p.position_id = a.position_id
            WHERE p.role_id = ?
              AND a.status = 'ACTIVE'
              AND a.end_at IS NULL
            ORDER BY a.assignment_id
            """,
            (role_id,),
        ).fetchall()
        for row in rows:
            aid = row["assignment_id"]
            existing = conn.execute(
                """
                SELECT start_at, status, end_at FROM org_assignment_scopes
                WHERE assignment_id=? AND scope_id=?
                ORDER BY start_at DESC LIMIT 1
                """,
                (aid, scope_id),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO org_assignment_scopes (
                      assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
                    ) VALUES (?, ?, ?, NULL, 'ACTIVE', ?, ?)
                    """,
                    (aid, scope_id, row["start_at"] or stamp, stamp, stamp),
                )
                attached.append(aid)
                continue
            if str(existing["status"] or "") != "ACTIVE" or existing["end_at"]:
                conn.execute(
                    """
                    UPDATE org_assignment_scopes
                    SET status='ACTIVE', end_at=NULL, updated_at=?
                    WHERE assignment_id=? AND scope_id=? AND start_at=?
                    """,
                    (stamp, aid, scope_id, existing["start_at"]),
                )
                attached.append(aid)
    return {
        "ok": True,
        "scope_id": scope_id,
        "roles": [ROLE_CREATIVE_DIRECTOR, ROLE_CONTENT_CREATOR],
        "attached_or_refreshed": attached,
        "content_all_base": base,
    }


def brand_scope_table(conn: sqlite3.Connection) -> list[dict]:
    people = [
        ("PERS-HAIKAL", "Haikal", "Creative Director"),
        ("PERS-MISA", "Misa", "Creative Director"),
        ("PERS-ZARAH", "Zarah", "Creative Director"),
        ("PERS-FRAIL", "Frail", "Creative Director"),
        ("PERS-YUDI", "Yudi", "Content Creator"),
        ("PERS-GERY", "Gery", "Content Creator"),
        ("PERS-ALAM", "Alam", "Content Creator"),
        ("PERS-TJ", "TJ", "Content Creator"),
        ("PERS-NATA", "Nata", "Content Creator"),
        ("PERS-RAPP", "Rapp", "Content Creator"),
    ]
    out = []
    for pid, name, seat in people:
        scopes = [
            str(r[0])
            for r in conn.execute(
                """
                SELECT DISTINCT s.scope_id
                FROM org_assignment_scopes s
                JOIN org_assignments a ON a.assignment_id = s.assignment_id
                WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
                  AND s.status='ACTIVE' AND s.end_at IS NULL
                ORDER BY s.scope_id
                """,
                (pid,),
            ).fetchall()
            if r[0]
        ]
        brands = nas.brands_for_scopes(scopes)
        auth = [b["slug"] for b in repair.authorised_brands(conn, scopes)]
        out.append(
            {
                "person_id": pid,
                "name": name,
                "seat": seat,
                "scopes": scopes,
                "brands": brands,
                "authorised": auth,
                "brand_count": len(auth),
            }
        )
    return out


def _attach_text_evidence(conn, work_item_id: str, person_id: str, text: str) -> None:
    """Minimal note evidence so mark_done can proceed for Matt-relay FAILs."""
    umw.store_evidence_file(
        work_item_id,
        filename="matt-relay-fail.txt",
        content=text.encode("utf-8"),
        uploaded_by_person_id=person_id,
        content_type="text/plain",
        note=text[:500],
        conn=conn,
        commit=False,
    )


def record_fails(conn: sqlite3.Connection) -> dict:
    """Set employee FAIL on live commissioning items; create ENGINEERING repairs."""
    results = {"haikal": [], "zayen": [], "repairs": []}

    haikal_rows = conn.execute(
        """
        SELECT work_item_id, commissioning_capability_id, status, human_result
        FROM core_work_items
        WHERE origin='commissioning' AND owner_person_id='PERS-HAIKAL'
          AND status NOT IN ('CANCELLED','VERIFIED')
        ORDER BY commissioning_capability_id
        """
    ).fetchall()
    for row in haikal_rows:
        wid = row["work_item_id"]
        if row["human_result"] == "FAIL" and row["status"] == "COMPLETED":
            repair = umw._find_linked_repair(conn, wid)
            results["haikal"].append({"work_item_id": wid, "already": True, "repair": (repair or {}).get("work_item_id")})
            continue
        if row["status"] == "OPEN":
            wi.start_work_item(wid, verified_person_id="PERS-HAIKAL", conn=conn, commit=False)
        _attach_text_evidence(conn, wid, "PERS-HAIKAL", HAIKAL_FAIL)
        out = umw.mark_done(
            wid,
            verified_person_id="PERS-HAIKAL",
            human_result="FAIL",
            human_comment=HAIKAL_FAIL,
            outcome="Employee FAIL — Matt relay 29 Sep",
            conn=conn,
            commit=False,
        )
        repair = out.get("repair_item") or {}
        results["haikal"].append(
            {
                "work_item_id": wid,
                "capability": row["commissioning_capability_id"],
                "repair": repair.get("work_item_id"),
            }
        )
        if repair.get("work_item_id"):
            results["repairs"].append(repair["work_item_id"])

    zayen_rows = conn.execute(
        """
        SELECT work_item_id, commissioning_capability_id, status, human_result
        FROM core_work_items
        WHERE origin='commissioning' AND owner_person_id='PERS-ZAYEN'
          AND status NOT IN ('CANCELLED','VERIFIED')
        ORDER BY commissioning_capability_id
        """
    ).fetchall()
    for row in zayen_rows:
        wid = row["work_item_id"]
        if row["human_result"] == "FAIL" and row["status"] == "COMPLETED":
            repair = umw._find_linked_repair(conn, wid)
            results["zayen"].append({"work_item_id": wid, "already": True, "repair": (repair or {}).get("work_item_id")})
            continue
        if row["status"] == "OPEN":
            wi.start_work_item(wid, verified_person_id="PERS-ZAYEN", conn=conn, commit=False)
        _attach_text_evidence(conn, wid, "PERS-ZAYEN", ZAYEN_FAIL)
        out = umw.mark_done(
            wid,
            verified_person_id="PERS-ZAYEN",
            human_result="FAIL",
            human_comment=ZAYEN_FAIL,
            outcome="Employee FAIL — Matt relay 29 Sep",
            conn=conn,
            commit=False,
        )
        repair = out.get("repair_item") or {}
        results["zayen"].append(
            {
                "work_item_id": wid,
                "capability": row["commissioning_capability_id"],
                "repair": repair.get("work_item_id"),
            }
        )
        if repair.get("work_item_id"):
            results["repairs"].append(repair["work_item_id"])
    return results


def run(*, db_path: Path | None = None, record: bool = True) -> dict:
    conn = wi.db_connect(db_path) if db_path else wi.db_connect()
    before = brand_scope_table(conn)
    scope = ensure_content_team_brand_scope(conn)
    fc = grant_fc_approve(conn)
    after = brand_scope_table(conn)
    fails = record_fails(conn) if record else {"skipped": True}
    conn.commit()
    return {
        "ok": True,
        "source": SOURCE,
        "brand_scope_before": before,
        "brand_scope_after": after,
        "content_team_scope": scope,
        "fc_approve": fc,
        "fails": fails,
        "staff_ready": False,
        "human_commissioned": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--db", type=Path, default=None)
    ap.add_argument("--no-record-fails", action="store_true")
    args = ap.parse_args()
    out = run(db_path=args.db, record=not args.no_record_fails)
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        print("HUMFIX-1 migration ok")
        print("repairs", len((out.get("fails") or {}).get("repairs") or []))
        for row in out["brand_scope_after"]:
            print(f"  {row['name']}: {row['brand_count']} brands {row['authorised']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
