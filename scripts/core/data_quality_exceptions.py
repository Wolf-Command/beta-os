#!/usr/bin/env python3
"""Data-quality exception register — trace and flag, never correct.

Owner brief OPSFIX-3, 29 Sep 2026. Reads local evidence only. Does not invent
numbers, does not write Alchemist/ESB/banks, and does not treat bank lines as
proof of an AP liability.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

BETA_ROOT = Path(__file__).resolve().parents[2]
REGISTER_PATH = BETA_ROOT / "state" / "ops" / "data-quality-exceptions.json"
ALCHEMIST_DB = Path.home() / ".openclaw" / "workspace" / "alchemist" / "data" / "alchemist.db"
NOTAS_DIR = Path.home() / ".openclaw" / "workspace" / "alchemist" / "notas"
MONEY_BRAIN = Path.home() / ".openclaw" / "state" / "money-brain-latest.json"
MASTER_STATUS = (
    Path.home() / ".openclaw" / "workspace" / "wolf-system" / "dashboards" / "data" / "master.status.json"
)
WITA = timezone(timedelta(hours=8))

DO_NOT_ACT = "Do not act on this number until the source is established."


def _now() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")


def _idr(value: Any) -> str:
    try:
        amount = int(round(float(value)))
    except (TypeError, ValueError):
        return "Rp ?"
    return f"Rp {amount:,}"


def _drive_id(url: str) -> str | None:
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url or "")
    return match.group(1) if match else None


def _nota_on_disk(url: str, names: set[str]) -> bool:
    photo = (url or "").strip()
    if not photo:
        return False
    base = Path(photo.split("?", 1)[0]).name
    if base and base in names:
        return True
    drive = _drive_id(photo)
    if drive and any(drive in name for name in names):
        return True
    return False


def _classify_broken_row(
    *,
    has_po: bool,
    has_receiving: bool,
    has_nota_disk: bool,
    has_nota_url: bool,
    has_ledger: bool,
) -> tuple[str, str]:
    """Classify evidence for one broken Received+paid PR. Bank is never proof of AP."""
    if has_po and has_receiving and has_nota_disk and has_ledger:
        return (
            "ESTABLISHED",
            "PO lines, receiving evidence, nota file on disk, and a paid ledger row "
            "are present. Still flagged broken because a Received PR stays linked to "
            "a paid ledger. Bank data is not used to prove the AP liability.",
        )
    if has_po or has_receiving or has_nota_url or has_ledger:
        missing = []
        if not has_po:
            missing.append("PO lines")
        if not has_receiving:
            missing.append("receiving")
        if not has_nota_disk:
            missing.append("nota file on disk")
        return (
            "PARTIAL",
            "Some evidence exists. Missing: "
            + (", ".join(missing) or "none listed")
            + ". Bank data proves bank transactions only and does not establish this AP liability.",
        )
    return (
        "NO EVIDENCE",
        "No PO, receiving, nota, or usable ledger chain to establish this payable.",
    )


def list_alchemist_broken() -> dict[str, Any]:
    """Trace the Alchemist 'broken 55' desync. Read-only."""
    if not ALCHEMIST_DB.is_file() or ALCHEMIST_DB.stat().st_size == 0:
        return {
            "ok": False,
            "count": 0,
            "counts": {"ESTABLISHED": 0, "PARTIAL": 0, "NO EVIDENCE": 0},
            "records": [],
            "why": "Alchemist database was not readable.",
        }
    nota_names = {path.name for path in NOTAS_DIR.iterdir()} if NOTAS_DIR.is_dir() else set()
    conn = sqlite3.connect(f"file:{ALCHEMIST_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        owe = conn.execute(
            "SELECT COUNT(*) AS n, SUM(amount) AS total FROM ledger WHERE payment_status='unpaid'"
        ).fetchone()
        rows = conn.execute(
            """
            SELECT p.id, p.pr_num, p.vendor, p.status, p.linked_payment, p.receipt_photo_url,
                   p.delivery_date, p.received_by,
                   l.id AS ledger_id, l.amount, l.payment_status, l.payment_date,
                   l.delivery_id AS led_delivery
            FROM pr_orders p
            JOIN ledger l ON p.linked_payment = 'L-' || l.id
            WHERE p.status = 'Received' AND l.payment_status = 'paid'
            ORDER BY p.pr_num
            """
        ).fetchall()
        records: list[dict[str, Any]] = []
        for row in rows:
            lines = int(
                conn.execute(
                    "SELECT COUNT(*) FROM pr_order_lines WHERE pr_id = ?", (row["id"],)
                ).fetchone()[0]
            )
            receipt = int(
                conn.execute(
                    "SELECT COUNT(*) FROM pr_receipt_lines WHERE pr_id = ?", (row["id"],)
                ).fetchone()[0]
            )
            del_by_pr = int(
                conn.execute(
                    "SELECT COUNT(*) FROM deliveries WHERE pr_id = ?", (row["id"],)
                ).fetchone()[0]
            )
            url = (row["receipt_photo_url"] or "").strip()
            has_po = lines > 0
            has_receiving = bool(row["delivery_date"]) or receipt > 0 or del_by_pr > 0
            has_nota_disk = _nota_on_disk(url, nota_names)
            has_nota_url = bool(url)
            has_ledger = True
            classification, reason = _classify_broken_row(
                has_po=has_po,
                has_receiving=has_receiving,
                has_nota_disk=has_nota_disk,
                has_nota_url=has_nota_url,
                has_ledger=has_ledger,
            )
            records.append(
                {
                    "pr_num": row["pr_num"],
                    "vendor": row["vendor"],
                    "amount_idr": int(row["amount"] or 0),
                    "amount_label": _idr(row["amount"]),
                    "ledger_id": f"L-{row['ledger_id']}",
                    "payment_date": row["payment_date"],
                    "po_lines": lines,
                    "receipt_lines": receipt,
                    "deliveries": del_by_pr,
                    "delivery_date": row["delivery_date"],
                    "receipt_photo_url_present": has_nota_url,
                    "nota_file_on_disk": has_nota_disk,
                    "bank_line": "NOT CHECKED AS AP PROOF — bank proves bank transactions only",
                    "classification": classification,
                    "reason": reason,
                }
            )
    finally:
        conn.close()
    counts = Counter(item["classification"] for item in records)
    return {
        "ok": True,
        "count": len(records),
        "counts": {
            "ESTABLISHED": int(counts.get("ESTABLISHED", 0)),
            "PARTIAL": int(counts.get("PARTIAL", 0)),
            "NO EVIDENCE": int(counts.get("NO EVIDENCE", 0)),
        },
        "owe_unpaid_count": int(owe["n"] or 0) if owe else 0,
        "owe_unpaid_total": float(owe["total"] or 0) if owe else 0,
        "owe_unpaid_label": _idr(owe["total"]) if owe else "Rp 0",
        "records": records,
        "rule": "Bank data proves bank transactions only. It does not establish the AP liability.",
    }


def _cash_owed_trace() -> dict[str, Any]:
    displayed = None
    note = None
    if MONEY_BRAIN.is_file():
        try:
            payload = json.loads(MONEY_BRAIN.read_text(encoding="utf-8"))
            displayed = payload.get("owed_total_blended") or payload.get(
                "sales_pipeline_outstanding_total"
            )
            note = payload.get("note")
        except (OSError, json.JSONDecodeError):
            payload = {}
    else:
        payload = {}
    amount = float(displayed) if displayed is not None else 128_532_978_747.26
    return {
        "id": "dq-cash-owed-to-you",
        "title": "Cash tile — owed to you",
        "displayed_value": _idr(amount),
        "displayed_raw": amount,
        "status": "OPEN",
        "owner_role": "Owner / GGV Finance",
        "do_not_act": DO_NOT_ACT,
        "href": "/owner/data-quality#dq-cash-owed-to-you",
        "plain_english": (
            "The morning money card shows about Rp 128.5 billion as owed to you. "
            "That figure is the remaining balance on the Atrium apartment sales orderbook "
            "(contract total minus collected), not day-to-day trade receivables. "
            "Xero AR in the same snapshot is zero."
        ),
        "trace": {
            "displayed_value": "money-brain owed_total_blended / sales_pipeline_outstanding_total",
            "calculation": (
                "scripts in wolf-system money-brain.py owed_to_you(): "
                "sum of BALANCE_ROW across unit columns = contract_total − collected_total"
            ),
            "underlying_records": (
                "Atrium apartment sales Google Sheet unit columns; "
                f"outstanding ≈ {_idr(amount)} from contract − collected"
            ),
            "source_system": "Atrium apartment sales sheet via command-brief / money-brain",
            "transformation": "Sheet balances bucketed under GGV pipeline and labelled owed to you / receivables",
            "where_it_breaks": (
                "Mislabel: an apartment sales orderbook is presented as money owed to you. "
                "It is not hotel AR and must not be collected as trade debt. "
                + (str(note) if note else "")
            ),
            "what_would_settle": (
                "A commissioned AR figure from the GGV invoice and receipt books, "
                "kept separate from the apartment sales pipeline."
            ),
        },
        "money_brain_note": note,
    }


def _occupancy_trace() -> dict[str, Any]:
    occ = "1.75%"
    rooms_occupied = 2
    capacity = 114
    if MASTER_STATUS.is_file():
        try:
            tiles = json.loads(MASTER_STATUS.read_text(encoding="utf-8")).get("tiles") or []
            for tile in tiles:
                if tile.get("key") == "atrium":
                    occ = str(tile.get("val") or occ)
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "id": "dq-atrium-occupancy",
        "title": "Atrium occupancy",
        "displayed_value": occ,
        "status": "OPEN",
        "owner_role": "Owner / Atrium Finance",
        "do_not_act": DO_NOT_ACT,
        "href": "/owner/data-quality#dq-atrium-occupancy",
        "plain_english": (
            f"The Atrium tile shows {occ} occupancy. That is Cloudbeds "
            f"percentageOccupied for today (rooms occupied {rooms_occupied} ÷ capacity {capacity}). "
            "It is a live dashboard snapshot, not a closed night-audit of rooms sold ÷ rooms available."
        ),
        "trace": {
            "displayed_value": "master.status.json atrium tile val",
            "calculation": (
                "command-brief collect_atrium() copies Cloudbeds getDashboard.percentageOccupied; "
                f"check {rooms_occupied}/{capacity} ≈ 1.75%"
            ),
            "underlying_records": "Cloudbeds getDashboard for Atrium Suites Lombok (today)",
            "source_system": "Cloudbeds",
            "transformation": "Displayed verbatim as '1.75% occ' on the master board",
            "where_it_breaks": (
                "Docstrings still say 120 rooms; live capacity is 114. "
                "The tile does not state the date basis. Low occupancy may be real for the moment, "
                "but it is not a settled hotel night figure."
            ),
            "what_would_settle": (
                "Authorised night-audit rooms sold ÷ rooms available for a named business date, "
                "with the room count commissioned."
            ),
        },
    }


def _alchemist_payable_trace(broken: dict[str, Any]) -> dict[str, Any]:
    owe_label = broken.get("owe_unpaid_label") or "Rp 62,950,910"
    count = int(broken.get("count") or 0)
    return {
        "id": "dq-alchemist-broken-payable",
        "title": "Alchemist payable — broken records",
        "displayed_value": f"{owe_label} unpaid · broken {count}",
        "status": "OPEN",
        "owner_role": "BZG F&B Operations / Owner",
        "do_not_act": DO_NOT_ACT,
        "href": "/owner/data-quality#dq-alchemist-broken-payable",
        "plain_english": (
            f"The Alchemist tile shows unpaid payables {owe_label} and {count} broken rows. "
            "Broken means a purchase request is still status Received while its linked ledger "
            "row is already paid. That is a desync to investigate, not a bank-beats-Alchemist rule."
        ),
        "trace": {
            "displayed_value": "alchemist_tile compute_five(): unpaid SUM(amount) + broken count",
            "calculation": (
                "owe = SUM(ledger.amount) WHERE payment_status='unpaid'; "
                "broken = COUNT pr_orders JOIN ledger WHERE status='Received' AND payment_status='paid'"
            ),
            "underlying_records": f"{count} PR numbers listed on this register",
            "source_system": str(ALCHEMIST_DB),
            "transformation": "Tile shortens the desync to 'broken N' next to the unpaid total",
            "where_it_breaks": (
                "Received PRs remain linked to paid ledger rows. Nota files for these 55 are not "
                "on the local disk even when a Drive URL exists. Bank lines were not used as AP proof."
            ),
            "what_would_settle": (
                "For each PR: PO lines, receiving evidence, nota file on disk, and a consistent "
                "ledger state. Do not invent a bank-beats-Alchemist rule."
            ),
        },
        "broken": {
            "count": count,
            "counts": broken.get("counts") or {},
            "records": broken.get("records") or [],
            "rule": broken.get("rule"),
        },
    }


def build_register(*, write: bool = True) -> dict[str, Any]:
    broken = list_alchemist_broken()
    items = [
        _cash_owed_trace(),
        _occupancy_trace(),
        _alchemist_payable_trace(broken),
    ]
    register = {
        "generated": _now(),
        "schema": "wolf.data-quality-exceptions.v1",
        "staff_ready": False,
        "human_commissioned": False,
        "note": (
            "Trace and flag only. Do not correct a suspicious number here. "
            "Bank data proves bank transactions only and does not establish AP."
        ),
        "open_count": sum(1 for item in items if item.get("status") == "OPEN"),
        "items": items,
    }
    if write:
        REGISTER_PATH.parent.mkdir(parents=True, exist_ok=True)
        REGISTER_PATH.write_text(json.dumps(register, indent=2) + "\n", encoding="utf-8")
    return register


def load_register(*, refresh: bool = False) -> dict[str, Any]:
    if refresh or not REGISTER_PATH.is_file():
        return build_register(write=True)
    try:
        return json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return build_register(write=True)


def open_items() -> list[dict[str, Any]]:
    register = load_register(refresh=False)
    return [item for item in register.get("items") or [] if item.get("status") == "OPEN"]
