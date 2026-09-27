#!/usr/bin/env python3
"""Uma Blu petty cash surface — Beta. Temp DB + ephemeral HTTP.

Petty route 200; nav links; float NOT FOUND; Today quiet-or-card;
ops + daily-close suites still green; no forbidden write helpers.
"""
from __future__ import annotations

import importlib.util
import inspect
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
OPS_PY = SCRIPTS / "core" / "uma_ops_console.py"
SERVE = SCRIPTS / "serve_beta.py"
OPS_TEST = SCRIPTS / "tests" / "test_uma_ops_console.py"
CLOSE_TEST = SCRIPTS / "tests" / "test_uma_blu_daily_close.py"
UMA_HTML = [
    ROOT / "dashboards" / "bzg-uma-blu.html",
    ROOT / "dashboards" / "bzg-uma-blu-bills.html",
    ROOT / "dashboards" / "bzg-uma-blu-issues.html",
    ROOT / "dashboards" / "bzg-uma-blu-petty.html",
]

PASS = 0
FAIL = 0

FORBIDDEN_WRITE_TERMS = (
    "clickup",
    "telegram",
    "esb_write",
    "push_esb",
    "bank_write",
    "write_to_bank",
)


def esb_refusal_only(src_lower: str) -> tuple[bool, str]:
    """The substring esb_write is the off-flag and the refusal, not a writer.

    test_bzg_loop_closure.py requires def refuse_esb_write, code
    esb_write_refused, and \"esb_write\": False. A bare substring ban
    cannot be true at the same time. Anything outside those forms fails.
    """
    if "def refuse_esb_write" not in src_lower:
        return False, "refuse_esb_write missing"
    if '"esb_write": true' in src_lower or "'esb_write': true" in src_lower:
        return False, "esb_write set true"
    residual = src_lower
    for allowed in (
        '"esb_write": false',
        "def refuse_esb_write",
        "refuse_esb_write(",
        "esb_write_refused",
    ):
        residual = residual.replace(allowed, "")
    if "esb_write" in residual:
        i = residual.find("esb_write")
        return False, residual[max(0, i - 40) : i + 48]
    return True, ""


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_ops():
    spec = importlib.util.spec_from_file_location("uma_ops_console", OPS_PY)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def patch_catalog(mod, path: Path) -> None:
    mod.CATALOG_DB = path


def main() -> int:
    global PASS, FAIL
    os.environ["WOLF_TEST_MODE"] = "1"
    os.environ["BETA_AUTH_MODE"] = "development_assertion"

    src = OPS_PY.read_text(encoding="utf-8").lower()
    serve_text = SERVE.read_text(encoding="utf-8")
    serve_src = serve_text.lower()
    for term in FORBIDDEN_WRITE_TERMS:
        if term == "esb_write":
            ok, detail = esb_refusal_only(src)
            check("ops no write helper esb_write", ok, detail)
        else:
            check(f"ops no write helper {term}", term not in src)
    # Petty handlers must not grow forbidden write helpers
    petty_block = ""
    if "def _uma_ops_petty" in serve_text:
        start = serve_text.index("def _uma_ops_petty")
        end = serve_text.find("\n    def ", start + 1)
        petty_block = serve_text[start:end if end > 0 else start + 800].lower()
    for term in FORBIDDEN_WRITE_TERMS:
        check(f"petty handler no {term}", term not in petty_block)
    check(
        "no wolf-system bzg-petty-cash import",
        "bzg-petty-cash" not in src and "bzg-petty-cash" not in serve_src,
    )
    check(
        "serve wires /bzg/uma-blu/petty",
        "/bzg/uma-blu/petty" in serve_text,
    )
    check(
        "serve maps bzg-uma-blu-petty.html",
        "bzg-uma-blu-petty.html" in serve_text,
    )

    for html_path in UMA_HTML:
        text = html_path.read_text(encoding="utf-8")
        check(
            f"nav links petty on {html_path.name}",
            'href="/bzg/uma-blu/petty"' in text,
            "missing petty href",
        )
        check(
            f"no disabled petty label on {html_path.name}",
            "Petty cash — later" not in text,
        )

    td = tempfile.mkdtemp(prefix="uma-petty-", dir=str(ROOT / "state"))
    httpd = None
    try:
        db = Path(td) / "content_library.sqlite"
        shutil.copy2(LIVE_DB, db)

        ops = load_ops()
        patch_catalog(ops, db)
        from core import audit as audit
        from core import authority as authority
        from core import evidence as evidence
        from core import venue_close as venue_close
        from core import work_items as work_items

        for m in (audit, authority, evidence, venue_close, work_items, ops):
            patch_catalog(m, db)

        conn = ops.db_connect(db)
        ops.ensure_schema(conn)
        # Clear any copied example/live petty so Today starts quiet for petty
        conn.execute("DELETE FROM bzg_ops_petty_movements")
        conn.execute("DELETE FROM bzg_ops_petty_days")
        conn.execute("DELETE FROM bzg_ops_purchase_requests")
        try:
            conn.execute(
                "UPDATE venue_daily_closes SET state='OPEN' WHERE state='EXCEPTION'"
            )
        except sqlite3.OperationalError:
            pass
        conn.commit()

        honesty = ops.honesty_flags()
        check("petty_cash_page is BUILT", honesty.get("petty_cash_page") == "BUILT", str(honesty))
        check(
            "float honesty is NOT_FOUND",
            honesty.get("float") == "NOT_FOUND",
            str(honesty.get("float")),
        )
        check(
            "payment_execution still NOT_BUILT",
            honesty.get("payment_execution") == "NOT_BUILT",
        )
        check(
            "authority_limits_invented false",
            honesty.get("authority_limits_invented") is False,
        )

        payload = ops.list_petty(conn=conn)
        check("petty list ok", payload.get("ok") is True)
        check(
            "float_status NOT_FOUND without invented number",
            payload.get("float_status") == "NOT_FOUND",
            str(payload.get("float_status")),
        )
        check(
            "opening_float not presented as 0",
            payload.get("opening_float") in (None, "see_days"),
            str(payload.get("opening_float")),
        )

        today_clean = ops.today_cards(conn=conn)
        petty_cards = [c for c in today_clean.get("cards", []) if c.get("kind") == "petty_cash"]
        check(
            "Today quiet when no open petty items",
            len(petty_cards) == 0,
            str(petty_cards),
        )

        ops.seed_fixture_petty(conn)
        conn.commit()
        seeded = ops.list_petty_movements(conn=conn)
        check("≤3 example fixtures", len(seeded) <= 3, str(len(seeded)))
        check(
            "fixtures labelled example",
            all(m.get("example") for m in seeded),
        )
        blank_cur = [m for m in seeded if m.get("movement_id") == "PETTY-UMA-EXAMPLE-3"]
        check(
            "blank currency stays null (never guessed)",
            blank_cur and blank_cur[0].get("currency") is None,
            str(blank_cur[:1]),
        )

        today_open = ops.today_cards(conn=conn)
        petty_cards2 = [c for c in today_open.get("cards", []) if c.get("kind") == "petty_cash"]
        check(
            "Today card when fixture open petty exists",
            len(petty_cards2) >= 1,
            str(today_open.get("cards")),
        )
        check(
            "Today petty card href",
            petty_cards2 and petty_cards2[0].get("href") == "/bzg/uma-blu/petty",
        )

        # Count without float → POLICY_REQUIRED (no invented threshold)
        counted = ops.note_petty_count("2026-09-18", 100000.0, conn=conn, commit=True)
        check(
            "count without float → POLICY_REQUIRED",
            counted.get("state") == "POLICY_REQUIRED",
            str(counted),
        )
        check(
            "expected stays null when float missing",
            counted.get("expected_amount") is None,
            str(counted.get("expected_amount")),
        )

        petty_events = audit.list_events(
            entity_id="ENT-BZG",
            source="uma_ops_console",
            limit=40,
            conn=conn,
        )
        check(
            "petty movement writes uma_ops_console audit",
            any(e.get("action") == "bzg.petty.movement" and e.get("source") == "uma_ops_console" for e in petty_events),
            str([e.get("action") for e in petty_events][:8]),
        )
        check(
            "petty count writes uma_ops_console audit",
            any(
                e.get("action") == "bzg.petty.count" and e.get("reason_code") == "POLICY_REQUIRED"
                for e in petty_events
            ),
            str([e.get("action") for e in petty_events][:8]),
        )

        forced = ops.list_issues(conn=conn)
        forced_rows = forced.get("issues") or []
        check(
            "Issues lists petty POLICY_REQUIRED when fixture forces it",
            any(
                i.get("kind") == "petty_policy_required"
                or (
                    "Petty" in (i.get("label") or "")
                    and "POLICY_REQUIRED" in (i.get("label") or "")
                )
                for i in forced_rows
            ),
            str(forced_rows)[:400],
        )
        check(
            "petty issue label is human",
            all(
                "PETTY-" not in (i.get("label") or "") and "PERS-" not in (i.get("label") or "")
                for i in forced_rows
            ),
            str(forced_rows)[:300],
        )

        conn.execute("DELETE FROM bzg_ops_petty_movements")
        conn.execute("DELETE FROM bzg_ops_petty_days")
        conn.execute("DELETE FROM bzg_ops_purchase_requests")
        try:
            conn.execute(
                "UPDATE venue_daily_closes SET state='OPEN' WHERE state='EXCEPTION'"
            )
        except sqlite3.OperationalError:
            pass
        conn.commit()
        quiet = ops.list_issues(conn=conn)
        check(
            "Issues quiet when petty clean",
            quiet.get("empty") is True and len(quiet.get("issues") or []) == 0,
            str(quiet)[:300],
        )

        # Ephemeral HTTP: page + API
        import serve_beta as sb

        sb.CATALOG_DB = db
        if hasattr(sb, "_uma_ops"):
            patch_catalog(sb._uma_ops, db)
        patch_catalog(ops, db)

        Handler = None
        for _, obj in inspect.getmembers(sb, inspect.isclass):
            if issubclass(obj, BaseHTTPRequestHandler) and obj is not BaseHTTPRequestHandler:
                Handler = obj
                break
        check("BetaHandler found", Handler is not None)
        if Handler:
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()

            def get(path: str, headers: dict | None = None):
                req = Request(
                    f"http://127.0.0.1:{port}{path}",
                    method="GET",
                    headers=headers or {},
                )
                try:
                    with urlopen(req, timeout=8) as r:
                        return r.status, r.read()
                except HTTPError as e:
                    return e.code, e.read()
                except URLError as e:
                    return 0, str(e).encode()

            st, body = get("/bzg/uma-blu/petty")
            check("petty page 200", st == 200, f"status={st}")
            html = body.decode("utf-8", errors="replace")
            check("petty page has title", "Petty" in html)
            check("petty page float NOT FOUND copy", "NOT FOUND" in html)

            st2, body2 = get("/api/bzg/uma-blu/petty")
            check("petty API no identity 403", st2 == 403, f"status={st2}")
            import core.request_auth as _ra

            os.environ["BETA_AUTH_MODE"] = "development_assertion"
            _ra._ENV_LOADED = True
            st2, body2 = get(
                "/api/bzg/uma-blu/petty",
                headers={"X-Wolf-Subject": "deviputu236@gmail.com"},
            )
            os.environ["BETA_AUTH_MODE"] = "cloudflare_access"
            _ra._ENV_LOADED = True
            check("petty API Devi Uma scope 200", st2 == 200, f"status={st2} {body2[:180]!r}")
            try:
                data = json.loads(body2.decode("utf-8"))
            except json.JSONDecodeError:
                data = {}
            check("petty API ok", data.get("ok") is True, str(data)[:200])
            check(
                "petty API float_status NOT_FOUND",
                data.get("float_status") == "NOT_FOUND"
                or (data.get("honesty") or {}).get("float") == "NOT_FOUND",
                str(data.get("float_status")),
            )

        conn.close()
    finally:
        if httpd is not None:
            try:
                httpd.shutdown()
            except Exception:  # noqa: BLE001
                pass
        shutil.rmtree(td, ignore_errors=True)

    # Keep existing suites green
    env = os.environ.copy()
    env["WOLF_TEST_MODE"] = "1"
    for label, path in (
        ("test_uma_ops_console", OPS_TEST),
        ("test_uma_blu_daily_close", CLOSE_TEST),
    ):
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        m = re.search(r"PASS=(\d+)\s+FAIL=(\d+)", out)
        if m:
            check(
                f"{label} still passes",
                int(m.group(2)) == 0 and proc.returncode == 0,
                f"rc={proc.returncode} {m.group(0)}",
            )
        else:
            check(
                f"{label} still passes",
                proc.returncode == 0,
                out[-500:],
            )

    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
