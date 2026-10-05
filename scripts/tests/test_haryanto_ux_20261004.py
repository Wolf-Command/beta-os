#!/usr/bin/env python3
"""HARYANTO-UX — Recipe Builder human-test repair proofs (temp sqlite only)."""
from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"
_TMP = Path(tempfile.mkdtemp(prefix="haryanto-ux-"))
_TEST_RECIPES = _TMP / "recipes-test.sqlite"
_TEST_CATALOG = _TMP / "content-test.sqlite"
shutil.copy2(ROOT / "catalog" / "bzg_recipes.sqlite", _TEST_RECIPES)
os.environ["RECIPE_BUILDER_DB"] = str(_TEST_RECIPES)

import sys

sys.path.insert(0, str(ROOT / "scripts"))

from core import bzg_outlet_registry as outlets  # noqa: E402
from core import rbac  # noqa: E402
from core import recipe_builder as rb  # noqa: E402
from core import wolf_shell as ws  # noqa: E402
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
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    outlets.seed_registry(conn, ts)
    conn.commit()
    conn.close()


def test_outlet_seed_and_registry() -> None:
    seed = {row["outlet_id"]: row["status"] for row in outlets.SEED}
    check("seed Uma OPEN", seed.get("BZG-UMA") == "OPEN")
    check("seed Rainforest OPEN", seed.get("BZG-RAIN") == "OPEN")
    check("seed Pool Bar OPEN", seed.get("OU-BZG-RAIN-POOL") == "OPEN")
    check("seed Merah PRE-OPENING", seed.get("BZG-MERAH") == "PRE-OPENING")
    check("seed Rooftop PRE-OPENING", seed.get("BZG-ROOF") == "PRE-OPENING")
    check("seed Room Service PRE-OPENING", seed.get("BZG-RS") == "PRE-OPENING")
    check("seed Catering PRE-OPENING", seed.get("BZG-CAT") == "PRE-OPENING")

    _seed_test_catalog()
    conn = sqlite3.connect(str(_TEST_CATALOG))
    try:
        rows = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT outlet_id, status FROM org_outlet_registry ORDER BY outlet_id"
            )
        }
    finally:
        conn.close()
    check("temp registry Rainforest OPEN", rows.get("BZG-RAIN") == "OPEN", str(rows))
    check("temp registry Pool Bar OPEN", rows.get("OU-BZG-RAIN-POOL") == "OPEN", str(rows))
    check("temp registry Uma still OPEN", rows.get("BZG-UMA") == "OPEN", str(rows))


def test_ingredient_search() -> None:
    pack_c = rb.search_ingredients(query="c", limit=50)
    names_c = [str(i.get("name") or "").lower() for i in pack_c.get("ingredients") or []]
    check("search c returns capsicum", any(n == "capsicum" or "capsicum" in n for n in names_c), str(names_c[:12]))
    check("search c returns celery stick", any("celery stick" in n for n in names_c), str(names_c[:12]))

    pack_ca = rb.search_ingredients(query="ca", limit=30)
    names_ca = [str(i.get("name") or "").lower() for i in pack_ca.get("ingredients") or []]
    check("search ca returns capsicum", any("capsicum" in n for n in names_ca), str(names_ca[:10]))

    pack = rb.search_ingredients(query="car", limit=20)
    names = [str(i.get("name") or "").lower() for i in pack.get("ingredients") or []]
    check("search car returns carrot", any("carrot" in n for n in names), str(names[:8]))
    check("search car returns caramelized onion", any("caramelized onion" in n for n in names), str(names[:8]))
    check("search car narrows vs c", len(names) <= len(names_c))

    exact = rb.search_ingredients(query="carrot", limit=5)
    top = (exact.get("ingredients") or [None])[0]
    check("exact carrot ranks first", top and str(top.get("name")).lower() == "carrot", str(top))

    conn = rb.connect(writable=True)
    try:
        before = conn.execute("SELECT COUNT(*) FROM ingredient_master").fetchone()[0]
    finally:
        conn.close()
    unknown = rb.search_ingredients(query="zzznomatchxyz", limit=5)
    check("unknown query no_match", unknown.get("no_match") is True)
    conn = rb.connect(writable=True)
    try:
        after = conn.execute("SELECT COUNT(*) FROM ingredient_master").fetchone()[0]
    finally:
        conn.close()
    check("search did not insert master rows", before == after, f"{before} vs {after}")

    null_row = next(
        (
            i
            for i in rb.list_ingredients().get("ingredients") or []
            if i.get("purchase_cost") is None
        ),
        None,
    )
    if null_row:
        check(
            "null cost not coerced to zero",
            null_row.get("purchase_cost") is None and null_row.get("cost_status") == "INCOMPLETE COST",
        )
    else:
        check("null cost fixture present", False, "no null-cost ingredient in temp master")


def test_save_binds_ingredient_id() -> None:
    carrot = rb.search_ingredients(query="carrot", limit=1)["ingredients"][0]
    created = rb.create_recipe(
        {
            "name": "HARYANTO-UX Bind Test",
            "yield_n": 1,
            "yield_unit": "Pax",
            "outlet_ids": ["BZG-RAIN"],
            "lines": [
                {
                    "ingredient_id": carrot["id"],
                    "name": carrot["name"],
                    "qty": 10,
                    "unit": carrot.get("default_unit") or "gr",
                }
            ],
        },
        created_by="PERS-HARIYANTO",
    )
    rid = created["recipe_id"]
    conn = rb.connect(writable=True)
    try:
        row = conn.execute(
            "SELECT ingredient_id, name, unit_cost FROM recipe_lines WHERE recipe_id=?",
            (rid,),
        ).fetchone()
    finally:
        conn.close()
    check("line stores ingredient_id", row and row[0] == carrot["id"], str(row))
    check("line keeps human name", row and row[1] == carrot["name"], str(row))
    if carrot.get("purchase_cost") is None:
        check("null master cost stored null not 0", row and row[2] is None, str(row))
    dup_denied = False
    try:
        rb.update_recipe(
            rid,
            {
                "lines": [
                    {
                        "ingredient_id": carrot["id"],
                        "name": carrot["name"],
                        "qty": 5,
                        "unit": "gr",
                    },
                    {
                        "ingredient_id": carrot["id"],
                        "name": carrot["name"],
                        "qty": 2,
                        "unit": "gr",
                    },
                ]
            },
            updated_by="PERS-HARIYANTO",
        )
    except ValueError:
        dup_denied = True
    check("duplicate ingredient blocked", dup_denied)


def test_head_chef_nav_and_rbac() -> None:
    check(
        "no venue.close.read",
        not rbac.can("PERS-HARIYANTO", "venue.close.read", {"entity_id": "ENT-BZG"}),
    )
    aud = ws.audience_for_person("PERS-HARIYANTO")
    pages = set(ws.pages_for_audience(aud))
    check("Head Chef audience", aud == "HEAD_CHEF", aud)
    check("pages exclude uma-blu close", "/bzg/uma-blu" not in pages, str(sorted(pages)))
    check("pages include recipe-builder", "/bzg/recipe-builder" in pages)

    who = ws.build_whoami(person_id="PERS-HARIYANTO", email=HARI_EMAIL)
    allowed = set(ws.filter_hrefs(who))
    check("filter_hrefs exclude uma-blu", "/bzg/uma-blu" not in allowed, str(sorted(allowed)))
    children = ws.outlet_children_for_whoami(who)
    hrefs = [str(c.get("href") or "") for c in children]
    check("outlet strip has no uma-blu href", not any(h.startswith("/bzg/uma-blu") for h in hrefs), str(hrefs))


def test_http_builder(base: str) -> None:
    code, body = _http("GET", f"{base}/bzg/recipe-builder", HARI_EMAIL)
    check("builder page 200", code == 200)
    check("page has combobox", isinstance(body, str) and "combo-options" in body and "l-ingredient-id" in body)

    code, ing = _http("GET", f"{base}/api/bzg/recipe-builder/ingredients?q=car", HARI_EMAIL)
    check("ingredient search API", code == 200 and (ing or {}).get("count", 0) >= 1, str(code))

    code, menu = _http(
        "GET",
        f"{base}/api/bzg/recipe-builder/menu-items?outlet_id=BZG-RAIN",
        HARI_EMAIL,
    )
    check("rain menu honest empty", code == 200 and (menu or {}).get("count") == 0)
    truth = (menu or {}).get("outlet_truth") or {}
    check(
        "rain menu truth message",
        "no menu items" in str(truth.get("message") or "").lower(),
        str(truth),
    )

    code, _ = _http("GET", f"{base}/bzg/uma-blu", HARI_EMAIL)
    check("uma-blu still denied", code in (403, 404), str(code))


def main() -> int:
    print("HARYANTO-UX tests — temp dirs:", _TMP)
    test_outlet_seed_and_registry()
    test_ingredient_search()
    test_save_binds_ingredient_id()
    test_head_chef_nav_and_rbac()
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
