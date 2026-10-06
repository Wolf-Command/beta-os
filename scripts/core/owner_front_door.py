#!/usr/bin/env python3
"""Owner front door read model for /wolf.

Pulse, Ask Wolf, Needs You, and Running come from canonical control-plane
state. Ask Wolf answers first from that state. It does not call a model.
"""
from __future__ import annotations

from typing import Any

from core import wolf_policy_gate as gate

SCHEMA = "wolf.owner-front-door.v1"

GGV_TESTS = (
    {
        "id": "september-mandiri-upload",
        "what": "September Mandiri statement upload",
        "href": "/ggv/finance/banking",
        "status": "NOT RUN ON THIS RUNTIME",
    },
    {
        "id": "statement-preservation",
        "what": "Original statement preservation",
        "href": "/ggv/finance/banking",
        "status": "NOT RUN ON THIS RUNTIME",
    },
    {
        "id": "parse-without-silent-loss",
        "what": "Transaction parsing without silent loss",
        "href": "/ggv/finance/transactions",
        "status": "NOT RUN ON THIS RUNTIME",
    },
    {
        "id": "one-real-reconciliation",
        "what": "One real reconciliation",
        "href": "/ggv/finance/reconciliation",
        "status": "NOT RUN ON THIS RUNTIME",
    },
    {
        "id": "historical-ggv-lookup",
        "what": "Historical GGV lookup",
        "href": "/ggv/finance/history",
        "status": "NOT RUN ON THIS RUNTIME",
    },
)


def ggv_finance() -> dict[str, Any]:
    return {
        "human_commissioned": False,
        "staff_ready": False,
        "truth": "NOT HUMAN COMMISSIONED",
        "why": "Remaining real tests have not passed on this runtime. An automated check is not commissioning.",
        "remaining_tests": list(GGV_TESTS),
        "href": "/ggv/finance",
    }


def arya_uma() -> dict[str, Any]:
    return {
        "role_model": "PERSON → ROLE/POSITION → ASSIGNMENT → SCOPE → PERMISSION",
        "hardcoded_permission": False,
        "tonight_close": "UNKNOWN",
        "started": "UNKNOWN",
        "submitted": "UNKNOWN",
        "when": "UNKNOWN",
        "exceptions": "UNKNOWN",
        "audited_actor": "UNKNOWN",
        "evidence": (
            "No live venue close catalog is on this runtime. "
            "Wolf did not open or modify the Uma Blu close."
        ),
        "interfered": False,
    }


def _item_view(item: dict[str, Any]) -> dict[str, Any]:
    eta = item.get("eta")
    return {
        "id": item.get("id"),
        "what": item.get("what"),
        "status": item.get("status"),
        "current_step": item.get("current_step"),
        "worker": item.get("worker"),
        "worker_reason": item.get("worker_reason"),
        "started": item.get("started"),
        "last_change": item.get("last_real_change") or item.get("last_change"),
        "next_step": item.get("next_step"),
        "blocker": item.get("blocker"),
        "owner_needed": bool(item.get("owner_needed")),
        "eta": eta if eta else None,
    }


def pulse(state: dict[str, Any]) -> dict[str, Any]:
    finance = ggv_finance()
    evidence = gate.runtime_evidence()
    disk = evidence["disk"]
    running = [item for item in state.get("items") or [] if str(item.get("status") or "").upper() == "RUNNING"]
    failed = [
        item
        for item in state.get("items") or []
        if str(item.get("status") or "").upper() in {"FAILED", "STALE", "WAITING_CAPACITY"}
    ]
    tiles = [
        {
            "id": "exceptions",
            "what": "Critical exceptions",
            "value": "GGV Finance is not commissioned" if not finance["human_commissioned"] else "None recorded",
            "why": "Remaining GGV tests have not passed. This page does not commission the desk.",
            "state": "NEEDS REVIEW",
        },
        {
            "id": "security",
            "what": "Security",
            "value": "Read gate is server-side in this build",
            "why": "Owner cockpit, God Mode, AMG state, and out-of-scope person reads fail closed before the payload.",
            "state": "NEEDS REVIEW",
        },
        {
            "id": "finance",
            "what": "Finance",
            "value": finance["truth"],
            "why": finance["why"],
            "state": "BLOCKED",
            "href": finance["href"],
        },
        {
            "id": "capacity",
            "what": "Capacity",
            "value": f"{disk['free_gb']} GB free",
            "why": f"Floor stays {disk['floor_gb']} GB. Included Cursor dispatch is waiting, not spending.",
            "state": "BLOCKED" if disk["below_floor"] else "LIVE",
        },
        {
            "id": "failures",
            "what": "Operational failures",
            "value": f"{len(failed)} work item(s) not running",
            "why": "Stale, failed, and waiting-capacity rows are off RUNNING. No model is polled.",
            "state": "NEEDS REVIEW" if failed else "LIVE",
        },
        {
            "id": "changes",
            "what": "Meaningful changes",
            "value": f"{len(running)} running" if running else "Directive is in canonical work state",
            "why": "The overnight directive is a work item under state/wolf-control, not a markdown note.",
            "state": "LIVE" if running else "NEEDS REVIEW",
        },
    ]
    priorities = [
        "Keep GGV Finance uncommissioned until the five real tests pass.",
        "Keep metered workers out of the control loop.",
        "Use /wolf for Pulse, Ask Wolf, Running, and Needs You.",
    ]
    return {"tiles": tiles, "priorities": priorities, "metric_clutter": False}


def workers(env: dict[str, str] | None = None) -> list[dict[str, Any]]:
    names = ("cursor", "claude-pro", "codex", "local-deterministic", "ollama")
    return [gate.worker_eligibility(name, env) for name in names]


def build_front_door(root=None) -> dict[str, Any]:
    state = gate.tick(root)
    disk = gate.disk_report()
    needs = gate.needs_you(state)
    running = [_item_view(item) for item in gate.running_items(state)]
    return {
        "ok": True,
        "schema": SCHEMA,
        "surface": "/wolf",
        "human_commissioned": False,
        "staff_ready": False,
        "production_mutation": False,
        "pulse": pulse(state),
        "needs_you": {
            "items": needs,
            "empty": not needs,
            "empty_message": "Nothing needs you. Routine engineering is not escalated.",
        },
        "running": {
            "items": running,
            "empty": not running,
            "empty_message": "Nothing is running. Stale work is not left in RUNNING.",
            "lease_seconds": gate.LEASE_SECONDS,
            "fields": [
                "what",
                "status",
                "current_step",
                "worker",
                "started",
                "last_change",
                "next_step",
                "blocker",
                "owner_needed",
            ],
        },
        "work": [_item_view(item) for item in state.get("items") or []],
        "ggv_finance": ggv_finance(),
        "arya_uma": arya_uma(),
        "workers": workers(),
        "disk": disk,
        "evidence": gate.runtime_evidence(),
        "ask": {"href": "/api/owner/ask", "ui_name": "Wolf"},
    }


def _hit(text: str, *needles: str) -> bool:
    low = text.lower()
    return any(needle in low for needle in needles)


def answer(
    question: str,
    root=None,
    env: dict[str, str] | None = None,
    *,
    action: str | None = None,
    work_item_id: str | None = None,
    worker: str | None = None,
) -> dict[str, Any]:
    """Answer first. Why, next, and evidence only when they help."""
    if action:
        return _action_answer(action, work_item_id or "", worker, root)
    q = (question or "").strip()
    state = gate.tick(root)
    door = build_front_door(root)
    evidence: list[Any] = []
    why = None
    nxt = None

    if not q:
        text = "Ask a question."
    elif _hit(q, "stop ") and _hit(q, "wi-"):
        text = _control_phrase(q, "stop", root)
    elif _hit(q, "reassign"):
        text = _control_phrase(q, "reassign", root)
    elif _hit(q, "fix this", "fix "):
        text = _control_phrase(q, "fix", root)
    elif _hit(q, "need me", "needs me", "needs you", "what needs"):
        items = door["needs_you"]["items"]
        text = (
            door["needs_you"]["empty_message"]
            if not items
            else "Needs you: " + "; ".join(str(item["what"]) for item in items)
        )
        why = "Only paid spend, irreversible action, production mutation, governance, or a material decision is escalated."
    elif _hit(q, "running", "what is running"):
        items = door["running"]["items"]
        text = (
            door["running"]["empty_message"]
            if not items
            else "; ".join(f"{item['what']} is {item['status']}" for item in items)
        )
        why = "RUNNING expires by lease. No model is polled."
    elif _hit(q, "arya", "uma blu", "uma"):
        uma = door["arya_uma"]
        text = (
            f"Uma Blu close is {uma['tonight_close']}. "
            f"Started {uma['started']}. Submitted {uma['submitted']}."
        )
        why = uma["evidence"]
        evidence.append({"interfered": False, "hardcoded_permission": False})
    elif _hit(q, "overnight", "what happened"):
        lines = [f"{item.get('what')}: {item.get('status')}" for item in state.get("items") or []]
        text = " ".join(lines) if lines else "No overnight work items are recorded."
        evidence.append({"kind": "work-state", "path": "state/wolf-control/work-state.json"})
    elif _hit(q, "ggv", "finance"):
        finance = door["ggv_finance"]
        text = f"GGV Finance is {finance['truth']}."
        why = finance["why"]
        nxt = "The remaining tests are on the GGV finance desk."
        evidence = [{"id": row["id"], "href": row["href"], "status": row["status"]} for row in finance["remaining_tests"]]
    elif _hit(q, "remain", "left to test", "what remains"):
        rows = door["ggv_finance"]["remaining_tests"]
        text = "Still to test: " + "; ".join(row["what"] for row in rows) + "."
        evidence = [{"href": row["href"], "status": row["status"]} for row in rows]
    elif _hit(q, "constrained", "which ai", "workers"):
        blocked = [row for row in workers(env) if not row.get("eligible")]
        text = "Constrained: " + ", ".join(f"{row['worker']} ({row['reason']})" for row in blocked) + "."
        why = "Included Cursor is not invoked on demand. Subscription workers fail closed when an API key is set."
    elif _hit(q, "disk"):
        disk = door["disk"]
        text = f"Free disk is {disk['free_gb']} GB. The floor stays {disk['floor_gb']} GB."
        why = "The floor was not lowered. Nothing was deleted."
    elif _hit(q, "why did wolf", "why wolf", "choose that worker", "chose", "why wolf chose"):
        choices = [
            f"{item.get('id')}: {item.get('worker') or 'none'} because {item.get('worker_reason') or 'no worker was eligible'}"
            for item in state.get("items") or []
        ]
        text = " ".join(choices) if choices else "Wolf has not chosen a worker."
        why = "The local plane holds state. Cursor, Claude Pro, and Codex are not called from here."
    elif _hit(q, "evidence", "show evidence"):
        text = "Evidence is the control-plane record and the checks this runtime could actually make."
        evidence.append(door["evidence"])
    else:
        text = "Wolf does not have a canonical answer to that. Nothing was invented."
        why = "UNKNOWN stays UNKNOWN."

    return {
        "ok": True,
        "answer": text,
        "why": why,
        "what_next": nxt,
        "evidence": evidence,
        "ui_name": "Wolf",
        "human_commissioned": False,
        "staff_ready": False,
        "model_called": False,
        "production_mutation": False,
    }


def _action_answer(action: str, item_id: str, worker: str | None, root) -> dict[str, Any]:
    try:
        result = gate.apply_owner_action(action, item_id, worker=worker, root=root)
    except ValueError as exc:
        return {
            "ok": False,
            "answer": str(exc),
            "error": str(exc),
            "ui_name": "Wolf",
            "human_commissioned": False,
            "staff_ready": False,
            "model_called": False,
            "production_mutation": False,
        }
    item = result["item"]
    return {
        "ok": True,
        "answer": f"{action} recorded for {item_id}. Status is {item.get('status')}.",
        "why": "Control-plane state only. Reversible. No production system was changed.",
        "evidence": [{"action": action, "status": item.get("status"), "reversible": True}],
        "ui_name": "Wolf",
        "human_commissioned": False,
        "staff_ready": False,
        "model_called": False,
        "production_mutation": False,
    }


def _control_phrase(question: str, action: str, root) -> str:
    parts = question.split()
    item_id = next((part.strip(".,") for part in parts if part.upper().startswith("WI-")), "")
    worker = None
    if "cursor" in question.lower():
        worker = "cursor"
    if "local" in question.lower():
        worker = "local-deterministic"
    try:
        result = gate.apply_owner_action(action, item_id, worker=worker, root=root)
    except ValueError as exc:
        return str(exc)
    return f"{action} recorded for {item_id}. Status is {result['item'].get('status')}."
