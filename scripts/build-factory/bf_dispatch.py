#!/usr/bin/env python3
"""Named-queue dispatcher for the build factory. Beta tooling only.

Matt is not the scheduler. On worker exit or idle, this module classifies the
result, releases the writer lock, and starts the next safe READY slice itself.

Credit conservation still blocks Tours/Events and other breadth. It does not
block the Owner 5 Oct 2026 06:24 WITA God Mode queue.

Does not kill a live cursor. Does not touch Production. staff_ready and
human_commissioned stay false. No commit, push, or merge.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os").resolve()
BF = ROOT / "state" / "build-factory"
RUNS = BF / "runs"
ACTIVE = BF / "ACTIVE"
QUEUE_PATH = BF / "GOD-MODE-DISPATCH.json"
AUDIT_PATH = BF / "DISPATCH-AUDIT.jsonl"
LOCK_PATH = BF / "WRITER.lock"
LAUNCH_SH = ROOT / "scripts" / "build-factory" / "bf_cursor_launch.sh"
BETA_CWD = "/Users/wolfterminal/beta-os"

# Dead pid, or a live pid whose watched files have not moved this long.
STALL_SECONDS = 45 * 60
# Hung checkpoints with no completion before the slice is BLOCKED.
HUNG_BLOCK_AFTER = 2
# Owner order 5 Oct 2026 19:01 WITA (overnight finance queue): a strict slice that
# ends BLOCKED gets exactly one automatic fix slice; if that also blocks, its chain
# stops and the next priority's chain head (no predecessor) is selected instead.
AUTOFIX_SUFFIX = "-AUTOFIX1"
# Never signalled, whatever happens (Owner hard rule).
NEVER_SIGNAL_PIDS = frozenset({1297, 2627})

STATE_READY = "READY"
STATE_RUNNING = "RUNNING"
STATE_BLOCKED = "BLOCKED"
STATE_HUMAN = "READY FOR HUMAN TEST"
STATE_DONE = "DONE"
TERMINAL = frozenset({STATE_BLOCKED, STATE_HUMAN, STATE_DONE})
PROGRESS = frozenset({STATE_HUMAN, STATE_DONE})

# Owner order, highest priority first. Finance was in flight; then purchasing.
NAMED_SEQUENCE = (
    "GGV-BILLS-605",
    "BZG-P2P-RECV-1",
    "BZG-P2P-NOTA-BILL-1",
    "BZG-P2P-THREE-WAY-1",
    "BZG-P2P-AP-1",
    "BZG-P2P-READY-TO-PAY-1",
    "OWNER-HOME-FACTORY-INDICATOR",
)

BREADTH_TOKENS = (
    "tour",
    "event",
    "operator-depth",
    "operator_depth",
    "management-depth",
    "management_depth",
    "connective",
    "atrium-ops-tours",
)

# Already built or explicitly not to be rebuilt. Not auto-armed.
REBUILD_BANNED = (
    "bzg-p2p-po-1",
    "purchase-orders",
    "purchase orders",
    "haryanto-recipe",
    "recipe-builder",
    "recipe builder",
    "daily-close",
    "daily close",
    "petty-cash",
    "petty cash",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    return True


def _audit(event: str, **fields: object) -> None:
    BF.mkdir(parents=True, exist_ok=True)
    payload = {"event": event, "at": now_iso(), "require_matt": False}
    for key, value in fields.items():
        if any(tok in key.lower() for tok in ("cmd", "command", "argv", "prompt")):
            continue
        payload[key] = value
    with AUDIT_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def default_queue() -> dict:
    """Seed. Later slices stay READY but are not selectable until the predecessor progresses."""
    items = [
        {
            "id": "GGV-BILLS-605",
            "priority": 1,
            "state": STATE_HUMAN,
            "title": "Finance GGV bills",
            "run_id": "BF-ad715c36d015",
            "cursor_log": "state/reliability/GGV-BILLS-605-CURSOR-2026-10-05.log",
            "predecessor": None,
            "auto_arm": False,
            "exempt_from_credit_veto": True,
            "staff_ready": False,
            "human_commissioned": False,
        },
        {
            "id": "BZG-P2P-RECV-1",
            "priority": 2,
            "state": STATE_RUNNING,
            "title": "purchasing Receiving",
            "run_id": "BF-50c02ad53714",
            "prompt": "state/reliability/BZG-P2P-RECV-1-PROMPT-2026-10-05.md",
            "cursor_log": "state/reliability/BZG-P2P-RECV-1-CURSOR-2026-10-05.log",
            "predecessor": "GGV-BILLS-605",
            "auto_arm": True,
            "exempt_from_credit_veto": True,
            "staff_ready": False,
            "human_commissioned": False,
            "hung_checkpoints": 0,
        },
        {
            "id": "BZG-P2P-NOTA-BILL-1",
            "priority": 3,
            "state": STATE_READY,
            "title": "purchasing Nota/Bill",
            "predecessor": "BZG-P2P-RECV-1",
            "auto_arm": True,
            "exempt_from_credit_veto": True,
            "staff_ready": False,
            "human_commissioned": False,
        },
        {
            "id": "BZG-P2P-THREE-WAY-1",
            "priority": 4,
            "state": STATE_READY,
            "title": "purchasing Three-way Match",
            "predecessor": "BZG-P2P-NOTA-BILL-1",
            "auto_arm": True,
            "exempt_from_credit_veto": True,
            "staff_ready": False,
            "human_commissioned": False,
        },
        {
            "id": "BZG-P2P-AP-1",
            "priority": 5,
            "state": STATE_READY,
            "title": "purchasing AP",
            "predecessor": "BZG-P2P-THREE-WAY-1",
            "auto_arm": True,
            "exempt_from_credit_veto": True,
            "staff_ready": False,
            "human_commissioned": False,
        },
        {
            "id": "BZG-P2P-READY-TO-PAY-1",
            "priority": 6,
            "state": STATE_READY,
            "title": "purchasing Ready to Pay",
            "predecessor": "BZG-P2P-AP-1",
            "auto_arm": True,
            "exempt_from_credit_veto": True,
            "staff_ready": False,
            "human_commissioned": False,
        },
        {
            "id": "OWNER-HOME-FACTORY-INDICATOR",
            "priority": 7,
            "state": STATE_READY,
            "title": "Owner Home factory indicator",
            "predecessor": "BZG-P2P-READY-TO-PAY-1",
            "auto_arm": True,
            "exempt_from_credit_veto": True,
            "staff_ready": False,
            "human_commissioned": False,
        },
    ]
    return {
        "owner_order": "2026-10-05T06:24:00+08:00",
        "owner_order_note": (
            "God Mode queue supersedes credit conservation for these ids only. "
            "Tours/Events and other breadth stay vetoed. Do not rebuild Purchase Orders, "
            "Recipe Builder, Daily Close, or Petty Cash."
        ),
        "staff_ready": False,
        "human_commissioned": False,
        "last_completion_at": "2026-10-04T22:31:00Z",
        "last_autonomous_dispatch_at": None,
        "items": items,
        "blocked_breadth": [
            "ATRIUM-OPS-TOURS-CONCIERGE-1",
            "events",
            "operator-depth",
            "management-depth",
            "connective",
        ],
        "do_not_rebuild": [
            "BZG-P2P-PO-1",
            "HARYANTO-RECIPE-FINISH",
            "Daily Close",
            "Petty Cash",
        ],
    }


def load_queue() -> dict:
    data = _read_json(QUEUE_PATH)
    if not data or not isinstance(data.get("items"), list):
        data = default_queue()
    data["staff_ready"] = False
    data["human_commissioned"] = False
    return data


def save_queue(data: dict) -> None:
    data["staff_ready"] = False
    data["human_commissioned"] = False
    data["updated_at"] = now_iso()
    _write_json(QUEUE_PATH, data)


def item_by_id(queue: dict, item_id: str | None) -> dict | None:
    if not item_id:
        return None
    for item in queue.get("items") or []:
        if item.get("id") == item_id:
            return item
    return None


def hint_is_breadth(hint: str | None) -> bool:
    h = (hint or "").lower().replace("_", "-")
    if not h:
        return False
    return any(tok.replace("_", "-") in h for tok in BREADTH_TOKENS)


def hint_is_rebuild(hint: str | None) -> bool:
    h = (hint or "").lower().replace("_", "-")
    if not h:
        return False
    return any(tok.replace("_", "-") in h for tok in REBUILD_BANNED)


def hint_is_named_exempt(hint: str | None, queue: dict | None = None) -> bool:
    h = (hint or "").lower().replace("_", "-")
    if not h or hint_is_breadth(h) or hint_is_rebuild(h):
        return False
    ids = [s.lower() for s in NAMED_SEQUENCE]
    if queue:
        for item in queue.get("items") or []:
            if item.get("exempt_from_credit_veto") and item.get("id"):
                ids.append(str(item["id"]).lower())
    return any(item_id in h or h in item_id for item_id in ids)


def named_ready(queue: dict | None = None) -> bool:
    queue = queue if queue is not None else load_queue()
    return select_next(queue) is not None


def _predecessor_clear(queue: dict, item: dict) -> bool:
    pred = item.get("predecessor")
    if not pred:
        return True
    prev = item_by_id(queue, pred)
    if not prev:
        return False
    if prev.get("state") in PROGRESS:
        return True
    # Predecessor blocked but its single auto-fix slice finished: chain may continue.
    if prev.get("state") == STATE_BLOCKED and prev.get("fixed_by"):
        fix = item_by_id(queue, prev.get("fixed_by"))
        return bool(fix and fix.get("state") in PROGRESS)
    return False


def select_next(queue: dict) -> dict | None:
    ready = []
    for item in queue.get("items") or []:
        if item.get("state") != STATE_READY:
            continue
        if item.get("auto_arm") is False:
            continue
        if item.get("breadth") or hint_is_breadth(item.get("id")) or hint_is_breadth(item.get("title")):
            continue
        if item.get("rebuild") or hint_is_rebuild(item.get("id")) or hint_is_rebuild(item.get("title")):
            continue
        if not _predecessor_clear(queue, item):
            continue
        ready.append(item)
    ready.sort(key=lambda it: int(it.get("priority") or 999))
    return ready[0] if ready else None


def _log_text(item_or_run: dict) -> str:
    rel = item_or_run.get("cursor_log") or item_or_run.get("child_log")
    if not rel:
        return ""
    path = Path(rel)
    if not path.is_absolute():
        path = ROOT / rel
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def classify_text(text: str, exit_code: int | None) -> str | None:
    """Return a terminal state, or None when the slice did not finish."""
    if exit_code == 0 or "CURSOR_DONE" in text:
        return STATE_HUMAN
    if re.search(r"\d+\s+pass,\s+0\s+fail", text, re.I):
        return STATE_HUMAN
    if "EXITED_IMPLEMENTATION_DONE" in text or "IMPLEMENTATION_DONE" in text:
        return STATE_HUMAN
    if exit_code not in (None, 0):
        return STATE_BLOCKED
    return None


def _exit_code_from_log(text: str) -> int | None:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("EXIT:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def _watched_mtime(item: dict) -> float | None:
    paths = []
    for key in ("cursor_log", "prompt"):
        rel = item.get(key)
        if rel:
            path = Path(rel)
            if not path.is_absolute():
                path = ROOT / rel
            paths.append(path)
    run_id = item.get("run_id")
    if run_id:
        paths.append(RUNS / f"{run_id}.json")
    mtimes = []
    for path in paths:
        if path.exists():
            try:
                mtimes.append(path.stat().st_mtime)
            except OSError:
                continue
    return max(mtimes) if mtimes else None


def live_beta_cursor_pids() -> list[int]:
    """cursor-agent processes whose cwd is the beta-os workspace. No command lines."""
    try:
        listing = subprocess.check_output(["ps", "-ax", "-o", "pid=,comm="], text=True)
    except (OSError, subprocess.CalledProcessError):
        return []
    found: list[int] = []
    for line in listing.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) < 2:
            continue
        pid_s, comm = parts
        base = os.path.basename(comm).lower()
        if base != "cursor-agent" and "cursor-agent" not in base:
            continue
        try:
            pid = int(pid_s)
        except ValueError:
            continue
        cwd = _pid_cwd(pid)
        if cwd == BETA_CWD or cwd.startswith(BETA_CWD + "/"):
            found.append(pid)
    return found


def _pid_cwd(pid: int) -> str:
    try:
        raw = subprocess.check_output(
            ["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    for line in raw.splitlines():
        if line.startswith("n"):
            return line[1:].rstrip("/")
    return ""


def _load_lock() -> dict | None:
    return _read_json(LOCK_PATH)


def release_lock(reason: str) -> None:
    lock = _load_lock() or {}
    if LOCK_PATH.exists():
        try:
            LOCK_PATH.unlink()
        except OSError:
            pass
    _audit("WRITER_LOCK_RELEASED", reason=reason, run_id=lock.get("run_id"), slice=lock.get("slice"))


def _write_lock(payload: dict) -> None:
    payload["cwd"] = BETA_CWD
    payload["staff_ready"] = False
    payload["human_commissioned"] = False
    _write_json(LOCK_PATH, payload)


def lock_holder_alive(lock: dict | None = None) -> bool:
    lock = _load_lock() if lock is None else lock
    if not lock:
        return False
    for key in ("cursor_pid", "wrapper_pid"):
        pid = lock.get(key)
        if pid and pid_alive(int(pid)):
            cwd = _pid_cwd(int(pid)) if key == "cursor_pid" else ""
            if key == "wrapper_pid":
                return True
            if not cwd or cwd == BETA_CWD or cwd.startswith(BETA_CWD + "/"):
                return True
    return False


def _save_run_state(run_id: str, **fields: object) -> None:
    path = RUNS / f"{run_id}.json"
    data = _read_json(path) or {"run_id": run_id, "findings": [], "fix_attempts": 0}
    for key, value in fields.items():
        data[key] = value
    data["staff_ready"] = False
    data["human_commissioned"] = False
    data["updated_at"] = now_iso()
    _write_json(path, data)


def _clear_active_if(run_id: str | None) -> None:
    if not run_id or not ACTIVE.exists():
        return
    if ACTIVE.read_text(encoding="utf-8").strip() == run_id:
        ACTIVE.unlink()


BETA_RULES_TAG = "BETA-RESTART-RULE-v2"
BETA_RULES_PREAMBLE = (
    "# " + BETA_RULES_TAG + " (factory hard rule, Owner P0 5 Oct 2026 20:00 WITA)\n"
    "- NEVER restart, kill or kickstart Beta (:8788) yourself and NEVER add a Beta restart to a test, "
    "migration or helper. launchd owns Beta restarts. Tests run in-process.\n"
    "- The ONLY reload path is ONE call at the very end: `python3 scripts/beta_restart.py --reason <slice>` "
    "(it runs the reload gate; RELOAD_HELD is a normal answer: record reload_held=true and finish).\n"
    "- Do not re-run old slices' test files that write RESULT JSONs or restart Beta; if you must run a regression, "
    "run it with BF_IN_TEST=1.\n"
    "- You do NOT decide READY FOR HUMAN TEST. The factory ready gate does (build, deploy, healthy service, public "
    "route, rendered workflow test, 3-minute stability). If you ran a rendered (browser) workflow test, record "
    "`rendered_workflow_test: {\"pass\": true, \"steps\": [...], \"shots\": [...]}` in your result JSON.\n\n"
)


def _ready_gate():
    try:
        import bf_ready_gate as rg  # noqa: WPS433
        return rg
    except Exception:  # noqa: BLE001
        return None


def _notify(kind: str, **fields: object) -> None:
    rg = _ready_gate()
    if rg is None:
        return
    try:
        rg.notify(kind, **fields)
    except Exception:  # noqa: BLE001
        pass


def _apply_terminal(queue: dict, item: dict, state: str, reason: str) -> None:
    item["state"] = state
    item["classified_at"] = now_iso()
    item["classify_reason"] = reason
    item["staff_ready"] = False
    item["human_commissioned"] = False
    if state in PROGRESS:
        queue["last_completion_at"] = now_iso()
    run_id = item.get("run_id")
    if run_id:
        stage = "DONE" if state in PROGRESS else "BLOCKED"
        _save_run_state(
            run_id,
            stage=stage,
            final_state=state,
            status=state,
            ready_for_human_test=state == STATE_HUMAN,
            blocker=None if state in PROGRESS else reason,
        )
        _clear_active_if(run_id)
    release_lock(reason)
    if state == STATE_BLOCKED:
        fix = _maybe_arm_autofix(queue, item, reason)
        if not fix:
            _notify("FAIL_NO_SELF_REPAIR", slice=item.get("id"), run_id=run_id, reason=reason,
                    fix_of=item.get("fix_of"))


def _checkpoint_hung(queue: dict, item: dict, reason: str) -> None:
    """Dead or stalled-dead writer must not hold the factory. Do not kill a live pid."""
    count = int(item.get("hung_checkpoints") or 0) + 1
    item["hung_checkpoints"] = count
    item["checkpoint_at"] = now_iso()
    item["checkpoint_reason"] = reason
    run_id = item.get("run_id")
    if run_id:
        _save_run_state(
            run_id,
            stage="WAITING_CURSOR",
            checkpoint_reason=reason,
            hung_checkpoints=count,
            final_state=None,
        )
        _clear_active_if(run_id)
    release_lock(reason)
    if count >= HUNG_BLOCK_AFTER:
        item["state"] = STATE_BLOCKED
        item["block_reason"] = reason
        if run_id:
            _save_run_state(run_id, stage="BLOCKED", final_state=STATE_BLOCKED, blocker=reason)
        _maybe_arm_autofix(queue, item, reason)
        _notify("STUCK_RECOVERY_FAILED", slice=item.get("id"), run_id=run_id, reason=reason,
                hung_checkpoints=count)
    else:
        item["state"] = STATE_READY
        item["auto_arm"] = True
    _audit(
        "FACTORY_HUNG_CHECKPOINT",
        slice=item.get("id"),
        run_id=run_id,
        reason=reason,
        hung_checkpoints=count,
        state=item.get("state"),
    )


def _strict_result_state(item: dict) -> tuple[str, str]:
    """For strict_result slices: the slice's own RESULT JSON decides, not CURSOR_DONE."""
    rel = item.get("result_json")
    if not rel:
        return STATE_BLOCKED, "strict_result_without_result_json"
    path = Path(rel)
    if not path.is_absolute():
        path = ROOT / rel
    data = _read_json(path)
    if data is None:
        return STATE_BLOCKED, "result_json_missing_or_invalid"
    status = str(data.get("status") or "").upper()
    try:
        fails = int(data.get("tests_fail") or 0)
    except (TypeError, ValueError):
        fails = 1
    if status in ("BLOCKED", "FAILED", "FAIL", "ERROR") or "BLOCKED" in status:
        return STATE_BLOCKED, "result_status_" + (status or "empty")
    if fails > 0:
        return STATE_BLOCKED, f"result_tests_fail_{fails}"
    if data.get("staff_ready") or data.get("human_commissioned"):
        return STATE_BLOCKED, "result_claimed_commissioned"
    return STATE_HUMAN, "result_ok"


def _maybe_arm_autofix(queue: dict, item: dict, reason: str) -> str | None:
    """Append one READY fix slice for a blocked strict slice. Idempotent. Returns fix id."""
    if not item.get("auto_fix_once") or item.get("fix_of") or item.get("fixed_by"):
        return None
    base = str(item.get("id") or "")
    fix_id = base + AUTOFIX_SUFFIX
    if item_by_id(queue, fix_id):
        item["fixed_by"] = fix_id
        return fix_id
    orig_rel = item.get("prompt") or ""
    orig_path = ROOT / orig_rel if orig_rel else None
    try:
        orig_text = orig_path.read_text(encoding="utf-8") if orig_path and orig_path.exists() else ""
    except OSError:
        orig_text = ""
    fix_prompt_rel = f"state/reliability/{fix_id}-PROMPT-2026-10-05.md"
    fix_result_rel = f"state/reliability/{fix_id}-RESULT-2026-10-05.json"
    fix_log_rel = f"state/reliability/{fix_id}-CURSOR-2026-10-05.log"
    preamble = (
        f"# {fix_id} — ONE automatic fix attempt for {base}\n\n"
        f"The slice {base} ended BLOCKED (reason: {reason}). You get exactly one attempt to finish it.\n"
        f"Read first: its result JSON `{item.get('result_json')}` (may be missing), its cursor log "
        f"`{item.get('cursor_log')}` (read the tail; do not print process command lines), and `git status`/`git diff` "
        f"for files it touched (read-only; do NOT commit, stash, reset, or clean).\n"
        f"Fix the failing tests / missing pieces so the ORIGINAL scope below is met — no new scope. "
        f"If it cannot be finished safely in this run, set status BLOCKED with the exact blocker; the factory then moves on.\n"
        f"Write YOUR result to `{fix_result_rel}` (same fields as the original asks; pack={fix_id}, fix_of={base}). "
        f"Do not edit or delete the original's result file. Final line: `RESULT_JSON: {fix_result_rel}`.\n\n"
        f"---\nORIGINAL SLICE PROMPT (all hard rules apply in full; where it names its own RESULT path, use `{fix_result_rel}` instead):\n\n"
    )
    try:
        (ROOT / fix_prompt_rel).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / fix_prompt_rel).write_text(preamble + orig_text, encoding="utf-8")
    except OSError:
        return None
    fix = {
        "id": fix_id,
        "priority": item.get("priority"),
        "owner_priority": item.get("owner_priority"),
        "state": STATE_READY,
        "title": "Auto-fix: " + str(item.get("title") or base),
        "predecessor": None,
        "depends_on": [base],
        "fix_of": base,
        "auto_arm": True,
        "auto_fix_once": False,
        "strict_result": True,
        "exempt_from_credit_veto": True,
        "staff_ready": False,
        "human_commissioned": False,
        "zayen_ready": False,
        "rebuild": False,
        "machine_solvable": True,
        "max_runtime_minutes": item.get("max_runtime_minutes"),
        "prompt": fix_prompt_rel,
        "cursor_log": fix_log_rel,
        "result_json": fix_result_rel,
        "armed_by": "bf_dispatch_autofix",
        "armed_at": now_iso(),
    }
    items = queue.setdefault("items", [])
    try:
        idx = items.index(item) + 1
    except ValueError:
        idx = len(items)
    items.insert(idx, fix)
    item["fixed_by"] = fix_id
    _audit("FACTORY_AUTOFIX_ARMED", slice=base, fix_slice=fix_id, reason=reason)
    return fix_id


def _maybe_timeout(item: dict) -> str | None:
    """SIGTERM only this slice's own factory cursor after max_runtime_minutes. Never 1297/2627."""
    limit = item.get("max_runtime_minutes")
    started = item.get("dispatched_at")
    pid = item.get("cursor_pid")
    if not limit or not started or not pid or item.get("timeout_terminated_at"):
        return None
    try:
        t0 = datetime.strptime(started, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    if (datetime.now(timezone.utc) - t0).total_seconds() < float(limit) * 60:
        return None
    pid = int(pid)
    if pid in NEVER_SIGNAL_PIDS or not pid_alive(pid):
        return None
    cwd = _pid_cwd(pid)
    if cwd != BETA_CWD and not cwd.startswith(BETA_CWD + "/"):
        return None
    import signal
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return None
    item["timeout_terminated_at"] = now_iso()
    _audit("FACTORY_SLICE_TIMEOUT_SIGTERM", slice=item.get("id"), run_id=item.get("run_id"),
           cursor_pid=pid, max_runtime_minutes=limit)
    return f"timeout_sigterm:{item.get('id')}"


def reconcile_running(queue: dict) -> list[str]:
    """Classify exited workers and checkpoint dead RUNNING rows. Never signals a live pid."""
    notes: list[str] = []
    live = set(live_beta_cursor_pids())
    for item in queue.get("items") or []:
        if item.get("state") != STATE_RUNNING:
            continue
        pid = item.get("cursor_pid")
        wrapper = item.get("wrapper_pid")
        if wrapper and pid_alive(int(wrapper)):
            notes_alive = True
        else:
            notes_alive = False
        alive = False
        if pid and pid_alive(int(pid)):
            cwd = _pid_cwd(int(pid))
            # Alive pid whose cwd is elsewhere is pid reuse, not our writer.
            if not cwd or cwd == BETA_CWD or cwd.startswith(BETA_CWD + "/"):
                alive = True
        if notes_alive:
            alive = True
        if alive:
            tnote = _maybe_timeout(item)
            if tnote:
                notes.append(tnote)
            mtime = _watched_mtime(item)
            if mtime is not None and (time.time() - mtime) >= STALL_SECONDS:
                item["stall_observed"] = True
                item["stall_observed_at"] = now_iso()
                notes.append(f"stall_live_not_killed:{item.get('id')}")
            continue
        text = _log_text(item)
        exit_code = _exit_code_from_log(text)
        klass = classify_text(text, exit_code)
        reason = None
        if klass and item.get("strict_result"):
            klass, why = _strict_result_state(item)
            reason = "worker_exit_" + klass.replace(" ", "_") + ":" + why
        if klass == STATE_HUMAN:
            # Owner P0 5 Oct 20:00: the slice does not decide READY. DONE (progress, never blocks
            # independent work) until bf_ready_gate proves build/deploy/service/public/rendered/stability.
            rg = _ready_gate()
            if rg is not None:
                klass = STATE_DONE
                reason = (reason or "worker_exit_clean") + "|ready_gate_pending"
                item["ready_gate"] = "PENDING"
                item["ready_gate_began_at"] = now_iso()
                try:
                    rg.begin(item)
                except Exception as exc:  # noqa: BLE001
                    item["ready_gate"] = "ERROR"
                    item["ready_gate_error"] = exc.__class__.__name__
        if klass:
            _apply_terminal(queue, item, klass, reason or ("worker_exit_" + klass.replace(" ", "_")))
            notes.append(f"classified:{item.get('id')}:{klass}")
            _audit(
                "FACTORY_WORKER_EXIT",
                slice=item.get("id"),
                run_id=item.get("run_id"),
                state=klass,
                exit_code=exit_code,
            )
        else:
            _checkpoint_hung(queue, item, "running_dead_pid")
            notes.append(f"checkpoint:{item.get('id')}")
    return notes


def _note_conservation(queue: dict, launched_id: str | None) -> None:
    path = BF / "CREDIT-CONSERVATION.json"
    data = _read_json(path)
    if not data:
        return
    if data.get("veto_scope") == "BREADTH_ONLY_NAMED_QUEUE_EXEMPT" and not launched_id:
        return
    data["named_god_mode_queue"] = {
        "ordered_at": "2026-10-05T06:24:00+08:00",
        "supersedes_veto_for_named_queue_only": True,
        "sequence": list(NAMED_SEQUENCE),
        "veto_still_blocks": [
            "tours",
            "events",
            "operator-depth",
            "management-depth",
            "connective",
            "rebuild purchase orders",
            "recipe builder",
            "daily close",
            "petty cash",
        ],
    }
    data["veto_scope"] = "BREADTH_ONLY_NAMED_QUEUE_EXEMPT"
    ship = data.get("ship_queue")
    if isinstance(ship, dict) and launched_id:
        ship["next_pack"] = launched_id
        ship["next_pack_launched"] = True
        ship["hold_reason"] = None
    # Never commission from the dispatcher.
    if "staff_ready" in data:
        data["staff_ready"] = False
    if "human_commissioned" in data:
        data["human_commissioned"] = False
    data["updated_at"] = now_iso()
    _write_json(path, data)


def _mint_run_id() -> str:
    import uuid
    return "BF-" + uuid.uuid4().hex[:12]


def start_item(queue: dict, item: dict) -> dict:
    """Start one slice. Caller must have proved no live beta-os cursor."""
    if live_beta_cursor_pids() or lock_holder_alive():
        return {"started": False, "reason": "live_writer_appeared"}
    prompt = item.get("prompt")
    if not prompt or not (ROOT / prompt).exists():
        return {"started": False, "reason": "prompt_missing", "slice": item.get("id")}
    if not LAUNCH_SH.exists():
        return {"started": False, "reason": "launcher_missing", "slice": item.get("id")}

    run_id = item.get("run_id") or _mint_run_id()
    item["run_id"] = run_id
    launch_prompt = ROOT / prompt
    try:
        ptxt = launch_prompt.read_text(encoding="utf-8")
        if BETA_RULES_TAG not in ptxt:
            pdir = BF / "prompts"
            pdir.mkdir(parents=True, exist_ok=True)
            launch_prompt = pdir / f"{run_id}-{item['id']}.md"
            launch_prompt.write_text(BETA_RULES_PREAMBLE + ptxt, encoding="utf-8")
    except OSError:
        launch_prompt = ROOT / prompt
    log_rel = item.get("cursor_log") or f"state/build-factory/logs/{item['id']}-cursor.log"
    item["cursor_log"] = log_rel
    log_path = ROOT / log_rel
    pidfile = BF / "logs" / f"{run_id}.cursor.pid"
    pidfile.parent.mkdir(parents=True, exist_ok=True)
    if pidfile.exists():
        pidfile.unlink()

    _write_lock(
        {
            "state": "starting",
            "slice": item["id"],
            "run_id": run_id,
            "acquired_at": now_iso(),
        }
    )
    try:
        wrapper = subprocess.Popen(
            [str(LAUNCH_SH), str(log_path), str(launch_prompt), str(pidfile)],
            cwd=str(ROOT),
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        release_lock("launch_oserror")
        return {"started": False, "reason": "launch_failed", "detail": exc.errno}

    _write_lock(
        {
            "state": "RUNNING",
            "slice": item["id"],
            "run_id": run_id,
            "wrapper_pid": wrapper.pid,
            "acquired_at": now_iso(),
        }
    )
    cursor_pid = None
    deadline = time.time() + 8
    while time.time() < deadline:
        if pidfile.exists():
            raw = pidfile.read_text(encoding="utf-8").strip()
            if raw.isdigit() and pid_alive(int(raw)):
                cursor_pid = int(raw)
                break
        if wrapper.poll() is not None:
            break
        time.sleep(0.2)

    item["state"] = STATE_RUNNING
    item["cursor_pid"] = cursor_pid
    item["wrapper_pid"] = wrapper.pid
    item["dispatched_at"] = now_iso()
    item["staff_ready"] = False
    item["human_commissioned"] = False
    queue["last_autonomous_dispatch_at"] = now_iso()
    _save_run_state(
        run_id,
        slice=item["id"],
        stage="WAITING_CURSOR",
        approved_scope=item.get("title"),
        grok_plan_ref=prompt,
        cursor_log=log_rel,
        cursor_pid=cursor_pid,
        wrapper_pid=wrapper.pid,
        final_state=None,
        blocker=None,
    )
    ACTIVE.write_text(run_id + "\n", encoding="utf-8")
    _write_lock(
        {
            "state": "RUNNING",
            "slice": item["id"],
            "run_id": run_id,
            "wrapper_pid": wrapper.pid,
            "cursor_pid": cursor_pid,
            "acquired_at": now_iso(),
        }
    )
    _audit(
        "FACTORY_DISPATCH",
        slice=item["id"],
        run_id=run_id,
        cursor_pid=cursor_pid,
        wrapper_pid=wrapper.pid,
    )
    return {
        "started": True,
        "slice": item["id"],
        "run_id": run_id,
        "cursor_pid": cursor_pid,
        "wrapper_pid": wrapper.pid,
    }


def supervisor_dispatch(*, dry_run: bool = False) -> dict:
    """One dispatch decision. Starts at most one slice when no live beta-os cursor."""
    queue = load_queue()
    gate_notes: list[str] = []
    if not dry_run:
        rg = _ready_gate()
        if rg is not None:
            gate_notes = rg.tick(queue)
            if gate_notes:
                save_queue(queue)
                _audit("FACTORY_READY_GATE_TICK", notes=gate_notes)
    live = live_beta_cursor_pids()
    lock = _load_lock()
    if live or lock_holder_alive(lock):
        adopted = None
        if not dry_run and len(live) == 1:
            running = [it for it in (queue.get("items") or []) if it.get("state") == STATE_RUNNING]
            # Prefer the ACTIVE run; never attach a live pid to a second slice.
            active_id = ACTIVE.read_text(encoding="utf-8").strip() if ACTIVE.exists() else ""
            target = None
            for it in running:
                if it.get("run_id") and it.get("run_id") == active_id:
                    target = it
                    break
            if target is None and len(running) == 1:
                target = running[0]
            if target is not None and not (
                target.get("cursor_pid") and pid_alive(int(target["cursor_pid"]))
            ):
                target["cursor_pid"] = live[0]
                target["staff_ready"] = False
                target["human_commissioned"] = False
                if target.get("run_id"):
                    _save_run_state(
                        target["run_id"],
                        slice=target.get("id"),
                        stage="WAITING_CURSOR",
                        cursor_pid=live[0],
                        cursor_log=target.get("cursor_log"),
                        final_state=None,
                    )
                    ACTIVE.write_text(target["run_id"] + "\n", encoding="utf-8")
                _write_lock(
                    {
                        "state": "RUNNING",
                        "slice": target.get("id"),
                        "run_id": target.get("run_id"),
                        "cursor_pid": live[0],
                        "acquired_at": now_iso(),
                        "adopted": True,
                    }
                )
                adopted = target.get("id")
            for it in queue.get("items") or []:
                if it.get("state") in PROGRESS and it.get("run_id"):
                    _save_run_state(
                        it["run_id"],
                        slice=it.get("id"),
                        stage="DONE",
                        final_state=it.get("state"),
                        status=it.get("state"),
                        ready_for_human_test=it.get("state") == STATE_HUMAN,
                    )
        out = {
            "handled": True,
            "action": "WAIT",
            "reason": "live_beta_cursor" if live else "writer_lock_alive",
            "active": True,
            "wake_parent": False,
            "stopped": False,
            "require_matt": False,
            "live_cursor_pids": live,
            "run_id": (lock or {}).get("run_id"),
            "slice": (lock or {}).get("slice") or adopted,
            "adopted_slice": adopted,
            "ready_gate_notes": gate_notes,
        }
        if not dry_run:
            save_queue(queue)
            _note_conservation(queue, None)
        return out

    notes = reconcile_running(queue) if not dry_run else []
    if dry_run:
        # Report what would be classified without writing.
        for item in queue.get("items") or []:
            if item.get("state") == STATE_RUNNING:
                pid = item.get("cursor_pid")
                if not (pid and pid_alive(int(pid))):
                    notes.append(f"would_release:{item.get('id')}")

    nxt = select_next(queue)
    if not nxt:
        if not dry_run:
            save_queue(queue)
        active = ACTIVE.exists() and bool(ACTIVE.read_text(encoding="utf-8").strip())
        return {
            "handled": False if not notes else True,
            "action": "IDLE",
            "reason": "no_ready_named_slice",
            "active": active,
            "wake_parent": False,
            "stopped": True,
            "require_matt": False,
            "notes": notes,
            "last_completion_at": queue.get("last_completion_at"),
            "last_autonomous_dispatch_at": queue.get("last_autonomous_dispatch_at"),
        }

    # No live cursor and READY work exists: idle recovery, even if a dead run was just released.
    recovery = {
        "handled": True,
        "action": "DISPATCH",
        "reason": "FACTORY_IDLE_RECOVERY" if not notes else "worker_exit_then_dispatch",
        "wake_parent": False,
        "stopped": False,
        "require_matt": False,
        "next_slice": nxt.get("id"),
        "notes": notes,
        "staff_ready": False,
        "human_commissioned": False,
    }
    if dry_run:
        recovery["dry_run"] = True
        recovery["started"] = False
        return recovery

    _audit(
        "FACTORY_IDLE_RECOVERY",
        next_slice=nxt.get("id"),
        notes=notes,
        ready=True,
    )
    started = start_item(queue, nxt)
    recovery.update(started)
    recovery["active"] = bool(started.get("started"))
    recovery["run_id"] = started.get("run_id")
    recovery["slice"] = started.get("slice")
    recovery["cursor_pid"] = started.get("cursor_pid")
    if not started.get("started"):
        recovery["action"] = "HOLD"
        recovery["reason"] = started.get("reason")
        recovery["wake_parent"] = False
        recovery["stopped"] = False
    save_queue(queue)
    _note_conservation(queue, nxt.get("id") if started.get("started") else None)
    return recovery


def self_check() -> dict:
    """Pure checks. Does not launch a writer."""
    breadth = hint_is_breadth("ATRIUM-OPS-TOURS-CONCIERGE-1")
    rebuild = hint_is_rebuild("HARYANTO-RECIPE-FINISH")
    named = hint_is_named_exempt("BZG-P2P-RECV-1")
    finance = hint_is_named_exempt("GGV-BILLS-605")
    queue = default_queue()
    # Finance is human-ready, receiving is RUNNING in the seed; force READY to test select.
    recv = item_by_id(queue, "BZG-P2P-RECV-1")
    assert recv is not None
    recv["state"] = STATE_READY
    chosen = select_next(queue)
    tours = {
        "id": "ATRIUM-OPS-TOURS-CONCIERGE-1",
        "priority": 0,
        "state": STATE_READY,
        "title": "Tours",
        "auto_arm": True,
        "prompt": "state/reliability/BZG-P2P-RECV-1-PROMPT-2026-10-05.md",
        "predecessor": None,
    }
    queue["items"].insert(0, tours)
    not_tours = select_next(queue)
    ok = (
        breadth
        and rebuild
        and named
        and finance
        and chosen is not None
        and chosen["id"] == "BZG-P2P-RECV-1"
        and not_tours is not None
        and not_tours["id"] == "BZG-P2P-RECV-1"
        and classify_text("21 pass, 0 fail", None) == STATE_HUMAN
        and classify_text("BZG-P2P-RECV-1 start", None) is None
    )
    return {
        "ok": ok,
        "breadth_blocked": breadth,
        "rebuild_blocked": rebuild,
        "named_exempt": named,
        "finance_exempt": finance,
        "selected": None if not chosen else chosen["id"],
        "tours_not_selected": None if not not_tours else not_tours["id"],
    }


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        print(json.dumps(self_check(), indent=2))
        return 0 if self_check()["ok"] else 1
    dry = "--dry-run" in sys.argv
    print(json.dumps(supervisor_dispatch(dry_run=dry), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
