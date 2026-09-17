#!/usr/bin/env python3
"""Matt Progress Dashboard v2 — Owner Cockpit read-model (Beta, Owner-only).

BUILT ≠ HUMAN_COMMISSIONED ≠ LIVE.
Factory health is SYSTEM STATUS — excluded from mission weighted %.
progress_type: PARTIAL_ESTIMATE while Master_Build CSV + overlay mix exists.
No ESB / Metricool / Production / Habitat mutations.
"""
from __future__ import annotations

import csv
import json
import socket
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
BUILD_DASH = BETA_ROOT / "docs" / "canon" / "build-dashboard"
OVERLAY_PATH = BETA_ROOT / "state" / "progress" / "v1_overlay.json"
FACTORY_RUNS = BETA_ROOT / "state" / "build-factory" / "runs"
TZ8 = timezone(timedelta(hours=8))

PERS_MATT = "PERS-MATT"

# Mission domain weights — Factory health REMOVED. Prior ratios ÷ 0.95, labelled ESTIMATED.
# Prior (with Factory 5%): Core 25 / GGV 20 / BZG 15 / AMG 15 / Intel 10 / Integ 5 / Sale 5 / Factory 5
DOMAIN_WEIGHTS: dict[str, float] = {
    "Core": 0.2632,
    "GGV": 0.2105,
    "BZG": 0.1579,
    "AMG": 0.1579,
    "Intelligence": 0.1053,
    "Integrations": 0.0526,
    "Sale Readiness": 0.0526,
}

PRIOR_MISSION_PCT_WITH_FACTORY = 27  # v1 computed overall before factory exclusion

LIFECYCLE_SCORES: dict[str, float] = {
    "IDEA": 0.05,
    "NOT TARGET": 0.0,
    "NOT_TARGET": 0.0,
    "SPECIFIED": 0.05,
    "APPROVED": 0.15,
    "BUILDING": 0.35,
    "SCHEMA_BUILT": 0.55,
    "BETA": 0.55,
    "TESTED": 0.55,
    "PILOT": 0.70,
    "VERIFIED": 0.85,
    "LIVE": 1.0,
    "RETIRED": 0.0,
    "WRITE_LOCKED": 0.55,
    "READ_ONLY": 0.55,
    "PARTIAL": 0.35,
    "BUILT": 0.55,
    "NOT_DONE": 0.0,
    "DONE": 1.0,
}

COMMISSIONING_CAP = 0.65  # BUILT/TESTED without HUMAN_COMMISSIONING=DONE

VIEWS = (
    "Empire",
    "Wolf Core",
    "GGV",
    "AMG",
    "BZG",
    "Intelligence",
    "Integrations",
    "Sale Readiness",
    "Build Factory",
    "Backlog",
)

DOMAIN_ALIASES: dict[str, str] = {
    "wolf core": "Core",
    "core": "Core",
    "ggv": "GGV",
    "bzg": "BZG",
    "amg": "AMG",
    "wolf intelligence": "Intelligence",
    "intelligence": "Intelligence",
    "finance": "Core",
    "people": "Core",
    "operations": "Core",
    "executive": "Core",
    "system": "Core",
    "sale readiness": "Sale Readiness",
    "integrations": "Integrations",
    "factory health": "Factory health",
    "build factory": "Factory health",
}

# Owner-facing Habitat stages (technical ids stay in technical_details)
HABITAT_OWNER_STAGE_MAP = [
    ("PLAN", "PLAN"),
    ("WORK", "WORK"),
    ("EVIDENCE", "PROOF"),
    ("APPROVAL", "APPROVAL"),
    ("PUBLISH_GATE", "PUBLISH READY"),
    ("METRICOOL", "PUBLISH"),
    ("PERFORMANCE", "LEARN"),
]

# Owner-facing Uma stages (collapsed from 7 technical)
UMA_OWNER_STAGE_MAP = [
    (("ESB", "SNAPSHOT"), "ESB DATA"),
    (("CASH",), "CASH COUNT"),
    (("RECONCILE",), "CHECK"),
    (("EXCEPTION",), "EXCEPTION"),
    (("RESOLUTION",), "FIX"),
    (("VERIFIED",), "VERIFIED CLOSE"),
]

WEIGHT_PCT_DISPLAY = {
    "Core": 26,
    "GGV": 21,
    "BZG": 16,
    "AMG": 16,
    "Intelligence": 11,
    "Integrations": 5,
    "Sale Readiness": 5,
}


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def _norm_domain(raw: str) -> str:
    key = (raw or "").strip()
    if not key:
        return "Core"
    aliased = DOMAIN_ALIASES.get(key.lower())
    if aliased:
        return aliased
    for name in DOMAIN_WEIGHTS:
        if name.lower() == key.lower():
            return name
    return key


def _norm_lifecycle(raw: str) -> str:
    s = (raw or "").strip().upper().replace("-", "_")
    s = s.replace(" ", "_")
    if s in LIFECYCLE_SCORES:
        return s
    aliases = {
        "SCHEMA_BUILT": "SCHEMA_BUILT",
        "NOT_YET": "SPECIFIED",
        "NOTTARGET": "NOT_TARGET",
        "HUMAN_APPROVED": "APPROVED",
    }
    return aliases.get(s, s if s else "SPECIFIED")


def load_overlay(path: Path | None = None) -> dict[str, Any]:
    p = path or OVERLAY_PATH
    if not p.is_file():
        return {
            "version": "v1",
            "progress_type": "PARTIAL_ESTIMATE",
            "master_build_csv_staleness": "KNOWN",
            "overlay_required": True,
            "rows": [],
            "verticals": {},
            "achievements": [],
            "prior_estimate_pct": 32,
            "owner_cockpit": {},
        }
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("overlay must be a JSON object")
    return data


def _read_csv(name: str) -> list[dict[str, str]]:
    path = BUILD_DASH / name
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_master_build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for r in _read_csv("Master_Build.csv"):
        mid = (r.get("ID") or "").strip()
        if not mid:
            continue
        domain = _norm_domain(r.get("Domain") or "")
        lifecycle = _norm_lifecycle(r.get("Status") or "SPECIFIED")
        rows.append(
            {
                "id": mid,
                "source_kind": "master_build_csv",
                "capability": (r.get("Capability / Module") or "").strip(),
                "domain": domain,
                "priority": (r.get("Priority") or "").strip(),
                "lifecycle": lifecycle,
                "owner": (r.get("Owner") or "").strip(),
                "next_action": (r.get("Next action") or "").strip(),
                "blocker": (r.get("Blocker / Risk") or "").strip(),
                "acceptance": (r.get("Acceptance / Live gate") or "").strip(),
                "why": (r.get("Why it matters") or "").strip(),
                "human_commissioning": "NOT_DONE",
                "built": lifecycle
                in ("SCHEMA_BUILT", "BETA", "TESTED", "PILOT", "VERIFIED", "LIVE", "BUILDING"),
                "commissioned": False,
                "live": lifecycle == "LIVE",
                "confidence": "DERIVED",
                "as_of": None,
                "source": "docs/canon/build-dashboard/Master_Build.csv",
            }
        )
    return rows


def load_commissioning_done_map() -> dict[str, bool]:
    out: dict[str, bool] = {}
    for r in _read_csv("Commissioning.csv"):
        name = (r.get("Capability / Release") or "").strip()
        if not name:
            continue
        live = (r.get("LIVE?") or "").strip().upper()
        out[name.lower()] = live in ("YES", "Y", "TRUE", "DONE")
    return out


def merge_overlay(
    master: list[dict[str, Any]], overlay: dict[str, Any]
) -> list[dict[str, Any]]:
    by_id = {r["id"]: dict(r) for r in master}
    extras: list[dict[str, Any]] = []
    for ov in overlay.get("rows") or []:
        if not isinstance(ov, dict):
            continue
        mid = (ov.get("master_build_id") or "").strip()
        lifecycle = _norm_lifecycle(ov.get("lifecycle") or "SPECIFIED")
        hc = (ov.get("human_commissioning") or "NOT_DONE").strip().upper()
        commissioned = hc == "DONE" or bool(ov.get("commissioned"))
        live = bool(ov.get("live")) and lifecycle == "LIVE"
        item = {
            "id": ov.get("id") or f"OV-{mid or 'X'}",
            "source_kind": "overlay",
            "master_build_id": mid or None,
            "capability": ov.get("capability") or "",
            "domain": _norm_domain(ov.get("domain") or "Core"),
            "lifecycle": lifecycle,
            "human_commissioning": hc,
            "built": bool(
                ov.get(
                    "built",
                    lifecycle
                    in ("SCHEMA_BUILT", "BETA", "TESTED", "PILOT", "VERIFIED", "LIVE"),
                )
            ),
            "commissioned": commissioned,
            "live": live,
            "confidence": ov.get("confidence") or "CURATED",
            "as_of": ov.get("as_of"),
            "source": ov.get("source") or str(OVERLAY_PATH),
            "waiting_class": ov.get("waiting_class"),
            "priority": ov.get("priority") or "",
            "next_action": ov.get("next_action") or "",
            "blocker": ov.get("blocker") or "",
        }
        if mid and mid in by_id:
            base = by_id[mid]
            base["overlay_applied"] = True
            base["overlay_note"] = f"Stale CSV vs overlay {item['id']} ({lifecycle})"
            if LIFECYCLE_SCORES.get(lifecycle, 0) > LIFECYCLE_SCORES.get(
                base.get("lifecycle") or "", 0
            ):
                base["lifecycle_csv"] = base.get("lifecycle")
        extras.append(item)
    return list(by_id.values()) + extras


def maturity_score(
    lifecycle: str,
    *,
    human_commissioning: str = "NOT_DONE",
    live: bool = False,
) -> float:
    lc = _norm_lifecycle(lifecycle)
    if lc == "RETIRED" or lc == "NOT_TARGET":
        return 0.0
    raw = LIFECYCLE_SCORES.get(lc, 0.05)
    if live and lc == "LIVE" and human_commissioning == "DONE":
        return 1.0
    builtish = lc in (
        "SCHEMA_BUILT",
        "BETA",
        "TESTED",
        "PILOT",
        "VERIFIED",
        "LIVE",
        "BUILDING",
        "BUILT",
        "WRITE_LOCKED",
        "READ_ONLY",
    )
    if builtish and human_commissioning != "DONE":
        return min(raw, COMMISSIONING_CAP)
    return raw


def score_items(items: list[dict[str, Any]]) -> float:
    if not items:
        return 0.0
    scores = [
        maturity_score(
            i.get("lifecycle") or "SPECIFIED",
            human_commissioning=str(i.get("human_commissioning") or "NOT_DONE").upper(),
            live=bool(i.get("live")),
        )
        for i in items
        if _norm_lifecycle(i.get("lifecycle") or "") not in ("RETIRED", "NOT_TARGET")
    ]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def integrations_items() -> list[dict[str, Any]]:
    items = []
    for r in _read_csv("Integrations.csv"):
        iid = (r.get("Integration ID") or "").strip()
        if not iid:
            continue
        lifecycle = _norm_lifecycle(r.get("Status") or "SPECIFIED")
        items.append(
            {
                "id": iid,
                "source_kind": "integrations_csv",
                "capability": f"{r.get('Source')} → {r.get('Target')}: {r.get('Purpose')}",
                "domain": "Integrations",
                "lifecycle": lifecycle,
                "human_commissioning": "NOT_DONE",
                "built": lifecycle
                in ("SCHEMA_BUILT", "BETA", "TESTED", "PILOT", "VERIFIED", "LIVE"),
                "commissioned": False,
                "live": lifecycle == "LIVE",
                "confidence": "DERIVED",
                "source": "docs/canon/build-dashboard/Integrations.csv",
                "criticality": (r.get("Criticality") or "").strip(),
            }
        )
    return items


def sale_readiness_items() -> list[dict[str, Any]]:
    items = []
    for i, r in enumerate(_read_csv("Sale_Readiness.csv")):
        entity = (r.get("Entity") or "").strip()
        area = (r.get("Area") or "").strip()
        if not entity and not area:
            continue
        lifecycle = _norm_lifecycle(r.get("Status") or "SPECIFIED")
        items.append(
            {
                "id": f"SR-{entity}-{i}",
                "source_kind": "sale_readiness_csv",
                "capability": f"{entity}: {area}",
                "domain": "Sale Readiness",
                "lifecycle": lifecycle,
                "human_commissioning": "NOT_DONE",
                "built": False,
                "commissioned": False,
                "live": False,
                "confidence": "DERIVED",
                "source": "docs/canon/build-dashboard/Sale_Readiness.csv",
                "target_profit_note": "TARGET ≠ ACTUAL — ACTUAL NOT YET TRUSTWORTHY",
            }
        )
    return items


def factory_health_items() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not FACTORY_RUNS.is_dir():
        return items
    for path in sorted(FACTORY_RUNS.glob("BF-*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        stage = (data.get("stage") or "UNKNOWN").strip()
        if stage in ("DONE", "SHIPPED", "COMPLETE", "VERIFIED"):
            lifecycle = "TESTED"
        elif stage in ("WAITING_CURSOR", "WAITING_GROK", "ACTIVE", "BUILDING"):
            lifecycle = "BUILDING"
        else:
            lifecycle = "SPECIFIED"
        items.append(
            {
                "id": data.get("run_id") or path.stem,
                "source_kind": "build_factory_run",
                "capability": data.get("slice") or path.stem,
                "domain": "Factory health",
                "lifecycle": lifecycle,
                "human_commissioning": "NOT_DONE",
                "built": lifecycle in ("TESTED", "BETA", "BUILDING"),
                "commissioned": False,
                "live": False,
                "confidence": "DERIVED",
                "source": str(path.relative_to(BETA_ROOT)),
                "stage": stage,
                "as_of": data.get("updated_at"),
            }
        )
    return items


def backlog_items() -> list[dict[str, Any]]:
    items = []
    for i, r in enumerate(_read_csv("Not_Yet.csv")):
        idea = (r.get("Idea") or "").strip()
        if not idea:
            continue
        items.append(
            {
                "id": f"NY-{i}",
                "source_kind": "not_yet_csv",
                "capability": idea,
                "domain": "Backlog",
                "lifecycle": "NOT_TARGET",
                "human_commissioning": "NOT_DONE",
                "built": False,
                "commissioned": False,
                "live": False,
                "confidence": "DERIVED",
                "source": "docs/canon/build-dashboard/Not_Yet.csv",
                "reason": (r.get("Reason not now") or "").strip(),
                "reconsider": (r.get("Reconsideration trigger") or "").strip(),
                "waiting_class": "UNAPPROVED_POLICY",
            }
        )
    return items


def _port_up(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_ok(url: str, timeout: float = 3.0) -> bool:
    try:
        req = urllib.request.Request(url, method="GET", headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= int(resp.status) < 400
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return False


def assess_factory_health(
    factory_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Deterministic system health — NOT mission maturity.

    Checks: ACTIVE factory clean · deployed UI routes reachable · Beta :8788 up · Production untouched.
    """
    items = factory_items if factory_items is not None else factory_health_items()
    checks: dict[str, dict[str, Any]] = {}

    # ACTIVE factory clean — no FAILED/FAILING; ACTIVE with heavy fix_attempts → degraded signal
    failing_runs = [
        i
        for i in items
        if str(i.get("stage") or "").upper() in ("FAILED", "FAILING", "ABORT", "ABORTED")
    ]
    active_messy = []
    if FACTORY_RUNS.is_dir():
        for path in FACTORY_RUNS.glob("BF-*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            stage = str(data.get("stage") or "").upper()
            if stage == "ACTIVE" and int(data.get("fix_attempts") or 0) > 3:
                active_messy.append(data.get("run_id") or path.stem)
    if failing_runs:
        checks["active_factory_clean"] = {
            "result": "FAIL",
            "detail": f"{len(failing_runs)} failing run(s)",
        }
    elif active_messy:
        checks["active_factory_clean"] = {
            "result": "DEGRADED",
            "detail": f"ACTIVE with fix_attempts>3: {', '.join(active_messy[:3])}",
        }
    else:
        checks["active_factory_clean"] = {
            "result": "PASS",
            "detail": "No FAILED/FAILING factory runs",
        }

    beta_up = _port_up("127.0.0.1", 8788)
    checks["beta_8788"] = {
        "result": "PASS" if beta_up else "FAIL",
        "detail": "Beta :8788 listening" if beta_up else "Beta :8788 not listening",
    }

    # Soft prove of deployed UI routes (same intent as prove_deployed_ui_routes)
    if beta_up:
        progress_ok = _http_ok("http://127.0.0.1:8788/progress")
        checks["prove_deployed_ui_routes"] = {
            "result": "PASS" if progress_ok else "FAIL",
            "detail": "GET /progress 200-class" if progress_ok else "GET /progress failed",
        }
    else:
        checks["prove_deployed_ui_routes"] = {
            "result": "FAIL",
            "detail": "Skipped — Beta down",
        }

    # Production untouched — invariant of this surface (read-model never writes :8787 / serve.py)
    checks["production_untouched"] = {
        "result": "PASS",
        "detail": "Progress surface is Beta-only; Production not written by this read-model",
    }

    results = [c["result"] for c in checks.values()]
    if any(r == "FAIL" for r in results):
        status = "FAILING"
    elif any(r == "DEGRADED" for r in results):
        status = "DEGRADED"
    else:
        status = "HEALTHY"

    return {
        "status": status,
        "checks": checks,
        "note": "Factory health is system status, not mission maturity. Excluded from weighted %.",
        "excluded_from_mission_pct": True,
        "production": "UNTOUCHED",
    }


def _plain_phase_for_pct(pct: int, domain: str) -> str:
    if domain == "Core":
        if pct < 15:
            return "Core foundations just starting"
        if pct < 40:
            return "Tracked Core capabilities mid-build — not yet commissioned"
        if pct < 70:
            return "Core slices largely built — awaiting human commission"
        return "Core mature on tracked set — commission & live still required"
    if pct < 10:
        return "Mostly not started"
    if pct < 35:
        return "Early build"
    if pct < 60:
        return "Built on Beta — not live"
    if pct < 85:
        return "Advanced build — human commission / live gaps remain"
    return "Near-complete on tracked items"


def _biggest_gap(items: list[dict[str, Any]], domain: str) -> str:
    waiting_policy = [
        i for i in items if i.get("waiting_class") == "UNAPPROVED_POLICY"
    ]
    waiting_human = [i for i in items if i.get("waiting_class") == "WAITING_HUMAN"]
    not_built = [i for i in items if not i.get("built") and not i.get("live")]
    if domain == "Sale Readiness":
        return "TARGET profit figures — ACTUAL NOT YET TRUSTWORTHY"
    if domain == "AMG":
        return "AMG capabilities still early / not started on tracked set"
    if waiting_policy:
        cap = waiting_policy[0].get("capability") or "policy item"
        return f"Policy needed: {cap}"
    if waiting_human:
        cap = waiting_human[0].get("capability") or "capability"
        return f"Waiting on people: {cap} (BUILT ≠ COMMISSIONED)"
    if not_built:
        cap = not_built[0].get("capability") or "capability"
        return f"Not yet built: {cap}"
    built_not_live = [i for i in items if i.get("built") and not i.get("live")]
    if built_not_live:
        return "Human commissioning still NOT DONE — BUILT ≠ LIVE"
    return "No dominant gap on tracked items"


def domain_scorecard(
    items: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_domain: dict[str, list[dict[str, Any]]] = {d: [] for d in DOMAIN_WEIGHTS}
    for it in items:
        d = _norm_domain(it.get("domain") or "")
        if d == "Factory health":
            continue  # never weight into mission domains
        if d not in by_domain:
            by_domain.setdefault("Core", []).append(it)
            continue
        by_domain[d].append(it)

    card: dict[str, dict[str, Any]] = {}
    for domain, weight in DOMAIN_WEIGHTS.items():
        group = by_domain.get(domain) or []
        score = score_items(group)
        pct = int(round(score * 100))
        card[domain] = {
            "domain": domain,
            "weight": weight,
            "weight_label": "ESTIMATED",
            "weight_pct_display": WEIGHT_PCT_DISPLAY.get(domain),
            "score": round(score, 4),
            "pct": pct,
            "visual_pct": pct,
            "item_count": len(group),
            "plain_phase": _plain_phase_for_pct(pct, domain),
            "biggest_gap": _biggest_gap(group, domain),
            "denominator_note": (
                "Core % = maturity of tracked approved Core capabilities in Master_Build+overlay "
                "(item_count denominator) — NOT all imaginable Wolf Core forever."
                if domain == "Core"
                else None
            ),
            "items": group,
        }
    return card


def overall_from_card(card: dict[str, dict[str, Any]]) -> dict[str, Any]:
    total_w = sum(DOMAIN_WEIGHTS.values())
    weighted = sum(
        card[d]["score"] * DOMAIN_WEIGHTS[d] for d in DOMAIN_WEIGHTS if d in card
    )
    overall = weighted / total_w if total_w else 0.0
    pct = int(round(overall * 100))
    return {
        "overall_score": round(overall, 4),
        "overall_pct": pct,
        "label": "PARTIAL ESTIMATE",
        "progress_type": "PARTIAL_ESTIMATE",
        "prior_mission_pct_with_factory": PRIOR_MISSION_PCT_WITH_FACTORY,
        "factory_excluded_note": (
            f"Factory health removed from mission %. Prior {PRIOR_MISSION_PCT_WITH_FACTORY}% "
            f"(with Factory weight) → {pct}% after re-normalization. "
            "Factory is system health (HEALTHY/DEGRADED/FAILING), not mission maturity."
        ),
    }


def reconcile_prior(overall_pct: int, overlay: dict[str, Any]) -> dict[str, Any] | None:
    prior = overlay.get("prior_estimate_pct")
    if prior is None:
        return None
    try:
        prior_i = int(prior)
    except (TypeError, ValueError):
        return None
    delta = overall_pct - prior_i
    # Always surface factory-split why when prior is the v1-with-factory figure
    factory_note = overlay.get("prior_estimate_note") or (
        "Factory health removed from mission weight; domains re-normalized."
    )
    if abs(delta) <= 8:
        return {
            "prior_pct": prior_i,
            "computed_pct": overall_pct,
            "delta": delta,
            "show_why": True,
            "why": factory_note,
        }
    return {
        "prior_pct": prior_i,
        "computed_pct": overall_pct,
        "delta": delta,
        "show_why": True,
        "why": factory_note,
    }


def waiting_class_for(item: dict[str, Any]) -> str | None:
    if item.get("waiting_class"):
        return item["waiting_class"]
    lc = _norm_lifecycle(item.get("lifecycle") or "")
    if item.get("live"):
        return None
    if lc in ("SPECIFIED", "APPROVED", "IDEA"):
        return "UNAPPROVED_POLICY"
    if lc in ("BUILDING", "SCHEMA_BUILT", "BETA", "TESTED"):
        if item.get("human_commissioning") != "DONE":
            return "WAITING_HUMAN"
        return "BLOCKED_SYSTEM"
    return None


VIEW_DOMAIN: dict[str, str | None] = {
    "Empire": None,
    "Wolf Core": "Core",
    "GGV": "GGV",
    "AMG": "AMG",
    "BZG": "BZG",
    "Intelligence": "Intelligence",
    "Integrations": "Integrations",
    "Sale Readiness": "Sale Readiness",
    "Build Factory": "Factory health",
    "Backlog": "Backlog",
}


def calculation_english() -> dict[str, Any]:
    weight_line = (
        "Domain weights (CURATED, labelled ESTIMATED; Factory health EXCLUDED): "
        "Core ~26%, GGV ~21%, BZG ~16%, AMG ~16%, Intelligence ~11%, "
        "Integrations ~5%, Sale Readiness ~5% (prior ratios ÷0.95 after removing Factory 5%)."
    )
    return {
        "title": "How is this calculated?",
        "progress_type": "PARTIAL_ESTIMATE",
        "steps": [
            weight_line,
            "Factory health is separate system status ∈ {HEALTHY, DEGRADED, FAILING} — not mission maturity.",
            "Core % = maturity of tracked approved Core capabilities in Master_Build+overlay "
            "(item_count denominator) — NOT all imaginable Wolf Core forever.",
            "Per-capability maturity from lifecycle (not file count): IDEA/SPECIFIED=0.05 · APPROVED=0.15 · "
            "BUILDING=0.35 · BETA/SCHEMA_BUILT/TESTED=0.55 · PILOT=0.7 · VERIFIED=0.85 · LIVE=1.0 · RETIRED=n/a.",
            "Commissioning penalty: if BUILT/TESTED but HUMAN_COMMISSIONING ≠ DONE → score capped at 0.65 (BUILT ≠ LIVE).",
            "Overall = weighted average of mission domain scores (no Factory). Shown as integer % + label "
            "PARTIAL ESTIMATE while Master_Build CSV + overlay mix exists.",
            f"Prior mission % with Factory weight was ~{PRIOR_MISSION_PCT_WITH_FACTORY}%; "
            "recompute excludes Factory and re-normalizes — do not inflate to look good.",
        ],
        "honesty": {
            "progress_type": "PARTIAL_ESTIMATE",
            "master_build_csv_staleness": "KNOWN",
            "overlay_required": True,
            "no_fake_precision": True,
            "peaches_recommendation_is_not_approved": True,
            "factory_excluded_from_mission_pct": True,
        },
        "distinctions": [
            "BUILT ≠ HUMAN_COMMISSIONED ≠ LIVE",
            "WAITING_HUMAN ≠ BLOCKED_SYSTEM ≠ UNAPPROVED_POLICY ≠ INACCESSIBLE_SOURCE",
            "TARGET profit ≠ ACTUAL (ACTUAL NOT YET TRUSTWORTHY)",
            "ESTIMATED labelled",
            "Factory HEALTHY ≠ mission complete",
        ],
    }


def _owner_habitat_stages(habitat: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {s.get("id"): s for s in (habitat.get("stages") or []) if isinstance(s, dict)}
    out = []
    for tech_id, owner_label in HABITAT_OWNER_STAGE_MAP:
        src = by_id.get(tech_id) or {}
        out.append(
            {
                "label": owner_label,
                "state": src.get("state") or "UNKNOWN",
                "note": src.get("note") or "",
            }
        )
    return out


def _owner_uma_stages(uma: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {s.get("id"): s for s in (uma.get("stages") or []) if isinstance(s, dict)}
    out = []
    for tech_ids, owner_label in UMA_OWNER_STAGE_MAP:
        states = [by_id.get(t, {}) for t in tech_ids]
        # Prefer most advanced non-empty state among collapsed set
        state = "UNKNOWN"
        note = ""
        for s in states:
            if s.get("state"):
                state = s["state"]
                note = s.get("note") or note
        out.append({"label": owner_label, "state": state, "note": note})
    return out


def _derive_owner_phase(
    card: dict[str, dict[str, Any]],
    overall_pct: int,
    verticals: dict[str, Any],
) -> str:
    core_pct = (card.get("Core") or {}).get("pct") or 0
    ggv_pct = (card.get("GGV") or {}).get("pct") or 0
    bzg_pct = (card.get("BZG") or {}).get("pct") or 0
    hab = verticals.get("habitat") or {}
    uma = verticals.get("uma_close") or {}
    met_locked = (hab.get("distinctions") or {}).get("METRICOL_WRITE") == "LOCKED"
    waiting_closer = uma.get("waiting") == "WAITING_FOR_CLOSER"

    if overall_pct < 15:
        return "Foundations — early tracked build across the empire"
    if core_pct >= 30 and (ggv_pct >= 40 or bzg_pct >= 25):
        bits = []
        if waiting_closer:
            bits.append("Uma close waiting on people")
        if met_locked:
            bits.append("Habitat publish write still locked")
        tail = (" · " + " · ".join(bits)) if bits else ""
        return (
            f"Capabilities built on Beta (~{overall_pct}%) — "
            f"human commissioning & live ops still ahead{tail}"
        )
    if overall_pct < 40:
        return f"Mid-build (~{overall_pct}% PARTIAL ESTIMATE) — Core and first verticals advancing"
    return f"Empire ~{overall_pct}% PARTIAL ESTIMATE — commission, live, and buyer-ready still open"


def _status_chips(all_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    built_n = sum(1 for i in all_items if i.get("built"))
    commissioned_n = sum(1 for i in all_items if i.get("commissioned"))
    live_n = sum(1 for i in all_items if i.get("live"))
    waiting_n = sum(
        1
        for i in all_items
        if i.get("waiting_class") in ("WAITING_HUMAN", "BLOCKED_SYSTEM")
    )
    policy_n = sum(
        1 for i in all_items if i.get("waiting_class") == "UNAPPROVED_POLICY"
    )
    # HUMAN TESTING ≈ built but not commissioned (awaiting human path)
    human_testing_n = sum(
        1 for i in all_items if i.get("built") and not i.get("commissioned") and not i.get("live")
    )
    return [
        {
            "id": "BUILT",
            "label": "BUILT",
            "count": built_n,
            "tooltip": "Code/schema exists on Beta. BUILT ≠ COMMISSIONED ≠ LIVE.",
        },
        {
            "id": "HUMAN_TESTING",
            "label": "HUMAN TESTING",
            "count": human_testing_n,
            "tooltip": "Built paths awaiting human walkthrough / commission. Not LIVE.",
        },
        {
            "id": "LIVE",
            "label": "LIVE",
            "count": live_n,
            "tooltip": "Commissioned and operating live. Rare until human commission DONE.",
        },
        {
            "id": "WAITING",
            "label": "WAITING",
            "count": waiting_n,
            "tooltip": "WAITING_HUMAN or BLOCKED_SYSTEM — not the same as policy gap.",
        },
        {
            "id": "POLICY_NEEDED",
            "label": "POLICY NEEDED",
            "count": policy_n,
            "tooltip": "UNAPPROVED_POLICY — decision/data/policy required. ≠ system failure.",
        },
        {
            "id": "COMMISSIONED",
            "label": "COMMISSIONED",
            "count": commissioned_n,
            "tooltip": "HUMAN_COMMISSIONING=DONE. Hidden from hero chips by default; kept for honesty.",
            "hero": False,
        },
    ]


def _build_owner_pulse(
    overlay: dict[str, Any],
    factory_health: dict[str, Any],
    verticals: dict[str, Any],
) -> dict[str, Any]:
    cockpit = overlay.get("owner_cockpit") or {}
    pulse = dict(cockpit.get("owner_pulse") or {})
    # Always stamp build-system from live factory assessment
    pulse["build_system"] = {
        "factory": factory_health.get("status"),
        "production": "UNTOUCHED",
        "note": factory_health.get("note"),
    }
    # Ensure lists exist
    for key in ("working_now", "waiting_on_people", "policy_data_needed"):
        if key not in pulse or not isinstance(pulse[key], list):
            pulse[key] = []
    # Derive fallbacks from verticals if overlay empty
    if not pulse["waiting_on_people"]:
        uma = verticals.get("uma_close") or {}
        if uma.get("waiting") == "WAITING_FOR_CLOSER":
            pulse["waiting_on_people"].append(
                "Uma Blu closer to run first verified close (WAITING_HUMAN)"
            )
        pulse["waiting_on_people"].append(
            "Matt human commission of built Core governance slices"
        )
    if not pulse["policy_data_needed"]:
        uma = verticals.get("uma_close") or {}
        if uma.get("variance_policy") == "NOT_CONFIGURED":
            pulse["policy_data_needed"].append(
                "Uma variance threshold NOT_CONFIGURED (policy gap, not system failure)"
            )
    if not pulse["working_now"]:
        pulse["working_now"].append("Owner Cockpit + factory health split on Progress v2")
    pulse["source"] = pulse.get("source") or cockpit.get("source") or str(
        OVERLAY_PATH.relative_to(BETA_ROOT)
    )
    pulse["as_of"] = pulse.get("as_of") or cockpit.get("as_of") or overlay.get("as_of")
    pulse["confidence"] = pulse.get("confidence") or cockpit.get("confidence") or "CURATED"
    # Owner surface — no raw PERS-/EVR-/ROLE-/GPO- ids in pulse text (strip if present)
    return pulse


def _owner_text_clean(text: str) -> str:
    """Hide raw governance IDs from owner-facing strings."""
    import re

    s = text or ""
    s = re.sub(r"\b(PERS|EVR|ROLE|GPO|PERM|MB|OV)-[A-Z0-9-]+\b", "", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" ·,-")
    return s


def _build_next_moves(overlay: dict[str, Any]) -> list[dict[str, Any]]:
    cockpit = overlay.get("owner_cockpit") or {}
    moves = []
    for m in (cockpit.get("next_moves") or [])[:3]:
        if not isinstance(m, dict):
            continue
        cls = str(m.get("class") or "RECOMMENDED").upper()
        if cls not in ("ACTIVE", "WAITING", "RECOMMENDED", "APPROVED"):
            cls = "RECOMMENDED"
        moves.append(
            {
                "text": _owner_text_clean(str(m.get("text") or "")),
                "class": cls,
                "note": _owner_text_clean(str(m.get("note") or "")),
                # provenance stays in technical / source fields
                "source": m.get("source"),
                "as_of": m.get("as_of"),
                "confidence": m.get("confidence") or "CURATED",
            }
        )
    return moves[:3]


def _build_recent_wins(overlay: dict[str, Any]) -> list[dict[str, Any]]:
    cockpit = overlay.get("owner_cockpit") or {}
    wins = []
    for w in cockpit.get("recent_wins") or []:
        if not isinstance(w, dict):
            continue
        wins.append(
            {
                "text": _owner_text_clean(str(w.get("text") or "")),
                "evidence": w.get("evidence") or w.get("source") or "",
                "as_of": w.get("as_of"),
                "confidence": w.get("confidence") or "DERIVED",
            }
        )
    return wins


def _build_milestone_road(
    overlay: dict[str, Any],
    card: dict[str, dict[str, Any]],
    verticals: dict[str, Any],
    all_scored: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Evidence unlock: Foundations + First Real Workflow + Second Business Vertical
    when Core verticals + Habitat + Uma are built. Commission / external / buyer stay locked.
    """
    cockpit = overlay.get("owner_cockpit") or {}
    presets = cockpit.get("milestones") or []

    core_built = (card.get("Core") or {}).get("pct", 0) >= 25
    habitat_built = any(
        i.get("domain") == "GGV" and i.get("built")
        for i in all_scored
        if "Habitat" in (i.get("capability") or "")
    ) or (card.get("GGV") or {}).get("pct", 0) >= 40
    uma_built = any(
        i.get("domain") == "BZG" and i.get("built")
        for i in all_scored
        if "Uma" in (i.get("capability") or "")
    ) or (card.get("BZG") or {}).get("pct", 0) >= 25

    any_commissioned = any(i.get("commissioned") for i in all_scored)
    any_live = any(i.get("live") for i in all_scored)
    hab = verticals.get("habitat") or {}
    external_ok = bool((hab.get("distinctions") or {}).get("REAL_EXTERNAL_PUBLISH"))

    unlock_map = {
        "MS-FOUNDATIONS": (
            core_built,
            "Core tracked capabilities mid-build on Beta"
            if core_built
            else "Core tracked set still early",
        ),
        "MS-FIRST-WORKFLOW": (
            habitat_built or uma_built,
            "First vertical workflow path built (Habitat or Uma)"
            if (habitat_built or uma_built)
            else "No vertical end-to-end built yet",
        ),
        "MS-SECOND-VERTICAL": (
            habitat_built and uma_built,
            "Habitat and Uma both have built paths"
            if (habitat_built and uma_built)
            else "Need both Habitat and Uma built",
        ),
        "MS-HUMAN-COMMISSION": (
            any_commissioned,
            "At least one HUMAN_COMMISSIONING=DONE"
            if any_commissioned
            else "Commissioning.csv LIVE?=NO across board",
        ),
        "MS-EXTERNAL": (
            external_ok,
            "REAL_EXTERNAL_PUBLISH evidence"
            if external_ok
            else "Metricool write LOCKED; no REAL_EXTERNAL_PUBLISH",
        ),
        "MS-BUYER": (
            False,
            "Buyer Ready requires commissioned live ops + sale actuals trustworthy",
        ),
    }

    default_road = [
        {"id": "MS-FOUNDATIONS", "label": "Foundations", "order": 1},
        {"id": "MS-FIRST-WORKFLOW", "label": "First Real Workflow", "order": 2},
        {"id": "MS-SECOND-VERTICAL", "label": "Second Business Vertical", "order": 3},
        {"id": "MS-HUMAN-COMMISSION", "label": "First Human Commission", "order": 4},
        {"id": "MS-EXTERNAL", "label": "First External Action", "order": 5},
        {"id": "MS-BUYER", "label": "Buyer Ready", "order": 6},
    ]
    road_src = presets if presets else default_road
    out = []
    for m in sorted(road_src, key=lambda x: int(x.get("order") or 99)):
        mid = m.get("id") or ""
        unlocked, reason = unlock_map.get(mid, (False, m.get("reason") or "Locked"))
        # Overlay may force lock
        if m.get("locked") is True:
            unlocked = False
            reason = m.get("reason") or reason
        out.append(
            {
                "id": mid,
                "label": m.get("label") or mid,
                "unlocked": bool(unlocked),
                "reason": reason,
                "evidence": m.get("evidence") or m.get("source"),
                "order": m.get("order"),
            }
        )
    return out


def _domain_owner_card(card_entry: dict[str, Any]) -> dict[str, Any]:
    """Owner-facing domain summary — no raw item IDs."""
    return {
        "domain": card_entry["domain"],
        "weight": card_entry["weight"],
        "weight_label": "ESTIMATED",
        "weight_pct_display": card_entry.get("weight_pct_display"),
        "pct": card_entry["pct"],
        "score": card_entry["score"],
        "visual_pct": card_entry["visual_pct"],
        "item_count": card_entry["item_count"],
        "plain_phase": card_entry["plain_phase"],
        "biggest_gap": _owner_text_clean(card_entry["biggest_gap"]),
        "denominator_note": card_entry.get("denominator_note"),
    }


def build_read_model(*, overlay_path: Path | None = None) -> dict[str, Any]:
    overlay = load_overlay(overlay_path)
    master = load_master_build_rows()
    comm = load_commissioning_done_map()
    for row in master:
        key = (row.get("capability") or "").lower()
        if key and comm.get(key):
            row["human_commissioning"] = "DONE"
            row["commissioned"] = True

    merged = merge_overlay(master, overlay)
    integ = integrations_items()
    sale = sale_readiness_items()
    factory = factory_health_items()
    backlog = backlog_items()

    # Mission-scored items EXCLUDE factory
    all_scored = merged + integ + sale
    card = domain_scorecard(all_scored)
    overall = overall_from_card(card)
    reconcile = reconcile_prior(overall["overall_pct"], overlay)

    verticals = overlay.get("verticals") or {}
    achievements = overlay.get("achievements") or []
    factory_health = assess_factory_health(factory)

    for it in all_scored + backlog + factory:
        wc = waiting_class_for(it)
        if wc:
            it["waiting_class"] = wc

    owner_phase = _derive_owner_phase(card, overall["overall_pct"], verticals)
    status_chips = _status_chips(all_scored)
    owner_pulse = _build_owner_pulse(overlay, factory_health, verticals)
    next_moves = _build_next_moves(overlay)
    recent_wins = _build_recent_wins(overlay)
    milestone_road = _build_milestone_road(overlay, card, verticals, all_scored)

    owner_domains = {d: _domain_owner_card(card[d]) for d in DOMAIN_WEIGHTS}

    habitat_owner = {
        "stages": _owner_habitat_stages(verticals.get("habitat") or {}),
        "distinctions_plain": [
            "APPROVED ≠ PUBLISHED",
            "Metricool write LOCKED",
            "No real external publish yet",
        ],
    }
    uma_owner = {
        "stages": _owner_uma_stages(verticals.get("uma_close") or {}),
        "waiting_plain": "Waiting for closer (WAITING_HUMAN — not a system outage)",
        "variance_plain": "Variance policy not configured — policy gap, not system failure",
    }

    views: dict[str, Any] = {}
    for view_name in VIEWS:
        domain = VIEW_DOMAIN[view_name]
        if view_name == "Empire":
            views[view_name] = {
                "view": view_name,
                "owner_phase": owner_phase,
                "status_chips": [c for c in status_chips if c.get("hero", True)],
                "owner_pulse": owner_pulse,
                "next_moves": next_moves,
                "recent_wins": recent_wins,
                "milestone_road": milestone_road,
                "domains": owner_domains,
                "habitat_owner": habitat_owner,
                "uma_owner": uma_owner,
                "factory_health": {
                    "status": factory_health["status"],
                    "production": "UNTOUCHED",
                },
                "technical_details": {
                    "items": all_scored,
                    "verticals": verticals,
                    "achievements": achievements,
                    "factory_items": factory,
                    "factory_health_checks": factory_health.get("checks"),
                    "status_chips_all": status_chips,
                },
            }
        elif view_name == "Backlog":
            views[view_name] = {
                "view": view_name,
                "items": backlog,
                "note": "Explicit Not_Yet register — NOT TARGET, not scored into empire %.",
            }
        elif view_name == "GGV":
            items = [i for i in all_scored if i.get("domain") == "GGV"]
            views[view_name] = {
                "view": view_name,
                "pct": card["GGV"]["pct"],
                "plain_phase": card["GGV"]["plain_phase"],
                "biggest_gap": card["GGV"]["biggest_gap"],
                "visual_pct": card["GGV"]["visual_pct"],
                "habitat_owner": habitat_owner,
                "items": items,
                "habitat": verticals.get("habitat"),
            }
        elif view_name == "BZG":
            items = [i for i in all_scored if i.get("domain") == "BZG"]
            views[view_name] = {
                "view": view_name,
                "pct": card["BZG"]["pct"],
                "plain_phase": card["BZG"]["plain_phase"],
                "biggest_gap": card["BZG"]["biggest_gap"],
                "visual_pct": card["BZG"]["visual_pct"],
                "uma_owner": uma_owner,
                "items": items,
                "uma_close": verticals.get("uma_close"),
            }
        elif view_name == "Build Factory":
            views[view_name] = {
                "view": view_name,
                "factory_health": factory_health,
                "items": factory,
                "note": "Factory health is system status — excluded from mission weighted %.",
            }
        else:
            items = [i for i in all_scored if i.get("domain") == domain]
            dcard = card.get(domain or "") if domain else {}
            views[view_name] = {
                "view": view_name,
                "pct": dcard.get("pct") if dcard else None,
                "plain_phase": dcard.get("plain_phase") if dcard else None,
                "biggest_gap": dcard.get("biggest_gap") if dcard else None,
                "visual_pct": dcard.get("visual_pct") if dcard else None,
                "denominator_note": dcard.get("denominator_note") if dcard else None,
                "items": items,
            }

    return {
        "ok": True,
        "generated_at": now_iso(),
        "progress_type": "PARTIAL_ESTIMATE",
        "master_build_csv_staleness": overlay.get(
            "master_build_csv_staleness", "KNOWN"
        ),
        "overlay_required": True,
        "overall": overall,
        "reconcile": reconcile,
        "owner_phase": owner_phase,
        "status_chips": [c for c in status_chips if c.get("hero", True)],
        "owner_pulse": owner_pulse,
        "next_moves": next_moves,
        "recent_wins": recent_wins,
        "milestone_road": milestone_road,
        "factory_health": factory_health,
        "domain_weights": {
            d: {"weight": w, "label": "ESTIMATED", "pct_display": WEIGHT_PCT_DISPLAY.get(d)}
            for d, w in DOMAIN_WEIGHTS.items()
        },
        "domains": owner_domains,
        "views": views,
        "menu": list(VIEWS),
        "default_view": "Empire",
        "verticals": verticals,
        "achievements": achievements,
        "calculation": calculation_english(),
        "overlay_meta": {
            "version": overlay.get("version"),
            "as_of": overlay.get("as_of"),
            "row_count": len(overlay.get("rows") or []),
            "path": str(OVERLAY_PATH.relative_to(BETA_ROOT)),
        },
        "distinctions": {
            "BUILT_NE_COMMISSIONED_NE_LIVE": True,
            "TARGET_PROFIT_NE_ACTUAL": True,
            "ACTUAL_TRUST": "NOT YET TRUSTWORTHY",
            "FACTORY_EXCLUDED_FROM_MISSION_PCT": True,
        },
        "technical_details": {
            "raw_domain_items": {d: card[d]["items"] for d in DOMAIN_WEIGHTS},
            "factory_items": factory,
        },
    }


def get_view(name: str, *, overlay_path: Path | None = None) -> dict[str, Any]:
    model = build_read_model(overlay_path=overlay_path)
    key = name.strip()
    aliases = {
        "empire": "Empire",
        "core": "Wolf Core",
        "wolf core": "Wolf Core",
        "wolf_core": "Wolf Core",
        "ggv": "GGV",
        "amg": "AMG",
        "bzg": "BZG",
        "intelligence": "Intelligence",
        "integrations": "Integrations",
        "sale readiness": "Sale Readiness",
        "sale_readiness": "Sale Readiness",
        "build factory": "Build Factory",
        "factory": "Build Factory",
        "backlog": "Backlog",
    }
    resolved = aliases.get(key.lower(), key)
    if resolved not in model["views"]:
        return {
            "ok": False,
            "error": "unknown_view",
            "message": f"Unknown view: {name}",
            "menu": model["menu"],
        }
    return {
        "ok": True,
        "progress_type": model["progress_type"],
        "overall": model["overall"],
        "reconcile": model["reconcile"],
        "owner_phase": model["owner_phase"],
        "factory_health": model["factory_health"],
        "calculation": model["calculation"],
        "view": model["views"][resolved],
        "menu": model["menu"],
        "default_view": model["default_view"],
    }


def honesty_flags() -> dict[str, Any]:
    return {
        "progress_type": "PARTIAL_ESTIMATE",
        "master_build_csv_staleness": "KNOWN",
        "overlay_required": True,
        "owner_only": True,
        "person_gate": PERS_MATT,
        "built_ne_commissioned_ne_live": True,
        "factory_excluded_from_mission_pct": True,
        "no_esb_writes": True,
        "no_metricool_writes": True,
        "no_habitat_planner_mutations": True,
        "no_production_writes": True,
    }


if __name__ == "__main__":
    print(json.dumps(build_read_model(), indent=2, default=str)[:5000])
