#!/usr/bin/env python3
"""Phase 1 Habitat acceptance suite (~19 checks)."""
from __future__ import annotations

import json
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

BETA = Path("/Users/wolfterminal/beta-os")
DB = BETA / "catalog" / "content_library.sqlite"
BASE = "http://127.0.0.1:8788"
SUBJECT_OK = "mrwolf@wolfcommand.net"
SUBJECT_DENY = "nobody@example.com"

sys.path.insert(0, str(BETA / "scripts"))
from wolf_intelligence import has_permission, write_memory_item, db_connect  # noqa: E402

PASS = 0
FAIL = 0
RESULTS = []


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        RESULTS.append(("PASS", name, detail))
        print(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        RESULTS.append(("FAIL", name, detail))
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def http(method: str, path: str, body: dict | None = None, headers: dict | None = None, expect_status: int | None = None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            payload = json.loads(raw) if raw else {}
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw}
        status = e.code
    if expect_status is not None:
        check(f"HTTP {method} {path} status", status == expect_status, f"got {status}")
    return status, payload


def main() -> int:
    # 1 health
    st, health = http("GET", "/api/health")
    check("1 health ok", st == 200 and health.get("ok") is True)

    # 2–4 ports: 8788 beta, 8787 wolf untouched
    import subprocess
    out = subprocess.check_output(
        ["lsof", "-nP", "-iTCP:8787", "-iTCP:8788", "-sTCP:LISTEN"], text=True
    )
    beta_pid = subprocess.check_output(["lsof", "-t", "-nP", "-iTCP:8788", "-sTCP:LISTEN"], text=True).strip().splitlines()[0]
    beta_cmd = subprocess.check_output(["ps", "-p", beta_pid, "-o", "command="], text=True)
    check("2 :8788 serve_beta running", "serve_beta.py" in beta_cmd and "127.0.0.1:8788" in out, beta_cmd.strip()[:140])
    check("3 :8787 still listening", "127.0.0.1:8787" in out, "port line present")
    try:
        ps = subprocess.check_output(["ps", "-p", "3758", "-o", "command="], text=True)
        check("4 wolf PID 3758 alive", "serve.py" in ps and "8787" in ps, ps.strip()[:100])
    except subprocess.CalledProcessError:
        check("4 wolf PID 3758 alive", False, "PID 3758 missing")

    # 5 schema tables exist
    conn = sqlite3.connect(str(DB))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    needed = {
        "brands", "permissions", "memory_items", "evidence_items",
        "content_plans", "plan_revisions", "content_cards", "card_revisions", "skill_runs",
    }
    check("5 phase1 tables present", needed.issubset(tables), str(sorted(needed - tables)))

    # 6 integrity
    ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
    check("6 integrity_check ok", ok == "ok", ok)

    # 7 brands seed
    b = conn.execute("SELECT display_name FROM brands WHERE id='habitat'").fetchone()
    check("7 habitat brand seeded", bool(b) and "Habitat" in b[0], str(b))

    # 8 permissions seed count
    nperm = conn.execute("SELECT COUNT(*) FROM permissions WHERE permission='can_create_plan'").fetchone()[0]
    check("8 can_create_plan seeds >=4", nperm >= 4, str(nperm))

    # 9 has_permission helper
    check("9 has_permission true for mrwolf", has_permission(SUBJECT_OK, "can_create_plan"))
    check("10 has_permission false for stranger", not has_permission(SUBJECT_DENY, "can_create_plan"))

    # 11 ACTIVE only if APPROVED
    bad = conn.execute(
        "SELECT COUNT(*) FROM memory_items WHERE status='ACTIVE' AND approval_state!='APPROVED'"
    ).fetchone()[0]
    check("11 no ACTIVE without APPROVED", bad == 0, str(bad))

    # 12 memory import counts
    active = conn.execute(
        "SELECT COUNT(*) FROM memory_items WHERE brand_id='habitat' AND status='ACTIVE' AND approval_state='APPROVED'"
    ).fetchone()[0]
    check("12 habitat ACTIVE memory >0", active >= 10, str(active))

    # 13 GET brands
    st, brands = http("GET", "/api/brands")
    check("13 GET /api/brands", st == 200 and brands.get("count", 0) >= 1)

    # 14 build-next without subject → 403
    st, body = http("POST", "/api/planner/build-next", {"brand_id": "habitat"}, expect_status=403)
    check("14 build-next missing subject 403", st == 403 and body.get("error") == "missing_subject")

    # 15 build-next denied subject → 403
    st, body = http(
        "POST",
        "/api/planner/build-next",
        {"brand_id": "habitat", "subject": SUBJECT_DENY},
        headers={"X-Wolf-Subject": SUBJECT_DENY},
        expect_status=403,
    )
    check("15 build-next denied 403", st == 403)

    # 16 build-next ok
    st, draft = http(
        "POST",
        "/api/planner/build-next",
        {"brand_id": "habitat", "subject": SUBJECT_OK},
        headers={"X-Wolf-Subject": SUBJECT_OK},
    )
    check("16 build-next Working Draft", st == 200 and draft.get("ok") and draft.get("plan_id"), str(draft.get("plan_id")))
    plan_id = draft.get("plan_id")
    feed_n = len(draft.get("feed_cards") or [])
    story_n = len(draft.get("story_spine") or [])
    check("17 ~3 feed cards", feed_n == 3, str(feed_n))
    check("18 ~14 story spine", story_n == 14, str(story_n))

    # 19 FILM allowed without assets
    filmish = all((c.get("asset_status") == "FILM") for c in (draft.get("feed_cards") or []))
    check("19 feed cards FILM without media", filmish)

    # 20 shot list note present
    note_ok = any(
        "Suggested coverage" in str((c.get("shot_list_note") or ""))
        for c in (draft.get("feed_cards") or [])
    )
    check("20 shot list adapt note", note_ok)

    # 21 checklist has placeholders for disconnected
    cl = draft.get("checklist") or []
    check("21 checklist has placeholders", any(i.get("status") == "placeholder" for i in cl), str(len(cl)))

    # 22 GET plan
    st, got = http("GET", f"/api/planner/plans/{plan_id}")
    check("22 GET Working Draft", st == 200 and got.get("ok"))

    # 23 AI_PROPOSAL revision exists
    ai = conn.execute(
        "SELECT COUNT(*) FROM plan_revisions WHERE plan_id=? AND role='AI_PROPOSAL'",
        (plan_id,),
    ).fetchone()[0]
    check("23 AI_PROPOSAL plan revision", ai >= 1, str(ai))

    # 24 card edit HUMAN_EDIT retains AI_PROPOSAL
    card_id = (got.get("feed_cards") or [{}])[0].get("id")
    st, edited = http(
        "POST",
        f"/api/planner/cards/{card_id}/edit",
        {"subject": SUBJECT_OK, "patch": {"hook": "Edited hook — timber and concrete, specifically."}},
        headers={"X-Wolf-Subject": SUBJECT_OK},
    )
    check("24 card HUMAN_EDIT ok", st == 200 and edited.get("card", {}).get("ai_proposal_retained") is True)
    ai_card = conn.execute(
        "SELECT COUNT(*) FROM card_revisions WHERE card_id=? AND role='AI_PROPOSAL'",
        (card_id,),
    ).fetchone()[0]
    hu_card = conn.execute(
        "SELECT COUNT(*) FROM card_revisions WHERE card_id=? AND role='HUMAN_EDIT'",
        (card_id,),
    ).fetchone()[0]
    check("25 AI_PROPOSAL card revision retained", ai_card >= 1 and hu_card >= 1, f"ai={ai_card} hu={hu_card}")

    # 26 plan edit
    st, _ = http(
        "POST",
        f"/api/planner/plans/{plan_id}/edit",
        {"subject": SUBJECT_OK, "patch": {"title": "Habitat fortnight (human titled)"}},
        headers={"X-Wolf-Subject": SUBJECT_OK},
    )
    check("26 plan HUMAN_EDIT", st == 200)
    hu_plan = conn.execute(
        "SELECT COUNT(*) FROM plan_revisions WHERE plan_id=? AND role='HUMAN_EDIT'",
        (plan_id,),
    ).fetchone()[0]
    check("27 plan HUMAN_EDIT revision row", hu_plan >= 1, str(hu_plan))

    # 28 approve does not publish
    st, appr = http(
        "POST",
        f"/api/planner/plans/{plan_id}/approve",
        {"subject": SUBJECT_OK},
        headers={"X-Wolf-Subject": SUBJECT_OK},
    )
    check("28 approve ok not published", st == 200 and appr.get("published") is False)
    status = conn.execute("SELECT status FROM content_plans WHERE id=?", (plan_id,)).fetchone()[0]
    check("29 plan status Human_Approved", status == "Human_Approved", status)
    ha = conn.execute(
        "SELECT COUNT(*) FROM plan_revisions WHERE plan_id=? AND role='HUMAN_APPROVED'",
        (plan_id,),
    ).fetchone()[0]
    check("30 HUMAN_APPROVED revision", ha >= 1, str(ha))

    # 31 skill_runs logged
    sr = conn.execute("SELECT COUNT(*) FROM skill_runs WHERE plan_id=?", (plan_id,)).fetchone()[0]
    check("31 skill_runs logged >=7", sr >= 7, str(sr))

    # 32 UI has Wolf Intelligence, no provider names in section (file scan)
    html = (BETA / "dashboards" / "content-2.0.html").read_text(encoding="utf-8")
    check("32 UI Wolf Intelligence section", "Wolf Intelligence" in html and "wiBuildNext" in html)
    # narrow: intelligenceView chunk
    i0 = html.find('id="intelligenceView"')
    chunk = html[i0:i0 + 3000]
    banned = ["OpenAI", "Anthropic", "Gemini", "Claude", "Muse", "Indigo", "Velvet", "Peaches"]
    check("33 UI section no provider/agent names", not any(b in chunk for b in banned))

    # 34 foreign_keys on connection helper
    src = (BETA / "scripts" / "serve_beta.py").read_text(encoding="utf-8")
    check("34 serve_beta PRAGMA foreign_keys", "PRAGMA foreign_keys=ON" in src)

    # 35 disconnected honesty in strategy
    check(
        "35 strategy marks disconnected data",
        "not connected" in json.dumps(draft.get("strategy") or {}),
    )

    conn.close()
    print(f"\nTOTAL PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
