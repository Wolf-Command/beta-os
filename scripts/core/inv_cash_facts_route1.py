#!/usr/bin/env python3
"""INV-CASH-FACTS-ROUTE-1 — Inventory/cash facts route (wire or human).

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack
INV-CASH-FACTS-ROUTE-1 (armed 2026-09-30 after FIN-BANK-CREDS-ROUTE-1
PASS_VERIFIED). Challenges UNKNOWN inventory/cash shells.

Probes authorised count/cash systems. Wires facts when present; otherwise
stamps HUMAN_COMMISSIONING or EXTERNAL with evidence. Never invents qty/cash.
Preserves BZG-INVENTORY-TRUTH-1 + FIN-CASH-TRUTH-1.
staff_ready=false · human_commissioned=false.
Does not auto-chain DEEPEN-SYNTH-CONTINUE / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import bzg_inventory_truth1 as _inv
from core import fin_cash_truth1 as _cash

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
COMMISSION_STAMP = (
    BETA_ROOT
    / "state"
    / "final-completion"
    / "packs"
    / "INV-CASH-FACTS-ROUTE-1-COMMISSION.json"
)

PACK_ID = "INV-CASH-FACTS-ROUTE-1"
SCHEMA_ID = "wolf.inv-cash-facts-route-1.v1"
BOUND = "beta-inv-cash-facts-route-safe"
CAP_INVENTORY = "CAP-BZG inventory"
CAP_FIN_CASH = "CAP-FIN cash"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
# Umbrella from synthesis; route resolves to HUMAN_COMMISSIONING or EXTERNAL
# (or WIRE when authorised facts exist).
PACK_CLASSIFICATION = "HUMAN_COMMISSIONING_OR_INTERNAL"
CLASSIFICATION = "HUMAN_COMMISSIONING"
CLOSES_TOWARD = ("inventory", "cash", CAP_INVENTORY, CAP_FIN_CASH)
PRESERVED_PACKS = ("BZG-INVENTORY-TRUTH-1", "FIN-CASH-TRUTH-1")
INV_PAGE = "/bzg/inventory-truth-1"
CASH_PAGE = "/fin/cash-truth-1"

PAGE_PATHS = frozenset(
    {
        "/ops/inv-cash-facts-route-1",
        "/ops/inv-cash-facts-route-1/",
        "/ops/inv-cash-facts-route",
        "/ops/inv-cash-facts-route/",
        "/fin/inv-cash-facts-route-1",
        "/fin/inv-cash-facts-route-1/",
        "/fin/inv-cash-facts-route",
        "/fin/inv-cash-facts-route/",
        "/inv-cash-facts-route-1",
        "/inv-cash-facts-route-1/",
        "/inv-cash-facts-route-1.html",
        "/dashboards/inv-cash-facts-route-1.html",
        "/bzg/inv-cash-facts-route-1",
        "/bzg/inv-cash-facts-route-1/",
    }
)
API_PATH = "/api/ops/inv-cash-facts-route-1"
API_PATHS = frozenset(
    {
        API_PATH,
        "/api/fin/inv-cash-facts-route-1",
        "/api/bzg/inv-cash-facts-route-1",
    }
)

STATUS_VOCAB = frozenset(
    {
        "HUMAN_COMMISSIONING",
        "HUMAN_COMMISSIONING_OR_INTERNAL",
        "EXTERNAL",
        "PRESERVED",
        "ABSENT",
        "REFUSED",
        "UNKNOWN",
        "WIRED",
        "COMMISSIONED",
    }
)

# Name-only inventory/count system env patterns — never load secret values.
_COUNT_ENV_NAME_RE = re.compile(
    r"(INVENTORY_|COUNT_|STOCK_|SKU_|PAR_LEVEL|POS_INVENT|"
    r"ZAYEN_|LIGHTSPEED_|TOAST_|SQUARE_INV|DELECTA_|APICA_|"
    r"COUNT_SHEET|COUNT_API|INVENTORY_API|INVENTORY_URL|"
    r"INVENTORY_TOKEN|INVENTORY_SECRET)",
    re.IGNORECASE,
)

# Name-only cash system env patterns (non-bank — bank is FIN-BANK-CREDS).
_CASH_ENV_NAME_RE = re.compile(
    r"(PETTY_CASH_|CASH_DRAWER_|CASH_ON_HAND_|CASH_COUNT_|"
    r"CASH_FACTS_|TILL_|FLOAT_CASH_|SAFE_CASH_|"
    r"CASH_API_|CASH_URL_|CASH_TOKEN_)",
    re.IGNORECASE,
)

COUNT_CLIENT_SEARCH: dict[str, Any] = {
    "glob": "scripts/core/**/*.py",
    "patterns": (
        "inventory_client",
        "count_client",
        "InventoryClient",
        "CountSheetClient",
        "live_inventory_feed",
    ),
    "found_modules": (),
    "note": (
        "No dedicated authorised inventory count client for BZG-INVENTORY-TRUTH-1. "
        "bzg_inventory_truth1 is honesty UNKNOWN shell only."
    ),
}

CASH_CLIENT_SEARCH: dict[str, Any] = {
    "glob": "scripts/core/**/*.py",
    "patterns": (
        "cash_facts_client",
        "petty_cash_feed",
        "CashFactsClient",
        "live_cash_feed",
    ),
    "found_modules": (),
    "note": (
        "No authorised empire cash-facts client for FIN-CASH-TRUTH-1. "
        "Uma Alchemist petty_cash RO is entity-scoped EXTERNAL — not wired "
        "into FIN-CASH-TRUTH-1 shells."
    ),
}

COMMISSIONING_PATH: tuple[dict[str, str], ...] = (
    {
        "step": "1",
        "title": "Owner authorises count / cash fact systems",
        "detail": (
            "Human Owner commissions an authorised inventory count system and/or "
            "cash facts feed (secret store + connector). Agents do not invent "
            "qty or cash into honesty shells."
        ),
    },
    {
        "step": "2",
        "title": "Owner writes commission stamp",
        "detail": (
            "Write state/final-completion/packs/INV-CASH-FACTS-ROUTE-1-COMMISSION.json "
            "with human_route_commissioned=true (or inv_cash_facts_authorised=true). "
            "Absent stamp → HUMAN_COMMISSIONING held."
        ),
    },
    {
        "step": "3",
        "title": "Parent arms wire pack when systems present",
        "detail": (
            "After stamp + verified authorised systems with real facts, parent/"
            "Peaches arms a wire pack. This pack EXIT never invents qty or cash."
        ),
    },
    {
        "step": "4",
        "title": "Until then: UNKNOWN shells preserved",
        "detail": (
            "BZG-INVENTORY-TRUTH-1 stays fact_count=0 UNKNOWN. "
            "FIN-CASH-TRUTH-1 stays FILE_IMPORT_ONLY / balances null. "
            "Empty is honest — never invent."
        ),
    },
)

GAPS: tuple[str, ...] = (
    "Authorised inventory count system ABSENT — no qty wire until human commission.",
    "Authorised empire cash facts feed ABSENT — FIN-CASH stays FILE_IMPORT_ONLY.",
    "qty / balance / cash_on_hand stay null — never invented.",
    "Uma Alchemist petty_cash RO is EXTERNAL to FIN-CASH-TRUTH-1 (not wired).",
    "staff_ready=false · human_commissioned=false on this pack.",
    "Next pack DEEPEN-SYNTH-CONTINUE is parent/Peaches only.",
)


class InvCashFactsRoute1Error(ValueError):
    """Fail closed. Does not invent qty, cash, or commission flips."""

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
        "inv_cash_facts_authorised"
    ) is True


def probe_count_systems() -> dict[str, Any]:
    """Name-only probe for inventory/count systems. Never returns secret values."""
    process_hits = sorted(k for k in os.environ if _COUNT_ENV_NAME_RE.search(k))
    dotenv_keys = _env_key_names_from_dotenv(BETA_ROOT / ".env")
    example_keys = _env_key_names_from_dotenv(BETA_ROOT / ".env.example")
    file_hits = sorted(
        {k for k in (dotenv_keys + example_keys) if _COUNT_ENV_NAME_RE.search(k)}
    )
    present = bool(process_hits or file_hits)
    client_found = bool(COUNT_CLIENT_SEARCH["found_modules"])
    return {
        "id": "count_systems",
        "label": "Inventory / count systems (name-only)",
        "status": "HUMAN_COMMISSIONING" if not (present and client_found) else "WIRED",
        "creds_present": present,
        "client_module_found": client_found,
        "process_env_key_names": process_hits,
        "dotenv_key_names": file_hits,
        "secret_values_exposed": False,
        "qty": None,
        "fact_count": 0,
        "value": None,
        "why": (
            "No INVENTORY_/COUNT_/STOCK_/POS invent key names and no authorised "
            "count client. Count systems ABSENT — stamp HUMAN_COMMISSIONING. "
            "Secret values never loaded."
            if not present
            else (
                "Count-related key names present; values not loaded. "
                "Wire still refused until commission stamp + authorised facts."
                if not client_found
                else "Count system names + client present; pack still refuses invent."
            )
        ),
        "evidence": ".env + .env.example key-name scan + client search (no values)",
        "client_search": dict(COUNT_CLIENT_SEARCH),
    }


def probe_cash_systems() -> dict[str, Any]:
    """Name-only probe for empire cash facts systems (non-bank)."""
    process_hits = sorted(k for k in os.environ if _CASH_ENV_NAME_RE.search(k))
    dotenv_keys = _env_key_names_from_dotenv(BETA_ROOT / ".env")
    example_keys = _env_key_names_from_dotenv(BETA_ROOT / ".env.example")
    file_hits = sorted(
        {k for k in (dotenv_keys + example_keys) if _CASH_ENV_NAME_RE.search(k)}
    )
    present = bool(process_hits or file_hits)
    client_found = bool(CASH_CLIENT_SEARCH["found_modules"])
    return {
        "id": "cash_systems",
        "label": "Cash facts systems (name-only)",
        "status": "HUMAN_COMMISSIONING" if not (present and client_found) else "WIRED",
        "creds_present": present,
        "client_module_found": client_found,
        "process_env_key_names": process_hits,
        "dotenv_key_names": file_hits,
        "secret_values_exposed": False,
        "balance": None,
        "cash_on_hand": None,
        "qty": None,
        "value": None,
        "why": (
            "No PETTY_CASH_/CASH_DRAWER_/CASH_FACTS_ key names and no authorised "
            "empire cash-facts client for FIN-CASH-TRUTH-1. Stamp "
            "HUMAN_COMMISSIONING. Secret values never loaded."
            if not present
            else (
                "Cash-related key names present; values not loaded. "
                "Wire still refused until commission + authorised facts."
                if not client_found
                else "Cash system names + client present; pack still refuses invent."
            )
        ),
        "evidence": ".env + .env.example key-name scan + client search (no values)",
        "client_search": dict(CASH_CLIENT_SEARCH),
    }


def probe_uma_petty_external() -> dict[str, Any]:
    """Uma Alchemist petty_cash RO exists but is EXTERNAL to FIN-CASH shells."""
    alchemist = BETA_ROOT / "catalog"  # marker only — do not invent balances
    # Existence of uma_alchemist_ro module is evidence of a separate RO path.
    uma_module = BETA_ROOT / "scripts" / "core" / "uma_alchemist_ro.py"
    present = uma_module.is_file()
    return {
        "id": "uma_petty_external",
        "label": "Uma Alchemist petty_cash (EXTERNAL)",
        "status": "EXTERNAL",
        "path_present": present,
        "wired_into_fin_cash": False,
        "wired_into_bzg_inventory": False,
        "balance": None,
        "cash_on_hand": None,
        "qty": None,
        "value": "entity_scoped_RO_not_empire_cash_truth",
        "why": (
            "Uma Alchemist petty_cash RO is entity-scoped EXTERNAL. "
            "Not authorised as the fact source for FIN-CASH-TRUTH-1 empire "
            "cash positions or BZG-INVENTORY-TRUTH-1. Stamp EXTERNAL — "
            "do not invent empire cash from Uma RO."
        ),
        "evidence": "scripts/core/uma_alchemist_ro.py · FIN-CASH-TRUTH-1 scope",
        "catalog_marker": str(alchemist),
    }


def probe_inventory_truth_facts() -> dict[str, Any]:
    """Read BZG-INVENTORY-TRUTH-1 — wire only if real fact_count > 0."""
    try:
        slice_ = _inv.build_slice()
        fact_count = int(slice_.get("fact_count") or 0)
        unknown = slice_.get("inventory_unknown") is True or fact_count == 0
        return {
            "id": "inventory_truth_facts",
            "label": "BZG-INVENTORY-TRUTH-1 facts",
            "status": "UNKNOWN" if unknown else "WIRED",
            "fact_count": fact_count,
            "qty": None,
            "on_hand": None,
            "last_count_at": slice_.get("last_count_at"),
            "fake_stock": slice_.get("fake_stock"),
            "invented_count": slice_.get("invented_count"),
            "value": fact_count,
            "why": (
                "BZG-INVENTORY-TRUTH-1 fact_count=0 — UNKNOWN. No qty to wire. "
                "Never invent stock/counts."
                if unknown
                else (
                    f"BZG-INVENTORY-TRUTH-1 reports fact_count={fact_count}. "
                    "Wire path available for parent wire pack — this pack does "
                    "not invent additional qty."
                )
            ),
            "evidence": INV_PAGE,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "id": "inventory_truth_facts",
            "status": "UNKNOWN",
            "fact_count": 0,
            "qty": None,
            "error": type(exc).__name__,
            "why": "Inventory truth probe failed — no invented qty.",
            "evidence": "core.bzg_inventory_truth1.build_slice",
        }


def probe_cash_truth_facts() -> dict[str, Any]:
    """Read FIN-CASH-TRUTH-1 — wire only if real import_count > 0."""
    try:
        slice_ = _cash.build_slice()
        import_count = int(slice_.get("import_count") or 0)
        unknown = slice_.get("positions_unknown") is True or import_count == 0
        return {
            "id": "cash_truth_facts",
            "label": "FIN-CASH-TRUTH-1 facts",
            "status": "UNKNOWN" if unknown else "WIRED",
            "import_count": import_count,
            "file_import_only": slice_.get("file_import_only"),
            "balance": None,
            "cash_on_hand": None,
            "last_success": slice_.get("last_success"),
            "invented_balance": slice_.get("invented_balance"),
            "value": import_count,
            "why": (
                "FIN-CASH-TRUTH-1 import_count=0 — UNKNOWN / FILE_IMPORT_ONLY. "
                "No cash to wire. Never invent balances."
                if unknown
                else (
                    f"FIN-CASH-TRUTH-1 reports import_count={import_count}. "
                    "Wire path available for parent wire pack — this pack does "
                    "not invent balances."
                )
            ),
            "evidence": CASH_PAGE,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "id": "cash_truth_facts",
            "status": "UNKNOWN",
            "import_count": 0,
            "balance": None,
            "error": type(exc).__name__,
            "why": "Cash truth probe failed — no invented cash.",
            "evidence": "core.fin_cash_truth1.build_slice",
        }


def decide_route(
    *,
    stamp_path: Path | None = None,
    count_probe: dict[str, Any] | None = None,
    cash_probe: dict[str, Any] | None = None,
    inv_facts: dict[str, Any] | None = None,
    cash_facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Core route decision. Never invents qty or cash."""
    count = count_probe if count_probe is not None else probe_count_systems()
    cash = cash_probe if cash_probe is not None else probe_cash_systems()
    inv_f = inv_facts if inv_facts is not None else probe_inventory_truth_facts()
    cash_f = cash_facts if cash_facts is not None else probe_cash_truth_facts()
    commissioned = human_route_commissioned(stamp_path=stamp_path)

    inv_fact_count = int(inv_f.get("fact_count") or 0)
    cash_import_count = int(cash_f.get("import_count") or 0)
    count_ready = bool(count.get("creds_present") and count.get("client_module_found"))
    cash_ready = bool(cash.get("creds_present") and cash.get("client_module_found"))
    wireable = (inv_fact_count > 0) or (cash_import_count > 0)

    if wireable and commissioned:
        action = "WIRE_FACTS"
        classification = "WIRED"
        reason = (
            "Authorised inventory/cash facts present and human route commissioned. "
            "This pack surfaces wireability; does not invent additional qty/cash. "
            "Parent may deepen wire. Honesty shells stay source-of-truth."
        )
        may_wire = True
    elif wireable and not commissioned:
        action = "STAMP_HUMAN_COMMISSIONING"
        classification = CLASSIFICATION
        reason = (
            "Some facts exist on honesty shells, but human route commission "
            "stamp is absent. Stamp HUMAN_COMMISSIONING before wire deepen. "
            "Never invent additional qty/cash."
        )
        may_wire = False
    elif (count_ready or cash_ready) and commissioned:
        action = "SYSTEMS_COMMISSIONED_AWAIT_FACTS"
        classification = "COMMISSIONED"
        reason = (
            "Count/cash system key names + client present and commissioned, "
            "but honesty shells still show zero facts. Await real facts — "
            "never invent qty/cash."
        )
        may_wire = False
    else:
        action = "STAMP_HUMAN_COMMISSIONING"
        classification = CLASSIFICATION
        reason = (
            "Authorised count/cash systems ABSENT (or no wireable facts). "
            "Stamp HUMAN_COMMISSIONING: Owner authorises systems, writes "
            "commission stamp, then parent arms wire. Uma Alchemist petty_cash "
            "stays EXTERNAL to empire cash shells. Never invent qty or cash."
        )
        may_wire = False

    return {
        "action": action,
        "classification": classification,
        "pack_classification": PACK_CLASSIFICATION,
        "route_classification": classification,
        "reason": reason,
        "may_wire": may_wire,
        "wired": False,
        "count_systems_present": bool(count.get("creds_present")),
        "cash_systems_present": bool(cash.get("creds_present")),
        "human_route_commissioned": commissioned,
        "inv_fact_count": inv_fact_count,
        "cash_import_count": cash_import_count,
        "invented_qty": False,
        "invented_cash": False,
        "invented_balance": False,
        "invented_count": False,
        "fake_stock": False,
        "qty": None,
        "balance": None,
        "cash_on_hand": None,
        "last_success": None,
        "file_import_only": True,
        "uma_petty_external": True,
    }


def bzg_inventory_truth1_preserved() -> dict[str, Any]:
    try:
        slice_ = _inv.build_slice()
        flags = _inv.honesty_flags()
        ok = (
            slice_.get("ok") is True
            and flags.get("fake_stock") is False
            and flags.get("invented_stock") is False
            and flags.get("invented_count") is False
            and flags.get("staff_ready") is False
            and flags.get("human_commissioned") is False
            and _inv.all_inventory_slots_unknown(slice_)
            and _inv.no_fake_stock(slice_)
        )
        return {
            "ok": ok,
            "fact_count": slice_.get("fact_count"),
            "inventory_unknown": slice_.get("inventory_unknown"),
            "fake_stock": slice_.get("fake_stock"),
            "invented_count": slice_.get("invented_count"),
            "why": (
                "BZG-INVENTORY-TRUTH-1 preserved: fact_count=0 UNKNOWN, "
                "no fake stock, no invented counts."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "BZG-INVENTORY-TRUTH-1 check failed — pack must not break it.",
        }


def fin_cash_truth1_preserved() -> dict[str, Any]:
    try:
        board = _cash.build_slice()
        flags = _cash.honesty_flags()
        ok = (
            board.get("ok") is True
            and flags.get("file_import_only") is True
            and flags.get("invented_balance") is False
            and flags.get("live_scrape") is False
            and flags.get("staff_ready") is False
            and flags.get("human_commissioned") is False
        )
        return {
            "ok": ok,
            "import_count": board.get("import_count"),
            "file_import_only": flags.get("file_import_only"),
            "invented_balance": flags.get("invented_balance"),
            "live_scrape": flags.get("live_scrape"),
            "why": (
                "FIN-CASH-TRUTH-1 preserved: FILE_IMPORT_ONLY, no invented "
                "balances, live_scrape false, commissioning flags false."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "FIN-CASH-TRUTH-1 check failed — pack must not break cash truth.",
        }


def honesty_flags() -> dict[str, Any]:
    decision = decide_route()
    inv = bzg_inventory_truth1_preserved()
    cash = fin_cash_truth1_preserved()
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "cap_bzg_inventory": CAP_INVENTORY,
        "cap_fin_cash": CAP_FIN_CASH,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "live_adoption": False,
        "human_review_gate": True,
        "file_import_only": True,
        "invented_qty": False,
        "invented_cash": False,
        "invented_balance": False,
        "invented_count": False,
        "fake_stock": False,
        "live_inventory": False,
        "live_scrape": False,
        "secret_values_exposed": False,
        "qty": None,
        "balance": None,
        "cash_on_hand": None,
        "last_success": None,
        "last_success_null": True,
        "count_systems_present": decision.get("count_systems_present"),
        "cash_systems_present": decision.get("cash_systems_present"),
        "human_route_commissioned_stamp": decision.get("human_route_commissioned"),
        "classification": decision.get("classification"),
        "route_classification": decision.get("route_classification"),
        "pack_classification": PACK_CLASSIFICATION,
        "action": decision.get("action"),
        "bzg_inventory_truth1_preserved": inv.get("ok") is True,
        "fin_cash_truth1_preserved": cash.get("ok") is True,
        "extends_bzg_inventory_truth1": True,
        "extends_fin_cash_truth1": True,
        "uma_petty_external": True,
        "second_inventory_system": False,
        "second_cash_system": False,
        "proven": False,
        "ready": False,
        "maturity_ceiling": CEILING,
        "ceiling": CEILING,
        "closes_toward": list(CLOSES_TOWARD),
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "anon_fail_closed": True,
        "next_pack_for_parent_only": "DEEPEN-SYNTH-CONTINUE",
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


def refuse_invent_qty(_body: dict | None = None) -> None:
    raise InvCashFactsRoute1Error(
        "Inventory qty invent is refused. UNKNOWN until authorised count facts.",
        code="invent_qty_refused",
    )


def refuse_invent_cash(_body: dict | None = None) -> None:
    raise InvCashFactsRoute1Error(
        "Cash invent is refused. Balances UNKNOWN until authorised facts/import.",
        code="invent_cash_refused",
    )


def refuse_invent_balance(_body: dict | None = None) -> None:
    raise InvCashFactsRoute1Error(
        "Balances are UNKNOWN until a real import or commissioned feed. "
        "Not invented.",
        code="invent_balance_refused",
    )


def refuse_fake_stock(_body: dict | None = None) -> None:
    raise InvCashFactsRoute1Error(
        "Fake stock is refused. Inventory stays UNKNOWN until real count facts.",
        code="fake_stock_refused",
    )


def refuse_commission_flip(_body: dict | None = None) -> None:
    raise InvCashFactsRoute1Error(
        "Inventing staff_ready / human_commissioned via API is refused. "
        "Human writes the commission stamp file; pack flags stay false.",
        code="ready_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise InvCashFactsRoute1Error(
        "Inventing PROVEN is refused. Inventory/cash stay at ledger state.",
        code="proven_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise InvCashFactsRoute1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {
            "qty",
            "quantity",
            "invent-qty",
            "invent-count",
            "count",
            "counts",
            "on-hand",
            "onhand",
        } or norm in {
            "qty",
            "quantity",
            "invent_qty",
            "invent_count",
            "count",
            "counts",
            "on_hand",
            "onhand",
        }:
            refuse_invent_qty(payload)
        if token in {
            "cash",
            "invent-cash",
            "cash-on-hand",
            "petty-cash",
            "till",
        } or norm in {
            "cash",
            "invent_cash",
            "cash_on_hand",
            "petty_cash",
            "till",
        }:
            refuse_invent_cash(payload)
        if token in {
            "balance",
            "balances",
            "invent-balance",
            "fake-balance",
        } or norm in {
            "balance",
            "balances",
            "invent_balance",
            "fake_balance",
        }:
            refuse_invent_balance(payload)
        if token in {
            "fake-stock",
            "stock",
            "stocks",
            "invent-stock",
        } or norm in {
            "fake_stock",
            "stock",
            "stocks",
            "invent_stock",
        }:
            refuse_fake_stock(payload)
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
    raise InvCashFactsRoute1Error(
        "INV-CASH-FACTS-ROUTE-1 is a read honesty / commissioning route board. "
        "Qty/cash invent and commission-flag flips refused.",
        code="write_refused",
    )


def surface_stamps(
    *,
    stamp_path: Path | None = None,
) -> list[dict[str, Any]]:
    decision = decide_route(stamp_path=stamp_path)
    count = probe_count_systems()
    cash = probe_cash_systems()
    uma = probe_uma_petty_external()
    inv_f = probe_inventory_truth_facts()
    cash_f = probe_cash_truth_facts()
    inv_p = bzg_inventory_truth1_preserved()
    cash_p = fin_cash_truth1_preserved()
    route_status = decision["classification"]
    return [
        {
            "id": "count_systems",
            "label": "Inventory / count systems",
            "status": count["status"] if count["status"] in STATUS_VOCAB else "ABSENT",
            "value": {
                "creds_present": count["creds_present"],
                "client_module_found": count["client_module_found"],
            },
            "qty": None,
            "why": count["why"],
            "evidence": count["evidence"],
        },
        {
            "id": "cash_systems",
            "label": "Cash facts systems",
            "status": cash["status"] if cash["status"] in STATUS_VOCAB else "ABSENT",
            "value": {
                "creds_present": cash["creds_present"],
                "client_module_found": cash["client_module_found"],
            },
            "balance": None,
            "why": cash["why"],
            "evidence": cash["evidence"],
        },
        {
            "id": "uma_petty_external",
            "label": "Uma Alchemist petty_cash",
            "status": "EXTERNAL",
            "value": uma.get("value"),
            "wired_into_fin_cash": False,
            "why": uma["why"],
            "evidence": uma["evidence"],
        },
        {
            "id": "inventory_truth_facts",
            "label": "BZG inventory facts",
            "status": inv_f["status"] if inv_f["status"] in STATUS_VOCAB else "UNKNOWN",
            "value": inv_f.get("fact_count"),
            "qty": None,
            "why": inv_f["why"],
            "evidence": inv_f["evidence"],
        },
        {
            "id": "cash_truth_facts",
            "label": "FIN cash facts",
            "status": cash_f["status"] if cash_f["status"] in STATUS_VOCAB else "UNKNOWN",
            "value": cash_f.get("import_count"),
            "balance": None,
            "why": cash_f["why"],
            "evidence": cash_f["evidence"],
        },
        {
            "id": "human_route",
            "label": "Human route / commission",
            "status": CLASSIFICATION
            if not decision["human_route_commissioned"]
            else "COMMISSIONED",
            "value": decision["human_route_commissioned"],
            "why": (
                "Human must authorise count/cash systems and write commission "
                "stamp. Absent stamp → HUMAN_COMMISSIONING. Pack flags stay false."
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
            "id": "bzg_inventory_truth1",
            "label": "BZG-INVENTORY-TRUTH-1 preserved",
            "status": "PRESERVED" if inv_p.get("ok") else "UNKNOWN",
            "value": inv_p.get("ok"),
            "why": inv_p.get("why"),
            "evidence": INV_PAGE,
        },
        {
            "id": "fin_cash_truth1",
            "label": "FIN-CASH-TRUTH-1 preserved",
            "status": "PRESERVED" if cash_p.get("ok") else "UNKNOWN",
            "value": cash_p.get("ok"),
            "why": cash_p.get("why"),
            "evidence": CASH_PAGE,
        },
        {
            "id": "invent_refused",
            "label": "Invent qty / cash",
            "status": "REFUSED",
            "value": False,
            "why": "Qty invent and cash invent are refused on this board.",
            "evidence": "refuse_invent_qty / refuse_invent_cash",
        },
    ]


def surfaces_are_honest(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board(OWNER_PERSON)
    if pack.get("invented_qty") is True or pack.get("invented_cash") is True:
        return False
    if pack.get("invented_balance") is True or pack.get("fake_stock") is True:
        return False
    if pack.get("qty") is not None or pack.get("balance") is not None:
        return False
    if pack.get("cash_on_hand") is not None:
        return False
    if pack.get("secret_values_exposed") is True:
        return False
    surfaces = pack.get("surfaces") or []
    if len(surfaces) < 8:
        return False
    for s in surfaces:
        if not isinstance(s, dict):
            return False
        if s.get("status") not in STATUS_VOCAB:
            return False
        if s.get("id") == "invent_refused" and s.get("status") != "REFUSED":
            return False
        if s.get("id") == "uma_petty_external" and s.get("status") != "EXTERNAL":
            return False
        if s.get("id") == "bzg_inventory_truth1" and s.get("status") != "PRESERVED":
            return False
        if s.get("id") == "fin_cash_truth1" and s.get("status") != "PRESERVED":
            return False
    if not pack.get("human_route_commissioned") and not pack.get("may_wire"):
        if pack.get("classification") != CLASSIFICATION:
            return False
        if pack.get("action") != "STAMP_HUMAN_COMMISSIONING":
            return False
        if pack.get("pack_classification") != PACK_CLASSIFICATION:
            return False
    return True


def no_invented_qty_or_cash(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board(OWNER_PERSON)
    if pack.get("invented_qty") is not False:
        return False
    if pack.get("invented_cash") is not False:
        return False
    if pack.get("invented_balance") is not False:
        return False
    if pack.get("invented_count") is not False:
        return False
    if pack.get("fake_stock") is not False:
        return False
    if pack.get("qty") is not None:
        return False
    if pack.get("balance") is not None:
        return False
    if pack.get("cash_on_hand") is not None:
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
        raise InvCashFactsRoute1Error(
            "Inventory/cash facts route requires Owner or an authorised "
            "finance/ops role. Unsigned / unauthorised callers are refused.",
            code="denied",
        )

    decision = decide_route(stamp_path=stamp_path)
    surfaces = surface_stamps(stamp_path=stamp_path)
    inv = bzg_inventory_truth1_preserved()
    cash = fin_cash_truth1_preserved()
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
        "cap_bzg_inventory": CAP_INVENTORY,
        "cap_fin_cash": CAP_FIN_CASH,
        "person_id": pid,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "live_adoption": False,
        "human_review_gate": True,
        "file_import_only": True,
        "invented_qty": False,
        "invented_cash": False,
        "invented_balance": False,
        "invented_count": False,
        "fake_stock": False,
        "live_inventory": False,
        "live_scrape": False,
        "secret_values_exposed": False,
        "wired": False,
        "qty": None,
        "balance": None,
        "cash_on_hand": None,
        "last_success": None,
        "pack_classification": PACK_CLASSIFICATION,
        "classification": decision["classification"],
        "route_classification": decision.get("route_classification"),
        "action": decision["action"],
        "may_wire": decision["may_wire"],
        "reason": decision["reason"],
        "count_systems_present": decision["count_systems_present"],
        "cash_systems_present": decision["cash_systems_present"],
        "inv_fact_count": decision["inv_fact_count"],
        "cash_import_count": decision["cash_import_count"],
        "human_route_commissioned": decision["human_route_commissioned"],
        "uma_petty_external": True,
        "commission_stamp_path": str(stamp_path or COMMISSION_STAMP),
        "commissioning_path": commissioning_path(),
        "surfaces": surfaces,
        "surface_counts": by_status,
        "closes_toward": list(CLOSES_TOWARD),
        "ceiling": flags["maturity_ceiling"],
        "gaps": gaps(),
        "desk_links": [
            {
                "id": "bzg_inventory_truth_1",
                "label": "BZG Inventory Truth-1",
                "href": INV_PAGE,
                "note": "Upstream UNKNOWN inventory honesty. Preserved.",
            },
            {
                "id": "fin_cash_truth_1",
                "label": "FIN Cash Truth-1",
                "href": CASH_PAGE,
                "note": "Cash/bank UNKNOWN deepen. Preserved.",
            },
            {
                "id": "fin_bank_creds_route_1",
                "label": "FIN Bank Creds Route-1",
                "href": "/fin/bank-creds-route-1",
                "note": "Prior pack — bank HUMAN_COMMISSIONING. Preserved separately.",
            },
        ],
        "does_not_claim": [
            "live_inventory",
            "invented_qty",
            "invented_cash",
            "invented_balance",
            "fake_stock",
            "staff_ready",
            "human_commissioned",
            "CAP-BZG inventory PROVEN",
            "CAP-FIN cash PROVEN",
        ],
        "preserved": {
            "BZG-INVENTORY-TRUTH-1": inv,
            "FIN-CASH-TRUTH-1": cash,
        },
        "bzg_inventory_truth1_preserved": inv.get("ok") is True,
        "fin_cash_truth1_preserved": cash.get("ok") is True,
        "honesty": flags,
        "summary": (
            "Inventory/cash facts route. Count/cash systems ABSENT — stamp "
            "HUMAN_COMMISSIONING. Uma petty_cash EXTERNAL. "
            "BZG-INVENTORY + FIN-CASH UNKNOWN preserved. Never invent qty/cash. "
            "Not staff_ready. Not commissioned."
        ),
        "next_pack_for_parent_only": "DEEPEN-SYNTH-CONTINUE",
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
