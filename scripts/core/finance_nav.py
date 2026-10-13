#!/usr/bin/env python3
"""Shared Finance navigation. One vocabulary, three companies, existing routes.

Gate 1 of the canonical architecture. This module does not open a book,
copy a row, post a journal, pay a bill, or file a return. Secondary links
point at the desks that already own the data.
"""
from __future__ import annotations

from typing import Any

from core import entity_books
from core import ggv_finance_invoice as invoices
from core import rbac

PRIMARY_LABELS: tuple[str, ...] = (
    "Overview",
    "Banking",
    "Transactions",
    "Sales",
    "Purchases",
    "Expenses",
    "Reconciliation",
    "Accounting",
    "Tax",
    "Reports",
)

_ALIASES = {
    "GGV": "ENT-GGV",
    "AMG": "ENT-AMG",
    "ATRIUM": "ENT-AMG",
    "BZG": "ENT-BZG",
    "ENT-GGV": "ENT-GGV",
    "ENT-AMG": "ENT-AMG",
    "ENT-BZG": "ENT-BZG",
}

READ = ("finance.nota.read", "atrium.board.read")
ACCOUNTANT = ("finance.records.read",)
REVIEW = ("finance.recon.review", "finance.nota.read", "atrium.board.read")


class FinanceNavError(Exception):
    def __init__(self, message: str, *, code: str = "forbidden", http_status: int = 403):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _item(
    item_id: str,
    label: str,
    href: str,
    requires_any: tuple[str, ...] = READ,
    note: str = "",
) -> dict[str, Any]:
    return {
        "id": item_id,
        "label": label,
        "href": href,
        "requires_any": list(requires_any),
        "note": note,
        "payment_execute": False,
        "journal_post": False,
        "government_filing": False,
    }


def _areas(items: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    missing = [label for label in PRIMARY_LABELS if label not in items]
    if missing:
        raise FinanceNavError(
            "Finance navigation is missing an area.",
            code="invalid_nav",
            http_status=500,
        )
    return [{"id": label.lower(), "label": label, "items": items[label]} for label in PRIMARY_LABELS]


def _ggv() -> list[dict[str, Any]]:
    return _areas(
        {
            "Overview": [
                _item("ggv-overview", "Finance overview", "/ggv/finance"),
            ],
            "Banking": [
                _item("ggv-banking", "Bank accounts and statements", "/ggv/finance/banking"),
                _item("ggv-statements", "Statement library", "/ggv/finance/statements"),
            ],
            "Transactions": [
                _item("ggv-transactions", "Bank transactions", "/ggv/finance/transactions"),
            ],
            "Sales": [
                _item("ggv-invoices", "Customer invoices", "/ggv/finance/invoices"),
                _item("ggv-customers", "Customers", "/ggv/finance/customers"),
            ],
            "Purchases": [
                _item("ggv-bills", "Supplier bills", "/ggv/finance/bills"),
                _item("ggv-suppliers", "Suppliers", "/ggv/finance/vendors"),
            ],
            "Expenses": [
                _item("ggv-notas", "Notas", "/ggv/finance/notas"),
                _item("ggv-receipts", "Peaches receipts", "/ggv/finance/receipts"),
                _item("ggv-missing", "Missing evidence", "/ggv/finance/missing-evidence"),
                _item(
                    "ggv-reimbursements",
                    "Matt and Amanda reimbursements",
                    "/ggv/finance/accountant",
                    ACCOUNTANT,
                    "Stored GGV rows only. An empty schedule is not filled in.",
                ),
            ],
            "Reconciliation": [
                _item("ggv-recon", "Bank reconciliation", "/ggv/finance/reconciliation", REVIEW),
                _item(
                    "ggv-september-exceptions",
                    "September bank exceptions",
                    "/ggv/finance/accountant",
                    REVIEW,
                    "Alfamart, Blu Zone, Keen Eye, Canva, and ATM. Not the invoice or tax gaps.",
                ),
            ],
            "Accounting": [
                _item(
                    "ggv-accountant",
                    "Accountant workspace",
                    "/ggv/finance/accountant",
                    ACCOUNTANT,
                ),
                _item("ggv-audit", "Audit history", "/ggv/finance/audit"),
                _item("ggv-history", "Filing and review history", "/ggv/finance/history"),
            ],
            "Tax": [
                _item(
                    "ggv-tax",
                    "Tax preparation",
                    "/ggv/finance/accountant",
                    ("finance.filing.record", "finance.records.read"),
                    "NPWP, PKP, and regimes stay unverified until ILA records them. Wolf does not file.",
                ),
            ],
            "Reports": [
                _item("ggv-reports", "Evidence and exports", "/ggv/finance/reports"),
            ],
        }
    )


def _amg() -> list[dict[str, Any]]:
    return _areas(
        {
            "Overview": [
                _item("amg-board", "Hotel position", "/amg/finance"),
                _item("amg-overview", "Operational overview", "/amg-finance-ops"),
            ],
            "Banking": [
                _item("amg-banking", "Bank accounts and statements", "/amg/finance/banking"),
                _item("amg-statements", "Statement library", "/amg/finance/statements"),
            ],
            "Transactions": [
                _item("amg-transactions", "Bank transactions", "/amg/finance/transactions"),
            ],
            "Sales": [
                _item("amg-invoices", "Customer invoices", "/amg/finance/invoices"),
                _item("amg-customers", "Customers", "/amg/finance/customers"),
            ],
            "Purchases": [
                _item("amg-bills", "Supplier bills", "/amg/finance/bills"),
                _item("amg-suppliers", "Suppliers", "/amg/finance/vendors"),
            ],
            "Expenses": [
                _item("amg-notas", "Notas", "/amg/finance/notas"),
                _item("amg-receipts", "Receipts", "/amg/finance/receipts"),
                _item("amg-missing", "Missing evidence", "/amg/finance/missing-evidence"),
            ],
            "Reconciliation": [
                _item("amg-recon", "Bank reconciliation", "/amg/finance/reconciliation", REVIEW),
            ],
            "Accounting": [
                _item("amg-ledger", "General ledger", "/amg/finance/ledger"),
                _item("amg-chart", "Chart of accounts", "/amg/finance/accounts"),
                _item("amg-journals", "Journals", "/amg/finance/journals"),
                _item("amg-approvals", "Approvals", "/amg/finance/approvals"),
                _item("amg-audit", "Audit history", "/amg/finance/audit"),
            ],
            "Tax": [
                _item(
                    "amg-tax",
                    "Tax records",
                    "/amg/finance/reports",
                    note="Hotel reports. No tax liability is calculated on this navigation.",
                ),
            ],
            "Reports": [
                _item("amg-hotel-reports", "Hotel reports", "/amg/finance/reports"),
            ],
        }
    )


def _bzg() -> list[dict[str, Any]]:
    return _areas(
        {
            "Overview": [
                _item("bzg-overview", "Finance overview", "/bzg/finance"),
                _item("bzg-outlets", "Outlet reporting", "/bzg/outlets"),
            ],
            "Banking": [
                _item("bzg-bank", "Bank", "/bzg/finance/bank"),
                _item("bzg-statements", "Statements", "/bzg/finance/statements"),
            ],
            "Transactions": [
                _item("bzg-txns", "Bank transactions", "/bzg/finance/bank"),
            ],
            "Sales": [
                _item(
                    "bzg-venue",
                    "Venue sales",
                    "/bzg/venue-pnl",
                    note="ESB remains the POS sales source. This link does not invent a second total.",
                ),
            ],
            "Purchases": [
                _item("bzg-ap", "Accounts payable", "/bzg/finance/ap"),
                _item("bzg-suppliers", "Suppliers", "/bzg/finance/suppliers"),
                _item("bzg-pos", "Purchase orders", "/bzg/uma-blu/purchase-orders"),
                _item("bzg-bills", "Supplier bills", "/bzg/uma-blu/bills"),
                _item(
                    "bzg-ready",
                    "Ready to pay review",
                    "/bzg/finance/ready-to-pay",
                    note="Review queue. This screen does not pay.",
                ),
            ],
            "Expenses": [
                _item("bzg-petty", "Petty cash", "/bzg/finance/petty"),
                _item("bzg-photos", "Receipt photographs", "/bzg/finance/photos-to-review"),
            ],
            "Reconciliation": [
                _item("bzg-exceptions", "Exceptions", "/bzg/finance/exceptions", REVIEW),
                _item("bzg-completeness", "Completeness", "/bzg/finance/completeness", REVIEW),
                _item(
                    "bzg-nightly-close",
                    "Nightly close",
                    "/uma-blu-close",
                    note="Uma Blu close workflow. A finance-only seat is still stopped by the current finance wall.",
                ),
            ],
            "Accounting": [
                _item("bzg-evidence", "Purchase evidence", "/bzg/uma-blu/evidence"),
                _item(
                    "bzg-books",
                    "BZG books shell",
                    "/bzg/finance",
                    note="The BZG book file is separate from AMG and GGV. This link does not post a journal.",
                ),
            ],
            "Tax": [
                _item(
                    "bzg-tax",
                    "Tax records",
                    "/bzg/finance/completeness",
                    note="No BZG tax liability is stored on this navigation.",
                ),
            ],
            "Reports": [
                _item("bzg-venue-report", "Venue report", "/bzg/venue-pnl"),
                _item("bzg-completeness-report", "Completeness report", "/bzg/finance/completeness"),
            ],
        }
    )


_BUILDERS = {
    "ENT-GGV": _ggv,
    "ENT-AMG": _amg,
    "ENT-BZG": _bzg,
}


def normalize_entity(entity_id: str | None) -> str:
    key = (entity_id or "").strip().upper()
    found = _ALIASES.get(key)
    if found is None:
        raise FinanceNavError("Unknown company.", code="unknown_entity", http_status=404)
    return found


def catalog(entity_id: str) -> list[dict[str, Any]]:
    """Full navigation for one company, before permission filtering."""
    eid = normalize_entity(entity_id)
    return _BUILDERS[eid]()


def permission_codes(entity_id: str) -> list[str]:
    codes: list[str] = []
    for area in catalog(entity_id):
        for item in area["items"]:
            for code in item["requires_any"]:
                if code not in codes:
                    codes.append(code)
    return codes


def visible_areas(entity_id: str, allowed: set[str]) -> list[dict[str, Any]]:
    areas = []
    for area in catalog(entity_id):
        items = [
            item
            for item in area["items"]
            if any(code in allowed for code in item["requires_any"])
        ]
        areas.append(
            {
                "id": area["id"],
                "label": area["label"],
                "items": items,
                "empty_note": "" if items else "Nothing in this area for this assignment.",
            }
        )
    return areas


def _held_codes(person_id: str, entity_id: str, conn: Any) -> set[str]:
    ctx = {"entity_id": entity_id}
    return {
        code
        for code in permission_codes(entity_id)
        if rbac.can(person_id, code, ctx, conn=conn)
    }


def for_person(person_id: str, entity_id: str, conn: Any) -> dict[str, Any]:
    eid = normalize_entity(entity_id)
    pid = (person_id or "").strip()
    if not pid or not invoices._can_access_finance_entity(pid, eid, conn):
        raise FinanceNavError(
            "Finance for this company is not on this assignment.",
            code="forbidden",
            http_status=403,
        )
    chip = invoices.ENTITY_FINANCE_CHIP[eid]
    areas = visible_areas(eid, _held_codes(pid, eid, conn))
    return {
        "ok": True,
        "entity_id": eid,
        "company_id": chip["id"],
        "company_label": chip["label"],
        "books_file": entity_books.ENTITY_FILES[eid],
        "books_merged": False,
        "areas": areas,
        "primary_labels": list(PRIMARY_LABELS),
        "payment_execute": False,
        "journal_post": False,
        "government_filing": False,
        "staff_ready": False,
        "human_commissioned": False,
    }
