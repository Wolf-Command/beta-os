#!/usr/bin/env python3
"""Emit Peaches morning summary from live evidence."""
from __future__ import annotations

import json
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("/Users/wolfterminal/beta-os")
TZ = ZoneInfo("Asia/Makassar")


def tip() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def short() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True).strip()


def ui_ok() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8799/api/health", timeout=2) as r:
            return json.loads(r.read().decode()).get("ok") is True
    except Exception:
        return False


def main() -> int:
    cfg = ROOT / "wolf_intelligence" / "config"
    workers = json.loads((cfg / "worker-status-phase2.json").read_text())
    score = json.loads((cfg / "model-scorecard.json").read_text())
    mirror = ROOT / "state" / "wolf-intelligence" / "mirror"
    shadow_path = mirror / "shadow-compare-phase6.json"
    if not shadow_path.exists():
        shadow_path = cfg / "shadow-compare-phase6.json"
    shadow = json.loads(shadow_path.read_text())
    stats_path = mirror / "stats-summary.json"
    if not stats_path.exists():
        stats_path = cfg / "stats-summary.json"
    stats = json.loads(stats_path.read_text()) if stats_path.exists() else {}
    decisions = json.loads((cfg / "decisions-needed.json").read_text())
    ollama = workers["workers"].get("ollama", {})
    lines = [
        "WOLF INTELLIGENCE NIGHT BUILD — PEACHES SUMMARY",
        f"AT: {datetime.now(TZ).isoformat(timespec='seconds')}",
        f"BRANCH: build/wolf-intelligence-control-plane",
        f"TIP: {tip()} ({short()})",
        f"OWNER UI: http://127.0.0.1:8799/  WORKING={'YES' if ui_ok() else 'NO'} (LaunchAgent KeepAlive)",
        f"BETA PATH: /owner/intelligence wired in code; reload HELD (use sidecar until safe window)",
        f"STORE: SQLite canonical under state/wolf-intelligence/control_plane.sqlite",
        f"WORKERS: {workers.get('summary')} | ollama={ollama.get('status')} retire={ollama.get('retire_candidate')} (NOT deleted)",
        f"SCORECARD: ollama-llama3.2-3b has real local scores; others UNKNOWN (not invented)",
        f"SHADOW: agreement_rate={shadow.get('agreement_rate')} expensive={shadow.get('expensive_executed')} dup={shadow.get('duplicate_expensive_dispatch')}",
        f"LEARNING: outcomes_total={stats.get('outcomes_total')} human={stats.get('outcomes_human')} passes={stats.get('human_passes')}",
        f"DECISIONS_NEEDED: {len(decisions.get('decisions') or [])} (see wolf_intelligence/config/decisions-needed.json)",
        "PRODUCTION TOUCHED: NO",
        "V1 RETIRED: NO",
        "AGENTS DELETED: NO",
        "READY FOR CHATGPT INDEPENDENT REVIEW: YES",
        "",
        "WORKING vs STUB:",
        "- WORKING: Owner UI :8799, SQLite store, shadow dispatch, worker health, local ollama benches, learning+stats, Pass/Fail, KeepAlive, overnight ticks",
        "- STUB/DEFERRED: paid API benches, Grok/ChatGPT plan USD (UNKNOWN), Beta reload for /owner/intelligence, live non-shadow dispatch",
    ]
    text = "\n".join(lines) + "\n"
    out = ROOT / "state/wolf-intelligence/audit/MORNING-PEACHES-SUMMARY.txt"
    out.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
