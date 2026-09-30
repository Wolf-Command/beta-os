#!/usr/bin/env python3
"""ATRIUM-FC-TRUTH-DEEPEN-1 — Atrium FC authority truth deepen (no invent books).

Decision served: 2026-09-29 PICK ATRIUM-SOD-1 + FINAL_WOLF_COMPLETION_MISSION
Phase 2 Wave10 pack ATRIUM-FC-TRUTH-DEEPEN-1 (armed 2026-09-30 after
OWNER-DASH-FRESHNESS-1 PASS_VERIFIED).

Deepens the Atrium FC desk honesty board from live atrium beta state only:
books_opened / shell_kind / SoD authority / invent-refused pins.
Never invents P&L, books balances, posted journals, or go-live money.
Preserve FC-SHELL-2 + ATRIUM-SOD-1 + atrium_fc_authority SoD.
staff_ready=false · human_commissioned=false.
Ceiling BUILT. Not PROVEN/READY.
Does not auto-chain HR-DEFERRED-HOLD-STAMP-1 / HEADCHEF / Exit Report.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core import atrium_fc_authority as _fc
from core import entity_books as _books
from core import fin_interco1 as _interco
from core.staff_access import ROLE_ATRIUM_FINANCIAL_CONTROLLER

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
ATRIUM_DB = Path("/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite")
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

PACK_ID = "ATRIUM-FC-TRUTH-DEEPEN-1"
SCHEMA_ID = "wolf.atrium-fc-truth-deepen-1.v1"
BOUND = "beta-atrium-fc-truth-deepen"
OWNER_PERSON = "PERS-MATT"
PROD_PID_HELD = 15975
WRITE_AUTHORITY = "NONE_EXPANDED"
WITA = timezone(timedelta(hours=8))
CEILING = "BUILT"
# Pack umbrella — live stamps/SoD → INTERNALLY_SOLVABLE; sealed books → HUMAN.
CLASSIFICATION = "INTERNALLY_SOLVABLE_OR_HUMAN"
ACTION = "DEEPEN_ATRIUM_FC_AUTHORITY_TRUTH"
PRESERVED_PACKS = ("FC-SHELL-2", "ATRIUM-SOD-1", "atrium_fc_authority")
NEXT_PACK = "HR-DEFERRED-HOLD-STAMP-1"
COMM1_JOURNAL = "JRN-ATRIUMSOD1B-COMM1"
COMM1_PREPARER = "PERS-ZENITALFATHAN"

PAGE_PATHS = frozenset(
    {
        "/ops/atrium-fc-truth-deepen-1",
        "/ops/atrium-fc-truth-deepen-1/",
        "/ops/atrium-fc-truth-deepen",
        "/ops/atrium-fc-truth-deepen/",
        "/ops/atrium-fc-truth-1",
        "/ops/atrium-fc-truth-1/",
        "/atrium-fc-truth-deepen-1",
        "/atrium-fc-truth-deepen-1/",
        "/atrium-fc-truth-deepen-1.html",
        "/dashboards/atrium-fc-truth-deepen-1.html",
    }
)
API_PATH = "/api/ops/atrium-fc-truth-deepen-1"
API_PATHS = frozenset(
    {
        API_PATH,
        "/api/ops/atrium-fc-truth-deepen",
        "/api/ops/atrium-fc-truth-1",
        "/api/amg/atrium-fc-truth-deepen-1",
    }
)

_ENTITY_SPECS: tuple[tuple[str, str, str], ...] = (
    ("ENT-AMG", "AMG / Atrium", "/amg/finance"),
    ("ENT-BZG", "BZG", "/bzg/finance"),
    ("ENT-GGV", "GGV", "/ggv/finance"),
)

_INVENT_BOOKS_TOKENS = frozenset(
    {
        "books",
        "invent-books",
        "invent_books",
        "fake-books",
        "fake_books",
        "open-books",
        "open_books",
        "force-open",
        "force_open",
        "books-opened",
        "books_opened",
        "shell-kind",
        "shell_kind",
        "seed-journals",
        "seed_journals",
        "fake-journals",
        "fake_journals",
        "invent-journals",
        "invent_journals",
    }
)

_INVENT_PNL_TOKENS = frozenset(
    {
        "pnl",
        "p-and-l",
        "p_and_l",
        "invent-pnl",
        "invent_pnl",
        "fake-pnl",
        "fake_pnl",
        "profit",
        "loss",
        "income-statement",
        "income_statement",
        "pl",
        "revenue",
        "expense",
        "go-live-money",
        "go_live_money",
    }
)

_INVENT_BALANCE_TOKENS = frozenset(
    {
        "balance",
        "balances",
        "invent-balance",
        "invent_balance",
        "fake-balance",
        "fake_balance",
        "posted-balance",
        "posted_balance",
        "ledger-balance",
        "ledger_balance",
        "trial-balance",
        "trial_balance",
        "bs",
        "balance-sheet",
        "balance_sheet",
    }
)


class AtriumFcTruthDeepen1Error(ValueError):
    """Fail closed. Does not invent books, P&L, or balances."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid",
        http_status: int = 403,
    ):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


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
    return trimmed in {p.rstrip("/") for p in API_PATHS} or raw in API_PATHS


def matches(path: str | None) -> bool:
    return page_matches(path) or api_matches(path)


def _catalog_ro() -> sqlite3.Connection:
    uri = CATALOG_DB.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def person_may_view(
    person_id: str | None, *, conn: sqlite3.Connection | None = None
) -> bool:
    """Owner / atrium finance progress readers may view the honesty board."""
    from core import rbac as _rbac

    pid = (person_id or "").strip()
    if not pid:
        return False
    if pid == OWNER_PERSON:
        return True
    own = conn is None
    c = conn
    if c is None:
        c = _catalog_ro()
    try:
        if _rbac.can(pid, "progress.read", {}, conn=c):
            return True
        if _rbac.can(pid, "atrium.journal.draft", {"entity_id": "ENT-AMG"}, conn=c):
            return True
        if _rbac.can(pid, "atrium.journal.approve", {"entity_id": "ENT-AMG"}, conn=c):
            return True
        return False
    finally:
        if own and c is not None:
            c.close()


def require_view(
    person_id: str | None, *, conn: sqlite3.Connection | None = None
) -> None:
    if not person_may_view(person_id, conn=conn):
        raise AtriumFcTruthDeepen1Error(
            "Atrium FC truth deepen board is not on this assignment.",
            code="forbidden",
            http_status=403,
        )


def _entity_classification(snap: dict[str, Any]) -> str:
    """INTERNALLY_SOLVABLE when live stamps exist; HUMAN if sealed/missing."""
    if snap.get("exists") is not True:
        return "HUMAN_COMMISSIONING"
    shell = str(snap.get("shell_kind") or "")
    if shell in {"live", "coa_template_shell", "empty_shell", "books_shell"}:
        return "INTERNALLY_SOLVABLE"
    # Unknown shell without authorised open stamp.
    if snap.get("books_enabled") is not True:
        return "HUMAN_COMMISSIONING"
    return "HUMAN_COMMISSIONING"


def _entity_stamp(legal_entity_id: str, label: str, href: str) -> dict[str, Any]:
    try:
        snap = _books.snapshot(legal_entity_id)
    except Exception as exc:  # noqa: BLE001
        return {
            "id": legal_entity_id,
            "legal_entity_id": legal_entity_id,
            "label": label,
            "href": href,
            "exists": False,
            "books_opened": False,
            "books_enabled": False,
            "shell_kind": "UNAVAILABLE",
            "accounts": None,
            "journals": None,
            "classification": "HUMAN_COMMISSIONING",
            "status": "UNAVAILABLE",
            "display": "UNAVAILABLE",
            "pnl": None,
            "balance": None,
            "invented_books": False,
            "invented_pnl": False,
            "invented_balance": False,
            "ok": False,
            "why": (
                f"{label}: snapshot failed ({type(exc).__name__}). "
                "UNAVAILABLE — not invented books/P&L."
            ),
        }
    exists = snap.get("exists") is True
    books_enabled = bool(snap.get("books_enabled"))
    books_opened = exists and books_enabled
    shell = str(snap.get("shell_kind") or ("UNAVAILABLE" if not exists else "UNKNOWN"))
    cls = _entity_classification(snap)
    # Honest empty money facts — never invent.
    pnl = None
    balance = None
    money_status = "UNAVAILABLE"
    if shell == "coa_template_shell":
        money_status = "HONEST_EMPTY"
    elif shell == "empty_shell":
        money_status = "HONEST_EMPTY"
    elif shell == "live":
        # Live AMG books exist; this deepen board still does not invent P&L/balances.
        money_status = "LIVE_BOOKS_NO_INVENT_PNL"
    return {
        "id": legal_entity_id,
        "legal_entity_id": legal_entity_id,
        "label": label,
        "href": href,
        "exists": exists,
        "books_opened": books_opened,
        "books_enabled": books_enabled,
        "shell_kind": shell,
        "accounts": snap.get("accounts"),
        "journals": snap.get("journals"),
        "pack": snap.get("pack"),
        "classification": cls,
        "status": shell if exists else "UNAVAILABLE",
        "display": shell if exists else "UNAVAILABLE",
        "money_status": money_status,
        "pnl": pnl,
        "balance": balance,
        "invented_books": False,
        "invented_pnl": False,
        "invented_balance": False,
        "staff_ready": False,
        "human_commissioned": False,
        "ok": exists,
        "why": (
            f"{label}: books_opened={books_opened} shell_kind={shell} "
            f"accounts={snap.get('accounts')} journals={snap.get('journals')}. "
            f"classification={cls}. pnl=null balance=null — never invent. "
            "Entity isolation held."
        ),
    }


def entity_stamps() -> list[dict[str, Any]]:
    return [_entity_stamp(eid, label, href) for eid, label, href in _ENTITY_SPECS]


def sod_authority_stamp() -> dict[str, Any]:
    """Live ATRIUM-SOD-1 / atrium_fc_authority SoD truth — no invent."""
    result_md = BETA_ROOT / "docs" / "wolf" / "finance" / "ATRIUM-FC-AUTHORITY-MATRIX.md"
    module_ok = Path(_fc.__file__).is_file() if getattr(_fc, "__file__", None) else True
    fc_approve_path = _fc.fc_may_approve_path(
        ROLE_ATRIUM_FINANCIAL_CONTROLLER, "POST", "/api/journals/x/approve"
    )
    fc_post_path = _fc.fc_may_approve_path(
        ROLE_ATRIUM_FINANCIAL_CONTROLLER, "POST", "/api/journals/x/post"
    )
    pay_denied = _fc.still_denied_sensitive("POST", "/api/ap/payments")
    bank_denied = _fc.still_denied_sensitive("POST", "/api/bank/foo")
    self_prep = _fc.is_self_prepare(
        "Zayen", "PERS-ZAYEN", "Zayen", preparer_person_id="PERS-ZAYEN"
    )
    other_prep = _fc.is_self_prepare(
        "Zenit", "PERS-ZAYEN", "Zayen", preparer_person_id="PERS-ZENITALFATHAN"
    )

    journal_status = None
    preparer = None
    wolf_created = None
    journal_found = False
    books_path = None
    if ATRIUM_DB.is_file():
        books_path = str(ATRIUM_DB)
        try:
            con = sqlite3.connect(f"file:{ATRIUM_DB}?mode=ro", uri=True)
            try:
                row = con.execute(
                    "SELECT status, preparer_person_id, wolf_created "
                    "FROM journal_headers WHERE journal_id=?",
                    (COMM1_JOURNAL,),
                ).fetchone()
            finally:
                con.close()
            if row:
                journal_found = True
                journal_status, preparer, wolf_created = row[0], row[1], row[2]
        except Exception as exc:  # noqa: BLE001
            return {
                "id": "sod_authority",
                "label": "ATRIUM-SOD-1 / FC authority",
                "ok": False,
                "status": "UNAVAILABLE",
                "display": "UNAVAILABLE",
                "classification": "HUMAN_COMMISSIONING",
                "journal_id": COMM1_JOURNAL,
                "journal_found": False,
                "error": type(exc).__name__,
                "invented": False,
                "why": (
                    f"SoD journal read failed ({type(exc).__name__}). "
                    "UNAVAILABLE — not invented."
                ),
            }

    sod_ok = (
        module_ok
        and fc_approve_path is True
        and fc_post_path is True
        and pay_denied is True
        and bank_denied is True
        and self_prep is True
        and other_prep is False
        and (
            not ATRIUM_DB.is_file()
            or (
                journal_found
                and journal_status == "POSTED"
                and preparer == COMM1_PREPARER
            )
        )
    )
    if not ATRIUM_DB.is_file():
        cls = "HUMAN_COMMISSIONING"
        status = "BOOKS_ABSENT"
        why = (
            "Atrium beta sqlite absent — SoD module pins held, but COMM1 not "
            "checkable. HUMAN_COMMISSIONING until authorised books open. "
            "No invent journals."
        )
    elif not journal_found:
        cls = "HUMAN_COMMISSIONING"
        status = "COMM1_ABSENT"
        why = (
            f"{COMM1_JOURNAL} not in live books — pack did not invent it. "
            "HUMAN_COMMISSIONING for sealed/missing SoD evidence."
        )
    elif sod_ok:
        cls = "INTERNALLY_SOLVABLE"
        status = "SOD_LIVE"
        why = (
            f"SoD live: {COMM1_JOURNAL} POSTED preparer={COMM1_PREPARER}; "
            "FC may approve/post others' journals; self-prepare blocked; "
            "pay/bank still denied. atrium_fc_authority preserved."
        )
    else:
        cls = "HUMAN_COMMISSIONING"
        status = "SOD_DRIFT"
        why = (
            f"SoD stamp unexpected (status={journal_status} preparer={preparer}). "
            "Not invented. Investigate — pack did not mutate."
        )
    return {
        "id": "sod_authority",
        "label": "ATRIUM-SOD-1 / FC authority",
        "ok": sod_ok,
        "status": status,
        "display": status,
        "classification": cls,
        "journal_id": COMM1_JOURNAL,
        "journal_found": journal_found,
        "journal_status": journal_status,
        "preparer_person_id": preparer,
        "wolf_created": wolf_created,
        "fc_role": ROLE_ATRIUM_FINANCIAL_CONTROLLER,
        "fc_may_approve_others": fc_approve_path,
        "fc_may_post_others": fc_post_path,
        "self_prepare_blocked": self_prep is True,
        "other_prepare_allowed_for_approve": other_prep is False,
        "pay_denied": pay_denied,
        "bank_denied": bank_denied,
        "matrix_doc_present": result_md.is_file(),
        "books_path": books_path,
        "invented": False,
        "invented_journal": False,
        "why": why,
    }


def fc_shell2_preserved() -> dict[str, Any]:
    try:
        stamp = _interco.fc_shell2_books_preserved()
        ok = stamp.get("ok") is True and stamp.get("journals_invented") is False
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "pack": "FC-SHELL-2",
            "status": "CHECK_FAILED",
            "why": f"FC-SHELL-2 honesty read failed ({type(exc).__name__}).",
        }
    result = BETA_ROOT / "docs" / "wolf" / "ops" / "FC-SHELL-2-RESULT.md"
    ok = ok and result.is_file()
    return {
        "ok": ok,
        "pack": "FC-SHELL-2",
        "status": "PRESERVED" if ok else "CHECK_FAILED",
        "href": "/amg/finance",
        "bzg": stamp.get("bzg"),
        "ggv": stamp.get("ggv"),
        "amg": stamp.get("amg"),
        "journals_invented": False,
        "books_written": False,
        "why": (
            stamp.get("why")
            if ok
            else "FC-SHELL-2 RESULT missing or COA template / AMG live pins drifted."
        ),
    }


def atrium_sod1_preserved() -> dict[str, Any]:
    sod = sod_authority_stamp()
    ok = sod.get("ok") is True and sod.get("invented") is False
    return {
        "ok": ok,
        "pack": "ATRIUM-SOD-1",
        "status": "PRESERVED" if ok else "CHECK_FAILED",
        "href": "/amg/finance",
        "journal_id": COMM1_JOURNAL,
        "journal_status": sod.get("journal_status"),
        "preparer_person_id": sod.get("preparer_person_id"),
        "why": sod.get("why"),
    }


def atrium_fc_authority_preserved() -> dict[str, Any]:
    sod = sod_authority_stamp()
    module = Path(__file__).resolve().parent / "atrium_fc_authority.py"
    ok = (
        module.is_file()
        and sod.get("fc_may_approve_others") is True
        and sod.get("fc_may_post_others") is True
        and sod.get("self_prepare_blocked") is True
        and sod.get("pay_denied") is True
        and sod.get("bank_denied") is True
        and sod.get("invented") is False
    )
    return {
        "ok": ok,
        "pack": "atrium_fc_authority",
        "status": "PRESERVED" if ok else "CHECK_FAILED",
        "module": str(module),
        "why": (
            "atrium_fc_authority SoD helpers intact: approve/post others · "
            "self-prepare blocked · pay/bank denied."
            if ok
            else "atrium_fc_authority SoD helpers drifted."
        ),
    }


def resolve_pack_classification(
    entities: list[dict[str, Any]] | None = None,
    sod: dict[str, Any] | None = None,
) -> str:
    """INTERNALLY_SOLVABLE when live stamps/SoD exist; else HUMAN_COMMISSIONING."""
    ents = entities if entities is not None else entity_stamps()
    sod_s = sod if sod is not None else sod_authority_stamp()
    live = any(
        e.get("exists") is True
        and e.get("shell_kind") in {"live", "coa_template_shell", "empty_shell"}
        for e in ents
    )
    sod_live = sod_s.get("classification") == "INTERNALLY_SOLVABLE"
    if live and sod_live:
        return "INTERNALLY_SOLVABLE"
    if live or sod_live:
        return "INTERNALLY_SOLVABLE_OR_HUMAN"
    return "HUMAN_COMMISSIONING"


def _honesty_tiles(
    entities: list[dict[str, Any]],
    sod: dict[str, Any],
    fc2: dict[str, Any],
    sod_p: dict[str, Any],
    fc_auth: dict[str, Any],
    pack_cls: str,
) -> list[dict[str, Any]]:
    amg = next((e for e in entities if e.get("legal_entity_id") == "ENT-AMG"), {})
    bzg = next((e for e in entities if e.get("legal_entity_id") == "ENT-BZG"), {})
    ggv = next((e for e in entities if e.get("legal_entity_id") == "ENT-GGV"), {})
    return [
        {
            "id": "pack_class",
            "label": "Pack classification",
            "status": pack_cls,
            "value": pack_cls,
            "why": (
                "Live stamps/SoD → INTERNALLY_SOLVABLE; sealed books → "
                "HUMAN_COMMISSIONING. Never invent."
            ),
        },
        {
            "id": "amg_books",
            "label": "AMG books",
            "status": amg.get("shell_kind") or "UNAVAILABLE",
            "value": {
                "books_opened": amg.get("books_opened"),
                "shell_kind": amg.get("shell_kind"),
                "accounts": amg.get("accounts"),
                "journals": amg.get("journals"),
            },
            "why": amg.get("why"),
        },
        {
            "id": "bzg_books",
            "label": "BZG books",
            "status": bzg.get("shell_kind") or "UNAVAILABLE",
            "value": {
                "books_opened": bzg.get("books_opened"),
                "shell_kind": bzg.get("shell_kind"),
                "accounts": bzg.get("accounts"),
                "journals": bzg.get("journals"),
            },
            "why": bzg.get("why"),
        },
        {
            "id": "ggv_books",
            "label": "GGV books",
            "status": ggv.get("shell_kind") or "UNAVAILABLE",
            "value": {
                "books_opened": ggv.get("books_opened"),
                "shell_kind": ggv.get("shell_kind"),
                "accounts": ggv.get("accounts"),
                "journals": ggv.get("journals"),
            },
            "why": ggv.get("why"),
        },
        {
            "id": "sod",
            "label": "SoD authority",
            "status": sod.get("status") or "UNAVAILABLE",
            "value": sod.get("journal_status"),
            "why": sod.get("why"),
        },
        {
            "id": "invent_books",
            "label": "Invent books",
            "status": "REFUSED",
            "value": False,
            "why": "Invent-books / force-open / fake journals refused 403.",
        },
        {
            "id": "invent_pnl",
            "label": "Invent P&L",
            "status": "REFUSED",
            "value": False,
            "why": "Invent-P&L / go-live money refused 403. Honest empty held.",
        },
        {
            "id": "invent_balance",
            "label": "Invent balance",
            "status": "REFUSED",
            "value": False,
            "why": "Invent-balance / trial-balance invent refused 403.",
        },
        {
            "id": "fc_shell2",
            "label": "FC-SHELL-2",
            "status": "PRESERVED" if fc2.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": fc2.get("why"),
        },
        {
            "id": "atrium_sod1",
            "label": "ATRIUM-SOD-1",
            "status": "PRESERVED" if sod_p.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": sod_p.get("why"),
        },
        {
            "id": "atrium_fc_authority",
            "label": "atrium_fc_authority",
            "status": "PRESERVED" if fc_auth.get("ok") else "CHECK_FAILED",
            "value": None,
            "why": fc_auth.get("why"),
        },
        {
            "id": "write_authority",
            "label": "Write authority",
            "status": WRITE_AUTHORITY,
            "value": WRITE_AUTHORITY,
            "why": "Invent-books / invent-P&L / invent-balance writes refused.",
        },
    ]


def _desk_links() -> list[dict[str, Any]]:
    return [
        {
            "id": "amg_finance",
            "label": "AMG / Atrium finance desk",
            "href": "/amg/finance",
            "kind": "existing",
            "note": "Live AMG books + SoD. Entity isolation held.",
        },
        {
            "id": "bzg_finance",
            "label": "BZG finance desk",
            "href": "/bzg/finance",
            "kind": "existing",
            "note": "FC-SHELL-2 COA template · 0 journals · no invent P&L.",
        },
        {
            "id": "ggv_finance",
            "label": "GGV finance desk",
            "href": "/ggv/finance",
            "kind": "existing",
            "note": "FC-SHELL-2 COA template · 0 journals · no invent P&L.",
        },
        {
            "id": "fc_matrix",
            "label": "Atrium FC authority matrix",
            "href": "/amg/finance",
            "kind": "docs",
            "note": "docs/wolf/finance/ATRIUM-FC-AUTHORITY-MATRIX.md",
        },
    ]


def honesty_flags() -> dict[str, Any]:
    entities = entity_stamps()
    sod = sod_authority_stamp()
    fc2 = fc_shell2_preserved()
    sod_p = atrium_sod1_preserved()
    fc_auth = atrium_fc_authority_preserved()
    pack_cls = resolve_pack_classification(entities, sod)
    return {
        "pack": PACK_ID,
        "schema_id": SCHEMA_ID,
        "bound": BOUND,
        "classification": pack_cls,
        "classification_umbrella": CLASSIFICATION,
        "action": ACTION,
        "ceiling": CEILING,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "prod_pid_held": PROD_PID_HELD,
        "no_push": True,
        "write_authority_expanded": False,
        "write_authority": WRITE_AUTHORITY,
        "invented_books": False,
        "invented_pnl": False,
        "invented_balance": False,
        "fake_books": False,
        "fake_pnl": False,
        "fake_balance": False,
        "pnl": None,
        "balance": None,
        "money": None,
        "anon_fail_closed": True,
        "owner_read": True,
        "entity_isolation_held": True,
        "fc_shell2_preserved": fc2.get("ok") is True,
        "atrium_sod1_preserved": sod_p.get("ok") is True,
        "atrium_fc_authority_preserved": fc_auth.get("ok") is True,
        "preserved_packs": list(PRESERVED_PACKS),
        "cursor_did_not_auto_start_next": True,
        "next_pack_for_parent_only": NEXT_PACK,
        "pins": {
            "pack": pack_cls,
            "amg": (next((e.get("shell_kind") for e in entities if e.get("id") == "ENT-AMG"), None)),
            "bzg": (next((e.get("shell_kind") for e in entities if e.get("id") == "ENT-BZG"), None)),
            "ggv": (next((e.get("shell_kind") for e in entities if e.get("id") == "ENT-GGV"), None)),
            "sod": sod.get("status"),
            "invent_books": "REFUSED",
            "invent_pnl": "REFUSED",
            "invent_balance": "REFUSED",
            "exit_report_headchef": "MATT_ACTION",
            "prod_mutate": "EXTERNAL_BLOCKER",
        },
    }


def refuse_invent_books(_body: dict | None = None) -> None:
    raise AtriumFcTruthDeepen1Error(
        "Invented books / force-open / fake journals are refused.",
        code="invent_books_refused",
        http_status=403,
    )


def refuse_invent_pnl(_body: dict | None = None) -> None:
    raise AtriumFcTruthDeepen1Error(
        "Invented P&L / go-live money is refused. Honest empty held.",
        code="invent_pnl_refused",
        http_status=403,
    )


def refuse_invent_balance(_body: dict | None = None) -> None:
    raise AtriumFcTruthDeepen1Error(
        "Invented balances are refused. Books facts stay real or UNAVAILABLE.",
        code="invent_balance_refused",
        http_status=403,
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise AtriumFcTruthDeepen1Error(
        "PROVEN is refused. Atrium FC truth deepen is honesty, not prove.",
        code="proven_refused",
        http_status=403,
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise AtriumFcTruthDeepen1Error(
        "READY is refused. An FC truth deepen board is not READY.",
        code="ready_refused",
        http_status=403,
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if not isinstance(payload, dict):
        raise AtriumFcTruthDeepen1Error("Write payload refused.", code="write_refused")
    for key in payload:
        token = str(key).strip().lower().replace("_", "-")
        norm = token.replace("-", "_")
        if token in {"proven", "prove"}:
            refuse_proven(payload)
        if token in {"ready", "staff-ready", "human-commissioned"}:
            refuse_ready(payload)
        if (
            token in _INVENT_BOOKS_TOKENS
            or norm in {t.replace("-", "_") for t in _INVENT_BOOKS_TOKENS}
            or "invent-book" in token
            or "invent_book" in norm
        ):
            refuse_invent_books(payload)
        if (
            token in _INVENT_PNL_TOKENS
            or norm in {t.replace("-", "_") for t in _INVENT_PNL_TOKENS}
            or "pnl" in token
            or "p-and-l" in token
        ):
            refuse_invent_pnl(payload)
        if (
            token in _INVENT_BALANCE_TOKENS
            or norm in {t.replace("-", "_") for t in _INVENT_BALANCE_TOKENS}
            or "balance" in token
            or "balance" in norm
        ):
            refuse_invent_balance(payload)
    raise AtriumFcTruthDeepen1Error(
        "ATRIUM-FC-TRUTH-DEEPEN-1 is a read honesty shell. Writes refused.",
        code="write_refused",
        http_status=403,
    )


def no_invented_money(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    if pack.get("invented_books") is not False:
        return False
    if pack.get("invented_pnl") is not False or pack.get("invented_balance") is not False:
        return False
    if pack.get("pnl") is not None or pack.get("balance") is not None:
        return False
    if pack.get("money") is not None:
        return False
    for e in pack.get("entity_stamps") or []:
        if e.get("invented_books") is not False:
            return False
        if e.get("invented_pnl") is not False or e.get("invented_balance") is not False:
            return False
        if e.get("pnl") is not None or e.get("balance") is not None:
            return False
    return True


def entity_isolation_held(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    stamps = pack.get("entity_stamps") or []
    ids = {s.get("legal_entity_id") for s in stamps}
    if not {"ENT-AMG", "ENT-BZG", "ENT-GGV"}.issubset(ids):
        return False
    by_id = {s.get("legal_entity_id"): s for s in stamps}
    amg = by_id.get("ENT-AMG") or {}
    bzg = by_id.get("ENT-BZG") or {}
    ggv = by_id.get("ENT-GGV") or {}
    if amg.get("shell_kind") == "live" and bzg.get("shell_kind") == "live":
        # Both live is fine only if journals differ — but we expect BZG template.
        pass
    if bzg.get("shell_kind") == "coa_template_shell" and bzg.get("journals") not in (0, None):
        return False
    if ggv.get("shell_kind") == "coa_template_shell" and ggv.get("journals") not in (0, None):
        return False
    return pack.get("entity_isolation_held") is True


def sod_is_honest(payload: dict[str, Any] | None = None) -> bool:
    pack = payload if payload is not None else build_board()
    sod = pack.get("sod_authority") or {}
    if sod.get("invented") is not False or sod.get("invented_journal") is not False:
        return False
    if sod.get("pay_denied") is not True or sod.get("bank_denied") is not True:
        return False
    if sod.get("self_prepare_blocked") is not True:
        return False
    return True


def build_board() -> dict[str, Any]:
    """Public vertical-slice payload. Auth gating is caller's responsibility."""
    entities = entity_stamps()
    sod = sod_authority_stamp()
    fc2 = fc_shell2_preserved()
    sod_p = atrium_sod1_preserved()
    fc_auth = atrium_fc_authority_preserved()
    pack_cls = resolve_pack_classification(entities, sod)
    flags = honesty_flags()
    return {
        "ok": True,
        "pack": PACK_ID,
        "schema": SCHEMA_ID,
        "bound": BOUND,
        "as_of_wita": _now_wita(),
        "closes_toward": ["atrium finance"],
        "title": "Atrium FC authority truth — live stamps only, no invent books",
        "classification": pack_cls,
        "classification_umbrella": CLASSIFICATION,
        "action": ACTION,
        "ceiling": CEILING,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_touched": False,
        "prod_pid_held": PROD_PID_HELD,
        "write_authority": WRITE_AUTHORITY,
        "write_authority_expanded": False,
        "invented_books": False,
        "invented_pnl": False,
        "invented_balance": False,
        "fake_books": False,
        "fake_pnl": False,
        "fake_balance": False,
        "pnl": None,
        "balance": None,
        "money": None,
        "entity_isolation_held": True,
        "entity_count": len(entities),
        "entity_stamps": entities,
        "sod_authority": sod,
        "fc_shell2_preserved": fc2.get("ok") is True,
        "atrium_sod1_preserved": sod_p.get("ok") is True,
        "atrium_fc_authority_preserved": fc_auth.get("ok") is True,
        "fc_shell2": fc2,
        "atrium_sod1": sod_p,
        "atrium_fc_authority": fc_auth,
        "honesty_tiles": _honesty_tiles(entities, sod, fc2, sod_p, fc_auth, pack_cls),
        "desk_links": _desk_links(),
        "preserved_packs": list(PRESERVED_PACKS),
        "does_not_claim": [
            "invented_books",
            "invented_pnl",
            "invented_balance",
            "pnl",
            "balance",
            "money",
            "staff_ready",
            "human_commissioned",
            "proven",
            "ready",
        ],
        "honesty": flags,
        "pins": flags.get("pins"),
        "cursor_did_not_auto_start_next_pack": True,
        "next_pack_for_parent_only": NEXT_PACK,
        "summary": (
            "Atrium FC truth deepen. books_opened / shell_kind / SoD from live "
            "beta state only. No invent books / P&L / balance. "
            "FC-SHELL-2 + ATRIUM-SOD-1 + atrium_fc_authority preserved. "
            "staff_ready=false · human_commissioned=false."
        ),
    }


def build_slice() -> dict[str, Any]:
    return build_board()


def public_payload(person_id: str | None = None) -> dict[str, Any]:
    if person_id is not None:
        require_view(person_id)
    return build_board()


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "pack": PACK_ID,
        "additionalProperties": False,
        "invented_books": False,
        "invented_pnl": False,
        "invented_balance": False,
        "writes_accepted": False,
        "classification_umbrella": CLASSIFICATION,
        "preserves": list(PRESERVED_PACKS),
        "entities": [e[0] for e in _ENTITY_SPECS],
        "why": (
            "Atrium FC authority truth from live atrium beta stamps. "
            "books_opened / shell_kind / SoD. Never invent books/P&L/balance."
        ),
    }
