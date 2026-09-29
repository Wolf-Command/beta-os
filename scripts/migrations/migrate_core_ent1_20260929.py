#!/usr/bin/env python3
"""CORE-ENT-1 — BZG Financial Controller (Zayen) + External Accountant shells.

Decision served: Matt-ordered Owner sprint Finance Core (2026-09-29);
Zayen BZG FC seating OWNER_AUTHORIZED. Inventory:
state/finance-core-sprint/INVENTORY-20260929.json.

Creates ROLE/POS/SCOPE-BZG finance + ASG-ZAYEN-BZG-FC-1 ACTIVE.
Creates unseated External/Tax Accountant role+position+scope shells for
AMG and BZG (GGV shell already exists). Does not invent people.
Does not grant GGV finance to Zayen. Does not flip staff_ready /
human_commissioned. Beta catalog only. No prod.
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
ATRIUM_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")
OU_DOC = ROOT / "state" / "finance-core-sprint" / "BZG-OPERATING-UNITS.json"
MIGRATION_ID = "core_ent1_20260929"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")

ZAYEN = "PERS-ZAYEN"
ZAYEN_EMAIL = "laluzayen@gmail.com"

ENTITY_AMG = "ENT-AMG"
ENTITY_BZG = "ENT-BZG"
ENTITY_GGV = "ENT-GGV"

ROLE_BZG_FC = "ROLE-BZG-FINANCIAL-CONTROLLER"
POS_BZG_FC = "POS-BZG-FINANCIAL-CONTROLLER-1"
ASG_BZG_FC = "ASG-ZAYEN-BZG-FC-1"
SCOPE_BZG_FINANCE = "SCOPE-BZG-FINANCE"
START = "2026-09-29T00:00:00+08:00"

# Preserve AMG seats (do not touch).
PRESERVE_ASG = (
    "ASG-ZAYEN-FC-1",
    "ASG-ZAYEN-AR-1",
    "ASG-ZENITALFATHAN-AP-1",
)

# External / Tax Accountant shells — unseated.
EXT_SHELLS = (
    {
        "role_id": "ROLE-AMG-EXTERNAL-ACCOUNTANT",
        "role_label": "AMG external / tax accountant",
        "position_id": "POS-AMG-EXT-ACCT",
        "entity_id": ENTITY_AMG,
        "scope_id": "SCOPE-AMG-FINANCE",
        "scope_type": "structural",
        "scope_label": "Atrium Finance only",
    },
    {
        "role_id": "ROLE-BZG-EXTERNAL-ACCOUNTANT",
        "role_label": "BZG external / tax accountant",
        "position_id": "POS-BZG-EXT-ACCT",
        "entity_id": ENTITY_BZG,
        "scope_id": SCOPE_BZG_FINANCE,
        "scope_type": "structural",
        "scope_label": "BZG Finance only",
    },
    {
        # Already exists — reaffirm pattern; never invent a person seat.
        "role_id": "ROLE-GGV-EXTERNAL-ACCOUNTANT",
        "role_label": "GGV external accountant",
        "position_id": "POS-GGV-EXT-ACCT",
        "entity_id": ENTITY_GGV,
        "scope_id": "SCOPE-GGV-FINANCE",
        "scope_type": "structural",
        "scope_label": "GGV Finance only",
    },
)

ACCOUNTANT_PERM_CODES = (
    "finance.nota.read",
    "finance.nota.review",
    "finance.invoice.read",
    "finance.evidence.export",
    "vendor.read",
)

ACCOUNTANT_DENY_CODES = (
    "payment.approve",
    "payment.execute",
    "vendor.bank.change",
    "finance.policy.admin",
    "atrium.journal.approve",
    "atrium.journal.post",
    "progress.read",
    "organisation.role.read",
    "organisation.person.read",
)

# BZG FC mirrors AMG FC capability codes — entity scope isolates authority.
BZG_FC_PERM_CODES = (
    "atrium.board.read",
    "atrium.coa.read",
    "atrium.ledger.read",
    "atrium.report.read",
    "atrium.journal.draft",
    "atrium.journal.approve",
    "atrium.journal.reject",
    "atrium.journal.post",
    "approval.request",
    "evidence.record.read",
    "evidence.record.submit",
    "work.read",
    "work.update",
    "work.complete",
    # Shared read surface for entity-generic finance desks later.
    "finance.nota.read",
    "finance.invoice.read",
    "finance.evidence.export",
    "vendor.read",
)

BZG_FC_DENY = (
    "payment.approve",
    "payment.execute",
    "vendor.bank.change",
    "finance.policy.admin",
    "progress.read",
    "organisation.role.read",
    "organisation.person.read",
    "governance.exception.authorise",
    "content.plan.read",
    "amg.day.operator",
    "core.operator",
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


def _perm_id(conn: sqlite3.Connection, code: str) -> str:
    row = conn.execute(
        "SELECT permission_id FROM org_permissions WHERE code=? AND status='ACTIVE'",
        (code,),
    ).fetchone()
    if not row:
        raise RuntimeError(f"REFUSE: missing ACTIVE permission {code}")
    return str(row[0])


def _grant(conn: sqlite3.Connection, role_id: str, code: str, ts: str) -> None:
    pid = _perm_id(conn, code)
    conn.execute(
        """
        INSERT INTO org_role_permissions (
          role_id, permission_id, effect, created_at, updated_at
        ) VALUES (?, ?, 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET
          effect='ALLOW', updated_at=excluded.updated_at
        """,
        (role_id, pid, ts, ts),
    )


def _strip_denies(conn: sqlite3.Connection, role_id: str, codes: tuple[str, ...]) -> None:
    for code in codes:
        row = conn.execute(
            "SELECT permission_id FROM org_permissions WHERE code=?",
            (code,),
        ).fetchone()
        if not row:
            continue
        conn.execute(
            "DELETE FROM org_role_permissions WHERE role_id=? AND permission_id=?",
            (role_id, row[0]),
        )


def _assert_role_denies(conn: sqlite3.Connection, role_id: str, codes: tuple[str, ...]) -> None:
    rows = conn.execute(
        """
        SELECT p.code FROM org_role_permissions rp
        JOIN org_permissions p ON p.permission_id = rp.permission_id
        WHERE rp.role_id=? AND rp.effect='ALLOW'
        """,
        (role_id,),
    ).fetchall()
    allowed = {r[0] for r in rows}
    leaked = [c for c in codes if c in allowed]
    if leaked:
        raise RuntimeError(f"REFUSE: {role_id} must not have {leaked}")


def _ensure_scope(
    conn: sqlite3.Connection,
    *,
    scope_id: str,
    scope_type: str,
    display_name: str,
    entity_id: str,
    ts: str,
) -> None:
    conn.execute(
        """
        INSERT INTO org_scopes (
          scope_id, scope_type, display_name, status, created_at, updated_at
        ) VALUES (?, ?, ?, 'ACTIVE', ?, ?)
        ON CONFLICT(scope_id) DO UPDATE SET
          scope_type=excluded.scope_type,
          display_name=excluded.display_name,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (scope_id, scope_type, display_name, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES (?, 'entity', ?, ?)
        ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
        """,
        (scope_id, entity_id, ts),
    )


def _seed_bzg_fc(conn: sqlite3.Connection, ts: str) -> None:
    z = conn.execute(
        "SELECT person_id FROM org_persons WHERE person_id=?",
        (ZAYEN,),
    ).fetchone()
    if not z:
        raise RuntimeError("REFUSE: PERS-ZAYEN missing — do not invent")
    email = conn.execute(
        """
        SELECT identifier FROM org_auth_identities
        WHERE person_id=? AND provider='email' AND status='ACTIVE'
        """,
        (ZAYEN,),
    ).fetchone()
    if not email or str(email[0]).lower() != ZAYEN_EMAIL.lower():
        raise RuntimeError("REFUSE: Zayen email mismatch — do not invent")

    for asg in PRESERVE_ASG:
        row = conn.execute(
            """
            SELECT status, end_at FROM org_assignments WHERE assignment_id=?
            """,
            (asg,),
        ).fetchone()
        if asg.startswith("ASG-ZAYEN") and (not row or row[0] != "ACTIVE" or row[1]):
            if asg in ("ASG-ZAYEN-FC-1", "ASG-ZAYEN-AR-1"):
                raise RuntimeError(f"REFUSE: preserve {asg} ACTIVE")

    _ensure_scope(
        conn,
        scope_id=SCOPE_BZG_FINANCE,
        scope_type="structural",
        display_name="BZG Finance only",
        entity_id=ENTITY_BZG,
        ts=ts,
    )

    conn.execute(
        """
        INSERT INTO org_roles (
          role_id, display_name, department_id, role_type, status, created_at, updated_at
        ) VALUES (?, 'BZG Financial Controller', NULL, 'OPERATING', 'ACTIVE', ?, ?)
        ON CONFLICT(role_id) DO UPDATE SET
          display_name=excluded.display_name,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (ROLE_BZG_FC, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_positions (
          position_id, role_id, entity_id, location_id, brand_id, department_id,
          position_label, status, fte, created_at, updated_at
        ) VALUES (?, ?, ?, NULL, NULL, NULL, 'BZG Financial Controller', 'ACTIVE', 1, ?, ?)
        ON CONFLICT(position_id) DO UPDATE SET
          role_id=excluded.role_id,
          entity_id=excluded.entity_id,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (POS_BZG_FC, ROLE_BZG_FC, ENTITY_BZG, ts, ts),
    )

    for code in BZG_FC_PERM_CODES:
        _grant(conn, ROLE_BZG_FC, code, ts)
    _strip_denies(conn, ROLE_BZG_FC, BZG_FC_DENY)
    _assert_role_denies(conn, ROLE_BZG_FC, BZG_FC_DENY)

    existing = conn.execute(
        "SELECT status, end_at, person_id FROM org_assignments WHERE assignment_id=?",
        (ASG_BZG_FC,),
    ).fetchone()
    if existing and str(existing[2]) != ZAYEN:
        raise RuntimeError(f"REFUSE: {ASG_BZG_FC} bound to {existing[2]}")
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, status, is_primary,
          start_at, end_at, created_at, updated_at
        ) VALUES (?, ?, ?, 'ACTIVE', 0, ?, NULL, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET
          person_id=excluded.person_id,
          position_id=excluded.position_id,
          status='ACTIVE',
          end_at=NULL,
          updated_at=excluded.updated_at
        """,
        (ASG_BZG_FC, ZAYEN, POS_BZG_FC, START, ts, ts),
    )
    upsert_assignment_scope(conn, ASG_BZG_FC, SCOPE_BZG_FINANCE, START, ts)


def _seed_ext_accountant_shells(conn: sqlite3.Connection, ts: str) -> list[str]:
    seeded: list[str] = []
    for shell in EXT_SHELLS:
        role_id = shell["role_id"]
        _ensure_scope(
            conn,
            scope_id=shell["scope_id"],
            scope_type=shell["scope_type"],
            display_name=shell["scope_label"],
            entity_id=shell["entity_id"],
            ts=ts,
        )
        conn.execute(
            """
            INSERT INTO org_roles (
              role_id, display_name, department_id, role_type, status, created_at, updated_at
            ) VALUES (?, ?, NULL, 'EXTERNAL', 'ACTIVE', ?, ?)
            ON CONFLICT(role_id) DO UPDATE SET
              display_name=excluded.display_name,
              role_type='EXTERNAL',
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (role_id, shell["role_label"], ts, ts),
        )
        conn.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, location_id, brand_id, department_id,
              position_label, status, fte, created_at, updated_at
            ) VALUES (?, ?, ?, NULL, NULL, NULL, ?, 'ACTIVE', 1, ?, ?)
            ON CONFLICT(position_id) DO UPDATE SET
              role_id=excluded.role_id,
              entity_id=excluded.entity_id,
              position_label=excluded.position_label,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (
                shell["position_id"],
                role_id,
                shell["entity_id"],
                shell["role_label"],
                ts,
                ts,
            ),
        )
        for code in ACCOUNTANT_PERM_CODES:
            _grant(conn, role_id, code, ts)
        _strip_denies(conn, role_id, ACCOUNTANT_DENY_CODES)
        _assert_role_denies(conn, role_id, ACCOUNTANT_DENY_CODES)
        # No person assignment — prove unseated.
        seated = conn.execute(
            """
            SELECT a.assignment_id, a.person_id
            FROM org_assignments a
            WHERE a.position_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
            """,
            (shell["position_id"],),
        ).fetchall()
        if seated:
            raise RuntimeError(
                f"REFUSE: External Accountant {shell['position_id']} must stay unseated; found {seated}"
            )
        seeded.append(role_id)
    return seeded


def _write_operating_units_doc() -> None:
    OU_DOC.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "wolf.bzg.operating-units.v1",
        "as_of_wita": now_iso(),
        "pack": "CORE-ENT-1",
        "rule": "measurable operating unit under parent brand — not a second brand_id",
        "legal_entity_id": ENTITY_BZG,
        "units": [
            {
                "operating_unit_id": "OU-BZG-RAIN-POOL",
                "display_name": "Pool Bar",
                "parent_brand_id": "BZG-RAIN",
                "parent_brand_name": "Blu Zone Rainforest Restaurant & Bar",
                "status": "HOOK",
                "note": (
                    "Pool Bar is folded under Rainforest in org_brands today. "
                    "This operating_unit_id is the finance measurability hook. "
                    "Deep outlet registry left to sibling pack."
                ),
            }
        ],
        "sidecar_column": "journal_lines.operating_unit_id (nullable, additive)",
        "sibling_pack": "BZG multi-outlet registry",
    }
    OU_DOC.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _ensure_sidecar_entity_columns() -> dict:
    """Additive legal_entity_id on Beta atrium.sqlite (Python path; sidecar also migrates)."""
    if not ATRIUM_DB.is_file():
        return {"ok": False, "reason": "atrium.sqlite missing"}
    tables = [
        "accounts",
        "departments",
        "journal_headers",
        "journal_lines",
        "revenue_transactions",
        "spending_transactions",
        "mapping_config",
        "system_settings",
        "report_config",
        "ar_settlements",
        "ap_payments",
        "inventory_movements",
        "inventory_requisitions",
        "inventory_purchase_orders",
        "inventory_receipts",
        "inventory_adjustments",
        "inventory_count_sessions",
        "inventory_items",
        "inventory_categories",
        "inventory_storerooms",
        "owner_pool_units",
        "owner_pool_batches",
        "owner_pool_rule_config",
        "owner_pool_rule_history",
        "service_charge_employees",
        "service_charge_collections",
        "service_charge_cycles",
        "tax_rules",
        "tax_obligations",
        "tax_closed_periods",
        "journal_evidence",
        "journal_workflow_audit",
        "historical_import_batches",
    ]
    conn = sqlite3.connect(str(ATRIUM_DB))
    try:
        added = []
        for table in tables:
            exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if not exists:
                continue
            cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if "legal_entity_id" not in cols:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN legal_entity_id TEXT NOT NULL DEFAULT 'ENT-AMG'"
                )
                added.append(table)
        jl_cols = {r[1] for r in conn.execute("PRAGMA table_info(journal_lines)").fetchall()}
        if "operating_unit_id" not in jl_cols:
            conn.execute("ALTER TABLE journal_lines ADD COLUMN operating_unit_id TEXT")
            added.append("journal_lines.operating_unit_id")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operating_unit_registry (
              operating_unit_id TEXT PRIMARY KEY,
              legal_entity_id TEXT NOT NULL,
              parent_brand_id TEXT,
              display_name TEXT NOT NULL,
              status TEXT NOT NULL,
              note TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL
            )
            """
        )
        ts = now_iso()
        conn.execute(
            """
            INSERT INTO operating_unit_registry (
              operating_unit_id, legal_entity_id, parent_brand_id, display_name, status, note, created_at
            ) VALUES (?, 'ENT-BZG', 'BZG-RAIN', 'Pool Bar', 'HOOK', ?, ?)
            ON CONFLICT(operating_unit_id) DO UPDATE SET
              display_name=excluded.display_name,
              status=excluded.status,
              note=excluded.note
            """,
            (
                "OU-BZG-RAIN-POOL",
                "Measurable under BZG-RAIN. Not a second brand_id. CORE-ENT-1 hook.",
                ts,
            ),
        )
        conn.commit()
        present = 0
        for table in tables:
            exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if not exists:
                continue
            cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if "legal_entity_id" in cols:
                present += 1
        return {"ok": True, "added": added, "legal_entity_tables": present}
    finally:
        conn.close()


def main() -> int:
    bad = _refuse_path(DB)
    if bad:
        print(f"REFUSE: {bad} in {DB}", file=sys.stderr)
        return 2

    ts = now_iso()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"pre-core-ent1-{stamp()}.sqlite"
    shutil.copy2(DB, dest)
    print(f"BACKUP={dest}")
    print(f"SHA256={_sha256(dest)}")

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        _seed_bzg_fc(conn, ts)
        shells = _seed_ext_accountant_shells(conn, ts)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    _write_operating_units_doc()
    sidecar = _ensure_sidecar_entity_columns()

    # Prove Zayen has zero GGV finance assignment
    conn = sqlite3.connect(str(DB))
    try:
        ggv = conn.execute(
            """
            SELECT a.assignment_id, pos.role_id
            FROM org_assignments a
            JOIN org_positions pos ON pos.position_id=a.position_id
            WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
              AND (
                pos.entity_id='ENT-GGV'
                OR pos.role_id LIKE '%GGV%FINANCE%'
                OR pos.role_id='ROLE-GGV-EXTERNAL-ACCOUNTANT'
                OR pos.role_id='ROLE-GGV-FINANCE-OPERATOR'
              )
            """,
            (ZAYEN,),
        ).fetchall()
        if ggv:
            raise RuntimeError(f"REFUSE: Zayen has GGV finance seat {ggv}")
        bzg = conn.execute(
            """
            SELECT assignment_id, status FROM org_assignments
            WHERE assignment_id=? AND person_id=? AND status='ACTIVE' AND end_at IS NULL
            """,
            (ASG_BZG_FC, ZAYEN),
        ).fetchone()
        if not bzg:
            raise RuntimeError("REFUSE: ASG-ZAYEN-BZG-FC-1 not ACTIVE")
    finally:
        conn.close()

    print(f"MIGRATION={MIGRATION_ID}")
    print(f"ASG_BZG_FC={ASG_BZG_FC}")
    print(f"EXT_SHELLS={','.join(shells)}")
    print(f"OU_DOC={OU_DOC}")
    print(f"SIDECAR={json.dumps(sidecar)}")
    print("staff_ready=false")
    print("human_commissioned=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
