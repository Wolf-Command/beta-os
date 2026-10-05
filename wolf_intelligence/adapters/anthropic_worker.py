"""Anthropic — Claude subscription vs API separate. Haiku = default not best."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from .base import AdapterResult, WorkerAdapter, register

BETA_ENV = Path("/Users/wolfterminal/beta-os/.env")
OPENCLAW = Path.home() / ".openclaw" / "openclaw.json"

def _env_has(name: str) -> bool:
    if not BETA_ENV.exists():
        return False
    for line in BETA_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == name and v.strip():
            return True
    return False

class AnthropicAPIAdapter(WorkerAdapter):
    worker_id = "anthropic_api"
    label = "Anthropic API"
    supports = frozenset({"health", "submit"})

    def health(self) -> AdapterResult:
        has = _env_has("ANTHROPIC_API_KEY")
        evidence = []
        openclaw_holds = False
        if has:
            evidence.append("ANTHROPIC_API_KEY configured in beta .env (value not read)")
        name_present = False
        try:
            env = Path("/Users/wolfterminal/beta-os/.env")
            if env.exists():
                for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.strip().startswith("ANTHROPIC_API_KEY="):
                        name_present = True
                        break
        except OSError:
            pass
        if name_present and not has:
            evidence.append("ANTHROPIC_API_KEY name present in beta .env but value empty")
        if OPENCLAW.exists():
            try:
                txt = OPENCLAW.read_text(encoding="utf-8", errors="replace")
                if "haiku" in txt.lower():
                    evidence.append("openclaw primary mentions haiku (default not best)")
                if "anthropic" in txt.lower():
                    evidence.append("openclaw references anthropic")
                # Detect credential material WITHOUT copying it
                # Credential material may live in auth profiles — detect presence only
                if "sk-ant-" in txt:
                    openclaw_holds = True
                    evidence.append("openclaw.json appears to embed Anthropic credential material (not copied)")
                auth_roots = [
                    Path.home() / ".openclaw" / "agents",
                    Path.home() / ".openclaw",
                ]
                for root in auth_roots:
                    if not root.exists():
                        continue
                    for ap in root.rglob("auth-profiles.json"):
                        try:
                            at = ap.read_text(encoding="utf-8", errors="replace")
                        except OSError:
                            continue
                        if "anthropic" in at.lower() or "sk-ant-" in at:
                            openclaw_holds = True
                            evidence.append(f"auth-profiles references anthropic ({ap.name})")
                            break
                    if openclaw_holds:
                        break
            except OSError:
                pass
        status = "CONNECTED" if (has or openclaw_holds) else ("PARTIAL" if evidence else "UNAVAILABLE")
        if evidence:
            return AdapterResult(True if status != "UNAVAILABLE" else False, status, "; ".join(evidence),
                                 {"billing": "api", "note": "haiku_is_default_not_best", "openclaw_may_hold_creds": openclaw_holds})
        return AdapterResult(False, "UNAVAILABLE", "no Anthropic API evidence")

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        if not job.get("shadow_isolated"):
            return AdapterResult(False, "SHADOW_SKIPPED", "no live Anthropic API in shadow")
        return AdapterResult(True, "SHADOW_OK", "shadow — no tokens spent", {"billing": "api"})

class ClaudeSubAdapter(WorkerAdapter):
    worker_id = "claude_sub"
    label = "Claude Subscription"
    supports = frozenset({"health"})

    def health(self) -> AdapterResult:
        claude_home = Path.home() / ".claude"
        evidence = []
        if claude_home.exists():
            evidence.append("~/.claude present")
        return AdapterResult(True, "PARTIAL",
                             "Owner-declared Claude sub $25/mo; live plan tier not probed. " + "; ".join(evidence),
                             {"billing": "subscription", "owner_declared_usd_mo": 25})

register(AnthropicAPIAdapter())
register(ClaudeSubAdapter())
