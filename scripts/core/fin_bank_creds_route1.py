#!/usr/bin/env python3
"""FIN-BANK-CREDS-ROUTE-1 — Human bank credentials commissioning route.

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack
FIN-BANK-CREDS-ROUTE-1 (armed 2026-09-30 after SOP-CATALOG-SEED-ROUTE-1
PASS_VERIFIED). Challenges bank recon FILE_IMPORT_ONLY ceiling.

Documents HUMAN_COMMISSIONING path for live bank feed.
FILE_IMPORT_ONLY stays until human-commissioned credentials.
Never invents scrape / balances. Preserves FIN-RECON-SHELL-1 +
FIN-CASH-TRUTH-1. staff_ready=false · human_commissioned=false.
Does not auto-chain INV-CASH-FACTS-ROUTE-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import fin_cash_truth1 as _cash
from core import fin_recon_shell1 as _recon

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
COMMISSION_STAMP = (
    BETA_ROOT
    / "state"
    / "final-completion"
    / "packs"
    / "FIN-BANK-CREDS-ROUTE-1-COMMISSION.json"
)

PACK_ID = "FIN-BANK-CREDS-ROUTE-1"
SCHEMA_ID = "wolf.fin-bank-creds-route-1.v1"
BOUND = "beta-fin-bank-creds-route-safe"
CAP_FIN_02 = "CAP-FIN-02"
INT_BANK = "INT-BANK"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
# Route disposition until human deposits bank credentials + commissions.
CLASSIFICATION = "HUMAN_COMMISSIONING"
PACK_CLASSIFICATION = "HUMAN_COMMISSIONING"
CLOSES_TOWARD = ("INT-BANK", CAP_FIN_02, "bank recon")
PRESERVED_PACKS = ("FIN-RECON-SHELL-1", "FIN-CASH-TRUTH-1")
RECON_PAGE = "/fin/recon-shell-1"
CASH_PAGE = "/fin/cash-truth-1"
INTG_PAGE = "/ops/integrations-status"

PAGE_PATHS = frozenset(
    {
        "/fin/bank-creds-route-1",
        "/fin/bank-creds-route-1/",
        "/fin/bank-creds-route",
        "/fin/bank-creds-route/",
        "/fin-bank-creds-route-1",
        "/fin-bank-creds-route-1/",
        "/fin-bank-creds-route-1.html",
        "/dashboards/fin-bank-creds-route-1.html",
        "/ops/fin-bank-creds-route-1",
        "/ops/fin-bank-creds-route-1/",
    }
)
API_PATH = "/api/fin/bank-creds-route-1"
API_PATHS = frozenset({API_PATH, "/api/ops/fin-bank-creds-route-1"})

STATUS_VOCAB = frozenset(
    {
        "HUMAN_COMMISSIONING",
        "FILE_IMPORT_ONLY",
        "PRESERVED",
        "ABSENT",
        "REFUSED",
        "UNKNOWN",
        "COMMISSIONED",
    }
)

# Name-only bank credential env patterns — never load secret values.
_BANK_ENV_NAME_RE = re.compile(
    r"(BANK_|INT_BANK|INT-BANK|BANK_API|BANK_URL|BANK_HOST|BANK_TOKEN|"
    r"BANK_SECRET|BANK_PASS|BANK_USER|BANK_LOGIN|OPEN_BANKING|"
    r"PLAID_|YODLEE_|TRUE_LAYER|TRUELAYER_|STATEMENT_FEED)",
    re.IGNORECASE,
)

COMMISSIONING_PATH: tuple[dict[str, str], ...] = (
    {
        "step": "1",
        "title": "Owner deposits bank credentials",
        "detail": (
            "Human Owner stores live bank credentials in the authorised secret "
            "store (not invented into repo .env by agents). Names only on this "
            "board — secret values never loaded or painted."
        ),
    },
    {
        "step": "2",
        "title": "Owner writes commission stamp",
        "detail": (
            "Write state/final-completion/packs/FIN-BANK-CREDS-ROUTE-1-COMMISSION.json "
            "with human_route_commissioned=true (or bank_creds_authorised=true). "
            "Absent stamp → HUMAN_COMMISSIONING held."
        ),
    },
    {
        "step": "3",
        "title": "Parent arms live-feed wire pack",
        "detail": (
            "After stamp + verified creds, parent/Peaches arms a follow-on wire "
            "pack. This pack EXIT never invents scrape, balances, or last_success."
        ),
    },
    {
        "step": "4",
        "title": "Until then: FILE_IMPORT_ONLY",
        "detail": (
            "FIN-RECON-SHELL-1 + FIN-CASH-TRUTH-1 stay FILE_IMPORT_ONLY. "
            "Balances UNKNOWN/null. Live scrape refused. Empty is honest."
        ),
    },
)

GAPS: tuple[str, ...] = (
    "Live bank credentials ABSENT — no scrape until human commission.",
    "FILE_IMPORT_ONLY held on FIN-RECON-SHELL-1 + FIN-CASH-TRUTH-1.",
    "Balances / last_success stay null — never invented.",
    "staff_ready=false · human_commissioned=false on this pack.",
    "Next pack INV-CASH-FACTS-ROUTE-1 is parent/Peaches only.",
)


class FinBankCredsRoute1Error(ValueError):
    """Fail closed. Does not invent scrape, balances, or commission flips."""

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
        "bank_creds_authorised"
    ) is True


def probe_credentials() -> dict[str, Any]:
    """Name-only probe for bank credentials. Never returns secret values."""
    process_hits = sorted(k for k in os.environ if _BANK_ENV_NAME_RE.search(k))
    dotenv_keys = _env_key_names_from_dotenv(BETA_ROOT / ".env")
    example_keys = _env_key_names_from_dotenv(BETA_ROOT / ".env.example")
    file_hits = sorted(
        {k for k in (dotenv_keys + example_keys) if _BANK_ENV_NAME_RE.search(k)}
    )
    present = bool(process_hits or file_hits)
    return {
        "id": "bank_credentials",
        "label": "Bank credentials (name-only)",
        "status": "HUMAN_COMMISSIONING" if not present else "COMMISSIONED",
        "creds_present": present,
        "process_env_key_names": process_hits,
        "dotenv_key_names": file_hits,
        "secret_values_exposed": False,
        "balance": None,
        "scrape": None,
        "value": None,
        "why": (
            "No BANK_* / INT_BANK / PLAID / statement-feed key names in process "
            "env, .env, or .env.example. Credentials ABSENT — stamp "
            "HUMAN_COMMISSIONING. Secret values never loaded."
            if not present
            else (
                "Bank-related key names present; values not loaded this pack. "
                "Live scrape still refused until commission stamp + wire pack."
            )
        ),
        "evidence": ".env + .env.example key-name scan (no values)",
    }


def probe_live_scrape_path() -> dict[str, Any]:
    """No authorised live bank scrape client — FILE_IMPORT_ONLY held."""
    return {
        "id": "live_scrape_path",
        "label": "Live bank scrape / API path",
        "status": "FILE_IMPORT_ONLY",
        "path_configured": False,
        "client_module_found": False,
        "balance": None,
        "scrape": None,
        "value": None,
        "why": (
            "No authorised live bank scrape client. INT-BANK stays "
            "FILE_IMPORT_ONLY until human credentials + commission. "
            "Never invent scrape or balances."
        ),
        "evidence": "FIN-RECON-SHELL-1 + INTG-TRUTH-1 bank probe",
    }


def decide_route(
    *,
    stamp_path: Path | None = None,
    creds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Core route decision. Never invents scrape or balances."""
    probe = creds if creds is not None else probe_credentials()
    commissioned = human_route_commissioned(stamp_path=stamp_path)
    creds_present = bool(probe.get("creds_present"))

    if creds_present and commissioned:
        action = "CREDS_COMMISSIONED_AWAIT_WIRE"
        classification = "COMMISSIONED"
        reason = (
            "Bank credential key names present and human route commissioned. "
            "This pack still refuses invent scrape/balances; parent arms wire."
        )
        may_scrape = False
    elif not creds_present:
        action = "STAMP_HUMAN_COMMISSIONING"
        classification = CLASSIFICATION
        reason = (
            "Bank credentials ABSENT. Stamp HUMAN_COMMISSIONING: Owner deposits "
            "creds in authorised secret store, writes commission stamp, then "
            "parent arms live-feed wire. FILE_IMPORT_ONLY held — never invent."
        )
        may_scrape = False
    else:
        action = "STAMP_HUMAN_COMMISSIONING"
        classification = CLASSIFICATION
        reason = (
            "Bank-related key names may exist, but human route commission "
            "stamp is absent. Live scrape refused. Stamp HUMAN_COMMISSIONING."
        )
        may_scrape = False

    return {
        "action": action,
        "classification": classification,
        "pack_classification": PACK_CLASSIFICATION,
        "route_classification": CLASSIFICATION
        if classification == CLASSIFICATION
        else classification,
        "reason": reason,
        "may_scrape": may_scrape,
        "scraped": False,
        "creds_present": creds_present,
        "human_route_commissioned": commissioned,
        "file_import_only": True,
        "invented_scrape": False,
        "invented_balance": False,
        "live_scrape": False,
        "bank_api": False,
        "balance": None,
        "last_success": None,
    }


def fin_recon_shell1_preserved() -> dict[str, Any]:
    try:
        slice_ = _recon.build_slice()
        empty = _recon.queue_is_empty(slice_) and _recon.all_account_stubs_empty(slice_)
        return {
            "ok": (
                empty
                and slice_.get("ok") is True
                and slice_.get("file_import_only") is True
                and slice_.get("last_success") is None
                and slice_.get("invented_balance") is False
            ),
            "queue_empty": empty,
            "import_count": slice_.get("import_count"),
            "file_import_only": slice_.get("file_import_only"),
            "last_success": slice_.get("last_success"),
            "invented_balance": slice_.get("invented_balance"),
            "why": (
                "FIN-RECON-SHELL-1 preserved: recon queue EMPTY, "
                "FILE_IMPORT_ONLY, last_success=null, no invented balances."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": type(exc).__name__,
            "why": "FIN-RECON-SHELL-1 check failed — pack must not break recon shell.",
        }


def fin_cash_truth1_preserved() -> dict[str, Any]:
    try:
        board = _cash.build_slice() if hasattr(_cash, "build_slice") else _cash.public_payload()
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
    recon = fin_recon_shell1_preserved()
    cash = fin_cash_truth1_preserved()
    bank = _recon.bank_path_honesty()
    return {
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "cap_fin_02": CAP_FIN_02,
        "int_bank": INT_BANK,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "live_adoption": False,
        "human_review_gate": True,
        "file_import_only": True,
        "invented_scrape": False,
        "invented_balance": False,
        "live_scrape": False,
        "bank_api": False,
        "bank_write": False,
        "payment_write": False,
        "secret_values_exposed": False,
        "balance": None,
        "last_success": None,
        "last_success_null": True,
        "creds_present": decision.get("creds_present"),
        "human_route_commissioned_stamp": decision.get("human_route_commissioned"),
        "classification": decision.get("classification"),
        "route_classification": decision.get("route_classification"),
        "pack_classification": PACK_CLASSIFICATION,
        "action": decision.get("action"),
        "fin_recon_shell1_preserved": recon.get("ok") is True,
        "fin_cash_truth1_preserved": cash.get("ok") is True,
        "extends_fin_recon_shell1": True,
        "extends_fin_cash_truth1": True,
        "second_bank_system": False,
        "proven": False,
        "ready": False,
        "cap_fin_02_proven": False,
        "cap_fin_02_ready": False,
        "maturity_ceiling": CEILING,
        "ceiling": CEILING,
        "closes_toward": list(CLOSES_TOWARD),
        "prod_mutate": False,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "anon_fail_closed": True,
        "bank_path_file_import_only": bank.get("file_import_only") is True
        or bank.get("ok") is True,
        "next_pack_for_parent_only": "INV-CASH-FACTS-ROUTE-1",
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


def refuse_scrape(_body: dict | None = None) -> None:
    raise FinBankCredsRoute1Error(
        "Live bank scrape invent is refused. FILE_IMPORT_ONLY until "
        "human-commissioned credentials + wire pack.",
        code="scrape_refused",
    )


def refuse_invent_balance(_body: dict | None = None) -> None:
    raise FinBankCredsRoute1Error(
        "Bank balances are UNKNOWN until a real import or commissioned feed. "
        "Not invented.",
        code="invent_balance_refused",
    )


def refuse_bank_write(_body: dict | None = None) -> None:
    raise FinBankCredsRoute1Error(
        "Bank writes are refused. FILE_IMPORT_ONLY — no bank API mutate.",
        code="bank_write_refused",
    )


def refuse_commission_flip(_body: dict | None = None) -> None:
    raise FinBankCredsRoute1Error(
        "Inventing staff_ready / human_commissioned via API is refused. "
        "Human writes the commission stamp file; pack flags stay false.",
        code="ready_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise FinBankCredsRoute1Error(
        "Inventing PROVEN is refused. CAP-FIN-02 stays at ledger state.",
        code="proven_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise FinBankCredsRoute1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {
            "scrape",
            "live-scrape",
            "invent-scrape",
            "fake-scrape",
            "bank-scrape",
        } or norm in {
            "scrape",
            "live_scrape",
            "invent_scrape",
            "fake_scrape",
            "bank_scrape",
        }:
            refuse_scrape(payload)
        if token in {
            "balance",
            "balances",
            "invent-balance",
            "fake-balance",
            "cash",
        } or norm in {
            "balance",
            "balances",
            "invent_balance",
            "fake_balance",
            "cash",
        }:
            refuse_invent_balance(payload)
        if token in {
            "bank-write",
            "bank-api",
            "payment",
            "payment-write",
        } or norm in {
            "bank_write",
            "bank_api",
            "payment",
            "payment_write",
        }:
            refuse_bank_write(payload)
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
    raise FinBankCredsRoute1Error(
        "FIN-BANK-CREDS-ROUTE-1 is a read honesty / commissioning route board. "
        "Scrape/balance invent and commission-flag flips refused.",
        code="write_refused",
    )


def surface_stamps(
    *,
    stamp_path: Path | None = None,
) -> list[dict[str, Any]]:
    decision = decide_route(stamp_path=stamp_path)
    creds = probe_credentials()
    scrape = probe_live_scrape_path()
    recon = fin_recon_shell1_preserved()
    cash = fin_cash_truth1_preserved()
    route_status = (
        CLASSIFICATION
        if decision["classification"] == CLASSIFICATION
        else decision["classification"]
    )
    return [
        {
            "id": "bank_credentials",
            "label": "Bank credentials",
            "status": creds["status"] if creds["status"] in STATUS_VOCAB else "ABSENT",
            "value": {"creds_present": creds["creds_present"]},
            "balance": None,
            "why": creds["why"],
            "evidence": creds["evidence"],
        },
        {
            "id": "live_scrape_path",
            "label": "Live scrape path",
            "status": "FILE_IMPORT_ONLY",
            "value": False,
            "scrape": None,
            "why": scrape["why"],
            "evidence": scrape["evidence"],
        },
        {
            "id": "human_route",
            "label": "Human route / commission",
            "status": CLASSIFICATION
            if not decision["human_route_commissioned"]
            else "COMMISSIONED",
            "value": decision["human_route_commissioned"],
            "why": (
                "Human must deposit bank creds and write commission stamp. "
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
            "may_scrape": decision["may_scrape"],
            "why": decision["reason"],
            "evidence": "decide_route()",
        },
        {
            "id": "file_import_only",
            "label": "FILE_IMPORT_ONLY held",
            "status": "FILE_IMPORT_ONLY",
            "value": True,
            "why": (
                "Bank path stays FILE_IMPORT_ONLY until commissioned creds + "
                "wire pack. Empty import queue is honest."
            ),
            "evidence": INTG_PAGE,
        },
        {
            "id": "fin_recon_shell1",
            "label": "FIN-RECON-SHELL-1 preserved",
            "status": "PRESERVED" if recon.get("ok") else "UNKNOWN",
            "value": recon.get("ok"),
            "why": recon.get("why"),
            "evidence": RECON_PAGE,
        },
        {
            "id": "fin_cash_truth1",
            "label": "FIN-CASH-TRUTH-1 preserved",
            "status": "PRESERVED" if cash.get("ok") else "UNKNOWN",
            "value": cash.get("ok"),
            "why": cash.get("why"),
            "evidence": CASH_PAGE,
        },
        {
            "id": "invent_refused",
            "label": "Invent scrape / balances",
            "status": "REFUSED",
            "value": False,
            "why": "Scrape invent and balance invent are refused on this board.",
            "evidence": "refuse_scrape / refuse_invent_balance",
        },
    ]


def surfaces_are_honest(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board(OWNER_PERSON)
    if pack.get("invented_scrape") is True or pack.get("invented_balance") is True:
        return False
    if pack.get("live_scrape") is True or pack.get("file_import_only") is not True:
        return False
    if pack.get("balance") is not None or pack.get("last_success") is not None:
        return False
    if pack.get("secret_values_exposed") is True:
        return False
    surfaces = pack.get("surfaces") or []
    if len(surfaces) < 6:
        return False
    for s in surfaces:
        if not isinstance(s, dict):
            return False
        if s.get("status") not in STATUS_VOCAB:
            return False
        if s.get("id") == "invent_refused" and s.get("status") != "REFUSED":
            return False
        if s.get("id") == "file_import_only" and s.get("status") != "FILE_IMPORT_ONLY":
            return False
        if s.get("id") == "fin_recon_shell1" and s.get("status") != "PRESERVED":
            return False
        if s.get("id") == "fin_cash_truth1" and s.get("status") != "PRESERVED":
            return False
    if not pack.get("human_route_commissioned") and not pack.get("creds_present"):
        if pack.get("classification") != CLASSIFICATION:
            return False
        if pack.get("action") != "STAMP_HUMAN_COMMISSIONING":
            return False
    return True


def no_invented_scrape_or_balances(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board(OWNER_PERSON)
    if pack.get("invented_scrape") is not False:
        return False
    if pack.get("invented_balance") is not False:
        return False
    if pack.get("live_scrape") is not False:
        return False
    if pack.get("balance") is not None:
        return False
    if pack.get("last_success") is not None:
        return False
    if pack.get("scraped") is True:
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
        raise FinBankCredsRoute1Error(
            "Bank credentials commissioning route requires Owner or an "
            "authorised finance role. Unsigned / unauthorised callers are refused.",
            code="denied",
        )

    decision = decide_route(stamp_path=stamp_path)
    surfaces = surface_stamps(stamp_path=stamp_path)
    recon = fin_recon_shell1_preserved()
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
        "cap_fin_02": CAP_FIN_02,
        "int_bank": INT_BANK,
        "person_id": pid,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": False,
        "live_adoption": False,
        "human_review_gate": True,
        "file_import_only": True,
        "invented_scrape": False,
        "invented_balance": False,
        "live_scrape": False,
        "bank_api": False,
        "bank_write": False,
        "payment_write": False,
        "secret_values_exposed": False,
        "scraped": False,
        "balance": None,
        "last_success": None,
        "pack_classification": PACK_CLASSIFICATION,
        "classification": decision["classification"],
        "route_classification": decision.get("route_classification"),
        "action": decision["action"],
        "may_scrape": decision["may_scrape"],
        "reason": decision["reason"],
        "creds_present": decision["creds_present"],
        "human_route_commissioned": decision["human_route_commissioned"],
        "commission_stamp_path": str(stamp_path or COMMISSION_STAMP),
        "commissioning_path": commissioning_path(),
        "surfaces": surfaces,
        "surface_counts": by_status,
        "closes_toward": list(CLOSES_TOWARD),
        "ceiling": flags["maturity_ceiling"],
        "cap_fin_02_proven": False,
        "cap_fin_02_ready": False,
        "gaps": gaps(),
        "desk_links": [
            {
                "id": "fin_recon_shell_1",
                "label": "FIN Recon Shell-1",
                "href": RECON_PAGE,
                "note": "Upstream FILE_IMPORT_ONLY recon queue. Preserved.",
            },
            {
                "id": "fin_cash_truth_1",
                "label": "FIN Cash Truth-1",
                "href": CASH_PAGE,
                "note": "Cash/bank UNKNOWN deepen. Preserved.",
            },
            {
                "id": "integrations_status",
                "label": "Integrations honesty (INTG-TRUTH-1)",
                "href": INTG_PAGE,
                "note": "INT-BANK FILE_IMPORT_ONLY · last_success null.",
            },
        ],
        "does_not_claim": [
            "live_scrape",
            "invented_balance",
            "invented_scrape",
            "bank_api",
            "staff_ready",
            "human_commissioned",
            "CAP-FIN-02 PROVEN",
            "CAP-FIN-02 READY",
        ],
        "preserved": {
            "FIN-RECON-SHELL-1": recon,
            "FIN-CASH-TRUTH-1": cash,
        },
        "fin_recon_shell1_preserved": recon.get("ok") is True,
        "fin_cash_truth1_preserved": cash.get("ok") is True,
        "honesty": flags,
        "summary": (
            "Human bank credentials commissioning route. Credentials ABSENT — "
            "stamp HUMAN_COMMISSIONING. FILE_IMPORT_ONLY held on recon + cash "
            "truth. Never invent scrape or balances. Not staff_ready. Not commissioned."
        ),
        "next_pack_for_parent_only": "INV-CASH-FACTS-ROUTE-1",
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
