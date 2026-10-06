"""Non-Grok control-plane orchestrator — deterministic, no LLM in the control loop."""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import failover, worker_registry
from .adapters.subscription_cli import scrubbed_env
from .capacity import TZ, capacity_snapshot
from .governance import GROK_WORKER_ID, load_policy
from . import paths
from .paths import ensure_dirs
from .scope_guard import check_invocation

def _orch_paths() -> dict[str, Path]:
    root = paths.STATE_ROOT / "orchestrator"
    return {
        "ORCH_DIR": root,
        "ITEMS_PATH": root / "work_items.json",
        "LEASES_PATH": root / "leases.json",
        "CONFIG_PATH": root / "config.json",
        "AUDIT_PATH": root / "audit.jsonl",
        "NOTIFICATIONS_PATH": root / "notifications.jsonl",
        "COMPLETIONS_DIR": root / "completions",
    }


_paths = _orch_paths()
ORCH_DIR = _paths["ORCH_DIR"]
ITEMS_PATH = _paths["ITEMS_PATH"]
LEASES_PATH = _paths["LEASES_PATH"]
CONFIG_PATH = _paths["CONFIG_PATH"]
AUDIT_PATH = _paths["AUDIT_PATH"]
NOTIFICATIONS_PATH = _paths["NOTIFICATIONS_PATH"]
COMPLETIONS_DIR = _paths["COMPLETIONS_DIR"]


def rebind_orchestrator_paths() -> None:
    global ORCH_DIR, ITEMS_PATH, LEASES_PATH, CONFIG_PATH, AUDIT_PATH, NOTIFICATIONS_PATH, COMPLETIONS_DIR
    p = _orch_paths()
    ORCH_DIR = p["ORCH_DIR"]
    ITEMS_PATH = p["ITEMS_PATH"]
    LEASES_PATH = p["LEASES_PATH"]
    CONFIG_PATH = p["CONFIG_PATH"]
    AUDIT_PATH = p["AUDIT_PATH"]
    NOTIFICATIONS_PATH = p["NOTIFICATIONS_PATH"]
    COMPLETIONS_DIR = p["COMPLETIONS_DIR"]

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
TERMINAL_STATUSES = frozenset({"CLOSED", "FAILED", "TIMED_OUT"})
NON_PENDING_STATUSES = frozenset({"CLOSED", "FAILED", "TIMED_OUT", "AWAITING_REVIEW"})
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


def _append_jsonl(path: Path, rec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


def load_config() -> dict[str, Any]:
    cfg = _read_json(CONFIG_PATH, {})
    cfg.setdefault("claude_paused", False)
    cfg.setdefault("worktree_cwd", None)
    cfg.setdefault("worker_cmds", {})
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    _write_json(CONFIG_PATH, cfg)


def load_items() -> dict[str, dict[str, Any]]:
    data = _read_json(ITEMS_PATH, {})
    return data if isinstance(data, dict) else {}


def save_items(items: dict[str, dict[str, Any]]) -> None:
    _write_json(ITEMS_PATH, items)


def load_leases() -> dict[str, dict[str, Any]]:
    data = _read_json(LEASES_PATH, {})
    return data if isinstance(data, dict) else {}


def save_leases(leases: dict[str, dict[str, Any]]) -> None:
    _write_json(LEASES_PATH, leases)


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


def submit(item: dict[str, Any], *, now: datetime | str | None = None) -> dict[str, Any]:
    ensure_dirs()
    ORCH_DIR.mkdir(parents=True, exist_ok=True)
    kind = str(item.get("kind") or "").strip()
    if kind not in VALID_KINDS:
        raise ValueError(f"invalid kind: {kind!r}")
    item_id = str(item.get("id") or "").strip()
    if not item_id:
        raise ValueError("work item id required")
    items = load_items()
    if item_id in items and items[item_id].get("status") not in TERMINAL_STATUSES:
        raise ValueError(f"work item already exists: {item_id}")
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
        "created_at": _now_iso(now),
        "updated_at": _now_iso(now),
        "last_worker": None,
        "owner_action_required": "",
    }
    items[item_id] = record
    save_items(items)
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
        if decision.get("notify_owner"):
            notify_owner(item["id"], "WAITING_FOR_CAPACITY: urgent item blocked", now=now)
        before = dict(item)
        item["status"] = "WAITING_FOR_CAPACITY"
        item["updated_at"] = _now_iso(now)
        all_items = load_items()
        all_items[item["id"]] = item
        save_items(all_items)
        audit_transition(item["id"], "waiting_for_capacity", before, item, now=now, extra=decision.get("audit"))
        return None, "waiting_for_capacity"
    return None, "no_eligible_worker"


def claim(
    item_id: str,
    *,
    now: datetime | str | None = None,
    force: bool = False,
) -> tuple[dict[str, Any] | None, str]:
    items = load_items()
    item = items.get(item_id)
    if not item:
        return None, "not_found"
    attempt = int(item.get("attempt") or 0) + 1
    key = _lease_key(item_id, attempt)
    leases = load_leases()
    existing = leases.get(key)
    now_dt = _parse_now(now)
    if existing and not force:
        exp = existing.get("expires_at")
        if exp and datetime.fromisoformat(exp) > now_dt:
            return None, "lease_active"
    before = dict(item)
    item["attempt"] = attempt
    item["status"] = "CLAIMED"
    item["updated_at"] = _now_iso(now_dt)
    items[item_id] = item
    save_items(items)
    lease = {
        "work_item_id": item_id,
        "attempt": attempt,
        "worker": None,
        "claimed_at": _now_iso(now_dt),
        "expires_at": (now_dt + timedelta(seconds=int(item.get("timeout_s") or 300) + 30)).isoformat(),
        "dispatched": False,
    }
    leases[key] = lease
    save_leases(leases)
    audit_transition(item_id, "claim", before, item, now=now_dt, extra={"lease_key": key})
    return item, key


def refuse_double_claim(item_id: str, attempt: int) -> bool:
    leases = load_leases()
    key = _lease_key(item_id, attempt)
    lease = leases.get(key)
    return bool(lease and lease.get("dispatched"))


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
    completion_file = str(ORCH_DIR / "runtime" / f"{item['id']}-{item.get('attempt')}.completion.json")
    if worker_id == "cursor_sub":
        prompt = spec.get("prompt") or json.dumps(spec)
        return [
            "cursor-agent",
            "--print",
            "--output-format",
            "json",
            "--mode",
            "ask",
            "--sandbox",
            "enabled",
            "--trust",
            "--workspace",
            worktree,
            "--model",
            str(spec.get("model") or "composer-2.5"),
            prompt,
        ]
    if worker_id == "codex_sub":
        return [
            "codex",
            "exec",
            "--json",
            "--ephemeral",
            "--skip-git-repo-check",
            "--ignore-user-config",
            "-s",
            "read-only",
            "-C",
            worktree,
            "-c",
            'forced_login_method="chatgpt"',
            "-",
        ]
    if worker_id == "claude_pro_sub":
        return ["claude", "-p", "--output-format", "json", "--no-session-persistence"]
    raise ValueError(f"unsupported worker: {worker_id}")


def _billing_class(worker_id: str) -> str:
    if worker_registry.is_metered(worker_id):
        return "metered"
    meta = worker_registry.WORKERS.get(worker_id) or {}
    bc = meta.get("billing_class") or "none"
    if bc in ("subscription", "free", "local"):
        return "subscription" if bc == "subscription" else "none"
    return "none"


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        pass


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
    leases = load_leases()
    lease = leases.get(key)
    if lease and lease.get("dispatched"):
        return {"ok": False, "error": "already_dispatched", "lease_key": key}
    items = load_items()
    before = dict(items[item_id])
    items[item_id]["status"] = "RUNNING"
    items[item_id]["last_worker"] = worker_id
    items[item_id]["updated_at"] = _now_iso(now)
    save_items(items)
    if lease:
        lease["dispatched"] = True
        lease["worker"] = worker_id
        leases[key] = lease
        save_leases(leases)
    audit_transition(item_id, "dispatch", before, items[item_id], now=now, extra={"worker": worker_id})

    argv = _worker_cmd(worker_id, config, items[item_id], worktree)
    env = scrubbed_env()
    cwd = worktree
    using_override = worker_id in (config.get("worker_cmds") or {})
    scope_ok, scope_reasons = (True, []) if using_override else check_invocation(worker_id, argv, cwd, env)
    if not scope_ok:
        return _finish_dispatch(
            items[item_id],
            worker_id,
            status="FAILED",
            summary="scope refused",
            exceptions=scope_reasons,
            exit_code=None,
            now=now,
        )

    runtime_dir = ORCH_DIR / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    completion_path = runtime_dir / f"{item_id}-{attempt}.completion.json"
    spec = items[item_id].get("spec") or {}
    stdin_data = spec.get("stdin")
    if worker_id == "codex_sub" and stdin_data is None:
        stdin_data = json.dumps({"acceptance": items[item_id].get("acceptance"), "spec": spec})

    timeout_s = float(items[item_id].get("timeout_s") or 300)
    started = time.perf_counter()
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
        return _finish_dispatch(
            items[item_id],
            worker_id,
            status="FAILED",
            summary=str(exc),
            exceptions=[type(exc).__name__],
            exit_code=None,
            now=now,
        )

    err_kind = None
    try:
        out, err_txt = proc.communicate(input=stdin_data, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        err_kind = "TIMEOUT"
        _kill_group(proc)
        out, err_txt = proc.communicate()
    finally:
        _kill_group(proc)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    exit_code = proc.returncode if err_kind is None else None

    if completion_path.exists():
        try:
            payload = json.loads(completion_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
    else:
        payload = {}
        if out.strip():
            try:
                payload = json.loads(out.strip().splitlines()[-1])
            except (json.JSONDecodeError, IndexError):
                payload = {"summary": out.strip()[:500]}

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
            evidence=[str(completion_path)] if completion_path.exists() else [],
            payload=payload,
            now=now,
            elapsed_ms=elapsed_ms,
        )

    if exit_code != 0 or err_txt.strip():
        failover.record_availability_from_dispatch(
            worker_id,
            exit_code=exit_code,
            stderr=err_txt or "",
            stdout=out or "",
            now=now,
        )

    verdict = str(payload.get("verdict") or payload.get("status") or "").upper()
    if exit_code != 0:
        status = "FAILED"
    elif item["kind"] == "review" and verdict == "FAIL":
        status = "FAILED"
    elif item["kind"] == "review" and verdict not in ("PASS", "OK", "SUCCESS", ""):
        if verdict:
            status = "FAILED"
        else:
            status = "COMPLETED"
    else:
        status = "COMPLETED"

    summary = str(payload.get("summary") or payload.get("result") or out[:500] or "ok")
    return _finish_dispatch(
        items[item_id],
        worker_id,
        status=status,
        summary=summary,
        exceptions=[err_txt.strip()] if err_txt.strip() and status == "FAILED" else [],
        exit_code=exit_code,
        evidence=[str(completion_path)] if completion_path.exists() else [],
        payload=payload,
        now=now,
        elapsed_ms=elapsed_ms,
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
) -> dict[str, Any]:
    items = load_items()
    item = items.get(item["id"], item)
    before = dict(item)
    attempt = int(item.get("attempt") or 1)
    owner_action = str((payload or {}).get("owner_action_required") or item.get("owner_action_required") or "")

    cfg = load_config()
    worktree = str(cfg.get("worktree_cwd") or ".")
    try:
        argv = _worker_cmd(worker_id, cfg, item, worktree)
        cli = " ".join(argv[:4])
    except ValueError:
        cli = worker_id
    rec = completion_record(
        work_item_id=item["id"],
        status=status,
        result_summary=summary,
        evidence_paths=evidence or [],
        exceptions=exceptions,
        owner_action_required=owner_action,
        executed_by=f"{worker_id} {cli}",
        billing_class=_billing_class(worker_id),
    )
    json_path, md_path = write_completion(rec, attempt)
    rec["EVIDENCE_PATHS"] = list(rec["EVIDENCE_PATHS"]) + [str(json_path), str(md_path)]

    review_id = None
    if status == "COMPLETED" and item["kind"] == "build" and item.get("reviewer_gate"):
        review_id = f"{item['id']}-review"
        if review_id not in items:
            submit(
                {
                    "id": review_id,
                    "kind": "review",
                    "spec": {"parent": item["id"], "acceptance": item.get("acceptance")},
                    "acceptance": item.get("acceptance"),
                    "depends_on": [item["id"]],
                    "reviewer_gate": False,
                    "timeout_s": item.get("timeout_s"),
                    "max_attempts": 1,
                },
                now=now,
            )
            items = load_items()
            item["review_enqueued"] = review_id
        item["status"] = "AWAITING_REVIEW"
    parent_updates: dict[str, dict[str, Any]] = {}
    if status == "COMPLETED" and item["kind"] == "review":
        parent = (item.get("spec") or {}).get("parent")
        if parent and items.get(parent):
            parent_item = dict(items[parent])
            parent_item["status"] = "CLOSED"
            parent_item["updated_at"] = _now_iso(now)
            parent_updates[parent] = parent_item
        item["status"] = "CLOSED"
    elif status == "FAILED" and item["kind"] == "review":
        parent = (item.get("spec") or {}).get("parent")
        if parent and items.get(parent):
            parent_item = dict(items[parent])
            if int(parent_item.get("attempt") or 0) < int(parent_item.get("max_attempts") or 1):
                parent_item["status"] = "QUEUED"
                parent_item["updated_at"] = _now_iso(now)
                parent_updates[parent] = parent_item
        item["status"] = "FAILED"
    elif status in ("FAILED", "TIMED_OUT") and int(item.get("attempt") or 0) < int(item.get("max_attempts") or 1):
        item["status"] = "QUEUED"
    elif status == "COMPLETED":
        item["status"] = "CLOSED"
    else:
        item["status"] = status if status in TERMINAL_STATUSES else status

    item["updated_at"] = _now_iso(now)
    item["last_result"] = status
    latest = load_items()
    latest[item["id"]] = item
    for pid, prec in parent_updates.items():
        latest[pid] = prec
    save_items(latest)

    key = _lease_key(item["id"], attempt)
    leases = load_leases()
    leases.pop(key, None)
    save_leases(leases)

    audit_transition(item["id"], "complete", before, item, now=now, extra={"worker": worker_id, "exit_code": exit_code})
    terminal_fail = item["status"] in ("FAILED", "TIMED_OUT") and int(item.get("attempt") or 0) >= int(item.get("max_attempts") or 1)
    if owner_action:
        notify_owner(item["id"], owner_action, now=now)
    elif terminal_fail:
        notify_owner(item["id"], f"terminally failed: {status}", now=now)

    return {
        "ok": status == "COMPLETED",
        "status": status,
        "completion": rec,
        "review_enqueued": review_id,
        "elapsed_ms": elapsed_ms,
        "exit_code": exit_code,
    }


def run_once(*, worktree: str | None = None, now: datetime | str | None = None) -> dict[str, Any]:
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
        (iid for iid, it in items.items() if it.get("status") == "QUEUED"),
        key=lambda x: x,
    )
    seen = set(pending)
    while pending:
        item_id = pending.pop(0)
        items = load_items()
        item = items.get(item_id)
        if not item or item.get("status") != "QUEUED":
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


def run_until_idle(*, worktree: str | None = None, max_rounds: int = 50, now: datetime | str | None = None) -> dict[str, Any]:
    rounds: list[dict[str, Any]] = []
    for _ in range(max_rounds):
        out = run_once(worktree=worktree, now=now)
        rounds.append(out)
        if not out["processed"]:
            break
        if all(p.get("action") == "skipped" for p in out["processed"]):
            break
    items = load_items()
    pending = [i for i in items.values() if i.get("status") not in NON_PENDING_STATUSES]
    return {"rounds": len(rounds), "pending": len(pending), "items": items, "history": rounds}


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
