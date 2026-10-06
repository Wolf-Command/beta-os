"""Canonical WI worker registry — one worker per provider × billing path.

Static descriptors below state only HOW a worker is reached and billed. Every
dynamic fact (availability, model observed, capabilities, latency, last
success/failure, benchmark history) is derived from REAL evidence records
(real_evidence.py) and live preflights — never hardcoded. Synthetic history is
ignored because real_evidence.read() returns only evidence_class=REAL rows.

Billing classes: subscription | billing_unverified | local | metered_api.

Commissioning states follow the Owner taxonomy (order 2026-10-06 09:03 WITA) and are
applied only when the evidence supports them; nothing is upgraded without evidence.
Metered workers are gated: routing never selects them and the dispatcher refuses
them unless an unexpired Owner approval record exists. No silent fallback.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from statistics import median
from typing import Any

from . import real_evidence
from .adapters import ADAPTER_REGISTRY

METERED = "metered_api"

WORKERS: dict[str, dict[str, Any]] = {
    "claude_pro_sub": {
        "provider_family": "anthropic", "execution_path": "claude -p (Claude Code CLI), child env scrubbed of ANTHROPIC_API_KEY & co",
        "auth_class": "oauth_subscription_login (claude.ai)", "billing_class": "subscription", "cost_class": "flat_subscription",
        "allowance_visibility": "PARTIAL: claude auth status shows plan tier; remaining 5h/weekly allowance not exposed to CLI -p",
        "human_commissioned": "2026-10-06 Matt: Claude Pro gosscap@gmail.com, header 'Opus 5.5 · Claude Pro'",
        "gated": False, "adapter": "claude_pro_sub", "legacy_ids": ["claude_sub"],
    },
    "anthropic_api": {
        "provider_family": "anthropic", "execution_path": "HTTPS api.anthropic.com/v1/messages",
        "auth_class": "api_key", "billing_class": METERED, "cost_class": "metered_per_token",
        "allowance_visibility": "NONE (console only)", "gated": True, "adapter": "anthropic_api",
        "config_note": "ANTHROPIC_API_KEY exists only as a persistent shell export (~/.zshenv:1, ~/.zshrc:13); beta .env value empty.",
    },
    "codex_sub": {
        "provider_family": "openai", "execution_path": "codex exec --ignore-user-config -s read-only, OPENAI_API_KEY/CODEX_API_KEY scrubbed, -c forced_login_method=chatgpt",
        "auth_class": "oauth_subscription_login (ChatGPT)", "billing_class": "subscription", "cost_class": "flat_subscription",
        "allowance_visibility": "PARTIAL: Owner saw 100% weekly remaining at commissioning; codex exec does not report remaining allowance",
        "human_commissioned": "2026-10-06 Matt: Account Business, GPT-6.1-Sol, 100% weekly remaining",
        "gated": False, "adapter": "codex_sub", "legacy_ids": ["openai_chatgpt"],
    },
    "openai_api": {
        "provider_family": "openai", "execution_path": "HTTPS api.openai.com", "auth_class": "api_key",
        "billing_class": METERED, "cost_class": "metered_per_token", "allowance_visibility": "NONE",
        "gated": True, "adapter": "openai_api", "configured_check": "OPENAI_API_KEY",
    },
    "cursor_sub": {
        "provider_family": "cursor", "execution_path": "cursor-agent --print --mode ask --trust --workspace <scoped temp dir>",
        "auth_class": "subscription_login", "billing_class": "subscription", "cost_class": "flat_subscription_with_included_usage",
        "allowance_visibility": "NONE via CLI (dashboard only)",
        "human_commissioned": "2026-10-06 Matt: mrwolf@wolfcommand.net, Composer 2.5, tested in /private/tmp/wolf-cursor-test",
        "gated": False, "adapter": "cursor_sub", "legacy_ids": ["cursor"],
    },
    "grok_bot_sub": {
        "provider_family": "xai_grok_bot", "execution_path": "PULL ONLY: WI outbox -> human-started Grok Bot session (local-exec) -> WI inbox",
        "auth_class": "grok_bot_app_login", "billing_class": "subscription", "cost_class": "flat_subscription",
        "allowance_visibility": "NONE", "human_commissioned": "2026-10-06 Matt: Grok Bot app replied 'WOLF GROK CONNECTED'",
        "gated": False, "adapter": "grok_bot_sub", "legacy_ids": ["grok_bot"], "push_dispatchable": False,
        "dispatch_mode": "grok_bridge: WI rings a GitHub-issue doorbell (id + nonce only); a Grok routine on issue-assigned claims a lease via the Studio CLI",
    },
    "xai_api": {
        "provider_family": "xai", "execution_path": "HTTPS api.x.ai", "auth_class": "api_key", "billing_class": METERED,
        "cost_class": "metered_per_token", "allowance_visibility": "NONE", "gated": True, "adapter": None,
        "configured_check": "XAI_API_KEY",
    },
    "gemini_api": {
        "provider_family": "google", "execution_path": "generativelanguage v1beta generateContent, flash allowlist",
        "auth_class": "api_key (openclaw credential file)", "billing_class": "billing_unverified",
        "cost_class": "billing_unverified",
        "allowance_visibility": "NONE (429 on exhaustion)", "gated": False, "adapter": "gemini_api",
        "legacy_ids": ["gemini", "gemini_free"],
        "billing_caveat": "billing UNVERIFIED: the key's project billing status is not observable from the Studio and the Owner has not confirmed it",
    },
    "gemini_paid": {
        "provider_family": "google", "execution_path": "generativelanguage (pro/paid models)", "auth_class": "api_key",
        "billing_class": METERED, "cost_class": "metered_per_token", "allowance_visibility": "NONE",
        "gated": True, "adapter": None, "configured_check": "GEMINI_PAID_ENABLED",
    },
    "ollama_local": {
        "provider_family": "ollama", "execution_path": "HTTP 127.0.0.1:11434/api/generate", "auth_class": "none_local",
        "billing_class": "local", "cost_class": "local_compute", "allowance_visibility": "N/A (local)",
        "gated": False, "adapter": "ollama_local", "legacy_ids": ["ollama"],
    },
}

# Owner taxonomy, 2026-10-06 09:03 WITA. Each label is applied only when its evidence condition holds
# (see _commissioning_state); otherwise a lower, truthful label is shown. Metered workers are always GATED.
OWNER_TAXONOMY: dict[str, str] = {
    "claude_pro_sub": "HUMAN COMMISSIONED / CONNECTED",
    "codex_sub": "HUMAN COMMISSIONED / CONNECTED",
    "cursor_sub": "HUMAN COMMISSIONED / CONNECTED",
    "grok_bot_sub": "HUMAN COMMISSIONED MANUALLY / WOLF DISPATCH PARTIAL",
    "gemini_api": "CONNECTED / BILLING UNVERIFIED / NOT HUMAN COMMISSIONED",
    "ollama_local": "CONNECTED / LOCAL / NOT HUMAN COMMISSIONED",
}
METERED_STATE = "GATED"


def canonical_id(worker_id: str) -> str:
    """Map a legacy worker id (e.g. one recorded in older REAL evidence) to its registry id."""
    if worker_id in WORKERS:
        return worker_id
    for wid, d in WORKERS.items():
        if worker_id in (d.get("legacy_ids") or []):
            return wid
    return worker_id


TASK_CLASSES = ("coding", "debugging", "security", "finance", "ux_product", "large_context",
                "vision_document", "structured_extraction", "reasoning_planning")


def is_metered(worker_id: str) -> bool:
    return WORKERS.get(worker_id, {}).get("billing_class") == METERED


def _configured(wid: str, d: dict[str, Any]) -> bool | None:
    check = d.get("configured_check")
    if not check:
        return None
    if os.environ.get(check, "").strip():
        return True
    env = Path("/Users/wolfterminal/beta-os/.env")
    try:
        for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
            k, _, v = line.strip().partition("=")
            if k == check and v.strip().strip("\"'"):
                return True
    except OSError:
        pass
    return False


def _derive(wid: str) -> dict[str, Any]:
    ids = {wid, *(WORKERS.get(wid, {}).get("legacy_ids") or [])}
    conn = [r for r in real_evidence.read("connectivity") if r.get("worker") in ids]
    from .routing_policy import latest_runs
    runs = [r for r in latest_runs() if r.get("worker") in ids]
    calls = [r for r in real_evidence.read("dispatch") if r.get("worker") in ids]
    ok_calls = [c for c in calls if c.get("ok")]
    bad_calls = [c for c in calls if not c.get("ok") and c.get("status") not in {"GATED", "QUEUED_FOR_PULL"}]
    lat = [c.get("latency_ms") for c in ok_calls if isinstance(c.get("latency_ms"), (int, float))]
    models = sorted({str(c.get("model_observed")) for c in ok_calls if c.get("model_observed")})
    caps: dict[str, Any] = {}
    for tc in TASK_CLASSES:
        rs = [r for r in runs if r.get("task_class") == tc]
        if not rs:
            caps[tc] = {"status": "UNTESTED", "n": 0}
            continue
        if all(r.get("completion") == "UNSUPPORTED" for r in rs):
            caps[tc] = {"status": "UNSUPPORTED", "n": len(rs), "reason": rs[-1].get("failure_mode")}
            continue
        scores = [float(r.get("quality_score") or 0) for r in rs]
        mean = sum(scores) / len(scores)
        caps[tc] = {"status": "EVIDENCED_STRONG" if mean >= 0.8 else "EVIDENCED_PARTIAL" if mean >= 0.5 else "EVIDENCED_WEAK",
                    "mean_quality": round(mean, 3), "n": len(rs), "confidence": "low (n=1)" if len(rs) == 1 else f"n={len(rs)}"}
    last_conn = conn[-1] if conn else None
    return {
        "connectivity_last": {k: last_conn.get(k) for k in ("status", "pass", "timestamp", "latency_ms", "evidence_file")} if last_conn else None,
        "last_success": ok_calls[-1].get("timestamp") if ok_calls else None,
        "last_failure": ({"timestamp": bad_calls[-1].get("timestamp"), "status": bad_calls[-1].get("status"),
                          "message": bad_calls[-1].get("message")} if bad_calls else None),
        "latency_history_ms": lat[-20:],
        "latency_median_ms": round(median(lat), 1) if lat else None,
        "model_observed": models or None,
        "benchmark_history": [{"task_class": r.get("task_class"), "quality_score": r.get("quality_score"),
                               "completion": r.get("completion"), "run_id": r.get("run_id")} for r in runs[-30:]],
        "capabilities_evidence": caps,
        "vision": (caps.get("vision_document") or {}).get("status", "UNTESTED"),
        "large_context": (caps.get("large_context") or {}).get("status", "UNTESTED"),
        "limit_hits": sum(1 for c in calls if c.get("limit_hit")),
    }


def _commissioning_state(wid: str, d: dict[str, Any], avail: str, derived: dict[str, Any], configured: bool | None) -> str:
    """Owner taxonomy, gated by evidence. Never upgrades a worker beyond what the evidence shows."""
    if d.get("billing_class") == METERED or d.get("gated"):
        return METERED_STATE
    if d.get("adapter") is None or configured is False:
        return "NOT_CONFIGURED"
    conn_ok = bool(derived.get("connectivity_last") and derived["connectivity_last"].get("pass"))
    human = bool(d.get("human_commissioned"))
    label = OWNER_TAXONOMY.get(wid)
    if wid == "grok_bot_sub":
        return label if (human and label) else "NOT HUMAN COMMISSIONED / WOLF DISPATCH PARTIAL"
    if label and label.startswith("HUMAN COMMISSIONED"):
        if human and conn_ok:
            return label
        return "HUMAN COMMISSIONED / NOT CONNECTED (no WI connectivity pass)" if human else "NOT HUMAN COMMISSIONED / NOT CONNECTED"
    if label:  # CONNECTED / ... / NOT HUMAN COMMISSIONED
        return label if conn_ok else label.replace("CONNECTED", "NOT CONNECTED", 1)
    if human:
        return "HUMAN COMMISSIONED / CONNECTED" if conn_ok else "HUMAN COMMISSIONED / NOT CONNECTED (no WI connectivity pass)"
    return "CONNECTED / NOT HUMAN COMMISSIONED" if conn_ok else "NOT CONNECTED / NOT HUMAN COMMISSIONED"


def build(*, live_preflight: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {"generated_at": real_evidence.now_wita(), "evidence_class": "REAL",
                           "evidence_root": str(real_evidence.root()), "workers": {}}
    for wid, d in WORKERS.items():
        adapter = ADAPTER_REGISTRY.get(d["adapter"]) if d.get("adapter") else None
        configured = _configured(wid, d)
        avail, avail_msg, avail_facts = "NOT_CONFIGURED", "", {}
        if adapter is not None and configured is not False and live_preflight:
            pf = adapter.preflight() if hasattr(adapter, "preflight") else adapter.health()
            avail, avail_msg = pf.status, pf.message
            avail_facts = {k: v for k, v in (pf.data or {}).items() if k not in {"key_source"}}
        elif adapter is not None and configured is not False:
            avail = "NOT_PROBED"
        derived = _derive(wid)
        rec = dict(d)
        rec.update({
            "worker_id": wid,
            "configured": configured,
            "availability": avail,
            "availability_message": real_evidence.redact(str(avail_msg))[:300],
            "billing_verification": avail_facts,
            "routable": (not d.get("gated")) and d.get("push_dispatchable", True) and avail == "CONNECTED",
            **derived,
        })
        rec["commissioning_state"] = _commissioning_state(wid, d, avail, derived, configured)
        rec["evidence_ref"] = "records/{connectivity,dispatch,bench_runs}.jsonl filtered by worker"
        out["workers"][wid] = rec
    blob = json.dumps(out, default=str)
    if real_evidence.contains_secret(blob):
        raise real_evidence.RealEvidenceError("registry snapshot contains secret-shaped material")
    return out


def write_snapshot(path: Path | str, *, live_preflight: bool = True) -> dict[str, Any]:
    reg = build(live_preflight=live_preflight)
    Path(path).write_text(json.dumps(reg, indent=1, default=str) + "\n", encoding="utf-8")
    return reg
