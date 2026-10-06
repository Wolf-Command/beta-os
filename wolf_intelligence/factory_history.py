"""Current-system worker from per-job factory history.

A job counts only when that job names its worker or carries an execution
marker (cursor_pid / cursor_log / cursor.pid, or the grok equivalents).
Aggregate counts and implied_primary_from_bf_cursor_launch are not jobs.
Jobs with no per-job worker stay out of the list. The hint is then UNKNOWN.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import BUILD_FACTORY_DIR, FACTORY_HISTORY_PATH

KNOWN_WORKERS = frozenset(
    {
        "grok_bot",
        "cursor",
        "peaches",
        "openai_chatgpt",
        "openai_api",
        "claude_sub",
        "anthropic_api",
        "gemini",
        "ollama",
    }
)

_MAX_FILES = 400
_MAX_BYTES = 1_000_000
_REGISTRY_NAMES = frozenset(
    {"factory-history-workers.json", "worker-registry.json", "work-store.json"}
)
_ALLOWED_LIST_EVIDENCE = frozenset(
    {
        "field:worker",
        "field:worker_id",
        "field:executor",
        "cursor_pid_or_cursor_log",
        "grok_pid_or_grok_log",
        "cursor.pid",
        "CURSOR.log",
        "grok.pid",
        "GROK.log",
    }
)


def worker_from_job(data: dict[str, Any]) -> tuple[str | None, str]:
    """Return (worker_id, evidence) for one job object, or (None, reason)."""
    if not isinstance(data, dict):
        return None, "not_an_object"
    for key in ("worker_id", "worker", "executor"):
        val = data.get(key)
        if isinstance(val, str) and val.strip() in KNOWN_WORKERS:
            return val.strip(), f"field:{key}"
    if _marker(data.get("cursor_pid")) or _marker(data.get("cursor_log")):
        return "cursor", "cursor_pid_or_cursor_log"
    if _marker(data.get("grok_pid")) or _marker(data.get("grok_log")):
        return "grok_bot", "grok_pid_or_grok_log"
    return None, "no_per_job_worker"


def _marker(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _stamp(data: dict[str, Any], path: Path) -> str:
    for key in ("updated_at", "at", "created_at"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    except OSError:
        return ""


def _records_from_document(path: Path, data: Any) -> tuple[list[dict[str, Any]], int]:
    """Parse one JSON document. Returns (records, skipped_job_count)."""
    records: list[dict[str, Any]] = []
    skipped = 0

    def take(obj: dict[str, Any], job_id: str) -> None:
        nonlocal skipped
        worker, evidence = worker_from_job(obj)
        if not worker:
            skipped += 1
            return
        records.append(
            {
                "worker": worker,
                "evidence": evidence,
                "job_id": job_id,
                "source": str(path),
                "source_path": str(path),
                "at": _stamp(obj, path),
            }
        )

    if isinstance(data, dict):
        rows = None
        for key in ("jobs", "per_job", "assignments"):
            if isinstance(data.get(key), list):
                rows = data[key]
                break
        if rows is not None and path.name in _REGISTRY_NAMES:
            for row in rows:
                if not isinstance(row, dict):
                    skipped += 1
                    continue
                evidence = row.get("evidence") or row.get("worker_evidence") or ""
                if not isinstance(evidence, str):
                    evidence = ""
                evidence = evidence.strip()
                worker, _found = worker_from_job(row)
                if not worker or evidence not in _ALLOWED_LIST_EVIDENCE:
                    skipped += 1
                    continue
                records.append(
                    {
                        "worker": worker,
                        "evidence": evidence,
                        "job_id": str(row.get("job_id") or row.get("run_id") or row.get("file") or ""),
                        "source": str(path),
                        "source_path": str(path),
                        "at": _stamp(row, path),
                    }
                )
            return records, skipped
        job_id = str(data.get("run_id") or data.get("job_id") or path.stem)
        if data.get("run_id") or data.get("job_id") or "cursor_pid" in data or "cursor_log" in data or "worker" in data or "worker_id" in data or "executor" in data or "grok_pid" in data or "grok_log" in data:
            take(data, job_id)
            return records, skipped
    if isinstance(data, list):
        for row in data:
            if isinstance(row, dict):
                take(row, str(row.get("run_id") or row.get("job_id") or path.stem))
            else:
                skipped += 1
    return records, skipped


def _dir_marker_record(directory: Path) -> dict[str, Any] | None:
    if (directory / "cursor.pid").is_file() or (directory / "CURSOR.log").is_file():
        evidence = "cursor.pid" if (directory / "cursor.pid").is_file() else "CURSOR.log"
        return {
            "worker": "cursor",
            "evidence": evidence,
            "job_id": directory.name,
            "source": str(directory),
            "source_path": str(directory),
            "at": _stamp({}, directory),
        }
    if (directory / "grok.pid").is_file() or (directory / "GROK.log").is_file():
        evidence = "grok.pid" if (directory / "grok.pid").is_file() else "GROK.log"
        return {
            "worker": "grok_bot",
            "evidence": evidence,
            "job_id": directory.name,
            "source": str(directory),
            "source_path": str(directory),
            "at": _stamp({}, directory),
        }
    return None


def _candidate_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    found: list[Path] = []
    try:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix == ".json" and (
                path.name.startswith("BF-")
                or path.parent.name in {"runs", "work-store", "jobs"}
                or path.name in {"worker-registry.json", "work-store.json"}
            ):
                found.append(path)
            if len(found) >= _MAX_FILES:
                break
    except OSError:
        return found
    return found


def _load_json(path: Path) -> Any | None:
    try:
        if path.stat().st_size > _MAX_BYTES:
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None


def collect_actual_workers(
    *,
    factory_root: Path | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Newest-first per-job workers. Empty result → last_worker_hint UNKNOWN."""
    root = factory_root if factory_root is not None else BUILD_FACTORY_DIR
    cfg = config_path if config_path is not None else FACTORY_HISTORY_PATH
    records: list[dict[str, Any]] = []
    skipped = 0

    for path in _candidate_files(root):
        data = _load_json(path)
        if data is None:
            continue
        got, skip = _records_from_document(path, data)
        records.extend(got)
        skipped += skip

    runs = root / "runs"
    if runs.is_dir():
        try:
            children = [p for p in runs.iterdir() if p.is_dir()]
        except OSError:
            children = []
        for directory in children:
            marker = _dir_marker_record(directory)
            if marker:
                records.append(marker)
            else:
                skipped += 1

    if cfg.is_file():
        data = _load_json(cfg)
        if data is not None:
            got, skip = _records_from_document(cfg, data)
            records.extend(got)
            skipped += skip

    records.sort(key=lambda row: row.get("at") or "", reverse=True)
    counts: dict[str, int] = {}
    for row in records:
        counts[row["worker"]] = counts.get(row["worker"], 0) + 1
    if records:
        hint = records[0]["worker"]
        source = records[0]["source_path"]
    else:
        hint = "UNKNOWN"
        source = "UNKNOWN"
    return {
        "jobs": records,
        "last_worker_hint": hint,
        "last_worker_hint_source": source,
        "last_worker_hint_sample_counts": counts,
        "skipped_without_worker": skipped,
        "hint_defaulted": False,
    }
