#!/usr/bin/env python3
"""Wave 2.06 — Month-end to shareholder pack. Read only.

Historical July and August boards stay on the V1 disk. They are not a live
P&L. Beta has no copy. Xero is absent. Uma daily closes are not a
shareholder pack.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
V1_DASH = Path("/Users/wolfterminal/.openclaw/workspace/wolf-system/dashboards")
BETA_DASH = BETA_ROOT / "dashboards"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
XERO_MATRIX = (
    BETA_ROOT / "state/final-completion/beta-house-20261001/CONNECTION-TRUTH-MATRIX.json"
)

BOARDS = (
    {
        "id": "july-2026",
        "file": "bzg-july-2026.html",
        "role": "PRESERVE",
    },
    {
        "id": "august-2026",
        "file": "bzg-august-2026.html",
        "role": "PRESERVE",
    },
)


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=8)
    conn.row_factory = sqlite3.Row
    return conn


def _title(path: Path) -> str | None:
    if not path.is_file():
        return None
    head = path.read_text(encoding="utf-8", errors="replace")[:8000]
    match = re.search(r"<title>(.*?)</title>", head, re.I | re.S)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _boards() -> list[dict[str, Any]]:
    out = []
    for spec in BOARDS:
        v1 = V1_DASH / spec["file"]
        beta = BETA_DASH / spec["file"]
        out.append(
            {
                "id": spec["id"],
                "file": spec["file"],
                "role": spec["role"],
                "v1_present": v1.is_file(),
                "beta_present": beta.is_file(),
                "title": _title(v1),
                "live_replacement": False,
                "figures_copied": False,
            }
        )
    return out


def _index() -> dict[str, Any]:
    name = "bzg-shareholder-reports.html"
    v1 = V1_DASH / name
    beta = BETA_DASH / name
    links = {"july": False, "august": False}
    if v1.is_file():
        text = v1.read_text(encoding="utf-8", errors="replace")
        links["july"] = "bzg-july-2026.html" in text
        links["august"] = "bzg-august-2026.html" in text
    return {
        "file": name,
        "v1_present": v1.is_file(),
        "beta_present": beta.is_file(),
        "title": _title(v1),
        "links_historical_boards": links["july"] and links["august"],
        "pack_completed": False,
        "live_replacement": False,
        "why": "The V1 page is an index of the historical boards. Beta has no copy and no completed pack.",
    }


def _closes() -> dict[str, Any]:
    if not CATALOG_DB.is_file():
        return {"present": False, "count": None, "why": "Beta catalog is missing."}
    conn = _ro(CATALOG_DB)
    try:
        names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "venue_daily_closes" not in names:
            return {"present": False, "count": None, "why": "venue_daily_closes is missing."}
        rows = conn.execute(
            """
            SELECT close_id, business_date, state, venue_brand_id, declared_cash_evidence_id
            FROM venue_daily_closes
            ORDER BY business_date
            """
        ).fetchall()
    finally:
        conn.close()
    return {
        "present": True,
        "count": len(rows),
        "rows": [
            {
                "close_id": row["close_id"],
                "business_date": row["business_date"],
                "state": row["state"],
                "venue_brand_id": row["venue_brand_id"],
                "declared_cash_evidence_id": row["declared_cash_evidence_id"],
                "month_end_pack": False,
            }
            for row in rows
        ],
        "figures_copied": False,
        "why": "These are Uma daily closes. They are not a month-end shareholder pack.",
    }


def _books() -> dict[str, Any]:
    if not CATALOG_DB.is_file():
        return {"present": False, "why": "Beta catalog is missing."}
    conn = _ro(CATALOG_DB)
    try:
        names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        notas = int(conn.execute("SELECT COUNT(*) FROM ggv_notas").fetchone()[0]) if "ggv_notas" in names else None
        invoices = (
            int(conn.execute("SELECT COUNT(*) FROM ggv_invoices").fetchone()[0]) if "ggv_invoices" in names else None
        )
        xero_tables = sorted(name for name in names if "xero" in name.lower())
    finally:
        conn.close()
    return {
        "ggv_notas": notas,
        "ggv_invoices": invoices,
        "xero_tables": xero_tables,
        "xero_book": False,
        "why": "Catalog row counts are not a Xero book and not a P&L.",
    }


def _xero() -> dict[str, Any]:
    if not XERO_MATRIX.is_file():
        return {"present": False, "precise_state": "UNKNOWN", "why": "Connection matrix is missing."}
    try:
        data = json.loads(XERO_MATRIX.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"present": False, "precise_state": "UNKNOWN", "why": f"Matrix unreadable ({type(exc).__name__})."}
    found = None
    for item in data.get("integrations") or []:
        if isinstance(item, dict) and item.get("id") == "Xero":
            found = item
            break
    if found is None:
        return {
            "present": True,
            "precise_state": "UNKNOWN",
            "as_of_wita": data.get("generated_at_wita"),
            "why": "The matrix has no Xero row.",
        }
    return {
        "present": True,
        "precise_state": found.get("precise_state"),
        "beta_connected": found.get("BETA_CONNECTED"),
        "credential_found": found.get("CREDENTIAL_FOUND"),
        "live_read_tested": found.get("LIVE_READ_TESTED"),
        "write_capability": found.get("WRITE_CAPABILITY_AVAILABLE"),
        "last_success": found.get("LAST_SUCCESS"),
        "as_of_wita": data.get("generated_at_wita"),
        "enabled": False,
        "why": "Xero stays absent. This desk does not enable it.",
    }


def load_monthend() -> dict[str, Any]:
    xero = _xero()
    return {
        "ok": True,
        "pack": "WAVE2-06",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "xero_enabled": False,
        "state": "SHELL",
        "chain": "BROKEN",
        "pnl": None,
        "pnl_invented": False,
        "pack_completed": False,
        "historical_boards": _boards(),
        "shareholder_index": _index(),
        "daily_closes": _closes(),
        "books": _books(),
        "xero": xero,
        "why": (
            "Historical boards stay preserved on the V1 disk. "
            "Uma daily closes are not a month-end pack. Xero is absent. No P&L was copied."
        ),
    }


def refuse_write() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "writes_off",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "xero_enabled": False,
        "pnl_invented": False,
        "message": "Month-end does not write a P&L, a close figure, or a Xero connection.",
    }
