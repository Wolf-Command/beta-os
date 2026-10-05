"""Phase 6 — shadow orchestration vs the current factory.

Synthetic compare does not invent the factory worker. Real shadow runs the
router's live-capable worker beside the factory's actual worker, records both,
and stays labelled SHADOW. It does not take factory or production action.

A record is SHADOW PROVED only when all of these are real and the run is not
mocked or synthetic: current-system worker, Wolf's recommendation, outcome,
test result, time, and known cost or capacity.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from . import dispatcher, events, ledger, work_items
from .adapters import get_adapter
from .adapters.live_gate import env_enabled, providers_mocked
from .factory_history import collect_actual_workers
from .paths import CONFIG_DIR, ensure_dirs
from . import paths
from .router import recommend

TZ = ZoneInfo("Asia/Makassar")
TINY_PROMPT = 'Return the JSON {"ok":true,"n":<sum of 17 and 25>}'
EXPECTED_N = 42
LIVE_CAPABLE = frozenset({"ollama", "cursor", "openai_api", "anthropic_api", "gemini"})
PAID_API = frozenset({"openai_api", "anthropic_api"})
REQUIRED_KEYS = (
    "actual_current_system_worker",
    "recommended_worker",
    "outcome",
    "test_result",
    "at",
    "cost_or_capacity",
)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _phase6_path():
    return CONFIG_DIR / "shadow-compare-phase6.json"


def _compare_log():
    return paths.SHADOW_DIR / "compare.jsonl"


def _real_shadow_log():
    day = datetime.now(TZ).strftime("%Y%m%d")
    return paths.SHADOW_DIR / f"real-shadow-{day}.jsonl"


def rubric_pass(text: str | None) -> bool | None:
    if text is None or not str(text).strip():
        return None
    match = re.search(r"\{.*\}", str(text), re.S)
    if not match:
        return False
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return False
    if not isinstance(data, dict):
        return False
    return data.get("ok") is True and data.get("n") == EXPECTED_N


def test_result_label(passed: bool | None) -> str:
    if passed is True:
        return "pass"
    if passed is False:
        return "fail"
    return "UNKNOWN"


def compute_quality_diff(
    *,
    paired: bool,
    primary_pass: bool | None = None,
    shadow_pass: bool | None = None,
    human_primary: bool | None = None,
    human_shadow: bool | None = None,
) -> tuple[Any, str]:
    """Numeric diff only from paired scored outcomes. Otherwise UNKNOWN."""
    if not paired:
        return "UNKNOWN", "no_paired_outputs"
    if human_primary is not None and human_shadow is not None:
        return _pass_diff(human_primary, human_shadow), "human_pass_fail"
    if primary_pass is None or shadow_pass is None:
        return "UNKNOWN", "no_scored_outputs"
    return _pass_diff(primary_pass, shadow_pass), "automated_rubric"


def _pass_diff(recommended_pass: bool, actual_pass: bool) -> int:
    recommended = 1 if recommended_pass else 0
    actual = 1 if actual_pass else 0
    return recommended - actual


def _known_cost(worker_id: str | None, *, amount_usd: Any = "UNKNOWN", metered_usd: Any = "UNKNOWN") -> dict[str, Any]:
    base = ledger.capacity_for_worker(worker_id)
    if worker_id and isinstance(amount_usd, (int, float)) and metered_usd != "UNKNOWN":
        base["amount_usd"] = float(amount_usd)
        base["metered_usd"] = float(metered_usd)
        base["known"] = True
    elif worker_id and base.get("known"):
        base["amount_usd"] = amount_usd
        base["metered_usd"] = metered_usd
    else:
        base["amount_usd"] = "UNKNOWN"
        base["metered_usd"] = "UNKNOWN"
        base["known"] = False
    return base


def missing_for_shadow_proved(record: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if record.get("mocked") is True:
        missing.append("mocked_not_evidence")
    if record.get("synthetic") is True:
        missing.append("synthetic_not_evidence")
    worker = record.get("actual_current_system_worker")
    if worker in (None, "", "UNKNOWN"):
        missing.append("actual_current_system_worker")
    if not record.get("recommended_worker"):
        missing.append("recommended_worker")
    outcome = record.get("outcome")
    if outcome in (None, "", "UNKNOWN"):
        missing.append("outcome")
    elif isinstance(outcome, dict) and outcome.get("current_system") in (None, "", "UNKNOWN"):
        missing.append("outcome")
    if record.get("test_result") not in ("pass", "fail"):
        missing.append("test_result")
    if not record.get("at"):
        missing.append("at")
    cost = record.get("cost_or_capacity") or {}
    if not isinstance(cost, dict) or cost.get("known") is not True:
        missing.append("cost_or_capacity")
    return missing


def assemble_record(**fields: Any) -> dict[str, Any]:
    record = {
        "at": fields.get("at") or now_iso(),
        "label": fields.get("label") or "SYNTHETIC",
        "mode": "SHADOW",
        "truth_label": "SYNTHETIC",
        "took_action": False,
        "production_touched": False,
        "mocked": bool(fields.get("mocked")),
        "synthetic": bool(fields.get("synthetic")),
        "work_item_id": fields.get("work_item_id"),
        "kind": fields.get("kind"),
        "recommended_worker": fields.get("recommended_worker"),
        "actual_current_system_worker": fields.get("actual_current_system_worker") or None,
        "actual_job_id": fields.get("actual_job_id"),
        "actual_worker_evidence": fields.get("actual_worker_evidence"),
        "actual_worker_source": fields.get("actual_worker_source") or "UNKNOWN",
        "outcome": fields.get("outcome") if fields.get("outcome") is not None else "UNKNOWN",
        "test_result": fields.get("test_result") or "UNKNOWN",
        "cost_or_capacity": fields.get("cost_or_capacity") or _known_cost(None),
        "quality_diff": fields.get("quality_diff", "UNKNOWN"),
        "quality_diff_reason": fields.get("quality_diff_reason") or "no_paired_outputs",
        "expensive_executed": bool(fields.get("expensive_executed")),
        "duplicate_expensive_dispatch": bool(fields.get("duplicate_expensive_dispatch")),
        "shadow_mode": True,
        "latency_ms": fields.get("latency_ms"),
    }
    actual = record["actual_current_system_worker"]
    recommended = record["recommended_worker"]
    if not actual:
        record["agreement"] = None
        record["agreement_reason"] = "NO_REAL_EXECUTION_RECORD"
    else:
        record["agreement"] = recommended == actual
        record["agreement_reason"] = "compared_to_per_job_factory_record"
    record["missing_for_shadow_proved"] = missing_for_shadow_proved(record)
    record["shadow_proved"] = not record["missing_for_shadow_proved"]
    if record["shadow_proved"]:
        record["truth_label"] = "SHADOW PROVED"
    elif record["label"] == "SHADOW" and not record["synthetic"]:
        record["truth_label"] = "SHADOW"
    else:
        record["truth_label"] = "SYNTHETIC"
    return record


def _current_system_actual(*, factory_root=None, config_path=None) -> dict[str, Any]:
    """Per-job factory history only. No cursor default."""
    evidence = collect_actual_workers(factory_root=factory_root, config_path=config_path)
    return {
        "source": evidence["last_worker_hint_source"],
        "last_worker_hint": evidence["last_worker_hint"],
        "last_worker_hint_source": evidence["last_worker_hint_source"],
        "last_worker_hint_sample_counts": evidence["last_worker_hint_sample_counts"],
        "hint_defaulted": False,
        "jobs": evidence["jobs"],
        "skipped_without_worker": evidence["skipped_without_worker"],
        "active": None,
        "active_path": None,
        "priority_queue_n": None,
    }


def _factory_history_workers(limit: int = 30, *, factory_root=None, config_path=None) -> list[dict[str, Any]]:
    evidence = collect_actual_workers(factory_root=factory_root, config_path=config_path)
    return list(evidence["jobs"][:limit])


def _read_phase6() -> dict[str, Any]:
    path = _phase6_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_phase6(summary: dict[str, Any], *, real_shadow: dict[str, Any] | None = None) -> None:
    existing = _read_phase6()
    if real_shadow is None:
        real_shadow = existing.get("real_shadow") or {
            "status": "NOT_RUN",
            "shadow_proved": False,
            "truth_label": "NOT SHADOW PROVED",
            "note": "No Studio real-shadow artifact. Synthetic and mocked runs are not evidence.",
        }
    summary = dict(summary)
    summary["real_shadow"] = real_shadow
    _phase6_path().write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def run_compare(*, samples: int = 12) -> dict[str, Any]:
    ensure_dirs()
    actual = _current_system_actual()
    history = actual["jobs"]
    comparisons = []
    agree = 0
    comparable = 0
    for i in range(samples):
        wi = work_items.create(
            title=f"Shadow compare sample {i+1}",
            kind=["code_debug", "review", "security", "data_recon", "ui_ux"][i % 5],
            isolated_safe=True,
            allow_expensive=False,
            tags=["phase6", "shadow_compare", "synthetic"],
        )
        out = dispatcher.dispatch(wi["id"])
        rec_worker = (out.get("recommendation") or {}).get("recommended_worker")
        job = history[i % len(history)] if history else None
        actual_worker = job["worker"] if job else None
        quality, quality_reason = compute_quality_diff(paired=False)
        row = assemble_record(
            at=now_iso(),
            label="SYNTHETIC",
            synthetic=True,
            mocked=False,
            work_item_id=wi["id"],
            kind=wi["kind"],
            recommended_worker=rec_worker,
            actual_current_system_worker=actual_worker,
            actual_job_id=job.get("job_id") if job else None,
            actual_worker_evidence=job.get("evidence") if job else None,
            actual_worker_source=job.get("source_path") if job else "UNKNOWN",
            outcome="UNKNOWN",
            test_result="UNKNOWN",
            cost_or_capacity=_known_cost(actual_worker),
            quality_diff=quality,
            quality_diff_reason=quality_reason,
        )
        if row["agreement"] is True:
            agree += 1
            comparable += 1
        elif row["agreement"] is False:
            comparable += 1
        comparisons.append(row)
        with _compare_log().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        events.emit("shadow.compare_recorded", {"work_item_id": wi["id"], "shadow_proved": False}, work_item_id=wi["id"])

    summary = {
        "at": now_iso(),
        "samples": samples,
        "agreement_count": agree,
        "agreement_rate": round(agree / comparable, 3) if comparable else None,
        "comparable_samples": comparable,
        "expensive_executed": False,
        "duplicate_expensive_dispatch": False,
        "cost_diff_usd_total": "UNKNOWN",
        "quality_diff": "UNKNOWN",
        "quality_diff_reason": "no_paired_outputs",
        "shadow_proved": False,
        "truth_label": "SYNTHETIC",
        "current_system_snapshot": {
            "last_worker_hint": actual["last_worker_hint"],
            "last_worker_hint_source": actual["last_worker_hint_source"],
            "last_worker_hint_sample_counts": actual["last_worker_hint_sample_counts"],
            "hint_defaulted": False,
            "priority_queue_n": actual.get("priority_queue_n"),
            "active_path": actual.get("active_path"),
            "per_job_records": len(history),
        },
        "comparisons": comparisons,
        "production_touched": False,
        "note": "Synthetic compare. SHADOW PROVED requires a real current-system worker, recommendation, outcome, test result, time, and known cost or capacity.",
    }
    (paths.SHADOW_DIR / "phase6-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    _write_phase6(summary)
    return summary


def _live_job(worker_id: str, work_item_id: str, *, shadow_label: bool) -> dict[str, Any]:
    return {
        "execute": True,
        "prompt": TINY_PROMPT,
        "work_item_id": work_item_id,
        "shadow_mode": True,
        "ledger_note": "SHADOW tiny task; no factory or production action",
        "label": "SHADOW",
        "num_predict": 64,
        "timeout_s": 180,
        "worker_id": worker_id,
        "shadow_label": shadow_label,
    }


def _result_view(result) -> dict[str, Any]:
    if result is None:
        return {"status": "NOT_RUN", "output": None, "latency_ms": None, "ok": False}
    data = result.data or {}
    return {
        "status": result.status,
        "ok": bool(result.ok),
        "message": result.message,
        "output": data.get("output"),
        "latency_ms": data.get("latency_ms"),
        "model_id": data.get("model_id") or "UNKNOWN",
        "amount_usd": (data.get("usage") or {}).get("amount_usd", "UNKNOWN"),
        "metered_usd": (data.get("usage") or {}).get("metered_usd", "UNKNOWN"),
        "provider_called": bool(data.get("provider_called")),
        "mocked": bool(data.get("mocked") or providers_mocked()),
    }


def run_real_shadow(
    n: int = 3,
    *,
    primary_worker: str | None = None,
    shadow_worker: str | None = None,
) -> dict[str, Any]:
    """Run up to 5 tiny SHADOW tasks. Never mutates factory or production."""
    ensure_dirs()
    n = max(1, min(int(n), 5))
    if not env_enabled():
        summary = {
            "at": now_iso(),
            "status": "NOT_RUN",
            "label": "SHADOW",
            "truth_label": "NOT SHADOW PROVED",
            "shadow_proved": False,
            "took_action": False,
            "production_touched": False,
            "mocked": False,
            "reason": "WOLF_INTELLIGENCE_LIVE_SUBMIT is off (default). No provider calls.",
            "runs": [],
        }
        existing = _read_phase6()
        if existing:
            _write_phase6(existing, real_shadow=summary)
        else:
            _write_phase6({"note": "synthetic summary not refreshed by a refused real-shadow"}, real_shadow=summary)
        return summary

    evidence = collect_actual_workers()
    runs = []
    for i in range(n):
        wi = work_items.create(
            title=f"Real shadow tiny {i+1}",
            kind="code_debug",
            payload={"prompt": TINY_PROMPT, "expected_n": EXPECTED_N},
            isolated_safe=True,
            allow_expensive=False,
            tags=["phase6", "real_shadow", "SHADOW"],
        )
        scored = recommend(wi)
        recommended = (scored.get("recommendation") or {}).get("recommended_worker")
        work_items.update_fields(wi["id"], recommendation=scored["recommendation"], scores=scored["scores"])
        job = evidence["jobs"][i % len(evidence["jobs"])] if evidence["jobs"] else None
        actual_worker = job["worker"] if job else None

        runner_recommended = primary_worker or (recommended if recommended in LIVE_CAPABLE else None)
        if shadow_worker:
            runner_actual = shadow_worker
            actual_role = "operator_requested_runner"
        else:
            runner_actual = actual_worker if actual_worker in LIVE_CAPABLE else None
            actual_role = "current_system_actual"
        duplicate = False
        if runner_recommended in PAID_API and runner_actual in PAID_API and runner_recommended != runner_actual:
            runner_actual = None
            duplicate = True

        def _submit(worker_id: str):
            adapter = get_adapter(worker_id)
            if not adapter or "submit" not in adapter.supports:
                from .adapters.base import AdapterResult
                return AdapterResult(False, "UNSUPPORTED", "no live submit", {"provider_called": False})
            return adapter.submit(_live_job(worker_id, wi["id"], shadow_label=True))

        results: dict[str, Any] = {}
        same = runner_recommended and runner_recommended == runner_actual
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {}
            if runner_recommended:
                futures["recommended"] = pool.submit(_submit, runner_recommended)
            if runner_actual and not same:
                futures["actual"] = pool.submit(_submit, runner_actual)
            for key, fut in futures.items():
                results[key] = fut.result()
        if same and "recommended" in results:
            results["actual"] = results["recommended"]

        rec_view = _result_view(results.get("recommended"))
        act_view = _result_view(results.get("actual")) if runner_actual else _result_view(None)
        rec_pass = rubric_pass(rec_view.get("output"))
        act_pass = rubric_pass(act_view.get("output")) if runner_actual else None
        paired = bool(runner_recommended and runner_actual and rec_view.get("output") and act_view.get("output"))
        quality, quality_reason = compute_quality_diff(
            paired=paired,
            primary_pass=rec_pass,
            shadow_pass=act_pass,
        )
        if actual_worker and act_view.get("output"):
            outcome: Any = {
                "current_system": {
                    "worker": actual_worker,
                    "output": (act_view.get("output") or "")[:800],
                    "status": act_view.get("status"),
                }
            }
        else:
            outcome = "UNKNOWN"
        cost_worker = actual_worker or runner_actual
        metered = act_view.get("metered_usd", "UNKNOWN")
        amount = act_view.get("amount_usd", "UNKNOWN")
        if isinstance(amount, (int, float)) and metered != "UNKNOWN":
            cost = _known_cost(cost_worker, amount_usd=amount, metered_usd=metered)
        else:
            cost = _known_cost(actual_worker, amount_usd=amount, metered_usd=metered)
        mocked = providers_mocked() or bool(rec_view.get("mocked") or act_view.get("mocked"))
        row = assemble_record(
            label="SHADOW",
            synthetic=False,
            mocked=mocked,
            work_item_id=wi["id"],
            kind="code_debug",
            recommended_worker=recommended,
            actual_current_system_worker=actual_worker,
            actual_job_id=job.get("job_id") if job else None,
            actual_worker_evidence=job.get("evidence") if job else None,
            actual_worker_source=job.get("source_path") if job else "UNKNOWN",
            outcome=outcome,
            test_result=test_result_label(act_pass) if actual_worker else "UNKNOWN",
            cost_or_capacity=cost,
            quality_diff=quality,
            quality_diff_reason=quality_reason,
            latency_ms={
                "recommended": rec_view.get("latency_ms"),
                "actual": act_view.get("latency_ms"),
            },
            duplicate_expensive_dispatch=False,
        )
        row["recommended_runner"] = runner_recommended
        row["actual_runner"] = runner_actual
        row["actual_runner_role"] = actual_role
        row["recommended_outcome"] = (rec_view.get("output") or "")[:800] or "UNKNOWN"
        row["recommended_test_result"] = test_result_label(rec_pass)
        row["refused_second_paid_api"] = duplicate
        row["same_worker_single_execution"] = bool(same)
        row["took_action"] = False
        runs.append(row)
        with _real_shadow_log().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        events.emit("shadow.compare_recorded", {"shadow_proved": row["shadow_proved"], "mocked": mocked, "label": "SHADOW"}, work_item_id=wi["id"])

    proved = bool(runs) and all(row["shadow_proved"] for row in runs)
    summary = {
        "at": now_iso(),
        "status": "RECORDED",
        "label": "SHADOW",
        "n": n,
        "shadow_proved": proved,
        "truth_label": "SHADOW PROVED" if proved else "SHADOW",
        "took_action": False,
        "production_touched": False,
        "mocked": any(row["mocked"] for row in runs),
        "prompt": TINY_PROMPT,
        "expected_n": EXPECTED_N,
        "runs": runs,
        "note": "SHADOW observation only. Not SHADOW PROVED unless every run has the factory worker, recommendation, outcome, test result, time, and known cost or capacity, and the run is not mocked.",
    }
    existing = _read_phase6()
    base = existing or {"note": "synthetic summary unchanged"}
    _write_phase6(base, real_shadow=summary)
    (paths.SHADOW_DIR / "real-shadow-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def accept() -> dict[str, Any]:
    summary = run_compare(samples=12)
    hint = (summary.get("current_system_snapshot") or {}).get("last_worker_hint")
    counts = (summary.get("current_system_snapshot") or {}).get("last_worker_hint_sample_counts") or {}
    hint_ok = hint == "UNKNOWN" or (isinstance(hint, str) and sum(int(v) for v in counts.values()) > 0)
    rows = summary.get("comparisons") or []
    fields_ok = all(all(key in row for key in REQUIRED_KEYS) for row in rows) if rows else False
    not_proved = summary.get("shadow_proved") is False and all(row.get("shadow_proved") is False for row in rows)
    quality = summary.get("quality_diff")
    if quality == "UNKNOWN":
        quality_ok = bool(summary.get("quality_diff_reason"))
    else:
        quality_ok = summary.get("quality_diff_reason") in {"automated_rubric", "human_pass_fail"}
    checks = [
        {"name": "samples", "ok": summary["samples"] >= 10},
        {"name": "no_expensive", "ok": summary["expensive_executed"] is False},
        {"name": "no_dup", "ok": summary["duplicate_expensive_dispatch"] is False},
        {"name": "has_agreement_rate", "ok": "agreement_rate" in summary},
        {"name": "quality_not_invented", "ok": quality_ok},
        {"name": "no_prod", "ok": summary["production_touched"] is False},
        {"name": "hint_not_defaulted", "ok": hint_ok and summary["current_system_snapshot"].get("hint_defaulted") is False},
        {"name": "record_has_required_fields", "ok": fields_ok},
        {"name": "shadow_not_proved_without_evidence", "ok": not_proved},
    ]
    passed = all(c["ok"] for c in checks)
    out = {
        "phase": 6,
        "passed": passed,
        "checks": checks,
        "agreement_rate": summary["agreement_rate"],
        "shadow_proved": False,
    }
    (paths.SHADOW_DIR / "phase6-accept.json").write_text(json.dumps(out, indent=2) + "\n")
    return out
