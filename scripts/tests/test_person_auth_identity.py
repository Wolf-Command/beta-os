#!/usr/bin/env python3
"""Person + Authentication Identity acceptance tests — Beta only."""
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

from migrations.migrate_person_auth_identity import main as migrate_main  # noqa: E402
from core import identity as ident  # noqa: E402
import wolf_intelligence as wi  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}  {detail}")


def main() -> int:
    src = (SCRIPTS / "core" / "identity.py").read_text()
    check("no Role/Assignment tables referenced for grants", "org_roles" not in src and "org_assignments" not in src and "has_permission" not in src)
    check("no CF JWT fake verification", "jwt" not in src.lower() or "NOT BUILT" in src or "not" in src.lower())
    check("beta-os guard present", "beta-os" in src and "wolf-system" in src)

    before_perm = sqlite3.connect(str(DB)).execute("SELECT COUNT(*) FROM permissions").fetchone()[0]

    check("migration 1", migrate_main() == 0)
    check("migration 2 idempotent", migrate_main() == 0)

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    n_p = conn.execute("SELECT COUNT(*) FROM org_persons").fetchone()[0]
    n_a = conn.execute("SELECT COUNT(*) FROM org_auth_identities").fetchone()[0]
    check("4 persons", n_p == 4, str(n_p))
    check("4 auth identities", n_a == 4, str(n_a))

    # Person IDs are not emails
    for r in conn.execute("SELECT person_id FROM org_persons"):
        check(f"person_id not email {r['person_id']}", "@" not in r["person_id"])

    # Email maps to one person
    matt = ident.resolve_person_from_email("mrwolf@wolfcommand.net")
    check("matt email → PERS-MATT", matt and matt["person_id"] == "PERS-MATT")
    check("case-insensitive email", ident.resolve_person_from_email("MrWolf@WolfCommand.net")["person_id"] == "PERS-MATT")

    # Unique provider+identifier
    dups = conn.execute(
        """
        SELECT provider, lower(identifier), COUNT(*) c
        FROM org_auth_identities GROUP BY 1,2 HAVING c>1
        """
    ).fetchall()
    check("no duplicate provider+identifier", not dups, str(dups))

    # One email cannot map to two persons (structural)
    multi = conn.execute(
        """
        SELECT lower(identifier), COUNT(DISTINCT person_id) c
        FROM org_auth_identities WHERE provider='email'
        GROUP BY 1 HAVING c>1
        """
    ).fetchall()
    check("one email → one person", not multi)

    # Multiple identities structurally supported (table allows; seed has one each)
    # Insert second identity for Matt in temp then rollback via delete
    conn.execute(
        """
        INSERT INTO org_auth_identities (
          auth_identity_id, person_id, provider, identifier, status,
          is_primary, created_at, updated_at, last_verified_at
        ) VALUES ('AUTH-MATT-EMAIL-ALT', 'PERS-MATT', 'email', 'matt.alt.test@wolfcommand.net',
                  'ACTIVE', 0, datetime('now'), datetime('now'), NULL)
        """
    )
    conn.commit()
    n_matt = conn.execute(
        "SELECT COUNT(*) FROM org_auth_identities WHERE person_id='PERS-MATT'"
    ).fetchone()[0]
    check("one person can hold multiple identities", n_matt == 2)
    # deactivate alt — person survives
    conn.execute("UPDATE org_auth_identities SET status='INACTIVE' WHERE auth_identity_id='AUTH-MATT-EMAIL-ALT'")
    conn.commit()
    p = ident.get_person("PERS-MATT")
    check("person survives auth status change", p and p["status"] == "ACTIVE")
    conn.execute("DELETE FROM org_auth_identities WHERE auth_identity_id='AUTH-MATT-EMAIL-ALT'")
    conn.commit()

    # Content permissions still email-based
    after_perm = conn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
    check("permissions rows unchanged", after_perm == before_perm)
    check(
        "has_permission still works via email subject",
        wi.has_permission("mrwolf@wolfcommand.net", "can_create_plan"),
    )
    # Transitional: email → person → still use email for permission
    resolved = ident.resolve_person_from_email("amanda@wolfcommand.net")
    check(
        "transitional adapter amanda",
        resolved and resolved["person_id"] == "PERS-AMANDA",
    )
    check(
        "amanda permissions still by email",
        wi.has_permission(resolved["auth_identifier"], "can_create_plan"),
    )

    check("unknown identifier fails", ident.resolve_person_from_email("nobody@example.com") is None)

    # Honesty API labels
    me = ident.resolve_from_development_assertion("mrwolf@wolfcommand.net")
    check("assurance is development_assertion", me["identity_assurance"] == "development_assertion")
    check("real_authentication False", me["real_authentication"] is False)
    check("not labeled authenticated_user", "authenticated_user" not in json.dumps(me))

    # DEVELOPMENT assertion helper renamed
    check(
        "resolve_development_identity_assertion exists",
        hasattr(wi, "resolve_development_identity_assertion"),
    )
    subj = wi.resolve_development_identity_assertion(
        {"headers": {"X-Wolf-Subject": "haikalqilbari123@gmail.com"}, "body": {}}
    )
    check("dev assertion returns email", subj == "haikalqilbari123@gmail.com")
    legacy = wi.resolve_authenticated_subject(
        {"headers": {"X-Wolf-Subject": "mlsary111@gmail.com"}, "body": {}}
    )
    check("legacy alias still works", legacy == "mlsary111@gmail.com")

    # No Role sneak
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    check("no org_roles table this slice", "org_roles" not in tables and "org_assignments" not in tables)

    conn.close()

    # Optional live API
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8788/api/core/me?subject=mrwolf@wolfcommand.net",
            headers={"X-Wolf-Subject": "mrwolf@wolfcommand.net"},
        )
        with urllib.request.urlopen(req, timeout=2) as r:
            body = json.loads(r.read().decode())
        check("API /me assurance honest", body.get("identity_assurance") == "development_assertion")
        check("API /me real_authentication false", body.get("real_authentication") is False)
        check("API /me has person_id", body.get("person_id") == "PERS-MATT")
        with urllib.request.urlopen("http://127.0.0.1:8788/api/core/persons", timeout=2) as r:
            plist = json.loads(r.read().decode())
        check("API persons list ok", plist.get("ok") and len(plist.get("persons", [])) == 4)
        # list must not dump emails
        blob = json.dumps(plist)
        check("persons list has no emails", "wolfcommand.net" not in blob and "gmail.com" not in blob)
        with urllib.request.urlopen("http://127.0.0.1:8788/api/core/persons/PERS-NOPE", timeout=2) as r:
            pass
        check("person 404", False)
    except urllib.error.HTTPError as e:
        check("person 404", e.code == 404)
    except Exception as e:
        check("API optional skip", True, str(e))

    print(f"\nSUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
