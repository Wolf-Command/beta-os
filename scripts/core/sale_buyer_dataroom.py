#!/usr/bin/env python3
"""CAP-SALE-02 buyer data room framework (Beta, read-only).

Decision served: 2026-09-20 PICK, buyer data room framework on Beta only
(docs/deliveries/GROK-PLAN-SALE-BUYER-DATAROOM-FRAMEWORK-2026-09-19.md).

Names an empty virtual folder tree and a checklist of document slots. A slot
stays empty. Source text is not copied in. This module does not grant a
buyer, issue a share link, export a room, or invent PROVEN or READY.

Honesty is bound to CR-766f242208e401ad when that row is present. Ledger
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

CR_ID = "CR-766f242208e401ad"
CAP_ID = "CAP-SALE-02"
CANON_SLOTS = evidence.CANON_CONTROLS
FOLDER_COUNT = len(evidence.DOMAINS)

MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})

HONESTY = {
    "cap": CAP_ID,
    "slice": "sale_buyer_dataroom",
    "read_only": True,
    "framework_skeleton": "BUILT",
    "on_disk": False,
    "buyer_access": False,
    "live_share": False,
    "vdr_share": False,
    "vdr_export": False,
    "buyer_export": False,
    "documents_invented": False,
    "filled_docs_invented": False,
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


class BuyerDataroomError(ValueError):
    """Fail closed. Does not fill a slot, share a room, or invent maturity."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_share(_body: dict | None = None) -> None:
    """A live share link is not this skeleton."""
    raise BuyerDataroomError(
        "Live VDR share is refused. This framework does not issue a share link.",
        code="vdr_share_refused",
    )


def refuse_export(_body: dict | None = None) -> None:
    """Export would write a buyer package. This slice does not."""
    raise BuyerDataroomError(
        "Buyer data room export is refused. This framework does not write an export.",
        code="vdr_export_refused",
    )


def refuse_buyer_access(_body: dict | None = None) -> None:
    """No buyer is granted. Owner read is not buyer access."""
    raise BuyerDataroomError(
        "Buyer access is refused. This framework does not grant a buyer.",
        code="buyer_access_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    """Document slots are not filled by this framework."""
    raise BuyerDataroomError(
        "Buyer data room does not place documents in slots.",
        code="fill_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    """Every mutation path ends here. Nothing is written."""
    payload = body or {}
    export = str(payload.get("export") or "").strip().lower()
    if payload.get("share") or payload.get("vdr_share") or payload.get("live_share") or export == "share":
        refuse_share(payload)
    if (
        payload.get("vdr_export")
        or payload.get("download")
        or export in {"vdr", "buyer", "export", "1", "true"}
    ):
        refuse_export(payload)
    if payload.get("buyer") or payload.get("buyer_access") or payload.get("grant") or payload.get("buyer_mode"):
        refuse_buyer_access(payload)
    if any(payload.get(key) not in (None, "", False) for key in ("document", "filename", "fill", "upload", "file")):
        refuse_fill(payload)
    raise BuyerDataroomError(
        "Buyer data room is read-only. No share, no export, and no filled document.",
        code="writes_refused",
    )


def guard_query(
    *,
    export: str | None = None,
    fill: str | None = None,
    share: str | None = None,
    buyer: str | None = None,
) -> None:
    """A read that asks to share, export, or fill is still a write. Refuse it."""
    export_token = (export or "").strip().lower()
    if (share or "").strip() or export_token == "share":
        refuse_share()
    if export_token in {"vdr", "buyer", "export", "1", "true"}:
        refuse_export()
    if (buyer or "").strip():
        refuse_buyer_access()
    if (fill or "").strip():
        refuse_fill()


def _guard_path(path: Path) -> None:
    text = str(path)
    low = text.lower()
    if "alchemist" in low:
        raise BuyerDataroomError("buyer data room refuses an Alchemist path", code="alchemist_refused")
    if low.endswith("money.sqlite") or "/production" in low:
        raise BuyerDataroomError("buyer data room refuses a production path", code="not_beta")
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
        raise BuyerDataroomError(
            "buyer data room refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc
    if "wolf-system" in low:
        raise BuyerDataroomError("buyer data room refuses a wolf-system fixture path", code="not_beta")


def _maturity(value: str) -> str:
    token = (value or "").strip().upper()
    if token in MATURITY:
        return token
    return "UNKNOWN"


def _load_controls(csv_path: Path | str | None) -> list[dict[str, Any]]:
    try:
        return evidence.load_controls(csv_path)
    except evidence.SalePackError as exc:
        code = "duplicate_slot" if exc.code == "duplicate_control" else exc.code
        raise BuyerDataroomError(str(exc), code=code) from exc


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-SALE-02 from the ledger. Does not write it."""
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
    """Read CR-766f242208e401ad. Does not upsert, resolve, or harvest."""
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
    flags["live_share"] = False
    flags["vdr_share"] = False
    flags["vdr_export"] = False
    flags["documents_invented"] = False
    return flags


def _filter_entity(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    token = str(value).strip().upper()
    if token not in evidence.ENTITIES:
        raise BuyerDataroomError(
            "Unknown entity. This framework does not invent a company.",
            code="invalid_entity",
        )
    return token


def _filter_folder(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    token = str(value).strip().upper()
    if token.startswith("FOLDER-"):
        token = token[len("FOLDER-") :]
    if token == "UNKNOWN" or token in evidence.DOMAIN_IDS:
        return token
    raise BuyerDataroomError(
        "Unknown folder. This framework does not invent a data-room folder.",
        code="invalid_folder",
    )


def _slot(control: dict[str, Any]) -> dict[str, Any]:
    """A checklist row. Source text is not a document and is not copied."""
    domain = control.get("domain") or "UNKNOWN"
    folder = None if domain == "UNKNOWN" else domain
    control_id = str(control.get("id") or "")
    suffix = control_id[len("CTRL-") :] if control_id.startswith("CTRL-") else control_id
    return {
        "id": f"CHK-{suffix}" if suffix else "CHK-UNNAMED",
        "source_control": control_id or None,
        "folder": folder,
        "folder_id": None if folder is None else f"FOLDER-{folder}",
        "entity": control.get("entity"),
        "area": control.get("area"),
        "unexpected_entity": bool(control.get("unexpected_entity")),
        "document": None,
        "filename": None,
        "slot": "EMPTY",
        "filled": False,
        "shared": False,
        "buyer_access": False,
        "proven": False,
        "why": "No document is in this slot. Source text is not copied into the data room.",
    }


def _folders(slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in evidence.DOMAINS:
        matched = [row for row in slots if row["folder"] == spec["id"]]
        rows.append(
            {
                "id": f"FOLDER-{spec['id']}",
                "domain": spec["id"],
                "name": spec["name"],
                "path": f"VDR/{spec['name']}",
                "on_disk": False,
                "required": True,
                "documents": [],
                "document_count": 0,
                "slot": "EMPTY",
                "checklist_count": len(matched),
                "empty_slots": len(matched),
                "filled_slots": 0,
                "shared": False,
                "share_url": None,
                "buyer_access": False,
                "live_share": False,
                "buyers": [],
                "why": "Required folder name only. No file is stored here.",
            }
        )
    return rows


def _unmapped(slots: list[dict[str, Any]]) -> dict[str, Any]:
    matched = [row for row in slots if row["folder"] is None]
    return {
        "folder": None,
        "required": False,
        "documents": [],
        "document_count": 0,
        "slot": "EMPTY",
        "checklist_count": len(matched),
        "empty_slots": len(matched),
        "filled_slots": 0,
        "shared": False,
        "buyer_access": False,
        "why": (
            "These slots are not placed in Finance, HR, Legal, Ops, Compliance, or Tech. "
            "They are not forced into a folder."
        ),
    }


def _tree(folders: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": "VDR",
        "name": "Buyer data room",
        "path": "VDR",
        "on_disk": False,
        "documents": [],
        "document_count": 0,
        "shared": False,
        "share_url": None,
        "buyer_access": False,
        "live_share": False,
        "buyers": [],
        "buyer_count": 0,
        "children": folders,
    }


def build_room(
    csv_path: Path | str | None = None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
    entity: str | None = None,
    folder: str | None = None,
) -> dict[str, Any]:
    """Read-only room. Filters narrow the checklist. They do not invent folders or files."""
    entity_token = _filter_entity(entity)
    folder_token = _filter_folder(folder)
    flags = honesty_flags(ledger_path, catalog_db)
    controls = _load_controls(csv_path)
    slots = [_slot(row) for row in controls]
    list_matches = len(slots) == CANON_SLOTS
    scoped = slots
    if entity_token:
        scoped = [row for row in scoped if row["entity"] == entity_token]
    folders = _folders(scoped)
    shown = scoped
    if folder_token == "UNKNOWN":
        shown = [row for row in scoped if row["folder"] is None]
    elif folder_token:
        shown = [row for row in scoped if row["folder"] == folder_token]
    empty_slots = sum(1 for row in shown if row["slot"] == "EMPTY")
    filled_slots = sum(1 for row in shown if row["filled"])
    return {
        "ok": True,
        "cap": CAP_ID,
        "slice": "sale_buyer_dataroom",
        "framework_skeleton": "BUILT",
        "read_only": True,
        "on_disk": False,
        "buyer_access": False,
        "live_share": False,
        "vdr_share": False,
        "vdr_export": False,
        "buyer_export": False,
        "documents_invented": False,
        "ledger_write": False,
        "external_writes": False,
        "buyers": [],
        "buyer_count": 0,
        "seeded_from": ["docs/canon/build-dashboard/Sale_Readiness.csv"],
        "folders_expected": FOLDER_COUNT,
        "folder_count": len(folders),
        "slots_expected": CANON_SLOTS,
        "slots_read": len(slots),
        "slot_list_matches_canon": list_matches,
        "slot_count": len(shown),
        "empty_slots": empty_slots,
        "filled_slots": filled_slots,
        "document_count": 0,
        "filters": {"entity": entity_token, "folder": folder_token},
        "tree": _tree(folders),
        "folders": folders,
        "checklist": shown,
        "unmapped": _unmapped(scoped),
        "honesty": flags,
    }


def read_folder(
    folder_id: str,
    csv_path: Path | str | None = None,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """One folder. A share or export token is refused. A missing id is not invented."""
    token = (folder_id or "").strip()
    upper = token.upper()
    if not token or upper in {"TREE", "CHECKLIST"}:
        raise BuyerDataroomError("That path is not a folder.", code="not_found")
    if upper in {"SHARE", "VDR-SHARE"}:
        refuse_share()
    if upper in {"EXPORT", "DOWNLOAD"}:
        refuse_export()
    if upper in {"GRANT", "BUYER", "ACCESS"}:
        refuse_buyer_access()
    if upper in {"UPLOAD", "FILL"}:
        refuse_fill()
    room = build_room(csv_path=csv_path, ledger_path=ledger_path, catalog_db=catalog_db)
    want = upper if upper.startswith("FOLDER-") else f"FOLDER-{upper}"
    for folder in room["folders"]:
        if folder["id"] == want or folder["domain"] == upper:
            items = [row for row in room["checklist"] if row["folder_id"] == folder["id"]]
            return {
                "ok": True,
                "cap": CAP_ID,
                "folder": folder,
                "checklist": items,
                "document_count": 0,
                "on_disk": False,
                "buyer_access": False,
                "live_share": False,
                "vdr_share": False,
                "vdr_export": False,
                "ledger_write": False,
                "honesty": room["honesty"],
            }
    raise BuyerDataroomError("Folder was not in the taxonomy. It was not invented.", code="not_found")
