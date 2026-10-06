"""Worker adapters — truthful subset of submit/status/cancel/result/usage/health."""
from __future__ import annotations

from .base import AdapterResult, WorkerAdapter, registry as ADAPTER_REGISTRY
from . import grok_bot, cursor, peaches, openai_worker, anthropic_worker, gemini, ollama  # noqa: F401
# REAL worker paths (2026-10-06): one adapter per provider x billing path.
from . import subscription_cli, grok_pull  # noqa: F401,E402

__all__ = ["WorkerAdapter", "AdapterResult", "ADAPTER_REGISTRY", "get_adapter"]


def get_adapter(worker_id: str) -> WorkerAdapter | None:
    return ADAPTER_REGISTRY.get(worker_id)
