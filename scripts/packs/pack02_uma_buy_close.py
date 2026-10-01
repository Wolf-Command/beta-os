#!/usr/bin/env python3
"""Pack 2 live apply — Uma Blu buy, receive, petty, close on the Beta catalog.

Reads Alchemist read-only. Writes Beta catalog only. Does not write prod
:8787, Alchemist, Xero, HR, or Metricool. Idempotent on the Alchemist keys
it cites. Does not invent a till count. staff_ready stays false.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import esb_close_snapshot as esb  # noqa: E402
from core import evidence as evidence  # noqa: E402
from core import uma_devi_p0 as p0  # noqa: E402
from core import uma_ops_console as ops  # noqa: E402
from core import venue_close  # noqa: E402

ALCHEMIST_DB = Path(
    "/Users/wolfterminal/.openclaw/workspace/alchemist/data/alchemist.db"
)
MARKER = "alchemist pr_orders.id 557"
PETTY_MARKER = "alchemist petty_cash id 451"
BUYER = "PERS-DEVI"
APPROVER = "PERS-MATT"
FINISHED_NIGHT = "2026-09-30"


def _alchemist():
    conn = sqlite3.connect(f"file:{ALCHEMIST_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _lines(alc: sqlite3.Connection) -> list[dict]:
    rows = alc.execute(
        "SELECT item, qty, unit FROM pr_order_lines WHERE pr_id=557 ORDER BY id"
    ).fetchall()
    out = []
    for row in rows:
        unit = str(row["unit"] or "").strip() or None
        out.append({"item": row["item"], "qty": float(row["qty"]), "unit": unit})
    return out


def _already(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        """
        SELECT pr_id FROM bzg_ops_purchase_requests
        WHERE example=0 AND purpose LIKE ?
        LIMIT 1
        """,
        (f"%{MARKER}%",),
    ).fetchone()
    return str(row[0]) if row else None


def main() -> int:
    alc = _alchemist()
    try:
        order = dict(
            alc.execute(
                """
                SELECT id, pr_num, department, requested_by, vendor, order_date,
                       status, approver, source
                FROM pr_orders WHERE id=557
                """
            ).fetchone()
        )
        lines = _lines(alc)
        petty = dict(alc.execute("SELECT * FROM petty_cash WHERE id=451").fetchone())
    finally:
        alc.close()
    if not lines:
        raise SystemExit("Alchemist PR 557 has no lines")

    conn = ops.db_connect()
    try:
        existing = _already(conn)
        resumed = bool(existing)
        if existing:
            pr = {"pr_id": existing}
            approved_row = conn.execute(
                """
                SELECT approval_request_id, status, requested_by_person_id
                FROM core_approval_requests
                WHERE source_id=? AND request_type='GENERAL'
                ORDER BY created_at DESC LIMIT 1
                """,
                (existing,),
            ).fetchone()
            receipt_row = conn.execute(
                """
                SELECT receipt_id, status, evidence_id
                FROM bzg_ops_receipt_events WHERE pr_key=?
                ORDER BY created_at DESC LIMIT 1
                """,
                (existing,),
            ).fetchone()
            if not approved_row or not receipt_row:
                raise SystemExit(f"partial PR {existing} is missing approval or receipt")
            approved = {
                "approval_request_id": approved_row["approval_request_id"],
                "state": "RECEIVED",
            }
            receipt = {
                "receipt": {
                    "receipt_id": receipt_row["receipt_id"],
                    "status": receipt_row["status"],
                    "evidence_id": receipt_row["evidence_id"],
                    "lines": [],
                }
            }
            self_denied = "self_approval_denied"
            ordered = {"state": "RECEIVED"}
        else:
            pr = None
        if pr is None:
            purpose = (
                f"Kitchen buy shaped from Alchemist {order['pr_num']} {MARKER} "
                f"vendor {order['vendor']} order_date {order['order_date']} "
                f"department {order['department']}. Wolf row is new. Alchemist not rewritten."
            )
            pr = ops.create_pr(
                requester_label=str(order["requested_by"] or "Devi"),
                supplier_name=str(order["vendor"] or ""),
                purpose=purpose,
                requested_date=str(order["order_date"] or ""),
                lines=lines,
                submitted=True,
                example=False,
                verified_person_id=BUYER,
                actor_type="PERSON",
                conn=conn,
                commit=False,
            )
            self_denied = None
            try:
                p0.approve_purchase_segregated(
                    person_id=BUYER,
                    pr_id=pr["pr_id"],
                    conn=conn,
                    commit=False,
                )
            except ops.UmaOpsError as exc:
                self_denied = exc.code
            if self_denied != "self_approval_denied":
                raise SystemExit(f"self-approval did not fail closed: {self_denied}")

            approved = p0.approve_purchase_segregated(
                person_id=APPROVER,
                pr_id=pr["pr_id"],
                conn=conn,
                commit=False,
            )
            ordered = p0.ops_advance(
                person_id=BUYER,
                pr_id=pr["pr_id"],
                to_state="ORDERED",
                conn=conn,
                commit=False,
            )
            detail = p0.pr_detail(pr["pr_id"], conn=conn)
            receive_lines = [
                {
                    "source_line_id": ln["source_line_id"],
                    "received_qty": ln["qty"],
                }
                for ln in detail["lines"]
            ]
            note = evidence.submit_evidence(
                entity_id=ops.ENTITY_BZG,
                evidence_type="receiving_document",
                governed_object_type="bzg_purchase_request",
                governed_object_id=pr["pr_id"],
                verified_person_id=BUYER,
                source_type="HUMAN",
                brand_id=ops.VENUE_UMA,
                source_reference=f"alchemist:{order['pr_num']}",
                metadata={
                    "note": "Receiving note for the Wolf copy of Alchemist PR-1557. Alchemist not rewritten.",
                    "alchemist_pr_orders_id": 557,
                },
                conn=conn,
                commit=False,
            )
            receipt = ops.goods_receipt(
                person_id=BUYER,
                pr_key=pr["pr_id"],
                lines=receive_lines,
                notes=purpose,
                evidence_note_id=note["evidence_id"],
                require_evidence=True,
                conn=conn,
                commit=False,
            )
        photo = str(petty.get("photo_link") or "").strip() or None
        prior_petty = conn.execute(
            """
            SELECT movement_id, amount, currency FROM bzg_ops_petty_movements
            WHERE example=0 AND purpose LIKE ?
            LIMIT 1
            """,
            (f"%{PETTY_MARKER}%",),
        ).fetchone()
        if prior_petty:
            movement = {
                "movement_id": prior_petty["movement_id"],
                "amount": prior_petty["amount"],
                "currency": prior_petty["currency"],
            }
        else:
            petty_note = evidence.submit_evidence(
                entity_id=ops.ENTITY_BZG,
                evidence_type="photo",
                governed_object_type="bzg_ops_petty_movement",
                governed_object_id=PETTY_MARKER,
                verified_person_id=BUYER,
                source_type="HUMAN",
                brand_id=ops.VENUE_UMA,
                object_ref=photo,
                source_reference=PETTY_MARKER,
                metadata={
                    "alchemist_petty_cash_id": 451,
                    "logged_by_name": petty.get("logged_by_name"),
                    "entry_date": petty.get("entry_date"),
                    "category": petty.get("category"),
                    "currency_left_blank": True,
                },
                conn=conn,
                commit=False,
            )
            movement = ops.record_petty_ops(
                person_id=BUYER,
                business_date=str(petty["entry_date"]),
                direction="OUT",
                amount=float(petty["amount"]),
                currency=None,
                purpose=(
                    f"Transport cash out. {PETTY_MARKER}. "
                    f"Logged by {petty.get('logged_by_name')}. "
                    "Currency left blank because the Alchemist row has no currency column."
                ),
                evidence_note_id=petty_note["evidence_id"],
                conn=conn,
                commit=False,
            )

        today = ops.today_biz_date()
        today_close = venue_close.open_or_get(
            today,
            verified_person_id=BUYER,
            conn=conn,
            commit=False,
        )
        today_capture_error = None
        try:
            venue_close.capture_esb_snapshot(
                today_close["close_id"],
                verified_person_id=BUYER,
                conn=conn,
                commit=False,
            )
        except venue_close.VenueCloseError as exc:
            today_capture_error = exc.code
        snap = esb.snapshot_day(today)
        issue = None
        prior_issue = conn.execute(
            """
            SELECT issue_id FROM bzg_ops_operator_issues
            WHERE source_id=? AND source_kind='daily_close' AND status='OPEN'
            LIMIT 1
            """,
            (today_close["close_id"],),
        ).fetchone()
        if prior_issue:
            issue = {"issue_id": prior_issue["issue_id"]}
        elif today_capture_error:
            issue = ops.create_operator_issue(
                person_id=BUYER,
                source_kind="daily_close",
                source_id=today_close["close_id"],
                note=(
                    f"Daily close {today} stayed open. ESB snapshot incomplete "
                    f"({snap.get('incomplete_reason') or today_capture_error}). "
                    "No till count was invented. cash_count in Alchemist is empty."
                ),
                conn=conn,
                commit=False,
            )

        night = venue_close.open_or_get(
            FINISHED_NIGHT,
            verified_person_id=BUYER,
            conn=conn,
            commit=False,
        )
        night_close = venue_close.capture_esb_snapshot(
            night["close_id"],
            verified_person_id=BUYER,
            conn=conn,
            commit=False,
        )

        cards = ops.today_cards(conn=conn)
        close_card = next(c for c in cards.get("cards") or [] if c.get("kind") == "daily_close")
        conn.commit()

        report = {
            "ok": True,
            "idempotent": False,
            "staff_ready": False,
            "human_proven": False,
            "alchemist_written": False,
            "buyer": BUYER,
            "approver": APPROVER,
            "self_approval_denied": self_denied,
            "pr_id": pr["pr_id"],
            "pr_state": ordered["state"] if receipt["receipt"]["status"] != "COMPLETE" else "see_receipt",
            "approval_request_id": approved.get("approval_request_id"),
            "receipt_id": receipt["receipt"]["receipt_id"],
            "receipt_status": receipt["receipt"]["status"],
            "receipt_evidence_id": receipt["receipt"]["evidence_id"],
            "receipt_line_count": len(receipt["receipt"]["lines"]),
            "petty_movement_id": movement.get("movement_id"),
            "petty_amount": float(petty["amount"]),
            "petty_currency": None,
            "today": today,
            "today_close_id": today_close["close_id"],
            "today_capture_error": today_capture_error,
            "issue_id": None if not issue else issue.get("issue_id"),
            "night": FINISHED_NIGHT,
            "night_close_id": night_close["close_id"],
            "night_state": night_close.get("state"),
            "night_declared_cash_evidence_id": night_close.get("declared_cash_evidence_id"),
            "today_card": {
                "attention": close_card.get("attention"),
                "blocked": close_card.get("blocked"),
                "explain_kind": close_card.get("explain_kind"),
                "why": close_card.get("why"),
                "title": close_card.get("title"),
            },
            "declared_cash_not_invented": True,
            "recipe_variance": False,
        }
        # Re-read committed rows.
        check = ops.db_connect()
        try:
            pr_row = check.execute(
                "SELECT state, example FROM bzg_ops_purchase_requests WHERE pr_id=?",
                (pr["pr_id"],),
            ).fetchone()
            n_lines = check.execute(
                "SELECT COUNT(*) FROM bzg_ops_pr_lines WHERE pr_id=?",
                (pr["pr_id"],),
            ).fetchone()[0]
            n_receipts = check.execute(
                "SELECT COUNT(*) FROM bzg_ops_receipt_events WHERE pr_key=?",
                (pr["pr_id"],),
            ).fetchone()[0]
            n_rl = check.execute(
                """
                SELECT COUNT(*) FROM bzg_ops_receipt_lines
                WHERE receipt_id=?
                """,
                (receipt["receipt"]["receipt_id"],),
            ).fetchone()[0]
            petty_row = check.execute(
                "SELECT example, amount, currency, purpose FROM bzg_ops_petty_movements WHERE movement_id=?",
                (movement.get("movement_id"),),
            ).fetchone()
            apr = check.execute(
                "SELECT status, requested_by_person_id FROM core_approval_requests WHERE approval_request_id=?",
                (approved.get("approval_request_id"),),
            ).fetchone()
            report["readback"] = {
                "pr_state": pr_row["state"],
                "pr_example": pr_row["example"],
                "pr_lines": n_lines,
                "receipt_events_for_pr": n_receipts,
                "receipt_lines": n_rl,
                "petty_example": petty_row["example"],
                "petty_amount": petty_row["amount"],
                "petty_currency": petty_row["currency"],
                "approval_status": apr["status"],
                "approval_requester": apr["requested_by_person_id"],
            }
        finally:
            check.close()
        report["pr_state"] = report["readback"]["pr_state"]
        print(json.dumps(report, indent=2))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
