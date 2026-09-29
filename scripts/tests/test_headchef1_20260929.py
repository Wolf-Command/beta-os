#!/usr/bin/env python3
"""HEADCHEF-1 — Hariyanto Recipe Builder allow/deny + Maciej auth-only + regression."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ["WOLF_TEST_MODE"] = "1"
os.environ["BETA_AUTH_MODE"] = "development_assertion"
_TMP = Path(tempfile.mkdtemp(prefix="headchef1-"))
os.environ["RECIPE_BUILDER_DB"] = str(_TMP / "recipes-test.sqlite")

import sys

sys.path.insert(0, str(ROOT / "scripts"))

from core import identity  # noqa: E402
from core import rbac  # noqa: E402
from core import recipe_builder as rb  # noqa: E402
from core import scope  # noqa: E402
from core import universal_my_work as umw  # noqa: E402
from core.staff_home import build_home  # noqa: E402
import serve_beta as sb  # noqa: E402

HARI_EMAIL = "carolus.haryanto@gmail.com"
MACIEJ_EMAIL = "barefeet14@hotmail.com"
DEVI_EMAIL = "deviputu236@gmail.com"
ZAYEN_EMAIL = "laluzayen@gmail.com"
HAIKAL_EMAIL = "haikalqilbari123@gmail.com"
YUDI_EMAIL = "widiatmika.11@gmail.com"

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
    except Exception as exc:  # noqa: BLE001 — fail-closed network / handler crash
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
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    # wait ready
    for _ in range(50):
        try:
            code, _ = _http("GET", f"{base}/api/health", HARI_EMAIL)
            if code in (200, 403):
                break
        except Exception:
            time.sleep(0.05)
    return httpd, base


def test_identity_and_rbac() -> None:
    hari = identity.resolve_person_from_email(HARI_EMAIL)
    check("Hariyanto person exists", hari is not None and hari["person_id"] == "PERS-HARIYANTO")
    check("display Hariyanto", hari and hari["display_name"] == "Hariyanto")
    check("legal Carolus Haryanto", hari and hari.get("legal_name") == "Carolus Haryanto")

    conn = sqlite3.connect(str(ROOT / "catalog" / "content_library.sqlite"))
    try:
        owners = conn.execute(
            """
            SELECT person_id FROM org_auth_identities
            WHERE provider='email' AND lower(identifier)=?
            """,
            (HARI_EMAIL,),
        ).fetchall()
        check("email unique to Hariyanto", len(owners) == 1 and owners[0][0] == "PERS-HARIYANTO")
        brand = conn.execute(
            "SELECT brand_id FROM org_positions WHERE position_id='POS-BZG-HEAD-CHEF-1'"
        ).fetchone()
        check("position not outlet-tied", brand is not None and brand[0] is None)
        allowed = {
            r[0]
            for r in conn.execute(
                """
                SELECT p.code FROM org_role_permissions rp
                JOIN org_permissions p ON p.permission_id=rp.permission_id
                WHERE rp.role_id='ROLE-BZG-HEAD-CHEF' AND rp.effect='ALLOW'
                """
            )
        }
    finally:
        conn.close()

    for code in (
        "recipe.read",
        "recipe.create",
        "recipe.edit",
        "recipe.cost.read",
        "ingredient.read",
        "menu.price.read",
        "supplier.product.read",
        "recipe.exceptions.read",
        "work.read",
    ):
        check(
            f"ALLOW {code}",
            code in allowed and rbac.can("PERS-HARIYANTO", code, {"entity_id": "ENT-BZG"}),
        )

    for code in (
        "payment.approve",
        "payment.execute",
        "vendor.bank.change",
        "bzg.pr.payment_approve",
        "progress.read",
        "organisation.role.read",
        "organisation.person.read",
        "approval.decide",
        "venue.close.verify",
        "atrium.ledger.read",
        "finance.nota.read",
        "finance.invoice.read",
    ):
        check(
            f"DENY {code}",
            code not in allowed
            and not rbac.can("PERS-HARIYANTO", code, {"entity_id": "ENT-BZG"}),
        )

    ctx = scope.resolve_effective_scope_context("SCOPE-BZG-FB")
    brands = (ctx.get("structurally_covered") or {}).get("brands") or []
    check("SCOPE-BZG-FB covers multiple BZG brands", len(brands) >= 2, str(brands))
    check("SCOPE-BZG-FB includes BZG-UMA", "BZG-UMA" in brands)
    check("no outlet name hardcoded in scope targets as brand-only", ctx.get("scope", {}).get("scope_type") == "entity")

    maciej = identity.resolve_person_from_email(MACIEJ_EMAIL)
    check("Maciej person exists", maciej is not None and maciej["person_id"] == "PERS-MACIEJ")
    conn = sqlite3.connect(str(ROOT / "catalog" / "content_library.sqlite"))
    try:
        n = conn.execute(
            """
            SELECT COUNT(*) FROM org_assignments
            WHERE person_id='PERS-MACIEJ' AND status='ACTIVE' AND end_at IS NULL
            """
        ).fetchone()[0]
    finally:
        conn.close()
    check("Maciej zero assignments", n == 0)
    check(
        "Maciej no recipe.read",
        not rbac.can("PERS-MACIEJ", "recipe.read", {"entity_id": "ENT-BZG"}),
    )


def test_recipe_store() -> None:
    # Seed test DB from V1 (idempotent)
    report = rb.import_v1_recipes()
    check("import ok", report.get("ok") is True, str(report))
    brands = scope.resolve_effective_scope_context("SCOPE-BZG-FB")["structurally_covered"]["brands"]
    pack = rb.list_recipes(brand_ids=brands, limit=200)
    check("list has real recipes", pack["count"] >= 100, str(pack["count"]))
    complete = next((r for r in pack["recipes"] if r["food_cost_status"] == "COMPLETE"), None)
    check("at least one complete cost", complete is not None)
    if complete:
        detail = rb.get_recipe(complete["recipe_id"])
        check("detail food_cost numeric", detail is not None and isinstance(detail.get("food_cost"), (int, float)))
        check("sell price read-only flag", detail.get("sell_price_editable") is False)
    missing = next((r for r in pack["recipes"] if r["food_cost_status"] != "COMPLETE"), None)
    check("incomplete stays cost missing", missing is not None and missing.get("food_cost") is None)
    if missing:
        detail = rb.get_recipe(missing["recipe_id"])
        check(
            "no invented zero cost",
            detail is not None
            and detail.get("food_cost") is None
            and detail.get("food_cost_status") == "cost missing",
        )
        check(
            "line badge cost missing not 0",
            any(
                line.get("cost_badge") == "cost missing" and line.get("extended_cost") is None
                for line in (detail.get("lines") or [])
            ),
        )

    created = rb.create_recipe(
        {
            "name": "HEADCHEF1 Test Dish",
            "group_name": "Test",
            "yield_n": 1,
            "yield_unit": "Pax",
            "method": "Test method for HEADCHEF-1",
            "lines": [
                {"name": "chicken legs", "unit": "gr", "qty": 100, "line_kind": "ingredient"},
            ],
        },
        created_by="PERS-HARIYANTO",
        brand_id="BZG-UMA",
    )
    check("create recipe", created.get("recipe_id") and created.get("name") == "HEADCHEF1 Test Dish")
    rid = created["recipe_id"]
    edited = rb.update_recipe(
        rid,
        {"method": "Updated method HEADCHEF-1", "lines": created.get("lines") or []},
        updated_by="PERS-HARIYANTO",
    )
    check("edit recipe", edited.get("method") == "Updated method HEADCHEF-1")
    denied = False
    try:
        rb.update_recipe(rid, {"real_sell": 99999}, updated_by="PERS-HARIYANTO")
    except PermissionError:
        denied = True
    check("sell price edit refused", denied)

    exc = rb.list_cost_exceptions(brand_ids=brands)
    check("exceptions list present", isinstance(exc.get("count"), int) and exc["count"] >= 0)
    check("exceptions not invented", exc.get("invented_costs") is False)


def test_http(base: str) -> None:
    code, body = _http("GET", f"{base}/bzg/recipe-builder", HARI_EMAIL)
    check("Hariyanto Recipe Builder page 200", code == 200, str(code))

    code, body = _http("GET", f"{base}/api/bzg/recipe-builder/recipes", HARI_EMAIL)
    check("Hariyanto list recipes 200", code == 200 and isinstance(body, dict) and body.get("count", 0) >= 1, str(code))
    recipes = (body or {}).get("recipes") or []
    if recipes:
        rid = recipes[0]["recipe_id"]
        code, detail = _http("GET", f"{base}/api/bzg/recipe-builder/recipes/{rid}", HARI_EMAIL)
        check("Hariyanto recipe detail 200", code == 200 and isinstance(detail, dict), str(code))
        recipe = (detail or {}).get("recipe") or detail
        if recipe.get("food_cost_status") == "COMPLETE":
            check("real costing visible", isinstance(recipe.get("food_cost"), (int, float)))
        else:
            check("cost missing not invent", recipe.get("food_cost") is None)

    code, body = _http(
        "POST",
        f"{base}/api/bzg/recipe-builder/recipes",
        HARI_EMAIL,
        {
            "name": "HEADCHEF1 HTTP Dish",
            "yield_n": 1,
            "yield_unit": "Pax",
            "lines": [{"name": "garlic", "unit": "gr", "qty": 5}],
        },
    )
    check("Hariyanto create 200", code == 200 and isinstance(body, dict) and body.get("ok"), str((code, body)))
    new_id = ((body or {}).get("recipe") or {}).get("recipe_id")
    if new_id:
        code, body = _http(
            "PUT",
            f"{base}/api/bzg/recipe-builder/recipes/{new_id}",
            HARI_EMAIL,
            {"method": "http edit", "lines": [{"name": "garlic", "unit": "gr", "qty": 6}]},
        )
        check("Hariyanto edit 200", code == 200 and body.get("ok"), str((code, body)))
        code, body = _http(
            "PUT",
            f"{base}/api/bzg/recipe-builder/recipes/{new_id}",
            HARI_EMAIL,
            {"real_sell": 50000},
        )
        check("Hariyanto sell-price edit 403", code == 403, str(code))

    code, body = _http("GET", f"{base}/api/bzg/recipe-builder/exceptions", HARI_EMAIL)
    check("Hariyanto exceptions 200", code == 200 and isinstance(body, dict), str(code))

    deny_paths = [
        ("GET", "/wolf"),
        ("GET", "/api/owner/command"),
        ("GET", "/api/owner/data-quality"),
        ("GET", "/api/core/roles"),
        ("GET", "/api/core/persons"),
        ("GET", "/progress"),
        ("GET", "/bzg/uma-blu"),
        ("GET", "/hr-payroll-inputs"),
        ("GET", "/api/hr/payroll-inputs"),
        ("GET", "/api/fin/mgmt-reporting"),
        ("GET", "/amg/finance"),
        ("GET", "/api/amg/finance"),
        ("POST", "/api/core/approvals/sample/approve"),
        ("POST", "/api/journals/sample/approve"),
        ("POST", "/api/journals/sample/post"),
    ]
    for method, path in deny_paths:
        code, _body = _http(method, f"{base}{path}", HARI_EMAIL, {} if method == "POST" else None)
        check(f"Hariyanto DENY {method} {path}", code in (403, 404, 405), str(code))

    # Maciej auth-only — every operational route 403
    for method, path in [
        ("GET", "/bzg/recipe-builder"),
        ("GET", "/api/bzg/recipe-builder/recipes"),
        ("GET", "/my-work"),
        ("GET", "/api/staff/home"),
        ("GET", "/bzg/uma-blu"),
        ("GET", "/content-2.0"),
        ("GET", "/amg/finance"),
        ("GET", "/wolf"),
        ("GET", "/api/owner/command"),
    ]:
        code, _body = _http(method, f"{base}{path}", MACIEJ_EMAIL)
        check(f"Maciej 403 {path}", code == 403, str(code))

    # Regression: Devi, content, Zayen unchanged on their allow paths
    code, _ = _http("GET", f"{base}/bzg/uma-blu", DEVI_EMAIL)
    check("Devi Uma Today still 200", code == 200, str(code))
    code, _ = _http("GET", f"{base}/bzg/recipe-builder", DEVI_EMAIL)
    check("Devi Recipe Builder still 403 (no recipe.*)", code == 403, str(code))
    code, _ = _http("GET", f"{base}/content-2.0", HAIKAL_EMAIL)
    check("Haikal content still 200", code == 200, str(code))
    code, _ = _http("GET", f"{base}/content-2.0", YUDI_EMAIL)
    check("Yudi content still 200", code == 200, str(code))
    # Zayen desk may 502 if atrium sidecar is down under the guard — RBAC still denies Recipe Builder
    code, _ = _http("GET", f"{base}/api/staff/home", ZAYEN_EMAIL)
    check("Zayen My Work API still 200", code == 200, str(code))
    code, _ = _http("GET", f"{base}/bzg/recipe-builder", ZAYEN_EMAIL)
    check("Zayen Recipe Builder 403", code == 403, str(code))


def test_commissioning_held() -> None:
    conn = sqlite3.connect(str(ROOT / "catalog" / "content_library.sqlite"))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT work_item_id, status, routing_state, routing_reason, origin
            FROM core_work_items
            WHERE commissioning_capability_id='COMM-HARIYANTO-RECIPE-BUILDER'
              AND owner_person_id='PERS-HARIYANTO'
              AND status!='CANCELLED'
            """
        ).fetchone()
    finally:
        conn.close()
    check("commissioning WI exists", row is not None)
    check(
        "commissioning HELD_UNTIL_CF_ACCESS",
        row is not None and row["routing_state"] == "HELD_UNTIL_CF_ACCESS",
        str(dict(row) if row else None),
    )
    check(
        "held note mentions Cloudflare",
        row is not None and "carolus.haryanto@gmail.com" in (row["routing_reason"] or ""),
    )
    sections = umw.build_universal_sections("PERS-HARIYANTO")
    active_ids = []
    for sec in sections:
        for item in sec.get("items") or []:
            active_ids.append(item.get("work_item_id"))
    check(
        "held WI not active My Work",
        row is None or row["work_item_id"] not in active_ids,
        str(active_ids),
    )
    queue = umw.war_room_commissioning_queue()
    qids = [c.get("work_item_id") for c in queue.get("queue") or []]
    check("held WI not in active war-room queue", row is None or row["work_item_id"] not in qids)

    # staff_ready stays false
    home = build_home("PERS-HARIYANTO")
    check("Hariyanto staff_ready false", home.get("staff_ready") is False)


def test_regression_homes() -> None:
    for pid, label in (
        ("PERS-DEVI", "Devi"),
        ("PERS-HAIKAL", "Haikal"),
        ("PERS-ZAYEN", "Zayen"),
    ):
        home = build_home(pid)
        check(f"{label} home builds", isinstance(home, dict) and home.get("staff_ready") is False)


def main() -> int:
    test_identity_and_rbac()
    test_recipe_store()
    httpd, base = start_server()
    try:
        test_http(base)
    finally:
        httpd.shutdown()
    test_commissioning_held()
    test_regression_homes()
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    print("RESULT: PASS" if FAIL == 0 else "RESULT: FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
