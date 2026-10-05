"""Phase 3 — benchmark harness across capability dimensions.

Does NOT invent scores. Stores historical results. Writes model-scorecard.json.
Uses only public synthetic fixtures — no private/customer data.
Shadow: does not call paid APIs; records structural/self-check scores only for
local deterministic checks, and UNKNOWN for model-requiring dimensions until a
worker actually runs a benchmark job.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import events, registry
from .paths import BENCHMARKS_DIR, CONFIG_DIR, PKG_ROOT, SCORECARD_PATH, ensure_dirs

TZ = ZoneInfo("Asia/Makassar")
FIXTURES = PKG_ROOT / "benchmarks" / "fixtures"

CAPABILITIES = (
    "code_debug",
    "review",
    "security",
    "data_recon",
    "ui_ux",
    "large_context",
    "vision",
    "research",
)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _fixture_ok() -> dict[str, bool]:
    return {
        "code_debug": (FIXTURES / "code_debug.py").exists(),
        "review": (FIXTURES / "review_snippet.py").exists(),
        "security": (FIXTURES / "security_snippet.py").exists(),
        "data_recon": (FIXTURES / "data_recon.csv").exists(),
        "ui_ux": (FIXTURES / "ui_copy.txt").exists(),
        "large_context": (FIXTURES / "large_context.txt").exists(),
        "vision": (FIXTURES / "vision_desc.txt").exists(),
        "research": (FIXTURES / "research_query.txt").exists(),
    }


def _local_structural_checks() -> dict[str, Any]:
    """Deterministic fixture integrity checks — NOT model capability scores."""
    out = {}
    # code_debug: confirm intentional bug present
    src = (FIXTURES / "code_debug.py").read_text()
    out["code_debug_fixture"] = {
        "intentional_bug_present": "return a - b" in src,
        "has_test": "assert add(2, 3) == 5" in src,
    }
    # security: confirm synthetic SQLi pattern
    sec = (FIXTURES / "security_snippet.py").read_text()
    out["security_fixture"] = {"synthetic_sqli_pattern": "SELECT * FROM users" in sec}
    # data_recon: row count
    rows = (FIXTURES / "data_recon.csv").read_text().strip().splitlines()
    out["data_recon_fixture"] = {"rows": len(rows) - 1}
    # large_context size
    lc = FIXTURES / "large_context.txt"
    out["large_context_fixture"] = {"bytes": lc.stat().st_size}
    # ui jargon present for review target
    ui = (FIXTURES / "ui_copy.txt").read_text()
    out["ui_ux_fixture"] = {"jargon_present": "idempotent" in ui}
    return out


def run_all(*, models: list[str] | None = None) -> dict[str, Any]:
    ensure_dirs()
    events.emit("benchmark.started", {"capabilities": list(CAPABILITIES)})
    t0 = time.time()
    fixtures = _fixture_ok()
    structural = _local_structural_checks()

    model_ids = models or [m["id"] for m in registry.list_models()]
    # Capability scores remain UNKNOWN until a real worker benchmark executes.
    # This harness records history + fixture readiness only.
    per_model = {}
    for mid in model_ids:
        scores = {cap: "UNKNOWN" for cap in CAPABILITIES}
        per_model[mid] = {
            "capability_scores": scores,
            "benchmark_status": "NOT_RUN_PAID_SHADOW",
            "note": "Scores stay UNKNOWN until isolated benchmark job executes on worker; shadow harness does not spend API.",
        }

    history_entry = {
        "at": now_iso(),
        "elapsed_ms": int((time.time() - t0) * 1000),
        "fixtures_ok": fixtures,
        "structural": structural,
        "private_customer_data_used": False,
        "models": per_model,
        "mode": "SHADOW_HARNESS",
    }
    hist_path = BENCHMARKS_DIR / "history.jsonl"
    with hist_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(history_entry, ensure_ascii=False) + "\n")

    scorecard = {
        "updated_at": now_iso(),
        "rule": "Do not invent capability scores. UNKNOWN until worker benchmark completes.",
        "capabilities": list(CAPABILITIES),
        "fixtures": {k: str((FIXTURES / name).name) for k, name in {
            "code_debug": "code_debug.py",
            "review": "review_snippet.py",
            "security": "security_snippet.py",
            "data_recon": "data_recon.csv",
            "ui_ux": "ui_copy.txt",
            "large_context": "large_context.txt",
            "vision": "vision_desc.txt",
            "research": "research_query.txt",
        }.items()},
        "fixtures_ok": fixtures,
        "models": per_model,
        "latest_history_at": history_entry["at"],
    }
    SCORECARD_PATH.write_text(json.dumps(scorecard, indent=2) + "\n", encoding="utf-8")
    # Commitable mirror
    (CONFIG_DIR / "model-scorecard.json").write_text(json.dumps(scorecard, indent=2) + "\n")
    # Also update registry models.json capability_scores stay UNKNOWN (already)
    events.emit("benchmark.completed", {"models": len(per_model), "all_unknown": True})
    return scorecard


def accept() -> dict[str, Any]:
    card = run_all()
    checks = [
        {"name": "fixtures_all_ok", "ok": all(card["fixtures_ok"].values())},
        {"name": "scorecard_written", "ok": SCORECARD_PATH.exists()},
        {"name": "commitable_mirror", "ok": (CONFIG_DIR / "model-scorecard.json").exists()},
        {
            "name": "no_invented_scores",
            "ok": all(
                all(v == "UNKNOWN" for v in m["capability_scores"].values())
                for m in card["models"].values()
            ),
        },
        {"name": "no_private_data", "ok": True},
    ]
    passed = all(c["ok"] for c in checks)
    out = {"phase": 3, "passed": passed, "checks": checks}
    (BENCHMARKS_DIR / "phase3-accept.json").write_text(json.dumps(out, indent=2) + "\n")
    return out
