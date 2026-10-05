"""Safe local benchmarks (Ollama only). No paid API spend."""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import events, registry
from .paths import BENCHMARKS_DIR, CONFIG_DIR, PKG_ROOT, SCORECARD_PATH, ensure_dirs

TZ = ZoneInfo("Asia/Makassar")
FIXTURES = PKG_ROOT / "benchmarks" / "fixtures"
OLLAMA = "http://127.0.0.1:11434"


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _ollama_generate(prompt: str, *, model: str = "llama3.2:3b", timeout: int = 60) -> str:
    body = json.dumps({"model": model, "prompt": prompt, "stream": False, "options": {"num_predict": 120}}).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/generate", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    return (data.get("response") or "").strip()


def _score_presence(text: str, needles: list[str]) -> float:
    if not text:
        return 0.0
    hits = sum(1 for n in needles if n.lower() in text.lower())
    return round(hits / max(len(needles), 1), 3)


def run_ollama_safe() -> dict[str, Any]:
    ensure_dirs()
    # health
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=2) as resp:
            tags = json.loads(resp.read().decode())
    except Exception as e:
        return {"ok": False, "error": f"ollama_down:{type(e).__name__}"}

    model = "llama3.2:3b"
    names = [m.get("name") for m in tags.get("models") or []]
    if model not in names and not any(model in (n or "") for n in names):
        return {"ok": False, "error": "model_missing", "models": names}

    results: dict[str, Any] = {}
    # code_debug
    bug = (FIXTURES / "code_debug.py").read_text()
    t0 = time.time()
    out = _ollama_generate(f"Find the bug in this Python. Reply briefly.\n\n{bug}")
    results["code_debug"] = {
        "score": _score_presence(out, ["-", "subtract", "bug", "should add", "return a + b", "addition"]),
        "latency_ms": int((time.time() - t0) * 1000),
        "output_excerpt": out[:240],
    }
    # review
    rev = (FIXTURES / "review_snippet.py").read_text()
    t0 = time.time()
    out = _ollama_generate(f"Code review: what risk?\n\n{rev}")
    results["review"] = {
        "score": _score_presence(out, ["overdraft", "negative", "balance", "check", "validation", "amount"]),
        "latency_ms": int((time.time() - t0) * 1000),
        "output_excerpt": out[:240],
    }
    # security
    sec = (FIXTURES / "security_snippet.py").read_text()
    t0 = time.time()
    out = _ollama_generate(f"Security issue?\n\n{sec}")
    results["security"] = {
        "score": _score_presence(out, ["sql", "injection", "inject", "user_input", "parameter", "sanitize"]),
        "latency_ms": int((time.time() - t0) * 1000),
        "output_excerpt": out[:240],
    }
    # data_recon
    csv = (FIXTURES / "data_recon.csv").read_text()
    t0 = time.time()
    out = _ollama_generate(f"Sum amount for category alpha:\n{csv}\nAnswer with the number.")
    results["data_recon"] = {
        "score": 1.0 if "15" in out else _score_presence(out, ["15", "alpha", "10", "5"]),
        "latency_ms": int((time.time() - t0) * 1000),
        "output_excerpt": out[:240],
    }
    # ui_ux
    ui = (FIXTURES / "ui_copy.txt").read_text()
    t0 = time.time()
    out = _ollama_generate(f"Rewrite for a non-technical owner. Flag jargon:\n{ui}")
    results["ui_ux"] = {
        "score": _score_presence(out, ["jargon", "simple", "submit", "clear", "idempotent"]),
        "latency_ms": int((time.time() - t0) * 1000),
        "output_excerpt": out[:240],
    }
    # research (public fact)
    t0 = time.time()
    out = _ollama_generate((FIXTURES / "research_query.txt").read_text())
    results["research"] = {
        "score": _score_presence(out, ["jakarta", "indonesia"]),
        "latency_ms": int((time.time() - t0) * 1000),
        "output_excerpt": out[:240],
    }
    # large_context / vision — not meaningfully runnable on 3b without spend/time; leave UNKNOWN
    results["large_context"] = {"score": "UNKNOWN", "reason": "skipped_local_3b_context_limit"}
    results["vision"] = {"score": "UNKNOWN", "reason": "no_local_vision_model"}

    entry = {
        "at": now_iso(),
        "worker": "ollama",
        "model_id": "ollama-llama3.2-3b",
        "paid_spend_usd": 0.0,
        "results": results,
    }
    hist = BENCHMARKS_DIR / "local-ollama-history.jsonl"
    with hist.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Update scorecard ONLY for this model from real runs
    scorecard_path = CONFIG_DIR / "model-scorecard.json"
    if scorecard_path.exists():
        card = json.loads(scorecard_path.read_text())
    else:
        card = {"models": {}}
    mid = "ollama-llama3.2-3b"
    scores = {}
    for cap, r in results.items():
        scores[cap] = r["score"] if isinstance(r.get("score"), (int, float)) else "UNKNOWN"
    card.setdefault("models", {})[mid] = {
        "capability_scores": scores,
        "benchmark_status": "LOCAL_OLLAMA_RUN",
        "last_run_at": entry["at"],
        "paid_spend_usd": 0.0,
        "note": "Scores from real local ollama generate; UNKNOWN where skipped",
    }
    card["updated_at"] = now_iso()
    scorecard_path.write_text(json.dumps(card, indent=2) + "\n")
    SCORECARD_PATH.write_text(json.dumps(card, indent=2) + "\n")

    # Reflect into models.json for this model only
    models_path = CONFIG_DIR / "models.json"
    models = json.loads(models_path.read_text())
    for m in models.get("models") or []:
        if m.get("id") == mid:
            m["capability_scores"] = scores
            m["benchmark_status"] = "LOCAL_OLLAMA_RUN"
            m["last_benchmark_at"] = entry["at"]
    models_path.write_text(json.dumps(models, indent=2) + "\n")

    events.emit("benchmark.completed", {"model_id": mid, "local": True, "paid_spend_usd": 0.0})
    return {"ok": True, "entry": entry}
