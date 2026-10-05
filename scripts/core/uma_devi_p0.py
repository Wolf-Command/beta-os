#!/usr/bin/env python3
"""Devi feedback P0 — close history, PR detail, append-only receive (Beta).

Slice BF-devi-feedback-p0-20260919.

Extends Uma commissioning. Does not finish it. Does not grant payment
approval. Does not write Alchemist. Receipt rows are append-only.
Receive POST fails closed when RBAC has no venue receive permission.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from core import evidence as _evidence
from core import rbac as _rbac
from core import uma_alchemist_ro as _alc
from core import uma_ops_console as _ops
from core import venue_close as _venue_close

EMPTY_PREVIOUS = "No previous closes recorded in Wolf yet"
WOLF_VERIFIED_CHIP = "Wolf-verified"
EXISTING_CHIP = "Existing"
WAITING_TEMPLATE = "Waiting on {role} — no action needed from you"
CAN_ACT_LABEL = "You can act"
POLICY_REQUIRED_LABEL = "Policy required"
PR_STATE_LABELS: dict[str, str] = {
    "DRAFT": "Draft — not submitted",
    "REQUESTED": "Waiting approval",
    "APPROVED": "Approved",
    "ORDERED": "Ordered",
    "PARTIALLY_RECEIVED": "Part received",
    "RECEIVED": "Received",
    "BILL_RECEIVED": "Bill received",
    "PAYMENT_REQUESTED": "Payment requested",
    "PAYMENT_APPROVED": "Payment approved",
    "PAID_CLAIMED": "Paid claimed — not verified",
    "PAYMENT_VERIFIED": "Payment verified",
    "CLOSED": "Closed",
    "POLICY_REQUIRED": POLICY_REQUIRED_LABEL,
    "REJECTED": "Rejected",
    "OPS_CLOSED": "Closed for operations — payment not executed",
}
ACTION_RECEIVE = "Receive goods"
ACTION_PERFORM_CLOSE = "Perform close"
ACTION_RESOLVE = "Resolve exception"
ACTION_OPEN_EXCEPTION = "Open exception"
ACTION_APPROVE = "Approve request"
ACTION_SUBMIT = "Submit request"
ACTION_ORDER = "Mark ordered"
# Waiting tokens that map to a role. A single other active assignee becomes the person.
_WAIT_ROLE_IDS = {
    "Head of F&B": ("ROLE-BZG-HFB",),
    "closer": ("ROLE-BZG-CLOSER",),
}
CLOSE_DENIED = (
    "You cannot open, submit, or reconcile this close. "
    "Waiting on closer — no action needed from you."
)
UMA_TARGET = {"entity_id": "ENT-BZG", "brand_id": "BZG-UMA"}
EVIDENCE_TYPE = "receiving_document"
RESOURCE_RECEIPT = "bzg_ops_receipt"
QTY_EPS = 1e-6

# Exact codes first. Then any ACTIVE venue./bzg. code whose action is receive.
# payment_approve is never a receive permission.
_RECEIVE_EXACT = (
    "venue.receive",
    "venue.goods.receive",
    "bzg.pr.receive",
    "bzg.goods.receive",
    "bzg.receive",
)

_CLOSE_AUDIT = {
    "venue_close.open": "Close opened",
    "venue_close.esb_captured": "ESB snapshot captured",
    "venue_close.declared_cash": "Declared cash recorded",
    "venue_close.reconcile": "Close reconciled",
    "venue_close.exception_opened": "Exception opened",
    "venue_close.exception_resolved": "Exception resolved",
    "venue_close.verify": "Close verified",
}

_INFORMATIONAL = frozenset({"history", "issues"})


def waiting_copy(role: str) -> str:
    return WAITING_TEMPLATE.format(role=(role or "policy").strip() or "policy")


def discover_receive_permission(conn: sqlite3.Connection) -> str | None:
    """ACTIVE venue/bzg receive code, or None. Does not insert a permission."""
    try:
        rows = conn.execute(
            """
            SELECT code, resource, action
            FROM org_permissions
            WHERE status='ACTIVE'
            """
        ).fetchall()
    except sqlite3.Error:
        return None
    by_code = {str(r["code"]): r for r in rows if r["code"]}
    for code in _RECEIVE_EXACT:
        if code in by_code:
            return code
    for code, row in by_code.items():
        low = code.lower()
        if "payment" in low:
            continue
        action = str(row["action"] or "").lower()
        resource = str(row["resource"] or "").lower()
        if action == "receive" and resource.startswith(("venue", "bzg")):
            return code
        if low.startswith(("venue.", "bzg.")) and "receive" in low:
            return code
    return None


def ensure_receipt_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS bzg_ops_receipt_events (
          receipt_id TEXT PRIMARY KEY,
          venue TEXT NOT NULL,
          pr_key TEXT NOT NULL,
          pr_num TEXT,
          alchemist_pr_id TEXT,
          provenance_json TEXT,
          receiver_person_id TEXT NOT NULL,
          status TEXT NOT NULL CHECK (status IN ('PARTIAL', 'COMPLETE')),
          notes TEXT,
          evidence_id TEXT,
          corrects_receipt_id TEXT,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_bzg_ops_receipt_pr
          ON bzg_ops_receipt_events(venue, pr_key);
        CREATE TABLE IF NOT EXISTS bzg_ops_receipt_lines (
          line_id TEXT PRIMARY KEY,
          receipt_id TEXT NOT NULL,
          source_line_id TEXT NOT NULL,
          item TEXT,
          unit TEXT,
          requested_qty REAL,
          received_qty REAL NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_bzg_ops_receipt_line
          ON bzg_ops_receipt_lines(receipt_id);
        CREATE TABLE IF NOT EXISTS bzg_ops_receipt_slots (
          receipt_id TEXT PRIMARY KEY,
          evidence_note_id TEXT,
          evidence_photo_id TEXT,
          variance_flag INTEGER NOT NULL DEFAULT 0,
          shortfall_json TEXT,
          created_at TEXT NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS trg_bzg_receipt_events_no_update
        BEFORE UPDATE ON bzg_ops_receipt_events
        BEGIN
          SELECT RAISE(ABORT, 'receipt events are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS trg_bzg_receipt_events_no_delete
        BEFORE DELETE ON bzg_ops_receipt_events
        BEGIN
          SELECT RAISE(ABORT, 'receipt events are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS trg_bzg_receipt_lines_no_update
        BEFORE UPDATE ON bzg_ops_receipt_lines
        BEGIN
          SELECT RAISE(ABORT, 'receipt lines are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS trg_bzg_receipt_lines_no_delete
        BEFORE DELETE ON bzg_ops_receipt_lines
        BEGIN
          SELECT RAISE(ABORT, 'receipt lines are append-only');
        END;
        """
    )


def _person_label(conn: sqlite3.Connection, person_id: str | None) -> str | None:
    pid = (person_id or "").strip()
    if not pid:
        return None
    try:
        row = conn.execute(
            "SELECT display_name FROM org_persons WHERE person_id=?",
            (pid,),
        ).fetchone()
    except sqlite3.Error:
        return None
    if not row:
        return None
    name = str(row["display_name"] or "").strip()
    return name or None


def _caps(person_id: str, conn: sqlite3.Connection) -> dict[str, bool]:
    pid = (person_id or "").strip()
    receive_code = discover_receive_permission(conn)

    def allow(code: str | None) -> bool:
        if not pid or not code:
            return False
        return _rbac.can(pid, code, UMA_TARGET, conn=conn)

    submit = allow("venue.close.submit")
    resolve = allow("venue.close.resolve_exception")
    reassign = allow("venue.close.reassign")
    owner_control = allow("venue.close.owner_control")
    return {
        "read": allow("venue.close.read"),
        "submit": submit,
        "open": submit,
        "capture": submit,
        "declare": submit,
        "reconcile": submit,
        "resolve": resolve,
        "exception": submit or resolve,
        "verify": allow("venue.close.verify"),
        "reassign": reassign,
        "takeover": reassign,
        "owner_control": owner_control,
        "reopen": owner_control,
        "cancel_close": owner_control,
        "unlock_abandoned": owner_control,
        "return_for_correction": owner_control,
        "override_lock": owner_control,
        "correct_assignment": owner_control,
        "payment_approve": allow("bzg.pr.payment_approve"),
        "receive": allow(receive_code),
        "receive_permission": receive_code,
        "create": allow("bzg.pr.create") or allow("work.create"),
        "submit_pr": allow("work.update"),
        "approve_ops": allow("work.complete"),
        "order": allow("work.update"),
        "close_ops": allow("work.complete"),
        "petty": allow("petty_cash.record_out"),
        "petty_record_out": allow("petty_cash.record_out"),
        "petty_record_in": allow("petty_cash.record_in"),
        "petty_reconcile": allow("petty_cash.reconcile"),
        "issue": allow("work.create"),
        # Sprint2 P1 operator depth — PR detail/correction affordance.
        "pr_operator": allow(_ops.PERM_PR_OPERATOR) or allow("work.update"),
    }


def close_capabilities(person_id: str, *, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    c = conn or _ops.db_connect()
    try:
        caps = _caps(person_id, c)
        denied = None if caps["submit"] else CLOSE_DENIED
        return {
            "ok": True,
            "person_id": (person_id or "").strip() or None,
            "can": {k: v for k, v in caps.items() if k != "receive_permission"},
            "receive_permission": caps.get("receive_permission"),
            "payment_approve_granted": False if not caps["payment_approve"] else True,
            "denied_explanation": denied,
            "alchemist_cash_count_used": False,
        }
    finally:
        if own:
            c.close()


def _esb_present(row: dict[str, Any]) -> dict[str, Any] | None:
    totals = row.get("esb_totals")
    if not isinstance(totals, dict) or not totals:
        return None
    kept = {k: v for k, v in totals.items() if v is not None}
    return kept or None


def summarise_close(row: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    """Stored close fields only. No cash_count. No invented operator name."""
    out: dict[str, Any] = {
        "close_id": row.get("close_id"),
        "business_date": row.get("business_date"),
        "state": row.get("state"),
    }
    if row.get("declared_cash_amount") is not None:
        out["declared_cash_amount"] = row.get("declared_cash_amount")
    if row.get("variance_cash_amount") is not None:
        out["variance_cash_amount"] = row.get("variance_cash_amount")
        out["variance_flag"] = True
    if row.get("state") in ("EXCEPTION", "VARIANCE_REQUIRES_POLICY"):
        out["exception_flag"] = True
    esb = _esb_present(row)
    if esb:
        out["esb_totals"] = esb
    if row.get("fingerprint_stale"):
        out["fingerprint_stale"] = True
    labels: dict[str, str] = {}
    for src, dest in (
        ("submitted_by_person_id", "submitted_by"),
        ("resolved_by_person_id", "resolved_by"),
        ("verified_by_person_id", "verified_by"),
    ):
        label = _person_label(conn, row.get(src))
        if label:
            labels[dest] = label
    if labels:
        out["operator_labels"] = labels
    if row.get("state") == "VERIFIED_CLOSED":
        out["chip"] = WOLF_VERIFIED_CHIP
    return out


def previous_closes(
    *,
    exclude_business_date: str | None = None,
    limit: int = 50,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Newest-first venue_daily_closes. Honest empty. Never reads cash_count."""
    own = conn is None
    c = conn or _ops.db_connect()
    try:
        rows = _venue_close.list_closes(limit=limit, conn=c)
        skip = (exclude_business_date or "").strip()
        if skip:
            rows = [r for r in rows if (r.get("business_date") or "") != skip]
        summarised = [summarise_close(r, c) for r in rows]
        empty = len(summarised) == 0
        return {
            "ok": True,
            "closes": summarised,
            "count": len(summarised),
            "empty": empty,
            "empty_message": EMPTY_PREVIOUS if empty else None,
            "source": "venue_daily_closes",
            "alchemist_cash_count_used": False,
        }
    finally:
        if own:
            c.close()


def _evidence_refs(row: dict[str, Any]) -> list[dict[str, str]]:
    refs = []
    for field in ("declared_cash_evidence_id", "resolve_evidence_id"):
        evid = (row.get(field) or "").strip() if isinstance(row.get(field), str) else row.get(field)
        if evid:
            refs.append({"field": field, "evidence_id": str(evid)})
    return refs


def _audit_sentences(conn: sqlite3.Connection, close_id: str) -> list[dict[str, Any]]:
    try:
        rows = conn.execute(
            """
            SELECT action, occurred_at, result, evidence_reference, actor_person_id
            FROM core_audit_events
            WHERE resource_type='venue_daily_close' AND resource_id=?
            ORDER BY occurred_at ASC, recorded_at ASC
            """,
            (close_id,),
        ).fetchall()
    except sqlite3.Error:
        return []
    out = []
    for row in rows:
        action = str(row["action"] or "")
        text = _CLOSE_AUDIT.get(action) or action
        when = str(row["occurred_at"] or "")
        day = when[:10] if len(when) >= 10 else ""
        sentence = f"{day} · {text}" if day else text
        label = _person_label(conn, row["actor_person_id"])
        if label:
            sentence = f"{sentence} · {label}"
        item: dict[str, Any] = {
            "when": when or None,
            "action": action,
            "sentence": sentence,
        }
        evid = (row["evidence_reference"] or "").strip() if row["evidence_reference"] else ""
        if evid:
            item["evidence_reference"] = evid
        out.append(item)
    return out


def close_detail(close_id: str, *, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    own = conn is None
    c = conn or _ops.db_connect()
    try:
        row = _venue_close.get_close((close_id or "").strip(), conn=c)
        if not row:
            return None
        chip = WOLF_VERIFIED_CHIP if row.get("state") == "VERIFIED_CLOSED" else None
        labels: dict[str, str] = {}
        for src, dest in (
            ("submitted_by_person_id", "submitted_by"),
            ("resolved_by_person_id", "resolved_by"),
            ("verified_by_person_id", "verified_by"),
        ):
            label = _person_label(c, row.get(src))
            if label:
                labels[dest] = label
        # Finance Control history board — saved snapshot / dual source (no live mutate).
        history = None
        try:
            from core import bzg_daily_close as _bzg_dc

            history = _bzg_dc.history_detail(row["close_id"], conn=c)
        except Exception:  # noqa: BLE001
            history = None
        return {
            "close": row,
            "summary": summarise_close(row, c),
            "operator_labels": labels,
            "evidence_refs": _evidence_refs(row),
            "audit_sentences": _audit_sentences(c, row["close_id"]),
            "chip": chip,
            "alchemist_cash_count_used": False,
            "three_objects": _venue_close.three_close_objects(row),
            "snapshot_frozen": bool(row.get("esb_fingerprint_sha256")),
            "history_detail": history,
        }
    finally:
        if own:
            c.close()


def _drop_nulls(row: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    out = {}
    for key in keys:
        val = row.get(key)
        if val is None or val == "":
            continue
        out[key] = val
    return out


def pr_detail(key: str, *, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    """Merge Wolf PR and Alchemist projection. No invented amount. No Alchemist write."""
    wanted = (key or "").strip()
    if not wanted:
        return None
    own = conn is None
    c = conn or _ops.db_connect()
    try:
        _ops.ensure_schema(c)
        wolf = _ops.get_pr(wanted, conn=c)
        legacy = _alc.project_pr_by_key(wanted)
        if wolf is None and legacy is None:
            return None
        detail: dict[str, Any] = {
            "wolf_verified": False,
            "payment_approve": False,
        }
        if legacy:
            detail.update(
                _drop_nulls(
                    legacy,
                    (
                        "pr_num",
                        "supplier_name",
                        "department",
                        "requester_label",
                        "requested_date",
                        "state",
                        "display_status",
                        "alchemist_status",
                        "purpose",
                        "provenance",
                        "record_origin",
                    ),
                )
            )
            detail["legacy"] = True
            detail["chip"] = EXISTING_CHIP
            detail["pr_id"] = legacy.get("pr_id")
            if legacy.get("expected_value") is not None:
                detail["expected_value"] = legacy.get("expected_value")
            lines = legacy.get("lines") or []
            detail["lines"] = lines
            if legacy.get("alchemist_pr_id") is not None:
                detail["alchemist_pr_id"] = legacy.get("alchemist_pr_id")
            if legacy.get("alchemist_status"):
                detail["source_status_note"] = (
                    "Existing record status is not a Wolf verification."
                )
        if wolf:
            wolf_bits = _drop_nulls(
                wolf,
                (
                    "pr_id",
                    "supplier_name",
                    "requester_label",
                    "requested_date",
                    "state",
                    "purpose",
                    "currency",
                    "bill_reference",
                ),
            )
            for field, value in wolf_bits.items():
                if field == "state" and legacy and legacy.get("state"):
                    detail["wolf_state"] = value
                    continue
                detail[field] = value
            if wolf.get("expected_value") is not None:
                detail["expected_value"] = wolf.get("expected_value")
            detail["wolf"] = True
            if not legacy:
                detail["legacy"] = False
                detail["lines"] = _ops.list_pr_lines(str(wolf.get("pr_id") or wanted), conn=c)
                detail["display_status"] = wolf.get("state")
        if "expected_value" not in detail:
            detail["expected_value"] = None
        detail["lines"] = _attach_wolf_received(detail.get("lines") or [], detail, c)
        st = str(detail.get("state") or detail.get("wolf_state") or "").strip().upper()
        if st and not detail.get("display_status"):
            detail["display_status"] = PR_STATE_LABELS.get(st, st.title().replace("_", " "))
        _attach_pr_business_and_po(detail, c)
        return detail
    finally:
        if own:
            c.close()


def _attach_pr_business_and_po(detail: dict[str, Any], conn: sqlite3.Connection) -> None:
    """Outlet-derived business label for legacy rows; PO back-link when saved."""
    from core import bzg_outlet_registry as _outlets

    oid = (detail.get("outlet_id") or "").strip()
    if oid:
        outlet = _outlets.get_outlet(oid, conn=conn)
        if outlet:
            detail.setdefault("outlet_display_name", outlet.get("display_name"))
            if not (detail.get("entity_id") or "").strip():
                detail["business_label"] = outlet.get("display_name") or "Uma Blu"
            else:
                ent_id = str(detail.get("entity_id") or "").strip()
                row = conn.execute(
                    "SELECT display_name FROM org_entities WHERE entity_id=?",
                    (ent_id,),
                ).fetchone()
                detail["business_label"] = (
                    str(row[0]).strip() if row and row[0] else outlet.get("display_name")
                )
    pr_key = str(detail.get("pr_id") or detail.get("pr_num") or "").strip()
    if pr_key:
        try:
            po = conn.execute(
                "SELECT po_id FROM bzg_ops_purchase_orders WHERE pr_id=?",
                (pr_key,),
            ).fetchone()
        except sqlite3.OperationalError:
            po = None
        if po:
            detail["linked_po_id"] = str(po["po_id"])
            detail["linked_po_href"] = "/bzg/uma-blu/purchase-orders"


def _pr_match_keys(detail: dict[str, Any]) -> list[str]:
    keys = []
    for field in ("pr_num", "pr_id", "alchemist_pr_id"):
        val = detail.get(field)
        if val is None or val == "":
            continue
        keys.append(str(val))
    return keys


def _wolf_received_by_line(conn: sqlite3.Connection, keys: list[str]) -> dict[str, float]:
    if not keys:
        return {}
    ensure_receipt_schema(conn)
    placeholders = ",".join("?" * len(keys))
    rows = conn.execute(
        f"""
        SELECT l.source_line_id, SUM(l.received_qty) AS qty
        FROM bzg_ops_receipt_lines l
        JOIN bzg_ops_receipt_events e ON e.receipt_id = l.receipt_id
        WHERE e.venue=?
          AND (
            e.pr_key IN ({placeholders})
            OR IFNULL(e.pr_num, '') IN ({placeholders})
            OR IFNULL(e.alchemist_pr_id, '') IN ({placeholders})
          )
        GROUP BY l.source_line_id
        """,
        (_ops.VENUE_UMA, *keys, *keys, *keys),
    ).fetchall()
    return {str(r["source_line_id"]): float(r["qty"] or 0) for r in rows}


def _attach_wolf_received(
    lines: list[dict[str, Any]],
    detail: dict[str, Any],
    conn: sqlite3.Connection,
) -> list[dict[str, Any]]:
    got = _wolf_received_by_line(conn, _pr_match_keys(detail))
    out = []
    for line in lines:
        row = dict(line)
        sid = str(row.get("source_line_id") or "")
        wolf_qty = got.get(sid, 0.0)
        if sid in got:
            row["wolf_received_qty"] = wolf_qty
        qty = row.get("qty")
        if row.get("interpretable") and qty is not None:
            outstanding = float(qty) - wolf_qty
            if outstanding < 0 and abs(outstanding) < QTY_EPS:
                outstanding = 0.0
            row["wolf_outstanding_qty"] = outstanding
        out.append(row)
    return out


def pr_actions(person_id: str, *, conn: sqlite3.Connection) -> dict[str, Any]:
    caps = _caps(person_id, conn)
    actions: dict[str, Any] = {
        "create_pr": bool(caps.get("create")),
        "submit": bool(caps.get("submit_pr")),
        "approve_ops": bool(caps.get("approve_ops")),
        "reject_ops": bool(caps.get("approve_ops")),
        "order": bool(caps.get("order")),
        "close_ops": bool(caps.get("close_ops")),
        "petty_record": bool(caps.get("petty")),
        "petty_record_out": bool(caps.get("petty_record_out")),
        "petty_record_in": bool(caps.get("petty_record_in")),
        "petty_reconcile": bool(caps.get("petty_reconcile")),
        "petty_count": bool(caps.get("petty_reconcile")),
        "create_issue": bool(caps.get("issue")),
        "perform_close": bool(caps.get("submit")),
        "payment_approve": False,
        "payment_execution": False,
        "verify_close": False,
        "progress": False,
    }
    if caps["receive"]:
        actions["receive"] = True
    else:
        actions["receive"] = False
        actions["receive_waiting"] = waiting_copy("policy" if not caps.get("receive_permission") else "receiver")
    actions["pr_operator"] = bool(caps.get("pr_operator"))
    actions["correction"] = bool(caps.get("pr_operator"))
    if not caps.get("pr_operator"):
        actions["pr_operator_waiting"] = waiting_copy("staff")
    if not caps["submit_pr"]:
        actions["submit_waiting"] = waiting_copy("staff")
    if not caps["approve_ops"]:
        actions["approve_waiting"] = waiting_copy("approver")
        actions["reject_waiting"] = waiting_copy("approver")
    actions["payment_waiting"] = waiting_copy("finance")
    return actions


def _waiting_subject(conn: sqlite3.Connection, role: str, person_id: str) -> str:
    """Role label, or the one other active person's name. Never invents a name."""
    token = (role or "").strip() or "policy"
    role_ids = _WAIT_ROLE_IDS.get(token)
    if not role_ids:
        return token
    placeholders = ",".join("?" * len(role_ids))
    try:
        rows = conn.execute(
            f"""
            SELECT DISTINCT pe.person_id, pe.display_name
            FROM org_assignments a
            JOIN org_positions po ON po.position_id = a.position_id
            JOIN org_persons pe ON pe.person_id = a.person_id
            WHERE po.role_id IN ({placeholders})
              AND a.status = 'ACTIVE'
              AND a.end_at IS NULL
              AND pe.status = 'ACTIVE'
            """,
            role_ids,
        ).fetchall()
    except sqlite3.Error:
        return token
    viewer = (person_id or "").strip()
    names: list[str] = []
    seen: set[str] = set()
    for row in rows:
        pid = str(row[0] or "")
        if not pid or pid == viewer or pid in seen:
            continue
        seen.add(pid)
        name = str(row[1] or "").strip()
        if name:
            names.append(name)
    if len(names) == 1:
        return names[0]
    return token


def _first_pr_href(card: dict[str, Any], fallback: str = "/bzg/uma-blu/bills") -> str:
    """Deep-link to the first live PR on the card. List href is fallback only."""
    for item in card.get("items") or []:
        if item.get("example"):
            continue
        if item.get("href"):
            return str(item["href"])
        key = str(item.get("pr_id") or item.get("pr_num") or "").strip()
        if key:
            return f"/bzg/uma-blu/bills/{key}"
    return str(card.get("href") or fallback)


def _perform_action(kind: str, card: dict[str, Any], caps: dict[str, Any]) -> dict[str, str] | None:
    """Verb the operator can perform. Verify is never a Today action."""
    if kind == "ordered_not_received" and caps.get("receive"):
        return {
            "label": ACTION_RECEIVE,
            "href": _first_pr_href(card),
        }
    if kind == "awaiting_remainder" and caps.get("receive"):
        return {
            "label": ACTION_RECEIVE,
            "href": _first_pr_href(card),
        }
    if kind == "prs_waiting_approval" and caps.get("approve_ops"):
        return {
            "label": ACTION_APPROVE,
            "href": _first_pr_href(card),
        }
    if kind == "draft_pr" and caps.get("submit_pr"):
        return {
            "label": ACTION_SUBMIT,
            "href": _first_pr_href(card),
        }
    if kind != "daily_close":
        return None
    close = card.get("close") or {}
    status = str(close.get("status") or "")
    state = str(close.get("state") or "")
    if status == "verified" or state in ("VERIFIED_CLOSED", "RESOLVED"):
        return None
    href = "/uma-blu-close"
    if status == "exception" or state == "EXCEPTION":
        if caps.get("resolve"):
            return {"label": ACTION_RESOLVE, "href": href}
        return None
    if status == "blocked" or state == "VARIANCE_REQUIRES_POLICY":
        if caps.get("exception"):
            return {"label": ACTION_OPEN_EXCEPTION, "href": href}
        return None
    if caps.get("submit"):
        return {"label": ACTION_PERFORM_CLOSE, "href": href}
    return None


def actionable_for(
    person_id: str,
    card: dict[str, Any],
    *,
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    """Whether this Today card is something this person can act on."""
    kind = str(card.get("kind") or "")
    if kind in _INFORMATIONAL:
        return {"actionable": True, "navigation": True, "waiting_role": None, "action": None}
    caps = _caps(person_id, conn)
    actionable, role = _card_gate(kind, card, caps)
    action = _perform_action(kind, card, caps) if actionable else None
    if actionable and kind == "daily_close" and action is None:
        return {
            "actionable": True,
            "navigation": True,
            "waiting_role": None,
            "waiting_copy": None,
            "waiting_on": None,
            "action": None,
        }
    token = role or "policy"
    waiting_on = None
    if not actionable:
        waiting_on = "policy" if token == "policy" else _waiting_subject(conn, token, person_id)
    return {
        "actionable": actionable,
        "navigation": False,
        "waiting_role": None if actionable else token,
        "waiting_on": None if actionable else waiting_on,
        "waiting_copy": None
        if actionable
        else waiting_copy("policy" if token == "policy" else (waiting_on or token)),
        "action": action,
    }


def _card_gate(kind: str, card: dict[str, Any], caps: dict[str, Any]) -> tuple[bool, str | None]:
    if kind in ("bills_waiting_payment_approval", "payment_claimed_not_verified", "legacy_unpaid_ledger"):
        return False, "finance"
    if kind in ("policy_required", "opening_balance_required", "petty_policy_required"):
        return False, "policy"
    if kind == "prs_waiting_approval":
        if caps.get("approve_ops"):
            return True, None
        return False, "approver"
    if kind == "draft_pr":
        if caps.get("submit_pr"):
            return True, None
        return False, "staff"
    if kind == "ordered_not_received" or kind == "awaiting_remainder":
        if caps.get("receive"):
            return True, None
        return False, "policy"
    if kind == "received_follow_up":
        return False, "staff"
    if kind == "petty_cash":
        title = str(card.get("title") or "").upper()
        if card.get("classification") == "NEEDS_POLICY" or "OPENING" in title:
            return False, "policy"
        return False, "staff"
    if kind == "daily_close":
        return _close_gate(card, caps)
    if card.get("classification") == "NEEDS_POLICY":
        return False, "policy"
    return False, "staff"


def _close_gate(card: dict[str, Any], caps: dict[str, Any]) -> tuple[bool, str | None]:
    close = card.get("close") or {}
    status = str(close.get("status") or "")
    state = str(close.get("state") or "")
    if status == "exception" or state == "EXCEPTION":
        if caps.get("resolve"):
            return True, None
        return False, "Head of F&B"
    if status == "blocked" or state == "VARIANCE_REQUIRES_POLICY":
        if caps.get("exception"):
            return True, None
        return False, "policy"
    if state == "RESOLVED":
        if caps.get("verify"):
            return True, None
        return False, "Head of F&B"
    if status == "verified" or state == "VERIFIED_CLOSED":
        return True, None
    if caps.get("submit"):
        return True, None
    return False, "closer"


def _apply_operator_chip(row: dict[str, Any], decision: dict[str, Any]) -> None:
    """Authenticated operator: a perform action when they can. Never 'Needs staff' then.

    Waiting on [role/person], or Policy required, when they cannot.
    Verify is not offered here.
    """
    if decision.get("action"):
        row["action"] = dict(decision["action"])
    if decision.get("navigation"):
        return
    if decision.get("actionable"):
        if decision.get("action"):
            row["classification"] = "CAN_ACT"
            row["classification_label"] = CAN_ACT_LABEL
            href = (decision.get("action") or {}).get("href")
            if href:
                row["href"] = href
            return
        label = str(row.get("classification_label") or "")
        if row.get("classification") == "NEEDS_STAFF" or label in ("", "Needs staff"):
            row["classification"] = "CAN_ACT"
            row["classification_label"] = CAN_ACT_LABEL
        return
    role = str(decision.get("waiting_role") or "policy")
    if role == "policy":
        row["classification_label"] = POLICY_REQUIRED_LABEL
        return
    who = str(decision.get("waiting_on") or role)
    row["waiting_on"] = who
    row["classification_label"] = f"Waiting on {who}"


def annotate_today(
    payload: dict[str, Any],
    *,
    person_id: str,
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    cards = []
    for card in payload.get("cards") or []:
        row = dict(card)
        decision = actionable_for(person_id, row, conn=conn)
        row["actionable"] = bool(decision["actionable"])
        if decision.get("navigation"):
            row["navigation"] = True
        if not decision["actionable"]:
            row["waiting_role"] = decision.get("waiting_role")
            row["waiting_on"] = decision.get("waiting_on")
            row["waiting_copy"] = decision.get("waiting_copy")
            row.pop("action", None)
            row["href"] = None
            items = []
            for item in row.get("items") or []:
                it = dict(item)
                it.pop("href", None)
                items.append(it)
            row["items"] = items
        _apply_operator_chip(row, decision)
        cards.append(row)

    def sort_key(card: dict[str, Any]) -> tuple:
        kind = str(card.get("kind") or "")
        if kind == "history":
            tier = 4
        elif card.get("actionable") and card.get("attention") and not card.get("navigation"):
            tier = 0
        elif card.get("attention") and not card.get("actionable"):
            tier = 1
        elif card.get("navigation"):
            tier = 2
        else:
            tier = 3
        return (tier, int(card.get("rank") or 500), kind)

    cards.sort(key=sort_key)
    out = dict(payload)
    out["cards"] = cards
    out["order"] = [c.get("kind") for c in cards]
    out["operator_person_id"] = person_id
    lead = next(
        (
            c
            for c in cards
            if c.get("attention") and c.get("actionable") and not c.get("navigation")
        ),
        None,
    )
    if lead is None:
        lead = next(
            (
                c
                for c in cards
                if c.get("attention") and c.get("waiting_copy") and c.get("kind") != "history"
            ),
            None,
        )
    if lead is None:
        out["now"] = None
    else:
        out["now"] = {
            "title": lead.get("title"),
            "why": lead.get("why") or "",
            "classification": lead.get("classification") or "",
            "classification_label": lead.get("classification_label") or "",
            "href": lead.get("href") if lead.get("actionable") else None,
            "kind": lead.get("kind"),
            "actionable": bool(lead.get("actionable")),
            "waiting_copy": lead.get("waiting_copy") or "",
            "waiting_role": lead.get("waiting_role") or "",
            "waiting_on": lead.get("waiting_on") or "",
            "action": lead.get("action"),
        }
    return out


def _outstanding(lines: list[dict[str, Any]], already: dict[str, float]) -> dict[str, float]:
    out = {}
    for line in lines:
        if not line.get("interpretable"):
            continue
        sid = str(line.get("source_line_id") or "")
        qty = float(line.get("qty"))
        got = already.get(sid, 0.0)
        out[sid] = qty - got
    return out


def receive_goods(
    *,
    person_id: str,
    pr_key: str,
    lines: list[dict[str, Any]],
    notes: str | None = None,
    corrects_receipt_id: str | None = None,
    evidence_note_id: str | None = None,
    evidence_photo_id: str | None = None,
    require_evidence: bool = False,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Append one Wolf receipt. Does not update Alchemist or prior receipt rows."""
    pid = (person_id or "").strip()
    if not pid:
        raise _ops.UmaOpsError("verified_person_id required", code="missing_verified_person")
    key = (pr_key or "").strip()
    if not key:
        raise _ops.UmaOpsError("pr required", code="missing_pr")
    if not isinstance(lines, list) or not lines:
        raise _ops.UmaOpsError("lines required", code="lines_required")

    own = conn is None
    c = conn or _ops.db_connect()
    try:
        _ops.assert_catalog_writable(_ops.CATALOG_DB)
        ensure_receipt_schema(c)
        code = discover_receive_permission(c)
        if not code:
            raise _ops.UmaOpsError(
                "No venue receive permission in RBAC. Fail closed.",
                code="receive_permission_absent",
                http_status=403,
            )
        if not _rbac.can(pid, code, UMA_TARGET, conn=c):
            raise _ops.UmaOpsError(
                f"permission denied: {code}",
                code="forbidden",
                http_status=403,
            )
        detail = pr_detail(key, conn=c)
        if not detail:
            raise _ops.UmaOpsError("PR not found", code="not_found", http_status=404)
        if detail.get("wolf") and not detail.get("legacy"):
            wolf_state = str(detail.get("state") or "")
            if wolf_state not in ("ORDERED", "PARTIALLY_RECEIVED"):
                raise _ops.UmaOpsError(
                    "Goods can be received after the request is ordered.",
                    code="illegal_transition",
                )
        note_id = (evidence_note_id or "").strip() or None
        photo_id = (evidence_photo_id or "").strip() or None
        if require_evidence and not note_id and not photo_id:
            raise _ops.UmaOpsError(
                "A note id or photo id is required to record this receipt.",
                code="missing_evidence",
            )
        source_lines = [ln for ln in (detail.get("lines") or []) if ln.get("interpretable")]
        if not source_lines:
            raise _ops.UmaOpsError(
                "Order lines are not interpretable. No quantities were invented.",
                code="lines_not_interpretable",
            )
        by_id = {str(ln["source_line_id"]): ln for ln in source_lines}
        keys = _pr_match_keys(detail)
        if key not in keys:
            keys.append(key)
        already = _wolf_received_by_line(c, keys)
        outstanding = _outstanding(source_lines, already)

        parsed: list[tuple[dict[str, Any], float]] = []
        for raw in lines:
            if not isinstance(raw, dict):
                raise _ops.UmaOpsError("line must be an object", code="invalid_line")
            sid = str(raw.get("source_line_id") or "").strip()
            src = by_id.get(sid)
            if not src:
                raise _ops.UmaOpsError(
                    "unknown source line",
                    code="unknown_line",
                )
            try:
                qty = float(raw.get("received_qty"))
            except (TypeError, ValueError) as exc:
                raise _ops.UmaOpsError(
                    "received_qty must be numeric",
                    code="invalid_qty",
                ) from exc
            if qty <= 0:
                raise _ops.UmaOpsError("received_qty must be positive", code="invalid_qty")
            left = outstanding.get(sid, 0.0)
            if qty - left > QTY_EPS:
                raise _ops.UmaOpsError(
                    "received_qty exceeds outstanding",
                    code="exceeds_outstanding",
                )
            parsed.append((src, qty))

        for src, qty in parsed:
            sid = str(src["source_line_id"])
            outstanding[sid] = outstanding.get(sid, 0.0) - qty

        complete = all(v <= QTY_EPS for v in outstanding.values()) and bool(outstanding)
        status = "COMPLETE" if complete else "PARTIAL"
        corrects = (corrects_receipt_id or "").strip() or None
        if corrects:
            prior = c.execute(
                "SELECT receipt_id FROM bzg_ops_receipt_events WHERE receipt_id=?",
                (corrects,),
            ).fetchone()
            if not prior:
                raise _ops.UmaOpsError(
                    "correction target not found",
                    code="not_found",
                    http_status=404,
                )

        ts = _ops.now_utc_iso()
        receipt_id = f"RCP-{uuid.uuid4()}"
        provenance = detail.get("provenance") if isinstance(detail.get("provenance"), dict) else None
        try:
            evid = _evidence.submit_evidence(
                entity_id=_ops.ENTITY_BZG,
                evidence_type=EVIDENCE_TYPE,
                governed_object_type=RESOURCE_RECEIPT,
                governed_object_id=receipt_id,
                verified_person_id=pid,
                source_type="HUMAN",
                brand_id=_ops.VENUE_UMA,
                metadata={
                    "pr_key": key,
                    "status": status,
                    "note": "Wolf receipt. Does not verify the existing Alchemist record.",
                    "alchemist_status": detail.get("alchemist_status"),
                },
                identity=identity,
                conn=c,
                commit=False,
            )
        except _evidence.EvidenceError as exc:
            c.rollback()
            raise _ops.UmaOpsError(
                str(exc),
                code=getattr(exc, "code", "evidence_failed"),
                http_status=int(getattr(exc, "http_status", 400) or 400),
            ) from exc
        c.execute(
            """
            INSERT INTO bzg_ops_receipt_events (
              receipt_id, venue, pr_key, pr_num, alchemist_pr_id, provenance_json,
              receiver_person_id, status, notes, evidence_id, corrects_receipt_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt_id,
                _ops.VENUE_UMA,
                key,
                detail.get("pr_num"),
                None if detail.get("alchemist_pr_id") is None else str(detail.get("alchemist_pr_id")),
                json.dumps(provenance) if provenance else None,
                pid,
                status,
                (notes or "").strip() or None,
                evid["evidence_id"],
                corrects,
                ts,
            ),
        )
        stored_lines = []
        for src, qty in parsed:
            line_id = f"RCPL-{uuid.uuid4()}"
            c.execute(
                """
                INSERT INTO bzg_ops_receipt_lines (
                  line_id, receipt_id, source_line_id, item, unit, requested_qty,
                  received_qty, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    line_id,
                    receipt_id,
                    str(src["source_line_id"]),
                    src.get("item"),
                    src.get("unit"),
                    src.get("qty"),
                    qty,
                    ts,
                ),
            )
            stored_lines.append(
                {
                    "line_id": line_id,
                    "source_line_id": str(src["source_line_id"]),
                    "item": src.get("item"),
                    "received_qty": qty,
                    "requested_qty": src.get("qty"),
                }
            )
        variance = not complete
        shortfall = {k: v for k, v in outstanding.items() if v > QTY_EPS}
        c.execute(
            """
            INSERT INTO bzg_ops_receipt_slots (
              receipt_id, evidence_note_id, evidence_photo_id, variance_flag,
              shortfall_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                receipt_id,
                note_id,
                photo_id,
                1 if variance else 0,
                json.dumps(shortfall),
                ts,
            ),
        )
        if detail.get("wolf") and not detail.get("legacy"):
            dest = "RECEIVED" if complete else "PARTIALLY_RECEIVED"
            if str(detail.get("state") or "") != dest:
                _ops.transition_pr(
                    str(detail.get("pr_id") or key),
                    dest,
                    verified_person_id=pid,
                    actor_type="PERSON",
                    identity=identity,
                    conn=c,
                    commit=False,
                )
        _ops._audit_ops(
            action="bzg.receipt.appended",
            result="SUCCEEDED",
            resource_type=RESOURCE_RECEIPT,
            resource_id=receipt_id,
            conn=c,
            metadata={
                "status": status,
                "pr_key": key,
                "evidence_id": evid["evidence_id"],
                "note": "Append-only Wolf receipt. Alchemist row not rewritten.",
                "corrects_receipt_id": corrects,
            },
            actor_type="PERSON",
            verified_person_id=pid,
            identity=identity,
        )
        if commit:
            c.commit()
        return {
            "receipt_id": receipt_id,
            "status": status,
            "pr_key": key,
            "pr_num": detail.get("pr_num"),
            "evidence_id": evid["evidence_id"],
            "lines": stored_lines,
            "corrects_receipt_id": corrects,
            "wolf_verified_alchemist": False,
            "variance_flag": variance,
            "variance_is_not_a_stock_count": True,
            "evidence_note_id": note_id,
            "evidence_photo_id": photo_id,
            "outstanding": {k: v for k, v in outstanding.items()},
        }
    finally:
        if own:
            c.close()


OWNER_PERSON = "PERS-MATT"


def _seat_line(view: str, buttons: dict[str, bool]) -> str:
    """Plain sentence from capabilities. The person's name is not an input."""
    if view == "owner":
        return "You can read the day. This screen does not pay anyone."
    if buttons.get("perform_close") and not buttons.get("receive"):
        return (
            "You count the till and record the day. "
            "You cannot pay, change a bank, or verify your own close."
        )
    if buttons.get("receive") or buttons.get("perform_close"):
        return "You run the day's operations. You cannot pay or change a bank."
    return "Sign-in decides what you can do. Payment is not on this screen."


_OPS_DEST_CAP = {
    "REQUESTED": "submit_pr",
    "APPROVED": "approve_ops",
    "REJECTED": "approve_ops",
    "ORDERED": "order",
    "OPS_CLOSED": "close_ops",
}


def operator_view(person_id: str, *, conn: sqlite3.Connection) -> dict[str, Any]:
    """Devi-scoped operator versus Owner manager read. No money controls on either."""
    pid = (person_id or "").strip()
    caps = _caps(pid, conn)
    owner = pid == OWNER_PERSON
    buttons = {
        "create_pr": bool(caps.get("create")),
        "submit": bool(caps.get("submit_pr")),
        "approve_ops": bool(caps.get("approve_ops")),
        "order": bool(caps.get("order")),
        "receive": bool(caps.get("receive")),
        "close_ops": bool(caps.get("close_ops")),
        "petty_record": bool(caps.get("petty")),
        "petty_record_out": bool(caps.get("petty_record_out")),
        "petty_record_in": bool(caps.get("petty_record_in")),
        "petty_reconcile": bool(caps.get("petty_reconcile")),
        "petty_count": bool(caps.get("petty_reconcile")),
        "create_issue": bool(caps.get("issue")),
        "perform_close": bool(caps.get("submit")),
        "pr_operator": bool(caps.get("pr_operator")),
        "correction": bool(caps.get("pr_operator")),
        "payment_approve": False,
        "payment_execution": False,
        "verify_close": False,
        "progress": False,
    }
    view = "owner" if owner else "operator"
    return {
        "ok": True,
        "view": view,
        "person_id": pid or None,
        "manager_read": owner,
        "seat_line": _seat_line(view, buttons),
        "buttons": buttons,
        "payment_execution": False,
        "sees_money_controls": False,
        "human_commissioning": "NOT_DONE",
        "live_devi_commission": False,
        "proven": False,
        "ready": False,
        "operator_depth_bound": _ops.LOOP_BOUND,
    }


def _pr_requester_person(conn: sqlite3.Connection, pr_id: str) -> str | None:
    """Person who drafted or submitted the PR. Column first, then audit."""
    key = (pr_id or "").strip()
    if not key:
        return None
    col = conn.execute(
        "SELECT requester_person_id FROM bzg_ops_purchase_requests WHERE pr_id=?",
        (key,),
    ).fetchone()
    if col and col[0]:
        return str(col[0]).strip() or None
    row = conn.execute(
        """
        SELECT actor_person_id
        FROM core_audit_events
        WHERE resource_type=? AND resource_id=?
          AND action IN ('bzg.pr.draft', 'bzg.pr.requested', 'bzg.pr.create')
          AND actor_person_id IS NOT NULL AND actor_person_id != ''
        ORDER BY occurred_at ASC, created_at ASC
        LIMIT 1
        """,
        (_ops.RESOURCE_TYPE, key),
    ).fetchone()
    if not row:
        return None
    return str(row[0]).strip() or None


def ops_advance(
    *,
    person_id: str,
    pr_id: str,
    to_state: str,
    evidence_note_id: str | None = None,
    evidence_photo_id: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Ops lifecycle only. Payment destinations are refused."""
    dest = (to_state or "").strip().upper()
    _ops.assert_not_payment_execution(dest)
    need = _OPS_DEST_CAP.get(dest)
    if not need:
        raise _ops.UmaOpsError(f"invalid state: {to_state!r}", code="invalid_state")
    pid = (person_id or "").strip()
    own = conn is None
    c = conn or _ops.db_connect()
    try:
        _ops.assert_catalog_writable(_ops.CATALOG_DB)
        caps = _caps(pid, c)
        if not caps.get(need):
            raise _ops.UmaOpsError(
                f"permission denied: {need}",
                code="forbidden",
                http_status=403,
            )
        if dest in ("APPROVED", "REJECTED"):
            requester = _pr_requester_person(c, (pr_id or "").strip())
            if not requester or requester == pid:
                verb = "reject" if dest == "REJECTED" else "approve"
                raise _ops.UmaOpsError(
                    f"A different person must {verb} this request.",
                    code="self_approval_denied",
                    http_status=403,
                )
        if dest == "OPS_CLOSED":
            _ops.save_pr_close_slot(
                c,
                pr_id=(pr_id or "").strip(),
                evidence_note_id=evidence_note_id,
                evidence_photo_id=evidence_photo_id,
                closed_by=pid,
            )
        out = _ops.transition_pr(
            pr_id,
            dest,
            verified_person_id=pid,
            actor_type="PERSON",
            identity=identity,
            conn=c,
            commit=False,
        )
        out["payment_execution"] = False
        if commit:
            c.commit()
        return out
    finally:
        if own:
            c.close()


def reject_purchase_segregated(
    *,
    person_id: str,
    pr_id: str,
    reason: str,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Segregating ops rejection. Reason required. Not payment."""
    from core import approvals as _approvals

    pid = (person_id or "").strip()
    key = (pr_id or "").strip()
    text = (reason or "").strip()
    if not text:
        raise _ops.UmaOpsError(
            "A reason is required to reject.",
            code="missing_reason",
            http_status=400,
        )
    own = conn is None
    c = conn or _ops.db_connect()
    try:
        _ops.assert_catalog_writable(_ops.CATALOG_DB)
        requester = _pr_requester_person(c, key)
        if not requester or requester == pid:
            raise _ops.UmaOpsError(
                "A different person must reject this request.",
                code="self_approval_denied",
                http_status=403,
            )
        existing = c.execute(
            """
            SELECT approval_request_id, status
            FROM core_approval_requests
            WHERE source_id=? AND request_type='GENERAL'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (key,),
        ).fetchone()
        if existing and str(existing["status"]) == "REJECTED":
            request_id = str(existing["approval_request_id"])
        elif existing and str(existing["status"]) == "PENDING":
            request_id = str(existing["approval_request_id"])
        elif existing and str(existing["status"]) == "APPROVED":
            raise _ops.UmaOpsError(
                "This request was already approved.",
                code="already_approved",
                http_status=409,
            )
        elif existing:
            raise _ops.UmaOpsError(
                f"approval request is {existing['status']}",
                code="approval_not_pending",
                http_status=409,
            )
        else:
            detail = pr_detail(key, conn=c) or {}
            title = f"Uma Blu purchase {detail.get('pr_num') or key}"
            try:
                created = _approvals.create_approval_request(
                    title=title[:200],
                    owning_entity_id=_ops.ENTITY_BZG,
                    brand_id=_ops.VENUE_UMA,
                    required_permission_code="work.complete",
                    verified_person_id=requester,
                    request_type="GENERAL",
                    description=(
                        "Segregating ops rejection for one Uma Blu purchase. "
                        "Not a payment and not an authority limit."
                    ),
                    source_type="HUMAN",
                    source_id=key,
                    governed_object_type=_ops.RESOURCE_TYPE,
                    governed_object_id=key,
                    bind_policy=False,
                    identity=identity,
                    conn=c,
                    commit=False,
                )
            except _approvals.ApprovalError as exc:
                raise _ops.UmaOpsError(
                    str(exc),
                    code=getattr(exc, "code", "approval_failed"),
                    http_status=int(getattr(exc, "http_status", 400) or 400),
                ) from exc
            request_id = str(created["approval_request_id"])
        if not existing or str(existing["status"]) == "PENDING":
            try:
                _approvals.reject_request(
                    request_id,
                    verified_person_id=pid,
                    reason=text,
                    identity=identity,
                    conn=c,
                    commit=False,
                )
            except _approvals.ApprovalError as exc:
                raise _ops.UmaOpsError(
                    str(exc),
                    code=getattr(exc, "code", "approval_failed"),
                    http_status=int(getattr(exc, "http_status", 400) or 400),
                ) from exc
        out = ops_advance(
            person_id=pid,
            pr_id=key,
            to_state="REJECTED",
            identity=identity,
            conn=c,
            commit=False,
        )
        out["approval_request_id"] = request_id
        out["approval_status"] = "REJECTED"
        out["reject_reason"] = text
        out["segregated"] = True
        out["payment_execution"] = False
        if commit:
            c.commit()
        return out
    except Exception:
        if commit and own:
            try:
                c.rollback()
            except Exception:
                pass
        raise
    finally:
        if own:
            c.close()


def approve_purchase_segregated(
    *,
    person_id: str,
    pr_id: str,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """One segregating ops approval. Not the approvals product.

    The requester cannot approve. A different person with work.complete
    decides one GENERAL core_approval_requests row, then the PR moves to
    APPROVED. No payment, no authority-limit table, no delegation product.
    """
    from core import approvals as _approvals

    pid = (person_id or "").strip()
    key = (pr_id or "").strip()
    own = conn is None
    c = conn or _ops.db_connect()
    try:
        _ops.assert_catalog_writable(_ops.CATALOG_DB)
        requester = _pr_requester_person(c, key)
        if not requester or requester == pid:
            raise _ops.UmaOpsError(
                "A different person must approve this request.",
                code="self_approval_denied",
                http_status=403,
            )
        existing = c.execute(
            """
            SELECT approval_request_id, status
            FROM core_approval_requests
            WHERE source_id=? AND request_type='GENERAL'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (key,),
        ).fetchone()
        if existing and str(existing["status"]) == "APPROVED":
            request_id = str(existing["approval_request_id"])
        elif existing and str(existing["status"]) == "PENDING":
            request_id = str(existing["approval_request_id"])
        elif existing:
            raise _ops.UmaOpsError(
                f"approval request is {existing['status']}",
                code="approval_not_pending",
                http_status=409,
            )
        else:
            detail = pr_detail(key, conn=c) or {}
            title = f"Uma Blu purchase {detail.get('pr_num') or key}"
            try:
                created = _approvals.create_approval_request(
                    title=title[:200],
                    owning_entity_id=_ops.ENTITY_BZG,
                    brand_id=_ops.VENUE_UMA,
                    required_permission_code="work.complete",
                    verified_person_id=requester,
                    request_type="GENERAL",
                    description=(
                        "Segregating ops approval for one Uma Blu purchase. "
                        "Not a payment and not an authority limit."
                    ),
                    source_type="HUMAN",
                    source_id=key,
                    governed_object_type=_ops.RESOURCE_TYPE,
                    governed_object_id=key,
                    bind_policy=False,
                    identity=identity,
                    conn=c,
                    commit=False,
                )
            except _approvals.ApprovalError as exc:
                raise _ops.UmaOpsError(
                    str(exc),
                    code=getattr(exc, "code", "approval_failed"),
                    http_status=int(getattr(exc, "http_status", 400) or 400),
                ) from exc
            request_id = str(created["approval_request_id"])
        if not existing or str(existing["status"]) == "PENDING":
            try:
                _approvals.approve_request(
                    request_id,
                    verified_person_id=pid,
                    reason="Segregated ops approval. Not a payment.",
                    identity=identity,
                    conn=c,
                    commit=False,
                )
            except _approvals.ApprovalError as exc:
                raise _ops.UmaOpsError(
                    str(exc),
                    code=getattr(exc, "code", "approval_failed"),
                    http_status=int(getattr(exc, "http_status", 400) or 400),
                ) from exc
        out = ops_advance(
            person_id=pid,
            pr_id=key,
            to_state="APPROVED",
            identity=identity,
            conn=c,
            commit=False,
        )
        out["approval_request_id"] = request_id
        out["approval_status"] = "APPROVED"
        out["segregated"] = True
        out["payment_execution"] = False
        if commit:
            c.commit()
        return out
    except Exception:
        if commit and own:
            try:
                c.rollback()
            except Exception:
                pass
        raise
    finally:
        if own:
            c.close()
