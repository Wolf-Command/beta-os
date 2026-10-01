#!/usr/bin/env python3
"""Pack 9 — pre-open registry rows and a blank close. No fake sales."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import bzg_preopen_config_pack9 as pre  # noqa: E402

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
    catalog_mtime = pre.CATALOG_DB.stat().st_mtime_ns
    claude_mtime = pre.CLAUDE_MD.stat().st_mtime_ns
    brand_mtime = pre.BRAND_CONFIG.stat().st_mtime_ns
    data = pre.load_preopen()
    check("staff not ready", data.get("staff_ready") is False and data.get("human_proven") is False and data.get("writes") is False)
    check("no fake sales", data.get("fake_sales") is False and data.get("sales") is None and data.get("till") is None and data.get("covers") is None)
    standing = data["standing_name"]
    check(
        "standing title resolved",
        standing.get("resolved") is True and standing.get("title") == "Blu Zone Restaurant" and standing.get("rainforest_restaurant_dead") is True,
        str(standing),
    )
    name = data["name_resolution"]
    check(
        "board title is not Rainforest",
        name.get("state") == "PARTIAL"
        and name.get("ui_title") == "Blu Zone Restaurant"
        and name.get("stored_display_name") == "Rainforest"
        and name.get("board_title_is_rainforest") is False,
        str(name),
    )
    brand = data["brand_config"]
    check("brand config label kept", brand.get("label") == "Rainforest" and brand.get("present") is True)
    cards = {card["outlet_id"]: card for card in data["cards"]}
    check("six outlets", set(cards) == {spec["outlet_id"] for spec in pre.PREOPEN})
    for outlet_id, card in cards.items():
        template = card["close_template"]
        check(
            f"{outlet_id} blank",
            card.get("status") == "PRE-OPENING"
            and card.get("sales") is None
            and card.get("till") is None
            and card.get("close_count") == 0
            and template.get("inserted") is False
            and template.get("sales") is None
            and template.get("state") == "BLANK",
            str(card),
        )
    restaurant = cards["BZG-RAIN"]
    check("restaurant ui title", restaurant.get("ui_title") == "Blu Zone Restaurant" and restaurant.get("state") == "PARTIAL")
    pool = cards["OU-BZG-RAIN-POOL"]
    check(
        "pool bar under restaurant",
        pool.get("ui_title") == "Pool Bar" and pool.get("parent_outlet_id") == "BZG-RAIN" and data["pool_bar_parent"]["ui_title"] == "Blu Zone Restaurant",
    )
    check("uma stays open", data.get("uma_left_open") == "OPEN")
    page = (ROOT / "dashboards" / "bzg-preopen-config.html").read_text(encoding="utf-8")
    check("page title is not Rainforest", "<title>Pre-open outlets</title>" in page and "Rainforest" not in page.split("<title>", 1)[0])
    check("page has standing name", "Blu Zone Restaurant" in page)
    refused = pre.refuse_write()
    check("refuse write", refused.get("error") == "writes_off" and refused.get("fake_sales") is False)
    check(
        "files unread",
        pre.CATALOG_DB.stat().st_mtime_ns == catalog_mtime
        and pre.CLAUDE_MD.stat().st_mtime_ns == claude_mtime
        and pre.BRAND_CONFIG.stat().st_mtime_ns == brand_mtime,
    )
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
