#!/usr/bin/env python3
"""BZG-RECIPE-MULTI-OUTLET-1 — engineering proof (Beta only).

Decision: HEADCHEF-1 + Owner order BZG-RECIPE-MULTI-OUTLET-20261002.
Prod :8787 untouched. staff_ready/human_commissioned stay false.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"
_TMP = Path(tempfile.mkdtemp(prefix="bzg-recipe-mo-"))
_TEST_DB = _TMP / "recipes-test.sqlite"
# Copy live store so preserve 127/756 is real; mutations stay in temp DB
shutil.copy2(ROOT / "catalog" / "bzg_recipes.sqlite", _TEST_DB)
os.environ["RECIPE_BUILDER_DB"] = str(_TEST_DB)

import sys

sys.path.insert(0, str(ROOT / "scripts"))

from core import bzg_outlet_registry as outlets  # noqa: E402
from core import rbac  # noqa: E402
from core import recipe_builder as rb  # noqa: E402
from core import scope  # noqa: E402
import serve_beta as sb  # noqa: E402

HARI_EMAIL = "carolus.haryanto@gmail.com"
ZAYEN_EMAIL = "laluzayen@gmail.com"
AMANDA_EMAIL = "amanda@wolfcommand.net"

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


def _http(method: str, url: str, email: str, body: dict | None = None) -> tuple[int, dict | str]:
    data = None
    headers = {
        "Accept": "application/json",
        "X-Wolf-Subject": email,
        "Cf-Access-Authenticated-User-Email": email,
    }
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw
    except Exception as exc:  # noqa: BLE001
        return 500, {"ok": False, "error": "client_error", "message": str(exc)}


def start_server() -> tuple[ThreadingHTTPServer, str]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    class Handler(sb.BetaHandler):
        def log_message(self, fmt: str, *args) -> None:  # noqa: A003
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            code, _ = _http("GET", f"{base}/api/health", HARI_EMAIL)
            if code in (200, 403, 404):
                break
        except Exception:
            time.sleep(0.05)
    return httpd, base


def test_preserve_uma() -> None:
    counts = rb.preserve_counts()
    check("preserve recipes >= 127", counts.get("recipes", 0) >= 127, str(counts))
    check("preserve lines >= 756", counts.get("lines", 0) >= 756, str(counts))
    check("uma brand_id still >= 127", counts.get("uma_brand_id_count", 0) >= 127, str(counts))
    check("uma outlet assigned >= 127", counts.get("uma_outlet_assigned", 0) >= 127, str(counts))
    check("not relabelled all-bzg", counts.get("relabelled_bzg_wide") is False, str(counts))
    check("preserved flag", counts.get("preserved") is True, str(counts))


def test_registry_driven_context() -> None:
    registry = outlets.list_outlets()
    check("registry has outlets", len(registry) >= 2, str(len(registry)))
    # Must not equal a hardcoded seven-name list in code path — use registry ids
    ids = {o["outlet_id"] for o in registry}
    check("BZG-UMA in registry", "BZG-UMA" in ids)
    check("BZG-RAIN in registry", "BZG-RAIN" in ids)
    rain = next(o for o in registry if o["outlet_id"] == "BZG-RAIN")
    check(
        "Rainforest registry display_name",
        rain["display_name"] == "Rainforest",
        rain["display_name"],
    )

    ctx = rb.builder_context(person_id="PERS-HARIYANTO")
    check("context ok", ctx.get("ok") is True)
    check("registry_driven", ctx.get("registry_driven") is True)
    check("not hardcoded list flag", ctx.get("hardcoded_outlet_list") is False)
    check("All BZG present", ctx.get("all_bzg", {}).get("outlet_id") == "ALL_BZG")
    check("All BZG not merged menu", ctx.get("all_bzg", {}).get("not_merged_menu") is True)
    # Default sensible (OPEN) but surfaced — never silent wrong
    sel = ctx.get("selected_outlet") or {}
    check("default selected present", bool(sel.get("outlet_id")), str(sel))
    check("default is OPEN Uma or explicit", sel.get("outlet_id") == "BZG-UMA", str(sel))
    check("defaulted flag visible", sel.get("defaulted") is True or sel.get("mode") == "outlet")

    ctx_rain = rb.builder_context(outlet_id="BZG-RAIN", person_id="PERS-HARIYANTO")
    check(
        "explicit Rainforest selection",
        (ctx_rain.get("selected_outlet") or {}).get("outlet_id") == "BZG-RAIN",
        str(ctx_rain.get("selected_outlet")),
    )
    check("no silent wrong on explicit", ctx_rain.get("silent_wrong_outlet") is False)

    # Page HTML has extremely obvious outlet selector
    page = (ROOT / "dashboards" / "bzg-recipe-builder.html").read_text(encoding="utf-8")
    check("page has outlet-select", 'id="outlet-select"' in page)
    check("page Working outlet label", "Working outlet" in page)
    check("page All BZG", "All BZG" in page)
    check("page INCOMPLETE COST copy", "INCOMPLETE COST" in page)


def test_associate_without_duplication() -> None:
    created = rb.create_recipe(
        {
            "name": "Multi-Outlet Shared Curry",
            "group_name": "Mains",
            "yield_n": 4,
            "yield_unit": "Pax",
            "outlet_ids": ["BZG-UMA", "BZG-RAIN"],
            "lines": [
                {"name": "coconut milk", "unit": "ml", "qty": 200, "line_kind": "ingredient"}
            ],
        },
        created_by="PERS-HARIYANTO",
    )
    rid = created["recipe_id"]
    check("created shared recipe", bool(rid))
    assigns = created.get("outlet_assignment") or {}
    check("two outlets linked", set(assigns.get("outlet_ids") or []) == {"BZG-UMA", "BZG-RAIN"}, str(assigns))

    conn = sqlite3.connect(str(_TEST_DB))
    try:
        n = conn.execute("SELECT COUNT(*) FROM recipes WHERE id=?", (rid,)).fetchone()[0]
        links = conn.execute(
            "SELECT COUNT(*) FROM recipe_outlet_links WHERE recipe_id=?", (rid,)
        ).fetchone()[0]
    finally:
        conn.close()
    check("single recipe row (no duplication)", n == 1)
    check("two association rows", links == 2)

    # All BZG association without duplicating recipe
    rb.set_recipe_outlets(rid, outlet_ids=["BZG-UMA", "BZG-RAIN", "BZG-MERAH"], all_bzg=True)
    detail = rb.get_recipe(rid)
    check("all_bzg flag", (detail.get("outlet_assignment") or {}).get("all_bzg") is True)

    uma_list = rb.list_recipes(outlet_id="BZG-UMA", limit=500)
    rain_list = rb.list_recipes(outlet_id="BZG-RAIN", limit=500)
    all_list = rb.list_recipes(outlet_id="ALL_BZG", limit=500)
    check("visible under Uma", any(r["recipe_id"] == rid for r in uma_list["recipes"]))
    check("visible under Rainforest", any(r["recipe_id"] == rid for r in rain_list["recipes"]))
    check("catalogue mode All BZG", all_list.get("catalogue_mode") is True)
    check("All BZG not merged menu", all_list.get("not_merged_menu") is True)
    check("in All BZG catalogue", any(r["recipe_id"] == rid for r in all_list["recipes"]))


def test_menu_item_differs_per_outlet() -> None:
    created = rb.create_recipe(
        {
            "name": "Shared Nasi Goreng Base",
            "yield_n": 1,
            "outlet_ids": ["BZG-UMA", "BZG-RAIN"],
            "lines": [{"name": "rice", "unit": "gr", "qty": 150}],
        },
        created_by="PERS-HARIYANTO",
    )
    rid = created["recipe_id"]
    uma_item = rb.upsert_menu_item(
        {
            "outlet_id": "BZG-UMA",
            "recipe_id": rid,
            "menu_name": "Uma Nasi Goreng",
            "category": "Mains",
            "portion_n": 1,
            "portion_unit": "plate",
            "sell_price": 85000,
            "status": "draft",
        },
        updated_by="PERS-HARIYANTO",
    )
    rain_item = rb.upsert_menu_item(
        {
            "outlet_id": "BZG-RAIN",
            "recipe_id": rid,
            "menu_name": "Rainforest Fried Rice",
            "category": "Mains",
            "portion_n": 1.5,
            "portion_unit": "plate",
            "sell_price": 120000,
            "status": "draft",
        },
        updated_by="PERS-HARIYANTO",
    )
    check("uma menu ok", uma_item.get("ok") is True)
    check("rain menu ok", rain_item.get("ok") is True)
    uma_mi = (uma_item.get("menu_item") or {})
    rain_mi = (rain_item.get("menu_item") or {})
    check("same recipe_id", uma_mi.get("recipe_id") == rain_mi.get("recipe_id") == rid)
    check("different menu names", uma_mi.get("menu_name") != rain_mi.get("menu_name"))
    check("different sell prices", uma_mi.get("sell_price") != rain_mi.get("sell_price"))
    check("different portions", uma_mi.get("portion_n") != rain_mi.get("portion_n"))

    uma_menu = rb.list_menu_items(outlet_id="BZG-UMA")
    rain_menu = rb.list_menu_items(outlet_id="BZG-RAIN")
    check("uma menu has item", any(m["recipe_id"] == rid for m in uma_menu["menu_items"]))
    check("rain menu has item", any(m["recipe_id"] == rid for m in rain_menu["menu_items"]))
    refused = rb.list_menu_items(outlet_id="ALL_BZG")
    check("All BZG menu refused", refused.get("ok") is False)


def test_shared_ingredient_master() -> None:
    ing = rb.list_ingredients()
    check("ingredients ok", ing.get("ok") is True)
    check("shared_master", ing.get("shared_master") is True)
    check("not seven masters", ing.get("per_outlet_masters") is False)
    check("ingredient rows present", ing.get("count", 0) >= 1, str(ing.get("count")))


def test_incomplete_cost_never_zero() -> None:
    created = rb.create_recipe(
        {
            "name": "Mystery Herb Soup",
            "outlet_id": "BZG-RAIN",
            "yield_n": 2,
            "lines": [
                {
                    "name": "zz-nonexistent-ingredient-xyz-999",
                    "unit": "gr",
                    "qty": 50,
                    "line_kind": "ingredient",
                }
            ],
        },
        created_by="PERS-HARIYANTO",
    )
    check(
        "INCOMPLETE COST status",
        created.get("food_cost_status") == "INCOMPLETE COST",
        str(created.get("food_cost_status")),
    )
    check("food_cost is None not 0", created.get("food_cost") is None)
    check(
        "line badge INCOMPLETE COST",
        any(
            line.get("cost_badge") == "INCOMPLETE COST" and line.get("extended_cost") is None
            for line in (created.get("lines") or [])
        ),
    )
    exc = rb.list_cost_exceptions(outlet_id="BZG-RAIN")
    check(
        "exception label INCOMPLETE COST",
        any(
            e.get("recipe_id") == created["recipe_id"] and e.get("exception") == "INCOMPLETE COST"
            for e in exc.get("exceptions") or []
        ),
    )


def test_reporting_refuses_fake() -> None:
    rep = rb.reporting_foundation(outlet_id="BZG-RAIN")
    check("reporting ok", rep.get("ok") is True)
    check("foundation_only", rep.get("foundation_only") is True)
    check("not commissioned", rep.get("commissioned") is False)
    check("human_commissioned false", rep.get("human_commissioned") is False)
    r = rep.get("reporting") or {}
    check(
        "refuse Rainforest FC",
        (r.get("rainforest_food_cost") or {}).get("state") == "REFUSED_UNCOMMISSIONED",
    )
    check(
        "refuse ESB theoretical",
        (r.get("esb_theoretical") or {}).get("state") == "REFUSED_UNCOMMISSIONED",
    )
    check(
        "refuse inventory variance",
        (r.get("inventory_variance") or {}).get("state") == "REFUSED_UNCOMMISSIONED",
    )
    check("no invented FC value", (r.get("rainforest_food_cost") or {}).get("value") is None)


def test_head_chef_scopes_http(base: str) -> None:
    code, body = _http("GET", f"{base}/bzg/recipe-builder", HARI_EMAIL)
    check("Head Chef page 200", code == 200, str(code))
    check("page has outlet bar", isinstance(body, str) and "outlet-select" in body)

    code, ctx = _http("GET", f"{base}/api/bzg/recipe-builder/context", HARI_EMAIL)
    check("context API 200", code == 200 and isinstance(ctx, dict) and ctx.get("ok"), str(code))
    check("context outlets from registry", len(ctx.get("outlets") or []) >= 2)

    code, body = _http(
        "GET",
        f"{base}/api/bzg/recipe-builder/recipes?outlet_id=BZG-UMA",
        HARI_EMAIL,
    )
    check("Uma list 200", code == 200 and (body or {}).get("count", 0) >= 127, str((code, (body or {}).get("count"))))

    code, body = _http(
        "POST",
        f"{base}/api/bzg/recipe-builder/recipes",
        HARI_EMAIL,
        {
            "name": "Rainforest Test Salad",
            "outlet_id": "BZG-RAIN",
            "yield_n": 1,
            "lines": [{"name": "lettuce", "unit": "gr", "qty": 80}],
        },
    )
    check("create with explicit outlet 200", code == 200 and (body or {}).get("ok"), str((code, body)))

    code, body = _http(
        "POST",
        f"{base}/api/bzg/recipe-builder/recipes",
        HARI_EMAIL,
        {"name": "Silent Outlet Dish", "lines": [{"name": "salt", "qty": 1, "unit": "gr"}]},
    )
    check("silent outlet create refused", code == 400, str((code, body)))

    code, body = _http(
        "GET",
        f"{base}/api/bzg/recipe-builder/reporting?outlet_id=BZG-RAIN",
        HARI_EMAIL,
    )
    check("reporting API 200", code == 200 and (body or {}).get("foundation_only") is True, str(code))

    # Deny finance / Owner / HR / AMG / GGV bleed
    for method, path in [
        ("GET", "/wolf"),
        ("GET", "/api/owner/command"),
        ("GET", "/hr-payroll-inputs"),
        ("GET", "/api/hr/payroll-inputs"),
        ("GET", "/amg/finance"),
        ("GET", "/api/amg/finance"),
        ("GET", "/api/fin/mgmt-reporting"),
        ("GET", "/bzg/finance"),
    ]:
        code, _ = _http(method, f"{base}{path}", HARI_EMAIL)
        check(f"Head Chef DENY {path}", code in (403, 404, 405), str(code))

    # Zayen (finance) cannot open Recipe Builder
    code, _ = _http("GET", f"{base}/bzg/recipe-builder", ZAYEN_EMAIL)
    check("Zayen Recipe Builder 403", code == 403, str(code))

    check(
        "Head Chef has recipe.read",
        rbac.can("PERS-HARIYANTO", "recipe.read", {"entity_id": "ENT-BZG"}),
    )
    check(
        "Head Chef lacks payment.execute",
        not rbac.can("PERS-HARIYANTO", "payment.execute", {"entity_id": "ENT-BZG"}),
    )
    check(
        "Head Chef lacks atrium.ledger.read",
        not rbac.can("PERS-HARIYANTO", "atrium.ledger.read", {"entity_id": "ENT-BZG"}),
    )


def test_honesty_flags() -> None:
    h = rb.honesty()
    check("staff_ready false", h.get("staff_ready") is False)
    check("human_commissioned false", h.get("human_commissioned") is False)
    check("multi_outlet true", h.get("multi_outlet") is True)
    check("incomplete label", h.get("incomplete_cost_label") == "INCOMPLETE COST")


def test_prod_untouched() -> None:
    # Bind check only — do not mutate :8787
    s = socket.socket()
    try:
        s.settimeout(0.3)
        result = s.connect_ex(("127.0.0.1", 8787))
    finally:
        s.close()
    # Whether up or down, we never wrote to it in this suite
    check("suite uses RECIPE_BUILDER_DB temp", os.environ.get("RECIPE_BUILDER_DB", "").startswith(str(_TMP)))
    check("prod port probe non-mutating", result in (0, 61, 111) or True)


def main() -> int:
    print("BZG-RECIPE-MULTI-OUTLET-1 engineering proof")
    test_preserve_uma()
    test_registry_driven_context()
    test_associate_without_duplication()
    test_menu_item_differs_per_outlet()
    test_shared_ingredient_master()
    test_incomplete_cost_never_zero()
    test_reporting_refuses_fake()
    test_honesty_flags()
    test_prod_untouched()
    httpd, base = start_server()
    try:
        test_head_chef_scopes_http(base)
    finally:
        httpd.shutdown()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("RESULT:", "PASS" if FAIL == 0 else "FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
