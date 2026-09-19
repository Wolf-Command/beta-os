#!/usr/bin/env python3
"""CAP-SALE-01 sale evidence pack framework (Beta, read-only).

Decision served: 2026-09-19 PICK, sale evidence pack framework on Beta only
(docs/deliveries/GROK-PLAN-SALE-EVIDENCE-PACK-FRAMEWORK-2026-09-19.md).

Lists the six required source domains and the diligence controls under them.
An empty source cell stays empty. This module does not fill evidence, export
a buyer data room, or invent PROVEN.

Honesty is bound to CR-b7ce6d6668848b6e when that row is present. Ledger
maturity is read, not written. The skeleton ceiling is BUILT unless the
ledger is already PROVEN or READY.
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
SALE_CSV = BETA_ROOT / "docs" / "canon" / "build-dashboard" / "Sale_Readiness.csv"

CR_ID = "CR-b7ce6d6668848b6e"
CAP_ID = "CAP-SALE-01"
CANON_CONTROLS = 60

ENTITIES = frozenset({"GGV", "AMG", "BZG"})
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})

# Classification of control names. Not evidence. Growth opportunities is
# left UNKNOWN so it is not forced into a domain this catalog did not name.
AREA_DOMAIN = {
    "Finance quality": "FINANCE",
    "Profitability / EBITDA": "FINANCE",
    "Quality of earnings": "FINANCE",
    "Customer concentration": "FINANCE",
    "Supplier concentration": "OPS",
    "Management depth": "HR",
    "Founder dependency": "HR",
    "SOP coverage": "OPS",
    "Training coverage": "HR",
    "Compliance": "COMPLIANCE",
    "Contract quality": "LEGAL",
    "Data quality": "TECH",
    "Technology portability": "TECH",
    "Cybersecurity": "TECH",
    "Asset condition": "OPS",
    "Brand/IP ownership": "LEGAL",
    "Employee retention": "HR",
    "Succession": "HR",
    "Operational consistency": "OPS",
    "Growth opportunities": "UNKNOWN",
}

DOMAINS: tuple[dict[str, str], ...] = (
    {
        "id": "FINANCE",
        "name": "Finance",
        "why": "Required source domain. This pack does not clone the Finance capability and does not fill evidence.",
    },
    {
        "id": "HR",
        "name": "HR",
        "why": "Required source domain. This pack does not clone the HR capability and does not fill evidence.",
    },
    {
        "id": "LEGAL",
        "name": "Legal",
        "why": "Required source domain. This pack does not clone a Legal capability and does not fill evidence.",
    },
    {
        "id": "OPS",
        "name": "Ops",
        "why": "Required source domain. This pack does not clone an Ops capability and does not fill evidence.",
    },
    {
        "id": "COMPLIANCE",
        "name": "Compliance",
        "why": "Required source domain. This pack does not clone a Compliance capability and does not fill evidence.",
    },
    {
        "id": "TECH",
        "name": "Tech",
        "why": "Required source domain. This pack does not clone a Tech capability and does not fill evidence.",
    },
)
DOMAIN_IDS = frozenset(row["id"] for row in DOMAINS)

REQUIRED_COLUMNS = (
    "Entity",
    "Area",
    "Evidence / Metric",
    "Current State",
    "Target State",
    "Gap",
    "Owner",
    "Next action",
    "Status",
)

_SLUG_RE = re.compile(r"[^A-Z0-9]+")

HONESTY = {
    "cap": CAP_ID,
    "slice": "sale_evidence_pack",
    "read_only": True,
    "framework_skeleton": "BUILT",
    "vdr_export": False,
    "buyer_export": False,
    "evidence_invented": False,
    "filled_slots_invented": False,
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


class SalePackError(ValueError):
    """Fail closed. Does not fill a slot, export a VDR, or invent maturity."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_vdr_export(_body: dict | None = None) -> None:
    """Buyer data room export is CAP-SALE-02. This slice does not do it."""
    raise SalePackError(
        "Buyer VDR export is refused. This framework does not write a data room.",
        code="vdr_export_refused",
    )


def refuse_buyer_export(_body: dict | None = None) -> None:
    """Buyer mode export is CAP-SALE-03. This slice does not do it."""
    raise SalePackError(
        "Buyer mode export is refused. This framework does not export diligence.",
        code="buyer_export_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    """Evidence cells are not filled by this framework."""
    raise SalePackError(
        "Sale evidence pack does not fill evidence slots.",
        code="fill_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    """Every mutation path ends here. Nothing is written."""
    payload = body or {}
    export = str(payload.get("export") or "").strip().lower()
    if payload.get("vdr") or payload.get("vdr_export") or export == "vdr":
        refuse_vdr_export(payload)
    if payload.get("buyer") or payload.get("buyer_export") or payload.get("buyer_mode") or export in {
        "buyer",
        "buyer-mode",
        "buyer_mode",
    }:
        refuse_buyer_export(payload)
    if any(payload.get(key) not in (None, "", False) for key in ("evidence", "fill", "current_state", "slot")):
        refuse_fill(payload)
    raise SalePackError(
        "Sale evidence pack is read-only. No buyer export and no filled evidence.",
        code="writes_refused",
    )


def guard_query(*, export: str | None = None, fill: str | None = None, vdr: str | None = None) -> None:
    """A read that asks to export or fill is still a write. Refuse it."""
    export_token = (export or "").strip().lower()
    if (vdr or "").strip() or export_token == "vdr":
        refuse_vdr_export()
    if export_token in {"buyer", "buyer-mode", "buyer_mode", "1", "true"}:
        refuse_buyer_export()
    if (fill or "").strip():
        refuse_fill()


def _guard_path(path: Path) -> None:
    text = str(path)
    low = text.lower()
    if "alchemist" in low:
        raise SalePackError("sale pack refuses an Alchemist path", code="alchemist_refused")
    if low.endswith("money.sqlite") or "/production" in low:
        raise SalePackError("sale pack refuses a production path", code="not_beta")
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
        raise SalePackError(
            "sale pack refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc
    if "wolf-system" in low:
        raise SalePackError("sale pack refuses a wolf-system fixture path", code="not_beta")


def _maturity(value: str) -> str:
    token = (value or "").strip().upper()
    if token in MATURITY:
        return token
    return "UNKNOWN"


def _cell(row: dict[str, Any], key: str) -> str | None:
    raw = row.get(key)
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _slug(area: str) -> str:
    return _SLUG_RE.sub("-", (area or "").upper()).strip("-") or "UNNAMED"


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-SALE-01 from the ledger. Does not write it."""
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
    """Read CR-b7ce6d6668848b6e. Does not upsert, resolve, or harvest."""
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
    flags["framework_skeleton"] = "BUILT"
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["vdr_export"] = False
    flags["buyer_export"] = False
    flags["evidence_invented"] = False
    return flags


def _filter_entity(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    token = str(value).strip().upper()
    if token not in ENTITIES:
        raise SalePackError(
            "Unknown entity. This framework does not invent a company.",
            code="invalid_entity",
        )
    return token


def _filter_domain(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    token = str(value).strip().upper()
    if token == "UNKNOWN" or token in DOMAIN_IDS:
        return token
    raise SalePackError(
        "Unknown domain. This framework does not invent a source domain.",
        code="invalid_domain",
    )


def load_controls(csv_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Read diligence controls. Missing file is not an empty pack."""
    path = Path(csv_path) if csv_path else SALE_CSV
    _guard_path(path)
    if not path.is_file():
        raise SalePackError(
            "Sale readiness source was not read. Empty is not a completed pack.",
            code="not_read",
        )
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SalePackError("Sale readiness source was not read.", code="not_read") from exc
    reader = csv.DictReader(text.splitlines())
    fields = reader.fieldnames or []
    missing = [name for name in REQUIRED_COLUMNS if name not in fields]
    if missing:
        raise SalePackError(
            "Sale readiness source is missing required columns.",
            code="bad_source",
        )
    controls: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in reader:
        if raw is None:
            continue
        if not any((raw.get(name) or "").strip() for name in REQUIRED_COLUMNS):
            continue
        area = _cell(raw, "Area") or ""
        entity = _cell(raw, "Entity")
        evidence = _cell(raw, "Evidence / Metric")
        domain = AREA_DOMAIN.get(area, "UNKNOWN") if area else "UNKNOWN"
        entity_token = entity or "UNSTATED"
        control_id = f"CTRL-{entity_token}-{_slug(area)}"
        if control_id in seen:
            raise SalePackError(
                "Duplicate control id. This framework does not merge slots.",
                code="duplicate_control",
            )
        seen.add(control_id)
        controls.append(
            {
                "id": control_id,
                "cap": CAP_ID,
                "is_control": True,
                "is_capability": False,
                "entity": entity,
                "area": area or None,
                "domain": domain,
                "unexpected_entity": entity not in ENTITIES,
                "evidence": evidence,
                "current_state": _cell(raw, "Current State"),
                "target_state": _cell(raw, "Target State"),
                "gap": _cell(raw, "Gap"),
                "owner": _cell(raw, "Owner"),
                "next_action": _cell(raw, "Next action"),
                "source_status": _cell(raw, "Status"),
                "slot": "EMPTY" if evidence is None else "SOURCE_TEXT",
                "filled": evidence is not None,
                "proven": False,
                "why": (
                    "Source evidence cell is empty. This framework does not fill it."
                    if evidence is None
                    else "Source evidence cell has text. This framework did not add it and does not treat it as proved."
                ),
            }
        )
    return controls


def _domain_rows(controls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in DOMAINS:
        matched = [row for row in controls if row["domain"] == spec["id"]]
        empty = sum(1 for row in matched if row["slot"] == "EMPTY")
        filled = sum(1 for row in matched if row["filled"])
        rows.append(
            {
                "id": spec["id"],
                "name": spec["name"],
                "required": True,
                "evidence": None,
                "slot": "EMPTY" if filled == 0 else "SOURCE_TEXT",
                "filled": filled > 0,
                "filled_controls": filled,
                "empty_controls": empty,
                "control_count": len(matched),
                "proven": False,
                "why": spec["why"],
            }
        )
    return rows


def _unmapped(controls: list[dict[str, Any]]) -> dict[str, Any]:
    matched = [row for row in controls if row["domain"] == "UNKNOWN"]
    filled = sum(1 for row in matched if row["filled"])
    return {
        "domain": "UNKNOWN",
        "required": False,
        "evidence": None,
        "slot": "EMPTY" if filled == 0 else "SOURCE_TEXT",
        "filled": filled > 0,
        "filled_controls": filled,
        "empty_controls": sum(1 for row in matched if row["slot"] == "EMPTY"),
        "control_count": len(matched),
        "proven": False,
        "why": (
            "These controls are not classified into Finance, HR, Legal, Ops, "
            "Compliance, or Tech. They are not forced into a domain."
        ),
    }


def build_pack(
    csv_path: Path | str | None = None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    entity: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    """Read-only pack. Filters narrow controls. They do not invent rows."""
    entity_token = _filter_entity(entity)
    domain_token = _filter_domain(domain)
    flags = honesty_flags(ledger_path, catalog_db)
    controls = load_controls(csv_path)
    list_matches = len(controls) == CANON_CONTROLS
    scoped = controls
    if entity_token:
        scoped = [row for row in scoped if row["entity"] == entity_token]
    shown = scoped
    if domain_token:
        shown = [row for row in scoped if row["domain"] == domain_token]
    empty_slots = sum(1 for row in shown if row["slot"] == "EMPTY")
    filled_slots = sum(1 for row in shown if row["filled"])
    return {
        "ok": True,
        "cap": CAP_ID,
        "slice": "sale_evidence_pack",
        "framework_skeleton": "BUILT",
        "read_only": True,
        "vdr_export": False,
        "buyer_export": False,
        "evidence_invented": False,
        "ledger_write": False,
        "external_writes": False,
        "seeded_from": ["docs/canon/build-dashboard/Sale_Readiness.csv"],
        "controls_expected": CANON_CONTROLS,
        "controls_read": len(controls),
        "control_list_matches_canon": list_matches,
        "control_count": len(shown),
        "empty_slots": empty_slots,
        "filled_slots": filled_slots,
        "filters": {"entity": entity_token, "domain": domain_token},
        "domains": _domain_rows(scoped),
        "unmapped": _unmapped(scoped),
        "controls": shown,
        "honesty": flags,
    }


def read_control(
    control_id: str,
    csv_path: Path | str | None = None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """One control. Missing id is not an empty invented slot."""
    token = (control_id or "").strip()
    if not token or token.upper() in {"EXPORT", "VDR", "BUYER-EXPORT", "DOMAINS"}:
        raise SalePackError("That path is not a control.", code="not_found")
    pack = build_pack(csv_path=csv_path, ledger_path=ledger_path, catalog_db=catalog_db)
    for row in pack["controls"]:
        if row["id"] == token:
            return {
                "ok": True,
                "cap": CAP_ID,
                "control": row,
                "vdr_export": False,
                "buyer_export": False,
                "ledger_write": False,
                "honesty": pack["honesty"],
            }
    raise SalePackError("Control was not in the source. It was not invented.", code="not_found")
