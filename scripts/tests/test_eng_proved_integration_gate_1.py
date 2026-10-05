#!/usr/bin/env python3
"""ENG-PROVED-INTEGRATION-GATE-1 — permanent fail-closed prove gate.

Mocks/fixtures alone cannot claim ENG_PROVED for external integrations.
Also covers RECEIPT_IMAGE_EXTRACTION staff-safe + soft-fail (no live spend).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def load_mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    gate = load_mod(
        SCRIPTS / "core" / "eng_proved_integration_gate.py",
        "eng_proved_integration_gate",
    )
    vision = load_mod(SCRIPTS / "core" / "bzg_close_vision.py", "bzg_close_vision")
    ui = (ROOT / "dashboards" / "uma-blu-close.html").read_text(encoding="utf-8")
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    policy = ROOT / "state" / "bzg-daily-close" / "ENG-PROVED-INTEGRATION-GATE-1.json"
    receipt = (
        ROOT
        / "state"
        / "bzg-daily-close"
        / "receipts"
        / "EVD-CLOSE-ESB-806C52F2BFBF.jpg"
    )

    check("policy file present", policy.is_file())
    check("preserve receipt on disk", receipt.is_file() and receipt.stat().st_size > 1000)

    # Fail closed: mock-only claim must raise
    raised = False
    try:
        gate.assert_integration_eng_proved(
            {
                "claim_eng_proved": True,
                "code_test": True,
                "provider": "fixture",
                "mock_only": True,
            }
        )
    except gate.IntegrationProveError:
        raised = True
    check("mock-only ENG_PROVED raises", raised)

    # Fail closed: missing live credential path
    raised2 = False
    try:
        gate.assert_integration_eng_proved(
            {
                "claim_eng_proved": True,
                "code_test": True,
                "beta_deployed": True,
                "live_credential_path_available": False,
                "real_representative_input": True,
                "expected_output_or_honest_partial": True,
                "failure_or_fallback_path": True,
                "evidence_on_disk": True,
                "real_provider_or_service_call": True,
                "real_beta_credential_resolution": True,
            }
        )
    except gate.IntegrationProveError:
        raised2 = True
    check("live_credential unavailable fails closed", raised2)

    # Honest classify without claim → not ENG_PROVED
    cls = gate.classify_integration_prove(
        {
            "code_test": True,
            "beta_deployed": True,
            "real_beta_credential_resolution": True,
            "real_provider_or_service_call": True,
            "real_representative_input": True,
            "expected_output_or_honest_partial": True,
            "failure_or_fallback_path": True,
            "evidence_on_disk": True,
            "provider": "anthropic",
            "claim_eng_proved": False,
        }
    )
    check("full chain without claim is not ENG_PROVED", cls["eng_proved"] is False)
    check("stamp is not mock-only", "UNPROVED" not in cls["stamp"] or "LIVE" in cls["stamp"])

    # Vision capability wiring
    check("capability name", vision.CAPABILITY == "RECEIPT_IMAGE_EXTRACTION")
    check("uses model_router", "vision_extract" in Path(vision.__file__).read_text(encoding="utf-8"))
    check(
        "staff-safe copy",
        "temporarily unavailable" in vision.STAFF_VISION_UNAVAILABLE.lower(),
    )
    bad = vision._staff_sanitize("Gemini API key not authorised / Anthropic missing")
    check("sanitize strips providers", "gemini" not in bad.lower() and "anthropic" not in bad.lower())

    dry = vision.extract_esb_closing_receipt(
        image_bytes=b"not-a-real-jpeg", force_provider="dry"
    )
    check("dry soft-fail unavailable", dry.get("extraction_unavailable") is True)
    check(
        "dry staff message safe",
        "gemini" not in (dry.get("staff_message") or "").lower(),
    )
    check(
        "dry keeps empty document",
        isinstance(dry.get("document") or dry.get("extracted"), dict),
    )
    check(
        "fixture is not live path",
        gate.receipt_image_extraction_live_path_ok(
            {"provider": "fixture", "extracted": {"gross_amount": 1}}
        )
        is False,
    )

    # UI / serve staff-safe
    check("Retry Reading UI", "Retry Reading" in ui)
    check("Enter Manually UI", "Enter Manually" in ui)
    check("UI staffSafeVisionMsg", "staffSafeVisionMsg" in ui)
    check("serve staff sanitize", "_staff_vision_sanitize" in serve)
    check("serve VisionError soft path", "extraction_unavailable" in serve)

    # Gap note for Wolf Intelligence surfaces
    gap = ROOT / "state" / "bzg-daily-close" / "GAP-STAFF-SAFE-PROVIDER-NAMING.md"
    check("Wolf Intelligence gap note", gap.is_file())

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
