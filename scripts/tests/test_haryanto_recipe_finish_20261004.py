#!/usr/bin/env python3
"""HARYANTO-RECIPE-FINISH — Recipe Builder bug-test readiness proofs (temp sqlite only)."""
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
_TMP = Path(tempfile.mkdtemp(prefix="haryanto-recipe-finish-"))
_TEST_RECIPES = _TMP / "recipes-test.sqlite"
_TEST_CATALOG = _TMP / "content-test.sqlite"
shutil.copy2(ROOT / "catalog" / "bzg_recipes.sqlite", _TEST_RECIPES)
os.environ["RECIPE_BUILDER_DB"] = str(_TEST_RECIPES)

import sys

sys.path.insert(0, str(ROOT / "scripts"))

from core import bzg_outlet_registry as outlets  # noqa: E402
from core import rbac  # noqa: E402
from core import recipe_builder as rb  # noqa: E402
import serve_beta as sb  # noqa: E402

HARI_EMAIL = "carolus.haryanto@gmail.com"

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


def start_server() -> tuple[ThreadingHTTPServer, str]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    class Handler(sb.BetaHandler):
        def log_message(self, fmt: str, *args) -> None:  # noqa: A003
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            code, _ = _http("GET", f"{base}/api/health", HARI_EMAIL)
            if code in (200, 403):
                break
        except Exception:
            time.sleep(0.05)
    return httpd, base


def _seed_test_catalog() -> None:
    live = sqlite3.connect(str(ROOT / "catalog" / "content_library.sqlite"))
    live.backup(sqlite3.connect(str(_TEST_CATALOG)))
    live.close()
    conn = sqlite3.connect(str(_TEST_CATALOG))
    ts = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    outlets.seed_registry(conn, ts)
    conn.commit()
    conn.close()


def test_uma_recipe_opens_and_cost_honest() -> None:
    pack = rb.list_recipes(outlet_id="BZG-UMA", limit=5)
    check("uma has recipes", pack.get("count", 0) >= 1, str(pack.get("count")))
    first = (pack.get("recipes") or [None])[0]
    check("first recipe present", first is not None)
    if not first:
        return
    rid = first["recipe_id"]
    detail = rb.get_recipe(rid)
    check("recipe opens", detail is not None and detail.get("name"))
    if detail.get("food_cost_status") == "COMPLETE":
        check("known cost is numeric", isinstance(detail.get("food_cost"), (int, float)))
    else:
        check("missing cost not invented", detail.get("food_cost") is None)


def test_save_qty_unit_persists() -> None:
    uma = rb.list_recipes(outlet_id="BZG-UMA", limit=1)
    rid = uma["recipes"][0]["recipe_id"]
    carrot = rb.search_ingredients(query="carrot", limit=1)["ingredients"][0]
    qty = 42.5
    unit = carrot.get("default_unit") or "gr"
    rb.update_recipe(
        rid,
        {
            "lines": [
                {
                    "ingredient_id": carrot["id"],
                    "name": carrot["name"],
                    "qty": qty,
                    "unit": unit,
                    "line_kind": "ingredient",
                }
            ]
        },
        updated_by="PERS-HARIYANTO",
    )
    reloaded = rb.get_recipe(rid)
    line = next((l for l in reloaded["lines"] if l.get("name") == carrot["name"]), None)
    check("reload keeps qty", line and float(line.get("qty") or 0) == qty, str(line))
    check("reload keeps unit", line and line.get("unit") == unit, str(line))
    if carrot.get("purchase_cost") is not None:
        check(
            "stored cost used",
            line and line.get("extended_cost") is not None,
            str(line.get("extended_cost") if line else None),
        )
    else:
        check(
            "null master cost stays unknown",
            line and line.get("extended_cost") is None,
            str(line),
        )


def test_outlet_registry_honest_empty() -> None:
    rain = rb.list_recipes(outlet_id="BZG-RAIN", limit=5)
    pool = rb.list_recipes(outlet_id="OU-BZG-RAIN-POOL", limit=5)
    check("rainforest no copied recipes", rain.get("count") == 0, str(rain.get("count")))
    check("pool bar no copied recipes", pool.get("count") == 0, str(pool.get("count")))
    rain_menu = rb.list_menu_items(outlet_id="BZG-RAIN")
    pool_menu = rb.list_menu_items(outlet_id="OU-BZG-RAIN-POOL")
    check("rainforest menu empty", rain_menu.get("count") == 0)
    check("pool bar menu empty", pool_menu.get("count") == 0)


def test_head_chef_access_without_work_update() -> None:
    check(
        "recipe.read allowed",
        rbac.can("PERS-HARIYANTO", "recipe.read", {"entity_id": "ENT-BZG"}),
    )
    check(
        "recipe.edit allowed",
        rbac.can("PERS-HARIYANTO", "recipe.edit", {"entity_id": "ENT-BZG"}),
    )
    check(
        "work.update denied",
        not rbac.can("PERS-HARIYANTO", "work.update", {"entity_id": "ENT-BZG"}),
    )


def test_staff_page_copy() -> None:
    page = (ROOT / "dashboards" / "bzg-recipe-builder.html").read_text(encoding="utf-8")
    check("staff cost unknown copy", "Cost unknown" in page)
    check("no GL on page", "GL " not in page and "general ledger" not in page.lower())
    check("no journal labels", "journal" not in page.lower())
    check("no account code labels", "account code" not in page.lower())
    check("desktop width cap", "max-width: 960px" in page)
    check("ingredient combobox present", "combo-options" in page and "l-ingredient-id" in page)


def test_http_builder(base: str) -> None:
    code, body = _http("GET", f"{base}/bzg/recipe-builder", HARI_EMAIL)
    check("builder page not access denied", code == 200, str(code))
    check(
        "page not narrow access card",
        isinstance(body, str) and "Access denied" not in body,
    )
    check("page cost unknown copy", isinstance(body, str) and "Cost unknown" in body)

    code, pack = _http(
        "GET",
        f"{base}/api/bzg/recipe-builder/recipes?outlet_id=BZG-UMA&limit=1",
        HARI_EMAIL,
    )
    check("list recipes api", code == 200 and (pack or {}).get("count", 0) >= 1, str(code))
    rid = ((pack or {}).get("recipes") or [{}])[0].get("recipe_id")
    if rid:
        code, detail = _http("GET", f"{base}/api/bzg/recipe-builder/recipes/{rid}", HARI_EMAIL)
        check("open recipe api", code == 200, str(code))

    code, menu = _http(
        "GET",
        f"{base}/api/bzg/recipe-builder/menu-items?outlet_id=BZG-RAIN",
        HARI_EMAIL,
    )
    check("menu tab honest empty", code == 200 and (menu or {}).get("count") == 0)


def main() -> int:
    print("HARYANTO-RECIPE-FINISH tests — temp dirs:", _TMP)
    _seed_test_catalog()
    rb.connect(writable=True).close()  # run migrations + backfill on temp db
    conn = rb.connect()
    try:
        with_id = conn.execute(
            "SELECT COUNT(*) FROM recipe_lines WHERE ingredient_id IS NOT NULL"
        ).fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM recipe_lines").fetchone()[0]
    finally:
        conn.close()
    check("ingredient_id backfill progressed", with_id > 13, f"{with_id}/{total}")

    test_uma_recipe_opens_and_cost_honest()
    test_save_qty_unit_persists()
    test_outlet_registry_honest_empty()
    test_head_chef_access_without_work_update()
    test_staff_page_copy()
    httpd, base = start_server()
    try:
        test_http_builder(base)
    finally:
        httpd.shutdown()
    try:
        shutil.rmtree(_TMP)
    except OSError:
        pass
    print(f"\nSUMMARY  pass={PASS}  fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
