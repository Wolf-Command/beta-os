"""Aggregate learning/shadow/worker stats for Owner technical panel."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .paths import LEARNING_DIR, SHADOW_DIR, WORKERS_DIR, CONFIG_DIR, ensure_dirs

TZ = ZoneInfo("Asia/Makassar")
STATS_PATH = LEARNING_DIR / "stats.json"
SUMMARY_PATH = CONFIG_DIR / "stats-summary.json"


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def recompute() -> dict[str, Any]:
    from .learning import OUTCOMES_PATH, is_real_human_outcome

    ensure_dirs()
    outcomes = OUTCOMES_PATH
    n = n_human = n_self = passes = fails = 0
    if outcomes.exists():
        for line in outcomes.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            n += 1
            if rec.get("self_eval_rating") is not None:
                n_self += 1
            if not is_real_human_outcome(rec):
                continue
            n_human += 1
            if rec.get("human_passed") is True:
                passes += 1
            elif rec.get("human_passed") is False:
                fails += 1
    shadow_n = 0
    agree = 0
    sc = CONFIG_DIR / "shadow-compare-phase6.json"
    if sc.exists():
        try:
            s = json.loads(sc.read_text())
            shadow_n = s.get("samples") or 0
            agree = s.get("agreement_count") or 0
        except json.JSONDecodeError:
            pass
    workers = {}
    ws = CONFIG_DIR / "worker-status-phase2.json"
    if ws.exists():
        try:
            workers = json.loads(ws.read_text()).get("summary") or {}
        except json.JSONDecodeError:
            pass
    stats = {
        "updated_at": now_iso(),
        "outcomes_total": n,
        "outcomes_human": n_human,
        "outcomes_self_eval_recorded": n_self,
        "human_passes": passes,
        "human_fails": fails,
        "shadow_samples": shadow_n,
        "shadow_agreements": agree,
        "workers": workers,
        "rule": "human > self-eval; human counts require an actor",
    }
    STATS_PATH.write_text(json.dumps(stats, indent=2) + "\n")
    SUMMARY_PATH.write_text(json.dumps(stats, indent=2) + "\n")
    return stats
