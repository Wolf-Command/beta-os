#!/usr/bin/env python3
"""CAP-MSC-01 asset and maintenance register v1 (Beta only).

Decision served: 2026-09-20 plan
docs/deliveries/GROK-PLAN-MSC-ASSET-REGISTER-V1-2026-09-20.md.
CR-7ea69933a9d39ba9 stays OPEN. Owner lane msc-asset-register-v1.
Wave-6 after dr-crown-jewel-framework e40e7c7.
intel-learning-policy-v1 stays parked.

A row is an id, a venue that already exists, a type, a status, and a
last-service note. The live register starts empty. An empty register is
not an inventory count and not a payment. A location is not an asset.
This module does not write Production, Alchemist, the Model C ledger, or
the completion row. CAP-MSC-01 stays at the ledger value. The ceiling
label is BUILT unless the ledger is already PROVEN or READY.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "msc_asset_register.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-7ea69933a9d39ba9"
CAP_ID = "CAP-MSC-01"
SCHEMA_ID = "wolf.cap-msc-01.asset-register.v1"
TZ_UTC = timezone.utc

STATUS_NOTED = "NOTED"
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
REGISTER_KEYS = frozenset({"venue", "type", "status", "last_service"})

PAYMENT_KEYS = frozenset(
    {
        "payment",
        "payments",
        "money",
        "price",
        "prices",
        "amount",
        "cost",
        "fee",
        "fees",
        "invoice",
        "receipt",
        "paid",
        "currency",
        "idr",
        "usd",
        "tariff",
        "transfer",
        "bank",
    }
)
INVENTORY_KEYS = frozenset(
    {
        "inventory",
        "inventory_count",
        "count",
        "counts",
        "quantity",
        "qty",
        "stock",
        "census",
        "asset_count",
        "units",
    }
)
MATURITY_KEYS = frozenset(
    {
        "proven",
        "prove",
        "ready",
        "maturity",
        "ledger",
        "resolve",
        "cr_resolved",
        "production",
        "alchemist",
        "score",
    }
)

_PAYMENT_TEXT = re.compile(
    r"(?:^|[\s(])(?:rp|idr|usd|\$|€|£)\s*\d|\d+(?:[.,]\d+)?\s*(?:rp|idr|usd)\b",
    re.IGNORECASE,
)
_PAYMENT_WORD = re.compile(
    r"\b(?:paid|invoice|receipt|payment|transfer)\b",
    re.IGNORECASE,
)
_BARE_NUMBER = re.compile(r"^\d+(?:[.,]\d+)?$")
_COUNT_PHRASE = re.compile(
    r"\b\d+\s*(?:units?|items?|assets?|pcs|pieces|qty)\b",
    re.IGNORECASE,
)
_TYPE_RE = re.compile(r"^[A-Za-z][A-Za-z][A-Za-z -]{0,38}$")
_VENUE_RE = re.compile(r"^LOC-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
_ASSET_RE = re.compile(
    r"^AST-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)

REFUSED_STATUS = frozenset(
    {
        "PROVEN",
        "READY",
        "BUILT",
        "SPECIFIED",
        "ABSENT",
        "LIVE",
        "PAID",
        "SERVICED",
        "OPERATIONAL",
        "GREEN",
        "SUCCESS",
        "COUNTED",
        "INVENTORY",
    }
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "msc_asset_register_v1",
    "slice_label": "BUILT",
    "empty_honest": True,
    "empty_is_inventory": False,
    "inventory_count": None,
    "recorded_is_inventory": False,
    "payment": None,
    "money": None,
    "service_proved": False,
    "last_service_is_note": True,
    "media_library_is_not_inventory": True,
    "locations_are_not_assets": True,
    "score_changed": False,
    "production": False,
    "alchemist_write": False,
    "anon_fail_closed": True,
    "owner_read": True,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "invented_proven": False,
    "invented_ready": False,
    "ledger_write": False,
}


class AssetRegisterError(ValueError):
    """Fail closed. Does not invent an inventory count, a payment, or PROVEN."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_asset_id() -> str:
    return f"AST-{uuid.uuid4()}"


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def _assert_beta_path(resolved: Path) -> None:
    low = str(resolved).lower()
    if "alchemist" in low:
        raise AssetRegisterError(
            "asset register refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise AssetRegisterError(
            "asset register refuses a wolf-system path",
            code="not_beta",
        )
    if "/production" in low or low.endswith("money.sqlite"):
        raise AssetRegisterError(
            "asset register refuses a production path",
            code="not_beta",
        )
    try:
        resolved.resolve().relative_to(BETA_ROOT)
        return
    except ValueError:
        pass
    import tempfile

    tmp = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.resolve().relative_to(tmp)
    except ValueError as exc:
        raise AssetRegisterError(
            "asset register refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def _resolve_db(db_path: Path | str | None) -> Path:
    if db_path is not None:
        path = Path(db_path)
    else:
        override = (os.environ.get("WOLF_MSC_ASSET_DB") or "").strip()
        path = Path(override) if override else DEFAULT_DB
    resolved = path.resolve()
    _assert_beta_path(resolved)
    if resolved.name == "content_library.sqlite" or resolved == CATALOG_DB.resolve():
        raise AssetRegisterError(
            "asset register does not write the content catalog",
            code="catalog_refused",
        )
    return resolved


def assert_db_writable(db_path: Path) -> None:
    resolved = Path(db_path).resolve()
    if (os.environ.get("WOLF_ALLOW_LIVE_MSC_ASSET") or "").strip() == "1":
        return
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        raise AssetRegisterError(
            "test mode refuses writes to the live asset register; "
            "point db_path at a temp file",
            code="live_guard",
        )


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-MSC-01. Does not write the ledger."""
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    _assert_beta_path(path.resolve())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    row = data.get(CAP_ID) if isinstance(data, dict) else None
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    state = str(row[0]).strip().upper()
    if state not in MATURITY:
        return "UNKNOWN"
    return state


def ceiling_for(state: str) -> str:
    """BUILT label unless the ledger is already higher. Does not write it."""
    if state in HIGHER_THAN_BUILT:
        return state
    return "BUILT"


def load_cr_binding(catalog_db: Path | str | None = None) -> dict[str, Any]:
    """Read CR-7ea69933a9d39ba9. Does not upsert, resolve, or harvest."""
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
    _assert_beta_path(path.resolve())
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
    flags = dict(HONESTY)
    flags.update(load_cr_binding(catalog_db))
    flags["ledger_maturity"] = state
    flags["maturity"] = state
    flags["maturity_ceiling"] = ceiling_for(state)
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["invented_proven"] = False
    flags["invented_ready"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["inventory_count"] = None
    flags["payment"] = None
    flags["money"] = None
    flags["service_proved"] = False
    flags["empty_is_inventory"] = False
    flags["recorded_is_inventory"] = False
    return flags


def known_venues(catalog_db: Path | str | None = None) -> list[dict[str, Any]] | None:
    """Read org_locations. None means unread, which is not zero venues.

    A location row is not an asset and not an inventory count. This read
    does not touch the content-library media table.
    """
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    if not path.is_file():
        return None
    _assert_beta_path(path.resolve())
    uri = path.resolve().as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return None
    try:
        rows = conn.execute(
            """
            SELECT location_id, entity_id, display_name, location_type, status
            FROM org_locations
            ORDER BY location_id
            """
        ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    out: list[dict[str, Any]] = []
    for location_id, entity_id, display_name, location_type, org_status in rows:
        out.append(
            {
                "location_id": location_id,
                "entity_id": entity_id,
                "display_name": display_name,
                "location_type": location_type,
                "org_status": org_status,
                "asset": None,
                "inventory_count": None,
                "payment": None,
            }
        )
    return out


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "additionalProperties": False,
        "required": ["venue", "type", "status", "last_service"],
        "properties": {
            "id": {"type": "string", "description": "Minted. Not accepted on write."},
            "venue": {"type": "string", "description": "Existing org_locations.location_id"},
            "type": {"type": "string"},
            "status": {"type": "string", "enum": [STATUS_NOTED]},
            "last_service": {"type": "string", "description": "A note. Not a payment."},
        },
        "status_enum": [STATUS_NOTED],
        "refused_status": sorted(REFUSED_STATUS),
        "payment_property": False,
        "inventory_property": False,
        "id_accepted_on_write": False,
    }


def _key_code(key: str) -> str | None:
    token = key.strip().lower()
    if token in PAYMENT_KEYS:
        return "payment_refused"
    if token in INVENTORY_KEYS:
        return "inventory_refused"
    if token in {"proven", "prove"}:
        return "proven_refused"
    if token == "ready":
        return "ready_refused"
    if token in {"resolve", "cr_resolved"}:
        return "resolve_refused"
    if token in {"production", "production_mutate"}:
        return "production_refused"
    if token in {"maturity", "ledger", "score"}:
        return "ledger_write_refused"
    if token == "alchemist":
        return "alchemist_refused"
    if token in {"fill", "slots_filled"}:
        return "slots_refused"
    return None


def _reject_keys(payload: dict) -> None:
    for key in payload:
        code = _key_code(str(key))
        if code == "payment_refused":
            refuse_payment(payload)
        if code == "inventory_refused":
            refuse_inventory(payload)
        if code == "proven_refused":
            refuse_proven(payload)
        if code == "ready_refused":
            refuse_ready(payload)
        if code == "resolve_refused":
            refuse_resolve(payload)
        if code == "production_refused":
            refuse_production(payload)
        if code == "ledger_write_refused":
            raise AssetRegisterError(
                "The ledger is not written from the asset register.",
                code="ledger_write_refused",
            )
        if code == "alchemist_refused":
            raise AssetRegisterError(
                "asset register refuses an Alchemist write",
                code="alchemist_refused",
            )
        if code == "slots_refused":
            refuse_fill(payload)
        if str(key) not in REGISTER_KEYS:
            raise AssetRegisterError(
                "An asset row only accepts venue, type, status, and a last-service note.",
                code="extra_field_refused",
            )


def _looks_like_payment(text: str) -> bool:
    token = text.strip()
    if not token:
        return False
    if _PAYMENT_TEXT.search(token):
        return True
    return _PAYMENT_WORD.search(token) is not None


def _looks_like_count(text: str) -> bool:
    token = text.strip()
    if not token:
        return False
    if _BARE_NUMBER.fullmatch(token):
        return True
    return _COUNT_PHRASE.search(token) is not None


def _validate_type(raw: Any) -> str:
    if not isinstance(raw, str):
        raise AssetRegisterError("A type label is required.", code="fields_required")
    label = raw.strip()
    if _looks_like_count(label):
        refuse_inventory({"type": label})
    if _looks_like_payment(label):
        refuse_payment({"type": label})
    if not _TYPE_RE.fullmatch(label):
        raise AssetRegisterError(
            "A type is a short word, not a count and not a payment.",
            code="fields_required",
        )
    if label.upper() in REFUSED_STATUS or label.upper() in {"PAYMENT", "INVENTORY", "COUNT"}:
        raise AssetRegisterError(
            "A maturity word, a payment, or a count is not a type.",
            code="status_refused",
        )
    return label


def _validate_note(raw: Any) -> str:
    if not isinstance(raw, str):
        raise AssetRegisterError(
            "A last-service note is required. A blank note is not a service.",
            code="note_required",
        )
    note = raw.strip()
    if len(note) < 8 or len(note) > 240:
        raise AssetRegisterError(
            "A last-service note is required. A blank note is not a service.",
            code="note_required",
        )
    if _looks_like_count(note):
        refuse_inventory({"last_service": note})
    if _looks_like_payment(note):
        refuse_payment({"last_service": note})
    return note


def _validate_status(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise AssetRegisterError("Status must be NOTED.", code="status_refused")
    status = raw.strip().upper()
    if status == "PROVEN":
        refuse_proven({})
    if status == "READY":
        refuse_ready({})
    if status in {"PAID", "INVOICE"}:
        refuse_payment({})
    if status in {"COUNTED", "INVENTORY"}:
        refuse_inventory({})
    if status != STATUS_NOTED:
        raise AssetRegisterError(
            "Status must be NOTED. PROVEN, READY, a payment, and a count are not statuses.",
            code="status_refused",
        )
    return status


def refuse_payment(_body: dict | None = None) -> None:
    raise AssetRegisterError(
        "A payment is not stored on this register. No amount is kept.",
        code="payment_refused",
    )


def refuse_inventory(_body: dict | None = None) -> None:
    raise AssetRegisterError(
        "An inventory count is refused. Unread is not zero. A note is not a census.",
        code="inventory_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise AssetRegisterError(
        "PROVEN is refused. The ceiling label is BUILT unless the ledger is already higher.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise AssetRegisterError(
        "READY is refused. This register does not mark the capability ready.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise AssetRegisterError(
        "Resolving the completion row is refused. CR-7ea69933a9d39ba9 stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise AssetRegisterError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise AssetRegisterError(
        "An empty register stays empty. A row without a note is not filled in.",
        code="slots_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if isinstance(payload, dict):
        _reject_keys(payload)
    raise AssetRegisterError(
        "This path does not invent an asset, an inventory count, or a payment.",
        code="writes_refused",
    )


def resolve_cr(*_args: Any, **_kwargs: Any) -> None:
    refuse_resolve({})


def mark_proven(*_args: Any, **_kwargs: Any) -> None:
    refuse_proven({})


def _truthy(value: str | None) -> bool:
    token = (value or "").strip().lower()
    return token not in {"", "0", "false", "no", "off"}


def _present(value: str | None) -> bool:
    return (value or "").strip() != ""


def guard_query(
    *,
    payment: str | None = None,
    money: str | None = None,
    count: str | None = None,
    inventory: str | None = None,
    prove: str | None = None,
    proven: str | None = None,
    ready: str | None = None,
    resolve: str | None = None,
    production: str | None = None,
    fill: str | None = None,
    write: str | None = None,
) -> None:
    if _present(payment) or _present(money):
        refuse_payment({})
    if _present(count) or _present(inventory) or _truthy(count):
        refuse_inventory({})
    if _present(proven) or _present(prove):
        refuse_proven({})
    if _present(ready):
        refuse_ready({})
    if _present(resolve):
        refuse_resolve({})
    if _present(production):
        refuse_production({})
    if _present(fill):
        refuse_fill({})
    if _present(write):
        refuse_external_write({})


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS asset_notes (
            id TEXT PRIMARY KEY,
            venue TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            status TEXT NOT NULL,
            last_service TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            recorded_by TEXT NOT NULL
        )
        """
    )
    return conn


def _row_to_asset(row: tuple, venues: dict[str, str]) -> dict[str, Any] | None:
    asset_id, venue, asset_type, status, last_service, recorded_at, recorded_by = row
    if status != STATUS_NOTED:
        return None
    if not isinstance(last_service, str) or len(last_service.strip()) < 8:
        return None
    if _looks_like_payment(last_service) or _looks_like_count(last_service):
        return None
    return {
        "id": asset_id,
        "venue": venue,
        "venue_name": venues.get(venue),
        "type": asset_type,
        "status": status,
        "last_service": last_service,
        "last_service_is_note": True,
        "recorded_at": recorded_at,
        "recorded_by": recorded_by,
        "inventory_count": None,
        "payment": None,
        "service_proved": False,
    }


def list_assets(db_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Recorded notes only. A missing file is an empty register, not a census."""
    if db_path is None and not (os.environ.get("WOLF_MSC_ASSET_DB") or "").strip():
        if not DEFAULT_DB.is_file():
            return []
    resolved = _resolve_db(db_path)
    if not resolved.is_file():
        return []
    venues = {
        row["location_id"]: row["display_name"]
        for row in (known_venues() or [])
    }
    uri = resolved.as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return []
    try:
        rows = conn.execute(
            """
            SELECT id, venue, asset_type, status, last_service, recorded_at, recorded_by
            FROM asset_notes
            ORDER BY recorded_at, id
            """
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    assets: list[dict[str, Any]] = []
    for row in rows:
        item = _row_to_asset(row, venues)
        if item is not None:
            assets.append(item)
    return assets


def register_asset(
    body: dict,
    *,
    person_id: str,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Append one noted row. Does not store a payment or an inventory count."""
    if not isinstance(body, dict):
        raise AssetRegisterError("An asset body must be an object.", code="fields_required")
    _reject_keys(body)
    if (person_id or "").strip() != OWNER_PERSON:
        raise AssetRegisterError(
            "Only the Owner can record an asset note.",
            code="forbidden",
        )
    venue_raw = body.get("venue")
    if not isinstance(venue_raw, str) or not venue_raw.strip():
        raise AssetRegisterError(
            "Venue must be an existing location id.",
            code="venue_unknown",
        )
    venue = venue_raw.strip()
    if _looks_like_count(venue):
        refuse_inventory({"venue": venue})
    if _looks_like_payment(venue):
        refuse_payment({"venue": venue})
    if not _VENUE_RE.fullmatch(venue):
        raise AssetRegisterError(
            "Venue must be an existing location id. This register does not invent a venue.",
            code="venue_unknown",
        )
    asset_type = _validate_type(body.get("type"))
    status = _validate_status(body.get("status"))
    note = _validate_note(body.get("last_service"))
    venues = known_venues(catalog_db)
    if venues is None:
        raise AssetRegisterError(
            "Venue allowlist is unread. Unread is not zero venues, and the row is not stored.",
            code="venues_unread",
        )
    allowed = {row["location_id"] for row in venues}
    if venue not in allowed:
        raise AssetRegisterError(
            "Venue must already exist on org_locations. This register does not invent a venue.",
            code="venue_unknown",
        )
    names = {row["location_id"]: row["display_name"] for row in venues}
    resolved = _resolve_db(db_path)
    assert_db_writable(resolved)
    asset_id = mint_asset_id()
    recorded_at = now_utc_iso()
    conn = _connect(resolved)
    try:
        conn.execute(
            """
            INSERT INTO asset_notes
                (id, venue, asset_type, status, last_service, recorded_at, recorded_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (asset_id, venue, asset_type, status, note, recorded_at, OWNER_PERSON),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "ok": True,
        "id": asset_id,
        "venue": venue,
        "venue_name": names.get(venue),
        "type": asset_type,
        "status": status,
        "last_service": note,
        "last_service_is_note": True,
        "recorded_at": recorded_at,
        "recorded_by": OWNER_PERSON,
        "inventory_count": None,
        "payment": None,
        "service_proved": False,
        "ledger_write": False,
        "cr_resolved": False,
    }


def read_asset(asset_id: str, db_path: Path | str | None = None) -> dict[str, Any]:
    token = (asset_id or "").strip()
    if not _ASSET_RE.fullmatch(token):
        raise AssetRegisterError("Unknown asset id.", code="not_found")
    for row in list_assets(db_path):
        if row["id"] == token:
            return {
                "ok": True,
                "asset": row,
                "inventory_count": None,
                "payment": None,
                "service_proved": False,
                "ledger_write": False,
                "cr_resolved": False,
                "honesty": honesty_flags(),
            }
    raise AssetRegisterError("Unknown asset id.", code="not_found")


def build_register(
    db_path: Path | str | None = None,
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    rows = list_assets(db_path)
    venues = known_venues(catalog_db)
    flags = honesty_flags(ledger_path, catalog_db)
    recorded = len(rows)
    return {
        "ok": True,
        "cap": CAP_ID,
        "schema_id": SCHEMA_ID,
        "schema": schema_document(),
        "empty": recorded == 0,
        "empty_is_inventory": False,
        "recorded_count": recorded,
        "recorded_is_inventory": False,
        "inventory_count": None,
        "payment": None,
        "money": None,
        "service_proved": False,
        "rows": rows,
        "venues": venues,
        "locations_are_not_assets": True,
        "venue_allowlist_unread": venues is None,
        "media_library_is_not_inventory": True,
        "framework_skeleton": "BUILT",
        "ledger_write": False,
        "cr_resolved": flags["cr_resolved"] if flags["cr_state"] == "RESOLVED" else False,
        "honesty": flags,
    }
