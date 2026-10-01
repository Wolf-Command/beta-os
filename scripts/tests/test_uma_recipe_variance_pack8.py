#!/usr/bin/env python3
"""Pack 8 — recipe variance stays unknown unless actuals are joined."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import uma_recipe_variance_pack8 as var  # noqa: E402

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
    recipe_mtime = var.RECIPES_DB.stat().st_mtime_ns
    esb_mtime = var.ESB_DB.stat().st_mtime_ns
    catalog_mtime = var.CATALOG_DB.stat().st_mtime_ns
    v1_mtime = var.V1_RECIPES_DB.stat().st_mtime_ns
    data = var.load_variance()
    check("staff not ready", data.get("staff_ready") is False and data.get("human_proven") is False)
    check("esb write off", data.get("esb_write") is False and data.get("yield_invented") is False)
    recipes = data["recipes"]
    check(
        "recipes with lines",
        recipes.get("recipes") == 127 and recipes.get("lines") == 756 and recipes.get("with_lines") == 127,
        str(recipes),
    )
    compare = data["recipe_compare"]
    check("compare table empty", compare.get("count") == 0 and compare.get("present") is True)
    mix = data["product_mix"]
    check(
        "product mix real",
        mix.get("real") is True
        and mix.get("day") == "2026-09-30"
        and mix.get("branch") == "BLZ"
        and mix.get("menu_count") == 76
        and mix.get("qty_sum") == 292.0,
        str(mix),
    )
    theoretical = data["theoretical"]
    sample = theoretical.get("sample") or []
    check(
        "theoretical is partial",
        theoretical.get("state") == "PARTIAL" and theoretical.get("matched_recipes", 0) > 0 and len(sample) <= 8,
        str(theoretical.get("matched_recipes")),
    )
    example = sample[0]
    expected = round(float(example["sold_qty"]) * float(example["example_line_qty"]), 4)
    check(
        "example is sold times stored qty",
        example.get("example_theoretical_qty") == expected and example.get("variance_qty") is None,
        str(example),
    )
    variance = data["variance"]
    check(
        "variance unknown",
        variance.get("state") == "UNKNOWN" and variance.get("amount") is None and variance.get("qty") is None and variance.get("yield_invented") is False,
        str(variance),
    )
    actual = data["actual"]
    check(
        "usage not joined",
        actual.get("joined") is False and actual.get("row_count") == 160 and actual.get("day") == "2026-09-30",
        str(actual),
    )
    close = data["pack2_close"]
    check(
        "pack 2 close cited",
        close.get("close_id") == var.PACK2_CLOSE
        and close.get("business_date") == "2026-09-30"
        and close.get("state") == "DATA_CAPTURED"
        and close.get("finished_count") == 50
        and close.get("policies") == 0
        and close.get("declared_cash_evidence_id") is None,
        str(close),
    )
    check("desk href", data.get("desk_href") == "/bzg/uma-blu/recipes")
    refused = var.refuse_write()
    check("refuse write", refused.get("error") == "writes_off" and refused.get("esb_write") is False)
    check(
        "files unread",
        var.RECIPES_DB.stat().st_mtime_ns == recipe_mtime
        and var.ESB_DB.stat().st_mtime_ns == esb_mtime
        and var.CATALOG_DB.stat().st_mtime_ns == catalog_mtime
        and var.V1_RECIPES_DB.stat().st_mtime_ns == v1_mtime,
    )
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
