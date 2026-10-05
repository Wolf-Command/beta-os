#!/usr/bin/env python3
"""BZG P2P explicit permission matrix + document segregation (Beta).

Replaces copy-from-work.complete grants. Segregation: PO creator and nota
recorder cannot mark the same document AP-ready or ready-to-pay.
"""
from __future__ import annotations

import sqlite3
from typing import Any

PACK = "BZG-P2P-GRANT-REPAIR-1"

# Explicit role matrix — never copy from work.complete.
P2P_PERMISSION_MATRIX: dict[str, tuple[str, ...]] = {
    "bzg.po.create": (
        "ROLE-BZG-FB-OPS-LEAD",
        "ROLE-BZG-HFB",
        "ROLE-BZG-CAPTAIN",
        "ROLE-MATT",
        "ROLE-OWNER",
    ),
    "bzg.bill.capture": (
        "ROLE-BZG-FB-OPS-LEAD",
        "ROLE-BZG-HFB",
    ),
    "bzg.match.run": (
        "ROLE-BZG-FB-OPS-LEAD",
        "ROLE-BZG-HFB",
        "ROLE-BZG-FINANCIAL-CONTROLLER",
    ),
    "bzg.match.accept": (
        "ROLE-BZG-FB-OPS-LEAD",
        "ROLE-BZG-FINANCIAL-CONTROLLER",
    ),
    "bzg.ap.view": (
        "ROLE-BZG-FB-OPS-LEAD",
        "ROLE-BZG-HFB",
        "ROLE-BZG-FINANCIAL-CONTROLLER",
        "ROLE-MATT",
        "ROLE-OWNER",
    ),
    "bzg.ap.mark_ready": (
        "ROLE-BZG-FB-OPS-LEAD",
        "ROLE-BZG-FINANCIAL-CONTROLLER",
    ),
    "bzg.pay.list_ready": (
        "ROLE-BZG-FB-OPS-LEAD",
        "ROLE-BZG-FINANCIAL-CONTROLLER",
        "ROLE-MATT",
        "ROLE-OWNER",
    ),
    "bzg.pay.mark_ready": (
        "ROLE-BZG-FB-OPS-LEAD",
        "ROLE-BZG-FINANCIAL-CONTROLLER",
    ),
}

P2P_PERMISSION_CODES: tuple[str, ...] = tuple(P2P_PERMISSION_MATRIX.keys())

# Live acceptance probes — GGV content must DENY on BZG outlets.
GGV_CONTENT_DENY_PERSONS: tuple[str, ...] = (
    "PERS-HAIKAL",
    "PERS-MISA",
    "PERS-YUDI",
)

GGV_CONTENT_DENY_OUTLETS: tuple[str, ...] = (
    "BZG-UMA",
    "BZG-RAIN",
    "OU-BZG-RAIN-POOL",
)

GGV_CONTENT_DENY_PERMISSIONS: tuple[str, ...] = (
    "bzg.po.create",
    "bzg.bill.capture",
    "bzg.ap.mark_ready",
    "bzg.pay.list_ready",
    "bzg.pay.mark_ready",
)

CHAIN_DENY_LIVE_PERSONS: tuple[str, ...] = (
    "PERS-IZA",
    "PERS-HARIYANTO",
)

CHAIN_DENY_PERMISSIONS: tuple[str, ...] = (
    "bzg.po.create",
    "bzg.bill.capture",
    "bzg.ap.mark_ready",
    "bzg.pay.mark_ready",
)


def p2p_pay_ready_segregation_deny(
    person_id: str,
    bill_id: str,
    conn: sqlite3.Connection,
    *,
    stage: str = "ap",
) -> str | None:
    """Return segregation deny code if person must not mark at this stage.

    stage: ``ap`` for mark_ap_ready, ``pay`` for mark_ready_to_pay.
    """
    pid = (person_id or "").strip()
    bid = (bill_id or "").strip()
    if not pid or not bid:
        return None
    bill = conn.execute(
        "SELECT po_id, capturer_person_id FROM bzg_ops_supplier_bills WHERE bill_id=?",
        (bid,),
    ).fetchone()
    if not bill:
        return None
    if str(bill["capturer_person_id"]) == pid:
        return "nota_recorder_cannot_mark_pay_ready"
    po = conn.execute(
        "SELECT created_by_person_id FROM bzg_ops_purchase_orders WHERE po_id=?",
        (bill["po_id"],),
    ).fetchone()
    if po and str(po["created_by_person_id"]) == pid:
        return "po_creator_cannot_mark_pay_ready"
    st = (stage or "ap").strip().lower()
    if st == "pay":
        ap_row = conn.execute(
            "SELECT marked_by_person_id FROM bzg_ops_ap_ready WHERE bill_id=?",
            (bid,),
        ).fetchone()
        if ap_row and str(ap_row["marked_by_person_id"]) == pid:
            return "same_person_cannot_mark_both_stages"
    elif st == "ap":
        try:
            rtp_row = conn.execute(
                "SELECT marked_by_person_id FROM bzg_ops_ready_to_pay WHERE bill_id=?",
                (bid,),
            ).fetchone()
        except sqlite3.OperationalError:
            rtp_row = None
        if rtp_row and str(rtp_row["marked_by_person_id"]) == pid:
            return "same_person_cannot_mark_both_stages"
    return None


def revoke_all_p2p_grants(conn: sqlite3.Connection, ts: str) -> list[str]:
    """Remove ALLOW grants for all P2P permission codes from every role."""
    revoked: list[str] = []
    for code in P2P_PERMISSION_CODES:
        perm = conn.execute(
            "SELECT permission_id FROM org_permissions WHERE code=? AND status='ACTIVE'",
            (code,),
        ).fetchone()
        if not perm:
            continue
        perm_id = str(perm["permission_id"])
        rows = conn.execute(
            """
            SELECT role_id FROM org_role_permissions
            WHERE permission_id=? AND effect='ALLOW'
            """,
            (perm_id,),
        ).fetchall()
        for row in rows:
            role_id = str(row["role_id"])
            conn.execute(
                """
                DELETE FROM org_role_permissions
                WHERE role_id=? AND permission_id=? AND effect='ALLOW'
                """,
                (role_id, perm_id),
            )
            revoked.append(f"{role_id}:{code}")
    return revoked


def apply_p2p_grant_matrix(conn: sqlite3.Connection, ts: str) -> dict[str, list[str]]:
    """Apply explicit P2P role matrix. Returns granted role_id per permission code."""
    granted: dict[str, list[str]] = {code: [] for code in P2P_PERMISSION_CODES}
    for code, roles in P2P_PERMISSION_MATRIX.items():
        perm = conn.execute(
            "SELECT permission_id FROM org_permissions WHERE code=? AND status='ACTIVE'",
            (code,),
        ).fetchone()
        if not perm:
            continue
        perm_id = str(perm["permission_id"])
        for role_id in roles:
            role = conn.execute(
                "SELECT role_id FROM org_roles WHERE role_id=?", (role_id,)
            ).fetchone()
            if not role:
                continue
            conn.execute(
                """
                INSERT INTO org_role_permissions (
                  role_id, permission_id, effect, created_at, updated_at
                ) VALUES (?, ?, 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET
                  effect='ALLOW', updated_at=excluded.updated_at
                """,
                (role_id, perm_id, ts, ts),
            )
            granted[code].append(role_id)
    return granted


def person_holds_full_chain(
    person_id: str,
    outlet_id: str,
    conn: sqlite3.Connection,
    *,
    rbac_can: Any,
    outlet_target: Any,
) -> bool:
    """True when person ALLOWs create + capture + pay-ready on the outlet target."""
    pid = (person_id or "").strip()
    oid = (outlet_id or "").strip()
    if not pid or not oid:
        return False
    target = outlet_target(oid, conn)
    needed = (
        "bzg.po.create",
        "bzg.bill.capture",
        "bzg.ap.mark_ready",
        "bzg.pay.mark_ready",
    )
    return all(rbac_can(pid, code, target, conn=conn) for code in needed)
