"""Owner-facing REAL summary + registry/routing snapshots.

  python3 -m wolf_intelligence.real_report --out-dir <dir> [--config-snapshot]
Writes worker-registry.json, routing-policy-real.json, OWNER-SUMMARY.md to --out-dir (REAL evidence root),
and with --config-snapshot also refreshes config/worker-registry.json + config/routing-policy-real.json
(tracked snapshot; commit-time only).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import real_evidence, routing_policy, worker_registry
from .paths import CONFIG_DIR

LABELS = {"claude_pro_sub": "Claude Pro (subscription)", "codex_sub": "ChatGPT/Codex (subscription)",
          "cursor_sub": "Cursor (subscription)", "grok_bot_sub": "Grok Bot (subscription, pull-only)",
          "gemini_free": "Gemini (free path)", "ollama_local": "Ollama llama3.2:3b (local)",
          "anthropic_api": "Anthropic API (metered)", "openai_api": "OpenAI API (metered)",
          "xai_api": "xAI API (metered)", "gemini_paid": "Gemini paid (metered)"}


def owner_bucket(w: str, r: dict) -> str:
    st = r["commissioning_state"]
    if "WI_CONNECTED" in st and "NOT_WI" not in st:
        return "CONNECTED"
    if "pull-mode PASS" in st:
        return "NEEDS YOU"
    if st.startswith("GATED"):
        return "GATED (metered; stays off unless Owner approves)" if w == "anthropic_api" else "NOT CONFIGURED"
    if st.startswith("NOT_CONFIGURED"):
        return "NOT CONFIGURED"
    return "FAILED"


def summary_md(reg: dict, pol: dict) -> str:
    L = ["# Wolf Intelligence — REAL worker commissioning summary", "",
         f"Generated {reg['generated_at']} (WITA). Evidence class: REAL only (synthetic dev evidence excluded).", "",
         "## Workers", "", "| Worker | Status | Billing | Commissioning state | WI connectivity | Median latency (all REAL calls) |",
         "|---|---|---|---|---|---|"]
    for w, r in reg["workers"].items():
        c = r.get("connectivity_last") or {}
        L.append(f"| {LABELS.get(w, w)} | {owner_bucket(w, r)} | {r['billing_class']} | {r['commissioning_state']} | "
                 f"{'PASS' if c.get('pass') else (c.get('status') or '-')} | {r.get('latency_median_ms') or '-'} ms |")
    L += ["", "## Best current per task class (n=1 per worker: low confidence, not a universal ranking)", "",
          "| Task class | Best current | Default pick (tie broken by latency) | Ranking (mean quality) | Confidence | Caveat |", "|---|---|---|---|---|---|"]
    for tc, e in pol["task_classes"].items():
        rk = ", ".join(f"{x['worker']} {x['mean_quality']:.2f}" for x in e.get("ranking", []))
        best = e.get("preferred") or (" / ".join(e.get("tied_top") or []) + " (tie)" if e.get("tied_top") else "-")
        cav = ("unsupported: " + ", ".join(e["unsupported"])) if e.get("unsupported") else ""
        pick = (e.get("order") or ["-"])[0]
        L.append(f"| {tc} | {best} | {pick} | {rk} | {e.get('confidence', '-')} | {cav} |")
    L += ["", "Routing never selects a metered worker and never falls back to one. Metered workers need an Owner approval record."]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(real_evidence.root()))
    ap.add_argument("--config-snapshot", action="store_true")
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    reg = worker_registry.write_snapshot(out / "worker-registry.json")
    pol = routing_policy.write(out / "routing-policy-real.json")
    (out / "OWNER-SUMMARY.md").write_text(summary_md(reg, pol), encoding="utf-8")
    if a.config_snapshot:
        (CONFIG_DIR / "worker-registry.json").write_text(json.dumps(reg, indent=1, default=str) + "\n", encoding="utf-8")
        (CONFIG_DIR / "routing-policy-real.json").write_text(json.dumps(pol, indent=1) + "\n", encoding="utf-8")
    print(summary_md(reg, pol))


if __name__ == "__main__":
    main()
