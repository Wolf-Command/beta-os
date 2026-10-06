#!/usr/bin/env python3
"""Deterministic Wolf policy gate. Not a second orchestrator.

OpenClaw is the intended worker host when it is present and proven not to
spend a metered model on coordination. This module only:
- records canonical work state
- applies completion and failure events
- reaps stale RUNNING rows
- refuses blocked workers and API-key routes

It does not call a model to see whether a job finished.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "wolf.policy-gate.v1"
LEASE_SECONDS = 600
DISK_FLOOR_BYTES = 100 * 1024 * 1024 * 1024
BLOCKED_WORKERS = frozenset(
    {
        "grok",
        "peaches",
        "vesper",
        "haiku",
        "claude-haiku",
        "gemini",
        "anthropic-api",
        "openai-api",
        "cursor-on-demand",
    }
)
METERED_ENV = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "XAI_API_KEY",
    "GROK_API_KEY",
)
ALLOWED_STATUS = frozenset(
    {
        "RUNNING",
        "DONE",
        "FAILED",
        "BLOCKED",
        "STALLED",
        "WAITING_CAPACITY",
        "BUILT_NOT_DEPLOYED",
    }
)


def beta_root() -> Path:
    override = (os.environ.get("WOLF_BETA_ROOT") or "").strip()
    if override:
        return Path(override)
    mac = Path("/Users/wolfterminal/beta-os")
    if mac.is_dir():
        return mac
    return Path(__file__).resolve().parents[2]


def state_dir(root: Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    override = (os.environ.get("WOLF_POLICY_STATE") or "").strip()
    if override:
        return Path(override)
    return beta_root() / "state" / "wolf-control"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    text = str(ts).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _read(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        return fallback
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback
    return data if isinstance(data, dict) else fallback


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_event(directory: Path, event: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, separators=(",", ":"))
    with (directory / "events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _blocked_name(name: str) -> bool:
    worker = (name or "").strip().lower()
    return bool(
        worker
        and (
            worker in BLOCKED_WORKERS
            or "grok" in worker
            or "peaches" in worker
            or "vesper" in worker
        )
    )


def worker_eligibility(name: str | None, env: dict[str, str] | None = None) -> dict[str, Any]:
    """Subscription route or local tool. API keys fail closed. No invocation happens here."""
    env = env if env is not None else dict(os.environ)
    worker = (name or "").strip().lower()
    base = {
        "worker": worker or None,
        "eligible": False,
        "metered": False,
        "invoked": False,
        "spend": "blocked",
    }
    if not worker:
        return {**base, "reason": "no_worker"}
    if _blocked_name(worker):
        return {**base, "reason": "blocked_worker"}
    if worker in {"local", "deterministic", "local-deterministic"}:
        return {**base, "eligible": True, "reason": "local_deterministic", "route": "local"}
    if worker in {"cursor", "cursor-ultra"}:
        if (env.get("CURSOR_ON_DEMAND") or "").strip() in {"1", "true", "TRUE", "yes"}:
            return {**base, "reason": "cursor_on_demand_blocked"}
        return {
            **base,
            "eligible": True,
            "reason": "cursor_ultra_included",
            "route": "cursor_ultra",
        }
    if worker in {"claude", "claude-pro", "claude-code"}:
        if (env.get("ANTHROPIC_API_KEY") or "").strip():
            return {**base, "reason": "anthropic_api_key_present_fail_closed", "metered": True}
        return {**base, "reason": "claude_pro_subscription_not_proven", "capacity": "WAITING_CAPACITY"}
    if worker in {"codex", "openai-codex", "chatgpt-business"}:
        if (env.get("OPENAI_API_KEY") or "").strip():
            return {**base, "reason": "openai_api_key_present_fail_closed", "metered": True}
        return {**base, "reason": "codex_subscription_not_proven", "capacity": "WAITING_CAPACITY"}
    if worker == "ollama":
        return {**base, "reason": "ollama_not_a_generic_fallback"}
    return {**base, "reason": "unknown_worker"}


def _process_lines() -> list[str]:
    try:
        out = subprocess.check_output(["ps", "aux"], text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return []
    return out.splitlines()


def inspect_openclaw() -> dict[str, Any]:
    """Live host check. Repo comments are not proof that a process is running."""
    home = Path.home() / ".openclaw"
    mac = Path("/Users/wolfterminal/.openclaw")
    homes = [p for p in (home, mac) if p.is_dir()]
    lines = _process_lines()
    hits = []
    for line in lines:
        cols = line.split(None, 10)
        if len(cols) < 11:
            continue
        cmd = cols[10]
        first = (cmd.split() or [""])[0]
        base = first.rsplit("/", 1)[-1].lower()
        low = cmd.lower()
        if base in {"openclaw", "openclaw-gateway"} or low.startswith("openclaw ") or "openclaw gateway" in low:
            hits.append(line[:240])
    metered_present = [key for key in METERED_ENV if (os.environ.get(key) or "").strip()]
    missing = []
    if not hits:
        missing.append("openclaw_process")
    if not homes:
        missing.append("openclaw_home")
    missing.extend(
        [
            "proven_cursor_adapter",
            "proven_claude_pro_subscription_adapter",
            "proven_codex_business_subscription_adapter",
            "proven_non_metered_coordination_model",
        ]
    )
    return {
        "schema": SCHEMA,
        "checked_at": _now(),
        "running": bool(hits),
        "process_owner": None,
        "process_lines": hits[:5],
        "homes_present": [str(p) for p in homes],
        "event_bus_db": any((p / "state" / "event_bus.db").is_file() for p in homes),
        "canonical_state": "state/wolf-control/work-state.json",
        "worker_adapters_in_repo": [],
        "cursor_independent": False,
        "claude_pro_subscription": False,
        "codex_business_subscription": False,
        "completion_events_without_llm": True,
        "restart_safe_host": False,
        "depends_on_grok": False,
        "metered_orchestration": False,
        "paid_fallback": False,
        "suitable_as_overnight_brain": False,
        "reason": (
            "OpenClaw is the intended host. This runtime has no OpenClaw process and no "
            "proven subscription adapters. Coordination stays in this deterministic gate. "
            "A model is not called to move work, reap a lease, or record evidence."
        ),
        "haiku_claim": "UNVERIFIED",
        "repo_haiku_path": {
            "path": "scripts/llm_orchestrator.py",
            "model": "claude-3-5-haiku-latest",
            "route": "anthropic_messages_api",
            "used_for_coordination": False,
            "overnight_use": "blocked",
            "note": (
                "Content caption role only. This is not proof of the OpenClaw control model. "
                "The claim that OpenClaw runs on Claude Haiku is UNVERIFIED on this runtime."
            ),
        },
        "peaches_in_execution_loop": False,
        "grok_in_execution_loop": False,
        "vesper_in_execution_loop": False,
        "metered_env_present": metered_present,
        "missing": missing,
        "integration": (
            "OpenClaw may submit a completion event to wolf_policy_gate.apply_event. "
            "This gate does not start a parallel scheduler."
        ),
    }


def _blank() -> dict[str, Any]:
    now = _now()
    return {
        "schema": SCHEMA,
        "updated_at": now,
        "orchestrator": "openclaw_when_proven_else_policy_gate",
        "parallel_orchestrator": False,
        "human_commissioned": False,
        "staff_ready": False,
        "production_mutation": False,
        "openclaw": inspect_openclaw(),
        "items": [
            {
                "id": "WOLF-OWNER-OVERNIGHT-20261006",
                "what": "Wolf Owner System at /wolf: Pulse, Ask Wolf, Needs You, Running",
                "status": "BUILT_NOT_DEPLOYED",
                "current_step": "Policy gate and Owner front door are in the beta-os tree",
                "worker": "cursor",
                "worker_reason": "cursor_ultra_included",
                "started": now,
                "last_change": now,
                "next_step": "Deploy on Beta only after the server-side read gate is on the live route",
                "blocker": None,
                "owner_needed": False,
                "eta": None,
                "human_commissioned": False,
            },
            {
                "id": "OPENCLAW-HOST-20261006",
                "what": "Use OpenClaw as the worker host once it is present and not a metered brain",
                "status": "BLOCKED",
                "current_step": "Host inspection",
                "worker": None,
                "worker_reason": "openclaw_not_running_here",
                "started": now,
                "last_change": now,
                "next_step": "OpenClaw submits events to this gate. Do not add a second scheduler.",
                "blocker": "OpenClaw process and home are absent on this runtime",
                "owner_needed": False,
                "eta": None,
                "human_commissioned": False,
            },
        ],
    }


def load(root: Path | None = None) -> dict[str, Any]:
    directory = state_dir(root)
    path = directory / "work-state.json"
    data = _read(path, {})
    if not data.get("items"):
        data = _blank()
        _write(path, data)
    return data


def save(data: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    data["updated_at"] = _now()
    data["schema"] = SCHEMA
    data["human_commissioned"] = False
    data["parallel_orchestrator"] = False
    _write(state_dir(root) / "work-state.json", data)
    return data


def tick(root: Path | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    """Reap stale RUNNING rows. No model call."""
    data = load(root)
    data["openclaw"] = inspect_openclaw()
    clock = now or datetime.now(timezone.utc)
    changed = False
    for item in data.get("items") or []:
        if str(item.get("status") or "").upper() != "RUNNING":
            continue
        worker = str(item.get("worker") or "")
        eligibility = worker_eligibility(worker) if worker else {"eligible": True}
        if worker and not eligibility.get("eligible"):
            item["status"] = "FAILED"
            item["blocker"] = eligibility.get("reason")
            item["last_change"] = _now()
            item["owner_needed"] = False
            changed = True
            _append_event(
                state_dir(root),
                {
                    "at": item["last_change"],
                    "item_id": item.get("id"),
                    "type": "worker_rejected",
                    "reason": eligibility.get("reason"),
                },
            )
            continue
        last = _parse(item.get("last_change")) or _parse(item.get("started"))
        if last is None or (clock - last).total_seconds() > LEASE_SECONDS:
            item["status"] = "STALLED"
            item["blocker"] = "lease_expired"
            item["last_change"] = _now()
            item["owner_needed"] = False
            changed = True
            _append_event(
                state_dir(root),
                {
                    "at": item["last_change"],
                    "item_id": item.get("id"),
                    "type": "stale_running",
                    "reason": "lease_expired",
                },
            )
    save(data, root)
    return data


def apply_event(event: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    """OpenClaw or a local tool reports completion. The model is not asked."""
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    source = str(event.get("source") or "").strip().lower()
    if _blocked_name(source):
        raise ValueError("blocked_source")
    worker_name = str(event.get("worker") or "").strip().lower()
    if worker_name:
        eligibility = worker_eligibility(worker_name)
        if not eligibility.get("eligible"):
            raise ValueError(str(eligibility.get("reason") or "worker_rejected"))
    item_id = str(event.get("item_id") or "").strip()
    if not item_id:
        raise ValueError("item_id required")
    status = str(event.get("status") or "").upper()
    if status not in ALLOWED_STATUS:
        raise ValueError("status not allowed")
    data = tick(root)
    found = None
    for item in data.get("items") or []:
        if item.get("id") == item_id:
            found = item
            break
    if found is None:
        raise ValueError("unknown_item")
    if status == "RUNNING" and worker_name:
        found["worker_reason"] = worker_eligibility(worker_name).get("reason")
    if worker_name:
        found["worker"] = event.get("worker")
    found["status"] = status
    if event.get("current_step"):
        found["current_step"] = event["current_step"]
    if event.get("next_step"):
        found["next_step"] = event["next_step"]
    if "blocker" in event:
        found["blocker"] = event.get("blocker")
    found["owner_needed"] = bool(event.get("owner_needed"))
    found["last_change"] = _now()
    found["human_commissioned"] = False
    record = {
        "at": found["last_change"],
        "item_id": item_id,
        "type": "completion_event",
        "status": status,
        "worker": event.get("worker"),
        "source": source or "policy_gate",
    }
    _append_event(state_dir(root), record)
    save(data, root)
    return {"ok": True, "item": found, "event": record, "human_commissioned": False}


def runtime_evidence() -> dict[str, Any]:
    """Facts this process could check. Not a model summary."""
    return {
        "openclaw": inspect_openclaw(),
        "disk": disk_report(),
        "metered_call": False,
        "parallel_orchestrator": False,
    }


def apply_owner_action(
    action: str,
    item_id: str,
    *,
    worker: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Reversible control-plane change. Does not call a worker."""
    act = (action or "").strip().lower()
    if act == "stop":
        status = "BLOCKED"
        chosen = "local"
        blocker = "stopped_by_owner"
        step = "Stopped from Ask Wolf"
    elif act == "reassign":
        status = "WAITING_CAPACITY"
        chosen = worker or "local"
        blocker = None
        step = f"Reassigned to {chosen}"
    elif act == "fix":
        status = "WAITING_CAPACITY"
        chosen = "cursor"
        blocker = None
        step = "Fix recorded for Cursor. Not done."
    else:
        raise ValueError("action not allowed")
    if not item_id:
        raise ValueError("item_id required")
    return apply_event(
        {
            "item_id": item_id,
            "status": status,
            "worker": chosen,
            "current_step": step,
            "blocker": blocker,
            "owner_needed": False,
            "source": "owner",
        },
        root,
    )


def disk_report() -> dict[str, Any]:
    root = beta_root()
    usage = shutil.disk_usage(root if root.exists() else Path("/"))
    free = int(usage.free)
    return {
        "path": str(root if root.exists() else Path("/")),
        "free_bytes": free,
        "free_gb": round(free / (1024 ** 3), 1),
        "floor_gb": 100,
        "floor_lowered": False,
        "below_floor": free < DISK_FLOOR_BYTES,
        "action": "none" if free >= DISK_FLOOR_BYTES else "clean_only_proven_scratch",
    }


def running_items(data: dict[str, Any] | None = None, root: Path | None = None) -> list[dict[str, Any]]:
    state = data if data is not None else tick(root)
    return [item for item in state.get("items") or [] if str(item.get("status")).upper() == "RUNNING"]


def needs_you(data: dict[str, Any] | None = None, root: Path | None = None) -> list[dict[str, Any]]:
    state = data if data is not None else tick(root)
    rows = []
    for item in state.get("items") or []:
        if item.get("owner_needed") is True:
            rows.append(
                {
                    "id": item.get("id"),
                    "what": item.get("what"),
                    "why": item.get("blocker") or item.get("current_step"),
                    "kind": "owner_decision",
                }
            )
    disk = disk_report()
    if disk["below_floor"]:
        rows.append(
            {
                "id": "DISK-FLOOR",
                "what": "Disk free space is under the 100 GB floor",
                "why": "Clean only proven disposable scratch. Do not delete evidence or databases.",
                "kind": "capacity",
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    cmd = args[0] if args else "tick"
    if cmd == "inspect":
        print(json.dumps(inspect_openclaw(), indent=2))
        return 0
    if cmd == "tick":
        print(json.dumps(tick(), indent=2))
        return 0
    if cmd == "event":
        payload = json.loads(sys.stdin.read() or "{}")
        print(json.dumps(apply_event(payload), indent=2))
        return 0
    print(json.dumps({"ok": False, "error": "unknown_command"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
