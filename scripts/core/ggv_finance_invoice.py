#!/usr/bin/env python3
"""GGV customer invoices on the existing GGV Finance desk.

Decision served: owner decision (Matthew, 28 Sep 2026 13:17 WITA): the next
GGV invoice number is 067A and Wolf owns issuance. Extends the same desk as
the 28 Sep 2026 11:52 WITA invoice work in scripts/core/ggv_finance_nota.py.
Not a second finance system.

Numbering rule: the number is assigned at issue, inside one BEGIN IMMEDIATE
transaction. A draft has no number and shows "Number assigned on issue".
Issued numbers are immutable. Void keeps the number. The sequence never
goes backwards and a voided number is not recycled. An operator does not
type a number. Owner historical import keeps the original number, marks
source imported, and refuses a number already stored.

Reused, not forked
------------------
- Catalog sqlite, org RBAC, audit events, and the GGV Finance scope.
- Nota vendors, nota upload, history search, and month evidence export.
- org_entities legal name for the invoice From line.
- crm_customers when that table already has the same normalised name.
- Staff AuthIdentity → Person → Role → Assignment → Scope → Permission.
  The role is GGV Finance Operator. It is not named for a person.

This module does not move money, write a bank, execute a payment, write
Xero, or send email. Issued is not paid. Claimed is not verified.
Unknown cash, profit, ageing, margin, and tax position stay unknown.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from core import ggv_finance_nota as nota

ROLE_OPERATOR = "ROLE-GGV-FINANCE-OPERATOR"
ROLE_OWNER = "ROLE-MATT"
POSITION_OPERATOR = "POS-GGV-FINANCE-OPERATOR-1"
ASSIGNMENT_AMANDA = "ASG-AMANDA-GGV-FIN-1"
AMANDA_PERSON = "PERS-AMANDA"
AMANDA_EMAIL = "amanda@wolfcommand.net"

# Display states. OVERDUE is calculated. It is not stored.
STATUSES = (
    "DRAFT",
    "READY",
    "ISSUED",
    "PART_PAID",
    "PAID_CLAIMED",
    "PAYMENT_VERIFIED",
    "VOID",
)
STATUS_LABEL = {
    "DRAFT": "Draft",
    "READY": "Ready — approval required",
    "ISSUED": "Issued",
    "PART_PAID": "Part paid",
    "PAID_CLAIMED": "Paid — claimed",
    "PAYMENT_VERIFIED": "Payment verified",
    "VOID": "Void",
    "OVERDUE": "Overdue",
}
EDITABLE = frozenset({"DRAFT"})
ISSUE_FROM = frozenset({"DRAFT", "READY"})
CLAIM_FROM = frozenset({"ISSUED"})
VOID_FROM = frozenset({"DRAFT", "READY", "ISSUED"})

ROUNDING = {
    "mode": "ROUND_HALF_UP",
    "idr": "0 decimal places. One rupiah is the minor unit.",
    "other": "2 decimal places.",
    "order": (
        "Each line subtotal is rounded, then each line tax is rounded, "
        "then the invoice total is the sum of those rounded line totals. "
        "A total typed in the browser is ignored."
    ),
}

OPERATOR_PERMS: tuple[tuple[str, str, str, str], ...] = (
    ("PERM-FIN-INV-READ", "finance.invoice.read", "finance.invoice", "read"),
    ("PERM-FIN-INV-CREATE", "finance.invoice.create", "finance.invoice", "create"),
    ("PERM-FIN-INV-EDIT", "finance.invoice.edit", "finance.invoice", "edit"),
    ("PERM-FIN-INV-ISSUE", "finance.invoice.issue", "finance.invoice", "issue"),
    ("PERM-FIN-INV-VOID", "finance.invoice.void", "finance.invoice", "void"),
    ("PERM-FIN-INV-CLAIM", "finance.invoice.claim", "finance.invoice", "claim"),
    ("PERM-FIN-CUST-READ", "finance.customer.read", "finance.customer", "read"),
    ("PERM-FIN-CUST-CREATE", "finance.customer.create", "finance.customer", "create"),
)
OPERATOR_EXISTING: tuple[str, ...] = (
    "finance.nota.read",
    "finance.nota.create",
    "finance.nota.edit",
    "vendor.read",
    "vendor.create",
    "evidence.create",
    "finance.evidence.export",
    "work.read",
)
IMPORT_PERM = ("PERM-FIN-INV-IMPORT", "finance.invoice.import", "finance.invoice", "import")
HELD_BACK: tuple[str, ...] = (
    "payment.approve",
    "payment.execute",
    "vendor.bank.change",
    "finance.policy.admin",
    "finance.invoice.verify",
    "finance.invoice.import",
    "atrium.board.read",
    "organisation.role.read",
)
SEQUENCE_FORMAT = "{n:03d}A"
SEQUENCE_NEXT = 67
SEQUENCE_ACTOR = "Matthew"
SEQUENCE_REASON = (
    "Owner decision (Matthew, 28 Sep 2026 13:17 WITA): next GGV invoice number is 067A. "
    "Wolf owns issuance from now on. Historical 064A, 065A, and 066A stay provenance only "
    "and are not created."
)
DRAFT_NUMBER_LABEL = "Number assigned on issue"
NEXT_INTEGRATION = (
    "Generate Gmail draft with PDF attachment — human review/send, never automatic"
)
OWNER_PERSON = "PERS-MATT"

FINANCE_ENTITIES: dict[str, dict[str, str]] = {
    "ROLE-GGV-FINANCE-OPERATOR": {
        "id": "GGV",
        "label": "GGV",
        "href": "/ggv/finance",
        "entity_id": "ENT-GGV",
    },
    "ROLE-GGV-EXTERNAL-ACCOUNTANT": {
        "id": "GGV",
        "label": "GGV",
        "href": "/ggv/finance",
        "entity_id": "ENT-GGV",
    },
    "ROLE-AMG-FINANCE-OFFICER": {
        "id": "AMG",
        "label": "AMG",
        "href": "/amg/finance",
        "entity_id": "ENT-AMG",
    },
}

_NUMBER = re.compile(r"^[A-Z0-9][A-Z0-9./-]{0,31}$")
_SERIES = re.compile(r"^(\d{3})A$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")


def _fail(
    message: str,
    *,
    code: str = "invalid",
    status: int = 400,
    extra_conflict: bool = False,
) -> None:
    extra = {"conflict": True} if extra_conflict else None
    raise nota.FinanceNotaError(message, code=code, http_status=status, extra=extra)


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS fin_counterparties (
          counterparty_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          kind TEXT NOT NULL,
          legal_name TEXT NOT NULL,
          trading_name TEXT,
          tax_id TEXT,
          company_id TEXT,
          billing_address TEXT,
          contact_name TEXT,
          email TEXT,
          phone TEXT,
          default_terms TEXT,
          notes TEXT,
          crm_customer_id TEXT,
          name_norm TEXT NOT NULL,
          tax_norm TEXT,
          status TEXT NOT NULL,
          created_by_person_id TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_fin_cp_name
          ON fin_counterparties(entity_id, kind, name_norm);
        CREATE TABLE IF NOT EXISTS ggv_invoices (
          invoice_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          customer_id TEXT NOT NULL,
          invoice_number TEXT,
          invoice_date TEXT NOT NULL,
          due_date TEXT,
          terms TEXT,
          currency TEXT NOT NULL,
          notes TEXT,
          reference TEXT,
          payment_method TEXT,
          payment_reference TEXT,
          lines_json TEXT NOT NULL,
          subtotal TEXT NOT NULL,
          tax_total TEXT NOT NULL,
          grand_total TEXT NOT NULL,
          rounding_json TEXT NOT NULL,
          status TEXT NOT NULL,
          number_source TEXT NOT NULL,
          created_by_person_id TEXT NOT NULL,
          finalised_by_person_id TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          issued_at TEXT,
          draft_email_json TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_ggv_invoice_number
          ON ggv_invoices(entity_id, invoice_number);
        CREATE TABLE IF NOT EXISTS ggv_invoice_history (
          history_id TEXT PRIMARY KEY,
          invoice_id TEXT NOT NULL,
          action TEXT NOT NULL,
          actor_person_id TEXT NOT NULL,
          detail_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ggv_invoice_documents (
          document_id TEXT PRIMARY KEY,
          invoice_id TEXT NOT NULL,
          version INTEGER NOT NULL,
          sha256 TEXT NOT NULL,
          pdf BLOB NOT NULL,
          created_by_person_id TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_ggv_invoice_doc_ver
          ON ggv_invoice_documents(invoice_id, version);
        CREATE TABLE IF NOT EXISTS fin_invoice_sequences (
          entity_id TEXT PRIMARY KEY,
          format TEXT NOT NULL,
          next_value INTEGER NOT NULL,
          updated_by TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS fin_invoice_sequence_audit (
          audit_id TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          actor TEXT NOT NULL,
          reason TEXT NOT NULL,
          previous_value INTEGER,
          next_value INTEGER NOT NULL,
          format TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS fin_invoice_sequences_no_rewind
        BEFORE UPDATE ON fin_invoice_sequences
        FOR EACH ROW
        WHEN NEW.next_value < OLD.next_value
        BEGIN
          SELECT RAISE(ABORT, 'invoice sequence cannot go backwards');
        END;
        """
    )
    seed_ggv_sequence(conn)
    conn.commit()


def _perm(conn: sqlite3.Connection, perm_id: str, code: str, resource: str, action: str, ts: str) -> None:
    conn.execute(
        """
        INSERT INTO org_permissions (
          permission_id, code, resource, action, description, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
        ON CONFLICT(permission_id) DO UPDATE SET
          code=excluded.code, status='ACTIVE', updated_at=excluded.updated_at
        """,
        (perm_id, code, resource, action, f"GGV invoice desk: {code}", ts, ts),
    )


def _allow(conn: sqlite3.Connection, role_id: str, code: str, ts: str) -> None:
    role = conn.execute("SELECT role_id FROM org_roles WHERE role_id=?", (role_id,)).fetchone()
    row = conn.execute(
        "SELECT permission_id FROM org_permissions WHERE code=? AND status='ACTIVE'",
        (code,),
    ).fetchone()
    if role is None or row is None:
        return
    conn.execute(
        """
        INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES (?, ?, 'ALLOW', ?, ?)
        ON CONFLICT(role_id, permission_id) DO UPDATE SET
          effect='ALLOW', updated_at=excluded.updated_at
        """,
        (role_id, row[0], ts, ts),
    )


def seed_operator_role(conn: sqlite3.Connection) -> None:
    """Role and permissions only. Does not create a person."""
    from pathlib import Path

    raw = conn.execute("PRAGMA database_list").fetchone()[2]
    nota.assert_catalog_writable(Path(raw or nota.CATALOG_DB))
    ts = nota._now()
    ensure_schema(conn)
    for row in OPERATOR_PERMS:
        _perm(conn, row[0], row[1], row[2], row[3], ts)
    _perm(conn, IMPORT_PERM[0], IMPORT_PERM[1], IMPORT_PERM[2], IMPORT_PERM[3], ts)
    conn.execute(
        """
        INSERT INTO org_roles (
          role_id, display_name, department_id, role_type, status, created_at, updated_at
        ) VALUES (?, 'GGV Finance Operator', NULL, 'OPERATING', 'SPECIFIED', ?, ?)
        ON CONFLICT(role_id) DO UPDATE SET
          display_name='GGV Finance Operator',
          role_type='OPERATING',
          status='SPECIFIED',
          updated_at=excluded.updated_at
        """,
        (ROLE_OPERATOR, ts, ts),
    )
    codes = [row[1] for row in OPERATOR_PERMS] + list(OPERATOR_EXISTING)
    for code in codes:
        _allow(conn, ROLE_OPERATOR, code, ts)
    for code in ("finance.invoice.read", "finance.invoice.create", "finance.invoice.edit", "finance.invoice.issue", "finance.customer.read", "finance.customer.create", "finance.invoice.import"):
        _allow(conn, ROLE_OWNER, code, ts)
    _allow(conn, nota.ROLE_EXTERNAL_ACCOUNTANT, "finance.invoice.read", ts)
    held = conn.execute(
        f"""
        SELECT permission_id FROM org_permissions
        WHERE code IN ({",".join("?" for _ in HELD_BACK)})
        """,
        HELD_BACK,
    ).fetchall()
    if held:
        ids = [row[0] for row in held]
        conn.execute(
            f"""
            DELETE FROM org_role_permissions
            WHERE role_id=? AND permission_id IN ({",".join("?" for _ in ids)})
            """,
            (ROLE_OPERATOR, *ids),
        )
    conn.execute(
        """
        INSERT INTO org_scopes (
          scope_id, scope_type, display_name, status, created_at, updated_at
        ) VALUES (?, 'structural', 'GGV Finance only', 'ACTIVE', ?, ?)
        ON CONFLICT(scope_id) DO UPDATE SET
          display_name='GGV Finance only', status='ACTIVE', updated_at=excluded.updated_at
        """,
        (nota.SCOPE_GGV_FINANCE, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_scope_targets (scope_id, target_type, target_id, created_at)
        VALUES (?, 'entity', ?, ?)
        ON CONFLICT(scope_id, target_type, target_id) DO NOTHING
        """,
        (nota.SCOPE_GGV_FINANCE, nota.ENTITY_GGV, ts),
    )


def finance_entities(person_id: str | None, conn: sqlite3.Connection) -> list[dict[str, str]]:
    pid = (person_id or "").strip()
    if not pid:
        return []
    rows = conn.execute(
        """
        SELECT DISTINCT pos.role_id
        FROM org_assignments a
        JOIN org_positions pos ON pos.position_id = a.position_id
        WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
          AND pos.status='ACTIVE'
        """,
        (pid,),
    ).fetchall()
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        item = FINANCE_ENTITIES.get(str(row[0]))
        if item and item["id"] not in seen:
            seen.add(item["id"])
            found.append(dict(item))
    order = {"GGV": 0, "AMG": 1, "BZG": 2}
    found.sort(key=lambda item: order.get(item["id"], 9))
    return found


def _money_quantum(currency: str) -> Decimal:
    return Decimal("1") if currency == "IDR" else Decimal("0.01")


def _q(amount: Decimal, currency: str) -> Decimal:
    return amount.quantize(_money_quantum(currency), rounding=ROUND_HALF_UP)


def _decimal(value: Any, label: str) -> Decimal:
    text = str(value if value is not None else "").strip().replace(",", "")
    if not text:
        _fail(f"{label} is required.")
    try:
        number = Decimal(text)
    except Exception as exc:  # noqa: BLE001
        _fail(f"{label} is not a number.")
        raise exc
    if not number.is_finite():
        _fail(f"{label} is not a number.")
    return number


def _one_item(description: Any, index: int) -> str:
    text = str(description or "")
    label = f"Line {index}"
    if not text.strip():
        _fail(f"{label} needs a description.")
    if "\n" in text or "\r" in text or ";" in text or "\t" in text:
        _fail(f"{label} is one item. Split combined lines.")
    if len(re.findall(r"\b\d+(?:[.,]\d+)?\s*[x×]\b", text, flags=re.I)) > 1:
        _fail(f"{label} looks like more than one item. Use a separate line.")
    if re.search(r"(?:rp|idr|\$)\s*\d", text, flags=re.I):
        _fail(f"{label} has a price in the description. Put the price in unit price.")
    cleaned = " ".join(text.split())
    if len(cleaned) > 180:
        _fail(f"{label} is too long for one item.")
    return cleaned


def price_lines(raw_lines: Any, currency: str) -> dict[str, Any]:
    if not isinstance(raw_lines, list) or not raw_lines:
        _fail("Add at least one line.")
    if len(raw_lines) > 40:
        _fail("Too many lines.")
    lines = []
    subtotal = Decimal("0")
    tax_total = Decimal("0")
    grand = Decimal("0")
    for index, raw in enumerate(raw_lines, start=1):
        if not isinstance(raw, dict):
            _fail(f"Line {index} is not a line.")
        description = _one_item(raw.get("description"), index)
        qty = _decimal(raw.get("qty"), f"Line {index} quantity")
        unit = _decimal(raw.get("unit_price"), f"Line {index} unit price")
        if qty <= 0:
            _fail(f"Line {index} quantity must be above zero.")
        if unit < 0:
            _fail(f"Line {index} unit price cannot be negative.")
        rate_raw = raw.get("tax_rate")
        if rate_raw in (None, ""):
            rate = Decimal("0")
            taxable = False
        else:
            rate = _decimal(rate_raw, f"Line {index} tax rate")
            if rate < 0 or rate > 100:
                _fail(f"Line {index} tax rate must be from 0 to 100.")
            taxable = True
        line_sub = _q(qty * unit, currency)
        line_tax = _q(line_sub * rate / Decimal("100"), currency) if taxable else Decimal("0")
        line_total = line_sub + line_tax
        subtotal += line_sub
        tax_total += line_tax
        grand += line_total
        lines.append(
            {
                "line_no": index,
                "description": description,
                "qty": format(qty.normalize(), "f") if qty == qty.to_integral() else format(qty, "f"),
                "unit_price": format(_q(unit, currency), "f"),
                "tax_rate": None if not taxable else format(rate.normalize(), "f"),
                "tax_applicable": taxable,
                "subtotal": format(line_sub, "f"),
                "tax": format(line_tax, "f"),
                "total": format(line_total, "f"),
            }
        )
    return {
        "lines": lines,
        "subtotal": format(subtotal, "f"),
        "tax_total": format(tax_total, "f"),
        "grand_total": format(grand, "f"),
        "currency": currency,
        "rounding": ROUNDING,
    }


def _currency(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return "IDR"
    if not _CURRENCY.fullmatch(text):
        _fail("Currency must be a 3-letter code. Blank means IDR.")
    return text


def _date(value: Any, label: str, *, required: bool) -> str | None:
    text = str(value or "").strip()
    if not text:
        if required:
            _fail(f"{label} is required.")
        return None
    if not _DATE.fullmatch(text):
        _fail(f"{label} must be YYYY-MM-DD.")
    return text


def _sequence_audit(
    conn: sqlite3.Connection,
    *,
    actor: str,
    reason: str,
    previous: int | None,
    nxt: int,
    fmt: str,
) -> None:
    conn.execute(
        """
        INSERT INTO fin_invoice_sequence_audit (
          audit_id, entity_id, actor, reason, previous_value, next_value, format, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (nota._mint("SEQ"), nota.ENTITY_GGV, actor, reason, previous, nxt, fmt, nota._now()),
    )


def seed_ggv_sequence(conn: sqlite3.Connection) -> str:
    """Idempotent GGV seed. Never rewinds. Does not create invoices. Returns inserted, advanced, or kept."""
    row = conn.execute(
        "SELECT format, next_value FROM fin_invoice_sequences WHERE entity_id=?",
        (nota.ENTITY_GGV,),
    ).fetchone()
    if row is None:
        ts = nota._now()
        conn.execute(
            """
            INSERT INTO fin_invoice_sequences (
              entity_id, format, next_value, updated_by, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (nota.ENTITY_GGV, SEQUENCE_FORMAT, SEQUENCE_NEXT, SEQUENCE_ACTOR, ts),
        )
        _sequence_audit(
            conn,
            actor=SEQUENCE_ACTOR,
            reason=SEQUENCE_REASON,
            previous=None,
            nxt=SEQUENCE_NEXT,
            fmt=SEQUENCE_FORMAT,
        )
        if conn.execute("SELECT person_id FROM org_persons WHERE person_id=?", (OWNER_PERSON,)).fetchone():
            nota._audit(
                conn,
                person_id=OWNER_PERSON,
                action="ggv.invoice.sequence.seed",
                resource_type="fin_invoice_sequence",
                resource_id=nota.ENTITY_GGV,
                metadata={"actor": SEQUENCE_ACTOR, "reason": SEQUENCE_REASON, "next_value": SEQUENCE_NEXT},
            )
        return "inserted"
    current = int(row["next_value"])
    fmt = str(row["format"] or SEQUENCE_FORMAT)
    if current < SEQUENCE_NEXT:
        ts = nota._now()
        conn.execute(
            """
            UPDATE fin_invoice_sequences
            SET next_value=?, format=?, updated_by=?, updated_at=?
            WHERE entity_id=? AND next_value=?
            """,
            (SEQUENCE_NEXT, SEQUENCE_FORMAT, SEQUENCE_ACTOR, ts, nota.ENTITY_GGV, current),
        )
        _sequence_audit(
            conn,
            actor=SEQUENCE_ACTOR,
            reason=SEQUENCE_REASON,
            previous=current,
            nxt=SEQUENCE_NEXT,
            fmt=SEQUENCE_FORMAT,
        )
        return "advanced"
    if fmt != SEQUENCE_FORMAT:
        conn.execute(
            "UPDATE fin_invoice_sequences SET format=? WHERE entity_id=? AND next_value>=?",
            (SEQUENCE_FORMAT, nota.ENTITY_GGV, current),
        )
    return "kept"


def _format_number(fmt: str, value: int) -> str:
    try:
        rendered = str(fmt).format(n=int(value))
    except (IndexError, KeyError, ValueError):
        _fail("Invoice sequence format is not usable.", code="sequence_missing", status=500)
    if not _SERIES.fullmatch(rendered):
        _fail("Invoice sequence format must render NNNA.", code="sequence_missing", status=500)
    return rendered


def _series_value(number: str) -> int | None:
    match = _SERIES.fullmatch(number)
    if not match:
        return None
    return int(match.group(1))


def _begin_immediate(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA busy_timeout=8000")
    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as exc:
        if "within a transaction" not in str(exc).lower():
            raise
        conn.rollback()
        conn.execute("BEGIN IMMEDIATE")


def _sequence_row(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute(
        "SELECT format, next_value FROM fin_invoice_sequences WHERE entity_id=?",
        (nota.ENTITY_GGV,),
    ).fetchone()
    if row is None:
        seed_ggv_sequence(conn)
        row = conn.execute(
            "SELECT format, next_value FROM fin_invoice_sequences WHERE entity_id=?",
            (nota.ENTITY_GGV,),
        ).fetchone()
    if row is None:
        _fail("GGV invoice sequence is not seeded.", code="sequence_missing", status=500)
    return row


def _number_taken(conn: sqlite3.Connection, number: str, ignore: str = "") -> bool:
    row = conn.execute(
        "SELECT invoice_id FROM ggv_invoices WHERE entity_id=? AND invoice_number=?",
        (nota.ENTITY_GGV, number),
    ).fetchone()
    return row is not None and str(row[0]) != ignore


def _allocate_locked(conn: sqlite3.Connection, person_id: str) -> str:
    """Caller holds BEGIN IMMEDIATE. Increments next. Does not commit."""
    row = _sequence_row(conn)
    current = int(row["next_value"])
    fmt = str(row["format"])
    number = _format_number(fmt, current)
    if _number_taken(conn, number):
        _fail("That invoice number is already used.", code="duplicate_number", status=409)
    ts = nota._now()
    updated = conn.execute(
        """
        UPDATE fin_invoice_sequences
        SET next_value=?, updated_by=?, updated_at=?
        WHERE entity_id=? AND next_value=?
        """,
        (current + 1, person_id, ts, nota.ENTITY_GGV, current),
    )
    if updated.rowcount != 1:
        _fail("Invoice number allocation collided.", code="duplicate_number", status=409)
    _sequence_audit(
        conn,
        actor=person_id,
        reason=f"Allocated {number} at issue.",
        previous=current,
        nxt=current + 1,
        fmt=fmt,
    )
    return number


def _advance_past_import(conn: sqlite3.Connection, number: str, person_id: str) -> int:
    """Move next past an imported series number. Never decreases next. Caller holds the transaction."""
    series = _series_value(number)
    row = _sequence_row(conn)
    current = int(row["next_value"])
    fmt = str(row["format"])
    if series is None or series < current:
        _sequence_audit(
            conn,
            actor=person_id,
            reason=f"Imported {number}. Sequence left at {current}.",
            previous=current,
            nxt=current,
            fmt=fmt,
        )
        return current
    nxt = series + 1
    ts = nota._now()
    updated = conn.execute(
        """
        UPDATE fin_invoice_sequences
        SET next_value=?, updated_by=?, updated_at=?
        WHERE entity_id=? AND next_value<=?
        """,
        (nxt, person_id, ts, nota.ENTITY_GGV, series),
    )
    if updated.rowcount != 1:
        fresh = int(_sequence_row(conn)["next_value"])
        if fresh > series:
            return fresh
        _fail("Invoice sequence did not advance.", code="duplicate_number", status=409)
    _sequence_audit(
        conn,
        actor=person_id,
        reason=f"Imported {number}. Sequence advanced from {current} to {nxt}.",
        previous=current,
        nxt=nxt,
        fmt=fmt,
    )
    return nxt


def numbering_status(conn: sqlite3.Connection, person_id: str | None = None) -> dict[str, Any]:
    """Next number comes from fin_invoice_sequences. It is assigned at issue, not typed."""
    row = None
    try:
        row = conn.execute(
            "SELECT format, next_value FROM fin_invoice_sequences WHERE entity_id=?",
            (nota.ENTITY_GGV,),
        ).fetchone()
    except sqlite3.Error:
        row = None
    if row is None:
        return {
            "proven": False,
            "pattern": "NNNA",
            "format": SEQUENCE_FORMAT,
            "next": None,
            "next_value": None,
            "assignment": "issue",
            "draft_label": DRAFT_NUMBER_LABEL,
            "confirmation_required": False,
            "operator_types_number": False,
            "can_import": False,
            "reason": "GGV invoice sequence is not seeded.",
        }
    nxt = _format_number(str(row["format"]), int(row["next_value"]))
    can_import = bool(person_id) and nota.person_can(person_id, "finance.invoice.import", conn)
    return {
        "proven": True,
        "pattern": "NNNA",
        "format": str(row["format"]),
        "next": nxt,
        "next_value": int(row["next_value"]),
        "assignment": "issue",
        "draft_label": DRAFT_NUMBER_LABEL,
        "confirmation_required": False,
        "operator_types_number": False,
        "can_import": can_import,
        "historical_not_created": ["064A", "065A", "066A"],
        "reason": DRAFT_NUMBER_LABEL + ".",
    }


def _reject_typed_number(body: dict[str, Any], *, status: str) -> None:
    supplied = str(body.get("invoice_number") or "").strip()
    confirmed = body.get("number_confirmed") is True
    if not supplied and not confirmed:
        return
    if status not in EDITABLE and status != "NEW":
        _fail("An issued invoice number cannot be changed.", code="number_immutable", status=409)
    _fail("The invoice number is assigned on issue.", code="number_assigned_on_issue")


def _norm(value: str | None) -> str:
    return nota.norm_name(value)


def _blank(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def known_customer_links(conn: sqlite3.Connection) -> dict[str, Any]:
    """Report canonical names only when a row exists. Never insert them."""
    wanted = {"the one": None, "keen eye": None}
    rows = conn.execute(
        """
        SELECT counterparty_id, legal_name, trading_name, crm_customer_id
        FROM fin_counterparties
        WHERE entity_id=? AND kind='customer'
        """,
        (nota.ENTITY_GGV,),
    ).fetchall()
    for row in rows:
        for key in wanted:
            blob = _norm(f"{row[1] or ''} {row[2] or ''}")
            if key in blob:
                wanted[key] = row[0]
    if _table(conn, "crm_customers"):
        for row in conn.execute(
            "SELECT customer_id, display_name FROM crm_customers WHERE entity_id=?",
            (nota.ENTITY_GGV,),
        ):
            blob = _norm(row[1])
            for key in wanted:
                if key in blob and wanted[key] is None:
                    wanted[key] = row[0]
    return {
        "the_one": wanted["the one"],
        "keen_eye": wanted["keen eye"],
        "seeded": False,
    }


def _table(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _link_crm(conn: sqlite3.Connection, legal_name: str) -> str | None:
    if not _table(conn, "crm_customers"):
        return None
    target = _norm(legal_name)
    rows = conn.execute(
        "SELECT customer_id, display_name FROM crm_customers WHERE entity_id=?",
        (nota.ENTITY_GGV,),
    ).fetchall()
    hits = [row for row in rows if _norm(row[1]) == target]
    if len(hits) == 1:
        return str(hits[0][0])
    return None


def _history(conn: sqlite3.Connection, invoice_id: str, action: str, person_id: str, detail: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO ggv_invoice_history (
          history_id, invoice_id, action, actor_person_id, detail_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (nota._mint("HST"), invoice_id, action, person_id, json.dumps(detail, default=str), nota._now()),
    )
    nota._audit(
        conn,
        person_id=person_id,
        action=f"ggv.invoice.{action}",
        resource_type="ggv_invoice",
        resource_id=invoice_id,
        metadata=detail,
    )


def _customer_public(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "customer_id": row["counterparty_id"],
        "legal_name": row["legal_name"],
        "trading_name": row["trading_name"],
        "tax_id": row["tax_id"],
        "company_id": row["company_id"],
        "billing_address": row["billing_address"],
        "contact_name": row["contact_name"],
        "email": row["email"],
        "phone": row["phone"],
        "default_terms": row["default_terms"],
        "notes": row["notes"],
        "crm_customer_id": row["crm_customer_id"],
        "status": row["status"],
    }


def create_customer(person_id: str, body: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    nota.require(person_id, "finance.customer.create", conn)
    legal = _blank(body.get("legal_name"))
    if not legal or len(legal) < 2:
        _fail("Legal name is required.")
    name_norm = _norm(legal)
    tax = _blank(body.get("tax_id"))
    tax_norm = re.sub(r"[^a-z0-9]+", "", (tax or "").lower()) or None
    existing = conn.execute(
        """
        SELECT * FROM fin_counterparties
        WHERE entity_id=? AND kind='customer' AND name_norm=?
        """,
        (nota.ENTITY_GGV, name_norm),
    ).fetchone()
    if existing is not None and body.get("use_existing") is not True:
        _fail(
            "A customer with this legal name already exists.",
            code="duplicate_customer",
            status=409,
        )
    if existing is not None:
        return nota.public_payload({"ok": True, "customer": _customer_public(existing), "reused": True})
    if tax_norm:
        tax_hit = conn.execute(
            """
            SELECT counterparty_id FROM fin_counterparties
            WHERE entity_id=? AND tax_norm=?
            """,
            (nota.ENTITY_GGV, tax_norm),
        ).fetchone()
        if tax_hit is not None:
            _fail("That tax id is already on a customer.", code="duplicate_customer", status=409)
    crm_id = _link_crm(conn, legal)
    cid = nota._mint("CUST")
    ts = nota._now()
    conn.execute(
        """
        INSERT INTO fin_counterparties (
          counterparty_id, entity_id, kind, legal_name, trading_name, tax_id, company_id,
          billing_address, contact_name, email, phone, default_terms, notes,
          crm_customer_id, name_norm, tax_norm, status, created_by_person_id, created_at, updated_at
        ) VALUES (?, ?, 'customer', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?)
        """,
        (
            cid,
            nota.ENTITY_GGV,
            legal,
            _blank(body.get("trading_name")),
            tax,
            _blank(body.get("company_id")),
            _blank(body.get("billing_address")),
            _blank(body.get("contact_name")),
            _blank(body.get("email")),
            _blank(body.get("phone")),
            _blank(body.get("default_terms")),
            _blank(body.get("notes")),
            crm_id,
            name_norm,
            tax_norm,
            person_id,
            ts,
            ts,
        ),
    )
    nota._audit(
        conn,
        person_id=person_id,
        action="ggv.customer.create",
        resource_type="fin_counterparty",
        resource_id=cid,
        metadata={"crm_customer_id": crm_id},
    )
    conn.commit()
    row = conn.execute("SELECT * FROM fin_counterparties WHERE counterparty_id=?", (cid,)).fetchone()
    return nota.public_payload({"ok": True, "customer": _customer_public(row), "reused": False})


def search_customers(person_id: str, query: str, conn: sqlite3.Connection) -> dict[str, Any]:
    nota.require(person_id, "finance.customer.read", conn)
    needle = _norm(query)
    rows = conn.execute(
        """
        SELECT * FROM fin_counterparties
        WHERE entity_id=? AND kind='customer' AND status='ACTIVE'
        ORDER BY legal_name
        """,
        (nota.ENTITY_GGV,),
    ).fetchall()
    if needle:
        rows = [
            row
            for row in rows
            if needle in _norm(f"{row['legal_name']} {row['trading_name'] or ''} {row['email'] or ''}")
        ]
    return nota.public_payload(
        {
            "ok": True,
            "customers": [_customer_public(row) for row in rows],
            "known": known_customer_links(conn),
        }
    )


def _customer_or_404(conn: sqlite3.Connection, customer_id: str) -> sqlite3.Row:
    row = conn.execute(
        """
        SELECT * FROM fin_counterparties
        WHERE counterparty_id=? AND entity_id=? AND kind='customer'
        """,
        (customer_id, nota.ENTITY_GGV),
    ).fetchone()
    if row is None:
        _fail("Customer was not found.", code="not_found", status=404)
    return row


def _invoice_or_404(conn: sqlite3.Connection, invoice_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM ggv_invoices WHERE invoice_id=? AND entity_id=?",
        (invoice_id, nota.ENTITY_GGV),
    ).fetchone()
    if row is None:
        _fail("Invoice was not found.", code="not_found", status=404)
    return row


def _display_status(row: sqlite3.Row, today: str) -> str:
    status = str(row["status"])
    due = str(row["due_date"] or "")
    if status == "ISSUED" and due and due < today:
        return "OVERDUE"
    return status


def _from_party(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        "SELECT legal_name, display_name FROM org_entities WHERE entity_id=?",
        (nota.ENTITY_GGV,),
    ).fetchone()
    if row is None:
        return {"legal_name": None, "display_name": "GGV", "address": None, "address_status": "UNKNOWN"}
    return {
        "legal_name": row[0],
        "display_name": row[1] or "GGV",
        "address": None,
        "address_status": "UNKNOWN",
    }


def _invoice_public(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    customer = _customer_or_404(conn, str(row["customer_id"]))
    today = nota._now()[:10]
    display = _display_status(row, today)
    history = conn.execute(
        """
        SELECT action, actor_person_id, detail_json, created_at
        FROM ggv_invoice_history WHERE invoice_id=? ORDER BY created_at
        """,
        (row["invoice_id"],),
    ).fetchall()
    docs = conn.execute(
        """
        SELECT document_id, version, sha256, created_at
        FROM ggv_invoice_documents WHERE invoice_id=? ORDER BY version
        """,
        (row["invoice_id"],),
    ).fetchall()
    return {
        "invoice_id": row["invoice_id"],
        "invoice_number": row["invoice_number"],
        "number_label": row["invoice_number"] or DRAFT_NUMBER_LABEL,
        "invoice_date": row["invoice_date"],
        "due_date": row["due_date"],
        "terms": row["terms"],
        "currency": row["currency"],
        "notes": row["notes"],
        "reference": row["reference"],
        "payment_method": row["payment_method"],
        "payment_reference": row["payment_reference"],
        "lines": json.loads(row["lines_json"]),
        "subtotal": row["subtotal"],
        "tax_total": row["tax_total"],
        "grand_total": row["grand_total"],
        "rounding": json.loads(row["rounding_json"]),
        "status": row["status"],
        "display_status": display,
        "status_label": STATUS_LABEL.get(display, display),
        "number_source": row["number_source"],
        "customer": _customer_public(customer),
        "from": _from_party(conn),
        "created_by": row["created_by_person_id"],
        "finalised_by": row["finalised_by_person_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "issued_at": row["issued_at"],
        "history": [
            {"action": item[0], "actor": item[1], "at": item[3]}
            for item in history
        ],
        "documents": [
            {"document_id": item[0], "version": item[1], "sha256": item[2], "at": item[3]}
            for item in docs
        ],
        "issued_is_not_paid": True,
        "claimed_is_not_verified": True,
    }


def _header(body: dict[str, Any]) -> dict[str, Any]:
    currency = _currency(body.get("currency"))
    invoice_date = _date(body.get("invoice_date"), "Invoice date", required=True)
    due = _date(body.get("due_date"), "Due date", required=False)
    terms = _blank(body.get("terms"))
    if not due and not terms:
        _fail("Enter a due date or payment terms.")
    priced = price_lines(body.get("lines"), currency)
    return {
        "currency": currency,
        "invoice_date": invoice_date,
        "due_date": due,
        "terms": terms,
        "notes": _blank(body.get("notes")),
        "reference": _blank(body.get("reference")),
        "payment_method": _blank(body.get("payment_method")),
        "payment_reference": _blank(body.get("payment_reference")),
        **priced,
    }


def preview_invoice(person_id: str, body: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    nota.require(person_id, "finance.invoice.create", conn)
    header = _header(body)
    customer = None
    if body.get("customer_id"):
        customer = _customer_public(_customer_or_404(conn, str(body.get("customer_id"))))
    return nota.public_payload(
        {
            "ok": True,
            "preview": True,
            "saved": False,
            "customer": customer,
            "from": _from_party(conn),
            "numbering": numbering_status(conn, person_id),
            **header,
        }
    )


def create_invoice(person_id: str, body: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    nota.require(person_id, "finance.invoice.create", conn)
    _reject_typed_number(body, status="NEW")
    customer = _customer_or_404(conn, str(body.get("customer_id") or ""))
    header = _header(body)
    invoice_id = nota._mint("INV")
    ts = nota._now()
    try:
        conn.execute(
            """
            INSERT INTO ggv_invoices (
              invoice_id, entity_id, customer_id, invoice_number, invoice_date, due_date, terms,
              currency, notes, reference, payment_method, payment_reference, lines_json,
              subtotal, tax_total, grand_total, rounding_json, status, number_source,
              created_by_person_id, finalised_by_person_id, created_at, updated_at, issued_at,
              draft_email_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?, NULL, ?, ?, NULL, NULL)
            """,
            (
                invoice_id,
                nota.ENTITY_GGV,
                customer["counterparty_id"],
                None,
                header["invoice_date"],
                header["due_date"],
                header["terms"],
                header["currency"],
                header["notes"],
                header["reference"],
                header["payment_method"],
                header["payment_reference"],
                json.dumps(header["lines"]),
                header["subtotal"],
                header["tax_total"],
                header["grand_total"],
                json.dumps(ROUNDING),
                "assigned_on_issue",
                person_id,
                ts,
                ts,
            ),
        )
    except sqlite3.IntegrityError:
        _fail("That invoice number is already used.", code="duplicate_number", status=409)
    _history(conn, invoice_id, "draft", person_id, {"invoice_number": None, "number_label": DRAFT_NUMBER_LABEL})
    conn.commit()
    row = _invoice_or_404(conn, invoice_id)
    return nota.public_payload({"ok": True, "invoice": _invoice_public(conn, row)})


def edit_invoice(person_id: str, invoice_id: str, body: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    nota.require(person_id, "finance.invoice.edit", conn)
    row = _invoice_or_404(conn, invoice_id)
    _reject_typed_number(body, status=str(row["status"]))
    if row["status"] not in EDITABLE:
        _fail("Only a draft can be edited.")
    customer_id = str(body.get("customer_id") or row["customer_id"])
    customer = _customer_or_404(conn, customer_id)
    header = _header(body)
    number, source = row["invoice_number"], row["number_source"]
    ts = nota._now()
    try:
        conn.execute(
            """
            UPDATE ggv_invoices SET
              customer_id=?, invoice_number=?, invoice_date=?, due_date=?, terms=?,
              currency=?, notes=?, reference=?, payment_method=?, payment_reference=?,
              lines_json=?, subtotal=?, tax_total=?, grand_total=?, number_source=?, updated_at=?
            WHERE invoice_id=?
            """,
            (
                customer["counterparty_id"],
                number,
                header["invoice_date"],
                header["due_date"],
                header["terms"],
                header["currency"],
                header["notes"],
                header["reference"],
                header["payment_method"],
                header["payment_reference"],
                json.dumps(header["lines"]),
                header["subtotal"],
                header["tax_total"],
                header["grand_total"],
                source,
                ts,
                invoice_id,
            ),
        )
    except sqlite3.IntegrityError:
        _fail("That invoice number is already used.", code="duplicate_number", status=409)
    _history(conn, invoice_id, "edit", person_id, {"lines": len(header["lines"])})
    conn.commit()
    return nota.public_payload({"ok": True, "invoice": _invoice_public(conn, _invoice_or_404(conn, invoice_id))})


def list_invoices(person_id: str, conn: sqlite3.Connection, qs: dict[str, list[str]]) -> dict[str, Any]:
    nota.require(person_id, "finance.invoice.read", conn)
    query = ((qs.get("q") or [""])[0]).strip().lower()
    rows = conn.execute(
        "SELECT * FROM ggv_invoices WHERE entity_id=? ORDER BY updated_at DESC",
        (nota.ENTITY_GGV,),
    ).fetchall()
    public = [_invoice_public(conn, row) for row in rows]
    if query:
        public = [
            item
            for item in public
            if query in " ".join(
                [
                    str(item.get("invoice_number") or ""),
                    str(item.get("status_label") or ""),
                    str((item.get("customer") or {}).get("legal_name") or ""),
                ]
            ).lower()
        ]
    return nota.public_payload({"ok": True, "invoices": public, "numbering": numbering_status(conn, person_id)})


def get_invoice(person_id: str, invoice_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    nota.require(person_id, "finance.invoice.read", conn)
    return nota.public_payload({"ok": True, "invoice": _invoice_public(conn, _invoice_or_404(conn, invoice_id))})


def mark_ready(person_id: str, invoice_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    nota.require(person_id, "finance.invoice.issue", conn)
    row = _invoice_or_404(conn, invoice_id)
    if row["status"] != "DRAFT":
        _fail("Only a draft can be marked ready.")
    _header_from_row(row)
    ts = nota._now()
    conn.execute(
        "UPDATE ggv_invoices SET status='READY', updated_at=? WHERE invoice_id=?",
        (ts, invoice_id),
    )
    _history(conn, invoice_id, "ready", person_id, {"approval": "required"})
    conn.commit()
    return nota.public_payload({"ok": True, "invoice": _invoice_public(conn, _invoice_or_404(conn, invoice_id))})


def _header_from_row(row: sqlite3.Row) -> None:
    if not row["due_date"] and not row["terms"]:
        _fail("Enter a due date or payment terms.")
    lines = json.loads(row["lines_json"] or "[]")
    if not lines:
        _fail("Add at least one line.")


def _pdf_escape(text: str) -> str:
    raw = text.encode("latin-1", "replace").decode("latin-1")
    return raw.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def render_pdf(invoice: dict[str, Any]) -> bytes:
    """Text PDF from the stored invoice. The same record always renders the same bytes."""
    party = invoice.get("from") or {}
    customer = invoice.get("customer") or {}
    lines = [
        f"{party.get('display_name') or 'GGV'}  {party.get('legal_name') or ''}".strip(),
        "Invoice",
        f"Number {invoice.get('invoice_number') or ''}",
        f"Date {invoice.get('invoice_date') or ''}",
        f"Due {invoice.get('due_date') or ''}",
        f"Terms {invoice.get('terms') or ''}",
        f"Bill to {customer.get('legal_name') or ''}",
        f"Trading {customer.get('trading_name') or ''}",
        f"Address {customer.get('billing_address') or 'UNKNOWN'}",
    ]
    for line in invoice.get("lines") or []:
        lines.append(
            f"{line.get('line_no')} {line.get('description')}  qty {line.get('qty')}  "
            f"unit {line.get('unit_price')}  tax {line.get('tax')}  total {line.get('total')}"
        )
    lines.extend(
        [
            f"Subtotal {invoice.get('subtotal')} {invoice.get('currency')}",
            f"Tax {invoice.get('tax_total')} {invoice.get('currency')}",
            f"Total {invoice.get('grand_total')} {invoice.get('currency')}",
            f"Payment method {invoice.get('payment_method') or ''}",
            f"Payment reference {invoice.get('payment_reference') or ''}",
            f"Notes {invoice.get('notes') or ''}",
            f"Reference {invoice.get('reference') or ''}",
            "Issued is not paid. Claimed is not verified.",
        ]
    )
    commands = ["BT", "/F1 11 Tf", "48 800 Td"]
    for index, line in enumerate(lines[:55]):
        if index:
            commands.append("0 -14 Td")
        commands.append(f"({_pdf_escape(line)}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{number} 0 obj\n".encode("ascii"))
        out.extend(body)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(out)


def _draft_email(invoice: dict[str, Any]) -> dict[str, Any]:
    number = invoice.get("invoice_number") or "invoice"
    customer = invoice.get("customer") or {}
    recipient = customer.get("email")
    subject = f"Invoice {number}"
    body = (
        f"Please find invoice {number} for {invoice.get('grand_total')} {invoice.get('currency')}.\n"
        "This message is a draft to copy. It has not been sent."
    )
    return {
        "prepared": True,
        "sent": False,
        "gmail_called": False,
        "gmail_draft_created": False,
        "reason": "No sanctioned Gmail draft path is called. Copy this draft.",
        "next_integration": NEXT_INTEGRATION,
        "to": recipient,
        "subject": subject,
        "body": body,
        "pdf_filename": f"{number}.pdf",
        "copy_text": f"To: {recipient or 'UNKNOWN'}\nSubject: {subject}\n\n{body}",
    }


def issue_invoice(person_id: str, invoice_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    nota.require(person_id, "finance.invoice.issue", conn)
    row = _invoice_or_404(conn, invoice_id)
    if row["status"] not in ISSUE_FROM:
        _fail("This invoice cannot be issued from its current state.")
    _header_from_row(row)
    _begin_immediate(conn)
    try:
        locked = _invoice_or_404(conn, invoice_id)
        if locked["status"] not in ISSUE_FROM:
            _fail("This invoice cannot be issued from its current state.")
        if locked["invoice_number"]:
            _fail("An issued invoice number cannot be changed.", code="number_immutable", status=409)
        number = _allocate_locked(conn, person_id)
        public = _invoice_public(conn, locked)
        public["invoice_number"] = number
        public["number_label"] = number
        public["number_source"] = "sequence"
        pdf = render_pdf(public)
        digest = hashlib.sha256(pdf).hexdigest()
        email = _draft_email(public)
        ts = nota._now()
        version = int(
            conn.execute(
                "SELECT COALESCE(MAX(version), 0) FROM ggv_invoice_documents WHERE invoice_id=?",
                (invoice_id,),
            ).fetchone()[0]
        ) + 1
        updated = conn.execute(
            """
            UPDATE ggv_invoices SET
              invoice_number=?, number_source='sequence', status='ISSUED',
              finalised_by_person_id=?, issued_at=?, updated_at=?, draft_email_json=?
            WHERE invoice_id=? AND status IN ('DRAFT', 'READY') AND invoice_number IS NULL
            """,
            (number, person_id, ts, ts, json.dumps(email), invoice_id),
        )
        if updated.rowcount != 1:
            _fail("This invoice cannot be issued from its current state.")
        conn.execute(
            """
            INSERT INTO ggv_invoice_documents (
              document_id, invoice_id, version, sha256, pdf, created_by_person_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (nota._mint("PDF"), invoice_id, version, digest, pdf, person_id, ts),
        )
        _history(
            conn,
            invoice_id,
            "issue",
            person_id,
            {"sha256": digest, "email_sent": False, "invoice_number": number, "gmail_called": False},
        )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        raise
    fresh = _invoice_public(conn, _invoice_or_404(conn, invoice_id))
    again = render_pdf(fresh)
    return nota.public_payload(
        {
            "ok": True,
            "invoice": fresh,
            "pdf_sha256": digest,
            "pdf_reproducible": hashlib.sha256(again).hexdigest() == digest,
            "email_sent": False,
            "draft_email": email,
        }
    )


def void_invoice(person_id: str, invoice_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    nota.require(person_id, "finance.invoice.void", conn)
    row = _invoice_or_404(conn, invoice_id)
    if row["status"] not in VOID_FROM:
        _fail("This invoice cannot be voided from its current state.")
    ts = nota._now()
    kept = row["invoice_number"]
    conn.execute(
        "UPDATE ggv_invoices SET status='VOID', invoice_number=?, updated_at=? WHERE invoice_id=?",
        (kept, ts, invoice_id),
    )
    _history(
        conn,
        invoice_id,
        "void",
        person_id,
        {"invoice_number": kept, "recycled": False, "sequence_rewound": False},
    )
    conn.commit()
    return nota.public_payload({"ok": True, "invoice": _invoice_public(conn, _invoice_or_404(conn, invoice_id))})


def import_historical(person_id: str, body: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    """Owner-only. Keeps the original number. Does not rewind the sequence."""
    nota.require(person_id, "finance.invoice.import", conn)
    number = str(body.get("invoice_number") or "").strip().upper()
    if not _NUMBER.fullmatch(number):
        _fail("Enter the historical invoice number to import.")
    customer = _customer_or_404(conn, str(body.get("customer_id") or ""))
    header = _header(body)
    invoice_id = nota._mint("INV")
    _begin_immediate(conn)
    try:
        if _number_taken(conn, number):
            _fail(
                "That invoice number is already used.",
                code="duplicate_number",
                status=409,
                extra_conflict=True,
            )
        ts = nota._now()
        conn.execute(
            """
            INSERT INTO ggv_invoices (
              invoice_id, entity_id, customer_id, invoice_number, invoice_date, due_date, terms,
              currency, notes, reference, payment_method, payment_reference, lines_json,
              subtotal, tax_total, grand_total, rounding_json, status, number_source,
              created_by_person_id, finalised_by_person_id, created_at, updated_at, issued_at,
              draft_email_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ISSUED', 'imported', ?, ?, ?, ?, ?, NULL)
            """,
            (
                invoice_id,
                nota.ENTITY_GGV,
                customer["counterparty_id"],
                number,
                header["invoice_date"],
                header["due_date"],
                header["terms"],
                header["currency"],
                header["notes"],
                header["reference"],
                header["payment_method"],
                header["payment_reference"],
                json.dumps(header["lines"]),
                header["subtotal"],
                header["tax_total"],
                header["grand_total"],
                json.dumps(ROUNDING),
                person_id,
                person_id,
                ts,
                ts,
                ts,
            ),
        )
        nxt = _advance_past_import(conn, number, person_id)
        _history(
            conn,
            invoice_id,
            "import",
            person_id,
            {"invoice_number": number, "number_source": "imported", "next_value": nxt, "conflict": False},
        )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        raise
    fresh = _invoice_public(conn, _invoice_or_404(conn, invoice_id))
    return nota.public_payload(
        {
            "ok": True,
            "invoice": fresh,
            "imported": True,
            "conflict": False,
            "numbering": numbering_status(conn, person_id),
        }
    )


def claim_paid(person_id: str, invoice_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    nota.require(person_id, "finance.invoice.claim", conn)
    row = _invoice_or_404(conn, invoice_id)
    if row["status"] not in CLAIM_FROM:
        _fail("Only an issued invoice can be marked paid — claimed.")
    ts = nota._now()
    conn.execute(
        "UPDATE ggv_invoices SET status='PAID_CLAIMED', updated_at=? WHERE invoice_id=?",
        (ts, invoice_id),
    )
    _history(conn, invoice_id, "paid_claimed", person_id, {"verified": False, "money_movement": False})
    conn.commit()
    return nota.public_payload(
        {
            "ok": True,
            "invoice": _invoice_public(conn, _invoice_or_404(conn, invoice_id)),
            "payment_executed": False,
            "verified": False,
        }
    )


def invoice_pdf(person_id: str, invoice_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    nota.require(person_id, "finance.invoice.read", conn)
    row = _invoice_or_404(conn, invoice_id)
    doc = conn.execute(
        """
        SELECT pdf, sha256 FROM ggv_invoice_documents
        WHERE invoice_id=? ORDER BY version DESC LIMIT 1
        """,
        (invoice_id,),
    ).fetchone()
    if doc is None:
        _fail("No PDF has been generated. Issue the invoice first.", code="not_found", status=404)
    number = row["invoice_number"] or invoice_id
    return {
        "_file": {
            "data": doc[0],
            "content_type": "application/pdf",
            "filename": f"{number}.pdf",
            "disposition": "inline",
        }
    }


def draft_email(person_id: str, invoice_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    nota.require(person_id, "finance.invoice.read", conn)
    row = _invoice_or_404(conn, invoice_id)
    if not row["draft_email_json"]:
        _fail("Issue the invoice before preparing the draft email.")
    payload = json.loads(row["draft_email_json"])
    payload["sent"] = False
    payload["gmail_called"] = False
    return nota.public_payload({"ok": True, "draft_email": payload, "email_sent": False})


def reports(person_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    nota.require(person_id, "finance.evidence.export", conn)
    desk = desk_snapshot(person_id, conn)
    return nota.public_payload(
        {
            "ok": True,
            "desk": desk,
            "cash": None,
            "profit_and_loss": None,
            "ar_ageing": None,
            "margin": None,
            "tax_position": None,
            "unknown_reason": "Cash, profit, ageing, margin, and tax position are not stored on this desk.",
            "evidence": "Month evidence export remains on the existing nota history.",
        }
    )


def desk_snapshot(person_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    ensure_schema(conn)
    if not nota.person_can(person_id, "finance.invoice.read", conn):
        return {"invoice_access": False, "finance_entities": finance_entities(person_id, conn)}
    today = nota._now()[:10]
    rows = conn.execute(
        "SELECT status, due_date, invoice_id, invoice_number, updated_at FROM ggv_invoices WHERE entity_id=?",
        (nota.ENTITY_GGV,),
    ).fetchall()
    awaiting = 0
    overdue = 0
    claimed = 0
    for row in rows:
        if row[0] in {"DRAFT", "READY"}:
            awaiting += 1
        if row[0] == "ISSUED" and row[1] and str(row[1]) < today:
            overdue += 1
        if row[0] == "PAID_CLAIMED":
            claimed += 1
    activity = conn.execute(
        """
        SELECT action, created_at, invoice_id FROM ggv_invoice_history
        ORDER BY created_at DESC LIMIT 8
        """
    ).fetchall()
    return {
        "invoice_access": True,
        "awaiting_action": awaiting,
        "overdue": overdue,
        "payment_unverified": claimed,
        "invoice_count": len(rows),
        "recent_activity": [
            {"action": item[0], "at": item[1], "invoice_id": item[2]} for item in activity
        ],
        "finance_entities": finance_entities(person_id, conn),
        "cash": None,
        "profit_and_loss": None,
        "ar_ageing": None,
        "margin": None,
        "tax_position": None,
    }


def try_dispatch(
    method: str,
    rest: str,
    qs: dict[str, list[str]],
    body: dict[str, Any],
    person_id: str | None,
) -> dict[str, Any] | None:
    if rest.startswith("/invoices") and (
        rest.endswith("/verify") or rest.endswith("/part-paid") or rest.endswith("/pdf-edit")
    ):
        nota.refuse_money(rest)
    routes = {
        ("GET", "/invoices"),
        ("POST", "/invoices"),
        ("POST", "/invoices/preview"),
        ("POST", "/invoices/import"),
        ("GET", "/customers"),
        ("POST", "/customers"),
        ("GET", "/numbering"),
        ("GET", "/reports"),
        ("GET", "/entities"),
    }
    invoice_match = re.fullmatch(r"/invoices/([^/]+)(?:/(ready|issue|void|claim|pdf|draft-email))?", rest)
    customer_match = re.fullmatch(r"/customers/([^/]+)", rest)
    if (method, rest) not in routes and not invoice_match and not customer_match:
        return None
    conn = nota._open_ready()
    try:
        ensure_schema(conn)
        if method == "GET" and rest == "/entities":
            nota.require(person_id, "finance.nota.read", conn)
            return nota.public_payload({"ok": True, "finance_entities": finance_entities(person_id, conn)})
        if method == "GET" and rest == "/numbering":
            nota.require(person_id, "finance.invoice.read", conn)
            return nota.public_payload({"ok": True, "numbering": numbering_status(conn, person_id)})
        if method == "GET" and rest == "/reports":
            return reports(person_id or "", conn)
        if method == "GET" and rest == "/customers":
            return search_customers(person_id or "", (qs.get("q") or [""])[0], conn)
        if method == "POST" and rest == "/customers":
            return create_customer(person_id or "", body, conn)
        if method == "POST" and rest == "/invoices/preview":
            return preview_invoice(person_id or "", body, conn)
        if method == "POST" and rest == "/invoices/import":
            return import_historical(person_id or "", body, conn)
        if method == "POST" and rest == "/invoices":
            return create_invoice(person_id or "", body, conn)
        if method == "GET" and rest == "/invoices":
            return list_invoices(person_id or "", conn, qs)
        if customer_match and method == "GET":
            nota.require(person_id, "finance.customer.read", conn)
            row = _customer_or_404(conn, customer_match.group(1))
            return nota.public_payload({"ok": True, "customer": _customer_public(row)})
        if not invoice_match:
            return None
        invoice_id, action = invoice_match.group(1), invoice_match.group(2)
        if invoice_id == "preview":
            return None
        if method == "GET" and action is None:
            return get_invoice(person_id or "", invoice_id, conn)
        if method == "POST" and action is None:
            return edit_invoice(person_id or "", invoice_id, body, conn)
        if method == "POST" and action == "ready":
            return mark_ready(person_id or "", invoice_id, conn)
        if method == "POST" and action == "issue":
            return issue_invoice(person_id or "", invoice_id, conn)
        if method == "POST" and action == "void":
            return void_invoice(person_id or "", invoice_id, conn)
        if method == "POST" and action == "claim":
            return claim_paid(person_id or "", invoice_id, conn)
        if method == "GET" and action == "pdf":
            return invoice_pdf(person_id or "", invoice_id, conn)
        if method == "GET" and action == "draft-email":
            return draft_email(person_id or "", invoice_id, conn)
        if action in {"verify", "part-paid", "pay"}:
            nota.refuse_money(rest)
        return None
    finally:
        conn.close()
