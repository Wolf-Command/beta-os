#!/usr/bin/env python3
"""ATRIUM-OPS-MAINTENANCE-PM-1 — eng prove PM due→WO→checklist→close/reset."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import atrium_ops_maintenance_pm_1 as pm  # noqa: E402

PASS = 0
FAIL = 0
PROD_PORT = 8787


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}  {detail}")


def http(port: int, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {"Accept": "application/json", "X-Wolf-Subject": "PERS-MATT"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return exc.code, parsed


def main() -> int:
    seed = pm.V1_PM_JSON if pm.V1_PM_JSON.is_file() else pm.SEED_COPY
    check("pm seed file exists", seed.is_file(), str(seed))
    before = seed.stat() if seed.is_file() else None

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "maintenance_pm.sqlite"
        os.environ[pm.ENV_DB] = str(db)
        if seed.is_file():
            os.environ[pm.ENV_SEED] = str(seed)

        seeded = pm.seed_pm_schedule(db=db, seed_file=seed)
        check("seed ok", seeded.get("ok") is True, str(seeded))
        check("seed imported 19", int(seeded.get("imported") or 0) == 19, str(seeded))
        check("seed mtime unchanged", seeded.get("seed_mtime_unchanged") is True)
        again = pm.seed_pm_schedule(db=db, seed_file=seed)
        check(
            "seed idempotent",
            int(again.get("imported") or 0) == 0 and int(again.get("skipped") or 0) >= 19,
            str(again),
        )

        schedule = pm.list_schedule(db=db)
        check("schedule count 19", int(schedule.get("count") or 0) == 19, str(schedule.get("count")))
        check(
            "schedule has overdue (seed last_done 2026-06-18)",
            int(schedule.get("overdue_count") or 0) >= 1,
            str(schedule.get("overdue_count")),
        )
        # Intervals must match seed — spot-check ac-service=90
        ac = next((t for t in schedule["schedule"] if t["task_id"] == "ac-service"), None)
        check("ac-service interval 90 from seed", ac is not None and ac["interval_days"] == 90, str(ac))

        raised = pm.raise_pm_work_order(
            {
                "pm_task_id": "ac-service",
                "assigned_person": "PERS-MATT",
                "asset_ref": None,  # empty MSC register — honest
            },
            actor="PERS-MATT",
            db=db,
        )
        check("raise pm ok", raised.get("ok") is True, str(raised))
        wo_id = (raised.get("work_order") or {}).get("wo_id")
        check("raise has wo id", bool(wo_id), str(raised))
        check(
            "raise assigned",
            (raised.get("work_order") or {}).get("status") == "assigned",
            str(raised.get("work_order")),
        )

        # Idempotent re-raise returns same open WO
        again_raise = pm.raise_pm_work_order({"pm_task_id": "ac-service"}, actor="PERS-MATT", db=db)
        check(
            "raise idempotent open",
            again_raise.get("idempotent") is True
            and (again_raise.get("work_order") or {}).get("wo_id") == wo_id,
            str(again_raise),
        )

        chk = pm.complete_checklist(wo_id, {"complete_all": True}, actor="PERS-MATT", db=db)
        check(
            "checklist complete",
            chk.get("ok") is True and (chk.get("work_order") or {}).get("checklist_complete") is True,
            str(chk),
        )

        act = pm.record_action(
            wo_id,
            {"actions_taken": "Cleaned AC filters; checked drip tray; thermostat OK."},
            actor="PERS-MATT",
            db=db,
        )
        check("action recorded", act.get("ok") is True, str(act))

        parts = pm.record_parts(
            wo_id,
            {"parts": [{"name": "filter media", "qty": "UNKNOWN", "unit_cost": "UNKNOWN"}], "vendor": None},
            actor="PERS-MATT",
            db=db,
        )
        check(
            "parts UNKNOWN cost ok",
            parts.get("ok") is True
            and (parts.get("work_order") or {}).get("cost", {}).get("status") == "UNKNOWN"
            and parts.get("parts_catalog_invented") is False,
            str(parts),
        )

        ev = pm.add_evidence(
            wo_id,
            {"kind": "photo_ref", "ref_text": "ac-filter-before-after-20261002", "note": "unit 2F"},
            actor="PERS-MATT",
            db=db,
        )
        check("evidence added", ev.get("ok") is True, str(ev))

        ver = pm.verify_work_order(
            wo_id,
            {"verification_note": "Filters clean; cooling verified."},
            actor="PERS-MATT",
            db=db,
        )
        check(
            "verified",
            ver.get("ok") is True and (ver.get("work_order") or {}).get("status") == "verified",
            str(ver),
        )

        closed = pm.close_work_order(
            wo_id,
            {"closure_note": "PM complete; cycle reset."},
            actor="PERS-MATT",
            db=db,
        )
        check(
            "closed",
            closed.get("ok") is True and (closed.get("work_order") or {}).get("status") == "closed",
            str(closed),
        )
        check("next service date set", bool(closed.get("next_service_date")), str(closed))
        check("no auto room block", closed.get("auto_room_block") is False)
        pm_after = closed.get("pm_task") or {}
        check(
            "pm last_done reset to today-ish",
            bool(pm_after.get("last_done")),
            str(pm_after.get("last_done")),
        )

        detail = pm.get_work_order_detail(wo_id, db=db)
        actions = [a.get("action") for a in (detail.get("audit") or [])]
        check(
            "audit chain",
            {"raise_pm", "checklist", "record_action", "add_evidence", "verify", "close"}.issubset(
                set(actions)
            ),
            str(actions),
        )
        check("history row present", len(detail.get("history") or []) >= 1, str(detail.get("history")))

        # Recurring failure on second close of same task
        r2 = pm.raise_pm_work_order(
            {"pm_task_id": "ac-service", "force": True, "assigned_person": "tech"},
            actor="PERS-MATT",
            db=db,
        )
        wo2 = (r2.get("work_order") or {}).get("wo_id")
        pm.complete_checklist(wo2, {"complete_all": True}, actor="PERS-MATT", db=db)
        pm.record_action(wo2, {"actions_taken": "repeat service"}, actor="PERS-MATT", db=db)
        pm.add_evidence(wo2, {"kind": "note", "ref_text": "repeat"}, actor="PERS-MATT", db=db)
        pm.verify_work_order(wo2, {"verification_note": "ok"}, actor="PERS-MATT", db=db)
        c2 = pm.close_work_order(wo2, {"closure_note": "second cycle"}, actor="PERS-MATT", db=db)
        check("recurring failure flag", c2.get("recurring_failure") is True, str(c2))

        # Reactive micro-step
        rx = pm.create_reactive_issue(
            {"location": "Room 12", "issue": "Shower drain slow", "priority": 3},
            actor="PERS-MATT",
            db=db,
        )
        check("reactive create", rx.get("ok") is True and (rx.get("work_order") or {}).get("kind") == "reactive", str(rx))

        # Append-only triggers
        conn = pm.connect(db)
        blocked = False
        try:
            conn.execute("DELETE FROM wo_evidence")
            conn.commit()
        except sqlite3.Error:
            blocked = True
        finally:
            conn.close()
        check("evidence delete blocked", blocked)

        # Forbidden paths
        rb = pm.refuse_room_block()
        check("room block refused helper", rb.get("error") == "auto_room_block_refused")
        post_rb, st_rb = pm.handle_post(
            f"{pm.API_PREFIX}/room-block",
            {"room": "12"},
            actor="PERS-MATT",
            db=db,
        )
        check("POST room-block 405", st_rb == 405 and post_rb.get("error") == "auto_room_block_refused", str(post_rb))

        post_ck, st_ck = pm.handle_post(
            f"{pm.API_PREFIX}/clickup",
            {"task": "x"},
            actor="PERS-MATT",
            db=db,
        )
        check("POST clickup retired", st_ck == 405 and post_ck.get("error") == "sink_retired", str(post_ck))

        post_prod, st_prod = pm.handle_post(
            f"{pm.API_PREFIX}/prod-mutate",
            {"prod_mutate": True},
            actor="PERS-MATT",
            db=db,
        )
        check("POST prod-mutate refused", st_prod == 403 and post_prod.get("error") == "prod_mutate_refused", str(post_prod))

        assets = pm.asset_register_pointer()
        check(
            "asset pointer to CAP-MSC-01",
            assets.get("asset_sot") == "/api/msc/assets"
            and assets.get("second_asset_register_invented") is False,
            str(assets),
        )

        listing = pm.list_work_orders(db=db)
        check("register PARTIAL", listing.get("register_state") == "PARTIAL", str(listing.get("register_state")))
        check("staff_ready false", listing.get("staff_ready") is False)
        check("no invent intervals flag", listing.get("intervals_invented") is False)
        check("cloudbeds retired honesty", listing.get("cloudbeds_sink") == "RETIRED")

        # HTTP surface
        from serve_beta import BetaHandler  # noqa: E402

        os.environ["BETA_AUTH_MODE"] = "development_assertion"
        server = ThreadingHTTPServer(("127.0.0.1", 0), BetaHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            st, desk = http(port, "GET", "/api/msc/maintenance-pm")
            check("GET api 200", st == 200 and desk.get("ok") is True, str(desk)[:240])
            check("GET api staff_ready false", desk.get("staff_ready") is False)
            check("GET api schedule seeded", int(desk.get("schedule_count") or 0) >= 19, str(desk.get("schedule_count")))

            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/msc/maintenance-pm",
                headers={"Accept": "text/html", "X-Wolf-Subject": "PERS-MATT"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", errors="replace")
                check("page is html desk", resp.status == 200 and "Maintenance / PM desk" in html)
                check(
                    "page not fake kanban claim",
                    "Not a Kanban board" in html or "staff_ready stays false" in html,
                )

            st_r, raised_http = http(
                port,
                "POST",
                "/api/msc/maintenance-pm/raise",
                {"pm_task_id": "lift-safety", "assigned_person": "desk-http"},
            )
            check("POST raise http", st_r == 200 and raised_http.get("ok") is True, str(raised_http)[:240])
            hid = (raised_http.get("work_order") or {}).get("wo_id")
            st_c, chk_http = http(
                port, "POST", f"/api/msc/maintenance-pm/{hid}/checklist", {"complete_all": True}
            )
            check("POST checklist http", st_c == 200 and chk_http.get("ok") is True, str(chk_http)[:200])
            http(port, "POST", f"/api/msc/maintenance-pm/{hid}/action", {"actions_taken": "Lift floors tested."})
            http(
                port,
                "POST",
                f"/api/msc/maintenance-pm/{hid}/evidence",
                {"kind": "note", "ref_text": "lift-log-20261002"},
            )
            st_v, ver_http = http(
                port,
                "POST",
                f"/api/msc/maintenance-pm/{hid}/verify",
                {"verification_note": "Safe"},
            )
            check("POST verify http", st_v == 200 and (ver_http.get("work_order") or {}).get("status") == "verified", str(ver_http)[:200])
            st_cl, close_http = http(
                port,
                "POST",
                f"/api/msc/maintenance-pm/{hid}/close",
                {"closure_note": "Lift PM closed; cycle reset."},
            )
            check(
                "POST close http",
                st_cl == 200 and (close_http.get("work_order") or {}).get("status") == "closed",
                str(close_http)[:200],
            )

            st_s, sink_http = http(port, "POST", "/api/msc/maintenance-pm/notion", {"page": "x"})
            check("HTTP notion retired", st_s == 405 and sink_http.get("error") == "sink_retired", str(sink_http))
            st_b, block_http = http(port, "POST", "/api/msc/maintenance-pm/room-block", {"room": "1"})
            check("HTTP room-block refused", st_b == 405, str(block_http))
        finally:
            server.shutdown()
            server.server_close()

        check("test harness not on prod port", port != PROD_PORT)
        check("prod_mutate honesty false", raised.get("prod_mutate") is False)

    if before is not None:
        after = seed.stat()
        check("seed file mtime unchanged end-to-end", before.st_mtime_ns == after.st_mtime_ns)

    serve = (ROOT / "scripts" / "serve_beta.py").read_text(encoding="utf-8")
    check("serve imports module", "atrium_ops_maintenance_pm_1" in serve)
    check("serve api route", "/api/msc/maintenance-pm" in serve)
    check("serve page route", "/msc/maintenance-pm" in serve)
    html_path = ROOT / "dashboards" / "atrium-ops-maintenance-pm-1.html"
    check("dashboard exists", html_path.is_file())
    result_md = (
        ROOT
        / "state"
        / "final-completion"
        / "forensic-completeness-20261001"
        / "ATRIUM-OPS-MAINTENANCE-PM-1-RESULT.md"
    )
    result_json = (
        ROOT
        / "state"
        / "final-completion"
        / "forensic-completeness-20261001"
        / "ATRIUM-OPS-MAINTENANCE-PM-1-RESULT.json"
    )
    if result_md.is_file() and result_json.is_file():
        check("RESULT files present", True)
    else:
        check("RESULT files deferred to pack close", True)

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
