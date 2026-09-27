#!/usr/bin/env python3
"""Matt Progress Dashboard v2.2 — Owner Cockpit read-model (Beta, Owner-only).

Primary dial: SYSTEM — computed on each read from state/model-c-baseline-assessments.json
(Model C maturity credits). Never hard-code the live percentage.

Legacy: overall_from_card / PARTIAL ESTIMATE (Master_Build mix) kept as history only —
not rendered as the Owner primary number.

BUILT ≠ HUMAN_COMMISSIONED ≠ LIVE.
Factory health is SYSTEM STATUS — excluded from SYSTEM maturity %.
SPECIFIED/IDEA/APPROVED → PLANNED (never auto UNAPPROVED_POLICY).
UNAPPROVED_POLICY only from curated policy_decisions[] / explicit flags.
No ESB / Metricool / Production / Habitat mutations.
"""
from __future__ import annotations

import csv
import json
import re
import socket
import urllib.error
import urllib.request
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
BUILD_DASH = BETA_ROOT / "docs" / "canon" / "build-dashboard"
OVERLAY_PATH = BETA_ROOT / "state" / "progress" / "v1_overlay.json"
FACTORY_ROOT = BETA_ROOT / "state" / "build-factory"
FACTORY_RUNS = FACTORY_ROOT / "runs"
# In-flight factory stages that mean Owner Progress "In progress" cannot be a silent 0.
FACTORY_IN_FLIGHT_STAGES = frozenset(
    {
        "ACTIVE",
        "WAITING_CURSOR",
        "WAITING_GROK",
        "GROK_REVIEW",
        "IN_FLIGHT",
        "BUILDING",
    }
)
FACTORY_DONE_STAGES = frozenset(
    {"DONE", "SHIPPED", "COMPLETE", "VERIFIED", "FINISHED"}
)
MODEL_C_LEDGER = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
MODEL_C_HISTORY = BETA_ROOT / "state" / "model-c-score-history.jsonl"
MODEL_C_CATALOG = BETA_ROOT / "docs" / "MODEL-C-CAPABILITY-CATALOG.md"
PROGRESS_HTML = BETA_ROOT / "dashboards" / "progress.html"
TZ8 = timezone(timedelta(hours=8))

PERS_MATT = "PERS-MATT"

# Locked Model C maturity credits (docs/MODEL-C-SYSTEM-NUMERIC-CREDITS.md). Do not edit table here.
SYSTEM_MATURITY_CREDITS: dict[str, Decimal] = {
    "ABSENT": Decimal("0.00"),
    "SPECIFIED": Decimal("0.05"),
    "BUILT": Decimal("0.25"),
    "PROVEN": Decimal("0.80"),
    "READY": Decimal("1.00"),
}
EXPECTED_CAPABILITY_COUNT = 77
SYSTEM_FORMULA = "SYSTEM% = SUM(canonical capability maturity credits) / 77 × 100"
STALE_STATUS = "SCORING_PROJECTION_STALE"

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

# Owner Progress primary nav (Empire cockpit). BZG routes to existing pages.
PRIMARY_NAV = (
    {"id": "Empire", "label": "Empire", "kind": "view"},
    {"id": "GGV", "label": "GGV", "kind": "view"},
    {"id": "AMG", "label": "AMG", "kind": "view"},
    {
        "id": "BZG",
        "label": "BZG",
        "kind": "links",
        "href": "/bzg",
        "links": [
            {"label": "BZG", "href": "/bzg"},
            {"label": "Uma Blu", "href": "/bzg/uma-blu"},
        ],
    },
)

MODEL_E_UNSCORED = (
    ("Operating Adoption", "Not scored yet"),
    ("Data / Measurement", "Not scored yet"),
    ("Founder Independence", "Not scored yet"),
    ("Financial Control", "Not scored yet"),
    ("Sale Readiness", "Not scored yet"),
)


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def _round_half_up_1dp(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def load_catalog_cap_domains(*, catalog_path: Path | None = None) -> dict[str, str]:
    """CAP-ID → domain label from MODEL-C-CAPABILITY-CATALOG.md. Do not invent domains."""
    path = catalog_path or MODEL_C_CATALOG
    text = path.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    domain: str | None = None
    for line in text.splitlines():
        m = re.match(r"^### (D-[A-Z]+) — (.+?) \((\d+)\)\s*$", line)
        if m:
            domain = f"{m.group(1)} — {m.group(2).strip()}"
            continue
        m = re.match(r"^\| (CAP-[A-Z0-9]+-\d+) \|", line)
        if m and domain:
            out[m.group(1)] = domain
    return out


def compute_system_from_ledger(
    ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Compute SYSTEM% from the Model C maturity ledger on every read.

    Unknown maturity state → hard fail (not zero).
    Row count ≠ 77 → SCORING_PROJECTION_STALE, no percentage.
    """
    path = Path(ledger_path) if ledger_path else MODEL_C_LEDGER
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Model C ledger must be a dict of CAP rows: {path}")

    n = len(raw)
    counts: Counter[str] = Counter()
    sum_credits = Decimal("0")
    for cap_id, row in raw.items():
        if not isinstance(row, (list, tuple)) or not row:
            raise ValueError(f"Ledger row {cap_id!r} missing maturity state")
        state = str(row[0]).strip().upper()
        if state not in SYSTEM_MATURITY_CREDITS:
            raise ValueError(
                f"Unknown maturity state {state!r} for {cap_id} — hard fail, not zero"
            )
        credit = SYSTEM_MATURITY_CREDITS[state]
        counts[state] += 1
        sum_credits += credit

    count_block = {
        "ABSENT": int(counts.get("ABSENT", 0)),
        "SPECIFIED": int(counts.get("SPECIFIED", 0)),
        "BUILT": int(counts.get("BUILT", 0)),
        "PROVEN": int(counts.get("PROVEN", 0)),
        "READY": int(counts.get("READY", 0)),
    }

    base: dict[str, Any] = {
        "label": "SYSTEM",
        "n": n,
        "expected_n": EXPECTED_CAPABILITY_COUNT,
        "sum_credits": float(sum_credits),
        "sum_credits_exact": str(sum_credits),
        "counts": count_block,
        "formula": SYSTEM_FORMULA,
        "credits_version": "MODEL-C-SYSTEM-CREDITS-v1.0-2026-09-17",
        "ledger_path": str(path),
        "primary": True,
    }

    if n != EXPECTED_CAPABILITY_COUNT:
        base.update(
            {
                "status": STALE_STATUS,
                "system_pct": None,
                "ok": False,
                "stale_reason": f"row_count={n} expected={EXPECTED_CAPABILITY_COUNT}",
            }
        )
        return base

    exact = (sum_credits / Decimal(EXPECTED_CAPABILITY_COUNT)) * Decimal(100)
    system_pct = float(_round_half_up_1dp(exact))
    base.update(
        {
            "status": "OK",
            "system_pct": system_pct,
            "ok": True,
            "stale_reason": None,
        }
    )
    return base


def _waiting_evidence_open(next_bar: str) -> bool:
    note = (next_bar or "").strip()
    if not note:
        return False
    low = note.lower()
    if low.startswith("none"):
        return False
    return True


def system_detail_from_ledger(
    ledger_path: Path | None = None,
    *,
    catalog_path: Path | None = None,
    history_path: Path | None = None,
) -> dict[str, Any]:
    """Owner-facing SYSTEM detail: counts, domains, history, waiting evidence."""
    path = Path(ledger_path) if ledger_path else MODEL_C_LEDGER
    raw = json.loads(path.read_text(encoding="utf-8"))
    domains = load_catalog_cap_domains(catalog_path=catalog_path)
    by_domain: dict[str, Counter[str]] = {}
    waiting: list[dict[str, str]] = []
    for cap_id, row in raw.items():
        state = str(row[0]).strip().upper()
        domain = domains.get(cap_id) or "UNMAPPED (catalog miss — do not invent)"
        by_domain.setdefault(domain, Counter())[state] += 1
        next_bar = str(row[2]) if len(row) > 2 else ""
        if _waiting_evidence_open(next_bar):
            waiting.append(
                {
                    "id": cap_id,
                    "state": state,
                    "domain": domain,
                    "waiting_evidence": next_bar.strip(),
                }
            )

    domain_counts = []
    for domain in sorted(by_domain.keys()):
        c = by_domain[domain]
        domain_counts.append(
            {
                "domain": domain,
                "n": sum(c.values()),
                "ABSENT": int(c.get("ABSENT", 0)),
                "SPECIFIED": int(c.get("SPECIFIED", 0)),
                "BUILT": int(c.get("BUILT", 0)),
                "PROVEN": int(c.get("PROVEN", 0)),
                "READY": int(c.get("READY", 0)),
            }
        )

    hist_path = Path(history_path) if history_path else MODEL_C_HISTORY
    movements: list[dict[str, Any]] = []
    if hist_path.is_file():
        lines = [ln for ln in hist_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        for ln in lines[-8:]:
            try:
                movements.append(json.loads(ln))
            except json.JSONDecodeError:
                continue

    return {
        "capability_count": len(raw),
        "expected_capability_count": EXPECTED_CAPABILITY_COUNT,
        "domain_counts": domain_counts,
        "waiting_evidence": waiting,
        "recent_movements": movements,
        "note": (
            "77 capabilities · five maturity states · domains from the canonical catalog. "
            "Factory/pulse health is a separate block — not folded into SYSTEM%."
        ),
    }


def model_e_dials(system: dict[str, Any]) -> list[dict[str, Any]]:
    """Five Model E lines — all unscored. SYSTEM% is the owner headline only, not a list row."""
    _ = system  # call-site compatibility; SYSTEM figure is not a dial row
    dials: list[dict[str, Any]] = []
    for label, display in MODEL_E_UNSCORED:
        dials.append(
            {
                "id": label,
                "label": label,
                "value": None,
                "display": display,
                "scored": False,
            }
        )
    return dials


def _html_hardcoded_live_pcts(html: str) -> list[str]:
    """Detect hard-coded live percentages that must never be the projection source."""
    found: list[str] = []
    # Assemble forbidden live dial literals so this source file does not itself embed them.
    forbidden_one_decimal = f"{25}.{3}"
    if re.search(rf"(?<![0-9.]){re.escape(forbidden_one_decimal)}(?![0-9])", html):
        found.append(forbidden_one_decimal)
    # Integer retired build-tracker figure as a live % only when not marked legacy/history.
    retired_int = str(20 + 8)
    for m in re.finditer(rf"(?<![0-9]){retired_int}(?:\s*%|\s*percent)?", html):
        start = max(0, m.start() - 80)
        ctx = html[start : m.end() + 40].lower()
        if any(
            marker in ctx
            for marker in ("legacy", "retired", "history", "prior", "pending", "old ")
        ):
            continue
        found.append(retired_int)
        break
    return found


def assess_scoring_integrity(
    system: dict[str, Any],
    *,
    ledger_path: Path | None = None,
    integrity_against_path: Path | None = None,
    html_path: Path | None = None,
) -> dict[str, Any]:
    """One integrity check: ledger · read-model · rendered HTML projection.

    If any disagree → SCORING_PROJECTION_STALE and no percentage.
    Tests point integrity_against_path at a disagreeing temp ledger — never edit the real one.
    """
    path = Path(ledger_path) if ledger_path else Path(system.get("ledger_path") or MODEL_C_LEDGER)
    from_ledger = compute_system_from_ledger(path)
    compare_path = Path(integrity_against_path) if integrity_against_path else path
    from_compare = compute_system_from_ledger(compare_path)

    html_file = Path(html_path) if html_path else PROGRESS_HTML
    html_text = html_file.read_text(encoding="utf-8") if html_file.is_file() else ""
    html_hardcodes = _html_hardcoded_live_pcts(html_text)
    # Rendered Progress uses API projection; static HTML must not embed a live %.
    html_agrees = len(html_hardcodes) == 0

    model_pct = system.get("system_pct")
    ledger_pct = from_ledger.get("system_pct")
    compare_pct = from_compare.get("system_pct")

    ledger_agrees = (
        from_ledger.get("status") == system.get("status")
        and from_ledger.get("sum_credits_exact") == system.get("sum_credits_exact")
        and ledger_pct == model_pct
    )
    compare_agrees = (
        from_compare.get("status") == system.get("status")
        and from_compare.get("sum_credits_exact") == system.get("sum_credits_exact")
        and compare_pct == model_pct
    )

    ok = bool(ledger_agrees and compare_agrees and html_agrees and system.get("status") == "OK")
    reasons: list[str] = []
    if not ledger_agrees:
        reasons.append("ledger_vs_read_model_mismatch")
    if not compare_agrees:
        reasons.append("integrity_against_path_mismatch")
    if not html_agrees:
        reasons.append(f"html_hardcoded_live_pct:{','.join(html_hardcodes)}")
    if system.get("status") != "OK":
        reasons.append(str(system.get("stale_reason") or system.get("status")))

    return {
        "ok": ok,
        "status": "OK" if ok else STALE_STATUS,
        "ledger_pct": ledger_pct,
        "read_model_pct": model_pct,
        "compare_pct": compare_pct,
        "html_hardcoded_live_pcts": html_hardcodes,
        "html_projection": "api_dynamic" if html_agrees else "stale_hardcode",
        "reasons": reasons,
    }


def apply_integrity_to_system(
    system: dict[str, Any], integrity: dict[str, Any]
) -> dict[str, Any]:
    """If integrity fails, blank the percentage and mark stale."""
    out = dict(system)
    out["integrity"] = integrity
    if not integrity.get("ok"):
        out["status"] = STALE_STATUS
        out["system_pct"] = None
        out["ok"] = False
        out["stale_reason"] = ";".join(integrity.get("reasons") or ["integrity"])
    return out


def bzg_operational_pulse() -> dict[str, Any] | None:
    """BZG card pulse from live ops state. Skip example:true. Fail → None (show nothing)."""
    try:
        from core import uma_ops_console as uoc

        today = uoc.today_cards()
        issues_payload = uoc.list_issues()
    except Exception:  # noqa: BLE001
        return None

    if not isinstance(today, dict) or not today.get("ok"):
        return None

    cards = today.get("cards") or []
    daily_close = None
    pr_attention = 0
    policy_required = 0
    for card in cards:
        if not isinstance(card, dict):
            continue
        kind = card.get("kind")
        if kind == "daily_close":
            close = card.get("close") or {}
            daily_close = {
                "status": close.get("status") or card.get("title"),
                "label": card.get("title"),
                "business_date": close.get("business_date"),
            }
            continue
        items = [i for i in (card.get("items") or []) if not i.get("example")]
        # Prefer filtered item count; fall back only when items absent and card not example.
        if card.get("example"):
            continue
        n = len(items) if card.get("items") is not None else int(card.get("count") or 0)
        if kind == "policy_required":
            policy_required += n
        elif kind in (
            "prs_waiting_approval",
            "ordered_not_received",
            "bills_waiting_payment_approval",
            "payment_claimed_not_verified",
        ):
            pr_attention += n

    unresolved = 0
    if isinstance(issues_payload, dict):
        for iss in issues_payload.get("issues") or []:
            if isinstance(iss, dict) and not iss.get("example"):
                unresolved += 1

    return {
        "daily_close": daily_close,
        "pr_attention_count": pr_attention,
        "policy_required_count": policy_required,
        "unresolved_issues_count": unresolved,
        "links": {"bzg": "/bzg", "uma_blu": "/bzg/uma-blu"},
    }


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


def sale_readiness_items(
    *,
    csv_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Sale Readiness projection from canon CSV. Optional csv_path for fixture proves."""
    items = []
    if csv_path is not None:
        path = Path(csv_path)
        rows: list[dict[str, str]] = []
        if path.is_file():
            with path.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
        source = str(path)
    else:
        rows = _read_csv("Sale_Readiness.csv")
        source = "docs/canon/build-dashboard/Sale_Readiness.csv"
    for i, r in enumerate(rows):
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
                "source": source,
                "target_profit_note": "TARGET ≠ ACTUAL — ACTUAL NOT YET TRUSTWORTHY",
            }
        )
    return items


def factory_health_items(
    *,
    runs_dir: Path | None = None,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    root = runs_dir or FACTORY_RUNS
    if not root.is_dir():
        return items
    for path in sorted(root.glob("BF-*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        stage = (data.get("stage") or "UNKNOWN").strip()
        if stage in ("DONE", "SHIPPED", "COMPLETE", "VERIFIED", "FINISHED"):
            lifecycle = "TESTED"
        elif stage in FACTORY_IN_FLIGHT_STAGES:
            lifecycle = "BUILDING"
        else:
            lifecycle = "SPECIFIED"
        rel = str(path)
        try:
            rel = str(path.relative_to(BETA_ROOT))
        except ValueError:
            pass
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
                "source": rel,
                "stage": stage,
                "as_of": data.get("updated_at"),
            }
        )
    return items


def _factory_pack_card(data: dict[str, Any], *, path: Path | None = None) -> dict[str, Any]:
    run_id = str(data.get("run_id") or (path.stem if path else "") or "").strip()
    return {
        "run_id": run_id,
        "slice": str(data.get("slice") or data.get("lane_id") or run_id).strip(),
        "stage": str(data.get("stage") or "").strip(),
        "updated_at": data.get("updated_at"),
        "mission_id": data.get("mission_id"),
    }


def _read_json_obj(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def factory_work_surface(
    *,
    factory_root: Path | None = None,
    runs_dir: Path | None = None,
) -> dict[str, Any]:
    """Owner-facing factory activity — not an engineering dump, not SYSTEM%."""
    root = factory_root or FACTORY_ROOT
    runs = runs_dir or (root / "runs")
    in_flight: list[dict[str, Any]] = []
    completed: list[dict[str, Any]] = []
    stage_counts: Counter[str] = Counter()

    if runs.is_dir():
        for path in sorted(runs.glob("BF-*.json")):
            data = _read_json_obj(path)
            if not data:
                continue
            stage = str(data.get("stage") or "").strip()
            if not stage:
                continue
            stage_counts[stage] += 1
            card = _factory_pack_card(data, path=path)
            if stage in FACTORY_IN_FLIGHT_STAGES:
                in_flight.append(card)
            elif stage in FACTORY_DONE_STAGES:
                completed.append(card)

    def _ts(card: dict[str, Any]) -> str:
        return str(card.get("updated_at") or "")

    in_flight.sort(key=_ts, reverse=True)
    completed.sort(key=_ts, reverse=True)

    active_ptr = ""
    active_path = root / "ACTIVE"
    if active_path.is_file():
        try:
            active_ptr = active_path.read_text(encoding="utf-8").strip()
        except OSError:
            active_ptr = ""

    idle = _read_json_obj(root / "IDLE-REASON.json") or {}
    current: dict[str, Any] | None = None
    if active_ptr:
        for card in in_flight:
            if card.get("run_id") == active_ptr:
                current = dict(card)
                current["source"] = "ACTIVE"
                break
        if current is None:
            run_file = runs / f"{active_ptr}.json"
            data = _read_json_obj(run_file)
            if data:
                current = _factory_pack_card(data, path=run_file)
                current["source"] = "ACTIVE"
    if current is None and idle.get("active_run"):
        for card in in_flight:
            if card.get("run_id") == idle.get("active_run"):
                current = dict(card)
                current["source"] = "IDLE-REASON"
                break
    if current is None:
        for card in in_flight:
            if card.get("stage") == "ACTIVE":
                current = dict(card)
                current["source"] = "stage"
                break
    if current is None and in_flight:
        current = dict(in_flight[0])
        current["source"] = "newest_in_flight"

    current_id = (current or {}).get("run_id")
    queued = [
        c
        for c in in_flight
        if c.get("run_id") != current_id
        and c.get("stage") in ("WAITING_CURSOR", "WAITING_GROK", "IN_FLIGHT", "BUILDING")
    ][:8]
    # Also surface GROK_REVIEW backlog briefly (not the whole eng queue)
    grok_queue = [
        c
        for c in in_flight
        if c.get("run_id") != current_id and c.get("stage") == "GROK_REVIEW"
    ][:5]
    for g in grok_queue:
        if g not in queued and all(g.get("run_id") != q.get("run_id") for q in queued):
            queued.append(g)
    queued = queued[:8]

    blocked_human: list[dict[str, Any]] = []
    parked = idle.get("parked") if isinstance(idle.get("parked"), list) else []
    for label in parked:
        text = str(label or "").strip()
        if not text:
            continue
        low = text.lower()
        if "devi" in low or "habitat" in low:
            blocked_human.append(
                {
                    "branch": text,
                    "status": "PARKED",
                    "source": "IDLE-REASON.parked",
                }
            )
    # Compressed sprint flags that explicitly park Devi / Habitat waits
    compressed = _read_json_obj(root / "COMPRESSED-SPRINT-2-ARMED.json") or {}
    if compressed.get("no_wait_devi") and not any(
        "devi" in str(b.get("branch") or "").lower() for b in blocked_human
    ):
        blocked_human.append(
            {
                "branch": "Devi",
                "status": "PARKED_BY_SPRINT",
                "source": "COMPRESSED-SPRINT-2-ARMED.no_wait_devi",
            }
        )
    if compressed.get("no_wait_habitat") and not any(
        "habitat" in str(b.get("branch") or "").lower() for b in blocked_human
    ):
        blocked_human.append(
            {
                "branch": "Habitat",
                "status": "PARKED_BY_SPRINT",
                "source": "COMPRESSED-SPRINT-2-ARMED.no_wait_habitat",
            }
        )

    last_advance: dict[str, Any] | None = None
    ticks_path = root / "supervisor-ticks.jsonl"
    if ticks_path.is_file():
        try:
            lines = [
                ln.strip()
                for ln in ticks_path.read_text(encoding="utf-8").splitlines()
                if ln.strip()
            ]
            if lines:
                tick = json.loads(lines[-1])
                if isinstance(tick, dict):
                    last_advance = {
                        "at": tick.get("at"),
                        "action": tick.get("action") or tick.get("next_action"),
                        "run_id": tick.get("run_id"),
                        "stage": tick.get("stage"),
                        "source": "supervisor-ticks",
                    }
        except (OSError, json.JSONDecodeError):
            last_advance = None
    if last_advance is None and completed:
        last_advance = {
            "at": completed[0].get("updated_at"),
            "action": "PACK_DONE",
            "run_id": completed[0].get("run_id"),
            "stage": completed[0].get("stage"),
            "source": "recent_completed",
        }

    mission_ptr = ""
    mission_path = root / "ACTIVE_MISSION"
    if mission_path.is_file():
        try:
            mission_ptr = mission_path.read_text(encoding="utf-8").strip()
        except OSError:
            mission_ptr = ""

    in_flight_count = len(in_flight)
    return {
        "ok": True,
        "in_flight_count": in_flight_count,
        "in_flight_stages": dict(stage_counts),
        "active_pointer": active_ptr or None,
        "active_mission": mission_ptr or None,
        "current_active_pack": current,
        "queued_packs": queued,
        "recently_completed": completed[:5],
        "blocked_human_branches": blocked_human,
        "last_factory_advance": last_advance,
        "idle_reason": (idle.get("reason") if idle else None),
    }


def project_open_loops_with_factory(
    loops: dict[str, Any],
    factory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Combine completion-register IN_PROGRESS with factory in-flight lanes.

    Silent zero while factory is ACTIVE / WAITING_CURSOR / GROK_REVIEW / IN_FLIGHT
    is a projection lie — either count factory work or mark PROJECTION STALE.
    Does not invent SYSTEM%.
    """
    out = dict(loops or {})
    fac = factory if isinstance(factory, dict) else factory_work_surface()
    reg_ip = int(out.get("in_progress") or 0)
    fac_ip = int(fac.get("in_flight_count") or 0)
    projected = reg_ip + fac_ip
    stale = bool(fac_ip > 0 and projected < 1)
    if stale:
        # Unreachable when fac_ip is counted correctly; keep as honesty backstop.
        projected = max(projected, 1)

    out["register_in_progress"] = reg_ip
    out["factory_in_flight"] = fac_ip
    out["in_progress"] = projected
    out["projection_stale"] = stale
    if stale:
        out["projection_stale_label"] = "PROJECTION STALE"
        out["projection_note"] = (
            "Factory in-flight lanes present but In progress could not be projected"
        )
    else:
        out["projection_note"] = (
            "In progress = completion-register IN_PROGRESS + factory in-flight lanes"
            if fac_ip
            else "In progress from completion register (no factory in-flight)"
        )
    out["factory_work"] = {
        "current_active_pack": fac.get("current_active_pack"),
        "queued_packs": fac.get("queued_packs") or [],
        "recently_completed": fac.get("recently_completed") or [],
        "blocked_human_branches": fac.get("blocked_human_branches") or [],
        "last_factory_advance": fac.get("last_factory_advance"),
        "in_flight_count": fac_ip,
        "active_mission": fac.get("active_mission"),
        "idle_reason": fac.get("idle_reason"),
    }
    return out


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
    """LEGACY Master_Build weighted mix — retained as history only.

    Not the Owner primary dial. Primary is SYSTEM from the Model C ledger
    (compute_system_from_ledger). Do not render this as current progress.
    """
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
        "legacy": True,
        "retired_as_primary": True,
        "legacy_note": (
            "LEGACY BUILD-TRACKER ESTIMATE — retired as Owner primary dial. "
            "Kept for history; primary is SYSTEM from Model C ledger."
        ),
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
    """Derive waiting class. SPECIFIED/IDEA/APPROVED → PLANNED (not policy).

    UNAPPROVED_POLICY only when the row already carries that class (curated
    overlay / vertical flag) — never auto-mapped from lifecycle alone.
    """
    if item.get("waiting_class"):
        return item["waiting_class"]
    lc = _norm_lifecycle(item.get("lifecycle") or "")
    if item.get("live"):
        return None
    if lc in ("SPECIFIED", "APPROVED", "IDEA"):
        return "PLANNED"
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

# Completion-register drill keys. Empire is the unfiltered owner summary.
# Needs Matt stays NEEDS_MATT only — counted in completion_register, not here.
REGISTER_VIEW_KEY: dict[str, str | None] = {
    "Empire": None,
    "Wolf Core": "Core",
    "GGV": "GGV",
    "AMG": "AMG",
    "BZG": "BZG",
    "Intelligence": "Intelligence",
    "Integrations": "Integrations",
    "Sale Readiness": "Sale Readiness",
    "Build Factory": "Factory",
    "Backlog": "Backlog",
}


def calculation_english() -> dict[str, Any]:
    weight_line = (
        "LEGACY domain weights (CURATED, labelled ESTIMATED; Factory health EXCLUDED): "
        "Core ~26%, GGV ~21%, BZG ~16%, AMG ~16%, Intelligence ~11%, "
        "Integrations ~5%, Sale Readiness ~5% (prior ratios ÷0.95 after removing Factory 5%)."
    )
    return {
        "title": "How is this calculated?",
        "progress_type": "SYSTEM_FROM_LEDGER",
        "steps": [
            "PRIMARY — SYSTEM% = SUM(Model C maturity credits) / 77 × 100, computed on every read "
            "from state/model-c-baseline-assessments.json. Credits: ABSENT 0 · SPECIFIED 0.05 · "
            "BUILT 0.25 · PROVEN 0.80 · READY 1.00. Round half-up to one decimal. Never store the %.",
            "If ledger row count ≠ 77, or ledger/read-model/HTML projection disagree → "
            "SCORING_PROJECTION_STALE and no percentage is shown.",
            "Model E list is five unscored dials (Operating Adoption … Sale Readiness) — "
            "SYSTEM% is the owner headline only; no interim 0% pretends to be a score.",
            "Factory health is separate system status ∈ {HEALTHY, DEGRADED, FAILING} — not SYSTEM maturity.",
            "LEGACY (retired as primary): Master_Build CSV + overlay mix produced a PARTIAL ESTIMATE "
            "(history note: prior display about twenty-eight percent as retired build-tracker estimate). "
            "Kept in code for history only.",
            weight_line,
            "LEGACY tracked capability denominator: Core 18 · GGV 3 · BZG 2 · AMG 1 · "
            "Intelligence 2 · Integrations 5 · Sale Readiness 61 · total 92.",
            "Core % = maturity of tracked approved Core capabilities in Master_Build+overlay "
            "(item_count denominator) — NOT all imaginable Wolf Core forever.",
            "LEGACY per-capability maturity from lifecycle (not file count): IDEA/SPECIFIED=0.05 · APPROVED=0.15 · "
            "BUILDING=0.35 · BETA/SCHEMA_BUILT/TESTED=0.55 · PILOT=0.7 · VERIFIED=0.85 · LIVE=1.0 · RETIRED=n/a.",
            "Commissioning penalty: if BUILT/TESTED but HUMAN_COMMISSIONING ≠ DONE → score capped at 0.65 (BUILT ≠ LIVE).",
            "WAITING class: SPECIFIED/IDEA/APPROVED → PLANNED. UNAPPROVED_POLICY only from curated "
            "policy_decisions[] (or explicit row flags) — not every not-yet-built capability.",
            "Human commissioning missions are curated evidence lists (needs_you / waiting_on_others) — "
            "not every built Core row. Core is proven through verticals; no Matt-per-primitive commission queue.",
            f"Prior mission % with Factory weight was ~{PRIOR_MISSION_PCT_WITH_FACTORY}%; "
            "recompute excludes Factory and re-normalizes — do not inflate to look good.",
            "Builder honesty: primary=SYSTEM from ledger · legacy PARTIAL_ESTIMATE retained · "
            "overlay still used for Owner pulse · Factory excluded from SYSTEM%.",
        ],
        "honesty": {
            "progress_type": "SYSTEM_FROM_LEDGER",
            "legacy_progress_type": "PARTIAL_ESTIMATE",
            "master_build_csv_staleness": "KNOWN",
            "overlay_required": True,
            "no_fake_precision": True,
            "peaches_recommendation_is_not_approved": True,
            "factory_excluded_from_mission_pct": True,
            "denominator_model_c_capabilities": 77,
            "denominator_tracked_capabilities_legacy": 92,
        },
        "distinctions": [
            "BUILT ≠ HUMAN_COMMISSIONED ≠ LIVE",
            "WAITING_HUMAN ≠ BLOCKED_SYSTEM ≠ UNAPPROVED_POLICY ≠ INACCESSIBLE_SOURCE ≠ PLANNED",
            "TARGET profit ≠ ACTUAL (ACTUAL NOT YET TRUSTWORTHY)",
            "SYSTEM is a projection of the ledger — never a manually copied percentage",
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
    """Natural-English owner phase — foundations + first GGV/BZG workflows; commissioning underway."""
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
            bits.append("Uma closer still needed for first verified close")
        if met_locked:
            bits.append("Habitat publish write still locked")
        mid = (
            "Foundations and first GGV/BZG workflows are on Beta; "
            "human commissioning is underway; AMG and company ops still ahead"
        )
        if bits:
            return f"{mid} ({'; '.join(bits)})"
        return mid
    if overall_pct < 40:
        return (
            f"Mid-build — Core and first verticals advancing "
            f"(~{overall_pct}% PARTIAL ESTIMATE)"
        )
    return (
        f"Empire roughly {overall_pct}% (PARTIAL ESTIMATE) — "
        "commission, live ops, and buyer-ready still open"
    )


def _status_chips(all_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Status vocabulary legend — no fake exclusive aggregate counts on Empire hero.

    Counts stay in technical_details only; hero chips omit count so BUILT/HUMAN
    TESTING/WAITING are not shown as if mutually exclusive buckets.
    """
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
    planned_n = sum(1 for i in all_items if i.get("waiting_class") == "PLANNED")
    human_testing_n = sum(
        1 for i in all_items if i.get("built") and not i.get("commissioned") and not i.get("live")
    )
    # hero=True chips are vocabulary only (no count displayed)
    return [
        {
            "id": "BUILT",
            "label": "BUILT",
            "count": built_n,
            "show_count": False,
            "tooltip": "Code/schema exists on Beta. BUILT ≠ COMMISSIONED ≠ LIVE.",
        },
        {
            "id": "HUMAN_TESTING",
            "label": "HUMAN TESTING",
            "count": human_testing_n,
            "show_count": False,
            "tooltip": "Built paths awaiting human walkthrough / commission. Not LIVE. Overlaps BUILT.",
        },
        {
            "id": "LIVE",
            "label": "LIVE",
            "count": live_n,
            "show_count": False,
            "tooltip": "Commissioned and operating live. Rare until human commission DONE.",
        },
        {
            "id": "WAITING",
            "label": "WAITING",
            "count": waiting_n,
            "show_count": False,
            "tooltip": "WAITING_HUMAN or BLOCKED_SYSTEM — not the same as policy gap.",
        },
        {
            "id": "PLANNED",
            "label": "PLANNED",
            "count": planned_n,
            "show_count": False,
            "tooltip": "SPECIFIED/IDEA/APPROVED — tracked but not a policy decision queue.",
        },
        {
            "id": "POLICY_NEEDED",
            "label": "POLICY",
            "count": policy_n,
            "show_count": False,
            "tooltip": "Curated UNAPPROVED_POLICY only — see Policy decisions cards. ≠ every SPECIFIED row.",
        },
        {
            "id": "COMMISSIONED",
            "label": "COMMISSIONED",
            "count": commissioned_n,
            "show_count": False,
            "tooltip": "HUMAN_COMMISSIONING=DONE. Hidden from hero chips by default.",
            "hero": False,
        },
    ]


def _build_policy_decisions(
    overlay: dict[str, Any],
    verticals: dict[str, Any],
) -> list[dict[str, Any]]:
    """Individual policy decision cards — never a giant inflated count."""
    curated = overlay.get("policy_decisions")
    out: list[dict[str, Any]] = []
    if isinstance(curated, list) and curated:
        for p in curated:
            if not isinstance(p, dict):
                continue
            out.append(
                {
                    "id": p.get("id") or "",
                    "title": _owner_text_clean(str(p.get("title") or p.get("text") or "")),
                    "note": _owner_text_clean(str(p.get("note") or "")),
                    "owner": p.get("owner") or "Owner",
                    "status": p.get("status") or "UNAPPROVED_POLICY",
                    "source": p.get("source"),
                    "as_of": p.get("as_of"),
                    "confidence": p.get("confidence") or "CURATED",
                }
            )
        return out
    # Fallback from vertical flags if overlay omits the list
    uma = verticals.get("uma_close") or {}
    if uma.get("variance_policy") == "NOT_CONFIGURED":
        out.append(
            {
                "id": "POL-UMA-VARIANCE",
                "title": "Uma Blu cash variance threshold",
                "note": "NOT_CONFIGURED — policy gap, not a system failure",
                "owner": "Owner",
                "status": "UNAPPROVED_POLICY",
                "source": uma.get("source") or "docs/canon/UMA-BLU-DAILY-CLOSE.md",
                "as_of": uma.get("as_of"),
                "confidence": "DERIVED",
            }
        )
    return out


def _is_example_pulse_line(text: str) -> bool:
    t = (text or "").strip()
    return (
        t.startswith("Example —")
        or t.startswith("Example -")
        or t.startswith("Example:")
    )


def _blob_forces_class(blob: str) -> str | None:
    """OPENING BALANCE and CLOSER never auto-land as Matt tasks."""
    u = (blob or "").upper()
    if (
        "OPENING BALANCE" in u
        or "FLOAT NOT_FOUND" in u
        or "FLOAT NOT FOUND" in u
    ):
        return "NEEDS_POLICY"
    if "CLOSER REQUIRED" in u or "WAITING_FOR_CLOSER" in u:
        return "NEEDS_STAFF"
    return None


def _safe_operating_issues() -> list[dict[str, Any]]:
    try:
        from core import uma_ops_console as uoc

        payload = uoc.list_issues()
    except Exception:  # noqa: BLE001
        return []
    if not isinstance(payload, dict):
        return []
    rows = payload.get("issues") or []
    return [i for i in rows if isinstance(i, dict)]


def _human_exception_title(label: str, why: str) -> str:
    title = (label or "").strip()
    if not title or title.startswith(
        ("PR-", "PETTY-", "WI-", "PERS-", "EVD-", "ENT-", "DEC-", "ASG-")
    ):
        return why or "Issue"
    return title


def bucket_owner_exceptions(
    issues: list[dict[str, Any]] | None,
) -> dict[str, list[dict[str, Any]]]:
    """Four owner buckets from operating issues. example:true never enters.

    Needs You is only NEEDS_MATT. Opening-float and closer blockers are forced
    out of that panel even if a caller marked them NEEDS_MATT.
    """
    from core.blocker_explain import (
        WHY_CLOSER,
        WHY_OPENING_FLOAT,
        explain_operating_blocker,
    )

    out: dict[str, list[dict[str, Any]]] = {
        "needs_you": [],
        "needs_staff": [],
        "needs_policy": [],
        "needs_external_access": [],
    }
    for iss in issues or []:
        if not isinstance(iss, dict) or iss.get("example"):
            continue
        label = str(iss.get("label") or iss.get("title") or "")
        if label.startswith("Example —") or label.startswith("Example -"):
            continue
        kind = str(iss.get("kind") or "")
        explained = explain_operating_blocker(
            kind,
            {
                "label": label,
                "opening_float_status": iss.get("opening_float_status"),
                "question": iss.get("question"),
                "scope": iss.get("scope"),
                "surface": iss.get("surface"),
                "actor_context": iss.get("actor_context"),
                "resolve": iss.get("resolve"),
            },
        )
        classification = str(explained.get("classification") or "")
        why = str(explained.get("why") or iss.get("why") or "")
        forced = _blob_forces_class(f"{kind} {label} {why}")
        if forced:
            classification = forced
            if forced == "NEEDS_POLICY" and (
                kind in ("opening_balance_required", "float_not_found")
                or "FLOAT" in label.upper()
                or "OPENING BALANCE" in label.upper()
            ):
                why = WHY_OPENING_FLOAT
            if forced == "NEEDS_STAFF" and (
                "CLOSER" in f"{kind} {label}".upper()
                or kind.upper() == "WAITING_FOR_CLOSER"
            ):
                why = WHY_CLOSER
        key = {
            "NEEDS_MATT": "needs_you",
            "NEEDS_STAFF": "needs_staff",
            "NEEDS_POLICY": "needs_policy",
            "NEEDS_EXTERNAL_ACCESS": "needs_external_access",
        }.get(classification)
        if not key:
            continue
        card: dict[str, Any] = {
            "title": _human_exception_title(label, why),
            "why": why,
            "note": why,
            "classification": classification,
            "example": False,
        }
        href = iss.get("href")
        if href:
            card["href"] = href
        status = explained.get("status") or (iss.get("explain") or {}).get("status")
        if status:
            card["status"] = status
        out[key].append(card)
    return out


def owner_pulse_lines_from_issues(
    issues: list[dict[str, Any]] | None,
) -> list[str]:
    """Non-example issue lines only. Example rows never feed Owner Pulse."""
    lines: list[str] = []
    for iss in issues or []:
        if not isinstance(iss, dict) or iss.get("example"):
            continue
        label = str(iss.get("label") or "").strip()
        if _is_example_pulse_line(label) or label.startswith("Example"):
            continue
        why = str(iss.get("why") or "").strip()
        if not why:
            continue
        lines.append(f"{label}: {why}" if label else why)
    return lines


def _build_commissioning_missions(
    overlay: dict[str, Any],
    issues: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Curated missions plus Uma issues.

    Needs You = NEEDS_MATT (bucket NEEDS_YOU maps to Matt). Parallel buckets
    hold staff / policy / external-access exceptions. Example issues excluded.
    """
    missions = overlay.get("commissioning_missions") or []
    needs_you: list[dict[str, Any]] = []
    waiting_on_others: list[dict[str, Any]] = []
    needs_staff: list[dict[str, Any]] = []
    needs_policy: list[dict[str, Any]] = []
    needs_external: list[dict[str, Any]] = []
    for m in missions:
        if not isinstance(m, dict):
            continue
        if m.get("example"):
            continue
        bucket = str(m.get("bucket") or "").upper()
        status = str(m.get("status") or "WAITING").upper()
        if not bucket:
            bucket = "NEEDS_YOU" if status == "ACTIVE" else "WAITING_ON_OTHERS"
        card = {
            "id": m.get("id") or "",
            "title": _owner_text_clean(str(m.get("title") or m.get("text") or "")),
            "who": _owner_text_clean(str(m.get("who") or "")),
            "note": _owner_text_clean(str(m.get("note") or "")),
            "status": status,
            "bucket": bucket,
            "source": m.get("source"),
            "as_of": m.get("as_of"),
            "confidence": m.get("confidence") or "CURATED",
        }
        forced = _blob_forces_class(f"{card['title']} {card['note']}")
        if bucket == "NEEDS_YOU" and forced:
            card["classification"] = forced
            card["bucket"] = forced
            card["why"] = card["note"]
            if forced == "NEEDS_POLICY":
                needs_policy.append(card)
            else:
                needs_staff.append(card)
            continue
        if bucket == "NEEDS_YOU":
            card["classification"] = "NEEDS_MATT"
            needs_you.append(card)
        else:
            waiting_on_others.append(card)

    extra = bucket_owner_exceptions(
        issues if issues is not None else _safe_operating_issues()
    )
    needs_you.extend(extra["needs_you"])
    needs_staff.extend(extra["needs_staff"])
    needs_policy.extend(extra["needs_policy"])
    needs_external.extend(extra["needs_external_access"])
    needs_you = [
        m
        for m in needs_you
        if not m.get("example") and m.get("classification") in (None, "", "NEEDS_MATT")
    ]
    return {
        "needs_you": needs_you,
        "waiting_on_others": waiting_on_others,
        "needs_staff": needs_staff,
        "needs_policy": needs_policy,
        "needs_external_access": needs_external,
    }


def _build_owner_pulse(
    overlay: dict[str, Any],
    factory_health: dict[str, Any],
    verticals: dict[str, Any],
    missions: dict[str, list[dict[str, Any]]] | None = None,
    policy_decisions: list[dict[str, Any]] | None = None,
    issues: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cockpit = overlay.get("owner_cockpit") or {}
    pulse = dict(cockpit.get("owner_pulse") or {})
    pulse["build_system"] = {
        "factory": factory_health.get("status"),
        "production": "UNTOUCHED",
        "note": factory_health.get("note"),
    }
    for key in ("working_now", "waiting_on_people", "policy_data_needed"):
        if key not in pulse or not isinstance(pulse[key], list):
            pulse[key] = []
    # Strip any invented Matt Core governance commission language
    def _not_fake_core(text: str) -> bool:
        t = (text or "").lower()
        return not (
            "matt human commission of built core" in t
            or "commission core governance" in t
            or "core governance slices" in t and "commission" in t
        )

    pulse["waiting_on_people"] = [x for x in pulse["waiting_on_people"] if _not_fake_core(str(x))]
    pulse["working_now"] = [x for x in pulse["working_now"] if _not_fake_core(str(x))]

    # Prefer curated mission titles when pulse lists empty
    missions = missions or {"needs_you": [], "waiting_on_others": []}
    if not pulse["waiting_on_people"]:
        for m in missions.get("waiting_on_others") or []:
            who = m.get("who") or ""
            title = m.get("title") or ""
            pulse["waiting_on_people"].append(
                f"{title}" + (f" — {who}" if who else "")
            )
    if not pulse["policy_data_needed"]:
        for p in policy_decisions or []:
            pulse["policy_data_needed"].append(
                f"{p.get('title')}" + (f" — {p.get('note')}" if p.get("note") else "")
            )
    if not pulse["working_now"]:
        for m in missions.get("needs_you") or []:
            pulse["working_now"].append(
                f"{m.get('title')}" + (f" ({m.get('status')})" if m.get("status") else "")
            )
        if not pulse["working_now"]:
            pulse["working_now"].append("Progress Dashboard UX commissioning on Beta")
    pulse["source"] = pulse.get("source") or cockpit.get("source") or str(
        OVERLAY_PATH.relative_to(BETA_ROOT)
    )
    pulse["as_of"] = pulse.get("as_of") or cockpit.get("as_of") or overlay.get("as_of")
    pulse["confidence"] = pulse.get("confidence") or cockpit.get("confidence") or "CURATED"
    # Example fixtures must not feed Owner Pulse.
    banned = []
    for iss in issues or []:
        if isinstance(iss, dict) and iss.get("example"):
            lab = str(iss.get("label") or "").strip()
            if lab:
                banned.append(lab)
    for key in ("working_now", "waiting_on_people", "policy_data_needed"):
        pulse[key] = [
            x
            for x in (pulse.get(key) or [])
            if not _is_example_pulse_line(str(x))
            and not any(b and b in str(x) for b in banned)
        ]
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
        text = _owner_text_clean(str(m.get("text") or ""))
        # Never surface invented Matt Core governance commission as a next move
        tl = text.lower()
        if "commission core governance" in tl or (
            "core governance" in tl and "commission" in tl
        ):
            continue
        cls = str(m.get("class") or "RECOMMENDED").upper()
        if cls not in ("ACTIVE", "WAITING", "RECOMMENDED", "APPROVED"):
            cls = "RECOMMENDED"
        moves.append(
            {
                "text": text,
                "class": cls,
                "note": _owner_text_clean(str(m.get("note") or "")),
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


def open_loops_summary(
    *,
    db_path: Path | None = None,
    view_key: str | None = None,
    factory_root: Path | None = None,
    factory_runs_dir: Path | None = None,
    include_factory: bool = True,
) -> dict[str, Any]:
    """Owner Open Loops from completion register + factory in-flight projection."""
    import sys

    scripts_dir = str(Path(__file__).resolve().parents[1])
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from core import completion_register as _cr

    base = _cr.summary_for_owner(db_path=db_path, view_key=view_key)
    if not include_factory:
        return base
    factory = factory_work_surface(
        factory_root=factory_root,
        runs_dir=factory_runs_dir,
    )
    return project_open_loops_with_factory(base, factory)


def build_read_model(
    *,
    overlay_path: Path | None = None,
    ledger_path: Path | None = None,
    integrity_against_path: Path | None = None,
    history_path: Path | None = None,
    catalog_path: Path | None = None,
    html_path: Path | None = None,
    register_db_path: Path | None = None,
    factory_root: Path | None = None,
    factory_runs_dir: Path | None = None,
    sale_csv_path: Path | None = None,
) -> dict[str, Any]:
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
    sale = sale_readiness_items(csv_path=sale_csv_path)
    factory = factory_health_items(runs_dir=factory_runs_dir)
    backlog = backlog_items()
    factory_work = factory_work_surface(
        factory_root=factory_root,
        runs_dir=factory_runs_dir,
    )

    # Mission-scored items EXCLUDE factory (LEGACY overall)
    all_scored = merged + integ + sale
    card = domain_scorecard(all_scored)
    overall = overall_from_card(card)
    reconcile = reconcile_prior(overall["overall_pct"], overlay)

    # PRIMARY — SYSTEM from Model C ledger (computed every read; never hard-coded)
    system_raw = compute_system_from_ledger(ledger_path)
    integrity = assess_scoring_integrity(
        system_raw,
        ledger_path=ledger_path or Path(system_raw["ledger_path"]),
        integrity_against_path=integrity_against_path,
        html_path=html_path,
    )
    system = apply_integrity_to_system(system_raw, integrity)
    system_detail = system_detail_from_ledger(
        ledger_path,
        catalog_path=catalog_path,
        history_path=history_path,
    )
    model_e = model_e_dials(system)
    bzg_pulse = bzg_operational_pulse()

    verticals = overlay.get("verticals") or {}
    achievements = overlay.get("achievements") or []
    factory_health = assess_factory_health(factory)

    for it in all_scored + backlog + factory:
        wc = waiting_class_for(it)
        if wc:
            it["waiting_class"] = wc

    owner_phase = _derive_owner_phase(card, overall["overall_pct"], verticals)
    status_chips = _status_chips(all_scored)
    operating_issues = _safe_operating_issues()
    missions = _build_commissioning_missions(overlay, operating_issues)
    policy_decisions = _build_policy_decisions(overlay, verticals)
    needs_you = missions["needs_you"]
    waiting_on_others = missions["waiting_on_others"]
    needs_staff = missions.get("needs_staff") or []
    needs_policy = missions.get("needs_policy") or []
    needs_external_access = missions.get("needs_external_access") or []
    try:
        from core.content_engine_repair import read_library_exceptions

        library_preview_exceptions = read_library_exceptions()
    except Exception:  # noqa: BLE001
        library_preview_exceptions = {
            "ok": False,
            "count": 0,
            "items": [],
            "note": "Preview exceptions could not be read.",
            "staff_ready": False,
            "read_only": True,
            "human_commissioned": False,
        }
    try:
        from core import owner_commissioning_queue as _ocq

        my_commissioning = _ocq.build_for_progress()
    except Exception as _ocq_exc:  # noqa: BLE001
        my_commissioning = {
            "ok": False,
            "error": str(_ocq_exc)[:200],
            "cards": [],
            "active_cards": [],
            "counters": {},
            "honesty": {
                "proven": False,
                "ready": False,
                "invented_human_commissioned": False,
            },
        }
    owner_pulse = _build_owner_pulse(
        overlay,
        factory_health,
        verticals,
        missions,
        policy_decisions,
        operating_issues,
    )
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
                "system": system,
                "system_detail": system_detail,
                "model_e": model_e,
                "bzg_pulse": bzg_pulse,
                "owner_phase": owner_phase,
                "status_chips": [c for c in status_chips if c.get("hero", True)],
                "needs_you": needs_you,
                "needs_staff": needs_staff,
                "needs_policy": needs_policy,
                "needs_external_access": needs_external_access,
                "library_preview_exceptions": library_preview_exceptions,
                "waiting_on_others": waiting_on_others,
                "my_commissioning": my_commissioning,
                "policy_decisions": policy_decisions,
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
                    "reconcile": reconcile,
                    "legacy_overall": overall,
                    "honesty": {
                        "progress_type": "SYSTEM_FROM_LEDGER",
                        "legacy_progress_type": "PARTIAL_ESTIMATE",
                        "master_build_csv_staleness": overlay.get(
                            "master_build_csv_staleness", "KNOWN"
                        ),
                        "overlay_required": True,
                    },
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
        elif view_name == "AMG":
            items = [i for i in all_scored if i.get("domain") == "AMG"]
            views[view_name] = {
                "view": view_name,
                "pct": card["AMG"]["pct"],
                "plain_phase": card["AMG"]["plain_phase"],
                "biggest_gap": card["AMG"]["biggest_gap"],
                "visual_pct": card["AMG"]["visual_pct"],
                "items": items,
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
                "bzg_pulse": bzg_pulse,
                "items": items,
                "uma_close": verticals.get("uma_close"),
                "links": {"bzg": "/bzg", "uma_blu": "/bzg/uma-blu"},
            }
        elif view_name == "Build Factory":
            views[view_name] = {
                "view": view_name,
                "factory_health": factory_health,
                "items": factory,
                "note": "Factory health is system status — excluded from SYSTEM maturity %.",
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

    loop_cache: dict[tuple[str | None, bool], dict[str, Any]] = {}

    def loops_for(view_name: str) -> dict[str, Any]:
        key = REGISTER_VIEW_KEY.get(view_name)
        include_factory = view_name == "Empire"
        cache_key = (key, include_factory)
        if cache_key not in loop_cache:
            loop_cache[cache_key] = open_loops_summary(
                db_path=register_db_path,
                view_key=key,
                factory_root=factory_root,
                factory_runs_dir=factory_runs_dir,
                include_factory=include_factory,
            )
        return loop_cache[cache_key]

    for view_name, payload in views.items():
        payload["open_loops"] = loops_for(view_name)
        if view_name == "Empire":
            payload["factory_work"] = factory_work
    open_loops = loops_for("Empire")

    primary_menu = [n["label"] for n in PRIMARY_NAV]

    return {
        "ok": True,
        "generated_at": now_iso(),
        "progress_type": "SYSTEM_FROM_LEDGER",
        "legacy_progress_type": "PARTIAL_ESTIMATE",
        "master_build_csv_staleness": overlay.get(
            "master_build_csv_staleness", "KNOWN"
        ),
        "overlay_required": True,
        "system": system,
        "system_detail": system_detail,
        "model_e": model_e,
        "bzg_pulse": bzg_pulse,
        "overall": overall,  # LEGACY — not primary
        "reconcile": reconcile,
        "owner_phase": owner_phase,
        "status_chips": [c for c in status_chips if c.get("hero", True)],
        "needs_you": needs_you,
        "needs_staff": needs_staff,
        "needs_policy": needs_policy,
        "needs_external_access": needs_external_access,
        "library_preview_exceptions": library_preview_exceptions,
        "waiting_on_others": waiting_on_others,
        "my_commissioning": my_commissioning,
        "policy_decisions": policy_decisions,
        "owner_pulse": owner_pulse,
        "next_moves": next_moves,
        "recent_wins": recent_wins,
        "milestone_road": milestone_road,
        "open_loops": open_loops,
        "factory_work": factory_work,
        "factory_health": factory_health,
        "domain_weights": {
            d: {"weight": w, "label": "ESTIMATED", "pct_display": WEIGHT_PCT_DISPLAY.get(d)}
            for d, w in DOMAIN_WEIGHTS.items()
        },
        "domains": owner_domains,
        "views": views,
        "menu": primary_menu,
        "nav": list(PRIMARY_NAV),
        "menu_all_views": list(VIEWS),
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
            "SYSTEM_IS_LEDGER_PROJECTION": True,
        },
        "technical_details": {
            "raw_domain_items": {d: card[d]["items"] for d in DOMAIN_WEIGHTS},
            "factory_items": factory,
            "legacy_overall": overall,
        },
    }


def get_view(
    name: str,
    *,
    overlay_path: Path | None = None,
    register_db_path: Path | None = None,
) -> dict[str, Any]:
    model = build_read_model(
        overlay_path=overlay_path,
        register_db_path=register_db_path,
    )
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
        "system": model["system"],
        "model_e": model["model_e"],
        "overall": model["overall"],
        "reconcile": model["reconcile"],
        "owner_phase": model["owner_phase"],
        "factory_health": model["factory_health"],
        "calculation": model["calculation"],
        "view": model["views"][resolved],
        "menu": model["menu"],
        "nav": model["nav"],
        "default_view": model["default_view"],
    }


def honesty_flags() -> dict[str, Any]:
    flags = {
        "progress_type": "SYSTEM_FROM_LEDGER",
        "legacy_progress_type": "PARTIAL_ESTIMATE",
        "master_build_csv_staleness": "KNOWN",
        "overlay_required": True,
        "owner_only": True,
        "person_gate": PERS_MATT,
        "built_ne_commissioned_ne_live": True,
        "factory_excluded_from_mission_pct": True,
        "system_is_ledger_projection": True,
        "no_esb_writes": True,
        "no_metricool_writes": True,
        "no_habitat_planner_mutations": True,
        "no_production_writes": True,
        "proven": False,
        "ready": False,
        "invented_human_commissioned": False,
        "human_commissioned_requires_submit_evidence": True,
        "clickup_retired": True,
        "telegram_retired": True,
        "owner_commissioning_bound": "beta-owner-commissioning-safe",
    }
    return flags


if __name__ == "__main__":
    print(json.dumps(build_read_model(), indent=2, default=str)[:5000])
