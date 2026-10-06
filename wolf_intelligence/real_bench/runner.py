"""Run the REAL benchmark pack through WI's dispatcher; grade; blind cross-review; record REAL evidence.

  WOLF_INTELLIGENCE_LIVE_SUBMIT=1 WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT=<root> WOLF_INTELLIGENCE_STATE_ROOT=<scratch> \
  python3 -m wolf_intelligence.real_bench.runner run --workers claude_pro_sub,codex_sub,cursor_sub,gemini_free,ollama_local
"""
from __future__ import annotations

import argparse
import json
import random
import string
import threading
import time
from pathlib import Path
from typing import Any, Callable

from .. import real_evidence, worker_registry
from ..real_dispatch import dispatch_real
from . import tasks_a as A
from . import tasks_b as B

TASKS: list[dict[str, Any]] = [
    {"id": "coding-service-charge-split", "task_class": "coding", "prompt": lambda: A.CODING_PROMPT, "grade": A.grade_coding},
    {"id": "debug-monthend-recon-tz", "task_class": "debugging", "prompt": lambda: A.DEBUG_PROMPT, "grade": A.grade_debugging},
    {"id": "security-flask-seeded", "task_class": "security", "prompt": lambda: A.SEC_PROMPT, "grade": A.grade_security},
    {"id": "finance-ggv-amg-bzg-recon", "task_class": "finance", "prompt": lambda: A.FIN_PROMPT, "grade": A.grade_finance},
    {"id": "ux-shift-close-flow", "task_class": "ux_product", "prompt": lambda: B.UX_PROMPT, "grade": None},
    {"id": "large-context-ops-pack", "task_class": "large_context", "prompt": B.large_context_prompt, "grade": B.grade_large_context},
    {"id": "vision-supplier-receipt", "task_class": "vision_document", "prompt": lambda: B.VISION_PROMPT, "grade": B.grade_vision, "vision": True},
    {"id": "extract-shift-report", "task_class": "structured_extraction", "prompt": lambda: B.EXTRACT_PROMPT, "grade": B.grade_extraction},
    {"id": "plan-pos-commissioning", "task_class": "reasoning_planning", "prompt": lambda: B.PLAN_PROMPT, "grade": B.grade_planning},
]
GRADER_VERSION = "1.1"  # 1.0 = first run; 1.1 fixes 3 grader/spec ambiguities (see REAL-WORKERS.md)
VISION_UNSUPPORTED = {"ollama_local": "installed model llama3.2:3b is text-only"}
REVIEWERS = ("claude_pro_sub", "codex_sub", "gemini_free")


def _receipt() -> str:
    p = real_evidence.root() / "bench" / "fixtures" / "receipt.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        B.make_receipt_png(p)
    return str(p)


def run_one(run_id: str, task: dict[str, Any], worker: str) -> dict[str, Any]:
    base = {"run_id": run_id, "task_id": task["id"], "task_class": task["task_class"], "worker": worker,
            "billing_class": worker_registry.WORKERS[worker]["billing_class"],
            "cost_class": worker_registry.WORKERS[worker]["cost_class"],
            "execution_path": worker_registry.WORKERS[worker]["execution_path"]}
    if task.get("vision") and worker in VISION_UNSUPPORTED:
        return real_evidence.append("bench_runs", {**base, "completion": "UNSUPPORTED", "quality_score": None,
                                                    "failure_mode": VISION_UNSUPPORTED[worker], "latency_ms": None})
    files = [_receipt()] if task.get("vision") else None
    prompt = task["prompt"]()
    r = dispatch_real(worker, prompt, purpose=f"benchmark:{run_id}", task_class=task["task_class"], files=files,
                      timeout_s=600 if task["task_class"] == "large_context" else 420,
                      extra={"num_ctx": 32768} if task["task_class"] == "large_context" else None)
    out = r.get("_output") or ""
    rec = {**base, "dispatch_request_id": r.get("request_id"), "latency_ms": r.get("latency_ms"),
           "model_observed": r.get("model_observed"), "status": r.get("status"), "limit_hit": r.get("limit_hit"),
           "raw_output_artifact": r.get("response_artifact")}
    if not r.get("ok"):
        rec.update({"completion": "FAILED", "quality_score": 0.0, "failure_mode": f"dispatch:{r.get('status')}",
                    "error_excerpt": r.get("error_excerpt") or r.get("message")})
        return real_evidence.append("bench_runs", rec)
    if task["grade"] is None:
        pre = B.grade_ux_precheck(out)
        rec.update({"completion": "COMPLETED", "quality_score": None, "pending_review": True, "precheck": pre,
                    "governance_compliance": pre["governance_ok"], "grading": "blind cross-worker rubric (pending)"})
        return real_evidence.append("bench_runs_pending", rec)
    g = task["grade"](out)
    rec.update({"completion": "COMPLETED", **g, "grading": "deterministic", "grader_version": GRADER_VERSION})
    return real_evidence.append("bench_runs", rec)


def run_matrix(run_id: str, workers: list[str], task_ids: list[str] | None = None) -> None:
    tasks = [t for t in TASKS if not task_ids or t["id"] in task_ids or t["task_class"] in task_ids]
    lock = threading.Lock()

    done = {(r.get("worker"), r.get("task_id")) for k in ("bench_runs", "bench_runs_pending")
            for r in real_evidence.read(k) if r.get("run_id") == run_id}

    def worker_loop(w: str) -> None:
        for t in tasks:
            if (w, t["id"]) in done:  # resume: never re-spend allowance on a recorded run
                continue
            rec = run_one(run_id, t, w)
            with lock:
                print(json.dumps({"worker": w, "task": t["id"], "completion": rec.get("completion"),
                                  "quality": rec.get("quality_score"), "latency_ms": rec.get("latency_ms"),
                                  "failure_mode": rec.get("failure_mode")}), flush=True)
            if rec.get("limit_hit"):
                with lock:
                    print(json.dumps({"worker": w, "event": "LIMIT_HIT_STOPPING_WORKER"}), flush=True)
                real_evidence.append("limits", {"worker": w, "run_id": run_id, "task_id": t["id"], "timestamp": real_evidence.now_wita()})
                return

    threads = [threading.Thread(target=worker_loop, args=(w,), daemon=True) for w in workers]
    for th in threads:
        th.start()
    for th in threads:
        th.join()


def cross_review(run_id: str, reviewers: tuple[str, ...] = REVIEWERS) -> list[dict[str, Any]]:
    pend = [r for r in real_evidence.read("bench_runs_pending") if r.get("run_id") == run_id]
    done = {(r.get("worker"), r.get("task_id")) for r in real_evidence.read("bench_runs") if r.get("run_id") == run_id}
    pend = [p for p in pend if (p["worker"], p["task_id"]) not in done]
    if not pend:
        return []
    root = real_evidence.root()
    texts = {p["worker"]: (root / p["raw_output_artifact"]).read_text(encoding="utf-8") for p in pend if p.get("raw_output_artifact")}
    rng = random.Random(f"{run_id}-ux")
    reviews: dict[str, list[dict[str, Any]]] = {w: [] for w in texts}
    blind_maps = {}
    for rv in reviewers:
        cands = [w for w in texts if w != rv]  # never review yourself
        rng.shuffle(cands)
        labels = {w: string.ascii_uppercase[i] for i, w in enumerate(cands)}
        blind_maps[rv] = labels
        prompt = B.ux_review_prompt([(labels[w], texts[w]) for w in cands])
        r = dispatch_real(rv, prompt, purpose=f"cross_review:{run_id}", task_class="ux_product", timeout_s=420)
        j = None
        if r.get("ok"):
            from .common import extract_json
            j = extract_json(r.get("_output") or "")
        sc = (j or {}).get("scores") or {}
        for w, lab in labels.items():
            s = sc.get(lab) or sc.get(f"CANDIDATE {lab}") or {}
            vals = [s.get(k) for k, _ in B.UX_RUBRIC]
            if all(isinstance(v, (int, float)) for v in vals):
                reviews[w].append({"reviewer": rv, "label": lab, "scores": {k: s.get(k) for k, _ in B.UX_RUBRIC},
                                   "normalized": round(sum(min(max(v, 0), 2) for v in vals) / (2 * len(vals)), 3),
                                   "comment": str(s.get("comment", ""))[:300]})
        real_evidence.append("cross_reviews", {"run_id": run_id, "reviewer": rv, "blind_labels": labels,
                                               "dispatch_request_id": r.get("request_id"), "ok": r.get("ok"),
                                               "parsed": bool(sc)})
    out = []
    for p in pend:
        w = p["worker"]
        rs = [x for x in reviews.get(w, []) if x["reviewer"] != w]
        q = round(sum(x["normalized"] for x in rs) / len(rs), 3) if rs else None
        rec = {k: v for k, v in p.items() if k not in {"record_sha256", "recorded_at", "evidence_class", "synthetic", "pending_review"}}
        gov = bool(p.get("precheck", {}).get("governance_ok", True))
        rec.update({"quality_score": q if q is not None else 0.0, "accuracy": q, "instruction_following":
                    1.0 if (p.get("precheck", {}).get("words", 0) <= 900) else 0.6,
                    "governance_compliance": gov, "tool_correctness": "N/A (text-only harness)",
                    "grading": f"blind cross-worker rubric, reviewers={[x['reviewer'] for x in rs]} (self excluded)",
                    "reviews": rs, "failure_mode": None if (q or 0) >= 0.8 else "rubric_gaps" if rs else "no_valid_reviews",
                    "completion": "COMPLETED"})
        out.append(real_evidence.append("bench_runs", rec))
    return out


def regrade(run_id: str) -> list[dict[str, Any]]:
    """Re-grade recorded raw outputs with the current grader. Appends new records; never edits old ones."""
    by_id = {t["id"]: t for t in TASKS}
    root = real_evidence.root()
    latest: dict[tuple, dict] = {}
    for r in real_evidence.read("bench_runs"):
        if r.get("run_id") == run_id:
            latest[(r["worker"], r["task_id"])] = r
    out = []
    for (w, tid), r in latest.items():
        t = by_id.get(tid)
        if not t or t["grade"] is None or r.get("completion") != "COMPLETED" or r.get("grader_version") == GRADER_VERSION:
            continue
        text = (root / r["raw_output_artifact"]).read_text(encoding="utf-8")
        g = t["grade"](text)
        keep = {k: v for k, v in r.items() if k not in {"record_sha256", "recorded_at", "evidence_class", "synthetic"}}
        keep.update({**g, "grader_version": GRADER_VERSION, "supersedes_record": r["record_sha256"],
                     "previous_quality_score": r.get("quality_score"), "regraded_from_raw": True})
        out.append(real_evidence.append("bench_runs", keep))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "review", "regrade"])
    ap.add_argument("--run-id", default=time.strftime("bench-%Y%m%d-%H%M"))
    ap.add_argument("--workers", default="claude_pro_sub,codex_sub,cursor_sub,gemini_free,ollama_local")
    ap.add_argument("--tasks", default="")
    a = ap.parse_args()
    workers = [w for w in a.workers.split(",") if w]
    for w in workers:
        if worker_registry.is_metered(w):
            raise SystemExit(f"refusing metered worker {w} in benchmark")
    if a.cmd == "run":
        print(json.dumps({"run_id": a.run_id, "workers": workers}), flush=True)
        run_matrix(a.run_id, workers, [t for t in a.tasks.split(",") if t] or None)
        for r in cross_review(a.run_id):
            print(json.dumps({"review": r["worker"], "quality": r["quality_score"]}), flush=True)
    elif a.cmd == "regrade":
        for r in regrade(a.run_id):
            print(json.dumps({"regraded": r["worker"], "task": r["task_id"], "from": r["previous_quality_score"],
                              "to": r["quality_score"]}), flush=True)
    else:
        for r in cross_review(a.run_id):
            print(json.dumps({"review": r["worker"], "quality": r["quality_score"]}), flush=True)


if __name__ == "__main__":
    main()
