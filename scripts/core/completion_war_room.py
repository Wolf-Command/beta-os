#!/usr/bin/env python3
"""Finish war room — read model over the canonical 77 ledger.

Decision served: owner brief 27 Sep 2026, PACK 5. Not a second task
system. Not a new approval store. Wolf Core tables are not written.
The maturity ledger is not written here.

SYSTEM maturity stays on state/model-c-baseline-assessments.json.
Staff readiness, human commissioning, and operating adoption stay off
that score. READY is not commissioned and is not adoption.

Priority rule W3-P5-PRIORITY-v1 (first match wins; it does not read
the maturity state):

1. P0 — must exist for Wolf to operate. The control kernel
   CAP-CORE-01 through CAP-CORE-10, plus the two boundaries without
   which that kernel cannot be used safely: CAP-MSC-02 (Access seats)
   and CAP-INTG-07 (Dev/Beta/Prod separation). Factors: operational
   dependency, and safety/control risk on the two boundaries.
2. P1 — required for business operation or founder independence.
   Founder machinery (CAP-CORE-11, CAP-CORE-12, CAP-STRAT-02), the
   daily loops for GGV, AMG, and BZG, the minimum money picture,
   people master, payroll inputs, and the connectors those loops name
   as prerequisites (Yanolja, ESB, bank files). Factors: founder
   dependency, staff usability, financial importance, prerequisites.
3. P2 — can follow initial commissioning. Remaining catalog
   capabilities that are real operating depth, a later adoption, or
   sale readiness, and were not required above.
4. P3 — future. Catalog capabilities that are observe/derive or
   buyer-only and are not the first operating loop. Sale readiness
   is P2, not P3: the factor counts, and it can follow commissioning.

The sets are closed, disjoint, and cover the catalog. A capability
that matches none is an error, not a silent P3.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from core.dashboard_truth import public_text
from core.progress_read_model import (
    MODEL_C_CATALOG,
    MODEL_C_LEDGER,
    SYSTEM_MATURITY_CREDITS,
    compute_system_from_ledger,
    load_catalog_cap_domains,
)

BETA_ROOT = Path(__file__).resolve().parents[2]
COMMISSIONING_PATH = (
    BETA_ROOT / "state" / "completion-register" / "COMMISSIONING-STATE-20260927.json"
)
DEPLOYED_PROOF_PATH = (
    BETA_ROOT / "state" / "completion-register" / "DEPLOYED-ROUTE-PROOF-20260927.json"
)

RULE_ID = "W3-P5-PRIORITY-v1"
STATES = ("ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY")
PRIORITIES = ("P0", "P1", "P2", "P3")
EFFORT = {
    "ABSENT": "XL",
    "SPECIFIED": "L",
    "BUILT": "M",
    "PROVEN": "S",
    "READY": "none",
}
WHY = {
    "P0": "Wolf cannot enforce or refuse an action without this.",
    "P1": "A daily operating loop, the money picture, or founder independence depends on this.",
    "P2": "This can follow the first commissioning. It is not the kernel and not the first daily loop.",
    "P3": "This is later work. It is not required for the first operating loop.",
}

# Closed sets. Order inside a set is not priority order.
P0_OPERATE = frozenset(
    {
        "CAP-CORE-01",
        "CAP-CORE-02",
        "CAP-CORE-03",
        "CAP-CORE-04",
        "CAP-CORE-05",
        "CAP-CORE-06",
        "CAP-CORE-07",
        "CAP-CORE-08",
        "CAP-CORE-09",
        "CAP-CORE-10",
        "CAP-MSC-02",
        "CAP-INTG-07",
    }
)
P1_BUSINESS = frozenset(
    {
        "CAP-CORE-11",
        "CAP-CORE-12",
        "CAP-STRAT-02",
        "CAP-GGV-01",
        "CAP-GGV-02",
        "CAP-GGV-04",
        "CAP-AMG-01",
        "CAP-AMG-04",
        "CAP-BZG-01",
        "CAP-BZG-03",
        "CAP-FIN-01",
        "CAP-FIN-02",
        "CAP-FIN-03",
        "CAP-FIN-05",
        "CAP-HR-01",
        "CAP-HR-04",
        "CAP-INTG-01",
        "CAP-INTG-02",
        "CAP-INTG-04",
        "CAP-CRM-01",
    }
)
P3_FUTURE = frozenset(
    {
        "CAP-GGV-05",
        "CAP-AMG-07",
        "CAP-BZG-07",
    }
)
# P2 is the remainder of the catalog after P0, P1, and P3. Checked at load.

# Dependency order for the six-day path. Prerequisites before dependents.
# This list is exactly P0 then the P1 daily chain. It is not a sort key
# taken from the maturity state.
CRITICAL_ORDER = (
    "CAP-CORE-02",
    "CAP-INTG-07",
    "CAP-MSC-02",
    "CAP-CORE-01",
    "CAP-CORE-03",
    "CAP-CORE-04",
    "CAP-CORE-05",
    "CAP-CORE-06",
    "CAP-CORE-07",
    "CAP-CORE-08",
    "CAP-CORE-09",
    "CAP-CORE-10",
    "CAP-STRAT-02",
    "CAP-INTG-01",
    "CAP-AMG-01",
    "CAP-AMG-04",
    "CAP-INTG-02",
    "CAP-BZG-01",
    "CAP-BZG-03",
    "CAP-INTG-04",
    "CAP-FIN-02",
    "CAP-FIN-01",
    "CAP-FIN-03",
    "CAP-FIN-05",
    "CAP-GGV-02",
    "CAP-GGV-01",
    "CAP-GGV-04",
    "CAP-CRM-01",
    "CAP-HR-01",
    "CAP-HR-04",
    "CAP-CORE-11",
    "CAP-CORE-12",
)

PREREQUISITES: dict[str, tuple[str, ...]] = {
    "CAP-AMG-01": ("CAP-INTG-01",),
    "CAP-AMG-04": ("CAP-INTG-01", "CAP-AMG-01"),
    "CAP-BZG-01": ("CAP-INTG-02",),
    "CAP-BZG-03": ("CAP-INTG-02", "CAP-BZG-01"),
    "CAP-FIN-02": ("CAP-INTG-04",),
    "CAP-GGV-05": ("CAP-INTG-05",),
    "CAP-FIN-06": ("CAP-GGV-06",),
    "CAP-STRAT-02": ("CAP-CORE-01", "CAP-CORE-06", "CAP-CORE-07"),
}

# Catalog ownership INTEGRATE, plus capabilities whose intent says an
# external system owns the transactional truth.
EXTERNAL_SOT = frozenset(
    {
        "CAP-INTG-01",
        "CAP-INTG-02",
        "CAP-INTG-03",
        "CAP-INTG-04",
        "CAP-INTG-05",
        "CAP-AMG-01",
        "CAP-BZG-01",
        "CAP-GGV-05",
        "CAP-FIN-02",
        "CAP-CRM-04",
    }
)

# Owner still has to decide. This does not by itself move the row.
OWNER_DECISION = frozenset(
    {
        "CAP-CORE-02",
        "CAP-CORE-05",
        "CAP-CORE-12",
        "CAP-STRAT-02",
        "CAP-MSC-02",
        "CAP-INTG-01",
        "CAP-INTG-07",
        "CAP-FIN-01",
        "CAP-FIN-02",
        "CAP-FIN-03",
        "CAP-FIN-05",
        "CAP-BZG-03",
        "CAP-GGV-02",
        "CAP-DR-01",
        "CAP-DR-02",
    }
)

RESPONSIBLE_ROLE = {
    "CAP-GGV-01": "ROLE-GGV-CREATIVE-DIRECTOR",
    "CAP-GGV-02": "ROLE-GGV-CREATIVE-DIRECTOR",
    "CAP-GGV-04": "Owner",
    "CAP-GGV-05": "ROLE-GGV-CREATIVE-DIRECTOR",
    "CAP-AMG-01": "ROLE-AMG-GM",
    "CAP-AMG-04": "ROLE-AMG-GM",
    "CAP-BZG-01": "ROLE-BZG-FB-OPS-LEAD",
    "CAP-BZG-03": "ROLE-BZG-CLOSER",
    "CAP-FIN-01": "Owner",
    "CAP-FIN-02": "Owner",
    "CAP-FIN-03": "Owner",
    "CAP-FIN-05": "Owner",
}

_CATALOG_ROW = re.compile(
    r"^\| (CAP-[A-Z0-9]+-\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$"
)


class WarRoomError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def refuse_external_write(_body: dict | None = None) -> None:
    raise WarRoomError(
        "Finish war room is a read desk. Writes are refused.",
        code="writes_refused",
    )


def priority_of(cap_id: str) -> str:
    """W3-P5-PRIORITY-v1. Ignores maturity state."""
    if cap_id in P0_OPERATE:
        return "P0"
    if cap_id in P1_BUSINESS:
        return "P1"
    if cap_id in P3_FUTURE:
        return "P3"
    return "P2"


def _load_catalog_rows(catalog_path: Path | None = None) -> dict[str, dict[str, str]]:
    path = catalog_path or MODEL_C_CATALOG
    text = path.read_text(encoding="utf-8")
    rows: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        match = _CATALOG_ROW.match(line)
        if not match:
            continue
        cap_id, name, ownership, scope, intent = (part.strip() for part in match.groups())
        rows[cap_id] = {
            "id": cap_id,
            "name": name,
            "ownership": ownership,
            "scope": scope,
            "intent": intent,
        }
    return rows


def _credit(state: str) -> str:
    credit = SYSTEM_MATURITY_CREDITS[state]
    return f"{credit:.2f}"


def _work_classes(state: str, ownership: str, cap_id: str) -> list[str]:
    classes: list[str] = []
    if state in {"ABSENT", "SPECIFIED"}:
        classes.append("cursor_build")
    if state in {"ABSENT", "SPECIFIED", "BUILT", "PROVEN"}:
        classes.append("local_deterministic")
    classes.append("human_commissioning")
    if ownership == "INTEGRATE" or cap_id in EXTERNAL_SOT:
        classes.append("external_dependency")
        classes.append("real_world_data_integration")
    if cap_id in OWNER_DECISION or state == "READY":
        classes.append("owner_decision")
    return classes


def _left_group(priority: str, state: str, ownership: str) -> str:
    """One group per capability. Human acts are a separate list."""
    if priority in {"P2", "P3"}:
        return "follow"
    if state == "READY":
        return "commission"
    if ownership == "INTEGRATE" and state in {"ABSENT", "SPECIFIED"}:
        return "external"
    return "finish"


def _dependency(cap_id: str) -> str:
    prior = PREREQUISITES.get(cap_id)
    if not prior:
        return (
            "No extra prerequisite is recorded. The control kernel "
            "(CAP-CORE-01 through CAP-CORE-04) is already PROVEN or READY."
        )
    return "Requires " + ", ".join(prior) + "."


def _evidence_to_close(state: str) -> str:
    if state == "ABSENT":
        return (
            "An approved specification bound to this CAP-ID, then locatable "
            "implementation. A vendor existing is not that evidence."
        )
    if state == "SPECIFIED":
        return (
            "Locatable implementation for BUILT. PROVEN still needs "
            "deterministic tests and material red-team or review evidence."
        )
    if state == "BUILT":
        return (
            "Deterministic verification plus material red-team or review "
            "evidence. BUILT is not PROVEN. A rendered desk is not that review."
        )
    if state == "PROVEN":
        return (
            "Deployed or runtime proof on the intended Beta boundary for READY. "
            "A repository test is not a deployed-route test. A human walk is "
            "not this bar."
        )
    return (
        "Human commissioning evidence recorded on the commissioning register. "
        "That evidence does not change this SYSTEM row. Operating adoption "
        "is a separate measurement and is not on record."
    )


def _six_day_note(state: str, group: str) -> str:
    if group == "commission":
        return "Commissioning only. Not a build. A sign-in does not raise SYSTEM."
    if group == "external":
        return "The outside system has no Wolf connector at BUILT. Do not invent its feed."
    if state == "PROVEN":
        return (
            "Deployed-route bar is open. Unsigned Beta stays fail-closed. "
            "A development-subject 200 is not that proof."
        )
    if state == "BUILT":
        return (
            "A local prove can be attempted. PROVEN still needs the review "
            "the scoring rules require. This pack does not supply that review."
        )
    if state == "SPECIFIED":
        return "Not at BUILT. Six days does not stand in for the missing implementation."
    return "No implementation is on the ledger. Do not fill the gap with a sample."


def _role(cap_id: str) -> str:
    return RESPONSIBLE_ROLE.get(cap_id, "Owner")


def _commissioning_index(path: Path | None) -> dict[str, dict[str, Any]]:
    file_path = path or COMMISSIONING_PATH
    if not file_path.is_file():
        return {}
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for row in raw.get("capabilities") or []:
        if isinstance(row, dict) and row.get("id"):
            out[str(row["id"])] = row
    return out


def _deployed_line(path: Path | None) -> str:
    file_path = path or DEPLOYED_PROOF_PATH
    if not file_path.is_file():
        return "No deployed-route proof file was read. Not proved."
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    result = str(raw.get("result") or "UNKNOWN")
    reason = public_text(raw.get("fail_reason") or "", limit=360)
    return (
        f"DEPLOYED-ROUTE-PROOF-20260927 result is {result}. {reason} "
        "That file is not a per-capability pass."
    )


def raise_refusals() -> list[dict[str, str]]:
    """Candidates looked at for this reconciliation. None are raised.

    PROVEN needs deterministic verification and material red-team or
    review evidence. READY needs deployed or runtime proof on the
    intended boundary. A Wave 3 desk, an ephemeral development subject,
    and a missing staff walk do not meet those bars. Scoring rules
    section 5: a new UI does not by itself move a capability.
    """
    return [
        {
            "id": "CAP-STRAT-02",
            "ledger_state": "BUILT",
            "considered": "PROVEN",
            "decision": "not raised",
            "reason": (
                "Owner Command is a read model with test_owner_command.py. "
                "The ledger next bar is a CAP-bound Model C prove, and the "
                "row says not to inflate this capability via the Progress "
                "dashboard. PROVEN requires material red-team or review "
                "evidence. No review artifact binds this desk to CAP-STRAT-02."
            ),
        },
        {
            "id": "CAP-INTEL-02",
            "ledger_state": "PROVEN",
            "considered": "READY",
            "decision": "not raised",
            "reason": (
                "Accepted PROVEN on 2026-09-18. The next bar on the row is "
                "sustained human workflow use. Wave 3 did not add a deployed "
                "route proof for this capability. DEPLOYED-ROUTE-PROOF-20260927 "
                "is FAIL."
            ),
        },
        {
            "id": "CAP-INTEL-03",
            "ledger_state": "PROVEN",
            "considered": "READY",
            "decision": "not raised",
            "reason": (
                "The truth layer is a display classifier. It is not the "
                "provenance capability's deployed-route bar. An ephemeral "
                "development-subject 200 is not the Cloudflare route proof. "
                "D3 result is FAIL."
            ),
        },
        {
            "id": "CAP-INTEL-04",
            "ledger_state": "PROVEN",
            "considered": "READY",
            "decision": "not raised",
            "reason": (
                "The row already says READY needs an owner screen and a real "
                "person using recall. Wave 3 did not record that person."
            ),
        },
        {
            "id": "CAP-INTG-06",
            "ledger_state": "SPECIFIED",
            "considered": "BUILT",
            "decision": "not raised",
            "reason": (
                "A tech-registry route exists in the Beta server. This "
                "reconciliation did not verify inventory, ownership of truth, "
                "lifecycle, and exit conditions against the catalog intent. "
                "Unverified presence is not BUILT."
            ),
        },
    ]


def human_acts(by_id: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    """Human gates already on record. Not a second maturity score."""
    acts = [
        {
            "id": "cloudflare-session",
            "title": "Owner and staff sign in on Beta with Cloudflare Access",
            "caps": "CAP-CORE-02, and every PROVEN row whose next bar is a deployed route",
            "why": "Unsigned Beta routes stay fail-closed. D3 deployed-route proof is FAIL.",
            "current_state": "CAP-CORE-02 is SYSTEM READY. No seated session was observed.",
            "remaining": "A person with a Cloudflare seat opens Beta :8788. Do not bypass the gate.",
            "dependency": "Cloudflare Access. Not a code change.",
            "role": "Owner",
            "evidence": "A real JWT session recorded as commissioning evidence. It does not raise SYSTEM.",
            "source": "state/completion-register/DEPLOYED-ROUTE-PROOF-20260927.json",
        },
        {
            "id": "open-books",
            "title": "Open the finance books the desks are not allowed to invent",
            "caps": "CAP-FIN-01, CAP-FIN-03, CAP-FIN-05",
            "why": "Owner Command and the business desks say finance UNAVAILABLE. That is not cash.",
            "current_state": by_id["CAP-FIN-01"]["system_state"] + " on CAP-FIN-01",
            "remaining": "The Owner opens the real books, or confirms they stay unavailable. Do not type a balance.",
            "dependency": "Owner decision. Bank files are CAP-INTG-04 and stay a connector, not a payment.",
            "role": "Owner",
            "evidence": "A books source the truth register can stamp. UNAVAILABLE cleared only by that source.",
            "source": "docs/wolf/wave3/W3-P1-OWNER-RESULT.md",
        },
        {
            "id": "source-commissioning",
            "title": "Declare a source commissioned, or leave it uncommissioned",
            "caps": "Yanolja, ESB, Wolf Core, NAS, finance ledgers, Klaviyo, Metricool",
            "why": "Pack 4 left commissioned false on every source. The Needs you queue is that decision.",
            "current_state": "Not commissioned. Wolf Core CURRENT is a store read, not a commissioning.",
            "remaining": "The Owner accepts or refuses each source. This pack does not accept them.",
            "dependency": "Owner decision. Yanolja still has no reader. ESB settlement stays unavailable.",
            "role": "Owner",
            "evidence": "A commissioning record per source. A file on disk is not that record.",
            "source": "docs/wolf/wave3/W3-P4-TRUTH-RESULT.md",
        },
        {
            "id": "closer-seat",
            "title": "Seat a closer and, separately, write a variance policy if cash must mismatch",
            "caps": "CAP-BZG-03",
            "why": "The close machine is SYSTEM READY. Nobody is on the closer position. Policy count was 0.",
            "current_state": "SYSTEM READY. Human commissioning no. venue_daily_closes 0.",
            "remaining": "Assign a real person to POS-BZG-CLOSER-UMA-1. Do not invent a policy to force a green close.",
            "dependency": "Owner decision. ESB settlement_api stays UNAVAILABLE. No payment is added.",
            "role": "Owner",
            "evidence": "An active assignment on ROLE-BZG-CLOSER, plus a real variance policy only if a mismatch must be closable.",
            "source": "state/completion-register/COMMISSIONING-STATE-20260927.json",
        },
        {
            "id": "accountant-seat",
            "title": "Seat the external accountant, or leave that position empty",
            "caps": "CAP-FIN-03",
            "why": "POS-GGV-EXT-ACCT has no person. Finance and external accountant are one catalog role.",
            "current_state": "Position empty. Notes desk is not the books.",
            "remaining": "The Owner assigns a real person, or records that the seat stays empty.",
            "dependency": "Owner decision. Opening the books is the separate act above.",
            "role": "Owner",
            "evidence": "An active assignment on POS-GGV-EXT-ACCT for a real person.",
            "source": "docs/wolf/wave3/W3-P3-STAFF-RESULT.md",
        },
        {
            "id": "misa-primary",
            "title": "Choose the primary assignment for the person on both Content Crew and General Manager",
            "caps": "CAP-CORE-03",
            "why": "My Work follows the primary role. That person's primary is Content Crew. The General Manager page is not what they land on.",
            "current_state": "CAP-CORE-03 is PROVEN. The assignment fact is already stored. It was not moved.",
            "remaining": "The Owner keeps or changes the primary assignment. This is not an engineering rename.",
            "dependency": "Owner decision. People are not roles.",
            "role": "Owner",
            "evidence": "The assignment row the Owner meant, still a real person, not a new demo seat.",
            "source": "docs/wolf/wave3/W3-P3-STAFF-RESULT.md",
        },
    ]
    return acts


def _ledger_classification() -> dict:
    try:
        from core import ledger_class

        return ledger_class.summarize_live()
    except Exception:  # noqa: BLE001
        return {"read": "UNAVAILABLE"}


def build_war_room(
    *,
    ledger_path: Path | None = None,
    catalog_path: Path | None = None,
    commissioning_path: Path | None = None,
    deployed_proof_path: Path | None = None,
) -> dict[str, Any]:
    """Project the 77. Does not write the ledger or the catalog database."""
    path = Path(ledger_path) if ledger_path else MODEL_C_LEDGER
    computed = compute_system_from_ledger(path)
    if not computed.get("ok"):
        raise WarRoomError(
            "Ledger projection is stale. The percentage is withheld.",
            code="stale",
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    catalog = _load_catalog_rows(catalog_path)
    domains = load_catalog_cap_domains(catalog_path=catalog_path)
    if set(raw) != set(catalog):
        missing = sorted(set(catalog) ^ set(raw))
        raise WarRoomError(
            "Ledger and catalog CAP-IDs differ: " + ", ".join(missing[:8]),
            code="stale",
        )
    covered = P0_OPERATE | P1_BUSINESS | P3_FUTURE
    if not covered <= set(catalog):
        unknown = sorted(covered - set(catalog))
        raise WarRoomError("Priority set names an unknown CAP-ID: " + ", ".join(unknown), code="stale")
    overlap = (P0_OPERATE & P1_BUSINESS) | (P0_OPERATE & P3_FUTURE) | (P1_BUSINESS & P3_FUTURE)
    if overlap:
        raise WarRoomError("Priority sets overlap: " + ", ".join(sorted(overlap)), code="stale")
    if set(CRITICAL_ORDER) != (P0_OPERATE | P1_BUSINESS):
        raise WarRoomError("Critical path is not exactly P0 and P1.", code="stale")

    commissioning = _commissioning_index(commissioning_path)
    deployed = _deployed_line(deployed_proof_path)
    sum_credits = Decimal("0")
    rows: list[dict[str, Any]] = []
    for cap_id in sorted(raw):
        record = raw[cap_id]
        state = str(record[0]).strip().upper()
        if state not in SYSTEM_MATURITY_CREDITS:
            raise WarRoomError(f"Unknown maturity state for {cap_id}", code="stale")
        credit = SYSTEM_MATURITY_CREDITS[state]
        sum_credits += credit
        meta = catalog[cap_id]
        priority = priority_of(cap_id)
        ownership = meta["ownership"]
        classes = _work_classes(state, ownership, cap_id)
        group = _left_group(priority, state, ownership)
        gap = commissioning.get(cap_id) or {}
        rows.append(
            {
                "id": cap_id,
                "name": meta["name"],
                "domain": domains.get(cap_id) or "UNMAPPED",
                "ownership": ownership,
                "scope": meta["scope"],
                "intent": public_text(meta["intent"], limit=500),
                "system_state": state,
                "score": _credit(state),
                "evidence": public_text(record[1] if len(record) > 1 else "", limit=500),
                "deployed_proof": deployed,
                "staff_readiness": "No",
                "human_commissioning": "No",
                "operating_adoption": "NOT MEASURED",
                "staff_ready": False,
                "human_commissioned": False,
                "blocker": public_text(record[2] if len(record) > 2 else "", limit=500) or "No next bar is stored on the ledger.",
                "owner_role": _role(cap_id),
                "next_action": public_text(record[2] if len(record) > 2 else "", limit=500) or "No next bar is stored on the ledger.",
                "dependency": _dependency(cap_id),
                "effort_class": EFFORT[state],
                "priority": priority,
                "priority_rule": RULE_ID,
                "why": WHY[priority],
                "work_classes": classes,
                "left_group": group,
                "evidence_to_close": _evidence_to_close(state),
                "six_day_note": _six_day_note(state, group),
                "ledger_health": public_text(record[3] if len(record) > 3 else "", limit=40),
                "commissioning_gap": public_text(gap.get("gap") or "", limit=400),
                "on_critical_path": cap_id in set(CRITICAL_ORDER),
            }
        )

    exact = (sum_credits / Decimal(77)) * Decimal(100)
    pct_2 = exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    pct_1 = exact.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    if str(sum_credits) != str(computed.get("sum_credits_exact")):
        raise WarRoomError("War room sum disagrees with the progress read model.", code="stale")

    by_id = {row["id"]: row for row in rows}
    critical = [by_id[cap_id] for cap_id in CRITICAL_ORDER]
    counts = {state: sum(1 for row in rows if row["system_state"] == state) for state in STATES}
    rank = {cap_id: index for index, cap_id in enumerate(CRITICAL_ORDER)}

    def _ordered(group: str) -> list[str]:
        ids = [row["id"] for row in rows if row["left_group"] == group]
        return sorted(ids, key=lambda cap_id: (rank.get(cap_id, 10_000), cap_id))

    groups = {
        "finish": _ordered("finish"),
        "commission": _ordered("commission"),
        "external": _ordered("external"),
        "follow": _ordered("follow"),
    }
    return {
        "ok": True,
        "read": "READ",
        "rule": RULE_ID,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": "NOT MEASURED",
        "staff_ready_count": 0,
        "human_commissioned_count": 0,
        "money": None,
        "payment_executed": False,
        "external_writes": False,
        "ledger_write": False,
        "green_kpi": False,
        "system_sum": f"{sum_credits:.2f}",
        "system_n": 77,
        "system_pct_2dp": f"{pct_2:.2f}",
        "system_pct_1dp": f"{pct_1:.1f}",
        "system_line": f"{sum_credits:.2f} / 77 = {pct_2:.2f}%",
        "formula": "SYSTEM% = SUM(canonical capability maturity credits) / 77 × 100",
        "counts": counts,
        "priority_counts": {key: sum(1 for row in rows if row["priority"] == key) for key in PRIORITIES},
        "groups": groups,
        "capabilities": rows,
        "critical_path": [
            {
                "order": index + 1,
                "id": row["id"],
                "name": row["name"],
                "priority": row["priority"],
                "system_state": row["system_state"],
                "left_group": row["left_group"],
                "next_action": row["next_action"],
                "dependency": row["dependency"],
                "six_day_note": row["six_day_note"],
                "effort_class": row["effort_class"],
                "owner_role": row["owner_role"],
            }
            for index, row in enumerate(critical)
        ],
        "human_acts": human_acts(by_id),
        "raise_refusals": raise_refusals(),
        "raises": [],
        "ledger_classification": _ledger_classification(),
        "headline": (
            f"SYSTEM = {sum_credits:.2f} / 77 = {pct_2:.2f}% ; "
            "STAFF READY = 0 ; HUMAN COMMISSIONED = 0 ; "
            "OPERATING ADOPTION = NOT MEASURED"
        ),
    }


def _item_md(row: dict[str, Any]) -> str:
    classes = ", ".join(row["work_classes"])
    return "\n".join(
        [
            f"### {row['id']} — {row['name']}",
            "",
            f"- What it is: {row['intent']}",
            f"- Why it matters: {row['why']}",
            f"- Current state: SYSTEM {row['system_state']} ({row['score']}). Domain {row['domain']}. Priority {row['priority']}. Effort {row['effort_class']}.",
            f"- Exact remaining work: {row['next_action']}",
            f"- Work classes: {classes}.",
            f"- Dependency: {row['dependency']}",
            f"- Responsible role: {row['owner_role']}.",
            f"- Evidence required to close: {row['evidence_to_close']}",
            f"- Six-day note: {row['six_day_note']}",
            "- Staff ready: No. Human commissioned: No. Operating adoption: NOT MEASURED.",
            f"- Deployed proof: {row['deployed_proof']}",
            "",
        ]
    )


def _act_md(act: dict[str, str]) -> str:
    return "\n".join(
        [
            f"### {act['title']}",
            "",
            f"- What it is: {act['title']}",
            f"- Why it matters: {act['why']}",
            f"- Current state: {act['current_state']}",
            f"- Exact remaining work: {act['remaining']}",
            f"- Dependency: {act['dependency']}",
            f"- Responsible role: {act['role']}.",
            f"- Evidence required to close: {act['evidence']}",
            f"- Capabilities: {act['caps']}.",
            f"- Source already on record: {act['source']}.",
            "",
        ]
    )


def render_what_is_left(room: dict[str, Any] | None = None) -> str:
    room = room or build_war_room()
    by_id = {row["id"]: row for row in room["capabilities"]}

    def section(title: str, ids: list[str], lede: str) -> str:
        body = [_item_md(by_id[cap_id]) for cap_id in ids]
        if not body:
            body = ["None.\n"]
        return f"## {title}\n\n{lede}\n\n" + "\n".join(body)

    human = "\n".join(_act_md(act) for act in room["human_acts"])
    lines = [
        "# What is left to finish Wolf Command",
        "",
        room["headline"],
        "",
        "As of the Wave 3 Pack 5 reconciliation on 27 Sep 2026. "
        "SYSTEM is the machinery score from `state/model-c-baseline-assessments.json`. "
        "Staff readiness, human commissioning, and operating adoption are not added into it.",
        "",
        f"Priority rule: {room['rule']}. Progress dial rounds the same sum to {room['system_pct_1dp']}%. "
        "That 1-decimal figure is the same credit total, not a second score.",
        "",
        "Counts: "
        + ", ".join(f"{state} {room['counts'][state]}" for state in STATES)
        + ". Priorities: "
        + ", ".join(f"{key} {room['priority_counts'][key]}" for key in PRIORITIES)
        + ".",
        "",
        "No capability in this list is staff ready. None is human commissioned. "
        "Operating adoption is NOT MEASURED. A rendered desk is not a walk.",
        "",
        section(
            "Must finish in the next 6 days",
            room["groups"]["finish"],
            "P0 or P1, and the SYSTEM state is not READY. The next bar is Wolf-side work. "
            "Several of these still wait on a person for the deployed-route half. That wait is named on the item and under Waiting on a human. It is not a second copy of the capability.",
        ),
        section(
            "Must commission",
            room["groups"]["commission"],
            "SYSTEM is READY. The remaining work is a human commissioning. It does not raise the row, and it is not operating adoption.",
        ),
        "## Waiting on a human\n\n"
        "These are acts already recorded in Day 2 and Wave 3. They are not new tasks and they are not a maturity score.\n\n"
        + human,
        section(
            "Waiting on an external system",
            room["groups"]["external"],
            "P0 or P1, catalog ownership INTEGRATE, and the Wolf side is not yet BUILT. "
            "Connectors that are already BUILT stay under Must finish, with the vendor named as the dependency.",
        ),
        section(
            "Can safely follow after initial launch",
            room["groups"]["follow"],
            "P2 and P3. Real capabilities. Not the control kernel and not the first daily loop. "
            "Leaving them here is not a claim they are unimportant later.",
        ),
    ]
    return "\n".join(lines).rstrip() + "\n"


def render_critical_path(room: dict[str, Any] | None = None) -> str:
    room = room or build_war_room()
    steps = []
    for step in room["critical_path"]:
        steps.append(
            "\n".join(
                [
                    f"### {step['order']}. {step['id']} — {step['name']}",
                    "",
                    f"- Priority {step['priority']}. SYSTEM {step['system_state']}. Effort {step['effort_class']}. Group: {step['left_group']}.",
                    f"- Next bar: {step['next_action']}",
                    f"- Dependency: {step['dependency']}",
                    f"- Responsible role: {step['owner_role']}.",
                    f"- In six days: {step['six_day_note']}",
                    "",
                ]
            )
        )
    text = [
        "# Six-day critical path",
        "",
        room["headline"],
        "",
        "Order is dependency order under rule W3-P5-PRIORITY-v1: the sign-in boundary, "
        "environment separation, Access posture, the rest of the control kernel, then the "
        "owner picture, then each business loop after the connector it names. "
        "Maturity state does not reorder this list.",
        "",
        "This path does not promise that every step reaches READY in six days. "
        "The note on each step says what those six days can and cannot close. "
        "Nothing here moves money, writes a bank, or marks a human commissioning.",
        "",
        "Production `:8787` is out of this path. Beta `:8788` is the boundary for any deployed-route prove.",
        "",
        *steps,
        "## Not on this path",
        "",
        "P2 and P3 stay in the follow-after list. They are not blockers for the first operating loop. "
        "Sale capabilities are P2 because sale readiness is a named factor and can follow commissioning. "
        "Brand social performance, service-improvement capture, review capture, and the buyer room surfaces are P3.",
        "",
    ]
    return "\n".join(text).rstrip() + "\n"
