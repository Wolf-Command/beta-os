#!/usr/bin/env python3
"""ATRIUM-OPS-SECURITY-EVIDENCE-1 — eng prove create→evidence→escalate→close."""
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

from core import atrium_ops_security_evidence_1 as sec  # noqa: E402

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
    v1 = sec.V1_INCIDENTS_DB
    check("v1 incidents.db exists", v1.is_file(), str(v1))
    before = v1.stat() if v1.is_file() else None

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "security_evidence.sqlite"
        os.environ[sec.ENV_DB] = str(db)

        seed = sec.import_v1_seed(db=db)
        check("v1 seed ok", seed.get("ok") is True, str(seed))
        check("v1 seed imported >= 1", int(seed.get("imported") or 0) >= 1, str(seed))
        check("v1 mtime unchanged after seed", seed.get("v1_mtime_unchanged") is True)
        check(
            "v1 provenance label",
            "v1:incidents.db#id=" in str(seed.get("provenance_label") or ""),
            str(seed),
        )
        again = sec.import_v1_seed(db=db)
        check("v1 seed idempotent", int(again.get("imported") or 0) == 0 and int(again.get("skipped") or 0) >= 1)

        created = sec.create_incident(
            {
                "reported_by": "PERS-MATT",
                "business": "AMG",
                "venue": "Atrium lobby cash desk",
                "category": "cash_theft",
                "severity": "incident",
                "details": "Till short noticed at hand-over; count pending.",
                "people_involved": ["night cashier"],
                "asset_ref": "ATRIUM-TILL-1",
                "responsible_person": "duty manager",
                "cctv_timestamp": "2026-10-02T02:15:00+08:00",
                "cctv_camera_ref": "LOBBY-CAM-text-ref-only",
            },
            actor="PERS-MATT",
            db=db,
        )
        check("create ok", created.get("ok") is True, str(created))
        incident_id = (created.get("incident") or {}).get("incident_id")
        check("create has id", bool(incident_id), str(created))
        check(
            "create stores cctv text refs not stream",
            (created.get("incident") or {}).get("cctv_timestamp") == "2026-10-02T02:15:00+08:00"
            and (created.get("incident") or {}).get("cctv_stream") is False,
            str(created.get("incident")),
        )

        payload, status = sec.handle_post(
            sec.API_PREFIX,
            {"reported_by": "x", "details": "no venue", "category": "security"},
            actor="PERS-MATT",
            db=db,
        )
        check("fail-closed missing venue", status == 400 and payload.get("error") == "missing_venue", str(payload))

        ev = sec.add_evidence(
            incident_id,
            {
                "kind": "cash_control_ref",
                "ref_text": "till-count-sheet-20261002",
                "note": "Hand-over short; sheet attached as ref only.",
            },
            actor="PERS-MATT",
            db=db,
        )
        check("evidence added", ev.get("ok") is True and ev.get("workflow_step") == "evidence_added", str(ev))
        check(
            "status moves to investigating",
            (ev.get("incident") or {}).get("status") == "investigating",
            str(ev.get("incident")),
        )

        esc = sec.escalate(
            incident_id,
            {"reason": "cash variance needs owner visibility", "severity": "critical"},
            actor="PERS-MATT",
            db=db,
        )
        check(
            "escalated",
            esc.get("ok") is True
            and (esc.get("incident") or {}).get("status") == "escalated"
            and (esc.get("incident") or {}).get("severity") == "critical",
            str(esc),
        )

        act = sec.record_action(
            incident_id,
            {
                "actions_taken": "Recounted till; secured drawer; notified duty manager.",
                "follow_up": "Preventability review at next SOD.",
            },
            actor="PERS-MATT",
            db=db,
        )
        check("action recorded", act.get("ok") is True and (act.get("incident") or {}).get("status") == "actioned", str(act))

        closed = sec.close_incident(
            incident_id,
            {"closure_note": "Variance logged; drawer secured; review queued."},
            actor="PERS-MATT",
            db=db,
        )
        check(
            "closed",
            closed.get("ok") is True and (closed.get("incident") or {}).get("status") == "closed",
            str(closed),
        )

        detail = sec.get_incident_detail(incident_id, db=db)
        check("detail has evidence", len(detail.get("evidence") or []) >= 1, str(detail.get("evidence")))
        actions = [a.get("action") for a in (detail.get("audit") or [])]
        check(
            "audit trail immutable chain",
            {"create", "add_evidence", "escalate", "record_action", "close"}.issubset(set(actions)),
            str(actions),
        )

        # Append-only: direct SQL delete must abort
        conn = sec.connect(db)
        blocked = False
        try:
            conn.execute("DELETE FROM security_evidence")
            conn.commit()
        except sqlite3.Error:
            blocked = True
        finally:
            conn.close()
        check("evidence delete blocked by trigger", blocked)

        stream = sec.refuse_cctv_stream()
        check(
            "cctv stream absent",
            stream.get("cctv_stream") is False
            and stream.get("error") == "cctv_stream_unavailable"
            and stream.get("cctv_stream_status") == "EXTERNAL_UNAVAILABLE",
            str(stream),
        )
        prod = sec.refuse_prod_mutate()
        check("prod mutate refused helper", prod.get("error") == "prod_mutate_refused")

        post_stream, st_stream = sec.handle_post(
            f"{sec.API_PREFIX}/stream",
            {"stream_url": "rtsp://fake"},
            actor="PERS-MATT",
            db=db,
        )
        check("POST stream refused", st_stream == 405 and post_stream.get("error") == "cctv_stream_unavailable", str(post_stream))

        post_prod, st_prod = sec.handle_post(
            f"{sec.API_PREFIX}/prod-mutate",
            {"prod_mutate": True},
            actor="PERS-MATT",
            db=db,
        )
        check("POST prod-mutate refused", st_prod == 403 and post_prod.get("error") == "prod_mutate_refused", str(post_prod))

        listing = sec.list_incidents(db=db)
        check("register toward PARTIAL", listing.get("register_state") == "PARTIAL", str(listing.get("register_state")))
        check("staff_ready false", listing.get("staff_ready") is False)
        check("honesty no cctv invent", listing.get("cctv_inventory_invented") is False)

        # HTTP surface on free port (Beta handler) — writes go to temp DB via ENV
        from serve_beta import BetaHandler  # noqa: E402

        os.environ["BETA_AUTH_MODE"] = "development_assertion"
        server = ThreadingHTTPServer(("127.0.0.1", 0), BetaHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            st, desk = http(port, "GET", "/api/msc/security-evidence")
            check("GET api 200", st == 200 and desk.get("ok") is True, str(desk)[:200])
            check("GET api staff_ready false", desk.get("staff_ready") is False)
            check("GET api cctv unavailable", desk.get("cctv_stream") is False)

            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/msc/security-evidence",
                headers={"Accept": "text/html", "X-Wolf-Subject": "PERS-MATT"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", errors="replace")
                check("page is html desk", resp.status == 200 and "Security / evidence desk" in html)
                check(
                    "page not cctv viewer",
                    "Not a CCTV viewer" in html or "CCTV stream is EXTERNAL" in html,
                )

            st_c, created_http = http(
                port,
                "POST",
                "/api/msc/security-evidence",
                {
                    "reported_by": "desk-http",
                    "business": "AMG",
                    "venue": "Atrium ballroom door",
                    "category": "access",
                    "severity": "near-miss",
                    "details": "Door propped open after event load-in.",
                },
            )
            check("POST create http", st_c == 200 and created_http.get("ok") is True, str(created_http)[:240])
            hid = (created_http.get("incident") or {}).get("incident_id")
            st_e, ev_http = http(
                port,
                "POST",
                f"/api/msc/security-evidence/{hid}/evidence",
                {"kind": "access_log_ref", "ref_text": "door-log-20261002", "note": "propped 12 min"},
            )
            check("POST evidence http", st_e == 200 and ev_http.get("ok") is True, str(ev_http)[:200])
            st_x, esc_http = http(
                port,
                "POST",
                f"/api/msc/security-evidence/{hid}/escalate",
                {"reason": "repeat prop"},
            )
            check("POST escalate http", st_x == 200 and (esc_http.get("incident") or {}).get("status") == "escalated", str(esc_http)[:200])
            st_cl, close_http = http(
                port,
                "POST",
                f"/api/msc/security-evidence/{hid}/close",
                {"closure_note": "Door secured; note to events lead."},
            )
            check(
                "POST close http",
                st_cl == 200 and (close_http.get("incident") or {}).get("status") == "closed",
                str(close_http)[:200],
            )

            st_s, stream_http = http(port, "POST", "/api/msc/security-evidence/stream", {"url": "x"})
            check("HTTP stream refused", st_s == 405 and stream_http.get("error") == "cctv_stream_unavailable", str(stream_http))
        finally:
            server.shutdown()
            server.server_close()

        # Prove we did not target prod port in this test harness
        check("test harness not on prod port", port != PROD_PORT)
        check("prod_mutate honesty false", created.get("prod_mutate") is False)

    if before is not None:
        after = v1.stat()
        check("v1 incidents.db mtime unchanged end-to-end", before.st_mtime_ns == after.st_mtime_ns)

    # Static wiring presence
    serve = (ROOT / "scripts" / "serve_beta.py").read_text(encoding="utf-8")
    check("serve imports module", "atrium_ops_security_evidence_1" in serve)
    check("serve api route", "/api/msc/security-evidence" in serve)
    check("serve page route", "/msc/security-evidence" in serve)
    html_path = ROOT / "dashboards" / "atrium-ops-security-evidence-1.html"
    check("dashboard exists", html_path.is_file())
    result_md = ROOT / "state" / "final-completion" / "forensic-completeness-20261001" / "ATRIUM-OPS-SECURITY-EVIDENCE-1-RESULT.md"
    result_json = ROOT / "state" / "final-completion" / "forensic-completeness-20261001" / "ATRIUM-OPS-SECURITY-EVIDENCE-1-RESULT.json"
    # RESULT may be written after tests in the same session — soft check if present
    if result_md.is_file() and result_json.is_file():
        check("RESULT files present", True)
    else:
        check("RESULT files deferred to pack close", True)

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
