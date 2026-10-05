"""Worker adapter interface. Truthful subset only — never fake success."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AdapterResult:
    ok: bool
    status: str  # CONNECTED | PARTIAL | UNAVAILABLE | SHADOW_OK | SHADOW_SKIPPED | ERROR
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] | None = None


class WorkerAdapter:
    worker_id: str = "base"
    label: str = "base"
    # Methods implemented: truthful subset of the six
    supports: frozenset[str] = frozenset()

    def health(self) -> AdapterResult:
        return AdapterResult(False, "UNAVAILABLE", "not implemented")

    def submit(self, job: dict[str, Any]) -> AdapterResult:
        return AdapterResult(False, "UNAVAILABLE", "submit not supported")

    def status(self, handle: str) -> AdapterResult:
        return AdapterResult(False, "UNAVAILABLE", "status not supported")

    def cancel(self, handle: str) -> AdapterResult:
        return AdapterResult(False, "UNAVAILABLE", "cancel not supported")

    def result(self, handle: str) -> AdapterResult:
        return AdapterResult(False, "UNAVAILABLE", "result not supported")

    def usage(self, handle: str | None = None) -> AdapterResult:
        return AdapterResult(False, "UNAVAILABLE", "usage not supported")


registry: dict[str, WorkerAdapter] = {}


def register(adapter: WorkerAdapter) -> WorkerAdapter:
    registry[adapter.worker_id] = adapter
    return adapter
