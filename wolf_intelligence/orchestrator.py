"""Non-Grok control-plane orchestrator — deterministic, no LLM in the control loop."""
from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import signal
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterator
from zoneinfo import ZoneInfo

from . import failover, worker_registry
from .capacity import TZ, capacity_snapshot
from .governance import GROK_WORKER_ID, load_policy
from . import paths
from .paths import ensure_dirs
from .scope_guard import build_worker_env, check_invocation

def _orch_paths() -> dict[str, Path]:
    root = paths.STATE_ROOT / "orchestrator"
    return {
        "ORCH_DIR": root,
        "ITEMS_PATH": root / "work_items.json",
        "LEASES_PATH": root / "leases.json",
        "DISPATCH_LEDGER_PATH": root / "dispatch-ledger.json",
        "DISPATCH_LEDGER_LOG_PATH": root / "dispatch-ledger.jsonl",
        "ORCHESTRATOR_LOCK_PATH": root / "orchestrator.lock",
        "CONFIG_PATH": root / "config.json",
        "AUDIT_PATH": root / "audit.jsonl",
        "NOTIFICATIONS_PATH": root / "notifications.jsonl",
        "COMPLETIONS_DIR": root / "completions",
    }


_paths = _orch_paths()
ORCH_DIR = _paths["ORCH_DIR"]
ITEMS_PATH = _paths["ITEMS_PATH"]
LEASES_PATH = _paths["LEASES_PATH"]
DISPATCH_LEDGER_PATH = _paths["DISPATCH_LEDGER_PATH"]
DISPATCH_LEDGER_LOG_PATH = _paths["DISPATCH_LEDGER_LOG_PATH"]
ORCHESTRATOR_LOCK_PATH = _paths["ORCHESTRATOR_LOCK_PATH"]
CONFIG_PATH = _paths["CONFIG_PATH"]
AUDIT_PATH = _paths["AUDIT_PATH"]
NOTIFICATIONS_PATH = _paths["NOTIFICATIONS_PATH"]
COMPLETIONS_DIR = _paths["COMPLETIONS_DIR"]

DISPATCH_LEDGER_BLOCKING = frozenset({"in_flight", "completed", "failed"})


def rebind_orchestrator_paths() -> None:
    global ORCH_DIR, ITEMS_PATH, LEASES_PATH, DISPATCH_LEDGER_PATH
    global DISPATCH_LEDGER_LOG_PATH, ORCHESTRATOR_LOCK_PATH
    global CONFIG_PATH, AUDIT_PATH, NOTIFICATIONS_PATH, COMPLETIONS_DIR
    p = _orch_paths()
    ORCH_DIR = p["ORCH_DIR"]
    ITEMS_PATH = p["ITEMS_PATH"]
    LEASES_PATH = p["LEASES_PATH"]
    DISPATCH_LEDGER_PATH = p["DISPATCH_LEDGER_PATH"]
    DISPATCH_LEDGER_LOG_PATH = p["DISPATCH_LEDGER_LOG_PATH"]
    ORCHESTRATOR_LOCK_PATH = p["ORCHESTRATOR_LOCK_PATH"]
    CONFIG_PATH = p["CONFIG_PATH"]
    AUDIT_PATH = p["AUDIT_PATH"]
    NOTIFICATIONS_PATH = p["NOTIFICATIONS_PATH"]
    COMPLETIONS_DIR = p["COMPLETIONS_DIR"]

CANONICAL_ITEM_FIELDS = ("context_size", "urgent")
DEFAULT_TIMEOUT_KILL_GRACE_S = 5.0

COMPLETION_FIELDS = (
    "WORK_ITEM_ID",
    "STATUS",
    "RESULT_SUMMARY",
    "EVIDENCE_PATHS",
    "EXCEPTIONS",
    "OWNER_ACTION_REQUIRED",
    "EXECUTED_BY",
    "BILLING_CLASS",
)

VALID_KINDS = frozenset({"build", "review", "test"})
TERMINAL_STATUSES = frozenset({"CLOSED", "FAILED", "TIMED_OUT", "FAILED_TERMINAL"})
NON_PENDING_STATUSES = frozenset({"CLOSED", "FAILED", "TIMED_OUT", "AWAITING_REVIEW", "FAILED_TERMINAL"})
TERMINAL_NO_REGRESS = frozenset({"CLOSED", "FAILED_TERMINAL"})
GROK_STATES_EXCLUDE = frozenset({"CONSERVE", "RESERVE", "EXHAUSTED"})
STATE_RANK = {"NORMAL": 0, "CONSERVE": 1, "RESERVE": 2, "EXHAUSTED": 3}

REVIEW_WORKERS = ("codex_sub", "claude_pro_sub")
BUILD_WORKERS = ("cursor_sub",)
TEST_WORKERS = ("cursor_sub",)


def _now_iso(now: datetime | str | None = None) -> str:
    if isinstance(now, str):
        return now
    dt = now or datetime.now(TZ)
    return dt.isoformat(timespec="seconds")


def _parse_now(now: datetime | str | None) -> datetime:
    if isinstance(now, str):
        return datetime.fromisoformat(now)
    return now or datetime.now(TZ)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"
    with tmp.open("w", encoding="utf-8") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _append_jsonl(path: Path, rec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


def _append_jsonl_fsync(path: Path, rec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def load_config() -> dict[str, Any]:
    cfg = _read_json(CONFIG_PATH, {})
    cfg.setdefault("claude_paused", False)
    cfg.setdefault("worktree_cwd", None)
    cfg.setdefault("worker_cmds", {})
    cfg.setdefault("allow_concurrent_orchestrators", False)
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    _write_json(CONFIG_PATH, cfg)


def load_items() -> dict[str, dict[str, Any]]:
    data = _read_json(ITEMS_PATH, {})
    return data if isinstance(data, dict) else {}


def save_items(items: dict[str, dict[str, Any]]) -> None:
    _atomic_write_json(ITEMS_PATH, items)


def load_leases() -> dict[str, dict[str, Any]]:
    data = _read_json(LEASES_PATH, {})
    return data if isinstance(data, dict) else {}


def save_leases(leases: dict[str, dict[str, Any]]) -> None:
    _write_json(LEASES_PATH, leases)


def load_dispatch_ledger() -> dict[str, dict[str, Any]]:
    ledger: dict[str, dict[str, Any]] = {}
    legacy = _read_json(DISPATCH_LEDGER_PATH, {})
    if isinstance(legacy, dict):
        ledger.update(legacy)
    if DISPATCH_LEDGER_LOG_PATH.exists():
        try:
            for line in DISPATCH_LEDGER_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                entry = json.loads(line)
                key = str(entry.get("idempotency_key") or _lease_key(
                    str(entry.get("work_item_id") or ""),
                    int(entry.get("attempt") or 0),
                ))
                ledger[key] = entry
        except (OSError, json.JSONDecodeError):
            pass
    return ledger


def save_dispatch_ledger(ledger: dict[str, dict[str, Any]]) -> None:
    """Test helper — production path appends to dispatch-ledger.jsonl only."""
    _atomic_write_json(DISPATCH_LEDGER_PATH, ledger)


def _dispatch_ledger_entry_unlocked(
    item_id: str,
    attempt: int,
    *,
    status: str,
    worker: str | None = None,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    key = _lease_key(item_id, attempt)
    prior = load_dispatch_ledger().get(key) or {}
    entry = {
        "work_item_id": item_id,
        "attempt": attempt,
        "idempotency_key": _dispatch_idempotency_key(item_id, attempt),
        "status": status,
    }
    if worker is not None:
        entry["worker"] = worker
    ts = _now_iso(now)
    if status == "in_flight":
        entry["dispatched_at"] = ts
    else:
        entry["completed_at"] = ts
    if prior.get("dispatched_at"):
        entry["dispatched_at"] = prior["dispatched_at"]
    _append_jsonl_fsync(DISPATCH_LEDGER_LOG_PATH, entry)
    return entry


def _dispatch_ledger_entry(
    item_id: str,
    attempt: int,
    *,
    status: str,
    worker: str | None = None,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    with _orch_exclusive_lock():
        return _dispatch_ledger_entry_unlocked(
            item_id,
            attempt,
            status=status,
            worker=worker,
            now=now,
        )


def _dispatch_ledger_blocks(item_id: str, attempt: int) -> bool:
    entry = load_dispatch_ledger().get(_lease_key(item_id, attempt))
    return bool(entry and entry.get("status") in DISPATCH_LEDGER_BLOCKING)


def audit_transition(
    item_id: str,
    event: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    *,
    now: datetime | str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    rec = {
        "timestamp": _now_iso(now),
        "actor": "control-plane",
        "event": event,
        "work_item_id": item_id,
        "before": before,
        "after": after,
    }
    if extra:
        rec.update(extra)
    _append_jsonl(AUDIT_PATH, rec)


def notify_owner(item_id: str, message: str, *, now: datetime | str | None = None) -> None:
    _append_jsonl(
        NOTIFICATIONS_PATH,
        {"timestamp": _now_iso(now), "work_item_id": item_id, "message": message},
    )


def _lease_key(item_id: str, attempt: int) -> str:
    return f"{item_id}:{attempt}"


def _dispatch_idempotency_key(item_id: str, attempt: int) -> str:
    return _lease_key(item_id, attempt)


@contextmanager
def _orch_exclusive_lock() -> Iterator[None]:
    ORCH_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = ORCH_DIR / ".exclusive.lock"
    with lock_path.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _item_version(item: dict[str, Any]) -> int:
    return int(item.get("version") or 0)


def _is_terminal_no_regress(item: dict[str, Any]) -> bool:
    status = str(item.get("status") or "")
    if status in TERMINAL_NO_REGRESS:
        return True
    if status in ("FAILED", "TIMED_OUT"):
        attempt = int(item.get("attempt") or 0)
        max_attempts = int(item.get("max_attempts") or 1)
        return attempt >= max_attempts
    return False


def transition_item(
    item_id: str,
    *,
    expected_status: str | tuple[str, ...] | None = None,
    expected_version: int | None = None,
    mutator: Callable[[dict[str, Any]], dict[str, Any] | None],
    event: str,
    now: datetime | str | None = None,
    extra: dict[str, Any] | None = None,
    parent_updates: dict[str, dict[str, Any]] | None = None,
) -> tuple[bool, dict[str, Any] | None, str]:
    """Atomic compare-and-swap work-item transition under exclusive lock."""
    with _orch_exclusive_lock():
        items = load_items()
        item = items.get(item_id)
        if not item:
            return False, None, "not_found"
        cur_status = str(item.get("status") or "")
        cur_ver = _item_version(item)
        if _is_terminal_no_regress(item):
            return False, None, f"terminal:{cur_status}"
        if expected_status is not None:
            allowed = (expected_status,) if isinstance(expected_status, str) else expected_status
            if cur_status not in allowed:
                return False, None, f"status_mismatch:{cur_status}"
        if expected_version is not None and cur_ver != expected_version:
            return False, None, f"version_mismatch:{cur_ver}!={expected_version}"
        before = dict(item)
        updated = mutator(dict(item))
        if updated is None:
            return False, None, "mutator_refused"
        if _is_terminal_no_regress(before) and updated.get("status") != before.get("status"):
            return False, None, "terminal_regression_blocked"
        updated["version"] = cur_ver + 1
        updated.setdefault("updated_at", _now_iso(now))
        items = load_items()
        items[item_id] = updated
        if parent_updates:
            for parent_id, prec in parent_updates.items():
                parent = items.get(parent_id)
                if not parent or _is_terminal_no_regress(parent):
                    continue
                pver = _item_version(parent)
                merged = dict(prec)
                merged["version"] = pver + 1
                merged.setdefault("updated_at", _now_iso(now))
                items[parent_id] = merged
        _atomic_write_json(ITEMS_PATH, items)
        audit_transition(item_id, event, before, updated, now=now, extra=extra)
        return True, updated, "ok"


def acquire_orchestrator_run_lock() -> tuple[bool, Any, str]:
    """Exclusive non-blocking orchestrator session lock."""
    cfg = load_config()
    if cfg.get("allow_concurrent_orchestrators"):
        return True, None, "concurrent_allowed"
    ORCH_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = ORCHESTRATOR_LOCK_PATH.open("w", encoding="utf-8")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.close()
        audit_transition(
            "orchestrator",
            "orchestrator_lock_refused",
            None,
            None,
            extra={"lock": str(ORCHESTRATOR_LOCK_PATH)},
        )
        return False, None, "orchestrator_lock_held"
    lock_file.write(f"{os.getpid()}\n")
    lock_file.flush()
    return True, lock_file, "ok"


def release_orchestrator_run_lock(lock_file: Any) -> None:
    if lock_file is None:
        return
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        lock_file.close()


def _active_item_lease(item_id: str, now: datetime | str | None = None) -> dict[str, Any] | None:
    now_dt = _parse_now(now)
    for lease in load_leases().values():
        if lease.get("work_item_id") != item_id:
            continue
        exp = lease.get("expires_at")
        if exp and datetime.fromisoformat(exp) > now_dt:
            return lease
    return None


def _item_context_size(item: dict[str, Any]) -> int:
    spec = item.get("spec") or {}
    return int(item.get("context_size") or spec.get("context_size") or 0)


def _item_urgent(item: dict[str, Any]) -> bool:
    spec = item.get("spec") or {}
    return bool(item.get("urgent") or spec.get("urgent"))


def _truncate_summary(text: str, max_lines: int = 5) -> str:
    lines = (text or "").splitlines()
    if len(lines) <= max_lines:
        return text.strip()
    return "\n".join(lines[:max_lines]).strip()


def completion_record(
    *,
    work_item_id: str,
    status: str,
    result_summary: str,
    evidence_paths: list[str],
    exceptions: list[str],
    owner_action_required: str,
    executed_by: str,
    billing_class: str,
) -> dict[str, Any]:
    return {
        "WORK_ITEM_ID": work_item_id,
        "STATUS": status,
        "RESULT_SUMMARY": _truncate_summary(result_summary),
        "EVIDENCE_PATHS": list(evidence_paths),
        "EXCEPTIONS": list(exceptions),
        "OWNER_ACTION_REQUIRED": owner_action_required,
        "EXECUTED_BY": executed_by,
        "BILLING_CLASS": billing_class,
    }


def render_completion_md(rec: dict[str, Any]) -> str:
    lines = [f"# Completion — {rec['WORK_ITEM_ID']}", ""]
    for key in COMPLETION_FIELDS:
        val = rec.get(key)
        if key == "RESULT_SUMMARY":
            lines.append(f"## {key}")
            lines.append(str(val or ""))
            lines.append("")
        elif isinstance(val, list):
            lines.append(f"## {key}")
            lines.extend(f"- {v}" for v in val)
            lines.append("")
        else:
            lines.append(f"**{key}:** {val}")
    return "\n".join(lines).strip() + "\n"


def write_completion(rec: dict[str, Any], attempt: int) -> tuple[Path, Path]:
    COMPLETIONS_DIR.mkdir(parents=True, exist_ok=True)
    base = COMPLETIONS_DIR / f"{rec['WORK_ITEM_ID']}-{attempt}"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_completion_md(rec), encoding="utf-8")
    return json_path, md_path


def _submit_record(item: dict[str, Any], *, now: datetime | str | None = None) -> dict[str, Any]:
    kind = str(item.get("kind") or "").strip()
    if kind not in VALID_KINDS:
        raise ValueError(f"invalid kind: {kind!r}")
    item_id = str(item.get("id") or "").strip()
    if not item_id:
        raise ValueError("work item id required")
    record = {
        "id": item_id,
        "kind": kind,
        "spec": item.get("spec") or {},
        "acceptance": item.get("acceptance") or "",
        "depends_on": list(item.get("depends_on") or []),
        "reviewer_gate": bool(item.get("reviewer_gate", kind == "build")),
        "timeout_s": int(item.get("timeout_s") or 300),
        "max_attempts": int(item.get("max_attempts") or 3),
        "status": "QUEUED",
        "attempt": 0,
        "version": 0,
        "created_at": _now_iso(now),
        "updated_at": _now_iso(now),
        "last_worker": None,
        "owner_action_required": "",
    }
    for field in CANONICAL_ITEM_FIELDS:
        if field in item:
            record[field] = item[field]
    return record


def submit(item: dict[str, Any], *, now: datetime | str | None = None) -> dict[str, Any]:
    ensure_dirs()
    ORCH_DIR.mkdir(parents=True, exist_ok=True)
    record = _submit_record(item, now=now)
    item_id = record["id"]
    with _orch_exclusive_lock():
        items = load_items()
        if item_id in items and items[item_id].get("status") not in TERMINAL_STATUSES:
            raise ValueError(f"work item already exists: {item_id}")
        items[item_id] = record
        _atomic_write_json(ITEMS_PATH, items)
    audit_transition(item_id, "submit", None, record, now=now)
    return record


def _submit_under_lock(item: dict[str, Any], *, now: datetime | str | None = None) -> dict[str, Any]:
    record = _submit_record(item, now=now)
    item_id = record["id"]
    items = load_items()
    if item_id in items and items[item_id].get("status") not in TERMINAL_STATUSES:
        raise ValueError(f"work item already exists: {item_id}")
    items[item_id] = record
    _atomic_write_json(ITEMS_PATH, items)
    audit_transition(item_id, "submit", None, record, now=now)
    return record


def _deps_satisfied(item: dict[str, Any], items: dict[str, dict[str, Any]]) -> bool:
    for dep in item.get("depends_on") or []:
        dep_item = items.get(dep)
        if not dep_item:
            return False
        dep_status = dep_item.get("status")
        if dep_status not in ("CLOSED", "AWAITING_REVIEW", "COMPLETED"):
            return False
    return True


def _qualified_non_grok(capacity: dict[str, Any], candidates: tuple[str, ...]) -> list[str]:
    workers = capacity.get("workers") or {}
    out: list[str] = []
    for wid in candidates:
        if wid == GROK_WORKER_ID:
            continue
        rec = workers.get(wid) or {}
        state = rec.get("state", "CONSERVE")
        if state == "EXHAUSTED":
            continue
        if worker_registry.is_metered(wid):
            continue
        out.append(wid)
    return out


def _grok_excluded(capacity: dict[str, Any], candidates: tuple[str, ...]) -> bool:
    workers = capacity.get("workers") or {}
    grok = workers.get(GROK_WORKER_ID) or {}
    grok_state = grok.get("state", "EXHAUSTED")
    if grok_state in GROK_STATES_EXCLUDE:
        return True
    return bool(_qualified_non_grok(capacity, candidates))


def route_worker(
    kind: str,
    config: dict[str, Any],
    capacity: dict[str, Any],
    item: dict[str, Any] | None = None,
    items: dict[str, dict[str, Any]] | None = None,
    now: datetime | str | None = None,
) -> str | None:
    """Legacy pool router — delegates to deterministic failover when item context is available."""
    stub = item or {"id": f"route-{kind}", "kind": kind, "spec": {}}
    return failover.select_worker(kind, config, capacity, item=stub, items=items, now=now)


def eligibility(
    item: dict[str, Any],
    items: dict[str, dict[str, Any]],
    capacity: dict[str, Any],
    config: dict[str, Any],
    now: datetime | str | None = None,
) -> tuple[str | None, str]:
    if item.get("status") not in ("QUEUED", "FAILED", "WAITING_FOR_CAPACITY"):
        return None, f"status:{item.get('status')}"
    if not _deps_satisfied(item, items):
        return None, "deps_unsatisfied"
    ctx_size = _item_context_size(item)
    if ctx_size:
        max_ctx = failover.max_eligible_context(item, capacity=capacity, orch_config=config, items=items)
        if max_ctx and ctx_size > max_ctx:
            return None, "context_exceeded"
    failover.update_grok_capacity_flag(capacity)
    decision = failover.decide_routing(
        item,
        capacity=capacity,
        orch_config=config,
        items=items,
        now=now,
    )
    action = decision.get("action")
    worker = decision.get("worker_id")
    if action in ("DISPATCH", "FAILOVER") and worker:
        if worker_registry.is_metered(worker) and not failover.metered_allowed(worker):
            return None, "metered_queue"
        return worker, action.lower()
    if action == "WAIT":
        return None, "wait_for_preferred"
    if action == "WAITING_FOR_CAPACITY":
        if decision.get("notify_owner") or _item_urgent(item):
            notify_owner(item["id"], "WAITING_FOR_CAPACITY: urgent item blocked", now=now)
        ok, updated, _reason = transition_item(
            item["id"],
            expected_status=("QUEUED", "FAILED", "WAITING_FOR_CAPACITY"),
            expected_version=_item_version(item),
            mutator=lambda rec: {**rec, "status": "WAITING_FOR_CAPACITY"},
            event="waiting_for_capacity",
            now=now,
            extra=decision.get("audit"),
        )
        if ok and updated:
            item.update(updated)
        return None, "waiting_for_capacity"
    return None, "no_eligible_worker"


def claim(
    item_id: str,
    *,
    now: datetime | str | None = None,
    force: bool = False,
) -> tuple[dict[str, Any] | None, str]:
    with _orch_exclusive_lock():
        items = load_items()
        item = items.get(item_id)
        if not item:
            return None, "not_found"
        now_dt = _parse_now(now)
        if _active_item_lease(item_id, now_dt) and not force:
            return None, "lease_active"
        if item.get("status") in TERMINAL_STATUSES:
            return None, f"status:{item.get('status')}"
        if item.get("status") not in ("QUEUED", "FAILED", "WAITING_FOR_CAPACITY"):
            return None, f"status:{item.get('status')}"
        attempt = int(item.get("attempt") or 0) + 1
        max_attempts = int(item.get("max_attempts") or 3)
        if attempt > max_attempts:
            return None, "max_attempts_exceeded"
        key = _lease_key(item_id, attempt)
        leases = load_leases()
        existing = leases.get(key)
        if existing and not force:
            exp = existing.get("expires_at")
            if exp and datetime.fromisoformat(exp) > now_dt:
                return None, "lease_active"
        cur_ver = _item_version(item)
        before = dict(item)
        item["attempt"] = attempt
        item["status"] = "CLAIMED"
        item["updated_at"] = _now_iso(now_dt)
        item["version"] = cur_ver + 1
        items[item_id] = item
        _atomic_write_json(ITEMS_PATH, items)
        lease = {
            "work_item_id": item_id,
            "attempt": attempt,
            "worker": None,
            "claimed_at": _now_iso(now_dt),
            "expires_at": (now_dt + timedelta(seconds=int(item.get("timeout_s") or 300) + 30)).isoformat(),
            "dispatched": False,
            "idempotency_key": _dispatch_idempotency_key(item_id, attempt),
        }
        leases[key] = lease
        save_leases(leases)
        audit_transition(item_id, "claim", before, item, now=now_dt, extra={"lease_key": key})
        return item, key


def refuse_double_claim(item_id: str, attempt: int) -> bool:
    if _dispatch_ledger_blocks(item_id, attempt):
        return True
    leases = load_leases()
    key = _lease_key(item_id, attempt)
    lease = leases.get(key)
    return bool(lease and lease.get("dispatched"))


FIXTURE_WORKER_MARKER = "tests/fixtures"
VERDICT_RE = re.compile(r"VERDICT:\s*(PASS|FAIL)", re.IGNORECASE)


def is_fixture_worker_cmd(argv: list[str]) -> bool:
    for part in argv:
        if FIXTURE_WORKER_MARKER in str(part).replace("\\", "/"):
            return True
    return False


def refuse_fixture_worker(config: dict[str, Any], argv: list[str]) -> bool:
    """Refuse fixture workers unless explicitly allowed (dry-run / unit tests)."""
    if config.get("allow_fixture_workers"):
        return False
    return is_fixture_worker_cmd(argv)


def _env_refused_exceptions(refused: list[str]) -> list[str]:
    return [f"env_refused:{key}" for key in refused]


def _runtime_path(item_id: str, attempt: int, suffix: str) -> Path:
    return ORCH_DIR / "runtime" / f"{item_id}-{attempt}{suffix}"


def _review_prompt(item: dict[str, Any]) -> str:
    parent = (item.get("spec") or {}).get("parent") or item["id"]
    acceptance = item.get("acceptance") or ""
    return (
        f"Review the build for work item {parent}. "
        f"Acceptance criteria: {acceptance}. "
        "Respond with a line VERDICT: PASS or VERDICT: FAIL "
        "followed by a 5-line summary."
    )


def _build_prompt(item: dict[str, Any]) -> str:
    spec = item.get("spec") or {}
    acceptance = item.get("acceptance") or ""
    task = spec.get("prompt") or json.dumps(spec)
    return (
        f"Implement work item {item['id']}. "
        f"Task: {task}. "
        f"Acceptance criteria: {acceptance}. "
        "Make the required changes in the workspace and run tests as needed."
    )


def _grade_build(worktree: str, exit_code: int | None) -> tuple[str, str, list[str]]:
    exceptions: list[str] = []
    hello = Path(worktree) / "fixture" / "hello.py"
    if exit_code not in (0, None) and exit_code != 0:
        return "FAILED", f"cursor-agent exit {exit_code}", exceptions
    if not hello.is_file():
        return "FAILED", "fixture/hello.py missing", exceptions
    try:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "discover", "-s", "fixture", "-p", "test_*.py"],
            cwd=worktree,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "FAILED", f"unittest error: {type(exc).__name__}", [str(exc)]
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-500:]
        if tail:
            exceptions.append(tail)
        return "FAILED", "unittest failed in fixture worktree", exceptions
    return "COMPLETED", "fixture/hello.py present and unittest passed", exceptions


def _extract_review_verdict(text: str) -> str | None:
    for line in text.splitlines():
        match = VERDICT_RE.search(line)
        if match:
            return match.group(1).upper()
    return None


def _grade_review_text(text: str, exit_code: int | None, *, worker_label: str = "review") -> tuple[str, str, list[str]]:
    verdict = _extract_review_verdict(text)
    if exit_code not in (0, None) and exit_code != 0:
        return "FAILED", f"{worker_label} exit {exit_code}", []
    if verdict == "FAIL":
        return "FAILED", _truncate_summary(text) or "review verdict FAIL", []
    if verdict == "PASS":
        return "COMPLETED", _truncate_summary(text) or "review verdict PASS", []
    return "FAILED", f"no VERDICT line in {worker_label} output", []


def _grade_review(output_path: Path, exit_code: int | None) -> tuple[str, str, list[str]]:
    text = output_path.read_text(encoding="utf-8") if output_path.is_file() else ""
    return _grade_review_text(text, exit_code, worker_label="codex")


def _executed_by(argv: list[str], *, using_override: bool, worker_id: str) -> str:
    if not argv:
        return worker_id
    binary = Path(argv[0]).name
    if using_override:
        return f"{worker_id} {' '.join(str(x) for x in argv[:4])}"
    resolved = shutil.which(binary) or argv[0]
    return str(resolved)


def reclaim_stale_leases(now: datetime | str | None = None) -> list[str]:
    now_dt = _parse_now(now)
    leases = load_leases()
    reclaimed: list[str] = []
    items = load_items()
    for key, lease in list(leases.items()):
        exp = lease.get("expires_at")
        if not exp:
            continue
        if datetime.fromisoformat(exp) > now_dt:
            continue
        item_id = lease.get("work_item_id")
        item = items.get(item_id or "")
        if item and item.get("status") in ("CLAIMED", "RUNNING"):
            before = dict(item)
            item["status"] = "QUEUED"
            item["updated_at"] = _now_iso(now_dt)
            item["version"] = _item_version(item) + 1
            items[item_id] = item
            audit_transition(item_id, "lease_reclaimed", before, item, now=now_dt, extra={"lease_key": key})
        reclaimed.append(key)
        del leases[key]
    if reclaimed:
        save_leases(leases)
        save_items(items)
    return reclaimed


def _worker_cmd(worker_id: str, config: dict[str, Any], item: dict[str, Any], worktree: str) -> list[str]:
    overrides = config.get("worker_cmds") or {}
    if worker_id in overrides:
        cmd = list(overrides[worker_id])
        attempt = str(item.get("attempt") or 1)
        return [
            str(x)
            .replace("{worktree}", worktree)
            .replace("{item_id}", item["id"])
            .replace("{attempt}", attempt)
            for x in cmd
        ]
    spec = item.get("spec") or {}
    attempt = int(item.get("attempt") or 1)
    if worker_id == "cursor_sub":
        prompt = spec.get("prompt") or json.dumps(spec)
        return [
            "cursor-agent",
            "-p",
            "--model",
            str(spec.get("model") or "composer-2.5"),
            "--trust",
            "--force",
            "--sandbox",
            "enabled",
            "--workspace",
            worktree,
            "--output-format",
            "text",
            prompt,
        ]
    if worker_id == "codex_sub":
        out_file = str(_runtime_path(item["id"], attempt, ".codex.out"))
        prompt = _review_prompt(item) if item.get("kind") == "review" else json.dumps(
            {"acceptance": item.get("acceptance"), "spec": spec}
        )
        sandbox = "read-only" if item.get("kind") == "review" else "workspace-write"
        return [
            "codex",
            "exec",
            "-c",
            "forced_login_method=chatgpt",
            "-s",
            sandbox,
            "-C",
            worktree,
            "-o",
            out_file,
            prompt,
        ]
    if worker_id == "claude_pro_sub":
        argv = [
            "claude",
            "-p",
            "--output-format",
            "json",
            "--no-session-persistence",
            "--permission-mode",
            "plan" if item.get("kind") == "review" else "acceptEdits",
        ]
        if item.get("kind") != "review":
            argv.extend(["--allowedTools", "Edit,Write,Read,Bash(python3 -m unittest:*)"])
        return argv
    return []


def worker_has_command_builder(
    worker_id: str,
    config: dict[str, Any],
    item: dict[str, Any],
) -> bool:
    worktree = str(config.get("worktree_cwd") or ".")
    return bool(_worker_cmd(worker_id, config, item, worktree))


def _billing_class(worker_id: str) -> str:
    if worker_registry.is_metered(worker_id):
        return "metered"
    meta = worker_registry.WORKERS.get(worker_id) or {}
    bc = meta.get("billing_class") or "none"
    if bc in ("subscription", "free", "local"):
        return "subscription" if bc == "subscription" else "none"
    return "none"


def _timeout_kill_grace_s(config: dict[str, Any]) -> float:
    return float(config.get("timeout_kill_grace_s") or DEFAULT_TIMEOUT_KILL_GRACE_S)


def _terminate_process_group(pgid: int, *, grace_s: float) -> None:
    try:
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    if grace_s > 0:
        deadline = time.perf_counter() + grace_s
        while time.perf_counter() < deadline:
            time.sleep(0.05)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _close_proc_pipes(proc: subprocess.Popen) -> None:
    for stream in (proc.stdin, proc.stdout, proc.stderr):
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass


def _communicate_bounded(
    proc: subprocess.Popen,
    *,
    pgid: int,
    stdin_data: str | None,
    timeout_s: float,
    kill_grace_s: float,
    started: float,
) -> tuple[str | None, str | None, str | None]:
    hard_deadline = started + timeout_s + kill_grace_s + 1.0
    try:
        out, err_txt = proc.communicate(input=stdin_data, timeout=timeout_s)
        return out, err_txt, None
    except subprocess.TimeoutExpired as te:
        _terminate_process_group(pgid, grace_s=kill_grace_s)
        drain_timeout = max(0.05, hard_deadline - time.perf_counter())
        out = te.output if isinstance(te.output, str) else (te.output or b"").decode(errors="replace")
        err_txt = te.stderr if isinstance(te.stderr, str) else (te.stderr or b"").decode(errors="replace")
        try:
            more_out, more_err = proc.communicate(timeout=drain_timeout)
            if isinstance(more_out, bytes):
                more_out = more_out.decode(errors="replace")
            if isinstance(more_err, bytes):
                more_err = more_err.decode(errors="replace")
            out = (out or "") + (more_out or "")
            err_txt = (err_txt or "") + (more_err or "")
        except subprocess.TimeoutExpired as te2:
            part_out = te2.output if isinstance(te2.output, str) else (te2.output or b"").decode(errors="replace")
            part_err = te2.stderr if isinstance(te2.stderr, str) else (te2.stderr or b"").decode(errors="replace")
            out = (out or "") + (part_out or "")
            err_txt = (err_txt or "") + (part_err or "")
            _terminate_process_group(pgid, grace_s=0)
            try:
                proc.communicate(timeout=0.2)
            except subprocess.TimeoutExpired:
                pass
        if proc.poll() is None:
            _terminate_process_group(pgid, grace_s=0)
        _close_proc_pipes(proc)
        return out, err_txt, "TIMEOUT"


def dispatch_item(
    item: dict[str, Any],
    worker_id: str,
    *,
    worktree: str,
    config: dict[str, Any],
    now: datetime | str | None = None,
) -> dict[str, Any]:
    item_id = item["id"]
    attempt = int(item.get("attempt") or 1)
    key = _lease_key(item_id, attempt)
    idempotency_key = _dispatch_idempotency_key(item_id, attempt)

    with _orch_exclusive_lock():
        if _dispatch_ledger_blocks(item_id, attempt):
            return {
                "ok": False,
                "error": "already_dispatched",
                "lease_key": key,
                "idempotency_key": idempotency_key,
            }
        leases = load_leases()
        lease = leases.get(key)
        if lease and lease.get("dispatched"):
            return {
                "ok": False,
                "error": "already_dispatched",
                "lease_key": key,
                "idempotency_key": idempotency_key,
            }
        items = load_items()
        before = dict(items[item_id])
        running = dict(items[item_id])
        running["status"] = "RUNNING"
        running["last_worker"] = worker_id
        running["updated_at"] = _now_iso(now)
        running["version"] = _item_version(running) + 1
        items[item_id] = running
        _atomic_write_json(ITEMS_PATH, items)
        if lease:
            lease["dispatched"] = True
            lease["worker"] = worker_id
            lease["idempotency_key"] = idempotency_key
            leases[key] = lease
            save_leases(leases)
        audit_transition(item_id, "dispatch", before, items[item_id], now=now, extra={"worker": worker_id})

    argv = _worker_cmd(worker_id, config, items[item_id], worktree)
    if not argv:
        return _finish_dispatch(
            items[item_id],
            worker_id,
            status="FAILED",
            summary=f"unsupported worker or empty command: {worker_id}",
            exceptions=["empty_argv"],
            exit_code=None,
            now=now,
            argv=[worker_id],
            using_override=False,
        )
    pl = load_policy()
    policy = pl.policy if pl and pl.policy else None
    env, refused_env = build_worker_env(worktree, os.environ, policy=policy)
    cwd = worktree
    using_override = worker_id in (config.get("worker_cmds") or {})
    if refuse_fixture_worker(config, argv):
        return _finish_dispatch(
            items[item_id],
            worker_id,
            status="FAILED",
            summary="fixture worker refused in non-dry-run path",
            exceptions=["fixture_worker_refused"],
            exit_code=None,
            now=now,
            argv=argv,
            using_override=using_override,
        )
    scope_ok, scope_reasons = (True, []) if using_override else check_invocation(
        worker_id, argv, cwd, env, policy=policy
    )
    if not scope_ok:
        return _finish_dispatch(
            items[item_id],
            worker_id,
            status="FAILED",
            summary="scope refused",
            exceptions=scope_reasons + _env_refused_exceptions(refused_env),
            exit_code=None,
            now=now,
            argv=argv,
            using_override=using_override,
        )

    runtime_dir = ORCH_DIR / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    completion_path = runtime_dir / f"{item_id}-{attempt}.completion.json"
    codex_output_path = _runtime_path(item_id, attempt, ".codex.out")
    spec = items[item_id].get("spec") or {}
    stdin_data = spec.get("stdin") if using_override else None
    if using_override and worker_id == "codex_sub" and stdin_data is None:
        stdin_data = json.dumps({"acceptance": items[item_id].get("acceptance"), "spec": spec})
    elif worker_id == "claude_pro_sub" and stdin_data is None:
        stdin_data = (
            _review_prompt(items[item_id])
            if items[item_id].get("kind") == "review"
            else _build_prompt(items[item_id])
        )
    elif not using_override and worker_id == "codex_sub" and items[item_id].get("kind") != "review":
        stdin_data = json.dumps({"acceptance": items[item_id].get("acceptance"), "spec": spec})

    timeout_s = float(items[item_id].get("timeout_s") or 300)
    kill_grace_s = _timeout_kill_grace_s(config)
    started = time.perf_counter()
    with _orch_exclusive_lock():
        if _dispatch_ledger_blocks(item_id, attempt):
            return {
                "ok": False,
                "error": "already_dispatched",
                "lease_key": key,
                "idempotency_key": idempotency_key,
            }
        _dispatch_ledger_entry_unlocked(item_id, attempt, status="in_flight", worker=worker_id, now=now)
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=cwd,
            start_new_session=True,
        )
    except OSError as exc:
        _dispatch_ledger_entry(item_id, attempt, status="failed", worker=worker_id, now=now)
        return _finish_dispatch(
            items[item_id],
            worker_id,
            status="FAILED",
            summary=str(exc),
            exceptions=[type(exc).__name__],
            exit_code=None,
            now=now,
            argv=argv,
            using_override=using_override,
        )

    worker_pid = proc.pid
    pgid = proc.pid
    out, err_txt, err_kind = _communicate_bounded(
        proc,
        pgid=pgid,
        stdin_data=stdin_data,
        timeout_s=timeout_s,
        kill_grace_s=kill_grace_s,
        started=started,
    )

    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    exit_code = proc.returncode if err_kind is None else None

    payload: dict[str, Any] = {}
    evidence: list[str] = []
    if using_override:
        if completion_path.exists():
            try:
                payload = json.loads(completion_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {}
        elif out.strip():
            try:
                payload = json.loads(out.strip().splitlines()[-1])
            except (json.JSONDecodeError, IndexError):
                payload = {"summary": out.strip()[:500]}
        if completion_path.exists():
            evidence.append(str(completion_path))

    if err_kind == "TIMEOUT":
        failover.record_availability_from_dispatch(
            worker_id,
            exit_code=exit_code,
            stderr=err_txt or "",
            stdout=out or "",
            now=now,
        )
        return _finish_dispatch(
            items[item_id],
            worker_id,
            status="TIMED_OUT",
            summary=f"timeout after {timeout_s}s",
            exceptions=["TIMEOUT"],
            exit_code=exit_code,
            evidence=evidence,
            payload=payload,
            now=now,
            elapsed_ms=elapsed_ms,
            pid=worker_pid,
            argv=argv,
            using_override=using_override,
        )

    if exit_code != 0 or err_txt.strip():
        failover.record_availability_from_dispatch(
            worker_id,
            exit_code=exit_code,
            stderr=err_txt or "",
            stdout=out or "",
            now=now,
        )

    exceptions: list[str] = _env_refused_exceptions(refused_env)
    if using_override:
        verdict = str(payload.get("verdict") or payload.get("status") or "").upper()
        if exit_code != 0:
            status = "FAILED"
        elif item["kind"] == "review" and verdict == "FAIL":
            status = "FAILED"
        elif item["kind"] == "review" and verdict not in ("PASS", "OK", "SUCCESS", ""):
            status = "FAILED" if verdict else "COMPLETED"
        else:
            status = "COMPLETED"
        summary = str(payload.get("summary") or payload.get("result") or out[:500] or "ok")
        if err_txt.strip() and status == "FAILED":
            exceptions.append(err_txt.strip())
    elif item["kind"] == "build":
        hello_path = Path(worktree) / "fixture" / "hello.py"
        status, summary, grade_exc = _grade_build(worktree, exit_code)
        exceptions.extend(grade_exc)
        if hello_path.is_file():
            evidence.append(str(hello_path))
    elif item["kind"] == "review" and worker_id == "claude_pro_sub":
        review_text = out or ""
        if not review_text.strip() and err_txt.strip():
            review_text = err_txt
        status, summary, grade_exc = _grade_review_text(review_text, exit_code, worker_label="claude")
        exceptions.extend(grade_exc)
    elif item["kind"] == "review":
        status, summary, grade_exc = _grade_review(codex_output_path, exit_code)
        exceptions.extend(grade_exc)
        if codex_output_path.is_file():
            evidence.append(str(codex_output_path))
    else:
        status = "COMPLETED" if exit_code == 0 else "FAILED"
        summary = out[:500] or "ok"
        if err_txt.strip() and status == "FAILED":
            exceptions.append(err_txt.strip())

    return _finish_dispatch(
        items[item_id],
        worker_id,
        status=status,
        summary=summary,
        exceptions=exceptions,
        exit_code=exit_code,
        evidence=evidence,
        payload=payload,
        now=now,
        elapsed_ms=elapsed_ms,
        pid=worker_pid,
        argv=argv,
        using_override=using_override,
    )


def _finish_dispatch(
    item: dict[str, Any],
    worker_id: str,
    *,
    status: str,
    summary: str,
    exceptions: list[str],
    exit_code: int | None,
    evidence: list[str] | None = None,
    payload: dict[str, Any] | None = None,
    now: datetime | str | None = None,
    elapsed_ms: float | None = None,
    pid: int | None = None,
    argv: list[str] | None = None,
    using_override: bool = False,
) -> dict[str, Any]:
    item_id = item["id"]
    snapshot = load_items().get(item_id, item)
    attempt = int(snapshot.get("attempt") or 1)
    expected_version = _item_version(snapshot)
    owner_action = str((payload or {}).get("owner_action_required") or snapshot.get("owner_action_required") or "")

    if argv is None:
        cfg = load_config()
        worktree = str(cfg.get("worktree_cwd") or ".")
        try:
            argv = _worker_cmd(worker_id, cfg, snapshot, worktree)
        except ValueError:
            argv = [worker_id]
    rec = completion_record(
        work_item_id=item_id,
        status=status,
        result_summary=summary,
        evidence_paths=evidence or [],
        exceptions=exceptions,
        owner_action_required=owner_action,
        executed_by=_executed_by(argv, using_override=using_override, worker_id=worker_id),
        billing_class=_billing_class(worker_id),
    )
    json_path, md_path = write_completion(rec, attempt)
    rec["EVIDENCE_PATHS"] = list(rec["EVIDENCE_PATHS"]) + [str(json_path), str(md_path)]

    review_id: str | None = None
    parent_updates: dict[str, dict[str, Any]] = {}

    def _apply_finish(rec_item: dict[str, Any]) -> dict[str, Any] | None:
        nonlocal review_id
        updated = dict(rec_item)
        items_now = load_items()
        if status == "COMPLETED" and updated["kind"] == "build" and updated.get("reviewer_gate"):
            review_id = f"{updated['id']}-review-{attempt}"
            if review_id not in items_now:
                _submit_under_lock(
                    {
                        "id": review_id,
                        "kind": "review",
                        "spec": {"parent": updated["id"], "acceptance": updated.get("acceptance")},
                        "acceptance": updated.get("acceptance"),
                        "depends_on": [updated["id"]],
                        "reviewer_gate": False,
                        "timeout_s": updated.get("timeout_s"),
                        "max_attempts": 1,
                    },
                    now=now,
                )
            updated["review_enqueued"] = review_id
            updated["status"] = "AWAITING_REVIEW"
        elif status == "COMPLETED" and updated["kind"] == "review":
            parent = (updated.get("spec") or {}).get("parent")
            if parent and items_now.get(parent):
                parent_item = dict(items_now[parent])
                parent_item["status"] = "CLOSED"
                parent_item["updated_at"] = _now_iso(now)
                parent_updates[parent] = parent_item
            updated["status"] = "CLOSED"
        elif status == "FAILED" and updated["kind"] == "review":
            parent = (updated.get("spec") or {}).get("parent")
            if parent and items_now.get(parent):
                parent_item = dict(items_now[parent])
                if int(parent_item.get("attempt") or 0) < int(parent_item.get("max_attempts") or 1):
                    parent_item["status"] = "QUEUED"
                    parent_item["updated_at"] = _now_iso(now)
                    parent_updates[parent] = parent_item
            updated["status"] = "FAILED"
        elif status in ("FAILED", "TIMED_OUT") and int(updated.get("attempt") or 0) < int(updated.get("max_attempts") or 1):
            updated["status"] = "QUEUED"
        elif status == "COMPLETED":
            updated["status"] = "CLOSED"
        else:
            updated["status"] = status if status in TERMINAL_STATUSES else status
        updated["updated_at"] = _now_iso(now)
        updated["last_result"] = status
        return updated

    ok, finished, reason = transition_item(
        item_id,
        expected_status=("RUNNING", "CLAIMED"),
        expected_version=expected_version,
        mutator=_apply_finish,
        event="complete",
        now=now,
        extra={"worker": worker_id, "exit_code": exit_code},
        parent_updates=parent_updates,
    )
    if not ok or not finished:
        return {
            "ok": False,
            "status": status,
            "error": reason,
            "completion": rec,
            "review_enqueued": review_id,
            "elapsed_ms": elapsed_ms,
            "exit_code": exit_code,
            "pid": pid,
            "worker": worker_id,
        }

    key = _lease_key(item_id, attempt)
    with _orch_exclusive_lock():
        leases = load_leases()
        leases.pop(key, None)
        save_leases(leases)
    ledger_status = "completed" if status == "COMPLETED" else "failed"
    _dispatch_ledger_entry(item_id, attempt, status=ledger_status, worker=worker_id, now=now)

    terminal_fail = finished["status"] in ("FAILED", "TIMED_OUT", "FAILED_TERMINAL") and int(
        finished.get("attempt") or 0
    ) >= int(finished.get("max_attempts") or 1)
    if owner_action:
        notify_owner(item_id, owner_action, now=now)
    elif terminal_fail:
        notify_owner(item_id, f"terminally failed: {status}", now=now)

    return {
        "ok": status == "COMPLETED" and ok,
        "status": status,
        "completion": rec,
        "review_enqueued": review_id,
        "elapsed_ms": elapsed_ms,
        "exit_code": exit_code,
        "pid": pid,
        "worker": worker_id,
    }


def reevaluate_waiting_for_capacity(*, now: datetime | str | None = None) -> list[str]:
    config = load_config()
    pl = load_policy()
    cap = capacity_snapshot(now, policy=pl.policy, policy_mode=pl.mode)
    items = load_items()
    resumed: list[str] = []
    for item_id, item in list(items.items()):
        if item.get("status") != "WAITING_FOR_CAPACITY":
            continue
        failover.update_grok_capacity_flag(cap)
        decision = failover.decide_routing(
            item,
            capacity=cap,
            orch_config=config,
            items=items,
            now=now,
        )
        action = decision.get("action")
        worker = decision.get("worker_id")
        if action not in ("DISPATCH", "FAILOVER") or not worker:
            continue
        capability = failover.capability_for_item(item)
        primary_pool = set(failover.preferred_workers(capability, config))
        primary_pool.update(failover.FALLBACK_BY_CAPABILITY.get(capability, ()))
        if worker not in primary_pool:
            continue
        ok, updated, _reason = transition_item(
            item_id,
            expected_status="WAITING_FOR_CAPACITY",
            expected_version=_item_version(item),
            mutator=lambda rec: {**rec, "status": "QUEUED"},
            event="capacity_resumed",
            now=now,
            extra=decision.get("audit"),
        )
        if ok:
            resumed.append(item_id)
    return resumed


def _run_once_impl(*, worktree: str | None = None, now: datetime | str | None = None) -> dict[str, Any]:
    ensure_dirs()
    ORCH_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()
    if worktree:
        config["worktree_cwd"] = worktree
        save_config(config)
    worktree_cwd = str(config.get("worktree_cwd") or worktree or os.getcwd())
    reclaim_stale_leases(now=now)
    pl = load_policy()
    cap = capacity_snapshot(now, policy=pl.policy, policy_mode=pl.mode)
    items = load_items()
    processed: list[dict[str, Any]] = []
    pending = sorted(
        (iid for iid, it in items.items() if it.get("status") in ("QUEUED", "WAITING_FOR_CAPACITY")),
        key=lambda x: x,
    )
    seen = set(pending)
    while pending:
        item_id = pending.pop(0)
        items = load_items()
        item = items.get(item_id)
        if not item or item.get("status") not in ("QUEUED", "WAITING_FOR_CAPACITY"):
            continue
        worker, reason = eligibility(item, items, cap, config, now=now)
        if not worker:
            processed.append({"work_item_id": item_id, "action": "skipped", "reason": reason})
            continue
        claimed, key = claim(item_id, now=now)
        if not claimed:
            processed.append({"work_item_id": item_id, "action": "claim_refused", "reason": key})
            continue
        result = dispatch_item(claimed, worker, worktree=worktree_cwd, config=config, now=now)
        processed.append({"work_item_id": item_id, "action": "dispatched", "worker": worker, **result})
        review_id = result.get("review_enqueued")
        if review_id and review_id not in seen:
            seen.add(review_id)
            pending.append(review_id)
            pending.sort()
    return {"processed": processed, "queue_depth": sum(1 for i in items.values() if i.get("status") == "QUEUED")}


def run_once(*, worktree: str | None = None, now: datetime | str | None = None) -> dict[str, Any]:
    acquired, lock_fd, lock_reason = acquire_orchestrator_run_lock()
    if not acquired:
        return {"processed": [], "queue_depth": 0, "error": lock_reason}
    try:
        return _run_once_impl(worktree=worktree, now=now)
    finally:
        release_orchestrator_run_lock(lock_fd)


def run_until_idle(*, worktree: str | None = None, max_rounds: int = 50, now: datetime | str | None = None) -> dict[str, Any]:
    acquired, lock_fd, lock_reason = acquire_orchestrator_run_lock()
    if not acquired:
        return {"rounds": 0, "pending": 0, "items": load_items(), "history": [], "error": lock_reason}
    rounds: list[dict[str, Any]] = []
    try:
        for _ in range(max_rounds):
            out = _run_once_impl(worktree=worktree, now=now)
            rounds.append(out)
            if not out["processed"]:
                break
            if all(p.get("action") == "skipped" for p in out["processed"]):
                break
        items = load_items()
        pending = [i for i in items.values() if i.get("status") not in NON_PENDING_STATUSES]
        return {"rounds": len(rounds), "pending": len(pending), "items": items, "history": rounds}
    finally:
        release_orchestrator_run_lock(lock_fd)


def status() -> dict[str, Any]:
    items = load_items()
    leases = load_leases()
    return {
        "items": items,
        "leases": leases,
        "counts": {
            s: sum(1 for i in items.values() if i.get("status") == s)
            for s in ("QUEUED", "CLAIMED", "RUNNING", "COMPLETED", "CLOSED", "FAILED", "TIMED_OUT")
        },
    }


def show(item_id: str) -> dict[str, Any] | None:
    return load_items().get(item_id)


def health(*, now: datetime | str | None = None) -> dict[str, Any]:
    issues: list[str] = []
    items = load_items()
    leases = load_leases()
    if not ORCH_DIR.exists():
        issues.append("orchestrator_dir_missing")
    for path in (ITEMS_PATH, LEASES_PATH):
        if path.exists():
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                issues.append(f"corrupt:{path.name}")

    reclaimed = reclaim_stale_leases(now=now)
    resumed = reevaluate_waiting_for_capacity(now=now)
    workers = {
        "cursor_sub": shutil.which("cursor-agent"),
        "codex_sub": shutil.which("codex"),
        "claude_pro_sub": shutil.which("claude"),
    }
    missing = [w for w, bin_path in workers.items() if not bin_path]

    pl = load_policy()
    cap = capacity_snapshot(now, policy=pl.policy, policy_mode=pl.mode)
    grok = (cap.get("workers") or {}).get(GROK_WORKER_ID) or {}
    obs_at = grok.get("observed_at")
    stale = False
    if obs_at:
        try:
            age_h = (_parse_now(now) - datetime.fromisoformat(obs_at)).total_seconds() / 3600.0
            stale = age_h > float((pl.policy or {}).get("capacity_decay", {}).get("max_observation_age_hours", 24))
        except ValueError:
            stale = True
    else:
        stale = True

    if missing:
        issues.append(f"missing_workers:{','.join(missing)}")
    if stale:
        issues.append("capacity_stale")
    if reclaimed:
        issues.append(f"reclaimed_leases:{len(reclaimed)}")

    ok = not any(i.startswith("corrupt:") or i == "orchestrator_dir_missing" for i in issues)
    return {
        "ok": ok,
        "issues": issues,
        "reclaimed_leases": reclaimed,
        "workers": workers,
        "capacity_at": cap.get("at"),
        "grok_state": grok.get("state"),
        "items": len(items),
        "leases": len(load_leases()),
        "resumed_from_capacity_wait": resumed,
    }


def grok_invocation_count() -> int:
    if not AUDIT_PATH.exists():
        return 0
    count = 0
    for line in AUDIT_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        worker = rec.get("worker") or (rec.get("after") or {}).get("last_worker")
        extra = json.dumps(rec)
        if GROK_WORKER_ID in str(worker) or "grok" in extra.lower():
            if rec.get("event") == "dispatch":
                count += 1
    return count
