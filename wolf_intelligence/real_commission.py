"""REAL commissioning: billing-separation proof + one connectivity ping per worker, via WI's dispatcher.

Usage (writes only to the REAL evidence root):
  WOLF_INTELLIGENCE_LIVE_SUBMIT=1 WOLF_INTELLIGENCE_REAL_EVIDENCE_ROOT=... \
  WOLF_INTELLIGENCE_STATE_ROOT=<scratch> python3 -m wolf_intelligence.real_commission connectivity
"""
from __future__ import annotations

import json
import os
import sys
from unittest import mock

from . import real_evidence, worker_registry
from .adapters import ADAPTER_REGISTRY
from .real_dispatch import dispatch_real

PING_WORKERS = ("claude_pro_sub", "codex_sub", "cursor_sub", "gemini_api", "ollama_local", "grok_bot_sub",
                "anthropic_api", "openai_api", "xai_api", "gemini_paid")


def expected_for(worker: str) -> str:
    return f"WOLF {worker.upper()} WI PASS"


def billing_separation_proof() -> dict:
    """Show that parent-env API keys do NOT change which billing path a subscription worker uses."""
    out = {"timestamp": real_evidence.now_wita(), "checks": []}
    claude = ADAPTER_REGISTRY["claude_pro_sub"]
    parent_has = bool(os.environ.get("ANTHROPIC_API_KEY"))
    pf = claude.preflight()
    out["checks"].append({"worker": "claude_pro_sub", "parent_env_has_ANTHROPIC_API_KEY": parent_has,
                          "child_env_has_ANTHROPIC_API_KEY": "ANTHROPIC_API_KEY" in claude.env(),
                          "preflight_status": pf.status, "authMethod": pf.data.get("authMethod"),
                          "apiKeySource": pf.data.get("apiKeySource"), "subscriptionType": pf.data.get("subscriptionType"),
                          "pass": pf.ok and parent_has is not None})
    codex = ADAPTER_REGISTRY["codex_sub"]
    with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "dummy-not-a-real-key", "CODEX_API_KEY": "dummy-not-a-real-key"}):
        pf2 = codex.preflight()
        child = codex.env()
    out["checks"].append({"worker": "codex_sub", "parent_env_injected_dummy": ["OPENAI_API_KEY", "CODEX_API_KEY"],
                          "child_env_has_OPENAI_API_KEY": "OPENAI_API_KEY" in child,
                          "child_env_has_CODEX_API_KEY": "CODEX_API_KEY" in child,
                          "preflight_status": pf2.status, "login_status": pf2.data.get("login_status"),
                          "auth_json_auth_mode": pf2.data.get("auth_json_auth_mode"), "pass": pf2.ok})
    cur = ADAPTER_REGISTRY["cursor_sub"]
    with mock.patch.dict(os.environ, {"CURSOR_API_KEY": "dummy-not-a-real-key"}):
        child = cur.env()
    out["checks"].append({"worker": "cursor_sub", "child_env_has_CURSOR_API_KEY": "CURSOR_API_KEY" in child,
                          "pass": "CURSOR_API_KEY" not in child})
    out["all_pass"] = all(c["pass"] for c in out["checks"])
    return real_evidence.append("billing_separation", out)


def connectivity() -> list[dict]:
    results = []
    for w in PING_WORKERS:
        exp = expected_for(w)
        prompt = f"Reply with exactly this text and nothing else: {exp}"
        r = dispatch_real(w, prompt, purpose="connectivity", timeout_s=240)
        out = (r.get("_output") or "").strip()
        exact = out == exp
        contains = exp in out
        status = r.get("status")
        rec = {"worker": w, "path": worker_registry.WORKERS[w]["execution_path"], "timestamp": r.get("timestamp"),
               "request": prompt, "expected": exp, "response": out[:200], "latency_ms": r.get("latency_ms"),
               "status": status, "pass": bool(r.get("ok") and contains), "exact_match": exact,
               "billing_class": worker_registry.WORKERS[w]["billing_class"], "model_observed": r.get("model_observed"),
               "billing_preflight": r.get("billing_preflight"), "dispatch_request_id": r.get("request_id"),
               "evidence_file": "records/dispatch.jsonl#" + str(r.get("request_id")), "response_artifact": r.get("response_artifact"),
               "message": r.get("message")}
        results.append(real_evidence.append("connectivity", rec))
        print(json.dumps({k: rec[k] for k in ("worker", "status", "pass", "exact_match", "latency_ms", "model_observed", "response")}), flush=True)
    return results


def approve_metered(worker: str, hours: float) -> dict:
    """Owner-only, interactive. Writes an expiring approval for ONE metered worker. Refuses without a TTY."""
    if not worker_registry.is_metered(worker):
        raise SystemExit(f"{worker} is not a metered worker")
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise SystemExit("approval needs an interactive Owner terminal (no TTY)")
    phrase = f"APPROVE {worker} {hours:g}h"
    typed = input(f"Owner: type exactly '{phrase}' to allow metered billing for {worker}: ").strip()
    if typed != phrase:
        raise SystemExit("not approved")
    from datetime import datetime, timedelta
    exp = (datetime.now(real_evidence.WITA) + timedelta(hours=hours)).isoformat(timespec="seconds")
    return real_evidence.append("owner_approvals", {"worker_id": worker, "expires_at": exp, "approved_via": "interactive TTY"})


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "connectivity"
    if cmd == "approve-metered":
        print(json.dumps(approve_metered(sys.argv[2], float(sys.argv[3] if len(sys.argv) > 3 else 1)), indent=1))
        raise SystemExit(0)
    if cmd == "billing":
        print(json.dumps(billing_separation_proof(), indent=1))
    elif cmd == "connectivity":
        connectivity()
