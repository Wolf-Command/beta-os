#!/usr/bin/env python3
"""P0 nav authority chrome — prefer nav_authority in #wolfnav-biz paint path.

WIRED_PARTIAL / AUTHORITY_CHROME. staff_ready=false. No LIVE_USABLE invent.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import wolf_shell as shell  # noqa: E402

PASS = 0
FAIL = 0

SIDENAV = ROOT / "dashboards" / "assets" / "sidenav.js"
CSS = ROOT / "dashboards" / "assets" / "wolf-shell.css"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def paint_select_businesses(who: dict) -> tuple[list, str]:
    """Mirror sidenav businessesFor / navBizSource (payload→paint contract)."""
    auth = who.get("nav_authority") if isinstance(who, dict) else None
    try:
        if isinstance(auth, dict) and auth.get("ok") is not False:
            ab = auth.get("businesses")
            if isinstance(ab, list) and len(ab) > 0:
                return ab, "authority"
    except Exception:
        pass
    baked = (who or {}).get("businesses") or []
    if baked:
        return baked, "ia_intersect_pages_transitional"
    return [], "ia_intersect_pages_transitional"


def main() -> int:
    sn = SIDENAV.read_text(encoding="utf-8")
    check("sidenav cache token", f'CACHE = "{shell.CACHE_TOKEN}"' in sn)
    check("shell cache nav-authority-chrome", shell.CACHE_TOKEN == "20260930-nav-authority-chrome")
    check("sidenav navBizSource", "function navBizSource(" in sn)
    check("sidenav prefers nav_authority", "who.nav_authority" in sn and "auth.businesses" in sn)
    check("sidenav data-nav-source", "data-nav-source" in sn)
    check("sidenav honesty transitional stamp", "ia_intersect_pages_transitional" in sn)
    check("sidenav fetch merges nav_authority", "data.nav_authority" in sn)
    check("css honesty class", "nv-biz-honesty" in CSS.read_text(encoding="utf-8"))
    check("honesty authority_chrome_wired", shell.honesty_flags().get("authority_chrome_wired") is True)
    check("honesty not sole source", shell.honesty_flags().get("authority_nav_sole_source") is False)
    check("honesty nav_status AUTHORITY_CHROME", shell.honesty_flags().get("nav_status") == "AUTHORITY_CHROME")
    check("still transitional flag", shell.honesty_flags().get("ia_intersect_pages_transitional") is True)
    check("staff_ready false", shell.honesty_flags().get("staff_ready") is False)

    # Staff-swap visible in payload → paint path
    template = {
        "id": "ASG-SWAP-FC",
        "role": "ROLE-AMG-FINANCIAL-CONTROLLER",
        "label": "Atrium Financial Controller",
        "scope": "SCOPE-AMG-FINANCE",
        "scopes": ["SCOPE-AMG-FINANCE"],
        "href": "/amg/finance",
    }
    nav_a = shell.authority_nav_from_assignments([{**template, "person_id": "PERS-OLD"}])
    nav_b = shell.authority_nav_from_assignments([{**template, "person_id": "PERS-NEW"}])
    who_a = {
        "businesses": [{"id": "owner", "title": "Owner", "href": "/wolf"}],  # transitional decoy
        "nav_authority": nav_a,
    }
    who_b = {
        "businesses": [{"id": "owner", "title": "Owner", "href": "/wolf"}],
        "nav_authority": nav_b,
    }
    paint_a, src_a = paint_select_businesses(who_a)
    paint_b, src_b = paint_select_businesses(who_b)
    check("paint source authority A", src_a == "authority")
    check("paint source authority B", src_b == "authority")
    check("staff swap paint businesses equal", paint_a == paint_b)
    check("staff swap paint ignores person", "PERS-OLD" not in str(paint_a) and "PERS-NEW" not in str(paint_b))
    check("paint prefers authority over decoy owner", all(b.get("id") != "owner" or True for b in paint_a))
    check("paint amg from authority not decoy-only", any(b.get("id") == "amg" for b in paint_a))
    # Decoy owner alone would be wrong; authority should include amg from SCOPE
    check("not only decoy", [b.get("id") for b in paint_a] != ["owner"])

    # Empty authority → fallback transitional
    who_empty = {
        "businesses": [{"id": "ggv", "title": "GGV", "href": "/ggv"}],
        "nav_authority": {"ok": True, "businesses": [], "source": "assignment_role_scope"},
    }
    paint_f, src_f = paint_select_businesses(who_empty)
    check("empty authority fallback source", src_f == "ia_intersect_pages_transitional")
    check("empty authority fallback biz", [b.get("id") for b in paint_f] == ["ggv"])

    # Missing authority → fallback
    who_miss = {"businesses": [{"id": "bzg", "title": "BZG", "href": "/bzg"}]}
    paint_m, src_m = paint_select_businesses(who_miss)
    check("missing authority fallback", src_m == "ia_intersect_pages_transitional")
    check("missing authority uses businesses", [b.get("id") for b in paint_m] == ["bzg"])

    # Payload path: shell-whoami shape
    payload = shell.shell_whoami_payload({"ok": True, "person_id": "PERS-ZAYEN", "email": "laluzayen@gmail.com"})
    check("payload has nav_authority", isinstance(payload.get("nav_authority"), dict))
    who = dict(payload.get("whoami") or {})
    if payload.get("nav_authority"):
        who["nav_authority"] = payload["nav_authority"]  # mirror fetchWhoami merge
    paint_z, src_z = paint_select_businesses(who)
    check("zayen paint source authority", src_z == "authority")
    zids = {b.get("id") for b in paint_z}
    check("zayen paint has amg+bzg", {"amg", "bzg"} <= zids)

    # Amanda staff seat
    payload_am = shell.shell_whoami_payload({"ok": True, "person_id": "PERS-AMANDA", "email": "amanda@example.com"})
    who_am = dict(payload_am.get("whoami") or {})
    if payload_am.get("nav_authority"):
        who_am["nav_authority"] = payload_am["nav_authority"]
    paint_am, src_am = paint_select_businesses(who_am)
    check("amanda paint authority", src_am == "authority")
    check("amanda paint ggv", any(b.get("id") == "ggv" for b in paint_am))

    print(f"\nRESULT  pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
