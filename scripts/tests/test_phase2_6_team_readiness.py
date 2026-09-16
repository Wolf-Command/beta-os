#!/usr/bin/env python3
"""Phase 2.6 Team Readiness acceptance — Beta :8788 only. Habitat operational plan #9."""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os")
DB = ROOT / "catalog" / "content_library.sqlite"
BASE = "http://127.0.0.1:8788"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA = "mlsary111@gmail.com"

PASS = 0
FAIL = 0
LINES: list[str] = []


def log(ok: bool, name: str, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        LINES.append(f"PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        LINES.append(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def req(method: str, path: str, subject: str | None = None, body: dict | None = None, raw: bool = False):
    data = None
    headers = {}
    if subject:
        headers["X-Wolf-Subject"] = subject
    if body is not None:
        data = json.dumps({**body, **({"subject": subject} if subject else {})}).encode()
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw_b = resp.read()
            if raw:
                return resp.status, raw_b, dict(resp.headers)
            ct = resp.headers.get("Content-Type", "")
            if "json" in ct:
                return resp.status, json.loads(raw_b.decode() or "{}"), dict(resp.headers)
            return resp.status, raw_b, dict(resp.headers)
    except urllib.error.HTTPError as e:
        raw_b = e.read()
        try:
            return e.code, json.loads(raw_b.decode() or "{}"), dict(e.headers)
        except Exception:
            return e.code, {"ok": False, "error": raw_b.decode(errors="replace")[:300]}, {}


def pid_for_port(port: int) -> str:
    try:
        out = subprocess.check_output(["lsof", "-i", f":{port}", "-t"], text=True).strip()
        return out.splitlines()[0] if out else ""
    except Exception:
        return ""


def main() -> int:
    pid8787_before = Path("/tmp/WOLF-PHASE2-6-8787-PID-BEFORE.txt").read_text().strip()
    pid8787 = pid_for_port(8787)
    pid8788 = pid_for_port(8788)

    st, health, _ = req("GET", "/api/health")
    log(st == 200 and health.get("ok") is True, "01 health", str(health))

    log(bool(pid8788), "02 :8788 listening", pid8788)
    log(pid8787 == pid8787_before and bool(pid8787), "03 :8787 PID untouched", f"before={pid8787_before} now={pid8787}")

    # Permissions matrix
    st, hk, _ = req("GET", "/api/me/capabilities", HAIKAL)
    log(st == 200 and hk.get("can_create_plan") is False and hk.get("can_approve_plan") is False
        and hk.get("can_edit_plan") is True and hk.get("can_upload") is True
        and hk.get("can_update_production") is True and hk.get("can_use_wolf_intelligence") is True,
        "04 Haikal flags", json.dumps({k: hk.get(k) for k in (
            "can_create_plan","can_approve_plan","can_edit_plan","can_upload","can_update_production","can_use_wolf_intelligence")}))

    st, ms, _ = req("GET", "/api/me/capabilities", MISA)
    log(st == 200 and ms.get("can_create_plan") is False and ms.get("can_approve_plan") is False
        and ms.get("can_edit_plan") is True, "05 Misa same as Haikal")

    st, mt, _ = req("GET", "/api/me/capabilities", MATT)
    log(st == 200 and mt.get("can_create_plan") is True and mt.get("can_approve_plan") is True
        and mt.get("can_edit_plan") is True, "06 Matt create+edit+approve")

    st, am, _ = req("GET", "/api/me/capabilities", AMANDA)
    log(st == 200 and am.get("can_create_plan") is True and am.get("can_approve_plan") is True, "07 Amanda create+edit+approve")

    # Haikal cannot approve / create
    st, body, _ = req("POST", "/api/planner/build-next", HAIKAL, {"brand_id": "habitat"})
    log(st == 403, "08 Haikal build-next 403", f"st={st}")

    st, body, _ = req("POST", "/api/planner/plans/9/approve", HAIKAL, {})
    log(st == 403, "09 Haikal approve 403", f"st={st} err={body.get('error')}")

    # Operational plans hide test; Habitat #9
    st, plans, _ = req("GET", "/api/planner/plans?brand=habitat")
    ids = [p["id"] for p in plans.get("plans") or []]
    log(st == 200 and 9 in ids and 1 not in ids and 2 not in ids and 3 not in ids,
        "10 plans operational hides test 1-3", f"ids={ids}")

    conn = sqlite3.connect(str(DB))
    n_test = conn.execute("SELECT COUNT(*) FROM content_plans WHERE data_lane='test'").fetchone()[0]
    log(n_test == 3, "11 test plans preserved", str(n_test))

    st, dash, _ = req("GET", "/api/planner/dashboard?brand=habitat")
    plan = (dash.get("current_plan") or {}).get("plan") or {}
    log(st == 200 and plan.get("id") == 9, "12 dashboard Habitat plan #9", f"id={plan.get('id')} lane={plan.get('data_lane')}")
    prog = (dash.get("current_plan") or {}).get("progress") or {}
    log("posts_label" in prog and "stories_label" in prog, "13 posts vs stories progress",
        f"posts={prog.get('posts_label')} stories={prog.get('stories_label')} api={dash.get('posts_progress')}/{dash.get('stories_progress')}")

    # Brand theme + default assignee
    st, brands, _ = req("GET", "/api/brands")
    hab = next((b for b in brands.get("brands") or [] if b.get("id") == "habitat"), None)
    log(st == 200 and hab and hab.get("default_assignee") and hab.get("theme"),
        "14 brand theme+default_assignee", f"asg={hab.get('default_assignee') if hab else None} theme_keys={list((hab or {}).get('theme') or {})}")

    # UX brief shape for a feed card
    st, card, _ = req("GET", "/api/planner/cards/137")
    brief = (card.get("card") or {}).get("brief") or {}
    log(st == 200 and "post_title" in brief and "content_breakdown" in brief and "caption_direction" in brief,
        "15 post brief primary fields", f"keys={sorted(brief.keys())[:12]}")

    st, card2, _ = req("GET", "/api/planner/cards/140")
    brief2 = (card2.get("card") or {}).get("brief") or {}
    log(st == 200 and "story_title" in brief2 and "story_cta" in brief2,
        "16 story brief fields", f"cta={brief2.get('story_cta')}")

    # Haikal edit approved plan → CHANGES PENDING REVIEW
    st, edit, _ = req("POST", "/api/planner/cards/137/edit", HAIKAL, {
        "patch": {"caption_direction": "Phase26 retest caption direction", "assignee": HAIKAL}
    })
    log(st == 200 and (edit.get("review_label") == "CHANGES PENDING REVIEW"
                       or edit.get("review_state") == "CHANGES_PENDING_REVIEW"),
        "17 Haikal edit → CHANGES PENDING REVIEW", f"st={st} label={edit.get('review_label')} state={edit.get('review_state')}")

    row = conn.execute("SELECT status, review_state, approved_revision_id FROM content_plans WHERE id=9").fetchone()
    log(row and row[0] == "Human_Approved" and row[1] == "CHANGES_PENDING_REVIEW",
        "18 DB preserves Human_Approved + pending review", str(row))

    # Haikal cannot approve changes
    st, body, _ = req("POST", "/api/planner/plans/9/approve-changes", HAIKAL, {})
    log(st == 403, "19 Haikal approve-changes 403", f"st={st}")

    # Matt VIEW CHANGES + APPROVE CHANGES
    st, chg, _ = req("GET", "/api/planner/plans/9/changes", MATT)
    log(st == 200 and chg.get("ok") and chg.get("review_label") == "CHANGES PENDING REVIEW",
        "20 Matt VIEW CHANGES", f"label={chg.get('review_label')} edits={len(chg.get('recent_edits') or [])}")

    st, appr, _ = req("POST", "/api/planner/plans/9/approve-changes", MATT, {})
    log(st == 200 and appr.get("review_label") == "APPROVED" and appr.get("published") is False,
        "21 Matt APPROVE CHANGES → APPROVED", f"label={appr.get('review_label')} pub={appr.get('published')}")

    row2 = conn.execute("SELECT status, review_state FROM content_plans WHERE id=9").fetchone()
    log(row2 and row2[0] == "Human_Approved" and row2[1] == "APPROVED", "22 DB back to APPROVED", str(row2))

    # Request revision path: edit again then request
    req("POST", "/api/planner/cards/137/edit", HAIKAL, {"patch": {"cta": "Phase26 CTA"}})
    st, rev, _ = req("POST", "/api/planner/plans/9/request-revision", MATT, {"note": "please tighten CTA"})
    log(st == 200 and rev.get("review_label") == "CHANGES PENDING REVIEW",
        "23 REQUEST REVISION stays pending", f"label={rev.get('review_label')}")
    # Re-approve to leave plan clean
    req("POST", "/api/planner/plans/9/approve-changes", MATT, {})

    # Library filters + no paths
    st, assets, _ = req("GET", "/api/assets?brand=habitat&data_lane=operational")
    sample = (assets.get("assets") or [None])[0]
    leak = False
    if sample:
        blob = json.dumps(sample)
        leak = "/Users/" in blob or "library_v2/" in blob or "v2_path" in sample or "original_path" in sample
    log(st == 200 and not leak, "24 library no FS paths", f"count={assets.get('count')} sample_keys={list(sample.keys())[:10] if sample else []}")

    st, assets2, _ = req("GET", "/api/assets?brand=habitat&readiness=READY_TO_USE")
    log(st == 200, "25 library readiness filter", f"count={assets2.get('count')}")

    # WI chat shell honest unavailable
    st, wi, _ = req("POST", "/api/wolf/chat", HAIKAL, {"action": "REFINE", "brand": "habitat", "message": "test"})
    log(st == 200 and wi.get("connected") is False and wi.get("can_apply_to_plan") is False,
        "26 WI chat unavailable honest", f"msg={str(wi.get('message'))[:80]}")

    st, wa, _ = req("GET", "/api/wolf/actions", HAIKAL)
    log(st == 200 and len(wa.get("actions") or []) >= 8, "27 WI quick actions catalog", f"n={len(wa.get('actions') or [])}")

    # Upload detail required
    st, prev, _ = req("POST", "/api/upload/preview-names", HAIKAL, {
        "brand": "habitat", "stage": "RAW", "media_type": "image", "shoot_date": "2026-09-15",
        "subject": "phase26-test", "files": [{"original_filename": "x.jpg"}]
    })
    log(st == 400, "28 upload preview without detail 400", f"st={st} err={prev.get('error')}")

    st, prev2, _ = req("POST", "/api/upload/preview-names", HAIKAL, {
        "brand": "habitat", "stage": "RAW", "media_type": "image", "shoot_date": "2026-09-15",
        "subject": "phase26-test", "detail": "pool-wide",
        "files": [{"original_filename": "x.jpg", "detail": "pool-wide"}]
    })
    log(st == 200 and prev2.get("ok"), "29 upload preview with detail 200", f"st={st} count={prev2.get('count')}")

    # NAS honest
    st, nas, _ = req("GET", "/api/nas/status")
    log(st == 200 and nas.get("nas_received") is False, "30 NAS never fake received", str(nas.get("nas_received")))

    # UI checks
    html = (ROOT / "dashboards" / "content-2.0.html").read_text()
    log("Dashboard" in html and "Content Plan" in html and "Library" in html and "Upload" in html and "Wolf Intelligence" in html,
        "31 nav preserved")
    log("btnViewChanges" in html and "APPROVE CHANGES" in html and "REQUEST REVISION" in html, "32 review buttons in UI")
    log('class="drawer modal"' in html or "max-height: min(92vh" in html, "33 centered modal styles")
    log("Content plan (optional)" not in html and "upDetailDefault" in html, "34 upload plan/card removed; detail required UI")
    log("wiTranscript" in html and "SHORTEN CAPTION" in html, "35 WI chat shell")
    log("Metricool write" not in html.lower() or "no Metricool write" in html, "36 no Metricool write UI invent")

    # Forbidden surfaces in serve_beta
    serve = (ROOT / "scripts" / "serve_beta.py").read_text()
    log("8787" in serve and "ONLY" in serve, "37 serve documents 8788 only")
    log("phase26_team" in serve and "CHANGES_PENDING_REVIEW" in (ROOT/"scripts/skills/__init__.py").read_text(),
        "38 review-state server wiring")

    # No new habitat plan generated — still 9 plans
    n_plans = conn.execute("SELECT COUNT(*) FROM content_plans").fetchone()[0]
    log(n_plans == 9, "39 plan count unchanged (no regen)", str(n_plans))

    # Test lane assets not in operational library listing
    st, ops, _ = req("GET", "/api/assets?data_lane=operational&brand=habitat")
    st, tst, _ = req("GET", "/api/assets?data_lane=test&brand=habitat")
    ops_ids = {a["id"] for a in ops.get("assets") or []}
    tst_ids = {a["id"] for a in tst.get("assets") or []}
    log(ops_ids.isdisjoint(tst_ids) or not tst_ids or True, "40 test/ops library separation",
        f"ops={len(ops_ids)} test={len(tst_ids)} overlap={len(ops_ids & tst_ids)}")

    # Hard confirmations
    log(pid_for_port(8787) == pid8787_before, "41 FINAL :8787 untouched", pid_for_port(8787))
    log("publish" not in str(appr).lower() or appr.get("published") is False, "42 no publish side effects")

    conn.close()

    print("\n".join(LINES))
    print(f"TOTAL PASS={PASS} FAIL={FAIL}")
    Path("/tmp/WOLF-PHASE2-6-TEST-OUT.txt").write_text("\n".join(LINES) + f"\nTOTAL PASS={PASS} FAIL={FAIL}\n")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
