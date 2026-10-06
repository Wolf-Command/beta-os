"""Governance policy loader — versioned config, FAIL CLOSED on any invalid state."""
from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Path used in fail_closed_policy defaults and structure bounds.

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

CONSERVE_ALLOWED_GROK_CODES = frozenset({"OTHERS_UNAVAILABLE", "EXPLICIT_JUSTIFIED"})

CAPACITY_STATES = ("NORMAL", "CONSERVE", "RESERVE", "EXHAUSTED")
STATE_RANK = {s: i for i, s in enumerate(CAPACITY_STATES)}
GROK_WORKER_ID = "grok_bot_sub"

HARDCODED_PROTECTED_CLASSES = frozenset({
    "owner_conversation",
    "orchestration",
    "exception_handling",
    "recovery_communication",
    "critical_synthesis",
})

HARDCODED_GROK_THRESHOLDS = {
    "conserve_at": 30,
    "reserve_at": 60,
    "exhausted_at": 95,
}

HARDCODED_FAIL_CLOSED_ORDER = (
    "claude_pro_sub",
    "codex_sub",
    "cursor_sub",
)

HARDCODED_TASK_FAMILIES: dict[str, list[str]] = {
    "engineering": ["coding", "debugging", "refactor", "testing"],
    "reasoning_review": [
        "reasoning_planning", "review", "red_team", "security", "analysis", "research",
        "finance", "large_context", "structured_extraction", "ux_product", "vision_document",
    ],
    "protected": list(HARDCODED_PROTECTED_CLASSES),
    "operations": ["state_update", "evidence_collection", "recovery"],
}

HARDCODED_VELOCITY: dict[str, Any] = {
    "window_hours": 168,
    "min_points": 2,
    "min_span_minutes": 10,
    "reserve_if_exhaustion_within_hours": 48,
    "assumed_reset_hours_if_unknown": 168,
}

HARDCODED_GROK_CONSERVE_CONDUCT: dict[str, Any] = {
    "no_grok_when_other_qualified": True,
    "polling": "FORBIDDEN",
    "completion_events": "COMPACT",
    "vesper_reserved_for": ["final_gate"],
}

HARDCODED_BENCHMARK_CLASS_MAP: dict[str, str] = {
    "review": "reasoning_planning",
    "analysis": "reasoning_planning",
    "research": "reasoning_planning",
    "red_team": "security",
    "refactor": "coding",
    "testing": "coding",
    "state_update": "structured_extraction",
    "evidence_collection": "structured_extraction",
    "recovery": "structured_extraction",
}

MIN_JUSTIFICATION_LENGTH = 20
MAX_OBSERVATION_AGE_HOURS = 72
MAX_POLICY_BYTES = 256 * 1024
MAX_POLICY_DEPTH = 32
MAX_POLICY_ARRAY_LEN = 1000
MAX_POLICY_NODES = 50_000
MAX_VALIDATOR_ERRORS = 50


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


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate JSON key: {key}")
        seen.add(key)
        out[key] = value
    return out


def _resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        return {}
    parts = ref[2:].split("/")
    node: Any = schema
    for part in parts:
        if isinstance(node, dict):
            node = node.get(part, {})
        else:
            return {}
    return node if isinstance(node, dict) else {}


def _deref_schema(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in schema:
        resolved = _resolve_ref(root, schema["$ref"])
        return _deref_schema(resolved, root) if resolved else {}
    return schema


def _validate_schema_node(
    schema: dict[str, Any],
    data: Any,
    path: str,
    errors: list[str],
    root: dict[str, Any],
) -> None:
    if not isinstance(schema, dict):
        return
    schema = _deref_schema(schema, root)
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
        if expected_type != "number" and actual != expected_type:
            errors.append(f"{path}: expected {expected_type}, got {actual}")
            return
    if expected_type in ("integer", "number") and isinstance(data, (int, float)) and not isinstance(data, bool):
        if not math.isfinite(data):
            errors.append(f"{path}: non-finite number {data!r}")
            return
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{path}: {data} < minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{path}: {data} > maximum {schema['maximum']}")
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
                child = _deref_schema(props[key], root)
                _validate_schema_node(child, value, f"{path}.{key}", errors, root)
            elif addl is False:
                errors.append(f"{path}: unexpected field '{key}'")
            elif isinstance(addl, dict):
                _validate_schema_node(addl, value, f"{path}.{key}", errors, root)
    if expected_type == "array" and isinstance(data, list):
        items = schema.get("items")
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if min_items is not None and len(data) < min_items:
            errors.append(f"{path}: array length {len(data)} < minItems {min_items}")
        if max_items is not None and len(data) > max_items:
            errors.append(f"{path}: array length {len(data)} > maxItems {max_items}")
        if schema.get("uniqueItems") and len(data) != len(set(json.dumps(x, sort_keys=True) for x in data)):
            errors.append(f"{path}: array items must be unique")
        if items:
            item_schema = _deref_schema(items, root) if isinstance(items, dict) else items
            for i, item in enumerate(data):
                _validate_schema_node(item_schema, item, f"{path}[{i}]", errors, root)
    if expected_type == "string" and isinstance(data, str):
        min_len = schema.get("minLength")
        if min_len is not None and len(data) < min_len:
            errors.append(f"{path}: string length {len(data)} < minLength {min_len}")


def validate_policy_schema(policy: dict[str, Any], schema: dict[str, Any] | None = None) -> list[str]:
    """Validate policy against the JSON-Schema-style document. Returns error strings."""
    errors: list[str] = []
    if schema is None:
        try:
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return [f"schema unreadable: {exc}"]
    if not isinstance(schema, dict) or schema.get("type") != "object":
        return ["schema invalid: root must be object with type object"]
    if not schema.get("properties"):
        return ["schema invalid: missing properties"]
    props = schema.get("properties") or {}
    required = schema.get("required") or []
    for key in required:
        if key not in policy:
            errors.append(f"root: missing required field '{key}'")
    for key, value in policy.items():
        if key in props:
            node_schema = _deref_schema(props[key], schema)
            _validate_schema_node(node_schema, value, f"root.{key}", errors, schema)
    return errors


def _known_benchmark_classes() -> set[str]:
    routing_path = CONFIG_DIR / "routing-policy-real.json"
    try:
        routing = json.loads(routing_path.read_text(encoding="utf-8"))
        return set((routing.get("task_classes") or {}).keys())
    except (OSError, json.JSONDecodeError):
        return set()


def _validate_unknown_state_value(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or value not in CAPACITY_STATES:
        errors.append(f"invariant: {path} must be a capacity state")
        return
    if STATE_RANK.get(value, 0) < STATE_RANK["CONSERVE"]:
        errors.append(f"invariant: {path} must be CONSERVE or stricter, got {value!r}")


def _glob_literal_prefix(pattern: str) -> str:
    for i, ch in enumerate(pattern):
        if ch in "*?[":
            return pattern[:i]
    return pattern


def _home_relative_literal_prefix(pattern: str) -> str | None:
    lit = _glob_literal_prefix(os.path.expanduser(str(pattern)))
    home = str(Path.home())
    if lit in ("~", "/", home, f"{home}/"):
        return None
    if lit.startswith(home + "/"):
        return lit[len(home) + 1 :]
    if lit.startswith("~/"):
        return lit[2:]
    return None


def _allowed_glob_prefixes(roots: list[str]) -> list[str]:
    prefixes: list[str] = []
    home = str(Path.home())
    for root in roots:
        lit = _glob_literal_prefix(os.path.expanduser(str(root)))
        if lit.startswith(home + "/"):
            prefixes.append(lit[len(home) + 1 :])
        elif lit.startswith("~/"):
            prefixes.append(lit[2:])
    return prefixes


def _scope_glob_widens_scope(pattern: str, allowed_roots: list[str]) -> bool:
    pat = os.path.expanduser(str(pattern))
    home = str(Path.home())
    if pat in ("~", "/", home, str(Path("/"))):
        return True
    if pat in ("~/*", "/*", f"{home}/*", "/Users/*", "/home/*"):
        return True
    if pat.endswith("/*") and pat[:-2] in (home, "/"):
        return True
    rel = _home_relative_literal_prefix(pattern)
    if rel is None:
        return True
    prefixes = _allowed_glob_prefixes(allowed_roots)
    if not prefixes:
        return True
    return not any(rel.startswith(p) for p in prefixes)


def validate_hardcoded_safety_invariants(policy: dict[str, Any]) -> list[str]:
    """Hardcoded safety invariants independent of schema file."""
    errors: list[str] = []
    min_len = policy.get("grok_justification_min_length")
    if not isinstance(min_len, int) or isinstance(min_len, bool) or min_len < MIN_JUSTIFICATION_LENGTH:
        errors.append(f"invariant: grok_justification_min_length must be >= {MIN_JUSTIFICATION_LENGTH}")
    floors = policy.get("quality_floors") or {}
    default_floor = floors.get("default")
    if not _is_finite_number(default_floor) or not (0 <= default_floor <= 1):
        errors.append("invariant: quality_floors.default must be finite in [0, 1]")
    for tc, floor in (floors.get("by_task_class") or {}).items():
        if not _is_finite_number(floor) or not (0 <= floor <= 1):
            errors.append(f"invariant: quality_floors.by_task_class.{tc} must be finite in [0, 1]")
    decay_cfg = policy.get("capacity_decay") or {}
    decay_rate = decay_cfg.get("decay_pct_per_hour")
    if not _is_finite_number(decay_rate) or decay_rate <= 0:
        errors.append("invariant: capacity_decay.decay_pct_per_hour must be > 0")
    max_age = decay_cfg.get("max_observation_age_hours")
    if not _is_finite_number(max_age) or max_age <= 0 or max_age > MAX_OBSERVATION_AGE_HOURS:
        errors.append(f"invariant: capacity_decay.max_observation_age_hours must be in (0, {MAX_OBSERVATION_AGE_HOURS}]")
    unknown_cfg = decay_cfg.get("unknown_state") or {}
    if isinstance(unknown_cfg, dict):
        for key, val in unknown_cfg.items():
            _validate_unknown_state_value(val, f"capacity_decay.unknown_state.{key}", errors)
    delta = policy.get("tie_band_quality_delta")
    if delta is not None and (not _is_finite_number(delta) or not (0 <= delta <= 1)):
        errors.append("invariant: tie_band_quality_delta must be finite in [0, 1]")
    scope = policy.get("worker_execution_scope") or {}
    if isinstance(scope, dict):
        hardcoded = fail_closed_policy().get("worker_execution_scope") or {}

        def _scope_path(value: Any) -> Path:
            return Path(os.path.expanduser(str(value))).resolve()

        for key in ("isolated_sandbox_root", "zdotdir_empty"):
            val = scope.get(key)
            expected = hardcoded.get(key)
            if val is None or expected is None:
                continue
            if _scope_path(val) != _scope_path(expected):
                errors.append(f"invariant: worker_execution_scope.{key} is pinned")
        globs = scope.get("allowed_workspace_globs")
        if isinstance(globs, list):
            allowed_roots = list(hardcoded.get("allowed_workspace_globs") or [])
            for pattern in globs:
                if _scope_glob_widens_scope(pattern, allowed_roots):
                    errors.append(
                        "invariant: worker_execution_scope.allowed_workspace_globs cannot widen scope"
                    )
                    break
        denied = scope.get("denied_paths") or []
        beta = str(Path.home() / "beta-os")
        if beta not in [str(Path(os.path.expanduser(str(p)))) for p in denied]:
            errors.append("invariant: worker_execution_scope.denied_paths must include beta-os")
    return errors


def validate_policy_invariants(policy: dict[str, Any]) -> list[str]:
    """Pin invariants beyond JSON Schema — monotonic thresholds, reason codes, etc."""
    from . import worker_registry

    errors: list[str] = []
    if policy.get("metered_fallback") != "NEVER":
        errors.append("invariant: metered_fallback must be NEVER")
    if policy.get("paid_spend") != "OFF":
        errors.append("invariant: paid_spend must be OFF")
    if policy.get("on_demand_policy") != "NEVER_ENABLE":
        errors.append("invariant: on_demand_policy must be NEVER_ENABLE")
    if policy.get("grok_worker_id") != GROK_WORKER_ID:
        errors.append(f"invariant: grok_worker_id must be {GROK_WORKER_ID!r}")
    codes = set(policy.get("grok_reason_codes") or [])
    if codes != ALLOWED_GROK_REASON_CODES:
        errors.append(f"invariant: grok_reason_codes must be exactly {sorted(ALLOWED_GROK_REASON_CODES)}")
    protected = set(policy.get("protected_classes") or [])
    if protected != HARDCODED_PROTECTED_CLASSES:
        errors.append(
            f"invariant: protected_classes must be exactly {sorted(HARDCODED_PROTECTED_CLASSES)}"
        )
    families = policy.get("task_families") or {}
    if not isinstance(families, dict):
        errors.append("invariant: task_families must be object")
        families = {}
    family_protected = set(families.get("protected") or [])
    grok_reserve = policy.get("grok_reserve") or {}
    if not isinstance(grok_reserve, dict):
        errors.append("invariant: grok_reserve must be object")
        grok_reserve = {}
    gr_classes = set(grok_reserve.get("protected_classes") or [])
    if gr_classes != HARDCODED_PROTECTED_CLASSES:
        errors.append(
            f"invariant: grok_reserve.protected_classes must be exactly {sorted(HARDCODED_PROTECTED_CLASSES)}"
        )
    if family_protected != HARDCODED_PROTECTED_CLASSES:
        errors.append(
            f"invariant: task_families.protected must be exactly {sorted(HARDCODED_PROTECTED_CLASSES)}"
        )
    for fam_name in ("engineering", "reasoning_review", "operations"):
        fam_classes = set(families.get(fam_name) or [])
        overlap = protected & fam_classes
        if overlap:
            errors.append(
                f"invariant: protected_classes must be disjoint from task_families.{fam_name}; "
                f"overlap: {sorted(overlap)}"
            )
    allowed_by_state = grok_reserve.get("allowed_reason_codes_by_state") or {}
    if not isinstance(allowed_by_state, dict):
        errors.append("invariant: allowed_reason_codes_by_state must be object")
        allowed_by_state = {}
    state_order = ["NORMAL", "CONSERVE", "RESERVE", "EXHAUSTED"]
    prev_codes: set[str] | None = None
    for st in state_order:
        codes_st = set(allowed_by_state.get(st) or [])
        if prev_codes is not None and not (codes_st <= prev_codes):
            errors.append(
                f"invariant: allowed_reason_codes_by_state must be monotonic non-increasing "
                f"({st} not subset of prior state)"
            )
        prev_codes = codes_st
    if allowed_by_state.get("RESERVE"):
        errors.append("invariant: RESERVE allowed_reason_codes must be empty")
    if allowed_by_state.get("EXHAUSTED"):
        errors.append("invariant: EXHAUSTED allowed_reason_codes must be empty")
    conserve_codes = set(allowed_by_state.get("CONSERVE") or [])
    if conserve_codes - CONSERVE_ALLOWED_GROK_CODES:
        errors.append(
            f"invariant: CONSERVE allowed codes must be subset of {sorted(CONSERVE_ALLOWED_GROK_CODES)}"
        )
    if "BENCHMARK_SELECTED" in conserve_codes:
        errors.append("invariant: CONSERVE must not contain BENCHMARK_SELECTED")
    thresholds_root = policy.get("capacity_thresholds") or {}
    if not isinstance(thresholds_root, dict):
        errors.append("invariant: capacity_thresholds must be object")
        thresholds_root = {}
    if GROK_WORKER_ID not in thresholds_root:
        errors.append(f"invariant: capacity_thresholds.{GROK_WORKER_ID} is required")
    grok_th = thresholds_root.get(GROK_WORKER_ID) or {}
    if not isinstance(grok_th, dict):
        errors.append(f"invariant: capacity_thresholds.{GROK_WORKER_ID} must be object")
        grok_th = {}
    for key, spec_max in HARDCODED_GROK_THRESHOLDS.items():
        val = grok_th.get(key)
        if not _is_finite_number(val):
            errors.append(f"invariant: capacity_thresholds.{GROK_WORKER_ID}.{key} must be a finite number")
        elif val > spec_max:
            errors.append(
                f"invariant: capacity_thresholds.{GROK_WORKER_ID}.{key} must be <= {spec_max}"
            )
    default_th = thresholds_root.get("default") or {}
    for key in ("conserve_at", "reserve_at", "exhausted_at"):
        g_val = grok_th.get(key)
        d_val = default_th.get(key) if isinstance(default_th, dict) else None
        if _is_finite_number(g_val) and _is_finite_number(d_val) and g_val > d_val:
            errors.append(f"invariant: grok capacity {key} must be <= default {key}")
    for name, th in thresholds_root.items():
        if not isinstance(th, dict):
            continue
        c, r, e = th.get("conserve_at"), th.get("reserve_at"), th.get("exhausted_at")
        if not all(_is_finite_number(x) for x in (c, r, e)):
            errors.append(f"invariant: capacity_thresholds.{name} values must be finite numbers")
            continue
        if not (0 <= c < r < e <= 100):
            errors.append(
                f"invariant: capacity_thresholds.{name} must be monotonic 0 <= conserve < reserve < exhausted <= 100"
            )
    vel = policy.get("velocity") or {}
    if not isinstance(vel, dict):
        errors.append("invariant: velocity must be object")
        vel = {}
    for key, spec in HARDCODED_VELOCITY.items():
        val = vel.get(key)
        if not _is_finite_number(val):
            errors.append(f"invariant: velocity.{key} must be a finite number")
        elif key == "min_points" and (not isinstance(val, int) or isinstance(val, bool) or val < 2):
            errors.append("invariant: velocity.min_points must be integer >= 2")
        elif key in ("window_hours", "assumed_reset_hours_if_unknown") and val <= 0:
            errors.append(f"invariant: velocity.{key} must be > 0")
        elif key == "min_span_minutes" and val < 0:
            errors.append("invariant: velocity.min_span_minutes must be >= 0")
        elif key == "reserve_if_exhaustion_within_hours" and val < 0:
            errors.append("invariant: velocity.reserve_if_exhaustion_within_hours must be >= 0")
    conduct = policy.get("grok_conserve_conduct") or {}
    if not isinstance(conduct, dict):
        errors.append("invariant: grok_conserve_conduct must be object")
        conduct = {}
    for key, expected in HARDCODED_GROK_CONSERVE_CONDUCT.items():
        if conduct.get(key) != expected:
            errors.append(f"invariant: grok_conserve_conduct.{key} must be {expected!r}")
    for pen_key in ("grok_routing_penalty_default", "grok_routing_penalty_step", "grok_routing_penalty_max"):
        val = policy.get(pen_key)
        if val is not None and (not _is_finite_number(val) or val < 0):
            errors.append(f"invariant: {pen_key} must be >= 0")
    imb = policy.get("imbalance") or {}
    if not isinstance(imb, dict):
        errors.append("invariant: imbalance must be object")
        imb = {}
    share = imb.get("max_grok_share_delegatable")
    if share is not None and (not _is_finite_number(share) or not (0 <= share <= 1)):
        errors.append("invariant: imbalance.max_grok_share_delegatable must be in [0, 1]")
    for pen_key in ("penalty_step", "penalty_max", "penalty_hard_block_at"):
        val = imb.get(pen_key)
        if val is not None and (not _is_finite_number(val) or val < 0):
            errors.append(f"invariant: imbalance.{pen_key} must be >= 0")
    known_bench = _known_benchmark_classes()
    bcm = policy.get("benchmark_class_map") or {}
    if isinstance(bcm, dict):
        for src, target in bcm.items():
            if target not in known_bench:
                errors.append(f"invariant: benchmark_class_map.{src} target {target!r} not a known benchmark class")
    forbidden_workers = {GROK_WORKER_ID}
    forbidden_workers.update(w for w in worker_registry.WORKERS if worker_registry.is_metered(w))
    for list_name, paths in (
        ("fail_closed_conservative_order", [policy.get("fail_closed_conservative_order")]),
        ("specialisation", [
            (policy.get("specialisation") or {}).get(fam, {}).get("prefer_workers")
            for fam in ("engineering", "reasoning_review")
        ]),
    ):
        for workers in paths:
            if not workers:
                continue
            if not isinstance(workers, list):
                errors.append(f"invariant: {list_name} must be array")
                continue
            for w in workers:
                if w in forbidden_workers:
                    errors.append(f"invariant: {list_name} must not contain {w!r}")
    errors.extend(validate_hardcoded_safety_invariants(policy))
    return errors


def append_audit_event(event_type: str, payload: dict[str, Any], *, fsync: bool = False) -> None:
    ensure_dirs()
    GOVERNANCE_DIR.mkdir(parents=True, exist_ok=True)
    rec = {"event": event_type, **payload}
    with GOVERNANCE_AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        if fsync:
            f.flush()
            os.fsync(f.fileno())


def _policy_structure_bounds(data: Any, *, depth: int = 0, nodes: list[int] | None = None) -> list[str]:
    """Reject pathological policy JSON before schema validation."""
    if nodes is None:
        nodes = [0]
    errors: list[str] = []
    nodes[0] += 1
    if nodes[0] > MAX_POLICY_NODES:
        errors.append(f"policy exceeds max node count {MAX_POLICY_NODES}")
        return errors
    if depth > MAX_POLICY_DEPTH:
        errors.append(f"policy exceeds max depth {MAX_POLICY_DEPTH}")
        return errors
    if isinstance(data, list):
        if len(data) > MAX_POLICY_ARRAY_LEN:
            errors.append(f"array length {len(data)} exceeds max {MAX_POLICY_ARRAY_LEN}")
        for item in data:
            errors.extend(_policy_structure_bounds(item, depth=depth + 1, nodes=nodes))
    elif isinstance(data, dict):
        for value in data.values():
            errors.extend(_policy_structure_bounds(value, depth=depth + 1, nodes=nodes))
    return errors


def load_policy(path: Path | str | None = None) -> PolicyLoad:
    """Load and validate governance policy. FAIL_CLOSED on any problem."""
    p = _policy_path(path)
    try:
        raw = p.read_bytes()
    except OSError as exc:
        pl = PolicyLoad(ok=False, mode="FAIL_CLOSED", policy=None, sha256="", errors=[f"unreadable: {exc}"])
        append_audit_event("GOVERNANCE_POLICY_FAIL_CLOSED", {"path": str(p), "errors": pl.errors})
        return pl
    if len(raw) > MAX_POLICY_BYTES:
        pl = PolicyLoad(
            ok=False,
            mode="FAIL_CLOSED",
            policy=None,
            sha256=_sha256_bytes(raw),
            errors=[f"policy exceeds max bytes {MAX_POLICY_BYTES}"],
        )
        append_audit_event("GOVERNANCE_POLICY_FAIL_CLOSED", {"path": str(p), "sha256": pl.sha256, "errors": pl.errors})
        return pl
    sha = _sha256_bytes(raw)
    try:
        policy = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, UnicodeError, ValueError, RecursionError) as exc:
        pl = PolicyLoad(ok=False, mode="FAIL_CLOSED", policy=None, sha256=sha, errors=[f"invalid JSON: {exc}"])
        append_audit_event("GOVERNANCE_POLICY_FAIL_CLOSED", {"path": str(p), "sha256": sha, "errors": pl.errors})
        return pl
    if not isinstance(policy, dict):
        pl = PolicyLoad(ok=False, mode="FAIL_CLOSED", policy=None, sha256=sha, errors=["policy root must be object"])
        append_audit_event("GOVERNANCE_POLICY_FAIL_CLOSED", {"path": str(p), "sha256": sha, "errors": pl.errors})
        return pl
    try:
        errors = _policy_structure_bounds(policy)
        if not errors:
            errors = validate_policy_schema(policy) + validate_policy_invariants(policy)
        if len(errors) > MAX_VALIDATOR_ERRORS:
            errors = errors[:MAX_VALIDATOR_ERRORS] + [f"truncated after {MAX_VALIDATOR_ERRORS} errors"]
    except Exception as exc:
        errors = [f"validation exception: {exc}"]
    if errors:
        pl = PolicyLoad(ok=False, mode="FAIL_CLOSED", policy=None, sha256=sha, errors=errors)
        append_audit_event("GOVERNANCE_POLICY_FAIL_CLOSED", {"path": str(p), "sha256": sha, "errors": errors})
        return pl
    return PolicyLoad(ok=True, mode="ENFORCED", policy=policy, sha256=sha, errors=[])


def metered_permitted(policy_load: PolicyLoad | None = None) -> bool:
    """Consult governance paid_spend, metered_fallback, and live_gate."""
    from .adapters import live_gate

    pl = policy_load or load_policy()
    policy = pl.policy or {}
    if policy.get("paid_spend") != "ON":
        return False
    if policy.get("metered_fallback") != "ALLOWED":
        return False
    try:
        cap = live_gate.cost_cap({})
        return cap is not None
    except Exception:
        return False


def grok_worker_id(policy: dict[str, Any] | None) -> str:
    if policy and policy.get("grok_worker_id"):
        return policy["grok_worker_id"]
    return GROK_WORKER_ID


def protected_classes(policy: dict[str, Any] | None) -> frozenset[str]:
    return HARDCODED_PROTECTED_CLASSES


def is_protected_class(task_class: str, policy: dict[str, Any] | None) -> bool:
    return task_class in protected_classes(policy)


def task_family(task_class: str, policy: dict[str, Any] | None) -> str:
    families = (policy or {}).get("task_families") or HARDCODED_TASK_FAMILIES
    for name, classes in families.items():
        if task_class in (classes or []):
            return name
    return "unknown"


def benchmark_class_for(task_class: str, policy: dict[str, Any] | None) -> str | None:
    """Resolve benchmark class for quality/latency; None if task is unclassified."""
    if not task_class or task_family(task_class, policy) == "unknown":
        return None
    bcm = (policy or {}).get("benchmark_class_map") or HARDCODED_BENCHMARK_CLASS_MAP
    return bcm.get(task_class, task_class)


def fail_closed_policy() -> dict[str, Any]:
    """Conservative hardcoded policy used when ENFORCED policy is unavailable."""
    return {
        "grok_worker_id": GROK_WORKER_ID,
        "capacity_thresholds": {
            "default": {"conserve_at": 70, "reserve_at": 85, "exhausted_at": 100},
            GROK_WORKER_ID: dict(HARDCODED_GROK_THRESHOLDS),
        },
        "primary_capacity_pool": {
            "cursor_sub": "cursor_models",
            GROK_WORKER_ID: "weekly",
            "claude_pro_sub": "week_all_models",
            "codex_sub": "week",
        },
        "capacity_decay": {
            "decay_pct_per_hour": 0.5,
            "max_observation_age_hours": 24,
            "unknown_state": {"default": "CONSERVE", GROK_WORKER_ID: "CONSERVE"},
        },
        "velocity": dict(HARDCODED_VELOCITY),
        "grok_conserve_conduct": dict(HARDCODED_GROK_CONSERVE_CONDUCT),
        "grok_justification_min_length": MIN_JUSTIFICATION_LENGTH,
        "tie_band_quality_delta": 0.05,
        "fail_closed_conservative_order": list(HARDCODED_FAIL_CLOSED_ORDER),
        "worker_execution_scope": {
            "isolated_sandbox_root": str(Path.home() / "wi-sandboxes"),
            "zdotdir_empty": str(Path.home() / "wi-sandboxes" / ".zdotdir-empty"),
            "allowed_workspace_globs": ["~/wi-*-wt", "~/wt-*", "~/wi-gov-*"],
            "allowed_temp_under_sandbox": True,
            "denied_paths": [
                str(Path.home() / "beta-os"),
                str(Path.home() / "wi-runtime"),
            ],
            "env_allowlist": ["PATH", "HOME", "USER", "TERM", "LANG", "TMPDIR", "ZDOTDIR"],
        },
    }
