"""Phase 2 dry skills orchestrator — no paid LLM / no provider names in output."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wolf_intelligence import (  # noqa: E402
    fortnight_bounds,
    log_skill_run,
    now_iso,
)

from . import (  # noqa: E402
    build_evidence_pack,
    build_fortnight_strategy,
    check_asset_status,
    generate_feed_cards,
    generate_story_spine,
    load_brand_memory,
    load_metricool_evidence,
    load_recent_plans,
    validate_brand_rules,
)

# Order for checklist display (wired skills)
SKILL_ORDER = [
    ("load_brand_memory", load_brand_memory),
    ("load_recent_plans", load_recent_plans),
    ("load_metricool_evidence", load_metricool_evidence),
    ("check_asset_status_pre", check_asset_status),  # placeholder name; real asset check later
    ("build_evidence_pack", build_evidence_pack),
    ("build_fortnight_strategy", build_fortnight_strategy),
    ("generate_feed_cards", generate_feed_cards),
    ("generate_story_spine", generate_story_spine),
    ("check_asset_status", check_asset_status),
    ("validate_brand_rules", validate_brand_rules),
]


def build_checklist(skill_results: dict[str, dict]) -> list[dict]:
    """UI checklist — no provider names. Performance reviewed when Metricool evidence used."""
    steps = []
    mapping = [
        ("load_brand_memory", "Brand Memory"),
        ("load_recent_plans", "Previous Plans"),
        ("load_metricool_evidence", "Performance reviewed"),
        ("build_evidence_pack", "Evidence Pack"),
        ("build_fortnight_strategy", "Strategy"),
        ("generate_feed_cards", "Feed Cards"),
        ("generate_story_spine", "Story Spine"),
        ("check_asset_status", "Asset State"),
        ("validate_brand_rules", "Brand Rules"),
    ]
    for key, label in mapping:
        r = skill_results.get(key) or {}
        if key == "load_metricool_evidence":
            avail = bool((r.get("result") or {}).get("available"))
            steps.append(
                {
                    "step": label,
                    "status": "done" if avail else "placeholder",
                    "note": None if avail else "Performance unavailable",
                    "confidence": r.get("confidence"),
                    "missing": r.get("missing_information") or [],
                }
            )
        else:
            steps.append(
                {
                    "step": label,
                    "status": "done",
                    "confidence": r.get("confidence"),
                    "missing": r.get("missing_information") or [],
                }
            )
    steps.extend(
        [
            {"step": "Trend signals", "status": "placeholder", "note": "not connected"},
            {"step": "Inspiration library", "status": "placeholder", "note": "not connected"},
            {"step": "Publish / schedule", "status": "placeholder", "note": "out of Phase 2 — no publish"},
        ]
    )
    return steps


def orchestrate_build_next(conn, brand_id: str, subject: str) -> dict[str, Any]:
    """Brand Memory + Previous Plans + Metricool Evidence + Asset State
    → Evidence Pack → Strategy → Working Draft.

    Soft-fail if Metricool down — plan still builds with Performance unavailable.
    Freezes planning_context_snapshot linked to plan + AI_PROPOSAL revision.
    """
    results: dict[str, dict] = {}
    data_lane = "operational"

    mem = load_brand_memory.run(conn, brand_id)
    results["load_brand_memory"] = mem

    recent = load_recent_plans.run(conn, brand_id, for_learning=True)
    results["load_recent_plans"] = recent

    # Soft-fail Metricool evidence
    try:
        metricool = load_metricool_evidence.run(conn, brand_id, data_lane="operational")
    except Exception as exc:  # noqa: BLE001
        metricool = {
            "result": {"brand_key": brand_id, "available": False, "note": "Performance unavailable"},
            "evidence": [],
            "confidence": 0.1,
            "assumptions": ["Metricool evidence soft-failed"],
            "missing_information": [f"Performance unavailable ({type(exc).__name__})"],
        }
    results["load_metricool_evidence"] = metricool

    # Asset state before pack (library counts) — empty feed/story ok
    assets_pre = check_asset_status.run(conn, brand_id, feed_result=None, story_result=None)
    results["check_asset_status_pre"] = assets_pre

    pack = build_evidence_pack.run(
        conn,
        brand_id,
        memory_result=mem,
        recent_plans_result=recent,
        metricool_result=metricool,
        asset_result=assets_pre,
    )
    results["build_evidence_pack"] = pack

    strat = build_fortnight_strategy.run(
        conn, brand_id, memory_result=mem, evidence_pack=pack
    )
    results["build_fortnight_strategy"] = strat

    feed = generate_feed_cards.run(conn, brand_id, strategy_result=strat)
    results["generate_feed_cards"] = feed
    stories = generate_story_spine.run(conn, brand_id, strategy_result=strat)
    results["generate_story_spine"] = stories
    assets = check_asset_status.run(conn, brand_id, feed_result=feed, story_result=stories)
    results["check_asset_status"] = assets
    validated = validate_brand_rules.run(conn, brand_id, asset_result=assets)
    results["validate_brand_rules"] = validated

    strategy = strat.get("result") or {}
    period_start = strategy.get("period_start") or fortnight_bounds()[0]
    period_end = strategy.get("period_end") or fortnight_bounds()[1]
    checklist = build_checklist(results)
    ts = now_iso()

    cur = conn.execute(
        """
        INSERT INTO content_plans (
          brand_id, title, period_start, period_end, status,
          strategy_json, checklist_json, created_by, created_at, updated_at, data_lane
        ) VALUES (?, ?, ?, ?, 'Working_Draft', ?, ?, ?, ?, ?, ?)
        """,
        (
            brand_id,
            f"{brand_id} fortnight {period_start} → {period_end}",
            period_start,
            period_end,
            json.dumps(strategy),
            json.dumps(checklist),
            subject,
            ts,
            ts,
            data_lane,
        ),
    )
    plan_id = int(cur.lastrowid)

    feed_cards = list((validated.get("result") or assets.get("result") or {}).get("feed_cards") or [])
    story_spine = list((validated.get("result") or assets.get("result") or {}).get("story_spine") or [])

    full_snapshot = {
        "plan_id": plan_id,
        "brand_id": brand_id,
        "strategy": strategy,
        "feed_cards": feed_cards,
        "story_spine": story_spine,
        "checklist": checklist,
        "validation": validated.get("result"),
        "evidence_pack": pack.get("result"),
        "metricool_evidence_used": bool(strategy.get("metricool_evidence_used")),
    }
    rcur = conn.execute(
        """
        INSERT INTO plan_revisions (plan_id, role, full_json, diff_json, actor, created_at, data_lane)
        VALUES (?, 'AI_PROPOSAL', ?, NULL, ?, ?, ?)
        """,
        (plan_id, json.dumps(full_snapshot), subject, ts, data_lane),
    )
    plan_revision_id = int(rcur.lastrowid)

    card_ids = []
    for c in feed_cards + story_spine:
        body = {
            k: v
            for k, v in c.items()
            if k not in ("card_type", "sequence", "title", "asset_status", "status")
        }
        ccur = conn.execute(
            """
            INSERT INTO content_cards (
              plan_id, card_type, sequence, title, body_json, asset_status, status, created_at, updated_at, data_lane
            ) VALUES (?, ?, ?, ?, ?, ?, 'AI_PROPOSAL', ?, ?, ?)
            """,
            (
                plan_id,
                c.get("card_type") or "feed",
                c.get("sequence") or 0,
                c.get("title"),
                json.dumps(body),
                c.get("asset_status") or "FILM",
                ts,
                ts,
                data_lane,
            ),
        )
        cid = int(ccur.lastrowid)
        card_ids.append(cid)
        conn.execute(
            """
            INSERT INTO card_revisions (card_id, role, full_json, diff_json, actor, created_at, data_lane)
            VALUES (?, 'AI_PROPOSAL', ?, NULL, ?, ?, ?)
            """,
            (cid, json.dumps(c), subject, ts, data_lane),
        )

    snap_id = build_evidence_pack.freeze_planning_context_snapshot(
        conn,
        brand_key=brand_id,
        plan_id=plan_id,
        plan_revision_id=plan_revision_id,
        subject=subject,
        memory_result=mem,
        recent_plans_result=recent,
        metricool_result=metricool,
        asset_result=assets,
        evidence_pack=pack,
        data_lane=data_lane,
    )

    for name, payload in results.items():
        if name == "check_asset_status_pre":
            continue
        log_skill_run(
            conn,
            skill_name=name,
            brand_id=brand_id,
            plan_id=plan_id,
            payload={
                "input": {"brand_id": brand_id},
                "result": payload.get("result"),
                "evidence": payload.get("evidence"),
                "confidence": payload.get("confidence"),
                "assumptions": payload.get("assumptions"),
                "missing_information": payload.get("missing_information"),
                "status": "ok",
            },
            data_lane=data_lane,
        )

    conn.commit()
    return {
        "plan_id": plan_id,
        "brand_id": brand_id,
        "status": "Working_Draft",
        "period_start": period_start,
        "period_end": period_end,
        "strategy": strategy,
        "feed_cards": feed_cards,
        "story_spine": story_spine,
        "checklist": checklist,
        "card_ids": card_ids,
        "planning_context_snapshot_id": snap_id,
        "metricool_evidence_used": bool(strategy.get("metricool_evidence_used")),
        "skill_results_summary": {
            k: {
                "confidence": v.get("confidence"),
                "missing_information": v.get("missing_information"),
            }
            for k, v in results.items()
            if k != "check_asset_status_pre"
        },
        "identity_note": (
            "resolve_authenticated_subject: X-Wolf-Subject / JSON subject is DEVELOPMENT ONLY. "
            "Cloudflare Access JWT not wired yet."
        ),
    }


def get_plan_working_draft(conn, plan_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM content_plans WHERE id=?", (plan_id,)).fetchone()
    if not row:
        return None
    plan = dict(row)
    cards = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM content_cards WHERE plan_id=? ORDER BY card_type, sequence",
            (plan_id,),
        ).fetchall()
    ]
    for c in cards:
        try:
            c["body"] = json.loads(c.get("body_json") or "{}")
        except json.JSONDecodeError:
            c["body"] = {}
    revs = [
        dict(r)
        for r in conn.execute(
            "SELECT id, plan_id, role, actor, created_at FROM plan_revisions WHERE plan_id=? ORDER BY id",
            (plan_id,),
        ).fetchall()
    ]
    try:
        strategy = json.loads(plan.get("strategy_json") or "{}")
    except json.JSONDecodeError:
        strategy = {}
    try:
        checklist = json.loads(plan.get("checklist_json") or "[]")
    except json.JSONDecodeError:
        checklist = []
    snap = conn.execute(
        "SELECT id, content_hash, created_at FROM planning_context_snapshots WHERE plan_id=? ORDER BY id DESC LIMIT 1",
        (plan_id,),
    ).fetchone()
    return {
        "plan": {
            "id": plan["id"],
            "brand_id": plan["brand_id"],
            "title": plan["title"],
            "period_start": plan["period_start"],
            "period_end": plan["period_end"],
            "status": plan["status"],
            "created_by": plan["created_by"],
            "created_at": plan["created_at"],
            "updated_at": plan["updated_at"],
            "data_lane": plan["data_lane"] if "data_lane" in plan.keys() else None,
            "review_state": plan["review_state"] if "review_state" in plan.keys() else None,
            "approved_revision_id": plan["approved_revision_id"] if "approved_revision_id" in plan.keys() else None,
        },
        "strategy": strategy,
        "checklist": checklist,
        "feed_cards": [c for c in cards if c["card_type"] == "feed"],
        "story_spine": [c for c in cards if c["card_type"] == "story"],
        "plan_revisions": revs,
        "planning_context_snapshot": dict(snap) if snap else None,
    }


def human_edit_plan(conn, plan_id: int, patch: dict, subject: str) -> dict:
    row = conn.execute("SELECT * FROM content_plans WHERE id=?", (plan_id,)).fetchone()
    if not row:
        raise KeyError("plan not found")
    plan = dict(row)
    ts = now_iso()
    before = get_plan_working_draft(conn, plan_id)
    if "title" in patch:
        conn.execute("UPDATE content_plans SET title=?, updated_at=? WHERE id=?", (patch["title"], ts, plan_id))
    if "strategy" in patch:
        conn.execute(
            "UPDATE content_plans SET strategy_json=?, updated_at=? WHERE id=?",
            (json.dumps(patch["strategy"]), ts, plan_id),
        )
    after = get_plan_working_draft(conn, plan_id)
    diff = {"before_title": plan.get("title"), "patch": patch}
    lane = plan["data_lane"] if "data_lane" in plan.keys() else "operational"
    conn.execute(
        """
        INSERT INTO plan_revisions (plan_id, role, full_json, diff_json, actor, created_at, data_lane)
        VALUES (?, 'HUMAN_EDIT', ?, ?, ?, ?, ?)
        """,
        (plan_id, json.dumps(after), json.dumps(diff), subject, ts, lane),
    )
    conn.commit()
    return after


def human_edit_card(conn, card_id: int, patch: dict, subject: str) -> dict:
    row = conn.execute("SELECT * FROM content_cards WHERE id=?", (card_id,)).fetchone()
    if not row:
        raise KeyError("card not found")
    card = dict(row)
    ts = now_iso()
    try:
        body = json.loads(card.get("body_json") or "{}")
    except json.JSONDecodeError:
        body = {}
    before = dict(card)
    before["body"] = body
    title = patch.get("title", card.get("title"))
    asset_status = patch.get("asset_status", card.get("asset_status"))
    brief_keys = (
        "hook", "caption_draft", "shot_list", "shot_list_note", "pillar", "platform",
        "scheduled_date", "goal", "theme", "content_type", "idea", "concept",
        "scene", "slide", "text_overlays", "cta", "hashtags", "caption",
        "production_notes", "existing_footage", "footage_needed", "inspiration",
        "assignee", "workflow_status", "format",
        # Phase 2.6 team brief
        "post_type", "content_breakdown", "caption_direction", "recommended_shot_list",
        "inspiration_examples", "story_breakdown", "story_cta", "evergreen",
        "cta_type", "visual_suggestions",
    )
    for k in brief_keys:
        if k in patch:
            body[k] = patch[k]
    # Alias caption → caption_draft for generators that read caption_draft
    if "caption" in patch and "caption_draft" not in patch:
        body["caption_draft"] = patch["caption"]
    if "workflow_status" in patch:
        # Keep revision role as HUMAN_EDIT; workflow_status is the team-facing state
        pass
    if "body" in patch and isinstance(patch["body"], dict):
        body.update(patch["body"])
    # Phase 2.6: inherit brand default assignee when blank (human override wins when set)
    if not str(body.get("assignee") or "").strip():
        try:
            prow = conn.execute(
                "SELECT brand_id FROM content_plans WHERE id=?",
                (card["plan_id"],),
            ).fetchone()
            if prow:
                brow = conn.execute(
                    "SELECT default_assignee FROM brands WHERE id=?",
                    (prow["brand_id"] if hasattr(prow, "keys") else prow[0],),
                ).fetchone()
                if brow:
                    da = (brow["default_assignee"] if hasattr(brow, "keys") else brow[0]) or ""
                    if da:
                        body["assignee"] = da
        except Exception:
            pass
    conn.execute(
        """
        UPDATE content_cards
        SET title=?, body_json=?, asset_status=?, status='HUMAN_EDIT', updated_at=?
        WHERE id=?
        """,
        (title, json.dumps(body), asset_status, ts, card_id),
    )
    after = {
        "id": card_id,
        "plan_id": card["plan_id"],
        "card_type": card["card_type"],
        "sequence": card["sequence"],
        "title": title,
        "body": body,
        "asset_status": asset_status,
        "status": "HUMAN_EDIT",
    }
    lane = card["data_lane"] if "data_lane" in card.keys() else "operational"
    conn.execute(
        """
        INSERT INTO card_revisions (card_id, role, full_json, diff_json, actor, created_at, data_lane)
        VALUES (?, 'HUMAN_EDIT', ?, ?, ?, ?, ?)
        """,
        (
            card_id,
            json.dumps(after),
            json.dumps({"before": {"title": before.get("title"), "body": before.get("body")}, "patch": patch}),
            subject,
            ts,
            lane,
        ),
    )
    ai = conn.execute(
        "SELECT COUNT(*) FROM card_revisions WHERE card_id=? AND role='AI_PROPOSAL'",
        (card_id,),
    ).fetchone()[0]
    # Phase 2.6: editing an approved/working plan → CHANGES PENDING REVIEW (preserve last approved revision)
    plan_id = int(card["plan_id"])
    plan_row = conn.execute("SELECT * FROM content_plans WHERE id=?", (plan_id,)).fetchone()
    review_ui = None
    if plan_row:
        plan = dict(plan_row)
        st = str(plan.get("status") or "")
        rs = str(plan.get("review_state") or "")
        if st in ("Human_Approved", "HUMAN_APPROVED", "Approved") or rs in ("APPROVED", "CHANGES_PENDING_REVIEW"):
            # Remember last HUMAN_APPROVED revision id if not set
            if not plan.get("approved_revision_id"):
                last_appr = conn.execute(
                    "SELECT id FROM plan_revisions WHERE plan_id=? AND role='HUMAN_APPROVED' ORDER BY id DESC LIMIT 1",
                    (plan_id,),
                ).fetchone()
                if last_appr:
                    conn.execute(
                        "UPDATE content_plans SET approved_revision_id=? WHERE id=?",
                        (int(last_appr[0]), plan_id),
                    )
            conn.execute(
                "UPDATE content_plans SET review_state='CHANGES_PENDING_REVIEW', updated_at=? WHERE id=?",
                (ts, plan_id),
            )
            review_ui = "CHANGES PENDING REVIEW"
        elif st in ("Working_Draft", "AI_Generated", "Draft") or rs == "WORKING":
            # Working drafts stay WORKING; still save edit revision (already done)
            conn.execute(
                "UPDATE content_plans SET review_state=COALESCE(NULLIF(review_state,''),'WORKING'), updated_at=? WHERE id=?",
                (ts, plan_id),
            )
            review_ui = "WORKING"
    conn.commit()
    after["ai_proposal_retained"] = ai > 0
    after["plan_review_state"] = review_ui
    after["plan_review_label"] = review_ui
    return after


def approve_plan(conn, plan_id: int, subject: str) -> dict:
    """Approve plan or approve pending changes. UI label: APPROVED.

    Preserves prior HUMAN_APPROVED revisions; new approval creates a fresh one.
    Clears CHANGES_PENDING_REVIEW → APPROVED.
    """
    row = conn.execute("SELECT * FROM content_plans WHERE id=?", (plan_id,)).fetchone()
    if not row:
        raise KeyError("plan not found")
    ts = now_iso()
    conn.execute(
        "UPDATE content_plans SET status='Human_Approved', review_state='APPROVED', updated_at=? WHERE id=?",
        (ts, plan_id),
    )
    snap = get_plan_working_draft(conn, plan_id)
    snap["plan"]["status"] = "Human_Approved"
    snap["plan"]["review_state"] = "APPROVED"
    lane = row["data_lane"] if "data_lane" in row.keys() else "operational"
    cur = conn.execute(
        """
        INSERT INTO plan_revisions (plan_id, role, full_json, diff_json, actor, created_at, data_lane)
        VALUES (?, 'HUMAN_APPROVED', ?, ?, ?, ?, ?)
        """,
        (plan_id, json.dumps(snap), json.dumps({"status": "Human_Approved", "review_state": "APPROVED"}), subject, ts, lane),
    )
    rev_id = int(cur.lastrowid)
    conn.execute(
        "UPDATE content_plans SET approved_revision_id=? WHERE id=?",
        (rev_id, plan_id),
    )
    conn.commit()
    snap["approved_revision_id"] = rev_id
    snap["review_state"] = "APPROVED"
    snap["review_label"] = "APPROVED"
    return snap


def request_plan_revision(conn, plan_id: int, subject: str, note: str = "") -> dict:
    """Matt/Amanda request revision while changes are pending — stays CHANGES PENDING REVIEW with note."""
    row = conn.execute("SELECT * FROM content_plans WHERE id=?", (plan_id,)).fetchone()
    if not row:
        raise KeyError("plan not found")
    ts = now_iso()
    plan = dict(row)
    lane = plan.get("data_lane") or "operational"
    conn.execute(
        "UPDATE content_plans SET review_state='CHANGES_PENDING_REVIEW', updated_at=? WHERE id=?",
        (ts, plan_id),
    )
    snap = get_plan_working_draft(conn, plan_id)
    conn.execute(
        """
        INSERT INTO plan_revisions (plan_id, role, full_json, diff_json, actor, created_at, data_lane)
        VALUES (?, 'REQUEST_REVISION', ?, ?, ?, ?, ?)
        """,
        (
            plan_id,
            json.dumps(snap),
            json.dumps({"note": note or "", "review_state": "CHANGES_PENDING_REVIEW"}),
            subject,
            ts,
            lane,
        ),
    )
    conn.commit()
    snap["review_state"] = "CHANGES_PENDING_REVIEW"
    snap["review_label"] = "CHANGES PENDING REVIEW"
    snap["request_note"] = note or ""
    return snap


def get_plan_changes_view(conn, plan_id: int) -> dict:
    """Compare current working draft vs last approved revision for VIEW CHANGES."""
    current = get_plan_working_draft(conn, plan_id)
    plan = current.get("plan") or {}
    # Prefer live DB review_state (authoritative)
    live = conn.execute(
        "SELECT status, review_state, approved_revision_id FROM content_plans WHERE id=?",
        (plan_id,),
    ).fetchone()
    if live:
        plan["status"] = live["status"] if hasattr(live, "keys") else live[0]
        plan["review_state"] = live["review_state"] if hasattr(live, "keys") else live[1]
        plan["approved_revision_id"] = live["approved_revision_id"] if hasattr(live, "keys") else live[2]
        if current.get("plan"):
            current["plan"].update({
                "status": plan["status"],
                "review_state": plan["review_state"],
                "approved_revision_id": plan["approved_revision_id"],
            })
    approved_id = plan.get("approved_revision_id")
    approved = None
    if approved_id:
        row = conn.execute(
            "SELECT id, role, full_json, actor, created_at FROM plan_revisions WHERE id=?",
            (int(approved_id),),
        ).fetchone()
        if row:
            try:
                approved = json.loads(row["full_json"] or "{}")
            except json.JSONDecodeError:
                approved = None
    if approved is None:
        row = conn.execute(
            "SELECT id, role, full_json, actor, created_at FROM plan_revisions "
            "WHERE plan_id=? AND role='HUMAN_APPROVED' ORDER BY id DESC LIMIT 1",
            (plan_id,),
        ).fetchone()
        if row:
            try:
                approved = json.loads(row["full_json"] or "{}")
            except json.JSONDecodeError:
                approved = None
    # Pending card edits since last approval
    pending_edits = [
        dict(r)
        for r in conn.execute(
            """
            SELECT cr.id, cr.card_id, cr.actor, cr.created_at, cr.diff_json, cc.title, cc.card_type, cc.sequence
            FROM card_revisions cr
            JOIN content_cards cc ON cc.id = cr.card_id
            WHERE cc.plan_id=? AND cr.role='HUMAN_EDIT'
            ORDER BY cr.id DESC
            LIMIT 40
            """,
            (plan_id,),
        ).fetchall()
    ]
    return {
        "plan_id": plan_id,
        "review_state": plan.get("review_state") or "",
        "review_label": (
            "CHANGES PENDING REVIEW"
            if (plan.get("review_state") or "") == "CHANGES_PENDING_REVIEW"
            else ("APPROVED" if (plan.get("status") or "") in ("Human_Approved", "HUMAN_APPROVED") else "WORKING")
        ),
        "current": current,
        "approved_snapshot": approved,
        "pending_edits": pending_edits,
    }
