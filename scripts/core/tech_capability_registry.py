#!/usr/bin/env python3
"""Owner Tech & Capability Registry (Beta, read-only) — CAP-INTG-06 slice.

Decision served: 2026-09-19 PICK, Tech & Capability Registry on Beta only
(docs/deliveries/GROK-PLAN-INTG-TECH-CAPABILITY-REGISTRY-2026-09-19.md).

Seeds capabilities from the Model C catalog, ledger maturity from the
baseline file, and connector/technology health from local Integration Health
reads or an explicit not-probed note. Does not write the ledger, the
completion register, Alchemist, or any external system.

Honesty is bound to CR-44ffb6a57469ff25. CAP-INTG-06 maturity is the ledger
state. The ceiling is BUILT unless the ledger is already PROVEN or READY.
This module never invents PROVEN and never emits a GREEN health token.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_MD = BETA_ROOT / "docs" / "MODEL-C-CAPABILITY-CATALOG.md"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

CR_ID = "CR-44ffb6a57469ff25"
CAP_ID = "CAP-INTG-06"
EXPECTED_CAPS = 77

MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})
HIGHER_THAN_BUILT = frozenset({"PROVEN", "READY"})
HEALTH = ("UNKNOWN", "NOT_CONFIGURED", "READ_OK", "DEGRADED", "ERROR")
_HEALTH = frozenset(HEALTH)
KINDS = ("capability", "connector", "technology")
OWNERSHIP = frozenset({"OWN", "INTEGRATE", "OBSERVE", "DERIVE"})

_BANNED_HEALTH = frozenset({"GREEN", "HEALTHY", "OK", "UP", "LIVE"})
_REPLACE = "No replace decision is recorded. This registry does not invent a replacement."

_EXIT_BY_OWNERSHIP = {
    "OWN": "Wolf owns this workflow. No exit decision is recorded in this registry.",
    "INTEGRATE": (
        "An external system owns the canonical facts. Exit means Wolf stops "
        "consuming them. Wolf does not take over that system."
    ),
    "OBSERVE": (
        "Wolf observes and does not control the source. Exit means stop observing. "
        "No replace is recorded."
    ),
    "DERIVE": (
        "Wolf calculates a view from other sources. Exit means stop publishing "
        "the view. The source system stays."
    ),
}

# Known connectors and technologies. Health is filled from a local read or
# left NOT_CONFIGURED. None of these notes name a replacement vendor.
_SYSTEMS: tuple[dict[str, str], ...] = (
    {
        "slug": "YANOLJA",
        "name": "Yanolja",
        "cap_id": "CAP-INTG-01",
        "health_from": "CAP-INTG-01",
        "exit_note": (
            "Exit is to stop taking reservation facts from Yanolja. "
            "Yanolja keeps PMS truth."
        ),
    },
    {
        "slug": "ESB",
        "name": "ESB",
        "cap_id": "CAP-INTG-02",
        "health_from": "CAP-INTG-02",
        "exit_note": (
            "Exit is to stop taking F&B sales and inventory facts from ESB. "
            "ESB keeps transactional truth."
        ),
    },
    {
        "slug": "GOOGLE-WORKSPACE",
        "name": "Google Workspace",
        "cap_id": "CAP-INTG-03",
        "health_from": "CAP-INTG-03",
        "exit_note": (
            "Exit is to stop authorised mail, calendar, and document reads. "
            "This registry does not probe Gmail, Drive, or Calendar."
        ),
    },
    {
        "slug": "BANK",
        "name": "Bank statement file import",
        "cap_id": "CAP-INTG-04",
        "health_from": "CAP-INTG-04",
        "exit_note": (
            "Exit is to stop statement-file ingest. No bank API is claimed. "
            "No import was run by this registry."
        ),
    },
    {
        "slug": "METRICOOL",
        "name": "Metricool",
        "cap_id": "CAP-INTG-05",
        "health_from": "CAP-INTG-05",
        "exit_note": (
            "Exit is to stop social-performance reads. Metricool keeps platform "
            "analytics. This registry does not call Metricool."
        ),
    },
    {
        "slug": "KLAVIYO",
        "name": "Klaviyo",
        "cap_id": "CAP-CRM-04",
        "health_from": "",
        "exit_note": (
            "Exit is to stop the Habitat read path. This registry did not call "
            "Klaviyo and did not insert profiles."
        ),
    },
    {
        "slug": "ACTIVECAMPAIGN",
        "name": "ActiveCampaign",
        "cap_id": "CAP-CRM-04",
        "health_from": "",
        "exit_note": (
            "No ActiveCampaign reader was called. ActiveCampaign is not Klaviyo. "
            "Exit is not applicable until a reader exists."
        ),
    },
)

_TECH_ONLY: tuple[dict[str, str], ...] = (
    {
        "slug": "CLOUDFLARE-ACCESS",
        "name": "Cloudflare Access",
        "cap_id": "CAP-MSC-02",
        "health_from": "cf_access",
        "exit_note": (
            "Exit is not a seat change. This registry does not edit Access "
            "and does not fetch JWKS."
        ),
    },
    {
        "slug": "ALCHEMIST",
        "name": "Alchemist",
        "cap_id": "",
        "health_from": "alchemist",
        "exit_note": "This registry does not write Alchemist. Exit is not a write.",
    },
)

_NOT_PROBED = (
    "Not probed by this registry. Missing local health is NOT_CONFIGURED, "
    "not a healthy connector."
)

_DOMAIN_RE = re.compile(r"^### (D-[A-Z]+) — (.+?) \(\d+\)\s*$")
_CAP_RE = re.compile(r"^\| (CAP-[A-Z0-9]+-\d+) \|")

HONESTY = {
    "cap": CAP_ID,
    "slice": "tech_capability_registry",
    "read_only": True,
    "external_writes": False,
    "production": False,
    "alchemist_write": False,
    "network_probes": False,
    "green_invented": False,
    "fake_connector_status": False,
    "score_changed": False,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "anon_fail_closed": True,
}


class RegistryError(ValueError):
    """Fail closed. Does not invent a row, a status, or a maturity."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def refuse_external_write(_body: dict | None = None) -> None:
    """Every mutation path ends here. Nothing is written."""
    raise RegistryError(
        "Tech registry is read-only. External writes are refused.",
        code="writes_refused",
    )


def _guard_path(path: Path) -> None:
    text = str(path)
    low = text.lower()
    if "alchemist" in low:
        raise RegistryError(
            "Tech registry refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low or "/production" in low or text.endswith("money.sqlite"):
        raise RegistryError(
            "Tech registry refuses a production path",
            code="not_beta",
        )


def _clean(text: str) -> str:
    out = text or ""
    for bad in ("GREEN", "Green", "HEALTHY", "Healthy"):
        out = out.replace(bad, "refused-token")
    return out


def _maturity(value: str) -> str:
    token = (value or "").strip().upper()
    if token in MATURITY:
        return token
    return "UNKNOWN"


def _health(value: str) -> str:
    token = (value or "").strip().upper()
    if token in _BANNED_HEALTH:
        return "ERROR"
    if token in _HEALTH:
        return token
    return "ERROR"


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-INTG-06 from the ledger. Does not write it."""
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


def load_cr_binding() -> dict[str, Any]:
    """Read CR-44ffb6a57469ff25. Does not upsert, resolve, or harvest."""
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
    if not CATALOG_DB.is_file():
        return out
    uri = CATALOG_DB.resolve().as_uri() + "?mode=ro"
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


def honesty_flags(ledger_path: Path | str | None = None) -> dict[str, Any]:
    state = ledger_cap_state(ledger_path)
    ceiling = state if state in HIGHER_THAN_BUILT else "BUILT"
    flags = dict(HONESTY)
    flags.update(load_cr_binding())
    flags["ledger_maturity"] = state
    flags["maturity"] = state
    flags["maturity_ceiling"] = ceiling
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["external_writes"] = False
    flags["green_invented"] = False
    return flags


def parse_catalog(catalog_path: Path | str | None = None) -> list[dict[str, str]]:
    """Read capability rows from the canonical catalog. Does not invent ids."""
    path = Path(catalog_path) if catalog_path else CATALOG_MD
    _guard_path(path)
    if not path.is_file():
        raise RegistryError("Model C catalog is missing", code="catalog_missing")
    domain = ""
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        header = _DOMAIN_RE.match(line)
        if header:
            domain = f"{header.group(1)} — {header.group(2).strip()}"
            continue
        if not _CAP_RE.match(line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        cap_id, name, ownership, scope, intent = cells[:5]
        if cap_id in seen:
            continue
        seen.add(cap_id)
        rows.append(
            {
                "id": cap_id,
                "name": name,
                "ownership": ownership if ownership in OWNERSHIP else ownership,
                "scope": scope,
                "intent": intent,
                "domain": domain,
            }
        )
    if len(rows) != EXPECTED_CAPS:
        raise RegistryError(
            f"catalog seed count {len(rows)} is not {EXPECTED_CAPS}",
            code="catalog_incomplete",
        )
    return rows


def _load_ledger(ledger_path: Path | str | None) -> dict[str, str]:
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    _guard_path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str] = {}
    for cap_id, row in data.items():
        if isinstance(row, list) and row:
            out[str(cap_id)] = _maturity(str(row[0]))
        else:
            out[str(cap_id)] = "UNKNOWN"
    return out


def _health_index(report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not report:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in report.get("connectors") or []:
        if isinstance(row, dict) and row.get("cap_id"):
            out[str(row["cap_id"])] = row
    for row in report.get("sources") or []:
        if isinstance(row, dict) and row.get("source_id"):
            out[str(row["source_id"])] = row
    return out


def _status_from_health(row: dict[str, Any] | None, *, probed: bool) -> tuple[str, str, str]:
    if not probed:
        return "NOT_CONFIGURED", "not_probed", _NOT_PROBED
    if row is None:
        return "NOT_CONFIGURED", "integration_health", _NOT_PROBED
    status = _health(str(row.get("status") or ""))
    evidence = _clean(str(row.get("evidence") or ""))
    if status == "ERROR" and str(row.get("status") or "").strip().upper() in _BANNED_HEALTH:
        evidence = "Connector status token refused. " + evidence
    source = "integration_health"
    return status, source, evidence or _NOT_PROBED


def _capability_row(seed: dict[str, str], maturity: str) -> dict[str, Any]:
    ownership = seed["ownership"]
    exit_note = _EXIT_BY_OWNERSHIP.get(
        ownership,
        "Ownership was not a catalog enum. No exit or replace is invented.",
    )
    return {
        "id": seed["id"],
        "kind": "capability",
        "name": seed["name"],
        "domain": seed["domain"],
        "ownership": ownership,
        "scope": seed["scope"],
        "cap_id": seed["id"],
        "status": maturity,
        "status_kind": "maturity",
        "intent": seed["intent"],
        "exit_note": exit_note,
        "replace_note": _REPLACE,
        "evidence": "Ledger read only. Maturity was not written by this registry.",
        "source": "model_c_catalog",
        "external_writes": False,
        "promotes_ledger": False,
    }


def _system_row(
    spec: dict[str, str],
    *,
    kind: str,
    health: dict[str, dict[str, Any]],
    ledger: dict[str, str],
    health_attached: bool,
) -> dict[str, Any]:
    key = spec["health_from"]
    probed = bool(key) and health_attached
    status, source, evidence = _status_from_health(health.get(key) if key else None, probed=probed)
    cap_id = spec["cap_id"]
    prefix = "CONN" if kind == "connector" else "TECH"
    row: dict[str, Any] = {
        "id": f"{prefix}-{spec['slug']}",
        "kind": kind,
        "name": spec["name"],
        "cap_id": cap_id or None,
        "status": status,
        "status_kind": "health",
        "exit_note": spec["exit_note"],
        "replace_note": _REPLACE,
        "evidence": evidence,
        "source": source,
        "external_writes": False,
        "promotes_ledger": False,
    }
    if cap_id:
        row["ledger_maturity"] = ledger.get(cap_id, "UNKNOWN")
    return row


def _load_health(
    health_report: dict[str, Any] | None,
    *,
    attach_health: bool,
    esb_path: Path | str | None,
    alchemist_path: Path | str | None,
    env_root: Path | str | None,
) -> dict[str, Any] | None:
    if health_report is not None:
        if not isinstance(health_report, dict):
            raise RegistryError("health report must be a dict", code="invalid")
        return health_report
    if not attach_health:
        return None
    for candidate in (esb_path, alchemist_path, env_root):
        if candidate is not None:
            _guard_path(Path(candidate))
    from core import integration_health as health

    return health.build_report(
        esb_path=esb_path,
        alchemist_path=alchemist_path,
        env_root=env_root,
    )


def build_registry(
    *,
    catalog_path: Path | str | None = None,
    ledger_path: Path | str | None = None,
    esb_path: Path | str | None = None,
    alchemist_path: Path | str | None = None,
    env_root: Path | str | None = None,
    health_report: dict[str, Any] | None = None,
    attach_health: bool = True,
    kind: str | None = None,
) -> dict[str, Any]:
    """Owner read. Seeds catalog caps plus known connectors. Writes nothing."""
    if kind is not None and kind not in KINDS:
        raise RegistryError("unknown registry kind", code="invalid_kind")
    seeds = parse_catalog(catalog_path)
    ledger = _load_ledger(ledger_path)
    report = _load_health(
        health_report,
        attach_health=attach_health,
        esb_path=esb_path,
        alchemist_path=alchemist_path,
        env_root=env_root,
    )
    health = _health_index(report)
    entries: list[dict[str, Any]] = []
    for seed in seeds:
        entries.append(_capability_row(seed, ledger.get(seed["id"], "UNKNOWN")))
    attached = report is not None
    for spec in _SYSTEMS:
        entries.append(
            _system_row(spec, kind="connector", health=health, ledger=ledger, health_attached=attached)
        )
        entries.append(
            _system_row(spec, kind="technology", health=health, ledger=ledger, health_attached=attached)
        )
    for spec in _TECH_ONLY:
        entries.append(
            _system_row(spec, kind="technology", health=health, ledger=ledger, health_attached=attached)
        )
    if kind is not None:
        entries = [row for row in entries if row["kind"] == kind]
    flags = honesty_flags(ledger_path)
    counts = {name: sum(1 for row in entries if row["kind"] == name) for name in KINDS}
    return {
        "ok": True,
        "bound": "beta-tech-capability-registry",
        "cap": CAP_ID,
        "entries": entries,
        "counts": counts,
        "catalog_seed_count": EXPECTED_CAPS,
        "vocabulary_maturity": sorted(MATURITY | {"UNKNOWN"}),
        "vocabulary_health": list(HEALTH),
        "external_writes": False,
        "ledger_write": False,
        "network_probes": False,
        "green_invented": False,
        "seeded_from": [
            "model_c_catalog",
            "known_connectors",
            "ledger_read",
            "integration_health" if report is not None else "health_not_attached",
        ],
        "honesty": flags,
    }


def read_entry(entry_id: str, **kwargs: Any) -> dict[str, Any]:
    want = (entry_id or "").strip()
    if not want or "/" in want or want.upper() in _BANNED_HEALTH:
        raise RegistryError("registry id refused", code="invalid")
    report = build_registry(**kwargs)
    for row in report["entries"]:
        if row["id"] == want:
            return {
                "ok": True,
                "entry": row,
                "bound": report["bound"],
                "external_writes": False,
                "ledger_write": False,
                "honesty": report["honesty"],
            }
    raise RegistryError("not in registry", code="not_found")
