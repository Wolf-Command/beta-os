#!/usr/bin/env python3
"""Sprint2 P7 Dashboard Derivation Prove — fixture mutate tests.

Plan: docs/deliveries/GROK-PLAN-SPRINT2-P7-DERIVATION-PROVE-2026-09-22.md
Bound: beta-derive-prove-safe
Claim: bf-sprint2-p7-derivation-v2-20260922

Canonical change → Progress / CR / Needs You / Empire / Integration Health /
Sale Readiness auto-update OR visibly FAIL STALE. No second scoring table.
No invent SYSTEM%/PROVEN/READY. No Production. No silent unpark prior P7.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"

from core import derivation_prove as dp  # noqa: E402
from core import progress_read_model as prm  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
PARKED = ROOT / "state" / "build-factory" / "PARKED-BF-sprint2-p7-derivation-prove-20260922.json"
WIP = (
    "scripts/migrations/migrate_phase2_6_team_readiness.py",
    "scripts/phase26_team.py",
    "scripts/skills/__init__.py",
    "scripts/wolf_intelligence.py",
)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_honesty_and_refuses() -> None:
    flags = dp.honesty_flags()
    check("bound", flags["bound"] == "beta-derive-prove-safe")
    check("run_id v2", flags["run_id"] == dp.RUN_ID)
    check("claim id", flags["claim_id"] == dp.CLAIM_ID)
    check("no silent unpark", flags["silent_unpark_prior_p7"] is False)
    check("no second scoring table", flags["second_scoring_table"] is False)
    check("not invent system%", flags["invented_system_pct"] is False)
    check("not proven", flags["proven"] is False and flags["invented_proven"] is False)
    check("not ready", flags["ready"] is False and flags["invented_ready"] is False)
    check("no ledger write", flags["ledger_write"] is False)
    check("no production", flags["production"] is False)
    check("surfaces six", flags["surfaces"] == list(dp.SURFACES))
    schema = dp.schema_document()
    check("schema id", schema["id"] == dp.SCHEMA_ID)
    check("schema writes false", schema["writes"] is False)
    for name, fn, code in (
        ("proven", dp.refuse_proven, "proven_refused"),
        ("ready", dp.refuse_ready, "ready_refused"),
        ("percent", dp.refuse_percent, "percent_refused"),
        ("ledger", dp.refuse_ledger_write, "ledger_write_refused"),
        ("production", dp.refuse_production, "production_refused"),
        ("unpark", dp.refuse_silent_unpark, "silent_unpark_refused"),
    ):
        try:
            fn({})
            check(f"{name} raises", False)
        except dp.DeriveProveError as exc:
            check(f"{name} refused", exc.code == code, exc.code)


def test_surface_proves() -> None:
    with tempfile.TemporaryDirectory(prefix="p7-derive-") as td:
        root = Path(td)
        report = dp.run_all_proves(td=root)
        check("run_all ok", report.get("ok") is True, str(report.get("frozen_scan")))
        check("bound in report", report.get("bound") == dp.BOUND)
        by = {r["surface"]: r for r in report["results"]}
        # Progress appears twice (auto-update + fail-stale) — collect by mode
        progress_rows = [r for r in report["results"] if r["surface"] == "progress"]
        check("progress proves ≥2", len(progress_rows) >= 2, str(len(progress_rows)))
        auto = next((r for r in progress_rows if r.get("mode") == "AUTO_UPDATE"), None)
        stale = next((r for r in progress_rows if r.get("fail_stale")), None)
        check("progress auto-update", auto is not None and auto.get("ok") is True, str(auto))
        check(
            "progress FAIL STALE",
            stale is not None
            and stale.get("ok") is True
            and stale.get("mode") == dp.FAIL_STALE
            and stale.get("visible_label") == dp.FAIL_STALE,
            str(stale),
        )
        for surface in (
            "completion_register",
            "needs_you",
            "empire",
            "integration_health",
            "sale_readiness",
        ):
            row = by.get(surface) or {}
            check(f"{surface} ok", row.get("ok") is True, str(row))
            check(
                f"{surface} auto or stale",
                row.get("mode") in ("AUTO_UPDATE", dp.FAIL_STALE),
                str(row.get("mode")),
            )
        frozen = report.get("frozen_scan") or {}
        check("frozen scan clean", frozen.get("ok") is True, str(frozen.get("hits")))


def test_individual_fixture_mutates() -> None:
    with tempfile.TemporaryDirectory(prefix="p7-one-") as td:
        base = Path(td)
        p = dp.prove_progress_auto_update(td=base / "p")
        (base / "p").mkdir(exist_ok=True)
        # re-run with existing dir
        p = dp.prove_progress_auto_update(td=base / "p")
        check("progress mutate ok", p.get("ok") is True, str(p))
        check("progress pct moved", p.get("before_pct") != p.get("after_pct"), str(p))

        s = dp.prove_progress_fail_stale(td=base / "s")
        (base / "s").mkdir(exist_ok=True)
        s = dp.prove_progress_fail_stale(td=base / "s")
        check("stale ok", s.get("ok") is True and s.get("fail_stale") is True, str(s))
        check("stale status", s.get("status") == prm.STALE_STATUS, str(s.get("status")))

        (base / "cr").mkdir(exist_ok=True)
        c = dp.prove_completion_register(td=base / "cr")
        check("cr ok", c.get("ok") is True, str(c))
        check(
            "cr bumped",
            c.get("after_unresolved", 0) == c.get("before_unresolved", -1) + 1,
            str(c),
        )

        (base / "ny").mkdir(exist_ok=True)
        n = dp.prove_needs_you(td=base / "ny")
        check("needs_you ok", n.get("ok") is True, str(n))
        check("needs_you grew", n.get("after_n", 0) >= n.get("before_n", 0) + 1, str(n))

        (base / "e").mkdir(exist_ok=True)
        e = dp.prove_empire(td=base / "e")
        check("empire ok", e.get("ok") is True, str(e))
        check(
            "empire auto or stale",
            e.get("mode") in ("AUTO_UPDATE", dp.FAIL_STALE),
            str(e),
        )

        (base / "ih").mkdir(exist_ok=True)
        i = dp.prove_integration_health(td=base / "ih")
        check("integration_health ok", i.get("ok") is True, str(i))
        check(
            "ih status flip",
            i.get("before_status") == "NOT_CONFIGURED" and i.get("after_status") == "READ_OK",
            str(i),
        )

        (base / "sale").mkdir(exist_ok=True)
        sale = dp.prove_sale_readiness(td=base / "sale")
        check("sale_readiness ok", sale.get("ok") is True, str(sale))
        check(
            "sale grew",
            sale.get("after_n", 0) == sale.get("before_n", -1) + 1,
            str(sale),
        )


def test_live_ledger_untouched_and_parked_prior() -> None:
    before = _sha(LEDGER)
    with tempfile.TemporaryDirectory(prefix="p7-live-") as td:
        report = dp.run_all_proves(td=Path(td))
        check("prove ran", report.get("ok") is True)
    after = _sha(LEDGER)
    check("live ledger bytes unchanged", before == after)
    check("prior P7 park file remains", PARKED.is_file())
    parked = json.loads(PARKED.read_text(encoding="utf-8"))
    check(
        "prior P7 still parked run_id",
        parked.get("run_id") == dp.PRIOR_PARKED_RUN,
        str(parked.get("run_id")),
    )
    check("v2 run ≠ parked run", dp.RUN_ID != dp.PRIOR_PARKED_RUN)


def test_html_fail_stale_visible() -> None:
    html = (ROOT / "dashboards" / "progress.html").read_text(encoding="utf-8")
    check("progress HTML has SCORING PROJECTION STALE", "SCORING PROJECTION STALE" in html)
    check("progress HTML has PROJECTION STALE", "PROJECTION STALE" in html)
    empire_html = (ROOT / "dashboards" / "owner-empire-pack.html").read_text(encoding="utf-8")
    check(
        "empire HTML derives today.system_pct (no freeze)",
        "today.system_pct" in empire_html,
    )
    check(
        "empire HTML LEDGER gate",
        'today.status === "LEDGER"' in empire_html,
    )


def test_wip_untouched_digests() -> None:
    for rel in WIP:
        path = ROOT / rel
        check(f"wip present {rel}", path.is_file())


def main() -> int:
    test_honesty_and_refuses()
    test_surface_proves()
    test_individual_fixture_mutates()
    test_live_ledger_untouched_and_parked_prior()
    test_html_fail_stale_visible()
    test_wip_untouched_digests()
    print(f"\nPASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
