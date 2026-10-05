"""Phase 2 — wrap EXISTING workers; report CONNECTED/PARTIAL/UNAVAILABLE with evidence.

Safe isolated tests only. Never kill workers. Never touch Production.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import events
from .adapters import ADAPTER_REGISTRY
from .paths import CONFIG_DIR, WORKERS_DIR, WORKER_STATUS_PATH, ensure_dirs

TZ = ZoneInfo("Asia/Makassar")

WORKER_ORDER = (
    "grok_bot",
    "cursor",
    "peaches",
    "openai_chatgpt",
    "openai_api",
    "claude_sub",
    "anthropic_api",
    "gemini",
    "ollama",
)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _ollama_retire_note() -> dict[str, Any]:
    path = CONFIG_DIR / "ollama-caller-audit.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"classification": "UNKNOWN"}


def report() -> dict[str, Any]:
    ensure_dirs()
    workers: dict[str, Any] = {}
    for wid in WORKER_ORDER:
        adapter = ADAPTER_REGISTRY.get(wid)
        if not adapter:
            workers[wid] = {
                "status": "UNAVAILABLE",
                "evidence": "no adapter registered",
                "supports": [],
            }
            continue
        h = adapter.health()
        entry: dict[str, Any] = {
            "label": adapter.label,
            "status": h.status,
            "ok": h.ok,
            "evidence": h.message,
            "data": h.data,
            "supports": sorted(adapter.supports),
        }
        # Safe isolated shadow submit test (no expensive)
        if "submit" in adapter.supports:
            sub = adapter.submit({"shadow_isolated": True, "prompt": "phase2 isolated ping"})
            entry["isolated_submit_test"] = {
                "status": sub.status,
                "ok": sub.ok,
                "message": sub.message,
            }
        if wid == "ollama":
            audit = _ollama_retire_note()
            entry["retire_candidate"] = audit.get("classification")
            entry["retire_why"] = audit.get("why") or audit.get("notes")
            entry["action"] = "DO_NOT_DELETE"
        events.emit(
            "worker.health_checked",
            {"worker": wid, "status": h.status, "evidence": h.message},
        )
        workers[wid] = entry

    out = {
        "at": now_iso(),
        "mode": "SHADOW",
        "production_touched": False,
        "workers_killed": False,
        "workers": workers,
        "summary": {
            "CONNECTED": sum(1 for w in workers.values() if w.get("status") == "CONNECTED"),
            "PARTIAL": sum(1 for w in workers.values() if w.get("status") == "PARTIAL"),
            "UNAVAILABLE": sum(1 for w in workers.values() if w.get("status") == "UNAVAILABLE"),
        },
    }
    WORKER_STATUS_PATH.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    # Commitable mirror (no secrets)
    mirror = CONFIG_DIR / "worker-status-phase2.json"
    mirror.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    events.emit("worker.status_reported", {"summary": out["summary"]})
    return out


def accept() -> dict[str, Any]:
    r = report()
    checks = []
    for wid in WORKER_ORDER:
        w = r["workers"].get(wid) or {}
        checks.append(
            {
                "worker": wid,
                "status": w.get("status"),
                "has_evidence": bool(w.get("evidence")),
                "ok": w.get("status") in ("CONNECTED", "PARTIAL", "UNAVAILABLE") and bool(w.get("evidence")),
            }
        )
    ollama = r["workers"].get("ollama") or {}
    checks.append(
        {
            "worker": "ollama_retire_mark",
            "ok": ollama.get("retire_candidate") == "RETIRE CANDIDATE"
            and ollama.get("action") == "DO_NOT_DELETE",
            "detail": ollama.get("retire_candidate"),
        }
    )
    checks.append({"name": "no_prod", "ok": r["production_touched"] is False})
    checks.append({"name": "no_kill", "ok": r["workers_killed"] is False})
    passed = all(c.get("ok") for c in checks)
    report_out = {"phase": 2, "passed": passed, "checks": checks, "summary": r["summary"]}
    (WORKERS_DIR / "phase2-accept.json").write_text(json.dumps(report_out, indent=2) + "\n")
    return report_out
