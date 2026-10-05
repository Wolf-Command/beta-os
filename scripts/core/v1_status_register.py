#!/usr/bin/env python3
"""V1-SWEEP-1 — Non-HR V1 status register + safe Beta board redirects.

Decision served: Matt-ordered Owner sprint V1-SWEEP-1 (2026-09-29);
inventory state/finance-core-sprint/INVENTORY-20260929.json §C + RULE exit discipline.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTER_PATH = ROOT / "state" / "finance-core-sprint" / "V1-STATUS-REGISTER-20260929.json"
PACK = "V1-SWEEP-1"

# SUPERSEDED / safe historical board aliases → Beta canonical (302). No prod.
# HR paths intentionally absent.
V1_BOARD_REDIRECTS: dict[str, str] = {
    "/atrium-finance": "/amg/finance",
    "/atrium-finance/": "/amg/finance",
    "/atrium-finance.html": "/amg/finance",
    "/dashboards/atrium-finance.html": "/amg/finance",
    "/bzg-finance": "/bzg/finance",
    "/bzg-finance.html": "/bzg/finance",
    "/dashboards/bzg-finance.html": "/bzg/finance",
    # P0 UI-REAUDIT 20260930 — orphan short-path 404 → products board (same pattern as /bzg-finance)
    "/amg-packages": "/amg-packages-products",
    "/amg-packages/": "/amg-packages-products",
    "/amg-packages.html": "/amg-packages-products",
    "/dashboards/amg-packages.html": "/amg-packages-products",
}

PAGE_PATHS = frozenset(
    {
        "/ops/v1-status",
        "/ops/v1-status/",
        "/v1-status",
        "/v1-status/",
        "/v1-status.html",
        "/dashboards/v1-status.html",
    }
)


def register_path() -> Path:
    return REGISTER_PATH


def load_register() -> dict[str, Any]:
    if not REGISTER_PATH.is_file():
        raise FileNotFoundError(f"V1 status register missing: {REGISTER_PATH}")
    data = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("register root must be object")
    return data


def board_redirect_target(path: str | None) -> str | None:
    """Return Beta Location for superseded/historical V1 board aliases."""
    raw = (path or "").split("?")[0].split("#")[0]
    if not raw:
        return None
    if not raw.startswith("/"):
        raw = "/" + raw
    if raw.startswith("/api/"):
        return None
    if raw in V1_BOARD_REDIRECTS:
        return V1_BOARD_REDIRECTS[raw]
    stripped = raw.rstrip("/") or "/"
    if stripped in V1_BOARD_REDIRECTS:
        return V1_BOARD_REDIRECTS[stripped]
    return None


def page_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    return trimmed in PAGE_PATHS or raw in PAGE_PATHS


def api_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw.rstrip("/") == "/api/ops/v1-status"


def public_payload() -> dict[str, Any]:
    reg = load_register()
    items = list(reg.get("items") or [])
    by_class: dict[str, int] = {}
    for it in items:
        cls = str(it.get("class") or "UNKNOWN")
        by_class[cls] = by_class.get(cls, 0) + 1
    return {
        "ok": True,
        "pack": PACK,
        "schema": reg.get("schema"),
        "as_of_wita": reg.get("as_of_wita"),
        "staff_ready": False,
        "human_commissioned": False,
        "hr_deferred": True,
        "prod_touched": False,
        "destructive_sor_cutover": False,
        "class_counts": reg.get("class_counts") or by_class,
        "remaining_mounted_read_only": reg.get("remaining_mounted_read_only") or [],
        "beta_redirects": reg.get("beta_redirects") or [],
        "items": items,
        "owner_addendum": reg.get("owner_addendum"),
        "cursor_did_not_auto_start_exit_report": True,
    }


def mounted_ro_paths_intact() -> list[dict[str, Any]]:
    """Evidence that MOUNTED READ-ONLY paths were not deleted."""
    reg = load_register()
    out: list[dict[str, Any]] = []
    for it in reg.get("items") or []:
        if it.get("class") != "MOUNTED READ-ONLY":
            continue
        p = it.get("evidence_path")
        exists = None
        if isinstance(p, str) and p.startswith("/"):
            exists = Path(p).exists()
        out.append(
            {
                "id": it.get("id"),
                "path": p,
                "exists": exists if exists is not None else it.get("evidence_exists"),
                "destructive": False,
            }
        )
    return out


def hr_is_deferred(reg: dict[str, Any] | None = None) -> bool:
    data = reg or load_register()
    if data.get("hr_deferred") is not True:
        return False
    for it in data.get("items") or []:
        if it.get("id") == "hr-surfaces" and it.get("class") == "HR-DEFERRED":
            return True
    return False


def superseded_have_beta_disposition(reg: dict[str, Any] | None = None) -> bool:
    data = reg or load_register()
    for it in data.get("items") or []:
        if it.get("class") != "SUPERSEDED":
            continue
        disp = (it.get("beta_disposition") or "").strip()
        if not disp:
            return False
    return True
