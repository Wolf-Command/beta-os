#!/usr/bin/env python3
"""Founder-dependency classification + safe E/A/A routing read-model.

Decision served: 2026-09-22 Sprint 2 P5 Owner Disappear + Pack Gen
(docs/deliveries/GROK-PLAN-SPRINT2-P5-OWNER-PACKGEN-2026-09-22.md),
under COMPRESSED-SPRINT-2-ARMED continuous_pack_generation.

Bound: beta-factory-packgen-safe

Classifies founder dependencies as ELIMINATE / AUTOMATE / AUGMENT /
SIMPLIFY / RETAIN. Implements only safe E/A/A as read-models + routing
labels — never invents Owner controls away. FIN/HR/Trading refused.
No money, CF, Production, or maturity invent.
"""
from __future__ import annotations

import re
from typing import Any

BOUND = "beta-factory-packgen-safe"
SCHEMA_ID = "wolf.founder-dep-routing.v1"

CLASSES = frozenset(
    {"ELIMINATE", "AUTOMATE", "AUGMENT", "SIMPLIFY", "RETAIN"}
)
# Safe to surface as routing labels (not control removal).
SAFE_IMPLEMENT = frozenset({"ELIMINATE", "AUTOMATE", "AUGMENT"})

RESERVED_CAP_PREFIXES = ("CAP-FIN-", "CAP-HR-")
RESERVED_TOKENS = frozenset(
    {
        "trading",
        "finance",
        "payroll",
        "hris",
        "bank",
        "payment",
        "folio",
        "zayen",
        "cloudflare",
        "production",
    }
)

# Signals that a dependency is accidental founder interrupt vs intentional authority.
_ELIMINATE_HINTS = re.compile(
    r"\b(needs.?matt|matt invent|owner invent|pick next pack|idle.?reason|"
    r"switchboard|triage for owner|founder interrupt)\b",
    re.I,
)
_AUTOMATE_HINTS = re.compile(
    r"\b(auto.?advance|deterministic|machine.?generat|factory|pack.?gen|"
    r"without matt|no.?human pick|continuous)\b",
    re.I,
)
_AUGMENT_HINTS = re.compile(
    r"\b(owner.?only|authority|approval|veto|policy|delegation|"
    r"intentional|commission)\b",
    re.I,
)
_SIMPLIFY_HINTS = re.compile(
    r"\b(simplify|collapse|merge desk|reduce surface)\b",
    re.I,
)
_RETAIN_HINTS = re.compile(
    r"\b(retain|keep owner|must.?not.?agent|matt.?only|cf access|"
    r"monetary authority|owner control)\b",
    re.I,
)


class FounderDepError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def refuse_reserved(text: str | None) -> None:
    blob = (text or "").lower()
    for tok in RESERVED_TOKENS:
        if tok in blob:
            raise FounderDepError(
                f"Founder-dep routing refuses reserved domain: {tok}",
                code="reserved_refused",
            )
    upper = (text or "").upper()
    for prefix in RESERVED_CAP_PREFIXES:
        if prefix in upper:
            raise FounderDepError(
                f"Founder-dep routing refuses reserved capability: {prefix}",
                code="reserved_refused",
            )


def classify_text(text: str, *, has_staff_seat: bool = True) -> dict[str, Any]:
    """Classify one dependency string. Honesty first — never fake ELIMINATE."""
    refuse_reserved(text)
    blob = text or ""
    label = "AUGMENT"
    reason = "Default AUGMENT: Owner still in the loop until a safer class proves out."

    if _RETAIN_HINTS.search(blob):
        label = "RETAIN"
        reason = "Intentional Owner control — retain; do not invent away."
    elif _SIMPLIFY_HINTS.search(blob) and not _AUTOMATE_HINTS.search(blob):
        label = "SIMPLIFY"
        reason = "Surface can shrink, but not auto-routed away yet."
    elif _ELIMINATE_HINTS.search(blob) and has_staff_seat:
        label = "ELIMINATE"
        reason = "Accidental founder interrupt with a staff seat — route away from Owner."
    elif _ELIMINATE_HINTS.search(blob) and not has_staff_seat:
        label = "AUGMENT"
        reason = "Would be ELIMINATE but no staff seat — honesty keeps AUGMENT."
    elif _AUTOMATE_HINTS.search(blob):
        label = "AUTOMATE"
        reason = "System can do this without a human pick."
    elif _AUGMENT_HINTS.search(blob):
        label = "AUGMENT"
        reason = "Owner still needed; label is honesty, not removal."

    assert label in CLASSES
    return {
        "class": label,
        "reason": reason,
        "safe_implement": label in SAFE_IMPLEMENT,
        "invented_owner_control_away": False,
        "text_excerpt": blob[:160],
    }


def classify_cr_row(row: dict[str, Any], *, has_staff_seat: bool = True) -> dict[str, Any]:
    """Classify one completion-register row. Reserved caps refuse."""
    cap = str(row.get("capability") or "")
    title = str(row.get("title") or "")
    next_action = str(row.get("next_action") or "")
    dependency = str(row.get("dependency") or "")
    domain = str(row.get("domain") or "")
    blob = " | ".join([cap, title, next_action, dependency, domain])
    refuse_reserved(blob)
    classified = classify_text(blob, has_staff_seat=has_staff_seat)
    return {
        "cr_id": row.get("id"),
        "capability": cap or None,
        "class": classified["class"],
        "reason": classified["reason"],
        "safe_implement": classified["safe_implement"],
        "invented_owner_control_away": False,
        "routing": _routing_for(classified["class"], cap, row),
    }


def _routing_for(label: str, cap: str, row: dict[str, Any]) -> dict[str, Any]:
    """Safe E/A/A become routing cards. S/R stay classified only."""
    href = _href_for_cap(cap)
    if label not in SAFE_IMPLEMENT:
        return {
            "implemented": False,
            "kind": "classify_only",
            "href": href,
            "why": f"{label} is classified but not auto-routed (no invent Owner controls away).",
        }
    return {
        "implemented": True,
        "kind": "read_model_route",
        "href": href,
        "seat_hint": _seat_hint(cap),
        "why": (
            f"{label} surfaced as routing label only — Owner desk is not removed."
        ),
        "next_action": row.get("next_action"),
    }


def _href_for_cap(cap: str) -> str | None:
    c = (cap or "").upper()
    if c.startswith("CAP-BZG-"):
        return "/bzg/uma-blu"
    if c.startswith("CAP-GGV-") or c.startswith("CAP-CRM-"):
        return "/ggv-ops-pack"
    if c.startswith("CAP-AMG-"):
        return "/amg-ops-pack"
    if c.startswith("CAP-INTEL-"):
        return "/intel-ops-pack"
    if c.startswith("CAP-STRAT-") or c.startswith("CAP-CORE-"):
        return "/owner-empire-pack"
    return None


def _seat_hint(cap: str) -> str | None:
    c = (cap or "").upper()
    if c.startswith("CAP-BZG-"):
        return "PERS-DEVI"
    if c.startswith("CAP-GGV-") or c.startswith("CAP-CRM-"):
        return "PERS-AMANDA"
    if c.startswith("CAP-AMG-"):
        return "WAITING_ASSIGNMENT"
    if c.startswith("CAP-STRAT-") or c.startswith("CAP-CORE-") or c.startswith("CAP-INTEL-"):
        return "PERS-MATT"
    return None


def build_routing_read_model(
    rows: list[dict[str, Any]],
    *,
    staff_seats: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Read-model of founder deps. Skips reserved rows (block branch, continue)."""
    seats = staff_seats or {
        "PERS-DEVI": True,
        "PERS-AMANDA": True,
        "PERS-HAIKAL": True,
        "PERS-MISA": True,
    }
    implemented: list[dict[str, Any]] = []
    classified_only: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []

    for row in rows:
        cap = str(row.get("capability") or "")
        seat = _seat_hint(cap)
        has_seat = True
        if seat == "WAITING_ASSIGNMENT":
            has_seat = False
        elif seat and seat.startswith("PERS-"):
            has_seat = bool(seats.get(seat, False))
        try:
            item = classify_cr_row(row, has_staff_seat=has_seat)
        except FounderDepError as exc:
            blocked.append(
                {
                    "cr_id": row.get("id"),
                    "capability": cap or None,
                    "blocked": True,
                    "reason": exc.code,
                    "message": str(exc),
                }
            )
            continue
        if item["safe_implement"]:
            implemented.append(item)
        else:
            classified_only.append(item)

    return {
        "ok": True,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "implemented_eaa": implemented,
        "classified_only": classified_only,
        "blocked_reserved": blocked,
        "counts": {
            "implemented_eaa": len(implemented),
            "classified_only": len(classified_only),
            "blocked_reserved": len(blocked),
        },
        "invented_owner_control_away": False,
        "money": None,
        "trading": False,
        "finance": False,
        "hr": False,
        "why": (
            "Safe ELIMINATE/AUTOMATE/AUGMENT are routing labels only. "
            "SIMPLIFY/RETAIN stay classified. Reserved domains are blocked, not invented."
        ),
    }


def label_for_pack_handoff(pack_id: str, attention_count: int | None) -> dict[str, Any]:
    """Attach founder-dep label to an Empire pack handoff card."""
    pid = (pack_id or "").upper()
    if pid == "BZG":
        has_seat = True
        text = "Uma ops switchboard — route to Devi seat when attention exists"
        if isinstance(attention_count, int) and attention_count > 0:
            text = "needs matt invent? no — staff seat Devi can take Uma Today attention"
    elif pid == "GGV":
        has_seat = True
        text = "GGV ops continuous next-action routing to Amanda seat"
    elif pid == "AMG":
        has_seat = False
        text = "AMG desk — waiting assignment; owner augment until hotel-ops seat exists"
    else:
        has_seat = False
        text = "Owner authority retain"
    classified = classify_text(text, has_staff_seat=has_seat)
    return {
        "founder_dep_class": classified["class"],
        "founder_dep_reason": classified["reason"],
        "safe_implement": classified["safe_implement"],
        "invented_owner_control_away": False,
    }
