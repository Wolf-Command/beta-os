#!/usr/bin/env python3
"""UMA-HIST-CLOSE-QUEUE-1 — Owner historical close completion queue (Uma Blu).

Decision served: 2026-09-17 · PICK Uma Blu Daily Close (extend) + Owner backlog
queue for Sep/Oct 2026 without fake CLOSED greens or Production touch.

Canonical UI statuses from venue_daily_closes only — never infer CLOSED from ESB.
Preflight freeze per backlog date; today's petty PETTY-UMA-6D853EEAE0 never
contaminates historical dates.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from core import bzg_daily_close as _bzg
from core import uma_ops_console as _petty
from core import venue_close as _vc

PACK = "UMA-HIST-CLOSE-QUEUE-1"
BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
PREFLIGHT_PATH = (
    BETA_ROOT / "state" / "reliability" / "UMA-HIST-CLOSE-QUEUE-PREFLIGHT-2026-10-05.json"
)
FREEZE_PATH = (
    BETA_ROOT
    / "state"
    / "reliability"
    / "UMA-HIST-CLOSE-QUEUE-PREFLIGHT-FREEZE-2026-10-05.json"
)
OUTLET_UMA = _bzg.OUTLET_UMA
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"
WITA = timezone(timedelta(hours=8))

NINE_OWNER_DATES: tuple[str, ...] = (
    "2026-09-25",
    "2026-09-27",
    "2026-09-28",
    "2026-09-29",
    "2026-09-30",
    "2026-10-01",
    "2026-10-02",
    "2026-10-03",
    "2026-10-04",
)

PROTECTED_CLOSE_PREFIXES: tuple[str, ...] = (
    "VDC-470e741f",
    "VDC-64f5f529",
    "VDC-8fd544e2",
)

# 3 Oct + 4 Oct — Owner order: stay read-only; byte-unchanged.
READONLY_PROTECTED_PREFIXES: tuple[str, ...] = (
    "VDC-470e741f",
    "VDC-64f5f529",
)

# 29 Sep — protected from unsafe mutation; Owner/Finance may complete when INCOMPLETE.
COMPLETABLE_PROTECTED_PREFIXES: tuple[str, ...] = (
    "VDC-8fd544e2",
)

DO_NOT_SUBMIT_PREFIXES: tuple[str, ...] = READONLY_PROTECTED_PREFIXES

HONESTY = {
    **_vc.HONESTY,
    "pack": PACK,
    "staff_ready": False,
    "human_commissioned": False,
}


def _today_wita() -> str:
    return datetime.now(WITA).date().isoformat()


def _loads(raw: Any) -> Any:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(str(raw))
    except (TypeError, json.JSONDecodeError):
        return None


def _close_prefix(close_id: str | None) -> str:
    cid = (close_id or "").strip()
    if len(cid) >= 12:
        return cid[:12]
    return cid


def protected_close_checksums(conn: sqlite3.Connection) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if conn.row_factory is None:
        conn.row_factory = sqlite3.Row
    for prefix in PROTECTED_CLOSE_PREFIXES:
        row = conn.execute(
            """
            SELECT close_id, business_date, state, declared_cash_amount,
                   variance_cash_amount, updated_at
            FROM venue_daily_closes WHERE close_id LIKE ?
            """,
            (prefix + "%",),
        ).fetchone()
        if row:
            out[str(row["close_id"])] = {
                "business_date": row["business_date"],
                "state": row["state"],
                "declared_cash_amount": row["declared_cash_amount"],
                "variance_cash_amount": row["variance_cash_amount"],
                "updated_at": row["updated_at"],
            }
    return out


def _evidence_counts(close_id: str | None, conn: sqlite3.Connection) -> dict[str, Any]:
    if not close_id:
        return {
            "till_rows": 0,
            "edc_receipts": 0,
            "edc_with_image": 0,
            "printed_shift_receipts": 0,
            "printed_with_image": 0,
            "core_evidence": 0,
            "vision_events": 0,
        }
    cid = close_id.strip()
    till = 0
    try:
        till = int(
            conn.execute(
                "SELECT COUNT(*) FROM venue_close_till_declarations WHERE close_id=?",
                (cid,),
            ).fetchone()[0]
        )
    except sqlite3.Error:
        till = 0
    edc_receipts = 0
    edc_with_image = 0
    try:
        rows = conn.execute(
            """
            SELECT image_object_ref FROM venue_close_edc_receipts
            WHERE close_id=? AND COALESCE(evidence_role,'CURRENT')='CURRENT'
            """,
            (cid,),
        ).fetchall()
        edc_receipts = len(rows)
        edc_with_image = sum(1 for r in rows if r[0])
    except sqlite3.Error:
        pass
    printed_shift = 0
    printed_with_image = 0
    try:
        rows = conn.execute(
            """
            SELECT image_object_ref FROM venue_close_esb_closing_receipts
            WHERE close_id=?
            """,
            (cid,),
        ).fetchall()
        printed_shift = len(rows)
        printed_with_image = sum(1 for r in rows if r[0])
    except sqlite3.Error:
        pass
    vision = 0
    try:
        vision = int(
            conn.execute(
                "SELECT COUNT(*) FROM venue_close_vision_events WHERE close_id=?",
                (cid,),
            ).fetchone()[0]
        )
    except sqlite3.Error:
        vision = 0
    core = till + edc_with_image + printed_with_image
    return {
        "till_rows": till,
        "edc_receipts": edc_receipts,
        "edc_with_image": edc_with_image,
        "printed_shift_receipts": printed_shift,
        "printed_with_image": printed_with_image,
        "core_evidence": core,
        "vision_events": vision,
    }


def _closes_for_date(
    business_date: str,
    *,
    conn: sqlite3.Connection,
) -> list[dict[str, Any]]:
    rows = _vc.list_closes(
        date_from=business_date,
        date_to=business_date,
        limit=20,
        conn=conn,
    )
    return list(rows or [])


def _primary_close(closes: list[dict[str, Any]]) -> dict[str, Any] | None:
    active = [
        c
        for c in closes
        if str(c.get("state") or "").upper() != "CANCELLED"
    ]
    if not active:
        return None
    priority = {
        "EXCEPTION": 0,
        "VARIANCE_REQUIRES_POLICY": 0,
        "VERIFIED_CLOSED": 1,
        "DATA_CAPTURED": 2,
        "EVIDENCE_SUBMITTED": 2,
        "OPEN": 3,
    }
    active.sort(
        key=lambda x: (
            priority.get(str(x.get("state") or "").upper(), 9),
            str(x.get("updated_at") or ""),
        )
    )
    return active[0]


def canonical_ui_status(
    *,
    business_date: str,
    closes: list[dict[str, Any]],
    evidence: dict[str, Any] | None = None,
) -> str:
    """Map venue_daily_closes to owner queue status — no ESB-inferred CLOSED."""
    primary = _primary_close(closes)
    if primary is None:
        return "OPEN"
    state = str(primary.get("state") or "").upper()
    ev = evidence or {}
    photos_missing = int(ev.get("core_evidence") or 0) == 0
    if state == "VERIFIED_CLOSED":
        if photos_missing:
            return "MISSING EVIDENCE"
        return "CLOSED"
    if state == "OPEN":
        return "OPEN"
    if state in ("EXCEPTION", "VARIANCE_REQUIRES_POLICY"):
        return "EXCEPTION"
    if state in ("DATA_CAPTURED", "EVIDENCE_SUBMITTED", "RECONCILING"):
        return "INCOMPLETE"
    if state == "CANCELLED":
        return "OPEN"
    return "NEEDS REVIEW"


def _incomplete_close(row: dict[str, Any] | None) -> bool:
    st = str((row or {}).get("state") or "").upper()
    return st in ("OPEN", "DATA_CAPTURED", "EVIDENCE_SUBMITTED", "RECONCILING")


def can_complete_protected_close(
    verified_person_id: str | None,
    *,
    conn: sqlite3.Connection | None = None,
) -> bool:
    """Owner or authorised Finance may complete incomplete protected historical closes."""
    pid = (verified_person_id or "").strip()
    if not pid:
        return False
    from core import rbac as _rbac

    own = conn is None
    c = conn or _bzg.db_connect()
    try:
        target = _vc._rbac_target()  # noqa: SLF001
        if _rbac.can(pid, _vc.OWNER_CONTROL_PERM, target, conn=c):
            return True
        if _rbac.can(pid, "venue.close.resolve_exception", target, conn=c):
            return True
        if _rbac.can(pid, "venue.close.verify", target, conn=c):
            return True
        return False
    finally:
        if own:
            c.close()


def submit_block_reason(
    close_id: str | None,
    row: dict[str, Any] | None = None,
    *,
    verified_person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> str | None:
    """Return block message when submit/finalise must not run on protected closes."""
    cid = (close_id or (row or {}).get("close_id") or "").strip()
    prefix = _close_prefix(cid)
    if prefix in READONLY_PROTECTED_PREFIXES:
        if prefix == "VDC-470e741f":
            return "3 Oct exception close is protected — do not create or submit another close."
        if prefix == "VDC-64f5f529":
            return "4 Oct close is protected — read-only review only."
    if prefix in COMPLETABLE_PROTECTED_PREFIXES:
        own = conn is None
        c = conn or _bzg.db_connect()
        try:
            if can_complete_protected_close(verified_person_id, conn=c) and _incomplete_close(
                row
            ):
                return None
            if prefix == "VDC-8fd544e2":
                return (
                    "29 Sep close is protected — only Owner or Finance may complete this close."
                )
        finally:
            if own:
                c.close()
    return None


def open_block_reason(close_id: str | None, row: dict[str, Any] | None = None) -> str | None:
    """Block opening a duplicate close when protected exception exists."""
    cid = (close_id or (row or {}).get("close_id") or "").strip()
    prefix = _close_prefix(cid)
    st = str((row or {}).get("state") or "").upper()
    if prefix == "VDC-470e741f" and st == "EXCEPTION":
        return "3 Oct exception close exists — do not create another close."
    return None


def mutation_block_reason(
    close_id: str | None,
    row: dict[str, Any] | None = None,
    *,
    verified_person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> str | None:
    """Block capture/declare/submit mutations on protected historical closes."""
    cid = (close_id or (row or {}).get("close_id") or "").strip()
    prefix = _close_prefix(cid)
    if prefix not in PROTECTED_CLOSE_PREFIXES:
        return None
    if prefix in COMPLETABLE_PROTECTED_PREFIXES:
        own = conn is None
        c = conn or _bzg.db_connect()
        try:
            if can_complete_protected_close(verified_person_id, conn=c) and _incomplete_close(
                row
            ):
                return None
        finally:
            if own:
                c.close()
    explicit = submit_block_reason(
        close_id, row, verified_person_id=verified_person_id, conn=conn
    )
    if explicit:
        return explicit
    return "Protected close — read-only review only; mutations refused."


def row_action_label(
    status: str, *, protected: bool, owner_can_complete: bool = False
) -> str:
    st = str(status or "").upper()
    if st == "EXCEPTION":
        return "REVIEW EXCEPTION"
    if protected and not owner_can_complete:
        return "REVIEW"
    if st == "INCOMPLETE":
        return "CONTINUE"
    if st in ("OPEN",) or "MISSING" in st:
        return "OPEN"
    if st == "CLOSED":
        return "REVIEW"
    return "OPEN"


def row_summary_line(
    status: str,
    *,
    protected: bool,
    variance_cash_amount: float | int | None = None,
) -> str:
    """Staff-facing subtitle — no internal close ids."""
    st = str(status or "").upper()
    parts = [st]
    if protected:
        parts.append("Protected")
    if str(status or "").upper() == "EXCEPTION" and variance_cash_amount is not None:
        diff = abs(round(float(variance_cash_amount)))
        parts.append(f"Rp{diff:,.0f} difference".replace(",", "."))
    return " · ".join(parts)


def exception_review_payload(
    close_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Read-only exception figures from the saved close record — no mutation."""
    own = conn is None
    c = conn or _bzg.db_connect()
    try:
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise _bzg.BzgDailyCloseError(
                "close not found", code="not_found", http_status=404
            )
        declared = row.get("declared_cash_amount")
        variance = row.get("variance_cash_amount")
        expected: float | None = None
        difference: float | None = None
        if declared is not None and variance is not None:
            expected = round(float(declared) - float(variance), 2)
            difference = abs(round(float(variance), 2))
        elif variance is not None:
            difference = abs(round(float(variance), 2))
        cash_wiz: dict[str, Any] = {}
        try:
            enriched = _bzg.enrich_close(row, conn=c)
            cash_wiz = enriched.get("wizard_cash") or {}
        except (_bzg.BzgDailyCloseError, sqlite3.Error, OSError):
            cash_wiz = {}
        if expected is None and cash_wiz.get("expected_cash_in_till") is not None:
            expected = round(float(cash_wiz["expected_cash_in_till"]), 2)
        if declared is None and cash_wiz.get("cash_counted") is not None:
            declared = round(float(cash_wiz["cash_counted"]), 2)
        review = {}
        try:
            review = _bzg.wizard_review_board(close_id, conn=c)
        except (_bzg.BzgDailyCloseError, sqlite3.Error, OSError):
            review = {}
        cash_ack = _bzg.get_workflow_ack(close_id, "cash_count_confirmed", conn=c)
        return {
            **HONESTY,
            "ok": True,
            "close_id": close_id,
            "business_date": row.get("business_date"),
            "state": row.get("state"),
            "protected": _close_prefix(close_id) in PROTECTED_CLOSE_PREFIXES,
            "cash_counted": declared,
            "expected_cash_in_till": expected,
            "difference": difference,
            "variance_cash_amount": variance,
            "cash_why_note": (cash_ack or {}).get("why_note"),
            "wizard_review": review,
            "read_only": True,
            "mutations_refused": True,
        }
    finally:
        if own:
            c.close()


def _petty_for_date(business_date: str, *, conn: sqlite3.Connection) -> dict[str, Any]:
    biz = (business_date or "").strip()
    contamination: list[str] = []
    try:
        _petty.ensure_schema(conn)
        outs = _petty.list_petty_out_for_date(biz, conn=conn)
        ins = _petty.list_petty_in_for_date(biz, conn=conn)
        out_total = _petty.sum_petty_out_for_date(biz, conn=conn)
        in_total = _petty.sum_petty_in_for_date(biz, conn=conn)
    except (sqlite3.Error, RuntimeError, OSError):
        outs, ins, out_total, in_total = [], [], 0.0, 0.0
    movements: list[dict[str, Any]] = []
    for mv in outs + ins:
        mid = str(mv.get("movement_id") or mv.get("petty_movement_id") or "")
        if PROTECTED_PETTY in mid or mid == PROTECTED_PETTY:
            contamination.append(mid)
            continue
        movements.append(
            {
                "movement_id": mid,
                "direction": mv.get("direction") or ("OUT" if mv in outs else "IN"),
                "amount": mv.get("amount"),
                "purpose": mv.get("note") or mv.get("purpose") or mv.get("reason"),
                "outlet": mv.get("outlet"),
                "venue": mv.get("venue"),
            }
        )
    return {
        "business_date": biz,
        "movements": movements,
        "petty_out_total": out_total,
        "petty_in_total": in_total,
        "contamination": contamination,
        "ok_not_contaminated": PROTECTED_PETTY not in contamination
        and not any(PROTECTED_PETTY in str(m.get("movement_id") or "") for m in movements),
    }


def multi_source_preserve_29sep(
    close_id: str | None,
    *,
    conn: sqlite3.Connection,
) -> dict[str, Any] | None:
    if _close_prefix(close_id) != "VDC-8fd544e2":
        return None
    row = _vc.get_close(close_id, conn=conn)
    if not row:
        return None
    esb = row.get("esb_totals") if isinstance(row.get("esb_totals"), dict) else _loads(
        row.get("esb_totals")
    )
    warehouse_cash = (esb or {}).get("cash_from_payments")
    warehouse_bills = (esb or {}).get("finished_count")
    cfg = _bzg.OWNER_TYPED_PRINTED_SOURCES.get("2026-09-29") or {}
    fig = cfg.get("figures") or {}
    printed_cash = fig.get("cash")
    printed_bills = fig.get("bills")
    cash_delta = None
    bills_delta = None
    if warehouse_cash is not None and printed_cash is not None:
        cash_delta = round(float(warehouse_cash) - float(printed_cash), 2)
    if warehouse_bills is not None and printed_bills is not None:
        bills_delta = int(warehouse_bills) - int(printed_bills)
    return {
        "close_id": close_id,
        "warehouse_cash": warehouse_cash,
        "warehouse_bills": warehouse_bills,
        "printed_gross": fig.get("gross_sales_total"),
        "printed_cash": printed_cash,
        "printed_bills": printed_bills,
        "printed_pax": fig.get("pax"),
        "non_sales_exec_chef": fig.get("non_sales_executive_chef"),
        "discrepancy_cash": cash_delta,
        "discrepancy_bills": bills_delta,
        "auto_resolve": False,
        "do_not_submit": False,
        "owner_completable": True,
        "photo_status": "SOURCE EVIDENCE PROVIDED / FILE INGEST PENDING",
    }


def preflight_freeze_row(
    business_date: str,
    *,
    conn: sqlite3.Connection,
    preflight_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze one backlog date from saved close snapshot — never today's live ESB."""
    closes = _closes_for_date(business_date, conn=conn)
    primary = _primary_close(closes)
    close_id = primary.get("close_id") if primary else None
    ev = _evidence_counts(close_id, conn)
    petty = _petty_for_date(business_date, conn=conn)
    esb_totals = None
    esb_freeze = None
    if primary:
        raw_totals = primary.get("esb_totals")
        esb_totals = raw_totals if isinstance(raw_totals, dict) else _loads(raw_totals)
        if preflight_entry:
            esb_freeze = preflight_entry.get("esb_freeze_snapshot")
        if not esb_freeze and esb_totals:
            esb_freeze = {
                k: esb_totals.get(k)
                for k in (
                    "cash_from_payments",
                    "cash_label",
                    "cash_provenance",
                    "qris_from_payments",
                    "sales_grand_excl_other_cost",
                    "sales_bill_count_excl_other_cost",
                    "sales_pax_excl_other_cost",
                    "cancelled_count",
                    "other_cost_bill_count",
                    "cash_change_overpay",
                    "cash_sales_grand",
                    "cash_tendered_includes_change",
                )
                if esb_totals.get(k) is not None
            }
    printed = None
    warehouse = None
    discrepancy = None
    if close_id and primary:
        warehouse = _bzg.warehouse_source_board(primary)
        if business_date == "2026-09-29" and _close_prefix(close_id) == "VDC-8fd544e2":
            ms = multi_source_preserve_29sep(close_id, conn=conn)
            if ms:
                printed = {
                    "gross_sales_rp": ms.get("printed_gross"),
                    "cash_rp": ms.get("printed_cash"),
                    "bills": ms.get("printed_bills"),
                    "pax": ms.get("printed_pax"),
                    "non_sales_executive_chef_rp": ms.get("non_sales_exec_chef"),
                    "image_status": ms.get("photo_status"),
                }
                discrepancy = {
                    "has_discrepancy": True,
                    "warehouse": {
                        "cash_rp": ms.get("warehouse_cash"),
                        "finished_bills": ms.get("warehouse_bills"),
                    },
                    "printed": {
                        "cash_rp": ms.get("printed_cash"),
                        "bills": ms.get("printed_bills"),
                    },
                    "difference": {
                        "cash_rp": ms.get("discrepancy_cash"),
                        "bills": ms.get("discrepancy_bills"),
                    },
                    "auto_resolve": False,
                }
        else:
            try:
                printed = _bzg.printed_shift_source(close_id, conn=conn)
                if warehouse and printed:
                    discrepancy = _bzg.source_discrepancy_between(warehouse, printed)
            except (_bzg.BzgDailyCloseError, sqlite3.Error, OSError):
                printed = None
    edc_receipts: list[dict[str, Any]] = []
    if close_id:
        try:
            edc_receipts = _bzg.list_edc_receipts(close_id, conn=conn)
        except Exception:  # noqa: BLE001
            edc_receipts = []
    return {
        "business_date": business_date,
        "frozen_at": datetime.now(WITA).isoformat(),
        "close_id": close_id,
        "db_state": primary.get("state") if primary else None,
        "canonical_ui_status": canonical_ui_status(
            business_date=business_date, closes=closes, evidence=ev
        ),
        "esb_warehouse_freeze": esb_freeze,
        "esb_totals_full": esb_totals,
        "esb_pulled_at": primary.get("esb_pulled_at") if primary else None,
        "printed_shift": printed,
        "warehouse_source": warehouse,
        "source_discrepancy": discrepancy,
        "terminals_edc_receipts": edc_receipts,
        "cash": {
            "declared_cash_amount": primary.get("declared_cash_amount") if primary else None,
            "variance_cash_amount": primary.get("variance_cash_amount") if primary else None,
        },
        "petty": petty,
        "existing_close": primary,
        "all_records": [
            {
                "close_id": c.get("close_id"),
                "state": c.get("state"),
                "updated_at": c.get("updated_at"),
            }
            for c in closes
        ],
        "evidence": ev,
        "exceptions": {
            "state": primary.get("state") if primary else None,
            "variance_cash_amount": primary.get("variance_cash_amount") if primary else None,
        },
        "multi_source_preserve": multi_source_preserve_29sep(close_id, conn=conn),
        "petty_contamination_ok": petty.get("ok_not_contaminated"),
        "live_esb_excluded": True,
    }


def build_preflight_freeze_matrix(
    *,
    conn: sqlite3.Connection | None = None,
    write: bool = True,
) -> dict[str, Any]:
    own = conn is None
    c = conn or _bzg.db_connect()
    preflight: dict[str, Any] = {}
    if PREFLIGHT_PATH.is_file():
        preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    by_date = {
        str(x.get("business_date")): x
        for x in (preflight.get("owner_queue_nine") or [])
    }
    matrix: list[dict[str, Any]] = []
    for bd in NINE_OWNER_DATES:
        matrix.append(
            preflight_freeze_row(bd, conn=c, preflight_entry=by_date.get(bd))
        )
    out = {
        "generated_at": datetime.now(WITA).isoformat(),
        "pack": PACK,
        "slice": PACK,
        "source_preflight": str(PREFLIGHT_PATH.relative_to(BETA_ROOT)),
        "nine_dates": NINE_OWNER_DATES,
        "preflight_freeze_matrix": matrix,
        "petty_contamination_check": {
            "protected_petty": PROTECTED_PETTY,
            "ok_not_contaminated": all(
                row.get("petty_contamination_ok") for row in matrix
            ),
        },
        "staff_ready": False,
        "human_commissioned": False,
    }
    if write:
        FREEZE_PATH.parent.mkdir(parents=True, exist_ok=True)
        FREEZE_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if PREFLIGHT_PATH.is_file():
            merged = {**preflight, "preflight_freeze_matrix": matrix}
            PREFLIGHT_PATH.write_text(
                json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
    if own:
        c.close()
    return out


def _queue_row(
    business_date: str,
    *,
    conn: sqlite3.Connection,
    preflight_entry: dict[str, Any] | None = None,
    verified_person_id: str | None = None,
) -> dict[str, Any]:
    closes = _closes_for_date(business_date, conn=conn)
    primary = _primary_close(closes)
    close_id = primary.get("close_id") if primary else None
    ev = _evidence_counts(close_id, conn)
    status = canonical_ui_status(
        business_date=business_date, closes=closes, evidence=ev
    )
    prefix = _close_prefix(close_id)
    protected = prefix in PROTECTED_CLOSE_PREFIXES
    owner_can_complete = (
        protected
        and status in ("OPEN", "INCOMPLETE")
        and can_complete_protected_close(verified_person_id, conn=conn)
        and prefix in COMPLETABLE_PROTECTED_PREFIXES
    )
    do_not_submit = prefix in DO_NOT_SUBMIT_PREFIXES or (
        protected and not owner_can_complete and prefix in COMPLETABLE_PROTECTED_PREFIXES
    )
    variance = primary.get("variance_cash_amount") if primary else None
    ready = status in ("OPEN", "INCOMPLETE") and not do_not_submit and (
        not protected or owner_can_complete
    )
    flow = "readonly"
    if protected:
        if owner_can_complete and status in ("OPEN", "INCOMPLETE"):
            flow = "wizard"
        elif status == "EXCEPTION":
            flow = "exception_readonly"
        elif status == "CLOSED":
            flow = "closed_readonly"
        elif status == "MISSING EVIDENCE":
            flow = "evidence_recover"
        else:
            flow = "protected_readonly"
    elif status in ("OPEN", "INCOMPLETE"):
        flow = "wizard"
    elif status == "EXCEPTION":
        flow = "exception_readonly"
    elif status == "CLOSED":
        flow = "closed_readonly"
    elif status == "MISSING EVIDENCE":
        flow = "evidence_recover"
    return {
        "business_date": business_date,
        "status": status,
        "close_id": close_id,
        "db_state": primary.get("state") if primary else None,
        "protected": protected,
        "do_not_submit": do_not_submit,
        "owner_can_complete": owner_can_complete,
        "ready_to_close": ready,
        "flow": flow,
        "action_label": row_action_label(
            status, protected=protected, owner_can_complete=owner_can_complete
        ),
        "summary_line": row_summary_line(
            status,
            protected=protected,
            variance_cash_amount=variance,
        ),
        "variance_cash_amount": variance,
        "evidence": ev,
        "photos_missing": int(ev.get("core_evidence") or 0) == 0,
        "multi_source_preserve": multi_source_preserve_29sep(close_id, conn=conn),
        "petty_that_date": _petty_for_date(business_date, conn=conn).get("movements"),
        "all_records": [
            {
                "close_id": c.get("close_id"),
                "state": c.get("state"),
                "updated_at": c.get("updated_at"),
            }
            for c in closes
        ],
        "ui_note": (preflight_entry or {}).get("ui_note"),
    }


def owner_history_queue(
    *,
    conn: sqlite3.Connection | None = None,
    today: str | None = None,
    verified_person_id: str | None = None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or _bzg.db_connect()
    try:
        preflight: dict[str, Any] = {}
        if PREFLIGHT_PATH.is_file():
            preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
        by_date = {
            str(x.get("business_date")): x
            for x in (preflight.get("owner_queue_nine") or [])
        }
        today_iso = (today or _today_wita()).strip()
        nine = [
            _queue_row(
                bd,
                conn=c,
                preflight_entry=by_date.get(bd),
                verified_person_id=verified_person_id,
            )
            for bd in NINE_OWNER_DATES
        ]
        ready_count = sum(1 for r in nine if r.get("ready_to_close"))
        status_counts: dict[str, int] = {}
        for r in nine:
            st = str(r.get("status") or "UNKNOWN")
            status_counts[st] = status_counts.get(st, 0) + 1
        evidence_recovery = {
            "queue_dates_missing_photos": [
                r["business_date"] for r in nine if r.get("photos_missing")
            ],
            "queue_dates_with_photos": [
                r["business_date"] for r in nine if not r.get("photos_missing")
            ],
            "counts": {
                "nine_with_any_photo_evidence": sum(
                    1 for r in nine if not r.get("photos_missing")
                ),
                "nine_photos_missing_or_no_record": sum(
                    1 for r in nine if r.get("photos_missing")
                ),
            },
        }
        return {
            **HONESTY,
            "ok": True,
            "pack": PACK,
            "route": "/uma-blu-close#history-queue",
            "one_owner_link": "/uma-blu-close#history-queue",
            "today_business_date": today_iso,
            "today_separate": True,
            "nine_owner_dates": list(NINE_OWNER_DATES),
            "nine_date_statuses": {r["business_date"]: r["status"] for r in nine},
            "queue": nine,
            "status_counts": status_counts,
            "ready_to_close_now": ready_count,
            "evidence_recovery": evidence_recovery,
            "protected_closes": list(PROTECTED_CLOSE_PREFIXES),
            "protected_petty": PROTECTED_PETTY,
            "zero_closed_sep_oct": not any(r.get("status") == "CLOSED" for r in nine),
            "no_fake_closed_from_esb": True,
        }
    finally:
        if own:
            c.close()


def closed_readonly_summary(
    close_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    own = conn is None
    c = conn or _bzg.db_connect()
    try:
        row = _vc.get_close(close_id, conn=c)
        if not row:
            raise _bzg.BzgDailyCloseError("close not found", code="not_found", http_status=404)
        hist = _bzg.history_detail(close_id, conn=c)
        enriched = _bzg.enrich_close(row, conn=c)
        audit = _bzg.staff_plain_audit_trail(close_id, conn=c)
        return {
            **HONESTY,
            "ok": True,
            "close_id": close_id,
            "business_date": row.get("business_date"),
            "state": row.get("state"),
            "summary": enriched,
            "history_detail": hist,
            "audit_trail": audit,
            "reopen_available": True,
            "reopen_note": "Deliberate audited REOPEN only — original financial close preserved.",
            "evidence_recover_without_reopen": row.get("state") == "VERIFIED_CLOSED",
        }
    finally:
        if own:
            c.close()
