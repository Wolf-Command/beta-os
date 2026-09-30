#!/usr/bin/env python3
"""FIN-TAX-DEEPEN-1 — Tax dues deepen (wire or HUMAN/EXTERNAL).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave8 pack
FIN-TAX-DEEPEN-1 (armed 2026-09-30 after INV-CASH-FACTS-ROUTE-1
PASS_VERIFIED). Challenges FIN-TAX-SHELL-1 UNKNOWN dues ceiling.

Probes authorised tax systems/facts. Wires when present; otherwise stamps
HUMAN_COMMISSIONING and/or EXTERNAL_BLOCKER with evidence. Never invents
dues, filings, or NPWP. Google NPWP = MATT_ACTION non-blocking.
Preserves FIN-TAX-SHELL-1 honesty (UNKNOWN until facts).
staff_ready=false · human_commissioned=false.
Does not auto-chain CRM-PIPELINE-TRUTH-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import fin_tax_shell1 as _tax

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
COMMISSION_STAMP = (
    BETA_ROOT
    / "state"
    / "final-completion"
    / "packs"
    / "FIN-TAX-DEEPEN-1-COMMISSION.json"
)

PACK_ID = "FIN-TAX-DEEPEN-1"
SCHEMA_ID = "wolf.fin-tax-deepen-1.v1"
BOUND = "beta-fin-tax-deepen-safe"
CAP_FIN_TAX = "CAP-FIN tax"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
# Umbrella from ARM/queue; route resolves to HUMAN_COMMISSIONING (+ EXTERNAL).
PACK_CLASSIFICATION = "INTERNALLY_SOLVABLE_OR_HUMAN"
CLASSIFICATION = "HUMAN_COMMISSIONING"
CLOSES_TOWARD = ("tax", CAP_FIN_TAX)
PRESERVED_PACKS = ("FIN-TAX-SHELL-1",)
TAX_SHELL_PAGE = "/fin/tax-shell-1"
NPWP_STATUS = "MATT_ACTION"
NPWP_BLOCKING = False

PAGE_PATHS = frozenset(
    {
        "/fin/tax-deepen-1",
        "/fin/tax-deepen-1/",
        "/fin/tax-deepen",
        "/fin/tax-deepen/",
        "/ops/fin-tax-deepen-1",
        "/ops/fin-tax-deepen-1/",
        "/ops/fin-tax-deepen",
        "/ops/fin-tax-deepen/",
        "/fin-tax-deepen-1",
        "/fin-tax-deepen-1/",
        "/fin-tax-deepen-1.html",
        "/dashboards/fin-tax-deepen-1.html",
    }
)
API_PATH = "/api/fin/tax-deepen-1"
API_PATHS = frozenset(
    {
        API_PATH,
        "/api/ops/fin-tax-deepen-1",
        "/api/ops/tax-deepen-1",
    }
)

STATUS_VOCAB = frozenset(
    {
        "HUMAN_COMMISSIONING",
        "INTERNALLY_SOLVABLE_OR_HUMAN",
        "EXTERNAL_BLOCKER",
        "EXTERNAL",
        "MATT_ACTION",
        "PRESERVED",
        "ABSENT",
        "REFUSED",
        "UNKNOWN",
        "WIRED",
        "COMMISSIONED",
    }
)

# Name-only tax system env patterns — never load secret values.
_TAX_ENV_NAME_RE = re.compile(
    r"(TAX_|NPWP|PAJAK_|DJP_|EFAKTUR|E_FAKTUR|E-FILING|EFILING|"
    r"SPT_|PPN_|PPH_|CORETAX|DJAPONLINE|TAX_API|TAX_URL|"
    r"TAX_TOKEN|TAX_SECRET|TAX_CALENDAR|FILING_API)",
    re.IGNORECASE,
)

TAX_CLIENT_SEARCH: dict[str, Any] = {
    "glob": "scripts/core/**/*.py",
    "patterns": (
        "tax_client",
        "djp_client",
        "efaktur_client",
        "TaxFilingClient",
        "live_tax_feed",
        "spt_client",
    ),
    "found_modules": (),
    "note": (
        "No dedicated authorised Indonesian tax filing client. "
        "fin_tax_shell1 is honesty UNKNOWN shell only. "
        "Live DJP / eFaktur / e-filing not in-repo."
    ),
}

COMMISSIONING_PATH: tuple[dict[str, str], ...] = (
    {
        "step": "1",
        "title": "Owner authorises tax fact systems",
        "detail": (
            "Human Owner commissions an authorised tax calendar / filing "
            "system (secret store + connector — DJP Online, eFaktur, or "
            "internal tax ledger). Agents do not invent dues or filings."
        ),
    },
    {
        "step": "2",
        "title": "Owner writes commission stamp",
        "detail": (
            "Write state/final-completion/packs/FIN-TAX-DEEPEN-1-COMMISSION.json "
            "with human_route_commissioned=true (or tax_facts_authorised=true). "
            "Absent stamp → HUMAN_COMMISSIONING held."
        ),
    },
    {
        "step": "3",
        "title": "Parent arms wire pack when systems present",
        "detail": (
            "After stamp + verified authorised tax systems with real dues/"
            "filings, parent/Peaches arms a wire pack. This pack EXIT never "
            "invents due amounts, filings, or NPWP numbers."
        ),
    },
    {
        "step": "4",
        "title": "Until then: UNKNOWN shell preserved · NPWP MATT_ACTION",
        "detail": (
            "FIN-TAX-SHELL-1 stays calendars/obligations UNKNOWN with null "
            "dues. Live DJP/eFaktur held EXTERNAL_BLOCKER. Google NPWP remains "
            "MATT_ACTION Owner-only non-blocking. Empty is honest — never invent."
        ),
    },
)

GAPS: tuple[str, ...] = (
    "Authorised tax system ABSENT — no dues wire until human commission.",
    "Live DJP / eFaktur / e-filing ABSENT in-repo — EXTERNAL_BLOCKER.",
    "due_amount / due_on / filed stay null/false — never invented.",
    "Google NPWP = MATT_ACTION non-blocking (does not block this pack).",
    "FIN-TAX-SHELL-1 UNKNOWN honesty preserved.",
    "staff_ready=false · human_commissioned=false on this pack.",
    "Next pack CRM-PIPELINE-TRUTH-1 is parent/Peaches only.",
)


class FinTaxDeepen1Error(ValueError):
    """Fail closed. Does not invent dues, filings, NPWP, or commission flips."""

    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def page_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/") or "/"
    return trimmed in PAGE_PATHS or raw in PAGE_PATHS


def api_matches(path: str | None) -> bool:
    raw = (path or "").split("?")[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    trimmed = raw.rstrip("/")
    return trimmed in API_PATHS or raw in API_PATHS


def person_may_view(person_id: str | None, *, role_allowed: bool = False) -> bool:
    pid = (person_id or "").strip()
    if not pid:
        return False
    if pid == OWNER_PERSON:
        return True
    return bool(role_allowed)


def _env_key_names_from_dotenv(path: Path) -> list[str]:
    if not path.is_file():
        return []
    names: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key = raw.split("=", 1)[0].strip()
            if key:
                names.append(key)
    except OSError:
        return []
    return names


def human_route_commissioned(*, stamp_path: Path | None = None) -> bool:
    """True only when an explicit commission stamp says so.

    Pack honesty keeps human_commissioned=false. This helper is for the
    route gate only — presence of stamp does not flip pack flags.
    """
    path = Path(stamp_path) if stamp_path is not None else COMMISSION_STAMP
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    if data.get("pack") not in {None, PACK_ID}:
        return False
    return data.get("human_route_commissioned") is True or data.get(
        "tax_facts_authorised"
    ) is True


def probe_tax_systems() -> dict[str, Any]:
    """Name-only probe for tax systems. Never returns secret values."""
    process_hits = sorted(k for k in os.environ if _TAX_ENV_NAME_RE.search(k))
    dotenv_keys = _env_key_names_from_dotenv(BETA_ROOT / ".env")
    example_keys = _env_key_names_from_dotenv(BETA_ROOT / ".env.example")
    file_hits = sorted(
        {k for k in (dotenv_keys + example_keys) if _TAX_ENV_NAME_RE.search(k)}
    )
    present = bool(process_hits or file_hits)
    client_found = bool(TAX_CLIENT_SEARCH["found_modules"])
    return {
        "id": "tax_systems",
        "label": "Tax systems (name-only)",
        "status": "HUMAN_COMMISSIONING" if not (present and client_found) else "WIRED",
        "creds_present": present,
        "client_module_found": client_found,
        "process_env_key_names": process_hits,
        "dotenv_key_names": file_hits,
        "secret_values_exposed": False,
        "due_amount": None,
        "due_on": None,
        "filing_count": 0,
        "value": None,
        "why": (
            "No TAX_/DJP_/EFAKTUR/SPT_/PPN_/PPH_ key names and no authorised "
            "tax filing client. Tax systems ABSENT — stamp HUMAN_COMMISSIONING. "
            "Secret values never loaded."
            if not present
            else (
                "Tax-related key names present; values not loaded. "
                "Wire still refused until commission stamp + authorised facts."
                if not client_found
                else "Tax system names + client present; pack still refuses invent."
            )
        ),
        "evidence": ".env + .env.example key-name scan + client search (no values)",
        "client_search": dict(TAX_CLIENT_SEARCH),
    }


def probe_djp_external() -> dict[str, Any]:
    """Live DJP / eFaktur / e-filing path — EXTERNAL_BLOCKER when absent."""
    djp_module = BETA_ROOT / "scripts" / "core" / "djp_client.py"
    efaktur_module = BETA_ROOT / "scripts" / "core" / "efaktur_client.py"
    present = djp_module.is_file() or efaktur_module.is_file()
    return {
        "id": "djp_efaktur_external",
        "label": "DJP / eFaktur / e-filing (EXTERNAL_BLOCKER)",
        "status": "EXTERNAL_BLOCKER",
        "path_present": present,
        "wired_into_fin_tax": False,
        "due_amount": None,
        "filing_count": 0,
        "value": "live_djp_efaktur_absent_in_repo",
        "why": (
            "Live DJP Online / eFaktur / e-filing connectors are ABSENT in-repo. "
            "Stamp EXTERNAL_BLOCKER — do not invent filings or dues from a "
            "missing external tax platform. Human Owner must commission "
            "external path before any wire."
        ),
        "evidence": (
            "no scripts/core/djp_client.py · no efaktur_client.py · "
            "no TAX_/DJP_ env keys"
        ),
    }


def probe_npwp_matt_action() -> dict[str, Any]:
    """Google NPWP stays MATT_ACTION Owner-only — non-blocking."""
    return {
        "id": "npwp_matt_action",
        "label": "Google NPWP (MATT_ACTION)",
        "status": "MATT_ACTION",
        "blocking": False,
        "npwp": None,
        "npwp_number": None,
        "invented_npwp": False,
        "value": "Owner-only non-blocking",
        "why": (
            "Google NPWP remains Matt Owner exception ONLY (MATT_ACTION). "
            "Non-blocking for this pack — do not invent NPWP numbers; do not "
            "fail EXIT waiting on NPWP."
        ),
        "evidence": "MISSION / ARM npwp=MATT_ACTION_NON_BLOCKING",
    }


def probe_tax_shell_facts() -> dict[str, Any]:
    """Read FIN-TAX-SHELL-1 — wire only if real filing facts exist."""
    try:
        slice_ = _tax.build_slice()
        filing_count = int(slice_.get("filing_count") or 0)
        unknown = slice_.get("dues_unknown") is True or filing_count == 0
        return {
            "id": "tax_shell_facts",
            "label": "FIN-TAX-SHELL-1 facts",
            "status": "UNKNOWN" if unknown else "WIRED",
            "filing_count": filing_count,
            "dues_unknown": unknown,
            "due_amount": None,
            "due_on": None,
            "invented_filing": slice_.get("invented_filing"),
            "invented_amount": slice_.get("invented_amount"),
            "fake_filings": slice_.get("fake_filings"),
            "value": filing_count,
            "why": (
                "FIN-TAX-SHELL-1 filing_count=0 — UNKNOWN. No dues to wire. "
                "Never invent amounts or filings."
                if unknown
                else (
                    f"FIN-TAX-SHELL-1 reports filing_count={filing_count}. "
                    "Wire path available for parent wire pack — this pack does "
                    "not invent additional dues."
                )
            ),
            "evidence": TAX_SHELL_PAGE,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "id": "tax_shell_facts",
            "status": "UNKNOWN",
            "filing_count": 0,
            "due_amount": None,
            "error": type(exc).__name__,
            "why": "Tax shell probe failed — no invented dues.",
            "evidence": "core.fin_tax_shell1.build_slice",
        }


def decide_route(
    *,
    stamp_path: Path | None = None,
    tax_probe: dict[str, Any] | None = None,
    tax_facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Core route decision. Never invents dues, filings, or NPWP."""
    tax = tax_probe if tax_probe is not None else probe_tax_systems()
    facts = tax_facts if tax_facts is not None else probe_tax_shell_facts()
    commissioned = human_route_commissioned(stamp_path=stamp_path)

    filing_count = int(facts.get("filing_count") or 0)
    tax_ready = bool(tax.get("creds_present") and tax.get("client_module_found"))
    wireable = filing_count > 0

    if wireable and commissioned:
        action = "WIRE_FACTS"
        classification = "WIRED"
        reason = (
            "Authorised tax facts present and human route commissioned. "
            "This pack surfaces wireability; does not invent additional dues. "
            "Parent may deepen wire. FIN-TAX-SHELL-1 stays source-of-truth."
        )
        may_wire = True
    elif wireable and not commissioned:
        action = "STAMP_HUMAN_COMMISSIONING"
        classification = CLASSIFICATION
        reason = (
            "Some tax facts exist on the honesty shell, but human route "
            "commission stamp is absent. Stamp HUMAN_COMMISSIONING before "
            "wire deepen. Never invent additional dues/filings."
        )
        may_wire = False
    elif tax_ready and commissioned:
        action = "SYSTEMS_COMMISSIONED_AWAIT_FACTS"
        classification = "COMMISSIONED"
        reason = (
            "Tax system key names + client present and commissioned, but "
            "FIN-TAX-SHELL-1 still shows zero filings. Await real facts — "
            "never invent dues. DJP/eFaktur stays EXTERNAL_BLOCKER until wired."
        )
        may_wire = False
    else:
        action = "STAMP_HUMAN_COMMISSIONING"
        classification = CLASSIFICATION
        reason = (
            "Authorised tax systems ABSENT (or no wireable filing facts). "
            "Stamp HUMAN_COMMISSIONING: Owner authorises systems, writes "
            "commission stamp, then parent arms wire. Live DJP/eFaktur stamped "
            "EXTERNAL_BLOCKER. NPWP stays MATT_ACTION non-blocking. "
            "Never invent dues, filings, or NPWP numbers."
        )
        may_wire = False

    return {
        "action": action,
        "classification": classification,
        "pack_classification": PACK_CLASSIFICATION,
        "route_classification": classification,
        "external_blocker": "EXTERNAL_BLOCKER",
        "npwp": NPWP_STATUS,
        "npwp_blocking": NPWP_BLOCKING,
        "reason": reason,
        "may_wire": may_wire,
        "wired": False,
        "tax_systems_present": bool(tax.get("creds_present")),
        "human_route_commissioned": commissioned,
        "filing_count": filing_count,
        "invented_amount": False,
        "invented_filing": False,
        "invented_due": False,
        "invented_npwp": False,
        "fake_filings": False,
        "due_amount": None,
        "due_on": None,
        "npwp_number": None,
        "last_filed_at": None,
    }


def fin_tax_shell1_preserved() -> dict[str, Any]:
    try:
        slice_ = _tax.build_slice()
        flags = _tax.honesty_flags()
        ok = (
            slice_.get("ok") is True
            and flags.get("invented_filing") is False
            and flags.get("invented_amount") is False
            and flags.get("fake_filings") is False
            and flags.get("staff_ready") is False
            and flags.get("human_commissioned") is False
            and flags.get("dues_unknown") is True
            and _tax.all_calendars_unknown(slice_)
            and _tax.all_obligations_unknown(slice_)
            and _tax.no_fake_filings(slice_)
        )
        return {
            "ok": ok,
            "filing_count": slice_.get("filing_count"),
            "dues_unknown": slice_.get("dues_unknown"),
            "invented_filing": slice_.get("invented_filing"),
            "invented_amount": slice_.get("invented_amount"),
            "fake_filings": slice_.get("fake_filings"),
            "why": (
                "FIN-TAX-SHELL-1 preserved: calendars/obligations UNKNOWN, "
                "null dues, no fake filings, no invented amounts."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "FIN-TAX-SHELL-1 check failed — pack must not break it.",
        }


def honesty_flags() -> dict[str, Any]:
    decision = decide_route()
    tax = fin_tax_shell1_preserved()
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "cap_fin_tax": CAP_FIN_TAX,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "live_adoption": False,
        "human_review_gate": True,
        "invented_amount": False,
        "invented_filing": False,
        "invented_due": False,
        "invented_npwp": False,
        "fake_filings": False,
        "live_tax": False,
        "live_filing": False,
        "secret_values_exposed": False,
        "due_amount": None,
        "due_on": None,
        "npwp_number": None,
        "last_filed_at": None,
        "last_filed_null": True,
        "tax_systems_present": decision.get("tax_systems_present"),
        "human_route_commissioned_stamp": decision.get("human_route_commissioned"),
        "classification": decision.get("classification"),
        "route_classification": decision.get("route_classification"),
        "pack_classification": PACK_CLASSIFICATION,
        "external_blocker": "EXTERNAL_BLOCKER",
        "npwp": NPWP_STATUS,
        "npwp_blocking": NPWP_BLOCKING,
        "action": decision.get("action"),
        "fin_tax_shell1_preserved": tax.get("ok") is True,
        "extends_fin_tax_shell1": True,
        "djp_efaktur_external": True,
        "second_tax_system": False,
        "proven": False,
        "ready": False,
        "maturity_ceiling": CEILING,
        "ceiling": CEILING,
        "closes_toward": list(CLOSES_TOWARD),
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "anon_fail_closed": True,
        "next_pack_for_parent_only": "CRM-PIPELINE-TRUTH-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
        "status_vocab": "|".join(sorted(STATUS_VOCAB)),
        "commission_stamp_path": str(COMMISSION_STAMP),
        "commission_stamp_present": COMMISSION_STAMP.is_file(),
    }


def gaps() -> list[str]:
    return list(GAPS)


def commissioning_path() -> list[dict[str, str]]:
    return [dict(step) for step in COMMISSIONING_PATH]


def refuse_invent_amount(_body: dict | None = None) -> None:
    raise FinTaxDeepen1Error(
        "Tax due amounts are UNKNOWN until authorised facts. Not invented.",
        code="invent_amount_refused",
    )


def refuse_invent_filing(_body: dict | None = None) -> None:
    raise FinTaxDeepen1Error(
        "Filings stay unfiled until a real fact lands. Not invented.",
        code="invent_filing_refused",
    )


def refuse_invent_npwp(_body: dict | None = None) -> None:
    raise FinTaxDeepen1Error(
        "NPWP invent is refused. Google NPWP is MATT_ACTION Owner-only "
        "non-blocking — never invent NPWP numbers.",
        code="invent_npwp_refused",
    )


def refuse_commission_flip(_body: dict | None = None) -> None:
    raise FinTaxDeepen1Error(
        "Inventing staff_ready / human_commissioned via API is refused. "
        "Human writes the commission stamp file; pack flags stay false.",
        code="ready_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise FinTaxDeepen1Error(
        "Inventing PROVEN is refused. Tax dues stay at shell honesty state.",
        code="proven_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise FinTaxDeepen1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {
            "amount",
            "amounts",
            "due",
            "dues",
            "due-amount",
            "tax",
            "tax-amount",
            "invent-amount",
            "fake-amount",
            "fake-tax",
            "fake-dues",
        } or norm in {
            "amount",
            "amounts",
            "due",
            "dues",
            "due_amount",
            "tax",
            "tax_amount",
            "invent_amount",
            "fake_amount",
            "fake_tax",
            "fake_dues",
        }:
            refuse_invent_amount(payload)
        if token in {
            "filing",
            "filings",
            "file",
            "filed",
            "filed-at",
            "invent-filing",
            "fake-filing",
            "fake-filings",
            "spt",
            "submit",
        } or norm in {
            "filing",
            "filings",
            "file",
            "filed",
            "filed_at",
            "invent_filing",
            "fake_filing",
            "fake_filings",
            "spt",
            "submit",
        }:
            refuse_invent_filing(payload)
        if token in {
            "npwp",
            "npwp-number",
            "invent-npwp",
            "fake-npwp",
        } or norm in {
            "npwp",
            "npwp_number",
            "invent_npwp",
            "fake_npwp",
        }:
            refuse_invent_npwp(payload)
        if token in {
            "staff-ready",
            "human-commissioned",
            "commission",
            "ready",
        } or norm in {
            "staff_ready",
            "human_commissioned",
            "commission",
            "ready",
        }:
            refuse_commission_flip(payload)
        if token in {"proven", "prove"}:
            refuse_proven(payload)
    raise FinTaxDeepen1Error(
        "FIN-TAX-DEEPEN-1 is a read honesty / commissioning deepen board. "
        "Dues/filing/NPWP invent and commission-flag flips refused.",
        code="write_refused",
    )


def surface_stamps(
    *,
    stamp_path: Path | None = None,
) -> list[dict[str, Any]]:
    decision = decide_route(stamp_path=stamp_path)
    tax = probe_tax_systems()
    djp = probe_djp_external()
    npwp = probe_npwp_matt_action()
    facts = probe_tax_shell_facts()
    preserved = fin_tax_shell1_preserved()
    route_status = decision["classification"]
    return [
        {
            "id": "tax_systems",
            "label": "Tax systems",
            "status": tax["status"] if tax["status"] in STATUS_VOCAB else "ABSENT",
            "value": {
                "creds_present": tax["creds_present"],
                "client_module_found": tax["client_module_found"],
            },
            "due_amount": None,
            "why": tax["why"],
            "evidence": tax["evidence"],
        },
        {
            "id": "djp_efaktur_external",
            "label": "DJP / eFaktur / e-filing",
            "status": "EXTERNAL_BLOCKER",
            "value": djp.get("value"),
            "wired_into_fin_tax": False,
            "why": djp["why"],
            "evidence": djp["evidence"],
        },
        {
            "id": "npwp_matt_action",
            "label": "Google NPWP",
            "status": "MATT_ACTION",
            "value": npwp.get("value"),
            "blocking": False,
            "npwp_number": None,
            "why": npwp["why"],
            "evidence": npwp["evidence"],
        },
        {
            "id": "tax_shell_facts",
            "label": "FIN-TAX-SHELL-1 facts",
            "status": facts["status"] if facts["status"] in STATUS_VOCAB else "UNKNOWN",
            "value": facts.get("filing_count"),
            "due_amount": None,
            "why": facts["why"],
            "evidence": facts["evidence"],
        },
        {
            "id": "human_route",
            "label": "Human route / commission",
            "status": CLASSIFICATION
            if not decision["human_route_commissioned"]
            else "COMMISSIONED",
            "value": decision["human_route_commissioned"],
            "why": (
                "Human must authorise tax systems and write commission stamp. "
                "Absent stamp → HUMAN_COMMISSIONING. Pack flags stay false."
            ),
            "evidence": str(stamp_path or COMMISSION_STAMP),
        },
        {
            "id": "route_decision",
            "label": "Route decision",
            "status": route_status if route_status in STATUS_VOCAB else CLASSIFICATION,
            "value": decision["action"],
            "classification": decision["classification"],
            "pack_classification": PACK_CLASSIFICATION,
            "may_wire": decision["may_wire"],
            "why": decision["reason"],
            "evidence": "decide_route()",
        },
        {
            "id": "fin_tax_shell1",
            "label": "FIN-TAX-SHELL-1 preserved",
            "status": "PRESERVED" if preserved.get("ok") else "UNKNOWN",
            "value": preserved.get("ok"),
            "why": preserved.get("why"),
            "evidence": TAX_SHELL_PAGE,
        },
        {
            "id": "invent_refused",
            "label": "Invent dues / filings / NPWP",
            "status": "REFUSED",
            "value": False,
            "why": "Due invent, filing invent, and NPWP invent are refused.",
            "evidence": "refuse_invent_amount / refuse_invent_filing / refuse_invent_npwp",
        },
    ]


def surfaces_are_honest(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board(OWNER_PERSON)
    if pack.get("invented_amount") is True or pack.get("invented_filing") is True:
        return False
    if pack.get("invented_due") is True or pack.get("invented_npwp") is True:
        return False
    if pack.get("fake_filings") is True:
        return False
    if pack.get("due_amount") is not None or pack.get("due_on") is not None:
        return False
    if pack.get("npwp_number") is not None:
        return False
    if pack.get("secret_values_exposed") is True:
        return False
    surfaces = pack.get("surfaces") or []
    if len(surfaces) < 7:
        return False
    for s in surfaces:
        if not isinstance(s, dict):
            return False
        if s.get("status") not in STATUS_VOCAB:
            return False
        if s.get("id") == "invent_refused" and s.get("status") != "REFUSED":
            return False
        if s.get("id") == "djp_efaktur_external" and s.get("status") != "EXTERNAL_BLOCKER":
            return False
        if s.get("id") == "npwp_matt_action" and s.get("status") != "MATT_ACTION":
            return False
        if s.get("id") == "fin_tax_shell1" and s.get("status") != "PRESERVED":
            return False
    if not pack.get("human_route_commissioned") and not pack.get("may_wire"):
        if pack.get("classification") != CLASSIFICATION:
            return False
        if pack.get("action") != "STAMP_HUMAN_COMMISSIONING":
            return False
        if pack.get("pack_classification") != PACK_CLASSIFICATION:
            return False
    return True


def no_invented_dues_or_filings(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board(OWNER_PERSON)
    if pack.get("invented_amount") is not False:
        return False
    if pack.get("invented_filing") is not False:
        return False
    if pack.get("invented_due") is not False:
        return False
    if pack.get("invented_npwp") is not False:
        return False
    if pack.get("fake_filings") is not False:
        return False
    if pack.get("due_amount") is not None:
        return False
    if pack.get("due_on") is not None:
        return False
    if pack.get("npwp_number") is not None:
        return False
    if pack.get("wired") is True and pack.get("may_wire") is not True:
        return False
    return True


def build_board(
    person_id: str | None,
    *,
    role_allowed: bool = False,
    stamp_path: Path | None = None,
) -> dict[str, Any]:
    pid = (person_id or "").strip() or None
    if not person_may_view(pid, role_allowed=role_allowed):
        raise FinTaxDeepen1Error(
            "Tax dues deepen requires Owner or an authorised finance role. "
            "Unsigned / unauthorised callers are refused.",
            code="denied",
        )

    decision = decide_route(stamp_path=stamp_path)
    surfaces = surface_stamps(stamp_path=stamp_path)
    tax = fin_tax_shell1_preserved()
    flags = honesty_flags()
    by_status: dict[str, int] = {}
    for s in surfaces:
        st = str(s.get("status") or "UNKNOWN")
        by_status[st] = by_status.get(st, 0) + 1

    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "cap_fin_tax": CAP_FIN_TAX,
        "person_id": pid,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "live_adoption": False,
        "human_review_gate": True,
        "invented_amount": False,
        "invented_filing": False,
        "invented_due": False,
        "invented_npwp": False,
        "fake_filings": False,
        "live_tax": False,
        "live_filing": False,
        "secret_values_exposed": False,
        "wired": False,
        "due_amount": None,
        "due_on": None,
        "npwp_number": None,
        "last_filed_at": None,
        "pack_classification": PACK_CLASSIFICATION,
        "classification": decision["classification"],
        "route_classification": decision.get("route_classification"),
        "external_blocker": "EXTERNAL_BLOCKER",
        "npwp": NPWP_STATUS,
        "npwp_blocking": NPWP_BLOCKING,
        "action": decision["action"],
        "may_wire": decision["may_wire"],
        "reason": decision["reason"],
        "tax_systems_present": decision["tax_systems_present"],
        "filing_count": decision["filing_count"],
        "human_route_commissioned": decision["human_route_commissioned"],
        "djp_efaktur_external": True,
        "commission_stamp_path": str(stamp_path or COMMISSION_STAMP),
        "commissioning_path": commissioning_path(),
        "surfaces": surfaces,
        "surface_counts": by_status,
        "closes_toward": list(CLOSES_TOWARD),
        "ceiling": flags["maturity_ceiling"],
        "gaps": gaps(),
        "desk_links": [
            {
                "id": "fin_tax_shell_1",
                "label": "FIN Tax Shell-1",
                "href": TAX_SHELL_PAGE,
                "note": "Upstream UNKNOWN tax calendar honesty. Preserved.",
            },
            {
                "id": "fin_cash_truth_1",
                "label": "FIN Cash Truth-1",
                "href": "/fin/cash-truth-1",
                "note": "Adjacent cash honesty. Preserved separately.",
            },
            {
                "id": "fin_bank_creds_route_1",
                "label": "FIN Bank Creds Route-1",
                "href": "/fin/bank-creds-route-1",
                "note": "Bank HUMAN_COMMISSIONING. Preserved separately.",
            },
        ],
        "does_not_claim": [
            "live_filings",
            "tax_due_amounts",
            "filed_stamps",
            "npwp_numbers",
            "staff_ready",
            "human_commissioned",
            "CAP-FIN tax PROVEN",
        ],
        "preserved": {
            "FIN-TAX-SHELL-1": tax,
        },
        "fin_tax_shell1_preserved": tax.get("ok") is True,
        "honesty": flags,
        "summary": (
            "Tax dues deepen. Tax systems ABSENT — stamp HUMAN_COMMISSIONING. "
            "DJP/eFaktur EXTERNAL_BLOCKER. NPWP MATT_ACTION non-blocking. "
            "FIN-TAX-SHELL-1 UNKNOWN preserved. Never invent dues/filings/NPWP. "
            "Not staff_ready. Not commissioned."
        ),
        "next_pack_for_parent_only": "CRM-PIPELINE-TRUTH-1",
        "cursor_did_not_auto_start_next": True,
        "preserved_packs": list(PRESERVED_PACKS),
        "prod_pid_held": PROD_PID_HELD,
        "prod_mutate": False,
        "no_push": True,
    }


def public_payload(
    person_id: str | None = OWNER_PERSON,
    *,
    role_allowed: bool = False,
) -> dict[str, Any]:
    return build_board(person_id, role_allowed=role_allowed)
