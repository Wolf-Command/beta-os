"""Gen-2 statistics and leader selection.

Tie rule (defined BEFORE any gen-2 run): two workers' class means are a quality TIE when
    |mean1 - mean2| <= IMMATERIAL = max(0.05, 2 * sqrt(sd1^2/n1 + sd2^2/n2))
i.e. within 5 points or within ~2 standard errors of run-to-run variation, whichever is larger.
Only inside a TIE may latency be used, and then only as a labelled preference, never as a quality win.
A run FAILS when it did not complete, produced no gradeable output, hit a critical semantic failure, or scored < 0.5.
"""
from __future__ import annotations

import math
from statistics import mean, stdev
from typing import Any

FLOOR = 0.05


def failed(r: dict) -> bool:
    return (r.get("completion") != "COMPLETED" or r.get("quality_score") is None or bool(r.get("critical_failure"))
            or float(r.get("quality_score") or 0) < 0.5)


def summarize(runs: list[dict]) -> dict[str, Any]:
    sup = [r for r in runs if r.get("completion") not in ("UNSUPPORTED", "NOT_ATTEMPTED", "DEFERRED", "PENDING")]
    if not sup:
        st = runs[0].get("completion") if runs else "NO_RUNS"
        return {"status": st, "n": 0, "reason": runs[0].get("failure_mode") if runs else None}
    qs = [float(r.get("quality_score") or 0.0) for r in sup]
    lat = [r["latency_ms"] for r in sup if isinstance(r.get("latency_ms"), (int, float))]
    sd = stdev(qs) if len(qs) > 1 else 0.0
    return {"status": "SUPPORTED", "n": len(qs), "mean": round(mean(qs), 4), "sd": round(sd, 4), "variance": round(sd * sd, 5),
            "min": round(min(qs), 4), "max": round(max(qs), 4),
            "failure_rate": round(sum(failed(r) for r in sup) / len(sup), 3),
            "critical_failures": sum(bool(r.get("critical_failure")) for r in sup),
            "accuracy_mean": round(mean(float(r.get("accuracy") or 0) for r in sup), 4),
            "instruction_mean": round(mean(float(r.get("instruction_following") or 0) for r in sup), 4),
            "governance_pass_rate": round(sum(bool(r.get("governance_compliance", True)) for r in sup) / len(sup), 3),
            "latency_ms_median": sorted(lat)[len(lat) // 2] if lat else None,
            "latency_ms_mean": round(mean(lat)) if lat else None}


def immaterial(a: dict, b: dict) -> float:
    se = math.sqrt((a["sd"] ** 2) / max(1, a["n"]) + (b["sd"] ** 2) / max(1, b["n"]))
    return round(max(FLOOR, 2 * se), 4)


def leader(class_stats: dict[str, dict]) -> dict[str, Any]:
    sup = {w: s for w, s in class_stats.items() if s.get("status") == "SUPPORTED" and s["n"] >= 1}
    if not sup:
        return {"leader": None, "confidence": "NONE", "reason": "no supported worker"}
    ranked = sorted(sup.items(), key=lambda kv: (-kv[1]["mean"], kv[1]["failure_rate"]))
    top_w, top = ranked[0]
    if len(ranked) == 1:
        return {"leader": top_w, "confidence": "LOW", "reason": "only one supported worker", "tied_with": []}
    tied = []
    for w, s in ranked[1:]:
        thr = immaterial(top, s)
        if top["mean"] - s["mean"] <= thr:
            tied.append({"worker": w, "delta": round(top["mean"] - s["mean"], 4), "threshold": thr})
    second_w, second = ranked[1]
    thr2 = immaterial(top, second)
    if tied:
        group = [top_w] + [t["worker"] for t in tied]
        lat = {w: sup[w].get("latency_ms_median") or 10**12 for w in group}
        pref = min(group, key=lambda w: (sup[w]["failure_rate"], lat[w]))
        return {"leader": None, "confidence": "TIE", "tie_group": group, "tied_with": tied,
                "latency_preference_within_tie": pref,
                "reason": f"quality difference within immaterial threshold (top-second delta {round(top['mean'] - second['mean'], 4)} <= {thr2})"}
    margin = round(top["mean"] - second["mean"], 4)
    conf = "HIGH" if (top["n"] >= 3 and second["n"] >= 3 and margin > 2 * thr2 and top["failure_rate"] <= second["failure_rate"]) else "MEDIUM"
    return {"leader": top_w, "confidence": conf, "runner_up": second_w, "margin": margin, "threshold": thr2,
            "reason": f"mean {top['mean']} vs {second['mean']} (margin {margin} > threshold {thr2})"}
