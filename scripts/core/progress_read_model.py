#!/usr/bin/env python3
"""Matt Progress Dashboard v1 — read-model (Beta, Owner-only consumers).

BUILT ≠ HUMAN_COMMISSIONED ≠ LIVE.
progress_type: PARTIAL_ESTIMATE while Master_Build CSV + overlay mix exists.
No ESB / Metricool / Production / Habitat mutations.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
BUILD_DASH = BETA_ROOT / "docs" / "canon" / "build-dashboard"
OVERLAY_PATH = BETA_ROOT / "state" / "progress" / "v1_overlay.json"
FACTORY_RUNS = BETA_ROOT / "state" / "build-factory" / "runs"
TZ8 = timezone(timedelta(hours=8))

PERS_MATT = "PERS-MATT"

# CURATED domain weights — labelled ESTIMATED until a registry owns them.
DOMAIN_WEIGHTS: dict[str, float] = {
    "Core": 0.25,
    "GGV": 0.20,
    "BZG": 0.15,
    "AMG": 0.15,
    "Intelligence": 0.10,
    "Integrations": 0.05,
    "Sale Readiness": 0.05,
    "Factory health": 0.05,
}

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
    # Vertical / honesty tokens (not Master_Build lifecycle)
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


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def _norm_domain(raw: str) -> str:
    key = (raw or "").strip()
    if not key:
        return "Core"
    aliased = DOMAIN_ALIASES.get(key.lower())
    if aliased:
        return aliased
    # Preserve known weight keys
    for name in DOMAIN_WEIGHTS:
        if name.lower() == key.lower():
            return name
    return key


def _norm_lifecycle(raw: str) -> str:
    s = (raw or "").strip().upper().replace("-", "_")
    s = s.replace(" ", "_")
    # CSV uses SCHEMA_BUILT, BETA, etc.
    if s in LIFECYCLE_SCORES:
        return s
    # Soft aliases
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
                "human_commissioning": "NOT_DONE",  # Commissioning.csv LIVE?=NO
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
    """Return capability-name → commissioning LIVE? Done.

    Commissioning.csv currently marks LIVE?=NO for every row — honesty preserved.
    """
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
    """Overlay fills gaps; does not invent a second PM truth."""
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
            "built": bool(ov.get("built", lifecycle in ("SCHEMA_BUILT", "BETA", "TESTED", "PILOT", "VERIFIED", "LIVE"))),
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
        # Prefer overlay maturity over stale Master_Build for same MB id:
        # keep Master row, stamp overlay_applied; also keep discrete overlay capability.
        if mid and mid in by_id:
            base = by_id[mid]
            # Raise Master row lifecycle if overlay is further along for that slice area
            base["overlay_applied"] = True
            base["overlay_note"] = f"Stale CSV vs overlay {item['id']} ({lifecycle})"
            # Do not silently flip Master LIVE; preserve honesty on MB row
            if LIFECYCLE_SCORES.get(lifecycle, 0) > LIFECYCLE_SCORES.get(
                base.get("lifecycle") or "", 0
            ):
                base["lifecycle_csv"] = base.get("lifecycle")
                # Keep CSV status visible; scoring uses capability list including overlay rows
        extras.append(item)
    return list(by_id.values()) + extras


def maturity_score(
    lifecycle: str,
    *,
    human_commissioning: str = "NOT_DONE",
    live: bool = False,
) -> float:
    """Lifecycle score with commissioning penalty (BUILT ≠ LIVE)."""
    lc = _norm_lifecycle(lifecycle)
    if lc == "RETIRED" or lc == "NOT_TARGET":
        return 0.0
    raw = LIFECYCLE_SCORES.get(lc, 0.05)
    if live and lc == "LIVE" and human_commissioning == "DONE":
        return 1.0
    # Cap when built/tested/live-claimed but human commissioning not DONE (BUILT ≠ LIVE)
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
                "built": lifecycle in ("SCHEMA_BUILT", "BETA", "TESTED", "PILOT", "VERIFIED", "LIVE"),
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
        # Map factory stages roughly — COMPLETED/SHIPPED ≈ tested; WAITING_* not live
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


def domain_scorecard(
    items: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_domain: dict[str, list[dict[str, Any]]] = {d: [] for d in DOMAIN_WEIGHTS}
    for it in items:
        d = _norm_domain(it.get("domain") or "")
        if d not in by_domain:
            # Fold unknown into Core for empire weight (still listed in detail views)
            by_domain.setdefault("Core", []).append(it)
            continue
        by_domain[d].append(it)

    card: dict[str, dict[str, Any]] = {}
    for domain, weight in DOMAIN_WEIGHTS.items():
        group = by_domain.get(domain) or []
        score = score_items(group)
        card[domain] = {
            "domain": domain,
            "weight": weight,
            "weight_label": "ESTIMATED",
            "score": round(score, 4),
            "pct": int(round(score * 100)),
            "item_count": len(group),
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
    if abs(delta) <= 8:
        return {
            "prior_pct": prior_i,
            "computed_pct": overall_pct,
            "delta": delta,
            "show_why": False,
        }
    return {
        "prior_pct": prior_i,
        "computed_pct": overall_pct,
        "delta": delta,
        "show_why": True,
        "why": overlay.get("prior_estimate_note")
        or "Computed estimate differs from prior ~32% by >8 pts (new Core slices + verticals).",
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
    return {
        "title": "How is this calculated?",
        "progress_type": "PARTIAL_ESTIMATE",
        "steps": [
            "Domain weights (CURATED, labelled ESTIMATED): Core 25%, GGV 20%, BZG 15%, AMG 15%, Intelligence 10%, Integrations 5%, Sale Readiness 5%, Factory health 5%.",
            "Per-capability maturity from lifecycle (not file count): IDEA/SPECIFIED=0.05 · APPROVED=0.15 · BUILDING=0.35 · BETA/SCHEMA_BUILT/TESTED=0.55 · PILOT=0.7 · VERIFIED=0.85 · LIVE=1.0 · RETIRED=n/a.",
            "Commissioning penalty: if BUILT/TESTED but HUMAN_COMMISSIONING ≠ DONE → score capped at 0.65 (BUILT ≠ LIVE).",
            "Overall = weighted average of domain scores. Shown as integer % + label PARTIAL ESTIMATE while Master_Build CSV + overlay mix exists.",
            "If computed % differs from prior ~32% by more than 8 points, a why note explains new Core slices + verticals.",
        ],
        "honesty": {
            "progress_type": "PARTIAL_ESTIMATE",
            "master_build_csv_staleness": "KNOWN",
            "overlay_required": True,
            "no_fake_precision": True,
            "peaches_recommendation_is_not_approved": True,
        },
        "distinctions": [
            "BUILT ≠ HUMAN_COMMISSIONED ≠ LIVE",
            "WAITING_HUMAN ≠ BLOCKED_SYSTEM ≠ UNAPPROVED_POLICY ≠ INACCESSIBLE_SOURCE",
            "TARGET profit ≠ ACTUAL (ACTUAL NOT YET TRUSTWORTHY)",
            "ESTIMATED labelled",
        ],
    }


def build_read_model(*, overlay_path: Path | None = None) -> dict[str, Any]:
    overlay = load_overlay(overlay_path)
    master = load_master_build_rows()
    # Apply commissioning map (all NOT_DONE today)
    comm = load_commissioning_done_map()
    for row in master:
        # Best-effort name match — default NOT_DONE
        key = (row.get("capability") or "").lower()
        if key and comm.get(key):
            row["human_commissioning"] = "DONE"
            row["commissioned"] = True

    merged = merge_overlay(master, overlay)
    integ = integrations_items()
    sale = sale_readiness_items()
    factory = factory_health_items()
    backlog = backlog_items()

    all_scored = merged + integ + sale + factory
    card = domain_scorecard(all_scored)
    # Backlog is view-only (NOT_TARGET); do not weight into empire
    overall = overall_from_card(card)
    reconcile = reconcile_prior(overall["overall_pct"], overlay)

    verticals = overlay.get("verticals") or {}
    achievements = overlay.get("achievements") or []

    views: dict[str, Any] = {}
    for view_name in VIEWS:
        domain = VIEW_DOMAIN[view_name]
        if view_name == "Empire":
            views[view_name] = {
                "view": view_name,
                "domains": {
                    d: {
                        "domain": d,
                        "weight": card[d]["weight"],
                        "weight_label": "ESTIMATED",
                        "pct": card[d]["pct"],
                        "score": card[d]["score"],
                        "item_count": card[d]["item_count"],
                    }
                    for d in DOMAIN_WEIGHTS
                },
                "items": all_scored,
                "verticals": verticals,
                "achievements": achievements,
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
                "items": items,
                "habitat": verticals.get("habitat"),
            }
        elif view_name == "BZG":
            items = [i for i in all_scored if i.get("domain") == "BZG"]
            views[view_name] = {
                "view": view_name,
                "pct": card["BZG"]["pct"],
                "items": items,
                "uma_close": verticals.get("uma_close"),
            }
        else:
            items = [i for i in all_scored if i.get("domain") == domain]
            views[view_name] = {
                "view": view_name,
                "pct": card.get(domain or "", {}).get("pct") if domain else None,
                "items": items,
            }

    # Annotate waiting classes
    for it in all_scored + backlog:
        wc = waiting_class_for(it)
        if wc:
            it["waiting_class"] = wc

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
        "domain_weights": {
            d: {"weight": w, "label": "ESTIMATED"} for d, w in DOMAIN_WEIGHTS.items()
        },
        "domains": {
            d: {
                "domain": d,
                "weight": card[d]["weight"],
                "weight_label": "ESTIMATED",
                "pct": card[d]["pct"],
                "score": card[d]["score"],
                "item_count": card[d]["item_count"],
            }
            for d in DOMAIN_WEIGHTS
        },
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
        },
    }


def get_view(name: str, *, overlay_path: Path | None = None) -> dict[str, Any]:
    model = build_read_model(overlay_path=overlay_path)
    key = name.strip()
    # Accept aliases
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
        "no_esb_writes": True,
        "no_metricool_writes": True,
        "no_habitat_planner_mutations": True,
        "no_production_writes": True,
    }


if __name__ == "__main__":
    print(json.dumps(build_read_model(), indent=2, default=str)[:4000])
