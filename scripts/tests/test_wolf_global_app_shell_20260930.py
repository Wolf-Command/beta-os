#!/usr/bin/env python3
"""P0 global app shell — business switcher + Owner Trading/Fitness IA (Beta).

PARTIAL only. staff_ready=false. No prod. No invent PROVEN/READY.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"

from core import wolf_shell as shell  # noqa: E402

PASS = 0
FAIL = 0

MATT = "mrwolf@wolfcommand.net"
DEVI = "deviputu236@gmail.com"
SIDENAV = ROOT / "dashboards" / "assets" / "sidenav.js"
CSS = ROOT / "dashboards" / "assets" / "wolf-shell.css"
SPEC = ROOT / "state" / "final-completion" / "p0-v1" / "GLOBAL-APP-SHELL-SPEC.md"
TRADING = ROOT / "dashboards" / "owner-trading-1.html"
FITNESS = ROOT / "dashboards" / "owner-fitness-1.html"


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
    check("cache token matches shell", shell.CACHE_TOKEN == "20261002-owner-ux-petty")
    check("spec exists", SPEC.is_file())
    check("honesty business_switcher_from_ia", shell.honesty_flags().get("business_switcher_from_ia") is True)
    check("not proven", shell.honesty_flags().get("proven") is False)
    check("staff_ready false", shell.honesty_flags().get("staff_ready") is False)

    cat = shell.business_catalog_from_ia()
    keys = [b["id"] for b in cat]
    check("catalog has owner", "owner" in keys)
    check("catalog has ggv amg bzg", all(k in keys for k in ("ggv", "amg", "bzg")))
    check("catalog derived not empty", len(cat) >= 4)

    personal = next(s for s in shell.IA_TREE if s["id"] == "personal")
    hrefs = [it["href"] for it in personal["items"]]
    check("PERSONAL has trading", "/owner/trading" in hrefs)
    check("PERSONAL has fitness", "/owner/fitness" in hrefs)
    check("trading crumb", bool(shell.ROUTE_CRUMBS.get("/owner/trading")))
    check("fitness crumb", bool(shell.ROUTE_CRUMBS.get("/owner/fitness")))
    check("trading parent empire", shell.ROUTE_PARENT.get("/owner/trading") == shell.EMPIRE_HREF)
    check("fitness parent empire", shell.ROUTE_PARENT.get("/owner/fitness") == shell.EMPIRE_HREF)

    owner = shell.build_whoami(person_id="PERS-MATT", email=MATT)
    biz = owner.get("businesses") or []
    bids = [b["id"] for b in biz]
    check("owner business_switcher on", owner.get("business_switcher") is True)
    check("owner has Owner chip", "owner" in bids)
    check("owner has AMG", "amg" in bids)
    check("owner has BZG", "bzg" in bids)
    check("owner has GGV", "ggv" in bids)
    check("owner trading in pages", "/owner/trading" in owner["pages"])
    check("owner fitness in pages", "/owner/fitness" in owner["pages"])
    check(
        "active trading→owner",
        shell.active_business_id("/owner/trading", biz) == "owner",
    )
    check(
        "active uma bills→bzg (Uma under BZG)",
        shell.active_business_id("/bzg/uma-blu/bills", biz) == "bzg",
    )
    check("owner top chips exclude uma", "uma" not in bids)
    outs = owner.get("outlet_children") or []
    check("owner has BZG outlets", any(o.get("id") == "uma" for o in outs))
    check(
        "pre-opening outlets labeled",
        any("PRE-OPENING" in str(o.get("title") or "") for o in outs),
    )

    payload = shell.shell_whoami_payload(
        {"ok": True, "person_id": "PERS-MATT", "email": MATT}
    )
    check("payload businesses", len(payload.get("businesses") or []) > 1)
    check("payload business_switcher", payload.get("business_switcher") is True)

    client = shell.build_whoami(person_id=None, email=None, audience="CLIENT")
    check("client no businesses", client.get("businesses") == [])
    check("client switcher off", client.get("business_switcher") is False)

    sn = SIDENAV.read_text(encoding="utf-8")
    check("sidenav cache token", f'CACHE = "{shell.CACHE_TOKEN}"' in sn)
    check("sidenav paintBusiness", "function paintBusiness(" in sn)
    check("sidenav wolfnav-biz", "wolfnav-biz" in sn)
    check("sidenav trading parent", '"/owner/trading": "/owner-empire-pack"' in sn)
    check("sidenav fitness crumb", '"/owner/fitness"' in sn and "Fitness" in sn)
    check("css nv-biz", "nv-biz" in CSS.read_text(encoding="utf-8"))
    check("trading html sidenav", "sidenav.js" in TRADING.read_text(encoding="utf-8"))
    check("fitness html sidenav", "sidenav.js" in FITNESS.read_text(encoding="utf-8"))
    check("nav stub has biz", 'id="wolfnav-biz"' in Path(shell.__file__).read_text(encoding="utf-8"))

    # Devi — no Owner chip (not wolf_authorized pages for empire unless in pages)
    devi = shell.build_whoami(person_id="PERS-DEVI", email=DEVI)
    db = [b["id"] for b in (devi.get("businesses") or [])]
    check("devi no owner chip", "owner" not in db)
    check("devi has uma or bzg", "uma" in db or "bzg" in db)

    print(f"\nRESULT  pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
