#!/usr/bin/env python3
"""Read-only projection of GGV invoice files already on this Mac.

Does not insert a row, does not move the invoice sequence, and does not
invent a number that is not on a file.
"""
from __future__ import annotations

import re
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

BETA_ROOT = Path(__file__).resolve().parents[2]
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
PDF_DIR = Path.home() / ".openclaw" / "workspace" / "wolf-system" / "state" / "pdfs"
MIRRORS = (
    Path.home() / ".openclaw" / "workspace" / "wolf-system" / "state" / "ggv-xero-final" / "07-sqlite-mirror-copy" / "money.sqlite",
    Path.home() / ".openclaw" / "workspace" / "wolf-system" / "state" / "xero-snapshot-20260909" / "mirror" / "money.sqlite",
    Path.home() / ".openclaw" / "workspace" / "wolf-system" / "state" / "xero-snapshot-20260910-final" / "disk-copy" / "money.sqlite",
)
FILE_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-GGV-(\d{3}A)-branded\.pdf$")
NUMBER = re.compile(r"^\d{3}A$")
_CACHE: dict[str, Any] | None = None


def _idr(amount: int | None) -> str | None:
    if amount is None:
        return None
    sign = "-" if amount < 0 else ""
    return f"Rp {sign}{abs(amount):,}"


def _catalog_count(numbers: list[str]) -> int:
    if not CATALOG_DB.is_file() or not numbers:
        return 0
    conn = sqlite3.connect(f"file:{CATALOG_DB}?mode=ro", uri=True)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "ggv_invoices" not in tables:
            return 0
        marks = ",".join("?" for _ in numbers)
        return int(
            conn.execute(
                f"SELECT COUNT(*) FROM ggv_invoices WHERE invoice_number IN ({marks})",
                numbers,
            ).fetchone()[0]
        )
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def _mirror_note() -> str:
    highs = []
    for path in MIRRORS:
        if not path.is_file():
            highs.append(f"{path.parent.name}: missing")
            continue
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            high = conn.execute("SELECT MAX(number) FROM sales_invoice").fetchone()[0]
        except sqlite3.Error:
            high = "unreadable"
        finally:
            conn.close()
        highs.append(f"{path.parent.name}: highest {high}")
    return "; ".join(highs)


def _parse_pdf(path: Path, number: str) -> dict[str, Any]:
    """Number, date, customer, and total only. Bank lines and guest names stay out."""
    text = subprocess.check_output(
        ["pdftotext", "-layout", str(path), "-"],
        text=True,
        timeout=20,
    )
    file_number = None
    match = re.search(r"No\.\s*(\d{3}A)", text)
    if match:
        file_number = match.group(1)
    if file_number != number:
        raise ValueError("file number does not match the name")
    date_match = re.search(r"Date:\s*(\d{1,2} \w+ \d{4})", text)
    due_match = re.search(r"Due:\s*(\d{1,2} \w+ \d{4})", text)
    amounts = [int(item.replace(",", "")) for item in re.findall(r"Rp\s*([0-9][0-9,]*)", text)]
    total = amounts[-1] if amounts and len(set(amounts)) == 1 else (amounts[-1] if amounts else None)
    customer = None
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if "BILL TO" not in line:
            continue
        for nxt in lines[index + 1 : index + 6]:
            parts = [part.strip() for part in re.split(r"\s{2,}", nxt.strip()) if part.strip()]
            if len(parts) >= 2 and parts[-1].upper() != "PT GOSS GROUP VENTURES":
                customer = parts[-1]
                break
        break
    return {
        "invoice_date": date_match.group(1) if date_match else None,
        "due_date": due_match.group(1) if due_match else None,
        "customer_name": customer,
        "grand_total": total,
        "currency": "IDR" if total is not None else None,
    }


def projection() -> dict[str, Any]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    chosen: dict[str, Path] = {}
    if PDF_DIR.is_dir():
        for path in PDF_DIR.iterdir():
            match = FILE_NAME.match(path.name)
            if not match or not path.is_file():
                continue
            number = match.group(2)
            previous = chosen.get(number)
            if previous is None or path.name > previous.name:
                chosen[number] = path
    invoices = []
    for number in sorted(chosen):
        path = chosen[number]
        try:
            parsed = _parse_pdf(path, number)
        except (OSError, subprocess.SubprocessError, ValueError):
            parsed = {
                "invoice_date": None,
                "due_date": None,
                "customer_name": None,
                "grand_total": None,
                "currency": None,
            }
        amount = parsed.get("grand_total")
        invoices.append(
            {
                "invoice_number": number,
                "number_label": number,
                "customer_name": parsed.get("customer_name"),
                "invoice_date": parsed.get("invoice_date"),
                "due_date": parsed.get("due_date"),
                "grand_total": amount,
                "grand_total_idr": _idr(amount if isinstance(amount, int) else None),
                "currency": parsed.get("currency") or "IDR",
                "status_label": "Historical file",
                "read_only": True,
                "href": f"/api/ggv/finance/invoices/historical/{number}/file",
                "source_system": "local-pdf",
                "source_id": path.name,
                "source_path": str(path),
                "source_timestamp": parsed.get("invoice_date"),
                "import_timestamp": None,
                "origin": "historical",
                "verified_by_wolf": False,
                "staff_footnote": "From the branded PDF on disk. Not yet checked in Wolf.",
            }
        )
    numbers = [row["invoice_number"] for row in invoices]
    searched = [
        f"Beta catalog content_library.sqlite ggv_invoices ({_catalog_count(numbers)} of these numbers stored)",
        f"Xero mirror copies of sales_invoice ({_mirror_note()})",
        f"Local invoice files in {PDF_DIR} ({len(invoices)} branded PDFs)",
        "Gmail export files on disk: none found",
    ]
    if invoices:
        message = None
    else:
        message = "Earlier invoices not imported — source: " + "; ".join(searched)
    _CACHE = {
        "found": bool(invoices),
        "invoices": invoices,
        "by_number": {row["invoice_number"]: row for row in invoices},
        "searched": searched,
        "message": message,
        "inserted": False,
    }
    return _CACHE


def file_bytes(number: str) -> tuple[bytes, str] | None:
    if not NUMBER.match(number or ""):
        return None
    row = (projection().get("by_number") or {}).get(number)
    if not row:
        return None
    path = Path(row["source_path"]).resolve()
    root = PDF_DIR.resolve()
    if root not in path.parents or path.suffix.lower() != ".pdf" or not path.is_file():
        return None
    return path.read_bytes(), path.name
