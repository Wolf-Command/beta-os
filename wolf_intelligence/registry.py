"""Provider / model registry. Capability scores are UNKNOWN until benchmarked."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import CONFIG_DIR, ensure_dirs

PROVIDERS_PATH = CONFIG_DIR / "providers.json"
MODELS_PATH = CONFIG_DIR / "models.json"


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_providers() -> dict[str, Any]:
    ensure_dirs()
    return _load(PROVIDERS_PATH)


def load_models() -> dict[str, Any]:
    ensure_dirs()
    return _load(MODELS_PATH)


def list_models(*, provider: str | None = None, billing: str | None = None) -> list[dict[str, Any]]:
    data = load_models()
    models = list(data.get("models") or [])
    if provider:
        models = [m for m in models if m.get("provider") == provider]
    if billing:
        models = [m for m in models if m.get("billing") == billing]
    return models


def get_model(model_id: str) -> dict[str, Any] | None:
    for m in list_models():
        if m.get("id") == model_id:
            return m
    return None


def capability_score(model_id: str, capability: str) -> str | float:
    """Never invent scores — UNKNOWN until benchmark harness writes evidence."""
    m = get_model(model_id)
    if not m:
        return "UNKNOWN"
    scores = (m.get("capability_scores") or {})
    val = scores.get(capability)
    if val is None or val == "UNKNOWN":
        return "UNKNOWN"
    return val
