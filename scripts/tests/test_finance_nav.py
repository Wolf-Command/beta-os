#!/usr/bin/env python3
"""Shared Finance navigation: one vocabulary, separate company routes."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import finance_nav  # noqa: E402
from core import ggv_finance_nota as nota  # noqa: E402

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


def hrefs(entity: str) -> list[str]:
    found = []
    for area in finance_nav.catalog(entity):
        for item in area["items"]:
            found.append(item["href"])
    return found


def main() -> int:
    labels = list(finance_nav.PRIMARY_LABELS)
    check("ten areas", len(labels) == 10 and labels[0] == "Overview" and labels[-1] == "Reports")
    for entity in ("ENT-GGV", "ENT-AMG", "ENT-BZG"):
        got = [area["label"] for area in finance_nav.catalog(entity)]
        check(f"{entity} uses the shared labels", got == labels, str(got))
    ggv = " ".join(hrefs("ENT-GGV"))
    amg = " ".join(hrefs("ENT-AMG"))
    bzg = " ".join(hrefs("ENT-BZG"))
    check("ggv keeps september desk", "/ggv/finance/accountant" in ggv and "/ggv/finance/receipts" in ggv)
    check("amg keeps the hotel ledger", "/amg/finance/journals" in amg and "/amg/finance/accounts" in amg)
    check("bzg keeps purchasing and close", "/bzg/uma-blu/purchase-orders" in bzg and "/uma-blu-close" in bzg)
    check("ggv nav has no amg route", "/amg/" not in ggv and "/bzg/" not in ggv)
    check("amg nav has no ggv route", "/ggv/" not in amg)
    check("bzg nav has no ggv route", "/ggv/" not in bzg)
    all_hrefs = hrefs("ENT-GGV") + hrefs("ENT-AMG") + hrefs("ENT-BZG")
    unsafe = [
        href
        for href in all_hrefs
        if href.rstrip("/").endswith("/pay") or href.rstrip("/").endswith("/post") or "/payments" in href
    ]
    check("nav does not pay or post", unsafe == [], str(unsafe))
    from core import entity_books

    check(
        "book files stay separate",
        len(set(entity_books.ENTITY_FILES.values())) == 3,
        str(entity_books.ENTITY_FILES),
    )
    operator = finance_nav.visible_areas("ENT-GGV", {"finance.nota.read"})
    visible = [item["id"] for area in operator for item in area["items"]]
    check("operator still sees banking", "ggv-banking" in visible)
    check("operator without accountant grant skips tax", "ggv-tax" not in visible)
    check("ten labels remain when items are hidden", [area["label"] for area in operator] == labels)
    try:
        finance_nav.catalog("ENT-OTHER")
        check("unknown company refused", False)
    except finance_nav.FinanceNavError as exc:
        check("unknown company refused", exc.http_status == 404)
    check("nav api is shell chrome", "/api/finance/nav" in nota.SHELL_CHROME_PATHS)
    check("nav script is shell chrome", "/shared/finance-nav.js" in nota.SHELL_CHROME_PATHS)
    for name in (
        "dashboards/ggv-finance.html",
        "dashboards/amg-finance-ops.html",
        "dashboards/amg-finance.html",
        "dashboards/bzg-finance.html",
    ):
        text = (ROOT / name).read_text(encoding="utf-8")
        check(f"{name} mounts shared nav", 'id="wolf-finance-nav"' in text and "finance-nav.js" in text)
        check(f"{name} keeps the previous navigation", "legacy-finance-tabs" in text)
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
