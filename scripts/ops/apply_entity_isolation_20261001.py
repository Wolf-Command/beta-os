#!/usr/bin/env python3
"""Surgical Beta entity-isolation patch — rbac + staff_home. Run on Mac only."""
from __future__ import annotations

import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BETA = Path("/Users/wolfterminal/beta-os")
RBAC = BETA / "scripts" / "core" / "rbac.py"
STAFF = BETA / "scripts" / "core" / "staff_home.py"
TZ = ZoneInfo("Asia/Makassar")


def backup(path: Path) -> Path:
    ts = datetime.now(TZ).strftime("%Y%m%d-%H%M%S")
    dest = path.with_suffix(path.suffix + f".bak-entity-iso-{ts}")
    shutil.copy2(path, dest)
    print(f"backup {dest}")
    return dest


def patch_rbac() -> None:
    src = RBAC.read_text(encoding="utf-8")
    if "ENTITY ISOLATION (2026-10-01)" in src and "_ENTITY_BOUND_PREFIXES" in src:
        print("rbac.py already patched")
        return
    helper = '''
# Entity-bound permission families (ONE FINANCE PRODUCT / THREE ENTITY CONFIGS).
# Shared permission codes must never vacuous-ALLOW without a requested entity/resource.
# Bare/empty target → DENY entity_scope_required (not a seating revoke/strip).
_ENTITY_BOUND_PREFIXES = (
    "finance.",
    "vendor.",
    "payment.",
    "atrium.",
)


def permission_requires_entity_scope(permission_code: str) -> bool:
    """True when evaluating this code requires entity/brand/location/department in target."""
    code = (permission_code or "").strip().lower()
    if not code:
        return False
    return code.startswith(_ENTITY_BOUND_PREFIXES)


def _target_has_where_keys(target: dict[str, Any] | None) -> bool:
    target = target or {}
    return any(
        str(target.get(k) or "").strip()
        for k in ("entity_id", "brand_id", "location_id", "department_id")
    )
'''
    anchor = 'CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"\n'
    if "_ENTITY_BOUND_PREFIXES" not in src:
        if anchor not in src:
            raise SystemExit("rbac anchor missing")
        src = src.replace(anchor, anchor + "\n" + helper + "\n", 1)

    needle = '''        explanation["permission_id"] = perm["permission_id"]

        # Active assignments
'''
    insert = '''        explanation["permission_id"] = perm["permission_id"]

        # ENTITY ISOLATION (2026-10-01): finance/vendor/payment/atrium codes require
        # a WHERE key on the request. Vacuous bare ALLOW was soft-bleed BREACH-2026-09-30-J1.
        target = target_context or {}
        if permission_requires_entity_scope(code) and not _target_has_where_keys(target):
            explanation["reason"] = "entity_scope_required"
            explanation["target_context"] = target
            return explanation

        # Active assignments
'''
    if "ENTITY ISOLATION (2026-10-01)" not in src:
        if needle not in src:
            raise SystemExit("rbac evaluate needle missing")
        src = src.replace(needle, insert, 1)

    # Update module docstring lightly
    old_doc = 'AI/LLM never decides access. Deny by default.\nAuthority Limits and real CF auth are NOT BUILT.'
    new_doc = (
        'AI/LLM never decides access. Deny by default.\n'
        'Finance/vendor/payment/atrium require entity scope on the request '
        '(entity_scope_required).\n'
        'Authority Limits and real CF auth are NOT BUILT.'
    )
    if old_doc in src and "entity_scope_required" not in src.split('"""')[1]:
        src = src.replace(old_doc, new_doc, 1)

    ast.parse(src)
    backup(RBAC)
    RBAC.write_text(src, encoding="utf-8")
    print(f"patched {RBAC} bytes={RBAC.stat().st_size}")


def patch_staff_home() -> None:
    src = STAFF.read_text(encoding="utf-8")
    if "finance_read_by_entity" in src and "ENTITY ISOLATION (2026-10-01)" in src:
        print("staff_home.py already patched")
        return

    # Ensure rbac import near top if missing
    if "from core import rbac" not in src and "import rbac" not in src:
        # after existing core imports
        marker = "from core import identity\nfrom core import work_items as wi\n"
        if marker not in src:
            raise SystemExit("staff_home import marker missing")
        src = src.replace(
            marker,
            marker + "from core import rbac as _rbac\n",
            1,
        )

    old = '''        authority = {
            "move_money": bool(codes & _MONEY),
            "change_bank": bool(codes & _BANK),
            "authorise_governance": bool(codes & _GOVERN),
            "finance_read": "finance.nota.read" in codes,
            "finance_review": "finance.nota.review" in codes,
            "finance_edit": "finance.nota.create" in codes or "finance.nota.edit" in codes,
            "unrestricted": False,
        }
'''
    new = '''        # ENTITY ISOLATION (2026-10-01): finance_* flags are AND-ed with entity scope.
        # Scope-blind role-code union was soft-bleed BREACH-2026-09-30-J1 (Zayen GGV adjacency).
        _FIN_ENTS = ("ENT-AMG", "ENT-BZG", "ENT-GGV")
        finance_read_by_entity = {
            eid: bool(_rbac.can(pid, "finance.nota.read", {"entity_id": eid}, conn=c))
            for eid in _FIN_ENTS
        }
        finance_review_by_entity = {
            eid: bool(_rbac.can(pid, "finance.nota.review", {"entity_id": eid}, conn=c))
            for eid in _FIN_ENTS
        }
        finance_edit_by_entity = {
            eid: bool(
                _rbac.can(pid, "finance.nota.create", {"entity_id": eid}, conn=c)
                or _rbac.can(pid, "finance.nota.edit", {"entity_id": eid}, conn=c)
            )
            for eid in _FIN_ENTS
        }
        authority = {
            "move_money": bool(codes & _MONEY),
            "change_bank": bool(codes & _BANK),
            "authorise_governance": bool(codes & _GOVERN),
            "finance_read": any(finance_read_by_entity.values()),
            "finance_review": any(finance_review_by_entity.values()),
            "finance_edit": any(finance_edit_by_entity.values()),
            "finance_read_by_entity": finance_read_by_entity,
            "finance_review_by_entity": finance_review_by_entity,
            "finance_edit_by_entity": finance_edit_by_entity,
            "unrestricted": False,
        }
'''
    if old not in src:
        raise SystemExit("staff_home authority block missing or already changed")
    src = src.replace(old, new, 1)
    ast.parse(src)
    backup(STAFF)
    STAFF.write_text(src, encoding="utf-8")
    print(f"patched {STAFF} bytes={STAFF.stat().st_size}")


def main() -> int:
    if not RBAC.is_file() or not STAFF.is_file():
        print("beta-os core files missing", file=sys.stderr)
        return 2
    patch_rbac()
    patch_staff_home()
    print("DONE entity isolation patch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
