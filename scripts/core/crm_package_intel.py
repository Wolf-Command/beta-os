#!/usr/bin/env python3
"""CAP-CRM-03 package product register v1 (Beta only).

Decision served: 2026-09-20 plan
docs/deliveries/GROK-PLAN-CRM-PACKAGE-INTEL-V1-2026-09-20.md.
CR-e5ff219bb1d585f7 next action is Implementation. Owner lane
crm-package-intel-v1. Wave-6 after intg-gws-integrate-prove 3ac2f28.
intel-learning-policy-v1 stays parked.

A package row is a name, a brand id that already exists, a status, and
evidence refs. The live register starts empty. An empty register is not a
market census and not a price. This module does not write a booking, a
price, the Model C ledger, or the completion row. CAP-CRM-03 stays at the
ledger value. The ceiling label is BUILT unless the ledger is already
PROVEN or READY. The CR is not resolved.
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
DEFAULT_DB = BETA_ROOT / "catalog" / "crm_package_intel.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-e5ff219bb1d585f7"
CAP_ID = "CAP-CRM-03"
SCHEMA_ID = "wolf.cap-crm-03.package-register.v1"
TZ_UTC = timezone.utc

STATUS_NAMED = "NAMED"
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
REGISTER_KEYS = frozenset({"name", "brand", "status", "evidence_refs"})

PRICE_KEYS = frozenset(
    {
        "price",
        "prices",
        "amount",
        "rate",
        "currency",
        "margin",
        "cost",
        "fee",
        "fees",
        "idr",
        "usd",
        "tariff",
        "priced",
        "pricing",
        "pricing_is_truth",
    }
)
BOOKING_KEYS = frozenset(
    {
        "booking",
        "bookings",
        "reservation",
        "reservations",
        "availability",
        "book",
        "occupancy",
        "nights",
        "booking_id",
        "booking_db",
        "mutate_booking",
        "booking_mutated",
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
        "demand",
        "census",
        "market_package_count",
        "score",
    }
)

_PRICE_TEXT = re.compile(
    r"(?:^|[\s(])(?:rp|idr|usd|\$|€|£)\s*\d|\d+(?:[.,]\d+)?\s*(?:rp|idr|usd)\b",
    re.IGNORECASE,
)
_BARE_NUMBER = re.compile(r"^\d+(?:[.,]\d+)?$")
_EVIDENCE_RE = re.compile(
    r"^(?:EV-[A-Za-z0-9][A-Za-z0-9._:/-]{2,120}|docs/[A-Za-z0-9][A-Za-z0-9._/-]{2,160}\.md)$"
)
_PKG_RE = re.compile(
    r"^PKG-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)

REFUSED_STATUS = frozenset(
    {
        "PROVEN",
        "READY",
        "BUILT",
        "SPECIFIED",
        "ABSENT",
        "LIVE",
        "BOOKED",
        "PRICED",
        "AVAILABLE",
        "SOLD",
        "GREEN",
        "SUCCESS",
    }
)

HONESTY = {
    "cap": CAP_ID,
    "slice": "crm_package_intel_v1",
    "slice_label": "BUILT",
    "empty_honest": True,
    "empty_is_market_census": False,
    "pricing_is_truth": False,
    "price": None,
    "margin": None,
    "demand": None,
    "market_package_count": None,
    "booking_mutated": False,
    "live_booking_write": False,
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


class PackageIntelError(ValueError):
    """Fail closed. Does not invent a price, a booking, or PROVEN."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def now_utc_iso() -> str:
    return datetime.now(TZ_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def mint_package_id() -> str:
    return f"PKG-{uuid.uuid4()}"


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def _assert_beta_path(resolved: Path) -> None:
    low = str(resolved).lower()
    if "alchemist" in low:
        raise PackageIntelError(
            "package register refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise PackageIntelError(
            "package register refuses a wolf-system path",
            code="not_beta",
        )
    if "/production" in low or low.endswith("money.sqlite"):
        raise PackageIntelError(
            "package register refuses a production path",
            code="not_beta",
        )
    if "booking" in low or "reservation" in low:
        raise PackageIntelError(
            "package register refuses a booking path",
            code="booking_refused",
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
        raise PackageIntelError(
            "package register refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def _resolve_db(db_path: Path | str | None) -> Path:
    if db_path is not None:
        path = Path(db_path)
    else:
        override = (os.environ.get("WOLF_CRM_PACKAGE_DB") or "").strip()
        path = Path(override) if override else DEFAULT_DB
    resolved = path.resolve()
    _assert_beta_path(resolved)
    if resolved.name == "content_library.sqlite" or resolved == CATALOG_DB.resolve():
        raise PackageIntelError(
            "package register does not write the lead catalog",
            code="catalog_refused",
        )
    return resolved


def assert_db_writable(db_path: Path) -> None:
    resolved = Path(db_path).resolve()
    if (os.environ.get("WOLF_ALLOW_LIVE_CRM_PACKAGE") or "").strip() == "1":
        return
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        raise PackageIntelError(
            "test mode refuses writes to the live package register; "
            "point db_path at a temp file",
            code="live_guard",
        )


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-CRM-03. Does not write the ledger."""
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
    """Read CR-e5ff219bb1d585f7. Does not upsert, resolve, or harvest."""
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
    flags["pricing_is_truth"] = False
    flags["price"] = None
    flags["booking_mutated"] = False
    flags["market_package_count"] = None
    return flags


def known_brands(catalog_db: Path | str | None = None) -> list[dict[str, Any]] | None:
    """Read org_brands. None means unread, which is not zero brands."""
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
            SELECT brand_id, entity_id, display_name, status
            FROM org_brands
            ORDER BY brand_id
            """
        ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    out: list[dict[str, Any]] = []
    for brand_id, entity_id, display_name, org_status in rows:
        out.append(
            {
                "brand_id": brand_id,
                "entity_id": entity_id,
                "display_name": display_name,
                "org_status": org_status,
                "package": None,
                "price": None,
            }
        )
    return out


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "additionalProperties": False,
        "required": ["name", "brand", "status", "evidence_refs"],
        "properties": {
            "name": {"type": "string"},
            "brand": {"type": "string", "description": "Existing org_brands.brand_id"},
            "status": {"type": "string", "enum": [STATUS_NAMED]},
            "evidence_refs": {"type": "array", "minItems": 1},
        },
        "status_enum": [STATUS_NAMED],
        "refused_status": sorted(REFUSED_STATUS),
        "price_property": False,
        "pricing_is_truth": False,
        "booking_property": False,
    }


def _key_code(key: str) -> str | None:
    token = key.strip().lower()
    if token in PRICE_KEYS:
        return "price_refused"
    if token in BOOKING_KEYS:
        return "booking_refused"
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
    if token in {"demand", "census", "market_package_count"}:
        return "invent_metrics_refused"
    if token == "alchemist":
        return "alchemist_refused"
    if token in {"fill", "slots_filled"}:
        return "slots_refused"
    return None


def _reject_keys(payload: dict) -> None:
    for key in payload:
        code = _key_code(str(key))
        if code == "price_refused":
            refuse_price(payload)
        if code == "booking_refused":
            refuse_booking(payload)
        if code == "proven_refused":
            refuse_proven(payload)
        if code == "ready_refused":
            refuse_ready(payload)
        if code == "resolve_refused":
            refuse_resolve(payload)
        if code == "production_refused":
            refuse_production(payload)
        if code == "ledger_write_refused":
            raise PackageIntelError(
                "The ledger is not written from the package register.",
                code="ledger_write_refused",
            )
        if code == "invent_metrics_refused":
            refuse_invent_metrics(payload)
        if code == "alchemist_refused":
            raise PackageIntelError(
                "package register refuses an Alchemist write",
                code="alchemist_refused",
            )
        if code == "slots_refused":
            refuse_fill(payload)
        if str(key) not in REGISTER_KEYS:
            raise PackageIntelError(
                "A package row only accepts name, brand, status, and evidence refs.",
                code="extra_field_refused",
            )


def _looks_like_price(text: str) -> bool:
    token = text.strip()
    if not token:
        return False
    if _BARE_NUMBER.fullmatch(token):
        return True
    return _PRICE_TEXT.search(token) is not None


def _validate_evidence(raw: Any) -> list[str]:
    if not isinstance(raw, list) or not raw:
        raise PackageIntelError(
            "A package row needs at least one evidence ref. An empty list is not evidence.",
            code="evidence_required",
        )
    if len(raw) > 8:
        raise PackageIntelError(
            "Too many evidence refs on one row.",
            code="evidence_required",
        )
    refs: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise PackageIntelError(
                "An evidence ref is a string, not a price object.",
                code="evidence_required",
            )
        ref = item.strip()
        if _looks_like_price(ref):
            refuse_price({"price": ref})
        if not _EVIDENCE_RE.fullmatch(ref):
            raise PackageIntelError(
                "An evidence ref must be EV-… or a docs/….md path. A price is not evidence.",
                code="evidence_required",
            )
        refs.append(ref)
    return refs


def _validate_name(raw: Any) -> str:
    if not isinstance(raw, str):
        raise PackageIntelError("A package name is required.", code="fields_required")
    name = raw.strip()
    if len(name) < 2 or len(name) > 80:
        raise PackageIntelError("A package name is required.", code="fields_required")
    if _looks_like_price(name):
        refuse_price({"price": name})
    upper = name.upper()
    if upper in REFUSED_STATUS:
        raise PackageIntelError(
            "A maturity word is not a package name.",
            code="status_refused",
        )
    return name


def _validate_status(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise PackageIntelError("Status must be NAMED.", code="status_refused")
    status = raw.strip().upper()
    if status in {"PROVEN"}:
        refuse_proven({})
    if status == "READY":
        refuse_ready({})
    if status in {"BOOKED", "AVAILABLE"}:
        refuse_booking({})
    if status in {"PRICED", "SOLD"}:
        refuse_price({})
    if status != STATUS_NAMED:
        raise PackageIntelError(
            "Status must be NAMED. PROVEN, READY, and a price are not statuses.",
            code="status_refused",
        )
    return status


def refuse_price(_body: dict | None = None) -> None:
    raise PackageIntelError(
        "A price is not truth on this register. No amount is stored.",
        code="price_refused",
    )


def refuse_booking(_body: dict | None = None) -> None:
    raise PackageIntelError(
        "A live booking mutation is refused. This register does not book.",
        code="booking_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise PackageIntelError(
        "PROVEN is refused. The ceiling label is BUILT unless the ledger is already higher.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise PackageIntelError(
        "READY is refused. This register does not mark the capability ready.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise PackageIntelError(
        "Resolving the completion row is refused. CR-e5ff219bb1d585f7 stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise PackageIntelError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise PackageIntelError(
        "An empty register stays empty. A product without evidence is not filled in.",
        code="slots_refused",
    )


def refuse_invent_metrics(_body: dict | None = None) -> None:
    raise PackageIntelError(
        "A market count, margin, or demand figure is refused. Unread is not zero.",
        code="invent_metrics_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if isinstance(payload, dict):
        _reject_keys(payload)
    raise PackageIntelError(
        "This path does not invent a package, a price, or a booking.",
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
    price: str | None = None,
    booking: str | None = None,
    prove: str | None = None,
    proven: str | None = None,
    ready: str | None = None,
    resolve: str | None = None,
    production: str | None = None,
    fill: str | None = None,
    demand: str | None = None,
    margin: str | None = None,
    write: str | None = None,
) -> None:
    if _present(price):
        refuse_price({})
    if _present(booking) or _truthy(booking):
        refuse_booking({})
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
    if _present(demand) or _present(margin):
        refuse_invent_metrics({})
    if _present(write):
        refuse_external_write({})


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS package_products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            brand TEXT NOT NULL,
            status TEXT NOT NULL,
            evidence_refs TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            recorded_by TEXT NOT NULL
        )
        """
    )
    return conn


def _row_to_product(row: tuple) -> dict[str, Any] | None:
    package_id, name, brand, status, evidence_raw, recorded_at, recorded_by = row
    if status != STATUS_NAMED:
        return None
    try:
        refs = json.loads(evidence_raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(refs, list) or not refs:
        return None
    clean = [item for item in refs if isinstance(item, str) and _EVIDENCE_RE.fullmatch(item)]
    if not clean:
        return None
    return {
        "id": package_id,
        "name": name,
        "brand": brand,
        "status": status,
        "evidence_refs": clean,
        "recorded_at": recorded_at,
        "recorded_by": recorded_by,
        "price": None,
        "pricing_is_truth": False,
    }


def list_products(db_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Recorded rows only. A missing file is an empty register, not a census."""
    if db_path is None and not (os.environ.get("WOLF_CRM_PACKAGE_DB") or "").strip():
        if not DEFAULT_DB.is_file():
            return []
    resolved = _resolve_db(db_path)
    if not resolved.is_file():
        return []
    uri = resolved.as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return []
    try:
        rows = conn.execute(
            """
            SELECT id, name, brand, status, evidence_refs, recorded_at, recorded_by
            FROM package_products
            ORDER BY recorded_at, id
            """
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    products: list[dict[str, Any]] = []
    for row in rows:
        item = _row_to_product(row)
        if item is not None:
            products.append(item)
    return products


def register_product(
    body: dict,
    *,
    person_id: str,
    db_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Append one evidenced row. Does not store a price or touch a booking."""
    if not isinstance(body, dict):
        raise PackageIntelError("A package body must be an object.", code="fields_required")
    _reject_keys(body)
    if (person_id or "").strip() != OWNER_PERSON:
        raise PackageIntelError(
            "Only the Owner can record a package row.",
            code="forbidden",
        )
    name = _validate_name(body.get("name"))
    status = _validate_status(body.get("status"))
    brand_raw = body.get("brand")
    if not isinstance(brand_raw, str) or not brand_raw.strip():
        raise PackageIntelError("Brand must be an existing brand id.", code="brand_unknown")
    brand = brand_raw.strip()
    refs = _validate_evidence(body.get("evidence_refs"))
    brands = known_brands(catalog_db)
    if brands is None:
        raise PackageIntelError(
            "Brand allowlist is unread. Unread is not zero brands, and the row is not stored.",
            code="brands_unread",
        )
    allowed = {row["brand_id"] for row in brands}
    if brand not in allowed:
        raise PackageIntelError(
            "Brand must already exist on org_brands. This register does not invent a brand.",
            code="brand_unknown",
        )
    resolved = _resolve_db(db_path)
    assert_db_writable(resolved)
    package_id = mint_package_id()
    recorded_at = now_utc_iso()
    conn = _connect(resolved)
    try:
        conn.execute(
            """
            INSERT INTO package_products
                (id, name, brand, status, evidence_refs, recorded_at, recorded_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                package_id,
                name,
                brand,
                status,
                json.dumps(refs, separators=(",", ":")),
                recorded_at,
                OWNER_PERSON,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "ok": True,
        "id": package_id,
        "name": name,
        "brand": brand,
        "status": status,
        "evidence_refs": refs,
        "recorded_at": recorded_at,
        "recorded_by": OWNER_PERSON,
        "price": None,
        "pricing_is_truth": False,
        "booking_mutated": False,
        "market_package_count": None,
        "ledger_write": False,
        "cr_resolved": False,
    }


def read_product(package_id: str, db_path: Path | str | None = None) -> dict[str, Any]:
    token = (package_id or "").strip()
    if not _PKG_RE.fullmatch(token):
        raise PackageIntelError("Unknown package id.", code="not_found")
    for row in list_products(db_path):
        if row["id"] == token:
            return {
                "ok": True,
                "product": row,
                "price": None,
                "pricing_is_truth": False,
                "booking_mutated": False,
                "market_package_count": None,
                "ledger_write": False,
                "cr_resolved": False,
                "honesty": honesty_flags(),
            }
    raise PackageIntelError("Unknown package id.", code="not_found")


def build_register(
    db_path: Path | str | None = None,
    *,
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    products = list_products(db_path)
    brands = known_brands(catalog_db)
    flags = honesty_flags(ledger_path, catalog_db)
    recorded = len(products)
    return {
        "ok": True,
        "cap": CAP_ID,
        "schema_id": SCHEMA_ID,
        "schema": schema_document(),
        "empty": recorded == 0,
        "empty_is_market_census": False,
        "recorded_count": recorded,
        "market_package_count": None,
        "price": None,
        "pricing_is_truth": False,
        "margin": None,
        "demand": None,
        "booking_mutated": False,
        "products": products,
        "brands": brands,
        "brands_are_not_packages": True,
        "brand_allowlist_unread": brands is None,
        "framework_skeleton": "BUILT",
        "ledger_write": False,
        "cr_resolved": flags["cr_resolved"] if flags["cr_state"] == "RESOLVED" else False,
        "honesty": flags,
    }
