#!/usr/bin/env python3
"""CAP-SALE-03 buyer mode / controlled export framework (Beta, read-only).

Decision served: 2026-09-20 PICK, buyer mode / controlled export framework on
Beta only (docs/deliveries/GROK-PLAN-SALE-BUYER-MODE-FRAMEWORK-2026-09-19.md).

Names approved company-specific diligence surfaces and a company-specific Ask
context slot. Crown jewels and cross-company intelligence stay hidden. Export
slots stay empty. This module does not grant a buyer, issue a share, write an
export, or invent PROVEN or READY.

Honesty is bound to CR-b428ac5cbc8986b5 when that row is present. Ledger
maturity is read, not written. The skeleton ceiling is BUILT unless the
ledger is already PROVEN or READY.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from core import sale_evidence_pack as evidence

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

CR_ID = "CR-b428ac5cbc8986b5"
CAP_ID = "CAP-SALE-03"
CANON_CONTROLS = evidence.CANON_CONTROLS
ENTITY_ORDER = ("GGV", "AMG", "BZG")

MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})

# Named hides. Spec sections 24 and 25. Contents are not read.
HIDE_SPECS: tuple[dict[str, str], ...] = (
    {
        "id": "HIDE-CROWN-PLAYBOOK",
        "hide_class": "crown_jewel",
        "name": "Full Wolf backup playbook",
        "why": "Spec section 25 keeps the full backup playbook Matt-only. This framework does not open it.",
    },
    {
        "id": "HIDE-CROWN-REGISTRY",
        "hide_class": "crown_jewel",
        "name": "Technology and Provider Registry",
        "why": "Spec section 25 keeps the full Technology and Provider Registry Matt-only. This framework does not copy it.",
    },
    {
        "id": "HIDE-CROWN-WOLF-IP",
        "hide_class": "crown_jewel",
        "name": "Generic Wolf IP and architecture",
        "why": "Spec section 24 keeps generic Wolf IP and architecture Matt-owned. This framework does not copy it.",
    },
    {
        "id": "HIDE-CROSS-COMPANY",
        "hide_class": "cross_company",
        "name": "Cross-company intelligence",
        "why": "Spec section 24 hides cross-company intelligence. Companies are not blended here.",
    },
)

GAPS: tuple[str, ...] = (
    "No live buyer is granted.",
    "No share link is issued.",
    "No controlled export file is written.",
    "Every export slot stays empty.",
    "Crown jewels are named and stay hidden. They are not opened.",
    "Cross-company intelligence is named and stays hidden. Companies are not blended.",
    "Ask context is named per company. No Ask answer is copied.",
    "Source diligence text is not copied onto a surface.",
    "This read does not change the ledger and does not close the completion row.",
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "sale_buyer_mode",
    "read_only": True,
    "framework_skeleton": "BUILT",
    "on_disk": False,
    "buyer_access": False,
    "buyer_grant": False,
    "live_share": False,
    "buyer_export": False,
    "controlled_export": False,
    "export_written": False,
    "crown_jewels_opened": False,
    "cross_company_exposed": False,
    "ask_answered": False,
    "documents_invented": False,
    "filled_exports_invented": False,
    "score_changed": False,
    "production_write": False,
    "production": False,
    "alchemist_write": False,
    "external_writes": False,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "anon_fail_closed": True,
}

_RESERVED = {
    "SURFACES": "not_found",
    "HIDES": "not_found",
    "EXPORTS": "not_found",
    "EXPORT": "export",
    "DOWNLOAD": "export",
    "GRANT": "grant",
    "BUYER": "grant",
    "ACCESS": "grant",
    "SHARE": "share",
    "REVEAL": "reveal",
    "UNHIDE": "reveal",
    "FILL": "fill",
    "UPLOAD": "fill",
    "PRODUCTION": "production",
    "BLEND": "cross",
    "CROSS": "cross",
}


class BuyerModeError(ValueError):
    """Fail closed. Does not grant a buyer, export a pack, or open a hide."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_export(_body: dict | None = None) -> None:
    """A controlled export would write a buyer pack. This slice does not."""
    raise BuyerModeError(
        "Controlled export is refused. Export slots stay empty. This framework does not write a pack.",
        code="buyer_export_refused",
    )


def refuse_grant(_body: dict | None = None) -> None:
    """No buyer is granted. Owner read is not a buyer grant."""
    raise BuyerModeError(
        "Buyer grant is refused. This framework does not grant a buyer.",
        code="buyer_grant_refused",
    )


def refuse_share(_body: dict | None = None) -> None:
    """A live share link is not this skeleton."""
    raise BuyerModeError(
        "Live share is refused. This framework does not issue a share link.",
        code="buyer_share_refused",
    )


def refuse_reveal(_body: dict | None = None) -> None:
    """Crown jewels and cross-company intelligence stay hidden."""
    raise BuyerModeError(
        "Hidden surfaces stay hidden. This framework does not open crown jewels or cross-company intelligence.",
        code="hide_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    """Export slots are not filled by this framework."""
    raise BuyerModeError(
        "Buyer mode does not fill an export slot.",
        code="fill_refused",
    )


def refuse_cross(_body: dict | None = None) -> None:
    """A blend across companies is the hide, not a view."""
    raise BuyerModeError(
        "Cross-company intelligence stays hidden. This framework does not blend companies.",
        code="cross_company_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    """Production is not this tree."""
    raise BuyerModeError(
        "Production mutation is refused. This framework does not write Production.",
        code="production_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    """Every mutation path ends here. Nothing is written."""
    payload = body or {}
    export = str(payload.get("export") or "").strip().lower()
    action = str(payload.get("action") or "").strip().lower()
    if payload.get("production") or payload.get("mutate_production") or action == "production":
        refuse_production(payload)
    if payload.get("alchemist") or action == "alchemist":
        raise BuyerModeError("buyer mode refuses an Alchemist write", code="alchemist_refused")
    if payload.get("share") or payload.get("live_share") or export == "share" or action == "share":
        refuse_share(payload)
    if (
        payload.get("reveal")
        or payload.get("unhide")
        or payload.get("open_playbook")
        or payload.get("crown_jewels")
        or action in {"reveal", "unhide"}
    ):
        refuse_reveal(payload)
    if payload.get("blend") or payload.get("cross_company") or action in {"blend", "cross"}:
        refuse_cross(payload)
    if (
        payload.get("buyer_export")
        or payload.get("download")
        or payload.get("controlled_export")
        or export in {"buyer", "buyer-mode", "buyer_mode", "export", "vdr", "1", "true"}
        or action in {"export", "download"}
    ):
        refuse_export(payload)
    if (
        payload.get("buyer")
        or payload.get("buyer_mode")
        or payload.get("buyer_access")
        or payload.get("grant")
        or payload.get("buyer_grant")
        or action == "grant"
    ):
        refuse_grant(payload)
    if any(payload.get(key) not in (None, "", False) for key in ("document", "filename", "fill", "upload", "file", "pack")):
        refuse_fill(payload)
    raise BuyerModeError(
        "Buyer mode is read-only. No grant, no share, and no filled export.",
        code="writes_refused",
    )


def _truthy(value: str | None) -> bool:
    return bool((value or "").strip())


def guard_query(
    *,
    export: str | None = None,
    fill: str | None = None,
    share: str | None = None,
    grant: str | None = None,
    buyer: str | None = None,
    reveal: str | None = None,
    unhide: str | None = None,
    cross: str | None = None,
    blend: str | None = None,
    production: str | None = None,
) -> None:
    """A read that asks to grant, share, export, or unhide is still a write."""
    if _truthy(production):
        refuse_production()
    if _truthy(share):
        refuse_share()
    if _truthy(reveal) or _truthy(unhide):
        refuse_reveal()
    if _truthy(cross) or _truthy(blend):
        refuse_cross()
    if _truthy(export):
        refuse_export()
    if _truthy(grant) or _truthy(buyer):
        refuse_grant()
    if _truthy(fill):
        refuse_fill()


def _guard_path(path: Path) -> None:
    text = str(path)
    low = text.lower()
    if "alchemist" in low:
        raise BuyerModeError("buyer mode refuses an Alchemist path", code="alchemist_refused")
    if low.endswith("money.sqlite") or "/production" in low:
        raise BuyerModeError("buyer mode refuses a production path", code="not_beta")
    resolved = path.resolve()
    try:
        resolved.relative_to(BETA_ROOT)
        return
    except ValueError:
        pass
    tmp = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.relative_to(tmp)
    except ValueError as exc:
        raise BuyerModeError(
            "buyer mode refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc
    if "wolf-system" in low:
        raise BuyerModeError("buyer mode refuses a wolf-system fixture path", code="not_beta")


def _maturity(value: str) -> str:
    token = (value or "").strip().upper()
    if token in MATURITY:
        return token
    return "UNKNOWN"


def _load_names(csv_path: Path | str | None) -> list[dict[str, Any]]:
    """Control names only. Source text is dropped here and is not returned."""
    try:
        rows = evidence.load_controls(csv_path)
    except evidence.SalePackError as exc:
        code = "duplicate_surface" if exc.code == "duplicate_control" else exc.code
        raise BuyerModeError(str(exc), code=code) from exc
    named: list[dict[str, Any]] = []
    for row in rows:
        named.append(
            {
                "id": str(row.get("id") or ""),
                "entity": row.get("entity"),
                "area": row.get("area"),
                "domain": row.get("domain") or "UNKNOWN",
                "unexpected_entity": bool(row.get("unexpected_entity")),
            }
        )
    return named


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-SALE-03 from the ledger. Does not write it."""
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    _guard_path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    row = data.get(CAP_ID) if isinstance(data, dict) else None
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    return _maturity(str(row[0]))


def load_cr_binding(catalog_db: Path | str | None = None) -> dict[str, Any]:
    """Read CR-b428ac5cbc8986b5. Does not upsert, resolve, or harvest."""
    out: dict[str, Any] = {
        "cr_id": CR_ID,
        "cr_bound": True,
        "cr_present": False,
        "cr_state": None,
        "cr_blocker": None,
        "cr_capability": CAP_ID,
        "cr_title": None,
        "cr_next_action": None,
        "cr_resolved": False,
    }
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    if not path.is_file():
        return out
    _guard_path(path)
    uri = path.resolve().as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return out
    try:
        row = conn.execute(
            """
            SELECT state, blocker_class, capability, title, next_action
            FROM wolf_completion_items WHERE id=?
            """,
            (CR_ID,),
        ).fetchone()
    except sqlite3.Error:
        return out
    finally:
        conn.close()
    if row is None:
        return out
    out["cr_present"] = True
    out["cr_state"] = row[0]
    out["cr_blocker"] = row[1]
    out["cr_capability"] = row[2] or CAP_ID
    out["cr_title"] = row[3]
    out["cr_next_action"] = row[4]
    out["cr_resolved"] = row[0] == "RESOLVED"
    return out


def honesty_flags(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    state = ledger_cap_state(ledger_path)
    ceiling = state if state in HIGHER_THAN_BUILT else "BUILT"
    flags = dict(HONESTY)
    flags.update(load_cr_binding(catalog_db))
    flags["ledger_maturity"] = state
    flags["maturity"] = state
    flags["maturity_ceiling"] = ceiling
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["invented_proven"] = False
    flags["invented_ready"] = False
    flags["framework_skeleton"] = "BUILT"
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["on_disk"] = False
    flags["buyer_access"] = False
    flags["buyer_grant"] = False
    flags["live_share"] = False
    flags["buyer_export"] = False
    flags["controlled_export"] = False
    flags["crown_jewels_opened"] = False
    flags["cross_company_exposed"] = False
    flags["ask_answered"] = False
    return flags


def _filter_entity(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    token = str(value).strip().upper()
    if token not in evidence.ENTITIES:
        raise BuyerModeError(
            "Unknown entity. This framework does not invent a company.",
            code="invalid_entity",
        )
    return token


def _entities_present(rows: list[dict[str, Any]]) -> list[str]:
    found = {row["entity"] for row in rows if row.get("entity") in evidence.ENTITIES}
    return [name for name in ENTITY_ORDER if name in found]


def _item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "area": row.get("area"),
        "named": True,
        "data": None,
    }


def _export_slot(surface: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"EXP-{surface['id']}",
        "surface": surface["id"],
        "entity": surface["entity"],
        "kind": surface["kind"],
        "slot": "EMPTY",
        "filled": False,
        "bytes": None,
        "filename": None,
        "path": None,
        "written": False,
        "shared": False,
        "granted": False,
        "buyer_access": False,
        "why": "Export slot is empty. This framework does not write a controlled export.",
    }


def _diligence_surfaces(rows: list[dict[str, Any]], entities: list[str]) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = []
    for entity in entities:
        for spec in evidence.DOMAINS:
            items = [
                _item(row)
                for row in rows
                if row.get("entity") == entity and row.get("domain") == spec["id"]
            ]
            sid = f"SURF-{entity}-{spec['id']}"
            surfaces.append(
                {
                    "id": sid,
                    "kind": "diligence",
                    "entity": entity,
                    "domain": spec["id"],
                    "name": spec["name"],
                    "approved": True,
                    "company_specific": True,
                    "visibility": "NAMED",
                    "hidden": False,
                    "data": None,
                    "ask_context": None,
                    "answers": [],
                    "items": items,
                    "item_count": len(items),
                    "export_id": f"EXP-{sid}",
                    "export_slot": "EMPTY",
                    "shared": False,
                    "granted": False,
                    "buyer_access": False,
                    "why": "Approved company-specific diligence surface. Named only. No diligence data is copied.",
                }
            )
    return surfaces


def _ask_surfaces(entities: list[str]) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = []
    for entity in entities:
        sid = f"SURF-{entity}-ASK"
        surfaces.append(
            {
                "id": sid,
                "kind": "ask_context",
                "entity": entity,
                "domain": None,
                "name": "Ask context",
                "approved": True,
                "company_specific": True,
                "visibility": "NAMED",
                "hidden": False,
                "data": None,
                "ask_context": None,
                "answers": [],
                "items": [],
                "item_count": 0,
                "export_id": f"EXP-{sid}",
                "export_slot": "EMPTY",
                "shared": False,
                "granted": False,
                "buyer_access": False,
                "why": "Approved company-specific Ask context. Named only. No Ask answer is copied.",
            }
        )
    return surfaces


def _hides() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in HIDE_SPECS:
        rows.append(
            {
                "id": spec["id"],
                "kind": "hide",
                "class": spec["hide_class"],
                "name": spec["name"],
                "entity": None,
                "approved": False,
                "company_specific": False,
                "visibility": "HIDDEN",
                "default_hidden": True,
                "hidden": True,
                "opened": False,
                "payload": None,
                "data": None,
                "ask_context": None,
                "answers": [],
                "items": [],
                "export_id": None,
                "export_slot": None,
                "shared": False,
                "granted": False,
                "buyer_access": False,
                "why": spec["why"],
            }
        )
    return rows


def _name_bucket(rows: list[dict[str, Any]], *, why: str) -> dict[str, Any]:
    return {
        "approved": False,
        "required": False,
        "control_count": len(rows),
        "export_count": 0,
        "names": [_item(row) | {"entity": row.get("entity")} for row in rows],
        "why": why,
    }


def build_mode(
    csv_path: Path | str | None = None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    entity: str | None = None,
) -> dict[str, Any]:
    """Read-only mode map. A company filter narrows names. It does not reveal hides."""
    entity_token = _filter_entity(entity)
    flags = honesty_flags(ledger_path, catalog_db)
    rows = _load_names(csv_path)
    list_matches = len(rows) == CANON_CONTROLS
    scoped = rows
    if entity_token:
        scoped = [row for row in scoped if row.get("entity") == entity_token]
    entities = _entities_present(scoped)
    diligence = _diligence_surfaces(scoped, entities)
    asks = _ask_surfaces(entities)
    surfaces = diligence + asks
    hides = _hides()
    exports = [_export_slot(row) for row in surfaces]
    unmapped_rows = [row for row in scoped if row.get("domain") == "UNKNOWN" and not row.get("unexpected_entity")]
    refused_rows = [row for row in scoped if row.get("unexpected_entity")]
    empty_exports = sum(1 for row in exports if row["slot"] == "EMPTY" and row["filled"] is False)
    return {
        "ok": True,
        "cap": CAP_ID,
        "slice": "sale_buyer_mode",
        "framework_skeleton": "BUILT",
        "read_only": True,
        "on_disk": False,
        "buyer_access": False,
        "buyer_grant": False,
        "live_share": False,
        "buyer_export": False,
        "controlled_export": False,
        "export_written": False,
        "crown_jewels_opened": False,
        "cross_company_exposed": False,
        "blended": False,
        "ask_answered": False,
        "documents_invented": False,
        "ledger_write": False,
        "external_writes": False,
        "buyers": [],
        "buyer_count": 0,
        "share_url": None,
        "seeded_from": ["docs/canon/build-dashboard/Sale_Readiness.csv"],
        "controls_expected": CANON_CONTROLS,
        "controls_read": len(rows),
        "control_list_matches_canon": list_matches,
        "entities": entities,
        "diligence_surface_count": len(diligence),
        "ask_surface_count": len(asks),
        "approved_count": len(surfaces),
        "item_count": sum(row["item_count"] for row in diligence),
        "hide_count": len(hides),
        "hides_default_hidden": all(row["default_hidden"] and row["hidden"] and row["payload"] is None for row in hides),
        "export_count": len(exports),
        "empty_exports": empty_exports,
        "filled_exports": 0,
        "filters": {"entity": entity_token},
        "surfaces": surfaces,
        "diligence_surfaces": diligence,
        "ask_surfaces": asks,
        "hides": hides,
        "exports": exports,
        "unmapped": _name_bucket(
            unmapped_rows,
            why=(
                "These rows are not approved diligence surfaces. "
                "They are not forced into a surface and they are not exported."
            ),
        ),
        "not_approved": _name_bucket(
            refused_rows,
            why="An unexpected company is not approved. This framework does not invent approval.",
        ),
        "gaps": list(GAPS),
        "honesty": flags,
    }


def _refuse_reserved(token: str) -> None:
    kind = _RESERVED.get(token)
    if kind == "export":
        refuse_export()
    elif kind == "grant":
        refuse_grant()
    elif kind == "share":
        refuse_share()
    elif kind == "reveal":
        refuse_reveal()
    elif kind == "fill":
        refuse_fill()
    elif kind == "production":
        refuse_production()
    elif kind == "cross":
        refuse_cross()
    elif kind == "not_found":
        raise BuyerModeError("That path is not a surface.", code="not_found")


def read_surface(
    surface_id: str,
    csv_path: Path | str | None = None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """One named surface, hide, or empty export slot. A missing id is not invented."""
    token = (surface_id or "").strip().upper()
    if not token:
        raise BuyerModeError("That path is not a surface.", code="not_found")
    _refuse_reserved(token)
    mode = build_mode(csv_path=csv_path, ledger_path=ledger_path, catalog_db=catalog_db)
    candidates = [token]
    if not token.startswith(("SURF-", "HIDE-", "EXP-")):
        candidates.append(f"SURF-{token}")
    base = {
        "ok": True,
        "cap": CAP_ID,
        "buyer_grant": False,
        "buyer_access": False,
        "live_share": False,
        "buyer_export": False,
        "controlled_export": False,
        "crown_jewels_opened": False,
        "cross_company_exposed": False,
        "ledger_write": False,
        "on_disk": False,
        "honesty": mode["honesty"],
    }
    for row in mode["surfaces"]:
        if row["id"] in candidates:
            slot = next((item for item in mode["exports"] if item["surface"] == row["id"]), None)
            return {**base, "surface": row, "export_slot": slot, "payload": None}
    for row in mode["hides"]:
        if row["id"] in candidates:
            return {**base, "hide": row, "opened": False, "payload": None}
    for row in mode["exports"]:
        if row["id"] in candidates:
            return {**base, "export_slot": row, "payload": None}
    raise BuyerModeError("Surface was not in the map. It was not invented.", code="not_found")
