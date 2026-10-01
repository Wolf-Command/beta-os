#!/usr/bin/env python3
"""Wave 2.01 — Uma declared cash on the night close.

The attach function needs a numeric declaration. Alchemist cash_count is
empty, so no amount is passed and no evidence row is written.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core import authority as _authority

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
ALCHEMIST_DB = Path("/Users/wolfterminal/.openclaw/workspace/alchemist/data/alchemist.db")
NIGHT_CLOSE = "VDC-25a3123a-3e26-43db-8085-10c6f208bbcd"
TODAY_CLOSE = "VDC-3353351f-3234-4f7d-acf0-a63e0e176114"
RECEIPT_EVIDENCE = "EVD-372162c1-d0ac-42a6-b5f3-5959c11f4621"
PETTY_EVIDENCE = "EVD-9498bb75-294c-4924-b30b-8cef0cab5351"


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=8)
    conn.row_factory = sqlite3.Row
    return conn


def _close_row(conn: sqlite3.Connection, close_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT close_id, business_date, state, venue_brand_id, entity_id,
               declared_cash_amount, declared_cash_evidence_id, esb_totals_json
        FROM venue_daily_closes
        WHERE close_id=?
        """,
        (close_id,),
    ).fetchone()
    if row is None:
        return None
    out = dict(row)
    raw = out.pop("esb_totals_json", None)
    try:
        totals = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        totals = {}
    out["esb_cash_from_payments"] = totals.get("cash_from_payments")
    out["esb_cash_label"] = totals.get("cash_label")
    out["esb_cash_provenance"] = totals.get("cash_provenance")
    out["esb_finished_count"] = totals.get("finished_count")
    return out


def _cash_count() -> dict[str, Any]:
    if not ALCHEMIST_DB.is_file():
        return {
            "present": False,
            "count": None,
            "state": "UNKNOWN",
            "why": "Alchemist database is missing. No till count was invented.",
        }
    conn = _ro(ALCHEMIST_DB)
    try:
        try:
            count = int(conn.execute("SELECT COUNT(*) FROM cash_count").fetchone()[0])
        except sqlite3.Error as exc:
            return {
                "present": False,
                "count": None,
                "state": "UNKNOWN",
                "why": f"cash_count could not be read ({type(exc).__name__}). No till count was invented.",
            }
    finally:
        conn.close()
    return {
        "present": True,
        "count": count,
        "path": str(ALCHEMIST_DB),
        "state": "UNAVAILABLE" if count == 0 else "PRESENT",
        "why": "Physical till rows live in Alchemist cash_count. Zero rows means no count to attach.",
    }


def _not_cash(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = []
    for evidence_id, why in (
        (RECEIPT_EVIDENCE, "Receiving document for the Uma receipt. Not a till count."),
        (PETTY_EVIDENCE, "Transport petty photo. Not a till count."),
    ):
        row = conn.execute(
            """
            SELECT evidence_id, evidence_type, governed_object_type, governed_object_id
            FROM core_evidence_records
            WHERE evidence_id=?
            """,
            (evidence_id,),
        ).fetchone()
        item = dict(row) if row else {"evidence_id": evidence_id, "present": False}
        item["used_as_declared_cash"] = False
        item["why"] = why
        rows.append(item)
    return rows


def _amount_gate(conn: sqlite3.Connection) -> dict[str, Any]:
    limit_count = int(conn.execute("SELECT COUNT(*) FROM org_authority_limits").fetchone()[0])
    petty = conn.execute(
        """
        SELECT amount, currency FROM bzg_ops_petty_movements
        WHERE movement_id='PETTY-UMA-2321496C6D'
        """
    ).fetchone()
    amount = petty["amount"] if petty else None
    currency = petty["currency"] if petty else None
    auth = _authority.within_authority(
        "PERS-MATT",
        "work.complete",
        {"entity_id": "ENT-BZG"},
        {"amount": amount, "currency": currency},
        conn=conn,
    )
    return {
        "authority_limit_count": limit_count,
        "active_threshold": None,
        "allowed": bool(auth.get("allowed")),
        "reason": auth.get("reason"),
        "detail": auth.get("detail"),
        "matched_limit": auth.get("matched_limit"),
        "threshold_invented": False,
        "probe_amount": amount,
        "probe_currency": currency,
        "why": "Limits were re-read. No org_authority_limits row was written.",
    }


def load_declared_cash() -> dict[str, Any]:
    if not CATALOG_DB.is_file():
        return {
            "ok": False,
            "pack": "WAVE2-01",
            "staff_ready": False,
            "human_proven": False,
            "error": "catalog_missing",
            "attached": False,
        }
    conn = _ro(CATALOG_DB)
    try:
        night = _close_row(conn, NIGHT_CLOSE)
        today = _close_row(conn, TODAY_CLOSE)
        others = _not_cash(conn)
        gate = _amount_gate(conn)
        requests = int(conn.execute("SELECT COUNT(*) FROM core_approval_requests").fetchone()[0])
    finally:
        conn.close()
    counts = _cash_count()
    attached = bool(night and night.get("declared_cash_evidence_id"))
    amount = night.get("declared_cash_amount") if night else None
    missing_count = counts.get("count") == 0
    if night is None:
        state = "UNKNOWN"
        why = "The night close row is missing. No close and no till were invented."
    elif missing_count and amount is None and not attached:
        state = "FAIL_CLOSED"
        why = (
            "Alchemist cash_count has no rows. The night close has no declared amount "
            "and no declared-cash evidence. ESB cash from payments was not copied onto the till."
        )
    elif attached:
        state = "ATTACHED"
        why = "A declared-cash evidence id is already on the close."
    else:
        state = "UNKNOWN"
        why = "The close and the count table disagree. No amount was written to force a match."
    return {
        "ok": True,
        "pack": "WAVE2-01",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "attached": attached,
        "till_invented": False,
        "state": state,
        "count_state": counts.get("state"),
        "why": why,
        "night_close": night,
        "today_close": today,
        "cash_count": counts,
        "not_used_as_cash": others,
        "esb_not_till": {
            "cash_from_payments": None if night is None else night.get("esb_cash_from_payments"),
            "label": None if night is None else night.get("esb_cash_label"),
            "provenance": None if night is None else night.get("esb_cash_provenance"),
            "copied_to_declared_cash": False,
        },
        "amount_gate": gate,
        "approval_request_count": requests,
        "attach_called_with_amount": False,
    }


def refuse_write() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "writes_off",
        "staff_ready": False,
        "human_proven": False,
        "writes": False,
        "till_invented": False,
        "message": "Declared cash does not write a till, an evidence row, or an authority limit.",
    }
