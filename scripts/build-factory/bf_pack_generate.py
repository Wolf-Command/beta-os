#!/usr/bin/env python3
"""Continuous compressed pack generation from OPEN CR + architecture.

Decision served: 2026-09-22 Sprint 2 P5 Owner Disappear + Pack Gen
(docs/deliveries/GROK-PLAN-SPRINT2-P5-OWNER-PACKGEN-2026-09-22.md /
docs/deliveries/GROK-GAP-ATTACK-SPRINT-2-2026-09-22.md §7),
under state/build-factory/COMPRESSED-SPRINT-2-ARMED.json
(continuous_pack_generation / no_ask_matt_invent_pack).

Bound: beta-factory-packgen-safe

Factory script only (parallel-safe vs serve-heavy packs). Reads OPEN
NEEDS_ENGINEERING CRs, clusters coherent safe work, safety-validates,
writes a vertical pack plan + lane proposal, and Peaches veto gate file
PACK-PROPOSAL-LATEST.json. Auto-accept only when safety_ok and bound known.

Refuses FIN/HR/Trading. Blocks NEEDS_POLICY / unknown policy and continues
elsewhere. No money/CF/Production/external write. No invent PROVEN/READY.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path("/Users/wolfterminal/beta-os").resolve()
sys.path.insert(0, str(ROOT / "scripts"))

from core import completion_register as cr  # noqa: E402
from core import founder_dep_routing as fdr  # noqa: E402

BOUND = "beta-factory-packgen-safe"
SCHEMA_ID = "wolf.bf-pack-generate.v1"
BF = ROOT / "state" / "build-factory"
PROPOSAL_PATH = BF / "PACK-PROPOSAL-LATEST.json"
DELIVERIES = ROOT / "docs" / "deliveries"
TZ8 = timezone(timedelta(hours=8))

# --- CREDIT CONSERVATION GATE (Owner 2026-09-23) ---
# Reads state/build-factory/CREDIT-CONSERVATION.json + GATE-credit-conservation-20260923.json.
# If enabled and proposed pack is operator-depth|management-depth|connective breadth
# without credit_value_gate pass → PEACHES_VETO_CREDIT_CONSERVATION (do not arm).
# Exception: allow_finish_run_id / exception_run_ids (MSC in flight) may finish.
CREDIT_CONSERVATION_PATH = BF / "CREDIT-CONSERVATION.json"
CREDIT_GATE_PATH = BF / "GATE-credit-conservation-20260923.json"
BREADTH_PACK_CLASSES = frozenset(
    {
        "operator-depth",
        "management-depth",
        "connective",
        "operator_depth",
        "management_depth",
    }
)

# Known safe bounds the factory may auto-accept. Unknown → veto pending.
KNOWN_BOUNDS = frozenset(
    {
        "beta-factory-packgen-safe",
        "beta-bzg-loop-safe",
        "beta-ggv-loop-safe",
        "beta-amg-day-safe",
        "beta-intel-connect-safe",
        "beta-staff-ready-safe",
        "beta-derive-prove-safe",
        "beta-connective-safe",
        "beta-owner-safe",
        "beta-core-safe",
        "beta-harmless",
        "beta-harmless-prove",
    }
)

RESERVED_CAP_PREFIXES = ("CAP-FIN-", "CAP-HR-")
RESERVED_DOMAIN_TOKENS = frozenset(
    {"finance", "fin ", " hr", "hr ", "hris", "trading", "payroll", "zayen"}
)

ARCHITECTURE_POINTERS = (
    "docs/canon/WOLF-COMMAND-MASTER-SPECIFICATION.md",
    "docs/MODEL-C-CAPABILITY-CATALOG.md",
    "docs/deliveries/COMPRESSED-SPRINT-DEPENDENCY-GRAPH-2026-09-21.md",
    "docs/deliveries/GROK-GAP-ATTACK-SPRINT-2-2026-09-22.md",
    "state/build-factory/COMPRESSED-SPRINT-2-ARMED.json",
)

# Affirmative unsafe intent only — refusal catalogs ("MUST NOT … Production")
# must not trip the scanner.
UNSAFE_PLAN_PATTERNS = (
    re.compile(r"\bwrite\s+to\s+production\b", re.I),
    re.compile(r"\bmutate\s+production\b", re.I),
    re.compile(r"\bexternal[-_ ]write\b", re.I),
    re.compile(r"\bcloudflare\s+access\s+include\b", re.I),
    re.compile(r"\b(execute|approve)\s+(payment|money|transfer)\b", re.I),
    re.compile(r"\bbank\s+transfer\b", re.I),
    re.compile(r"\btrading\s+live\b", re.I),
    re.compile(r"\binvent\s+(proven|ready)\b", re.I),
    re.compile(r"\bpromote\s+to\s+(proven|ready)\b", re.I),
    re.compile(r"\bpayment_approve\b", re.I),
)

# Domain family → preferred bound for proposed next pack
FAMILY_BOUNDS = {
    "BZG": "beta-bzg-loop-safe",
    "GGV": "beta-ggv-loop-safe",
    "AMG": "beta-amg-day-safe",
    "INTEL": "beta-intel-connect-safe",
    "CORE": "beta-core-safe",
    "CRM": "beta-ggv-loop-safe",
    "INTG": "beta-connective-safe",
    "MSC": "beta-core-safe",
    "STRAT": "beta-owner-safe",
    "PROC": "beta-connective-safe",
    "DR": "beta-core-safe",
    "SALE": "beta-connective-safe",
    "MIXED": "beta-factory-packgen-safe",
}

MAX_CLUSTER = 6


class PackGenError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def now_wita() -> str:
    return datetime.now(TZ8).strftime("%Y-%m-%d %H:%M WITA")


def _cap_family(capability: str | None) -> str:
    cap = (capability or "").strip().upper()
    m = re.match(r"^CAP-([A-Z]+)-\d+", cap)
    if m:
        return m.group(1)
    return "OTHER"


def is_reserved_row(row: dict[str, Any]) -> bool:
    cap = str(row.get("capability") or "").upper()
    for prefix in RESERVED_CAP_PREFIXES:
        if cap.startswith(prefix):
            return True
    blob = " ".join(
        str(row.get(k) or "")
        for k in ("domain", "title", "next_action", "dependency", "capability")
    ).lower()
    if "trading" in blob:
        return True
    for tok in RESERVED_DOMAIN_TOKENS:
        if tok.strip() and tok in f" {blob} ":
            # careful: 'fin ' / ' hr' style — also match CAP already handled
            if tok in ("finance", "hris", "payroll", "zayen", "trading"):
                return True
    # Explicit CAP-FIN / CAP-HR already covered; domain label Finance/HR
    domain = str(row.get("domain") or "").upper()
    if "D-FIN" in domain or "D-HR" in domain or "FINANCE" in domain:
        if "CAP-FIN" in cap or "CAP-HR" in cap or "D-FIN" in domain or "D-HR" in domain:
            return True
    return False


def is_policy_blocked(row: dict[str, Any]) -> bool:
    """Unknown / policy requirements block this branch; generator continues elsewhere."""
    blocker = str(row.get("blocker_class") or "").upper()
    if blocker == "NEEDS_POLICY":
        return True
    next_action = str(row.get("next_action") or "").lower()
    dependency = str(row.get("dependency") or "").lower()
    blob = f"{next_action} {dependency}"
    if "unknown policy" in blob or "needs policy" in blob or "policy required" in blob:
        return True
    if "needs_matt" in blob and "policy" in blob:
        return True
    return False


def load_architecture_pointers(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    found: list[dict[str, Any]] = []
    missing: list[str] = []
    for rel in ARCHITECTURE_POINTERS:
        path = base / rel
        entry = {"path": rel, "present": path.is_file()}
        if path.is_file():
            entry["bytes"] = path.stat().st_size
            found.append(entry)
        else:
            missing.append(rel)
    return {
        "ok": True,
        "pointers": found,
        "missing": missing,
        "dependency_graph": "docs/deliveries/COMPRESSED-SPRINT-DEPENDENCY-GRAPH-2026-09-21.md",
        "master_spec": "docs/canon/WOLF-COMMAND-MASTER-SPECIFICATION.md",
        "why": "Approved architecture / Master Spec / dependency graph pointers only — not invented.",
    }


def load_open_engineering_crs(
    conn: Any,
    *,
    include_reserved: bool = False,
) -> dict[str, Any]:
    """Read OPEN NEEDS_ENGINEERING. Default excludes FIN/HR/Trading reserved."""
    rows = cr.list_open(conn, blocker_class="NEEDS_ENGINEERING")
    # Also surface NEEDS_POLICY so we can block-branch them explicitly
    policy_rows = cr.list_open(conn, blocker_class="NEEDS_POLICY")

    eligible: list[dict[str, Any]] = []
    reserved: list[dict[str, Any]] = []
    policy_blocked: list[dict[str, Any]] = []

    for row in rows:
        if is_policy_blocked(row):
            policy_blocked.append(_slim(row, reason="policy_blocked"))
            continue
        if is_reserved_row(row):
            reserved.append(_slim(row, reason="reserved_fin_hr_trading"))
            if include_reserved:
                eligible.append(row)
            continue
        eligible.append(row)

    for row in policy_rows:
        policy_blocked.append(_slim(row, reason="needs_policy"))

    return {
        "ok": True,
        "eligible": eligible,
        "reserved_excluded": reserved,
        "policy_blocked": policy_blocked,
        "counts": {
            "eligible": len(eligible),
            "reserved_excluded": len(reserved),
            "policy_blocked": len(policy_blocked),
            "engineering_open_raw": len(rows),
        },
    }


def _slim(row: dict[str, Any], *, reason: str) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "capability": row.get("capability"),
        "title": row.get("title"),
        "blocker_class": row.get("blocker_class"),
        "reason": reason,
    }


def cluster_crs(rows: list[dict[str, Any]], *, max_size: int = MAX_CLUSTER) -> dict[str, Any]:
    """Cluster coherent related safe work by CAP family into one vertical pack."""
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        fam = _cap_family(row.get("capability"))
        by_family.setdefault(fam, []).append(row)

    # Prefer largest coherent family that has a known bound (ops loops first)
    priority = ("BZG", "GGV", "AMG", "INTEL", "CORE", "CRM", "INTG", "MSC", "STRAT", "PROC", "DR", "SALE")
    ordered_families = [f for f in priority if f in by_family] + [
        f for f in sorted(by_family) if f not in priority
    ]
    if not ordered_families:
        return {
            "ok": False,
            "reason": "no_eligible_crs",
            "family": None,
            "members": [],
            "bound": None,
        }

    family = ordered_families[0]
    members = by_family[family][:max_size]
    bound = FAMILY_BOUNDS.get(family, BOUND)
    return {
        "ok": True,
        "family": family,
        "members": members,
        "member_ids": [m.get("id") for m in members],
        "capabilities": [m.get("capability") for m in members],
        "bound": bound,
        "other_families_deferred": {
            f: len(by_family[f]) for f in ordered_families[1:]
        },
        "why": f"Largest coherent safe family={family}; deferred families continue later.",
    }


def validate_safety(
    cluster: dict[str, Any],
    *,
    plan_text: str = "",
    known_bounds: frozenset[str] | None = None,
) -> dict[str, Any]:
    """No money/CF/prod/external write/fake maturity. Bound must be known for auto-accept."""
    known = known_bounds or KNOWN_BOUNDS
    reasons: list[str] = []
    bound = str(cluster.get("bound") or "")

    if not cluster.get("ok"):
        reasons.append(cluster.get("reason") or "cluster_failed")

    for row in cluster.get("members") or []:
        if is_reserved_row(row):
            reasons.append(f"reserved_in_cluster:{row.get('id')}")
        if is_policy_blocked(row):
            reasons.append(f"policy_in_cluster:{row.get('id')}")

    # Scan actionable body only — drop "## MUST NOT" refusal catalog so
    # listing forbidden acts does not look like proposing them.
    scan_text = plan_text or ""
    if "## MUST NOT" in scan_text:
        scan_text = scan_text.split("## MUST NOT", 1)[0]
    for pat in UNSAFE_PLAN_PATTERNS:
        if pat.search(scan_text):
            reasons.append(f"unsafe_token:{pat.pattern}")

    # Refuse invent maturity language as a claim in the pack plan
    if re.search(
        r"\b(now proven|now ready|promote to proven|promote to ready)\b",
        scan_text,
        re.I,
    ):
        reasons.append("fake_maturity")

    bound_known = bound in known
    if bound and not bound_known:
        reasons.append(f"unknown_bound:{bound}")

    # Bound guard via bf_queue tokens when available
    try:
        sys.path.insert(0, str(ROOT / "scripts" / "build-factory"))
        import bf_queue as bq  # noqa: WPS433

        g = bq.guard_lane_bound(bound)
        if not g.get("allowed"):
            reasons.append(g.get("reason") or "bound_guard_refused")
    except Exception:  # noqa: BLE001
        pass

    safety_ok = len(reasons) == 0 and bool(cluster.get("ok")) and bound_known
    return {
        "safety_ok": safety_ok,
        "bound": bound,
        "bound_known": bound_known,
        "reasons": reasons,
        "money": False,
        "cloudflare": False,
        "production": False,
        "external_write": False,
        "fake_maturity": "fake_maturity" not in reasons,
        "fin_hr_trading": False,
    }


def render_pack_plan_markdown(
    cluster: dict[str, Any],
    *,
    architecture: dict[str, Any],
    founder_deps: dict[str, Any],
    safety: dict[str, Any],
    stamp: str,
) -> str:
    family = cluster.get("family") or "MIXED"
    bound = cluster.get("bound") or BOUND
    members = cluster.get("members") or []
    lines = [
        f"# GROK PLAN — Auto Pack Gen — {family} Cluster — {stamp[:10]}",
        "",
        f"- Generated: {stamp}",
        f"- Generator: `scripts/build-factory/bf_pack_generate.py`",
        f"- Bound: `{bound}`",
        f"- Class: CONTINUOUS PACK PROPOSAL (Beta only) — Matt invent not required",
        f"- safety_ok: `{safety.get('safety_ok')}`",
        "",
        "## Why this pack",
        "",
        "Factory IDLE after Sprint1 A–F required Matt/Grok to invent the next bound.",
        "This plan is clustered from OPEN CR NEEDS_ENGINEERING + approved architecture pointers.",
        "",
        "## Architecture pointers",
        "",
    ]
    for p in architecture.get("pointers") or []:
        lines.append(f"- `{p['path']}` ({p.get('bytes', 0)} B)")
    if architecture.get("missing"):
        lines.append("")
        lines.append("Missing (not invented):")
        for m in architecture["missing"]:
            lines.append(f"- `{m}`")
    lines.extend(
        [
            "",
            "## Clustered OPEN NEEDS_ENGINEERING (safe)",
            "",
            "| CR | Capability | Next action |",
            "|----|------------|-------------|",
        ]
    )
    for row in members:
        na = str(row.get("next_action") or "").replace("|", "/")[:80]
        lines.append(
            f"| `{row.get('id')}` | `{row.get('capability')}` | {na} |"
        )
    lines.extend(
        [
            "",
            "## Founder dependency classification",
            "",
            f"- Implemented E/A/A routing labels: **{founder_deps.get('counts', {}).get('implemented_eaa', 0)}**",
            f"- Classify-only (SIMPLIFY/RETAIN): **{founder_deps.get('counts', {}).get('classified_only', 0)}**",
            f"- Blocked reserved: **{founder_deps.get('counts', {}).get('blocked_reserved', 0)}**",
            "- Honesty: no invent Owner controls away.",
            "",
            "## MUST NOT",
            "",
            "- Production / money move / CF Access Include / external write",
            "- FIN / HR / Trading reserved architectures",
            "- Invent PROVEN / READY / COMMISSIONED / ADOPTED",
            "- False-resolve any CR",
            "",
            "## Acceptance",
            "",
            "- Pack plan + lane proposal written without Matt invent",
            "- Peaches veto gate: auto-accept only if safety_ok and bound known",
            "- Reserved / policy branches blocked; other families continue",
            "",
            f"Bound: `{bound}`",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def propose_lane_json(
    cluster: dict[str, Any],
    *,
    plan_rel: str,
    safety: dict[str, Any],
    mission_id: str = "compressed-sprint-2-20260922",
) -> dict[str, Any]:
    family = (cluster.get("family") or "mixed").lower()
    stamp = datetime.now(TZ8).strftime("%Y%m%d")
    lane_id = f"auto-pack-{family}-{stamp}"
    return {
        "mission_id": mission_id,
        "lane": {
            "id": lane_id,
            "bound": cluster.get("bound") or BOUND,
            "status": "PENDING" if safety.get("safety_ok") else "BLOCKED",
            "stage": "GROK_PLAN",
            "track": "AUTO",
            "plan": plan_rel,
            "family": cluster.get("family"),
            "cr_ids": cluster.get("member_ids") or [],
            "capabilities": cluster.get("capabilities") or [],
            "parallel_group": "factory-parallel",
            "priority": 3,
            "generated_by": "bf_pack_generate",
            "matt_invent_required": False,
            "block_reason": None
            if safety.get("safety_ok")
            else ",".join(safety.get("reasons") or ["safety_failed"]),
        },
        "propose_only": True,
        "why": "Lane JSON proposed for mission; Peaches veto gate decides accept.",
    }




def load_credit_conservation(base: Path | None = None) -> dict[str, Any]:
    """Load CREDIT-CONSERVATION + GATE. Fail-open to disabled if files missing."""
    root_bf = (base or ROOT) / "state" / "build-factory" if base else BF
    mode_path = root_bf / "CREDIT-CONSERVATION.json"
    gate_path = root_bf / "GATE-credit-conservation-20260923.json"
    mode: dict[str, Any] = {}
    gate: dict[str, Any] = {}
    if mode_path.exists():
        try:
            mode = json.loads(mode_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            mode = {}
    if gate_path.exists():
        try:
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            gate = {}
    enabled = bool(mode.get("enabled")) or bool(gate.get("enabled"))
    return {
        "enabled": enabled,
        "mode": mode,
        "gate": gate,
        "veto_code": (
            mode.get("veto_code")
            or gate.get("veto_code")
            or "PEACHES_VETO_CREDIT_CONSERVATION"
        ),
        "allow_finish_run_id": mode.get("allow_finish_run_id"),
        "exception_run_ids": list(gate.get("exception_run_ids") or []),
        "veto_if_pack_class_in": list(
            gate.get("veto_if_pack_class_in") or sorted(BREADTH_PACK_CLASSES)
        ),
        "heavy_pack_gate": mode.get("heavy_pack_gate") or "credit_value_gate_v1",
        "credit_value_gate_pass": bool(mode.get("credit_value_gate_pass")),
    }


def classify_pack_breadth(
    *,
    cluster: dict[str, Any] | None = None,
    lane_proposal: dict[str, Any] | None = None,
    plan_rel: str = "",
    bound: str = "",
) -> str | None:
    """Return breadth pack class if this proposal is operator/management/connective."""
    cluster = cluster or {}
    lane_proposal = lane_proposal or {}
    lane = lane_proposal.get("lane") if isinstance(lane_proposal.get("lane"), dict) else {}
    hay = " ".join(
        str(x or "")
        for x in (
            plan_rel,
            bound or cluster.get("bound") or "",
            cluster.get("family"),
            lane.get("id"),
            lane.get("track"),
            lane.get("slice"),
            lane.get("bound"),
            " ".join(str(c) for c in (lane.get("capabilities") or [])),
        )
    ).lower()
    if "operator-depth" in hay or "operator_depth" in hay:
        return "operator-depth"
    if "management-depth" in hay or "management_depth" in hay:
        return "management-depth"
    if (
        "connective" in hay
        or "ops-needs-you-connective" in hay
        or (bound or cluster.get("bound") or "").lower() == "beta-connective-safe"
    ):
        return "connective"
    return None


def credit_conservation_veto(
    *,
    cluster: dict[str, Any] | None = None,
    lane_proposal: dict[str, Any] | None = None,
    plan_rel: str = "",
    proposed_run_id: str | None = None,
    base: Path | None = None,
) -> dict[str, Any]:
    """CREDIT_CONSERVATION_GATE_V1 — veto breadth auto-arm when conservation enabled."""
    cc = load_credit_conservation(base)
    if not cc["enabled"]:
        return {"veto": False, "enabled": False}
    pack_class = classify_pack_breadth(
        cluster=cluster,
        lane_proposal=lane_proposal,
        plan_rel=plan_rel,
        bound=(cluster or {}).get("bound") or "",
    )
    if not pack_class:
        return {
            "veto": False,
            "enabled": True,
            "pack_class": None,
            "reason": "not_breadth_class",
        }
    exceptions = set(cc["exception_run_ids"])
    if cc.get("allow_finish_run_id"):
        exceptions.add(cc["allow_finish_run_id"])
    if proposed_run_id and proposed_run_id in exceptions:
        return {
            "veto": False,
            "enabled": True,
            "pack_class": pack_class,
            "reason": "exception_allow_finish",
            "run_id": proposed_run_id,
        }
    if pack_class not in set(cc["veto_if_pack_class_in"]) | BREADTH_PACK_CLASSES:
        return {
            "veto": False,
            "enabled": True,
            "pack_class": pack_class,
            "reason": "class_not_in_veto_list",
        }
    if cc.get("credit_value_gate_pass"):
        return {
            "veto": False,
            "enabled": True,
            "pack_class": pack_class,
            "reason": "credit_value_gate_pass",
        }
    return {
        "veto": True,
        "enabled": True,
        "pack_class": pack_class,
        "veto_code": cc["veto_code"],
        "reason": "breadth_without_credit_value_gate",
        "heavy_pack_gate": cc["heavy_pack_gate"],
    }

def write_proposal_gate(
    *,
    cluster: dict[str, Any],
    safety: dict[str, Any],
    plan_rel: str,
    lane_proposal: dict[str, Any],
    founder_deps: dict[str, Any],
    architecture: dict[str, Any],
    selection: dict[str, Any],
    path: Path | None = None,
) -> dict[str, Any]:
    """Peaches veto gate. Auto-accept only if safety_ok and bound known."""
    out_path = path or PROPOSAL_PATH
    auto_accept = bool(safety.get("safety_ok")) and bool(safety.get("bound_known"))
    cc_veto = credit_conservation_veto(
        cluster=cluster,
        lane_proposal=lane_proposal,
        plan_rel=plan_rel,
    )
    veto_status = "AUTO_ACCEPTED" if auto_accept else "PENDING_PEACHES_VETO"
    if cc_veto.get("veto"):
        auto_accept = False
        veto_status = cc_veto.get("veto_code") or "PEACHES_VETO_CREDIT_CONSERVATION"
    proposal = {
        "schema": SCHEMA_ID,
        "at": now_iso(),
        "wita": now_wita(),
        "bound": cluster.get("bound") or BOUND,
        "bound_known": safety.get("bound_known"),
        "safety_ok": safety.get("safety_ok"),
        "safety": safety,
        "auto_accepted": auto_accept,
        "veto_status": veto_status,
        "credit_conservation": cc_veto,
        "require_matt": False,
        "plan": plan_rel,
        "lane_proposal": lane_proposal,
        "cluster": {
            "family": cluster.get("family"),
            "member_ids": cluster.get("member_ids"),
            "capabilities": cluster.get("capabilities"),
            "other_families_deferred": cluster.get("other_families_deferred"),
        },
        "selection_counts": selection.get("counts"),
        "policy_blocked": selection.get("policy_blocked"),
        "reserved_excluded": selection.get("reserved_excluded"),
        "architecture": {
            "pointers": [p["path"] for p in architecture.get("pointers") or []],
            "missing": architecture.get("missing") or [],
        },
        "founder_deps": {
            "counts": founder_deps.get("counts"),
            "invented_owner_control_away": False,
        },
        "honesty": {
            "money": False,
            "cloudflare": False,
            "production": False,
            "fin_hr_trading": False,
            "invented_proven": False,
            "invented_ready": False,
            "matt_invent_required": False,
        },
        "why": (
            (
                f"{veto_status}: breadth pack_class={cc_veto.get('pack_class')} "
                "blocked under CREDIT CONSERVATION (Owner 2026-09-23); "
                "PARK unless credit_value_gate_pass or P0/P1."
            )
            if cc_veto.get("veto")
            else (
                "Auto-accept only when safety_ok and bound known. "
                "Otherwise Peaches veto. Matt invent not required."
            )
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
    proposal["path"] = str(out_path.relative_to(ROOT)) if out_path.is_relative_to(ROOT) else str(out_path)
    return proposal


def generate_pack(
    *,
    db_path: Path | str | None = None,
    root: Path | None = None,
    write_files: bool = True,
    deliveries_dir: Path | None = None,
    proposal_path: Path | None = None,
    mission_id: str = "compressed-sprint-2-20260922",
) -> dict[str, Any]:
    """Full pipeline: CR → architecture → cluster → safety → plan → lane → veto gate."""
    base = root or ROOT
    deliveries = deliveries_dir or (base / "docs" / "deliveries")
    stamp = now_iso()

    conn = cr.db_connect(db_path)
    try:
        selection = load_open_engineering_crs(conn)
    finally:
        conn.close()

    architecture = load_architecture_pointers(base)
    cluster = cluster_crs(selection["eligible"])
    founder_deps = fdr.build_routing_read_model(cluster.get("members") or [])

    # Draft plan text for safety scan before write
    draft_md = render_pack_plan_markdown(
        cluster,
        architecture=architecture,
        founder_deps=founder_deps,
        safety={"safety_ok": False},
        stamp=stamp,
    )
    safety = validate_safety(cluster, plan_text=draft_md)

    plan_rel = None
    plan_path = None
    if write_files and cluster.get("ok"):
        family = (cluster.get("family") or "mixed").lower()
        day = datetime.now(TZ8).strftime("%Y-%m-%d")
        fname = f"GROK-PLAN-AUTO-PACK-{family.upper()}-CLUSTER-{day}.md"
        plan_path = deliveries / fname
        final_md = render_pack_plan_markdown(
            cluster,
            architecture=architecture,
            founder_deps=founder_deps,
            safety=safety,
            stamp=stamp,
        )
        # Re-validate with final text
        safety = validate_safety(cluster, plan_text=final_md)
        if write_files:
            deliveries.mkdir(parents=True, exist_ok=True)
            plan_path.write_text(final_md, encoding="utf-8")
            try:
                plan_rel = str(plan_path.relative_to(base))
            except ValueError:
                plan_rel = str(plan_path)
    elif cluster.get("ok"):
        plan_rel = f"docs/deliveries/GROK-PLAN-AUTO-PACK-{(cluster.get('family') or 'MIXED').upper()}-CLUSTER-DRY.md"

    lane_proposal = propose_lane_json(
        cluster,
        plan_rel=plan_rel or "",
        safety=safety,
        mission_id=mission_id,
    )

    proposal = None
    if write_files:
        proposal = write_proposal_gate(
            cluster=cluster,
            safety=safety,
            plan_rel=plan_rel or "",
            lane_proposal=lane_proposal,
            founder_deps=founder_deps,
            architecture=architecture,
            selection=selection,
            path=proposal_path or (base / "state" / "build-factory" / "PACK-PROPOSAL-LATEST.json"),
        )

    return {
        "ok": True,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "generated_at": stamp,
        "selection": {
            "counts": selection["counts"],
            "reserved_excluded": selection["reserved_excluded"],
            "policy_blocked": selection["policy_blocked"],
        },
        "architecture": architecture,
        "cluster": {
            "ok": cluster.get("ok"),
            "family": cluster.get("family"),
            "bound": cluster.get("bound"),
            "member_ids": cluster.get("member_ids"),
            "capabilities": cluster.get("capabilities"),
            "other_families_deferred": cluster.get("other_families_deferred"),
            "reason": cluster.get("reason"),
        },
        "founder_deps": founder_deps,
        "safety": safety,
        "plan": plan_rel,
        "lane_proposal": lane_proposal,
        "proposal_gate": {
            "path": proposal.get("path") if proposal else None,
            "auto_accepted": proposal.get("auto_accepted") if proposal else None,
            "veto_status": proposal.get("veto_status") if proposal else None,
            "safety_ok": safety.get("safety_ok"),
            "bound_known": safety.get("bound_known"),
        },
        "matt_invent_required": False,
        "honesty": {
            "invented_proven": False,
            "invented_ready": False,
            "money": False,
            "production": False,
            "fin_hr_trading_included": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate next compressed pack from CR")
    parser.add_argument("--db", default=None, help="Override completion register DB")
    parser.add_argument("--dry-run", action="store_true", help="Do not write plan/proposal files")
    parser.add_argument("--json", action="store_true", help="Print full JSON result")
    parser.add_argument("--mission", default="compressed-sprint-2-20260922")
    args = parser.parse_args(argv)

    result = generate_pack(
        db_path=args.db,
        write_files=not args.dry_run,
        mission_id=args.mission,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        c = result["cluster"]
        g = result["proposal_gate"]
        print(
            f"family={c.get('family')} bound={c.get('bound')} "
            f"members={len(c.get('member_ids') or [])} "
            f"safety_ok={result['safety'].get('safety_ok')} "
            f"veto={g.get('veto_status')} "
            f"plan={result.get('plan')} "
            f"matt_invent={result.get('matt_invent_required')}"
        )
        print(
            f"eligible={result['selection']['counts']['eligible']} "
            f"reserved={result['selection']['counts']['reserved_excluded']} "
            f"policy_blocked={result['selection']['counts']['policy_blocked']}"
        )
    return 0 if result.get("ok") and result["cluster"].get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
