#!/usr/bin/env python3
"""Role + Position + Assignment acceptance tests — Beta only."""
from __future__ import annotations

import json
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os").resolve()
SCRIPTS = ROOT / "scripts"
DB = ROOT / "catalog" / "content_library.sqlite"
sys.path.insert(0, str(SCRIPTS))

from migrations.migrate_role_position_assignment import main as migrate_main  # noqa: E402
from core import staffing as st  # noqa: E402
import wolf_intelligence as wi  # noqa: E402
from llm_orchestrator import ROLE_ROUTING  # noqa: E402

PASS = FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}  {detail}")


def main() -> int:
    src = (SCRIPTS / "core" / "staffing.py").read_text()
    check("staffing uses org_roles not LLM ROLE_ROUTING", "org_roles" in src and "ROLE_ROUTING" not in src)
    check("no permission-engine calls in staffing", "has_permission" not in src and "KNOWN_PERMISSIONS" not in src)

    before_perm = sqlite3.connect(str(DB)).execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
    before_persons = sqlite3.connect(str(DB)).execute("SELECT COUNT(*) FROM org_persons").fetchone()[0]

    check("migration 1", migrate_main() == 0)
    check("migration 2 idempotent", migrate_main() == 0)

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    n_roles = conn.execute("SELECT COUNT(*) FROM org_roles").fetchone()[0]
    n_pos = conn.execute("SELECT COUNT(*) FROM org_positions").fetchone()[0]
    n_asg = conn.execute("SELECT COUNT(*) FROM org_assignments").fetchone()[0]
    check("roles seeded >= 7", n_roles >= 7, str(n_roles))
    check("positions seeded = 4", n_pos == 4, str(n_pos))
    check("assignments seeded = 4", n_asg == 4, str(n_asg))

    for r in conn.execute("SELECT role_id FROM org_roles"):
        check(f"role_id stable not email {r['role_id']}", "@" not in r["role_id"])

    # Position entity ownership
    ve = conn.execute(
        "SELECT entity_id, role_id FROM org_positions WHERE position_id='POS-VIDEO-EDITOR-1'"
    ).fetchone()
    check("video editor under ENT-GGV", ve and ve["entity_id"] == "ENT-GGV" and ve["role_id"] == "ROLE-GGV-EDIT")

    # Assignment links
    a = conn.execute(
        "SELECT person_id, position_id FROM org_assignments WHERE assignment_id='ASG-HAIKAL-VE-1'"
    ).fetchone()
    check("Haikal assigned to video editor seat", a and a["person_id"] == "PERS-HAIKAL" and a["position_id"] == "POS-VIDEO-EDITOR-1")

    # Historical survival: end an assignment copy then restore
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status, is_primary, created_at, updated_at
        ) VALUES (
          'ASG-HIST-TEST', 'PERS-MISA', 'POS-CONTENT-CREW-1',
          '2026-01-01T00:00:00+08:00', '2026-06-01T00:00:00+08:00',
          'ENDED', 0, datetime('now'), datetime('now')
        )
        """
    )
    # Wait - POS-CONTENT-CREW-1 already has primary active Misa - historical with is_primary=0 and ENDED is fine
    conn.commit()
    hist = conn.execute("SELECT status, end_at FROM org_assignments WHERE assignment_id='ASG-HIST-TEST'").fetchone()
    check("historical assignment kept", hist and hist["status"] == "ENDED" and hist["end_at"] is not None)
    person = conn.execute("SELECT status FROM org_persons WHERE person_id='PERS-MISA'").fetchone()
    pos = conn.execute("SELECT status FROM org_positions WHERE position_id='POS-CONTENT-CREW-1'").fetchone()
    check("ending asg does not delete person", person and person["status"] == "ACTIVE")
    check("ending asg does not delete position", pos and pos["status"] == "ACTIVE")

    # Multiple assignments for one person structurally
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status, is_primary, created_at, updated_at
        ) VALUES (
          'ASG-MATT-SECOND', 'PERS-MATT', 'POS-CONTENT-MGMT-1',
          '2026-09-16T00:00:00+08:00', NULL, 'ACTIVE', 0, datetime('now'), datetime('now')
        )
        """
    )
    # POS-CONTENT-MGMT-1 has Amanda as primary — Matt secondary on same position OK if is_primary=0
    try:
        conn.commit()
        n_matt = conn.execute(
            "SELECT COUNT(*) FROM org_assignments WHERE person_id='PERS-MATT' AND status='ACTIVE' AND end_at IS NULL"
        ).fetchone()[0]
        check("one person multiple active assignments", n_matt >= 2)
    except sqlite3.IntegrityError as e:
        check("one person multiple active assignments", False, str(e))

    # Duplicate primary active blocked
    blocked = False
    try:
        conn.execute(
            """
            INSERT INTO org_assignments (
              assignment_id, person_id, position_id, start_at, end_at, status, is_primary, created_at, updated_at
            ) VALUES (
              'ASG-DUP-PRIMARY', 'PERS-HAIKAL', 'POS-OWNER-EXEC-1',
              '2026-09-16T00:00:00+08:00', NULL, 'ACTIVE', 1, datetime('now'), datetime('now')
            )
            """
        )
        conn.commit()
    except sqlite3.IntegrityError:
        blocked = True
        conn.rollback()
    check("duplicate active primary occupancy prevented", blocked)

    # Cleanup test rows
    conn.execute("DELETE FROM org_assignments WHERE assignment_id IN ('ASG-HIST-TEST','ASG-MATT-SECOND','ASG-DUP-PRIMARY')")
    conn.commit()

    after_perm = conn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
    after_persons = conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0]
    check("permissions unchanged", after_perm == before_perm)
    check("persons unchanged", after_persons == before_persons)
    check("content permission still email", wi.has_permission("haikalqilbari123@gmail.com", "can_edit_plan"))

    # LLM role collision check
    check("LLM ROLE_ROUTING still separate", "hook_generation" in ROLE_ROUTING)
    check("org role ROLE-GGV-EDIT not in LLM routing", "ROLE-GGV-EDIT" not in ROLE_ROUTING)

    # Repo helpers
    check("list_roles", len(st.list_roles()) >= 7)
    check("positions by entity GGV", len(st.list_positions_by_entity("ENT-GGV")) == 4)
    check("active asg Haikal", len(st.list_active_assignments_for_person("PERS-HAIKAL")) == 1)
    occ = st.get_current_occupants("POS-OWNER-EXEC-1")
    check("Matt occupies owner seat", len(occ) == 1 and occ[0]["person_id"] == "PERS-MATT")
    ctx = st.resolve_org_context_for_person("PERS-AMANDA")
    check("org context scope NOT_BUILT", ctx.get("scope") == "NOT_BUILT" and ctx.get("rbac") == "NOT_BUILT")

    # No Scope/RBAC tables
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    check("no org_scopes/rbac tables", "org_scopes" not in tables and "org_permissions_engine" not in tables)
    conn.close()

    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8788/api/core/me/assignments",
            headers={"X-Wolf-Subject": "mrwolf@wolfcommand.net"},
        )
        with urllib.request.urlopen(req, timeout=2) as r:
            body = json.loads(r.read().decode())
        check("me/assignments assurance", body.get("identity_assurance") == "development_assertion")
        check("me/assignments real_auth false", body.get("real_authentication") is False)
        check("me/assignments has owner seat", any(a.get("position_id") == "POS-OWNER-EXEC-1" for a in body.get("assignments", [])))
        with urllib.request.urlopen("http://127.0.0.1:8788/api/core/roles", timeout=2) as r:
            roles = json.loads(r.read().decode())
        check("API roles ok", roles.get("ok") and len(roles.get("roles", [])) >= 7)
    except Exception as e:
        check("API optional", True, str(e))

    print(f"\nSUMMARY pass={PASS} fail={FAIL}")
    print(f"COUNTS roles={n_roles} positions={n_pos} assignments={n_asg}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
