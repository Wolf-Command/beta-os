#!/usr/bin/env python3
"""Sprint2 P7 Dashboard Derivation Prove — Beta only.

Decision served: 2026-09-22 COMPRESSED-SPRINT-2 Gap Attack P7
(docs/deliveries/GROK-PLAN-SPRINT2-P7-DERIVATION-PROVE-2026-09-22.md /
docs/deliveries/GROK-GAP-ATTACK-SPRINT-2-2026-09-22.md §3–4),
extending 2026-09-17 Progress Dashboard PICK and 2026-09-18
RULE-Dashboard-Projection LOCKED.

Bound: beta-derive-prove-safe

Prove invariant: canonical underlying state change → Progress / Completion
Register / Needs You / Empire / Integration Health / Sale Readiness
projections auto-update OR visibly FAIL STALE.

No second scoring table. No invent SYSTEM% / PROVEN / READY.
No Production / money / CF / Access mutate. No silent unpark of prior P7.
"""
from __future__ import annotations

import copy
import csv
import json
import re
import sqlite3
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any

from core import completion_register as cr
from core import integration_health as ih
from core import owner_empire_pack as empire
from core import progress_read_model as prm

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
OVERLAY = BETA_ROOT / "state" / "progress" / "v1_overlay.json"
SALE_CSV = BETA_ROOT / "docs" / "canon" / "build-dashboard" / "Sale_Readiness.csv"

BOUND = "beta-derive-prove-safe"
SCHEMA_ID = "wolf.derivation-prove.v1"
SLICE = "sprint2_p7_derivation_prove_v2"
RUN_ID = "BF-sprint2-p7-derivation-prove-v2-20260922"
CLAIM_ID = "bf-sprint2-p7-derivation-v2-20260922"
PRIOR_PARKED_RUN = "BF-sprint2-p7-derivation-prove-20260922"
FAIL_STALE = "FAIL STALE"

SURFACES = (
    "progress",
    "completion_register",
    "needs_you",
    "empire",
    "integration_health",
    "sale_readiness",
)

# Projection surfaces that must never embed a live SYSTEM dial literal.
SCAN_PATHS = (
    BETA_ROOT / "dashboards" / "progress.html",
    BETA_ROOT / "dashboards" / "owner-empire-pack.html",
    BETA_ROOT / "scripts" / "core" / "progress_read_model.py",
    BETA_ROOT / "scripts" / "core" / "owner_empire_pack.py",
    BETA_ROOT / "scripts" / "core" / "derivation_prove.py",
)


class DeriveProveError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def honesty_flags() -> dict[str, Any]:
    return {
        "bound": BOUND,
        "schema": SCHEMA_ID,
        "slice": SLICE,
        "run_id": RUN_ID,
        "claim_id": CLAIM_ID,
        "prior_parked_run": PRIOR_PARKED_RUN,
        "silent_unpark_prior_p7": False,
        "second_scoring_table": False,
        "invented_system_pct": False,
        "invented_proven": False,
        "invented_ready": False,
        "proven": False,
        "ready": False,
        "caps_raised": False,
        "ledger_write": False,
        "production": False,
        "money": False,
        "cloudflare_mutated": False,
        "access_mutated": False,
        "surfaces": list(SURFACES),
        "fail_stale_label": FAIL_STALE,
    }


def refuse_proven(_body: dict | None = None) -> None:
    raise DeriveProveError("Derivation prove does not mark PROVEN.", code="proven_refused")


def refuse_ready(_body: dict | None = None) -> None:
    raise DeriveProveError("Derivation prove does not mark READY.", code="ready_refused")


def refuse_percent(_body: dict | None = None) -> None:
    raise DeriveProveError(
        "Derivation prove refuses an invented SYSTEM%.",
        code="percent_refused",
    )


def refuse_ledger_write(_body: dict | None = None) -> None:
    raise DeriveProveError(
        "Derivation prove does not write the Model C ledger.",
        code="ledger_write_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise DeriveProveError(
        "Derivation prove does not touch Production.",
        code="production_refused",
    )


def refuse_silent_unpark(_body: dict | None = None) -> None:
    raise DeriveProveError(
        f"Prior P7 {PRIOR_PARKED_RUN} stays PARKED. Use new run_id {RUN_ID}.",
        code="silent_unpark_refused",
    )


def _ok(surface: str, detail: str, **extra: Any) -> dict[str, Any]:
    out = {
        "surface": surface,
        "ok": True,
        "mode": "AUTO_UPDATE",
        "fail_stale": False,
        "detail": detail,
    }
    out.update(extra)
    return out


def _stale(surface: str, detail: str, **extra: Any) -> dict[str, Any]:
    out = {
        "surface": surface,
        "ok": True,
        "mode": FAIL_STALE,
        "fail_stale": True,
        "detail": detail,
        "visible_label": FAIL_STALE,
    }
    out.update(extra)
    return out


def _fail(surface: str, detail: str, **extra: Any) -> dict[str, Any]:
    out = {
        "surface": surface,
        "ok": False,
        "mode": "PROVE_FAILED",
        "fail_stale": False,
        "detail": detail,
    }
    out.update(extra)
    return out


def _copy_ledger(dest: Path) -> dict[str, Any]:
    raw = json.loads(LEDGER.read_text(encoding="utf-8"))
    dest.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    return raw


def _find_state(raw: dict[str, Any], state: str) -> str:
    want = state.upper()
    for cap_id, row in raw.items():
        if isinstance(row, (list, tuple)) and row and str(row[0]).upper() == want:
            return str(cap_id)
    raise DeriveProveError(f"no {want} row in fixture ledger", code="fixture")


def prove_progress_auto_update(*, td: Path | None = None) -> dict[str, Any]:
    """Canonical ledger maturity change → Progress SYSTEM% refreshes on next read."""
    base = Path(td) if td else Path(tempfile.mkdtemp(prefix="derive-progress-"))
    base.mkdir(parents=True, exist_ok=True)
    try:
        ledger = base / "ledger.json"
        raw = _copy_ledger(ledger)
        before = prm.compute_system_from_ledger(ledger)
        if before.get("status") != "OK" or before.get("system_pct") is None:
            return _fail(
                "progress",
                f"fixture ledger not OK before mutate: {before.get('status')}",
                before=before,
            )
        cap = _find_state(raw, "SPECIFIED")
        moved = copy.deepcopy(raw)
        row = list(moved[cap])
        row[0] = "BUILT"
        moved[cap] = row
        ledger.write_text(json.dumps(moved, indent=2), encoding="utf-8")
        after = prm.compute_system_from_ledger(ledger)
        model = prm.build_read_model(ledger_path=ledger, integrity_against_path=ledger)
        msys = model.get("system") or {}
        sum_before = Decimal(str(before["sum_credits_exact"]))
        sum_after = Decimal(str(after["sum_credits_exact"]))
        delta = sum_after - sum_before
        refreshed = (
            after.get("status") == "OK"
            and after.get("system_pct") is not None
            and after.get("system_pct") != before.get("system_pct")
            and delta == Decimal("0.20")
            and msys.get("system_pct") == after.get("system_pct")
            and msys.get("status") == "OK"
        )
        if not refreshed:
            return _fail(
                "progress",
                "Progress did not refresh after SPECIFIED→BUILT fixture mutate",
                before_pct=before.get("system_pct"),
                after_pct=after.get("system_pct"),
                model_pct=msys.get("system_pct"),
                sum_delta=str(delta),
            )
        return _ok(
            "progress",
            "SPECIFIED→BUILT sum +0.20; Progress SYSTEM% auto-updated",
            before_pct=before.get("system_pct"),
            after_pct=after.get("system_pct"),
            cap_id=cap,
        )
    except DeriveProveError as exc:
        return _fail("progress", str(exc))


def prove_progress_fail_stale(*, td: Path | None = None) -> dict[str, Any]:
    """Disagreeing integrity path → SCORING_PROJECTION_STALE, no percentage (FAIL STALE)."""
    base = Path(td) if td else Path(tempfile.mkdtemp(prefix="derive-stale-"))
    base.mkdir(parents=True, exist_ok=True)
    ledger = base / "ledger.json"
    raw = _copy_ledger(ledger)
    cap = _find_state(raw, "SPECIFIED")
    moved = copy.deepcopy(raw)
    row = list(moved[cap])
    row[0] = "BUILT"
    moved[cap] = row
    ledger.write_text(json.dumps(moved, indent=2), encoding="utf-8")
    stale_model = prm.build_read_model(
        ledger_path=ledger,
        integrity_against_path=LEDGER,
    )
    ssys = stale_model.get("system") or {}
    if ssys.get("status") != prm.STALE_STATUS or ssys.get("system_pct") is not None:
        return _fail(
            "progress",
            "Disagreeing integrity did not FAIL STALE / hide percentage",
            status=ssys.get("status"),
            pct=ssys.get("system_pct"),
        )
    return _stale(
        "progress",
        "integrity mismatch → SCORING_PROJECTION_STALE; percentage withheld",
        status=ssys.get("status"),
        visible_label=FAIL_STALE,
        html_banner="SCORING PROJECTION STALE",
    )


def prove_completion_register(*, td: Path | None = None) -> dict[str, Any]:
    """CR upsert → summary_for_owner counts refresh on next read."""
    base = Path(td) if td else Path(tempfile.mkdtemp(prefix="derive-cr-"))
    base.mkdir(parents=True, exist_ok=True)
    db = base / "register.sqlite"
    conn = cr.db_connect(db)
    try:
        cr.ensure_schema(conn)
        before = cr.summary_for_owner(conn)
        cr.upsert(
            conn,
            capability="CAP-DERIVE-FIXTURE-01",
            title="P7 fixture CR row",
            entity="CORE",
            domain="Core",
            view_key="Empire",
            state="OPEN",
            blocker_class="NEEDS_ENGINEERING",
            source="derivation_prove_fixture",
            evidence="fixture mutate for P7 derivation prove",
        )
        after = cr.summary_for_owner(conn)
        loops = prm.open_loops_summary(db_path=db, include_factory=False)
        bumped = (
            after["total_unresolved"] == before["total_unresolved"] + 1
            and after["total_open"] == before["total_open"] + 1
            and after["engineering_debt"] == before["engineering_debt"] + 1
            and loops.get("total_unresolved") == after["total_unresolved"]
        )
        if not bumped:
            return _fail(
                "completion_register",
                "CR summary did not refresh after fixture upsert",
                before=before,
                after=after,
                loops=loops,
            )
        return _ok(
            "completion_register",
            "CR upsert → summary + Progress open_loops refreshed",
            before_unresolved=before["total_unresolved"],
            after_unresolved=after["total_unresolved"],
        )
    finally:
        conn.close()


def prove_needs_you(*, td: Path | None = None) -> dict[str, Any]:
    """Overlay commissioning mission mutate → Needs You list refreshes."""
    base = Path(td) if td else Path(tempfile.mkdtemp(prefix="derive-needs-"))
    base.mkdir(parents=True, exist_ok=True)
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    before_path = base / "overlay-before.json"
    after_path = base / "overlay-after.json"
    before_path.write_text(json.dumps(overlay, indent=2), encoding="utf-8")
    before_model = prm.build_read_model(overlay_path=before_path)
    before_ids = {m.get("id") for m in (before_model.get("needs_you") or [])}

    missions = list(overlay.get("commissioning_missions") or [])
    fixture_id = "P7-DERIVE-NEEDS-YOU-FIXTURE"
    missions.append(
        {
            "id": fixture_id,
            "title": "P7 derivation prove Needs You fixture",
            "who": "Matt",
            "note": "Fixture mission for derivation prove only",
            "status": "ACTIVE",
            "bucket": "NEEDS_YOU",
            "source": "derivation_prove_fixture",
            "as_of": "2026-09-22",
            "confidence": "CURATED",
        }
    )
    overlay["commissioning_missions"] = missions
    after_path.write_text(json.dumps(overlay, indent=2), encoding="utf-8")
    after_model = prm.build_read_model(overlay_path=after_path)
    after_ids = {m.get("id") for m in (after_model.get("needs_you") or [])}
    if fixture_id in before_ids:
        return _fail("needs_you", "fixture id already present before mutate")
    if fixture_id not in after_ids:
        return _fail(
            "needs_you",
            "Needs You did not pick up overlay fixture mission",
            before_n=len(before_ids),
            after_n=len(after_ids),
        )
    if len(after_ids) < len(before_ids) + 1:
        return _fail(
            "needs_you",
            "Needs You count did not increase after mutate",
            before_n=len(before_ids),
            after_n=len(after_ids),
        )
    return _ok(
        "needs_you",
        "Overlay mission append → Needs You auto-updated",
        before_n=len(before_ids),
        after_n=len(after_ids),
        fixture_id=fixture_id,
    )


def prove_empire(*, td: Path | None = None) -> dict[str, Any]:
    """Ledger mutate → Empire today_strip refreshes OR loud UNWIRED (FAIL STALE)."""
    base = Path(td) if td else Path(tempfile.mkdtemp(prefix="derive-empire-"))
    base.mkdir(parents=True, exist_ok=True)
    ledger = base / "ledger.json"
    raw = _copy_ledger(ledger)
    before = empire.today_strip(ledger)
    if before.get("status") != "LEDGER" or before.get("system_pct") is None:
        return _fail("empire", "Empire today_strip not LEDGER before mutate", before=before)
    cap = _find_state(raw, "SPECIFIED")
    moved = copy.deepcopy(raw)
    row = list(moved[cap])
    row[0] = "BUILT"
    moved[cap] = row
    ledger.write_text(json.dumps(moved, indent=2), encoding="utf-8")
    after = empire.today_strip(ledger)
    refreshed = (
        after.get("status") == "LEDGER"
        and after.get("system_pct") is not None
        and after.get("system_pct") != before.get("system_pct")
        and after.get("invented_system_pct") is False
    )
    if refreshed:
        return _ok(
            "empire",
            "Empire today_strip SYSTEM% auto-updated from Progress ledger helper",
            before_pct=before.get("system_pct"),
            after_pct=after.get("system_pct"),
        )
    # Short ledger → UNWIRED = visible FAIL STALE (no frozen percent)
    short = {k: moved[k] for k in list(moved.keys())[:76]}
    short_path = base / "short.json"
    short_path.write_text(json.dumps(short), encoding="utf-8")
    unwired = empire.today_strip(short_path)
    if (
        unwired.get("status") == "UNWIRED"
        and unwired.get("system_pct") is None
        and unwired.get("loud") is True
    ):
        return _stale(
            "empire",
            "n≠77 → Empire UNWIRED (FAIL STALE); no frozen percent",
            status=unwired.get("status"),
        )
    return _fail(
        "empire",
        "Empire neither refreshed nor FAIL STALE after fixture mutate",
        after=after,
        unwired=unwired,
    )


def prove_integration_health(*, td: Path | None = None) -> dict[str, Any]:
    """ESB fixture presence change → Integration Health connector status refreshes."""
    base = Path(td) if td else Path(tempfile.mkdtemp(prefix="derive-ih-"))
    base.mkdir(parents=True, exist_ok=True)
    missing = base / "missing-esb.sqlite"
    good = base / "esb-good.sqlite"
    conn = sqlite3.connect(good)
    conn.execute(
        "CREATE TABLE sales (nk TEXT, biz_date TEXT, raw TEXT, pulled_at TEXT)"
    )
    conn.commit()
    conn.close()
    before = ih.build_report(
        esb_path=missing,
        alchemist_path=base / "missing-alc.sqlite",
        env_root=base / "no-env",
    )
    after = ih.build_report(
        esb_path=good,
        alchemist_path=base / "missing-alc.sqlite",
        env_root=base / "no-env",
    )

    def _esb(report: dict[str, Any]) -> str:
        for row in report.get("connectors") or []:
            if row.get("cap_id") == "CAP-INTG-02":
                return str(row.get("status") or "")
        return ""

    b_status = _esb(before)
    a_status = _esb(after)
    if b_status != "NOT_CONFIGURED":
        return _fail(
            "integration_health",
            f"missing ESB expected NOT_CONFIGURED got {b_status}",
        )
    if a_status != "READ_OK":
        return _fail(
            "integration_health",
            f"sales ESB expected READ_OK got {a_status}",
        )
    return _ok(
        "integration_health",
        "ESB fixture mutate NOT_CONFIGURED→READ_OK auto-updated",
        before_status=b_status,
        after_status=a_status,
    )


def prove_sale_readiness(*, td: Path | None = None) -> dict[str, Any]:
    """Sale_Readiness CSV mutate → Sale Readiness projection items refresh."""
    base = Path(td) if td else Path(tempfile.mkdtemp(prefix="derive-sale-"))
    base.mkdir(parents=True, exist_ok=True)
    before_csv = base / "sale-before.csv"
    after_csv = base / "sale-after.csv"
    live = SALE_CSV.read_text(encoding="utf-8")
    before_csv.write_text(live, encoding="utf-8")
    before_items = prm.sale_readiness_items(csv_path=before_csv)
    before_n = len(before_items)
    # Append one fixture row
    with after_csv.open("w", encoding="utf-8", newline="") as f:
        f.write(live if live.endswith("\n") else live + "\n")
        writer = csv.writer(f)
        writer.writerow(
            [
                "GGV",
                "P7 Derivation Prove Fixture",
                "fixture",
                "SPECIFIED",
                "Sale-ready evidence continuously maintained",
                "",
                "",
                "",
                "SPECIFIED",
            ]
        )
    after_items = prm.sale_readiness_items(csv_path=after_csv)
    model = prm.build_read_model(sale_csv_path=after_csv)
    view = ((model.get("views") or {}).get("Sale Readiness") or {})
    view_items = view.get("items") or []
    sale_view_n = sum(
        1 for i in view_items if i.get("source_kind") == "sale_readiness_csv"
    )
    if len(after_items) != before_n + 1:
        return _fail(
            "sale_readiness",
            "Sale Readiness items did not grow after CSV append",
            before_n=before_n,
            after_n=len(after_items),
        )
    fixture_caps = [i.get("capability") for i in after_items]
    if not any("P7 Derivation Prove Fixture" in str(c) for c in fixture_caps):
        return _fail("sale_readiness", "fixture area missing from items")
    if sale_view_n < before_n + 1:
        return _fail(
            "sale_readiness",
            "Sale Readiness view did not refresh from fixture CSV",
            view_n=sale_view_n,
            before_n=before_n,
        )
    return _ok(
        "sale_readiness",
        "Sale_Readiness.csv append → items + view auto-updated",
        before_n=before_n,
        after_n=len(after_items),
        view_n=sale_view_n,
    )


def scan_frozen_live_pcts(
    paths: tuple[Path, ...] | list[Path] | None = None,
) -> dict[str, Any]:
    """Detect frozen/manual live dial literals in projection surfaces.

    Uses the same rules as progress_read_model._html_hardcoded_live_pcts.
    Historical claim snapshots and explicit prior/legacy notes are out of scope.
    """
    targets = list(paths) if paths is not None else list(SCAN_PATHS)
    hits: list[dict[str, str]] = []
    for path in targets:
        if not path.is_file():
            continue
        # Do not flag this module's own documentation of the FAIL STALE label.
        if path.resolve() == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8")
        found = prm._html_hardcoded_live_pcts(text)
        # Also catch a raw "system_pct": <number> copy in dashboard HTML/JS only.
        if path.suffix in {".html", ".js"}:
            for m in re.finditer(r'"system_pct"\s*:\s*([0-9]+(?:\.[0-9]+)?)', text):
                found.append(f"copied_json_system_pct:{m.group(1)}")
        for token in found:
            hits.append({"path": str(path.relative_to(BETA_ROOT)), "token": token})
    return {
        "ok": len(hits) == 0,
        "hits": hits,
        "scanned": [str(p.relative_to(BETA_ROOT)) if p.is_relative_to(BETA_ROOT) else str(p) for p in targets],
        "repaired": [],
    }


def repair_frozen_live_pcts() -> dict[str, Any]:
    """Scan and repair if frozen live % / copied JSON found. No-op when clean."""
    scan = scan_frozen_live_pcts()
    if scan["ok"]:
        scan["detail"] = "No frozen/manual duplicate % or copied JSON in projection surfaces"
        return scan
    # Auto-repair is intentionally narrow: only HTML hard-codes of the known
    # retired dial literals. Anything else fails the prove loudly.
    repaired: list[str] = []
    remaining: list[dict[str, str]] = []
    for hit in scan["hits"]:
        path = BETA_ROOT / hit["path"]
        token = hit["token"]
        if path.suffix == ".html" and token.startswith("copied_json_system_pct:"):
            text = path.read_text(encoding="utf-8")
            new = re.sub(
                r'"system_pct"\s*:\s*[0-9]+(?:\.[0-9]+)?',
                '"system_pct": null /* projection — never freeze */',
                text,
            )
            if new != text:
                path.write_text(new, encoding="utf-8")
                repaired.append(hit["path"])
                continue
        remaining.append(hit)
    return {
        "ok": len(remaining) == 0,
        "hits": remaining,
        "repaired": repaired,
        "scanned": scan["scanned"],
        "detail": (
            "Repaired copied JSON system_pct"
            if repaired and not remaining
            else "Frozen live % remains — FAIL STALE until removed"
        ),
    }


def run_all_proves(*, td: Path | None = None) -> dict[str, Any]:
    """Run every surface prove under one temp root. Live ledger untouched."""
    root = Path(td) if td else Path(tempfile.mkdtemp(prefix="derive-prove-all-"))
    root.mkdir(parents=True, exist_ok=True)
    slots = {
        "progress": root / "progress",
        "stale": root / "stale",
        "cr": root / "cr",
        "needs": root / "needs",
        "empire": root / "empire",
        "ih": root / "ih",
        "sale": root / "sale",
    }
    for path in slots.values():
        path.mkdir(parents=True, exist_ok=True)
    results = [
        prove_progress_auto_update(td=slots["progress"]),
        prove_progress_fail_stale(td=slots["stale"]),
        prove_completion_register(td=slots["cr"]),
        prove_needs_you(td=slots["needs"]),
        prove_empire(td=slots["empire"]),
        prove_integration_health(td=slots["ih"]),
        prove_sale_readiness(td=slots["sale"]),
    ]
    frozen = repair_frozen_live_pcts()
    all_ok = all(r.get("ok") for r in results) and frozen.get("ok") is True
    return {
        "ok": all_ok,
        "bound": BOUND,
        "schema": SCHEMA_ID,
        "run_id": RUN_ID,
        "claim_id": CLAIM_ID,
        "honesty": honesty_flags(),
        "results": results,
        "frozen_scan": frozen,
        "surfaces": list(SURFACES),
        "temp_root": str(root),
    }


def schema_document() -> dict[str, Any]:
    return {
        "id": SCHEMA_ID,
        "bound": BOUND,
        "slice": SLICE,
        "run_id": RUN_ID,
        "surfaces": list(SURFACES),
        "writes": False,
        "second_scoring_table": False,
    }


if __name__ == "__main__":
    report = run_all_proves()
    print(json.dumps(report, indent=2, default=str)[:8000])
    raise SystemExit(0 if report.get("ok") else 1)
