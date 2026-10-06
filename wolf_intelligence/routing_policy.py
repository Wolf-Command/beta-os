"""Per-task-class routing preferences learned from REAL benchmark evidence only.

* Only evidence_class=REAL bench_runs count; synthetic/dev history is excluded.
* Metered workers are never placed in a preference list.
* Confidence reflects sample size: with n=1 per (worker, task) everything is
  'low'. A preference is a starting point, not a universal winner claim.
* Ties within 0.05 quality are reported as ties; latency breaks only the order.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import real_evidence, worker_registry


def _confidence(n: int, margin: float) -> str:
    if n <= 1:
        return "low (n=1 per worker; margin %.2f)" % margin
    if n < 5:
        return "low-moderate (n=%d)" % n
    return "moderate (n=%d)" % n


def latest_runs() -> list[dict[str, Any]]:
    """Latest record per (run_id, worker, task_id): regrades supersede, harness-invalid runs drop out."""
    invalid = {r.get("dispatch_request_id") for r in real_evidence.read("bench_invalidations")}
    latest: dict[tuple, dict[str, Any]] = {}
    for r in real_evidence.read("bench_runs"):
        if r.get("dispatch_request_id") and r.get("dispatch_request_id") in invalid:
            continue
        latest[(r.get("run_id"), r.get("worker"), r.get("task_id") or r.get("task_class"))] = r
    return list(latest.values())


def learn() -> dict[str, Any]:
    runs = latest_runs()
    policy: dict[str, Any] = {"label": "DRAFT - NOT WIRED", "status": "DRAFT", "wired": False, "active": False,
                              "generated_at": real_evidence.now_wita(), "evidence_class": "REAL",
                              "source": "records/bench_runs.jsonl (REAL only)", "synthetic_history_used": False,
                              "metered_workers_excluded": sorted(w for w in worker_registry.WORKERS if worker_registry.is_metered(w)),
                              "fallback_to_metered": "NEVER", "task_classes": {}}
    for tc in worker_registry.TASK_CLASSES:
        per: dict[str, list[dict[str, Any]]] = {}
        for r in runs:
            if r.get("task_class") != tc or worker_registry.is_metered(r.get("worker", "")):
                continue
            per.setdefault(r["worker"], []).append(r)
        rows = []
        for w, rs in per.items():
            supported = [r for r in rs if r.get("completion") != "UNSUPPORTED"]
            if not supported:
                rows.append({"worker": w, "status": "UNSUPPORTED"})
                continue
            q = sum(float(r.get("quality_score") or 0) for r in supported) / len(supported)
            lat = [r.get("latency_ms") for r in supported if isinstance(r.get("latency_ms"), (int, float))]
            rows.append({"worker": w, "mean_quality": round(q, 3), "n": len(supported),
                         "median_latency_ms": sorted(lat)[len(lat) // 2] if lat else None,
                         "failure_modes": sorted({r.get("failure_mode") for r in supported if r.get("failure_mode")})})
        ranked = sorted([r for r in rows if "mean_quality" in r],
                        key=lambda r: (-r["mean_quality"], r["median_latency_ms"] or 9e12))
        entry: dict[str, Any] = {"ranking": ranked, "unsupported": [r["worker"] for r in rows if r.get("status") == "UNSUPPORTED"]}
        if ranked:
            top = ranked[0]
            ties = [r["worker"] for r in ranked if top["mean_quality"] - r["mean_quality"] <= 0.05]
            margin = top["mean_quality"] - (ranked[1]["mean_quality"] if len(ranked) > 1 else 0.0)
            entry.update({"preferred": ranked[0]["worker"] if len(ties) == 1 else None,
                          "tied_top": ties if len(ties) > 1 else [],
                          "fast_acceptable": [r["worker"] for r in ranked if r["mean_quality"] >= 0.8 and (r["median_latency_ms"] or 9e12) < 60000],
                          "confidence": _confidence(min(r["n"] for r in ranked), margin),
                          "order": [r["worker"] for r in ranked]})
        policy["task_classes"][tc] = entry
    return policy


def route(task_class: str, policy: dict[str, Any], registry: dict[str, Any]) -> list[str]:
    """Ordered candidate list: policy order filtered to routable, non-metered workers. Never metered."""
    order = (policy.get("task_classes", {}).get(task_class) or {}).get("order") or []
    workers = registry.get("workers", {})
    return [w for w in order if workers.get(w, {}).get("routable") and not worker_registry.is_metered(w)
            and (worker_registry.WORKERS.get(w) or {}).get("billing_status", "VERIFIED") != "UNVERIFIED"]


def write(path: Path | str) -> dict[str, Any]:
    pol = learn()
    Path(path).write_text(json.dumps(pol, indent=1) + "\n", encoding="utf-8")
    return pol
