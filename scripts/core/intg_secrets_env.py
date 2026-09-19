#!/usr/bin/env python3
"""CAP-INTG-07 secrets and environment separation skeleton v1 (Beta only).

Decision served: 2026-09-20 plan
docs/deliveries/GROK-PLAN-INTG-SECRETS-ENV-SEPARATION-V1-2026-09-20.md.
CR-273f30371bd52c8a stays OPEN. Owner lane intg-secrets-env-separation-v1.
Wave-7 after msc-records-defensibility-v1 5945509.
intel-learning-policy-v1 stays parked.
Bound beta-integration-health-readonly.

Names the vault, rotation, and Beta-Production separation slots and leaves
every slot empty. An empty framework is not proof of separation and not a
live vault. Existing .env.example, gitignore, and sacred-rule checks are
evidence pointers only. This module does not read secret values, and it
does not write Production, Alchemist, Cloudflare, Access, an external
secret store, the Model C ledger, or the completion row. CAP-INTG-07 stays
at the ledger value. The ceiling label is BUILT unless the ledger is
already PROVEN or READY.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "intg_secrets_env.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-273f30371bd52c8a"
CAP_ID = "CAP-INTG-07"
SCHEMA_ID = "wolf.cap-intg-07.secrets-env-separation.v1"
BOUND = "beta-integration-health-readonly"

KIND_IDS = ("vault", "rotation", "beta-prod")
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})

EVIDENCE_KINDS: tuple[dict[str, Any], ...] = (
    {
        "kind": "vault",
        "label": "Vault",
        "slot": "empty",
        "evidence": None,
        "vault": None,
        "rotation": None,
        "separation": None,
        "live_vault": False,
        "current": False,
        "separation_proved": False,
        "payment": None,
        "why": "Named vault slot. Empty is not a live vault and not proof of separation.",
    },
    {
        "kind": "rotation",
        "label": "Rotation",
        "slot": "empty",
        "evidence": None,
        "vault": None,
        "rotation": None,
        "separation": None,
        "live_vault": False,
        "current": False,
        "separation_proved": False,
        "payment": None,
        "why": "Named rotation slot. Empty is not current rotation and not proof of separation.",
    },
    {
        "kind": "beta-prod",
        "label": "Beta and Production separation",
        "slot": "empty",
        "evidence": None,
        "vault": None,
        "rotation": None,
        "separation": None,
        "live_vault": False,
        "current": False,
        "separation_proved": False,
        "payment": None,
        "why": "Named Beta-Production slot. Empty is not proof that Beta and Production are separated.",
    },
)

POINTER_SPECS: tuple[dict[str, str], ...] = (
    {
        "id": "env-example",
        "path": ".env.example",
        "label": ".env.example",
        "why": "Existing .env.example check is an evidence pointer only. It is not a vault and not proof of separation.",
    },
    {
        "id": "gitignore",
        "path": ".gitignore",
        "label": ".gitignore",
        "why": "Existing gitignore markers are an evidence pointer only. They are not a vault and not proof of separation.",
    },
    {
        "id": "sacred-rule",
        "path": "docs/RULE-Beta-Construction-Production-Sacred-2026-09-16.md",
        "label": "Sacred Beta/Production rule",
        "why": "The sacred Beta/Production rule is an evidence pointer only. It is not proof that Beta and Production are separated.",
    },
)

GAPS: tuple[str, ...] = (
    "The framework is empty.",
    "An empty framework is not proof of separation.",
    "An empty framework is not a live vault.",
    "Rotation is not invented as current.",
    "Beta and Production are not invented as separated.",
    "Repo checks are evidence pointers only.",
    "No payment is stored.",
    "Cloudflare is not mutated.",
    "Access is not mutated.",
    "No external secret store write.",
    "The completion row is not resolved.",
    "CAP-INTG-07 stays at the ledger value.",
)

HONESTY = {
    "cap": CAP_ID,
    "bound": BOUND,
    "slice": "intg_secrets_env_separation_v1",
    "slice_label": "BUILT",
    "read_only": True,
    "on_disk": False,
    "empty_honest": True,
    "empty_is_separation": False,
    "separation_proved": False,
    "live_vault": False,
    "vault": None,
    "rotation": None,
    "separation": None,
    "current": False,
    "pointer_is_proof": False,
    "checks_are_proof": False,
    "contents_read": False,
    "payment": None,
    "money": None,
    "secret_store_write": False,
    "cloudflare_mutated": False,
    "access_mutated": False,
    "score_changed": False,
    "production": False,
    "alchemist_write": False,
    "wolf_system_write": False,
    "anon_fail_closed": True,
    "owner_read": True,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "invented_proven": False,
    "invented_ready": False,
    "ledger_write": False,
}


class SecretsEnvError(ValueError):
    """Fail closed. Does not invent separation, a live vault, or PROVEN."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def _assert_beta_path(resolved: Path) -> None:
    low = str(resolved).lower()
    if "alchemist" in low:
        raise SecretsEnvError(
            "secrets framework refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise SecretsEnvError(
            "secrets framework refuses a wolf-system path",
            code="not_beta",
        )
    for token in ("1password", "doppler", "secretsmanager", "infisical", "keychain"):
        if token in low:
            raise SecretsEnvError(
                "An external secret store write is refused. This is not a live vault.",
                code="secret_store_refused",
            )
    if "/production" in low or low.endswith("money.sqlite"):
        raise SecretsEnvError(
            "secrets framework refuses a production path",
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
        raise SecretsEnvError(
            "secrets framework refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-INTG-07. Does not write the ledger."""
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
    """Read CR-273f30371bd52c8a. Does not upsert, resolve, or harvest."""
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
    flags["empty_is_separation"] = False
    flags["separation_proved"] = False
    flags["live_vault"] = False
    flags["vault"] = None
    flags["rotation"] = None
    flags["separation"] = None
    flags["current"] = False
    flags["pointer_is_proof"] = False
    flags["checks_are_proof"] = False
    flags["contents_read"] = False
    flags["payment"] = None
    flags["money"] = None
    flags["secret_store_write"] = False
    flags["cloudflare_mutated"] = False
    flags["access_mutated"] = False
    flags["on_disk"] = False
    flags["bound"] = BOUND
    return flags


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "additionalProperties": False,
        "required": ["kind", "subject", "status", "evidence_note"],
        "properties": {
            "kind": {"type": "string", "enum": list(KIND_IDS)},
            "subject": {"type": "string"},
            "status": {"type": "string", "enum": ["NOTED"]},
            "evidence_note": {
                "type": "string",
                "description": "Not accepted. A note would not be proof.",
            },
        },
        "kind_enum": list(KIND_IDS),
        "status_enum": ["NOTED"],
        "writes_accepted": False,
        "payment_property": False,
        "vault_property": False,
        "rotation_property": False,
        "separation_property": False,
        "live_vault_property": False,
        "current_property": False,
        "secret_store_property": False,
        "cloudflare_property": False,
        "access_property": False,
        "pointer_is_proof": False,
    }


def kind_slots() -> list[dict[str, Any]]:
    """Named slots. Each one is empty. Empty is not proof."""
    return [dict(row) for row in EVIDENCE_KINDS]


def evidence_pointers() -> list[dict[str, Any]]:
    """Name existing repo checks. Presence is not proof. Contents are not read."""
    rows: list[dict[str, Any]] = []
    for spec in POINTER_SPECS:
        rel = spec["path"]
        rows.append(
            {
                "id": spec["id"],
                "path": rel,
                "label": spec["label"],
                "role": "evidence_pointer",
                "present": (BETA_ROOT / rel).is_file(),
                "contents_read": False,
                "proves_separation": False,
                "live_vault": False,
                "why": spec["why"],
            }
        )
    return rows


def read_kind(kind_id: str) -> dict[str, Any]:
    token = (kind_id or "").strip().lower()
    for row in EVIDENCE_KINDS:
        if row["kind"] == token:
            return {
                "ok": True,
                "kind": dict(row),
                "empty": True,
                "empty_is_separation": False,
                "separation_proved": False,
                "live_vault": False,
                "vault": None,
                "rotation": None,
                "separation": None,
                "current": False,
                "payment": None,
                "pointer_is_proof": False,
                "contents_read": False,
                "ledger_write": False,
                "cr_resolved": False,
                "honesty": honesty_flags(),
            }
    raise SecretsEnvError("Unknown framework slot.", code="not_found")


def build_register(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Owner read of the skeleton. Does not create a vault file or read secrets."""
    flags = honesty_flags(ledger_path, catalog_db)
    slots = kind_slots()
    pointers = evidence_pointers()
    return {
        "ok": True,
        "cap": CAP_ID,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "schema": schema_document(),
        "empty": True,
        "empty_is_separation": False,
        "recorded_count": 0,
        "separation_proved": False,
        "live_vault": False,
        "vault": None,
        "rotation": None,
        "separation": None,
        "current": False,
        "payment": None,
        "money": None,
        "pointer_is_proof": False,
        "checks_are_proof": False,
        "contents_read": False,
        "secret_store_write": False,
        "cloudflare_mutated": False,
        "access_mutated": False,
        "on_disk": False,
        "kinds": slots,
        "pointers": pointers,
        "rows": [],
        "gaps": list(GAPS),
        "framework_skeleton": "BUILT",
        "ledger_write": False,
        "cr_resolved": flags["cr_resolved"] if flags["cr_state"] == "RESOLVED" else False,
        "honesty": flags,
    }


def refuse_payment(_body: dict | None = None) -> None:
    raise SecretsEnvError(
        "A payment is not stored on this framework. No amount is kept.",
        code="payment_refused",
    )


def refuse_current(_body: dict | None = None) -> None:
    raise SecretsEnvError(
        "A live vault, current rotation, and proved separation are not invented. Empty is not proof of separation.",
        code="current_refused",
    )


def refuse_secret_store(_body: dict | None = None) -> None:
    raise SecretsEnvError(
        "An external secret store write is refused. This is not a live vault.",
        code="secret_store_refused",
    )


def refuse_cloudflare(_body: dict | None = None) -> None:
    raise SecretsEnvError(
        "Cloudflare is not mutated from this framework.",
        code="cloudflare_refused",
    )


def refuse_access(_body: dict | None = None) -> None:
    raise SecretsEnvError(
        "Access is not mutated from this framework.",
        code="access_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise SecretsEnvError(
        "PROVEN is refused. The ceiling label is BUILT unless the ledger is already higher.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise SecretsEnvError(
        "READY is refused. This framework does not mark the capability ready.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise SecretsEnvError(
        "Resolving the completion row is refused. CR-273f30371bd52c8a stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise SecretsEnvError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise SecretsEnvError(
        "The framework stays empty. A filled slot would not be proof of separation.",
        code="slots_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if isinstance(payload, dict):
        for key in payload:
            token = str(key).strip().lower().replace("_", "-")
            if token in {"payment", "payments", "money", "price", "amount", "invoice", "paid"}:
                refuse_payment(payload)
            if token in {
                "vault",
                "live-vault",
                "rotation",
                "rotation-status",
                "separation",
                "separation-status",
                "beta-prod",
                "current",
            }:
                refuse_current(payload)
            if token in {
                "secret",
                "secret-store",
                "secrets",
                "token",
                "password",
                "external",
                "dotenv",
            }:
                refuse_secret_store(payload)
            if token in {"cloudflare", "cf", "zone", "tunnel"}:
                refuse_cloudflare(payload)
            if token in {"access", "cf-access", "zero-trust"}:
                refuse_access(payload)
            if token in {"proven", "prove"}:
                refuse_proven(payload)
            if token == "ready":
                refuse_ready(payload)
            if token in {"resolve", "cr-resolved"}:
                refuse_resolve(payload)
            if token in {"production", "production-mutate"}:
                refuse_production(payload)
            if token in {"fill", "note", "evidence", "evidence-note", "slots-filled"}:
                refuse_fill(payload)
    raise SecretsEnvError(
        "This framework does not store a secret, a payment, or a live vault.",
        code="writes_refused",
    )


def refuse_store(db_path: Path | str) -> None:
    """Refuse a destination. Does not create the file and does not read secrets."""
    resolved = Path(db_path).resolve()
    if resolved == CATALOG_DB.resolve() or resolved.name == "content_library.sqlite":
        raise SecretsEnvError(
            "secrets framework does not write the content catalog",
            code="catalog_refused",
        )
    _assert_beta_path(resolved)
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        if (os.environ.get("WOLF_ALLOW_LIVE_INTG_SECRETS") or "").strip() != "1":
            raise SecretsEnvError(
                "test mode refuses the live secrets framework path",
                code="live_guard",
            )
    raise SecretsEnvError(
        "The framework stays empty. Empty is not proof of separation and not a live vault.",
        code="slots_refused",
    )


def resolve_cr(*_args: Any, **_kwargs: Any) -> None:
    refuse_resolve({})


def mark_proven(*_args: Any, **_kwargs: Any) -> None:
    refuse_proven({})


def mark_current(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def mark_live_vault(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def _present(value: str | None) -> bool:
    return (value or "").strip() != ""


def guard_query(
    *,
    payment: str | None = None,
    money: str | None = None,
    vault: str | None = None,
    live_vault: str | None = None,
    rotation: str | None = None,
    separation: str | None = None,
    current: str | None = None,
    secret: str | None = None,
    secret_store: str | None = None,
    cloudflare: str | None = None,
    access: str | None = None,
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
    if (
        _present(vault)
        or _present(live_vault)
        or _present(rotation)
        or _present(separation)
        or _present(current)
    ):
        refuse_current({})
    if _present(secret) or _present(secret_store):
        refuse_secret_store({})
    if _present(cloudflare):
        refuse_cloudflare({})
    if _present(access):
        refuse_access({})
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
