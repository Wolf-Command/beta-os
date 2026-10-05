#!/usr/bin/env python3
"""Shared Finance Core entity scope — one product, isolated entity rows."""
from __future__ import annotations

import contextvars
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DEFAULT_ENTITY = "ENT-GGV"

_entity_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "finance_core_entity", default=DEFAULT_ENTITY
)

ENTITY_CONFIG: dict[str, dict[str, object]] = {
    "ENT-GGV": {
        "label": "GGV",
        "title": "GGV Finance",
        "finance_rel": Path("Finance") / "GGV" / "Notas",
        "bank_originals": Path("state") / "ggv-bank-statements" / "originals",
        "bound": "beta-ggv-finance-nota",
        "page_prefix": "/ggv/finance",
        "api_prefix": "/api/ggv/finance",
    },
    "ENT-AMG": {
        "label": "AMG",
        "title": "AMG Finance",
        "finance_rel": Path("Finance") / "AMG" / "Notas",
        "bank_originals": Path("state") / "amg-bank-statements" / "originals",
        "bound": "beta-amg-finance-nota",
        "page_prefix": "/amg/finance",
        "api_prefix": "/api/amg/finance",
    },
    "ENT-BZG": {
        "label": "BZG",
        "title": "BZG Finance",
        "finance_rel": Path("Finance") / "BZG" / "Notas",
        "bank_originals": Path("state") / "bzg-bank-statements" / "originals",
        "bound": "beta-bzg-finance",
        "page_prefix": "/bzg/finance",
        "api_prefix": "/api/bzg/finance",
    },
}


def active_entity() -> str:
    return _entity_ctx.get()


def entity_config(entity_id: str | None = None) -> dict[str, object]:
    eid = (entity_id or active_entity()).strip()
    cfg = ENTITY_CONFIG.get(eid)
    if cfg is None:
        raise KeyError(f"unknown finance entity {eid}")
    return cfg


@contextmanager
def entity_scope(entity_id: str) -> Iterator[str]:
    token = _entity_ctx.set(entity_id.strip())
    try:
        yield entity_id.strip()
    finally:
        _entity_ctx.reset(token)
