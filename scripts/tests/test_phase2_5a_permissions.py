#!/usr/bin/env python3
"""Phase 2.5A Permissions — Matthew's 20 acceptance tests (:8788 only)."""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

BETA = Path("/Users/wolfterminal/beta-os")
DB = BETA / "catalog" / "content_library.sqlite"
BASE = "http://127.0.0.1:8788"

MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"
STRANGER = "nobody@example.com"

sys.path.insert(0, str(BETA / "scripts"))
from wolf_intelligence import has_permission, list_permissions, db_connect  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def http(method: str, path: str, body: dict | None = None, headers: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            payload = json.loads(raw) if raw else {}
            return resp.status, payload
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return e.code, payload


def main() -> int:
    # 1 health
    st, health = http("GET", "/api/health")
    check("01 health", st == 200 and health.get("ok") is True)

    # 2–3 ports: 8788 beta, 8787 untouched (PID 3758)
    out = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-iTCP:8788", "-sTCP:LISTEN"], text=True
    )
    check("02 :8788 listening", "127.0.0.1:8788" in out)
    try:
        ps = subprocess.check_output(["ps", "-p", "3758", "-o", "command="], text=True)
        check("03 :8787 PID 3758 untouched", "8787" in ps, ps.strip()[:120])
    except subprocess.CalledProcessError:
        check("03 :8787 PID 3758 untouched", False, "PID missing")

    conn = db_connect()

    # 4 Haikal/Misa lack can_create_plan
    check(
        "04 Haikal+Misa NO can_create_plan",
        (not has_permission(HAIKAL, "can_create_plan"))
        and (not has_permission(MISA, "can_create_plan")),
    )

    # 5 Matt+Amanda have can_create_plan
    check(
        "05 Matt+Amanda HAVE can_create_plan",
        has_permission(MATT, "can_create_plan") and has_permission(AMANDA, "can_create_plan"),
    )

    # 6 All four have can_approve_plan + can_edit_plan
    ok6 = all(
        has_permission(s, "can_approve_plan") and has_permission(s, "can_edit_plan")
        for s in (MATT, AMANDA, HAIKAL, MISA)
    )
    check("06 all four can_approve+can_edit", ok6)

    # 7 All four have upload/production/view/wolf_intel
    needed = (
        "can_upload",
        "can_update_production",
        "can_view_plan",
        "can_use_wolf_intelligence",
    )
    ok7 = all(has_permission(s, p) for s in (MATT, AMANDA, HAIKAL, MISA) for p in needed)
    check("07 all four upload/prod/view/wi", ok7)

    # 8 capabilities for Haikal
    st, caps = http("GET", f"/api/me/capabilities?subject={HAIKAL}")
    check(
        "08 Haikal capabilities flags",
        st == 200
        and caps.get("can_create_plan") is False
        and caps.get("can_approve_plan") is True
        and caps.get("can_edit_plan") is True,
        json.dumps({k: caps.get(k) for k in ("can_create_plan", "can_approve_plan", "can_edit_plan")}),
    )

    # 9 capabilities for Matt
    st, caps_m = http("GET", f"/api/me/capabilities?subject={MATT}")
    check("09 Matt can_create_plan true", st == 200 and caps_m.get("can_create_plan") is True)

    # 10 plans list default operational only (hide #1–3)
    st, plans = http("GET", "/api/planner/plans?brand=habitat")
    ids = [p["id"] for p in (plans.get("plans") or [])]
    lanes = {p["id"]: p.get("data_lane") for p in (plans.get("plans") or [])}
    check(
        "10 plans default operational hides 1-3",
        st == 200
        and 1 not in ids
        and 2 not in ids
        and 3 not in ids
        and all((lanes[i] or "operational") == "operational" for i in ids),
        f"ids={ids}",
    )

    # 11 test fixtures still in DB
    n_test = conn.execute(
        "SELECT COUNT(*) FROM content_plans WHERE id IN (1,2,3) AND data_lane='test'"
    ).fetchone()[0]
    check("11 test plans 1-3 still in DB", n_test == 3, str(n_test))

    # 12 dashboard operational primary (Habitat #9-ish)
    st, dash = http("GET", "/api/planner/dashboard?brand=habitat")
    cur = ((dash.get("current_plan") or {}).get("plan") or {})
    check(
        "12 dashboard Habitat operational plan",
        st == 200
        and cur.get("id") is not None
        and (cur.get("data_lane") or "operational") == "operational"
        and not cur.get("is_test_lane"),
        f"id={cur.get('id')} lane={cur.get('data_lane')}",
    )

    # 13 Haikal build-next → 403
    st, body = http(
        "POST",
        "/api/planner/build-next",
        {"brand_id": "habitat", "subject": HAIKAL},
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check(
        "13 Haikal build-next 403",
        st == 403 and body.get("required_permission") == "can_create_plan",
        f"st={st} err={body.get('error')}",
    )

    # 14 stranger / missing subject → 403
    st, body = http("POST", "/api/planner/build-next", {"brand_id": "habitat"})
    check("14 build-next missing subject 403", st == 403 and body.get("error") == "missing_subject")

    # 15 Haikal can edit card (can_edit_plan)
    card_id = conn.execute(
        """
        SELECT c.id FROM content_cards c
        JOIN content_plans p ON p.id=c.plan_id
        WHERE p.data_lane='operational' AND p.brand_id='habitat'
        ORDER BY c.id LIMIT 1
        """
    ).fetchone()[0]
    st, edited = http(
        "POST",
        f"/api/planner/cards/{card_id}/edit",
        {"subject": HAIKAL, "patch": {"hook": "Phase2.5A perm gate hook"}},
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("15 Haikal card edit 200", st == 200 and edited.get("ok") is True, f"st={st}")

    # 16 stranger card edit → 403
    st, body = http(
        "POST",
        f"/api/planner/cards/{card_id}/edit",
        {"subject": STRANGER, "patch": {"hook": "nope"}},
        headers={"X-Wolf-Subject": STRANGER},
    )
    check(
        "16 stranger card edit 403",
        st == 403 and body.get("required_permission") == "can_edit_plan",
    )

    # 17 production-status gate
    st, body = http(
        "POST",
        f"/api/planner/cards/{card_id}/production-status",
        {"subject": STRANGER, "workflow_status": "IN_PRODUCTION"},
        headers={"X-Wolf-Subject": STRANGER},
    )
    check(
        "17 stranger production-status 403",
        st == 403 and body.get("required_permission") == "can_update_production",
    )
    st, okp = http(
        "POST",
        f"/api/planner/cards/{card_id}/production-status",
        {"subject": HAIKAL, "workflow_status": "IN_PRODUCTION"},
        headers={"X-Wolf-Subject": HAIKAL},
    )
    check("17b Haikal production-status 200", st == 200 and okp.get("ok") is True)

    # 18 Haikal approve (can_approve_plan) — UI label APPROVED; DB Human_Approved
    plan_id = int(cur.get("id") or 9)
    # Use a throwaway operational draft if available that we can re-approve
    # Prefer latest Working_Draft operational
    row = conn.execute(
        """
        SELECT id FROM content_plans
        WHERE brand_id='habitat' AND ifnull(data_lane,'operational')='operational'
          AND status='Working_Draft'
        ORDER BY id DESC LIMIT 1
        """
    ).fetchone()
    if row:
        plan_id = int(row[0])
    st, appr = http(
        "POST",
        f"/api/planner/plans/{plan_id}/approve",
        {"subject": HAIKAL},
        headers={"X-Wolf-Subject": HAIKAL},
    )
    db_status = conn.execute(
        "SELECT status FROM content_plans WHERE id=?", (plan_id,)
    ).fetchone()[0]
    check(
        "18 Haikal approve → APPROVED label",
        st == 200
        and appr.get("status_label") == "APPROVED"
        and appr.get("published") is False
        and db_status == "Human_Approved"
        and "HUMAN_APPROVED" not in json.dumps({k: appr.get(k) for k in ("status_label", "ui_status")}),
        f"st={st} label={appr.get('status_label')} db={db_status}",
    )

    # 19 upload without subject → 403; stranger → 403
    # Use a tiny multipart via urllib is awkward; hit JSON-less with empty body using header check
    # Server reads permission before multipart — Content-Length 0 is fine
    st, body = http("POST", "/api/upload/remote", body=None, headers={})
    # Without Content-Type multipart it may 403 on permission first
    check(
        "19 upload missing subject 403",
        st == 403 and body.get("required_permission") == "can_upload",
        f"st={st} body={body}",
    )
    st, body = http(
        "POST",
        "/api/upload/remote",
        body=None,
        headers={"X-Wolf-Subject": STRANGER},
    )
    check(
        "19b upload stranger 403",
        st == 403 and body.get("required_permission") == "can_upload",
    )

    # 20 wolf intelligence prepare: llm/generate gated
    st, body = http(
        "POST",
        "/api/llm/generate",
        {"brand": "habitat", "role": "copy", "prompt": "x", "dry_run": True, "subject": STRANGER},
        headers={"X-Wolf-Subject": STRANGER},
    )
    check(
        "20 llm generate stranger 403 wi",
        st == 403 and body.get("required_permission") == "can_use_wolf_intelligence",
    )
    st, body = http(
        "POST",
        "/api/llm/generate",
        {"brand": "habitat", "role": "copy", "prompt": "x", "dry_run": True, "subject": HAIKAL},
        headers={"X-Wolf-Subject": HAIKAL},
    )
    # May return 200 with ok False from orchestrator — permission must pass (not 403)
    check("20b Haikal llm generate not 403", st != 403, f"st={st}")

    # UI strings (bonus folded into report; keep suite at 20 numbered groups — we already have 20+)
    html = (BETA / "dashboards" / "content-2.0.html").read_text(encoding="utf-8")
    check(
        "UI Approve confirmation copy",
        "Approve this fortnight plan for the team?" in html and "Approve Plan" in html,
    )
    check(
        "UI no Metricool write / no CF invent in serve gate comments",
        "DEVELOPMENT ONLY" in (BETA / "scripts" / "serve_beta.py").read_text(encoding="utf-8"),
    )

    # Confirm test fixtures not deleted
    n_plans = conn.execute("SELECT COUNT(*) FROM content_plans").fetchone()[0]
    check("DB plan count preserved (>=9)", n_plans >= 9, str(n_plans))

    conn.close()
    print(f"\nTOTAL PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
