"""Governance policy loader — versioned config, FAIL CLOSED on any invalid state."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import CONFIG_DIR, GOVERNANCE_AUDIT_PATH, GOVERNANCE_DIR, ensure_dirs

GOVERNANCE_CONFIG_DIR = CONFIG_DIR / "governance"
DEFAULT_POLICY_PATH = GOVERNANCE_CONFIG_DIR / "worker-allocation-policy.json"
SCHEMA_PATH = GOVERNANCE_CONFIG_DIR / "worker-allocation-policy.schema.json"
POLICY_ENV = "WOLF_INTELLIGENCE_GOVERNANCE_POLICY"

ALLOWED_GROK_REASON_CODES = frozenset({
    "BENCHMARK_SELECTED",
    "REQUIRES_GROK_ENVIRONMENT",
    "OTHERS_UNAVAILABLE",
    "EXPLICIT_JUSTIFIED",
})

CAPACITY_STATES = ("NORMAL", "CONSERVE", "RESERVE", "EXHAUSTED")


@dataclass
class PolicyLoad:
    ok: bool
    mode: str  # "ENFORCED" | "FAIL_CLOSED"
    policy: dict[str, Any] | None
    sha256: str
    errors: list[str] = field(default_factory=list)


def _policy_path(path: Path | str | None = None) -> Path:
    if path is not None:
        return Path(path)
    env = os.environ.get(POLICY_ENV, "").strip()
    if env:
        return Path(env).expanduser()
    return DEFAULT_POLICY_PATH


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _validate_schema_node(schema: dict[str, Any], data: Any, path: str, errors: list[str]) -> None:
    if not isinstance(schema, dict):
        return
    if "const" in schema and data != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}, got {data!r}")
        return
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: value {data!r} not in enum {schema['enum']}")
        return
    expected_type = schema.get("type")
    if expected_type:
        actual = _type_name(data)
        if expected_type == "number" and actual not in ("number", "integer"):
            errors.append(f"{path}: expected {expected_type}, got {actual}")
            return
        elif expected_type != "number" and actual != expected_type:
            errors.append(f"{path}: expected {expected_type}, got {actual}")
            return
    if expected_type == "object":
        if not isinstance(data, dict):
            return
        required = schema.get("required") or []
        for key in required:
            if key not in data:
                errors.append(f"{path}: missing required field '{key}'")
        props = schema.get("properties") or {}
        addl = schema.get("additionalProperties", True)
        for key, value in data.items():
            if key in props:
                _validate_schema_node(props[key], value, f"{path}.{key}", errors)
            elif addl is False:
                errors.append(f"{path}: unexpected field '{key}'")
    if expected_type == "array" and isinstance(data, list):
        items = schema.get("items")
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if min_items is not None and len(data) < min_items:
            errors.append(f"{path}: array length {len(data)} < minItems {min_items}")
        if max_items is not None and len(data) > max_items:
            errors.append(f"{path}: array length {len(data)} > maxItems {max_items}")
        if items:
            for i, item in enumerate(data):
                _validate_schema_node(items, item, f"{path}[{i}]", errors)
    if expected_type in ("integer", "number") and isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{path}: {data} < minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{path}: {data} > maximum {schema['maximum']}")
    if expected_type == "string" and isinstance(data, str):
        min_len = schema.get("minLength")
        if min_len is not None and len(data) < min_len:
            errors.append(f"{path}: string length {len(data)} < minLength {min_len}")


def _resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        return {}
    parts = ref[2:].split("/")
    node: Any = schema
    for part in parts:
        if isinstance(node, dict):
            node = node.get(part, {})
    return node if isinstance(node, dict) else {}


def validate_policy_schema(policy: dict[str, Any], schema: dict[str, Any] | None = None) -> list[str]:
    """Validate policy against the JSON-Schema-style document. Returns error strings."""
    errors: list[str] = []
    if schema is None:
        try:
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return [f"schema unreadable: {exc}"]
    props = schema.get("properties") or {}
    required = schema.get("required") or []
    for key in required:
        if key not in policy:
            errors.append(f"root: missing required field '{key}'")
    for key, value in policy.items():
        if key in props:
            node_schema = props[key]
            if "$ref" in node_schema:
                node_schema = _resolve_ref(schema, node_schema["$ref"])
            _validate_schema_node(node_schema, value, f"root.{key}", errors)
    return errors


def validate_policy_invariants(policy: dict[str, Any]) -> list[str]:
    """Pin invariants beyond JSON Schema — monotonic thresholds, reason codes, etc."""
    errors: list[str] = []
    if policy.get("metered_fallback") != "NEVER":
        errors.append("invariant: metered_fallback must be NEVER")
    if policy.get("paid_spend") != "OFF":
        errors.append("invariant: paid_spend must be OFF")
    if policy.get("on_demand_policy") != "NEVER_ENABLE":
        errors.append("invariant: on_demand_policy must be NEVER_ENABLE")
    codes = set(policy.get("grok_reason_codes") or [])
    if codes != ALLOWED_GROK_REASON_CODES:
        errors.append(f"invariant: grok_reason_codes must be exactly {sorted(ALLOWED_GROK_REASON_CODES)}")
    protected = policy.get("protected_classes") or []
    if not protected:
        errors.append("invariant: protected_classes must be non-empty")
    thresholds_root = policy.get("capacity_thresholds") or {}
    for name, th in thresholds_root.items():
        if not isinstance(th, dict):
            continue
        c, r, e = th.get("conserve_at"), th.get("reserve_at"), th.get("exhausted_at")
        if not all(isinstance(x, (int, float)) for x in (c, r, e)):
            errors.append(f"invariant: capacity_thresholds.{name} values must be numbers")
            continue
        if not (0 <= c < r < e <= 100):
            errors.append(
                f"invariant: capacity_thresholds.{name} must be monotonic 0 <= conserve < reserve < exhausted <= 100"
            )
    grok_reserve = policy.get("grok_reserve") or {}
    gr_classes = grok_reserve.get("protected_classes") or []
    if not gr_classes:
        errors.append("invariant: grok_reserve.protected_classes must be non-empty")
    imb = policy.get("imbalance") or {}
    share = imb.get("max_grok_share_delegatable")
    if share is not None and not (0 <= share <= 1):
        errors.append("invariant: imbalance.max_grok_share_delegatable must be in [0, 1]")
    return errors


def append_audit_event(event_type: str, payload: dict[str, Any]) -> None:
    ensure_dirs()
    GOVERNANCE_DIR.mkdir(parents=True, exist_ok=True)
    rec = {"event": event_type, **payload}
    with GOVERNANCE_AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


def load_policy(path: Path | str | None = None) -> PolicyLoad:
    """Load and validate governance policy. FAIL_CLOSED on any problem."""
    p = _policy_path(path)
    try:
        raw = p.read_bytes()
    except OSError as exc:
        pl = PolicyLoad(ok=False, mode="FAIL_CLOSED", policy=None, sha256="", errors=[f"unreadable: {exc}"])
        append_audit_event("GOVERNANCE_POLICY_FAIL_CLOSED", {"path": str(p), "errors": pl.errors})
        return pl
    sha = _sha256_bytes(raw)
    try:
        policy = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        pl = PolicyLoad(ok=False, mode="FAIL_CLOSED", policy=None, sha256=sha, errors=[f"invalid JSON: {exc}"])
        append_audit_event("GOVERNANCE_POLICY_FAIL_CLOSED", {"path": str(p), "sha256": sha, "errors": pl.errors})
        return pl
    if not isinstance(policy, dict):
        pl = PolicyLoad(ok=False, mode="FAIL_CLOSED", policy=None, sha256=sha, errors=["policy root must be object"])
        append_audit_event("GOVERNANCE_POLICY_FAIL_CLOSED", {"path": str(p), "sha256": sha, "errors": pl.errors})
        return pl
    errors = validate_policy_schema(policy) + validate_policy_invariants(policy)
    if errors:
        pl = PolicyLoad(ok=False, mode="FAIL_CLOSED", policy=None, sha256=sha, errors=errors)
        append_audit_event("GOVERNANCE_POLICY_FAIL_CLOSED", {"path": str(p), "sha256": sha, "errors": errors})
        return pl
    return PolicyLoad(ok=True, mode="ENFORCED", policy=policy, sha256=sha, errors=[])


def metered_permitted(policy_load: PolicyLoad | None = None) -> bool:
    """Paid/metered spend is never permitted under governance."""
    pl = policy_load or load_policy()
    if pl.mode == "FAIL_CLOSED":
        return False
    policy = pl.policy or {}
    return policy.get("paid_spend") == "ON" and policy.get("metered_fallback") == "ALLOWED"


def grok_worker_id(policy: dict[str, Any]) -> str:
    return policy.get("grok_worker_id", "grok_bot_sub")


def is_protected_class(task_class: str, policy: dict[str, Any]) -> bool:
    return task_class in (policy.get("protected_classes") or [])


def task_family(task_class: str, policy: dict[str, Any]) -> str:
    families = policy.get("task_families") or {}
    for name, classes in families.items():
        if task_class in (classes or []):
            return name
    return "unknown"
