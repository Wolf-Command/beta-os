#!/usr/bin/env python3
"""Tests for Wolf Core Authorised Knowledge Resolver v1 (Beta).

Fixture-only — no network. No memory_items writes. No Production.
CAP-INTEL-02 + CAP-INTEL-03.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import authorised_knowledge as akr  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures" / "authorised_knowledge"
REGISTRY = FIX / "registry.json"
EMPTY_CANON = json.loads((FIX / "habitat" / "empty_canon.json").read_text(encoding="utf-8"))

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


def _resolve(question_key: str, **kwargs):
    kw = {
        "scope": "brand:habitat",
        "question_key": question_key,
        "sources_registry": REGISTRY,
        "fixture_root": FIX,
        "canonical": kwargs.pop("canonical", EMPTY_CANON),
    }
    kw.update(kwargs)
    return akr.resolve(**kw)


def test_honesty_and_caps() -> None:
    h = akr.honesty_flags()
    check("honesty.llm_invent_false", h.get("llm_invent") is False)
    check("honesty.no_auto_promote", h.get("memory_items_auto_promote") is False)
    check("honesty.no_crawl", h.get("crawl") is False)
    check("cap.max_sources_8", akr.MAX_SOURCES_PER_RESOLVE == 8)
    check("cap.max_bytes_256kib", akr.MAX_BYTES_PER_SOURCE == 256 * 1024)
    check(
        "status.vocab",
        akr.STATUSES
        == {
            "NOT CANONICAL",
            "NOT FOUND",
            "INACCESSIBLE",
            "CONFLICTED",
            "UNKNOWN",
        },
    )


def test_empty_field_not_unknown() -> None:
    r = _resolve("brand_font", canonical=EMPTY_CANON)
    check(
        "empty≠UNKNOWN.status",
        r["status"] == akr.STATUS_NOT_CANONICAL,
        detail=str(r.get("status")),
    )
    check(
        "empty≠UNKNOWN.answer_manrope",
        (r.get("answer") or {}).get("value") == "Manrope"
        or (r.get("answer") or {}).get("brand_font") == "Manrope",
        detail=str(r.get("answer")),
    )
    check("empty≠UNKNOWN.has_provenance", len(r.get("provenance") or []) >= 1)
    log = " ".join(a.get("detail", "") for a in r.get("attempt_log") or [])
    check("empty≠UNKNOWN.attempt_mentions_empty", "EMPTY FIELD" in log or "empty" in log.lower())


def test_canonical_present_short_circuit() -> None:
    r = _resolve(
        "brand_font",
        canonical={"fields": {"brand_font": "CanonFont"}},
    )
    check("canonical.status_none", r["status"] is None, detail=str(r.get("status")))
    check("canonical.value", (r.get("answer") or {}).get("value") == "CanonFont")
    check("canonical.flag", (r.get("answer") or {}).get("canonical") is True)
    check("canonical.resolved", r.get("resolved") is True)


def test_manrope_vs_inter_scoped() -> None:
    r = _resolve("font")
    check(
        "habitat.font.status_not_canonical",
        r["status"] == akr.STATUS_NOT_CANONICAL,
        detail=str(r.get("status")),
    )
    ans = r.get("answer") or {}
    check("habitat.font.scoped", ans.get("resolution") == "scoped", detail=str(ans))
    check("habitat.font.brand_manrope", ans.get("brand_font") == "Manrope", detail=str(ans))
    check("habitat.font.ui_inter", ans.get("ui_font") == "Inter", detail=str(ans))
    check("habitat.font.not_conflicted", r["status"] != akr.STATUS_CONFLICTED)
    check("habitat.font.confidence_high", r.get("confidence") == "high")


def test_conflicted_same_lane() -> None:
    r = _resolve("headline_case")
    check(
        "conflict.status",
        r["status"] == akr.STATUS_CONFLICTED,
        detail=str(r.get("status")),
    )
    check("conflict.no_safe_answer", r.get("answer") is None)
    check("conflict.sides", len(r.get("conflicts") or []) >= 1, detail=str(r.get("conflicts")))
    sides = []
    for c in r.get("conflicts") or []:
        for v in c.get("values") or []:
            sides.append(v.get("value"))
    check(
        "conflict.has_both_cases",
        "UPPERCASE" in sides and "lowercase" in sides,
        detail=str(sides),
    )


def test_not_found() -> None:
    r = _resolve("live_unit_price_this_week")
    check(
        "not_found.status",
        r["status"] == akr.STATUS_NOT_FOUND,
        detail=str(r.get("status")),
    )
    check("not_found.no_answer", r.get("answer") is None)
    check("not_found.has_attempt_log", len(r.get("attempt_log") or []) >= 1)


def test_inaccessible() -> None:
    # Registry with only the Canva inaccessible source for visual_identity-ish key
    # Use a narrow registry so brand_guide does not answer.
    narrow = [
        {
            "source_id": "habitat-canva-kit",
            "scopes": ["brand:habitat"],
            "question_keys": ["canva_pixel_truth"],
            "authority": "CLIENT_APPROVED",
            "freshness": "2026-06-01",
            "lane": "brand_identity",
            "identity": {"brand": "habitat"},
            "accessible": False,
            "path": "habitat/canva_unreachable.json",
        }
    ]
    r = akr.resolve(
        "brand:habitat",
        "canva_pixel_truth",
        narrow,
        fixture_root=FIX,
        canonical=EMPTY_CANON,
    )
    check(
        "inaccessible.status",
        r["status"] == akr.STATUS_INACCESSIBLE,
        detail=str(r.get("status")),
    )
    check("inaccessible.no_answer", r.get("answer") is None)


def test_unknown_requires_search_evidence() -> None:
    r = akr.resolve(
        "brand:habitat",
        "obscure_thing",
        [],  # empty allowlist
        fixture_root=FIX,
        canonical=EMPTY_CANON,
    )
    check("unknown.status", r["status"] == akr.STATUS_UNKNOWN, detail=str(r.get("status")))
    log = r.get("attempt_log") or []
    check("unknown.has_attempt_log", len(log) >= 1)
    check(
        "unknown.mentions_search",
        any("allowlisted" in (a.get("detail") or "") or a.get("step") == "UNKNOWN" for a in log),
        detail=str(log),
    )


def test_inference_rejected() -> None:
    # Only inference source for a unique key
    reg = [
        {
            "source_id": "grok-inference-only",
            "scopes": ["brand:habitat"],
            "question_keys": ["invented_font"],
            "authority": "INFERENCE",
            "lane": "brand_identity",
            "identity": {"brand": "habitat"},
            "accessible": True,
            "facts": {"invented_font": "ComicSans"},
        }
    ]
    r = akr.resolve(
        "brand:habitat",
        "invented_font",
        reg,
        fixture_root=FIX,
        canonical={"fields": {"invented_font": ""}},
    )
    check(
        "inference.not_used_as_answer",
        (r.get("answer") or {}).get("value") != "ComicSans",
        detail=str(r.get("answer")),
    )
    check(
        "inference.not_found_or_unknown",
        r["status"] in (akr.STATUS_NOT_FOUND, akr.STATUS_UNKNOWN),
        detail=str(r.get("status")),
    )


def test_source_found_not_canonical() -> None:
    r = _resolve("brand_font")
    check("found.not_canonical_status", r["status"] == akr.STATUS_NOT_CANONICAL)
    prov = r.get("provenance") or []
    check("found.provenance_nonempty", len(prov) >= 1)
    if prov:
        check("found.source_not_marked_canonical", prov[0].get("canonical") is False)
        check(
            "found.authoritative_client",
            prov[0].get("authoritative") is True,
            detail=str(prov[0]),
        )


def test_max_sources_cap() -> None:
    many = []
    for i in range(12):
        many.append(
            {
                "source_id": f"pad-{i}",
                "scopes": ["brand:habitat"],
                "question_keys": ["pad_field"],
                "authority": "OPERATIONAL",
                "lane": "general",
                "identity": {"brand": "habitat"},
                "accessible": True,
                "facts": {"pad_field": f"v{i}"},
            }
        )
    r = akr.resolve(
        "brand:habitat",
        "pad_field",
        many,
        fixture_root=FIX,
        canonical=None,
        max_sources=8,
    )
    check("cap.sources_matched_12", r["caps"].get("sources_matched") == 12, detail=str(r["caps"]))
    check("cap.skipped_4", r["caps"].get("sources_skipped_cap") == 4, detail=str(r["caps"]))
    # All same value pattern — first 8 agree on different values → CONFLICTED
    check(
        "cap.conflict_or_answer",
        r["status"] in (akr.STATUS_CONFLICTED, akr.STATUS_NOT_CANONICAL),
        detail=str(r.get("status")),
    )


def test_max_bytes_cap() -> None:
    huge = "X" * (akr.MAX_BYTES_PER_SOURCE + 100)
    # Write temp oversized fixture
    big_path = FIX / "habitat" / "_oversized_tmp.json"
    try:
        big_path.write_text(json.dumps({"facts": {"oversized_key": huge}}), encoding="utf-8")
        reg = [
            {
                "source_id": "too-big",
                "scopes": ["brand:habitat"],
                "question_keys": ["oversized_key"],
                "authority": "OPERATIONAL",
                "lane": "general",
                "identity": {"brand": "habitat"},
                "accessible": True,
                "path": "habitat/_oversized_tmp.json",
            }
        ]
        r = akr.resolve(
            "brand:habitat",
            "oversized_key",
            reg,
            fixture_root=FIX,
            canonical=None,
        )
        check(
            "bytes.skipped_oversize",
            r["status"] == akr.STATUS_NOT_FOUND,
            detail=str(r.get("status")),
        )
        log = " ".join(a.get("detail", "") for a in r.get("attempt_log") or [])
        check("bytes.attempt_mentions_max", "max_bytes" in log, detail=log[:200])
    finally:
        if big_path.exists():
            big_path.unlink()


def test_scope_isolation() -> None:
    r = akr.resolve(
        "brand:habitat",
        "brand_font",
        REGISTRY,
        fixture_root=FIX,
        canonical=EMPTY_CANON,
    )
    ans = (r.get("answer") or {}).get("value") or (r.get("answer") or {}).get("brand_font")
    check("scope.habitat_not_uma", ans == "Manrope", detail=str(r.get("answer")))


def test_no_network_fixture_only() -> None:
    # Guard: registry paths are relative under fixtures; no http
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    for s in data["sources"]:
        p = s.get("path") or ""
        check(
            f"fixture.no_http:{s.get('source_id')}",
            not str(p).startswith("http"),
            detail=str(p),
        )


def main() -> int:
    test_honesty_and_caps()
    test_empty_field_not_unknown()
    test_canonical_present_short_circuit()
    test_manrope_vs_inter_scoped()
    test_conflicted_same_lane()
    test_not_found()
    test_inaccessible()
    test_unknown_requires_search_evidence()
    test_inference_rejected()
    test_source_found_not_canonical()
    test_max_sources_cap()
    test_max_bytes_cap()
    test_scope_isolation()
    test_no_network_fixture_only()

    print("")
    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
