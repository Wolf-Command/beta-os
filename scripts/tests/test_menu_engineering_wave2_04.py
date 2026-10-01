#!/usr/bin/env python3
"""Wave 2.04 — menu classes stay unassigned when usage is not joined."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import menu_engineering_wave2_04 as menu  # noqa: E402

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
    recipe_mtime = menu.RECIPES_DB.stat().st_mtime_ns
    esb_mtime = menu.ESB_DB.stat().st_mtime_ns
    v1_mtime = menu.V1_RECIPES_DB.stat().st_mtime_ns
    data = menu.load_engineering()
    check(
        "staff not ready",
        data.get("staff_ready") is False
        and data.get("human_proven") is False
        and data.get("writes") is False
        and data.get("scores_written") is False
        and data.get("state") == "PARTIAL",
    )
    recipes = data["recipes"]
    check(
        "recipes copied",
        recipes.get("recipes") == 127
        and recipes.get("lines") == 756
        and recipes.get("with_lines") == 127
        and recipes.get("esb_menu_links") == 0,
        str({k: recipes.get(k) for k in ("recipes", "lines", "with_lines", "esb_menu_links")}),
    )
    check(
        "line cost is stored not scored",
        recipes.get("cost_complete") == 108
        and recipes.get("cost_partial") == 2
        and recipes.get("cost_missing") == 17
        and recipes.get("line_cost_present") == 628
        and recipes.get("line_cost_zero") == 0
        and recipes.get("line_cost_missing") == 128
        and recipes.get("cost_source_card") == 628
        and recipes.get("cost_source_manual") == 2
        and recipes.get("cost_source_missing") == 126
        and recipes.get("stored_target_cos_rows") == 127
        and recipes.get("stored_real_sell_rows") == 107,
        str(recipes),
    )
    compare = data["recipe_compare"]
    check("compare table empty", compare.get("present") is True and compare.get("count") == 0)
    mix = data["product_mix"]
    check(
        "mix is quantity only",
        mix.get("real") is True
        and mix.get("day") == "2026-09-30"
        and mix.get("branch") == "BLZ"
        and mix.get("menu_count") == 76
        and mix.get("qty_sum") == 292.0
        and mix.get("amounts_copied") is False
        and "items" not in mix
        and "amount" not in mix
        and "total" not in mix,
        str(mix),
    )
    join = data["name_join"]
    check(
        "name join is partial",
        join.get("matched") == 26
        and join.get("ambiguous") == 0
        and join.get("matched_cost_complete") == 23
        and join.get("matched_cost_missing") == 3
        and join.get("unmatched_menus") == 50,
        str(join),
    )
    usage = data["usage"]
    check(
        "usage not joined",
        usage.get("joined") is False and usage.get("row_count") == 160 and usage.get("day") == "2026-09-30",
        str(usage),
    )
    contribution = data["contribution"]
    check(
        "contribution unavailable",
        contribution.get("state") == "UNAVAILABLE"
        and contribution.get("margin_pct") is None
        and contribution.get("amount") is None,
        str(contribution),
    )
    quadrants = data["quadrants"]
    check(
        "no classes",
        quadrants.get("drawn") is False
        and quadrants.get("stars") is None
        and quadrants.get("plowhorses") is None
        and quadrants.get("puzzles") is None
        and quadrants.get("dogs") is None,
        str(quadrants),
    )
    page = (ROOT / "dashboards" / "uma-menu-engineering.html").read_text(encoding="utf-8")
    check("page title", "<title>Menu engineering</title>" in page)
    check("tiles start closed", page.count("<details>") >= 4 and "<details open" not in page)
    check("page assigns no class", "No class was assigned" in page)
    refused = menu.refuse_write()
    check(
        "refuse write",
        refused.get("error") == "writes_off" and refused.get("scores_written") is False,
    )
    check(
        "files unread",
        menu.RECIPES_DB.stat().st_mtime_ns == recipe_mtime
        and menu.ESB_DB.stat().st_mtime_ns == esb_mtime
        and menu.V1_RECIPES_DB.stat().st_mtime_ns == v1_mtime,
    )
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
