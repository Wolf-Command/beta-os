#!/usr/bin/env python3
"""GGV receipt intake — reuse existing vault pipeline (no second ingest).

Decision served: Finance Control Repair 2026-10-03 Part B (extend) +
existing receipt-from-telegram.py → receipts-inbox → receipt-ingest.py path.

Telegram channel is retired for staff UX; Peaches caption "receipt ggv" + image
files into the SAME identity-vault receipts-inbox via the existing bridge script.
Xero live create remains CANCELLED / fail-closed upstream — this module is
read + intake bridge only. staff_ready stays false.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
VAULT = Path("/Users/wolfterminal/.openclaw/identity-vault")
RECEIPTS_INBOX = VAULT / "receipts-inbox"
RECEIPTS_PROCESSED = VAULT / "receipts-processed"
RECEIPTS_ARCHIVE = VAULT / "receipts-archive"
BRIDGE = Path(
    "/Users/wolfterminal/.openclaw/workspace/wolf-system/scripts/receipt-from-telegram.py"
)
INGEST = Path(
    "/Users/wolfterminal/.openclaw/workspace/wolf-system/scripts/receipt-ingest.py"
)

HONESTY = {
    "staff_ready": False,
    "eng_proved": False,
    "proven": False,
    "second_pipeline": False,
    "reuses_receipt_from_telegram": True,
    "reuses_receipts_inbox": True,
    "telegram_channel_retired_for_staff_ux": True,
    "peaches_caption_intake": "receipt ggv",
    "xero_live_create": "CANCELLED_FAIL_CLOSED",
    "money_movement": False,
    "image_permanent": True,
}

_CAPTION_RE = re.compile(
    r"^\s*receipt\s+ggv\b(?:\s+(.+))?$",
    re.IGNORECASE,
)
_MEDIA_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".pdf"}


class GgvReceiptIntakeError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid",
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.details = dict(details or {})


def parse_peaches_receipt_caption(caption: str | None) -> dict[str, Any]:
    """Parse Peaches 'receipt ggv …' caption. Does not invent tenant from merchant."""
    raw = (caption or "").strip()
    m = _CAPTION_RE.match(raw)
    if not m:
        return {
            "ok": False,
            "matched": False,
            "tenant": None,
            "note": None,
            "message": "Caption must start with 'receipt ggv' (tenant stated, not guessed).",
        }
    note = (m.group(1) or "").strip() or None
    return {
        "ok": True,
        "matched": True,
        "tenant": "GGV",
        "tenant_source": "stated",
        "note": note,
        "caption": raw,
        **HONESTY,
    }


def _load_meta(path: Path) -> dict[str, Any] | None:
    meta = Path(str(path) + ".meta.json")
    if not meta.is_file():
        # also try sibling .jpg.meta.json style already used
        alt = path.with_suffix(path.suffix + ".meta.json")
        if alt.is_file():
            meta = alt
        else:
            return None
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _is_ggv_receipt(name_l: str, meta_tenant: str | None) -> bool:
    """Entity isolation — meta tenant wins; exclude AMG/BZG filename infixes."""
    if "_bzg_receipt_" in name_l or "_amg_receipt_" in name_l:
        return False
    if meta_tenant in ("BZG", "AMG"):
        return False
    if meta_tenant == "GGV":
        return True
    if "_ggv_receipt_" in name_l:
        return True
    return False


def _scan_dir(folder: Path, *, queue: str, tenant: str = "GGV") -> list[dict[str, Any]]:
    if not folder.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(folder.iterdir(), key=lambda x: x.name, reverse=True):
        if not p.is_file():
            continue
        if p.name.endswith(".meta.json"):
            continue
        if p.suffix.lower() not in _MEDIA_EXT:
            continue
        name_l = p.name.lower()
        meta = _load_meta(p)
        meta_tenant = None
        if meta:
            meta_tenant = str(meta.get("tenant") or "").upper() or None
        is_ggv = _is_ggv_receipt(name_l, meta_tenant)
        if tenant == "GGV" and not is_ggv:
            continue
        try:
            st = p.stat()
            size = int(st.st_size)
            mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(
                timespec="seconds"
            ).replace("+00:00", "Z")
        except OSError:
            size = None
            mtime = None
        out.append(
            {
                "filename": p.name,
                "queue": queue,
                "tenant": meta_tenant or ("GGV" if is_ggv else None),
                "path": str(p),
                "size_bytes": size,
                "mtime": mtime,
                "meta": meta,
                "sender": (meta or {}).get("sender_slug"),
                "note": (meta or {}).get("note"),
                "reimburse": bool((meta or {}).get("reimburse")),
                "uploaded_via": (meta or {}).get("uploaded_via"),
                "image_retrievable": p.is_file(),
                "xero_booked": False,
                "processing_status": queue.upper(),
            }
        )
    return out


def list_ggv_receipts(*, limit: int = 100) -> dict[str, Any]:
    """Accountant-visible receipt queues from the existing vault (RO)."""
    lim = max(1, min(int(limit or 100), 500))
    inbox = _scan_dir(RECEIPTS_INBOX, queue="inbox")
    processed = _scan_dir(RECEIPTS_PROCESSED, queue="processed")
    archive = _scan_dir(RECEIPTS_ARCHIVE, queue="archive")
    all_rows = inbox + processed + archive
    all_rows.sort(key=lambda r: r.get("mtime") or "", reverse=True)
    rows = all_rows[:lim]
    return {
        "ok": True,
        "source": "identity_vault_receipts",
        "live_esb_used": False,
        "queues": {
            "inbox": len(inbox),
            "processed": len(processed),
            "archive": len(archive),
        },
        "receipts": rows,
        "count": len(rows),
        "bridge_script": str(BRIDGE) if BRIDGE.is_file() else None,
        "ingest_script": str(INGEST) if INGEST.is_file() else None,
        "bridge_present": BRIDGE.is_file(),
        "ingest_present": INGEST.is_file(),
        "inbox_path": str(RECEIPTS_INBOX),
        "remaining": {
            "peaches_live_hook": "Wire Peaches chat handler to POST intake (caption + media path)",
            "accounting_ui_queues": "ggv_receipt_accounting1 — needs_coding / needs_review / unmatched / duplicate",
            "bank_statement_import": "ggv_bank_statement1 FILE_IMPORT_ONLY — originals + normalised txns + propose-only match",
            "human_confirm_vs_extraction": "ggv_receipt_accounting1 confirm keeps extraction beside human fields",
            "xero_replacement_ledger": "receipt-ingest remains fail-closed for Xero create",
        },
        **HONESTY,
    }


def file_via_existing_bridge(
    *,
    media_path: str,
    sender: str = "mr_wolf",
    caption: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """File image through existing receipt-from-telegram.py into receipts-inbox.

    Does not invent a second pipeline. Does not call Xero.
    """
    parsed = parse_peaches_receipt_caption(caption or f"receipt ggv {note or ''}".strip())
    if not parsed.get("matched"):
        raise GgvReceiptIntakeError(
            parsed.get("message") or "caption must be receipt ggv",
            code="caption_mismatch",
        )
    if not BRIDGE.is_file():
        raise GgvReceiptIntakeError(
            "Existing receipt-from-telegram.py missing — cannot file without second pipeline.",
            code="bridge_missing",
            http_status=503,
        )
    src = Path(media_path)
    if not src.is_file():
        raise GgvReceiptIntakeError("media_path not found", code="media_missing", http_status=404)
    use_note = note if note is not None else parsed.get("note")
    cmd = [
        sys.executable,
        str(BRIDGE),
        "--media-path",
        str(src.resolve()),
        "--tenant",
        "GGV",
        "--sender",
        (sender or "mr_wolf").strip(),
        "--caption",
        caption or "receipt ggv",
    ]
    if use_note:
        cmd.extend(["--note", str(use_note)])
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        raise GgvReceiptIntakeError(
            f"bridge failed: {type(exc).__name__}",
            code="bridge_error",
            http_status=500,
        ) from exc
    body = (proc.stdout or "").strip()
    parsed_out: dict[str, Any]
    try:
        parsed_out = json.loads(body) if body else {}
    except json.JSONDecodeError:
        parsed_out = {"ok": proc.returncode == 0, "raw_stdout": body[-500:]}
    return {
        "ok": bool(parsed_out.get("ok")) and proc.returncode == 0,
        "returncode": proc.returncode,
        "bridge": parsed_out,
        "stderr_tail": (proc.stderr or "")[-400:],
        "filed_path": parsed_out.get("filed_path"),
        "tenant": "GGV",
        **HONESTY,
    }


def api_matches(path: str) -> bool:
    raw = (path or "").split("?")[0].rstrip("/") or "/"
    return raw in {
        "/api/ggv/finance/receipts",
        "/api/ggv/accounting/receipts",
    }
