#!/usr/bin/env python3
"""CAP-SALE-04 buyer attack and transition readiness framework (Beta, read-only).

Decision served: 2026-09-20 PICK, buyer attack and transition readiness
framework on Beta only
(docs/deliveries/GROK-PLAN-SALE-ATTACK-AUDIT-FRAMEWORK-2026-09-19.md).

Names the attack-audit sections and the empty transition-pack slots. The Wolf
licence post-sale boundary stays preserved. This module does not run an
attack, fill a pack, grant a buyer, or invent PROVEN or READY.

Honesty is bound to CR-c6e1a48e4a3e8a91 when that row is present. Ledger
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

CR_ID = "CR-c6e1a48e4a3e8a91"
CAP_ID = "CAP-SALE-04"
CANON_CONTROLS = evidence.CANON_CONTROLS
ENTITY_ORDER = ("GGV", "AMG", "BZG")

MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})

# Catalog row map: these Sale_Readiness areas are controls under CAP-SALE-04.
# Named only. Findings are not written. An attack is not run.
AUDIT_AREAS: tuple[dict[str, str], ...] = (
    {
        "id": "CUSTOMER-CONCENTRATION",
        "area": "Customer concentration",
        "name": "Customer concentration",
        "why": "Named attack-audit section. No finding is written and no attack is run.",
    },
    {
        "id": "SUPPLIER-CONCENTRATION",
        "area": "Supplier concentration",
        "name": "Supplier concentration",
        "why": "Named attack-audit section. No finding is written and no attack is run.",
    },
    {
        "id": "COMPLIANCE",
        "area": "Compliance",
        "name": "Compliance",
        "why": "Named attack-audit section. No finding is written and no attack is run.",
    },
    {
        "id": "CONTRACT-QUALITY",
        "area": "Contract quality",
        "name": "Contract quality",
        "why": "Named attack-audit section. No finding is written and no attack is run.",
    },
    {
        "id": "DATA-QUALITY",
        "area": "Data quality",
        "name": "Data quality",
        "why": "Named attack-audit section. No finding is written and no attack is run.",
    },
    {
        "id": "TECHNOLOGY-PORTABILITY",
        "area": "Technology portability",
        "name": "Technology portability",
        "why": "Named attack-audit section. No finding is written and no attack is run.",
    },
    {
        "id": "CYBERSECURITY",
        "area": "Cybersecurity",
        "name": "Cybersecurity",
        "why": "Named attack-audit section. No finding is written and no attack is run.",
    },
    {
        "id": "ASSET-CONDITION",
        "area": "Asset condition",
        "name": "Asset condition",
        "why": "Named attack-audit section. No finding is written and no attack is run.",
    },
    {
        "id": "BRAND-IP",
        "area": "Brand/IP ownership",
        "name": "Brand/IP ownership",
        "why": "Named attack-audit section. No finding is written and no attack is run.",
    },
    {
        "id": "GROWTH",
        "area": "Growth opportunities",
        "name": "Growth opportunities",
        "why": "Named attack-audit section. No finding is written and no attack is run.",
    },
)

# Round 13 transition topics. Slots stay empty. Nothing is written.
PACK_KINDS: tuple[dict[str, str], ...] = (
    {
        "id": "SHARED-SERVICES",
        "name": "Shared-service continuity and exit",
        "why": "Transition-pack slot is empty. Continuity and exit are named and not written.",
    },
    {
        "id": "TRANSITION-SERVICES",
        "name": "Transition services",
        "why": "Transition-pack slot is empty. Transition services are named and not written.",
    },
    {
        "id": "POST-SALE",
        "name": "Post-sale obligations",
        "why": "Transition-pack slot is empty. Post-sale obligations are named and not written.",
    },
    {
        "id": "TRANSACTION-PERMISSIONS",
        "name": "Transaction permissions",
        "why": "Transition-pack slot is empty. Transaction permissions are named and not written.",
    },
)

# Spec section 24. The licence can continue after sale. This framework does not grant it.
LICENCE_ID = "BOUND-WOLF-LICENCE"

GAPS: tuple[str, ...] = (
    "No attack was run.",
    "No weakness was invented.",
    "No fix was written.",
    "Every transition-pack slot stays empty.",
    "The Wolf licence post-sale boundary stays preserved.",
    "No licence is granted.",
    "Generic Wolf IP and architecture are not copied.",
    "No buyer is granted.",
    "No share link is issued.",
    "No export file is written.",
    "Source diligence text is not copied onto a section.",
    "This read does not change the ledger and does not close the completion row.",
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "sale_attack_audit",
    "read_only": True,
    "framework_skeleton": "BUILT",
    "on_disk": False,
    "attack_run": False,
    "live_attack": False,
    "findings_written": False,
    "weakness_invented": False,
    "fix_written": False,
    "transition_pack_written": False,
    "filled_packs_invented": False,
    "licence_granted": False,
    "wolf_ip_transferred": False,
    "architecture_copied": False,
    "buyer_access": False,
    "buyer_grant": False,
    "live_share": False,
    "buyer_export": False,
    "documents_invented": False,
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
    "SECTIONS": "not_found",
    "PACKS": "not_found",
    "LICENCE": "not_found",
    "EXPORT": "export",
    "DOWNLOAD": "export",
    "GRANT": "grant",
    "BUYER": "grant",
    "ACCESS": "grant",
    "SHARE": "share",
    "FILL": "fill",
    "UPLOAD": "fill",
    "PACK": "fill",
    "ATTACK": "attack",
    "RUN": "attack",
    "REDTEAM": "attack",
    "TRANSFER": "licence",
    "PRODUCTION": "production",
}

_AREA_BY_NAME = {spec["area"]: spec for spec in AUDIT_AREAS}


class AttackAuditError(ValueError):
    """Fail closed. Does not run an attack, fill a pack, or grant a licence."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_attack(_body: dict | None = None) -> None:
    """A live attack would red-team a company. This slice does not."""
    raise AttackAuditError(
        "Live attack is refused. Audit sections stay named. This framework does not run an attack.",
        code="attack_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    """Transition-pack slots are not filled by this framework."""
    raise AttackAuditError(
        "Attack audit does not fill a transition pack.",
        code="fill_refused",
    )


def refuse_grant(_body: dict | None = None) -> None:
    """No buyer is granted. Owner read is not a buyer grant."""
    raise AttackAuditError(
        "Buyer grant is refused. This framework does not grant a buyer.",
        code="buyer_grant_refused",
    )


def refuse_share(_body: dict | None = None) -> None:
    """A live share link is not this skeleton."""
    raise AttackAuditError(
        "Live share is refused. This framework does not issue a share link.",
        code="buyer_share_refused",
    )


def refuse_export(_body: dict | None = None) -> None:
    """An export would write a pack. This slice does not."""
    raise AttackAuditError(
        "Export is refused. Transition-pack slots stay empty. This framework does not write a pack.",
        code="buyer_export_refused",
    )


def refuse_licence(_body: dict | None = None) -> None:
    """The Wolf licence boundary stays preserved. It is not granted."""
    raise AttackAuditError(
        "Wolf licence stays preserved. This framework does not grant a licence or copy Wolf IP.",
        code="licence_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    """Production is not this tree."""
    raise AttackAuditError(
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
        raise AttackAuditError("attack audit refuses an Alchemist write", code="alchemist_refused")
    if (
        payload.get("attack")
        or payload.get("run")
        or payload.get("live_attack")
        or payload.get("redteam")
        or action in {"attack", "run", "redteam"}
    ):
        refuse_attack(payload)
    if (
        payload.get("licence")
        or payload.get("transfer")
        or payload.get("wolf_ip")
        or payload.get("grant_licence")
        or action in {"licence", "transfer"}
    ):
        refuse_licence(payload)
    if payload.get("share") or payload.get("live_share") or export == "share" or action == "share":
        refuse_share(payload)
    if (
        payload.get("buyer_export")
        or payload.get("download")
        or export in {"export", "pack", "attack", "1", "true"}
        or action in {"export", "download"}
    ):
        refuse_export(payload)
    if (
        payload.get("buyer")
        or payload.get("buyer_access")
        or payload.get("grant")
        or payload.get("buyer_grant")
        or action == "grant"
    ):
        refuse_grant(payload)
    if any(payload.get(key) not in (None, "", False) for key in ("document", "filename", "fill", "upload", "file", "pack")):
        refuse_fill(payload)
    raise AttackAuditError(
        "Attack audit is read-only. No attack, no filled pack, and no buyer grant.",
        code="writes_refused",
    )


def _truthy(value: str | None) -> bool:
    return bool((value or "").strip())


def guard_query(
    *,
    attack: str | None = None,
    run: str | None = None,
    fill: str | None = None,
    share: str | None = None,
    grant: str | None = None,
    buyer: str | None = None,
    export: str | None = None,
    licence: str | None = None,
    transfer: str | None = None,
    production: str | None = None,
) -> None:
    """A read that asks to attack, fill, grant, or transfer is still a write."""
    if _truthy(production):
        refuse_production()
    if _truthy(attack) or _truthy(run):
        refuse_attack()
    if _truthy(licence) or _truthy(transfer):
        refuse_licence()
    if _truthy(share):
        refuse_share()
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
        raise AttackAuditError("attack audit refuses an Alchemist path", code="alchemist_refused")
    if low.endswith("money.sqlite") or "/production" in low:
        raise AttackAuditError("attack audit refuses a production path", code="not_beta")
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
        raise AttackAuditError(
            "attack audit refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc
    if "wolf-system" in low:
        raise AttackAuditError("attack audit refuses a wolf-system fixture path", code="not_beta")


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
        code = "duplicate_section" if exc.code == "duplicate_control" else exc.code
        raise AttackAuditError(str(exc), code=code) from exc
    named: list[dict[str, Any]] = []
    for row in rows:
        named.append(
            {
                "id": str(row.get("id") or ""),
                "entity": row.get("entity"),
                "area": row.get("area"),
                "unexpected_entity": bool(row.get("unexpected_entity")),
            }
        )
    return named


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-SALE-04 from the ledger. Does not write it."""
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
    """Read CR-c6e1a48e4a3e8a91. Does not upsert, resolve, or harvest."""
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
    flags["attack_run"] = False
    flags["live_attack"] = False
    flags["licence_granted"] = False
    flags["wolf_ip_transferred"] = False
    flags["buyer_grant"] = False
    flags["buyer_export"] = False
    return flags


def _filter_entity(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    token = str(value).strip().upper()
    if token not in evidence.ENTITIES:
        raise AttackAuditError(
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
        "entity": row.get("entity"),
        "named": True,
        "data": None,
    }


def _sections(rows: list[dict[str, Any]], entities: list[str]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for entity in entities:
        for spec in AUDIT_AREAS:
            items = [
                _item(row)
                for row in rows
                if row.get("entity") == entity
                and row.get("area") == spec["area"]
                and not row.get("unexpected_entity")
            ]
            sid = f"AUD-{entity}-{spec['id']}"
            sections.append(
                {
                    "id": sid,
                    "kind": "audit_section",
                    "entity": entity,
                    "area": spec["area"],
                    "name": spec["name"],
                    "company_specific": True,
                    "named": True,
                    "attack_run": False,
                    "findings": None,
                    "weakness": None,
                    "fix": None,
                    "data": None,
                    "items": items,
                    "item_count": len(items),
                    "why": spec["why"],
                }
            )
    return sections


def _packs(entities: list[str]) -> list[dict[str, Any]]:
    packs: list[dict[str, Any]] = []
    for entity in entities:
        for spec in PACK_KINDS:
            pid = f"PACK-{entity}-{spec['id']}"
            packs.append(
                {
                    "id": pid,
                    "kind": "transition_pack",
                    "entity": entity,
                    "name": spec["name"],
                    "company_specific": True,
                    "slot": "EMPTY",
                    "filled": False,
                    "bytes": None,
                    "filename": None,
                    "path": None,
                    "written": False,
                    "shared": False,
                    "granted": False,
                    "buyer_access": False,
                    "attack_run": False,
                    "data": None,
                    "why": spec["why"],
                }
            )
    return packs


def _licence() -> dict[str, Any]:
    return {
        "id": LICENCE_ID,
        "kind": "licence_boundary",
        "preserved": True,
        "optional_after_sale": True,
        "licence_granted": False,
        "wolf_ip_transferred": False,
        "architecture_copied": False,
        "business_data_copied": False,
        "approved_knowledge_copied": False,
        "payload": None,
        "data": None,
        "matt_retains": "Generic Wolf IP and architecture",
        "buyer_receipt": None,
        "why": (
            "Spec section 24. The Wolf licence can continue after sale. "
            "This framework does not grant it and does not copy Wolf IP or architecture."
        ),
    }


def _name_bucket(rows: list[dict[str, Any]], *, why: str) -> dict[str, Any]:
    return {
        "in_audit": False,
        "control_count": len(rows),
        "pack_count": 0,
        "names": [_item(row) for row in rows],
        "why": why,
    }


def build_audit(
    csv_path: Path | str | None = None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    entity: str | None = None,
) -> dict[str, Any]:
    """Read-only checklist. A company filter narrows names. It does not run an attack."""
    entity_token = _filter_entity(entity)
    flags = honesty_flags(ledger_path, catalog_db)
    rows = _load_names(csv_path)
    list_matches = len(rows) == CANON_CONTROLS
    scoped = rows
    if entity_token:
        scoped = [row for row in scoped if row.get("entity") == entity_token]
    entities = _entities_present(scoped)
    sections = _sections(scoped, entities)
    packs = _packs(entities)
    licence = _licence()
    in_areas = {spec["area"] for spec in AUDIT_AREAS}
    outside = [
        row
        for row in scoped
        if not row.get("unexpected_entity") and row.get("area") not in in_areas
    ]
    refused_rows = [row for row in scoped if row.get("unexpected_entity")]
    empty_packs = sum(1 for row in packs if row["slot"] == "EMPTY" and row["filled"] is False)
    return {
        "ok": True,
        "cap": CAP_ID,
        "slice": "sale_attack_audit",
        "framework_skeleton": "BUILT",
        "read_only": True,
        "on_disk": False,
        "attack_run": False,
        "live_attack": False,
        "findings_written": False,
        "licence_granted": False,
        "wolf_ip_transferred": False,
        "architecture_copied": False,
        "licence_preserved": licence["preserved"] is True and licence["payload"] is None,
        "buyer_access": False,
        "buyer_grant": False,
        "live_share": False,
        "buyer_export": False,
        "transition_pack_written": False,
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
        "section_count": len(sections),
        "item_count": sum(row["item_count"] for row in sections),
        "pack_count": len(packs),
        "empty_packs": empty_packs,
        "filled_packs": 0,
        "filters": {"entity": entity_token},
        "sections": sections,
        "packs": packs,
        "licence": licence,
        "not_in_audit": _name_bucket(
            outside,
            why=(
                "These controls are not CAP-SALE-04 attack sections. "
                "They are not forced into a section and they are not packed."
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
    elif kind == "fill":
        refuse_fill()
    elif kind == "attack":
        refuse_attack()
    elif kind == "licence":
        refuse_licence()
    elif kind == "production":
        refuse_production()
    elif kind == "not_found":
        raise AttackAuditError("That path is not a section.", code="not_found")


def read_section(
    section_id: str,
    csv_path: Path | str | None = None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """One named section, empty pack, or the licence boundary. A missing id is not invented."""
    token = (section_id or "").strip().upper()
    if not token:
        raise AttackAuditError("That path is not a section.", code="not_found")
    _refuse_reserved(token)
    audit = build_audit(csv_path=csv_path, ledger_path=ledger_path, catalog_db=catalog_db)
    candidates = [token]
    if not token.startswith(("AUD-", "PACK-", "BOUND-")):
        candidates.append(f"AUD-{token}")
    base = {
        "ok": True,
        "cap": CAP_ID,
        "attack_run": False,
        "live_attack": False,
        "buyer_grant": False,
        "buyer_access": False,
        "live_share": False,
        "buyer_export": False,
        "licence_granted": False,
        "wolf_ip_transferred": False,
        "ledger_write": False,
        "on_disk": False,
        "honesty": audit["honesty"],
    }
    for row in audit["sections"]:
        if row["id"] in candidates:
            return {**base, "section": row, "payload": None, "findings": None}
    for row in audit["packs"]:
        if row["id"] in candidates:
            return {**base, "pack": row, "payload": None}
    if audit["licence"]["id"] in candidates:
        return {**base, "licence": audit["licence"], "preserved": True, "payload": None}
    raise AttackAuditError("Section was not in the checklist. It was not invented.", code="not_found")
