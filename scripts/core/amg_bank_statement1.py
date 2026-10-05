#!/usr/bin/env python3
"""FINANCE-CORE-AMG-PROVE-1 — AMG bank statement import (entity ENT-AMG)."""
from __future__ import annotations

import sqlite3
from typing import Any

from core import finance_core_entity as _fce
from core import ggv_bank_statement1 as _core

ENTITY = "ENT-AMG"

GgvBankStatementError = _core.GgvBankStatementError


def _scoped(fn, *args, **kwargs):
    with _fce.entity_scope(ENTITY):
        return fn(*args, **kwargs)


def ensure_schema(conn: sqlite3.Connection) -> None:
    with _fce.entity_scope(ENTITY):
        _core.ensure_schema(conn)


def import_statement(
    *,
    verified_person_id: str,
    filename: str,
    content: bytes,
    conn: sqlite3.Connection | None = None,
    bank_label: str | None = None,
) -> dict[str, Any]:
    with _fce.entity_scope(ENTITY):
        return _core.import_statement(
            verified_person_id=verified_person_id,
            filename=filename,
            content=content,
            conn=conn,
            bank_label=bank_label,
        )


def list_imports(
    *,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    with _fce.entity_scope(ENTITY):
        return _core.list_imports(verified_person_id=verified_person_id, conn=conn)


def list_transactions(
    *,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    import_id: str | None = None,
    recon_status: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    with _fce.entity_scope(ENTITY):
        return _core.list_transactions(
            verified_person_id=verified_person_id,
            conn=conn,
            import_id=import_id,
            recon_status=recon_status,
            limit=limit,
        )
