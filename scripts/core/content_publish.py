#!/usr/bin/env python3
"""Habitat content publish gate — Core Approval is canonical.

Legacy Human_Approved is derived from Core APPROVED only.
APPROVED ≠ PUBLISHED. Metricool write stays fail-closed on Beta.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from core import approvals as _approvals
from core import evidence as _evidence
from core import rbac as _rbac
from core import work_items as _work_items

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"

ENTITY_GGV = "ENT-GGV"
SCOPE_GGV_CONTENT = "SCOPE-GGV-CONTENT"
BRAND_HABITAT = "habitat"
ACTION_HABITAT_PUBLISH = "HABITAT.CONTENT.PUBLISH"
PERM_APPROVE = "content.habitat.approve"
PERM_PUBLISH_REQUEST = "content.habitat.publish.request"
EVIDENCE_TYPE = "content_draft"
GOVERNED_OBJECT_TYPE = "content_planner"

STATUS_APPROVED_LEGACY = "Human_Approved"

HONESTY = {
    "core_approval_canonical": True,
    "legacy_human_approved_derived_only": True,
    "approved_is_not_published": True,
    "metricool_write": "DISABLED",
    "real_external_publish": "NO",
    "creator_approver_sod": "NOT_REQUIRED",
    "pilot_brand": BRAND_HABITAT,
}


class ContentPublishError(ValueError):
    """Fail-closed Habitat publish / submit error."""

    def __init__(self, message: str, *, code: str = "invalid", http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _norm_ws(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def fingerprint_fields(slot: dict[str, Any]) -> dict[str, Any]:
    """Canonical fingerprint fields for version hash."""
    raw_asset = slot.get("raw_asset_id")
    if raw_asset is None or str(raw_asset).strip() == "":
        asset_norm: Any = None
    else:
        try:
            asset_norm = int(raw_asset)
        except (TypeError, ValueError):
            asset_norm = _norm_ws(raw_asset)
    return {
        "brand": _norm_ws(slot.get("brand")).lower(),
        "platform": _norm_ws(slot.get("platform")),
        "title_slug": _norm_ws(slot.get("title_slug")),
        "script_body": _norm_ws(slot.get("script_body")),
        "raw_asset_id": asset_norm,
    }


def compute_version_hash(slot: dict[str, Any]) -> str:
    """SHA-256 of canonical JSON fingerprint (sorted keys)."""
    fp = fingerprint_fields(slot)
    payload = json.dumps(fp, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def metricool_write_status() -> dict[str, Any]:
    """Standing Beta fail-closed unless BETA_METRICOOL_WRITE_ENABLED already true."""
    try:
        from metricool_read_client import metricool_write_enabled

        enabled = bool(metricool_write_enabled())
    except Exception:  # noqa: BLE001
        raw = (os.environ.get("BETA_METRICOOL_WRITE_ENABLED") or "").strip().lower()
        enabled = raw in ("1", "true", "yes", "on")
    return {
        "write_enabled": enabled,
        "status": "ENABLED" if enabled else "DISABLED",
        "real_external_publish": "YES" if enabled else "NO",
    }


def _slot_row(conn: sqlite3.Connection, slot_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id, brand, platform, scheduled_date, slot_time, title_slug,
               script_body, raw_asset_id, status, updated_at,
               content_version_hash, work_item_id, core_approval_request_id,
               approved_version_hash
        FROM content_planner WHERE id = ?
        """,
        (int(slot_id),),
    ).fetchone()
    return dict(row) if row else None


def _ensure_columns(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(content_planner)")}
    for col in (
        "content_version_hash",
        "work_item_id",
        "core_approval_request_id",
        "approved_version_hash",
    ):
        if col not in cols:
            raise ContentPublishError(
                f"content_planner.{col} missing — run migrate_habitat_publish_gate",
                code="schema_missing",
                http_status=500,
            )


def refresh_version_hash(
    slot_id: int,
    *,
    verified_person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Compute hash, append content_versions if new, update content_planner."""
    own = conn is None
    c = conn or _approvals.db_connect()
    try:
        _ensure_columns(c)
        slot = _slot_row(c, slot_id)
        if not slot:
            raise ContentPublishError("slot not found", code="not_found", http_status=404)
        vhash = compute_version_hash(slot)
        fp = fingerprint_fields(slot)
        prev = (slot.get("content_version_hash") or "").strip() or None
        if prev != vhash:
            c.execute(
                """
                INSERT OR IGNORE INTO content_versions (
                  slot_id, version_hash, brand, platform, title_slug, script_body,
                  raw_asset_id, payload_json, created_by_person_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(slot_id),
                    vhash,
                    fp["brand"],
                    fp["platform"],
                    fp["title_slug"],
                    fp["script_body"],
                    fp["raw_asset_id"],
                    json.dumps(fp, sort_keys=True),
                    (verified_person_id or "").strip() or None,
                    _approvals.now_utc_iso(),
                ),
            )
            c.execute(
                """
                UPDATE content_planner
                SET content_version_hash=?
                WHERE id=?
                """,
                (vhash, int(slot_id)),
            )
        if commit and own:
            c.commit()
        out = _slot_row(c, slot_id)
        assert out is not None
        out["content_version_hash"] = vhash
        return out
    finally:
        if own:
            c.close()


def ensure_work_item_for_slot(
    slot_id: int,
    *,
    verified_person_id: str,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Create or reuse CONTENT work item owned by producer Person."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise ContentPublishError(
            "verified_person_id required", code="missing_verified_person", http_status=401
        )
    own = conn is None
    c = conn or _approvals.db_connect()
    try:
        slot = refresh_version_hash(
            slot_id, verified_person_id=verified, conn=c, commit=False
        )
        if (slot.get("brand") or "").strip().lower() != BRAND_HABITAT:
            raise ContentPublishError(
                "Habitat publish gate applies to brand=habitat only",
                code="not_habitat",
                http_status=400,
            )
        existing = (slot.get("work_item_id") or "").strip() or None
        if existing:
            wi = _work_items.get_work_item(existing, conn=c)
            if wi and wi.get("status") not in ("CANCELLED",):
                if commit and own:
                    c.commit()
                return wi
        title = f"Habitat slot {slot_id}: {_norm_ws(slot.get('title_slug')) or 'untitled'}"
        wi = _work_items.create_work_item(
            title=title[:200],
            owning_entity_id=ENTITY_GGV,
            work_type="CONTENT",
            source_type="SYSTEM",
            source_id=f"content_planner:{int(slot_id)}",
            created_by_actor_type="PERSON",
            verified_person_id=verified,
            owner_person_id=verified,
            description=f"version_hash={slot.get('content_version_hash')}",
            conn=c,
            commit=False,
        )
        c.execute(
            "UPDATE content_planner SET work_item_id=? WHERE id=?",
            (wi["work_item_id"], int(slot_id)),
        )
        if commit and own:
            c.commit()
        return wi
    finally:
        if own:
            c.close()


def submit_for_approval(
    slot_id: int,
    *,
    verified_person_id: str,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Attach content_draft evidence + create Core approval (bind_policy+enforce_evidence)."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise ContentPublishError(
            "verified_person_id required", code="missing_verified_person", http_status=401
        )

    own = conn is None
    c = conn or _approvals.db_connect()
    try:
        _approvals.assert_catalog_writable(Path(CATALOG_DB))
        ev = _rbac.evaluate(
            verified,
            PERM_PUBLISH_REQUEST,
            {"entity_id": ENTITY_GGV, "department_id": "DEPT-GGV-CONTENT"},
            conn=c,
        )
        if not ev.get("allowed"):
            raise ContentPublishError(
                "content.habitat.publish.request denied",
                code="rbac_denied",
                http_status=403,
            )

        wi = ensure_work_item_for_slot(
            slot_id, verified_person_id=verified, conn=c, commit=False
        )
        slot = _slot_row(c, slot_id)
        assert slot is not None
        vhash = (slot.get("content_version_hash") or "").strip()
        if not vhash:
            raise ContentPublishError("version hash missing", code="missing_version")

        gov_id = f"{int(slot_id)}:{vhash}"
        _evidence.submit_evidence(
            entity_id=ENTITY_GGV,
            evidence_type=EVIDENCE_TYPE,
            governed_object_type=GOVERNED_OBJECT_TYPE,
            governed_object_id=gov_id,
            verified_person_id=verified,
            scope_id=SCOPE_GGV_CONTENT,
            department_id="DEPT-GGV-CONTENT",
            object_ref=f"content_planner:{int(slot_id)}",
            content_hash=vhash,
            source_type="WORK_ITEM",
            source_reference=wi["work_item_id"],
            metadata={
                "slot_id": int(slot_id),
                "version_hash": vhash,
                "preview_title": _norm_ws(slot.get("title_slug")),
                "platform": _norm_ws(slot.get("platform")),
            },
            identity=identity,
            conn=c,
            commit=False,
        )

        prior = (slot.get("core_approval_request_id") or "").strip() or None
        if prior:
            prev = _approvals.get_approval_request(prior, conn=c, expire=True)
            if prev and prev.get("status") == "PENDING":
                prev_ref = (prev.get("evidence_reference") or "").strip()
                if prev_ref != f"version:{vhash}":
                    try:
                        _approvals.cancel_request(
                            prior,
                            verified_person_id=verified,
                            reason="superseded by new content version",
                            identity=identity,
                            conn=c,
                            commit=False,
                        )
                    except _approvals.ApprovalError:
                        pass

        asg = None
        arow = c.execute(
            """
            SELECT a.assignment_id FROM org_assignments a
            JOIN org_assignment_scopes s ON s.assignment_id=a.assignment_id
            WHERE a.person_id=? AND a.status='ACTIVE' AND a.end_at IS NULL
              AND s.scope_id=? AND s.status='ACTIVE'
            ORDER BY a.is_primary DESC, a.assignment_id
            LIMIT 1
            """,
            (verified, SCOPE_GGV_CONTENT),
        ).fetchone()
        if arow:
            asg = arow["assignment_id"]

        apr = _approvals.create_approval_request(
            title=f"Habitat publish slot {slot_id}",
            owning_entity_id=ENTITY_GGV,
            required_permission_code=PERM_APPROVE,
            verified_person_id=verified,
            request_type="GENERAL",
            # brand_id omitted: SCOPE-GGV-CONTENT is department-scoped;
            # brand_id in target breaks RBAC match for content roles.
            department_id="DEPT-GGV-CONTENT",
            source_type="WORK_ITEM",
            source_id=f"content_planner:{int(slot_id)}",
            evidence_reference=f"version:{vhash}",
            requested_by_assignment_id=asg,
            link_work_item=False,
            bind_policy=True,
            enforce_evidence=True,
            action_type=ACTION_HABITAT_PUBLISH,
            scope_id=SCOPE_GGV_CONTENT,
            governed_object_type=GOVERNED_OBJECT_TYPE,
            governed_object_id=gov_id,
            identity=identity,
            conn=c,
            commit=False,
        )

        c.execute(
            """
            UPDATE content_planner
            SET core_approval_request_id=?, work_item_id=?
            WHERE id=?
            """,
            (apr["approval_request_id"], wi["work_item_id"], int(slot_id)),
        )
        if commit and own:
            c.commit()
        out = {
            "ok": True,
            "slot_id": int(slot_id),
            "version_hash": vhash,
            "work_item_id": wi["work_item_id"],
            "approval_request_id": apr["approval_request_id"],
            "approval_status": apr.get("status"),
        }
        out.update(HONESTY)
        return out
    except (_approvals.ApprovalError, _evidence.EvidenceError, _work_items.WorkItemError) as e:
        code = getattr(e, "code", "invalid")
        status = getattr(e, "http_status", 400)
        raise ContentPublishError(str(e), code=code, http_status=status) from e
    finally:
        if own:
            c.close()


def apply_core_approval_to_slot(
    slot_id: int,
    *,
    verified_person_id: str,
    reason: str | None = None,
    identity: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Thin Core decide wrapper. On APPROVED derive Human_Approved + approved_version_hash."""
    verified = (verified_person_id or "").strip()
    if not verified:
        raise ContentPublishError(
            "verified_person_id required", code="missing_verified_person", http_status=401
        )
    own = conn is None
    c = conn or _approvals.db_connect()
    try:
        slot = refresh_version_hash(
            slot_id, verified_person_id=verified, conn=c, commit=False
        )
        if (slot.get("brand") or "").strip().lower() != BRAND_HABITAT:
            raise ContentPublishError(
                "Habitat Core approve applies to brand=habitat only",
                code="not_habitat",
                http_status=400,
            )
        apr_id = (slot.get("core_approval_request_id") or "").strip() or None
        if not apr_id:
            raise ContentPublishError(
                "no Core approval request — submit for approval first",
                code="missing_approval_request",
                http_status=409,
            )
        req = _approvals.get_approval_request(apr_id, conn=c, expire=True)
        if not req:
            raise ContentPublishError(
                "Core approval request not found", code="not_found", http_status=404
            )
        vhash = (slot.get("content_version_hash") or "").strip()
        expected_ref = f"version:{vhash}"
        if (req.get("evidence_reference") or "").strip() != expected_ref:
            raise ContentPublishError(
                "content version changed since submit — re-submit for approval",
                code="version_mismatch",
                http_status=409,
            )

        gov_id = f"{int(slot_id)}:{vhash}"
        decided = _approvals.approve_request(
            apr_id,
            verified_person_id=verified,
            reason=reason,
            enforce_evidence=True,
            governed_object_type=GOVERNED_OBJECT_TYPE,
            governed_object_id=gov_id,
            identity=identity,
            conn=c,
            commit=False,
        )
        req_out = decided.get("request") if isinstance(decided.get("request"), dict) else decided
        core_status = (req_out or {}).get("status")
        if core_status != "APPROVED":
            raise ContentPublishError(
                f"Core request not APPROVED (status={core_status!r})",
                code="not_approved",
                http_status=409,
            )

        now = _approvals.now_utc_iso()
        c.execute(
            """
            UPDATE content_planner
            SET status=?, approved_version_hash=?, updated_at=?
            WHERE id=?
            """,
            (STATUS_APPROVED_LEGACY, vhash, now, int(slot_id)),
        )
        if commit and own:
            c.commit()
        out = {
            "ok": True,
            "slot_id": int(slot_id),
            "status": STATUS_APPROVED_LEGACY,
            "approved_version_hash": vhash,
            "approval_request_id": apr_id,
            "core_status": "APPROVED",
            "derived_from_core": True,
        }
        out.update(HONESTY)
        return out
    except _approvals.ApprovalError as e:
        raise ContentPublishError(
            str(e), code=e.code, http_status=e.http_status
        ) from e
    finally:
        if own:
            c.close()


def assert_habitat_publish_allowed(
    slot_id: int,
    *,
    verified_person_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Core-canonical publish gate. Legacy Human_Approved alone → DENY.

    Returns {ok, stage: READY_TO_PUBLISH|DENIED, reason, metricool: DISABLED|...}.
    Does NOT publish externally.
    """
    mc = metricool_write_status()
    base: dict[str, Any] = {
        "ok": False,
        "stage": "DENIED",
        "reason": "denied",
        "metricool": mc["status"],
        "slot_id": int(slot_id),
        "real_external_publish": mc["real_external_publish"],
    }
    base.update(HONESTY)
    base["metricool"] = mc["status"]

    own = conn is None
    c = conn or _approvals.db_connect()
    try:
        try:
            _ensure_columns(c)
        except ContentPublishError as e:
            base["reason"] = e.code
            return base

        slot = _slot_row(c, slot_id)
        if not slot:
            base["reason"] = "slot_not_found"
            return base

        brand = (slot.get("brand") or "").strip().lower()
        if brand != BRAND_HABITAT:
            base["reason"] = "not_habitat"
            return base

        version_hash = compute_version_hash(slot)
        apr_id = (slot.get("core_approval_request_id") or "").strip() or None
        approved_hash = (slot.get("approved_version_hash") or "").strip() or None
        legacy_status = (slot.get("status") or "").strip()

        if not apr_id:
            base["reason"] = "legacy_status_alone_denied"
            base["legacy_status"] = legacy_status
            return base

        req = _approvals.get_approval_request(apr_id, conn=c, expire=True)
        if not req:
            base["reason"] = "approval_request_missing"
            return base
        if req.get("status") != "APPROVED":
            base["reason"] = f"core_not_approved:{req.get('status')}"
            base["core_status"] = req.get("status")
            return base

        if not approved_hash:
            base["reason"] = "approved_version_hash_missing"
            return base
        if version_hash != approved_hash:
            base["reason"] = "version_mismatch"
            base["content_version_hash"] = version_hash
            base["approved_version_hash"] = approved_hash
            return base

        gov_id = f"{int(slot_id)}:{version_hash}"
        ev = _evidence.evaluate_evidence_requirements(
            ENTITY_GGV,
            ACTION_HABITAT_PUBLISH,
            request_type="GENERAL",
            scope_id=SCOPE_GGV_CONTENT,
            governed_object_type=GOVERNED_OBJECT_TYPE,
            governed_object_id=gov_id,
            verified_person_id=verified_person_id,
            conn=c,
        )
        if ev.get("result") != "SATISFIED":
            base["reason"] = ev.get("reason_code") or "evidence_unsatisfied"
            base["evidence"] = ev
            return base

        base["ok"] = True
        base["stage"] = "READY_TO_PUBLISH"
        base["reason"] = (
            "metricool_write_disabled" if not mc["write_enabled"] else "ready"
        )
        base["content_version_hash"] = version_hash
        base["approved_version_hash"] = approved_hash
        base["approval_request_id"] = apr_id
        base["legacy_status"] = legacy_status
        base["core_status"] = "APPROVED"
        return base
    finally:
        if own:
            c.close()


__all__ = [
    "ACTION_HABITAT_PUBLISH",
    "BRAND_HABITAT",
    "ContentPublishError",
    "HONESTY",
    "apply_core_approval_to_slot",
    "assert_habitat_publish_allowed",
    "compute_version_hash",
    "ensure_work_item_for_slot",
    "fingerprint_fields",
    "metricool_write_status",
    "refresh_version_hash",
    "submit_for_approval",
]
