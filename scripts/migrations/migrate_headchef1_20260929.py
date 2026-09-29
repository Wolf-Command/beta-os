#!/usr/bin/env python3
"""HEADCHEF-1 — Hariyanto Head Chef + Maciej auth-only. Beta catalog only.

Decision served: 2026-09-29 PICK HEADCHEF-1 in ~/.openclaw/wolf-output/decisions.md.
Creates PERS-HARIYANTO, ROLE-BZG-HEAD-CHEF, POS/ASG, upgrades SCOPE-BZG-FB to
entity membership (current + future BZG brands, no outlet names in grants),
recipe.* permissions via role_permissions only, HELD commissioning WI,
PERS-MACIEJ auth-only (zero assignments). Does not activate the WI.
Does not mutate Cloudflare. Does not touch Production.
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
from core import recipe_builder as rb  # noqa: E402
from core import work_items as wi  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
BACKUP_DIR = ROOT / "catalog" / "backups"
MIGRATION_ID = "headchef1_20260929"
TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("wolf-system", "money.sqlite", "/Production", "8787")

HARI = "PERS-HARIYANTO"
HARI_AUTH = "AUTH-HARIYANTO-EMAIL"
HARI_EMAIL = "carolus.haryanto@gmail.com"
HARI_DISPLAY = "Hariyanto"
HARI_LEGAL = "Carolus Haryanto"

MACIEJ = "PERS-MACIEJ"
MACIEJ_AUTH = "AUTH-MACIEJ-EMAIL"
MACIEJ_EMAIL = "barefeet14@hotmail.com"
MACIEJ_DISPLAY = "Maciej"

ENTITY = "ENT-BZG"
DEPT = "DEPT-BZG-FB"
ROLE = "ROLE-BZG-HEAD-CHEF"
ROLE_DISPLAY = "Head Chef"
POS = "POS-BZG-HEAD-CHEF-1"
ASG = "ASG-HARIYANTO-HEAD-CHEF-1"
SCOPE_FB = "SCOPE-BZG-FB"
START = "2026-09-29T00:00:00+08:00"
COMM_CAP = "COMM-HARIYANTO-RECIPE-BUILDER"
ROUTING_HELD_CF = "HELD_UNTIL_CF_ACCESS"

GRANT_CODES: tuple[tuple[str, str, str, str, str], ...] = (
    ("PERM-RECIPE-READ", "recipe.read", "recipe", "read", "Read Recipe Builder and BZG outlet recipes/menus in scope"),
    ("PERM-RECIPE-CREATE", "recipe.create", "recipe", "create", "Create recipes in Recipe Builder"),
    ("PERM-RECIPE-EDIT", "recipe.edit", "recipe", "edit", "Edit recipes, ingredients, subrecipes, yields, portions"),
    ("PERM-RECIPE-COST-READ", "recipe.cost.read", "recipe.cost", "read", "Read recipe costing, food cost %, margins"),
    ("PERM-INGREDIENT-READ", "ingredient.read", "ingredient", "read", "Read ingredients and purchase unit costs for costing"),
    ("PERM-MENU-PRICE-READ", "menu.price.read", "menu.price", "read", "Read menu selling prices (edit not granted)"),
    ("PERM-SUPPLIER-PRODUCT-READ", "supplier.product.read", "supplier.product", "read", "Read supplier/product info needed for costing"),
    ("PERM-RECIPE-EXCEPTIONS-READ", "recipe.exceptions.read", "recipe.exceptions", "read", "Read recipe completeness / missing-cost exceptions"),
)

# Existing codes also granted (must already be ACTIVE)
EXISTING_GRANTS = (
    "work.read",
    "work.create",
    "work.update",
    "work.complete",
    "evidence.record.read",
    "evidence.record.submit",
    "approval.request",
)

DENY_ASSERT = (
    "payment.approve",
    "payment.execute",
    "vendor.bank.change",
    "bzg.pr.payment_approve",
    "progress.read",
    "organisation.role.read",
    "organisation.person.read",
    "approval.decide",
    "venue.close.verify",
    "governance.exception.authorise",
    "finance.nota.read",
    "finance.invoice.read",
    "atrium.ledger.read",
    "atrium.journal.approve",
    "atrium.journal.post",
    "content.plan.approve",
    "work.verify",
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


def _ensure_person(
    conn: sqlite3.Connection,
    *,
    person_id: str,
    display_name: str,
    legal_name: str | None,
    auth_id: str,
    email: str,
    ts: str,
) -> None:
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
    existing = conn.execute(
        """
        SELECT person_id FROM org_auth_identities
        WHERE provider='email' AND lower(identifier)=?
        """,
        (email.lower(),),
    ).fetchone()
    if existing is None:
        conn.execute(
            """
            INSERT INTO org_auth_identities (
              auth_identity_id, person_id, provider, identifier, status,
              is_primary, created_at, updated_at
            ) VALUES (?, ?, 'email', ?, 'ACTIVE', 1, ?, ?)
            """,
            (auth_id, person_id, email.lower(), ts, ts),
        )
    elif str(existing[0]) != person_id:
        raise RuntimeError(
            f"REFUSE: {email.lower()} already bound to {existing[0]} (want {person_id})"
        )
    else:
        conn.execute(
            """
            UPDATE org_auth_identities
            SET status='ACTIVE', is_primary=1, updated_at=?
            WHERE provider='email' AND lower(identifier)=?
            """,
            (ts, email.lower()),
        )


def _upgrade_scope_fb(conn: sqlite3.Connection, ts: str) -> None:
    """SCOPE-BZG-FB → entity ENT-BZG so current + future BZG brands resolve.

    No outlet names in grants. resolve_effective_scope_context expands entity
    to org_brands under ENT-BZG automatically when brands are added later.
    """
    conn.execute(
        """
        INSERT INTO org_scopes (
          scope_id, scope_type, display_name, status, created_at, updated_at
        ) VALUES (?, 'entity', 'BZG F&B venues (all current and future under ENT-BZG)', 'ACTIVE', ?, ?)
        ON CONFLICT(scope_id) DO UPDATE SET
          scope_type='entity',
          display_name=excluded.display_name,
          status='ACTIVE',
          updated_at=excluded.updated_at
        """,
        (SCOPE_FB, ts, ts),
    )
    # Drop brand-hardcoded targets; keep only entity membership
    conn.execute(
        "DELETE FROM org_scope_targets WHERE scope_id=? AND target_type='brand'",
        (SCOPE_FB,),
    )
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES (?, 'entity', ?, ?)
        ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
        """,
        (SCOPE_FB, ENTITY, ts),
    )
    # Also keep department target for F&B clarity (no outlet names)
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES (?, 'department', ?, ?)
        ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
        """,
        (SCOPE_FB, DEPT, ts),
    )


def _grant_role_perms(conn: sqlite3.Connection, ts: str) -> list[str]:
    granted: list[str] = []
    for perm_id, code, resource, action, desc in GRANT_CODES:
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
        # If code already exists under another id, activate that row too
        conn.execute(
            """
            UPDATE org_permissions SET status='ACTIVE', updated_at=?
            WHERE code=? AND status!='ACTIVE'
            """,
            (ts, code),
        )
        row = conn.execute(
            "SELECT permission_id FROM org_permissions WHERE code=? AND status='ACTIVE'",
            (code,),
        ).fetchone()
        if not row:
            raise RuntimeError(f"missing permission {code}")
        conn.execute(
            """
            INSERT INTO org_role_permissions (
              role_id, permission_id, effect, created_at, updated_at
            ) VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET
              effect='ALLOW', updated_at=excluded.updated_at
            """,
            (ROLE, row[0], ts, ts),
        )
        granted.append(code)

    for code in EXISTING_GRANTS:
        row = conn.execute(
            "SELECT permission_id, status FROM org_permissions WHERE code=?",
            (code,),
        ).fetchone()
        if not row or row[1] != "ACTIVE":
            raise RuntimeError(f"REFUSE: missing ACTIVE permission {code}")
        conn.execute(
            """
            INSERT INTO org_role_permissions (
              role_id, permission_id, effect, created_at, updated_at
            ) VALUES (?, ?, 'ALLOW', ?, ?)
            ON CONFLICT(role_id, permission_id) DO UPDATE SET
              effect='ALLOW', updated_at=excluded.updated_at
            """,
            (ROLE, row[0], ts, ts),
        )
        granted.append(code)
    return granted


def _assert_denies(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT p.code FROM org_role_permissions rp
        JOIN org_permissions p ON p.permission_id = rp.permission_id
        WHERE rp.role_id=? AND rp.effect='ALLOW'
        """,
        (ROLE,),
    ).fetchall()
    allowed = {r[0] for r in rows}
    leaked = [c for c in DENY_ASSERT if c in allowed]
    if leaked:
        raise RuntimeError(f"REFUSE: Head Chef must not have {leaked}")


def _create_held_commissioning(conn: sqlite3.Connection, ts: str) -> str:
    existing = conn.execute(
        """
        SELECT work_item_id FROM core_work_items
        WHERE origin='commissioning'
          AND commissioning_capability_id=?
          AND owner_person_id=?
          AND status NOT IN ('CANCELLED')
        """,
        (COMM_CAP, HARI),
    ).fetchone()
    if existing:
        wid = str(existing[0])
        conn.execute(
            """
            UPDATE core_work_items
            SET routing_state=?,
                routing_reason=?,
                updated_at=?
            WHERE work_item_id=?
            """,
            (
                ROUTING_HELD_CF,
                "activate when Matt confirms carolus.haryanto@gmail.com is in Beta Cloudflare "
                "(confirmed 2026-09-29 — Peaches activates only after Person/AuthIdentity, "
                "Head Chef Assignment/Scope, real Recipe Builder and all server-side "
                "allow/deny checks pass)",
                ts,
                wid,
            ),
        )
        return wid

    instructions = (
        "Recipe Builder commissioning (HELD — do not start until Peaches activates):\n"
        "1. Open Recipe Builder.\n"
        "2. Check one real recipe's cost (must be real purchase/card data, or 'cost missing').\n"
        "3. Create or edit one recipe.\n"
        "4. Choose PASS or FAIL and attach evidence.\n"
        "Note: activate when Matt confirms carolus.haryanto@gmail.com is in Beta Cloudflare."
    )
    item = wi.create_work_item(
        title="Commission Recipe Builder (Hariyanto)",
        description=instructions,
        owning_entity_id=ENTITY,
        work_type="AUDIT_FINDING",
        source_type="SYSTEM",
        created_by_actor_type="SYSTEM",
        owner_person_id=HARI,
        owner_org_assignment_id=ASG,
        source_id=f"commissioning:{COMM_CAP}",
        priority=2,
        conn=conn,
        commit=False,
    )
    wid = item["work_item_id"]
    conn.execute(
        """
        UPDATE core_work_items
        SET accountable_person_id=?,
            executor_person_id=?,
            requested_by_person_id='PERS-MATT',
            origin='commissioning',
            instructions=?,
            evidence_required=?,
            checklist_json=?,
            scope_label=?,
            commissioning_capability_id=?,
            what_happens_next=?,
            routing_state=?,
            routing_reason=?,
            updated_at=?
        WHERE work_item_id=?
        """,
        (
            HARI,
            HARI,
            instructions,
            "Screenshot of Recipe Builder with real cost or cost missing; create/edit evidence",
            json.dumps(
                [
                    {
                        "step": instructions,
                        "href": "/bzg/recipe-builder",
                    }
                ]
            ),
            "BZG · Head Chef · Recipe Builder",
            COMM_CAP,
            "HELD until Peaches activates after allow/deny pass. Not visible as active My Work.",
            ROUTING_HELD_CF,
            "activate when Matt confirms carolus.haryanto@gmail.com is in Beta Cloudflare "
            "(confirmed 2026-09-29 — Peaches activates only after Person/AuthIdentity, "
            "Head Chef Assignment/Scope, real Recipe Builder and all server-side "
            "allow/deny checks pass)",
            ts,
            wid,
        ),
    )
    return wid


def main() -> int:
    db_path = Path(DB)
    bad = _refuse_path(db_path)
    if bad:
        print(f"REFUSE: {bad} in {db_path}", file=sys.stderr)
        return 2

    ts = now_iso()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        dest = BACKUP_DIR / f"pre-headchef1-{stamp()}.sqlite"
        shutil.copy2(db_path, dest)
        digest = _sha256(dest)
        print(f"BACKUP={dest}")
        print(f"SHA256={digest}")

        # --- Hariyanto person + identity (assert unique email) ---
        _ensure_person(
            conn,
            person_id=HARI,
            display_name=HARI_DISPLAY,
            legal_name=HARI_LEGAL,
            auth_id=HARI_AUTH,
            email=HARI_EMAIL,
            ts=ts,
        )
        # Assert no other Person holds that identifier
        owners = conn.execute(
            """
            SELECT person_id FROM org_auth_identities
            WHERE provider='email' AND lower(identifier)=?
            """,
            (HARI_EMAIL,),
        ).fetchall()
        if len(owners) != 1 or owners[0][0] != HARI:
            raise RuntimeError(f"email ownership assert failed: {owners}")

        # --- Maciej auth-only (zero assignments) ---
        _ensure_person(
            conn,
            person_id=MACIEJ,
            display_name=MACIEJ_DISPLAY,
            legal_name=None,
            auth_id=MACIEJ_AUTH,
            email=MACIEJ_EMAIL,
            ts=ts,
        )
        maciej_asg = conn.execute(
            """
            SELECT COUNT(*) FROM org_assignments
            WHERE person_id=? AND status='ACTIVE' AND end_at IS NULL
            """,
            (MACIEJ,),
        ).fetchone()[0]
        if maciej_asg:
            raise RuntimeError("REFUSE: Maciej must have zero active assignments")

        # --- Role / Position / Assignment ---
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
            (ROLE, ROLE_DISPLAY, DEPT, ts, ts),
        )
        # Position not tied to one outlet (brand_id / location_id NULL)
        conn.execute(
            """
            INSERT INTO org_positions (
              position_id, role_id, entity_id, location_id, brand_id, department_id,
              position_label, status, fte, created_at, updated_at
            ) VALUES (?, ?, ?, NULL, NULL, ?, 'Head Chef · BZG F&B', 'ACTIVE', 1.0, ?, ?)
            ON CONFLICT(position_id) DO UPDATE SET
              role_id=excluded.role_id,
              entity_id=excluded.entity_id,
              location_id=NULL,
              brand_id=NULL,
              department_id=excluded.department_id,
              position_label=excluded.position_label,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (POS, ROLE, ENTITY, DEPT, ts, ts),
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
            (ASG, HARI, POS, START, ts, ts),
        )

        _upgrade_scope_fb(conn, ts)
        upsert_assignment_scope(conn, ASG, SCOPE_FB, START, ts)

        granted = _grant_role_perms(conn, ts)
        _assert_denies(conn)

        wid = _create_held_commissioning(conn, ts)

        # Recipe import into Beta store
        import_report = rb.import_v1_recipes()

        tabs = {
            r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "schema_migrations" in tabs:
            conn.execute(
                """
                INSERT INTO schema_migrations (id, applied_at, note)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET applied_at=excluded.applied_at, note=excluded.note
                """,
                (MIGRATION_ID, ts, "HEADCHEF-1 Hariyanto + Recipe Builder"),
            )

        conn.commit()

        report = {
            "migration": MIGRATION_ID,
            "person_id": HARI,
            "auth_identity_id": HARI_AUTH,
            "email": HARI_EMAIL,
            "role_id": ROLE,
            "position_id": POS,
            "assignment_id": ASG,
            "scope_id": SCOPE_FB,
            "granted": granted,
            "deny_asserted": list(DENY_ASSERT),
            "commissioning_work_item_id": wid,
            "commissioning_routing_state": ROUTING_HELD_CF,
            "maciej_person_id": MACIEJ,
            "maciej_assignments": 0,
            "recipe_import": import_report,
            "staff_ready": False,
            "human_commissioned": False,
            "activated": False,
        }
        print(json.dumps(report, indent=2, default=str))
        return 0
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
