#!/usr/bin/env python3
"""P0 authority-derived nav — Assignment/Role/Scope (People ≠ Roles).

PARTIAL only. staff_ready=false. No prod. Survives staff-swap unit case.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import wolf_shell as shell  # noqa: E402

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


def main() -> int:
    check("bound beta", shell.BOUND == "beta")
    check("honesty ia transitional", shell.honesty_flags().get("ia_intersect_pages_transitional") is True)
    check("honesty authority_nav_partial", shell.honesty_flags().get("authority_nav_partial") is True)
    check("staff_ready false", shell.honesty_flags().get("staff_ready") is False)
    check("not proven", shell.honesty_flags().get("proven") is False)

    # --- Staff swap: same ROLE+SCOPE, different person_id → identical nav ---
    template = {
        "id": "ASG-SWAP-FC",
        "role": "ROLE-AMG-FINANCIAL-CONTROLLER",
        "label": "Atrium Financial Controller",
        "scope": "SCOPE-AMG-FINANCE",
        "scopes": ["SCOPE-AMG-FINANCE"],
        "href": "/amg/finance",
    }
    nav_a = shell.authority_nav_from_assignments([{**template, "person_id": "PERS-OLD-STAFF"}])
    nav_b = shell.authority_nav_from_assignments([{**template, "person_id": "PERS-NEW-STAFF"}])
    check("staff swap businesses equal", nav_a["businesses"] == nav_b["businesses"])
    check("staff swap items equal", nav_a["items"] == nav_b["items"])
    check("staff swap roles equal", nav_a["roles"] == nav_b["roles"])
    check("staff swap scopes equal", nav_a["scopes"] == nav_b["scopes"])
    blob = str(nav_a) + str(nav_b)
    check("no person_id in nav payload", "PERS-OLD-STAFF" not in blob and "PERS-NEW-STAFF" not in blob)
    check("no hard-coded Zayen in authority nav", "Zayen" not in blob)
    check("amg chip from SCOPE-AMG-FINANCE", any(b.get("id") == "amg" for b in nav_a["businesses"]))
    check("finance item href", any(i.get("href") == "/amg/finance" for i in nav_a["items"]))
    check("source assignment_role_scope", nav_a.get("source") == "assignment_role_scope")
    check("people_neq_roles flag", nav_a.get("people_neq_roles") is True)

    # Chef role → recipe builder (Hariyanto seat is ROLE not person)
    chef = shell.authority_nav_from_assignments(
        [
            {
                "id": "ASG-SWAP-CHEF",
                "role": "ROLE-BZG-HEAD-CHEF",
                "label": "Head Chef · BZG F&B",
                "scope": "SCOPE-BZG-FB",
                "scopes": ["SCOPE-BZG-FB"],
                "href": "/bzg/recipe-builder",
            }
        ]
    )
    check("chef bzg chip", any(b.get("id") == "bzg" for b in chef["businesses"]))
    check("chef recipe item", any(i.get("href") == "/bzg/recipe-builder" for i in chef["items"]))

    # Content role → content surface
    content = shell.authority_nav_from_assignments(
        [
            {
                "id": "ASG-SWAP-CONTENT",
                "role": "ROLE-CONTENT",
                "label": "Content",
                "scope": "SCOPE-GGV-CONTENT",
                "scopes": ["SCOPE-GGV-CONTENT"],
                "href": "/content-2.0",
            }
        ]
    )
    check("content ggv chip", any(b.get("id") == "ggv" for b in content["businesses"]))
    check("content href", any(i.get("href") == "/content-2.0" for i in content["items"]))

    # Owner roles get full business chip set from catalog (not person map)
    owner = shell.authority_nav_from_assignments(
        [
            {
                "id": "ASG-SWAP-OWNER",
                "role": "ROLE-OWNER",
                "label": "Owner",
                "scope": "SCOPE-WOLF-GROUP",
                "scopes": ["SCOPE-WOLF-GROUP"],
                "href": "/wolf",
            }
        ]
    )
    ob = [b["id"] for b in owner["businesses"]]
    check("owner has owner chip", "owner" in ob)
    check("owner has multi biz", all(k in ob for k in ("ggv", "amg", "bzg")))

    # whoami exposes nav_authority; transitional businesses still present
    who = shell.build_whoami(person_id="PERS-ZAYEN")
    check("whoami has nav_authority", isinstance(who.get("nav_authority"), dict))
    check("whoami still has transitional businesses", isinstance(who.get("businesses"), list))
    payload = shell.shell_whoami_payload({"ok": True, "person_id": "PERS-ZAYEN", "email": "laluzayen@gmail.com"})
    check("payload nav_authority", isinstance(payload.get("nav_authority"), dict))
    check(
        "payload authority source",
        (payload.get("nav_authority") or {}).get("source") == "assignment_role_scope",
    )

    # Live DB seats route recovered caps to intended ROLE surfaces (not invent PASS)
    z = shell.authority_nav_for_person("PERS-ZAYEN")
    check("zayen amg+bzg chips", set(b["id"] for b in z["businesses"]) >= {"amg", "bzg"})
    zhrefs = {i["href"] for i in z["items"]}
    check("zayen amg finance item", "/amg/finance" in zhrefs)
    check("zayen bzg finance item", "/bzg/finance" in zhrefs)

    am = shell.authority_nav_for_person("PERS-AMANDA")
    check("amanda ggv chip", any(b["id"] == "ggv" for b in am["businesses"]))
    amhrefs = {i["href"] for i in am["items"]}
    check("amanda ggv finance item", "/ggv/finance" in amhrefs)

    hari = shell.authority_nav_for_person("PERS-HARIYANTO")
    check("hari recipe item", any(i["href"] == "/bzg/recipe-builder" for i in hari["items"]))

    print(f"\nRESULT  pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
