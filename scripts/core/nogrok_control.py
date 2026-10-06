#!/usr/bin/env python3
"""Deterministic non-Grok control plane.

CANONICAL WORK ITEM → THIS PLANE → ELIGIBLE WORKER → COMPLETION EVENT →
CANONICAL STATE UPDATE → NEXT POLICY GATE → NEXT WORKER

Peaches, Grok, and Vesper are not workers in that loop. Ollama is not a
generic fallback. Cursor on-demand spend stays blocked. Claude Pro and Codex
fail closed when an API key is set. This module does not invoke them.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA = "wolf.nogrok-control.v1"
DIRECTIVE_ID = "WI-OWNER-OVERNIGHT-20261006"
LEASE_SECONDS = 90
DISK_FLOOR_BYTES = 100 * 1024 * 1024 * 1024
DISK_FLOOR_GB = 100
BLOCKED_WORKERS = frozenset({"grok", "peaches", "vesper"})
BLOCKED_WORD = re.compile(r"\b(grok|peaches|vesper)\b", re.IGNORECASE)
METERED_ENV = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "XAI_API_KEY",
    "GROK_API_KEY",
)
LOCAL_WORKER = "local-deterministic"
TERMINAL = frozenset({"DONE", "FAILED", "STOPPED", "STALE"})


def beta_root() -> Path:
    override = (os.environ.get("WOLF_BETA_ROOT") or "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2]


def state_dir(root: Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    override = (os.environ.get("WOLF_CONTROL_STATE") or "").strip()
    if override:
        return Path(override)
    return beta_root() / "state" / "wolf-control"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(moment: datetime | None = None) -> str:
    return (moment or _now()).isoformat()


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
        return json.loads(json.dumps(fallback))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(fallback))
    return data if isinstance(data, dict) else json.loads(json.dumps(fallback))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_event(directory: Path, event: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, separators=(",", ":")) + "\n")


def blocked_name(value: Any) -> str | None:
    """Return a blocked worker name if it appears. Used to reject work items."""
    if isinstance(value, str):
        match = BLOCKED_WORD.search(value)
        return match.group(1).lower() if match else None
    if isinstance(value, dict):
        for item in value.values():
            found = blocked_name(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = blocked_name(item)
            if found:
                return found
    return None


def worker_eligibility(name: str | None, env: dict[str, str] | None = None) -> dict[str, Any]:
    """Decide whether a worker may be invoked. This function does not invoke it."""
    env = env if env is not None else dict(os.environ)
    worker = (name or "").strip().lower()
    base = {
        "worker": worker or None,
        "eligible": False,
        "approved": False,
        "invoked": False,
        "metered": False,
        "spend": "blocked",
        "capacity": None,
    }
    if not worker:
        return {**base, "reason": "no_worker"}
    if worker in BLOCKED_WORKERS or blocked_name(worker):
        return {**base, "reason": "blocked_worker"}
    if worker == "ollama":
        return {**base, "reason": "ollama_not_a_generic_fallback"}
    if worker in {"local", "deterministic", LOCAL_WORKER}:
        return {
            **base,
            "worker": LOCAL_WORKER,
            "eligible": True,
            "approved": True,
            "reason": "local_deterministic",
            "route": "local",
            "capacity": "READY",
        }
    if worker in {"cursor", "cursor-ultra"}:
        return {
            **base,
            "approved": True,
            "on_demand_blocked": True,
            "capacity": "WAITING_CAPACITY",
            "reason": "cursor_included_on_demand_blocked",
            "route": "included_not_invoked",
        }
    if worker in {"claude", "claude-pro", "claude-code"}:
        if (env.get("ANTHROPIC_API_KEY") or "").strip():
            return {
                **base,
                "reason": "anthropic_api_key_present_fail_closed",
                "metered": True,
                "fail_closed": True,
            }
        if not shutil.which("claude"):
            return {
                **base,
                "approved": True,
                "capacity": "WAITING_CAPACITY",
                "reason": "claude_pro_binary_absent",
            }
        return {
            **base,
            "eligible": True,
            "approved": True,
            "reason": "claude_pro_key_unset",
            "route": "subscription_binary_not_invoked_by_this_plane",
            "capacity": "READY",
        }
    if worker in {"codex", "openai-codex", "chatgpt-business"}:
        if (env.get("OPENAI_API_KEY") or "").strip():
            return {
                **base,
                "reason": "openai_api_key_present_fail_closed",
                "metered": True,
                "fail_closed": True,
            }
        if not shutil.which("codex"):
            return {
                **base,
                "approved": True,
                "capacity": "WAITING_CAPACITY",
                "reason": "codex_binary_absent",
            }
        return {
            **base,
            "eligible": True,
            "approved": True,
            "reason": "codex_key_unset",
            "route": "subscription_binary_not_invoked_by_this_plane",
            "capacity": "READY",
        }
    return {**base, "reason": "unknown_worker"}


def disk_report() -> dict[str, Any]:
    usage = shutil.disk_usage("/")
    free = int(usage.free)
    return {
        "path": "/",
        "free_bytes": free,
        "free_gb": round(free / (1024 ** 3), 1),
        "floor_gb": DISK_FLOOR_GB,
        "floor_bytes": DISK_FLOOR_BYTES,
        "floor_lowered": False,
        "below_floor": free < DISK_FLOOR_BYTES,
        "deleted": False,
        "action": "none" if free >= DISK_FLOOR_BYTES else "stop_and_ask_owner",
    }


def runtime_evidence() -> dict[str, Any]:
    """Facts this process can check. A missing Mac process is not reported as running."""
    return {
        "checked_at": _iso(),
        "metered_env_present": [key for key in METERED_ENV if (os.environ.get(key) or "").strip()],
        "claude_binary": bool(shutil.which("claude")),
        "codex_binary": bool(shutil.which("codex")),
        "ollama_binary": bool(shutil.which("ollama")),
        "catalog_sqlite_present": Path("/Users/wolfterminal/beta-os/catalog/content_library.sqlite").is_file(),
        "mac_supervisor_running": False,
        "mac_supervisor_checked": False,
        "disk": disk_report(),
        "invoked_workers": [],
        "production_mutation": False,
    }


def _capacity_blocker(evidence: dict[str, Any]) -> str:
    parts = [
        "Cursor dispatch is WAITING_CAPACITY because on-demand spend is blocked.",
    ]
    if not evidence.get("claude_binary"):
        parts.append("Claude Pro binary is absent on this runtime.")
    if not evidence.get("codex_binary"):
        parts.append("Codex binary is absent on this runtime.")
    if not evidence.get("catalog_sqlite_present"):
        parts.append("The Beta catalog sqlite is not on this runtime.")
    parts.append("No Mac supervisor was checked or claimed running.")
    return " ".join(parts)


def _directive(now: str) -> dict[str, Any]:
    evidence = runtime_evidence()
    return {
        "id": DIRECTIVE_ID,
        "what": (
            "Wolf Intelligence Owner System overnight: server-side read gates, "
            "Owner front door on /wolf, and a local deterministic control plane. "
            "Beta only. No production mutation."
        ),
        "status": "QUEUED",
        "current_step": "Directive recorded in canonical work state",
        "worker": LOCAL_WORKER,
        "worker_reason": "local_deterministic",
        "started": now,
        "last_change": now,
        "last_real_change": now,
        "next_step": (
            "Hold the lease locally. Leave Cursor, Claude Pro, and Codex in "
            "WAITING_CAPACITY until they can run without metered spend."
        ),
        "blocker": _capacity_blocker(evidence),
        "owner_needed": False,
        "eta": None,
        "lease_until": None,
        "human_commissioned": False,
        "staff_ready": False,
        "production_mutation": False,
        "evidence": evidence,
    }


def _blank() -> dict[str, Any]:
    now = _iso()
    return {
        "schema": SCHEMA,
        "updated_at": now,
        "orchestrator": "nogrok_control",
        "parallel_orchestrator": False,
        "human_commissioned": False,
        "staff_ready": False,
        "production_mutation": False,
        "items": [_directive(now)],
    }


def _items_path(directory: Path) -> Path:
    return directory / "work-items.json"


def load(root: Path | None = None) -> dict[str, Any]:
    directory = state_dir(root)
    data = _read(_items_path(directory), {})
    if not data.get("items"):
        data = _blank()
        _write(_items_path(directory), data)
        _append_event(
            directory,
            {
                "at": data["updated_at"],
                "item_id": DIRECTIVE_ID,
                "type": "directive_recorded",
                "status": "QUEUED",
            },
        )
    return data


def save(data: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    found = blocked_name({"items": data.get("items") or []})
    if found:
        raise ValueError("blocked_worker")
    data["updated_at"] = _iso()
    data["schema"] = SCHEMA
    data["orchestrator"] = "nogrok_control"
    data["parallel_orchestrator"] = False
    data["human_commissioned"] = False
    data["staff_ready"] = False
    data["production_mutation"] = False
    _write(_items_path(state_dir(root)), data)
    return data


def _lease_expired(item: dict[str, Any], clock: datetime) -> bool:
    lease = _parse(item.get("lease_until"))
    if lease is not None:
        return clock > lease
    last = _parse(item.get("last_real_change")) or _parse(item.get("last_change")) or _parse(item.get("started"))
    if last is None:
        return True
    return (clock - last).total_seconds() > LEASE_SECONDS


def tick(root: Path | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    """Reap stale RUNNING rows and refuse blocked workers. No model call."""
    data = load(root)
    clock = now or _now()
    changed = False
    for item in data.get("items") or []:
        if str(item.get("status") or "").upper() != "RUNNING":
            continue
        worker = str(item.get("worker") or "")
        eligibility = worker_eligibility(worker)
        if worker and not eligibility.get("eligible"):
            item["status"] = "WAITING_CAPACITY" if eligibility.get("capacity") == "WAITING_CAPACITY" else "FAILED"
            item["blocker"] = eligibility.get("reason")
            item["last_change"] = _iso(clock)
            item["last_real_change"] = item["last_change"]
            item["lease_until"] = None
            item["owner_needed"] = False
            changed = True
            _append_event(
                state_dir(root),
                {
                    "at": item["last_change"],
                    "item_id": item.get("id"),
                    "type": "left_running",
                    "status": item["status"],
                    "reason": eligibility.get("reason"),
                },
            )
            continue
        if _lease_expired(item, clock):
            item["status"] = "STALE"
            item["blocker"] = "lease_expired"
            item["last_change"] = _iso(clock)
            item["last_real_change"] = item["last_change"]
            item["lease_until"] = None
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
    if changed:
        save(data, root)
    return data


def hold_local(root: Path | None = None) -> dict[str, Any]:
    """Supervisor heartbeat. Local work only. Does not spawn a worker process."""
    data = tick(root)
    clock = _now()
    lease = _iso(clock + timedelta(seconds=LEASE_SECONDS))
    changed = False
    for item in data.get("items") or []:
        worker = str(item.get("worker") or "")
        eligibility = worker_eligibility(worker)
        status = str(item.get("status") or "").upper()
        if worker in {"local", "deterministic", LOCAL_WORKER} and status in {"QUEUED", "RUNNING", "STALE"}:
            item["status"] = "RUNNING"
            item["worker"] = LOCAL_WORKER
            item["worker_reason"] = "local_deterministic"
            item["lease_until"] = lease
            item["last_change"] = _iso(clock)
            item["current_step"] = "Local supervisor holds the lease. No metered worker was called."
            item["blocker"] = _capacity_blocker(runtime_evidence())
            item["owner_needed"] = False
            item["eta"] = None
            changed = True
        elif status == "QUEUED" and not eligibility.get("eligible"):
            item["status"] = "WAITING_CAPACITY"
            item["blocker"] = eligibility.get("reason")
            item["last_change"] = _iso(clock)
            item["last_real_change"] = item["last_change"]
            item["owner_needed"] = False
            item["eta"] = None
            changed = True
            _append_event(
                state_dir(root),
                {
                    "at": item["last_change"],
                    "item_id": item.get("id"),
                    "type": "waiting_capacity",
                    "reason": eligibility.get("reason"),
                },
            )
    if changed:
        save(data, root)
        _append_event(
            state_dir(root),
            {"at": _iso(clock), "item_id": DIRECTIVE_ID, "type": "lease_held", "worker": LOCAL_WORKER},
        )
    return data


def apply_event(event: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    """Record a completion or control event. The model is not asked."""
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    found_name = blocked_name(event)
    if found_name:
        source = str(event.get("source") or "")
        if found_name in source.lower():
            raise ValueError("blocked_source")
        raise ValueError("blocked_worker")
    worker = str(event.get("worker") or "")
    if worker and str(event.get("status") or "").upper() == "RUNNING":
        eligibility = worker_eligibility(worker)
        if not eligibility.get("eligible"):
            raise ValueError(eligibility.get("reason") or "worker_rejected")
    item_id = str(event.get("item_id") or "").strip()
    if not item_id:
        raise ValueError("item_id required")
    data = tick(root)
    found = next((item for item in data.get("items") or [] if item.get("id") == item_id), None)
    if found is None:
        raise ValueError("unknown_item")
    status = str(event.get("status") or "").upper()
    allowed = {"RUNNING", "DONE", "FAILED", "BLOCKED", "STALE", "WAITING_CAPACITY", "QUEUED", "STOPPED"}
    if status not in allowed:
        raise ValueError("status not allowed")
    if status == "RUNNING":
        eligibility = worker_eligibility(str(event.get("worker") or found.get("worker") or ""))
        if not eligibility.get("eligible"):
            raise ValueError(eligibility.get("reason") or "worker_not_eligible")
        found["worker"] = event.get("worker") or found.get("worker")
        found["worker_reason"] = eligibility.get("reason")
        found["lease_until"] = _iso(_now() + timedelta(seconds=LEASE_SECONDS))
    else:
        found["lease_until"] = None
    found["status"] = status
    if event.get("current_step"):
        found["current_step"] = event["current_step"]
    if event.get("next_step"):
        found["next_step"] = event["next_step"]
    if "blocker" in event:
        found["blocker"] = event.get("blocker")
    found["owner_needed"] = bool(event.get("owner_needed"))
    found["last_change"] = _iso()
    found["last_real_change"] = found["last_change"]
    found["human_commissioned"] = False
    found["eta"] = event.get("eta") if event.get("eta") else None
    record = {
        "at": found["last_change"],
        "item_id": item_id,
        "type": "completion_event",
        "status": status,
        "worker": event.get("worker"),
        "source": "nogrok_control",
    }
    _append_event(state_dir(root), record)
    save(data, root)
    return {"ok": True, "item": found, "event": record, "human_commissioned": False, "production_mutation": False}


def apply_owner_action(
    action: str,
    item_id: str,
    *,
    worker: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """fix, reassign, or stop. Reversible control-plane state only."""
    act = (action or "").strip().lower()
    if act not in {"fix", "reassign", "stop"}:
        raise ValueError("action_not_allowed")
    if blocked_name(item_id) or blocked_name(worker):
        raise ValueError("blocked_worker")
    data = tick(root)
    found = next((item for item in data.get("items") or [] if item.get("id") == item_id), None)
    if found is None:
        raise ValueError("unknown_item")
    if act == "stop":
        found["status"] = "STOPPED"
        found["blocker"] = "stopped_by_owner"
        found["current_step"] = "Stopped from Ask Wolf. Reversible with fix."
        found["lease_until"] = None
        found["owner_needed"] = False
    elif act == "fix":
        found["status"] = "QUEUED"
        found["worker"] = LOCAL_WORKER
        found["worker_reason"] = "local_deterministic"
        found["blocker"] = None
        found["current_step"] = "Requeued by Owner. No production system was changed."
        found["lease_until"] = None
        found["owner_needed"] = False
    else:
        chosen = (worker or LOCAL_WORKER).strip().lower()
        eligibility = worker_eligibility(chosen)
        if blocked_name(chosen) or eligibility.get("reason") == "blocked_worker":
            raise ValueError("blocked_worker")
        found["worker"] = eligibility.get("worker") or chosen
        found["worker_reason"] = eligibility.get("reason")
        if eligibility.get("eligible") and found["worker"] == LOCAL_WORKER:
            found["status"] = "QUEUED"
            found["blocker"] = None
            found["current_step"] = "Reassigned to local deterministic work."
        else:
            found["status"] = "WAITING_CAPACITY"
            found["blocker"] = eligibility.get("reason")
            found["current_step"] = "Reassigned. Not invoked. Spend stays blocked."
        found["lease_until"] = None
        found["owner_needed"] = False
    found["last_change"] = _iso()
    found["last_real_change"] = found["last_change"]
    found["human_commissioned"] = False
    found["production_mutation"] = False
    found["eta"] = None
    _append_event(
        state_dir(root),
        {
            "at": found["last_change"],
            "item_id": item_id,
            "type": "owner_action",
            "action": act,
            "status": found["status"],
            "reversible": True,
            "production_mutation": False,
        },
    )
    save(data, root)
    return {
        "ok": True,
        "action": act,
        "item": found,
        "reversible": True,
        "production_mutation": False,
        "human_commissioned": False,
    }


def running_items(data: dict[str, Any] | None = None, root: Path | None = None) -> list[dict[str, Any]]:
    state = data if data is not None else tick(root)
    return [item for item in state.get("items") or [] if str(item.get("status") or "").upper() == "RUNNING"]


def needs_you(data: dict[str, Any] | None = None, root: Path | None = None) -> list[dict[str, Any]]:
    """Genuine Owner decisions only. Routine engineering stays off this list."""
    state = data if data is not None else tick(root)
    rows = [
        {
            "id": "NY-GGV-FINANCE-COMMISSION",
            "what": "GGV Finance remains NOT HUMAN COMMISSIONED until the remaining real tests pass.",
            "why": (
                "Commissioning is a material business decision. "
                "Automated checks are not HUMAN COMMISSIONED. Wolf will not mark them commissioned."
            ),
            "kind": "material_business_decision",
            "href": "/ggv/finance",
            "owner_needed": True,
        }
    ]
    for item in state.get("items") or []:
        if item.get("owner_needed") is True:
            rows.append(
                {
                    "id": item.get("id"),
                    "what": item.get("what"),
                    "why": item.get("blocker") or item.get("current_step"),
                    "kind": "owner_decision",
                    "owner_needed": True,
                }
            )
    disk = disk_report()
    if disk["below_floor"]:
        rows.append(
            {
                "id": "DISK-FLOOR",
                "what": "Disk free space is under the 100 GB floor",
                "why": "Stop. Do not delete evidence, databases, source, or backups. The floor was not lowered.",
                "kind": "capacity",
                "owner_needed": True,
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    cmd = args[0] if args else "tick"
    if cmd == "tick":
        print(json.dumps(tick(), indent=2))
        return 0
    if cmd == "hold":
        print(json.dumps(hold_local(), indent=2))
        return 0
    if cmd == "evidence":
        print(json.dumps(runtime_evidence(), indent=2))
        return 0
    print(json.dumps({"ok": False, "error": "unknown_command"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
