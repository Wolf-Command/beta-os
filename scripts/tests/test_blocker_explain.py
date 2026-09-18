#!/usr/bin/env python3
"""Blocker explanation + Needs You classification (Beta). No production writes."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import knowledge_resolution as kr  # noqa: E402
from core import progress_read_model as prm  # noqa: E402
from core.blocker_explain import (  # noqa: E402
    WHY_CLOSER,
    WHY_OPENING_FLOAT,
    WHY_POLICY_REQUIRED,
    explain_operating_blocker,
)

PASS = 0
FAIL = 0

FORBIDDEN_STAGE = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)

ALLOWED_KEYS = {
    "why",
    "classification",
    "decision",
    "provenance",
    "status",
    "honesty",
}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def test_templates() -> None:
    policy = explain_operating_blocker("policy_required", {})
    check(
        "policy_required classification NEEDS_POLICY",
        policy.get("classification") == "NEEDS_POLICY",
        str(policy.get("classification")),
    )
    check(
        "policy_required fixed why",
        policy.get("why") == WHY_POLICY_REQUIRED,
        str(policy.get("why")),
    )
    check("policy why has no invented limit", "25" not in (policy.get("why") or ""))

    floated = explain_operating_blocker(
        "opening_balance_required",
        {"opening_float_status": "NOT_FOUND", "label": "Petty tin (float NOT FOUND)"},
    )
    check(
        "float NOT_FOUND is NEEDS_POLICY",
        floated.get("classification") == "NEEDS_POLICY",
        str(floated.get("classification")),
    )
    check(
        "float NOT_FOUND is not NEEDS_MATT",
        floated.get("classification") != "NEEDS_MATT",
    )
    check(
        "float NOT_FOUND fixed why",
        floated.get("why") == WHY_OPENING_FLOAT,
        str(floated.get("why")),
    )

    closer = explain_operating_blocker("WAITING_FOR_CLOSER", {})
    check(
        "closer is NEEDS_STAFF",
        closer.get("classification") == "NEEDS_STAFF",
        str(closer.get("classification")),
    )
    check("closer is not NEEDS_MATT", closer.get("classification") != "NEEDS_MATT")
    check("closer fixed why", closer.get("why") == WHY_CLOSER, str(closer.get("why")))

    for row in (policy, floated, closer):
        honesty = row.get("honesty") or {}
        check(
            "honesty refuses invented authority/float/closer",
            honesty.get("invented_authority") is False
            and honesty.get("invented_float") is False
            and honesty.get("invented_closer") is False,
            str(honesty),
        )
        check("explain keys stay on the allowlist", set(row) <= ALLOWED_KEYS, str(set(row)))


def test_resolution_without_cot() -> None:
    missed = explain_operating_blocker(
        "policy_required",
        {
            "question": "What is Wolf's ClickUp policy?",
            "scope": {"entity": "BZG", "brand": "Uma Blu"},
        },
    )
    check(
        "resolve_question NOT_FOUND surfaced",
        missed.get("status") == kr.STATUS_NOT_FOUND,
        str(missed.get("status")),
    )
    blob = json.dumps(missed)
    check("NOT_FOUND omits attempts", "attempts" not in missed and "attempts" not in blob)
    check(
        "NOT_FOUND omits chain-of-thought",
        "chain-of-thought" not in blob.lower() and "chain of thought" not in blob.lower(),
    )
    check(
        "NOT_FOUND keeps policy classification",
        missed.get("classification") == "NEEDS_POLICY"
        and missed.get("why") == WHY_POLICY_REQUIRED,
    )

    original = kr.resolve_question

    def _conflicted(question, scope, *, actor_context=None):
        return {
            "status": "CONFLICTED",
            "answer": None,
            "provenance": [
                {
                    "decision_id": "DEC-TEST-CONFLICT",
                    "authority": "OWNER_DECISION",
                }
            ],
            "attempts": [
                {
                    "step": "MAP",
                    "detail": "chain-of-thought prompt leaked",
                }
            ],
            "conflict": {"sides": ["do not copy this rationale"]},
        }

    kr.resolve_question = _conflicted
    try:
        hit = explain_operating_blocker(
            "policy_required",
            {
                "question": "What is Wolf's ClickUp policy?",
                "resolve": True,
                "scope": {"entity": "BZG", "brand": "Uma Blu"},
            },
        )
    finally:
        kr.resolve_question = original

    check(
        "resolve_question CONFLICTED surfaced",
        hit.get("status") == "CONFLICTED",
        str(hit.get("status")),
    )
    dumped = json.dumps(hit)
    check("CONFLICTED omits attempts", "attempts" not in hit)
    check(
        "CONFLICTED omits prompts and CoT",
        "chain-of-thought" not in dumped.lower()
        and "prompt leaked" not in dumped
        and "do not copy" not in dumped,
        dumped[:300],
    )
    check(
        "CONFLICTED explain stays allowlisted",
        set(hit) <= ALLOWED_KEYS,
        str(set(hit)),
    )
    check(
        "decision id present without becoming the why",
        (hit.get("decision") or {}).get("id") == "DEC-TEST-CONFLICT"
        and hit.get("why") == WHY_POLICY_REQUIRED,
    )


def test_owner_buckets() -> None:
    issues = [
        {
            "kind": "policy_required",
            "label": "Example — Dairy order",
            "example": True,
            "why": "No approved monetary authority limit exists for this action.",
        },
        {
            "kind": "policy_required",
            "label": "Live supplier · milk",
            "example": False,
        },
        {
            "kind": "closer_required",
            "label": "CLOSER REQUIRED",
            "example": False,
        },
        {
            "kind": "opening_balance_required",
            "label": "Petty tin · today · OPEN (float NOT FOUND)",
            "example": False,
            "opening_float_status": "NOT_FOUND",
        },
        {
            "kind": "missing_payment_evidence",
            "label": "Paid claim still needs evidence",
            "example": False,
        },
    ]
    buckets = prm.bucket_owner_exceptions(issues)
    check(
        "Needs You empty when only policy/staff blockers exist",
        buckets["needs_you"] == [],
        str(buckets["needs_you"]),
    )
    titles = " | ".join(
        m.get("title") or ""
        for rows in buckets.values()
        for m in rows
    )
    check("example issues excluded from Needs You buckets", "Example —" not in titles, titles)
    check(
        "opening balance not in Needs You",
        all("float" not in (m.get("title") or "").lower() for m in buckets["needs_you"]),
    )
    check(
        "closer lands in Needs staff",
        any("CLOSER" in (m.get("title") or "") for m in buckets["needs_staff"]),
        str(buckets["needs_staff"]),
    )
    check(
        "closer not in Needs You",
        all("CLOSER" not in (m.get("title") or "") for m in buckets["needs_you"]),
    )
    check(
        "float NOT_FOUND lands in Needs policy",
        any(m.get("classification") == "NEEDS_POLICY" for m in buckets["needs_policy"])
        and any("float" in (m.get("why") or "").lower() or "opening" in (m.get("why") or "").lower() for m in buckets["needs_policy"]),
        str(buckets["needs_policy"]),
    )
    check(
        "live policy issue is NEEDS_POLICY",
        any("Live supplier" in (m.get("title") or "") for m in buckets["needs_policy"]),
    )

    missions = prm._build_commissioning_missions(
        {
            "commissioning_missions": [
                {
                    "id": "CM-PROGRESS-UX",
                    "title": "Progress Dashboard UX commissioning",
                    "bucket": "NEEDS_YOU",
                    "status": "ACTIVE",
                    "who": "Matt",
                },
                {
                    "id": "CM-FLOAT",
                    "title": "OPENING BALANCE REQUIRED",
                    "bucket": "NEEDS_YOU",
                    "status": "ACTIVE",
                },
                {
                    "id": "CM-CLOSER",
                    "title": "CLOSER REQUIRED",
                    "bucket": "NEEDS_YOU",
                    "status": "WAITING",
                },
            ]
        },
        issues,
    )
    check(
        "curated NEEDS_YOU Progress stays Needs You",
        any(
            "Progress" in (m.get("title") or "") and m.get("classification") == "NEEDS_MATT"
            for m in missions["needs_you"]
        ),
        str(missions["needs_you"]),
    )
    check(
        "OPENING BALANCE REQUIRED does not auto-land in Needs You",
        all("OPENING BALANCE" not in (m.get("title") or "") for m in missions["needs_you"]),
        str([m.get("title") for m in missions["needs_you"]]),
    )
    check(
        "CLOSER REQUIRED does not auto-land in Needs You",
        all("CLOSER REQUIRED" not in (m.get("title") or "") for m in missions["needs_you"]),
    )
    pulse_lines = prm.owner_pulse_lines_from_issues(issues)
    check(
        "example issues excluded from Owner Pulse lines",
        all("Example" not in line for line in pulse_lines),
        str(pulse_lines),
    )
    pulse = prm._build_owner_pulse(
        {
            "owner_cockpit": {
                "owner_pulse": {
                    "working_now": ["Example — Dairy order must not stay"],
                    "waiting_on_people": [],
                    "policy_data_needed": ["Example — Dairy order in policy"],
                }
            }
        },
        {"status": "HEALTHY", "note": ""},
        {},
        {"needs_you": [], "waiting_on_others": []},
        [],
        issues,
    )
    blob = " ".join(
        str(x)
        for key in ("working_now", "waiting_on_people", "policy_data_needed")
        for x in (pulse.get(key) or [])
    )
    check("example label scrubbed from Owner Pulse", "Example —" not in blob, blob)


def test_surfaces_and_wip() -> None:
    html = (ROOT / "dashboards" / "progress.html").read_text(encoding="utf-8")
    issues_html = (ROOT / "dashboards" / "bzg-uma-blu-issues.html").read_text(encoding="utf-8")
    rm = (ROOT / "scripts" / "core" / "progress_read_model.py").read_text(encoding="utf-8")
    check("progress HTML has no hard-coded 25.3", "25.3" not in html)
    check("read model has no hard-coded 25.3", "25.3" not in rm)
    check("WOLF TRANSFORMATION untouched", "WOLF TRANSFORMATION" in html)
    check("SYSTEM projection binding untouched", "SYSTEM — ${esc(systemPct)}%" in html)
    for needle in ("Needs you", "Needs staff", "Needs policy", "Needs external access"):
        check(f"progress renders {needle}", needle in html)
    check("issues page keeps Example label", "Example" in issues_html)
    check(
        "issues page shows classification in human language",
        "Needs policy" in issues_html and "classification_label" in issues_html,
    )
    check(
        "issues page does not use raw kind as the row headline",
        'it.kind || "issue"' not in issues_html,
    )

    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    for path in FORBIDDEN_STAGE:
        check(f"dirty WIP not staged {path}", path not in staged, str(staged))

    touched = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (
            ROOT / "scripts" / "core" / "blocker_explain.py",
            ROOT / "scripts" / "core" / "uma_ops_console.py",
            ROOT / "scripts" / "core" / "progress_read_model.py",
        )
    )
    for banned in ("phase26_team", "wolf_intelligence", "migrate_phase2_6_team_readiness"):
        check(f"new path does not import {banned}", banned not in touched)


def main() -> int:
    test_templates()
    test_resolution_without_cot()
    test_owner_buckets()
    test_surfaces_and_wip()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
