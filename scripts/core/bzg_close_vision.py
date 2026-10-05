#!/usr/bin/env python3
"""BZG Daily Close vision — RECEIPT_IMAGE_EXTRACTION capability.

ESB closing receipts are captured as an extensible DOCUMENT:
  RECEIPT → SECTION → LINE ITEM (raw label/value first; normalize what we know;
  preserve everything else as NEEDS_CLASSIFICATION).

AI must not decide what accounting information is worth keeping.
Human-confirmed values remain authoritative. Vision is an accelerator.

Pack: BZG-CLOSE-ESB-RECEIPT-DOCUMENT-1 (2026-10-02 Owner order).
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

PACK = "BZG-CLOSE-ESB-RECEIPT-DOCUMENT-1"
CAPABILITY = "RECEIPT_IMAGE_EXTRACTION"
LOW_CONFIDENCE_FLOOR = 0.55

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
    "capture_entire_receipt_first": True,
    "unknown_lines_are_preserved_not_discarded": True,
}

_log = logging.getLogger("bzg_close_vision")

# Known section title patterns → normalized_type (extensible; unknowns preserved)
_SECTION_ALIASES: list[tuple[tuple[str, ...], str]] = [
    (("shift summary", "sales summary", "sales total", "closing summary"), "SHIFT_SUMMARY"),
    (("payment method summary", "payment methods", "payment method"), "PAYMENT_METHODS"),
    (("non sales", "non-sales", "nonsales", "non sales payment"), "NON_SALES"),
    (("cancelled menu", "cancel menu", "cancelled menu summary"), "CANCELLED_MENU"),
    (("void payment", "void payment detail", "void"), "VOID_PAYMENT"),
    (("promotion summary", "promotions", "promotion"), "PROMOTION"),
    (("discount", "total discount"), "DISCOUNT"),
]

# Known SHIFT_SUMMARY line labels → normalized_type
_SHIFT_LINE_ALIASES: list[tuple[tuple[str, ...], str]] = [
    (("sales total",), "SALES_TOTAL"),
    (("menu discount",), "MENU_DISCOUNT"),
    (("bill discount",), "BILL_DISCOUNT"),
    (("net sales total", "net sales"), "NET_SALES"),
    (("delivery cost total", "delivery cost"), "DELIVERY_COST"),
    (("order fee total", "order fee"), "ORDER_FEE"),
    (("service charge total", "service charge", "service"), "SERVICE_CHARGE"),
    (("tax total", "tax"), "TAX"),
    (("tip total", "tip"), "TIP"),
    (("platform fee total", "platform fee"), "PLATFORM_FEE"),
    (("voucher sales total", "voucher sales"), "VOUCHER_SALES"),
    (("rounding total", "rounding"), "ROUNDING"),
    (("gross sales total", "gross sales", "gross"), "GROSS_SALES"),
    (("number of pax", "pax", "no. of pax", "nopax"), "PAX"),
    (("avg. net sales per pax", "avg net sales per pax"), "AVG_NET_PER_PAX"),
    (("avg. sales per pax", "avg sales per pax"), "AVG_SALES_PER_PAX"),
    (("number of bills", "bills", "no. of bills", "nobills"), "BILLS"),
    (("avg. net sales per bill", "avg net sales per bill"), "AVG_NET_PER_BILL"),
    (("avg. sales per bill", "avg sales per bill"), "AVG_SALES_PER_BILL"),
    (("cancel total",), "CANCEL_TOTAL"),
    (("void total",), "VOID_TOTAL"),
]

# Payment method heuristics (never collapse banks; never invent meaning for house accounts)
_PAYMENT_KIND_RULES: list[tuple[str, str | None, str]] = [
    # (startswith/contains pattern handled in code)
]


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
    if isinstance(v, str):
        s = v.strip().replace(",", "").replace("Rp", "").replace("rp", "").replace(" ", "")
        if not s or s in (".", "-"):
            return None
        v = s
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if n < 0:
        return None
    return round(n, 2)


def _int_or_none(v: Any) -> int | None:
    n = _num_or_none(v)
    if n is None:
        return None
    return int(round(n))


def _confidence_band(conf: float | None) -> str:
    if conf is None:
        return "UNKNOWN"
    if conf < LOW_CONFIDENCE_FLOOR:
        return "LOW"
    if conf < 0.8:
        return "MEDIUM"
    return "HIGH"


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
    if len(msg) > 180:
        return STAFF_VISION_UNAVAILABLE
    return msg


def _import_model_router():
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
    images = [b64]
    try:
        result = mr.route(
            "vision_extract",
            prompt,
            budget="low",
            max_tokens=4000,
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


def call_gemini_vision(
    prompt: str,
    *,
    image_bytes: bytes | None,
    mime_type: str = "image/jpeg",
    model: str | None = None,
    api_key: str | None = None,
) -> tuple[str, str, str]:
    del model, api_key
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


# ── EDC (settlement slip) — unchanged shape ─────────────────────────────────

EDC_PROMPT = """Extract settlement receipt fields as JSON only.
Keys: acquirer_label, terminal_label, settlement_batch_date (YYYY-MM-DD),
edc_card_amount (number, card/EDC only — NEVER include QRIS),
qris_amount (number, QRIS only — NEVER merge into edc_card_amount),
batch_ref, ocr_confidence (0..1).
If unsure, use null and lower ocr_confidence. Do not invent amounts or TIDs.
EDC card and QRIS must stay separate."""


def _edc_prompt_with_bank_context(
    *,
    bank_hint: str | None = None,
    esb_edc_expected: float | None = None,
    esb_qris_expected: float | None = None,
) -> str:
    """Build EDC vision prompt with optional bank/ESB hints (hints only — read the slip)."""
    parts = [EDC_PROMPT]
    hint = (bank_hint or "").strip()
    if hint:
        parts.append(f"Context: acquirer/bank hint is {hint}.")
    if esb_edc_expected is not None:
        parts.append(
            f"Context: shift report expects EDC card about {esb_edc_expected} "
            "(hint only — extract what the terminal slip shows)."
        )
    if esb_qris_expected is not None:
        parts.append(
            f"Context: shift report expects QRIS about {esb_qris_expected} "
            "(hint only — extract what the terminal slip shows)."
        )
    parts.append("Return edc_card_amount and qris_amount as separate numbers. Never merge them.")
    return "\n".join(parts)


def _blank_low_edc(fields: dict[str, Any], conf: float | None) -> dict[str, Any]:
    out = dict(fields)
    band = _confidence_band(conf)
    out["ocr_confidence"] = conf
    out["ocr_confidence_band"] = band
    if band == "LOW" and conf is not None and conf < 0.35:
        for k in (
            "edc_card_amount",
            "qris_amount",
            "receipt_total",
            "batch_ref",
            "acquirer_label",
            "settlement_batch_date",
            "terminal_label",
        ):
            if k in out:
                out[k] = None
        out["low_confidence_flag"] = True
    return out


def normalize_edc_fields(raw: dict[str, Any]) -> dict[str, Any]:
    edc = _num_or_none(
        raw.get("edc_card_amount") if "edc_card_amount" in raw else raw.get("edc_amount")
    )
    qris = _num_or_none(raw.get("qris_amount"))
    if edc is None and qris is None and raw.get("batch_total") is not None:
        return _blank_low_edc(
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
    return _blank_low_edc(fields, _num_or_none(raw.get("ocr_confidence")))


# ── ESB CLOSING RECEIPT — DOCUMENT MODEL ────────────────────────────────────

ESB_DOCUMENT_PROMPT = """You are reading a complete ESB / POS day-end CLOSING RECEIPT photograph
(Indonesian restaurant — Uma Blu style).

TASK: Capture the ENTIRE document as structured JSON. Do NOT omit unfamiliar lines.
Do NOT collapse payment methods into Cash/EDC/QRIS totals only.
Do NOT invent amounts. Preserve every printed section and line.

Return JSON ONLY with this shape:
{
  "business_date": "YYYY-MM-DD or null",
  "ocr_confidence": 0..1,
  "sections": [
    {
      "raw_title": "exact section header as printed (or best guess)",
      "lines": [
        {
          "raw_label": "exact line label as printed",
          "quantity": number or null,
          "amount": number or null,
          "raw_value": "optional raw text if not a plain amount",
          "confidence": 0..1
        }
      ]
    }
  ]
}

Rules:
- Include Shift/Sales Summary lines (Sales Total, discounts, Net, fees, Service, Tax,
  Tip Total, Gross, Pax, Bills, averages, Cancel/Void totals, etc.) even when amount is 0.
- Always keep the Tip Total label as "Tip Total" (never collapse it to a bare "Total").
- Include EVERY payment method line separately with quantity AND amount on the SAME line
  object (CASH, EDC BNI, EDC MANDIRI, QRIS BNI, QRIS MANDIRI, house/room/family accounts, …).
  Never split Qty and Total into two separate line objects for the same method.
- Include Non Sales section lines (COMPLIMENT, Executive Chef, …) separately —
  do NOT add them into payment-method totals.
- Include Cancelled Menu, Void Payment, Promotion / Discount sections even if Total is 0.
- If you see a section or line you do not recognise, STILL include it with its raw_title/raw_label.
- Amounts are Indonesian Rupiah integers (no thousand separators in JSON numbers).
- Never put EDC Mandiri amount into QRIS. Never merge banks.
"""


def _norm_key(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("&", "and")
    return s


def _match_alias(label: str, aliases: list[tuple[tuple[str, ...], str]]) -> str | None:
    key = _norm_key(label)
    for needles, ntype in aliases:
        for n in needles:
            if key == n or key.startswith(n + " ") or n in key:
                # prefer exact / startswith
                if key == n or key.startswith(n):
                    return ntype
    # second pass: contains
    for needles, ntype in aliases:
        for n in needles:
            if n in key:
                return ntype
    return None


def _classify_section_title(raw_title: str) -> tuple[str, str]:
    ntype = _match_alias(raw_title, _SECTION_ALIASES)
    if ntype:
        return ntype, "KNOWN"
    return "UNKNOWN", "NEEDS_CLASSIFICATION"


def _classify_payment_label(raw_label: str) -> dict[str, Any]:
    key = _norm_key(raw_label)
    bank = None
    for b in ("bni", "mandiri", "bca", "bri", "cimb", "permata", "danamon", "ocbc"):
        if re.search(rf"\b{b}\b", key) or f" {b}" in f" {key}" or key.endswith(b):
            bank = b.upper()
            break
    if key == "cash" or key.startswith("cash"):
        return {
            "normalized_type": "CASH",
            "subtype": None,
            "bank_acquirer": None,
            "classification": "KNOWN",
        }
    if "qris" in key:
        return {
            "normalized_type": "QRIS",
            "subtype": bank,
            "bank_acquirer": bank,
            "classification": "KNOWN",
        }
    if key.startswith("edc") or " edc" in key or key.startswith("card"):
        return {
            "normalized_type": "EDC",
            "subtype": bank,
            "bank_acquirer": bank,
            "classification": "KNOWN",
        }
    # House / room / named accounts — preserve raw; do NOT invent accounting meaning
    if any(
        x in key
        for x in (
            "room charge",
            "room",
            "family",
            "compliment",
            "executive",
            "house",
            "scott",
            "etik",
            "rob",
            "rdb",
            "outstanding",
            "city ledger",
        )
    ):
        return {
            "normalized_type": "ACCOUNT_OR_HOUSE",
            "subtype": None,
            "bank_acquirer": None,
            "classification": "NEEDS_CLASSIFICATION",
        }
    if key in ("total", "payment method total", "payment methods total") or ("total" in key and "payment" in key):
        return {
            "normalized_type": "PAYMENT_METHOD_TOTAL",
            "subtype": None,
            "bank_acquirer": None,
            "classification": "KNOWN",
        }
    return {
        "normalized_type": "UNKNOWN",
        "subtype": None,
        "bank_acquirer": None,
        "classification": "NEEDS_CLASSIFICATION",
    }


def _classify_shift_line(raw_label: str) -> tuple[str, str]:
    ntype = _match_alias(raw_label, _SHIFT_LINE_ALIASES)
    if ntype:
        return ntype, "KNOWN"
    return "UNKNOWN", "NEEDS_CLASSIFICATION"


def _classify_nonsales_line(raw_label: str) -> tuple[str, str]:
    key = _norm_key(raw_label)
    if "compliment" in key:
        return "COMPLIMENT", "KNOWN"
    if "executive" in key or "chef" in key:
        return "EXECUTIVE_CHEF", "KNOWN"
    if "total non" in key or key in ("total non sales", "total nonsales"):
        return "NON_SALES_TOTAL", "KNOWN"
    return "UNKNOWN", "NEEDS_CLASSIFICATION"


def _new_line_id() -> str:
    return f"LN-{uuid.uuid4().hex[:12]}"


def _new_section_id() -> str:
    return f"SEC-{uuid.uuid4().hex[:10]}"


def _build_line(
    *,
    raw_label: str,
    quantity: Any,
    amount: Any,
    raw_value: Any,
    confidence: Any,
    section_type: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    amt = _num_or_none(amount)
    qty = _int_or_none(quantity)
    conf = _num_or_none(confidence)
    raw_label = (raw_label or "").strip() or "(unlabeled)"
    if section_type == "PAYMENT_METHODS":
        cls = _classify_payment_label(raw_label)
        ntype = cls["normalized_type"]
        subtype = cls.get("subtype")
        bank = cls.get("bank_acquirer")
        classification = cls["classification"]
    elif section_type == "SHIFT_SUMMARY":
        ntype, classification = _classify_shift_line(raw_label)
        subtype = None
        bank = None
    elif section_type == "NON_SALES":
        ntype, classification = _classify_nonsales_line(raw_label)
        subtype = None
        bank = None
    elif section_type in ("CANCELLED_MENU", "VOID_PAYMENT", "PROMOTION", "DISCOUNT"):
        key = _norm_key(raw_label)
        if "total" in key:
            ntype, classification = f"{section_type}_TOTAL", "KNOWN"
        else:
            ntype, classification = "UNKNOWN", "NEEDS_CLASSIFICATION"
        subtype = None
        bank = None
    else:
        ntype, classification = "UNKNOWN", "NEEDS_CLASSIFICATION"
        subtype = None
        bank = None
    uncertain = classification == "NEEDS_CLASSIFICATION" or (
        conf is not None and conf < LOW_CONFIDENCE_FLOOR
    )
    return {
        "line_id": _new_line_id(),
        "raw_label": raw_label,
        "raw_value": None if raw_value is None else str(raw_value),
        "quantity": qty,
        "amount": amt,
        "normalized_type": ntype,
        "subtype": subtype,
        "bank_acquirer": bank,
        "confidence": conf,
        "extracted_value": amt if amt is not None else qty,
        "human_confirmed_value": None,
        "classification": classification,
        "uncertain": uncertain,
        "provenance": provenance,
    }



def _base_pay_label(raw_label: str) -> str:
    lab = (raw_label or "").strip()
    lab = re.sub(r"\s*-\s*(qty|quantity|total)\s*$", "", lab, flags=re.I).strip()
    lab = re.sub(r"\s+(qty|quantity|total)\s*$", "", lab, flags=re.I).strip()
    return lab


def _coalesce_payment_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge adjacent Qty-only / Amount-only rows that share a payment method label."""
    if not lines:
        return lines
    out: list[dict[str, Any]] = []
    i = 0
    while i < len(lines):
        cur = dict(lines[i])
        label = _base_pay_label(str(cur.get("raw_label") or ""))
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        merged = False
        if nxt is not None:
            nlabel = _base_pay_label(str(nxt.get("raw_label") or ""))
            same_label = label.lower() == nlabel.lower()
            same_type = (
                cur.get("normalized_type")
                and cur.get("normalized_type") == nxt.get("normalized_type")
                and (cur.get("bank_acquirer") or "") == (nxt.get("bank_acquirer") or "")
                and cur.get("normalized_type")
                not in (None, "UNKNOWN", "PAYMENT_METHOD_TOTAL")
            )
            cur_has_q = cur.get("quantity") is not None and cur.get("amount") is None
            cur_has_a = cur.get("amount") is not None and cur.get("quantity") is None
            nxt_has_q = nxt.get("quantity") is not None and nxt.get("amount") is None
            nxt_has_a = nxt.get("amount") is not None and nxt.get("quantity") is None
            if (same_label or same_type) and ((cur_has_q and nxt_has_a) or (cur_has_a and nxt_has_q)):
                merged_ln = dict(cur)
                if cur_has_q:
                    merged_ln["quantity"] = cur.get("quantity")
                    merged_ln["amount"] = nxt.get("amount")
                else:
                    merged_ln["amount"] = cur.get("amount")
                    merged_ln["quantity"] = nxt.get("quantity")
                merged_ln["raw_label"] = label or cur.get("raw_label")
                merged_ln["extracted_value"] = (
                    merged_ln["amount"] if merged_ln.get("amount") is not None else merged_ln.get("quantity")
                )
                if nxt.get("confidence") is not None and cur.get("confidence") is not None:
                    try:
                        merged_ln["confidence"] = min(float(cur["confidence"]), float(nxt["confidence"]))
                    except (TypeError, ValueError):
                        pass
                if merged_ln.get("classification") == "NEEDS_CLASSIFICATION" and nxt.get("classification") == "KNOWN":
                    merged_ln["normalized_type"] = nxt.get("normalized_type")
                    merged_ln["bank_acquirer"] = nxt.get("bank_acquirer")
                    merged_ln["classification"] = "KNOWN"
                    merged_ln["uncertain"] = False
                # Prefer KNOWN from cur over UNKNOWN nxt
                if cur.get("classification") == "KNOWN" and nxt.get("classification") != "KNOWN":
                    pass
                out.append(merged_ln)
                i += 2
                merged = True
        if not merged:
            if re.search(r"\s*-\s*(qty|quantity|total)\s*$", str(cur.get("raw_label") or ""), re.I):
                cur["raw_label"] = label
            out.append(cur)
            i += 1
    return out



def _ensure_shift_tip_present(lines: list[dict[str, Any]], provenance: dict[str, Any]) -> list[dict[str, Any]]:
    """Tip Total must appear even when vision omits a zero tip line."""
    if any(ln.get("normalized_type") == "TIP" for ln in lines):
        return lines
    tip = _build_line(
        raw_label="Tip Total",
        quantity=None,
        amount=0,
        raw_value=None,
        confidence=0.4,
        section_type="SHIFT_SUMMARY",
        provenance={**provenance, "note": "tip_line_ensured_absent_from_vision"},
    )
    tip["classification"] = "NEEDS_CLASSIFICATION"
    tip["uncertain"] = True
    # Insert after TAX when possible
    out: list[dict[str, Any]] = []
    inserted = False
    for ln in lines:
        out.append(ln)
        if not inserted and ln.get("normalized_type") == "TAX":
            out.append(tip)
            inserted = True
    if not inserted:
        out.append(tip)
    return out


def _repair_shift_tip(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """If Tip Total was OCR'd as bare Total between Tax and Platform Fee, recover it."""
    if any(ln.get("normalized_type") == "TIP" for ln in lines):
        return lines
    out: list[dict[str, Any]] = []
    for i, ln in enumerate(lines):
        lab = str(ln.get("raw_label") or "").strip().lower()
        prev_t = lines[i - 1].get("normalized_type") if i else None
        next_t = lines[i + 1].get("normalized_type") if i + 1 < len(lines) else None
        if (
            ln.get("normalized_type") in ("UNKNOWN", None)
            and lab in ("total", "tip", "tip total")
            and prev_t == "TAX"
            and next_t == "PLATFORM_FEE"
        ):
            fixed = dict(ln)
            fixed["raw_label"] = ln.get("raw_label") if lab.startswith("tip") else "Tip Total"
            fixed["normalized_type"] = "TIP"
            fixed["classification"] = "KNOWN" if lab.startswith("tip") else "NEEDS_CLASSIFICATION"
            try:
                fixed["confidence"] = min(float(fixed.get("confidence") or 0.7), 0.55)
            except (TypeError, ValueError):
                fixed["confidence"] = 0.55
            fixed["uncertain"] = True
            out.append(fixed)
        else:
            out.append(ln)
    return out


def _unclassified_lines_from_sections(
    sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Lines that still need human classification — preserved, not folded into totals."""
    out: list[dict[str, Any]] = []
    for sec in sections:
        st = sec.get("normalized_type")
        raw_title = sec.get("raw_title")
        for ln in sec.get("lines") or []:
            if ln.get("classification") != "NEEDS_CLASSIFICATION":
                continue
            out.append(
                {
                    "line_id": ln.get("line_id"),
                    "raw_label": ln.get("raw_label"),
                    "raw_value": ln.get("raw_value"),
                    "quantity": ln.get("quantity"),
                    "amount": ln.get("amount"),
                    "normalized_type": ln.get("normalized_type"),
                    "classification": ln.get("classification"),
                    "section_type": st,
                    "section_title": raw_title,
                }
            )
    return out


def _derive_views(sections: list[dict[str, Any]]) -> dict[str, Any]:
    """Convenience derived totals — never a substitute for line storage."""
    shift: dict[str, Any] = {}
    payments: list[dict[str, Any]] = []
    nonsales: list[dict[str, Any]] = []
    other_sections: list[dict[str, Any]] = []
    for sec in sections:
        st = sec.get("normalized_type")
        if st == "SHIFT_SUMMARY":
            for ln in sec.get("lines") or []:
                nt = ln.get("normalized_type")
                if nt and nt != "UNKNOWN":
                    shift[nt] = ln.get("human_confirmed_value")
                    if shift[nt] is None:
                        shift[nt] = ln.get("extracted_value")
        elif st == "PAYMENT_METHODS":
            for ln in sec.get("lines") or []:
                if ln.get("normalized_type") == "PAYMENT_METHOD_TOTAL":
                    continue
                payments.append(ln)
        elif st == "NON_SALES":
            nonsales.extend(sec.get("lines") or [])
        else:
            other_sections.append(sec)

    total_edc = round(
        sum(
            (ln.get("human_confirmed_value")
             if ln.get("human_confirmed_value") is not None
             else ln.get("amount")
             or 0.0)
            for ln in payments
            if ln.get("normalized_type") == "EDC"
        ),
        2,
    )
    total_qris = round(
        sum(
            (ln.get("human_confirmed_value")
             if ln.get("human_confirmed_value") is not None
             else ln.get("amount")
             or 0.0)
            for ln in payments
            if ln.get("normalized_type") == "QRIS"
        ),
        2,
    )
    total_cash = None
    for ln in payments:
        if ln.get("normalized_type") != "CASH":
            continue
        cand = (
            ln.get("human_confirmed_value")
            if ln.get("human_confirmed_value") is not None
            else ln.get("amount")
        )
        if cand is None:
            continue
        total_cash = cand
        break
    def _pay_amount(ln: dict[str, Any]) -> float:
        if ln.get("human_confirmed_value") is not None:
            return float(ln.get("human_confirmed_value") or 0.0)
        return float(ln.get("amount") or 0.0)

    payment_sum = round(
        sum(
            _pay_amount(ln)
            for ln in payments
            if ln.get("normalized_type") not in (None, "PAYMENT_METHOD_TOTAL", "UNKNOWN")
            and ln.get("amount") is not None
        ),
        2,
    )
    # Flat compat fields for older columns / mismatch helpers
    return {
        "shift": shift,
        "payment_lines": [
            {
                "raw_label": ln.get("raw_label"),
                "quantity": ln.get("quantity"),
                "amount": ln.get("amount"),
                "normalized_type": ln.get("normalized_type"),
                "bank_acquirer": ln.get("bank_acquirer"),
                "classification": ln.get("classification"),
                "line_id": ln.get("line_id"),
            }
            for ln in payments
        ],
        "nonsales_lines": [
            {
                "raw_label": ln.get("raw_label"),
                "amount": ln.get("amount"),
                "normalized_type": ln.get("normalized_type"),
                "classification": ln.get("classification"),
                "line_id": ln.get("line_id"),
            }
            for ln in nonsales
        ],
        "other_section_count": len(other_sections),
        "total_edc": total_edc,
        "total_qris": total_qris,
        "total_cash": total_cash,
        "payment_methods_sum": payment_sum,
        # legacy flat keys (derived; not the source of truth)
        "cash_amount": total_cash,
        "edc_card_amount": total_edc if total_edc else None,
        "qris_amount": total_qris if total_qris else None,
        "gross_amount": shift.get("GROSS_SALES"),
        "net_sales": shift.get("NET_SALES") or shift.get("SALES_TOTAL"),
        "bills": shift.get("BILLS"),
        "pax": shift.get("PAX"),
        "service_charge": shift.get("SERVICE_CHARGE"),
        "tax": shift.get("TAX"),
        "unclassified_lines": _unclassified_lines_from_sections(sections),
    }


def parse_shift_receipt(fixture: dict[str, Any] | str) -> dict[str, Any]:
    """Parse shift-receipt fixture text or vision JSON into extensible document.

    Unknown labels stay readable with raw label/value and NEEDS_CLASSIFICATION.
    They are not dropped or rewritten into known totals.
    """
    raw = _parse_json_loose(fixture) if isinstance(fixture, str) else dict(fixture or {})
    return normalize_esb_document(raw)


def normalize_esb_document(raw: dict[str, Any]) -> dict[str, Any]:
    """Turn vision JSON into extensible RECEIPT→SECTION→LINE document."""
    provenance_base = {"source": "vision", "capability": CAPABILITY, "pack": PACK}
    sections_in = raw.get("sections")
    sections: list[dict[str, Any]] = []

    # Accept legacy flat payload and wrap into document (migration path)
    if not isinstance(sections_in, list) or not sections_in:
        # Build minimal sections from flat keys if present
        shift_lines = []
        for label, key in (
            ("Sales Total", "sales_total"),
            ("Net Sales Total", "net_sales"),
            ("Gross Sales Total", "gross_amount"),
            ("Number of Pax", "pax"),
            ("Number of Bills", "bills"),
            ("Cash", "cash_amount"),
        ):
            if key in raw and raw.get(key) is not None:
                shift_lines.append(
                    {
                        "raw_label": label,
                        "amount": raw.get(key),
                        "quantity": None,
                        "confidence": raw.get("ocr_confidence"),
                    }
                )
        pm_lines = []
        for item in raw.get("payment_methods") or []:
            if isinstance(item, dict):
                pm_lines.append(item)
        # bank keys
        for key, label in (
            ("edc_bni", "EDC BNI"),
            ("edc_mandiri", "EDC MANDIRI"),
            ("qris_bni", "QRIS BNI"),
            ("qris_mandiri", "QRIS MANDIRI"),
            ("cash_amount", "CASH"),
        ):
            if raw.get(key) is not None and key != "cash_amount":
                pm_lines.append({"raw_label": label, "amount": raw.get(key)})
            elif key == "cash_amount" and raw.get(key) is not None:
                pm_lines.append({"raw_label": "CASH", "amount": raw.get(key)})
        sections_in = []
        if shift_lines:
            sections_in.append({"raw_title": "Shift Summary", "lines": shift_lines})
        if pm_lines:
            sections_in.append({"raw_title": "Payment Method Summary", "lines": pm_lines})

    for sec in sections_in or []:
        if not isinstance(sec, dict):
            # Unknown shape — preserve as raw blob section
            sections.append(
                {
                    "section_id": _new_section_id(),
                    "raw_title": "(unstructured section)",
                    "normalized_type": "UNKNOWN",
                    "classification": "NEEDS_CLASSIFICATION",
                    "lines": [
                        {
                            "line_id": _new_line_id(),
                            "raw_label": "raw_section_blob",
                            "raw_value": json.dumps(sec, default=str)[:2000],
                            "quantity": None,
                            "amount": None,
                            "normalized_type": "UNKNOWN",
                            "subtype": None,
                            "bank_acquirer": None,
                            "confidence": None,
                            "extracted_value": None,
                            "human_confirmed_value": None,
                            "classification": "NEEDS_CLASSIFICATION",
                            "uncertain": True,
                            "provenance": {**provenance_base, "note": "non-dict section preserved"},
                        }
                    ],
                }
            )
            continue
        raw_title = (sec.get("raw_title") or sec.get("title") or sec.get("name") or "").strip()
        if not raw_title:
            raw_title = "(untitled section)"
        stype, sclass = _classify_section_title(raw_title)
        lines_out: list[dict[str, Any]] = []
        for ln in sec.get("lines") or []:
            if not isinstance(ln, dict):
                lines_out.append(
                    _build_line(
                        raw_label=str(ln),
                        quantity=None,
                        amount=None,
                        raw_value=str(ln),
                        confidence=None,
                        section_type=stype,
                        provenance={**provenance_base, "note": "non-dict line preserved"},
                    )
                )
                continue
            lines_out.append(
                _build_line(
                    raw_label=str(ln.get("raw_label") or ln.get("label") or ln.get("name") or ""),
                    quantity=ln.get("quantity") if "quantity" in ln else ln.get("qty"),
                    amount=ln.get("amount") if "amount" in ln else ln.get("total") or ln.get("value"),
                    raw_value=ln.get("raw_value"),
                    confidence=ln.get("confidence") or ln.get("ocr_confidence") or raw.get("ocr_confidence"),
                    section_type=stype,
                    provenance=provenance_base,
                )
            )
        # Preserve empty sections (zero totals matter for other days)
        sections.append(
            {
                "section_id": _new_section_id(),
                "raw_title": raw_title,
                "normalized_type": stype,
                "classification": sclass,
                "lines": lines_out,
            }
        )

    conf = _num_or_none(raw.get("ocr_confidence"))
    for sec in sections:
        ntype = sec.get("normalized_type")
        if ntype == "PAYMENT_METHODS":
            sec["lines"] = _coalesce_payment_lines(list(sec.get("lines") or []))
        elif ntype == "SHIFT_SUMMARY":
            sec["lines"] = _repair_shift_tip(list(sec.get("lines") or []))
            sec["lines"] = _ensure_shift_tip_present(list(sec.get("lines") or []), provenance_base)
    derived = _derive_views(sections)
    doc = {
        "document_kind": "ESB_CLOSING_RECEIPT",
        "schema_version": 1,
        "business_date": (raw.get("business_date") or "").strip() or None,
        "sections": sections,
        "derived": derived,
        "ocr_confidence": conf,
        "ocr_confidence_band": _confidence_band(conf),
        # legacy flat mirrors for older API consumers (derived only)
        "cash_amount": derived.get("cash_amount"),
        "edc_card_amount": derived.get("edc_card_amount"),
        "qris_amount": derived.get("qris_amount"),
        "gross_amount": derived.get("gross_amount"),
        "net_sales": derived.get("net_sales"),
        "bills": derived.get("bills"),
        "pax": derived.get("pax"),
        "payment_methods": derived.get("payment_lines"),
        "extensible": True,
        "unknown_preserved": True,
    }
    return doc


# Back-compat name used by older callers
def normalize_esb_fields(raw: dict[str, Any]) -> dict[str, Any]:
    return normalize_esb_document(raw)


def empty_esb_document() -> dict[str, Any]:
    return normalize_esb_document(
        {
            "ocr_confidence": 0.0,
            "sections": [
                {"raw_title": "Shift Summary", "lines": []},
                {"raw_title": "Payment Method Summary", "lines": []},
                {"raw_title": "Non Sales Payment Method Summary", "lines": []},
                {"raw_title": "Cancelled Menu Summary", "lines": []},
                {"raw_title": "Void Payment Detail", "lines": []},
                {"raw_title": "Promotion Summary", "lines": []},
            ],
        }
    )


def _unavailable_draft(kind: str, *, diagnostic: str | None = None) -> dict[str, Any]:
    if kind == "EDC_RECEIPT":
        blank = normalize_edc_fields({"ocr_confidence": 0.0})
    else:
        blank = empty_esb_document()
    return {
        **HONESTY,
        "ok": True,
        "extraction_unavailable": True,
        "provider": None,
        "model": None,
        "kind": kind,
        "capability": CAPABILITY,
        "extracted": blank,
        "document": blank if kind != "EDC_RECEIPT" else None,
        "message": STAFF_VISION_UNAVAILABLE,
        "staff_message": STAFF_VISION_UNAVAILABLE,
        "diagnostic_code": "vision_unavailable",
        "diagnostic": diagnostic,
    }


def extract_edc_receipt(
    *,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
    fixture_fields: dict[str, Any] | None = None,
    force_provider: str | None = None,
    bank_hint: str | None = None,
    esb_edc_expected: float | None = None,
    esb_qris_expected: float | None = None,
) -> dict[str, Any]:
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
        }
    if not image_bytes:
        raise VisionError(
            "image required for live vision",
            code="missing_image",
            staff_message="Take Photo or Upload Photo for the receipt first.",
        )
    try:
        text, provider, model = call_receipt_image_extraction(
            _edc_prompt_with_bank_context(
                bank_hint=bank_hint,
                esb_edc_expected=esb_edc_expected,
                esb_qris_expected=esb_qris_expected,
            ),
            image_bytes=image_bytes,
            mime_type=mime_type
        )
    except VisionError as exc:
        if exc.code in ("vision_unavailable", "vision_http", "vision_transport"):
            return _unavailable_draft("EDC_RECEIPT", diagnostic=exc.diagnostic)
        raise
    except Exception as exc:  # noqa: BLE001 — never surface raw provider errors to staff
        return _unavailable_draft("EDC_RECEIPT", diagnostic=str(exc)[:240])
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
        doc = normalize_esb_document(fixture_fields or {})
        return {
            **HONESTY,
            "ok": True,
            "provider": "fixture",
            "model": None,
            "kind": "ESB_CLOSING_RECEIPT",
            "extracted": doc,
            "document": doc,
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
            ESB_DOCUMENT_PROMPT, image_bytes=image_bytes, mime_type=mime_type
        )
    except VisionError as exc:
        if exc.code in ("vision_unavailable", "vision_http", "vision_transport"):
            return _unavailable_draft(
                "ESB_CLOSING_RECEIPT", diagnostic=exc.diagnostic
            )
        raise
    doc = normalize_esb_document(_parse_json_loose(text))
    return {
        **HONESTY,
        "ok": True,
        "extraction_unavailable": False,
        "provider": provider,
        "model": model,
        "kind": "ESB_CLOSING_RECEIPT",
        "capability": CAPABILITY,
        "extracted": doc,
        "document": doc,
        "raw_text": text[:8000],
    }
