#!/usr/bin/env python3
"""ENG-PROVED-INTEGRATION-GATE-1 — fail closed for external integrations.

An integration-backed feature cannot be stamped ENG_PROVED on mocked /
fixture / dry-run paths alone. Required chain:

  code_test → beta_deployed → real_beta_credential_resolution →
  real_provider_or_service_call → real_representative_input →
  expected_output_or_honest_partial → failure_or_fallback_path →
  evidence_on_disk

Otherwise stamp: CODE COMPLETE / INTEGRATION UNPROVED

Pack trigger: BZG-CLOSE-VISION-CAPABILITY-1 (2026-10-02) — vision was
falsely ENG_PROVED while deployed Beta had no live Gemini env key.
"""
from __future__ import annotations

from typing import Any

POLICY_ID = "ENG-PROVED-INTEGRATION-GATE-1"
OTHERWISE = "CODE COMPLETE / INTEGRATION UNPROVED"
REQUIRED_CHAIN = (
    "code_test",
    "beta_deployed",
    "real_beta_credential_resolution",
    "real_provider_or_service_call",
    "real_representative_input",
    "expected_output_or_honest_partial",
    "failure_or_fallback_path",
    "evidence_on_disk",
)

# Providers that prove only a mock/fixture path — never enough for ENG_PROVED.
MOCK_PROVIDERS = frozenset({"fixture", "dry_run", "mock", "unit", "stub", ""})


class IntegrationProveError(ValueError):
    def __init__(self, message: str, *, missing: list[str] | None = None):
        super().__init__(message)
        self.missing = missing or []


def classify_integration_prove(evidence: dict[str, Any] | None) -> dict[str, Any]:
    """Classify evidence for an integration-backed feature.

    Returns stamp + missing links. Never invents PASS.
    """
    ev = evidence if isinstance(evidence, dict) else {}
    missing: list[str] = []
    for key in REQUIRED_CHAIN:
        if not ev.get(key):
            missing.append(key)

    provider = str(ev.get("provider") or "").strip().lower()
    if provider in MOCK_PROVIDERS or ev.get("mock_only"):
        if "real_provider_or_service_call" not in missing:
            missing.append("real_provider_or_service_call")
        if "real_beta_credential_resolution" not in missing:
            missing.append("real_beta_credential_resolution")

    if ev.get("live_credential_path_available") is False:
        if "real_beta_credential_resolution" not in missing:
            missing.append("real_beta_credential_resolution")

    eng_proved = not missing and bool(ev.get("claim_eng_proved"))
    if missing:
        stamp = OTHERWISE
        eng_proved = False
    elif ev.get("claim_eng_proved"):
        stamp = "ENG_PROVED"
    else:
        stamp = "CODE COMPLETE / INTEGRATION LIVE PATH PROVED — human/ops confirm still required"

    return {
        "policy_id": POLICY_ID,
        "stamp": stamp,
        "eng_proved": eng_proved,
        "missing": missing,
        "required_chain": list(REQUIRED_CHAIN),
        "otherwise": OTHERWISE,
        "provider": provider or None,
    }


def assert_integration_eng_proved(evidence: dict[str, Any] | None) -> dict[str, Any]:
    """Fail closed when claiming ENG_PROVED without the full live chain."""
    result = classify_integration_prove(evidence)
    if evidence and evidence.get("claim_eng_proved") and not result["eng_proved"]:
        raise IntegrationProveError(
            f"{POLICY_ID}: cannot ENG_PROVED — missing {result['missing']}; "
            f"stamp={result['stamp']}",
            missing=list(result["missing"]),
        )
    return result


def receipt_image_extraction_live_path_ok(draft: dict[str, Any] | None) -> bool:
    """True when a RECEIPT_IMAGE_EXTRACTION draft used a real provider path."""
    if not isinstance(draft, dict):
        return False
    if draft.get("extraction_unavailable"):
        return False
    provider = str(draft.get("provider") or "").strip().lower()
    if provider in MOCK_PROVIDERS:
        return False
    extracted = draft.get("extracted") or draft.get("document")
    return isinstance(extracted, dict) and bool(extracted)
