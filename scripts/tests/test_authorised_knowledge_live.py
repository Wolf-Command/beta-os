#!/usr/bin/env python3
"""Live read-only prove for Habitat Authorised Knowledge Resolver.

Uses explicit allowlisted roots only. No crawl. No writes outside this repo
except reading the registered live sources. No customer PII in logs/assertions.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import authorised_knowledge as akr  # noqa: E402

LIVE_REGISTRY = SCRIPTS / "core" / "data" / "akr_habitat_live_registry.json"

PASS = 0
FAIL = 0

# LIVE prove statuses for the mission Done line
LIVE_STATUSES: dict[str, str] = {
    "font": "FAIL",
    "voice": "FAIL",
    "conflict": "FAIL",
    "empty": "FAIL",
    "absent": "FAIL",
}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _live_resolve(question_key: str, **kwargs):
    kw = {
        "scope": "brand:habitat",
        "question_key": question_key,
        "sources_registry": LIVE_REGISTRY,
        "canonical": kwargs.pop("canonical", {"fields": {}}),
    }
    kw.update(kwargs)
    return akr.resolve(**kw)


def _log_blob(r: dict) -> str:
    return json.dumps(
        {"attempt_log": r.get("attempt_log"), "provenance": r.get("provenance")},
        ensure_ascii=False,
        default=str,
    )


def _assert_no_secret_dump(r: dict, *, forbid_substrings: list[str]) -> bool:
    blob = _log_blob(r)
    for s in forbid_substrings:
        if s and s in blob:
            return False
    # Full phase26 / brand file bodies must not appear in attempt details
    for a in r.get("attempt_log") or []:
        detail = a.get("detail") or ""
        if len(detail) > 400 and ("def " in detail or "## ESSENCE" in detail):
            return False
    return True


def test_live_font_lanes() -> None:
    r_brand = _live_resolve("brand_font", canonical={"fields": {"brand_font": ""}})
    ans = r_brand.get("answer") or {}
    brand_ok = (
        r_brand["status"] == akr.STATUS_NOT_CANONICAL
        and ans.get("value") == "Manrope"
        and ans.get("lane") == "brand_identity"
        and r_brand["status"] != akr.STATUS_CONFLICTED
    )
    check("live.font.brand_manrope", brand_ok, detail=str({"status": r_brand.get("status"), "answer": ans}))

    prov = r_brand.get("provenance") or []
    pdf_prov = [p for p in prov if p.get("source_id") == "habitat-nas-brand-guide"]
    if pdf_prov:
        check(
            "live.font.pdf_client_approved",
            pdf_prov[0].get("authority") == "CLIENT_APPROVED",
            detail=str(pdf_prov[0]),
        )
        check(
            "live.font.pdf_provenance_page_sha",
            pdf_prov[0].get("page") is not None and bool(pdf_prov[0].get("sha256")),
            detail=str({k: pdf_prov[0].get(k) for k in ("page", "sha256", "path")}),
        )
    else:
        # PDF missing → vault OPERATIONAL still answers Manrope
        check(
            "live.font.vault_fallback_manrope",
            any(p.get("source_id") == "habitat-vault-brand" for p in prov)
            and ans.get("value") == "Manrope",
            detail=str(prov),
        )

    r_ui = _live_resolve("ui_font", canonical={"fields": {"ui_font": ""}})
    ui_ans = r_ui.get("answer") or {}
    ui_ok = (
        r_ui["status"] == akr.STATUS_NOT_CANONICAL
        and ui_ans.get("value") == "Inter"
        and ui_ans.get("lane") == "ui_chrome"
        and r_ui["status"] != akr.STATUS_CONFLICTED
    )
    check("live.font.ui_inter", ui_ok, detail=str({"status": r_ui.get("status"), "answer": ui_ans}))

    # Two answers, distinct lanes — not CONFLICTED when asked separately
    check(
        "live.font.lanes_not_conflicted",
        brand_ok and ui_ok and r_brand["status"] != akr.STATUS_CONFLICTED and r_ui["status"] != akr.STATUS_CONFLICTED,
    )
    if brand_ok and ui_ok:
        LIVE_STATUSES["font"] = "PASS"
    else:
        LIVE_STATUSES["font"] = str(r_brand.get("status")) + "/" + str(r_ui.get("status"))


def test_live_brand_voice() -> None:
    r = _live_resolve("brand_voice", canonical={"fields": {"brand_voice": ""}})
    ans = r.get("answer") or {}
    val = ans.get("value") or ""
    ok = (
        r["status"] == akr.STATUS_NOT_CANONICAL
        and ans.get("kind") == "EVIDENCE"
        and "interpretation" not in ans
        and isinstance(val, str)
        and len(val) > 20
        and ("Voice Descriptors" in val or "Brand Essence" in val or "property-portfolio" in val)
    )
    check("live.voice.status_evidence", ok, detail=str({"status": r.get("status"), "kind": ans.get("kind"), "value_len": len(str(val))}))
    prov = r.get("provenance") or []
    check(
        "live.voice.source_vault_brand",
        any(p.get("source_id") == "habitat-vault-brand" for p in prov),
        detail=str([p.get("source_id") for p in prov]),
    )
    check(
        "live.voice.kind_evidence_prov",
        any(p.get("kind") == "EVIDENCE" for p in prov) or ans.get("kind") == "EVIDENCE",
    )
    LIVE_STATUSES["voice"] = "PASS" if ok else str(r.get("status"))


def test_live_headline_conflict() -> None:
    r = _live_resolve("headline_case", canonical={"fields": {"headline_case": ""}})
    check(
        "live.conflict.status",
        r["status"] == akr.STATUS_CONFLICTED,
        detail=str(r.get("status")),
    )
    check("live.conflict.no_winner", r.get("answer") is None)
    sides = []
    authorities = set()
    for c in r.get("conflicts") or []:
        check("live.conflict.lane_brand_identity", c.get("lane") == "brand_identity", detail=str(c))
        for v in c.get("values") or []:
            sides.append(v.get("value"))
            authorities.add(v.get("authority"))
    check(
        "live.conflict.both_cases",
        "lowercase" in sides and "UPPERCASE" in sides,
        detail=str(sides),
    )
    check(
        "live.conflict.peer_operational",
        authorities == {"OPERATIONAL"} or "OPERATIONAL" in authorities,
        detail=str(authorities),
    )
    ok = r["status"] == akr.STATUS_CONFLICTED and r.get("answer") is None
    LIVE_STATUSES["conflict"] = "PASS" if ok else str(r.get("status"))


def test_live_empty_field_not_unknown() -> None:
    r = _live_resolve(
        "brand_voice",
        canonical={"fields": {"brand_voice": ""}},
    )
    ok = r["status"] == akr.STATUS_NOT_CANONICAL and r["status"] != akr.STATUS_UNKNOWN
    check("live.empty.status_not_canonical", ok, detail=str(r.get("status")))
    check("live.empty.not_unknown", r["status"] != akr.STATUS_UNKNOWN)
    ans = r.get("answer") or {}
    check(
        "live.empty.carries_evidence",
        bool(ans.get("value")) and ans.get("canonical") is False,
        detail=str({"canonical": ans.get("canonical"), "has_value": bool(ans.get("value"))}),
    )
    log = " ".join(a.get("detail", "") for a in r.get("attempt_log") or [])
    check("live.empty.attempt_mentions_empty", "EMPTY FIELD" in log or "empty" in log.lower())
    LIVE_STATUSES["empty"] = "PASS" if ok else str(r.get("status"))


def test_live_absent() -> None:
    r = _live_resolve("habitat_submarine_policy", canonical={"fields": {}})
    check(
        "live.absent.status",
        r["status"] in (akr.STATUS_NOT_FOUND, akr.STATUS_UNKNOWN),
        detail=str(r.get("status")),
    )
    check("live.absent.no_answer", r.get("answer") is None)
    log = r.get("attempt_log") or []
    check("live.absent.has_attempt_log", len(log) >= 1)
    skip_reasons = [
        a for a in log if a.get("step") == "DISCOVER" and "skipped" in (a.get("detail") or "")
    ]
    check(
        "live.absent.lists_skip_reasons",
        len(skip_reasons) >= 1,
        detail=str(skip_reasons[:6]),
    )
    # Must not invent a fake source
    ids = {a.get("source_id") for a in log if a.get("source_id")}
    check("live.absent.no_fake_source", "habitat-submarine" not in ids)
    LIVE_STATUSES["absent"] = "PASS" if r["status"] in (akr.STATUS_NOT_FOUND, akr.STATUS_UNKNOWN) else str(r.get("status"))


def test_security_path_dotdot() -> None:
    with tempfile.TemporaryDirectory(prefix="akr-allow-") as tmp:
        root = Path(tmp)
        safe = root / "safe.md"
        safe.write_text("Primary Typeface: Manrope\n", encoding="utf-8")
        # Escape via ..
        evil = str(root / "sub" / ".." / ".." / "outside.md")
        reg = {
            "allowlisted_roots": [str(root) + "/"],
            "sources": [
                {
                    "source_id": "evil-dotdot",
                    "type": "markdown",
                    "scopes": ["brand:habitat"],
                    "question_keys": ["brand_font"],
                    "authority": "OPERATIONAL",
                    "lane": "brand_identity",
                    "identity": {"brand": "habitat"},
                    "path": evil,
                }
            ],
        }
        r = akr.resolve(
            "brand:habitat",
            "brand_font",
            reg,
            canonical={"fields": {"brand_font": ""}},
        )
        check(
            "sec.dotdot.inaccessible",
            r["status"] == akr.STATUS_INACCESSIBLE,
            detail=str(r.get("status")),
        )


def test_security_scope_isolation() -> None:
    with tempfile.TemporaryDirectory(prefix="akr-scope-") as tmp:
        root = Path(tmp)
        uma = root / "uma.md"
        uma.write_text("Primary Typeface: ComicSans\n", encoding="utf-8")
        reg = {
            "allowlisted_roots": [str(root) + "/"],
            "sources": [
                {
                    "source_id": "uma-only",
                    "type": "markdown",
                    "scopes": ["brand:uma-blu"],
                    "question_keys": ["brand_font"],
                    "authority": "CLIENT_APPROVED",
                    "lane": "brand_identity",
                    "identity": {"brand": "uma-blu"},
                    "path": str(uma),
                }
            ],
        }
        r = akr.resolve(
            "brand:habitat",
            "brand_font",
            reg,
            canonical={"fields": {"brand_font": ""}},
        )
        check(
            "sec.scope.uma_not_retrieved",
            r["status"] in (akr.STATUS_NOT_FOUND, akr.STATUS_UNKNOWN),
            detail=str(r.get("status")),
        )
        check(
            "sec.scope.no_comicsans",
            (r.get("answer") or {}).get("value") != "ComicSans",
            detail=str(r.get("answer")),
        )


def test_security_bytes_cap() -> None:
    with tempfile.TemporaryDirectory(prefix="akr-bytes-") as tmp:
        root = Path(tmp)
        big = root / "big.md"
        # File larger than a tight cap; must not fully ingest
        payload = ("X" * 5000) + "\nPrimary Typeface: Manrope\n"
        big.write_text(payload, encoding="utf-8")
        reg = {
            "allowlisted_roots": [str(root) + "/"],
            "sources": [
                {
                    "source_id": "oversized-md",
                    "type": "markdown",
                    "scopes": ["brand:habitat"],
                    "question_keys": ["brand_font"],
                    "authority": "OPERATIONAL",
                    "lane": "brand_identity",
                    "identity": {"brand": "habitat"},
                    "path": str(big),
                }
            ],
        }
        cap = 200
        r = akr.resolve(
            "brand:habitat",
            "brand_font",
            reg,
            canonical={"fields": {"brand_font": ""}},
            max_bytes_per_source=cap,
        )
        # Cap truncates before Manrope (at offset 5000) → no hit or capped bytes
        prov = r.get("provenance") or []
        bytes_ok = all(int(p.get("bytes_read") or 0) <= cap for p in prov)
        log = " ".join(a.get("detail", "") for a in r.get("attempt_log") or [])
        check(
            "sec.bytes.not_fully_ingested",
            bytes_ok and ("truncated=True" in log or r["status"] in (akr.STATUS_NOT_FOUND, akr.STATUS_NOT_CANONICAL)),
            detail=str({"status": r.get("status"), "log": log[:240], "prov": prov}),
        )
        # Attempt log must not contain the full 5k body
        check("sec.bytes.log_no_full_body", "X" * 500 not in log)


def test_security_unsupported_type() -> None:
    with tempfile.TemporaryDirectory(prefix="akr-png-") as tmp:
        root = Path(tmp)
        png = root / "logo.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
        reg = {
            "allowlisted_roots": [str(root) + "/"],
            "sources": [
                {
                    "source_id": "png-logo",
                    "type": "png",
                    "scopes": ["brand:habitat"],
                    "question_keys": ["brand_font"],
                    "authority": "OPERATIONAL",
                    "lane": "brand_identity",
                    "identity": {"brand": "habitat"},
                    "path": str(png),
                }
            ],
        }
        r = akr.resolve(
            "brand:habitat",
            "brand_font",
            reg,
            canonical={"fields": {"brand_font": ""}},
        )
        check(
            "sec.png.inaccessible",
            r["status"] == akr.STATUS_INACCESSIBLE,
            detail=str(r.get("status")),
        )


def test_security_no_secret_in_logs() -> None:
    # Use live resolve; ensure attempt_log does not dump full source bodies
    r = _live_resolve("brand_font", canonical={"fields": {"brand_font": ""}})
    phase26 = (SCRIPTS / "phase26_team.py").read_text(encoding="utf-8")
    # A distinctive long unique slice from mid-file should not appear in logs
    marker = None
    for line in phase26.splitlines():
        if len(line) > 40 and "SHARED" not in line and "Inter" not in line:
            marker = line.strip()
            if len(marker) > 40:
                break
    ok = _assert_no_secret_dump(r, forbid_substrings=[marker] if marker else [])
    check("sec.logs.no_secret_dump", ok, detail="attempt/provenance leaked source body")


def test_registry_shape() -> None:
    data = json.loads(LIVE_REGISTRY.read_text(encoding="utf-8"))
    roots = data.get("allowlisted_roots") or []
    check("reg.roots_count", len(roots) == 3, detail=str(roots))
    ids = [s["source_id"] for s in data["sources"]]
    check(
        "reg.source_ids",
        ids
        == [
            "habitat-nas-brand-guide",
            "habitat-vault-brand",
            "habitat-vault-strategy",
            "wolf-ui-chrome",
        ],
        detail=str(ids),
    )
    check("reg.no_drive_notion", not any("drive" in i or "notion" in i for i in ids))
    # Authority explicit on each source
    for s in data["sources"]:
        check(
            f"reg.authority_explicit:{s['source_id']}",
            bool(s.get("authority")),
            detail=str(s.get("authority")),
        )


def main() -> int:
    if not LIVE_REGISTRY.is_file():
        print(f"FAIL  live registry missing: {LIVE_REGISTRY}")
        return 1

    test_registry_shape()
    test_live_font_lanes()
    test_live_brand_voice()
    test_live_headline_conflict()
    test_live_empty_field_not_unknown()
    test_live_absent()
    test_security_path_dotdot()
    test_security_scope_isolation()
    test_security_bytes_cap()
    test_security_unsupported_type()
    test_security_no_secret_in_logs()

    print("")
    print(f"PASS={PASS} FAIL={FAIL}")
    print(
        "LIVE: "
        f"font={LIVE_STATUSES['font']} "
        f"voice={LIVE_STATUSES['voice']} "
        f"conflict={LIVE_STATUSES['conflict']} "
        f"empty={LIVE_STATUSES['empty']} "
        f"absent={LIVE_STATUSES['absent']}"
    )
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
