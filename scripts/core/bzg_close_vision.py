#!/usr/bin/env python3
"""BZG Daily Close vision extract — draft only, never accounting truth.

Decision: 2026-09-17 Uma Blu Daily Close (extend) + MULTI-EDC-VISION Owner order.

Cheapest reliable Wolf path: Gemini Vision when key authorised; otherwise fixture /
deterministic blank-low-confidence draft. Low confidence → blank or flag; do not invent.
Human Looks Correct / Edit is the only accounting truth path.
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

PACK = "BZG-DAILY-CLOSE-MULTI-EDC-VISION-1"
DEFAULT_MODEL = "gemini-1.5-flash"
LOW_CONFIDENCE_FLOOR = 0.55

HONESTY = {
    "pack": PACK,
    "ai_is_not_accounting_truth": True,
    "vision_draft_requires_human_confirm": True,
    "low_confidence_does_not_invent": True,
}


class VisionError(ValueError):
    def __init__(self, message: str, *, code: str = "vision_error", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


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


def _confidence_band(conf: float | None) -> str:
    if conf is None:
        return "UNKNOWN"
    if conf < LOW_CONFIDENCE_FLOOR:
        return "LOW"
    if conf < 0.8:
        return "MEDIUM"
    return "HIGH"


def _blank_low(fields: dict[str, Any], conf: float | None) -> dict[str, Any]:
    """Low confidence: blank inventable amount fields; keep flags honest."""
    out = dict(fields)
    band = _confidence_band(conf)
    out["ocr_confidence"] = conf
    out["ocr_confidence_band"] = band
    if band == "LOW":
        for k in (
            "edc_card_amount",
            "qris_amount",
            "cash_amount",
            "gross_amount",
            "receipt_total",
            "batch_ref",
            "acquirer_label",
            "settlement_batch_date",
            "terminal_label",
        ):
            if k in out and out[k] is not None and conf is not None and conf < 0.35:
                out[k] = None if k not in ("edc_card_amount", "qris_amount", "cash_amount", "gross_amount", "receipt_total") else None
        out["low_confidence_flag"] = True
        out["invented"] = False
    else:
        out["low_confidence_flag"] = False
        out["invented"] = False
    return out


def _parse_json_loose(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return {}
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else {}
        except json.JSONDecodeError:
            return {}


def _gemini_key() -> str | None:
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        v = (os.environ.get(name) or "").strip()
        if v:
            return v
    return None


def _dry_run() -> bool:
    raw = (os.environ.get("BETA_LLM_DRY_RUN") or os.environ.get("WOLF_CLOSE_VISION_DRY") or "").strip()
    return raw.lower() in ("1", "true", "yes", "on")


def call_gemini_vision(
    prompt: str,
    *,
    image_bytes: bytes | None,
    mime_type: str = "image/jpeg",
    model: str | None = None,
    api_key: str | None = None,
) -> tuple[str, str, str]:
    """Return (text, provider, model). Raises VisionError on hard failure."""
    key = (api_key or _gemini_key() or "").strip()
    if not key:
        raise VisionError("Gemini key not authorised/available", code="vision_unavailable", http_status=503)
    mdl = (model or os.environ.get("WOLF_CLOSE_VISION_MODEL") or DEFAULT_MODEL).strip()
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{mdl}:generateContent?key={key}"
    )
    parts: list[dict[str, Any]] = [{"text": prompt}]
    if image_bytes:
        parts.append(
            {
                "inline_data": {
                    "mime_type": mime_type or "image/jpeg",
                    "data": base64.b64encode(image_bytes).decode("ascii"),
                }
            }
        )
    body = json.dumps({"contents": [{"parts": parts}]}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise VisionError(
            f"Gemini vision HTTP {exc.code}",
            code="vision_http",
            http_status=502,
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise VisionError(str(exc), code="vision_transport", http_status=502) from exc
    cands = payload.get("candidates") or []
    text = ""
    if cands:
        content = (cands[0].get("content") or {})
        parts_out = content.get("parts") or []
        text = "\n".join(
            (p.get("text") or "") for p in parts_out if isinstance(p, dict)
        ).strip()
    return text, "gemini", mdl


EDC_PROMPT = """Extract settlement receipt fields as JSON only.
Keys: acquirer_label, terminal_label, settlement_batch_date (YYYY-MM-DD),
edc_card_amount (number, card/EDC only — NEVER include QRIS),
qris_amount (number, QRIS only — NEVER merge into edc_card_amount),
batch_ref, ocr_confidence (0..1).
If unsure, use null and lower ocr_confidence. Do not invent amounts or TIDs.
EDC card and QRIS must stay separate."""


ESB_PROMPT = """Extract ESB / POS closing receipt fields as JSON only.
Keys: cash_amount, edc_card_amount (card only), qris_amount (QRIS only),
gross_amount, settlement_batch_date (YYYY-MM-DD), ocr_confidence (0..1).
If unsure, null + lower confidence. Never merge QRIS into card. Do not invent."""


def normalize_edc_fields(raw: dict[str, Any]) -> dict[str, Any]:
    edc = _num_or_none(raw.get("edc_card_amount") if "edc_card_amount" in raw else raw.get("edc_amount"))
    qris = _num_or_none(raw.get("qris_amount"))
    # Explicit refuse merge: if only batch_total supplied without split → leave both blank/flag
    if edc is None and qris is None and raw.get("batch_total") is not None:
        return _blank_low(
            {
                "acquirer_label": (raw.get("acquirer_label") or raw.get("bank") or "").strip() or None,
                "terminal_label": (raw.get("terminal_label") or "").strip() or None,
                "settlement_batch_date": (raw.get("settlement_batch_date") or "").strip() or None,
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
        "acquirer_label": (raw.get("acquirer_label") or raw.get("bank") or "").strip() or None,
        "terminal_label": (raw.get("terminal_label") or "").strip() or None,
        "settlement_batch_date": (raw.get("settlement_batch_date") or "").strip() or None,
        "edc_card_amount": edc,
        "qris_amount": qris,
        "receipt_total": total,
        "batch_ref": (raw.get("batch_ref") or raw.get("ref") or "").strip() or None,
        "split_missing": False,
    }
    return _blank_low(fields, _num_or_none(raw.get("ocr_confidence")))


def normalize_esb_fields(raw: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "cash_amount": _num_or_none(raw.get("cash_amount")),
        "edc_card_amount": _num_or_none(
            raw.get("edc_card_amount") if "edc_card_amount" in raw else raw.get("card_amount")
        ),
        "qris_amount": _num_or_none(raw.get("qris_amount")),
        "gross_amount": _num_or_none(raw.get("gross_amount")),
        "settlement_batch_date": (raw.get("settlement_batch_date") or "").strip() or None,
    }
    return _blank_low(fields, _num_or_none(raw.get("ocr_confidence")))


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
        fields = normalize_edc_fields(
            {
                "ocr_confidence": 0.0,
                "edc_card_amount": None,
                "qris_amount": None,
            }
        )
        return {
            **HONESTY,
            "ok": True,
            "provider": "dry_run",
            "model": None,
            "kind": "EDC_RECEIPT",
            "extracted": fields,
            "message": "Vision dry-run — blank draft; human must enter or provide fixture",
        }

    if not image_bytes:
        raise VisionError("image required for live vision", code="missing_image")

    text, provider, model = call_gemini_vision(
        EDC_PROMPT, image_bytes=image_bytes, mime_type=mime_type
    )
    fields = normalize_edc_fields(_parse_json_loose(text))
    return {
        **HONESTY,
        "ok": True,
        "provider": provider,
        "model": model,
        "kind": "EDC_RECEIPT",
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
        fields = normalize_esb_fields({"ocr_confidence": 0.0})
        return {
            **HONESTY,
            "ok": True,
            "provider": "dry_run",
            "model": None,
            "kind": "ESB_CLOSING_RECEIPT",
            "extracted": fields,
            "message": "Vision dry-run — blank draft; human must enter or provide fixture",
        }

    if not image_bytes:
        raise VisionError("image required for live vision", code="missing_image")

    text, provider, model = call_gemini_vision(
        ESB_PROMPT, image_bytes=image_bytes, mime_type=mime_type
    )
    fields = normalize_esb_fields(_parse_json_loose(text))
    return {
        **HONESTY,
        "ok": True,
        "provider": provider,
        "model": model,
        "kind": "ESB_CLOSING_RECEIPT",
        "extracted": fields,
        "raw_text": text[:4000],
    }
