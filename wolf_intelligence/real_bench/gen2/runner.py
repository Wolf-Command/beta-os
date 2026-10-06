"""Benchmark generation 2 runner. Resumable, rep-by-rep, with allowance snapshots between reps.

  WOLF_INTELLIGENCE_LIVE_SUBMIT=1 WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT=<root> WOLF_INTELLIGENCE_STATE_ROOT=<scratch> \
  python3 -m wolf_intelligence.real_bench.gen2.runner rep --rep 1 --workers claude_pro_sub,codex_sub,cursor_sub,ollama_local
  ... review --rep 1          (blind UX cross-review, self excluded)
  ... allowance --label pre   (allowance snapshot)
  ... report                  (tables + DRAFT proposed routing, never activated)
"""
from __future__ import annotations

import argparse
import json
import random
import string
import threading
import time
from pathlib import Path
from typing import Any

from ... import real_evidence, worker_registry
from ...real_dispatch import dispatch_real
from . import allowance as AL
from . import stats as ST
from . import t_coding, t_debug, t_extract, t_finance, t_largectx, t_planning, t_regression, t_security, t_ux, t_vision
from .common2 import extract_json

RUN_ID = "gen2-20261006"
GRADER_VERSION = "2.1"  # 2.1: finance GGV duplicate treatment ambiguity + vision discount sign (see GEN2-RESULTS.md)
FIXTURE = Path(__file__).parent / "fixtures" / "receipt2.jpg"
TASKS: list[dict[str, Any]] = [
    {"id": "g2-coding-idr-parser", "cls": "coding", "prompt": lambda: t_coding.PROMPT, "grade": t_coding.grade},
    {"id": "g2-debug-dup-payments", "cls": "debugging", "prompt": lambda: t_debug.PROMPT, "grade": t_debug.grade},
    {"id": "g2-security-portal", "cls": "security", "prompt": lambda: t_security.PROMPT, "grade": t_security.grade},
    {"id": "g2-finance-3entity-close", "cls": "finance", "prompt": t_finance.prompt, "grade": t_finance.grade},
    {"id": "g2-ux-delivery-receiving", "cls": "ux_product", "prompt": lambda: t_ux.PROMPT, "grade": None},
    {"id": "g2-largectx-12docs", "cls": "large_context", "prompt": t_largectx.prompt, "grade": t_largectx.grade, "timeout": 900},
    {"id": "g2-vision-bill", "cls": "vision_document", "prompt": lambda: t_vision.PROMPT, "grade": t_vision.grade, "vision": True},
    {"id": "g2-extract-invoice-thread", "cls": "structured_extraction", "prompt": lambda: t_extract.PROMPT, "grade": t_extract.grade},
    {"id": "g2-plan-freezer", "cls": "reasoning_planning", "prompt": lambda: t_planning.PROMPT, "grade": t_planning.grade},
    {"id": "g2-regression-esb-shift", "cls": "regression_daily_close_extraction", "prompt": t_regression.prompt, "grade": t_regression.grade},
]
OLLAMA_SKIP = {
    "large_context": ("UNSUPPORTED", "llama3.2:3b local: 110 KB corpus exceeds what the 3B model can attend to reliably on this host; not attempted"),
    "vision_document": ("UNSUPPORTED", "installed model llama3.2:3b is text-only"),
    "ux_product": ("NOT_ATTEMPTED", "not plausible for a 3B model; skipped to save blind-review allowance"),
}
REVIEWERS = ("claude_pro_sub", "codex_sub", "cursor_sub")
STOP = {"claude_session_pct": 85, "claude_week_pct": 50, "codex_week_pct": 50}
_stopped: dict[str, str] = {}


def _base(task: dict, worker: str, rep: int) -> dict:
    w = worker_registry.WORKERS[worker]
    return {"run_id": RUN_ID, "rep": rep, "task_id": task["id"], "task_class": task["cls"], "worker": worker,
            "billing_class": w["billing_class"], "cost_class": w["cost_class"], "execution_path": w["execution_path"]}


def run_one(task: dict, worker: str, rep: int) -> dict:
    base = _base(task, worker, rep)
    if worker == "ollama_local" and task["cls"] in OLLAMA_SKIP:
        st, why = OLLAMA_SKIP[task["cls"]]
        return real_evidence.append("gen2_runs", {**base, "completion": st, "quality_score": None, "failure_mode": why, "latency_ms": None})
    files = [str(FIXTURE)] if task.get("vision") else None
    extra = {"num_ctx": 8192} if worker == "ollama_local" else None
    r = dispatch_real(worker, task["prompt"](), purpose=f"benchmark:{RUN_ID}:rep{rep}", task_class=task["cls"], files=files,
                      timeout_s=task.get("timeout", 480), extra=extra)
    out = r.get("_output") or ""
    rec = {**base, "dispatch_request_id": r.get("request_id"), "latency_ms": r.get("latency_ms"), "model_observed": r.get("model_observed"),
           "status": r.get("status"), "limit_hit": r.get("limit_hit"), "raw_output_artifact": r.get("response_artifact"),
           "usage": r.get("usage"), "notional_cost_usd_reported_by_cli": r.get("notional_cost_usd_reported_by_cli")}
    if worker == "cursor_sub" and AL.ON_DEMAND.search(out + " " + str(r.get("error_excerpt") or "") + " " + str(r.get("message") or "")):
        _stopped["cursor_sub"] = "on-demand/usage-based wording observed"
        rec["on_demand_signal"] = True
    if not r.get("ok"):
        rec.update({"completion": "FAILED", "quality_score": 0.0, "failure_mode": f"dispatch:{r.get('status')}",
                    "error_excerpt": r.get("error_excerpt") or r.get("message"), "critical_failure": False})
        return real_evidence.append("gen2_runs", rec)
    if task["grade"] is None:
        pre = t_ux.deterministic(out)
        rec.update({"completion": "COMPLETED", "quality_score": None, "pending_review": True, "deterministic": pre,
                    "governance_compliance": pre.get("governance_ok", True), "grading": "0.6 deterministic + 0.4 blind cross-review (pending)"})
        return real_evidence.append("gen2_ux_pending", rec)
    g = task["grade"](out)
    rec.update({"completion": "COMPLETED", **g, "grading": "deterministic", "grader_version": GRADER_VERSION})
    return real_evidence.append("gen2_runs", rec)


def _done(rep: int) -> set[tuple[str, str]]:
    return {(r["worker"], r["task_id"]) for k in ("gen2_runs", "gen2_ux_pending") for r in real_evidence.read(k)
            if r.get("run_id") == RUN_ID and r.get("rep") == rep}


def run_rep(rep: int, workers: list[str], task_filter: list[str] | None = None) -> None:
    tasks = [t for t in TASKS if not task_filter or t["id"] in task_filter or t["cls"] in task_filter]
    done = _done(rep)
    lock = threading.Lock()

    def loop(w: str) -> None:
        for t in tasks:
            if (w, t["id"]) in done:
                continue
            if w in _stopped:
                rec = real_evidence.append("gen2_runs", {**_base(t, w, rep), "completion": "NOT_RUN_STOPPED", "quality_score": None,
                                                         "failure_mode": _stopped[w]})
                continue
            rec = run_one(t, w, rep)
            with lock:
                print(json.dumps({"rep": rep, "worker": w, "task": t["id"], "completion": rec.get("completion"),
                                  "q": rec.get("quality_score"), "crit": rec.get("critical_failure"),
                                  "ms": rec.get("latency_ms"), "fm": (rec.get("failure_mode") or "")[:80]}), flush=True)
            if rec.get("limit_hit"):
                _stopped[w] = "subscription limit hit"
                real_evidence.append("limits", {"worker": w, "run_id": RUN_ID, "rep": rep, "task_id": t["id"], "timestamp": real_evidence.now_wita()})

    th = [threading.Thread(target=loop, args=(w,), daemon=True) for w in workers]
    for x in th:
        x.start()
    for x in th:
        x.join()


def review(rep: int) -> list[dict]:
    pend = [r for r in real_evidence.read("gen2_ux_pending") if r.get("run_id") == RUN_ID and r.get("rep") == rep]
    graded = {(r["worker"], r["rep"]) for r in real_evidence.read("gen2_runs") if r.get("run_id") == RUN_ID and r.get("task_class") == "ux_product"}
    pend = [p for p in pend if (p["worker"], rep) not in graded]
    if not pend:
        return []
    root = real_evidence.root()
    texts = {p["worker"]: (root / p["raw_output_artifact"]).read_text(encoding="utf-8") for p in pend if p.get("raw_output_artifact")}
    rng = random.Random(f"{RUN_ID}-ux-{rep}")
    reviews: dict[str, list[dict]] = {w: [] for w in texts}
    for rv in REVIEWERS:
        if rv in _stopped:
            continue
        cands = [w for w in texts if w != rv]  # never review yourself
        if not cands:
            continue
        rng.shuffle(cands)
        labels = {w: string.ascii_uppercase[i] for i, w in enumerate(cands)}
        r = dispatch_real(rv, t_ux.review_prompt([(labels[w], texts[w]) for w in cands]), purpose=f"cross_review:{RUN_ID}:rep{rep}",
                          task_class="ux_product", timeout_s=480)
        j = extract_json(r.get("_output") or "") if r.get("ok") else None
        sc = (j or {}).get("scores") or {}
        for w, lab in labels.items():
            s = sc.get(lab) or sc.get(f"CANDIDATE {lab}") or {}
            vals = [s.get(k) for k, _ in t_ux.RUBRIC]
            if all(isinstance(v, (int, float)) for v in vals):
                reviews[w].append({"reviewer": rv, "label": lab, "scores": {k: s.get(k) for k, _ in t_ux.RUBRIC},
                                   "normalized": round(sum(min(max(v, 0), 2) for v in vals) / (2 * len(vals)), 4),
                                   "comment": str(s.get("comment", ""))[:300]})
        real_evidence.append("gen2_reviews", {"run_id": RUN_ID, "rep": rep, "reviewer": rv, "blind_labels": labels,
                                              "dispatch_request_id": r.get("request_id"), "ok": r.get("ok"), "parsed": bool(sc),
                                              "latency_ms": r.get("latency_ms")})
    out = []
    for p in pend:
        w = p["worker"]
        rs = [x for x in reviews.get(w, []) if x["reviewer"] != w]
        rub = round(sum(x["normalized"] for x in rs) / len(rs), 4) if rs else None
        det = float(p["deterministic"].get("score") or 0)
        q = round(0.6 * det + 0.4 * rub, 4) if rub is not None else round(0.6 * det, 4)
        gov = bool(p["deterministic"].get("governance_ok", True))
        if not gov:
            q = min(q, 0.5)
        rec = {k: v for k, v in p.items() if k not in {"record_sha256", "recorded_at", "evidence_class", "synthetic", "pending_review"}}
        rec.update({"quality_score": q, "accuracy": det, "rubric_score": rub,
                    "instruction_following": 1.0 if p["deterministic"].get("json_only") else 0.7,
                    "governance_compliance": gov, "critical_failure": False, "reviews": rs,
                    "grading": f"0.6 deterministic + 0.4 blind rubric; reviewers={[x['reviewer'] for x in rs]} (self excluded)",
                    "grader_version": GRADER_VERSION,
                    "failure_mode": None if q >= 0.8 else ("no_valid_reviews" if rub is None else "rubric_or_permission_gaps")})
        out.append(real_evidence.append("gen2_runs", rec))
    return out


def regrade() -> list[dict]:
    """Re-grade recorded raw outputs with the current deterministic graders. Appends superseding records only."""
    by_id = {t["id"]: t for t in TASKS}
    root = real_evidence.root()
    out = []
    for r in latest_runs():
        t = by_id.get(r["task_id"])
        if not t or t["grade"] is None or r.get("completion") != "COMPLETED" or r.get("grader_version") == GRADER_VERSION:
            continue
        g = t["grade"]((root / r["raw_output_artifact"]).read_text(encoding="utf-8"))
        keep = {k: v for k, v in r.items() if k not in {"record_sha256", "recorded_at", "evidence_class", "synthetic"}}
        keep.update({**g, "grader_version": GRADER_VERSION, "supersedes_record": r.get("record_sha256"),
                     "previous_quality_score": r.get("quality_score"), "regraded_from_raw": True})
        out.append(real_evidence.append("gen2_runs", keep))
    return out


def latest_runs() -> list[dict]:
    seen: dict[tuple, dict] = {}
    for r in real_evidence.read("gen2_runs"):
        if r.get("run_id") == RUN_ID:
            seen[(r["worker"], r["task_id"], r["rep"])] = r
    return list(seen.values())


def build_report(extra_rows: dict[str, dict] | None = None) -> dict:
    runs = latest_runs()
    classes = [t["cls"] for t in TASKS]
    workers = sorted({r["worker"] for r in runs})
    table: dict[str, dict] = {}
    for c in classes:
        table[c] = {}
        for w in workers:
            rs = [r for r in runs if r["task_class"] == c and r["worker"] == w and r.get("completion") != "NOT_RUN_STOPPED"]
            table[c][w] = ST.summarize(rs) if rs else {"status": "NO_RUNS", "n": 0}
        for w, row in (extra_rows or {}).items():
            table[c][w] = row
        table[c]["_leader"] = ST.leader({w: s for w, s in table[c].items() if not w.startswith("_")})
    return {"run_id": RUN_ID, "grader_version": GRADER_VERSION, "tie_rule": ST.__doc__.strip(), "table": table}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["rep", "review", "allowance", "report", "regrade"])
    ap.add_argument("--rep", type=int, default=1)
    ap.add_argument("--workers", default="claude_pro_sub,codex_sub,cursor_sub,ollama_local")
    ap.add_argument("--tasks", default="")
    ap.add_argument("--label", default="snap")
    a = ap.parse_args()
    workers = [w for w in a.workers.split(",") if w]
    for w in workers:
        if worker_registry.is_metered(w):
            raise SystemExit(f"refusing metered worker {w}")
    if a.cmd == "rep":
        run_rep(a.rep, workers, [t for t in a.tasks.split(",") if t] or None)
        print(json.dumps({"stopped": _stopped}), flush=True)
    elif a.cmd == "review":
        for r in review(a.rep):
            print(json.dumps({"ux": r["worker"], "rep": a.rep, "q": r["quality_score"], "det": r["accuracy"], "rubric": r["rubric_score"]}), flush=True)
    elif a.cmd == "regrade":
        for r in regrade():
            if r.get("previous_quality_score") != r.get("quality_score"):
                print(json.dumps({"regraded": r["worker"], "task": r["task_id"], "rep": r["rep"], "from": r["previous_quality_score"], "to": r["quality_score"]}), flush=True)
    elif a.cmd == "allowance":
        snap = AL.snapshot(real_evidence.root(), a.label, workers)
        real_evidence.append("gen2_allowance", snap)
        print(json.dumps(snap), flush=True)
    else:
        rep = build_report()
        p = real_evidence.root() / "gen2-report.json"
        p.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
        print(str(p))


if __name__ == "__main__":
    main()
