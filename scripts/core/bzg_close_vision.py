#!/usr/bin/env python3
"""BZG Daily Close vision — RECEIPT_IMAGE_EXTRACTION capability.

Capability-backed (Wolf model_router vision_extract). Never hardcode a single
provider in staff UX. Vision is an accelerator; human-confirmed values are
authoritative. Provider failure must soft-fail with staff-safe copy.

Decision: 2026-10-02 Owner order VISION-CAPABILITY-1 (false ENG_PROVED fix).
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

PACK = "BZG-CLOSE-VISION-CAPABILITY-1"
CAPABILITY = "RECEIPT_IMAGE_EXTRACTION"
LOW_CONFIDENCE_FLOOR = 0.55

# Staff-facing only — never provider/key names.
STAFF_VISION_UNAVAILABLE = (
    "Receipt reading is temporarily unavailable. "
    "Retry or enter the figures manually."
)

HONESTY = {
    "pack": PACK,
    "capability": CAPABILITY,
    "ai_is_not_accounting_truth": True,
    "vision_draft_requires_human_confirm": True,
    "low_confidence_does_not_invent": True,
    "vision_is_accelerator_not_authority": True,
    "provider_failure_must_not_block_close": True,
}

_log = logging.getLogger("bzg_close_vision")


class VisionError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "vision_error",
        http_status: int = 400,
        staff_message: str | None = None,
        diagnostic: str | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.staff_message = staff_message or STAFF_VISION_UNAVAILABLE
        self.diagnostic = diagnostic or message


def _num_or_none(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if n < 0:
        return None
    return round(n, 2)


def _int_or_none(v: Any) -> int | None:
    if v is None or v == "":
        return None
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return None
    if n < 0:
        return None
    return n


def _confidence_band(conf: float | None) -> str:
    if conf is None:
        return "UNKNOWN"
    if conf < LOW_CONFIDENCE_FLOOR:
        return "LOW"
    if conf < 0.8:
        return "MEDIUM"
    return "HIGH"


def _blank_low(fields: dict[str, Any], conf: float | None) -> dict[str, Any]:
    out = dict(fields)
    band = _confidence_band(conf)
    out["ocr_confidence"] = conf
    out["ocr_confidence_band"] = band
    if band == "LOW" and conf is not None and conf < 0.35:
        for k in (
            "edc_card_amount",
            "qris_amount",
            "cash_amount",
            "gross_amount",
            "net_sales",
            "receipt_total",
            "batch_ref",
            "acquirer_label",
            "settlement_batch_date",
            "terminal_label",
            "bills",
            "pax",
        ):
            if k in out:
                out[k] = None
        out["payment_methods"] = []
        out["low_confidence_flag"] = True
    return out


def _parse_json_loose(text: str) -> dict[str, Any]:
    if not text:
        return {}
    text = text.strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return {}
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        return {}


def _dry_run() -> bool:
    raw = (
        os.environ.get("BETA_LLM_DRY_RUN")
        or os.environ.get("WOLF_CLOSE_VISION_DRY")
        or ""
    ).strip()
    return raw.lower() in ("1", "true", "yes", "on")


def _staff_sanitize(msg: str | None) -> str:
    """Strip provider/key names from any string that might reach staff UI."""
    if not msg:
        return STAFF_VISION_UNAVAILABLE
    low = msg.lower()
    banned = (
        "gemini",
        "anthropic",
        "openai",
        "claude",
        "gpt-",
        "api_key",
        "api key",
        "google_api",
        "generativelanguage",
        "not authorised",
        "not authorized",
        "unauthorized",
        "401",
        "403",
        "bearer",
    )
    if any(b in low for b in banned):
        return STAFF_VISION_UNAVAILABLE
    # Keep short operational messages; otherwise staff-safe default.
    if len(msg) > 180:
        return STAFF_VISION_UNAVAILABLE
    return msg


def _import_model_router():
    """Load Wolf model_router from authorised workspace paths."""
    candidates = []
    env = (os.environ.get("WOLF_MODEL_ROUTER_PATH") or "").strip()
    if env:
        candidates.append(Path(env))
    home = Path.home()
    candidates.extend(
        [
            home / ".openclaw" / "workspace" / "wolf-system" / "scripts" / "model_router.py",
            Path("/Users/wolfterminal/.openclaw/workspace/wolf-system/scripts/model_router.py"),
        ]
    )
    for p in candidates:
        if p.is_file():
            parent = str(p.parent)
            if parent not in sys.path:
                sys.path.insert(0, parent)
            import model_router as mr  # type: ignore

            return mr
    return None


def call_receipt_image_extraction(
    prompt: str,
    *,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> tuple[str, str, str]:
    """Capability RECEIPT_IMAGE_EXTRACTION via Wolf vision_extract router.

    Returns (text, provider, model). Raises VisionError(code=vision_unavailable)
    with staff-safe message when no authorised provider can complete the call.
    Never prints secrets. Diagnostic detail stays on the exception only.
    """
    if not image_bytes:
        raise VisionError(
            "image required",
            code="missing_image",
            http_status=400,
            staff_message="Take Photo or Upload Photo for the receipt first.",
        )

    mr = _import_model_router()
    if mr is None:
        raise VisionError(
            "model_router unavailable",
            code="vision_unavailable",
            http_status=503,
            diagnostic="RECEIPT_IMAGE_EXTRACTION: model_router not found on disk",
        )

    b64 = base64.b64encode(image_bytes).decode("ascii")
    # model_router _cap_b64/_img_media_type expect RAW base64 (no data-URL prefix)
    images = [b64]
    try:
        result = mr.route(
            "vision_extract",
            prompt,
            budget="low",
            max_tokens=2500,
            images=images,
            use_cache=False,
        )
    except Exception as exc:  # noqa: BLE001
        diag = f"RECEIPT_IMAGE_EXTRACTION route failed: {type(exc).__name__}"
        _log.warning("%s", diag)
        raise VisionError(
            STAFF_VISION_UNAVAILABLE,
            code="vision_unavailable",
            http_status=503,
            diagnostic=diag,
        ) from exc

    if not isinstance(result, dict):
        raise VisionError(
            STAFF_VISION_UNAVAILABLE,
            code="vision_unavailable",
            http_status=503,
            diagnostic="RECEIPT_IMAGE_EXTRACTION: empty router result",
        )
    text = (result.get("text") or "").strip()
    provider = str(result.get("provider") or "unknown")
    model = str(result.get("model") or "")
    if not text:
        raise VisionError(
            STAFF_VISION_UNAVAILABLE,
            code="vision_unavailable",
            http_status=503,
            diagnostic=f"RECEIPT_IMAGE_EXTRACTION: empty text from {provider}",
        )
    return text, provider, model


# Back-compat alias — callers must not assume Gemini.
def call_gemini_vision(
    prompt: str,
    *,
    image_bytes: bytes | None,
    mime_type: str = "image/jpeg",
    model: str | None = None,
    api_key: str | None = None,
) -> tuple[str, str, str]:
    del model, api_key  # capability router owns provider selection
    if not image_bytes:
        raise VisionError(
            STAFF_VISION_UNAVAILABLE,
            code="missing_image",
            http_status=400,
            staff_message="Take Photo or Upload Photo for the receipt first.",
        )
    return call_receipt_image_extraction(
        prompt, image_bytes=image_bytes, mime_type=mime_type
    )


EDC_PROMPT = """Extract settlement receipt fields as JSON only.
Keys: acquirer_label, terminal_label, settlement_batch_date (YYYY-MM-DD),
edc_card_amount (number, card/EDC only — NEVER include QRIS),
qris_amount (number, QRIS only — NEVER merge into edc_card_amount),
batch_ref, ocr_confidence (0..1).
If unsure, use null and lower ocr_confidence. Do not invent amounts or TIDs.
EDC card and QRIS must stay separate."""


ESB_PROMPT = """Extract ESB / POS closing receipt fields as JSON only.
This is an Indonesian restaurant day-end closing receipt (Uma Blu / ESB).
Read EVERY printed payment line carefully. Amounts are Indonesian Rupiah integers
(no currency symbol). Do not drop zeros. Do not confuse 545000 with 5450000.
Return JSON with these keys:
- cash_amount
- edc_card_amount (sum of all EDC/card/debit lines only — NEVER include QRIS or house charges)
- qris_amount (sum of all QRIS lines only — NEVER merge into edc_card_amount)
- gross_amount (Gross Sales / Gross if printed)
- net_sales (Net Sales / Net if printed)
- bills (Bill / Bills / Nota count — usually near the header totals)
- pax (Pax / Guest count)
- settlement_batch_date (YYYY-MM-DD if printed)
- payment_methods: array of {label, amount, kind} for EACH printed tender line
  kind is one of EDC, QRIS, CASH, OTHER — keep bank names in label
  (e.g. "EDC BNI", "EDC Mandiri", "QRIS BNI", "QRIS Mandiri", "ROB & FAMILY")
- edc_bni, edc_mandiri, edc_bca, edc_bri, edc_other (per-bank EDC card amounts if printed)
- qris_bni, qris_mandiri, qris_bca, qris_bri, qris_other (per-bank QRIS if printed)
- ocr_confidence (0..1)
If a line is unclear, null + lower confidence. Never invent amounts.
Never merge QRIS into EDC. House charges / room charge / family accounts are OTHER, not EDC.
"""


def normalize_edc_fields(raw: dict[str, Any]) -> dict[str, Any]:
    edc = _num_or_none(
        raw.get("edc_card_amount") if "edc_card_amount" in raw else raw.get("edc_amount")
    )
    qris = _num_or_none(raw.get("qris_amount"))
    if edc is None and qris is None and raw.get("batch_total") is not None:
        return _blank_low(
            {
                "acquirer_label": (raw.get("acquirer_label") or raw.get("bank") or "").strip()
                or None,
                "terminal_label": (raw.get("terminal_label") or "").strip() or None,
                "settlement_batch_date": (raw.get("settlement_batch_date") or "").strip()
                or None,
                "edc_card_amount": None,
                "qris_amount": None,
                "receipt_total": None,
                "batch_ref": (raw.get("batch_ref") or raw.get("ref") or "").strip() or None,
                "split_missing": True,
                "message": "batch_total without EDC/QRIS split — do not invent split",
            },
            _num_or_none(raw.get("ocr_confidence")),
        )
    total = None
    if edc is not None or qris is not None:
        total = round((edc or 0.0) + (qris or 0.0), 2)
    fields = {
        "acquirer_label": (raw.get("acquirer_label") or raw.get("bank") or "").strip()
        or None,
        "terminal_label": (raw.get("terminal_label") or "").strip() or None,
        "settlement_batch_date": (raw.get("settlement_batch_date") or "").strip() or None,
        "edc_card_amount": edc,
        "qris_amount": qris,
        "receipt_total": total,
        "batch_ref": (raw.get("batch_ref") or raw.get("ref") or "").strip() or None,
        "split_missing": False,
    }
    return _blank_low(fields, _num_or_none(raw.get("ocr_confidence")))


def _payment_methods(raw: dict[str, Any]) -> list[dict[str, Any]]:
    pm = raw.get("payment_methods")
    out: list[dict[str, Any]] = []
    if isinstance(pm, list):
        for item in pm:
            if not isinstance(item, dict):
                continue
            label = (item.get("label") or item.get("name") or "").strip()
            amt = _num_or_none(item.get("amount"))
            kind = (item.get("kind") or "").strip().upper() or None
            if label or amt is not None:
                out.append({"label": label or None, "amount": amt, "kind": kind})
    # Also fold explicit bank keys into payment_methods if not already present
    bank_keys = (
        ("edc_bni", "EDC BNI", "EDC"),
        ("edc_mandiri", "EDC Mandiri", "EDC"),
        ("edc_bca", "EDC BCA", "EDC"),
        ("edc_bri", "EDC BRI", "EDC"),
        ("qris_bni", "QRIS BNI", "QRIS"),
        ("qris_mandiri", "QRIS Mandiri", "QRIS"),
        ("qris_bca", "QRIS BCA", "QRIS"),
        ("qris_bri", "QRIS BRI", "QRIS"),
    )
    existing_labels = {(x.get("label") or "").lower() for x in out}
    for key, label, kind in bank_keys:
        amt = _num_or_none(raw.get(key))
        if amt is None:
            continue
        if label.lower() in existing_labels:
            continue
        out.append({"label": label, "amount": amt, "kind": kind})
    return out


def normalize_esb_fields(raw: dict[str, Any]) -> dict[str, Any]:
    edc = _num_or_none(
        raw.get("edc_card_amount") if "edc_card_amount" in raw else raw.get("card_amount")
    )
    qris = _num_or_none(raw.get("qris_amount"))
    methods = _payment_methods(raw)
    # If totals missing, sum from methods
    if edc is None:
        s = sum(
            (m["amount"] or 0.0)
            for m in methods
            if (m.get("kind") or "").upper() == "EDC" and m.get("amount") is not None
        )
        if s > 0:
            edc = round(s, 2)
    if qris is None:
        s = sum(
            (m["amount"] or 0.0)
            for m in methods
            if (m.get("kind") or "").upper() == "QRIS" and m.get("amount") is not None
        )
        if s > 0:
            qris = round(s, 2)
    fields = {
        "cash_amount": _num_or_none(raw.get("cash_amount")),
        "edc_card_amount": edc,
        "qris_amount": qris,
        "gross_amount": _num_or_none(raw.get("gross_amount") or raw.get("gross_sales")),
        "net_sales": _num_or_none(raw.get("net_sales") or raw.get("net_amount")),
        "bills": _int_or_none(raw.get("bills") or raw.get("bill_count")),
        "pax": _int_or_none(raw.get("pax") or raw.get("pax_count")),
        "settlement_batch_date": (raw.get("settlement_batch_date") or "").strip() or None,
        "payment_methods": methods,
        "edc_bni": _num_or_none(raw.get("edc_bni")),
        "edc_mandiri": _num_or_none(raw.get("edc_mandiri")),
        "edc_bca": _num_or_none(raw.get("edc_bca")),
        "edc_bri": _num_or_none(raw.get("edc_bri")),
        "qris_bni": _num_or_none(raw.get("qris_bni")),
        "qris_mandiri": _num_or_none(raw.get("qris_mandiri")),
        "qris_bca": _num_or_none(raw.get("qris_bca")),
        "qris_bri": _num_or_none(raw.get("qris_bri")),
    }
    return _blank_low(fields, _num_or_none(raw.get("ocr_confidence")))


def _unavailable_draft(kind: str, *, diagnostic: str | None = None) -> dict[str, Any]:
    blank = (
        normalize_edc_fields({"ocr_confidence": 0.0})
        if kind == "EDC_RECEIPT"
        else normalize_esb_fields({"ocr_confidence": 0.0})
    )
    return {
        **HONESTY,
        "ok": True,
        "extraction_unavailable": True,
        "provider": None,
        "model": None,
        "kind": kind,
        "capability": CAPABILITY,
        "extracted": blank,
        "message": STAFF_VISION_UNAVAILABLE,
        "staff_message": STAFF_VISION_UNAVAILABLE,
        # diagnostic for Owner/logs only — serve layer must not forward to staff UI
        "diagnostic_code": "vision_unavailable",
        "diagnostic": diagnostic,
    }


def extract_edc_receipt(
    *,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
    fixture_fields: dict[str, Any] | None = None,
    force_provider: str | None = None,
) -> dict[str, Any]:
    """Return vision draft for one EDC receipt. Never accounting truth."""
    if fixture_fields is not None or force_provider == "fixture":
        fields = normalize_edc_fields(fixture_fields or {})
        return {
            **HONESTY,
            "ok": True,
            "provider": "fixture",
            "model": None,
            "kind": "EDC_RECEIPT",
            "extracted": fields,
        }

    if _dry_run() or force_provider == "dry":
        return {
            **_unavailable_draft("EDC_RECEIPT", diagnostic="dry_run"),
            "provider": "dry_run",
            "message": STAFF_VISION_UNAVAILABLE,
        }

    if not image_bytes:
        raise VisionError(
            "image required for live vision",
            code="missing_image",
            staff_message="Take Photo or Upload Photo for the receipt first.",
        )

    try:
        text, provider, model = call_receipt_image_extraction(
            EDC_PROMPT, image_bytes=image_bytes, mime_type=mime_type
        )
    except VisionError as exc:
        if exc.code in ("vision_unavailable", "vision_http", "vision_transport"):
            return _unavailable_draft("EDC_RECEIPT", diagnostic=exc.diagnostic)
        raise

    fields = normalize_edc_fields(_parse_json_loose(text))
    return {
        **HONESTY,
        "ok": True,
        "extraction_unavailable": False,
        "provider": provider,
        "model": model,
        "kind": "EDC_RECEIPT",
        "capability": CAPABILITY,
        "extracted": fields,
        "raw_text": text[:4000],
    }


def extract_esb_closing_receipt(
    *,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
    fixture_fields: dict[str, Any] | None = None,
    force_provider: str | None = None,
) -> dict[str, Any]:
    if fixture_fields is not None or force_provider == "fixture":
        fields = normalize_esb_fields(fixture_fields or {})
        return {
            **HONESTY,
            "ok": True,
            "provider": "fixture",
            "model": None,
            "kind": "ESB_CLOSING_RECEIPT",
            "extracted": fields,
        }

    if _dry_run() or force_provider == "dry":
        return {
            **_unavailable_draft("ESB_CLOSING_RECEIPT", diagnostic="dry_run"),
            "provider": "dry_run",
        }

    if not image_bytes:
        raise VisionError(
            "image required for live vision",
            code="missing_image",
            staff_message="Take Photo or Upload Photo for the receipt first.",
        )

    try:
        text, provider, model = call_receipt_image_extraction(
            ESB_PROMPT, image_bytes=image_bytes, mime_type=mime_type
        )
    except VisionError as exc:
        if exc.code in ("vision_unavailable", "vision_http", "vision_transport"):
            return _unavailable_draft(
                "ESB_CLOSING_RECEIPT", diagnostic=exc.diagnostic
            )
        raise

    fields = normalize_esb_fields(_parse_json_loose(text))
    return {
        **HONESTY,
        "ok": True,
        "extraction_unavailable": False,
        "provider": provider,
        "model": model,
        "kind": "ESB_CLOSING_RECEIPT",
        "capability": CAPABILITY,
        "extracted": fields,
        "raw_text": text[:4000],
    }
