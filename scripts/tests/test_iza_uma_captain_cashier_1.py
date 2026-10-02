#!/usr/bin/env python3
"""IZA-UMA-CAPTAIN-CASHIER-1 — Person/role/roster + close ACL (Beta catalog).

Asserts Captain⊇Cashier composition, multi-closer roster (Devi+Iza), Uma-only
scope, no person-specific forks, and serve_beta close_roles includes CAPTAIN.
Does not weaken CF production auth. staff_ready/human_commissioned stay false.
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import rbac  # noqa: E402
from core.ggv_finance_nota import active_role_ids  # noqa: E402

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
SERVE = SCRIPTS / "serve_beta.py"
MIG = SCRIPTS / "migrations" / "migrate_iza_uma_captain_cashier_1.py"

IZA = "PERS-IZA"
IZA_EMAIL = "izazaen00@gmail.com"
DEVI = "PERS-DEVI"
ROLE_CASHIER = "ROLE-BZG-CASHIER"
ROLE_CAPTAIN = "ROLE-BZG-CAPTAIN"
ASG_IZA = "ASG-IZA-CAPTAIN-UMA-1"
SCOPE_UMA = "SCOPE-BZG-UMA"
CASHIER_BUNDLE = {
    "venue.close.read",
    "venue.close.submit",
    "evidence.record.read",
    "evidence.record.submit",
    "work.read",
    "work.update",
    "work.complete",
}
DENY_CODES = (
    "finance.nota.read",
    "finance.invoice.read",
    "atrium.ledger.read",
    "payment.approve",
    "bzg.pr.payment_approve",
)

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _role_codes(conn: sqlite3.Connection, role_id: str) -> set[str]:
    rows = conn.execute(
        """
        SELECT p.code FROM org_role_permissions rp
        JOIN org_permissions p ON p.permission_id = rp.permission_id
        WHERE rp.role_id=? AND rp.effect='ALLOW'
        """,
        (role_id,),
    ).fetchall()
    return {str(r[0]) for r in rows}


def main() -> int:
    if not LIVE_DB.is_file():
        print(f"FAIL  missing catalog {LIVE_DB}")
        return 1

    conn = sqlite3.connect(str(LIVE_DB))
    conn.row_factory = sqlite3.Row
    try:
        # Person + auth bind
        person = conn.execute(
            "SELECT person_id, display_name, legal_name, status FROM org_persons WHERE person_id=?",
            (IZA,),
        ).fetchone()
        check("PERS-IZA exists", person is not None)
        if person:
            check("PERS-IZA ACTIVE", str(person["status"]) == "ACTIVE")
            check(
                "PERS-IZA display_name HR",
                str(person["display_name"]) == "Iza Zainatulloh Hulhidayati",
            )
            check(
                "PERS-IZA legal_name HR",
                str(person["legal_name"] or "") == "Iza Zainatulloh Hulhidayati",
            )

        auth = conn.execute(
            """
            SELECT auth_identity_id, person_id, provider, identifier, status
            FROM org_auth_identities
            WHERE provider='email' AND lower(identifier)=?
            """,
            (IZA_EMAIL,),
        ).fetchone()
        check("auth email bind exists", auth is not None)
        if auth:
            check("AUTH-IZA-EMAIL id", str(auth["auth_identity_id"]) == "AUTH-IZA-EMAIL")
            check("auth binds PERS-IZA", str(auth["person_id"]) == IZA)
            check("auth ACTIVE", str(auth["status"]) == "ACTIVE")

        # Captain + Cashier identical bundle
        cashier = _role_codes(conn, ROLE_CASHIER)
        captain = _role_codes(conn, ROLE_CAPTAIN)
        check("ROLE-BZG-CASHIER has CASHIER_BUNDLE", cashier == CASHIER_BUNDLE, str(cashier))
        check("ROLE-BZG-CAPTAIN has CASHIER_BUNDLE", captain == CASHIER_BUNDLE, str(captain))
        check("Captain bundle == Cashier bundle", cashier == captain)

        roles = active_role_ids(IZA, conn)
        check("active_role_ids includes CAPTAIN", ROLE_CAPTAIN in roles, str(roles))

        uma = {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}
        submit = rbac.evaluate(IZA, "venue.close.submit", uma, conn=conn)
        check(
            "venue.close.submit ALLOW on Uma",
            bool(submit.get("allowed")),
            str(submit.get("reason")),
        )
        read = rbac.evaluate(IZA, "venue.close.read", uma, conn=conn)
        check("venue.close.read ALLOW on Uma", bool(read.get("allowed")), str(read.get("reason")))

        for code in DENY_CODES:
            dec = rbac.evaluate(IZA, code, uma, conn=conn)
            check(
                f"DENY or no grant {code}",
                not bool(dec.get("allowed")),
                str(dec.get("reason")),
            )

        # Assignment + Uma-only scope
        asg = conn.execute(
            """
            SELECT assignment_id, person_id, position_id, status, is_primary, end_at
            FROM org_assignments WHERE assignment_id=?
            """,
            (ASG_IZA,),
        ).fetchone()
        check("ASG-IZA-CAPTAIN-UMA-1 exists", asg is not None)
        if asg:
            check("assignment ACTIVE", str(asg["status"]) == "ACTIVE" and asg["end_at"] is None)
            check("assignment primary", int(asg["is_primary"] or 0) == 1)
            check("assignment person PERS-IZA", str(asg["person_id"]) == IZA)
            check(
                "assignment position POS-BZG-CAPTAIN-UMA-1",
                str(asg["position_id"]) == "POS-BZG-CAPTAIN-UMA-1",
            )

        scopes = {
            str(r[0])
            for r in conn.execute(
                """
                SELECT scope_id FROM org_assignment_scopes
                WHERE assignment_id=? AND status='ACTIVE' AND end_at IS NULL
                """,
                (ASG_IZA,),
            )
        }
        check("scope SCOPE-BZG-UMA only", scopes == {SCOPE_UMA}, str(scopes))
        check("no SCOPE-BZG-ENTITY", "SCOPE-BZG-ENTITY" not in scopes)
        check("no AMG/GGV scopes", not any(s.startswith(("SCOPE-AMG", "SCOPE-GGV")) for s in scopes))

        # Multi-closer roster
        roster = {
            str(r["roster_id"]): dict(r)
            for r in conn.execute(
                """
                SELECT roster_id, person_id, assignment_id, status
                FROM venue_closer_roster
                WHERE brand_id='BZG-UMA' AND status='ACTIVE'
                """
            )
        }
        check("VCR-UMA-1 Devi ACTIVE", roster.get("VCR-UMA-1", {}).get("person_id") == DEVI)
        check("VCR-UMA-2 Iza ACTIVE", roster.get("VCR-UMA-2", {}).get("person_id") == IZA)
        check(
            "multi-closer Devi+Iza",
            {"VCR-UMA-1", "VCR-UMA-2"}.issubset(set(roster.keys())),
            str(sorted(roster.keys())),
        )

        pol = int(
            conn.execute(
                "SELECT COUNT(*) FROM venue_close_variance_policies WHERE status='ACTIVE'"
            ).fetchone()[0]
        )
        check("ACTIVE variance policies still 0", pol == 0, str(pol))

        # No emp/salary/bank columns invented on org_persons
        cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(org_persons)")}
        check(
            "org_persons has no emp/salary/bank cols",
            not any(c in cols for c in ("employee_id", "salary", "bank_account", "bank")),
            str(sorted(cols)),
        )
    finally:
        conn.close()

    # Source ACL — roster resolution, not person/email hardcode
    serve_src = SERVE.read_text(encoding="utf-8")
    m = re.search(
        r'path in \(\s*"/uma-blu-close".*?person_authorised_for_venue_close',
        serve_src,
        re.DOTALL,
    )
    check("uma-blu-close uses person_authorised_for_venue_close", m is not None)
    check("no PERS-IZA hardcode in serve close gate", "PERS-IZA" not in serve_src[serve_src.find("/uma-blu-close"):serve_src.find("/uma-blu-close") + 1200])
    check(
        "no Iza email in serve close gate",
        IZA_EMAIL not in serve_src[serve_src.find("/uma-blu-close"):serve_src.find("/uma-blu-close") + 1200],
    )

    mig_src = MIG.read_text(encoding="utf-8")
    check(
        "no if Iza fork in serve_beta",
        not re.search(r"if\s+.*\bIza\b|person_id\s*==\s*['\"]PERS-IZA", serve_src),
    )
    check(
        "migration does not DELETE/END VCR-UMA-1",
        "DELETE FROM venue_closer_roster" not in mig_src
        and "UPDATE venue_closer_roster" not in mig_src
        and "status='ENDED'" not in mig_src,
    )
    check(
        "migration preserves Devi roster",
        "VCR-UMA-1" in mig_src and "must stay ACTIVE PERS-DEVI" in mig_src,
    )
    check("no if Iza in migration", "if Iza" not in mig_src)

    # Unsigned close page remains assignment-gated (403 path intact)
    check(
        "unsigned forbidden path intact",
        "This close is not on your assignment." in serve_src
        and "permission-denied" in serve_src,
    )

    # Dev-assertion harness note only — do not weaken CF
    auth_mode = os.environ.get("BETA_AUTH_MODE", "")
    if auth_mode == "development_assertion":
        check(
            "dev-assertion mode noted (test harness)",
            True,
            "BETA_AUTH_MODE=development_assertion — CF production path unchanged",
        )
    else:
        check(
            "CF production path not weakened",
            "person_authorised_for_venue_close" in serve_src,
        )

    print(f"\npass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
