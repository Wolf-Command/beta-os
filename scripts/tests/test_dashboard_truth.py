#!/usr/bin/env python3
"""Dashboard truth — SYSTEM from Model C ledger; no hard-coded live %."""
from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import core.progress_read_model as prm  # noqa: E402

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HTML = ROOT / "dashboards" / "progress.html"
READ_MODEL = SCRIPTS / "core" / "progress_read_model.py"
RULE = ROOT / "docs" / "RULE-Dashboard-Projection-2026-09-18.md"

CREDITS = {
    "ABSENT": Decimal("0.00"),
    "SPECIFIED": Decimal("0.05"),
    "BUILT": Decimal("0.25"),
    "PROVEN": Decimal("0.80"),
    "READY": Decimal("1.00"),
}

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


def ledger_sum_and_pct(path: Path) -> tuple[Decimal, float, int]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    total = sum(CREDITS[str(row[0]).upper()] for row in raw.values())
    n = len(raw)
    pct = float((total / Decimal(77) * Decimal(100)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    return total, pct, n


def find_specified_cap(raw: dict) -> str:
    for cid, row in raw.items():
        if str(row[0]).upper() == "SPECIFIED":
            return cid
    raise RuntimeError("no SPECIFIED row in temp ledger")


def main() -> int:
    check("rule doc exists", RULE.is_file())
    check("ledger exists", LEDGER.is_file())
    check("progress.html exists", HTML.is_file())

    live_sum, live_pct, live_n = ledger_sum_and_pct(LEDGER)
    check("live ledger n=77", live_n == 77, str(live_n))
    check("live sum credits == 19.65", live_sum == Decimal("19.65"), str(live_sum))
    check("live computed pct is 25.5", live_pct == 25.5, str(live_pct))
    check("live computed pct one-decimal", isinstance(live_pct, float), str(live_pct))

    system = prm.compute_system_from_ledger(LEDGER)
    check("compute status OK", system.get("status") == "OK", str(system.get("status")))
    check("compute system_pct matches ledger", system.get("system_pct") == live_pct, str(system.get("system_pct")))
    check("compute sum matches", Decimal(str(system.get("sum_credits_exact"))) == live_sum)
    check("counts present", set((system.get("counts") or {})) >= {"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
    check("formula present", "77" in (system.get("formula") or ""))

    model = prm.build_read_model()
    check("model ok", model.get("ok") is True)
    check("primary progress_type SYSTEM_FROM_LEDGER", model.get("progress_type") == "SYSTEM_FROM_LEDGER")
    check("legacy progress_type retained", model.get("legacy_progress_type") == "PARTIAL_ESTIMATE")
    msys = model.get("system") or {}
    check("model system_pct matches ledger", msys.get("system_pct") == live_pct, str(msys.get("system_pct")))
    check("integrity ok", (msys.get("integrity") or {}).get("ok") is True, str(msys.get("integrity")))
    check("system is primary", msys.get("primary") is True)

    overall = model.get("overall") or {}
    check("legacy overall labelled PARTIAL ESTIMATE", overall.get("label") == "PARTIAL ESTIMATE")
    check("legacy overall marked retired_as_primary", overall.get("retired_as_primary") is True)

    dials = model.get("model_e") or []
    check("model_e has 5 dials", len(dials) == 5, str(len(dials)))
    check("no SYSTEM dial in model_e list", all(d.get("id") != "SYSTEM" and d.get("label") != "SYSTEM" for d in dials))
    expected_labels = [
        "Operating Adoption",
        "Data / Measurement",
        "Founder Independence",
        "Financial Control",
        "Sale Readiness",
    ]
    check(
        "five Model E labels exact",
        [d.get("label") for d in dials] == expected_labels,
        str([d.get("label") for d in dials]),
    )
    unscored = [d for d in dials if d.get("display") == "Not scored yet"]
    check("five dials Not scored yet", len(unscored) == 5, str([d.get("display") for d in dials]))
    check("no fake 0% on unscored", all(d.get("value") is None for d in dials))

    detail = model.get("system_detail") or {}
    check("detail capability_count 77", detail.get("capability_count") == 77)
    check("detail has domain_counts", len(detail.get("domain_counts") or []) >= 10)
    check("detail domains from catalog (D-)", all(str(d.get("domain", "")).startswith("D-") for d in (detail.get("domain_counts") or [])))

    nav = model.get("nav") or []
    labels = [n.get("label") for n in nav]
    check("nav Empire GGV AMG BZG", labels == ["Empire", "GGV", "AMG", "BZG"], str(labels))
    bzg = next((n for n in nav if n.get("id") == "BZG"), {})
    hrefs = {l.get("href") for l in (bzg.get("links") or [])}
    check("BZG links /bzg and /bzg/uma-blu", hrefs == {"/bzg", "/bzg/uma-blu"}, str(hrefs))

    # --- Regression on TEMP ledger only (never write live ledger) ---
    raw = json.loads(LEDGER.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="dash-truth-") as td:
        tmp = Path(td) / "ledger.json"
        tmp.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        before = prm.compute_system_from_ledger(tmp)
        cap = find_specified_cap(raw)
        moved = copy.deepcopy(raw)
        row = list(moved[cap])
        row[0] = "BUILT"
        moved[cap] = row
        tmp.write_text(json.dumps(moved, indent=2), encoding="utf-8")
        after = prm.compute_system_from_ledger(tmp)
        expected_delta_exact = float(Decimal("0.20") / Decimal(77) * Decimal(100))
        # Prefer exact credit delta; rounded display delta may be 0.2 or 0.3 depending on half-up boundaries.
        sum_before = Decimal(str(before["sum_credits_exact"]))
        sum_after = Decimal(str(after["sum_credits_exact"]))
        check(
            "SPECIFIED→BUILT sum delta == 0.20",
            sum_after - sum_before == Decimal("0.20"),
            f"{sum_after - sum_before}",
        )
        delta = (after["system_pct"] or 0) - (before["system_pct"] or 0)
        check(
            "SPECIFIED→BUILT pct delta ≈ 0.20/77*100",
            abs(delta - expected_delta_exact) < 0.15,
            f"delta={delta} expected≈{expected_delta_exact}",
        )
        # Move back
        tmp.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        restored = prm.compute_system_from_ledger(tmp)
        check(
            "score returns after move-back",
            restored.get("system_pct") == before.get("system_pct"),
            f"{restored.get('system_pct')} vs {before.get('system_pct')}",
        )

        # Integrity stale: point read model at temp that disagrees with live ledger compare path
        tmp.write_text(json.dumps(moved, indent=2), encoding="utf-8")
        stale_model = prm.build_read_model(
            ledger_path=tmp,
            integrity_against_path=LEDGER,
        )
        ssys = stale_model.get("system") or {}
        check(
            "disagreeing integrity → STALE",
            ssys.get("status") == prm.STALE_STATUS,
            str(ssys.get("status")),
        )
        check("stale hides percentage", ssys.get("system_pct") is None, str(ssys.get("system_pct")))

        # Wrong count → stale
        short = {k: moved[k] for k in list(moved.keys())[:76]}
        short_path = Path(td) / "short.json"
        short_path.write_text(json.dumps(short), encoding="utf-8")
        short_sys = prm.compute_system_from_ledger(short_path)
        check("n≠77 → STALE", short_sys.get("status") == prm.STALE_STATUS)
        check("n≠77 no pct", short_sys.get("system_pct") is None)

        # Unknown state hard fail
        bad = copy.deepcopy(raw)
        first = next(iter(bad))
        badrow = list(bad[first])
        badrow[0] = "HALF_BAKED"
        bad[first] = badrow
        bad_path = Path(td) / "bad.json"
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        raised = False
        try:
            prm.compute_system_from_ledger(bad_path)
        except ValueError as exc:
            raised = True
            check("unknown state hard fail message", "Unknown maturity state" in str(exc), str(exc))
        check("unknown state raises", raised)

    # Live ledger must remain untouched by this test
    after_live = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("live ledger unchanged by tests", after_live == raw)

    # Grep-style: no hard-coded live 25.3; 28 only as retired/legacy history
    html = HTML.read_text(encoding="utf-8")
    rm = READ_MODEL.read_text(encoding="utf-8")
    check("HTML has no hard-coded 25.3", "25.3" not in html)
    check("read model has no hard-coded 25.3", "25.3" not in rm)
    check("HTML primary dial uses system.system_pct", "system.system_pct" in html or "systemPct" in html)
    check("HTML shows Not scored yet", "Not scored yet" in html)
    check("HTML primary title WOLF TRANSFORMATION", "WOLF TRANSFORMATION" in html)
    check("HTML SYSTEM headline binds systemPct", "SYSTEM — ${esc(systemPct)}%" in html)
    # Entity surfaces P2 — dedicated AMG; domain % honesty on GGV/AMG/BZG
    check("HTML AMG dedicated title AMG · Atrium", "AMG · Atrium" in html)
    check("HTML AMG dedicated render branch", 'if (view === "AMG")' in html)
    check(
        "HTML GGV/AMG/BZG domain pct labelled ESTIMATED",
        html.count("${esc(v.pct)}% · ESTIMATED") >= 3
        and 'if (view === "GGV")' in html
        and 'if (view === "AMG")' in html
        and 'if (view === "BZG")' in html,
        str(html.count("${esc(v.pct)}% · ESTIMATED")),
    )
    check(
        "HTML subtitle technical capability",
        "Technical capability built &amp; proven" in html
        or "Technical capability built & proven" in html,
    )
    panel_match = re.search(
        r'data-owner-primary="wolf-transform">([\s\S]*?)<p class="legacy-note">',
        html,
    )
    primary_body = panel_match.group(1) if panel_match else ""
    check("primary card markup found", bool(panel_match))
    check(
        "phase sentence not in primary card",
        "phase-line" not in primary_body and "${esc(phase)}" not in primary_body,
    )
    check(
        "decorative chips absent from primary card",
        "Status vocabulary" not in primary_body
        and "heroChips" not in primary_body
        and 'class="chips"' not in primary_body
        and "BUILT" not in primary_body,
    )
    check("phase sentence under SYSTEM detail", 'class="phase-line">${esc(phase)}' in html)
    check("HTML shows SYSTEM label", "SYSTEM" in html)
    check("HTML legacy notes PARTIAL ESTIMATE", "PARTIAL ESTIMATE" in html)
    check("HTML does not use overall_pct as primary pct dial", 'class="pct">${esc(overall.overall_pct)}' not in html)
    check("HTML links /bzg", 'href="/bzg"' in html)
    check("HTML links /bzg/uma-blu", 'href="/bzg/uma-blu"' in html)
    check("RULE says projection", "projection" in RULE.read_text(encoding="utf-8").lower())

    # 28 as live % forbidden unless legacy/retired context in source
    for label, text in (("html", html), ("read_model", rm)):
        bad_28 = False
        for m in re.finditer(r"(?<![0-9])28(?:\s*%|\s*percent)?", text):
            ctx = text[max(0, m.start() - 80) : m.end() + 40].lower()
            if any(x in ctx for x in ("legacy", "retired", "history", "prior", "pending", "old ")):
                continue
            bad_28 = True
            break
        check(f"{label} has no live hard-coded 28%", not bad_28)

    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
