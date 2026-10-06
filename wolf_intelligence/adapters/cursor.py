"""Cursor adapter. Shadow submit does not spawn. Live submit needs execute=True and the env flag."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .base import AdapterResult, WorkerAdapter, register
from .live_gate import (
    cursor_selected_model,
    env_enabled,
    execute_requested,
    ledger_provider_call,
    live_disabled,
    providers_mocked,
    safe_excerpt,
)

BETA = Path("/Users/wolfterminal/beta-os")
LAUNCH = BETA / "scripts" / "build-factory" / "bf_cursor_launch.sh"


def _cursor_bin() -> str | None:
    found = shutil.which("cursor-agent")
    if found:
        return found
    candidate = Path.home() / ".local" / "bin" / "cursor-agent"
    if candidate.is_file():
        return str(candidate)
    return None


class CursorAdapter(WorkerAdapter):
    worker_id = "cursor"
    label = "Cursor"
    supports = frozenset({"health", "submit", "status", "cancel", "result"})

    def health(self) -> AdapterResult:
        evidence = []
        if LAUNCH.exists():
            evidence.append("bf_cursor_launch.sh present")
        cursor_home = Path.home() / ".cursor"
        if cursor_home.exists():
            evidence.append("~/.cursor present")
        binary = _cursor_bin()
        if binary:
            evidence.append(f"cursor-agent on PATH: {binary}")
        if evidence:
            status = "CONNECTED" if LAUNCH.exists() or binary else "PARTIAL"
            return AdapterResult(True, status, "; ".join(evidence), {"launch": str(LAUNCH)})
        return AdapterResult(False, "UNAVAILABLE", "no cursor launch path")

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        if execute_requested(job):
            if not env_enabled():
                return live_disabled()
            return self._live(job)
        if not job.get("shadow_isolated"):
            return AdapterResult(False, "SHADOW_SKIPPED", "refusing live cursor-agent in shadow mode")
        return AdapterResult(
            True,
            "SHADOW_OK",
            "shadow only — would have used cursor-agent --print --mode ask",
            {"prompt_chars": len(job.get("prompt") or ""), "provider_called": False},
        )

    def _live(self, job: dict[str, Any]) -> AdapterResult:
        binary = _cursor_bin()
        if not binary:
            return AdapterResult(False, "UNAVAILABLE", "cursor-agent not on PATH", {"provider_called": False})
        prompt = str(job.get("prompt") or "")
        model_id = str(job.get("model") or cursor_selected_model())
        timeout = float(job.get("timeout_s") or 180)
        workspace = str(job.get("workspace") or "").strip()
        created = None
        if not workspace:
            created = tempfile.mkdtemp(prefix="wi-cursor-ask-")
            workspace = created
        argv = [binary, "--print", "--mode", "ask", "--trust", "--workspace", workspace, prompt]
        started = time.perf_counter()
        try:
            try:
                completed = subprocess.run(
                    argv,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return AdapterResult(False, "ERROR", "cursor-agent timeout", {"provider_called": True, "mocked": providers_mocked()})
            except OSError as exc:
                return AdapterResult(False, "ERROR", type(exc).__name__, {"provider_called": False})
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            output = safe_excerpt(completed.stdout or "")
            ok = completed.returncode == 0 and bool(output)
            status = "LIVE_OK" if ok else "ERROR"
            usage = {
                "pool_id": "cursor_sub_300",
                "amount_usd": 0.0,
                "metered_usd": "UNKNOWN",
                "note": "prepaid cursor_sub_300 USD 300/month; per-call metered USD UNKNOWN",
            }
            ledger_provider_call(
                worker_id="cursor",
                model_id=model_id,
                work_item_id=job.get("work_item_id"),
                amount_usd=0.0,
                metered_usd="UNKNOWN",
                note=str(job.get("ledger_note") or "cursor live submit; metered USD UNKNOWN; no action"),
                shadow_mode=bool(job.get("shadow_mode")),
                latency_ms=latency_ms,
                status=status,
                ok=ok,
                output_excerpt=output,
                label=str(job.get("label") or "LIVE_SUBMIT"),
            )
            return AdapterResult(
                ok,
                status,
                "cursor-agent --print --mode ask --trust --workspace",
                {
                    "output": output,
                    "latency_ms": latency_ms,
                    "exit_code": completed.returncode,
                    "model_id": model_id,
                    "provider_called": True,
                    "mocked": providers_mocked(),
                    "usage": usage,
                    "took_action": False,
                },
                usage=usage,
            )
        finally:
            if created:
                shutil.rmtree(created, ignore_errors=True)

    def status(self, handle: str) -> AdapterResult:
        return AdapterResult(True, "SHADOW_OK", "shadow", {"handle": handle})

    def cancel(self, handle: str) -> AdapterResult:
        return AdapterResult(True, "SHADOW_OK", "shadow cancel noop — never kills workers", {"handle": handle})

    def result(self, handle: str) -> AdapterResult:
        return AdapterResult(True, "SHADOW_OK", "shadow result", {"handle": handle, "output": "SHADOW_NO_EXEC"})


# Legacy worker_id "cursor" superseded by subscription_cli.CursorSubAdapter; not registered.
