"""Grok Bot subscription path — PULL mode only (truthful).

Findings (2026-10-06, Studio): the Grok Bot desktop app (v0.66.0) exposes no
local API, CLI, or deep link that accepts a prompt and returns an answer. Its
URL schemes (grokbot://, sand://) only open the app / OAuth callbacks. The
local-exec daemon (~/.grokbot/local-exec-daemon*.json) is INBOUND: a Grok Bot
agent session in the cloud drives the Studio, not the other way round. Its
credential file must never be read or replayed by WI.

So WI cannot PUSH a job to Grok Bot. What does work, with no credentials and no
new spend: WI writes the job to an outbox under the REAL evidence root; any
Grok Bot session that a human has started (e.g. Matt's chat, or a Grok Bot
scheduled run) reads the outbox via local-exec, answers, and writes the inbox
file. WI then collects the result. Commissioning state: HUMAN COMMISSIONED /
NOT WI-PUSH-DISPATCHABLE (pull mode available).
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from .. import real_evidence
from .base import AdapterResult, WorkerAdapter, register
from .live_gate import execute_requested

GROKBOT = Path.home() / ".grokbot"


def _boxes() -> tuple[Path, Path]:
    root = real_evidence.root() / "grok_bot_pull"
    outbox, inbox = root / "outbox", root / "inbox"
    outbox.mkdir(parents=True, exist_ok=True)
    inbox.mkdir(parents=True, exist_ok=True)
    return outbox, inbox


class GrokBotPullAdapter(WorkerAdapter):
    worker_id = "grok_bot_sub"
    label = "Grok Bot app — subscription path (pull mode; not WI-push-dispatchable)"
    billing_class = "subscription"
    supports = frozenset({"health", "submit", "result"})

    def health(self) -> AdapterResult:
        facts = {
            "app_present": Path("/Applications/Grok Bot.app").exists(),
            "local_exec_state_present": (GROKBOT / "local-exec-daemon.json").exists(),
            "push_route": "NONE (no local API/CLI/deep-link prompt route; local-exec is inbound only)",
            "pull_route": "outbox/inbox under REAL evidence root, answered by a human-started Grok Bot session",
        }
        return AdapterResult(True, "PULL_ONLY", "Grok Bot reachable only in pull mode", facts)

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        if not execute_requested(job):
            return AdapterResult(False, "SHADOW_SKIPPED", "execute=True required", {"provider_called": False})
        outbox, _ = _boxes()
        handle = str(job.get("request_id") or f"grok-{uuid.uuid4().hex[:12]}")
        if not re.fullmatch(r"[A-Za-z0-9_\-]+", handle):
            return AdapterResult(False, "REFUSED", "bad request id", {"provider_called": False})
        (outbox / f"{handle}.json").write_text(json.dumps({
            "request_id": handle, "prompt": job.get("prompt"), "created_at": real_evidence.now_wita(),
            "instructions": "A Grok Bot session answers by writing inbox/<request_id>.json {request_id, response, answered_at, answered_by}",
        }, indent=1), encoding="utf-8")
        return AdapterResult(False, "QUEUED_FOR_PULL", "queued; needs a human-started Grok Bot session to answer",
                             {"handle": handle, "provider_called": False, "billing_class": "subscription"})

    def result(self, handle: str) -> AdapterResult:
        _, inbox = _boxes()
        p = inbox / f"{handle}.json"
        if not p.exists():
            return AdapterResult(False, "PENDING", "no answer yet", {"handle": handle})
        d = json.loads(p.read_text(encoding="utf-8"))
        return AdapterResult(True, "LIVE_OK", "answered via Grok Bot pull path",
                             {"handle": handle, "output": d.get("response", ""), "answered_at": d.get("answered_at"),
                              "answered_by": d.get("answered_by"), "billing_class": "subscription",
                              "model_observed": d.get("model", "UNKNOWN (Grok Bot does not expose model to WI)")})


register(GrokBotPullAdapter())
