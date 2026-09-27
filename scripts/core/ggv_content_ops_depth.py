#!/usr/bin/env python3
"""GGV Content Machine ops depth — content/library operator path on Beta :8788.

Decision served: keep_building_without_matt (owner-autonomous-release-2026-09-19)
+ overnight Owner directive + Connection/NAS P0 continue without Haikal human
+ docs/deliveries/GROK-PLAN-GGV-CONTENT-OPS-DEPTH-2026-09-23.md.

Authorised content seats open a content/library asset and see operator detail
tied to NAS-aware Smart Upload / library read models (no invent assets, no
Metricool metrics). Allowed actions: note / tag-touch / next-action-touch /
handoff-touch / dismiss-noise — refresh GGV Content Needs-You + Owner attention
projections. Never Metricool/Klaviyo publish. Never Haikal human fake. Never
NAS destroy. Never invent PROVEN/READY/staff_ready. CAP-GGV-01/05 stay BUILT;
CAP-GGV-03/06 SPECIFIED; target CRs stay OPEN.

Bound: beta-ggv-loop-safe.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import ggv_content_nas_haikal_prep as nas_prep
from core import ggv_ops_pack as ops
from core import nas_library as nas
from core import staff_ready_ux as sru

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LIVE_CATALOG_DB = CATALOG_DB.resolve()
DEFAULT_OPERATOR_DB = BETA_ROOT / "catalog" / "ggv_content_ops_operator.sqlite"
LIVE_OPERATOR_DB = DEFAULT_OPERATOR_DB.resolve()

BOUND = "beta-ggv-loop-safe"
SCHEMA_ID = "wolf.ggv-content-ops-depth.v1"
SLICE = "ggv_content_ops_depth"
OPERATOR_DEPTH_SCHEMA_ID = SCHEMA_ID
OPERATOR_DEPTH_SLICE = SLICE
RUN_ID = "BF-ggv-content-ops-depth-20260923"
CONTENT_HREF = "/content-2.0"
DESK_ANCHOR = "/content-2.0#content-ops-depth"

CAP_01 = "CAP-GGV-01"
CAP_05 = "CAP-GGV-05"
CAP_03 = "CAP-GGV-03"
CAP_06 = "CAP-GGV-06"
CR_01 = "CR-8c1fa12404180c02"
CR_05 = "CR-e20099e21930b9a6"

OWNER = ops.OWNER
AMANDA = ops.AMANDA
HAIKAL = ops.HAIKAL
MISA = ops.MISA
CONTENT_OPERATOR_FIXTURES: tuple[str, ...] = (AMANDA, HAIKAL, MISA, OWNER)
CONTENT_OPERATOR_ROLES: tuple[str, ...] = (
    "ROLE-CONTENT-MGMT",
    "ROLE-GGV-EDIT",
    "ROLE-CONTENT-CREW",
    "ROLE-MATT",
)

PERM_CONTENT_OPERATOR = "ggv.content.operator"
PERM_CONTENT_OPERATOR_ID = "PERM-GGV-CONTENT-OPERATOR"
SCOPE_CONTENT_LIBRARY = "SCOPE-GGV-CONTENT-LIBRARY"
ENTITY_GGV = ops.ENTITY_GGV

CONTENT_OPERATOR_ACTION_KINDS = frozenset(
    {
        "note",
        "tag_touch",
        "next_action",
        "handoff_touch",
        "dismiss_noise",
    }
)
_ACTION_KIND_ALIASES = {
    "note": "note",
    "tag": "tag_touch",
    "tag-touch": "tag_touch",
    "tag_touch": "tag_touch",
    "next-action": "next_action",
    "next-action-touch": "next_action",
    "next_action_touch": "next_action",
    "next_action": "next_action",
    "handoff": "handoff_touch",
    "handoff-touch": "handoff_touch",
    "handoff_touch": "handoff_touch",
    "handover": "handoff_touch",
    "handover-touch": "handoff_touch",
    "handover_touch": "handoff_touch",
    "dismiss": "dismiss_noise",
    "dismiss-noise": "dismiss_noise",
    "dismiss_noise": "dismiss_noise",
}
OPERATOR_DISPOSITIONS = frozenset({"open", "dismissed"})
CANDIDATE_LIMIT = 40

OPERATOR_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS content_operator_state (
  object_id TEXT PRIMARY KEY,
  asset_id INTEGER NOT NULL,
  brand TEXT,
  disposition TEXT NOT NULL DEFAULT 'open',
  note TEXT,
  tags_json TEXT NOT NULL DEFAULT '[]',
  next_action TEXT,
  last_kind TEXT,
  updated_by TEXT,
  updated_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS content_operator_events (
  event_id TEXT PRIMARY KEY,
  object_id TEXT NOT NULL,
  asset_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  note TEXT,
  disposition_before TEXT,
  disposition_after TEXT,
  actor_person_id TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_content_op_events_obj
  ON content_operator_events(object_id, recorded_at DESC);
"""

HONESTY: dict[str, Any] = {
    "bound": BOUND,
    "slice": SLICE,
    "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
    "operator_depth_schema_id": OPERATOR_DEPTH_SCHEMA_ID,
    "run_id": RUN_ID,
    "cap_ggv_01": CAP_01,
    "cap_ggv_05": CAP_05,
    "cr_01": CR_01,
    "cr_05": CR_05,
    "proven": False,
    "ready": False,
    "staff_ready": False,
    "invented_proven": False,
    "invented_ready": False,
    "invented_staff_ready": False,
    "invented_haikal_human_pass": False,
    "haikal_human_status": "not_started",
    "empty_operator_is_not_invent": True,
    "empty_library_is_not_invent": True,
    "invented_assets": False,
    "invented_metricool_metrics": False,
    "metricool_write": False,
    "metricool_publish": False,
    "klaviyo_write": False,
    "klaviyo_publish": False,
    "nas_destructive": False,
    "nas_destroy": False,
    "cr_resolved": False,
    "false_resolve_cr": False,
    "caps_raised": False,
    "production": False,
    "production_mutate": False,
    "cf_seat_mint": False,
    "cloudflare_mutated": False,
    "access_mutated": False,
    "money": None,
    "clickup_retired": True,
    "telegram_retired": True,
    "anon_fail_closed": True,
    "live_habitat_commission": False,
}


class ContentOpsError(ValueError):
    """Fail closed. Does not invent library assets, maturity, or publish."""

    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def honesty_flags() -> dict[str, Any]:
    flags = dict(HONESTY)
    flags["ledger_maturity"] = _ledger_cap(CAP_01)
    flags["cr_state"] = (_cr_row(CR_01).get("state") or "UNKNOWN")
    return flags


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
        "operator_depth_schema_id": OPERATOR_DEPTH_SCHEMA_ID,
        "bound": BOUND,
        "slice": SLICE,
        "run_id": RUN_ID,
        "content_operator_action_kinds": sorted(CONTENT_OPERATOR_ACTION_KINDS),
        "caps": [CAP_01, CAP_05, CAP_03, CAP_06],
        "target_crs": [CR_01, CR_05],
        "surface": CONTENT_HREF,
        "metricool_publish": False,
        "klaviyo_publish": False,
        "nas_destructive": False,
        "proven_property": False,
        "ready_property": False,
        "staff_ready_property": False,
        "additionalProperties": False,
    }


def refuse_proven(_body: dict[str, Any] | None = None) -> None:
    raise ContentOpsError(
        "GGV Content ops depth refuses inventing PROVEN.",
        code="proven_refused",
        http_status=403,
    )


def refuse_ready(_body: dict[str, Any] | None = None) -> None:
    raise ContentOpsError(
        "GGV Content ops depth refuses inventing READY.",
        code="ready_refused",
        http_status=403,
    )


def refuse_staff_ready(_body: dict[str, Any] | None = None) -> None:
    raise ContentOpsError(
        "GGV Content ops depth refuses inventing staff_ready=true.",
        code="staff_ready_refused",
        http_status=403,
    )


def refuse_haikal_human(_body: dict[str, Any] | None = None) -> None:
    raise ContentOpsError(
        "GGV Content ops depth refuses inventing Haikal human PASS.",
        code="haikal_human_refused",
        http_status=403,
    )


def refuse_metricool(_body: dict[str, Any] | None = None) -> None:
    raise ContentOpsError(
        "GGV Content ops depth refuses Metricool publish/write.",
        code="metricool_refused",
        http_status=403,
    )


def refuse_klaviyo(_body: dict[str, Any] | None = None) -> None:
    raise ContentOpsError(
        "GGV Content ops depth refuses Klaviyo publish/write.",
        code="klaviyo_refused",
        http_status=403,
    )


def refuse_nas_destroy(_body: dict[str, Any] | None = None) -> None:
    raise ContentOpsError(
        "GGV Content ops depth refuses NAS destroy.",
        code="nas_destroy_refused",
        http_status=403,
    )


def refuse_invent_asset(_body: dict[str, Any] | None = None) -> None:
    raise ContentOpsError(
        "GGV Content ops depth refuses inventing library assets.",
        code="invent_asset_refused",
        http_status=403,
    )


def refuse_production(_body: dict[str, Any] | None = None) -> None:
    raise ContentOpsError(
        "GGV Content ops depth refuses Production mutation.",
        code="production_refused",
        http_status=403,
    )


def refuse_resolve(_body: dict[str, Any] | None = None) -> None:
    raise ContentOpsError(
        "GGV Content ops depth refuses resolving completion rows.",
        code="resolve_refused",
        http_status=403,
    )


def refuse_code(path: str) -> str | None:
    """Map refuse paths. Operator depth routes are not refused here."""
    p = (path or "").rstrip("/")
    if "/operator-depth" in p or "/operator-action" in p or p.endswith("/operator"):
        return None
    tail = p.rsplit("/", 1)[-1].lower()
    mapping = {
        "proven": "proven",
        "ready": "ready",
        "staff-ready": "staff_ready",
        "staff_ready": "staff_ready",
        "haikal-human": "haikal_human",
        "haikal_human": "haikal_human",
        "metricool": "metricool",
        "metricool-publish": "metricool",
        "klaviyo": "klaviyo",
        "klaviyo-publish": "klaviyo",
        "nas-destroy": "nas_destroy",
        "destroy": "nas_destroy",
        "invent-asset": "invent_asset",
        "production": "production",
        "resolve": "resolve",
    }
    return mapping.get(tail)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _under_test_process() -> bool:
    return (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1"


def assert_catalog_writable(db_path: Path | str | None = None) -> None:
    path = Path(db_path) if db_path else CATALOG_DB
    resolved = Path(path).resolve()
    from core.canonical_guard import assert_write_allowed
    assert_write_allowed(resolved)
    if resolved == LIVE_CATALOG_DB and _under_test_process():
        raise ContentOpsError(
            "test mode refuses writes to live catalog DB; point catalog at a temp copy",
            code="live_write_refused",
        )


def assert_operator_writable(db_path: Path | str | None = None) -> None:
    path = Path(db_path) if db_path else DEFAULT_OPERATOR_DB
    resolved = Path(path).resolve()
    from core.canonical_guard import assert_write_allowed
    assert_write_allowed(resolved)
    if resolved == LIVE_OPERATOR_DB and _under_test_process():
        raise ContentOpsError(
            "test mode refuses writes to live content operator DB; "
            "point operator_db at a temp copy",
            code="live_write_refused",
        )


def _assert_beta_path(path: Path) -> Path:
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    try:
        resolved.relative_to(BETA_ROOT)
        return resolved
    except ValueError:
        pass
    tmp = Path(os.environ.get("TMPDIR") or "/tmp").resolve()
    try:
        resolved.relative_to(tmp)
    except ValueError as exc:
        raise ContentOpsError(
            "GGV Content ops depth refuses a path outside Beta or a test fixture.",
            code="not_beta",
        ) from exc
    return resolved


def operator_db_path(db_path: Path | str | None = None) -> Path:
    path = Path(db_path) if db_path else DEFAULT_OPERATOR_DB
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    return _assert_beta_path(resolved)


def ensure_operator_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(OPERATOR_SCHEMA_SQL)
    conn.commit()


def _open_catalog(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else CATALOG_DB
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _open_operator(
    db_path: Path | str | None = None, *, write: bool = True
) -> tuple[sqlite3.Connection, Path]:
    path = operator_db_path(db_path)
    if write:
        assert_operator_writable(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        ensure_operator_schema(conn)
        return conn, path
    if not path.is_file():
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        ensure_operator_schema(conn)
        return conn, path
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn, path


def _normalise_action_kind(kind: str | None) -> str:
    raw = (kind or "").strip().lower()
    return _ACTION_KIND_ALIASES.get(raw, raw)


def _ledger_cap(cap: str, ledger_path: Path | str | None = None) -> str:
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    row = data.get(cap) if isinstance(data, dict) else None
    if isinstance(row, list) and row:
        return str(row[0])
    return "UNKNOWN"


def _cr_row(cr_id: str, catalog_db: Path | str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": cr_id,
        "state": None,
        "present": False,
    }
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    if not path.is_file():
        return out
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return out
    try:
        row = conn.execute(
            "SELECT state FROM wolf_completion_items WHERE id=?",
            (cr_id,),
        ).fetchone()
    except sqlite3.Error:
        return out
    finally:
        conn.close()
    if row is None:
        return out
    out["present"] = True
    out["state"] = row[0]
    return out


def require_actor(person_id: str | None) -> dict[str, Any]:
    """GGV content seats only (Amanda/Haikal/Misa/Owner). Anon/outsider fail closed."""
    pid = (person_id or "").strip()
    if not pid:
        raise ContentOpsError(
            "GGV Content ops depth refuses anonymous callers.",
            code="forbidden",
            http_status=403,
        )
    seat = ops.seat_for(pid)
    if seat is None:
        raise ContentOpsError(
            "GGV Content ops depth requires a GGV content seat "
            "(Amanda/Haikal/Misa/Owner fixtures).",
            code="forbidden",
            http_status=403,
        )
    return {
        "person_id": pid,
        "seat": seat.get("label") or seat.get("seat") or "content",
        "label": sru.human_person(pid),
        "live_habitat_commission": False,
    }


def object_id_for_asset(asset_id: int | str) -> str:
    return f"asset-{int(asset_id)}"


def parse_asset_object_id(object_id: str) -> int:
    key = (object_id or "").strip()
    if key.startswith("asset-"):
        key = key[6:]
    try:
        aid = int(key)
    except (TypeError, ValueError) as exc:
        raise ContentOpsError(
            f"Unknown content/library object {object_id!r}",
            code="not_found",
            http_status=404,
        ) from exc
    if aid <= 0:
        raise ContentOpsError(
            f"Unknown content/library object {object_id!r}",
            code="not_found",
            http_status=404,
        )
    return aid


def content_object_operator_href(object_id: str | None) -> str:
    key = (object_id or "").strip()
    if not key:
        return DESK_ANCHOR
    return f"{CONTENT_HREF}#content-obj-{key}"


def _role_has_perm(conn: sqlite3.Connection, role_id: str, perm_id: str) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM org_role_permissions
        WHERE role_id=? AND permission_id=? AND effect='ALLOW'
        """,
        (role_id, perm_id),
    ).fetchone()
    return bool(row)


def ensure_operator_depth_rbac(
    *,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Idempotent grant: ggv.content.operator on content/Owner roles + GGV entity scope.

    Beta catalog only. Does not mint CF Access seats. Does not invent Haikal human.
    """
    own = conn is None
    c = conn or _open_catalog(db_path)
    try:
        ts = _now_utc_iso()
        existing = c.execute(
            "SELECT permission_id, status FROM org_permissions WHERE code=?",
            (PERM_CONTENT_OPERATOR,),
        ).fetchone()
        op_id = str(existing["permission_id"]) if existing else PERM_CONTENT_OPERATOR_ID

        scope_row = c.execute(
            "SELECT scope_id, status FROM org_scopes WHERE scope_id=?",
            (SCOPE_CONTENT_LIBRARY,),
        ).fetchone()
        target_ok = bool(
            c.execute(
                """
                SELECT 1 FROM org_scope_targets
                WHERE scope_id=? AND target_type='entity' AND target_id=?
                """,
                (SCOPE_CONTENT_LIBRARY, ENTITY_GGV),
            ).fetchone()
        )
        roles_ok = all(
            _role_has_perm(c, role_id, op_id) for role_id in CONTENT_OPERATOR_ROLES
        )
        fixture_asg: dict[str, str | None] = {}
        for pid in CONTENT_OPERATOR_FIXTURES:
            asg = c.execute(
                """
                SELECT a.assignment_id
                FROM org_assignments a
                JOIN org_positions po ON po.position_id = a.position_id
                WHERE a.person_id=? AND po.role_id IN (?, ?, ?, ?)
                  AND a.status='ACTIVE' AND a.end_at IS NULL
                LIMIT 1
                """,
                (pid, *CONTENT_OPERATOR_ROLES),
            ).fetchone()
            fixture_asg[pid] = str(asg["assignment_id"]) if asg else None
        scopes_linked = True
        for asg_id in fixture_asg.values():
            if not asg_id:
                scopes_linked = False
                break
            linked = c.execute(
                """
                SELECT 1 FROM org_assignment_scopes
                WHERE assignment_id=? AND scope_id=?
                """,
                (asg_id, SCOPE_CONTENT_LIBRARY),
            ).fetchone()
            if not linked:
                scopes_linked = False
                break

        already = (
            bool(existing)
            and str(existing["status"] or "") == "ACTIVE"
            and bool(scope_row)
            and str(scope_row["status"] or "") == "ACTIVE"
            and target_ok
            and roles_ok
            and scopes_linked
        )
        if already:
            return {
                "ok": True,
                "grants": [PERM_CONTENT_OPERATOR],
                "roles": list(CONTENT_OPERATOR_ROLES),
                "permission_ids": {PERM_CONTENT_OPERATOR: op_id},
                "scope_id": SCOPE_CONTENT_LIBRARY,
                "unchanged": True,
                "cf_seat_mint": False,
                "live_habitat_commission": False,
                "bound": BOUND,
            }

        db_file = Path(c.execute("PRAGMA database_list").fetchone()[2] or CATALOG_DB)
        assert_catalog_writable(db_file)

        c.execute(
            """
            INSERT INTO org_permissions (
              permission_id, code, resource, action, description,
              status, created_at, updated_at
            ) VALUES (?, ?, 'ggv.content', 'operator',
              'Content/library operator detail + note/tag/next/handoff/dismiss (no Metricool/Klaviyo publish; no NAS destroy)',
              'ACTIVE', ?, ?)
            ON CONFLICT(permission_id) DO UPDATE SET
              code=excluded.code,
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (op_id, PERM_CONTENT_OPERATOR, ts, ts),
        )
        c.execute(
            """
            UPDATE org_permissions
               SET status='ACTIVE', updated_at=?
             WHERE code=? AND status!='ACTIVE'
            """,
            (ts, PERM_CONTENT_OPERATOR),
        )
        c.execute(
            """
            INSERT INTO org_scopes (
              scope_id, scope_type, display_name, status, created_at, updated_at
            ) VALUES (?, 'entity', 'GGV content/library operator', 'ACTIVE', ?, ?)
            ON CONFLICT(scope_id) DO UPDATE SET
              status='ACTIVE',
              updated_at=excluded.updated_at
            """,
            (SCOPE_CONTENT_LIBRARY, ts, ts),
        )
        c.execute(
            """
            INSERT OR IGNORE INTO org_scope_targets (
              scope_id, target_type, target_id, created_at
            ) VALUES (?, 'entity', ?, ?)
            """,
            (SCOPE_CONTENT_LIBRARY, ENTITY_GGV, ts),
        )
        for role_id in CONTENT_OPERATOR_ROLES:
            role = c.execute(
                "SELECT role_id, status FROM org_roles WHERE role_id=?",
                (role_id,),
            ).fetchone()
            if not role:
                raise ContentOpsError(
                    f"{role_id} missing — GGV content role required",
                    code="role_missing",
                    http_status=500,
                )
            c.execute(
                """
                INSERT INTO org_role_permissions (
                  role_id, permission_id, effect, created_at, updated_at
                ) VALUES (?, ?, 'ALLOW', ?, ?)
                ON CONFLICT(role_id, permission_id) DO UPDATE SET
                  effect='ALLOW', updated_at=excluded.updated_at
                """,
                (role_id, op_id, ts, ts),
            )
        for pid, asg_id in fixture_asg.items():
            if not asg_id:
                raise ContentOpsError(
                    f"fixture assignment missing for {pid}",
                    code="assignment_missing",
                    http_status=500,
                )
            c.execute(
                """
                INSERT OR IGNORE INTO org_assignment_scopes (
                  assignment_id, scope_id, start_at, end_at, status, created_at, updated_at
                ) VALUES (?, ?, ?, NULL, 'ACTIVE', ?, ?)
                """,
                (asg_id, SCOPE_CONTENT_LIBRARY, ts, ts, ts),
            )
        if commit:
            c.commit()
        return {
            "ok": True,
            "grants": [PERM_CONTENT_OPERATOR],
            "roles": list(CONTENT_OPERATOR_ROLES),
            "permission_ids": {PERM_CONTENT_OPERATOR: op_id},
            "scope_id": SCOPE_CONTENT_LIBRARY,
            "unchanged": False,
            "cf_seat_mint": False,
            "live_habitat_commission": False,
            "bound": BOUND,
        }
    finally:
        if own:
            c.close()


def prove_content_operator(
    *,
    person_id: str = HAIKAL,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Fixture prove Amanda/Haikal/Misa/Owner can run content-operator actions."""
    from core import rbac as _rbac

    own = conn is None
    c = conn or _open_catalog(db_path)
    try:
        ensure_operator_depth_rbac(conn=c, commit=True)
        pid = (person_id or "").strip() or HAIKAL
        seat = ops.seat_for(pid)
        target = {"entity_id": ENTITY_GGV}
        can_operator = bool(_rbac.can(pid, PERM_CONTENT_OPERATOR, target, conn=c))
        asg = c.execute(
            """
            SELECT a.assignment_id, a.status, a.end_at, po.role_id
            FROM org_assignments a
            JOIN org_positions po ON po.position_id = a.position_id
            WHERE a.person_id=? AND po.role_id IN (?, ?, ?, ?)
              AND a.status='ACTIVE' AND a.end_at IS NULL
            LIMIT 1
            """,
            (pid, *CONTENT_OPERATOR_ROLES),
        ).fetchone()
        allowed = (can_operator or pid == OWNER) and seat is not None
        return {
            "ok": True,
            "person_id": pid,
            "can_content_operator": allowed,
            "assignment_active": bool(asg) or pid == OWNER,
            "role_id": str(asg["role_id"]) if asg else ("ROLE-MATT" if pid == OWNER else None),
            "permission": PERM_CONTENT_OPERATOR,
            "live_habitat_commission": False,
            "cf_seat_mint": False,
            "haikal_human_pass": False,
            "staff_ready": False,
            "actions": {
                "content_operator": allowed,
                "note": allowed,
                "tag_touch": allowed,
                "next_action": allowed,
                "handoff_touch": allowed,
                "dismiss_noise": allowed,
                "metricool_publish": False,
                "klaviyo_publish": False,
                "nas_destroy": False,
                "invent_asset": False,
            },
            "bound": BOUND,
        }
    finally:
        if own:
            c.close()


def _require_content_operator(
    conn: sqlite3.Connection, *, verified_person_id: str
) -> dict[str, Any]:
    from core import rbac as _rbac

    pid = (verified_person_id or "").strip()
    seat = require_actor(pid)
    ensure_operator_depth_rbac(conn=conn, commit=False)
    target = {"entity_id": ENTITY_GGV}
    if pid != OWNER and not _rbac.can(pid, PERM_CONTENT_OPERATOR, target, conn=conn):
        raise ContentOpsError(
            f"permission denied: {PERM_CONTENT_OPERATOR}",
            code="forbidden",
            http_status=403,
        )
    return seat


def _load_asset_row(
    asset_id: int,
    *,
    catalog_db: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    own = conn is None
    c = conn or _open_catalog(catalog_db)
    try:
        row = c.execute(
            """
            SELECT id, brand, stage, type, slug, filename, original_filename,
                   canonical_filename, subject, detail, location, shoot_date,
                   media_type, source_system, library_status, processing_status,
                   readiness, readiness_note, nas_path, nas_rel, nas_received,
                   nas_received_at, data_lane, uploaded_by, uploaded_at,
                   detail_tags_json
            FROM assets
            WHERE id=?
            """,
            (asset_id,),
        ).fetchone()
    except sqlite3.Error:
        row = None
    finally:
        if own:
            c.close()
    if row is None:
        return None
    return dict(row)


def list_library_asset_ids(
    *,
    catalog_db: Path | str | None = None,
    conn: sqlite3.Connection | None = None,
    limit: int = CANDIDATE_LIMIT,
) -> list[int]:
    """Real library assets only — never invent. EMPTY when none."""
    own = conn is None
    c = conn or _open_catalog(catalog_db)
    try:
        rows = c.execute(
            """
            SELECT id FROM assets
            ORDER BY COALESCE(uploaded_at, date_added, id) DESC, id DESC
            LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        if own:
            c.close()
    return [int(r[0] if not isinstance(r, sqlite3.Row) else r["id"]) for r in rows]


def nas_readiness_strip() -> dict[str, Any]:
    """NAS / Smart Upload readiness honesty — no invent staff_ready / Haikal human."""
    status = nas.public_nas_status() if hasattr(nas, "public_nas_status") else nas_status_fallback()
    connected = bool(status.get("connected") or status.get("nas_connected"))
    prep = nas_prep.honesty_flags()
    return {
        "ok": True,
        "nas_connected": connected,
        "nas": status,
        "smart_upload_path": f"{CONTENT_HREF}#upload",
        "library_path": f"{CONTENT_HREF}#library",
        "wolf_write_prefix_rel": "_Imports/Wolf-Library",
        "staff_ready": False,
        "proven": False,
        "ready": False,
        "haikal_human_status": prep.get("haikal_human_status") or "not_started",
        "invented_staff_ready": False,
        "invented_haikal_human_pass": False,
        "nas_destructive": False,
        "message": (
            "NAS connected — Smart Upload / Library path available. "
            "staff_ready stays false until Haikal human submit."
            if connected
            else "NAS not connected — uploads stay on Beta only. Do not claim nas_received."
        ),
    }


def nas_status_fallback() -> dict[str, Any]:
    try:
        return {"connected": nas.media_library_connected(), "nas_connected": nas.media_library_connected()}
    except Exception:  # noqa: BLE001
        return {"connected": False, "nas_connected": False}


def _parse_tags(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            pass
        return [t.strip() for t in text.split(",") if t.strip()]
    return []


def _load_operator_state(
    object_id: str,
    *,
    operator_db: Path | str | None = None,
) -> dict[str, Any]:
    conn, _path = _open_operator(operator_db, write=False)
    try:
        row = conn.execute(
            """
            SELECT object_id, asset_id, brand, disposition, note, tags_json,
                   next_action, last_kind, updated_by, updated_at, created_at
            FROM content_operator_state
            WHERE object_id=?
            """,
            (object_id,),
        ).fetchone()
    except sqlite3.Error:
        row = None
    finally:
        conn.close()
    if row is None:
        return {
            "object_id": object_id,
            "disposition": "open",
            "note": None,
            "tags": [],
            "next_action": None,
            "last_kind": None,
            "updated_by": None,
            "updated_at": None,
            "empty": True,
        }
    return {
        "object_id": row["object_id"],
        "asset_id": row["asset_id"],
        "brand": row["brand"],
        "disposition": str(row["disposition"] or "open"),
        "note": row["note"],
        "tags": _parse_tags(row["tags_json"]),
        "next_action": row["next_action"],
        "last_kind": row["last_kind"],
        "updated_by": row["updated_by"],
        "updated_at": row["updated_at"],
        "created_at": row["created_at"],
        "empty": False,
    }


def list_content_operator_actions(
    object_id: str,
    *,
    operator_db: Path | str | None = None,
) -> list[dict[str, Any]]:
    conn, _path = _open_operator(operator_db, write=False)
    try:
        rows = conn.execute(
            """
            SELECT event_id, object_id, asset_id, kind, note,
                   disposition_before, disposition_after, actor_person_id,
                   recorded_at, payload_json
            FROM content_operator_events
            WHERE object_id=?
            ORDER BY recorded_at DESC
            LIMIT 40
            """,
            (object_id,),
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    out: list[dict[str, Any]] = []
    for r in rows:
        try:
            payload = json.loads(r["payload_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            payload = {}
        out.append(
            {
                "event_id": r["event_id"],
                "kind": r["kind"],
                "note": r["note"],
                "disposition_before": r["disposition_before"],
                "disposition_after": r["disposition_after"],
                "created_by": r["actor_person_id"],
                "created_at": r["recorded_at"],
                "payload": payload,
                "metricool_publish": False,
                "klaviyo_publish": False,
                "nas_destroy": False,
                "invented": False,
            }
        )
    return out


def operator_object_card(
    object_id: str,
    *,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    events: list[dict[str, Any]] | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    asset_id = parse_asset_object_id(object_id)
    asset = _load_asset_row(asset_id, catalog_db=catalog_db, conn=conn)
    if asset is None:
        raise ContentOpsError(
            f"content/library asset {asset_id} not found (no invent)",
            code="not_found",
            http_status=404,
        )
    oid = object_id_for_asset(asset_id)
    state = _load_operator_state(oid, operator_db=operator_db)
    prior = events if events is not None else list_content_operator_actions(
        oid, operator_db=operator_db
    )
    dismissed = state.get("disposition") == "dismissed"
    recorded_next = state.get("next_action")
    nas_received = bool(asset.get("nas_received"))
    title = (
        asset.get("canonical_filename")
        or asset.get("filename")
        or asset.get("original_filename")
        or f"Asset {asset_id}"
    )
    primary: dict[str, Any]
    if recorded_next and not dismissed:
        primary = {
            "code": "operator_next_action",
            "label": recorded_next,
            "href": content_object_operator_href(oid),
            "invented": False,
            "operator_recorded": True,
        }
    elif not dismissed:
        primary = {
            "code": "review_library_object",
            "label": f"Review library object · {title}",
            "href": content_object_operator_href(oid),
            "invented": False,
        }
    else:
        primary = {
            "code": "dismissed",
            "label": "Dismissed noise",
            "href": DESK_ANCHOR,
            "invented": False,
        }
    return {
        "object_id": oid,
        "asset_id": asset_id,
        "kind": "library_asset",
        "title": title,
        "staff_title": title,
        "brand": asset.get("brand"),
        "stage": asset.get("stage"),
        "media_type": asset.get("media_type") or asset.get("type"),
        "source_system": asset.get("source_system"),
        "library_status": asset.get("library_status"),
        "readiness": asset.get("readiness"),
        "readiness_note": asset.get("readiness_note"),
        "nas_received": nas_received,
        "nas_rel": asset.get("nas_rel"),
        "nas_path_leaked": False,
        "subject": asset.get("subject"),
        "detail": asset.get("detail"),
        "cap": CAP_01,
        "cr": CR_01,
        "ledger_maturity": _ledger_cap(CAP_01, ledger_path=ledger_path),
        "cr_state": (_cr_row(CR_01, catalog_db=catalog_db).get("state") or "OPEN"),
        "disposition": state.get("disposition") or "open",
        "note": state.get("note"),
        "tags": state.get("tags") or [],
        "recorded_next_action": recorded_next,
        "last_kind": state.get("last_kind"),
        "primary_next": primary,
        "operator_action_count": len(prior or []),
        "dismissed": dismissed,
        "href": content_object_operator_href(oid),
        "metricool_publish": False,
        "klaviyo_publish": False,
        "nas_destroy": False,
        "invented": False,
        "invented_assets": False,
        "proven": False,
        "ready": False,
        "staff_ready": False,
    }


def content_desk_needs_you_consequence(
    *,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    """GGV Content Needs-You projection from open operator depth objects. EMPTY honesty."""
    items: list[dict[str, Any]] = []
    primary: dict[str, Any] | None = None
    catalog = _open_catalog(catalog_db)
    try:
        for aid in list_library_asset_ids(conn=catalog):
            oid = object_id_for_asset(aid)
            card = operator_object_card(
                oid,
                catalog_db=catalog_db,
                operator_db=operator_db,
                ledger_path=ledger_path,
                conn=catalog,
            )
            if card.get("dismissed"):
                continue
            reasons: list[str] = []
            last = card.get("last_kind")
            if last == "handoff_touch":
                reasons.append("handoff_needs_you")
            if last in ("note", "tag_touch") and not card.get("recorded_next_action"):
                reasons.append("missing_next_action")
            if last == "next_action":
                reasons.append("next_action_open")
            if not last and not card.get("recorded_next_action"):
                # Unengaged library object is not auto Needs-You — EMPTY honesty.
                continue
            if not reasons and not card.get("recorded_next_action"):
                continue
            row = {
                "object_id": oid,
                "asset_id": aid,
                "staff_title": card.get("staff_title"),
                "reasons": reasons or ["operator_next"],
                "last_kind": last,
                "recorded_next_action": card.get("recorded_next_action"),
                "href": card.get("href"),
                "invented": False,
            }
            items.append(row)
            if primary is None:
                label = card.get("recorded_next_action") or (
                    f"Content Needs-You · {card.get('staff_title')}"
                )
                primary = {
                    "code": "content_needs_you",
                    "label": label,
                    "href": card.get("href"),
                    "invented": False,
                    "object_id": oid,
                }
    finally:
        catalog.close()
    empty = primary is None
    if empty:
        primary = {
            "code": "none",
            "label": "No GGV Content Needs-You — EMPTY (not invent).",
            "href": DESK_ANCHOR,
            "invented": False,
        }
    return {
        "ok": True,
        "bound": BOUND,
        "empty": empty,
        "count": 0 if empty else len(items),
        "items": items,
        "next_action": primary,
        "empty_message": (
            "No GGV Content Needs-You from operator depth — EMPTY (not invent)."
            if empty
            else None
        ),
        "invented": False,
        "metricool_publish": False,
        "klaviyo_publish": False,
        "why": (
            "GGV Content Needs-You is a projection of open content/library operator "
            "objects (dismiss-noise drops off). Recording refreshes this strip."
        ),
    }


def owner_attention_consequence(
    *,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    """Owner attention strip from content operator work. EMPTY honesty."""
    items: list[dict[str, Any]] = []
    catalog = _open_catalog(catalog_db)
    try:
        for aid in list_library_asset_ids(conn=catalog):
            oid = object_id_for_asset(aid)
            card = operator_object_card(
                oid,
                catalog_db=catalog_db,
                operator_db=operator_db,
                ledger_path=ledger_path,
                conn=catalog,
            )
            if card.get("dismissed"):
                continue
            last = card.get("last_kind")
            if not last:
                continue
            reasons: list[str] = []
            if last == "handoff_touch":
                reasons.append("handoff_touch")
            if last in ("note", "tag_touch") and not card.get("recorded_next_action"):
                reasons.append("missing_next_action")
            if not reasons:
                continue
            items.append(
                {
                    "object_id": oid,
                    "asset_id": aid,
                    "staff_title": card.get("staff_title"),
                    "reasons": reasons,
                    "last_kind": last,
                    "href": card.get("href"),
                    "invented": False,
                }
            )
    finally:
        catalog.close()
    empty = len(items) == 0
    return {
        "ok": True,
        "bound": BOUND,
        "pack": "GGV-CONTENT",
        "empty": empty,
        "count": 0 if empty else len(items),
        "attention_count": None if empty else len(items),
        "items": items,
        "empty_message": (
            "No GGV Content objects need Owner attention — EMPTY (not invent)."
            if empty
            else None
        ),
        "invented": False,
        "metricool_publish": False,
        "klaviyo_publish": False,
        "staff_ready": False,
        "why": (
            "Owner attention projects handoff / missing next from content operator "
            "depth. Dismiss-noise drops off. Not a CAP maturity invent."
        ),
    }


def operator_object_detail(
    object_id: str,
    *,
    verified_person_id: str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    """Content/library operator detail/action path. No publish. No invent assets."""
    catalog = _open_catalog(catalog_db)
    try:
        ensure_operator_depth_rbac(conn=catalog, commit=True)
        oid = object_id_for_asset(parse_asset_object_id(object_id))
        pid = (verified_person_id or "").strip() or None
        actions = {
            "content_operator": False,
            "note": False,
            "tag_touch": False,
            "next_action": False,
            "handoff_touch": False,
            "dismiss_noise": False,
            "metricool_publish": False,
            "klaviyo_publish": False,
            "nas_destroy": False,
            "invent_asset": False,
        }
        if pid:
            try:
                require_actor(pid)
                prove = prove_content_operator(person_id=pid, conn=catalog)
                actions.update(prove.get("actions") or {})
            except ContentOpsError:
                pass
        prior = list_content_operator_actions(oid, operator_db=operator_db)
        card = operator_object_card(
            oid,
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
            events=prior,
            conn=catalog,
        )
        return {
            "ok": True,
            "bound": BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "slice": OPERATOR_DEPTH_SLICE,
            "object": card,
            "actions": actions,
            "operator_actions": prior,
            "href": card["href"],
            "nas_readiness": nas_readiness_strip(),
            "content_desk_needs_you": content_desk_needs_you_consequence(
                catalog_db=catalog_db,
                operator_db=operator_db,
                ledger_path=ledger_path,
            ),
            "owner_attention": owner_attention_consequence(
                catalog_db=catalog_db,
                operator_db=operator_db,
                ledger_path=ledger_path,
            ),
            "metricool_publish": False,
            "klaviyo_publish": False,
            "nas_destroy": False,
            "proven": False,
            "ready": False,
            "staff_ready": False,
            "cr_resolved": False,
            "honesty": honesty_flags(),
        }
    finally:
        catalog.close()


def record_content_operator_action(
    *,
    verified_person_id: str,
    object_id: str,
    kind: str,
    note: str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Record note / tag / next-action / handoff / dismiss. Refresh strips.

    Never Metricool/Klaviyo publish. Never NAS destroy. Never invent PROVEN/READY.
    """
    k = _normalise_action_kind(kind)
    if k not in CONTENT_OPERATOR_ACTION_KINDS:
        raise ContentOpsError(
            f"kind must be one of {sorted(CONTENT_OPERATOR_ACTION_KINDS)}",
            code="invalid_kind",
        )
    text = (note or "").strip()
    pid = (verified_person_id or "").strip()
    if not pid:
        raise ContentOpsError(
            "verified_person_id required", code="missing_verified_person"
        )
    asset_id = parse_asset_object_id(object_id)
    oid = object_id_for_asset(asset_id)
    if k in ("note", "tag_touch", "next_action", "handoff_touch") and not text:
        raise ContentOpsError(f"{k} note required", code="missing_note")
    if text and len(text) > 2000:
        raise ContentOpsError("note too long", code="invalid")

    catalog = _open_catalog(catalog_db)
    op_conn, op_path = _open_operator(operator_db, write=True)
    try:
        assert_catalog_writable(
            Path(catalog.execute("PRAGMA database_list").fetchone()[2] or CATALOG_DB)
        )
        seat = _require_content_operator(catalog, verified_person_id=pid)
        asset = _load_asset_row(asset_id, conn=catalog)
        if asset is None:
            raise ContentOpsError(
                f"content/library asset {asset_id} not found (no invent)",
                code="not_found",
                http_status=404,
            )
        before = _load_operator_state(oid, operator_db=op_path)
        before_disp = str(before.get("disposition") or "open")
        stamp = _now_utc_iso()
        new_disp = before_disp
        new_note = str(before.get("note") or "")
        new_next = before.get("next_action")
        new_tags = list(before.get("tags") or [])
        event_note: str | None = text or None

        if k == "note":
            new_note = text
        elif k == "tag_touch":
            # Operator tags only — never Metricool tags / invent publish tags.
            touched = _parse_tags(text)
            if not touched:
                touched = [text]
            merged: list[str] = []
            for t in list(new_tags) + touched:
                if t and t not in merged:
                    merged.append(t)
            new_tags = merged[:24]
            new_note = text if not new_note else new_note
        elif k == "next_action":
            new_next = text
            new_note = text if not new_note else new_note
        elif k == "handoff_touch":
            new_note = text
        elif k == "dismiss_noise":
            new_disp = "dismissed"
            if text:
                new_note = text
            elif not event_note:
                event_note = "Dismissed noise by content operator."

        created_at = before.get("created_at") or stamp
        op_conn.execute(
            """
            INSERT INTO content_operator_state (
              object_id, asset_id, brand, disposition, note, tags_json,
              next_action, last_kind, updated_by, updated_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              disposition=excluded.disposition,
              note=excluded.note,
              tags_json=excluded.tags_json,
              next_action=excluded.next_action,
              last_kind=excluded.last_kind,
              updated_by=excluded.updated_by,
              updated_at=excluded.updated_at
            """,
            (
                oid,
                asset_id,
                asset.get("brand"),
                new_disp,
                new_note or None,
                json.dumps(new_tags),
                new_next,
                k,
                seat["person_id"],
                stamp,
                created_at,
            ),
        )
        event_id = "CEV-" + uuid.uuid4().hex[:12]
        payload = {
            "operator_depth": True,
            "content_ops_depth": True,
            "kind": k,
            "tags": new_tags if k == "tag_touch" else None,
            "metricool_publish": False,
            "klaviyo_publish": False,
            "nas_destroy": False,
            "invented": False,
            "staff_ready": False,
        }
        op_conn.execute(
            """
            INSERT INTO content_operator_events (
              event_id, object_id, asset_id, kind, note,
              disposition_before, disposition_after, actor_person_id,
              recorded_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                oid,
                asset_id,
                k,
                event_note,
                before_disp,
                new_disp,
                seat["person_id"],
                stamp,
                json.dumps(payload),
            ),
        )
        if commit:
            op_conn.commit()
            # RBAC grant may have been applied; commit catalog if we wrote it.
            try:
                catalog.commit()
            except sqlite3.Error:
                pass

        card = operator_object_card(
            oid,
            catalog_db=catalog_db,
            operator_db=op_path,
            ledger_path=ledger_path,
            conn=catalog,
        )
        return {
            "ok": True,
            "bound": BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "action": "content_operator",
            "kind": k,
            "event_id": event_id,
            "object": card,
            "content_desk_needs_you": content_desk_needs_you_consequence(
                catalog_db=catalog_db,
                operator_db=op_path,
                ledger_path=ledger_path,
            ),
            "owner_attention": owner_attention_consequence(
                catalog_db=catalog_db,
                operator_db=op_path,
                ledger_path=ledger_path,
            ),
            "nas_readiness": nas_readiness_strip(),
            "metricool_publish": False,
            "klaviyo_publish": False,
            "nas_destroy": False,
            "invented_assets": False,
            "proven": False,
            "ready": False,
            "staff_ready": False,
            "cr_resolved": False,
            "honesty": honesty_flags(),
        }
    finally:
        op_conn.close()
        catalog.close()


def operator_depth_desk(
    *,
    verified_person_id: str | None = None,
    catalog_db: Path | str | None = None,
    operator_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    """Content ops depth desk: RBAC prove + library candidates + consequence honesty."""
    catalog = _open_catalog(catalog_db)
    try:
        ensure_operator_depth_rbac(conn=catalog, commit=True)
        pid = (verified_person_id or "").strip() or HAIKAL
        seat = require_actor(pid)
        prove = prove_content_operator(person_id=pid, conn=catalog)
        candidates: list[dict[str, Any]] = []
        for aid in list_library_asset_ids(conn=catalog):
            oid = object_id_for_asset(aid)
            card = operator_object_card(
                oid,
                ledger_path=ledger_path,
                catalog_db=catalog_db,
                operator_db=operator_db,
                conn=catalog,
            )
            if card.get("dismissed"):
                continue
            candidates.append(card)
        needs = content_desk_needs_you_consequence(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
        )
        attention = owner_attention_consequence(
            ledger_path=ledger_path,
            catalog_db=catalog_db,
            operator_db=operator_db,
        )
        empty = len(candidates) == 0
        return {
            "ok": True,
            "bound": BOUND,
            "schema_id": OPERATOR_DEPTH_SCHEMA_ID,
            "slice": OPERATOR_DEPTH_SLICE,
            "run_id": RUN_ID,
            "seat": seat,
            "rbac": prove,
            "object_candidates": candidates,
            "content_desk_needs_you": needs,
            "owner_attention": attention,
            "nas_readiness": nas_readiness_strip(),
            "empty": empty,
            "empty_message": (
                "No content/library objects for operator depth — EMPTY (not invent assets)."
                if empty
                else None
            ),
            "why": (
                "GGV Content Machine ops depth: content/library detail + "
                "note/tag/next-action/handoff/dismiss recording that refreshes "
                "GGV Content Needs-You and Owner attention strips. "
                "No Metricool/Klaviyo publish. No Haikal human fake. No NAS destroy."
            ),
            "metricool_publish": False,
            "klaviyo_publish": False,
            "nas_destroy": False,
            "cf_seat_mint": False,
            "live_habitat_commission": False,
            "proven": False,
            "ready": False,
            "staff_ready": False,
            "haikal_human_status": "not_started",
            "cr_resolved": False,
            "target_crs": [CR_01, CR_05],
            "caps": {
                CAP_01: _ledger_cap(CAP_01, ledger_path=ledger_path),
                CAP_05: _ledger_cap(CAP_05, ledger_path=ledger_path),
                CAP_03: _ledger_cap(CAP_03, ledger_path=ledger_path),
                CAP_06: _ledger_cap(CAP_06, ledger_path=ledger_path),
            },
            "honesty": honesty_flags(),
            "href": DESK_ANCHOR,
        }
    finally:
        catalog.close()
