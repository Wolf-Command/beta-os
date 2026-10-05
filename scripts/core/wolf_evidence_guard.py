#!/usr/bin/env python3
"""Guard live Beta evidence dirs from test/walkthrough contamination.

Quarantine synthetic walkthrough artifacts without deleting on-disk evidence.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from core.canonical_guard import BETA_CATALOG, is_test_process

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LIVE_CATALOG_DB = BETA_CATALOG

LIVE_CLOSE_RECEIPT_DIR = BETA_ROOT / "state" / "bzg-daily-close" / "receipts"
LIVE_PETTY_RECEIPT_DIR = BETA_ROOT / "state" / "uma-petty-receipts"
LIVE_NOTA_PHOTO_DIR = BETA_ROOT / "state" / "bzg-supplier-notas"
LIVE_PAYMENT_PROOF_DIR = BETA_ROOT / "state" / "bzg-payment-proofs"

QUARANTINE_BASENAME = "quarantine-synthetic-2026-10-05.jsonl"
SYNTHETIC_HASH_PREFIX = "dc907e33c28ecd64"
QUARANTINE_REASON = (
    "synthetic test image from isolated walkthrough harness — never real evidence"
)


def evidence_root() -> Path | None:
    raw = (os.environ.get("WOLF_EVIDENCE_ROOT") or "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def resolve_close_receipt_dir() -> Path:
    root = evidence_root()
    if root is not None:
        return root / "bzg-daily-close" / "receipts"
    return LIVE_CLOSE_RECEIPT_DIR


def resolve_petty_receipt_dir() -> Path:
    root = evidence_root()
    if root is not None:
        return root / "uma-petty-receipts"
    return LIVE_PETTY_RECEIPT_DIR


def resolve_nota_photo_dir() -> Path:
    root = evidence_root()
    if root is not None:
        return root / "bzg-supplier-notas"
    return LIVE_NOTA_PHOTO_DIR


def resolve_payment_proof_dir() -> Path:
    root = evidence_root()
    if root is not None:
        return root / "bzg-payment-proofs"
    return LIVE_PAYMENT_PROOF_DIR


def _under_test_process() -> bool:
    return is_test_process()


def _catalog_db_in_use() -> Path:
    try:
        from core import venue_close as _vc

        return Path(_vc.CATALOG_DB).resolve()
    except Exception:
        return LIVE_CATALOG_DB


def _must_isolate_from_live_evidence() -> bool:
    if _under_test_process():
        return True
    return _catalog_db_in_use() != LIVE_CATALOG_DB


def assert_live_evidence_writable(target_dir: Path, *, label: str) -> None:
    """Refuse writes into live state evidence dirs under test or non-live catalog."""
    resolved = Path(target_dir).resolve()
    live_candidates = (
        LIVE_CLOSE_RECEIPT_DIR.resolve(),
        LIVE_PETTY_RECEIPT_DIR.resolve(),
        LIVE_NOTA_PHOTO_DIR.resolve(),
    )
    if resolved not in live_candidates:
        return
    if not _must_isolate_from_live_evidence():
        return
    raise RuntimeError(
        f"{label}: isolated process refuses writes to live evidence dir "
        f"({resolved}); set WOLF_EVIDENCE_ROOT to a temp copy"
    )


def quarantine_path_for(receipt_dir: Path | None = None) -> Path:
    base = Path(receipt_dir) if receipt_dir else LIVE_CLOSE_RECEIPT_DIR
    return base / QUARANTINE_BASENAME


@lru_cache(maxsize=4)
def _load_quarantine_refs(receipt_dir_str: str) -> frozenset[str]:
    path = Path(receipt_dir_str) / QUARANTINE_BASENAME
    refs: set[str] = set()
    if not path.is_file():
        return frozenset()
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ref = (row.get("object_ref") or "").strip()
            if ref:
                refs.add(ref)
    except OSError:
        return frozenset()
    return frozenset(refs)


def is_quarantined_ref(
    object_ref: str | None,
    *,
    receipt_dir: Path | None = None,
) -> bool:
    ref = (object_ref or "").strip()
    if not ref:
        return False
    base = Path(receipt_dir) if receipt_dir else LIVE_CLOSE_RECEIPT_DIR
    return ref in _load_quarantine_refs(str(base.resolve()))


def refuse_quarantined_ref(
    object_ref: str | None,
    *,
    receipt_dir: Path | None = None,
    label: str = "evidence",
) -> None:
    if is_quarantined_ref(object_ref, receipt_dir=receipt_dir):
        raise ValueError(
            f"{label} object_ref is quarantined synthetic test artifact and "
            "cannot be attached or served"
        )


def clear_quarantine_cache() -> None:
    _load_quarantine_refs.cache_clear()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_quarantine_entries_from_photo_index(
    photo_index: Path,
    *,
    detected_at: str | None = None,
) -> list[dict[str, object]]:
    stamp = detected_at or utc_now_iso()
    out: list[dict[str, object]] = []
    if not photo_index.is_file():
        return out
    for line in photo_index.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ch = (row.get("content_hash") or "").strip()
        if not ch.startswith(SYNTHETIC_HASH_PREFIX):
            continue
        ref = (row.get("object_ref") or "").strip()
        if not ref:
            continue
        out.append(
            {
                "object_ref": ref,
                "close_id": (row.get("close_id") or "").strip() or None,
                "content_hash": ch,
                "reason": QUARANTINE_REASON,
                "detected_at": stamp,
            }
        )
    return out
